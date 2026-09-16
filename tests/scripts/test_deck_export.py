"""Unit tests for scripts/deck_export.py: regenerating a presentation deck's
derived export artifacts (standalone HTML + two PPTX targets) from its Marp
``.md`` sources via ``marp``.

Fixture style mirrors tests/scripts/test_deck_trio.py: a synthetic repo root
under tmp_path (also a real, throwaway git repo -- Story 23.5's
``stamps.write_stamp`` shells real ``git``), the module reached through
sys.path since scripts/ has no ``__init__.py``, and ``deck_export.ROOT`` /
``deck_export.run_marp`` / ``deck_export.chrome_available`` monkeypatched so
every test runs offline, with no live ``marp`` binary and no live browser.

Covers (Story 23.5): the no-chrome skip guard on the two ``--pptx`` targets
(exit 0, ``derive-skipped: no chrome (<target>)``, no file/stamp for that
target, ``html`` unaffected), and that every produced artifact gets a
``<artifact>.stamp.json`` sidecar.

``pyforge-herald``'s own ``src/`` is not a ``local-recipes`` pixi dependency
(only its ``deck-export``/``deck-trio`` TASKS get a ``PYTHONPATH`` env override
in pixi.toml, per this story) -- a bare ``python -m pytest`` invocation of this
file needs the same path on ``sys.path`` itself, so it is added here too,
mirroring the ``_SCRIPTS_DIR`` insertion just below.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
_HERALD_SRC = REPO_ROOT / "src" / "shared" / "packages" / "pyforge-herald" / "src"
if str(_HERALD_SRC) not in sys.path:
    sys.path.insert(0, str(_HERALD_SRC))

import deck_export  # noqa: E402
from pyforge.herald import stamps  # noqa: E402


def _init_git_repo(root: Path) -> None:
    """Mirrors ``test_deck_pipeline.py``/``test_deck_trio.py``'s own helper
    of the same name -- ``stamps.write_stamp`` shells real ``git``
    commands, so every test that reaches a write needs a real, throwaway
    git repo under it."""
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=root, check=True)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fake_run_marp(calls: list[list[str]]):
    """A ``run_marp`` stand-in: records the exact args and writes a dummy
    file at the ``-o`` target -- every real invocation's last two args are
    ``"-o", <out>``, so ``extra[-1]`` is always the output path."""

    def _run(extra: list[str]) -> None:
        calls.append(list(extra))
        out = Path(extra[-1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"fake-marp-output")

    return _run


@pytest.fixture
def root(tmp_path, monkeypatch) -> Path:
    """A synthetic repo with one deck (``pyforge-alpha``) carrying deck +
    infographic Marp sources; ``deck_export.ROOT`` monkeypatched so every
    test runs against tmp_path, and ``chrome_available`` defaults to
    ``True`` (most tests care about the happy path, not the skip guard)."""
    marp_dir = tmp_path / "presentations/pyforge-alpha/src/marp"
    _write(marp_dir / "pyforge-alpha-deck-2026-01-01.md", "# Deck\n")
    _write(marp_dir / "pyforge-alpha-infographic-2026-01-01.md", "# Infographic\n")
    _init_git_repo(tmp_path)
    monkeypatch.setattr(deck_export, "ROOT", str(tmp_path))
    monkeypatch.setattr(deck_export, "chrome_available", lambda: True)
    return tmp_path


def _run(monkeypatch, argv: list[str]) -> list[list[str]]:
    calls: list[list[str]] = []
    monkeypatch.setattr(deck_export, "run_marp", _fake_run_marp(calls))
    monkeypatch.setattr(sys, "argv", ["deck_export.py", *argv])
    deck_export.main()
    return calls


# --------------------------------------------------------------- happy path


def test_html_target_produces_the_standalone_and_a_stamp(root, monkeypatch):
    calls = _run(monkeypatch, ["pyforge-alpha", "html"])

    out = root / "presentations/pyforge-alpha/src/marp/pyforge-alpha-infographic-standalone-2026-01-01.html"
    src = root / "presentations/pyforge-alpha/src/marp/pyforge-alpha-infographic-2026-01-01.md"
    assert out.is_file()
    assert calls == [[str(src), "-o", str(out)]]
    stamp = stamps.read_stamp(out)
    assert stamp is not None
    assert stamp.tree
    assert stamp.etag is None


def test_infographic_pptx_target_produces_a_pptx_and_a_stamp(root, monkeypatch):
    _run(monkeypatch, ["pyforge-alpha", "infographic-pptx"])

    out = root / "presentations/pyforge-alpha/src/pptx/pyforge-alpha_infographic_deck-2026-01-01.pptx"
    assert out.is_file()
    assert stamps.read_stamp(out) is not None


def test_deck_pptx_target_produces_a_pptx_and_a_stamp(root, monkeypatch):
    _run(monkeypatch, ["pyforge-alpha", "deck-pptx"])

    out = root / "presentations/pyforge-alpha/src/pptx/pyforge-alpha-deck-2026-01-01.pptx"
    assert out.is_file()
    assert stamps.read_stamp(out) is not None


def test_default_no_targets_regenerates_all_three_and_stamps_each(root, monkeypatch):
    calls = _run(monkeypatch, ["pyforge-alpha"])

    assert len(calls) == 3
    pptx_dir = root / "presentations/pyforge-alpha/src/pptx"
    marp_dir = root / "presentations/pyforge-alpha/src/marp"
    produced = [
        marp_dir / "pyforge-alpha-infographic-standalone-2026-01-01.html",
        pptx_dir / "pyforge-alpha_infographic_deck-2026-01-01.pptx",
        pptx_dir / "pyforge-alpha-deck-2026-01-01.pptx",
    ]
    for path in produced:
        assert path.is_file()
        assert stamps.read_stamp(path) is not None


# ------------------------------------------------------------ no-chrome skip


def test_infographic_pptx_skipped_when_chrome_unavailable(root, monkeypatch, capsys):
    monkeypatch.setattr(deck_export, "chrome_available", lambda: False)

    calls = _run(monkeypatch, ["pyforge-alpha", "infographic-pptx"])

    assert calls == []
    out = capsys.readouterr().out
    assert "derive-skipped: no chrome (infographic-pptx)" in out
    pptx_path = root / "presentations/pyforge-alpha/src/pptx/pyforge-alpha_infographic_deck-2026-01-01.pptx"
    assert not pptx_path.exists()
    assert stamps.read_stamp(pptx_path) is None


def test_deck_pptx_skipped_when_chrome_unavailable(root, monkeypatch, capsys):
    monkeypatch.setattr(deck_export, "chrome_available", lambda: False)

    calls = _run(monkeypatch, ["pyforge-alpha", "deck-pptx"])

    assert calls == []
    out = capsys.readouterr().out
    assert "derive-skipped: no chrome (deck-pptx)" in out
    pptx_path = root / "presentations/pyforge-alpha/src/pptx/pyforge-alpha-deck-2026-01-01.pptx"
    assert not pptx_path.exists()


def test_html_target_is_unaffected_by_no_chrome(root, monkeypatch):
    """Boundaries & Constraints: chrome-skip applies only to the ``--pptx``
    targets -- ``html`` is pure Node and must still run."""
    monkeypatch.setattr(deck_export, "chrome_available", lambda: False)

    calls = _run(monkeypatch, ["pyforge-alpha", "html"])

    assert len(calls) == 1
    out = root / "presentations/pyforge-alpha/src/marp/pyforge-alpha-infographic-standalone-2026-01-01.html"
    assert out.is_file()


def test_default_no_targets_with_no_chrome_still_produces_html_and_exits_zero(
    root, monkeypatch, capsys
):
    """The process exits 0 even when both PPTX targets are skipped -- no
    exception, matching the AC's "process still exits 0"."""
    monkeypatch.setattr(deck_export, "chrome_available", lambda: False)

    calls = _run(monkeypatch, ["pyforge-alpha"])

    assert len(calls) == 1  # only html actually ran marp
    out = capsys.readouterr().out
    assert "derive-skipped: no chrome (infographic-pptx)" in out
    assert "derive-skipped: no chrome (deck-pptx)" in out
    html_out = root / "presentations/pyforge-alpha/src/marp/pyforge-alpha-infographic-standalone-2026-01-01.html"
    assert html_out.is_file()


# ------------------------------------------------------------------ refusals


def test_unknown_target_exits_with_error(root, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["deck_export.py", "pyforge-alpha", "bogus"])
    with pytest.raises(SystemExit, match="unknown target"):
        deck_export.main()


def test_missing_marp_dir_exits_with_error(root, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["deck_export.py", "pyforge-nope"])
    with pytest.raises(SystemExit, match="not found"):
        deck_export.main()


def test_missing_infographic_source_for_html_exits_with_error(root, monkeypatch):
    (root / "presentations/pyforge-alpha/src/marp/pyforge-alpha-infographic-2026-01-01.md").unlink()
    monkeypatch.setattr(sys, "argv", ["deck_export.py", "pyforge-alpha", "html"])
    with pytest.raises(SystemExit, match="no infographic .md source"):
        deck_export.main()


def test_missing_deck_source_for_deck_pptx_exits_with_error(root, monkeypatch):
    (root / "presentations/pyforge-alpha/src/marp/pyforge-alpha-deck-2026-01-01.md").unlink()
    monkeypatch.setattr(sys, "argv", ["deck_export.py", "pyforge-alpha", "deck-pptx"])
    with pytest.raises(SystemExit, match="no deck .md source"):
        deck_export.main()


# ----------------------------------------------------------- chrome_available


def test_chrome_available_true_when_the_hardcoded_chrome_path_exists(monkeypatch):
    monkeypatch.setattr(deck_export.os.path, "exists", lambda p: p == deck_export.CHROME)
    monkeypatch.setattr(deck_export.shutil, "which", lambda name: None)
    assert deck_export.chrome_available() is True


def test_chrome_available_true_when_chromium_is_on_path(monkeypatch):
    monkeypatch.setattr(deck_export.os.path, "exists", lambda p: False)
    monkeypatch.setattr(
        deck_export.shutil, "which", lambda name: "/usr/bin/chromium" if name == "chromium" else None
    )
    assert deck_export.chrome_available() is True


def test_chrome_available_true_when_chromium_browser_is_on_path(monkeypatch):
    monkeypatch.setattr(deck_export.os.path, "exists", lambda p: False)
    monkeypatch.setattr(
        deck_export.shutil,
        "which",
        lambda name: "/usr/bin/chromium-browser" if name == "chromium-browser" else None,
    )
    assert deck_export.chrome_available() is True


def test_chrome_available_true_when_google_chrome_is_on_path(monkeypatch):
    monkeypatch.setattr(deck_export.os.path, "exists", lambda p: False)
    monkeypatch.delenv("CHROME_PATH", raising=False)
    monkeypatch.setattr(
        deck_export.shutil,
        "which",
        lambda name: "/usr/bin/google-chrome" if name == "google-chrome" else None,
    )
    assert deck_export.chrome_available() is True


def test_chrome_available_true_when_google_chrome_stable_is_on_path(monkeypatch):
    monkeypatch.setattr(deck_export.os.path, "exists", lambda p: False)
    monkeypatch.delenv("CHROME_PATH", raising=False)
    monkeypatch.setattr(
        deck_export.shutil,
        "which",
        lambda name: "/usr/bin/google-chrome-stable"
        if name == "google-chrome-stable"
        else None,
    )
    assert deck_export.chrome_available() is True


def test_chrome_available_true_when_chrome_path_env_var_is_already_set(monkeypatch):
    """A machine with Chrome installed under a path this module does not
    hardcode, and not named anything ``shutil.which`` above checks for, can
    still declare it via ``CHROME_PATH`` (``marp``'s own override)."""
    monkeypatch.setattr(deck_export.os.path, "exists", lambda p: False)
    monkeypatch.setattr(deck_export.shutil, "which", lambda name: None)
    monkeypatch.setenv("CHROME_PATH", "/opt/chrome/chrome")
    assert deck_export.chrome_available() is True


def test_chrome_available_false_when_nothing_is_found(monkeypatch):
    monkeypatch.setattr(deck_export.os.path, "exists", lambda p: False)
    monkeypatch.setattr(deck_export.shutil, "which", lambda name: None)
    monkeypatch.delenv("CHROME_PATH", raising=False)
    assert deck_export.chrome_available() is False
