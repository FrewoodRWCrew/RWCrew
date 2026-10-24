# Aggregate KPI stats for MasterData's landing dashboard ("Masterdata
# Overview"). Kept free of FastAPI/routing concerns, mirroring
# app/modules/module_1/tag_dashboard.py, so it's easy to unit test on its
# own. The product tiles and charts moved to StockMaster's KPI page together
# with the product screens (see app/modules/module_4/product_stats.py).

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.season import Season
from app.schemas.masterdata import MasterDataDashboardResponse


def build_dashboard_stats(db: Session) -> MasterDataDashboardResponse:
    total_seasons = db.scalar(select(func.count()).select_from(Season))
    return MasterDataDashboardResponse(total_seasons=total_seasons)
