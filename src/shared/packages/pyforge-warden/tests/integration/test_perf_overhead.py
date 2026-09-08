"""Stubbed-engine orchestration/report overhead benchmark (Story 5.2,
NFR-P-warm) -- ``architecture.md:350`` flagged this threshold as needing
calibration once a reference corpus existed; this story IS that
calibration point.

All 4 axis engines are replaced (not merely appended -- see
``_replace_engines_for_test`` below) with instant-return stubs, mirroring
``test_scan_harness.py``'s ``register_engine_for_test``/``FindingsOnlyEngine``
pattern, so the measured wall-clock is orchestration/report cost only
(config load, discovery, extraction, the ``ThreadPoolExecutor`` fan-out +
join, policy evaluation, report assembly/render) -- NEVER real deptry/
osv-scanner subprocess timing, per NFR-P-warm's "engines-stubbed"
requirement.

The scan target is ``tests/fixtures/corpus/recipes/types-lxml`` -- the
corpus's MEDIAN-sized manifest by file size, measured when this story
harvested the corpus (1,979 files) -- a representative, moderate real
recipe rather than the smallest/largest outlier or a hand-picked toy
fixture.

``PERF_OVERHEAD_P95_BUDGET_SECONDS`` is machine-relative (recorded
alongside ``platform.platform()``/``os.cpu_count()`` in the assertion
message so a failure names the hardware it ran on) -- measured p95 on the
reference machine this story calibrated on: ~6ms (16 logical CPUs). The
committed budget carries substantial headroom (two orders of magnitude)
over that measurement so the gate tolerates slower/busier CI runners
without becoming vacuous; it exists to catch a genuine orchestration
regression (e.g. accidentally serializing the engine fan-out again, or an
O(n) become O(n^2) report-assembly bug), not to chase the exact
millisecond figure. May be recalibrated on a materially different
reference machine; never loosened just to paper over a real regression on
the SAME class of hardware."""

from __future__ import annotations

import json
import math
import os
import platform
import time
from pathlib import Path

from pyforge.warden import engines as engines_module
from pyforge.warden.cli import main
from pyforge.warden.interfaces import EngineResult
from pyforge.warden.models import (
    AXIS_CURRENCY,
    AXIS_HYGIENE,
    AXIS_LICENSE,
    AXIS_VULNERABILITY,
)

REPRESENTATIVE_TARGET = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "corpus"
    / "recipes"
    / "types-lxml"
)

PERF_ITERATIONS = 30
PERF_OVERHEAD_P95_BUDGET_SECONDS = 1.0


def _replace_engines_for_test(monkeypatch, engine_classes) -> None:
    """UNLIKE ``test_scan_harness.py``'s ADDITIVE ``register_engine_for_test``
    convention, this REPLACES the engine registry outright -- the whole
    point of this benchmark is measuring overhead with EVERY axis engine
    stubbed, never a real engine running alongside the stubs."""
    monkeypatch.setattr(engines_module, "_ENGINE_FACTORIES", list(engine_classes))


def _make_stub_engine(label: str, axis: str):
    engine_axis = axis  # see test_engine_parallelism.py's identical note:
    # a same-named class-body assignment shadows the enclosing parameter.

    class _StubEngine:
        name = label
        axis = engine_axis

        def run(self, target, inventory) -> EngineResult:
            return EngineResult(findings=(), errors=(), coverage=(), axis=self.axis)

    return _StubEngine


def _p95(samples: list[float]) -> float:
    """Nearest-rank p95 (simple, dependency-free, no interpolation
    subtleties): the smallest sample at or above the 95th percentile rank."""
    ordered = sorted(samples)
    rank = max(1, math.ceil(0.95 * len(ordered)))
    return ordered[rank - 1]


def test_stubbed_engine_overhead_holds_the_p95_budget(capsys, monkeypatch):
    assert REPRESENTATIVE_TARGET.is_dir(), (
        f"{REPRESENTATIVE_TARGET} missing -- run scripts/harvest_corpus.py"
    )
    stubs = [
        _make_stub_engine("stub-hygiene", AXIS_HYGIENE),
        _make_stub_engine("stub-vulnerability", AXIS_VULNERABILITY),
        _make_stub_engine("stub-license", AXIS_LICENSE),
        _make_stub_engine("stub-currency", AXIS_CURRENCY),
    ]
    _replace_engines_for_test(monkeypatch, stubs)

    samples: list[float] = []
    for _ in range(PERF_ITERATIONS):
        capsys.readouterr()
        start = time.perf_counter()
        main(["scan", str(REPRESENTATIVE_TARGET), "--format", "json"])
        elapsed = time.perf_counter() - start
        captured = capsys.readouterr()
        # A schema-valid report every iteration -- a stub-engine crash would
        # silently invalidate the timing (e.g. measuring the last-resort
        # exception net's traceback formatting instead of a real scan).
        document = json.loads(captured.out)
        assert document["errors"] == [], document["errors"]
        samples.append(elapsed)

    p95 = _p95(samples)
    reference = f"{platform.platform()} / {os.cpu_count()} logical CPUs"
    assert p95 <= PERF_OVERHEAD_P95_BUDGET_SECONDS, (
        f"stubbed-engine scan p95={p95 * 1000:.1f}ms over "
        f"{PERF_ITERATIONS} iterations exceeds the committed "
        f"{PERF_OVERHEAD_P95_BUDGET_SECONDS * 1000:.0f}ms budget "
        f"(reference machine: {reference}; min={min(samples) * 1000:.1f}ms, "
        f"max={max(samples) * 1000:.1f}ms)"
    )
