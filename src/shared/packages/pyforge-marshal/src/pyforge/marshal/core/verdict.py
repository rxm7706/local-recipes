"""Sole owner of Marshal's verdict lattice + exit-code projection (Story
1.1, architecture spine AD-7/AD-31).

Lattice order (fixed, strongest first): ``error > gate-failed >
scope-violation > unevaluable > warn > clean`` (AD-7). Exit-code assignment
(recorded assumption, not architecture-dictated -- see the spec's Design
Notes: architecture pins only ``clean -> 0``, and PRD FR-19 requires "a
distinct code for could not evaluate"; neither source gives the other 3
numbers). Chosen, monotonic with lattice strength: ``warn=0`` (AD-31's own
reasoning for why ``warn`` is a distinct rung from ``unevaluable`` only
holds if ``warn`` exits 0, matching both ``pyforge-warden``'s and
``pyforge-doctor``'s existing exit-0 treatment of ``warn``),
``unevaluable=1``, ``scope-violation=2``, ``gate-failed=3``, ``error=4``.
``EXIT_SIGINT = 130``, ``EXIT_OK = 0``, and ``EXIT_USAGE = 2`` are
CLI-boundary constants, not lattice rungs; ``GUARDED_EXIT_CODES`` is the
computed frozen domain. AD-7 makes this module the only one permitted to
embed a literal from that domain -- every other module (the CLI included)
imports these names instead of spelling the integers.

``classify()`` is the SOLE owner of finding-code -> lattice-member
classification (AD-31): no other module assigns a verdict directly.
``_CLASSIFY_TABLE`` shipped Story 1.1 empty for the same reason ``findings.
REGISTERED_CODES`` did -- no command in that story emitted a real finding.
Story 1.2's two real codes (``MRS-IDENT-001``/``MRS-IDENT-002``, from
``core/identity.py``) are its first real entries, both classified
``Verdict.UNEVALUABLE`` -- a malformed key or non-conforming merge subject
means the reference could not be evaluated, not that anything failed a
gate. Story 1.3's real codes (``MRS-POLICY-001/002/003/004/006``, from
``core/policy.py``/``cli/config.py``) classify ``Verdict.UNEVALUABLE`` for the
same reason: an unknown policy key, a malformed field value, a malformed
project slug, or a CLI-boundary I/O failure resolving/writing policy means
Marshal cannot determine operator intent or complete the requested
operation, not that a gate failed. ``MRS-POLICY-005`` (no project slug
supplied) classifies ``Verdict.WARN`` -- a bare no-active-project
``marshal config`` is a legitimate show-me-the-defaults invocation, so it
stays in the exit-0 half of the lattice while still surfacing that the
project-derived seed path was omitted. Story 1.4's real codes
(``MRS-INIT-001/002``, from ``cli/init.py``) classify ``Verdict.UNEVALUABLE``
for the same reason as their ``core/policy.py`` counterparts: a malformed
slug or an unknown project means Marshal cannot determine what to
provision, not that a gate failed. ``MRS-INIT-003``/``MRS-INIT-004``
classify ``Verdict.ERROR``: a marker/symlink desync or a failed
``git``/filesystem operation means a real provisioning step was attempted
(or correctly refused) and did not converge, a stronger failure than
"could not evaluate". Story 1.5's ``MRS-INIT-005`` (``cli/init.py``'s
``tier3_backlink`` step) classifies ``Verdict.ERROR`` too, the same tier as
its two predecessors: a real, non-empty local Tier-3 directory is a real
provisioning step correctly refused, not "could not evaluate". Story 1.6's
``cli/init.py::run_homes`` (``marshal homes``) adds ``MRS-HOMES-001`` (a
home's or the main checkout's marker/symlink/branch-derived-slug agreement
check failed), ``MRS-HOMES-002`` (a home's Tier-3 backlink realpath does not
match its canonical store), and ``MRS-HOMES-003`` (a ``git``/filesystem
operation failed while gathering state) -- all three classify
``Verdict.ERROR``, the same tier as ``MRS-INIT-003/004/005``: a real
isolation check ran and found (or could not complete) a real violation, not
"could not evaluate". Story 1.7's ``cli/init.py::run_preflight``
(``marshal preflight``) adds ``MRS-PREFLIGHT-001`` through
``MRS-PREFLIGHT-009`` -- all nine classify ``Verdict.ERROR`` too: every one
is a real prerequisite check that ran (the harness binary, its version, the
multiplexer, the adapter, the story feed, each verify command, the
single-checkout invariant, seed-file copying, first-run acknowledgement, or
the loop home's own existence) and found a real gap, never "could not
evaluate" -- same tier as every code this story's siblings registered.
``MRS-PREFLIGHT-010`` (a malformed slug, checked before any I/O) classifies
``Verdict.UNEVALUABLE`` instead, the same tier as its ``MRS-INIT-001``
counterpart: Marshal cannot determine what to preflight, not that a gate
failed. Later
stories populate the table
further as they add real codes. The mechanism (a total, fail-loud lookup) is
separately proven via ``monkeypatch``-injected synthetic entries in
``tests/unit/test_verdict.py``.

Every other module *feeds* findings; only this module *projects* them to a
verdict and an exit code -- enforced by the sole-ownership meta-test
(``tests/meta/test_ad7_verdict_sole_ownership.py``, adapted from
``pyforge-warden``'s sibling guard).
"""

from __future__ import annotations

from collections.abc import Iterable

from .findings import require_registered
from .model import Finding, Verdict

LATTICE_ORDER: tuple[Verdict, ...] = (
    Verdict.ERROR,
    Verdict.GATE_FAILED,
    Verdict.SCOPE_VIOLATION,
    Verdict.UNEVALUABLE,
    Verdict.WARN,
    Verdict.CLEAN,
)

_RANK: dict[Verdict, int] = {verdict: rank for rank, verdict in enumerate(LATTICE_ORDER)}

EXIT_SIGINT = 130

_EXIT_BY_VERDICT: dict[Verdict, int] = {
    Verdict.CLEAN: 0,
    Verdict.WARN: 0,
    Verdict.UNEVALUABLE: 1,
    Verdict.SCOPE_VIOLATION: 2,
    Verdict.GATE_FAILED: 3,
    Verdict.ERROR: 4,
}

# CLI-boundary constants (like EXIT_SIGINT above, not lattice rungs).
# EXIT_USAGE is argparse's usage-error convention; it numerically coincides
# with scope-violation's exit code but is a distinct concern.
EXIT_OK = 0
EXIT_USAGE = 2

# The full frozen exit-code domain (AD-7), computed -- never re-spelled --
# from the lattice projection plus the boundary constants.
GUARDED_EXIT_CODES: frozenset[int] = frozenset(_EXIT_BY_VERDICT.values()) | {
    EXIT_OK,
    EXIT_USAGE,
    EXIT_SIGINT,
}

# Story 1.2's core/identity.py -- the table's first real classifications.
# Story 1.3's core/policy.py/cli/config.py add the second real caller's six codes.
# Story 1.4's cli/init.py adds the third real caller's four codes.
# Story 1.5's cli/init.py tier3_backlink step adds a fifth code.
# Story 1.6's cli/init.py::run_homes adds the fourth real caller's three codes.
# Story 1.7's cli/init.py::run_preflight adds the fifth real caller's ten codes.
_CLASSIFY_TABLE: dict[str, Verdict] = {
    "MRS-IDENT-001": Verdict.UNEVALUABLE,
    "MRS-IDENT-002": Verdict.UNEVALUABLE,
    "MRS-POLICY-001": Verdict.UNEVALUABLE,
    "MRS-POLICY-002": Verdict.UNEVALUABLE,
    "MRS-POLICY-003": Verdict.UNEVALUABLE,
    "MRS-POLICY-004": Verdict.UNEVALUABLE,
    "MRS-POLICY-005": Verdict.WARN,
    "MRS-POLICY-006": Verdict.UNEVALUABLE,
    "MRS-INIT-001": Verdict.UNEVALUABLE,
    "MRS-INIT-002": Verdict.UNEVALUABLE,
    "MRS-INIT-003": Verdict.ERROR,
    "MRS-INIT-004": Verdict.ERROR,
    "MRS-INIT-005": Verdict.ERROR,
    "MRS-HOMES-001": Verdict.ERROR,
    "MRS-HOMES-002": Verdict.ERROR,
    "MRS-HOMES-003": Verdict.ERROR,
    "MRS-PREFLIGHT-001": Verdict.ERROR,
    "MRS-PREFLIGHT-002": Verdict.ERROR,
    "MRS-PREFLIGHT-003": Verdict.ERROR,
    "MRS-PREFLIGHT-004": Verdict.ERROR,
    "MRS-PREFLIGHT-005": Verdict.ERROR,
    "MRS-PREFLIGHT-006": Verdict.ERROR,
    "MRS-PREFLIGHT-007": Verdict.ERROR,
    "MRS-PREFLIGHT-008": Verdict.ERROR,
    "MRS-PREFLIGHT-009": Verdict.ERROR,
    "MRS-PREFLIGHT-010": Verdict.UNEVALUABLE,
}


def classify(code: str) -> Verdict:
    """Total classification: a registered finding ``code`` -> its lattice
    member (AD-31). ``code`` must first pass ``require_registered`` (raises
    ``UnregisteredFindingCodeError`` for a malformed/unregistered code); a
    registered code absent from ``_CLASSIFY_TABLE`` raises ``ValueError``
    naming the gap -- ``classify`` is meant to be total over every
    registered code, so a miss is a real registration bug, never a silent
    default."""
    require_registered(code)
    try:
        return _CLASSIFY_TABLE[code]
    except KeyError as exc:
        raise ValueError(
            f"finding code {code!r} is registered but has no lattice "
            "classification in _CLASSIFY_TABLE"
        ) from exc


def compute_verdict(
    findings: Iterable[Finding], *, floor: Verdict = Verdict.CLEAN
) -> Verdict:
    """The verdict for a command: the maximum (strongest, per
    ``LATTICE_ORDER``) over every emitted finding's classification, plus a
    command-declared ``floor`` (AD-31). Empty ``findings`` returns ``floor``
    unchanged -- the defined empty-input behavior. ``floor`` is coerced via
    ``Verdict(floor)`` -- like ``exit_code_for``, this function is total and
    never silently returns an unregistered/invalid value."""
    winner = Verdict(floor)
    for finding in findings:
        # Same member-strictness as Envelope.__post_init__: a non-Finding
        # element is this module's fail-loud ValueError, not a raw
        # AttributeError from deep inside the loop.
        if not isinstance(finding, Finding):
            raise ValueError(
                f"findings must contain only Finding instances, got {finding!r}"
            )
        candidate = classify(finding.code)
        if _RANK[candidate] < _RANK[winner]:
            winner = candidate
    return winner


def exit_code_for(verdict: Verdict | str) -> int:
    """Project a ``Verdict`` to its process exit code -- TOTAL over the
    closed 6-member lattice (AD-7). ``EXIT_SIGINT`` is never produced here;
    it lives at the CLI boundary."""
    return _EXIT_BY_VERDICT[Verdict(verdict)]
