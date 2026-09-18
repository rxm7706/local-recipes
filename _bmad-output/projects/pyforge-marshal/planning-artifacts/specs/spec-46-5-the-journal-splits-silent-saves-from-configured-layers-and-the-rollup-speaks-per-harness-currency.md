---
title: '46.5: The journal splits silent saves from configured layers, and the rollup speaks per-harness currency'
type: 'feature'
created: '2026-09-18'
status: 'in-progress'
baseline_revision: '887d02532d8cbe1489b21646ea2331a9494e1ee7'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
warnings: [oversized]
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** As an operator reading savings, I want the journal taxonomy to distinguish silent saves (repo default) from configured layers, and the rollup keyed per harness × binding currency, So that a Cursor-first station never reads a Claude-shaped number as its own — USD for Claude, quota-burn for Cursor/Copilot, request-count for Gemini, ACUs for Devin, never one blended token number.

**Approach:** `core/layer_savings_sources.py` journal schema and the rollup report surface.

Ledger key: `46-5-the-journal-splits-silent-saves-from-configured-layers-and-the-rollup-speaks-per-harness-currency`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / S-46.4.

### Living CAP citations

- `spec-pyforge-marshal` CAP-193 (fold remint of `spec-marshal-token-economy` CAP-20; `spec-marshal-token-economy` is absorbed — cite living numbers).
- Living: `spec-pyforge-marshal CAP-193` ← `spec-marshal-token-economy CAP-20`.

## Acceptance Criteria

- Given runs on at least two harnesses with different binding currencies When the rollup renders Then each harness's savings appear in their own currency with no blended total And silent saves and configured layers are distinguishable per journal row

## Boundaries & Constraints

**Always:** Implement only the Surface named in epics.md. Keep ACs machine-checkable. Physical `_bmad-output/projects/pyforge-marshal/` paths.

**Never:**
- Do not mint a new story key or flip `sprint-status-ledger.yaml`.
- Do not run `scripts/bmad-switch`; pin `BMAD_ACTIVE_PROJECT=pyforge-marshal` and physical paths.
- Do not cite absorbed `spec-marshal-token-economy` CAP-19..24 as living numbers; use CAP-192..197.
- Do not flip the parent Dream to `realized` (benchmark artifact is the realized-guard).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| runs on at least two harnesses with different binding currencies | the rollup renders | each harness's savings appear in their own currency with no blended total | named finding / refuse |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/layer_savings_sources.py` -- Surface file. Pure JSONL readers, no `core/journal.py` domain-model import (module docstring: "no subprocess, no imports of headroom/cocoindex/graphify"). `read_dispatch_idle_timing` (~L169-215) is the exact pattern to mirror: globs `_bmad-output/projects/<slug>/implementation-artifacts/dispatch-runs/*/journal.jsonl`, manually `json.loads` per line, reads `entry["payload"]`/`entry["kind"]` by hand.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/harness.py` -- `LayerSavings` (~L234), 5 fields: `output_compression_saved`, `wire_compression_saved`, `graph_hits_vs_file_reads`, `derived_context_cache_hits`, `planning_graph_tokens_saved`. These are the exact keys the journal's `layer_savings` payload dict carries (read-only reference; do not edit).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch.py:37` -- `KIND_DISPATCH_LAUNCH = "dispatch-launch"`. `cli/dispatch.py` (~L2141) already writes this kind's `Phase.OUTCOME` entry with payload key `"harness_profile"` (the running harness's profile name, e.g. `"claude"`). Read-only reuse -- no write-path changes needed.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/__main__.py:426` -- `_BUDGET_USAGE_KIND = "budget-usage"`; `_budget_usage_payload` (~L449-482) already writes each run's `layer_savings` dict under this kind. Both this kind and `dispatch-launch` land in the SAME per-run `journal.jsonl`, so the join is a single-file read. Read-only reuse.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py` -- the rollup report surface. `run_status` (L1412+) computes `git_repo_root` and, when `args.project` is set, builds `data["homes"] = rows` at L1937. `_format_savings_summary` (L198) is the sibling per-home formatter; `_render_text_status` (L2259+) is where it's called (~L2285). Add the new reader's output here.
- `src/shared/packages/pyforge-marshal/tests/unit/test_layer_savings_sources.py` -- existing unit-test file for the Surface module; add coverage here.
- `src/shared/packages/pyforge-marshal/tests/unit/test_status.py` -- existing unit-test file for `cli/status.py`; add rollup-rendering coverage here.

## Tasks & Acceptance

**Execution:**
- `core/layer_savings_sources.py` -- add `SILENT_LAYER_KEYS = ("output_compression_saved", "graph_hits_vs_file_reads", "derived_context_cache_hits", "planning_graph_tokens_saved")` and `CONFIGURED_LAYER_KEYS = ("wire_compression_saved",)` (the 4 repo-default layers Story 46.4 makes harness-agnostic vs. the 1 capability/config-resolved wire layer) plus `classify_layer_kind(layer_key: str) -> str` returning `"silent"`/`"configured"`, raising `ValueError` on an unrecognized key -- the single source of truth for the taxonomy.
- `core/layer_savings_sources.py` -- add `HARNESS_CURRENCY: dict[str, str] = {"claude": "usd", "cursor": "quota-burn", "copilot": "quota-burn", "gemini": "request-count", "devin": "acus"}`, `UNKNOWN_HARNESS_CURRENCY = "unknown"`, and `currency_for_harness(profile_name: str | None) -> str` (never raises; returns `UNKNOWN_HARNESS_CURRENCY` for `None`/unrecognized names) -- the per-harness binding-currency table.
- `core/layer_savings_sources.py` -- add `read_rollup_by_harness(repo_root: Path, *, project_slug: str = "pyforge-marshal") -> dict[str, object]`, mirroring `read_dispatch_idle_timing`'s manual-JSONL-scan idiom. Per run under `dispatch-runs/*/journal.jsonl`: extract `harness_profile` from the `dispatch-launch` kind's outcome-phase entry, and the `layer_savings` dict from that run's LAST `budget-usage`-kind entry (last-write-wins per run, matching `cli/status.py::_gather_run_journal_facts`'s own convention); skip runs missing either. Bucket each `layer_savings` key's value into `silent`/`configured` (via `classify_layer_kind`) under a per-harness entry carrying that harness's own `currency` (via `currency_for_harness`) and a `runs` count. Return `{"status": "ok"|"no-dispatch-journals"|"no-savings-samples", "harnesses": {<profile_name>: {"currency": ..., "silent": {...}, "configured": {...}, "runs": N}}}` -- never a cross-harness summed total.
- `core/layer_savings_sources.py` -- add `classify_layer_kind`, `currency_for_harness`, `HARNESS_CURRENCY`, `UNKNOWN_HARNESS_CURRENCY`, `read_rollup_by_harness` to `__all__`.
- `cli/status.py` -- import `from ..core import layer_savings_sources`. In `run_status`, immediately after `data["homes"] = rows` (L1937), when `args.project is not None`: `data["savings_rollup_by_harness"] = layer_savings_sources.read_rollup_by_harness(git_repo_root, project_slug=args.project)`. Whole-fleet status (`args.project is None`) does not compute a cross-project rollup -- each project's dispatch-runs are scoped to that project only.
- `cli/status.py` -- add `_format_rollup_by_harness(rollup: Mapping[str, object]) -> str`, sibling of `_format_savings_summary` (L198): one line per harness, `"{harness} ({currency}): silent={silent_dict} configured={configured_dict}"`; empty/`"no-dispatch-journals"`/`"no-savings-samples"` status returns `""`. Call it from `_render_text_status` (~L2285, alongside the existing `_format_savings_summary` call) when `data.get("savings_rollup_by_harness")` is present, appended as its own line(s) -- never summed into `savings_text`.
- `tests/unit/test_layer_savings_sources.py` -- unit-test `classify_layer_kind` (each silent key, the configured key, an unknown key raises), `currency_for_harness` (each of the 5 known names, `None`, and an unrecognized name), and `read_rollup_by_harness` against a synthetic two-harness `dispatch-runs/<run>/journal.jsonl` fixture (one run's `dispatch-launch` outcome payload naming `"claude"`, another naming `"cursor"`, each with a distinct `budget-usage` `layer_savings` payload) -- the I/O Matrix scenario.
- `tests/unit/test_status.py` -- unit-test `_format_rollup_by_harness` renders both harnesses' currencies with no blended total, and that `run_status`'s envelope carries `savings_rollup_by_harness` only when `--project` is given.

**Acceptance Criteria:**
- Given a project's `dispatch-runs/` journals span at least two distinct `harness_profile` values (e.g. `claude` and `cursor`), when `marshal status --project <slug>` renders, then the envelope's `savings_rollup_by_harness` and its text rendering show each harness's savings under its own `currency` string, with no single summed-across-harnesses total field or line anywhere in the output.
- Given a single run's `layer_savings` payload, when `read_rollup_by_harness` classifies its keys, then every one of the 5 `LayerSavings` field names resolves to exactly one of `"silent"` or `"configured"` per `classify_layer_kind`, matching Story 46.4's harness-agnostic-repo-default (output/structure-graph/derived-context/planning-graph) vs. capability-resolved (wire) split.
- Given a run whose journal has a `budget-usage` entry but no `dispatch-launch` outcome entry (or vice versa), when `read_rollup_by_harness` scans it, then that run is skipped (not counted under an `"unknown"` bucket) -- an incomplete run contributes no partial data.

## Design Notes

The join is READ-ONLY and single-pass per file: nothing in `cli/dispatch.py`, `supervisor/__main__.py`, or `core/policy.py` (the write paths) changes. `harness_profile` is already durably written into the SAME `journal.jsonl` a run's `budget-usage` entries live in (`cli/dispatch.py`'s `dispatch-launch` outcome payload), so the per-harness split is purely a read-time correlation keyed by `run_id` (the journal filename's parent directory) -- no new journal schema field, no sidecar, no second file.

`currency_for_harness` never raises, mirroring this epic's "a repo default can never claim a wrap a harness can't perform" ethos (epic-46-context.md): an unrecognized or absent harness name degrades to the honest `"unknown"` currency label rather than a crash or a silent USD default that would misrepresent a non-Claude station's savings.

`classify_layer_kind` DOES raise on an unrecognized key -- unlike the currency lookup, an unknown `LayerSavings` field name is a programmer error (a new layer added to `ports/harness.py` without updating this taxonomy), not user-facing data absence, and should fail loud in tests rather than silently mis-bucket.

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pyforge-marshal-test` -- expected: full station suite green, including the new `test_layer_savings_sources.py` and `test_status.py` cases.
- `pixi run -e pyforge-marshal marshal status --project pyforge-marshal --format json` -- expected: valid envelope; `savings_rollup_by_harness` key present (possibly `{"status": "no-dispatch-journals", "harnesses": {}}` if this worktree's own `dispatch-runs/` is sparse -- not a failure, a real "no data yet" state).

## Source

Contract recovered from `epics.md` Story 46.5 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.
