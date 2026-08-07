"""Diagnose & Prescribe pipeline -- pure functions over already-gathered
``Finding``\\ s (Epic 3, FR-6/FR-7/FR-8, AD-4).

``AD-4``: ``doctor.prescribe`` adds ZERO subprocess/MCP calls of its own --
it consumes Epic 1's `checks` gather filter and Epic 2's `sources.atlas`
gather filter as already-shipped inputs (``list[Finding]`` in, structured
data out). The meta-test ``test_prescribe_pure_function.py`` enforces this
with an AST scan; this module's entire import surface is
``__future__``/``dataclasses``/``collections.abc``/``..models``.

Three stages, one dataclass each (Story 3.1/3.2/3.3), composed by the CLI
layer (Story 3.4) into full ``Prescription`` objects:

- :func:`partition` (Story 3.1, FR-6) -- classifies every given ``Finding``
  into ``Partition.ACTIONABLE``/``BLOCKED``/``ACCEPTED_RISK``, with a
  human-readable reason, never a silent drop.
- :func:`rank` (Story 3.2, FR-7) -- orders the ``ACTIONABLE`` partition by
  severity x exploitability x blast-radius, naming which signals fired.
- :func:`name_root_cause` (Story 3.3, FR-8) -- per-``Finding`` root-cause
  text, correlating CVE findings against a same-``check`` staleness signal
  when one is present in the same gather batch, else templating from the
  ``Finding``'s own ``evidence``/``message``.

None of the three heuristics below call out to any external classifier --
each reads only the ``Finding``\\ s it is given (AD-4's own "pure function"
requirement), driven by evidence keys existing Source producers already
populate, plus three forward-compatible hooks (``waived``/``waived_reason``,
``fix_available``/``block_reason``) that no current producer sets (so
``ACCEPTED_RISK``/``BLOCKED`` stay empty in live data today, per the Story
3.1 AC's own "none yet waived" framing) but are directly testable with
synthetic ``Finding`` fixtures and become live the moment a future producer
starts setting them.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from .models import DoctorStatus, Finding, Partition, Source

# --- Story 3.1: partition --------------------------------------------------


@dataclass(frozen=True)
class PartitionedFinding:
    """One ``Finding``, classified -- the intermediate shape between a raw
    gather batch and a full ``Prescription`` (Story 3.4 assembles the
    latter from this plus :func:`rank`/:func:`name_root_cause`)."""

    finding: Finding
    partition: Partition
    reason: str


def _partition_one(finding: Finding) -> PartitionedFinding:
    evidence = finding.evidence

    waived = evidence.get("waived")
    if waived:
        reason = str(evidence.get("waived_reason") or "accepted risk (waived)")
        return PartitionedFinding(finding, Partition.ACCEPTED_RISK, reason)

    if finding.status is DoctorStatus.OK:
        # A clean Finding has no problem to act on -- it is trivially
        # "actionable: nothing to do" rather than blocked or at-risk, which
        # both require an unresolved problem. Every Finding passed to
        # partition() lands in exactly one bucket (Story 3.1 AC1's "total
        # count == count of Findings" rule), so an OK Finding must land
        # somewhere too, not be silently dropped.
        return PartitionedFinding(finding, Partition.ACTIONABLE, "clean -- no remediation needed")

    fix_available = evidence.get("fix_available")
    if fix_available is False:
        reason = str(evidence.get("block_reason") or "no fix version published")
        return PartitionedFinding(finding, Partition.BLOCKED, reason)

    return PartitionedFinding(
        finding, Partition.ACTIONABLE, "actionable -- a remediation path exists"
    )


def partition(findings: Iterable[Finding]) -> tuple[PartitionedFinding, ...]:
    """Classify every given ``Finding`` into ``actionable``/``blocked``/
    ``accepted-risk`` (Story 3.1, FR-6). Pure -- reads only each
    ``Finding``'s own ``status``/``evidence``, makes zero external calls.

    Classification order (first match wins):

    1. ``evidence["waived"]`` truthy -> ``ACCEPTED_RISK`` (reason from
       ``evidence["waived_reason"]`` if present).
    2. ``status is DoctorStatus.OK`` -> ``ACTIONABLE`` ("clean" reason) --
       see the module docstring for why a healthy Finding still lands in a
       bucket rather than being excluded.
    3. ``evidence["fix_available"] is False`` -> ``BLOCKED`` (reason from
       ``evidence["block_reason"]`` if present, else "no fix version
       published").
    4. Otherwise -> ``ACTIONABLE``.

    Every Finding passed in appears in exactly one returned
    ``PartitionedFinding`` -- never dropped, never duplicated. The returned
    tuple preserves input order."""
    return tuple(_partition_one(finding) for finding in findings)
