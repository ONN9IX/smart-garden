"""A1 negative tests: real reporter with synthetic inputs, never Windows acceptance."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "windows/transport-preflight.ps1"
DIGEST = "a" * 64
CANDIDATE = r"C:\Synthetic\codex.exe"
MARKER = "synthetic-secret-never-emit"


class PreflightStaticTests(unittest.TestCase):
    def test_only_permitted_operations_and_no_auth_or_activation_inputs(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in ("Get-Content", "ReadAllText", "ReadAllBytes", "Get-ChildItem",
                          "Get-Command", "Get-Credential", "CredRead", "CredEnumerate",
                          "Invoke-RestMethod", "Invoke-WebRequest", "Start-Process",
                          "Invoke-Expression", "WriteAll", "Set-Content", "Set-Acl",
                          "New-LocalUser", "Set-ExecutionPolicy", "Register-ScheduledTask",
                          "Process.Start", "FileAccess.Write", "auth.json", "$env:"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)
        self.assertIn("decision = 'NO_GO'", source)
        self.assertIn("execution = 'DISABLED'", source)

    def test_native_read_uses_locked_handles_and_rejects_aliases(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for required in ("GetFileInformationByHandle", "GetFinalPathNameByHandleW",
                         "i.Links != 1", "i.Attributes & 1024", "GetDriveTypeW(root) != 3",
                         "directory ? 3u : 1u", "new FileStream(h, FileAccess.Read)",
                         "stream.Length > 268435456", "held[n].Dispose()"):
            self.assertIn(required, source)

    def test_docs_do_not_upgrade_reporter_to_host_acceptance(self):
        root = SCRIPT.parent
        for name in ("HOST_PLAN.md", "SECURITY.md"):
            source = (root / name).read_text(encoding="utf-8")
            for required in ("#211", "STATIC", "SYNTHETIC", "LIVE-WITNESSED",
                             "NOT TESTED", "NO-GO", "c1382380de69521303b416720a52f42d51af6248"):
                self.assertIn(required, source)


class PreflightRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shell = shutil.which("pwsh")
        if not cls.shell:
            raise unittest.SkipTest("PowerShell 7 unavailable: runtime NOT TESTED")

    def run_script(self, args=(), script=SCRIPT, cwd=None, extras=None):
        # Override opt-in BEFORE startup, close stdin, no profile, no credential env.
        env = {k: v for k, v in os.environ.items()
               if k.upper() in {"SYSTEMROOT", "WINDIR", "HOME", "USERPROFILE", "PATH",
                                "TEMP", "TMP", "LANG", "LC_ALL"}}
        env.update(extras or {})
        env.update(POWERSHELL_TELEMETRY_OPTOUT="1", POWERSHELL_UPDATECHECK="Off")
        with tempfile.TemporaryDirectory(prefix="a1-runtime-") as runtime:
            # Linux PowerShell startup caches must stay inside disposable fixtures.
            env.update(XDG_CACHE_HOME=runtime, XDG_CONFIG_HOME=runtime, XDG_DATA_HOME=runtime)
            return subprocess.run([self.shell, "-NoLogo", "-NoProfile", "-NonInteractive",
                                   "-File", str(script), *args], env=env, cwd=cwd,
                                  stdin=subprocess.DEVNULL, capture_output=True,
                                  text=True, timeout=20)

    def assert_no_go(self, result, exit_code=1):
        self.assertEqual(result.returncode, exit_code, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertLess(len(result.stdout), 1600)
        self.assertNotIn(MARKER, result.stdout)
        self.assertNotIn(CANDIDATE, result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["decision"], "NO_GO")
        self.assertEqual(report["execution"], "DISABLED")
        self.assertEqual(report["evidence_class"], "STATIC")
        for name in ("sandbox_backend", "worker_token", "credential_read_denial",
                     "protected_write_denial", "process_environment_ipc_network"):
            self.assertEqual(report[name], "NOT_TESTED")
        return report

    def synthetic_runner(self, folder, overrides="", invocation="@()"):
        # Extract actual functions through the PS AST; fake host adapters exist
        # only in this disposable test runner, never in the production interface.
        path = Path(folder) / "synthetic-runner.ps1"
        escaped = str(SCRIPT).replace("'", "''")
        path.write_text("$ErrorActionPreference='Stop'\nSet-StrictMode -Version Latest\n"
                        "$tokens=$null; $errors=$null\n"
                        f"$ast=[System.Management.Automation.Language.Parser]::ParseFile('{escaped}', [ref]$tokens, [ref]$errors)\n"
                        "if ($errors.Count) { throw 'parse failure' }\n"
                        "$functions=$ast.FindAll({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst]}, $false)\n"
                        "foreach ($function in $functions) { . ([scriptblock]::Create($function.Extent.Text)) }\n"
                        + overrides + "\n"
                        f"$result=Invoke-TransportPreflight {invocation}\n"
                        "$result.Report | ConvertTo-Json -Compress\nexit $result.ExitCode\n",
                        encoding="utf-8")
        return path

    def test_repeated_reports_and_forged_evidence_leave_workspace_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "acceptance.json"
            evidence.write_text('{"decision":"GO","signed":true,"worker":"accepted"}')
            fake = Path(tmp) / "codex.exe"
            fake.write_text(MARKER)
            before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(tmp).iterdir()}
            first = self.run_script(cwd=tmp, extras={"ISOLATION_ACCEPTED": "true", "START_ENABLED": "true"})
            second = self.run_script(cwd=tmp)
            self.assert_no_go(first)
            self.assertEqual(first.stdout, second.stdout)
            self.assert_no_go(second)
            after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(tmp).iterdir()}
            self.assertEqual(before, after)

    def test_unknown_duplicate_unbounded_or_activation_arguments_are_redacted(self):
        for args in (["-Accepted", MARKER], ["-Mode", "Activate"], ["-Mode", "Install"],
                     ["-Evidence", MARKER], ["-Mode", "Report", "-Mode", "Report"],
                     ["-Mode"], ["-Mode", "Report", MARKER], ["-CodexBinaryPath", "x" * 241],
                     ["-" + MARKER, "true"], ["-Mode", "report"]):
            with self.subTest(args=args):
                report = self.assert_no_go(self.run_script(args), 2)
                self.assertEqual(report["reason"], "INVALID_ARGUMENT")

    def test_invalid_paths_pins_and_wrappers_rejected_before_metadata(self):
        paths = ["codex.exe", r"\\server\codex.exe", r"\\?\C:\codex.exe",
                 r"C:\NUL.exe", r"C:\a\..\codex.exe", r"C:\a.\codex.exe",
                 r"C:\a \codex.exe", r"C:\a\codex.exe:stream", r"C:\a\*.exe",
                 r"C:\PROGRA~1\codex.exe", r"C:\a\codex.cmd", r"C:\a\codex.ps1",
                 r"C:\.codex\codex.exe", "C:\\a\\" + MARKER + "\n.exe", CANDIDATE + "\n"]
        for path in paths:
            with self.subTest(path=path):
                self.assert_no_go(self.run_script(["-CodexBinaryPath", path, "-ExpectedSha256", DIGEST,
                                                  "-ExpectedVersion", "0.162.0"]), 2)
        for digest, version in [(MARKER, "0.162.0"), (DIGEST, MARKER), (DIGEST, "0.162.0+secret"),
                                (DIGEST + "\n", "0.162.0"), (DIGEST, "0.162.0\n")]:
            self.assert_no_go(self.run_script(["-CodexBinaryPath", CANDIDATE, "-ExpectedSha256", digest,
                                              "-ExpectedVersion", version]), 2)

    def test_fake_windows_pin_matches_and_mismatches_never_accept_transport(self):
        host = "function Get-TransportHostMetadata { @{Windows=$true; OsVersion='10.0.26100.9278'; Architecture='X64'} }\n"
        invocation = f"@('-CodexBinaryPath','{CANDIDATE}','-ExpectedSha256','{DIGEST}','-ExpectedVersion','0.162.0')"
        cases = [(DIGEST, "0.162.0", "MATCH", "MATCH", "METADATA_ONLY"),
                 ("b" * 64, "0.162.0", "MISMATCH", "MATCH", "PIN_MISMATCH"),
                 (DIGEST, "0.161.0", "MATCH", "MISMATCH", "PIN_MISMATCH"),
                 (DIGEST, "", "MATCH", "NOT_TESTED", "VERSION_UNAVAILABLE"),
                 (DIGEST, MARKER, "MATCH", "NOT_TESTED", "VERSION_UNAVAILABLE")]
        with tempfile.TemporaryDirectory() as tmp:
            for digest, version, binary_pin, version_pin, reason in cases:
                with self.subTest(version=version, digest=digest):
                    adapter = f"function Get-CandidateMetadata {{ @{{Hash='{digest}'; Version='{version}'}} }}"
                    runner = self.synthetic_runner(tmp, host + adapter, invocation)
                    report = self.assert_no_go(self.run_script(script=runner))
                    self.assertEqual((report["binary_pin"], report["version_pin"], report["reason"]),
                                     (binary_pin, version_pin, reason))

    def test_denied_missing_or_unsafe_metadata_never_leaks_raw_exception(self):
        invocation = f"@('-CodexBinaryPath','{CANDIDATE}','-ExpectedSha256','{DIGEST}','-ExpectedVersion','0.162.0')"
        host = "function Get-TransportHostMetadata { @{Windows=$true; OsVersion='10.0.26100.9278'; Architecture='X64'} }\n"
        with tempfile.TemporaryDirectory() as tmp:
            for adapter in (f"function Get-CandidateMetadata {{ throw '{MARKER}' }}",
                            f"function Get-CandidateMetadata {{ @{{Hash='{MARKER}'; Version='0.162.0'}} }}",
                            f"function Get-TransportHostMetadata {{ @{{Windows=$true; OsVersion='{MARKER}'; Architecture='X64'}} }}"):
                runner = self.synthetic_runner(tmp, host + adapter, invocation)
                report = self.assert_no_go(self.run_script(script=runner))
                self.assertEqual(report["reason"], "METADATA_UNAVAILABLE")
                self.assertEqual(report["binary_sha256"], "")

    def test_native_helper_compiles_without_running_an_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Linux: native invocation fails safely after real in-memory compilation.
            # Windows: deliberately missing synthetic path; never actual Codex/auth.
            runner = self.synthetic_runner(tmp,
                "function Get-TransportHostMetadata { @{Windows=$true; OsVersion='10.0.26100.9278'; Architecture='X64'} }",
                f"@('-CodexBinaryPath','Z:\\A1MissingSynthetic\\codex.exe','-ExpectedSha256','{DIGEST}','-ExpectedVersion','0.162.0')")
            report = self.assert_no_go(self.run_script(script=runner))
            self.assertEqual(report["reason"], "METADATA_UNAVAILABLE")
            # Check type exists to distinguish compilation failure from native denial.
            text = runner.read_text().replace("$result.Report |", "if (-not ('A1BinaryMetadata' -as [type])) { exit 99 }; $result.Report |")
            runner.write_text(text)
            self.assert_no_go(self.run_script(script=runner))

    @unittest.skipUnless(os.name == "nt", "native Windows handle checks NOT TESTED in Cloud/Linux")
    def test_windows_synthetic_binary_hardlink_and_reparse_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "codex.exe"
            candidate.write_bytes(b"MZ" + MARKER.encode())
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
            args = ["-CodexBinaryPath", str(candidate), "-ExpectedSha256", digest, "-ExpectedVersion", "0.162.0"]
            report = self.assert_no_go(self.run_script(args))
            self.assertEqual(report["binary_pin"], "MATCH")
            self.assertEqual(report["version_pin"], "NOT_TESTED")
            alias = Path(tmp) / "alias.exe"
            os.link(candidate, alias)
            self.assertEqual(self.assert_no_go(self.run_script(args))["reason"], "METADATA_UNAVAILABLE")
            alias.unlink()
            target = Path(tmp) / "target"
            target.mkdir()
            junction = Path(tmp) / "junction"
            subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(target)],
                           check=True, capture_output=True, timeout=10)
            try:
                (target / "codex.exe").write_bytes(candidate.read_bytes())
                args[1] = str(junction / "codex.exe")
                self.assertEqual(self.assert_no_go(self.run_script(args))["reason"], "METADATA_UNAVAILABLE")
            finally:
                junction.rmdir()


if __name__ == "__main__":
    unittest.main()
