"""Tests for _bmad/skf/shared/scripts/skf-provenance-gap-dispatch.py (Story 27.1)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = REPO_ROOT / "_bmad/skf/shared/scripts/skf-provenance-gap-dispatch.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("skf_provenance_gap_dispatch", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_classify_retro_mirror_alone_does_not_override_unresolved():
    m = _load_module()
    status, prior = m._classify(["retro-mirror"])
    assert status == m._UNRESOLVED
    assert prior is None


def test_classify_demoted_exclude_wins_over_later_retro_mirror():
    m = _load_module()
    status, prior = m._classify(["demoted-exclude", "retro-mirror"])
    assert status == m._PRE_DECIDED_DEMOTED
    assert prior == "demoted-exclude"


def test_classify_earlier_skip_or_promotion_stands_over_later_retro_mirror():
    m = _load_module()
    assert m._classify(["skipped", "retro-mirror"]) == (m._PRE_DECIDED_SKIPPED, "skipped")
    assert m._classify(["promoted", "retro-mirror"]) == (m._ALREADY_IN_SCOPE, "promoted")
    assert m._classify(["retro-mirror", "promoted"]) == (m._ALREADY_IN_SCOPE, "promoted")


def test_skill_brief_schema_constrains_amendment_action_to_known_values():
    schema = json.loads(
        (REPO_ROOT / "_bmad/skf/shared/scripts/schemas/skill-brief.v1.json").read_text(encoding="utf-8")
    )
    action = schema["properties"]["scope"]["properties"]["amendments"]["items"]["properties"]["action"]
    assert "retro-mirror" in action["enum"]
    assert {"promoted", "skipped", "demoted-include", "demoted-exclude"} <= set(action["enum"])
