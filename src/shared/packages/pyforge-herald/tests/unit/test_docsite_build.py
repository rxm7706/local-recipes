"""Unit tests for ``docsite/build.py`` (Story 35.1 / DW-FU-24-2-1)."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[6]


def _load_build_module(monkeypatch):
    stub = types.ModuleType("jinja2")

    class _Env:
        def __init__(self, *args, **kwargs):
            pass

        def get_template(self, name):
            raise RuntimeError("jinja not used in these unit tests")

    stub.Environment = _Env  # type: ignore[attr-defined]
    stub.FileSystemLoader = object  # type: ignore[attr-defined]
    stub.StrictUndefined = object  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "jinja2", stub)
    path = REPO_ROOT / "docsite" / "build.py"
    spec = importlib.util.spec_from_file_location("docsite_build_under_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def build_mod(monkeypatch):
    return _load_build_module(monkeypatch)


def _green_check_tree(tmp_path: Path) -> tuple[Path, dict]:
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
        "infographics": [
            {
                "source": "presentations/pyforge-alpha/project/Alpha Infographic standalone.html",
                "out_name": "alpha.html",
                "bytes": 100,
            }
        ],
        "families": [
            {
                "slug": "pyforge-alpha",
                "infographic_deck": None,
                "executive_summary": None,
                "pptx": [],
                "marp": [],
            }
        ],
    }
    ig_path = out_dir / "infographics" / "alpha.html"
    ig_path.write_text("x" * 100, encoding="utf-8")
    deck_dir = out_dir / "decks" / "pyforge-alpha"
    deck_dir.mkdir(parents=True)
    (deck_dir / "index.html").write_text("<html><body>" + ("y" * 600) + "</body></html>", encoding="utf-8")
    gallery = out_dir / "infographics" / "index.html"
    gallery.write_text(gallery.read_text(encoding="utf-8") + " alpha.html ", encoding="utf-8")
    decks_index = out_dir / "decks" / "index.html"
    decks_index.write_text(decks_index.read_text(encoding="utf-8") + " pyforge-alpha ", encoding="utf-8")
    return out_dir, result


def test_collect_infographics_respects_include_exclude_order_and_dedupe(build_mod, tmp_path: Path):
    repo = tmp_path
    html = repo / "presentations/pyforge-alpha/project/Alpha Infographic standalone.html"
    html.parent.mkdir(parents=True)
    html.write_text("<html><head><title>Alpha</title></head><body></body></html>", encoding="utf-8")
    beta = repo / "presentations/pyforge-beta/project/Beta Infographic standalone.html"
    beta.parent.mkdir(parents=True)
    beta.write_text("<html><head><title>Beta</title></head><body></body></html>", encoding="utf-8")
    noise = repo / "presentations/pyforge-alpha/project/skip.html"
    noise.write_text("<html><head><title>Skip</title></head><body></body></html>", encoding="utf-8")
    cfg = {
        "infographics": {
            "include": ["presentations/pyforge-*/project/*standalone.html"],
            "exclude": ["presentations/pyforge-alpha/project/skip.html"],
            "overrides": {
                "presentations/pyforge-beta/project/Beta Infographic standalone.html": {"order": 1},
                "presentations/pyforge-alpha/project/Alpha Infographic standalone.html": {"order": 2},
            },
        }
    }
    items = build_mod.collect_infographics(cfg, repo)
    assert [i["source"] for i in items] == [
        "presentations/pyforge-beta/project/Beta Infographic standalone.html",
        "presentations/pyforge-alpha/project/Alpha Infographic standalone.html",
    ]
    dup = repo / "presentations/pyforge-gamma/project/Gamma Infographic standalone.html"
    dup.parent.mkdir(parents=True)
    dup.write_text("<html><head><title>Gamma</title></head><body></body></html>", encoding="utf-8")
    cfg["infographics"]["overrides"]["presentations/pyforge-gamma/project/Gamma Infographic standalone.html"] = {
        "slug": "gamma"
    }
    cfg["infographics"]["include"].append("presentations/pyforge-gamma/project/*standalone.html")
    items2 = build_mod.collect_infographics(cfg, repo)
    names = [i["out_name"] for i in items2 if "gamma" in i["source"]]
    assert names == ["gamma.html"]


def test_collect_families_derives_slug_and_artifact_fields(build_mod, tmp_path: Path):
    repo = tmp_path
    deck_dir = repo / "presentations/pyforge-alpha"
    poster = deck_dir / "project/Alpha Infographic standalone.html"
    poster.parent.mkdir(parents=True)
    poster.write_text("<html><head><title>Alpha</title></head><body></body></html>", encoding="utf-8")
    (deck_dir / "README.md").write_text("# Alpha\n", encoding="utf-8")
    (deck_dir / "project" / "Alpha - Infographic Deck.dc.html").write_text("<html></html>", encoding="utf-8")
    pptx_dir = deck_dir / "src/pptx"
    pptx_dir.mkdir(parents=True)
    (pptx_dir / "alpha-deck-2026-01-01.pptx").write_bytes(b"pptx")
    marp_dir = deck_dir / "src/marp"
    marp_dir.mkdir(parents=True)
    (marp_dir / "alpha-2026-01-01.md").write_text("# slide", encoding="utf-8")
    infographics = [
        {
            "source": "presentations/pyforge-alpha/project/Alpha Infographic standalone.html",
            "path": poster,
            "title": "Alpha",
            "order": 1,
            "description": "desc",
        }
    ]
    families = build_mod.collect_families(infographics, repo, commit="abc123")
    assert len(families) == 1
    fam = families[0]
    assert fam["slug"] == "pyforge-alpha"
    assert fam["infographic_deck"] is not None
    assert fam["pptx"] and fam["marp"]


def test_check_passes_on_a_green_fixture(build_mod, tmp_path: Path, capsys):
    out_dir, result = _green_check_tree(tmp_path)
    assert build_mod.check(out_dir, result) == 0
    assert "checks passed" in capsys.readouterr().out


def test_check_flags_each_required_output(build_mod, tmp_path: Path, capsys):
    out_dir, result = _green_check_tree(tmp_path)
    (out_dir / "index.html").unlink()
    assert build_mod.check(out_dir, result) == 1
    err = capsys.readouterr().err
    assert "missing output: index.html" in err


def test_check_flags_unrendered_jinja_in_dossier(build_mod, tmp_path: Path, capsys):
    out_dir, result = _green_check_tree(tmp_path)
    dossier = out_dir / "dossier" / "index.html"
    dossier.write_text(dossier.read_text(encoding="utf-8") + " {{ bad }} ", encoding="utf-8")
    assert build_mod.check(out_dir, result) == 1
    assert "unrendered Jinja" in capsys.readouterr().err


def test_check_flags_artifact_with_document_tags(build_mod, tmp_path: Path, capsys):
    out_dir, result = _green_check_tree(tmp_path)
    (out_dir / "artifact" / "dossier.html").write_text("<html><body>x</body></html>", encoding="utf-8")
    assert build_mod.check(out_dir, result) == 1
    assert "artifact build must not contain" in capsys.readouterr().err


def test_check_flags_missing_infographic_publish(build_mod, tmp_path: Path, capsys):
    out_dir, result = _green_check_tree(tmp_path)
    (out_dir / "infographics" / "alpha.html").unlink()
    assert build_mod.check(out_dir, result) == 1
    assert "infographic not published" in capsys.readouterr().err
