# This file defines the "can this user do that?" checks used by every
# Altsien Select endpoint. Altsien Select doesn't use the
# shared, generic app/modules/common.py factory that most other modules
# use, because it needs a richer permission model: custom roles with a
# separate view/create/edit/delete switch per screen, instead of one fixed
# admin/editor/reader role — the same pattern as app/modules/module_3/deps.py.
# On top of that it decides which teams a user may work on (their own teams
# as Altsien Kernlid, or all teams for the organisation) and whether a
# season is still open for changes.

from typing import Literal

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.altsien_select_role_permission import AltsienSelectRolePermission
from app.db.models.altsien_select_screen import AltsienSelectScreen
from app.db.models.altsien_select_user_role import AltsienSelectUserRole
from app.db.models.module import Module
from app.db.models.season import Season
from app.db.models.team import Team
from app.db.models.team_kernlid import TeamKernlid
from app.db.models.user import User
from app.db.models.user_module_access import UserModuleAccess
from app.landing.deps import get_current_user

MODULE_KEY = "module-8"
MODULE_LABEL = "Altsien Select"

# The four actions a role's permission on a screen can be checked for.
PermissionAction = Literal["view", "create", "edit", "delete"]


def require_module_access(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> User:
    """Only let the request through if the user has been granted access to
    Altsien Select at all (super admins are not automatically
    exempt — matching every other module's behaviour, see
    app/shared/access.py).
    """
    module = db.scalar(select(Module).where(Module.key == MODULE_KEY))
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{MODULE_LABEL} module not found")

    has_access = db.scalar(
        select(UserModuleAccess).where(
            UserModuleAccess.user_id == current_user.id, UserModuleAccess.module_id == module.id
        )
    )
    if has_access is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"No access to {MODULE_LABEL}")

    return current_user


def get_user_role(db: Session, user_id: int) -> AltsienSelectUserRole | None:
    """Look up the calling user's current Altsien Select role
    assignment, if any.
    """
    return db.scalar(select(AltsienSelectUserRole).where(AltsienSelectUserRole.user_id == user_id))


def get_permission_for_screen(db: Session, role_id: int, screen_id: int) -> AltsienSelectRolePermission | None:
    """Look up one role's permissions row for one screen. Returns None if
    that role has never been given any permissions on that screen at all
    — which simply means "no access", the same as every flag being False.
    """
    return db.scalar(
        select(AltsienSelectRolePermission).where(
            AltsienSelectRolePermission.role_id == role_id,
            AltsienSelectRolePermission.screen_id == screen_id,
        )
    )


def user_can(db: Session, user: User, screen_key: str, action: PermissionAction) -> bool:
    """The actual yes/no permission check, reused by both
    require_screen_permission (below) and the "my permissions" endpoint.
    """
    if user.is_super_admin:
        # The site-wide super admin can always do anything in Altsien Select
        # — this is what lets them bootstrap the module's very
        # first role.
        return True

    screen = db.scalar(select(AltsienSelectScreen).where(AltsienSelectScreen.key == screen_key))
    if screen is None:
        return False

    user_role = get_user_role(db, user.id)
    if user_role is None:
        return False

    permission = get_permission_for_screen(db, user_role.role_id, screen.id)
    if permission is None:
        return False

    return {
        "view": permission.can_view,
        "create": permission.can_create,
        "edit": permission.can_edit,
        "delete": permission.can_delete,
    }[action]


def require_screen_permission(screen_key: str, action: PermissionAction):
    """Build a dependency that only lets a request through if the caller
    can perform "action" on the screen identified by "screen_key".
    """

    def dependency(
        db: Session = Depends(get_db),
        current_user: User = Depends(require_module_access),
    ) -> User:
        if not user_can(db, current_user, screen_key, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Not allowed to {action} on {screen_key}"
            )
        return current_user

    return dependency


# --- Team scope and season lock (Altsien Select specific) ----------------

# The switch-screen that widens a user's scope from "my own teams" to "all
# teams" (see screens.py).
ALL_TEAMS_SCREEN_KEY = "altsienselect.allteams"


def can_see_all_teams(db: Session, user: User) -> bool:
    """Whether this user works for the organisation (sees every team)
    rather than only the teams they're linked to as Altsien Kernlid.
    """
    return user_can(db, user, ALL_TEAMS_SCREEN_KEY, "view")


def accessible_team_ids(db: Session, user: User) -> set[int]:
    """The ids of the teams this user may open in the wizard/ploegfiche:
    every active team for the organisation, otherwise only the active teams
    linked to them in MasterData > Teams (Altsien Kernleden).
    """
    active_team_ids = select(Team.id).where(Team.active.is_(True))
    if can_see_all_teams(db, user):
        return set(db.scalars(active_team_ids).all())
    return set(
        db.scalars(
            active_team_ids.join(TeamKernlid, TeamKernlid.team_id == Team.id).where(
                TeamKernlid.altsien_kernlid_id == user.id
            )
        ).all()
    )


def get_team_in_scope(db: Session, user: User, team_id: int) -> Team:
    """Load a team the user is allowed to work on. A team outside their
    scope answers 404 (not 403), so its existence isn't revealed.
    """
    team = db.get(Team, team_id)
    if team is None or team_id not in accessible_team_ids(db, user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return team


def get_season_or_404(db: Session, season_id: int) -> Season:
    """Load a season, or answer 404."""
    season = db.get(Season, season_id)
    if season is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Season not found")
    return season


def season_is_editable_for(db: Session, user: User, season: Season) -> bool:
    """Choices can be changed while the season's period is open. The
    organisation (edit on "all teams") can still correct them afterwards.
    """
    return season.periode_open or user_can(db, user, ALL_TEAMS_SCREEN_KEY, "edit")


def ensure_season_editable(db: Session, user: User, season: Season) -> None:
    """Refuse a change once the season's period is closed (see above)."""
    if not season_is_editable_for(db, user, season):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This season is closed for changes")
