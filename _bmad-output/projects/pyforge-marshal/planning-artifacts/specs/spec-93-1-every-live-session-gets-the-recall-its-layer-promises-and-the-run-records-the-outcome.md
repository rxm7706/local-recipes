---
title: "93.1: Every live session gets the recall its layer promises, and the run records the outcome"
type: 'fix'
created: '2026-10-11'
status: 'in-progress'
baseline_revision: 'e981ff751c113c9b651548c58d5aee16ccb1d438'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-recall-in-the-loop/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-47-1-a-bmad-loop-dev-pass-automatically-receives-relevant-scribe-feedback-before-it-starts.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-47-2-a-bmad-loop-review-pass-sees-the-same-scoped-feedback-the-dev-pass-saw.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-47-3-the-recall-injection-layer-composes-with-the-existing-context-pipeline.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-47-4-a-genuine-recall-miss-injects-nothing-never-a-fabricated-confidence-claim.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadbuild.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/scribe_cli.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/recall_feedback.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/spin.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadloop_recall.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_recall_feedback.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the recall layer is built, unit-tested and reported as enabled, and no live session has ever received a
recall. Stories 47.1–47.4 (`spec-marshal-recall-in-the-loop` CAP-1..4) landed on 2026-10-08 (47.2, 47.3, 47.4) and
2026-10-11 (47.1), and two deferred-work rows they left open say why: `DW-marshal-47-2` (the fold has no in-tree
caller) and `DW-marshal-47-3` (no live launch path passes the resolved `[context]` layers to it). Line numbers below
are at `47397de509`.

**What exists (the fold).**
- `adapters/harness_bmadloop.py` `inject_recall_feedback` (`:1365`) runs `ScribeCli.recall(..., mode="memory")` with no
  `--scope` (Story 47.1, the operator's 2026-10-10 ruling), formats the outcome through
  `core/recall_feedback.format_recall_feedback_for_injection` (a grounded hit becomes the labelled block; a miss or a
  failure becomes empty text, Story 47.4), writes it to `<loop_home>/_bmad-output/projects/<slug>/implementation-artifacts/recall-feedback.md`,
  and writes a sibling `recall-feedback.md.query-ran` marker. It returns a `RecallInjectionResult` (`attempted`, `ok`,
  `injected`, `reason`, `target`, `:1331`-`:1356`).
- `augment_bmad_loop_session_prompt_with_recall` (`:1429`-`:1475`) gates on `[context.recall]` when it is handed the
  resolved layers (Story 47.3), runs the query for a `dev` session when the marker is absent, and appends the cached
  block to the prompt for `dev` and `review` sessions alike (Story 47.2).
- `_bmad-output/policy-defaults.toml` declares `[context.recall] enabled = true`; `policy.resolve_context_layers` gives
  it `aggressiveness = "medium"`.

**What never runs it (the evidence).**
- `augment_bmad_loop_session_prompt_with_recall` is called only from `tests/unit/test_harness_bmadloop_recall.py`
  (`git grep` at `47397de509`).
- **The `bmad-loop` engine.** `cli/spin.py` launches `bmad-loop run` against the policy `render_policy_toml` writes,
  whose `[plugins]` block is `enabled = []` (`_POLICY_TEMPLATE`, `:412`). bmad-loop 0.12.0 (the installed harness)
  builds its own session prompts; the one place a prompt can change is its plugin hook bus: `engine.py`
  `_emit_session_gate` fires the role's session stage and then `pre_session`, with the prompt as the mutable
  `proposed_prompt` (`plugins/context.py` `MUTABLE_FIELDS`). With no plugin enabled, no session sees the block.
- **The dispatch engine.** `marshal factory dispatch` builds its `bmad-build-auto` prompt in
  `adapters/harness_bmadbuild.py` `dispatch()` (`:415`-`:424`) from the station, story, spec path, project addressing
  and the spec-surface obligation, with no recall. Yet `cli/dispatch.py` sets `data["context"] = context_payload`
  (`:2940`-`:2941`) and journals the same payload on the launch INTENT (`:3465`), so every dispatch envelope reads
  `"context": {"recall": {"enabled": true, "aggressiveness": "medium"}, ...}`: a layer declared on and never attempted.
  Only `wire` (Story 28.2) and `structure-graph` (Story 77.1) report a disposition of their own (`data["wire"]`,
  `data["structure_graph"]`).
- **A cache that would go stale once wired (found while specifying).** The `.query-ran` marker and the cached block are
  keyed by project slug alone, under `implementation-artifacts/`, which a loop home and a dispatch worktree share with
  the canonical Tier-3 store. Wired as it stands, the first dispatch on a station would write the marker, and every later
  dev session on that station, in any story or run, would skip the query and fold in that first block forever.

**Scope, as the operator ruled it.** Story 47.1 resolved the Spec's Open Question 2 as "bmad-loop dev passes only".
The operator's 2026-10-11 ruling "Mint a wiring story (Recommended)" replaces that answer; its option read: "Marshal
story: dispatch's session prompt (harness_bmadbuild.py) and the bmad-loop launcher both call the recall fold when the
layer is enabled; the dispatch envelope reports whether recall ran and grounded; closes DW-marshal-47-2/47-3; proof is a
journaled grounded recall in a real dispatch run."

**Approach:** both engines call the one fold that exists, behind the one layer gate, with a cache keyed to the story
dispatch, and every dispatch records what the recall did.
- **The dispatch engine.** Before `BuildHarnessPort.dispatch` launches the session, `dispatch_once` calls the fold for
  role `dev` with the station's project slug, the dispatch worktree as the home, and the resolved `[context]` payload it
  already holds (`context_payload`). `harness_bmadbuild.dispatch()` gains one optional argument carrying the block (or
  the recall layer's resolved entry and the fold's result), never the whole `[context]` payload, as Story 28.2's
  `wire_layer` does. The block is appended after the existing prompt lines. One `bmad-build-auto` session runs both its
  dev and review steps, so the block it starts with is the block its review step reads.
- **The `bmad-loop` engine.** Marshal ships a bmad-loop plugin whose `pre_session` hook (or the role session stages it
  fires first) calls `augment_bmad_loop_session_prompt_with_recall` with the session's role (`dev` or `review`), the loop
  home, the station slug and the resolved layers, and sets `proposed_prompt` to its result. `render_policy_toml` enables
  that plugin in the rendered `[plugins]` block only when the recall layer is enabled, so a disabled layer loads no
  plugin and runs no query. The plugin lives in marshal's harness adapter (AD-3: one module family touches the harness)
  and reaches scribe only through `ScribeCli` (a subprocess). If bmad-loop's plugin manifest or hook signature cannot
  carry this, the dev stops and records the mismatch in the Spec Change Log rather than editing bmad-loop's installed
  package (AD-74).
- **The cache.** The marker and the cached block are keyed to the story dispatch: the story key and the run (the
  dispatch run id, or the bmad-loop run id and story), so a later dispatch or another story queries again, and a block
  from another story or run is never read. Within one dispatch, the first `dev` session queries; every later `dev` or
  `review` session of that dispatch reads the cached block. A query that fails leaves no marker, so the next session of
  that dispatch may try once more. Exactly one `scribe recall` runs per story dispatch when it succeeds.
- **The disposition.** `dispatch_once` seeds `data["recall"]` the moment the `[context]` payload exists (beside
  `data["wire"]` and `data["structure_graph"]`, Story 77.1's pattern), so every envelope emitted from the policy
  composition onward carries it, and journals it on the launch INTENT. Its fields: `attempted` (bool), `outcome` (one of
  `grounded`, `miss`, `failed`, `disabled`, `no-station`, `not-reached`), `reason` (present when `failed`), and
  `cached` (the block came from this dispatch's cache). `not-reached` is the seed, overwritten once the fold runs or
  the layer gate says why it did not. A `failed` recall adds one WARN finding (the next free `MRS-DISP` code at
  implementation, registered in `core/findings.py` and `core/verdict.py`); it never refuses or blocks the launch. The
  `bmad-loop` hook journals its own outcome per session through marshal's journal when the loop home has one, or in the
  hook's return to bmad-loop's own events otherwise; the dev names the channel in the Spec Change Log.
- **Unchanged:** scribe's `recall.py` and its grounding rules; `ScribeCli.recall`'s argv for every other caller
  (`marshal context retrieve` keeps `--mode planning --scope <slug>`); `format_recall_feedback_for_injection`'s
  empty-miss rule; the other five `[context]` layers; the dispatch prompt's existing lines; verification, landing and
  the fix turn.

Ledger key: `93-1-every-live-session-gets-the-recall-its-layer-promises-and-the-run-records-the-outcome`.
Type / Effort / Deps: fix / M / none.

### Living CAP citations

- **Shipped behaviour.** `spec-marshal-recall-in-the-loop` CAP-1 (a dev pass receives relevant team-memory feedback
  before it starts) and CAP-2 (the review pass sees the same block), with CAP-3 (the `[context.recall]` layer gate,
  Story 47.3) and CAP-4 (a miss injects nothing, Story 47.4). Stories 47.1–47.4 built the fold, and no live session
  runs it, so the CAP-1 and CAP-2 success criteria are unmet in production. This story closes that gap. The fold of
  2026-10-11 carries these four as `spec-pyforge-marshal` CAP-288..CAP-291 (CAP-1 → CAP-288, CAP-2 → CAP-289, CAP-3 →
  CAP-290, CAP-4 → CAP-291) once the operator-approved render lands; the re-derived CAP-288 and CAP-289 name both
  engines, per the operator's ruling. `spec-pyforge-marshal` CAP-174 (← `spec-marshal-token-economy` CAP-1) is the
  `[context]` block's one composition site both engines already read. The story mints no CAP and writes no `SPEC.md`.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag: it makes shipped behaviour reach the
  session it was built for, and `[context.recall]` `enabled = false` already turns it off.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-11 (recall is built and never runs), and the
  folded section of the same date. Operator rulings 2026-10-11, verbatim: "Mint a wiring story (Recommended)" and "Fold
  into pyforge-marshal (Recommended)".

## Acceptance Criteria

Every test uses a fake scribe at the `ScribeCli` seam (a fake binary or an injected `ScribeCli` double) with four
shapes: grounded (text plus a `.claude/memory/feedback/<slug>.md` citation), miss (`ok`, not grounded), failure
(`ok=False` with a reason, including a non-zero exit and a timeout) and not called. The dispatch tests use the existing
`BuildHarnessPort` and forge fakes; the `bmad-loop` tests drive the shipped hook with a `HookContext`-shaped object and
a real temporary loop home, never a live bmad-loop run.

- **AC1 — The dispatch prompt carries a grounded recall.**
  - **Given** `[context.recall]` enabled, a station slug, and a fake scribe that grounds.
  - **When** `dispatch_once` launches the session.
  - **Then** the prompt handed to the session ends with the labelled block (`RECALL_FEEDBACK_HEADER`, the text, and
    `Source: .claude/memory/feedback/<slug>.md`), after every existing prompt line, unchanged; the fake saw exactly one
    `recall <query> --mode memory` call with no `--scope`; the envelope's `recall` reads `attempted: true`,
    `outcome: grounded`; the launch INTENT carries the same disposition.
- **AC2 — A `bmad-loop` dev and review session carry the same block.**
  - **Given** a rendered loop-home policy with the recall layer enabled, and a fake scribe that grounds.
  - **When** the shipped hook runs for the story's `dev` session and then its `review` session (and a second `dev`
    attempt) of one dispatch.
  - **Then** each `proposed_prompt` ends with the identical block; the fake was called once; `render_policy_toml`
    lists marshal's plugin in `[plugins] enabled`, and lists nothing new when the layer is disabled.
- **AC3 — A miss, a failure or a disabled layer injects nothing, and says so.**
  - A miss: no block in either engine's prompt; `outcome: miss`; no finding.
  - A failure (non-zero exit, timeout, missing binary): no block; `outcome: failed` with the reason; one WARN finding;
    the session still launches.
  - A disabled layer: no scribe call at all, no plugin enabled, no block; `outcome: disabled`.
  - No station slug: no call; `outcome: no-station`.
  - In every case the prompt holds no sentence about the recall (no "no relevant corrections found").
- **AC4 — The cache belongs to one story dispatch.**
  - Two dispatches of two different stories on the same station, against the same `implementation-artifacts/`, each
    call scribe once, and the second never reads the first's block.
  - A second dispatch of the same story (a new run) queries again.
  - A failed query writes no marker; the next session of that dispatch may query once more.
- **AC5 — Every envelope says what the recall did.** Every `dispatch_once` envelope emitted after the policy
  composition (launch, refusal after composition, `BuildHarnessError`) carries `recall` with `attempted` and `outcome`;
  an envelope whose `context.recall.enabled` is true and whose `recall.attempted` is false names its `outcome`
  (`not-reached`, `no-station`) instead of reading as a recall that ran.
- **AC6 — Nothing else moves.** Every existing marshal test passes; the tests of Stories 47.1–47.4
  (`test_harness_bmadloop_recall.py`, `test_recall_feedback.py`) change only where the cache key changes, and the dev
  names each changed expectation with its reason in the Spec Change Log. `marshal context retrieve`'s argv test is
  untouched. `DW-marshal-47-2` and `DW-marshal-47-3` close in `deferred-work-ledger.md` with `verified:` lines citing the
  new callers by `path:line`.
- **AC7 — Mutation.**
  - Dropping the dispatch call fails AC1.
  - Dropping the hook's call, or enabling the plugin regardless of the layer, fails AC2 or AC3.
  - Keying the cache by project slug alone fails AC4.
  - Seeding no `recall` disposition, or reporting `grounded` for a miss, fails AC1, AC3 or AC5.

## Boundaries & Constraints

**Always:**
- Reach scribe only through `ScribeCli` (a subprocess, `--mode memory`, no `--scope`); never `import pyforge.scribe`.
- Keep the decisions pure (`core/`, AD-4): whether to query, the cache key, the disposition. The subprocess, file and
  journal I/O stay at the edge.
- Journal the recall's INTENT before the query runs (AD-6); a disposition the code cannot settle reads `failed` or
  `not-reached`, never `grounded` (AD-8).
- Treat the recalled text as evidence handed to the session, never as an instruction marshal acts on (AD-32).
- Reconcile every governed path the change touches on the memlogs of the Specs that govern it, then stamp those Specs
  scoped: `spec-pyforge-marshal` and `spec-pyforge-core` (it co-governs every station's `src/`), plus every co-governor
  `spec-surface-check` names (AGENTS.md pre-PR item 5). If the fold's render has not landed when this story is built,
  `spec-marshal-recall-in-the-loop` still governs `adapters/harness_bmadloop.py` and is reconciled too.

**Never:**
- Never inject a block for a miss, a failure or a disabled layer, and never synthesize a recall sentence.
- Never run more than one successful `scribe recall` per story dispatch, and never read a block cached for another
  story or run.
- Never edit bmad-loop's installed package or vendor it; never change scribe's capture or grounding.
- Never let a recall failure refuse, block or delay a launch beyond the scribe call's own timeout.
- Never change the other five `[context]` layers or the dispatch prompt's existing lines.

**Residual risk:**
- A grounded recall depends on team memory holding a capture that matches the station query (`feedback corrections
  guidance for <slug>`). The manual check below proves the path once; whether captures ground for every station is a
  property of the memory, not of this story.
- bmad-loop's plugin API is upstream's. A later bmad-loop that renames `pre_session` or `proposed_prompt` breaks the
  hook; the era-pin tests (AD-78) are where that shows.

## I/O & Edge-Case Matrix

| Engine | Layer | Scribe | At `47397de509` | After |
|---|---|---|---|---|
| dispatch | enabled | grounded | no call; envelope reads `enabled: true` | block appended; `recall.outcome: grounded` |
| dispatch | enabled | miss | no call | no block; `outcome: miss` |
| dispatch | enabled | fails | no call | no block; `outcome: failed`, WARN; launch proceeds |
| dispatch | disabled | — | no call | no call, no block; `outcome: disabled` |
| bmad-loop dev, then review | enabled | grounded | no call (`[plugins] enabled = []`) | plugin enabled; both prompts end with the same block; one call |
| bmad-loop | disabled | — | no call | plugin not enabled; no call |
| two stories, one station | enabled | grounded | (never wired) | one call each; no cross-story block |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-11 (recall is built and never runs) entry, and
  the dated section "2026-10-11 — The review bot remembers the correction you gave two weeks ago (folded from
  marshal-recall-in-the-loop)".
- Epic: Epic 93 (a new fix epic, because Epic 47, which built the fold, is `done`).
- Ledger key: `93-1-every-live-session-gets-the-recall-its-layer-promises-and-the-run-records-the-outcome`.
- Ledger status at mint: `backlog`.
- Deps: none.
- Surface: `[epic_surfaces]` `"93"` in `marshal-policy.toml` (the default surface, the deferred-work ledger, and every
  Spec memlog).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python scripts/spec_surface_reconcile.py` — expected: exit 0 (the derived surface guard).

**Manual checks (not a dispatch gate):**
- The mutations of AC7 — expected: each fails its named test. Restore each.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and scoped
  stamps.
- One real dispatch run with `[context.recall]` enabled, against a station whose query a team-memory capture grounds:
  its launch INTENT in the run's `journal.jsonl` carries `recall.attempted: true` and `recall.outcome: grounded`, and the
  session's prompt (the dispatch log) ends with the labelled block and its `.claude/memory/**` citation. Record the run
  id in the Auto Run Result.

## Named, not fixed here

- **`run_resume` and recall.** Whether a resumed `bmad-loop` run re-queries is the 2026-09-20 review's question 3; with
  the cache keyed to the story dispatch, a resumed run reads its own dispatch's block. Nothing else is decided here.
- **Reverse-direction capture.** A correction a review pass surfaces is not captured back into scribe; the folded Spec
  carries this as a non-goal (a separate capability if pursued).
