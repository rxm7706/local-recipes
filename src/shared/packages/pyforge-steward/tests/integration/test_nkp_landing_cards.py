"""Attended probe: the landing page shows the JupyterHub and Nebi cards, both healthy (steward Story 118.6;
spec-pyforge-steward CAP-177; the observable of Story 118.2 AC2).

The landing page's ``/api/v1/services`` is read with the SPA's bearer token for the bootstrap admin. It must list a
``JupyterHub`` card and a ``Nebi`` card, each with ``health.status`` ``healthy``.
"""

from __future__ import annotations

import nkp_probes
import pytest

# Story 117.4 (spec-pyforge-steward:CAP-175): the directory's conftest hands the repo root to nkp_probes.connect,
# so every module here is marked live_tree and the station-tests trigger map routes what they read to steward's
# live-tree half. Neither half collects tests/integration; pyforge-steward-nkp-probes does (Story 118.6).
pytestmark = pytest.mark.live_tree


def test_the_landing_page_shows_the_jupyterhub_and_nebi_cards_healthy(nkp: nkp_probes.NkpCluster) -> None:
    signin = nkp_probes.landing_signin(nkp)
    cards = nkp_probes.landing_cards(nkp.browser(), nkp.outputs, signin.access_token)
    problems = nkp_probes.card_problems(cards)
    if problems:
        seen = ", ".join(f"{card.name}={card.health}" for card in cards) or "none"
        pytest.fail(f"landing cards: {'; '.join(problems)} (cards seen: {seen})", pytrace=False)
