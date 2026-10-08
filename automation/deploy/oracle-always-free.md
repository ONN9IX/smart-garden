# Oracle Cloud Always Free — ARM64 deployment runbook (2026-10-08)

**Scope:** a stand-alone automation **development** host for Smart Garden using **synthetic-only** data. This does not host kindergarten production or identifiable children/parent records and does not establish Russian 152-FZ compliance. **This is a deployment plan, not a provisioned server.**

## Price ceiling and prerequisites

Authoritative [Oracle Always Free documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm): Always Free compute must run in the account's **home region**; shared allocation is **2 Ampere A1 OCPUs + 12 GB RAM** (1,500 OCPU-hours + 9,000 GB-hours per month); all Always Free boot and block volumes together <= **200 GB**. Availability is not guaranteed. The 100 GB boot-volume choice below leaves room in the free storage allowance for other uses, but *check all existing tenancy resources first*. ARM A1 idle VMs may be reclaimed. Oracle does not provide a free-tier uptime SLA.

**Account owner only (cannot be automated without identity/payment verification):**

1. Sign up at <https://www.oracle.com/cloud/free/>. Payment-card verification may impose a temporary authorization hold. Do **not** upgrade to Pay As You Go and do not intentionally enable paid services or trial-credit-paid resources. Oracle chooses / offers a **home region** during account creation; pick **Germany Central (Frankfurt)** only if available and suitable, otherwise a supported EU home region **before finishing sign-up**. Home region cannot simply be changed later. Account eligibility and A1 capacity vary; do not presume capacity.
2. In OCI Console, `Compute` → `Instances` → `Create instance`. Region must equal the tenancy home region. Choose **Ubuntu 24.04 ARM64** from an `Always Free Eligible` image and **VM.Standard.A1.Flex** shape explicitly tagged `Always Free-eligible`. Set **2 OCPU, 12 GB RAM** (not 4/24); select **100 GB boot volume** (not paid NVMe/block tiers). Do not create other VMs consuming these shared limits. Use one default VCN/public subnet + ephemeral public IPv4 if marked free. No load balancer, NAT Gateway, Autonomous DB, paid backup schedule, Reserved public IP or extra paid services. Confirm **estimated cost: 0** and Always Free labels before create; abort if the console shows chargeable items. An `out of host capacity` error means **stop** or try another availability domain inside the *same* home region, never switch to a paid shape.
3. Configure an **SSH public key** in the OCI instance wizard. The **private key remains on your computer**; never paste it, your password, OTP, card, ChatGPT authentication or GitHub token into any issue, chat, log or repository. Restrict inbound security-list/firewall to SSH TCP/22 from your own IP if available. **Do not expose 5678 (n8n) or 8080 (worker) publicly**. Record the VM public IP and the OCI instance's `Always Free` label; sharing just the IP is enough for guided follow-up.
4. No automatic paid fallback. Stay on Always Free even if capacity is temporarily unavailable. Never run synthetic load to evade Oracle idle-reclamation rules.

## Post-creation on the VM (owner-operated terminal)

SSH from your local machine, using the key you created:

```bash
ssh -i ~/.ssh/smart-garden-oracle ubuntu@YOUR_ORACLE_PUBLIC_IP
```

After the infrastructure PR #205 has been reviewed and **merged by an explicit Master Chat decision** (until then use only the approved PR branch in an isolated validation environment), run:

```bash
sudo apt-get update && sudo apt-get install -y git python3
sudo mkdir -p /opt/smart-garden && sudo chown "$USER":"$USER" /opt/smart-garden
cd /opt/smart-garden
git clone https://github.com/ONN9IX/smart-garden.git
cd smart-garden
python3 automation/deploy/oracle-a1-preflight.py
sudo bash automation/deploy/bootstrap-ubuntu.sh
sudo bash automation/deploy/init-secrets.sh
```

**Expected preflight:** `PASS` with ARM64/aarch64, Ubuntu 24.04, 2 CPUs, ~12 GB RAM and ~100 GB root volume. This validates only Linux resources, **not** Oracle chargeability. Check Oracle Console separately.

Set the GitHub **fine-grained repository-scoped** token using a root-owned local file only (do not enter it as a CLI argument or expose it in logs); then follow `automation/README.md` for Codex ChatGPT Plus `device-auth` login and Telegram credential assignment. Tokens are **never** sent into ChatGPT. Avoid typing tokens in shared terminal recordings. Prepare a secure local backup of n8n configuration/state; free instances can be reclaimed without an uptime guarantee.

With `START_ENABLED=false`, after tokens are in place:

```bash
cd /opt/smart-garden/smart-garden/automation
sudo docker compose config --quiet
sudo docker compose build codex-worker
sudo docker compose up -d
sudo docker compose ps
sudo docker compose exec -u 10001 codex-worker codex --version
```

Access private n8n UI only through an SSH tunnel on your local machine:

```bash
ssh -i ~/.ssh/smart-garden-oracle -L 5678:127.0.0.1:5678 ubuntu@YOUR_ORACLE_PUBLIC_IP
```

Open <http://localhost:5678> in the browser. n8n workflows remain disabled, worker START_ENABLED remains false. Import `automation/n8n/smart-garden-dispatcher.json` and bind credentials locally; validate read-only mode before granting any workflow execution. Existing PR #196 must be resolved and Master Chat must approve a small synthetic-only Issue before enabling the worker.

## Operational guardrails

- No API billing: Codex CLI `codex login --device-auth` uses the owner's ChatGPT Plus entitlements, subject to usage limits. If exhausted, pause; do not add a paid API key or enable purchased credits.
- During the pilot **GitHub Actions** performs full backend/frontend/PostgreSQL CI on GitHub; do not run full-stack browser CI concurrently on this small ARM VM.
- Never relax no-merge, exact BASE-SHA, WRITE-SET, owner and CI gates. n8n + worker are separate processes, there is one development job at a time.
- Keep Docker/n8n/Codex versions pinned and security-updated after testing; ARM support is evidenced by upstream multiarch packages but **actual image startup on Oracle A1 has not yet been validated**.
- If credentials leak, revoke/rotate at the provider. If the instance is reclaimed, restore from protected backups; do not assume guaranteed 24/7 availability.
- **Cost safeguard:** visit OCI `Billing & Cost Management` regularly, enable available budget alerts (alerts do not hard-stop charges), and periodically verify your resources remain tagged Always Free. Free-trial credits may mask paid resources; do not mistake a zero bill during trial for Always Free eligibility.

## Sources

- <https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm>
- <https://docs.oracle.com/en-us/iaas/Content/GSG/Tasks/signingup_topic-Sign_Up_for_Free_Oracle_Cloud_Promotion.htm>
- <https://www.npmjs.com/package/@openai/codex?activeTab=versions> (Linux ARM64 package)
- <https://hub.docker.com/r/n8nio/n8n/tags> (linux/arm64 manifests)
