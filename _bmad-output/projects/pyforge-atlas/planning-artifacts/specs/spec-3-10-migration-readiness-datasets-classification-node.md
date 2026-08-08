---
title: 'Story B10 (3.10): Migration-readiness datasets + classification node'
type: 'feature'
status: shipped
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #83 body + main commit log; dev narrative recovered, review-triage partial)'
---

> **Contract-spec — no original ever existed (corrected 2026-07-25).** This story
> (wave B9–H4) was built by the atlas migration's **in-session agent loop**, which —
> unlike `bmad-create-story` (used only for waves 0/A/B1–B8) — never emitted a per-story
> spec file. The atlas migration session (`01FYyQvBJuXwySiaMUUYCqBZ`) confirmed this
> exhaustively: no such file exists in `implementation-artifacts/`, `.bmad-loop/runs/`
> (which never existed for atlas), any git worktree, git history, or anywhere on disk.
> **Nothing was lost — there is no original to recover.** This file carries the
> load-bearing contract (Intent + Acceptance Criteria **verbatim** from the tracked
> `planning-artifacts/epics.md`) plus a dev narrative reconstructed from the merged record
> (the "Dev narrative" section below). A fuller BMAD-story-format reconstruction (Dev
> Agent Record + File List + Review Triage Log, built from the agent-loop transcripts) is
> at `../../spec-archive/retro-story-files/3-10-b10.md` — the operator's web-session archive.

## Contract (from epics.md — verbatim, authoritative)

### Story B10 (3.10): Migration-readiness datasets + classification node

As the operator,
I want conda-forge-bot-data `status/` category lists and per-migration detail ingested with a readiness-classification node,
So that migration readiness (e.g. python314) is a queryable four-way split with blocker labels and volume ranking.

**Acceptance Criteria:** (spec § 9 Story B10, binding)

**Given** the `status/` category lists and `migration_json/<name>.json` detail
**When** the datasets + classification node land
**Then** the category-list datasets enumerate active migrations and drive per-migration partitioning — a new migration upstream requires zero code change
**And** for a live migration the classification node produces the four-way readiness split (noarch / rebuild-done / confirmed-pending / not-in-tracker) with the per-feedstock blocker buckets (`in-pr`, `awaiting-pr`, `awaiting-parents`, `not-solvable`, `bot-error`)
**And** the `not-in-tracker` bucket is labeled as inferred, never confirmed tracker status (fixture-proven in the report output)
**And** the downloads join yields a top-unmigrated-by-volume ranking
**And** all fetches route through the existing `resolve_github_raw_urls` (no new override helper); offline the nodes skip gracefully and mark the datasets stale (`version_status.v2.json` excluded).

- **FRs:** FR-21.
- **Invariants:** AD-13, AD-14 (not parity-gated), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (zero-code-change partitioning fixture + inferred-label fixture).
- **Depends on:** B1 (feedstock set + `conda_noarch`), B2 (downloads join); NOT gated on B4 parity.

## Tasks / Subtasks

*(Derived from the ACs — no original task breakdown was authored for this loop-run story.)*

- [x] the category-list datasets enumerate active migrations and drive per-migration partitioning — a new migration upstream requires zero code change
- [x] for a live migration the classification node produces the four-way readiness split (noarch / rebuild-done / confirmed-pending / not-in-tracker) with the per-feedstock blocker buckets (`in-pr`, `awaiting-pr`, `awaiting-parents`, `not-solvable`, `bot-error`)
- [x] the `not-in-tracker` bucket is labeled as inferred, never confirmed tracker status (fixture-proven in the report output)
- [x] the downloads join yields a top-unmigrated-by-volume ranking
- [x] all fetches route through the existing `resolve_github_raw_urls` (no new override helper); offline the nodes skip gracefully and mark the datasets stale (`version_status.v2.json` excluded).

## Dev Notes

**Planning metadata (from `epics.md`):**

- **FRs:** FR-21.
- **Invariants:** AD-13, AD-14 (not parity-gated), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (zero-code-change partitioning fixture + inferred-label fixture).
- **Depends on:** B1 (feedstock set + `conda_noarch`), B2 (downloads join); NOT gated on B4 parity.

### Implementation notes

<!-- DERIVED 2026-07-27 by reading the shipped code (PR #83). No original dev-session
     notes existed for this story; this is what the merged implementation actually does. -->

**What was added.** Two source-dataset classes in `datasets/migration_status.py`
(`MigrationCategoryDataset`, `MigrationDetailDataset`) plus the
`classify_migration_readiness` node in `pipelines/vcs_health/nodes.py`. The data behind
`conda-forge.org/status/#migrations` — the `conda-forge/conda-forge-bot-data` repo's
`status/` tree.

**Zero-code-change generalization is the design goal.** Category lists (`regular`,
`longterm` = the ACTIVE set; `closed`, `paused`, `total`) enumerate which migrations
exist, and `migration_names()` derives partition keys from that payload as a **pure
function with no IO**. A new upstream migration therefore flows straight to a new
partition — "python314 today, python315 tomorrow" — without touching this code. That is
why readiness is driven by the category lists rather than by a hardcoded migration list.

**`version_status.v2.json` is excluded on purpose, and the exclusion is guarded.** The bot's
version-update queue is *not* a source: the atlas measures version currency itself via
Phases H/K (`behind-upstream`) and does not mirror the bot's view of the same signal.
`EXCLUDED_STATUS_FILES` is the guard a fetch can never route through, `migration_names()`
defensively drops it even if it appears in a payload, and
`tests/datasets/test_migration_status.py` asserts the exclusion. This is a case where the
*absence* of a source is a contract.

**The four-way split.** For each (migration, feedstock):
1. `noarch` — architecture-independent, so the migration does not apply.
2. `rebuild-done` — present in the `done` bucket.
3. `confirmed-pending` — present in a pending/blocker bucket, with the specific `blocker`
   resolved by **first match in `BLOCKER_BUCKETS` precedence** (`in-pr` wins over
   `awaiting-*`, then the two error buckets) since a feedstock can appear in more than one.
4. `not-in-tracker` — absent from every bucket.

**`not-in-tracker` is an inference and is labeled as one.** This is the load-bearing
semantic of the story. Absence from the migration JSON does not mean the tracker confirmed
the feedstock is unmigrated — it means we did not find it. The dedicated
`not_in_tracker_inferred` boolean column carries that distinction into the data, so no
downstream surface can quietly promote an inference to a confirmed tracker status.

**IO and offline posture.** All fetches route through the **existing**
`GITHUB_RAW_BASE_URL` override point — no new `resolve_*_urls` helper was added, so
enterprise/JFrog mirror routing is inherited rather than re-implemented. IO is
dataset-owned via an **injected fetcher whose default is `None`, meaning offline**:
keep last-good and mark stale (AD-13). `MigrationDetailDataset` mirrors the
`PartitionedDataset` shape but is hand-rolled precisely because the stock one cannot
provide that offline safety.

**Not parity-gated, and the name proves it.** `vcs_migration_readiness` is aligned to B4's
fixture-enforced `EXCLUDED_NEW_SIGNAL_DATASETS` list in `parity/legacy_surface.py`. The
dataset name is load-bearing: rename it and it silently re-enters the parity gate it was
designed to sit outside (AD-14).

**Dtype discipline.** `_empty_migration_readiness()` declares explicit dtypes — object name
columns, bool `not_in_tracker_inferred`, float `downloads_total`, nullable `Int64`
`unmigrated_volume_rank` — so the empty path sinks to Parquet identically to the populated
path. Same class of fix as B9's `_empty()`.

### References

- [Source: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md#Story-B10]
- [Source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md#§9-Story-B10]
- [Architecture: _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md]

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Delivery Record

<!-- DERIVED from the merged PR via `gh` on 2026-07-27. Exact, not reconstructed. -->

| | |
|---|---|
| Pull request | **#83** — story(B10): migration-readiness datasets + classification node (FR-21) |
| Merged | 2026-07-18 |
| Diff | 10 files, +1424 / -14 |
| Test files touched | 5 |

**Commits**

- `ecc161a` story(B10): migration-readiness datasets + classification node (FR-21)
- `520a75b` story(B10): harden inferred-label test with a confirmed-pending row (…

**File list** *(exact, from the merged diff)*

```
  478 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/migration_status.py
  344 +     0 -  src/shared/packages/pyforge-atlas/tests/pipelines/vcs_health/test_migration_readiness.py
  256 +     0 -  src/shared/packages/pyforge-atlas/tests/datasets/test_migration_status.py
  220 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/vcs_health/nodes.py
   70 +     0 -  src/shared/packages/pyforge-atlas/conf/base/catalog.yml
   14 +    11 -  src/shared/packages/pyforge-atlas/tests/pipelines/test_dag_resolves.py
   19 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/__init__.py
   18 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/vcs_health/pipeline.py
    2 +     2 -  src/shared/packages/pyforge-atlas/tests/catalog/conftest.py
    3 +     1 -  src/shared/packages/pyforge-atlas/tests/parity/test_parity_complete.py
```

## Dev Agent Record

### Agent Model Used

In-session BMAD agent loop (draft → 2× adversarial review → 1× independent fresh-eyes review → real-gate verify), not a `bmad-dev-story` story-file run.

### Completion Notes List

- **Impl commit `ecc161a`** — story(B10): migration-readiness datasets + classification node (FR-21)
  - Ingests the conda-forge/conda-forge-bot-data status/ tree into vcs_health
  - (AD-3, new-signal, AD-14 not parity-gated):
  - - MigrationCategoryDataset — the status/{regular,longterm,closed,paused,
  - total}_status.json category lists; they enumerate active migrations and
  - DRIVE the partitioning, so a new migration upstream (python314 -> python315)
  - needs ZERO code change.
  - - MigrationDetailDataset — the per-migration status/migration_json/<name>.json
  - detail, PARTITIONED by active migration, carrying the per-feedstock buckets
  - (done/in-pr/awaiting-pr/awaiting-parents/not-solvable/bot-error).
  - - classify_migration_readiness — four-way split with strict precedence
  - (noarch > rebuild-done > confirmed-pending > not-in-tracker); the downloads
  - join (Phase F) yields the top-unmigrated-by-volume ranking.
  - Load-bearing semantics:
  - - not-in-tracker is an INFERENCE: the not_in_tracker_inferred bool is True for
  - exactly those rows, so a report can never present an inference as confirmed
  - tracker status (fixture-proven).
  - - NO migration name is hardcoded anywhere (iterates sorted(detail_map)).
  - - version_status.v2.json is DELIBERATELY EXCLUDED (atlas measures currency
  - itself, Phases H/K) — EXCLUDED_STATUS_FILES guards every fetch path.
  - - conda_noarch is DERIVED from the existing core subdirs column (exact 'noarch'
  - token; list/comma-string/None/ndarray safe) — the parity-gated core enumerate
  - output is NOT mutated.
  - All fetches route through the existing GITHUB_RAW_BASE_URL override (no new
  - resolve_*_urls helper); offline the datasets skip + mark stale (AD-13,
  - ExternalRefreshDataset shape). Output vcs_migration_readiness aligned to B4's
  - frozen EXCLUDED_NEW_SIGNAL_DATASETS (len stays 3).
  - 492 passed (+40 new), incl. both mandatory fixtures (zero-code-change
  - partitioning + inferred-label) and the version_status exclusion.

## Review Triage Log

Independent/Gemini review produced follow-up fix commit(s) on PR `#83`:

- `520a75b` — story(B10): harden inferred-label test with a confirmed-pending row (reviewer F1)

<!-- end retro story -->

## Dev narrative — recovered from the merged record

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #83: story(B10): migration-readiness datasets + classification node (FR-21)
