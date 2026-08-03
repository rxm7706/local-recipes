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
failed. Story 1.8's ``cli/init.py::run_teardown`` (``marshal teardown``)
adds ``MRS-TEARDOWN-001`` (a malformed slug, checked before any I/O),
classified ``Verdict.UNEVALUABLE`` for the same reason as its
``MRS-INIT-001``/``MRS-PREFLIGHT-010`` counterparts, plus
``MRS-TEARDOWN-002`` (a git operation failed, including resolving the
current working directory or the loop-home root) and ``MRS-TEARDOWN-003``
(refused: uncommitted changes, a genuinely unmerged branch, or an
unreachable promotion, and ``--force`` was not supplied) -- both classify
``Verdict.ERROR``, the same tier as every sibling story's
real-operation-attempted-or-correctly-refused codes: a real teardown was
attempted and either failed or was correctly blocked, never "could not
evaluate". Story 1.9's ``cli/init.py::run_preflight`` (packaging,
FR-52/FR-57) graduates the harness-version check into two tiers and adds
``MRS-PREFLIGHT-011`` (a resolvable, same-major harness version outside
the declared minor range) classified ``Verdict.WARN`` -- a legitimate,
non-blocking heads-up, the same reasoning as ``MRS-POLICY-005``'s own
``Verdict.WARN`` tier, and distinct from ``MRS-PREFLIGHT-002`` (unchanged:
``harness_version is None`` or a genuine major-version mismatch), which
stays ``Verdict.ERROR``. Story 2.1's ``cli/gate.py``/``core/gate.py``
(``marshal gate evaluate``, FR-20) add five more codes. ``MRS-GATE-001`` (a
configured verify command ran and exited non-zero) classifies
``Verdict.GATE_FAILED`` -- this table's FIRST classification into that
rung: a REAL check ran and failed, the lattice's own dedicated "a gate
failed" tier, distinct from every ``Verdict.ERROR``-tier code before it
(those are all "an internal Marshal operation failed", never "a project's
own gate failed"); matches Story 2.2's own AC text that a failing verify
command is this exact rung. ``MRS-GATE-002`` (the command's executable
could not be launched at all) and ``MRS-GATE-003`` (the command's string
could not be ``shlex.split``) classify ``Verdict.UNEVALUABLE`` -- Marshal
could not run the check at all, matching Story 2.2's own AC text: "a
missing verify command ... produces unevaluable". ``MRS-GATE-005`` (``--run
<id>`` supplied with no run-journal fold available yet) classifies
``Verdict.UNEVALUABLE`` too, for the same reason: the requested run-scoped
answer could not be produced. ``MRS-GATE-004`` (``verify_commands``
composed to the empty tuple) classifies ``Verdict.WARN``, the same tier as
``MRS-POLICY-005``/``MRS-PREFLIGHT-011`` -- see ``core/gate.py``'s own
``no_commands_configured_finding`` docstring for why a brand-new project's
own ``DEFAULT_POLICY`` value must not read as a blocking failure. Story
2.4's ``core/gate.py::classify_doc_only_declaration`` adds ``MRS-GATE-006``
(no worktree changes AND the story was not declared doc-only) --
classifies ``Verdict.GATE_FAILED``, the same tier as ``MRS-GATE-001``: a
real, determinable outcome ("no change, not declared doc-only" is
something Marshal evaluated and found, not something it could not
evaluate). Story 3.2's ``core/journal.py::fold`` adds ``MRS-JOURNAL-001``
(an unparseable/invalid journal line) and ``MRS-JOURNAL-002`` (a missing
or invalid-JSON sidecar blob) -- both classify ``Verdict.UNEVALUABLE``,
the same tier as every other "Marshal could not determine the answer"
code: a quarantined line's own story key and decision domain could not be
evaluated, never a gate that failed. Story 3.3's ``cli/spin.py`` (``marshal
factory spin``/``attach``, FR-9/FR-17) adds six more codes.
``MRS-SPIN-001`` (a malformed project slug, checked before any I/O)
classifies ``Verdict.UNEVALUABLE``, the same tier as every sibling pre-I/O
shape gate (``MRS-INIT-001``/``MRS-PREFLIGHT-010``/``MRS-TEARDOWN-001``):
Marshal cannot determine what to launch. ``MRS-SPIN-002`` (the loop home is
not provisioned), ``MRS-SPIN-003`` (the harness process could not be
launched at all -- shared by ``spin``'s detached launch, ``run_foreground``'s
synchronous one, and ``attach``'s exec, all the same underlying failure
mode), and ``MRS-SPIN-005`` (the story feed is missing or unparseable)
classify ``Verdict.ERROR``, the same tier as every other
real-precondition-checked-and-failed code. ``MRS-SPIN-004`` (the harness's
own self-minted ``harness_run_id`` could not be recovered within the
bounded poll window -- the detached spawn itself already succeeded) and
``MRS-SPIN-006`` (the detached spawn itself succeeded, but its ``outcome``
entry could not be journaled -- distinct from ``MRS-SPIN-003``'s "never
launched" tier, review finding: reusing 003 there conflated "safe to
retry" with "a live, unaccounted-for process") classify ``Verdict.WARN``,
the same tier as ``MRS-POLICY-005``/``MRS-PREFLIGHT-011``/``MRS-GATE-004`` --
and, for ``006`` specifically, matching AD-21's amendment (F-17) for a lone
unclosed journal ``intent`` generally: a launch that already succeeded is
never re-classified as a failure over a paper-trail gap. A malformed raw
feed key surfaces via the EXISTING ``MRS-IDENT-001`` (already
``Verdict.UNEVALUABLE``) -- no new code was needed for that scenario. Later
stories populate the table further as they add real codes. The mechanism (a
total, fail-loud lookup) is separately proven via ``monkeypatch``-injected
synthetic entries in ``tests/unit/test_verdict.py``.

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

# The codes `relay_exit_code` lets through from a RELAYED child process --
# deliberately a strict subset of GUARDED_EXIT_CODES (which is what a
# HANDLER may return, a different question). Only these three carry the same
# meaning whether Marshal or a child process produced them: success,
# "could not be evaluated", and interrupted-by-SIGINT. The rest of the
# admitted domain (EXIT_USAGE, and the SCOPE_VIOLATION/GATE_FAILED rungs)
# names a judgment Marshal itself makes -- relaying a child's coincidental
# 2/3/4 would assert one Marshal never evaluated. See `relay_exit_code`.
_RELAY_PASSTHROUGH: frozenset[int] = frozenset(
    {EXIT_OK, _EXIT_BY_VERDICT[Verdict.UNEVALUABLE], EXIT_SIGINT}
)

# Story 1.2's core/identity.py -- the table's first real classifications.
# Story 1.3's core/policy.py/cli/config.py add the second real caller's six codes.
# Story 1.4's cli/init.py adds the third real caller's four codes.
# Story 1.5's cli/init.py tier3_backlink step adds a fifth code.
# Story 1.6's cli/init.py::run_homes adds the fourth real caller's three codes.
# Story 1.7's cli/init.py::run_preflight adds the fifth real caller's ten codes.
# Story 1.8's cli/init.py::run_teardown adds the sixth real caller's three codes.
# Story 1.9's cli/init.py::run_preflight adds an eleventh code, graduating
# the harness-version check into two tiers.
# Story 2.1's cli/gate.py/core/gate.py add the seventh real caller's five
# codes -- MRS-GATE-001 is the table's first GATE_FAILED classification.
# Story 2.4's core/gate.py::classify_doc_only_declaration adds MRS-GATE-006,
# joining MRS-GATE-001 at GATE_FAILED.
# Story 3.2's core/journal.py::fold adds MRS-JOURNAL-001/002, both UNEVALUABLE.
# Story 3.3's cli/spin.py adds the ninth real caller's SIX codes (MRS-SPIN-006
# joined 001-005 in review, splitting "launched but its outcome could not be
# journaled" off MRS-SPIN-003's "never launched, safe to retry").
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
    "MRS-PREFLIGHT-011": Verdict.WARN,
    "MRS-TEARDOWN-001": Verdict.UNEVALUABLE,
    "MRS-TEARDOWN-002": Verdict.ERROR,
    "MRS-TEARDOWN-003": Verdict.ERROR,
    "MRS-GATE-001": Verdict.GATE_FAILED,
    "MRS-GATE-002": Verdict.UNEVALUABLE,
    "MRS-GATE-003": Verdict.UNEVALUABLE,
    "MRS-GATE-004": Verdict.WARN,
    "MRS-GATE-005": Verdict.UNEVALUABLE,
    "MRS-GATE-006": Verdict.GATE_FAILED,
    "MRS-JOURNAL-001": Verdict.UNEVALUABLE,
    "MRS-JOURNAL-002": Verdict.UNEVALUABLE,
    "MRS-SPIN-001": Verdict.UNEVALUABLE,
    "MRS-SPIN-002": Verdict.ERROR,
    "MRS-SPIN-003": Verdict.ERROR,
    "MRS-SPIN-004": Verdict.WARN,
    "MRS-SPIN-005": Verdict.ERROR,
    "MRS-SPIN-006": Verdict.WARN,
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


def relay_exit_code(child_code: int) -> int:
    """Project a RELAYED child process's exit code into the frozen domain
    (AD-7) -- for the handlers that hand a terminal to another process and
    report its result instead of an ``Envelope``'s (Story 3.3's
    ``marshal factory spin --foreground`` and ``marshal factory attach``).

    Review finding (Blind Hunter + Edge Case Hunter, both verified live):
    those two handlers returned the child's raw code, but ``cli/main.py``
    admits only ``GUARDED_EXIT_CODES`` from a handler and clamps everything
    else to ``EXIT_USAGE`` as an "internal wiring bug" -- so a child exiting
    5/7/137/143 surfaced as ``2``, which in THIS package's own lattice reads
    as scope-violation/usage, not as the harness failing. That also silently
    voided ``BmadLoopHarness._normalize_returncode``: its ``128 + N`` signal
    convention lands outside the domain for every signal except ``SIGINT``
    (``130``), so a SIGTERM'd foreground run reported a usage error.

    AD-7's domain is frozen, so widening it is not the fix; making the
    projection DELIBERATE is. Exactly ``_RELAY_PASSTHROUGH`` passes through
    untouched -- ``0``, ``1``, and ``EXIT_SIGINT`` (so a Ctrl-C'd child still
    reports ``130``); anything else collapses to the ERROR rung, the honest
    statement that the relayed process failed in a way this package's own
    closed vocabulary cannot name more precisely. ``bool`` is excluded
    exactly as ``main()`` excludes it: ``True`` numerically equals ``1`` but
    is not an exit code.

    Follow-up review finding (Blind Hunter + Edge Case Hunter, both verified
    live): the first version of this fix tested membership in
    ``GUARDED_EXIT_CODES``, which is ``{0, 1, 2, 3, 4, 130}`` -- so ``2``,
    ``3`` and ``4`` ALSO passed through, reproducing the very misreport this
    function exists to prevent. A child exiting ``2`` still surfaced as
    ``EXIT_USAGE`` (a Marshal usage error it never committed), and one
    exiting ``3`` asserted the ``GATE_FAILED`` rung -- a gate verdict Marshal
    never evaluated -- from a process whose exit codes are its own, not this
    package's. ``bmad-loop attach`` in particular returns ``subprocess.call``
    of a multiplexer, an unconstrained code. The passthrough set is now
    spelled explicitly rather than borrowed from the full admitted domain,
    which made the docstring's and ``--foreground``'s ``--help`` text's own
    "0/1/130" claim factually false."""
    if isinstance(child_code, bool) or child_code not in _RELAY_PASSTHROUGH:
        return _EXIT_BY_VERDICT[Verdict.ERROR]
    return child_code
