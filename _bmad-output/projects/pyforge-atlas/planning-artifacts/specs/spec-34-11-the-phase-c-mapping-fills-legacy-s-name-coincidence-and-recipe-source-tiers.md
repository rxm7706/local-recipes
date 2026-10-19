---
title: "34.11: The Phase C mapping fills legacy's name-coincidence and recipe-source tiers"
type: 'feature'
created: '2026-10-18'
status: 'done'
baseline_revision: '2282c7bbf9'
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/live-sources.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-34-2-the-phase-c-mapping-fills-from-the-conda-forge-bot-s-name-mapping.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-34-3-dependencies-feedstock-health-and-maintainers-read-the-bot-s-split-graph-repos.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/core_sources.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/pypi_intelligence/nodes.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/core/nodes.py
deferred: []
declared_low_risk: false
review_loop_iteration: 2
followup_review_recommended: false
---

<intent-contract>

## Intent

**Problem:** the atlas maps half the PyPI projects legacy maps, so Phase H, the vdb scan and everything keyed on a
PyPI name cover half of legacy's universe (`DW-atlas-34-10-1`).

- `map_pypi_conda` maps only the bot's parselmouth names: 10,967 rows on 2026-10-18.
- Legacy's Phase H universe is 20,938 distinct names (`v_actionable_packages`). After parselmouth (Phase C),
  legacy fills two more tiers, each only where a conda package has no PyPI name yet:
  1. **Name coincidence.** Phase D (`_phase_d_update_working_set`, CFA:1837-1895): a PyPI project whose
     lower-cased name equals the conda name. Legacy checks the PyPI side first: a project already mapped to
     another conda package never matches by name. pandas, requests, scipy, django, flask, pillow, tensorflow
     and cryptography come from this tier, because the bot's mapping omits them.
  2. **Recipe source URL.** Phase C.5, folded into Phase E (CFA:2434-2446): every output Phase B.5 attributes
     to a feedstock whose recipe's `source.url` downloads from PyPI
     (`(pypi.io|pypi.org)/packages/source/<l>/<name>/`, CFA:2050). Its `COALESCE` keeps a name coincidence's
     name and relabels it `recipe_source_url`; a parselmouth row is never touched.
- Legacy's Phase B resets `match_source` to 'none' on every run but never clears `pypi_name` (CFA:1482). So 9,949
  of legacy's names read 'none' today.
- Atlas's `match_source_urls` reads `pypi_json_raw`, the projects already fetched, so it cannot add a project the
  mapping missed.
- **Found by Story 34.7's live run:** with the PyPI name missing, the vdb scan queries conda purls only, which match
  almost nothing. `django` alone returns 229 vulnerabilities as `pkg:pypi/django`.

**Approach:**
1. **The cf-graph frame carries each output's recipe `source_url`** on its anchor row (Story 34.3's frame; edge
   rows and bot-only rows are null). It is the first source that has a URL.
   - Deviation: legacy takes the first source even when it has none, so a leading `path:` or `git_url:` source hides
     the URL.
2. **`map_pypi_conda` fills the tiers in legacy's phase order,** only for enumerated conda packages:
   - parselmouth, as before;
   - then `name_coincidence`, from `pypi_universe` (Phase D's output; lower-cased on both sides, as legacy), for a
     package with no PyPI name yet and a project no row names yet (PEP 503, one package per project);
   - then `recipe_source_url`: every package `core_feedstock_attribution` puts in a feedstock whose recipe names a
     PyPI sdist, or, for a package attribution has no row for, its first anchor whose URL names a PyPI project. A
     coincidence keeps its name and takes this label (legacy's `COALESCE`); a parselmouth row is untouched.
   It takes `core_cf_graph_raw`, `pypi_universe` and `core_feedstock_attribution` as inputs, so Kedro runs it
   after Phases B.5 and D.
   - Deviation: the recipe-source pattern also reads `files.pythonhosted.org/packages/source/<l>/<name>/`. Legacy
     counts that host as PyPI (`_SRC_REGEX_PATTERNS`), but its name pattern omits it. In the shipped code the host adds
     194 rows (35 names) and relabels 518 coincidences `recipe_source_url`, which ranks them above a plain
     coincidence in the flat export and protects them from `match_source_urls` (review round 2, 2026-10-18).
   - Deviation: the anchor fallback. Legacy maps only the packages Phase B.5 attributes (CFA:2283); here a package
     attribution has no row for takes its first anchor whose URL names a PyPI project. Live it adds 26 rows and
     relabels 46 coincidences.
   - Deviation: the PyPI-side check compares PEP 503 names, and counts every parselmouth name, an unenumerated
     package's included; legacy compares lower-cased names of rows in its `packages` table. Both are stricter, and
     neither changed a row live (10,027 coincidences either way).
3. **One cf-graph fetch per session (healed tissue).** `CfGraphTarballDataset.load()` fetched all four bot
   tarballs on every load, and three nodes already loaded it per run; this story adds a fourth. The instance now
   keeps its frame for an hour and hands each node a shallow copy, so a node that assigns a column never reaches
   the next, and a host that keeps the instance across runs never serves an older graph.

Ledger key: `34-11-the-phase-c-mapping-fills-legacy-s-name-coincidence-and-recipe-source-tiers`.
Type / Effort / Deps: feature / M / Story 34.2 (parselmouth), Story 34.3 (node_attrs).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-64** (`live-sources.md`, the Phase C row): this story completes the mapping the fetches
  key on. It is not flag-gated itself: the mapping is pure, and the node_attrs and simple-index fetches it reads are
  already behind `pyforge.atlas.live_public_sources`.
- **AD-3** (cross-pipeline inputs by catalog name), **AD-13**, **AD-14** (no new parity surface; `pypi_conda_mapping`
  was already parity-scoped).
- **Origin.** `DW-atlas-34-10-1` (Story 34.10's live parity, corrected by its independent review round 1); Dream
  entry 2026-10-18 (atlas fills its own data), R3.

## Acceptance Criteria

- **AC1 — Tier order.**
  - Parselmouth wins: its rows are never relabelled, and its packages and projects never take a coincidence.
  - Name coincidence fills next, lower-cased on both sides, one package per PyPI project (PEP 503).
  - The recipe source URL fills last, for every output attributed to the feedstock (the first anchor whose URL
    names a PyPI project, where attribution has no row; a package attributed to a non-PyPI feedstock stays
    unmapped by this tier); a coincidence keeps its name and takes the `recipe_source_url` label.
  - Only an enumerated conda package is mapped.
- **AC2 — The source URL.**
  - It is the first source that has a URL, a list of URLs giving its first.
  - It sits on anchor rows only.
  - A frame of bot records alone still has the column.
- **AC3 — The pattern.**
  - `pypi.io`, `pypi.org` and `files.pythonhosted.org` `/packages/source/<l>/<name>/` URLs give the lower-cased name.
  - A hashed `files.pythonhosted.org` path, a GitHub URL, or a non-string gives none.
- **AC4 — Degradation.** Without the new inputs (absent, empty, or lacking their columns) the mapping is parselmouth
  alone. With no parselmouth mapping, the other tiers still fill.
- **AC5 — One fetch per session.** A second load within the hour does not fetch, with or without a `filepath`; a
  load past it does; a column one node adds never reaches the next.
- **AC6 — Live.** See Verification. Tolerance, against legacy Phase H's universe the same day (PEP 503 keys): the
  mapping's PyPI names cover at least 99% of legacy's, and where both map a conda package, at least 99% agree
  (legacy's name is among the package's atlas names).
- **AC7 — Gates.** `pyforge-atlas-test`, `kedro-test`, `kedro-catalog-check`, the coverage gate, `lint-types` (and
  mypy in `pyforge-foundry-full`); governing Specs reconciled and stamped scoped.

## Verification

- Unit, from the repo root: `src/shared/packages/pyforge-atlas/tests/unit/pipelines/pypi_intelligence/test_mapping_tiers.py`.
- **Live, recorded 2026-10-18.**
  - **Setup:** a scratch copy of the 2026-10-17 data root (its `pypi_universe` from Story 34.6's run), flag on (dev),
    `--pipelines pypi_intelligence --nodes map_pypi_conda,match_source_urls`, with a fresh node_attrs fetch.
  - **First run:** exit 0, 37 s, peak RSS 1.29 GB. `pypi_conda_mapping` went from 10,967 to 22,098 rows (21,292
    PyPI names under PEP 503). Before the coincidence tier was added, the recipe tier alone, with legacy's pattern,
    matched 6,676.
  - **After review round 1,** on a copy of the reviewer's root: exit 0, 32.7 s, peak RSS 1.28 GB.
    - `pypi_conda_mapping`: 22,328 rows, 21,293 PyPI names under PEP 503.
      - parselmouth 10,966;
      - `recipe_source_url` 7,701 (relabelled coincidences included);
      - `name_coincidence` 3,661.
    - **Against legacy `cf_atlas.db`:**
      - Legacy's 20,938 names: 20,923 are mapped here (99.93%), 15 are not.
      - Atlas maps 370 names legacy does not.
      - Of the 21,838 conda packages both map, 21,828 agree (99.95%).
    - None of the twelve native packages the review found mapped to an unrelated PyPI project (GNU flex, blis,
      glpk, glfw, bullet3, crlibm, cityhash, c-blosc, libgeotiff, docker, couchdb, bash-completion) is mapped.
    - Every `airflow-with-*` output maps to `apache-airflow`, and `black`, `altair`, `bleach` and `arviz` export to
      their own package.
  - **Flagship projects** missing before are now mapped: pandas, requests, scipy, django, flask, pillow, tensorflow,
    cryptography.

## Boundaries & Constraints

**Never:** a network call in the mapping node; a new parity surface; a clobbered parselmouth row.

**Residual risk:**
- **Name coincidence is a likely match, not a verified one** (legacy calls it `likely`). A conda package can share
  its name with an unrelated PyPI project. Parselmouth always wins where it names one.
- **The cf-graph frame is shared for an hour.** A consumer that mutates values in place, rather than assigning
  columns, could still reach the next node. None does today. A run longer than the hour fetches the graph again.
- **244 relabelled coincidences name a different project from their recipe** (PEP 503; 266 compared lower-cased;
  aiida/aiida-core, airflow/apache-airflow, bs4/beautifulsoup4 …). As legacy, the coincidence keeps its name under
  the `recipe_source_url` label.
- **A degraded cf-graph load is reused for the hour** (stale last-good or empty), so a run sees one graph
  throughout; a fetch that recovers mid-hour waits for the window.
- **Dagster runs each op in its own process,** so the memo saves nothing there: each of the four ops fetches the
  graph, and `map_pypi_conda`'s budget is now 600 s.
- **Legacy's 15 remaining names** are stale `pypi_name` values from earlier legacy runs that no current tier
  reproduces.

## I/O & Edge-Case Matrix

| Situation | Before | After |
|---|---|---|
| A conda package parselmouth names | parselmouth | unchanged |
| An unmapped package whose name is a PyPI project | unmapped | `name_coincidence` |
| An unmapped output of a feedstock built from a PyPI sdist | unmapped | `recipe_source_url`, the sdist's project |
| A recipe sourced from GitHub | unmapped | unmapped (unless its name coincides) |
| A native package whose name is a PyPI project parselmouth maps elsewhere (GNU flex) | unmapped | unmapped |
| A coincidence whose own recipe downloads a PyPI sdist | unmapped | its name, `recipe_source_url` |
| An output attributed to a feedstock but not one of its anchors (`airflow-with-amazon`) | unmapped | the feedstock's project |
| `core_cf_graph_raw` loaded by four nodes in one Kedro run | four full fetches | one fetch |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-64 (FR-72), a feature.
- Origin: `DW-atlas-34-10-1`; Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-18 (atlas fills its
  own data).
- Epic 34 / Story 34.11 in `planning-artifacts/epics.md`.

## Spec Change Log

- 2026-10-18: minted and written with the implementation (branch `atlas-34-11-recipe-source-pypi`, cut from `main`
  at `2282c7bbf9`).
  - The live run first measured the recipe-source tier alone, which matched 6,676 and left 4,233 legacy names
    unmapped. That pointed to legacy's name-coincidence tier, which closes all but 15.
- 2026-10-18: independent review round 1 FAIL. 2 blockers, 3 should-fix items, 9 nits; 36 mutants, 11 survived.
  - **B1:** the coincidence tier now checks the PyPI side first, as legacy's Phase D does. 78 native packages lost an
    unrelated PyPI name.
  - **B2:** the branch merged `main`, which carries the 34.9 ledger row the shared feed had promoted.
  - **S1:** a coincidence whose recipe names a PyPI sdist takes the `recipe_source_url` label (legacy's
    `COALESCE`), so the flat export ranks it above a sub-output.
  - **S2:** the recipe tier reads `core_feedstock_attribution` (legacy's Phase B.5) and falls back to anchors. It
    recovers the `airflow-with-*` outputs and the multi-feedstock names.
  - **S3:** tests pin parselmouth's package and project, one coincidence per project, attribution over anchors, a
    null-URL first anchor, the catalog form's one fetch, and the memo window.
  - **Nits:**
    - The figures are restated (parselmouth count, the files.pythonhosted.org rows, the agreement method).
    - The comment was moved and the parity harness names the five inputs.
    - A frame without `source_url` logs a warning.
    - The memo lasts an hour; the node's budget is 600 s.
    - `DW-atlas-34-10-1` closes here, after Story 34.10 lands.
- 2026-10-18: independent review round 2 FAIL. 1 blocker (planning), 2 should-fix items, nits; 28 mutants, 7 survived
  (3 targeted). The code findings of round 1 were confirmed fixed, and the live figures reproduced.
  - **B1:** `DW-atlas-34-10-1`'s `verified:` line now cites the code, the tests and the command with its exit code.
  - **S1:** a test pins a package attributed to a GitHub-sourced feedstock and anchored in a PyPI-sourced one: it
    stays unmapped by the recipe tier.
  - **S2:** the anchor fallback, the files.pythonhosted.org effect (194 rows, 35 names, 518 relabels) and the
    PyPI-side check's breadth are recorded as deviations; the fallback's wording is corrected.
  - **Nits:** tests pin the PEP 503 check, the unenumerated parselmouth name, and the one-hour window; the 292 is
    restated as 244; a degraded load reused for the hour is a residual risk; Story 36.1's Flag line names both flags.
- 2026-10-18: independent review round 3 PASS (R2, R6, R12, R25 killed; planning detectors green). Promoted to done.
