"""The artifact loads nothing from another origin (Story 43.3, CAP-61; AD-21, CAP-56): every absolute URL its HTML,
CSS and JS load (src, srcset, poster, data, a loading <link>, url(), @import, fetch, import(), .src=) is on `origin`; no
href names `other` (the public host, building for another). An off-site link is navigation, not a load."""

import re
from pathlib import Path
from urllib.parse import urlparse

_URL = r"""((?:https?:)?//[^\s"'`)<>,;]+)"""
_LOADS = [
    rf"""<(?:script|img|iframe|frame|source|video|audio|track|embed|input|object)\b[^>]*?\s(?:src|poster|data)\s*=\s*["']?{_URL}""",
    rf"""<(?:img|source)\b[^>]*?\ssrcset\s*=\s*["'][^"']*?{_URL}""",
    rf"""<link\b(?=[^>]*\brel\s*=\s*["']?[^"'>]*(?:stylesheet|icon|preload|prefetch|preconnect|dns-prefetch|manifest))"""
    rf"""[^>]*?\shref\s*=\s*["']?{_URL}""",
    rf"""(?:@import\s+(?:url\(\s*)?|url\(\s*)["']?{_URL}""",
    rf"""(?:\b(?:fetch|import|importScripts)\s*\(|\.src\s*=|setAttribute\(\s*["']src["']\s*,)\s*["'`]{_URL}""",
]
_LOAD = re.compile("|".join(f"(?:{p})" for p in _LOADS), re.IGNORECASE)
_LINK = re.compile(rf"""\bhref\s*=\s*["']?{_URL}""", re.IGNORECASE)


def site_origin(url: str) -> str:
    parsed = urlparse(f"https:{url}" if url.startswith("//") else url)
    return f"{parsed.scheme}://{parsed.hostname}{f':{parsed.port}' if parsed.port else ''}".lower()


def findings(root: Path, origin: str, other: str = "", exempt: tuple[str, ...] = ()) -> list[str]:
    """One line per offending URL: the file, relative to `root`; `exempt` names vendored files and roots (ending /)."""
    out = []
    for path in sorted(p for p in root.rglob("*") if p.suffix.lower() in {".html", ".css", ".js", ".mjs"}):
        rel = path.relative_to(root).as_posix()
        if any(rel == e or (e.endswith("/") and rel.startswith(e)) for e in exempt):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        loads = [u for m in _LOAD.finditer(text) for u in m.groups() if u and site_origin(u) != origin]
        links = [u for u in _LINK.findall(text) if other and other != origin and site_origin(u) == other]
        out += [f"{rel}: loads {u!r} from another origin (expected {origin})" for u in loads]
        out += [f"{rel}: links {u!r} on the other host {other}" for u in links]
    return out
