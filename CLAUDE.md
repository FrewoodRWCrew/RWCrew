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
  app/modules/   One package per module (module_1 .. module_9). module_2 .. module_9 are thin
                 wrappers around the shared app/modules/common.py factory; module_1 (TagScan) has
                 its own bespoke custom-roles-with-per-screen-permissions system instead — see
                 docs/module-custom-roles-pattern.md if another module needs the same thing
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
    modules/module-1/             TagScan: CSV-intake module with its own custom-roles system
                                  (Roles + Users under "Access Rights") — see
                                  docs/module-custom-roles-pattern.md
    modules/module-2..9/         One route folder per module, thin wrapper around
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
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8020
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
- **Backend runs on port 8020, and dev mode does NOT use `--reload`.** Root cause found:
  `uvicorn --reload` on Windows launches its actual worker via Python's `multiprocessing` (you can
  see it as a `python.exe -c "from multiprocessing.spawn import spawn_main; spawn_main(parent_pid=...,
  ...)"` process in `Get-CimInstance Win32_Process`). Killing the reloader/parent PID that
  `Get-NetTCPConnection`'s `OwningProcess` reports does **not** kill that spawned child — it's left
  running as an orphan, still holding the listening socket with whatever code was loaded when it
  was spawned. Every subsequent request has a race between the orphan (stale code) and any new
  process on the same port, so routes intermittently 404/405/500 or behave as if a fix was never
  applied — confirmed by comparing against FastAPI's in-process `TestClient`, which always reflects
  the real, current code. This cost real time across ports 8000, 8010, and 8020 before being found.
  **Fix / prevention**: run the dev server *without* `--reload`
  (`uvicorn app.main:app --port 8020`) and restart it manually after backend changes; if you must
  use `--reload`, after killing it always check `Get-CimInstance Win32_Process -Filter "Name =
  'python.exe'"` for lingering `multiprocessing.spawn` children and kill those specific PIDs too —
  killing only the reloader PID is not enough. If a port ever seems haunted again despite this,
  `netstat -ano | findstr :<port>` for a stray LISTENING PID and moving to a fresh port remains the
  fallback (update `frontend/.env.local(.example)`, `frontend/src/lib/config.ts`, `backend/README.md`,
  and this file).
- **JWTs must include a random `jti`.** `app/core/security.py`'s `_create_token` adds one
  specifically because two tokens for the same user issued within the same second would
  otherwise be byte-for-byte identical (all other claims round to the same second), silently
  breaking refresh-token rotation/reuse-detection. Found via a genuinely flaky test — don't remove it.
- **Silent session refresh happens in two places, both needed.** The access cookie lives 15 min, the
  refresh cookie 30 days (`backend/app/core/config.py`). (1) `frontend/src/proxy.ts` — on a page
  request with a refresh cookie but no access cookie, it calls `/api/auth/refresh` *before* rendering
  (via `lib/session-refresh.ts`) and sets the new cookies on both the request (so Server Components see
  them) and the response. Server Components can't set cookies, so this can't move into
  `server-auth.ts`. (2) `lib/api.ts` `fetchWithRefresh` — retries once after a 401 for calls made
  from the browser. Both share ONE in-flight refresh per token (the backend rotates the refresh token
  on every use, so a second concurrent refresh with the same token gets a 401) — keep that
  single-flight/short result cache if you touch either. New plain `fetch` calls to the backend in
  `api.ts` should use `fetchWithRefresh`, not `fetch`.
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
- **Raspberry Pi → VPS CSV push (TagScan)**: a Pi runs `scripts/pi-watcher/` and POSTs finished CSVs
  over HTTPS to `POST /api/public/tagscan-intake` (`module_1/device_router.py`, per-scanner
  `X-API-Key`); files land in `Unreaded Tags` and are ingested by the manual "Scan" button. Full
  setup: `docs/tagscan-raspi-setup-guide.pdf`. Things that bite:
  - nginx's default 1 MB body limit rejects larger CSVs before FastAPI sees them —
    `deploy/nginx/rwcrew.conf` sets `client_max_body_size 25m` on that one location (app limit is
    `tagscan_intake_max_file_mb`, 20). The same location is rate-limited (`limit_req`). After
    certbot rewrites the file on the server, those directives must exist in the `443` blocks too.
  - The Pi's producing app must write `name.csv.tmp` then `rename()` to `name.csv`, and use unique
    filenames. The backend dedupes by filename + content: same name and bytes → `duplicate`; same
    name, *different* bytes → stored as `name__<sha256-12>.csv` (never dropped).
  - A scanner's API key only works on the environment (test vs production) it was generated on.
- Documentation style for this project: comment every logical block/statement in plain language
  (not literally every line, not just top-level docstrings) — see any file under `app/` or `src/`
  for the expected density. This applies to backend and frontend code we write; generated files
  (Alembic migrations, shadcn's `src/components/ui/*`) are left as generated.
- **Every list/CRUD table must pin its header row and its Actions column while scrolling, and
  scroll both directions inside a capped-height box instead of growing the whole page.** Canonical
  example: `frontend/src/components/module-3/intervention-requests-management.tsx`. The pattern,
  always used together:
  - Wrapper div around `<Table>`: `rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto`
    (no `overflow-x-auto` on this div itself — that Tailwind arbitrary-child-variant reaches into
    `<Table>`'s own internal container, which already has `overflow-x-auto`, and adds vertical
    scrolling on top of it).
  - Every header-row `TableHead` (first row): `sticky top-0 z-20 bg-background` added to its
    existing classes. A second header row (e.g. per-column filters) uses `top-10` instead (offset
    below the first row's height) at the same `z-20`.
  - The Actions column's `TableHead`: `sticky top-0 right-0 z-30 bg-background` (or `top-10` on a
    filter-row placeholder cell) — z-30 so the corner cell stays above the other sticky headers.
  - Each `TableRow`: `className="group"`. Each Actions `TableCell`:
    `sticky right-0 z-10 bg-background group-hover:bg-muted/50` (keeps the pinned cell's hover
    background in sync with the row's own `hover:bg-muted/50`).
  - `bg-background` is required on every sticky cell (opaque, prevents ghosting from rows/columns
    scrolling underneath). A table with no Actions column still gets the scroll wrapper + sticky
    header treatment, just without the `right-0`/z-30 pieces.
  Apply this to every new list-screen table from the start — don't ship one without it.
