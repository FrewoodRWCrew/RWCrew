# Adds the help-manual endpoint to a module's own router:
#
#   GET /api/modules/<module>/help/pdf?locale=nl|en[&topic=<topic>]
#
# The sidebar's "Handleiding" link asks for the whole manual, the (?) next
# to a screen for one topic. The module passes in its own module-access
# dependency and a function returning the screen keys the user may view, so
# each module keeps using its own rights system (no new rights needed).

from collections.abc import Callable, Collection
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models.user import User
from app.help.content import has_manual, load_manual
from app.help.help_pdf import TopicNotFound, build_help_pdf

Locale = Literal["nl", "en"]


def register_help_route(
    router: APIRouter,
    *,
    module_key: str,
    require_access: Callable[..., User],
    viewable_screen_keys: Callable[[Session, User], Collection[str]],
) -> None:
    """Add GET /help/pdf to `router` for the module `module_key`."""

    @router.get("/help/pdf")
    def get_help_pdf(
        locale: Locale = "nl",
        topic: str | None = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(require_access),
    ) -> Response:
        """The module's manual (or one topic of it), opened inline in a new
        browser tab. Only chapters of screens the user may view are in it.
        """
        # Fall back to Dutch when a module has no manual in this language yet.
        language = locale if has_manual(module_key, locale) else "nl"
        if not has_manual(module_key, language):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="help_not_found")

        try:
            content = build_help_pdf(
                module_key,
                language,
                set(viewable_screen_keys(db, current_user)),
                topic=topic,
                printed_for=current_user.display_name,
            )
        except TopicNotFound:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="help_topic_not_found") from None

        # e.g. "StockMaster - Handleiding.pdf" or "StockMaster - book-in.pdf".
        filename = f"{load_manual(module_key, language).title} - {topic or 'Handleiding'}.pdf"
        ascii_fallback = filename.encode("ascii", "replace").decode("ascii").replace('"', "_")
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"},
        )
