"""Story 27.2: unified GitHub Pages artifact (Starlight + herald + dashboard)."""

from __future__ import annotations

import importlib.util
import re
import sys
import tomllib
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


def test_dashboard_yml_is_sole_deploy_pages_caller() -> None:
    root = _repo_root()
    workflows = root / ".github" / "workflows"
    deploy_hits: list[str] = []
    for path in sorted(workflows.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        if "actions/deploy-pages" in text or "deploy-pages@" in text:
            deploy_hits.append(path.name)
    assert deploy_hits == ["dashboard.yml"]


def test_dashboard_yml_uploads_unified_artifact() -> None:
    root = _repo_root()
    text = (root / ".github/workflows/dashboard.yml").read_text(encoding="utf-8")
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


def test_pr_preflight_site_check_leg_unchanged() -> None:
    root = _repo_root()
    pixi = tomllib.loads((root / "pixi.toml").read_text(encoding="utf-8"))
    preflight = pixi["feature"]["guild-tasks"]["tasks"]["pr-preflight-lanes"]
    legs = preflight["depends-on"]
    site_legs = [leg for leg in legs if isinstance(leg, dict) and leg.get("task") == "site-check"]
    assert site_legs == [{"task": "site-check", "environment": "site"}]


def test_assemble_writes_redirect_per_herald_html(tmp_path: Path) -> None:
    assemble_pages = _load_assemble_pages()
    artifact = tmp_path / "site"
    artifact.mkdir()
    (artifact / "index.html").write_text("<html></html>", encoding="utf-8")
    (artifact / "404.html").write_text("<html></html>", encoding="utf-8")

    herald = artifact / "herald"
    (herald / "dossier").mkdir(parents=True)
    (herald / "dossier" / "index.html").write_text('<html><a href="../index.html">home</a></html>', encoding="utf-8")
    (herald / "index.html").write_text("<html></html>", encoding="utf-8")

    dashboard = artifact / "dashboard" / "kedro-viz"
    dashboard.mkdir(parents=True)
    (dashboard / "index.html").write_text("<html></html>", encoding="utf-8")

    assemble_pages._write_dossier_redirects(artifact)
    assemble_pages._ensure_kedro_viz_redirect(artifact)
    redirect = artifact / "dossier" / "index.html"
    assert redirect.is_file()
    assert "herald/dossier" in redirect.read_text(encoding="utf-8")
    assemble_pages.check(artifact)


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
