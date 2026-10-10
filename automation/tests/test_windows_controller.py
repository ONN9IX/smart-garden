"""Offline controller lifecycle; source snapshots are synthetic, not trusted GitHub."""
import base64
from datetime import timedelta
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "windows"))
import controller_core as core
import dispatcher as d
from test_windows_dispatcher import approval, BASE, NOW, checks, snapshot, merged_snapshot, MERGE


def root_fixture(name="synthetic-signature.json"):
    f = d.load_json(Path(d.__file__).with_name(name))
    return int.from_bytes(base64.urlsafe_b64decode(f["n"]), "big"), f["signature"]


class ControllerCoreTests(unittest.TestCase):
    def setUp(self):
        root, signature = root_fixture()
        self.root = root
        self.envelope = {"record": approval(), "signature": signature}

    def tick(self, core_, event, **kwargs):
        return core_.tick(envelope=self.envelope, public_root=self.root,
                          main=event["main"], snapshot=event, now=NOW, **kwargs)

    def test_deterministic_offline_dry_run(self):
        first = core.SyntheticControllerCore.dry_run()
        self.assertEqual(first, core.SyntheticControllerCore.dry_run())
        self.assertEqual(first["decision"], "NO_GO")
        with self.assertRaisesRegex(d.Denied, "NO_GO"):
            core.require_execution()

    def test_resume_existing_pr_and_exact_ci(self):
        with tempfile.TemporaryDirectory() as temp:
            first = core.SyntheticControllerCore(temp)
            self.assertEqual(self.tick(first, snapshot()), "PR_PENDING")
            second = core.SyntheticControllerCore(temp)
            event = snapshot()
            event["checks"] = checks()
            self.assertEqual(self.tick(second, event), "READY_FOR_MASTER_CHAT")
            event["checks"][0]["head_sha"] = MERGE
            self.assertEqual(self.tick(second, event), "PR_PENDING")

    def test_signature_spoof_and_changed_main_block(self):
        with tempfile.TemporaryDirectory() as temp:
            control = core.SyntheticControllerCore(temp)
            with self.assertRaises(d.Denied):
                control.tick(envelope={"number": 214, "comment": "owner approved"},
                             public_root=self.root, main=BASE, snapshot=snapshot(), now=NOW)
            event = snapshot()
            event["main"] = MERGE
            with self.assertRaises(d.Denied):
                self.tick(control, event)

    def test_signed_merge_requires_exact_post_ci_and_timeout(self):
        with tempfile.TemporaryDirectory() as temp:
            control = core.SyntheticControllerCore(temp, post_merge_timeout=timedelta(seconds=2))
            self.tick(control, snapshot())
            event, evidence = merged_snapshot()
            root, signature = root_fixture("synthetic-merge-signature.json")
            evidence["signature"] = signature
            event["post_merge_checks"] = checks()
            self.assertEqual(self.tick(control, event, merge_evidence=evidence,
                                       merge_root=root), "POST_MERGE_CI")
            self.assertEqual(control.tick(envelope=self.envelope, public_root=self.root,
                snapshot=event, main=event["main"], now=NOW + timedelta(seconds=3),
                merge_evidence=evidence, merge_root=root), "BLOCKED")
            event["post_merge_checks"] = checks(MERGE)
            self.assertEqual(self.tick(control, event, merge_evidence=evidence,
                                       merge_root=root), "BLOCKED")

    def test_signed_merge_after_all_eight_can_finish(self):
        with tempfile.TemporaryDirectory() as temp:
            control = core.SyntheticControllerCore(temp)
            self.tick(control, snapshot())
            event, evidence = merged_snapshot()
            root, signature = root_fixture("synthetic-merge-signature.json")
            evidence["signature"] = signature
            self.assertEqual(self.tick(control, event, merge_evidence=evidence,
                                       merge_root=root), "DONE")


    def test_late_success_cannot_bypass_existing_post_merge_deadline(self):
        with tempfile.TemporaryDirectory() as temp:
            control = core.SyntheticControllerCore(temp, post_merge_timeout=timedelta(seconds=2))
            self.tick(control, snapshot())
            event, evidence = merged_snapshot()
            root, signature = root_fixture("synthetic-merge-signature.json")
            evidence["signature"] = signature
            event["post_merge_checks"] = checks()  # pending on merge SHA
            self.assertEqual(self.tick(control, event, merge_evidence=evidence,
                                       merge_root=root), "POST_MERGE_CI")
            event["post_merge_checks"] = checks(MERGE)  # too late
            self.assertEqual(control.tick(envelope=self.envelope, public_root=self.root,
                snapshot=event, main=MERGE, now=NOW + timedelta(seconds=3),
                merge_evidence=evidence, merge_root=root), "BLOCKED")
            self.assertEqual(self.tick(control, event, merge_evidence=evidence,
                                       merge_root=root), "BLOCKED")

    def test_durable_deadline_survives_regressed_state_and_crash(self):
        with tempfile.TemporaryDirectory() as temp:
            control = core.SyntheticControllerCore(temp, post_merge_timeout=timedelta(seconds=2))
            self.tick(control, snapshot())
            event, evidence = merged_snapshot()
            root, signature = root_fixture("synthetic-merge-signature.json")
            evidence["signature"] = signature
            event["post_merge_checks"] = checks()  # starts the deadline
            self.assertEqual(self.tick(control, event, merge_evidence=evidence,
                                       merge_root=root), "POST_MERGE_CI")
            # An unmerged snapshot must never rewind an already-merged delivery.
            with self.assertRaises(d.Denied):
                self.tick(control, snapshot())
            # Simulate crash/partial recovery: state was rolled back after
            # deadline fsync but before durable state update.
            approval_record = self.envelope["record"]
            stale = d.Delivery(approval_record["id"], approval_record["issue"],
                               approval_record["base"], approval_record["branch"])
            stale.state = "PR_PENDING"
            d.save_state(control.state_file, stale)
            event["post_merge_checks"] = checks(MERGE)
            self.assertEqual(control.tick(envelope=self.envelope, public_root=self.root,
                snapshot=event, main=MERGE, now=NOW + timedelta(seconds=3),
                merge_evidence=evidence, merge_root=root), "BLOCKED")

    def test_malformed_snapshot_is_bounded_denial_not_key_error(self):
        valid = snapshot()
        fake_pr = valid["prs"][0]
        malformed = (
            {"main": BASE},
            {"main": BASE, "prs": [], "checks": None},
            {"main": BASE, "prs": {}, "checks": []},
            {"main": BASE, "prs": [{}], "checks": []},
            {"main": BASE, "prs": [fake_pr | {"head": None}], "checks": []},
            {"main": BASE, "prs": [fake_pr | {"number": True}], "checks": []},
            {"main": BASE, "prs": [fake_pr], "checks": [{}]},
            {"main": BASE, "prs": [fake_pr], "checks": ["fake"]},
            {"main": BASE, "prs": [fake_pr], "checks": [], "merged": "true"},
            {"main": BASE, "prs": [fake_pr], "checks": [], "merged": True},
            {"main": BASE, "prs": [fake_pr], "checks": [], "untrusted": True},
        )
        with tempfile.TemporaryDirectory() as temp:
            control = core.SyntheticControllerCore(temp)
            for bad in malformed:
                with self.subTest(snapshot=repr(bad)[:70]), self.assertRaises(d.Denied):
                    control.tick(envelope=self.envelope, public_root=self.root,
                                 snapshot=bad, main=BASE, now=NOW)

    def test_controller_lock_link_cannot_write_outside_fixture(self):
        import os
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as external:
            victim = Path(external) / "unrelated"
            victim.write_bytes(b"")
            control = core.SyntheticControllerCore(temp)
            try:
                os.symlink(victim, control.lock)
            except (OSError, NotImplementedError):
                self.skipTest("synthetic symlink permission unavailable")
            with self.assertRaises(d.Denied):
                self.tick(control, snapshot())
            self.assertEqual(victim.read_bytes(), b"")


if __name__ == "__main__":
    unittest.main()