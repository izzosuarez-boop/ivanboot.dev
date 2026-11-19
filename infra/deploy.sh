#!/usr/bin/env bash
# Deploy the stack to the VPS. Run from Git Bash:  bash infra/deploy.sh
# Requires the "portafolio" host alias in ~/.ssh/config (or DEPLOY_HOST=user@ip).
set -euo pipefail

HOST="${DEPLOY_HOST:-portafolio}"
DIR=/opt/ivanboot
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(date -u +%Y%m%d-%H%M%S)"
cd "$ROOT"

echo "==> uploading source ($VERSION) to $HOST:$DIR"
# Replace apps/ and infra/ wholesale so files deleted locally disappear on the server too.
# .env and Docker volumes (TLS certificates) are untouched.
tar --exclude=node_modules --exclude=.next --exclude=__pycache__ --exclude='.env*' -czf - apps infra \
  | ssh "$HOST" "mkdir -p $DIR && rm -rf $DIR/apps $DIR/infra && tar -xzf - -C $DIR"

echo "==> syncing .env (mode 600)"
scp -q .env "$HOST:$DIR/.env"
ssh "$HOST" "chmod 600 $DIR/.env"

echo "==> building and starting containers"
ssh "$HOST" "cd $DIR && APP_VERSION=$VERSION docker compose -f infra/docker-compose.yml up -d --build --remove-orphans && docker image prune -f >/dev/null && docker compose -f infra/docker-compose.yml ps"

echo "==> smoke test"
sleep 5
for url in https://ivanboot.dev https://tienda.ivanboot.dev https://api.ivanboot.dev/health; do
  printf '%-36s %s\n' "$url" "$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$url" || echo FAIL)"
done
