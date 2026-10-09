"""Offline controller core. No model launch, credentials, network or publication adapter.

Deploy only from an owner-protected copy outside the agent workspace. Repository
code and supplied public keys are not trust anchors. See SECURITY.md.
"""
import argparse
import base64
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re

REPO = "ONN9IX/smart-garden"
CI = frozenset(("Backend quality", "Frontend quality", "Dependency security",
                "Browser auth flow (Frontend → Backend → PostgreSQL)",
                "Local browser preview (Docker Compose)", "PostgreSQL backup and recovery",
                "Backend checks", "Frontend checks"))
SHA = re.compile(r"[0-9a-f]{40}")


class Denied(ValueError):
    """A trust boundary failed; never include untrusted payloads in this error."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Denied("duplicate JSON field")
        result[key] = value
    return result


def load_json(path):
    if path.stat().st_size > 1024 * 1024:
        raise Denied("oversized record")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def verify_signature(record, signature, modulus, exponent=65537):
    """Strict RSA PKCS#1 v1.5 SHA256; owner public root must be OS protected."""
    if type(modulus) is not int or modulus.bit_length() < 3072 or exponent != 65537:
        raise Denied("invalid trust root")
    try:
        raw = base64.b64decode(signature, validate=True)
    except (ValueError, TypeError):
        raise Denied("invalid signature") from None
    size = (modulus.bit_length() + 7) // 8
    if len(raw) != size or int.from_bytes(raw, "big") >= modulus:
        raise Denied("invalid signature")
    digest = bytes.fromhex("3031300d060960864801650304020105000420") + hashlib.sha256(canonical(record)).digest()
    expected = b"\x00\x01" + b"\xff" * (size - len(digest) - 3) + b"\x00" + digest
    if pow(int.from_bytes(raw, "big"), exponent, modulus).to_bytes(size, "big") != expected:
        raise Denied("signature verification failed")


def exact_path(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise Denied("invalid path")
    parts = value.split("/")
    if PurePosixPath(value).is_absolute() or any(p in ("", ".", "..") for p in parts):
        raise Denied("invalid path")
    for part in parts:
        if part.endswith((".", " ")) or not re.fullmatch(r"[A-Za-z0-9_.-]+", part):
            raise Denied("invalid path")
        if part.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(10)), *(f"LPT{i}" for i in range(10))}:
            raise Denied("device path")
    if any(p.lower() in (".git", ".github", ".codex", ".ssh", ".aws") for p in parts):
        raise Denied("protected path")
    return value


def inspect_path(root, name):
    """Reject links and Windows reparse points on every existing ancestor."""
    target = root.absolute()
    for component in (target, *target.parents):
        if component.is_symlink() or (component.lstat().st_file_attributes & 1024 if hasattr(component.lstat(), "st_file_attributes") else False):
            raise Denied("reparse point")
    for part in exact_path(name).split("/"):
        target /= part
        if target.exists() or target.is_symlink():
            info = target.lstat()
            if target.is_symlink() or getattr(info, "st_file_attributes", 0) & 1024:
                raise Denied("reparse point")
            if target.is_file() and info.st_nlink != 1:
                raise Denied("hardlink")
    return target


def authorize(record, *, main, now, revoked, consumed):
    fields = {"id", "repo", "issue", "base", "branch", "paths", "expires", "max_repairs"}
    if not isinstance(record, dict) or set(record) != fields:
        raise Denied("invalid approval schema")
    if record["repo"] != REPO or type(record["issue"]) is not int or record["issue"] <= 0:
        raise Denied("foreign approval")
    if not isinstance(record["base"], str) or not SHA.fullmatch(record["base"]) or record["base"] != main:
        raise Denied("stale baseline")
    if not re.fullmatch(r"[a-zA-Z0-9-]{16,80}", record["id"]):
        raise Denied("invalid approval identity")
    if record["id"] in revoked or record["id"] in consumed:
        raise Denied("revoked or replayed approval")
    if not isinstance(record["branch"], str) or not re.fullmatch(r"(?:automation|codex)/[A-Za-z0-9-]+", record["branch"]):
        raise Denied("branch mismatch")
    try:
        expiry = datetime.fromisoformat(record["expires"])
        if expiry.tzinfo is None or expiry <= now:
            raise Denied("expired approval")
    except (TypeError, ValueError):
        raise Denied("invalid expiry") from None
    paths = record["paths"]
    if not isinstance(paths, list) or not paths or len(paths) > 500:
        raise Denied("invalid write set")
    normalized = [exact_path(p).casefold() for p in paths]
    if len(set(normalized)) != len(paths) or paths != sorted(paths):
        raise Denied("noncanonical write set")
    if type(record["max_repairs"]) is not int or not 0 <= record["max_repairs"] <= 3:
        raise Denied("invalid repair budget")
    return record


def verified_approval(envelope, modulus, **context):
    """Single entry gate for a future trusted controller, not workspace authority."""
    if not isinstance(envelope, dict) or set(envelope) != {"record", "signature"}:
        raise Denied("invalid signed envelope")
    verify_signature(envelope["record"], envelope["signature"], modulus)
    return authorize(envelope["record"], **context)


def next_delivery(active, candidates):
    """Candidates must already pass verified_approval; serialize all delivery work."""
    if active is not None and active.state != "DONE":
        return active
    if not candidates:
        return None
    if len({a["id"] for a in candidates}) != len(candidates) or len({a["issue"] for a in candidates}) != len(candidates):
        raise Denied("ambiguous delivery queue")
    chosen = candidates[0]
    return Delivery(chosen["id"], chosen["issue"], chosen["base"], chosen["branch"])


def validate_changes(root, approval, entries):
    """Publisher must build entries from its own Git objects, never worker status."""
    seen = set()
    for entry in entries:
        if set(entry) != {"path", "mode", "blob", "status"}:
            raise Denied("invalid diff")
        path = exact_path(entry["path"])
        if path not in approval["paths"] or path.casefold() in seen:
            raise Denied("write set escape")
        seen.add(path.casefold())
        if entry["mode"] != "100644" or entry["status"] not in ("A", "M", "D") or not SHA.fullmatch(entry["blob"]):
            raise Denied("unsafe Git object")
        inspect_path(root, path)


def ci_passed(checks, head):
    if not isinstance(head, str) or not SHA.fullmatch(head) or not isinstance(checks, list) or len(checks) != 8:
        return False
    return ({c.get("name") for c in checks if isinstance(c, dict)} == CI
            and all(c.get("head_sha") == head and c.get("status") == "completed"
                    and c.get("conclusion") == "success" for c in checks))


@dataclass
class Delivery:
    approval_id: str
    issue: int
    base: str
    branch: str
    state: str = "READY"
    head: str = ""
    pr: int | None = None
    repairs: int = 0

    def observe(self, approval, snapshot):
        """Validated controller snapshot only. No Issue/PR prose is interpreted."""
        if self.approval_id != approval["id"] or self.issue != approval["issue"] or self.base != approval["base"] or self.branch != approval["branch"]:
            raise Denied("state identity mismatch")
        if self.state in ("DONE", "BLOCKED"):
            return self.state
        if snapshot["main"] != self.base and not snapshot.get("merged", False):
            self.state = "BLOCKED"
            return self.state
        prs = snapshot["prs"]
        if len(prs) > 1:
            raise Denied("overlapping PRs")
        if not prs:
            if self.pr is not None:
                raise Denied("existing PR disappeared")
            self.state = "READY"
            return self.state
        pr = prs[0]
        if pr["repo"] != REPO or pr["head_repo"] != REPO or pr["branch"] != self.branch or pr["base"] != "main" or type(pr["number"]) is not int or not SHA.fullmatch(pr["head"]):
            raise Denied("foreign or malformed PR")
        if self.pr is not None and self.pr != pr["number"]:
            raise Denied("duplicate PR")
        self.pr, self.head = pr["number"], pr["head"]
        if snapshot.get("merged", False):
            if not snapshot.get("owner_merge_verified", False) or not SHA.fullmatch(snapshot.get("merge_sha", "")):
                raise Denied("unverified merge")
            self.state = "DONE" if ci_passed(snapshot["post_merge_checks"], snapshot["merge_sha"]) else "POST_MERGE_CI"
        elif ci_passed(snapshot["checks"], self.head):
            self.state = "READY_FOR_MASTER_CHAT"
        elif snapshot.get("ci_failed", False):
            self.state = "CI_FIXING" if self.repairs < approval["max_repairs"] else "BLOCKED"
        else:
            self.state = "PR_PENDING"
        return self.state

    def begin_repair(self, approval):
        if self.state != "CI_FIXING" or self.repairs >= approval["max_repairs"]:
            raise Denied("repair not permitted")
        self.repairs += 1
        self.state = "RUNNING"


@contextmanager
def global_lock(path):
    """Kernel byte lock; crash releases it. Never delete a stale lock file."""
    with open(path, "a+b") as stream:
        stream.seek(0)
        if stream.read(1) == b"":
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            if os.name == "nt":
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def save_state(path, delivery):
    temporary = path.with_suffix(".tmp")
    with temporary.open("wb") as stream:
        stream.write(canonical(delivery.__dict__))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


STATES = frozenset(("WAITING_APPROVAL", "READY", "RUNNING", "PR_PENDING", "CI_FIXING",
                    "READY_FOR_MASTER_CHAT", "MERGE_PENDING", "POST_MERGE_CI", "BLOCKED", "DONE"))


def restore_state(path, approval):
    record = load_json(path)
    if not isinstance(record, dict) or set(record) != set(Delivery.__dataclass_fields__):
        raise Denied("invalid durable state")
    job = Delivery(**record)
    if (job.approval_id, job.issue, job.base, job.branch) != (approval["id"], approval["issue"], approval["base"], approval["branch"]):
        raise Denied("durable identity mismatch")
    if job.state not in STATES or type(job.repairs) is not int or not 0 <= job.repairs <= approval["max_repairs"]:
        raise Denied("invalid durable budget or state")
    if job.pr is not None and (type(job.pr) is not int or job.pr <= 0 or not isinstance(job.head, str) or not SHA.fullmatch(job.head)):
        raise Denied("invalid durable PR")
    # A crashed RUNNING delivery cannot automatically relaunch or spend twice.
    if job.state == "RUNNING":
        job.state = "BLOCKED"
    return job


def audit(path, delivery, when):
    """Append fixed metadata only, under the same owner-protected global lock."""
    if delivery.state not in STATES or not re.fullmatch(r"[A-Za-z0-9-]{16,80}", delivery.approval_id) or type(delivery.issue) is not int:
        raise Denied("invalid audit metadata")
    if when.tzinfo is None:
        raise Denied("invalid audit time")
    entry = dict(approval_id=delivery.approval_id, issue=delivery.issue,
                 state=delivery.state, at=when.isoformat())
    with path.open("ab") as stream:
        stream.write(canonical(entry) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def require_execution():
    # No configurable boolean / model-generated certificate can bypass this gate.
    raise Denied("NO_GO: OS isolation and credential transport not accepted; execution adapter absent")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", required=True)
    parser.parse_args()
    print(json.dumps({"execution": "DISABLED", "state": "WAITING_APPROVAL",
                      "isolation": "NOT_ACCEPTED", "publisher": "ABSENT",
                      "scheduler_install": "NOT_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
