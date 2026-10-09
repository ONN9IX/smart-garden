# Run ONLY as the real non-admin model worker identity, never as owner/admin.
# Synthetic canaries must be provisioned by owner outside the workspace using
# the SAME ACLs as OAuth, git/SSH/gh caches, and controller registry respectively.
# Reading actual secrets is forbidden. Missing/inaccessible parent is NOT proof.
param(
    [Parameter(Mandatory=$true)][string]$ExpectedWorkerSid,
    [Parameter(Mandatory=$true)][string]$OAuthCanary,
    [Parameter(Mandatory=$true)][string]$GitCanary,
    [Parameter(Mandatory=$true)][string]$RegistryCanary
)
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
if ($identity.User.Value -ne $ExpectedWorkerSid) { throw 'Wrong worker identity; acceptance NOT TESTED.' }
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Admin worker forbidden.' }
$failed = $false
foreach ($item in @(@{Name='OAuth';Path=$OAuthCanary;Write=$false}, @{Name='Git';Path=$GitCanary;Write=$false}, @{Name='Registry';Path=$RegistryCanary;Write=$true})) {
    $stream = $null
    try {
        $access = [IO.FileAccess]::Read
        if ($item.Write) { $access = [IO.FileAccess]::ReadWrite }
        # Open existing file only; do not read or change any content.
        $stream = [IO.File]::Open($item.Path, [IO.FileMode]::Open, $access, [IO.FileShare]::ReadWrite)
        Write-Output ('FAIL: {0} accessible' -f $item.Name)
        $failed = $true
    } catch [UnauthorizedAccessException] {
        Write-Output ('DENIED: {0}' -f $item.Name)
    } catch {
        Write-Output ('NOT_TESTED: {0}' -f $item.Name)
        $failed = $true
    } finally {
        if ($null -ne $stream) { $stream.Dispose() }
    }
}
Write-Output 'Canary checks alone do not authorize activation: owner must attest existence, matching ACLs, Credential Manager/process/network isolation and worker-token provenance.'
if ($failed) { exit 1 }
exit 0
