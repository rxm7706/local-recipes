"""Unit tests for ``docsite/build.py`` (Story 35.1 / DW-FU-24-2-1)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[6]


def _load_build_module():
    if "jinja2" not in sys.modules:
        stub = types.ModuleType("jinja2")
        stub.Environment = object  # type: ignore[attr-defined]
        stub.FileSystemLoader = object  # type: ignore[attr-defined]
        stub.StrictUndefined = object  # type: ignore[attr-defined]
        sys.modules["jinja2"] = stub
    path = REPO_ROOT / "docsite" / "build.py"
    spec = importlib.util.spec_from_file_location("docsite_build", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def build_mod():
    return _load_build_module()


def test_collect_infographics_respects_include_exclude_and_order(build_mod, tmp_path: Path):
    repo = tmp_path
    html = repo / "presentations/pyforge-alpha/project/Alpha Infographic standalone.html"
    html.parent.mkdir(parents=True)
    html.write_text("<html><head><title>Alpha</title></head><body></body></html>", encoding="utf-8")
    noise = repo / "presentations/pyforge-alpha/project/skip.html"
    noise.write_text("<html><head><title>Skip</title></head><body></body></html>", encoding="utf-8")
    cfg = {
        "infographics": {
            "include": ["presentations/pyforge-alpha/project/*standalone.html"],
            "exclude": ["presentations/pyforge-alpha/project/skip.html"],
            "overrides": {},
        }
    }
    items = build_mod.collect_infographics(cfg, repo)
    assert len(items) == 1
    assert items[0]["source"].endswith("Alpha Infographic standalone.html")


def test_collect_families_derives_one_slug_from_infographics(build_mod, tmp_path: Path):
    repo = tmp_path
    deck_dir = repo / "presentations/pyforge-alpha"
    poster = deck_dir / "project/Alpha Infographic standalone.html"
    poster.parent.mkdir(parents=True)
    poster.write_text("<html><head><title>Alpha</title></head><body></body></html>", encoding="utf-8")
    (deck_dir / "README.md").write_text("# Alpha\n", encoding="utf-8")
    infographics = [
        {
            "source": "presentations/pyforge-alpha/project/Alpha Infographic standalone.html",
            "path": poster,
            "title": "Alpha",
            "order": 1,
        }
    ]
    families = build_mod.collect_families(infographics, repo, commit="abc123")
    assert len(families) == 1
    assert families[0]["slug"] == "pyforge-alpha"


def test_check_flags_missing_required_output(build_mod, tmp_path: Path):
    out_dir = tmp_path / "dist"
    out_dir.mkdir()
    for name in ("index.html", "dossier/index.html", "infographics/index.html", "decks/index.html"):
        path = out_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("<html><body>" + ("x" * 600) + "</body></html>", encoding="utf-8")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")
    (out_dir / "assets").mkdir()
    (out_dir / "assets/site.css").write_text("body{}", encoding="utf-8")
    (out_dir / "artifact").mkdir()
    (out_dir / "artifact/dossier.html").write_text("fragment only", encoding="utf-8")
    result = {
        "infographics": [{"source": "presentations/x/y.html", "out_name": "missing.html", "bytes": 100}],
        "families": [],
    }
    assert build_mod.check(out_dir, result) == 1
