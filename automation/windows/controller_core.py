"""Offline lifecycle harness using #207's fail-closed delivery primitives.

No GitHub adapter, OS provisioning, signer, model launcher, or publisher exists.
Inputs are synthetic snapshots, NOT an authenticated live GitHub feed.
"""
from datetime import datetime, timedelta
from pathlib import Path

import dispatcher as d


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

    def tick(self, *, envelope, public_root, snapshot, main, now,
             revoked=frozenset(), consumed=frozenset(), merge_evidence=None,
             merge_root=None):
        """Never fetch, execute or publish; only inspect supplied fake snapshots."""
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise d.Denied("invalid clock")
        if not isinstance(snapshot, dict) or snapshot.get("main") != main:
            raise d.Denied("untrusted snapshot identity")
        if not isinstance(revoked, (set, frozenset)) or not isinstance(consumed, (set, frozenset)):
            raise d.Denied("invalid revocation state")
        with d.global_lock(self.lock):
            approval = d.verified_approval(envelope, public_root, main=main
                      if not snapshot.get("merged") else envelope["record"].get("base"),
                      now=now, revoked=revoked, consumed=consumed)
            job = self._current(approval)
            if job.state == "DONE":
                return "DONE"
            if job.state == "BLOCKED":
                return "BLOCKED"
            state = job.observe(approval, snapshot, merge_evidence=merge_evidence,
                                owner_modulus=merge_root)
            if state == "POST_MERGE_CI":
                if self.deadline_file.exists():
                    deadline = d.load_json(self.deadline_file)
                    if not isinstance(deadline, dict) or set(deadline) != {"approval_id", "at"} or deadline["approval_id"] != job.approval_id:
                        raise d.Denied("invalid post-merge deadline")
                    try:
                        timestamp = datetime.fromisoformat(deadline["at"])
                    except (ValueError, TypeError):
                        raise d.Denied("invalid post-merge deadline") from None
                    if timestamp.tzinfo is None or timestamp > now:
                        raise d.Denied("invalid post-merge deadline")
                    if now - timestamp >= self.post_merge_timeout:
                        job.state = "BLOCKED"
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
