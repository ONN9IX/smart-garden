"""Synthetic, offline approval-ledger adapter; NOT a protected production registry.

Only a protected host installation with independently witnessed OS boundaries
could supply a real approval store. This module never grants runtime authority.
"""
import hashlib
import json
import os
import re
import stat
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

import dispatcher as d

_KEYS = frozenset(("revoked", "consumed", "reserved"))
_ID = re.compile(r"[A-Za-z0-9-]{16,80}\Z")


def _empty():
    return {"revoked": [], "consumed": [], "reserved": {}}


def read_fixture_json(path):
    """Bounded handle-based JSON read, no links, payloads or raw error output.

    Protected parent custody is still a host prerequisite, not a Python promise.
    """
    path = Path(path)
    fd = None
    try:
        for ancestor in (path.parent, *path.parent.parents):
            info = ancestor.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 1024:
                raise d.Denied("unsafe fixture ancestor")
        before = path.lstat()
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or getattr(before, "st_file_attributes", 0) & 1024):
            raise d.Denied("unsafe fixture record")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                     | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0))
        opened = os.fstat(fd)
        if ((opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
                or opened.st_nlink != 1 or opened.st_size > 1024 * 1024):
            raise d.Denied("fixture record replaced or oversized")
        with os.fdopen(fd, "rb") as stream:
            fd = None
            raw = stream.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise d.Denied("oversized fixture record")
        return json.loads(raw.decode("utf-8"), object_pairs_hook=d.unique_object)
    except (OSError, UnicodeError, ValueError, TypeError):
        raise d.Denied("invalid fixture record") from None
    finally:
        if fd is not None:
            os.close(fd)


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


@contextmanager
def synthetic_lock(path):
    """Lock a disposable fixture using a checked file handle, never a followed link.

    POSIX O_NOFOLLOW closes the final-symlink race; native Windows reparse/ACL
    acceptance remains NOT TESTED and this is not a privileged host lock.
    """
    path = Path(path)
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_BINARY", 0)
    if os.name != "nt":
        if not hasattr(os, "O_NOFOLLOW"):
            raise d.Denied("safe synthetic lock unavailable")
        flags |= os.O_NOFOLLOW

    def checked(info):
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or getattr(info, "st_file_attributes", 0) & 1024):
            raise d.Denied("unsafe synthetic lock")

    fd = None
    locked = False
    try:
        if os.path.lexists(path):
            checked(path.lstat())
        fd = os.open(path, flags, 0o600)
        info = os.fstat(fd)
        checked(info)
        path_info = path.lstat()
        checked(path_info)
        if (path_info.st_dev, path_info.st_ino) != (info.st_dev, info.st_ino):
            raise d.Denied("synthetic lock replaced")
        if os.name == "nt":
            import msvcrt
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        locked = True
        final = path.lstat()
        checked(final)
        if (final.st_dev, final.st_ino) != (info.st_dev, info.st_ino):
            raise d.Denied("synthetic lock replaced")
        if os.fstat(fd).st_size == 0:
            os.lseek(fd, 0, os.SEEK_SET)
            os.write(fd, b"0")
            os.fsync(fd)
        yield
    except OSError:
        raise d.Denied("unsafe synthetic lock") from None
    finally:
        if fd is not None:
            if locked:
                try:
                    if os.name == "nt":
                        import msvcrt
                        os.lseek(fd, 0, os.SEEK_SET)
                        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(fd, fcntl.LOCK_UN)
                finally:
                    os.close(fd)
            else:
                os.close(fd)


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
        return _validate(read_fixture_json(self.path))

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
        with synthetic_lock(self.lock):
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
        with synthetic_lock(self.lock):
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
        with synthetic_lock(self.lock):
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


def fingerprint(record):
    return hashlib.sha256(d.canonical(record)).hexdigest()


def fixture_time(value):
    try:
        result = datetime.fromisoformat(value)
        if result.tzinfo is None:
            raise ValueError()
        return result
    except (TypeError, ValueError):
        raise d.Denied("invalid fixture clock") from None


_DELIVERY_STATES = frozenset(("READY", "RUNNING", "TEST_PASS", "TEST_FAIL",
                            "WAITING_FOR_OWNER", "POST_MERGE_CI", "DONE", "BLOCKED"))
_ATTEMPT_STATES = frozenset(("RESERVED", "TEST_PASS", "TEST_FAIL", "CANCELLED",
                           "TIMED_OUT", "BUDGET_EXCEEDED"))


def validate_delivery_ledger(state):
    """One atomic document binds scope, reservations, budget and lifecycle.

    Only minimized synthetic IDs, SHA values, timestamps and enums are stored.
    """
    if (not isinstance(state, dict)
            or set(state) != {"schema", "revoked", "consumed", "delivery"}
            or type(state["schema"]) is not int or state["schema"] != 1):
        raise d.Denied("invalid delivery ledger")
    for key in ("revoked", "consumed"):
        values = state[key]
        if (not isinstance(values, list) or len(values) > 500
                or any(type(v) is not str or not _ID.fullmatch(v) for v in values)
                or values != sorted(set(values))):
            raise d.Denied("invalid delivery identities")
    delivery = state["delivery"]
    if delivery is None:
        return state
    fields = {"record", "fingerprint", "state", "attempts", "started", "deadline",
              "max_tokens", "attempt_tokens", "attempt_seconds", "head", "pr",
              "merge_sha", "post_deadline", "polls"}
    if not isinstance(delivery, dict) or set(delivery) != fields:
        raise d.Denied("invalid delivery reservation")
    record = delivery["record"]
    started = fixture_time(delivery["started"])
    try:
        d.authorize(record, main=record["base"], now=started,
                    revoked=set(), consumed=set())
    except (KeyError, TypeError):
        raise d.Denied("invalid reserved scope") from None
    if (delivery["fingerprint"] != fingerprint(record)
            or not isinstance(delivery["state"], str)
            or delivery["state"] not in _DELIVERY_STATES
            or not started < fixture_time(delivery["deadline"]) <= fixture_time(record["expires"])
            or (fixture_time(delivery["deadline"]) - started).total_seconds() > 600):
        raise d.Denied("invalid reserved limits")
    for name, upper in (("max_tokens", 4096), ("attempt_tokens", 1024),
                        ("attempt_seconds", 120)):
        if type(delivery[name]) is not int or not 1 <= delivery[name] <= upper:
            raise d.Denied("invalid reserved budget")
    attempts = delivery["attempts"]
    if not isinstance(attempts, list) or len(attempts) > record["max_repairs"] + 1:
        raise d.Denied("invalid attempt ledger")
    for index, attempt in enumerate(attempts):
        if (not isinstance(attempt, dict) or set(attempt) != {"id", "status", "tokens"}
                or type(attempt["id"]) is not int or attempt["id"] != index
                or not isinstance(attempt["status"], str)
                or attempt["status"] not in _ATTEMPT_STATES
                or type(attempt["tokens"]) is not int
                or attempt["tokens"] != delivery["attempt_tokens"]):
            raise d.Denied("invalid attempt reservation")
    if sum(a["tokens"] for a in attempts) > delivery["max_tokens"]:
        raise d.Denied("invalid spent budget")
    if any(a["status"] != "TEST_FAIL" for a in attempts[:-1]):
        raise d.Denied("attempt history regression")
    if delivery["state"] == "READY" and attempts:
        raise d.Denied("attempt reservation rewound")
    required_outcome = {"RUNNING": "RESERVED", "TEST_PASS": "TEST_PASS",
                        "TEST_FAIL": "TEST_FAIL", "WAITING_FOR_OWNER": "TEST_PASS",
                        "POST_MERGE_CI": "TEST_PASS", "DONE": "TEST_PASS"}.get(delivery["state"])
    if required_outcome is not None and (not attempts or attempts[-1]["status"] != required_outcome):
        raise d.Denied("inconsistent delivery outcome")
    for key in ("head", "merge_sha"):
        if delivery[key] != "" and (type(delivery[key]) is not str or not d.SHA.fullmatch(delivery[key])):
            raise d.Denied("invalid reserved SHA")
    if (delivery["pr"] is not None
            and (type(delivery["pr"]) is not int or delivery["pr"] <= 0)):
        raise d.Denied("invalid reserved PR")
    if type(delivery["polls"]) is not int or not 0 <= delivery["polls"] <= 20:
        raise d.Denied("invalid post-merge polls")
    if delivery["post_deadline"] is not None:
        end = fixture_time(delivery["post_deadline"])
        if not started < end <= started + timedelta(days=2):
            raise d.Denied("invalid post-merge deadline")
    if delivery["state"] in ("WAITING_FOR_OWNER", "POST_MERGE_CI", "DONE") and (
            not delivery["head"] or delivery["pr"] is None):
        raise d.Denied("missing publication identity")
    if delivery["state"] in ("POST_MERGE_CI", "DONE") and (
            not delivery["merge_sha"] or delivery["post_deadline"] is None):
        raise d.Denied("missing post-merge identity")
    if delivery["state"] == "DONE" and record["id"] not in state["consumed"]:
        raise d.Denied("unconsumed completed delivery")
    if record["id"] in state["consumed"] and delivery["state"] != "DONE":
        raise d.Denied("consumed active delivery")
    if record["id"] in state["revoked"] and delivery["state"] != "BLOCKED":
        raise d.Denied("revoked active delivery")
    return state


class SyntheticDeliveryStore(SyntheticApprovalStore):
    """A3 TEST-ONLY transaction store, never install with live keys.

    The initialization marker is committed first. A missing/corrupt journal
    after initialization is denied instead of silently resetting replay state.
    One shared lock serializes ALL controller operations in this directory.
    """

    def __init__(self, directory):
        super().__init__(directory)
        self.path = self.directory / "delivery-ledger.json"
        self.marker = self.directory / "delivery-initialized.json"
        self.lock = self.directory / "controller.lock"

    def initialize(self):
        with synthetic_lock(self.lock):
            if os.path.lexists(self.marker) or os.path.lexists(self.path):
                raise d.Denied("fixture already initialized or ambiguous")
            # First reserve the namespace; a crash here MUST require recovery.
            original = self.path
            self.path = self.marker
            try:
                self._commit({"schema": 1})
            finally:
                self.path = original
            self.commit({"schema": 1, "revoked": [], "consumed": [], "delivery": None})

    def _commit(self, state):
        # Same atomic, unpredictable-temp-file path as A2, different schema.
        temporary = None
        try:
            d.inspect_path(self.directory, self.path.name)
            with tempfile.NamedTemporaryFile("wb", dir=self.directory,
                                             prefix="delivery-", delete=False) as output:
                temporary = Path(output.name)
                output.write(d.canonical(state))
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.path)
            if os.name != "nt":
                fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
        except OSError:
            raise d.Denied("fixture persistence unavailable") from None
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()

    def commit(self, state):
        """Caller holds shared lock; reserve before fake effects and acknowledge after fsync."""
        self._commit(validate_delivery_ledger(state))

    @contextmanager
    def transaction(self):
        with synthetic_lock(self.lock):
            marker = read_fixture_json(self.marker)
            if (marker != {"schema": 1} or type(marker.get("schema")) is not int):
                raise d.Denied("invalid initialization marker")
            yield validate_delivery_ledger(read_fixture_json(self.path))

    def revoke_delivery(self, ident):
        if not isinstance(ident, str) or not _ID.fullmatch(ident):
            raise d.Denied("invalid approval identity")
        with self.transaction() as state:
            if ident in state["consumed"] or ident in state["revoked"]:
                raise d.Denied("replayed revocation")
            state["revoked"] = sorted([*state["revoked"], ident])
            job = state["delivery"]
            if job is not None and job["record"]["id"] == ident:
                job["state"] = "BLOCKED"
            self.commit(state)
