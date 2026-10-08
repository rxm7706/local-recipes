#!/usr/bin/env python3
"""Assemble one GitHub Pages artifact: Starlight + herald dossier + dashboard."""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pages_second_host import (  # noqa: E402
    SITE_URL_MARKER,
    resolve_from_process_environment,
    site_origin,
)

HERALD_PREFIX = "herald"
DASHBOARD_PREFIX = "dashboard"
ROOT_HERALD_INDEX = f"{HERALD_PREFIX}/index.html"
KEDRO_VIZ_REDIRECT = "kedro-viz/index.html"

# Vendored roots the cross-origin check does not judge (AD-21 rule 5, "re-vendor, never fork"):
# a vendored upstream bundle stays byte-identical to its recorded build, so pages-check cannot
# ask it to drop its own third-party references. Each root is named here with its reason --
# never a blanket skip -- and `check` reports every root it exempted and what it found there.
VENDORED_ROOTS: dict[str, str] = {
    f"{DASHBOARD_PREFIX}/kedro-viz/": (
        "Kedro-Viz static build, vendored from atlas viz-publish-stage "
        "via docs/dashboard/kedro-viz/"
    ),
}

_HREF_SRC = re.compile(
    r"""(?:href|src)\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
)

# Cross-origin check (Story 31.1, AD-21 amended: no runtime cross-origin call). Only what the
# browser fetches by itself when the page loads counts: stylesheets, scripts, images, media,
# frames, fonts, CSS url()/@import, resource hints (preload, prefetch, preconnect), fetch( and
# XHR. A navigation link (<a href>, <area href>) and a non-loading <link> rel (canonical,
# alternate, author, ...) passes, unless it is an absolute internal link to the other host.
_LOADING_LINK_RELS = frozenset(
    {
        "stylesheet",
        "icon",
        "apple-touch-icon",
        "apple-touch-icon-precomposed",
        "mask-icon",
        "manifest",
        "preload",
        "prefetch",
        "modulepreload",
        "prerender",
        "preconnect",
        "dns-prefetch",
    }
)
_LOADING_ATTRS: dict[str, tuple[tuple[str, str], ...]] = {
    "script": (("src", "script"),),
    "img": (("src", "image"), ("srcset", "image")),
    "input": (("src", "image"),),
    "source": (("src", "media"), ("srcset", "image")),
    "video": (("src", "media"), ("poster", "image")),
    "audio": (("src", "media"),),
    "track": (("src", "media"),),
    "iframe": (("src", "frame"),),
    "frame": (("src", "frame"),),
    "embed": (("src", "embed"),),
    "object": (("data", "embed"),),
    "image": (("href", "image"), ("xlink:href", "image")),  # SVG <image>
    "use": (("href", "image"), ("xlink:href", "image")),  # SVG <use>
}
_FONT_SUFFIXES = (".woff", ".woff2", ".ttf", ".otf", ".eot")
_CSS_REF = re.compile(
    r"""@import\s+(?:url\(\s*)?["']?((?:https?:)?//[^"')\s;]+)"""
    r"""|url\(\s*["']?((?:https?:)?//[^"')\s]+)""",
    re.IGNORECASE,
)
_FETCH_URL = re.compile(
    r"""\bfetch\s*\(\s*["'`]((?:https?:)?//[^"'`]+)["'`]""",
    re.IGNORECASE,
)
_XHR_OPEN = re.compile(
    r"""\.open\s*\(\s*["'][A-Z]+["']\s*,\s*["'`]((?:https?:)?//[^"'`]+)["'`]""",
    re.IGNORECASE,
)
_JS_SRC_SET = re.compile(
    r"""(?:\.src\s*=\s*|\bsetAttribute\(\s*["']src["']\s*,\s*)["'`]((?:https?:)?//[^"'`\s]+)""",
    re.IGNORECASE,
)
_JS_TAG_FRAGMENT = re.compile(
    r"""<(?:a|area|link|script|img|input|source|video|audio|track|iframe|frame|embed|object|image|use)\b[^<>]*>""",
    re.IGNORECASE,
)

REDIRECT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Redirect</title>
<meta http-equiv="refresh" content="0; url={target}">
<link rel="canonical" href="{target}">
</head>
<body>
<p><a href="{target}">Continue</a></p>
</body>
</html>
"""


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / "docsite" / "build.py").is_file():
            return candidate
    raise RuntimeError("could not locate repo root")


def redirect_html(target: str) -> str:
    return REDIRECT_TEMPLATE.format(target=html.escape(target, quote=True))


def _relative_url(from_file: Path, to_file: Path) -> str:
    """Relative URL from ``from_file``'s directory to ``to_file`` (POSIX)."""
    return os.path.relpath(to_file, start=from_file.parent).replace("\\", "/")


def _artifact_path(path: Path, artifact_root: Path) -> str:
    return path.relative_to(artifact_root).as_posix()


def _refuses_collision(artifact_root: Path, rel_path: str) -> None:
    target = artifact_root / rel_path
    if target.exists():
        print(f"assemble_pages: collision at {rel_path}", file=sys.stderr)
        raise SystemExit(1)


def _run_docs_site_build(repo_root: Path, site_url: str) -> None:
    env = os.environ.copy()
    env["SITE_URL"] = site_url
    subprocess.run(
        ["npm", "run", "build"],
        cwd=repo_root / "docs-site",
        env=env,
        check=True,
    )


def _write_site_url_marker(artifact_root: Path, site_url: str) -> None:
    (artifact_root / SITE_URL_MARKER).write_text(site_url.strip() + "\n", encoding="utf-8")


def _read_site_url_for_check(artifact_root: Path) -> str:
    marker = artifact_root / SITE_URL_MARKER
    if marker.is_file():
        return marker.read_text(encoding="utf-8").strip()
    return resolve_from_process_environment()


def _copy_dashboard(dashboard_src: Path, artifact_root: Path) -> None:
    dest = artifact_root / DASHBOARD_PREFIX
    mount = f"{DASHBOARD_PREFIX}/"
    _refuses_collision(artifact_root, mount)
    dest.mkdir(parents=True, exist_ok=True)
    for item in dashboard_src.iterdir():
        if item.name == "README.md":
            continue
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def _build_herald(herald_out: Path, repo_root: Path) -> None:
    herald_out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(repo_root / "docsite" / "build.py"),
        "--out",
        str(herald_out),
        "--check",
    ]
    subprocess.run(cmd, cwd=repo_root, check=True)


def _iter_herald_html(artifact_root: Path) -> list[Path]:
    herald_root = artifact_root / HERALD_PREFIX
    return sorted(p for p in herald_root.rglob("*.html") if p.is_file())


def _iter_checkable_files(artifact_root: Path) -> list[Path]:
    exts = {".html", ".css", ".js", ".mjs"}
    return sorted(
        p
        for p in artifact_root.rglob("*")
        if p.is_file() and p.suffix.lower() in exts and p.name != SITE_URL_MARKER
    )


def _old_path_for_herald_page(artifact_root: Path, herald_html: Path) -> str | None:
    rel = _artifact_path(herald_html, artifact_root)
    if rel == ROOT_HERALD_INDEX:
        return None
    if not rel.startswith(f"{HERALD_PREFIX}/"):
        raise RuntimeError(f"unexpected herald path {rel}")
    return rel.removeprefix(f"{HERALD_PREFIX}/")


def _write_dossier_redirects(artifact_root: Path) -> None:
    for herald_html in _iter_herald_html(artifact_root):
        old_rel = _old_path_for_herald_page(artifact_root, herald_html)
        if old_rel is None:
            continue
        redirect_path = artifact_root / old_rel
        _refuses_collision(artifact_root, old_rel)
        redirect_path.parent.mkdir(parents=True, exist_ok=True)
        target = _relative_url(redirect_path, herald_html)
        redirect_path.write_text(redirect_html(target), encoding="utf-8")


def _ensure_kedro_viz_redirect(artifact_root: Path) -> None:
    """Write kedro-viz redirect unless Starlight already emitted one."""
    rel = KEDRO_VIZ_REDIRECT
    path = artifact_root / rel
    if path.exists():
        return
    dashboard_index = artifact_root / DASHBOARD_PREFIX / "kedro-viz" / "index.html"
    if not dashboard_index.is_file():
        print(f"assemble_pages: missing mount {dashboard_index}", file=sys.stderr)
        raise SystemExit(1)
    path.parent.mkdir(parents=True, exist_ok=True)
    target = _relative_url(path, dashboard_index)
    path.write_text(redirect_html(target), encoding="utf-8")


def _resolve_in_artifact(base: Path, raw: str, artifact_root: Path) -> Path | None:
    raw = raw.strip().split("#", 1)[0]
    if not raw:
        return None
    if raw in ("./support.js", "support.js"):
        # Deck ``.dc.html`` exports reference an unreachable script; build.py documents this.
        return None
    if not raw or raw.startswith("#"):
        return None
    if raw.startswith(("mailto:", "tel:", "javascript:", "data:")):
        return None
    parsed = urlparse(raw)
    if parsed.scheme in ("http", "https") or parsed.netloc:  # off-site, incl. //host/...
        return None
    artifact_root = artifact_root.resolve()
    if raw.startswith("/"):
        candidate = (artifact_root / raw.lstrip("/")).resolve()
    else:
        candidate = (base.parent / raw).resolve()
    try:
        candidate.relative_to(artifact_root)
    except ValueError:
        return Path("/")  # outside artifact
    return candidate


def _should_check_page_links(rel_posix: str) -> bool:
    """Only Jinja-built navigation pages — not raw infographic or deck ``.dc.html`` exports."""
    if rel_posix == f"{HERALD_PREFIX}/artifact/dossier.html":
        return False
    if rel_posix.startswith(f"{HERALD_PREFIX}/infographics/") and not rel_posix.endswith(
        "/index.html"
    ):
        return False
    if "/decks/" in rel_posix and rel_posix.rsplit("/", 1)[-1] in (
        "infographic-deck.html",
        "executive-summary.html",
    ):
        return False
    return True


def _absolute_url(raw: str) -> str | None:
    """``raw`` as an absolute http(s) URL, or None when it is relative, ``data:`` and the like."""
    url = raw.strip()
    if url.startswith("//"):
        return f"https:{url}"
    if url.lower().startswith(("http://", "https://")):
        return url
    return None


def _origin_of(url: str) -> str:
    try:
        return site_origin(url)
    except ValueError:  # an unparseable port: never the configured origin
        return url


def _srcset_urls(value: str) -> list[str]:
    return [part.split()[0] for part in value.split(",") if part.strip()]


def _link_kind(rels: set[str], attrs: dict[str, str]) -> str:
    if "stylesheet" in rels:
        return "stylesheet"
    if rels & {"preconnect", "dns-prefetch"}:
        return "preconnect"
    if rels & {"preload", "prefetch", "modulepreload", "prerender"}:
        return "font" if attrs.get("as", "").lower() == "font" else "preload"
    if "manifest" in rels:
        return "manifest"
    return "icon"


class _ResourceScanner(HTMLParser):
    """Sort one HTML document's URLs into what the browser loads and what only links."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.loads: list[tuple[str, str]] = []  # (kind, url) the browser fetches on load
        self.links: list[str] = []  # navigation and non-loading <link> hrefs
        self.css: list[str] = []  # <style> bodies and style="" attributes
        self.js: list[str] = []  # inline <script> bodies
        self._body: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value for name, value in attrs if value is not None}
        loading = _LOADING_ATTRS.get(tag, ())
        if tag == "link":
            href = values.get("href")
            rels = set(values.get("rel", "").lower().split())
            if href and rels & _LOADING_LINK_RELS:
                self.loads.append((_link_kind(rels, values), href))
            elif href:
                self.links.append(href)
        for attr, kind in loading:
            value = values.get(attr)
            if value:
                urls = _srcset_urls(value) if attr == "srcset" else [value]
                self.loads.extend((kind, url) for url in urls)
        if tag != "link":
            loading_names = {attr for attr, _ in loading}
            for attr in ("href", "xlink:href"):
                if values.get(attr) and attr not in loading_names:
                    self.links.append(values[attr])
        if values.get("style"):
            self.css.append(values["style"])
        if tag == "style":
            self._body = "style"
        elif tag == "script" and "src" not in values:
            self._body = "script"

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._body = None

    def handle_data(self, data: str) -> None:
        if self._body == "style":
            self.css.append(data)
        elif self._body == "script":
            self.js.append(data)


def _css_loads(text: str) -> list[tuple[str, str]]:
    loads: list[tuple[str, str]] = []
    for match in _CSS_REF.finditer(text):
        imported, url = match.group(1), match.group(2)
        if imported:
            loads.append(("stylesheet", imported))
        elif url:
            path = urlparse(_absolute_url(url) or url).path.lower()
            loads.append(("font" if path.endswith(_FONT_SUFFIXES) else "css url()", url))
    return loads


def _js_scan(text: str) -> tuple[list[tuple[str, str]], list[str]]:
    text = text.replace('\\"', '"').replace("\\'", "'").replace("\\/", "/")
    loads: list[tuple[str, str]] = []
    links: list[str] = []
    loads.extend(("fetch", m.group(1)) for m in _FETCH_URL.finditer(text))
    loads.extend(("xhr", m.group(1)) for m in _XHR_OPEN.finditer(text))
    loads.extend(("dynamic src", m.group(1)) for m in _JS_SRC_SET.finditer(text))
    for match in _JS_TAG_FRAGMENT.finditer(text):  # HTML built in a JS string
        fragment = _ResourceScanner()
        fragment.feed(match.group(0))
        fragment.close()
        loads.extend(fragment.loads)
        links.extend(fragment.links)
    loads.extend(_css_loads(text))  # CSS-in-JS
    return loads, links


def _scan_file(path: Path) -> tuple[list[tuple[str, str]], list[str]]:
    """``(loads, links)`` for one artifact file: loads are ``(kind, url)`` the browser fetches."""
    text = path.read_text(encoding="utf-8", errors="replace")
    suffix = path.suffix.lower()
    if suffix == ".css":
        return _css_loads(text), []
    if suffix in (".js", ".mjs"):
        return _js_scan(text)
    scanner = _ResourceScanner()
    scanner.feed(text)
    scanner.close()
    loads = list(scanner.loads)
    links = list(scanner.links)
    for css in scanner.css:
        loads.extend(_css_loads(css))
    for js in scanner.js:
        js_loads, js_links = _js_scan(js)
        loads.extend(js_loads)
        links.extend(js_links)
    return loads, links


def _vendored_root(rel_file: str) -> str | None:
    return next((root for root in VENDORED_ROOTS if rel_file.startswith(root)), None)


def cross_origin_findings(
    artifact_root: Path, site_url: str
) -> tuple[list[str], dict[str, tuple[int, list[str]]]]:
    """Every cross-origin finding outside the vendored roots, and what each vendored root held.

    Returns ``(findings, exempt)``: ``findings`` are report lines; ``exempt`` maps each
    :data:`VENDORED_ROOTS` entry to ``(files seen, cross-origin URLs found there)``.
    """
    from pages_second_host import public_site_url

    configured_origin = site_origin(site_url)
    public_origin = site_origin(public_site_url())
    findings: list[str] = []
    exempt: dict[str, tuple[int, list[str]]] = {root: (0, []) for root in VENDORED_ROOTS}

    for path in _iter_checkable_files(artifact_root):
        rel_file = _artifact_path(path, artifact_root)
        loads, links = _scan_file(path)
        hits: list[tuple[str, str]] = []  # (url, report line)
        for kind, raw in loads:
            url = _absolute_url(raw)
            if url is not None and _origin_of(url) != configured_origin:
                where = f"{rel_file} -> {raw!r} (expected origin {configured_origin})"
                hits.append((url, f"assemble_pages: cross-origin {kind}: {where}"))
        if configured_origin != public_origin:
            for raw in links:
                url = _absolute_url(raw)
                if url is not None and _origin_of(url) == public_origin:
                    where = f"{rel_file} -> {raw!r}"
                    hits.append(
                        (url, f"assemble_pages: absolute internal link to other host: {where}")
                    )
        root = _vendored_root(rel_file)
        if root is None:
            findings.extend(line for _, line in hits)
        else:  # reported as exempt, never judged (AD-21 rule 5)
            files, urls = exempt[root]
            exempt[root] = (files + 1, urls + [url for url, _ in hits])
    return findings, exempt


def _check_cross_origin_and_hosts(artifact_root: Path, site_url: str) -> None:
    findings, exempt = cross_origin_findings(artifact_root, site_url)
    for root, (files, urls) in exempt.items():
        origins = sorted({_origin_of(url) for url in urls})
        print(
            f"assemble_pages: exempt vendored root {root} (AD-21 rule 5: {VENDORED_ROOTS[root]}): "
            f"{files} file(s) not judged, {len(urls)} cross-origin reference(s)"
            + (f" to {', '.join(origins)}" if origins else ""),
            flush=True,  # ahead of the stderr findings in a combined log
        )
    for line in findings:
        print(line, file=sys.stderr)
    if findings:
        print(f"assemble_pages: {len(findings)} cross-origin finding(s)", file=sys.stderr)
        raise SystemExit(1)


def _check_href_resolution(artifact_root: Path) -> None:
    for page in _iter_herald_html(artifact_root):
        rel_page = _artifact_path(page, artifact_root)
        if not _should_check_page_links(rel_page):
            continue
        text = page.read_text(encoding="utf-8", errors="replace")
        for match in _HREF_SRC.finditer(text):
            raw = match.group(1)
            resolved = _resolve_in_artifact(page, raw, artifact_root)
            if resolved is None:
                continue
            if resolved == Path("/"):
                rel_page = _artifact_path(page, artifact_root)
                print(
                    f"assemble_pages: link escapes artifact: {rel_page} -> {raw!r}",
                    file=sys.stderr,
                )
                raise SystemExit(1)
            if raw.endswith("/"):
                if not resolved.is_dir() and not (resolved / "index.html").is_file():
                    rel_page = _artifact_path(page, artifact_root)
                    print(
                        f"assemble_pages: broken directory link: {rel_page} -> {raw!r}",
                        file=sys.stderr,
                    )
                    raise SystemExit(1)
            elif not resolved.is_file():
                rel_page = _artifact_path(page, artifact_root)
                print(
                    f"assemble_pages: broken link: {rel_page} -> {raw!r}",
                    file=sys.stderr,
                )
                raise SystemExit(1)


def _required_paths() -> list[str]:
    return [
        "index.html",
        "404.html",
        ROOT_HERALD_INDEX,
        f"{HERALD_PREFIX}/dossier/index.html",
        f"{DASHBOARD_PREFIX}/kedro-viz/index.html",
        KEDRO_VIZ_REDIRECT,
    ]


def check(artifact_root: Path, *, site_url: str | None = None) -> None:
    site_url = site_url or _read_site_url_for_check(artifact_root)
    for rel in _required_paths():
        if not (artifact_root / rel).is_file():
            print(f"assemble_pages: missing required path {rel}", file=sys.stderr)
            raise SystemExit(1)

    herald_htmls = _iter_herald_html(artifact_root)
    for herald_html in herald_htmls:
        old_rel = _old_path_for_herald_page(artifact_root, herald_html)
        if old_rel is None:
            continue
        redirect_file = artifact_root / old_rel
        if not redirect_file.is_file():
            print(
                f"assemble_pages: missing redirect for herald page "
                f"{_artifact_path(herald_html, artifact_root)} at {old_rel}",
                file=sys.stderr,
            )
            raise SystemExit(1)

    _check_href_resolution(artifact_root)
    _check_cross_origin_and_hosts(artifact_root, site_url)


def assemble(
    artifact_root: Path,
    *,
    repo_root: Path | None = None,
    dashboard_src: Path | None = None,
    skip_herald_build: bool = False,
    skip_docs_site_build: bool = False,
    site_url: str | None = None,
) -> str:
    repo_root = repo_root or _repo_root()
    dashboard_src = dashboard_src or (repo_root / "docs" / "dashboard")
    artifact_root = artifact_root.resolve()
    herald_out = artifact_root / HERALD_PREFIX
    site_url = site_url or resolve_from_process_environment()

    if not skip_docs_site_build:
        _run_docs_site_build(repo_root, site_url)
    _write_site_url_marker(artifact_root, site_url)

    for mount in (f"{HERALD_PREFIX}/", f"{DASHBOARD_PREFIX}/"):
        existing = artifact_root / mount.rstrip("/")
        if existing.exists():
            print(f"assemble_pages: collision at {mount}", file=sys.stderr)
            raise SystemExit(1)

    if not skip_herald_build:
        _build_herald(herald_out, repo_root)
    _copy_dashboard(dashboard_src, artifact_root)
    _write_dossier_redirects(artifact_root)
    _ensure_kedro_viz_redirect(artifact_root)
    return site_url


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path("docs-site/build/site"),
        help="Unified Pages artifact directory (default: docs-site/build/site)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the artifact without rebuilding",
    )
    parser.add_argument(
        "--skip-herald-build",
        action="store_true",
        help="Skip docsite/build.py (tests only)",
    )
    parser.add_argument(
        "--skip-docs-site-build",
        action="store_true",
        help="Skip Starlight npm build (tests only)",
    )
    args = parser.parse_args(argv)
    repo_root = _repo_root()
    artifact_root = (repo_root / args.artifact_root).resolve()

    if args.check:
        check(artifact_root)
        return

    site_url = assemble(
        artifact_root,
        repo_root=repo_root,
        skip_herald_build=args.skip_herald_build,
        skip_docs_site_build=args.skip_docs_site_build,
    )
    check(artifact_root, site_url=site_url)


if __name__ == "__main__":
    main()
