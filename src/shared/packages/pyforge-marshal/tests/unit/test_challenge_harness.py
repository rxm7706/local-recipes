"""Story 113.1 (CAP-298): the challenge session's argv comes from the packaged claude profile."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.marshal.adapters import challenge_harness as harness
from pyforge.marshal.core.harness_profile import load_packaged_profiles


def test_argv_widens_the_profile_settings_with_plugin_cache_read_rules(tmp_path: Path) -> None:
    profile = load_packaged_profiles()["claude"]
    rules = harness.plugin_cache_read_rules(tmp_path / "plugins")
    run_dir = tmp_path / "run"
    argv = harness.render_argv(
        profile, prompt="PROMPT", model="claude-fable-5-1", session_id="sid", read_rules=rules, run_dir=run_dir
    )
    settings = json.loads(argv[argv.index("--settings") + 1])
    assert settings["pluginConfigs"]  # the profile's own settings survive
    allow = settings["permissions"]["allow"]
    assert set(rules) <= set(allow) and set(harness.ORCHESTRATOR_TOOLS) <= set(allow)
    assert f"Write(/{run_dir}/**)" in allow and "Write" not in allow and "Bash" not in allow
    assert set(harness.DENIED_TOOLS) <= set(settings["permissions"]["deny"])
    assert argv[argv.index("--permission-mode") + 1] == "default" and "bypassPermissions" not in argv
    assert all(rule.startswith("Read(//") and "/cache/egm/egm/*/" in rule for rule in rules)
    assert argv[-1] == "PROMPT" and "sid" in argv
    assert "--model" in argv and "{model_args}" not in argv


def test_an_unrenderable_settings_value_is_an_error() -> None:
    with pytest.raises(harness.ChallengeHarnessError):
        harness.widen_settings("{not json", [])
