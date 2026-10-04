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

# The version shown in the app (super admin's left menu, and /api/health):
# the commit date in Belgian time + the short commit hash, e.g.
# "2026.10.04" + "97cdc36". Read here because the Docker build contexts have
# no .git folder; docker compose passes them on (see docker-compose.prod.yml).
export APP_COMMIT="$(git rev-parse --short HEAD)"
export APP_COMMIT_DATE="$(TZ=Europe/Brussels git log -1 --format=%cd --date=format-local:%Y.%m.%d)"

docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec -T backend python -m alembic upgrade head
docker image prune -f
