"""Deck visual-QA gate report interface (Story 14.1).

Herald's deck pipeline needs a shared, extensible way for visual-QA gates
-- a future headless-render gate (Story 14.2), an image-slot scan (Story
14.3), and three parked ``.pptx``-contingent gates -- to report findings
against one deck slug. This module defines that report's JSON-round-
trippable schema and the ``run()`` entrypoint that executes a caller-
supplied gate mapping, without deciding what any individual gate checks.

``DEFAULT_GATES`` ships empty in this story on purpose: 14.2/14.3 each add
one entry here (a ``GateFn`` registered under a gate id) with zero change
to this module's public shape, to ``run()``'s signature, or to ``cli.py``
-- the whole point of the interface existing ahead of any real gate.

**A gate failure is isolated, never fatal to the report.** A gate raising
an exception is a realistic first failure mode (a missing browser binary,
a malformed deck source, a bug in the gate itself) and must not deny an
operator every OTHER gate's results just because one gate broke -- so
``run()`` catches per-gate, recording ``GateResult(status="error", ...)``
for that id alone. ``run()`` itself never raises because of a gate's own
failure.

**``GateResult`` never repeats its own gate id.** The id lives only as the
dict key in ``DeckQaReport.gates`` -- a ``gate_id`` field on ``GateResult``
too would let a hand-edited or buggy report disagree with itself (the key
says one id, the field says another) with no way to say which is right.
Mirrors ``state.py``'s AD-6 discipline: ``to_dict``/``parse_report`` round-
trip the schema exactly, and ``parse_report`` rejects any missing/
unrecognized field or bad ``status`` value by raising ``errors.HeraldError``
rather than silently dropping or coercing it.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import errors


@dataclass(frozen=True)
class Finding:
    """One gate's flagged problem on one slide."""

    slide_id: str
    message: str


@dataclass(frozen=True)
class GateResult:
    """One gate's outcome: ``status`` is ``"ok"`` or ``"error"``.

    ``error`` carries the caught exception's message when ``status`` is
    ``"error"`` (``run()`` sets it; a gate function itself never needs to
    populate it directly) and stays ``None`` for ``"ok"``. ``artifacts`` is
    a list of paths/identifiers a gate produced (e.g. a rendered PNG) --
    this story defines the slot but writes nothing to disk itself; where
    such artifacts live is Story 14.2's decision."""

    status: str
    findings: list[Finding] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass(frozen=True)
class DeckQaReport:
    """The whole QA report for one deck slug: every gate's result, keyed by
    gate id (the key is the sole owner of the id -- see module docstring)."""

    slug: str
    gates: dict[str, GateResult]


@dataclass(frozen=True)
class GateContext:
    """What every gate function receives: the deck slug and the repo root
    to resolve deck sources against. 14.2/14.3 may extend this dataclass
    (they edit this same file) as real gates need more inputs."""

    slug: str
    repo_root: Path


GateFn = Callable[[GateContext], GateResult]
"""One gate: a function from a ``GateContext`` to its own ``GateResult``."""


DEFAULT_GATES: dict[str, GateFn] = {}
"""Ships empty in this story -- see module docstring. A plain module-level
dict, not a decorator-based registry: every gate lives in this one file per
the epic's Surface lines, so there is no cross-module registration to
build."""


def run(
    slug: str, repo_root: Path, gates: Mapping[str, GateFn] | None = None
) -> DeckQaReport:
    """Run every gate in ``gates`` against ``slug``/``repo_root`` and
    assemble the report. Pure computation over the supplied mapping: never
    writes to disk, never mutates deck sources, never triggers a rebuild.

    ``gates`` defaults to ``None`` and is resolved to ``DEFAULT_GATES``
    *inside* the call, not via a mutable default-argument value -- a
    default bound at def time would keep pointing at today's empty dict
    forever if a later story reassigns ``DEFAULT_GATES = {...}`` rather
    than mutating it in place. Reading the module attribute fresh on every
    call makes both update styles safe. A caller -- including a test
    proving the "add a third gate" extensibility claim -- can still supply
    its own mapping without touching shared state.

    A gate misbehaving is caught for that gate alone and recorded as
    ``GateResult(status="error", error=...)`` -- the remaining gates still
    run, and this function itself never raises because of one gate's own
    failure (module docstring). "Misbehaving" covers both a raised
    exception AND a gate returning something other than a well-formed
    ``GateResult`` (wrong type, an unrecognized ``status``, or a
    ``status``/``error`` pairing that violates the ``"error"`` <=>
    non-``None`` invariant ``parse_report`` also enforces) -- a gate that
    forgets its ``return`` or hands back a bespoke object is exactly as
    contained as one that raises, never silently corrupting the report."""
    if gates is None:
        gates = DEFAULT_GATES
    context = GateContext(slug=slug, repo_root=repo_root)
    results: dict[str, GateResult] = {}
    for gate_id, gate_fn in gates.items():
        try:
            result = gate_fn(context)
            if (
                not isinstance(result, GateResult)
                or result.status not in _GATE_STATUSES
                or (result.status == "error") != (result.error is not None)
            ):
                raise TypeError(
                    f"gate {gate_id!r} returned {result!r}, expected a "
                    f"GateResult with status in {sorted(_GATE_STATUSES)} and "
                    f"'error' set if and only if status is 'error'"
                )
            results[gate_id] = result
        except Exception as exc:  # noqa: BLE001 -- isolates one gate's failure
            results[gate_id] = GateResult(status="error", error=str(exc))
    return DeckQaReport(slug=slug, gates=results)


def to_dict(report: DeckQaReport) -> dict[str, Any]:
    """``report`` as a JSON-serializable dict -- the exact shape
    ``parse_report`` inverts. Delegates to ``dataclasses.asdict`` (mirrors
    ``state.py``'s own idiom): every field here is itself a dataclass,
    primitive, or a plain ``list``/``dict`` of those, so the recursive
    default handles the whole tree with no manual field-by-field walk."""
    return asdict(report)


_REPORT_FIELDS = frozenset(("slug", "gates"))
_GATE_RESULT_FIELDS = frozenset(("status", "findings", "artifacts", "error"))
_FINDING_FIELDS = frozenset(("slide_id", "message"))
_GATE_STATUSES = frozenset(("ok", "error"))


def _finding_from_dict(gate_id: str, index: int, entry: object) -> Finding:
    malformed = f"gate {gate_id!r} finding #{index} is malformed"
    if not isinstance(entry, dict):
        raise errors.HeraldError(f"{malformed}: entry is not a JSON object")
    unknown = sorted(set(entry) - _FINDING_FIELDS)
    if unknown:
        raise errors.HeraldError(
            f"{malformed}: unknown field(s) {', '.join(map(repr, unknown))}"
        )
    missing = sorted(_FINDING_FIELDS - set(entry))
    if missing:
        raise errors.HeraldError(
            f"{malformed}: missing field(s) {', '.join(map(repr, missing))}"
        )
    slide_id = entry["slide_id"]
    message = entry["message"]
    if not isinstance(slide_id, str) or not isinstance(message, str):
        raise errors.HeraldError(
            f"{malformed}: 'slide_id' and 'message' must both be strings"
        )
    return Finding(slide_id=slide_id, message=message)


def _gate_result_from_dict(gate_id: str, entry: object) -> GateResult:
    malformed = f"gate {gate_id!r} entry is malformed"
    if not isinstance(entry, dict):
        raise errors.HeraldError(f"{malformed}: entry is not a JSON object")
    unknown = sorted(set(entry) - _GATE_RESULT_FIELDS)
    if unknown:
        raise errors.HeraldError(
            f"{malformed}: unknown field(s) {', '.join(map(repr, unknown))}"
        )
    missing = sorted(_GATE_RESULT_FIELDS - set(entry))
    if missing:
        raise errors.HeraldError(
            f"{malformed}: missing field(s) {', '.join(map(repr, missing))}"
        )
    status = entry["status"]
    if status not in _GATE_STATUSES:
        raise errors.HeraldError(
            f"{malformed}: 'status' must be one of {sorted(_GATE_STATUSES)}, "
            f"got {status!r}"
        )
    findings = entry["findings"]
    if not isinstance(findings, list):
        raise errors.HeraldError(f"{malformed}: 'findings' must be a list")
    artifacts = entry["artifacts"]
    if not isinstance(artifacts, list) or not all(
        isinstance(a, str) for a in artifacts
    ):
        raise errors.HeraldError(
            f"{malformed}: 'artifacts' must be a list of strings"
        )
    error = entry["error"]
    if error is not None and not isinstance(error, str):
        raise errors.HeraldError(f"{malformed}: 'error' must be a string or null")
    if (status == "error") != (error is not None):
        raise errors.HeraldError(
            f"{malformed}: 'status'=={status!r} requires 'error' to be "
            f"{'non-null' if status == 'error' else 'null'}, got {error!r}"
        )
    return GateResult(
        status=status,
        findings=[
            _finding_from_dict(gate_id, i, item) for i, item in enumerate(findings)
        ],
        artifacts=list(artifacts),
        error=error,
    )


def parse_report(data: object) -> DeckQaReport:
    """The strict inverse of ``to_dict`` (AD-6, mirroring ``state.py``):
    raises ``errors.HeraldError`` naming the problem on any missing or
    unrecognized top-level/gate-level/finding-level field, a wrong field
    type, or a ``status`` value other than ``"ok"``/``"error"`` -- a typoed
    field or a corrupt hand-edit is never silently dropped or coerced."""
    if not isinstance(data, dict):
        raise errors.HeraldError(
            "deck QA report is malformed: top level is not a JSON object"
        )
    unknown = sorted(set(data) - _REPORT_FIELDS)
    if unknown:
        raise errors.HeraldError(
            f"deck QA report is malformed: unknown field(s) "
            f"{', '.join(map(repr, unknown))}"
        )
    missing = sorted(_REPORT_FIELDS - set(data))
    if missing:
        raise errors.HeraldError(
            f"deck QA report is malformed: missing field(s) "
            f"{', '.join(map(repr, missing))}"
        )
    slug = data["slug"]
    if not isinstance(slug, str):
        raise errors.HeraldError(
            "deck QA report is malformed: 'slug' must be a string"
        )
    gates = data["gates"]
    if not isinstance(gates, dict) or not all(isinstance(k, str) for k in gates):
        raise errors.HeraldError(
            "deck QA report is malformed: 'gates' must be an object with "
            "string keys"
        )
    return DeckQaReport(
        slug=slug,
        gates={
            gate_id: _gate_result_from_dict(gate_id, entry)
            for gate_id, entry in gates.items()
        },
    )
