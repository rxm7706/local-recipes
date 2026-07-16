---
stepsCompleted: [1]
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
