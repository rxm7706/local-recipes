"""Unit tests for ``docsite/build.py`` (Story 35.1 / DW-FU-24-2-1; Story 35.2)."""

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
    page_html = "<html><body>" + ("x" * 600) + "</body></html>"
    for name in ("index.html", "dossier/index.html", "infographics/index.html", "decks/index.html"):
        path = out_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page_html, encoding="utf-8")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")
    (out_dir / "assets").mkdir()
    (out_dir / "assets/site.css").write_text("body{}", encoding="utf-8")
    (out_dir / "artifact").mkdir()
    (out_dir / "artifact/dossier.html").write_text("fragment " + ("x" * 600), encoding="utf-8")

    ig_bytes = 100
    deck_view_bytes = 650
    exec_bytes = 640
    pptx_bytes = 120
    marp_bytes = 80

    result = {
        "infographics": [
            {
                "source": "presentations/pyforge-alpha/project/Alpha Infographic standalone.html",
                "out_name": "alpha.html",
                "bytes": ig_bytes,
            }
        ],
        "families": [
            {
                "slug": "pyforge-alpha",
                "title": "Alpha",
                "infographic_deck": {
                    "path": Path("deck.dc.html"),
                    "label": "Infographic Deck",
                    "bytes": deck_view_bytes,
                },
                "executive_summary": {
                    "path": Path("exec.dc.html"),
                    "label": "Executive Summary",
                    "bytes": exec_bytes,
                },
                "pptx": [{"name": "alpha-deck-2026-01-01.pptx", "bytes": pptx_bytes}],
                "marp": [{"name": "alpha-2026-01-01.md", "bytes": marp_bytes}],
            }
        ],
    }
    ig_path = out_dir / "infographics" / "alpha.html"
    ig_path.write_text("x" * ig_bytes, encoding="utf-8")
    deck_dir = out_dir / "decks" / "pyforge-alpha"
    deck_dir.mkdir(parents=True)
    (deck_dir / "index.html").write_text(page_html, encoding="utf-8")
    (deck_dir / "infographic-deck.html").write_text("d" * deck_view_bytes, encoding="utf-8")
    (deck_dir / "executive-summary.html").write_text("e" * exec_bytes, encoding="utf-8")
    downloads = deck_dir / "downloads"
    downloads.mkdir()
    (downloads / "alpha-deck-2026-01-01.pptx").write_bytes(b"p" * pptx_bytes)
    (downloads / "alpha-2026-01-01.md").write_text("m" * marp_bytes, encoding="utf-8")
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
    # The noise file matches the include glob, so only the exclude can drop it.
    skip_rel = "presentations/pyforge-alpha/project/Skip Infographic standalone.html"
    noise = repo / skip_rel
    noise.write_text("<html><head><title>Skip</title></head><body></body></html>", encoding="utf-8")
    cfg = {
        "infographics": {
            "include": ["presentations/pyforge-*/project/*standalone.html"],
            "exclude": [skip_rel],
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
    assert skip_rel not in {i["source"] for i in items}
    unexcluded = build_mod.collect_infographics({"infographics": {**cfg["infographics"], "exclude": []}}, repo)
    assert skip_rel in {i["source"] for i in unexcluded}
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

    twin = repo / "presentations/pyforge-delta/project/Delta Infographic standalone.html"
    twin.parent.mkdir(parents=True)
    twin.write_text("<html><head><title>Gamma</title></head><body></body></html>", encoding="utf-8")
    cfg["infographics"]["include"].append("presentations/pyforge-delta/project/*standalone.html")
    colliding = build_mod.collect_infographics(cfg, repo)
    out_names = sorted(i["out_name"] for i in colliding if i["title"].lower() == "gamma")
    assert out_names == ["gamma-1.html", "gamma.html"]


def test_collect_families_derives_slug_and_artifact_fields(build_mod, tmp_path: Path):
    repo = tmp_path
    deck_dir = repo / "presentations/pyforge-alpha"
    poster = deck_dir / "project/Alpha Infographic standalone.html"
    poster.parent.mkdir(parents=True)
    poster.write_text("<html><head><title>Alpha</title></head><body></body></html>", encoding="utf-8")
    (deck_dir / "README.md").write_text("# Alpha\n", encoding="utf-8")
    deck_path = deck_dir / "project" / "Alpha - Infographic Deck.dc.html"
    deck_path.write_text("<html>" + ("d" * 400) + "</html>", encoding="utf-8")
    exec_path = deck_dir / "project" / "Alpha - Executive Summary.dc.html"
    exec_path.write_text("<html>" + ("e" * 300) + "</html>", encoding="utf-8")
    pptx_dir = deck_dir / "src/pptx"
    pptx_dir.mkdir(parents=True)
    pptx_path = pptx_dir / "alpha-deck-2026-01-01.pptx"
    pptx_path.write_bytes(b"pptx")
    marp_dir = deck_dir / "src/marp"
    marp_dir.mkdir(parents=True)
    marp_path = marp_dir / "alpha-2026-01-01.md"
    marp_path.write_text("# slide", encoding="utf-8")
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
    assert fam["infographic_deck"]["path"] == deck_path
    assert fam["infographic_deck"]["bytes"] == deck_path.stat().st_size
    assert fam["executive_summary"] is not None
    assert fam["executive_summary"]["path"] == exec_path
    assert fam["executive_summary"]["bytes"] == exec_path.stat().st_size
    assert fam["pptx"][0]["name"] == "alpha-deck-2026-01-01.pptx"
    assert fam["pptx"][0]["bytes"] == pptx_path.stat().st_size
    assert fam["marp"][0]["name"] == "alpha-2026-01-01.md"
    assert fam["marp"][0]["bytes"] == marp_path.stat().st_size


def test_check_passes_on_a_green_fixture(build_mod, tmp_path: Path, capsys):
    out_dir, result = _green_check_tree(tmp_path)
    assert build_mod.check(out_dir, result) == 0
    assert "checks passed" in capsys.readouterr().out


@pytest.mark.parametrize(
    "mutator,needle",
    [
        (lambda od, r: (od / "index.html").unlink(), "missing output: index.html"),
        (
            lambda od, r: (od / "dossier/index.html").write_text("tiny", encoding="utf-8"),
            "suspiciously small: dossier/index.html",
        ),
        (
            lambda od, r: (od / "artifact/dossier.html").write_text("<html><body>x</body></html>", encoding="utf-8"),
            "artifact build must not contain",
        ),
        (
            lambda od, r: (od / "dossier/index.html").write_text(
                (od / "dossier/index.html").read_text(encoding="utf-8") + " {{ bad }} ",
                encoding="utf-8",
            ),
            "unrendered Jinja delimiters in dossier output",
        ),
        (lambda od, r: (od / "infographics/alpha.html").unlink(), "infographic not published"),
        (
            lambda od, r: (od / "infographics/alpha.html").write_text("x" * 50, encoding="utf-8"),
            "infographic shrank on publish",
        ),
        (
            lambda od, r: (od / "infographics/index.html").write_text("x" * 600, encoding="utf-8"),
            "infographic missing from gallery: alpha.html",
        ),
        (lambda od, r: (od / "decks/pyforge-alpha/index.html").unlink(), "deck family page not published"),
        (
            lambda od, r: (od / "decks/pyforge-alpha/index.html").write_text("small", encoding="utf-8"),
            "suspiciously small: decks/pyforge-alpha/index.html",
        ),
        (
            lambda od, r: (od / "decks/pyforge-alpha/index.html").write_text(
                "<html><body>" + ("y" * 600) + " {% bad %} </body></html>",
                encoding="utf-8",
            ),
            "unrendered Jinja delimiters in decks/pyforge-alpha/index.html",
        ),
        (
            lambda od, r: (od / "decks/index.html").write_text("x" * 600, encoding="utf-8"),
            "deck missing from the decks index: pyforge-alpha",
        ),
        (
            lambda od, r: (od / "decks/pyforge-alpha/infographic-deck.html").unlink(),
            "pyforge-alpha: infographic_deck not published",
        ),
        (
            lambda od, r: (od / "decks/pyforge-alpha/executive-summary.html").write_text("e" * 100, encoding="utf-8"),
            "pyforge-alpha: executive_summary shrank on publish",
        ),
        (
            lambda od, r: (od / "decks/pyforge-alpha/downloads/alpha-deck-2026-01-01.pptx").unlink(),
            "download not published: alpha-deck-2026-01-01.pptx",
        ),
        (
            lambda od, r: (od / "decks/pyforge-alpha/downloads/alpha-deck-2026-01-01.pptx").write_bytes(b"x"),
            "download size mismatch: alpha-deck-2026-01-01.pptx",
        ),
        (
            lambda od, r: (od / "decks/pyforge-alpha/downloads/alpha-2026-01-01.md").unlink(),
            "download not published: alpha-2026-01-01.md",
        ),
        (
            lambda od, r: (od / "decks/pyforge-alpha/downloads/alpha-2026-01-01.md").write_text("m", encoding="utf-8"),
            "download size mismatch: alpha-2026-01-01.md",
        ),
    ],
)
def test_check_flags_each_problem_predicate(build_mod, tmp_path: Path, capsys, mutator, needle):
    out_dir, result = _green_check_tree(tmp_path)
    mutator(out_dir, result)
    assert build_mod.check(out_dir, result) == 1
    assert needle in capsys.readouterr().err


@pytest.mark.parametrize(
    "plant,needle",
    [
        (
            lambda od: (od / "index.html").write_text(
                (od / "index.html").read_text(encoding="utf-8")
                + '<link rel="preconnect" href="https://fonts.gstatic.com">',
                encoding="utf-8",
            ),
            "external origin 'fonts.gstatic.com'",
        ),
        (
            lambda od: (od / "assets/planted.css").write_text(
                "@import url('https://fonts.googleapis.com/css2?family=Archivo');",
                encoding="utf-8",
            )
            or (od / "index.html").write_text(
                (od / "index.html").read_text(encoding="utf-8") + '<link rel="stylesheet" href="assets/planted.css">',
                encoding="utf-8",
            ),
            "external origin 'fonts.googleapis.com'",
        ),
        (
            lambda od: (od / "dossier/index.html").write_text(
                (od / "dossier/index.html").read_text(encoding="utf-8")
                + '<a href="https://github.com/example/repo">repo</a>',
                encoding="utf-8",
            ),
            None,
        ),
        (
            lambda od: (
                (od / "assets/fonts").mkdir(parents=True, exist_ok=True),
                (od / "assets/fonts/bad.css").write_text(
                    "@font-face{font-family:X;src:url('./missing.woff2');}",
                    encoding="utf-8",
                ),
            ),
            "missing font file",
        ),
    ],
)
def test_check_external_origin_and_font_face(build_mod, tmp_path: Path, capsys, plant, needle):
    out_dir, result = _green_check_tree(tmp_path)
    plant(out_dir)
    code = build_mod.check(out_dir, result)
    err = capsys.readouterr().err
    if needle is None:
        assert code == 0
    else:
        assert code == 1
        assert needle in err


def test_rewrite_google_font_links_inserts_vendored_stylesheet(build_mod):
    raw = (
        "<html><head>"
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link href="https://fonts.googleapis.com/css2?family=Archivo" rel="stylesheet">'
        "</head><body></body></html>"
    )
    out = build_mod.rewrite_google_font_links(raw, "../assets/fonts/fonts.css")
    assert "fonts.googleapis.com" not in out
    assert '../assets/fonts/fonts.css' in out


def test_check_skips_family_views_when_executive_summary_is_none(build_mod, tmp_path: Path, capsys):
    out_dir, result = _green_check_tree(tmp_path)
    (out_dir / "decks/pyforge-alpha/executive-summary.html").unlink()
    result["families"][0]["executive_summary"] = None
    assert build_mod.check(out_dir, result) == 0
