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
not provisioned), ``MRS-SPIN-003`` (NO harness process was started and none
can have been -- shared by ``spin``'s detached launch, ``run_foreground``'s
synchronous one and ``attach``'s exec failing to launch, AND by
``run_spin``'s two pre-spawn filesystem setup failures, which abort before
``HarnessPort.spin`` is called; see ``core/findings.py`` for why one code
serves them all), and ``MRS-SPIN-005`` (the story feed is missing or
unparseable)
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
``Verdict.UNEVALUABLE``) -- no new code was needed for that scenario.
Story 3.4's ``cli/spin.py`` (the supervisor's own process lifecycle,
AD-9/AD-20/AD-25) adds ``MRS-SPIN-007`` (the supervisor sidecar's
``ProcessPort.spawn_detached`` raised ``ProcessError`` after the harness
itself already launched successfully) -- classified ``Verdict.WARN``, the
same tier as ``MRS-SPIN-006`` and for the same reason: a live,
already-launched process is never re-classified as a failure over a
paper-trail gap, here the absence of a supervisor rather than a missing
outcome entry. Story 3.5's ``supervisor/__main__.py`` (idle-strand
detection, AD-9/AD-20) adds a NEW area, ``MRS-SUPV-*``: ``MRS-SUPV-001``
(the idle ladder's ``nudge`` rung could not deliver its text --
``SessionObserverPort.send_text`` returned ``False``), ``MRS-SUPV-002``
(the ``stop-and-retry`` rung's ``HarnessPort.stop``/``.resume`` call raised
``HarnessError``), and ``MRS-SUPV-003`` (the run-launch outcome entry's
``harness_run_id`` is unavailable, so the ladder cannot act at all for this
run). All three classify ``Verdict.WARN``, the same tier as
``MRS-SPIN-004``/``006``/``007`` and for the identical reason: each names a
degraded-but-still-supervised condition, never a failure that invalidates
the run itself. Story 3.6 (budget ceilings, AD-20/AD-32) adds THREE more
codes to the same area: ``MRS-SUPV-004`` (a budget ceiling transitioned
``NONE``->``APPROACHING``), ``MRS-SUPV-005`` (a budget ceiling BREACHED and
the terminal stop call failed or had no ``harness_run_id`` to target), and
``MRS-SUPV-006`` (a token-ceiling usage sample is ``stale-evidence`` --
AD-32's own F-24 amendment: never ``unevaluable``). All three classify
``Verdict.WARN`` too, for the identical reason the story's own
``MRS-SUPV-001/002/003`` already do. The same story adds ``MRS-SPIN-009``
(FR-14's non-blocking preflight advisory) at that same ``Verdict.WARN``
tier, alongside ``MRS-SPIN-004/006/007/008``. Story 3.7 (escalation,
deferral, and resume, AD-9/AD-34/AD-45) adds ``MRS-SUPV-007`` (the
mandatory escalation file-marker write failed) to the same ``Verdict.WARN``
tier as this area's own 001-006: the escalation was detected and journaled
regardless, so only the durable marker's own write failed -- a degraded-
but-still-supervised condition, never a failure that invalidates the
detach. The same story adds ``MRS-SPIN-010`` (``marshal factory resume``
refused: a live ``run_status_snapshot`` read classified the paused
escalation ``EscalationStatus.UNRESOLVED``) and ``MRS-SPIN-011`` (``marshal
factory resume`` refused: no resumable run) to ``cli/spin.py``'s own area,
both classified ``Verdict.ERROR`` -- the same tier as ``MRS-SPIN-002/003/
005``: a real refusal gate ran and blocked the resume BEFORE any spawn,
never a degraded-but-proceeding launch (unlike ``MRS-SPIN-004/006/007/008/
009``, which all describe an ALREADY-launched process). Review finding
(pass 1): the same caller adds ``MRS-SPIN-012`` (the resume refusal gate's
own live ``run_status_snapshot`` read returned ``None`` -- an unconfirmed,
not a positively-cleared, escalation status) at ``Verdict.WARN`` -- the
gate proceeds rather than refuses on mere ambiguity (refusing every resume
on a transient read hiccup would make the ordinary, never-escalated case
newly unreliable), so this is a degraded-but-proceeding condition, the
same tier as ``MRS-SPIN-004/006/007/008/009``, never the refusal tier its
two siblings above use. Story 3.8 (stage-bound durability and fleet-launch
wiring, AD-46) adds ``MRS-SUPV-008`` (a durability push failed) to the same
``Verdict.WARN`` tier as this area's own 001-007: AD-46's own "best-effort
against transient network conditions, never a new refusal gate" -- a
failed push never invalidates the run's own supervision. Story 2.3
(frozen-surface scope check, narrowing only, AD-4/AD-26/AD-27) adds
``MRS-GATE-007``/``008``, this table's FIRST classifications into
``Verdict.SCOPE_VIOLATION`` -- reserved in the lattice since Story 1.1 but
never actually produced by any real code until now: a changed path outside
the computed effective surface, or one touching the live frozen set, is a
real, determinable scope violation, distinct from ``GATE_FAILED`` (a
configured check that ran and failed) and from ``UNEVALUABLE`` (Marshal
could not determine an answer at all). The same story adds
``MRS-GATE-009`` (``--scope-check`` could not be evaluated at all) at
``Verdict.UNEVALUABLE``, the same tier as ``MRS-GATE-002``/``003``/``005``.
Story 4.1 (story-spec promotion, AD-13/AD-24/AD-29/AD-33) adds a NEW area,
``MRS-DEPLOY-*``: ``MRS-DEPLOY-001`` (a durable story has no Tier-3 spec to
promote) and ``MRS-DEPLOY-002`` (a durable story's Tier-3 spec fails the
minimal parse, so it is not promoted over a possibly-good existing copy)
classify ``Verdict.WARN`` -- the same tier as every other paper-trail gap
this codebase already treats as reported-but-non-blocking
(``MRS-POLICY-005``, ``MRS-PREFLIGHT-011``, ``MRS-GATE-004``, AD-21's own
F-17 unclosed-``intent`` precedent): named so it is never passed over
silently, but never itself failing the whole run when other candidates
promote cleanly. ``MRS-DEPLOY-003`` (``VcsPort.commit_subjects`` could not
read local ``main``'s commit history, or the promotion write path --
copying a spec's bytes or ``VcsPort.commit_paths``'s stage-and-commit --
failed) classifies ``Verdict.UNEVALUABLE``: Marshal could not positively
confirm this run's promotion, the same "could not determine" tier as
``MRS-GATE-002``/``003``/``005``/``009`` -- AD-31 forbids classifying the
SAME code two different ways depending on which of its two emit sites
fired, so both fold into this one rung rather than splitting into an
untested ERROR-tier sibling for the write-path case. Story 2.7 (a gate
binds to the spec's Success signal, AD-4/AD-31/AD-49) adds ``MRS-GATE-010``
(``core.gate.check_spec_binding`` was given ``declared_commands is None``
-- no tracked spec, or its Success signal could not be parsed) and
``MRS-GATE-011`` (a spec-declared verify command is no longer among the
policy's own ``verify_commands``) -- both classify ``Verdict.
SCOPE_VIOLATION``, the SAME rung as ``MRS-GATE-007``/``008``: AD-49 states
plainly that "an untraceable or mismatched binding cannot itself be waived
to green", the identical closed-lattice reasoning already governing this
codebase's other ``SCOPE_VIOLATION`` codes. Story 4.2 (teardown
reachability and spec-recovery assistance, AD-27/AD-29) adds
``MRS-TEARDOWN-004`` (an unreachable-promotion refusal met with ``--force``
but no, or a mismatched, ``--abandon`` set) at ``Verdict.ERROR`` -- the
same tier as ``MRS-TEARDOWN-003``: a real refusal gate ran and the
operator's own override attempt did not satisfy it, never "could not
evaluate". ``MRS-DEPLOY-004`` (``deploy recover-spec`` found a genuinely
orphaned key -- no Tier-3 snapshot, no ``epics.md`` section) classifies
``Verdict.WARN``, the same tier as ``MRS-DEPLOY-001``/``002``: a
paper-trail gap reported for the operator's attention, never itself a
failed operation.
Code review (2026-08-06, P1) adds ``MRS-TEARDOWN-005`` (the AD-29
reachability check itself could not run -- local ``main``'s commit history
was unreadable, ``MRS-DEPLOY-003``) at ``Verdict.ERROR``, the SAME tier as
``MRS-TEARDOWN-003``/``004`` -- deliberately NOT ``UNEVALUABLE`` (the tier
``MRS-DEPLOY-003`` itself uses): an UNDETERMINED reachability answer must
refuse teardown AT LEAST as strictly as a real non-empty unreachable set,
never more loosely.
Code review (2026-08-06, P5) adds ``MRS-DEPLOY-005`` (``deploy
recover-spec``'s epics-derived fallback wrote a recovered spec whose Intent
and/or Acceptance Criteria section came back empty) at ``Verdict.WARN``,
the same tier as ``MRS-DEPLOY-001``/``002``/``004``.
Later stories populate the table further as they add real codes. The mechanism (a total, fail-loud
lookup) is separately proven via ``monkeypatch``-injected synthetic entries
in ``tests/unit/test_verdict.py``.

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
# Story 3.4's cli/spin.py adds a SEVENTH code to the same caller,
# MRS-SPIN-007, at the same WARN tier as MRS-SPIN-006.
# Story 3.5's supervisor/__main__.py adds a NEW area, MRS-SUPV-* (three
# codes), all classified WARN alongside MRS-SPIN-004/006/007, and cli/spin.py
# gains MRS-SPIN-008 (project-policy findings raised while resolving the
# supervisor's idle threshold) at that same WARN tier -- see core/findings.py
# for why those findings must NOT keep MRS-POLICY-*'s own UNEVALUABLE tier
# when they surface from an already-successful launch.
# Story 3.6's supervisor/__main__.py adds MRS-SUPV-004/005/006 (budget-warn,
# budget-stop failure, stale usage evidence) to the same area, all WARN, and
# cli/spin.py gains MRS-SPIN-009 (FR-14's preflight advisory), also WARN.
# Story 3.7's supervisor/__main__.py adds MRS-SUPV-007 (escalation
# file-marker write failure) to the same area, WARN; cli/spin.py gains
# MRS-SPIN-010/011 (resume refused: unresolved escalation / no resumable
# run), both ERROR, plus MRS-SPIN-012 (the live status read failed, so the
# escalation gate confirmed nothing and resume proceeds anyway) -- WARN, not
# ERROR, for AD-32's own reason: an unreadable sample is ambiguity, and
# refusing on it would make the ordinary, never-escalated resume newly
# unreliable.
# Story 3.8's supervisor/__main__.py adds MRS-SUPV-008 (a durability push
# failed), WARN, alongside this area's own 001-007.
# Story 2.3's cli/gate.py/core/gate.py add MRS-GATE-007/008 at
# SCOPE_VIOLATION (this table's first use of that rung) and MRS-GATE-009
# at UNEVALUABLE, alongside MRS-GATE-002/003/005.
# Story 4.1's cli/deploy.py/core/promotion.py add a NEW area, MRS-DEPLOY-*:
# 001/002 (missing/invalid Tier-3 spec for a durable story) at WARN,
# 003 (commit-history-read or promotion-write failure) at UNEVALUABLE.
# Story 2.7's cli/gate.py/core/gate.py add MRS-GATE-010/011 (missing/
# unparseable spec-binding Success signal; a declared command narrowed or
# removed from policy) at SCOPE_VIOLATION, alongside MRS-GATE-007/008.
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
    "MRS-SPIN-007": Verdict.WARN,
    "MRS-SPIN-008": Verdict.WARN,
    "MRS-SPIN-009": Verdict.WARN,
    "MRS-SUPV-001": Verdict.WARN,
    "MRS-SUPV-002": Verdict.WARN,
    "MRS-SUPV-003": Verdict.WARN,
    "MRS-SUPV-004": Verdict.WARN,
    "MRS-SUPV-005": Verdict.WARN,
    "MRS-SUPV-006": Verdict.WARN,
    "MRS-SUPV-007": Verdict.WARN,
    "MRS-SPIN-010": Verdict.ERROR,
    "MRS-SPIN-011": Verdict.ERROR,
    "MRS-SPIN-012": Verdict.WARN,
    "MRS-SUPV-008": Verdict.WARN,
    "MRS-GATE-007": Verdict.SCOPE_VIOLATION,
    "MRS-GATE-008": Verdict.SCOPE_VIOLATION,
    "MRS-GATE-009": Verdict.UNEVALUABLE,
    "MRS-DEPLOY-001": Verdict.WARN,
    "MRS-DEPLOY-002": Verdict.WARN,
    "MRS-DEPLOY-003": Verdict.UNEVALUABLE,
    "MRS-GATE-010": Verdict.SCOPE_VIOLATION,
    "MRS-GATE-011": Verdict.SCOPE_VIOLATION,
    "MRS-TEARDOWN-004": Verdict.ERROR,
    "MRS-DEPLOY-004": Verdict.WARN,
    "MRS-TEARDOWN-005": Verdict.ERROR,
    "MRS-DEPLOY-005": Verdict.WARN,
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
