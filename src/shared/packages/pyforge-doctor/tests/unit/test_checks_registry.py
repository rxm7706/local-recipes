"""Unit tests for ``pyforge.doctor.checks.registry`` (Story 1.3) -- covers
every row of the spec's I/O & Edge-Case Matrix: list all/filtered/unknown-
category, the no-execution proof for ``list_checks``, ``gather_one``
found/not-found/unknown-category-raises, and the live drift-detection
cross-check against a real, unmocked ``sources.warden.gather()`` call --
mirroring ``test_sources_warden.py``'s monkeypatch-``run_doctor_checks``
idiom and its "live equivalence" real-call idiom.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.doctor.checks.registry import (
    _CATALOG,
    CheckSpec,
    gather_one,
    list_checks,
)
from pyforge.doctor.models import DoctorStatus
from pyforge.doctor.sources import warden as warden_source
from pyforge.warden import engines as engines_mod
from pyforge.warden.engines import DoctorCheck

# The test suite's OWN copy of the six names, deliberately NOT imported
# from the module under test -- importing registry's tuple would make the
# catalog tests tautologies. (Registry's copy is in turn guarded against
# warden itself by the live drift test at the bottom.)
_ENGINE_NAMES = (
    "deptry",
    "osv-scanner",
    "osv-db",
    "kev-feed",
    "epss-feed",
    "endoflife-feed",
)

_EXPECTED_ENGINE_SPECS = tuple(
    CheckSpec(category="engines", name=name) for name in _ENGINE_NAMES
)


def _checks(*specs: tuple[str, bool, str]) -> tuple[DoctorCheck, ...]:
    return tuple(DoctorCheck(name=n, ok=ok, message=m) for n, ok, m in specs)


# --- list_checks -------------------------------------------------------------


def test_list_checks_returns_the_six_known_engine_specs():
    assert list_checks() == _EXPECTED_ENGINE_SPECS


def test_list_checks_filtered_by_engines_matches_unfiltered():
    assert list_checks(category="engines") == list_checks()


def test_list_checks_unknown_category_returns_empty_tuple_no_exception():
    # "env" is a DELIBERATE tripwire, not just an example: the moment
    # Story 1.4 registers it in _CATALOG, the first assert fails, sending
    # that implementer here -- and to gather_one's dispatch (see
    # test_every_cataloged_category_is_dispatchable_by_gather_one).
    assert list_checks(category="env") == ()
    assert list_checks(category="bogus-category") == ()


def test_list_checks_never_invokes_run_doctor_checks(monkeypatch):
    def _boom(target):
        raise AssertionError(
            "list_checks() must never execute a real check to build its "
            "catalog"
        )

    monkeypatch.setattr(engines_mod, "run_doctor_checks", _boom)

    assert list_checks() == _EXPECTED_ENGINE_SPECS


# --- gather_one ---------------------------------------------------------------


def test_gather_one_matches_the_named_finding_from_a_full_gather(
    monkeypatch, tmp_path: Path
):
    checks = _checks(
        ("deptry", True, "within tested range"),
        ("osv-scanner", False, "osv-scanner binary not found on PATH"),
        ("osv-db", True, "snapshot fresh"),
        ("kev-feed", True, "operating air-gapped"),
        ("epss-feed", True, "operating air-gapped"),
        ("endoflife-feed", True, "operating air-gapped"),
    )
    monkeypatch.setattr(engines_mod, "run_doctor_checks", lambda target: checks)

    result = gather_one("engines", "osv-scanner", tmp_path)
    full = warden_source.gather(tmp_path)
    expected = next(f for f in full if f.check == "osv-scanner")

    assert result == expected
    assert result.status is DoctorStatus.FAIL


def test_gather_one_unknown_check_name_returns_none(monkeypatch, tmp_path: Path):
    checks = _checks(
        ("deptry", True, "within tested range"),
        ("osv-scanner", True, "within tested range"),
        ("osv-db", True, "snapshot fresh"),
        ("kev-feed", True, "operating air-gapped"),
        ("epss-feed", True, "operating air-gapped"),
        ("endoflife-feed", True, "operating air-gapped"),
    )
    monkeypatch.setattr(engines_mod, "run_doctor_checks", lambda target: checks)

    assert gather_one("engines", "not-a-real-check", tmp_path) is None


def test_gather_one_unknown_category_raises_value_error(
    monkeypatch, tmp_path: Path
):
    # The guard must reject BEFORE gathering: if a refactor ever moves the
    # category check after the gather call, warden's degrade-never-crash
    # wrapper would swallow this sentinel and no ValueError would surface,
    # failing this test loudly instead of silently running real
    # subprocesses inside a unit test.
    def _boom(target):
        raise AssertionError("an unknown category must never reach a gather")

    monkeypatch.setattr(engines_mod, "run_doctor_checks", _boom)

    with pytest.raises(
        ValueError, match=r"unsupported check category: 'bogus-category'"
    ):
        gather_one("bogus-category", "x", tmp_path)


def test_every_cataloged_category_is_dispatchable_by_gather_one(
    monkeypatch, tmp_path: Path
):
    # Coherence tripwire, enforcing what registry.py's dispatch comment
    # can only ask for: every category registered in _CATALOG must have a
    # matching dispatch branch in gather_one. A category added to the
    # catalog (Story 1.4's "env") without its own branch fails here with
    # "unsupported check category" instead of shipping a registry that
    # lists a category gather_one rejects.
    monkeypatch.setattr(engines_mod, "run_doctor_checks", lambda target: ())

    for category in _CATALOG:
        assert gather_one(category, "no-such-check", tmp_path) is None


def test_gather_one_can_address_the_degradation_sentinel_by_name(
    monkeypatch, tmp_path: Path
):
    # Filter semantics cut both ways (the complement of the sentinel->None
    # test below): the degradation sentinel's own check name -- one
    # list_checks() never advertises -- IS addressable, and returns the
    # sentinel Finding itself. Whether Story 1.5's CLI validates names
    # against the catalog (making this unreachable) or passes them through
    # is its decision (review finding, 2026-07-30 -- logged in
    # deferred-work.md).
    def _boom(target):
        raise RuntimeError("simulated warden self-check crash")

    monkeypatch.setattr(engines_mod, "run_doctor_checks", _boom)

    sentinel = gather_one("engines", "pyforge-warden", tmp_path)

    assert sentinel is not None
    assert sentinel.check == "pyforge-warden"
    assert sentinel.status is DoctorStatus.FAIL


def test_gather_one_returns_none_when_gather_degrades_to_sentinel_finding(
    monkeypatch, tmp_path: Path
):
    # When sources.warden.gather() degrades to its single "pyforge-warden"
    # sentinel Finding (warden absent/unimportable/raising -- Story 1.2's
    # own tests cover all three shapes), no Finding named "osv-scanner"
    # exists in the result. gather_one is a literal filter over that
    # result (AC3), so it returns None here -- it does not surface the
    # sentinel's own failure reason. Pinning today's actual, spec-mandated
    # behavior; whether a caller should see the sentinel instead is a
    # Story 1.5 CLI-wiring UX decision, not this module's job (review
    # finding, 2026-07-30 -- logged in deferred-work.md).
    def _boom(target):
        raise RuntimeError("simulated warden self-check crash")

    monkeypatch.setattr(engines_mod, "run_doctor_checks", _boom)

    assert gather_one("engines", "osv-scanner", tmp_path) is None


# --- live drift-detection cross-check ----------------------------------------


def test_live_catalog_matches_real_warden_gather_check_names(tmp_path: Path):
    # Order-preserving, not just set equality: the module docstring claims
    # to mirror run_doctor_checks' own documented FIXED order, so a
    # same-names-different-order drift (a reorder without a rename) should
    # fail this test too, not just a renamed/added/removed check (review
    # finding, 2026-07-30).
    live_findings = warden_source.gather(tmp_path)
    live_names = tuple(finding.check for finding in live_findings)

    # Separate the two possible diagnoses up front: a degraded gather (the
    # single "pyforge-warden" sentinel -- warden broken in THIS test
    # environment) would otherwise fail the assert below reading exactly
    # like catalog drift (review finding, 2026-07-30).
    if live_names == ("pyforge-warden",):
        pytest.fail(
            "warden degraded in this environment (not catalog drift): "
            + live_findings[0].message
        )

    catalog_names = tuple(spec.name for spec in list_checks())

    assert catalog_names == live_names


def test_live_gather_one_equivalence_with_real_gather(tmp_path: Path):
    # AC2 end-to-end without mocks, mirroring test_sources_warden.py's
    # live-equivalence idiom (which already relies on two consecutive live
    # runs agreeing): gather_one really is the literal filter over a real
    # full-suite run, not just over the monkeypatched ones above.
    expected = next(
        (f for f in warden_source.gather(tmp_path) if f.check == "deptry"),
        None,
    )

    assert gather_one("engines", "deptry", tmp_path) == expected
