# Offline readiness report only. Never provisions or probes real protected assets.
# Exit 1 is intentional: this delivery cannot accept a credential transport.
# Use controller.py --report: startup opt-out must be set BEFORE pwsh starts.
$ErrorActionPreference = 'Stop'
# Avoid argument-binder errors that echo untrusted values.
if ($args.Count -ne 0 -and -not ($args.Count -eq 2 -and $args[0] -ceq '-Mode' -and $args[1] -ceq 'Report')) {
    '{"decision":"NO_GO","evidence_class":"STATIC","input":"REJECTED","execution":"DISABLED"}'
    exit 2
}
$report = [ordered]@{
    schema = 2
    issue = 216
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
    raw_git_verifier = 'SYNTHETIC_ONLY'
    github_provenance = 'SYNTHETIC_ONLY'
    independent_review_provider = 'NOT_PROVISIONED'
    live_windows_boundaries = 'NOT_TESTED'
    sam_activation = 'NO_GO'
    notification_channel = 'CHATGPT_TASKS_MASTER_CHAT'
}
$report | ConvertTo-Json -Compress
exit 1
