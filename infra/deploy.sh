#!/usr/bin/env bash
# Deploy the stack to the VPS. Run from Git Bash:  bash infra/deploy.sh [service ...]
#   bash infra/deploy.sh        # rebuild everything
#   bash infra/deploy.sh api    # rebuild only the API (the web container keeps running its current image)
# Requires the "portafolio" host alias in ~/.ssh/config (or DEPLOY_HOST=user@ip).
set -euo pipefail

HOST="${DEPLOY_HOST:-portafolio}"
DIR=/opt/ivanboot
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(date -u +%Y%m%d-%H%M%S)"
SERVICES="$*"
cd "$ROOT"

echo "==> uploading source ($VERSION) to $HOST:$DIR"
# Replace apps/ and infra/ wholesale so files deleted locally disappear on the server too.
# .env and Docker volumes (TLS certificates) are untouched.
tar --exclude=node_modules --exclude=.next --exclude=__pycache__ --exclude='.env*' -czf - apps infra \
  | ssh "$HOST" "mkdir -p $DIR && rm -rf $DIR/apps $DIR/infra && tar -xzf - -C $DIR"

echo "==> syncing .env and sites.env (mode 600)"
scp -q .env "$HOST:$DIR/.env"
scp -q sites.env "$HOST:$DIR/sites.env"   # the two portfolio versions' domains and profiles (not in the repo)
ssh "$HOST" "chmod 600 $DIR/.env $DIR/sites.env"

echo "==> building and starting containers"
ssh "$HOST" "cd $DIR && APP_VERSION=$VERSION docker compose --env-file sites.env -f infra/docker-compose.yml up -d --build ${SERVICES:---remove-orphans} && docker image prune -f >/dev/null && docker compose --env-file sites.env -f infra/docker-compose.yml ps"

echo "==> smoke test"
sleep 5
set -a; . ./sites.env; set +a
for url in "https://$UPWORK_SITE_HOST" "https://$UPWORK_STORE_HOST" "https://api.$UPWORK_SITE_HOST/health"            "https://$WORKANA_SITE_HOST" "https://$WORKANA_STORE_HOST"; do
  printf '%-36s %s\n' "$url" "$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$url" || echo FAIL)"
done
