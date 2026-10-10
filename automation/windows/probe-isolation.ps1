# Future owner-approved canary opens ONLY; no provisioning or secret contents.
# Run as actual non-admin worker after separate host approval, never as owner.
# Owner independently attests canary existence/ACL/token provenance. Denial alone
# is not acceptance. This reporter ALWAYS returns NO_GO, including all denials.
$ErrorActionPreference = 'Stop'
$names = @('ExpectedWorkerSid', 'OAuthCanary', 'GitCanary', 'RegistryCanary',
    'ControllerCanary', 'RootCanary', 'StateCanary', 'AuditCanary')
$values = @{}
$invalid = $args.Count -gt 16 -or ($args.Count % 2) -ne 0
for ($index = 0; -not $invalid -and $index -lt $args.Count; $index += 2) {
    $key = [string]$args[$index]
    if (-not $key.StartsWith('-')) { $invalid = $true; break }
    $key = $key.Substring(1)
    if ($key -cnotin $names -or $values.ContainsKey($key)) { $invalid = $true; break }
    $values[$key] = [string]$args[$index + 1]
}
if ($invalid -or -not $values.ContainsKey('ExpectedWorkerSid') -or
    $values.ExpectedWorkerSid -cnotmatch '^S-1-5-21-(?:[0-9]{1,10}-){3}[0-9]{1,10}\z') {
    '{"decision":"NO_GO","evidence":"NOT_TESTED","input":"REJECTED"}'
    exit 2
}
foreach ($key in $names[1..7]) {
    if ($values.ContainsKey($key)) {
        # Explicit local ASCII synthetic paths only: no ADS/UNC/devices/globs.
        $path = $values[$key]
        if ($path.Length -gt 240 -or $path -cnotmatch '^[A-Za-z]:\\(?:[A-Za-z0-9_-][A-Za-z0-9_. -]*\\)*[A-Za-z0-9_-][A-Za-z0-9_. -]*\z') {
            '{"decision":"NO_GO","evidence":"NOT_TESTED","input":"REJECTED"}'
            exit 2
        }
        foreach ($part in $path.Substring(3).Split('\')) {
            if ($part.EndsWith('.') -or $part.EndsWith(' ') -or
                $part -match '^(?i:CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\.|$)') {
                '{"decision":"NO_GO","evidence":"NOT_TESTED","input":"REJECTED"}'
                exit 2
            }
        }
    }
}
try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if ($identity.User.Value -cne $values.ExpectedWorkerSid -or
        $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Wrong worker identity'
    }
} catch {
    '{"decision":"NO_GO","evidence":"NOT_TESTED","identity":"NOT_ACCEPTED"}'
    exit 1
}
$items = @(
    @{Name='OAuth';Key='OAuthCanary';Write=$false},
    @{Name='Git';Key='GitCanary';Write=$false},
    @{Name='Registry';Key='RegistryCanary';Write=$true},
    @{Name='Controller';Key='ControllerCanary';Write=$true},
    @{Name='Root';Key='RootCanary';Write=$true},
    @{Name='State';Key='StateCanary';Write=$true},
    @{Name='Audit';Key='AuditCanary';Write=$true}
)
$results = [ordered]@{}
foreach ($item in $items) {
    $stream = $null
    if (-not $values.ContainsKey($item.Key)) { $results[$item.Name] = 'NOT_TESTED'; continue }
    try {
        # Reparse/link/provenance uncertainty is NOT_TESTED, never acceptance.
        $target = New-Object IO.FileInfo($values[$item.Key])
        $parent = $target.Directory
        while ($null -ne $parent) {
            if (-not $parent.Exists -or ($parent.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                throw 'Unsafe canary parent'
            }
            $parent = $parent.Parent
        }
        if (-not $target.Exists -or ($target.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw 'Missing or unsafe canary'
        }
        $access = [IO.FileAccess]::Read
        if ($item.Write) { $access = [IO.FileAccess]::Write }
        # Open existing file only; no content transferred. Write-only ACLs
        # must fail the protected-write-denial check: never request ReadWrite.
        $stream = [IO.File]::Open($values[$item.Key], [IO.FileMode]::Open, $access, [IO.FileShare]::ReadWrite)
        $results[$item.Name] = 'FAIL_ACCESSIBLE'
    } catch [UnauthorizedAccessException] {
        $results[$item.Name] = 'DENIED_OPEN_ONLY'
    } catch {
        $results[$item.Name] = 'NOT_TESTED'
    } finally {
        if ($null -ne $stream) { $stream.Dispose() }
    }
}
[ordered]@{decision='NO_GO';evidence='NOT_TESTED';canaries=$results;
    credential_manager='NOT_TESTED';process_memory='NOT_TESTED';environment='NOT_TESTED';
    ipc_loopback_network='NOT_TESTED';hardlink_and_race_provenance='NOT_TESTED';
    owner_witness='REQUIRED';execution='DISABLED'} | ConvertTo-Json -Depth 3 -Compress
exit 1
