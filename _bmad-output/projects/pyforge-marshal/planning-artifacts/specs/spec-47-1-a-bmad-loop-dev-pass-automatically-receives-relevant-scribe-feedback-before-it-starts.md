---
title: '47.1: A bmad-loop dev pass automatically receives relevant scribe feedback before it starts'
type: 'feature' # feature | bugfix | refactor | chore
created: '2026-09-18'
status: 'blocked' # draft | ready-for-dev | in-progress | in-review | done | blocked
baseline_revision: '2f98ede57d5ebb7df285bbd1383782cf6a7c86af'
review_loop_iteration: 0 # incremented by step-04 before each review loopback
followup_review_recommended: false # set by step-04 on status: done; step-01 READS this — false HALTs, true allows one follow-up then forces false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-recall-in-the-loop/SPEC.md']
deferred: [] # append-only machine-readable deferred review findings; each item carries summary/evidence and optional location/severity
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Scribe's `recall`/`capture` primitive is real, shipped, and grounded (a genuine miss
is explicit, never an invented answer) — but it doesn't reach forward on its own. A correction
captured today doesn't automatically show up in the next `bmad-loop` dev pass working nearby
code; a human has to remember to run `scribe recall` and paste the result in by hand.

**Approach:** Before a `bmad-loop` dev pass (`bmad-dev-auto`) launches, `harness_bmadloop.py`
shells `scribe recall --scope <station-slug>` (CLI subprocess, never a direct `pyforge.scribe`
import — Scribe stays the sole owner of capture/compile per the parent Spec's own constraint) and,
if the answer is grounded, folds it into the dev-pass session's starting context as a
clearly-labeled block.

## Boundaries & Constraints

**Always:**
- Query scoped by `--scope <station-slug>`, reusing the mechanism `scribe-marshal-fact-visibility`
  CAP-1 already proves — never a narrower per-file-glob scope (this story's own resolution of the
  parent Spec's Open Question 1).
- One `scribe recall` subprocess call per story dispatch, run before the dev-pass session launches.
- The injected context block is clearly labeled as scribe-sourced feedback, distinguishable from
  the story's own spec/intent-contract content.
- Reach Scribe only through its CLI (`scribe recall ...` subprocess) — never `import
  pyforge.scribe`, matching this Spec's "read-only consumer" constraint.
- Scoped to `bmad-loop` dev passes only in this story — `bmad-build-auto` dispatch is explicitly
  out of scope here (this story's own resolution of Open Question 2, matching the source Dream's
  literal text).

**Never:**
- Never treat a recall failure (subprocess error, scribe unavailable) as a dispatch-blocking
  error — degrade silently to no injected context, same fail-open discipline this fleet's other
  live-query findings already use (e.g. doctor CAP-2/CAP-14).
- Never write to scribe's own capture store from this path — read-only consumer only.
- Never inject a fabricated or synthesized confidence claim when the query fails or times out —
  absence of a block is the correct behavior (Story 47.4 owns the "genuine empty hit" case; this
  story owns "the query didn't run at all," which behaves identically — no block).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Relevant feedback exists | `scribe recall --scope <slug>` returns a grounded hit for the story's station | Dev-pass session context includes the labeled feedback block before it starts working | No error expected |
| No relevant feedback | `scribe recall` returns a grounded miss (Story 47.4's own scope) | No block injected | No error expected |
| `scribe` CLI unavailable | subprocess exits non-zero or times out | No block injected; dispatch proceeds unaffected (fail-open) | Warn-level log only, never blocks dispatch |
| Story with no resolvable station slug | dispatch context lacks a station scope | Recall query skipped entirely (nothing to scope it to) | No error expected |

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-011 binding corrected 2026-09-19 — the `-k recall` scoping is a manual check below, not the declared command).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-011 binding corrected 2026-09-19 — the `-k recall` scoping is a manual check below, not the declared command).

**Manual checks:**
- `pixi run -e pyforge-marshal pyforge-marshal-test -k recall` -- expected: all new tests pass,
  covering every I/O matrix row above via fixture `scribe recall` output, not a live scribe
  process
- `pixi run -e pyforge-marshal marshal factory dispatch pyforge-doctor <a real backlog story>`
  (manual smoke, read-only recall query only) -- expected: the dispatch's own session log shows
  the recall query ran and, if scribe has a relevant entry for pyforge-doctor, that it was folded
  into context

## Review Triage Log

### 2026-09-20 — Review pass
- verdicts: 15 findings — high 7, medium 1, low 4, false 3, maybe-false 0
- findings:
  - `[high]` `[intent_gap]` (Blind Hunter) Recall query hardcodes `--mode planning` (`render_scribe_recall_argv`, `core/planning_graph.py:108`), which resolves to kinds `{doc, memlog}` and excludes `kind="memory"` — the kind `.claude/memory/{feedback,project,reference}/*.md` captures compile to (`pyforge-scribe/.../compile.py:383`) — so a grounded hit can never surface real team-memory feedback content. — Verified directly: `ScribeCli.recall()` (`adapters/scribe_cli.py:221-242`) routes unconditionally through `render_scribe_recall_argv` with no mode override; `RECALL_MODE_KINDS["planning"] = frozenset({"doc","memlog"})` (`pyforge-scribe/.../recall.py:51-55`). No single-owner code change resolves this without a mode/kind decision the spec never made; grouped with the two following findings and the Verification Gap finding below under the same root cause.
  - `[high]` `[intent_gap]` (Blind Hunter) Independently of mode, scribe's own `_citation_in_scope()` (`pyforge-scribe/.../recall.py:143-159`) only admits citations under `_bmad-output/projects/<scope>/` or `presentations/<scope>/facts.yaml` — a `.claude/memory/**` citation matches neither, so even a mode fix would still be blocked by the mandatory `--scope <station-slug>` the Boundaries require. — Verified by reading the full function and its own docstring ("every other citation shape... is excluded rather than guessed at"). Same root cause as the mode finding above (the Boundaries' mandated scoping mechanism is structurally incompatible with the Problem statement's target content); shares that group and route.
  - `[high]` `[intent_gap]` (Blind Hunter) Nothing in the repo reads `recall-feedback.md` back into a live dev-pass session's context; the Approach's "folds into the dev-pass session's starting context" has no implementation. — Verified: no reference to `recall-feedback.md` anywhere outside the new code itself; `step-01-clarify-and-route.md`'s context-assembly step never names it. Grouped with the Edge Case Hunter and Intent Alignment Auditor findings below under the same root cause (the intent-contract names an outcome — context injection — but never names the surface that performs it).
  - `[medium]` `[intent_gap]` (Blind Hunter) `run_resume` (`cli/spin.py`) never calls `inject_recall_feedback`, so a resumed dev-pass session gets no recall context at all, with no signal distinguishing that from "nothing relevant found." — Verified: `run_resume` has no call to the injection helper `run_spin` uses. The Boundaries text ("run before the dev-pass session launches") does not say whether a resumed session counts as a launch; this is a genuine ambiguity inside the intent-contract, not a scope line the plan drew — routes to intent_gap standalone (does not share the grounding or context-fold root cause).
  - `[low]` `[patch]` (Blind Hunter) The `MRS-SPIN-018` WARN message ("scribe recall for station %r did not run (%s)") is worded for the "recall never ran" case but is also used for the write-failure branch, where recall did run and only the file write failed. — Verified against the exact call site and the write-failure return path. Smallest fix is a one-line reword to a failure-agnostic message; trivial, no public surface (moot: code reverted under the intent_gap branch below, logged here since Classify precedes the routing cascade).
  - `[low]` `[patch]` (Blind Hunter) In the double-failure branch (scribe recall fails AND the fallback file write also fails), `inject_recall_feedback` returns only the write-failure reason, silently discarding the original scribe-failure reason; untested. — Verified by reading the function body: the `except` on the write attempt returns before the `if not outcome.ok` check is ever reached. Smallest fix is to concatenate both reasons; trivial, no public surface. Shares this defect and route with the Edge Case Hunter row below.
  - `[high]` `[intent_gap]` (Blind Hunter) All new tests use fake `ScribeCli`/`FsPort` doubles returning canned outcomes; none exercises the real `render_scribe_recall_argv` → scribe `answer()` filtering path, so the mode/scope defect above shipped fully green. — Verified: `pixi run -e pyforge-marshal pyforge-marshal-test -k recall` passes 49/49 against fixture doubles only. Same root cause as the grounding-impossible findings above (a test that exercised the real path would have caught it); shares that group and route.
  - `[low]` `[defer]` (Blind Hunter) The `_await_file` polling-helper fix (`test_harness_bmadbuild.py`) shipped with no comment explaining the race it fixes, and is outside this story's declared surface. — Verified: the fix had no comment, unlike the rest of this diff's annotated style. The underlying flaky-test bug is pre-existing (not caused by 47.1); the fix (and this note) is reverted along with the rest of the diff under the intent_gap branch below — a future change should reapply it independently, with a one-line comment. location: `src/shared/packages/pyforge-marshal/tests/unit/test_harness_bmadbuild.py:403`
  - `[false]` `[reject]` (Blind Hunter) `RecallInjectionResult.ok` defaults to `True` while `attempted=False`, risking a future caller misreporting a skipped recall as successful. — Refuted: the sole current caller, `run_spin`, already checks `if recall_result.attempted and not recall_result.ok:` before consulting `.ok`, so the described misreport does not occur anywhere in the shipped diff.
  - `[low]` `[patch]` (Edge Case Hunter) Double-failure branch discards the original scribe-failure `reason` when the fallback write also fails (`harness_bmadloop.py`). — Same defect and location as the Blind Hunter row above; shares its route and evidence.
  - `[false]` `[reject]` (Edge Case Hunter) The old `_await_file` returned on file-existence rather than file-content, risking a misleading timeout. — Refuted: the code under review (this diff's own fix) already guards with `if content:` before returning; the bad outcome the finding describes does not occur in the code being reviewed.
  - `[high]` `[intent_gap]` (Edge Case Hunter) No reader consumes `recall-feedback.md`; the Intent's "folds into the dev-pass session's starting context" claim is unimplemented. — Same defect as the Blind Hunter context-fold row above; shares its group and route.
  - `[high]` `[intent_gap]` (Verification Gap Reviewer, pre-verified) The recall query's hardcoded mode and mandatory scope structurally exclude the exact content (`.claude/memory/**` feedback/project/reference captures) the Problem statement names as the target, so the feature is inert for its stated purpose despite every unit test passing. — Filed disposition (`patch`) weighed and not adopted: the smallest fix adds new public surface (a mode/kind parameter) and does not, by itself, resolve the independent scribe-side scope exclusion — multiple defensible resolutions exist (extend the marshal-side call, drop the mandatory scope, or change scribe's own `_citation_in_scope`) and the spec settles none of them, so this fails patch's "no public surface" test and there is no single reading the spec supports — routes to intent_gap, not patch. Shares the grounding-root-cause group above.
  - `[false]` `[reject]` (Verification Gap Reviewer, "Other findings") The bundled `_await_file` fix is flagged as scope creep unrelated to the recall feature. — Refuted per the reviewer's own filed evidence: it "doesn't weaken any assertions"; no demonstrated harm from bundling a verified, independently-tested fix.
  - `[high]` `[intent_gap]` (Intent Alignment Auditor) The Approach's "folds into the dev-pass session's starting context" admits at least three defensible readings (direct session-context injection; artifact-drop trusting an unnamed downstream reader; marshal-side plumbing only) and the diff implements Reading B/C, not the literal Reading A the parent Spec's own CAP-1 success line states. — Verified: the intent-contract names the outcome but never names which surface performs the fold; more than one reading is defensible, satisfying the "do not infer intent unless exactly one reading" test directly. Shares the context-fold group and route above.

**Routing outcome:** `intent_gap` present (two independent root causes, both inside `<intent-contract>`) — all lower-priority entries are moot. Attempted implementation saved as `_bmad-output/projects/pyforge-marshal/implementation-artifacts/story-47-1-attempted-implementation-2026-09-20.patch`; code reverted to `baseline_revision` `2f98ede57d5ebb7df285bbd1383782cf6a7c86af` (commit `1729efda43`). HALT status `blocked`, blocking condition `intent gap`.

**Unresolved questions for whoever resolves the gap:**
1. **Grounding is structurally impossible as specified.** The Boundaries mandate `--scope <station-slug>`, reusing the `scribe-marshal-fact-visibility` CAP-1 mechanism, which hardcodes `--mode planning` (kinds `{doc, memlog}`) and, independently, scribe's `_citation_in_scope()` never admits a `.claude/memory/**` citation under any per-station scope. Does the fix (a) add a `mode`/`kind` override to `ScribeCli.recall()`/`render_scribe_recall_argv()` (new public surface, marshal-side only), (b) drop the mandatory per-station scope for this query (contradicts the Boundaries' explicit "never a narrower... scope" but the Boundaries never anticipated an *unscopable* content kind), or (c) extend scribe's own `_citation_in_scope()` to admit team-memory citations under some rule (a `pyforge-scribe`-owned change, outside this story's stated read-only-consumer boundary)? Each has a different owner and blast radius; the spec does not pick one.
2. **"Folds into the dev-pass session's starting context" names an outcome, not a surface.** Does CAP-1's deliverable end at writing a correctly-labeled `recall-feedback.md` artifact (trusting a separate, not-yet-built capability to consume it), or does this story also need to wire an actual reader into `bmad-loop`'s own session-context assembly (which lives outside this repo's control surface, as an externally-installed tool)? If the latter, which file/step is the intended read point?
3. (Lower-priority, logged but not blocking on its own) Should `run_resume` also inject recall context, or is "only the initial launch" intentional?
