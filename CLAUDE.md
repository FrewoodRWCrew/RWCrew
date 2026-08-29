# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

- Frontend: Next.js 16 (App Router, Tailwind v4, shadcn/ui on Base UI, next-intl, next-themes)
- Backend: FastAPI (SQLAlchemy 2.x, Alembic, PyJWT)
- Database: PostgreSQL (pg8000 driver — pure Python, no compiled dependency, chosen because this
  machine runs Python 3.14 and pg8000 always has wheels regardless of Python version)

**Note:** a separate, unrelated project also called "RWCrew" (Combell-hosted, at
`c:\Fre Software\RWCrew.be`) exists on this machine — do not confuse the two. This repo is the
"Module 1..9" tile-launcher app described below; the other is a multi-tenant SaaS with Kar Tracker/
Kar Scanner/Walkies modules.

## Repo layout

```
backend/
  app/core/      Settings (.env), DB session, password hashing, JWT create/decode
  app/db/models/ SQLAlchemy models: User, Module, UserModuleAccess, ModuleRole, RefreshToken
  app/landing/   Auth endpoints (/api/auth/*) + super-admin endpoints (/api/admin/*)
  app/modules/   One package per module (module_1 .. module_9), all built on app/modules/common.py
  app/shared/    Small cross-module helpers (e.g. computing a user's accessible module keys)
  app/cli/seed.py   Seeds the 9 modules + the first super-admin user
  migrations/    Alembic
  tests/         pytest, mirrors app/ structure, runs against in-memory SQLite (see Gotchas)
frontend/
  src/app/layout.tsx           True root layout: <html>/<body>, ThemeProvider (dark-default)
  src/app/[locale]/layout.tsx  Locale-scoped layout: NextIntlClientProvider only (see Gotchas)
  src/app/[locale]/(auth)/login/          Public login page
  src/app/[locale]/(protected)/           Everything requiring login (see Architecture below)
    page.tsx                    Landing tile grid ("Modules Overview")
    admin/access/                Super admin's "Manage Access" screen
    admin/master-data/           Redirects to its first sub-item (season/)
    admin/master-data/season/    "Season" master data (id, unique name) — sidebar groups
                                  future master-data entities as siblings here
    modules/module-1..9/         One route folder per module, thin wrapper around
                                  ModulePlaceholderPage until real content is designed
  src/lib/api.ts               Browser-side API client (fetch with credentials: "include")
  src/lib/server-auth.ts, server-api.ts   Server-Component-side fetchers (forward cookies() manually)
  src/lib/module-theme.ts      Per-module accent colours (tileClassName = solid landing-tile fill,
                                badgeClassName = soft pill used on the module's own page)
  messages/nl.json (default), en.json    next-intl translations
docker-compose.yml   Local Postgres for dev only (port 5433, see Gotchas)
```

## Running locally

Backend (from `backend/`):
```
docker compose up -d db                      # from repo root: starts Postgres on :5433
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # first time
cp .env.example .env                         # first time
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m app.cli.seed --email admin@example.com --password "ChangeMe123!" --name "Your Name"
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8010
```

Frontend (from `frontend/`, in a second terminal):
```
npm install       # first time
cp .env.local.example .env.local   # first time
npm run dev       # http://localhost:3000 -- redirects to /nl by default
```

## Testing

Backend: `cd backend && .venv/Scripts/python -m pytest` — runs against a temporary in-memory
SQLite database (see Gotchas), no Docker required. Currently 34 tests covering auth, token
rotation/reuse-detection, and every access-rights rule.

No frontend automated test suite yet (per the project's stated testing scope: basic backend
tests for core logic only).

## Architecture: the two independent access axes

- **Module access** (`Landing_user_module_access` table): a plain yes/no per user per module, granted
  ONLY by the super admin (`User.is_super_admin`) via `/api/admin/users/{id}/access`
  (`app/landing/admin.py`) and the "Manage Access" checkbox grid. Being super admin does **not**
  auto-grant module access to yourself or anyone else — see `app/shared/access.py`
  `get_accessible_module_keys`. This is deliberate: the super admin's power is scoped to
  *deciding who can open what*, not automatically seeing everything.
- **Module roles** (`Landing_module_roles` table, admin/editor/reader): scoped to one module, assigned by
  that module's own admin (`require_module_admin` in `app/modules/common.py`) — independent of the
  super admin, except the super admin can also always manage roles in any module as a fallback.
  A role can only be granted to a user who already has module access (400 otherwise).
- Both axes are enforced per-module via `create_module_router(module_key, module_label)` in
  `app/modules/common.py` — each of the 9 `app/modules/module_N/router.py` files is a one-line
  call into this shared factory. Add module-specific endpoints alongside that call in the
  module's own `router.py` once real functionality is designed.

## Gotchas

- **Local Postgres runs on port 5433, not 5432** — the other "RWCrew.be" project's own Postgres
  container already occupies 5432 on this machine. See `docker-compose.yml` /
  `backend/.env.example`.
- **Backend runs on port 8010, not 8000.** `netstat -ano` on this machine shows TWO processes
  LISTENING on `127.0.0.1:8000` simultaneously, neither of which `Get-Process`/`tasklist` can
  identify by PID (likely something tied to Docker Desktop's WSL2 networking) — requests to 8000
  get routed to whichever one wins the race, so our own routes appear to 404 at random even
  though the app itself is correct (confirmed via FastAPI's in-process `TestClient`, which always
  worked). Moving the dev server to 8010 sidesteps it entirely. If this ever needs 8000 back,
  check `netstat -ano | findstr :8000` for a second LISTENING PID first.
- **JWTs must include a random `jti`.** `app/core/security.py`'s `_create_token` adds one
  specifically because two tokens for the same user issued within the same second would
  otherwise be byte-for-byte identical (all other claims round to the same second), silently
  breaking refresh-token rotation/reuse-detection. Found via a genuinely flaky test — don't remove it.
- **SQLite ignores `ON DELETE CASCADE` unless told to.** `backend/tests/conftest.py` runs
  `PRAGMA foreign_keys=ON` on connect so deleting a user in tests actually cascades to their
  `Landing_user_module_access`/`Landing_module_roles`/`Landing_refresh_tokens` rows the same way
  Postgres does natively.
- **Every table is prefixed `Landing_`** (e.g. `Landing_users`, `Landing_modules`) at the user's
  request — done via `ALTER TABLE ... RENAME TO` in migration `51a15c8d59d2`, not a drop/recreate,
  so existing data survives. Postgres folds unquoted identifiers to lowercase, but SQLAlchemy
  auto-quotes any identifier containing uppercase letters, so the mixed-case names round-trip
  correctly through the ORM without extra configuration. New models should follow the same
  `Landing_<name>` convention if they belong to the landing/access-rights part of the app (as
  opposed to one specific module).
- **shadcn here is Base UI, not Radix** — `npx shadcn add` on this project generates components
  around `@base-ui/react`. Two consequences that read like Radix but aren't:
  - Composing a custom trigger uses `render={<Button .../>}` on the primitive
    (`DialogTrigger`/`AlertDialogTrigger`/`DropdownMenuTrigger`/etc.), **not** `asChild` + a
    child element — `asChild` doesn't exist on these primitives and fails to type-check.
  - `DropdownMenuItem`/menu items use a plain **`onClick`**, not Radix's `onSelect` (`onSelect` is
    just the native, irrelevant DOM text-selection event on these components — it type-checks
    fine and silently never fires). Cost real debugging time once already; grep for `onSelect` in
    `src/components/` before adding a new menu action.
- **next-themes + next-intl's `[locale]` segment**: the true `<html>`/`<body>`/`ThemeProvider`
  shell lives in `src/app/layout.tsx`, one level *above* `src/app/[locale]/layout.tsx` (which only
  wraps children in `NextIntlClientProvider`). If theme/root-shell code is moved back inside the
  `[locale]` layout, switching languages remounts the whole document (next-themes' injected
  FOUC-prevention script trips a React "script tag" console warning, and you get an unnecessary
  full-shell flash) since the `[locale]` param changes on every language switch.
- **Python 3.14 is the only Python on this machine.** Backend dependencies were deliberately
  picked to have prebuilt wheels for it without a C/Rust toolchain: `pg8000` (pure-Python
  Postgres driver, not `psycopg2`/`asyncpg`) and stdlib `hashlib.pbkdf2_hmac` for password hashing
  (not `passlib`/`bcrypt`). Keep that constraint in mind before adding a new dependency.
- `NEXT_PUBLIC_API_URL` (`frontend/.env.local`) and the URL used to open the frontend in the
  browser must use the **same hostname** (`localhost` vs `127.0.0.1` count as different sites for
  the `SameSite=Lax` auth cookies) — mismatching them silently breaks every authenticated request.
- Documentation style for this project: comment every logical block/statement in plain language
  (not literally every line, not just top-level docstrings) — see any file under `app/` or `src/`
  for the expected density. This applies to backend and frontend code we write; generated files
  (Alembic migrations, shadcn's `src/components/ui/*`) are left as generated.
