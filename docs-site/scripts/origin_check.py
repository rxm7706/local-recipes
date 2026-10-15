"""Nothing loads from another origin (Story 43.3; AD-21, CAP-56): each URL a loading tag's src, srcset candidate, poster, data or SVG
href, a loading <link>, url(), @import, fetch, XHR, import() or .src= names, entities and \\/ unescaped, is on `origin`; no href names `other`."""

import html
import re
from pathlib import Path
from urllib.parse import urlparse

_URL = r"""((?:https?:)?//[^\s"'`)<>,;]+)"""
_TAG = re.compile(r"""<(link|script|img|i?frame|source|video|audio|track|embed|input|object|image|use)\b((?:[^>"']|"[^"]*"|'[^']*')*)>""", re.I)
_ATTR = re.compile(r"""[\s/](?:src|srcset|poster|data|href|xlink:href)\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)""", re.I)
_REL = re.compile(r"""\brel\s*=\s*["']?[^"'>]*\b(?:stylesheet|icon|preload|prefetch|modulepreload|prerender|preconnect|dns-prefetch|manifest)""", re.I)
_CODE = re.compile(rf"""(?:(?:@import\s+(?:url\(\s*)?|url\(\s*)["']?|(?:\b(?:fetch|import|importScripts)\s*\(|\.open\(\s*["']\w+["']\s*,|\.src\s*=|setAttribute\(\s*["']src["']\s*,)\s*["'`]){_URL}""", re.I)


def site_origin(url: str) -> str:
    try:  # a host or port that does not parse is its own origin, so a foreign one, named in the finding
        parsed = urlparse(f"https:{url}" if url.startswith("//") else url)
        return f"{parsed.scheme}://{parsed.hostname}{f':{parsed.port}' if parsed.port else ''}".lower()
    except ValueError:
        return url


def loads(text: str) -> list[str]:
    """Every absolute URL `text` loads: each loading attribute, and each srcset candidate, judged on its own."""
    attrs = [a for tag, a in _TAG.findall(text) if tag.lower() != "link" or _REL.search(html.unescape(a))]
    values = [c.split()[0] for a in attrs for v in _ATTR.findall(a) for c in html.unescape(v.strip("\"'")).split(",") if c.strip()]
    return _CODE.findall(html.unescape(text).replace("\\/", "/")) + [v for v in values if re.match(r"(?:https?:)?//", v)]


def findings(root: Path, origin: str, other: str = "", exempt: tuple[str, ...] = ()) -> list[str]:
    """One line per offending URL: the file, relative to `root`; `exempt` names vendored files and roots (ending /)."""
    out = []
    for path in sorted(p for p in root.rglob("*") if p.suffix.lower() in {".html", ".css", ".js", ".mjs"} and p.is_file()):
        rel, text = path.relative_to(root).as_posix(), path.read_text(encoding="utf-8", errors="replace")
        if not any(rel == e or (e.endswith("/") and rel.startswith(e)) for e in exempt):
            out += [f"{rel}: loads {u!r} from another origin (expected {origin})" for u in loads(text) if site_origin(u) != origin]
            out += [f"{rel}: links {u!r} on the other host {other}" for u in re.findall(rf"""\bhref\s*=\s*["']?{_URL}""", html.unescape(text), re.I) if other != origin and site_origin(u) == other]
    return out
