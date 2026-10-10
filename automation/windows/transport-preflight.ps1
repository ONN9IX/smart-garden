# A1 / #211: offline metadata reporter, never an isolation certificate.
# Launch with startup telemetry opt-out and update checks off (HOST_PLAN.md).
# No param binder: unknown arguments must not echo caller data in raw errors.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function New-TransportReport {
    [ordered]@{
        schema = 1; issue = 211; decision = 'NO_GO'; evidence_class = 'STATIC'
        execution = 'DISABLED'; reason = 'METADATA_ONLY'
        platform = 'NOT_TESTED'; os_version = ''; architecture = ''
        powershell_version = $PSVersionTable.PSVersion.ToString()
        binary_pin = 'NOT_TESTED'; binary_sha256 = ''; binary_version = ''
        version_pin = 'NOT_TESTED'; sandbox_backend = 'NOT_TESTED'
        credential_transport = 'NOT_ACCEPTED'; worker_token = 'NOT_TESTED'
        credential_read_denial = 'NOT_TESTED'; protected_write_denial = 'NOT_TESTED'
        process_environment_ipc_network = 'NOT_TESTED'
    }
}

function Read-TransportArguments([object[]]$Items) {
    $result = @{ Mode = 'Report'; CodexBinaryPath = ''; ExpectedSha256 = ''; ExpectedVersion = '' }
    $seen = @{}
    if ($Items.Count -gt 8 -or $Items.Count % 2 -ne 0) { throw 'INVALID_ARGUMENT' }
    for ($i = 0; $i -lt $Items.Count; $i += 2) {
        $name = [string]$Items[$i]
        if ($name -cnotmatch '^-(Mode|CodexBinaryPath|ExpectedSha256|ExpectedVersion)\z') { throw 'INVALID_ARGUMENT' }
        $key = $name.Substring(1)
        if ($seen.ContainsKey($key)) { throw 'INVALID_ARGUMENT' }
        $seen[$key] = $true
        $value = [string]$Items[$i + 1]
        if ($value.Length -gt 240 -or $value.Length -eq 0) { throw 'INVALID_ARGUMENT' }
        $result[$key] = $value
    }
    if ($result.Mode -cne 'Report') { throw 'INVALID_ARGUMENT' }
    $supplied = @('CodexBinaryPath', 'ExpectedSha256', 'ExpectedVersion' | Where-Object { $seen.ContainsKey($_) })
    if ($supplied.Count -ne 0 -and $supplied.Count -ne 3) { throw 'INVALID_ARGUMENT' }
    if ($supplied.Count -eq 3) {
        if ($result.ExpectedSha256 -cnotmatch '^[0-9a-fA-F]{64}\z' -or
            $result.ExpectedVersion -cnotmatch '^[0-9]{1,5}(\.[0-9]{1,5}){1,3}\z' -or
            -not (Test-CandidatePath $result.CodexBinaryPath)) { throw 'INVALID_ARGUMENT' }
    }
    return $result
}

function Test-CandidatePath([string]$Path) {
    # Local drive only: no providers, UNC/devices, ADS, globs, 8.3 aliases or wrappers.
    if ($Path -cnotmatch '^[A-Za-z]:\\[A-Za-z0-9 _.-]+(\\[A-Za-z0-9 _.-]+)*\.exe\z') { return $false }
    foreach ($part in $Path.Substring(3).Split('\')) {
        if ($part -match '^[.]|[ .]$|^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])([.]|$)') { return $false }
    }
    return $true
}

function Get-TransportHostMetadata {
    @{
        Windows = [Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT
        OsVersion = [Environment]::OSVersion.Version.ToString()
        Architecture = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
    }
}

function Get-CandidateMetadata([string]$Path) {
    # PowerShell 7 Add-Type compiles this fixed source in memory. No Codex invocation.
    # Each directory handle denies deletion; the file handle denies writes/deletion.
    # Native handle checks precede all content reads; the only content hashed is
    # the explicitly selected executable. Never supply a secret/cache path.
    if (-not ('A1BinaryMetadata' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Text;
using System.Diagnostics;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using Microsoft.Win32.SafeHandles;
public sealed class A1BinaryMetadata {
    [StructLayout(LayoutKind.Sequential)] struct Info {
        public uint Attributes; public System.Runtime.InteropServices.ComTypes.FILETIME Creation, Access, Write;
        public uint Volume, SizeHigh, SizeLow, Links, IndexHigh, IndexLow;
    }
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern SafeFileHandle CreateFileW(string path, uint access, uint share, IntPtr security, uint disposition, uint flags, IntPtr template);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool GetFileInformationByHandle(SafeFileHandle handle, out Info info);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern uint GetFinalPathNameByHandleW(SafeFileHandle handle, StringBuilder path, uint size, uint flags);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] static extern uint GetDriveTypeW(string root);
    public string Hash; public string Version;
    static SafeFileHandle Open(string path, bool directory) {
        var h = CreateFileW(path, directory ? 0u : 0x80000000u, directory ? 3u : 1u, IntPtr.Zero, 3, 0x02200000, IntPtr.Zero);
        try {
            Info i;
            if (h.IsInvalid || !GetFileInformationByHandle(h, out i) || (i.Attributes & 1024) != 0 ||
                ((i.Attributes & 16) != 0) != directory || (!directory && i.Links != 1)) throw new IOException();
            var final = new StringBuilder(512);
            uint count = GetFinalPathNameByHandleW(h, final, 512, 0);
            if (count == 0 || count >= 512 || !String.Equals(final.ToString(), @"\\?\" + path, StringComparison.OrdinalIgnoreCase)) throw new IOException();
            return h;
        } catch { h.Dispose(); throw; }
    }
    public static A1BinaryMetadata Inspect(string path) {
        var held = new List<SafeFileHandle>();
        try {
            string root = Path.GetPathRoot(path);
            if (GetDriveTypeW(root) != 3) throw new IOException(); // Reject mapped/removable drives.
            held.Add(Open(root, true));
            string parent = root;
            var parts = path.Substring(root.Length).Split('\\');
            for (int n = 0; n < parts.Length - 1; n++) {
                parent = Path.Combine(parent, parts[n]); held.Add(Open(parent, true));
            }
            using (var h = Open(path, false))
            using (var stream = new FileStream(h, FileAccess.Read)) {
                if (stream.Length < 2 || stream.Length > 268435456 || stream.ReadByte() != 77 || stream.ReadByte() != 90) throw new IOException();
                stream.Position = 0;
                string hash;
                using (var sha = SHA256.Create()) { hash = BitConverter.ToString(sha.ComputeHash(stream)).Replace("-", "").ToLowerInvariant(); }
                // Same path remains locked; no CLI --version and no resource strings emitted raw.
                return new A1BinaryMetadata { Hash = hash, Version = FileVersionInfo.GetVersionInfo(path).ProductVersion ?? "" };
            }
        } finally { for (int n = held.Count - 1; n >= 0; n--) held[n].Dispose(); }
    }
}
'@ -ErrorAction Stop
    }
    return [A1BinaryMetadata]::Inspect($Path)
}

function Invoke-TransportPreflight([object[]]$Items) {
    $report = New-TransportReport
    $exitCode = 1
    try {
        $options = Read-TransportArguments $Items
    } catch {
        $report.reason = 'INVALID_ARGUMENT'
        return @{ Report = $report; ExitCode = 2 }
    }
    try {
        $hostMetadata = Get-TransportHostMetadata
        if (-not $hostMetadata.Windows -or $PSVersionTable.PSVersion.Major -lt 7) {
            $report.platform = 'UNSUPPORTED'; $report.reason = 'UNSUPPORTED_PLATFORM'
        } else {
            $report.platform = 'WINDOWS'
            # Validate every variable metadata field before emitting it.
            if ($hostMetadata.OsVersion -cnotmatch '^[0-9]{1,5}(\.[0-9]{1,5}){1,3}\z' -or
                $hostMetadata.Architecture -cnotmatch '^(X86|X64|Arm|Arm64)\z') { throw 'METADATA_UNAVAILABLE' }
            $report.os_version = $hostMetadata.OsVersion
            $report.architecture = $hostMetadata.Architecture
            if ($options.CodexBinaryPath) {
                $metadata = Get-CandidateMetadata $options.CodexBinaryPath
                if ($metadata.Hash -cnotmatch '^[0-9a-f]{64}\z') { throw 'METADATA_UNAVAILABLE' }
                $report.binary_sha256 = $metadata.Hash
                $report.binary_pin = if ($metadata.Hash -ceq $options.ExpectedSha256.ToLowerInvariant()) { 'MATCH' } else { 'MISMATCH' }
                if ($metadata.Version -cmatch '^[0-9]{1,5}(\.[0-9]{1,5}){1,3}\z') {
                    $report.binary_version = $metadata.Version
                    $report.version_pin = if ($metadata.Version -ceq $options.ExpectedVersion) { 'MATCH' } else { 'MISMATCH' }
                }
                $report.reason = if ($report.binary_pin -eq 'MISMATCH' -or $report.version_pin -eq 'MISMATCH') { 'PIN_MISMATCH' } elseif ($report.version_pin -eq 'NOT_TESTED') { 'VERSION_UNAVAILABLE' } else { 'METADATA_ONLY' }
            }
        }
    } catch {
        # No raw error, path, account identifier, arbitrary resource string or log.
        $report.binary_sha256 = ''; $report.binary_version = ''
        $report.binary_pin = 'NOT_TESTED'; $report.version_pin = 'NOT_TESTED'
        $report.reason = 'METADATA_UNAVAILABLE'
    }
    return @{ Report = $report; ExitCode = $exitCode }
}

$result = Invoke-TransportPreflight @($args)
$result.Report | ConvertTo-Json -Compress
exit $result.ExitCode
