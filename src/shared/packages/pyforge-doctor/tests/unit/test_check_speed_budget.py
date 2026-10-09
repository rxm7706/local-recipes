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

One untimed warm-up run, then five timed ones judged by their median
(Story 41.4, DW-FU-6-6-8 / DW-FU-18-2). The first run on a cold worktree
pays for imports and an unwarmed filesystem cache, and a loaded host adds
one-off spikes; under the old max-of-three either one failed the gate with
the code unchanged (4.2s-10.5s measured on identical code). The budget
itself is unchanged: a warm median over it is still a real regression
(measured 2026-10-04: warm-up plus five runs in 10.9s, about 1.8s a run).
Not warden's 30-iteration convention -- each run costs real seconds.
"""

from __future__ import annotations

import statistics
import time
from pathlib import Path

import pytest

from pyforge.doctor.__main__ import main
from pyforge.doctor.checks import registry

# Guarded, unlike the sibling's bare `parents[6]` (review finding): at
# module scope an IndexError from a shallower-than-7-levels layout (e.g. an
# extracted sdist) would be a COLLECTION error for the whole file instead
# of the skip the docstring promises. None -> the test skips.
try:
    _REPO_ROOT: Path | None = Path(__file__).resolve().parents[6]
except IndexError:
    _REPO_ROOT = None

# PRD SM-C1's own number, adopted verbatim (not a newly-invented budget) --
# see the story spec's Design Notes for the live measurement this carries
# forward (~2.1-2.5s combined against this same monorepo, ~2x headroom).
_BUDGET_SECONDS = 5.0
_WARMUP_ITERATIONS = 1
_ITERATIONS = 5

pytestmark = pytest.mark.xdist_group(name="doctor_check_speed_budget")


def test_doctor_check_completes_within_the_five_second_budget(capsys):
    if _REPO_ROOT is None or not (_REPO_ROOT / ".claude").is_dir():
        pytest.skip("not running inside the local-recipes monorepo checkout")

    engines_suite_size = len(registry.list_checks(category="engines"))
    durations: list[float] = []
    for iteration in range(_WARMUP_ITERATIONS + _ITERATIONS):
        start = time.monotonic()
        exit_code = main(["check", str(_REPO_ROOT)])
        if iteration >= _WARMUP_ITERATIONS:
            durations.append(time.monotonic() - start)
        # Only the timing is under budget-test here -- a real environment's
        # engine availability (FAIL) or env-hygiene hits (WARN, never
        # gating) are both acceptable outcomes; a crash (any other exit) is
        # not.
        assert exit_code in {0, 2}
        # Guard against a VACUOUS pass (review finding): a fully-degraded
        # warden collapses the engines category to one instant sentinel
        # Finding, so "fast" and "broken-and-therefore-fast" would both
        # satisfy the budget. A run that did the real work always reports
        # at least the full engines suite (warden's gather is
        # all-or-nothing: healthy OR engines-missing both yield every
        # named check), plus any env findings on top.
        header = capsys.readouterr().out.splitlines()[0]
        findings_count = int(header.split(":")[1].split("finding(s)")[0])
        assert findings_count >= engines_suite_size, (
            f"only {findings_count} finding(s) -- the run degraded to a "
            "sentinel instead of doing the real end-to-end work, so this "
            "benchmark's timing is meaningless"
        )

    assert len(durations) == _ITERATIONS
    median = statistics.median(durations)
    assert median < _BUDGET_SECONDS, (
        f"doctor check took a median {median:.2f}s (timed runs: "
        f"{[f'{d:.2f}' for d in durations]}, after {_WARMUP_ITERATIONS} "
        f"warm-up) against the monorepo root -- over the documented "
        f"{_BUDGET_SECONDS}s budget (PRD SM-C1)"
    )
