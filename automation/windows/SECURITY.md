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

## Issue #209 first-gate follow-up

See [HOST_PLAN.md](HOST_PLAN.md) for the credential-transport blocker, trust/action
matrix and exact acceptance sequence. This follow-up is the contract-permitted
blocker delivery; controller/worker/publisher adapters are deferred until a
supported separated transport and concrete host plan can be reviewed.
`acceptance.ps1` is an offline STATIC readiness reporter, always NO_GO (exit 1),
not a verifier of OS isolation. It cannot consume an accepted flag or workspace
evidence to enable execution. No host provisioning or live credential test was
performed. Existing execution denial and disabled task candidate are unchanged.
Use `python automation/windows/controller.py --report` to disable PowerShell
startup telemetry before launch and avoid passing ambient credential variables.
This wrapper is not a runtime model controller. Fixed report fields and synthetic
tests introduce no business personal-data processing; host metadata stays local.

## A1 / Issue #211: transport qualification security review

Approved four-file baseline `92aea397b4ecee449084d3a8e04ccce64c57004b`.
Research reference: Codex 0.162.0, commit
`c1382380de69521303b416720a52f42d51af6248`, not the installed Windows artifact.
[HOST_PLAN.md](HOST_PLAN.md) contains immutable sources, feasibility, future
checklist/approvals/rollback. Existing gates and retired worker stay unchanged.
Activation **NO-GO**; actual Windows isolation **NOT TESTED**.

Binary paths/pins/resource metadata, environment, workspace, RPC, Issue prose and
model output are untrusted. Hash match to caller input is not authority. Shell
and descendants must lack file/key-store credentials, credential-process memory/
handles/debug/dumps/environment and privileged IPC/loopback access. Refresh and
restart must preserve separation. `auto` storage fallback, backend fallback,
broad workspace writes and upgrades are risks. Storage modes and RPC are not
boundaries; #209's independent OS identities remain mandatory.

### New-function privacy/boundary review

| Function / helper | Data/effect | Limit |
| --- | --- | --- |
| `New-TransportReport` | Fixed enums and PowerShell version; no writes | STATIC, never GO |
| `Read-TransportArguments` | Bounded path/hash/version/Report; rejects duplicates/unknowns | No arbitrary commands/evidence or invalid-value echo |
| `Test-CandidatePath` | String-only validation | No artifact/owner attestation |
| `Get-TransportHostMetadata` | OS/platform/architecture versions | No credentials/policy/identity/backend inspection |
| `Get-CandidateMetadata`, native `Open`/`Inspect` | Fixed-source in-memory compilation; locked executable hash/metadata; disposed handles | No execution/secret paths; native behavior NOT TESTED in Cloud |
| `Invoke-TransportPreflight` | Validated output and fixed errors; always NO_GO | No network/auth/model/publication/provisioning |
| Test helpers | Disposable synthetic markers/fake metadata; bounded child env, telemetry opt-out before startup, no stdin | SYNTHETIC; AST overrides only in tests, no production simulation/acceptance input |

Only an explicitly selected owner-approved executable is hashed (256 MiB max).
Never pass renamed credential files or real secrets; owner verifies provenance.
Native code checks canonical fixed-drive paths, reparse ancestors, final handle
paths and single-link regular files; file read sharing denies concurrent write/
delete, directory handles deny deletion until inspection finishes. This is not
a sandbox, trusted publisher or proof of a protected Windows host.

No paths/SIDs/user/account IDs/raw exceptions/arbitrary resource strings appear
in reports. Version strings are bounded numeric fields; unknown resource versions
are NOT_TESTED. Set startup telemetry opt-out/update checks off before PowerShell;
script cannot retroactively suppress startup. Interpreter caches are outside the
script's no-persistent-write guarantee; Linux tests redirect them to disposable
fixtures. C# compilation can be tested on Linux, not Windows file enforcement.

Valid reports exit 1; invalid inputs exit 2 without parameter-binder echo. No env
booleans, workspace evidence, flags or modes can grant GO or change isolation
fields. STATIC, SYNTHETIC, LIVE-WITNESSED and NOT TESTED remain distinct; A1 has
no LIVE-WITNESSED acceptance. Future evidence needs protected provenance/freshness,
actual token/host binding and independent witness.

No production personal data, real credential reads, Windows ACL/accounts/policy/
auth changes, scheduler installation or model launch. Host evidence requires
owner-approved retention/access. This is technical privacy/152-FZ review, not
production legal compliance. Blocker delivery is valid; provisioning, functional
transport tests, adapters, merge and activation still need separate decisions.


## A2 / Issue #214 — offline protected-core implementation boundaries (2026-10-10)

This addition is **STATIC/SYNTHETIC only**. The new importable modules are
`controller_core.py`, `approval_store.py`, `worker_adapter.py`, and
`publisher.py`. They are independent offline harnesses and do **not**
replace the existing `dispatcher.py`, retired worker or `controller.py`.
A2 code must never become the privileged production trust anchor by copying
the files or setting an environment flag.

- `SyntheticApprovalStore`: isolated disposable test directory, RSA signed
  approval checked using existing #207 strict verifier, durable lock,
  reservations/consumption/revocation. It does not attest real directory ACLs,
  signing-key custody, independent approval issuance or actual revocation feed.
  `require_live_store()` always denies.
- `SyntheticControllerCore`: bounded, serialized state transitions over
  owner-supplied **synthetic** snapshots; relies on existing exact eight-job
  checks and independently signed merge evidence from #207; persists crash
  state and blocks pending post-merge after timeout. Not a real GitHub reader.
  `require_execution()` always denies.
- `FakeWorkerAdapter`: fixed synthetic event strings only; no shell, CLI,
  model, login, network, credentials or output publication; launch/publish/
  merge always deny. Simulation is not isolation.
- `publisher.py`: validates complete *synthetic* Git tree dictionaries and
  computes delta independent of worker-reported changed paths; rejects
  out-of-scope changes, unsafe modes, path aliases, hardlink/reparse metadata
  and Git execution-configuration changes. The returned decision is always
  NO_GO. Actual immutable OS snapshot, real Git object provenance,
  link-race prevention, isolated Git process/environment and independent
  GitHub authenticated state remain **NOT TESTED**.

All new files are permanently non-privileged; they cannot launch worker/model,
provision host, install scheduler, read credentials, push, create/update PR or
merge. Synthetic status/result fields cannot assert LIVE-WITNESSED or GO.
No production PII, secrets, host paths or SIDs are required; tests use only
temporary synthetic records/objects. Each function has a minimized-data privacy
boundary; this is not 152-FZ production legal acceptance.

SAM-1 design #213 remains **INACTIVE / AUTO-MERGE NO-GO**. No trusted
security-check publisher, actual signed single-use merge permit, owner
root/ledger provisioning, branch-protection change, real credential transport
or Windows isolation acceptance is delivered in A2. Further permissions,
rulesets, host provisioning, real publication or activation require separate
owner decision and LIVE-WITNESSED evidence where appropriate.

## A3 / Issue #216 — integrated offline interfaces, live gates CLOSED

Baseline `cb5072aa39fb73a4cf3bae4cae4f10ee5773c2e3`. Only #216's 16
approved paths may change; no product, workflow, dependencies, signed fixtures,
retired worker, ruleset or host changes. #213 SAM-1 remains INACTIVE. ChatGPT
Tasks / Master Chat are the selected notification/confirmation channel; old
Telegram/n8n notification proposals are superseded, not implemented.

### Protected-core candidate and durable synthetic authority

`SyntheticProtectedController` uses `SyntheticDeliveryStore` under the same
single directory-global `controller.lock` as A2. Initialize explicitly in a
new disposable directory. A committed initialization marker makes a missing,
corrupt or partial ledger a denial instead of an empty replay state. A marker
committed before a crash does not authorize reinitialization. The entire
approval/fingerprint, delivery, nonce consumption/revocation, reserved attempt
IDs, spent token ceilings, absolute deadline, PR/head/merge identity and bounded
post-merge query count are committed as ONE atomic document. Flush before
fake invocation and before acknowledgement; directory fsync on POSIX only.
No two independent state writes are claimed to be a single transaction.

The existing eight-field #207 signed scope and signed `max_repairs` remain
unchanged. Fixture limits (600-second total, at most 120 seconds/1024 tokens
per attempt and 4096 total tokens) are fixed maximum accounting constraints;
callers can lower them before reservation, never increase them on restart.
They are NOT an owner-signed runtime resource policy or native metering. A
future live schema must independently bind operations, policy/version,
expiration/nonces and resource permissions; new flags cannot confer authority.

Fresh strict signature, repo/Issue/branch/base/exact paths, expiry, consumed and
revoked checks precede start, repair and candidate verification. Reservation
fingerprint binds the complete scope across restarts. No next delivery before
separately signed owner merge + independent fixture PR/main + exact eight-job
post-merge SUCCESS + durable consumption. Unknown RUNNING outcome is BLOCKED
without duplicate work. Exceptions, exhausted budgets, cancellation, timeouts,
ambiguous collector state and incomplete/failed post checks block. Polling is
bounded (20 queries and two-hour persisted post-merge deadline); never reruns CI.
No raw error, PR/Issue prose, logs or arbitrary callback is executed or persisted.

### Worker and publisher boundaries

`ReservedSyntheticUnit` is an immutable minimized task containing scope,
attempt identity, scope digest and limits; no environment, credentials or
shell command. Only the exact `FakeWorkerAdapter` type is admitted. Its finite
allowlisted result enums simulate accounting/cancellation/timeouts. There is
no Codex CLI/app-server launcher, sign-in flow, privileged process or network.
All require_execution/launch/publish/merge seams always deny, regardless of
synthetic signatures, environment flags or "accepted" workspace metadata.

`SyntheticEvidenceFeed` authenticates finite OFFLINE envelopes using an
independent disposable collector root; the controller rejects reuse of its
owner root for the collector. Fixture policy binds repository, Issue, policy,
PR origin/branch/base/head, review identity, exact App-like IDs, expiry and
collection time. Eight checks must be SUCCESS on the exact current HEAD.
Named checks alone, implementer review, stale review/policy, blocking findings,
fake merge fields, foreign forks and HEAD/base drift are rejected. Recollect
after tree verification. These signatures authenticate test data, NOT real
GitHub state or a provisioned GitHub App. No signed model output may be treated
as a trusted online collector. `SYNTHETIC` can never claim `LIVE-WITNESSED`.

`LooseFixtureGitReader` independently reads/hashes complete raw loose commit,
tree and blob objects from a disposable stopped fixture. It verifies object
header/type/size/hash, baseline ancestry and loose HEAD/branch/main refs; denies
packs, gitdir/commondir indirection, alternates/replacements/grafts/shallow data,
links/reparse/hardlinks, path/case/directory aliases, unsafe modes, oversized or
corrupt objects and detectable replacement. Config/hooks/filters, external diff,
credential helpers and submodules are NEVER invoked: no Git subprocess exists.
All changed added/modified/deleted/rename-source/rename-target paths are derived
from full trees. Existing unchanged workflow/executable blobs may be inspected;
changes to protected namespaces or executable modes cannot be authorized by
this worker approval. The reader is conservative and cannot verify the actual
packed repository; unsupported input denies rather than falling back to Git.

Directory custody, malicious concurrent writers, atomic stopped-worker snapshot,
native Windows locks/durability, real API provenance/revocation feeds, check
provider protection and network credentials remain NOT TESTED. Metadata
rechecks or a cooperative Python lock do not prove Windows TOCTOU protection.
The publisher returns NO_GO and has no actual push/PR/merge adapter.

### Acceptance and privacy review

`acceptance.ps1` is a deterministic static NO_GO reporter; bad arguments are
redacted fixed denials. `controller.py --report` starts only that reporter with
telemetry opt-out, bounded timeout, dropped ambient credential variables and
disposable startup caches. It never launches a model. `probe-isolation.ps1`
accepts only explicit synthetic local paths and actual expected non-admin SID;
opens existing canaries without reading/writing contents. Registry/controller/
root/state/audit opens request WRITE alone, preventing read-denied/write-allowed
false positives. Wrong identity, missing/inaccessible metadata, reparse/path
ambiguity => NOT_TESTED. It ALWAYS returns NO_GO, even after denied opens;
Credential Manager/process/env/IPC/network/hardlink/race provenance need
independent owner-witnessed tests. No actual credential path may be supplied.

Privacy / 152-FZ review by function family: ledger/signature helpers handle
synthetic IDs/public signature metadata and canonical scope; fake work handles
fixed enums and limits; evidence validation handles synthetic IDs/SHAs and
provider enums; raw-object reader inspects disposable synthetic source objects
without emitting contents; reporter/probe emit only fixed statuses, no host
path/SID/usernames, token/secret contents or arbitrary logs. Tests generate only
disposable synthetic RSA private keys outside Git, use temporary canaries,
and clean them up. No production personal data or legal compliance is claimed.

Host provisioning/ACL/account/auth/firewall/scheduler/worker/model/publisher/
ruleset/SAM activation remain NO-GO. See HOST_PLAN for the concrete protected
manifest, proposal, witness evidence, separate owner approvals and rollback.
