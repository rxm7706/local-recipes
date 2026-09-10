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
    model, escalated, from_model, to_model = apply_dispatch_retry_floor_raise(
        "composer-2.5-fast", "composer-2.5"
    )
    assert escalated is True
    assert model == "composer-2.5"
    assert from_model == "composer-2.5-fast"
    assert to_model == "composer-2.5"


def test_apply_dispatch_retry_floor_raise_is_idempotent_when_already_equal() -> None:
    model, escalated, from_model, to_model = apply_dispatch_retry_floor_raise(
        "composer-2.5", "composer-2.5"
    )
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
    escalated_model, escalated, from_model, to_model = (
        resolve_dispatch_model_with_retry_escalation(
            effective, difficulty="medium", prior_failed_attempts=2
        )
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
    policy_path = (
        repo_root
        / "_bmad-output"
        / "projects"
        / station
        / "planning-artifacts"
        / "marshal-policy.toml"
    )
    parsed = tomllib.loads(policy_path.read_text(encoding="utf-8"))
    tier_map = parsed.get("model_tier_map")
    assert isinstance(tier_map, dict) and tier_map
    assert "medium" in tier_map


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
def test_newly_fed_station_policies_compose_non_null_dispatch_model(
    station: str,
) -> None:
    """Story 33.6 CAP-1: composed station policy resolves a dev model on dispatch."""
    repo_root = Path(__file__).resolve().parents[6]
    policy_path = (
        repo_root
        / "_bmad-output"
        / "projects"
        / station
        / "planning-artifacts"
        / "marshal-policy.toml"
    )
    project = tomllib.loads(policy_path.read_text(encoding="utf-8"))
    effective, _ = policy.compose(project_slug=station, project=project, flags={})
    model, escalated, _, _ = resolve_dispatch_model_with_retry_escalation(
        effective, difficulty="medium", prior_failed_attempts=0
    )
    assert model == "composer-2.5-fast"
    assert escalated is False
