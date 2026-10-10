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
