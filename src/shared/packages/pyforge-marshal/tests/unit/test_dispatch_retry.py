"""Unit tests for dispatch retry helpers (Story 33.6)."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from pyforge.marshal.core import policy
from pyforge.marshal.core.dispatch import resolve_dispatch_model_with_retry_escalation
from pyforge.marshal.core.dispatch_retry import (
    apply_dispatch_retry_floor_raise,
    should_dispatch_retry_escalate,
)


@pytest.mark.parametrize(
    ("prior", "max_dev", "expected"),
    [
        (0, 2, False),
        (1, 2, False),
        (2, 2, True),
        (3, 2, True),
        (2, 0, False),
    ],
)
def test_should_dispatch_retry_escalate(prior: int, max_dev: int, expected: bool) -> None:
    assert should_dispatch_retry_escalate(prior, max_dev) is expected


def test_apply_dispatch_retry_floor_raise_escalates_dev_to_review() -> None:
    model, escalated, from_model, to_model = apply_dispatch_retry_floor_raise("composer-2.5-fast", "composer-2.5")
    assert escalated is True
    assert model == "composer-2.5"
    assert from_model == "composer-2.5-fast"
    assert to_model == "composer-2.5"


def test_apply_dispatch_retry_floor_raise_is_idempotent_when_already_equal() -> None:
    model, escalated, from_model, to_model = apply_dispatch_retry_floor_raise("composer-2.5", "composer-2.5")
    assert escalated is False
    assert model == "composer-2.5"
    assert from_model is None
    assert to_model is None


def test_resolve_dispatch_model_with_retry_escalation_floor_raises() -> None:
    effective, _ = policy.compose(
        project_slug="acme",
        project={
            "model_tier_map": {
                "medium": {"dev": "composer-2.5-fast", "review": "composer-2.5"},
            }
        },
        flags={"max_dev_attempts": 2},
    )
    base, _, _, _ = resolve_dispatch_model_with_retry_escalation(
        effective, difficulty="medium", prior_failed_attempts=0
    )
    escalated_model, escalated, from_model, to_model = resolve_dispatch_model_with_retry_escalation(
        effective, difficulty="medium", prior_failed_attempts=2
    )
    assert base == "composer-2.5-fast"
    assert escalated is True
    assert escalated_model == "composer-2.5"
    assert from_model == "composer-2.5-fast"
    assert to_model == "composer-2.5"


@pytest.mark.parametrize(
    "station",
    [
        "pyforge-atlas",
        "pyforge-doctor",
        "pyforge-herald",
        "pyforge-marshal",
        "pyforge-mason",
        "pyforge-scribe",
        "pyforge-steward",
        "pyforge-warden",
    ],
)
def test_all_eight_stations_declare_model_tier_map(station: str) -> None:
    """Story 33.6 CAP-1: every station policy carries a non-empty tier map."""
    repo_root = Path(__file__).resolve().parents[6]
    policy_path = repo_root / "_bmad-output" / "projects" / station / "planning-artifacts" / "marshal-policy.toml"
    parsed = tomllib.loads(policy_path.read_text(encoding="utf-8"))
    tier_map = parsed.get("model_tier_map")
    assert isinstance(tier_map, dict) and tier_map
    assert {"heavy", "medium", "easy"}.issubset(tier_map)


def _declared_dev_model(project: dict, difficulty: str) -> str:
    """The dev model the station's OWN `model_tier_map` names for
    `difficulty` -- the expectation this test derives per station instead
    of pinning a fleet-wide table.

    2026-09-13 (spec-cursor-native-tier-map / Story 33.15) every station's
    `model_tier_map` became an explicit `{harness, model}` inline table (CAP-1)
    and this test pinned the Cursor Ultra ladder ids fleet-wide. 2026-09-18:
    Cursor ran out of usage for the week and herald's policy moved back to
    the Claude harness (PR #1458), which turned three parametrizations red on
    `main` for five hours -- the pinned ids were volatile per-station config,
    not the Story 33.6 CAP-1 contract ("a composed station policy resolves a
    NON-NULL dev model on dispatch"). The contract is what this asserts now:
    the resolved model is exactly what that station's tier map declares, and
    it is non-empty. `resolve_dispatch_model_with_retry_escalation` stays
    harness-agnostic by design (it only knows "dev"/"review" stages); the
    CAP-2 fails-safe that refuses to launch a Cursor-catalogued model on a
    `claude` adapter lives one layer up, in `dispatch_once`'s own live
    harness cross-check (`test_dispatch.py::test_cross_provider_model_
    override_is_dropped_...`, MRS-DISP-043) -- unaffected here."""
    entry = project["model_tier_map"][difficulty]["dev"]
    model = entry["model"] if isinstance(entry, dict) else entry
    assert isinstance(model, str) and model, f"{difficulty}: station tier map names no dev model ({entry!r})"
    return model


@pytest.mark.parametrize(
    "station",
    [
        "pyforge-doctor",
        "pyforge-herald",
        "pyforge-mason",
        "pyforge-scribe",
        "pyforge-steward",
        "pyforge-warden",
    ],
)
@pytest.mark.parametrize("difficulty", ["heavy", "medium", "easy"])
def test_newly_fed_station_policies_compose_non_null_dispatch_model(station: str, difficulty: str) -> None:
    """Story 33.6 CAP-1: composed station policy resolves a non-null dev
    model on dispatch -- the one its own tier map declares (see
    `_declared_dev_model` for why this is no longer a pinned table)."""
    repo_root = Path(__file__).resolve().parents[6]
    policy_path = repo_root / "_bmad-output" / "projects" / station / "planning-artifacts" / "marshal-policy.toml"
    project = tomllib.loads(policy_path.read_text(encoding="utf-8"))
    effective, _ = policy.compose(project_slug=station, project=project, flags={})
    model, escalated, _, _ = resolve_dispatch_model_with_retry_escalation(
        effective, difficulty=difficulty, prior_failed_attempts=0
    )
    assert model == _declared_dev_model(project, difficulty)
    assert escalated is False
