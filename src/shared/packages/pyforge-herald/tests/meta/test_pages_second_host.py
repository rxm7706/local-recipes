"""Story 31.1: Pages artifact builds for the deploying host (CAP-56)."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest
from pyforge.testing_kit.flags import flagd_tree

PAGES_SECOND_HOST_FLAG = "pyforge.herald.pages_second_host"
ENTERPRISE_SITE = "https://pages.ghe.example/org/local-recipes"
ENTERPRISE_BASE_PATH = "/org/local-recipes/"


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (
            candidate / "src" / "shared" / "packages" / "pyforge-herald"
        ).is_dir():
            return candidate
    raise AssertionError("could not locate repo root")


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _pages_second_host():
    root = _repo_root()
    tools = root / "docsite" / "tools"
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    return _load_module("pages_second_host_under_test", tools / "pages_second_host.py")


def _assemble_pages():
    root = _repo_root()
    return _load_module(
        "assemble_pages_under_test",
        root / "docsite" / "tools" / "assemble_pages.py",
    )


def test_public_site_url_default() -> None:
    psh = _pages_second_host()
    assert psh.public_site_url(github_repository="rxm7706/local-recipes") == (
        "https://rxm7706.github.io/local-recipes"
    )


def test_combine_pages_host() -> None:
    psh = _pages_second_host()
    url = psh.combine_pages_host(ENTERPRISE_SITE, ENTERPRISE_BASE_PATH)
    assert url == "https://pages.ghe.example/org/local-recipes"


def test_resolve_build_site_url_flag_on() -> None:
    psh = _pages_second_host()
    url = psh.resolve_build_site_url(
        configured_base_url=ENTERPRISE_SITE,
        configured_base_path=ENTERPRISE_BASE_PATH,
        apply_second_host=True,
    )
    assert url == "https://pages.ghe.example/org/local-recipes"


def test_resolve_build_site_url_flag_off_ignores_enterprise() -> None:
    psh = _pages_second_host()
    url = psh.resolve_build_site_url(
        configured_base_url=ENTERPRISE_SITE,
        configured_base_path=ENTERPRISE_BASE_PATH,
        apply_second_host=False,
    )
    assert url == "https://rxm7706.github.io/local-recipes"


def test_export_host_env_flag_on_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    psh = _pages_second_host()
    monkeypatch.setenv("PAGES_HOST_BASE_URL", ENTERPRISE_SITE)
    monkeypatch.setenv("PAGES_HOST_BASE_PATH", ENTERPRISE_BASE_PATH)

    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, {PAGES_SECOND_HOST_FLAG: "on"})))
    on_env = psh.export_host_env_for_ci()
    assert on_env[psh.ENV_APPLY_HOST] == "1"
    assert on_env[psh.ENV_SITE_URL] == "https://pages.ghe.example/org/local-recipes"

    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(flagd_tree(tmp_path, {PAGES_SECOND_HOST_FLAG: "off"})))
    off_env = psh.export_host_env_for_ci()
    assert off_env[psh.ENV_APPLY_HOST] == "0"
    assert off_env[psh.ENV_SITE_URL] == "https://rxm7706.github.io/local-recipes"


def _minimal_artifact(artifact: Path, site_url: str, *, herald_index_body: str) -> None:
    assemble_pages = _assemble_pages()
    (artifact / "index.html").write_text("<html></html>", encoding="utf-8")
    (artifact / "404.html").write_text("<html></html>", encoding="utf-8")
    herald = artifact / "herald"
    (herald / "dossier").mkdir(parents=True)
    (herald / "dossier" / "index.html").write_text("<html></html>", encoding="utf-8")
    (herald / "index.html").write_text(herald_index_body, encoding="utf-8")
    (artifact / "dossier").mkdir(parents=True, exist_ok=True)
    (artifact / "dossier" / "index.html").write_text(
        assemble_pages.redirect_html("herald/dossier/index.html"),
        encoding="utf-8",
    )
    dashboard = artifact / "dashboard" / "kedro-viz"
    dashboard.mkdir(parents=True)
    (dashboard / "index.html").write_text("<html></html>", encoding="utf-8")
    (artifact / "kedro-viz").mkdir(parents=True, exist_ok=True)
    (artifact / "kedro-viz" / "index.html").write_text(
        assemble_pages.redirect_html("../dashboard/kedro-viz/index.html"),
        encoding="utf-8",
    )
    assemble_pages._write_site_url_marker(artifact, site_url)


@pytest.mark.parametrize(
    ("snippet", "kind"),
    [
        ('<script src="https://cdn.example/x.js"></script>', "script"),
        ('<link rel="stylesheet" href="https://cdn.example/x.css">', "stylesheet"),
        ('@font-face { src: url(https://fonts.gstatic.com/font.woff2); }', "font"),
        ('<img src="https://cdn.example/x.png">', "image"),
        ('fetch("https://platform.example/api")', "fetch"),
        ('xhr.open("GET", "https://platform.example/api")', "xhr"),
    ],
)
def test_pages_check_cross_origin_kinds(tmp_path: Path, snippet: str, kind: str) -> None:
    assemble_pages = _assemble_pages()
    psh = _pages_second_host()
    artifact = tmp_path / "site"
    artifact.mkdir()
    site_url = psh.public_site_url()
    body = f"<html><body>{snippet}</body></html>"
    _minimal_artifact(artifact, site_url, herald_index_body=body)

    with pytest.raises(SystemExit) as exc:
        assemble_pages.check(artifact, site_url=site_url)
    assert exc.value.code == 1


def test_pages_check_allows_github_navigation(tmp_path: Path) -> None:
    assemble_pages = _assemble_pages()
    psh = _pages_second_host()
    artifact = tmp_path / "site"
    artifact.mkdir()
    site_url = psh.public_site_url()
    body = '<html><a href="https://github.com/rxm7706/local-recipes">repo</a></html>'
    _minimal_artifact(artifact, site_url, herald_index_body=body)
    assemble_pages.check(artifact, site_url=site_url)


def test_pages_check_absolute_internal_other_host(tmp_path: Path) -> None:
    assemble_pages = _assemble_pages()
    psh = _pages_second_host()
    artifact = tmp_path / "site"
    artifact.mkdir()
    enterprise = psh.combine_pages_host(ENTERPRISE_SITE, ENTERPRISE_BASE_PATH)
    body = '<html><a href="https://rxm7706.github.io/local-recipes/herald/">home</a></html>'
    _minimal_artifact(artifact, enterprise, herald_index_body=body)
    with pytest.raises(SystemExit) as exc:
        assemble_pages.check(artifact, site_url=enterprise)
    assert exc.value.code == 1


def test_flags_json_carries_pages_second_host() -> None:
    root = _repo_root()
    tree = json.loads((root / "src/platform/config/flags.json").read_text(encoding="utf-8"))
    flag = tree["flags"][PAGES_SECOND_HOST_FLAG]
    assert flag["defaultVariant"] == "off"
