# This is Tagscan's own router file. Unlike modules 2-9 (which just call
# the shared create_module_router() factory), Tagscan needs its own
# custom-roles-with-per-screen-permissions system, so its endpoints are
# written out in full here.

import secrets
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password
from app.db.models.module import Module
from app.db.models.product import Product
from app.db.models.product_type import ProductType
from app.db.models.rfid_tag import RfidTag
from app.db.models.scanner import Scanner
from app.db.models.tag_header_data import TagHeaderData
from app.db.models.tag_line_data import TagLineData
from app.db.models.tagscan_role import TagscanRole
from app.db.models.tagscan_role_permission import TagscanRolePermission
from app.db.models.tagscan_screen import TagscanScreen
from app.db.models.tagscan_settings import TagscanSettings
from app.db.models.tagscan_user_role import TagscanUserRole
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.modules.module_1.deps import (
    MODULE_KEY,
    get_user_role,
    require_module_access,
    require_screen_permission,
    user_can,
)
from app.modules.module_1.file_browser import (
    SETTINGS_ROW_ID,
    build_folder_tree,
    get_source_root,
    list_files,
    read_file_preview,
    resolve_safe_path,
)
from app.modules.module_1.tag_dashboard import build_dashboard_stats
from app.modules.module_1.tag_header_data import delete_header_data, list_header_data, scan_unreaded_tags
from app.modules.module_1.tag_header_pdf import build_header_summary_pdf
from app.modules.module_1.tag_import import build_template_xlsx, import_tags_from_xlsx
from app.modules.module_1.tag_line_data import list_line_data, sync_line_data
from app.schemas.tagscan import (
    CreateOrGrantUserRequest,
    FileContentResponse,
    FileEntryResponse,
    FolderNode,
    MyPermissionsResponse,
    RfidTagCreateRequest,
    RfidTagImportResponse,
    RfidTagResponse,
    RfidTagUpdateRequest,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
    ScannerApiKeyResponse,
    ScannerCreateRequest,
    ScannerResponse,
    ScannerUpdateRequest,
    ScreenPermissionResponse,
    ScreenResponse,
    SetRolePermissionsRequest,
    SetUserRoleRequest,
    TagDashboardResponse,
    TagHeaderDataResponse,
    TagHeaderDataScanResponse,
    TagLineDataResponse,
    TagLineDataSyncResponse,
    TagscanSettingsResponse,
    TagscanSettingsUpdateRequest,
    TagscanUserSummaryResponse,
)

router = APIRouter(prefix="/api/modules/module-1", tags=["Tagscan"])


def _content_disposition(filename: str) -> str:
    """A safe "Content-Disposition: attachment" header value for a
    filesystem-derived filename that's never been validated against HTTP
    header syntax — escapes `"`/`\\` so the name can't break out of the
    quoted-string form, and adds the RFC 5987 filename* fallback so a
    non-ASCII name still round-trips correctly in browsers that support it.
    """
    ascii_fallback = filename.encode("ascii", "replace").decode("ascii").replace("\\", "_").replace('"', "_")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"


@router.get("/dashboard", response_model=TagDashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    _user: User = Depends(require_module_access),
) -> TagDashboardResponse:
    """Aggregate KPI stats for TagScan's landing dashboard — gated by
    plain module access only, matching the landing page's own
    unconditional visibility (no specific screen permission needed, same
    as the placeholder it replaces).
    """
    return build_dashboard_stats(db)


def _build_role_response(db: Session, role: TagscanRole) -> RoleResponse:
    """Turn one role into its full permission-matrix response: every
    registered screen, paired with that role's permissions on it (all
    False if the role has never been given any permissions there yet).
    """
    screens = db.scalars(select(TagscanScreen).order_by(TagscanScreen.sort_order)).all()
    permissions_by_screen_id = {
        permission.screen_id: permission
        for permission in db.scalars(select(TagscanRolePermission).where(TagscanRolePermission.role_id == role.id))
    }

    permission_rows = []
    for screen in screens:
        # If this role has never had its permissions set for this screen,
        # treat every action as "not allowed" rather than erroring out.
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


@router.get("/files/tree", response_model=FolderNode)
def get_folder_tree(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.dashboard", "view")),
) -> FolderNode:
    """The full folder structure of the CSV intake directory, for the
    Dashboard screen's folder-tree pane.
    """
    return build_folder_tree(get_source_root(db))


@router.get("/files", response_model=list[FileEntryResponse])
def get_folder_files(
    path: str = "",
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.dashboard", "view")),
) -> list[FileEntryResponse]:
    """The files directly inside one folder of the CSV intake directory
    (not its subfolders), for the Dashboard screen's file-list pane.
    """
    folder = resolve_safe_path(db, path)
    if not folder.is_dir():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return list_files(db, folder)


@router.get("/files/content", response_model=FileContentResponse)
def get_file_content(
    path: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.dashboard", "view")),
) -> FileContentResponse:
    """One file's text content, for the Dashboard screen's "notepad" preview pane."""
    file = resolve_safe_path(db, path)
    if not file.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    content, truncated = read_file_preview(file)
    return FileContentResponse(path=path, content=content, truncated=truncated)


@router.get("/header-data", response_model=list[TagHeaderDataResponse])
def list_tag_header_data(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.tag-headerdata", "view")),
) -> list[TagHeaderData]:
    """List every CSV file logged so far, for the Tag Headerdata screen's table."""
    return list_header_data(db)


@router.get("/header-data/{header_id}/pdf")
def download_tag_header_pdf(
    header_id: int,
    locale: str = "nl",
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.tag-headerdata", "view")),
) -> Response:
    """A "beautiful layout" PDF summary of one scanned file's lines,
    grouped by matched product with a subtotal per group — see
    tag_header_pdf.build_header_summary_pdf.
    """
    header = db.get(TagHeaderData, header_id)
    if header is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File record not found")

    pdf_bytes = build_header_summary_pdf(db, header, locale=locale)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": _content_disposition(f"{header.filename}.pdf")},
    )


@router.post("/header-data/scan", response_model=TagHeaderDataScanResponse)
def scan_tag_header_data(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.tag-headerdata", "create")),
) -> TagHeaderDataScanResponse:
    """Scan Unreaded Tags for CSV files not yet logged: count each file's
    lines, log it, and move it into Read Tags so it's never picked up
    again. One bad file is reported, not fatal to the rest of the scan —
    see app/modules/module_1/tag_header_data.py.
    """
    results, entries = scan_unreaded_tags(db)
    return TagHeaderDataScanResponse(
        results=results,
        entries=[TagHeaderDataResponse.model_validate(entry, from_attributes=True) for entry in entries],
    )


@router.delete("/header-data/{header_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag_header_data(
    header_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.tag-headerdata", "delete")),
) -> None:
    """Permanently delete one Tag Headerdata row and every Tag Linedata
    row linked to it, so its filename can be logged again later. Does
    NOT touch the physical CSV file — move it back into Unreaded Tags
    yourself if you want it re-scanned.
    """
    if not delete_header_data(db, header_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File record not found")


def _build_line_data_response(line: TagLineData, header_filename: str) -> TagLineDataResponse:
    return TagLineDataResponse(
        id=line.id,
        header_data_id=line.header_data_id,
        header_filename=header_filename,
        line_number=line.line_number,
        scanner=line.scanner,
        epc=line.epc,
        rssi=line.rssi,
        antenna=line.antenna,
        count=line.count,
        last_seen=line.last_seen,
        mode=line.mode,
        action=line.action,
        rfid_tag_id=line.rfid_tag_id,
        assigned_product_name=line.assigned_product_name,
        assigned_serial_number=line.assigned_serial_number,
        manufacturer=line.manufacturer,
        batch_number=line.batch_number,
        scanner_id=line.scanner_id,
        scanner_name=line.scanner_name,
        scanner_location=line.scanner_location,
        scanner_technology=line.scanner_technology,
        status=line.status,
        created_at=line.created_at,
    )


@router.get("/line-data", response_model=list[TagLineDataResponse])
def list_tag_line_data(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.tag-linedata", "view")),
) -> list[TagLineDataResponse]:
    """List every CSV data line logged so far, for the Tag Linedata screen's table."""
    return [_build_line_data_response(line, filename) for line, filename in list_line_data(db)]


@router.post("/line-data/sync", response_model=TagLineDataSyncResponse)
def sync_tag_line_data(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.tag-linedata", "edit")),
) -> TagLineDataSyncResponse:
    """Re-check every non-cancelled line's EPC against the CURRENT
    TagManagement registry and refresh its status/product/serial/
    manufacturer/batch snapshot — see tag_line_data.sync_line_data for
    why cancelled lines are skipped.
    """
    updated_count = sync_line_data(db)
    return TagLineDataSyncResponse(
        updated_count=updated_count,
        entries=[_build_line_data_response(line, filename) for line, filename in list_line_data(db)],
    )


@router.post("/line-data/{line_id}/cancel", response_model=TagLineDataResponse)
def cancel_tag_line_data(
    line_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.tag-linedata", "edit")),
) -> TagLineDataResponse:
    """Manually mark one line as cancelled — the only way a line's status
    ever becomes "cancelled" (scanning itself only ever produces
    "converted" or "no_match").
    """
    line = db.get(TagLineData, line_id)
    if line is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Line not found")

    line.status = "cancelled"
    db.commit()
    db.refresh(line)

    header = db.get(TagHeaderData, line.header_data_id)
    return _build_line_data_response(line, header.filename)


def _validate_tag_lookup_ids(db: Session, payload: RfidTagCreateRequest | RfidTagUpdateRequest) -> None:
    """Make sure assigned_product_id, if given, actually exists — the
    same pattern used for Product's own type_id/warehouse_id/category_id/
    limit_id (see app/modules/module_9/router.py) — otherwise a bad id
    would only surface as an opaque foreign-key IntegrityError instead of
    a clear 404.
    """
    if payload.assigned_product_id is not None and db.get(Product, payload.assigned_product_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")


@router.get("/tags", response_model=list[RfidTagResponse])
def list_tags(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.tag-management", "view")),
) -> list[RfidTag]:
    """List every registered RFID tag, for the TagManagement screen's table."""
    return list(db.scalars(select(RfidTag).order_by(RfidTag.epc_uid)).all())


@router.post("/tags", response_model=RfidTagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(
    payload: RfidTagCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.tag-management", "create")),
) -> RfidTag:
    """Register a brand-new RFID tag."""
    _validate_tag_lookup_ids(db, payload)

    new_tag = RfidTag(**payload.model_dump())
    db.add(new_tag)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A tag with this EPC/UID already exists"
        ) from error

    db.refresh(new_tag)
    return new_tag


@router.put("/tags/{tag_id}", response_model=RfidTagResponse)
def update_tag(
    tag_id: int,
    payload: RfidTagUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.tag-management", "edit")),
) -> RfidTag:
    """Update every field of an existing tag."""
    tag = db.get(RfidTag, tag_id)
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    _validate_tag_lookup_ids(db, payload)

    for field, value in payload.model_dump().items():
        setattr(tag, field, value)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A tag with this EPC/UID already exists"
        ) from error

    db.refresh(tag)
    return tag


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.tag-management", "delete")),
) -> None:
    """Permanently delete a tag."""
    tag = db.get(RfidTag, tag_id)
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    db.delete(tag)
    db.commit()


def _validate_scanner_lookup_ids(db: Session, payload: ScannerCreateRequest | ScannerUpdateRequest) -> None:
    """Make sure type_id actually exists — same pattern as
    _validate_tag_lookup_ids above, but type_id is always required here
    (there's no "optional" case to skip), otherwise a bad id would only
    surface as an opaque foreign-key IntegrityError instead of a clear 404.
    """
    if db.get(ProductType, payload.type_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product type not found")


@router.get("/scanners", response_model=list[ScannerResponse])
def list_scanners(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.scanners", "view")),
) -> list[Scanner]:
    """List every registered scanner device, for the Scanners screen's table."""
    return list(db.scalars(select(Scanner).order_by(Scanner.scanner)).all())


@router.post("/scanners", response_model=ScannerResponse, status_code=status.HTTP_201_CREATED)
def create_scanner(
    payload: ScannerCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.scanners", "create")),
) -> Scanner:
    """Register a brand-new scanner device."""
    _validate_scanner_lookup_ids(db, payload)

    new_scanner = Scanner(**payload.model_dump())
    db.add(new_scanner)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A scanner with this name already exists"
        ) from error

    db.refresh(new_scanner)
    return new_scanner


@router.put("/scanners/{scanner_id}", response_model=ScannerResponse)
def update_scanner(
    scanner_id: int,
    payload: ScannerUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.scanners", "edit")),
) -> Scanner:
    """Update every field of an existing scanner."""
    scanner = db.get(Scanner, scanner_id)
    if scanner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scanner not found")

    _validate_scanner_lookup_ids(db, payload)

    for field, value in payload.model_dump().items():
        setattr(scanner, field, value)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A scanner with this name already exists"
        ) from error

    db.refresh(scanner)
    return scanner


@router.delete("/scanners/{scanner_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scanner(
    scanner_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.scanners", "delete")),
) -> None:
    """Permanently delete a scanner device — blocked while it's still
    referenced by any logged Tag Headerdata file or Tag Linedata line, so
    a snapshot's scanner_id can never dangle (see tag_line_data.py's
    module docstring on why these fields are a snapshot in the first
    place).
    """
    scanner = db.get(Scanner, scanner_id)
    if scanner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scanner not found")

    still_used = db.scalar(
        select(TagHeaderData.id).where(TagHeaderData.scanner_id == scanner_id)
    ) or db.scalar(select(TagLineData.id).where(TagLineData.scanner_id == scanner_id))
    if still_used is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This scanner is still used by at least one logged file/line",
        )

    db.delete(scanner)
    db.commit()


@router.post("/scanners/{scanner_id}/api-key", response_model=ScannerApiKeyResponse)
def generate_scanner_api_key(
    scanner_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.scanners", "edit")),
) -> ScannerApiKeyResponse:
    """Generate a brand-new API key for a scanner's device-intake uploads
    (see app/modules/module_1/device_router.py), invalidating any previous
    one. The plaintext key is returned here once and never again — only
    its hash is stored.
    """
    scanner = db.get(Scanner, scanner_id)
    if scanner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scanner not found")

    api_key = f"module1_{scanner.id}_{secrets.token_urlsafe(32)}"
    scanner.api_key_hash = hash_password(api_key)
    scanner.api_key_generated_at = datetime.now(timezone.utc)
    scanner.api_key_last_used_at = None
    db.commit()

    return ScannerApiKeyResponse(api_key=api_key)


@router.delete("/scanners/{scanner_id}/api-key", status_code=status.HTTP_204_NO_CONTENT)
def revoke_scanner_api_key(
    scanner_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.scanners", "edit")),
) -> None:
    """Revoke a scanner's current API key, if any — its device-intake
    uploads will start being rejected with 401 immediately.
    """
    scanner = db.get(Scanner, scanner_id)
    if scanner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scanner not found")

    scanner.api_key_hash = None
    scanner.api_key_generated_at = None
    scanner.api_key_last_used_at = None
    db.commit()


def _resolve_settings_response(db: Session) -> TagscanSettingsResponse:
    override = db.get(TagscanSettings, SETTINGS_ROW_ID)
    if override is not None and override.receive_folder_path:
        return TagscanSettingsResponse(receive_folder_path=override.receive_folder_path, is_override=True)
    return TagscanSettingsResponse(receive_folder_path=settings.tagscan_source_dir, is_override=False)


@router.get("/settings", response_model=TagscanSettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.settings", "view")),
) -> TagscanSettingsResponse:
    """The currently effective receive-folder path — a DB-saved override
    if one exists, otherwise the .env-configured default.
    """
    return _resolve_settings_response(db)


@router.put("/settings", response_model=TagscanSettingsResponse)
def update_settings(
    payload: TagscanSettingsUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.settings", "edit")),
) -> TagscanSettingsResponse:
    """Save a new receive-folder-path override. Fails fast with a clear
    400 if the backend process can't actually create/access that path,
    rather than silently saving a broken configuration.
    """
    try:
        Path(payload.receive_folder_path).mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot use this folder: {error}"
        ) from error

    override = db.get(TagscanSettings, SETTINGS_ROW_ID)
    if override is None:
        override = TagscanSettings(id=SETTINGS_ROW_ID, receive_folder_path=payload.receive_folder_path)
        db.add(override)
    else:
        override.receive_folder_path = payload.receive_folder_path
    db.commit()

    return _resolve_settings_response(db)


@router.get("/tags/template")
def download_tag_import_template(
    _user: User = Depends(require_screen_permission("tagscan.tag-management", "view")),
) -> Response:
    """The downloadable XLSX template for bulk-importing tags."""
    return Response(
        content=build_template_xlsx(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="tag-import-template.xlsx"'},
    )


@router.post("/tags/import", response_model=RfidTagImportResponse)
def import_tags(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.tag-management", "create")),
) -> RfidTagImportResponse:
    """Bulk-import tags from an uploaded XLSX workbook — best-effort:
    every row is applied independently, so invalid rows are skipped (and
    reported) rather than failing the whole upload.
    """
    results = import_tags_from_xlsx(db, file.file.read())
    return RfidTagImportResponse(results=results)


@router.get("/screens", response_model=list[ScreenResponse])
def list_screens(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.roles", "view")),
) -> list[TagscanScreen]:
    """List every registered Tagscan screen — used to build the columns of
    the permission-matrix grid in the UI.
    """
    return list(db.scalars(select(TagscanScreen).order_by(TagscanScreen.sort_order)).all())


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.roles", "view")),
) -> list[RoleResponse]:
    """List every Tagscan role, each with its full permission matrix."""
    roles = db.scalars(select(TagscanRole).order_by(TagscanRole.name)).all()
    return [_build_role_response(db, role) for role in roles]


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.roles", "create")),
) -> RoleResponse:
    """Create a brand-new role, with no permissions granted yet."""
    new_role = TagscanRole(name=payload.name)
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
    _user: User = Depends(require_screen_permission("tagscan.roles", "edit")),
) -> RoleResponse:
    """Rename an existing role."""
    role = db.get(TagscanRole, role_id)
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
    _user: User = Depends(require_screen_permission("tagscan.roles", "delete")),
) -> None:
    """Delete a role, as long as nobody currently holds it."""
    role = db.get(TagscanRole, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    still_assigned = db.scalar(select(TagscanUserRole).where(TagscanUserRole.role_id == role_id))
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
    _user: User = Depends(require_screen_permission("tagscan.roles", "edit")),
) -> RoleResponse:
    """Replace a role's entire permission matrix with exactly what was sent."""
    role = db.get(TagscanRole, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    existing_permissions = {
        permission.screen_id: permission
        for permission in db.scalars(select(TagscanRolePermission).where(TagscanRolePermission.role_id == role_id))
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
                TagscanRolePermission(
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


def _build_user_summary(db: Session, user: User) -> TagscanUserSummaryResponse:
    user_role = get_user_role(db, user.id)
    role = db.get(TagscanRole, user_role.role_id) if user_role else None
    return TagscanUserSummaryResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role_id=role.id if role else None,
        role_name=role.name if role else None,
    )


@router.get("/users", response_model=list[TagscanUserSummaryResponse])
def list_users(
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.users", "view")),
) -> list[TagscanUserSummaryResponse]:
    """List every user with access to Tagscan, and their current role."""
    module = db.scalar(select(Module).where(Module.key == MODULE_KEY))
    users_with_access = db.scalars(
        select(User)
        .join(UserModuleAccess, UserModuleAccess.user_id == User.id)
        .where(UserModuleAccess.module_id == module.id)
        .order_by(User.display_name)
    ).all()
    return [_build_user_summary(db, user) for user in users_with_access]


@router.put("/users/{user_id}/role", response_model=TagscanUserSummaryResponse)
def set_user_role(
    user_id: int,
    payload: SetUserRoleRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.users", "edit")),
) -> TagscanUserSummaryResponse:
    """Assign (or, if role_id is null, remove) a Tagscan role for a user
    who already has access to Tagscan.
    """
    target_user = db.get(User, user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    module = db.scalar(select(Module).where(Module.key == MODULE_KEY))
    has_access = db.scalar(
        select(UserModuleAccess).where(UserModuleAccess.user_id == user_id, UserModuleAccess.module_id == module.id)
    )
    if has_access is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This user does not have access to Tagscan")

    existing_role_row = get_user_role(db, user_id)

    if payload.role_id is None:
        if existing_role_row is not None:
            db.delete(existing_role_row)
    else:
        role = db.get(TagscanRole, payload.role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        if existing_role_row is not None:
            existing_role_row.role_id = payload.role_id
        else:
            db.add(TagscanUserRole(user_id=user_id, role_id=payload.role_id))

    db.commit()
    return _build_user_summary(db, target_user)


@router.post("/users", response_model=TagscanUserSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_or_grant_user(
    payload: CreateOrGrantUserRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_screen_permission("tagscan.users", "create")),
) -> TagscanUserSummaryResponse:
    """Give someone access to Tagscan, creating their account first if
    they don't already have one anywhere in RW Crew.

    This ALWAYS grants access to Tagscan only — never any other module —
    regardless of who calls it, which is what keeps a Tagscan admin (not
    just the super admin) safely able to onboard people on their own.
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
        role = db.get(TagscanRole, payload.role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        existing_role_row = get_user_role(db, target_user.id)
        if existing_role_row is not None:
            existing_role_row.role_id = payload.role_id
        else:
            db.add(TagscanUserRole(user_id=target_user.id, role_id=payload.role_id))

    db.commit()
    return _build_user_summary(db, target_user)


@router.get("/me/permissions", response_model=MyPermissionsResponse)
def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access),
) -> MyPermissionsResponse:
    """Tell the frontend which Tagscan screens the current user can view,
    so it knows what to show in the sidebar without duplicating the
    permission-checking rules itself.
    """
    screens = db.scalars(select(TagscanScreen)).all()
    viewable_keys = [screen.key for screen in screens if user_can(db, current_user, screen.key, "view")]
    return MyPermissionsResponse(viewable_screen_keys=viewable_keys)
