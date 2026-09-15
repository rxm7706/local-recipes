"""Unit tests for scripts/deck_trio.py (spec-21-1-deck-trio-derives-the-infographic-
head-from-the-standalone, herald Story 21.1): deriving a deck's Infographic HEAD
(``project/<Persona> - Infographic.dc.html``) from its standalone poster via the
three documented mechanical transforms, refusing rather than guessing on malformed
input, and never touching the standalone. Covers every I/O matrix row.

Fixture style mirrors tests/scripts/test_deck_facts.py: a synthetic repo root under
tmp_path, the module reached through sys.path since scripts/ has no __init__.py, and
``deck_trio.ROOT`` / ``deck_trio.measure_height`` monkeypatched so the run is offline,
independent of the live tree, and needs no real browser.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import deck_trio  # noqa: E402

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


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def root(tmp_path, monkeypatch) -> Path:
    """A synthetic repo with one deck (``pyforge-alpha``) carrying a standalone
    poster; ``deck_trio.ROOT`` and ``deck_trio.measure_height`` are monkeypatched
    so every test runs offline against tmp_path, with no live browser."""
    _write(tmp_path / "presentations/pyforge-alpha/project/Alpha Infographic standalone.html", POSTER)
    monkeypatch.setattr(deck_trio, "ROOT", tmp_path)
    monkeypatch.setattr(deck_trio, "measure_height", lambda poster: MEASURED_HEIGHT)
    return tmp_path


def _head_path(root: Path) -> Path:
    return root / "presentations/pyforge-alpha/project/Alpha - Infographic.dc.html"


def _standalone_path(root: Path) -> Path:
    return root / "presentations/pyforge-alpha/project/Alpha Infographic standalone.html"


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


def test_head_flag_is_required(root):
    with pytest.raises(SystemExit) as exc:
        deck_trio.main(["pyforge-alpha"])
    assert exc.value.code == 2
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
