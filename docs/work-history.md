# Work history

One entry per plan that was accepted and carried out, newest on top. Rules and entry format: see
"Work history (plan log)" in `CLAUDE.md`.

## 2026-10-29 — Voice count: works on iPhone (home-screen app)
**Request:** Testing the voice count in the test app: on an iPhone, opened from the home-screen icon, the microphone button
gave no text and no lines (no error either).
**Plan:**
- Speech hook: keep the last interim text when no final text comes (iOS), one sentence per turn on iOS (its continuous
  mode loses results), report a start that dies without audio as "unavailable", `service-not-allowed` = Dictation off.
- Screen: tap to start/stop instead of hold-to-talk; a "Dicteren of typen" box that uses the keyboard's own dictation
  (always works on iPhone), shown first in an iPhone home-screen app; `?debug=1` event log.
**Changes:**
- Frontend: `components/phone/module-4/use-speech-recognition.ts` (`isIos`, interim fallback, `onstart`/`onaudiostart`,
  failures `unavailable`/`dictationOff`, `onDebug`), `voice-count-screen.tsx` (tap button, dictation form, debug log);
  translations `stockMaster.phone.voiceCount.tapToTalk|tapToStop|tapToTalkHint|dictateLabel|dictateHint|
  dictatePlaceholder|process|speechErrors.unavailable|dictationOff` (nl + en; `holdToTalk*` removed).
- Docs: help chapter "Spraaktellingen" (nl + en), CLAUDE.md. No backend change, no migration.
**Verification:** `npx tsc --noEmit` (only stale `.next` module-9 errors) and eslint clean. Not yet tried on the iPhone:
after deploying to test, check the home-screen app (with `?debug=1`), Safari and Android Chrome.
**Notes:** Cause found by reasoning about known WebKit limitations, not yet confirmed on the device; the debug log is
there to confirm it. The parked product-alias/expected-products plan (better matching) is still open.

## 2026-10-28 — StockMaster: voice count of a kar on the phone (phase 1)
**Request:** For non-tagged items, count by voice in the phone app: scan the kar's QR code, choose Ophalen or Terugbrengen,
speak, list the counted items and save; writing them into StockMaster stock comes in a later phase. Speech recognition =
the browser's free Web Speech API (option A of the feasibility analysis).
**Plan:**
- Phone screen `/m/module-4/voice-count` (first StockMaster phone screen): scan kar → Ophalen/Terugbrengen → hold-to-talk
  microphone → lines (product + quantity, +/−, delete, orange = needs confirming) → Opslaan; hand-add fallback.
- Pure parser (number words nl/en, product matching) in the frontend; saved counts in two new StockMaster tables, status
  `new`; desktop list "Spraaktellingen" with detail, CSV download and cancel. No stock change yet.
**Changes:**
- Backend: models `StockMaster_voice_count` + `StockMaster_voice_count_line` (migration `a4e7c2d9f610`),
  `module_4/voice_count_service.py` (only writer), `module_4/voice_count_router.py` (included in `main.py`):
  `GET /voice-count/lookups`, `POST /voice-counts`, `GET /voice-counts?season_id=`, `GET /voice-counts/{id}`,
  `POST /voice-counts/{id}/cancel`, `GET /voice-counts/{id}/csv`; screen `stockmaster.voicecount` (create = count on the
  phone, view = list, edit = cancel); schemas in `schemas/stockmaster.py`; tests `tests/modules/module_4/test_voice_counts.py`.
- Frontend phone: `module-4` added to `phone-modules.ts`; `m/(signed-in)/module-4/{layout,page}.tsx` + `voice-count/page.tsx`;
  `components/phone/module-4/` (rights, routes, menu, `voice-count-screen.tsx`, `use-speech-recognition.ts`,
  `voice-count-parser.ts`).
- Frontend desktop: `/modules/module-4/voice-counts` (`components/module-4/voice-counts-list.tsx`), sidebar link under
  Historiek, help route, landing `FALLBACK_SCREENS`; API functions + types; translations `stockMaster.phone.*`,
  `stockMaster.voiceCounts.*`, `stockMaster.errors.voice_count_*` (nl + en).
- Docs: help manual chapter "Spraaktellingen" (nl + en, no screenshot yet), CLAUDE.md.
**Verification:** full backend suite 928 passed (module-4: 6 new tests); migration applied locally and `alembic check`
reports no differences; parser tried on sample sentences with Node ("20 rollen tape en 5 kabelhaspels",
"drieëntwintig vuilniszakken", "zwarte tape 4" → gaffer tape, "verwijder laatste"); `npx tsc --noEmit` (only stale
`.next` module-9 errors) and eslint clean. Not yet tried on a real phone with the microphone.
**Notes:** Phase 2 = booking a `new` count via `stock_service.py` (Ophalen ≈ Kar laden, Terugbrengen ≈ Kar terug / count
of the kar; exact mapping still to decide), filling `document_id` and status `booked`. Possible improvements: spoken
aliases per product, a screenshot for the help chapter. Every StockMaster user now sees the StockMaster tile on the
phone; without the voice count right the menu says there's nothing for them.

## 2026-10-27 — Atelier: team leads behind an icon on Ophalen; Openstaand without email column
**Request:** (1) Openstaand: hide the email column; (2) Uitgifte & inname: right-aligned, level with "Gekend", the team's
ploegverantwoordelijken as in MasterData — not shown directly, behind an icon that opens them on click.
**Plan:**
- Openstaand: remove the email column, its filter and the mail link (instead of the masking of the entry below).
- Desk context returns the team leads of the festival's season (read from MasterData, no Atelier copy); Ophalen shows a
  contact icon right of the "Gekend" line that opens a dialog with name, phone (tel:), email (mailto:) and comments.
**Changes:**
- Frontend: `components/module-5/open-handouts.tsx` (email column gone, `atelier.open.email` translation removed),
  `desk-screen.tsx` (`TeamResponsiblesButton` + dialog), `lib/types.ts` (`AtelierDeskTeamResponsible`), translations
  `atelier.desk.teamResponsibles|teamResponsiblesTitle|noTeamResponsibles` (nl + en).
- Backend: `DeskTeamResponsible` + `DeskContextResponse.team_responsibles` (`schemas/atelier.py`), filled in
  `desk_router.get_desk_context` via `module_9/team_responsible_service.list_team_responsibles`; test
  `test_context_shows_team_responsibles`. No migration.
- Docs: help manual (desk, Openstaand; nl + en), CLAUDE.md.
**Verification:** `pytest tests/modules/module_5` (65 passed) + help tests passed; `npx tsc --noEmit` (only stale `.next`
module-9 errors) and eslint clean. Not yet clicked through on localhost.
**Notes:** The team leads' contact details are shown in full in the dialog (they are contact persons, not workers).

## 2026-10-27 — Atelier: masked emails on screen, wash statistics on the KPI page
**Request:** (1) email addresses on Uitgifte & inname must not be fully visible on screen (GDPR), the database keeps them in
full; (2) keep track of how many clothes are washed, per day / festival / year.
**Plan:**
- Step 1: shared `maskEmail` (`fr***@gm***.com`); desk search results + chosen person masked; Ophalen shows a filled-in
  address (scan / known worker) masked read-only with "Wijzig" (empties the box); Openstaand's email column removed
  (follow-up request the same day, instead of masking it).
- Step 2: nothing stored; posted wash documents per Belgian day, linked to a festival by date (days after a festival stay
  in that season, "Geen festival" group); "Gewassen" section on the KPI page following its season dropdown.
**Changes:**
- Frontend: `lib/mask-email.ts` (new), `components/module-5/desk-screen.tsx`, `open-handouts.tsx`,
  `wash-stats-section.tsx` (new), `atelier-dashboard.tsx`, `lib/api.ts` (`getAtelierWashStats`), `lib/types.ts`,
  translations `atelier.desk.changeEmail` and `atelier.landing.wash.*` (nl + en).
- Backend: `module_5/wash_stats.py` (new), `GET /api/modules/module-5/stock/wash-stats?season_id=` in `stock_router.py`
  (KPI view right), `WashStatsResponse` schemas; tests `tests/modules/module_5/test_wash_stats.py`. No migration.
- Docs: Atelier help manual (KPI, desk, Openstaand chapters, nl + en), CLAUDE.md Atelier bullets.
**Verification:** `pytest tests/modules/module_5 tests/help` passed; `npx tsc --noEmit` (only pre-existing stale `.next`
type errors for module-9 routes) and eslint on the changed files clean. Not yet clicked through on localhost.
**Notes:** Washes before the season's first
festival are in no season. Next: "Maten double" on Data Upload/Download, waiting for the user's screenshots.

## 2026-10-26 — Atelier: bigger desk buttons, Openstaand grouped, desk mails, Reservaties progress
**Request:** four Atelier needs: (1) Ophalen/Terugbrengen buttons twice as tall and vertically centred; (2) Openstaand without
overlapping fields, a filter above every column, grouped ploeg → persoon → open pieces; (3) a mail to the person after every
Uitgifte and Inname, with subject/body per mail editable by admins on a new Instellingen screen; (4) Reservaties without
overlapping fields, a filter above every column and per ploeg how many of its Altsien Select festivals are filled in.
**Plan:**
- Shared: festival dropdown never shrunk (`shrink-0`, trigger `w-full`); reusable `column-filters.tsx` for the filter rows.
- Desk choice: `min-h-96` buttons, the screen fills the height under the topbar and centres the choice.
- Openstaand: one row per open piece, grouped client-side per team and person; Ploeg dropdown replaced by the column filter.
- Mails: `Atelier_mail_template` (handout/return: subject, body with placeholders, active), `notifications.py` renders them
  (HTML-escaped) and queues `send_email` as a background task; one person-level return call so a return = one mail;
  screen "Instellingen > E-mails" (`atelier.mailtemplates`) with placeholder buttons, live preview and test mail to yourself.
- Reservaties: `festivals_picked` per row (picks via `festivals_by_team`, done = persons > 0); "x / y" column with tooltip,
  "geen selectie" without picks, "niet gekozen" badge; filter row; unsaved rows stay visible.
**Changes:**
- Backend: model `atelier_mail_template.py` + migration `c8e2a5f1d394` (seeds both default Dutch texts),
  `module_5/notifications.py`, `module_5/mail_template_router.py` (`GET /mail-templates`, `PUT /mail-templates/{key}`,
  `POST /mail-templates/{key}/test`, included in `main.py`), `desk_service.return_person_lines` + `POST /desk/persons/{id}/return`
  (mails; the per-handout return endpoint stays, without mail), `POST /desk/handouts` mails, `reservation_service.festival_progress`
  + `festivals_picked` on `ReservationRowResponse`, screen `atelier.mailtemplates`.
- Frontend: `desk-screen.tsx` (buttons, centring, one return call), `open-handouts.tsx` (rewritten), `reservation-screen.tsx`,
  `atelier-festival-select.tsx`, new `column-filters.tsx`, `mail-templates-screen.tsx` + page `settings/mails`, sidebar link,
  `FALLBACK_SCREENS`, help route, `lib/api.ts` / `lib/types.ts`, `messages/{nl,en}.json`.
- Help manual `module_5/{nl,en}.md` (desk mail, Openstaand, Reservaties progress/filters, new E-mails chapter) + refreshed
  module-5 screenshots (new `mails.png`, added to `help-screenshots.mjs`).
- Tests: `tests/modules/module_5/test_mails.py` (new), `test_reservations.py` (`festivals_picked`).
**Verification:** full pytest suite 918 passed; `alembic upgrade head` on local Postgres; tsc (no errors in `src/`) and eslint
clean; backend restarted and the four screens checked on localhost via the help screenshots (temporary screenshot user removed).
**Notes:** the PDF handbooks (Gebruikershandleiding / Ontwikkelaarshandleiding) don't yet describe the new E-mails screen.
Mails only go out where Resend is configured (`RESEND_API_KEY`/`MAIL_FROM`); locally they're logged as skipped.

## 2026-10-26 — Atelier desk: message for an article without sizes
**Request:** on test the desk showed the package articles without any size to pick (the articles were imported, their
Artikelmaten not).
**Plan:** no code bug — sizes come from `Atelier_article_size`; show a clear message on such an article and keep the thumb left.
**Changes:** `components/module-5/desk-screen.tsx` (`desk.noSizes` message, thumb wrapped so its `mx-auto` doesn't push
the name right), `messages/{nl,en}.json`.
**Verification:** tsc (no errors in `src/`) and eslint clean.

## 2026-10-26 — Atelier: XLSX import of an export from another environment; festival box width
**Request:** uploading Atelier's article export (made on localhost) on test.rwcrew.eu gave "id … not found" on every row; the
desk's festival box overlapped the day box.
**Plan:**
- Sizes/articles import: an id that doesn't exist here (or a blank id) falls back to the natural key (name + fit / code):
  found = update, else create. A non-number id stays a row error.
- Festival select: minimum width instead of a fixed width.
**Changes:** `module_5/xlsx_imports.py` (`_find_by_id_or_key`), dialog hints (nl/en), help `module_5/{nl,en}.md`, CLAUDE.md,
`tests/modules/module_5/test_masterdata.py` (blank id + existing size is now "updated"; new test for foreign ids),
`components/module-5/atelier-festival-select.tsx` (`min-w-80`).
**Verification:** full pytest suite 911 passed; eslint clean on the festival select.

## 2026-10-25 — Documentation update: handbooks, help manuals, technical setup
**Request:** update all PDF documentation (Gebruikershandleiding, Ontwikkelaarshandleiding incl. technical setup, the module help manuals) with screenshots.
**Plan:**
- Screenshot tooling: Atelier/Walkies in the temporary screenshot user, Atelier personal data masked, module-5 + new KarTracker shots in the help script.
- Help manuals: screenshots for every Atelier chapter and the new KarTracker screens; refreshed KarTracker shots.
- Developer handbook v2.1 and user manual v1.1: Atelier, Walkies, new KarTracker screens, products moved to StockMaster, Altsien products step, `ATELIER_WEBHOOK_TOKEN` + public webhook, screens/rights appendices.
**Changes:**
- `docs/handleiding/screenshot_user.py` (atelier + walkies roles, Atelier names/emails exported for masking), `screenshots.py` (shots 48–56), `build_pdf.py` (keeps waiting for Edge's DevTools port when the first Edge process hands off — headless start failed otherwise).
- `frontend/scripts/help-screenshots.mjs`: module-5 list, 7 new module-2 shots, Plan een kar without the old team pick, masking via `.screenshot-namen.json`.
- `backend/app/help/content/module_5/*` (19 images + references, KPI text no longer says "next blocks"), `module_2/*` (7 new images, all refreshed).
- Developer handbook chapters 00–07: module table, KarTracker/StockMaster/Atelier sections, Walkies, env var table, public endpoints, module package/services/Atelier code section, recipes, Atelier wristband admin steps, screen-key appendix (KarTracker, TagScan, Atelier, Walkies); all screenshots retaken + 9 new. PDF 126 pages.
- User manual: Atelier chapter (screens, reservations, desk, stock, wristband scans), KarTracker Leveringsvolgorde/Planningsanalyses/Karcode/Speciale levertoeren, products under StockMaster, StockMaster TagScan book-in/Kar laden/nalevering, Altsien step 4, phone Karcode, festival-year checklist, FAQ, glossary, screen-name appendix. PDF 53 pages.
- CLAUDE.md: help manual list + screenshot login/masking + handbooks note.
**Verification:** `pytest tests/help` 28 passed; eslint on the screenshot script clean; both PDFs built without unknown cross-references; screenshots checked for masking (names/emails replaced). Temporary screenshot user removed (`cleanup`: nothing left).
**Notes:** the PDFs could not be page-rendered here for a visual check (no poppler) — worth a quick read-through. The user manual stays without screenshots, as before.

## 2026-10-26 — Atelier: block 5 (wristband scans via webhook + Test-scan)
**Request:** the next block: the wristband. It turned out we don't scan ourselves: the wristband company scans at our
counter and sends us a small JSON message via a webhook (example given). Also a screen to type the data or drop a JSON
file, since the company can only be connected from May 2027.
**Plan:** public webhook logging every message (shared-secret token, configurable, refused ones logged); scanner per
`data.device.id`, auto-registered and labelled; wristband number = `data.id`, new per festival; team by name; email
always optional; one global switch "Polsband verplicht bij Ophalen"; desk screen picks its scanner and polls scans;
Instellingen + Test-scan screens.
**Changes:** migration `b2d5f8a3c697` (`Atelier_scan`, `Atelier_scanner`, `Atelier_person_bracelet`, `Atelier_settings`;
`Atelier_person.bracelet_number` dropped, email nullable); config/env `ATELIER_WEBHOOK_TOKEN` (also
docker-compose.prod.yml + .env examples); `scan_service.py`, `scan_webhook_router.py`, `scan_router.py`;
`desk_service.py` (bracelet per festival, `bracelet_required`, `scan_id` → used, email optional); `desk_router.py`
(`/desk/scanners`, `/desk/scans`, dismiss, `/desk/persons/by-bracelet`, `/desk/wristband-required`); screens
`atelier.settings|scantest`. Frontend: desk screen (scanner dropdown, polling, scan card, pre-fill, size pre-select),
`atelier-settings.tsx`, `scan-test.tsx`, menu group Instellingen, translations, help, CLAUDE.md.
**Verification:** new `tests/modules/module_5/test_scans.py` (6 tests) + Atelier/help tests (82) passed; full backend
suite 910 passed; `tsc` + eslint clean; local DB migrated, backend restarted; `curl` to the local webhook → 401 + logged
(no token set locally).
**Notes:** the meaning of `token` is unknown (treated as a fixed secret; every message is logged to check). Existing
local wristband numbers (no festival) were dropped. To accept real messages on a server, set `ATELIER_WEBHOOK_TOKEN`
in its `.env` and restart the backend container.

## 2026-10-26 — Atelier desk: optional articles, clear "still has", return warning
**Request:** "Uitgeven" stayed disabled (the OneSize apron had no size selected) and a second pick-up gave "not
returned yet" although the user thought everything was back (the T-shirt had been left unticked at the return).
**Plan:** articles optional (click again to skip, single in-stock size pre-selected, at least one, hint why the button
is disabled); orange "still has" box with "Eerst terugbrengen" → return of that person; re-lookup after
`article_still_out`; confirmation on Terugbrengen when pieces stay unticked. Backend rules unchanged.
**Changes:** `components/module-5/desk-screen.tsx` (PickupForm selection model + missing hint + still-has box +
hand-over to ReturnForm; ReturnForm with `initialPerson`, open pick-ups via `useKeyedLoad`, "unticked" list and
confirm), translations nl/en, help chapter; new desk test (two pick-ups a day, only some articles).
**Verification:** Atelier/help tests 76 passed; `tsc` + eslint clean. Not clicked through by me (no login).
**Notes:** the local person "fredtest" (empty family name from before the name split) still has the T-shirt S out —
return it via Terugbrengen (search "fredtest").

## 2026-10-26 — Atelier desk: first + family name as the person, bracelet number
**Request:** split the name into first name and family name, entered first and then the email; the email is not
unique, the first + family name combination is. Also add a unique festival personal number from the future wristband.
**Plan:** follow-up of block 4 without plan mode.
**Changes:** migration `a1c4e7f2b586` (`Atelier_person`: `first_name`, `last_name`, unique `name_key`, email index no
longer unique, new unique optional `bracelet_number`; existing names split on the first space). `desk_service.py`
(`name_key`, `find_person`, person found by name, latest email kept, `bracelet_in_use`), `desk_router.py` (search also
by bracelet number, `GET /desk/persons/lookup?first_name=&last_name=`), schemas, Ophalen form order first name →
family name → email → bracelet number (lookup by name), bracelet shown in search results and Openstaand;
translations, help, CLAUDE.md.
**Verification:** desk tests updated + new test (email shared by two persons, bracelet unique, search by bracelet);
Atelier/help tests 75 passed; full backend suite 903 passed; `tsc` + eslint clean; local DB migrated, backend restarted.
**Notes:** the bracelet number is optional until block 5 (scan the wristband QR). The local test person "fredtest" had
no space in the name, so its family name is empty.

## 2026-10-26 — Atelier: block 4 (counter desk)
**Request:** plan and build block 4 of Atelier (the counter: hand-out and return).
**Plan:** per person name + email (required) + team + festival + day; 1 piece per package article with the size picked
at the desk, never an article the person still has; package quantity always 1 (field stays, fixed at 1); warning only
when more people than reserved; return = find the person and tick what's back; open list only; web screen. Every
transaction starts with a big "Ophalen" / "Terugbrengen" choice (added by the user during planning).
**Changes:** migration `f9b3d6e1a475` (`Atelier_person`, `Atelier_handout`, `Atelier_handout_line`; package lines set
to 1). Backend: `stock_service.py` (`hand_out`, `return_pieces`, `use_desk` guard on reversals),
`reservation_service.py` (`PACKAGE_QUANTITY` = 1 everywhere), `desk_service.py`, `desk_router.py` (`/desk/teams`,
`/desk/persons`, `/desk/context`, `/desk/handouts` + `/return` + `/cancel`, `/desk/persons/{id}/open`, `/desk/open`,
`/desk/stats`); screens `atelier.desk|open`. Frontend: sidebar group Balie, `desk-screen.tsx` (choice → pick-up / return),
`open-handouts.tsx`, `desk-common.ts`, KPI `desk-stats-section.tsx`, Pakket dialog quantity read-only 1, desk bookings
not undoable on Boekingen; translations nl/en; help chapters; CLAUDE.md. Tests updated for quantity 1.
**Verification:** new `tests/modules/module_5/test_desk.py` (5 tests) + Atelier/help tests (74) passed; full backend
suite 902 passed; `tsc` + eslint clean; local DB migrated, backend restarted. Not clicked through by me (no login).
**Notes:** on XLSX "Pakketlijnen" any quantity is stored as 1 without a separate row note (the import result has no
note for successful rows). Block 5 (wristband QR) will add a code to `Atelier_person`.

## 2026-10-25 — Atelier: block 3 (Stock)
**Request:** plan and build block 3 of Atelier (stock), after asking what the user had to explain.
**Plan:** no purchase orders and no suppliers — goods are simply received; own washing (to wash → available);
start empty; write-off with a reason; stock count; undo by counter-booking; shortage on Voorbereiden, a "Te
bestellen" list (+PDF) and a minimum-stock warning. Stock per article size and status (available / to wash /
handed out), following StockMaster's stock-service pattern.
**Changes:** migration `e8a2c5d9f364` (`Atelier_stock_document`, `Atelier_stock_movement`, `Atelier_stock_balance`).
Backend: `module_5/stock_service.py` (receive, wash, write_off, count_stock, reverse_document), `stock_needs.py`
(overview, order needs, min-stock alerts), `stock_pdfs.py` (Boekingsbon, Bestellijst), `stock_router.py` (`/stock`,
`/stock/receipt|wash|write-off|count`, `/stock/documents[/{id}[/reverse|/pdf]]`, `/stock/order-needs[/pdf]`,
`/stock/min-stock`, `/stock/totals`); 7 new screens; preparation size estimates carry available/owned; article sizes
with stock history can't be removed. Frontend: sidebar group Stock with `stock-overview.tsx`,
`stock-booking-screen.tsx` (Ontvangst/Wassen/Afboeken), `stock-count.tsx`, `stock-bookings.tsx`, `order-needs.tsx`,
minimum-stock banner in the layout, KPI `stock-totals-section.tsx`, red/orange stock on Voorbereiden; translations
nl/en; help chapters; CLAUDE.md.
**Verification:** `tests/modules/module_5/test_stock.py` (6 tests) + Atelier/help tests (69) passed; full backend
suite 897 passed; `tsc` + eslint clean; local DB migrated, backend restarted. Screens not clicked through by me (no login).
**Notes:** the planned "Stock" export tile on Data Upload/Download was left out (the stock overview shows the same
and the tile component expects an import); can be added if wanted. Block 4 will add hand-out (available →
handed out) and return (handed out → to wash) through `stock_service.py`.

## 2026-10-25 — Atelier KPI: teams forgotten at a festival
**Request:** an indication when a team got a reservation at one festival but was forgotten at another.
**Plan:** signal based on the season's other reservations (not Altsien Select), shown only on the KPI page: a team
with persons > 0 at another active festival of the season and nothing here (no persons, no note) counts as
"forgotten"; 0 persons + a note silences it.
**Changes:** `reservation_router.py` `_forgotten_teams` + `teams_missing` on `FestivalReservationStatsResponse`;
`reservation-stats-section.tsx` column "Vergeten?" (count opens the team names + link to that festival's
Reservaties); types, translations nl/en, KPI help chapter, CLAUDE.md.
**Verification:** new test in `test_reservations.py`; module-5 + help tests passed (63); `tsc` + eslint clean;
backend restarted.

## 2026-10-25 — Atelier: Ploegpakketten merged into Reservaties (package per festival)
**Request:** merge the Ploegpakketten functionality into the Reservaties screen, so everything is entered on one page.
**Plan:** the package becomes per festival (not copied automatically; "copy from the same festival last year" is
proposed); the Ploegpakketten screen is removed; Reservaties lists all active teams. Persons and package share the
key festival + team, so a reservation gets its own package lines.
**Changes:** migration `d7f1b4c8e253`: new `Atelier_reservation_line`, existing season packages copied onto every
active festival of their season, `Atelier_team_package` and screen `atelier.teampackages` (+ its rights) removed.
Backend: `reservation_service.py` rewritten (persons/note/lines via one `upsert_reservation`, `upsert_line`,
`previous_festival` + `copy_from_previous_festival`), `team_package_service.py` deleted, `reservation_router.py`
(`PUT /reservations/{festival}` with `lines`, `GET …/previous`, `POST …/copy-previous`), preparation reads the
reservation's lines, `masterdata_router.py` lost `/teams` + `/team-packages*` (masterdata-stats without season),
XLSX "Ploegpakketten" → "Pakketlijnen" (season, festival, team, article_code, quantity_per_person). Frontend:
`reservation-screen.tsx` (Pakket dialog per team, chips, "no package" warning, copy-from-last-year panel, one
Save), `team-package-management.tsx` + page + menu link removed, KPI sections adjusted, upload tile, translations,
help manual, CLAUDE.md.
**Verification:** `test_reservations.py` rewritten (10 tests) + module_5/help/StockMaster tests (178) passed; full
backend suite 890 passed; `tsc` + eslint clean; local DB
migrated — 3 teams × 9 package lines became 18 lines on Parklife 2026 and Rock Werchter 2026; backend restarted.
**Notes:** a reservation with 0 persons but a package is kept (shows the package for later). Downgrade of the
migration restores an empty season-package table only.

## 2026-10-25 — Atelier: block 2 (Reservations + Voorbereiden)
**Request:** plan and build block 2 of Atelier (reservations), after listing what the user had to explain.
**Plan:** one reservation = team + festival → persons, entered by the atelier team; the team works every festival day
and returns the clothing every evening, so each day needs persons × package; teams offered = package this season +
festival picked in Altsien Select (all festivals when nothing picked); sizes estimated with a size split (%) per
article; output = totals per day, bundle per team, picklist PDF. Changing/locking reservations: decided later.
**Changes:** table `Atelier_reservation` (unique festival+team, `updated_by(_name)` = session user) and
`Atelier_article_size.size_share_pct` — migration `c6e9a3b7d142`. Screens `atelier.reservations|preparation`.
Backend `module_5/reservation_router.py` (`/festivals`, `/reservations`, `PUT /reservations/{festival}`,
`/preparation`, `/preparation/pdf`, `/reservation-stats`), `reservation_service.py` (only writer, `offered_teams`
reusing `module_2/plan_kar_service.festivals_by_team`), `preparation_service.py` (calculation, largest-remainder size
split), `picklist_pdf.py`; Reservaties XLSX tile + `size_share_pct` column in `xlsx_imports.py`; article form checks
the split adds up to 100%. `module_4/pdf_layout.py`: `StockMasterPDF` got optional `accent_color`/`brand` (defaults
unchanged) so Atelier's PDF is red; `require_view_on_any` moved to `module_5/deps.py`. Frontend: sidebar group
Reservaties, `reservation-screen.tsx`, `preparation-screen.tsx`, `atelier-festival-select.tsx` (`?festival=`),
`reservation-stats-section.tsx` on the KPI page, % per size in the article form; translations nl/en; help chapters.
**Verification:** `tests/modules/module_5/test_reservations.py` (8 tests) + Atelier/StockMaster/help tests (178)
passed; full backend suite 890 passed; `tsc --noEmit` (src) and eslint clean; migration applied locally, backend restarted.
Screens not clicked through in a browser by me (no local login).
**Notes:** reservation history / deadline lock still to be decided. The picklist for a subset of teams also estimates
sizes for that subset only.

## 2026-10-25 — Atelier: roadmap + block 1 (Masterdata)
**Request:** start building the Atelier module's content (work clothing handed out before a shift and returned after
it), in blocks: masterdata, reservations, procurement/inbound, digital wristband reading, later RFID per piece.
Sizes must have a fit (Women/Men/Unisex) and a "OneSize".
**Plan:** roadmap of 6 blocks (1 masterdata, 2 reservations per team + festival + day entered by the atelier team,
3 suppliers + purchasing/receiving + stock service with wash cycle, 4 counter-desk hand-out/return, 5 wristband QR
code, 6 RFID via TagScan). Block 1: own article catalogue with size variants, sizes = name + fit, team packages per
season (article + pieces per person, size chosen at the desk), copy from last season, XLSX upload/download, KPI counts.
Decisions: workers aren't in a database (name typed at the desk, later the wristband); everything is returned; one
atelier store.
**Changes:** tables `Atelier_size` (unique name+fit, seeded XS–XXL × Women/Men/Unisex + OneSize·Unisex),
`Atelier_article` (unique code, colour, cost, picture, `is_tag_managed` for block 6, active), `Atelier_article_size`,
`Atelier_team_package` (season + team + article, quantity per person) — migration `b5d8f2a6c931`. Screens
`atelier.articles|sizes|teampackages|dataupload`. Backend `module_5/masterdata_router.py` (CRUD, picture, team
packages + `/team-packages/previous` + `/copy-previous`, `/masterdata-stats`, XLSX template/import/export per table),
`team_package_service.py` (the only writer of packages), `xlsx_imports.py`; `router.py` got `GET /seasons` and the
article picture GET. Frontend: sidebar group Masterdata (Artikelen > Maten, Ploegpakketten, Data Upload/Download),
`article-management.tsx`, `size-management.tsx`, `team-package-management.tsx`, `atelier-data-upload-download.tsx`,
KPI `masterdata-stats-section.tsx`, own season dropdown (`atelier-season-select.tsx`); translations nl/en; help manual
chapters; landing `FALLBACK_SCREENS`; CLAUDE.md.
**Verification:** new `tests/modules/module_5/test_masterdata.py` (11 tests) + full backend suite 883 passed;
`tsc --noEmit` (src) and eslint clean on the Atelier files; migration applied to local Postgres (19 sizes seeded),
backend restarted and healthy. The screens were not clicked through in a browser (no local login available to me).
**Notes:** deleting an article in a package / a size used by an article is refused (deactivate instead); unticking a
size on an article deletes it — once stock exists (block 3) that must become a refusal. Packages of a closed season
are still editable (no season lock yet). Help screenshots not made yet (`npm run help:screenshots module-5`).

## 2026-10-25 — Karcode Simulator: scan uses the last 3 digits
**Request:** when scanning a QR code in the Karcode Simulator, take only the last 3 digits of the scanned value.
**Plan:** small follow-up, no plan mode: `handleScanned` keeps the scanned value's digits and uses the last 3.
**Changes:** `components/module-2/karcode-calculator.tsx` (web + phone), help manual sentence (nl/en), CLAUDE.md.
**Verification:** eslint + `tsc --noEmit` clean; help tests.
**Notes:** a scanned value without any digit still shows the "digits only" error. Typing is not limited to 3 digits.

## 2026-10-25 — KarTracker: Karcode Simulator in the phone app (+ QR scan)
**Request:** the Karcode Simulator also in KarTracker's phone app, only for the people allowed to use it; the kar
number can be filled in by scanning the kar's existing QR code, and must also be possible to type manually.
**Plan:** share the calculator between web and phone (`variant` prop), phone page + menu row gated by the existing
`kartracker.karcodesimulator` right, a "Scan QR" key opening the existing `QrScanner` full screen; no backend change.
**Changes:** `components/module-2/karcode-calculator.tsx` (was the body of `karcode-simulator.tsx`, now with the
scan overlay, phone layout with bigger keys and no native keyboard popping up), `karcode-simulator.tsx` = web
heading + calculator; phone `kartracker-phone-rights.ts` (`canViewKarcode`), `kartracker-phone-routes.ts`
(`karcode`), `kartracker-phone-menu.tsx` (row with lock icon), new page `/m/(signed-in)/module-2/karcode`;
translations (`scanQr`, `scanHint`, `scanCancel`, `phone.menu.karcodeDescription`); help manual (phone list +
scan paragraph), CLAUDE.md.
**Verification:** `tsc --noEmit` and eslint clean on the changed files; help tests 30 passed.
**Notes:** a QR text that isn't only digits shows "a kar number consists of digits only" on the display. The scan
button is on the web screen too (camera needs https or localhost). Not yet tried on a real phone.

## 2026-10-25 — KarTracker: Karcode Simulator + Instellingen (karcode formula)
**Request:** a "Karcode Simulator" screen under Acties (below Manuele karbeweging) that computes the code of a kar's
lock from its kar number (Excel: `=LEFT((B5*500)+3118;4)`), styled like a calculator for user adoption, plus a new
"Instellingen" menu where admins change the formula.
**Plan:** one active formula as a free Excel-like expression in a single-row `KarTracker_settings` table, evaluated
safely server-side (AST whitelist, never eval); two new screens with their own rights; the simulator never sees the
formula itself; calculator-style UI with a seven-segment display, keypad, keyboard support and recent codes.
**Changes:** model `kartracker_settings.py` + migration `a7c3e9f1b524` (row 1 = `LEFT(kar*500+3118; 4)`);
`module_2/karcode_formula.py` (variable `kar`, + - * / ^, LEFT/RIGHT/MID/MOD/INT/ROUND/ABS, `;` between arguments,
`,`/`.` decimals; errors `code|param`); `module_2/karcode_router.py` (`GET /karcode`, `GET /settings`,
`POST /settings/karcode/preview`, `PUT /settings/karcode`), included in `main.py`; screens
`kartracker.karcodesimulator` (20) and `kartracker.settings` (21); frontend pages
`module-2/actions/karcode-simulator` and `module-2/settings`, components `karcode-simulator.tsx`,
`kartracker-settings.tsx`, `karcode-common.ts`, sidebar link + new "Instellingen" group, help routes, nl/en
translations, help manual chapters `karcode` and `settings`.
**Verification:** `tests/modules/module_2/test_karcode.py` (34 tests: evaluator incl. kar 36 → 2111, refused input,
rights per screen, preview doesn't save) and the full backend suite: 873 passed. `tsc --noEmit` and eslint clean on
the changed files. Migration applied locally, backend restarted, `/api/health` ok and `/karcode` answers 401
without login.
**Notes:** not yet clicked through in the browser; no help screenshots yet for the two chapters
(`npm run help:screenshots module-2`); no phone (`/m`) screen.

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
