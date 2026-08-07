"""The central finding-code registry (Story 1.1, architecture spine AD-15).

Every failure or warning Marshal ever emits carries a stable machine code
from this one registry, plus a human message (AD-15). Codes are never
reused or renumbered. Format: ``MRS-<AREA>-<NNN>`` (Consistency Conventions'
``Findings`` row) -- e.g. ``MRS-GATE-001``.

``REGISTERED_CODES`` shipped Story 1.1 as an empty ``frozenset()`` --
``marshal --version``/``--help`` bypass the envelope entirely (mirrors
``pyforge-doctor``), so nothing emitted a real finding yet. Story 1.2's
``core/identity.py`` is the first real caller: ``MRS-IDENT-001`` (a
malformed story key) and ``MRS-IDENT-002`` (a non-conforming merge subject)
are its two registered codes. Story 1.3's ``core/policy.py``/``cli/config.py``
add the registry's second real caller: ``MRS-POLICY-001`` (an unknown
top-level policy key), ``MRS-POLICY-002`` (a malformed STATIC field value),
``MRS-POLICY-003`` (a malformed SEED field value), ``MRS-POLICY-004``
(a CLI-boundary I/O failure resolving or writing policy -- an unreadable
``--project-policy`` file or an unwritable ``--materialize`` target),
``MRS-POLICY-005`` (no project slug supplied -- the composed policy omits
its project-derived seed path), and ``MRS-POLICY-006`` (a malformed project
slug -- not usable as a single path segment). 001-004 and 006 classify
``Verdict.UNEVALUABLE``; 005 classifies ``Verdict.WARN`` (a bare
no-active-project invocation legitimately shows the defaults and exits 0)
-- see ``core/verdict.py``. Story 1.4's ``cli/init.py`` adds the registry's
third real caller: ``MRS-INIT-001`` (a malformed project slug -- the shape
check itself is shared with ``core/policy.py`` via
``_is_valid_project_slug``, but ``init`` registers its own code since
``marshal init`` is a distinct command with its own envelope),
``MRS-INIT-002`` (the slug names no known BMAD project -- no
``_bmad-output/projects/<slug>/planning-artifacts`` in the main checkout),
``MRS-INIT-003`` (the loop home's active-project marker and
``planning-artifacts`` symlink already disagree with each other, or the
symlink carries a target shape this command never writes -- a prior partial
failure or hand configuration, blocked before any further write rather
than silently overwritten), and ``MRS-INIT-004`` (a ``git``/filesystem
operation failed -- worktree add, marker write, or symlink repoint -- or a
blocking in-home check found the provisioned tree missing the project the
symlink would target). 001-002 classify ``Verdict.UNEVALUABLE`` (Marshal
could not determine what to provision); 003-004 classify ``Verdict.ERROR``
(a real operation was attempted and failed, or was blocked to avoid
compounding an existing failure) -- see ``core/verdict.py``. Story 1.5's
``tier3_backlink`` step (still ``cli/init.py``) adds a fifth code,
``MRS-INIT-005``: a real, non-empty directory already occupies the loop
home's local Tier-3 path
(``_bmad-output/projects/<slug>/implementation-artifacts``) -- the safe,
structural refusal to silently
replace it with a backlink to the main checkout's canonical copy (see the
spec's Design Notes on why this is a distinct code from ``MRS-INIT-004``
rather than a message a caller would need to string-match). It classifies
``Verdict.ERROR``, the same tier as 003-004: a real operation was attempted
and blocked, not "could not evaluate". Story 1.6's read-only ``cli/init.py::run_homes``
(``marshal homes``, FR-4/FR-8) adds the registry's fourth real caller and its
own three codes: ``MRS-HOMES-001`` (a discovered home's marker slug, symlink
slug, or branch-derived slug disagree -- the three-way check that closes
``MRS-INIT-003``'s own narrower two-way blind spot named in deferred-work,
scoped to this NEW command only; the SAME code also names the main
checkout's own marker/symlink pair disagreeing, checked by the identical
two-way rule with no branch-derived third leg), ``MRS-HOMES-002`` (a home's
local Tier-3 backlink resolves, BY REALPATH, to a directory other than its
expected canonical store), and ``MRS-HOMES-003`` (a ``git``/filesystem
operation failed while gathering state -- the same "real operation attempted
and did not complete" tier as ``MRS-INIT-004``, not "could not evaluate").
All three classify ``Verdict.ERROR``, following ``MRS-INIT-003/004/005``'s
precedent: a real isolation check ran and found (or could not complete)
a real violation. Story 1.7's ``cli/init.py::run_preflight``
(``marshal preflight``, FR-7/FR-47/FR-52) adds the registry's fifth real
caller and its own ten codes, one per report check plus one shared by two
pre-provisioning gates, plus a pre-I/O slug-shape gate: ``MRS-PREFLIGHT-001``
(the ``bmad-loop`` harness binary is not on ``PATH``), ``MRS-PREFLIGHT-002``
(the harness's ``--version`` is outside the declared ``>=0.9.0,<0.10`` range,
or could not be determined at all), ``MRS-PREFLIGHT-003`` (no multiplexer
backend is available), ``MRS-PREFLIGHT-004`` (the configured adapter cannot
be resolved, or its binary is not on ``PATH``), ``MRS-PREFLIGHT-005`` (the
story feed is missing or unparseable), ``MRS-PREFLIGHT-006`` (a configured
verify command's executable is not on ``PATH``), ``MRS-PREFLIGHT-007``
(``main`` is checked out in more than one worktree, or that could not be
verified), ``MRS-PREFLIGHT-008`` (the configured adapter's first-run
requirement is unacknowledged, OR the acknowledgement state path could not
be resolved, OR a requested acknowledgement could not be recorded -- all
three are "the first-run gate is not satisfiably recorded"), and
``MRS-PREFLIGHT-009`` (a seed-file copy failed, OR the loop-home ROOT could
not be resolved, OR the loop home named on the command line is not
provisioned at all -- the latter two checked before any of the other eight,
sharing this code rather than adding more: each is "a real filesystem
precondition this command needs is not met", the same tier as the seed-copy
failure). All nine
classify ``Verdict.ERROR`` -- a real prerequisite check ran and failed, the
same tier as ``MRS-INIT-003/004/005``/``MRS-HOMES-*``, never "could not
evaluate". ``MRS-PREFLIGHT-010`` (a malformed project slug, checked before
any filesystem read/write -- review finding: an unvalidated slug could
resolve OUTSIDE the loop home via ``..``/an absolute path, and the seed-copy
step would then write real bytes there) classifies ``Verdict.UNEVALUABLE``
instead, mirroring ``MRS-INIT-001``'s own tier for the identical shape check:
a malformed slug means Marshal cannot determine what to preflight, not that
a gate failed. Story 1.8's ``cli/init.py::run_teardown`` (``marshal
teardown``, NFR-6/AD-29) adds the registry's sixth real caller and its own
three codes: ``MRS-TEARDOWN-001`` (a malformed project slug, including a
shape git rejects as a branch-name component -- the same pre-I/O shape gate
``run_init`` already applies, reusing its identical checks rather than a
third slug regex; ``run_preflight`` does not apply this same git-ref-shape
guard today, a pre-existing gap this story surfaced but did not cause),
``MRS-TEARDOWN-002`` (a git operation
failed -- resolving the current working directory or the loop-home root,
resolving worktree/branch state, or the removal itself -- or an on-disk
state git can no longer account for: a deregistered home path that still
exists and was never checked for uncommitted work), and
``MRS-TEARDOWN-003`` (refused: the home has uncommitted changes, the
branch's content is not yet safely captured on ``main``, or the AD-29
promotion-reachability stub names something unreachable -- and ``--force``
was not supplied; the one finding names every triggering condition).
``MRS-TEARDOWN-001`` classifies ``Verdict.UNEVALUABLE`` (Marshal cannot
determine what to tear down), the same tier as ``MRS-INIT-001``/
``MRS-PREFLIGHT-010``'s identical shape check; ``MRS-TEARDOWN-002/003``
classify ``Verdict.ERROR``, the same tier as every other story's
real-operation-attempted-and-did-not-complete codes -- see
``core/verdict.py``. Story 1.9's ``cli/init.py::run_preflight`` (packaging,
FR-52/FR-57) graduates the harness-version check and adds an eleventh
code, ``MRS-PREFLIGHT-011`` (a resolvable, same-major harness version that
lies outside the declared minor range, ``>=0.9.0,<0.10``) -- previously
this state shared ``MRS-PREFLIGHT-002`` with the undeterminable/
major-mismatch case; it is now split into its own code because it does
NOT block: ``MRS-PREFLIGHT-002`` remains for ``harness_version is None``
or a genuine major-version mismatch (``Verdict.ERROR``, blocking,
unchanged), while ``MRS-PREFLIGHT-011`` classifies ``Verdict.WARN``
(non-blocking) -- see ``core/verdict.py``. Story 2.1's ``cli/gate.py``/
``core/gate.py`` (``marshal gate evaluate``, FR-20) add the registry's
seventh real caller and its own five codes: ``MRS-GATE-001`` (a configured
verify command ran and exited non-zero), ``MRS-GATE-002`` (a verify
command's executable could not be launched at all -- surfaced by the
injected ``ProcessPort``, never a pre-flight ``shutil.which`` check),
``MRS-GATE-003`` (a verify command's string could not be ``shlex.split``,
e.g. an unterminated quote), ``MRS-GATE-004`` (``verify_commands`` composed
to the empty tuple -- Marshal's own ``DEFAULT_POLICY`` value, not a
project's declared intent to skip gating), and ``MRS-GATE-005`` (``--run
<id>`` was supplied but no run-journal fold exists yet -- ``core/journal``
is Story 3.1/3.2, both ``backlog``). ``MRS-GATE-001`` classifies
``Verdict.GATE_FAILED`` -- the table's first classification into that rung,
distinct from every prior code's ``Verdict.ERROR``/``Verdict.UNEVALUABLE``
tier: a REAL check ran and failed, not "an internal Marshal operation
failed" or "could not evaluate". ``MRS-GATE-002``/``003``/``005`` classify
``Verdict.UNEVALUABLE`` (Marshal could not run the check at all -- the same
tier as ``MRS-PREFLIGHT-006``'s own verify-command-resolvability code);
``MRS-GATE-004`` classifies ``Verdict.WARN``, the same tier as
``MRS-POLICY-005``/``MRS-PREFLIGHT-011`` -- a legitimate, non-blocking
bootstrap state, never a silent ``clean`` -- see ``core/verdict.py``. Story
2.4's ``core/gate.py::classify_doc_only_declaration`` adds a sixth code,
``MRS-GATE-006`` (the worktree has no changes AND the story was not
declared doc-only -- the one combination indistinguishable from a story
that silently failed to do its work). It classifies ``Verdict.GATE_FAILED``,
the same tier as ``MRS-GATE-001``: a real, determinable outcome (Marshal
evaluated and found nothing produced while no doc-only exemption was
claimed), never "could not evaluate" -- see ``core/verdict.py``. Story
3.2's ``core/journal.py::fold`` adds the registry's eighth real caller and
its own two codes: ``MRS-JOURNAL-001`` (a journal line that failed to
parse as JSON, or parsed but failed one of ``build_entry``'s own shape
invariants) and ``MRS-JOURNAL-002`` (a ``sidecar_ref`` payload whose blob
is missing from the caller-supplied ``sidecars`` mapping, or whose text is
not valid JSON, or whose decoded value is not itself a JSON object). Both
classify ``Verdict.UNEVALUABLE`` (AD-8): a quarantined line's own story key
and decision domain could not be evaluated, never a gate that failed --
see ``core/verdict.py``. Story 3.3's ``cli/spin.py`` (``marshal factory
spin``/``attach``, FR-9/FR-17) adds the registry's ninth real caller and its
own six codes: ``MRS-SPIN-001`` (a malformed project slug, checked before
any I/O -- the same pre-I/O shape gate every sibling command's own
``MRS-INIT-001``/``MRS-PREFLIGHT-010``/``MRS-TEARDOWN-001`` applies),
``MRS-SPIN-002`` (the loop home is not provisioned -- ``fs.is_dir(home)`` is
``False``, its Tier-3 backlink is absent, or that backlink dangles),
``MRS-SPIN-003`` (NO harness process was started, and none can have been --
covers ``spin``'s detached launch, ``run_foreground``'s synchronous one, and
``attach``'s exec failing to launch at all (a missing binary, a launch-time
``OSError``), AND ``run_spin``'s two pre-spawn filesystem setup failures,
creating the run directory and journaling the ``intent``, which abort before
``HarnessPort.spin`` is ever called. Review finding, Blind Hunter: the
earlier wording said "could not be LAUNCHED at all", which was false for
those latter two of its six emit sites. One code serves them all because
they share the property a caller acts on -- nothing is running, so a retry
is safe -- and each site's own message names which one it was), ``MRS-SPIN-004`` (the
harness's own self-minted ``harness_run_id`` could not be recovered within
``spin``'s bounded poll window -- the detached spawn itself still
succeeded), ``MRS-SPIN-005`` (the story feed is missing or unparseable --
``HarnessPort.story_feed_error`` returned non-``None``), and ``MRS-SPIN-006``
(the detached spawn itself SUCCEEDED, but its ``outcome`` entry could not be
journaled -- review finding, Blind Hunter, verified live: this case
originally reused ``MRS-SPIN-003``, conflating "never launched, safe to
retry" with "a live process now exists, unaccounted for in the journal" --
a caller treating either alike as safe-to-retry could double-spawn a second
concurrent run). ``MRS-SPIN-001`` classifies ``Verdict.UNEVALUABLE``, the
same tier as every sibling pre-I/O shape gate: Marshal cannot determine what
to launch. ``MRS-SPIN-002``/``003``/``005`` classify ``Verdict.ERROR``, the
same tier as every other real-precondition-checked-and-failed code
(``MRS-INIT-003/004/005``, ``MRS-PREFLIGHT-001``-``009``,
``MRS-TEARDOWN-002/003``): a real operation was attempted (or a real
precondition was checked) and did not converge, never "could not evaluate".
``MRS-SPIN-004``/``006`` classify ``Verdict.WARN``, the same tier as
``MRS-POLICY-005``/``MRS-PREFLIGHT-011``/``MRS-GATE-004`` -- and, for
``006`` specifically, the SAME tier AD-21's amendment (F-17) already assigns
a lone unclosed journal ``intent`` generally ("an unclosed intent... stays
open and is reported... classifies WARN, not error... escalating it is an
operator decision, never automatic"): a launch that already succeeded is
never re-classified as a failure over a paper-trail gap this codebase's own
architecture already treats as WARN system-wide. A malformed raw feed key
surfaces via the EXISTING ``MRS-IDENT-001`` (``core/identity.py``, already
``Verdict.UNEVALUABLE``) -- no new code was needed for that scenario, per
this story's own spec. Story 3.4's ``cli/spin.py`` (the supervisor's own
process lifecycle, AD-9/AD-20/AD-25) adds a SEVENTH code to the SAME
caller: ``MRS-SPIN-007`` (``ProcessPort.spawn_detached`` raised
``ProcessError`` spawning the supervisor sidecar, after the harness itself
already launched successfully). It classifies ``Verdict.WARN``, the same
tier as ``MRS-SPIN-006`` and for the identical reason: a live,
already-launched process is never re-classified as a failure over a
paper-trail gap -- here "no supervisor is watching this run" rather than
"the outcome entry could not be journaled." Story 3.5's
``supervisor/__main__.py`` (idle-strand detection, AD-9/AD-20) adds the
registry's tenth real caller and a NEW area, ``MRS-SUPV-*``, its own three
codes: ``MRS-SUPV-001`` (the idle ladder's ``nudge`` rung resolved no
window to deliver its text to, or delivery otherwise failed --
``SessionObserverPort.send_text`` returned ``False``), ``MRS-SUPV-002``
(the ``stop-and-retry`` rung's ``HarnessPort.stop``/``.resume`` call
raised ``HarnessError`` -- the tick loop continues watching the
possibly-still-wedged original pid rather than crashing), and
``MRS-SUPV-003`` (the run-launch outcome entry's ``harness_run_id`` field
is unavailable, so the ladder cannot act at all for this run -- journaled
once at attach; the tick loop continues heartbeat-only). All three
classify ``Verdict.WARN``, the same tier as ``MRS-SPIN-004``/``006``/
``007``: each names a DEGRADED-but-still-supervised condition (a nudge that
could not be delivered, a stop-and-retry that could not complete, a ladder
that cannot act at all) over a run that is never itself invalidated by it.
The same story adds an EIGHTH code to ``cli/spin.py``: ``MRS-SPIN-008``
(composing the project-policy layer to resolve the supervisor's own
``idle_threshold_minutes`` produced one or more ``MRS-POLICY-*`` findings).
It exists specifically so those findings reach the operator WITHOUT
inheriting their ``Verdict.UNEVALUABLE`` classification (review finding):
they are raised by ``core/policy.py`` for a command -- ``marshal config``
-- whose entire job IS the policy, where "the policy could not be
evaluated" is the correct verdict. In ``spin`` the policy is a supplementary
input consulted AFTER the harness has already launched, so re-using their
own tier would exit ``1`` over a live, running, supervised process and
invite a retrying caller to double-dispatch the story. ``MRS-SPIN-008``
therefore classifies ``Verdict.WARN``, for the identical reason
``MRS-SPIN-006``/``007`` do: a launch that already succeeded is never
re-classified as a failure over a diagnostic about something else.

Story 3.6 (budget ceilings, AD-20/AD-32, FR-13) adds THREE more codes to
``supervisor/__main__.py``'s own ``MRS-SUPV-*`` area: ``MRS-SUPV-004`` (a
budget ceiling transitioned ``NONE`` -> ``APPROACHING`` -- the 80%-of-limit
warning, journaled once on the rising edge), ``MRS-SUPV-005`` (a budget
ceiling BREACHED and the terminal ``HarnessPort.stop`` call either raised
``HarnessError``, reported the run was not stopped, or had no
``harness_run_id`` to stop against -- the identical shape ``MRS-SUPV-002``
already registers for the idle ladder's own ``stop``/``resume`` failures,
given a distinct code because a budget breach and an idle-ladder action are
different DECISIONS reaching the same kind of stop-call failure), and
``MRS-SUPV-006`` (a token-ceiling usage sample is ``stale-evidence`` --
``state.json``'s own mtime is older than the reused idle-ladder threshold,
or unresolvable -- AD-32's own amendment, F-24: this is NEVER
``unevaluable``, which is AD-8-blocking and would red the run over the
ordinary case FR-12's ladder already handles gracefully with a nudge; both
token ceilings are simply skipped for that tick, and the wall-clock
ceilings remain the binding constraint). All three classify
``Verdict.WARN``, the same tier as the story's own ``MRS-SUPV-001/002/003``
and every DEGRADED-but-still-supervised condition this area already
registers -- a budget warning, a failed stop, or stale evidence never
itself invalidates the run's supervision. The same story adds a NINTH code
to ``cli/spin.py``: ``MRS-SPIN-009`` (FR-14's own non-blocking preflight
advisory -- a resolved story's spec size or prior-attempt history in this
loop home's own past runs suggests it is likely to exceed budget). It
classifies ``Verdict.WARN`` for the same reason ``MRS-SPIN-004``/``006``/
``007``/``008`` do: a heads-up about a story about to run is never a
launch precondition, and never re-classifies an otherwise-clean launch as a
failure.

Story 3.7 (escalation, deferral, and resume, AD-9/AD-34/AD-45,
FR-15/16/17) adds a TWELFTH code to ``supervisor/__main__.py``'s own
``MRS-SUPV-*`` area, ``MRS-SUPV-007`` (the mandatory escalation file-marker
write -- ``NotifyPort.notify_file`` -- raised ``FsError``; the desktop
notify is fully best-effort and registers no finding at all). It classifies
``Verdict.WARN``, the same tier as this area's own 001-006: a degraded-but-
still-supervised condition (the escalation was detected and journaled
regardless; only the durable marker's own write failed) never itself
invalidates the detach. The same story adds two more codes to
``cli/spin.py``'s own caller: ``MRS-SPIN-010`` (``marshal factory resume``
refused -- a live ``run_status_snapshot`` read classified
``EscalationStatus.UNRESOLVED`` before any spawn) and ``MRS-SPIN-011``
(``marshal factory resume`` refused -- no resumable Marshal run exists for
the slug, or the one found could not have its ``harness_run_id`` recovered
from its own journal). Both classify
``Verdict.ERROR``, the same tier as every other real-precondition-checked-
and-failed code on this caller (``MRS-SPIN-002/003/005``): a real refusal
gate ran and blocked the resume, never "could not evaluate" and never a
degraded-but-proceeding launch.

Review finding (pass 1): the SAME caller adds a THIRTEENTH code,
``MRS-SPIN-012`` -- the live ``run_status_snapshot`` read the resume
refusal gate depends on returned ``None`` (a ``state.json`` read/parse
failure at exactly the moment ``resume`` runs), so the gate could not
positively confirm the escalation is resolved and proceeded anyway
(mirrors AD-32's own "a stale/unreadable sample degrades to a registered
WARN, never a silent pass" precedent for the budget ceilings' identical
ambiguity). It classifies ``Verdict.WARN``: the launch is not refused on
mere ambiguity -- refusing every resume on a transient read hiccup would
make the common case (resuming an ordinary, never-escalated pause) newly
unreliable -- but the ambiguity is never silent.

Story 3.8 (stage-bound durability and fleet-launch wiring, AD-46/FR-61)
adds an EIGHTH code to ``supervisor/__main__.py``'s own ``MRS-SUPV-*``
area, ``MRS-SUPV-008`` (a durability push -- ``VcsPort.push``, at a stage
boundary or the interval-watcher fallback -- raised ``VcsCommandError``).
It classifies ``Verdict.WARN``, the same tier as this area's own 001-007:
AD-46 states plainly that durability is "best-effort against transient
network conditions, never a new refusal gate" -- a failed push never
invalidates the run's own supervision, and the tick loop continues
regardless.

Story 2.3 (frozen-surface scope check, narrowing only, AD-4/AD-26/AD-27)
adds THREE more codes to ``cli/gate.py``/``core/gate.py``'s own area, the
first real classifications into ``Verdict.SCOPE_VIOLATION`` (reserved
since Story 1.1, never used until now): ``MRS-GATE-007`` (a changed path
matches no glob in the computed effective surface,
``policy_surface ∩ spec_surface``), ``MRS-GATE-008`` (a changed path
matches a glob in the live frozen set -- names the offending path and the
freezing story, or "policy" for a policy-seeded freeze), and
``MRS-GATE-009`` (``--scope-check`` was requested but could not be
evaluated at all -- no active/resolvable project, no ``--story``, a
``VcsPort`` failure resolving the worktree's changed files, or the
story's own tracked spec declaring a ``surface:`` key in a form
``core.spec_surface.parse_declared_surface`` does not support -- a
multi-line YAML block, review finding, Edge Case Hunter: that form must
never be silently treated as "no declared surface", which would WIDEN the
effective surface, the exact AD-27 violation this whole feature exists to
prevent). An unresolvable ``--story`` value is a DIFFERENT, EXISTING code
-- ``MRS-IDENT-001`` (``core/identity.py``'s own malformed-story-key code),
never ``MRS-GATE-009`` (review finding, Blind Hunter: an earlier draft of
this docstring, and of ``cli/gate.py``'s own, both claimed
``MRS-GATE-009`` here, which the code has never actually emitted for this
case -- pinned by
``tests/unit/test_cli.py::test_gate_evaluate_scope_check_unresolved_story_reports_mrs_ident_001``).

Story 4.1 (story-spec promotion, AD-13/AD-24/AD-29/AD-33) adds the
registry's eleventh real caller, ``cli/deploy.py``/``core/promotion.py``
(``marshal deploy promote``), and a NEW area, ``MRS-DEPLOY-*``, its own
three codes: ``MRS-DEPLOY-001`` (a story is durable per
``core.promotion.merged_story_keys`` -- reachable from ``origin/main`` or
local ``main`` -- but no Tier-3 ``spec-<key>*.md`` file exists to promote
for it at all), ``MRS-DEPLOY-002`` (a durable story's Tier-3 spec exists but
fails ``core.promotion.is_valid_spec_text``'s minimal parse -- zero-byte or
missing frontmatter/``status:`` -- and is therefore NOT promoted, never
overwriting a good existing tracked copy, per AD-13), and
``MRS-DEPLOY-003`` (``VcsPort.commit_subjects`` could not read local
``main``'s own commit history at all -- the run cannot determine ANY
story's durability, so nothing is promoted -- OR the promotion write path
itself -- copying a spec's bytes into the tracked archive, or
``VcsPort.commit_paths``'s stage-and-commit -- failed, leaving that run
unable to positively confirm its own promotion completed). ``MRS-DEPLOY-001``/
``002`` classify ``Verdict.WARN``, the same tier as this codebase's every
other "reported, never blocks progression" paper-trail-gap code
(``MRS-POLICY-005``, ``MRS-PREFLIGHT-011``, ``MRS-GATE-004``, AD-21's own
F-17 unclosed-``intent`` precedent): a gap is named so it is never passed
over silently, but promotion continues for every OTHER candidate in the
same run -- the same reasoning this codebase already applies system-wide to
a paper-trail gap that does not itself invalidate the surrounding
operation. ``MRS-DEPLOY-003`` classifies ``Verdict.UNEVALUABLE`` (the
story's own edge-case matrix names this explicitly for the ``commit_subjects``
failure; the write-path failure is folded into the SAME code and tier per
AD-31's "one code, one classification" rule -- AD-31 forbids the same code
classifying two different rungs depending on context, so a git-history read
failure and a promotion-write failure are reported as the SAME "Marshal
could not confirm this run's promotion truthfully" condition rather than
inventing an asymmetric ERROR-tier sibling for an untested edge no
acceptance criterion names). The push route (``commit_subjects(repo_root,
"origin/main")``) is deliberately EXEMPT from ``MRS-DEPLOY-003``: a missing
``origin`` remote (or an unfetched ``origin/main``) is the ordinary,
non-error "no push route available" case (the story's own I/O matrix: "No
error, no ``VcsCommandError``") and falls back to the local-``main`` route
silently, per AD-29's own "durability must not require the network"
amendment (F-14).
``MRS-GATE-007``/``008`` classify ``Verdict.
SCOPE_VIOLATION``: a real change was evaluated and found outside the
allowlist it is judged against, or touching a file its own or another
story froze -- a distinct rung from ``GATE_FAILED`` (a configured check
that ran and failed) and from ``UNEVALUABLE`` (Marshal could not determine
an answer at all). ``MRS-GATE-009`` classifies ``Verdict.UNEVALUABLE``,
the same tier as ``MRS-GATE-002``/``003``/``005``: Marshal could not run
the scope check at all. The SAME story also generalizes ``MRS-GATE-005``'s
own meaning: since ``core/journal.fold`` now has a real caller here (Story
3.2's own fold gains its second real caller), ``--run <id>`` no longer
means "no run-journal fold exists yet" -- it now means "the requested
run-scoped fold could not be PRODUCED" (no loop home resolvable for the
active project, the run directory does not exist, or its journal could
not be read/folded), a strictly broader reading of the SAME code rather
than a new one, since both describe the identical caller-facing shape
("a run-scoped answer was requested and Marshal could not honor it") and
the identical ``Verdict.UNEVALUABLE`` classification.

Story 2.7 (a gate binds to the spec's Success signal, AD-4/AD-31/AD-49)
adds two more codes to ``cli/gate.py``/``core/gate.py``'s own area:
``MRS-GATE-010`` (``core.gate.check_spec_binding`` was given
``declared_commands is None`` -- no tracked spec exists for the story
``--story`` names, or its tracked spec's ``## Verification`` ->
``**Commands:**`` section could not be parsed at all) and ``MRS-GATE-011``
(one per command the spec's own Success signal declared that is no longer
present in the policy's ``verify_commands`` -- narrowed or removed since
the spec was tracked). Both classify ``Verdict.SCOPE_VIOLATION``, the SAME
rung ``MRS-GATE-007``/``008`` already use: per AD-49's own text, "an
untraceable or mismatched binding cannot itself be waived to green" --
the identical closed-lattice reasoning this codebase's other
``SCOPE_VIOLATION`` codes already carry, never a ``WARN`` folded into an
otherwise-green verdict.

Story 4.2 (teardown reachability and spec-recovery assistance, AD-27/AD-29)
adds two more codes. ``MRS-TEARDOWN-004`` (``cli/init.py::run_teardown``,
joining the ``MRS-TEARDOWN-*`` area Story 1.8 opened): an AD-29
unreachable-promotion refusal was met with ``--force`` but no ``--abandon``,
or an ``--abandon`` set that does not EXACTLY match the reachability check's
own reported set (a superset or a subset both refuse -- no vacuous or
partial abandonment). Classifies ``Verdict.ERROR``, the same tier as
``MRS-TEARDOWN-003``: a real refusal gate ran and the operator's own
override attempt did not satisfy it. ``MRS-DEPLOY-004``
(``cli/deploy.py::run_recover_spec``, joining the ``MRS-DEPLOY-*`` area
Story 4.1 opened): a story key has neither a surviving Tier-3 run-worktree
snapshot nor an ``epics.md`` section to regenerate from -- a genuinely
orphaned key, reported rather than fabricated. Classifies ``Verdict.WARN``,
the same tier as ``MRS-DEPLOY-001``/``002``: a paper-trail gap reported for
the operator's attention, not itself a failed operation (recovery
correctly found nothing to recover, and said so).

Code review (2026-08-06, P5, Edge Case Hunter) adds a fifth ``MRS-DEPLOY-*``
code, ``MRS-DEPLOY-005``: ``deploy recover-spec``'s epics.md-derived
fallback wrote a "recovered" spec whose Intent and/or Acceptance Criteria
section came back empty after parsing (a parsing miss, or a genuinely
sparse epics.md section) -- the file is still written (this command
"reports, never fabricates"), but the operator is warned rather than
trusting a hollow recovery silently. Classifies ``Verdict.WARN``, the same
tier as ``MRS-DEPLOY-001``/``002``/``004``: a paper-trail caveat, never
itself a failed operation.

Code review (2026-08-06, P1, both reviewers' independent top finding) adds a
third ``MRS-TEARDOWN-*`` code, ``MRS-TEARDOWN-005``: ``run_teardown``'s AD-29
reachability check itself could not run (its delegate,
``deploy.unreachable_promotions_for_slug``, returns ``None`` rather than
``()`` when the REQUIRED local-``main`` route -- ``VcsPort.commit_subjects``
-- raises, ``MRS-DEPLOY-003``). An UNDETERMINED reachability state must
never be reported the same as a CONFIRMED-empty one -- classifies
``Verdict.ERROR``, the SAME tier as ``MRS-TEARDOWN-003``/``004``, never a
looser ``UNEVALUABLE``: this refusal must be AT LEAST as strict as a real
non-empty unreachable set, and ``--force`` alone must never silently carry
past it (see ``run_teardown``'s own comment for the ``--abandon
UNDETERMINED`` sentinel override it requires instead).

Story 4.3 (merge-subject conformance and review-cap landing, FR-27/AD-24)
adds four more codes, joining the ``MRS-DEPLOY-*`` area with
``cli/deploy.py``'s ``marshal deploy land-story`` action. ``MRS-DEPLOY-006``
(``--justification`` missing or empty -- the cheap precondition checked
FIRST, before any gate re-run) and ``MRS-DEPLOY-007`` (the named story's
loop-home/station branch could not be resolved: no provisioned loop home,
the branch does not exist, or the ``--since`` merge-base read failed)
classify ``Verdict.UNEVALUABLE`` -- both mean Marshal cannot determine what
to land, the same tier as ``MRS-INIT-001``/``MRS-GATE-009``'s own precondition
codes. ``MRS-DEPLOY-008`` (``VcsPort.merge_branch`` raised -- a real
conflict or other git failure) classifies ``Verdict.ERROR``, the same tier
as ``MRS-INIT-003``/``MRS-TEARDOWN-002``: a real write was attempted against
a gate that had already passed, and did not converge. ``MRS-DEPLOY-009``
(the post-merge conformance audit's own ``VcsPort.commit_subjects`` read
failed) classifies ``Verdict.WARN``, the same tier as ``MRS-DEPLOY-001``/
``002``/``004``/``005``: the landing itself already succeeded by this point
(a merge failure is ``MRS-DEPLOY-008``, reported before any journal entry
is written), so an audit that cannot enumerate its own window is a
reporting gap, never grounds to undo or block a landing that has already
happened (the story's own "the conformance audit never blocks the landing"
Never bullet).

Code review (2026-08-06) adds three more ``MRS-DEPLOY-*`` codes for
``land-story``. ``MRS-DEPLOY-010`` (P2: the full gate's verdict was not
EXACTLY ``clean`` -- e.g. ``warn``, real non-blocking findings exist)
classifies ``Verdict.GATE_FAILED``, the same tier as ``MRS-GATE-001``: FR-27
requires a fully clean gate before a deliberate manual landing, so anything
short of ``clean`` (even the ordinarily-exit-0 ``warn`` rung) is refused
here, same as a real gate failure. ``MRS-DEPLOY-011`` (P4: the loop-home
station branch's tip could not be reconfirmed immediately before merging,
or had moved since the gate evaluated it) classifies ``Verdict.ERROR``, the
same tier as ``MRS-TEARDOWN-003``/``004``: a real safety refusal after an
already-attempted operation, not "could not determine" -- the gate DID run;
this is a stronger, race-condition-specific stop. ``MRS-DEPLOY-012`` (P7: a
redaction failure at journal-capture time swallowed the operator's
``--justification`` text) classifies ``Verdict.WARN``, the same tier as
``MRS-DEPLOY-001``/``002``/``004``/``005``/``009``: the landing itself
already succeeded, so a lost justification is a paper-trail visibility gap,
never grounds to undo it.

Story 4.4 (batch pull request with hygiene preflight, FR-29/NFR-2, AD-34)
adds two more ``MRS-DEPLOY-*`` codes for ``marshal deploy batch-pr``.
``MRS-DEPLOY-013`` (a fired ``landing_rules`` entry with ``required_check``
set is NOT satisfied -- its named check is missing or did not conclude
``"success"`` on the wave's own head commit) classifies
``Verdict.SCOPE_VIOLATION``, the same rung ``MRS-GATE-007``-``011`` already
use: a real, project-declared gate evaluated the change set and found it
non-conforming, blocking before any PR write is attempted -- never a mere
internal-operation failure. ``MRS-DEPLOY-014`` (``ForgePort``'s own ``gh``
invocation failed -- listing, creating, updating a PR, or applying labels)
classifies ``Verdict.ERROR``, the same tier as ``MRS-DEPLOY-008``
(``VcsPort.merge_branch`` failing): a real outbound write was attempted and
did not complete.

Code review (2026-08-06) adds three more ``MRS-DEPLOY-*`` codes for
``marshal deploy batch-pr``, most severe first. ``MRS-DEPLOY-015`` (P1: policy
composition reported an ERROR-severity finding naming the ``landing_rules``
key -- a malformed layer that ``core/policy.py`` silently excludes, falling
back to ``DEFAULT_POLICY``'s empty rule set) HARD REFUSES the entire
``batch-pr`` invocation before the hygiene preflight ever runs and before the
forge is ever touched: proceeding on a malformed ``landing_rules`` layer
would silently evaluate against ZERO rules instead of the project's declared
ones, letting a config typo -- not a deliberate decision -- bypass the
hygiene gate entirely. Classifies ``Verdict.ERROR``, the same tier as
``MRS-TEARDOWN-005``'s identical "this refusal must be at least as strict as
a real violation, never a softer UNEVALUABLE" reasoning. ``MRS-DEPLOY-016``
(P4: the head branch moved between the hygiene preflight's own read of its
tip and the PR write that was about to follow) classifies ``Verdict.ERROR``,
the same tier as ``MRS-DEPLOY-011``'s identical TOCTOU shape for
``land-story``'s own branch-tip pinning: content the hygiene preflight never
vetted must never reach ``create_pr``/``update_pr``. ``MRS-DEPLOY-017`` (P5:
the loop-home worktree's own checked-out commit does not match the head
branch's resolved tip immediately before ``changed_files`` is trusted)
classifies ``Verdict.ERROR``, the same tier: a stale or detached local
worktree must never silently under-report the hygiene preflight's own
change set. ``MRS-DEPLOY-018`` (P8, Edge Case Hunter: ``find_open_pr``
returned an existing PR whose own ``base`` does not equal the
policy-declared ``landing_base_branch``) classifies ``Verdict.ERROR``, the
same tier: ``update_pr`` must never be called against a PR targeting a
different base than policy declares -- that PR belongs to some other,
unrelated intent this command must not silently rewrite.

Story 4.5 (feed refresh with truth partitioned by domain, AD-33) adds two
more ``MRS-DEPLOY-*`` codes for ``marshal deploy refresh-feed`` plus a new
area, ``MRS-STATUS-*``. ``MRS-DEPLOY-019`` (a ``landing_resync_commands``
entry could not be run at all -- it failed to ``shlex.split``, used bare
shell syntax ``ProcessPort`` would never honor, or ``ProcessPort.run``
itself raised) classifies ``Verdict.UNEVALUABLE``, the same tier as
``MRS-GATE-002``/``003``: Marshal could not run the configured command at
all. ``MRS-DEPLOY-020`` (a ``landing_resync_commands`` entry ran and exited
non-zero) classifies ``Verdict.GATE_FAILED``, the same tier as
``MRS-GATE-001``/``MRS-DEPLOY-010``: a real, policy-configured command ran
and did not pass. ``MRS-STATUS-001`` (``core.status.reconcile_feed_domains``:
a journal-claimed ``commit_sha`` for a story that git's own
``core.promotion.merged_story_keys`` does not confirm -- the harness
believes a commit landed; git disagrees) classifies ``Verdict.WARN``, the
same tier as this codebase's every other "reported, never blocks
progression" paper-trail-gap code (``MRS-DEPLOY-001``/``002``/``004``/
``005``/``009``/``012``): AD-33 forbids resolving the discrepancy either
way, so it is named, never silently passed over, but never itself
invalidates the report.

Story 4.6 (deploy idempotence and reconciliation of open intents, AD-6/
AD-21/AD-28) adds a twenty-first ``MRS-DEPLOY-*`` code, ``MRS-DEPLOY-021``
(``cli/deploy.py``'s ``promote``/``land-story``/``batch-pr`` all gain
intent/outcome journal pairs around their own irreversible step -- a
committed spec, a merge, a PR create/update -- and, before re-attempting
that step, fold the journal for a matching OPEN intent left by a prior,
possibly-crashed invocation; ``core.journal.intent_reconciles`` judges
whether externally-gathered evidence closes it). ``MRS-DEPLOY-021`` names
an open intent that no evidence yet confirms -- classifies ``Verdict.WARN``,
never ``Verdict.ERROR``, per AD-21's own F-17 amendment: an unclosed
intent must never make every subsequent ``deploy`` invocation non-zero,
and never blocks the run reporting it; escalating it is an operator
decision, never automatic.

Code review (2026-08-06, P3, Blind Hunter) adds a twenty-second
``MRS-DEPLOY-*`` code, ``MRS-DEPLOY-022``: ``_fold_deploy_journal``'s own
GLOBAL fold across every run directory can itself fail (a shape ``fold``
does not tolerate escaping as ``TypeError``/``ValueError``/``KeyError``/
``OSError``) -- previously this degraded SILENTLY to an empty
``FoldResult``, indistinguishable from "confirmed: no open intents
anywhere" and hiding every genuinely open intent from reconciliation with
zero signal. ``MRS-DEPLOY-022`` names that the cross-run fold failed and
reconciliation could not be attempted this invocation. Classifies
``Verdict.WARN``, the same tier as ``MRS-DEPLOY-021``: the underlying
action still proceeds normally (this story's own architecture-wide "never
blocking" posture for a paper-trail gap), but the gap itself is reported,
never silently absorbed.

Story 4.8's ``cli/land.py::run_land`` adds the twelfth real caller's own NEW
area, ``MRS-LAND-*`` (FR-60/AD-40, "marshal land -- the last mile lands
itself"): seven codes. ``MRS-LAND-001`` (the loop-home station branch
``loop/<slug>`` could not be resolved or does not exist -- refused before
any forge call) and ``MRS-LAND-002`` (a malformed ``landing_rules`` policy
layer -- the SAME hard-refuse-before-any-forge-call precondition
``MRS-DEPLOY-015`` already established for ``batch-pr``, copied verbatim
for ``land``) both classify ``Verdict.ERROR`` -- a precondition failure,
never "ran and found nothing". ``MRS-LAND-003`` (this wave is already
durably merged into the base branch, but ``ForgePort`` reports the PR's own
head branch is still open on the forge -- ``ForgePort`` has no standalone
"delete this branch" primitive, deliberately, per this story's own Design
Notes, so this run has no forge-side action left to retire it through)
classifies ``Verdict.WARN`` -- reported, never blocking: the landing itself
already happened, only its own retirement bookkeeping is unconfirmed.
``MRS-LAND-004`` (a fired ``required_check`` landing rule resolved to a
real, non-``"success"`` conclusion -- e.g. ``"failure"``/``"cancelled"`` --
or could not be read at all) classifies ``Verdict.GATE_FAILED``, the same
tier as ``MRS-GATE-001``/``MRS-DEPLOY-010``/``020``: a real, negative CI
signal, never treated the same as "still running". ``MRS-LAND-005`` (a
fired ``required_check`` has not concluded yet -- ``ForgePort.
check_run_status`` returned ``None``) classifies ``Verdict.WARN``: this run
refuses to merge, but a still-pending check is not itself a failure --
AD-8's own "an unevaluable/pending signal is treated as NOT-YET-SAFE-TO-ACT,
never silently treated as passing" amendment, re-run ``marshal land`` once
the check concludes. ``MRS-LAND-006`` (this run's own hygiene/required-check
evaluation surfaced a WARN-tier finding whose code is NOT already present
in ``cli/init.py``'s shared, machine-scoped acknowledgement store, Story
1.7's ``_ack_state_path``/``_read_acknowledged``) classifies
``Verdict.ERROR`` -- escalated, and blocks the merge: an unacknowledged
advisory is never a silent force, mirroring ``land-story``'s own "no partial
force" precedent. ``MRS-LAND-007`` (``ForgePort.merge_pr`` itself failed --
network/auth/conflict) classifies ``Verdict.ERROR``, the same tier as
``MRS-DEPLOY-008``/``014``: a real, irreversible-step write was attempted
and did not converge; the intent stays open, no outcome is journaled.

Story 4.9 (an advisory lock serializes concurrent writes to the shared,
git-tracked ``planning-artifacts/specs/`` store, AD-42) adds a twenty-third
``MRS-DEPLOY-*`` code, ``MRS-DEPLOY-023``: ``run_promote``'s new
``FsPort.acquire_advisory_lock`` call (wrapping the ``copy_file`` loop plus
``commit_paths``) could not acquire the lock within its own ``timeout_s`` --
another process is plausibly promoting the SAME project concurrently, or the
lock file's parent is unwritable. Classifies ``Verdict.WARN``, the same tier
as ``MRS-DEPLOY-021``/``022``: a clean, re-entrant refusal
(``data.lock_contended: true``, ``data.promoted: []``), never a hard error
-- re-running ``promote`` later is always safe and expected to converge,
matching AD-6's own idempotence posture for every other ``deploy``
precondition.

Story 4.10 (fleet-wide branch retirement, FR-63/AD-47) adds the thirteenth
real caller's own NEW area, ``MRS-RETIRE-*`` (``cli/retire.py``'s ``marshal
retire``): three codes. ``MRS-RETIRE-001`` (a malformed ``--project`` slug,
checked before any I/O -- the same pre-I/O shape gate every sibling
command's own ``MRS-INIT-001``/``MRS-SPIN-001``/``MRS-TEARDOWN-001``
applies) classifies ``Verdict.UNEVALUABLE``: Marshal cannot determine what
to sweep. ``MRS-RETIRE-002`` (a ``VcsCommandError`` from
``VcsPort.is_branch_merged``/``worktree_path_for_branch`` while gathering
evidence for one candidate branch, or from enumerating the fleet's
worktrees at all) classifies ``Verdict.WARN`` -- per the story's own I/O
matrix, that branch is refused (``insufficient_evidence``) and the sweep
continues for every other branch/project; a read failure never itself
invalidates the report. ``MRS-RETIRE-003`` (a ``VcsPort.delete_branch``
call under ``--execute`` failed for one already-PROPOSED branch, or the
post-deletion journal write for a project's own deleted set failed)
classifies ``Verdict.WARN``, the same tier as ``MRS-RETIRE-002`` and this
codebase's every other "reported, never blocks progression" paper-trail-gap
code: the remaining proposed branches still get their own attempt, per the
story's own Always bullet ("a delete_branch failure for one branch does not
abort the sweep").

Story 5.1 (fleet-wide runtime status, FR-36/AD-5) adds one more code,
``MRS-STATUS-002`` (``cli/status.py``'s ``marshal status``): a discovered
home's most recent run journal, or bmad-loop's own ``state.json`` (via
``HarnessPort.run_status_snapshot``), could not be read far enough to
recover a supervisor pid and a live snapshot -- OR the fleet's own
``VcsPort.list_worktrees`` enumeration itself failed. Classifies
``Verdict.WARN``, the same "a per-row/per-sweep read failure degrades
cleanly, never aborts the whole report" tier as ``MRS-RETIRE-002``'s
identical rationale: the affected row (or the whole sweep, for an
enumeration failure) reports a reportable ``"unknown"``-shaped state
rather than crashing or silently reading as healthy -- see
``core/status.py::build_fleet_row``'s own docstring for the row-shape
degradation.

Story 5.2 (per-run detail, FR-37/NFR-12) adds two more codes to
``cli/status.py``'s own ``MRS-STATUS-*`` area: ``MRS-STATUS-003``
(``--run <run_id>`` was supplied without ``--project <slug>`` alongside it
-- a run id alone does not name which project's Tier-3 store to look
under, checked before any I/O) and ``MRS-STATUS-004`` (``--run``/
``--project`` were both supplied but no run directory exists for that
project/run-id pair). ``MRS-STATUS-003`` classifies ``Verdict.
UNEVALUABLE``, the same tier as every other pre-I/O precondition-shape
gate (``MRS-INIT-001``, ``MRS-SPIN-001``, ``MRS-DEPLOY-006``'s own
``--justification`` precedent): Marshal cannot determine what to report.
``MRS-STATUS-004`` classifies ``Verdict.WARN``, the same "clean, reportable
gap, never itself a failure" tier as ``MRS-DEPLOY-004``'s own orphaned-key
precedent: a typo'd or torn-down run id is reported, never fabricated, and
never blocks (``data.found: false``). ``MRS-STATUS-002`` (already
registered, Story 5.1) is REUSED, not replaced, with a broadened meaning:
it now ALSO names a per-run detail view whose live ``state.json`` could not
be read (no loop home currently attached for the project, or its own
``RunStatusSnapshot`` read failed) -- the identical shape and rationale
Story 4.1's own ``MRS-GATE-005`` broadening already established for the
SAME "a run-scoped answer was requested and Marshal could not honor it"
caller-facing meaning.

Story 5.4 (ledger-vs-git reconciliation, FR-39/FR-40) adds three more codes
to ``cli/status.py``'s own ``MRS-STATUS-*`` area. ``MRS-STATUS-005`` (the
tracked ``sprint-status-ledger.yaml`` twin for ``--project SLUG`` could not
be read -- missing entirely, invalid YAML, or no ``development_status``
map) classifies ``Verdict.WARN``, the same "clean, reportable gap, never
itself a failure" tier as ``MRS-STATUS-004``'s own orphaned-run precedent:
``data.discrepancies`` reports empty, never fabricated. ``MRS-STATUS-006``
(``--reconcile-ledger`` supplied without ``--project`` alongside it,
checked before any I/O) classifies ``Verdict.UNEVALUABLE``, the same
pre-I/O shape-gate tier as ``MRS-STATUS-003``'s own ``--run``/``--project``
precedent -- a fleet-wide reconciliation sweep is out of this story's own
scope. ``MRS-STATUS-007`` (git's own commit history for ``main`` could not
be read while gathering ``core.promotion.merged_story_keys``'s durability
evidence) classifies ``Verdict.UNEVALUABLE``, mirroring
``MRS-DEPLOY-003``'s identical rationale in the promotion area: Marshal
cannot honestly determine ANY story's durability this run, so this is a
"could not evaluate", never a "reported and moved on", finding.

Story 5.5 (durability as a reported fleet-status dimension, FR-62/AD-48)
adds two more codes to ``cli/status.py``'s own ``MRS-STATUS-*`` area, both
sourced from the fleet-summary path's ONE-per-sweep read of the EXISTING
``scripts/unpushed_work_check.py --json --branches-only`` detector (AD-48:
read from that detector, never re-derive its branch-vs-remote diff a
second way). ``MRS-STATUS-008`` (a home's own station branch,
``loop/<slug>``, carries local-only content the detector confirmed is not
on any remote) classifies ``Verdict.WARN``, the same "reported, never
blocks progression" tier as this area's own 001/005 -- a home with
unpushed work is never reported clean, but the sweep still reports every
other home normally. ``MRS-STATUS-009`` (the detector itself could not be
consulted this run at all -- the script is missing, its launch failed, it
returned its own documented ``UNKNOWN``/exit-2 case, or its ``--json``
output failed to parse) also classifies ``Verdict.WARN``, the same tier:
every row's ``unpushed_work`` reports ``null`` (unknown) rather than
crashing the sweep or, worse, silently reading as "confirmed clean" -- the
exact false-green the detector's own module docstring names as the
2026-07-31 incident's root cause.

Story 6.1 (profile-driven adapter selection, project-scoped, FR-48/FR-51/
AD-19) adds two more codes to ``cli/spin.py``'s own ``MRS-SPIN-*`` area:
``MRS-SPIN-013`` (a resolved in-scope story's own tracked spec declares a
``difficulty:`` frontmatter key in a form ``core.spec_difficulty.
parse_declared_difficulty`` does not support -- the multi-line YAML block
form, ``DifficultyParseError`` -- that story is treated as undeclared for
governance purposes, but the gap is reported rather than silently
absorbed) and ``MRS-SPIN-014`` (the loop home's own configured adapter name
could not be resolved to a real profile -- ``HarnessPort.adapter_binary``
raised ``HarnessError`` for an unknown/unrecognized adapter). Both classify
``Verdict.WARN``/``Verdict.UNEVALUABLE`` respectively (``MRS-SPIN-013``
alongside this area's own 004/006/007/008/009/012 "reported, never blocks
an already-in-flight launch" paper-trail-gap tier: the launch's own model
resolution degrades to "no override" for that one story, exactly as an
undeclared difficulty already does, and every other story in the batch is
unaffected; ``MRS-SPIN-014`` at the SAME tier ``MRS-GATE-009``'s own
"Marshal could not evaluate this at all" reasoning uses, per the spec's own
explicit "Verdict.UNEVALUABLE, never a crash" wording for this exact
scenario -- distinct from ``MRS-SPIN-002``/``003``/``005``'s ERROR tier
because an unresolvable adapter name is a configuration fact Marshal cannot
determine, not a real precondition that was checked and failed) -- see
``core/verdict.py``.

A review pass on Story 6.1 found the resolved model tiering was journaled
and reported but never actually reached the loop home's own
``.bmad-loop/policy.toml`` -- the file ``bmad-loop run`` (the process this
same launch spawns) actually reads -- so the launched process could apply a
DIFFERENT model tier than the one this run's own outcome entry claimed.
The fix persists the resolved policy via ``write_policy_toml`` once the
adapter itself resolves; ``MRS-SPIN-015`` (``Verdict.WARN``, alongside
013/007's identical "reported, never blocks an already-viable launch"
tier) covers the one failure mode that write can still hit -- an
unwritable loop home -- degrading to whatever policy was already on disk
rather than aborting the launch.

Later stories append further real codes here as they gain their own real
callers. The registry MECHANISM (format check, then membership check) is
separately proven via ``monkeypatch``-injected synthetic codes in
``tests/unit/test_findings.py``.

This module is pure data: no I/O, no subprocess, no network, no clock
(AD-4).
"""

from __future__ import annotations

import re

# No ^/$ anchors -- matched with .fullmatch(), not .match(), so a trailing
# newline can never sneak a malformed code past the check (a known Python
# `re` pitfall: `$` alone matches immediately before a trailing "\n"; see
# pyforge-warden's models.py docstring, which calls out this exact gotcha).
# [0-9], never \d: Python's \d matches any Unicode decimal digit, while the
# packaged JSON schema's ECMA-262 pattern treats \d as [0-9] -- spelling
# [0-9] in both keeps the two independent copies behaviorally identical.
CODE_PATTERN = re.compile(r"MRS-[A-Z][A-Z0-9]*-[0-9]{3}")

# Story 1.2's core/identity.py -- the registry's first real registrations.
# Story 1.3's core/policy.py/cli/config.py add the second real caller's six codes.
# Story 1.4's cli/init.py adds the third real caller's four codes.
# Story 1.5's cli/init.py tier3_backlink step adds a fifth code.
# Story 1.6's cli/init.py::run_homes adds the fourth real caller's three codes.
# Story 1.7's cli/init.py::run_preflight adds the fifth real caller's ten codes.
# Story 1.8's cli/init.py::run_teardown adds the sixth real caller's three codes.
# Story 1.9's cli/init.py::run_preflight adds an eleventh code, graduating
# the harness-version check into two tiers.
# Story 2.1's cli/gate.py/core/gate.py add the seventh real caller's five codes.
# Story 2.4's core/gate.py::classify_doc_only_declaration adds a sixth code.
# Story 3.2's core/journal.py::fold adds the eighth real caller's two codes.
# Story 3.3's cli/spin.py adds the ninth real caller's SIX codes (MRS-SPIN-006
# joined 001-005 in review, splitting "launched but its outcome could not be
# journaled" off MRS-SPIN-003's "never launched, safe to retry").
# Story 3.4's cli/spin.py adds a SEVENTH code to the same caller,
# MRS-SPIN-007 (the supervisor sidecar could not be spawned).
# Story 3.5's supervisor/__main__.py adds the tenth real caller's own NEW
# area, MRS-SUPV-* (three codes: nudge-send failure, stop/resume failure,
# harness-run-id-unavailable), and an EIGHTH cli/spin.py code, MRS-SPIN-008
# (the project-policy layer produced findings while resolving the
# supervisor's idle threshold, over an already-live launch).
# Story 3.6's supervisor/__main__.py adds three more MRS-SUPV-* codes
# (budget-warn, budget-stop failure, stale usage evidence), and cli/spin.py
# adds a NINTH code, MRS-SPIN-009 (the FR-14 preflight advisory).
# Story 3.7's supervisor/__main__.py adds a SEVENTH MRS-SUPV-* code,
# MRS-SUPV-007 (the mandatory escalation file-marker write failed), and
# cli/spin.py adds a TENTH, ELEVENTH and TWELFTH code: MRS-SPIN-010 (resume
# refused: unresolved escalation), MRS-SPIN-011 (resume refused: no
# resumable run) and MRS-SPIN-012 (resume proceeding without having been
# able to read the run's live status at all -- added in review).
# Story 3.8's supervisor/__main__.py adds an EIGHTH MRS-SUPV-* code,
# MRS-SUPV-008 (a durability push -- stage-boundary or interval-watcher --
# failed).
# Story 2.3's cli/gate.py/core/gate.py add MRS-GATE-007/008/009 -- the
# table's first SCOPE_VIOLATION classifications (007/008) plus a new
# UNEVALUABLE code for a --scope-check that could not be evaluated at all
# (009). MRS-GATE-005 is REUSED, not replaced, with a broadened meaning
# (see the prose above).
# Story 4.1's cli/deploy.py/core/promotion.py add the eleventh real
# caller's own NEW area, MRS-DEPLOY-* (three codes: missing spec for a
# merged story, invalid/truncated spec, and a commit-history-read or
# promotion-write failure).
# Story 4.2's cli/init.py/cli/deploy.py add two more codes:
# MRS-TEARDOWN-004 (an unreachable-promotion refusal met with --force but
# no/mismatched --abandon) and MRS-DEPLOY-004 (recover-spec found a
# genuinely orphaned key -- no snapshot, no epics.md section).
# Code review (2026-08-06, P1) adds a third MRS-TEARDOWN-* code,
# MRS-TEARDOWN-005 (the AD-29 reachability check itself could not run --
# local main's commit history was unreadable -- an UNDETERMINED state,
# never treated the same as a confirmed-empty one).
# Code review (2026-08-06, P5) adds a fifth MRS-DEPLOY-* code,
# MRS-DEPLOY-005 (recover-spec's epics-derived fallback wrote a recovered
# spec whose Intent and/or Acceptance Criteria came back empty).
# Story 2.7's cli/gate.py/core/gate.py add MRS-GATE-010/011 (missing/
# unparseable Success signal binding; a declared command narrowed or
# removed from policy since tracking) -- both SCOPE_VIOLATION, the same
# rung as MRS-GATE-007/008.
# Story 4.3's cli/deploy.py adds four more MRS-DEPLOY-* codes for
# `marshal deploy land-story`: MRS-DEPLOY-006 (missing/empty
# --justification), MRS-DEPLOY-007 (the station branch could not be
# resolved), MRS-DEPLOY-008 (the merge itself failed), and MRS-DEPLOY-009
# (the post-merge conformance audit could not enumerate its own window).
# Code review (2026-08-06) adds three more MRS-DEPLOY-* codes:
# MRS-DEPLOY-010 (P2: the gate's verdict was not exactly clean),
# MRS-DEPLOY-011 (P4: the station branch's tip moved or could not be
# reconfirmed before merging), and MRS-DEPLOY-012 (P7: --justification
# redaction failed at journal-capture time).
# Story 4.4's cli/deploy.py adds two more MRS-DEPLOY-* codes for
# `marshal deploy batch-pr`: MRS-DEPLOY-013 (an unsatisfied blocking
# hygiene rule) and MRS-DEPLOY-014 (a ForgePort/gh command failure).
# Code review (2026-08-06) adds four more MRS-DEPLOY-* codes for
# `marshal deploy batch-pr`: MRS-DEPLOY-015 (P1: a malformed landing_rules
# policy layer hard-refuses the whole invocation), MRS-DEPLOY-016 (P4: the
# head branch moved between hygiene evaluation and the PR write),
# MRS-DEPLOY-017 (P5: the loop-home worktree's checkout does not match the
# head branch's resolved tip before changed_files is trusted), and
# MRS-DEPLOY-018 (P8: an existing PR's own base branch does not match the
# policy-declared landing_base_branch).
# Story 4.5's cli/deploy.py/core/status.py add two more MRS-DEPLOY-* codes
# for `marshal deploy refresh-feed` (MRS-DEPLOY-019: a landing_resync_
# commands entry could not be run at all; MRS-DEPLOY-020: it ran and exited
# non-zero) plus a new area, MRS-STATUS-* (MRS-STATUS-001: a journal-claimed
# commit_sha for a story git's own merged_story_keys does not confirm).
# Story 4.6's cli/deploy.py adds a twenty-first MRS-DEPLOY-* code,
# MRS-DEPLOY-021 (an open intent from a prior promote/land-story/batch-pr
# invocation has no confirming evidence yet -- WARN, never ERROR, per
# AD-21's own F-17 amendment).
# Code review (2026-08-06, P3) adds a twenty-second MRS-DEPLOY-* code,
# MRS-DEPLOY-022 (the cross-run journal fold itself failed, so
# reconciliation could not be attempted this invocation -- WARN, never a
# silent empty FoldResult).
# Story 4.8's cli/land.py adds the twelfth real caller's own NEW area,
# MRS-LAND-* (seven codes): MRS-LAND-001 (the station branch could not be
# resolved/does not exist), MRS-LAND-002 (a malformed landing_rules policy
# layer), MRS-LAND-003 (an already-landed wave's own branch retirement
# could not be confirmed), MRS-LAND-004 (a fired required_check resolved to
# a real failure or could not be read), MRS-LAND-005 (a fired
# required_check has not concluded yet), MRS-LAND-006 (an unacknowledged
# WARN-tier finding from this run's own evaluation, escalated), and
# MRS-LAND-007 (ForgePort.merge_pr itself failed).
# Story 4.9 (an advisory lock serializes concurrent writes to the shared
# planning-artifacts/specs/ store, AD-42) adds a twenty-third MRS-DEPLOY-*
# code, MRS-DEPLOY-023: run_promote's new FsPort.acquire_advisory_lock call
# could not acquire the lock within timeout_s -- WARN, a clean re-entrant
# refusal (lock_contended: true, promoted: []), never a hard error.
# Story 4.10 (fleet-wide branch retirement, FR-63/AD-47) adds the thirteenth
# real caller's own NEW area, MRS-RETIRE-* (three codes): MRS-RETIRE-001
# (a malformed --project slug) at UNEVALUABLE; MRS-RETIRE-002 (a
# VcsCommandError gathering evidence for one branch, or enumerating the
# fleet) and MRS-RETIRE-003 (a delete_branch failure under --execute, or a
# post-deletion journal-write failure) both at WARN -- never blocking, the
# sweep continues.
# Story 5.1's cli/status.py adds MRS-STATUS-002 (a discovered home's
# journal/state.json couldn't be read far enough, or the fleet enumeration
# itself failed) at WARN.
# Story 5.2 (per-run detail, FR-37/NFR-12) adds MRS-STATUS-003 (--run given
# without --project) at UNEVALUABLE and MRS-STATUS-004 (a run id that does
# not resolve to a real run directory) at WARN; MRS-STATUS-002 is reused,
# broadened to also cover a per-run detail view's own unreadable
# state.json.
# Story 5.4 (ledger-vs-git reconciliation, FR-39/FR-40) adds three more
# MRS-STATUS-* codes: MRS-STATUS-005 (the tracked ledger could not be read)
# at WARN, MRS-STATUS-006 (--reconcile-ledger given without --project) at
# UNEVALUABLE, and MRS-STATUS-007 (main's own commit history could not be
# read while gathering merged_story_keys) at UNEVALUABLE.
# Story 5.5 (durability as a reported fleet-status dimension, FR-62/AD-48)
# adds two more MRS-STATUS-* codes, both WARN: MRS-STATUS-008 (a home's own
# station branch carries local-only content the unpushed_work_check.py
# detector confirmed is not on origin) and MRS-STATUS-009 (that detector
# could not be consulted this run at all -- every row's unpushed_work
# reports null, never fabricated as clean).
# Story 5.6 (marshal check, FR-65/AD-50) adds the fourteenth real caller's
# own NEW area, MRS-CHECK-* (four codes): MRS-CHECK-001 (the detector
# registry -- scripts/detectors.py -- could not be consulted this run at
# all: a subprocess launch failure or unparseable JSON output, mirroring
# MRS-STATUS-009's identical "detector unavailable" precedent) at WARN;
# MRS-CHECK-002 (one detector reported status == "FINDINGS") and
# MRS-CHECK-003 (one registry-self-reported gap -- an undeclared or
# untasked detector) both at ERROR; MRS-CHECK-004 (one detector reported
# status == "unknown", could not run) at UNEVALUABLE.
# Story 6.1 (profile-driven adapter selection, project-scoped, FR-48/FR-51/
# AD-19) adds two more MRS-SPIN-* codes: MRS-SPIN-013 (a resolved story's own
# declared difficulty was malformed -- DifficultyParseError -- treated as
# undeclared, reported) at WARN, and MRS-SPIN-014 (the configured adapter
# name could not be resolved -- HarnessError from adapter_binary) at
# UNEVALUABLE.
# Story 6.2 (skill-tree projection, FR-41, AD-12/AD-36) adds the fifteenth
# real caller's own NEW area, MRS-ADP-* (ten codes): MRS-ADP-001/002
# (malformed --slug / loop home not provisioned, mirroring MRS-SPIN-001/
# 002 exactly) at ERROR; MRS-ADP-003 (the canonical `.claude/skills` tree
# does not exist in the loop home) at ERROR; MRS-ADP-004 (HarnessPort.
# adapter_skill_trees failed -- unimportable bmad_loop or an unreadable
# profile overlay) and MRS-ADP-005 (the resolved platform has no declared
# projection-mechanism table row) both at UNEVALUABLE, mirroring
# MRS-SPIN-014's "Marshal cannot determine" tier; MRS-ADP-006/008 (a
# specific tree's create/repoint or stale-removal I/O failed) both at
# ERROR, isolated per tree; MRS-ADP-007 (a structural conflict -- real
# content occupies a projection path, or an existing symlink points
# somewhere other than canonical -- refused, never destroyed) at WARN;
# MRS-ADP-009/010 (a malformed skill-projection.json manifest / the
# manifest write itself failed) both at WARN, mirroring MRS-SPIN-015's
# "degrades, never blocks an otherwise-viable operation" precedent.
#
# A review pass on Story 6.2 added MRS-ADP-011 (WARN, same "skip this one
# tree, never abort the run" tier as 005/007): an adapter-declared
# skill_tree -- including one from a project-local profile overlay -- that
# is absolute, or that resolves outside the loop home once joined against
# it, is refused rather than projected. Previously `home / Path(rel)` for
# such a value could write a symlink anywhere the process could reach.
#
# Story 6.3 (projection drift detection, FR-42, AD-31/AD-36) adds the
# sixteenth real caller's own ONE new code, MRS-CONFORM-001 (link-target
# identity drift detected for one or more projected trees -- added/removed/
# modified, folded into one code per the MRS-GATE-001 "one code, several
# triggering shapes, same tier" precedent) at ERROR.
#
# A review pass on this same story added MRS-ADP-012 (ERROR: reading a
# tree's own live symlink state failed -- an unsearchable
# ancestor directory, a real, documented `LocalFs` failure mode). Isolated
# per tree (mirrors MRS-ADP-006/008's own "one tree's failure never aborts
# another's" precedent) rather than letting the raw `FsError` propagate
# out of `gather_conformance_findings` -- since that function now runs
# UNCONDITIONALLY as part of `marshal preflight`, an unguarded I/O failure
# here would have crashed the whole preflight command.
# `gather_conformance_findings` (`cli/adapters.py`, shared by the new
# `marshal adapters conform` verb and `marshal preflight`'s own additional
# step) reuses MRS-ADP-001/002/003/004/005/009/011 verbatim for the
# preconditions it shares with `adapters sync` -- the same code, the same
# tier, a second call site, per AD-31's own MRS-DEPLOY-003 precedent ("the
# SAME code two different ways depending on which of its two emit sites
# fired... both fold into this one rung").
#
# Story 6.4 (adapter probe with a machine-scoped record, FR-43, AD-31/AD-34/
# AD-37) adds `cli/adapters.py`'s own `run_adapters_probe` (`marshal
# adapters probe`), reusing MRS-ADP-001/002 verbatim for the preconditions
# it shares with `sync`/`conform` (the SAME MRS-DEPLOY-003 precedent, now a
# THIRD call site), plus four wholly new codes. MRS-ADP-013 (`--adapter` is
# missing/blank, checked before any harness/filesystem touch) classifies
# UNEVALUABLE, the same pre-I/O shape-gate tier as MRS-STATUS-003's own
# "a required companion argument is missing" precedent. MRS-ADP-014
# (`HarnessPort.adapter_probe` raised `HarnessError` -- an unknown adapter
# name or an unimportable `bmad_loop`) classifies UNEVALUABLE, the same
# tier as MRS-SPIN-014's own "an adapter name could not be resolved to a
# real profile" reasoning -- a configuration fact Marshal cannot determine,
# never a real precondition that was checked and failed. MRS-ADP-015
# (writing the machine-scoped probe record failed -- `RecordPort.
# write_redacted_atomic` raised `FsError`) classifies ERROR, the same tier
# as MRS-ADP-006/008's own "a real write was attempted and failed" rung --
# the OBSERVATION itself still succeeded and is still reported in
# `data.probe`; only the durable write is what failed. MRS-ADP-016 (a
# pre-existing `adapter-probes.json` was malformed JSON or not a JSON
# object) classifies WARN, the same "malformed bookkeeping degrades to
# empty, never blocks" tier MRS-ADP-009 already established for the
# skill-projection manifest -- this probe's own fresh entry still writes.
# Deliberately, `binary_present is False` (the AC's own "unavailable")
# registers NO finding at all: `data.probe.status == "unavailable"` with an
# empty findings list folds to `Verdict.CLEAN`, exit 0 -- the AC's own
# "reports it as unavailable and exits 0", read literally. The DIFFERENT
# reading ("unevaluable anywhere a run depends on it", AD-31) is already
# satisfied by the SHIPPED `MRS-PREFLIGHT-004` (a run-dependent call site
# reporting the identical real-world fact at `Verdict.ERROR`) -- see the
# story's own spec Design Notes for why this needed no new code.
#
# Story 6.5 (conformance smoke in an ephemeral home, FR-44/AD-37) adds
# `cli/adapters.py`'s own `run_adapters_smoke` (`marshal adapters smoke`) --
# a NEW area, `MRS-SMOKE-*`, never reusing `MRS-ADP-001`/`002` (this verb
# provisions its OWN throwaway home rather than operating on an existing
# project's, so the slug-shape/home-provisioned preconditions those two
# codes name simply do not apply the same way here). MRS-SMOKE-005 (a
# missing/blank `--adapter`, checked before any I/O) classifies
# UNEVALUABLE, the same pre-I/O shape-gate tier MRS-ADP-013 already
# established. MRS-SMOKE-001 (`HarnessPort.run_smoke` raised `HarnessError`
# -- an unknown adapter name or an unimportable `bmad_loop`) classifies
# UNEVALUABLE, mirroring MRS-ADP-014's identical reasoning. MRS-SMOKE-002
# (ephemeral-home provisioning failed -- a git/filesystem operation) and
# MRS-SMOKE-003 (the smoke's own status is `"fail"`, naming the failing
# stage) both classify ERROR, the same "a real operation was attempted and
# failed, or real drift/failure was detected" tier MRS-ADP-002/
# MRS-CONFORM-001 already established. MRS-SMOKE-006 (writing the
# machine-scoped smoke record failed) classifies ERROR, mirroring
# MRS-ADP-015 verbatim -- the OBSERVATION itself still succeeded and is
# still reported in `data.smoke`; only the durable write is what failed.
# MRS-SMOKE-004 (teardown of the ephemeral home failed -- residue left
# behind) and MRS-SMOKE-007 (a pre-existing `adapter-smoke.json` was
# malformed) both classify WARN, the same "degrades, never blocks, the
# primary observation already succeeded" tier MRS-ADP-009/016 already
# established -- a teardown failure NEVER overrides the smoke's own
# already-computed pass/fail/unavailable verdict (AD-31: the context lives
# in the code, and cleanup is a different fact from the smoke's own
# result). Deliberately, `binary_present is False` (the AC's own
# "unavailable") registers NO finding at all -- the SAME "read-only
# reporting surface, never a run precondition" tier MRS-ADP-013/014's own
# sibling verb (`adapters probe`) already established for the identical
# real-world fact.
REGISTERED_CODES: frozenset[str] = frozenset(
    {
        "MRS-IDENT-001",
        "MRS-IDENT-002",
        "MRS-POLICY-001",
        "MRS-POLICY-002",
        "MRS-POLICY-003",
        "MRS-POLICY-004",
        "MRS-POLICY-005",
        "MRS-POLICY-006",
        "MRS-INIT-001",
        "MRS-INIT-002",
        "MRS-INIT-003",
        "MRS-INIT-004",
        "MRS-INIT-005",
        "MRS-HOMES-001",
        "MRS-HOMES-002",
        "MRS-HOMES-003",
        "MRS-PREFLIGHT-001",
        "MRS-PREFLIGHT-002",
        "MRS-PREFLIGHT-003",
        "MRS-PREFLIGHT-004",
        "MRS-PREFLIGHT-005",
        "MRS-PREFLIGHT-006",
        "MRS-PREFLIGHT-007",
        "MRS-PREFLIGHT-008",
        "MRS-PREFLIGHT-009",
        "MRS-PREFLIGHT-010",
        "MRS-PREFLIGHT-011",
        "MRS-TEARDOWN-001",
        "MRS-TEARDOWN-002",
        "MRS-TEARDOWN-003",
        "MRS-GATE-001",
        "MRS-GATE-002",
        "MRS-GATE-003",
        "MRS-GATE-004",
        "MRS-GATE-005",
        "MRS-GATE-006",
        "MRS-JOURNAL-001",
        "MRS-JOURNAL-002",
        "MRS-SPIN-001",
        "MRS-SPIN-002",
        "MRS-SPIN-003",
        "MRS-SPIN-004",
        "MRS-SPIN-005",
        "MRS-SPIN-006",
        "MRS-SPIN-007",
        "MRS-SPIN-008",
        "MRS-SPIN-009",
        "MRS-SUPV-001",
        "MRS-SUPV-002",
        "MRS-SUPV-003",
        "MRS-SUPV-004",
        "MRS-SUPV-005",
        "MRS-SUPV-006",
        "MRS-SUPV-007",
        "MRS-SPIN-010",
        "MRS-SPIN-011",
        "MRS-SPIN-012",
        "MRS-SUPV-008",
        "MRS-GATE-007",
        "MRS-GATE-008",
        "MRS-GATE-009",
        "MRS-DEPLOY-001",
        "MRS-DEPLOY-002",
        "MRS-DEPLOY-003",
        "MRS-GATE-010",
        "MRS-GATE-011",
        "MRS-TEARDOWN-004",
        "MRS-DEPLOY-004",
        "MRS-TEARDOWN-005",
        "MRS-DEPLOY-005",
        "MRS-DEPLOY-006",
        "MRS-DEPLOY-007",
        "MRS-DEPLOY-008",
        "MRS-DEPLOY-009",
        "MRS-DEPLOY-010",
        "MRS-DEPLOY-011",
        "MRS-DEPLOY-012",
        "MRS-DEPLOY-013",
        "MRS-DEPLOY-014",
        "MRS-DEPLOY-015",
        "MRS-DEPLOY-016",
        "MRS-DEPLOY-017",
        "MRS-DEPLOY-018",
        "MRS-DEPLOY-019",
        "MRS-DEPLOY-020",
        "MRS-STATUS-001",
        "MRS-DEPLOY-021",
        "MRS-DEPLOY-022",
        "MRS-LAND-001",
        "MRS-LAND-002",
        "MRS-LAND-003",
        "MRS-LAND-004",
        "MRS-LAND-005",
        "MRS-LAND-006",
        "MRS-LAND-007",
        "MRS-DEPLOY-023",
        "MRS-RETIRE-001",
        "MRS-RETIRE-002",
        "MRS-RETIRE-003",
        "MRS-STATUS-002",
        "MRS-STATUS-003",
        "MRS-STATUS-004",
        "MRS-STATUS-005",
        "MRS-STATUS-006",
        "MRS-STATUS-007",
        "MRS-STATUS-008",
        "MRS-STATUS-009",
        "MRS-CHECK-001",
        "MRS-CHECK-002",
        "MRS-CHECK-003",
        "MRS-CHECK-004",
        "MRS-SPIN-013",
        "MRS-SPIN-014",
        "MRS-SPIN-015",
        "MRS-ADP-001",
        "MRS-ADP-002",
        "MRS-ADP-003",
        "MRS-ADP-004",
        "MRS-ADP-005",
        "MRS-ADP-006",
        "MRS-ADP-007",
        "MRS-ADP-008",
        "MRS-ADP-009",
        "MRS-ADP-010",
        "MRS-ADP-011",
        "MRS-CONFORM-001",
        "MRS-ADP-012",
        "MRS-ADP-013",
        "MRS-ADP-014",
        "MRS-ADP-015",
        "MRS-ADP-016",
        "MRS-SMOKE-001",
        "MRS-SMOKE-002",
        "MRS-SMOKE-003",
        "MRS-SMOKE-004",
        "MRS-SMOKE-005",
        "MRS-SMOKE-006",
        "MRS-SMOKE-007",
    }
)


class UnregisteredFindingCodeError(ValueError):
    """Raised when a ``Finding`` is constructed with a code that either does
    not match ``CODE_PATTERN`` or is not a member of ``REGISTERED_CODES``."""


def require_registered(code: str) -> str:
    """Return ``code`` unchanged if it is well-formed AND registered; raise
    ``UnregisteredFindingCodeError`` otherwise. Format is checked first -- a
    malformed code fails before the membership check ever runs."""
    if not CODE_PATTERN.fullmatch(code):
        raise UnregisteredFindingCodeError(
            f"malformed finding code {code!r} -- expected MRS-<AREA>-<NNN>"
        )
    if code not in REGISTERED_CODES:
        raise UnregisteredFindingCodeError(
            f"unregistered finding code {code!r} -- not in REGISTERED_CODES"
        )
    return code
