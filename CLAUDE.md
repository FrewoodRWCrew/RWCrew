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
  app/db/models/ SQLAlchemy models (one file per table): landing ones (User, Module, UserModuleAccess,
                 ModuleRole, RefreshToken, LoginHistory) plus every module's own tables
  app/landing/   Auth endpoints (/api/auth/*) + super-admin endpoints (/api/admin/*)
  app/modules/   One package per module (module_1 .. module_10). Modules 1, 2, 3, 8 and 9 have their own
                 routers with the custom-roles-with-per-screen-permissions system (see
                 docs/module-custom-roles-pattern.md); modules 4-7 (placeholders) and 10 (phone-app
                 install page) use the shared app/modules/common.py factory
  app/shared/    Small cross-module helpers (accessible module keys, device type from a User-Agent)
  app/cli/seed.py   Seeds the modules + the first super-admin user
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
    modules/module-8/             Altsien Select: KPI, "Ploeg Wizard" (per team + season a
                                  Kernlid walks through steps), "Ploegfiche" (all choices on
                                  one screen + PDF), request follow-up, request statuses,
                                  Access Rights — see "Altsien Select (module-8)" below
    modules/module-4..7/         Placeholder modules: thin wrapper around ModulePlaceholderPage
                                  until real content is designed
    modules/module-10/            "Mobile App": install page for the phone app (QR code + steps),
                                  see "Phone section (PWA)" below
  src/app/[locale]/m/          Phone section of the PWA (only the phone screens) — see "Phone section (PWA)"
  src/components/phone/        Phone screens: shared/ + one folder per module
  src/lib/api.ts               Browser-side API client (fetch with credentials: "include")
  src/lib/server-auth.ts, server-api.ts   Server-Component-side fetchers (forward cookies() manually)
  src/lib/module-theme.ts      Per-module accent colours (tileClassName = solid landing-tile fill,
                                badgeClassName = soft pill used on the module's own page)
  messages/nl.json (default), en.json    next-intl translations
docker-compose.yml   Local Postgres for dev only (port 5433, see Gotchas)
```

## Altsien Select (module-8)

A wizard in which Altsien Kernleden make, per team and per season, the choices the organisation
builds its instructions on. Same custom-roles-per-screen system as module-3 (`AltsienSelect_*` roles
tables, `backend/app/modules/module_8/screens.py`).

- **Team scope**: a user sees the teams linked to them in `MasterData_team_kernlid`; a role with
  "view" on the `altsienselect.allteams` switch-screen sees every team (organisation). Other teams → 404.
- **Season lock**: changes are refused (403) once `Season.periode_open` is off, unless the user has
  "edit" on `altsienselect.allteams`. The module has its own season dropdown (all seasons, `?season=`)
  because the header's selector only lists open seasons.
- **Where choices are stored**: only step progress (`AltsienSelect_step_progress`) and special requests
  (`AltsienSelect_special_requests` + editable `AltsienSelect_request_status`, lowest `sort_order` = the
  start status) live in module-8 tables. Festivals go to `MasterData_team_festival`; delivery locations go
  to KarTracker's Plan a kar table via `module_2/plan_kar_service.py` (shared with module-2's own screen).
- **Adding a wizard step**: add a `StepDefinition` in `backend/app/modules/module_8/steps.py` (optional
  completion check), a component in `frontend/src/components/module-8/wizard/steps/` registered in its
  `index.ts` (unknown keys fall back to a placeholder), translations under `altsienSelect.steps.<key>`,
  and optionally a section in `module_8/ploegfiche_pdf.py`. Progress is keyed by string: no migration.
- **Copy from last season**: steps listed in `COPYABLE_STEPS` (`module_8/previous_season.py`) get a panel
  above them with last season's values line by line (checkbox each, select all, "Copy"). "Last season" is the
  season whose name sorts right before the current one; festivals are matched by name ignoring case, 4-digit
  years and punctuation. Copying only adds/updates, never removes and never marks the step done. Offered now on
  delivery locations, team leads and special requests; add products there once that step is real.
- Products and walkie-talkies are placeholder steps until their own modules exist.
- **Ploegverantwoordelijken** (team leads, per team + season, not RWCrew users) live in MasterData's
  `MasterData_team_responsible`, managed on module-9's `masterdata.team-responsibles` screen (Teams >
  Ploegverantwoordelijken) *and* by wizard step `ploegverantwoordelijken` (step 3, needs ≥1 person) — both
  write through `module_9/team_responsible_service.py`. No module-8 copy of the data.

## TagScan action processing (module-1)

Every scanned CSV line (`Tagscan_line_data`) and file (`Tagscan_header_data`) has a `process_status`
(`new`/`loaded`/`cancelled`) + `process_comment` + `processed_at`, separate from the line's EPC-match `status`.
Lines start `new` at scan time; the file's status is derived from its lines
(`line_processing.refresh_header_process_status`: any `new` → `new`, all cancelled → `cancelled`, else `loaded`).

- `backend/app/modules/module_1/line_processing.py` `PROCESSABLE_ACTIONS` maps a lowercased CSV `Action` to its
  handler. Today only `assignment` (create the `RfidTag` when the EPC isn't registered; already registered →
  `loaded` + comment). **Adding an action** = one `_process_<action>()` returning `(outcome, comment)` + a dict entry;
  lines with an action without a handler simply stay `new`.
- Waiting lines (`new` + action with a handler) show as an orange banner above every TagScan screen
  (`components/module-1/pending-actions-banner.tsx`, rendered by the module layout); it opens
  `pending-actions-dialog.tsx` (process all / cancel one line with a required reason). Screens that create lines
  without navigating dispatch `PENDING_ACTIONS_CHANGED_EVENT` so the banner re-counts.
- Rows on Tag Headerdata/Tag Linedata are coloured by `process_status` (`components/module-1/process-status.ts`:
  orange new, green loaded, red cancelled). Lines that existed before this feature were backfilled as `loaded`.

## Outgoing email (Resend)

- `backend/app/core/mail.py` `send_email()` posts to Resend's HTTP API with `httpx` (no extra package). It
  never raises: errors are logged. With `RESEND_API_KEY`/`MAIL_FROM` empty (local dev, tests) it just logs a skip.
- Settings per environment in the server's `.env`: `RESEND_API_KEY`, `MAIL_FROM` (its domain must be verified
  in Resend via DNS), `APP_PUBLIC_URL` (link in mails), and `MAIL_SUBJECT_PREFIX` (e.g. `[TEST] ` on test).
  **Gotcha:** `docker-compose.prod.yml` passes the backend an explicit `environment:` list, so any new
  backend setting must be added there too (and to `.env.test/production.example`) — a value only in the
  server's `.env` never reaches the container. This is why the first test deploy sent no mail.
- **Intervention Requests (module-3) new-request mail**: every new request — staff screen, public QR form
  *and* phone app — mails the active addresses of `InterventionRequests_mailing_recipient` with the
  delivery-note PDF attached (`module_3/notifications.py` `queue_new_request_mail`, sent as a FastAPI
  background task after the 201). The list is managed on "Instellingen > Mailinglijst"
  (screen key `interventionrequests.mailinglist`). A new create path must call `queue_new_request_mail` too;
  edits never mail.

## Phone section (PWA, `/m`)

The phone version of the app is a Progressive Web App served by the same Next.js frontend: `src/app/manifest.ts`
makes the site installable ("Add to Home Screen"), and the installed app opens `/m`, a separate section that
shows **only** the phone screens: login, module tiles, KarTracker (KarScan, Kar Planning, Kar Map) and
Interventie Aanvragen (Akties list/create/edit, KPI overzicht). No desktop sidebar/topbar, no delete, no PDFs.
This is the only phone app: there is no native (App Store / Play Store) app, no separate phone API, no Bearer
tokens and no separate release — a web deploy updates the phone app too. (A React Native/Expo app existed
until October 2026 and was removed entirely; only old login-history rows still mention it, see below.)

- **Organised per module, like the web app**: routes in `frontend/src/app/[locale]/m/` (`login/` outside,
  everything else under `(signed-in)/`, whose layout does the login check), one folder per module
  (`(signed-in)/module-2/`, `(signed-in)/module-3/`); screens in `src/components/phone/module-N/`; cross-module
  pieces (header, body, tiles, menu row, bottom tabs, native select, notices) in `src/components/phone/shared/`.
  Pages stay thin (server-fetch data + rights, render one component).
- **Same API and rights as the web**: the phone uses the normal `/api/modules/...` endpoints with the cookie
  login. Each module has a `*-phone-rights.ts` (reads `me/permissions`, `null` = no module access → the module
  layout shows `PhoneForbidden`) and a `*-phone-routes.ts` (all its phone URLs). Endpoints added for the phone,
  in the modules' own routers: module-3 `GET /lookups` and `GET /intervention-requests/{id}`, module-3 (and
  module-8, same schema) `me/permissions` now also return create/edit/delete keys, module-2 `GET /seasons`.
- **Shared desktop/phone code stays in the module's own folder**: `components/module-2/qr-scanner.tsx` (camera,
  `@zxing/browser`), `components/module-2/kar-map-rows.tsx` (pins/popups of the Kar Map),
  `components/module-3/request-dates.ts` (date helpers).
- **Translations per module**: `phone.*` for the shell, `<moduleNamespace>.phone.*` for a module's screens
  (`karTracker.phone`, `interventionRequests.phone`); existing desktop keys are reused where the text matches.
- **Camera and GPS need HTTPS** (or localhost). To use localhost *and* a real phone at the same time: put
  `NEXT_PUBLIC_API_URL=` (empty) and `DEV_API_PROXY_TARGET=http://localhost:8020` in `frontend/.env.local`,
  restart `npm run dev`, run `cloudflared tunnel --url http://localhost:3000` and open the printed
  `https://<name>.trycloudflare.com` + `/m` on the phone; `http://localhost:3000` keeps working on the PC. Browser
  calls are then relative (`/api/...`, forwarded by `next.config.ts`), so the cookies always belong to the address
  the page was opened on; server code uses `SERVER_API_BASE_URL` (`lib/config.ts`) = the proxy target. A new tunnel
  address needs no config change. **Never put the tunnel URL in `NEXT_PUBLIC_API_URL`**: logging in on
  localhost then silently fails (cookie set for the tunnel's site, login screen comes back with no message).
- **Adding a phone module**: (1) add its key to `components/phone/shared/phone-modules.ts`; (2) create
  `(signed-in)/module-N/layout.tsx` that loads its rights and shows `PhoneForbidden` on `null`; (3) put its
  screens in `components/phone/module-N/` with a rights + routes file; (4) add texts under
  `<moduleNamespace>.phone.*`.
- **Install page (module-10, "Mobile App")**: a normal module granted through "Manage Access", shown as the
  small tile at the top right of the landing page. It shows the `/m` address with a QR code and the "Add to
  Home Screen" steps for iPhone and Android. Both come from `GET /api/modules/module-10/install-info`
  (`backend/app/modules/module_10/router.py`), built from the environment's `APP_PUBLIC_URL` (QR code by
  `segno`); without that setting the page says "not configured".
- **Login history knows website vs phone and PC vs phone**: the login form sends `client` (`"web"`, or
  `"pwa"` from `/m/login`), stored as `Landing_login_history.source`; `device_type` (desktop/mobile/tablet)
  comes from the User-Agent via `backend/app/shared/device.py`, and the raw `user_agent` is kept so it can be
  re-classified later. `source = "mobile"` only exists on old rows from the removed native app (shown as
  "Native app (old)"); never write it again. iPads on iPadOS 13+ present themselves as a Mac → "desktop".

## Version label (which code runs where)

`deploy/scripts/deploy.sh` exports `APP_COMMIT` (short hash) and `APP_COMMIT_DATE` (commit date in Belgian
time, `2026.10.04`) from git. `docker-compose.prod.yml` passes them to the frontend build
(`NEXT_PUBLIC_APP_COMMIT*`) and the backend environment. The frontend shows `v<date> · <hash>` at the bottom of the
super admin's left menu (`AdminSidebar`, `APP_VERSION_LABEL` in `lib/config.ts`), and `/api/health` returns the
backend's `version`. Locally `next.config.ts` reads the same values from git; without git the label is `dev`.

## Running locally

Backend (from `backend/`):
```
docker compose up -d db                      # from repo root: starts Postgres on :5433
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # first time
cp .env.example .env                         # first time
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m app.cli.seed --email admin@example.com --password "ChangeMe123!" --name "Your Name"
.venv/Scripts/python -m uvicorn app.main:app --port 8020   # no --reload, see Gotchas
```

Frontend (from `frontend/`, in a second terminal):
```
npm install       # first time
cp .env.local.example .env.local   # first time
npm run dev       # http://localhost:3000 -- redirects to /nl by default
```

### "Start / restart localhost" = everything, PC *and* phone

When the user asks to start or restart localhost (the app, the web app, "mobile + webapp", ...), always bring
up **all four** pieces, not just the web app, and finish by giving the three addresses below:

1. **Postgres**: `docker compose up -d db` (repo root) if `rwcrew_db` isn't running (`docker ps`).
2. **Backend** on 8020: first stop every `python.exe` whose command line contains `uvicorn` (parent *and*
   child — `Get-CimInstance Win32_Process`), then start it in its own minimised window so it outlives the
   Claude session: `Start-Process <backend>.venvScriptspython.exe -ArgumentList "-m","uvicorn","app.main:app",
   "--port","8020" -WorkingDirectory <backend> -WindowStyle Minimized`.
3. **Frontend** on 3000: stop the process tree on port 3000 (`taskkill /PID <pid> /T /F`) and any
   `cmd.exe ... npm run dev`, then `Start-Process cmd.exe -ArgumentList "/c","npm run dev" -WorkingDirectory
   <frontend> -WindowStyle Minimized`. `frontend/.env.local` must have `NEXT_PUBLIC_API_URL=` (empty) and
   `DEV_API_PROXY_TARGET=http://localhost:8020` (see "Phone section"), otherwise phone/Wi-Fi logins fail.
4. **Cloudflare tunnel** (phone over HTTPS, needed for camera/GPS): stop any running `cloudflared`, then
   `Start-Process "C:Program Files (x86)cloudflaredcloudflared.exe" -ArgumentList "tunnel","--url",
   "http://localhost:3000","--logfile",<scratchpad>cloudflared.log -WindowStyle Minimized` and read the
   `https://<name>.trycloudflare.com` address from the log (it changes on every start; no config edit needed).

Check each one answers (`/api/health` on 8020, `/nl/login` on 3000, the Wi-Fi address and the tunnel), then
report:
- **PC**: http://localhost:3000
- **Phone on the same Wi-Fi** (no camera/GPS — not HTTPS): `http://<PC's Wi-Fi IPv4>:3000/m` — look the IP up
  each time (`Get-NetIPAddress`, interface "Wi-Fi"); it can change. Allowed by `allowedDevOrigins`
  (`192.168.*.*`) in `next.config.ts`; the Windows firewall already allows Node.js.
- **Phone anywhere, with camera/GPS**: `https://<name>.trycloudflare.com/m`

## Testing

Backend: `cd backend && .venv/Scripts/python -m pytest` — runs against a temporary in-memory
SQLite database (see Gotchas), no Docker required. Covers auth, token rotation/reuse-detection,
every access-rights rule and each module's endpoints.

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
  refresh cookie ends the login session after `session_max_hours` (6 h, absolute from the password entry; rotation never extends it — `backend/app/core/config.py`). (1) `frontend/src/proxy.ts` — on a page
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
  Even in the right place, React 19 warns about next-themes' inline `<script>` whenever it renders on the
  client; `theme-provider.tsx` passes `scriptProps` with `type: "application/json"` in the browser only
  (the server HTML keeps the real script) — keep that until next-themes fixes it upstream.
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
  - **Routing by the CSV's `Mode` column** (`TEST`/`PROD`): the Pi may post to either environment; when `Mode`
    names the other one, `module_1/intake_forward.py` re-POSTs the file to that environment's intake (with an
    `X-TagScan-Forwarded: 1` header, so it's never bounced back). Needs `TAGSCAN_ENVIRONMENT`,
    `TAGSCAN_FORWARD_URL` and `TAGSCAN_FORWARD_API_KEY` (a key made on the *other* environment) in each `.env`.
    Empty/unknown `Mode` or no `TAGSCAN_ENVIRONMENT` (local dev) = stored where it arrived.
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
