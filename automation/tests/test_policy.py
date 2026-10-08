"""Synthetic security regression tests for scoped autonomous delivery."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'worker'))
from policy import ScopeError, parse_issue, validate_changed_paths, validate_path

SHA = 'a' * 40

def issue(paths='- frontend/src/app/demo/page.tsx\n', **kwargs):
    value = {
        'number': 200,
        'state': 'open',
        'user': {'login': 'ONN9IX'},
        'labels': [{'name': 'ai:ready'}],
        'title': 'Demo',
        'body': f'AUTOMATION-AUTHORIZED: YES\nPARALLEL-SAFE: NO\nBASE-SHA: {SHA}\nWRITE-SET:\n{paths}',
    }
    value.update(kwargs)
    return value

class PolicyTests(unittest.TestCase):
    def test_valid_issue(self):
        scope = parse_issue(issue(), SHA)
        self.assertEqual(scope.paths, ('frontend/src/app/demo/page.tsx',))

    def test_rejects_wrong_sha(self):
        with self.assertRaises(ScopeError): parse_issue(issue(), 'b' * 40)

    def test_rejects_other_authors(self):
        with self.assertRaises(ScopeError): parse_issue(issue(user={'login': 'attacker'}), SHA)

    def test_rejects_unlabeled_and_incomplete(self):
        with self.assertRaises(ScopeError): parse_issue(issue(labels=[]), SHA)
        with self.assertRaises(ScopeError): parse_issue(issue(body='WRITE-SET:\n- frontend/a.tsx'), SHA)

    def test_denies_shared_and_sensitive_paths(self):
        for path in ['../AGENTS.md', 'AGENTS.md', '.github/workflows/ci.yml',
                     'backend/alembic/versions/x.py', 'backend/app/models/x.py',
                     'backend/.env', 'frontend/../README.md', 'automation/worker.py',
                     'frontend//bad.tsx', 'frontend\\bad.tsx', 'frontend/x.pem',
                     'docs/CURRENT_STATE.md', '/etc/passwd']:
            with self.subTest(path=path), self.assertRaises(ScopeError):
                validate_path(path)

    def test_rejects_diff_outside_scope(self):
        with self.assertRaises(ScopeError):
            validate_changed_paths(['frontend/src/app/other.tsx'], ('frontend/src/app/demo/page.tsx',))

    def test_rejects_repeated_scope(self):
        with self.assertRaises(ScopeError):
            parse_issue(issue(paths='- frontend/foo.tsx\n- frontend/foo.tsx\n'), SHA)

    def test_rejects_mutated_body(self):
        with self.assertRaises(ScopeError):
            parse_issue(issue(body=f'AUTOMATION-AUTHORIZED: YES\nPARALLEL-SAFE: YES\nBASE-SHA: {SHA}\nWRITE-SET:\n- frontend/foo.tsx'), SHA)

if __name__ == '__main__': unittest.main()
