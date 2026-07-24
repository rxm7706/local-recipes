"""The strategy layer — five Protocols + ``EngineResult`` + ``DefaultPolicy``
(Story 1.2).

Ownership decisions recorded here:

* Interface mechanics are ``typing.Protocol`` (structural typing — no ABC
  inheritance tax). Implementations live in their stage modules
  (``engines.py`` owns the engine registry, ``extract/`` the extractors,
  ``routing.py`` the router) and *conform* to these shapes; Stories
  1.3/1.5/2.x implement the seams, never redesign them. ``DefaultPolicy``
  is the RECORDED EXCEPTION to that layering rule: the fail-closed
  inventory→verdict bridge lives WITH the seam it closes. Story 3.1 landed
  the policy stage module (``config.py``'s ``EffectiveConfig``/
  ``ConfigLoader``); ``DefaultPolicy`` now consumes it (``self._config``)
  for DEP001's mapping-confidence trust threshold and the vulnerability-
  axis severity→status table, defaulting to ``EffectiveConfig.default()``
  when no config is supplied.
* Engine findings pass through into the report AND each feeds one
  conservative ``indeterminate`` rung whose driver references it — the
  FALSE-GREEN BACKSTOP: ``register_engine`` is a public seam, so a
  findings-only engine result is reachable today, and a report carrying
  findings must never compose ``clean``/exit 0 (C0c). The finding→severity
  policy mapping (which findings escalate to ``policy-violation``) is now
  real for hygiene (Story 1.3) and vulnerability (Story 1.6) — each
  REPLACING the backstop for its own axis; both may only tighten (toward
  ``policy-violation``), never loosen (toward ``clean``). Story 6.2 (license)
  and Story 6.3 (currency) also replace the backstop for their own axes,
  each with a HARD ``Status.WARN`` cap (``license_rung``/``currency_rung``),
  not a real escalation table — real ``denied``/``unknown`` (license) and
  ``eol``/``over-lag``/``unknown`` (currency) escalation is Story 6.5's sole
  ownership. The backstop itself now only governs a hypothetical future axis
  with no mapping of its own yet.
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
  — and carries the PRODUCING engine's own axis (``result.axis``; Story 1.7
  landed the final grammar + axis choice), never a blanket default.
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

from .config import EffectiveConfig
from .inventory import Component, ResolvedInventory
from .models import (
    AXIS_CURRENCY,
    AXIS_HYGIENE,
    AXIS_LICENSE,
    AXIS_VULNERABILITY,
    AxisCoverage,
    Ecosystem,
    ErrorRecord,
    FeedProvenance,
    Finding,
    ScannedManifest,
    Status,
    StatusDriver,
    VulnData,
)
from .verdict import match_level_rung

# Every character str.splitlines() treats as a line boundary, mapped to a
# percent-escape. All are str.isspace()-true, so an interior one survives the
# entry .strip() and would otherwise reach a finding-id segment and split it
# for a line-oriented consumer. CR/LF keep their historical %0D/%0A forms; the
# astral separators (U+2028/U+2029) use a %uXXXX form to stay unambiguous
# against the 2-hex escapes.
_LINE_BOUNDARY_ESCAPES: dict[str, str] = {
    "\r": "%0D",
    "\n": "%0A",
    "\x0b": "%0B",
    "\x0c": "%0C",
    "\x1c": "%1C",
    "\x1d": "%1D",
    "\x1e": "%1E",
    "\x85": "%85",
    " ": "%u2028",
    " ": "%u2029",
}


def _sanitize_id_segment(value: str) -> str:
    """Escape a value destined for a finding-id segment. ``%`` first (the
    escape scheme must escape its own escape character, or ``foo\\nbar``
    and a literal ``foo%0Abar`` would alias onto one id and silently
    dedupe two distinct components — waiver matching depends on
    injectivity), then EVERY Python line-boundary character (the full
    ``_LINE_BOUNDARY_ESCAPES`` set that ``str.splitlines`` splits on,
    each ``str.isspace``-true, so an interior one survives the entry
    ``.strip()`` and reaches a ``RAW_MALFORMED`` name) plus the colon
    delimiter: the id grammar is single-line and colon-delimited by
    contract, while TOML happily encodes any of them inside a dependency
    name. An empty value (an empty growable token from a future producer)
    degrades to ``unspecified`` instead of minting a grammar-violating id.
    Deterministic, so ids stay stable across runs; ``Finding.subject``
    keeps the raw value."""
    escaped = value.replace("%", "%25")
    for char, replacement in _LINE_BOUNDARY_ESCAPES.items():
        escaped = escaped.replace(char, replacement)
    escaped = escaped.replace(":", "%3A")
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
    seam's shape is frozen, not because 1.2 reads it.

    ``vuln_data`` (Story 1.5, additive/defaulted — ``NullEngine``/
    ``DeptryEngine`` unaffected): populated ONLY by a vulnerability-axis
    engine that successfully consulted a provenance-bearing DB
    (``OsvEngine`` on a completed 0/1 osv-scanner run); ``None`` on every
    other engine result, including osv's own DB-unavailable/error paths.
    ``cli.py`` threads the first non-``None`` value across ``engine_results``
    into ``report.assemble_report``.

    ``kev_data`` (Story 6.4, additive/defaulted — mirrors ``vuln_data``'s
    own shape and threading): populated ONLY by ``OsvEngine`` when
    ``fail_on_kev`` is active AND the CISA KEV feed was actually consulted
    (present, whether fresh or stale); ``None`` when KEV consultation is
    disabled (``fail_on_kev=False``) or the feed is absent/unreadable.
    ``cli.py`` threads the first non-``None`` value across
    ``engine_results`` into ``report.assemble_report`` the same way.

    ``currency_data`` (Story 6.3, additive/defaulted — mirrors ``kev_data``'s
    own shape and threading): populated by ``CurrencyEngine`` with the
    bundled LTS registry's own ``FeedProvenance`` (``currency.
    currency_findings``'s second return value) — ``None`` whenever no
    usable provenance can be derived: the bundled registry is absent,
    unreadable, unparsable, not a mapping, or its ``updated:`` date is
    missing/unparsable (``currency._load_registry`` degrades every read
    failure to ``{}``, whose missing ``updated:`` then yields ``None`` —
    see ``currency.py``'s module docstring). ``cli.py`` threads the first
    non-``None`` value across ``engine_results`` into
    ``report.assemble_report`` the same way."""

    findings: tuple[Finding, ...]
    errors: tuple[ErrorRecord, ...]
    coverage: tuple[AxisCoverage, ...]
    axis: str
    vuln_data: VulnData | None = None
    kev_data: FeedProvenance | None = None
    currency_data: FeedProvenance | None = None


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
    axis: str

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
      is a report construction invariant, never a crash site. Each unique
      engine finding ALSO feeds one conservative ``indeterminate`` rung
      (driver = that finding) — the false-green backstop: a finding-carrying
      report never composes ``clean``. Story 1.3 (hygiene) and Story 1.6
      (vulnerability) have each replaced the backstop with their axis's real
      severity mapping (tighten-only); Story 6.2 (license) and Story 6.3
      (currency) replace it with a hard ``Status.WARN`` cap instead (real
      escalation is Story 6.5's); the backstop itself now only fires for a
      hypothetical future axis.
    * Engine ``ErrorRecord``s feed ``(error, driver)`` rungs: an engine
      failure must reach the verdict (composition yields status ``error`` →
      ``exit_code_for`` gives the error exit), while the report is still
      emitted — the exit code is orthogonal to emission. The driver id uses
      the ``error:<kind>:<owner>`` grammar and carries the PRODUCING
      engine's own axis (Story 1.7 landed the final grammar + axis choice).
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

    def __init__(self, config: EffectiveConfig | None = None) -> None:
        # No config -> EffectiveConfig.default(), which reproduces every
        # pre-3.1 caller's behavior byte-for-byte (Story 3.1's Boundaries:
        # DefaultPolicy() must stay unchanged).
        self._config = config or EffectiveConfig.default()

    def evaluate(
        self, inventory: ResolvedInventory, engine_results: Sequence[EngineResult]
    ) -> tuple[tuple[Finding, ...], tuple[tuple[Status, StatusDriver | None], ...]]:
        # Lazy imports break the interfaces<->hygiene, interfaces<->vuln, and
        # interfaces<->license cycles; by the time evaluate() runs, all
        # modules are fully loaded.
        from .currency import currency_rung
        from .hygiene import hygiene_rung
        from .license import license_rung
        from .vuln import vuln_rung

        # Story 2.1, Gap-A: DEP001 is trusted (blocks) unless the inventory
        # carries a positive ambiguous-mapping signal — a component whose
        # mapping_confidence ranks below the configured
        # dep001_block_confidence threshold (Story 3.1: self._config.
        # is_confidence_trusted, default "verified") — anywhere. Computed
        # once per scan, not per finding (see hygiene.hygiene_rung's
        # docstring for why). A total map miss (mapping_confidence is None)
        # does NOT count as ambiguous: most conda packages are legitimately
        # non-Python/native and will NEVER have a pypi_identity, so treating
        # every miss as a distrust signal would make this gate false almost
        # universally — only a POSITIVE untrusted candidate is evidence the
        # mapping pipeline actually saw ambiguity for this scan.
        dep001_trusted = all(
            self._config.is_confidence_trusted(component.mapping_confidence)
            for component in inventory.components
        )

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
                if finding.axis == AXIS_HYGIENE:
                    # Story 1.3: hygiene-axis engine findings route through the
                    # real default hygiene->status table (DEP001 blocks;
                    # DEP002-005 warn; an unknown DEP code still degrades to
                    # indeterminate). This REPLACES the 1.2 indeterminate
                    # backstop for the hygiene axis only — never mapping a
                    # finding to clean (C0 preserved).
                    rungs.append(hygiene_rung(finding, dep001_trusted=dep001_trusted))
                elif finding.axis == AXIS_VULNERABILITY:
                    # Story 1.6: vulnerability-axis engine findings route
                    # through the real default severity->status table
                    # (CRITICAL blocks; HIGH/MEDIUM/LOW/NONE warn; an
                    # unmapped/absent severity, including UNKNOWN, still
                    # degrades to indeterminate). This REPLACES the 1.2
                    # indeterminate backstop for the vulnerability axis too —
                    # never mapping a finding to clean (C0 preserved). The
                    # axis's own indeterminate: withhold findings (severity
                    # is None) still land on indeterminate via vuln_rung's
                    # own fallback, unchanged from today. Story 3.1: the
                    # policy table is derived from self._config's fail_on
                    # (default reproduces DEFAULT_VULN_SEVERITY_POLICY
                    # exactly). Story 6.4: fail_on_kev threads the same way
                    # -- a KEV-listed finding forces policy-violation
                    # independent of the CVSS tier above.
                    rungs.append(
                        vuln_rung(
                            finding,
                            policy=self._config.vuln_severity_policy,
                            fail_on_kev=self._config.fail_on_kev,
                        )
                    )
                elif finding.axis == AXIS_LICENSE:
                    # Story 6.2: license-axis engine findings route through
                    # license_rung, a HARD Status.WARN cap that never
                    # consults self._config.license_policy and never
                    # escalates (real denied->policy-violation / unknown->
                    # indeterminate escalation is Story 6.5's sole
                    # ownership). This REPLACES the 1.2 indeterminate
                    # backstop for the license axis too — never mapping a
                    # finding to clean (C0 preserved).
                    rungs.append(license_rung(finding))
                elif finding.axis == AXIS_CURRENCY:
                    # Story 6.3: currency-axis engine findings route through
                    # currency_rung, a HARD Status.WARN cap that never
                    # consults self._config.currency_policy and never
                    # escalates (real eol/over-lag->policy-violation /
                    # unknown->indeterminate escalation is Story 6.5's sole
                    # ownership). This REPLACES the 1.2 indeterminate
                    # backstop for the currency axis too — never mapping a
                    # finding to clean (C0 preserved).
                    rungs.append(currency_rung(finding))
                else:
                    # The false-green backstop now only governs a
                    # hypothetical future axis with no mapping of its own: a
                    # finding-carrying report must never compose clean/exit 0
                    # (C0c). One conservative indeterminate rung per engine
                    # finding until that axis gets its own real mapping
                    # (tighten-only).
                    rungs.append(
                        (
                            Status.INDETERMINATE,
                            StatusDriver(axis=finding.axis, finding_id=finding.id),
                        )
                    )
            for record in result.errors:
                # An engine failure must reach the verdict. The driver
                # carries the PRODUCING engine's own axis (Story 1.7 landed
                # the final error:<kind>:<owner> grammar + axis choice) —
                # never a blanket default. The owner segment is sanitized
                # like every id segment (single-line grammar).
                rungs.append(
                    (
                        Status.ERROR,
                        StatusDriver(
                            axis=result.axis,
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
            # Story 6.1: the license/currency coverage mechanism, landed inert
            # (every 6.1-era component is license_covered/currency_covered=True;
            # producers set False later). The reason tokens MUST be
            # axis-qualified — a bare "uncovered" (hygiene's token) would
            # collide all three onto one id ("indeterminate:uncovered:<name>")
            # and silently swallow two axes via the id-dedupe below.
            if not component.license_covered:
                derived.append(
                    (
                        Status.INDETERMINATE,
                        "uncovered-license",
                        AXIS_LICENSE,
                        f"{component.name}: not license-covered — "
                        "license-axis cleanliness cannot be claimed",
                    )
                )
            if not component.currency_covered:
                derived.append(
                    (
                        Status.INDETERMINATE,
                        "uncovered-currency",
                        AXIS_CURRENCY,
                        f"{component.name}: not currency-covered — "
                        "currency-axis cleanliness cannot be claimed",
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
