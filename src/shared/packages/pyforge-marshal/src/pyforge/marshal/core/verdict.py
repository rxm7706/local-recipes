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
Story 4.3 (merge-subject conformance and review-cap landing, FR-27/AD-24)
adds four more ``MRS-DEPLOY-*`` codes for ``marshal deploy land-story``.
``MRS-DEPLOY-006`` (``--justification`` missing or empty, the cheap
precondition checked before any gate re-run) and ``MRS-DEPLOY-007`` (the
named story's loop-home station branch could not be resolved -- no
provisioned loop home, the branch does not exist, or the ``--since``
merge-base read failed) classify ``Verdict.UNEVALUABLE``, the same tier as
``MRS-INIT-001``/``MRS-GATE-009``: Marshal cannot determine what to land,
not that a real operation failed. ``MRS-DEPLOY-008`` (``VcsPort.
merge_branch`` raised -- a real conflict or other git failure, always AFTER
the full gate already passed) classifies ``Verdict.ERROR``, the same tier
as ``MRS-INIT-003``/``MRS-TEARDOWN-002``: a real write was attempted and
did not converge. ``MRS-DEPLOY-009`` (the post-merge conformance audit's
own ``VcsPort.commit_subjects`` read failed) classifies ``Verdict.WARN``,
the same tier as ``MRS-DEPLOY-001``/``002``/``004``/``005`` -- the landing
already succeeded by the time this check runs, so an audit that cannot
enumerate its own window is a reporting gap, never grounds to undo or
block a landing that has already happened.
Story 4.6 (deploy idempotence and reconciliation of open intents, AD-6/
AD-21/AD-28) adds a twenty-first ``MRS-DEPLOY-*`` code, ``MRS-DEPLOY-021``:
an open ``intent`` journaled by a prior, possibly-crashed invocation of
``promote``/``land-story``/``batch-pr`` has no confirming external
evidence yet. It classifies ``Verdict.WARN`` -- AD-21's own F-17 amendment
requires this explicitly: an unclosed intent must never classify
``Verdict.ERROR`` (that would make every subsequent ``deploy`` invocation
non-zero forever, breaking AD-21's exit-0 convergence property by design),
and never blocks the run it is reported on -- it is surfaced every time,
escalating it is an operator decision (``marshal audit``), never automatic.
Story 4.10 (fleet-wide branch retirement, FR-63/AD-47) adds a new area,
``MRS-RETIRE-*``: ``MRS-RETIRE-001`` (a malformed ``--project`` slug,
checked before any I/O) classifies ``Verdict.UNEVALUABLE``, the same tier
as ``MRS-INIT-001``/``MRS-SPIN-001``/``MRS-TEARDOWN-001``'s identical
pre-I/O shape gates: Marshal cannot determine what to sweep.
``MRS-RETIRE-002`` (a ``VcsCommandError`` gathering evidence for one
candidate branch, or enumerating the fleet's worktrees at all) and
``MRS-RETIRE-003`` (a ``delete_branch`` failure under ``--execute``, or a
post-deletion journal-write failure) both classify ``Verdict.WARN``, the
same tier as this codebase's every other "reported, never blocks
progression" paper-trail-gap code (``MRS-DEPLOY-021``/``022``/``023``): a
refused/failed branch is named, but the sweep continues for every other
branch and project.

Story 5.2 (per-run detail, FR-37/NFR-12) adds two more codes to
``cli/status.py``'s own ``MRS-STATUS-*`` area: ``MRS-STATUS-003`` (``--run``
supplied without ``--project`` alongside it, checked before any I/O)
classifies ``Verdict.UNEVALUABLE``, the same tier as ``MRS-INIT-001``/
``MRS-SPIN-001``/``MRS-RETIRE-001``'s identical pre-I/O shape gates.
``MRS-STATUS-004`` (a run id that does not resolve to a real run directory
for the given project) classifies ``Verdict.WARN``, the same "clean,
reportable gap" tier as ``MRS-DEPLOY-004``'s own orphaned-key precedent: a
typo'd or torn-down run id is named, never fabricated, and never blocks.

Story 5.4 (ledger-vs-git reconciliation, FR-39/FR-40) adds three more
codes to ``cli/status.py``'s own ``MRS-STATUS-*`` area. ``MRS-STATUS-005``
(the tracked ``sprint-status-ledger.yaml`` twin could not be read) and
``MRS-STATUS-007`` (main's own commit history could not be read while
gathering ``core.promotion.merged_story_keys``'s durability evidence) --
``005`` classifies ``Verdict.WARN``, alongside ``MRS-STATUS-004``'s own
"clean, reportable gap" tier (``data.discrepancies`` reports empty, never
fabricated); ``007`` classifies ``Verdict.UNEVALUABLE``, mirroring
``MRS-DEPLOY-003``'s identical "cannot honestly determine durability this
run" rationale -- a REQUIRED read, not a per-row degradation.
``MRS-STATUS-006`` (``--reconcile-ledger`` given without ``--project``,
checked before any I/O) classifies ``Verdict.UNEVALUABLE``, alongside
``MRS-STATUS-003``'s own identical pre-I/O shape-gate precedent.

Story 5.5 (durability as a reported fleet-status dimension, FR-62/AD-48)
adds two more codes to the same area, both ``Verdict.WARN``:
``MRS-STATUS-008`` (a home's own station branch carries local-only content
the ``scripts/unpushed_work_check.py`` detector confirmed is not on
origin) and ``MRS-STATUS-009`` (that detector could not be consulted this
run at all -- missing script, launch failure, its own documented
``UNKNOWN``/exit-2 case, or malformed JSON). Both are "reported, never
blocks progression", the same tier as ``MRS-STATUS-001``/``005``.

Story 6.1 (profile-driven adapter selection, project-scoped, FR-48/FR-51/
AD-19) adds two more codes to ``cli/spin.py``'s own ``MRS-SPIN-*`` area.
``MRS-SPIN-013`` (a resolved story's own declared ``difficulty:`` was
malformed -- ``core.spec_difficulty.DifficultyParseError``) classifies
``Verdict.WARN``, alongside this area's own 004/006/007/008/009/012: the
malformed story is treated as undeclared for the launch's own model
resolution (the exact same "no override" degradation an undeclared
difficulty already gets), so the gap is reported, never itself a reason to
refuse an otherwise-clean launch. ``MRS-SPIN-014`` (the loop home's own
configured adapter name could not be resolved to a real profile --
``HarnessError`` from ``HarnessPort.adapter_binary``) classifies
``Verdict.UNEVALUABLE``, the same tier as ``MRS-GATE-009``'s own "Marshal
could not evaluate this at all" reasoning -- an unresolvable adapter name
is a configuration fact Marshal cannot determine, not a real precondition
that was checked and failed (the spec's own explicit "never a crash"
wording for this exact scenario).

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
# Story 4.3's cli/deploy.py::run_land_story adds four more MRS-DEPLOY-*
# codes: 006 (missing/empty --justification) and 007 (the station branch
# could not be resolved) at UNEVALUABLE -- both mean Marshal cannot
# determine what to land, never that a real operation failed; 008 (the
# merge itself failed) at ERROR -- a real write was attempted against an
# already-green gate and did not converge; 009 (the post-merge conformance
# audit could not enumerate its own window) at WARN -- the landing already
# succeeded by this point, so an audit gap is a reporting caveat, never
# grounds to undo it.
# Code review (2026-08-06) adds three more MRS-DEPLOY-* codes: 010 (P2, the
# gate's own verdict was not EXACTLY clean) at GATE_FAILED, alongside
# MRS-GATE-001 -- FR-27 requires a fully clean gate before a manual
# landing, so a warn-tier result is refused here exactly like a real gate
# failure, stricter than status_for's ordinarily-permissive ok/error
# partition; 011 (P4, the station branch's tip could not be reconfirmed
# before merging, or had moved since the gate ran) at ERROR, alongside
# MRS-TEARDOWN-003/004/MRS-DEPLOY-008 -- a real safety refusal after an
# already-attempted operation, not "could not evaluate"; 012 (P7,
# --justification redaction failed at journal-capture time) at WARN,
# alongside MRS-DEPLOY-001/002/004/005/009 -- the landing already
# succeeded, so a lost justification is a paper-trail visibility gap.
# Story 4.4 (batch pull request with hygiene preflight, FR-29/NFR-2, AD-34)
# adds two more MRS-DEPLOY-* codes for `marshal deploy batch-pr`:
# MRS-DEPLOY-013 (a fired `required_check` landing rule was not satisfied)
# at SCOPE_VIOLATION, alongside MRS-GATE-007/008/010/011 -- a real,
# project-declared gate evaluated the change set and blocked it, before any
# PR write is attempted; MRS-DEPLOY-014 (a ForgePort/`gh` command failed --
# listing, creating, updating a PR, or applying labels) at ERROR, the same
# tier as MRS-DEPLOY-008 -- a real outbound write was attempted and did not
# complete.
# Code review (2026-08-06) adds three more MRS-DEPLOY-* codes: 015 (P1, a
# malformed landing_rules policy layer hard-refuses the whole batch-pr
# invocation before hygiene evaluation or any forge write) at ERROR,
# alongside MRS-TEARDOWN-005 -- this refusal must be at least as strict as a
# real blocking violation, never a softer UNEVALUABLE; 016 (P4, the head
# branch moved between hygiene evaluation and the PR write) at ERROR,
# alongside MRS-DEPLOY-011's identical TOCTOU shape; 017 (P5, the loop-home
# worktree's checkout does not match the head branch's resolved tip before
# changed_files is trusted) at ERROR, the same tier -- a stale/detached
# local worktree must never silently under-report the change set; 018 (P8,
# an existing PR's own base branch does not match the policy-declared
# landing_base_branch) at ERROR, the same tier -- update_pr must never be
# called against a PR targeting a different base than policy declares.
# Story 4.5 (feed refresh with truth partitioned by domain, AD-33) adds two
# more MRS-DEPLOY-* codes for `marshal deploy refresh-feed` plus a new area,
# MRS-STATUS-*: MRS-DEPLOY-019 (a `landing_resync_commands` entry could not
# be run at all -- parse failure, bare shell syntax, or a launch failure) at
# UNEVALUABLE, the same tier as MRS-GATE-002/003 -- Marshal could not run
# the configured command at all; MRS-DEPLOY-020 (a `landing_resync_commands`
# entry ran and exited non-zero) at GATE_FAILED, the same tier as
# MRS-GATE-001/MRS-DEPLOY-010 -- a real, configured command ran and failed.
# MRS-STATUS-001 (`core.status.reconcile_feed_domains`'s own reconciliation
# mismatch: a journal-claimed `commit_sha` for a story that git's own
# `merged_story_keys` does not confirm) classifies WARN, the same tier as
# this codebase's every other "reported, never blocks progression"
# paper-trail-gap code (MRS-DEPLOY-001/002/004/005/009/012) -- AD-33 forbids
# resolving the discrepancy either way; it is named so it is never passed
# over silently, but never itself invalidates the report.
# Story 4.6 (deploy idempotence and reconciliation of open intents, AD-6/
# AD-21/AD-28) adds MRS-DEPLOY-021 (an open intent from a prior deploy
# invocation has no confirming evidence yet) at WARN, per AD-21's own F-17
# amendment -- never ERROR, never blocking.
# Code review (2026-08-06, P3) adds MRS-DEPLOY-022 (the cross-run journal
# fold itself failed -- reconciliation could not be attempted this
# invocation) at WARN, the same tier as MRS-DEPLOY-021: the underlying
# action still proceeds, but the gap is reported, never silently absorbed.
# Story 4.8 (`marshal land`, FR-60/AD-40) adds a new area, MRS-LAND-*, seven
# codes. MRS-LAND-001 (the station branch could not be resolved/does not
# exist) and MRS-LAND-002 (a malformed landing_rules policy layer) classify
# ERROR, the same tier as MRS-DEPLOY-015 -- a precondition failure, refused
# before any forge call. MRS-LAND-003 (an already-landed wave's own branch
# retirement could not be confirmed through ForgePort) classifies WARN --
# reported, never blocking: the landing itself already happened.
# MRS-LAND-004 (a fired required_check resolved to a real failure, or could
# not be read at all) classifies GATE_FAILED, the same tier as
# MRS-GATE-001/MRS-DEPLOY-010/020 -- a real, negative CI signal.
# MRS-LAND-005 (a fired required_check has not concluded yet) classifies
# WARN, per AD-8's "an unevaluable/pending signal is NOT-YET-SAFE-TO-ACT,
# never silently treated as passing" -- this run refuses to merge, but a
# still-pending check is not itself a failure. MRS-LAND-006 (this run's own
# hygiene/required-check evaluation surfaced a WARN-tier finding whose code
# is not already acknowledged via cli/init.py's shared acknowledgement
# store) classifies ERROR -- escalated, and blocks the merge: no silent
# force. MRS-LAND-007 (ForgePort.merge_pr itself failed) classifies ERROR,
# the same tier as MRS-DEPLOY-008/014 -- a real, irreversible-step write was
# attempted and did not converge.
# Story 4.9 (an advisory lock serializes concurrent writes to the shared
# planning-artifacts/specs/ store, AD-42) adds MRS-DEPLOY-023 (run_promote's
# new FsPort.acquire_advisory_lock call could not acquire the lock within
# timeout_s) at WARN, the same tier as MRS-DEPLOY-021/022 -- a clean,
# re-entrant refusal, never a hard error.
# Story 4.10 (fleet-wide branch retirement, FR-63/AD-47) adds a new area,
# MRS-RETIRE-*: MRS-RETIRE-001 (a malformed --project slug) at UNEVALUABLE,
# alongside MRS-INIT-001/MRS-SPIN-001/MRS-TEARDOWN-001; MRS-RETIRE-002 (a
# VcsCommandError gathering evidence, or enumerating the fleet) and
# MRS-RETIRE-003 (a delete_branch failure under --execute, or a
# post-deletion journal-write failure) both at WARN, alongside
# MRS-DEPLOY-021/022/023 -- never blocking, the sweep continues.
# Story 5.1 (fleet-wide runtime status, FR-36/AD-5) adds MRS-STATUS-002 (a
# discovered home's most recent run journal / bmad-loop state.json could not
# be read far enough to recover a supervisor pid and a live snapshot, or the
# fleet's own list_worktrees enumeration itself failed) at WARN, the same
# "per-row/per-sweep read failure degrades cleanly" tier as MRS-RETIRE-002.
# Story 5.2 (per-run detail, FR-37/NFR-12) adds MRS-STATUS-003 (--run given
# without --project, checked before any I/O) at UNEVALUABLE, alongside
# MRS-INIT-001/MRS-SPIN-001/MRS-RETIRE-001, and MRS-STATUS-004 (a run id
# that does not resolve to a real run directory) at WARN, alongside
# MRS-DEPLOY-004's own orphaned-key precedent -- a clean, reportable gap,
# never itself a failure.
# Story 5.5 (durability as a reported fleet-status dimension, FR-62/AD-48)
# adds MRS-STATUS-008 (a home's branch carries unpushed content the
# unpushed_work_check.py detector confirmed) and MRS-STATUS-009 (that
# detector could not be consulted this run), both at WARN.
# Story 5.6 (marshal check, FR-65/AD-50) adds MRS-CHECK-001 (the detector
# registry itself could not be consulted this run) at WARN -- the same
# tier as MRS-STATUS-009's identical precedent; MRS-CHECK-002 (a detector
# reported real findings) and MRS-CHECK-003 (a registry-self-reported gap)
# both at ERROR -- a confirmed defect, not merely an unevaluated one; and
# MRS-CHECK-004 (a detector reported "unknown", could not run) at
# UNEVALUABLE, never conflated with a confirmed FINDINGS failure.
# Story 6.1's cli/spin.py adds MRS-SPIN-013 (a malformed declared
# difficulty, treated as undeclared) at WARN, alongside this area's own
# 004/006/007/008/009/012, and MRS-SPIN-014 (the configured adapter could
# not be resolved) at UNEVALUABLE, alongside MRS-GATE-009. A review pass on
# Story 6.1 added MRS-SPIN-015 (the resolved, difficulty-tiered policy could
# not be persisted to the loop home's own policy.toml) at the SAME WARN
# tier as 013/007: the harness launch is already viable, so losing the
# write degrades the run's OWN model resolution to whatever was already on
# disk -- never a reason to abort an otherwise-viable launch.
# Story 6.2's cli/adapters.py adds a new area, MRS-ADP-* (ten codes):
# 001/002 (malformed slug / loop home not provisioned) and 003 (canonical
# `.claude/skills` tree missing) at ERROR; 004 (adapter enumeration failed)
# and 005 (unsupported platform, no declared mechanism-table row) at
# UNEVALUABLE, alongside MRS-SPIN-014/MRS-GATE-009's identical "Marshal
# cannot determine" tier; 006/008 (a specific tree's create or stale-removal
# I/O failed) at ERROR, isolated per tree; 007 (a structural conflict --
# real content in the way, or a hand-repointed symlink -- refused, not
# destroyed) at WARN; 009/010 (a malformed manifest / the manifest write
# itself failed) at WARN, the SAME "degrades, never blocks" tier as
# MRS-SPIN-015.
# Story 6.3 (projection drift detection, FR-42/AD-31/AD-36) adds ONE new
# code, MRS-CONFORM-001 (link-target identity drift detected for one or
# more projected trees -- added/removed/modified, all folded into this one
# code) at ERROR, alongside MRS-ADP-003/006/008 and MRS-CHECK-002/003's
# identical "a real, attempted check found a real problem" reasoning --
# never GATE_FAILED (reserved for a PROJECT's own configured verify
# command, not Marshal's own projection-mechanism integrity) and never WARN
# (reserved for a safe refusal or a paper-trail gap that never blocks an
# otherwise-viable operation, neither of which describes a confirmed drift
# finding). `gather_conformance_findings` (`cli/adapters.py`, shared by the
# new `marshal adapters conform` verb and `marshal preflight`'s own
# additional step) reuses MRS-ADP-001/002/003/004/005/009/011 verbatim --
# same codes, same tiers, a second call site, per this table's own
# MRS-DEPLOY-003 precedent.
# Story 6.4 (adapter probe with a machine-scoped record, FR-43, AD-31/AD-34/
# AD-37) adds `cli/adapters.py::run_adapters_probe` (`marshal adapters
# probe`), reusing MRS-ADP-001/002 verbatim for its shared preconditions,
# plus four new codes. MRS-ADP-013 (a missing/blank --adapter, checked
# before any I/O) and MRS-ADP-014 (adapter_probe raised HarnessError --
# an unknown adapter or unimportable bmad_loop) both classify UNEVALUABLE,
# the same tier as MRS-STATUS-003/MRS-SPIN-014's own "Marshal cannot
# determine what to probe" precedents. MRS-ADP-015 (writing the
# machine-scoped record failed) classifies ERROR, the same tier as
# MRS-ADP-006/008's "a real write was attempted and failed" rung. MRS-ADP-016
# (a pre-existing adapter-probes.json was malformed) classifies WARN, the
# same "degrades to empty, never blocks" tier as MRS-ADP-009. `binary_
# present is False` registers NO finding at all -- `Verdict.CLEAN`, exit 0,
# the AC's own "reports unavailable and exits 0" read literally; the
# ALREADY-SHIPPED MRS-PREFLIGHT-004 (Verdict.ERROR) already covers the
# SAME real-world fact from a run-dependent call site (AD-31: the same
# code never classifies two rungs, but the same FACT may, from two
# call sites with different meanings) -- see the story's own spec.
# Story 6.5 (conformance smoke in an ephemeral home, FR-44/AD-37) adds
# `cli/adapters.py::run_adapters_smoke` (`marshal adapters smoke`), a NEW
# area (MRS-SMOKE-*) -- this verb provisions its own throwaway home rather
# than operating on an existing project's, so it does not reuse
# MRS-ADP-001/002. MRS-SMOKE-005 (a missing/blank --adapter) and
# MRS-SMOKE-001 (run_smoke raised HarnessError -- an unknown adapter or
# unimportable bmad_loop) both classify UNEVALUABLE, mirroring
# MRS-ADP-013/014's own tiers. MRS-SMOKE-002 (ephemeral-home provisioning
# failed) and MRS-SMOKE-003 (the smoke's own status is "fail", naming the
# failing stage) both classify ERROR, mirroring MRS-ADP-002/MRS-CONFORM-001.
# MRS-SMOKE-006 (writing the machine-scoped smoke record failed) classifies
# ERROR, mirroring MRS-ADP-015. MRS-SMOKE-004 (teardown failed, residue
# left behind) and MRS-SMOKE-007 (a pre-existing adapter-smoke.json was
# malformed) both classify WARN, mirroring MRS-ADP-009/016's own "degrades,
# never blocks" tier -- a teardown failure never overrides the smoke's own
# already-computed verdict. `binary_present is False` registers NO finding
# at all -- the SAME "unavailable, exits 0" tier `adapters probe` already
# established.
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
    "MRS-DEPLOY-006": Verdict.UNEVALUABLE,
    "MRS-DEPLOY-007": Verdict.UNEVALUABLE,
    "MRS-DEPLOY-008": Verdict.ERROR,
    "MRS-DEPLOY-009": Verdict.WARN,
    "MRS-DEPLOY-010": Verdict.GATE_FAILED,
    "MRS-DEPLOY-011": Verdict.ERROR,
    "MRS-DEPLOY-012": Verdict.WARN,
    "MRS-DEPLOY-013": Verdict.SCOPE_VIOLATION,
    "MRS-DEPLOY-014": Verdict.ERROR,
    "MRS-DEPLOY-015": Verdict.ERROR,
    "MRS-DEPLOY-016": Verdict.ERROR,
    "MRS-DEPLOY-017": Verdict.ERROR,
    "MRS-DEPLOY-018": Verdict.ERROR,
    "MRS-DEPLOY-019": Verdict.UNEVALUABLE,
    "MRS-DEPLOY-020": Verdict.GATE_FAILED,
    "MRS-STATUS-001": Verdict.WARN,
    "MRS-DEPLOY-021": Verdict.WARN,
    "MRS-DEPLOY-022": Verdict.WARN,
    "MRS-LAND-001": Verdict.ERROR,
    "MRS-LAND-002": Verdict.ERROR,
    "MRS-LAND-003": Verdict.WARN,
    "MRS-LAND-004": Verdict.GATE_FAILED,
    "MRS-LAND-005": Verdict.WARN,
    "MRS-LAND-006": Verdict.ERROR,
    "MRS-LAND-007": Verdict.ERROR,
    "MRS-DEPLOY-023": Verdict.WARN,
    "MRS-RETIRE-001": Verdict.UNEVALUABLE,
    "MRS-RETIRE-002": Verdict.WARN,
    "MRS-RETIRE-003": Verdict.WARN,
    "MRS-STATUS-002": Verdict.WARN,
    "MRS-STATUS-003": Verdict.UNEVALUABLE,
    "MRS-STATUS-004": Verdict.WARN,
    "MRS-STATUS-005": Verdict.WARN,
    "MRS-STATUS-006": Verdict.UNEVALUABLE,
    "MRS-STATUS-007": Verdict.UNEVALUABLE,
    "MRS-STATUS-008": Verdict.WARN,
    "MRS-STATUS-009": Verdict.WARN,
    "MRS-CHECK-001": Verdict.WARN,
    "MRS-CHECK-002": Verdict.ERROR,
    "MRS-CHECK-003": Verdict.ERROR,
    "MRS-CHECK-004": Verdict.UNEVALUABLE,
    "MRS-SPIN-013": Verdict.WARN,
    "MRS-SPIN-014": Verdict.UNEVALUABLE,
    "MRS-SPIN-015": Verdict.WARN,
    "MRS-ADP-001": Verdict.ERROR,
    "MRS-ADP-002": Verdict.ERROR,
    "MRS-ADP-003": Verdict.ERROR,
    "MRS-ADP-004": Verdict.UNEVALUABLE,
    "MRS-ADP-005": Verdict.UNEVALUABLE,
    "MRS-ADP-006": Verdict.ERROR,
    "MRS-ADP-007": Verdict.WARN,
    "MRS-ADP-008": Verdict.ERROR,
    "MRS-ADP-009": Verdict.WARN,
    "MRS-ADP-010": Verdict.WARN,
    "MRS-ADP-011": Verdict.WARN,
    "MRS-CONFORM-001": Verdict.ERROR,
    "MRS-ADP-012": Verdict.ERROR,
    "MRS-ADP-013": Verdict.UNEVALUABLE,
    "MRS-ADP-014": Verdict.UNEVALUABLE,
    "MRS-ADP-015": Verdict.ERROR,
    "MRS-ADP-016": Verdict.WARN,
    "MRS-SMOKE-001": Verdict.UNEVALUABLE,
    "MRS-SMOKE-002": Verdict.ERROR,
    "MRS-SMOKE-003": Verdict.ERROR,
    "MRS-SMOKE-004": Verdict.WARN,
    "MRS-SMOKE-005": Verdict.UNEVALUABLE,
    "MRS-SMOKE-006": Verdict.ERROR,
    "MRS-SMOKE-007": Verdict.WARN,
    # Story 6.6 (the conformance matrix, FR-45/SM-6/AD-31/AD-37):
    # MRS-MATRIX-001 (a pre-existing adapter-probes.json/adapter-smoke.json
    # was malformed) at WARN, mirroring MRS-ADP-016/MRS-SMOKE-007's own
    # "degrades to empty, never blocks" tier. MRS-MATRIX-002 (writing the
    # tracked matrix file failed) at ERROR, mirroring MRS-ADP-015/
    # MRS-SMOKE-006's own "a real write was attempted and failed" tier.
    "MRS-MATRIX-001": Verdict.WARN,
    "MRS-MATRIX-002": Verdict.ERROR,
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
