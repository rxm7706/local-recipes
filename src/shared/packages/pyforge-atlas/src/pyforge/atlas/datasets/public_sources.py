"""The one reader of ``pyforge.atlas.live_public_sources`` (Story 34.4, CAP-64).

Every public-source dataset Epic 34 wires asks :func:`live` at the moment it would fetch,
never at import. The atlas test suite pins :func:`live` OFF in its root ``conftest.py``,
so no test reaches the network (Epic 34's hard boundary, AD-11); a test of the live path
patches it ON and supplies its own responses.
"""

from __future__ import annotations

from typing import Any

from kedro.io import DatasetError
from kedro_datasets.api import APIDataset
from pyforge.core.flags import read_boolean

FLAG_KEY = "pyforge.atlas.live_public_sources"


def live() -> bool:
    """Whether a public-source dataset may fetch now (``False`` when the flag tree is unreadable)."""
    return read_boolean(FLAG_KEY, default=False)


def _no_auth(request: Any) -> Any:
    return request


def request_args(timeout: int) -> dict[str, Any]:
    """``APIDataset`` ``load_args`` for an unauthenticated public GET: a timeout, and a no-op
    ``auth``. With no ``auth``, requests reads ``~/.netrc`` (or ``$NETRC``) and would send any
    credential kept there for the host, a GitHub token for git over HTTPS among them; a truthy
    no-op auth stops that on the request itself. (A redirect to another host still consults
    netrc for that host -- requests' ``rebuild_auth``.)"""
    return {"timeout": timeout, "auth": _no_auth}


def fetch_text(url: str, *, timeout: int = 300) -> str:
    """Story 34.6: one unauthenticated public GET over a composed ``APIDataset`` (AD-2), as
    text: the declared charset, else UTF-8 (requests would read a ``text/*`` body with no
    charset as ISO-8859-1). The per-URL fetcher the discovery stores take. A failed request
    raises ``DatasetError`` (kedro's wrapper); the store's refresh keeps last-good under its
    AD-13 marker."""
    payload = APIDataset(url=url, load_args=request_args(timeout)).load()
    content = getattr(payload, "content", None)
    if not isinstance(content, bytes):
        raise DatasetError(f"{url}: expected a bytes body, got {type(content).__name__}")
    headers = getattr(payload, "headers", None) or {}
    declared = "charset=" in str(headers.get("content-type", "")).lower()
    encoding = getattr(payload, "encoding", None) if declared else None
    return content.decode(encoding or "utf-8", errors="replace")
