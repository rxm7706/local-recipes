"""Attended probe: the hub signs in through Keycloak and a ``small-instance`` server spawns (steward Story 118.6;
spec-pyforge-steward CAP-177; the observable of Story 118.2 AC2).

``https://hub.<domain>`` goes through ``/hub/oauth_login`` to Keycloak and back through ``/hub/oauth_callback``, then
``/hub/api/user`` names the bootstrap admin. A ``POST /hub/spawn profile=small-instance`` must reach ``ready``
within five minutes, and the probe then stops the server it started. It refuses to run over a server the admin
already has.
"""

from __future__ import annotations

import nkp_probes
import pytest

# Story 117.4 (spec-pyforge-steward:CAP-175): the directory's conftest hands the repo root to nkp_probes.connect,
# so every module here is marked live_tree and the station-tests trigger map routes what they read to steward's
# live-tree half. Neither half collects tests/integration; pyforge-steward-nkp-probes does (Story 118.6).
pytestmark = pytest.mark.live_tree


def test_the_hub_signs_in_through_keycloak_and_a_small_instance_server_spawns(nkp: nkp_probes.NkpCluster) -> None:
    browser = nkp.browser()
    user = nkp_probes.hub_signin(browser, nkp.outputs)
    if user.get("name") != nkp_probes.ADMIN_USER:
        pytest.fail(f"the hub signed in {user.get('name')!r}, not {nkp_probes.ADMIN_USER!r}", pytrace=False)
    server = nkp_probes.spawn_and_stop(browser, nkp.outputs)
    options = server.get("user_options")
    profile = options.get("profile") if isinstance(options, dict) else None
    if profile not in (None, nkp_probes.SPAWN_PROFILE):
        pytest.fail(f"the ready server ran profile {profile!r}, not {nkp_probes.SPAWN_PROFILE!r}", pytrace=False)
