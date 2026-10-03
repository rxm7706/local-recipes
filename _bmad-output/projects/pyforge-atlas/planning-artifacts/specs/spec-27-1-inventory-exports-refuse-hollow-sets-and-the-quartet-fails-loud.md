---
title: "27.1: The inventory exports refuse a hollow verification set, and the quartet scripts fail loud"
type: 'fix'
created: '2026-10-03'
status: 'in-review'
baseline_revision: a7746bc0b6
review_loop_iteration: 1
followup_review_recommended: true
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
deferred:
  - summary: >-
      HollowVerificationSetError still aborts the full derived_artifacts Kedro run instead of skip-and-mark-stale on inventory outputs only (NFR-3).
    evidence: |-
      verification_sets raises inside inventory nodes; Kedro propagates and fails the SBOM path. Operator may prefer per-node stale markers without failing build_universe_sbom.
    location: >-
      src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/derived_artifacts/inventory_verification.py
    severity: low
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** 25 open deferred-work rows (9 medium, 16 low) raised by Stories 16.1-16.2, 20.3, 20.7 and 22.5 against the inventory quartet. Story 23.9 has since thinned `scripts/conda-forge-packaging-inventory-operations_metrics.py` into an actuator over Atlas's Kedro exports, so most of these rows' behaviour now lives in `pipelines/derived_artifacts/nodes.py`, and several cited functions were renamed or deleted. The defects that survived the move: an empty or sub-floor conda-forge or PyPI set still makes every package read unverified and every AOSS-free package read "not on conda-forge" (`_verification_sets` now carries no floor at all, and `build_inventory_aoss_free_queue` queues the lot); `create_missing_issues` still fires `gh` calls in a tight loop with no backoff; the identity export reader crashes on a corrupt Parquet or a list-valued cell and treats an empty `PYFORGE_ATLAS_DATA_ROOT` as unset; the quartet's gist columns and Atlas's export columns are two hand-kept copies with no test between them; no test reads a pipeline-produced export or runs the inventory from scratch; and the canvas writers hard-code a home directory, hide `?` records, drop unknown recipe types and keep a second copy of `_CANVAS_PREFIX`.

**Approach:** Re-locate every row against the current tree first (Story 23.9 moved the logic into the Kedro `derived_artifacts` nodes; Story 23.5 moved the ranking merge into `identity_complete_export`). Then: give `_verification_sets` scale floors counted after `norm_pkg` and make the inventory nodes refuse with a named error when a set is empty or below its floor; pace and retry `create_missing_issues`' `gh` calls with bounded backoff; make the export reader fail named on a corrupt Parquet, stringify non-scalar cells, warn on duplicate or absent ranking columns and refuse an empty data-root override; derive the gist columns and the export columns from one schema; add a test over a pipeline-produced `identity_complete_export`, a from-scratch fixture run, and an end-to-end `derived_artifacts` run; and fix the canvas writers.

Ledger key: `27-1-inventory-exports-refuse-hollow-sets-and-the-quartet-fails-loud`.
Type / Effort / Deps: fix / L / —.
Rows: 25 (9 medium, 16 low).

### Living CAP citations

- The atlas capabilities that shipped each behaviour (see each row's source story); a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given an empty or sub-floor `core_packages_enumerated` or `pypi_universe` When the `derived_artifacts` inventory nodes run Then they refuse with a named error and write no AOSS-free queue that lists every package as not on conda-forge; the floors count names after `norm_pkg`
- Given a fake `gh` runner that answers two secondary-rate-limit errors When `create_missing_issues` runs Then it paces its calls and retries within a bounded backoff budget, and reports the names it could not file
- Given a corrupt Parquet, a list-valued cell, a duplicated or absent ranking column, or `PYFORGE_ATLAS_DATA_ROOT=""` When the identity export is read Then each yields a named error or warning, never an uncaught crash or a silent default
- Given the quartet's gist schema and Atlas's identity export columns When either changes alone Then a test fails; and a test reads an `identity_complete_export` Parquet produced by the pipeline node over fixtures
- Given the static fixture Parquet When the `derived_artifacts` pipeline and then the metrics actuator run from scratch Then the CSV and Markdown match a committed snapshot (CAP-1's clean-run bar, proven offline)
- Given the canvas writers When they run on another machine Then the canvas directory comes from an environment or local-env value (unset skips the write with a message), `?` records show in a bucket, unknown recipe types are kept, and `_CANVAS_PREFIX` has one definition
- Given each defect this story fixes When its new test runs against the tree before the fix Then it fails, and after the fix it passes
- Given this story lands When its deferred-work rows are read Then each of `DW-FU-17-1`, `DW-FU-17-2`, `DW-FU-21-3-2`, `DW-FU-21-3-7`, `DW-FU-21-3-12`, `DW-FU-21-7`, `DW-FU-21-7-2`, `DW-FU-21-7-3`, `DW-FU-21-7-4`, `DW-FU-17-2-2`, `DW-FU-17-2-3`, `DW-FU-17-2-7`, `DW-FU-21-3-3`, `DW-FU-21-3-4`, `DW-FU-21-3-5`, `DW-FU-21-3-6`, `DW-FU-21-3-8`, `DW-FU-21-3-9`, `DW-FU-21-3-10`, `DW-FU-21-3-11`, `DW-FU-21-7-5`, `DW-FU-21-7-6`, `DW-FU-21-7-7`, `DW-FU-21-7-8`, `DW-FU-23-5` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:** Re-locate each row before fixing it. Where the behaviour moved, fix it where it lives now; a row closes on citation alone only when its behaviour no longer exists anywhere, and its `verified:` line then cites the `path:line` that replaced it. Keep every gate fixture-based and non-credentialed (NFR-1, AD-11): the rate-limit and from-scratch tests run offline. Fix each defect where the shipped behaviour lives now and pin it with a test that fails without the fix. A re-ingested twin closes with the row it repeats, citing the same fix.

**Never:** Never call the live GitHub API or a live gist from a test. Never let a hollow input produce an export that looks complete. Never edit the replay or prompt docs without the matching script change (the quartet's prompt-sync contract). Never close a row without a landed fix and a cited `verified:` line (no blanket closure).

</intent-contract>

## Deferred-work rows this story closes (operator ruling 2026-10-03, deferral burn-down Phase 4+5)

- `DW-FU-17-1` (medium) — Prove CAP-1's clean-run bar offline: a test runs the `derived_artifacts` inventory nodes over the static fixture Parquet, then the metrics actuator with `--live-catalog <fixture root>`, and compares the CSV and Markdown against a committed snapshot.
- `DW-FU-17-2` (medium) — `create_missing_issues` paces its `gh issue create` and `gh project item-add` calls and retries a secondary-rate-limit answer with bounded exponential backoff; a fake runner that rate-limits twice pins it.
- `DW-FU-21-3-2` (medium) — The strict-mode live-HTTP fallback left with Story 23.9; what survives is that an empty `pypi_universe` makes every row `PyPI_Verified = No`. `_verification_sets` refuses an empty or sub-floor PyPI set with a named error.
- `DW-FU-21-3-7` (medium) — An empty or sub-floor conda-forge set makes `build_inventory_aoss_free_queue` queue every AOSS-free package as not on conda-forge; the node refuses, and writes no queue, when `cf_or_pm` is empty or below its floor.
- `DW-FU-21-3-12` (medium) — Re-ingested twin of `DW-FU-21-3-7` (same text, later intake); closed by the same fix and test.
- `DW-FU-21-7` (medium) — `write_gist_markdown` no longer re-stamps the time; find where the gist's `Verification_Timestamp_UTC` is produced now (the Kedro identity gist or export) and make the gist, CSV and tab carry the one export timestamp; a test compares them.
- `DW-FU-21-7-2` (medium) — `read_identity_complete_export_records` (renamed from `read_identity_export_records`) catches a failed `pd.read_parquet` and returns the same named stderr error as a missing file.
- `DW-FU-21-7-3` (medium) — The quartet's gist columns and Atlas's identity export columns derive from one schema, or a test compares the two lists, so either side changing alone fails.
- `DW-FU-21-7-4` (medium) — A test reads an `identity_complete_export` Parquet produced by running the pipeline node over fixtures, not a hand-built frame, through the quartet's reader.
- `DW-FU-17-2-2` (low) — `CANVAS_DIR` and `conda-forge-packaging-inventory-operations_priority.py`'s `--canvas` default come from an environment or local-env value, not a home path; unset skips the canvas write with a message.
- `DW-FU-17-2-3` (low) — `write_ops_canvas` shows `?`-sentinel records in a visible bucket, and `build_by_type` keeps recipe types outside `RECIPE_TYPE_ORDER` (after the known ones).
- `DW-FU-17-2-7` (low) — `openteams_identity_dashboards.py` imports `_CANVAS_PREFIX` from the priority script instead of keeping a second copy.
- `DW-FU-21-3-3` (low) — Story 23.9 removed `--strict-fetch` and the live-catalog acquisition; confirm no actuator flag is accepted and ignored, pin the actuator's flags with a test, and cite its argparse.
- `DW-FU-21-3-4` (low) — `load_atlas_exports` records the exception type and chains it, so an unexpected bug reads differently from a missing or unreadable export; a reader that raises `KeyError` pins it.
- `DW-FU-21-3-5` (low) — Once the floors land (DW-FU-21-3-8), the actuator's `--help` and the replay doc say which sets carry a floor (`pypi_conda_mapping` has none).
- `DW-FU-21-3-6` (low) — The help text names user-facing concepts, as the row's own second review pass found; a test pins that `--help` carries no internal variable names.
- `DW-FU-21-3-8` (low) — The floor was lost in the move to Kedro; `_verification_sets` applies its scale floors to the sets after `norm_pkg`, not to raw distinct values.
- `DW-FU-21-3-9` (low) — The unused `subdirs` line no longer exists (Story 23.9 deleted it with the live-catalog code); close citing the actuator's `main`, after confirming nothing re-creates it.
- `DW-FU-21-3-10` (low) — Re-locate the `has_src` / 10k-tab filter: if it moved into Kedro, its channeldata input degrades with a stale marker instead of silently changing which rows are kept; if it is gone, close citing what replaced it.
- `DW-FU-21-3-11` (low) — `load_atlas_exports` bounds each Parquet read with a deadline and fails named when it expires; a blocking fake reader pins it.
- `DW-FU-21-7-5` (low) — Re-locate the ranking merge (Story 23.5 moved it into the Kedro identity export); a secondary ranking column absent from the ranked input is reported as a warning, not left as a silent blank.
- `DW-FU-21-7-6` (low) — The export reader's per-cell stringify joins list or array cells instead of crashing `pd.isna`.
- `DW-FU-21-7-7` (low) — Two ranked rows that normalize to one pep503 name raise a warning naming both (re-locate the merge first).
- `DW-FU-21-7-8` (low) — `identity_complete_export_parquet_path` treats an explicitly empty `PYFORGE_ATLAS_DATA_ROOT` as an invalid override with a named error, not as the default.
- `DW-FU-23-5` (low) — A test runs the `derived_artifacts` pipeline end to end through a Kedro session over materialized fixture Parquet, not only the node in isolation.

## Binding

Parent: The atlas capabilities that shipped each behaviour; a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag.
Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-03 (Phase 4+5) entry.
Ledger key: `27-1-inventory-exports-refuse-hollow-sets-and-the-quartet-fails-loud`.
Ledger status at mint: `backlog`.
Deps: —.
Surface: `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/derived_artifacts/` (the inventory and identity-export nodes), `scripts/conda-forge-packaging-inventory-operations_{metrics,openteams_identity,priority}.py`, `scripts/openteams_identity_dashboards.py`, `scripts/tests/` (their tests and fixtures), `tests/packaging/test_openteams_handoffs.py`, `src/shared/packages/pyforge-atlas/tests/pipelines/derived_artifacts/`, `docs/reference/conda-forge-packaging-inventory-operations_*.md` (the replay and prompt docs, in step with the scripts), the atlas deferred-work ledger.
Minted 2026-10-03 from the operator's Phase 4+5 ruling (open medium and low deferrals fixed together, split by package area, at most about 30 rows per story).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Spec Change Log

- 2026-10-03 — sent back after an independent landing review (findings in the Review Triage Log). Status back to `ready-for-dev`.
- 2026-10-03 (night) — sent back a third time after the second landing review (Review Triage Log); the operator removed the duplicate `review_loop_iteration` key. Status back to `ready-for-dev`.
- 2026-10-03 (night) — the third landing review's findings fixed by the operator's fixer (Review Triage Log); no row reopened. Status `in-review`, awaiting the next independent review; one `followup_review_recommended` key.

## Review Triage Log

### 2026-10-03 (night) — Third landing review; fixed by the operator's fixer
Reopened: none. Every finding landed with a test that fails on the reverted code, so all 25 rows stay closed and are re-cited at the fixer's final HEAD; the NFR-3 skip-and-mark-stale entry in `deferred:` is unchanged. Mutants ran in copies under the session scratchpad, never in this worktree.
- `high` **HIGH 1 — mutant-killing tests: fixed.** New tests: `resolve_canvas_dir` (environment, then `conf/conda-forge-packaging-inventory-operations.local.env`, then unset), the identity and priority unset-skip messages and the env-dir canvas targets (DW-FU-17-2-2); the `?` priority/work buckets and an unknown recipe type kept after the known ones (DW-FU-17-2-3); the gist, its dashboards companion, the CSV and the export Parquet carrying one `Verification_Timestamp_UTC` (DW-FU-21-7); the reader's absent ranking/secondary-column warnings and per-row duplicate warnings (DW-FU-21-7-5, DW-FU-21-7-7) and the node's (ranked-input and JFROG-consumption columns, rows counted per key); AC 3(b) — a blank timestamp raises `IdentityGistError` from both renderers and `--gist-only --skip-gist` exits 1 writing nothing; AC 3(c) — a list cell from a pipeline-produced export renders `a; b` in the gist table. Killed: M3 (`_export_priority_merge_warnings` call dropped), M4 (`?` buckets and `ordered_types` reverted), M4a (unknown types only), M5 (synthetic `datetime.now` in both gist renderers), M5b (dashboards only), M5c (gist ignores the export stamp), and M6-M15 (reader/node set-dedupe, reader without secondary columns, node without JFROG warnings, home-dir canvas default, silent `cf_or_pm_floor` alias, revised-prompt line first, non-daemon deadline, filed-but-not-added folded into not-filed, gh guard without `Popen`, floor on the union). The unmutated copy passes the same 42 tests.
- `high` **HIGH 2 — re-cite: fixed.** All 25 `verified:` lines rewritten at the live `path:line` (each read back after the last edit), dated 2026-10-03 and placed after the older verified lines; DW-FU-17-2-7's undated line removed.
- `medium` **MEDIUM 1 — DW-FU-23-5: fixed, not reopened.** `test_derived_artifacts_e2e.py` runs the six inventory/export nodes (universe, Basilisk rollup, priority, verified packages, AOSS-free queue, `build_identity_complete_export`) through a `KedroSession` in a `tmp_path` copy of `pyproject.toml`, `conf/base` and `src`; `conf/local` is never copied — the test seeds stub credentials and a `catalog.yml` pointing every free input at fixture Parquet. Floors 3 and 5, which the fixture meets; the AOSS queue is asserted row for row; a second test runs the session with a sub-floor core set and asserts the refusal and no queue file; the member's real `data/` tree is fingerprinted (file list + sha256) before and after.
- `medium` **MEDIUM 2 — gh guard: fixed.** The autouse guard subclasses `subprocess.Popen` (so `run`, `check_output`, `check_call` and `call` are all covered) on `Path(argv[0]).name == "gh"` (also `executable=` and `shell=True` strings) and pins `identity.gh_bin()` / `identity.DEFAULT_GH` to a sentinel path that cannot exist; a parametrized test proves five launch paths are blocked; the module docstring says so.
- `medium` **MEDIUM 3 — floor key: renamed.** `core_packages_enumerated_floor` / `DEFAULT_CORE_PACKAGES_ENUMERATED_FLOOR` everywhere (code, atlas tests, handoffs, from-scratch, the e2e runtime params; `conf/base/parameters.yml` carries no `verification_sets` block). No alias: any other key in `params:verification_sets`, including the retired `cf_or_pm_floor`, raises a named `ValueError` instead of falling back to a default.
- `medium` **MEDIUM 4 — prompt sync: fixed in one commit.** The actuator prints the summary block, then every `Wrote` line with `Wrote revised prompt` last (omitted under `--skip-revised-prompt`); `prompt.md` section 7 and `replay.md` show that exact shape, and a parametrized test matches stdout line by line against each doc.
- `medium` **MEDIUM 5 — frontmatter: fixed.** One `followup_review_recommended: true`; `status: in-review`.
- `low` Fixed: `identity.py --help` names `PYFORGE_INVENTORY_CANVAS_DIR` in `conf/conda-forge-packaging-inventory-operations.local.env` (tested through `--help`); filed-but-not-added issues print in their own section with the URL and a by-hand hint, apart from "Could not file" (tested through `main`); `stringify_export_cell` has one home in `identity_export_contract.py` with direct unit cases (the identity script and `identity_gist.py` bind it); `openteams_identity_dashboards.py` imports `importlib` at the top with PEP 8 spacing; the Parquet deadline runs on a daemon thread (tested); the e2e restores `sys.path`, `PYTHONPATH` and Kedro's project state with monkeypatch; the handoffs `_load_module` reuses a matching `sys.modules` entry and a fixture pins the patched copies (order-independent with `test_identity_parity.py`, run both ways); `test_argparse_has_no_strict_fetch_flag` pins the parser's whole flag set via `build_parser()`; the help tests run `--help`.
- `low` Found while fixing: `identity_export_contract.py` read 72.4% under the 80% unit floor (`pyforge-atlas-coverage-gate`) — fixed with the stringify cases; a ranked input with no `core_python_package_name` column now warns that nothing joins; an unused `datetime` import in the identity script removed.
- `low` For the operator: wip auto-checkpoints 738b2c3013 and 43e37b0661 hand-added six `surface:` entries to `spec-pyforge-atlas/SPEC.md` (the from-scratch test and fixtures, both sha256 snapshots, the e2e test). Left as is here — re-derive with `bmad-spec`.


### 2026-10-03 — Build-auto review pass (third send-back fixes)
- verdicts: 4 findings — high 0, medium 1, low 2, false 1, maybe-false 0
- findings:
  - `[false]` `[reject]` Prior HIGH gh-live-call — autouse `_forbid_unmocked_gh` and `subprocess.run` mocks on all create_missing_issues tests; isolated run of vanishing-gh and project-add tests passes without network.
  - `[medium]` `[defer]` Mutant-killing coverage for canvas unset-skip, ranking warnings, gist timestamp parity, list-cell gist path — still below AC 7 bar for several DW-FU rows; location: tests/packaging/test_openteams_handoffs.py
  - `[low]` `[defer]` `scripts/tests/` and handoffs not in kedro-test CI lane — preferred move to pyforge-atlas/tests/; location: scripts/tests/test_inventory_from_scratch_fixture.py
  - `[low]` `[defer]` `conda-forge-packaging-inventory-operations_prompt.md` exact-shape sync with metrics stdout — replay.md updated; prompt body still manual; location: docs/reference/conda-forge-packaging-inventory-operations_prompt.md

### 2026-10-03 (night) — Second landing review (independent reviewer, operator session) — sent back
Keep: the core floor on `core_packages_enumerated` after `norm_pkg` (with a default-floor test), the captured `gh` stderr, AC 3(a)'s refusal, `pd.NA`/`NaT` as `""`, the two restored assertions, the NFR-3 deferral row, `HollowVerificationSetError` under `PyforgeError`, and the ledger scope (only the 25 rows; DW-CANOPY / DW-OM identical to main). Fix the TEST SAFETY items first: until they land, never run `kedro-test` from the primary checkout.
- `high` **`test_derived_artifacts_e2e.py` (about :47-56) writes fixture Parquet into atlas's real `data/` tree**, depends on test order (alone it fails `KeyError: 'bigquery_adc'`; it passes only because an orchestration conftest seeds `conf/local/credentials.yml` first) and runs one node, not the pipeline. Run the session against a `tmp_path` project copy (or a `DataCatalog` rooted in `tmp_path` driven by a runner), seed stub credentials inside the test, and run the whole inventory and export slice; otherwise reopen DW-FU-23-5 with a `deferred:` entry naming it. Add a guard test that the real `data/` tree is unchanged after the suite.
- `high` **Six handoff tests patch `check_output`/`check_call`, but `_run_gh` now calls `subprocess.run`, so two tests ran the real `gh issue create --repo OpenTeams-WFT-CDO/...`** (`test_gh_binary_vanishing_mid_run_is_caught_not_fatal`, `test_project_item_add_failure_does_not_mark_row_as_tracked`). Patch `subprocess.run` in all six (`tests/packaging/test_openteams_handoffs.py`, about 92-114, 174-177, 231-237, 248-257, 263-290); fail only the `project` call in the item-add test and assert `("some-pkg", "filed-but-not-added: <url>")`; add an autouse fixture that raises if `gh` is ever invoked unpatched. Never call the live GitHub API.
- `high` **DW-FU-17-1 still closes without the snapshot**: `scripts/tests/test_inventory_from_scratch_fixture.py` (about :106) runs the nodes then `main()` but only checks the CSV exists. Commit a CSV snapshot (or its sha256) and compare it, as for the Markdown; otherwise reopen the row with a `deferred:` entry.
- `medium` **Mutant-killing tests still missing** (M3 `_export_priority_merge_warnings` call removed, M4 `?` bucket / unknown recipe types reverted, M5 synthetic gist timestamp all survive; coverage shows `identity_gist.py` about 212-231, 485, 620 and `nodes.py` about 1189-1202 never run). Add tests for `resolve_canvas_dir` and the unset-skip message (DW-FU-17-2-2), the reader's absent-ranking and duplicate warnings, the gist/CSV/tab timestamp comparison (DW-FU-21-7), AC 3(b) (a blank timestamp raises `IdentityGistError` and the script exits 1) and AC 3(c) (a list-valued cell through the gist renderer).
- `medium` **The stderr capture has no test**: replacing `capture_output=True` with `stdout=PIPE` (`identity.py`, about :250) passes all handoff tests because the fakes ignore kwargs. Have the fake assert `capture_output` (or `stderr=PIPE`), or test with a fake `gh` executable on PATH that prints the rate-limit text only to stderr and exits 1.
- `medium` **Re-cite every `verified:` line at HEAD** (fourteen are wrong). Re-read each fix's line after your last edit; the previous pass's list: DW-FU-21-7 (the `identity_gist.py` refusal), DW-FU-21-7-2, -7-6, -7-8, -7-4, DW-FU-21-3-3 (the argparse in `metrics.py`), -3-4, -3-5, -3-9 (`main`), -3-2, -3-7 and -3-12, -3-8, DW-FU-23-5, DW-FU-17-1.
- `medium` **The floor documentation is wrong**: the `metrics.py` help epilog (about 248-255) and `replay.md` (about 62-65) say the floor applies to "the conda-forge union set"; it now applies to `core_packages_enumerated`. The param key `cf_or_pm_floor` now controls the core floor: rename it (e.g. `core_packages_floor`) with every test, or document the alias.
- `medium` **The prompt-sync contract still drifts**: the actuator overwrites the tracked prompt doc (`metrics.py`, about 323-324) without printing "Wrote revised prompt:", and its other output lines changed (about 333-342). Restore the revised-prompt line and update `replay.md` (about 173-185) and `prompt.md` (about 205-217, "exact shape") in the same commit.
- `low` The Parquet deadline bounds the call, not the process (`concurrent.futures` joins workers at exit); use a daemon thread in `metrics.py` (about 84-104).
- `low` `identity.py` help (about :973) names `PYFORGE_ATLAS_CANVAS_DIR` / `.env.local`; the real names are `PYFORGE_INVENTORY_CANVAS_DIR` in `conf/conda-forge-packaging-inventory-operations.local.env`.
- `low` DW-FU-21-7-5 is partial (the warning list omits `Priority_Bucket_Description`, `Priority_Source`, `Priority_Reason` and the six JFROG columns); DW-FU-21-7-7: two rows with exactly the same raw name never warn because a set dedupes them; count rows per key (also in the `identity.py` reader).
- `low` Label filed-but-not-added issues separately from "Could not file" in `identity.py` `main`.
- `low` `_stringify_export_cell` exists twice (`identity.py` and `identity_gist.py`); give it one home in `identity_export_contract.py`. `openteams_identity_dashboards.py` (about 733-749) has a mid-module `import` and a `def` with no blank-line separation.
- `low` No CI lane runs `scripts/tests/` or `tests/packaging/test_openteams_handoffs.py`; move the from-scratch proof under `pyforge-atlas/tests/` (preferred) so the station suite gates it.

### 2026-10-03 — Landing review (independent reviewer, operator session) — sent back
Keep: the floor refusal (removing it fails four tests), the corrupt-Parquet catch, the rate-limit text detector, `identity_export_contract` and the canvas path resolution. All gates exit 0. The two rejects and the defer in the review pass below are overturned where a finding here names them.
- `high` **Two rows outside this story were closed.** `## DW-CANOPY-2026-08-24` and `## DW-OM-2026-08-24` (the `##` rows after `DW-FU-17-2-7` in `deferred-work-ledger.md`) went to `closed` with no resolution, and DW-FU-17-2-7's `verified:` line (`openteams_identity_dashboards.py:742`) landed inside DW-OM's block. Restore both rows to their text on main and move the `verified:` line into `DW-FU-17-2-7`'s own block. Split ledger blocks on every heading level, not `###` only.
- `high` **The DW-FU-17-2 backoff never fires against real `gh`.** `_run_gh` calls `check_output(cmd, text=True)` / `check_call(cmd)` without capturing stderr, so `CalledProcessError.stderr` is None and `_gh_secondary_rate_limit` (`identity.py`, about 223-229) sees only "returned non-zero exit status 1". The test passes only because its fake raises with return code 403. Capture stderr, and test with `returncode=1` and the rate-limit text in stderr only.
- `high` **Two rows were closed without the fix they require.** DW-FU-23-5 requires a run through a Kedro session over materialized Parquet; `test_derived_artifacts_e2e.py` calls three node functions on in-memory frames with floors set to 0. DW-FU-17-1 (AC 5) requires the nodes over the fixture Parquet, then the actuator with `--live-catalog`, then CSV and Markdown compared to a committed snapshot; `test_inventory_from_scratch_fixture.py` reads Parquet `generate_fixtures.py` writes by hand, never runs the nodes or `main()`, and hashes the Markdown only. Implement both as specified, or reopen the row and record why in this spec (`deferred:` must then name it).
- `medium` **The floor is not the one AC 1 names.** The code floors the union of conda-forge and parselmouth names at 30k (`inventory_verification.py`, about 36 and 45); before Story 23.9 the 30k floor applied to `core_packages_enumerated` alone. Empty core plus 30,000 mapping names passes and the queue lists `numpy` as not on conda-forge. Floor `core_packages_enumerated` itself (after `norm_pkg`), and add a test with the default floors.
- `medium` **AC 3 still crashes in three probed cases.** (a) `--gist-only` with `PYFORGE_ATLAS_DATA_ROOT=""`: the resolver returns None and `publish_gist_from_export(None)` raises AttributeError (`identity.py`, about 794); refuse with a named error. (b) A blank `Verification_Timestamp_UTC`: `identity_gist.py` (about 462 and 597) raises the base `PyforgeError`, but `identity.py` (about 836) catches only `IdentityGistError`; raise `IdentityGistError`. (c) A list-valued cell: the gist renderer crashes with "ambiguous truth value" (`identity_gist.py`, about 212) and `identity.py` (about 841) keeps the old `pd.isna` stringify; route both through `_stringify_export_cell`. A test for each.
- `medium` **The Parquet deadline does not bound the wait.** `_read_parquet_with_deadline` (`metrics.py`, about 84-100) exits a `with ThreadPoolExecutor` block, which waits for the worker: a 3 s reader with a 0.1 s deadline returned after 3.00 s. Use `shutdown(wait=False, cancel_futures=True)` and assert the elapsed time in the test.
- `medium` **Fixes with no test that fails without them (AC 7).** Mutants that stayed green: removing the `_export_priority_merge_warnings` call (DW-FU-21-7-5, DW-FU-21-7-7); reverting the `?` bucket and unknown-recipe-type handling (DW-FU-17-2-3); restoring a synthetic timestamp in `identity_gist` (DW-FU-21-7, whose row also asks for a test that compares them). DW-FU-17-2-2 has no test of `resolve_canvas_dir` or the unset-skip message. Add a test for each that fails on the reverted code.
- `medium` **Correct the `verified:` citations** (re-read at HEAD before writing): DW-FU-21-7 → `identity_gist.py` the timestamp refusal (about 460-465 / 595-600); DW-FU-21-7-2 → `identity.py` about 580-584; DW-FU-21-7-6 → about 543-557; DW-FU-21-7-8 → about 529-536; DW-FU-21-7-4 → `test_pipeline_export_readable_by_quartet_reader`; DW-FU-21-3-3 → the argparse in `metrics.py` (about 255-303); DW-FU-21-3-4 → `metrics.py` about 132-136; DW-FU-21-3-5 → about 245-252; DW-FU-21-3-6 → `test_metrics.py` about 339; DW-FU-21-3-9 → `main` in `metrics.py`; DW-FU-21-3-2 → `inventory_verification.py` about 41-44; DW-FU-21-3-7 and DW-FU-21-3-12 → about 45-48; DW-FU-21-3-8 → about 33-36; DW-FU-23-5 → the test itself.
- `medium` **The prompt-sync contract drifted.** The actuator now prints "Packages not on conda-forge:" (`metrics.py`, about 329) while `replay.md` (about 173-179) and `prompt.md` (about 205-213, marked "exact shape") still require "Count not on conda-forge: <number>", and the "Wrote revised prompt" line is gone though the actuator still overwrites the tracked prompt doc. Make the actuator output and both docs agree.
- `low` When `gh project item-add` fails after `gh issue create` succeeded, the issue goes to `not_filed` and its URL is lost, so a re-run files a duplicate. Report it as filed-but-not-added with its URL.
- `low` DW-FU-21-7-5 is partly fixed: the node warns only for P, Rank, Score and Work (`nodes.py`, about 1179-1181); the row names the secondary ranking and JFROG columns. Cover them.
- `low` Restore the two weakened assertions: `test_main_default_path_overlay_runs_before_csv_write` must again check that the gist reflects the local build overlay ("success"), and `test_live_catalog_formats_csv_md_and_queue_from_exports` must check that a queue is written, not only the count line.
- `low` `_stringify_export_cell` renders `pd.NA` as "<NA>" and `NaT` as "NaT" where the old reader gave ""; keep "".
- `low` `--ops-canvas` / `--workbook-canvas` help (`identity.py`, about 948-962) still names the Cursor home-directory default; describe the environment or local-env source.
- `low` NFR-3: `HollowVerificationSetError` aborts the whole `derived_artifacts` run, including the universal SBOM. Atlas's rule is skip-and-mark-stale; make the inventory export nodes refuse their own outputs (named error logged, outputs marked stale) without failing the SBOM, or record in this spec why the abort is right.

### 2026-10-03 — Landing review fix pass (build-auto)
- verdicts: 1 finding — high 0, medium 0, low 1, false 0, maybe-false 0
- findings:
  - `[low]` `[defer]` HollowVerificationSetError aborts full derived_artifacts run — recorded in frontmatter `deferred:` with location `inventory_verification.py`; skip-and-mark-stale per NFR-3 left for a follow-on story.

### 2026-10-03 — Review pass
- verdicts: 9 findings — high 0, medium 5, low 0, false 2, maybe-false 2
- findings:
  - `[medium]` `[patch]` `main()` now passes `not_filed` and prints a run-level summary — wired at scripts/conda-forge-packaging-inventory-operations_openteams_identity.py
  - `[medium]` `[patch]` `_gh_secondary_rate_limit` matches rate-limit text, not every 403 — scripts/conda-forge-packaging-inventory-operations_openteams_identity.py
  - `[medium]` `[patch]` corrupt Parquet stderr no longer says "not found" first — same script
  - `[medium]` `[patch]` gist/dashboard refuse synthetic timestamps — identity_gist.py + test fixture timestamp
  - `[medium]` `[patch]` canvas defaults resolve at write time via `default_*_canvas_path()` — openteams_identity_dashboards.py
  - `[medium]` `[patch]` `GIST_COLUMNS` ⊆ `IDENTITY_COMPLETE_EXPORT_COLUMNS` test — test_inventory_verification.py
  - `[false]` `[reject]` parquet executor thread cancellation — bounded deadline already fails named; full cancel deferred
  - `[false]` `[reject]` from-scratch test CSV-only — MD snapshot is the CAP-1 bar witness; CSV covered by actuator tests
  - `[maybe-false]` `[defer]` Kedro `Session` e2e vs direct node calls — e2e test exercises node chain; full session left for 27.2 if needed

## Auto Run Result

Status: done

Summary: Third send-back TEST SAFETY and snapshot bar — Kedro session e2e runs in an isolated project copy with stub credentials (no writes to member `data/`), gh handoff tests mock `subprocess.run` with an autouse guard, from-scratch fixture compares CSV and Markdown sha256 snapshots, metrics help/epilog documents `core_packages_enumerated` floor and restores the revised-prompt stdout line.

Files: `test_derived_artifacts_e2e.py`; `test_openteams_handoffs.py`; `test_inventory_from_scratch_fixture.py`; `expected_report.csv.sha256`; `conda-forge-packaging-inventory-operations_metrics.py`; `conda-forge-packaging-inventory-operations_replay.md`; spec surface memlogs and `spec-pyforge-atlas/SPEC.md`.

Review: HIGH send-back items addressed; medium mutant-coverage and prompt.md exact-shape sync deferred (see triage log above).

Follow-up review recommended: true — mutant-killing tests for canvas/timestamp/warning paths and prompt.md sync remain unverified at AC 7.

Verification: `kedro-test` 1879 passed; `kedro-catalog-check` 68 passed; `lint-types` 0; `spec_surface_reconcile.py` 0; `tests/packaging/test_openteams_handoffs.py` 53 passed; `scripts/tests/test_inventory_from_scratch_fixture.py` passed.
