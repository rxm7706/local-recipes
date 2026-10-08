"""HTML twin zero-origin scan, React bundle build, and publish helpers (CAP-55 D5)."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from pyforge.core.errors import PyforgeError

from . import deck_versions

DECK_VIEWER_FLAG = "pyforge.herald.deck_viewer"

_EXTERNAL_SCHEME = re.compile(r"^https?:", re.I)
_A_NAV_HREF = re.compile(
    r"<a\b[^>]*\shref=(['\"])(https?://[^'\"]+)\1",
    re.I | re.DOTALL,
)
_URL_IN_CSS = re.compile(
    r"url\(\s*(['\"]?)(https?://[^)'\"]+)\1\s*\)",
    re.I,
)
_IMPORT_URL = re.compile(
    r"@import\s+url\(\s*(['\"]?)(https?://[^)'\"]+)\1\s*\)",
    re.I,
)
_SRC_HREF = re.compile(
    r"\b(?:src|href)=(['\"])(https?://[^'\"]+)\1",
    re.I,
)
_TWEMOJI_IMG = re.compile(
    r'<img\b[^>]*\bclass="emoji"[^>]*/?>',
    re.I,
)
_TWEMOJI_ALT = re.compile(r'\balt="([^"]*)"', re.I)
_GOOGLE_FONTS_IMPORT = re.compile(
    r"@import\s+url\(['\"]https://fonts\.googleapis\.com/[^'\"]+['\"]\)\s*;?",
    re.I,
)


@dataclass(frozen=True, slots=True)
class OriginFinding:
    """One reference to another origin inside a twin file."""

    path: Path
    origin: str
    reference: str


class TwinOriginError(PyforgeError, Exception):
    """Publish refused because a twin names another origin (D5)."""

    def __init__(self, finding: OriginFinding) -> None:
        self.finding = finding
        rel = finding.path.name
        super().__init__(f"{rel}: external origin {finding.origin!r} in {finding.reference!r}")


def _navigation_hrefs(text: str) -> set[str]:
    return {match.group(2) for match in _A_NAV_HREF.finditer(text)}


def _origin_of(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return ""
    return parsed.netloc.lower()


def scan_text(text: str, path: Path) -> list[OriginFinding]:
    """Return every external-origin reference that is not plain ``<a href>`` navigation."""
    allowed = _navigation_hrefs(text)
    findings: list[OriginFinding] = []
    seen: set[tuple[str, str, str]] = set()

    def record(url: str, reference: str) -> None:
        if not _EXTERNAL_SCHEME.match(url):
            return
        if url in allowed:
            return
        origin = _origin_of(url)
        if not origin:
            return
        key = (str(path), origin, url)
        if key in seen:
            return
        seen.add(key)
        findings.append(OriginFinding(path=path, origin=origin, reference=reference))

    for match in _IMPORT_URL.finditer(text):
        record(match.group(2), match.group(0))
    for match in _URL_IN_CSS.finditer(text):
        record(match.group(2), match.group(0))
    for match in _SRC_HREF.finditer(text):
        record(match.group(2), match.group(0))

    return findings


def scan_file(path: Path) -> list[OriginFinding]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return scan_text(text, path)


def scan_tree(root: Path) -> list[OriginFinding]:
    if not root.is_dir():
        return scan_file(root)
    out: list[OriginFinding] = []
    for file in sorted(root.rglob("*")):
        if not file.is_file():
            continue
        if file.suffix.lower() not in {".html", ".css", ".js", ".svg"}:
            continue
        out.extend(scan_file(file))
    return out


def _twemoji_to_alt(match: re.Match[str]) -> str:
    tag = match.group(0)
    alt = _TWEMOJI_ALT.search(tag)
    return alt.group(1) if alt else ""


def vendor_standalone_html(path: Path) -> None:
    """Post-process a Marp standalone export: drop CDN twemoji and Google Fonts imports."""
    text = path.read_text(encoding="utf-8", errors="replace")
    text = _TWEMOJI_IMG.sub(_twemoji_to_alt, text)
    text = _GOOGLE_FONTS_IMPORT.sub("", text)
    text = re.sub(
        r'<link[^>]+href="https://fonts\.googleapis\.com/[^"]+"[^>]*/?>',
        "",
        text,
        flags=re.I,
    )
    text = re.sub(
        r'<link[^>]+href="https://fonts\.gstatic\.com/[^"]+"[^>]*/?>',
        "",
        text,
        flags=re.I,
    )
    path.write_text(text, encoding="utf-8")


def current_standalone_twin(repo_root: Path, slug: str) -> Path | None:
    presentations = repo_root / "presentations"
    for export in deck_versions.current_exports(repo_root, slug):
        if export.suffix.lower() != ".html":
            continue
        if "infographic-standalone" not in export.name:
            continue
        return export
    deck_dir = presentations / slug
    if not deck_dir.is_dir():
        return None
    marp_dir = deck_dir / "src" / "marp"
    if not marp_dir.is_dir():
        return None
    candidates = sorted(marp_dir.glob(f"{slug}-infographic-standalone-*.html"))
    return candidates[-1] if candidates else None


def react_deck_dir(repo_root: Path, slug: str) -> Path | None:
    deck_dir = repo_root / "presentations" / slug
    if (deck_dir / "package.json").is_file():
        return deck_dir
    return None


def build_react_bundle(deck_dir: Path) -> Path:
    dist = deck_dir / "dist"
    npm = _which("npm")
    if npm is None:
        msg = f"npm not on PATH — cannot build {deck_dir.name} bundle"
        raise RuntimeError(msg)
    subprocess.run([npm, "ci"], cwd=deck_dir, check=True, capture_output=True, text=True)
    subprocess.run(
        [npm, "run", "build"],
        cwd=deck_dir,
        check=True,
        capture_output=True,
        text=True,
    )
    if not dist.is_dir():
        msg = f"{dist} missing after vite build"
        raise RuntimeError(msg)
    return dist


def _which(name: str) -> str | None:
    from shutil import which

    return which(name)


def iter_react_deck_index_files(repo_root: Path) -> list[Path]:
    presentations = repo_root / "presentations"
    if not presentations.is_dir():
        return []
    out: list[Path] = []
    for deck_dir in sorted(presentations.iterdir()):
        if not deck_dir.is_dir():
            continue
        index = deck_dir / "index.html"
        pkg = deck_dir / "package.json"
        if index.is_file() and pkg.is_file():
            out.append(index)
    return out


def iter_standalone_twin_files(repo_root: Path) -> list[Path]:
    presentations = repo_root / "presentations"
    if not presentations.is_dir():
        return []
    out: list[Path] = []
    for path in sorted(presentations.glob("*/src/marp/*-infographic-standalone-*.html")):
        if path.is_file():
            out.append(path)
    return out


def bundle_manifest_paths(dist_dir: Path) -> dict[str, Path]:
    """Relative path within ``dist/`` -> absolute file path."""
    mapping: dict[str, Path] = {}
    for file in sorted(dist_dir.rglob("*")):
        if not file.is_file():
            continue
        rel = file.relative_to(dist_dir).as_posix()
        mapping[rel] = file
    return mapping
