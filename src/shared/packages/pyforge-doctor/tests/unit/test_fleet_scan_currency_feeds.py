"""``scripts/fleet_scan.py::_currency`` feeds edges — the retired ``epics→sprint`` pair.

Retired 2026-09-04 (PR #1043). The tracked sprint ledger is a GENERATED twin of the
gitignored Tier-3 feed: no frontmatter, so ``_artifact_dates`` falls through to git
last-touch, and ``sprint-ledger-sync`` writes nothing when no status changed. On an
idle station the ledger therefore cannot move, and a currency-only ``epics.md``
re-stamp produced a permanent "epics newer than sprint" finding that no honest act
could clear (scribe, 2026-09-04). "Did the ledger follow the epics?" is answered by
content by chain-completeness INV-B (epics story ids == ledger keys), so the
date-based edge is redundant where it is right and wrong where it is not.

Loads the real ``scripts/fleet_scan.py`` the same way ``sources/board.py`` does.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from pyforge.doctor.sources import board

try:
    _REPO_ROOT: Path | None = Path(__file__).resolve().parents[6]
except IndexError:
    _REPO_ROOT = None
_SCAN = (_REPO_ROOT / "scripts" / "fleet_scan.py") if _REPO_ROOT else None

pytestmark = pytest.mark.skipif(not (_SCAN and _SCAN.is_file()), reason="scripts/fleet_scan.py required")


@pytest.fixture(scope="module")
def fleet_scan():
    assert _SCAN is not None
    # the package's own loader: registers the module in sys.modules before executing it,
    # which fleet_scan's dataclasses need to resolve their annotations
    return board._load_foreign_module(_SCAN, "_fleet_scan_currency_feeds")


_TODAY = date(2026, 9, 4)


def test_epics_to_sprint_is_not_a_feeds_edge(fleet_scan) -> None:
    assert ("epics", "sprint") not in fleet_scan._FEEDS
    # the contract edges the runbook still lists are untouched
    for pair in (("spec", "prd"), ("prd", "arch"), ("arch", "epics"), ("code", "retro")):
        assert pair in fleet_scan._FEEDS


def test_idle_ledger_behind_a_currency_only_epics_restamp_is_not_stale(fleet_scan) -> None:
    # scribe on 2026-09-04: epics re-stamped today, twin last touched 2026-09-01 (> grace)
    updated_at = {"arch": "2026-09-04", "epics": "2026-09-04", "sprint": "2026-09-01"}
    out = fleet_scan._currency("pyforge-scribe", {}, updated_at, set(), _TODAY, realized=True)
    assert [f for f in out if f["kind"] == "feeds"] == []


def test_contract_edges_still_fire_past_the_grace_window(fleet_scan) -> None:
    # arch re-cut 4 days after the epics were last validated -> arch→epics fires
    updated_at = {"arch": "2026-09-04", "epics": "2026-08-31", "sprint": "2026-09-01"}
    out = fleet_scan._currency("pyforge-scribe", {}, updated_at, set(), _TODAY, realized=True)
    feeds = [f for f in out if f["kind"] == "feeds"]
    assert [(f["stage"], f["than"]) for f in feeds] == [("arch", "epics")]


# --- Story 6.13: spec→prd reads contract date, not trailing memlog bookkeeping ---------

_RUN = date(2026, 10, 7)
_PRD = "2026-10-03"
_CONTRACT = "2026-10-04"
_MEMLOG_STAMP = "2026-10-07T09:00"


def _spec_prd_feeds(fleet_scan, *, spec_feeds: str, spec_stage: str = _MEMLOG_STAMP) -> list[dict]:
    updated_at = {"spec": spec_stage, "prd": _PRD}
    out = fleet_scan._currency(
        "pyforge-atlas",
        {},
        updated_at,
        set(),
        _RUN,
        realized=False,
        spec_feeds_updated=spec_feeds,
    )
    return [f for f in out if f["kind"] == "feeds" and f["stage"] == "spec"]


def test_trailing_surface_reconcile_does_not_feed_spec_prd(fleet_scan) -> None:
    assert _spec_prd_feeds(fleet_scan, spec_feeds=_CONTRACT) == []


def test_trailing_marshal_landing_does_not_feed_spec_prd(fleet_scan) -> None:
    assert _spec_prd_feeds(fleet_scan, spec_feeds=_CONTRACT) == []


def test_decision_before_surface_reconcile_feeds_spec_prd(fleet_scan) -> None:
    feeds = _spec_prd_feeds(fleet_scan, spec_feeds="2026-10-07")
    assert len(feeds) == 1
    assert feeds[0]["than"] == "prd"
    assert feeds[0]["at"].startswith("2026-10-07")


def test_spec_md_updated_with_only_bookkeeping_feeds_spec_prd(fleet_scan) -> None:
    feeds = _spec_prd_feeds(fleet_scan, spec_feeds="2026-10-07", spec_stage="2026-10-07")
    assert len(feeds) == 1


def test_last_contract_entry_uses_frontmatter_for_spec_prd(fleet_scan) -> None:
    feeds = _spec_prd_feeds(fleet_scan, spec_feeds="2026-10-07T12:00", spec_stage="2026-10-07T12:00")
    assert len(feeds) == 1


def test_behind_code_ignores_spec_feeds_contract_date(fleet_scan) -> None:
    updated_at = {"spec": "2026-10-07", "prd": _PRD, "code": "2026-10-08"}
    out = fleet_scan._currency(
        "pyforge-atlas",
        {},
        updated_at,
        set(),
        _RUN,
        realized=False,
        spec_feeds_updated=_CONTRACT,
    )
    behind = [f for f in out if f["kind"] == "behind-code" and f["stage"] == "spec"]
    assert len(behind) == 1
    assert behind[0]["at"] == "2026-10-07"


def test_non_bookkeeping_event_is_a_contract_entry(fleet_scan) -> None:
    """An `(event)` about spec-surface that is not a Surface reconcile line still dates."""
    feeds = _spec_prd_feeds(fleet_scan, spec_feeds="2026-10-07")
    assert len(feeds) == 1


def test_memlog_bookkeeping_entry_classifier(fleet_scan) -> None:
    assert fleet_scan._memlog_entry_is_bookkeeping("event", "Surface reconcile 2026-10-07: x")
    assert fleet_scan._memlog_entry_is_bookkeeping("event by marshal", "Story 25.2 landed (run abc): done")
    assert not fleet_scan._memlog_entry_is_bookkeeping("decision", "Surface reconcile noop")
    assert not fleet_scan._memlog_entry_is_bookkeeping("event", "2026-10-05 spec-surface: stamp only")


def test_memlog_contract_date_uses_blame_when_trailing_bookkeeping(
    fleet_scan, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "t"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    mem = repo / "spec" / ".memlog.md"
    mem.parent.mkdir(parents=True)
    mem.write_text(
        "---\nupdated: 2026-10-04T12:00\n---\n\n- (capability) 2026-10-04 contract moved\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    env = {"GIT_AUTHOR_DATE": "2026-10-04T12:00:00", "GIT_COMMITTER_DATE": "2026-10-04T12:00:00"}
    subprocess.run(["git", "commit", "-m", "contract"], cwd=repo, check=True, capture_output=True, env=env)
    mem.write_text(
        "---\nupdated: 2026-10-07T09:00\n---\n\n"
        "- (capability) 2026-10-04 contract moved\n"
        "- (event) Surface reconcile 2026-10-07 (probe): no path\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "spec/.memlog.md"], cwd=repo, check=True, capture_output=True)
    env2 = {"GIT_AUTHOR_DATE": "2026-10-07T09:00:00", "GIT_COMMITTER_DATE": "2026-10-07T09:00:00"}
    subprocess.run(
        ["git", "commit", "-m", "reconcile"],
        cwd=repo,
        check=True,
        capture_output=True,
        env=env2,
    )
    rel = "spec/.memlog.md"
    monkeypatch.setattr(fleet_scan, "REPO_ROOT", repo)
    monkeypatch.setattr(fleet_scan, "_GIT_FIRST", {})
    monkeypatch.setattr(fleet_scan, "_GIT_LAST", {})
    got = fleet_scan._memlog_contract_updated(rel, _RUN)
    assert got.startswith("2026-10-04")


def test_memlog_contract_date_no_git_falls_back_to_frontmatter(
    fleet_scan, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mem = tmp_path / ".memlog.md"
    mem.write_text(
        "---\nupdated: 2026-10-07T09:00\n---\n\n- (capability) still the contract\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(fleet_scan, "REPO_ROOT", tmp_path)
    got = fleet_scan._memlog_contract_updated(".memlog.md", _RUN)
    assert got.startswith("2026-10-07")
