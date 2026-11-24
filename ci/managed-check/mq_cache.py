"""Content-addressed translation-unit comparison receipts for the merge queue.

A receipt records one fact: comparing translation unit X on the protected base
against X on a queue head passed, for the exact inputs named by its digest. The
digest binds:

- the trusted environment: every top-level entry of the base tree other than
  `src` and `include` (ci/, tools/, config/, expected/, baseline/, ...), the
  sealed compiler pins, the Boat runner label and this bundle's policy digest;
- on each side (base and head): the SHA-256 of every non-unit source file in the
  compiler projection (all headers, anywhere under `src/` or `include/`), plus
  the SHA-256 of X and of every `.c`/`.cpp` file X can reach through literal
  includes.

Any change to any of those inputs changes the digest, so a receipt can only be
reused for an identical comparison. Only passing shard verdicts produce
receipts. Every lookup fails open: a missing, malformed or mismatched receipt
sends its translation unit back to a Boat compile.

Receipts reach a queue entry two ways:

- A main-scoped store: an Actions cache entry under `STORE_KEY_PREFIX`
  holding one `receipts.json`. A merge_group run can restore caches saved on
  the default branch, so the planner reads it on a hosted runner and drops
  proven units before any Boat shard exists. Only default-branch runs can
  write it (`unit_digests` and `merge_store` serve such a writer).
- The predecessor entry: the queue runs each entry on its own
  `gh-readonly-queue/...` ref, and caches saved there are invisible to
  sibling entries. Receipts therefore also travel through the
  `bfme-mq-receipts` artifact of the predecessor entry's run of this same
  workflow, read with the run token.
"""
from collections import defaultdict, deque
import io
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from common import HEX40, HEX64, PIN, REPO, REPO_ID, RUNNER_LABEL, digest, encoded, policy, read, write

SCHEMA = "bfme-mq-tu-receipt-v1"
DIGEST_TAG = "bfme-mq-tu-v1"
ARTIFACT = "bfme-mq-receipts"
RECEIPTS_FILE = "receipts.json"
WORKFLOW_PATH = ".github/workflows/merge-queue-boat.yml"
STORE_KEY_PREFIX = "bfme-tu-verdict-v1-"
MAX_RECEIPTS = 4096
MAX_RECEIPTS_BYTES = 4 * 1024**2
MAX_ARTIFACT_BYTES = 8 * 1024**2
RECEIPT_KEYS = frozenset({"schema", "tu", "digest", "verdict", "producer", "seal"})
SOURCE_TREES = frozenset({"src", "include"})
WAIT_SECONDS = 20 * 60
APPEAR_SECONDS = 3 * 60
POLL_SECONDS = 15


def is_unit(path):
    return path.startswith("src/") and Path(path).suffix.lower() in {".c", ".cpp"}


def environment_digest(git, base):
    """Digest the trusted, non-source part of the protected base and the sealed tool identity."""
    listing = git.run("ls-tree", "--full-tree", base).stdout.decode("utf-8", "strict")
    entries = []
    for line in listing.splitlines():
        meta, _, name = line.partition("\t")
        if not name:
            raise ValueError("Unexpected git ls-tree output.")
        if name not in SOURCE_TREES:
            entries.append([name, meta])
    return digest(encoded({
        "tag": DIGEST_TAG,
        "tree": sorted(entries),
        "pin": PIN,
        "runner": RUNNER_LABEL,
        "policy": policy(),
    }))


class SourceSide:
    """One exact compiler projection (`pool_compare.projection`) and its literal include graph."""

    def __init__(self, files, hashes, *, include_cache=None, literal_includes=None):
        if literal_includes is None:
            from intake import literal_includes
        self.hashes = dict(hashes)
        self.headers = digest(encoded(sorted([path, sha] for path, sha in self.hashes.items()
                                             if not is_unit(path))))
        cache = {} if include_cache is None else include_cache
        aliases = defaultdict(set)
        for path in files:
            parts = path.casefold().split("/")
            for start in range(len(parts)):
                aliases["/".join(parts[start:])].add(path)
        # Same over-approximating resolution as `intake.affected`, followed forwards.
        self.edges = defaultdict(set)
        for path, content in files.items():
            if content not in cache:
                cache[content] = literal_includes(content)
            for name in cache[content]:
                pieces = name.split("/")
                label = "/".join(part for part in pieces if part not in {"", ".", ".."})
                targets = aliases[label]
                if ".." in pieces:
                    targets = targets | aliases[pieces[-1]]
                self.edges[path] |= targets

    def units(self, unit):
        seen, todo = {unit}, deque([unit])
        while todo:
            for target in self.edges.get(todo.popleft(), ()):
                if target not in seen:
                    seen.add(target)
                    todo.append(target)
        return sorted(path for path in seen if is_unit(path))

    def inputs(self, unit):
        if unit not in self.hashes:
            raise ValueError(f"Translation unit is absent from the projection: {unit}")
        return {"headers": self.headers, "units": [[path, self.hashes[path]] for path in self.units(unit)]}


def tu_digest(environment, unit, base_side, head_side):
    if not HEX64.fullmatch(str(environment)):
        raise ValueError("Expected a 64-hex environment digest.")
    return digest(encoded({
        "tag": DIGEST_TAG,
        "tu": unit,
        "env": environment,
        "base": base_side.inputs(unit),
        "head": head_side.inputs(unit),
    }))


def unit_digests(git, base, head, units):
    """Digest each unit for a base/head comparison straight from Git (for receipt writers)."""
    from pool_compare import projection
    cache = {}
    base_side = SourceSide(*projection(git, base), include_cache=cache)
    head_side = SourceSide(*projection(git, head), include_cache=cache)
    environment = environment_digest(git, base)
    return {unit: tu_digest(environment, unit, base_side, head_side) for unit in units}


def merge_store(*groups):
    """Combine receipt lists for a store, newest group first, one receipt per (unit, digest), capped."""
    merged, seen = [], set()
    for group in groups:
        for item in group:
            if not isinstance(item, dict):
                continue
            key = (item.get("tu"), item.get("digest"))
            if key in seen or not check_receipt(item, item.get("tu"), item.get("digest")):
                continue
            seen.add(key)
            merged.append(item)
            if len(merged) >= MAX_RECEIPTS:
                return merged
    return merged


def _seal(body):
    return digest(encoded({key: body[key] for key in sorted(RECEIPT_KEYS - {"seal"})}))


def make_receipt(unit, tu_sha, producer):
    if not is_unit(unit) or not HEX64.fullmatch(str(tu_sha)):
        raise ValueError("A receipt needs a translation unit and a 64-hex digest.")
    body = {"schema": SCHEMA, "tu": unit, "digest": tu_sha, "verdict": "pass", "producer": dict(producer)}
    body["seal"] = _seal(body)
    return body


def check_receipt(item, unit, expected):
    """Accept a receipt only for this exact unit, exact digest and a passing verdict."""
    try:
        return (isinstance(item, dict)
                and set(item) == RECEIPT_KEYS
                and item["schema"] == SCHEMA
                and item["verdict"] == "pass"
                and item["tu"] == unit
                and isinstance(expected, str) and HEX64.fullmatch(expected) is not None
                and item["digest"] == expected
                and isinstance(item["producer"], dict)
                and item["seal"] == _seal(item))
    except (TypeError, ValueError, KeyError):
        return False


def load_receipts(path):
    """Read a receipts file. Any malformed file yields no receipts."""
    path = Path(path)
    try:
        if not path.is_file() or path.stat().st_size > MAX_RECEIPTS_BYTES:
            return []
        return parse_receipts(path.read_bytes())
    except (OSError, ValueError):
        return []


def parse_receipts(raw):
    try:
        if len(raw) > MAX_RECEIPTS_BYTES:
            return []
        payload = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        return []
    items = payload.get("receipts")
    if not isinstance(items, list):
        return []
    return [item for item in items[:MAX_RECEIPTS] if isinstance(item, dict)]


def accept(receipts, expected):
    """Map each expected unit to the first receipt that proves its exact digest."""
    accepted = {}
    for item in receipts:
        unit = item.get("tu") if isinstance(item, dict) else None
        if isinstance(unit, str) and unit in expected and unit not in accepted:
            if check_receipt(item, unit, expected[unit]):
                accepted[unit] = item
    return accepted


def write_receipts(path, receipts):
    rows = sorted(list(receipts)[:MAX_RECEIPTS], key=lambda item: (item["tu"], item["digest"]))
    Path(path).parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    write(path, {"schema": SCHEMA, "receipts": rows})


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class ArtifactReader:
    """Read-only GitHub client for this workflow's runs and artifacts."""

    def __init__(self, token=None, opener=None):
        self.token = os.environ.get("BFME_MQ_READ_TOKEN", "") if token is None else token
        if not self.token:
            raise ValueError("Missing BFME_MQ_READ_TOKEN.")
        self.opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())

    def _request(self, path):
        request = urllib.request.Request(
            "https://api.github.com/repos/" + REPO + "/" + path,
            headers={"Authorization": "Bearer " + self.token,
                     "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28",
                     "User-Agent": "bfme-merge-queue-receipts"})
        return self.opener.open(request, timeout=30)

    def json(self, path):
        with self._request(path) as reply:
            raw = reply.read(MAX_ARTIFACT_BYTES + 1)
        if len(raw) > MAX_ARTIFACT_BYTES:
            raise ValueError("GitHub reply exceeded its limit.")
        return json.loads(raw)

    def runs(self, head_sha):
        query = urllib.parse.urlencode({"event": "merge_group", "head_sha": head_sha, "per_page": 20})
        return self.json("actions/runs?" + query).get("workflow_runs") or []

    def artifacts(self, run_id):
        query = urllib.parse.urlencode({"name": ARTIFACT, "per_page": 20})
        return self.json(f"actions/runs/{int(run_id)}/artifacts?" + query).get("artifacts") or []

    def download(self, artifact_id):
        try:
            with self._request(f"actions/artifacts/{int(artifact_id)}/zip") as reply:
                raw = reply.read(MAX_ARTIFACT_BYTES + 1)
        except urllib.error.HTTPError as exc:
            location = exc.headers.get("Location", "") if exc.code in {301, 302, 303, 307, 308} else ""
            if not location.startswith("https://"):
                raise
            # Blob storage URLs are pre-signed; never forward the token off api.github.com.
            plain = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
            with plain.open(urllib.request.Request(location, headers={"User-Agent": "bfme-merge-queue-receipts"}),
                            timeout=60) as reply:
                raw = reply.read(MAX_ARTIFACT_BYTES + 1)
        if len(raw) > MAX_ARTIFACT_BYTES:
            raise ValueError("Receipt artifact exceeded its limit.")
        return raw


def trusted_run(run, head_sha):
    return (isinstance(run, dict)
            and run.get("event") == "merge_group"
            and run.get("path") == WORKFLOW_PATH
            and run.get("head_sha") == head_sha
            and (run.get("repository") or {}).get("id") == REPO_ID
            and (run.get("head_repository") or {}).get("id") == REPO_ID)


def receipts_from_zip(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = [info for info in archive.infolist() if info.filename == RECEIPTS_FILE]
        if len(names) != 1 or names[0].file_size > MAX_RECEIPTS_BYTES:
            return []
        with archive.open(names[0]) as stream:
            return parse_receipts(stream.read(MAX_RECEIPTS_BYTES + 1))


def predecessor_receipts(reader, head_sha, *, wait=WAIT_SECONDS, poll=POLL_SECONDS,
                         clock=time.monotonic, sleep=time.sleep, log=print):
    """Wait for the predecessor entry's receipts; return [] once its runs finish without any."""
    started = clock()
    deadline = started + wait
    while True:
        runs = [run for run in reader.runs(head_sha) if trusted_run(run, head_sha)]
        collected, active = [], False
        for run in runs:
            for artifact in reader.artifacts(run["id"]):
                if (isinstance(artifact, dict) and artifact.get("name") == ARTIFACT
                        and not artifact.get("expired")
                        and isinstance(artifact.get("size_in_bytes"), int)
                        and artifact["size_in_bytes"] <= MAX_ARTIFACT_BYTES):
                    collected.extend(receipts_from_zip(reader.download(artifact["id"])))
            active = active or run.get("status") != "completed"
        if collected:
            return collected
        if runs and not active:
            log("The predecessor entry finished without receipts.")
            return []
        if not runs and clock() >= started + APPEAR_SECONDS:
            log("No run of this workflow exists for the predecessor entry.")
            return []
        if clock() >= deadline:
            log("Timed out waiting for predecessor receipts.")
            return []
        sleep(poll)


def _write_outputs(env, shards):
    out_path = env.get("GITHUB_OUTPUT")
    if not out_path:
        return
    with Path(out_path).open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(f"shards={json.dumps(shards, separators=(',', ':'))}\n")
        stream.write(f"has_shards={'yes' if shards else 'no'}\n")


def collect(plans_dir, out_dir, *, env=None, reader=None, **wait_options):
    """Resolve deferred shards: reuse proven receipts, return the shards still needing Boat."""
    env = os.environ if env is None else env
    plans_dir, out_dir = Path(plans_dir), Path(out_dir)
    manifest = read(plans_dir / "manifest.json", 2 * 1024**2)
    deferred = manifest.get("deferred") or {}
    shard_ids = [sid for sid in deferred.get("shards") or [] if type(sid) is int]
    shard_tus = manifest.get("shard_tus") or {}
    digests = manifest.get("tu_digests") or {}
    expected = {unit: digests.get(unit) for sid in shard_ids for unit in shard_tus.get(str(sid), [])}
    accepted = {}
    predecessor = deferred.get("predecessor", "")
    if expected and HEX40.fullmatch(str(predecessor)):
        try:
            reader = ArtifactReader() if reader is None else reader
            accepted = accept(predecessor_receipts(reader, predecessor, **wait_options), expected)
        except Exception as exc:  # noqa: BLE001 - every failure falls back to a Boat compile
            print(f"Predecessor receipts unavailable ({type(exc).__name__}); compiling on Boat.", file=sys.stderr)
            accepted = {}
    write_receipts(out_dir / RECEIPTS_FILE, accepted.values())
    needed = [sid for sid in shard_ids
              if not shard_tus.get(str(sid)) or any(unit not in accepted for unit in shard_tus[str(sid)])]
    _write_outputs(env, needed)
    print(f"Reused {len(accepted)} of {len(expected)} deferred translation unit receipts; "
          f"{len(needed)} of {len(shard_ids)} deferred shard(s) still compile on Boat.")
    return needed, accepted


def main(argv):
    os.umask(0o077)
    if len(argv) != 3 or argv[0] != "collect":
        raise SystemExit("usage: mq_cache.py collect <plans-dir> <out-dir>")
    try:
        collect(argv[1], argv[2])
    except Exception as exc:  # noqa: BLE001 - fail open: every deferred shard compiles
        print(f"Receipt collection failed ({type(exc).__name__}); compiling every deferred shard.", file=sys.stderr)
        manifest = read(Path(argv[1]) / "manifest.json", 2 * 1024**2)
        shards = [sid for sid in (manifest.get("deferred") or {}).get("shards") or [] if type(sid) is int]
        write_receipts(Path(argv[2]) / RECEIPTS_FILE, [])
        _write_outputs(os.environ, shards)


if __name__ == "__main__":
    main(sys.argv[1:])
