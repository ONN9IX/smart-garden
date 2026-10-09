# Smart Garden — current no-VPS coordinator (GitHub Actions only)

**CURRENT CHOICE (2026-10-08): no VPS, no credit card, no autonomous code execution.**
The free GitHub-hosted, read-only queue/CI observer is defined in
[NO-VPS.md](NO-VPS.md) and `.github/workflows/automation-observer.yml`.
For an already-installed Windows Codex CLI, see [CODEX-CLOUD.md](CODEX-CLOUD.md)
for read-only PC diagnostics and one-time Codex Cloud setup. Installing Codex
locally does not automatically enable Cloud or start approved Issues.
It runs on PR #205 to verify GitHub integration and, **only after human-reviewed
merge to main**, hourly via GitHub `schedule` on the default branch.
It has **no merge/commit/AI-execution capability** and requires no paid OpenAI API.

**Security remediation (PR #205):** the legacy executor is retired in code, not
merely disabled by an environment flag. Issue metadata never authorizes execution;
`START_ENABLED=true` is ignored; model/branch/publication helpers reject direct calls.
Compose has no OAuth volume and the worker image installs no Codex CLI.
The execution allowlist is empty. Future execution requires a separately reviewed
owner-controlled approval mechanism, credential broker/isolation and audited file
allowlist. The historical deployment/login/activation commands below are obsolete
and must not be followed. This does not change the existing Codex Cloud environment.

The sections below document the **legacy OPTIONAL self-hosted n8n/Codex candidate**;
they are NOT deployed and NOT the selected configuration. Do not procure
Hetzner/Oracle or set `START_ENABLED=true` under this no-VPS decision.

---

# Smart Garden — bounded autonomous development (deployment candidate)

**Status:** configuration and offline policy tests only; **NOT deployed or authorized to start**.
No existing PR, production deployment, 152-FZ data, or ChatGPT credential is changed by this directory.

## Free, arm64 self-hosted option (Oracle Cloud Always Free)

For **no additional VPS subscription** and a computer that may be switched off,
see [`deploy/oracle-always-free.md`](deploy/oracle-always-free.md).
The conservative verified target is **VM.Standard.A1.Flex (2 OCPU, 12 GB RAM, 100 GB
boot volume, Ubuntu 24.04 ARM64)**, within the tenancy's combined Always Free
compute/storage limits **if the OCI console explicitly shows eligibility**.
Run `python3 automation/deploy/oracle-a1-preflight.py` on the new VM **before**
installing Docker. There is **no automatic account sign-up, provisioning or
paid fallback**; Oracle account creation, billing eligibility and SSH-key
management require the owner. The Linux preflight cannot validate OCI billing.
The existing Docker Compose design is architecture-neutral; upstream n8n and
Codex publish ARM64 distributions, but full on-host Docker/Codex login smoke
is still required. See the runbook for SSH-only UI access and cost safeguards.

## Architecture

```text
Master Chat freezes scope → owner-written GitHub Issue (ai:ready, owner-only,
 BASE-SHA, explicit WRITE-SET, AUTOMATION-AUTHORIZED: YES)
      ↓
Private n8n Schedule Trigger (10 min) → authenticated HTTP /tick
      ↓
Worker policy gate (one job at a time, no conflicting open PRs,
 base SHA equal main, exact paths, frozen stages excluded)
      ↓
Isolated Linux agent UID 10001 runs Codex CLI, ChatGPT Plus device-code login,
 workspace-write sandbox; root-only Git metadata and no GitHub PAT in Codex child environment
      ↓
Coordinator independently inspects git changes and only commits allowlisted files
      ↓
New branch + ordinary PR → existing required PR CI (8 baseline checks)
      ↓
n8n Telegram notification → owner reviews PR and explicitly decides merge
```

The **worker intentionally has no merge endpoint**. This first release has no automatic
repair loop: CI failure alerts and stops; fix in the same branch by the normal Master Chat/
Work review process. Changes to migrations, auth/RBAC, security, privacy, shared files,
contracts or future stages always go through separately approved Master Chat delivery.
The n8n import is **disabled by default**; `START_ENABLED=false` independently prevents
new development even when the workflow is accidentally activated.

### State machine and failure behavior

| State | Behavior |
|---|---|
| PAUSED | No approved execution while `START_ENABLED=false`. `/healthz` works. |
| BLOCKED | Missing authorization, incorrect baseline/write-set, overlapping PR, changed main or crash. Do not bypass automatically. |
| RUNNING | Maximum one Issue globally and one bounded Codex call per Issue. |
| PR_PENDING | Commit and PR created, existing GitHub Actions checks observed on later ticks. |
| CI_PASSED | Required checks passed; Telegram sends PR link, **human review required**. |
| CI_FAILED | Automatic execution stops; no merge or unsupervised repair. |

A changed Issue does not silently rerun; state is persisted on disk. For an approved
retry, inspect the previous result, explicitly reconcile the branch/PR and reset state
under human control. Never delete state while a job is running. Never create another
PR for a correction that belongs on the existing delivery branch.

## Required one-time human actions (deferred until deployment)

1. **Dedicated Linux host/VPS:** target Hetzner CX33 (4 vCPU, 8 GB RAM,
   80 GB NVMe), Germany (Falkenstein/Nuremberg), Ubuntu 24.04 LTS x86_64,
   public IPv4 and SSH-key access. Check availability and exact billing before
   purchase. OpenAI access must originate from a supported country; **do not
   use a Russian VPS for the Codex worker**. This is synthetic-only development
   automation, not the production data host for real children/parents.
   Install Docker Engine/Compose, allow outbound HTTPS and SSH.
   Keep host updated, use SSH keys, firewall and disk encryption. A dedicated host/VM is
   preferable to sharing the Smart Garden production server. No domain is required for
   the outbound-only pilot. The n8n UI listens on `127.0.0.1:5678`; access it with
   `ssh -L 5678:127.0.0.1:5678 user@host` (or approved HTTPS reverse proxy).
2. **GitHub fine-grained PAT** restricted to `ONN9IX/smart-garden`, with Contents RW,
   Pull requests RW, Issues R, Checks R and metadata access. Never send it in ChatGPT,
   GitHub Issues or n8n workflow exports. Put it in `automation/secrets/github_token`
   with Linux owner root and `chmod 600` (not in Git). The app refuses to boot if it is
   readable by another UID. Use a short expiration and rotate regularly.
3. **ChatGPT Plus login** after first container startup:
   `sudo docker compose exec -u 10001 codex-worker codex login --device-auth`.
   Complete the one-time code in the browser **yourself**. Device-code sign-in may need
   enabling in ChatGPT account settings. Check with
   `sudo docker compose exec -u 10001 codex-worker codex login status`.
   The OAuth cache is retained in isolated Docker volume `codex_home`, never in GitHub.
   Keep the one-time code, passwords, token files and OAuth cache out of chat.
   Account usage remains subject to Codex plan limits; no separate OpenAI API key.
4. **Telegram**: create a bot with BotFather, record bot token privately, send `/start`
   to it and obtain the private chat ID. Configure Telegram credentials in n8n and set
   the chat ID on `Telegram notification`. The bot only sends notifications in this
   version; **it cannot authorize merge**. Do not share the bot token in chat.
5. **n8n**: import `n8n/smart-garden-dispatcher.json`, set `HTTP Header Auth` credential
   (header name `X-Worker-Key`, value of `secrets/worker_key`) in both HTTP nodes,
   Telegram credential in the Telegram node and the private chat ID. Keep disabled
   until read-only integration verification is successful. Credentials remain local
   and are not embedded in exported JSON.
6. **Explicit owner approval**: use a specific GitHub Issue with contract and frozen
   scope, create repository label `ai:ready`, then attach it to that Issue. Do not
   label #175 or an existing PR. `START_ENABLED` must first be set to `true` and the
   worker container restarted **only after the initial manual dry run**.

There is no way to complete actions 1–5 solely by committing repository code: they
require a real server, account authorization and secret provisioning.

## Deployment from the repository (no credentials in Git)

After this infrastructure PR is independently reviewed and merged, create the
VPS and use a non-root operator account with SSH-key access. From the VPS:

```bash
git clone --depth 1 https://github.com/ONN9IX/smart-garden.git
sudo bash smart-garden/automation/deploy/bootstrap-ubuntu.sh
cd smart-garden/automation
bash deploy/init-secrets.sh
```

This host bootstrap installs Docker but does not change SSH/firewall settings,
create a GitHub access token or run Codex. Configure the provider firewall to
allow SSH **only from your own IP**. n8n listens on localhost; access its UI via
SSH forwarding, not an open Internet port. Docker grants root-equivalent host
access, so use `sudo docker compose` rather than putting an untrusted account
in the Docker group. Keep encrypted off-host backups.

From the approved version of `main`:

```bash
cd automation
# The .env and worker_key already exist from deploy/init-secrets.sh; inspect them.
ls -l .env secrets/worker_key
# Place the GitHub PAT through your own secure password-manager/console flow;
# do not paste it into chat, workflow JSON, or a shell command's history.
# Required: root-owned secrets/github_token with mode 600.
umask 077
chmod 600 secrets/worker_key secrets/github_token
# Image versions are pinned, and N8N_ENCRYPTION_KEY was generated locally.
sudo docker compose config --quiet
sudo docker compose build codex-worker
sudo docker compose up -d
curl -fsS http://127.0.0.1:5678/healthz || true  # n8n path varies by version
# Probe worker on the private Compose network, without exposing it to the host:
sudo docker compose exec n8n node -e 'require("http").get("http://codex-worker:8080/healthz",r=>{console.log(r.statusCode);r.resume()})'
```

**Important:** `docker compose up` cannot authenticate a ChatGPT account. The
`codex login` command above is required separately. Do not set `START_ENABLED=true`
in `.env` until validation and an explicit approval decision.

Pinned deployment candidates as of 2026-10-08: n8n `2.41.7` (stable channel)
and Codex CLI `0.161.0` (npm stable). Recheck release safety and on-host
compatibility before activation; updates require a reviewed change, not `latest`.

## Issue authorization contract (exact syntax)

```text
Title: <small, isolated scope that does not change frozen design>

AUTOMATION-AUTHORIZED: YES
PARALLEL-SAFE: NO
BASE-SHA: <exact current 40-char main SHA>
WRITE-SET:
- frontend/src/app/example/page.tsx
- frontend/src/components/example.tsx

Goal: ...
Acceptance criteria: ...
Privacy/test criteria: synthetic only ...
```

`WRITE-SET` contains **exact relative file paths**, no directories, wildcards,
renames or 152-FZ-sensitive materials. It is capped at 30 files. The owner-authored
Issue must be **open** and carry `ai:ready`. Current `main` SHA must match exactly;
**any open PR to main blocks the next automated delivery**, including PR #196.
A stale Issue is rejected; it is not auto-rebased or silently implemented against
another contract. Put no passwords, child records, passport numbers, or other real
personal data in Issues or prompts.

## Preflight and recovery

- **Read-only smoke:** with `START_ENABLED=false`, run n8n workflow manually after
  configuring credentials. `/tick` returns `enabled=false`, no code execution or
  repository write. Verify no PR or branch was created.
- **First write pilot:** after #196 has finished, use one small Master Chat-approved
  Issue with synthetic-only frontend scope and exact main SHA. Verify single PR,
  write-set enforcement, existing CI, Telegram notification and no automatic merge.
- **Errors:** `sudo docker compose logs --tail 50 codex-worker`; logs deliberately omit
  Codex transcripts, HTTP payloads and secrets. Review event messages in Telegram,
  then inspect the Issue/PR in GitHub. Before any retry, verify no orphaned branch/PR.
- **Stop switch:** set `START_ENABLED=false`, then
  `sudo docker compose up -d --no-deps --force-recreate codex-worker`. This prevents new
  work but does **not** interrupt a job already running; if urgent, stop the worker
  container and inspect the workspace before resuming.
- **Backups:** back up n8n data and the worker state with encryption. OAuth cache and
  token files must be secured separately, never committed and never shared publicly.
- **Security:** no Docker socket mount; worker port unpublished; no production
  database; untrusted Issues cannot override owner/freeze/path/baseline policy.
  Worker design reduces risk but requires host hardening and an on-host smoke test.

## Change documentation discipline

- One completed major block → one meaningful Git commit and one delivery PR.
- No commits per small edit and no new PR per review correction.
- Update `docs/CURRENT_STATE.md` **only on cardinal changes** in architecture,
  product contracts, schema, RBAC/privacy or stage/gate status; ordinary fixes remain
  visible in Git/PR. This delivery does not change `CURRENT_STATE.md`.

## Acceptance checklist before calling the system "running"

- [ ] Dedicated host installed/hardened; images pinned, backups and firewall checked
- [ ] Secrets owner-only, worker refuses permissive token permissions
- [ ] Codex CLI device login and plan quota verified on that host
- [ ] n8n import successfully executes read-only `/tick` with START_ENABLED=false
- [ ] Telegram private chat receives synthetic test event; credentials not exported
- [ ] Existing #196 cleared; scoped small approval Issue created with exact SHA
- [ ] Pilot generated only approved files/one PR, CI completed, no auto-merge
- [ ] Explicit owner authorization given for `START_ENABLED=true`

## Windows dispatcher candidate — Issue #207

See [Windows security boundary and candidate commands](windows/SECURITY.md).
This delivery adds an offline controller core and negative-test harness; activation
remains **NO-GO**. It does not revive the retired worker or authorize the historical
installation/activation checklist above. Task Scheduler XML is disabled, runs at
two-hour cadence, and requires separate owner host approval before installation.
No worker, OAuth transport or publisher is installed. Live credential-isolation
acceptance remains untested; Python dry-run does not imply working autonomy.
