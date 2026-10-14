"""Story 27.2: unified GitHub Pages artifact (Starlight + herald + dashboard)."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest


def _load_assemble_pages():
    root = _repo_root()
    path = root / "docsite" / "tools" / "assemble_pages.py"
    spec = importlib.util.spec_from_file_location("assemble_pages_under_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (
            candidate / "src" / "shared" / "packages" / "pyforge-herald"
        ).is_dir():
            return candidate
    raise AssertionError("could not locate repo root")


# Story 40.1 (FR-8.6): pages-check requires herald's shared menu, exactly as docsite/content/site.yml
# lists it, on every docs page and every herald shell page; the docs root also links every herald
# target from its sidebar. (label, docs path from the site root, herald href from the /herald/ mount)
_SHARED_MENU = [
    ("Docs", "", "../"),
    ("Overview", "herald/", "index.html"),
    ("Dossier", "herald/dossier/", "dossier/index.html"),
    ("Infographics", "herald/infographics/", "infographics/index.html"),
    ("Decks", "herald/decks/", "decks/index.html"),
    ("Kedro-Viz", "dashboard/kedro-viz/", "../dashboard/kedro-viz/"),
]


def _write_shared_menu(artifact: Path, base: str, *, herald_index_extra: str = "") -> None:
    """The docs root and 404 with the top menu and Herald sidebar links, and herald's four shell
    pages with the same menu as relative links."""
    top = "".join(f'<a data-pf-menu-link href="{base}{path}">{label}</a>' for label, path, _ in _SHARED_MENU)
    sidebar = "".join(f'<a href="{base}{path}">{label}</a>' for label, path, _ in _SHARED_MENU[1:])
    for rel in ("index.html", "404.html"):
        (artifact / rel).write_text(f"<html>{top}{sidebar}</html>", encoding="utf-8")
    for sub in ("", "dossier/", "infographics/", "decks/"):
        rel = "../" if sub else ""
        menu = "".join(f'<a data-pf-menu-link href="{rel}{href}">{label}</a>' for label, _, href in _SHARED_MENU)
        page = artifact / "herald" / sub / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        extra = herald_index_extra if not sub else ""
        page.write_text(f"<html>{menu}{extra}</html>", encoding="utf-8")


def test_dashboard_yml_is_sole_deploy_pages_caller() -> None:
    root = _repo_root()
    workflows = root / ".github" / "workflows"
    deploy_hits: list[str] = []
    for path in sorted(workflows.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        if "actions/deploy-pages" in text or "deploy-pages@" in text:
            deploy_hits.append(path.name)
    assert deploy_hits == ["pages.yml"]


def test_dashboard_yml_uploads_unified_artifact() -> None:
    root = _repo_root()
    text = (root / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    assert "path: docs-site/build/site" in text
    assert "concurrency:" in text
    assert "group: pages" in text
    assert re.search(r"push:\s*\n\s*branches:\s*\[main\]", text)
    assert "workflow_dispatch" in text


def test_docsite_check_runs_pages_check_with_path_filters() -> None:
    root = _repo_root()
    text = (root / ".github/workflows/docsite-check.yml").read_text(encoding="utf-8")
    assert "pages-check" in text
    assert "docs/**" in text
    assert "docs-site/**" in text


def test_assemble_writes_redirect_per_herald_html(tmp_path: Path) -> None:
    assemble_pages = _load_assemble_pages()
    artifact = tmp_path / "site"
    artifact.mkdir()
    _write_shared_menu(artifact, "/local-recipes/")

    dashboard = artifact / "dashboard" / "kedro-viz"
    dashboard.mkdir(parents=True)
    (dashboard / "index.html").write_text("<html></html>", encoding="utf-8")

    assemble_pages._write_dossier_redirects(artifact)
    assemble_pages._ensure_kedro_viz_redirect(artifact)
    redirect = artifact / "dossier" / "index.html"
    assert redirect.is_file()
    assert "herald/dossier" in redirect.read_text(encoding="utf-8")
    assemble_pages.check(artifact, site_url="https://rxm7706.github.io/local-recipes")


def test_assemble_refuses_mount_collision(tmp_path: Path) -> None:
    assemble_pages = _load_assemble_pages()
    artifact = tmp_path / "site"
    artifact.mkdir()
    (artifact / "index.html").write_text("<html></html>", encoding="utf-8")
    (artifact / "herald").mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "docsite").mkdir()
    (repo / "docsite" / "build.py").write_text("", encoding="utf-8")
    (repo / "pixi.toml").write_text("", encoding="utf-8")
    (repo / "docs").mkdir()
    (repo / "docs" / "dashboard").mkdir()

    with pytest.raises(SystemExit) as exc:
        assemble_pages.assemble(
            artifact,
            repo_root=repo,
            skip_herald_build=True,
            skip_docs_site_build=True,
        )
    assert exc.value.code == 1


def test_assemble_refuses_redirect_collision(tmp_path: Path) -> None:
    assemble_pages = _load_assemble_pages()
    artifact = tmp_path / "site"
    artifact.mkdir()
    (artifact / "index.html").write_text("<html></html>", encoding="utf-8")
    (artifact / "404.html").write_text("<html></html>", encoding="utf-8")
    herald = artifact / "herald"
    (herald / "dossier").mkdir(parents=True)
    (herald / "dossier" / "index.html").write_text("<html></html>", encoding="utf-8")
    (herald / "index.html").write_text("<html></html>", encoding="utf-8")
    (artifact / "dossier").mkdir()
    (artifact / "dossier" / "index.html").write_text("existing", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        assemble_pages._write_dossier_redirects(artifact)
    assert exc.value.code == 1


def test_check_fails_on_missing_mount(tmp_path: Path) -> None:
    assemble_pages = _load_assemble_pages()
    artifact = tmp_path / "site"
    artifact.mkdir()
    (artifact / "index.html").write_text("<html></html>", encoding="utf-8")
    (artifact / "404.html").write_text("<html></html>", encoding="utf-8")
    herald = artifact / "herald"
    herald.mkdir()
    (herald / "index.html").write_text("<html></html>", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        assemble_pages.check(artifact)
    assert exc.value.code == 1
