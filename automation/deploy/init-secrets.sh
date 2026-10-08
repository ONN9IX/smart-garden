#!/usr/bin/env bash
# Initialize local-only credentials; never overwrite an existing key or PAT.
# No network access or GitHub/ChatGPT account login is performed.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
umask 077
if [[ -e .env ]]; then
  echo 'Refusing to overwrite existing automation/.env' >&2
  exit 1
fi
if [[ -e secrets/worker_key || -e secrets/github_token ]]; then
  echo 'Existing credentials found; manually inspect before proceeding.' >&2
  exit 1
fi
command -v openssl >/dev/null || { echo 'openssl required' >&2; exit 1; }
install -d -m 0700 secrets
cp .env.example .env
chmod 0600 .env
key="$(openssl rand -hex 32)"
python3 - "$key" <<'PY'
import pathlib, sys
p = pathlib.Path('.env')
s = p.read_text()
s = s.replace('REPLACE_WITH_RANDOM_32_BYTE_OR_LONGER_KEY', sys.argv[1])
assert 'REPLACE_WITH_RANDOM' not in s
p.write_text(s)
PY
openssl rand -hex 32 > secrets/worker_key
chmod 0600 secrets/worker_key
printf '%s\n' 'Local n8n/worker keys created. No GitHub token or ChatGPT authentication was provisioned.'
printf '%s\n' 'START_ENABLED=false; DO NOT enable until owner-approved isolated pilot.'
