#!/usr/bin/env bash
# Bootstrap an otherwise empty Ubuntu 24.04 VPS for private Smart Garden automation.
# Installs Docker Engine/Compose from Docker's apt repository. It deliberately
# does NOT start Codex, request secrets, modify SSH, or enable autonomous work.
set -Eeuo pipefail
if [[ "$(id -u)" != 0 ]]; then
  echo "Run with sudo bash automation/deploy/bootstrap-ubuntu.sh" >&2
  exit 1
fi
. /etc/os-release
if [[ "${ID:-}" != 'ubuntu' || "${VERSION_ID:-}" != '24.04' ]]; then
  echo 'Ubuntu 24.04 LTS is required; no changes made.' >&2
  exit 1
fi
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git openssl gnupg python3
install -m 0755 -d /etc/apt/keyrings
curl --fail --silent --show-error --location https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu %s stable\n' \
  "$(dpkg --print-architecture)" "${VERSION_CODENAME}" > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
printf '\nDocker: '; docker --version
printf 'Compose: '; docker compose version
printf '\nBootstrap complete. Autonomous execution is still OFF.\n'
printf 'Next: configure owner-held credentials using automation/README.md.\n'
printf 'Keep n8n bound to 127.0.0.1; use SSH port forwarding for its UI.\n'
