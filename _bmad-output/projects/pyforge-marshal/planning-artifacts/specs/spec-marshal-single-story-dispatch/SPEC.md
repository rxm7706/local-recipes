---
id: SPEC-marshal-single-story-dispatch
spec: marshal-single-story-dispatch
status: ready
owner-dream: docs/dreams/marshal-single-story-dispatch.md
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/main.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/
companions:
  - fleet-drain-playbook.md
sources:
  - ../../../../../../docs/dreams/marshal-single-story-dispatch.md
related:
  - ../../../../../../docs/dreams/dashboard-velocity-captures-hand-driven-work.md
open_questions:
  - "Exact verb naming (`marshal factory dispatch` vs a `marshal dev` family) — converges with PRD Q-15's open verb-naming question; not decided here."
  - "Concrete launch mechanism for a headless bmad-dev-auto session (binary / adapter profile) — must preserve the plain-agent requirement (bmad-dev-auto's mandatory subagents break inside a fork)."
  - "What budget signal is actually enforceable on a dispatched session, given the loop's own token cap is known not to enforce."
  - "Whether the cross-station disjointness advisory compares declared frozen surfaces only, or also live diff surfaces."
  - "Whether completion detection needs a dedicated sidecar (Story 3.4 shape) or the existing supervisor generalizes to a second engine."
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> to build, test, and validate. `docs/dreams/marshal-single-story-dispatch.md` is listed in
> `sources:` for narrative rationale this contract intentionally omits.

# Single-story dispatch is a marshal verb, not a session's discipline

## Why

A pain to solve and an opportunity to capture. The fastest story-landing pattern the factory
has ever run is a hand-performed ritual: one story per fresh, worktree-isolated
`bmad-dev-auto` agent; wait for *real* completion; independently verify (run the tests, read
the diff, invoke the live CLI); land through a PR; only then dispatch the next. On 2026-08-21
it landed **22 stories across four stations in one session** where the preceding
`marshal factory spin` pass had stalled near one story per station. The speed is structural:
the pattern sidesteps the orchestrator layer where every documented bmad-loop failure lives
(stuck-orchestrator baseline drift, feed-reports-intent-as-fact, invisible interactive-prompt
stalls, the worktree path-length panic, the ~600 s watchdog killing a busy-waiting parent) and
adds the one step no self-report supplies — independent verification, which caught two
live-reproducible leaks in a story that had already marked itself shipped (doctor 12.3).

Run by hand, the pattern has exactly the weaknesses bmad-loop does not: it dies with the
operating session, has no budget ceilings, no resumable journal, no escalation protocol, no
`changes.patch` safety net, and its rigor is discipline, not machinery. Marshal already owns
every piece except the driver: Epic 1 provisions isolated homes, Epic 2 provides runnable
gates, Epic 4 owns landing and the one-pusher rule, Story 5.9 (FR-186) makes non-loop
completions ledger-visible (label `not-loop-native`, sharpened by FR-187's detectable merge
subject), Epic 5 + `fleet-picture` report per-station state, and Epic 15 mechanizes the
surrounding rituals. No FR in FR-1..FR-191 covers a verb that launches, awaits, or judges a
single-story dev-auto session — `marshal factory` today is `spin`/`attach`/`resume`,
bmad-loop only. This spec is that missing driver: marshal's deterministic governance wrapped
around the dispatch pattern's speed and verification honesty.

**Wrap-vs-absorb, named honestly (the Dream's decision 3).** The PRD resolved Q-1 as
**"wrap and supervise"** (§5.3: *"`marshal` is thin porcelain over `bmad-loop` … plus a
supervisory layer that owns everything the loop's core does not"*), with §5.2's finding that
every known gap lives *outside* the dev/verify/review/commit engine. This capability replaces
the bmad-loop *orchestrator layer* for the single-story case — the layer where the documented
bugs live — while the engine of a dispatched story remains external (`bmad-dev-auto`, a BMAD
skill marshal does not own or modify). That is the §5.3 doctrine extended to a second
external engine, not a revision of it: the supervisor is still the product, marshal still
contains no dev/verify/review/commit engine, and the escape-hatch economics (FR-52
single-seam) carry over. **The PRD decision stands; dispatch is bounded as a sibling launch
mode beside `spin`, never a replacement.**

## Capabilities

- **CAP-1**
  - **intent:** An operator (or a fleet driver acting for one) can launch exactly one story
    on a station as a fresh, worktree-isolated `bmad-dev-auto` session under marshal
    governance: policy-composed budget ceilings and model tier, `BMAD_ACTIVE_PROJECT` passed
    per-invocation with physical artifact paths (never `bmad-switch`), and a journaled launch
    with intent/outcome discipline (AD-25/AD-28/AD-30).
  - **success:** Dispatching a backlog story provisions a fresh isolated worktree, launches
    the session detached, journals the launch, and the run appears in `marshal status` /
    `fleet-picture`; the launched session demonstrably receives the pinned project scope and
    the policy-resolved model/budget parameters.
- **CAP-2**
  - **intent:** The driver judges a dispatched session's completion or failure from git facts
    (AD-33: commits on the story branch, merge refs) plus running-process facts — never from
    harness notifications, session self-reports, or busy-wait polling filler.
  - **success:** Two motivating traps are regression-pinned: (a) the driver awaiting a
    long-running nested review is never watchdog-killed, because no foreground path
    busy-waits — awaiting is a detached supervisor's job (Story 3.4 precedent); (b) a session
    that emits a killed/failed notification while git facts show live progress is treated as
    live: a redispatch of the same story is refused, naming the evidence — the observed
    near-duplicate ("dead" agent landed two stories after its failure notification) cannot
    recur.
- **CAP-3**
  - **intent:** Verification is the product: before any landing, the driver itself runs the
    story's real verify commands via Epic 2's standalone gate objects and reads the diff
    surface against the story's frozen surface — the session's self-report is input, never
    the verdict (never-false-green lattice; unevaluable ≠ pass).
  - **success:** A story whose session self-reports shipped but whose gates fail or whose
    diff exceeds its frozen surface ends in a loud non-landing verdict naming the failed gate
    — the doctor-12.3 shape (self-marked shipped, two live-reproducible leaks) is the
    canonical refusal fixture; no landing occurs on self-report alone in any test path.
- **CAP-4**
  - **intent:** A verified story lands through the existing Epic 4 machinery — `marshal
    land`/`deploy land-story` semantics, FR-187's detectable merge subject, Story 4.1 spec
    promotion, Epic 15's ledger promotion — composition of shipped verbs, never a second
    landing/promotion path. **Merge-in-agent (2026-08-23):** the dispatch driver (or
    coordinating finalize step) merges with `gh pr merge --merge` when CI is green, then
    scoped `sprint-ledger-sync --project <station>` and spec promotion — never `--squash`.
  - **success:** A dispatch-landed story is classified marshal-native by
    `marshal_native_merged_keys` (it never falls into FR-186's `not-loop-native` bucket), its
    spec is durably promoted, and its ledger key advances — with zero new landing or
    promotion code paths introduced.
- **CAP-5**
  - **intent:** One story in flight per station, enforced: the driver refuses a second
    dispatch onto a station whose in-flight story (judged by CAP-2's facts) has not
    completed. Dispatches onto different stations may run concurrently — the cross-project
    plane spec-horizontal-run-concurrency explicitly excludes from FR-184's in-loop
    `max_parallel` clamp. Cross-station surface disjointness is advisory: a detectable
    overlap between in-flight stories' declared frozen surfaces is reported loudly, never
    silently, but the operator is trusted to proceed.
  - **success:** A second dispatch to a busy station is refused naming the in-flight story;
    dispatches to two stations proceed concurrently; an overlap between two in-flight
    declared surfaces produces the advisory; FR-184's clamp posture is untouched by any of
    it.
- **CAP-6**
  - **intent:** The dispatched run survives its operator: detached-by-default (AD-22
    precedent), its own journal, and an attach/resume path. Death of the driver, the
    terminal, or the operating session orphans nothing invisibly; a failed or abandoned
    session's worktree and diff survive for recovery (Epic 1's teardown-refuses-to-destroy-
    work discipline — the `changes.patch`-analog the hand-run pattern lacked); and the
    per-story session record (start/end, baseline→final revisions) makes dispatch the
    natural producer of the per-story effort signal the dashboard-velocity Dream consumes.
  - **success:** Killing the terminal that issued the dispatch leaves the session running; a
    fresh `marshal status` reports it from journal + process facts alone; attach/resume
    recovers supervision; a story that completed while unsupervised is reconciled from git
    facts rather than lost; the journal carries per-story timing a downstream consumer can
    read without new instrumentation.
- **CAP-7**
  - **intent:** Fleet-wide drain across all eight pyforge stations is a marshal-orchestrated
    mode: read per-station ordered backlogs (from tracked ledgers + optional overrides),
    apply campaign mode (`drain_to_zero`, `leave_one`, `skip_on_blocked` policies), preflight
    each dispatch (CAP-2 zombie refusal), launch one story per station in parallel (CAP-5),
    and chain the next story when merge-through-finalize completes (CAP-4 with merge-in-agent:
    merge when CI green, scoped `sprint-ledger-sync`, spec promotion, queue regen).
  - **success:** An operator runs one documented command (provisional: `marshal factory
    dispatch --fleet` or `marshal drain`) and the eight-station 2026-08-22/23 hand ritual
    replays without session discipline; interim acceptance oracle is
    `fleet-drain-playbook.md` + `.cursor/pyforge-fleet-drain/` until the verb ships.

## Constraints

- **HARD:** PRD Q-1 (§5.3 wrap-and-supervise) is not revised. Dispatch is a sibling launch
  mode beside `factory spin`/`resume` — it never replaces, deprecates, or gates bmad-loop,
  and the dispatched story's engine (`bmad-dev-auto`) stays external and unmodified (FR-186
  precedent: the skill gains no marshal dependency).
- **Always:** completion and liveness verdicts derive from git facts (AD-33) plus process
  facts; notifications and self-reports are input, never verdicts.
- **Always:** no foreground path busy-waits on a session; waiting is owned by a detached
  supervisor.
- **Always:** every call into the session harness goes through one adapter seam (FR-52's
  single-seam discipline extended to the second engine) — never scattered subprocess calls.
- **Always:** dispatched sessions receive `BMAD_ACTIVE_PROJECT` per-invocation and write
  through physical artifact paths; `scripts/bmad-switch` is never invoked by the driver or
  its sessions (standing HARD rule).
- **Always:** composition, not reimplementation — Epic 1 provisioning, Epic 2 gates, Epic 4
  landing + FR-187 subject, Story 4.1/Epic 15 promotion are reused as shipped; no parallel
  gate, landing, or promotion implementation.
- **Always:** FR-184's in-loop `max_parallel` clamp stays untouched; the driver's
  concurrency lives only on the cross-project plane.

## Non-goals

- **Not** a bmad-loop replacement, fork, or absorption — and not a change to the vendored
  `bmad_loop` package on any timeline.
- **Not** backlog orchestration: the unit of dispatch is exactly one story; handing one
  agent a whole backlog is the documented anti-pattern this verb exists to retire.
- **Not** the dashboard display work of
  `docs/dreams/dashboard-velocity-captures-hand-driven-work.md` (specified in parallel) —
  this spec produces the per-story session/timing signal; rendering it is that Dream's
  scope.
- **Not** in-loop concurrent story fan-out — FR-184 stays parked until upstream Phase 5
  ships.
- **Not** a change to `bmad-dev-auto` or `bmad-quick-dev` themselves.

## Success signal

The 2026-08-21 session is replayable as machinery: an operator issues one dispatch per
station across four stations; each story runs isolated, is judged complete from git and
process facts, is independently gate-verified, and lands with a detectable merge subject,
promoted spec, and advanced ledger — while a story that self-reports shipped with failing
gates is loudly refused. Killing the operator's terminal mid-run orphans nothing: the runs
survive, report, and reconcile. The ritual's rigor no longer depends on which session
remembers it.

**Fleet drain (2026-08-22/23):** the eight-station campaign (marshal + steward backlog drain;
six stations already at zero) validated CAP-7 operational semantics in
`fleet-drain-playbook.md`. Epic 22.1+ must subsume `.cursor/pyforge-fleet-drain/` as marshal
verbs and in-repo queue state under `pyforge-marshal` (not session-local `.cursor/`).

## Assumptions

- Verb naming (`marshal factory dispatch` vs a `marshal dev` family) is deliberately left to
  PRD Q-15's verb-naming resolution; this spec binds behavior, not the name.
- The session harness is the agent-CLI pattern validated at N=22 — a plain background agent,
  never a fork-style subagent (bmad-dev-auto's mandatory subagents break inside a fork);
  generality across other adapters inherits Epic 6's portability posture and is not
  re-proven here.
- Whether dispatch-landed stories get a distinct completion-path label beyond marshal-native
  classification is a story-level design decision.
- Escalation reuses Story 3.7's escalate/defer/resume shapes unless a downstream story shows
  a reduced ladder suffices.

## Open Questions

- Exact verb naming (`marshal factory dispatch` vs a `marshal dev` family) — converges with
  PRD Q-15; not decided here.
- Concrete launch mechanism for a headless `bmad-dev-auto` session (binary / adapter
  profile) — must preserve the plain-agent requirement.
- What budget signal is actually enforceable on a dispatched session, given the loop's own
  token cap is known not to enforce.
- Whether the cross-station disjointness advisory compares declared frozen surfaces only, or
  also live diff surfaces.
- Whether completion detection needs a dedicated sidecar (Story 3.4 shape) or the existing
  supervisor generalizes to a second engine.
