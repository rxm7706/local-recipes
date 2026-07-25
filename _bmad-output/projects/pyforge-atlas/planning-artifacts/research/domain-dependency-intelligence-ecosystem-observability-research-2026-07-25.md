---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - docs/dreams/pyforge-atlas.md
  - docs/dreams/pyforge-charter.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
research_type: 'domain'
research_topic: 'Dependency-intelligence and package-ecosystem-observability tooling (libraries.io, ecosyste.ms, deps.dev / Open Source Insights) as reference points for pyforge-atlas'
research_goals: 'Ground the RETROSPECTIVE pyforge-atlas product brief in how comparable dependency-intelligence platforms structure their data model, signal taxonomy, and read surfaces — Atlas is an internal, non-commercial conda-forge intelligence data platform, not a market product, so this report frames the three named platforms as comparable/reference tooling, never as competitors.'
user_name: 'Rxm7706'
date: '2026-07-25'
web_research_enabled: true
source_verification: true
scope_note: 'LIGHT + RETROSPECTIVE scope. Atlas already SHIPPED (32/32 stories, PRs #58-#105, 2026-07-18) before the factory adopted the research-first convention — this report is backfilled evidence, grounding a brief that describes what was built and why it was worth building, not a pre-build decision input. No TAM/SAM/SOM or competitive-share analysis: Atlas is an internal data platform with one operator + an agent workforce as its users, never sold or marketed.'
methodology_note: 'The session WebSearch budget was exhausted (200/200) before this report began. Per the task''s explicit fallback instruction, every external claim below is sourced via WebFetch against each platform''s own site/docs and `gh` CLI calls against GitHub''s REST/GraphQL API (repo metadata: stars, license, last-push timestamp, latest release) — i.e., primary sources, not search-engine secondary summaries. This is disclosed as a methodology limitation, not a quality gap: `gh api` repo metadata is arguably more precise than a search snippet for the currency questions this report answers (is the project still maintained, under what license, as of when).'
---

# Research Report: Domain Research — Dependency-Intelligence & Package-Ecosystem-Observability Tooling

**Date:** 2026-07-25
**Author:** Rxm7706
**Research Type:** Domain (light, retrospective — internal data platform)

---

## Research Overview

Atlas is not a product pitched against these three platforms — it is the packaging factory's own intelligence layer, built to answer one operator's and one agent workforce's questions about a single channel (conda-forge) and its ~19,726-feedstock population. This report surveys three general-purpose, cross-ecosystem dependency-intelligence platforms — **libraries.io**, **ecosyste.ms**, and **deps.dev / Open Source Insights** — not to benchmark Atlas against them competitively, but to check Atlas's post-hoc design (data model shape, signal taxonomy, read-surface choice) against tooling the wider ecosystem has already converged on for the same underlying job: turning a package registry into a queryable intelligence surface. The finding, stated up front: Atlas's post-migration shape (a declared Data Catalog of typed datasets, a semantic layer translating them into named metrics, MCP/A2A machine-read surfaces) rediscovers the same three structural moves these platforms independently made at cross-ecosystem scale — this is convergent validation, not novelty, and the one place Atlas meaningfully diverges (conda-forge depth over ecosystem breadth) is a deliberate, defensible scope choice given its actual user base of one.

---

## 1. Libraries.io — the earliest cross-ecosystem precedent, and a currency warning

Libraries.io launched 2015 (founder Andrew Nesbitt), was acquired by Tidelift in 2017, and as of its last well-documented snapshot (April 2022) indexed ~6.9 million libraries across 32 package managers, organized by language, package manager, license, and keyword. It is AGPL-3.0-licensed with public source.

**Structural pattern relevant to Atlas:** Libraries.io's core abstraction is exactly Atlas's `packages` table generalized across ecosystems — one row per (ecosystem, package name), enriched with dependents, dependent-repositories, and a maintenance/popularity signal set. This is the same "one canonical entity, many enrichment columns" shape Atlas's Boring Semantic Layer (BSL) models declare over the Data Catalog.

**Currency finding (a genuine "dates the comparable," not Atlas):** `gh api repos/librariesio/libraries.io` (2026-07-25) shows the repo still receiving pushes as recently as 2026-07-06 and not archived — so the codebase is alive — but no public, current statement of Tidelift's own funding/staffing commitment to the service was found in this pass (the most recent substantive figures available date to 2022). This is flagged as an open question, not a claim of abandonment: unlike Atlas, whose freshness is enforced by its own TTL-gated pipeline and observable via `staleness-report`, libraries.io's *own* data currency is not independently verifiable from outside without re-querying it live.

**Implication for Atlas:** the comparable's ambiguous-currency status is itself a point in Atlas's favor as a design reference — Atlas's per-dataset TTL contract (Phase D 7d, Phase P 30d, EPSS 1d, CWE 90d) and its `staleness-report`/`behind-upstream` CLIs make Atlas's *own* freshness a first-class, queryable signal, which is precisely the property an outside consumer of libraries.io cannot get from libraries.io itself.

## 2. ecosyste.ms — the closest architectural analogue, and validation of "many small typed sources, one queryable graph"

Ecosyste.ms (operated as an open-source project, AGPL-3.0, data under CC BY-SA 4.0, funded by Schmidt Futures and the Open Source Collective) states its mission as building "open source intelligence" to "support, sustain, and secure critical digital infrastructure." As of the fetch date, it indexes **14.4 million packages across 109 sources**, **293 million repositories from ~2,000 sources**, **24.6 billion dependencies**, and **33.6 thousand security advisories across 12 languages** — a materially larger and more source-diverse graph than libraries.io's, built explicitly as its intelligence-layer scope grew.

**Structural pattern relevant to Atlas:** ecosyste.ms decomposes its intelligence surface into discrete, independently-versioned data services (packages, repositories, advisories, dependency-parsing/resolution, SBOM analysis, license extraction, package-comparison) rather than one monolithic schema — this is the closest external precedent for Atlas's own **seven-domain-pipeline decomposition** (Core; PyPI Intelligence; Vulnerability; VCS & Health; Universal SBOM; Seed-Gaps; Read-Surface/Derived-Artifacts), each pipeline owning its datasets with one producer per dataset (Architecture AD-3). Independently arriving at "decompose by data-service, not by monolith" across two different projects (one Ruby/Rails-era, one modern) is a signal this is the domain-correct shape, not an Atlas-specific invention.

**Implication for Atlas:** ecosyste.ms's advisory-tracking service (33.6k advisories/12 languages) is architecturally the same job as Atlas's Basilisk (conda-native vulnerabilities, FR-19) + the KEV/EPSS overlay — both are "vulnerability data as one more typed dataset alongside package/dependency data," not a bolted-on separate tool. This validates FR-18's design (assembling the `ComplianceReport` from atlas-native data plus pyforge-warden's axes) rather than treating vulnerability intelligence as an external black box.

## 3. deps.dev / Open Source Insights — the API-surface and provenance-chain precedent

deps.dev is "a service developed and hosted by Google to help developers better understand the structure, construction, and security of open source software packages," offering a **stable v3 API (with deprecation guarantees) and an experimental v3alpha**, both over JSON/HTTP or gRPC. It aggregates npm, PyPI, Maven (+ Google Maven/Jenkins/Gradle), Crates.io, Go, NuGet, and RubyGems registries, layering in GitHub/GitLab/Bitbucket project metadata, **OSV.dev advisories, OpenSSF Scorecard, and OSS-Fuzz coverage** on top.

**Structural pattern relevant to Atlas:** deps.dev's "stable-vs-alpha API tier" convention is the direct external precedent for Atlas's own MCP/A2A surface discipline (FR-7/FR-11) — a machine-read surface that promises a contract (schema-validated, versioned) distinct from an experimental one. More significant: deps.dev's practice of joining *its own* package graph against **external, independently-governed signal feeds** (OSV.dev, OpenSSF Scorecard, OSS-Fuzz) rather than re-deriving those signals in-house is the same design Atlas makes for KEV/EPSS (cached feeds joined onto Atlas-native package data, never re-scanned) and for its optional dependency on pyforge-warden's `ComplianceReport` schema at the FR-18 gate (Atlas provides package data; Warden owns compliance verdicts; the join is at the data layer, not a re-implementation).

**Implication for Atlas:** deps.dev's Scorecard integration is the closest external analogue to Atlas's currently-vision-tier "OpenSSF Scorecard maintenance axis" (see the PyForge Charter's Warden entry, axis 6) — evidence that if this axis is ever built, joining an existing external Scorecard feed (as deps.dev does) is the domain-proven approach, not standing up a parallel scorer.

---

## Cross-Domain Synthesis: What Atlas Already Matches vs. Where It Deliberately Diverges

| Pattern | Domain consensus (3 platforms) | Atlas's position |
|---|---|---|
| Data decomposition | Typed, independently-versioned data services/pipelines, not one monolith (ecosyste.ms explicit; deps.dev's per-registry adapters) | **Matches** — seven domain pipelines, one producer per dataset (AD-3), realized post-migration exactly as these platforms structure their own ingestion |
| External signal joining | Join independently-governed feeds (OSV.dev, Scorecard, OSS-Fuzz) rather than re-derive them | **Matches** — KEV/EPSS/endoflife feeds joined, never re-scanned; Basilisk and warden's ComplianceReport are joins, not re-implementations |
| API/read-surface tiering | Stable-vs-alpha contract discipline (deps.dev v3/v3alpha) | **Matches in spirit** — MCP surface audited/re-authored per FR-7; BSL is the one declared semantic translation layer (AD-8), preventing the per-surface metric drift these platforms' API-versioning exists to prevent |
| Ecosystem breadth | All three cover many ecosystems/registries (7+ languages each) | **Deliberate divergence** — Atlas is conda-forge-only by design (FR-15); breadth was never the goal, and the PRD's own non-goals (§5) name "Ecosystem-composition-by-language report" and cross-ecosystem breadth as explicitly deferred. This is the correct call for a single-operator internal tool serving one channel, not a gap to close. |
| Freshness as a first-class signal | Weakly externally-verifiable (libraries.io's own currency could not be confirmed past 2022 in this pass) | **Stronger than the comparables** — per-dataset TTL (`IncrementalParquetDataset`, AD-5) makes Atlas's own freshness queryable via `staleness-report`/`behind-upstream`, a property none of the three comparables expose about themselves to an outside observer |
| Public productization | All three are public-facing services (deps.dev/ecosyste.ms free; libraries.io was Tidelift-commercial-adjacent) | **Deliberate divergence** — Atlas's 2026-07-16 internal market research (cited in the PRD, § 1) found "feeds > pages" demand shape and explicitly scoped out public dashboard productization (SM-C4); the D2 factory-status page is the intentionally narrow public-facing surface |

---

## Assumptions

- No TAM/SAM/SOM, pricing, or competitive-share analysis — Atlas is not sold, marketed, or positioned against these three platforms; they are read here purely as *architectural* reference points for a data-model/signal-taxonomy sanity check, consistent with the task's explicit framing.
- This report is **retrospective**: Atlas's actual architecture (AD-1 through AD-11, the seven-pipeline decomposition, the BSL/MCP/A2A surfaces) was already fully specified and shipped (2026-07-18) before this research ran. Findings above validate design choices already made; none of them are new requirements.
- Libraries.io's post-2022 operational/funding status could not be independently confirmed in this pass (WebSearch budget exhausted; the Wikipedia secondary source itself notes no update past 2025-09-21 on funding). Flagged as an open question, not asserted either way.

## Open Questions

- Should Atlas ever expose a public, versioned API surface analogous to deps.dev's v3/v3alpha tiering (as opposed to today's MCP-tool-mediated agent access), the stable/experimental split is the domain-proven shape to copy — but this is out of scope for the shipped v1 migration and would need its own evidence-gated FR per the PRD's own promotion discipline (§ 9.2, "promotion requires measured evidence → FR + story").
- If the OpenSSF-Scorecard-style maintenance axis (Charter's Warden axis 6, currently vision-tier) is ever built, should it live in Atlas (as a joined external feed, deps.dev-style) or in Warden (as a compliance-gate axis)? This report's finding is that the *data* belongs in Atlas (feed-join pattern) while the *verdict* belongs in Warden (gate pattern) — consistent with the already-established atlas-provides-data / warden-uses-data relationship (PRD § 9.13) — but this is a future-scope question, not a v1 gap.

## Sources

- [Ecosyste.ms](https://ecosyste.ms/) — mission, package/repository/advisory/dependency counts, funding (Schmidt Futures, Open Source Collective), AGPL-3.0 license (fetched 2026-07-25 via WebFetch)
- [deps.dev](https://github.com/google/deps.dev) — API tiers (v3/v3alpha), registry coverage, OSV.dev/Scorecard/OSS-Fuzz integration (fetched 2026-07-25 via WebFetch of the GitHub repo README, since deps.dev's own homepage is a JS-rendered SPA with no static content)
- [Libraries.io — Wikipedia](https://en.wikipedia.org/wiki/Libraries.io) — founding, Tidelift acquisition, 2022 snapshot figures (fetched 2026-07-25 via WebFetch)
- `gh api repos/librariesio/libraries.io` — repo metadata: AGPL-3.0, not archived, last push 2026-07-06 (2026-07-25)
- `gh api repos/google/deps.dev` — repo metadata: not archived, last push 2026-07-21 (2026-07-25)
- Internal: `docs/dreams/pyforge-atlas.md`, `docs/dreams/pyforge-charter.md` § Atlas/Warden, `_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md`, `.../architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md`, `.../epics.md` — Atlas's own shipped design, read for comparison, not as external evidence
