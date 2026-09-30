"""Story 74.2 (``spec-feature-flag-governance`` CAP-3): a drain re-preflights a story the flag gate refused.

``MRS-DISP-052`` is a re-preflightable gate (the ``MRS-DISP-005`` shape): the campaign block a refused story leaves
clears once the story's spec fingerprint changes, so the next cycle runs ``dispatch_once`` again and the gate judges the
edited spec. The predicate is never the gate's answer -- this module never runs the gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core import dispatch_re_preflight as re_preflight

_SLUG = "pyforge-marshal"
_STORY = "74-2-dispatch-refuses-a-story-the-flag-gate-would-red"
_GATE = "MRS-DISP-052"
_DETAIL = f"{_GATE}: the feature-flag gate reds spec-{_STORY}.md: flag-missing: neither a flag block nor an exemption"


def _write_spec(repo_root: Path, text: str) -> Path:
    specs = dispatch_core.planning_specs_dir(repo_root, _SLUG)
    specs.mkdir(parents=True, exist_ok=True)
    spec = specs / f"spec-{_STORY}.md"
    spec.write_text(text, encoding="utf-8")
    return spec


def _predicate(repo_root: Path, *, gate: str = _GATE, verify: tuple[str, ...] = ()) -> re_preflight.RefusePredicate:
    return re_preflight.compute_refuse_predicate(
        repo_root=repo_root, slug=_SLUG, story=_STORY, gate=gate, verify_commands=verify
    )


def _reconcile(
    repo_root: Path,
    *,
    detail: str = _DETAIL,
    prior: re_preflight.RefusePredicate | None,
    verify: tuple[str, ...] = (),
) -> tuple[dict[str, str], tuple[re_preflight.RePreflightResult, ...]]:
    return re_preflight.reconcile_station_re_preflight(
        repo_root=repo_root,
        slug=_SLUG,
        blocked={_STORY: detail},
        verify_commands=verify,
        prior_predicates=None if prior is None else {_STORY: prior},
    )


def test_the_flag_gate_refusal_is_a_re_preflightable_gate_read_from_its_detail() -> None:
    assert re_preflight.parse_refuse_gate(_DETAIL) == _GATE
    assert re_preflight.is_re_preflightable_gate(_GATE)
    assert _GATE in re_preflight._RE_PREFLIGHTABLE_GATES


def test_a_changed_spec_fingerprint_clears_the_flag_gate_block(tmp_path: Path) -> None:
    """AC6: the spec is edited after the refusal -> CLEARED, so the next cycle re-preflights the story."""
    _write_spec(tmp_path, "---\ntype: feature\n---\n# no flag block\n")
    prior = _predicate(tmp_path)
    _write_spec(tmp_path, "---\ntype: feature\nflag-exempt: detector-or-gate\n---\n# now exempt\n")
    assert _predicate(tmp_path).spec_fingerprint != prior.spec_fingerprint

    kept, results = _reconcile(tmp_path, prior=prior)

    assert kept == {}
    [result] = results
    assert result.decision is re_preflight.RePreflightDecision.CLEARED
    assert result.gate == _GATE
    assert result.prior_detail == _DETAIL
    assert result.predicate is not None and result.predicate.spec_fingerprint != prior.spec_fingerprint


def test_an_unchanged_spec_stays_blocked_and_rate_limited(tmp_path: Path) -> None:
    _write_spec(tmp_path, "---\ntype: feature\n---\n# no flag block\n")
    kept, results = _reconcile(tmp_path, prior=_predicate(tmp_path))

    assert kept == {_STORY: _DETAIL}
    assert [r.decision for r in results] == [re_preflight.RePreflightDecision.RATE_LIMITED]


def test_the_first_tick_after_the_refusal_rate_limits_even_with_no_prior_predicate(tmp_path: Path) -> None:
    _write_spec(tmp_path, "---\ntype: feature\n---\n# no flag block\n")
    kept, results = _reconcile(tmp_path, prior=None)

    assert kept == {_STORY: _DETAIL}
    assert [r.decision for r in results] == [re_preflight.RePreflightDecision.RATE_LIMITED]


def test_a_verify_config_change_alone_does_not_clear_the_flag_gate_block(tmp_path: Path) -> None:
    """The gate judges the spec, not the verify commands: only a spec change re-preflights it."""
    _write_spec(tmp_path, "---\ntype: feature\n---\n# no flag block\n")
    prior = _predicate(tmp_path, verify=("pytest -q",))
    kept, results = _reconcile(tmp_path, prior=prior, verify=("pytest -q", "ruff check"))

    assert kept == {_STORY: _DETAIL}
    assert [r.decision for r in results] == [re_preflight.RePreflightDecision.RATE_LIMITED]


def test_a_spec_edit_clears_the_flag_gate_block_even_when_verify_config_changed_too(tmp_path: Path) -> None:
    _write_spec(tmp_path, "---\ntype: feature\n---\n# no flag block\n")
    prior = _predicate(tmp_path, verify=("pytest -q",))
    _write_spec(tmp_path, "---\ntype: feature\nflag-exempt: docs-only\n---\n# edited, longer\n")
    kept, results = _reconcile(tmp_path, prior=prior, verify=("pytest -q", "ruff check"))

    assert kept == {}
    assert [r.decision for r in results] == [re_preflight.RePreflightDecision.CLEARED]


def test_a_spec_change_still_only_rate_limits_a_verify_gate(tmp_path: Path) -> None:
    """The new branch is scoped to ``MRS-DISP-052``: ``MRS-GATE-*`` keeps its own rule (AC3 of Story 28.18)."""
    _write_spec(tmp_path, "---\ntype: feature\n---\n# a\n")
    prior = _predicate(tmp_path, gate="MRS-GATE-001", verify=("pytest -q",))
    _write_spec(tmp_path, "---\ntype: feature\n---\n# a longer edit\n")
    kept, results = _reconcile(tmp_path, detail="MRS-GATE-001: verify failed", prior=prior, verify=("pytest -q",))

    assert _STORY in kept
    assert [r.decision for r in results] == [re_preflight.RePreflightDecision.RATE_LIMITED]


@pytest.mark.parametrize("gate", ["MRS-DISP-041", "MRS-DISP-053", "MRS-DISP-055"])
def test_the_other_dispatch_refusals_stay_out_of_the_re_preflight_set(gate: str) -> None:
    assert not re_preflight.is_re_preflightable_gate(gate)
