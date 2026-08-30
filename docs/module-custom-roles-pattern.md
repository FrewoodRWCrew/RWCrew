# Reusable Pattern: Custom Roles + Per-Screen Permissions (built for TagScan)

This document explains the access-control system built for the **TagScan** module
(`module-1`) in enough detail that it can be copied into any of the other 8 modules
(`module-2` .. `module-9`) when one of them needs the same thing: custom,
admin-defined roles with fine-grained view/create/edit/delete permission per screen,
instead of the site-wide fixed admin/editor/reader roles.

It is a step-by-step replication guide, not just a description — follow the steps in
order, swapping in your module's own name where marked, and you'll end up with a
working, independently-gated permission system for that module.

## 1. Two different systems exist in this codebase — know which one you're extending

RW Crew actually has **two** separate role systems. Do not confuse them.

| | The shared system (modules 2–9 today) | TagScan's system (module-1) |
|---|---|---|
| Roles | Fixed: `admin` / `editor` / `reader` (an enum) | Fully custom — created/renamed/deleted freely by that module's own admin |
| Permissions | Implicit in the role name, not configurable | Explicit per-screen switches: `can_view` / `can_create` / `can_edit` / `can_delete` |
| New screens | Nothing to register — the fixed roles apply everywhere | Must be registered in a small Python list; then automatically appear (unchecked) in every role's permission matrix |
| Built by | `app/modules/common.py`'s `create_module_router()` factory — one shared implementation used by all 9 modules' thin `router.py` files | A bespoke set of models/schemas/router per module — **not** a shared factory (see §8) |
| DB tables | `Landing_module_roles` (one shared table, `module_id` column distinguishes modules) | Four tables *per module*, each prefixed with that module's own name (`Tagscan_roles`, `Tagscan_screens`, …) |

**Use the shared system (do nothing extra) if** the module just needs "this person is
this module's admin/editor/reader" — that's already working for modules 2–9 out of the
box via `create_module_router()`.

**Use this TagScan-style pattern (follow this guide) if** the module needs roles whose
name and exact permissions are decided by that module's own admin, screen by screen —
e.g. "Scanner Operator can view and create, but not delete, on the Uploads screen, and
has no access at all to the Reports screen."

## 2. Architecture overview

Four database tables, all scoped to one module:

```
<Module>_screens            registry of every screen the module has
  id, key (unique, e.g. "tagscan.roles"), label, sort_order

<Module>_roles               the module's own custom roles
  id, name (unique), created_at

<Module>_role_permissions    what one role can do on one screen
  id, role_id → <Module>_roles, screen_id → <Module>_screens,
  can_view, can_create, can_edit, can_delete
  UNIQUE(role_id, screen_id)

<Module>_user_roles          which single role a user currently holds
  id, user_id → Landing_users (UNIQUE — one role per user), role_id → <Module>_roles
```

Two things make screens "just work" without manual DB edits:

1. **The screen registry is code, not data entry.** A plain Python list
   (`SCREEN_DEFINITIONS` in `screens.py`) is the single source of truth for which
   screens exist. A `sync_screens(db)` function upserts that list into
   `<Module>_screens` every time the backend starts (wired into `app/main.py`'s
   `lifespan`). Add one entry to the list → restart the backend → the screen exists
   and shows up as a new, unchecked row in every role's permission matrix. Nothing
   else needs to be touched by hand.

2. **A permission with no row means "no access".** `<Module>_role_permissions` only
   has a row for a (role, screen) pair once someone has explicitly saved permissions
   for it. No row is treated exactly like a row of all-`False` — this is what makes a
   brand-new screen safe by default (nobody can do anything on it until an admin
   opts a role in).

The permission check itself (`user_can()` in `deps.py`) is: super admin → always
allowed; otherwise look up the user's one role, look up that role's permission row for
the screen in question, and check the specific action's boolean. `UserModuleAccess`
(the normal site-wide "does this user have access to this module at all" grant) is
checked first and separately — a user needs *both* plain module access *and* a role
with the right permission to do anything.

## 3. Complete file inventory

Everything below exists today for TagScan under `module_1` / `Tagscan*`. Treat each
row as "create the equivalent of this file for your module."

**Backend**

| File | Responsibility |
|---|---|
| `app/db/models/tagscan_screen.py` | `TagscanScreen` model → `Tagscan_screens` table |
| `app/db/models/tagscan_role.py` | `TagscanRole` model → `Tagscan_roles` table |
| `app/db/models/tagscan_role_permission.py` | `TagscanRolePermission` model → `Tagscan_role_permissions` table |
| `app/db/models/tagscan_user_role.py` | `TagscanUserRole` model → `Tagscan_user_roles` table |
| `app/db/base.py` | Must import all 4 new models so Alembic autogenerate can see them |
| `app/schemas/tagscan.py` | Pydantic request/response schemas for screens, roles, permissions, users, `/me/permissions` |
| `app/modules/module_1/screens.py` | `ScreenDefinition` + `SCREEN_DEFINITIONS` list + `sync_screens(db)` |
| `app/modules/module_1/deps.py` | `require_module_access`, `user_can()`, `require_screen_permission()` — the actual permission-checking logic |
| `app/modules/module_1/router.py` | The bespoke router: screen list, role CRUD, permission-matrix save, user list/create/role-assignment, `/me/permissions` |
| `app/main.py` | Registers the module's router + calls `sync_screens()` in `lifespan` |
| A new Alembic migration | Creates the 4 tables (see §6) |
| `tests/modules/module_1/test_roles.py` | Full test coverage — sync, access enforcement, role CRUD, permission independence, user scoping |

**Frontend**

| File | Responsibility |
|---|---|
| `src/lib/types.ts` | `TagscanScreen`, `TagscanScreenPermission`, `TagscanRole`, `TagscanUserSummary`, `TagscanMyPermissions` interfaces |
| `src/lib/api.ts` | Fetch wrappers for every endpoint above |
| `src/components/module-1/tagscan-sidebar.tsx` | The module's own left-hand nav — group heading + one link per screen, each gated by `viewableScreenKeys` |
| `src/app/[locale]/(protected)/modules/module-1/layout.tsx` | Fetches `/me/permissions` once, renders the sidebar, shows a forbidden message on 403 |
| `src/app/[locale]/(protected)/modules/module-1/access-rights/page.tsx` | Redirects to the first sub-screen |
| `.../access-rights/roles/page.tsx` + `src/components/module-1/roles-management.tsx` | Role CRUD + permission-matrix editor UI |
| `.../access-rights/users/page.tsx` + `src/components/module-1/users-management.tsx` | User list + role assignment + "grant access" UI |
| `messages/en.json`, `messages/nl.json` | A `tagscan.*` (rename to your module's key) translation namespace |

## 4. Step-by-step replication guide

Worked example below targets **module-2**, giving it the illustrative name
**"Scanner"** — replace every occurrence of `Scanner`/`scanner`/`module-2` with your
module's own real name and key.

### Step 1 — Four SQLAlchemy models

Copy each of the 4 `tagscan_*.py` model files into `app/db/models/scanner_*.py`.
Rename the class (`TagscanScreen` → `ScannerScreen`, etc.) and `__tablename__`
(`"Tagscan_screens"` → `"Scanner_screens"`, etc.) — nothing else changes. The FK from
`<Module>_user_roles.user_id` always points at `Landing_users.id` regardless of module
(there is only ever one shared users table — see CLAUDE.md's "two independent access
axes" section for why).

Add the four new model imports to `app/db/base.py` (next to the existing `Tagscan*`
imports) so Alembic can see them.

### Step 2 — Alembic migration

```
cd backend
.venv/Scripts/python -m alembic revision --autogenerate -m "add scanner tables"
```

Review the generated migration against `3508ebb3e74d_add_tagscan_tables.py` as a
template — it should create the same 4 tables/indexes/constraints, just renamed. If
this module also needs its `Landing_modules.name` display value changed away from the
generic seeded placeholder (e.g. `"Module 2"` → `"Scanner"`), add the same hand-written
`op.execute('UPDATE "Landing_modules" SET name = \'Scanner\' WHERE key = \'module-2\'')`
data change (with a matching `downgrade()`) — see that same migration file for the
exact pattern. Then:

```
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m alembic check   # confirms zero drift
```

### Step 3 — Schemas

Copy `app/schemas/tagscan.py` to `app/schemas/scanner.py`, renaming
`TagscanUserSummaryResponse` → `ScannerUserSummaryResponse` (the rest of the class
names are generic enough — `RoleResponse`, `ScreenResponse`, etc. — to keep as-is if
you put them in their own `scanner.py` module; only rename where a name collision with
another module's schemas file would actually occur, since each lives in its own file).

### Step 4 — Screen registry

Copy `app/modules/module_1/screens.py` to `app/modules/module_2/screens.py`. Replace
the import (`TagscanScreen` → `ScannerScreen`) and write your own
`SCREEN_DEFINITIONS`, e.g.:

```python
SCREEN_DEFINITIONS: list[ScreenDefinition] = [
    ScreenDefinition(key="scanner.dashboard", label="Dashboard", sort_order=1),
    ScreenDefinition(key="scanner.roles", label="Roles", sort_order=2),
    ScreenDefinition(key="scanner.users", label="Users", sort_order=3),
    # add module-specific screens here as they're built, e.g.:
    # ScreenDefinition(key="scanner.uploads", label="Uploads", sort_order=4),
]
```

Screen keys must be globally unique-in-intent (they're only ever looked up within
this module's own table, so a collision with another module's key string is
harmless, but keep the `<module>.` prefix for readability).

### Step 5 — Permission dependency logic

Copy `app/modules/module_1/deps.py` to `app/modules/module_2/deps.py`. Change:
- `MODULE_KEY = "module-1"` → `"module-2"`
- `MODULE_LABEL = "Tagscan"` → `"Scanner"`
- Every `Tagscan*` model import/reference → `Scanner*`

Nothing else in this file is module-specific — `user_can()`, `require_screen_permission()`,
`require_module_access()`, `get_user_role()`, `get_permission_for_screen()` are all
generic logic that just needs the right models plugged in.

### Step 6 — Router

Copy `app/modules/module_1/router.py` to `app/modules/module_2/router.py`. Rename the
model/schema imports, the `router = APIRouter(prefix="/api/modules/module-2", ...)`
line, and every hard-coded `"tagscan.roles"` / `"tagscan.users"` / `"tagscan.dashboard"`
screen-key string to your module's own keys. The endpoint shapes
(`GET /screens`, `GET|POST /roles`, `PUT|DELETE /roles/{id}`, `PUT /roles/{id}/permissions`,
`GET /users`, `PUT /users/{id}/role`, `POST /users`, `GET /me/permissions`) can be
copied verbatim otherwise.

Keep the two screens gated independently as TagScan does (`"tagscan.roles"` for role
CRUD/permissions, `"tagscan.users"` for the three user-management endpoints) — this is
what lets a module have someone who can manage roles but not onboard users, or vice
versa.

### Step 7 — Wire it into `app/main.py`

- Import `sync_screens` from `app.modules.module_2.screens` alongside the existing
  `module_1` one, and call it in `lifespan` too.
- Replace `module_2_router`'s import with the new bespoke router (it currently comes
  from the generic `create_module_router()` call in the module's old `router.py`).

### Step 8 — Tests

Copy `tests/modules/module_1/test_roles.py` to `tests/modules/module_2/test_roles.py`
and rename the imports/keys throughout. This gives you, out of the box: screen-sync
tests, access-enforcement tests (no access / access-but-no-role / view-but-not-edit),
super-admin-bypass, role CRUD (duplicate name, delete-while-assigned), permission
matrix replacement, user creation scoped to this module only, and the two
independent-gating tests for "Roles" vs "Users". Run `pytest` and fix any leftover
`module-1`/`Tagscan` references.

### Step 9 — Frontend types + API client

In `src/lib/types.ts`, copy the 5 `Tagscan*` interfaces, renaming to `Scanner*`. In
`src/lib/api.ts`, copy the corresponding fetch functions, pointing at
`/api/modules/module-2/...`.

### Step 10 — Frontend components

Copy `src/components/module-1/{tagscan-sidebar,roles-management,users-management}.tsx`
into `src/components/module-2/`, renaming the component names, imports, and every
`/modules/module-1/...` route/URL to `/modules/module-2/...`. Copy the layout and page
files under `src/app/[locale]/(protected)/modules/module-1/` into the `module-2`
equivalent the same way.

### Step 11 — Translations

Add a `scanner` (or your module's real key) namespace to both `messages/en.json` and
`messages/nl.json`, mirroring the `tagscan` namespace's shape: top-level `dashboard`,
`dashboardComingSoon`, `accessRights`, then nested `roles` and `users` objects. See
§5 for the naming convention to keep translations consistent across modules.

## 5. Naming convention reference

| Thing | Pattern | TagScan example |
|---|---|---|
| DB table prefix | `<ModuleName>_` (PascalCase, matches the module's own display name) | `Tagscan_screens`, `Tagscan_roles` |
| Model class prefix | `<ModuleName>` | `TagscanScreen`, `TagscanRole` |
| Screen key | `<modulename>.<screen>` (lowercase, dot-separated) | `tagscan.roles`, `tagscan.users` |
| Module key (URL/routing) | `module-<N>` (unchanged — this is the existing module numbering, not module-specific) | `module-1` |
| Translation namespace | `<modulename>` (lowercase, matches screen-key prefix) | `tagscan` |
| Frontend component folder | `src/components/module-<N>/` | `src/components/module-1/` |

This mirrors the naming decision already made for TagScan/`Tagscan_*` — see
CLAUDE.md's Gotchas section for why `Landing_`, `landing_md_`, and `Tagscan_` are three
deliberately different prefixes in this codebase.

## 6. Gotchas specific to this pattern

- **This is not (yet) a shared factory.** Unlike `create_module_router()`, there is no
  single reusable implementation of the custom-roles system — each module that needs
  it gets its own copy of models/schemas/deps/router, per the steps above. This was a
  deliberate choice when TagScan was built (module-1 needed this system alone; modules
  2–9 kept the simple fixed-role system). If three or more modules end up needing this
  same pattern, it would be worth extracting a generic version (parameterized by
  module key + table prefix, the same way `create_module_router()` is parameterized
  today) — but don't do that speculatively; wait until a second module actually needs
  it, then generalize from two real implementations instead of guessing at the right
  abstraction from one.
- **Restart the backend after adding a screen.** `sync_screens()` only runs at
  startup (see the multiprocessing/`--reload` gotcha in CLAUDE.md — always restart
  manually rather than relying on `--reload`).
- **A role with permission on one screen doesn't imply anything about another
  screen.** This is intentional (it's the whole point), but it means the frontend
  must fetch data for exactly the screen it's showing and treat a 403 on one
  endpoint as *that screen's* forbidden state, not the whole module's. See how
  `access-rights/users/page.tsx` fetches roles as a "best effort, empty list on 403"
  fallback (for the role-assignment dropdown) rather than treating a lack of
  `"tagscan.roles"` permission as fully blocking the Users screen.
- **One role per user, not many.** `<Module>_user_roles.user_id` is unique. If a
  future module genuinely needs multiple simultaneous roles per user, that's a
  different (more complex) design than what's documented here.
- **Module access vs. module role are still two separate steps.** Creating a user via
  this system's `POST /users` grants `UserModuleAccess` (via the super-admin-only
  mechanism, exposed to this module's own admin for this module only) — a role
  assignment on top of that is optional and separate. Don't assume access implies a
  role, or a role implies access; both are checked independently everywhere.
