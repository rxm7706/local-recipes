"""Composite health-grade synthesis over already-gathered ``Finding``\\ s
(Epic 4, Story 4.1, FR-10, architecture spine AD-7).

``AD-7``: ``doctor.score`` adds ZERO subprocess/MCP calls of its own -- it
consumes the same ``list[Finding]`` shape ``doctor.prescribe`` (AD-4)
already consumes, as an already-shipped input from Epic 1's ``checks``
gather filter and Epic 2's ``sources.atlas`` gather filter. The meta-test
``test_score_pure_function.py`` enforces this with an AST scan, mirroring
``test_prescribe_pure_function.py``'s own AD-4 guard exactly (this module's
entire import surface is ``__future__``/``dataclasses``/``enum``/
``collections.abc``/``..models``).

:func:`grade` groups the given Findings by their own ``Source`` tag (one
"axis" per Source present in the input -- deliberately NOT a hardcoded
staleness/cve/abandonment/adoption axis list, so a future ``Source`` member
such as Story 4.3's ``ADOPTION`` is graded automatically, with zero changes
needed here) and computes a per-axis letter grade from that axis's own
ok/warn/fail counts. The composite grade is the WORST axis grade (a simple,
deterministic, conservative aggregation -- a fleet is only as healthy as its
worst-scoring axis, never averaged into a falsely-reassuring middle grade).

Deterministic (FR-10's own testable consequence): no wall-clock read, no
randomness, anywhere in this module -- the same ``list[Finding]`` passed
twice always produces a byte-identical :class:`GradeResult`.

Incomplete-gather handling (FR-10's other testable consequence): an axis
whose OWN gather degraded to a sentinel Finding (``sources/atlas.py``'s
``_one_fail_finding`` default shape -- ``check == "doctor.sources.atlas"``,
``evidence == {}``) never gets graded as if it were real data. That axis
grades ``incomplete``, and an incomplete axis poisons the WHOLE composite to
``incomplete`` too -- a computed letter grade must never stand in for
missing data (this module never silently drops the incomplete axis from the
composite the way it might be tempting to "just grade what we have").
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from .models import DoctorStatus, Finding, Source

# Duplicated literal from ``sources/atlas.py``'s ``_one_fail_finding``'s own
# default ``check`` parameter -- AD-7 forbids ``doctor.score`` from importing
# ``sources.atlas`` (that would pull a subprocess/MCP-capable module into a
# pure-function guard's own import surface), so this is a deliberate
# duplicated literal, not a shared import, mirroring ``prescribe.py``'s own
# ``_UNKNOWN_FEEDSTOCK_CHECK`` precedent for the identical reason. It is the
# one marker that distinguishes "this axis's OWN gather failed" from an
# ordinary FAIL Finding about a real package problem.
_GATHER_FAILURE_CHECK = "doctor.sources.atlas"


class Grade(StrEnum):
    """Closed taxonomy (mirrors ``DoctorStatus``/``Source``'s own AD-3
    closed-enum discipline): a real letter grade, or ``incomplete`` -- never
    an open/stringly-typed escape hatch."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"
    INCOMPLETE = "incomplete"


# Worst-to-best ordering used to pick the composite grade (the max-severity
# axis wins) -- INCOMPLETE outranks every real letter grade, so a single
# incomplete axis always poisons the composite regardless of how healthy
# every other axis looks.
_GRADE_SEVERITY: dict[Grade, int] = {
    Grade.A: 0,
    Grade.B: 1,
    Grade.C: 2,
    Grade.D: 3,
    Grade.F: 4,
    Grade.INCOMPLETE: 5,
}


@dataclass(frozen=True)
class AxisScore:
    """One ``Source``'s own grade + the raw counts it was computed from --
    ``axis`` is the ``Source``'s string value (e.g. ``"cve-watcher"``), never
    a bare letter with no explanation (mirrors ``prescribe.RankedPrescription``'s
    own "never a bare integer" discipline, Story 3.2 AC4)."""

    axis: str
    ok: int
    warn: int
    fail: int
    grade: Grade

    def to_json_dict(self) -> dict[str, object]:
        return {
            "axis": self.axis,
            "ok": self.ok,
            "warn": self.warn,
            "fail": self.fail,
            "grade": self.grade.value,
        }


@dataclass(frozen=True)
class GradeResult:
    """The composite grade plus every constituent axis score (FR-10 AC4:
    "the grade and its constituent axis scores both appear") and a
    human-readable ``reason`` naming why (mirrors ``PartitionedFinding``'s
    own "never a silent classification" discipline)."""

    grade: Grade
    axis_scores: tuple[AxisScore, ...]
    reason: str

    def to_json_dict(self) -> dict[str, object]:
        return {
            "grade": self.grade.value,
            "axis_scores": [axis.to_json_dict() for axis in self.axis_scores],
            "reason": self.reason,
        }


def _is_gather_failure(finding: Finding) -> bool:
    return finding.check == _GATHER_FAILURE_CHECK and not finding.evidence


def _axis_grade(ok: int, warn: int, fail: int) -> Grade:
    """A real (non-incomplete) axis's letter grade from its own ok/warn/fail
    counts -- deliberately simple thresholds (Simplicity First: this is a
    v1.x synthesis layer, not a tuned scoring model with no real-world
    calibration data behind it yet)."""
    total = ok + warn + fail
    if total == 0:
        # Unreachable via `grade()` itself (an axis only exists in the
        # grouping when it has at least one Finding), kept as a defensive
        # floor for any future direct caller of this helper.
        return Grade.A
    if fail:
        return Grade.F if (fail / total) >= 0.5 else Grade.D
    if warn:
        return Grade.C if (warn / total) > 0.5 else Grade.B
    return Grade.A


def grade(findings: Sequence[Finding]) -> GradeResult:
    """Compute a composite health grade over an already-gathered
    ``Finding`` collection (FR-10). Pure -- reads only each Finding's own
    ``source``/``status``/``check``/``evidence``; makes zero subprocess/MCP
    calls; no wall-clock read anywhere in this function (deterministic:
    the same input always produces the same :class:`GradeResult`).

    Grouping: one axis per distinct ``Finding.source`` present in
    ``findings`` (sorted by the Source's own string value, for a
    deterministic ``axis_scores`` ordering independent of gather order).

    An axis is ``incomplete`` when ANY of its Findings is a gather-failure
    sentinel (see module docstring) -- and ANY incomplete axis poisons the
    WHOLE composite to ``incomplete`` (never a computed letter grade
    standing in for missing data, FR-10's own testable consequence).
    Otherwise the composite is the WORST (highest-severity) axis grade.

    An empty ``findings`` sequence (nothing gathered at all) also grades
    ``incomplete`` -- there is no data to synthesize a grade from, and a
    default ``A`` would misrepresent "nothing was checked" as "everything
    passed"."""
    if not findings:
        return GradeResult(
            grade=Grade.INCOMPLETE,
            axis_scores=(),
            reason="no findings gathered -- nothing to grade",
        )

    by_source: dict[Source, list[Finding]] = {}
    for finding in findings:
        by_source.setdefault(finding.source, []).append(finding)

    axis_scores: list[AxisScore] = []
    incomplete_axes: list[str] = []
    for source in sorted(by_source, key=lambda s: s.value):
        group = by_source[source]
        if any(_is_gather_failure(f) for f in group):
            incomplete_axes.append(source.value)
            axis_scores.append(
                AxisScore(axis=source.value, ok=0, warn=0, fail=0, grade=Grade.INCOMPLETE)
            )
            continue
        ok = sum(1 for f in group if f.status is DoctorStatus.OK)
        warn = sum(1 for f in group if f.status is DoctorStatus.WARN)
        fail = sum(1 for f in group if f.status is DoctorStatus.FAIL)
        axis_scores.append(
            AxisScore(
                axis=source.value, ok=ok, warn=warn, fail=fail,
                grade=_axis_grade(ok, warn, fail),
            )
        )

    if incomplete_axes:
        return GradeResult(
            grade=Grade.INCOMPLETE,
            axis_scores=tuple(axis_scores),
            reason=(
                "gather did not complete for axis(es): "
                f"{', '.join(sorted(incomplete_axes))}"
            ),
        )

    worst = max(axis_scores, key=lambda axis: _GRADE_SEVERITY[axis.grade])
    return GradeResult(
        grade=worst.grade,
        axis_scores=tuple(axis_scores),
        reason=(
            f"composite = worst of {len(axis_scores)} axis grade(s); "
            f"{worst.axis} scored {worst.grade.value}"
        ),
    )
