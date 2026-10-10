"""No shell/model/network/credentials in this intentionally fake adapter."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "windows"))
import dispatcher as d
import worker_adapter as worker
from test_windows_dispatcher import approval, NOW


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


if __name__ == "__main__":
    unittest.main()
