# Offline readiness report only. Never provisions or probes real protected assets.
# Exit 1 is intentional: this delivery cannot accept a credential transport.
# Use controller.py --report: startup opt-out must be set BEFORE pwsh starts.
[CmdletBinding()]
param([ValidateSet('Report')][string]$Mode = 'Report')
$ErrorActionPreference = 'Stop'
$report = [ordered]@{
    schema = 1
    issue = 209
    decision = 'NO_GO'
    evidence_class = 'STATIC'
    credential_transport = 'NOT_ACCEPTED'
    worker_token = 'NOT_TESTED'
    credential_read_denial = 'NOT_TESTED'
    controller_write_denial = 'NOT_TESTED'
    process_environment_network = 'NOT_TESTED'
    approval_ledger = 'NOT_PROVISIONED'
    execution = 'DISABLED'
    publisher = 'ABSENT'
    scheduler_install = 'NOT_AUTHORIZED'
}
$report | ConvertTo-Json -Compress
exit 1
