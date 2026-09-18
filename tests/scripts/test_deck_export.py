"""Unit tests for scripts/deck_export.py: regenerating a presentation deck's
derived export artifacts (standalone HTML + two PPTX targets) from its Marp
``.md`` sources via ``marp``, plus Story 21.5's exec/marp ledger-band
stamping from ``facts.yaml`` (CAP-3).

Fixture style for the Story 23.3 (formerly 23.5) coverage below mirrors
tests/scripts/test_deck_trio.py: a synthetic repo root under tmp_path (also
a real, throwaway git repo -- Story 23.3's ``stamps.write_stamp`` shells
real ``git``), the module reached through sys.path since scripts/ has no
``__init__.py``, and ``deck_export.ROOT`` / ``deck_export.run_marp`` /
``deck_export.chrome_available`` monkeypatched so every test runs offline,
with no live ``marp`` binary and no live browser.

Covers (Story 23.3): the no-chrome skip guard on the two ``--pptx`` targets
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


# ------------------------------------------------------------- Story 21.5


def _facts_yaml() -> str:
    return (
        "deck: demo\n"
        "facts:\n"
        "  - id: tree_commit_date\n"
        "    value: \"2026-09-01\"\n"
        "  - id: cfe_skill_version\n"
        "    value: \"8.90.5\"\n"
        "  - id: bmad_core_version\n"
        "    value: \"6.12.0\"\n"
        "  - id: fleet_epics_done_total\n"
        "    value: \"1/2\"\n"
        "  - id: fleet_stories_done_total\n"
        "    value: \"3/4\"\n"
    )


def _exec_html() -> str:
    return (
        "<!DOCTYPE html><html><body><x-dc>"
        "<p>Catch risky dependencies before they ship.</p>"
        "</x-dc></body></html>\n"
    )


def _marp_md() -> str:
    return "---\nmarp: true\n---\n\n# Demo\n\nHello.\n"


def test_load_fact_values(tmp_path: Path) -> None:
    p = tmp_path / "facts.yaml"
    p.write_text(_facts_yaml(), encoding="utf-8")
    got = deck_export.load_fact_values(p)
    assert got["tree_commit_date"] == "2026-09-01"
    assert got["cfe_skill_version"] == "8.90.5"


def test_stamp_exec_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "Demo - Executive Summary.dc.html"
    path.write_text(_exec_html(), encoding="utf-8")
    facts = deck_export.load_fact_values(tmp_path / "x")  # empty
    facts = {
        "tree_commit_date": "2026-09-01",
        "cfe_skill_version": "8.90.5",
        "bmad_core_version": "6.12.0",
        "fleet_epics_done_total": "1/2",
        "fleet_stories_done_total": "3/4",
    }
    deck_export.stamp_exec_summary(path, facts)
    first = path.read_text(encoding="utf-8")
    assert 'data-fact="tree_commit_date"' in first
    assert ">2026-09-01<" in first
    deck_export.stamp_exec_summary(path, facts)
    assert path.read_text(encoding="utf-8") == first
    facts["cfe_skill_version"] = "9.0.0"
    deck_export.stamp_exec_summary(path, facts)
    second = path.read_text(encoding="utf-8")
    assert ">9.0.0<" in second
    assert first != second
    assert first.count(deck_export.BAND_ATTR) == second.count(deck_export.BAND_ATTR) == 1


def test_stamp_marp_then_fact_change(tmp_path: Path) -> None:
    src = tmp_path / "demo-infographic-2026-07-15.md"
    dest = tmp_path / "demo-infographic-2026-09-15.md"
    src.write_text(_marp_md(), encoding="utf-8")
    facts = {"tree_commit_date": "2026-09-01", "cfe_skill_version": "8.90.5"}
    deck_export.stamp_marp_source(src, dest, facts)
    text = dest.read_text(encoding="utf-8")
    assert deck_export.MARP_BAND in text
    assert 'data-fact="cfe_skill_version"' in text
    deck_export.stamp_marp_source(dest, dest, {**facts, "cfe_skill_version": "9.0.0"})
    again = dest.read_text(encoding="utf-8")
    assert again.count(deck_export.MARP_BAND) == 1
    assert ">9.0.0<" in again
    assert ">8.90.5<" not in again


def test_find_source_ignores_narration_suffix(tmp_path: Path) -> None:
    (tmp_path / "demo-infographic-2026-07-24.md").write_text("# old\n", encoding="utf-8")
    (tmp_path / "demo-infographic-2026-09-15.md").write_text("# new\n", encoding="utf-8")
    (tmp_path / "demo-infographic-deck-narration-2026-07-31.md").write_text(
        "# narration\n", encoding="utf-8"
    )
    src, day = deck_export.find_source(str(tmp_path), "demo", "infographic")
    assert day == "2026-09-15"
    assert src.endswith("demo-infographic-2026-09-15.md")


def test_format_to_targets() -> None:
    assert deck_export.format_to_targets("summary", []) == set()
    assert deck_export.format_to_targets("pptx", []) == {"deck-pptx", "infographic-pptx"}
    assert deck_export.format_to_targets("html", []) == {"html"}
    assert deck_export.format_to_targets("all", []) == deck_export.VALID_TARGETS
    assert deck_export.format_to_targets(None, []) == deck_export.VALID_TARGETS
    assert deck_export.format_to_targets(None, ["html"]) == {"html"}


def test_cli_summary_updates_exec_and_skips_marp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "repo"
    deck = root / "presentations" / "demo"
    project = deck / "project"
    marp = deck / "src" / "marp"
    project.mkdir(parents=True)
    marp.mkdir(parents=True)
    (deck / "facts.yaml").write_text(_facts_yaml(), encoding="utf-8")
    exec_path = project / "Demo - Executive Summary.dc.html"
    exec_path.write_text(_exec_html(), encoding="utf-8")
    (marp / "demo-infographic-2026-07-15.md").write_text(_marp_md(), encoding="utf-8")
    monkeypatch.setattr(deck_export, "ROOT", str(root))
    monkeypatch.setattr(sys, "argv", ["deck_export.py", "demo", "--format", "summary"])
    deck_export.main()
    body = exec_path.read_text(encoding="utf-8")
    assert 'data-fact="fleet_stories_done_total"' in body
    assert ">3/4<" in body
    # summary does not date-stamp marp
    assert not list(marp.glob("demo-infographic-2026-09-15.md"))


# ------------------------------------------------------------- Story 23.3


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
    still declare it via ``CHROME_PATH`` (``marp``'s own override) --
    provided the path it names actually exists."""
    monkeypatch.setattr(
        deck_export.os.path, "exists", lambda p: p == "/opt/chrome/chrome"
    )
    monkeypatch.setattr(deck_export.shutil, "which", lambda name: None)
    monkeypatch.setenv("CHROME_PATH", "/opt/chrome/chrome")
    assert deck_export.chrome_available() is True


def test_chrome_available_false_when_chrome_path_env_var_is_stale(monkeypatch):
    """A ``CHROME_PATH`` left over from a machine/image where it no longer
    points at a real binary must not be trusted -- reporting "available"
    here means the guard this story adds never fires and ``marp --pptx``
    crashes instead of skipping (Story 23.5 follow-up review)."""
    monkeypatch.setattr(deck_export.os.path, "exists", lambda p: False)
    monkeypatch.setattr(deck_export.shutil, "which", lambda name: None)
    monkeypatch.setenv("CHROME_PATH", "/opt/chrome/chrome-that-no-longer-exists")
    assert deck_export.chrome_available() is False


def test_chrome_available_false_when_nothing_is_found(monkeypatch):
    monkeypatch.setattr(deck_export.os.path, "exists", lambda p: False)
    monkeypatch.setattr(deck_export.shutil, "which", lambda name: None)
    monkeypatch.delenv("CHROME_PATH", raising=False)
    assert deck_export.chrome_available() is False
