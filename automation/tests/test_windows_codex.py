"""Static fail-closed checks for the optional, read-only Windows Codex preflight."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WindowsCodexReadinessTests(unittest.TestCase):
    def test_preflight_only_uses_read_commands(self):
        text = (ROOT / 'windows/check-codex.ps1').read_text(encoding='utf-8')
        expected = ('codex --version', 'codex login status',
                    'codex cloud list --json --limit 1', 'Invoke-RestMethod',
                    'api.github.com/repos/ONN9IX/smart-garden/branches/main')
        for phrase in expected:
            self.assertIn(phrase, text)
        for forbidden in ('& codex cloud exec', '& codex exec', 'git push', 'git commit',
                          'Start-Process -Verb RunAs', 'Set-ExecutionPolicy',
                          'OPENAI_API_KEY', 'GH_TOKEN', 'WriteAllText', 'Set-Content'):
            self.assertNotIn(forbidden, text)

    def test_cmd_launcher_has_no_powershell_bypass(self):
        text = (ROOT / 'windows/check-codex.cmd').read_text(encoding='utf-8')
        self.assertIn('powershell.exe -NoProfile -File', text)
        self.assertNotIn('ExecutionPolicy Bypass', text)
        self.assertNotIn('runas', text.lower())

    def test_cloud_docs_keep_executor_off(self):
        text = (ROOT / 'CODEX-CLOUD.md').read_text(encoding='utf-8')
        for phrase in ('не запускают', 'не вызывает', 'пока не реализован',
                       'Codex Cloud', 'WRITE-SET', 'GitHub Actions'):
            self.assertIn(phrase, text)


if __name__ == '__main__':
    unittest.main()
