# This file defines the "KarTracker_groundplan" table: a single row (id=1)
# holding the event site's ground-plan image plus the geographic
# coordinates of its south-west/north-east corners, used to overlay it on
# the Kar Map. The image is stored as bytes directly in Postgres rather
# than on local disk — there is no existing file-storage convention
# anywhere in this app, and this is a single, rarely-changed image, same
# "single settings row" shape as Tagscan_settings.

from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class KarTrackerGroundplan(Base):
    """A single row (id=1): the ground-plan image and its geographic bounds."""

    __tablename__ = "KarTracker_groundplan"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The raw image bytes and their content type (e.g. "image/png"), so the
    # image-serving endpoint can set the right Content-Type on the way out.
    # Both NULL until an image has ever been uploaded.
    image_data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    image_content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # The image's south-west and north-east corners, in plain lat/lng floats
    # — same column style as KarTrackerAfleverlocatie.latitude/longitude —
    # used as the bounds of the Leaflet ImageOverlay on the Kar Map.
    sw_latitude: Mapped[float | None] = mapped_column(nullable=True)
    sw_longitude: Mapped[float | None] = mapped_column(nullable=True)
    ne_latitude: Mapped[float | None] = mapped_column(nullable=True)
    ne_longitude: Mapped[float | None] = mapped_column(nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
