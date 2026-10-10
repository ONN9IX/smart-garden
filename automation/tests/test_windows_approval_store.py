"""Offline signed-ledger regression; synthetic keys only."""
import base64
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "windows"))
import approval_store as store
import dispatcher as d
from test_windows_dispatcher import approval, BASE, NOW


def fixture():
    f = d.load_json(Path(d.__file__).with_name("synthetic-signature.json"))
    root = int.from_bytes(base64.urlsafe_b64decode(f["n"]), "big")
    return {"record": approval(), "signature": f["signature"]}, root


class OfflineApprovalStoreTests(unittest.TestCase):
    def test_signature_revocation_replay_consume(self):
        envelope, root = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            storage = store.SyntheticApprovalStore(tmp)
            self.assertEqual(storage.reserve(envelope, root, main=BASE, now=NOW), approval())
            self.assertEqual(storage.check(envelope, root, main=BASE, now=NOW), approval())
            with self.assertRaises(d.Denied):
                storage.reserve(envelope, root, main=BASE, now=NOW)
            storage.consume(approval()["id"])
            for fn in (storage.reserve, storage.check):
                with self.assertRaises(d.Denied):
                    fn(envelope, root, main=BASE, now=NOW)

    def test_tampered_foreign_expired_and_fake_issue(self):
        envelope, root = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            storage = store.SyntheticApprovalStore(tmp)
            for bad in ({"number": 214, "labels": ["ai:ready"]},
                        envelope | {"signature": "AAAA"},
                        {"record": approval() | {"issue": 214}, "signature": envelope["signature"]}):
                with self.assertRaises(d.Denied):
                    storage.reserve(bad, root, main=BASE, now=NOW)
            with self.assertRaises(d.Denied):
                storage.reserve(envelope, root, main="f" * 40, now=NOW)
            with self.assertRaises(d.Denied):
                storage.reserve(envelope, root, main=BASE, now=datetime(2026, 10, 11, tzinfo=timezone.utc))

    def test_revocation_and_corrupt_ledger(self):
        envelope, root = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            storage = store.SyntheticApprovalStore(tmp)
            storage.reserve(envelope, root, main=BASE, now=NOW)
            storage.revoke(approval()["id"])
            with self.assertRaises(d.Denied):
                storage.check(envelope, root, main=BASE, now=NOW)
            storage.path.write_text('{"revoked":[],"revoked":[],"consumed":[],"reserved":{}}')
            with self.assertRaises(d.Denied):
                storage.reserve(envelope, root, main=BASE, now=NOW)

    def test_duplicate_workers_and_fail_closed_live(self):
        envelope, root = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            first = store.SyntheticApprovalStore(tmp)
            second = store.SyntheticApprovalStore(tmp)
            first.reserve(envelope, root, main=BASE, now=NOW)
            with self.assertRaises(d.Denied):
                second.reserve(envelope, root, main=BASE, now=NOW)
            with self.assertRaises(d.Denied):
                store.require_live_store()


if __name__ == "__main__":
    unittest.main()
