"""Canonical enums + the one response envelope (Story 1.1, architecture
spine AD-14/AD-39).

``Verdict`` is Marshal's closed 6-member lattice (AD-7/AD-31, ordering
strongest first: ``error > gate-failed > scope-violation > unevaluable >
warn > clean``) -- ``core/verdict.py`` owns the lattice ORDER and the
exit-code projection; this module only defines the vocabulary.

``Status`` is the envelope's coarse ok/error partition -- a pure 2-way
function of ``Verdict`` (``status_for``): ``{clean, warn} -> ok``, every
other verdict -> ``error``. It lives HERE, not in ``core/verdict.py``,
because it needs nothing but the ``Verdict`` enum itself; routing it
through ``verdict.py`` would create the one import cycle this package must
avoid (``core/verdict.py`` already imports ``Verdict``/``Finding`` from
here). ``core/verdict.py`` owns the lattice ORDERING and the *exit-code*
projection -- a genuinely distinct concern from this *status* projection.

``Severity`` is per-``Finding`` presentation only (``error``/``warn``/
``info``) -- the lattice member a finding classifies to comes from
``verdict.classify(code)`` (AD-31), never from ``Severity`` directly.

``Envelope`` is the one response shape every ``marshal`` command emits
(Consistency Conventions' ``Envelope`` row): ``{schema_version, command,
status, verdict, data, data_version, findings[], assumptions[]}``.
``Envelope.__post_init__`` is a hard type-level check, not a convention: it
raises ``ValueError`` if ``status`` doesn't equal ``status_for(verdict)``,
or if ``status`` is ``ok`` while any finding carries ``severity == error``
(AD-39's own named failure example). ``build_envelope`` is the convenience
constructor that derives ``status`` for the caller so the two can never be
set independently by accident.

This module is pure data: no I/O, no subprocess, no network, no clock
(AD-4).
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from enum import StrEnum

from .findings import require_registered

SCHEMA_VERSION = 1


class Verdict(StrEnum):
    """Marshal's closed lattice member vocabulary (AD-7, AD-31). The ORDER
    is owned exclusively by ``core/verdict.py``'s ``LATTICE_ORDER`` -- this
    enum only enumerates the 6 members, unordered."""

    CLEAN = "clean"
    WARN = "warn"
    UNEVALUABLE = "unevaluable"
    SCOPE_VIOLATION = "scope-violation"
    GATE_FAILED = "gate-failed"
    ERROR = "error"


class Status(StrEnum):
    """The envelope's coarse ok/error partition (AD-39)."""

    OK = "ok"
    ERROR = "error"


class Severity(StrEnum):
    """Per-``Finding`` presentation severity (Consistency Conventions'
    ``Findings`` row) -- presentational only; the lattice member a finding
    classifies to comes from ``verdict.classify(code)``, never from this
    enum."""

    ERROR = "error"
    WARN = "warn"
    INFO = "info"


_OK_VERDICTS = frozenset({Verdict.CLEAN, Verdict.WARN})


def status_for(verdict: Verdict | str) -> Status:
    """The pure 2-way partition: ``{clean, warn} -> ok``, every other
    verdict -> ``error`` (AD-39). Coerces a raw string first."""
    return Status.OK if Verdict(verdict) in _OK_VERDICTS else Status.ERROR


@dataclass(frozen=True)
class Finding:
    """One coded finding (AD-15): ``{code, severity, message, path?}``.

    ``code`` must be registered in ``core.findings.REGISTERED_CODES`` --
    enforced at construction via ``require_registered`` (raises
    ``UnregisteredFindingCodeError``, a ``ValueError`` subclass).
    """

    code: str
    severity: Severity
    message: str
    path: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", require_registered(self.code))
        object.__setattr__(self, "severity", Severity(self.severity))
        if not isinstance(self.message, str):
            raise ValueError(f"message must be a str, got {self.message!r}")
        if self.path is not None and not isinstance(self.path, str):
            raise ValueError(f"path must be a str or None, got {self.path!r}")

    def to_json_dict(self) -> dict[str, object]:
        document: dict[str, object] = {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
        }
        if self.path is not None:
            document["path"] = self.path
        return document


@dataclass(frozen=True)
class Envelope:
    """The one response envelope every ``marshal`` command emits (AD-14).

    ``__post_init__`` enforces AD-39's two named invariants: ``status`` must
    equal ``status_for(verdict)``, and an ``ok`` envelope may carry no
    error-severity finding. It also validates every payload field's shape
    (``schema_version``/``command``/``data``/``data_version`` plus the
    ``findings``/``assumptions`` member types) AND that ``data`` is
    deep-copyable and JSON-serializable, so a successfully constructed
    envelope always serializes to schema-valid JSON -- ``to_json_dict``
    cannot fail on an envelope that constructed.
    """

    schema_version: int
    command: str
    status: Status
    verdict: Verdict
    data: dict
    data_version: int
    findings: tuple[Finding, ...] = ()
    assumptions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        # bool excluded (True == 1) AND a real int required (1.0 == 1 too --
        # a float schema_version would otherwise construct and emit
        # "schema_version": 1.0 on the wire).
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != SCHEMA_VERSION
        ):
            raise ValueError(
                f"schema_version must be {SCHEMA_VERSION}, got "
                f"{self.schema_version!r}"
            )
        if not isinstance(self.command, str) or not self.command:
            raise ValueError(
                f"command must be a non-empty str, got {self.command!r}"
            )
        if (
            isinstance(self.data_version, bool)
            or not isinstance(self.data_version, int)
            or self.data_version < 1
        ):
            raise ValueError(
                f"data_version must be an int >= 1, got {self.data_version!r}"
            )
        if not isinstance(self.data, dict):
            raise ValueError(f"data must be a dict, got {self.data!r}")
        object.__setattr__(self, "verdict", Verdict(self.verdict))
        object.__setattr__(self, "status", Status(self.status))
        # A bare str is iterable, so tuple("assumed x") would silently become
        # nine one-char "assumptions" that each pass the str member check
        # below -- reject it before the coercion.
        if isinstance(self.assumptions, str):
            raise ValueError(
                "assumptions must be a sequence of str, not a bare str -- "
                f"got {self.assumptions!r}"
            )
        object.__setattr__(self, "findings", tuple(self.findings))
        object.__setattr__(self, "assumptions", tuple(self.assumptions))
        # Member-type checks BEFORE any invariant that touches the elements:
        # without them, a non-Finding element crashed with AttributeError at
        # construction on the ok path but survived to to_json_dict() on the
        # error path -- validation strictness must not depend on the verdict.
        for finding in self.findings:
            if not isinstance(finding, Finding):
                raise ValueError(
                    f"findings must contain only Finding instances, got {finding!r}"
                )
        for assumption in self.assumptions:
            if not isinstance(assumption, str):
                raise ValueError(
                    f"assumptions must contain only str, got {assumption!r}"
                )
        # Deep copy -- frozen=True only blocks attribute reassignment, not
        # mutation of a referenced mutable value (same rationale as
        # pyforge-doctor's Finding.evidence, extended to nested structures
        # since a shallow dict() copy still shares any nested list/dict with
        # the caller). Both failure modes surface as this module's ValueError
        # convention, not a raw TypeError from deep inside copy/json.
        try:
            copied_data = copy.deepcopy(self.data)
        except TypeError as exc:
            raise ValueError(f"data is not deep-copyable: {exc}") from exc
        # The docstring's contract -- to_json_dict() cannot fail on an
        # envelope that constructed -- requires the payload's CONTENTS to be
        # JSON-serializable, not just data's own dict shape.
        try:
            json.dumps(copied_data)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"data is not JSON-serializable: {exc}") from exc
        object.__setattr__(self, "data", copied_data)

        expected_status = status_for(self.verdict)
        if self.status is not expected_status:
            raise ValueError(
                f"status {self.status.value!r} does not match "
                f"status_for({self.verdict.value!r}) = {expected_status.value!r}"
            )
        if self.status is Status.OK and any(
            finding.severity is Severity.ERROR for finding in self.findings
        ):
            raise ValueError(
                "status 'ok' but at least one finding has severity 'error' "
                "-- an 'ok' envelope may carry no error-severity finding"
            )

    def to_json_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "command": self.command,
            "status": self.status.value,
            "verdict": self.verdict.value,
            # Deep-copied: self.data is already a defensive deep copy of the
            # caller's input, but returning it directly would still let a
            # caller of to_json_dict() mutate THIS envelope's stored value
            # through the returned dict.
            "data": copy.deepcopy(self.data),
            "data_version": self.data_version,
            "findings": [finding.to_json_dict() for finding in self.findings],
            "assumptions": list(self.assumptions),
        }


def build_envelope(
    *,
    command: str,
    verdict: Verdict | str,
    data: dict | None = None,
    data_version: int = 1,
    findings: tuple[Finding, ...] = (),
    assumptions: tuple[str, ...] = (),
) -> Envelope:
    """Convenience constructor: derives ``status`` from ``verdict`` via
    ``status_for`` so a caller can never set the two independently, and pins
    ``schema_version`` -- ``SCHEMA_VERSION`` is its only legal value, so a
    parameter for it would just invite the one mistake it cannot survive."""
    resolved_verdict = Verdict(verdict)
    return Envelope(
        schema_version=SCHEMA_VERSION,
        command=command,
        status=status_for(resolved_verdict),
        verdict=resolved_verdict,
        data=data if data is not None else {},
        data_version=data_version,
        findings=findings,
        assumptions=assumptions,
    )
