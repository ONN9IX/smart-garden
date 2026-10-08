"""Offline install tests use disposable fake automation directories only."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

AUTOMATION = Path(__file__).resolve().parents[1]


class SetupTests(unittest.TestCase):
    def test_local_keys_generated_without_enabling_worker(self):
        if not shutil.which('openssl'):
            self.skipTest('openssl is not installed')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / 'deploy').mkdir()
            shutil.copy2(AUTOMATION / 'deploy/init-secrets.sh', path / 'deploy/init-secrets.sh')
            shutil.copy2(AUTOMATION / '.env.example', path / '.env.example')
            cmd = ['bash', 'deploy/init-secrets.sh']
            subprocess.run(cmd, cwd=path, capture_output=True, text=True, check=True)
            env = (path / '.env').read_text()
            self.assertIn('START_ENABLED=false', env)
            self.assertNotIn('REPLACE_WITH_RANDOM', env)
            self.assertIn('CODEX_VERSION=0.161.0', env)
            self.assertTrue((path / 'secrets/worker_key').exists())
            self.assertFalse((path / 'secrets/github_token').exists())
            self.assertEqual((path / 'secrets/worker_key').stat().st_mode & 0o077, 0)
            self.assertNotEqual(subprocess.run(cmd, cwd=path, capture_output=True).returncode, 0)


if __name__ == '__main__':
    unittest.main()
