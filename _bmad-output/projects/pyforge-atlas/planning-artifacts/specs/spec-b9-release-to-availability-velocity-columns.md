---
title: 'Story B9 (3.9): Release-to-availability velocity columns'
type: 'feature'
status: shipped
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #82 body + main commit log; dev narrative recovered, review-triage partial)'
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
> at `../../spec-archive/retro-story-files/3-9-b9.md` — the operator's web-session archive.

## Contract (from epics.md — verbatim, authoritative)

### Story B9 (3.9): Release-to-availability velocity columns

As the operator,
I want `release_lag_hours` + `release_lag_qualifies` derived on the Phase H join with the 90-day recency gate,
So that packaging velocity is measurable without the false "47% behind" failure mode.

**Acceptance Criteria:** (spec § 9 Story B9, binding)

**Given** Phase H's retained per-release `upload_time_iso_8601`
**When** the column pair is derived
**Then** it exists on the Phase H join dataset with no new external fetch introduced
**And** the rebuild-cadence guard is fixture-enforced: a version-unchanged package whose upstream release is >90 days old is excluded (`release_lag_qualifies = false`)
**And** lag is computed against first availability of the matched version (minimum per-build repodata `timestamp`), fixture-enforced: a second build of the same version inside the window does not shift `release_lag_hours`
**And** a population run reproduces the live baseline shape (median ≈ 9 h, ~72% within 24 h) within reasonable drift, recorded as a calibration reference (not a hard gate); the two coincident 83.7% measurements re-verify against the § 15 evidence gists.

- **FRs:** FR-20.
- **Invariants:** AD-14 (never `latest_conda_upload`; not parity-gated), AD-3 (lives in `vcs_health`), timestamp convention (epoch seconds at ingest — repodata ms converted at the dataset boundary).
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (both failure-mode fixtures).
- **Depends on:** B2 (Phase H dataset); NOT gated on B4 parity.

## Tasks / Subtasks

*(Derived from the ACs — no original task breakdown was authored for this loop-run story.)*

- [x] it exists on the Phase H join dataset with no new external fetch introduced
- [x] the rebuild-cadence guard is fixture-enforced: a version-unchanged package whose upstream release is >90 days old is excluded (`release_lag_qualifies = false`)
- [x] lag is computed against first availability of the matched version (minimum per-build repodata `timestamp`), fixture-enforced: a second build of the same version inside the window does not shift `release_lag_hours`
- [x] a population run reproduces the live baseline shape (median ≈ 9 h, ~72% within 24 h) within reasonable drift, recorded as a calibration reference (not a hard gate); the two coincident 83.7% measurements re-verify against the § 15 evidence gists.

## Dev Notes

**Planning metadata (from `epics.md`):**

- **FRs:** FR-20.
- **Invariants:** AD-14 (never `latest_conda_upload`; not parity-gated), AD-3 (lives in `vcs_health`), timestamp convention (epoch seconds at ingest — repodata ms converted at the dataset boundary).
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (both failure-mode fixtures).
- **Depends on:** B2 (Phase H dataset); NOT gated on B4 parity.

### Implementation notes

<!-- DERIVED 2026-07-27 by reading the shipped code (PR #82). No original dev-session
     notes existed for this story; this is what the merged implementation actually does. -->

**The node and where it lives.** `derive_release_velocity` in
`pipelines/vcs_health/nodes.py`. It sits in `vcs_health` but **reads
`pypi_current_versions`, which `pypi_intelligence` produces** — legal and normal, because
Kedro datasets are shared by catalog *name* and ownership belongs to the producer (AD-3).
The node only reads it. Its other inputs are `core_repodata_raw` and `pypi_conda_mapping`.

**No new external source.** This is the whole economy of the story: the signal is derived
entirely from data three earlier phases already fetched. It works only because Phase H
**retains `upload_time_iso_8601`** — B2/AC-5 kept that column specifically so B9 could
exist. Removing it silently kills this signal.

**First availability = `MIN(timestamp)`, and this is the load-bearing rule.** The conda
side is the *minimum* per-build `timestamp` across the matched version's artifacts, never
`latest_conda_upload`. conda-forge periodically rebuilds long-stable, version-unchanged
packages (migrations, ABI, compiler, py-matrix bumps), so a latest-upload delta measures
the most recent *rebuild*, not first availability. The naive
`latest_conda_upload − pypi_upload_time` formulation produced a false **"47% of packages
are >10 days behind"** headline. Using `MIN` means a rebuild landing inside the window
cannot shift the lag — and that is fixture-enforced, not merely intended.

**Two guards, deliberately redundant.** First availability is the suspenders; the 90-day
recency gate (`release_lag_qualifies`) is the belt. A version-unchanged package whose
upstream release is older than 90 days is excluded outright. Either guard alone would
mostly work; together they make the false-behind classification impossible to recur.

**Unit conversion happens exactly once, here.** Repodata per-build `timestamp` is in
**milliseconds**. It is normalized ms→s at this boundary via
`ts.where(ts < _MS_THRESHOLD, ts // 1000)` with `_MS_THRESHOLD = 1e12` — the same
convention as `core.nodes` and `IncrementalParquetDataset` (the DW-A3-P10 magnitude
split; `1e12` cleanly separates epoch-seconds ~1.7e9 from epoch-ms ~1.7e12). Everything
downstream of this line is epoch seconds.

**Determinism.** `now` is an injectable parameter defaulting to `int(time.time())`, so the
90-day gate is testable without freezing the clock.

**Three review-hardening details worth preserving.** Each fixes a silent-wrongness class,
not a crash:
- `_key()` normalizes every join key to a stripped string, because a version like `1.0`
  that round-tripped through a float dtype on one side would otherwise **miss its match
  silently** rather than error.
- `_empty()` declares explicit per-column dtypes (`release_lag_hours` float64,
  `release_lag_qualifies` bool). A bare `DataFrame(columns=cols)` yields object columns,
  which mismatches a schema-typed Parquet sink or a concat with a populated result.
- `qualifies` requires `upload_s.notna() AND lag_hours.notna()` *as well as* the 90-day
  window. A qualifying row must carry a real lag — otherwise it poisons any downstream
  aggregation over the qualifying population with a NaN.

**Degradation.** A malformed or unparseable `upload_time_iso_8601` yields
`release_lag_hours = NaN` and `qualifies = False`. It never raises (AD-13). Unmatched
versions produce no row at all rather than a null-lag row.

**Calibration, not assertion.** The live baseline the signal should roughly reproduce —
median ≈ 8.9 h, 72.4% within 24 h, 83.7% within 72 h — is recorded in the docstring as a
calibration reference and is deliberately **not** asserted by any gate. It was
cross-validated against a 5,000-package sample and the full 19,726-feedstock population to
within 1 pp.

### References

- [Source: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md#Story-B9]
- [Source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md#§9-Story-B9]
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
| Pull request | **#82** — story(B9): release-to-availability velocity columns (FR-20) |
| Merged | 2026-07-18 |
| Diff | 7 files, +484 / -15 |
| Test files touched | 4 |

**Commits**

- `73e477f` story(B9): release-to-availability velocity columns (FR-20)

**File list** *(exact, from the merged diff)*

```
  251 +     0 -  src/shared/packages/pyforge-atlas/tests/pipelines/vcs_health/test_release_velocity.py
  183 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/vcs_health/nodes.py
   17 +    12 -  src/shared/packages/pyforge-atlas/tests/pipelines/test_dag_resolves.py
   16 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/vcs_health/pipeline.py
   12 +     0 -  src/shared/packages/pyforge-atlas/conf/base/catalog.yml
    2 +     2 -  src/shared/packages/pyforge-atlas/tests/catalog/conftest.py
    3 +     1 -  src/shared/packages/pyforge-atlas/tests/parity/test_parity_complete.py
```

## Dev Agent Record

### Agent Model Used

In-session BMAD agent loop (draft → 2× adversarial review → 1× independent fresh-eyes review → real-gate verify), not a `bmad-dev-story` story-file run.

### Completion Notes List

- **Impl commit `73e477f`** — story(B9): release-to-availability velocity columns (FR-20)
  - Adds derive_release_velocity to the vcs_health pipeline (AD-3): reads the
  - Phase H pypi_current_versions (retained upload_time_iso_8601, no new fetch),
  - core_repodata_raw per-build timestamps, and the Phase C pypi_conda_mapping,
  - emitting release_lag_hours + release_lag_qualifies into vcs_release_velocity.
  - Load-bearing rule: the conda side is FIRST AVAILABILITY = MIN per-build
  - repodata timestamp of the matched version, NEVER latest_conda_upload — so a
  - rebuild landing inside the window can't shift the lag (fixture-enforced).
  - Repodata ms is normalized ms->s at this boundary (same _MS_THRESHOLD
  - convention as core.nodes / IncrementalParquetDataset). The 90-day recency
  - gate (release_lag_qualifies) keys on upstream-release age, killing the false
  - '47% behind' rebuild-cadence artifact.
  - AD-14: vcs_release_velocity is a new signal, name aligned to B4's frozen
  - EXCLUDED_NEW_SIGNAL_DATASETS (len stays 3); never parity-gated. AD-13:
  - pure DataFrame->DataFrame, malformed/empty inputs degrade to a typed empty
  - frame, never raise.
  - Two adversarial reviewer passes applied:
  - - malformed conda timestamp now yields qualifies=False (a qualifying row must
  - carry a real lag, else NaN pollutes downstream aggregation)
  - - empty-frame columns typed bool/float64 to match the non-empty path
  - 17 new tests (452 total), incl. both mandatory failure-mode fixtures.

## Review Triage Log

No separate review-fix commit; findings (if any) folded into the impl commit. Full review threads on PR `#82`.

<!-- end retro story -->

## Dev narrative — recovered from the merged record

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #82: story(B9): release-to-availability velocity columns (FR-20)
