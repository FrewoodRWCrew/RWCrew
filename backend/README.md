# RW Crew — backend

A FastAPI + PostgreSQL backend: authentication, the module access-rights
system, and one API package per module (`app/modules/module_1` ..
`module_9`).

## First-time setup

```bash
# 1. Start a local PostgreSQL database in Docker (run from the repo root):
docker compose up -d db

# 2. Create a virtual environment and install dependencies:
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
# .venv/bin/pip install -r requirements.txt     # macOS/Linux

# 3. Copy the example environment file and adjust if needed:
cp .env.example .env

# 4. Apply the database migrations:
.venv/Scripts/python -m alembic upgrade head

# 5. Seed the 9 modules and create the first super-admin account:
.venv/Scripts/python -m app.cli.seed --email admin@example.com --password "ChangeMe123!" --name "Your Name"
```

## Running the API

```bash
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8010
```

The API is then available at http://localhost:8010 (interactive docs at
http://localhost:8010/docs).

## Running the tests

```bash
.venv/Scripts/python -m pytest
```

Tests run against a temporary in-memory SQLite database, so they don't
require Docker/PostgreSQL to be running.

## Project layout

```
app/
  core/      Settings, database connection, password hashing & JWTs
  db/        SQLAlchemy models
  landing/   Auth endpoints + the super admin's access-rights endpoints
  modules/   One package per module (module_1 .. module_9)
  shared/    Small helpers used across modules
  cli/       The database-seeding script
migrations/  Alembic migrations
tests/       Automated tests, mirroring the app/ folder structure
```
