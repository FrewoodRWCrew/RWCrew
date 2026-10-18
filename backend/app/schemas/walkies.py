# Schemas for Walkies (module-6). For now the module only has its
# access-rights screens, whose custom-roles shapes (screens, roles,
# permissions, users) are identical to module 3's, so they are re-used from
# app/schemas/intervention_requests.py — the same as StockMaster does. The
# walkie-talkie shapes are added here in phase 2.

from app.schemas.intervention_requests import (  # noqa: F401  (re-exported for the router)
    CreateOrGrantUserRequest,
    InterventionRequestsUserSummaryResponse as UserSummaryResponse,
    MyPermissionsResponse,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
    ScreenPermissionResponse,
    ScreenResponse,
    SetRolePermissionsRequest,
    SetUserRoleRequest,
)
