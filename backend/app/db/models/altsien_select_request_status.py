# This file defines the "AltsienSelect_request_status" table: the editable
# list of statuses a special request can have (seeded with New / In
# Progress / Completed), managed on its own screen the same way
# Intervention Requests manages its statuses (see intervention_status.py).

from sqlalchemy import Boolean, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AltsienSelectRequestStatus(Base):
    """One row per status a special request can be set to."""

    __tablename__ = "AltsienSelect_request_status"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The status name, e.g. "New". Must be unique.
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # Whether requests in this status still need follow-up (counted as
    # "open" on the KPI screen).
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    # One of app.schemas.intervention_requests.StatusColor's fixed palette.
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="gray", server_default=text("'gray'"))

    # Controls the order statuses are listed in; the lowest one is the
    # status a newly created request starts in.
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
