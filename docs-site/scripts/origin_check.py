"""Nothing loads from another origin (Story 43.3; AD-21, CAP-56): every URL a loading tag's src, srcset candidate,
poster, data or SVG href, a loading <link>, or a url(), @import, fetch, XHR, import() or .src= in a script, a style or
a .css/.js file names is on `origin`; no href names `other`, the public host. Text and code samples load nothing."""

import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

_URL = r"""((?:https?:)?//[^\s"'`)<>,;]+)"""
_CODE = re.compile(r"""(?:(?:@import\s+(?:url\(\s*)?|url\(\s*)["']?|(?:\b(?:fetch|import|importScripts)\s*\("""
                   rf"""|\.src\s*=|\.open\(\s*["']\w+["']\s*,|setAttribute\(\s*["']src["']\s*,)\s*["'`]){_URL}""", re.I)
_REL = re.compile(r"\b(?:stylesheet|icon|preload|prefetch|modulepreload|prerender|preconnect|dns-prefetch|manifest)\b")
_LOADS = "link script img iframe frame source video audio track embed input object image use".split()
_KEYS = ("src", "srcset", "poster", "data", "href", "xlink:href")


class _Page(HTMLParser):
    """A page's loading URLs and hrefs (attribute values arrive entity-decoded) and the code it runs: its script and
    style bodies (raw, as a browser reads them) and style attributes -- never its text: a code sample loads nothing."""

    def __init__(self, text: str) -> None:
        super().__init__(convert_charrefs=True)
        self.urls, self.hrefs, self.code, self.body = [], [], [], False
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        self.hrefs.append(a.get("href", ""))
        self.code.append(a.get("style", ""))
        self.body = tag in ("script", "style")
        if tag in _LOADS and (tag != "link" or _REL.search(a.get("rel", "").lower())):
            self.urls += [c.split()[0] for k in _KEYS for c in a.get(k, "").split(",") if c.strip()]

    def handle_endtag(self, tag: str) -> None:
        self.body = False

    def handle_data(self, data: str) -> None:
        self.code += [data] if self.body else []


def site_origin(url: str) -> str:
    try:  # a host or port that does not parse is its own origin, so a foreign one, named in the finding
        parsed = urlparse(f"https:{url}" if url.startswith("//") else url)
        return f"{parsed.scheme}://{parsed.hostname}{f':{parsed.port}' if parsed.port else ''}".lower()
    except ValueError:
        return url


def findings(root: Path, origin: str, other: str = "", exempt: tuple[str, ...] = ()) -> list[str]:
    """One line per offending URL: the file, relative to `root`; `exempt` names vendored files and roots (ending /)."""
    out = []
    for path in sorted(p for p in root.rglob("*") if p.suffix.lower() in {".html", ".css", ".js", ".mjs"}):
        rel = path.relative_to(root).as_posix()
        if not path.is_file() or any(rel == e or (e.endswith("/") and rel.startswith(e)) for e in exempt):
            continue
        text, html = path.read_text(encoding="utf-8", errors="replace"), path.suffix.lower() == ".html"
        page = _Page(text if html else "")
        code = "\n".join(page.code) if html else text
        urls = [u for u in page.urls if re.match(r"(?:https?:)?//", u)] + _CODE.findall(code.replace("\\/", "/"))
        out += [f"{rel}: loads {u!r} from another origin (expected {origin})" for u in urls if site_origin(u) != origin]
        hosts = [u for u in page.hrefs if u and other != origin and site_origin(u) == other]
        out += [f"{rel}: links {u!r} on the other host {other}" for u in hosts]
    return out


if __name__ == "__main__":  # pages-check (scripts/pages.mts): ROOT ORIGIN OTHER [EXEMPT ...]; exit 1 naming each finding
    import sys

    found = findings(Path(sys.argv[1]), sys.argv[2], sys.argv[3], tuple(sys.argv[4:]))
    for line in found:
        print(line, file=sys.stderr)
    sys.exit(1 if found else 0)
