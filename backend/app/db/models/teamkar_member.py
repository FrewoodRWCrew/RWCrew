# This file defines the "InterventionRequests_teamkar_member" table: which
# app users are currently members of "TeamKar" — module-3's single, fixed
# group of users eligible for the "Team Kar" dropdown on intervention
# requests. Unlike MasterData_team_kernlid (see app/db/models/team_kernlid.py)
# this is NOT scoped to a team_id — there is only ever one TeamKar group, so
# a user_id alone (unique) is enough to say "this user is a member".

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TeamKarMember(Base):
    """One row means: this user is a member of TeamKar."""

    __tablename__ = "InterventionRequests_teamkar_member"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("Landing_users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
