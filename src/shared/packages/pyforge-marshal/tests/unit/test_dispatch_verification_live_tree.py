"""Dispatch independent verification (Story 22.3, CAP-3), read against every tracked story spec.

Story 116.1 (spec-pyforge-marshal:CAP-305): the one ``test_dispatch_verification.py`` test that reads the tracked
tree moved here, marked ``live_tree``; it fails, never skips, when the story specs it reads are absent. Every other
dispatch-verification test stays in ``test_dispatch_verification.py``, which keeps the pinned command literals this
test imports.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from test_dispatch_verification import DEFERRED_WORK_CHECK, LINT_TYPES, PYFORGE_CORE_TEST

from pyforge.marshal.adapters.harness_bmadloop import _SURFACE_RECONCILE_COMMAND
from pyforge.marshal.core import gate, policy, spec_binding
from pyforge.marshal.dispatch_verify import _verify_commands_with_surface_guard

pytestmark = pytest.mark.live_tree


def test_every_tracked_story_spec_binds_the_same_with_lint_types_widened() -> None:
    """Story 79.2, AC4, against the live tree: for every tracked story spec
    of every station, widening the policy's commands with the derived
    ``lint-types`` lane adds no ``MRS-GATE-010``/``MRS-GATE-011`` finding the
    pre-79.2 widening (station commands + the S-13.7 guard) did not already
    report -- ``gate.check_spec_binding`` is one-directional.

    Story 83.2: extends to include the new whole-tree check commands."""
    repo_root = Path(__file__).resolve().parents[6]
    spec_paths = sorted(repo_root.glob("_bmad-output/projects/*/planning-artifacts/specs/spec-*.md"))
    assert spec_paths, f"no tracked story specs in this checkout: {repo_root}"
    effective_by_slug: dict[str, policy.EffectivePolicy] = {}
    checked = 0
    for spec_path in spec_paths:
        slug = spec_path.parents[2].name
        if slug not in effective_by_slug:
            policy_path = spec_path.parents[1] / "marshal-policy.toml"
            project = tomllib.loads(policy_path.read_text(encoding="utf-8")) if policy_path.is_file() else {}
            effective_by_slug[slug], _ = policy.compose(project_slug=slug, project=dict(project), flags={})
        effective = effective_by_slug[slug]
        declared = spec_binding.parse_success_signal(spec_path.read_text(encoding="utf-8"))
        before = (*effective.verify_commands.value, _SURFACE_RECONCILE_COMMAND)
        widened = _verify_commands_with_surface_guard(effective)
        assert LINT_TYPES in widened
        assert PYFORGE_CORE_TEST in widened
        assert DEFERRED_WORK_CHECK in widened
        before_messages = {f.message for f in gate.check_spec_binding(declared, before)}
        after_messages = {f.message for f in gate.check_spec_binding(declared, widened)}
        assert after_messages <= before_messages, (spec_path.name, after_messages - before_messages)
        checked += 1
    assert checked == len(spec_paths)
