"""Read-only raw-tree contract validator for synthetic, immutable Git snapshots.

Not a trusted publisher: GitHub authentication, filesystem provenance, worker
stoppage, and OS-exclusive snapshots remain NOT TESTED / NO_GO. This module
never runs Git, executes hooks/filters, opens credentials, or sends requests.
"""
from dataclasses import dataclass

import dispatcher as d

_FORBIDDEN = frozenset((".gitattributes", ".gitmodules", ".lfsconfig", ".gitconfig"))
_MODES = frozenset(("100644",))


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
    for name, object_ in entries.items():
        path = d.exact_path(name)
        if path.casefold() in seen or not isinstance(object_, SyntheticBlob):
            raise d.Denied("tree collision or malformed object")
        seen.add(path.casefold())
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
        if path.casefold() in {p.casefold() for p in _FORBIDDEN}:
            raise d.Denied("Git execution configuration changed")
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
