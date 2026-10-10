"""Read-only raw-tree contract validator for synthetic, immutable Git snapshots.

Not a trusted publisher: GitHub authentication, filesystem provenance, worker
stoppage, and OS-exclusive snapshots remain NOT TESTED / NO_GO. This module
never runs Git, executes hooks/filters, opens credentials, or sends requests.
"""
import hashlib
import json
import os
import re
import stat
import zlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import dispatcher as d

_FORBIDDEN = frozenset((".gitattributes", ".gitmodules", ".lfsconfig", ".gitconfig"))
_MODES = frozenset(("100644", "100755"))


def tree_path(value):
    # Existing workflow blobs may be inspected but can NEVER be changed by
    # a worker approval. All other protected namespaces retain #207 denial.
    if isinstance(value, str) and value.startswith(".github/"):
        d.exact_path("workflow/" + value[len(".github/"):])
        return value
    return d.exact_path(value)


@dataclass(frozen=True)
class SyntheticBlob:
    oid: str
    mode: str = "100644"
    kind: str = "blob"
    links: int = 1
    reparse: bool = False


def _inspect_tree(entries):
    """Validate *every* path/object, not merely model-provided changed files."""
    if not isinstance(entries, dict) or len(entries) > 20000:
        raise d.Denied("invalid raw tree")
    result = {}
    seen = set()
    prefixes = {}
    for name, object_ in entries.items():
        path = tree_path(name)
        if path.casefold() in seen or not isinstance(object_, SyntheticBlob):
            raise d.Denied("tree collision or malformed object")
        seen.add(path.casefold())
        parts = path.split("/")
        for index in range(1, len(parts) + 1):
            prefix = "/".join(parts[:index])
            previous = prefixes.setdefault(prefix.casefold(), (prefix, index != len(parts)))
            if previous != (prefix, index != len(parts)):
                raise d.Denied("tree directory alias or file collision")
        if (object_.mode not in _MODES or object_.kind != "blob"
                or not isinstance(object_.oid, str) or not d.SHA.fullmatch(object_.oid)
                or type(object_.links) is not int or object_.links != 1
                or type(object_.reparse) is not bool or object_.reparse):
            raise d.Denied("unsafe raw tree object")
        result[path] = object_
    return result


def validate_offline_delta(*, approval, old_tree, new_tree, main_sha,
                           expected_base, pr_head, reviewed_head, review_status):
    """Compute delta from full synthetic trees; returns NO_GO, never authority.

    All arguments are synthetic model-readable fixtures. The future publisher
    MUST independently collect raw objects and securely freeze the worker.
    """
    if (not isinstance(approval, dict) or set(approval) !=
            {"id", "repo", "issue", "base", "branch", "paths", "expires", "max_repairs"}):
        raise d.Denied("invalid approval")
    if (not isinstance(main_sha, str) or not d.SHA.fullmatch(main_sha)
            or main_sha != expected_base or main_sha != approval["base"]
            or not isinstance(pr_head, str) or not d.SHA.fullmatch(pr_head)
            or pr_head != reviewed_head or review_status != "SYNTHETIC_PASS"):
        raise d.Denied("stale base or review")
    if not isinstance(approval["paths"], list):
        raise d.Denied("invalid write set")
    paths = approval["paths"]
    if not paths or paths != sorted(paths) or len(paths) != len(set(p.casefold() for p in paths if isinstance(p, str))):
        raise d.Denied("invalid write set")
    for name in paths:
        d.exact_path(name)
    old, new = _inspect_tree(old_tree), _inspect_tree(new_tree)
    changed = []
    for path in sorted(set(old) | set(new)):
        if old.get(path) == new.get(path):
            continue
        if path.rsplit("/", 1)[-1].casefold() in _FORBIDDEN:
            raise d.Denied("Git execution configuration changed")
        if new.get(path) is not None and new[path].mode != "100644":
            raise d.Denied("executable delta")
        if path not in paths:
            raise d.Denied("write set escape")
        changed.append(path)
    if not changed:
        raise d.Denied("empty synthetic delta")
    return {"decision": "NO_GO", "evidence": "SYNTHETIC", "publisher": "ABSENT",
            "changed_count": len(changed), "changes": tuple(changed)}


def require_publication(*_args, **_kwargs):
    raise d.Denied("NO_GO: trusted publisher not provisioned")


def merge(*_args, **_kwargs):
    raise d.Denied("NO_GO: GitHub Merge adapter absent")


class SyntheticEvidenceFeed:
    """A finite, signed OFFLINE collector; never an authenticated GitHub client.

    Feed root/provider policy are supplied by the fixture coordinator, never
    derived from PR prose. Signatures authenticate synthetic fixtures only.
    """

    def __init__(self, envelopes):
        if not isinstance(envelopes, (list, tuple)) or not 1 <= len(envelopes) <= 2:
            raise d.Denied("invalid fixture feed")
        try:
            raw = d.canonical(envelopes)
            if len(raw) > 1024 * 1024:
                raise d.Denied("oversized fixture feed")
            self._envelopes = json.loads(raw, object_pairs_hook=d.unique_object)
        except (ValueError, TypeError):
            raise d.Denied("invalid fixture feed") from None
        self._cursor = 0

    def collect(self):
        if self._cursor == len(self._envelopes):
            raise d.Denied("fixture feed unavailable")
        result = self._envelopes[self._cursor]
        self._cursor += 1
        return json.loads(d.canonical(result), object_pairs_hook=d.unique_object)


@dataclass(frozen=True)
class SyntheticProviderPolicy:
    policy: str = "SAM-INACTIVE-A3"
    ci_app: int = 101
    review_app: int = 202
    reviewer: str = "INDEPENDENT_SYNTHETIC_REVIEWER"


def verify_fixture_evidence(envelope, root, *, approval, now, policy):
    """Strict synthetic provenance check. No online authority or live writes."""
    from approval_store import fixture_time
    from controller_core import SyntheticControllerCore
    if (type(policy) is not SyntheticProviderPolicy or not isinstance(now, datetime)
            or now.tzinfo is None or not isinstance(envelope, dict)
            or set(envelope) != {"record", "signature"}):
        raise d.Denied("invalid synthetic evidence envelope")
    record = envelope["record"]
    if (not isinstance(record, dict) or set(record) != {
            "schema", "evidence", "repo", "issue", "policy", "collected", "expires",
            "snapshot", "providers", "review"} or type(record["schema"]) is not int
            or record["schema"] != 1 or record["evidence"] != "SYNTHETIC"
            or record["repo"] != approval["repo"] or type(record["issue"]) is not int
            or record["issue"] != approval["issue"] or record["policy"] != policy.policy):
        raise d.Denied("foreign synthetic evidence")
    d.verify_signature(record, envelope["signature"], root)
    collected, expires = fixture_time(record["collected"]), fixture_time(record["expires"])
    if not collected <= now < expires <= collected + timedelta(seconds=60):
        raise d.Denied("stale synthetic evidence")
    event = record["snapshot"]
    if not isinstance(event, dict):
        raise d.Denied("invalid synthetic snapshot")
    SyntheticControllerCore._validate_snapshot(event, event.get("main"))
    if len(event["prs"]) != 1:
        raise d.Denied("ambiguous synthetic PR")
    pr = event["prs"][0]
    if (pr["repo"] != approval["repo"] or pr["head_repo"] != approval["repo"]
            or pr["branch"] != approval["branch"] or pr["base"] != "main"):
        raise d.Denied("foreign synthetic PR")
    if pr.get("merged", False) != event.get("merged", False):
        raise d.Denied("inconsistent synthetic merge state")
    if event.get("merged") is True:
        if event["merge_sha"] != event["main"] or pr.get("merge_commit_sha") != event["main"]:
            raise d.Denied("inconsistent synthetic merge SHA")
    elif "merge_commit_sha" in pr:
        raise d.Denied("unexpected synthetic merge commit")
    providers = record["providers"]
    if (not isinstance(providers, dict) or set(providers) != d.CI
            or any(type(app) is not int or app != policy.ci_app for app in providers.values())):
        raise d.Denied("untrusted synthetic CI provider")
    review = record["review"]
    if (not isinstance(review, dict) or set(review) != {
            "head", "app", "reviewer", "policy", "status", "blocking"}
            or review["head"] != pr["head"] or type(review["app"]) is not int
            or review["app"] != policy.review_app or review["reviewer"] != policy.reviewer
            or review["policy"] != policy.policy or review["status"] != "SYNTHETIC_PASS"
            or review["blocking"] is not False):
        raise d.Denied("invalid independent synthetic review")
    if event.get("merged") is not True and event["main"] != approval["base"]:
        raise d.Denied("stale synthetic main")
    return json.loads(d.canonical(event), object_pairs_hook=d.unique_object)


def verify_fixture_candidate(*, approval, feed, evidence_root, now, policy,
                             old_tree, new_tree):
    """Recollect after tree checks to detect head/base/review/revocation drift.

    Caller independently rechecks signed approval in its shared ledger lock.
    Tree inputs here are immutable synthetic fixtures, NOT worker diff evidence.
    """
    if type(feed) is not SyntheticEvidenceFeed:
        raise d.Denied("untrusted evidence collector")
    first = verify_fixture_evidence(feed.collect(), evidence_root,
                                   approval=approval, now=now, policy=policy)
    if first.get("merged") or not d.ci_passed(first["checks"], first["prs"][0]["head"]):
        raise d.Denied("synthetic candidate CI incomplete")
    report = validate_offline_delta(approval=approval, old_tree=old_tree, new_tree=new_tree,
        main_sha=first["main"], expected_base=approval["base"],
        pr_head=first["prs"][0]["head"], reviewed_head=first["prs"][0]["head"],
        review_status="SYNTHETIC_PASS")
    second = verify_fixture_evidence(feed.collect(), evidence_root,
                                    approval=approval, now=now, policy=policy)
    if first != second:
        raise d.Denied("synthetic publication evidence changed")
    return report | {"head": first["prs"][0]["head"], "pr": first["prs"][0]["number"]}


class LooseFixtureGitReader:
    """Read/hash raw loose Git objects from a STOPPED disposable fixture only.

    No Git subprocess/config/hooks/filters/credential helpers are evaluated.
    Packed objects, alternates, indirection and unsupported modes fail closed.
    An advisory fixture lock cannot stop a malicious OS writer: host-exclusive
    stopped-worker custody remains NOT TESTED. Never treat this as live GO.
    """
    MAX_OBJECT = 8 * 1024 * 1024
    MAX_TOTAL = 64 * 1024 * 1024

    def __init__(self, directory):
        self.root = Path(directory).absolute()
        self.git = self.root / ".git"
        self.total = 0
        self.identities = {}
        try:
            for path in (self.git, self.root, *self.root.parents):
                info = path.lstat()
                if (not stat.S_ISDIR(info.st_mode)
                        or getattr(info, "st_file_attributes", 0) & 1024):
                    raise d.Denied("unsafe Git fixture root")
            for path in (self.git / "objects/info/alternates",
                         self.git / "objects/info/http-alternates", self.git / "commondir",
                         self.git / "shallow", self.git / "info/grafts", self.git / "refs/replace"):
                if os.path.lexists(path):
                    raise d.Denied("Git object indirection")
            pack = self.git / "objects/pack"
            if os.path.lexists(pack):
                d.inspect_path(self.git, "objects/pack")
                if any(pack.iterdir()):
                    raise d.Denied("packed Git fixture unsupported")
        except OSError:
            raise d.Denied("Git fixture unavailable") from None

    def _read(self, relative, limit):
        fd = None
        try:
            path = d.inspect_path(self.git, relative)
            before = path.lstat()
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit:
                raise d.Denied("unsafe Git fixture file")
            fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                         | getattr(os, "O_BINARY", 0) | getattr(os, "O_NONBLOCK", 0))
            info = os.fstat(fd)
            if ((info.st_dev, info.st_ino) != (before.st_dev, before.st_ino)
                    or info.st_nlink != 1 or info.st_size > limit):
                raise d.Denied("Git fixture replaced")
            with os.fdopen(fd, "rb") as stream:
                fd = None
                value = stream.read(limit + 1)
            if len(value) > limit:
                raise d.Denied("oversized Git fixture")
            self.identities[relative] = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
            return value
        except OSError:
            raise d.Denied("Git fixture unavailable") from None
        finally:
            if fd is not None:
                os.close(fd)

    def object(self, oid, expected):
        if type(oid) is not str or not d.SHA.fullmatch(oid):
            raise d.Denied("invalid Git object ID")
        compressed = self._read("objects/" + oid[:2] + "/" + oid[2:], self.MAX_OBJECT)
        try:
            decompressor = zlib.decompressobj()
            raw = decompressor.decompress(compressed, self.MAX_OBJECT + 1)
            self.total += len(raw)
            if (len(raw) > self.MAX_OBJECT or self.total > self.MAX_TOTAL
                    or not decompressor.eof or decompressor.unused_data
                    or hashlib.sha1(raw).hexdigest() != oid):
                raise d.Denied("corrupt or oversized Git object")
            header, content = raw.split(b"\0", 1)
            if header != expected.encode("ascii") + b" " + str(len(content)).encode("ascii"):
                raise d.Denied("Git object type mismatch")
            return content
        except (ValueError, zlib.error):
            raise d.Denied("corrupt Git fixture object") from None

    def tree(self, commit):
        content = self.object(commit, "commit")
        first = content.split(b"\n", 1)[0]
        if not first.startswith(b"tree ") or len(first) != 45:
            raise d.Denied("invalid Git fixture commit")
        try:
            tree_id = first[5:].decode("ascii")
        except UnicodeError:
            raise d.Denied("invalid Git fixture commit") from None
        entries = {}

        def walk(oid, prefix, depth):
            if depth > 32 or len(entries) > 20000:
                raise d.Denied("oversized Git fixture tree")
            raw = self.object(oid, "tree")
            position = 0
            names = set()
            previous_key = None
            while position < len(raw):
                end = raw.find(b"\0", position)
                if end < 0 or end + 21 > len(raw):
                    raise d.Denied("invalid raw Git tree")
                try:
                    mode, name = raw[position:end].decode("ascii").split(" ", 1)
                except (UnicodeError, ValueError):
                    raise d.Denied("invalid raw Git path") from None
                if "/" in name or name.casefold() in names:
                    raise d.Denied("aliased raw Git tree")
                # Git base_name_compare orders a directory as name + '/',
                # and a blob as name + NUL; sorting bare names is insufficient.
                key = name.encode("ascii") + (b"/" if mode == "40000" else b"\0")
                if previous_key is not None and key <= previous_key:
                    raise d.Denied("noncanonical raw Git tree order")
                previous_key = key
                names.add(name.casefold())
                path = tree_path(prefix + name)
                child = raw[end + 1:end + 21].hex()
                position = end + 21
                if mode == "40000":
                    walk(child, path + "/", depth + 1)
                elif mode in _MODES:
                    self.object(child, "blob")
                    entries[path] = SyntheticBlob(child, mode=mode)
                else:
                    raise d.Denied("unsafe Git fixture mode")
        walk(tree_id, "", 0)
        return _inspect_tree(entries)

    def verify_refs(self, branch, base, head):
        if type(branch) is not str or not re.fullmatch(r"(?:automation|codex)/[A-Za-z0-9-]+", branch):
            raise d.Denied("invalid fixture branch")
        if (self._read("HEAD", 256) != ("ref: refs/heads/" + branch + "\n").encode()
                or self._read("refs/heads/" + branch, 64) != (head + "\n").encode()
                or self._read("refs/heads/main", 64) != (base + "\n").encode()):
            raise d.Denied("Git fixture refs drift")

    def verify_ancestry(self, base, head):
        seen = set()
        current = head
        for _ in range(64):
            if current == base:
                return
            if current in seen:
                break
            seen.add(current)
            commit = self.object(current, "commit")
            headers = commit.split(b"\n\n", 1)[0].split(b"\n")
            parents = [line[7:] for line in headers if line.startswith(b"parent ")]
            if len(parents) != 1:
                break
            try:
                current = parents[0].decode("ascii")
            except UnicodeError:
                break
        raise d.Denied("Git fixture baseline ancestry unproven")

    def recheck(self):
        for relative, identity in self.identities.items():
            try:
                path = d.inspect_path(self.git, relative)
                info = path.lstat()
                if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns) != identity:
                    raise d.Denied("Git fixture changed during inspection")
            except OSError:
                raise d.Denied("Git fixture changed during inspection") from None


def verify_loose_fixture_candidate(*, directory, approval, feed, evidence_root, now, policy):
    """Read raw objects independently of model diff; fixture custody is not OS enforcement."""
    if type(feed) is not SyntheticEvidenceFeed:
        raise d.Denied("untrusted fixture feed")
    before = feed.collect()
    event = verify_fixture_evidence(before, evidence_root, approval=approval, now=now, policy=policy)
    reader = LooseFixtureGitReader(directory)
    head = event["prs"][0]["head"]
    reader.verify_refs(approval["branch"], approval["base"], head)
    reader.verify_ancestry(approval["base"], head)
    old_tree, new_tree = reader.tree(approval["base"]), reader.tree(head)
    report = verify_fixture_candidate(approval=approval,
        feed=SyntheticEvidenceFeed((before, feed.collect())), evidence_root=evidence_root,
        now=now, policy=policy, old_tree=old_tree, new_tree=new_tree)
    reader.verify_refs(approval["branch"], approval["base"], head)
    reader.recheck()
    return report
