---
title: 'Escalation queue'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: []
baseline_revision: '0e021d10cd0f39dc3f056bd2fc81f4e23d775f5f'
---

<intent-contract>

## Intent

**Problem:** `marshal status`'s fleet view (Story 5.1) already derives `"paused-on-escalation"` as a state value, but a run blocked on a human decision is buried alphabetically/arbitrarily among every other home -- nothing surfaces it first, and nothing names WHAT decision is needed without a separate `--run` drill-down (Story 5.2). FR-38 closes this: escalated rows sort to the top, carry their own reason and the artifact needing a decision inline, and are available as a standalone filtered view for scripting.

**Approach:** extend the SAME fleet-summary path (Code Map: `core/status.py`, `cli/status.py` -- no new files). `RunStatusSnapshot`'s own `paused_reason`/`escalated_spec_file`/`escalated_task_phase` fields (already read by `_gather_home_facts` for Story 5.1, just not threaded through) are added to `FleetHomeFacts`/the row dict -- reused, never re-derived. `core/status.py` gains a pure sort key (escalated rows first, stable otherwise) applied to `data.homes`. `--escalations` (a new boolean flag) filters the SAME report to escalated rows only -- a scripting-friendly standalone view, never a second command or a second read path.

## Boundaries & Constraints

**Always:**
- **Escalated rows (`state == "paused-on-escalation"`) sort FIRST in `data.homes`**, stable otherwise (every other row keeps its existing relative order) -- a pure sort applied once, after every row is already built, never re-ordering the underlying fleet enumeration itself.
- **Each escalated row carries its own `escalation_reason` (from `RunStatusSnapshot.paused_reason`) and `escalation_artifact` (from `escalated_spec_file`, falling back to `escalated_task_phase` when no spec file is recorded)** -- both already-shipped `RunStatusSnapshot` fields, reused verbatim, never re-derived from the journal a second way.
- **`--escalations` filters `data.homes` to ONLY escalated rows** -- the SAME single fleet read/gather pass Story 5.1 already performs, just a post-filter on the already-built row list; never a second sweep, never a different evidence source than the unfiltered view.
- **A fleet with zero escalations under `--escalations` reports a clean, empty `data.homes: []`** -- never an error, never a "nothing to see" finding.
- **The text rendering visually distinguishes an escalated row** (a marker prefix, e.g. `[ESCALATED]`) from every other state -- machine-readable output (`--format json`) carries the identical fields either way (NFR-12's own precedent, already established by Story 5.2).

**Never:**
- No new read primitive, no new journal fold, no new harness call -- every fact this story surfaces is already gathered by Story 5.1's own `_gather_home_facts`.
- Do not touch the `--run` per-run detail view (Story 5.2) -- that already reports escalation state for ONE run; this story is the fleet-wide SORT/FILTER, a different concern.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Zero escalated homes | Normal fleet | `data.homes` unchanged in order | No finding |
| One or more escalated homes among others | Mixed fleet | Escalated rows first, stable order otherwise | No finding |
| `--escalations` with zero matches | Nothing paused | Clean, empty `data.homes: []` | No finding |
| `--escalations` with matches | Some paused | Only those rows, same fields as the unfiltered view | No finding |
| An escalated row with no `escalated_spec_file` recorded | Falls back to task phase | `escalation_artifact` names the phase instead | No finding |
| `--escalations` combined with `--project SLUG` | Scoped + filtered | Both apply together (scope first, then filter) | No finding |

</intent-contract>

## Code Map

- `src/pyforge/marshal/core/status.py` -- EDIT. `FleetHomeFacts` gains `paused_reason`/`escalated_spec_file`/`escalated_task_phase`; `build_fleet_row` includes `escalation_reason`/`escalation_artifact` in the row dict; a new pure `sort_fleet_rows(rows) -> list[dict]` (escalated-first, stable).
- `src/pyforge/marshal/cli/status.py` -- EDIT. `_gather_home_facts` threads the three new snapshot fields through; `add_status_subparser` gains `--escalations`; `run_status`'s fleet path applies `sort_fleet_rows` always, then filters when `--escalations` is set; `_render_text_status` marks escalated rows.
- `tests/unit/test_status.py` -- EDIT. Sort/filter matrix.

## Verification

- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`

## Review Triage Log

### 2026-08-07 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 0
- patch: 1 (high 1)
- defer: 0
- reject: 0
- addressed_findings:
  - `[high]` `[patch]` **`escalation_reason`/`escalation_artifact` were populated from the raw `RunStatusSnapshot` facts unconditionally, never gated on the DERIVED `state` -- so a home that was BOTH escalated AND had a dead supervisor (or a finished run with a stale `paused_stage`) reported `state: "unsupervised"`/`"stopped"` (correctly, via `derive_home_state`'s own already-established precedence) while STILL carrying real escalation data in its JSON payload, silently excluded from `sort_fleet_rows`/`--escalations` (both key on `state`) despite being exactly the "needs a human decision" case this story exists to surface.** Independently found by BOTH reviewers as the single most severe finding against this story (the 7th story in this epic's own review history where both reviewers converged on the identical top finding). Fixed: both fields are now gated on `state == "paused-on-escalation"`, `None` otherwise -- and the `escalation_artifact` fallback now uses an explicit `is not None` check (folding in a related low-severity finding: `or` would have silently treated a legitimately empty-string spec file as absent). New tests: `test_escalated_but_dead_supervisor_reports_unsupervised_with_null_escalation_fields`, `test_escalated_but_finished_reports_stopped_with_null_escalation_fields`.
- deferred: none this pass.
- rejected: none this pass.

## Suggested Review Order

**The correctness fix — start here**

- `build_fleet_row`'s escalation-field gating on the derived `state`.
  [`core/status.py`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py) — search `escalated = state ==`

**Tests (peripherals)**

- The two new dead-supervisor/finished-but-stale-escalation regression tests.
</intent-contract>
