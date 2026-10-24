# Work history

One entry per plan that was accepted and carried out, newest on top. Rules and entry format: see
"Work history (plan log)" in `CLAUDE.md`.

## 2026-10-24 — Product master data moved from MasterData to StockMaster
**Request:** move MasterData's "Producten" group (Producten, Type, Magazijnen, Categorieën, Limieten) to StockMaster
under a new "Masterdata" submenu.
**Plan:** screens, endpoints and rights move to module-4, tables stay `MasterData_*`; sidebar nested as before
(Producten with the four lists indented); rights start fresh (new `stockmaster.*` screens unticked, old
`masterdata.*` product screens + grants deleted); product/lookup import/export and the product statistics move too;
TagScan and KarTracker read the lists from StockMaster's endpoints.
**Changes:** backend — new `module_4/product_masterdata_router.py` (CRUD, picture PUT/DELETE, XLSX import/export,
`GET /product-stats`, included in `main.py`), `module_4/product_stats.py`, the five `*_import.py` moved from module_9,
6 new screens in `module_4/screens.py`, the 5 removed from `module_9/screens.py`, endpoints/imports removed from
`module_9/router.py`, MasterData dashboard reduced to the seasons count (schema too), `ProductStats*` schemas; migration
`e6a1b4c8d235` (deletes the old MasterData screen rows and grants). Frontend — routes `module-4/masterdata/products/...`
and `masterdata/data-upload-download`, components moved to `components/module-4/` (`lookup-management.tsx` →
`components/shared/`, `DataTopicTile` extracted to `components/shared/data-topic-tile.tsx`), new
`product-data-upload-download.tsx` and `product-stats-section.tsx` (KPI page), StockMaster sidebar "Masterdata" group
(level-2 indent), MasterData sidebar/grid/dashboard trimmed, `api.ts` URLs → module-4, TagScan/KarTracker fetches and
TagScan's product link repointed, help routes, `FALLBACK_SCREENS`, nl/en texts moved to `stockMaster.*`. Help manual
chapters + 5 images moved to module_4 (new "Data Upload/Download" chapter), MasterData intro/overview updated;
screenshot script paths; `CLAUDE.md`; screen-key table in `docs/handleiding/.../07-deel-d-beheer-en-bijlagen.html`.
**Verification:** full backend suite green (product, lookup, upload, stats tests moved/split into `tests/modules/module_4/`;
the stock delete test now uses the module-4 endpoint); help tests 28 passed; `tsc --noEmit` clean apart from stale
`.next` route types of the removed module-9 pages; eslint clean; local `alembic upgrade head` applied and the screen
tables checked; backend restarted, new routes answer (redirect to login), old `/modules/module-9/products` is a 404.
**Notes:** after deploying, tick the new screens in StockMaster › Rollen (nobody has them yet; super admin passes).
Users of TagScan Tag management/Scanners and KarTracker Kar management need StockMaster access + view on the
product screens, or their product/type dropdowns stay empty. Screenshots for the moved chapters and MasterData's
overview should be re-made (`npm run help:screenshots module-4 module-9`). Not checked in a logged-in browser.

## 2026-10-24 — Speciale levertoeren-planning: stops instead of distributiepunten, working route map
**Request:** the PDF map showed nothing, and the list must not mention the distributiepunt.
**Plan:** (follow-up fix, no separate plan) cause: the map only badged locations with a Leveringsvolgorde position (just
1 of 4 in the real data; the rest were tiny grey dots, distributiepunten had no coordinates). The tour now has its own
stops 1..n (positioned first, then by name), each a numbered badge on the route; screen and PDF list the stops flat,
without distributiepunten.
**Changes:** `special_tour_planning_service.py` (flat `locations: SpecialTourStop[]` with `stop`); schema
`SpecialTourStop`; new `module_2/special_tour_pdf.py` (table + route map + legend, reusing `delivery_planning_pdf`
helpers and `kar_moves_pdf._badge`); print endpoint uses it. Reverted the earlier shared changes (`group_by_distributiepunt`
in `initial_delivery_service.py`, `_keep_selected_karren` in the router, the `special_tours` variant/column widths in
`delivery_planning_pdf.py`) back to the original code. Frontend `special-tour-planning-screen.tsx` (stop rows, "x stops"
instead of the per-distributiepunt pills), types, nl/en texts; help chapter nl/en; `CLAUDE.md`.
**Verification:** `test_special_tour_planning.py` updated (stop numbering incl. a location without position); module-2 +
help tests 174 + 28 passed; `tsc --noEmit` + eslint clean; PDF rendered from the real local data (Parklife 2026, 4 stops)
and checked: all 4 badges + route on the map, no distributiepunt in the table.
**Notes:** the route follows the stop numbers; locations without a Leveringsvolgorde position come after the positioned
ones by name, so the route only makes sense on the ground once they're in the Leveringsvolgorde.

## 2026-10-24 — Speciale levertoeren (master data, team fiche field, planning screen)
**Request:** link a ploeg to special delivery tours ("Kleine wastoer", "Grote wastoer", "Ijsblokken") via a new
"Levertoeren" field on MasterData's team fiche; the tours are new KarTracker master data; plus a KarTracker screen like
"Verplaatsingen tussen festivals" filtered by tour, with a leverplanning PDF + map like "Initiële leverplanning".
**Plan:** new table `KarTracker_speciale_levertoeren` (name, description, active) + many-to-many
`MasterData_team_speciale_levertoer`; KarTracker CRUD screen; multi-select on the team fiche + column in the Teams table;
Planningsanalyses screen with one festival dropdown + multi-select of tours (a kar on two tours shown once), grouped like
Initiële leverplanning, PDF reusing the leverplanning PDF ("Levertoer" column, "Geleverd" box, optional map).
**Changes:** models `kartracker_speciale_levertoer.py`, `team_speciale_levertoer.py`; migration `d5e9f3a7b124`; screens
`kartracker.specialelevertoeren`, `kartracker.levertoerplanning`; module-2 `/special-tours` CRUD,
`GET /special-tour-planning`, `POST /special-tour-planning/print`, `special_tour_planning_service.py`;
`group_by_distributiepunt` extracted from `initial_delivery_service.py` and `_keep_selected_karren` from the initial
print endpoint (shared, no behaviour change); `build_delivery_planning_pdf(special_tours=…)` variant (own title,
Levertoer column, wider column widths); module-9 `GET /special-tours` (teams-screen right) and `special_tour_ids` on the
team endpoints (left out on PUT = links kept). Frontend: `special-tour-management.tsx`, `special-tour-planning-screen.tsx`,
pages `module-2/special-tours` and `module-2/planning-analyses/special-tours`, sidebar links, help routes, team fiche
field + column, api/types, nl/en texts (`karTracker.specialTours`, `karTracker.specialTourPlanning`,
`masterdata.teams.*`); help chapters module_2 (2 new) + module_9 Teams; `CLAUDE.md`.
**Verification:** new tests `test_special_tours.py` (4), `test_special_tour_planning.py` (4), 3 new in
`module_9/test_teams.py`; full backend suite 834 passed (module-2 tests re-run after the PDF width tweak: 146 passed); `tsc --noEmit` + eslint clean;
migration applied on local Postgres; sample PDF rendered and checked visually (Levertoer column widened after the first
render truncated two tour names). Not clicked through in the browser.
**Notes:** deviation: the planning screen keeps festival/tours in component state (like Verplaatsingen) instead of the
URL. Both screens are new screen keys: roles need "view" on them before users see them. No XLSX import/export for tours.

## 2026-10-24 — Planningsanalyses: "Verplaatsingen tussen festivals"
**Request:** a second screen under Initiële leverplanning that shows which karren have to be moved from one
afleverlocatie to another between festivals, when a team's delivery locations differ between them.
**Plan:** dropdowns Van festival A → Naar festival B; list only karren whose team plays both, is planned at both and
the locations differ; grouped per pick-up location (location at A) in tour order with a "Naar" column; checkboxes +
filters like Initiële leverplanning; PDF in the same style with an optional map (arrows from pick-up to destination).
**Changes:** screen `kartracker.karverplaatsingen` (`module_2/screens.py`); `module_2/kar_moves_service.py`;
`module_2/kar_moves_pdf.py`; `_draw_map_view` extracted from `_render_map` in `delivery_planning_pdf.py` (shared, no
behaviour change); `GET /kar-moves`, `POST /kar-moves/print`; schemas `KarMoves*`; tests
`tests/modules/module_2/test_kar_moves.py`; page `modules/module-2/planning-analyses/kar-moves`,
`components/module-2/kar-moves-screen.tsx`, sidebar link, help route, `getKarMoves`/`printKarMoves` + types, nl/en
texts (`karTracker.karMoves`), help chapter nl/en; `CLAUDE.md`. No migration.
**Verification:** test_kar_moves.py (5) + full backend suite (823 passed); `tsc --noEmit` + eslint clean; sample PDF
(table + map page) rendered and checked visually. Not clicked through in the browser.
**Notes:** the screen is a new screen key, so roles need "view" on it (super admin via Access Rights) before users see it.

## 2026-10-24 — Initiële leverplanning: column filters
**Request:** filter the screen on column values, mainly Status, the other columns too.
**Plan:** a sticky filter row under the headings (pattern of Kar Planning): Status dropdown with the planning's
statuses, text filters for Positie/locatie, Karnummer, Ploeg, Transporttype, Festival, Leverdatum; empty groups drop
out, counts follow; select-all/group/Shift only act on the shown karren.
**Changes:** `initial-delivery-screen.tsx` (filters, "x van y getoond", Filters wissen, no-results row); nl/en texts;
help chapter nl/en; `CLAUDE.md`. Frontend only.
**Verification:** `tsc --noEmit` + eslint clean. Not clicked through in the browser.

## 2026-10-24 — Leverroute map: zoom on the printed points, legend by description + zone
**Request:** focus the PDF's route map on the selected points; in the legend show the description instead of the name
and the zone instead of the distributiepunt.
**Plan:** view = bounding box of the drawn points + 12% padding (min 150 m), widened to the map area's shape; the
ground plan image is cropped to the view (keeps it sharp); legend lines "position. description (zone)".
**Changes:** `module_2/delivery_planning_pdf.py` (`_render_map` view, `_print_image` crop, legend line); help nl/en;
`CLAUDE.md`.
**Verification:** test_initial_delivery.py + full suite; PDF rendered from local data with only the tour stops'
karren and checked visually (zoomed in on stops 1–12).

## 2026-10-24 — Initiële leverplanning: selection + "Leverplanning" PDF with route map
**Request:** a checkbox per line (Shift for a start–end range) and a landscape PDF of the selection telling the driver
where to pick up (distributiepunt) and deliver (afleverlocatie); optionally a map page with the delivery route like
Leveringsvolgorde's map.
**Plan:**
- Checkboxes on kar rows + distributiepunt/location/header group checkboxes; Shift-range via a click-capture ref.
- `POST /initial-delivery/print` re-derives the planning and keeps the ticked ids; fpdf2 landscape PDF in KarTracker
  purple; optional map page drawn server-side over the ground plan (Web-Mercator, like Leaflet).
**Changes:** `module_2/delivery_planning_pdf.py` (new), print endpoint + `InitialDeliveryPrintRequest`, lat/lng added
to the initial-delivery response; `initial-delivery-screen.tsx`, `printInitialDelivery`, types, nl/en texts; help
chapter nl/en; `CLAUDE.md`; 3 new tests (PDF with/without map, without ground plan, 404/422/403).
**Verification:** module-2 tests (9 in test_initial_delivery.py) + full suite, `tsc --noEmit` + eslint clean; PDF
rendered from the real local data (read-only) and checked visually: tables page(s) and map page.
**Notes:** with a ground plan the map shows only the plan's area (one stray coordinate otherwise shrank it); outside
points are listed. Locations without a tour position are grey dots and only counted in the legend.

## 2026-10-24 — Initiële leverplanning: group by distributiepunt first
**Request:** group the screen first by distributiepunt.
**Plan:** distributiepunt → afleverlocatie (tour order) → karren; distributiepunten ordered by their first location in
the tour.
**Changes:** response now `distributiepunten[{id, name, count, locations}]` + `total` (replaces `locations` /
`distributiepunt_totals`) in `initial_delivery_service.py` + schemas; test updated; `initial-delivery-screen.tsx`
(purple distributiepunt header row above the grey location rows) + types; help chapter nl/en; `CLAUDE.md`.
**Verification:** module-2 + help tests, `tsc --noEmit` + eslint clean; backend restarted.

## 2026-10-24 — KarTracker: "Planningsanalyses" group + "Initiële leverplanning"
**Request:** a new KarTracker menu group PLANNINGSANALYSES (between Acties and Masterdata) for analyses of what
has to be organised before/during/after the festival; first screen "Initiële leverplanning": the karren to deliver
per afleverlocatie, in terreinpositie order.
**Plan:**
- A kar's initial location = the Plan a kar location of its team's first festival of the season (earliest picked in
  Altsien Select, else the season's first active festival); karren without a team / plan are left out.
- Grouped per location in tour order (no position last), with distributiepunt, kar count, totals per distributiepunt
  and overall.
**Changes:** screen `kartracker.initieleleverplanning` (`module_2/screens.py`); `module_2/initial_delivery_service.py`;
`GET /api/modules/module-2/initial-delivery?season_id=`; schemas `InitialDelivery*`; tests
`tests/modules/module_2/test_initial_delivery.py`; page `modules/module-2/planning-analyses/initial-delivery`,
`components/module-2/initial-delivery-screen.tsx`, sidebar group, `getInitialDelivery` + types, nl/en texts, help
route + manual chapter nl/en; `CLAUDE.md` section. No migration.
**Verification:** full backend suite (815 passed), `tsc --noEmit` + eslint clean.
**Notes:** the new screen must be granted to roles on KarTracker's Roles screen (backend restart syncs it). No
screenshot in the manual yet.

## 2026-10-24 — Leveringsvolgorde: tour column on the left
**Request:** swap the two columns: the tour to the left, the locations not in the tour to the right.
**Plan:** swap the two `ListColumn` blocks, point the arrow buttons the other way, update the texts.
**Changes:** `delivery-order-screen.tsx` (column order, ← add / → remove, comments); screen description nl/en;
help chapter nl/en; `CLAUDE.md` line. The Kaart button stays at the top right.
**Verification:** tsc + eslint, help tests; read-only browser check (page opened, nothing saved, no API writes).
**Notes:** earlier test runs had wiped the user's saved terreinpositie values (they reset the tour to empty); from
now on test runs don't write to the local data, or restore exactly what was there.

## 2026-10-24 — Leveringsvolgorde: description / name / zone on the lines and map tooltip
**Request:** in the lists and on the Kaart's tooltip, replace name by description, zone by name and distributiepunt
by zone.
**Plan:**
- Add `description` to the delivery-order response.
- Each line: bold description, small "name · zone". Tooltip: "description — name · zone". Fall back to the name
  when there is no description.
**Changes:** `DeliveryOrderLocationResponse.description` (`schemas/kartracker.py`, `delivery_order_service.py`,
test); `types.ts`; `delivery-order-screen.tsx` (row text, search also on description, no longer on
distributiepunt); `delivery-order-map.tsx` (tooltip, no-coordinates note); `searchPlaceholder` nl/en; help
chapter nl/en.
**Verification:** `pytest tests/modules/module_2/test_delivery_order.py tests/help` 35 passed; tsc + eslint clean.
Edge (playwright), tour of 3 seeded and reset afterwards: rows read "APERO NWW APEROL Loc 3.3 | APER_03 · NWW",
searching "spirits" finds "APEROL SPIRITS STAGE B-Terrein Loc9.14 | APER_09 · B-terrein", the Kaart tooltip reads
"APERO NWW APEROL Loc 3.3 — APER_03 · NWW"; no console errors.
**Notes:** the left list stays sorted by name (the stable code).

## 2026-10-24 — Leveringsvolgorde: saved vs new number + "Kaart"
**Request:** show the saved (not yet overwritten) number next to the new one, to check the order is logical; and a
"Kaart" button above the right column that opens the RW ground plan with the afleverlocaties showing their order
number (new and old), the name in a tooltip on hover.
**Plan:**
- Badges in the lists: "was X" (amber when it changes) / "nieuw" in the tour, "was X → wordt leeg" outside it; a
  "x gewijzigd" counter.
- Reusable labels/tooltips/route on the shared Leaflet map; a map dialog following the unsaved tour.
- Coordinates in the delivery-order response; ground plans readable with the new screen's rights.
**Changes:**
- Backend: `DeliveryOrderLocationResponse` + `latitude`/`longitude` (`delivery_order_service.py`);
  `kartracker.leveringsvolgorde` added to `GET /groundplans` and `/groundplans/{id}/image`; 1 new test.
- Frontend: `delivery-order-screen.tsx` (`PositionBadge`, change counter, Kaart button + dialog; overlays built
  from the page's ground plans), new `delivery-order-map.tsx`, `kar-map-leaflet.tsx` (optional `label`, `tooltip`,
  `zIndexOffset` per pin, optional `route` polyline; existing maps unchanged), page also fetches `/groundplans`,
  types, translations nl/en.
- Help chapter Leveringsvolgorde (nl/en) and `CLAUDE.md` updated.
**Verification:** `pytest tests/modules/module_2 tests/help` 155 passed; `tsc --noEmit` + eslint clean. Edge
(playwright): seeded tour of 6, took #1 out, added one, dragged it to #2 → rows show "was 2" (amber), "nieuw",
"was 3…6" (muted), "3 gewijzigd"; Kaart shows "1 (was 2)", "2 (nieuw)", 3–6, the dashed route and the ground plan;
hover tooltip "HIVE_04 — HIVE · Altsien Hive 1 (LN17)". Kar Map still renders its 354 dots without errors. Local
data reset to an empty tour afterwards.
**Notes:** grey dots for locations outside the tour were first drawn over tour badges (Leaflet stacks by
latitude) — fixed with `zIndexOffset`. The map opens on the default Werchter extent like every other map.

## 2026-10-24 — KarTracker "Leveringsvolgorde" (delivery-tour order) screen
**Request:** a new KarTracker screen to put the delivery locations in delivery order: left the afleverlocaties without
a terreinPositie, right the ones with one (ordered), move lines left → right and drag them into order; Save writes the
order into terreinPositie.
**Plan:**
- `terrein_positie` becomes an integer (numeric text kept, other text → NULL); one tour for the whole ground; only
  active locations; own screen key `kartracker.leveringsvolgorde`.
- `GET/PUT /api/modules/module-2/delivery-order` via a new `delivery_order_service.py`.
- New two-column drag-and-drop screen under Actions, with `@dnd-kit`.
**Changes:**
- Migration `c4d8e2f6a913` (column → INTEGER + index); model, schemas, import parsing (whole number ≥ 1), screen
  definition, `module_2/delivery_order_service.py`, two routes in `module_2/router.py`.
- Frontend: `@dnd-kit/core|sortable|utilities`, page `modules/module-2/actions/delivery-order`,
  `components/module-2/delivery-order-screen.tsx`, sidebar link, help route, types/api, Afleverlocatie form input is
  now a number, translations `karTracker.deliveryOrder.*` (nl/en).
- Help manual chapter `leveringsvolgorde` (nl/en) + note in the Afleverlocatie chapter; `CLAUDE.md` section.
**Verification:** new `tests/modules/module_2/test_delivery_order.py` + import test; full backend suite 811 passed
(before the help/doc edits; help tests re-run, passing). Migration upgrade/downgrade/upgrade on local Postgres, the
conversion expression checked on sample values. `tsc --noEmit` and eslint clean. Browser run in Edge (playwright):
add via arrow, reorder by drag, drag from the left list into the tour, save, reload (order kept), remove + save; no
console errors (a dnd-kit hydration mismatch was fixed with a fixed `DndContext` id). Local data reset afterwards.
**Notes:** no help screenshot yet for the new chapter (`npm run help:screenshots module-2` once a login is set). On
test/production, any non-numeric terreinpositie text on afleverlocaties is cleared by the migration.

## 2026-10-24 — Introduce work-history log
**Request:** from now on, complete a specific file every time an accepted plan is executed, to keep the history of the work.
**Plan:**
- Add a mandatory "Work history (plan log)" section to `CLAUDE.md` with the rule and entry format.
- Create this file with a header and this first entry.
**Changes:** `CLAUDE.md` (new section + `docs/work-history.md` in the repo layout), new `docs/work-history.md`.
**Verification:** checked that both files contain the section, layout line and first entry.
