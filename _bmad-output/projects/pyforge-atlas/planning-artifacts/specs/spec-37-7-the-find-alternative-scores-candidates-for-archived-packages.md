---
title: "37.7: The find-alternative scores candidates for archived packages"
type: 'feature'
created: '2026-10-23'
status: 'done'
baseline_revision: 'e5810642d17ebee7159c3e020235d98918386e55'
flag:
  key: pyforge.atlas.board_projections            # existing; minted by Story 37.4, extended to this board
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through src/platform/config/flag-overlays.json
  scope: global                                   # v1 is global only
  fallback: 'the find-alternative reads primary/alternative_candidates as before, which nothing writes, and renders empty'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 3
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
   - the summary, the keywords, the recipe maintainers and the cf-graph flag reach a package only through
     `core_feedstock_attribution`, as legacy's Phase E and E.5 reach it through Phase B.5.
     `package_recipe_fields(..., unattributed=False)` drops its first-anchor fallback here, so a package
     attribution does not list gets nothing, and another feedstock that lists the same output adds nothing;
   - each candidate is a package in `semantic_packages` that is `active`, not archived, and not the package itself;
   - the score is keyword Jaccard ×3 + summary-term Jaccard ×2 + shared-dependent Jaccard ×4 + shared-maintainer
     Jaccard ×1. Dependents come from `core_dependencies`; maintainers are the attributed feedstock's
     `extra.recipe-maintainers` from the cf-graph, case kept. A candidate with no keyword or summary-term overlap is
     skipped, and so is one that scores under 0.10;
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
  `total_versions` are NULL; Story 37.6 sources the times, and DW-atlas-37-6-2 wires them in). Until then:
  - recency is 1.0 for every candidate, as legacy gives a package with no upload time;
  - `adoption_stage` reads `unknown`, as the adoption-stage board does today.
- Ties in the composite fall to the candidate name; legacy's order among ties is SQLite's row order.
- A malformed `extra.recipe-maintainers` is read as the cf-graph parse already reads it (Story 34.7's
  `_maintainers`), not as legacy's Phase E does:
  - a string is one handle (legacy splits it into characters);
  - a non-string entry becomes its string (legacy skips it);
  - an empty entry is dropped (legacy keeps it);
  - a mapping gives none (legacy takes its keys).

  On the live data this changes no list.

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
  neither. `package_recipe_fields(..., unattributed=False)`, as the node calls it, gives them to every attributed
  output whose feedstock the cf-graph carries, and to no unattributed one. An output attributed to a feedstock the
  cf-graph lacks, such as `staged-recipes`, gets nothing, as in legacy. Its default callers keep the first-anchor
  fallback.
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
- A live package can be scored as archived when Phase B.5 attributes it to an archived feedstock and a live one also
  lists it. On the live data, 60 scored packages are outputs of a live feedstock as well:
  - 44 are attributed to an archived feedstock named after them (duckdb, grpcio);
  - 16 are attributed to an archived feedstock that is not named after them, through the first-entry fallback or a
    registry that never lists the live feedstock. libgcc and libstdcxx go to m2w64-gcc-libs, and the
    apache-airflow-core family to apache-airflow-core-split.

  Legacy's attribution does the same, and the fix belongs in core's attribution, so it is DW-atlas-37-7-3's.
- Until `semantic_packages` carries upload times (DW-atlas-37-6-2), recency does not separate a stale candidate from
  a fresh one.

## I/O & Edge-Case Matrix

| Input | Result |
|-------|--------|
| archived package with no summary, keywords or overlap | no rows |
| candidate sharing only a dependent | not scored (legacy needs a keyword or term overlap) |
| candidate with no downloads | composite halved |
| candidate archived by the cf-graph only | never a candidate |
| package no attribution row lists | no text, no flag: never scored, never a candidate |
| an output a second, live feedstock also lists | maintainers from the attributed feedstock only |
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
after review 2's fixes.

- **AC1–AC6, tests:** `test_alternatives.py` (34), `test_board_models.py` and `test_board_projections.py` pass;
  `pyforge-atlas-test` gives 3,270 passed and 20 skipped, then 103 passed (exit 0).
- **Pins moved:** `derived_artifacts` has 13 nodes (12), the combined DAG 72 (71), the catalog 143 entries (142); the
  node has a timeout (900 s).
- **Mutations**, each restored, each failing a named test (40 of 40):
  - score: a keyword weight changed; the 0.10 floor removed, made inclusive, or applied to the composite; recency
    ignored, unclamped, over a 365.25-day year or in whole days; an upload of 0 read as a time; the download factor
    ignored; the composite not rounded before ranking; the component scores unrounded;
  - tokenizer and keywords: stopwords kept; short words kept; keywords not lowercased; a string or any other
    iterable read as keywords;
  - archived set and candidates: the cf-graph flag ignored; `semantic_packages`' flag ignored; the first-anchor
    fallback kept; inactive, archived or status-less candidates kept; candidates without an overlap scored; a
    keyword-only overlap dropped; a package's dependencies read as its dependents;
  - maintainers: ignored; read from every feedstock that lists the output; their handles lowercased;
  - rank and output: the limit ignored; ties not broken by name; the stage inputs dropped; the empty frame untyped;
  - about text: the summary not read, not joined from a list, or not stringified; a kept copy's keywords not read
    back as lists;
  - board: the board path not switched; the stage not the shared classifier; a store in the earlier shape not read.
- **Real data:** a fresh public parse of the cf-graph (359,499 rows, 33,527 anchor rows, in 31 s), with Story 37.2's
  live data root for `semantic_packages`, `core_dependencies` and the attribution:
  - 32,791 anchor rows carry a summary and 1 carries keywords. Conda-forge recipes almost never set
    `about.keywords`, so the summary terms carry the text score, as they do for legacy;
  - 828 packages on the channel are attributed to an archived feedstock (`semantic_packages` flags none,
    DW-atlas-37-7-2). 824 get candidates;
  - the node runs in 3.8 s and writes 8,199 rows (a median of 10 per package) over 4,580 distinct
    candidates, 339 KB of Parquet;
  - **legacy parity:** the comparison builds legacy's store on its own, from the attribution, the cf-graph anchors and
    `semantic_packages`: Phase B.5, then E and E.5 for text, flag and `package_maintainers`. It does not reuse the
    port's mapping or a maintainer table. Legacy `find_alternatives` then runs for every archived package with no
    limit, re-ranked by score and then name, top 10. All 828 lists match the port exactly: names,
    composite, the four components and downloads;
  - 60 scored packages are also outputs of a live feedstock (DW-atlas-37-7-3); none scored is off the channel or
    unarchived.

## Spec Change Log

- 2026-10-23, review 2 (FAIL, 1 blocker), fixed on the same branch:
  - R2-B1: maintainers still reached a package outside its attribution. `vcs_package_maintainers` merges every
    feedstock that lists an output, so 135 to 137 of 828 lists differed from legacy's Phase E (by round 3's and
    round 2's harnesses). The parity script hid it by
    filling legacy's `package_maintainers` from that same table. Now:
    - the node reads the attributed feedstock's recipe maintainers through the same attribution-only call, and its
      `vcs_package_maintainers` input is gone;
    - the parity store builds `package_maintainers` from the attribution;
    - a test pins an output that a second, live feedstock also lists.
  - R2-S1: DW-atlas-37-7-3 and the residual risk named one attribution path; 16 of the 60 packages come through the
    other one (libgcc and libstdcxx go to m2w64-gcc-libs). Both paths are now named.
  - Nits:
    - the keyword parse reads only a list, a tuple or an array (legacy reads a JSON object as no keywords), and
      maintainer handles get the same parse;
    - AC1 names the `unattributed=False` flag;
    - round 1's row count is restated as the net change.
  - Not changed: `_typed` and `_num` assume the epoch-second Int64 inputs `semantic_packages` declares (the atlas
    naming rule). DW-atlas-37-6-2, which wires those columns, owns their types. `_as_bool` reads only bool and
    Int64 flags.
- 2026-10-23, independent review (FAIL, 2 blockers), fixed on the same branch:
  - B1: no spec-surface reconcile or stamp; the merge gate's spec-surface check exited 2. The three governing Specs
    are reconciled and stamped.
  - B2: `package_recipe_fields`' first-anchor fallback gave text and the archived flag to packages attribution does
    not list, which legacy never does. 114 of 938 scored packages came only through it; the output fell from 9,323
    rows to 8,199. One archived flag depended on sort order (nose-parameterized). The node now reads text and flag
    through attribution only (`unattributed=False`).
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

- 2026-10-23, review 3 (independent subagent, focused on round 2's fixes): PASS, with 0 blockers, 0 should-fixes and
  4 nits, all addressed.
  - Its own legacy store, written independently, matches the port on 828 of 828 archived packages.
  - The same harness catches each of these bugs: merged maintainers (135 lists differ), lowercased handles (7) and
    the first-anchor fallback (150).
  - 2,500 randomized universes, with legacy built from raw payloads, give 0 differences.
  - Every Run-results number reproduces, and the merge-gate checks exit 0.
  - The nits:
    - the malformed-maintainers deviation is declared;
    - AC1 names outputs whose feedstock the cf-graph lacks;
    - the array branch of the list parse has a test;
    - the round-2 count is restated as a range.
  - It removed its scratch directory and wrote nothing tracked.
- 2026-10-23, review 2 (independent subagent): FAIL, with 1 blocker, 1 should-fix and 6 nits, all addressed or
  answered (Spec Change Log). It confirmed round 1's fixes:
  - spec-surface exits 0;
  - the default `package_recipe_fields` output equals `origin/main`'s on the real data;
  - 17 of its own mutations were killed;
  - the planning detectors and the full suite are green.

  With maintainers taken through attribution, it measured 828 of 828 lists matching legacy before the fix landed.
  It removed its scratch directory and the `.pyc` files its runs wrote.
- 2026-10-23, review 1 (independent subagent, read the diff against this spec): FAIL, with 2 blockers, 3 should-fixes
  and 5 nits, all addressed (Spec Change Log).
  - Under the port's own mapping, it found the scorer faithful: legacy `find_alternatives` matched 1,024 of 1,024
    lists, and 3,000 random universes gave no difference from legacy.
  - It reproduced the run's counts, timings and Parquet size.
  - It wrote nothing outside its own scratch directory, and it removed that directory.
