"""The strategy layer — five Protocols + ``EngineResult`` + ``DefaultPolicy``
(Story 1.2).

Ownership decisions recorded here:

* Interface mechanics are ``typing.Protocol`` (structural typing — no ABC
  inheritance tax). Implementations live in their stage modules
  (``engines.py`` owns the engine registry, ``extract/`` the extractors,
  ``routing.py`` the router) and *conform* to these shapes; Stories
  1.3/1.5/2.x implement the seams, never redesign them. ``DefaultPolicy``
  is the RECORDED EXCEPTION to that layering rule: the fail-closed
  inventory→verdict bridge lives WITH the seam it closes (no policy stage
  module exists until Story 3.1's config/policy tables).
* Engine findings PASS THROUGH without feeding rungs in 1.2 — mapping
  engine findings to policy rungs (severity thresholds, axis policy) is
  Story 1.3/1.6 scope by plan. The null engine emits no findings, so no
  1.2 code path reaches a verdict through this gap; 1.3 MUST close it
  when the first findings-producing engine registers.
* ``DefaultPolicy`` is the fail-closed inventory→verdict bridge: a withheld
  component (``indeterminate_reason`` set) becomes an
  ``indeterminate:<reason>:<pkg>`` finding plus a driver-carrying
  ``indeterminate`` rung — precisely the C0 property the sentinel fixture
  polices. Assessable components feed ``match_level_rung`` rungs.
* Withheld-component findings carry ``AXIS_VULNERABILITY`` (they record
  exclusion from vulnerability matching per Gap-C); the ``indeterminate:``
  id family is axis-free in the frozen model, so this is a 1.2 convention
  for Story 2.4's real producer to follow or supersede.
* Every non-clean rung this policy feeds carries a driver: an assessable
  component whose ``match_level_rung`` lands non-clean also derives an
  ``indeterminate:<match-level>:<pkg>`` finding so the rung can say why —
  a driverless non-clean winner is unconstructible at report time
  (``ComplianceReport.__post_init__``).
* Identical derived finding ids deduplicate deterministically (first wins in
  inventory order); an id already present among engine findings is reused by
  reference — the rung's driver points at the existing finding and carries
  THAT finding's axis — never duplicated. Identical ids ACROSS engine
  results also dedupe: the first occurrence in engine-registration order
  wins (finding-id uniqueness is a report construction invariant).
* Engine ``ErrorRecord``s feed ``(error, driver)`` rungs so an engine
  failure can never be swallowed into a green verdict. The driver id uses
  the ``error:<kind>:<owner>`` grammar — the established 1.1/1.2 convention
  — and carries ``AXIS_VULNERABILITY``; Story 1.7 (typed errors / error
  grammar) owns the final grammar + axis choice.
* Finding-id segments derived from component names (and growable-enum
  tokens) are sanitized (``%`` -> ``%25`` FIRST — the escape scheme must
  escape its own escape character to stay injective — then ``%0D``/
  ``%0A``/``%3A``): the id grammar is single-line and colon-delimited by
  contract, while TOML happily embeds newlines, colons, or a literal
  ``%0A`` inside a dependency string. An empty segment (an empty growable
  token from a future producer) degrades to ``unspecified``, never a
  ``Finding`` construction crash. ``Finding.subject`` keeps the raw name.
* A clean rung requires FULL coverage: a component with
  ``vuln_matchable=False`` or ``hygiene_covered=False`` — even with no
  withhold reason stated (constructible by future producers) — derives an
  ``indeterminate:unmatchable:<pkg>`` / ``indeterminate:uncovered:<pkg>``
  finding + rung instead of ever feeding clean. The hygiene check is
  INDEPENDENT of the withhold reason (the reason describes the
  vulnerability axis): a withheld component that is also
  ``hygiene_covered=False`` (the RAW_MALFORMED production path) derives
  BOTH the withheld finding and the hygiene-axis ``uncovered`` finding —
  the hygiene axis never goes silent about a known deficiency.

This module is pure composition: no I/O, no subprocess, no network.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from .inventory import Component, ResolvedInventory
from .models import (
    AXIS_HYGIENE,
    AXIS_VULNERABILITY,
    AxisCoverage,
    Ecosystem,
    ErrorRecord,
    Finding,
    ScannedManifest,
    Status,
    StatusDriver,
)
from .verdict import match_level_rung


def _sanitize_id_segment(value: str) -> str:
    """Escape a value destined for a finding-id segment. ``%`` first (the
    escape scheme must escape its own escape character, or ``foo\\nbar``
    and a literal ``foo%0Abar`` would alias onto one id and silently
    dedupe two distinct components — waiver matching depends on
    injectivity), then CR/LF/colon (``%0D``/``%0A``/``%3A``): the id
    grammar is single-line and colon-delimited by contract, while TOML
    happily encodes any of them inside a dependency name. An empty value
    (an empty growable token from a future producer) degrades to
    ``unspecified`` instead of minting a grammar-violating id.
    Deterministic, so ids stay stable across runs; ``Finding.subject``
    keeps the raw value."""
    escaped = (
        value.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
        .replace(":", "%3A")
    )
    return escaped if escaped else "unspecified"


@dataclass(frozen=True)
class EngineResult:
    """What one engine run contributes to the report (findings + typed
    errors + its own coverage claims). The null engine returns the empty
    result; real engines (1.3/1.5) populate it.

    Ownership note (``coverage``): engine coverage claims are CONSUMED
    starting Story 1.3 — the 1.2 orchestrator deliberately discards them
    and derives the report's coverage itself (``report.assemble_report``,
    ``deps_assessed=0`` under the null engine). The field exists now so the
    seam's shape is frozen, not because 1.2 reads it."""

    findings: tuple[Finding, ...]
    errors: tuple[ErrorRecord, ...]
    coverage: tuple[AxisCoverage, ...]


@runtime_checkable
class Extractor(Protocol):
    """Turns one discovered manifest into honest (Gap-C) components."""

    def extract(
        self, manifest_path: Path, manifest: ScannedManifest
    ) -> tuple[Component, ...]: ...


@runtime_checkable
class Router(Protocol):
    """FR2 — per-(manifest-kind, section) ecosystem classification."""

    def route(self, manifest_kind: str, section: str) -> Ecosystem: ...


@runtime_checkable
class Engine(Protocol):
    """An assessment engine run against the target + inventory."""

    name: str

    def run(self, target: Path, inventory: ResolvedInventory) -> EngineResult: ...


@runtime_checkable
class VulnStrategy(Protocol):
    """Vulnerability-matching strategy over the resolved inventory."""

    def match(self, inventory: ResolvedInventory) -> EngineResult: ...


@runtime_checkable
class Policy(Protocol):
    """Evaluates the inventory + engine results into findings + fed rungs.

    Only ``verdict.py`` projects the fed rungs to a status/exit — a policy
    feeds, never projects."""

    def evaluate(
        self, inventory: ResolvedInventory, engine_results: Sequence[EngineResult]
    ) -> tuple[tuple[Finding, ...], tuple[tuple[Status, StatusDriver | None], ...]]: ...


class DefaultPolicy:
    """The 1.2 policy: engine pass-through + fail-closed inventory derivation.

    * Engine findings pass through with deterministic engine-vs-engine
      dedupe: identical ids across (or within) ``EngineResult``s keep the
      FIRST occurrence in engine-registration order — finding-id uniqueness
      is a report construction invariant, never a crash site.
    * Engine ``ErrorRecord``s feed ``(error, driver)`` rungs: an engine
      failure must reach the verdict (composition yields status ``error`` →
      ``exit_code_for`` gives the error exit), while the report is still
      emitted — the exit code is orthogonal to emission. The driver id uses
      the ``error:<kind>:<owner>`` grammar and carries
      ``AXIS_VULNERABILITY``; the Story 1.7 error-grammar story owns the
      final grammar + axis choice.
    * Each withheld component (``indeterminate_reason`` set) derives one
      ``indeterminate:<reason>:<pkg>`` finding (axis ``vulnerability``) and
      feeds an ``indeterminate`` rung whose driver references it.
    * A component is clean-eligible only when BOTH coverage booleans hold:
      with no withhold reason, ``vuln_matchable=False`` derives
      ``indeterminate:unmatchable:<pkg>`` (axis ``vulnerability``); and —
      INDEPENDENT of the withhold reason, which describes only the
      vulnerability axis — ``hygiene_covered=False`` derives
      ``indeterminate:uncovered:<pkg>`` (axis ``hygiene``), so a withheld
      RAW_MALFORMED component surfaces BOTH deficiencies. The id grammar's
      reason segment is free text, so no enum grows.
    * A fully-covered component feeds ``match_level_rung(cve_match_level)``;
      a non-clean landing also derives an ``indeterminate:<match-level>:
      <pkg>`` finding + driver, so every non-clean rung this policy feeds
      can say why.
    * Every rung driver carries the referenced finding's axis (also when the
      id is reused from an engine finding), and every id segment built from
      a component name is CR/LF-sanitized (``_sanitize_id_segment``).
    """

    def evaluate(
        self, inventory: ResolvedInventory, engine_results: Sequence[EngineResult]
    ) -> tuple[tuple[Finding, ...], tuple[tuple[Status, StatusDriver | None], ...]]:
        findings: list[Finding] = []
        rungs: list[tuple[Status, StatusDriver | None]] = []
        axis_by_id: dict[str, str] = {}
        for result in engine_results:
            for finding in result.findings:
                if finding.id in axis_by_id:
                    # Engine-vs-engine dedupe: first registration order wins.
                    continue
                findings.append(finding)
                axis_by_id[finding.id] = finding.axis
            for record in result.errors:
                # An engine failure must reach the verdict. Axis choice and
                # the error:<kind>:<owner> driver grammar are finalized by
                # the Story 1.7 error-grammar story. The owner segment is
                # sanitized like every id segment (single-line grammar).
                rungs.append(
                    (
                        Status.ERROR,
                        StatusDriver(
                            axis=AXIS_VULNERABILITY,
                            finding_id=(
                                f"error:{record.kind}:"
                                f"{_sanitize_id_segment(record.owner)}"
                            ),
                        ),
                    )
                )

        for component in inventory.components:
            subject = _sanitize_id_segment(component.name)
            # (rung, id token, finding axis, message) per deficiency.
            derived: list[tuple[Status, str, str, str]] = []
            if component.indeterminate_reason is not None:
                derived.append(
                    (
                        Status.INDETERMINATE,
                        _sanitize_id_segment(str(component.indeterminate_reason)),
                        AXIS_VULNERABILITY,
                        f"{component.name}: withheld from vulnerability "
                        f"matching ({component.indeterminate_reason})",
                    )
                )
            elif not component.vuln_matchable:
                derived.append(
                    (
                        Status.INDETERMINATE,
                        "unmatchable",
                        AXIS_VULNERABILITY,
                        f"{component.name}: not vulnerability-matchable "
                        "(no withhold reason stated) — cleanliness "
                        "cannot be claimed",
                    )
                )
            if not component.hygiene_covered:
                # Independent of the withhold reason: the reason describes
                # the VULNERABILITY axis; the hygiene axis must never go
                # silent about a known deficiency (the RAW_MALFORMED
                # production path carries both).
                derived.append(
                    (
                        Status.INDETERMINATE,
                        "uncovered",
                        AXIS_HYGIENE,
                        f"{component.name}: not hygiene-covered — "
                        "hygiene-axis cleanliness cannot be claimed",
                    )
                )
            if not derived:
                rung = match_level_rung(component.cve_match_level)
                if rung is Status.CLEAN:
                    rungs.append((rung, None))
                    continue
                derived.append(
                    (
                        rung,
                        _sanitize_id_segment(str(component.cve_match_level)),
                        AXIS_VULNERABILITY,
                        f"{component.name}: cve match level "
                        f"{str(component.cve_match_level)!r} cannot "
                        "prove cleanliness",
                    )
                )
            for rung, token, axis, message in derived:
                finding_id = f"indeterminate:{token}:{subject}"
                if finding_id not in axis_by_id:
                    findings.append(
                        Finding(
                            id=finding_id,
                            axis=axis,
                            message=message,
                            subject=component.name,
                            severity=None,
                        )
                    )
                    axis_by_id[finding_id] = axis
                rungs.append(
                    (
                        rung,
                        StatusDriver(
                            axis=axis_by_id[finding_id], finding_id=finding_id
                        ),
                    )
                )

        return (tuple(findings), tuple(rungs))
