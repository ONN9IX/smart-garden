# Read-only Task Scheduler candidate. Never registers or enables a task.
param(
    [ValidateSet('DryRun','Status','Candidate','Install','Uninstall')]
    [string]$Mode = 'DryRun'
)
$ErrorActionPreference = 'Stop'
$taskName = 'SmartGarden-Dispatcher-Candidate'
switch ($Mode) {
    'DryRun' {
        Write-Output 'DISABLED; WAITING_APPROVAL; NO_GO; no worker or publisher launched.'
    }
    'Status' {
        $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        if ($null -eq $task) { Write-Output 'NOT_INSTALLED' }
        elseif ($task.State -ne 'Disabled') { throw 'Unexpected active task: security acceptance required.' }
        else { Write-Output 'DISABLED' }
    }
    'Candidate' {
        # Owner must pin absolute trusted Python/script paths and a dedicated
        # non-admin controller SID after security acceptance. No secrets in XML.
        Write-Output @'
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Disabled offline candidate; security gate pending</Description></RegistrationInfo>
  <Triggers><TimeTrigger><Repetition><Interval>PT2H</Interval><StopAtDurationEnd>false</StopAtDurationEnd></Repetition><StartBoundary>2026-10-09T00:00:00</StartBoundary><Enabled>true</Enabled></TimeTrigger></Triggers>
  <Principals><Principal id="Controller"><UserId>OWNER_MUST_SET_CONTROLLER_SID</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><StartWhenAvailable>false</StartWhenAvailable><ExecutionTimeLimit>PT10M</ExecutionTimeLimit><Enabled>false</Enabled></Settings>
  <Actions Context="Controller"><Exec><Command>OWNER_MUST_PIN_TRUSTED_PYTHON</Command><Arguments>"OWNER_MUST_PIN_TRUSTED_DISPATCHER" --dry-run</Arguments><WorkingDirectory>OWNER_MUST_PIN_CONTROLLER_DIRECTORY</WorkingDirectory></Exec></Actions>
</Task>
'@
    }
    'Install' { throw 'NO_GO: installation requires separate Master Chat host authorization and witnessed isolation acceptance.' }
    'Uninstall' { throw 'No task installed by this delivery. Owner must approve removal of any existing OS task.' }
}
