# Atelier steps of the mass test.
#
# AtelierDesk: last year's Uitgifte/Inname, replayed on the counter desk in
# time order with the real moment (`booked_at`, super admin only):
# - Ophalen      = POST /desk/handouts (one piece per row; email/wristband empty)
# - Terugbrengen = the person's open pieces of that article + size (oldest
#   first) through POST /desk/persons/{id}/return
# Teams are matched by name or alias, the festival by the day, articles by
# name (or code) and sizes by fit + name. A row that can't be resolved or
# breaks a desk rule is skipped and logged; the others of its transaction go.
# Back-dated desk bookings never send a mail.

from collections import defaultdict
from datetime import date, datetime

from masstest.client import ApiClient
from masstest.ledger import Ledger, transaction_key
from masstest.load_workbook import ATELIER_DESK, PICK_UP, RETURN
from masstest.report import BLOCKER, IssueLog
from masstest.steps.common import log_refusal, source_fields

ATELIER = "/api/modules/module-5"
MASTERDATA = "/api/modules/module-9"
MODULE = "atelier"
FIT_LABELS = {"men": "man", "women": "vrouw", "unisex": "unisex"}


def norm(value: object) -> str:
    """Lowercase with single spaces: how names are compared."""
    return " ".join(str(value or "").lower().split())


def _moment(value: object) -> str:
    """booked_at as ISO text without a zone (= Belgian time for the API)."""
    if isinstance(value, datetime):
        return value.replace(microsecond=0).isoformat()
    return str(value).strip().replace(" ", "T")


def _day(value: object) -> str:
    """The day as YYYY-MM-DD."""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()[:10]


class AtelierDeskStep:
    """Replays the Uitgifte/Inname sheet on the counter desk."""

    sheet = ATELIER_DESK
    module = MODULE

    def __init__(self) -> None:
        self.festivals_by_day: dict[str, list[dict]] = defaultdict(list)
        self.teams: dict[str, dict] = {}
        self.articles: dict[str, dict] = {}
        self.article_sizes: dict[tuple[int, str, str], int] = {}

    # --- Preflight ---------------------------------------------------------------

    def preflight(self, client: ApiClient, log: IssueLog) -> bool:
        """Check the account (super admin, desk and team rights) and load the
        lookups: festivals per day, teams with aliases, articles with sizes,
        and whether a wristband is required. Logs blockers, writes nothing."""
        ok = True
        me = client.call("GET", "/api/auth/me")
        if not me.ok:
            log_refusal(log, self.sheet, self.module, me, "Reading the logged-in account failed.", [], {}, BLOCKER)
            return False
        if not me.body.get("is_super_admin"):
            log.add(self.sheet, "not_super_admin", f"{me.body.get('email')} is not a super admin.", severity=BLOCKER,
                    module=self.module, request="GET /api/auth/me")
            ok = False
        for module_key, screen, right in (("module-5", "atelier.desk", "create"), ("module-9", "masterdata.teams", "view")):
            if module_key not in me.body.get("accessible_module_keys", []):
                log.add(self.sheet, "missing_right", f"The account has no access to {module_key}.", severity=BLOCKER,
                        params=["module access", module_key], module=self.module)
                ok = False
                continue
            permissions = client.call("GET", f"/api/modules/{module_key}/me/permissions")
            keys = (permissions.body or {}).get("creatable_screen_keys" if right == "create" else "viewable_screen_keys", [])
            if not permissions.ok or screen not in keys:
                log.add(self.sheet, "missing_right", f"The account lacks '{right}' on {screen}.", severity=BLOCKER,
                        params=[right, screen], module=self.module, request=f"GET /api/modules/{module_key}/me/permissions")
                ok = False
        if not ok:
            return False

        # Festivals of every season, per day.
        seasons = client.call("GET", f"{ATELIER}/seasons")
        for season in seasons.body if seasons.ok else []:
            festivals = client.call("GET", f"{ATELIER}/festivals", params={"season_id": season["id"]}, template=f"{ATELIER}/festivals")
            for festival in festivals.body if festivals.ok else []:
                for day in festival["days"]:
                    self.festivals_by_day[day].append(festival)

        # Teams by name and by alias.
        teams = client.call("GET", f"{MASTERDATA}/teams")
        for team in teams.body if teams.ok else []:
            for name in [team["name"], *team.get("aliases", [])]:
                self.teams.setdefault(norm(name), team)

        # Articles by name and code; article sizes by (article, fit, size name).
        sizes = client.call("GET", f"{ATELIER}/sizes")
        size_by_id = {size["id"]: size for size in (sizes.body if sizes.ok else [])}
        articles = client.call("GET", f"{ATELIER}/articles")
        for article in articles.body if articles.ok else []:
            self.articles.setdefault(norm(article["name"]), article)
            self.articles.setdefault(norm(article["code"]), article)
            for row in article["sizes"]:
                size = size_by_id.get(row["size_id"])
                if size:
                    self.article_sizes[(article["id"], size["fit"], norm(size["name"]))] = row["id"]
        for result in (seasons, teams, sizes, articles):
            if not result.ok:
                log_refusal(log, self.sheet, self.module, result, "A lookup the run needs failed.", [], {}, BLOCKER)
                ok = False

        # A required wristband would refuse every pick-up (the old lists have none).
        required = client.call("GET", f"{ATELIER}/desk/wristband-required")
        if required.ok and required.body is True:
            log.add(self.sheet, "bracelet_required", "Atelier requires a wristband number on every pick-up; last "
                    "year's list has none, so every Ophalen would be refused.", severity=BLOCKER, module=self.module,
                    request=f"GET {ATELIER}/desk/wristband-required")
            ok = False
        return ok

    # --- Run -----------------------------------------------------------------------

    def run(self, client: ApiClient, rows: list[dict], ledger: Ledger, log: IssueLog, dry_run: bool) -> None:
        """Every transaction in time order: resolve, skip what's loaded,
        send (or only check on a dry run)."""
        summary = log.summary(self.sheet)
        transactions: dict[str, list[dict]] = {}
        for row in rows:
            transactions.setdefault(str(row.get("transaction") or f"row{row.get('source_row')}"), []).append(row)
        ordered = sorted(transactions.values(), key=lambda group: (_moment(group[0].get("booked_at")), str(group[0].get("transaction"))))

        for group in ordered:
            summary.total += 1
            # Rows already loaded on this environment are skipped.
            keys = {id(row): transaction_key(self.sheet, str(row.get("source_file") or ""), [row]) for row in group}
            todo = [row for row in group if not ledger.is_done(keys[id(row)])]
            if not todo:
                summary.skipped_ledger += 1
                continue
            first = todo[0]
            action = norm(first.get("action"))
            context = self._context(first)

            festival = self._festival(first, todo, log, context)
            team = self._team(first, todo, log, context)
            lines = [(row, *self._article_size(row, log, context)) for row in todo]
            lines = [(row, article, size_id) for row, article, size_id in lines if size_id is not None]
            if festival is None or team is None or not lines:
                summary.errors += 1
                continue
            context.update(festival=festival["name"], team=team["name"])

            if action == PICK_UP:
                self._pick_up(client, ledger, log, keys, festival, team, lines, context, dry_run)
            elif action == RETURN:
                self._return(client, ledger, log, keys, lines, context, dry_run)
            else:
                log.add(self.sheet, "column_missing", f"Unknown action '{first.get('action')}' (ophalen/terugbrengen).",
                        params=["action"], module=self.module, **source_fields(todo))
                summary.errors += 1

    def _context(self, row: dict) -> dict:
        """The placeholders of descriptions and solutions for a row."""
        return {
            "person": f"{row.get('first_name')} {row.get('last_name')}",
            "day": _day(row.get("day") or row.get("booked_at")),
            "booked_at": _moment(row.get("booked_at")).replace("T", " "),
            "team": row.get("team"),
            "festival": row.get("festival") or "?",
        }

    def _festival(self, row: dict, rows: list[dict], log: IssueLog, context: dict) -> dict | None:
        """The festival running on the row's day (or the one named in the
        festival column); logged when none or several fit."""
        candidates = self.festivals_by_day.get(context["day"], [])
        if row.get("festival"):
            candidates = [festival for festival in candidates if norm(festival["name"]) == norm(row["festival"])]
        if len(candidates) == 1:
            return candidates[0]
        if not candidates:
            log.add(self.sheet, "festival_not_found", f"No festival found on {context['day']} for {context['person']}'s "
                    "transaction; it was skipped.", context=context, module=self.module, **source_fields(rows))
        else:
            names = ", ".join(festival["name"] for festival in candidates)
            log.add(self.sheet, "festival_ambiguous", f"Several festivals on {context['day']} ({names}); the "
                    "transaction was skipped.", params=[names], context=context, module=self.module, **source_fields(rows))
        return None

    def _team(self, row: dict, rows: list[dict], log: IssueLog, context: dict) -> dict | None:
        """The team by name or alias; logged when unknown."""
        team = self.teams.get(norm(row.get("team")))
        if team is None:
            log.add(self.sheet, "team_unknown", f"Group '{row.get('team')}' of {context['person']} matches no team or "
                    "alias; the transaction was skipped.", params=[str(row.get("team"))], context=context,
                    module=self.module, **source_fields(rows))
        return team

    def _article_size(self, row: dict, log: IssueLog, context: dict) -> tuple[dict | None, int | None]:
        """(article, article size id) of a row; logged and (None, None) when
        either is unknown, or when a pick-up row holds more than one piece."""
        where = {"context": {**context, "article": row.get("article"), "size": row.get("size"), "fit": row.get("fit")},
                 "module": self.module, **source_fields([row])}
        article = self.articles.get(norm(row.get("article")))
        if article is None:
            log.add(self.sheet, "article_unknown", f"Product '{row.get('article')}' (row {row.get('source_row')}) "
                    "matches no Atelier article; the row was skipped.", params=[str(row.get("article"))], **where)
            return None, None
        size_id = self.article_sizes.get((article["id"], norm(row.get("fit")), norm(row.get("size"))))
        if size_id is None:
            fit = FIT_LABELS.get(norm(row.get("fit")), str(row.get("fit")))
            # The fits the article does have this size in (e.g. only unisex), to help decide.
            other_fits = sorted(
                FIT_LABELS.get(key_fit, key_fit) for (article_id, key_fit, size), _id in self.article_sizes.items()
                if article_id == article["id"] and size == norm(row.get("size"))
            )
            elsewhere = ", ".join(other_fits) or "none"
            log.add(self.sheet, "size_unknown", f"Article {article['name']} has no size '{fit} {row.get('size')}' (row "
                    f"{row.get('source_row')}; this size exists for: {elsewhere}); the row was skipped.",
                    params=[article["name"], str(row.get("size")), fit, elsewhere], **where)
            return None, None
        quantity = int(row.get("quantity") or 1)
        if norm(row.get("action")) == PICK_UP and quantity != 1:
            log.add(self.sheet, "quantity_not_one", f"{context['person']} picked up {quantity} × {article['name']} in "
                    f"one row (row {row.get('source_row')}); the row was skipped.", params=[str(quantity)], **where)
            return None, None
        return article, size_id

    def _pick_up(self, client, ledger, log, keys, festival, team, lines, context, dry_run) -> None:
        """Ophalen of the resolved rows as one pick-up."""
        summary = log.summary(self.sheet)
        rows = [row for row, _article, _size in lines]
        if dry_run:
            summary.checked += 1
            return
        first = rows[0]
        payload = {
            "first_name": str(first["first_name"]),
            "last_name": str(first["last_name"]),
            "email": first.get("email") or None,
            "festival_id": festival["id"],
            "team_id": team["id"],
            "day": context["day"],
            "lines": [{"article_id": article["id"], "article_size_id": size_id} for _row, article, size_id in lines],
            "booked_at": _moment(first.get("booked_at")),
        }
        result = client.call("POST", f"{ATELIER}/desk/handouts", json=payload)
        if result.ok:
            for row in rows:
                ledger.mark_done(keys[id(row)], {"handout_id": result.body["id"], "row": row.get("source_row")})
            summary.loaded += 1
            return
        pieces = ", ".join(f"{article['name']} {row.get('fit')} {row.get('size')}" for row, article, _size in lines)
        log_refusal(log, self.sheet, self.module, result,
                    f"Ophalen of {context['person']} ({context['team']}, {context['festival']}, {context['booked_at']}: "
                    f"{pieces}) was refused:", rows, context)
        summary.errors += 1

    def _return(self, client, ledger, log, keys, lines, context, dry_run) -> None:
        """Terugbrengen: the person's open pieces of each row's article + size
        (oldest first), returned in one transaction."""
        summary = log.summary(self.sheet)
        rows = [row for row, _article, _size in lines]
        if dry_run:
            # Which pieces are open depends on the pick-ups this run would load.
            summary.checked += 1
            return
        first = rows[0]
        person = client.call(
            "GET", f"{ATELIER}/desk/persons/lookup",
            params={"first_name": str(first["first_name"]), "last_name": str(first["last_name"])},
        )
        if not person.ok:
            log_refusal(log, self.sheet, self.module, person, f"Looking up {context['person']} failed.", rows, context)
            summary.errors += 1
            return
        if not person.body:
            log.add(self.sheet, "return_person_unknown", f"Terugbrengen of {context['person']} on {context['booked_at']}: "
                    "nobody with this name has pieces out; the return was skipped.", params=[context["person"]],
                    context=context, module=self.module, **source_fields(rows))
            summary.errors += 1
            return

        # Each row takes its quantity of open pieces of the same article + size.
        open_lines = sorted(person.body["open_lines"], key=lambda line: (line["handout_id"], line["line_id"]))
        taken: set[int] = set()
        chosen: list[int] = []
        sent_rows: list[dict] = []
        for row, article, _size_id in lines:
            quantity = int(row.get("quantity") or 1)
            matching = [
                line["line_id"] for line in open_lines
                if line["line_id"] not in taken and line["article_id"] == article["id"]
                and line["fit"] == norm(row.get("fit")) and norm(line["size_name"]) == norm(row.get("size"))
            ]
            if len(matching) < quantity:
                label = f"{article['name']} {row.get('fit')} {row.get('size')}"
                log.add(self.sheet, "return_not_open", f"Terugbrengen of {quantity} × {label} by {context['person']} on "
                        f"{context['booked_at']}: only {len(matching)} open; the row was skipped.",
                        params=[label, str(quantity), str(len(matching))], context=context, module=self.module,
                        **source_fields([row]))
                summary.errors += 1
                continue
            taken.update(matching[:quantity])
            chosen.extend(matching[:quantity])
            sent_rows.append(row)
        if not chosen:
            return

        result = client.call(
            "POST", f"{ATELIER}/desk/persons/{person.body['id']}/return",
            template=f"{ATELIER}/desk/persons/{{id}}/return",
            json={"line_ids": chosen, "booked_at": _moment(first.get("booked_at"))},
        )
        if result.ok:
            for row in sent_rows:
                ledger.mark_done(keys[id(row)], {"person_id": person.body["id"], "row": row.get("source_row")})
            summary.loaded += 1
            return
        log_refusal(log, self.sheet, self.module, result,
                    f"Terugbrengen of {context['person']} on {context['booked_at']} was refused:", sent_rows, context)
        summary.errors += 1
