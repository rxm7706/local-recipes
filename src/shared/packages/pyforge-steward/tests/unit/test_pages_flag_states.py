"""Story 102.2: pages_duty flag gates deploy-when-changed (CAP-168 / CAP-4)."""

from __future__ import annotations

import json

from pyforge.steward.pages import build_json, decide_deploy
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states

flag_provider = make_flag_provider_fixture()


@flag_states("pyforge.steward.pages_duty")
def test_decide_deploy_respects_flag_states(flag_provider: dict[str, bool]) -> None:
    digest = "deadbeef"
    live = json.dumps(build_json(digest, "sha", "1", "2026-10-14T00:00:00Z"))
    flag_on = flag_provider["pyforge.steward.pages_duty"]
    result = decide_deploy(digest, live, flag_on=flag_on)
    if flag_on:
        assert result is False
    else:
        assert result is True
