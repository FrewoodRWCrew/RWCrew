# This is StockMaster's (module-4) own router file. It used to call the
# shared, generic create_module_router() factory (see app/modules/common.py)
# for the "coming soon" placeholder; it now has its own custom-roles-with-
# per-screen-permissions system — the same one Altsien Select (module-8)
# and the other modules have (see docs/module-custom-roles-pattern.md) — so
# every endpoint below is gated per-screen, per-action.
#
# StockMaster keeps the warehouse stock of MasterData products, as free
# stock (on the product's fixed bin) and loaded in KarTracker's kars. All
# stock changes go through stock_service.py; the read-only views come from
# stock_queries.py; the kar needs from requirement_service.py; the PDFs from
# stock_pdfs.py. See docs/stockmaster-design.md for the full design.

from datetime import date
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.db.models.kartracker_kar import KarTrackerKar
from app.db.models.module import Module
from app.db.models.product import Product
from app.db.models.product_category import ProductCategory
from app.db.models.season import Season
from app.db.models.stockmaster_document import StockMasterDocument
from app.db.models.stockmaster_reason import StockMasterReason
from app.db.models.stockmaster_role import StockMasterRole
from app.db.models.stockmaster_role_permission import StockMasterRolePermission
from app.db.models.stockmaster_screen import StockMasterScreen
from app.db.models.stockmaster_user_role import StockMasterUserRole
from app.db.models.team import Team
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.db.models.warehouse import Warehouse
from app.help.routes import register_help_route
from app.modules.module_4 import requirement_service, stock_service
from app.modules.module_4.deps import (
    MODULE_KEY,
    ensure_season_editable,
    get_season_or_404,
    get_user_role,
    require_any_screen_permission,
    require_module_access,
    require_screen_permission,
    screen_keys_allowed,
    user_can,
)
from app.modules.module_4.stock_pdfs import (
    build_booking_pdf,
    build_count_sheet_pdf,
    build_dispatch_pdf,
    build_load_list_pdf,
    build_order_list_pdf,
)
from app.modules.module_4.stock_queries import (
    DocumentFilters,
    build_count_sheet,
    build_dashboard,
    build_document_responses,
    build_kar_detail,
    build_kar_summaries,
    build_order_needs,
    build_product_stock,
    count_below_minimum,
    list_documents,
)
from app.modules.module_4.stock_service import BookingLine, CountLine, StockError
from app.schemas.masterdata import SeasonResponse
from app.schemas.stockmaster import (
    AlertsResponse,
    BookingRequest,
    CountSheetLine,
    CreateOrGrantUserRequest,
    DashboardResponse,
    DocumentPageResponse,
    DocumentResponse,
    KarDetailResponse,
    KarSummaryResponse,
    LookupsResponse,
    MyPermissionsResponse,
    NamedItem,
    OrderNeedResponse,
    PreviousRequirementLine,
    PreviousRequirementsResponse,
    ProductStockResponse,
    ReasonResponse,
    ReasonWriteRequest,
    RequirementResponse,
    RequirementsSaveRequest,
    ReverseRequest,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
    ScreenPermissionResponse,
    ScreenResponse,
    SetRolePermissionsRequest,
    SetUserRoleRequest,
    UserSummaryResponse,
)

router = APIRouter(prefix="/api/modules/module-4", tags=["StockMaster"])

# GET /help/pdf: the module's manual, with only the screens the user can view.
register_help_route(
    router,
    module_key=MODULE_KEY,
    require_access=require_module_access,
    viewable_screen_keys=lambda db, user: screen_keys_allowed(db, user, "view"),
)

STOCK_SCREEN = "stockmaster.stock"
KARS_SCREEN = "stockmaster.kars"
COUNT_SCREEN = "stockmaster.count"
REQUIREMENTS_SCREEN = "stockmaster.requirements"
ORDER_NEEDS_SCREEN = "stockmaster.orderneeds"
BOOKINGS_SCREEN = "stockmaster.bookings"
REASONS_SCREEN = "stockmaster.reasons"
KPI_SCREEN = "stockmaster.kpi"

# Which screen's "create" right allows which booking.
ACTION_SCREENS: dict[str, str] = {
    "book_in": STOCK_SCREEN,
    "book_out": STOCK_SCREEN,
    "kar_load": KARS_SCREEN,
    "kar_unload": KARS_SCREEN,
    "kar_dispatch": KARS_SCREEN,
    "kar_return": KARS_SCREEN,
    "count": COUNT_SCREEN,
}

Locale = Literal["nl", "en"]


def _stock_error(db: Session, error: StockError) -> HTTPException:
    """Undo everything the failed booking already wrote, and answer with
    the rule that was broken ("code|param|..." — translated by the frontend).
    """
    db.rollback()
    return HTTPException(status_code=error.status_code, detail=error.detail)


def _pdf_response(content: bytes, filename: str) -> Response:
    """A PDF opened inline in a new browser tab (print or save from there)."""
    ascii_fallback = filename.encode("ascii", "replace").decode("ascii").replace("\\", "_").replace('"', "_")
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"},
    )


def _get_kar_or_404(db: Session, kar_id: int) -> KarTrackerKar:
    """Load a kar, or answer 404."""
    kar = db.get(KarTrackerKar, kar_id)
    if kar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="kar_not_found")
    return kar


def _get_document_or_404(db: Session, document_id: int) -> StockMasterDocument:
    """Load a booking, or answer 404."""
    document = db.get(StockMasterDocument, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="booking_not_found")
    return document


def _document_detail(db: Session, document: StockMasterDocument) -> DocumentResponse:
    """One booking with all its lines."""
    return build_document_responses(db, [document], with_lines=True)[0]


# --- Screens, Roles, Users (access-rights screens) ------------------------
# The same endpoints as every other custom-roles module (copied from
# module_8/router.py), on StockMaster's own tables.


def _build_role_response(db: Session, role: StockMasterRole) -> RoleResponse:
    """Turn one role into its full permission-matrix response: every
    registered screen, paired with that role's permissions on it (all
    False if the role has never been given any permissions there yet).
    """
    screens = db.scalars(select(StockMasterScreen).order_by(StockMasterScreen.sort_order)).all()
    permissions_by_screen_id = {
        permission.screen_id: permission
        for permission in db.scalars(
            select(StockMasterRolePermission).where(StockMasterRolePermission.role_id == role.id)
        )
    }

    permission_rows = []
    for screen in screens:
        permission = permissions_by_screen_id.get(screen.id)
        permission_rows.append(
            ScreenPermissionResponse(
                screen_id=screen.id,
                screen_key=screen.key,
                screen_label=screen.label,
                can_view=permission.can_view if permission else False,
                can_create=permission.can_create if permission else False,
                can_edit=permission.can_edit if permission else False,
                can_delete=permission.can_delete if permission else False,
            )
        )

    return RoleResponse(id=role.id, name=role.name, permissions=permission_rows)


@router.get("/screens", response_model=list[ScreenResponse])
def list_screens(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("stockmaster.roles", "view")),
) -> list[StockMasterScreen]:
    """List every registered StockMaster screen — the rows of the
    permission matrix on the Roles screen.
    """
    return list(db.scalars(select(StockMasterScreen).order_by(StockMasterScreen.sort_order)).all())


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("stockmaster.roles", "view")),
) -> list[RoleResponse]:
    """List every StockMaster role, each with its full permission matrix."""
    roles = db.scalars(select(StockMasterRole).order_by(StockMasterRole.name)).all()
    return [_build_role_response(db, role) for role in roles]


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("stockmaster.roles", "create")),
) -> RoleResponse:
    """Create a brand-new role, with no permissions granted yet."""
    new_role = StockMasterRole(name=payload.name)
    db.add(new_role)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A role with this name already exists") from error

    db.refresh(new_role)
    return _build_role_response(db, new_role)


@router.put("/roles/{role_id}", response_model=RoleResponse)
def rename_role(
    role_id: int,
    payload: RoleUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("stockmaster.roles", "edit")),
) -> RoleResponse:
    """Rename an existing role."""
    role = db.get(StockMasterRole, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    role.name = payload.name
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A role with this name already exists") from error

    db.refresh(role)
    return _build_role_response(db, role)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("stockmaster.roles", "delete")),
) -> None:
    """Delete a role, as long as nobody currently holds it."""
    role = db.get(StockMasterRole, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    still_assigned = db.scalar(select(StockMasterUserRole).where(StockMasterUserRole.role_id == role_id))
    if still_assigned is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This role is still assigned to at least one user"
        )

    db.delete(role)
    db.commit()


@router.put("/roles/{role_id}/permissions", response_model=RoleResponse)
def set_role_permissions(
    role_id: int,
    payload: SetRolePermissionsRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("stockmaster.roles", "edit")),
) -> RoleResponse:
    """Replace a role's entire permission matrix with exactly what was sent."""
    role = db.get(StockMasterRole, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    existing_permissions = {
        permission.screen_id: permission
        for permission in db.scalars(
            select(StockMasterRolePermission).where(StockMasterRolePermission.role_id == role_id)
        )
    }

    for item in payload.permissions:
        existing = existing_permissions.get(item.screen_id)
        if existing is not None:
            existing.can_view = item.can_view
            existing.can_create = item.can_create
            existing.can_edit = item.can_edit
            existing.can_delete = item.can_delete
        else:
            db.add(
                StockMasterRolePermission(
                    role_id=role_id,
                    screen_id=item.screen_id,
                    can_view=item.can_view,
                    can_create=item.can_create,
                    can_edit=item.can_edit,
                    can_delete=item.can_delete,
                )
            )

    db.commit()
    return _build_role_response(db, role)


def _build_user_summary(db: Session, user: User) -> UserSummaryResponse:
    """One user with their current StockMaster role (if any)."""
    user_role = get_user_role(db, user.id)
    role = db.get(StockMasterRole, user_role.role_id) if user_role else None
    return UserSummaryResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role_id=role.id if role else None,
        role_name=role.name if role else None,
    )


@router.get("/users", response_model=list[UserSummaryResponse])
def list_users(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("stockmaster.users", "view")),
) -> list[UserSummaryResponse]:
    """List every user with access to StockMaster, and their current role."""
    module = db.scalar(select(Module).where(Module.key == MODULE_KEY))
    users_with_access = db.scalars(
        select(User)
        .join(UserModuleAccess, UserModuleAccess.user_id == User.id)
        .where(UserModuleAccess.module_id == module.id)
        .order_by(User.display_name)
    ).all()
    return [_build_user_summary(db, user) for user in users_with_access]


@router.put("/users/{user_id}/role", response_model=UserSummaryResponse)
def set_user_role(
    user_id: int,
    payload: SetUserRoleRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("stockmaster.users", "edit")),
) -> UserSummaryResponse:
    """Assign (or, if role_id is null, remove) a StockMaster role for a user
    who already has access to StockMaster.
    """
    target_user = db.get(User, user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    module = db.scalar(select(Module).where(Module.key == MODULE_KEY))
    has_access = db.scalar(
        select(UserModuleAccess).where(UserModuleAccess.user_id == user_id, UserModuleAccess.module_id == module.id)
    )
    if has_access is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This user does not have access to StockMaster"
        )

    existing_role_row = get_user_role(db, user_id)

    if payload.role_id is None:
        if existing_role_row is not None:
            db.delete(existing_role_row)
    else:
        role = db.get(StockMasterRole, payload.role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        if existing_role_row is not None:
            existing_role_row.role_id = payload.role_id
        else:
            db.add(StockMasterUserRole(user_id=user_id, role_id=payload.role_id))

    db.commit()
    return _build_user_summary(db, target_user)


@router.post("/users", response_model=UserSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_or_grant_user(
    payload: CreateOrGrantUserRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("stockmaster.users", "create")),
) -> UserSummaryResponse:
    """Give someone access to StockMaster, creating their account first if
    they don't already have one anywhere in RW Crew. This ALWAYS grants
    access to StockMaster only — never any other module.
    """
    target_user = db.scalar(select(User).where(User.email == payload.email))

    if target_user is None:
        if not payload.display_name or not payload.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A name and password are required to create a new user",
            )
        target_user = User(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            display_name=payload.display_name,
        )
        db.add(target_user)
        try:
            db.flush()
        except IntegrityError as error:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists"
            ) from error

    module = db.scalar(select(Module).where(Module.key == MODULE_KEY))
    has_access = db.scalar(
        select(UserModuleAccess).where(
            UserModuleAccess.user_id == target_user.id, UserModuleAccess.module_id == module.id
        )
    )
    if has_access is None:
        db.add(UserModuleAccess(user_id=target_user.id, module_id=module.id))

    if payload.role_id is not None:
        role = db.get(StockMasterRole, payload.role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        existing_role_row = get_user_role(db, target_user.id)
        if existing_role_row is not None:
            existing_role_row.role_id = payload.role_id
        else:
            db.add(StockMasterUserRole(user_id=target_user.id, role_id=payload.role_id))

    db.commit()
    return _build_user_summary(db, target_user)


@router.get("/me/permissions", response_model=MyPermissionsResponse)
def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access),
) -> MyPermissionsResponse:
    """Tell the frontend which StockMaster screens the current user can
    view / create on / edit / delete on, so it knows which menu items and
    buttons to show.
    """
    return MyPermissionsResponse(
        viewable_screen_keys=screen_keys_allowed(db, current_user, "view"),
        creatable_screen_keys=screen_keys_allowed(db, current_user, "create"),
        editable_screen_keys=screen_keys_allowed(db, current_user, "edit"),
        deletable_screen_keys=screen_keys_allowed(db, current_user, "delete"),
    )


# --- Lookups (every StockMaster user) ---------------------------------------


@router.get("/seasons", response_model=list[SeasonResponse])
def list_seasons(
    db: Session = Depends(get_db),
    _user: User = Depends(require_module_access),
) -> list[Season]:
    """Every season (open and closed) for the module's own season dropdown."""
    return list(db.scalars(select(Season).order_by(Season.name)).all())


@router.get("/lookups", response_model=LookupsResponse)
def get_lookups(
    db: Session = Depends(get_db),
    _user: User = Depends(require_module_access),
) -> LookupsResponse:
    """Warehouses, categories, teams, reasons and booking users for the
    screens' dropdowns and filters.
    """
    booking_users = db.execute(
        select(StockMasterDocument.created_by, StockMasterDocument.created_by_name)
        .where(StockMasterDocument.created_by.is_not(None))
        .distinct()
    ).all()
    return LookupsResponse(
        warehouses=[NamedItem(id=row.id, name=row.name) for row in db.scalars(select(Warehouse).order_by(Warehouse.name))],
        categories=[
            NamedItem(id=row.id, name=row.name)
            for row in db.scalars(select(ProductCategory).order_by(ProductCategory.name))
        ],
        teams=[
            NamedItem(id=row.id, name=row.name)
            for row in db.scalars(select(Team).where(Team.active.is_(True)).order_by(Team.name))
        ],
        reasons=[
            ReasonResponse.model_validate(reason)
            for reason in db.scalars(
                select(StockMasterReason)
                .where(StockMasterReason.active.is_(True))
                .order_by(StockMasterReason.sort_order, StockMasterReason.name)
            )
        ],
        booking_users=sorted(
            (NamedItem(id=user_id, name=name or str(user_id)) for user_id, name in booking_users),
            key=lambda item: item.name.lower(),
        ),
    )


@router.get("/stock", response_model=list[ProductStockResponse])
def get_stock(
    db: Session = Depends(get_db),
    _user: User = Depends(require_module_access),
) -> list[ProductStockResponse]:
    """Every product with its free stock, stock per kar and total — the
    stock overview, and the product search of every booking panel.
    """
    return build_product_stock(db)


@router.get("/alerts", response_model=AlertsResponse)
def get_alerts(
    db: Session = Depends(get_db),
    _user: User = Depends(require_module_access),
) -> AlertsResponse:
    """How many consumables are below their minimum (the orange banner)."""
    return AlertsResponse(below_minimum_count=count_below_minimum(db))


@router.get("/kars", response_model=list[KarSummaryResponse])
def list_kars(
    season_id: int | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_module_access),
) -> list[KarSummaryResponse]:
    """Every kar as a card: in the warehouse or out, its contents, and its
    loading progress against the season's needs.
    """
    return build_kar_summaries(db, season_id)


@router.get("/kars/{kar_id}", response_model=KarDetailResponse)
def get_kar_detail(
    kar_id: int,
    season_id: int | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_module_access),
) -> KarDetailResponse:
    """A kar's contents versus its needs, what left with it, and its team's
    festivals — for the kar detail and the kar booking panels.
    """
    return build_kar_detail(db, _get_kar_or_404(db, kar_id), season_id)


# --- KPI ---------------------------------------------------------------------


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    season_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(KPI_SCREEN, "view")),
) -> DashboardResponse:
    """Tiles and charts of the KPI main page for one season."""
    get_season_or_404(db, season_id)
    return build_dashboard(db, season_id)


# --- Bookings ------------------------------------------------------------------


@router.post("/bookings", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access),
) -> DocumentResponse:
    """Make one booking (Inboeken, Kar laden, Uitboeken, Kar vertrekt, Kar
    terug, Kar uitladen or Telling). It's always stored under the logged-in
    user — taken from the session here, never from the request.
    """
    screen = ACTION_SCREENS[payload.action]
    allowed = user_can(db, current_user, screen, "create")
    # "Te bestellen" can book in the delivered goods too.
    if payload.action == "book_in" and not allowed:
        allowed = user_can(db, current_user, ORDER_NEEDS_SCREEN, "create")
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not_allowed")

    season = get_season_or_404(db, payload.season_id)
    ensure_season_editable(db, current_user, season)

    lines = [BookingLine(line.product_id, line.quantity, line.destination) for line in payload.lines]
    try:
        if payload.action == "book_in":
            document = stock_service.book_in(
                db, current_user, season, lines,
                reference=payload.reference, reason_id=payload.reason_id, comment=payload.comment,
            )
        elif payload.action == "book_out":
            document = stock_service.book_out(
                db, current_user, season, lines,
                reason_id=payload.reason_id, from_kar_id=payload.kar_id,
                reference=payload.reference, comment=payload.comment,
            )
        elif payload.action == "kar_load":
            document = stock_service.load_kar(
                db, current_user, season, _required_kar(payload.kar_id), lines,
                from_kar_id=payload.from_kar_id, reference=payload.reference, comment=payload.comment,
            )
        elif payload.action == "kar_unload":
            document = stock_service.unload_kar(
                db, current_user, season, _required_kar(payload.kar_id), lines, comment=payload.comment
            )
        elif payload.action == "kar_dispatch":
            document = stock_service.dispatch_kar(
                db, current_user, season, _required_kar(payload.kar_id),
                team_id=payload.team_id, festival_id=payload.festival_id,
                reference=payload.reference, comment=payload.comment,
            )
        elif payload.action == "kar_return":
            document = stock_service.return_kar(
                db, current_user, season, _required_kar(payload.kar_id), lines, comment=payload.comment
            )
        else:
            document = stock_service.count_stock(
                db, current_user, season,
                [CountLine(line.product_id, line.quantity) for line in payload.lines],
                kar_id=payload.kar_id, reason_id=payload.reason_id, comment=payload.comment,
            )
        db.commit()
    except StockError as error:
        raise _stock_error(db, error) from error
    except IntegrityError as error:
        # Two people booked the very first piece of a product at the same
        # moment: the database refused the second one — just try again.
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="concurrent_booking") from error

    return _document_detail(db, document)


def _required_kar(kar_id: int | None) -> int:
    """Kar bookings need a kar."""
    if kar_id is None:
        raise StockError("kar_required")
    return kar_id


@router.get("/bookings", response_model=DocumentPageResponse)
def get_bookings(
    season_id: int | None = None,
    doc_type: str | None = None,
    product_id: int | None = None,
    kar_id: int | None = None,
    user_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(BOOKINGS_SCREEN, "view")),
) -> DocumentPageResponse:
    """The booking history, newest first, with filters and paging."""
    items, total = list_documents(
        db,
        DocumentFilters(season_id, doc_type, product_id, kar_id, user_id, date_from, date_to),
        offset,
        limit,
    )
    return DocumentPageResponse(items=items, total=total)


@router.get("/bookings/{document_id}", response_model=DocumentResponse)
def get_booking(
    document_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(BOOKINGS_SCREEN, "view")),
) -> DocumentResponse:
    """One booking with all its lines."""
    return _document_detail(db, _get_document_or_404(db, document_id))


@router.post("/bookings/{document_id}/reverse", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def reverse_booking(
    document_id: int,
    payload: ReverseRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(BOOKINGS_SCREEN, "delete")),
) -> DocumentResponse:
    """Ongedaan maken: book the exact opposite of a booking (stored under
    the logged-in user). Nothing is ever deleted.
    """
    document = _get_document_or_404(db, document_id)
    ensure_season_editable(db, current_user, get_season_or_404(db, document.season_id))
    try:
        reversal = stock_service.reverse_document(
            db, current_user, document, comment=payload.comment if payload else None
        )
        db.commit()
    except StockError as error:
        raise _stock_error(db, error) from error
    return _document_detail(db, reversal)


@router.get("/bookings/{document_id}/pdf")
def get_booking_pdf(
    document_id: int,
    locale: Locale = "nl",
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_any_screen_permission((BOOKINGS_SCREEN, "view"), (KARS_SCREEN, "view"))
    ),
) -> Response:
    """The Boekingsbon of a booking — or, for "Kar vertrekt", its Vertrekbon."""
    document = _document_detail(db, _get_document_or_404(db, document_id))
    if document.doc_type == stock_service.KAR_DISPATCH:
        content = build_dispatch_pdf(document, locale, current_user.display_name)
        return _pdf_response(content, f"Vertrekbon {document.kar_nummer or ''} {document.doc_number}.pdf")
    # A plain booking note needs the history right.
    if not user_can(db, current_user, BOOKINGS_SCREEN, "view"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not_allowed")
    content = build_booking_pdf(document, locale, current_user.display_name)
    return _pdf_response(content, f"Boekingsbon {document.doc_number}.pdf")


@router.get("/kars/{kar_id}/load-list/pdf")
def get_load_list_pdf(
    kar_id: int,
    season_id: int,
    locale: Locale = "nl",
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_any_screen_permission((KARS_SCREEN, "view"), (REQUIREMENTS_SCREEN, "view"))
    ),
) -> Response:
    """The Laadlijst of one kar for one season."""
    season = get_season_or_404(db, season_id)
    kar = _get_kar_or_404(db, kar_id)
    content = build_load_list_pdf(build_kar_detail(db, kar, season.id), season.name, locale, current_user.display_name)
    return _pdf_response(content, f"Laadlijst {kar.kar_nummer} {season.name}.pdf")


# --- Kar needs (Benodigdheden) -------------------------------------------------


def _requirement_responses(db: Session, season_id: int, kar_id: int) -> list[RequirementResponse]:
    """A kar's needs with product names, bins and what's in the kar now."""
    detail_lines = {line.product_id: line for line in build_kar_detail(db, _get_kar_or_404(db, kar_id), season_id).lines}
    result = []
    for row in requirement_service.list_requirements(db, season_id, kar_id):
        line = detail_lines.get(row.product_id)
        product = db.get(Product, row.product_id)
        result.append(
            RequirementResponse(
                product_id=row.product_id,
                product_name=product.name if product else str(row.product_id),
                bin_label=line.bin_label if line else None,
                quantity=row.quantity,
                comment=row.comment,
                in_kar=line.in_kar if line else 0,
                updated_by_name=row.updated_by_name,
                updated_at=row.updated_at,
            )
        )
    result.sort(key=lambda item: item.product_name.lower())
    return result


@router.get("/requirements", response_model=list[RequirementResponse])
def get_requirements(
    season_id: int,
    kar_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(REQUIREMENTS_SCREEN, "view")),
) -> list[RequirementResponse]:
    """What one kar needs this season."""
    get_season_or_404(db, season_id)
    return _requirement_responses(db, season_id, kar_id)


@router.put("/requirements", response_model=list[RequirementResponse])
def save_requirements(
    payload: RequirementsSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(REQUIREMENTS_SCREEN, "view")),
) -> list[RequirementResponse]:
    """Save a kar's complete list of needs for the season. Adding lines
    needs "create", changing them "edit", removing them "delete".
    """
    season = get_season_or_404(db, payload.season_id)
    ensure_season_editable(db, current_user, season)
    _get_kar_or_404(db, payload.kar_id)
    lines = [
        requirement_service.RequirementLine(line.product_id, line.quantity, line.comment) for line in payload.lines
    ]
    try:
        changes = requirement_service.plan_changes(db, season.id, payload.kar_id, lines)
        for needed, action in ((changes.added, "create"), (changes.changed, "edit"), (changes.removed, "delete")):
            if needed and not user_can(db, current_user, REQUIREMENTS_SCREEN, action):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not_allowed")
        requirement_service.apply_changes(db, current_user, season, payload.kar_id, changes)
        db.commit()
    except StockError as error:
        raise _stock_error(db, error) from error
    return _requirement_responses(db, season.id, payload.kar_id)


@router.get("/requirements/previous", response_model=PreviousRequirementsResponse)
def get_previous_requirements(
    season_id: int,
    kar_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(REQUIREMENTS_SCREEN, "view")),
) -> PreviousRequirementsResponse:
    """Last season's needs of the same kar ("Kopieer van vorig seizoen"),
    with what's already listed this season.
    """
    season = get_season_or_404(db, season_id)
    previous, rows = requirement_service.previous_season_requirements(db, season, kar_id)
    current = {row.product_id: row.quantity for row in requirement_service.list_requirements(db, season.id, kar_id)}
    lines = []
    for row in rows:
        product = db.get(Product, row.product_id)
        lines.append(
            PreviousRequirementLine(
                product_id=row.product_id,
                product_name=product.name if product else str(row.product_id),
                quantity=row.quantity,
                current_quantity=current.get(row.product_id),
            )
        )
    lines.sort(key=lambda item: item.product_name.lower())
    return PreviousRequirementsResponse(season_name=previous.name if previous else None, lines=lines)


# --- Te bestellen ------------------------------------------------------------------


@router.get("/order-needs", response_model=list[OrderNeedResponse])
def get_order_needs(
    season_id: int,
    warehouse_id: int | None = None,
    category_id: int | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(ORDER_NEEDS_SCREEN, "view")),
) -> list[OrderNeedResponse]:
    """Per product with needs this season: needed, in stock, to order."""
    get_season_or_404(db, season_id)
    return build_order_needs(db, season_id, warehouse_id, category_id)


@router.get("/order-needs/pdf")
def get_order_needs_pdf(
    season_id: int,
    warehouse_id: int | None = None,
    category_id: int | None = None,
    locale: Locale = "nl",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(ORDER_NEEDS_SCREEN, "view")),
) -> Response:
    """The Bestellijst of a season (with the same filters as the screen)."""
    season = get_season_or_404(db, season_id)
    filters = [
        name
        for name in (
            db.get(Warehouse, warehouse_id).name if warehouse_id and db.get(Warehouse, warehouse_id) else None,
            db.get(ProductCategory, category_id).name if category_id and db.get(ProductCategory, category_id) else None,
        )
        if name
    ]
    content = build_order_list_pdf(
        build_order_needs(db, season.id, warehouse_id, category_id),
        season.name,
        ", ".join(filters) or None,
        locale,
        current_user.display_name,
    )
    return _pdf_response(content, f"Bestellijst {season.name}.pdf")


# --- Telling -----------------------------------------------------------------------


@router.get("/count-sheet", response_model=list[CountSheetLine])
def get_count_sheet(
    kar_id: int | None = None,
    warehouse_id: int | None = None,
    bin_from: str | None = None,
    bin_to: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(COUNT_SCREEN, "view")),
) -> list[CountSheetLine]:
    """What to count, with the expected quantities (one kar, or the free
    stock of a warehouse / bin range).
    """
    if kar_id is not None:
        _get_kar_or_404(db, kar_id)
    return build_count_sheet(db, kar_id=kar_id, warehouse_id=warehouse_id, bin_from=bin_from, bin_to=bin_to)


@router.get("/count-sheet/pdf")
def get_count_sheet_pdf(
    kar_id: int | None = None,
    warehouse_id: int | None = None,
    bin_from: str | None = None,
    bin_to: str | None = None,
    season_id: int | None = None,
    locale: Locale = "nl",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(COUNT_SCREEN, "view")),
) -> Response:
    """The Telblad (with an empty "geteld" column)."""
    kar = _get_kar_or_404(db, kar_id) if kar_id is not None else None
    warehouse = db.get(Warehouse, warehouse_id) if warehouse_id is not None else None
    season = db.get(Season, season_id) if season_id is not None else None
    bin_range = " - ".join(part for part in (bin_from, bin_to) if part) or None
    content = build_count_sheet_pdf(
        build_count_sheet(db, kar_id=kar_id, warehouse_id=warehouse_id, bin_from=bin_from, bin_to=bin_to),
        kar_nummer=kar.kar_nummer if kar else None,
        warehouse_name=warehouse.name if warehouse else None,
        bin_range=None if kar else bin_range,
        season_name=season.name if season else None,
        locale=locale,
        printed_by=current_user.display_name,
    )
    name = kar.kar_nummer if kar else (warehouse.name if warehouse else "vrije voorraad")
    return _pdf_response(content, f"Telblad {name}.pdf")


# --- Reasons (Instellingen > Redenen) ----------------------------------------------


@router.get("/reasons", response_model=list[ReasonResponse])
def list_reasons(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(REASONS_SCREEN, "view")),
) -> list[StockMasterReason]:
    """Every reason, active and inactive."""
    return list(db.scalars(select(StockMasterReason).order_by(StockMasterReason.sort_order, StockMasterReason.name)))


@router.post("/reasons", response_model=ReasonResponse, status_code=status.HTTP_201_CREATED)
def create_reason(
    payload: ReasonWriteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_screen_permission(REASONS_SCREEN, "create")),
) -> StockMasterReason:
    """Add a reason (stored with the logged-in user who added it)."""
    reason = StockMasterReason(
        **payload.model_dump(), created_by=current_user.id, created_by_name=current_user.display_name
    )
    db.add(reason)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="reason_exists") from error
    db.refresh(reason)
    return reason


@router.put("/reasons/{reason_id}", response_model=ReasonResponse)
def update_reason(
    reason_id: int,
    payload: ReasonWriteRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(REASONS_SCREEN, "edit")),
) -> StockMasterReason:
    """Change a reason."""
    reason = db.get(StockMasterReason, reason_id)
    if reason is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="reason_not_found")
    for field_name, value in payload.model_dump().items():
        setattr(reason, field_name, value)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="reason_exists") from error
    db.refresh(reason)
    return reason


@router.delete("/reasons/{reason_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reason(
    reason_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission(REASONS_SCREEN, "delete")),
) -> None:
    """Remove a reason that was never used (a used one can be made inactive)."""
    reason = db.get(StockMasterReason, reason_id)
    if reason is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="reason_not_found")
    if db.scalar(select(StockMasterDocument.id).where(StockMasterDocument.reason_id == reason_id).limit(1)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="reason_in_use")
    db.delete(reason)
    db.commit()
