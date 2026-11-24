"""Plan sharded Boat comparisons for a GitHub Native Merge Queue group."""
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

from common import HEX40, PIN, REPO, REPO_ID, digest, policy, read, write
from gitrepo import Git, GitFailure, Refusal, safe_path
from intake import affected, blob, tu
import mq_cache
from pool_compare import projection
from pool_protocol import compiler_source_problem, encode

QUEUE_REF = re.compile(r"^refs/heads/gh-readonly-queue/main/[A-Za-z0-9._-]+$")
MAX_CHANGED = 60
MAX_FILE_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_AFFECTED_TUS = 192
SHARD_SIZE = 8


def _allowed_path(path):
    if not safe_path(path):
        return False
    if path.casefold().startswith("src/code/tools/"):
        return False
    return path.startswith("src/") or path.startswith("include/")


def _write_outputs(env, shards, has_shards, deferred=()):
    out_path = env.get("GITHUB_OUTPUT")
    if not out_path:
        return
    deferred = list(deferred)
    with Path(out_path).open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(f"shards={json.dumps(shards, separators=(',', ':'))}\n")
        stream.write(f"has_shards={'yes' if has_shards else 'no'}\n")
        stream.write(f"deferred_shards={json.dumps(deferred, separators=(',', ':'))}\n")
        stream.write(f"has_deferred={'yes' if deferred else 'no'}\n")


def _refuse(out_dir, env, base, head, tree, reason, *, total_tus=0):
    manifest = {
        "status": "refused",
        "reason": reason,
        "shards": [],
        "base": base,
        "head": head,
        "tree": tree,
        "total_tus": total_tus,
    }
    write(out_dir / "manifest.json", manifest)
    _write_outputs(env, [], False)
    return manifest


def parse_event(env):
    if env.get("GITHUB_EVENT_NAME") != "merge_group":
        raise ValueError("Expected GITHUB_EVENT_NAME=merge_group.")
    payload = read(env["GITHUB_EVENT_PATH"], 2 * 1024**2)
    group = payload.get("merge_group")
    if not isinstance(group, dict):
        raise ValueError("Missing merge_group object in event payload.")
    base_sha = group.get("base_sha", "")
    head_sha = group.get("head_sha", "")
    head_ref = group.get("head_ref", "")
    if not HEX40.fullmatch(base_sha) or not HEX40.fullmatch(head_sha):
        raise ValueError("Expected 40-hex base_sha and head_sha.")
    if (not isinstance(head_ref, str) or not QUEUE_REF.fullmatch(head_ref)
            or ".." in head_ref or head_ref.endswith((".", ".lock"))):
        raise ValueError("Unexpected merge_group head_ref.")
    base_ref = group.get("base_ref")
    if base_ref is not None and base_ref != "refs/heads/main":
        raise ValueError("Unexpected merge_group base_ref.")
    main_sha = env.get("BFME_MQ_MAIN_SHA", "")
    if main_sha:
        if not HEX40.fullmatch(main_sha):
            raise ValueError("Expected 40-hex BFME_MQ_MAIN_SHA.")
        base_sha = main_sha
    return base_sha, head_sha, head_ref


def event_base(env):
    """The queue's own base: main for the first entry, the previous entry's head after it."""
    group = read(env["GITHUB_EVENT_PATH"], 2 * 1024**2).get("merge_group") or {}
    base = group.get("base_sha", "")
    return base if isinstance(base, str) and HEX40.fullmatch(base) else ""


def _ancestor(git, older, newer):
    return git.run("merge-base", "--is-ancestor", older, newer, check=False).returncode == 0


def _deferrable(git, base_sha, head_sha, predecessor, old_files, environment, base_side, tu_digests,
                include_cache):
    """Units the predecessor entry compared with exactly these inputs, so its receipts can cover them."""
    if (not predecessor or predecessor in {base_sha, head_sha}
            or not _ancestor(git, base_sha, predecessor) or not _ancestor(git, predecessor, head_sha)):
        return set()
    paths = sorted(change.path for change in git.changes(base_sha, predecessor, validate=False))
    if not paths or len(paths) > MAX_CHANGED or not all(_allowed_path(path) for path in paths):
        return set()
    pred_files, pred_hashes = projection(git, predecessor)
    covered = (affected(old_files, paths, include_cache=include_cache)
               | affected(pred_files, paths, include_cache=include_cache))
    if len(covered) > MAX_AFFECTED_TUS:
        return set()
    pred_side = mq_cache.SourceSide(pred_files, pred_hashes, include_cache=include_cache)
    result = set()
    for path in covered & set(tu_digests):
        try:
            if mq_cache.tu_digest(environment, path, base_side, pred_side) == tu_digests[path]:
                result.add(path)
        except ValueError:
            continue
    return result


def _prepare_git(work_dir, repo_dir, base_sha, head_sha, head_ref, remote):
    git = Git(work_dir / "mq.git", initialize=True)
    repo_path = Path(repo_dir)
    git_dir = repo_path / ".git" if (repo_path / ".git").is_dir() else repo_path
    objects_dir = (git_dir / "objects").resolve(strict=True)
    (git.path / "objects/info/alternates").write_text(objects_dir.as_posix() + "\n", encoding="utf-8")
    shallow = git_dir / "shallow"
    if shallow.is_file():
        shutil.copyfile(shallow, git.path / "shallow")
    git.run("update-ref", "refs/ci/base", base_sha)
    if remote is not None:
        fetch_args = ["fetch", "-q", "--no-tags", "--no-write-fetch-head"]
        if str(remote).startswith(("http://", "https://")):
            fetch_args.append("--depth=128")
        fetch_args.extend(["--", str(remote), f"+{head_ref}:refs/ci/mq-head"])
        git.run(*fetch_args, timeout=120)
        fetched = git.rev("refs/ci/mq-head")
        if fetched != head_sha:
            raise GitFailure(f"Fetched {head_ref} resolved to {fetched}, expected {head_sha}.")
    return git


def plan_merge_group(out_dir, *, env=None, repo_dir=None, remote=None):
    env = os.environ if env is None else env
    out_dir = Path(out_dir)
    out_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    base_sha, head_sha, head_ref = parse_event(env)
    repo_root = Path.cwd() if repo_dir is None else Path(repo_dir)
    fetch_remote = f"https://github.com/{REPO}.git" if remote is None else remote

    with tempfile.TemporaryDirectory(prefix="bfme-mq-plan-") as tmp:
        git = _prepare_git(Path(tmp), repo_root, base_sha, head_sha, head_ref, fetch_remote)
        ancestry = git.run("merge-base", "--is-ancestor", base_sha, head_sha, check=False)
        if ancestry.returncode != 0:
            return _refuse(out_dir, env, base_sha, head_sha, "", "base_sha is not an ancestor of head_sha")
        head_tree = git.value("rev-parse", f"{head_sha}^{{tree}}")

        try:
            changes = git.changes(base_sha, head_sha, validate=False)
        except Refusal as exc:
            return _refuse(out_dir, env, base_sha, head_sha, head_tree, str(exc))

        if not changes:
            return _refuse(out_dir, env, base_sha, head_sha, head_tree, "Merge group contains no changed files")
        if len(changes) > MAX_CHANGED:
            return _refuse(out_dir, env, base_sha, head_sha, head_tree,
                           f"Merge group exceeds {MAX_CHANGED} changed files ({len(changes)})")

        changes_payload = []
        total_bytes = 0
        for change in changes:
            path, mode, oid = change.path, change.mode, change.oid
            if not _allowed_path(path):
                return _refuse(out_dir, env, base_sha, head_sha, head_tree, f"Disallowed path: {path}")
            if mode not in {"000000", "100644"}:
                return _refuse(out_dir, env, base_sha, head_sha, head_tree, f"Unsupported file mode for {path}: {mode}")
            if tu(path):
                expected_path = "expected/" + path[4:] + ".json"
                if git.run("cat-file", "-e", f"{base_sha}:{expected_path}", check=False).returncode != 0:
                    return _refuse(out_dir, env, base_sha, head_sha, head_tree, f"Missing expected ledger {expected_path}")
                if mode == "000000":
                    return _refuse(out_dir, env, base_sha, head_sha, head_tree, f"Affected TU missing on head: {path}")
            data = None
            if mode != "000000":
                data = blob(git, head_sha, path)
                if len(data) > MAX_FILE_BYTES:
                    return _refuse(out_dir, env, base_sha, head_sha, head_tree, f"File exceeds 1 MiB: {path}")
                total_bytes += len(data)
                if total_bytes > MAX_TOTAL_BYTES:
                    return _refuse(out_dir, env, base_sha, head_sha, head_tree, "Combined changed source exceeds 8 MiB")
                if b"\0" in data:
                    return _refuse(out_dir, env, base_sha, head_sha, head_tree, f"Binary or NUL byte in {path}")
                try:
                    data.decode("utf-8")
                except UnicodeDecodeError:
                    return _refuse(out_dir, env, base_sha, head_sha, head_tree, f"Non-UTF-8 source file: {path}")
                issue = compiler_source_problem(data)
                if issue:
                    rule, line = issue
                    return _refuse(out_dir, env, base_sha, head_sha, head_tree,
                                   f"Compiler source policy refused {path}:{line} ({rule})")
            changes_payload.append({
                "path": path,
                "mode": mode,
                "oid": oid,
                "blob": encode(data) if data is not None else None,
            })

        try:
            git.case_check(head_tree, changes)
        except Refusal as exc:
            return _refuse(out_dir, env, base_sha, head_sha, head_tree, str(exc))

        if git.tree_with(base_sha, changes) != head_tree:
            return _refuse(out_dir, env, base_sha, head_sha, head_tree,
                           "Reconstructed source tree does not match merge group tree")

        changed_paths = sorted(row["path"] for row in changes_payload)
        old_files, old_hashes = projection(git, base_sha)
        new_files, new_hashes = projection(git, head_sha)
        include_cache = {}
        affected_tus = sorted(
            affected(old_files, changed_paths, include_cache=include_cache)
            | affected(new_files, changed_paths, include_cache=include_cache)
        )

        if not affected_tus:
            manifest = {
                "status": "noop",
                "shards": [],
                "base": base_sha,
                "head": head_sha,
                "tree": head_tree,
                "total_tus": 0,
                "changed_count": len(changed_paths),
            }
            write(out_dir / "manifest.json", manifest)
            _write_outputs(env, [], False)
            return manifest

        if len(affected_tus) > MAX_AFFECTED_TUS:
            return _refuse(
                out_dir, env, base_sha, head_sha, head_tree,
                f"Too many affected translation units in one merge group (>{MAX_AFFECTED_TUS})",
                total_tus=len(affected_tus),
            )

        for path in affected_tus:
            expected_path = "expected/" + path[4:] + ".json"
            for rev, name, label in (
                (base_sha, expected_path, f"Missing expected ledger {expected_path}"),
                (base_sha, path, f"Affected TU missing on base: {path}"),
                (head_sha, path, f"Affected TU missing on head: {path}"),
            ):
                if git.run("cat-file", "-e", f"{rev}:{name}", check=False).returncode != 0:
                    return _refuse(out_dir, env, base_sha, head_sha, head_tree, label, total_tus=len(affected_tus))

        environment, tu_digests, cached, deferred = "", {}, {}, set()
        try:
            base_side = mq_cache.SourceSide(old_files, old_hashes, include_cache=include_cache)
            head_side = mq_cache.SourceSide(new_files, new_hashes, include_cache=include_cache)
            environment = mq_cache.environment_digest(git, base_sha)
            tu_digests = {path: mq_cache.tu_digest(environment, path, base_side, head_side)
                          for path in affected_tus}
            if env.get("BFME_MQ_RECEIPTS", "") != "no":
                store = env.get("BFME_MQ_STORE", "")
                if store:
                    cached = mq_cache.accept(mq_cache.load_receipts(Path(store) / mq_cache.RECEIPTS_FILE),
                                             tu_digests)
                deferred = _deferrable(git, base_sha, head_sha, event_base(env), old_files, environment,
                                       base_side, tu_digests, include_cache) - set(cached)
        except Exception as exc:  # noqa: BLE001 - receipts are optional; compile every unit on Boat
            print(f"Receipt digests unavailable ({type(exc).__name__}); compiling every unit.", file=sys.stderr)
            environment, tu_digests, cached, deferred = "", {}, {}, set()

        cur_policy = policy()
        immediate = [path for path in affected_tus if path not in deferred and path not in cached]
        later = [path for path in affected_tus if path in deferred]
        if cached:
            mq_cache.write_receipts(out_dir / "cached" / mq_cache.RECEIPTS_FILE, cached.values())
        chunks = ([immediate[i:i + SHARD_SIZE] for i in range(0, len(immediate), SHARD_SIZE)]
                  + [later[i:i + SHARD_SIZE] for i in range(0, len(later), SHARD_SIZE)])
        immediate_count = (len(immediate) + SHARD_SIZE - 1) // SHARD_SIZE
        shard_ids = list(range(immediate_count))
        deferred_ids = list(range(immediate_count, len(chunks)))
        shard_plans = {}
        for idx, shard_tus in enumerate(chunks):
            shard_dir = out_dir / f"shard-{idx}"
            shard_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            plan = {
                "version": 1,
                "repo": REPO_ID,
                "number": 1,
                "base": base_sha,
                "head": head_sha,
                "tree": head_tree,
                **PIN,
                "policy": cur_policy,
                "changed_paths": changed_paths,
                "request_paths": shard_tus,
                "changes": changes_payload,
            }
            plan_path = shard_dir / "plan.json"
            write(plan_path, plan)
            plan_hash = digest(plan_path.read_bytes())
            shard_plans[str(idx)] = plan_hash
            decision = {
                "version": 1,
                "repo": REPO_ID,
                "number": 1,
                "base": base_sha,
                "head": head_sha,
                "tree": head_tree,
                "kind": "compile",
                "plan": plan_hash,
            }
            write(shard_dir / "decision.json", decision)

        manifest = {
            "status": "planned",
            "shards": shard_ids,
            "base": base_sha,
            "head": head_sha,
            "tree": head_tree,
            "total_tus": len(affected_tus),
            "changed_count": len(changed_paths),
            "shard_plans": shard_plans,
            "shard_tus": {str(idx): shard_tus for idx, shard_tus in enumerate(chunks)},
            "environment": environment,
            "tu_digests": tu_digests,
            "cached": sorted(cached),
        }
        if deferred_ids:
            manifest["deferred"] = {"predecessor": event_base(env), "shards": deferred_ids}
        write(out_dir / "manifest.json", manifest)
        _write_outputs(env, shard_ids, bool(shard_ids), deferred_ids)
        return manifest


def main(out_dir):
    os.umask(0o077)
    plan_merge_group(out_dir)


if __name__ == "__main__":
    main(sys.argv[1])
