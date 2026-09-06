---
id: SPEC-marshal-single-story-dispatch
spec: marshal-single-story-dispatch
status: in-progress
updated: "2026-09-02"  # CAP-11 added (done-spec must not review-loop). Steward 41.2 / mason 13.2 incidents. Decomposed as Epic 29.
owner-dream: docs/dreams/marshal-single-story-dispatch.md
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/main.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - .claude/skills/bmad-build-auto/step-01-clarify-and-route.md
  - .claude/skills/bmad-build-auto/step-04-review.md
  - .claude/skills/bmad-build-auto/spec-template.md
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
- **CAP-8** *(added 2026-08-27 — motivated by the live fleet-drain failure of the same
  date: all three real dispatches, atlas/mason/marshal, died instantly on the hardcoded
  `cursor agent` harness's `Authentication required` wall while `binary_present()` reported
  the harness available)*
  - **intent:** The session-harness layer is adapter-plural and profile-driven: an ordered
    `harness_preference` policy key (4-layer composable, machine preference expressible in
    `_bmad-output/policy-defaults.toml`) selects among declarative marshal-owned CLI
    profiles (`claude`, `cursor`, `gemini`, `copilot`, `devin`, extensible via a repo
    overlay) — each declaring binary, argv template (worktree/prompt/trust-flag shape),
    per-CLI model-flag spelling, and a cheap non-interactive authcheck (or a documented
    reason none exists). Resolution takes the first profile whose binary resolves AND whose
    authcheck passes; every skipped candidate is a structured finding, never silent. The
    ONE policy preference drives BOTH engines: `marshal factory dispatch` launches the
    resolved profile directly, and bmad-loop's rendered `policy.toml` derives
    `[adapter].name` from the same preference (translated to bmad-loop's own adapter
    names; a preference with no bmad-loop counterpart renders the default and reports it).
    Mirrors bmad-loop's declarative-profile pattern in marshal's own code — AD-3 stands
    (no `bmad_loop` import outside `harness_bmadloop.py`), and FR-52's single-seam
    discipline stands (binary invocation stays confined to the adapter module).
  - **success:** With cursor unauthenticated and claude authenticated, a dispatch launches
    under the claude profile and reports the cursor skip by name; with nothing dispatchable
    the refusal names every candidate tried and why; the cursor profile preserves the
    previously-hardcoded invocation shape; `render_policy_toml` derives `[adapter].name`
    from the same preference with byte-identical default output; the empirical argv shapes
    for claude/cursor/gemini/copilot are smoke-verified against the real CLIs.
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
- **CAP-9** *(added 2026-08-28 — motivated by three live dispatches (mason 12.7, atlas
  20.5, mason 12.8) in one fleet-drain session, each observed journaling a `completed`
  verdict ~2 seconds after launch, before any real work happened)*
  - **intent:** CAP-2's `branch_merged` git fact is never true on ancestry alone.
    `is_branch_merged` shells `git merge-base --is-ancestor branch into`, which answers
    "yes" the instant a dispatch branch is forked from `into`'s own current tip — true of
    every fresh dispatch at launch, before any commit exists, and not evidence of
    anything having been merged. `gather_dispatch_git_facts` must gate that ancestry
    answer on the branch having actually diverged from its own launch
    `baseline_head_sha` before treating it as completion evidence.
  - **success:** A dispatch's `branch_merged` fact reads `false` for as long as
    `current_head_sha == baseline_head_sha`, regardless of what `is_branch_merged`
    answers — closing the false-positive that otherwise poisons
    `resolve_dispatch_session_verdict`'s journal short-circuit
    (`completion_verdict in {COMPLETED, FAILED}`) for the run's entire lifetime, making
    `marshal factory dispatch-resume`/`dispatch-attach` permanently unable to recover a
    dead supervisor even while the dispatched session is genuinely still alive and
    working. Once the branch carries real commits past baseline, a genuine "merged"
    ancestry answer is trusted exactly as before (CAP-2 is otherwise unchanged) — this is
    a divergence guard, not a rewrite of the ancestry check itself.
- **CAP-10** *(added 2026-08-31 — motivated by a live incident the same day: wanting to
  drain just `pyforge-scribe`'s 2 remaining backlog stories without touching atlas's or
  marshal's own in-flight backlogs found no CLI primitive for it — `drain`'s six flags
  carry no station filter, and `dispatch` chains nothing)*
  - **intent:** Station-scoped and sequence-scoped dispatch, both handed as an override to
    CAP-7's own per-station ordered-backlog reader rather than a second campaign
    implementation: `drain --mode <mode> --station <slug>` restricts CAP-7's
    chaining/preflight/journal to exactly one station's backlog instead of all eight;
    `dispatch <slug> --stories <key1>,<key2>,...` chains a caller-supplied ordered list
    instead of the ledger's own backlog order, for prioritizing specific stories without
    editing `fleet-drain-queue.yaml`'s `order_overrides` for a one-off push. Every named key
    is validated against the station's actual tracked backlog before anything launches.
  - **success:** `--station` scopes one drain cycle to that station's next backlog story
    only — every other station's backlog is provably untouched by that invocation;
    `--stories` launches its list in the given order via the same chaining `drain` already
    uses, and refuses before any worktree is provisioned when a named key is unknown or
    already done; both reuse CAP-2's zombie/in-flight preflight, CAP-4's landing machinery,
    and CAP-9's divergence guard unchanged — no second preflight or landing path exists.
- **CAP-11** *(added 2026-09-02 — steward 41.2 PR #1017 twenty-seven review
  write-backs while merge was DIRTY; mason 13.2 eighteen write-backs and no PR;
  ledger on `main` stayed backlog so drain re-launched `bmad-build-auto`)*
  - **intent:** A story whose spec is `status: done` must not enter another
    review pass unless `followup_review_recommended` is literally `true`, and
    even then only once. After the harness exits `done`, marshal's only legal
    next step is CAP-4 land. A land failure (conflicts, no PR, dirty) parks
    the story (`awaiting-operator` / CHAIN) naming the PR or worktree — it
    never starts another harness session. A 0-patch review must not commit.
  - **success:** Replaying the 41.2 / 13.2 fixtures (spec already `done`,
    `followup_review_recommended: false`, ledger still `backlog` on `main`)
    produces zero new review commits and zero new `bmad-build-auto` launches;
    CAP-4 either lands or escalates. A second `done`+`true` follow-up is
    allowed at most once, then the flag is forced `false`.

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
- **Always (CAP-10):** `--station` and `--stories` change ONLY which stories, on which
  stations, the campaign reads — never a lighter-weight preflight or landing path. A
  `--stories` list naming a story already done or absent from the station's tracked
  backlog refuses before any worktree is provisioned, the same zombie-refusal discipline
  fleet-wide `drain` already applies.
- **Always (CAP-11):** harness halt `done` is terminal for that story's
  session. Drain may only CAP-4 or escalate. Re-invoking `bmad-build-auto`
  because the ledger on `main` is still `backlog` is forbidden.
- **Always (CAP-11):** `done` + `followup_review_recommended: false` is a
  no-op HALT in the local `.claude/skills/bmad-build-auto/` copy. The
  vendored `bmad_loop` package is still unmodified.

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
- **Not** a change to the vendored `bmad_loop` package, or to
  `bmad-quick-dev`. The **in-repo** `.claude/skills/bmad-build-auto/` harness
  contract *is* in scope for CAP-11 (`done` routing + 0-patch no-commit).
  That amends the 2026-08-21 non-goal that left the skill untouched.
- **Not** shrinking `limits.max_followup_reviews` (see
  `docs/dreams/risk-tiered-review-depth.md`).

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

## Decomposition record (2026-08-27)

Reconciliation pass against `epics.md` (canonical) and the tracked
`sprint-status-ledger.yaml`. This Spec's frontmatter read `ready` while Epic 22's
2026-08-21 decomposition of CAP-1..6 had already shipped end to end — the known
stale-frontmatter pattern. Status corrected to `in-progress`: six of seven capabilities are
shipped; CAP-7 is now decomposed but not implemented.

| Capability | Covering story (epics.md / ledger key) | Ledger status |
|---|---|---|
| CAP-1 (governed, isolated single-story launch) | Story 22.1 — `22-1-the-dispatch-verb-launches-one-governed-isolated-story-session` | done |
| CAP-2 (completion from git+process facts; zombie never redispatched) | Story 22.2 — `22-2-completion-is-judged-from-git-and-process-facts-and-a-zombie-is-never-redispatched` | done |
| CAP-3 (verification is the product; no landing on a self-report) | Story 22.3 — `22-3-verification-is-the-product-no-landing-on-a-self-report` | done |
| CAP-4 (lands through existing machinery, marshal-native) | Story 22.4 — `22-4-a-verified-story-lands-through-the-existing-machinery-classified-marshal-native` | done |
| CAP-5 (one in flight per station; parallel stations; loud overlap) | Story 22.5 — `22-5-one-story-in-flight-per-station-stations-in-parallel-overlap-is-loud` | done |
| CAP-6 (run survives its operator; journal carries the timing signal) | Story 22.6 — `22-6-the-dispatched-run-survives-its-operator-and-its-journal-carries-the-timing-signal` | done |
| CAP-7 (fleet-wide drain as a marshal-orchestrated mode) | Story 22.7 — `22-7-fleet-wide-drain-is-a-marshal-orchestrated-mode` (minted this pass; previously uncovered — Epic 22's goal decomposed CAP-1..6 only, with CAP-7 named merely as the acceptance oracle) | backlog |
| CAP-8 (profile-driven, adapter-plural session harness; one preference, both engines) | Story 22.8 — `22-8-the-session-harness-is-profile-driven-across-agent-clis` (CAP added 2026-08-27 after the live cursor-auth dispatch failure; decomposed and implemented same day) | done |
| CAP-9 (`branch_merged` never trusts ancestry alone; requires real divergence past baseline) | Story 22.10 — `22-10-branch-merged-requires-real-divergence-not-just-ancestry` (CAP added 2026-08-28 after three live dispatches each journaled a false `completed` verdict ~2s post-launch, independently confirmed 20 of 26 real dispatch runs affected; decomposed, reviewed (2 layers, 1 medium patch + 2 low defers, 0 rejected), and landed same day; note the gap in Story 22.9, which never got a decomposition-record row here either) | done |
| CAP-10 (station-scoped drain + `--stories`) | Story 22.11 — `22-11-station-scoped-drain-and-an-explicit-story-sequence` | done |
| CAP-11 (done-spec must not review-loop) | Epic 29 — Stories 29.1 (`29-1-done-spec-halts-unless-followup-is-true`) and 29.2 (`29-2-harness-done-is-cap-4-only-never-another-session`) | backlog |

Shipped-surface evidence for CAP-1..6: `marshal factory dispatch` /
`dispatch-attach` / `dispatch-resume` (PRD § 18.3), `pyforge.marshal.dispatch_supervisor`,
`dispatch_verify`, `dispatch_land` (+ `core/dispatch_landing.py`), per-story promoted specs
`specs/spec-22-1-*.md` … `spec-22-6-*.md`. CAP-7's interim oracle remains the companion
`fleet-drain-playbook.md` + `.cursor/pyforge-fleet-drain/` (no `--fleet`/`drain` verb, no
campaign-mode policies in `cli/dispatch.py` as of this pass). This Spec flips to `shipped`
when Stories 22.7 and 22.8 both land.
