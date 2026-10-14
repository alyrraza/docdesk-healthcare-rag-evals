"""GET / and GET /static/{name}: the page and its fixed list of files, no directory mount."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from docdesk.core.errors import AppError

STATIC_DIR = Path(__file__).parent / "static"

# Explicit names and types: a Windows registry can map .js to text/plain, and a fixed list
# means no request can ever reach another file by path tricks.
FILE_TYPES: dict[str, str] = {
    "index.html": "text/html; charset=utf-8",
    "style.css": "text/css; charset=utf-8",
    "main.js": "text/javascript; charset=utf-8",
    "api.js": "text/javascript; charset=utf-8",
    "dom.js": "text/javascript; charset=utf-8",
    "render.js": "text/javascript; charset=utf-8",
}

# The page loads everything from itself and talks only to its own origin.
CSP = (
    "default-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; "
    "form-action 'self'; frame-ancestors 'none'"
)
HEADERS = {"content-security-policy": CSP, "x-content-type-options": "nosniff"}

router = APIRouter()


def serve(name: str) -> FileResponse:
    """Send one listed file, or the typed 404 for any other name."""
    if name not in FILE_TYPES:
        raise AppError("not_found", "Not Found", 404)
    return FileResponse(STATIC_DIR / name, media_type=FILE_TYPES[name], headers=HEADERS)


@router.get("/", include_in_schema=False)
def page() -> FileResponse:
    """Give a person the question page; it holds no data, the API calls need a login."""
    return serve("index.html")


@router.get("/static/{name}", include_in_schema=False)
def static_file(name: str) -> FileResponse:
    """Give the page its stylesheet and scripts from a fixed list."""
    return serve(name)
