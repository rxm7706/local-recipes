---
title: 'Adoption-tracking watch axis -- `--watch adoption` (FR-12, AD-9)'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: [
  '{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md',
  '{project-root}/_bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md',
  '{project-root}/src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/atlas.py',
  '{project-root}/.claude/tools/conda_forge_server.py',
  '{project-root}/.claude/skills/conda-forge-expert/scripts/adoption_stage.py',
  '{project-root}/.claude/skills/conda-forge-expert/scripts/version_downloads.py',
]
warnings: [
  'version_downloads has NO fleet-wide/maintainer mode (its CLI/MCP signature takes a single required package `name`, unlike every other Watch-axis tool) -- the sub-call is only attempted when `target` is given; without a target, the adoption axis gathers adoption_stage data only. See Design Notes.',
]
baseline_revision: 'HEAD at Story 4.3 start (after Stories 4.1/4.2 landed in the same pass)'
---

<intent-contract>

## Intent

**Problem:** `monitor --fleet --watch staleness,cve` misses genuine abandonment signals a package can exhibit despite looking fine on commit history alone -- cf_atlas's own `adoption-stage`/`version-downloads` classifiers were named as candidate sources in Doctor's original Dream but never wired into `sources.atlas`.

**Approach:** Extend `sources/atlas.py`'s existing MCP-first/CLI-fallback machinery (Story 2.1's exact pattern) with a fourth axis, `"adoption"` -- a COMPOSITE of `adoption_stage` (fleet/maintainer-scoped, always attempted) and `version_downloads` (per-package only, attempted when `target` is given), both normalized under a single new `Source.ADOPTION` enum member. Opt-in only via `--watch adoption`; `monitor --fleet`'s default axis set (`staleness`,`cve`) is unchanged.

## Boundaries & Constraints

**Always:**
- MCP-first, CLI-fallback for BOTH sub-calls -- reuses the SAME `_fetch_rows`/`_call_mcp`/`_call_cli` shared transport `_gather_staleness`/`_gather_cve`/`_gather_abandonment` already use; no new subprocess/MCP call-site machinery added (AD-5/AD-9's own "no fifth ad hoc query path" rule).
- `Source.ADOPTION` is a deliberate, reviewed closed-taxonomy extension (AD-3 "extended, never opened") -- both sub-instruments tag under this ONE Source (unlike `abandonment`'s per-sub-instrument tagging), matching Story 4.3 AC1's literal `Finding(source=Source.ADOPTION, ...)` wording.
- `adoption` is opt-in only -- `monitor --fleet`'s default `--watch` set stays `staleness,cve` (Story 2.3's existing default), proven by a dedicated regression test.
- Each sub-call degrades independently to its own FAIL Finding on total failure -- one sub-instrument failing never hides the other's real data (mirrors `_gather_abandonment`'s own partial-degrade discipline).

**Never:**
- Never call `version_downloads` when `target is None` -- the tool has no fleet-wide mode; there is nothing meaningful to call it with.
- Never widen `monitor --fleet`'s default axis set by this addition.
- Never open a second `mcp` import site, or a subprocess call outside `cli_bridge.py`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `--watch adoption`, no `--target` | MCP available | `adoption_stage` rows only, tagged `Source.ADOPTION` | No error |
| `--watch adoption --target pkg` | MCP available | BOTH `adoption_stage` (maintainer-scoped) AND `version_downloads` (per-package `pkg`) rows, both `Source.ADOPTION` | No error |
| `adoption_stage` stage=`silent` | Real row | `FAIL` | -- |
| `adoption_stage` stage=`declining` | Real row | `WARN` | -- |
| `adoption_stage` other stages | Real row | `OK` | -- |
| No MCP client | -- | Falls back to `adoption_stage.py`/`version_downloads.py --json` via `cli_bridge` | Same sole-subprocess-site guard |
| One sub-call fails, the other succeeds | e.g. `version_downloads` unreachable | The OTHER sub-call's real Findings still returned, plus one FAIL sentinel for the failed one | No error (partial degrade) |
| `monitor --fleet` (no `--watch`) | Default run | `adoption` never gathered -- default stays `staleness,cve` | No error |
| `Source` enum count | -- | 8 members (7 + `ADOPTION`) -- still closed, still enumerable | -- |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py` -- EDIT. `Source` gains `ADOPTION = "adoption"`.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/atlas.py` -- EDIT. `_VALID_AXES` gains `"adoption"`; `_normalize_adoption_stage_rows`/`_normalize_version_downloads_rows`; `_gather_adoption`; `gather()`'s dispatch extended.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/data/report-schema.json` -- EDIT. `finding.source` enum gains `"adoption"`.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py` -- EDIT. `--watch` help text mentions the new axis (dispatch itself needed no change -- `_validate_monitor_args` already validates against `atlas.VALID_WATCH_AXES` generically).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_atlas_watch_axes.py` -- EDIT. Full adoption-axis coverage appended.
- `src/shared/packages/pyforge-doctor/tests/unit/test_cli_monitor.py` -- EDIT. `--watch adoption` opt-in + default-unchanged regression tests.
- `src/shared/packages/pyforge-doctor/tests/unit/test_models.py` -- EDIT. `Source` member-count test extended to 8.

## Design Notes

**Why `version_downloads` only runs when `target` is given (the flagged warning above):** confirmed live against `.claude/skills/conda-forge-expert/scripts/version_downloads.py`'s own argparse signature (`name` is a REQUIRED positional; no `--maintainer` flag exists at all, unlike `adoption_stage`/`staleness_report`/`cve_watcher`/`feedstock_health`/`release_cadence`, which all accept `--maintainer`). There is no fleet-wide "per-version downloads for every package" query to make. Modeled as a conditional third sub-call (present only with `target`) rather than skipped silently -- `_gather_adoption`'s own docstring states this explicitly, and a dedicated test (`test_adoption_stage_only_when_no_target_given`) proves the axis still degrades gracefully to adoption_stage-only data without `target`, never an error.

**Why both sub-instruments share ONE `Source.ADOPTION` tag, unlike `abandonment`'s two-Source split:** Story 4.3 AC1's literal text says `Finding(source=Source.ADOPTION, ...)` (singular), not two Sources -- read as a deliberate, narrower design than `abandonment`'s own (which predates this story and was never asked to be uniform). `version_downloads`' rows are also explicitly framed in this spec as SUPPLEMENTARY evidence for `adoption_stage`'s own verdict (a single version's download count implies no independent health signal), reinforcing that they belong under the same tag rather than being presented as if they were a second instrument's own opinion.

**Why `version_downloads` rows always grade `OK`:** a raw per-version download count carries no pass/fail semantic by itself -- unlike `adoption_stage`'s own `stage` classification (which IS a real verdict), a version's download total is context, not a signal. Grading it WARN/FAIL would be inventing a threshold with no basis in the underlying data (mirrors `_classify_blast_radius`'s own documented "resolves to unknown... expected, not a bug" precedent for inventing signals the data doesn't support).

## Verification

- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`

**Actual results (2026-08-07):** full suite green (403 total after all four Epic 4 stories). 12 new adoption-axis unit tests + 2 new monitor CLI tests all pass; `test_score_pure_function.py`/`test_prescribe_pure_function.py`/`test_atlas_sole_mcp_import.py` all still pass unchanged (no new mcp-import site, no new subprocess site).

## Review Triage Log

### 2026-08-07 -- Self-review pass (adversarial re-read of the diff)

- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0

Checked specifically for: exception handling (`_gather_adoption` follows `_gather_abandonment`'s IDENTICAL try/`_FetchFailed`/degrade pattern verbatim -- no new exception class, no new swallow site); silent drops (a non-dict row from either sub-instrument degrades to its own FAIL Finding, never dropped -- `test_adoption_non_dict_row_degrades_to_a_fail_finding_not_a_crash`); docstring-vs-behavior drift (re-read `_gather_adoption`'s docstring against its own code -- the "no `cli_script_path` override" claim matches, since it calls `_default_cli_script` inline exactly like `_gather_abandonment` does); the opt-in-only guarantee (double-checked `_DEFAULT_MONITOR_AXES` was NOT touched by this diff -- `git diff` confirms only `_VALID_AXES` changed, never the default tuple); the sole-mcp-import-site guard (still passes -- `_gather_adoption` reuses `_fetch_rows`, adding no new `mcp` import anywhere).

**Follow-up review recommendation: false** -- this story is a mechanical, well-precedented extension of Story 2.1/2.2's already-reviewed machinery; the one real design decision (the `version_downloads` target-gating) is explicitly flagged and tested.

</intent-contract>
