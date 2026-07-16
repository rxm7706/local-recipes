"""deptry-output parsing + the default hygiene→status table (Story 1.3, E2).

This module turns deptry's ``--json-output`` records (DEP001–DEP005) into
``hygiene:<DEP-code>:<subject>`` ``Finding``s and owns the default
hygiene→``Status`` mapping. It NEVER projects an exit code and NEVER spells
the verdict lattice order — it produces ``(Status, StatusDriver)`` rungs the
sole owner (``verdict.py``) later projects (the sole-ownership AST guard
scans this module).

Ownership decisions recorded:

* ``DEFAULT_HYGIENE_POLICY`` is a MODULE DEFAULT: DEP001 is
  ``policy-violation`` (Story 2.1), DEP002–005 stay ``warn``. Architecture
  Gap-A required DEP001 blocking to be GATED on conda↔PyPI name-mapping
  confidence ("a mapping miss must not become a false-red disable-driver");
  that gate is ``dep001_trusted`` (computed once per scan in
  ``DefaultPolicy.evaluate()`` from ``inventory.components`` and threaded
  through ``hygiene_rung`` — see its docstring). deptry's ``module`` field is
  an import name, not a distribution name, so it can't be reliably
  correlated to one component without Story 2.2's synthesized front-door
  (not yet built); the trust gate is therefore scan-wide, not per-finding —
  false only when the inventory shows a positive ambiguous-mapping signal
  (a ``"likely"``-confidence conda component) anywhere. An UNKNOWN DEP code
  degrades to ``indeterminate`` (never a false-green — a new deptry code we
  have not classified must not silently pass). Story 3.1 lifts this default
  into an overridable config table; 1.3/2.1 keep it here.
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

# The default hygiene policy: DEP-code → Status. DEP001 blocks by default
# (Story 2.1, Gap-A); hygiene_rung downgrades it to warn on a per-scan
# untrusted-mapping signal (dep001_trusted=False — see module docstring).
# DEP002-005 stay warn (deptry false-positive-prone, unrelated to mapping
# confidence). Keys are deptry DEP codes (NOT Status tokens), so the
# sole-ownership rung-ordering guard does not fire on this literal.
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


def hygiene_rung(
    finding: Finding, *, dep001_trusted: bool = True
) -> tuple[Status, StatusDriver]:
    """Derive the ``(Status, StatusDriver)`` rung for one hygiene finding.

    The DEP code is the id's middle segment (``hygiene:<code>:<subject>``);
    a hygiene-axis finding that is not hygiene-family (an ``indeterminate:``
    id carrying the hygiene axis) yields an unknown code → ``indeterminate``.
    The driver carries the finding's own axis and id.

    ``dep001_trusted`` (Story 2.1, Gap-A) gates DEP001's block: when False
    (the scan's inventory carries a ``"likely"``-confidence conda component
    — an ambiguous mapping somewhere), a DEP001 finding downgrades to
    ``warn`` regardless of the default policy, rather than risk a false-red
    off an untrustworthy mapping. Every other code is unaffected.

    The default is ``True`` (trusted): C0's standing bias is toward MORE
    scrutiny, not less (an unknown DEP code degrades to ``indeterminate``,
    never a silent pass), so an un-wired caller failing to the block, not
    the warn, matches every other default in this module. The sole
    production caller (``DefaultPolicy.evaluate()``) always computes and
    passes the real per-scan value explicitly."""
    code = finding.id.split(":", 2)[1] if finding.id.count(":") >= 2 else ""
    status = status_for_code(code)
    if code == "DEP001" and not dep001_trusted:
        status = Status.WARN
    return (
        status,
        StatusDriver(axis=finding.axis, finding_id=finding.id),
    )


def parse_deptry_output(raw: str) -> DeptryParse:
    """Parse deptry's ``--json-output`` array into hygiene findings.

    A record must be a dict carrying a string ``error.code`` and a string
    ``module``; the finding id is ``hygiene:<code>:<sanitized-module>`` with
    the raw module as ``subject`` and deptry's message verbatim. Anything
    else is counted and reported (``engine-output-unrecognized``), never
    dropped. Undecodable/non-array top-level output fails the whole parse
    (``engine-output-unparseable``). An EMPTY output (deptry wrote nothing to
    its ``-o`` file — a version/flag skew, not garbage) is reported distinctly,
    not as 'invalid JSON'."""
    if not raw.strip():
        return DeptryParse(
            findings=(),
            errors=(
                ErrorRecord(
                    kind=ErrorKind.ENGINE_OUTPUT_UNPARSEABLE,
                    owner=_OWNER,
                    message=(
                        "deptry produced no machine output (empty -o file) — "
                        "check the installed deptry version supports -o/--no-ansi"
                    ),
                ),
            ),
            records_total=0,
            records_unparseable=0,
            output_parsed=False,
        )
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
    for record in data:
        finding = _record_to_finding(record)
        if finding is None:
            records_unparseable += 1
            errors.append(
                ErrorRecord(
                    kind=ErrorKind.ENGINE_OUTPUT_UNRECOGNIZED,
                    owner=_OWNER,
                    # No array index in the message: deptry's record ordering
                    # is not stable across runs, so an index would break the
                    # NFR-I3 twice-run byte-identical contract. The count is
                    # carried in records_unparseable / unparseable_rate.
                    message=(
                        "a deptry record is unrecognized "
                        "(missing string 'error.code' or 'module', or a "
                        "grammar-breaking code)"
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
    # The code is the id's own delimited segment, so it must be grammar-safe
    # on its own — a colon/newline/percent would make `hygiene:<code>:<module>`
    # non-injective (`hygiene_rung` reads the code back via split(":",2)[1] and
    # would recover the wrong token). Sanitizing the code SILENTLY would mint a
    # mangled-but-valid finding; instead a code that is not already grammar-safe
    # is UNRECOGNIZED (counted + reported by the caller). A well-formed but
    # unknown code (a future DEP006) is grammar-safe, so it still becomes a
    # finding and degrades to `indeterminate` via status_for_code — graceful.
    if _sanitize_id_segment(code) != code:
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
        # Belt-and-suspenders: with code grammar-checked and module sanitized
        # the id is always valid, but never let a Finding-invariant raise crash
        # the parse — treat as unrecognized.
        return None
