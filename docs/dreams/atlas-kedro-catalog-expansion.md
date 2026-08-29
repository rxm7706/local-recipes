---
title: Expand the Atlas Kedro catalog so live indexes match the packaging inventory
type: dream
owner: atlas
status: draft
---

# Expand the Atlas Kedro catalog so live indexes match the packaging inventory

## The Dream

[[pyforge-atlas]] already runs a declarative Kedro catalog — conda-forge backbone,
PyPI intelligence, vulnerability overlays, VCS health, discovery tracks. The
[[conda-forge-packaging-inventory-operations]] dream runs a **separate** quartet
(workbook + live endpoints + priority + OpenTeams handoff). Both need the **same
live indexes** for verification (PyPI yes/no, conda-forge yes/no, cross-channel
presence, Basilisk catalog, AOSS lists, Anaconda defaults). Today those indexes
are duplicated, partially implemented, or only reachable through one toolchain.

The dream is **one catalog surface**: every live source the inventory dream
depends on is declared in `conf/base/catalog.yml`, fetched at the **dataset**
layer (AD-2 — nodes stay pure), routed through the existing `${globals:…}` override
points (AD-13), and materialized as Parquet the BSL, dashboard, and inventory
quarter can all read. No second HTTP client in scripts; no workbook tab as the
only copy of a public index.

A bootstrap run that already completed legacy `cf_atlas` + the seven Kedro
pipelines should **not** re-fetch what SQLite already holds — but steady-state
runs should be able to refresh every catalog entry without the inventory quartet.

## What it looks like when real

- **Cross-channel presence is complete for the factory's channels**, not just
  bioconda / pytorch / nvidia / robostack: **SelfExplainML** joins Phase Q-style
  bulk repodata (`in_selfexplainml` beside the existing four BOOLs).
- **Basilisk is two catalog entries, one override**: vuln advisories
  (`vulnerability_basilisk_*`, already shipped) **and** the **package catalog**
  (`GET /v1/packages`) — the dream's Basilisk tab and the HTML SPA are never
  the only source of truth.
- **Anaconda defaults are first-class**: `repo.anaconda.com/pkgs/main/channeldata.json`
  and the **Anaconda Distribution 2026.x** release list are cataloged beside
  conda-forge `core_channeldata_raw`.
- **Google AOSS free and premium** Python supported-package lists are catalog
  raw sources; premium ⊃ free; the **AOSS-Free Mason queue** (PyPI-yes,
  conda-forge-no, not in CDO consumption) derives from catalog Parquet, not a
  one-off script parse.
- **Discovery signals share the catalog**: maintainer feedstocks from
  [rxm7706/about](https://github.com/rxm7706/about), live curated-org sweeps,
  and Basilisk/AOSS frames land in **`upstream_discovery`** (or a sibling
  **`discovery`** pipeline) — not ad-hoc fetches inside
  `conda-forge-packaging-inventory-operations_metrics.py`.
- **Inventory quartet thins to orchestration**: workbook tabs remain the offline
  fallback and the enterprise-specific layers (CDO-ENT-JFROG consumption fields,
  OpenTeams board, priority / Score / Work, identity gist). Verification against
  PyPI, conda-forge, cross-channel, and public assurance lists **reads Kedro
  outputs**.
- **`kedro-catalog-check` and parity discipline stay green**: new entries get
  typed datasets (never bare `api.APIDataset` returning `Response` objects);
  new-signal datasets follow AD-14 (explicit parity scope, not silent legacy-surface drift).

## Sources to catalog (priority order)

### Tier 1 — explicit gaps from the 2026-08-29 bootstrap resume

| Source | Endpoint / pattern | Target pipeline | Notes |
|--------|-------------------|-----------------|-------|
| SelfExplainML channel | `conda.anaconda.org/SelfExplainML/.../repodata.json` | `pypi_intelligence` | Factory channel; extend `CrossChannelRepodataDataset` |
| Anaconda main | `repo.anaconda.com/pkgs/main/channeldata.json` | `core` or `pypi_intelligence` | Same parser family as `core_channeldata_raw` |
| Basilisk package catalog | `GET {BASILISK_BASE_URL}/v1/packages` | `upstream_discovery` or new `discovery` | Distinct from `vulnerability_basilisk_*` |
| Google AOSS free | supported-packages doc (Python) | `discovery` | Git-tracked fallback seed for air-gap |
| Google AOSS premium | premium doc or Wayback snapshot | `discovery` | Set-diff vs free in node |
| Anaconda Distribution 2026.x | release-doc package list | `core` or `discovery` | Version the fetcher; brittle HTML |

Cross-channel **bioconda / pytorch / nvidia / robostack** already flows through
`pypi_cross_channel_repodata_raw` — Tier 1 here is **hardening** (subdir +
`repodata.json` fallback, tests, offline last-good), not a new source.

### Tier 2 — inventory dream alignment

| Source | Role |
|--------|------|
| `rxm7706/about` maintained feedstocks | Maintainer/co-maintainer universe vs all feedstock-outputs |
| Live curated org repo lists | Extend `org_audit_candidates` with live scrape + `10kClosed` org hints |
| Artifactory consumption (CDO) | Harden [[artifactory-download-intelligence]] pipeline toward CDO-ENT-JFROG semantics |

### Tier 3 — legacy Phase Q stretch (schema columns exist, fetch deferred since v8.1.0)

homebrew · nixpkgs · spack · debian · fedora bulk indexes (or URL-pointer heuristic
for OS/distro signals) — same dataset-owned fan-out pattern as Phase Q.

## Architecture constraints (non-negotiable)

- **Dataset-owned IO** — fetch, parse, rate-limit, and fallback live in
  `pyforge.atlas.datasets.*`; nodes are `DataFrame → DataFrame` (A2 law).
- **One override point per host** — new channels use `{CHANNEL}_BASE_URL` env
  normalization; Basilisk reuses `BASILISK_BASE_URL` for both packages and vulns.
- **Bootstrap seed, steady-state fetch** — post-bootstrap runs may seed from
  `cf_atlas.db` once (the 2026-08-29 pattern); catalog entries must document when
  live fetch is opt-in (credentialed GitHub GraphQL, BigQuery Phase P, etc.).
- **Do not fold inventory ranking** — `P1`–`P10`, Score, Work, OpenTeams issue
  creation, and gist publish stay in the inventory quartet unless a later dream
  says otherwise.
- **Do not duplicate workbook-only enterprise fields** in Kedro — JFROG
  `risk_level`, `platform_env_count`, `internal_app_count`, etc. remain inventory
  columns, not atlas Parquet.

## Non-goals

- Replacing the inventory-operations quartet with Kedro nodes in one PR.
- Re-implementing OpenTeams board sync or PURL Associator inside Atlas.
- Parity-gating AD-14 new signals (Basilisk catalog, AOSS, SelfExplainML BOOL)
  against legacy `cf_atlas.db` row counts — they are additive discovery signals.
- Running `universal_sbom` in the default bootstrap chain (entry-scoped; requires
  `sbom_intake_path`).

## Open questions (for `bmad-spec`)

1. **New pipeline `discovery` vs extend `upstream_discovery` + `pypi_intelligence`?**
2. **SelfExplainML subdirs** — `noarch` only, or also `linux-64` (factory publishes both)?
3. **AOSS premium** — live doc vs Wayback-only default for air-gap?
4. **Anaconda Dist 2026.x** — mechanical extractor vs hand-curated seed + detector?
5. **Inventory quartet consumption** — read Parquet paths directly, or export a thin
   compatibility JSON layer for the existing metrics script?

## Kinships

[[pyforge-atlas]] · [[conda-forge-packaging-inventory-operations]] ·
[[upstream-discovery]] · [[artifactory-download-intelligence]] ·
[[packaging-factory]] · [[enterprise-airgap]]

## Success signal

`pixi run -e pyforge-atlas pyforge-atlas --pipeline __default__` (or the
documented bootstrap chain) materializes every Tier-1 source without manual
workbook tabs; `conda-forge-packaging-inventory-operations_metrics.py` can run
with `--live-catalog` (or equivalent) and produce identical verification columns
for PyPI, conda-forge, cross-channel, Basilisk, AOSS, and Anaconda main/dist —
workbook tabs required only for CDO enterprise consumption and OpenTeams offline
snapshots.
