# Atelier's bulk XLSX import/export ("Masterdata > Data Upload/Download"):
# one table per tile — Maten, Artikelen, Artikelmaten, Reservaties and
# Pakketlijnen — each with a template, an upload and an export in the same
# columns, so an export can be edited and uploaded again. Built on
# MasterData's shared helpers (module_9/xlsx_common.py): every row in its
# own SAVEPOINT, one result per row.
#
# Maten and Artikelen follow the usual "id" rule: a row with an existing id
# updates it, an empty id creates a new record. The others are links and are
# matched on their natural key instead (article code + size + fit; season +
# festival + team; + article code for a package line): a known combination
# is updated (or left "unchanged"), a new one is added. Reservations and
# package lines are written through module_5/reservation_service.py.

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.atelier_article import AtelierArticle
from app.db.models.atelier_article_size import AtelierArticleSize
from app.db.models.atelier_reservation import AtelierReservation
from app.db.models.atelier_reservation_line import AtelierReservationLine
from app.db.models.atelier_size import FITS, AtelierSize
from app.db.models.festival import Festival
from app.db.models.season import Season
from app.db.models.team import Team
from app.db.models.user import User
from app.modules.module_5.reservation_service import KEEP, upsert_line, upsert_reservation
from app.modules.module_9.xlsx_common import (
    ID_COLUMN,
    RowError,
    UploadedRow,
    build_xlsx,
    find_by_id,
    parse_yes_no,
    read_rows,
    run_import,
)
from app.schemas.atelier import AtelierImportRowResult

# Accepted spellings of a fit, lowercase (code, Dutch and English).
FIT_ALIASES = {
    "women": "women", "woman": "women", "dames": "women", "vrouw": "women", "w": "women", "f": "women",
    "men": "men", "man": "men", "heren": "men", "m": "men",
    "unisex": "unisex", "u": "unisex",
}


def _result(row_number: int, key: str | None, outcome, detail: str | None) -> AtelierImportRowResult:
    """One row's result, in the shape every Atelier import returns."""
    return AtelierImportRowResult(row_number=row_number, name=key, outcome=outcome, detail=detail)


def _required(row: UploadedRow, column: str) -> str:
    """A cell that must be filled in."""
    text = row.text(column)
    if text is None:
        raise ValueError(f"{column} is required")
    return text


def _parse_fit(row: UploadedRow) -> str:
    """The fit cell: women/men/unisex (or Dames/Heren, ...)."""
    text = _required(row, "fit")
    fit = FIT_ALIASES.get(text.lower())
    if fit is None:
        raise ValueError(f'fit "{text}" must be one of {", ".join(FITS)}')
    return fit


def _parse_int(row: UploadedRow, column: str, *, minimum: int, required: bool = False) -> int | None:
    """A whole number of at least `minimum`; blank gives None (unless required)."""
    text = row.text(column)
    if text is None:
        if required:
            raise ValueError(f"{column} is required")
        return None
    try:
        number = float(text)
    except ValueError:
        raise ValueError(f'{column} "{text}" is not a number') from None
    if number != int(number) or number < minimum:
        raise ValueError(f"{column} must be a whole number of at least {minimum}")
    return int(number)


def _find_size(db: Session, name: str, fit: str) -> AtelierSize:
    """The size with this name (ignoring case) and fit."""
    size = db.scalar(select(AtelierSize).where(func.lower(AtelierSize.name) == name.lower(), AtelierSize.fit == fit))
    if size is None:
        raise ValueError(f'size "{name} · {fit}" not found')
    return size


def _find_article(db: Session, code: str) -> AtelierArticle:
    """The article with this code (ignoring case)."""
    article = db.scalar(select(AtelierArticle).where(func.lower(AtelierArticle.code) == code.lower()))
    if article is None:
        raise ValueError(f'article code "{code}" not found')
    return article


def _find_by_id_or_key(db: Session, model: type, row: UploadedRow, by_key: Callable[[], object | None]):
    """The record named by the row's id, or — when that id doesn't exist in
    this database (e.g. an export from another environment, where the ids
    differ) — the record with the same natural key, or None (= create).
    A blank id also matches by natural key, so re-uploading a template row
    never creates a duplicate; a non-number id stays a row error."""
    try:
        record = find_by_id(db, model, row)
    except ValueError as error:
        if not str(error).endswith("not found"):
            raise
        record = None
    return record if record is not None else by_key()


def _sizes_by_id(db: Session) -> dict[int, AtelierSize]:
    """Every size by id, for the exports."""
    return {size.id: size for size in db.scalars(select(AtelierSize)).all()}


# --- Maten -------------------------------------------------------------------

SIZE_COLUMNS = [ID_COLUMN, "name", "fit", "sort_order", "active"]


def _import_sizes(db: Session, file_bytes: bytes, _user: User) -> list[AtelierImportRowResult]:
    def apply_row(row: UploadedRow):
        name = row.text("name")
        try:
            name = _required(row, "name")
            fit = _parse_fit(row)
            clash = db.scalar(
                select(AtelierSize).where(func.lower(AtelierSize.name) == name.lower(), AtelierSize.fit == fit)
            )
            size = _find_by_id_or_key(db, AtelierSize, row, lambda: clash)
            if clash is not None and clash is not size:
                raise ValueError("This size already exists for this fit")
            # Optional columns left out of the file keep their current value.
            values = {"name": name, "fit": fit}
            if row.has("sort_order"):
                values["sort_order"] = _parse_int(row, "sort_order", minimum=0) or 0
            if row.has("active"):
                values["active"] = parse_yes_no("active", row.value("active"), default=True)
            if size is None:
                db.add(AtelierSize(**values))
                return f"{name} · {fit}", "created"
            for field, value in values.items():
                setattr(size, field, value)
            return f"{name} · {fit}", "updated"
        except ValueError as error:
            raise RowError(str(error), name) from None

    return run_import(read_rows(file_bytes), db, apply_row, _result)


def _export_sizes(db: Session) -> bytes:
    sizes = sorted(db.scalars(select(AtelierSize)).all(), key=lambda size: (FITS.index(size.fit), size.sort_order))
    rows = [[size.id, size.name, size.fit, size.sort_order, "yes" if size.active else "no"] for size in sizes]
    return build_xlsx("Maten", SIZE_COLUMNS, rows)


# --- Artikelen -------------------------------------------------------------------

ARTICLE_COLUMNS = [ID_COLUMN, "code", "name", "description", "colour", "cost", "is_tag_managed", "active"]


def _parse_cost(row: UploadedRow) -> Decimal | None:
    """The price per piece: blank, or a number ≥ 0 (comma or dot decimals)."""
    text = row.text("cost")
    if text is None:
        return None
    try:
        cost = Decimal(text.replace(",", "."))
    except InvalidOperation:
        raise ValueError(f'cost "{text}" is not a number') from None
    if cost < 0:
        raise ValueError("cost can't be negative")
    return cost.quantize(Decimal("0.01"))


def _import_articles(db: Session, file_bytes: bytes, _user: User) -> list[AtelierImportRowResult]:
    def apply_row(row: UploadedRow):
        code = row.text("code")
        try:
            code = _required(row, "code")
            clash = db.scalar(select(AtelierArticle).where(func.lower(AtelierArticle.code) == code.lower()))
            article = _find_by_id_or_key(db, AtelierArticle, row, lambda: clash)
            if clash is not None and clash is not article:
                raise ValueError("An article with this code already exists")
            # Optional columns left out of the file keep their current value.
            optional = {
                "description": lambda: row.text("description"),
                "colour": lambda: row.text("colour"),
                "cost": lambda: _parse_cost(row),
                "is_tag_managed": lambda: parse_yes_no("is_tag_managed", row.value("is_tag_managed"), default=False),
                "active": lambda: parse_yes_no("active", row.value("active"), default=True),
            }
            values = {"code": code, "name": _required(row, "name")}
            values.update({field: parse() for field, parse in optional.items() if row.has(field)})
            if article is None:
                db.add(AtelierArticle(**values))
                return code, "created"
            for field, value in values.items():
                setattr(article, field, value)
            return code, "updated"
        except ValueError as error:
            raise RowError(str(error), code) from None

    return run_import(read_rows(file_bytes), db, apply_row, _result)


def _export_articles(db: Session) -> bytes:
    articles = db.scalars(select(AtelierArticle).order_by(AtelierArticle.name)).all()
    rows = [
        [
            article.id, article.code, article.name, article.description, article.colour,
            float(article.cost) if article.cost is not None else None,
            "yes" if article.is_tag_managed else "no", "yes" if article.active else "no",
        ]
        for article in articles
    ]
    return build_xlsx("Artikelen", ARTICLE_COLUMNS, rows)


# --- Artikelmaten (which sizes an article comes in) ----------------------------------

ARTICLE_SIZE_COLUMNS = ["article_code", "size", "fit", "min_stock", "size_share_pct", "active"]


def _parse_share(row: UploadedRow) -> Decimal | None:
    """The size split (%): blank, or a number from 0 to 100. Whether an
    article's shares add up to 100 isn't checked per row: an incomplete split
    simply falls back to an equal split when preparing."""
    text = row.text("size_share_pct")
    if text is None:
        return None
    try:
        share = Decimal(text.replace(",", ".").rstrip("%").strip())
    except InvalidOperation:
        raise ValueError(f'size_share_pct "{text}" is not a number') from None
    if not 0 <= share <= 100:
        raise ValueError("size_share_pct must be between 0 and 100")
    return share.quantize(Decimal("0.01"))


def _import_article_sizes(db: Session, file_bytes: bytes, _user: User) -> list[AtelierImportRowResult]:
    def apply_row(row: UploadedRow):
        key = None
        try:
            article = _find_article(db, _required(row, "article_code"))
            size = _find_size(db, _required(row, "size"), _parse_fit(row))
            key = f"{article.code} · {size.name} · {size.fit}"
            # Optional columns left out of the file keep their current value.
            values = {}
            if row.has("min_stock"):
                values["min_stock"] = _parse_int(row, "min_stock", minimum=0)
            if row.has("size_share_pct"):
                values["size_share_pct"] = _parse_share(row)
            if row.has("active"):
                values["active"] = parse_yes_no("active", row.value("active"), default=True)

            existing = db.scalar(
                select(AtelierArticleSize).where(
                    AtelierArticleSize.article_id == article.id, AtelierArticleSize.size_id == size.id
                )
            )
            if existing is None:
                if not size.active:
                    raise ValueError("This size is inactive and can't be added")
                db.add(AtelierArticleSize(article_id=article.id, size_id=size.id, **values))
                return key, "created"
            if all(getattr(existing, field) == value for field, value in values.items()):
                return key, "unchanged"
            for field, value in values.items():
                setattr(existing, field, value)
            return key, "updated"
        except ValueError as error:
            raise RowError(str(error), key or row.text("article_code")) from None

    return run_import(read_rows(file_bytes), db, apply_row, _result)


def _export_article_sizes(db: Session) -> bytes:
    sizes = _sizes_by_id(db)
    rows = []
    for article in db.scalars(select(AtelierArticle).order_by(AtelierArticle.code)).all():
        lines = db.scalars(select(AtelierArticleSize).where(AtelierArticleSize.article_id == article.id)).all()
        for line in sorted(lines, key=lambda item: (FITS.index(sizes[item.size_id].fit), sizes[item.size_id].sort_order)):
            size = sizes[line.size_id]
            share = float(line.size_share_pct) if line.size_share_pct is not None else None
            rows.append([article.code, size.name, size.fit, line.min_stock, share, "yes" if line.active else "no"])
    return build_xlsx("Artikelmaten", ARTICLE_SIZE_COLUMNS, rows)


# --- Reservaties and Pakketlijnen (per festival, per team) ---------------------------


def _find_festival_and_team(db: Session, row: UploadedRow) -> tuple[Festival, Team]:
    """The row's festival (by season + name, ignoring case) and team."""
    season_name = _required(row, "season")
    season = db.scalar(select(Season).where(Season.name == season_name))
    if season is None:
        raise ValueError(f'season "{season_name}" not found')
    festival_name = _required(row, "festival")
    festival = db.scalar(
        select(Festival).where(Festival.season_id == season.id, func.lower(Festival.name) == festival_name.lower())
    )
    if festival is None:
        raise ValueError(f'festival "{festival_name}" not found in season {season.name}')
    team_name = _required(row, "team")
    team = db.scalar(select(Team).where(func.lower(Team.name) == team_name.lower()))
    if team is None:
        raise ValueError(f'team "{team_name}" not found')
    return festival, team


RESERVATION_COLUMNS = ["season", "festival", "team", "persons", "note"]


def _import_reservations(db: Session, file_bytes: bytes, user: User) -> list[AtelierImportRowResult]:
    def apply_row(row: UploadedRow):
        key = None
        try:
            festival, team = _find_festival_and_team(db, row)
            key = f"{festival.name} · {team.name}"
            persons = _parse_int(row, "persons", minimum=0, required=True)
            note = row.text("note") if row.has("note") else KEEP
            return key, upsert_reservation(db, user, festival, team.id, persons=persons, note=note)
        except ValueError as error:
            raise RowError(str(error), key or row.text("team")) from None

    return run_import(read_rows(file_bytes), db, apply_row, _result)


def _export_reservations(db: Session) -> bytes:
    rows = db.execute(
        select(Season.name, Festival.name, Team.name, AtelierReservation.persons, AtelierReservation.note)
        .join(Festival, Festival.id == AtelierReservation.festival_id)
        .join(Season, Season.id == AtelierReservation.season_id)
        .join(Team, Team.id == AtelierReservation.team_id)
        .order_by(Season.name, Festival.start_date, Team.name)
    ).all()
    return build_xlsx("Reservaties", RESERVATION_COLUMNS, [list(row) for row in rows])


PACKAGE_LINE_COLUMNS = ["season", "festival", "team", "article_code", "quantity_per_person"]


def _import_package_lines(db: Session, file_bytes: bytes, user: User) -> list[AtelierImportRowResult]:
    def apply_row(row: UploadedRow):
        key = None
        try:
            festival, team = _find_festival_and_team(db, row)
            article = _find_article(db, _required(row, "article_code"))
            key = f"{festival.name} · {team.name} · {article.code}"
            quantity = _parse_int(row, "quantity_per_person", minimum=1, required=True)
            return key, upsert_line(db, user, festival, team.id, article.id, quantity)
        except ValueError as error:
            raise RowError(str(error), key or row.text("team")) from None

    return run_import(read_rows(file_bytes), db, apply_row, _result)


def _export_package_lines(db: Session) -> bytes:
    rows = db.execute(
        select(Season.name, Festival.name, Team.name, AtelierArticle.code, AtelierReservationLine.quantity_per_person)
        .join(AtelierReservation, AtelierReservation.id == AtelierReservationLine.reservation_id)
        .join(Festival, Festival.id == AtelierReservation.festival_id)
        .join(Season, Season.id == AtelierReservation.season_id)
        .join(Team, Team.id == AtelierReservation.team_id)
        .join(AtelierArticle, AtelierArticle.id == AtelierReservationLine.article_id)
        .order_by(Season.name, Festival.start_date, Team.name, AtelierArticle.code)
    ).all()
    return build_xlsx("Pakketlijnen", PACKAGE_LINE_COLUMNS, [list(row) for row in rows])


# --- The tiles, as used by masterdata_router.py ------------------------------------------


@dataclass(frozen=True)
class XlsxTable:
    """One Data Upload/Download tile's template, upload and export."""

    # The URL part: "/<path>-import", "/<path>-import/template", "/<path>/export".
    path: str
    columns: list[str]
    # (db, file bytes, session user) -> one result per row.
    import_rows: Callable[[Session, bytes, User], list[AtelierImportRowResult]]
    export: Callable[[Session], bytes]
    sheet_title: str

    def template(self) -> bytes:
        """Only the header row — no example row, which re-uploaded unedited
        would create a real record."""
        return build_xlsx(self.sheet_title, self.columns)


TABLES: list[XlsxTable] = [
    XlsxTable("sizes", SIZE_COLUMNS, _import_sizes, _export_sizes, "Maten"),
    XlsxTable("articles", ARTICLE_COLUMNS, _import_articles, _export_articles, "Artikelen"),
    XlsxTable("article-sizes", ARTICLE_SIZE_COLUMNS, _import_article_sizes, _export_article_sizes, "Artikelmaten"),
    XlsxTable("reservations", RESERVATION_COLUMNS, _import_reservations, _export_reservations, "Reservaties"),
    XlsxTable("package-lines", PACKAGE_LINE_COLUMNS, _import_package_lines, _export_package_lines, "Pakketlijnen"),
]
