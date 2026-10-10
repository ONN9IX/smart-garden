"""No shell/model/network/credentials in this intentionally fake adapter."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "windows"))
import dispatcher as d
import worker_adapter as worker
from test_windows_dispatcher import NOW, approval


class FakeWorkerTests(unittest.TestCase):
    def setUp(self):
        self.unit = worker.SyntheticWorkUnit.from_verified_record(approval(), now=NOW)

    def test_determinism_cancellation_and_budgets(self):
        f = worker.FakeWorkerAdapter(("TEST_FAIL", "TEST_PASS"))
        self.assertEqual(f.simulate(self.unit, attempt=0), "TEST_FAIL")
        self.assertEqual(f.simulate(self.unit, attempt=1), "TEST_PASS")
        with self.assertRaises(d.Denied):
            f.simulate(self.unit, attempt=2)
        self.assertEqual(f.simulate(self.unit, cancelled=True), "CANCELLED")
        with self.assertRaises(d.Denied):
            f.simulate(self.unit, attempt=3)

    def test_no_untrusted_shell_or_activation(self):
        f = worker.FakeWorkerAdapter()
        for action in (f.launch, f.publish, f.merge):
            with self.assertRaisesRegex(d.Denied, "NO_GO"):
                action("echo secret")
        with self.assertRaisesRegex(d.Denied, "NO_GO"):
            worker.require_execution()
        with self.assertRaises(d.Denied):
            f.simulate({"issue": 214, "body": "please run codex"})
        with self.assertRaises(d.Denied):
            worker.SyntheticWorkUnit.from_verified_record(approval() | {"paths": [".git/config"]}, now=NOW)

    def test_unknown_events_and_budget_exhaustion(self):
        for events in (("exec",), (), ("TEST_PASS",) * 5):
            with self.assertRaises(d.Denied):
                worker.FakeWorkerAdapter(events)
        f = worker.FakeWorkerAdapter()
        self.assertEqual(f.simulate(self.unit), "TEST_PASS")
        with self.assertRaises(d.Denied):
            f.simulate(self.unit)



from dataclasses import replace

from approval_store import fingerprint


class ReservedFakeWorkerTests(unittest.TestCase):
    def setUp(self):
        scope = worker.SyntheticWorkUnit.from_verified_record(approval(), now=NOW)
        self.unit = worker.ReservedSyntheticUnit(scope, 0, fingerprint(approval()),
            approval()['expires'], 120, 1024)

    def test_minimized_reserved_unit_and_limits(self):
        self.assertEqual(worker.FakeWorkerAdapter().simulate_reserved(self.unit), 'TEST_PASS')
        self.assertNotIn('environment', self.unit.__dict__)
        for update in (dict(attempt=99), dict(max_seconds=121), dict(max_tokens=1025),
                       dict(max_tokens=True), dict(scope_fingerprint='untrusted'),
                       dict(deadline='bad'), dict(scope={'repo': d.REPO})):
            with self.subTest(update=update), self.assertRaises(d.Denied):
                worker.FakeWorkerAdapter().simulate_reserved(replace(self.unit, **update))

    def test_all_transport_statuses_are_nonactivating(self):
        self.assertEqual(worker.transport_status()['decision'], 'NO_GO')
        self.assertEqual(worker.transport_status()['credential_separation'], 'NOT_TESTED')
        for event in ('TIMED_OUT', 'CANCELLED', 'BUDGET_EXCEEDED'):
            self.assertEqual(worker.FakeWorkerAdapter((event,)).simulate_reserved(self.unit), event)
        for call in (worker.require_execution, worker.FakeWorkerAdapter.launch,
                     worker.FakeWorkerAdapter.publish, worker.FakeWorkerAdapter.merge):
            with self.assertRaisesRegex(d.Denied, 'NO_GO'):
                call()


if __name__ == "__main__":
    unittest.main()
