"""Offline signed-ledger regression; synthetic keys only."""
import base64
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "windows"))
import approval_store as store
import dispatcher as d
from test_windows_dispatcher import BASE, NOW, approval


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


    def test_symlink_and_hardlink_lock_cannot_modify_external_file(self):
        import os
        envelope, root = fixture()
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            victim = Path(outside) / "unrelated"
            victim.write_bytes(b"")
            storage = store.SyntheticApprovalStore(tmp)
            try:
                os.symlink(victim, storage.lock)
            except (OSError, NotImplementedError):
                self.skipTest("synthetic symlink permission unavailable")
            with self.assertRaises(d.Denied):
                storage.reserve(envelope, root, main=BASE, now=NOW)
            self.assertEqual(victim.read_bytes(), b"")
            storage.lock.unlink()
            try:
                os.link(victim, storage.lock)
            except (OSError, NotImplementedError):
                self.skipTest("synthetic hardlink permission unavailable")
            with self.assertRaises(d.Denied):
                storage.reserve(envelope, root, main=BASE, now=NOW)
            self.assertEqual(victim.read_bytes(), b"")



import json
import os
from unittest.mock import patch


class A3DeliveryStoreTests(unittest.TestCase):
    def test_missing_corrupt_or_partial_ledger_never_resets(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = store.SyntheticDeliveryStore(tmp)
            with self.assertRaises(d.Denied):
                with storage.transaction():
                    pass
            storage.initialize()
            storage.path.unlink()
            with self.assertRaises(d.Denied):
                with storage.transaction():
                    pass
            with self.assertRaises(d.Denied):
                storage.initialize()
        with tempfile.TemporaryDirectory() as tmp:
            storage = store.SyntheticDeliveryStore(tmp)
            original = storage._commit
            count = 0
            def crash(state):
                nonlocal count
                count += 1
                if count == 2:
                    raise d.Denied('synthetic persistence failure')
                return original(state)
            with patch.object(storage, '_commit', crash):
                with self.assertRaises(d.Denied):
                    storage.initialize()
            self.assertTrue(storage.marker.exists())
            with self.assertRaises(d.Denied):
                storage.initialize()

    def test_duplicate_json_hardlink_and_marker_spoof_denied(self):
        for attack in ('duplicate', 'hardlink', 'marker'):
            with self.subTest(attack=attack), tempfile.TemporaryDirectory() as tmp:
                storage = store.SyntheticDeliveryStore(tmp)
                storage.initialize()
                if attack == 'duplicate':
                    storage.path.write_text('{"schema":1,"schema":1,"revoked":[],"consumed":[],"delivery":null}')
                elif attack == 'hardlink':
                    os.link(storage.path, Path(tmp) / 'alias')
                else:
                    storage.marker.write_text('{"schema":2,"approved":true}')
                with self.assertRaises(d.Denied):
                    with storage.transaction():
                        pass

    def test_atomic_write_fsync_failure_is_denial_not_acknowledgement(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = store.SyntheticDeliveryStore(tmp)
            storage.initialize()
            with storage.transaction() as state:
                state['revoked'] = [approval()['id']]
                with patch('os.fsync', side_effect=OSError('synthetic failure')):
                    with self.assertRaises(d.Denied):
                        storage.commit(state)
            self.assertEqual(json.loads(storage.path.read_bytes())['revoked'], [])

    def test_no_untrusted_or_unbounded_ids_in_journal(self):
        for value in (['owner@example.test'], ['repeated-id-000001'] * 2,
                      ['z' * 16, 'a' * 16], [None], [[]]):
            with self.subTest(value=value), self.assertRaises(d.Denied):
                store.validate_delivery_ledger({'schema': 1, 'revoked': value,
                                                'consumed': [], 'delivery': None})


if __name__ == "__main__":
    unittest.main()
