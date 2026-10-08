"""Read-only observer policy regression using synthetic GitHub REST payloads."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import github_observer as ob

MAIN = 'a' * 40
HEAD = 'b' * 40


class StubReader:
    def __init__(self, *, prs=(), issues=(), checks=(), main=MAIN):
        self.prs, self.issues, self.checks, self.main = prs, issues, checks, main
        self.calls = []

    def get(self, path):
        self.calls.append(path)
        if path == '/branches/main':
            return {'commit': {'sha': self.main}}
        if path.startswith('/pulls?'):
            return list(self.prs)
        if path.startswith('/issues?'):
            return list(self.issues)
        if path.startswith('/commits/'):
            return {'check_runs': list(self.checks), 'total_count': len(self.checks)}
        raise AssertionError(path)


def make_issue(number=7, owner='ONN9IX', sha=MAIN):
    return {'number': number, 'state': 'open', 'user': {'login': owner},
            'labels': [{'name': 'ai:ready'}], 'title': 'Synthetic UI text only',
            'body': f'AUTOMATION-AUTHORIZED: YES\nPARALLEL-SAFE: NO\nBASE-SHA: {sha}\nWRITE-SET:\n- frontend/src/app/example/page.tsx\n'}


def checks(conclusion='success'):
    return [{'name': name, 'status': 'completed', 'conclusion': conclusion}
            for name in sorted(ob.EXPECTED_CI)]


class ObserverTests(unittest.TestCase):
    def test_no_issue_no_pr_stays_off(self):
        result = ob.inspect(StubReader())
        self.assertEqual(result['execution'], 'DISABLED')
        self.assertEqual(result['queue_gate'], 'NO_EXECUTOR')
        self.assertFalse(result['pull_requests'])

    def test_valid_issue_cannot_launch(self):
        result = ob.inspect(StubReader(issues=[make_issue()]))
        self.assertEqual(result['queue'][0]['status'], 'VALID_SCOPE_EXECUTOR_DISABLED')
        self.assertIn('DISABLED', ob.to_markdown(result))

    def test_open_pr_blocks_scope(self):
        result = ob.inspect(StubReader(prs=[{'number': 205, 'head': {'sha': HEAD}}],
                                       issues=[make_issue()], checks=checks()))
        self.assertEqual(result['queue_gate'], 'BLOCKED_OPEN_PR')
        self.assertEqual(result['queue'][0]['status'], 'VALID_SCOPE_BLOCKED')
        self.assertEqual(result['pull_requests'][0]['ci']['status'], 'passed')

    def test_stale_issue_marked_invalid_and_minimized(self):
        issue = make_issue(22, sha='c' * 40)
        issue['title'] = 'PRIVATE DATA MUST NEVER APPEAR'
        result = ob.inspect(StubReader(issues=[issue]))
        self.assertEqual(result['queue'][0]['status'], 'INVALID_OR_STALE_SCOPE')
        self.assertNotIn('PRIVATE DATA', ob.to_markdown(result))

    def test_foreign_author_not_allowed(self):
        result = ob.inspect(StubReader(issues=[make_issue(owner='outsider')]))
        self.assertEqual(result['queue'][0]['status'], 'INVALID_OR_STALE_SCOPE')

    def test_ci_failed_over_pending(self):
        values = checks()
        values[0]['conclusion'] = 'failure'
        values[1]['status'] = 'in_progress'
        self.assertEqual(ob.ci_status(values)['status'], 'failed')

    def test_missing_required_ci_is_not_pass(self):
        res = ob.ci_status(checks()[:-1])
        self.assertEqual(res['status'], 'pending')
        self.assertEqual(len(res['missing']), 1)

    def test_ci_all_succeeded(self):
        res = ob.ci_status(checks())
        self.assertEqual((res['status'], res['passed'], res['required']), ('passed', 8, 8))

    def test_ci_unexpected_format_fails_closed(self):
        with self.assertRaises(ob.ReadError):
            ob.ci_status({'x': 1})

    def test_pagination_fail_closed_at_full_page_limit(self):
        class FullReader:
            def get(self, path):
                return [{} for _ in range(100)]
        with self.assertRaises(ob.ReadError):
            ob.paged(FullReader(), '/issues?state=open', max_pages=2)

    def test_unsafe_pr_head_fails_closed(self):
        with self.assertRaises(ob.ReadError):
            ob.inspect(StubReader(prs=[{'number': 205, 'head': {'sha': 'bad'}}]))

    def test_git_read_only_workflow_lacks_write_permissions(self):
        wf = (ROOT.parent / '.github/workflows/automation-observer.yml').read_text()
        self.assertIn('schedule:', wf)
        self.assertIn('workflow_dispatch:', wf)
        self.assertIn("persist-credentials: false", wf)
        self.assertIn("AUTONOMOUS_EXECUTION: 'false'", wf)
        for forbidden in ('write:', 'pull_request_target:', 'OPENAI_API_KEY', 'codex exec', 'secrets.TELEGRAM'):
            self.assertNotIn(forbidden, wf)

    def test_paged_get_reads_only_bounded_paths(self):
        reader = StubReader()
        self.assertEqual(ob.paged(reader, '/pulls?state=open'), [])
        self.assertEqual(len(reader.calls), 1)


if __name__ == '__main__':
    unittest.main()
