"""Diagnose & Prescribe pipeline -- pure functions over already-gathered
``Finding``\\ s (Epic 3, FR-6/FR-7/FR-8, AD-4).

``AD-4``: ``doctor.prescribe`` adds ZERO subprocess/MCP calls of its own --
it consumes Epic 1's `checks` gather filter and Epic 2's `sources.atlas`
gather filter as already-shipped inputs (``list[Finding]`` in, structured
data out). The meta-test ``test_prescribe_pure_function.py`` enforces this
with an AST scan; this module's entire import surface is
``__future__``/``dataclasses``/``collections.abc``/``re``/``..models`` --
``re`` (stdlib) is Story 3.2's lightweight version-string parser, chosen
over the ``packaging`` library specifically because ``packaging`` is not a
declared ``pyforge-doctor`` dependency (see :func:`_leading_numeric_release`'s
own docstring).

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

import re
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


# --- Story 3.2: rank --------------------------------------------------------


@dataclass(frozen=True)
class RankedPrescription:
    """One actionable ``Finding``, ranked -- ``rank`` is 1-based (1 =
    highest priority); ``rank_factors`` names every signal that fired
    (Story 3.2 AC4: "never a bare integer with no explanation")."""

    finding: Finding
    rank: int
    rank_factors: dict


_SEVERITY_RANK = {DoctorStatus.FAIL: 2, DoctorStatus.WARN: 1, DoctorStatus.OK: 0}

# Mirrors `.claude/skills/conda-forge-expert/scripts/behind_upstream.py`'s
# own `_classify_lag` label set and "more behind = higher number" ordering
# -- reimplemented here (not imported: that script is a standalone CLI, not
# an importable library, and AD-4 forbids doctor.prescribe from reaching
# for it anyway) over whatever version-pair evidence a Finding happens to
# carry. Story 3.2 AC3's tiebreak wants the OPPOSITE ordering for ranking
# (patch < minor < major -- a SMALLER lag ranks first, "quick wins first"),
# so this tiebreak-priority map is intentionally the reverse of
# behind_upstream.py's own "bigger number = further behind" priority.
_BLAST_RADIUS_TIEBREAK = {
    "patch": 0,
    "minor": 1,
    "major": 2,
    "unknown": 3,
    "current": 4,
}


def _leading_numeric_release(value: str) -> tuple[int, ...] | None:
    """Best-effort dotted-numeric release extraction (``"1.2.3rc1"`` ->
    ``(1, 2, 3)``) -- deliberately NOT full PEP 440 (no pre/post/dev/local
    segment handling, no ``packaging`` import: that library is not a
    declared ``pyforge-doctor`` dependency, and full PEP 440 semantics are
    unneeded here -- see this function's own caller's docstring for why
    blast-radius classification degrades to ``"unknown"`` for every live
    Finding today regardless). ``None`` for a string with no leading
    digit."""
    match = re.match(r"^(\d+(?:\.\d+)*)", value.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def _classify_blast_radius(evidence: dict) -> tuple[str, int]:
    """Reimplements ``behind_upstream.py``'s own patch/minor/major/unknown/
    current classification as a pure function over evidence keys, not a
    DB/tool call (AD-4). No current Source producer's evidence carries both
    a "current" and a "target" version field (``staleness``'s evidence has
    only ``latest_conda_version``, no upstream target), so this resolves to
    ``("unknown", 3)`` for every Finding gathered by today's live axes --
    expected and documented, not a bug (see this story's own Design Notes).
    Directly exercised with synthetic evidence by the unit suite."""
    conda_v = evidence.get("latest_conda_version") or evidence.get("conda_version")
    target_v = evidence.get("upstream_version") or evidence.get("pypi_current_version")
    if not conda_v or not target_v:
        return ("unknown", _BLAST_RADIUS_TIEBREAK["unknown"])
    conda_v, target_v = str(conda_v), str(target_v)
    if conda_v == target_v:
        return ("current", _BLAST_RADIUS_TIEBREAK["current"])
    c_rel = _leading_numeric_release(conda_v)
    t_rel = _leading_numeric_release(target_v)
    if not c_rel or not t_rel:
        return ("unknown", _BLAST_RADIUS_TIEBREAK["unknown"])
    if t_rel <= c_rel:
        return ("current", _BLAST_RADIUS_TIEBREAK["current"])
    if t_rel[0] != c_rel[0]:
        return ("major", _BLAST_RADIUS_TIEBREAK["major"])
    if len(c_rel) >= 2 and len(t_rel) >= 2 and t_rel[1] != c_rel[1]:
        return ("minor", _BLAST_RADIUS_TIEBREAK["minor"])
    return ("patch", _BLAST_RADIUS_TIEBREAK["patch"])


def _is_kev(finding: Finding) -> bool:
    """``evidence["kev"]`` is the direct, source-agnostic signal (a
    synthetic fixture, or a future producer, can set it directly). As a
    real-data heuristic, a ``Source.CVE_WATCHER`` Finding gathered at
    ``severity="K"`` (cve_watcher's own KEV-listed axis) with a positive
    current count is ALSO a KEV signal, even without the explicit key --
    see ``sources/atlas.py``'s own ``_normalize_cve_rows``, which stamps
    ``evidence["severity"]`` from the axis's own query parameter."""
    evidence = finding.evidence
    if evidence.get("kev"):
        return True
    if finding.source is Source.CVE_WATCHER and evidence.get("severity") == "K":
        now_v = evidence.get("now_v")
        return isinstance(now_v, (int, float)) and now_v > 0
    return False


def _epss_score(finding: Finding) -> float | None:
    epss = finding.evidence.get("epss")
    return epss if isinstance(epss, (int, float)) and not isinstance(epss, bool) else None


def _rank_factors_and_sort_key(finding: Finding) -> tuple[tuple, dict]:
    severity_rank = _SEVERITY_RANK.get(finding.status, 0)
    kev = _is_kev(finding)
    epss = _epss_score(finding)
    blast_label, blast_tiebreak = _classify_blast_radius(finding.evidence)

    sort_key = (
        -severity_rank,
        -int(kev),
        -(epss if epss is not None else 0.0),
        blast_tiebreak,
    )
    rank_factors = {"kev": kev, "epss": epss, "blast_radius": blast_label}
    return sort_key, rank_factors


def rank(partitioned: Iterable[PartitionedFinding]) -> tuple[RankedPrescription, ...]:
    """Order the ``ACTIONABLE`` partition by severity x exploitability x
    blast-radius (Story 3.2, FR-7). Pure -- reads only each ``Finding``'s
    own ``status``/``source``/``evidence``.

    Sort key (ascending; first = rank 1 = highest priority):

    1. severity (``FAIL`` > ``WARN`` > ``OK``) -- higher severity ranks
       first (Story 3.2's own implicit precondition: severity is the
       PRIMARY signal, the AC's tie-break scenarios all hold severity
       equal).
    2. KEV flag -- a KEV-flagged Finding ranks above an equal-severity
       non-KEV Finding (AC1).
    3. EPSS score -- a higher score ranks above a lower one at equal
       severity+KEV (AC2).
    4. Blast-radius tier, reusing ``behind-upstream``'s own lag
       classification -- ``patch`` ranks above ``minor`` above ``major``
       (AC3's own explicit ordering: a smaller/quicker fix wins the final
       tiebreak).

    Every ranked ``RankedPrescription`` carries a ``rank_factors`` object
    naming which signals fired -- never a bare integer (AC4). Non-actionable
    partitions (``BLOCKED``/``ACCEPTED_RISK``) are excluded from the
    returned ranking entirely -- ranking is meaningless for a Finding
    that isn't actionable today; Story 3.4's CLI layer is responsible for
    still reporting them (unranked) per Story 3.1's own "never a silent
    drop" rule."""
    actionable = [
        pf.finding for pf in partitioned if pf.partition is Partition.ACTIONABLE
    ]
    # `key=` extracts the sort key ONCE per item and never compares the
    # `Finding`s themselves (frozen dataclasses have no `__lt__`) -- a tie
    # on the sort key falls back to Python's stable-sort input order, never
    # a TypeError from comparing two Findings directly (review finding,
    # caught before this ever reached a test: an earlier draft embedded
    # `finding` inside the sorted tuples themselves, which raises on any
    # tie).
    scored = [
        (finding, *_rank_factors_and_sort_key(finding)) for finding in actionable
    ]
    scored.sort(key=lambda item: item[1])
    return tuple(
        RankedPrescription(finding=finding, rank=index + 1, rank_factors=factors)
        for index, (finding, _sort_key, factors) in enumerate(scored)
    )


# --- Story 3.3: root-cause naming ------------------------------------------


def _find_correlated_staleness(
    finding: Finding, all_findings: Sequence[Finding]
) -> Finding | None:
    """A same-``check`` ``Source.STALENESS_REPORT`` Finding in the same
    gather batch, if one exists -- the correlation Story 3.3 AC1 asks for
    ("a Prescription for a CVE Finding that traces to a staleness lag").
    Never the SAME Finding object (a Finding is never "correlated" with
    itself); ``status`` is not filtered here -- any staleness signal for
    the same package is evidence of a lag, regardless of its own
    WARN/FAIL tier."""
    for other in all_findings:
        if (
            other is not finding
            and other.source is Source.STALENESS_REPORT
            and other.check == finding.check
        ):
            return other
    return None


def _cve_root_cause(finding: Finding, all_findings: Sequence[Finding]) -> str:
    staleness = _find_correlated_staleness(finding, all_findings)
    evidence = finding.evidence
    severity = evidence.get("severity")
    delta = evidence.get("delta")
    now_v = evidence.get("now_v")
    if staleness is not None:
        age_days = staleness.evidence.get("age_days")
        version = staleness.evidence.get("latest_conda_version")
        return (
            f"{finding.check}'s {severity or ''}-severity vulnerability count is "
            f"{now_v!s} (delta {delta!s}) -- correlated with a staleness signal "
            f"for the same package (pinned at {version!s}, {age_days!s} days "
            "stale): the fix most likely already shipped upstream and simply "
            "hasn't been adopted yet, rather than being genuinely unfixed."
        )
    return (
        f"{finding.check}'s {severity or ''}-severity vulnerability count is "
        f"{now_v!s} (delta {delta!s}) -- no correlated staleness signal for "
        "this package in the same run, so this may be a newly-disclosed CVE "
        "with no upstream fix yet rather than an adoption lag."
    )


def _templated_root_cause(finding: Finding) -> str:
    """Templates a root cause from a Finding's own ``evidence`` (Story 3.3
    AC2's "no new NLP/inference layer -- a pure template over already-
    structured evidence") -- every non-CVE Source (``warden-doctor``,
    ``staleness-report``, ``feedstock-health``, ``release-cadence``,
    ``env-hygiene``) is templated this way, not just the AC's own named
    "engine-missing" example, since the templating rule itself is
    Source-agnostic: join whatever structured evidence the Finding
    actually carries. Degrades to the Finding's own ``message`` verbatim
    when ``evidence`` is empty (e.g. today's live ``warden-doctor``
    Findings, which Story 1.2 documents as always carrying ``evidence={}``)
    -- ``message`` is itself already a human-readable explanation, not a
    placeholder, so this is a genuine fallback, not a degraded one."""
    if not finding.evidence:
        return finding.message
    evidence_clause = "; ".join(
        f"{key}={value!s}" for key, value in sorted(finding.evidence.items())
    )
    return f"{finding.message} (evidence: {evidence_clause})"


def name_root_cause(finding: Finding, all_findings: Sequence[Finding]) -> str:
    """Name WHY ``finding`` exists, not just what it is (Story 3.3, FR-8).
    Pure -- reads only ``finding`` and the other already-gathered
    ``all_findings`` it's being diagnosed alongside (for cross-Finding
    correlation, e.g. CVE-traces-to-staleness); makes zero external calls.

    ``Source.CVE_WATCHER`` Findings get a dedicated root-cause path that
    checks for a same-``check`` ``Source.STALENESS_REPORT`` Finding in
    ``all_findings`` (AC1: "traces to a staleness lag... names that lag").
    Every other Source templates its root cause from its own ``evidence``
    field, falling back to the Finding's own ``message`` when ``evidence``
    is empty (AC2: "templated from that Finding's own evidence field")."""
    if finding.source is Source.CVE_WATCHER:
        return _cve_root_cause(finding, all_findings)
    return _templated_root_cause(finding)
