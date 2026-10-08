"""Fail-closed allowlist policy for owner-authorized, scoped Smart Garden issues.

Input: GitHub issue and main SHA. Output: an immutable delivery scope, or rejection.
Syntax inspection only: a successful parse is NOT execution authorization.
The retired worker rejects all Issues independently of this parser.
"""
from dataclasses import dataclass
from pathlib import PurePosixPath
import re

REPO = 'ONN9IX/smart-garden'
OWNER = 'ONN9IX'
LABEL = 'ai:ready'
BLOCKED_EXACT = frozenset({
    'AGENTS.md', 'README.md', 'CONTRIBUTING.md', 'docs/CURRENT_STATE.md',
    '.gitignore', 'docker-compose.yml', 'docker-compose.preview.yml',
})
BLOCKED_PREFIXES = (
    '.git/', '.github/', '.codex/', '.agents/', 'automation/',
    'backend/alembic/', 'backend/migrations/', 'backend/app/models/',
    'backend/app/core/', 'backend/app/db/', 'docs/', 'scripts/',
)
ALLOWED_PREFIXES = ('frontend/', 'backend/')
# No product area is approved for autonomous writes in the no-VPS delivery.
EXECUTION_ALLOWED_PATHS = frozenset()

def validate_execution_paths(paths):
    if not paths or any(p not in EXECUTION_ALLOWED_PATHS for p in paths):
        raise ScopeError('No audited execution allowlist; autonomous writes prohibited')

SENSITIVE_NAMES = ('.env', 'secret', 'credential', 'auth.json', 'id_rsa', '.pem')

@dataclass(frozen=True)
class Scope:
    issue_number: int
    title: str
    base_sha: str
    paths: tuple[str, ...]
    body: str

class ScopeError(ValueError):
    pass

def validate_path(raw: str) -> str:
    if raw != raw.strip() or not raw or '\\' in raw or '\x00' in raw:
        raise ScopeError('Invalid or noncanonical path')
    path = PurePosixPath(raw)
    if path.is_absolute() or '..' in raw.split('/') or '.' in raw.split('/') or '//' in raw:
        raise ScopeError('Unsafe path')
    if not any(raw.startswith(p) for p in ALLOWED_PREFIXES):
        raise ScopeError('Path outside editable product tree')
    if raw in BLOCKED_EXACT or any(raw.startswith(p) for p in BLOCKED_PREFIXES):
        raise ScopeError('Protected/shared path requires Master Chat')
    if any(x in path.name.lower() for x in SENSITIVE_NAMES) or path.name.startswith('.'):
        raise ScopeError('Sensitive/hidden file cannot be edited automatically')
    parts = [part.lower() for part in path.parts]
    if any(re.search(r'(^|[_.-])(auth|authentication|authorization|rbac|tenant|sessions?|permissions?)([_.-]|$)', part) for part in parts):
        raise ScopeError('Security-critical path requires Master Chat')
    if path.name in {'package.json', 'package-lock.json', 'requirements.txt', 'pyproject.toml', 'Dockerfile'} or any('config' in part.lower() for part in path.parts):
        raise ScopeError('Dependency/config path requires Master Chat')
    return raw

def parse_issue(issue: dict, main_sha: str) -> Scope:
    if issue.get('pull_request') or issue.get('state') != 'open':
        raise ScopeError('Not an open Issue')
    if issue.get('user', {}).get('login') != OWNER:
        raise ScopeError('Issue must be authored by the owner')
    labels = {l.get('name') for l in issue.get('labels', [])}
    if LABEL not in labels:
        raise ScopeError('Issue not approved for automation')
    body = issue.get('body') or ''
    if not re.search(r'^AUTOMATION-AUTHORIZED: YES\s*$', body, re.M):
        raise ScopeError('Explicit owner authorization missing')
    if not re.search(r'^PARALLEL-SAFE: NO\s*$', body, re.M):
        raise ScopeError('Parallel delivery blocked by default')
    matches = re.findall(r'^BASE-SHA:\s*([0-9a-f]{40})\s*$', body, re.M)
    if len(matches) != 1 or matches[0] != main_sha:
        raise ScopeError('BASE-SHA must match current main exactly')
    scope_match = re.search(r'^WRITE-SET:\s*\n((?:- [^\n]+\n?)+)', body, re.M)
    if not scope_match:
        raise ScopeError('Explicit one-path-per-line WRITE-SET is required')
    paths = tuple(validate_path(s[2:].strip()) for s in scope_match.group(1).splitlines())
    if not paths or len(paths) > 30 or len(set(paths)) != len(paths):
        raise ScopeError('Invalid or duplicate WRITE-SET entries')
    if len(body) > 40000:
        raise ScopeError('Issue body too large')
    return Scope(int(issue['number']), (issue.get('title') or '').strip(), main_sha, paths, body)

def validate_changed_paths(changed: list[str], allowed: tuple[str, ...]):
    if not changed:
        raise ScopeError('No changes produced')
    for path in changed:
        validate_path(path)
        if path not in allowed:
            raise ScopeError('Changed file outside approved WRITE-SET: ' + path)
