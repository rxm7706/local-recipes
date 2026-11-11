"""Unit tests for ``pyforge.core.roster`` (Story 59.6, CAP-137).

Covers: the roster is exactly the eight declared stations, and
``long_form`` derives the ``pyforge-<station>`` path/package/env form.
The check that the roster matches ``docs/governance/guild-roster.json``'s
``stations`` key reads the repository, so it lives in
``test_roster_matches_the_guild_roster.py`` in the live-tree half
(Story 117.1, spec-pyforge-core:CAP-14).
"""

from __future__ import annotations

from pyforge.core.roster import STATIONS, long_form


def test_stations_is_eight_unique_names():
    assert len(STATIONS) == 8
    assert len(set(STATIONS)) == 8


def test_long_form_prefixes_pyforge():
    assert long_form("steward") == "pyforge-steward"
    assert long_form("mason") == "pyforge-mason"


def test_long_form_covers_every_station():
    assert {long_form(s) for s in STATIONS} == {f"pyforge-{s}" for s in STATIONS}
