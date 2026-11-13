"""``pyforge.marshal.core.policy`` (Story 1.3) composed over the tracked pyforge-marshal marshal-policy.toml.

Story 116.1 (spec-pyforge-marshal:CAP-305): the two ``test_policy.py`` tests that read the tracked tree moved
here, marked ``live_tree``; each fails, never skips, when the policy file it reads is absent. Story 116.2 moved
the third, which reads every station's tracked policy. Every other policy test stays in ``test_policy.py``.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from pyforge.marshal.core import policy
from pyforge.marshal.core.policy import compose

pytestmark = pytest.mark.live_tree

_POLICY_REL = "_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml"


def _tracked_policy_path() -> Path:
    policy_path = Path(__file__).resolve().parents[6] / _POLICY_REL
    assert policy_path.is_file(), f"marshal-policy.toml not present in this checkout: {policy_path}"
    return policy_path


def test_dispatch_max_parallel_two_on_real_marshal_policy_does_not_fire_scm_clamp():
    """Story 33.8: dispatch.max_parallel=2 composes without MRS-POLICY-007 --
    that advisory applies to scm max_parallel (SEED) only, not dispatch."""
    parsed = tomllib.loads(_tracked_policy_path().read_text(encoding="utf-8"))
    effective, findings = compose(project_slug="pyforge-marshal", project=parsed, flags={})
    assert effective.dispatch.value == {"max_parallel": 2}
    codes = {f.code for f in findings}
    assert "MRS-POLICY-007" not in codes


def test_the_real_pyforge_marshal_policy_declares_no_context_block():
    """Story 46.4 regression: the tracked marshal-policy.toml no longer
    force-declares `[context]` at all -- Story 33.2's five-layer enablement
    is superseded by the repo-default `_bmad-output/policy-defaults.toml`
    block (all 5 layers on, `wire` on the `"auto"` tri-state). Per
    `_merge_field`'s wholesale-per-field (not deep-merge) composition, a
    station file declaring ANY part of `[context]` would replace the repo
    default's entire value for that station -- so the station stays
    force-override-only by declaring nothing here at all. See
    `test_dispatch_live_tree.py::test_compose_policy_on_real_repo_enables_all_context_layers_for_dispatch`
    for the fully-composed (repo-defaults + project) resolution."""
    parsed = tomllib.loads(_tracked_policy_path().read_text(encoding="utf-8"))
    assert "context" not in parsed


_PAGES_STATIONS = ("pyforge-herald", "pyforge-steward", "pyforge-atlas", "pyforge-doctor")
_DEFAULT_STATIONS = ("pyforge-marshal", "pyforge-mason", "pyforge-scribe", "pyforge-warden")


@pytest.mark.parametrize("slug", _PAGES_STATIONS + _DEFAULT_STATIONS)
def test_the_tracked_station_policies_opt_in_exactly_the_four_pages_stations(slug):
    """Story 102.1: herald, steward, atlas and doctor declare ``on-code-change`` and compose with no
    ``MRS-POLICY-002``; every other station keeps ``always``. Steward's 45-minute fix turn survives beside it."""
    repo_root = Path(__file__).resolve().parents[6]
    policy_path = repo_root / f"_bmad-output/projects/{slug}/planning-artifacts/marshal-policy.toml"
    if not policy_path.is_file():
        pytest.fail(f"{policy_path} is missing")
    parsed = tomllib.loads(policy_path.read_text(encoding="utf-8"))
    effective, findings = compose(project_slug=slug, project=parsed, flags={})
    assert "MRS-POLICY-002" not in {f.code for f in findings}
    expected = "on-code-change" if slug in _PAGES_STATIONS else "always"
    assert policy.resolve_landing_reverify(effective) == expected
    if slug == "pyforge-steward":
        assert policy.resolve_verify_fix_settings(effective).wall_clock_minutes == 45.0
