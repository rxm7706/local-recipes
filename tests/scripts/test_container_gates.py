"""Tests for `scripts/container-gates`'s `secrets-scan` subcommand (Story 7.3,
"Credentials never enter image layers").

Real, non-mocked: every test subprocess-invokes the real `container-gates`
script against a synthetic fixture tree built with `tempfile`, and
`container-gates` itself subprocess-invokes the real `steward keys audit
--secrets` -- no mocking of either layer. That means these tests need a real
`steward` binary on PATH, which only the `pyforge-steward` pixi env provides
(mirrors why `pyforge-doctor-scripts-test` deliberately does NOT live under
`pyforge-ci`'s zero-runtime-deps env when its target needs more than stdlib):

    pixi run -e pyforge-steward pytest tests/scripts/test_container_gates.py -q
    pixi run -e pyforge-steward pyforge-steward-container-gates-test

Mirrors the story spec's I/O & Edge-Case Matrix, one test per row (plus a
combined `.pixi/`-exclusion proof that both halves of that row hold in the
SAME tree).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTAINER_GATES = REPO_ROOT / "scripts" / "container-gates"

# Synthetic, never a real credential (SYNTHETIC/TEST markers embedded in the
# literal itself, same convention pyforge-steward's own conformance fixtures
# use) -- matches `_SECRET_PATTERNS`'s `sk-ant-[A-Za-z0-9_-]{20,}` in
# src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py.
_SECRET_LITERAL = "sk-ant-api03-SYNTHETICTEST0000000000000000"


pytestmark = pytest.mark.skipif(
    shutil.which("steward") is None,
    reason="steward not on PATH -- run via `pixi run -e pyforge-steward pytest ...`",
)


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CONTAINER_GATES), *args],
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_pixi_dir_is_skipped_entirely_for_a_directory_root(tmp_path):
    """Matrix row 1: `.pixi/` present with a secret-shaped string inside --
    never scanned, exit 0."""
    (tmp_path / "clean.txt").write_text("nothing interesting here\n")
    pixi_dir = tmp_path / ".pixi"
    pixi_dir.mkdir()
    (pixi_dir / "age-keygen-like.txt").write_text(_SECRET_LITERAL + "\n")

    proc = _run("secrets-scan", str(tmp_path))

    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_pixi_dir_excluded_but_a_sibling_secret_still_fails_the_scan(tmp_path):
    """Matrix row 2, combined with row 1 in one tree: `.pixi/` still carries
    its secret-shaped string (still excluded, still not the cause of the
    failure below) while a non-`.pixi` file also carries one -- overall exit
    non-zero, proving the `.pixi/` exclusion and the outside-detection both
    hold at once, not just in isolation."""
    pixi_dir = tmp_path / ".pixi"
    pixi_dir.mkdir()
    (pixi_dir / "age-keygen-like.txt").write_text(_SECRET_LITERAL + "\n")
    leaked = tmp_path / "leaked.txt"
    leaked.write_text(_SECRET_LITERAL + "\n")

    proc = _run("secrets-scan", str(tmp_path))

    assert proc.returncode != 0
    combined = proc.stdout + proc.stderr
    assert "anthropic-api-key" in combined
    assert str(leaked) in combined


def test_file_root_with_a_secret_fails_directly(tmp_path):
    """Matrix row 3: a file root is scanned directly -- no `.pixi/`
    exclusion logic applies to a file."""
    leaked = tmp_path / "leaked.txt"
    leaked.write_text(_SECRET_LITERAL + "\n")

    proc = _run("secrets-scan", str(leaked))

    assert proc.returncode != 0
    assert str(leaked) in (proc.stdout + proc.stderr)


def test_clean_file_root_exits_zero(tmp_path):
    clean = tmp_path / "clean.txt"
    clean.write_text("nothing interesting here\n")

    proc = _run("secrets-scan", str(clean))

    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_nonexistent_root_fails_with_a_clear_stderr_message(tmp_path):
    """Matrix row 4: never silently treated as clean."""
    missing = tmp_path / "does-not-exist"

    proc = _run("secrets-scan", str(missing))

    assert proc.returncode != 0
    assert str(missing) in proc.stderr


def test_multiple_roots_only_one_dirty_scans_both_and_fails(tmp_path):
    """Matrix row 5: every root is scanned, no short-circuit -- overall
    non-zero because at least one root was dirty, and both roots' scans
    left evidence in the combined output."""
    clean_dir = tmp_path / "clean_root"
    clean_dir.mkdir()
    (clean_dir / "a.txt").write_text("nothing interesting\n")

    dirty_file = tmp_path / "dirty_root.txt"
    dirty_file.write_text(_SECRET_LITERAL + "\n")

    proc = _run("secrets-scan", str(clean_dir), str(dirty_file))

    assert proc.returncode != 0
    combined = proc.stdout + proc.stderr
    assert str(clean_dir / "a.txt") in combined  # proves clean_root was actually scanned
    assert str(dirty_file) in combined            # proves dirty_root was actually scanned


def test_multiple_clean_roots_exit_zero(tmp_path):
    root_a = tmp_path / "a"
    root_a.mkdir()
    (root_a / "clean.txt").write_text("nothing interesting\n")
    root_b = tmp_path / "b.txt"
    root_b.write_text("nothing interesting either\n")

    proc = _run("secrets-scan", str(root_a), str(root_b))

    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_steward_missing_from_path_fails_cleanly_not_with_a_traceback(tmp_path):
    """`steward` absent from PATH (e.g. a broken shell-hook source in the
    real Containerfile RUN step) must be a clean gate failure, not an
    unhandled `FileNotFoundError` traceback -- exercises the real PATH-lookup
    failure by giving the CHILD `container-gates` process an environment
    with no `steward` reachable, rather than mocking `subprocess.run`."""
    clean = tmp_path / "clean.txt"
    clean.write_text("nothing interesting here\n")

    proc = subprocess.run(
        [sys.executable, str(CONTAINER_GATES), "secrets-scan", str(clean)],
        capture_output=True,
        text=True,
        timeout=60,
        env={"PATH": "/nonexistent-empty-bin"},
    )

    assert proc.returncode != 0
    assert "not found on PATH" in proc.stderr
    assert "Traceback" not in proc.stderr
