---
title: 'Quartet thin-out and gist wrapper (Story 21.7, Epic 21)'
type: 'feature'
created: '2026-08-30'
status: 'done'
baseline_revision: '07da273ba7c52228e23cb26cf72148ac59151b20'
review_loop_iteration: 1
followup_review_recommended: true
deferred:
  - summary: >-
      Verification_Timestamp_UTC diverges between the persisted xlsx tab/CSV and the published
      gist on every non-`--skip-gist` run.
    evidence: |-
      write_gist_markdown has always unconditionally re-stamped Verification_Timestamp_UTC to a
      fresh datetime.now(...) for the gist -- confirmed unchanged at baseline commit 07da273ba7,
      so this pre-dates Story 21.7 and is not caused by it. main()/write_xlsx_tab/write_csv persist
      whatever the Parquet (or, before this story, the single per-run construction-time timestamp)
      carried instead.
    location: >-
      scripts/conda-forge-packaging-inventory-operations_openteams_identity.py:672-674
    severity: medium
  - summary: >-
      read_identity_export_records() has no try/except around pd.read_parquet, so a corrupt or
      unreadable Parquet crashes uncaught instead of producing a hard, named error.
    evidence: |-
      The I/O & Edge-Case Matrix only enumerates "Parquet present" and "Parquet missing"; a
      present-but-corrupt Parquet is an unstated edge case. The missing-file path already returns
      a clean, named stderr error + None -- a malformed-but-present file should plausibly follow
      the same pattern, but that's an inference, not something the matrix states.
    location: >-
      scripts/conda-forge-packaging-inventory-operations_openteams_identity.py:read_identity_export_records
    severity: medium
  - summary: >-
      RANKING_MERGE_COLUMNS (this script) and the Atlas-side gist-export column list are two
      independently hand-maintained copies of the same GIST_SCHEMA contract, with no test
      enforcing they stay aligned.
    evidence: |-
      RANKING_MERGE_COLUMNS is derived from GIST_COLUMNS, so it self-updates on this side when
      GIST_SCHEMA changes -- but the pyforge-atlas upstream_discovery pipeline that produces
      identity_export_parquet lists its own export columns separately. Touching that file is out
      of this story's scope (Never: "Implement identity_export_parquet or the Atlas Phase D node").
    location: >-
      scripts/conda-forge-packaging-inventory-operations_openteams_identity.py:132 vs.
      src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/upstream_discovery/nodes.py
    severity: medium
  - summary: >-
      No test exercises the real, Atlas-pipeline-produced identity_export_parquet -- every test
      builds its own hand-authored, already-conforming fixture.
    evidence: |-
      A genuine schema-parity check between this script's COLUMNS/GIST_SCHEMA expectations and
      what the real Story 21.6 Phase D join actually emits doesn't exist on either side of the
      contract. This is a cross-cutting testing-strategy gap, not something one story should
      absorb -- a fixture captured from a real pipeline run (matching pyforge-atlas's own Wave B
      parity-diff pattern) would be the natural shape for it.
    location: >-
      tests/packaging/test_openteams_handoffs.py
    severity: medium
  - summary: >-
      merge_ranking_columns merges ~12 secondary ranking/JFROG columns with a bare membership
      check and no warning if one is absent from the ranked tab.
    evidence: |-
      Only the primary P/Rank/Score/Work columns get an explicit missing-columns error in
      publish_gist_from_tab; the remaining RANKING_MERGE_COLUMNS entries (Platforms, Downloads,
      JFROG fields, etc.) are copied with `if col in ranking_row`, so an older or hand-edited
      ranked tab missing one silently produces a blank cell with no observability.
    location: >-
      scripts/conda-forge-packaging-inventory-operations_openteams_identity.py:merge_ranking_columns
    severity: low
  - summary: >-
      A Parquet column holding a list/array value crashes pd.isna() in
      read_identity_export_records with an ambiguous-truth-value ValueError.
    evidence: |-
      read_identity_export_records's per-cell stringify does `"" if pd.isna(v) else str(v).strip()`
      without first checking for a non-scalar value; pandas raises ValueError on pd.isna() for an
      array/list input rather than returning a scalar boolean.
    location: >-
      scripts/conda-forge-packaging-inventory-operations_openteams_identity.py:read_identity_export_records
    severity: low
  - summary: >-
      Two ranked-tab rows normalizing to the same pep503 name silently discard the earlier row in
      merge_ranking_columns, with no warning (unlike the miss case).
    evidence: |-
      ranking_by_name is built as a dict keyed by pep503_name(Core_Python_Package_Name); a later
      duplicate overwrites an earlier one with no diagnostic, asymmetric with the explicit
      stderr warning merge_ranking_columns emits on a no-match miss.
    location: >-
      scripts/conda-forge-packaging-inventory-operations_openteams_identity.py:merge_ranking_columns
    severity: low
  - summary: >-
      PYFORGE_ATLAS_DATA_ROOT="" (empty string) is falsy and silently resolves to the default
      path instead of being treated as an explicit-but-invalid override.
    evidence: |-
      identity_export_parquet_path() does `os.environ.get(PYFORGE_ATLAS_DATA_ROOT_ENV, "data")`,
      so an explicitly-set-but-empty env var (as opposed to unset) is indistinguishable from the
      unset default -- a narrow operator-error edge case, not currently triggered by any
      documented invocation.
    location: >-
      scripts/conda-forge-packaging-inventory-operations_openteams_identity.py:identity_export_parquet_path
    severity: low
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/identity-contract.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-conda-forge-packaging-inventory-operations/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-conda-forge-packaging-inventory-operations/.memlog.md'
---

<intent-contract>

## Intent

**Problem:** The identity script
(`scripts/conda-forge-packaging-inventory-operations_openteams_identity.py`) still live-fetches
`ASSOCIATOR_URL`, the inventory tab, and the OpenTeams board, then joins/overlays it all itself.
`--gist-only` depends on that join already having populated the identity xlsx tab. Story 21.6
lands `identity_export_parquet` (Atlas's own parity-tested Phase D join) but nothing consumes it,
and Epic 17's "purl-associator fetch stays in the quartet" constraint is now stale.

**Approach:** Replace `main()`'s fetch+join+overlay block with a read of `identity_export_parquet`.
Make `--gist-only` read that Parquet for identity/overlay columns, merged with ranking columns
(`P`/`Rank`/`Score`/`Work` + JFROG) still sourced from the existing ranked identity xlsx tab
(`priority.py`'s output, untouched -- Epic 23.5 supersedes this merge). Supersede Epic 17's
constraint with a dated memlog entry.

## Boundaries & Constraints

**Always:**
- No direct HTTP/GraphQL call to a public/board endpoint remains; `main()` builds `records` from
  one `identity_export_parquet` read.
- Parquet path resolves via the `PYFORGE_ATLAS_DATA_ROOT` / `${paths.data_root}/...` convention
  `globals.yml` uses (Story 21.1) -- use the landed filepath, do not guess it.
- `--gist-only` reads that Parquet for identity/overlay columns, merges ranking columns from the
  ranked xlsx tab by `Core_Python_Package_Name`; today's missing-ranking-columns error stays.
- `write_xlsx_tab`, `create_missing_issues`, canvas/gist writers, `--skip-gist`/`--create-issues`
  unchanged (`create_missing_issues`'s `board` arg becomes `{}` -- write-only, never read back).
- Append a dated inventory-memlog entry superseding the 2026-08-22 Story 17.1 clause,
  cross-referencing `identity-contract.md`.

**Block If:** None -- `identity-contract.md` fully specifies the target row shape.

**Never:**
- Touch `priority.py` or ranking logic (Epic 23.3).
- Touch gist/dashboard/canvas markdown generation beyond input-row source.
- Implement `identity_export_parquet` or the Atlas Phase D node (Story 21.6 dependency).
- Implement Epic 23.5's ranking-merged complete export -- merge stays a `--gist-only`-time join.
- Remove `write_xlsx_tab`/the identity-out tab (`priority.py`'s input).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `main()`, Parquet present | Atlas bootstrap + Phase D ran | Records match today's identity columns | No error expected |
| `main()`, Parquet missing | Fresh clone / no bootstrap | Exit non-zero naming the missing file/step | Never fall back to a live fetch |
| `--gist-only`, tab has ranking columns | Steady state | Parquet rows merged with ranking by name; gist published | No error expected |
| `--gist-only`, tab missing ranking columns | `priority.py` never ran | Return 1, existing error message | Unchanged from today |
| `--gist-only`, a name has no cross-source match | Universe drift | Row skipped, stderr warning names it | Never silent-drop; never raise |

</intent-contract>

## Code Map

- Identity script -- `ASSOCIATOR_URL` (~L79), `main()`'s fetch+join+overlay block (~L1382-1436),
  `publish_gist_from_tab` (~L1198-1236), and the 9 now-dead CLI flags feeding the associator/
  inventory-tab/board/overlay fetch (~L1256-1301 argparse block) -- all retired together with the
  helper functions they call (`lookup_assoc`, `from_assoc`, `from_inventory`, `from_board_only`,
  `attach_packaging_urls`, `read_inventory_tab`, `fetch_project_issues`,
  `board_packaging_urls`). **`overlay_live_local` is NOT part of this retirement** (corrected
  2026-08-31, review pass 1): it does a local-only `recipes/` filesystem scan, never an
  HTTP/GraphQL call, so it isn't in scope of the "no direct HTTP/GraphQL call... remains"
  boundary, and `write_gist_markdown` -- one of the "canvas/gist writers" the Always-boundary
  requires stay unchanged -- calls it internally. Retiring it would break that unchanged writer.
- `main()` must still invoke `overlay_live_local(records, REPO_ROOT / "recipes")` on the
  Parquet-sourced `records`, in the same place the old fetch+join+overlay block used to (right
  after building `records`, before `create_missing_issues`/`write_xlsx_tab`/`write_csv`) --
  removing the retired fetch/join code must not silently drop this local-only refresh too.
  `write_gist_markdown`'s own internal `overlay_live_local` call (unchanged) then re-runs on
  already-overlaid data for the gist step, so the persisted xlsx tab, `--output-csv`, and the
  published gist all agree on `Local_Recipes_URL`/`Local_Build_Status` within one run -- the same
  single-live-snapshot guarantee the pre-story code had. (`load_local_recipes`/
  `load_local_build_status`/`name_keys`/`first_map` stay for the same reason `overlay_live_local`
  does.) **Correction (2026-08-31, review pass 2):** `Verification_Timestamp_UTC` is NOT part of
  this guarantee, in this story or before it -- `write_gist_markdown` has always unconditionally
  re-stamped it to `datetime.now(...)` for the gist (confirmed unchanged at baseline
  `07da273ba7`), independent of whatever the tab/CSV persisted. That divergence pre-dates this
  story; it is deferred, not fixed here (see `## Review Triage Log`, pass 2).
- `src/shared/packages/pyforge-atlas/conf/base/globals.yml` (~L104-109, `paths.data_root`) --
  path convention to mirror (reference only).
- `identity-contract.md` -- Join semantics + Gist publish section (this story's target).
- Inventory `.memlog.md` + `SPEC.md` `## Constraints` -- where the superseding entry lands. The
  memlog entry's explanation for why `overlay_live_local` (and its local-only helpers) survive
  must name its real caller (`write_gist_markdown`, called directly) -- not the unrelated
  `openteams_identity_dashboards.py` `helpers = types.SimpleNamespace(**globals())` bridge (that
  bridge is why `packaging_name_from_title`/`join_list`/etc. survive, a separate reason).
- `tests/packaging/test_openteams_handoffs.py` -- `create_missing_issues`/canvas coverage
  unaffected; add coverage for the new read/merge paths.

## Tasks & Acceptance

**Execution:**
- Identity script -- swap `main()`'s fetch+join+overlay block for a `pandas.read_parquet` read
  (pandas already in `local-recipes`) into `records`, path via `PYFORGE_ATLAS_DATA_ROOT`; exit
  non-zero with a clear message if the file is missing. Immediately after, call
  `overlay_live_local(records, REPO_ROOT / "recipes")` on those records before any output is
  written (tab, CSV, or gist) -- see Code Map.
- Same file -- retire the dead functions/flags in Code Map (keeping `overlay_live_local` and its
  helpers); pass `board={}` to `create_missing_issues`.
- `tests/packaging/test_openteams_handoffs.py` -- add a `main()`-level test for the default
  (non-`--skip-gist`) path that plants a real `recipes/<pkg>/recipe.yaml` differing from the
  Parquet fixture's `Local_Build_Status`/`Local_Recipes_URL`, and asserts the value written to the
  persisted xlsx tab via `read_xlsx_tab` already reflects the live-scanned value (i.e. matches what
  the mocked gist publish would also see) -- this is the regression test for the Code Map fix
  above.
- Same file -- rewrite `publish_gist_from_tab`: read the Parquet for identity/overlay columns,
  merge ranking + JFROG columns from the ranked xlsx tab by name; keep the missing-columns error;
  warn (not raise) on a per-name merge miss.
- Inventory `.memlog.md` -- append a dated entry superseding Story 17.1's clause, cross-ref
  `identity-contract.md`; update `SPEC.md` `## Constraints` with a superseding note (keep
  history, mirror the Epic 16->17 renumber entry).
- `docs/reference/conda-forge-packaging-inventory-operations_replay.md` -- update flag docs for
  the retired/changed CLI surface.
- `tests/packaging/test_openteams_handoffs.py` (or a sibling) -- cover the I/O matrix.
- Housekeeping -- grep for orphaned callers of the retired symbols; re-stamp
  `scripts/.spec-surface-baseline.json` scoped to the inventory spec.

**Acceptance Criteria:**
- Given a full `main()` + `--gist-only` run against a bootstrapped Atlas data root, when audited,
  then neither makes a direct HTTP/GraphQL call to `ASSOCIATOR_URL` or the OpenTeams board API,
  and published gist rows carry both Parquet-sourced identity/overlay columns and tab-sourced
  ranking columns.
- Given the inventory `.memlog.md`, when this story lands, then it carries a dated entry
  superseding the Story 17.1 purl-associator-stays-in-quartet clause, cross-referencing
  `identity-contract.md`.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Spec Change Log

### 2026-08-31 — Review pass 1 loopback (bad_spec)
- **Trigger:** Review pass 1 (blind-hunter/edge-case-hunter/verification-gap/intent-alignment, run
  against the first implementation attempt) converged -- 3 of 4 layers independently -- on: the
  persisted xlsx tab/CSV and the published gist could silently disagree on
  `Local_Recipes_URL`/`Local_Build_Status`/`Verification_Timestamp_UTC` within a single `main()`
  run, because the pre-write live-local overlay that used to run once (feeding both outputs
  identically) was dropped from `main()` along with the retired fetch+join block, while
  `write_gist_markdown`'s own internal overlay call (required to stay unchanged) still runs, but
  only for the gist, and only after the tab/CSV are already on disk.
- **Root cause:** this `## Code Map`'s original retirement list named `overlay_live_local` as one
  of the helpers retired alongside the fetch+join block -- but `overlay_live_local` does a
  local-only filesystem scan (never HTTP/GraphQL), and `write_gist_markdown` (an unchanged "gist
  writer" per the `<intent-contract>` Always-boundary) calls it directly. The Code Map
  contradicted the Always-boundary: it could not be followed literally without breaking an
  unchanged writer. The first implementation resolved that contradiction correctly (kept the
  function) but the Code Map never told it to keep *calling* it from `main()` before persisting,
  so the single-live-snapshot guarantee silently regressed.
- **Amended:** `## Code Map` -- removed `overlay_live_local` from the retirement list, explained
  why, and added the explicit requirement that `main()` call it on the Parquet-sourced `records`
  before any output write. `## Tasks & Acceptance` -- added the corresponding execution step and a
  regression-test requirement for the `main()` default (non-`--skip-gist`) path. `<intent-contract>`
  is unchanged (this was never a gap in the Intent/Boundaries/Matrix themselves -- the Approach's
  "replace... fetch+join+overlay block" refers to the retired network-sourced join, not the
  unrelated local-only recipe scan).
- **Known-bad state avoided:** re-deriving without this fix would very likely reproduce the same
  divergence (nothing in the corrected boundary text was ambiguous once stated, so a fresh
  implementation given only the old Code Map would plausibly make the same choice again).
- **KEEP (positive preservation for re-derivation):** a byte-level reference of the reverted
  attempt is saved at `_bmad-output/implementation-artifacts/story-21-7-prior-attempt.patch`. In
  particular, keep:
  - The exact retirement list (functions, constants, and 9 CLI flags) from the amended Code Map
    above -- verified via repo-wide grep that none of them have any other caller.
  - `identity_export_parquet_path()` (`PYFORGE_ATLAS_DATA_ROOT_ENV` env override, default relative
    to `PYFORGE_ATLAS_PROJECT_DIR = REPO_ROOT / "src/shared/packages/pyforge-atlas"`,
    `IDENTITY_EXPORT_PARQUET_RELPATH = Path("derived/identity_export_parquet/identity_export_parquet.parquet")`
    -- verified to match `catalog.yml`'s landed `filepath:` entry verbatim).
  - `read_identity_export_records()` (`pandas.read_parquet`; stringify `NaN`/`pd.NA` to `""`;
    missing file -> stderr message naming the path + `pyforge-atlas-bootstrap`, return `None`,
    never raise, never fall back to a live fetch).
  - `merge_ranking_columns()` (`RANKING_MERGE_COLUMNS = [c for c in GIST_COLUMNS if c not in
    COLUMNS and c != "Package"]`, derived not hand-listed; match by
    `pep503_name(Core_Python_Package_Name)`; a Parquet name with no ranked-tab match is dropped
    with a stderr warning naming it, never raised).
  - `create_missing_issues(gh_bin(), records, {}, ...)` -- `board` always `{}` (write-only).
  - `publish_gist_from_tab` -- keep the ranked-tab missing-ranking-columns check strictly before
    any Parquet read (tested: the Parquet must never be touched once that check fails).
  - The 11 new tests from the prior attempt (test names in the saved patch), reused verbatim where
    still applicable: `test_identity_export_parquet_path_respects_data_root_env`,
    `test_identity_export_parquet_path_default_relative_to_atlas_project_dir`,
    `test_read_identity_export_records_reads_parquet_and_stringifies_nulls`,
    `test_read_identity_export_records_missing_file_returns_none_and_names_it`,
    `test_merge_ranking_columns_merges_by_name_and_warns_on_a_miss`,
    `test_merge_ranking_columns_never_raises_on_a_total_miss`,
    `test_dead_flags_removed_from_argparse`, `test_main_reads_parquet_writes_tab_and_skips_gist`,
    `test_main_exits_nonzero_when_parquet_missing`,
    `test_publish_gist_from_tab_merges_ranking_and_never_falls_back_to_a_live_fetch`,
    `test_publish_gist_from_tab_returns_1_when_tab_missing_ranking_columns` -- plus the new
    default-path regression test required above.
  - The `docs/reference/conda-forge-packaging-inventory-operations_replay.md` Deliverable 3
    paragraph and the `.memlog.md`/`SPEC.md` superseding entries -- reuse the substance, correcting
    the `overlay_live_local` survival reason per the amended Code Map note.

## Review Triage Log

### 2026-08-31 — Review pass 1
- intent_gap: 0
- bad_spec: 1: (high 1, medium 0, low 0)
- patch: 8: (high 1, medium 2, low 5)
- defer: 3: (high 0, medium 3, low 0)
- reject: 2
- addressed_findings:
  - `[high]` `[bad_spec]` main()/write_gist_markdown overlay-ordering divergence (tab/CSV vs gist
    can silently disagree on Local_Recipes_URL/Local_Build_Status/Verification_Timestamp_UTC) --
    traced to Code Map's incorrect `overlay_live_local` retirement; Code Map and Tasks &
    Acceptance amended above, code reverted, re-derivation follows.
- other findings this pass (moot per cascading rule -- not applied, itemized here for the record;
  re-triaged fresh on the next review pass against the re-derived code):
  - `[low]` `[patch]` memlog's stated reason `overlay_live_local` survives (dashboards bridge) is
    factually wrong -- it's called directly by `write_gist_markdown`.
  - `[low]` `[patch]` module docstring overclaims `Local_Recipes_URL`/`Local_Build_Status` come
    from the Parquet; `write_gist_markdown` always live-overlays them.
  - `[medium]` `[patch]` no test exercises `main()`'s default (non-`--skip-gist`) path against the
    new Parquet-sourced records.
  - `[medium]` `[patch]` `--cache-dir` is silently ignored on the `--gist-only` path;
    `publish_gist_from_tab` always writes to the hardcoded `CACHE_DIR`.
  - `[low]` `[patch]` `create_missing_issues`'s now-always-`{}` `board` param is dead weight, not
    dropped.
  - `[low]` `[patch]` unnecessary `# noqa: E402` on `import pandas as pd` in the test file (ruff
    doesn't select E402 here).
  - `[high]` `[patch]` `publish_gist_from_tab` has no guard against `merge_ranking_columns`
    returning an empty/near-empty list -- would publish and overwrite the pinned gist with
    near-empty content while returning 0.
  - `[low]` `[patch]` the new merge test calls the real, unmocked `write_gist_markdown`, which
    scans this actual repo's `recipes/` dir instead of an isolated fixture (non-hermetic).
  - `[medium]` `[defer]` `RANKING_MERGE_COLUMNS` (script side) and the Atlas-side gist-export
    column list (`pyforge-atlas/.../upstream_discovery/nodes.py`) are two independently
    hand-maintained copies of the same `GIST_SCHEMA` contract with no test enforcing alignment --
    touching the Atlas side is out of this story's scope (Never-boundary).
  - `[medium]` `[defer]` `read_identity_export_records()` only checks file existence, not schema
    validity -- a corrupt or column-mismatched Parquet degrades silently (crash or blank fields)
    rather than the same hard, named error the missing-file case gets; the I/O matrix doesn't
    enumerate this scenario.
  - `[medium]` `[defer]` no test exercises the real, Atlas-pipeline-produced
    `identity_export_parquet` (all tests build their own conforming fixture) -- a genuine
    cross-package parity check is absent from both sides; belongs to a future story, not this one.
  - `[low]` `[reject]` `scripts/.spec-surface-baseline.json`'s re-stamp incidentally also fixed an
    unrelated, pre-existing hash-drift entry for `..._metrics.py`/its test (from an earlier
    story's incomplete stamp) -- expected mechanical behavior of `--write-baseline`, not a defect.
  - `[low]` `[reject]` the merge only warns on a Parquet-name-with-no-ranked-tab-match, not the
    reverse direction -- defensible given the "steady state" matrix row frames the merge as
    Parquet-rows-primary ("Parquet rows merged with ranking by name").

### 2026-08-31 — Review pass 2
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 2, medium 2, low 2)
- defer: 7: (high 0, medium 4, low 3)
- reject: 2
- addressed_findings:
  - `[high]` `[patch]` `Package` (GIST_SCHEMA-required) was blank in every published gist row --
    `RANKING_MERGE_COLUMNS` deliberately excludes it and nothing else set it; `merge_ranking_columns`
    now sets `out["Package"] = row.get("Core_Python_Package_Name", "")` unconditionally.
  - `[high]` `[patch]` `publish_gist_from_tab` had no guard against `merge_ranking_columns`
    returning empty/near-empty -- would publish + overwrite the pinned gist with near-empty
    content while returning 0; added the `if not records: ...; return 1` guard.
  - `[medium]` `[patch]` `test_main_reads_parquet_writes_tab_and_skips_gist` and
    `test_publish_gist_from_tab_merges_ranking_and_never_falls_back_to_a_live_fetch` scanned the
    real repo `recipes/` dir (pass-1's fix made `main()`'s overlay call unconditional, widening
    this) -- both now `monkeypatch.setattr(identity, "REPO_ROOT", tmp_path)`.
  - `[medium]` `[patch]` module docstring + replay-doc overclaimed `Local_Recipes_URL`/
    `Local_Build_Status` come from the Parquet -- reworded to state they're always freshly
    live-scanned.
  - `[low]` `[patch]` `test_project_item_add_failure_does_not_mark_row_as_tracked`'s docstring
    still named the retired `board_packaging_urls` -- reworded to current semantics.
  - `[low]` `[patch]` pass-1's triage-log entry gave bare counts for `patch`/`defer`/`reject`
    without itemizing them (this repo's established convention, e.g. Story 17.2's memlog) --
    itemized above under pass 1's entry.
- other findings this pass (real, but not caused by this story, or genuine future hardening --
  not applied; added to frontmatter `deferred:` below):
  - `[medium]` `[defer]` `Verification_Timestamp_UTC` diverges between the persisted tab/CSV and
    the published gist on every non-`--skip-gist` run -- **confirmed pre-existing**:
    `write_gist_markdown` has always unconditionally re-stamped it fresh for the gist
    (unchanged at baseline `07da273ba7`), independent of what the tab/CSV persisted. Not caused
    by this story; Code Map's pass-1 wording corrected above to stop overclaiming it.
  - `[medium]` `[defer]` `read_identity_export_records()` has no try/except around
    `pd.read_parquet` -- a corrupt/unreadable Parquet crashes uncaught instead of the same kind
    of hard, named error the missing-file case gets; the I/O matrix doesn't enumerate this
    scenario.
  - `[medium]` `[defer]` `RANKING_MERGE_COLUMNS` (script side) and the Atlas-side gist-export
    column list are two independently hand-maintained copies of `GIST_SCHEMA` with no alignment
    test; touching the Atlas side is out of this story's scope (Never-boundary).
  - `[medium]` `[defer]` no test exercises the real, Atlas-pipeline-produced
    `identity_export_parquet` -- all tests build their own conforming fixture; a genuine
    cross-package parity check belongs to a future story.
  - `[low]` `[defer]` `merge_ranking_columns` merges ~12 secondary columns (Platforms/Downloads/
    JFROG fields/etc.) with a bare `if col in ranking_row`, no warning if one is absent, unlike
    the explicit P/Rank/Score/Work check.
  - `[low]` `[defer]` a Parquet column holding a list/array value crashes `pd.isna()` in
    `read_identity_export_records` (ambiguous-truth-value `ValueError`) instead of stringifying.
  - `[low]` `[defer]` two ranked-tab rows normalizing to the same `pep503_name` silently discard
    the earlier row in `merge_ranking_columns`, with no warning (unlike the miss case).
  - `[low]` `[defer]` `PYFORGE_ATLAS_DATA_ROOT=""` (empty string) is falsy, so it silently
    resolves to the default path instead of being treated as an explicit-but-invalid override.
- rejected this pass:
  - `[low]` `[reject]` `scripts/.spec-surface-baseline.json`'s re-stamp again touched the
    unrelated, already-explained `..._metrics.py`/test hash entries -- confirmed (again) as
    expected `--write-baseline` mechanics, not a defect.
  - `[low]` `[reject]` reverse-direction cross-source-match still unwarned -- same defensible
    one-directional design as pass 1.

## Auto Run Result

**Summary:** `main()`'s fetch+join+overlay block (live `ASSOCIATOR_URL`, OpenTeams board GraphQL,
`feedstock-outputs.json`, staged-recipes PR fetch) is replaced by one `pandas.read_parquet` read of
the pyforge-atlas Kedro catalog's `identity_export_parquet` (Story 21.6's Phase D join), resolved
via `PYFORGE_ATLAS_DATA_ROOT` -- a missing Parquet is a hard, named, non-zero-exit error, never a
live-fetch fallback. `main()` then live-overlays `Local_Recipes_URL`/`Local_Build_Status` via the
existing (kept, not retired) `overlay_live_local` before any output write, so the persisted xlsx
tab, `--output-csv`, and the published gist agree within one run -- the bug a review-pass-1
loopback found and fixed. `--gist-only` (`publish_gist_from_tab`) merges ranking/JFROG columns
from the ranked identity tab onto the Parquet-sourced rows by `Core_Python_Package_Name`
(`merge_ranking_columns`, including the required `Package` display-name field, a review-pass-2
fix), guards against a near/total merge miss, and keeps the pre-existing missing-ranking-columns
error unchanged and checked first. 9 dead CLI flags and ~20 now-orphaned helper
functions/constants are retired; `overlay_live_local` and its dependents are explicitly kept
(needed by the unchanged `write_gist_markdown`). The inventory `.memlog.md`/`SPEC.md` carry a dated
entry superseding Story 17.1's "purl-associator stays in the quartet" clause.

**Files changed:**
- `scripts/conda-forge-packaging-inventory-operations_openteams_identity.py` -- core rewrite: new
  `identity_export_parquet_path()`/`read_identity_export_records()`/`merge_ranking_columns()`;
  retired fetch/join helpers and flags; `main()`/`publish_gist_from_tab` rewritten per above.
- `tests/packaging/test_openteams_handoffs.py` -- 12 new tests (16 -> 28) covering the I/O &
  Edge-Case Matrix, the overlay-ordering regression, and the merge/guard fixes.
- `docs/reference/conda-forge-packaging-inventory-operations_replay.md` -- documents the new
  Parquet source, retired flags, and the always-live-scanned `Local_Recipes_URL`/
  `Local_Build_Status` nuance.
- `_bmad-output/.../spec-conda-forge-packaging-inventory-operations/{SPEC.md,.memlog.md}` --
  dated superseding entries for Story 17.1's clause plus this story's landed-work entry.
- `scripts/.spec-surface-baseline.json` -- re-stamped scoped to this spec.
- `_bmad-output/.../spec-21-7-quartet-thin-out-and-gist-wrapper.md` (this file) -- Code Map/Tasks &
  Acceptance amended (review pass 1), Spec Change Log + Review Triage Log + `deferred` added.

**Review findings breakdown (both passes):**
- Pass 1: 1 `bad_spec` (fixed via spec amendment + revert + re-derivation), 8 `patch` (moot,
  re-triaged fresh in pass 2), 3 `defer` (moot, re-triaged fresh in pass 2), 2 `reject`.
- Pass 2: 6 `patch` (all applied), 7 `defer` (recorded in frontmatter `deferred`), 2 `reject`.
- Net: 6 patches applied and verified; 8 items deferred (frontmatter, for a future story/pass); 4
  items rejected across both passes as noise/defensible-as-is.

**Follow-up review recommendation:** `true`. This pass's `patch` findings: 6 total (high 2, medium
2, low 2). Trigger: at least one `high`-severity patched finding (2 of them) -- the flag is set
regardless of the score, which is also over threshold: `3 × 2 (medium) + 1 × 2 (low) = 8 >= 5`.

**Verification performed:**
- `pixi run -e pyforge-atlas kedro-test` -- 1595 passed, 24 skipped (both passes, independently
  re-run by the orchestrator each time).
- `pixi run -e pyforge-atlas kedro-catalog-check` -- 61 passed (both passes, independently re-run).
- `pixi run -e local-recipes pytest tests/packaging/test_openteams_handoffs.py -q` -- 28 passed
  (independently re-run after the pass-2 patch set).
- `pixi run -e local-recipes test-packaging` -- 146 passed (subagent-reported, both passes).
- `pixi run -e pyforge-ci pyforge-deps-test` -- 118 passed, 1 skipped (lean-env `openpyxl`/`pandas`
  import-skip guard still correct; subagent-reported).
- `python -m py_compile` on both changed Python files -- clean.
- `--help` -- confirmed all 9 retired flags are gone.
- Repo-wide grep -- zero orphaned callers of any retired symbol.
- Orchestrator independently confirmed (not just subagent-reported): the `overlay_live_local` call
  site precedes `write_xlsx_tab`/`write_csv` in `main()` (source grep); `out["Package"] = ...` and
  the `if not records:` guard exist in `merge_ranking_columns`/`publish_gist_from_tab` (source
  grep); the `Verification_Timestamp_UTC` divergence is pre-existing at baseline commit
  `07da273ba7` (direct `git show` diff against baseline, not just the subagent's claim).

**Residual risks:** the 8 deferred items above (frontmatter `deferred`) are real but out of this
story's scope or not caused by it -- most notably `Verification_Timestamp_UTC`'s pre-existing
tab-vs-gist divergence, and the absence of any test against a real (not hand-fixture) Atlas-produced
Parquet. This dispatch touches files outside `recipes/`; per `CLAUDE.md`'s PR-gate rule, the PR for
branch `dispatch/pyforge-atlas/21.7` needs the `maintenance` label. No `pixi.toml`/`environment.yaml`
change was needed.
