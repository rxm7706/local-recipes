"""Story 13.5's scheduled-job module (``scheduler.py``): unit tests
independent of the CLI -- ``tests/test_cli_epic13.py`` covers the
``herald scheduler run`` wiring on top of this."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from pyforge.herald import claims, errors, progress, scheduler


class _Valid:
    is_valid = True


class _Invalid:
    is_valid = False


def _always_valid(url):
    return _Valid()


def _broken_for(broken_urls):
    def _validate(url):
        return _Invalid() if url in broken_urls else _Valid()

    return _validate


# --- run_scheduled_jobs: the I/O matrix -----------------------------------


def test_empty_db_completes_with_zero_counts(tmp_path):
    db_path = tmp_path / "herald.db"
    out_dir = tmp_path / "out"

    result = scheduler.run_scheduled_jobs(
        claims_path=db_path,
        progress_path=db_path,
        out_dir=out_dir,
        validate=_always_valid,
    )

    assert result.claims_checked == 0
    assert result.broken_evidence_claim_ids == ()
    assert result.records_aggregated == 0
    assert result.snapshot_path == out_dir / "progress.json"
    assert json.loads(result.snapshot_path.read_text(encoding="utf-8")) == []


def test_happy_path_revalidates_and_aggregates_in_one_call(tmp_path):
    db_path = tmp_path / "herald.db"
    claim = claims.create(
        db_path,
        project_name="warden",
        evidence=[claims.Evidence(type="test_results", url="https://ok", label="t")],
    )
    progress.upsert(
        db_path,
        station="warden",
        date="2026-08-08",
        shipped_capabilities=["hygiene gate"],
        compute_hours=1.5,
        token_spend=1000,
        wall_clock_hours=2.0,
        unblock_narrative="",
    )
    out_dir = tmp_path / "out"

    result = scheduler.run_scheduled_jobs(
        claims_path=db_path,
        progress_path=db_path,
        out_dir=out_dir,
        validate=_always_valid,
    )

    assert result.claims_checked == 1
    assert result.broken_evidence_claim_ids == ()
    assert result.records_aggregated == 1
    updated = claims.read_one(db_path, claim.id)
    assert updated.evidence[0].validated is True
    assert updated.evidence[0].validated_at is not None
    payload = json.loads(result.snapshot_path.read_text(encoding="utf-8"))
    assert len(payload) == 1
    assert payload[0]["station"] == "warden"


def test_broken_evidence_link_is_surfaced_by_id_without_raising(tmp_path):
    db_path = tmp_path / "herald.db"
    claim = claims.create(
        db_path,
        project_name="warden",
        evidence=[claims.Evidence(type="test_results", url="https://broken", label="t")],
    )
    out_dir = tmp_path / "out"

    result = scheduler.run_scheduled_jobs(
        claims_path=db_path,
        progress_path=db_path,
        out_dir=out_dir,
        validate=_broken_for({"https://broken"}),
    )

    assert result.claims_checked == 1
    assert result.broken_evidence_claim_ids == (claim.id,)
    updated = claims.read_one(db_path, claim.id)
    assert updated.evidence[0].validated is False


def test_a_claim_with_only_valid_evidence_is_never_named_broken(tmp_path):
    db_path = tmp_path / "herald.db"
    ok_claim = claims.create(
        db_path,
        project_name="warden",
        evidence=[claims.Evidence(type="test_results", url="https://ok", label="t")],
    )
    broken_claim = claims.create(
        db_path,
        project_name="marshal",
        evidence=[claims.Evidence(type="test_results", url="https://broken", label="t")],
    )
    out_dir = tmp_path / "out"

    result = scheduler.run_scheduled_jobs(
        claims_path=db_path,
        progress_path=db_path,
        out_dir=out_dir,
        validate=_broken_for({"https://broken"}),
    )

    assert result.claims_checked == 2
    assert result.broken_evidence_claim_ids == (broken_claim.id,)
    assert ok_claim.id not in result.broken_evidence_claim_ids


# --- run_evidence_revalidation: injected clock -----------------------------


def test_run_evidence_revalidation_honors_an_injected_clock(tmp_path):
    db_path = tmp_path / "herald.db"
    claim = claims.create(
        db_path,
        project_name="warden",
        evidence=[claims.Evidence(type="test_results", url="https://ok", label="t")],
    )
    fixed = datetime(2026, 1, 1, tzinfo=UTC)

    result = scheduler.run_evidence_revalidation(db_path, validate=_always_valid, now=lambda: fixed)

    assert result.claims_checked == 1
    assert result.broken_evidence_claim_ids == ()
    updated = claims.read_one(db_path, claim.id)
    assert updated.evidence[0].validated_at == fixed.isoformat()


def test_run_evidence_revalidation_on_a_missing_db_is_a_noop(tmp_path):
    """Mirrors ``claims.revalidate_all``'s own no-database-yet contract
    (``test_revalidate_all_on_a_completely_missing_file_is_a_noop``)."""
    result = scheduler.run_evidence_revalidation(tmp_path / "herald.db", validate=_always_valid)
    assert result.claims_checked == 0
    assert result.broken_evidence_claim_ids == ()


# --- run_progress_aggregation ----------------------------------------------


def test_run_progress_aggregation_writes_the_snapshot_and_counts_records(tmp_path):
    db_path = tmp_path / "herald.db"
    progress.upsert(
        db_path,
        station="atlas",
        date="2026-08-08",
        shipped_capabilities=[],
        compute_hours=0,
        token_spend=0,
        wall_clock_hours=0,
        unblock_narrative="",
    )
    out_dir = tmp_path / "out"

    result = scheduler.run_progress_aggregation(db_path, out_dir)

    assert result.records_aggregated == 1
    assert result.snapshot_path == out_dir / "progress.json"
    payload = json.loads(result.snapshot_path.read_text(encoding="utf-8"))
    assert len(payload) == 1
    assert payload[0]["station"] == "atlas"


def test_run_progress_aggregation_on_an_empty_db_writes_an_empty_array(tmp_path):
    db_path = tmp_path / "herald.db"
    out_dir = tmp_path / "out"

    result = scheduler.run_progress_aggregation(db_path, out_dir)

    assert result.records_aggregated == 0
    assert json.loads(result.snapshot_path.read_text(encoding="utf-8")) == []


# --- run_scheduled_jobs: job isolation --------------------------------------


def test_run_scheduled_jobs_still_aggregates_progress_when_revalidation_fails(tmp_path, monkeypatch):
    """A ``HeraldError`` from evidence revalidation (e.g. a claims-store
    problem) must not silently stop the progress snapshot from refreshing
    -- the two jobs are composed, not chained. The error still propagates
    after both are attempted, so the CLI still reports failure."""
    db_path = tmp_path / "herald.db"
    progress.upsert(
        db_path,
        station="warden",
        date="2026-08-08",
        shipped_capabilities=[],
        compute_hours=0,
        token_spend=0,
        wall_clock_hours=0,
        unblock_narrative="",
    )
    out_dir = tmp_path / "out"

    def _raise(*_args, **_kwargs):
        raise errors.HeraldError("claims store problem")

    monkeypatch.setattr(claims, "revalidate_all", _raise)

    with pytest.raises(errors.HeraldError, match="claims store problem"):
        scheduler.run_scheduled_jobs(
            claims_path=db_path,
            progress_path=db_path,
            out_dir=out_dir,
            validate=_always_valid,
        )

    payload = json.loads((out_dir / "progress.json").read_text(encoding="utf-8"))
    assert len(payload) == 1


# --- run_evidence_revalidation: concurrent-conflict claims never misnamed --


def test_a_claim_revalidate_all_left_untouched_is_never_named_broken(tmp_path, monkeypatch):
    """``claims.revalidate_all`` leaves a claim byte-for-byte unchanged when
    a concurrent writer raced it -- such a claim can still carry
    ``validated=False`` evidence from before this call ever ran (e.g. a
    brand new claim created mid-run, never actually checked). Only
    evidence stamped with THIS run's own timestamp should ever be named
    broken."""
    stale_entry = claims.Evidence(
        type="test_results",
        url="https://unrelated",
        label="t",
        validated=False,
        validated_at="2020-01-01T00:00:00+00:00",  # not this run's stamp
    )
    untouched_claim = claims.Claim(
        id="untouched-claim",
        project_name="warden",
        status="draft",
        thesis=None,
        shipped_date=None,
        created_at="2026-08-08T00:00:00+00:00",
        published_at=None,
        closed_at=None,
        updated_at="2026-08-08T00:00:00+00:00",
        evidence=(stale_entry,),
    )
    monkeypatch.setattr(claims, "revalidate_all", lambda *_a, **_k: [untouched_claim])

    result = scheduler.run_evidence_revalidation(tmp_path / "herald.db", validate=_always_valid)

    assert result.claims_checked == 1
    assert result.broken_evidence_claim_ids == ()
