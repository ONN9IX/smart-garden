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


if __name__ == "__main__":
    unittest.main()
