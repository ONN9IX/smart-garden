# Issue #207: implementation candidate, activation NO-GO

Delivery baseline: `28512cc234ff4ce340aa2b96510fae2f249acbba`.
Approval: Master Chat comment `6079371964`. Only the frozen infrastructure
write-set is changed. The retired worker and empty allowlist remain untouched.

## What exists

`dispatcher.py` is an offline controller core with RSA-3072-or-larger strict
PKCS#1 SHA256 verification, canonical exact-path authorization, expiry,
revocation/replay checks, Git tree validation, exact-HEAD eight-job CI gate,
bounded repair state, atomic state replacement, and a Windows kernel byte lock.
It provides a side-effect-free dry-run entry point. There is deliberately no
credential broker, network adapter, model execution or publication adapter.
Lifecycle tests use synthetic controller snapshots; they do not execute Issues.
`synthetic-signature.json` is a disposable test-only public key/signature, never
a production trust root; its private key was discarded. Verification tests use
this real RSA signature and reject altered records and roots.
`synthetic-merge-signature.json` likewise holds only a disposable public key and
signed synthetic merge evidence; its private key was discarded.
GitHub prose is never parsed as authority, shell code or scheduler configuration.

The signer uses an owner-only private RSA key outside model reach. The public key
must be pinned in an owner-installed, ACL-protected controller outside repository
reach; a key supplied by an Issue or workspace file is untrusted. Sign canonical
ASCII JSON bytes using SHA256/PKCS#1 v1.5. Record fields are exactly `id`, `repo`,
`issue`, `base`, `branch`, `paths` (sorted exact files, no globs), timezone-aware
`expires`, `max_repairs` (0–3). Each identity is single-use for one delivery; a
protected durable ledger reserves it before work and binds resumed state to it.
Revocation must be freshly checked at every tick, repair and publication.
The approval transport and protected ledger integration are NOT installed.
`authorize` accepts an already cryptographically verified record; callers must
first call `verify_signature`. No repository record enables execution.

## Trust boundaries and activation prerequisites

Repository, Issues, PRs, logs, Git status from worker, and all model output are
hostile. Owner decisions must be copied into signed approvals through an
authenticated owner control outside the model session. Controller/publisher
must be separate OS identities from the non-admin worker. The worker must not
read controller files, owner profile, OAuth caches, gh/git/SSH credentials,
Credential Manager, process memory, or inherited credential environment. It
must not modify controller binaries, pinned interpreter, public roots, ledger,
scheduled task, audit output or publish directory. The sandbox must enforce
write-set confinement at OS level; post-hoc path checking is insufficient.

Publisher must independently collect raw Git objects with hooks, external diff,
filters, config includes, credential helpers and submodules disabled; validate
the complete old/new tree and rename/delete paths, reject links/gitlinks/reparse
points, then recheck main, approval revocation, PR identity and exact HEAD before
publication. No adapter accepts model-provided status as evidence. Path checks
in this core cannot prevent concurrent junction replacement: owner must ensure
worker termination and exclusive trusted publication snapshot first. An agent
with an unrestricted network channel can exfiltrate readable credentials.

One protected global lock path is shared by ALL ticks, not per worktree. OS lock
release on crash permits recovery without unsafe stale-file deletion. Durable
state must be read under that lock, bounded and schema-validated, and reserve
approval before side effects. A crash in RUNNING requires independent diff/PR
reconciliation, never a duplicate launch. PR_PENDING/READY_FOR_MASTER_CHAT block
the next Issue. Proceed only after authenticated owner merge evidence and all
eight green checks on the exact merge SHA. Missing/revoked approval or malformed
response stops work. No merge command exists. Repairs consume durable budgets
before launch; future adapter must bound total runtime/tokens, apply backoff,
and stop after recurrent failures. Scheduler runtime candidate is ten minutes.

Merge completion additionally requires a separately supplied signed owner record
with exactly `approval_id`, `repo`, `issue`, `pr`, `head`, `merge_sha`, verified
against the controller's pinned owner root. `observe` accepts that envelope and
root only as controller arguments, never snapshot fields. Its identity must match
the delivery and authenticated PR; its merge SHA must equal both the PR's actual
`merge_commit_sha` and current trusted main. Snapshot booleans alone cannot finish
a delivery. Collect PR/main/checks through the future authenticated adapter;
signed evidence does not authenticate GitHub data supplied by a worker.

## Confirmed limitation and local security gate

This delivery has no privileged Windows account/ACL provisioning authorization,
no accepted restricted worker token, and no credential transport that separates
existing ChatGPT sign-in from model shell. Therefore autonomous execution is
NO-GO. A shared-account Codex launch or copying OAuth would violate the Issue.
No live isolation acceptance is claimed. A future reviewed adapter and protected
owner provisioning require a separate Master Chat decision; simulated passing
tests or flags cannot activate this core (`require_execution` always denies).

Owner must witness `probe-isolation.ps1` under the actual worker SID with three
existing synthetic canaries whose ACLs match protected OAuth, git auth and
registry locations. It attempts file opens without reading/writing content;
missing paths and wrong identity fail. Owner separately verifies canary existence,
effective ACLs, all credential locations, Credential Manager, process handles,
environment and network boundaries. Do not pass actual secret file paths.

The registry probe opens with write-only access, without requesting read rights
or changing content. `test-probe-write-only.ps1` provisions only a disposable
synthetic file under the current non-admin identity, denies ReadData while
allowing writes, and verifies the actual probe exits 1. It restores the ACL and
removes that exact file. This regression does not prove a production worker's
credential isolation. New merge evidence and tests contain synthetic identifiers
and public signature metadata only; the privacy/152-FZ review below applies.

```powershell
powershell.exe -NoProfile -File automation/windows/probe-isolation.ps1 -ExpectedWorkerSid <worker-SID> -OAuthCanary <synthetic-protected-file> -GitCanary <synthetic-protected-file> -RegistryCanary <synthetic-protected-file>
```

This script does not create accounts, change ACLs, provision keys, or prove those
other OS boundaries. Windows live negative-security acceptance: NOT TESTED.

Local validation on 2026-10-09: the Windows Python unittest suite passes with
UTF-8 and process-only Git `core.autocrlf=false`, `core.whitespace=cr-at-eol`
(no global configuration change). It includes real junction/hardlink rejection
and real two-process lock/crash recovery. Two Python dry-runs produced identical
fixed disabled status. The n8n workflow structural validator passed. PowerShell
`-File` DryRun/Status were blocked by the host Execution Policy; policy was not
changed or bypassed. Thus task status, script runtime and credential denial
under a separate worker SID have NOT been validated live. Syntax/static tests
do not substitute for those gates.

P1 repair validation on 2026-10-09: 70 Windows unittest cases pass (one existing
OpenSSL installer skip). The write-allowed/read-denied ACL regression passed
under the current non-admin identity with PowerShell 7 `-File`, without changing
execution policy; actual probe exit 1 and unchanged canary content were checked.
This is a synthetic ACL regression, not witnessed dedicated-worker acceptance.
Signed merge completion/tamper rejection and mismatched main/PR/evidence negative
tests pass. Autonomous execution remains NO-GO.

## Windows candidate commands

Run from the delivery checkout; no elevation or execution-policy bypass:

```powershell
python automation/windows/dispatcher.py --dry-run
powershell.exe -NoProfile -File automation/windows/task-candidate.ps1 -Mode DryRun
powershell.exe -NoProfile -File automation/windows/task-candidate.ps1 -Mode Status
powershell.exe -NoProfile -File automation/windows/task-candidate.ps1 -Mode Candidate
python -m unittest discover -s automation/tests -p 'test_*.py'
```

Candidate prints disabled Task Scheduler XML with PT2H repetition, least
privilege, IgnoreNew and PT10M limit. Placeholders prevent unattended use without
owner provisioning. No task is registered. `-Mode Install` and `-Mode Uninstall`
fail closed. After a separate host approval, owner reviews and pins absolute
trusted interpreter/controller paths and SID and imports XML **disabled** in
Task Scheduler; inspection uses Status. Owner removes that candidate through
Task Scheduler after separate approval. Enabling requires a new security
acceptance and reviewed executable adapter, not editing this candidate.

## Privacy / 152-FZ review

Every helper handles synthetic identifiers, signatures, file metadata or state;
none needs Issue prose, personal records or credential contents. Dry-run emits
only fixed status fields, never paths, usernames, secrets or model/test output.
Future protected audit should contain approval ID, Issue/PR numbers, SHAs, enum
state/reason and timestamp only, with owner-approved retention and ACLs. No
production personal-data processing is introduced; this technical review is
not production legal compliance under 152-FZ.
