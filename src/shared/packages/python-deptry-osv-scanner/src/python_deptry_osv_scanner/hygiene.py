"""deptry-output parsing + the default hygiene→status table (Story 1.3, E2).

This module turns deptry's ``--json-output`` records (DEP001–DEP005) into
``hygiene:<DEP-code>:<subject>`` ``Finding``s and owns the default
hygiene→``Status`` mapping. It NEVER projects an exit code and NEVER spells
the verdict lattice order — it produces ``(Status, StatusDriver)`` rungs the
sole owner (``verdict.py``) later projects (the sole-ownership AST guard
scans this module).

Ownership decisions recorded:

* ``DEFAULT_HYGIENE_POLICY`` is a MODULE DEFAULT: DEP001 (a missing/undeclared
  import — high-confidence for a PyPI-native project) blocks
  (``policy-violation``); DEP002/003/004/005 warn. An UNKNOWN DEP code
  degrades to ``indeterminate`` (never a false-green — a new deptry code we
  have not classified must not silently pass). Story 3.1 lifts this default
  into an overridable config table; 1.3 keeps it here.
* **DEP005 = stdlib dependency** (verified against deptry 0.25.1, 2026-07-13:
  ``'argparse' is defined as a dependency but it is included in the Python
  standard library.``). The architecture's pinned "unused-dev" label was
  wrong; ``DEP005 → warn`` is still the correct ceiling.
* A malformed/unmappable record (not a dict, or missing ``error.code`` /
  ``module``, or one whose finding id would violate the frozen id grammar)
  is COUNTED toward ``unparseable_rate`` AND surfaces a typed
  ``ErrorRecord(engine-output-unrecognized)`` — never silently dropped (C0).
  A top-level output that is not a JSON array (undecodable, non-list) fails
  the whole parse with ``output_parsed=False`` + an
  ``engine-output-unparseable`` error.
* ``UNPARSEABLE_RATE_BASELINE = 0.0`` is a RATCHET (NFR-R2): a conformance
  test pins ``unparseable_rate <= UNPARSEABLE_RATE_BASELINE`` over the real
  deptry corpus; the baseline may only ever DECREASE.
* Findings are sorted by id before emit (determinism); ``Finding.subject``
  keeps the raw deptry module name, the id segment is sanitized via the
  shared ``interfaces._sanitize_id_segment`` (single-line, colon-delimited
  grammar).

This module parses JSON as DATA: no subprocess, no network, no exec.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .interfaces import _sanitize_id_segment
from .models import (
    AXIS_HYGIENE,
    ErrorKind,
    ErrorRecord,
    Finding,
    Status,
    StatusDriver,
)

# The owner label every deptry-sourced error/finding carries.
_OWNER = "deptry"

# The default hygiene policy: DEP-code → Status. DEP001 blocks; the rest warn.
# Keys are deptry DEP codes (NOT Status tokens), so the sole-ownership
# rung-ordering guard does not fire on this literal.
DEFAULT_HYGIENE_POLICY: dict[str, Status] = {
    "DEP001": Status.POLICY_VIOLATION,
    "DEP002": Status.WARN,
    "DEP003": Status.WARN,
    "DEP004": Status.WARN,
    "DEP005": Status.WARN,
}

# Ratchet baseline (NFR-R2): the fraction of deptry records we fail to map may
# only ever decrease. A conformance test pins the real corpus at/below this.
UNPARSEABLE_RATE_BASELINE = 0.0


@dataclass(frozen=True)
class DeptryParse:
    """The outcome of parsing one deptry ``--json-output`` document.

    ``output_parsed`` is False only when the top-level output is not a JSON
    array (undecodable text, or a non-list) — a whole-output failure whose
    ``errors`` carries the ``engine-output-unparseable`` record. When True,
    ``findings`` are the mapped hygiene findings (sorted by id) and ``errors``
    carries one ``engine-output-unrecognized`` record per malformed record
    (which is also counted in ``records_unparseable``)."""

    findings: tuple[Finding, ...]
    errors: tuple[ErrorRecord, ...]
    records_total: int
    records_unparseable: int
    output_parsed: bool

    @property
    def unparseable_rate(self) -> float:
        """Structurally-unmappable records ÷ total (0.0 when total is 0)."""
        if self.records_total == 0:
            return 0.0
        return self.records_unparseable / self.records_total


def status_for_code(code: str) -> Status:
    """The default status for a deptry DEP code — unknown codes degrade to
    ``indeterminate`` (never a false-green)."""
    return DEFAULT_HYGIENE_POLICY.get(code, Status.INDETERMINATE)


def hygiene_rung(finding: Finding) -> tuple[Status, StatusDriver]:
    """Derive the ``(Status, StatusDriver)`` rung for one hygiene finding.

    The DEP code is the id's middle segment (``hygiene:<code>:<subject>``);
    a hygiene-axis finding that is not hygiene-family (an ``indeterminate:``
    id carrying the hygiene axis) yields an unknown code → ``indeterminate``.
    The driver carries the finding's own axis and id."""
    code = finding.id.split(":", 2)[1] if finding.id.count(":") >= 2 else ""
    return (
        status_for_code(code),
        StatusDriver(axis=finding.axis, finding_id=finding.id),
    )


def parse_deptry_output(raw: str) -> DeptryParse:
    """Parse deptry's ``--json-output`` array into hygiene findings.

    A record must be a dict carrying a string ``error.code`` and a string
    ``module``; the finding id is ``hygiene:<code>:<sanitized-module>`` with
    the raw module as ``subject`` and deptry's message verbatim. Anything
    else is counted and reported (``engine-output-unrecognized``), never
    dropped. Undecodable/non-array top-level output fails the whole parse
    (``engine-output-unparseable``)."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return DeptryParse(
            findings=(),
            errors=(
                ErrorRecord(
                    kind=ErrorKind.ENGINE_OUTPUT_UNPARSEABLE,
                    owner=_OWNER,
                    message="deptry output is not valid JSON",
                ),
            ),
            records_total=0,
            records_unparseable=0,
            output_parsed=False,
        )
    if not isinstance(data, list):
        return DeptryParse(
            findings=(),
            errors=(
                ErrorRecord(
                    kind=ErrorKind.ENGINE_OUTPUT_UNPARSEABLE,
                    owner=_OWNER,
                    message=(
                        "deptry output is not a JSON array "
                        f"(got {type(data).__name__})"
                    ),
                ),
            ),
            records_total=0,
            records_unparseable=0,
            output_parsed=False,
        )
    findings: list[Finding] = []
    errors: list[ErrorRecord] = []
    records_unparseable = 0
    for index, record in enumerate(data):
        finding = _record_to_finding(record)
        if finding is None:
            records_unparseable += 1
            errors.append(
                ErrorRecord(
                    kind=ErrorKind.ENGINE_OUTPUT_UNRECOGNIZED,
                    owner=_OWNER,
                    message=(
                        f"deptry record {index} is unrecognized "
                        "(missing string 'error.code' or 'module')"
                    ),
                )
            )
            continue
        findings.append(finding)
    findings.sort(key=lambda f: f.id)
    return DeptryParse(
        findings=tuple(findings),
        errors=tuple(errors),
        records_total=len(data),
        records_unparseable=records_unparseable,
        output_parsed=True,
    )


def _record_to_finding(record: object) -> Finding | None:
    """Map one deptry record to a hygiene ``Finding``, or ``None`` if it is
    structurally unrecognized (counted + reported by the caller, never
    dropped)."""
    if not isinstance(record, dict):
        return None
    error = record.get("error")
    if not isinstance(error, dict):
        return None
    code = error.get("code")
    module = record.get("module")
    if not isinstance(code, str) or not code:
        return None
    if not isinstance(module, str) or not module:
        return None
    message = error.get("message")
    if not isinstance(message, str):
        message = f"{code} (deptry provided no message)"
    finding_id = f"hygiene:{code}:{_sanitize_id_segment(module)}"
    try:
        return Finding(
            id=finding_id,
            axis=AXIS_HYGIENE,
            message=message,
            subject=module,
            severity=None,
        )
    except ValueError:
        # A code carrying a colon/newline would violate the frozen id
        # grammar; treat it as unrecognized rather than crash the parse.
        return None
