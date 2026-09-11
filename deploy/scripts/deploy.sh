#!/usr/bin/env bash
# Redeploys one environment (test or production) on the VPS: pulls the
# branch that environment tracks, rebuilds any changed images, restarts the
# stack, and applies any new database migrations. Run manually for the
# first deploy (Step 7), and by GitHub Actions on every push afterwards
# (Step 8) — see docs/deploying-to-hostinger.pdf.
#
# Usage: deploy.sh /opt/rwcrew/production
set -euo pipefail

DEPLOY_DIR="$1"
cd "$DEPLOY_DIR"

git pull --ff-only
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec -T backend python -m alembic upgrade head
docker image prune -f
