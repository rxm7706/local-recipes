# Station Roster — 9 PyForge Stations

Tier 2 Pitch Expansion covers **9 pyforge stations**. This roster provides the thesis, pain point, solution pillars, visual metaphors, and personas for each station's pitch deck. The six-act framework and artifact structure (Design proto → markdown → PPTX → SVG → video) remain constant; content varies per station.

---

## Station Roster (9 Stations)

### 1. Marshal — Policy Composition at Scale

**Thesis**: A single source of truth for policy infrastructure, with automatic composition across repo defaults, team overrides, and CLI flags.

**Problem** (Friction):
- Policy configuration is scattered across 50+ YAML files per repository
- Changes require manual edits in multiple places; inconsistencies hide
- No composition layers (defaults, overrides, precedence)
- Rollback is error-prone; audit trails are missing

**Solution Pillars**:
1. **Unified Policy Root** — One canonical YAML source per policy (e.g., `policy-defaults.toml`)
2. **Four-Layer Composition** — Repo defaults → Team overrides → CLI flags → Runtime (deterministic precedence)
3. **Validation & Linting** — Schema validation + policy linting to catch conflicts before deploy
4. **Deployment** — Render composed policy to target (Kubernetes, Docker, systemd, etc.)

**Ecosystem Vision**:
- Policy composition spreads across the PyForge guild; every station adopts it for their config
- Cross-station policy coordination (e.g., shared security gates)
- Audit trail: who changed policy, when, and why

**Visual Metaphors**:
- **Friction act**: Photograph of engineer drowning in YAML files (humorous, real)
- **Insight act**: Nested boxes diagram (root → layers → composed output)
- **Solution act**: 4-step pipeline (Observe → Compose → Validate → Deploy)
- **Real-world act**: Production policy composition in a multi-team environment (screenshot of rendered policy)

**Personas**:
1. **Janssen, DevOps Engineer** — Manages policy across 10 teams. Wants consistency without manual overhead. Cares about policy audit trail and version control.
2. **Aaliyah, Platform Architect** — Designs cross-team standards. Wants composition layers to enforce policy hierarchy without duplicating YAML. Cares about scalability to 100+ teams.
3. **Kwon, Security Lead** — Reviews policy changes. Wants every policy change in git history, with computed audit. Cares about compliance and rollback capability.

**Deck Variants**:
- Main: Full policy composition story (28 slides)
- Cover: Policy composition in 90 seconds
- Extended: Deep-dive on composition layers, precedence rules, edge cases (40+ slides)

**Success Metrics**:
- [ ] Policy defaults adopted across 9 PyForge stations
- [ ] Manual policy edits reduced by 80%
- [ ] Policy composition engine proven and shipped
- [ ] Audit trail complete (git history + computed diffs)

---

### 2. Warden — Dependency Compliance as a Gate

**Thesis**: Scan Python/Conda/Pixi dependencies for known risks (security, licensing, supply-chain) and gate code at CI/CD time based on policy.

**Problem** (Friction):
- Dependency risks unknown until build time or production
- Security vulnerabilities buried in lock files; no gate to block them
- No audit trail of dependency decisions
- Compliance reviews are manual and slow

**Solution Pillars**:
1. **Multi-Axis Scanning** — Hygiene (deptry), security (osv-scanner + CISA-KEV + EPSS), licensing, currency
2. **Policy-Based Gates** — Flag-activated gates per axis; configurable by team or organization
3. **Baseline & Grandfathering** — Establish baseline for existing projects; grandfathering for accepted risks
4. **Audit Trail** — Every gate decision in git; computed impact reports

**Ecosystem Vision**:
- Warden becomes standard in PyForge CI; every PR passes dependency compliance
- Upstream projects adopt Warden for their own GitHub Actions workflows
- Cross-org compliance reporting (e.g., SLSA, CycloneDX)

**Visual Metaphors**:
- **Friction act**: Screenshot of CVE alert buried in build log (real, partially obscured)
- **Insight act**: Dependency graph with red nodes (risky deps); gate symbol before production
- **Solution act**: Multi-axis scanning (4 axes: hygiene, security, licensing, currency) flowing into gate decision
- **Real-world act**: Warden gate blocking a PR with an unsafe dependency; team reviews and makes decision (flow diagram)

**Personas**:
1. **Rosa, Platform Engineer** — Maintains 40 microservices. Wants dependency safety without friction. Cares about gate speed and developer experience.
2. **Malik, Security Lead** — Risk-averse. Reviews every high-risk dependency. Wants a gate, not a suggestion. Cares about blocking unsafe code before merge.
3. **Simran, License Compliance Officer** — Audits open-source usage. Wants automated license scanning + policy enforcement. Cares about GPL/proprietary category boundaries.

**Deck Variants**:
- Main: Full compliance gate story (28 slides)
- Cover: Dependency compliance in 90 seconds
- Extended: Deep-dive on SLSA, supply-chain security, multi-registry scenarios (40+ slides)

**Success Metrics**:
- [ ] Warden gates active in 20+ PyForge recipes
- [ ] 100+ risky dependencies caught before merge (annual)
- [ ] License compliance achieved for all Python/Conda dependencies
- [ ] Gate configuration standardized across teams

---

### 3. Atlas — The Catalog Beyond Python

**Thesis**: A unified dependency intelligence platform spanning Python (PyPI + conda-forge), npm, Rust (crates.io), and beyond. Single source of truth for cross-language dependency analysis.

**Problem** (Friction):
- PyPI universe is opaque beyond Python; ecosystem interdependencies invisible
- NPM packages depend on Python; Rust crates depend on Node; but no unified view
- Cross-language supply-chain attacks slip through single-language gates
- Roadmap visibility stops at language boundary

**Solution Pillars**:
1. **Multi-Language Ingestion** — PyPI, conda-forge, npm, crates.io, CRAN, CPAN, LuaRocks, GitHub (org audit)
2. **Unified Dependency Graph** — Cross-language edges; transitive dependency resolution across languages
3. **Metadata Normalization** — License, CWE, SPDX, version scheme, platform, archival status in a single schema
4. **Actionable Intelligence** — Trendshift detection, phase tracking (active/deprecated/end-of-life), adoption metrics

**Ecosystem Vision**:
- Atlas becomes the reference dataset for open-source ecosystem health
- Upstream projects query Atlas for their own dependency impact
- Enterprise environments integrate Atlas into supply-chain governance

**Visual Metaphors**:
- **Friction act**: Split-screen (PyPI alone on left, npm alone on right; no bridge)
- **Insight act**: Unified graph with language nodes (Python, npm, Rust, CRAN, CPAN) all converging on center
- **Solution act**: 4-phase pipeline (Ingest → Normalize → Graph → Query) flowing left-to-right
- **Real-world act**: Enterprise using Atlas to audit cross-language supply chain; detected hidden npm→Python dependency chain (flow diagram)

**Personas**:
1. **Keisha, Open-Source Steward** — Maintains 5 PyPI packages. Wants to see who depends on her code and their language. Cares about impact metrics and maintenance burden.
2. **Dmitri, Enterprise Architect** — Responsible for 1000+ packages across Python, npm, Rust, Java. Wants unified governance. Cares about supply-chain risk across language boundaries.
3. **Yuki, Data Scientist** — Uses multi-language stacks (Python + R + Rust). Wants to understand ecosystem health. Cares about library stability and update patterns.

**Deck Variants**:
- Main: Full multi-language ecosystem story (28 slides)
- Cover: Cross-language catalog in 90 seconds
- Extended: Deep-dive on Phase pipeline, data model, query API (40+ slides)

**Success Metrics**:
- [ ] Phase B–H shipped (PyPI universe complete, Kedro orchestrator, scheduler, telemetry)
- [ ] Cross-language dependency graph live (Python + npm + Rust initial coverage)
- [ ] 100+ external projects query Atlas monthly
- [ ] Trendshift detection live; 50+ trending packages identified monthly

---

### 4. Mason — Conda Recipe Lifecycle at Scale

**Thesis**: Autonomous recipe generation, validation, building, and submission to conda-forge for any PyPI, npm, CRAN, CPAN, or LuaRocks package.

**Problem** (Friction):
- Conda recipes are boilerplate-heavy; few people write them correctly
- Staged-recipes submissions fail on linter issues (missing selectors, old patterns, etc.)
- Recipe maintenance lags upstream (version pins drift; build failures are reactive)
- Cross-platform builds (osx-arm64, linux-aarch64) require manual tweaking

**Solution Pillars**:
1. **Template-Driven Generation** — Language-specific recipes (Python, Node, R, CPAN, Lua) from upstream metadata
2. **Validation & Linting** — Pre-flight checks catch staged-recipes rejections before submission
3. **Build Pipeline** — Local builds via rattler-build or conda-build; test matrix automation
4. **Submission Bot** — PR formatting, authored commits, bot commands for rerender and merge

**Ecosystem Vision**:
- Mason becomes the standard recipe generation tool; 90% of staged-recipes PRs generated via Mason
- Upstream projects use Mason to self-publish to conda-forge (one-click submission)
- Recipe maintenance becomes automatic (version tracking, dependency updates)

**Visual Metaphors**:
- **Friction act**: Photograph of dense conda recipe YAML (humorous, real)
- **Insight act**: PyPI package → Mason engine → recipe output (simple flow, 2px arrows)
- **Solution act**: 4-step pipeline (Generate → Validate → Build → Submit)
- **Real-world act**: Langflow suite shipped via Mason (8 recipes, cross-platform, zero manual edits)

**Personas**:
1. **Chen, Package Maintainer** — Maintains langflow on PyPI. Wants easy conda distribution without learning conda recipes. Cares about time-to-release.
2. **Amelia, Conda-Forge Contributor** — Reviews staged-recipes PRs. Wants recipes to pass lint first time. Cares about review time and pattern consistency.
3. **Marcus, Platform Engineer** — Runs internal conda-forge mirror. Wants recipes generated programmatically. Cares about reproducibility and audit.

**Deck Variants**:
- Main: Full recipe lifecycle story (28 slides)
- Cover: Recipe generation in 90 seconds
- Extended: Deep-dive on cross-platform selectors, pinning strategy, build failure recovery (40+ slides)

**Success Metrics**:
- [ ] 50+ multi-output recipes generated and shipped
- [ ] 90% of Mason-generated recipes pass staged-recipes lint on first try
- [ ] Langflow suite (8 recipes) shipped via Mason
- [ ] Recipe maintenance cycle reduced to 2–4 weeks (version lag eliminated)

---

### 5. Steward — Feedstock Maintenance at Scale

**Thesis**: Bulk refresh of conda-forge feedstocks: regenerate recipes to latest shape, widen build matrix, and handle platform expansion (osx-arm64, linux-aarch64) automatically.

**Problem** (Friction):
- 2000+ rxm7706-maintained feedstocks drift from conda-forge v1 best practices
- Manual platform expansion is tedious; new platforms missed per feedstock
- Version updates lag upstream; automation falls apart on edge cases
- Cross-maintainer coordination on bulk updates is chaotic

**Solution Pillars**:
1. **Bulk Audit** — Detect all feedstocks behind upstream version; assess v0 vs. v1 status
2. **Batch Regeneration** — Waves of feedstock updates (smallest first, risk tiered)
3. **Platform Expansion** — Automatically add osx-arm64, linux-aarch64 selectors; verify build matrix
4. **Coordination** — Track progress per wave; defer blockers; maintain git PR discipline

**Ecosystem Vision**:
- All rxm7706-maintained feedstocks current within 2 weeks of upstream release
- Platform coverage expands to 100% (no selective osx-arm64 gaps)
- Steward automation handles 80% of maintenance; humans review 20%

**Visual Metaphors**:
- **Friction act**: Chart showing 537 rxm7706 feedstocks with version lag (bars in red for >6mo behind)
- **Insight act**: Waves diagram (Waves A–H, each targeting 50–80 feedstocks, staggered over time)
- **Solution act**: 4-step per-feedstock loop (Detect Version → Regenerate → Platform-Expand → Submit PR)
- **Real-world act**: Steward running Wave C refresh (80 feedstocks updated in parallel, CI green for all)

**Personas**:
1. **Priya, Sole Maintainer** — Maintains 40 feedstocks alone. Wants bulk refresh without manual edits per feedstock. Cares about time savings and quality gates.
2. **Jude, Co-Maintainer** — Shares maintenance with 2–3 others. Wants coordination tools (progress tracking, PR templates). Cares about team synchronization.
3. **Sam, Conda-Forge Moderator** — Oversees quality of staged-recipes PRs. Wants bulk submissions to follow patterns consistently. Cares about linter compliance.

**Deck Variants**:
- Main: Full feedstock maintenance story (28 slides)
- Cover: Bulk feedstock refresh in 90 seconds
- Extended: Deep-dive on wave sequencing, error recovery, multi-maintainer workflows (40+ slides)

**Success Metrics**:
- [ ] 537 rxm7706 feedstocks audited; 179 confirmed behind upstream
- [ ] Wave A–F completed (257 feedstocks refreshed)
- [ ] Wave G–H scheduled (remaining feedstocks)
- [ ] Platform coverage expanded to 100% (osx-arm64, linux-aarch64 added)

---

### 6. Scribe — Capability Documentation

**Thesis**: Every station publishes a user guide, API reference, and operational runbook. Consistent documentation format, structure, and tooling across all PyForge surfaces.

**Problem** (Friction):
- Documentation scattered across README, sphinx, mkdocs, GitHub wiki
- No consistent structure; users get lost finding what they need
- Operational runbooks missing for new users
- Examples are outdated or missing

**Solution Pillars**:
1. **Unified Structure** — Getting Started → API Reference → Guides → Runbooks → FAQ
2. **Version Control** — Docs live in git; versioning matches releases
3. **Examples & Tutorials** — Tested examples (not screenshots) for every major feature
4. **Search & Navigation** — Unified search across all stations; breadcrumb navigation

**Ecosystem Vision**:
- PyForge documentation becomes a reference for open-source project docs
- One-stop shop for any station's capabilities (no hunting across three sites)
- Upstream projects adopt Scribe's template for their own docs

**Visual Metaphors**:
- **Friction act**: Screenshot of scattered docs (multiple browser tabs, different layouts)
- **Insight act**: Book icon or library diagram (unified shelves, all docs organized)
- **Solution act**: 4-doc pipeline (API Ref → Getting Started → Guides → Runbooks)
- **Real-world act**: User navigating unified docs, finding what they need in 30 seconds

**Personas**:
1. **Fatima, Software Engineer** — New to PyForge. Wants step-by-step getting started. Cares about examples that actually run.
2. **Rashid, DevOps Engineer** — Deploying a station to production. Wants operational runbooks. Cares about troubleshooting guides and alerting.
3. **Iris, Open-Source Maintainer** — Considering integrating a station into her project. Wants API reference and integration examples. Cares about version compatibility matrix.

**Deck Variants**:
- Main: Full documentation story (28 slides)
- Cover: Docs in 90 seconds
- Extended: Deep-dive on tooling (mkdocs, Sphinx), versioning strategy, localization (40+ slides)

**Success Metrics**:
- [ ] Getting Started published for all 9 stations
- [ ] API Reference complete for all 9 stations
- [ ] Operational Runbook published for all 9 stations
- [ ] Search active; users find docs in <2 minutes

---

### 7. Genesis — Bootstrapping New Stations

**Thesis**: A template and process for rapid iteration when creating a new PyForge station. Dream → Spec → Architecture → Epics → Stories → Implementation → Shipped in weeks, not months.

**Problem** (Friction):
- Creating a new station from scratch is slow (unclear starting point, no playbook)
- Design decisions re-hashed per station (policy composition, vendoring strategy, testing approach)
- Early design errors compound into large refactors late

**Solution Pillars**:
1. **Dream-First Process** — Start with a clear vision; Dream written before spec
2. **Spec Kernel** — 5-field kernel (Why, Capabilities, Constraints, Non-goals, Success Signal)
3. **BMAD Planning Chain** — PRD → Architecture → Epics → Stories (structured decomposition)
4. **Implementation Loop** — Story-driven dev; parallel story execution; gates at each milestone

**Ecosystem Vision**:
- Genesis becomes the standard bootstrap for any PyForge-family project
- External projects adopt Genesis playbook for their own multi-station initiatives
- New stations ship in 4–6 weeks (vs. 3–6 months ad-hoc)

**Visual Metaphors**:
- **Friction act**: Timeline showing old bootstrap (3–6 months, many false starts)
- **Insight act**: Flowchart (Dream → Spec → PRD → Arch → Epics → Implementation, clear steps)
- **Solution act**: 4-phase timeline (Vision → Planning → Execution → Launch)
- **Real-world act**: One station (e.g., Warden) bootstrapped via Genesis playbook; shipped in 5 weeks

**Personas**:
1. **Anika, Product Lead** — Proposes new PyForge station. Wants clear timeline and decision gates. Cares about predictability and scope containment.
2. **Diego, Tech Lead** — Leads implementation. Wants architectural clarity before coding. Cares about parallel story execution.
3. **Priya, Project Manager** — Tracks progress. Wants visible milestones and risk alerts. Cares about staying on schedule.

**Deck Variants**:
- Main: Full bootstrap story (28 slides)
- Cover: Station bootstrap in 90 seconds
- Extended: Deep-dive on BMAD method, story-driven dev, gate criteria (40+ slides)

**Success Metrics**:
- [ ] Genesis process documented and live
- [ ] Next 2 new stations ship via Genesis (on time, on budget)
- [ ] Bootstrap time reduced to 4–6 weeks
- [ ] 80%+ scope planned before implementation starts

---

### 8. Doctor — Quality & Testing

**Thesis**: Comprehensive testing infrastructure: unit, integration, e2e, performance, and security tests. Unified test reporting and gate automation across all stations.

**Problem** (Friction):
- Test coverage varies wildly per station (40%–95%)
- Test failures are sometimes mysteries (no clear error messages, no linked PRs)
- Performance regressions slip through (no baseline tracking)
- Security tests are manual or missing

**Solution Pillars**:
1. **Test Generation** — E2E test scaffolding for common station patterns
2. **Unified Reporting** — Test results aggregated, searchable, linked to code
3. **Performance Baseline** — Track latency, memory, throughput; alert on regressions
4. **Security Testing** — SAST (source), DAST (runtime), supply-chain (dependencies)

**Ecosystem Vision**:
- All PyForge stations reach 80%+ test coverage
- Test infrastructure becomes a reference for open-source projects
- CI gates become predictable; test failures are rare and quickly resolved

**Visual Metaphors**:
- **Friction act**: Matrix showing test coverage per station (many red rows for <50%)
- **Insight act**: Test pyramid (unit → integration → e2e, with counts per station)
- **Solution act**: 4-step test pipeline (Generate → Run → Report → Gate)
- **Real-world act**: Performance regression detected; owner notified; fix merged within 2 hours

**Personas**:
1. **Bianca, Quality Engineer** — Owns test strategy. Wants coverage goals and automation. Cares about early defect detection.
2. **Marcus, Ops Engineer** — Runs production instances. Wants performance baselines and regression alerts. Cares about uptime and latency SLOs.
3. **Kenji, Security Engineer** — Audits code and dependencies. Wants automated security scanning. Cares about CVE response time.

**Deck Variants**:
- Main: Full testing story (28 slides)
- Cover: Testing in 90 seconds
- Extended: Deep-dive on SAST/DAST, performance profiling, flaky test triage (40+ slides)

**Success Metrics**:
- [ ] All 9 stations at 80%+ test coverage
- [ ] E2E tests automated for 80%+ common use cases
- [ ] Performance baselines established and monitored
- [ ] Security test failures → fix in <4 hours (SLO)

---

### 9. Herald — The Factory's Voice

**Thesis**: Multi-moment proclamation system: Pitch (this dream), Progress (build telemetry as imagery), Success (release proclamation + evidence), Operations (deprecations & end-of-life notices). Decks, videos, dashboards, and release notes in a unified voice.

**Problem** (Friction):
- Engineering is invisible to stakeholders; shipping is not self-announcing
- Release notes are inconsistent tone; no visual summary
- Video content about features doesn't exist; docs-only is dry
- Operations updates (deprecations, EOL) are hidden in changelogs

**Solution Pillars**:
1. **Design-Code-Bridge** — Etagged round-trip between Design and Code; zero manual file transfers
2. **Deckcraft** — Markdown → editable PPTX; programmatic yet refinable
3. **Video-Scripts** — Extract narration; feed to Manticore; render videos from real footage
4. **Modernist Identity** — One visual language across all surfaces (decks, dashboards, videos, docs)

**Ecosystem Vision**:
- Herald becomes the factory's megaphone; every major milestone is pronounced
- Upstream projects adopt Herald's four-moment framework and visual language
- Engineers communicate impact through branded, visual, multi-format storytelling

**Visual Metaphors**:
- **Friction act**: Engineer at desk, work shipping silently (no one notices)
- **Insight act**: Megaphone icon; same work, now visible and loud
- **Solution act**: 4-moment timeline (Pitch → Progress → Success → Operations, each with artifacts)
- **Real-world act**: Moment 1 (this dream) deployed; 9 pitch decks live; team celebrating

**Personas**:
1. **Alicia, Executive Sponsor** — Funds PyForge. Wants clear demonstration of impact. Cares about user adoption and ROI.
2. **Joel, Open-Source Evangelist** — Promotes PyForge externally. Wants compelling decks and videos. Cares about narrative arc and authenticity.
3. **Tariq, Community Manager** — Engages users. Wants release-note templates and announcement images. Cares about engagement metrics.

**Deck Variants**:
- Main: Full proclamation story (28 slides)
- Cover: Herald in 90 seconds
- Extended: Deep-dive on four moments, design bridge, deckcraft pipeline (40+ slides)

**Success Metrics**:
- [ ] 9 Pitch Expansion decks shipped and live
- [ ] 4 Progress videos (per-quarter build telemetry)
- [ ] 2 Success proclamations (major release milestones)
- [ ] 12+ Operations updates (monthly deprecations, EOL notices)

---

## Pitch Expansion: Tier 2 Coverage

**Stations Included**: All 9 listed above (Marshal, Warden, Atlas, Mason, Steward, Scribe, Genesis, Doctor, Herald)

**Not Included in This Dream**: The 12 legacy/extended stations (deckcraft, design-code-bridge, modernist-identity, video-scripts, pyforge-herald as vision, etc.) are covered by separate Tier 1 capability dreams. Moment 1 Pitch Expansion focuses on the 9 core PyForge stations.

**Future Moments**: Moments 2–4 (Progress, Success, Operations) will orchestrate the same 9 stations using updated content, following the same workflow stages and artifact structure.

---

## Content Customization Worksheet

For each station, the deck author completes:

| Field | Marshal Example | Your Station |
|-------|-------------------|---|
| **Thesis** (1 sentence, noun phrase or imperative) | "Policy Composition at Scale" | _______ |
| **Problem** (1–2 sentences; quantified pain) | "47 YAML files, zero consistency, manual edits, error-prone rollback" | _______ |
| **Solution** (4 pillars) | (1) Root (2) Composition (3) Validation (4) Deployment | _______ |
| **Ecosystem Vision** (future state when this is standard) | "Policy composition spreads across PyForge guild; every station adopts it" | _______ |
| **Visual Metaphor** (Friction) | Engineer drowning in YAML files (humorous, real photo) | _______ |
| **Real-World Scenario** (concrete use case) | Multi-team policy coordination; shared security gates; audit trail | _______ |
| **Primary CTA** | github.com/pyforge-guild/marshal | _______ |
| **Persona 1** | Janssen, DevOps Engineer | _______ |
| **Persona 2** | Aaliyah, Platform Architect | _______ |
| **Persona 3** | Kwon, Security Lead | _______ |

**Deck Author**: __________  
**Design Reviewer**: __________  
**Subject Matter Expert**: __________  
**Estimated Content Time**: 4–6 hours per station  

---

## Delivery Checklist (Per Station)

- [ ] Thesis articulated
- [ ] Problem framing complete (quantified, real)
- [ ] Solution pillars clear and distinct (4–5 pillars)
- [ ] Visual metaphors identified (friction, insight, real-world)
- [ ] Personas written (1–4, with care-abouts and voting record)
- [ ] Real-world scenario grounded in specific context (not abstract)
- [ ] Slide outline complete (Cover → Acts I–VI → Appendix)
- [ ] Design prototype seeded in Claude Design
- [ ] Prototype reviewed by subject-matter expert
- [ ] Prototype approved for extraction (speaker notes complete, all slides drafted)
- [ ] Markdown extracted and committed
- [ ] PPTX generated and reviewed (fonts, colors, layouts)
- [ ] SVG infographics rendered (all inline, no raster)
- [ ] Narration script extracted (linter passes; voice brand check OK)
- [ ] HTML deck renders (dashboard-check passes)
- [ ] Video render queued for manticore
- [ ] Final commit + PR open
- [ ] CI green; merged to main

---

*Station roster is a living document. Update as station scope evolves.*
