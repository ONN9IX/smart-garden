"""Offline lifecycle harness using #207's fail-closed delivery primitives.

No GitHub adapter, OS provisioning, signer, model launcher, or publisher exists.
Inputs are synthetic snapshots, NOT an authenticated live GitHub feed.
"""
from datetime import datetime, timedelta
from pathlib import Path

import dispatcher as d
from approval_store import synthetic_lock


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
        deadline = d.load_json(self.deadline_file)
        if (not isinstance(deadline, dict)
                or set(deadline) != {"approval_id", "at"}
                or deadline["approval_id"] != job.approval_id):
            raise d.Denied("invalid post-merge deadline")
        try:
            timestamp = datetime.fromisoformat(deadline["at"])
        except (TypeError, ValueError):
            raise d.Denied("invalid post-merge deadline") from None
        if timestamp.tzinfo is None or timestamp > now:
            raise d.Denied("invalid post-merge deadline")
        return now - timestamp >= self.post_merge_timeout

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
                return job.state
            # The durable deadline, not a mutable lifecycle state, controls
            # acceptance: a crash may leave an older PR_PENDING state while
            # the post-merge deadline file has already been committed.
            deadline_exists = self.deadline_file.exists()
            if deadline_exists:
                if self._check_deadline(job, now):
                    job.state = "BLOCKED"
                    d.save_state(self.state_file, job)
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
            d.save_state(self.state_file, job)
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
                stream.write(d.canonical({"approval_id": approval_id, "at": when.isoformat()}))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.deadline_file)
            # POSIX rename is not power-failure durable until the directory
            # entry is fsynced. This must happen BEFORE saving lifecycle state;
            # otherwise a surviving stale PR_PENDING state can drop the gate.
            if os.name != "nt":
                directory_fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            # Native Windows persistence/isolation remains NOT TESTED / NO_GO.
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