# Readiness assessment: Marshal's N-stories-in-flight machinery (Story 3.13)

**Status:** written 2026-08-12, a scoped starting point -- **not a readiness certification.**
No FR asks for concurrent story dispatch to ship, and nothing in this document claims it does.
**Owner station:** Marshal (the harness this concerns is `bmad-loop`'s own unbuilt Phase 5
parallel-fan-out scheduler; see `upstream-register.json`'s `parallel-fan-out` entry).
**Disposition:** read-only assessment. Nothing under `src/` was designed or changed by this
document -- `core/policy.py`'s `max_parallel` seed key and `MRS-POLICY-007` advisory (this
story's other half) are the only code changes Story 3.13 makes, and neither depends on any
conclusion below.

---

## Purpose

`bmad_loop==0.9.0`'s own `scm.max_parallel` knob is inert: direct read of the vendored package
confirms Phase 5 parallel fan-out "is not built yet" (`policy.py:448-451`) and every requested
value is clamped to 1 unconditionally (`policy.py:815-817,841-842`). Nothing about that will
change from Marshal's side -- Marshal wraps, it does not absorb (AD-2), and this story explicitly
never touches the vendored package or claims concurrent dispatch ships now.

What Marshal's *own* side of the story can usefully do today is ask: if an upstream scheduler
*did* ship tomorrow, which of Marshal's own N-stories-in-flight-adjacent machinery would already
tolerate it, and which would need real work first? This document answers that for the four areas
epics.md's own AC names -- worktree isolation, the journal's multi-writer design, the supervisor,
and the landing path -- each read directly against the current source, never inferred from
memory or from what the machinery was *intended* to eventually support.

## Method

Every claim below cites the file and line(s) it was read from in this checkout. No code was
written, run, or modified to produce this assessment; it is a source read, not an experiment.
Where a claim could not be settled by reading Marshal's own source (e.g., what `bmad_loop`
itself does internally with two worktrees), that is stated explicitly as unverified rather than
guessed at.

## Findings by area

### 1. Worktree isolation

**What Marshal owns.** `cli/init.py::run_init` provisions **one git worktree per project slug**
(a "station"): "provisions an isolated loop home: a git worktree at `<loop-home-root>/<slug>` on
branch `loop/<slug>`" (`cli/init.py:2-3`). This is per-*project*, not per-*story* -- a single
provisioned loop home is where every story for that project's sprint gets dispatched from, one
`marshal factory spin` invocation at a time (see § 3). Cross-project isolation is checked
structurally: `marshal homes` (`MRS-HOMES-001/002`) verifies each home's own marker/symlink/
branch-derived-slug agreement and Tier-3 backlink realpath, so two *different* projects' loop
homes cannot silently collide on the same paths.

**What is delegated to `bmad_loop`.** Marshal's own rendered `.bmad-loop/policy.toml` sets
`isolation = "worktree"` and `branch_per = "story"` (`adapters/harness_bmadloop.py:309-310`) --
this is the repo-wide override that tells the harness to check out each story's own working
branch into its own worktree *underneath* Marshal's single per-project loop home, rather than
reusing one shared working tree across stories. That per-story worktree creation, and whatever
sequencing or concurrency governs how many of them exist and are actively worked at once, is
entirely `bmad_loop`'s own internal concern -- Marshal never creates, lists, or reasons about a
per-*story* worktree directly.

**Verdict: HOLDS for what Marshal owns (per-project isolation); UNVERIFIED for what it delegates.**
Whether `bmad_loop` 0.9.0 ever runs two `branch_per: story` worktrees concurrently today, or
strictly sequentially (which the very existence of the `max_parallel` clamp strongly suggests --
a scheduler that already ran stories concurrently would have little reason to gate that on an
unbuilt "Phase 5"), was not settled by this assessment: it would require reading `bmad_loop`'s
own dispatch loop, which is out of this story's Never bullet ("touch the vendored `bmad_loop`
package"). Treat "sequential today" as the working assumption implied by the clamp's own existence,
not as something this document independently confirmed.

### 2. Journal multi-writer design

**The mechanism.** `ports/fs.py::append_line` is AD-30's one serialized append protocol: "a
single `os.write()` on an `O_APPEND`-opened descriptor with no buffered stream held open, so two
uncoordinated writers can never interleave a partial line" (`ports/fs.py:57-60`). The composite
`(writer_id, counter)` entry id is deliberately per-*writer*, never per-*run* -- "AD-30 mandates a
lock-free `O_APPEND` protocol with two concurrent writers by design... no coordination-free way
exists to mint a unique per-run integer" (`core/journal.py:13-16`).

**The design's own stated goal is two writers, not N.** The architecture spine is explicit:
"AD-30 mandates a lock-free protocol -- one `os.write()` on `O_APPEND`, no coordination primitive
-- with **two concurrent writers by design**" (architecture.md:301), and AD-30's own "Prevents"
clause names them concretely: "a long-lived buffered supervisor writer interleaving a partial line
with a short-lived CLI append" (architecture.md:320). `ports/fs.py` calls this out directly too:
"The journal's own two-writer case (`append_line` above)... " (`ports/fs.py:73`). The two roles
are the supervisor (long-lived, one heartbeat tick at a time) and one CLI session (short-lived,
one invocation's worth of intent/outcome entries) -- not N independently-dispatched per-story
sessions.

**The mechanism is proven safe well beyond that stated goal.** `tests/unit/test_fs_local.py`'s
`test_append_line_is_safe_under_concurrent_writers` (lines 633-678) runs **9 real threads**
concurrently against the same file -- one long-lived writer (200 lines) plus 8 short-lived writers
(15 lines each) -- and asserts zero malformed lines and zero `(writer_id, counter)` collisions
across all 320 appends. A companion test (`test_append_line_is_safe_under_concurrent_writers_near_the_sidecar_threshold`,
lines 681-720) repeats the proof with 6 writers at near-4KiB line sizes. Both prove the physical
append primitive itself does not care how many writers there are.

**But no caller mints N per-story writer_ids within one run today.** Grepping every real
`writer_id=`/`_writer_id()` call site in the tree: `cli/spin.py::_writer_id()` (line 750) is
called exactly once per `run_spin`/`run_resume` invocation (lines 1494 and 1972 respectively) --
one writer_id for the *whole launched run*, covering however many stories that run's own selector
resolved, not one per story. `supervisor/__main__.py:839` mints exactly one writer_id per
supervisor *process* (`f"supervisor-{os.getpid()}"`) -- one supervisor per watched run (see § 3).
`cli/deploy.py`/`cli/land.py`/`cli/retire.py`/`cli/init.py` each mint one writer_id per their own
single CLI invocation. None of these loops per selected story key.

**Verdict: mechanism HOLDS well past its design goal; the N-writer CALLER does not exist yet.**
The `O_APPEND` primitive and the `(writer_id, counter)` identity scheme are proven safe for far
more concurrent writers than the design ever required (9, tested, against a stated goal of 2).
Nothing here would need to change for N-stories-in-flight to journal safely. What is genuinely
absent is any Marshal-side code that would mint N *distinct* writer_ids for N concurrent
per-story sessions within one run -- that caller has no reason to exist while `max_parallel`
clamps to 1, and would be new work, not a gap in the proven mechanism.

### 3. Supervisor

**One process, one watched run.** `supervisor/__main__.py::run_supervisor`'s own signature is
`(home, slug, run_id, watched_pid, log_path, ...)` (`supervisor/__main__.py:622-626`) -- every
argument is scoped to exactly one run and one watched PID. `cli/spin.py`'s own docstring confirms
the spawn shape: `run_spin`'s order-of-operations names `ProcessPort.spawn_detached` the
supervisor sidecar "as the LAST step, whether or not the outcome append itself succeeded"
(`cli/spin.py:41-43`), and Story 3.4's own paragraph spells out exactly what that launches:
"`spawn_detached` launches `python -m pyforge.marshal.supervisor <home> <slug> <run_id>
<spin_result.pid> <supervisor_log>` detached" (`cli/spin.py:48-50`) -- one sidecar process spawned
per successful spin invocation, watching that invocation's one `harness.spin()` PID.

**No registry of live supervisors, and no concurrent-spin guard.** `run_spin`'s own precondition
chain (`cli/spin.py:1166-1466`, `MRS-SPIN-001` slug shape, `MRS-SPIN-002` loop home provisioned,
`MRS-SPIN-005` story feed readable) checks nothing about whether another `marshal factory spin`
is already running against the *same* loop home. Nothing in this tree maintains a registry of
which loop homes currently have a live supervisor attached, and no lock prevents two overlapping
`spin` invocations against one home.

**Verdict: HOLDS for 1:1 supervision; UNVERIFIED/blocking for N-in-flight.** The supervisor's own
process model is sound for exactly what it does today -- one process, one watched PID, one idle
ladder, one budget-ceiling tracker. It has no notion of "N supervised runs for one project" at
all: N concurrent per-story sessions would need N separate supervisor processes (mechanically
possible -- nothing in `run_supervisor`'s own signature assumes it is the only one), but there is
currently no code path that spawns more than one per `spin` invocation, and no coordination layer
that would stop two independently-spawned supervisors (or two overlapping `spin` invocations)
from targeting the same loop home. This is real, not-yet-built work, not a design flaw in the
existing 1:1 case.

### 4. Landing path

**One wave, one PR, per invocation.** `marshal land` (Story 4.8, FR-60) "takes one project's wave
from ... " (`cli/land.py:1`) and batches every currently-gated, durably-landed story key into one
PR update per invocation (`run_land`'s wave-discovery/wave-keys logic, `cli/land.py:344-520`).
Multiple stories landing in the same run is already the normal, tested case -- this is the one
area of the four where "more than one story handled per invocation" already ships.

**What is NOT coordinated: multiple invocations of `land` itself.** Two mechanisms exist, and
both are explicitly best-effort, not locks:

- `_promote_deferred_work` (`cli/land.py:1050-1142`) acquires an advisory lock on the shared,
  git-tracked deferred-work ledger before promoting a landing story's Tier-3 followups
  (`MRS-LAND-010`, `Verdict.WARN` on contention or a commit failure) -- this guards one specific
  shared *file*, not the landing operation as a whole, and failing to acquire it never blocks the
  landing itself (the promotion step is simply skipped and retried next run).
- The merge itself is closed atomically **forge-side** via `gh pr merge --match-head-commit`
  (`adapters/forge_gh.py:318-327`, invoked from `cli/land.py:946-952`) -- this prevents merging a
  stale head, but says nothing about whether the branch being merged is still actively in use by
  a live `bmad-loop` run.

**The gap is named in the code itself, not inferred.** `cli/land.py:902-912`'s own comment, on
the branch-retirement liveness check: "there is no equivalent atomic primitive for 'this branch's
run is still live' -- true closure needs a cross-process lock between `land` and the bmad-loop
supervisor, out of this story's scope." That lock does not exist anywhere in this tree today; the
liveness check that precedes it (`is_run_live`, `cli/land.py:913-944`) is a check-then-act read
of the same facts `marshal status` gathers, deliberately left open per that same comment.

**Verdict: HOLDS for one-wave-per-invocation batching and forge-side merge atomicity; UNVERIFIED/
blocking for cross-invocation and land↔supervisor coordination.** `marshal land` already handles
"more than one story at once" cleanly within a single invocation. What remains genuinely open,
by the code's own admission, is coordinating *across* invocations (no fleet-wide lock preventing
two concurrent `land` runs against different or the same project) and coordinating `land` against
a still-live supervised run (the named, scoped-out cross-process lock).

## Overall verdict

Two of the four areas (the journal's append mechanism, and `marshal land`'s one-wave-per-invocation
batching) already tolerate more concurrency than they are asked to handle today. The other two
(the supervisor's 1:1 process model, and the land↔supervisor liveness lock) have real, acknowledged
gaps that would need new code before N-stories-in-flight could be supervised or landed safely --
neither is a defect in what exists, both are simply not-yet-built. Worktree isolation HOLDS on
Marshal's own half and is UNVERIFIED on the half `bmad_loop` owns.

None of this is blocking anything today: `max_parallel` clamps to 1 in the wrapped harness
regardless of what this assessment concludes, so no real concurrent dispatch is possible from
Marshal's side even if every gap above were closed tomorrow. This document is a scoped starting
point for whenever `bmad_loop` ships a real Phase 5 scheduler -- not a promise that one is coming,
and not a certification that Marshal is "ready" for it.

## Provenance

Written 2026-08-12 as part of Story 3.13 ("The parallel-fan-out clamp is surfaced, not silent",
FR-184). Every citation was re-verified against this checkout's own source at time of writing,
not carried over verbatim from the story spec's approximate line numbers.
