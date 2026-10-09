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

`pwsh -NoProfile -NonInteractive -File automation/windows/acceptance.ps1`
prints a fixed STATIC/NO_GO report and deliberately exits **1**. It reads no
credentials, host configs, arbitrary evidence or Issue text; creates no files;
changes no ACL/accounts/tasks; launches no model/publisher. Report repetition
is deterministic. Unknown modes/arguments fail. This is a readiness reporter,
not a witnessed isolation test or activation certificate. Existing
`probe-isolation.ps1` remains the separate canary test requiring real worker SID.

## Rollback and privacy

This PR performs no host provisioning, so there are no host changes to undo.
For a later host plan, owner records pre-change ACL/policy metadata and owns
rollback: revoke approval first, stop execution, disable task, remove only newly
approved components, restore specifically changed ACL/rules, verify disabled
status. Never recursively remove a path computed from worker text.

All new reporter fields are fixed enums/numbers; tests use synthetic temporary
files and fake environment flags. No PII, usernames, paths, secret contents,
Issue prose or model logs are emitted. Future audit requires owner-approved
retention and protected ACLs. This is technical review, not 152-FZ legal acceptance.
