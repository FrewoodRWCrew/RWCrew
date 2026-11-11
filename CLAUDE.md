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
  app/modules/   One package per module (module_1 .. module_10; module_1 = "Scans", formerly TagScan). Modules 1, 2, 3, 4, 5, 6, 8 and 9 have
                 their own routers with the custom-roles-with-per-screen-permissions system (see
                 docs/module-custom-roles-pattern.md); module 7 (placeholder) and 10 (phone-app
                 install page) use the shared app/modules/common.py factory
  app/modules/wristband/  Wristband scans, shared by Scans (module-1) and the modules with a counter
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
    admin/changelog/             Super admin's "Wijzigingen" list (see "Changelog" below)
    admin/master-data/           Redirects to its first sub-item (season/)
    admin/master-data/season/    "Season" master data (id, unique name) — sidebar groups
                                  future master-data entities as siblings here
    modules/module-1/             Scans (formerly TagScan): RFID CSV intake + wristbands (QR), with its own
                                  custom-roles system (Roles + Users under "Access Rights") — see
                                  docs/module-custom-roles-pattern.md
    modules/module-8/             Altsien Select: KPI, "Ploeg Wizard" (per team + season a
                                  Kernlid walks through steps), "Ploegfiche" (all choices on
                                  one screen + PDF), request follow-up, request statuses,
                                  Access Rights — see "Altsien Select (module-8)" below
    modules/module-4/             StockMaster: warehouse stock (free + in kars), bookings,
                                  kar needs, "Te bestellen", PDFs — see "StockMaster (module-4)"
    modules/module-5/, module-6/  Atelier (work clothing; blocks 1–5 built) and Walkies (still a
                                  shell) — see "Atelier (module-5) and Walkies (module-6)" below
    modules/module-7/             Placeholder module: thin wrapper around ModulePlaceholderPage
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
docs/work-history.md Log of every accepted-and-executed plan (see "Work history" below)
```

## Work history (plan log) — mandatory

Every time a plan is accepted (plan mode approved) **and** carried out, add an entry to
`docs/work-history.md` as part of that same work — before reporting it done or committing. This keeps
the history of the work on the project.

- Newest entry on top, directly under the file's header. Date in Belgian time.
- Entries are never rewritten afterwards; a correction or follow-up gets its own new entry.
- Format:
  ```
  ## YYYY-MM-DD — <short title>
  **Request:** what the user asked for (1–2 lines)
  **Plan:** the approach that was accepted (a few bullets)
  **Changes:** files/areas changed, migrations, new endpoints/screens
  **Verification:** tests run / checks done and their result
  **Notes:** open points, follow-ups, deviations from the plan (optional)
  ```

## Changelog ("Wijzigingen" screen) — mandatory

The super admin's list of every update, correction and new functionality (`/admin/changelog`, under Login geschiedenis).
Colleagues keep requirements and bugs in a sheet with unique numbers; the user names that number when starting a point.

- **One source for localhost, test and production**: `changelog.json` on the git branch **`changelog`** (holds only that
  file, not deployed). Every backend reads it at runtime through `app/landing/changelog.py` (`GET /api/admin/changelog`,
  60 s cache, last good copy if GitHub fails, 503 without one), so a pushed change shows everywhere within a minute.
  Never add an environment-specific copy. `CHANGELOG_GITHUB_TOKEN` is optional: it only lifts GitHub's anonymous rate limit.
- **Keep it current as part of the work**, also for work without a number (and with or without plan mode):
  starting a point = add or update its line, `in_progress`; finished = `done`; right after each commit = add its **full**
  SHA to `commits`. Push the branch each time: this is the standing exception to "commit only when asked", for this branch only.
- **Line**: `id` (next free integer, never reused), `issues` (sheet numbers as text, `[]` without), `date` (Belgian; day
  finished, or day added/started while not done), `type` `feature|update|fix`, `status` `open|in_progress|done`, `module`
  (plain name, `General` for app-wide), `title`, `description` (English, one sentence), `commits`.
- **How to edit**: `git worktree add <scratchpad>/changelog-worktree changelog`, `git pull` there, edit `changelog.json`, from
  `backend/` run `.venv/Scripts/python -m app.cli.changelog_check <path>`, then commit, push to `origin changelog` and
  `git worktree remove`. A file that fails the check must not be pushed.

## StockMaster (module-4)

The warehouse stock of MasterData products (whole pieces only), as **free stock** on the product's fixed
bin (`MasterData_product.warehouse_id` + `warehouse_location`, no bin table) and **loaded in KarTracker's
kars** while they stand in the warehouse. Web only, except the phone's voice count (below). Full design: `docs/stockmaster-design.md`.
Same custom-roles-per-screen system as module-8 (`StockMaster_*` roles tables, `module_4/screens.py`).

- **Product master data lives here** (moved from MasterData on 2026-10-24): sidebar group "Masterdata" =
  Producten with Type/Magazijnen/Categorieën/Limieten nested under it (`/modules/module-4/masterdata/products/...`)
  + Data Upload/Download (`masterdata/data-upload-download`), screens `stockmaster.products|product-types|warehouses|
  product-categories|product-limits|dataupload`. Endpoints in `module_4/product_masterdata_router.py` (own APIRouter on
  the module-4 prefix, included in `main.py`): CRUD, picture PUT/DELETE (GET stays in `router.py`, module access only),
  XLSX import/export (`module_4/*_import.py`, still using `module_9/xlsx_common.py`) and `GET /product-stats` (KPI
  page's "Producten" section, `product_stats.py`). The tables keep their `MasterData_*` names. TagScan and KarTracker
  read the product lists from these endpoints, so their users need StockMaster view rights for those dropdowns.
- **Only `module_4/stock_service.py` changes stock.** Each booking = one `StockMaster_document` + one
  `StockMaster_movement` per product (`free`/`kar`/`external` from → to), and `StockMaster_balance` (one row
  per product per place; `kar_id` NULL = free; emptied rows are deleted) is updated in the same transaction
  after `SELECT … FOR UPDATE`, so stock never goes negative. Nothing is edited or deleted: "Ongedaan maken"
  = `reverse_document` (a `reversal` document). The service never commits — the router (or, later, an
  RWCrew Pi's `module_4/rfid_router.py`) does; a `StockError("code", *params)` becomes
  HTTP detail `"code|param|…"`, translated by the frontend under `stockMaster.errors.<code>` — a new code
  needs a translation in both languages.
- **The booked-by user is always the session user** (`created_by` + `created_by_name` snapshot on documents
  and movements), never taken from the request.
- **Kar stock only exists in the warehouse**: "Kar vertrekt" books the kar's whole contents out and opens a
  `StockMaster_kar_trip`; "Kar terug" books the returned lines into the kar or to free stock (per line,
  defaulted from the product's new `stock_return_to`) and closes it. A kar with an open trip can't be
  unloaded/counted. What didn't come back is the team's consumption on the KPI page.
- **Follow-up delivery ("nalevering")**: Kar laden of a kar with an open trip books free (or a warehouse kar) →
  `external` with `StockMaster_document.trip_id` = the trip; `dispatched_lines(trip)` adds those posted deliveries,
  so Kar terug, consumption and an out kar's progress count them. Undoing "Kar vertrekt" is refused
  (`kar_has_deliveries`) while such deliveries exist.
- **Kar needs** (`StockMaster_kar_requirement`, per season + kar) only through `module_4/requirement_service.py`
  — Altsien Select's Products wizard step reuses it (no module-8 copy of the data, see "Altsien Select"). They pre-fill
  "Kar laden", drive the kar cards' "18 / 20" and "Te bestellen" (needs − free − in kars).
- **StockMaster on the RWCrew Pi (RFID, 2026-11-09)** replaces the old CSV route (Pi → CSV → TagScan "Book In" →
  Inboeken basket; retired: `tagscan_book_in.py`, its banner, landing pill and `tagscan_line_ids` are gone). The Pi
  books live through `module_4/rfid_router.py` (own APIRouter on the module-4 prefix, included in `main.py`):
  `POST /rfid/resolve` (≤1000 EPCs; view on stock/kars/count/tags), `GET /rfid/products` (pickers, `tagged` count),
  `GET /rfid/place-tags`, `POST /rfid/assign` (Tags koppelen, `stockmaster.tags` create), `POST /rfid/bookings`
  (`TagBookingRequest`: action, season, kar, reason, `epcs`, `lines` = untagged pieces / Kar terug destinations,
  `missing` = Kar vertrekt's choices, `reader`; same rights + season lock as `POST /bookings` via
  `deps.ensure_booking_right`) and `GET /rfid/history` (`stockmaster.taghistory`, web page `/modules/module-4/tag-history`).
  One product tag = one piece of `Tagscan_rfid_tag.assigned_product_id`; quantity = tags + untagged lines; documents get
  `source="pi"`. `module_4/tag_booking.py` turns a Pi booking into `stock_service` calls; **`module_4/tag_service.py` is
  the only writer of the tag places**.
- **Tag places = last known place** (`Tagscan_rfid_tag.stock_place` free/kar/out/written_off, NULL = unknown, +
  `stock_kar_id`, `stock_trip_id`, `stock_document_id`, `stock_place_at`; trace per tag per booking in
  `StockMaster_movement_tag`, migration `a3d8f6c2e914`). **Only Pi bookings move tags**; web bookings move quantities, so
  a place can be stale: `tag_service.check_places` only refuses clear contradictions (`tag_already_in_stock`,
  `tag_in_kar`, `tag_in_other_kar`, `tag_already_in_kar`, `tag_on_trip`, `tag_on_other_trip`, `tag_written_off`; all
  translated under `stockMaster.errors` and in the Pi's `errors`). Unknown places are accepted everywhere; a kar that
  left since makes its tags "out", a closed trip makes them unknown (`PlaceBook`); a Pi **Telling** is the authority
  (read tags get the place, known-but-unread ones of the counted products become unknown; `count_stock(...,
  allow_no_differences=True)`). Changing a tag's product (Tagbeheer, Tags koppelen with replace) forgets its place.
  `reverse_document` calls `tag_service.reverse_places`: tags go back only while that booking is still their latest
  (`from_document_id` hands them back to the previous one). Tagbeheer shows the place ("Plaats" column).
- **Kar vertrekt on the Pi = "correct, then book"**: `stock_service.dispatch_kar_corrected` in one transaction —
  missing pieces back to free stock (`unload_kar`) or written off (`book_out`, reason required), extra pieces loaded
  (`load_kar`), then `dispatch_kar`. `missing` must cover the shortfall exactly (`missing_unresolved` /
  `missing_too_many`). The corrections are separate documents ("Kar vertrekt <kar>"); undoing the departure leaves them.
- **Kar laden's "Karinhoud" table** (`components/module-4/kar-load-table.tsx`): one row per product + Bron; rows from
  the kar needs ("Altsien Select") plus **manual requests** (`StockMaster_kar_manual_request`, per season + kar +
  product, written only by `module_4/manual_request_service.py`, `POST/DELETE /kars/{id}/manual-requests`, same right
  as booking Kar laden). What a manual request already got is not stored: it's what the kar holds (or consumed
  outside this season) beyond its need. Both rows of a product are booked as one line. Manual requests count in the
  kar's loading progress (`build_kar_summaries`) and the season demand for *Automatisch*, but not in the kar needs,
  Laadlijst or "Te bestellen".
- **"Op dit moment beschikbaar voor levering"** (Kar laden) = the organisation's flow diagram, worked out only in
  `module_4/delivery_entitlement.py` (Blokkeer → 0, logistiek product → asked, then the product's Limiet, matched by
  *name*: Ongelimiteerd/Automatisch/Percentage/Toegewezen aantal; Maximum initiële stock caps until the kar's KarTracker
  status is "Geleverd", shared by a kar's Altsien + Manueel row). `build_kar_detail` sends `entitled` + an
  `entitlement_trace` (values + path of diagram nodes) per kar line and manual request; the frontend's
  `availableForDelivery` only caps it by the physical stock, and `availability-flow-dialog.tsx` draws the trace
  (icon next to each row's value). A new diagram node needs a path key in both files.
- **Voice count ("Spraaktelling", phase 1)**: phone screen `/m/module-4/voice-count` (the only StockMaster phone screen):
  scan a kar's QR code → Ophalen/Terugbrengen → tap the microphone (browser's free Web Speech API, `nl-BE`/`en-GB`,
  `components/phone/module-4/use-speech-recognition.ts`) **or** dictate into the "Dicteren of typen" box with the
  keyboard's own microphone — on an iPhone home-screen app the Web Speech API often stays silent, so that box comes
  first there (iOS: one sentence per turn, last interim text counts; `?debug=1` shows the recognition's events) →
  `voice-count-parser.ts` turns sentences into quantity +
  product (number words nl/en, fuzzy name match; unsure = orange line to confirm) → Opslaan. Stored only through
  `module_4/voice_count_service.py` in `StockMaster_voice_count` + `_line` (status `new`/`booked`/`cancelled`,
  `document_id` for the later booking); **doesn't change stock yet** (phase 2). Screen `stockmaster.voicecount`:
  create = count on the phone (its `GET /voice-count/lookups` brings kars + products, no other rights needed), view =
  desktop "Spraaktellingen" (`/modules/module-4/voice-counts`, CSV download), edit = cancel.
- **Minimum stock** = MasterData product `min_stock` (consumables only) → orange banner in the module layout.
- Seasons: the module's own dropdown (`?season=`); bookings in a closed season need "edit" on the
  `stockmaster.closedseason` switch-screen. MasterData/KarTracker refuse deleting a product with stock history
  or a kar holding stock.
- PDFs (`module_4/stock_pdfs.py`, house style in `pdf_layout.py` with the TeamKar logo): Laadlijst, Vertrekbon
  (`/bookings/{id}/pdf` of a dispatch), Bestellijst, Telblad, Boekingsbon. The Laadlijst also exists for several
  kars in one PDF (`/kars/load-lists/pdf?kar_ids=…`, each kar on its own page) — printed from "Kar laden"'s loading overview
  (`components/module-4/kar-load-overview.tsx`: per kar the needed product types fully loaded and the pieces, from
  `KarSummaryResponse`). Kar laden opens on that overview; "Laden" opens the booking panel with `?kar=<id>`
  (`kar-load-screen.tsx` switches on `?kar=`/`?product=`/`?from=`).

## Karblad QR: public kar page + Kar inventaris (StockMaster)

The karblad's lower QR code (`module_2/karblad_pdf.py` `build_kar_qr_url`) opens **`/<locale>/kar?team_id=&cart_number=&
delivery_location=&zone=`**: a public page (no login, `(public)` route group) with two tiles, **Interventie aanvragen**
(`/kar/intervention-request`, the unchanged `PublicInterventionRequestForm`) and **Kar inventaris** (`/kar/inventory`).
Old karbladen point to `/intervention-request`, which now only redirects to `/kar` with the same query. The query helpers
are `lib/kar-qr-params.ts`; the tiles pass the query on. Look = the RWCrew Pi's (`.kar-qr` colour tokens in `globals.css`,
copied from the Pi's `Theme.qml`; shell/landing in `components/shared/kar-qr/`).

- **Kar inventaris** = a team counts its own kar before pick-up. **No RWCrew login or rights**: the kar's lock code
  (`KarTracker_karren.kar_code`) is the key. `POST /api/public/stockmaster/kar-inventory/unlock` → a 2 h JWT (`typ =
  "kar_inventory"`, kar id, fingerprint of the code: changing the code ends sessions) sent as `X-Kar-Inventory-Token`
  (`?token=` for product pictures). Unknown kar and wrong code give the same `wrong_code`; `no_code` for a kar without a
  code; per IP 10 tries/min and per kar 5 wrong codes → 15 min lock (`too_many_tries|seconds`, in memory via
  `app/shared/rate_limit.py`, also used by module-3's public form; one uvicorn process).
- **Expected** per product = what left with the kar on its open trip (`stock_service.dispatched_lines`, incl. naleveringen),
  else the kar's warehouse contents. Recomputed on save, never taken from the phone. Every list line needs a count (the
  screen offers "save as 0"); extra products (not blocked, not on the list) get expected 0.
- Stored only by `module_4/kar_inventory_service.py` in `StockMaster_kar_inventory` + `_line` (snapshots of kar number,
  team, product names; season = the trip's, else the last open one; migration `c8b774a60c98`). **Informative only: never
  changes stock, tags or trips.** Public endpoints in `module_4/public_kar_inventory_router.py`; errors under
  `stockMaster.publicInventory.errors.<code>`. Screens in `components/module-4/public-kar-inventory/` (token kept per kar in
  sessionStorage, `kar-inventory-token.ts`).
- **Staff screen** "Kar inventarissen" (`/modules/module-4/kar-inventories`, screen `stockmaster.karinventories`, view only,
  `module_4/kar_inventory_router.py`: list per season, detail, Excel of the shown ids).

## KarTracker (module-2): Leveringsvolgorde

- `KarTracker_afleverlocaties.terrein_positie` is an **integer**: the location's position in the one delivery tour
  across the ground (1 = delivered first, NULL = not in the tour; converted from free text in migration
  `c4d8e2f6a913`, non-numeric values became NULL). Not to be confused with `KarTracker_distributiepunten.terrein_positie`,
  which is still free text.
- Set on the "Leveringsvolgorde" screen (`/modules/module-2/actions/delivery-order`, screen key
  `kartracker.leveringsvolgorde`, `components/module-2/delivery-order-screen.tsx`, drag and drop with `@dnd-kit`):
  left = the tour, right = active locations without a position. `PUT /delivery-order` saves the whole tour through
  `module_2/delivery_order_service.py` (ids → 1..n, every other *active* location → NULL; inactive ones untouched).
  The Afleverlocatie form and XLSX import can also set it (a whole number ≥ 1).
- Each row shows the saved value next to the new number ("was 3" / "nieuw" / "wordt leeg"); **Kaart** opens
  `components/module-2/delivery-order-map.tsx` (ground plan + numbered badges "5 (was 3)", hover tooltip = name,
  dashed route 1 → n) built on `kar-map-leaflet.tsx`, whose `KarMapPin` now has optional `label`/`tooltip`/
  `zIndexOffset` and the map an optional `route`. `/groundplans` is also readable with `kartracker.leveringsvolgorde`.

## KarTracker (module-2): Planningsanalyses

Sidebar group (between "Acties" and "Masterdata") for analyses of what has to be organised before/during/after the
festival; route prefix `/modules/module-2/planning-analyses/`.

- **Initiële leverplanning** (`initial-delivery`, screen key `kartracker.initieleleverplanning`,
  `module_2/initial_delivery_service.py`, `GET /initial-delivery?season_id=`, `components/module-2/initial-delivery-screen.tsx`):
  grouped per distributiepunt (ordered by its first location in the tour), then per afleverlocatie in `terrein_positie`
  order (no position last), the karren delivered there at the start. A kar's
  initial location = the Plan a kar location of its **team's first festival** of the season (earliest picked in
  Altsien Select via `festivals_by_team`, else the season's first active festival). Karren without a team or whose
  team planned nothing there are left out. Totals per distributiepunt + overall. Read-only, follows the header's season.
  Filter row under the headings (Status dropdown + text per column, client-side; selection actions only touch the shown
  karren, hidden ticked ones stay ticked). Kar lines have checkboxes (Shift-click = range, group rows tick all their karren); **Print leverplanning**
  (`POST /initial-delivery/print`, `module_2/delivery_planning_pdf.py`) makes a landscape PDF of the ticked karren per
  distributiepunt ("Ophalen bij") with a "Geleverd" box, re-deriving the planning server-side and keeping only the ids.
  Optional **map page**: drawn server-side (no tiles) on the ground plan holding most points, lat/lng → page via
  Web-Mercator over the plan's bounds (as Leaflet stretches it), zoomed to the printed points (padding, min 150 m, plan
  image cropped to the view); points outside the plan / without coordinates are listed.
- **Verplaatsingen tussen festivals** (`kar-moves`, screen key `kartracker.karverplaatsingen`,
  `module_2/kar_moves_service.py`, `GET /kar-moves?season_id=&from_festival_id=&to_festival_id=`,
  `components/module-2/kar-moves-screen.tsx`): for a chosen festival A → B (dropdowns, default the first two; without a
  pair the response only holds the festivals) the karren whose team plays both (picks, or every festival while it picked
  none), has a Plan a kar location at both, and those differ. Grouped per **pick-up location** (the one at A) in tour
  order; each kar row has its `to_location`. Same filters/checkboxes as above; **Print verplaatsingen**
  (`POST /kar-moves/print`, `module_2/kar_moves_pdf.py`) = per pick-up location with a "Verplaatst" box, optional map
  with purple pick-up / green destination badges (tour position, letters for no position) and an arrow per move with
  its kar count. The map's ground-plan view (pick plan, zoom, background) is shared via `_draw_map_view` in
  `delivery_planning_pdf.py`.
- **Speciale levertoeren-planning** (`special-tours`, screen key `kartracker.levertoerplanning`,
  `module_2/special_tour_planning_service.py`, `GET /special-tour-planning?season_id=&festival_id=&tour_ids=…`,
  `components/module-2/special-tour-planning-screen.tsx`): Festival dropdown (default the first) + multi-select of
  active tours; lists the karren of teams linked to any chosen tour that play the festival, at their Plan a kar location
  there. **No distributiepunten** (the tour passes by the karren): a flat list of stops (`SpecialTourStop`) in tour order
  (`terrein_positie`, then the rest by name) numbered `stop` 1..n, so every stop gets a map badge even without a
  position. A kar on two chosen tours appears once with both in `tour_names`. **Print**
  (`POST /special-tour-planning/print`, `module_2/special_tour_pdf.py`, reusing the house style/map helpers of
  `delivery_planning_pdf.py`): one table (Stop, location, karren, Levertoer, "Geleverd" box) + optional route map with
  a numbered badge per stop and the dashed route 1 → n; printing a subset keeps the screen's stop numbers.

## KarTracker (module-2): Karcode

**The stored code is the truth**: `KarTracker_karren.kar_code` (String 20, typed by hand on KarManagement or via the kar
Excel column `kar_code`, empty cell = unchanged) is what the Ploegfiche (screen, PDF, so the ploegfiche mail) prints. The
Karblad deliberately does **not** print it (it hangs on the kar). Migration `e5b9c3d7a428` filled every kar once with the formula (`formula_code_for_kar_nummer`: digits
of the kar number, B001 → 1); changing the formula never changes stored codes — only the Karcode Simulator uses it.
`PUT /karren` without `kar_code` keeps the stored code.

The kar locks' code follows from the kar number via one admin-editable formula (single row `KarTracker_settings`,
id 1, seeded `LEFT(kar*500+3118; 4)` → kar 36 = 2111). **Only `module_2/karcode_formula.py` checks/computes it**:
Excel-like (`kar`, + - * / ^, LEFT/RIGHT/MID/MOD/INT/ROUND/ABS, `;` between arguments, `,` or `.` decimals),
parsed with `ast` and walked over a whitelist — never `eval`. Errors = `KarcodeError` → HTTP 400 `"code|param"`,
translated under `karTracker.karcode.errors.<code>` (a new code needs both languages). Endpoints in their own
`module_2/karcode_router.py` (included in `main.py`): `GET /karcode?kar=` (screen `kartracker.karcodesimulator`;
never returns the formula), `GET /settings` + `POST /settings/karcode/preview` (`kartracker.settings` view) and
`PUT /settings/karcode` (edit). Screens: "Karcode Simulator" under Acties (calculator UI,
`components/module-2/karcode-simulator.tsx`) and "Karcode formule" in the sidebar's **Instellingen** group
(`kartracker-settings.tsx`), where future KarTracker-wide settings go too. The calculator itself is
`components/module-2/karcode-calculator.tsx` (`variant="desktop"|"phone"`), shared by the web screen and the phone
page `/m/module-2/karcode` (same screen right); both can fill the kar number by scanning the kar's QR code
(`qr-scanner.tsx`; only the **last 3 digits** of the scanned value are used) or by typing it.

## KarTracker (module-2): Speciale levertoeren

KarTracker master data `KarTracker_speciale_levertoeren` (name unique, description, active; screen
`kartracker.specialelevertoeren`, `/modules/module-2/special-tours`, `components/module-2/special-tour-management.tsx`,
`/special-tours` CRUD): tours such as "Kleine wastoer"/"Ijsblokken" that regularly pass by teams. Teams are linked on
MasterData's team fiche (**Levertoeren** multi-select, `MasterData_team_speciale_levertoer`, `special_tour_ids` on the
team endpoints; `PUT /teams` without the field keeps the links). The fiche reads the options from module-9's own
`GET /special-tours` (gated by `masterdata.teams`), so managing teams needs no KarTracker rights. Deleting a tour that
is still linked is refused (400) — deactivate it instead (inactive tours stay on teams already linked but can't be picked).

## Atelier (module-5) and Walkies (module-6)

Started as a **shell**: tile with name + icon (`Shirt` / custom `components/icons/walkie-talkie-icon.tsx`), a KPI
landing page, and Access Rights (Roles/Users) with the same custom-roles-per-screen system as StockMaster
(`Atelier_*` / `Walkies_*` tables, screens in `module_5/screens.py` / `module_6/screens.py`). Translations under
`atelier.*` / `walkies.*`, help manuals in `app/help/content/module_5|6/` (Atelier with screenshots, Walkies without). Walkies is still
only that shell.

- **Atelier**: the atelier team hands out festival work clothing (T-shirts, hoodies for VIP, RW terras, …) at the
  start of a shift and takes **everything** back afterwards. Workers are **not** in a database: they belong to a
  ploeg (MasterData team), whose package says what they get. Built in blocks (see `docs/work-history.md`,
  2026-10-25): **1 Masterdata (done)**, **2 reservations (done)**, **3 stock (done**: receipt without purchase orders or suppliers, own washing, write-off, count; one atelier store), **4 counter desk (done)**:
  hand-out/return (first name, family name, email, bracelet number typed), **5 wristband scans via webhook (done)**, **6 RFID per piece
  (started: the Raspberry Pi app, see "RWCrew Pi" below)**.
- **Atelier masterdata** (sidebar group "Masterdata", `/modules/module-5/masterdata/...`, screens
  `atelier.articles|sizes|dataupload`, endpoints in `module_5/masterdata_router.py`):
  `Atelier_size` = name + **fit** (`women`/`men`/`unisex`, fixed list `FITS` in the model, unique name+fit; seeded
  XS–XXL per fit + OneSize·Unisex); `Atelier_article` (own catalogue, not StockMaster products; unique code,
  picture like products, `is_tag_managed` for block 6); `Atelier_article_size` = the stock-keeping unit of the later
  blocks (managed from the article form's size checklist, with `size_share_pct`; unticking deletes it — refuse once
  stock exists). Used things are deactivated, not deleted (400). XLSX per table in `module_5/xlsx_imports.py`
  (sizes/articles/return statuses by `id`, falling back to name+fit / code / name when the id is blank or unknown here — so an export from another environment imports cleanly; the rest by natural key; columns left out stay unchanged). The module has its own season
  dropdown (`atelier-season-select.tsx`, `?season=`) and `GET /seasons`; `/articles` is readable with the
  Reservaties screen too.
- **Atelier reservations** (sidebar group "Reservaties", `/modules/module-5/reservations[/preparation]`, screens
  `atelier.reservations|preparation`, endpoints in `module_5/reservation_router.py`): **one page per festival** with,
  per team, the **number of persons and its package** — `Atelier_reservation` (festival + team: persons, note,
  changer = session user) + `Atelier_reservation_line` (article × pieces per person; **size is chosen at the
  desk**). The package is **per festival** (there is no season package any more: the old Ploegpakketten screen and
  `Atelier_team_package` were removed on 2026-10-25, migration `d7f1b4c8e253` copied them onto every festival of
  their season). Written only by `module_5/reservation_service.py`; a reservation without persons, note and
  package is deleted. Every active team is listed (`offered_teams`), each with `festivals_picked`
  (`reservation_service.festival_progress`: the season's festivals the team picked in Altsien Select via
  `festivals_by_team`, done = persons > 0; empty = "geen selectie") shown as "Festivals ingevuld x / y". "Copy from last year" =
  `previous_festival` (previous season, same `normalize_festival_name`): package lines added/updated (never
  removed, inactive articles skipped), persons only while still 0. The team works **every festival day** and
  returns the clothing **every evening**, so each day needs persons × package. `preparation_service.py` computes
  (nothing stored) store totals per article with a size estimate from `Atelier_article_size.size_share_pct` (must
  total 100% per article, else equal split; largest-remainder rounding) and a bundle per team. Picklist PDF per day
  (`picklist_pdf.py`, StockMaster's house style via `StockMasterPDF(accent_color=…, brand="Atelier")`). Festival
  choice travels in `?festival=` (`atelier-festival-select.tsx`). History/lock of changed reservations: not decided.
  The KPI's reservation stats list per festival `teams_missing` (`_forgotten_teams`): active teams with persons at
  another festival of the season but no persons and no note here; 0 persons + a note silences it.
- **Atelier stock** (sidebar group "Stock", `/modules/module-5/stock[/receipt|wash|write-off|count|bookings|order-needs]`,
  screens `atelier.stock|receipt|wash|writeoff|count|bookings|orderneeds`, endpoints in `module_5/stock_router.py`):
  pieces per **article size** and status `available` / `to_wash` / `handed_out` (the last one for block 4). **Only
  `module_5/stock_service.py` changes stock** — the StockMaster pattern: `Atelier_stock_document` (`AT-<year>-<id>`,
  types receipt/washed/write_off/count/reversal) + `Atelier_stock_movement` (from/to status, NULL = outside) +
  `Atelier_stock_balance` (row per article size + status, locked `FOR UPDATE`, emptied rows deleted, never negative);
  never commits; `StockError("code", *params)` → detail `"code|param|…"`, translated under `atelier.stock.errors.<code>`
  (a status code as parameter is shown translated); booker = session user; undo = `reverse_document` (needs "edit" on
  `atelier.bookings`). Write-off reasons are a fixed list (damaged/lost/not_returned/other, other needs a note).
  `stock_needs.py`: overview, **Te bestellen** (per article size the highest festival-day size estimate of the season
  − owned), min-stock alerts (`Atelier_article_size.min_stock`, orange banner `atelier-min-stock-banner.tsx` in the
  layout, re-counted on `ATELIER_STOCK_CHANGED_EVENT`). Voorbereiden's size estimates carry `available`/`owned` (red =
  not owned, orange = still in the wash). An article size with stock bookings can't be unticked and its article can't
  be deleted. PDFs in `module_5/stock_pdfs.py` (Boekingsbon, Bestellijst).
  **Wash statistics** on the KPI page (`module_5/wash_stats.py`, `GET /stock/wash-stats?season_id=`, KPI right,
  `wash-stats-section.tsx`): posted `washed` documents per Belgian day, nothing stored; a day belongs to the season of the
  latest festival started on/before it and to the festival running that day, else the season's "no festival" group.
- **Atelier counter desk** (sidebar group "Balie", `/modules/module-5/desk[/open]`, screens `atelier.desk|open|returnissues`,
  endpoints in `module_5/desk_router.py`, rules in `module_5/desk_service.py` — the only writer of `Atelier_person`
  (**first name + family name** = the person's key, `name_key` "first|last" lowercase unique; email **optional**, not
  unique; the wristband number is **per festival** in `Atelier_person_bracelet`, unique within the festival), `Atelier_handout` (person, festival, team, day, status
  open/returned/cancelled, its `hand_out` stock document) and `Atelier_handout_line` (article + article size,
  `returned_at` + return document)). **Every transaction starts with the choice "Ophalen" / "Terugbrengen"** (big
  buttons, keys 1/2) in `desk-screen.tsx`, then back to that choice. Ophalen: only articles of the team's package for
  that festival, **1 piece each** (size picked at the desk), never an article the person still has out. **The reservation's persons are a limit** (2026-11-07):
  once as many people of the team at the festival **hold clothing now** (`desk_service.persons_holding`, open pick-ups)
  as reserved, a new person gets `reservation_full|team|holding|reserved`. Only a user with **edit** on `atelier.desk`
  may override (`confirm_over_reservation`, checked in `desk_router`, else 403 `reservation_full_no_right`); back-dated
  loads are not limited. `DeskContextResponse.persons_holding` drives the "x / y" counter (web + Pi). Terugbrengen: tick what's back (partial allowed) → `return` (handed out → to
  wash). `stock_service.hand_out` / `return_pieces`; those documents can't be undone on Boekingen (`use_desk`) — only
  "Uitgifte annuleren" (`edit` on the desk, while nothing was returned). **Package quantity is always 1**
  (`reservation_service.PACKAGE_QUANTITY`, forced on save/copy/XLSX; migration `f9b3d6e1a475` set existing lines to 1;
  the field stays visible, read-only). "Openstaand" = open pieces grouped per team → person → piece (client-side), with an "Inname" button per person (only
  with desk view + create) opening the desk's `components/module-5/desk-return-form.tsx` in a dialog;
  a piece that never comes back is written off there ("Afboeken", `POST /desk/persons/{id}/write-off`, `create` on `atelier.writeoff`,
  `desk_service.write_off_person_lines`, `components/module-5/desk-write-off-dialog.tsx`): handed out → outside, reason `not_returned`, no mail; it closes the
  line through `returned_at` + `return_document_id` (the write-off document), and `reverse_document` refuses it (`desk_write_off`).
  A known person with another wristband at this festival: `bracelet_differs|number|name` unless `confirm_new_bracelet` is sent (the desk asks; same name = one person). The bracelet field has a camera button (`QrScanDialog`; the QR code's whole text is the number).
  **Return status** per piece (optional, only a remark, not in the mail; stock still goes to wash):
  `Atelier_return_status` (screen `atelier.returnstatuses`, `/masterdata/return-statuses`, used = deactivate only),
  `Atelier_handout_line.return_status_id`, set through `line_statuses` on the return; overview "Retourproblemen"
  (`atelier.returnissues`, `/desk/return-issues`, read-only). Both also offer **"Alle festivals"** (`?festival=all`, `allowAll` on `atelier-festival-select.tsx`): the API's `season_id` loads the whole season, with a Festival column (also in the Excel) whose filter narrows it to one festival. Openstaand and Retourproblemen have an **Excel** button: the screen POSTs its shown
  `line_ids` (the column filters are client-side) to `/desk/open/export` / `/desk/return-issues/export` (`module_5/desk_export.py`,
  no email column, values that look like a formula stay text). Openstaand and Reservaties have a text filter above every column
  (`components/module-5/column-filters.tsx`).
  **Emails are shown masked** on the desk, Openstaand has no email column at all (`lib/mask-email.ts`, `fr***@gm***.com`, GDPR); the database,
  API and mails keep the full address. Ophalen shows a filled-in address read-only with "Wijzig" (empties the box).
  `GET /desk/context` also returns `team_responsibles` (MasterData's Ploegverantwoordelijken of the festival's season, via
  `module_9/team_responsible_service.list_team_responsibles`), shown behind a contact icon on Ophalen (only on click).
- **Atelier desk mails**: after Ophalen (`POST /desk/handouts`) and after Terugbrengen the person gets the "Uitgifte" /
  "Inname" mail (only with an email; `module_5/notifications.py` `queue_desk_mail`, background task like module-3). The
  desk returns through **`POST /desk/persons/{id}/return`** (`desk_service.return_person_lines`, all ticked pieces of
  every pick-up in one transaction = one mail); the per-handout `/desk/handouts/{id}/return` stays but never mails.
  Texts in `Atelier_mail_template` (key `handout`/`return`, subject, body, active; seeded by migration `c8e2a5f1d394`,
  defaults also in `DEFAULT_TEMPLATES`), edited on "Instellingen > E-mails" (screen `atelier.mailtemplates`,
  `module_5/mail_template_router.py`, test mail to yourself). Placeholders = `notifications.PLACEHOLDERS`
  ({voornaam} {familienaam} {ploeg} {festival} {dag} {polsband} {stuks} {openstaand}); an unknown one is refused
  (`unknown_placeholder|name`). A new placeholder needs a value in `desk_values`, `EXAMPLE_VALUES` and a translation.
- **Atelier wristband scans** (block 5): the scans are shared, see "Scans (module-1)". Atelier's side: the desk screen picks
  its scanner (localStorage via `useSyncExternalStore`, `components/module-5/desk-scanner.ts`) and polls `GET /desk/scans?device_id=&season_id=`
  every 2 s; a waiting scan shows as a card on the Ophalen/Terugbrengen choice and pre-fills the transaction, which sends `scan_id`
  (marked used, `used_by_module`). The sidebar shows a pulsing red count next to "Uitgifte & inname" (`desk-scan-alert.tsx`, polls every
  5 s for that scanner, or every scanner when the browser has none). Global switch `Atelier_settings.wristband_required` (`bracelet_required`)
  on `atelier.settings`; test scans on **`atelier.scantest`**.
- **Walkies**: management of the festival's walkie-talkies. Content follows in phase 2; for now also Instellingen > Test-scan
  (`walkies.scantest`). Its counter must add its rule to `wristband/visibility.py` `counter_rules` and call `waiting_scans` with its teams.
- A new screen = a `ScreenDefinition`, a sidebar link (`components/module-5|6/*-sidebar.tsx`), a line in the
  `*-help.ts` routes + a manual chapter, and an entry in the landing page's `FALLBACK_SCREENS`.

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
- **Festivals per team** are written only by `module_9/team_festival_service.py` (rules: only active festivals of
  the year, unticking also deletes the Plan a kar location and re-opens `afleverlocaties`), used by wizard step 1,
  the XLSX import and MasterData's **Festivals per ploeg** grid (Teams > Festivals per ploeg,
  `/modules/module-9/teams/festivals`, screen `masterdata.team-festivals`, `components/module-9/team-festival-grid.tsx`):
  all teams × the year's festivals, edited as a draft with one Save (`PUT /team-festivals/grid`, closed year → 403
  `season_closed`), "Kopieer van vorig jaar" (`GET /team-festivals/previous`, a proposal only, added to the draft).
  `previous_season_of` / `normalize_festival_name` live in that service (re-exported by `module_8/previous_season.py`).
- **Mails**: every Altsien Select mail goes through `module_8/notifications.py` `build_altsien_mail`, which always adds
  the CC list (`AltsienSelect_settings.cc_addresses`). Texts in `AltsienSelect_mail_template` (key `ploegfiche`),
  edited on Instellingen > E-mails (screen `altsienselect.mailtemplates`, `module_8/mail_template_router.py`), with the
  template editor shared with Atelier (`components/shared/mail-templates/`, placeholder helpers in
  `app/shared/mail_template.py`). When completing a step finishes the wizard, a popup offers the Ploegfiche PDF by mail
  (`POST /wizard/{team}/ploegfiche/mail`, to the session user + CC; also the "PDF mailen" button in the all-done banner).
- **Adding a wizard step**: add a `StepDefinition` in `backend/app/modules/module_8/steps.py` (optional
  completion check), a component in `frontend/src/components/module-8/wizard/steps/` registered in its
  `index.ts` (unknown keys fall back to a placeholder), translations under `altsienSelect.steps.<key>`,
  and optionally a section in `module_8/ploegfiche_pdf.py`. Progress is keyed by string: no migration.
- **Copy from last season**: steps listed in `COPYABLE_STEPS` (`module_8/previous_season.py`) get a panel
  above them with last season's values line by line (checkbox each, select all, "Copy"). "Last season" is the
  season whose name sorts right before the current one; festivals are matched by name ignoring case, 4-digit
  years and punctuation. Copying only adds/updates, never removes and never marks the step done. Offered on
  festivals, delivery locations, team leads and special requests (products has its own per-kar copy, see below).
- **Products** (step 4) = StockMaster's kar needs of the team's kars, written only through
  `module_4/requirement_service.py`. Module-8 serves its own endpoints for it (`/wizard/{team}/products/...`,
  `/products-import`, `/products/{id}/image`) gated by the wizard screen, team scope and season lock, so a Kernlid
  needs no StockMaster rights; StockMaster error codes pass through unchanged. The UI is the same
  `components/module-4/kar-requirements-list.tsx` as StockMaster's "Benodigdheden" screen (each passes its own
  `KarRequirementsApi`); its per-kar "copy from last season" replaces `COPYABLE_STEPS`. Done = at least one line on
  one of the team's kars; emptying every list un-marks the step. Ploegfiche (screen + PDF) lists them per kar.
- KarTracker's **Plan een kar** (`components/module-2/plan-kar-screen.tsx`) opens on a per-kar overview
  (`GET /plan-kar/overview`, kars of active teams, "x/y festivals" per team); `?team=<id>` opens the team's matrix.
  Both count only the festivals the team picked in the wizard (`MasterData_team_festival`), falling back to every
  active festival while it picked none (`module_2/plan_kar_service.py` `festivals_for_team`).
- There is **no walkie-talkies step** (removed 2026-11-07, migration `d2a7c4e9b136` deleted its progress rows):
  walkie-talkies are not managed in Altsien Select.
- **Ploegverantwoordelijken** (team leads, per team + season, not RWCrew users) live in MasterData's
  `MasterData_team_responsible`, managed on module-9's `masterdata.team-responsibles` screen (Teams >
  Ploegverantwoordelijken) *and* by wizard step `ploegverantwoordelijken` (step 3, needs ≥1 person) — both
  write through `module_9/team_responsible_service.py`. No module-8 copy of the data.

## Scans (module-1): wristbands

TagScan was renamed **Scans** (2026-11-01, display name only: the key `module-1`, URLs, `tagscan.*` screen keys, `Tagscan_*` tables and
`Tagscan*` code names stay). It has two parts under one set of Roles/Users: **RFID tags** (below) and **Wristbands (QR)**, screens
`tagscan.wristband-files|scans|scanners|test`, routes `/modules/module-1/wristbands/...`. Wristband scans are shared by every module with a
counter, so their code is in **`app/modules/wristband/`**, not in a module:

- `POST /api/public/wristband-scan` (`webhook_router.py`, body read raw): the wristband company posts one JSON message per scan. Its `token` must be
  this environment's token, generated on the module's Settings screen (`webhook_token.py`, `POST`/`DELETE /wristband/settings/token`, edit on
  `tagscan.settings`, `wristband-settings-card.tsx`): `wristband_<random>`, shown once, only its SHA-256 stored in `Tagscan_settings` (fast, this runs on
  every scan; fine for a random key). No token = everything refused. The company connects from May 2027. The explanation for them is the manual
  chapter `wristband-integration`, opened as a PDF from that card: never put a token or server address in it. Manual Markdown has ``` code blocks.
- `scan_service.process_message` is the only writer of `Wristband_scan` / `Wristband_scanner`: it logs **every** message (status new/used/
  dismissed/ignored/refused + detail + raw), maps `data.device.id` → scanner (auto-registered), `data.id` → wristband number,
  `data.person.first_name/last_name`, `data.attending_group.name` → team (`match_team`: name, then **team alias**, ignoring case), optional
  email/size; only `event = crew_participation` becomes `new`.
- **The row is made immediately** (a counter polls every 2 s, it can't wait for a file scan like the CSVs), and the message is also written as
  a `.json` file by `json_files.py`: `<wristband_source_dir>/YYYY-MM-DD/<HHMMSS>_<scan id>[_test].json` (Belgian day; Docker volume
  `wristband_data`, `WRISTBAND_SOURCE_DIR`). A failed write is logged and never loses the scan; `unreadable`/`bad_token` messages get no file, so
  the public address can't fill the disk. Deleting a file keeps its row, as with the CSVs. Files aren't cleaned up automatically.
- **Which counter shows a scan** (`visibility.py`): a team normally has Atelier *or* Walkies products, so a counter only shows teams with a
  reservation with a package at **any festival of the season** (`?season_id=`, default the last open one), plus scans with no matched team (they
  mustn't get stuck; the desk card warns and the person picks the team). Others stay `new`, only visible in Scans with "at no counter". One status
  per scan: the first counter to use it wins.
- **Test scans** from Scans, Atelier and Walkies: `register_scan_test_routes` (`test_routes.py`, same idea as `register_help_route`) adds
  `/wristband-test/{scanners,teams,log,send}` to each router with that module's own right; UI `components/shared/wristband/scan-test.tsx`
  (`moduleKey` prop, `wristbandTestApi` in `api.ts`). Same processing without token, `source = "test"`; `visible_at` says which counter shows it.
- `module_1/wristband_router.py` (`/api/modules/module-1/wristband/...`): JSON file browser (`file_browser.py`'s `*_under` helpers on another
  root, same traversal check; UI = `file-browser.tsx` with `api` + `messagesNamespace` props), scans table with filters, scanner labels, and
  `/settings` (webhook address + token state, shown on the module's Settings screen). Translations under `wristband.*`.

**Team aliases** (MasterData): `MasterData_team_alias`, written only by `module_9/team_alias_service.py`. Other names of a team in outside
applications, on the team fiche and in the Teams XLSX (`aliases` column, `;`-separated, missing column = unchanged); `aliases` left out of
`PUT /teams` keeps them. An alias may not be another team's alias or name (400).

## RWCrew Pi (Raspberry Pi app, separate repo `RWRaspiTagScanner`)

A stand-alone PySide6/QML touch app (7" 800×480, Chafon CF-E714 UHF reader) in the **separate repo**
`RWRaspiTagScanner` (`rwpi/`; the old CSV app was removed on 2026-11-09), so only Pi code goes to a Pi (updates = GitHub
Release, `update_check.sh` restarts `rwcrew-pi.service`). Modules: **StockMaster** (module-4, teal, see "StockMaster
(module-4)": seven booking tiles on one controller `modules/stockmaster/transaction.py` + `TransactionScreen.qml`,
Tags koppelen, EPC schrijven with the reader's `singleTag`/`writeEpc`/`writeData` + `toolResult`) and **Atelier**. It works **live on RWCrew's data through the normal HTTPS API** — never a direct database connection
(Postgres only listens on 127.0.0.1, and the rules live in the services). Built 2026-11-05, see `docs/work-history.md`.

- **Login = the operator's own account**: `POST /api/auth/token` (client `"pi"` in the login history) gives the same JWTs
  in the body; the Pi sends `Authorization: Bearer <access>` (`landing/deps.py get_current_user` reads the Bearer header
  before the cookie) and renews with `POST /api/auth/token/refresh` (body, rotated like the cookie) / `token/logout`. Same
  15 min / 6 h limits, same rights: landing tiles = module access, Atelier screens = the user's Atelier role.
- **RFID per piece (Atelier block 6)**: `Tagscan_rfid_tag.atelier_article_size_id` (what the piece is) and
  `Atelier_handout_line.rfid_tag_id` (which piece went out; migration `b6e2d9f4a817`). Only
  `module_5/rfid_service.py` links tags (`POST /rfid/assign`, screen **`atelier.tags`**, Pi-only "RFID-tags koppelen") and
  resolves read EPCs (`POST /rfid/resolve`: unknown / not_atelier / inactive / piece + who has it out). A tag is an Atelier
  piece **or** a StockMaster product/kar, never both (assign refuses, TagScan's tag PUT says `tag_is_atelier_piece`, its
  Assignment processing leaves such a tag alone). Stock stays counted per article size; the tag adds traceability.
- **Desk on the Pi** reuses the desk endpoints: `HandoutLineInput.rfid_tag_id` (checked by
  `rfid_service.check_handout_tags`: exactly that size, not out), `DeskOpenLine.epc`, the person-level return. Wristband
  scans come from the Scans webhook as on the web desk (`/desk/scanners`, `/desk/scans`). The Pi's review rules
  (`rwpi/modules/atelier/review.py`) only explain; the server decides. TagManagement shows the piece read-only
  (`RfidTagResponse.atelier_piece`).
- **Tag trace (2026-11-06)**: Scans' Tagbeheer (`Tagscan_rfid_tag`) is the reference for every tag; every Pi action
  sends `reader {name, location}` (the Pi's scanner name/location) and `rfid_service.touch` notes it on the tag
  (`last_read_at`, `last_reader_id`, `last_location`; linking also writes `notes_1` when empty). A hand-out line keeps
  `handout_epc` (snapshot, survives deleting/relinking the tag) and, on a Pi return, `return_rfid_tag_id` + `return_epc`
  (`ReturnRequest.line_tags`, checked by `check_return_tags`: same **article**, error `tag_article_mismatch`);
  `Atelier_handout.source` / `Atelier_handout_line.return_source` = `web` | `pi` (migration `c7f3a1e8d295`).
  `GET /rfid/history?epc=` (`rfid_service.history`) feeds the **Tag-historiek** screen (`atelier.taghistory`,
  `/modules/module-5/desk/tag-history`, `components/module-5/tag-history.tsx`, `EpcLink` used by the EPC column on
  Openstaand and Retourproblemen and in their Excel).
- **Massa-inname (2026-11-08)**: third Atelier tile on the Pi (`rwpi/modules/atelier/mass_return.py`,
  `MassReturnScreen.qml`, grouping in `review.py` `review_mass_return`): a team's box of dirty clothing is read at once,
  a big number shows the tags in the box, the pieces are listed per person who has them out. Bevestigen →
  `POST /desk/mass-return` (`desk_service.mass_return`, screen **`atelier.massreturn`** "create", Pi-only like
  `atelier.tags`): one transaction, `return_person_lines` per person, one Inname mail per person. **Any** tag that isn't
  a handed-out piece refuses the whole box (`mass_return_blocked|n`); max 500 tags (`MASS_RETURN_MAX_EPCS`).
- **Stock and tags**: Atelier's stock overview shows per size `tagged` (active tags, `rfid_service.tagged_counts`,
  also used by the Pi's article list) and `untagged` (owned − tagged, ≥ 0).
- **Pi details**: emails are masked in Python before they reach QML (`rwpi/shared/mask_email.py`, a port of
  `lib/mask-email.ts`; the full scan email stays in `AtelierDesk._scan_emails`, sent only with the booking). Tags
  koppelen has a checkbox per linkable tag (ticked by default; `StateRow.checkable`).
- **Pi settings / history**: the settings screen has the old app's reader tools (connect/disconnect with baud, reader
  info, RF power kept on the reader, antennas 1–4, activity + communication log via `ReaderBase` in
  `rwpi/hardware/rfid/reader.py`) and the scanner name + location (`config.scanner()`, default = the old app's scanner
  name). `rwpi/shared/history.py` keeps the Pi's own log (`~/.local/state/rwcrew-pi/history.jsonl`, 90 days) of every
  Ophalen/Terugbrengen/Koppelen/StockMaster booking (`stock`, with `action`, `kar`, `count`)/EPC write (`write`) incl.
  refused and offline ones, shown on `HistoryScreen.qml` (header clock icon).
  Gotchas: QML screen switches from inside a signal handler of the screen being destroyed go through `Qt.callLater`;
  PySide6 `Property` with notify must be declared on the class that declares the signal (not in a subclass), else
  random crashes. The reader is shared: `shared/tag_reading.py` `TagCollector` only stops it when it started it last,
  and StockMaster's screens leave with a ticket (`enter` → `leaveScreen(ticket)`) so a closing screen can't stop the
  next one. Test drivers that drive the app with a Python `QTimer` must keep their driver object referenced (an
  unreferenced one is garbage-collected mid-run → Qt access violation / hang; `tools/screenshots.py` keeps `demo`).
- **Pi structure**: `rwpi/api` (client), `hardware/rfid` + `hardware/gpio` (buzzer/LEDs/confirm button, gpiozero;
  no-ops on a PC), `shared/` (session, i18n nl/en, icons via an image provider — no shader effects), `modules/registry.py`
  (tiles) + `modules/<module>/` controllers, `qml/` screens. New Pi screens (Wassen, Ontvangst…) = controller + QML + texts
  + a tile; a new Atelier screen key also gets a manual chapter. Develop on a PC with
  `python -m rwpi --windowed --fake-reader --server http://127.0.0.1:8020`.

## TagScan action processing (module-1)

Every scanned CSV line (`Tagscan_line_data`) and file (`Tagscan_header_data`) has a `process_status`
(`new`/`loaded`/`cancelled`) + `process_comment` + `processed_at`, separate from the line's EPC-match `status`.
Lines start `new` at scan time; the file's status is derived from its lines
(`line_processing.refresh_header_process_status`: any `new` → `new`, all cancelled → `cancelled`, else `loaded`).

- `backend/app/modules/module_1/line_processing.py` `PROCESSABLE_ACTIONS` maps a lowercased CSV `Action` to its
  handler. Today only `assignment`: a **product is mandatory, chosen per file** in the dialog
  (`POST /line-data/pending/process` takes `files: [{header_data_id, product_id}]`); it creates the `RfidTag` with
  that product, fills the product in on a registered tag without one, and never changes a tag that already has a
  product. **Adding an action** = one `_process_<action>(db, line, context)` returning `(outcome, comment)` + a dict
  entry (extend `ProcessContext` for extra user input); lines with an action without a handler simply stay `new`.
- **`Book In` lines** (and the old app's other stock actions) are no longer waiting work: StockMaster books live on the
  RWCrew Pi (see "StockMaster (module-4)"). Such lines stay `new` like any action without a handler.
- Waiting lines (`new` + action with a handler) show as a banner in TagScan's own soft blue (`module-theme.ts`) above every TagScan screen
  (`components/module-1/pending-actions-banner.tsx`, rendered by the module layout); it opens
  `pending-actions-dialog.tsx` (process all / cancel one line with a required reason). Screens that create lines
  without navigating dispatch `PENDING_ACTIONS_CHANGED_EVENT` so the banner re-counts.
- **Automatic background Scan** (`module_1/auto_scan.py`): an asyncio task started in `main.py`'s lifespan runs
  `scan_unreaded_tags` every `auto_scan_interval_seconds` (default on, 60 s; set on TagScan's Settings screen,
  `Tagscan_settings`, `PUT /settings/auto-scan`). It ticks every 5 s and re-reads the settings, so changes apply
  without a restart. `SCAN_LOCK` stops it from running together with a manual Scan click. Relies on the backend
  being **one** uvicorn process per environment — if workers are ever added, move this to a single worker/cron.
  Ops switch `TAGSCAN_AUTO_SCAN_WORKER=false` keeps it from starting. Tests never run it (no lifespan).
- **Tag ↔ kar link**: `Tagscan_rfid_tag.kar_id` (optional FK to `KarTracker_karren`, `ON DELETE SET NULL`, several
  tags per kar allowed) is set on TagManagement's "Karnummer" dropdown (`GET /api/modules/module-1/kars`, gated by
  the tag-management screen, so no KarTracker rights needed) and the XLSX `kar_nummer` column. Groundwork for
  recognising a scanned RFID as a kar later. Lines snapshot it as `Tagscan_line_data.kar_nummer` (via `match_tag`,
  at scan time and on Synchro, like product/serial); Tag Headerdata shows its lines' distinct kar numbers
  (`kar_numbers_by_header`, computed, not stored). Both screens show it right after "Actie".
- Rows on Tag Headerdata/Tag Linedata are coloured by `process_status` (`components/module-1/process-status.ts`:
  orange new, green loaded, red cancelled). Lines that existed before this feature were backfilled as `loaded`.

## Mass test (loading last year's lists)

`backend/masstest/` (run from `backend/` with the venv) loads last year's lists, old Excel files in their own layout, through
the **normal API** as a real migration, on localhost → test → prod (`environments.py`). Every row that can't be loaded
becomes a line in an Excel issue report (description + proposed solution from `solutions.py`; I review the bugs and fill in
"Analysis"; confirmed bugs → changelog lines). The source lists and reports hold personal data: `--out` is refused inside
the repo.

- `python -m masstest convert <old.xlsx> --kind atelier-desk --out <dir>/load.xlsx` → the standard **load workbook**
  (one sheet per step, reviewed by a person; unreadable rows → `load-convert-issues.xlsx`). Converters live in
  `masstest/convert/` (registered in `CONVERTERS`).
- `python -m masstest run --env local|test|prod --load <dir>/load.xlsx --out <dir> [--dry-run] [--only Sheet]`: login
  (cookie), every step's **preflight** first (super admin, rights, lookups, settings: a blocker stops before any write),
  then the steps in `masstest/steps/__init__.py` `STEPS` order. `<out>/<env>/ledger.json` keys every source row, so a
  second run loads nothing twice. Calls > 2 s → performance issue. Prod needs `--confirm-production`, a prod dry run the
  same day and a typed confirmation of a database dump. Password from `MASSTEST_PASSWORD` or prompted, never stored.
- **Back-dating**: Atelier's desk and stock bookings accept an optional `booked_at` (super admin only,
  `stock_service.check_booked_at`; `backdate_not_allowed` / `backdate_in_future`): documents, pick-ups and returns keep
  that moment (doc number year = its Belgian year) and back-dated desk actions **never mail**.
- Screen check: `npm run mass-test:screens <out.json> [web address]` (`frontend/scripts/mass-test-screens.mjs`, Edge,
  `MASSTEST_EMAIL/PASSWORD/SEASON`) opens every Atelier screen per festival + the PDFs; `python -m masstest screens
  <out.json> --env … --out …` turns it into the same report.
- A new module = a converter + a step class (`sheet`, `module`, `preflight`, `run`; helpers in `steps/common.py`) + its
  error namespaces in `messages.py` + rules in `solutions.py`. Tests: `tests/masstest/` (a full run through an httpx
  transport into the TestClient).

## Module help manuals (PDF)

Each module can have a user manual, generated as PDF by the backend (`backend/app/help/`, fpdf2, module's own
accent colour). Every module with its own screens has one: Scans (module-1), KarTracker (module-2), Interventies
(module-3), StockMaster (module-4), Atelier (module-5), Walkies (module-6), Altsien Select (module-8) and MasterData (module-9).

- **Text** lives in `backend/app/help/content/<module_N>/{nl,en}.md` (small Markdown subset, see `content.py`):
  `## [topic | screen.key] Title` per chapter. A chapter is only in the PDF when the user may *view* that screen
  (no screen key = always shown). `tests/help/test_help.py` checks that keys exist, nl/en match and images exist.
- **Endpoint** `GET /api/modules/<module>/help/pdf?locale=&topic=`, added to a module's router with
  `register_help_route` (`app/help/routes.py`), passing its own module-access dependency + viewable-screens function.
- **Frontend**: `components/shared/module-help.tsx` — `ModuleHelpMenuLink` at the bottom of the module sidebar
  (whole manual) and `ScreenHelpButton` in the module layout (only the chapter of the open route, from the module's
  `<module>-help.ts` route → topic list).
- **Screenshots** in `content/<module_N>/images/`, made from localhost with `npm run help:screenshots [module-N]`
  (`frontend/scripts/help-screenshots.mjs`, playwright-core + the installed Edge, needs `HELP_SHOTS_EMAIL` /
  `HELP_SHOTS_PASSWORD` of a local login that sees every screen). Re-run it after a screen changes. Easiest login: the
  temporary user of `docs/handleiding/screenshot_user.py setup` (all modules, all rights; `cleanup` afterwards); while its
  `.screenshot-namen.json` exists, the script masks real names/emails/phones on the shots. Atelier's RWCrew Pi shots
  (`pi-*.png`) come from `RWRaspiTagScanner/tools/screenshots.py` (demo with fake people/EPCs that books on the local
  database: `pg_dump` it first and restore afterwards); run it before `help:screenshots`, whose `tag-history.png` uses
  the demo's first EPC.
- **The two handbooks** (`docs/RWCrew-Gebruikershandleiding.pdf`, `docs/RWCrew-Ontwikkelaarshandleiding-v2.pdf`) are HTML
  chapters in `docs/gebruikershandleiding/` and `docs/handleiding/`, built with their `build_pdf.py` (headless Edge);
  developer-handbook screenshots via `docs/handleiding/screenshots.py`. Update them when a module or screen is added.

## Outgoing email (Resend)

- `backend/app/core/mail.py` `send_email()` posts to Resend's HTTP API with `httpx` (no extra package). It
  never raises: errors are logged. With `RESEND_API_KEY`/`MAIL_FROM` empty (local dev, tests) it just logs a skip.
- Settings per environment in the server's `.env`: `RESEND_API_KEY`, `MAIL_FROM` (its domain must be verified
  in Resend via DNS), `APP_PUBLIC_URL` (link in mails), and `MAIL_SUBJECT_PREFIX` (e.g. `[TEST] ` on test).
  **Gotcha:** `docker-compose.prod.yml` passes the backend an explicit `environment:` list, so any new
  backend setting must be added there too (and to `.env.test/production.example`) — a value only in the
  server's `.env` never reaches the container. This is why the first test deploy sent no mail.
- **Interventions (module-3, formerly "Intervention Requests") new-request mail**: every new request — staff screen, public QR form
  *and* phone app — mails the active addresses of `InterventionRequests_mailing_recipient` with the
  delivery-note PDF attached (`module_3/notifications.py` `queue_new_request_mail`, sent as a FastAPI
  background task after the 201). The list is managed on "Instellingen > Mailinglijst"
  (screen key `interventionrequests.mailinglist`). A new create path must call `queue_new_request_mail` too;
  edits never mail.

## Phone section (PWA, `/m`)

The phone version of the app is a Progressive Web App served by the same Next.js frontend: `src/app/manifest.ts`
makes the site installable ("Add to Home Screen"), and the installed app opens `/m`, a separate section that
shows **only** the phone screens: login, module tiles, KarTracker (KarScan, Kar Planning, Kar Map, Karcode Simulator),
Interventies (Akties list/create/edit, KPI overzicht) and StockMaster (Spraaktelling; the microphone needs HTTPS too). No desktop sidebar/topbar, no delete, no PDFs.
This is the only phone app: there is no native (App Store / Play Store) app, no separate phone API, no Bearer
tokens (only the Raspberry Pi app uses Bearer, see "RWCrew Pi") and no separate release — a web deploy updates the phone app too. (A React Native/Expo app existed
until October 2026 and was removed entirely; only old login-history rows still mention it, see below.)

- **Organised per module, like the web app**: routes in `frontend/src/app/[locale]/m/` (`login/` outside,
  everything else under `(signed-in)/`, whose layout does the login check), one folder per module
  (`(signed-in)/module-2/`, `(signed-in)/module-3/`); screens in `src/components/phone/module-N/`; cross-module
  pieces (header, body, tiles, menu row, bottom tabs, notices) in `src/components/phone/shared/`.
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
- **Rule: every dropdown must have a search function, always, from the start.** This covers every new or changed
  dropdown, on desktop and phone (`size="phone"`), also short fixed lists — no exceptions, and never a plain `<select>`
  or a re-added `ui/select.tsx`/`PhoneSelect` (removed in PR_0019). A single choice uses `components/ui/searchable-select.tsx`
  (Base UI Combobox with a search box): `options=[{ value, label, disabled?, content? }]` (`label` is what's searched), optional
  `renderValue` when the button text differs from the label. Several values = `TagMultiSelect`; search-and-add-a-line = `Typeahead`.
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
