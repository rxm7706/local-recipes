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

The budget is judged on the CPU each run spends, not its wall time (Story
44.1). ``doctor check`` is single-threaded and CPU-bound: measured
2026-10-12 at ``c447946b3f``, one run spends 2.75s of CPU against 2.73s of
wall time on an idle machine, about 95% of it in its own ``env_hygiene``
scan, with only about 0.4s in child processes. CPU time therefore equals
the idle wall time the five-second promise is about, but it does not
stretch when other processes share the cores. In local ``pr-preflight``
about twenty lanes on sixteen cores stretched the same work's wall time to
medians of 5.19s-7.26s. CPU here is ``os.times()`` user plus system, for
this process and for the child processes it waited on. Time a run spends
blocked (a network wait, a sleep) is not CPU, so this measure would not see
it; ``doctor check`` is offline by design (NFR-1). Each run's wall time is
still reported beside its CPU when the budget fails.
"""

from __future__ import annotations

import os
import statistics
import subprocess
import sys
import time
from collections.abc import Callable
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


def _cpu_seconds() -> float:
    """User plus system CPU for this process and its waited-on children."""
    times = os.times()
    return times.user + times.system + times.children_user + times.children_system


def _wall_and_cpu(run: Callable[[], object]) -> tuple[float, float]:
    """Call ``run`` once and return the ``(wall, cpu)`` seconds it took.

    CPU counts this process and every child process ``run`` waited on
    (``os.times()``'s ``children_*`` fields only grow when a child is reaped),
    so a check that shells out to ``git`` or ``deptry`` is charged for them."""
    wall_start = time.monotonic()
    cpu_start = _cpu_seconds()
    run()
    return time.monotonic() - wall_start, _cpu_seconds() - cpu_start


def _burn_cpu(seconds: float) -> None:
    start = time.process_time()
    while time.process_time() - start < seconds:
        pass


def test_wall_and_cpu_counts_cpu_burned_in_process():
    _, cpu = _wall_and_cpu(lambda: _burn_cpu(0.3))
    assert cpu >= 0.25, f"0.3s of in-process CPU read as {cpu:.3f}s"


def test_wall_and_cpu_does_not_count_a_sleep():
    wall, cpu = _wall_and_cpu(lambda: time.sleep(0.3))
    assert wall >= 0.3
    assert cpu < 0.1, f"a 0.3s sleep read as {cpu:.3f}s of CPU"


def test_wall_and_cpu_counts_a_waited_child_process():
    child = "import time\nstart = time.process_time()\nwhile time.process_time() - start < 0.3:\n    pass\n"
    _, cpu = _wall_and_cpu(lambda: subprocess.run([sys.executable, "-c", child], check=True))
    assert cpu >= 0.25, f"a child burning 0.3s of CPU read as {cpu:.3f}s"


def test_doctor_check_completes_within_the_five_second_budget(capsys):
    if _REPO_ROOT is None or not (_REPO_ROOT / ".claude").is_dir():
        pytest.skip("not running inside the local-recipes monorepo checkout")

    engines_suite_size = len(registry.list_checks(category="engines"))
    cpu_runs: list[float] = []
    wall_runs: list[float] = []
    for iteration in range(_WARMUP_ITERATIONS + _ITERATIONS):
        exit_codes: list[int] = []
        wall, cpu = _wall_and_cpu(lambda: exit_codes.append(main(["check", str(_REPO_ROOT)])))
        exit_code = exit_codes[0]
        if iteration >= _WARMUP_ITERATIONS:
            cpu_runs.append(cpu)
            wall_runs.append(wall)
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

    assert len(cpu_runs) == _ITERATIONS
    median_cpu = statistics.median(cpu_runs)
    assert median_cpu < _BUDGET_SECONDS, (
        f"doctor check spent a median {median_cpu:.2f}s of CPU (judged; timed runs as cpu/wall: "
        f"{[f'{c:.2f}/{w:.2f}' for c, w in zip(cpu_runs, wall_runs, strict=True)]}, after "
        f"{_WARMUP_ITERATIONS} warm-up) against the monorepo root -- over the documented "
        f"{_BUDGET_SECONDS}s budget (PRD SM-C1)"
    )
