"""Offline lifecycle harness using #207's fail-closed delivery primitives.

No GitHub adapter, OS provisioning, signer, model launcher, or publisher exists.
Inputs are synthetic snapshots, NOT an authenticated live GitHub feed.
"""
from datetime import datetime, timedelta
from pathlib import Path

import dispatcher as d
from approval_store import read_fixture_json, synthetic_lock


class SyntheticControllerCore:
    """Serialize synthetic ticks and persist crash-safe delivery state.

    The directory is an owner-provided disposable fixture, not a protected
    Windows host. It must never be mounted into a model-capable privileged job.
    """

    def __init__(self, directory, *, post_merge_timeout=timedelta(hours=2)):
        self.directory = Path(directory)
        if not self.directory.is_dir() or self.directory.is_symlink():
            raise d.Denied("invalid synthetic workspace")
        if not isinstance(post_merge_timeout, timedelta) or not (
            timedelta(seconds=1) <= post_merge_timeout <= timedelta(days=1)
        ):
            raise d.Denied("invalid post-merge timeout")
        self.state_file = self.directory / "controller-state.json"
        self.lock = self.directory / "controller.lock"
        self.deadline_file = self.directory / "post-merge-deadline.json"
        self.post_merge_timeout = post_merge_timeout

    def _current(self, approval):
        if self.state_file.is_symlink() or self.deadline_file.is_symlink():
            raise d.Denied("unsafe controller state")
        if self.state_file.exists():
            # Validate the actual opened fixture handle before legacy schema
            # restoration; hardlinks/reparse/malformed JSON are fail-closed.
            saved = read_fixture_json(self.state_file)
            if not isinstance(saved, dict):
                raise d.Denied("invalid synthetic controller state")
            return d.restore_state(self.state_file, approval)
        return d.Delivery(approval["id"], approval["issue"], approval["base"],
                          approval["branch"])

    @staticmethod
    def _validate_snapshot(snapshot, main):
        """Reject malformed fake GitHub data before the #207 state machine uses it."""
        fields = {"main", "prs", "checks", "merged", "merge_sha",
                  "post_merge_checks", "ci_failed"}
        if (not isinstance(main, str) or not d.SHA.fullmatch(main)
                or not isinstance(snapshot, dict)
                or set(snapshot) - fields
                or not {"main", "prs", "checks"} <= set(snapshot)
                or snapshot["main"] != main
                or not isinstance(snapshot["prs"], list)
                or len(snapshot["prs"]) > 1
                or not isinstance(snapshot["checks"], list)
                or snapshot.get("merged", False) not in (True, False)
                or type(snapshot.get("merged", False)) is not bool
                or type(snapshot.get("ci_failed", False)) is not bool):
            raise d.Denied("invalid synthetic snapshot")
        if snapshot.get("merged", False):
            if (not isinstance(snapshot.get("merge_sha"), str)
                    or not d.SHA.fullmatch(snapshot["merge_sha"])
                    or not isinstance(snapshot.get("post_merge_checks"), list)):
                raise d.Denied("invalid synthetic merge snapshot")
        elif "merge_sha" in snapshot or "post_merge_checks" in snapshot:
            raise d.Denied("unexpected synthetic merge evidence")
        for name in ("checks", "post_merge_checks"):
            if name not in snapshot:
                continue
            checks = snapshot[name]
            if not isinstance(checks, list) or len(checks) > 16:
                raise d.Denied("invalid synthetic checks")
            for check in checks:
                if (not isinstance(check, dict)
                        or set(check) != {"name", "head_sha", "status", "conclusion"}
                        or not isinstance(check["name"], str)
                        or not isinstance(check["head_sha"], str)
                        or not d.SHA.fullmatch(check["head_sha"])
                        or not isinstance(check["status"], str)
                        or check["conclusion"] is not None
                        and not isinstance(check["conclusion"], str)):
                    raise d.Denied("invalid synthetic checks")
        for pr in snapshot["prs"]:
            required = {"repo", "head_repo", "branch", "base", "number", "head"}
            if (not isinstance(pr, dict) or not required <= set(pr)
                    or set(pr) - (required | {"merged", "merge_commit_sha"})
                    or any(not isinstance(pr[name], str)
                           for name in ("repo", "head_repo", "branch", "base", "head"))
                    or type(pr["number"]) is not int or pr["number"] <= 0
                    or not d.SHA.fullmatch(pr["head"])
                    or type(pr.get("merged", False)) is not bool):
                raise d.Denied("invalid synthetic PR")
            if "merge_commit_sha" in pr and (
                    not isinstance(pr["merge_commit_sha"], str)
                    or not d.SHA.fullmatch(pr["merge_commit_sha"])):
                raise d.Denied("invalid synthetic PR merge")

    def _check_deadline(self, job, now):
        """Enforce a prior deadline BEFORE allowing a successful CI transition."""
        if not self.deadline_file.exists() or self.deadline_file.is_symlink():
            raise d.Denied("missing or unsafe post-merge deadline")
        deadline = read_fixture_json(self.deadline_file)
        if (not isinstance(deadline, dict)
                or set(deadline) != {"approval_id", "at", "deadline"}
                or deadline["approval_id"] != job.approval_id):
            raise d.Denied("invalid post-merge deadline")
        try:
            timestamp = datetime.fromisoformat(deadline["at"])
            absolute_end = datetime.fromisoformat(deadline["deadline"])
        except (TypeError, ValueError):
            raise d.Denied("invalid post-merge deadline") from None
        if (timestamp.tzinfo is None or absolute_end.tzinfo is None
                or timestamp > now
                or not timedelta(seconds=1) <= absolute_end - timestamp <= timedelta(days=1)):
            raise d.Denied("invalid post-merge deadline")
        # The persisted absolute deadline wins across restarts even if the
        # next process receives a longer runtime timeout configuration.
        return now >= absolute_end

    def _sync_directory(self):
        """Durability of POSIX rename entries, never native Windows acceptance."""
        import os
        if os.name != "nt":
            try:
                fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
            except OSError:
                raise d.Denied("synthetic directory persistence unavailable") from None

    def _write_state(self, job):
        """Atomically persist only via an exclusive, unpredictable temp file.

        The legacy dispatcher saves through a predictable .tmp name which
        can follow symlinks or hardlinks. This test-only adapter must not.
        """
        import os
        import tempfile
        temporary = None
        try:
            with tempfile.NamedTemporaryFile("wb", delete=False, dir=self.directory,
                                             prefix="controller-state-", suffix=".tmp") as stream:
                temporary = Path(stream.name)
                stream.write(d.canonical(job.__dict__))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.state_file)
            temporary = None
        except OSError:
            raise d.Denied("unsafe synthetic state persistence") from None
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    raise d.Denied("unsafe synthetic state cleanup") from None

    def _save_state(self, job):
        self._write_state(job)
        # No DONE/BLOCKED transition may be returned before the rename is
        # durable. Native Windows persistence is NOT TESTED / NO_GO.
        self._sync_directory()

    def tick(self, *, envelope, public_root, snapshot, main, now,
             revoked=frozenset(), consumed=frozenset(), merge_evidence=None,
             merge_root=None):
        """Never fetch, execute or publish; only inspect supplied fake snapshots."""
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise d.Denied("invalid clock")
        self._validate_snapshot(snapshot, main)
        if (not isinstance(revoked, (set, frozenset))
                or not isinstance(consumed, (set, frozenset))):
            raise d.Denied("invalid revocation state")
        if (not isinstance(envelope, dict)
                or not isinstance(envelope.get("record"), dict)):
            raise d.Denied("invalid signed approval envelope")
        with synthetic_lock(self.lock):
            # Signed verification below authenticates base even for a merged PR.
            candidate_base = (envelope["record"].get("base")
                              if snapshot.get("merged", False) else main)
            approval = d.verified_approval(envelope, public_root,
                                           main=candidate_base, now=now,
                                           revoked=revoked, consumed=consumed)
            job = self._current(approval)
            if job.state in ("DONE", "BLOCKED"):
                # The state file may be visible after os.replace() even when
                # a previous directory fsync failed. Do not report a terminal
                # state until its directory entry is durably synchronized.
                # This also retries a failed sync on a later synthetic tick.
                self._sync_directory()
                return job.state
            # The durable deadline, not a mutable lifecycle state, controls
            # acceptance: a crash may leave an older PR_PENDING state while
            # the post-merge deadline file has already been committed.
            deadline_exists = self.deadline_file.exists()
            if deadline_exists:
                if self._check_deadline(job, now):
                    job.state = "BLOCKED"
                    self._save_state(job)
                    return job.state
                # Once any merged observation was recorded, a non-merged PR
                # snapshot must not rewind the lifecycle and reset its timer.
                if snapshot.get("merged") is not True:
                    raise d.Denied("post-merge snapshot regression")
            elif job.state == "POST_MERGE_CI":
                raise d.Denied("missing post-merge deadline")
            state = job.observe(approval, snapshot, merge_evidence=merge_evidence,
                                owner_modulus=merge_root)
            if state == "POST_MERGE_CI":
                if self.deadline_file.exists():
                    self._check_deadline(job, now)
                else:
                    self._write_deadline(job.approval_id, now)
            self._save_state(job)
            return job.state

    def _write_deadline(self, approval_id, when):
        # Fixed, minimized fields; no logs, usernames, paths or Issue content.
        import os
        import tempfile
        temporary = None
        try:
            with tempfile.NamedTemporaryFile("wb", delete=False, dir=self.directory,
                                             prefix="deadline-") as stream:
                temporary = Path(stream.name)
                stream.write(d.canonical({"approval_id": approval_id,
                                          "at": when.isoformat(),
                                          "deadline": (when + self.post_merge_timeout).isoformat()}))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.deadline_file)
            # Persist the deadline's new name BEFORE saving delivery state.
            self._sync_directory()
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    @staticmethod
    def dry_run():
        """Deterministic and side-effect-free even without a workspace."""
        return {"execution": "DISABLED", "publisher": "ABSENT",
                "isolation": "NOT_TESTED", "decision": "NO_GO"}


def require_execution():
    raise d.Denied("NO_GO: protected host worker has not been accepted")


class SyntheticProtectedController:
    """A3 integrated OFFLINE lifecycle with one durable reservation ledger.

    No Issue text, commands, environment, network or arbitrary worker callbacks.
    Fixed ceilings are fixture accounting, not a signed runtime resource grant.
    The legacy #207 approval schema is intentionally unchanged in this delivery.
    """

    def __init__(self, directory, *, approval_root=None, merge_root=None):
        from approval_store import SyntheticDeliveryStore
        for configured in (approval_root, merge_root):
            if type(configured) is not int or not 3072 <= configured.bit_length() <= 8192:
                raise d.Denied("independently configured owner roots required")
        self.approval_root = approval_root
        self.merge_root = merge_root
        self.store = SyntheticDeliveryStore(directory)

    def initialize(self):
        self.store.initialize()

    def _verify(self, envelope, root, state, main, now, *, allow_completed=False):
        if root != self.approval_root:
            raise d.Denied("owner approval root substitution")
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise d.Denied("invalid clock")
        consumed = set(state["consumed"])
        # Only an identical DONE record may be inspected again. It cannot run.
        prior = state["delivery"]
        if allow_completed and prior is not None and prior["state"] == "DONE":
            consumed.discard(prior["record"]["id"])
        try:
            return d.verified_approval(envelope, root, main=main, now=now,
                revoked=set(state["revoked"]), consumed=consumed)
        except (TypeError, KeyError):
            raise d.Denied("invalid signed scope") from None

    def _bound(self, job, approval):
        from approval_store import fingerprint
        if (job is None or job["record"] != approval or job["fingerprint"] != fingerprint(approval)
                or job["approval_root_fingerprint"] != fingerprint(self.approval_root)
                or job["merge_root_fingerprint"] != fingerprint(self.merge_root)):
            raise d.Denied("reservation scope changed")

    def run_fake(self, *, envelope, root, main, now, worker, cancelled=False,
                 max_tokens=4096, attempt_tokens=1024, attempt_seconds=120):
        """Persist the full attempt budget BEFORE any fake invocation.

        RUNNING on restart is terminally BLOCKED: there is no blind retry after
        unknown outcome. Repair is permitted only after an acknowledged failure.
        """
        from approval_store import fingerprint, fixture_time
        from worker_adapter import (
            FakeWorkerAdapter,
            ReservedSyntheticUnit,
            SyntheticWorkUnit,
        )
        if type(worker) is not FakeWorkerAdapter or type(cancelled) is not bool:
            raise d.Denied("only finite fake transport allowed")
        for value, upper in ((max_tokens, 4096), (attempt_tokens, 1024), (attempt_seconds, 120)):
            if type(value) is not int or not 1 <= value <= upper:
                raise d.Denied("invalid fixture limits")
        with self.store.transaction() as state:
            approval = self._verify(envelope, root, state, main, now)
            job = state["delivery"]
            if job is None or job["state"] == "DONE":
                job = {"record": approval, "fingerprint": fingerprint(approval),
                    "approval_root_fingerprint": fingerprint(self.approval_root),
                    "merge_root_fingerprint": fingerprint(self.merge_root),
                    "state": "READY", "attempts": [], "started": now.isoformat(),
                    "deadline": min(now + timedelta(seconds=600),
                                    fixture_time(approval["expires"])).isoformat(),
                    "max_tokens": max_tokens, "attempt_tokens": attempt_tokens,
                    "attempt_seconds": attempt_seconds, "head": "", "pr": None,
                    "merge_sha": "", "post_started": None, "post_deadline": None, "polls": 0}
                state["delivery"] = job
            self._bound(job, approval)
            # Persisted limits win after restart; caller cannot enlarge them.
            if (job["max_tokens"], job["attempt_tokens"], job["attempt_seconds"]) != (
                    max_tokens, attempt_tokens, attempt_seconds):
                raise d.Denied("reserved limits changed")
            if cancelled or now >= fixture_time(job["deadline"]) or job["state"] == "RUNNING":
                job["state"] = "BLOCKED"
                self.store.commit(state)
                return "BLOCKED"
            if job["state"] not in ("READY", "TEST_FAIL"):
                raise d.Denied("duplicate or blocked fake attempt")
            attempt = len(job["attempts"])
            if (attempt > approval["max_repairs"]
                    or (attempt + 1) * attempt_tokens > max_tokens):
                job["state"] = "BLOCKED"
                self.store.commit(state)
                return "BLOCKED"
            job["attempts"].append({"id": attempt, "status": "RESERVED", "tokens": attempt_tokens})
            job["state"] = "RUNNING"
            self.store.commit(state)
            unit = ReservedSyntheticUnit(SyntheticWorkUnit.from_verified_record(approval, now=now),
                attempt, job["fingerprint"], job["deadline"], attempt_seconds, attempt_tokens)
            try:
                event = worker.simulate_reserved(unit)
                if type(event) is not str or event not in FakeWorkerAdapter.EVENTS:
                    raise d.Denied("invalid fake outcome")
            except Exception:
                job["state"] = "BLOCKED"
                self.store.commit(state)
                raise d.Denied("ambiguous fake outcome") from None
            job["attempts"][-1]["status"] = event
            job["state"] = event if event in ("TEST_PASS", "TEST_FAIL") else "BLOCKED"
            self.store.commit(state)
            return job["state"]

    def verify_candidate(self, *, envelope, root, main, now, feed, evidence_root,
                         policy, old_tree=None, new_tree=None, directory=None):
        """Offline publication candidate; no branch/PR creation or write token."""
        import publisher as p
        from approval_store import fixture_time
        if root == evidence_root or self.merge_root == evidence_root:
            raise d.Denied("owner and collector roots must be independent")
        with self.store.transaction() as state:
            approval = self._verify(envelope, root, state, main, now)
            job = state["delivery"]
            self._bound(job, approval)
            if job["state"] != "TEST_PASS" or now >= fixture_time(job["deadline"]):
                raise d.Denied("candidate not ready or timed out")
            if directory is not None:
                if old_tree is not None or new_tree is not None:
                    raise d.Denied("ambiguous snapshot source")
                report = p.verify_loose_fixture_candidate(directory=directory,
                    approval=approval, feed=feed, evidence_root=evidence_root,
                    now=now, policy=policy)
            else:
                report = p.verify_fixture_candidate(approval=approval, feed=feed,
                    evidence_root=evidence_root, now=now, policy=policy,
                    old_tree=old_tree, new_tree=new_tree)
            # Fresh signature/revocation check under the same global lock.
            self._verify(envelope, root, state, main, now)
            job.update(head=report["head"], pr=report["pr"], state="WAITING_FOR_OWNER")
            self.store.commit(state)
            return report

    def observe_merge(self, *, envelope, root, now, feed, evidence_root, policy,
                      merge_evidence, merge_root):
        """Reconcile separately signed owner merge and signed FAKE GitHub state.

        Bounded status polling never reruns CI or triggers merge. Actual online
        authenticity and production protected custody are deliberately absent.
        """
        import publisher as p
        from approval_store import fixture_time
        if (type(feed) is not p.SyntheticEvidenceFeed or root == evidence_root
                or self.merge_root == evidence_root or merge_root != self.merge_root):
            raise d.Denied("independent synthetic collector required")
        with self.store.transaction() as state:
            job = state["delivery"]
            if job is None:
                raise d.Denied("no delivery to reconcile")
            approval = self._verify(envelope, root, state, job["record"]["base"], now,
                                    allow_completed=True)
            self._bound(job, approval)
            if job["state"] not in ("WAITING_FOR_OWNER", "POST_MERGE_CI", "DONE"):
                raise d.Denied("delivery not awaiting merge")
            if job["state"] == "DONE":
                self.store.commit(state)  # directory sync before acknowledgement
                return "DONE"
            if job["polls"] >= 20 or (job["post_deadline"] is not None
                    and now >= fixture_time(job["post_deadline"])):
                job["state"] = "BLOCKED"
                self.store.commit(state)
                return "BLOCKED"
            # Spend query budget before collecting; an unavailable/uncertain
            # response blocks reconciliation and cannot launch or publish again.
            job["polls"] += 1
            self.store.commit(state)
            try:
                event = p.verify_fixture_evidence(feed.collect(), evidence_root,
                                                  approval=approval, now=now, policy=policy)
                pr = event["prs"][0]
                if pr["head"] != job["head"] or pr["number"] != job["pr"]:
                    raise d.Denied("merge PR identity drift")
                legacy = d.Delivery(approval["id"], approval["issue"], approval["base"],
                    approval["branch"], state="READY_FOR_MASTER_CHAT", head=job["head"], pr=job["pr"])
                result = legacy.observe(approval, event, merge_evidence=merge_evidence,
                                        owner_modulus=merge_root)
                if event.get("merged") is not True:
                    raise d.Denied("missing actual synthetic merge")
                if job["merge_sha"] and job["merge_sha"] != event["merge_sha"]:
                    raise d.Denied("merge SHA changed")
                job["merge_sha"] = event["merge_sha"]
                if job["post_deadline"] is None:
                    if now < fixture_time(job["started"]):
                        raise d.Denied("merge observation clock regressed")
                    job["post_started"] = now.isoformat()
                    job["post_deadline"] = (now + timedelta(hours=2)).isoformat()
                post = event["post_merge_checks"]
                if (len(post) != 8 or {check["name"] for check in post} != d.CI
                        or any(check["head_sha"] != event["merge_sha"]
                               or check["status"] == "completed" and check["conclusion"] != "success"
                               for check in post)):
                    result = "BLOCKED"
                job["state"] = result
                if result == "DONE":
                    state["consumed"] = sorted([*state["consumed"], approval["id"]])
                self.store.commit(state)
                return result
            except Exception:
                job["state"] = "BLOCKED"
                self.store.commit(state)
                raise d.Denied("ambiguous merge reconciliation") from None
