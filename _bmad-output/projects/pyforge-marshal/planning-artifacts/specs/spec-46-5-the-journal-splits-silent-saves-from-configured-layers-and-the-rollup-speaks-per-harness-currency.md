---
title: '46.5: The journal splits silent saves from configured layers, and the rollup speaks per-harness currency'
type: 'feature'
created: '2026-09-18'
status: 'in-review'
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
- `core/layer_savings_sources.py` -- add `read_rollup_by_harness(repo_root: Path, *, project_slug: str = "pyforge-marshal") -> dict[str, object]`, mirroring `read_dispatch_idle_timing`'s manual-JSONL-scan idiom. Per run under `dispatch-runs/*/journal.jsonl`: extract `harness_profile` from the `dispatch-launch` kind's outcome-phase entry, and the `layer_savings` dict from that run's LAST `budget-usage`-kind entry whose payload actually carries a `layer_savings` dict (last-*non-empty*-write-wins — deliberately NOT identical to `cli/status.py::_gather_run_journal_facts`'s literal `usage_entries[-1]`, which reports `{}` with no fallback when the chronologically-last entry omits the key; the rollup instead falls back to the closest earlier entry that has data, so a terminal budget-usage flush that omits `layer_savings` doesn't blank out real savings a station actually earned earlier in the same run); skip runs missing either signal entirely. Read the payload's own `layer_savings` keys when bucketing (not a hardcoded field-name tuple) so an unrecognized key actually reaches `classify_layer_kind` and can raise, per Design Notes. Bucket each `layer_savings` key's value into `silent`/`configured` (via `classify_layer_kind`) under a per-harness entry carrying that harness's own `currency` (via `currency_for_harness`) and a `runs` count. Wrap each run's `journal_path.read_text(...)` in `try/except OSError: continue` (skip that run) -- a filesystem race (file removed/permission-changed between glob and read) must not crash the whole rollup, matching this module's existing `json.JSONDecodeError` per-line tolerance. Return `{"status": "ok"|"no-dispatch-journals"|"no-savings-samples", "harnesses": {<profile_name>: {"currency": ..., "silent": {...}, "configured": {...}, "runs": N}}}` -- never a cross-harness summed total.
- `core/layer_savings_sources.py` -- add `classify_layer_kind`, `currency_for_harness`, `HARNESS_CURRENCY`, `UNKNOWN_HARNESS_CURRENCY`, `read_rollup_by_harness` to `__all__`.
- `cli/status.py` -- import `from ..core import layer_savings_sources`. In `run_status`, immediately after `data["homes"] = rows` (L1937), when `args.project is not None`: `data["savings_rollup_by_harness"] = layer_savings_sources.read_rollup_by_harness(git_repo_root, project_slug=args.project)`. Whole-fleet status (`args.project is None`) does not compute a cross-project rollup -- each project's dispatch-runs are scoped to that project only.
- `cli/status.py` -- add `_format_rollup_by_harness(rollup: Mapping[str, object]) -> str`, sibling of `_format_savings_summary` (L198): one line per harness, in `_format_savings_summary`'s own human-readable style (no raw Python `repr()` of dicts/lists -- render each layer key as `key=value` joined by `, `, matching the sibling formatter's convention rather than dumping `{'output_compression_saved': [500]}`-shaped literals); empty/`"no-dispatch-journals"`/`"no-savings-samples"` status returns `""`. Call it from `_render_text_status` (~L2285, alongside the existing `_format_savings_summary` call) when `data.get("savings_rollup_by_harness")` is present, appended as its own line(s) -- never summed into `savings_text`.
- `tests/unit/test_layer_savings_sources.py` -- unit-test `classify_layer_kind` (each silent key, the configured key, an unknown key raises), `currency_for_harness` (each of the 5 known names, `None`, and an unrecognized name), and `read_rollup_by_harness` against a synthetic two-harness `dispatch-runs/<run>/journal.jsonl` fixture (one run's `dispatch-launch` outcome payload naming `"claude"`, another naming `"cursor"`, each with a distinct `budget-usage` `layer_savings` payload) -- the I/O Matrix scenario. Also cover: a single run with TWO `budget-usage` entries where only the earlier one carries `layer_savings` (proves last-*non-empty*-wins, not literal-last-entry) -- this is the scenario the last review pass found unexercised; a second run under an already-seen harness (proves per-harness accumulation across runs, `runs == 2`, per-field lists of length 2); a malformed line (non-JSON) and a non-dict `layer_savings` payload (both tolerated, not counted); the helper that builds a run missing its `dispatch-launch` entry must not also pass an unused `harness_profile` for that case.
- `tests/unit/test_status.py` -- unit-test `_format_rollup_by_harness` renders both harnesses' currencies with no blended total, and that `run_status`'s envelope carries `savings_rollup_by_harness` only when `--project` is given.

**Acceptance Criteria:**
- Given a project's `dispatch-runs/` journals span at least two distinct `harness_profile` values (e.g. `claude` and `cursor`), when `marshal status --project <slug>` renders, then the envelope's `savings_rollup_by_harness` and its text rendering show each harness's savings under its own `currency` string, with no single summed-across-harnesses total field or line anywhere in the output.
- Given a single run's `layer_savings` payload, when `read_rollup_by_harness` classifies its keys, then every one of the 5 `LayerSavings` field names resolves to exactly one of `"silent"` or `"configured"` per `classify_layer_kind`, matching Story 46.4's harness-agnostic-repo-default (output/structure-graph/derived-context/planning-graph) vs. capability-resolved (wire) split.
- Given a run whose journal has a `budget-usage` entry but no `dispatch-launch` outcome entry (or vice versa), when `read_rollup_by_harness` scans it, then that run is skipped (not counted under an `"unknown"` bucket) -- an incomplete run contributes no partial data.

## Spec Change Log

### 2026-09-18 -- review_loop_iteration 0 -> 1 (bad_spec)

**Triggering finding:** grouped finding #1 in the Review Triage Log below (Blind Hunter #1/#8, Edge Case Hunter #2, Verification Gap layer) -- the `read_rollup_by_harness` Tasks & Acceptance bullet claimed its per-run savings selection was "last-write-wins... matching `cli/status.py::_gather_run_journal_facts`'s own convention." Verified directly against `_gather_run_journal_facts` (`cli/status.py`, `usage_entries[-1]` with no fallback when that entry lacks `layer_savings`): the implemented code actually does last-*non-empty*-wins (falls back to an earlier entry when the latest lacks `layer_savings`), which does NOT match the cited convention. The false parity claim originated in my own step-02 planning text and was copied faithfully into the implementation's docstring/comments by step-03.

**What was amended:** Tasks & Acceptance (the `read_rollup_by_harness` bullet and the test-coverage bullet) and Design Notes, outside `<intent-contract>`. Replaced the false "matches `_gather_run_journal_facts`" claim with an explicit statement that last-non-empty-wins is an intentional, named divergence (and why: a terminal cost-only flush shouldn't blank out real earlier savings). Also folded in, as explicit spec guidance rather than leaving them for a second review round-trip: (a) bucket off the payload's own `layer_savings` keys, not a hardcoded field-name tuple, so `classify_layer_kind`'s "raises on unrecognized key" guarantee is actually reachable; (b) wrap `journal_path.read_text(...)` in `try/except OSError: continue`, matching the module's existing per-line `JSONDecodeError` tolerance; (c) `_format_rollup_by_harness` must use `_format_savings_summary`'s human-readable style, not raw dict `repr()`; (d) new test coverage for multi-`budget-usage`-entry-per-run (proves the non-empty-wins fallback), cross-run accumulation, malformed lines, and removal of an unused parameter in one existing test's fixture call.

**Known-bad state avoided:** a shipped docstring/spec claim that is factually false against the codebase; an unreachable "fail loud" promise that would let a future 6th `LayerSavings` field silently vanish from the rollup with no signal; an operator-facing CLI line rendering raw Python `repr()` instead of readable text; an unguarded filesystem read diverging from this module's own established tolerance pattern.

**KEEP -- verified sound, must survive re-derivation unchanged:** the overall taxonomy design (`SILENT_LAYER_KEYS` / `CONFIGURED_LAYER_KEYS` / `classify_layer_kind` split); the `HARNESS_CURRENCY` table and `currency_for_harness`'s never-raises degrade-to-`"unknown"` behavior; the read-only, single-file, `run_id`-keyed join (no journal schema change); the CLI wiring shape (`data["savings_rollup_by_harness"]`, gated on `args.project is not None`, `_format_rollup_by_harness` as a sibling of `_format_savings_summary` called from `_render_text_status`); the `_write_run_journal` test-fixture helper pattern and the two-harness fixture shape in `test_layer_savings_sources.py` / `test_status.py`.

## Review Triage Log

### 2026-09-18 -- review pass 1 (verdicts: 0 high / 5 medium / 6 low / 0 false / 0 maybe-false -- 11 findings total, 8 entries after grouping by shared root cause)

| # | Layer(s) | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|---|
| 1 | Blind Hunter (#1, #8), Edge Case Hunter (#2), Verification Gap | `read_rollup_by_harness` docstring/Tasks claimed "last-write-wins... matching `_gather_run_journal_facts`'s own convention"; actual code is last-*non-empty*-wins (falls back past an entry lacking `layer_savings`), which `_gather_run_journal_facts` (`usage_entries[-1]`, no fallback) does not do. Root cause traced to my own step-02 spec text, outside `<intent-contract>`. | medium | bad_spec | Verified by reading `cli/status.py` L610-627 (`_gather_run_journal_facts`) directly against `read_rollup_by_harness`'s `elif kind == _BUDGET_USAGE_KIND: ... if isinstance(layer_savings, dict): last_layer_savings = layer_savings` branch -- confirmed real divergence. Spec amended above (2026-09-18 entry); code reverted to baseline and re-derived via step-03. |
| 2 | Blind Hunter (#2) | `classify_layer_kind`'s "raises on unrecognized key" promise is unreachable in the real read path -- `_bucket_layer_savings` only ever calls it with the 5 hardcoded field names, never the payload's actual keys, so a future 6th `LayerSavings` field would be silently dropped, not raised. | low | reject | Verified real by inspection, but currently correct for all 5 known fields; catching future schema drift needs a design decision (raise vs. warn-and-skip) not specified anywhere -- fails the reject-low "fix is a direct correction" test on its own, so instead folded into the amended Tasks bullet above (bucket off payload keys) rather than tracked as a standalone patch. |
| 3 | Blind Hunter (#3) | No test exercises multi-run-same-harness accumulation (`runs == 2`, per-field lists of length 2). | low | reject | Verified the accumulation logic (`setdefault(...).append(...)`, `runs += 1`) is correct by direct inspection; no bug found, pure coverage gap. Folded into the amended test-coverage bullet above rather than tracked separately. |
| 4 | Blind Hunter (#4) | `_format_rollup_by_harness` renders raw Python `dict`/`list` `repr()` instead of `_format_savings_summary`'s human-readable convention -- a real operator-facing readability regression, not a style nit. | low | patch | Verified: `_format_savings_summary` humanizes bytes/percentages; the new formatter did `f"silent={silent!r}"`-shaped output. Fix is a direct, bounded reformat -- folded into the amended Tasks bullet above; re-derivation will produce the corrected formatter directly rather than a follow-up patch pass. |
| 5 | Blind Hunter (#5) | No test for malformed/corrupt journal lines or non-dict `layer_savings`/payload values. | low | reject | Verified existing guards (`try/except json.JSONDecodeError: continue`, `isinstance(..., dict)` checks) are correct by inspection; pure coverage gap, no bug. Folded into the amended test-coverage bullet above. |
| 6 | Blind Hunter (#6) | No test for `harness_profile` present-but-empty-string or non-string type. | low | reject | Verified the existing `isinstance(profile, str) and profile` guard handles both cases correctly by inspection; pure coverage gap, no bug. |
| 7 | Blind Hunter (#7) | `test_read_rollup_by_harness_skips_run_missing_launch_or_usage`'s `run-no-launch` case passes a dead `harness_profile=None` parameter that `include_launch=False` already makes unused -- misleading test intent. | low | patch | Verified: the parameter is genuinely unused on that code path. Folded into the amended test-coverage bullet above ("removal of an unused parameter"). |
| 8 | Edge Case Hunter (#1) | `read_rollup_by_harness` has no `try/except OSError` around `journal_path.read_text(...)`, unlike its own per-line `JSONDecodeError` guard -- an unguarded filesystem race would propagate uncaught. | medium | patch | Verified: no guard present in the reverted-to-baseline diff; `read_dispatch_idle_timing` (the sibling this function mirrors) has the same pre-existing gap, out of this story's scope to fix there, but this story's new code should not repeat it. Folded into the amended Tasks bullet above. |

Cascading order: finding #1 is `bad_spec`, so per protocol all lower entries are moot for this pass (code will be fully re-derived from the amended spec); findings #2/3/4/5/6/7/8's real substance was folded directly into the spec amendment above so the re-derivation addresses them without a separate follow-up patch round.

Intent Alignment Auditor: reported no discrete findings (descriptive-only per its charter) -- confirmed the diff's "read-time rollup only, no journal schema field" reading is a coherent, spec-endorsed interpretation of the Approach line's "journal schema" wording; its note that "distinguishable per journal row" was only tested at the aggregated-rollup level, not literally per persisted row, is the same underlying gap as finding #1's missing multi-entry-per-run test coverage -- no separate row.

## Design Notes

The join is READ-ONLY and single-pass per file: nothing in `cli/dispatch.py`, `supervisor/__main__.py`, or `core/policy.py` (the write paths) changes. `harness_profile` is already durably written into the SAME `journal.jsonl` a run's `budget-usage` entries live in (`cli/dispatch.py`'s `dispatch-launch` outcome payload), so the per-harness split is purely a read-time correlation keyed by `run_id` (the journal filename's parent directory) -- no new journal schema field, no sidecar, no second file.

`currency_for_harness` never raises, mirroring this epic's "a repo default can never claim a wrap a harness can't perform" ethos (epic-46-context.md): an unrecognized or absent harness name degrades to the honest `"unknown"` currency label rather than a crash or a silent USD default that would misrepresent a non-Claude station's savings.

`classify_layer_kind` DOES raise on an unrecognized key -- unlike the currency lookup, an unknown `LayerSavings` field name is a programmer error (a new layer added to `ports/harness.py` without updating this taxonomy), not user-facing data absence, and should fail loud in tests rather than silently mis-bucket. This guarantee only holds if the bucketing loop drives `classify_layer_kind` off the payload's own keys -- driving it off a fixed known-good tuple instead (as the prior pass did) makes the "raises on unrecognized" promise unreachable dead code, since the caller would never pass it anything but a name it already knows.

`read_rollup_by_harness`'s per-run savings selection is last-*non-empty*-wins, not literal-last-entry-wins: a terminal `budget-usage` flush in `supervisor/__main__.py` can legitimately omit `layer_savings` (e.g. a final cost-only snapshot), and falling back to `{}` in that case would silently blank out real savings a station earned earlier in the same run. This is an intentional, named divergence from `cli/status.py::_gather_run_journal_facts`'s literal `usage_entries[-1]` convention (that function accepts `{}` because its subject is a single run's point-in-time cost readout, not a savings rollup) -- do not "fix" this to match `_gather_run_journal_facts` exactly; the prior pass's docstring claim of exact parity was the actual defect (spec-authoring error, corrected here 2026-09-18).

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pyforge-marshal-test` -- expected: full station suite green, including the new `test_layer_savings_sources.py` and `test_status.py` cases.
- `pixi run -e pyforge-marshal marshal status --project pyforge-marshal --format json` -- expected: valid envelope; `savings_rollup_by_harness` key present (possibly `{"status": "no-dispatch-journals", "harnesses": {}}` if this worktree's own `dispatch-runs/` is sparse -- not a failure, a real "no data yet" state).

## Source

Contract recovered from `epics.md` Story 46.5 (Intent + ACs) so `marshal factory dispatch` can resolve `spec-<ledger-key>.md` (MRS-DISP-005). No new story minted.
