"""Unit tests for scripts/deck_trio.py (herald Story 21.1;
spec-deck-family-lockstep CAP-1 head half): ``deck-trio <slug> --head``
derives ``project/<Persona> - Infographic.dc.html`` from the standalone
poster. Refuse-don't-guess, idempotent write, never edits the standalone.

Fixture style mirrors tests/scripts/test_deck_facts.py: a synthetic repo
root under tmp_path, the module reached through sys.path since scripts/
has no __init__.py, and ROOT monkeypatched so the run never rewrites a
tracked presentation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import deck_trio

SLUG = "pyforge-alpha"
PERSONA = "Alpha"
STANDALONE_NAME = f"{PERSONA}{deck_trio.POSTER_SUFFIX}"
HEAD_NAME = f"{PERSONA} - Infographic.dc.html"

STYLE = ".box { color: red; }"
BODY_INNER = '\n<div style="width:1240px; margin:0 auto;">hello</div>\n'
STANDALONE = (
    "<!DOCTYPE html>\n"
    "<html>\n"
    "<head>\n"
    '<meta charset="utf-8">\n'
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="stylesheet" href="https://example.test/font.css">\n'
    f"<style>\n{STYLE}\n</style>\n"
    "</head>\n"
    f"<body>{BODY_INNER}</body>\n"
    "</html>\n"
)
NO_STYLE = STANDALONE.replace(f"<style>\n{STYLE}\n</style>\n", "")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _standalone_path(root: Path, name: str = STANDALONE_NAME) -> Path:
    return root / "presentations" / SLUG / "project" / name


def _head_path(root: Path) -> Path:
    return root / "presentations" / SLUG / "project" / HEAD_NAME


@pytest.fixture
def root(tmp_path, monkeypatch) -> Path:
    _write(_standalone_path(tmp_path), STANDALONE)
    monkeypatch.setattr(deck_trio, "ROOT", tmp_path)
    return tmp_path


def _xdc_after_helmet(head_text: str) -> str:
    after = head_text.split("</helmet>", 1)[1]
    return after.split("</x-dc>", 1)[0]


def test_happy_path(root, capsys):
    assert deck_trio.main([SLUG, "--head"]) == 0
    assert capsys.readouterr().out.strip() == "wrote"
    head = _head_path(root)
    assert head.is_file()
    text = head.read_text(encoding="utf-8")
    assert _xdc_after_helmet(text) == BODY_INNER
    helmet = text.split("<helmet>", 1)[1].split("</helmet>", 1)[0]
    assert STYLE in helmet
    assert '<link rel="preconnect" href="https://fonts.googleapis.com">' in helmet
    assert '<link rel="stylesheet" href="https://example.test/font.css">' in helmet
    assert '<script src="./support.js"></script>' in text
    assert (
        'data-props="{&quot;$preview&quot;:{&quot;width&quot;:1240,&quot;height&quot;:2200}}"'
        in text
    )
    assert _standalone_path(root).read_text(encoding="utf-8") == STANDALONE


def test_idempotent(root, capsys):
    assert deck_trio.main([SLUG, "--head"]) == 0
    first = _head_path(root).read_text(encoding="utf-8")
    assert capsys.readouterr().out.strip() == "wrote"
    assert deck_trio.main([SLUG, "--head"]) == 0
    assert capsys.readouterr().out.strip() == "unchanged"
    assert _head_path(root).read_text(encoding="utf-8") == first
    assert _standalone_path(root).read_text(encoding="utf-8") == STANDALONE


def test_missing_standalone(tmp_path, monkeypatch):
    deck = tmp_path / "presentations" / SLUG
    deck.mkdir(parents=True)
    monkeypatch.setattr(deck_trio, "ROOT", tmp_path)
    with pytest.raises(SystemExit) as err:
        deck_trio.main([SLUG, "--head"])
    assert err.value.code == 2
    assert not any(deck.rglob("*.dc.html"))
    assert not (deck / "project").exists() or list((deck / "project").iterdir()) == []


def test_no_style_block(root):
    _write(_standalone_path(root), NO_STYLE)
    with pytest.raises(SystemExit) as err:
        deck_trio.main([SLUG, "--head"])
    assert err.value.code == 2
    assert not _head_path(root).exists()
    assert _standalone_path(root).read_text(encoding="utf-8") == NO_STYLE


def test_ambiguous_posters(root):
    _write(_standalone_path(root, f"Beta{deck_trio.POSTER_SUFFIX}"), STANDALONE)
    with pytest.raises(SystemExit) as err:
        deck_trio.main([SLUG, "--head"])
    assert err.value.code == 2
    assert not _head_path(root).exists()
    assert _standalone_path(root).read_text(encoding="utf-8") == STANDALONE


def test_unknown_slug(root):
    with pytest.raises(SystemExit) as err:
        deck_trio.main(["nope", "--head"])
    assert err.value.code == 2
    assert not (root / "presentations" / "nope").exists()
    assert not _head_path(root).exists()


def test_flag_required(root):
    with pytest.raises(SystemExit) as err:
        deck_trio.main([SLUG])
    assert err.value.code == 2
    assert not _head_path(root).exists()
    assert _standalone_path(root).read_text(encoding="utf-8") == STANDALONE


def test_standalone_frozen(root):
    before = _standalone_path(root).read_bytes()
    assert deck_trio.main([SLUG, "--head"]) == 0
    assert _standalone_path(root).read_bytes() == before
    with pytest.raises(SystemExit) as err:
        deck_trio.main([SLUG])
    assert err.value.code == 2
    assert _standalone_path(root).read_bytes() == before
