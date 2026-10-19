---
title: "34.11: The Phase C mapping fills legacy's name-coincidence and recipe-source tiers"
type: 'feature'
created: '2026-10-18'
status: 'in-review'
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
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the atlas maps half the PyPI projects legacy maps, so Phase H, the vdb scan and everything keyed on a
PyPI name cover half of legacy's universe (`DW-atlas-34-10-1`).

- `map_pypi_conda` maps only the bot's parselmouth names: 10,967 rows on 2026-10-18.
- Legacy's Phase H universe is 20,938 distinct names (`v_actionable_packages`). After parselmouth (Phase C),
  legacy fills two more tiers, each only where a conda package has no PyPI name yet:
  1. **Name coincidence.** Phase D (`_phase_d_update_working_set`, CFA:1835-1890): a PyPI project whose
     lower-cased name equals the conda name. pandas, requests, scipy, django, flask, pillow, tensorflow and
     cryptography come from this tier, because the bot's mapping omits them.
  2. **Recipe source URL.** Phase C.5, folded into Phase E (CFA:2434-2446): every output of a feedstock whose
     recipe's `source.url` downloads from PyPI (`(pypi.io|pypi.org)/packages/source/<l>/<name>/`, CFA:2050).
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
2. **`map_pypi_conda` fills the tiers in legacy's phase order,** each only for an enumerated conda package the
   tier before left unmapped:
   - parselmouth, as before;
   - then `name_coincidence`, from `pypi_universe` (Phase D's output; lower-cased on both sides, as legacy);
   - then `recipe_source_url`, from the frame.
   It takes `core_cf_graph_raw` and `pypi_universe` as inputs, so Kedro runs it after Phase D.
   - Deviation: the recipe-source pattern also reads `files.pythonhosted.org/packages/source/<l>/<name>/`. Legacy
     counts that host as PyPI (`_SRC_REGEX_PATTERNS`), but its name pattern omits it, which drops 677 recipes
     (measured 2026-10-18).
3. **One cf-graph fetch per session (healed tissue).** `CfGraphTarballDataset.load()` fetched all four bot
   tarballs on every load, and three nodes already loaded it per run; this story adds a fourth. The instance now
   keeps its frame for the session and hands each node a shallow copy, so a node that assigns a column never
   reaches the next.

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
  - Parselmouth wins.
  - Name coincidence fills next, lower-cased on both sides.
  - The recipe source URL fills last, for every output of the feedstock.
  - Each tier fills only a package the one before left unmapped, and only an enumerated conda package.
- **AC2 — The source URL.**
  - It is the first source that has a URL, a list of URLs giving its first.
  - It sits on anchor rows only.
  - A frame of bot records alone still has the column.
- **AC3 — The pattern.**
  - `pypi.io`, `pypi.org` and `files.pythonhosted.org` `/packages/source/<l>/<name>/` URLs give the lower-cased name.
  - A hashed `files.pythonhosted.org` path, a GitHub URL, or a non-string gives none.
- **AC4 — Degradation.** Without the new inputs (absent, empty, or lacking their columns) the mapping is parselmouth
  alone. With no parselmouth mapping, the other tiers still fill.
- **AC5 — One fetch per session.** A second load does not fetch, and a column one node adds never reaches the next.
- **AC6 — Live.** See Verification. Tolerance, against legacy Phase H's universe the same day (PEP 503 keys): the
  mapping's PyPI names cover at least 99% of legacy's, and where both map a conda package, at least 99% agree.
- **AC7 — Gates.** `pyforge-atlas-test`, `kedro-test`, `kedro-catalog-check`, the coverage gate, `lint-types` (and
  mypy in `pyforge-foundry-full`); governing Specs reconciled and stamped scoped.

## Verification

- Unit, from the repo root: `src/shared/packages/pyforge-atlas/tests/unit/pipelines/pypi_intelligence/test_mapping_tiers.py`.
- **Live, recorded 2026-10-18.**
  - **Setup:** a scratch copy of the 2026-10-17 data root (its `pypi_universe` from Story 34.6's run), flag on (dev),
    `--pipelines pypi_intelligence --nodes map_pypi_conda,match_source_urls`, with a fresh node_attrs fetch.
  - **Run:** exit 0, 37 s, peak RSS 1.29 GB.
  - **`pypi_conda_mapping`:** 10,967 → 22,098 rows (21,292 PyPI names under PEP 503).
    - parselmouth 10,967;
    - `name_coincidence` 10,104;
    - `recipe_source_url` 1,027.
    - Before the coincidence tier was added, the recipe tier alone matched 6,676.
  - **Against legacy `cf_atlas.db`:**
    - Legacy's 20,938 names: 20,923 are mapped here (99.93%), 15 are not.
    - Atlas maps 369 names legacy does not.
    - Of the 21,583 conda packages both map, 21,568 map to the same name (99.93%).
  - **Flagship projects** missing before are now mapped: pandas, requests, scipy, django, flask, pillow, tensorflow,
    cryptography.

## Boundaries & Constraints

**Never:** a network call in the mapping node; a new parity surface; a clobbered parselmouth row.

**Residual risk:**
- **Name coincidence is a likely match, not a verified one** (legacy calls it `likely`). A conda package can share
  its name with an unrelated PyPI project. Parselmouth always wins where it names one.
- **The cf-graph frame is shared for the session.** A consumer that mutates values in place, rather than assigning
  columns, could still reach the next node. None does today.
- **Legacy's 15 remaining names** are stale `pypi_name` values from earlier legacy runs that no current tier
  reproduces.

## I/O & Edge-Case Matrix

| Situation | Before | After |
|---|---|---|
| A conda package parselmouth names | parselmouth | unchanged |
| An unmapped package whose name is a PyPI project | unmapped | `name_coincidence` |
| An unmapped output of a feedstock built from a PyPI sdist | unmapped | `recipe_source_url`, the sdist's project |
| A recipe sourced from GitHub | unmapped | unmapped (unless its name coincides) |
| `core_cf_graph_raw` loaded by four nodes in one run | four full fetches | one fetch |

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
