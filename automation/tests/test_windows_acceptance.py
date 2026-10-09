"""Exercise the real offline entry point; supplied text cannot accept isolation."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'windows' / 'acceptance.ps1'
LAUNCHER = SCRIPT.with_name('controller.py')


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.shell = shutil.which('pwsh')
        if not self.shell:
            self.skipTest('PowerShell 7 unavailable; runtime NOT TESTED')

    def run_report(self, args=(), env=None, cwd=None):
        return subprocess.run([sys.executable, str(LAUNCHER), '--report', *args],
                              capture_output=True, text=True, timeout=20,
                              env=env, cwd=cwd)

    def test_identical_reports_remain_no_go_without_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before = set(root.iterdir())
            first = self.run_report(cwd=tmp)
            second = self.run_report(cwd=tmp)
            self.assertEqual(first.returncode, 1, first.stderr)
            self.assertEqual(second.returncode, 1, second.stderr)
            self.assertEqual(first.stdout, second.stdout)
            self.assertEqual(set(root.iterdir()), before)
        report = json.loads(first.stdout)
        self.assertEqual(report['decision'], 'NO_GO')
        self.assertEqual(report['evidence_class'], 'STATIC')
        self.assertEqual(report['worker_token'], 'NOT_TESTED')
        self.assertEqual(report['execution'], 'DISABLED')
        self.assertEqual(report['publisher'], 'ABSENT')

    def test_environment_and_workspace_evidence_cannot_authorize(self):
        env = dict(os.environ, START_ENABLED='true', OWNER_MERGE_VERIFIED='true',
                   ISOLATION_ACCEPTED='true', APPROVAL='synthetic-approval',
                   POWERSHELL_TELEMETRY_OPTOUT='0')
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / 'acceptance.json'
            original = '{"decision":"GO","signed":true,"worker":"accepted"}'
            evidence.write_text(original)
            result = self.run_report(env=env, cwd=tmp)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(json.loads(result.stdout)['decision'], 'NO_GO')
            self.assertEqual(evidence.read_text(), original)

    def test_unknown_arguments_and_modes_cannot_request_activation(self):
        for args in (['-Mode', 'Install'], ['-Mode', 'Activate'],
                     ['-Evidence', 'synthetic.json'], ['-Accepted', 'true']):
            with self.subTest(args=args):
                result = self.run_report(args)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('"decision":"GO"', result.stdout)

    def test_launcher_opts_out_before_start_and_drops_ambient_credentials(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('offline_reporter', LAUNCHER)
        launcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(launcher)
        with patch.dict(os.environ, {'POWERSHELL_TELEMETRY_OPTOUT': '0',
                                     'GH_TOKEN': 'synthetic-not-a-secret'}), \
                patch.object(launcher.shutil, 'which', return_value=self.shell), \
                patch.object(launcher.subprocess, 'run') as run:
            run.return_value.returncode = 0
            self.assertEqual(launcher.report(), 1)
        child = run.call_args.kwargs
        self.assertEqual(child['env']['POWERSHELL_TELEMETRY_OPTOUT'], '1')
        self.assertEqual(child['env']['POWERSHELL_UPDATECHECK'], 'Off')
        self.assertNotIn('GH_TOKEN', child['env'])
        self.assertEqual(child['stdin'], subprocess.DEVNULL)
        self.assertEqual(child['timeout'], 20)


if __name__ == '__main__':
    unittest.main()
