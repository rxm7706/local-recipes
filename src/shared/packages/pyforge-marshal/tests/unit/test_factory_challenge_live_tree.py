"""Epic 113: ``marshal factory challenge`` read against this checkout's settings, station policies and overrides.

Story 116.3 (spec-pyforge-marshal:CAP-305): the five ``test_factory_challenge.py`` tests that read this checkout
outside the package -- ``.claude/settings.json``, every station's tracked ``marshal-policy.toml`` and the repo
default composed from the root, and ``_bmad/custom/bmad-retrospective.toml`` -- moved here, marked ``live_tree``;
the root is found when a test runs, never at import, and a missing file fails the test, never skips it. Every other
challenge test stays in ``test_factory_challenge.py``, which drives a fixture repository.
"""

from __future__ import annotations

import itertools
import json
import re
import tomllib
from pathlib import Path

import pytest
from pyforge.core.roster import STATIONS, long_form
from test_factory_challenge import SLUG

from pyforge.marshal.cli import challenge as cli
from pyforge.marshal.cli import config as config_cli
from pyforge.marshal.core import challenge as core

pytestmark = pytest.mark.live_tree


def _repo_root() -> Path:
    # tests/unit -> tests -> pyforge-marshal -> packages -> shared -> src -> this checkout's root, found when a
    # test runs, never at import
    return Path(__file__).resolve().parents[6]


def test_the_repo_pins_and_enables_the_plugin() -> None:
    settings = json.loads((_repo_root() / ".claude/settings.json").read_text(encoding="utf-8"))
    assert settings["enabledPlugins"][core.EGM_PLUGIN_ID] is True
    assert settings["extraKnownMarketplaces"]["egm"]["source"]["repo"] == core.EGM_MARKETPLACE_REPO


def test_a_sonnet_renders_on_all_eight_live_stations() -> None:
    """Story 113.16 AC1, AC3, read from the live policies: the comment's example renders on every station; the
    ``easy`` tier leaves ``review`` on its baseline, so ``opus`` stays a session model; Fable refuses only on marshal."""
    sonnet = core.ChallengeConfig(enabled=True, stages=("mint",), model="claude-sonnet-5-5")
    fable = core.ChallengeConfig(enabled=True, stages=("mint",), model="claude-fable-5-1")
    for slug in (long_form(station) for station in STATIONS):
        effective = cli.compose_effective(slug)
        assert cli.model_refusals(sonnet, slug=slug, effective=effective) == [], slug
        assert "opus" in cli.session_models(effective) and "sonnet" not in cli.session_models(effective), slug
        refused = cli.model_refusals(fable, slug=slug, effective=effective)
        assert bool(refused) is (slug == "pyforge-marshal"), slug
        assert "marshal factory spin" in " ".join(
            cli.model_refusals(sonnet, slug=slug, effective=effective, stage="drift")
        )
        drift = cli.model_refusals(fable, slug=slug, effective=effective, stage="drift")
        assert bool(drift) is (slug == "pyforge-marshal"), slug


def test_the_catalog_sonnet_is_an_id_claude_launches() -> None:
    """Story 113.16 AC4: ``claude --model sonnet-5`` exits 1 (``claude-code:unrecognized_model``), so the catalog names
    ``claude-sonnet-5-5`` at the same rates."""
    text = config_cli.conventional_project_policy_path(SLUG).read_text(encoding="utf-8")
    models = tomllib.loads(text)["model_cost_catalog"]["providers"]["anthropic"]["models"]
    assert "sonnet-5" not in models
    assert models["claude-sonnet-5-5"] == {
        "input_per_million": 2.0,
        "output_per_million": 10.0,
        "cache_read_per_million": 0.2,
        "cache_write_per_million": 2.5,
    }


def _documented_example_model(text: str) -> str:
    """The ``model`` of the commented ``[challenge]`` shape in marshal-policy.toml."""
    lines = text.splitlines()
    start = lines.index("#   [challenge]")
    block = itertools.takewhile(lambda line: line.startswith("#"), lines[start + 1 :])
    (model,) = (m.group(1) for line in block if (m := re.match(r'#\s+model = "([^"]+)"', line)))
    return model


def test_the_documented_example_renders_and_marshal_s_frontier_model_refuses_on_marshal() -> None:
    """Story 113.9 AC4 (amended by Story 113.16): the marshal-policy.toml comment example names ``claude-sonnet-5-5``,
    which renders on marshal; ``claude-fable-5-1``, marshal's own frontier model, refuses there with a reason naming
    it; neither marshal-policy.toml nor the repo default declares ``[challenge]``."""
    path = config_cli.conventional_project_policy_path(SLUG)
    text = path.read_text(encoding="utf-8")
    assert "challenge" not in tomllib.loads(text)
    repo_defaults, _ = config_cli.read_repo_policy_defaults()
    assert "challenge" not in repo_defaults
    example = _documented_example_model(text)
    assert example == "claude-sonnet-5-5"
    marshal = cli.compose_effective(SLUG)
    example_config = core.config_from_block({"enabled": True, "stages": list(core.STAGES), "model": example})
    assert cli.model_refusals(example_config, slug=SLUG, effective=marshal) == []

    fable = "claude-fable-5-1"
    frontier = dict(marshal.model_tier_map.value)["frontier"]
    assert frontier["dev"]["model"] == frontier["review"]["model"] == fable
    fable_config = core.config_from_block({"enabled": True, "stages": list(core.STAGES), "model": fable})
    (reason,) = cli.model_refusals(fable_config, slug=SLUG, effective=marshal)
    assert reason.startswith(f"[challenge].model {fable!r} is the dispatching session's own model ({fable})")


def test_the_retrospective_override_names_the_drift_verb() -> None:
    text = (_repo_root() / "_bmad/custom/bmad-retrospective.toml").read_text(encoding="utf-8")
    assert "marshal factory challenge --project pyforge-marshal --stage drift --epic" in text
    assert "pyforge.marshal.egm_retro_drift" in text
