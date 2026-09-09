---
title: Sprint Change Proposal — token economy in effect (Epic 33)
date: 2026-09-09
project: pyforge-marshal
chain: spec-marshal-token-economy
status: approved — operator 2026-09-09, fleet-readiness decision batch § 0 (C5 + C6 approved as recommended)
trigger: docs/dreams/marshal-token-economy.md § Addendum (2026-09-09) — Epic 28 is 24/24 `done` and every layer is off — plus the fleet-readiness decision batch rows C5 (the CAP-17 publishing seam) and C6 (effect stories on the owning station)
mode: batch
scope: moderate
operator: Rxm7706
authored_by: authored by hand at the physical path under the parallel-agents HARD rule; skill not invoked
supersedes_none: true
follows: change-history/sprint-change-proposal-2026-09-01-dispatch-autonomy-hotfixes.md
---

# Sprint Change Proposal — token economy in effect (Epic 33)

> **Authored by hand at the physical path under the parallel-agents HARD rule; skill not invoked.**
> This is one of seven concurrent station applies of the operator-approved fleet-readiness decision
> batch. `scripts/bmad-switch` was not run, the `_bmad-output/planning-artifacts` symlink was not
> written through, and no BMAD write-skill (`bmad-correct-course`,
> `bmad-create-epics-and-stories`, `bmad-sprint-planning`) was invoked — the two shared symlinks are
> per-working-tree global state and a parallel write-skill would silently re-point another agent's
> target mid-write (`CLAUDE.md` § *PARALLEL AGENTS: never touch the switch*; live incident
> 2026-07-25). The lead re-derives every affected Spec with `bmad-spec` afterwards; the memlog
> entries this apply wrote are the input to that re-derive. Ledger keys were minted with
> `sprint_plan.py generate`, never `sprint-ledger-sync`.

## 1. Issue summary

**Marshal's token economy is built and switched off, and the one gate that would have caught it was
bypassed by the epic that set out to close it.**

Epic 28 shipped 24 of 24 stories `done`. Verified against `main` `fe4025ea90`:

1. **No layer is enabled anywhere.** No `[context]` block is declared in `_bmad-output/policy-defaults.toml`,
   in any of the eight project `marshal-policy.toml` files, or in any of the eight rendered loop-home
   `.bmad-loop/policy.toml` files. CAP-1's own contract makes an absent block mean *every layer off,
   behaviour byte-identical to before*, so the loop today reads and says exactly what it did before
   Epic 28 landed. Three independent corroborations, none of them the ledger: no caveman skill in any
   loop home, no codegraph index in any loop home, and no benchmark comparison artifact anywhere.
   `index-freshness-check` reports "all indices fresh or layers off" — the second branch, a vacuous
   pass.
2. **The measurement-first gate was bypassed.** The Dream's § *Gates* says "before any layer ships, a
   pinned benchmark story must establish the real baseline." Every layer shipped; the baseline was
   never established. `core/token_economy_benchmark.py` and `marshal benchmark compare` exist and
   have never been run against a real story.
3. **CAP-7 could not measure it even if it were on.** The per-layer savings getters in
   `adapters/harness_bmadloop.py` are stubs that `return None` — `_get_headroom_savings`,
   `_get_codegraph_stats`, `_get_cocoindex_stats`, `_get_graphifyy_savings` at `:1880-1898`, plus the
   Layer-0 caveman getter immediately above them (five in total), each with the comment "would
   integrate with actual … stats when available". The supervisor journals a savings block whose every
   field is null, `marshal status` renders nothing, and the benchmark's per-layer rows have no source
   to read. Scribe's side of the Layer-4 seam is real (`extras/graphify.py` writes through the
   `GraphStore` port; `compile.py:736-764` flags stale nodes) — the read side is five `None`s.
4. **Spin folds only two of five layers.** `resolve_wire_wrap` is imported in exactly one place,
   `adapters/harness_bmadbuild.py:50` (used at `:235`). On `factory spin` marshal launches
   `bmad-loop run` and bmad-loop launches the coding CLI, so there is no argv to prefix
   (`DW-FU-28-2`); layers 3 and 4 are epic-context compile, which is `bmad-build-auto`'s step 01. The
   honest matrix is output+structure-graph on both engines, wire+derived-context+planning-graph on
   dispatch/build-auto only. Separately `cli/dispatch.py:318` folds `read_repo_policy_defaults()` and
   `cli/spin.py` does not (`DW-FU-28-2-3`), so a repo-wide `[context]` block would act on one engine
   and vanish silently on the other.
5. **Unifying CAP-17 (run state as a service) is the same inert shape at the same seam.** Marshal has
   **zero** imports of `django_pyforge` (grep over `src/shared/packages/pyforge-marshal/src/` returns
   0), `cli/init.py:331` still resolves `Path.home() / ".bmad-loops"`, and doctor's
   `sources/marshal.py:544` does the same. Steward Story **49.8** ("CAP-17 in effect — marshal
   publishes run state to the supervisor") is ledger **`blocked`** with `Deps:` reading *"cross-station:
   marshal Epic 33's Track story (ledger `blocked` until it exists)"* — and Epic 33 did not exist:
   marshal's `epics.md` topped out at Epic 32.
6. **Three more marshal capabilities are the same pathology, with no vessel.** `risk-tiered-review-depth`
   (`classify_review_tier`/`resolve_review_cycles` at `core/gate.py:724,768` — zero callers outside
   `tests/unit/test_gate.py`; `DW-FU-2-8-4` `verified: 2026-09-05 — STANDS`); `adaptive-model-tiering`
   (fed on 2 of 8 stations; Story 3.12's retry floor-raise fires only in `cli/spin.py:2268-2277
   _apply_retry_escalation`, unreachable from `factory dispatch`, the live engine since ~2026-08-22);
   `marshal-parallel-dispatch-fanout` (`max_parallel = 1` on all eight loop homes, no live wave ever).
   And the two Epic-20 watchdogs (`scripts/bmad_loop_baseline_drift_check.py:72,142`,
   `scripts/missing_preserve_check.py:61`) observe `~/.bmad-loops` only — a plane whose newest run in
   any of the eight homes is **2026-08-22** — so both exit **0 "OK"** on an empty observation plane
   rather than reporting could-not-observe, a false green by `pixi.toml:1033`'s own stated standard.

That is **six** built-but-not-in-effect capabilities on one station. The fleet-readiness batch's § 1
verdict says it plainly: *the fleet is built; it is not switched on.*

## 2. Change-navigation checklist (recorded)

| # | Item | Status | Finding |
|---|---|---|---|
| 1.1 | Triggering story | Done | None — the trigger is the Dream's own 2026-09-09 addendum plus batch rows C5/C6. Root causes span shipped Epics 20, 23, 24 and 28, `cli/spin.py` vs `cli/dispatch.py` asymmetry, and five stub getters in one adapter. |
| 1.2 | Problem type | Done | Mixed: *misunderstanding of done* (mechanism ≠ effect — the dominant one), *technical limitation* (spin has no argv to prefix; the dispatch supervisor has no provider meter), *documentation drift* (a Spec's CAP axis colliding with another spine's). Not a newly discovered requirement: every capability here is already contracted. |
| 1.3 | Evidence | Done | Dream § *Addendum (2026-09-09)* with file:line for every claim; the fleet-readiness batch § 2.3 C5/C6 and § 2.4 D6/D9; both marshal readiness reports (Tables A/B, Sections C–E), each claim re-verified by the reviewing session (batch § 6). |
| 2.1 | Current epics completable | Done | Epics 1–32 unchanged; nothing reopened. Epic 30 (`backlog` rows 30.1–30.5 are all `done`) and Epic 31 (31.4/31.5 `backlog`, 31.6 `blocked`) are untouched except 31.4's AC text (§ 4.4). |
| 2.2 | Epic-level change | Done | **Add Epic 33 — "Token economy in effect."** One epic, not two: every story here is the same act (turn on a capability that is already built) and they share one measurement gate. |
| 2.3 | Remaining epics | Done | Epic 31 stays as scoped. Steward Epic 49's index row for marshal points at this epic; steward 49.8 stays ledger `blocked` until Story 33.4 exists and then lands jointly with it — one publisher, not two. |
| 2.4 | Obsolete / new | Done | Nothing obsolete. New: Epic 33 (ten stories). Three deferred-work entries are promoted rather than left as debt: `DW-FU-28-2`, `DW-FU-28-2-2`, `DW-FU-28-2-3`. |
| 2.5 | Order / priority | Done | **33.1 first and alone.** Everything else depends on it — that is the Dream's own measurement-first gate, restored rather than re-argued. Then 33.2 → 33.3; 33.4–33.10 in parallel after 33.1, with 33.8 after 33.2 (a wave should not be the first thing a newly-enabled wire layer meets). |
| 3.1 | PRD conflicts | Done | None. No FR added. FR-51 (tiering), FR-12 (idle ladder) and E3.6 (ceilings) are exercised, not amended. The PRD gains a dated paragraph (§ 4.6). |
| 3.2 | Architecture conflicts | Done | One recorded, not resolved here: **AD-49's non-waivable `SCOPE_VIOLATION` refuse is no longer the fleet default** — `core/policy.py:609` sets `scope_violation_mode = "warn"` in `DEFAULT_POLICY` (CAP-17, the 2026-08-31 operator decision). That is intended; `docs/dreams/marshal-dependency-aware-dispatch.md` § D described it as an opt-in and was corrected in this same pass. |
| 3.3 | UI/UX conflicts | N/A | `marshal status` gains real savings numbers where it renders nulls today (33.1/33.4). No new surface. |
| 3.4 | Other artifacts | Done | `marshal-policy.toml` `[epic_surfaces]` `"33"` (§ 4.5); `sprint-status-ledger.yaml` **via `sprint_plan.py generate` only**; the deferred-work ledger (§ 4.7); Story 31.4's AC text (§ 4.4); `docs/dreams/marshal-token-economy.md` Realization log (already applied). |
| 4.1 | Option 1 Direct adjustment | Done | **Chosen.** Purely additive: one epic, ten stories, all `backlog`; no shipped epic reopened and no shipped CAP re-minted. |
| 4.2 | Option 2 Rollback | Done | Rejected. Nothing shipped is wrong. Epic 28's machinery is real and complete; it is unexercised. |
| 4.3 | Option 3 MVP review | Done | Rejected — the opposite move. *Effect* becomes part of scope, which is a scope increase by design. |
| 4.4 | Path forward | Done | Direct adjustment, moderate scope. |
| 5.x | Proposal components | Done | § 3–5 below. |
| 6.x | Review | Done | Batch mode; presented whole; operator approval is batch § 0 rows C5 and C6. |

## 3. Recommended approach

**Direct Adjustment, scope moderate. One epic, ten stories, all `backlog`. Dispatch 33.1 alone and
first.**

| Epic | Stories | Binds | Depends on |
|---|---|---|---|
| **33 Token economy in effect** | 33.1 measurement first · 33.2 layers on dispatch · 33.3 layers on spin · 33.4 **CAP-18 one publisher** · 33.5 risk-tiered review wiring · 33.6 adaptive tiering fed + floor-raise on dispatch · 33.7 the Epic-20 watchdogs re-pointed · 33.8 first live fan-out wave · 33.9 `verify_scope` at `factory dispatch` · 33.10 the derived CFE pin | `spec-marshal-token-economy` CAP-1..CAP-18 (CAP-18 new), `spec-risk-tiered-review-depth`, `spec-adaptive-model-tiering` CAP-2, `spec-marshal-parallel-dispatch-fanout` CAP-6 (new), `spec-bmad-loop-baseline-drift`, `spec-bmad-loop-intent-gap-work-preservation`, `spec-bmad-switch-scope-enforcement`, batch rows C5 / C6 / C10 / D6 / D9 | 33.1 gates 33.2+; nothing waits on foundry |

**Why one epic and not two.** Steward split 48 (bookkeeping) from 49 (a policy change) because those
are different kinds of work. Here every story is the *same* kind — a capability whose mechanism is
`done` gets a caller, a producer, or a declaration — and all of them are void without 33.1's
measurement. Splitting them would produce two epics with one shared blocking story.

**Why not fold these into Epics 20, 23, 24 or 28.** Those epics are `done`. Reopening a shipped epic
for effect work asserts the mechanism was wrong; it was not. Effect is new work, and reopening a
`done` ledger row re-arms the dispatch picker on a story whose code already exists — the respawn trap
auto-memory records (`feedback_merged_story_with_backlog_ledger_row_respawns_forever`).

**Why 33.1 is not negotiable.** The Dream states the gate and Epic 28 walked past it. The cost of
enabling first and measuring later is not "we learn less" — it is that the equivalence gate in
`marshal benchmark compare` has no off-leg to compare against, so the on-leg produces a number that
means nothing, and ceiling recalibration (the Dream's *"50M weighted was sized for an uncompressed
world"*) stays blocked forever. 33.1 is also where the five stub getters become real; without them
the on-leg's per-layer rows are null whatever the layers do.

**Effort / risk.** 33.1 **M** (five getters + a pinned benchmark run on
`1-1-marshal-conformance-smoke`; the off-leg is a re-run of an existing story, not new code).
33.2 **S** (fold `resolve_wire_wrap` on the dispatch path; the composition site already exists).
33.3 **M** (`DW-FU-28-2`'s loop-home launcher shim — the only story here that needs a new seam, and
the one most likely to come back as "spin stays a two-layer engine", which is an acceptable outcome
recorded rather than a failure). 33.4 **L** (the publisher; crosses into `django_pyforge` for the
first time and carries steward 49.8 with it). 33.5 **M**, 33.6 **M**, 33.7 **S**, 33.8 **M**,
33.9 **S**, 33.10 **S**. Risk **Medium**, concentrated in 33.4 (a new cross-package dependency
direction and a `blocked` cross-station row) and 33.3 (a seam that may not exist).

## 4. Detailed change proposals

### 4.1 `spec-marshal-token-economy` — CAP-18 (recorded by memlog, not hand-edited)

The Spec's `SPEC.md` is **not** edited by this apply. CAP-18 is recorded as a
`--type capability` memlog entry in
`planning-artifacts/specs/spec-marshal-token-economy/.memlog.md` for the lead's `bmad-spec`
re-derive:

> **CAP-18 — one publisher: marshal publishes run state AND savings telemetry to
> `django_pyforge.supervisor`.**
> **Intent:** a single supervisor-side publisher hop carries both the bmad-loop/dispatch run state
> that **Unifying CAP-17** (*qualified* — run-state-as-a-service on `spec-pyforge-unifying-strategy`,
> **not** this Spec's own CAP-17, which is `scope_violation_mode`) and the Hub's Track
> (**`hub:CAP-3`** on `spec-intelligence-hub`) require, and this Spec's own **CAP-7** per-layer
> savings fields; marshal and doctor stop reading `~/.bmad-loops` as the source of run truth.
> **Success:** marshal imports `django_pyforge` in exactly one publisher module (it imports it zero
> times today); `cli/init.py:331` and `pyforge-doctor` `sources/marshal.py:544` read the published
> plane instead of `Path.home() / ".bmad-loops"`; the front door shows live run state and the
> per-story timing survives the workstation; and CAP-7's savings fields carry real numbers, not the
> `None` stubs at `adapters/harness_bmadloop.py:1880-1898`. **One writer, not one per engine** — the
> loop supervisor and the dispatch supervisor both feed this single publisher.

**Why here and not on `spec-pyforge-marshal` CAP-5.** CAP-7 already contracts a supervisor journal
writer plus a `marshal status` renderer — the same hop a `django_pyforge.supervisor` publisher needs.
Splitting CAP-7 and CAP-17 across two Specs guarantees two publishers writing the same run state,
which is precisely what the Dream's own 2026-09-09 log warns against. This Spec is `ready`, so it
takes the correction cleanly. Three independent artifacts already name Epic 33 as the landing site
(this Dream's Realization log, the Unifying Dream's convergence map, and steward 49.8's own `Deps:`).
The alternative — `spec-pyforge-marshal` CAP-5, architecturally the purer home — would first require
that Spec's `status:` and its `BLOCKED-ON` F-1..F-6 disposition, which is a separate campaign; that
disposition was in fact performed in this same pass, but as a *record*, not as a re-decomposition.

**CAP-axis hazard closed in the same motion.** Three citations must always be written qualified, and
the story text below does so: the Track is **`hub:CAP-3`**, not this Spec's CAP-3 (caveman
output-compression seeding); savings telemetry is this Spec's **CAP-7**; and run-state-as-a-service is
**Unifying CAP-17**, which collides by number with this Spec's own unrelated CAP-17.

### 4.2 `spec-marshal-parallel-dispatch-fanout` — CAP-6 (recorded by memlog)

> **CAP-6 — factory fan-out has its own `dispatch.max_parallel` policy key.**
> **Intent:** the dispatch wave cap is a first-class marshal policy key resolved by
> `cli/dispatch.py:893-902`, independent of bmad-loop's `scm.max_parallel` (`core/policy.py:513`)
> which it falls back to today; raising the dispatch cap therefore stops firing
> `_max_parallel_clamp_finding` (`core/policy.py:1537-1551`), whose message names *bmad_loop 0.9.0* —
> a false-context warn on the dispatch path.
> **Success:** a station declaring `dispatch.max_parallel = N` forms waves of up to N with no
> bmad-loop clamp advisory; a station declaring nothing behaves exactly as today (1); the bmad-loop
> knob continues to govern the spin engine alone.

### 4.3 `epics.md` — Epic 33

Appended before the § *Deferred-work verification state* trailing section, mirroring Epic 32's story
shape (`**Type:** … • **Effort:** … • **Deps:** … • **FR/AD:** …`, `**Surface:**`, a
`**Given** / **When** / **Then**` line and one or more `**And**` lines). Full text is in `epics.md`;
the ten stories are summarised in § 3 and traced in the readiness report.

### 4.4 `epics.md` — Story 31.4's AC text (batch § 2.4 **D9**), amended not re-minted

Story 31.4 is `backlog` and its text says *"the seven files"*. The in-place-edited installer-owned
pool is now **eleven**, four of them ungoverned, and **three have never been named in any artifact**:
`.claude/skills/bmad-retrospective/scripts/sprint_status.py`, its test
`.claude/skills/bmad-retrospective/scripts/tests/test_sprint_status.py`, and
`.claude/skills/bmad-sprint-planning/sprint-status-template.yaml` — the last of which carries the
Epic-44 `blocked` restore, so an ungoverned in-place edit to it is a silent change to a gating
artifact. The story's Surface and its Given/When/Then are amended to the pool of eleven, with the
three named explicitly. **No new story is minted** and no `done` key is touched.

### 4.5 `marshal-policy.toml` — `[epic_surfaces]` `"33"`

Mirrors how steward's `"48"` / `"49"` were added on 2026-09-09: copy the station's `"31"` block and
add the epic's own globs — `src/shared/packages/django-pyforge/**` (33.4's publisher),
`src/shared/packages/pyforge-doctor/**` (33.4 re-points `sources/marshal.py:544`),
`docs/dreams/marshal-token-economy.md`, `_bmad-output/policy-defaults.toml`,
`.claude/skills/conda-forge-expert/SKILL.md` (33.10 reads the pin from it) and `scripts/**` (33.7's
two watchdogs). Without an entry, `effective_surface` falls back to an empty tuple and
`MRS-GATE-007` fires on every changed path.

> **This edit trips `spec-surface-check` for pyforge-marshal and is deliberately NOT stamped.**
> `marshal-policy.toml` is governed by `spec-marshal-parallel-dispatch-fanout`'s `surface:`; the
> reconciling memlog line was written, but the scoped
> `--write-baseline --spec pyforge-marshal/spec-marshal-parallel-dispatch-fanout` was **not** run —
> the lead re-baselines after the `bmad-spec` re-derives, per the batch's apply-order step 8. Expect
> one `drift` finding on this path until then.

### 4.6 PRD — `PRD.md`, dated paragraph

**2026-09-09 correct-course (token economy in effect):** Epic **33** binds the enablement of what
Epic 28 built. No FR added — *effect* is a definition-of-done discipline over existing requirements
(FR-51 tiering, FR-12 idle ladder, E3.6 ceilings, FR-153+ the tool surface). The Dream stays
`specified` until Story 33.1's benchmark artifact reports a measured saving on a real story.
Record: `sprint-change-proposal-2026-09-09-token-economy-enablement.md`.

### 4.7 Deferred-work ledger

Three entries stop being incidental debt and become story-bound:
`DW-FU-28-2` (spin is never wrapped) → **33.3**; `DW-FU-28-2-3` (`cli/spin.py` does not fold repo
defaults) → **33.3**; `DW-FU-28-2-2` (`headroom wrap` attaches to a running proxy on port 8787, so
two concurrent wrapped dispatches share the first launcher's CCR store — the fleet-parallel case) →
**33.8**. `DW-FU-2-8-2` / `DW-FU-2-8-4` (risk-tiered review has no producer and no caller) → **33.5**;
they **stay open and STANDS** until 33.5 lands both. `DW-FU-3-6-6` (mid-session ceiling blindness) is
named by 33.1 as what the savings block finally answers.

### 4.8 `sprint-status-ledger.yaml`

Ten story keys plus `epic-33` and `epic-33-retrospective`, minted by
`PYTHONPATH="$PWD/_bmad/scripts:$PYTHONPATH" python .claude/skills/bmad-sprint-planning/scripts/sprint_plan.py generate`
against this file — dry-run first, diffed, then for real. **`sprint-ledger-sync` was not run in any
form** (the tracked twin is authoritative here and the Tier-3 feed lags it by these keys, which is
correct until steward Story 48.1 lands its `STICKY_STATUSES` guard). Story **33.4** is minted
**`blocked`** with `--set`: it is the joint landing partner of steward 49.8, which is itself `blocked`
on it — one publisher, landed once, by whichever of the two dispatches first with the other's consent.

## 5. Implementation handoff

**Scope: Moderate** (backlog addition with a stated order). Route to Product Owner / Developer.

| Role | Responsibility |
|---|---|
| Operator (Rxm7706) | Approved as batch § 0 rows C5 + C6. Remaining call: whether 33.3 may close as *"spin stays a two-layer engine"* if the launcher shim proves unavailable — the story is written to accept that as an outcome, recorded, not as a failure. |
| Marshal (owner) | All ten stories. 33.4 jointly with steward 49.8. |
| Steward | 49.8 lands with 33.4; Epic 49 carries the index row for marshal's effect stories (batch C6). |
| Doctor | Consumes 33.4's published plane (`sources/marshal.py:544`) and records the incoming surface claim in `spec-pyforge-doctor`'s memlog **before** 33.4's code lands, or `spec-surface-check` reds the merge. 33.7's two watchdogs stay marshal-owned scripts. |
| Scribe | Layer 4's write side is already real (`extras/graphify.py`, `compile.py:736-764`); 33.1 reads it. No scribe story. |
| Mason / Atlas | Unaffected by this epic. (Their CLI⇄tool-parity gate for the 46 CFE tools and `pyforge/atlas/mcp/tools.py` is batch row C10, routed separately.) |
| Developer agent | One story per session; `BMAD_ACTIVE_PROJECT=pyforge-marshal` per invocation; physical paths; **ledger via `sprint_plan.py generate` only**; never a fork subagent (the new Constraint on `spec-marshal-single-story-dispatch`). |
| Warden | PR gate as usual; no second verdict. |

**Success criteria.**
**33.1 as a unit:** a committed benchmark artifact naming the pinned story, the off-leg verdict, the
on-leg verdict, and per-layer rows with **non-null** numbers; `marshal benchmark compare` either
reports a measured saving or **voids** the comparison — a void is the answer, not a failed test.
**Epic 33 as a unit:** a `[context]` block is declared and acting on both engines (or spin's
two-layer ceiling is recorded as a decision); `marshal status` renders real savings mid-run;
`grep -r django_pyforge src/shared/packages/pyforge-marshal/src/` returns exactly one publisher
module and steward 49.8 is `done`; `classify_review_tier` has a caller outside its own test file;
six more stations carry a `model_tier_map` and `factory dispatch` raises the model floor on a
struggling retry; both Epic-20 watchdogs exit **2** (could-not-observe), never 0, on an empty plane;
one live fan-out wave has landed two disjoint stories; `verify_scope` refuses a mis-scoped
`factory dispatch`; and `bmad-drift` reports zero `pin-behind` on marshal artifacts without anyone
having typed a version number.

**The gate on the Dream itself.** `docs/dreams/marshal-token-economy.md` stays `status: specified`
until 33.1's artifact exists. *"This Dream is not `realized` when its next epic closes. It is
`realized` when a benchmark artifact reports a measured saving on a real story. Nothing else counts."*

## 6. Applied

Operator approval: fleet-readiness decision batch § 0 — **C5** (*"`spec-marshal-token-economy` CAP-18
via the Epic 33 correct-course, one publisher with CAP-7; risk-tiered wiring story in Epic 33"*) and
**C6** (*"effect stories on each owning station's epics; steward Epic 49 keeps an index row per
station"*), both approved as recommended.

- `epics.md` — **Epic 33** (ten stories); Story **31.4**'s Surface + AC text amended to the
  eleven-file pool (§ 4.4).
- `specs/spec-marshal-token-economy/.memlog.md` — **CAP-18** (`--type capability`), the Epic-33
  enablement decision, and the CAP-axis qualification note.
- `specs/spec-marshal-parallel-dispatch-fanout/.memlog.md` — **CAP-6** (`--type capability`), oq1/oq2
  closures, `ready → shipped`, the residual, and the `[epic_surfaces] "33"` surface-touch record.
- `marshal-policy.toml` — `[epic_surfaces]` `"33"`. **Not stamped** (§ 4.5).
- `sprint-status-ledger.yaml` — ten story keys + `epic-33` + `epic-33-retrospective` via
  `sprint_plan.py generate`; 33.4 set `blocked`. **No sync of any form was run.**
- `docs/dreams/marshal-token-economy.md` — Realization-log entry naming Epic 33 and CAP-18; status
  deliberately unchanged (`specified`).
- `implementation-readiness-report-2026-09-09.md` — the readiness gate for
  this epic, written by hand under the same rule (no `bmad-sprint-planning` invocation).
- `PRD.md` § dated paragraph — **not** applied by this pass; it is left for the lead's re-derive so
  the PRD is touched by its own skill rather than by a parallel agent.
