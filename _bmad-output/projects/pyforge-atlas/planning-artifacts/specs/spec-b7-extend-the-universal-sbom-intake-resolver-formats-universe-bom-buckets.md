---
title: 'Story B7 (3.7): Extend the Universal SBOM intake (resolver, formats, universe BOM, buckets)'
type: 'feature'
status: 'regenerated'
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'
---

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story B7 (3.7): Extend the Universal SBOM intake (resolver, formats, universe BOM, buckets)

As a CI consumer,
I want the transitive-resolver node, the widened tiered manifest intake, the universe-BOM catalog dataset, and the matching node with shipped bucket semantics,
So that any manifest normalizes to CycloneDX and matches against the full conda-forge universe.

**Acceptance Criteria:** (spec § 9 Story B7, binding)

**Given** the § 4.10 tiered intake formats
**When** the SBOM pipeline is extended
**Then** a bare `requirements.txt` resolves to a full transitive dependency set with resolution depth + fan-out recorded (offline: `unresolved` marker, AD-13)
**And** every § 4.10 format normalizes to CycloneDX preserving the `cfe:*` property namespace and the `?channel=conda-forge` qualifier
**And** the full-universe CycloneDX BOM is a catalog dataset under the 14-day freshness contract; consumers refuse a stale atlas exactly as the legacy gate does
**And** a matching run reproduces the legacy six-bucket classification (ADD / ADD-NONPYPI / UPDATE-FEEDSTOCK / UPDATE-PIN / CURRENT / UNKNOWN) on a fixture inventory
**And** NBSP-padded pasted `conda list` / `pip list` text parses identically to its ASCII-space form (fixture).

- **FRs:** FR-13, FR-17.
- **Invariants:** AD-10 (`cfe:*` + qualifier never stripped), AD-12 (B7 produces security inputs, never assembles reports), AD-15, AD-13, AD-3.
- **Mode:** LOOP-S.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (format fixtures, six-bucket fixture, NBSP fixture).
- **Depends on:** B1, B2; § 14 position after B6.

### Story B8 (3.8): Basilisk conda-native vulnerability ingestion

As a CFE authoring agent,
I want the two Basilisk ingestion nodes in the Vulnerability pipeline with the tri-state `fix_available` join,
So that conda-native advisories reach the read surface without conflating version currency with security currency.

**Acceptance Criteria:** (spec § 9 Story B8, binding)

**Given** Q7's landing decision recorded before implementation
**When** the ingestion nodes land
**Then** a batch run over the full Python population writes `basilisk_vulns` (`conda_name`, `advisory_id`, `modified`) via `POST /v1/querybatch` at ≤1,000 queries per request (plus the bounded `GET /v1/vulns/{id}` detail fetch under standard rate-limit discipline)
**And** matching is by package name: a fixture proves an advisory whose `affected[]` ecosystem tag reads `PyPI` still matches its conda package
**And** `fix_available` is tri-state: a fixture advisory carrying only an enumerated `versions` list yields `unknown`, never `false`
**And** no read surface conflates version currency with security currency — a package can be `current` per `behind-upstream` AND carry a Basilisk advisory (fixture-proven)
**And** `BASILISK_BASE_URL` routes the endpoint per the mirror-routing convention; offline (consumer profile) the nodes skip gracefully and mark the dataset stale rather than failing.

- **FRs:** FR-19.
- **Invariants:** AD-13 (offline-skip + last-good + staleness marker), AD-14 (additive rider, fixture-enforced guards, not parity-gated), AD-2 (one new override point: `resolve_basilisk_urls`), AD-3.
- **Mode:** LOOP-S.
- **Gating question:** **Q7** (Basilisk landing point) — § 11 default adopted: build once as Kedro nodes in Wave B; a legacy Phase U pulls forward only if trendshift's timeline leaves a pre-migration window that matters. Recorded before implementation.
- **Verify gate:** `kedro-test` (the three binding-constraint fixtures + offline-skip fixture).
- **Depends on:** B2 (Vulnerability pipeline exists); NOT gated on B4 parity.

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
