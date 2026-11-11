# StockMaster's staff screen "Kar inventarissen": the counts teams made of
# their own kar on the public kar page (see public_kar_inventory_router.py).
# Its own APIRouter on the /api/modules/module-4 prefix (included in
# app/main.py), like voice_count_router.py. Read-only: gated by the
# "stockmaster.karinventories" screen's "view"; nothing here changes stock.

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.timezone import to_belgian
from app.db.models.user import User
from app.modules.module_4.deps import get_season_or_404, require_screen_permission
from app.modules.module_4.kar_inventory_service import get_inventory, list_inventories, to_responses
from app.modules.module_4.stock_service import StockError
from app.modules.module_9.xlsx_common import build_xlsx
from app.schemas.stockmaster import KarInventoryExportRequest, KarInventoryResponse

router = APIRouter(prefix="/api/modules/module-4", tags=["StockMaster"])

KAR_INVENTORIES_SCREEN = "stockmaster.karinventories"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

_HEADERS = {
    "nl": ["Datum", "Kar", "Ploeg", "Seizoen", "Geteld door", "Product", "Vertrokken", "Geteld", "Verschil",
           "Extra", "Opmerking"],
    "en": ["Date", "Kar", "Team", "Season", "Counted by", "Product", "Left with kar", "Counted", "Difference",
           "Extra", "Remark"],
}


@router.get("/kar-inventories", response_model=list[KarInventoryResponse])
def list_kar_inventories(
    season_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(KAR_INVENTORIES_SCREEN, "view")),
) -> list[KarInventoryResponse]:
    """Every inventory of a season, newest first, with its lines."""
    get_season_or_404(db, season_id)
    return to_responses(db, list_inventories(db, season_id=season_id))


@router.get("/kar-inventories/{inventory_id}", response_model=KarInventoryResponse)
def get_kar_inventory(
    inventory_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(KAR_INVENTORIES_SCREEN, "view")),
) -> KarInventoryResponse:
    """One inventory with its lines."""
    try:
        inventory = get_inventory(db, inventory_id)
    except StockError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error
    return to_responses(db, [inventory])[0]


def _text(value: str | None) -> str | None:
    """Text as Excel must show it: names and remarks are typed on a public page,
    so a value starting like a formula must not be run as one."""
    if value and value[0] in "=+-@":
        return f"'{value}"
    return value


def _moment(value: datetime) -> str:
    """A moment in Belgian time, as the screen shows it."""
    return to_belgian(value).strftime("%d-%m-%Y %H:%M")


@router.post("/kar-inventories/export")
def export_kar_inventories(
    payload: KarInventoryExportRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(KAR_INVENTORIES_SCREEN, "view")),
) -> Response:
    """Excel of the inventories the screen shows: one row per counted product."""
    language = "en" if payload.locale == "en" else "nl"
    inventories = list_inventories(db, ids=set(payload.ids)) if payload.ids else []
    yes = "ja" if language == "nl" else "yes"
    rows = [
        [
            _moment(inventory.created_at),
            _text(inventory.kar_nummer),
            _text(inventory.team_name),
            _text(inventory.season_name),
            _text(inventory.counted_by_name),
            _text(line.product_name),
            line.expected,
            line.counted,
            line.counted - line.expected,
            yes if line.is_extra else "",
            _text(inventory.remark),
        ]
        for inventory in to_responses(db, inventories)
        for line in inventory.lines
    ]
    content = build_xlsx("Kar inventarissen" if language == "nl" else "Kar inventories", _HEADERS[language], rows)
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="stockmaster-kar-inventarissen.xlsx"'},
    )
