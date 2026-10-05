# StockMaster (module-4) — stock management design

_Status: design agreed and first version built on 2026-10-04 (see CLAUDE.md, "StockMaster (module-4)")._

## Context
Module-4 is still a placeholder. It becomes **StockMaster**: the stock of ~250 MasterData products
(~10,000 movements/year) kept in the warehouse, either as **free stock** (on the product's bin) or
**loaded in a kar** (KarTracker kar, by kar number) while that kar stands in the warehouse.

Decisions taken:
- This document is the design only; the build order is in §8.
- Stock is tracked as **quantity only**: no per-item or RFID tracking.
- **Kar stock only exists while the kar is in the warehouse.** Dispatching a kar books its contents
  out; returning it books what comes back in.
- **One fixed bin per product.** Free stock lies on the product's existing `MasterData_product.warehouse_id`
  plus `warehouse_location`. No bin table.

Naming:
- The module name is spelled **StockMaster** on the tile, in titles and in texts.
- The table prefix is `StockMaster_` and the model classes are `StockMaster*`.
- Screen keys (`stockmaster.*`) and the translation namespace (`stockMaster`) follow the lowercase or
  camelCase convention of the other modules.


---

## 1. Core principle: an immutable ledger plus a balance table
- Every stock change is a **movement** row that is never edited or deleted. Corrections are made by
  **reversal** (opposite movements that point to the original). This gives a full audit trail
  ("who put 12 pieces in kar 47 on which date").
- The current stock is kept in a **balance table**, updated in the *same* DB transaction as the
  movement. The balance row is locked (`SELECT … FOR UPDATE`) so two users can't both take the last piece.
  This prevents negative stock.
- The balance can always be **rebuilt** from the ledger (an admin "recalculate" check). At 10k rows/year
  a SUM would be fast enough too, but the balance table keeps the overview screens and locking simple.

### Every transaction is booked under the logged-in user
- The user is **always taken from the login session on the server** (the authenticated `current_user`
  from the access cookie, the same dependency every module uses). It is **never** sent by the browser,
  so it can't be chosen or faked, and nobody can book "in someone else's name".
- Stored on every write, with the time in Belgian time:
  - `StockMaster_document.created_by` + `created_at`: every booking (Inboeken, Uitboeken, Kar laden,
    Kar uitladen, Kar vertrekt, Kar terug, Telling)
  - `StockMaster_movement.created_by` + `created_at`: each ledger line too, so a line read on its own
    still shows who booked it
  - **reversals**: the reversal is a new document with its own `created_by` (who undid it). The original
    keeps its own user, so both names stay visible.
  - `StockMaster_kar_requirement.updated_by` + `updated_at` (Benodigdheden), and `created_by` on reasons
- Shown on screen and on the PDFs as the user's **name** from `Landing_users`: Boekingen list column
  "Gebruiker", product/kar "Geschiedenis", the footer "afgedrukt door", and the Boekingsbon.
- The FK uses `ON DELETE SET NULL`, as `KarTracker_kar_actions.user_id` does.
  - A **name snapshot** column (`created_by_name`) is stored as well, so history still shows who booked
    even if that user is later deleted.
  - Boekingen can be filtered by user.

### Prepared for later automation from TagScan CSVs
Some actions (e.g. Inboeken, Kar laden, Kar uitladen) will later be booked **automatically from TagScan
CSVs**. This will work in roughly the same way as TagScan's tag creation: an `Action` in the CSV is
handled by `module_1/line_processing.py` (`PROCESSABLE_ACTIONS` → `_process_<action>`). The first
version stays manual, but the design is ready for it:
- **One booking entry point**: `module_4/stock_service.py` has plain functions (`book_in`, `load_kar`,
  `unload_kar`, `dispatch_kar`, …) that don't depend on a web request. A future TagScan handler simply
  calls them. Screens and automation follow the same rules: no negative stock, closed-season lock,
  blocked products.
- **Source on every booking**: `StockMaster_document.source` (`manual` / `tagscan`) plus nullable
  `tagscan_header_id` → `Tagscan_header_data`.
  - Boekingen shows the source and links back to the scan file.
  - TagScan's line `process_comment` can show the StockMaster document number.
- **Each scan line is booked only once**: a line counts only after its `process_status` turns
  `loaded`. A unique `tagscan_line_id` on `StockMaster_movement` blocks a second booking of the same line.
- **Counting from tags**: quantity-only stock stays as it is. Each read tag counts as 1 piece of its
  `Tagscan_rfid_tag.assigned_product_id`, and lines from one file are grouped per product into one
  booking.
- **User**: an automated booking is stored under the user who processes the lines in TagScan's
  pending-actions dialog. A fully automatic run (TagScan auto-scan) uses a fixed technical user
  "TagScan (automatisch)", so the user field is never empty.
- The CSV → StockMaster action mapping (which `Action` / scanner / kar column means what) is decided
  when this phase is designed.

## 2. Stock positions ("buckets")
A product's stock is in exactly one of these places:

| Bucket | Meaning | Key |
|---|---|---|
| `free` | free stock on the product's fixed bin | product |
| `kar` | loaded in a kar that is in the warehouse | product + kar |
| `external` | outside our stock: supplier, team/festival, consumed, scrap | not stored as a balance |

Total warehouse stock of a product = free + Σ kar.

**One product can be in free stock and in several kars at the same time.** The balance table holds
one row per product per place. Example, product "Walkie-lader" with 10 in the warehouse:

| product | kar_id | quantity |
|---|---|---|
| Walkie-lader | NULL (free stock, on its bin) | 5 |
| Walkie-lader | K101 | 2 |
| Walkie-lader | K043 | 3 |
| **Total in warehouse** | | **10** |

The stock overview shows this as one product line: Free 5 · In kars 5 (K101: 2, K043: 3) · Total 10.
The kar stock screen shows the same rows grouped per kar.
- Loading 1 more into K101 → free 4, K101 3.
- Dispatching K043 → its 3 leave the warehouse, so the total becomes 7.

## 3. Data model (prefix `StockMaster_`, one model file per table)
**Custom roles** (copy of module-8): `StockMaster_screens`, `StockMaster_roles`,
`StockMaster_role_permissions`, `StockMaster_user_roles`.

**`StockMaster_document`** (header, so one action = one document with several lines, e.g. "load kar 47 with 6 products"):
- `id`, `doc_type` (see §4), `doc_number` (readable, e.g. `SM-2026-00123`)
- `season_id` → `MasterData_season`
- `kar_id` → `KarTracker_karren` (nullable), `team_id` / `festival_id` (nullable, for dispatch/return)
- `reference`: delivery note, PO or free text
- `reason_id` → `StockMaster_reason` (nullable)
- `comment`, `status` (`posted` / `reversed`), `reversal_of_id` → self
- `created_by` → `Landing_users`, `created_at` (Belgian time display via `lib/date-time.ts`)

**`StockMaster_movement`** (ledger line):
- `id`, `document_id`, `product_id` → `MasterData_product`
- `quantity` (whole number, always > 0)
- `from_bucket` / `from_kar_id`, `to_bucket` / `to_kar_id`
- `bin_snapshot`: the product's warehouse + location text at booking time. If the bin later
  changes in MasterData, history still shows where it was.
- Indexes on product, kar and document.

**`StockMaster_balance`**: `product_id`, `kar_id` (NULL = free stock), `quantity`, `updated_at`.
Uniqueness comes from two partial unique indexes (`(product_id) WHERE kar_id IS NULL`,
`(product_id, kar_id) WHERE kar_id IS NOT NULL`). These work on both Postgres and the SQLite tests.

**`StockMaster_kar_trip`**: one row per dispatch of a kar. It holds `kar_id`, `dispatch_document_id`,
`return_document_id` (nullable), `team_id`, `festival_id` and `season_id`. A kar with an open trip is
"out" and cannot be loaded or unloaded.

**`StockMaster_reason`**: editable reasons (scrap, lost, count difference, consumed, …), with an
`applies_to` doc type and an `active` flag.

## 4. Movement (document) types

| Type | From → To | Notes |
|---|---|---|
| Inbound | external → free | delivery from supplier; reference = delivery note |
| Outbound | free → external | consumption, scrap, loss, sale; reason required |
| Load kar | free → kar | multi-line; kar must be in warehouse |
| Unload kar | kar → free | multi-line, or "unload everything" |
| Kar → kar | kar → kar | moving goods between kars |
| **Kar dispatch** | kar → external | books out the kar's full contents; opens a `kar_trip` (team/festival/season) |
| **Kar return** | external → kar *or* free | shows what was dispatched; the user enters what came back; the difference is reported as consumed/lost per line; closes the trip |
| Stock count | ± free / kar | user enters the counted quantity; the system books the difference with a reason |
| Reversal | opposite of original | cancels a whole document; refused if it would make stock negative |

Rules:
- No negative stock.
- Blocked products (`is_blocked`) can't be booked in or loaded.
- Consumables (`is_consumable`) are not expected back on return, so a "not returned" quantity is not
  flagged as missing.
- Changes in a closed season (`periode_open` off) are refused unless the user has "edit" on
  the `stockmaster.closedseason` switch-screen (same idea as module-8).

## 4b. Kar needs ("Benodigdheden per kar") — what each team needs in which kar
The Products step of Altsien Select's Ploeg Wizard is still a placeholder. StockMaster therefore gets
this functionality itself, built so that Altsien Select can **copy or reuse it later** (Altsien Select
collects functionality from other modules, the way it reuses `module_2/plan_kar_service.py`).

**`StockMaster_kar_requirement`**: `id`, `season_id`, `kar_id` → `KarTracker_karren`, `product_id`,
`quantity` (whole number ≥ 1), `comment`, `updated_by`, `updated_at`.
- Unique on `(season_id, kar_id, product_id)`.
- Needs are **per season** (the same for all the team's festivals) and **per specific kar number**. The
  team follows from the kar (`KarTracker_karren.team_id`).
- All reads and writes go through **`module_4/requirement_service.py`**, the future shared entry point
  for Altsien Select.

**Screen "Benodigdheden"** (`stockmaster.requirements`):
- Choose a season, then a team, then one of the team's kars.
- Edit the product list with quantities, using the same basket-style input as the booking panel.
- "Kopieer van vorig seizoen" is copied from module-8's copy-last-season panel.

**How the needs drive the stock actions:**
1. **Kar laden** is pre-filled with **what is still missing**: need − already in the kar, per
   product. The user only confirms or adjusts. Each line shows whether there is enough free stock ("vrij 3
   van 5 nodig" in orange when short).
2. **Kar cards** show the loading progress against the needs ("18 / 20 geladen", green when complete,
   orange when partial). The kar detail lists missing and surplus lines.
3. **Te bestellen** (`stockmaster.orderneeds`): per product for the selected season:
   - total needs (all kars)
   - in stock (free + in kars)
   - **to order = needs − in stock** (only shown when > 0)

   The list can be filtered on warehouse and category and printed or exported. Selecting lines and
   choosing "Inboeken" opens the booking panel pre-filled with those quantities, so the user only
   corrects what was actually delivered.
4. The **minimum-stock alert** for consumables (§ decisions) stays separate: it is about reordering
   consumables, while "Te bestellen" is about meeting the season's planned needs.

## 5. User friendliness (guiding principles)
The user should never need to know about "buckets", "documents" or "ledgers". The screens speak
warehouse language. The ledger, balances and locking stay invisible behind them.

1. **Plain action names (Dutch first), one button per real-world action:**
   - "Inboeken" (goods arrive)
   - "Uitboeken" (used, broken or lost)
   - "Kar laden"
   - "Kar uitladen"
   - "Kar vertrekt"
   - "Kar terug"
   - "Telling"

   Each opens the same simple **booking panel**, pre-set for that action, so no "from/to" choice is needed.
2. **Start from what you're looking at.**
   - On a product row: "Inboeken", "Uitboeken" and "Laden in kar…".
   - On a kar: "Laden", "Uitladen", "Vertrekt" and "Terug".

   The product or kar is already filled in; the user only adds the rest.
3. **Booking panel = a basket.**
   - Type a few letters of a product or kar number: the search shows matches with **current stock
     and bin** ("Walkie-lader · bin B-12 · vrij 5").
   - Enter a quantity and press Enter: the line is added and the cursor goes back to product search.
   - Several products are booked in one go.
   - The quantity field knows the maximum available and says so in plain words ("Er zitten maar 3 in
     K043").
4. **Preview before saving.** Each line shows "before → after" ("Vrij 5 → 4 · K101 2 → 3"). One
   "Bevestigen" button books everything at once.
5. **Smart pre-filling:**
   - "Kar uitladen" offers "Alles uitladen".
   - "Kar terug" is pre-filled with what left, so the user only changes the lines that differ.
     Differences are explained ("2 niet terug → verbruikt").
   - "Telling" is pre-filled with the expected quantity, and only differences are booked.
   - Team/festival on "Kar vertrekt" is defaulted from KarTracker and the season from the dropdown.
6. **Safe undo.** After every booking a toast offers "Ongedaan maken". Any booking can later be
   reversed from its detail page with one click. Nothing is ever deleted, so mistakes are harmless.
7. **Overview that answers "where is it?" at a glance.**
   - One line per product: Vrij · In karren · Totaal.
   - Click to expand the split per kar (K101: 2, K043: 3) with the bin.
   - Kars that are out are shown with a coloured "onderweg" chip.
   - There is a search box at the top, and filters are remembered per user.
8. **Kar stock view:**
   - A grid of kar cards (number, status in/out, number of products).
   - Click a card to see its contents and action buttons.
   - Typing a kar number jumps straight to it.
9. **History is always one click away.** Each product and kar has a "Geschiedenis" tab showing who
   did what and when, in Belgian time.
10. **Keyboard friendly and fast.**
    - Autofocus on search.
    - Enter adds a line, Esc closes, Ctrl+Enter confirms.
    - No page reloads.
11. **Clear, friendly errors and empty states**: say what to do, not what went wrong technically
    (e.g. "Deze kar is onderweg — boek eerst 'Kar terug'").
12. **Printable**: every PDF is one click away from the screen it belongs to (see §6b).

## 6. Menu structure and screens
The left menu (sidebar) is built the same way as Altsien Select's and MasterData's:
- a coloured header bar with the module name **StockMaster** (teal tile colour)
- a fixed link back to the landing page
- groups with an icon, each shown only when the user may view at least one item in it

All routes live under `/modules/module-4`.

```
StockMaster                                   (header bar, teal)
📊 KPI                       /                 stockmaster.kpi           (main page, as in the other modules)

📦 Voorraad
   ├─ Voorraadoverzicht      /stock            stockmaster.stock
   └─ Karren                 /kars             stockmaster.kars

⚡ Akties                    (in process order)
   ├─ 1. Inboeken            /book-in          stockmaster.stock    (create)
   ├─ 2. Kar laden           /kars/load        stockmaster.kars     (create)
   ├─ 3. Uitboeken           /book-out         stockmaster.stock    (create)
   ├─ 4. Kar vertrekt        /kars/dispatch    stockmaster.kars     (create)
   ├─ 5. Kar terug           /kars/return      stockmaster.kars     (create)
   ├─ 6. Kar uitladen        /kars/unload      stockmaster.kars     (create)
   └─ 7. Telling             /count            stockmaster.count

📋 Planning
   ├─ Benodigdheden          /requirements     stockmaster.requirements
   └─ Te bestellen           /order-needs      stockmaster.orderneeds

🕘 Historiek
   └─ Boekingen              /bookings         stockmaster.bookings
                             /bookings/{id}    (detail + "Ongedaan maken")

⚙️ Instellingen
   └─ Redenen                /settings/reasons stockmaster.reasons

🛡️ Toegangsrechten
   ├─ Rollen                 /access-rights/roles   stockmaster.roles
   └─ Gebruikers             /access-rights/users   stockmaster.users
```

How the screens fit together:
- **KPI** (main page, opened when clicking the StockMaster tile). It is built like the KPI/dashboard
  start pages of Altsien Select and the other modules:
  - Tiles at the top:
    - total stock
    - free stock
    - in kars
    - kars in the warehouse vs onderweg
    - kars fully loaded vs their needs ("12 / 30")
    - products under minimum
    - lines still to order
  - Charts below:
    - bookings per month per action
    - consumption per team / festival for the season
    - top consumed products
  - Every tile links to the screen behind it (e.g. "onder minimum" → Voorraadoverzicht filtered).
  - It follows the module's season dropdown.
- **Voorraadoverzicht**:
  - One line per product (Vrij · In karren · Totaal · bin · warehouse), expandable to the split per kar.
  - Filters: search, warehouse, category, "Alleen onder minimum".
  - Row buttons: Inboeken / Uitboeken / Laden in kar…
- **Karren**:
  - Kar cards (number, team, in warehouse / onderweg, loading progress "18 / 20").
  - Click a card for kar detail: contents vs needs, history, and buttons Laden / Uitladen / Vertrekt / Terug.
- **Akties** menu items: each opens the booking panel directly for that action. For kar actions, the
  first field asks for the kar number (typeahead). The same panel opens from the buttons on Voorraad and
  Karren, already filled in.
- **Telling**:
  - Choose a warehouse (+ optional bin range) or a kar.
  - The list is pre-filled with the expected quantities; enter differences only.
  - A printable count sheet is available.
- **Benodigdheden**: season → team → kar; product list with quantities; "Kopieer van vorig seizoen".
- **Te bestellen**: per product: needs, in stock, to order. Select lines → "Inboeken" (pre-filled).
  Print/export.
- **Boekingen**: all bookings, newest first.
  - Filters: date, action, product, kar, user.
  - The detail page shows all lines plus "Ongedaan maken".
- **Redenen**: list plus add/edit/delete of reasons per action.

The Akties menu follows the order of the real process:
1. **Inboeken**: goods arrive.
2. **Kar laden**: fill the kar from the needs.
3. **Uitboeken**: used, broken or lost goods from free stock.
4. **Kar vertrekt**.
5. **Kar terug**.
6. **Kar uitladen**: back to free stock.
7. **Telling**: periodic stock count.

The same order is used for the buttons on a kar detail and for the "Actie" filter on Boekingen.

**Top of every StockMaster screen**:
- the module's own season dropdown
- the orange minimum-stock banner, when consumables are below their minimum ("3 producten onder
  minimum stock" → opens Voorraadoverzicht filtered on those)

All tables follow the sticky header/Actions pattern and the bold+underlined titles.

## 6b. PDF documents (nice layout, TeamKar logo)
These are made with **fpdf2**, the library the other PDFs already use (`module_2/karblad_pdf.py`,
`module_8/ploegfiche_pdf.py`).

**One shared house style** in `module_4/pdf_layout.py`, used by every StockMaster PDF:
- **Header** on every page:
  - the TeamKar logo (`backend/app/assets/teamkar-logo.png`, as on the Karblad) top left
  - document title large and bold, with a subtitle (kar / season / warehouse)
  - document number and print date on the right, in Belgian time
- **Body**:
  - clean tables with a teal header row (StockMaster colour) and light zebra rows
  - numbers right-aligned
  - totals bold
  - long lists continue on the next page with the table header repeated
- **Footer**: "StockMaster · RWCrew", printed by (user), "pagina x / y".
- Optional fields at the bottom, where relevant: tick boxes and signature boxes
  ("Magazijn" / "Ploeg", name + date + signature).
- A4 portrait, with landscape only when a list needs it. Texts come from the translations (nl/en).

| PDF | Opened from | Contents |
|---|---|---|
| **Laadlijst per kar** | Kar detail, Kar laden | kar number + QR code (as on the Karblad), team, season; per product: needed · already in kar · **to load** · bin + warehouse, **sorted by bin** for an efficient picking route; tick box per line; signature "geladen door" |
| **Kar inhoud / vertrekbon** | Kar vertrekt (after confirming), Boekingen detail | kar + QR, team, festival, season, departure date; per product the quantity that leaves; signatures Magazijn + Ploeg. Also used as the check list on "Kar terug" (empty column "terug") |
| **Bestellijst** | Te bestellen | season, filters used; per product: needs · in stock · **to order**, grouped per warehouse and category; total lines; empty column "besteld" |
| **Telblad** | Telling | warehouse + bin range, or one kar; per product: bin · expected · empty column **"geteld"**, sorted by bin; signature "geteld door" |
| **Boekingsbon** | Boekingen detail (any booking: Inboeken, Uitboeken, Kar laden/uitladen, Telling, reversal) | action, document number, date, user, reference/reason; lines with product · from → to · quantity; "Ongedaan gemaakt" stamp if reversed |

Endpoints are `GET …/pdf` on the matching resource, each protected by the "view" right of that screen.

**Web app only.** StockMaster gets no phone (`/m`) screens.

### Roles and access rights — exactly like the other modules (1, 2, 3, 8, 9)
Nothing new is invented here. StockMaster follows `docs/module-custom-roles-pattern.md`, copied from
module-8.

- **Module access**: the super admin grants module-4 per user on "Manage Access" (`Landing_user_module_access`),
  the same as every other module. Without it the user can't open StockMaster at all.
- **Custom roles with per-screen permissions**:
  - Tables: `StockMaster_screens`, `StockMaster_roles`, `StockMaster_role_permissions`
    (view/create/edit/delete per screen) and `StockMaster_user_roles` (one role per user).
  - Managed by the module's own admin under the **Toegangsrechten** group (Rollen + Gebruikers), with the
    same `roles-management` / `users-management` screens as module-8.
  - The super admin can always manage roles.
  - A missing permission row means no access.
- **Backend**: `module_4/deps.py` holds `require_module_access` and `require_screen_permission(screen_key,
  action)`. `module_4/screens.py` holds `SCREEN_DEFINITIONS` plus `sync_screens`, run at startup in
  `main.py`. The generic endpoints are the same as module-8: `/screens`, `/roles`, `/roles/{id}/permissions`,
  `/users`, `/users/{id}/role` and `/me/permissions`.
- **Frontend**:
  - The layout loads `me/permissions`.
  - The sidebar only shows the screens the user can view.
  - Buttons (Inboeken, Kar laden, Ongedaan maken, …) are hidden when the matching
    create/edit/delete right is missing.
  - A 403 on one screen blocks only that screen.
- **Screens and what each permission means:**

| Screen key | view | create | edit | delete |
|---|---|---|---|---|
| `stockmaster.stock` (Voorraad) | see the overview | Inboeken / Uitboeken | – | – |
| `stockmaster.kars` (Karren) | see kars and contents | Kar laden / uitladen / vertrekt / terug | – | – |
| `stockmaster.requirements` (Benodigdheden) | see needs | add lines | change quantities | remove lines |
| `stockmaster.orderneeds` (Te bestellen) | see the list | Inboeken from the list | – | – |
| `stockmaster.bookings` (Boekingen) | see history | – | – | Ongedaan maken (reversal) |
| `stockmaster.count` (Telling) | see counts | book a count | – | – |
| `stockmaster.reasons` (Instellingen > Redenen) | see | add | change | remove |
| `stockmaster.kpi` (KPI, main page) | see KPI | – | – | – |
| `stockmaster.closedseason` (switch-screen) | – | – | book in a closed season | – |
| `stockmaster.roles` / `stockmaster.users` | as in module-8 | | | |

  The `closedseason` switch-screen works like module-8's `altsienselect.allteams`: it is not a page,
  only a right that can be granted.

## 7. Integration with existing modules
- **Products**: StockMaster reads `MasterData_product` (name, type, category, warehouse, location,
  is_blocked, is_consumable) and never edits product data itself.
  - Two **new product fields** are added to MasterData and maintained on module-9's product screen:
    - `stock_return_to` (`kar` / `free`, default `kar`): where returned goods go on "Kar terug".
    - `min_stock` (integer, nullable): reorder level, only used for consumable products.
  - The existing `MasterData_product_limit` is a name-only lookup, so it can't hold a number. It is not
    reused for this.
- **Warehouses**: there are several (`MasterData_warehouse`). Free stock sits in the product's
  warehouse, so it follows from the product's fixed bin.
  - The overview and count screens get a **warehouse filter**, remembered per user.
  - Kars are not tied to a warehouse; their stock shows under the kar.
- **Kars**: read-only from `KarTracker_karren` (kar_nummer, team).
  - Dispatch defaults team/festival from the kar's team and from `MasterData_team_festival`.
  - The kar's team (`team_id`) decides which kars appear under a team on "Benodigdheden".
- **Altsien Select**: later, its Products wizard step reuses `requirement_service.py` (and the
  Benodigdheden editor component). There is no separate module-8 copy of the data, the same approach as
  team leads and plan-a-kar.
- **Season**: the module's own season dropdown, like module-8.

## 8. Build approach (for later, once the design is agreed)
1. Scaffold module-4 with custom roles, copying module-8:
   - backend: `deps.py`, `screens.py`, the roles/users endpoints in `router.py`
   - frontend: layout, sidebar, roles/users pages
   - migration that renames the tile to "StockMaster"
   - add `_MODULE_NAMES` in `backend/app/modules/registry.py`
   - move `tests/landing/test_access.py` off module-4
2. Add the `stock_return_to` and `min_stock` product fields: migration plus module-9 product screen
   and schemas.
3. Stock tables plus `stock_service.py`, the only place that posts movements, locks balances and
   reverses documents, with pytest coverage.
4. Overview (with the minimum-stock alert), kar stock and bookings screens.
5. Kar needs (`requirement_service.py`, Benodigdheden screen, copy from last season) and Te bestellen.
6. Entry screens: inbound/outbound, load (pre-filled from needs)/unload, count.
7. Dispatch/return with trips.
8. PDFs: shared `pdf_layout.py`, then Laadlijst, Vertrekbon, Bestellijst, Telblad and Boekingsbon,
   each delivered together with its screen.
9. KPI main page. A simple version with tiles goes live in step 4 so the module has its start page from
   the beginning; the charts are added once there is booking data.

## Decisions on the earlier open questions
1. **Return destination**: returned goods go **back into the kar or straight to free stock**, according
   to the new product setting `stock_return_to`. On "Kar terug" each line is pre-set from that setting
   and can still be changed per line.
2. **Trigger for dispatch/return**: **kept open.** The first version works with explicit StockMaster
   actions ("Kar vertrekt" / "Kar terug"). `stock_service.py` exposes dispatch/return as functions, so a
   KarTracker status change can call them later without redesign.
3. **Minimum stock**: **yes, for consumable products** (`is_consumable` plus `min_stock`). Stock below
   the minimum shows in three places:
   - an orange "Onder minimum" chip on the overview
   - a filter "Alleen onder minimum"
   - an orange banner at the top of StockMaster ("3 producten onder minimum stock"), like TagScan's
     pending banner

   The check uses the product's total stock in the warehouse (free + kars in the warehouse).
4. **Warehouses**: there are several (see §7).
5. **Quantities**: **whole numbers only**. `quantity` and balance columns are integers, and the inputs
   accept only whole numbers ≥ 1.

