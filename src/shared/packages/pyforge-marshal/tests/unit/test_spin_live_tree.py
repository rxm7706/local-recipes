"""``marshal spin``'s policy render (Story 3.11), driven by the tracked pyforge-marshal marshal-policy.toml.

Story 116.1 (spec-pyforge-marshal:CAP-305): the one ``test_spin.py`` test that reads the tracked tree moved here,
marked ``live_tree``; it fails, never skips, when the policy file it reads is absent. Every other spin test stays
in ``test_spin.py``.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from pyforge.marshal.adapters.harness_bmadloop import render_policy_toml
from pyforge.marshal.core import policy as policy_module

pytestmark = pytest.mark.live_tree


def test_the_real_pyforge_marshal_policy_declares_a_working_model_tier_map():
    """Regression guard for Story 3.11 (review-pass finding): the REAL,
    committed `marshal-policy.toml` (not a hand-duplicated test fixture) must
    keep its `model_tier_map` table block valid and last -- a future edit
    that appends any root-level key after it would silently nest that key
    under `model_tier_map.easy` instead of the document root, per TOML's own
    table-scoping rule (see ``test_spin.py``'s own Design Notes). Also drives the
    `easy` tier end to end, which ``test_spin.py``'s populated-vs-empty test never
    does: `easy` overrides only `dev`, so `review` must stay at its own
    unrelated `opus` baseline, not silently fall to something else."""
    real_policy_path = (
        Path(__file__).resolve().parents[6]
        / "_bmad-output"
        / "projects"
        / "pyforge-marshal"
        / "planning-artifacts"
        / "marshal-policy.toml"
    )
    assert real_policy_path.is_file(), f"tracked project policy file not present in this checkout: {real_policy_path}"

    parsed = tomllib.loads(real_policy_path.read_text(encoding="utf-8"))

    # Root-level keys survived the table placement -- the exact footgun this
    # story's own Design Notes warn about.
    assert parsed["gate_mode"] == "none"
    assert len(parsed["verify_commands"]) == 2
    assert len(parsed["landing_rules"]) == 2
    # 2026-09-13 (spec-cursor-native-tier-map / Story 33.15): every station's
    # dev/review stages name an explicit {harness, model} inline table (CAP-1)
    # so a foreign model id cannot land on the wrong adapter. 2026-09-18: the
    # ids themselves are volatile per-week config (Cursor ran out of usage and
    # the fleet moved back to claude/sonnet), so this asserts the SHAPE the
    # story established, not a pinned ladder -- pinned ids turned this test
    # red on `main` the first time the harness changed.
    # 2026-10-25: the three classes a story falls into by default must exist; an
    # operator-ruled opt-in class (`fable`, selected by a spec's `difficulty:`) may
    # sit beside them and is held to the same shape below.
    tier_map = parsed["model_tier_map"]
    assert {"heavy", "medium", "easy"} <= set(tier_map)
    for difficulty, stages in tier_map.items():
        assert "dev" in stages, difficulty
        for stage, entry in stages.items():
            assert set(entry) == {"harness", "model"}, (difficulty, stage, entry)
            assert entry["harness"] and entry["model"], (difficulty, stage, entry)
    assert set(tier_map["easy"]) == {"dev"}  # easy overrides dev only

    effective, findings = policy_module.compose(project=parsed, project_slug="pyforge-marshal", flags={})
    assert findings == ()

    rendered_easy = render_policy_toml(effective, difficulty="easy")
    parsed_easy = tomllib.loads(rendered_easy)
    easy_dev = tier_map["easy"]["dev"]
    if easy_dev["harness"] == "claude":
        # Happy path: the tier map names the adapter this render targets, so
        # the override applies as an [adapter.dev] sub-table.
        assert parsed_easy["adapter"]["dev"]["model"] == easy_dev["model"]
    else:
        # Fails-safe path (Story 33.15 CAP-2): a foreign harness's model
        # against the claude adapter is dropped entirely -- no [adapter.dev]
        # sub-table, per FR-51's "absent stage inherits [adapter].model".
        assert "dev" not in parsed_easy["adapter"]
    assert parsed_easy["adapter"]["model"] == "sonnet"
    assert parsed_easy["adapter"]["review"]["model"] == "opus"
