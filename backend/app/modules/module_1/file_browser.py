# Plain filesystem helpers backing TagScan's "Dashboard" screen: a
# read-only, Explorer-style browser over the folder where incoming CSV
# scan files currently land (see app.core.config.settings.tagscan_source_dir).
# Kept free of FastAPI/DB concerns so it's easy to unit test on its own.

from pathlib import Path

from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.tagscan import FileEntryResponse, FolderNode

# Files bigger than this are still listed, but their content preview stops
# here rather than reading an arbitrarily large file into memory/the browser.
MAX_PREVIEW_BYTES = 2 * 1024 * 1024  # 2 MB


def get_source_root() -> Path:
    """The folder currently configured as TagScan's CSV intake location."""
    return Path(settings.tagscan_source_dir)


def resolve_safe_path(relative_path: str) -> Path:
    """Turn a client-supplied relative path into a real filesystem path,
    guaranteed to stay inside the configured source folder.

    relative_path comes straight from a query parameter, so this is the
    one thing standing between this feature and a path-traversal
    vulnerability (e.g. "../../app/core/config.py") — every endpoint that
    accepts a path MUST go through this function first.
    """
    root = get_source_root().resolve()
    # An empty path means "the root folder itself".
    candidate = (root / relative_path).resolve() if relative_path else root

    if candidate != root and root not in candidate.parents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path")

    return candidate


def build_folder_tree(root: Path) -> FolderNode:
    """Recursively describe every folder under (and including) root — no
    files, just the folder structure, for the tree pane on the left.
    """

    def describe(folder: Path) -> FolderNode:
        relative = "" if folder == root else str(folder.relative_to(root)).replace("\\", "/")
        subfolders = sorted((entry for entry in folder.iterdir() if entry.is_dir()), key=lambda entry: entry.name)
        return FolderNode(
            name=folder.name if folder != root else root.name,
            path=relative,
            children=[describe(subfolder) for subfolder in subfolders],
        )

    return describe(root)


def list_files(folder: Path) -> list[FileEntryResponse]:
    """List the files directly inside one folder (not its subfolders),
    for the file-list pane once a folder is selected.
    """
    root = get_source_root().resolve()
    entries = sorted((entry for entry in folder.iterdir() if entry.is_file()), key=lambda entry: entry.name)

    files = []
    for entry in entries:
        stats = entry.stat()
        files.append(
            FileEntryResponse(
                name=entry.name,
                path=str(entry.relative_to(root)).replace("\\", "/"),
                size_bytes=stats.st_size,
                modified_at=stats.st_mtime,
            )
        )
    return files


def read_file_preview(file: Path) -> tuple[str, bool]:
    """Read a file's content for the "notepad" preview panel, capped at
    MAX_PREVIEW_BYTES. Returns (content, was_truncated). Decoding uses
    errors="replace" since these are expected to be plain-text CSVs, but a
    stray non-UTF-8 byte shouldn't turn into a 500 error.
    """
    size = file.stat().st_size
    with file.open("rb") as handle:
        raw = handle.read(MAX_PREVIEW_BYTES)

    return raw.decode("utf-8", errors="replace"), size > MAX_PREVIEW_BYTES
