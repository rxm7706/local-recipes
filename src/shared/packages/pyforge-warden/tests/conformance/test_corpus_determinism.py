"""Corpus-scale ``--deterministic`` determinism proof (Story 5.2, NFR-R3b
at fleet scale) -- extends ``test_scan_harness.py``'s
``test_twice_run_stdout_is_byte_identical`` pattern to the FULL committed
corpus directory as the scan target (~1,979 real ``recipe.yaml``/
``meta.yaml`` manifests merged into one project-wide inventory) rather than
a single hand-authored fixture.

Marked ``@pytest.mark.slow`` (the Boundaries/pixi.toml carve-out for "any
other corpus-scale test whose cost is dominated by real renders/
subprocesses rather than pure extraction" -- unlike
``test_corpus_regression.py``, this goes through the REAL ``cli.main``
seam, so it invokes a real ``osv-scanner`` subprocess (against the ambient
offline DB ``tests/conftest.py`` already provisions for the whole suite)
plus real ``LicenseEngine``/``CurrencyEngine`` assessment across every
merged component -- measured ~7s for a single run, ~14s for the required
twice-run, which would push the default ``pyforge-warden-test`` suite
noticeably past its "well under a minute" budget if left in the default
collection). Lives in the same ``pyforge-warden-test-corpus-oracle`` task
as the render-based oracle (pixi.toml)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.warden.cli import main

CORPUS_RECIPES_DIR = (
    Path(__file__).resolve().parent.parent / "fixtures" / "corpus" / "recipes"
)

pytestmark = pytest.mark.slow


def _run_scan(capsys, *extra: str) -> tuple[int, str, str]:
    capsys.readouterr()
    rc = main(["scan", str(CORPUS_RECIPES_DIR), "--format", "json", *extra])
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


def test_corpus_recipes_dir_is_provisioned():
    assert CORPUS_RECIPES_DIR.is_dir(), (
        f"{CORPUS_RECIPES_DIR} missing -- run scripts/harvest_corpus.py"
    )
    assert next(CORPUS_RECIPES_DIR.rglob("recipe.yaml"), None) is not None
    assert next(CORPUS_RECIPES_DIR.rglob("meta.yaml"), None) is not None


def test_full_corpus_deterministic_twice_run_is_byte_identical(capsys):
    # Self-contained presence guard (review finding): pytest test
    # isolation means this test does not actually depend on
    # test_corpus_recipes_dir_is_provisioned above running/passing first
    # (e.g. `pytest -k twice_run` alone) -- without its own check, a
    # missing/empty corpus would scan a nonexistent directory twice and
    # produce identical ERROR output both times, passing this test
    # vacuously without proving anything about corpus-scale determinism.
    assert CORPUS_RECIPES_DIR.is_dir(), (
        f"{CORPUS_RECIPES_DIR} missing -- run scripts/harvest_corpus.py"
    )
    rc_one, out_one, _err_one = _run_scan(capsys, "--deterministic")
    rc_two, out_two, _err_two = _run_scan(capsys, "--deterministic")
    assert rc_one == rc_two
    assert out_one.encode("utf-8") == out_two.encode("utf-8")
