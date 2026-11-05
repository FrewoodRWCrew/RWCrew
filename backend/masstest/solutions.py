# Proposed solutions per error code: what a person should do about an issue.
# Codes are the API's own refusal codes (desk_service / stock_service) plus
# the runner's own checks (unknown team, article, size, …). A code without a
# rule is treated as a bug that needs analysis.
#
# Templates use the error's parameters ({p1}, {p2}, …) and the row's context
# ({team}, {festival}, {day}, {person}, {article}, {size}, {fit}).

from dataclasses import dataclass

DATA = "data"
BUG = "bug"
PERFORMANCE = "performance"
SCREEN = "screen"
SETUP = "setup"


@dataclass(frozen=True)
class Rule:
    """What kind of issue a code is and what to do about it."""

    category: str
    solution: str


RULES: dict[str, Rule] = {
    # --- Refused by the Atelier desk / stock (API codes) ---
    "no_package": Rule(DATA, "Give team {p1} a package for {festival} on Atelier > Reservaties (or import it through "
                             "Data Upload > Pakketlijnen), then run again."),
    "not_in_package": Rule(DATA, "Add article {p1} to the package of team {team} for {festival} (Atelier > "
                                 "Reservaties), then run again."),
    "size_required": Rule(DATA, "Size {size} ({fit}) is not active on article {p1}: tick it on the article (Atelier > "
                                "Masterdata > Artikelen) or correct the subtype in the load workbook."),
    "article_twice": Rule(DATA, "One transaction holds the same article twice: the desk hands out one piece per article. "
                                "Split the rows into separate pick-ups or remove the duplicate."),
    "insufficient_stock": Rule(DATA, "Not enough {p1} available ({p2} in {p3}): book an Ontvangst or a Telling for this "
                                     "size before the pick-up's date, then run again."),
    "article_still_out": Rule(DATA, "{person} still has {p1} from an earlier pick-up and the source has no return in "
                                    "between. Add the missing return row (negative aantal), or decide whether the desk "
                                    "must allow a second piece (that would be a change request)."),
    "day_not_in_festival": Rule(DATA, "{day} is not a day of {festival}: correct the festival's dates in MasterData or "
                                      "the datum in the source."),
    "bracelet_required": Rule(SETUP, "Switch off 'Polsband verplicht' (Atelier > Instellingen) while loading last "
                                     "year's lists, or add wristband numbers to the source."),
    "bracelet_differs": Rule(DATA, "The person already has another wristband at this festival: check the source."),
    "name_required": Rule(DATA, "The ophaler is empty or only one word: fill in first and family name in the load "
                                "workbook."),
    "backdate_not_allowed": Rule(SETUP, "Run the mass test with a super-admin account (only a super admin may "
                                        "back-date bookings)."),
    "backdate_in_future": Rule(DATA, "The datum lies in the future: correct it in the source."),
    "concurrent_change": Rule(DATA, "Someone else booked the same person at the same moment: run again (the ledger "
                                    "skips what is already loaded)."),
    "email_invalid": Rule(DATA, "Correct the email address in the load workbook or leave it empty."),
    "article_size_inactive": Rule(DATA, "{p1} is inactive: activate the article/size or correct the load workbook."),
    # --- The runner's own checks before sending ---
    "festival_not_found": Rule(DATA, "No active festival covers {day}: check the datum, or create/activate the "
                                     "festival (with the right dates) in MasterData."),
    "festival_ambiguous": Rule(DATA, "Several festivals cover {day} ({p1}): make their dates not overlap, or fill in "
                                     "the festival column of the load workbook."),
    "team_unknown": Rule(DATA, "No team is called '{p1}': add it as an alias on the matching team (MasterData > "
                               "Teams > Aliassen), or create the team, then run again."),
    "article_unknown": Rule(DATA, "No Atelier article is called '{p1}': create it (Atelier > Masterdata > Artikelen) "
                                  "or change the product in the load workbook to an existing article name."),
    "size_unknown": Rule(DATA, "Article {p1} has no size '{p2}' for fit '{p3}' (it has this size for: {p4}). If the "
                               "old list's fit means the same, change the fit column of the load workbook (e.g. men → "
                               "unisex); otherwise tick that size on the article (create it under Maten first if "
                               "needed)."),
    "fit_unknown": Rule(DATA, "Subtype '{p1}' doesn't start with man/heren, vrouw/dames or unisex: correct it in the "
                              "load workbook."),
    "quantity_not_one": Rule(DATA, "The row hands out {p1} pieces at once; the desk gives 1 piece per article per "
                                   "person. Split it over the persons who really got them, or decide that the desk "
                                   "must allow more than one piece (a change request)."),
    "return_person_unknown": Rule(DATA, "Nobody called '{p1}' has pieces out: the pick-up was not loaded (see its "
                                        "issue) or the name is spelled differently there."),
    "return_not_open": Rule(DATA, "{p2} piece(s) returned but only {p3} open for {p1}: the matching pick-up was not "
                                  "loaded (see its issue) or the source has more returns than pick-ups."),
    "date_invalid": Rule(DATA, "The datum '{p1}' can't be read: use YYYY-MM-DD HH:MM:SS."),
    "quantity_invalid": Rule(DATA, "The aantal '{p1}' is not a whole number other than 0: correct it."),
    "column_missing": Rule(DATA, "The source has no column '{p1}': rename the header or adjust the converter."),
    # --- Set-up and environment ---
    "login_failed": Rule(SETUP, "Check the email/password of the mass-test account on this environment."),
    "not_super_admin": Rule(SETUP, "Use a super-admin account: back-dated bookings need it."),
    "missing_right": Rule(SETUP, "Give the mass-test account '{p1}' on screen {p2} (module's Access Rights > Roles)."),
    "network": Rule(SETUP, "The environment didn't answer ({p1}): check it is running and reachable, then run again."),
    "production_guard": Rule(SETUP, "{p1}"),
    # --- Bugs and speed ---
    "server_error": Rule(BUG, "Server error: find the request at {time} in the backend log, analyse the cause in the "
                              "code and fix it."),
    "unexpected_response": Rule(BUG, "The API answered in an unexpected way: analyse the request against the "
                                     "endpoint's code."),
    "slow_call": Rule(PERFORMANCE, "{p1} took {p2} s (limit {p3} s): check its queries (count, indexes, N+1) for "
                                   "this volume of data."),
    "screen_error": Rule(SCREEN, "The screen showed an error or a failed request: open it with the same data and "
                                 "analyse the console/network log."),
    "slow_screen": Rule(SCREEN, "The screen took {p1} s to load (limit {p2} s): profile its API calls and rendering "
                                "for this volume of data."),
}

UNKNOWN = Rule(BUG, "Refusal without a known cause: needs analysis in the code (code '{code}').")


class _Blank(dict):
    """Leaves an unknown placeholder visible instead of failing."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def propose(code: str, params: list[str] | None = None, context: dict | None = None) -> Rule:
    """The rule for a code, its solution filled in with the parameters and
    the row's context."""
    rule = RULES.get(code, UNKNOWN)
    values = _Blank(context or {})
    values["code"] = code
    for index, value in enumerate(params or [], start=1):
        values[f"p{index}"] = value
    return Rule(rule.category, rule.solution.format_map(values))
