---
title: "37.7: The find-alternative scores candidates for archived packages"
type: 'feature'
created: '2026-10-23'
status: 'in-review'
baseline_revision: 'e5810642d17ebee7159c3e020235d98918386e55'
flag:
  key: pyforge.atlas.board_projections            # existing; minted by Story 37.4, extended to this board
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through src/platform/config/flag-overlays.json
  scope: global                                   # v1 is global only
  fallback: 'the find-alternative reads primary/alternative_candidates as before, which nothing writes, and renders empty'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - docs/reference/story-spec-flag-block.md
  - .claude/skills/conda-forge-expert/scripts/find_alternative.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/core_sources.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the find-alternative board reads `primary/alternative_candidates/`, and no node writes it
(DW-atlas-37-7-1). Legacy `find_alternative.py` scores one package per query from the package's summary and
keywords, and atlas stores neither.

**Approach:**
1. **Summary and keywords.** The cf-graph frame (`CfGraphTarballDataset`) adds two columns on each output's anchor row:
   - `summary` is `about.summary`;
   - `keywords` is `about.keywords` as a list of strings.

   Legacy Phase E reads both there (CFA:2327-2334), and `package_recipe_fields` gives them to each package by
   feedstock attribution, as it already gives the recipe URLs. The summary is stored as legacy's `_str` stores it:
   a list is joined with `, ` and any other value becomes its string. A keyword value that is not a list gives no
   keywords, since legacy's scorer drops it too. A kept `last_good.parquet` from before this story has neither
   column, so it gives no text and no candidates.
2. **A node,** `score_alternative_candidates` (new module `derived_artifacts/alternatives.py`, a port of legacy's
   `find_alternatives`). It scores every archived package on the channel:
   - the archived packages are those in `semantic_packages` whose feedstock is archived. That is either
     `semantic_packages.feedstock_archived` (from `vcs_archived_feedstocks`) or the cf-graph's own `archived` flag,
     which core's Phase J skip-set already reads;
   - the summary, the keywords and the cf-graph flag reach a package only through `core_feedstock_attribution`,
     as legacy's Phase E and E.5 reach it through Phase B.5. `package_recipe_fields(..., unattributed=False)`
     drops its first-anchor fallback here, so a package attribution does not list gets nothing;
   - each candidate is a package in `semantic_packages` that is `active`, not archived, and not the package itself;
   - the score is keyword Jaccard ×3 + summary-term Jaccard ×2 + shared-dependent Jaccard ×4 + shared-maintainer
     Jaccard ×1. Dependents come from `core_dependencies` and maintainers from `vcs_package_maintainers`. A candidate
     with no keyword or summary-term overlap is skipped, and so is one that scores under 0.10;
   - the composite is score × (0.5 + 0.5 × recency) × (1.0 with downloads, else 0.5). Recency falls linearly from 1.0
     to 0 over five years from `latest_conda_upload`, and is 1.0 without one;
   - it keeps the top 10 candidates per archived package, by composite (rounded to three places, as legacy reports
     it), then by name.

   It writes `derived_alternative_candidates`. Each row holds `archived_name`, `candidate_name`, `similarity_score`
   (the composite), the four component scores, `rank`, `downloads_total`, the candidate's `summary`, and the
   adoption-stage inputs (`latest_upload_age_days`, `releases_30d`, `total_versions`).
3. **The board,** behind `pyforge.atlas.board_projections` as Stories 37.4–37.10's boards are:
   - on, find-alternative reads `derived_alternative_candidates`;
   - off, it reads `primary/alternative_candidates/` as before.

   `adoption_stage` becomes `build_packages_model`'s classifier (`metrics.adoption_stage`) over the candidate's own
   inputs, so the two boards always agree. A store in the earlier shape, with an `adoption_stage` column and no
   inputs, still reads its own column. `similarity_score` stays a pass-through column.

**Deviations from legacy:**
- The board scores every archived package in one run, where legacy scores the one package a query names.
- The archived set adds the cf-graph's `archived` flag to legacy's Phase E.5 GitHub query
  (`vcs_archived_feedstocks`), which a public run does not fill.
- `semantic_packages` has no upload times yet (`latest_conda_upload`, `latest_upload_age_days`, `releases_30d` and
  `total_versions` are NULL; Story 37.6 sources them). Until then:
  - recency is 1.0 for every candidate, as legacy gives a package with no upload time;
  - `adoption_stage` reads `unknown`, as the adoption-stage board does today.
- Ties in the composite fall to the candidate name; legacy's order among ties is SQLite's row order.

Ledger key: `37-7-the-find-alternative-scores-candidates-for-archived-packages`.
Type / Effort / Deps: feature / M / Story 37.1 (the data root).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-69** (FR-77, the boards no pipeline feeds).
- **AD-2/AD-13**: the cf-graph dataset owns the about-field parse, and a kept copy without the columns degrades to no
  text.
- **AD-8**: BSL over DuckDB. The composite is computed upstream and passed through, and `adoption_stage` is the one
  registered classifier.
- **AD-14**: a new rider, not parity-gated.
- **AD-17**: the page's stamp comes from the dataset it reads.

## Acceptance Criteria

- **AC1 — About text.** An anchor row carries its recipe's `about.summary` and `about.keywords`; an edge row carries
  neither. `package_recipe_fields` gives them to every attributed output, and to no unattributed one.
- **AC2 — Archived set.** A package is scored when it is on the channel and its attributed feedstock is archived by
  either source. A package archived nowhere, or not attributed, is never an `archived_name`.
- **AC3 — Candidates.** Only an active, unarchived package other than the archived one is a candidate. It needs a
  keyword or summary-term overlap and a score of at least 0.10.
- **AC4 — Score.** The component scores and the composite follow legacy's weights, tokenizer (stopwords, three
  characters and up, lowercase), recency (fractional days over 1,825; 0 as no upload; clamped at 0, not at 1) and
  download factor; the floor reads the score, not the composite.
- **AC5 — Rank.** There are at most 10 rows per archived package, ranked by the composite rounded to three places,
  then by name.
- **AC6 — Board.** With the flag on, the board reads `derived_alternative_candidates`, its AD-17 stamp names that
  file, and its `adoption_stage` equals the adoption-stage board's for the same inputs. With the flag off, it reads
  `primary/alternative_candidates/` as before.

## Boundaries & Constraints

**Always:** pure over its input frames; never reach the network beyond what the cf-graph dataset already fetches.

**Never:** change core's outputs (`core_dependencies`, `core_packages_enumerated` and the rest), or
`semantic_packages`.

**Residual risk:**
- `semantic_packages.feedstock_archived` reads only `vcs_archived_feedstocks`, so on a public run the actionable and
  adoption views count archived feedstocks as live. This node reads the cf-graph flag too; the other views are
  DW-atlas-37-7-2's.
- A live package can be scored as archived. Phase B.5 attributes a package to its dedicated feedstock even when that
  feedstock is archived and a live one builds it now. On the live data, 60 scored packages are outputs of a live
  feedstock as well, among them duckdb, grpcio and apache-airflow-core. Legacy's attribution does the same, and
  the fix belongs in core's attribution, so it is DW-atlas-37-7-3's.
- Until Story 37.6 lands upload times, recency does not separate a stale candidate from a fresh one.

## I/O & Edge-Case Matrix

| Input | Result |
|-------|--------|
| archived package with no summary, keywords or overlap | no rows |
| candidate sharing only a dependent | not scored (legacy needs a keyword or term overlap) |
| candidate with no downloads | composite halved |
| candidate archived by the cf-graph only | never a candidate |
| package no attribution row lists | no text, no flag: never scored, never a candidate |
| `latest_status` missing | not active, never a candidate |
| an upload time of 0, or none | recency 1.0 |
| a score of exactly 0.10 | kept |
| inactive candidate | never a candidate |
| more than 10 candidates | the top 10 |
| a kept cf-graph copy without `summary` or `keywords` | no rows, no error |
| nothing in | an empty frame with the output columns |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-69 (FR-77). No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-19 entry (the Vizro boards read their data).
- Epic: Epic 37 (in progress). Closes DW-atlas-37-7-1; opens DW-atlas-37-7-2 and DW-atlas-37-7-3.
- Ledger key: `37-7-the-find-alternative-scores-candidates-for-archived-packages`.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas pyforge-atlas-test` — expected: pass.
- From the repo root: `src/shared/packages/pyforge-atlas/tests/unit/pipelines/derived_artifacts/test_alternatives.py`
  (the scorer and the about text), `src/shared/packages/pyforge-atlas/tests/unit/semantic/test_board_models.py` (the
  stage) and `src/shared/packages/pyforge-atlas/tests/unit/test_board_projections.py` (both flag states) — expected:
  pass.

## Run results

Run 2026-10-23 in the landing worktree on `e5810642d1`, every verdict read from its exit code; the numbers are those
after review 1's fixes.

- **AC1–AC6, tests:** `test_alternatives.py` (32), `test_board_models.py` and `test_board_projections.py` pass;
  `pyforge-atlas-test` gives 3,268 passed and 20 skipped, then 103 passed (exit 0).
- **Pins moved:** `derived_artifacts` has 13 nodes (12), the combined DAG 72 (71), the catalog 143 entries (142); the
  node has a timeout (900 s).
- **Mutations**, each restored, each failing a named test (37 of 37):
  - score: a keyword weight changed; the 0.10 floor removed, made inclusive, or applied to the composite; recency
    ignored, unclamped, over a 365.25-day year or in whole days; an upload of 0 read as a time; the download factor
    ignored; the composite not rounded before ranking; the component scores unrounded;
  - tokenizer and keywords: stopwords kept; short words kept; keywords not lowercased; a string keyword accepted;
  - archived set and candidates: the cf-graph flag ignored; `semantic_packages`' flag ignored; the first-anchor
    fallback kept; inactive, archived or status-less candidates kept; candidates without an overlap scored; a
    keyword-only overlap dropped; a package's dependencies read as its dependents; maintainers ignored;
  - rank and output: the limit ignored; ties not broken by name; the stage inputs dropped; the empty frame untyped;
  - about text: the summary not read, not joined from a list, or not stringified; a kept copy's keywords not read
    back as lists;
  - board: the board path not switched; the stage not the shared classifier; a store in the earlier shape not read.
- **Real data:** a fresh public parse of the cf-graph (359,499 rows, 33,527 anchor rows, in 31 s), with Story 37.2's
  live data root for `semantic_packages`, `core_dependencies`, `vcs_package_maintainers` and the attribution:
  - 32,791 anchor rows carry a summary and 1 carries keywords. Conda-forge recipes almost never set
    `about.keywords`, so the summary terms carry the text score, as they do for legacy;
  - 828 packages on the channel are attributed to an archived feedstock (`semantic_packages` flags none,
    DW-atlas-37-7-2). 824 get candidates;
  - the node runs in 3.9 s and writes 8,199 rows (a median of 10 per package) over 4,623 distinct candidates,
    342 KB of Parquet;
  - **legacy parity:** the comparison builds legacy's store on its own, from the attribution, the cf-graph anchors and
    the same frames (Phase B.5, E and E.5 semantics), not from the port's mapping. Legacy `find_alternatives` then
    runs for every archived package with no limit, re-ranked by score and then name, top 10. All 828 lists match the
    port exactly: names, composite, the four components and downloads;
  - 60 scored packages are also outputs of a live feedstock (DW-atlas-37-7-3); none scored is off the channel or
    unarchived.

## Spec Change Log

- 2026-10-23, independent review (FAIL, 2 blockers), fixed on the same branch:
  - B1: no spec-surface reconcile or stamp; the merge gate's spec-surface check exited 2. The three governing Specs
    are reconciled and stamped.
  - B2: `package_recipe_fields`' first-anchor fallback gave text and the archived flag to packages attribution does
    not list, which legacy never does. 114 of 938 scored packages and 1,124 of 9,323 rows came only through it, and
    one archived flag depended on sort order (nose-parameterized). The node now reads attribution only
    (`unattributed=False`). The parity check builds legacy's store independently, and it now matches all 828
    archived packages.
  - S1: nine legacy-divergent ports passed the tests. The edge cases are now tests: an upload of 0, one older than
    five years, a future one, fractional days, a keyword-only overlap, a floor read on the score, an exact 0.10, a
    missing status, a rounded tie, and rounded components.
  - S2: a live package can be scored as archived (duckdb, grpcio). This is recorded as residual risk and
    DW-atlas-37-7-3.
  - S3: the board model needed the stage inputs even with the flag off. A store in the earlier shape reads its own
    `adoption_stage` again.
  - Nits:
    - the module docstring's recency wording is fixed;
    - a summary that is neither text nor a list is stringified, as legacy's `_str` does;
    - the archived counts use one basis, packages on the channel through attribution;
    - Verification names the about-text tests' file;
    - `test-architecture.md` is regenerated.
- 2026-10-23: drafted from Story 37.7 and DW-atlas-37-7-1.

## Review Triage Log

- 2026-10-23, review 1 (independent subagent, read the diff against this spec): FAIL, with 2 blockers, 3 should-fixes
  and 5 nits, all addressed (Spec Change Log).
  - Under the port's own mapping, it found the scorer faithful: legacy `find_alternatives` matched 1,024 of 1,024
    lists, and 3,000 random universes gave no difference from legacy.
  - It reproduced the run's counts, timings and Parquet size.
  - It wrote nothing outside its own scratch directory, and it removed that directory.
