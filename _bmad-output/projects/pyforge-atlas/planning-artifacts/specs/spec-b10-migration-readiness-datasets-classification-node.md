---
title: 'Story B10 (3.10): Migration-readiness datasets + classification node'
type: 'feature'
status: 'shipped'
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

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

## Dev narrative — recovered from the merged record (2026-07-25)

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #83: story(B10): migration-readiness datasets + classification node (FR-21)

## Summary

Ingests the `conda-forge/conda-forge-bot-data` `status/` tree (the data behind conda-forge.org/status/#migrations) into the `vcs_health` pipeline as external datasets + a readiness-classification node (FR-21). New-signal, AD-14 not-parity-gated.

- **`MigrationCategoryDataset`** — the `status/{regular,longterm,closed,paused,total}_status.json` category lists. They enumerate active migrations and **drive the partitioning**, so a new migration upstream (`python314` → `python315`) needs **zero code change**.
- **`MigrationDetailDataset`** — the per-migration `status/migration_json/<name>.json` detail, **partitioned by active migration**, carrying the per-feedstock buckets (`done`, `in-pr`, `awaiting-pr`, `awaiting-parents`, `not-solvable`, `bot-error`).
- **`classify_migration_readiness`** — four-way split with strict precedence (`noarch` > `rebuild-done` > `confirmed-pending` > `not-in-tracker`); the Phase F downloads join yields the **top-unmigrated-by-volume** ranking.

## Load-bearing semantics

- **`not-in-tracker` is an INFERENCE** — the `not_in_tracker_inferred` bool is `True` for exactly those rows, so a report can never present an inference as confirmed tracker status (fixture-proven).
- **No migration name is hardcoded** anywhere — the node iterates `sorted(detail_map)`.
- **`version_status.v2.json` is deliberately EXCLUDED** (the atlas measures currency itself via Phases H/K) — `EXCLUDED_STATUS_FILES` guards every fetch path.
- **`conda_noarch` is DERIVED** from the existing core `subdirs` column (exact `noarch` token; list/comma-string/None/ndarray safe) — the parity-gated core enumerate output is **not** mutated.

## Architecture alignment

- All fetches route through the existing `GITHUB_RAW_BASE_URL` override (no new `resolve_*_urls` helper); enterprise/JFrog mirror routing inherited.
- **AD-13**: offline → datasets skip + mark stale (reuses the `ExternalRefreshDataset` atomic-write / never-clobber / never-raise shape); node returns a typed empty frame, never raises.
- **AD-14**: output `vcs_migration_readiness` aligned to B4's frozen `EXCLUDED_NEW_SIGNAL_DATASETS` (len stays 3).

## Tests

`492 passed` (+40 new), including both mandatory fixtures — zero-code-change partitioning (a new migration flows through with no edit) and the inferred-label proof — plus the `version_status.v2.json` exclusion and the offline→stale / 404-partition-isolation / corrupt-partition-skip paths.

### Commits on `main`

- `c104185554` story(B10): harden inferred-label test with a confirmed-pending row (reviewer F1)  _(review-fix)_
- `3d93a4b8a0` story(B10): migration-readiness datasets + classification node (FR-21)  _(dev-landing)_

_This PR also carried an automated Gemini review; not reproduced here per repo policy ([[feedback_no_gemini_reviews]])._

