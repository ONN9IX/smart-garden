"""Synthetic, offline approval-ledger adapter; NOT a protected production registry.

Only a protected host installation with independently witnessed OS boundaries
could supply a real approval store. This module never grants runtime authority.
"""
from datetime import datetime
import os
from pathlib import Path
import re
import tempfile

import dispatcher as d

_KEYS = frozenset(("revoked", "consumed", "reserved"))
_ID = re.compile(r"[A-Za-z0-9-]{16,80}\Z")


def _empty():
    return {"revoked": [], "consumed": [], "reserved": {}}


def _validate(state):
    if not isinstance(state, dict) or set(state) != _KEYS:
        raise d.Denied("invalid synthetic ledger")
    for field in ("revoked", "consumed"):
        values = state[field]
        if (not isinstance(values, list) or len(values) != len(set(map(str, values)))
                or any(not isinstance(s, str) or not _ID.fullmatch(s) for s in values)):
            raise d.Denied("invalid synthetic ledger")
    reserved = state["reserved"]
    if not isinstance(reserved, dict) or len(reserved) > 500:
        raise d.Denied("invalid synthetic ledger")
    for key, record in reserved.items():
        if (not isinstance(key, str) or not _ID.fullmatch(key)
                or not isinstance(record, dict) or record.get("id") != key):
            raise d.Denied("invalid synthetic ledger")
    if (set(state["consumed"]) & set(reserved)
            or set(state["revoked"]) & set(reserved)):
        raise d.Denied("invalid synthetic ledger")
    return state


class SyntheticApprovalStore:
    """Durable simulation over an existing disposable directory; never production.

    Trust-root custody, ACL equivalence, signature provenance and host attestation
    are OUTSIDE this class. The caller must not treat return values as GO.
    """

    def __init__(self, directory):
        self.directory = Path(directory)
        if (not self.directory.is_dir() or self.directory.is_symlink()
                or getattr(self.directory.lstat(), "st_file_attributes", 0) & 1024):
            raise d.Denied("untrusted synthetic directory")
        self.path = self.directory / "approval-ledger.json"
        self.lock = self.directory / "approval-ledger.lock"

    def _read(self):
        if not self.path.exists():
            if self.path.is_symlink():
                raise d.Denied("ledger link")
            return _empty()
        if self.path.is_symlink() or self.path.stat().st_nlink != 1:
            raise d.Denied("ledger link")
        return _validate(d.load_json(self.path))

    def _write(self, state):
        _validate(state)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", dir=self.directory, prefix="ledger-",
                                             delete=False) as output:
                temporary = Path(output.name)
                output.write(d.canonical(state))
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.path)
            if os.name != "nt":
                fd = os.open(self.directory, os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    def reserve(self, envelope, trust_root, *, main, now):
        """Record one synthetic reservation only after existing RSA verification."""
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise d.Denied("invalid time")
        with d.global_lock(self.lock):
            state = self._read()
            record = d.verified_approval(envelope, trust_root, main=main, now=now,
                                         revoked=set(state["revoked"]),
                                         consumed=set(state["consumed"]))
            ident = record["id"]
            if ident in state["reserved"]:
                raise d.Denied("duplicate reservation")
            state["reserved"][ident] = record
            self._write(state)
            return dict(record)

    def check(self, envelope, trust_root, *, main, now):
        """Recheck signature, expiry, revocation and exact stored reservation."""
        with d.global_lock(self.lock):
            state = self._read()
            record = d.verified_approval(envelope, trust_root, main=main, now=now,
                                         revoked=set(state["revoked"]),
                                         consumed=set(state["consumed"]))
            if state["reserved"].get(record["id"]) != record:
                raise d.Denied("unreserved approval")
            return dict(record)

    def _transition(self, ident, field):
        if not isinstance(ident, str) or not _ID.fullmatch(ident):
            raise d.Denied("invalid approval identity")
        with d.global_lock(self.lock):
            state = self._read()
            if field == "consumed" and ident not in state["reserved"]:
                raise d.Denied("cannot consume unreserved approval")
            if ident in state["consumed"] or ident in state["revoked"]:
                raise d.Denied("replay or revoked approval")
            state["reserved"].pop(ident, None)
            state[field].append(ident)
            state[field].sort()
            self._write(state)

    def revoke(self, ident):
        self._transition(ident, "revoked")

    def consume(self, ident):
        self._transition(ident, "consumed")


def require_live_store():
    raise d.Denied("NO_GO: owner-protected approval registry not provisioned")
