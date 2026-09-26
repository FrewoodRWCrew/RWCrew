# This file defines the "KarTracker_groundplan" table: one row per ground
# plan of the event site (e.g. one per zone or terrain), each holding its
# own image plus the geographic coordinates of its south-west/north-east
# corners, used to overlay it on the Kar Map. Every plan is drawn together
# on the map. The images are stored as bytes directly in Postgres rather
# than on local disk — there is no existing file-storage convention
# anywhere in this app, and these are a handful of rarely-changed images.

from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class KarTrackerGroundplan(Base):
    """One ground plan: a name, its image and its geographic bounds."""

    __tablename__ = "KarTracker_groundplan"

    id: Mapped[int] = mapped_column(primary_key=True)

    # A free-text label shown on the Grondplan list (e.g. "Zone Noord").
    # Not unique: two plans are allowed to share a name.
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # The raw image bytes and their content type (e.g. "image/png"), so the
    # image-serving endpoint can set the right Content-Type on the way out.
    image_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    image_content_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # The image's south-west and north-east corners, in plain lat/lng floats
    # — same column style as KarTrackerAfleverlocatie.latitude/longitude —
    # used as the bounds of the Leaflet ImageOverlay on the Kar Map.
    sw_latitude: Mapped[float] = mapped_column(nullable=False)
    sw_longitude: Mapped[float] = mapped_column(nullable=False)
    ne_latitude: Mapped[float] = mapped_column(nullable=False)
    ne_longitude: Mapped[float] = mapped_column(nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
