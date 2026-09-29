"""`StaticPanel` + `render_static_index` + `_is_board_output_dir_safe_to_write`
+ `steward deploy static` — Story 9.7 (CAP-8, AD-10).

Covers every row of the story spec's I/O & Edge-Case Matrix, plus CLI verb
dispatch through `DeployDuty.run` -- mirrors `test_deploy_perimeter.py`'s
conformance-tier shape (direct `DeployDuty().run(...)` / `main([...])`
invocation, no subprocess), section-comment-divided: validation -> refusal
-> rendering -> atomicity -> CLI.

`_run_static` never touches git; unlike `test_deploy_reconcile.py` this file
needs no real scratch git repo, only a scratch directory standing in for
`repo_root()` (monkeypatched), with `docs/dashboard/` pre-created to mirror
this repo's own real, permanent layout.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.deploy import (
    DeployDuty,
    StaticPanel,
    _is_board_output_dir_safe_to_write,
    _is_valid_board_slug,
    dashboard_diff,
    render_static_index,
)


def _ns(*, board="demo", panel=None, access_column=None) -> argparse.Namespace:
    return argparse.Namespace(deploy_verb="static", board=board, panel=panel, access_column=access_column)


@pytest.fixture
def fake_repo(tmp_path, monkeypatch) -> Path:
    """A scratch directory standing in for `repo_root()`, with `docs/
    dashboard/` already present -- mirrors this repo's own real layout,
    where that directory always exists (`repo_root()` itself locates the
    checkout by finding `pyforge.doctor.sources.fleet_scan`)."""
    root = tmp_path / "repo"
    (root / "docs" / "dashboard").mkdir(parents=True)
    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: root)
    return root


def _board_dir(root: Path, board: str = "demo") -> Path:
    return root / "docs" / "dashboard" / board


# ── StaticPanel construction ─────────────────────────────────────────────


def test_static_panel_rejects_non_string_label():
    with pytest.raises(TypeError, match="label"):
        StaticPanel(label=123, html="<div></div>")  # type: ignore[arg-type]


def test_static_panel_rejects_non_string_html():
    with pytest.raises(TypeError, match="html"):
        StaticPanel(label="East", html=123)  # type: ignore[arg-type]


def test_static_panel_rejects_empty_label():
    with pytest.raises(ValueError, match="label"):
        StaticPanel(label="   ", html="<div></div>")


def test_static_panel_rejects_padded_label():
    with pytest.raises(ValueError, match="label"):
        StaticPanel(label=" East ", html="<div></div>")


def test_static_panel_allows_empty_html():
    """Deliberately asymmetric with `label`'s strict validation -- an empty
    panel fragment is a caller's own (odd but harmless) choice, not a shape
    this module can meaningfully reject."""
    panel = StaticPanel(label="East", html="")
    assert panel.html == ""


def test_static_panel_is_frozen():
    panel = StaticPanel(label="East", html="<div></div>")
    with pytest.raises(FrozenInstanceError):
        panel.label = "West"  # type: ignore[misc]


# ── render_static_index ──────────────────────────────────────────────────


def test_render_static_index_embeds_panels_verbatim_in_order():
    panels = [
        StaticPanel(label="East", html="<div id='east'>East content</div>"),
        StaticPanel(label="West", html="<div id='west'>West content</div>"),
    ]
    text = render_static_index(panels, board="demo")

    assert "<div id='east'>East content</div>" in text
    assert "<div id='west'>West content</div>" in text
    assert text.index("East content") < text.index("West content")


def test_render_static_index_escapes_label_and_board_but_leaves_html_verbatim():
    panels = [StaticPanel(label="<b>Bold</b>", html="<script>alert('x')</script>")]
    text = render_static_index(panels, board="<i>weird</i>")

    assert "<b>Bold</b>" not in text
    assert "&lt;b&gt;Bold&lt;/b&gt;" in text
    assert "&lt;i&gt;weird&lt;/i&gt;" in text
    # panel.html stays byte-for-byte verbatim, unescaped.
    assert "<script>alert('x')</script>" in text


def test_render_static_index_rejects_duplicate_labels():
    panels = [
        StaticPanel(label="East", html="<div>1</div>"),
        StaticPanel(label="East", html="<div>2</div>"),
    ]
    with pytest.raises(ValueError, match="East"):
        render_static_index(panels, board="demo")


def test_render_static_index_includes_viewport_meta():
    text = render_static_index([StaticPanel(label="East", html="<div></div>")], board="demo")
    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in text


def test_render_static_index_handles_a_one_shot_iterable():
    """Review follow-up: `panels` is read twice (duplicate-label scan, then
    the section render), so a generator used to be exhausted by the first
    pass and silently render a page with ZERO panels -- wrong output
    reported as success. Materializing once up front fixes it."""
    panels = (StaticPanel(label=name, html=f"<div>{name}</div>") for name in ("East", "West"))

    text = render_static_index(panels, board="demo")

    assert "<div>East</div>" in text
    assert "<div>West</div>" in text


# ── _is_valid_board_slug / _is_board_output_dir_safe_to_write (direct) ─────


@pytest.mark.parametrize("bad_slug", ["../../etc", "/tmp/x", "a/b", "a b", "a..b", ""])
def test_is_valid_board_slug_rejects_unsafe_values(bad_slug):
    assert _is_valid_board_slug(bad_slug) is False


@pytest.mark.parametrize("good_slug", ["demo", "kedro-viz", "board_1", "A1"])
def test_is_valid_board_slug_accepts_safe_values(good_slug):
    assert _is_valid_board_slug(good_slug) is True


def test_safe_dir_check_absent_directory_is_safe(tmp_path):
    root = tmp_path / "repo"
    (root / "docs" / "dashboard").mkdir(parents=True)
    assert _is_board_output_dir_safe_to_write(root / "docs" / "dashboard" / "demo") is True


def test_safe_dir_check_empty_directory_is_safe(tmp_path):
    output_dir = tmp_path / "repo" / "docs" / "dashboard" / "demo"
    output_dir.mkdir(parents=True)
    assert _is_board_output_dir_safe_to_write(output_dir) is True


def test_safe_dir_check_lone_index_html_is_safe(tmp_path):
    output_dir = tmp_path / "repo" / "docs" / "dashboard" / "demo"
    output_dir.mkdir(parents=True)
    (output_dir / "index.html").write_text("<html></html>")
    assert _is_board_output_dir_safe_to_write(output_dir) is True


def test_safe_dir_check_foreign_content_is_unsafe(tmp_path):
    output_dir = tmp_path / "repo" / "docs" / "dashboard" / "kedro-viz"
    output_dir.mkdir(parents=True)
    (output_dir / "index.html").write_text("<html></html>")
    (output_dir / "assets").mkdir()
    assert _is_board_output_dir_safe_to_write(output_dir) is False


def test_safe_dir_check_board_path_not_a_directory_is_unsafe(tmp_path):
    (tmp_path / "repo" / "docs" / "dashboard").mkdir(parents=True)
    output_dir = tmp_path / "repo" / "docs" / "dashboard" / "demo"
    output_dir.write_text("not a directory")
    assert _is_board_output_dir_safe_to_write(output_dir) is False


# ── `deploy static` verb: validation & refusal (I/O matrix) ────────────────


def test_access_column_refuses_before_any_panel_is_read(fake_repo):
    """AD-10: the access-column refusal must fire even when the `--panel`
    path does not exist -- proving the refusal precedes the file read, not
    just that it eventually fires."""
    duty = DeployDuty()
    ns = _ns(board="demo", panel=["East=/does/not/exist.html"], access_column="region")

    result = duty.run(ns)

    assert result.ok is False
    assert "AD-10" in result.summary
    assert not _board_dir(fake_repo).exists()


def test_access_column_whitespace_only_does_not_refuse(fake_repo, tmp_path):
    east = tmp_path / "east.html"
    east.write_text("<div>east</div>")
    duty = DeployDuty()
    ns = _ns(board="demo", panel=[f"East={east}"], access_column="   ")

    result = duty.run(ns)

    assert result.ok is True


def test_missing_board_refuses(fake_repo):
    duty = DeployDuty()
    ns = _ns(board=None, panel=["East=x.html"])

    result = duty.run(ns)

    assert result.ok is False
    assert "board" in result.summary


@pytest.mark.parametrize("bad_board", ["../../etc", "/tmp/x", "a/b", "a b"])
def test_unsafe_board_slug_refuses(fake_repo, bad_board):
    duty = DeployDuty()
    ns = _ns(board=bad_board, panel=["East=x.html"])

    result = duty.run(ns)

    assert result.ok is False
    assert "board" in result.summary


def test_no_panel_at_all_refuses(fake_repo):
    duty = DeployDuty()
    ns = _ns(board="demo", panel=None)

    result = duty.run(ns)

    assert result.ok is False
    assert "panel" in result.summary
    assert not _board_dir(fake_repo).exists()


def test_panel_without_equals_separator_refuses(fake_repo):
    duty = DeployDuty()
    ns = _ns(board="demo", panel=["EastOnlyNoEquals"])

    result = duty.run(ns)

    assert result.ok is False
    assert "EastOnlyNoEquals" in result.summary


def test_panel_with_empty_label_refuses(fake_repo, tmp_path):
    east = tmp_path / "east.html"
    east.write_text("<div>east</div>")
    duty = DeployDuty()
    ns = _ns(board="demo", panel=[f"   ={east}"])

    result = duty.run(ns)

    assert result.ok is False


def test_panel_path_that_does_not_exist_refuses(fake_repo):
    duty = DeployDuty()
    ns = _ns(board="demo", panel=["East=/nonexistent/path/east.html"])

    result = duty.run(ns)

    assert result.ok is False


def test_panel_non_utf8_content_refuses_without_crashing(fake_repo, tmp_path):
    bad = tmp_path / "bad.html"
    bad.write_bytes(b"\xff\xfe\x00bad-not-utf8")
    duty = DeployDuty()
    ns = _ns(board="demo", panel=[f"East={bad}"])

    result = duty.run(ns)

    assert result.ok is False


def test_duplicate_panel_labels_refuses_and_writes_nothing(fake_repo, tmp_path):
    east = tmp_path / "east.html"
    east.write_text("<div>east</div>")
    west = tmp_path / "west.html"
    west.write_text("<div>west</div>")
    duty = DeployDuty()
    ns = _ns(board="demo", panel=[f"East={east}", f"East={west}"])

    result = duty.run(ns)

    assert result.ok is False
    assert "East" in result.summary
    assert not _board_dir(fake_repo).exists()


def test_non_string_access_column_refuses_not_crashes(fake_repo):
    duty = DeployDuty()
    ns = argparse.Namespace(deploy_verb="static", board="demo", panel=["East=x"], access_column=123)

    result = duty.run(ns)

    assert result.ok is False


def test_non_string_board_refuses_not_crashes(fake_repo):
    duty = DeployDuty()
    ns = argparse.Namespace(deploy_verb="static", board=123, panel=["East=x"], access_column=None)

    result = duty.run(ns)

    assert result.ok is False


def test_non_string_panel_entry_refuses_not_crashes(fake_repo):
    duty = DeployDuty()
    ns = _ns(board="demo", panel=[123])

    result = duty.run(ns)

    assert result.ok is False


def test_completely_empty_namespace_refuses_not_crashes(fake_repo):
    duty = DeployDuty()
    ns = argparse.Namespace(deploy_verb="static")

    result = duty.run(ns)

    assert result.ok is False


# ── `deploy static` verb: happy path / rendering ────────────────────────────


def test_happy_path_writes_both_panels_verbatim_in_call_order(fake_repo, tmp_path):
    east = tmp_path / "east.html"
    east.write_text("<div id='east'>East content</div>")
    west = tmp_path / "west.html"
    west.write_text("<div id='west'>West content</div>")
    duty = DeployDuty()
    ns = _ns(board="demo", panel=[f"East={east}", f"West={west}"])

    result = duty.run(ns)

    assert result.ok is True
    index_path = _board_dir(fake_repo) / "index.html"
    assert index_path.is_file()
    text = index_path.read_text()
    assert "<div id='east'>East content</div>" in text
    assert "<div id='west'>West content</div>" in text
    assert text.index("East content") < text.index("West content")
    assert 'name="viewport"' in text


def test_panel_label_with_markup_is_escaped_not_injected(fake_repo, tmp_path):
    panel_file = tmp_path / "panel.html"
    panel_file.write_text("<script>alert('x')</script>")
    duty = DeployDuty()
    ns = _ns(board="demo", panel=[f"<b>Bold</b>={panel_file}"])

    result = duty.run(ns)

    assert result.ok is True
    text = (_board_dir(fake_repo) / "index.html").read_text()
    assert "<b>Bold</b>" not in text
    assert "&lt;b&gt;Bold&lt;/b&gt;" in text
    assert "<script>alert('x')</script>" in text


# ── `deploy static` verb: directory-shape safety / atomicity ───────────────


def test_board_collision_with_kedro_viz_shaped_foreign_content_refuses(fake_repo, tmp_path):
    board_dir = _board_dir(fake_repo, "kedro-viz")
    board_dir.mkdir(parents=True)
    (board_dir / "index.html").write_text("<html>kedro-viz</html>")
    (board_dir / "assets").mkdir()
    (board_dir / "assets" / "app.js").write_text("// app")
    panel = tmp_path / "panel.html"
    panel.write_text("<div>panel</div>")
    duty = DeployDuty()
    ns = _ns(board="kedro-viz", panel=[f"P={panel}"])

    result = duty.run(ns)

    assert result.ok is False
    assert "kedro-viz" in result.summary
    assert (board_dir / "assets" / "app.js").read_text() == "// app"
    assert (board_dir / "index.html").read_text() == "<html>kedro-viz</html>"


def test_idempotent_republish_of_lone_index_html_overwrites_it(fake_repo, tmp_path):
    board_dir = _board_dir(fake_repo)
    board_dir.mkdir(parents=True)
    (board_dir / "index.html").write_text("<html>old content</html>")
    panel = tmp_path / "panel.html"
    panel.write_text("<div>new content</div>")
    duty = DeployDuty()
    ns = _ns(board="demo", panel=[f"P={panel}"])

    result = duty.run(ns)

    assert result.ok is True
    assert "new content" in (board_dir / "index.html").read_text()


@pytest.mark.skipif(sys.platform == "win32", reason="symlink creation needs privileges on Windows")
def test_symlinked_output_dir_refuses_and_writes_nothing_through_it(fake_repo, tmp_path):
    outside_target = tmp_path / "outside"
    outside_target.mkdir()
    _board_dir(fake_repo).symlink_to(outside_target, target_is_directory=True)
    panel = tmp_path / "panel.html"
    panel.write_text("<div>x</div>")
    duty = DeployDuty()
    ns = _ns(board="demo", panel=[f"P={panel}"])

    result = duty.run(ns)

    assert result.ok is False
    assert not (outside_target / "index.html").exists()


@pytest.mark.skipif(sys.platform == "win32", reason="symlink creation needs privileges on Windows")
def test_symlinked_dashboard_ancestor_refuses(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    real_dashboard = tmp_path / "real_dashboard"
    real_dashboard.mkdir()
    (root / "docs").mkdir()
    (root / "docs" / "dashboard").symlink_to(real_dashboard, target_is_directory=True)
    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: root)
    panel = tmp_path / "panel.html"
    panel.write_text("<div>x</div>")
    duty = DeployDuty()
    ns = _ns(board="demo", panel=[f"P={panel}"])

    result = duty.run(ns)

    assert result.ok is False
    assert not (real_dashboard / "demo").exists()


@pytest.mark.skipif(sys.platform == "win32", reason="symlink creation needs privileges on Windows")
def test_symlinked_docs_ancestor_refuses(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    real_docs = tmp_path / "real_docs"
    (real_docs / "dashboard").mkdir(parents=True)
    root_docs = root / "docs"
    root_docs.symlink_to(real_docs, target_is_directory=True)
    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: root)
    panel = tmp_path / "panel.html"
    panel.write_text("<div>x</div>")
    duty = DeployDuty()
    ns = _ns(board="demo", panel=[f"P={panel}"])

    result = duty.run(ns)

    assert result.ok is False
    assert not (real_docs / "dashboard" / "demo").exists()


def test_stray_tmp_from_killed_first_publish_self_heals(fake_repo, tmp_path):
    board_dir = _board_dir(fake_repo)
    board_dir.mkdir(parents=True)
    (board_dir / "index.html.tmp").write_text("leftover from a killed first-publish run")
    panel = tmp_path / "panel.html"
    panel.write_text("<div>fresh content</div>")
    duty = DeployDuty()
    ns = _ns(board="demo", panel=[f"P={panel}"])

    result = duty.run(ns)

    assert result.ok is True
    assert "fresh content" in (board_dir / "index.html").read_text()
    assert not (board_dir / "index.html.tmp").exists()


def test_stray_tmp_alongside_prior_index_from_killed_republish_self_heals(fake_repo, tmp_path):
    board_dir = _board_dir(fake_repo)
    board_dir.mkdir(parents=True)
    (board_dir / "index.html").write_text("old published content")
    (board_dir / "index.html.tmp").write_text("leftover from a killed republish")
    panel = tmp_path / "panel.html"
    panel.write_text("<div>newer content</div>")
    duty = DeployDuty()
    ns = _ns(board="demo", panel=[f"P={panel}"])

    result = duty.run(ns)

    assert result.ok is True
    assert "newer content" in (board_dir / "index.html").read_text()
    assert not (board_dir / "index.html.tmp").exists()


@pytest.mark.skipif(sys.platform == "win32", reason="symlink creation needs privileges on Windows")
def test_symlinked_tmp_entry_refuses_and_target_file_unchanged(fake_repo, tmp_path):
    board_dir = _board_dir(fake_repo)
    board_dir.mkdir(parents=True)
    outside = tmp_path / "outside_secret.html"
    outside.write_text("SECRET-TARGET-CONTENT")
    (board_dir / "index.html.tmp").symlink_to(outside)
    panel = tmp_path / "panel.html"
    panel.write_text("<div>x</div>")
    duty = DeployDuty()
    ns = _ns(board="demo", panel=[f"P={panel}"])

    result = duty.run(ns)

    assert result.ok is False
    assert outside.read_text() == "SECRET-TARGET-CONTENT"


@pytest.mark.skipif(sys.platform == "win32", reason="os.link is unavailable/privileged on Windows")
def test_hardlinked_tmp_entry_refuses_and_target_byte_identical(fake_repo, tmp_path):
    board_dir = _board_dir(fake_repo)
    board_dir.mkdir(parents=True)
    outside = tmp_path / "outside_hardlink.html"
    outside.write_text("SECRET-HARDLINK-TARGET")
    before = outside.read_bytes()
    os.link(str(outside), str(board_dir / "index.html.tmp"))
    panel = tmp_path / "panel.html"
    panel.write_text("<div>x</div>")
    duty = DeployDuty()
    ns = _ns(board="demo", panel=[f"P={panel}"])

    result = duty.run(ns)

    assert result.ok is False
    after = outside.read_bytes()
    assert after == before


@pytest.mark.skipif(sys.platform == "win32", reason="os.mkfifo does not exist on Windows")
def test_fifo_at_tmp_entry_refuses_without_hanging(fake_repo, tmp_path):
    """Pass-5's headline case: neither a symlink nor multiply-linked, a
    FIFO at the trusted entry name must still be refused -- and the check
    must never open/read it, or this test would hang forever."""
    board_dir = _board_dir(fake_repo)
    board_dir.mkdir(parents=True)
    os.mkfifo(str(board_dir / "index.html.tmp"))
    panel = tmp_path / "panel.html"
    panel.write_text("<div>x</div>")
    duty = DeployDuty()
    ns = _ns(board="demo", panel=[f"P={panel}"])

    result = duty.run(ns)

    assert result.ok is False


def test_write_failure_after_mkdir_cleans_up_every_freshly_created_ancestor_dir(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    # docs/dashboard does NOT exist yet -- mkdir(parents=True) must create
    # docs, docs/dashboard, AND docs/dashboard/demo all fresh in one call.
    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: root)
    panel = tmp_path / "panel.html"
    panel.write_text("<div>x</div>")

    def _boom(self, *args, **kwargs):
        raise OSError("simulated write failure")

    monkeypatch.setattr("pathlib.Path.write_text", _boom)

    duty = DeployDuty()
    ns = _ns(board="demo", panel=[f"P={panel}"])

    result = duty.run(ns)

    assert result.ok is False
    assert not (root / "docs" / "dashboard" / "demo").exists()
    assert not (root / "docs" / "dashboard").exists()
    assert not (root / "docs").exists()


# ── CLI round-trip (`main([...])`) ──────────────────────────────────────────


def test_static_via_cli_happy_path(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / "docs" / "dashboard").mkdir(parents=True)
    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: root)
    panel = tmp_path / "panel.html"
    panel.write_text("<div>cli panel</div>")

    rc = main(["deploy", "static", "--board", "demo", "--panel", f"East={panel}"])

    assert rc == EXIT_OK
    assert (root / "docs" / "dashboard" / "demo" / "index.html").is_file()


def test_static_via_cli_access_column_refuses(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / "docs" / "dashboard").mkdir(parents=True)
    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: root)
    panel = tmp_path / "panel.html"
    panel.write_text("<div>cli panel</div>")

    rc = main(
        [
            "deploy",
            "static",
            "--board",
            "demo",
            "--panel",
            f"East={panel}",
            "--access-column",
            "region",
        ]
    )

    assert rc == EXIT_FAILED
    assert not (root / "docs" / "dashboard" / "demo").exists()


def test_bare_deploy_names_static_among_available_verbs():
    duty = DeployDuty()
    result = duty.run(argparse.Namespace())
    assert result.ok is True
    assert "static" in result.summary


# ── gitignored board slugs / non-UTF-8 labels (review follow-up pass) ───────


def _git_repo_with_ignore(tmp_path: Path, monkeypatch, ignore: str) -> Path:
    """A REAL scratch git repo (like `test_deploy_reconcile.py`'s) — the
    gitignore interaction cannot be exercised against this file's usual
    non-git scratch dir, which is exactly why the gap survived six review
    passes: every existing test here monkeypatches `repo_root()` to a
    directory `git check-ignore` cannot answer for at all."""
    root = tmp_path / "gitrepo"
    (root / "docs" / "dashboard").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
    (root / ".gitignore").write_text(ignore)
    monkeypatch.setattr("pyforge.steward.deploy.repo_root", lambda: root)
    return root


def test_static_refuses_a_board_slug_a_gitignore_rule_would_swallow(tmp_path, monkeypatch):
    """`build` is a valid `^[A-Za-z0-9_-]+$` slug, and a bare `build/` rule
    matches at ANY depth — so `docs/dashboard/build/index.html` is ignored,
    `git add` skips it, `dashboard_diff()` never sees it, and the board
    silently never publishes while the run reports success."""
    root = _git_repo_with_ignore(tmp_path, monkeypatch, "build/\ndist/\n")
    panel = tmp_path / "panel.html"
    panel.write_text("<div>swallowed</div>")

    result = DeployDuty().run(_ns(board="build", panel=[f"East={panel}"]))

    assert result.ok is False
    assert ".gitignore" in result.summary
    assert "build" in result.summary
    assert not _board_dir(root, "build").exists()


def test_static_publishes_a_board_git_can_actually_see(tmp_path, monkeypatch):
    """The control for the test above, and the story's end-to-end claim:
    a non-ignored board is written AND is visible to `dashboard_diff()`,
    the gate `steward deploy dashboard` keys off before committing."""
    root = _git_repo_with_ignore(tmp_path, monkeypatch, "build/\n")
    panel = tmp_path / "panel.html"
    panel.write_text("<div>publishable</div>")

    result = DeployDuty().run(_ns(board="demo", panel=[f"East={panel}"]))

    assert result.ok is True
    assert (_board_dir(root, "demo") / "index.html").exists()
    assert dashboard_diff(cwd=root).strip() != ""


def test_static_refuses_a_non_utf8_panel_label_without_crashing(fake_repo, tmp_path):
    """argv is decoded with `surrogateescape`, so a non-UTF-8 byte in a
    `--panel` LABEL reaches the renderer as a lone surrogate and fails only
    at encode time — `UnicodeEncodeError` is a `ValueError`, not an
    `OSError`, the mirror image of the `--panel` READ case."""
    panel = tmp_path / "panel.html"
    panel.write_text("<div>ok</div>")

    result = DeployDuty().run(_ns(panel=[f"East\udcff={panel}"]))

    assert result.ok is False
    assert not (_board_dir(fake_repo) / "index.html").exists()
    # and no stray temp file survives the refusal
    assert not (_board_dir(fake_repo) / "index.html.tmp").exists()
