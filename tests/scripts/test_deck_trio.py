"""Unit tests for scripts/deck_trio.py: deriving a deck's Infographic HEAD
(``project/<Persona> - Infographic.dc.html``, spec-21-1, herald Story 21.1) and its
Infographic Deck (``project/<Persona> - Infographic Deck.dc.html``, spec-21-2, herald
Story 21.2) from its standalone poster via the documented mechanical transforms,
refusing rather than guessing on malformed input, and never touching the standalone.
Covers every I/O matrix row of both specs, plus (Story 23.5) that every derived
write also lands a ``<artifact>.stamp.json`` sidecar via the shared ``stamps``
module.

Fixture style mirrors tests/scripts/test_deck_facts.py: a synthetic repo root under
tmp_path, the module reached through sys.path since scripts/ has no __init__.py, and
``deck_trio.ROOT`` / ``deck_trio.measure_height`` / ``deck_trio.measure_all_sections``
monkeypatched so the run is offline, independent of the live tree, and needs no real
browser. ``root`` is ALSO a real (throwaway) git repo (Story 23.5): ``deck_trio.py``
now calls ``pyforge.herald.stamps.write_stamp`` after every derived write, and that
module shells real ``git`` commands to determine the source tree ref -- mirrors
``test_deck_pipeline.py``'s own ``_init_git_repo`` helper. ``pyforge-herald``'s own
``src/`` is not a `local-recipes` pixi dependency (only its ``deck-export``/
``deck-trio`` TASKS get a ``PYTHONPATH`` env override in pixi.toml, per this
story) -- a bare ``python -m pytest`` invocation of this file needs the same path
on ``sys.path`` itself, so it is added here too, mirroring the ``_SCRIPTS_DIR``
insertion just below.
"""

from __future__ import annotations

import subprocess
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
_HERALD_SRC = REPO_ROOT / "src" / "shared" / "packages" / "pyforge-herald" / "src"
if str(_HERALD_SRC) not in sys.path:
    sys.path.insert(0, str(_HERALD_SRC))

import deck_trio  # noqa: E402
from pyforge.herald import stamps  # noqa: E402

# Captured before any fixture monkeypatches ``deck_trio.measure_height`` (the
# ``root`` fixture below does, for every other test) -- the real-playwright-shape
# tests need to call the genuine function, not whatever the module attribute
# currently points to.
_REAL_MEASURE_HEIGHT = deck_trio.measure_height

MEASURED_HEIGHT = 4242

# A minimal but structurally representative standalone poster: DOCTYPE/html/head
# with meta+title+3 font/stylesheet <link> tags + one <style> block, then a body
# whose own <body ...> tag carries an attribute (dropped by the transform -- only
# the body's INNER content is copied) wrapping a 1240px content div.
POSTER = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alpha — Infographic</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="">
<link href="https://fonts.googleapis.com/css2?family=Archivo&amp;display=swap" rel="stylesheet">
<style>
  body { margin: 0; background: #eee; }
  .x { color: red; }
</style>
</head>
<body style="margin:0; background:#eae9e9;">
<div style="width:1240px; margin:0 auto;">
  <h1>Alpha</h1>
  <p>content</p>
</div>
</body>
</html>
"""

NO_STYLE_POSTER = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo">
</head>
<body>
<div style="width:1240px;">no style block here</div>
</body>
</html>
"""

# A synthetic standalone with two act bands and three numbered sections, in
# document order -- body's direct children are the acts/sections themselves
# (no wrapping content div), so there is no content before the first item or
# after the last: the clean "no masthead / no closing band" baseline for
# --deck happy-path/idempotency/combined-flag tests.
DECK_POSTER = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Zeta — Infographic</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<style>
  body { margin: 0; background: #eee; }
  .act { background: #201e1d; color: #f3f2f2; }
</style>
</head>
<body>
<div class="act">
  <span class="lbl">ACT I</span>
  <span class="ttl">Opening</span>
</div>
<section class="sec">
  <div class="sechead"><span class="num">01</span><h2>First section</h2></div>
  <p>Some content.</p>
</section>
<section class="sec">
  <div class="sechead"><span class="num">02</span><h2>Second section</h2></div>
  <p>More content.</p>
</section>
<div class="act">
  <span class="lbl">ACT II</span>
  <span class="ttl">Closing</span>
</div>
<section class="sec">
  <div class="sechead"><span class="num">03</span><h2>Third section</h2></div>
  <p>Even more content.</p>
</section>
</body>
</html>
"""

# Carries real masthead content before the first act, a non-numbered mid-deck
# banner (no .num, no class="sec" -- the "doctrine band" shape) BETWEEN two
# real sections, and a closing band after the last section -- exercises the
# masthead/closing-band bookends and the mid-deck-banner exclusion together.
BOOKEND_POSTER = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  .act { background: #201e1d; }
</style>
</head>
<body>
<header>Masthead content for Eta.</header>
<div class="act">
  <span class="lbl">ACT I</span>
  <span class="ttl">Opening</span>
</div>
<section class="sec">
  <div class="sechead"><span class="num">01</span><h2>First section</h2></div>
  <p>Some content.</p>
</section>
<section class="sec">
  <div class="sechead"><span class="num">02</span><h2>Second section</h2></div>
  <p>More content.</p>
</section>
<section style="background:#201e1d;">
  <div>The doctrine band -- not numbered, must not become a slide.</div>
</section>
<div class="act">
  <span class="lbl">ACT II</span>
  <span class="ttl">Closing</span>
</div>
<section class="sec">
  <div class="sechead"><span class="num">03</span><h2>Third section</h2></div>
  <p>Even more content.</p>
</section>
<section style="background:#ec3013;">
  <div>The creed -- closing band content.</div>
</section>
</body>
</html>
"""

# Same masthead/act/section/closing shape as BOOKEND_POSTER, but wrapped
# ENTIRELY in one ambient page-frame div -- the family's own standard
# authoring template (infographic-standard.md), and the live Warden
# standalone's own real shape. A naive body_start/body_end slice cuts
# through this div's own tag pair: the masthead ships with its opening tag
# unclosed, the closing band with its closing tag orphaned. Exercises the
# ambient-wrapper-exclusion fix (third review pass, 2026-09-15).
WRAPPED_BOOKEND_POSTER = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  .act { background: #201e1d; }
</style>
</head>
<body>
<div style="width:1240px; margin:0 auto; padding:56px 56px 0;">
  <header>Masthead content for Mu.</header>
  <div class="act">
    <span class="lbl">ACT I</span>
    <span class="ttl">Opening</span>
  </div>
  <section class="sec">
    <div class="sechead"><span class="num">01</span><h2>First section</h2></div>
    <p>Some content.</p>
  </section>
  <div class="act">
    <span class="lbl">ACT II</span>
    <span class="ttl">Closing</span>
  </div>
  <section class="sec">
    <div class="sechead"><span class="num">02</span><h2>Second section</h2></div>
    <p>More content.</p>
  </section>
  <section style="background:#ec3013;">
    <div>The creed -- closing band content.</div>
  </section>
</div>
</body>
</html>
"""

# HTML5 void elements inside numbered sections: a bare <br> nested inside a
# child (five of the six real posters that derive today carry bare <br>
# inside their .sec sections -- doctor 8, mason 9, scribe 6, steward 27,
# warden 3) and a self-closing <hr/> as a section's own direct child.
# _DeckStructure's depth stack must never push a void tag (there is no
# closing tag to pop it), or the section never closes at its own depth and
# every later section silently vanishes -- with no fixture carrying one, a
# regression in _VOID_ELEMENTS kept the suite green while the live posters
# lost roughly half their sections (Verification Gap, follow-up review
# pass, 2026-09-15).
VOID_CHILDREN_POSTER = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>.act { padding: 0; }</style>
</head>
<body>
<div class="act">
  <span class="lbl">ACT I</span>
  <span class="ttl">Opening</span>
</div>
<section class="sec">
  <div class="sechead"><span class="num">01</span><h2>Breaks and rules</h2></div>
  <p>Line one<br>Line two</p>
  <hr/>
  <p>After the rule.</p>
</section>
<section class="sec">
  <div class="sechead"><span class="num">02</span><h2>Plain</h2></div>
  <p>Plain content.</p>
</section>
</body>
</html>
"""

# An act label and a section heading carrying an HTML entity -- the live
# Warden poster's own "Local &amp; workstation mode" heading shape. handle_data
# hands _DeckStructure the DECODED text ("&"), so _escape_attr must re-escape
# it on the way back into data-label="..." or the attribute is malformed.
ENTITY_LABEL_POSTER = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>.act { padding: 0; }</style>
</head>
<body>
<div class="act">
  <span class="lbl">ACT I &amp; only</span>
  <span class="ttl">Opening</span>
</div>
<section class="sec">
  <div class="sechead"><span class="num">01</span><h2>Local &amp; workstation mode</h2></div>
  <p>content</p>
</section>
</body>
</html>
"""

# No <div class="act"> anywhere -- the "no act bands" refusal row.
NO_ACTS_POSTER = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>.sec { padding: 0; }</style>
</head>
<body>
<section class="sec">
  <div class="sechead"><span class="num">01</span><h2>Only section</h2></div>
  <p>content</p>
</section>
</body>
</html>
"""

# No <section class="sec"> anywhere -- the "no numbered sections" refusal row.
NO_SECTIONS_POSTER = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>.act { padding: 0; }</style>
</head>
<body>
<div class="act">
  <span class="lbl">ACT I</span>
</div>
</body>
</html>
"""

# An act whose .lbl span is empty -- the "empty act label" refusal row.
EMPTY_ACT_LABEL_POSTER = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>.act { padding: 0; }</style>
</head>
<body>
<div class="act">
  <span class="lbl"></span>
  <span class="ttl">Opening</span>
</div>
<section class="sec">
  <div class="sechead"><span class="num">01</span><h2>Only section</h2></div>
  <p>content</p>
</section>
</body>
</html>
"""

# A section with a direct child (so it is NOT the zero-children case) but no
# <h2> anywhere -- isolates the "empty section label" refusal row from the
# "zero direct children" one.
EMPTY_SECTION_HEADING_POSTER = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>.sec { padding: 0; }</style>
</head>
<body>
<div class="act">
  <span class="lbl">ACT I</span>
</div>
<section class="sec">
  <p>A paragraph but no h2 heading anywhere.</p>
</section>
</body>
</html>
"""

# A numbered section with literally zero direct children -- the "zero direct
# children" refusal row.
ZERO_CHILDREN_SECTION_POSTER = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>.sec { padding: 0; }</style>
</head>
<body>
<div class="act">
  <span class="lbl">ACT I</span>
</div>
<section class="sec"></section>
</body>
</html>
"""

# One section whose direct children (sechead + 3 paragraphs) overflow the
# slide budget once packed -- exercises the split-at-child-boundaries path.
# Carries one act band too so it satisfies the "no act bands" precondition.
OVERSIZED_POSTER = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>.sec { padding: 0; }</style>
</head>
<body>
<div class="act">
  <span class="lbl">ACT I</span>
</div>
<section class="sec">
  <div class="sechead"><span class="num">01</span><h2>Busy section</h2></div>
  <p>Para A</p>
  <p>Para B</p>
  <p>Para C</p>
</section>
</body>
</html>
"""

# One direct child that alone exceeds the budget -- the "single child alone
# exceeds budget" best-effort row (no deeper split attempted). Carries one
# act band too so it satisfies the "no act bands" precondition.
SINGLE_CHILD_OVERSIZED_POSTER = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>.sec { padding: 0; }</style>
</head>
<body>
<div class="act">
  <span class="lbl">ACT I</span>
</div>
<section class="sec">
  <div class="sechead"><span class="num">01</span><h2>Giant section</h2></div>
  <div>Enormous single block</div>
</section>
</body>
</html>
"""

# A section whose ONLY direct child (not the second of two, unlike
# SINGLE_CHILD_OVERSIZED_POSTER above) exceeds the budget -- _pack_children on
# a length-1 list always yields exactly one group, so this must produce one
# plain slide with no "(cont.)" suffix.
ONE_CHILD_OVERSIZED_POSTER = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>.sec { padding: 0; }</style>
</head>
<body>
<div class="act">
  <span class="lbl">ACT I</span>
</div>
<section class="sec">
  <div><h2>Solo section</h2> Only child, alone exceeds the slide budget.</div>
</section>
</body>
</html>
"""

# Three sections where only the middle one overflows -- exercises the
# oversized-section matrix row's own "other sections unaffected" clause.
MULTI_SECTION_ONE_OVERSIZED_POSTER = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>.sec { padding: 0; }</style>
</head>
<body>
<div class="act">
  <span class="lbl">ACT I</span>
</div>
<section class="sec">
  <div class="sechead"><span class="num">01</span><h2>Calm section</h2></div>
  <p>Fits fine.</p>
</section>
<section class="sec">
  <div class="sechead"><span class="num">02</span><h2>Busy section</h2></div>
  <p>Para A</p>
  <p>Para B</p>
  <p>Para C</p>
</section>
<section class="sec">
  <div class="sechead"><span class="num">03</span><h2>Also calm</h2></div>
  <p>Also fits fine.</p>
</section>
</body>
</html>
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _init_git_repo(root: Path) -> None:
    """Mirrors ``test_deck_pipeline.py``'s own helper of the same name --
    ``stamps.write_stamp`` (called after every derived write since Story
    23.5) shells real ``git`` commands, so every test that reaches a write
    needs a real, throwaway git repo under it."""
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=root, check=True)


@pytest.fixture
def root(tmp_path, monkeypatch) -> Path:
    """A synthetic repo with one deck (``pyforge-alpha``) carrying a standalone
    poster; ``deck_trio.ROOT``, ``deck_trio.measure_height`` and
    ``deck_trio.measure_all_sections`` are monkeypatched so every test runs
    offline against tmp_path, with no live browser. The default
    ``measure_all_sections`` reports every section as fitting (total=0), so
    most --deck tests need not think about splitting unless they override it.
    Also a real (throwaway) git repo (Story 23.5) -- see ``_init_git_repo``."""
    _write(tmp_path / "presentations/pyforge-alpha/project/Alpha Infographic standalone.html", POSTER)
    _init_git_repo(tmp_path)
    monkeypatch.setattr(deck_trio, "ROOT", tmp_path)
    monkeypatch.setattr(deck_trio, "measure_height", lambda poster: MEASURED_HEIGHT)
    monkeypatch.setattr(
        deck_trio,
        "measure_all_sections",
        lambda sections, poster_text, helmet_content: [(0, [0] * len(s.children)) for s in sections],
    )
    return tmp_path


def _head_path(root: Path) -> Path:
    return root / "presentations/pyforge-alpha/project/Alpha - Infographic.dc.html"


def _standalone_path(root: Path) -> Path:
    return root / "presentations/pyforge-alpha/project/Alpha Infographic standalone.html"


def _deck_path_for(root: Path, slug: str, persona: str) -> Path:
    return root / f"presentations/{slug}/project/{persona}{deck_trio.DECK_SUFFIX}"


# --------------------------------------------------------------- happy path

def test_happy_path_first_run_writes_derived_head(root, capsys):
    assert deck_trio.main(["pyforge-alpha", "--head"]) == 0
    out = capsys.readouterr().out
    assert "wrote" in out
    assert "Alpha - Infographic.dc.html" in out

    text = _head_path(root).read_text(encoding="utf-8")
    # Structural markers the acceptance criteria name explicitly.
    assert "<x-dc>" in text
    assert '<script src="./support.js"></script>' in text
    assert "data-dc-script" in text
    assert (
        f'data-props="{{&quot;$preview&quot;:{{&quot;width&quot;:1240,'
        f'&quot;height&quot;:{MEASURED_HEIGHT}}}}}"' in text
    )
    # The standalone's own font/stylesheet <link> tags and <style> block moved
    # into <helmet>, verbatim.
    assert '<link rel="preconnect" href="https://fonts.googleapis.com">' in text
    assert '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="">' in text
    assert ".x { color: red; }" in text
    assert "<helmet>" in text and text.index("<helmet>") < text.index(".x { color: red; }")
    assert text.index(".x { color: red; }") < text.index("</helmet>")
    # The body's inner content is byte-identical to the standalone's -- but the
    # <body ...> tag's own attribute is NOT carried over (only its inner content
    # moves; the tag itself never exists in the head, per the three-way transform).
    assert '<div style="width:1240px; margin:0 auto;">\n  <h1>Alpha</h1>\n  <p>content</p>\n</div>' in text
    assert 'background:#eae9e9' not in text
    # Well-formed: <title> is not part of any of the three named transforms, so
    # it is neither in the outer <head> nor carried into <helmet>.
    assert "<title>" not in text


def test_measure_height_is_called_with_the_standalone_path(root, monkeypatch):
    """The module docstring calls out a specific, easy-to-invert design decision:
    the standalone is measured, never the head. Assert the argument, not just that
    *some* callable was invoked -- the `root` fixture's own lambda ignores it."""
    calls: list[Path] = []

    def _capture(poster: Path) -> int:
        calls.append(poster)
        return MEASURED_HEIGHT

    monkeypatch.setattr(deck_trio, "measure_height", _capture)
    deck_trio.main(["pyforge-alpha", "--head"])
    assert calls == [_standalone_path(root)]


def test_head_body_is_standalone_body_modulo_the_three_transforms(root):
    deck_trio.main(["pyforge-alpha", "--head"])
    head_text = _head_path(root).read_text(encoding="utf-8")
    standalone_text = _standalone_path(root).read_text(encoding="utf-8")
    body_start = standalone_text.index('<div style="width:1240px; margin:0 auto;">')
    body_end = standalone_text.index("</body>")
    standalone_body = standalone_text[body_start:body_end]
    assert standalone_body in head_text


# -------------------------------------------------------------- idempotency

def test_second_run_unchanged_poster_leaves_head_untouched(root, capsys):
    assert deck_trio.main(["pyforge-alpha", "--head"]) == 0
    head = _head_path(root)
    first_bytes = head.read_bytes()
    first_mtime = head.stat().st_mtime_ns

    capsys.readouterr()
    assert deck_trio.main(["pyforge-alpha", "--head"]) == 0
    out = capsys.readouterr().out
    assert "unchanged" in out

    assert head.read_bytes() == first_bytes
    assert head.stat().st_mtime_ns == first_mtime


def test_transform_is_a_pure_function_of_poster_bytes(root):
    """Rerunning against byte-identical poster content produces byte-identical
    head output (Boundaries & Constraints, Always #2)."""
    deck_trio.main(["pyforge-alpha", "--head"])
    first = _head_path(root).read_bytes()
    _head_path(root).unlink()
    deck_trio.main(["pyforge-alpha", "--head"])
    assert _head_path(root).read_bytes() == first


# ------------------------------------------------------------------ refusals

def test_missing_poster_exits_two_and_writes_nothing(root, capsys):
    with pytest.raises(SystemExit) as exc:
        deck_trio.main(["pyforge-nope", "--head"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "no poster" in err
    assert "presentations/pyforge-nope/project/* Infographic standalone.html" in err
    assert not (root / "presentations/pyforge-nope").exists()


def test_ambiguous_poster_exits_two_and_writes_nothing(root, capsys):
    _write(root / "presentations/pyforge-alpha/project/Zulu Infographic standalone.html", POSTER)
    with pytest.raises(SystemExit) as exc:
        deck_trio.main(["pyforge-alpha", "--head"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "ambiguous poster" in err
    assert "Alpha Infographic standalone.html" in err
    assert "Zulu Infographic standalone.html" in err
    assert not _head_path(root).exists()
    assert not (root / "presentations/pyforge-alpha/project/Zulu - Infographic.dc.html").exists()


def test_style_block_unlocatable_exits_two_and_writes_nothing(root, capsys):
    _write(root / "presentations/pyforge-alpha/project/Alpha Infographic standalone.html", NO_STYLE_POSTER)
    with pytest.raises(SystemExit) as exc:
        deck_trio.main(["pyforge-alpha", "--head"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "<style>" in err
    assert not _head_path(root).exists()


def test_neither_head_nor_deck_given_names_the_fix(root, capsys):
    """--head is no longer individually required (Boundaries & Constraints,
    Always #8: the two flags are independently combinable) -- but at least
    one of --head/--deck must be given, and the refusal names the fix."""
    with pytest.raises(SystemExit) as exc:
        deck_trio.main(["pyforge-alpha"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "specify --head and/or --deck" in err
    assert not _head_path(root).exists()


def test_non_utf8_poster_exits_two_and_writes_nothing(root, capsys):
    _standalone_path(root).write_bytes(b"\xff\xfe not valid utf-8")
    with pytest.raises(SystemExit) as exc:
        deck_trio.main(["pyforge-alpha", "--head"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "not UTF-8" in err
    assert not _head_path(root).exists()


def test_main_reports_measure_height_failure_as_exit_two(root, monkeypatch, capsys):
    """A ``measure_height`` failure (browser unavailable, navigation timeout,
    etc.) must become the same clean ``ap.error`` refusal as every other
    malformed-input case -- not an unhandled traceback."""

    def _raise(poster):
        raise RuntimeError("no usable chromium: synthetic failure")

    monkeypatch.setattr(deck_trio, "measure_height", _raise)
    with pytest.raises(SystemExit) as exc:
        deck_trio.main(["pyforge-alpha", "--head"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "no usable chromium" in err
    assert not _head_path(root).exists()


# ------------------------------------------------------- link capture scope

def test_non_font_link_is_still_swept_into_helmet(root):
    """Documents current, deliberate behavior (Review pass, 2026-09-14): link
    capture is not filtered by ``rel`` -- every real poster's ``<head>`` only
    ever carries font/stylesheet links today, so a ``rel`` filter would be
    speculative complexity with zero live instances. A non-font/stylesheet
    link is still relocated into ``<helmet>`` verbatim, same as any other."""
    poster_with_icon = POSTER.replace(
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="icon" href="favicon.ico">',
    )
    _write(_standalone_path(root), poster_with_icon)
    deck_trio.main(["pyforge-alpha", "--head"])
    text = _head_path(root).read_text(encoding="utf-8")
    assert '<link rel="icon" href="favicon.ico">' in text
    assert (
        text.index("<helmet>")
        < text.index('<link rel="icon" href="favicon.ico">')
        < text.index("</helmet>")
    )


# ------------------------------------------------------ --deck happy path

def test_deck_happy_path_first_run_writes_derived_deck(root, capsys):
    _write(root / "presentations/pyforge-zeta/project/Zeta Infographic standalone.html", DECK_POSTER)
    assert deck_trio.main(["pyforge-zeta", "--deck"]) == 0
    out = capsys.readouterr().out
    assert "wrote" in out
    assert "Zeta - Infographic Deck.dc.html" in out

    deck_path = _deck_path_for(root, "pyforge-zeta", "Zeta")
    text = deck_path.read_text(encoding="utf-8")
    # Boundaries & Constraints, Always #6: the established 14-file skeleton.
    assert '<script src="./support.js"></script>' in text
    assert "<x-dc>" in text and "<helmet>" in text
    assert (
        '<x-import component-from-global-scope="deck-stage" from="./deck-stage.js" '
        'width="1920" height="1080" hint-size="100%,100%" data-uneditable="">' in text
    )
    # Acceptance: no masthead/closing content in this poster, so slide count ==
    # act-band count + numbered-section count, and every slide has a label.
    assert text.count("<section data-label=") == 5  # 2 acts + 3 sections
    assert 'data-label=""' not in text
    assert 'data-label="Cover"' not in text
    assert 'data-label="Close"' not in text
    assert 'data-label="ACT I"' in text
    assert 'data-label="ACT II"' in text
    assert 'data-label="First section"' in text
    assert 'data-label="Second section"' in text
    assert 'data-label="Third section"' in text
    # Never fabricate data-speaker-notes (Never #4).
    assert "data-speaker-notes" not in text
    # The act's own full outer span is wrapped verbatim.
    assert '<div class="act">' in text
    assert "<p>Some content.</p>" in text
    # Verification Gap (follow-up review pass, 2026-09-15): the poster's own
    # <link>/<style> content must land INSIDE <helmet> (Always #3 -- the
    # same relocation --head performs, asserted the same way its happy-path
    # test does), and every slide must carry the family's page frame
    # (Always #8) -- a deck emitting an empty helmet or dropping the frame
    # div previously passed this test unchanged.
    assert '<link rel="preconnect" href="https://fonts.googleapis.com">' in text
    assert ".act { background: #201e1d; color: #f3f2f2; }" in text
    assert (
        text.index("<helmet>")
        < text.index('<link rel="preconnect" href="https://fonts.googleapis.com">')
        < text.index(".act { background: #201e1d; color: #f3f2f2; }")
        < text.index("</helmet>")
    )
    assert text.count(f'<div style="{deck_trio.PAGE_FRAME_STYLE}">') == 5  # one per slide


def test_deck_and_head_together_derive_both_in_one_invocation(root):
    _write(root / "presentations/pyforge-zeta/project/Zeta Infographic standalone.html", DECK_POSTER)
    assert deck_trio.main(["pyforge-zeta", "--head", "--deck"]) == 0
    assert (root / "presentations/pyforge-zeta/project/Zeta - Infographic.dc.html").is_file()
    assert _deck_path_for(root, "pyforge-zeta", "Zeta").is_file()


def test_deck_only_does_not_also_write_head(root):
    """Verification Gap (Review pass, 2026-09-14): assert the head artifact's
    absence directly, not merely by a substring check on stdout."""
    _write(root / "presentations/pyforge-zeta/project/Zeta Infographic standalone.html", DECK_POSTER)
    assert deck_trio.main(["pyforge-zeta", "--deck"]) == 0
    assert not (root / "presentations/pyforge-zeta/project/Zeta - Infographic.dc.html").exists()


# ----------------------------------------------------- --deck idempotency

def test_deck_second_run_unchanged_poster_leaves_deck_untouched(root, capsys):
    _write(root / "presentations/pyforge-zeta/project/Zeta Infographic standalone.html", DECK_POSTER)
    assert deck_trio.main(["pyforge-zeta", "--deck"]) == 0
    deck_path = _deck_path_for(root, "pyforge-zeta", "Zeta")
    first_bytes = deck_path.read_bytes()
    first_mtime = deck_path.stat().st_mtime_ns

    capsys.readouterr()
    assert deck_trio.main(["pyforge-zeta", "--deck"]) == 0
    out = capsys.readouterr().out
    assert "unchanged" in out

    assert deck_path.read_bytes() == first_bytes
    assert deck_path.stat().st_mtime_ns == first_mtime


# ------------------------------------------------ --deck masthead/closing

def test_deck_masthead_present_becomes_first_cover_slide(root):
    _write(root / "presentations/pyforge-eta/project/Eta Infographic standalone.html", BOOKEND_POSTER)
    assert deck_trio.main(["pyforge-eta", "--deck"]) == 0
    text = _deck_path_for(root, "pyforge-eta", "Eta").read_text(encoding="utf-8")
    assert "Masthead content for Eta." in text
    assert text.index('data-label="Cover"') < text.index('data-label="ACT I"')
    # The masthead is the FIRST slide, never split.
    assert text.index('<section data-label="Cover"') == text.index("<section data-label=")


def test_deck_masthead_absent_no_cover_slide(root):
    _write(root / "presentations/pyforge-zeta/project/Zeta Infographic standalone.html", DECK_POSTER)
    assert deck_trio.main(["pyforge-zeta", "--deck"]) == 0
    text = _deck_path_for(root, "pyforge-zeta", "Zeta").read_text(encoding="utf-8")
    assert 'data-label="Cover"' not in text


def test_deck_closing_band_present_becomes_last_close_slide(root):
    _write(root / "presentations/pyforge-eta/project/Eta Infographic standalone.html", BOOKEND_POSTER)
    assert deck_trio.main(["pyforge-eta", "--deck"]) == 0
    text = _deck_path_for(root, "pyforge-eta", "Eta").read_text(encoding="utf-8")
    assert "The creed -- closing band content." in text
    assert text.rindex('data-label="Close"') > text.rindex('data-label="Third section"')


def test_deck_closing_band_absent_no_close_slide(root):
    _write(root / "presentations/pyforge-zeta/project/Zeta Infographic standalone.html", DECK_POSTER)
    assert deck_trio.main(["pyforge-zeta", "--deck"]) == 0
    text = _deck_path_for(root, "pyforge-zeta", "Zeta").read_text(encoding="utf-8")
    assert 'data-label="Close"' not in text


def test_deck_ambient_wrapper_excluded_from_masthead_and_closing_slides(root):
    """High-severity fix (third review pass, 2026-09-15, ambient-wrapper
    exclusion): the family's own standard authoring template wraps the
    ENTIRE body -- masthead through closing band -- in one page-frame div
    (the live Warden standalone's own real shape). A naive
    body_start/body_end slice cuts through that div's own tag pair,
    shipping the Cover slide with an unclosed <div> and the Close slide
    with an orphaned </div>. Assert both derived bookend slides carry
    balanced div tags -- proof the ambient wrapper was excluded, not
    sliced through. (The no-wrapper case, BOOKEND_POSTER, is already
    covered by the masthead/closing-band-present tests above -- the
    fallback path is unchanged.)"""
    _write(root / "presentations/pyforge-mu/project/Mu Infographic standalone.html", WRAPPED_BOOKEND_POSTER)
    assert deck_trio.main(["pyforge-mu", "--deck"]) == 0
    text = _deck_path_for(root, "pyforge-mu", "Mu").read_text(encoding="utf-8")

    cover_start = text.index('<section data-label="Cover"')
    act_i_start = text.index('<section data-label="ACT I"')
    cover_slide = text[cover_start:act_i_start]
    assert "Masthead content for Mu." in cover_slide
    assert cover_slide.count("<div") == cover_slide.count("</div>")

    close_start = text.index('<section data-label="Close"')
    close_slide = text[close_start:]
    assert "The creed -- closing band content." in close_slide
    assert close_slide.count("<div") == close_slide.count("</div>")


def test_deck_ambient_wrapper_with_gt_in_attribute_is_sliced_at_its_real_end(root):
    """The wrapper's own open-tag end offset comes from ``get_starttag_text()``
    (the same exact-source technique ``_PosterStructure`` uses), not a naive
    ``find(">")`` -- a ``>`` inside a quoted attribute value would otherwise
    end the span early and ship the Cover slide opening with the attribute's
    own tail as literal text (Blind Hunter + Edge Case Hunter, follow-up
    review pass, 2026-09-15)."""
    poster = WRAPPED_BOOKEND_POSTER.replace(
        '<div style="width:1240px; margin:0 auto; padding:56px 56px 0;">',
        '<div data-note="a > b" style="width:1240px; margin:0 auto; padding:56px 56px 0;">',
    )
    _write(root / "presentations/pyforge-mu/project/Mu Infographic standalone.html", poster)
    assert deck_trio.main(["pyforge-mu", "--deck"]) == 0
    text = _deck_path_for(root, "pyforge-mu", "Mu").read_text(encoding="utf-8")
    cover_slide = text[text.index('<section data-label="Cover"') : text.index('<section data-label="ACT I"')]
    assert "Masthead content for Mu." in cover_slide
    assert ' b"' not in cover_slide
    assert "data-note" not in cover_slide
    assert cover_slide.count("<div") == cover_slide.count("</div>")


def test_deck_mid_deck_banner_produces_no_slide(root):
    """Never (Boundaries & Constraints): a non-numbered full-bleed banner
    sitting BETWEEN act/section elements is neither a masthead, a closing
    band, nor a numbered section -- it produces no slide and its content is
    dropped, not merged into a neighbor."""
    _write(root / "presentations/pyforge-eta/project/Eta Infographic standalone.html", BOOKEND_POSTER)
    assert deck_trio.main(["pyforge-eta", "--deck"]) == 0
    text = _deck_path_for(root, "pyforge-eta", "Eta").read_text(encoding="utf-8")
    assert "doctrine band" not in text


def test_deck_slide_count_matches_formula_with_bookends(root):
    """Acceptance: slide count == acts + sections + 1 (masthead) + 1 (closing)."""
    _write(root / "presentations/pyforge-eta/project/Eta Infographic standalone.html", BOOKEND_POSTER)
    assert deck_trio.main(["pyforge-eta", "--deck"]) == 0
    text = _deck_path_for(root, "pyforge-eta", "Eta").read_text(encoding="utf-8")
    assert text.count("<section data-label=") == 7  # 2 acts + 3 sections + Cover + Close
    assert 'data-label=""' not in text


def test_deck_void_elements_inside_sections_do_not_disturb_section_boundaries(root):
    """Verification Gap (follow-up review pass, 2026-09-15): the void-element
    depth guard (``_VOID_ELEMENTS``) is load-bearing on five of the six real
    posters that derive today (bare ``<br>`` inside ``.sec`` sections), yet no
    fixture carried one -- dropping ``"br"`` from the set kept the suite green
    while the live posters silently lost roughly half their sections. Pin the
    parser directly (section and per-section direct-child counts) AND the
    derived slide count, so either regression fails loudly."""
    parser = deck_trio._DeckStructure(VOID_CHILDREN_POSTER)
    parser.feed(VOID_CHILDREN_POSTER)
    parser.close()
    assert len(parser.acts) == 1
    assert [s.heading for s in parser.sections] == ["Breaks and rules", "Plain"]
    # sechead div + <p>..<br>..</p> + self-closing <hr/> + <p> = 4 direct
    # children; the bare <br> nested inside the <p> is not one of them.
    assert [len(s.children) for s in parser.sections] == [4, 2]

    _write(root / "presentations/pyforge-nu/project/Nu Infographic standalone.html", VOID_CHILDREN_POSTER)
    assert deck_trio.main(["pyforge-nu", "--deck"]) == 0
    text = _deck_path_for(root, "pyforge-nu", "Nu").read_text(encoding="utf-8")
    assert text.count("<section data-label=") == 3  # 1 act + 2 sections
    assert 'data-label="Breaks and rules"' in text
    assert 'data-label="Plain"' in text
    assert "<p>Line one<br>Line two</p>" in text
    assert "<hr/>" in text
    assert "<p>After the rule.</p>" in text


def test_deck_entity_in_label_is_re_escaped_into_data_label(root):
    """``handle_data`` hands the parser decoded text, so a heading authored as
    ``Local &amp; workstation mode`` (the live Warden poster's own shape) must
    come back out of ``_escape_attr`` as ``&amp;`` inside ``data-label`` -- a
    raw ``&`` there is a malformed attribute (Blind Hunter, follow-up review
    pass, 2026-09-15: no fixture exercised the round trip)."""
    _write(root / "presentations/pyforge-xi/project/Xi Infographic standalone.html", ENTITY_LABEL_POSTER)
    assert deck_trio.main(["pyforge-xi", "--deck"]) == 0
    text = _deck_path_for(root, "pyforge-xi", "Xi").read_text(encoding="utf-8")
    assert 'data-label="ACT I &amp; only"' in text
    assert 'data-label="Local &amp; workstation mode"' in text
    assert 'data-label="ACT I & only"' not in text
    assert 'data-label="Local & workstation mode"' not in text


# --------------------------------------------------------- --deck refusals

def test_deck_missing_poster_exits_two_and_writes_nothing(root, capsys):
    with pytest.raises(SystemExit) as exc:
        deck_trio.main(["pyforge-nope", "--deck"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "no poster" in err
    assert not (root / "presentations/pyforge-nope").exists()


def test_deck_ambiguous_poster_exits_two_and_writes_nothing(root, capsys):
    _write(root / "presentations/pyforge-alpha/project/Zulu Infographic standalone.html", POSTER)
    with pytest.raises(SystemExit) as exc:
        deck_trio.main(["pyforge-alpha", "--deck"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "ambiguous poster" in err
    assert not _deck_path_for(root, "pyforge-alpha", "Alpha").exists()


def test_deck_style_block_unlocatable_exits_two_and_writes_nothing(root, capsys):
    """The <style>-block refusal is a SHARED precondition (both --head and
    --deck need the collected helmet content), so it must also gate a
    --deck-only invocation."""
    _write(root / "presentations/pyforge-alpha/project/Alpha Infographic standalone.html", NO_STYLE_POSTER)
    with pytest.raises(SystemExit) as exc:
        deck_trio.main(["pyforge-alpha", "--deck"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "<style>" in err
    assert not _deck_path_for(root, "pyforge-alpha", "Alpha").exists()


def test_deck_no_act_bands_exits_two_names_missing_structure(root, capsys):
    _write(root / "presentations/pyforge-alpha/project/Alpha Infographic standalone.html", NO_ACTS_POSTER)
    with pytest.raises(SystemExit) as exc:
        deck_trio.main(["pyforge-alpha", "--deck"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "act" in err.lower()
    assert not _deck_path_for(root, "pyforge-alpha", "Alpha").exists()


def test_deck_no_numbered_sections_exits_two_names_missing_structure(root, capsys):
    _write(root / "presentations/pyforge-alpha/project/Alpha Infographic standalone.html", NO_SECTIONS_POSTER)
    with pytest.raises(SystemExit) as exc:
        deck_trio.main(["pyforge-alpha", "--deck"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "section" in err.lower()
    assert not _deck_path_for(root, "pyforge-alpha", "Alpha").exists()


def test_deck_empty_act_label_exits_two_and_writes_nothing(root, capsys):
    _write(
        root / "presentations/pyforge-alpha/project/Alpha Infographic standalone.html",
        EMPTY_ACT_LABEL_POSTER,
    )
    with pytest.raises(SystemExit) as exc:
        deck_trio.main(["pyforge-alpha", "--deck"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "empty or missing .lbl label" in err
    assert not _deck_path_for(root, "pyforge-alpha", "Alpha").exists()


def test_deck_empty_section_heading_exits_two_and_writes_nothing(root, capsys):
    _write(
        root / "presentations/pyforge-alpha/project/Alpha Infographic standalone.html",
        EMPTY_SECTION_HEADING_POSTER,
    )
    with pytest.raises(SystemExit) as exc:
        deck_trio.main(["pyforge-alpha", "--deck"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "empty or missing <h2> label" in err
    assert not _deck_path_for(root, "pyforge-alpha", "Alpha").exists()


def test_deck_section_zero_children_exits_two_and_writes_nothing(root, capsys):
    _write(
        root / "presentations/pyforge-alpha/project/Alpha Infographic standalone.html",
        ZERO_CHILDREN_SECTION_POSTER,
    )
    with pytest.raises(SystemExit) as exc:
        deck_trio.main(["pyforge-alpha", "--deck"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "zero direct children" in err
    assert not _deck_path_for(root, "pyforge-alpha", "Alpha").exists()


def test_deck_reports_measure_all_sections_failure_as_exit_two(root, monkeypatch, capsys):
    _write(root / "presentations/pyforge-zeta/project/Zeta Infographic standalone.html", DECK_POSTER)

    def _raise(sections, poster_text, helmet_content):
        raise RuntimeError("no usable chromium: synthetic failure")

    monkeypatch.setattr(deck_trio, "measure_all_sections", _raise)
    with pytest.raises(SystemExit) as exc:
        deck_trio.main(["pyforge-zeta", "--deck"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "no usable chromium" in err
    assert not _deck_path_for(root, "pyforge-zeta", "Zeta").exists()


def test_deck_measure_all_sections_length_mismatch_exits_two(root, monkeypatch, capsys):
    """Never (Boundaries & Constraints): a length mismatch between measured
    and parsed sections must not raise an uncaught exception. Also pins the
    count-agnostic "section(s)" grammar fix (third review pass,
    2026-09-15) -- "measured 1 sections" reads as grammatically wrong."""
    _write(root / "presentations/pyforge-zeta/project/Zeta Infographic standalone.html", DECK_POSTER)
    monkeypatch.setattr(
        deck_trio,
        "measure_all_sections",
        lambda sections, poster_text, helmet_content: [(0, [])],  # DECK_POSTER has 3 sections
    )
    with pytest.raises(SystemExit) as exc:
        deck_trio.main(["pyforge-zeta", "--deck"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "measured 1 section(s)" in err
    assert "parsed 3 section(s)" in err
    assert not _deck_path_for(root, "pyforge-zeta", "Zeta").exists()


def test_head_and_deck_together_deck_failure_leaves_head_unwritten(root, capsys):
    """Boundaries & Constraints, Always #8: when --deck's own precondition
    fails after --head's own would otherwise succeed, --head must not have
    already written its file -- both modes are validated before either is
    written."""
    _write(root / "presentations/pyforge-alpha/project/Alpha Infographic standalone.html", NO_ACTS_POSTER)
    with pytest.raises(SystemExit) as exc:
        deck_trio.main(["pyforge-alpha", "--head", "--deck"])
    assert exc.value.code == 2
    assert not _head_path(root).exists()
    assert not _deck_path_for(root, "pyforge-alpha", "Alpha").exists()


# ------------------------------------------------------ --deck overflow split

def test_oversized_section_splits_at_child_boundaries(root, monkeypatch):
    _write(root / "presentations/pyforge-theta/project/Theta Infographic standalone.html", OVERSIZED_POSTER)
    monkeypatch.setattr(
        deck_trio,
        "measure_all_sections",
        lambda sections, poster_text, helmet_content: [(1300, [100, 400, 400, 400])],
    )
    assert deck_trio.main(["pyforge-theta", "--deck"]) == 0
    text = _deck_path_for(root, "pyforge-theta", "Theta").read_text(encoding="utf-8")

    assert text.count("<section data-label=") == 3  # 1 act + 2 split slides
    assert 'data-label="Busy section"' in text
    assert 'data-label="Busy section (cont. 2/2)"' in text

    slide2_pos = text.index('data-label="Busy section (cont. 2/2)"')
    before, after = text[:slide2_pos], text[slide2_pos:]
    assert "Para A" in before and "Para B" in before
    assert "Para C" not in before
    assert "Para C" in after
    assert "Para A" not in after and "Para B" not in after


def test_single_child_alone_exceeds_budget_becomes_its_own_best_effort_slide(root, monkeypatch):
    _write(
        root / "presentations/pyforge-iota/project/Iota Infographic standalone.html",
        SINGLE_CHILD_OVERSIZED_POSTER,
    )
    monkeypatch.setattr(
        deck_trio,
        "measure_all_sections",
        lambda sections, poster_text, helmet_content: [(2100, [100, 2000])],
    )
    assert deck_trio.main(["pyforge-iota", "--deck"]) == 0
    text = _deck_path_for(root, "pyforge-iota", "Iota").read_text(encoding="utf-8")

    assert text.count("<section data-label=") == 3  # 1 act + 2 split slides
    assert 'data-label="Giant section (cont. 2/2)"' in text
    assert "Enormous single block" in text


def test_section_with_only_one_child_that_alone_exceeds_budget_yields_one_plain_slide(root, monkeypatch):
    """Distinct from the test above: there the oversized child is the SECOND
    of two children in its section, so the section still splits into two
    slides. Here the oversized child is the section's ONLY child --
    ``_pack_children`` on a length-1 list always yields exactly one group
    (Design Notes § Overflow split), so the result must be one plain slide
    carrying the section's own heading, with no "(cont.)" suffix."""
    _write(
        root / "presentations/pyforge-kappa/project/Kappa Infographic standalone.html",
        ONE_CHILD_OVERSIZED_POSTER,
    )
    monkeypatch.setattr(
        deck_trio,
        "measure_all_sections",
        lambda sections, poster_text, helmet_content: [(2000, [2000])],
    )
    assert deck_trio.main(["pyforge-kappa", "--deck"]) == 0
    text = _deck_path_for(root, "pyforge-kappa", "Kappa").read_text(encoding="utf-8")

    assert text.count("<section data-label=") == 2  # 1 act + 1 plain slide, no split
    assert 'data-label="Solo section"' in text
    assert "(cont." not in text
    assert "Only child, alone exceeds the slide budget." in text


def test_oversized_section_does_not_affect_other_sections_in_a_multi_section_poster(root, monkeypatch):
    """The oversized-section matrix row's own "other sections unaffected"
    clause, exercised in a poster with 2+ sections where only the middle one
    overflows -- the existing OVERSIZED_POSTER fixture has exactly one
    section, so it cannot exercise this clause."""
    _write(
        root / "presentations/pyforge-lambda/project/Lambda Infographic standalone.html",
        MULTI_SECTION_ONE_OVERSIZED_POSTER,
    )
    monkeypatch.setattr(
        deck_trio,
        "measure_all_sections",
        lambda sections, poster_text, helmet_content: [
            (100, [50, 50]),
            (1300, [100, 400, 400, 400]),
            (100, [50, 50]),
        ],
    )
    assert deck_trio.main(["pyforge-lambda", "--deck"]) == 0
    text = _deck_path_for(root, "pyforge-lambda", "Lambda").read_text(encoding="utf-8")

    assert text.count("<section data-label=") == 5  # 1 act + 1 + 2 (split) + 1
    assert text.count('data-label="Calm section"') == 1
    assert text.count('data-label="Also calm"') == 1
    assert 'data-label="Busy section"' in text
    assert 'data-label="Busy section (cont. 2/2)"' in text
    assert text.count("(cont.") == 1


def test_pack_children_greedy_budget():
    assert deck_trio._pack_children([100, 400, 400, 400], 1024) == [[0, 1, 2], [3]]
    assert deck_trio._pack_children([100, 2000], 1024) == [[0], [1]]
    assert deck_trio._pack_children([200, 200, 200], 1024) == [[0, 1, 2]]
    assert deck_trio._pack_children([], 1024) == []


# --------------------------------------------------- real playwright shape

class _FakePage:
    """Records every ``goto``/``evaluate`` call so a test can assert
    ``measure_height`` actually wires the networkidle/fonts.ready fix (Review
    pass, 2026-09-14) rather than trusting a wholesale-monkeypatched stand-in."""

    def __init__(self, height: int, calls: list) -> None:
        self._height = height
        self._calls = calls

    def goto(self, url, wait_until=None):  # noqa: D102
        self._calls.append(("goto", url, wait_until))

    def evaluate(self, script):  # noqa: D102
        self._calls.append(("evaluate", script))
        if script == "document.documentElement.scrollHeight":
            return self._height
        return None

    def close(self):  # noqa: D102
        pass


class _FakeBrowser:
    def __init__(self, height: int, calls: list, fail_new_page: bool = False) -> None:
        self._height = height
        self._calls = calls
        self._fail_new_page = fail_new_page

    def new_page(self, viewport=None):  # noqa: D102
        if self._fail_new_page:
            raise RuntimeError("synthetic new_page failure")
        return _FakePage(self._height, self._calls)

    def close(self):  # noqa: D102
        pass


class _FakeChromium:
    def __init__(
        self, height: int, calls: list, launch_raises=None, fail_new_page: bool = False
    ) -> None:
        self._height = height
        self._calls = calls
        self._launch_raises = launch_raises
        self._fail_new_page = fail_new_page

    def launch(self, **kwargs):  # noqa: D102
        if self._launch_raises is not None:
            raise self._launch_raises
        return _FakeBrowser(self._height, self._calls, fail_new_page=self._fail_new_page)


class _FakeBrowserType:
    def __init__(self, chromium: _FakeChromium) -> None:
        self.chromium = chromium


class _FakePlaywrightCtx:
    def __init__(self, chromium: _FakeChromium) -> None:
        self._chromium = chromium

    def __enter__(self):  # noqa: D102
        return _FakeBrowserType(self._chromium)

    def __exit__(self, *exc_info):  # noqa: D102
        return False


def _patch_fake_playwright(monkeypatch, chromium: _FakeChromium) -> None:
    """Installs a fake ``playwright``/``playwright.sync_api`` into
    ``sys.modules`` for the test's duration -- these tests run in the
    ``pyforge-ci`` env (``tests/scripts/`` is deliberately stdlib-only, see
    ``spec-21-1``'s own Code Map), which does not install the real
    ``playwright`` package, so patching its real module in place (the
    ``test_deck_qa.py`` precedent, which runs in an env where playwright IS
    installed) is not available here. ``monkeypatch.setitem`` restores or
    deletes these keys afterward regardless of whether they existed before."""
    fake_pkg = types.ModuleType("playwright")
    fake_sync_api = types.ModuleType("playwright.sync_api")
    fake_sync_api.sync_playwright = lambda: _FakePlaywrightCtx(chromium)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "playwright", fake_pkg)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_sync_api)


def test_measure_height_waits_for_networkidle_and_fonts_ready(root, monkeypatch):
    """Exercises the real ``measure_height`` (not a wholesale monkeypatch): a
    2026-09-14 review pass found the height measurement non-deterministic
    run-to-run because it never waited for fonts/network to settle. Assert
    the fix is actually wired -- ``page.goto`` receives
    ``wait_until="networkidle"`` and ``document.fonts.ready`` is evaluated
    before the height is read."""
    calls: list = []
    chromium = _FakeChromium(MEASURED_HEIGHT, calls)
    _patch_fake_playwright(monkeypatch, chromium)

    height = _REAL_MEASURE_HEIGHT(_standalone_path(root))

    assert height == MEASURED_HEIGHT
    assert calls[0][0] == "goto"
    assert calls[0][2] == "networkidle"
    assert ("evaluate", "document.fonts.ready") in calls
    scroll_index = calls.index(("evaluate", "document.documentElement.scrollHeight"))
    fonts_index = calls.index(("evaluate", "document.fonts.ready"))
    assert fonts_index < scroll_index


def test_measure_height_no_usable_chromium_raises_even_on_system_exit(root, monkeypatch):
    """Mirrors pyforge-herald's ``deck_qa.render_gate`` regression test of the
    same name: playwright's own internals have raised ``SystemExit`` live, so
    the launch-fallback except clauses must catch it too, not just
    ``Exception`` -- a bare ``except Exception`` here would let it propagate
    raw instead of the function's own clean ``RuntimeError``."""
    chromium = _FakeChromium(
        MEASURED_HEIGHT, [], launch_raises=SystemExit("playwright internals raised this")
    )
    _patch_fake_playwright(monkeypatch, chromium)

    with pytest.raises(RuntimeError, match="no usable chromium"):
        _REAL_MEASURE_HEIGHT(_standalone_path(root))


def test_new_page_failure_raises_runtime_error(root, monkeypatch):
    chromium = _FakeChromium(MEASURED_HEIGHT, [], fail_new_page=True)
    _patch_fake_playwright(monkeypatch, chromium)

    with pytest.raises(RuntimeError, match="page creation failed"):
        _REAL_MEASURE_HEIGHT(_standalone_path(root))


# --------------------------------------------- --deck real playwright shape

class _FakeDeckPage:
    """Records every ``set_content``/``evaluate`` call so a test can assert
    ``measure_section`` actually wires the same networkidle/fonts.ready fix
    ``measure_height`` needed (Design Notes § One browser launch per --deck
    run), rather than trusting a wholesale-monkeypatched stand-in. Also
    captures the last rendered HTML so a test can assert the measurement
    container carries the id ``_MEASURE_SCRIPT`` looks up. ``raise_on`` names
    a page method that raises instead, for the failure-path test."""

    def __init__(
        self, total: int, children: list, calls: list, raise_on: str | None = None
    ) -> None:
        self._total = total
        self._children = children
        self._calls = calls
        self._raise_on = raise_on
        self.last_html: str | None = None

    def set_content(self, html, wait_until=None):  # noqa: D102
        if self._raise_on == "set_content":
            raise RuntimeError("synthetic set_content failure")
        self.last_html = html
        self._calls.append(("set_content", wait_until))

    def evaluate(self, script):  # noqa: D102
        self._calls.append(("evaluate", script))
        if script == deck_trio._MEASURE_SCRIPT:
            return {"total": self._total, "children": self._children}
        return None

    def close(self):  # noqa: D102
        pass


def test_measure_section_waits_for_networkidle_and_fonts_ready():
    """Exercises the real ``measure_section`` (not a wholesale monkeypatch),
    mirroring ``test_measure_height_waits_for_networkidle_and_fonts_ready``:
    ``page.set_content`` must receive ``wait_until="networkidle"`` and
    ``document.fonts.ready`` must be evaluated before the layout is read --
    an unfixed font-load race here could change which children land on which
    slide between runs (Design Notes § One browser launch per --deck run)."""
    calls: list = []
    page = _FakeDeckPage(total=1080, children=[300.4, 299.6], calls=calls)

    total, children = deck_trio.measure_section(page, "<style></style>", ["<p>a</p>", "<p>b</p>"])

    assert total == 1080 - deck_trio.PAGE_FRAME_PADDING_TOP - deck_trio.PAGE_FRAME_PADDING_BOTTOM
    assert children == [300, 300]
    assert calls[0] == ("set_content", "networkidle")
    assert ("evaluate", "document.fonts.ready") in calls
    fonts_index = calls.index(("evaluate", "document.fonts.ready"))
    script_index = calls.index(("evaluate", deck_trio._MEASURE_SCRIPT))
    assert fonts_index < script_index


def test_measure_section_renders_children_inside_the_identified_container():
    """The measurement container must carry ``_MEASURE_CONTAINER_ID`` so
    ``_MEASURE_SCRIPT`` can find it via ``getElementById`` -- the
    margin-collapse-safe height technique (Design Notes § Overflow split)
    reads every child's ``getBoundingClientRect().top``, which needs no
    positioned ancestor (unlike an ``offsetTop`` delta -- an ``HTMLElement``
    property that an inline ``<svg>`` root never carries, seen live against
    the Warden poster's own inline diagrams)."""
    page = _FakeDeckPage(total=100, children=[50], calls=[])
    deck_trio.measure_section(page, "<style></style>", ["<p>a</p>"])
    assert page.last_html is not None
    assert deck_trio._MEASURE_CONTAINER_ID in page.last_html
    assert "<p>a</p>" in page.last_html


def test_measure_section_wraps_page_failure_in_runtime_error():
    """``measure_section``'s own ``except (Exception, SystemExit)`` wrapper
    was never exercised -- every failure-path test monkeypatched
    ``measure_all_sections`` wholesale (Blind Hunter, follow-up review pass,
    2026-09-15). A page-level failure must surface as the tool's own
    ``RuntimeError`` (which ``main()`` turns into exit 2), never a raw
    traceback."""
    page = _FakeDeckPage(total=100, children=[50], calls=[], raise_on="set_content")
    with pytest.raises(RuntimeError, match="section measurement failed"):
        deck_trio.measure_section(page, "<style></style>", ["<p>a</p>"])


def test_measure_all_sections_reuses_one_page_across_every_section(monkeypatch):
    """Design Notes § One browser launch per --deck run: --deck launches
    Chromium ONCE and reuses a single page across every section's
    measurement, unlike measure_height's per-call launch for --head."""
    calls: list = []
    page = _FakeDeckPage(total=100, children=[50], calls=calls)

    class _OnePageBrowser:
        def __init__(self) -> None:
            self.new_page_calls = 0

        def new_page(self, viewport=None):  # noqa: D102
            self.new_page_calls += 1
            return page

        def close(self):  # noqa: D102
            pass

    class _OnePageChromium:
        def __init__(self, browser) -> None:
            self._browser = browser

        def launch(self, **kwargs):  # noqa: D102
            return self._browser

    browser = _OnePageBrowser()
    fake_pkg = types.ModuleType("playwright")
    fake_sync_api = types.ModuleType("playwright.sync_api")
    fake_sync_api.sync_playwright = lambda: _FakePlaywrightCtx(_OnePageChromium(browser))  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "playwright", fake_pkg)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_sync_api)

    sections = [
        deck_trio._Section(heading="A", children=[(0, 1)], span=(0, 2)),
        deck_trio._Section(heading="B", children=[(1, 2)], span=(1, 3)),
    ]
    results = deck_trio.measure_all_sections(sections, "xy", "<style></style>")

    assert browser.new_page_calls == 1
    assert results == [(100 - deck_trio.PAGE_FRAME_PADDING_TOP - deck_trio.PAGE_FRAME_PADDING_BOTTOM, [50])] * 2


def test_measure_all_sections_no_usable_chromium_raises_even_on_system_exit(monkeypatch):
    """Mirrors ``test_measure_height_no_usable_chromium_raises_even_on_system_exit``:
    playwright's own internals have raised ``SystemExit`` live, so the
    launch-fallback except clauses must catch it too."""
    chromium = _FakeChromium(0, [], launch_raises=SystemExit("playwright internals raised this"))
    _patch_fake_playwright(monkeypatch, chromium)

    with pytest.raises(RuntimeError, match="no usable chromium"):
        deck_trio.measure_all_sections([], "", "")


def test_measure_all_sections_new_page_failure_raises_runtime_error(monkeypatch):
    chromium = _FakeChromium(0, [], fail_new_page=True)
    _patch_fake_playwright(monkeypatch, chromium)

    with pytest.raises(RuntimeError, match="page creation failed"):
        deck_trio.measure_all_sections([], "", "")


# --------------------------------------------------------- standalone safety

def test_standalone_is_never_modified_happy_path(root):
    before = _standalone_path(root).read_bytes()
    deck_trio.main(["pyforge-alpha", "--head"])
    assert _standalone_path(root).read_bytes() == before


def test_standalone_is_never_modified_on_refusal(root):
    _write(root / "presentations/pyforge-alpha/project/Alpha Infographic standalone.html", NO_STYLE_POSTER)
    before = _standalone_path(root).read_bytes()
    with pytest.raises(SystemExit):
        deck_trio.main(["pyforge-alpha", "--head"])
    assert _standalone_path(root).read_bytes() == before


def test_deck_standalone_is_never_modified_happy_path(root):
    _write(root / "presentations/pyforge-zeta/project/Zeta Infographic standalone.html", DECK_POSTER)
    before = (root / "presentations/pyforge-zeta/project/Zeta Infographic standalone.html").read_bytes()
    deck_trio.main(["pyforge-zeta", "--deck"])
    assert (root / "presentations/pyforge-zeta/project/Zeta Infographic standalone.html").read_bytes() == before


def test_deck_standalone_is_never_modified_on_refusal(root):
    _write(root / "presentations/pyforge-alpha/project/Alpha Infographic standalone.html", NO_ACTS_POSTER)
    before = _standalone_path(root).read_bytes()
    with pytest.raises(SystemExit):
        deck_trio.main(["pyforge-alpha", "--deck"])
    assert _standalone_path(root).read_bytes() == before


# --------------------------------------------------------------- stamps (23.5)


def test_head_write_lands_a_stamp_sidecar(root):
    deck_trio.main(["pyforge-alpha", "--head"])

    stamp = stamps.read_stamp(_head_path(root))
    assert stamp is not None
    assert stamp.tree
    assert stamp.derived_at
    assert stamp.etag is None  # pyforge-alpha was never seeded in this fixture


def test_deck_write_lands_a_stamp_sidecar(root):
    _write(root / "presentations/pyforge-zeta/project/Zeta Infographic standalone.html", DECK_POSTER)

    deck_trio.main(["pyforge-zeta", "--deck"])

    stamp = stamps.read_stamp(_deck_path_for(root, "pyforge-zeta", "Zeta"))
    assert stamp is not None
    assert stamp.tree


def test_head_and_deck_together_both_get_stamped(root):
    _write(root / "presentations/pyforge-alpha/project/Alpha Infographic standalone.html", DECK_POSTER)

    deck_trio.main(["pyforge-alpha", "--head", "--deck"])

    assert stamps.read_stamp(_head_path(root)) is not None
    assert stamps.read_stamp(_deck_path_for(root, "pyforge-alpha", "Alpha")) is not None


def test_second_unchanged_run_still_refreshes_the_stamp(root, monkeypatch):
    """``_write_if_changed`` skips the rewrite on an unchanged poster, but
    every call still reaches ``stamps.write_stamp`` -- the stamp records
    "derived (or reverified) at this tree", not only "bytes changed"."""
    deck_trio.main(["pyforge-alpha", "--head"])
    first = stamps.read_stamp(_head_path(root))

    calls: list[Path] = []
    real_write_stamp = stamps.write_stamp

    def _spy(artifact_path, **kwargs):
        calls.append(artifact_path)
        return real_write_stamp(artifact_path, **kwargs)

    monkeypatch.setattr(deck_trio.stamps, "write_stamp", _spy)
    deck_trio.main(["pyforge-alpha", "--head"])

    assert calls == [_head_path(root)]
    second = stamps.read_stamp(_head_path(root))
    assert second.tree == first.tree
    assert second.derived_at >= first.derived_at


def test_a_refused_run_writes_no_stamp(root):
    _write(root / "presentations/pyforge-alpha/project/Alpha Infographic standalone.html", NO_STYLE_POSTER)

    with pytest.raises(SystemExit):
        deck_trio.main(["pyforge-alpha", "--head"])

    assert stamps.read_stamp(_head_path(root)) is None
