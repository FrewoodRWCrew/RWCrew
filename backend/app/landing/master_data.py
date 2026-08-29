# This file defines the super-admin-only endpoints behind the landing
# page's "Master Data" admin screen. "Season" is the first master-data
# entity; if more are added later, they'd get their own similar section
# in this same file (or their own file, if it grows large).
#
# Every endpoint here requires the super-admin flag (see
# require_super_admin in deps.py) — a normal user gets a 403 Forbidden
# error if they try to call any of these.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.season import Season
from app.db.models.user import User
from app.landing.deps import require_super_admin
from app.schemas.season import SeasonCreateRequest, SeasonResponse, SeasonUpdateRequest

router = APIRouter(prefix="/api/admin/master-data", tags=["master-data"])


@router.get("/seasons", response_model=list[SeasonResponse])
def list_seasons(
    db: Session = Depends(get_db),
    _super_admin: User = Depends(require_super_admin),
) -> list[Season]:
    """List every season, for the Master Data table."""
    return list(db.scalars(select(Season).order_by(Season.name)).all())


@router.post("/seasons", response_model=SeasonResponse, status_code=status.HTTP_201_CREATED)
def create_season(
    payload: SeasonCreateRequest,
    db: Session = Depends(get_db),
    _super_admin: User = Depends(require_super_admin),
) -> Season:
    """Create a brand-new season."""
    new_season = Season(name=payload.name)
    db.add(new_season)
    try:
        db.commit()
    except IntegrityError as error:
        # This happens if a season with this name already exists.
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A season with this name already exists") from error

    db.refresh(new_season)
    return new_season


@router.put("/seasons/{season_id}", response_model=SeasonResponse)
def update_season(
    season_id: int,
    payload: SeasonUpdateRequest,
    db: Session = Depends(get_db),
    _super_admin: User = Depends(require_super_admin),
) -> Season:
    """Rename an existing season."""
    season = db.get(Season, season_id)
    if season is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season not found")

    season.name = payload.name
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A season with this name already exists") from error

    db.refresh(season)
    return season


@router.delete("/seasons/{season_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_season(
    season_id: int,
    db: Session = Depends(get_db),
    _super_admin: User = Depends(require_super_admin),
) -> None:
    """Permanently delete a season."""
    season = db.get(Season, season_id)
    if season is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season not found")

    db.delete(season)
    db.commit()
