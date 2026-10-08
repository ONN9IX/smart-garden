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

    def test_coordinator_ignores_untrusted_worktree_git_pointer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            origin = root / 'origin'
            origin.mkdir()
            self.git(origin, 'init', '-q')
            self.git(origin, 'config', 'user.name', 'Synthetic Test')
            self.git(origin, 'config', 'user.email', 'test@example.invalid')
            (origin / 'README').write_text('clean\n')
            self.git(origin, 'add', '.')
            self.git(origin, 'commit', '-qm', 'initial')
            worktree = root / 'jobs' / 'issue-201'
            worktree.parent.mkdir()
            private = root / 'private-git'
            private.mkdir(mode=0o700)
            metadata = private / 'issue-201.git'
            self.git(root, 'clone', '-q', f'--separate-git-dir={metadata}',
                     str(origin), str(worktree))
            with patch.object(worker, 'ROOT', root), patch.object(worker, 'METADATA_DIR', private):
                expected = worker.git('rev-parse', 'HEAD', cwd=worktree)
                self.assertEqual(expected, self.git(worktree, 'rev-parse', 'HEAD').stdout.decode().strip())
                # Simulate an agent replacing the visible .git pointer. The root
                # coordinator must still use its private immutable metadata.
                (worktree / '.git').unlink()
                (worktree / '.git').mkdir()
                (worktree / '.git' / 'config').write_text('[core]\n\tbare = true\n')
                self.assertEqual(worker.git('rev-parse', 'HEAD', cwd=worktree), expected)
                (worktree / 'README').write_text('changed\n')
                self.assertEqual(worker.changed_files(worktree), ['README'])
                if hasattr(__import__('os'), 'geteuid') and __import__('os').geteuid() == 0:
                    import os
                    for entry in worktree.rglob('*'):
                        os.chown(entry, 10001, 10001)
                    os.chown(worktree, 10001, 10001)
                    self.assertEqual(worker.git('rev-parse', 'HEAD', cwd=worktree), expected)

if __name__ == '__main__': unittest.main()
