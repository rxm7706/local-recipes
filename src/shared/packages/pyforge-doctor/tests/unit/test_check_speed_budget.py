"""NFR-4 speed-budget benchmark for ``doctor check`` (Story 1.5, PRD SM-C1's
"five-second pre-flight promise"). A REAL, UNMOCKED end-to-end run against
this monorepo's own root -- unlike ``pyforge-warden``'s orchestration-only
``test_perf_overhead.py`` (which stubs real engines to isolate code-level
regressions), Doctor's whole NFR-4 claim is about actual wall-clock, so
nothing here is mocked.

Repo-root resolution mirrors ``test_checks_env_hygiene.py``'s own
``_REPO_ROOT = Path(__file__).resolve().parents[6]`` idiom (this file sits
at the identical ``tests/unit/`` depth, so the same parent count lands at
the monorepo root) -- skipped outside a monorepo checkout (no ``.claude/``
directory present), mirroring that file's own skip idiom for the golden
``_http.py`` fixture.

Only 2-3 iterations (not warden's 30-iteration convention): each run costs
real wall-clock seconds against this repo's own tree, so a larger iteration
count would make the whole suite noticeably slower for no extra signal --
the max (not a percentile) is the one number that matters for a hard
pre-flight budget.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from pyforge.doctor.__main__ import main

_REPO_ROOT = Path(__file__).resolve().parents[6]

# PRD SM-C1's own number, adopted verbatim (not a newly-invented budget) --
# see the story spec's Design Notes for the live measurement this carries
# forward (~2.1-2.5s combined against this same monorepo, ~2x headroom).
_BUDGET_SECONDS = 5.0
_ITERATIONS = 3


def test_doctor_check_completes_within_the_five_second_budget(capsys):
    if not (_REPO_ROOT / ".claude").is_dir():
        pytest.skip("not running inside the local-recipes monorepo checkout")

    durations: list[float] = []
    for _ in range(_ITERATIONS):
        start = time.monotonic()
        exit_code = main(["check", str(_REPO_ROOT)])
        durations.append(time.monotonic() - start)
        # Only the timing is under test here -- a real environment's engine
        # availability (FAIL) or env-hygiene hits (WARN, never gating) are
        # both acceptable outcomes; a crash (any other exit) is not.
        assert exit_code in {0, 2}

    capsys.readouterr()  # drain captured output, not asserted on here

    assert max(durations) < _BUDGET_SECONDS, (
        f"doctor check took {max(durations):.2f}s (iterations: "
        f"{[f'{d:.2f}' for d in durations]}) against the monorepo root -- "
        f"over the documented {_BUDGET_SECONDS}s budget (PRD SM-C1)"
    )
