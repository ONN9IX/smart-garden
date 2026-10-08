"""Retired executor: read-only legacy CI monitor, fail-closed.

Inputs: authenticated local /tick. Outputs: existing PR CI status events only.
Issue metadata, environment flags and direct helper calls cannot start execution.
No automatic merge, deployment, production data access or auth-token disclosure.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import stat
import subprocess
import threading
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from policy import REPO, ScopeError, validate_changed_paths

HOST = '0.0.0.0'
PORT = 8080
ROOT = Path('/workspace')
METADATA_DIR = ROOT / 'private-git'
STATE_FILE = ROOT / 'state.json'
GITHUB_API = 'https://api.github.com/repos/' + REPO
GH_TOKEN_FILE = Path('/run/secrets/github_token')
WORKER_KEY_FILE = Path('/run/secrets/worker_key')
EXPECTED_CI = {
    'Backend quality', 'Frontend quality', 'Dependency security',
    'Browser auth flow (Frontend → Backend → PostgreSQL)',
    'Local browser preview (Docker Compose)', 'PostgreSQL backup and recovery',
    'Backend checks', 'Frontend checks',
}
_lock = threading.RLock()
_busy = False


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def secret(path: Path) -> str:
    return path.read_text(encoding='utf-8').strip()


def load_state():
    if not STATE_FILE.exists():
        return {'issues': {}, 'events': [], 'next_event_id': 1}
    return json.loads(STATE_FILE.read_text(encoding='utf-8'))


def save_state(data):
    ROOT.mkdir(parents=True, exist_ok=True)
    temp = STATE_FILE.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.chmod(temp, 0o600)
    temp.replace(STATE_FILE)


def publish(message: str, url: str | None = None):
    with _lock:
        data = load_state()
        next_id = data.get('next_event_id', 1)
        data['next_event_id'] = next_id + 1
        data['events'].append({'id': next_id, 'message': message[:900], 'url': url or ''})
        save_state(data)


def update_issue(number: int, **fields):
    with _lock:
        data = load_state()
        entry = data['issues'].setdefault(str(number), {})
        entry.update(fields, updated_at=utcnow())
        save_state(data)


def github(method, suffix, payload=None):
    if method != 'GET' or payload is not None:
        raise ScopeError('Retired worker permits read-only GitHub requests')
    body = json.dumps(payload).encode() if payload is not None else None
    request = Request(GITHUB_API + suffix, data=body, method=method, headers={
        'Authorization': 'Bearer ' + secret(GH_TOKEN_FILE),
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'smart-garden-automation/1',
        **({'Content-Type': 'application/json'} if body is not None else {}),
    })
    try:
        with urlopen(request, timeout=25) as response:
            return json.loads(response.read())
    except (HTTPError, URLError) as error:
        # HTTP errors may contain credential-bearing payloads: never surface them.
        raise RuntimeError(f'GitHub request failed: {method} {suffix.split("?")[0]} ({getattr(error, "code", "network")})') from None


def command(args, cwd=None, env=None, timeout=60, uid=None):
    def drop():
        os.setgroups([])
        os.setgid(10001)
        os.setuid(10001)
    result = subprocess.run(
        args, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=timeout,
        preexec_fn=drop if uid == 10001 else None, check=False,
    )
    if result.returncode:
        # Avoid leaking tokens, PII or LLM outputs into n8n/Telegram/logs.
        raise RuntimeError(f'Command failed (exit={result.returncode}): {args[0]}')
    return result.stdout.rstrip('\n')


def git(*args, cwd=None, env=None, timeout=90):
    # Never trust .git in Codex-writable worktrees. Coordinator Git operations
    # use Git metadata stored in a root-only directory, not worktree discovery.
    clean_env = dict(os.environ if env is None else env)
    clean_env['GIT_CONFIG_GLOBAL'] = '/dev/null'
    clean_env['GIT_CONFIG_NOSYSTEM'] = '1'
    if cwd is not None:
        worktree = Path(cwd).resolve()
        if worktree.parent == (ROOT / 'jobs').resolve():
            clean_env['GIT_DIR'] = str(METADATA_DIR / f'{worktree.name}.git')
            clean_env['GIT_WORK_TREE'] = str(worktree)
    return command(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'credential.helper=', *args], cwd=cwd, env=clean_env, timeout=timeout)


def approvable_issue(issue: dict, main_sha: str):
    # Issue creator/body/labels are mutable task data, never execution approval.
    raise ScopeError('Autonomous execution retired; Issue metadata cannot authorize it')


def fresh_repository(scope):
    raise ScopeError('Autonomous execution retired; branch creation prohibited')


def run_codex(scope, path):
    # No model subprocess and no credential cache access, even on direct calls.
    raise ScopeError('Autonomous execution retired; Codex credential isolation unresolved')


def changed_files(path):
    # Porcelain -z is delimiter-safe. Reject renames/copies to avoid scope evasion.
    result = git('status', '--porcelain=v1', '-z', '--untracked-files=all', cwd=path)
    tokens = result.split('\x00')
    out = []
    for token in tokens:
        if not token:
            continue
        if len(token) < 4 or token[:2].strip() in ('R', 'C') or 'R' in token[:2] or 'C' in token[:2]:
            raise ScopeError('Rename/copy changes not allowed')
        out.append(token[3:])
    return out


def guard_files(path, paths):
    changed = changed_files(path)
    validate_changed_paths(changed, paths)
    for name in changed:
        p = path / name
        if p.is_symlink() or (p.exists() and not p.is_file()):
            raise ScopeError('Symlink or nonregular file rejected')
        if p.exists() and not p.resolve().is_relative_to(path.resolve()):
            raise ScopeError('Path escapes workspace')
    git('diff', '--check', cwd=path)
    return changed


def commit_and_open_pr(scope, path, branch):
    raise ScopeError('Autonomous execution retired; publication prohibited')


def check_ci(pr_state):
    number, head = pr_state['pr'], pr_state['head']
    checks = github('GET', f'/commits/{head}/check-runs?per_page=100')['check_runs']
    latest = {x['name']: x for x in checks}
    if not EXPECTED_CI.issubset(latest):
        return 'pending', 'Waiting for required CI checks'
    ours = [latest[n] for n in EXPECTED_CI]
    if any(x['status'] != 'completed' for x in ours):
        return 'pending', 'CI still running'
    if all(x['conclusion'] == 'success' for x in ours):
        return 'passed', 'All 8 baseline required CI checks passed; human review required'
    return 'failed', 'CI failed; automatic changes stopped until reviewed'


def workflow_step():
    global _busy
    try:
        data = load_state()
        # Monitor previously opened automation PRs before considering new work.
        for key, item in list(data['issues'].items()):
            if item.get('status') != 'pr_pending':
                continue
            try:
                status, note = check_ci(item)
                if status != 'pending':
                    update_issue(int(key), status='ci_' + status)
                    publish(f'Issue #{key}: {note}. PR #{item["pr"]}', item['url'])
            except Exception:
                # Transient checks API failures should not corrupt PR state.
                pass
        # Historical START_ENABLED is deliberately ignored. This build is read-only.
        return
    except Exception:
        publish('Automation stopped: GitHub or infrastructure error; inspect worker environment.')
    finally:
        with _lock:
            _busy = False


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        return  # suppress possible request data in HTTP logs

    def response(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authenticated(self):
        supplied = self.headers.get('X-Worker-Key', '')
        return len(supplied) >= 32 and hmac.compare_digest(supplied, secret(WORKER_KEY_FILE))

    def do_GET(self):
        if self.path == '/healthz':
            return self.response(200, {'ok': True, 'service': 'smart-garden-worker'})
        return self.response(404, {'error': 'not_found'})

    def do_POST(self):
        global _busy
        if not self.authenticated():
            return self.response(403, {'error': 'forbidden'})
        length = int(self.headers.get('Content-Length', '0'))
        if length > 2048 or length < 0:
            return self.response(413, {'error': 'payload_rejected'})
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw or b'{}')
            if not isinstance(payload, dict):
                raise ValueError('not object')
        except (ValueError, UnicodeError):
            return self.response(400, {'error': 'invalid_json'})
        if self.path == '/tick':
            with _lock:
                if not _busy:
                    _busy = True
                    threading.Thread(target=workflow_step, daemon=True).start()
                events = load_state()['events'][:25]
                return self.response(200, {'busy': _busy, 'enabled': False, 'events': events})
        if self.path == '/ack':
            event_id = payload.get('id')
            if not isinstance(event_id, int) or event_id < 1:
                return self.response(400, {'error': 'invalid_event'})
            with _lock:
                data = load_state()
                data['events'] = [event for event in data['events'] if event['id'] != event_id]
                save_state(data)
            return self.response(200, {'acknowledged': True})
        return self.response(404, {'error': 'not_found'})


if __name__ == '__main__':
    if os.geteuid() != 0:
        raise SystemExit('Worker coordinator must run as root to drop Codex privileges')
    for s in [GH_TOKEN_FILE, WORKER_KEY_FILE]:
        if not s.exists() or len(secret(s)) < 32:
            raise SystemExit('Required root-only secret unavailable: ' + s.name)
        if (s.stat().st_mode & 0o077) != 0:
            raise SystemExit('Refusing world/group-readable credential: ' + s.name)
    ROOT.mkdir(parents=True, exist_ok=True)
    with _lock:
        data = load_state()
        for item in data['issues'].values():
            if item.get('status') == 'running':
                item['status'] = 'blocked'
                item['reason'] = 'Worker restarted during task; manual inspection required'
        save_state(data)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
