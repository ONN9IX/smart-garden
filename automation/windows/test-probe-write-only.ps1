# Synthetic ACL regression only. Never pass real registry or credential paths.
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { exit 77 }
$path = Join-Path ([IO.Path]::GetTempPath()) ([Guid]::NewGuid().ToString() + '.canary')
$original = $null
try {
    [IO.File]::WriteAllText($path, 'synthetic-canary')
    # Copy only the DACL; never request SACL/owner privileges during restoration.
    $sections = [Security.AccessControl.AccessControlSections]::Access
    $sddl = (Get-Acl -LiteralPath $path).GetSecurityDescriptorSddlForm($sections)
    $original = [Security.AccessControl.FileSecurity]::new()
    $original.SetSecurityDescriptorSddlForm($sddl, $sections)
    $acl = [Security.AccessControl.FileSecurity]::new()
    $acl.SetSecurityDescriptorSddlForm($sddl, $sections)
    $acl.SetAccessRuleProtection($true, $false)
    $allow = [Security.AccessControl.FileSystemAccessRule]::new($identity.User, 'FullControl', 'Allow')
    $deny = [Security.AccessControl.FileSystemAccessRule]::new($identity.User, 'ReadData', 'Deny')
    $acl.AddAccessRule($allow)
    $acl.AddAccessRule($deny)
    [IO.FileSystemAclExtensions]::SetAccessControl([IO.FileInfo]::new($path), $acl)
    $readDenied = $false
    try {
        $stream = [IO.File]::Open($path, [IO.FileMode]::Open, [IO.FileAccess]::ReadWrite)
        $stream.Dispose()
    } catch [UnauthorizedAccessException] { $readDenied = $true }
    if (-not $readDenied) { throw 'Synthetic ReadWrite must be denied.' }
    $stream = [IO.File]::Open($path, [IO.FileMode]::Open, [IO.FileAccess]::Write)
    $stream.Dispose()
    # Run the actual probe in a child process: its exit 1 must identify the
    # writable registry even though both credential read probes are denied.
    $output = & (Get-Process -Id $PID).Path -NoProfile -File (Join-Path $PSScriptRoot 'probe-isolation.ps1') -ExpectedWorkerSid $identity.User.Value -OAuthCanary $path -GitCanary $path -RegistryCanary $path 2>&1
    if ($LASTEXITCODE -ne 1 -or $output -notcontains 'FAIL: Registry accessible' -or $output -notcontains 'DENIED: OAuth' -or $output -notcontains 'DENIED: Git') {
        throw 'Probe failed to detect synthetic write-only access.'
    }
    [IO.FileSystemAclExtensions]::SetAccessControl([IO.FileInfo]::new($path), $original)
    if ([IO.File]::ReadAllText($path) -ne 'synthetic-canary') { throw 'Canary content changed.' }
    Write-Output 'WRITE_ONLY_REGRESSION_OK'
} finally {
    if ($null -ne $original) { [IO.FileSystemAclExtensions]::SetAccessControl([IO.FileInfo]::new($path), $original) }
    Remove-Item -LiteralPath $path -ErrorAction SilentlyContinue
}
