# Issue #209: credential transport blocker and host acceptance plan

Baseline: `4ccd113cf20e1a80a486addc2a865e727b0e104d` (merged #208).
Scope approval: #209 comment 6080930686. This is the blocker delivery permitted
by #209, not an implementation of controller/worker/publisher runtime adapters.
No independent worker identity, protected ledger, credential transport or
publication adapter has been provisioned or accepted. Activation: **NO-GO**.

## First gate result (2026-10-09)

The supported authentication options do not by themselves establish the required
host boundary. [Official authentication documentation](https://learn.chatgpt.com/docs/auth)
describes file, OS credential-store and process-memory credential storage.
Changing storage does not prove denial to an agent shell, Credential Manager
or another process. This delivery neither reads auth caches nor changes storage.

[Official Windows sandbox documentation](https://learn.chatgpt.com/docs/windows/windows-sandbox)
describes MXC and legacy implementations; legacy unelevated mode lacks denied
read paths and has weaker network isolation. Compatibility and documentation do
not attest the effective implementation or restrictions on this host.

Inference: a protected model process plus restricted command runner may be a
viable architecture, but it is NOT demonstrated here. We have no authenticated,
witnessed evidence tying a specific worker token to secret-read, protected-write,
process, environment and network denial. We cannot claim transport impossibility
in general, nor claim this host is insecure from a repository-access failure.
The concrete blocker is **no accepted credential-separated execution transport**.
Shared-account launch, copying OAuth or using an API-key fallback is prohibited.
No real model invocation is needed to finish this blocker PR.

## Trust and action matrix

| Asset or operation | Controller/publisher | Worker | Acceptance evidence |
| --- | --- | --- | --- |
| Owner private signing key | Separate owner signer only | No read/write | Owner verifies custody; never passed to tests |
| Pinned public root/interpreter/controller | Read/execute protected copy | No write | Canary ACL plus binary/path provenance |
| Approval/revocation/reservation ledger | Validated read/atomic write under lock | No write | Actual-token write-denial canary |
| State/audit/global lock | Trusted read/write only | No write | Restart/race tests plus protected-directory denial |
| OAuth/git/gh/SSH caches | Only intended credential process | No read/write | Matching canary, environment/process/key-store checks |
| Worker workspace | Read exclusive stopped snapshot | Exact approved file writes only | OS confinement and independent full Git-tree verification |
| Network/model transport | Narrow authenticated endpoint boundary | No credential-bearing ambient channel | Witnessed blocked exfiltration tests, no real secret payload |
| Scheduled task/host configuration | Owner-managed only | No change | Absent/disabled status; no install in this PR |

The controller must not run untrusted workspace scripts with its credentials.
Issue text, model output, Git config/hooks/filters, test output and worker status
are untrusted. Credential-bearing controller/publisher processes must never
inherit model-provided environment or shell commands. A future publisher needs
a stopped-worker, exclusive raw Git snapshot and complete old/new tree checks.

## Concrete sequence before host changes

1. Owner selects the supported transport and effective sandbox implementation;
   captures installed version, policy and compatibility using metadata only.
   Review a pinned implementation showing separation of model process and shell.
2. In a protected owner record (not GitHub), bind actual controller/publisher and
   worker SIDs, absolute trusted interpreter/binary paths and hashes, worker
   workspace, global lock, registry/state/audit paths, ACLs and network policy.
   All identifiers are currently **UNRESOLVED**; do not substitute the current
   user or a temporary file as accepted worker identity.
3. Present the exact provisioning commands, effective ACLs, process restrictions,
   allowed endpoints, service/task changes and rollback for those resolved values.
   Obtain separate approval for that concrete plan before executing it. Broad
   Chat assent does not resolve missing host values or make tests witnessed.
4. Owner provisions outside model reach. Keep every scheduler absent/disabled;
   no unattended model or publication invocation. No ExecutionPolicy weakening.
5. Owner confirms canaries exist, have equivalent effective ACLs to each protected
   location, and records worker token provenance. Run read-only open tests using
   the real worker token; never substitute owner/admin or pass secret paths.
6. Independently witness process-handle/memory, Credential Manager, environment
   and network denial with synthetic data. A canary-only result is insufficient.
7. A subsequent reviewed adapter must consume independently authenticated signed
   approval/evidence, not arbitrary repository JSON or a boolean accepted flag.
   Only after review and complete witnessed evidence can the owner decide on
   activation. Merge is a separate decision; this PR cannot turn on execution.

## Required witnessed results

| Boundary | Pass condition | Current class/result |
| --- | --- | --- |
| Credential transport | Model request works through protected transport; shell has no tokens/cache/key-store/process access | NOT TESTED |
| Worker identity | Exact independently attested non-admin restricted token | NOT TESTED |
| OAuth/git caches | Matching existing canary read denied under that token | NOT TESTED |
| Registry/root/controller/state/audit | Write denied, including write-only access | NOT TESTED |
| Filesystem | Read secrets denied; write-set escapes and link swaps prevented at OS boundary | NOT TESTED |
| Process/environment | Handle/memory and inherited secret channels denied | NOT TESTED |
| Network | Synthetic unauthorized egress denied; permitted transport bounded | NOT TESTED |
| Approval lifecycle | Signed exact identity/base/scope; revocation/replay checked every operation; protected durable ledger | SYNTHETIC in #208; host NOT TESTED |
| Publisher | Complete raw tree verification, stopped worker and exact-HEAD authenticated publication | NOT IMPLEMENTED |
| Restart/merge/CI | Durable budgets; no next Issue until signed merge and exact post-merge 8/8 | SYNTHETIC in #208; runtime NOT TESTED |

Record each test's binary/plan digest, time, token provenance, canary equivalence,
fixed result and independent witness in owner-protected evidence. Freshness,
revocation, plan/host/SID binding and trusted origin are mandatory for a future
verifier. Do not place actual paths/SIDs or credential material in public reports.
STATIC/SYNTHETIC cannot be upgraded to LIVE-WITNESSED by editing JSON or flags.

## Offline acceptance command and exit semantics

`python automation/windows/controller.py --report`
prints a fixed STATIC/NO_GO report and deliberately exits **1**. It reads no
credentials, host configs, arbitrary evidence or Issue text; creates no files;
changes no ACL/accounts/tasks; launches no model/publisher. Report repetition
is deterministic. Unknown modes/arguments fail. This is a readiness reporter,
not a witnessed isolation test or activation certificate. Existing
`probe-isolation.ps1` remains the separate canary test requiring real worker SID.

The Python wrapper sets POWERSHELL_TELEMETRY_OPTOUT=1 before launching PowerShell,
disables its update check, filters the child environment to OS/runtime metadata,
closes stdin and bounds runtime. It overrides inherited telemetry opt-in.
Calling acceptance.ps1 directly does not suppress startup telemetry: use the
wrapper. See [Microsoft telemetry documentation](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_telemetry).
The wrapper is not a model controller, accepted interpreter or trust anchor;
its PATH-resolved runtime cannot establish host acceptance. Missing PowerShell
returns NO_GO/NOT_TESTED. A zero child exit cannot authorize activation.

## Rollback and privacy

This PR performs no host provisioning, so there are no host changes to undo.
For a later host plan, owner records pre-change ACL/policy metadata and owns
rollback: revoke approval first, stop execution, disable task, remove only newly
approved components, restore specifically changed ACL/rules, verify disabled
status. Never recursively remove a path computed from worker text.

All new reporter fields are fixed enums/numbers; the wrapper handles only local
runtime metadata, passes no ambient credential variables and launches no model.
Tests use synthetic temporary
files and fake environment flags. No PII, usernames, paths, secret contents,
Issue prose or model logs are emitted. Future audit requires owner-approved
retention and protected ACLs. This is technical review, not 152-FZ legal acceptance.

## A1 / Issue #211: pinned transport qualification (2026-10-10)

Approved four-file implementation baseline:
`92aea397b4ecee449084d3a8e04ccce64c57004b`; dependencies #208/#210 merged.
No host provisioning, adapters or transport acceptance. Activation **NO-GO**.
The root SECURITY.md is absent; [SECURITY.md](SECURITY.md) is the relevant contract.
#207/#209's separate controller/publisher vs worker OS identities still apply.

### Feasibility research — STATIC

Reference Codex **0.162.0**, tag `rust-v0.162.0`, immutable source commit
`c1382380de69521303b416720a52f42d51af6248`. This does not attest the installed
Windows version. Later candidate review must bind actual artifact/version/hash,
source revision and effective policy; moving docs and caller pins are not authority.

| Mechanism | Documented/pinned behavior | Qualification consequence |
| --- | --- | --- |
| Browser / device-code sign-in | ChatGPT subscription access; device code beta depends on settings | Existing entitlement/settings owner-confirmed; no login/logout/auth changes in A1 |
| `file` | Auth cache contains credentials | Shell cache denial required; successful login is not isolation |
| `keyring` | OS keyring; source also supports encrypted local storage backed by keyring | Review actual backend, all cache locations, Credential Manager and process memory without reading stores |
| `auto` | File fallback on missing/failed keyring load or failed save | Cannot assume keyring-only custody; fallback cannot satisfy acceptance |
| `ephemeral` | Global process-memory auth map | Process/handle/debug/dump denial and refresh/restart remain unqualified |
| Legacy `unelevated` | Restricted token, deny-read overrides refused, weaker network isolation | Cannot satisfy the required denied-read/separate-identity gate |
| Legacy `elevated` | Dedicated users plus ACL/firewall/policy setup | Candidate only after approved concrete host provisioning; never setup in A1 |
| MXC | Native PSEC create/close probe; deny paths need native deny capability | OS build alone insufficient; reconcile real token/identity boundary with #209 |
| MXC selection | Preference may fall back to legacy; explicit MXC strict; no command-error fallback | Record effective backend; unreviewed fallback/drift closes gate |
| MXC environment/network | Helper uses prepared child environment; managed networking permits host loopback | Verify env/process/IPC and privileged loopback services independently |
| App-server | Client auth/events protocol; experimental WebSocket not production-supported | RPC is not separation; no token passthrough/unprotected listener/broker in A1 |
| WSL2/container | Alternative platform/tooling | No automatic proof; no credential mounts/OAuth copying; separate host scope |

Official sources reviewed 2026-10-10:
[Authentication](https://learn.chatgpt.com/docs/auth),
[Windows sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox),
[App-server](https://learn.chatgpt.com/docs/app-server).
Immutable source evidence:
[storage/fallback](https://github.com/openai/codex/blob/c1382380de69521303b416720a52f42d51af6248/codex-rs/login/src/auth/storage.rs),
[auth/refresh manager](https://github.com/openai/codex/blob/c1382380de69521303b416720a52f42d51af6248/codex-rs/login/src/auth/manager.rs),
[legacy deny-read](https://github.com/openai/codex/blob/c1382380de69521303b416720a52f42d51af6248/codex-rs/sandboxing/src/windows.rs),
[MXC selection/capability/limits](https://github.com/openai/codex/blob/c1382380de69521303b416720a52f42d51af6248/codex-rs/mxc-sandbox/README.md),
[MXC child environment](https://github.com/openai/codex/blob/c1382380de69521303b416720a52f42d51af6248/codex-rs/mxc-sandbox/src/windows.rs),
[payload scrub](https://github.com/openai/codex/blob/c1382380de69521303b416720a52f42d51af6248/codex-rs/mxc-sandbox/src/transport.rs),
[loopback policy](https://github.com/openai/codex/blob/c1382380de69521303b416720a52f42d51af6248/codex-rs/core/src/windows_sandbox.rs).
This review does not attest deployed binaries or all upstream native internals.
Protected model process / restricted command runner remains a candidate, not
accepted transport. The concrete gap remains missing witnessed host boundary;
no general impossibility claim is made.

### Offline metadata preflight

`transport-preflight.ps1` supports only `Report`. Without a candidate it reports
runtime metadata; candidate inspection requires all of `-CodexBinaryPath`,
`-ExpectedSha256`, `-ExpectedVersion`, supplied from an owner-protected artifact
record. No PATH lookup, execution, auth status, config/cache/log/store inspection,
network or evidence/activation input. Do not use the older `check-codex.ps1` for
A1: it invokes auth status and network. Never supply actual secrets, renamed
credentials or secret paths as binaries/pins; owner verifies artifact provenance.

Candidate inspection supports PowerShell 7 on Windows and local fixed drives.
It rejects wrappers, relative/UNC/device/ADS/glob/8.3 paths, reparse ancestors and
hardlinked files. Fixed in-memory C# checks final handle paths, keeps non-delete-
shared ancestor handles and a read-only file handle denying write/delete sharing,
and bounds executable hashing to 256 MiB. Numeric resource version only; missing
resources mean VERSION_UNAVAILABLE / version NOT_TESTED, never CLI execution as
fallback. Matching hash only compares caller-supplied pins, not trusted provenance.
Native handle behavior is **NOT TESTED** until exercised on Windows.

Bounded JSON always says NO_GO/DISABLED, with all isolation fields NOT_TESTED.
Every valid report exits **1**, including matching pins. Invalid/duplicate/unknown
arguments exit **2** with fixed INVALID_ARGUMENT; unavailable/inaccessible/unsafe
metadata yields fixed METADATA_UNAVAILABLE. No paths/SIDs/user/account IDs/raw
exceptions/arbitrary resource strings are emitted. Startup failure before the
script produces no accepted report: NOT TESTED / NO-GO.

Owner uses an already installed, separately pinned PowerShell and reviewed script
at absolute trusted paths, approved runtime directories and independently sanitized
environment; this reporter does not inspect or certify ambient environment.
Set process-local telemetry opt-out and update-check off **before** interpreter
startup. No policy bypass or machine/user environment change. CMD launch example
(replace placeholders locally; do not paste host values into GitHub):

```bat
cmd.exe /d /c "set POWERSHELL_TELEMETRY_OPTOUT=1&& set POWERSHELL_UPDATECHECK=Off&& <trusted-absolute-pwsh.exe> -NoLogo -NoProfile -NonInteractive -File <reviewed-absolute-transport-preflight.ps1> -Mode Report"
```

The script creates no persistent files; PowerShell can maintain startup caches,
so interpreter startup is not claimed write-free. Linux tests redirect caches to
disposable fixtures. Keep metadata reports local with owner-approved retention.

### Protected host acceptance checklist — future approvals only

All real values remain UNRESOLVED, in a protected owner record outside repo/Chat:

1. Bind actual binaries/hashes/provenance, OS build, effective backend, native
   capabilities, sanitized managed policy and digest. Review updates/fallback;
   upgrade or policy drift requires requalification. No raw configs/logs to model.
2. Bind separate controller/publisher and non-admin worker identities, restricted
   token/groups/privileges, process ancestry, session/job/desktop. MXC availability
   does not discharge the #209 separate-identity requirement.
3. Map credential custody/refresh/restart/revocation and file/key-store/process/
   environment/IPC channels. Model requests stay in the protected process; no
   credentials in shell arguments/environment/response fields/mounts.
4. Specify exact OS-enforced read/write paths, controller/root/ledger/audit/task
   protection and link-swap prevention. Workspace-wide writes plus post-hoc diff
   checks do not satisfy exact write-set confinement.
5. Specify allowed model/proxy endpoints and all other egress denies. Inventory
   loopback/private services; reject worker access to privileged RPC/auth/publisher,
   including descendants, IPv6, redirects and alternate listeners.
6. Independently confirm existing synthetic canaries, matching effective
   permissions and actual worker-token provenance. No tests on actual credential
   files or extraction from Credential Manager/memory/environment.
7. Present exact provisioning commands, expected changes, non-secret pre-change
   policy metadata, witness, rollback and retention before separate host approval.
   Scheduler stays absent/disabled; no unattended worker launch.

Future witnessed tests: credential-canary read denial; protected-canary write-only
denial; process handles/memory/debug/dumps, synthetic key-store/env/IPC boundaries;
exact write-set/link/race escapes; egress/loopback; descendants/cancellation.
Wrong/admin/owner token, missing/non-equivalent canary, incomplete check or pin
drift = NOT TESTED / NO-GO. Compatibility echo alone is not credential isolation.
Real model-through-protected-transport check needs separate functional-test
approval and reviewed bounded adapter; A1 never launches a real model/worker.

Protected evidence binds host/plan/binary/policy digests, token/canary provenance,
freshness/time/revocation and independent witness. Issue prose, workspace JSON,
flags and model reports cannot confer authority or upgrade evidence classes.

### Evidence, approvals and rollback

| Work | Class / limitation |
| --- | --- |
| Pinned sources and reporter analysis | STATIC |
| Linux PowerShell reporter, fake metadata/redaction/arguments | SYNTHETIC, not native enforcement |
| Windows native file-handle/link regressions | NOT TESTED in Cloud/Linux; SYNTHETIC even on Windows |
| Actual worker credential/process/env/IPC/network isolation | NOT TESTED; no LIVE-WITNESSED acceptance in A1 |
| Functional subscription transport | NOT TESTED; future separately approved gate |

Cloud can implement and exercise synthetic tests; missing PowerShell is an
explicit runtime skip, never success. Windows is mandatory for actual native
enforcement and independent host acceptance, which this delivery does not perform.

A1 changes no host state: no host rollback needed. Code revert after merge needs
owner approval. Future host rollback: revoke approvals, stop approved processes,
disable task, remove only enumerated new components, restore specifically changed
ACL/policy/firewall rules, verify disabled state. No recursive worker-derived
deletion or OAuth backup/export. Separate approvals remain required for concrete
provisioning, supervised Windows acceptance, functional model check, adapters,
merge and activation. No paid API/VPS/new subscription/OAuth-copy fallback.

Local Cloud evidence (2026-10-10): PowerShell 7.5.3 Linux reporter tests and
in-memory native-helper compilation passed with synthetic metadata. The complete
automation suite ran 84 tests, 3 Windows-only skips (junction, ACL regression,
new native handle/link checks). Existing acceptance tests used a disposable
Linux startup-cache launcher around the real interpreter; repository launchers
were not changed. n8n structural checks and two identical disabled dispatcher
dry-runs passed. No native Windows operation or actual worker isolation was
witnessed; all such host gates remain NOT TESTED / NO-GO.


## A2 / Issue #214 — non-activating offline handoff (2026-10-10)

The added `SyntheticControllerCore`, `SyntheticApprovalStore`,
`FakeWorkerAdapter`, and read-only offline `publisher.py` form an executable
**synthetic test harness**, not the separately privileged Windows controller,
restricted worker or trusted publisher. No new host paths, service identities,
ACLs, credentials, secrets, network endpoints, scheduler or executable model
transport are configured by this change. All concrete host values remain
UNRESOLVED and owner-protected outside this repository.

Testing new offline Python modules is allowed with a disposable synthetic
directory; it does not demonstrate native Windows ACL/token/process,
Credential Manager, isolated environment, IPC, loopback/network confinement,
exact OS write-set enforcement, exclusive stopped-worker Git snapshot, or
real GitHub write-publication ability. Mark them **NOT TESTED** until separately
approved real Windows witness checks. Do not bind a live owner approval root
to these synthetic components. Do not enable the old worker, Task Scheduler,
GitHub Merge, SAM-1, or any credential-bearing action.

After A2 is merged with exact post-merge CI success, rebaseline #209 and
propose a *separate* owner-approved concrete Windows host provisioning and
witnessed acceptance plan. SAM-1 #213 is an architecture decision only.

## A3 / Issue #216 — protected transport integration candidate (INACTIVE)

Implementation baseline: `cb5072aa39fb73a4cf3bae4cae4f10ee5773c2e3`;
A2 #214/#215 merged, post-merge CI #366 SUCCESS 8/8. #209 remains the host
security contract; #213 SAM-1 remains design-only. This section supersedes
older prospective Telegram/n8n notification requirements: **ChatGPT Tasks and
Master Chat only**, no second monitor. Code acceptance and host activation are
separate decisions. Nothing here provisions the owner computer.

### Transport decision first — STATIC research, Windows NOT TESTED

Public primary documentation rechecked on 2026-10-10:

- [Codex authentication](https://learn.chatgpt.com/docs/auth): existing ChatGPT
  sign-in is the first candidate, using subscription allowances. File/keyring/
  auto/ephemeral custody still needs the A1 pin and real boundary verification.
- [App-server auth lifecycle](https://learn.chatgpt.com/docs/app-server): managed
  ChatGPT browser/device-code sign-in is available. External-token mode is an
  experimental host-owned lifecycle; do not extract or repurpose the owner's
  existing OAuth. An RPC boundary alone is not a process/credential boundary.
- [SIWC plan usage](https://developers.openai.com/siwc/token-sharing-open-source):
  an optional mechanism for eligible open-source/local clients; account,
  registration, scopes and licensing eligibility are UNVERIFIED for Smart
  Garden. It is not permission to register a client or change authorization.
- [SIWC app-server](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server):
  the documented provider passes an access token in the child environment.
  Such an example fails our gate if model commands can inherit that environment
  or inspect the credential-bearing process. No token broker is implemented.
- [Windows sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox):
  MXC is a candidate on supported builds; a preference permits fallback,
  explicit MXC fails when unavailable. Legacy unelevated lacks denied-read
  paths and cannot meet #209 as a fallback. Elevated setup changes host
  users/ACL/firewall/policy and needs separate approval. MXC host-loopback
  access requires independent examination of privileged local services.

Reference source remains A1's Codex 0.162.0 / `rust-v0.162.0` /
`c1382380de69521303b416720a52f42d51af6248`. This is NOT the installed
Windows pin. Owner must supply actual artifact provenance, version, SHA256,
source commit, OS capabilities and effective backend through the protected
channel. Reuse unchanged `transport-preflight.ps1` for metadata-only checking;
never execute a binary merely to determine its version. Its pin cannot prove
authentication, backend selection or effective identity.

**Concrete blocker:** no witnessed installed transport binds a restricted
worker to denial of OAuth/GitHub caches, Credential Manager, inherited secrets,
controller/broker process handles/memory, IPC and network/loopback. Native
Windows cannot be inspected in this Linux Cloud environment. Status is
**NOT TESTED / NO-GO**, not a claim that all supported transports are impossible.
The implemented adapter is FAKE_ONLY. No real Codex/model launch, account
login, credential transport or GitHub write is part of A3.

### Reviewable two-principal host matrix — owner values UNRESOLVED

The protected controller/publisher principal and non-admin worker principal
must be different; the independent owner signer/trust root is outside both
worker reach and repository control. Splitting publisher into a third
principal is a later least-privilege option, not assumed provisioned here.

| Boundary | Protected controller / publisher | Restricted worker | Witness required |
| --- | --- | --- | --- |
| Pinned runtime, controller and public roots | Controlled read/execute; owner-only updates | No modification, no protected-profile access | Actual effective token and matching canaries |
| Approval / nonce / revocation / state / audit / global lock | Read/atomic write; out of repo | No write, rename, delete or directory-create | Seven scoped write/read canaries plus directory rights |
| Owner signing key | Independent signer custody only | No access | Owner-controlled trust root; never an exported key |
| OAuth auth process / caches / refresh | Only approved transport identity | No read/write/handles/debug/dumps | Synthetic markers, never authentic credential content |
| GitHub publisher credentials | Approved publisher identity only | No read/env/key-store/process access | Credential Manager test with a disposable synthetic entry |
| Workspace and Git objects | Stopped-worker exclusive read snapshot | Exact approved file writes only; no privileged Git metadata | OS write-set / links / untracked / refs / race checks |
| IPC and loopback | Narrow authenticated command-independent interface | No privileged control endpoint | Named-pipe/socket impersonation and authorization negatives |
| Network | Narrow approved model/GitHub endpoints by intended process | No arbitrary exfiltration or local privileged services | Synthetic marker sink, egress and loopback denial |
| Scheduler | Absent/disabled | No install/enable | Protected status; no task created by A3 |

### Command-by-command proposal: NOT AUTHORIZED, NOT RUN

Before approving any host changes, owner fills a protected deployment manifest
with concrete SIDs, actual absolute paths, hashes, effective permissions,
endpoint policy, source/build and rollback targets. Do not put these values,
ACL exports, usernames or local reports in GitHub. The steps below are a
reviewable proposal using symbolic variables, not a deployable unattended script.
Missing values/capabilities or a vendor backend failing #209 => STOP; no fallback.

1. **Metadata only, no model execution:** privately inspect OS version,
   installed artifact metadata and `transport-preflight.ps1` with exact
   `-CodexBinaryPath`, `-ExpectedSha256`, `-ExpectedVersion`. Record only its
   sanitized fixed statuses publicly. No `login status`, auth/config store
   dumps, account/read refresh, environment dumps or process-memory reads.
2. **Approval of concrete provisioning separately:** owner reviews account
   selection, controller/interpreter placement, ACL changes, credential
   process custody and firewall/IPC changes for the chosen backend. Existing
   accounts may be selected only when their separation is proven. For legacy
   elevated sandbox the vendor proposal is `codex sandbox setup --elevated
   --user <approved-identity> --codex-home <approved-private-location>`;
   it reads configuration and changes host state, so it MUST NOT run in A3.
   MXC compatibility/startup commands also launch real processes and are
   deferred to the separately approved witnessed session.
3. **Snapshot specifically approved ACL metadata privately:** proposed owner
   command `icacls $ApprovedControllerRoot /save $PrivateAclBackup /t /c`.
   Obtain backup success and restoration mapping before any change. This
   metadata is sensitive host information, never upload it.
4. **Protect the resolved controller tree:** proposed, separately approved
   command `icacls $ApprovedControllerRoot /inheritance:r /grant:r
   "$($ApprovedControllerSid):(OI)(CI)F" "$($ApprovedOwnerSid):(OI)(CI)F"`.
   Owner must inspect/remove any pre-existing grants permitting worker access
   and verify effective rights, ancestors, replacement/delete-child rights,
   lock location and interpreter custody. This template alone is NOT an
   effective-ACL proof and is not applied recursively to arbitrary paths.
5. **Workspace confinement / process / IPC / network:** use only the reviewed
   vendor backend and a protected manifest. Deny reads of protected profiles;
   allow writes only to exact approved files and fixed disposable scratch
   paths. Pin the approved effective backend and disable unreviewed fallback.
   Record exact native provisioning commands for the selected installed
   backend before approval; none can be inferred safely from Cloud mocks.
6. **Owner provisions synthetic canaries privately:** use pre-existing,
   disposable marker files with independently witnessed existence and the
   SAME effective ACL as the tested assets. No authentic secret file path
   may be passed to `probe-isolation.ps1`. Preserve positive controls and
   metadata proof outside the worker; do not create a readable token canary
   beside a differently protected real cache and claim equivalence.
7. **Run sanitized open-only probe under actual worker identity:**
   `pwsh -NoProfile -NonInteractive -File <approved-probe-copy>
   -ExpectedWorkerSid <approved-worker-SID> -OAuthCanary <synthetic-file>
   -GitCanary <synthetic-file> -RegistryCanary <synthetic-file>
   -ControllerCanary <synthetic-file> -RootCanary <synthetic-file>
   -StateCanary <synthetic-file> -AuditCanary <synthetic-file>`.
   Missing arguments/paths, aliases, wrong/admin identity, inaccessible
   metadata, hardlink or race ambiguity => NOT TESTED. Read-only failure
   cannot substitute for a write-only open. The script transfers no file
   content and ALWAYS returns NO_GO; it cannot attest Credential Manager,
   process, environment, IPC, network or complete directory permissions.
8. **Independent witnessed native tests:** after separate host approval,
   owner tests synthetic Credential Manager/env/process/IPC/network markers,
   refresh/restart/backend drift, exact write confinement, hardlink/junction
   substitution and stopped-worker exclusive snapshot. Do not test denial
   by reading actual credentials or memory of real credential processes.
   Each result binds source/pin/token/policy/canary provenance and witness;
   Linux results remain SYNTHETIC regardless of passing count.
9. **Scheduler and live publication remain disabled:** host acceptance does
   not grant model execution, push/PR/merge, ruleset changes or SAM activation.
   Each requires its own concrete permission and reviewed live adapter.

### Rollback proposal and owner approvals

No host rollback is needed for A3 because it changes no host state. For the
later plan: revoke delivery first; stop only approved execution processes;
leave/remove any newly approved task disabled; preserve ledger/reservations
for reconciliation; restore only explicitly changed ACLs via the privately
verified `icacls <mapped-parent> /restore $PrivateAclBackup` mapping; undo
only listed firewall/IPC changes; remove only newly created approved canaries
and accounts after data ownership is reconciled. Never reset consumed nonces,
remove a lock to defeat a running process, restore/export OAuth caches, or
recursively delete a worker-supplied path. Vendor-created components need a
reviewed vendor rollback; no undocumented uninstall command is assumed.
Verify denied activation, protected state custody and main integrity after
rollback. Reverting a code PR is a separate owner decision, not auto-recovery.

Required owner approvals, separately: exact host manifest/provisioning and
rollback; synthetic witnessed session; later bounded live worker pilot;
read-only-to-write publisher transition; trusted check providers/ruleset;
SAM-1 activation. The PR merge itself requires an explicit PR/HEAD decision.

### ChatGPT notification and approval workflow

Use the existing hourly **Smart Garden — PR и подтверждения** read-only
ChatGPT Task. A3 neither creates nor reconfigures it. No Telegram bot,
n8n alert flow or unofficial ChatGPT messaging API is required.

After PR + exact-HEAD CI 8/8 + independent Codex Security Review, the existing
Task may notify on meaningful new readiness/blocker changes. Notification
delivery depends on the owner's ChatGPT settings. Master Chat presents the
PR URL, full HEAD SHA, CI/review links and remaining risks, and requests:
`Разрешаю merge PR #N при HEAD <40-character SHA>`.
The human-authorized chat action rechecks main/head/review/checks before
merge; checks actual merge SHA and all eight post-merge jobs afterward.
No next Issue starts before that gate. A button is optional only with an
official authenticated callback that binds identity, PR/HEAD and authority;
no such integration is implemented or presumed. Tasks, comments, labels and
model text never supply the autonomous publisher's cryptographic approval.

For a switched-off PC, existing manually delegated Codex Cloud work can
continue in `smart-garden`; local scheduled Git tasks need the host/app running
([official scheduled tasks](https://learn.chatgpt.com/docs/automations)). An
hourly observer does not dispatch a new authenticated coding task. A supported
always-available dispatch/execution path, protected custody and usage limits
remain unimplemented; no paid API/VPS/OAuth-to-Actions fallback is allowed.

### Evidence and next gated handoff

| Result | Evidence class | Limit |
| --- | --- | --- |
| Supported subscription / backend documentation and A1 source reference | STATIC | No installed Windows identity or auth is attested |
| Signed fixture collector, atomic delivery ledger, finite fake work, raw loose Git object hashing | SYNTHETIC | Offline disposable data only; never GO |
| Real GitHub authenticated collector/check providers, packed-object publication, OS-exclusive snapshot | NOT TESTED | No live adapter or privileged action exists |
| Windows token/ACL/key-store/env/process/IPC/network/refresh isolation | NOT TESTED | No LIVE-WITNESSED evidence in Cloud |
| Windows provisioning, execution, scheduler, publisher write, SAM-1 auto-merge | NO-GO | Separate approvals and accepted adapters required |

Next owner step after code review is explicit merge approval for this exact PR
HEAD. After post-merge CI 8/8, provide the resolved host manifest through the
protected owner channel for a separate witnessed acceptance decision. Future
SAM-1 still needs semantic NORMAL/SENSITIVE classification, trusted App-bound
checks, ruleset acceptance and a durable single-use merge permit with HEAD/base/
revocation race guarantees; no synthetic status or Codex comment substitutes.
