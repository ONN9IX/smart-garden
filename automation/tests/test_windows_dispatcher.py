"""Synthetic lifecycle tests: never launches an agent or publishes anything."""
from datetime import datetime, timezone
import multiprocessing
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

WINDOWS = Path(__file__).resolve().parents[1] / "windows"
sys.path.insert(0, str(WINDOWS))
import dispatcher as d

BASE = "a" * 40
HEAD = "b" * 40
NOW = datetime(2026, 10, 9, tzinfo=timezone.utc)


def approval():
    return dict(id="synthetic-approval-207", repo=d.REPO, issue=207,
                base=BASE, branch="automation/ONN9IX-207-windows-dispatcher",
                paths=["automation/windows/example.py"],
                expires="2026-10-10T00:00:00+00:00", max_repairs=2)


def checks(head=HEAD):
    return [dict(name=n, head_sha=head, status="completed", conclusion="success") for n in d.CI]


def snapshot():
    a = approval()
    return dict(main=BASE, prs=[dict(repo=d.REPO, head_repo=d.REPO,
                branch=a["branch"], base="main", number=208, head=HEAD)], checks=[])


def delivery():
    a = approval()
    return d.Delivery(a["id"], a["issue"], a["base"], a["branch"])


MERGE = "c" * 40
ROOT = (1 << 3072) - 1


def merged_snapshot():
    event = snapshot()
    event.update(main=MERGE, merged=True, merge_sha=MERGE,
                 post_merge_checks=checks(MERGE))
    event["prs"][0].update(merged=True, merge_commit_sha=MERGE)
    evidence = dict(record=dict(approval_id=approval()["id"], repo=d.REPO,
                                issue=207, pr=208, head=HEAD, merge_sha=MERGE),
                    signature="synthetic-signature-oracle")
    return event, evidence


def hold_lock(path, ready):
    with d.global_lock(path):
        ready.set()
        ready.wait(30)  # Parent kills the process to simulate a crash.
        import time
        time.sleep(30)


class DispatcherTests(unittest.TestCase):
    def test_serial_queue_waits_for_owner_merge_and_post_merge_ci(self):
        active = delivery()
        candidate = approval() | dict(id="synthetic-approval-209", issue=209,
                                     branch="codex/issue-209", base="c" * 40)
        for state in ("READY", "RUNNING", "PR_PENDING", "CI_FIXING", "READY_FOR_MASTER_CHAT", "MERGE_PENDING", "POST_MERGE_CI", "BLOCKED"):
            active.state = state
            self.assertIs(d.next_delivery(active, [candidate]), active)
        active.state = "DONE"
        self.assertEqual(d.next_delivery(active, [candidate]).issue, 209)
        with self.assertRaises(d.Denied):
            d.next_delivery(None, [candidate, candidate])

    def test_restart_resumes_existing_pr(self):
        job = delivery()
        self.assertEqual(job.observe(approval(), snapshot()), "PR_PENDING")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            d.save_state(path, job)
            resumed = d.restore_state(path, approval())
        self.assertEqual(resumed.pr, 208)
        event = snapshot()
        event["checks"] = checks()
        self.assertEqual(resumed.observe(approval(), event), "READY_FOR_MASTER_CHAT")

    def test_crashed_running_state_blocks_and_audit_is_minimized(self):
        job = delivery()
        job.state = "RUNNING"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            d.save_state(path, job)
            self.assertEqual(d.restore_state(path, approval()).state, "BLOCKED")
            path.write_bytes(d.canonical(job.__dict__ | dict(repairs=99)))
            with self.assertRaises(d.Denied):
                d.restore_state(path, approval())
            audit = Path(tmp) / "audit.jsonl"
            d.audit(audit, job, NOW)
            self.assertEqual(set(d.load_json(audit)), {"approval_id", "issue", "state", "at"})

    def test_new_head_requires_new_checks_and_bounded_repairs(self):
        event = snapshot()
        event["checks"] = checks("c" * 40)
        job = delivery()
        self.assertEqual(job.observe(approval(), event), "PR_PENDING")
        event["ci_failed"] = True
        for _ in range(2):
            self.assertEqual(job.observe(approval(), event), "CI_FIXING")
            job.begin_repair(approval())
        self.assertEqual(job.observe(approval(), event), "BLOCKED")
        with self.assertRaises(d.Denied):
            job.begin_repair(approval())

    def test_changed_main_and_missing_pr_stop(self):
        event = snapshot()
        event["main"] = "c" * 40
        self.assertEqual(delivery().observe(approval(), event), "BLOCKED")
        job = delivery()
        job.observe(approval(), snapshot())
        with self.assertRaises(d.Denied):
            job.observe(approval(), dict(main=BASE, prs=[]))

    def test_merge_requires_owner_evidence_and_exact_post_merge_ci(self):
        event, evidence = merged_snapshot()
        with self.assertRaises(d.Denied):
            delivery().observe(approval(), event)
        event["owner_merge_verified"] = True
        with self.assertRaises(d.Denied):
            delivery().observe(approval(), event)
        job = delivery()
        event["post_merge_checks"] = checks()
        # Signature oracle only: real signature/tamper tests are separate.
        with patch.object(d, "verify_signature") as verifier:
            self.assertEqual(job.observe(approval(), event, merge_evidence=evidence,
                                         owner_modulus=ROOT), "POST_MERGE_CI")
            verifier.assert_called_once_with(evidence["record"], evidence["signature"], ROOT)
            event["post_merge_checks"] = checks(MERGE)
            self.assertEqual(job.observe(approval(), event, merge_evidence=evidence,
                                         owner_modulus=ROOT), "DONE")

    def test_ci_missing_duplicate_failed_skipped_and_new_head(self):
        self.assertTrue(d.ci_passed(checks(), HEAD))
        for invalid in (checks()[:-1], checks() + checks()[:1], checks("c" * 40), [{}] * 8):
            self.assertFalse(d.ci_passed(invalid, HEAD))
        for result in ("failure", "skipped", "neutral", None):
            items = checks()
            items[0]["conclusion"] = result
            self.assertFalse(d.ci_passed(items, HEAD))

    def test_global_lock_race_and_crash_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "global.lock")
            ready = multiprocessing.Event()
            child = multiprocessing.Process(target=hold_lock, args=(path, ready))
            child.start()
            try:
                self.assertTrue(ready.wait(10))
                with self.assertRaises(OSError):
                    with d.global_lock(path):
                        self.fail("second tick acquired lock")
            finally:
                child.terminate()
                child.join(10)
            with d.global_lock(path):
                self.assertTrue(Path(path).exists())

    def test_runtime_always_disabled_even_without_credentials(self):
        with self.assertRaisesRegex(d.Denied, "NO_GO"):
            d.require_execution()


if __name__ == "__main__":
    unittest.main()
