# This file defines the "InterventionRequests_request" database table:
# the main entity of the Intervention Requests screen, matching the core
# fields of the reference spreadsheet RWCrew staff already use during the
# festival to log requests from participating associations (repairs,
# supplies, deliveries, etc.) — everything except the legacy Google-Form/
# Drive workflow columns (a plain sequential ID, an "email sent" flag, a
# PDF-file link, a "synced to central DB" flag), which belonged to that
# old external process and have no place in this fresh in-app screen.

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InterventionRequest(Base):
    """One row per intervention request logged by an association."""

    __tablename__ = "InterventionRequests_request"

    id: Mapped[int] = mapped_column(primary_key=True)

    # "Aanvraagnummer": the unique, human-facing request number, generated
    # server-side as "IA<last 2 digits of the current year>_<sequence>"
    # (e.g. "IA26_0001") — never accepted from the client. Listed first
    # among the business columns since it's the identifier staff actually
    # look up requests by.
    request_number: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)

    # "Timestamp": when this request was logged, set automatically at
    # creation — not user-editable, the same way ModuleRole.assigned_at is
    # auto-set rather than part of any create/update form.
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # "Ploeg": which MasterData team this request is for — a foreign key
    # into MasterData_team (see app/db/models/team.py) rather than free
    # text, so it's always one of the actual teams defined in MasterData.
    # Nullable because the public (no-login) intervention-request form lets a
    # customer type a Ploeg name that isn't in MasterData yet — in that case
    # team_id stays null and team_name below carries the typed name instead.
    # Exactly one of the two is ever set; enforced in
    # app/schemas/intervention_requests.py, not at the DB level.
    team_id: Mapped[int | None] = mapped_column(ForeignKey("MasterData_team.id"), nullable=True)

    # "Ploeg" as free text, used only when team_id is null (see above).
    team_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # "Kar Nummer": the association's own cart number, if any.
    cart_number: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # "Vraag / Opmerking": the actual request/remark text.
    question: Mapped[str] = mapped_column(Text, nullable=False)

    # "Naam Medewerker" / "Mobiel Nummer Medewerker": who from the
    # association submitted this request, and how to reach them.
    employee_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employee_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # "Voorkeur Moment van Levering": when the association would like this
    # delivered/handled.
    preferred_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # "Afleverplaats" / "Zone": where to deliver/act, and which festival
    # zone that's in.
    delivery_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    zone: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # "Status": selected from the Intervention Statuses lookup screen.
    status_id: Mapped[int] = mapped_column(ForeignKey("InterventionRequests_status.id"), nullable=False)

    # "Uitvoerder": which RWCrew staff member handled/is handling this.
    handled_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # "Team Kar": which RWCrew staff member (a current TeamKar member —
    # see app/db/models/teamkar_member.py) handled the delivery cart for
    # this request. A reference into Landing_users rather than free text,
    # so it's always one of the actual TeamKar members. ondelete="SET NULL"
    # so deleting that user account just clears this field instead of
    # breaking the request, the same "soft" degrade as handled_by today.
    team_cart_user_id: Mapped[int | None] = mapped_column(ForeignKey("Landing_users.id", ondelete="SET NULL"), nullable=True)
