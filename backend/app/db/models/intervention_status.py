# This file defines the "InterventionRequests_status" database table: a
# manageable lookup list of the statuses an Intervention Request can have
# (Open, Geleverd, Gecanceled, ...), managed on its own screen the same
# way Season/ProductType are managed on MasterData's lookup screens,
# rather than being a hardcoded closed set — kept editable since the exact
# list of statuses used during a festival can change from year to year.

from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InterventionStatus(Base):
    """One row per status an Intervention Request can be set to."""

    __tablename__ = "InterventionRequests_status"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The status name, e.g. "Open", "Geleverd". Must be unique so the same
    # status can't accidentally be entered twice.
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Whether this status counts as "open" (checked) or "closed" (unchecked)
    # — stored now so requests can be filtered by it later; not enforced
    # anywhere yet. Defaults to open for both new rows and, via
    # server_default, any row that predates this column.
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    # Which colour (one of app.schemas.intervention_requests.StatusColor's
    # fixed palette) this status's requests are shown in on the
    # Intervention Requests list — see the "Kleur" field on this screen.
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="gray", server_default=text("'gray'"))
