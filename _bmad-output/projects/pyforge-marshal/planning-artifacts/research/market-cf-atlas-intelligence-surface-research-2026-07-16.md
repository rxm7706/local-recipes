---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - 'docs/specs/cfe-atlas-datapipeline-kedro-migration.md (v5.5)'
  - '_bmad-output/projects/local-recipes/planning-artifacts/research/domain-cf-atlas-domain-triad-research-2026-07-16.md (supply-side/competitive baseline — not re-plowed)'
  - '_bmad-output/projects/local-recipes/planning-artifacts/prfaq-cfe-atlas-kedro-migration.md (premise kill-test; customers + null alternative)'
workflowType: 'research'
lastStep: 5
research_type: 'market'
research_topic: 'Demand-side market research for the cf_atlas intelligence surface across the FULL Python packaging market: who consumes package intelligence spanning PyPI + conda ecosystems (pip, uv, conda, pixi manifests; PyPI, conda-forge, prefix.dev channels), what they need, and whether the three outward-facing productization scenarios (public dashboard / community conda-CVE-mapping feed / positioning vs Anaconda PSM) have real demand'
research_goals: 'Complete the analysis phase with the deferred MR instrument, scoped to what the domain research did NOT cover: (1) customer/user segmentation + needs — internal personas (operator, CFE agents, BMAD agents) and external segments (conda-forge maintainers, enterprise Python platform teams, security/compliance teams under CRA); (2) demand signals + willingness-to-adopt for the three deferral-trigger scenarios; (3) a now-vs-later verdict on whether any scenario changes the migration requirements. SCOPE AMENDMENT (user, step 1): the market is NOT conda-forge-only — most consumers straddle PyPI + conda; the manifest/tooling landscape spans pip and uv (PyPI side), conda and pixi (conda side), and prefix.dev as an alternate channel — segment and size demand across the full cross-ecosystem market, where the atlas cross-ecosystem identity layer is the differentiator. Explicitly avoid re-plowing DR supply-side ground (market sizes, vendor funding, competitor states).'
user_name: 'Rxm7706'
date: '2026-07-16'
web_research_enabled: true
source_verification: true
---

# Research Report: market

**Date:** 2026-07-16
**Author:** Rxm7706
**Research Type:** market

---

## Research Overview

Demand-side market research complementing the 2026-07-16 domain-research triad (which covered supply-side facts: market sizes, vendor funding, competitor states — deliberately not repeated here). Method: three parallel web-research streams executed 2026-07-16, each producing a cited, confidence-flagged report, synthesized below:

1. **Customer segments & behavior** — segment sizing (developer-survey package-manager shares, uv/pixi trajectories), current tool habits per segment, cross-ecosystem straddling evidence.
2. **Pain points & decision behavior** — documented complaints in scanner/ecosystem issue trackers, decision criteria, willingness-to-pay evidence, adoption triggers.
3. **Scenario demand** — demand proxies for the three deferral-trigger productization scenarios (A public dashboard, B community conda-CVE-mapping feed, C open Anaconda-PSM alternative) plus per-scenario time sensitivity.

Execution note: the first two streams were interrupted repeatedly by a transient API-overload window (529s, ~20:11–20:30 UTC) and completed on retry; no research content was lost (their transcripts confirm zero completed searches before the successful run). Confidence flags: HIGH = primary source verified; MEDIUM = credible secondary or partially verified; LOW = inferred/unverified. Every load-bearing claim below carries its source.

**Headline:** demand ranks the scenarios **B > C > A**. The community conda-CVE-mapping feed (B) has named, funded actors converging now, a 4-year downstream scanner backlog, an unclaimed funding lane, and a hard regulatory clock (EU CRA vulnerability reporting starts 2026-09-11 — 8 weeks out). None of the scenarios adds requirements to the migration now — the atlas's existing identity layer + FR-19 already cover what B needs; the only delta is an export surface, recorded as a candidate signal.

---

## Research Scope (step 1 — confirmed with user amendment)

**Confirmed scope** (2026-07-16): demand-side analysis for the cf_atlas intelligence surface across the **full Python packaging market** — consumers straddle PyPI + conda (pip / uv / conda / pixi manifests; PyPI / conda-forge / prefix.dev channels), so segmentation, pain points, decision behavior, and the three productization scenarios are analyzed cross-ecosystem, not conda-forge-only. The atlas's PyPI↔conda identity layer is treated as the differentiating capability under test. Supply-side facts stay referenced from the DR artifact. Per-step gates compressed at user direction ("let's just do market research to get a full analysis complete"); the completion gate presents everything.

---

## Customer Segments & Behavior (step 2)

### 2.1 The denominator: package-manager and manifest shares

- Python Developers Survey 2024 (JetBrains + PSF, 30,000+ respondents): dependency tooling **pip 74%** (down from 77%), Poetry 20%, **conda 18%**, **uv 12% in its first measured year** (released Feb 2024), pip-tools 9%, Pipenv 8%. Manifests: requirements.txt 63%, pyproject.toml 32%, setup.py 17%. _Source: https://lp.jetbrains.com/python-developers-survey-2024/_ — HIGH.
- Population scale: GitHub Octoverse 2025 counts ~2.6M monthly Python contributors (+48.8% YoY). _Source: https://octoverse.github.com/_ — HIGH.
- Sizing implication: the conda-side addressable base is single-digit millions of practitioners; the pip/uv side is 5–8× larger — MEDIUM (arithmetic on surveyed shares). Cross-ecosystem intake is therefore not optional for external relevance; it is where most of the market lives.

### 2.2 The uv adoption shock (manifest gravity)

- uv: 0 → 12% of surveyed developers in year one; ~28M → **~126–127M monthly PyPI downloads** by Feb 2026; GitHub stars 36K → 85K+. _Sources: https://pypistats.org/packages/uv, https://lp.jetbrains.com/python-developers-survey-2024/_ — HIGH.
- **OpenAI acquired Astral (uv/Ruff) for a reported $750M, announced 2026-03-19/20.** The dominant installer is now owned by an AI lab; community commentary immediately raised neutrality/lock-in questions. Tailwind inference for open, self-hosted, vendor-neutral intelligence infrastructure — LOW (inference), acquisition fact HIGH. _Source: https://simonwillison.net/2026/Mar/19/openai-acquiring-astral/_
- pixi: ~5,300 active projects (Sept 2025, prefix.dev-affiliated arXiv paper); 2–3 orders of magnitude smaller than uv but strategically positioned as the **only conda+PyPI-unified lockfile** (pixi.lock spans both ecosystems). _Sources: https://arxiv.org/html/2511.04827v1, https://prefix.dev/_ — MEDIUM.
- Net: manifest gravity is moving to pyproject.toml / uv.lock / pixi.lock fast, while requirements.txt remains the 63% long tail — lockfile-native intake (already the atlas's `scan-project` posture) matters more than requirements.txt polish. — MEDIUM (inference from HIGH survey data).

### 2.3 Segment-by-segment sizing and behavior

| Segment | Size proxy | How they answer intelligence questions today | Confidence |
|---|---|---|---|
| App developers (pip/uv) | 74% pip / 12% uv of ~2.6M monthly GitHub Python contributors | **Dependabot default-on** (~2.67M projects enabled, +24% YoY; dependabot.yml repos +137% YoY); Renovate off-GitHub/monorepo | MEDIUM (secondary compilations) |
| Data-science / ML teams (conda-heavy) | 51% of surveyed devs do data work; Anaconda claims 50M+ users (vendor upper bound); conda-forge crossed **1B monthly downloads Apr 2025** | **Largely nothing systematic** — scattered anaconda.org pages, status page, gists; no deps.dev equivalent exists for conda | HIGH (downloads), MEDIUM (behavior gap) |
| Enterprise platform teams | JFrog: 7,000+ customers, ~70% of Fortune 100, 1,168 >$100K ARR (FY2025); prefix.dev channel hosting GA Apr 2026 | Curation at the mirror boundary (Artifactory/Xray); natural buyers of staleness/vuln/license gates at that boundary | HIGH (JFrog investor filings) |
| OSS maintainers | PyPI ~690–830K projects; conda-forge **25,000+ feedstocks** (no verified maintainer totals — measurement gap) | pypistats/pepy + manual checks; conda-forge: autotick-bot PRs + status page (silent-failure caveats, § 3.4) | HIGH (counts), LOW (maintainer numbers) |
| Security/compliance teams | CRA vulnerability reporting applies **from 2026-09-11**; full application 2027-12-11; fines to €15M / 2.5% turnover | SBOM pipelines + commercial SCA; ENISA 2026: 78% have begun SBOM implementation, only ~9% automation-mature | HIGH |
| AI-agent developers (emerging) | MCP: ~97M monthly SDK downloads, 5,800+ community servers; package-intel MCP servers exist but fragmented, no dominant player | deps.dev / PyPI JSON via ad-hoc MCP servers | MEDIUM (aggregators), LOW (volume) |

_Sources: https://lp.jetbrains.com/python-developers-survey-2024/, https://octoverse.github.com/, https://conda-forge.org/blog/2025/04/11/ten-years-of-conda-forge/, https://investors.jfrog.com/news/news-details/2026/JFrog-Announces-Fourth-Quarter-and-Fiscal-2025-Results/default.aspx, https://sqmagazine.co.uk/github-statistics/, https://anchore.com/sbom/eu-cra/, https://www.enisa.europa.eu/publications/sbom-adoption-state-of-play-2026, https://registry.modelcontextprotocol.io/_

### 2.4 Tool-habit landscape (what incumbents own)

- **Habitual/default-on:** GitHub Dependabot (the median developer's "good enough"); Renovate (90+ managers, includes a **pixi manager** — the only mainstream tool that updates pixi.toml/pixi.lock). _Sources: https://docs.renovatebot.com/bot-comparison/, https://docs.renovatebot.com/modules/manager/pixi/_ — HIGH.
- **Habitual within niches:** deps.dev (free API, 50M+ versions, feeds OSV-Scanner/GUAC — **no conda coverage**); pypistats/pepy/ClickPy (maintainer download checks); endoflife.date (EOL windows); pip-audit (CI gate). _Sources: https://docs.deps.dev/, https://pypistats.org/_ — HIGH on deps.dev conda absence.
- **In flux:** **Snyk Advisor reportedly shutting down Jan 2026** (single secondary source, unverified against a Snyk announcement — MEDIUM) — would orphan the mass-market "is this package healthy?" page habit; libraries.io in maintenance, conversation moved to ecosyste.ms. _Sources: https://scanner.blacksight.io/blog/snyk-advisor-alternatives, https://packages.ecosyste.ms/_
- **Conda side:** no deps.dev equivalent exists; intelligence lives in the status page, anaconda.org, and gists. The conda side is materially underserved relative to PyPI. — MEDIUM (absence-of-evidence finding, consistent with DR).

### 2.5 Cross-ecosystem straddling evidence (the amended-scope question)

The user's scope amendment ("most people use conda-forge and pypi both") is confirmed by the best available data, with one caveat — the strongest number is four years old:

- **2022 conda community survey: 79% of conda users use other package managers; 75% of all respondents also use pip.** The single best direct datum; no newer public replication found. _Source: https://conda.org/blog/2022-03-30-conda-survey/_ — MEDIUM (primary, dated).
- Arithmetic corroboration: conda users (18%) are a strict subset of a 74%-pip population — pure-conda workflows are rare. _Source: https://lp.jetbrains.com/python-developers-survey-2024/_ — MEDIUM.
- The ecosystem's own stewards treat mixing as pervasive: conda.org's "Conda and pip are two ecosystems, not just tools" (May 2026) — qualitative, explicitly numberless (verified by fetch). _Source: https://conda.org/blog/2026-05-07-conda-and-pip-ecosystems/_ — HIGH as stance.
- pixi's design is itself market evidence: a conda-ecosystem tool whose lockfile resolves both ecosystems together. — MEDIUM.
- **Measurement gap the atlas could uniquely fill:** no published corpus study quantifies the share of environment.yml files with `pip:` sections. cf_atlas-style corpus analysis could produce the first such number. — LOW/unverified prevalence; the gap itself is verified-by-absence.

---

## Pain Points & Needs (step 3)

### 3.1 Conda packages are structurally invisible to mainstream vulnerability tooling

The gap is documented in every major scanner's own tracker — this is externally-validated demand, not assumption:

- **OSV:** osv-scanner#1129 ("Support conda environment files as lockfiles", July 2024) open, labeled `backlog`; **zero conda issues exist in ossf/osv-schema** — conda has never been formally proposed to OSV's ecosystem list. _Sources: https://github.com/google/osv-scanner/issues/1129, https://github.com/ossf/osv-schema_ — HIGH / MEDIUM (absence claim).
- **Syft/Grype:** anchore/syft#932 ("Conda ecosystem support") **open since March 2022**; anchore/syft#3395 — conda packages get **PyPI purls**, corrupting downstream CVE matching and SBOMs (direct external validation of the identity-layer need). QuantCo authored basic conda support (syft PR #4002) with the caveat it stays "minimum-effort" until conda decides its identity approach. _Sources: https://github.com/anchore/syft/issues/932, https://github.com/anchore/syft/issues/3395, https://github.com/anchore/syft/pull/4002_ — HIGH.
- **Trivy:** #1856 (conda lockfile support) **open since March 2022**, explicitly blocked on conda-forge CVE-mapping difficulty; environment.yml parsing shipped 2024 but vuln matching still missing; pixi.lock request (discussion #6860) stalled on "wait for upvotes." _Sources: https://github.com/aquasecurity/trivy/issues/1856, https://github.com/aquasecurity/trivy/discussions/6860_ — HIGH.
- **Dependabot:** #2227 ("parse conda env", **2018, 141 👍**) — 7 years of demand; conda GA finally shipped **2025-12-16** but is **version-updates only** — no security alerts (GitHub Advisory DB has no conda ecosystem), no solver awareness (grouped updates propose broken envs, #13813 filed by a conda-forge core dev), plus parsing bugs (#14054, #14085, #14458). _Sources: https://github.com/dependabot/dependabot-core/issues/2227, https://github.blog/changelog/2025-12-16-conda-ecosystem-support-for-dependabot-now-generally-available/, https://github.com/dependabot/dependabot-core/issues/13813_ — HIGH.
- **Why scanners fail on conda** (articulated pain): conda mixes C libraries, applications, and Python packages in one namespace; Python-only scanners are structurally insufficient (Turner-Trauring). Anaconda monetizes exactly this gap ("CVE association for conda-forge packages" is a paid feature). _Sources: https://pythonspeed.com/articles/conda-security-scans/, https://www.anaconda.com/blog/new-cve-association-for-conda-forge-packages-helps-secure-your-software-supply-chain_ — HIGH.

### 3.2 PyPI↔conda name-mapping is acknowledged unsolved infrastructure

- conda/grayskull#564 ("Tame the PyPI/Conda mapping chaos") documents multiple competing sources of truth; conda/conda-pypi#49 is the conda org cataloging the fragmentation; prefix.dev built parselmouth (hourly conda↔PyPI mapping) because pixi breaks without it; conda-lock#807 wants to migrate onto it; **PEP 804** (2025) elevates external-dependency name mapping to the python.org standards track. _Sources: https://github.com/conda/grayskull/issues/564, https://github.com/conda/conda-pypi/issues/49, https://github.com/prefix-dev/parselmouth, https://peps.python.org/pep-0804/_ — HIGH.
- Interpretation (MEDIUM): every existing effort maps *names* only. The mapping layer alone is becoming commodity; **mapping fused with vulnerability/staleness/health intelligence has no open incumbent** — that fusion is the atlas's differentiated position.

### 3.3 Manifest fragmentation and scanner support gaps

Teams straddling requirements.txt + environment.yml + pyproject.toml + pixi.toml get inconsistent partial coverage per file type. Current support matrix for the conda-side lockfiles (all HIGH, verified per-tool above): **Renovate: pixi yes** (only mainstream tool); **Trivy / Snyk / osv-scanner / Dependabot-security: no** (Snyk's documented workaround: convert environment.yml via dephell — an abandoned tool). A pixi team in 2026 has renovation but **no mainstream SCA scanner** that reads its lockfile. The atlas's `scan-project` manifest matrix (incl. pixi.lock, S5a) already exceeds mainstream SCA conda-side coverage.

### 3.4 conda-forge maintainer awareness pain

- Today's toolkit is push-based: autotick-bot version PRs + the status page, with documented silent-failure modes (bot stops at ≥3 open version PRs; "if you can't find a version, chances are the bot couldn't find it either"); QuantCo wrote a dedicated guide to debugging why updates *didn't* arrive. _Sources: https://conda-forge.org/docs/maintainer/updating_pkgs/, https://tech.quantco.com/blog/debug-feedstock-updates_ — HIGH.
- **Vulnerability awareness is essentially absent at the maintainer level**: no per-feedstock CVE feed exists in the open ecosystem; CVE association is an Anaconda commercial feature; conda-forge-as-CNA (QuantCo/prefix.dev proposal) is still aspirational. Maintainers get "new version exists" signals but no "your package is vulnerable / your dependents are affected / this migration will hit you" intelligence — exactly the atlas's staleness/health/whodepends/cve-watcher surface. _Source: https://tech.quantco.com/blog/conda-regulation-support/_ — MEDIUM-HIGH (gap inference from documented tooling).

---

## Decision Criteria, Willingness-to-Pay, Adoption Triggers (step 4)

### 4.1 Revealed preferences of the target population

- **Free/OSS-first with proven license-flight behavior.** Anaconda's 2024 ToS enforcement (200+-employee orgs must pay, exemptions narrowed, legal back-billing demands, Anaconda v. Intel) triggered a documented institutional exodus: Mass General Brigham removed Anaconda from HPC repos; CaRCC stood up an "Anaconda Transition Working Group"; miniforge is now the documented default at university HPC centers. Direction HIGH, scale unquantified (LOW). _Sources: https://www.theregister.com/2024/08/08/anaconda_puts_the_squeeze_on/, https://carcc.org/anaconda-transition-working-group/, https://www.fabriziomusacchio.com/blog/2025-07-03-miniforge/_
- **Price anchor:** Anaconda Business ~**$50/user/month** (Nov 2025 clarification; 15-seat cap before custom Enterprise); its security value-prop (curated conda CVE data) is a paid feature. _Sources: https://www.anaconda.com/pricing, https://pricingsaas.com/news/anaconda/20251118/_ — HIGH ($50), MEDIUM (seat details).
- **Data-licensing sensitivity is decisive:** the Safety→pip-audit episode (Safety's DB free for non-commercial only → ecosystem rallied to PyPA's Apache-2.0 pip-audit on open OSV data) is a direct warning for any restrictively-licensed intelligence data. _Sources: https://sixfeetup.com/blog/safety-pip-audit-python-security-tools, https://github.com/pypa/pip-audit_ — HIGH (license facts).
- **CI integration is table stakes** (every winning tool is adopted as a CI gate) — MEDIUM (qualitative, well-supported). **Self-hosted/air-gapped demand in regulated orgs is real** (documented offline modes in enterprise scan platforms; Artifactory-mirror routing) — MEDIUM. Both match the atlas's existing posture (offline-safe read CLIs, enterprise `_http.py` routing).
- Interpretation (MEDIUM): this population is hostile to per-seat licensing but demonstrably pays under compliance pressure — Anaconda's model works via legal risk, not product pull. Open-core/self-hosted positioning with compliance-grade outputs fits; per-seat SaaS does not.

### 4.2 Adoption triggers

- **Incident-driven:** xz-utils (CVE-2024-3094) — the canonical distro-layer blind spot of Python-only scanners; **Shai-Hulud (Sept 2025)** first self-replicating npm worm (500+ packages, CISA alert) and Shai-Hulud 2.0 (Nov 2025); PyPI-side: ultralytics (Dec 2024, malicious releases *with valid signed provenance*), GhostAction (Sept 2025, 3,300+ secrets). Registry compromise is now assumed when-not-if. _Sources: https://www.cisa.gov/news-events/alerts/2025/09/23/widespread-supply-chain-compromise-impacting-npm-ecosystem, https://blog.pypi.org/posts/2024-12-11-ultralytics-attack-analysis/_ — HIGH.
- **Regulation-driven (nearest catalyst — 8 weeks out):** EU CRA Art. 14 reporting starts **2026-09-11** (24h early warning / 72h notification / 14d final via ENISA's Single Reporting Platform) — you cannot report what you cannot see in your conda environments. ENISA's SBOM Adoption 2026 survey: **78% have begun SBOM implementation, 79% expect required maturity, only ~9% automation-mature** — a large gap between intent and tooling. _Sources: https://digital-strategy.ec.europa.eu/en/policies/cra-reporting, https://www.enisa.europa.eu/publications/sbom-adoption-state-of-play-2026_ — HIGH (existence/dates), MEDIUM (exact percentages, via secondary coverage).
- **Audit-driven:** weakest direct evidence (no survey found); proxies: law-firm CRA/NIS2 advisories, vendor compliance marketing, and Anaconda's enforcement letters functioning as audit events. — LOW-MEDIUM.

---

## Scenario Demand & Competitive Positioning (step 5)

Demand evidence ranks the three deferral-trigger scenarios **B > C > A**.

### Scenario A — public read-only dashboard: **weakest standalone**

Every durable comparable is an API/data business or vendor marketing, not a destination page: deps.dev is an API backbone (no conda coverage; no public traffic data); ClickPy is a subsidized ClickHouse demo; libraries.io effectively died and its founder's successor **ecosyste.ms** pivoted explicitly to "infrastructure for researchers, policymakers, developers, and funders" — open data + APIs, with a concrete institutional consumer model (Ecosystem Funds with Open Collective: $67.5K initial from Sentry, 375 payments to 136 projects allocated from dependency data). conda-forge's maintainer audience is already served by free in-community surfaces (status page, srdb.thath.net). **Unmet demand is for data/feeds, not pages.** A thin dashboard is nearly free as a *showcase* on top of B, worthless as the bet itself. _Sources: https://docs.deps.dev/, https://clickhouse.com/blog/clickpy-2-trillion-rows, https://blog.ecosyste.ms/2025/04/04/ecosystem-funds-ga.html_ — Verdict MEDIUM-HIGH.

### Scenario B — community conda-CVE-mapping feed: **clearest, most time-stamped demand**

- **SIG window open now:** prefix.dev's proposal (blog, Apr 2026) for a conda-forge Security SIG + open community CVE mapping ("shouldn't live behind any single vendor's walls"), explicitly seeking NumFOCUS + Alpha-Omega funding — **no evidence the SIG has formally constituted as of 2026-07-16** (no governance artifact, no SIG repo). Whoever shows up with working infrastructure during formation defines the feed's architecture. Adjacent activity is hot: wolfv's source-attestation CEP #168 updated 2026-07-15 — the day before this research. _Sources: https://prefix.dev/blog/securing-the-supply-chain, https://github.com/conda/ceps/pull/168_ — HIGH.
- **The bottleneck is the atlas's core competence:** three parallel purl CEPs (conda/ceps#63 since Nov 2023, #114, #159 — an Anaconda engineer's, Apr 2026), 2.5 years, none landed. Strong energy, weak throughput; the blocking problem is exactly the cross-ecosystem identity/purl normalization cf_atlas already does. _Sources: https://github.com/conda/ceps/pull/63, https://github.com/conda/ceps/pull/159_ — HIGH (facts), MEDIUM (strategic read).
- **Downstream consumers waiting 4 years:** Trivy #1856 (open since 2022, explicitly blocked on conda CVE mapping), Syft/Grype (QuantCo's minimum-effort PR pending identity decisions), OSV's conda absence (quiet precisely because matching is impossible without the identity layer landing first). — HIGH.
- **Funding lane precedented and unoccupied:** Alpha-Omega funds exactly this class (PyPI Safety Engineer, PSF Security Developer-in-Residence, ~$6M 2024 grants) — **no conda-specific grant found to date**; conda-forge is NumFOCUS-sponsored (fiscal home exists); QuantCo proposes conda-forge become a CNA partnering with prefix.dev. _Sources: https://alpha-omega.dev/grants/grantrecipients/, https://numfocus.org/project/conda-forge, https://tech.quantco.com/blog/conda-regulation-support/_ — HIGH.
- Verdict: **HIGH** — named, funded, currently-active demand-side actors; hard regulatory date; unclaimed funding lane; the technical bottleneck is what the atlas already built.

### Scenario C — open Anaconda-PSM alternative: **viable as narrative, trap as product**

The trust environment is genuinely favorable (2024 ToS exodus is durable; "not Anaconda" is now a purchasing criterion), but Anaconda's moat is **human curation** ("curation team reviews flagged packages… 7x more accurate" marketing) — an automated pipeline can beat them on coverage, freshness, and openness, not on curated false-positive suppression, and PSM buyers are buying the someone-to-blame layer. Asymmetry: the organizations that fled Anaconda (academia, non-profits, HPC) are exactly the ones that won't pay anyone — "open PSM alternative" converts trust into adoption, not revenue. **Works as the narrative wrapper around Scenario B's feed, not as a feature-parity clone.** _Sources: https://www.anaconda.com/blog/securing-the-open-source-pipeline-with-anaconda-cve-curation, https://carcc.org/anaconda-transition-working-group/_ — Verdict MEDIUM.

### Per-scenario time sensitivity

| Scenario | Time-sensitive? | Clock |
|---|---|---|
| A — dashboard | No — deferrable; crowded and static for years; deferring costs little | none |
| B — conda-CVE feed | **Yes, acutely, on two clocks** | (1) CRA Art. 14 reporting **2026-09-11**; (2) SIG-formation window — proposed Apr 2026, unconstituted, CEP activity deciding *now* (Jun–Jul 2026) |
| C — PSM alternative | Semi — trust window open, not closing fast; each month prefix.dev/QuantCo occupy more of the "open conda security" identity | soft |

---

## Completion Synthesis — verdict and implications for the migration spec

### Does any scenario change the migration's requirements NOW? **No new FRs. One candidate signal. Deferral trigger discharged.**

1. **Scenario B is time-sensitive, but its requirements are already in the spec.** What B needs from the pipeline — purl-normalized cross-ecosystem identity, conda-CVE association (FR-19 Basilisk conda-PURL vuln source), KEV/EPSS awareness, DuckDB-materialized mapping data — is the existing v5.5 scope. The only delta is an **export surface** (OSV-format / SIG-consumable feed of the atlas's conda-CVE mapping), which is a rider on B/D-wave outputs, not a pipeline requirement. Recorded as a § 12.1 candidate signal, activation-gated on the SIG actually constituting. The time-sensitive move is **operator engagement with the SIG** (show up with the identity layer as seed infrastructure) — an operator action, not a migration story.
2. **Scenario C requires nothing** — it is positioning language for whenever B's feed exists ("the open data layer the post-Anaconda world needs"). No spec impact.
3. **Scenario A requires nothing** — the D2 Vizro factory-status page already planned is the right-sized "showcase" surface; a public dashboard remains explicitly deferred (unchanged § 15 decision).
4. **The MR-deferral trigger from the spec's decision log is hereby discharged**: external productization was evaluated with real demand evidence; the internal-customers-first premise (operator + CFE/BMAD agents, per PRFAQ) **survives** — external demand exists but points at *data/feeds*, which the migration's data model already produces as a byproduct.
5. **Cross-ecosystem scope validated:** the user's amendment is empirically right — 75–79% co-use (2022 survey, arithmetic corroboration 2024), manifest gravity moving to uv.lock/pixi.lock, and the conda side having no deps.dev equivalent make the PyPI↔conda identity layer the confirmed differentiator. This strengthens (not changes) FR-19's cross-ecosystem framing and the § 13 matrix's Basilisk/parselmouth rows.

### New market facts worth § 12.1/§ 13 candidate consideration (from this MR)

- **OSV-format export of the conda-CVE mapping** (SIG-consumable feed) — the one actionable delta (above).
- **OpenAI acquired Astral (uv/Ruff), ~$750M, Mar 2026** — neutrality tailwind for self-hosted intelligence; watch for uv-ecosystem data-surface moves. — HIGH (fact).
- **Snyk Advisor reported shutdown Jan 2026** (MEDIUM, unverified) — if confirmed, orphans the mass-market package-health page habit; relevant only if Scenario A ever re-opens.
- **Dependabot conda GA (Dec 2025) is version-only, solver-naive, security-blind** — the "mainstream catches up" risk to atlas relevance did not materialize; monitor at wave gates. — HIGH.
- **Measurement gap the atlas could uniquely fill:** first corpus study of `pip:`-section prevalence in environment.yml files — cheap byproduct of existing corpus phases, publishable, SIG-relevant.

### Known gaps in this MR (flagged honestly)

No public active-maintainer counts (PyPI or conda-forge); no post-2022 conda/pip co-use survey; no quantified miniforge-migration scale; ENISA exact percentages via secondary coverage (spot-check the PDF before quoting externally); Snyk Advisor shutdown single-sourced; no quantitative self-hosted-vs-SaaS survey for regulated orgs.

### Analysis-phase status

With this MR, the analysis instrument set for the Kedro-migration spec is complete: corpus gap analysis, domain research (triad), technical research, adversarial review (27 findings), PRFAQ kill-test (CONDITIONAL PASS), and market research (this document). The spec (v5.5) needs at most a small fold from this MR (one § 15 decision-log row discharging the MR-deferral trigger + the § 12.1 candidate signal); requirements are otherwise unchanged. Next phase: Tier-2 intake (bmad-prd with the spec + PRFAQ distillate).
