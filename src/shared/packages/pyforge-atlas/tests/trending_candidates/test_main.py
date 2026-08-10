"""CLI wrapper tests (Story 13.3, CAP-3) — ``python -m pyforge.atlas.trending_candidates``.

Exercises ``main(argv)`` directly (mirrors ``tests/test_main_version.py``'s
``from pyforge.atlas.__main__ import main`` pattern): a real ``DataCatalog`` +
monkeypatched ``bootstrapped_session`` end-to-end for the ``--json`` happy path (its
output must match ``query.query_trending_candidates``'s own return, since both the CLI
and the MCP tool delegate to the SAME function), and a bad ``--tier`` value for the
CLI's ``ValueError`` -> stderr + exit 1 contract.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from pyforge.atlas.trending_candidates import query
from pyforge.atlas.trending_candidates.__main__ import main

_FIXTURE_DF = pd.DataFrame(
    [
        {
            "repo_full_name": "alice/libfoo",
            "repo_url": "https://github.com/alice/libfoo",
            "description": None,
            "language": "Python",
            "stars_total": 1200,
            "stars_today": 5,
            "forks_total": 1,
            "period": "weekly",
            "source": "html_scrape",
            "fetched_at": 1_700_000_000,
            "pypi_name": "libfoo",
            "tier": "1",
            "reason": "pure-python packaging shape, OSI-approved license MIT",
        }
    ]
)


def test_json_output_matches_query_trending_candidates(seed_catalog, capsys):
    seed_catalog(_FIXTURE_DF)

    exit_code = main(["--json"])
    captured = capsys.readouterr()

    expected = query.query_trending_candidates()

    assert exit_code == 0
    # The LAST non-empty line is our own plain `print(json.dumps(envelope))` call --
    # robust to kedro's own one-time bootstrap log noise (a genuine, pre-existing
    # framework side effect this test must tolerate, not assert away) landing ahead
    # of it on stdout.
    last_line = [line for line in captured.out.splitlines() if line.strip()][-1]
    assert json.loads(last_line) == expected


def test_table_output_is_the_default_and_is_not_json(seed_catalog, capsys):
    seed_catalog(_FIXTURE_DF)

    exit_code = main([])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "alice/libfoo" in captured.out
    with pytest.raises(json.JSONDecodeError):
        json.loads(captured.out)


def test_bad_tier_exits_1_with_stderr_message():
    """No `seed_catalog` fixture: validation fails before any session/catalog touch."""
    exit_code = main(["--tier", "bogus"])

    assert exit_code == 1


def test_bad_tier_message_names_the_bad_value(capsys):
    exit_code = main(["--tier", "bogus"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "bogus" in captured.err
