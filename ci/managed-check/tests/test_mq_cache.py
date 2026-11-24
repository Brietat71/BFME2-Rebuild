"""Content-addressed merge queue receipts: digests, receipt checks, collection and end-to-end reuse."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ci/managed-check"))
sys.path.insert(1, str(ROOT / "ci/managed-check/tests"))
sys.path.insert(2, str(ROOT / "ci/managed-nt2"))

import common  # noqa: E402
import merge_queue_plan as mq_plan  # noqa: E402
import merge_queue_report as mq_report  # noqa: E402
import mq_cache  # noqa: E402
from gitrepo import Git  # noqa: E402
from pool_protocol import encode  # noqa: E402
from test_merge_queue import QUEUE_REF, FakeGitHub, commit_queue, make_repo, mq_env, read_outputs, run_git  # noqa: E402

ENV = "e" * 64
OTHER_QUEUE_REF = "refs/heads/gh-readonly-queue/main/pr-41-0123456789abcdef"


def side(files):
    """A SourceSide over plain text files, as `pool_compare.projection` would encode them."""
    encoded = {path: encode(text.encode("utf-8")) for path, text in files.items()}
    hashes = {path: common.digest(text.encode("utf-8")) for path, text in files.items()}
    return mq_cache.SourceSide(encoded, hashes)


BASE_FILES = {
    "include/Common.h": "int common();\n",
    "src/Game/Local.h": "int local();\n",
    "src/A.cpp": '#include "Common.h"\nint a() { return 0; }\n',
    "src/B.cpp": '#include "Game/Local.h"\nint b() { return 0; }\n',
    "src/Inl.cpp": "int inl() { return 0; }\n",
    "src/C.cpp": '#include "Inl.cpp"\nint c() { return 0; }\n',
}


class DigestTests(unittest.TestCase):
    def digest(self, unit, base=None, head=None, env=ENV):
        return mq_cache.tu_digest(env, unit, side(base or BASE_FILES), side(head or BASE_FILES))

    def test_stacked_entries_share_the_digest_of_an_untouched_unit(self):
        entry1 = BASE_FILES | {"src/A.cpp": '#include "Common.h"\nint a() { return 1; }\n'}
        entry2 = entry1 | {"src/B.cpp": '#include "Game/Local.h"\nint b() { return 1; }\n'}
        self.assertEqual(self.digest("src/A.cpp", head=entry1), self.digest("src/A.cpp", head=entry2))
        self.assertNotEqual(self.digest("src/B.cpp", head=entry1), self.digest("src/B.cpp", head=entry2))

    def test_any_input_change_changes_the_digest(self):
        reference = self.digest("src/C.cpp")
        cases = {
            "base unit blob": {"base": BASE_FILES | {"src/C.cpp": '#include "Inl.cpp"\nint c() { return 2; }\n'}},
            "head unit blob": {"head": BASE_FILES | {"src/C.cpp": '#include "Inl.cpp"\nint c() { return 3; }\n'}},
            "include header": {"head": BASE_FILES | {"include/Common.h": "int common(); // x\n"}},
            "src header": {"base": BASE_FILES | {"src/Game/Local.h": "int local(); // y\n"}},
            "new header path": {"head": BASE_FILES | {"include/New.h": "int fresh();\n"}},
            "included unit": {"head": BASE_FILES | {"src/Inl.cpp": "int inl() { return 9; }\n"}},
            "environment": {"env": "f" * 64},
        }
        seen = {reference}
        for name, change in cases.items():
            with self.subTest(change=name):
                value = self.digest("src/C.cpp", **change)
                self.assertNotEqual(value, reference)
                seen.add(value)
        self.assertEqual(len(seen), len(cases) + 1)

    def test_unrelated_unit_does_not_change_the_digest(self):
        head = BASE_FILES | {"src/B.cpp": '#include "Game/Local.h"\nint b() { return 5; }\n'}
        self.assertEqual(self.digest("src/A.cpp"), self.digest("src/A.cpp", head=head))

    def test_missing_unit_or_bad_environment_is_refused(self):
        with self.assertRaises(ValueError):
            self.digest("src/Missing.cpp")
        with self.assertRaises(ValueError):
            self.digest("src/A.cpp", env="not-a-digest")


class EnvironmentDigestTests(unittest.TestCase):
    def test_trusted_trees_and_pins_bind_the_environment(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            work, remote, base = make_repo(root, {
                "src/A.cpp": "int a() { return 0; }\n",
                "include/A.h": "int a();\n",
                "config/map.json": "{}\n",
                "expected/A.cpp.json": "{}\n",
                "tools/judge/judge.py": "pass\n",
                "ci/managed-check/x.py": "pass\n",
            })
            git = Git(work / ".git")
            reference = mq_cache.environment_digest(git, base)
            source_only = commit_queue(work, remote, {"src/A.cpp": "int a() { return 1; }\n",
                                                      "include/A.h": "int a(); // doc\n"})
            self.assertEqual(mq_cache.environment_digest(git, source_only), reference)
            seen = {reference}
            for path in ("config/map.json", "expected/A.cpp.json", "tools/judge/judge.py", "ci/managed-check/x.py"):
                with self.subTest(path=path):
                    commit = commit_queue(work, remote, {path: f"changed {path}\n"})
                    value = mq_cache.environment_digest(git, commit)
                    self.assertNotIn(value, seen)
                    seen.add(value)
            with mock.patch.object(mq_cache, "PIN", dict(common.PIN, image_sha256="0" * 64)):
                self.assertNotIn(mq_cache.environment_digest(git, base), seen)
            with mock.patch.object(mq_cache, "RUNNER_LABEL", "boat-small/from=other"):
                self.assertNotIn(mq_cache.environment_digest(git, base), seen)


class ReceiptTests(unittest.TestCase):
    UNIT, SHA = "src/A.cpp", "a" * 64

    def receipt(self):
        return mq_cache.make_receipt(self.UNIT, self.SHA, {"run_id": "1", "head": "2" * 40, "plan": "b" * 64})

    def test_exact_receipt_is_accepted(self):
        self.assertTrue(mq_cache.check_receipt(self.receipt(), self.UNIT, self.SHA))
        self.assertEqual(mq_cache.accept([self.receipt()], {self.UNIT: self.SHA}), {self.UNIT: self.receipt()})

    def test_failed_or_tampered_receipts_are_rejected(self):
        failed = self.receipt() | {"verdict": "fail"}
        failed["seal"] = mq_cache._seal(failed)
        resealed_digest = self.receipt() | {"digest": "c" * 64}
        resealed_digest["seal"] = mq_cache._seal(resealed_digest)
        cases = {
            "failed verdict": failed,
            "error verdict": self.receipt() | {"verdict": "error"},
            "digest mismatch": resealed_digest,
            "broken seal": self.receipt() | {"seal": "0" * 64},
            "payload edit": self.receipt() | {"producer": {"run_id": "999"}},
            "other unit": self.receipt() | {"tu": "src/B.cpp"},
            "extra key": self.receipt() | {"extra": 1},
            "wrong schema": self.receipt() | {"schema": "v0"},
            "not a dict": ["src/A.cpp"],
        }
        for name, item in cases.items():
            with self.subTest(case=name):
                self.assertFalse(mq_cache.check_receipt(item, self.UNIT, self.SHA))
                self.assertEqual(mq_cache.accept([item], {self.UNIT: self.SHA}), {})
        self.assertFalse(mq_cache.check_receipt(self.receipt(), self.UNIT, "not-hex"))

    def test_only_passing_receipts_can_be_made(self):
        with self.assertRaises(ValueError):
            mq_cache.make_receipt("include/A.h", self.SHA, {})
        with self.assertRaises(ValueError):
            mq_cache.make_receipt(self.UNIT, "short", {})
        self.assertEqual(self.receipt()["verdict"], "pass")

    def test_corrupt_receipt_files_yield_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "receipts.json"
            for raw in (b"{not json", b"[]", json.dumps({"schema": "other", "receipts": []}).encode(),
                        json.dumps({"schema": mq_cache.SCHEMA, "receipts": "x"}).encode(),
                        b" " * (mq_cache.MAX_RECEIPTS_BYTES + 1)):
                with self.subTest(raw=raw[:20]):
                    path.write_bytes(raw)
                    self.assertEqual(mq_cache.load_receipts(path), [])
            self.assertEqual(mq_cache.load_receipts(Path(td) / "absent.json"), [])
            mq_cache.write_receipts(path, [self.receipt()])
            self.assertEqual(mq_cache.load_receipts(path), [self.receipt()])


def receipts_zip(receipts, name=mq_cache.RECEIPTS_FILE):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, json.dumps({"schema": mq_cache.SCHEMA, "receipts": receipts}))
    return buffer.getvalue()


class FakeReader:
    def __init__(self, polls):
        """`polls` is a list of (runs, {run_id: [artifact, ...]}, {artifact_id: zip_bytes}) per poll."""
        self.polls = list(polls)
        self.current = None
        self.calls = 0

    def runs(self, head_sha):
        self.current = self.polls[min(self.calls, len(self.polls) - 1)]
        self.calls += 1
        return self.current[0]

    def artifacts(self, run_id):
        return self.current[1].get(run_id, [])

    def download(self, artifact_id):
        return self.current[2][artifact_id]


def trusted_run(head, status="completed", **overrides):
    return {"id": 7, "event": "merge_group", "path": mq_cache.WORKFLOW_PATH, "head_sha": head, "status": status,
            "repository": {"id": common.REPO_ID}, "head_repository": {"id": common.REPO_ID}} | overrides


def artifact(size=100):
    return {"id": 70, "name": mq_cache.ARTIFACT, "expired": False, "size_in_bytes": size}


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class PredecessorReceiptTests(unittest.TestCase):
    PRED = "4" * 40
    RECEIPT = mq_cache.make_receipt("src/A.cpp", "a" * 64, {"run_id": "7"})

    def collect(self, reader, **kwargs):
        clock = Clock()
        return mq_cache.predecessor_receipts(reader, self.PRED, clock=clock, sleep=clock.sleep,
                                             log=lambda _msg: None, **kwargs), reader.calls

    def test_waits_for_an_active_predecessor_then_reads_its_receipts(self):
        reader = FakeReader([
            ([trusted_run(self.PRED, "in_progress")], {}, {}),
            ([trusted_run(self.PRED, "in_progress")], {}, {}),
            ([trusted_run(self.PRED)], {7: [artifact()]}, {70: receipts_zip([self.RECEIPT])}),
        ])
        receipts, calls = self.collect(reader)
        self.assertEqual(receipts, [self.RECEIPT])
        self.assertEqual(calls, 3)

    def test_untrusted_runs_are_ignored(self):
        for name, run in (("other workflow", trusted_run(self.PRED, path=".github/workflows/evil.yml")),
                          ("other event", trusted_run(self.PRED, event="pull_request")),
                          ("other head", trusted_run("5" * 40)),
                          ("fork head", trusted_run(self.PRED, head_repository={"id": 1}))):
            with self.subTest(case=name):
                reader = FakeReader([([run], {7: [artifact()]}, {70: receipts_zip([self.RECEIPT])})])
                receipts, _ = self.collect(reader)
                self.assertEqual(receipts, [])

    def test_finished_without_receipts_or_never_started_gives_up(self):
        receipts, calls = self.collect(FakeReader([([trusted_run(self.PRED)], {}, {})]))
        self.assertEqual((receipts, calls), ([], 1))
        receipts, calls = self.collect(FakeReader([([], {}, {})]))
        self.assertEqual(receipts, [])
        self.assertLessEqual(calls, mq_cache.APPEAR_SECONDS // mq_cache.POLL_SECONDS + 2)

    def test_times_out_on_a_stuck_predecessor(self):
        reader = FakeReader([([trusted_run(self.PRED, "in_progress")], {}, {})])
        receipts, calls = self.collect(reader, wait=60, poll=15)
        self.assertEqual(receipts, [])
        self.assertEqual(calls, 5)

    def test_oversized_or_misnamed_artifacts_are_skipped(self):
        reader = FakeReader([([trusted_run(self.PRED)], {7: [artifact(size=mq_cache.MAX_ARTIFACT_BYTES + 1)]},
                              {70: receipts_zip([self.RECEIPT])})])
        self.assertEqual(self.collect(reader)[0], [])
        reader = FakeReader([([trusted_run(self.PRED)], {7: [artifact()]},
                              {70: receipts_zip([self.RECEIPT], name="other.json")})])
        self.assertEqual(self.collect(reader)[0], [])


class QueueFixture(unittest.TestCase):
    """Main with units A and B; queue entry 1 edits A."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)
        files = {"include/Stub.h": "int stub();\n"}
        for name in ("A", "B"):
            files[f"src/{name}.cpp"] = f'#include "Stub.h"\nint {name.lower()}() {{ return 0; }}\n'
            files[f"expected/{name}.cpp.json"] = "{}\n"
        self.work, self.remote, self.main = make_repo(self.root, files)
        self.entry1 = commit_queue(self.work, self.remote, {"src/A.cpp": '#include "Stub.h"\nint a() { return 1; }\n'},
                                   queue_ref=OTHER_QUEUE_REF)
        self.checkout = self.root / "checkout"
        run_git(self.root, "clone", "-q", "--depth=1", f"file://{self.remote.as_posix()}", str(self.checkout))

    def tearDown(self):
        self._td.cleanup()

    def plan(self, name, base_event, head, queue_ref=QUEUE_REF, **extra):
        tmp = self.root / name
        tmp.mkdir()
        env = mq_env(tmp, base_event, head, head_ref=queue_ref) | {"BFME_MQ_MAIN_SHA": self.main} | extra
        manifest = mq_plan.plan_merge_group(tmp / "plans", env=env, repo_dir=self.checkout, remote=str(self.remote))
        return tmp, env, manifest

    def verdict(self, tmp, manifest, shard, kind="ok"):
        path = tmp / "verdicts" / f"bfme-mq-verdict-{shard}"
        path.mkdir(parents=True)
        common.write(path / "verdict.json", {
            "version": 1, "repo": common.REPO_ID, "number": 1, "base": manifest["base"],
            "head": manifest["head"], "tree": manifest["tree"], "plan": manifest["shard_plans"][str(shard)],
            "report": {"kind": kind, "judged": len(manifest["shard_tus"][str(shard)]), "messages": ["boom"]},
            "counts": {"gained": 0}, "functions": []})

    def report(self, tmp, env, reused=None):
        api = FakeGitHub()
        rc = mq_report.report_merge_group(tmp / "plans", tmp / "verdicts", env=env, api=api,
                                          reused_dir=reused, receipts_out=tmp / "receipts")
        return rc, api.calls[0], mq_cache.load_receipts(tmp / "receipts" / mq_cache.RECEIPTS_FILE)

    def run_entry1(self, kind="ok"):
        tmp, env, manifest = self.plan("entry1", self.main, self.entry1, queue_ref=OTHER_QUEUE_REF)
        self.assertEqual(manifest["shards"], [0])
        self.assertNotIn("deferred", manifest)
        self.assertEqual(read_outputs(env["GITHUB_OUTPUT"])["has_deferred"], "no")
        self.verdict(tmp, manifest, 0, kind)
        return self.report(tmp, env)

    def collect(self, tmp, receipts):
        reader = FakeReader([([trusted_run(self.entry1)], {7: [artifact()]}, {70: receipts_zip(receipts)})])
        clock = Clock()
        needed, _ = mq_cache.collect(tmp / "plans", tmp / "reused", env={"GITHUB_OUTPUT": str(tmp / "collect.txt")},
                                     reader=reader, clock=clock, sleep=clock.sleep, log=lambda _m: None)
        return needed, read_outputs(tmp / "collect.txt")


class StackedQueueTests(QueueFixture):
    """Plan, collect and report two stacked queue entries against one main."""

    def test_partial_hit_defers_only_the_predecessor_unit(self):
        rc, status, receipts = self.run_entry1()
        self.assertEqual((rc, status[1]), (0, "success"))
        self.assertEqual([item["tu"] for item in receipts], ["src/A.cpp"])

        head = commit_queue(self.work, self.remote, {"src/B.cpp": '#include "Stub.h"\nint b() { return 1; }\n'})
        tmp, env, manifest = self.plan("entry2", self.entry1, head)
        self.assertEqual(manifest["shard_tus"], {"0": ["src/B.cpp"], "1": ["src/A.cpp"]})
        self.assertEqual(manifest["shards"], [0])
        self.assertEqual(manifest["deferred"], {"predecessor": self.entry1, "shards": [1]})
        outputs = read_outputs(env["GITHUB_OUTPUT"])
        self.assertEqual((outputs["shards"], outputs["deferred_shards"], outputs["has_deferred"]), ("[0]", "[1]", "yes"))
        self.assertEqual(receipts[0]["digest"], manifest["tu_digests"]["src/A.cpp"])

        needed, collected = self.collect(tmp, receipts)
        self.assertEqual((needed, collected["has_shards"]), ([], "no"))
        self.verdict(tmp, manifest, 0)
        rc, status, emitted = self.report(tmp, env, reused=tmp / "reused")
        self.assertEqual((rc, status[1]), (0, "success"))
        self.assertIn("1 reused", status[2])
        self.assertEqual(sorted(item["tu"] for item in emitted), ["src/A.cpp", "src/B.cpp"])
        summary = Path(env["GITHUB_STEP_SUMMARY"]).read_text(encoding="utf-8")
        self.assertIn("| 1 | Reused |", summary)

    def test_zero_hits_fall_back_to_a_boat_compile(self):
        self.run_entry1()
        head = commit_queue(self.work, self.remote, {"src/B.cpp": '#include "Stub.h"\nint b() { return 1; }\n'})
        tmp, env, manifest = self.plan("entry2", self.entry1, head)
        needed, collected = self.collect(tmp, [])
        self.assertEqual((needed, collected["shards"]), ([1], "[1]"))
        # Without the fallback verdict the deferred shard is missing: fail closed.
        self.verdict(tmp, manifest, 0)
        rc, status, _ = self.report(tmp, env, reused=tmp / "reused")
        self.assertEqual(rc, 1)
        self.assertIn("Shard 1: missing verdict", status[2])
        self.verdict(tmp, manifest, 1)
        rc, status, emitted = self.report(tmp, env, reused=tmp / "reused")
        self.assertEqual((rc, status[1]), (0, "success"))
        self.assertEqual(len(emitted), 2)

    def test_tampered_or_stale_receipts_fall_back(self):
        _, _, receipts = self.run_entry1()
        head = commit_queue(self.work, self.remote, {"src/B.cpp": '#include "Stub.h"\nint b() { return 1; }\n'})
        tmp, env, manifest = self.plan("entry2", self.entry1, head)
        forged = dict(receipts[0], digest="0" * 64)
        forged["seal"] = mq_cache._seal(forged)
        broken = dict(receipts[0], seal="1" * 64)
        needed, _ = self.collect(tmp, [forged, broken])
        self.assertEqual(needed, [1])
        # The report re-verifies receipts on its own; planting one in the reused folder cannot cover a shard.
        mq_cache.write_receipts(tmp / "reused" / mq_cache.RECEIPTS_FILE, [forged])
        self.verdict(tmp, manifest, 0)
        rc, status, _ = self.report(tmp, env, reused=tmp / "reused")
        self.assertEqual(rc, 1)
        self.assertIn("Shard 1: missing verdict", status[2])

    def test_failed_shard_produces_no_receipts(self):
        rc, status, receipts = self.run_entry1(kind="regression")
        self.assertEqual((rc, status[1], receipts), (1, "failure", []))

    def test_full_hit_needs_no_boat_shard(self):
        _, _, receipts = self.run_entry1()
        # A pull request already contained in its predecessor leaves nothing new to compile.
        head = commit_queue(self.work, self.remote, {})
        tmp, env, manifest = self.plan("entry2", self.entry1, head)
        self.assertEqual(manifest["shards"], [])
        self.assertEqual(manifest["deferred"]["shards"], [0])
        outputs = read_outputs(env["GITHUB_OUTPUT"])
        self.assertEqual((outputs["has_shards"], outputs["has_deferred"]), ("no", "yes"))
        needed, _ = self.collect(tmp, receipts)
        self.assertEqual(needed, [])
        rc, status, emitted = self.report(tmp, env, reused=tmp / "reused")
        self.assertEqual((rc, status[1]), (0, "success"))
        self.assertEqual([item["tu"] for item in emitted], ["src/A.cpp"])

    def test_header_change_or_kill_switch_disables_deferral(self):
        head = commit_queue(self.work, self.remote, {"include/Stub.h": "int stub(); // doc\n"})
        _, _, manifest = self.plan("header", self.entry1, head)
        self.assertNotIn("deferred", manifest)
        self.assertEqual(len(manifest["shard_tus"]["0"]), 2)
        _, env, manifest = self.plan("off", self.entry1, head, BFME_MQ_RECEIPTS="no")
        self.assertNotIn("deferred", manifest)
        self.assertEqual(read_outputs(env["GITHUB_OUTPUT"])["has_deferred"], "no")

    def test_collection_failure_compiles_every_deferred_shard(self):
        _, _, receipts = self.run_entry1()
        head = commit_queue(self.work, self.remote, {"src/B.cpp": '#include "Stub.h"\nint b() { return 1; }\n'})
        tmp, _, _ = self.plan("entry2", self.entry1, head)

        class Broken:
            def runs(self, head_sha):
                raise OSError("network down")

        needed, accepted = mq_cache.collect(tmp / "plans", tmp / "reused",
                                            env={"GITHUB_OUTPUT": str(tmp / "c.txt")}, reader=Broken())
        self.assertEqual((needed, accepted), ([1], {}))
        self.assertEqual(read_outputs(tmp / "c.txt")["has_shards"], "yes")
        self.assertEqual(mq_cache.load_receipts(tmp / "reused" / mq_cache.RECEIPTS_FILE), [])


class MainScopedStoreTests(QueueFixture):
    """Receipts restored from a default-branch cache resolve units on the hosted planner."""

    def store(self, head, units, *, digest_override=None):
        digests = mq_cache.unit_digests(Git(self.remote), self.main, head, units)
        store = self.root / f"store-{head[:8]}"
        receipts = [mq_cache.make_receipt(unit, digest_override or sha, {"run_id": "main-scope"})
                    for unit, sha in digests.items()]
        mq_cache.write_receipts(store / mq_cache.RECEIPTS_FILE, receipts)
        return store, digests

    def test_writer_digests_match_the_planner_and_skip_every_boat_shard(self):
        store, digests = self.store(self.entry1, ["src/A.cpp"])
        tmp, env, manifest = self.plan("entry1", self.main, self.entry1, queue_ref=OTHER_QUEUE_REF,
                                       BFME_MQ_STORE=str(store))
        self.assertEqual(manifest["tu_digests"], digests)
        self.assertEqual((manifest["shards"], manifest["cached"], manifest["shard_tus"]), ([], ["src/A.cpp"], {}))
        outputs = read_outputs(env["GITHUB_OUTPUT"])
        self.assertEqual((outputs["has_shards"], outputs["has_deferred"]), ("no", "no"))
        rc, status, emitted = self.report(tmp, env)
        self.assertEqual((rc, status[1]), (0, "success"))
        self.assertIn("1 reused", status[2])
        self.assertEqual([item["tu"] for item in emitted], ["src/A.cpp"])

    def test_partial_store_hit_compiles_only_the_rest(self):
        head = commit_queue(self.work, self.remote, {"src/B.cpp": '#include "Stub.h"\nint b() { return 1; }\n'})
        store, _ = self.store(head, ["src/A.cpp"])
        tmp, env, manifest = self.plan("entry2", self.entry1, head, BFME_MQ_STORE=str(store))
        self.assertEqual(manifest["cached"], ["src/A.cpp"])
        self.assertEqual(manifest["shard_tus"], {"0": ["src/B.cpp"]})
        self.assertNotIn("deferred", manifest)
        self.verdict(tmp, manifest, 0)
        rc, status, emitted = self.report(tmp, env)
        self.assertEqual((rc, status[1]), (0, "success"))
        self.assertEqual(sorted(item["tu"] for item in emitted), ["src/A.cpp", "src/B.cpp"])

    def test_stale_or_tampered_store_receipts_fall_back(self):
        store, _ = self.store(self.main, ["src/A.cpp"])  # digest of an unchanged A: stale for entry1
        _, _, manifest = self.plan("stale", self.main, self.entry1, queue_ref=OTHER_QUEUE_REF,
                                   BFME_MQ_STORE=str(store))
        self.assertEqual((manifest["cached"], manifest["shards"]), ([], [0]))
        store, _ = self.store(self.entry1, ["src/A.cpp"])
        tmp, env, manifest = self.plan("tampered", self.main, self.entry1, queue_ref=OTHER_QUEUE_REF,
                                       BFME_MQ_STORE=str(store))
        self.assertEqual(manifest["cached"], ["src/A.cpp"])
        planted = common.read(tmp / "plans/cached/receipts.json")
        planted["receipts"][0]["digest"] = "0" * 64
        common.write(tmp / "plans/cached/receipts.json", planted)
        rc, status, _ = self.report(tmp, env)
        self.assertEqual((rc, status[1]), (1, "failure"))
        self.assertIn("Cached receipt did not verify for src/A.cpp", status[2])

    def test_merge_store_keeps_newest_valid_receipt_per_digest(self):
        first = mq_cache.make_receipt("src/A.cpp", "a" * 64, {"run_id": "2"})
        older = mq_cache.make_receipt("src/A.cpp", "a" * 64, {"run_id": "1"})
        other = mq_cache.make_receipt("src/B.cpp", "b" * 64, {"run_id": "1"})
        broken = dict(other, seal="0" * 64)
        self.assertEqual(mq_cache.merge_store([first, broken], [older, other]), [first, other])


class WorkflowTests(unittest.TestCase):
    def test_receipt_jobs_are_wired_and_least_privileged(self):
        import yaml
        wf = yaml.safe_load((ROOT / ".github/workflows/merge-queue-boat.yml").read_text(encoding="utf-8"))
        jobs = wf["jobs"]
        self.assertEqual(jobs["reuse"]["permissions"], {"actions": "read", "contents": "read"})
        self.assertEqual(jobs["boat-fallback"]["permissions"], {"contents": "read"})
        self.assertEqual(jobs["boat"]["steps"], jobs["boat-fallback"]["steps"])
        self.assertEqual(jobs["report"]["needs"], ["plan", "boat", "reuse", "boat-fallback"])
        self.assertIn("needs.plan.outputs.deferred_shards", jobs["boat-fallback"]["strategy"]["matrix"]["shard"])
        report_run = "\n".join(step.get("run", "") for step in jobs["report"]["steps"])
        self.assertIn("bfme-mq-reused", report_run)
        uploads = [step["with"]["name"] for step in jobs["report"]["steps"]
                   if str(step.get("uses", "")).startswith("actions/upload-artifact")]
        self.assertEqual(uploads, [mq_cache.ARTIFACT])
        restores = [step for step in jobs["plan"]["steps"]
                    if str(step.get("uses", "")).startswith("actions/cache/restore@")]
        self.assertEqual(len(restores), 1)
        self.assertTrue(restores[0]["continue-on-error"])
        self.assertEqual(restores[0]["with"]["restore-keys"].strip(), mq_cache.STORE_KEY_PREFIX)
        names = [step.get("name") for step in jobs["plan"]["steps"]]
        self.assertLess(names.index(restores[0]["name"]), names.index("Build sharded Boat comparison plans"))
        self.assertFalse(any("actions/cache/save" in str(step.get("uses", ""))
                             for job in jobs.values() for step in job.get("steps", [])))


if __name__ == "__main__":
    unittest.main()
