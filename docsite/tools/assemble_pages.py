#!/usr/bin/env python3
"""Assemble one GitHub Pages artifact: Starlight + herald dossier + dashboard."""

from __future__ import annotations

import argparse
import html
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

HERALD_PREFIX = "herald"
DASHBOARD_PREFIX = "dashboard"
ROOT_HERALD_INDEX = f"{HERALD_PREFIX}/index.html"
KEDRO_VIZ_REDIRECT = "kedro-viz/index.html"

_HREF_SRC = re.compile(
    r"""(?:href|src)\s*=\s*["']([^"']+)["']""",
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
    import os

    return os.path.relpath(to_file, start=from_file.parent).replace("\\", "/")


def _artifact_path(path: Path, artifact_root: Path) -> str:
    return path.relative_to(artifact_root).as_posix()


def _refuses_collision(artifact_root: Path, rel_path: str) -> None:
    target = artifact_root / rel_path
    if target.exists():
        print(f"assemble_pages: collision at {rel_path}", file=sys.stderr)
        raise SystemExit(1)


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
    raw = raw.strip()
    if not raw or raw.startswith("#"):
        return None
    if raw.startswith(("mailto:", "tel:", "javascript:", "data:")):
        return None
    parsed = urlparse(raw)
    if parsed.scheme in ("http", "https"):
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


def _check_href_resolution(artifact_root: Path) -> None:
    herald_root = artifact_root / HERALD_PREFIX
    for page in _iter_herald_html(artifact_root):
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


def check(artifact_root: Path) -> None:
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


def assemble(
    artifact_root: Path,
    *,
    repo_root: Path | None = None,
    dashboard_src: Path | None = None,
    skip_herald_build: bool = False,
) -> None:
    repo_root = repo_root or _repo_root()
    dashboard_src = dashboard_src or (repo_root / "docs" / "dashboard")
    artifact_root = artifact_root.resolve()
    herald_out = artifact_root / HERALD_PREFIX

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
    args = parser.parse_args(argv)
    repo_root = _repo_root()
    artifact_root = (repo_root / args.artifact_root).resolve()

    if args.check:
        check(artifact_root)
        return

    assemble(
        artifact_root,
        repo_root=repo_root,
        skip_herald_build=args.skip_herald_build,
    )
    check(artifact_root)


if __name__ == "__main__":
    main()
