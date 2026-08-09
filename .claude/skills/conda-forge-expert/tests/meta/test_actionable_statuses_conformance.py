"""Conformance: Doctor's restated ``ACTIONABLE_STATUSES`` still equals the
harness's own (AD-13, Story 6.7).

WHY THIS FILE EXISTS
--------------------
``scripts/forward_dependency_check.py`` imported
``bmad_loop.sprintstatus.ACTIONABLE_STATUSES`` -- *derived, never restated*, so
the check could not drift from the engine it reasons about. Story 6.7 re-homed
that detector into Doctor as ``pyforge.doctor.sources.deps``, and AD-13 dropped
the import: Doctor is a lean package whose verdicts must not depend on the
machinery they judge (AD-11), and a ``bmad-loop`` resolution failure would
otherwise take Doctor's whole CLI down with it.

The invariant was not dropped. It MOVED -- from a runtime import to this
test-time equality assertion. This file IS the invariant. If it stops running,
or starts skipping, Doctor's copy can silently diverge from the engine and the
forward-dependency verdict becomes confidently wrong rather than merely absent,
which is strictly worse.

THREE PROPERTIES THIS TEST MUST KEEP
------------------------------------
1. **It imports ``bmad_loop`` unconditionally and FAILS when absent -- never
   skips.** This is a deliberate deviation from its sibling
   ``test_forward_dependency_check.py``, which guards the same import with
   ``pytest.importorskip``. That is correct there (it is skipping a whole
   module's worth of behavioural tests) and would be fatal here: a conformance
   assertion that skips when its comparand is missing evaporates in exactly the
   environment where nobody is watching. ``unpushed_work_check.py``'s own
   docstring names this failure class -- *"a gate reporting success because it
   is standing somewhere the failure cannot occur."*

   This suite runs under ``pixi run -e local-recipes test``, and
   ``bmad-loop >=0.9.0`` is a declared dependency of that environment, so
   absence is a real defect worth failing on, not an environment quirk.

2. **It asserts SET EQUALITY, not membership.** A subset/superset check passes
   when upstream ADDS a status, which is precisely the drift worth catching:
   Doctor would keep asserting a rule the engine no longer follows.

3. **It reads Doctor's constant as an AST literal, never by importing
   ``pyforge.doctor``** -- which is not installed in ``local-recipes`` anyway.
   That also means a future edit turning the constant into a computed value
   fails here loudly instead of silently defeating the comparison.

KNOWN LIMITATION (recorded, not papered over)
---------------------------------------------
This test cannot run in CI: no workflow runs this meta-suite, and CI's detector
job uses plain ``setup-python`` with no pixi and therefore no ``bmad_loop`` to
compare against. It runs at landing time, under the same command the landing
protocol already invokes. Same *missing observation plane* the ``scope=runtime``
detectors live with -- a named condition in this repo, not a new one.
"""

from __future__ import annotations

import ast
from pathlib import Path

# Deliberately NOT pytest.importorskip -- see property 1 above. An ImportError
# here is the failure this file exists to produce.
from bmad_loop.sprintstatus import ACTIONABLE_STATUSES as HARNESS_ACTIONABLE

REPO_ROOT = Path(__file__).resolve().parents[5]
DOCTOR_DEPS = (
    REPO_ROOT
    / "src"
    / "shared"
    / "packages"
    / "pyforge-doctor"
    / "src"
    / "pyforge"
    / "doctor"
    / "sources"
    / "deps.py"
)
CONSTANT = "ACTIONABLE_STATUSES"


def _restated_literal() -> frozenset[str]:
    """Doctor's ``ACTIONABLE_STATUSES``, read as a literal without importing it.

    Accepts ``frozenset({...})`` and a bare set literal. Anything else -- a
    computed value, a name reference, a comprehension -- raises, because the
    equality assertion below would otherwise be comparing against something
    this test cannot actually verify.
    """
    tree = ast.parse(DOCTOR_DEPS.read_text(encoding="utf-8"), filename=str(DOCTOR_DEPS))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(t, ast.Name) and t.id == CONSTANT for t in node.targets
        ):
            continue
        value = node.value
        # frozenset({...}) — unwrap the call to its single literal argument.
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "frozenset"
            and len(value.args) == 1
        ):
            value = value.args[0]
        try:
            literal = ast.literal_eval(value)
        except ValueError as exc:  # pragma: no cover - defended, not expected
            raise AssertionError(
                f"{CONSTANT} in {DOCTOR_DEPS} is not a literal ({exc}). AD-13 "
                "requires a plain literal of str: this conformance test reads it "
                "with ast, so a computed value would defeat the comparison "
                "rather than trip it."
            ) from exc
        if not isinstance(literal, (set, frozenset)):
            raise AssertionError(
                f"{CONSTANT} in {DOCTOR_DEPS} evaluated to "
                f"{type(literal).__name__}, expected a set literal."
            )
        return frozenset(literal)
    raise AssertionError(
        f"{CONSTANT} not found as a module-level assignment in {DOCTOR_DEPS}. "
        "AD-13's invariant cannot be checked — if the constant moved, move this "
        "test with it rather than deleting it."
    )


def test_doctor_source_exists() -> None:
    assert DOCTOR_DEPS.is_file(), (
        f"{DOCTOR_DEPS} is missing — Story 6.7's source module is what this "
        "conformance test guards."
    )


def test_restated_constant_is_a_literal_set_of_str() -> None:
    restated = _restated_literal()
    assert restated, f"{CONSTANT} is empty — every story status would read as non-actionable"
    assert all(isinstance(s, str) for s in restated), (
        f"{CONSTANT} must contain only str, got "
        f"{sorted(type(s).__name__ for s in restated)}"
    )


def test_restated_matches_installed_harness_exactly() -> None:
    """SET EQUALITY against the installed harness — the whole point of AD-13."""
    restated = _restated_literal()
    harness = frozenset(HARNESS_ACTIONABLE)
    assert restated == harness, (
        "Doctor's restated ACTIONABLE_STATUSES has DRIFTED from the installed "
        "bmad_loop.sprintstatus.\n"
        f"  doctor/sources/deps.py : {sorted(restated)}\n"
        f"  bmad_loop (installed)  : {sorted(harness)}\n"
        f"  only in doctor         : {sorted(restated - harness)}\n"
        f"  only in harness        : {sorted(harness - restated)}\n"
        "This is the exact failure AD-13 accepted the restatement risk for. "
        "Doctor's forward-dependency verdict is now reasoning about a rule the "
        "engine no longer follows. Update deps.py's literal to match, and check "
        "whether the new status changes which stories count as dispatchable."
    )
