"""Coverage policy: closed include/omit/fail_under surface (steward 16.4).

Freezes the measurement bound and floor so narrowing omit/include or lowering
fail_under is a gate failure. Competing ``.coveragerc`` is forbidden; fail_under
must be declared exactly once.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.policy import readers

# Closed surface — measured 2026-08-23 on steward/16-4 branch under
# platform-ci-test: TOTAL 100.00% on include=["platformapp/**"]. Floor set to
# the observed total so happy path stays green; lowering it is deliberate drift.
CLOSED_INCLUDE = ["platformapp/**"]
CLOSED_OMIT = ["*/migrations/*", "*/tests/*"]
CLOSED_FAIL_UNDER = 100


def _assert_closed_run_surface(pyproject: dict[str, Any]) -> None:
    include = readers.declared_include(pyproject)
    omit = readers.declared_omit(pyproject)
    assert include == CLOSED_INCLUDE, (
        f"coverage include drifted: expected {CLOSED_INCLUDE!r}, got {include!r}"
    )
    assert omit == CLOSED_OMIT, (
        f"coverage omit drifted: expected {CLOSED_OMIT!r}, got {omit!r}"
    )


def _assert_fail_under(pyproject: dict[str, Any]) -> None:
    value = readers.declared_fail_under(pyproject)
    assert value == CLOSED_FAIL_UNDER, (
        f"coverage fail_under drifted: expected {CLOSED_FAIL_UNDER!r}, got {value!r}"
    )


def test_coverage_include_and_omit_are_closed() -> None:
    """Happy path: include/omit match the closed constants."""
    _assert_closed_run_surface(readers.platform_pyproject())


def test_coverage_fail_under_matches_measured_floor() -> None:
    """Happy path: fail_under equals the measured floor constant."""
    _assert_fail_under(readers.platform_pyproject())


def test_fail_under_declared_exactly_once() -> None:
    """fail_under must appear exactly once in platform pyproject.toml."""
    count = readers.count_fail_under_declarations()
    assert count == 1, f"fail_under must be declared exactly once; found {count}"


def test_no_competing_coveragerc() -> None:
    """No ``.coveragerc`` beside pyproject (single declaration site)."""
    coveragerc = readers.PLATFORM_ROOT / ".coveragerc"
    assert not coveragerc.exists(), (
        f"{coveragerc.relative_to(readers.REPO_ROOT)} must not exist; "
        "coverage config lives in pyproject.toml only"
    )
    root_coveragerc = readers.REPO_ROOT / ".coveragerc"
    assert not root_coveragerc.exists(), (
        "repo-root .coveragerc must not exist for the platform coverage surface"
    )


def test_deliberate_omit_drift_reds() -> None:
    """Drift: widening omit must fail the closed-surface assertion."""
    drifted = readers.platform_pyproject()
    run = dict(drifted.setdefault("tool", {}).setdefault("coverage", {}).get("run", {}))
    run["omit"] = [*CLOSED_OMIT, "platformapp/users/*"]
    drifted = {
        "tool": {
            "coverage": {
                "run": run,
                "report": dict(
                    drifted.get("tool", {}).get("coverage", {}).get("report", {}),
                ),
            },
        },
    }
    with pytest.raises(AssertionError, match="omit drifted"):
        _assert_closed_run_surface(drifted)


def test_deliberate_include_drift_reds() -> None:
    """Drift: narrowing include must fail the closed-surface assertion."""
    drifted = {
        "tool": {
            "coverage": {
                "run": {
                    "include": ["platformapp/users/**"],
                    "omit": list(CLOSED_OMIT),
                },
            },
        },
    }
    with pytest.raises(AssertionError, match="include drifted"):
        _assert_closed_run_surface(drifted)


def test_deliberate_fail_under_drift_reds() -> None:
    """Drift: lowering fail_under must fail."""
    drifted = {
        "tool": {
            "coverage": {
                "run": {
                    "include": list(CLOSED_INCLUDE),
                    "omit": list(CLOSED_OMIT),
                },
                "report": {"fail_under": CLOSED_FAIL_UNDER - 10},
            },
        },
    }
    with pytest.raises(AssertionError, match="fail_under drifted"):
        _assert_fail_under(drifted)


def test_deliberate_duplicate_fail_under_reds() -> None:
    """Drift: two fail_under keys in text must fail the once-only check."""
    text = readers.PLATFORM_PYPROJECT.read_text(encoding="utf-8")
    drifted = text + "\nfail_under = 50\n"
    count = readers.count_fail_under_declarations(drifted)
    with pytest.raises(AssertionError, match="exactly once"):
        assert count == 1, f"fail_under must be declared exactly once; found {count}"
