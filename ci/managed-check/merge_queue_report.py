"""Aggregate sharded Boat verdicts for a GitHub Merge Queue group and post one status."""
import os
from pathlib import Path
import sys

from common import CONTEXT, HEX40, HEX64, REPO_ID, digest, read
from github_status import GitHub
import mq_cache

MAX_DESCRIPTION = 140


def _clip(text, limit=MAX_DESCRIPTION):
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[:limit - 3].rstrip() + "..."


def _event_shas(env):
    event_path = env.get("GITHUB_EVENT_PATH")
    if not event_path or not Path(event_path).is_file():
        return None, None
    payload = read(event_path, 2 * 1024**2)
    group = payload.get("merge_group") or {}
    base = group.get("base_sha")
    head = group.get("head_sha")
    main_sha = env.get("BFME_MQ_MAIN_SHA", "")
    if HEX40.fullmatch(str(main_sha or "")):
        base = main_sha
    return (base if HEX40.fullmatch(str(base or "")) else None,
            head if HEX40.fullmatch(str(head or "")) else None)


def _find_verdict(verdicts_dir, shard):
    for subdir in (f"verdict-{shard}", f"bfme-mq-verdict-{shard}"):
        candidate = verdicts_dir / subdir / "verdict.json"
        if candidate.is_file():
            return candidate
    return None


def _failure_detail(report):
    for key in ("messages", "diagnostics"):
        entries = report.get(key)
        if isinstance(entries, list) and entries:
            return str(entries[0])
    lost = report.get("lost")
    if isinstance(lost, list) and lost and isinstance(lost[0], dict):
        row = lost[0]
        return f"{row.get('path', 'unknown')} at {row.get('rva', '?')}: {row.get('old')} -> {row.get('new')}"
    rules = report.get("rules")
    if isinstance(rules, list) and rules:
        return "Refused by rules: " + ", ".join(str(r) for r in rules[:4])
    return f"Comparison verdict: {report.get('kind', 'unknown')}"


def _write_summary(env, lines):
    summary_path = env.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with Path(summary_path).open("a", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(lines) + "\n")


def _plan_units(plans_dir, shard, expected_plan):
    """Translation units of one shard, read from its plan only when the plan hash matches."""
    path = plans_dir / f"shard-{shard}" / "plan.json"
    try:
        raw = path.read_bytes()
        if len(raw) > 18 * 1024**2 or digest(raw) != expected_plan:
            return []
        units = read(path, 18 * 1024**2).get("request_paths")
    except (OSError, ValueError, AttributeError):
        return []
    return units if isinstance(units, list) and all(isinstance(unit, str) for unit in units) else []


def report_merge_group(plans_dir, verdicts_dir, *, env=None, api=None, reused_dir=None, receipts_out=None):
    env = os.environ if env is None else env
    plans_dir, verdicts_dir = Path(plans_dir), Path(verdicts_dir)
    event_base, event_head = _event_shas(env)
    api = GitHub() if api is None else api

    manifest_path = plans_dir / "manifest.json"
    if not manifest_path.is_file():
        if not event_head:
            raise ValueError("Missing both manifest.json and merge_group head_sha.")
        desc = "Merge queue planner failed before producing a plan"
        api.status({"head": event_head}, "failure", _clip(desc), context=CONTEXT)
        _write_summary(env, ["### BFME II Merge Queue Boat", "", f"- **Result:** Failure — {desc}"])
        return 1

    manifest = read(manifest_path, 2 * 1024**2)
    base = manifest.get("base", "")
    head = manifest.get("head", "")
    tree = manifest.get("tree", "")
    status = manifest.get("status", "")
    if not HEX40.fullmatch(base) or not HEX40.fullmatch(head):
        raise ValueError("Malformed manifest base/head SHAs.")
    if (event_head and head != event_head) or (event_base and base != event_base):
        raise ValueError("Manifest SHAs do not match merge_group event.")

    if status == "noop":
        desc = f"No translation units affected on main {base[:12]}"
        api.status({"head": head}, "success", _clip(desc), context=CONTEXT)
        _write_summary(env, [
            "### BFME II Merge Queue Boat",
            "",
            f"- **Base:** `{base[:12]}`",
            f"- **Head:** `{head[:12]}`",
            f"- **Result:** Pass — {desc}",
        ])
        return 0

    if status == "refused":
        reason = manifest.get("reason") or "Merge queue group refused"
        desc = _clip(f"Refused: {reason}")
        api.status({"head": head}, "failure", desc, context=CONTEXT)
        _write_summary(env, [
            "### BFME II Merge Queue Boat",
            "",
            f"- **Base:** `{base[:12]}`",
            f"- **Head:** `{head[:12]}`",
            f"- **Result:** Refused — {reason}",
        ])
        return 1

    if status != "planned":
        desc = _clip(f"Unexpected merge queue plan status: {status}")
        api.status({"head": head}, "failure", desc, context=CONTEXT)
        _write_summary(env, ["### BFME II Merge Queue Boat", "", f"- **Result:** Failure — {desc}"])
        return 1

    shards = manifest.get("shards")
    shard_plans = manifest.get("shard_plans")
    total_tus = manifest.get("total_tus", 0)
    deferred = manifest.get("deferred") or {}
    deferred_shards = deferred.get("shards") if isinstance(deferred, dict) else None
    deferred_shards = [] if deferred_shards is None else deferred_shards
    tu_digests = manifest.get("tu_digests") or {}
    cached_units = manifest.get("cached") or []
    all_shards = (shards + deferred_shards
                  if isinstance(shards, list) and isinstance(deferred_shards, list) else None)
    if (all_shards is None or not isinstance(cached_units, list) or not (all_shards or cached_units)
            or not isinstance(shard_plans, dict) or not isinstance(tu_digests, dict)
            or any(type(shard) is not int for shard in all_shards)
            or len(set(all_shards)) != len(all_shards)):
        desc = "Malformed planned manifest shards"
        api.status({"head": head}, "failure", desc, context=CONTEXT)
        _write_summary(env, ["### BFME II Merge Queue Boat", "", f"- **Result:** Failure — {desc}"])
        return 1

    reused = {}
    if reused_dir is not None and tu_digests:
        reused = mq_cache.accept(mq_cache.load_receipts(Path(reused_dir) / mq_cache.RECEIPTS_FILE), tu_digests)
    # Units the planner proved from main-scoped receipts; re-verified here against the manifest digests.
    cached = {}
    if cached_units and tu_digests:
        cached = mq_cache.accept(mq_cache.load_receipts(plans_dir / "cached" / mq_cache.RECEIPTS_FILE),
                                 {unit: tu_digests.get(unit) for unit in cached_units if isinstance(unit, str)})
    producer_run = str(env.get("GITHUB_RUN_ID", ""))
    receipts = dict(reused) | cached

    failures = []
    rows = []
    total_gained = 0
    total_judged = 0
    reused_tus = len(cached)
    if cached_units:
        missing = [unit for unit in cached_units if unit not in cached]
        if missing:
            failures.append(f"Cached receipt did not verify for {missing[0]}")
            rows.append(f"| cache | Error | {len(missing)} cached receipt(s) did not verify |")
        else:
            rows.append(f"| cache | Reused | {len(cached)} TUs proven by main-scoped receipts |")
    covered = set(cached)
    for shard in all_shards:
        expected_plan = shard_plans.get(str(shard))
        units = _plan_units(plans_dir, shard, expected_plan)
        covered.update(units)
        vpath = _find_verdict(verdicts_dir, shard)
        if vpath is None and shard in deferred_shards and units and all(unit in reused for unit in units):
            reused_tus += len(units)
            rows.append(f"| {shard} | Reused | {len(units)} TUs proven by predecessor receipts |")
            continue
        if vpath is None:
            msg = f"Shard {shard}: missing verdict"
            failures.append(msg)
            rows.append(f"| {shard} | Missing | Verdict artifact not found |")
            continue
        try:
            verdict = read(vpath, 256 * 1024)
        except (OSError, ValueError):
            msg = f"Shard {shard}: unreadable verdict"
            failures.append(msg)
            rows.append(f"| {shard} | Error | Unreadable verdict JSON |")
            continue

        binding_ok = (
            isinstance(verdict, dict)
            and verdict.get("version") == 1
            and verdict.get("repo") == REPO_ID
            and verdict.get("base") == base
            and verdict.get("head") == head
            and verdict.get("tree") == tree
            and verdict.get("plan") == expected_plan
        )
        if not binding_ok:
            msg = f"Shard {shard}: verdict binding mismatch"
            failures.append(msg)
            rows.append(f"| {shard} | Error | Binding or plan hash mismatch |")
            continue

        report = verdict.get("report")
        counts = verdict.get("counts") or {}
        if isinstance(report, dict) and report.get("kind") == "ok":
            judged = report.get("judged", 0)
            gained = counts.get("gained", 0)
            total_judged += judged if isinstance(judged, int) else 0
            total_gained += gained if isinstance(gained, int) else 0
            rows.append(f"| {shard} | Pass | {judged} TUs judged (+{gained} matched) |")
            # A passing shard proves each of its units: the verdict is the union of per-unit rules.
            for unit in units:
                unit_sha = tu_digests.get(unit)
                if unit not in receipts and isinstance(unit_sha, str) and HEX64.fullmatch(unit_sha):
                    receipts[unit] = mq_cache.make_receipt(
                        unit, unit_sha, {"run_id": producer_run, "head": head, "plan": expected_plan})
        else:
            detail = _failure_detail(report if isinstance(report, dict) else {})
            failures.append(f"Shard {shard}: {detail}")
            rows.append(f"| {shard} | Fail | {detail} |")

    if "cached" in manifest and len(covered) != total_tus:
        failures.append(f"Planned translation units are not all covered ({len(covered)} of {total_tus})")
        rows.append(f"| all | Error | {len(covered)} of {total_tus} planned TUs covered |")

    if receipts_out is not None:
        mq_cache.write_receipts(Path(receipts_out) / mq_cache.RECEIPTS_FILE, receipts.values())

    summary = [
        "### BFME II Merge Queue Boat",
        "",
        f"- **Base:** `{base[:12]}`",
        f"- **Head:** `{head[:12]}`",
        f"- **Shards:** {len(all_shards)} ({total_tus} TUs planned, {total_judged} judged, "
        f"{reused_tus} reused from receipts, +{total_gained} matched)",
        "",
        "| Shard | Status | Details |",
        "| --- | --- | --- |",
        *rows,
    ]
    _write_summary(env, summary)

    if not failures:
        reuse_note = f", {reused_tus} reused" if reused_tus else ""
        desc = _clip(f"BFME II comparison passed: {total_tus} TUs across {len(all_shards)} shard(s)"
                     f"{reuse_note} (main {base[:12]})")
        api.status({"head": head}, "success", desc, context=CONTEXT)
        return 0

    desc = _clip(f"{failures[0]} (main {base[:12]})")
    api.status({"head": head}, "failure", desc, context=CONTEXT)
    return 1


def main(argv):
    if len(argv) not in {2, 4}:
        raise SystemExit("usage: merge_queue_report.py <plans> <verdicts> [<reused-receipts> <receipts-out>]")
    reused_dir, receipts_out = (argv[2], argv[3]) if len(argv) == 4 else (None, None)
    raise SystemExit(report_merge_group(argv[0], argv[1], reused_dir=reused_dir, receipts_out=receipts_out))


if __name__ == "__main__":
    main(sys.argv[1:])
