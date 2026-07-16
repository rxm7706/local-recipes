---
stepsCompleted: [1, 2, 3]
inputDocuments: []
workflowType: 'research'
lastStep: 1
research_type: 'domain'
research_topic: 'cf_atlas domain triad: conda/PyPI packaging ecosystem, data-pipeline orchestration, software supply-chain security'
research_goals: 'Broad scan of all three domains, then targeted deep dives. Ground the cfe-atlas-datapipeline Kedro migration spec (v5.1) in current ecosystem evidence; systematically discover uncaptured external signals/feeds (e.g. are-we-recipe-v1-yet, migration trackers, advisory APIs) the atlas should ingest; validate or challenge the committed tool bets (Kedro + Dagster + DuckDB + Ibis/BSL + Vizro); map the vulnerability-feed and SBOM-standards landscape around FR-13/16/17/18/19.'
user_name: 'Rxm7706'
date: '2026-07-16'
web_research_enabled: true
source_verification: true
---

# Research Report: domain

**Date:** 2026-07-16
**Author:** Rxm7706
**Research Type:** domain

---

## Research Overview

[Research overview and methodology will be appended here]

---

<!-- Content will be appended sequentially through research workflow steps -->

## Domain Research Scope Confirmation

**Research Topic:** cf_atlas domain triad — conda/PyPI packaging ecosystem, data-pipeline orchestration, software supply-chain security
**Research Goals:** Broad scan of all three domains, then targeted deep dives. Ground the cfe-atlas-datapipeline Kedro migration spec (v5.1) in current ecosystem evidence; systematically discover uncaptured external signals/feeds (e.g. are-we-recipe-v1-yet, migration trackers, advisory APIs) the atlas should ingest; validate or challenge the committed tool bets (Kedro + Dagster + DuckDB + Ibis/BSL + Vizro); map the vulnerability-feed and SBOM-standards landscape around FR-13/16/17/18/19.

**Domain Research Scope:**

- Industry Analysis — structure and key players of each domain: packaging (conda-forge, prefix.dev, Anaconda, PyPA), orchestration (Kedro, Dagster, Airflow, Prefect, DuckDB-centric stacks), supply-chain security (OSV/Google, Aqua, Anchore, OWASP, Basilisk)
- Regulatory Environment — EU CRA, US EO 14028 / SSDF, SBOM mandates; PEP 740 / SLSA / CEPs as de-facto standards
- Technology Trends — recipe v1 adoption (are-we-recipe-v1-yet), rattler-build/pixi momentum, the DuckDB "small data" movement, semantic layers, agent-facing data surfaces (MCP)
- Economic Factors — ecosystem sizes, growth signals, sustainability of feeds the atlas would depend on
- Supply Chain / Ecosystem Analysis — the upstream release → advisory → packaging → consumption value chain; the **signal census** (every tracker/API/feed each domain publishes, mapped against current atlas ingestion)

**Research Methodology:**

- All claims verified against current public sources
- Multi-source validation for critical domain claims
- Confidence level framework for uncertain information
- Findings structured for direct incorporation into the migration spec's § 13 integration-surface matrix and § 12.1 candidate-signals table

**Scope Confirmed:** 2026-07-16

## Industry Analysis

*All figures verified against live sources 2026-07-16 (three parallel research agents + direct fetches); confidence flagged where evidence is thin. The triad's three domains are analyzed side by side.*

### Market Size and Valuation

**Domain 1 — conda/PyPI packaging ecosystem** (community-scale, not a "market" in analyst terms):
_conda-forge: 29,374 feedstocks (live, 2026-07-16); >1 billion downloads/month (first crossed April 2025); ~27 billion cumulative, excluding institutional mirrors._ _Sources: https://raw.githubusercontent.com/tdejager/are-we-recipe-v1-yet/main/feedstock-stats.toml ; https://conda-forge.org/blog/2025/04/11/ten-years-of-conda-forge/_
_PyPI: 852,477 projects / 9.1M releases / 20.1M files / 42.5 TB; ~2.8B downloads/day weekdays, >300B/year (vs ~7B in 2016)._ _Sources: https://pypi.org/ ; https://pypi.org/stats/ ; https://www.bambooweekly.com/bamboo-weekly-151-pypi-in-2025-solu/ (MEDIUM — single secondary source on BigQuery data)_
_Key valuations: Anaconda Inc. $1.5B (Series C, Jul 2025, >$150M ARR, profitable); prefix.dev seed-stage (one undisclosed 2022 round — 468 Capital, Costanoa; MEDIUM)._ _Sources: https://www.anaconda.com/press/anaconda-raises-150m-series-c-funding-ai-enterprise ; https://tracxn.com/d/companies/prefix.dev/__kBqv-xjEWV03NAElKhzjqdNNvf2duQQhwioeDbUs1_w/funding-and-investors_

**Domain 2 — data-pipeline orchestration**: analyst sizings span an order of magnitude ($19B–$64B for 2025, LOW–MEDIUM each) — treat as directional; the consistent signal is double-digit growth. Adoption proxies (GitHub, live 2026-07-16): Airflow 46.1k stars · DuckDB 39.5k · Prefect 23.4k · Dagster 15.8k · Kedro 10.9k · Ibis 6.6k · Vizro 3.8k. Money is flowing to durable-execution/agents: Temporal $300M Series D at $5B (2026). _Sources: https://github.com/apache/airflow (et al., per-repo) ; https://www.geekwire.com/2026/temporal-raises-300m-hits-5b-valuation-as-seattle-infrastructure-startup-rides-ai-wave/_

**Domain 3 — software supply-chain security**: narrow SCA sizings ~$380–710M (2025); broad supply-chain-security definitions ~$4.6B; convergent growth signal **~16–21% CAGR across six analyst houses** (MEDIUM-HIGH by convergence, any single number LOW). Category legitimized by the **inaugural Gartner Magic Quadrant for Software Supply Chain Security (June 17, 2026)** — Leaders: JFrog, Black Duck, Checkmarx, Chainguard, Sonatype. Chainguard $3.5B valuation; Socket $1B; Endor Labs $93M Series B. _Sources: https://www.skyquestt.com/report/software-composition-analysis-market ; https://jfrog.com/gartner-magic-quadrant/ ; https://fortune.com/2025/04/23/exclusive-chainguard-secures-356-million-series-d-as-valuation-soars-to-3-5-billion/ ; https://socket.dev/blog/series-c_

### Market Dynamics and Growth

_Growth drivers:_ AI-generated code (every SCA vendor re-messaging around it; Socket's $1B round explicitly framed on it); regulatory gravity — the **EU CRA reporting obligations go live September 11, 2026** and full application (incl. SBOM duty) December 11, 2027; conda-forge's rattler-build/recipe-v1 modernization; agent-facing data surfaces (MCP servers now table stakes for every warehouse vendor). _Sources: https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act ; https://socket.dev/blog/series-c ; https://chatforest.com/reviews/data-warehouse-lakehouse-mcp-servers/_
_Growth barriers / counter-currents:_ the **US federal driver weakened** — OMB M-26-05 (Jan 23, 2026) rescinded the secure-software attestation collection requirement; PSF fragility (~$5M budget, 14 staff, withdrawn $1.5M NSF grant Oct 2025, paused grants program); **NVD's April 2026 retreat from universal CVE enrichment** (only KEV/federal/critical CVEs enriched — ~15–20% of volume). _Sources: https://www.insidegovernmentcontracts.com/2026/02/omb-rescinds-the-common-form-secure-software-attestation-requirement/ ; https://pyfound.blogspot.com/2025/10/NSF-funding-statement.html ; https://www.nist.gov/news-events/news/2026/04/nist-updates-nvd-operations-address-record-cve-growth_
_Market maturity:_ packaging = mature-and-modernizing; orchestration = consolidating (see Competitive Dynamics); supply-chain security = high-growth, category-forming (first Gartner MQ in 2026).

### Market Structure and Segmentation

**Packaging**: community core (conda-forge: 24-member elected core team; QuantCo maintaining 1,000+ feedstocks and driving the regulatory workstream) + two commercial poles — Anaconda Inc. (distribution CDN + paid licensing >200-employee orgs; pivoting to AI platform via Outerbounds (Apr 2026) and Kilo Code (Jul 15, 2026) acquisitions) and prefix.dev (pixi/rattler-build/parselmouth OSS + channel hosting GA Apr 2026). _Sources: https://conda-forge.org/community/governance/ ; https://tech.quantco.com/blog/conda-regulation-support/ ; https://www.anaconda.com/blog/anaconda-acquires-kilo-code ; https://prefix.dev/_
**Orchestration**: consolidation wave — **Prefect acquired Dagster Labs (announced 2026-07-13**; combined company under the Prefect name from Aug 2026; Dagster founder departs to advisor role; public commitments: Dagster keeps its name, Apache-2.0 license, and roadmap); Fivetran+Tobiko+dbt Labs merged (2025); Astronomer took a ~48% down-round ($775M, May 2025). Foundation-governed components (Kedro → LF AI & Data **Graduate** since Dec 2024; DuckDB → DuckDB Foundation, no VC; Hamilton → ASF) are the stability pole. _Sources: https://www.prefect.io/prefect-acquires-dagster ; https://dagster.io/blog/prefect-is-acquiring-dagster ; https://lfaidata.foundation/projects/kedro/ ; https://www.astronomer.io/press-releases/astronomer-secures-93-million-series-d-funding/_
**Supply-chain security**: PE consolidation of legacy SCA (Black Duck sold by Synopsys for $2.1B, Oct 2024; Snyk IPO stalled, exploring buyout — MEDIUM) vs mega-funded "safe source"/AI-code challengers (Chainguard, Socket, Endor); the free-feed commons (OSV, GHSA, KEV, EPSS, Vulnrichment) sits underneath all of them. _Sources: https://www.franciscopartners.com/media/clearlake-and-francisco-partners-complete-acquisition-of-black-duck-software-formerly-known-as-synopsys-software-integrity-group ; https://www.theinformation.com/articles/cybersecurity-startup-snyk-considers-buyout-interest-ipo-plans-stall_

### Industry Trends and Evolution

- **Recipe v1 adoption (the seed signal)**: 6,270 of 29,374 feedstocks (21.3%) on rattler-build recipe v1, from ~700 in Feb 2025 — tracked daily by *are-we-recipe-v1-yet* (per-feedstock TOML incl. `last_changed` + downloads; method: `conda_build_tool: rattler-build` detection over cf-graph). Since May 2026 conda-forge v1 builds run through the py-rattler-build Python API. _Sources: https://raw.githubusercontent.com/tdejager/are-we-recipe-v1-yet/main/feedstock-stats.toml ; https://conda-forge.org/blog/2025/02/27/conda-forge-v1-recipe-support/ ; https://conda.org/blog/2026-05-20-may-releases/_
- **Python 3.14 rollout**: conda-forge's fastest Python migration ever — 77% progressed within days of release (Oct 2025); 1,932 binary packages at the 100-day mark. _Sources: https://conda-forge.org/blog/2025/10/09/python-314/ ; https://conda-forge.org/blog/2026/01/15/100-days-python314/_
- **Standards hardened in late 2025**: CycloneDX 1.7 = **ECMA-424 2nd ed.** (Dec 2025, adds Citations/provenance); **purl = ECMA-427** (approved Dec 10, 2025; ISO fast-track in process); OSV schema v1.8.0 (Jul 9, 2026) adds a severity `source` field. **CEP-63 (conda purls) is still an in-flight proposal, not accepted** (accepted CEPs end at 0047). _Sources: https://ecma-international.org/publications-and-standards/standards/ecma-427/ ; https://cyclonedx.org/news/cyclonedx-v1.7-released/ ; https://github.com/ossf/osv-schema/blob/main/CHANGELOG.md ; https://github.com/conda/ceps_
- **The NVD gap is the defining vuln-data event**: NIST reclassified ~29,000 backlogged CVEs "Not Scheduled" (Apr 15, 2026); CISA Vulnrichment (ADP containers in CVE 5.x) is the primary free replacement; CVE-program governance remains a structural single point of failure (Apr 2025 near-lapse; CVE Foundation hedge). _Sources: https://www.nist.gov/news-events/news/2026/04/nist-updates-nvd-operations-address-record-cve-growth ; https://github.com/cisagov/vulnrichment ; https://cyberscoop.com/cve-program-funding-crisis-cve-foundation-mitre/_
- **DuckDB-centric "small data" stack matured**: DuckDB 1.5.4; 1.4.x LTS line; DuckLake 1.0; full Iceberg writes; duckdb-wasm at parity 1.5.4 with in-browser Iceberg REST — directly de-risks the spec's FR-5/FR-14 bets. _Sources: https://github.com/duckdb/duckdb ; https://motherduck.com/blog/announcing-ducklake-1-0-on-motherduck/ ; https://duckdb.org/docs/current/clients/wasm/overview_
- **Semantic layer = agent interface** is the 2026 framing (dbt MCP, Cube-for-agents, warehouse-native semantic views); boring-semantic-layer is the lightweight Ibis+MCP entry (Malloy-inspired; Malloy itself absent from 2026 comparisons). _Sources: https://cube.dev/articles/semantic-layer-for-ai-agents-2026 ; https://juhache.substack.com/p/the-boring-semantic-layer_
- **Malicious-package volume**: cumulative open-source malware +75% YoY to 1.233M packages (Sonatype 2026); slopsquatting (LLM-hallucinated package names, 43% deterministic recurrence) is a new, pre-registerable attack surface. _Sources: https://www.sonatype.com/press-releases/sonatype-research-reveals-open-malware-grows-75-percent ; https://labs.cloudsecurityalliance.org/research/csa-research-note-slopsquatting-ai-supply-chain-20260419-csa/_

### Competitive Dynamics

- **Packaging**: distribution is single-vendor-dependent — the 1B+/month conda-forge firehose flows through Anaconda's CDN under a ToS (effective Jul 15, 2025) that **prohibits unauthorized mirroring**, while Anaconda's strategic center of gravity moves toward AI platforms; the QuantStack OCI mirror is the hedge but its CZI grant has concluded (ops funding unclear). prefix.dev is simultaneously seed-stage and ecosystem-critical (v1 toolchain, hourly parselmouth mapping, proposed conda-forge security SIG + community CVE mapping seeking NumFOCUS/Alpha-Omega funding). _Sources: https://www.anaconda.com/legal/terms/terms-of-service ; https://labs.quansight.org/blog/czi-eoss-5-conda-forge ; https://prefix.dev/blog/securing-the-supply-chain_
- **Orchestration — the spec's committed-bet health check** (full per-package table in the § Technical Trends step): Kedro 1.5.0 / DuckDB 1.5.4 / Vizro 0.1.59 all healthy and foundation- or enterprise-backed; **Dagster healthy but under acquisition uncertainty** (Prefect, Jul 13, 2026 — Apache-2.0 reaffirmed, founder departing); **kedro-dagster = bus factor ≈1** (sole maintainer at a small consultancy, 23 stars, `dagster <2.0` pin, community-plugin status — not in Kedro's officially-supported deployment list); **kedro-mcp = early/stale** (0.1.2, 14 commits, quiet ~5 months; scope is AI *guidance*, not pipeline access); **boring-semantic-layer = young, two-person core** (13 months old, 0.x churn, ~14k downloads/month). Dagster Components (GA Sep 2025) is both validation of declarative authoring and a substitution risk for the bridge. _Sources: https://github.com/stateful-y/kedro-dagster ; https://github.com/kedro-org/kedro-mcp ; https://github.com/boringdata/boring-semantic-layer ; https://dagster.io/blog/dagster-components-ga ; https://docs.kedro.org/en/stable/deploy/supported-platforms/dagster/_
- **Supply-chain security**: reachability analysis is the table-stakes differentiator (60–95% alert suppression claims — vendor figures, MEDIUM); every vendor pivoting to AI-code security; the durable free-feed layer (OSV/GHSA/KEV/EPSS/Vulnrichment) is what an open pipeline should anchor on, with multi-feed redundancy as the CVE-program-risk hedge. _Sources: https://www.pixee.ai/resource-center/software-supply-chain-security/reachability-analysis ; https://openssf.org/blog/2026/01/08/signal-in-the-noise-an-industry-wide-perspective-on-the-state-of-vex/_

### The Signal Economy — census summary (cross-domain)

*The census the deep-dive steps will refine. Sustainability legend: 🟢 institution-backed · 🟡 startup/grant-dependent · 🔴 single-maintainer.*

**Packaging-ecosystem signals:**

| Signal | Provides | Endpoint / cadence | Sust. |
|---|---|---|---|
| are-we-recipe-v1-yet | Per-feedstock v1-vs-meta.yaml state + `last_changed` + downloads | raw `feedstock-stats.toml` (TOML), daily | 🔴 (T. de Jager) |
| conda-forge status / bot-data | Migrations, incidents, version queue | JSON (`version_status.v2.json` etc.), continuous | 🟢 (already FR-21) |
| cf-graph-countyfair | Full dep graph, node attrs, PyPI↔conda maps | GitHub JSON, continuous (autotick bot) | 🟢 (already ingested) |
| parselmouth API | conda↔PyPI mapping + sha256 lookup | `conda-mapping.prefix.dev` (JSON/JSONL.gz), **hourly** | 🟡 (prefix.dev) |
| anaconda.org REST API | Metadata + `ndownloads` | `api.anaconda.org/package/...`, real-time | 🟢 ToS-gated (already ingested) |
| by-the-numbers | Ecosystem growth stats | GitHub notebooks/data, periodic | 🟢 |
| PyPI APIs (JSON/Simple/**Integrity**/RSS) | Metadata, files, **PEP 740 attestations** | docs.pypi.org/api, real-time | 🟢 (already ingested; Integrity API is new surface) |
| PyPI BigQuery | Download events (canonical) | BigQuery public dataset | 🟢 (already Phase P) |
| ecosyste.ms | 14.4M pkgs / 293M repos cross-registry | open JSON APIs, continuous | 🟡 (grant + one person) |
| deps.dev (Google) | Cross-registry deps/advisories (PyPI yes, conda no) | REST v3, continuous | 🟢 unilateral |
| pypistats.org / pepy.tech | Download aggregates | JSON APIs (heavy rate limits), daily | 🔴 |
| OCI conda-forge mirror | CDN-independence hedge | GHCR, continuous | 🟡 (grant concluded) |
| conda/ceps + cfep repos | Standards pipeline (CEP-63 watch) | GitHub markdown, per-proposal | 🟢 |

**Vulnerability-feed additions (beyond the ingested OSV/vdb/KEV/EPSS/CWE/endoflife/Basilisk set), in recommended priority order:**

| Feed | Adds | Endpoint / format | Sust. |
|---|---|---|---|
| CISA Vulnrichment (ADP) | SSVC + CWE + CVSS filling the NVD gap | github.com/cisagov/vulnrichment (CVE 5.x JSON), continuous | 🟢 (federal-budget MEDIUM) |
| VulnCheck KEV | >130% more exploited-vulns than CISA KEV, ~27 days earlier | free community REST (sign-up), continuous | 🟡 (free tier could change) |
| OpenSSF malicious-packages | `MAL-` records (malware axis) **already in OSV format via osv.dev** | github.com/ossf/malicious-packages, continuous | 🟢 |
| EUVD (ENISA) | EU-official aggregation + exploited/critical endpoints; CRA reporting hub from Sep 2026 | REST `euvd.enisa.europa.eu/apidoc`, continuous | 🟢 (NIS2-mandated) |
| VulnerableCode V3 | purl-native cross-check/dedup layer | public.vulnerablecode.io (V3; V1/V2 deprecated) | 🟡 (grant-dependent) |
| OpenSSF Scorecard / criticality_score | Repo security-posture + criticality signals | api.scorecard.dev REST / CSV dumps | 🟢 |
| GHSA / PYSEC | Human-reviewed advisories | OSV format | 🟢 (already transitively via OSV) |

**Orchestration-ecosystem signals** (lower priority): Apache Airflow Registry (104 providers, auto-updated), Dagster integrations index (~70+, no machine feed — track the `dagster-*` PyPI namespace), Kedro plugin topic, DuckDB community-extensions registry, MCP-server registries (fragmented, no canonical feed yet), the annual State of Airflow survey. _Sources: https://airflow.apache.org/registry/ ; https://dagster.io/integrations ; https://github.com/topics/kedro-plugin_

### Regulatory Snapshot (feeds § Regulatory Focus step)

EU CRA phase-in: notification bodies Jun 11, 2026 → **exploited-vuln/incident reporting Sep 11, 2026** (24h/72h/14d cascade to ENISA) → full application incl. SBOM duty Dec 11, 2027; open-source **stewards** get a light-touch regime (policy + cooperate + report known-exploited; exempt from fines; non-monetized maintainers out of scope). Germany BSI TR-03183-2 v2.1.0 accepts **CycloneDX ≥1.6 or SPDX ≥3.0.1** only. India CERT-In v2.0 (Jul 2025) is the strictest emerging regime (SBOM/AIBOM/CBOM for government + BFSI). US: OMB M-26-05 rescinded common-form attestation (Jan 2026). _Sources: https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act ; https://orcwg.org/cra/ ; https://www.bsi.bund.de/SharedDocs/Downloads/EN/BSI/Publications/TechGuidelines/TR03183/BSI-TR-03183-2_v2_1_0.html ; https://www.cert-in.org.in/PDF/TechnicalGuidelines-on-SBOM,QBOM&CBOM,AIBOM_and_HBOM_ver2.0.pdf_

### Quality Assessment

HIGH-confidence backbone (live fetches, primary sources): feedstock counts, adoption numbers, release/health data on all ten committed packages, ECMA/CRA/NVD facts, the Prefect-Dagster acquisition. MEDIUM: analyst market sizings (definition-dependent), vendor revenue claims, pixi adoption figures. LOW/unverified: Basilisk's public status (no public trace — but the API is live per this project's own validated batch runs of 2026-07-15; treat as pre-announcement), Snyk take-private numbers, noarch-share percentage (gap — derivable from repodata). Research gaps carried forward: head-to-head PyPI download comparison for orchestrators (pypistats rate limits), current PEP 740 coverage percentage.

## Competitive Landscape

*Analyzed at two altitudes: (a) the players within each domain, and (b) — the actionable lens — who competes with or adjacently to a conda/PyPI package-intelligence pipeline like cf_atlas.*

### Key Players and Market Leaders

_Packaging:_ conda-forge (community, 24-member core) is the de-facto scientific-Python channel; Anaconda Inc. controls distribution (CDN) and monetizes curation; prefix.dev owns the modern toolchain narrative (pixi/rattler-build); QuantCo and Quansight/QuantStack are the heavyweight community contributors. _Sources: https://conda-forge.org/community/governance/ ; https://prefix.dev/ ; https://tech.quantco.com/blog/conda-regulation-support/_
_Orchestration:_ Airflow (Apache; 46.1k stars, 80k+ orgs claimed) remains the incumbent; **Prefect+Dagster (one company as of 2026-07-13)** consolidates the "modern orchestrator" challenger lane; Temporal ($5B) owns durable execution; Kedro (LF AI & Data Graduate) is the framework-neutral authoring layer. _Sources: https://www.prefect.io/prefect-acquires-dagster ; https://lfaidata.foundation/projects/kedro/_
_Supply-chain security:_ 2026 Gartner MQ Leaders — JFrog, Black Duck, Checkmarx, Chainguard, Sonatype; challengers Socket ($1B) and Endor Labs (reachability); the free-data commons (OSV.dev/Google, GHSA/GitHub, CISA, FIRST) underpins all of them. _Source: https://jfrog.com/gartner-magic-quadrant/_

### Market Share and Competitive Positioning — the conda-CVE-mapping race (the pipeline's own lane)

A three-way race now exists for exactly the capability cf_atlas builds (conda-native vulnerability intelligence):

| Player | Approach | Model |
|---|---|---|
| **Anaconda Package Security Manager** | Human-curated CVE data + **"CVE Association for conda-forge packages"**; explicitly marketed as filling the NVD-enrichment gap | Commercial (PSM cloud/on-prem, air-gap capable) |
| **prefix.dev** | Basilisk OSV-compatible API (live, pre-announcement) + proposed **conda-forge security SIG** with an open community CVE mapping (seeking NumFOCUS/Alpha-Omega funding) | Open/community (VC-startup-sponsored) |
| **cf_atlas (this project)** | Local, offline-capable pipeline: vdb + KEV/EPSS overlay + Basilisk conda-PURL axis (FR-19), CycloneDX/purl-normalized | Open, self-hosted |

_Sources: https://www.anaconda.com/blog/new-cve-association-for-conda-forge-packages-helps-secure-your-software-supply-chain ; https://www.anaconda.com/blog/securing-the-open-source-pipeline-with-anaconda-cve-curation ; https://prefix.dev/blog/securing-the-supply-chain_
Adjacent positioning: **JFrog Xray added conda support** (Catalog, Curation, Compliant Version Selection; vulnerability coverage via binary scanning) — the enterprise-artifact-manager lane now overlaps conda; **Chainguard Libraries for Python** (GA; ~10k projects rebuilt from source, SLSA L3, 98% malware-block in testing, free until June 30, 2026) defines the "replace the intelligence problem with a trusted source" lane; **Tidelift (acquired by Sonar, Dec 2024)** sells maintainer-validated practice data — the human-attestation lane. _Sources: https://docs.jfrog.com/security/docs/supported-technologies-xray ; https://www.chainguard.dev/unchained/chainguard-libraries-for-python-now-generally-available-with-cve-remediation-and-malware-protection ; https://www.sonarsource.com/company/press-releases/sonar-to-acquire-tidelift/_

### Competitive Strategies and Differentiation

_Cost leadership:_ the free-feed commons (OSV, GHSA, KEV, EPSS, Vulnrichment, deps.dev, ecosyste.ms) — differentiation impossible, sustainability variable. _Differentiation:_ curation quality (Anaconda, Black Duck BDSA post-NVD), reachability (Endor, Mend/Atom), rebuild-from-source (Chainguard), earlier/wider exploit intel (VulnCheck: >130% more KEV entries, ~27 days earlier). _Focus/niche:_ conda-native intelligence is a genuine niche — only Anaconda, prefix.dev, and cf_atlas address conda identity properly (the OSV ecosystem-tag gotcha this project validated is exactly why generic SCA misses conda). _Innovation:_ AI-code security (Socket, Endor, Mend), agent-facing surfaces (MCP everywhere), attestation/provenance (PEP 740, CEP-27, Sigstore). _Sources: https://www.vulncheck.com/kev ; https://www.blackduck.com/blog/nist-nvd-policy-shift-2026.html_

### Business Models and Value Propositions

_Packaging:_ Anaconda — paid distribution licensing (>200-employee orgs) + PSM curation + AI platform (Outerbounds, Kilo Code); prefix.dev — channel hosting GA (Apr 2026) + OSS goodwill; conda-forge — volunteer + sponsored CI, distribution costs borne by Anaconda's CDN. _Orchestration:_ open-core cloud (Dagster+/Prefect Cloud, now merged; Astronomer for Airflow); foundations (Kedro, DuckDB) monetize nothing — adjacent companies do (MotherDuck for DuckDB). _Supply-chain:_ per-developer SaaS (Snyk), curated-feed subscription (BDSA, VulnCheck), safe-source subscription (Chainguard), maintainer-revenue-share (Tidelift/Sonar). _Sources: https://www.anaconda.com/products/package-security-manager ; https://motherduck.com/blog/announcing-ducklake-1-0-on-motherduck/_

### Competitive Dynamics and Entry Barriers

_Barriers:_ for feeds — trust and coverage accumulation (OSV's aggregation moat, GHSA's review throughput of 6,000+ decisions/month); for conda intelligence — the name-mapping problem (PyPI↔conda identity, which parselmouth/cf-graph/G10-spelling solve piecemeal) is the real technical moat. _Consolidation:_ Prefect+Dagster, Fivetran+Tobiko+dbt, Sonar+Tidelift, Black Duck PE carve-out, possible Snyk take-private — mid-size independents are merging; foundation-governed assets appreciate. _Switching costs:_ low for feeds (OSV-format normalization makes them swappable — the § 13 slot/status matrix's premise), high for orchestrators (pipeline-code lock-in — mitigated in the spec by Kedro's framework-neutral authoring). _Sources: https://github.blog/security/supply-chain-security/inside-the-advisory-database-and-what-happens-when-vulnerability-volume-breaks-records/ ; https://www.datagravity.dev/p/fivetran-acquires-tobiko-data-to_

### Ecosystem and Partnership Analysis (who controls the value chain)

_Distribution control:_ Anaconda's CDN carries conda-forge's 1B+/month downloads under a mirroring-restrictive ToS — the single most concentrated control point in the triad; hedges: repo.prefix.dev mirror, the QuantStack OCI mirror (grant concluded), JFrog private mirrors. _Identity control:_ purl (now ECMA-427) + the community mapping layers (parselmouth hourly API, cf-graph) — no single owner, which favors open pipelines. _Advisory control:_ CVE program (CISA-funded, structurally fragile) → CNAs/ADP enrichment (CISA Vulnrichment) → aggregators (OSV, GHSA, EUVD); redundancy across these is the resilience strategy. _Agent-interface control:_ MCP is vendor-neutral and ubiquitous (FastMCP itself now Prefect-owned — a quiet consolidation of the agent-tooling layer). _Sources: https://www.anaconda.com/legal/terms/terms-of-service ; https://ecma-international.org/publications-and-standards/standards/ecma-427/ ; https://www.businesswire.com/news/home/20260713065285/en/Prefect-Acquires-Dagster-Uniting-the-Two-Leading-Modern-Orchestrators_

## Regulatory Requirements

### Applicable Regulations

- **EU Cyber Resilience Act (Regulation 2024/2847)** — in force, phasing in: conformity-body notification Jun 11, 2026 → **exploited-vulnerability & severe-incident reporting Sep 11, 2026** (24 h early warning / 72 h notification / 14 d–1 mo final report, to ENISA + CSIRTs) → **full application incl. the SBOM obligation Dec 11, 2027** (machine-readable SBOM of at minimum top-level dependencies in technical documentation). _Source: https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act_
- **CRA open-source roles**: "open-source **stewards**" (Art. 24 — foundations/companies providing sustained support without monetizing the software) get a light-touch regime — documented cybersecurity policy, cooperation with authorities, reporting of known-exploited vulnerabilities; exempt from administrative fines (Art. 64(10)). Non-monetized individual maintainers are out of scope. The Eclipse-hosted ORC WG publishes the de-facto steward guidance. _Sources: https://orcwg.org/cra/ ; https://openssf.org/public-policy/eu-cyber-resilience-act/_
- **US (weakening then re-shaping)**: OMB **M-26-05 (Jan 23, 2026) rescinded** the M-22-18/M-23-16 secure-software attestation collection; CISA **BOD 26-04 (June 10, 2026)** supersedes BOD 22-01/19-02 — federal patching now follows a four-variable risk matrix (public exposure × KEV status × automatability × technical impact) with 3/14/60-day tiers, replacing CVSS-deadline patching. _Sources: https://www.insidegovernmentcontracts.com/2026/02/omb-rescinds-the-common-form-secure-software-attestation-requirement/ ; https://www.cisa.gov/news-events/directives/bod-26-04-prioritizing-security-updates-based-risk ; https://www.tenable.com/blog/cisa-bod-26-04-FAQ-vulnerability-remediation-impact_
- **Germany**: BSI TR-03183-2 v2.1.0 — machine-readable SBOMs in **CycloneDX ≥1.6 or SPDX ≥3.0.1** only. _Source: https://www.bsi.bund.de/SharedDocs/Downloads/EN/BSI/Publications/TechGuidelines/TR03183/BSI-TR-03183-2_v2_1_0.html_
- **India**: CERT-In Technical Guidelines v2.0 (Jul 9, 2025) — SBOM/QBOM/CBOM/**AIBOM**/HBOM for government, essential services, and exporters; RBI/SEBI SBOM mandates in BFSI. _Source: https://www.cert-in.org.in/PDF/TechnicalGuidelines-on-SBOM,QBOM&CBOM,AIBOM_and_HBOM_ver2.0.pdf_

### Industry Standards and Best Practices

**CycloneDX 1.7 = ECMA-424 2nd ed.** (Dec 2025; Citations/provenance, deeper CBOM) and **purl = ECMA-427** (Dec 10, 2025; ISO fast-track) are now formal standards — the pipeline's exact identity/format bets. OSV schema v1.8.0 (Jul 2026) adds severity-source provenance. VEX is bifurcated by design: CSAF 2.x (regulated/vendor-grade) vs OpenVEX (lightweight emission) — OpenSSF's Jan 2026 review blesses coexistence. PEP 740 attestations GA on PyPI (Trusted Publishing); CEP-27 live on prefix.dev; **CEP-63 (conda purl) still in-flight**. Transparency Exchange API (Project Koala, Ecma TC54 TG1) in Beta 2 — the likely future standard for *publishing* per-package SBOM/VEX. _Sources: https://ecma-international.org/publications-and-standards/standards/ecma-427/ ; https://openssf.org/blog/2026/01/08/signal-in-the-noise-an-industry-wide-perspective-on-the-state-of-vex/ ; https://github.com/CycloneDX/transparency-exchange-api ; https://github.com/conda/ceps_

### Compliance Frameworks

SSDF (NIST SP 800-218) remains the US practice baseline even after M-26-05 (agencies shift to risk-based approaches, may still use the common form voluntarily); SLSA provenance levels anchor build-integrity claims (Chainguard markets SLSA L3 rebuilds); CRA harmonized standards (Type A due Aug 30, 2026; B/C Oct 30, 2026 — MEDIUM confidence) will operationalize CE-marking for software. _Sources: https://www.cisa.gov/secure-software-attestation-form ; https://orcwg.org/cra/_

### Data Protection and Privacy

The pipeline processes **public developer identity data** (maintainer usernames from cf-graph/GitHub). Under GDPR this is personal data; the applicable basis is **legitimate interest** (research/ecosystem-maintenance purposes are the standard grounds; GitHub itself processes on legitimate-interest grounds), with the usual conditions: data minimization (role data only, no enrichment beyond public sources), purpose limitation, and honoring erasure where feasible. No special-category data is involved; risk is low but non-zero (the maintainer-universe tables are redistributable artifacts). _Sources: https://www.freeprivacypolicy.com/blog/open-source-projects-gdpr/ ; https://iapp.org/news/a/how-gdpr-changes-the-rules-for-research ; https://docs.github.com/site-policy/privacy-policies/github-privacy-statement_

### Licensing and Certification

Two live licensing surfaces for the pipeline: (1) **Anaconda ToS (Jul 15, 2025)** — mirroring the platform or offerings without authorization is prohibited; >200-employee orgs need paid licenses for Anaconda-built packages (conda-forge channel remains free) — binding on how Phase F/B source data at scale; (2) **upstream license compliance** — the pipeline's own SPDX normalization + license-map/seed-gap machinery is the compliance tooling, and BSI TR-03183 makes license fields part of conformant SBOMs. Feed-license hygiene: ecosyste.ms data is CC BY-SA 4.0 (share-alike — check before redistribution); OSV/GHSA/KEV/EPSS are openly licensed for reuse. _Sources: https://www.anaconda.com/legal/terms/terms-of-service ; https://ecosyste.ms/_

### Implementation Considerations

1. **CRA alignment is nearly free for this pipeline**: KEV/EPSS/Basilisk ingestion already produces the "actively exploited" signal class the Sep 2026 reporting regime turns on; emitting CycloneDX ≥1.6 with purls satisfies TR-03183-conformant SBOM expectations for downstream consumers. 2. **BOD 26-04's four-variable matrix** (KEV × automatability × exposure × impact) is a ready-made template for evolving the FR-18 policy gate's thresholds beyond max_critical/KEV — EPSS supplies the automatability proxy. 3. **NVD-gap hedging is a compliance issue too**: CRA-grade reporting needs enrichment NVD no longer provides — CISA Vulnrichment + CNA-native CVE 5.x fields are the free path. 4. Keep the pipeline's role honest: it is a *consumer/steward-support* tool, not a manufacturer — no CE-marking obligations attach to it. _Sources: https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act ; https://github.com/cisagov/vulnrichment_

### Risk Assessment

| Regulatory risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| CRA obligations misread as applying to the pipeline itself | Low | Low | § role clarity: consumer/steward-support tool; document the steward analysis |
| Downstream users demand CRA/TR-03183-grade SBOMs the pipeline can't emit | Medium | Medium | Already mitigated: CycloneDX 1.6+ w/ purls (FR-13); track 1.7 Citations adoption |
| Anaconda ToS enforcement against bulk data sourcing | Low–Medium | High (Phase F/B data supply) | S3-parquet + OCI-mirror fallbacks (already § 3.3); monitor ToS changes |
| CVE program disruption degrades all downstream feeds | Medium | High | Multi-feed redundancy (OSV+GHSA+EUVD+Vulnrichment) — § 13 matrix swappability |
| GDPR complaint over maintainer-identity processing | Low | Low | Public-source-only, minimization, legitimate-interest documentation |
