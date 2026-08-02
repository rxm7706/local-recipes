---
spec: upstream-discovery
status: draft
owner-dream: docs/dreams/upstream-discovery.md  # dream archived 2026-08-02 (absorbed, narrative only); consolidated narrative home: docs/dreams/pyforge-atlas.md § The estate Atlas hosts. This SPEC's contract is unchanged and stays the chain's owner-dream link (dream_chain_check INV-1).
program: regenerable-factory (pyforge-atlas post-migration extension)
companions:
  - tier-taxonomy.md
  - org-audit-precedent.md
sources:
  - ../../../../../../docs/dreams/upstream-discovery.md
  - ../../../../../../docs/specs/trendshift-conda-forge.md   # superseded (intent/contract only — legacy file untouched): the v29->v30 schema numbering, cf_atlas phase-registration mechanics (bootstrap_data.py/atlas_phase.py/profile gating), and table names (github_trending_repos/trending_classification/v_trending_candidates) are dropped by the Kedro reframe; the discovery/classifier/CLI intent and the Track A/B shape carry over into CAP-1..5 below
supersedes: docs/specs/trendshift-conda-forge.md
assumptions:
  - Track B's org-audit shape is a reusable workflow over CAP-2's shared
    classifier, not a one-off manual sweep frozen at the June 2026 snapshot
    (inferred from the Dream's present-tense "systematic sweeps of
    high-yield orgs" framing).
  - Downstream packaging governance (CFE skill CLAUDE.md Rules 1 and 2) is
    unchanged by the Kedro reframe — it governs recipes/ output, not the
    atlas dataflow that produces candidates.
open_questions:
  - Which of the 7 closed pipelines (core / pypi_intelligence /
    vulnerability / vcs_health / universal_sbom / seed_gaps /
    derived_artifacts) hosts trending/org-audit discovery, or does it need
    an architecture correct-course to add an 8th? `vcs_health` is the
    closest existing fit (already hosts GitHub live queries + upstream
    version tracking) but this is not confirmed.
  - What catalog/dataset names does discovery output take under the shipped
    `<domain>_<entity>` naming convention? No SCHEMA_VERSION concept
    survives the migration (confirmed against the shipped architecture),
    but the specific dataset/pipeline names are not yet chosen.
  - Does the Search-API fallback reuse `vcs_health`'s existing per-host
    credential-scoped GitHub dataset (AD-2), or does it need its own
    dataset-level endpoint/credential entry?
  - Is the June-2026 org-audit candidate list (see `org-audit-precedent.md`)
    still accurate — has any candidate since shipped independently, or gone
    stale/archived? Re-verify via `lookup_feedstock` before any future batch
    treats it as live scope.
  - Is pyforge-doctor's health-screen surface (abandonment, license) ready
    to gate candidates, or does discovery's first batch have to run without
    it? pyforge-doctor has planning artifacts as of 2026-07-25 but its
    implementation status is unverified from this kernel.
  - "Cadence mechanism for re-running discovery (legacy default: monthly):
    does it reuse the shipped migration's Dagster Sensor + RSS/poll-cursor
    pattern (G3, `orchestration/definitions.py` `UPSTREAM_SENSORS`) instead
    of a fresh scheduling routine? The sensor substrate already exists and
    is the more architecturally consistent fit, but this is not decided."
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# upstream discovery — sense what the world is building

## Why

The factory should not wait for requests. It should sense what the
ecosystem is adopting — GitHub trending momentum and high-yield org
releases — and carry the worthy candidates into conda-forge before anyone
files an issue: a vision to realize, grounded in a pain already scoped once
by hand (the June 2026 Microsoft org audit). The legacy
`docs/specs/trendshift-conda-forge.md` (status `ready`, zero implementation)
designed this as a cf_atlas Phase T. The atlas has since migrated to a
Kedro/Dagster/DuckDB dataflow (shipped 2026-07-18, `pyforge-atlas`, 32/32
stories, PRs #58–#105) — verified against the shipped architecture and
epics: Phase T was modeled only as a *conditional* dependency that would
join the migration surface if it shipped before Wave B completed (epics.md
D-15); it never shipped, so it was never absorbed into the 32 stories. This
kernel re-grounds the legacy intent in the shipped dataflow's own
conventions — a Kedro node/pipeline, not a legacy phase — per the Dream's
2026-07-23 reframe note.

## Capabilities

- **CAP-1 — trending ingest**
  - **intent:** The dataflow ingests GitHub-trending Python repos
    (daily/weekly/monthly) via HTML-scrape-primary + GitHub Search API
    fallback, and never hard-fails the pipeline on scrape drift.
  - **success:** A run produces a fresh trending snapshot dataset; a
    scrape-layout-break run leaves the prior snapshot intact and exits
    non-fatal (WARN), caught by a fixture-pinned parser test.
- **CAP-2 — tier classification**
  - **intent:** A classifier node joins each ingested repo against existing
    atlas signals (on-conda-forge / feedstock enumeration, PyPI universe,
    PyPI intelligence: license, `requires_python`, packaging-shape,
    downloads, readiness) and labels it per the tier taxonomy (see
    `tier-taxonomy.md`) with an explicit reason on every row — never a
    silent drop.
  - **success:** Every ingested row in a batch carries a tier or an
    enumerated `skip_reason`; a fixture of hand-labeled repos classifies to
    the expected tiers, including one already-on-cf skip and one
    awesome-list skip.
- **CAP-3 — operator surface**
  - **intent:** An operator or agent can query the tiered candidate list
    read-side, offline-safe, idempotent, filterable per
    `tier-taxonomy.md`'s parameter table, as both a CLI and an MCP tool
    mirroring the atlas's existing dataset-passthrough MCP pattern.
  - **success:** The CLI and MCP tool return matching output for the same
    filters with zero network calls after ingest; JSON output validates
    against a documented schema.
- **CAP-4 — fixed-source audit track**
  - **intent:** The same discover→triage→tier→wave-package shape
    generalizes from the moving trending feed to a fixed candidate source
    (a named org, a curated list), reusing CAP-2's classifier instead of a
    one-off manual audit. See `org-audit-precedent.md` for the worked
    example (June 2026 Microsoft org audit).
  - **success:** A fixed-source batch produces the same tiered/reasoned
    candidate shape as CAP-1/CAP-2's output, re-verified against live atlas
    data rather than a precedent's dated package list.
- **CAP-5 — downstream handoff**
  - **intent:** Every surviving candidate (tier 1 or 2) passes a
    pyforge-doctor-grade health screen (abandonment signal, license
    clarity) before it is handed to the packaging-factory campaign
    machinery as a candidate to package — never auto-submitted.
  - **success:** A candidate reaching packaging carries a recorded
    health-screen verdict; discovery output alone never opens a
    staged-recipes PR.

## Constraints

- Discovery never auto-submits: output is a candidate list only; a human or
  BMAD story decides what proceeds to packaging.
- Any conda-forge recipe work downstream of a surfaced candidate is
  CFE-skill-governed (CLAUDE.md Rules 1 and 2) — this kernel's output feeds
  that governed workflow, it does not replace or bypass it; recipe
  authoring is out of this kernel's surface.
- Zero new firewall-blocking dependency: both the trending scrape and the
  Search API route through the atlas's existing HTTP/auth plumbing, so the
  enterprise/JFrog/air-gapped story is unaffected.
- No repo is ever silently dropped from a batch: every ingested row
  resolves to a tier or an enumerated `skip_reason`.
- Discovery stays inside the shipped dataflow's own conventions: pipeline,
  node, and dataset registration follow the closed 7-pipeline architecture
  and additive-first per-dataset schema evolution — no reintroduction of a
  legacy phase list, a profile-gating string, or a global schema-version
  constant.

## Non-goals

- `trendshift.io` programmatic scraping — no public API, homage only.
- Non-Python trending feeds in v1 — Python-scoped by default.
- Auto-submission of recipes (see Constraints).
- Re-packaging of already-shipped feedstocks.
- Upstream PRs to discovered repos (no README fixes, no license
  corrections, no dependency loosening) — recipes absorb artifacts as
  published.
- CUDA-variant recipe shape as a discovery-time concern — a packaging-time
  decision, not this kernel's.
- Treating the June-2026 org-audit package list as committed current scope
  — it is illustrative precedent only (`org-audit-precedent.md`).
- Building the pyforge-doctor health-screen logic itself — owned by the
  `pyforge-doctor` project; this kernel only requires the gate exists
  before a candidate proceeds (CAP-5).

## Success signal

An operator or agent runs discovery against the shipped pyforge-atlas
dataflow with no legacy cf_atlas dependency and gets back a tiered, reasoned
candidate list — zero repos silently dropped — that a human or BMAD story
can hand to the packaging factory with a health-screen verdict attached.

## Assumptions

- Track B's org-audit shape is a reusable workflow over CAP-2's shared
  classifier, not a one-off manual sweep frozen at the June 2026 snapshot.
- Downstream packaging governance (CFE skill Rules 1 and 2) is unchanged by
  the Kedro reframe.
- Until the pipeline-assignment open question resolves, any discovery code
  that lands still falls under `spec-pyforge-atlas`'s existing `src/**` /
  `conf/**` governed surface (this kernel deliberately does not declare its
  own `surface:` yet — asserting a specific pipeline module path would
  invent an answer to the open pipeline-assignment question below).

## Open Questions

- Which of the 7 closed pipelines (`core` / `pypi_intelligence` /
  `vulnerability` / `vcs_health` / `universal_sbom` / `seed_gaps` /
  `derived_artifacts`) hosts trending/org-audit discovery, or does it need
  an architecture correct-course to add an 8th? `vcs_health` is the closest
  existing fit but this is not confirmed.
- What catalog/dataset names does discovery output take under the shipped
  `<domain>_<entity>` naming convention? No SCHEMA_VERSION concept survives
  the migration (confirmed), but the specific names are not yet chosen.
- Does the Search-API fallback reuse `vcs_health`'s existing per-host
  credential-scoped GitHub dataset, or does it need its own dataset-level
  endpoint/credential entry?
- Is the June-2026 org-audit candidate list still accurate? Re-verify via
  `lookup_feedstock` before any future batch treats it as live scope.
- Is pyforge-doctor's health-screen surface ready to gate candidates, or
  does discovery's first batch have to run without it?
- Cadence mechanism for re-running discovery: does it reuse the shipped
  migration's Dagster Sensor + RSS/poll-cursor pattern instead of a fresh
  scheduling routine?
