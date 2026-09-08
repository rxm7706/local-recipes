"""Proves the ``cli.py`` 4-axis engine fan-out (Story 5.2, NFR-P-concurrency)
actually runs CONCURRENTLY via ``ThreadPoolExecutor`` (not the pre-5.2
sequential loop) AND that ``engine_results``/``errors``/``rungs`` are
reassembled in ``engines_to_run``'s own registration order regardless of
which future finishes first — the load-bearing invariant the story's
Boundaries call out (NFR-R3b, the existing first-registration-order-wins
engine-vs-engine finding dedupe in ``interfaces.DefaultPolicy.evaluate``).

Mirrors ``test_scan_harness.py``'s ``register_engine_for_test`` monkeypatch
convention (duplicated locally per this package's existing per-file
convention — see e.g. ``test_kev_enrichment.py``/``test_epss_enrichment.py``,
which duplicate the sibling ``run_scan``/``parse_report`` helpers rather
than cross-import a test module)."""

from __future__ import annotations

import json
import time
from importlib import resources
from pathlib import Path

import jsonschema
import pytest

from pyforge.warden import engines as engines_module
from pyforge.warden.cli import main
from pyforge.warden.interfaces import EngineResult
from pyforge.warden.models import AXIS_HYGIENE, AXIS_VULNERABILITY, Finding

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "projects"
CLEAN = FIXTURES / "clean"


_SLOW_REAL_ENGINES = (
    engines_module.DeptryEngine,
    engines_module.OsvEngine,
    engines_module.LicenseEngine,
    engines_module.CurrencyEngine,
)


def register_engine_for_test(monkeypatch, engine_cls) -> None:
    """UNLIKE ``test_scan_harness.py``'s additive helper of the same name,
    this one also DROPS the slow, real subprocess/data-driven engines
    (deptry/osv-scanner/license/currency) from whatever is currently
    registered before appending ``engine_cls`` -- mirrors
    ``test_perf_overhead.py``'s full-replace convention. This file's
    concurrency-timing assertions measure ONLY the registered stub
    engines' wall-clock overlap; a real engine's variable subprocess cost
    running concurrently alongside them would otherwise make the timing
    floor flaky for reasons unrelated to the concurrency property under
    test (Story 5.2 review finding). ``NullEngine`` (near-instant, no
    subprocess) is deliberately kept. Registration order among the
    surviving factories — and repeated calls within one test — still
    accumulate exactly like the additive helper does."""
    current = [
        factory
        for factory in engines_module._ENGINE_FACTORIES
        if factory not in _SLOW_REAL_ENGINES
    ]
    monkeypatch.setattr(
        engines_module,
        "_ENGINE_FACTORIES",
        [*current, engine_cls],
    )


def load_schema() -> dict:
    schema_file = resources.files("pyforge.warden") / "data" / "report-schema.json"
    return json.loads(schema_file.read_text(encoding="utf-8"))


def run_scan(capsys, target, *extra: str) -> tuple[int, str, str]:
    capsys.readouterr()
    rc = main(["scan", str(target), "--format", "json", *extra])
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


def parse_report(stdout: str) -> dict:
    document = json.loads(stdout)
    jsonschema.Draft202012Validator(load_schema()).validate(document)
    return document


# --- concurrency proof -------------------------------------------------------

_SLEEP_SECONDS = 0.2
# One shared, thread-safe-enough (GIL-protected plain-list-append) sink each
# stub engine records its own (name, start, end) interval into -- reset per
# test via the fixture below.
_INTERVALS: list[tuple[str, float, float]] = []


@pytest.fixture(autouse=True)
def _reset_intervals():
    _INTERVALS.clear()
    yield
    _INTERVALS.clear()


def _make_sleepy_engine(label: str, axis: str):
    """Builds a stub ``Engine`` class that sleeps ``_SLEEP_SECONDS`` inside
    ``run`` and records its own [start, end) wall-clock interval — a
    sequential loop over N such engines takes >= N * _SLEEP_SECONDS; a truly
    concurrent fan-out takes close to ONE _SLEEP_SECONDS regardless of N."""

    engine_axis = axis  # class-body assignment below would otherwise shadow
    # the enclosing parameter of the same name before it's read (class
    # bodies resolve an assigned-to name locally, like a function scope).

    class _SleepyEngine:
        name = label
        axis = engine_axis

        def run(self, target, inventory) -> EngineResult:
            start = time.monotonic()
            time.sleep(_SLEEP_SECONDS)
            end = time.monotonic()
            _INTERVALS.append((label, start, end))
            return EngineResult(findings=(), errors=(), coverage=(), axis=self.axis)

    return _SleepyEngine


def test_stub_engines_run_concurrently_not_sequentially(capsys, monkeypatch):
    """4 stub engines (on top of the real, near-instant NullEngine already
    registered) each sleep 0.2s -- sequential execution would take
    >= 5 * 0.2s = 1.0s; concurrent execution finishes close to one 0.2s
    sleep. Asserts total wall time stays well under the sequential floor
    AND that at least two intervals genuinely overlap in wall-clock time
    (the direct, non-timing-fragile half of the proof)."""
    for i in range(4):
        register_engine_for_test(
            monkeypatch, _make_sleepy_engine(f"sleepy-{i}", AXIS_HYGIENE)
        )

    t0 = time.monotonic()
    rc, out, _err = run_scan(capsys, CLEAN)
    elapsed = time.monotonic() - t0
    parse_report(out)  # still a valid, schema-conformant report
    assert rc == 0

    assert len(_INTERVALS) == 4
    sequential_floor = 4 * _SLEEP_SECONDS
    assert elapsed < sequential_floor, (
        f"scan took {elapsed:.3f}s -- expected well under the "
        f"{sequential_floor:.3f}s sequential floor if the 4 stub engines "
        "truly ran concurrently"
    )

    # A direct overlap check, independent of the aggregate-timing margin
    # above: at least one pair of intervals must overlap in wall-clock time.
    def _overlaps(a: tuple[str, float, float], b: tuple[str, float, float]) -> bool:
        return a[1] < b[2] and b[1] < a[2]

    assert any(
        _overlaps(_INTERVALS[i], _INTERVALS[j])
        for i in range(len(_INTERVALS))
        for j in range(i + 1, len(_INTERVALS))
    ), f"no two stub-engine intervals overlapped: {_INTERVALS}"


# --- result-order stability under reordered completion -----------------------


def _make_dedupe_engine(label: str, *, sleep_seconds: float, message: str):
    """A stub engine emitting a finding under the SAME id every instance of
    this helper is given, tagged by ``message`` so the survivor of
    ``DefaultPolicy.evaluate``'s engine-vs-engine dedupe (first REGISTRATION
    order wins, per ``interfaces.py``'s own docstring) is identifiable —
    ``sleep_seconds`` lets a LATER-registered instance finish FIRST, so a
    completion-order bug would silently let the wrong message win."""

    class _DedupeEngine:
        name = label
        axis = AXIS_HYGIENE

        def run(self, target, inventory) -> EngineResult:
            time.sleep(sleep_seconds)
            return EngineResult(
                findings=(
                    Finding(
                        id="hygiene:DEP002:requests",
                        axis=AXIS_HYGIENE,
                        message=message,
                        subject="requests",
                        severity=None,
                    ),
                ),
                errors=(),
                coverage=(),
                axis=self.axis,
            )

    return _DedupeEngine


def test_result_order_survives_reordered_completion(capsys, monkeypatch):
    """Registers a SLOW engine first, then a FAST engine second — both
    contend for the SAME finding id. The fast one finishes first, but the
    dedupe must still pick the FIRST-REGISTERED (slow) engine's finding,
    proving engine_results is reassembled in registration order rather than
    completion order (the exact regression a naive
    ``as_completed()``-based fan-out would introduce)."""
    register_engine_for_test(
        monkeypatch,
        _make_dedupe_engine(
            "slow-first-registered", sleep_seconds=0.3, message="from the FIRST-registered (slow) engine"
        ),
    )
    register_engine_for_test(
        monkeypatch,
        _make_dedupe_engine(
            "fast-second-registered", sleep_seconds=0.0, message="from the SECOND-registered (fast) engine"
        ),
    )

    rc, out, _err = run_scan(capsys, CLEAN)
    document = parse_report(out)
    matches = [
        f for f in document["findings"] if f["id"] == "hygiene:DEP002:requests"
    ]
    assert len(matches) == 1, "engine-vs-engine dedupe must yield exactly one finding"
    assert matches[0]["message"] == "from the FIRST-registered (slow) engine"


def test_a_late_registered_engine_error_still_lands_in_registration_order(
    capsys, monkeypatch
):
    """A companion to the dedupe proof above, on the errors[]/typed-error
    side: a FAST-crashing engine registered AFTER a SLOW-succeeding one must
    not reorder ``errors[]`` — this is a coarser check (errors[] here has
    exactly one entry either way) that the crash path shares the same
    future-collection code path as the success path, not a special one
    that could reorder independently."""
    register_engine_for_test(
        monkeypatch, _make_sleepy_engine("slow-succeeds", AXIS_VULNERABILITY)
    )

    class _FastCrashingEngine:
        name = "fast-crashes"
        axis = AXIS_VULNERABILITY

        def run(self, target, inventory) -> EngineResult:
            raise RuntimeError("fails immediately, no sleep")

    register_engine_for_test(monkeypatch, _FastCrashingEngine)

    rc, out, _err = run_scan(capsys, CLEAN)
    document = parse_report(out)
    assert rc == 2
    assert document["status"]["value"] == "error"
    (error,) = document["errors"]
    assert error["kind"] == "engine-execution-failed"
    assert "fails immediately" in error["message"]
    # The slow engine still completed and contributed no error of its own.
    assert len(_INTERVALS) == 1


def test_engine_returning_none_is_a_typed_error_not_a_silent_drop(capsys, monkeypatch):
    """A misbehaving ``Engine.run()`` returning ``None`` (violates the
    ``Engine`` protocol, but nothing enforces it at runtime) must not
    vanish through ``_instantiate_and_run_engine``'s two-slot return
    contract — review finding: ``(None, None)`` would match neither the
    success nor the error branch the caller checks, silently dropping the
    engine's outcome (no result, no error, no rung) — a regression the
    pre-5.2 sequential loop did not have (it would raise ``AttributeError``
    later on ``result.errors``, loud rather than silent, but still not the
    clean typed-error path every other crash gets)."""

    class _NoneReturningEngine:
        name = "returns-none"
        axis = AXIS_VULNERABILITY

        def run(self, target, inventory):
            return None

    register_engine_for_test(monkeypatch, _NoneReturningEngine)

    rc, out, _err = run_scan(capsys, CLEAN)
    document = parse_report(out)
    assert rc == 2
    assert document["status"]["value"] == "error"
    (error,) = document["errors"]
    assert error["kind"] == "engine-execution-failed"
    assert "returns-none" in error["message"]
    assert "None" in error["message"]
