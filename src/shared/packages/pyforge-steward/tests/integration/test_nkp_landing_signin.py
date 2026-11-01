"""Attended probe: the landing SPA signs in through Keycloak as the bootstrap admin (steward Story 118.6;
spec-pyforge-steward CAP-177; the observable of Story 118.1 AC2).

The landing page's Keycloak client (``nebari-system-nebari-landing-spa``, realm ``nebari``) runs an
authorization-code flow with PKCE (S256) back to ``https://<domain>/``. The token it mints names the bootstrap admin.
The admin password comes from ``nic outputs --show-secrets`` at run time and is never stored.
"""

from __future__ import annotations

import nkp_probes
import pytest

# Story 117.4 (spec-pyforge-steward:CAP-175): the directory's conftest hands the repo root to nkp_probes.connect,
# so every module here is marked live_tree and the station-tests trigger map routes what they read to steward's
# live-tree half. Neither half collects tests/integration; pyforge-steward-nkp-probes does (Story 118.6).
pytestmark = pytest.mark.live_tree


def test_the_landing_spa_signs_in_through_keycloak_as_the_bootstrap_admin(nkp: nkp_probes.NkpCluster) -> None:
    signin = nkp_probes.landing_signin(nkp)
    username = signin.claims.get("preferred_username")
    if username != nkp_probes.ADMIN_USER:
        pytest.fail(
            f"the landing SPA's token names preferred_username={username!r}, not {nkp_probes.ADMIN_USER!r}",
            pytrace=False,
        )
