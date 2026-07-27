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
  correlated to one component even now that Story 2.2's synthesized
  front-door (``_synthesize_deptry_frontdoor``, below) exists — a module
  name is still not a distribution name; the trust gate is therefore
  scan-wide, not per-finding — false only when the inventory shows a
  positive ambiguous-mapping signal (a ``"likely"``-confidence conda
  component) anywhere, which the front-door now makes REACHABLE for a
  conda-sourced scan for the first time (previously only a
  ``pyproject.toml``-native scan could ever populate the inventory this
  gate reads). An UNKNOWN DEP code
  degrades to ``indeterminate`` (never a false-green — a new deptry code we
  have not classified must not silently pass). Story 3.1 lifts this default
  into an overridable config table; 1.3/2.1 keep it here.
* **DEP005 = stdlib dependency** (verified against deptry 0.25.1, 2026-07-13:
  ``'argparse' is defined as a dependency but it is included in the Python
  standard library.``). The architecture's pinned "unused-dev" label was
  wrong; ``DEP005 → warn`` is still the correct ceiling.
* ``_synthesize_deptry_frontdoor`` (Story 2.2, FR8's conda half):
  ``engines.DeptryEngine.run`` unconditionally synthesizes a
  ``--requirements-files`` input from EVERY component where
  ``hygiene_covered and pypi_identity is not None`` — a materially
  BROADER filter than ``vuln._synthesize_requirements``'s
  ``vuln_matchable`` pre-filter (Gap-C's concrete-version-only rule is a
  vuln-matching concern, not a hygiene one: deptry needs to know a
  package's NAME is a declared dependency, not that its version is
  exactly pinned). A component with a resolved identity but no concrete
  version writes a BARE name line (deptry's own requirements parser
  accepts a bare name — no version at all is still a valid "this is a
  declared dependency" signal); a concrete version writes
  ``name==version``. This is why DEP001 trust-gating (see above) is
  scan-wide, not per-finding: it now also governs conda-sourced hygiene
  findings this synthesized front-door makes possible for the first
  time. The NFR-S6 safe-token purity guard (``_is_safe_token``/
  ``_SAFE_TOKEN_CHARS``) is DUPLICATED here rather than imported from
  ``vuln.py`` — a small, security-relevant guard stays locally auditable
  in each producing module rather than cross-module-coupled. (The inert
  ``SynthesizedInput`` carrier dataclass IS imported from ``vuln.py``:
  it is a pure data shape with no guard logic, so sharing it is not the
  coupling the guard-duplication rationale avoids.) Beyond the charset
  guard, every line is also validated against ``packaging``'s OWN
  ``Requirement`` grammar before it is written (2026-07-16): deptry
  parses each front-door line with that same grammar and CRASHES the
  whole run (exit 1, no output file — verified live against deptry
  0.25.x) on the first invalid line, so one
  conda-legal-but-PEP-440-illegal identity (``numpy==1.20rc1x``) used to
  take the ENTIRE hygiene axis down with it. An invalid line is excluded
  + surfaced exactly like a charset failure, never written.
* ``unsafe_identity_finding`` (Fix 6, 2026-07-16): ``SynthesizedInput.
  excluded`` (the NFR-S6-guard-excluded components above) was computed but
  then silently discarded by ``engines.DeptryEngine.run`` — unlike
  ``OsvEngine.run``, which always turns its own parallel-shaped
  ``.excluded`` list into one ``indeterminate:unsafe-identity:<pkg>``
  finding per component via ``vuln.unsafe_identity_finding``. This module's
  own ``unsafe_identity_finding``/``_indeterminate_finding`` mirror that
  shape but hardcode ``AXIS_HYGIENE`` and use the DISTINCT reason segment
  ``unsafe-identity-hygiene`` (duplicated, not imported — same reasoning as
  ``_is_safe_token`` above: a wrong-axis import would silently roll the
  finding into the vulnerability axis's verdict instead of hygiene's; and a
  shared id family would collide in ``DefaultPolicy.evaluate``'s id-keyed
  dedupe when one component is excluded by BOTH front-doors, silently
  dropping the vuln-axis record — fixed 2026-07-16).
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
* ``has_adjacent_python_source`` (Story 2.4, AC3): a bounded, entry-capped
  ``os.walk`` predicate ``cli.py``'s orchestration consults BEFORE
  deciding whether to run ``DeptryEngine`` at all -- deliberately NOT a
  check inside ``DeptryEngine.run`` itself (``tests/unit/
  test_engine_env_deptry.py`` calls the engine directly against bare
  ``tmp_path`` dirs ~20 times to test its own argv/error-handling logic in
  isolation; embedding the skip there would exercise the wrong branch in
  every one of those tests -- see the story's Design Notes). A source-less
  conda/pixi manifest (the fleet's majority feedstock shape) makes deptry
  flag every conda-sourced dependency reaching the front-door as "unused"
  (DEP002) -- a noise wall, not a signal -- so ``cli.py`` filters
  ``DeptryEngine`` out of ``engines_to_run`` when this returns ``False`` and
  tells ``report.assemble_report`` the hygiene axis is not-applicable.

This module parses JSON as DATA: no subprocess, no network, no exec.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from packaging.requirements import InvalidRequirement, Requirement

from .interfaces import _sanitize_id_segment
from .inventory import Component
from .models import (
    AXIS_HYGIENE,
    ErrorKind,
    ErrorRecord,
    Finding,
    Status,
    StatusDriver,
)
from .vuln import SynthesizedInput

# The owner label every deptry-sourced error/finding carries.
_OWNER = "deptry"

# The default hygiene policy: DEP-code → Status. DEP001 blocks by default
# (Story 2.1, Gap-A); hygiene_rung downgrades it to warn on a per-scan
# untrusted-mapping signal (dep001_trusted=False — see module docstring).
# DEP002-005 stay warn (deptry false-positive-prone, unrelated to mapping
# confidence). Keys are deptry DEP codes (NOT Status tokens), so the
# sole-ownership rung-ordering guard does not fire on this literal.
# MappingProxyType-wrapped (Story 3.1, deferred-work.md): closes the same
# unprotected-mutable-module-dict finding vuln.DEFAULT_VULN_SEVERITY_POLICY
# closes; this table stays non-overridable in v1 (no `policy` parameter is
# added to status_for_code/hygiene_rung — Design Notes explain why), so the
# wrap is the ownership/immutability half only, never a config seam.
DEFAULT_HYGIENE_POLICY: Mapping[str, Status] = MappingProxyType(
    {
        "DEP001": Status.POLICY_VIOLATION,
        "DEP002": Status.WARN,
        "DEP003": Status.WARN,
        "DEP004": Status.WARN,
        "DEP005": Status.WARN,
    }
)

# Ratchet baseline (NFR-R2): the fraction of deptry records we fail to map may
# only ever decrease. A conformance test pins the real corpus at/below this.
UNPARSEABLE_RATE_BASELINE = 0.0


# --- Story 2.4 (AC3): the "no adjacent Python source" predicate -----------

# NFR-S5 bound: the max number of directory ENTRIES (files + subdirs,
# summed across the whole walk) examined before giving up. A real project's
# tree is orders of magnitude smaller; this exists so a pathological/huge
# tree can never turn a cheap pre-scan check into an unbounded walk.
_ADJACENT_PYTHON_SOURCE_ENTRY_CAP = 50_000


def has_adjacent_python_source(target: Path) -> bool:
    """Whether at least one ``*.py`` file exists anywhere under ``target``.

    A bounded, early-exiting ``os.walk`` — never a subprocess, never
    Jinja/execution (this is a pure filesystem-shape check, not
    extraction). ``.git`` directories are pruned from the walk (never
    genuinely a project's own Python source). The
    ``_ADJACENT_PYTHON_SOURCE_ENTRY_CAP`` bound is enforced ENTRY BY ENTRY
    (both directory names and file names, as they are visited) rather than
    once per ``os.walk`` step — a single directory holding far more than
    the cap in non-``.py`` files still bails out at the cap instead of
    scanning that whole directory's listing first (review finding,
    2026-07-17).

    Two "can't tell" cases both resolve to ``True`` (never silently skip
    the hygiene axis off an inconclusive answer — the same "more scrutiny,
    not less" bias ``hygiene_rung``'s ``dep001_trusted`` default documents):
    hitting the entry cap without a match, and ``os.walk`` being unable to
    descend into a subdirectory at all (permission-denied, vanished
    mid-walk — ``os.walk``'s default ``onerror=None`` otherwise swallows
    the failure and just omits that subtree, which reads identically to
    "genuinely no .py there"). Only an EXHAUSTIVE negative walk returns
    ``False``."""
    inconclusive = False

    def _on_error(_exc: OSError) -> None:
        nonlocal inconclusive
        inconclusive = True

    entries_visited = 0
    for _dirpath, dirnames, filenames in os.walk(target, onerror=_on_error):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        entries_visited += len(dirnames)
        if entries_visited >= _ADJACENT_PYTHON_SOURCE_ENTRY_CAP:
            return True
        for name in filenames:
            if name.endswith(".py"):
                return True
            entries_visited += 1
            if entries_visited >= _ADJACENT_PYTHON_SOURCE_ENTRY_CAP:
                return True
    return inconclusive


# --- Story 2.2 (FR8's conda half): the deptry front-door -----------------

# NFR-S6 purity guard: a manifest-derived name/version must be exactly this
# token shape to be written into the synthesized deptry input. DUPLICATED
# from ``vuln._is_safe_token``/``_SAFE_TOKEN_CHARS`` rather than imported
# (see module docstring) — a security-relevant guard stays locally
# auditable in each producing module.
_SAFE_TOKEN_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-"
)


def _is_safe_token(value: str) -> bool:
    """NFR-S6: exactly the ``[A-Za-z0-9._-]+`` token shape AND not leading
    with ``-`` (a pip-option-injection shape even though ``-`` is itself in
    the allowed charset). Mirrors ``vuln._is_safe_token`` exactly."""
    return (
        bool(value)
        and not value.startswith("-")
        and all(char in _SAFE_TOKEN_CHARS for char in value)
    )


def _is_valid_requirement_line(line: str) -> bool:
    """deptry parses each ``--requirements-files`` line with ``packaging``'s
    own ``Requirement`` grammar and CRASHES the whole run (exit 1, no output
    file — verified live against deptry 0.25.x) on the first invalid line,
    taking the entire hygiene axis down with it. A conda-legal but
    PEP-508/440-illegal identity (``numpy==1.20rc1x``, a trailing-hyphen
    name) passes the charset-only ``_is_safe_token`` guard, so every
    synthesized line must ALSO parse under that same grammar before it is
    written (fixed 2026-07-16)."""
    try:
        Requirement(line)
    except InvalidRequirement:
        return False
    return True


def _synthesize_deptry_frontdoor(components: Sequence[Component]) -> SynthesizedInput:
    """Turn every hygiene-covered, identified component into a sorted,
    de-duplicated pip-requirements-style line for deptry's
    ``--requirements-files`` front-door (Story 2.2): ``name==version`` when
    a concrete version is known, a BARE ``name`` otherwise (deptry's own
    requirements parser accepts a bare name — "this is a declared
    dependency" doesn't require an exact pin the way vuln-matching does).
    The filter is ``hygiene_covered and pypi_identity is not None`` —
    deliberately NOT ``vuln_matchable`` (see module docstring): a
    range-only or unversioned-but-mapped conda dependency still deserves a
    hygiene signal. A component whose resolved name/version fails the
    NFR-S6 safe-token purity guard — or whose synthesized line fails
    ``packaging``'s own ``Requirement`` grammar, which would crash deptry
    itself (see ``_is_valid_requirement_line``) — is excluded (never
    written raw) and reported back via ``SynthesizedInput.excluded``."""
    lines: list[str] = []
    excluded: list[Component] = []
    for component in components:
        # Uncovered deps stay invisible here — DefaultPolicy derives
        # ``indeterminate:uncovered:<pkg>@…``. Covered-but-no-identity is the
        # third bucket (AUD-WARDEN-018): must land on ``excluded`` so coverage
        # and findings stay honest (never a silent ``continue``).
        if not component.hygiene_covered:
            continue
        if component.pypi_identity is None:
            excluded.append(component)
            continue
        identity = component.pypi_identity
        if not _is_safe_token(identity.name):
            excluded.append(component)
            continue
        if identity.version:
            if not _is_safe_token(identity.version):
                excluded.append(component)
                continue
            line = f"{identity.name}=={identity.version}"
        else:
            line = identity.name
        if not _is_valid_requirement_line(line):
            excluded.append(component)
            continue
        lines.append(line)
    return SynthesizedInput(lines=tuple(sorted(set(lines))), excluded=tuple(excluded))


def _indeterminate_finding(reason: str, component: Component, message: str) -> Finding:
    """Mirrors ``vuln._indeterminate_finding``'s id family/subject shape
    exactly (duplicated, not imported: ``vuln.py``'s own copy hardcodes
    ``AXIS_VULNERABILITY``, and a finding this module produces must carry
    ``AXIS_HYGIENE`` — the same axis its own front-door synthesis feeds —
    or it would silently roll up into the WRONG axis's verdict; see
    ``_is_safe_token``'s own duplication rationale above for why a small,
    security-relevant/axis-relevant helper stays locally auditable in each
    producing module rather than cross-module-coupled). The subject segment
    carries BOTH name and version for the same reason ``vuln.py``'s copy
    does: two components sharing a name but differing by version must not
    collide onto one finding id."""
    version_segment = (
        _sanitize_id_segment(component.version)
        if component.version
        else "unspecified"
    )
    return Finding(
        id=(
            f"indeterminate:{reason}:"
            f"{_sanitize_id_segment(component.name)}@{version_segment}"
        ),
        axis=AXIS_HYGIENE,
        message=message,
        subject=component.name,
        severity=None,
    )


def unsafe_identity_finding(component: Component) -> Finding:
    """One finding per NFR-S6-excluded component (Fix 6, 2026-07-16): its
    resolved pypi identity failed the safe-token purity guard and was never
    written into the synthesized deptry front-door input.
    ``DeptryEngine.run`` previously discarded ``SynthesizedInput.excluded``
    entirely for this front-door, so such a component just vanished from the
    hygiene axis's input with zero surfaced record — unlike
    ``vuln.unsafe_identity_finding``, which ``OsvEngine.run`` always turns
    into a finding for its own (parallel-shaped) exclusion list.

    The reason segment is ``unsafe-identity-hygiene`` — deliberately NOT the
    vuln-axis counterpart's ``unsafe-identity`` (fixed 2026-07-16): a
    component excluded by BOTH front-doors would otherwise mint two findings
    with the IDENTICAL id on different axes, and ``DefaultPolicy.evaluate``'s
    id-keyed engine-vs-engine dedupe (first registration wins) silently
    dropped the vulnerability-axis record — destroying exactly the per-axis
    attribution this module's duplicated helpers exist to protect (verified
    live). A distinct id family keeps both axes' exclusion records and rung
    drivers alive; ``hygiene_rung`` still degrades the unknown code to
    ``indeterminate`` identically."""
    return _indeterminate_finding(
        "unsafe-identity-hygiene",
        component,
        f"{component.name}: excluded from the deptry front-door input — its "
        "resolved pypi identity is not a safely-writable requirements line "
        "(NFR-S6 safe-token purity guard / PEP 508 requirement grammar)",
    )


def no_identity_hygiene_finding(component: Component) -> Finding:
    """Hygiene-covered component with no ``pypi_identity`` (AUD-WARDEN-018).

    Previously dropped by a silent ``continue`` into neither ``lines`` nor
    ``excluded``, so coverage over-claimed. Surfaces as indeterminate on the
    hygiene axis with a distinct reason token so it never collides with
    ``unsafe-identity-hygiene`` or DefaultPolicy's ``uncovered``.
    """
    return _indeterminate_finding(
        "no-identity-hygiene",
        component,
        f"{component.name}: hygiene-covered but has no resolved pypi "
        "identity — cannot synthesize a deptry front-door line",
    )


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
