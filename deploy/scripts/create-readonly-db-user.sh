#!/usr/bin/env bash
# Creates (or resets the password of) the "rwcrew_readonly" database login for
# one environment on the VPS. pgAdmin uses this login to look at the test or
# production database for debugging: it can read every table but can never
# change data. The app itself keeps using its own POSTGRES_USER login.
#
# Run it once per environment, from inside that environment's folder, e.g.:
#   cd /opt/rwcrew/test && bash deploy/scripts/create-readonly-db-user.sh
# Running it again is safe; it just sets a new password.
set -euo pipefail

# Must run next to the environment's compose file and .env.
if [[ ! -f docker-compose.prod.yml || ! -f .env ]]; then
  echo "Run this from an environment folder (e.g. /opt/rwcrew/test)." >&2
  exit 1
fi

# Read the database name and owner from this environment's .env, without
# executing the rest of the file.
POSTGRES_USER="$(grep -E '^POSTGRES_USER=' .env | cut -d= -f2-)"
POSTGRES_DB="$(grep -E '^POSTGRES_DB=' .env | cut -d= -f2-)"

# Ask for the new password twice, without echoing it, so it never ends up in
# the repo or the shell history.
read -r -s -p "New password for rwcrew_readonly: " PASSWORD; echo
read -r -s -p "Repeat password: " PASSWORD_AGAIN; echo
if [[ -z "$PASSWORD" || "$PASSWORD" != "$PASSWORD_AGAIN" ]]; then
  echo "Passwords are empty or do not match." >&2
  exit 1
fi

# Run the SQL inside the running db container. The password is passed as a
# psql variable (:'pw' quotes it safely), and ON_ERROR_STOP aborts on the
# first failing statement.
docker compose -f docker-compose.prod.yml exec -T db \
  psql -v ON_ERROR_STOP=1 -v pw="$PASSWORD" -v owner="$POSTGRES_USER" -v db="$POSTGRES_DB" \
  -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<'SQL'
-- Create the login the first time, or only update its password afterwards.
SELECT format('CREATE ROLE rwcrew_readonly LOGIN PASSWORD %L', :'pw')
  WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rwcrew_readonly') \gexec
SELECT format('ALTER ROLE rwcrew_readonly LOGIN PASSWORD %L', :'pw') \gexec

-- Every transaction this login starts is read-only, as an extra safety net.
ALTER ROLE rwcrew_readonly SET default_transaction_read_only = on;

-- Allow connecting and reading everything that exists today.
GRANT CONNECT ON DATABASE :"db" TO rwcrew_readonly;
GRANT USAGE ON SCHEMA public TO rwcrew_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO rwcrew_readonly;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO rwcrew_readonly;

-- Tables that future Alembic migrations create (as the app's own login) are
-- readable too, without re-running this script.
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" IN SCHEMA public GRANT SELECT ON TABLES TO rwcrew_readonly;
ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" IN SCHEMA public GRANT SELECT ON SEQUENCES TO rwcrew_readonly;
SQL

echo "rwcrew_readonly is ready for database '$POSTGRES_DB'."
