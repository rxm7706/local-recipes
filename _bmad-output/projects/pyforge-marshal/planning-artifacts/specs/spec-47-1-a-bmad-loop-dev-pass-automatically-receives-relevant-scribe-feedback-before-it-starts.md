---
title: '47.1: A bmad-loop dev pass automatically receives relevant scribe feedback before it starts'
type: 'feature' # feature | bugfix | refactor | chore
created: '2026-09-18'
status: 'ready-for-dev' # draft | ready-for-dev | in-progress | in-review | done | blocked
baseline_revision: '4733295ea59e2bffe5407fea9bb47513d108b8ea'
review_loop_iteration: 0 # incremented by step-04 before each review loopback
followup_review_recommended: false # set by step-04 on status: done; step-01 READS this — false HALTs, true allows one follow-up then forces false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-recall-in-the-loop/SPEC.md']
deferred: [] # append-only machine-readable deferred review findings; each item carries summary/evidence and optional location/severity
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Scribe's `recall` primitive is real, shipped and grounded, but it does not reach a
`bmad-loop` dev pass on its own. Stories 47.2–47.4 shipped the injection plumbing (the
`recall-feedback.md` cache with its one-query marker, the prompt-fold helper, the `[context.recall]`
gate, the CAP-4 empty branch), but the query it runs is the planning-graph shape: `ScribeCli.recall`
always renders `--mode planning` (kinds `doc`, `memlog`), and `inject_recall_feedback` passes
`scope=<station-slug>`, which scribe's `_citation_in_scope` narrows to `_bmad-output/projects/<slug>/`.
A `.claude/memory/{feedback,project,reference}/*.md` capture (kind `memory`) can therefore never
ground — the 2026-09-20 intent gap.

**Approach:** Operator ruling 2026-10-10 ("Marshal --mode memory (Recommended)"): a marshal-only
change. `render_scribe_recall_argv` and `ScribeCli.recall` gain a recall-mode parameter whose
default stays `planning`, so every existing caller's argv is unchanged; `inject_recall_feedback`
asks for `memory` with no scope, so the dev-pass query is `scribe recall <query> --mode memory`.
Team memory is repo-wide, so the query carries no `--scope`. Scribe is untouched.

## Boundaries & Constraints

**Always:**
- Reach scribe only through its CLI (`adapters/scribe_cli.py`), never `import pyforge.scribe`.
- The dev-pass query is `--mode memory` with no `--scope` and no `--kind` (`--mode` and `--kind`
  are exclusive in scribe's CLI).
- Every other caller keeps its argv byte for byte: `marshal context retrieve` and the planning-graph
  layer still render `--mode planning` plus `--scope <slug>` (`cli/context.py`).
- Keep what 47.2–47.4 shipped: one `scribe recall` per story dispatch (the `.query-ran` marker), the
  labeled block (`RECALL_FEEDBACK_HEADER`), the `[context.recall]` gate, fail-open on an unavailable
  scribe (WARN, never dispatch-blocking), and CAP-4's rule that a miss injects nothing.
- Scope stays `bmad-loop` dev passes; `bmad-build-auto` dispatch sessions are out of scope.
- Fix each defect where the behaviour lives and pin it with a test that fails without the fix.

**Never:**
- Never edit `pyforge-scribe`: no scope rule admitting `.claude/memory/**`, no new scribe flag.
- Never inject text on a grounded miss, a failed query or a skipped query — no synthesized "no
  relevant corrections found" line (CAP-4).
- Never write to scribe's capture store; this path is a read-only consumer.
- Never forward an unrecognized recall mode to the subprocess.
- Never wire `augment_bmad_loop_session_prompt_with_recall` into a live `bmad-loop` launcher here
  and never close `DW-marshal-47-2` / `DW-marshal-47-3`: that seam is outside this story.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Grounded team-memory hit | `scribe recall <query> --mode memory` prints a body and `[source: .claude/memory/feedback/<x>.md]` | `recall-feedback.md` holds the labeled block ending `Source: .claude/memory/feedback/<x>.md`; the dev-role prompt fold appends it; `injected=True` | No error expected |
| Grounded miss | scribe prints `no grounded answer found` | empty string written, no block in the prompt, `injected=False`, `ok=True` | No error expected |
| `scribe` CLI unavailable | binary unresolved, non-zero exit or timeout | no block; `ok=False` with a reason; dispatch proceeds | WARN-level only, never blocks dispatch |
| No resolvable station slug | dispatch context lacks a station | query skipped (no loop-home target to write), `attempted=False` | No error expected |
| Planning-graph retrieve | `ScribeCli.recall` called with no mode, with or without a scope | argv unchanged: `recall <q> --mode planning [--scope <slug>]` | No error expected |
| Unrecognized mode | a caller passes a mode other than `planning` or `memory` | refused before any subprocess starts | Error raised to the caller, never forwarded |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/planning_graph.py` -- `render_scribe_recall_argv` (:94), the one place the recall argv is spelled; hardcodes `--mode planning` today.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/scribe_cli.py` -- `ScribeCli.recall` (:240), routes through the renderer with no mode override.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` -- `inject_recall_feedback` (:1365) passes `scope=station_slug` at :1385; `augment_bmad_loop_session_prompt_with_recall` (:1420) folds the cached block.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/context.py` -- `marshal context retrieve` (:541), the planning-graph caller whose argv must not move.
- `src/shared/packages/pyforge-marshal/tests/unit/test_planning_graph.py` (`TestRecallArgvScope`), `tests/unit/test_harness_bmadloop_recall.py` (its `_FakeScribeCli.recall` double and the scope assertion in `test_scopes_the_recall_call_by_station_slug_and_runs_it_against_repo_root`, which this ruling inverts), `tests/unit/test_cli_context_retrieve.py`.

## Tasks & Acceptance

**Acceptance Criteria:**
- Given `inject_recall_feedback` runs for a station, when it calls scribe through the real `ScribeCli` with a recording `ProcessPort`, then the argv is exactly `(<scribe>, "recall", build_recall_query(<slug>), "--mode", "memory")`: no `--scope`, no `--kind`, `--mode` once. The test uses the real adapter, not the `_FakeScribeCli` double, and fails if `--mode planning` or `--scope` returns.
- Given `render_scribe_recall_argv` or `ScribeCli.recall` is called without a mode, when the planning-graph layer or `marshal context retrieve` runs, then the argv is byte-identical to today's, and the existing `TestRecallArgvScope` and `test_cli_context_retrieve.py` assertions pass unchanged.
- Given a recall mode other than `planning` or `memory`, when the renderer is called, then it refuses before any subprocess starts.
- Given scribe stdout whose `[source: …]` line cites `.claude/memory/feedback/<x>.md`, when the dev-pass path runs, then `recall-feedback.md` carries the labeled block with `Source: .claude/memory/feedback/<x>.md`, and `augment_bmad_loop_session_prompt_with_recall(role="dev")` returns the prompt with that block appended. The test feeds the stdout through `parse_recall_output`, so the `.claude/memory/**` citation grounds end to end on marshal's side.
- Given a grounded miss, a non-zero exit or a missing binary under the new query, when the dev-pass path runs, then no text is injected and 47.2's one-query marker, 47.3's layer gate and 47.4's empty branch behave as their own tests already pin (all stay green).
- Given the recall query fails and the `recall-feedback.md` write also fails, when `inject_recall_feedback` returns, then its `reason` names both failures, never the write failure alone (the 2026-09-20 review's low `[patch]` finding, still present in the shipped code).
- Given this story lands, when `DW-marshal-47-1-intent-gap-2026-09-20` is read, then it is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` of the `mode="memory"` call. `DW-marshal-47-2` and `DW-marshal-47-3` stay open.

## Design Notes

The ruling picks option (a) of the 2026-09-20 review's question 1. Option (b), dropping the scope
while keeping `--mode planning`, would still exclude kind `memory`. Option (c), extending scribe's
`_citation_in_scope`, is scribe-owned and outside this Spec's read-only-consumer constraint.

Probe, 2026-10-10, primary checkout: `pixi run --frozen -e pyforge-guild scribe recall "feedback corrections guidance for pyforge-marshal" --mode memory` exited 0 with a grounded answer whose last line is `[source: .claude/memory/project/2026-10-08-marshal-story-47-2-cap-2-implemented-in-dispatch.md]`. The same query with `--mode planning --scope pyforge-marshal` cited a planning memlog.

The review's question 2 (a file versus a prompt) is settled by what shipped: both, the cache file and the prompt fold. Its question 3 (`run_resume`) stays behind the open launcher seam.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010/011 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010/011 binding).
- `python scripts/spec_surface_reconcile.py` — expected: exit 0 (the derived surface guard; `spec-marshal-recall-in-the-loop` and `spec-pyforge-marshal` memlogs name every governed path this story moves).

**Manual checks:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test -k recall` — expected: every new and existing recall test passes, through fixture scribe output and a recording `ProcessPort`, never a live scribe process.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild scribe recall "feedback corrections guidance for pyforge-marshal" --mode memory`, from a checkout with a compiled graph — expected: a grounded answer whose `[source: …]` line is under `.claude/memory/`.

## Spec Change Log

- 2026-10-10 — Operator ruling on the 2026-09-20 intent gap ("Marshal --mode memory (Recommended)"). Changed: Problem, Approach, Boundaries, the I/O matrix, Code Map, Acceptance Criteria, Design Notes and Verification are re-derived for the `--mode memory`, no-scope query. The old Always bullet mandating `--scope <station-slug>` is withdrawn. Known-bad state avoided: a green suite whose query can never ground a `.claude/memory/**` capture. KEEP: 47.2's one-query marker, 47.3's layer gate, 47.4's empty branch, fail-open on an unavailable scribe, the `bmad-loop`-only scope. Status moves from `blocked` to `ready-for-dev`; the ledger key moves from `blocked` to `backlog` with the operator's answer as the confirmation.

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

### 2026-10-10 — Operator ruling: the 2026-09-20 intent gap is resolved (Marshal --mode memory)

- ruling (verbatim answer): "Marshal --mode memory (Recommended)"; the option read: "Dev-pass query runs scribe recall --mode memory with no station scope (team memory is repo-wide); marshal-only change, scribe untouched. bmad-spec re-derives CAP-1, then 47.1 is flipped and dispatched."
- question 1 (grounding): resolved as option (a). Marshal's `ScribeCli.recall` and `render_scribe_recall_argv` take a mode, and the dev-pass query runs `--mode memory` with no `--scope`. Scribe's `_citation_in_scope` is unchanged.
- question 2 (file or prompt): settled by what Stories 47.2–47.4 shipped. It is both: `recall-feedback.md` with its one-query marker, and `augment_bmad_loop_session_prompt_with_recall` folding the block into the dev and review prompt. No in-tree `bmad-loop` launcher calls the helper yet (`DW-marshal-47-2`, `DW-marshal-47-3`, both open); this story does not take that seam.
- question 3 (`run_resume`): stays behind the same launcher seam; not in this story.
- the lower findings, re-read against the shipped code: the double-failure branch still returns only the write-failure reason (`inject_recall_feedback`, the `except (OSError, PyforgeError)` return precedes the `if not outcome.ok` check), so it is now an acceptance criterion; the `MRS-SPIN-018` WARN wording no longer applies (that code now names the supervisor-spawn finding and no shipped caller reports a recall WARN); the `_await_file` fix was reapplied with its docstring (`tests/unit/test_harness_bmadbuild.py:403`).
- chain: memlog entries on `spec-marshal-recall-in-the-loop` (the ruling verbatim, the question-2 settlement, the re-derived CAP-1); the `SPEC.md` re-render was refused by the session hook and is the parent session's to land. `DW-marshal-47-1-intent-gap-2026-09-20` carries a `ruled:` line and stays open until this story lands. Status `ready-for-dev`; ledger `blocked` → `backlog`, operator-confirmed by this answer.
