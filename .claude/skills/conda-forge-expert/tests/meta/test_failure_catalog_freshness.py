"""Meta: failure-catalog.yaml stays in sync with SKILL.md (Story 7.1).

The committed .claude/skills/conda-forge-expert/config/failure-catalog.yaml
is a derived, generated artifact -- `failure_catalog_generator.py` is a pure
function of SKILL.md's "Recipe Authoring Gotchas" corpus. This test proves
"hand edits are detectably wrong": it runs the generator's `--check` mode
against the REAL, live SKILL.md and the committed catalog, and asserts
success. A stray hand-edit to the catalog, or a SKILL.md gotcha edit without
regenerating, reds this test.

This is deliberately narrower than a standing CI drift/lint gate resolving
`enforced_by` pointers against the live check surface -- that's Story 7.2.
"""
from __future__ import annotations

import pytest


@pytest.mark.meta
def test_failure_catalog_check_passes_against_live_skill_md(script_runner):
    rc, out, err = script_runner("failure_catalog_generator.py", "--check", timeout=30)
    assert rc == 0, (
        "failure-catalog.yaml is out of sync with SKILL.md's gotcha corpus. "
        "Regenerate with: pixi run -e local-recipes generate-failure-catalog\n"
        f"stdout:\n{out}\nstderr:\n{err}"
    )
