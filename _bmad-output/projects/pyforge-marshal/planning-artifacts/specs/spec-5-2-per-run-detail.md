---
title: 'Per-run detail'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: []
baseline_revision: '21aad9f89e66e97717529f1f8413fb85b23cb4cc'
---

<intent-contract>

## Intent

**Problem:** `marshal status` (Story 5.1) gives one summary row per home; drilling into what actually happened in one run still means opening `journal.jsonl` by hand. FR-37/NFR-12 close this: a detail view for one run, with a machine-readable counterpart identical to what the text view shows.

**Approach:** extend the SAME `marshal status` command (Code Map: `core/status.py`, `cli/status.py` -- no new files) with a `--run <run_id> --project <slug>` pair that switches it from the fleet-summary view to a single-run detail view. The story sequence is `RunStatusSnapshot.tasks` (already read for Story 5.1's own "current story," now reported in FULL, in `state.json`'s own order). Per-story gate verdicts reuse `cli/deploy.py::_gather_gate_verdicts` (the SAME helper `run_batch_pr` already established, imported the same way `cli/land.py` already imports `cli/deploy.py`'s private helpers). Escalations/deferrals are `RunStatusSnapshot`'s own already-shipped fields (`paused_stage`/`paused_story_key`/`paused_reason`/`escalated_spec_file`/`escalated_task_phase`, and `deferred: tuple[DeferredStory, ...]`) -- read, never re-derived. Per-story consumption is grouped from the run's own journaled `"budget-usage"` observations (Story 5.1's own `_BUDGET_USAGE_KIND`, keyed by each entry's own `payload["story_key"]` this time, not just the single latest value 5.1's summary row reports). Open intents reuse `core.journal.fold`'s own `FoldResult.open_intents` field directly -- never re-derived a second way.

## Boundaries & Constraints

**Always:**
- **`--run <run_id>` requires `--project <slug>`** -- a run id alone does not name which project's Tier-3 store to look under (run directories nest per-project); given `--run` without `--project`, refuse with a registered finding, never guess.
- **The story sequence is `state.json`'s own `tasks` iteration order** -- never re-sorted, never deduplicated by this command (a duplicate `story_key` in the harness's own data is reported as-is; this command's job is to surface facts, not to editorialize).
- **Every field in the text rendering has an identical machine-readable counterpart in the SAME envelope `data`** (NFR-12's own explicit "no human-only information") -- the text view is a pure projection of `data`, exactly matching this module's own established `_render_text_status`/every other `_render_text*` convention in this package.
- **Open `intent`-phase journal entries are reported as open, each carrying what evidence it awaits** -- `FoldResult.open_intents` (Story 3.2's own already-shipped fold), reported verbatim (kind, payload, entry id) rather than re-interpreted; this command does not attempt to CLOSE or reconcile them (that stays `cli/deploy.py`'s own `_reconcile_open_intents` machinery, out of scope here).
- **A run id that does not resolve to a real run directory for the given project is a clean, reportable "not found," never a crash** -- a registered finding naming the run id and project.
- **Per-story consumption is grouped by `story_key`, taking each key's own LATEST `"budget-usage"` entry** (mirrors Story 5.1's own single-value convention, generalized from "latest overall" to "latest per key") -- a story with no budget-usage entries at all reports `null`, never a fabricated zero.

**Never:**
- No re-derivation of gate verdicts, escalation state, deferral state, or open-intent detection -- all four are ALREADY-SHIPPED reads (`_gather_gate_verdicts`, `RunStatusSnapshot`'s own fields, `FoldResult.open_intents`), reused verbatim.
- No mutation of any kind -- this is a pure read/report command, exactly like the fleet-summary view it extends.
- Do not build the escalation-queue sort/filter (Story 5.3) or the ledger-vs-git discrepancy report (Story 5.4) here -- this story is the per-run drill-down ONLY.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `--run` given without `--project` | Missing required pairing | Refused before any I/O | Registered finding |
| A run id with no matching directory | Typo/torn-down run | Reported "not found," never a crash | Registered finding |
| A run with an empty `tasks` tuple | No stories ran yet | `data.stories: []`, no crash | No finding |
| A story with a gate verdict on record | Normal case | Verdict named per story | No finding |
| A story with no gate verdict on record | Never gated | `null`, not an error | No finding |
| A run currently paused on escalation | `paused_stage == "escalation"` | Escalation section names the reason + artifact | No finding |
| A run with deferred stories | `deferred` non-empty | Every deferred story listed with its own reason/attempt | No finding |
| An open `intent` entry awaiting evidence | A crashed prior action | Listed as open, evidence named from its own payload | No finding |
| `--format json` vs default text | Either | Byte-identical field coverage (NFR-12) | No finding |

</intent-contract>

## Code Map

- `src/pyforge/marshal/cli/status.py` -- EDIT. `add_status_subparser` gains `--run`; `run_status` branches to a new `_run_detail(...)` path when `--run` is given; `_render_text_run_detail`.
- `src/pyforge/marshal/core/status.py` -- EDIT. A small pure `build_run_detail(...)` -shaped dict-builder mirroring `build_fleet_row`'s own established convention.
- `src/pyforge/marshal/core/findings.py` / `core/verdict.py` -- EDIT. Register + classify the new "run not found"/"--run without --project" codes.
- `tests/unit/test_status.py` -- EDIT. Extend with the per-run detail matrix.

## Design Notes

- **Why this extends `marshal status` rather than a new `marshal status detail`/`marshal run` command:** the AC's own framing ("I want to drill into ONE run") is explicitly a mode of the SAME fleet-status command, not a separate concept -- and the Code Map names the same two files Story 5.1 already touched, not new ones.
- **Why per-story consumption groups by `story_key` rather than reading a single "latest" value like Story 5.1's summary row does:** the AC's own wording is "per-story gate verdicts, escalations, deferrals AND CONSUMPTION" -- explicitly per-story, a genuinely different aggregation than the fleet-summary row's single home-level "budget consumed" figure.

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`

## Review Triage Log

### 2026-08-07 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 0
- patch: 2 (high 2)
- defer: 2
- reject: 0
- addressed_findings:
  - `[high]` `[patch]` **The `--run` detail path re-introduced the exact double-fold of the run's own `journal.jsonl` that Story 5.1's own adversarial review already flagged (and deferred) -- `_run_detail`/`_gather_home_facts` called `cli/spin.py::_resolve_harness_run_id_for_resume`, which independently reads+folds the identical file `_gather_run_journal_facts` had just read+folded moments earlier.** Found by the Blind Hunter. Fixed: `_RunJournalFacts` gained a `harness_run_id` field, captured from the SAME launch/resume OUTCOME entry already scanned for `pid` (the payload already carries both); both `_gather_home_facts` (Story 5.1's own fleet path) and `_run_detail` now prefer this value, falling back to the separate resolver only if the journal's own entry never recorded one. This also closes Story 5.1's own previously-deferred D2 entry.
  - `[high]` `[patch]` **A `VcsCommandError` resolving the repo root fabricated a false "confirmed absent" run report -- the filesystem was never consulted, so absence was genuinely unknown, but the code still built a `found=False` row and a second `MRS-STATUS-004` finding whose own message explicitly (and, in this branch, falsely) claims "reported, never fabricated."** Found by the Edge Case Hunter. Fixed: on this failure, report ONLY the `MRS-STATUS-002` repo-root finding, mirroring `run_status`'s own identical `VcsCommandError` handling for the fleet-summary path (which never synthesizes a second, unverified claim). New test: `test_repo_root_failure_never_fabricates_a_confirmed_absent_run`.
- deferred (not fixed in this pass, appended to `deferred-work.md` as NEW entries):
  - `[medium]` D1: a nonexistent `--project` slug and a nonexistent `--run` id under a real project both collapse into the identical `MRS-STATUS-004` signal -- not distinguishable from the report alone.
  - `[low]` D2: the reused `_gather_gate_verdicts` scopes gate verdicts to the whole PROJECT (last-write-wins across every run directory), not the specific run being inspected -- pre-existing, reused verbatim, but could mislead a reader of the per-run view into thinking a verdict pertains to the displayed run specifically.
- rejected: none this pass.

## Suggested Review Order

**The safety-critical fixes — start here**

- `_RunJournalFacts.harness_run_id` and both call sites that now prefer it over a second fold.
  [`status.py`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py) — search `harness_run_id`

- `_run_detail`'s corrected `VcsCommandError` handling (no fabricated absence).
  [`status.py`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py) — search `def _run_detail`

**Tests (peripherals)**

- The new regression test for the repo-root-failure path, plus the full per-run detail matrix.
</intent-contract>
