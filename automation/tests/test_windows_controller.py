"""Offline controller lifecycle; source snapshots are synthetic, not trusted GitHub."""
import base64
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "windows"))
import controller_core as core
import dispatcher as d
from test_windows_dispatcher import (
    BASE,
    HEAD,
    MERGE,
    NOW,
    approval,
    checks,
    merged_snapshot,
    snapshot,
)


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

    def test_deadline_directory_sync_precedes_state_commit(self):
        import os
        import stat
        from unittest.mock import patch
        if os.name == "nt":
            self.skipTest("native Windows directory durability not witnessed")
        with tempfile.TemporaryDirectory() as temp:
            control = core.SyntheticControllerCore(temp)
            self.tick(control, snapshot())
            event, evidence = merged_snapshot()
            root, signature = root_fixture("synthetic-merge-signature.json")
            evidence["signature"] = signature
            event["post_merge_checks"] = checks()
            sequence = []
            original_sync = os.fsync
            original_save = control._write_state

            def traced_sync(fd):
                if stat.S_ISDIR(os.fstat(fd).st_mode):
                    sequence.append("directory_synced")
                return original_sync(fd)

            def traced_save(*args):
                sequence.append("state_saved")
                return original_save(*args)

            with patch("os.fsync", side_effect=traced_sync), patch.object(
                    control, "_write_state", side_effect=traced_save):
                self.assertEqual(self.tick(control, event, merge_evidence=evidence,
                                           merge_root=root), "POST_MERGE_CI")
            self.assertIn("directory_synced", sequence)
            self.assertLess(sequence.index("directory_synced"),
                            sequence.index("state_saved"))

    def test_restart_config_cannot_extend_persisted_absolute_deadline(self):
        with tempfile.TemporaryDirectory() as temp:
            short = core.SyntheticControllerCore(temp, post_merge_timeout=timedelta(seconds=2))
            self.tick(short, snapshot())
            event, evidence = merged_snapshot()
            root, signature = root_fixture("synthetic-merge-signature.json")
            evidence["signature"] = signature
            event["post_merge_checks"] = checks()
            self.assertEqual(self.tick(short, event, merge_evidence=evidence,
                                       merge_root=root), "POST_MERGE_CI")
            restarted = core.SyntheticControllerCore(temp)  # default TWO HOURS
            event["post_merge_checks"] = checks(MERGE)
            self.assertEqual(restarted.tick(envelope=self.envelope,
                public_root=self.root, snapshot=event, main=MERGE,
                now=NOW + timedelta(seconds=3), merge_evidence=evidence,
                merge_root=root), "BLOCKED")

    def test_done_state_directory_sync_before_return(self):
        import os
        import stat
        from unittest.mock import patch
        if os.name == "nt":
            self.skipTest("native Windows directory durability not witnessed")
        with tempfile.TemporaryDirectory() as temp:
            control = core.SyntheticControllerCore(temp)
            self.tick(control, snapshot())
            event, evidence = merged_snapshot()
            root, signature = root_fixture("synthetic-merge-signature.json")
            evidence["signature"] = signature
            sync = os.fsync
            save = control._write_state
            order = []

            def trace_sync(fd):
                if stat.S_ISDIR(os.fstat(fd).st_mode):
                    order.append("dir_fsync")
                return sync(fd)

            def trace_save(*args):
                order.append("state_save")
                return save(*args)

            with patch("os.fsync", side_effect=trace_sync), patch.object(
                    control, "_write_state", side_effect=trace_save):
                self.assertEqual(self.tick(control, event,
                    merge_evidence=evidence, merge_root=root), "DONE")
            self.assertIn("state_save", order)
            self.assertIn("dir_fsync", order)
            self.assertLess(order.index("state_save"), order.index("dir_fsync"))

    def test_retry_terminal_state_resyncs_directory_after_failed_fsync(self):
        from unittest.mock import patch
        for terminal in ("DONE", "BLOCKED"):
            with self.subTest(terminal=terminal):
                with tempfile.TemporaryDirectory() as temp:
                    control = core.SyntheticControllerCore(temp)
                    # Simulate a terminal state renamed into place while its
                    # containing-directory fsync failed before acknowledgement.
                    a = self.envelope["record"]
                    job = d.Delivery(a["id"], a["issue"], a["base"], a["branch"])
                    job.state = terminal
                    d.save_state(control.state_file, job)
                    with patch.object(control, "_sync_directory",
                                      side_effect=d.Denied("synthetic fsync failure")):
                        with self.assertRaises(d.Denied):
                            self.tick(control, snapshot())
                    self.assertEqual(d.restore_state(control.state_file, a).state,
                                     terminal)
                    with patch.object(control, "_sync_directory",
                                      wraps=control._sync_directory) as sync:
                        self.assertEqual(self.tick(control, snapshot()), terminal)
                        sync.assert_called_once()

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

    def test_state_temp_symlink_does_not_touch_external_file(self):
        import os
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as external:
            victim = Path(external) / "synthetic-victim"
            sentinel = b"unchanged synthetic file"
            victim.write_bytes(sentinel)
            trap = Path(temp) / "controller-state.tmp"
            try:
                os.symlink(victim, trap)
            except (OSError, NotImplementedError):
                self.skipTest("synthetic symlink permission unavailable")
            control = core.SyntheticControllerCore(temp)
            self.assertEqual(self.tick(control, snapshot()), "PR_PENDING")
            self.assertEqual(victim.read_bytes(), sentinel)
            self.assertTrue(trap.is_symlink())
            self.assertTrue(control.state_file.is_file())

    def test_state_temp_hardlink_does_not_touch_external_file(self):
        import os
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as external:
            victim = Path(external) / "synthetic-victim"
            sentinel = b"unchanged synthetic file"
            victim.write_bytes(sentinel)
            trap = Path(temp) / "controller-state.tmp"
            try:
                os.link(victim, trap)
            except (OSError, NotImplementedError):
                self.skipTest("synthetic hardlink permission unavailable")
            control = core.SyntheticControllerCore(temp)
            self.assertEqual(self.tick(control, snapshot()), "PR_PENDING")
            self.assertEqual(victim.read_bytes(), sentinel)
            self.assertTrue(os.path.samefile(trap, victim))
            self.assertTrue(control.state_file.is_file())

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


import json
import multiprocessing
from unittest.mock import patch

from test_windows_approval_store import fixture
from test_windows_publisher import p, signed_evidence, signer_fixture
from worker_adapter import FakeWorkerAdapter


def hold_fixture_controller_lock(directory, ready, release):
    from approval_store import synthetic_lock
    with synthetic_lock(Path(directory) / 'controller.lock'):
        ready.set()
        release.wait(15)


class A3ProtectedControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.signer = signer_fixture()

    def setUp(self):
        self.envelope, self.root = fixture()
        self.a = approval()
        self.policy = p.SyntheticProviderPolicy()

    def start(self, tmp):
        controller = core.SyntheticProtectedController(tmp)
        controller.initialize()
        return controller

    def run_fake(self, controller, **updates):
        args = dict(envelope=self.envelope, root=self.root, main=BASE, now=NOW,
                    worker=FakeWorkerAdapter())
        args.update(updates)
        return controller.run_fake(**args)

    def verify(self, controller, **updates):
        event = snapshot()
        event['checks'] = checks()
        evidence = signed_evidence(self.signer, event)
        args = dict(envelope=self.envelope, root=self.root, main=BASE, now=NOW,
            feed=p.SyntheticEvidenceFeed((evidence, evidence)), evidence_root=self.signer.root,
            policy=self.policy, old_tree={self.a['paths'][0]: p.SyntheticBlob('1' * 40)},
            new_tree={self.a['paths'][0]: p.SyntheticBlob('2' * 40)})
        args.update(updates)
        return controller.verify_candidate(**args)

    def observe(self, controller, event=None, **updates):
        event = event if event is not None else merged_snapshot()[0]
        evidence = signed_evidence(self.signer, event)
        merge_root, signature = root_fixture('synthetic-merge-signature.json')
        owner_merge = merged_snapshot()[1]
        owner_merge['signature'] = signature
        args = dict(envelope=self.envelope, root=self.root, now=NOW,
            feed=p.SyntheticEvidenceFeed((evidence,)), evidence_root=self.signer.root,
            policy=self.policy, merge_evidence=owner_merge, merge_root=merge_root)
        args.update(updates)
        return controller.observe_merge(**args)

    def test_two_identical_full_offline_deliveries(self):
        outputs = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as tmp:
                controller = self.start(tmp)
                sequence = [self.run_fake(controller)]
                report = self.verify(controller)
                sequence.append(report['decision'])
                event = merged_snapshot()[0]
                event['post_merge_checks'] = checks(MERGE)
                sequence.append(self.observe(controller, event))
                sequence.append(core.SyntheticProtectedController(tmp).observe_merge(
                    envelope=self.envelope, root=self.root, now=NOW,
                    feed=p.SyntheticEvidenceFeed((signed_evidence(self.signer, event),)),
                    evidence_root=self.signer.root, policy=self.policy,
                    merge_evidence=None, merge_root=None))
                outputs.append((sequence, controller.store.path.read_bytes()))
                self.assertEqual(sequence, ['TEST_PASS', 'NO_GO', 'DONE', 'DONE'])
                with self.assertRaises(d.Denied):
                    self.run_fake(controller)
        self.assertEqual(outputs[0], outputs[1])

    def test_reservation_precedes_fake_effect_and_repairs_are_durable(self):
        with tempfile.TemporaryDirectory() as tmp:
            controller = self.start(tmp)
            original = FakeWorkerAdapter.simulate_reserved
            seen = []
            def inspect(worker, unit):
                reserved = json.loads(controller.store.path.read_bytes())['delivery']
                self.assertEqual(reserved['state'], 'RUNNING')
                self.assertEqual(reserved['attempts'][-1]['status'], 'RESERVED')
                seen.append(reserved['attempts'][-1]['id'])
                return original(worker, unit)
            with patch.object(FakeWorkerAdapter, 'simulate_reserved', inspect):
                self.assertEqual(self.run_fake(controller, worker=FakeWorkerAdapter(('TEST_FAIL',))), 'TEST_FAIL')
                controller = core.SyntheticProtectedController(tmp)
                self.assertEqual(self.run_fake(controller, worker=FakeWorkerAdapter(('TEST_FAIL',))), 'TEST_FAIL')
                self.assertEqual(self.run_fake(controller, worker=FakeWorkerAdapter(('TEST_FAIL',))), 'TEST_FAIL')
                self.assertEqual(self.run_fake(controller), 'BLOCKED')
            self.assertEqual(seen, [0, 1, 2])

    def test_unknown_crash_outcome_blocks_restart_without_duplicate_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            controller = self.start(tmp)
            with patch.object(FakeWorkerAdapter, 'simulate_reserved', side_effect=SystemExit(99)):
                with self.assertRaises(SystemExit):
                    self.run_fake(controller)
            restarted = core.SyntheticProtectedController(tmp)
            with patch.object(FakeWorkerAdapter, 'simulate_reserved') as simulate:
                self.assertEqual(self.run_fake(restarted), 'BLOCKED')
                simulate.assert_not_called()
            state = json.loads(restarted.store.path.read_bytes())
            self.assertEqual(state['delivery']['attempts'], [{'id': 0, 'status': 'RESERVED', 'tokens': 1024}])

    def test_cancel_timeout_budget_and_transport_denials(self):
        for update in (dict(cancelled=True), dict(worker=FakeWorkerAdapter(('TIMED_OUT',))),
                       dict(worker=FakeWorkerAdapter(('BUDGET_EXCEEDED',))),
                       dict(worker=FakeWorkerAdapter(('CANCELLED',)))):
            with self.subTest(update=update), tempfile.TemporaryDirectory() as tmp:
                controller = self.start(tmp)
                self.assertEqual(self.run_fake(controller, **update), 'BLOCKED')
                with self.assertRaises(d.Denied):
                    self.run_fake(controller)
        with tempfile.TemporaryDirectory() as tmp:
            controller = self.start(tmp)
            self.assertEqual(self.run_fake(controller, max_tokens=1024,
                worker=FakeWorkerAdapter(('TEST_FAIL',))), 'TEST_FAIL')
            self.assertEqual(self.run_fake(controller, max_tokens=1024), 'BLOCKED')
        with tempfile.TemporaryDirectory() as tmp:
            controller = self.start(tmp)
            self.run_fake(controller, worker=FakeWorkerAdapter(('TEST_FAIL',)))
            self.assertEqual(self.run_fake(controller, now=NOW + timedelta(seconds=600)), 'BLOCKED')
        with tempfile.TemporaryDirectory() as tmp:
            controller = self.start(tmp)
            for worker in (object(), lambda: 'TEST_PASS', {'transport': 'codex'}):
                with self.assertRaises(d.Denied):
                    self.run_fake(controller, worker=worker)

    def test_revocation_scope_substitution_and_fake_issue_never_authorize(self):
        with tempfile.TemporaryDirectory() as tmp:
            controller = self.start(tmp)
            self.run_fake(controller)
            for bad in ({'issue': 216, 'comment': 'approved'},
                        self.envelope | {'record': self.a | {'paths': ['outside.py']}},
                        self.signer.sign(self.a | {'paths': ['outside.py']})):
                with self.assertRaises(d.Denied):
                    self.verify(controller, envelope=bad)
            controller.store.revoke_delivery(self.a['id'])
            with self.assertRaises(d.Denied):
                self.verify(controller)
            self.assertEqual(json.loads(controller.store.path.read_bytes())['delivery']['state'], 'BLOCKED')

    def test_waiting_pr_cannot_run_again_or_publish_twice(self):
        with tempfile.TemporaryDirectory() as tmp:
            controller = self.start(tmp)
            self.run_fake(controller)
            self.verify(controller)
            with self.assertRaises(d.Denied):
                self.verify(core.SyntheticProtectedController(tmp))
            with self.assertRaises(d.Denied):
                self.run_fake(core.SyntheticProtectedController(tmp))

    def test_failed_post_merge_and_unavailable_collector_block(self):
        for attack in ('failed', 'fake_merge', 'unavailable', 'changed_head'):
            with self.subTest(attack=attack), tempfile.TemporaryDirectory() as tmp:
                controller = self.start(tmp)
                self.run_fake(controller)
                self.verify(controller)
                event = merged_snapshot()[0]
                if attack == 'failed':
                    event['post_merge_checks'][0]['conclusion'] = 'failure'
                    self.assertEqual(self.observe(controller, event), 'BLOCKED')
                elif attack == 'fake_merge':
                    with self.assertRaises(d.Denied):
                        self.observe(controller, event, merge_evidence={'record': {}, 'signature': 'AAAA'})
                elif attack == 'unavailable':
                    feed = p.SyntheticEvidenceFeed((signed_evidence(self.signer, event),))
                    feed.collect()
                    with self.assertRaises(d.Denied):
                        self.observe(controller, event, feed=feed)
                else:
                    event['prs'][0]['head'] = 'd' * 40
                    with self.assertRaises(d.Denied):
                        self.observe(controller, event)
                self.assertEqual(json.loads(controller.store.path.read_bytes())['delivery']['state'], 'BLOCKED')

    def test_post_merge_deadline_and_poll_budget_survive_restart(self):
        for attack in ('deadline', 'polls'):
            with self.subTest(attack=attack), tempfile.TemporaryDirectory() as tmp:
                controller = self.start(tmp)
                self.run_fake(controller)
                self.verify(controller)
                event = merged_snapshot()[0]
                event['post_merge_checks'] = checks(MERGE)
                event['post_merge_checks'][0].update(status='in_progress', conclusion=None)
                self.assertEqual(self.observe(controller, event), 'POST_MERGE_CI')
                if attack == 'deadline':
                    # Approval expiry is independently enforced as well.
                    with self.assertRaises(d.Denied):
                        self.observe(core.SyntheticProtectedController(tmp), event, now=NOW + timedelta(days=1))
                else:
                    with controller.store.transaction() as state:
                        state['delivery']['polls'] = 20
                        controller.store.commit(state)
                    self.assertEqual(self.observe(core.SyntheticProtectedController(tmp)), 'BLOCKED')

    def test_raw_git_fixture_flows_through_controller_independent_publisher(self):
        from test_windows_publisher import SyntheticSigner, make_git_fixture
        owner = SyntheticSigner()
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as git_tmp:
            a, head = make_git_fixture(git_tmp)
            envelope = owner.sign(a)
            controller = self.start(tmp)
            self.assertEqual(self.run_fake(controller, envelope=envelope, root=owner.root,
                main=a['base']), 'TEST_PASS')
            event = snapshot()
            event['main'] = a['base']
            event['prs'][0]['head'] = head
            event['checks'] = checks(head)
            evidence = signed_evidence(self.signer, event, a=a)
            result = controller.verify_candidate(envelope=envelope, root=owner.root,
                main=a['base'], now=NOW, feed=p.SyntheticEvidenceFeed((evidence, evidence)),
                evidence_root=self.signer.root, policy=self.policy, directory=git_tmp)
            self.assertEqual(result['head'], head)
            self.assertEqual(result['decision'], 'NO_GO')
            self.assertEqual(json.loads(controller.store.path.read_bytes())['delivery']['state'],
                'WAITING_FOR_OWNER')
        owner.temp.cleanup()

    def test_signature_and_revocation_rechecked_at_repair_and_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            controller = self.start(tmp)
            self.run_fake(controller, worker=FakeWorkerAdapter(('TEST_FAIL',)))
            with self.assertRaises(d.Denied):
                self.run_fake(controller, root=self.root - 2)
            with self.assertRaises(d.Denied):
                self.run_fake(controller, main=MERGE)
            with self.assertRaises(d.Denied):
                self.run_fake(controller, now=NOW + timedelta(days=1))
            controller.store.revoke_delivery(self.a['id'])
            with self.assertRaises(d.Denied):
                self.run_fake(core.SyntheticProtectedController(tmp))
        with tempfile.TemporaryDirectory() as tmp:
            controller = self.start(tmp)
            self.run_fake(controller)
            with self.assertRaises(d.Denied):
                self.verify(controller, evidence_root=self.root)
            with self.assertRaises(d.Denied):
                self.verify(controller, main=MERGE)
            with self.assertRaises(d.Denied):
                self.verify(controller, now=NOW + timedelta(seconds=600))

    def test_partial_or_stale_post_checks_block_instead_of_polling_forever(self):
        for changed in ('missing', 'stale', 'duplicate'):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as tmp:
                controller = self.start(tmp)
                self.run_fake(controller)
                self.verify(controller)
                event = merged_snapshot()[0]
                if changed == 'missing':
                    event['post_merge_checks'].pop()
                elif changed == 'stale':
                    event['post_merge_checks'][0]['head_sha'] = HEAD
                else:
                    event['post_merge_checks'][-1] = event['post_merge_checks'][0]
                self.assertEqual(self.observe(controller, event), 'BLOCKED')

    def test_late_success_blocked_by_persisted_post_deadline(self):
        with tempfile.TemporaryDirectory() as tmp:
            controller = self.start(tmp)
            self.run_fake(controller)
            self.verify(controller)
            event = merged_snapshot()[0]
            event['post_merge_checks'][0].update(status='in_progress', conclusion=None)
            self.assertEqual(self.observe(controller, event), 'POST_MERGE_CI')
            self.assertEqual(self.observe(core.SyntheticProtectedController(tmp),
                now=NOW + timedelta(hours=2, seconds=1)), 'BLOCKED')

    def test_two_actual_process_ticks_share_single_os_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            controller = self.start(tmp)
            context = multiprocessing.get_context('spawn')
            ready, release = context.Event(), context.Event()
            child = context.Process(target=hold_fixture_controller_lock, args=(tmp, ready, release))
            child.start()
            try:
                self.assertTrue(ready.wait(10))
                with self.assertRaises(d.Denied):
                    self.run_fake(controller)
                self.assertIsNone(json.loads(controller.store.path.read_bytes())['delivery'])
            finally:
                release.set()
                child.join(10)
                if child.is_alive():
                    child.terminate()
                    child.join()
            self.assertEqual(child.exitcode, 0)
            self.assertEqual(self.run_fake(controller), 'TEST_PASS')


if __name__ == "__main__":
    unittest.main()
