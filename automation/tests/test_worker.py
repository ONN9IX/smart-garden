"""Synthetic local Git-only checks; never uses network or credentials."""
import sys
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'worker'))
import worker
from policy import ScopeError

class WorkerTests(unittest.TestCase):
    def git(self, root, *args):
        return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True)

    def test_git_porcelain_paths_preserve_xy_whitespace(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.git(root, 'init', '-q')
            self.git(root, 'config', 'user.name', 'Synthetic Test')
            self.git(root, 'config', 'user.email', 'test@example.invalid')
            path = root / 'frontend/test.txt'
            path.parent.mkdir()
            path.write_text('old\n')
            self.git(root, 'add', '.')
            self.git(root, 'commit', '-qm', 'initial')
            path.write_text('new\n')
            self.assertEqual(worker.changed_files(root), ['frontend/test.txt'])
            self.assertEqual(worker.guard_files(root, ('frontend/test.txt',)), ['frontend/test.txt'])
            with self.assertRaises(ScopeError):
                worker.guard_files(root, ('backend/other.txt',))

    def test_ci_requires_all_checks(self):
        good = [{'name': n, 'status': 'completed', 'conclusion': 'success'}
                for n in worker.EXPECTED_CI]
        with patch.object(worker, 'github', return_value={'check_runs': good}):
            self.assertEqual(worker.check_ci({'pr': 1, 'head': 'a' * 40})[0], 'passed')
        with patch.object(worker, 'github', return_value={'check_runs': good[:-1]}):
            self.assertEqual(worker.check_ci({'pr': 1, 'head': 'a' * 40})[0], 'pending')
        good[0]['conclusion'] = 'failure'
        with patch.object(worker, 'github', return_value={'check_runs': good}):
            self.assertEqual(worker.check_ci({'pr': 1, 'head': 'a' * 40})[0], 'failed')

if __name__ == '__main__': unittest.main()
