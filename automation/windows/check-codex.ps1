# Read-only Windows preflight for a locally installed Codex CLI.
# Does not create tasks, mutate GitHub, print credentials, or modify local files.
param([switch]$CheckCloud)

$ErrorActionPreference = 'Stop'
$script:Failed = $false

function Show-Check([string]$Name, [bool]$Ok, [string]$Hint) {
    if ($Ok) {
        Write-Host "[PASS] $Name"
    } else {
        Write-Host "[ACTION NEEDED] $Name - $Hint"
        $script:Failed = $true
    }
}

$codexCmd = Get-Command 'codex' -ErrorAction SilentlyContinue
if ($null -eq $codexCmd) {
    Show-Check 'Codex CLI in PATH' $false 'Only the desktop app may be installed; install/access Codex CLI separately.'
} else {
    Show-Check 'Codex CLI in PATH' $true ''
    try {
        & codex --version *> $null
        Show-Check 'Codex CLI starts' ($LASTEXITCODE -eq 0) 'Check Codex CLI installation.'
    } catch {
        Show-Check 'Codex CLI starts' $false 'Check Codex CLI installation.'
    }
    try {
        # Suppress output: the auth status may contain personal/account details.
        & codex login status *> $null
        Show-Check 'ChatGPT sign-in available' ($LASTEXITCODE -eq 0) 'Sign in interactively using codex login.'
    } catch {
        Show-Check 'ChatGPT sign-in available' $false 'Sign in interactively using codex login.'
    }
    if ($CheckCloud) {
        try {
            # This is read-only; NEVER call `codex cloud exec` in preflight.
            & codex cloud list --json --limit 1 *> $null
            Show-Check 'Codex Cloud read-only listing' ($LASTEXITCODE -eq 0) 'Check cloud availability and publish a cloud environment.'
        } catch {
            Show-Check 'Codex Cloud read-only listing' $false 'Check cloud availability and publish a cloud environment.'
        }
    }
}

try {
    $response = Invoke-RestMethod -Uri 'https://api.github.com/repos/ONN9IX/smart-garden/branches/main' -Headers @{'User-Agent'='smart-garden-codex-preflight'} -TimeoutSec 20 -Method Get
    $sha = [string]$response.commit.sha
    Show-Check 'Read-only GitHub connectivity' ($sha -match '^[0-9a-f]{40}$') 'Check HTTPS access to api.github.com.'
} catch {
    Show-Check 'Read-only GitHub connectivity' $false 'Check HTTPS access to api.github.com.'
}

Write-Host ''
Write-Host 'This check changed no files or GitHub resources and launched no coding task.'
if ($script:Failed) { exit 1 }
exit 0
