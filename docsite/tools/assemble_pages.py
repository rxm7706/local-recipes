#!/usr/bin/env python3
"""Assemble one GitHub Pages artifact: Starlight + herald dossier + dashboard.

Story 42.2 (CAP-60): the Kedro-Viz mount is an artifact handoff that tolerates absence. Its one
build input is ``docs/dashboard/kedro-viz/`` (atlas's ``kedro-viz-export`` workflow artifact, or a
local ``viz-publish-stage``; ``kedro_viz_export.py``). Present, it is mounted verbatim at
``/dashboard/kedro-viz/`` with the ``/kedro-viz/`` redirect and herald's pipelines page at
``/dashboard/index.html``; absent, none of the three is written, the shared menu and the overview
tiles drop Kedro-Viz, and ``check`` refuses any page that still links either path.

Story 42.1 (CAP-60): ``/status/`` is herald's second prefix, mounted beside ``/herald/`` under the
same collision rule. With ``pyforge.herald.status_pages`` on (``PYFORGE_STATUS_PAGES``) the build input
``docsite/content/fleet-status.json`` is validated before anything is mounted (a missing or malformed
input exits 1 naming the file), herald writes the fleet board and the guild status page under
``status/``, and the shared menu carries Status. Off, the input is never opened, no ``status/`` path
may exist, and the menus are as before (``status_pages.py``)."""

from __future__ import annotations

import argparse
import html
import os
import posixpath
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kedro_viz_export as kv  # noqa: E402
import status_pages as sp  # noqa: E402
from pages_one_generator import DOSSIER_ARTIFACT_REL, enabled_from_env  # noqa: E402
from pages_site_url import (  # noqa: E402
    SITE_URL_MARKER,
    resolve_from_process_environment,
    site_origin,
)

HERALD_PREFIX = "herald"
DASHBOARD_PREFIX = "dashboard"
ROOT_HERALD_INDEX = f"{HERALD_PREFIX}/index.html"
KEDRO_VIZ_MOUNT = kv.MOUNT_REL
KEDRO_VIZ_REDIRECT = "kedro-viz/index.html"
#: Herald's pipelines page in front of the mount (Story 42.2); written only with the export.
PIPELINES_PAGE = f"{DASHBOARD_PREFIX}/index.html"
#: Herald's status pages (Story 42.1); written only with pyforge.herald.status_pages on.
STATUS_PREFIX = sp.STATUS_PREFIX
STATUS_PAGES = (sp.BOARD_PAGE, sp.GUILD_PAGE)

# Vendored roots the cross-origin check does not judge (AD-21 rule 5, "re-vendor, never fork"):
# a vendored upstream bundle stays byte-identical to its recorded build, so pages-check cannot
# ask it to drop its own third-party references. Each root is named here with its reason --
# never a blanket skip -- and `check` reports every root it exempted and what it found there.
VENDORED_ROOTS: dict[str, str] = {
    f"{KEDRO_VIZ_MOUNT}/": (
        "Kedro-Viz static build: atlas's kedro-viz-export artifact (viz-publish-stage), "
        "mounted verbatim from docs/dashboard/kedro-viz/"
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
    if enabled_from_env():
        env.setdefault("PYFORGE_PAGES_ONE_GENERATOR", "1")
    else:
        env["PYFORGE_PAGES_ONE_GENERATOR"] = "0"
    subprocess.run(
        ["npm", "run", "build"],
        cwd=repo_root / "docs-site",
        env=env,
        check=True,
    )


def _astro_dossier_preexists(artifact_root: Path) -> bool:
    path = artifact_root / DOSSIER_ARTIFACT_REL
    return path.is_file() and path.stat().st_size > 0


def _remove_empty_astro_dossier(artifact_root: Path) -> None:
    """Drop Astro's zero-byte dossier stub when the one-generator flag is off."""
    dossier_dir = artifact_root / HERALD_PREFIX / "dossier"
    if not dossier_dir.is_dir():
        return
    index = dossier_dir / "index.html"
    if index.is_file() and index.stat().st_size == 0:
        shutil.rmtree(dossier_dir)
    herald = artifact_root / HERALD_PREFIX
    if herald.is_dir() and not any(herald.iterdir()):
        herald.rmdir()


def _write_site_url_marker(artifact_root: Path, site_url: str) -> None:
    (artifact_root / SITE_URL_MARKER).write_text(site_url.strip() + "\n", encoding="utf-8")


def _read_site_url_for_check(artifact_root: Path) -> str:
    marker = artifact_root / SITE_URL_MARKER
    if marker.is_file():
        return marker.read_text(encoding="utf-8").strip()
    return resolve_from_process_environment()


def _input_label(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _copy_dashboard(dashboard_src: Path, artifact_root: Path, *, repo_root: Path | None = None) -> bool:
    """Copy ``dashboard_src`` (minus its README) under ``dashboard/``; True when Kedro-Viz was mounted.

    The Kedro-Viz input is validated first: a present export whose ``index.html`` or
    ``manifest.json`` is missing or malformed exits 1 naming the input path; an absent (missing or
    empty) one is skipped, and nothing is written for it (Story 42.2)."""
    dest = artifact_root / DASHBOARD_PREFIX
    _refuses_collision(artifact_root, f"{DASHBOARD_PREFIX}/")
    export_dir = dashboard_src / "kedro-viz"
    label = _input_label(export_dir, repo_root) if repo_root is not None else str(export_dir)
    try:
        export = kv.load(export_dir, label=label)
    except kv.ExportShapeError as exc:
        print(f"assemble_pages: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    items = [
        item
        for item in (sorted(dashboard_src.iterdir()) if dashboard_src.is_dir() else [])
        if item.name != "README.md" and not (item == export_dir and export is None)
    ]
    for item in items:
        target = dest / item.name
        dest.mkdir(parents=True, exist_ok=True)
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)
    if export is None:
        print(f"assemble_pages: no Kedro-Viz export at {label}: mount, redirect and menu entry skipped", flush=True)
    else:
        print(f"assemble_pages: Kedro-Viz export {export['commit'][:12]} ({export['date']}) mounted", flush=True)
    return export is not None


def _build_herald(
    herald_out: Path,
    repo_root: Path,
    *,
    kedro_viz_export: Path | None = None,
    dashboard_out: Path | None = None,
    status_out: Path | None = None,
    fleet_status: Path | None = None,
) -> None:
    herald_out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(repo_root / "docsite" / "build.py"),
        "--out",
        str(herald_out),
        "--check",
    ]
    if kedro_viz_export is not None:
        cmd += ["--kedro-viz-export", str(kedro_viz_export)]
    if dashboard_out is not None:
        cmd += ["--dashboard-out", str(dashboard_out)]
    if status_out is not None:
        cmd += ["--status-out", str(status_out)]
    if fleet_status is not None:
        cmd += ["--fleet-status", str(fleet_status)]
    subprocess.run(cmd, cwd=repo_root, check=True)


def _iter_herald_html(artifact_root: Path) -> list[Path]:
    herald_root = artifact_root / HERALD_PREFIX
    return sorted(p for p in herald_root.rglob("*.html") if p.is_file())


def _iter_herald_rendered_html(artifact_root: Path) -> list[Path]:
    """Herald's pages under ``/herald/``, plus the pipelines page it renders under ``/dashboard/``
    and the status pages under ``/status/`` (Story 42.1)."""
    others = [artifact_root / rel for rel in (PIPELINES_PAGE, *STATUS_PAGES)]
    return [*_iter_herald_html(artifact_root), *(page for page in others if page.is_file())]


def _lane1_href() -> str | None:
    """The Lane 1 live-view link the status pages carry, or ``None`` when they carry none: the
    status pages link ``site.yml``'s ``lane1.href`` only when it is an absolute URL
    (``status_pages.lane1_link``). Lane 1 is served by the platform, not by Pages, so that one link
    is never resolved inside the artifact; a root-absolute ``/console/`` on a status page is not
    exempt and fails as a broken link (herald 42.1 re-review)."""
    import yaml  # the ``site`` env carries PyYAML (docsite/build.py reads the same file)

    data = yaml.safe_load((_repo_root() / "docsite" / "content" / "site.yml").read_text(encoding="utf-8"))
    link = sp.lane1_link(data.get("lane1"))
    return link["href"] if link else None


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
    """Write the ``/kedro-viz/`` redirect from the mount's presence, unless Starlight already emitted one.

    No mount, no redirect (Story 42.2): ``check`` refuses a ``kedro-viz/`` path without the mount."""
    rel = KEDRO_VIZ_REDIRECT
    path = artifact_root / rel
    if path.exists():
        return
    dashboard_index = artifact_root / KEDRO_VIZ_MOUNT / "index.html"
    if not dashboard_index.is_file():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    target = _relative_url(path, dashboard_index)
    path.write_text(redirect_html(target), encoding="utf-8")


def _normalize_internal_absolute(raw: str, base_path: str) -> str:
    """Strip the publish base path from root-absolute hrefs (Astro Starlight assets)."""
    if not raw.startswith("/"):
        return raw
    prefix = (base_path or "/").rstrip("/")
    if prefix and prefix != "" and raw.startswith(f"{prefix}/"):
        return raw[len(prefix) :]
    return raw


def _resolve_in_artifact(
    base: Path, raw: str, artifact_root: Path, *, base_path: str = "/"
) -> Path | None:
    raw = raw.strip().split("#", 1)[0]
    raw = _normalize_internal_absolute(raw, base_path)
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
    from pages_site_url import public_site_url

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


def _check_href_resolution(artifact_root: Path, *, site_url: str) -> None:
    base_path = _base_path(site_url)
    lane1 = _lane1_href()
    for page in _iter_herald_rendered_html(artifact_root):
        rel_page = _artifact_path(page, artifact_root)
        if not _should_check_page_links(rel_page):
            continue
        text = page.read_text(encoding="utf-8", errors="replace")
        for match in _HREF_SRC.finditer(text):
            raw = match.group(1)
            if lane1 is not None and raw == lane1:  # the live view on Lane 1 (Story 42.1): another host
                continue
            resolved = _resolve_in_artifact(page, raw, artifact_root, base_path=base_path)
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



#: The Starlight container that holds a shelf page's rendered markdown (docs-site, CAP-52).
_SHELF_CONTAINER = "sl-markdown-content"
#: Elements in a shelf body whose URL the browser follows or loads.
_SHELF_URL_ATTRS = {"a": "href", "img": "src", "source": "src", "video": "src", "audio": "src", "iframe": "src"}


class _ShelfBody(HTMLParser):
    """Exactly the markdown container of one shelf page: its words and the URLs inside it. Depth is
    tracked on ``div`` so the page's footer (Starlight's Previous/Next links) is never counted as body
    (Story 44.1 review)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found = False
        self.depth = 0
        self.words: list[str] = []
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value for name, value in attrs if value is not None}
        if self.depth:
            if tag == "div":
                self.depth += 1
            attr = _SHELF_URL_ATTRS.get(tag)
            if attr and values.get(attr):
                self.urls.append(values[attr])
            return
        if not self.found and tag == "div" and _SHELF_CONTAINER in values.get("class", "").split():
            self.found = True
            self.depth = 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag == "div" and self.depth > 1:
            self.depth -= 1

    def handle_endtag(self, tag: str) -> None:
        if self.depth and tag == "div":
            self.depth -= 1

    def handle_data(self, data: str) -> None:
        if self.depth:
            self.words.extend(data.split())


def _iter_shelf_pages(artifact_root: Path) -> list[Path]:
    """Every Starlight shelf page: the HTML outside the herald and dashboard mounts that carries
    a markdown body container (legacy redirect stubs have none)."""
    pages = []
    for page in sorted(artifact_root.rglob("*.html")):
        rel = _artifact_path(page, artifact_root)
        if rel.startswith((f"{HERALD_PREFIX}/", f"{DASHBOARD_PREFIX}/", f"{STATUS_PREFIX}/")):
            continue
        if _SHELF_CONTAINER in page.read_text(encoding="utf-8", errors="replace"):
            pages.append(page)
    return pages


def _shelf_failure(message: str) -> None:
    print(f"assemble_pages: {message}", file=sys.stderr)
    raise SystemExit(1)


def _check_shelf_pages(artifact_root: Path, site_url: str) -> None:
    """Each shelf page renders a non-empty body, and every local URL in that body resolves to a file
    inside the artifact (Story 44.1: until 2026-10-14 every shelf body rendered empty, and no check
    looked at shelf links). The 404 page is served at any missing path, so its links must be
    absolute."""
    base_path = _base_path(site_url)
    root = artifact_root.resolve()
    pages = _iter_shelf_pages(artifact_root)
    if not pages:
        _shelf_failure("no shelf page found")
    for page in pages:
        rel_page = _artifact_path(page, artifact_root)
        body = _ShelfBody()
        body.feed(page.read_text(encoding="utf-8", errors="replace"))
        body.close()
        if not body.found or not body.words:
            _shelf_failure(f"empty shelf page body: {rel_page}")
        for raw in body.urls:
            url = raw.split("#", 1)[0].split("?", 1)[0]
            if not url or urlparse(url).scheme or url.startswith(("//", "mailto:", "tel:")):
                continue
            path = unquote(url)
            if path.startswith("/"):
                if not path.startswith(base_path):
                    _shelf_failure(f"shelf link outside the base path: {rel_page} -> {raw!r} (base {base_path})")
                target = root / path[len(base_path) :]
            elif rel_page == "404.html":
                _shelf_failure(f"relative link on the 404 page (served at any path): {rel_page} -> {raw!r}")
            else:
                target = page.parent.resolve() / path
            target = target.resolve()
            if target != root and root not in target.parents:
                _shelf_failure(f"shelf link escapes the artifact: {rel_page} -> {raw!r}")
            if not (target.is_file() or (target / "index.html").is_file()):
                _shelf_failure(f"broken shelf link: {rel_page} -> {raw!r}")

#: A menu link carries this attribute: the docs top menu (docs-site/src/components/SiteTitle.astro)
#: and the herald shell (docsite/templates/shell_page.html.j2). Story 40.1, CAP-58.
_MENU_LINK = re.compile(
    r"""<a\b(?=[^>]*\bdata-pf-menu-link\b)[^>]*\bhref\s*=\s*["']([^"']*)["'][^>]*>\s*([^<]*?)\s*</a>""",
    re.IGNORECASE,
)


def _base_path(site_url: str) -> str:
    path = urlparse(site_url).path or "/"
    return path if path.endswith("/") else f"{path}/"


def _expected_menu(*, kedro_viz: bool = True, status_pages: bool | None = None) -> list[tuple[str, str]]:
    """herald's one navigation list, ``docsite/content/site.yml``: (label, href) in menu order.

    ``kedro_viz=False`` drops the entries that need the Kedro-Viz mount (Story 42.2); ``status_pages``
    (default: ``PYFORGE_STATUS_PAGES``) keeps or drops the flag-gated Status entry (Story 42.1)."""
    import yaml  # the ``site`` env carries PyYAML (docsite/build.py reads the same file)

    data = yaml.safe_load((_repo_root() / "docsite" / "content" / "site.yml").read_text(encoding="utf-8"))
    enabled = sp.enabled_from_env() if status_pages is None else status_pages
    gated = sp.menu_entries([*data["nav"], *(data.get("neighbours") or [])], enabled=enabled)
    entries = kv.menu_entries(gated, present=kedro_viz)
    return [(item["label"], item["href"]) for item in entries]


def _menu_target(page: Path, raw: str, artifact_root: Path, base_path: str) -> Path | None:
    """Where a menu href lands inside the artifact; ``None`` when it does not.

    A docs page's hrefs carry the host's base path (``/local-recipes/herald/``); a herald page's
    are relative. Either way the target must be a file, or a directory with an ``index.html``. An
    empty or fragment-only href points at nothing and is refused."""
    href = raw.strip().split("#", 1)[0]
    if not href or urlparse(href).scheme or href.startswith("//"):
        return None
    if href.startswith("/"):
        if not href.startswith(base_path):
            return None
        candidate = (artifact_root / href[len(base_path) :]).resolve()
    else:
        candidate = (page.parent / href).resolve()
    try:
        candidate.relative_to(artifact_root.resolve())
    except ValueError:
        return None
    if candidate.is_file():
        return candidate
    if (candidate / "index.html").is_file():
        return candidate / "index.html"
    return None


def _carries_the_menu(rel_page: str, text: str) -> bool:
    """Every navigable page carries the shared menu: all docs pages and herald's shell pages.

    Not the Kedro-Viz export, not a redirect stub, and not a raw infographic or deck export
    (the pages ``_should_check_page_links`` already leaves out). Herald's pipelines page under
    ``/dashboard/`` is a shell page and carries it (Story 42.2)."""
    if rel_page.startswith(f"{DASHBOARD_PREFIX}/") and rel_page != PIPELINES_PAGE:
        return False
    if 'http-equiv="refresh"' in text:
        return False
    return not (rel_page.startswith(f"{HERALD_PREFIX}/") and not _should_check_page_links(rel_page))


def _menu_failure(message: str) -> None:
    print(f"assemble_pages: {message}", file=sys.stderr)
    raise SystemExit(1)


def _check_menu_links(artifact_root: Path, site_url: str, expected: list[tuple[str, str]] | None = None) -> None:
    """The shared menu (FR-8.6) on every navigable page, exactly as site.yml lists it.

    Each page that should carry it shows every label in order, each href resolves inside the
    artifact under the host's base path, and the docs root links every herald target twice: once
    in the top menu and once in its Herald sidebar group."""
    expected = expected if expected is not None else _expected_menu()
    labels = [label for label, _ in expected]
    base_path = _base_path(site_url)
    for page in sorted(artifact_root.rglob("*.html")):
        rel_page = _artifact_path(page, artifact_root)
        text = page.read_text(encoding="utf-8", errors="replace")
        if not _carries_the_menu(rel_page, text):
            continue
        found = _MENU_LINK.findall(text)
        if [label for _, label in found] != labels:
            _menu_failure(f"shared menu on {rel_page} reads {[label for _, label in found]}, expected {labels}")
        for raw, _ in found:
            if _menu_target(page, raw, artifact_root, base_path) is None:
                _menu_failure(f"menu link does not resolve: {rel_page} -> {raw!r} (base {base_path})")
    root_text = (artifact_root / "index.html").read_text(encoding="utf-8", errors="replace")
    for raw, label in _MENU_LINK.findall(root_text)[1:]:
        if root_text.count(f'href="{raw}"') < 2:
            _menu_failure(f"docs root has no Herald sidebar link for {label} ({raw!r})")


def _required_paths(*, kedro_viz: bool = True, status_pages: bool = False) -> list[str]:
    """The artifact's required files; the Kedro-Viz three only when the export is mounted, the two
    status pages only with pyforge.herald.status_pages on."""
    paths = [
        "index.html",
        "404.html",
        ROOT_HERALD_INDEX,
        f"{HERALD_PREFIX}/dossier/index.html",
    ]
    if kedro_viz:
        paths += [f"{KEDRO_VIZ_MOUNT}/index.html", KEDRO_VIZ_REDIRECT, PIPELINES_PAGE]
    if status_pages:
        paths += list(STATUS_PAGES)
    return paths


def _fleet_status_input(repo_root: Path) -> Path:
    return repo_root / sp.INPUT_REL


def _check_fleet_status_input(fleet_status: Path, repo_root: Path) -> None:
    """The shape check (Story 42.1 AC5): with the flag on, the build input must load; exit 1 naming it."""
    try:
        sp.load_fleet_status(fleet_status)
    except sp.FleetStatusShapeError as exc:
        label = _input_label(fleet_status, repo_root)
        message = str(exc)
        if message.startswith(str(fleet_status)):
            message = label + message[len(str(fleet_status)) :]
        print(f"assemble_pages: {message}", file=sys.stderr)
        raise SystemExit(1) from exc


def _check_status_menu_entry(expected: list[tuple[str, str]]) -> None:
    """With the flag on, the shared menu links the fleet board (Story 42.1 AC6): a site.yml nav that
    lost its Status entry would otherwise build seven pages' worth of consistent, Status-less menus."""
    board = sp.BOARD_PAGE
    for _, href in expected:
        target = posixpath.normpath(posixpath.join(HERALD_PREFIX, href.split("#", 1)[0]))
        if target in (board, posixpath.dirname(board)):
            return
    _menu_failure(f"pyforge.herald.status_pages is on but the shared menu has no entry linking {board} (site.yml nav)")


def _check_no_status_paths(artifact_root: Path) -> None:
    """With pyforge.herald.status_pages off no ``status/`` path exists in the artifact (Story 42.1 AC7)."""
    if (artifact_root / STATUS_PREFIX).exists():
        print(
            f"assemble_pages: {STATUS_PREFIX}/ exists in the artifact but pyforge.herald.status_pages is off",
            file=sys.stderr,
        )
        raise SystemExit(1)


def _kedro_viz_path(rel: str) -> bool:
    return rel in (KEDRO_VIZ_MOUNT, "kedro-viz") or rel.startswith((f"{KEDRO_VIZ_MOUNT}/", "kedro-viz/"))


def _check_no_kedro_viz_paths(artifact_root: Path, site_url: str) -> None:
    """With no export mounted, no ``/kedro-viz/`` path exists and no page links it or the mount.

    The link walk reads every ``href``/``src`` of every HTML page in the artifact (Story 42.2 AC2)."""
    if (artifact_root / "kedro-viz").exists():
        print(
            "assemble_pages: kedro-viz/ exists in the artifact but no Kedro-Viz export is mounted "
            f"at {KEDRO_VIZ_MOUNT}/",
            file=sys.stderr,
        )
        raise SystemExit(1)
    base_path = _base_path(site_url)
    root = artifact_root.resolve()
    for page in sorted(artifact_root.rglob("*.html")):
        text = page.read_text(encoding="utf-8", errors="replace")
        for match in _HREF_SRC.finditer(text):
            raw = match.group(1)
            target = _resolve_in_artifact(page, raw, artifact_root, base_path=base_path)
            if target is None or target == Path("/"):
                continue
            rel = target.relative_to(root).as_posix()
            if _kedro_viz_path(rel):
                print(
                    f"assemble_pages: link to the absent Kedro-Viz mount: "
                    f"{_artifact_path(page, artifact_root)} -> {raw!r}",
                    file=sys.stderr,
                )
                raise SystemExit(1)


_REFRESH_URL = re.compile(r"""http-equiv=["']refresh["'][^>]*content=["'][^"']*url=([^"']+)["']""", re.IGNORECASE)


def _check_kedro_viz_redirect(artifact_root: Path, site_url: str) -> None:
    """The ``/kedro-viz/`` stub lands on the mount under this host's base path.

    Whoever wrote it (Starlight's redirects map or ``_ensure_kedro_viz_redirect``), a root-absolute
    target outside the base path leaves the site: until 2026-10-15 the live stub sent
    ``/local-recipes/kedro-viz/`` to ``/dashboard/kedro-viz/`` on the user site's root."""
    stub = artifact_root / KEDRO_VIZ_REDIRECT
    match = _REFRESH_URL.search(stub.read_text(encoding="utf-8", errors="replace"))
    target = match.group(1).strip() if match else ""
    base_path = _base_path(site_url)
    if target.startswith("/"):
        resolved = (
            (artifact_root / target[len(base_path) :]).resolve() if target.startswith(base_path) else None
        )
    elif target and not urlparse(target).scheme and not target.startswith("//"):
        resolved = (stub.parent / target).resolve()
    else:
        resolved = None
    mount = (artifact_root / KEDRO_VIZ_MOUNT).resolve()
    if resolved not in (mount, mount / "index.html"):
        print(
            f"assemble_pages: {KEDRO_VIZ_REDIRECT} redirects to {target!r}, not to {KEDRO_VIZ_MOUNT}/ "
            f"under the base path {base_path}",
            file=sys.stderr,
        )
        raise SystemExit(1)


def check(artifact_root: Path, *, site_url: str | None = None, fleet_status: Path | None = None) -> None:
    site_url = site_url or _read_site_url_for_check(artifact_root)
    mounted = (artifact_root / KEDRO_VIZ_MOUNT).exists()
    status_on = sp.enabled_from_env()
    if status_on:
        repo_root = _repo_root()
        _check_fleet_status_input(fleet_status or _fleet_status_input(repo_root), repo_root)
    else:
        _check_no_status_paths(artifact_root)
    for rel in _required_paths(kedro_viz=mounted, status_pages=status_on):
        if not (artifact_root / rel).is_file():
            print(f"assemble_pages: missing required path {rel}", file=sys.stderr)
            raise SystemExit(1)
    if mounted:
        try:
            kv.read_manifest(artifact_root / KEDRO_VIZ_MOUNT, label=KEDRO_VIZ_MOUNT)
        except kv.ExportShapeError as exc:
            print(f"assemble_pages: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        _check_kedro_viz_redirect(artifact_root, site_url)
    else:
        _check_no_kedro_viz_paths(artifact_root, site_url)

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

    _check_href_resolution(artifact_root, site_url=site_url)
    _check_shelf_pages(artifact_root, site_url)
    _check_cross_origin_and_hosts(artifact_root, site_url)
    expected = _expected_menu(kedro_viz=mounted, status_pages=status_on)
    if status_on:
        _check_status_menu_entry(expected)
    _check_menu_links(artifact_root, site_url, expected)


def assemble(
    artifact_root: Path,
    *,
    repo_root: Path | None = None,
    dashboard_src: Path | None = None,
    skip_herald_build: bool = False,
    skip_docs_site_build: bool = False,
    site_url: str | None = None,
    fleet_status: Path | None = None,
) -> str:
    repo_root = repo_root or _repo_root()
    status_on = sp.enabled_from_env()
    fleet_status = fleet_status or _fleet_status_input(repo_root)
    dashboard_src = dashboard_src or (repo_root / "docs" / "dashboard")
    artifact_root = artifact_root.resolve()
    herald_out = artifact_root / HERALD_PREFIX
    site_url = site_url or resolve_from_process_environment()

    if not skip_docs_site_build:
        _run_docs_site_build(repo_root, site_url)
        if not enabled_from_env():
            _remove_empty_astro_dossier(artifact_root)
    _write_site_url_marker(artifact_root, site_url)

    one_generator = enabled_from_env()
    mounts = [f"{HERALD_PREFIX}/", f"{DASHBOARD_PREFIX}/", *([f"{STATUS_PREFIX}/"] if status_on else [])]
    for mount in mounts:
        existing = artifact_root / mount.rstrip("/")
        if existing.exists():
            if (
                mount.startswith(f"{HERALD_PREFIX}/")
                and one_generator
                and _astro_dossier_preexists(artifact_root)
            ):
                continue
            print(f"assemble_pages: collision at {mount}", file=sys.stderr)
            raise SystemExit(1)

    if status_on:  # before anything is mounted; off, the input is never opened
        _check_fleet_status_input(fleet_status, repo_root)
    mounted = _copy_dashboard(dashboard_src, artifact_root, repo_root=repo_root)
    if not skip_herald_build:
        _build_herald(
            herald_out,
            repo_root,
            kedro_viz_export=dashboard_src / "kedro-viz",
            dashboard_out=(artifact_root / DASHBOARD_PREFIX) if mounted else None,
            status_out=(artifact_root / STATUS_PREFIX) if status_on else None,
            fleet_status=fleet_status if status_on else None,
        )
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
