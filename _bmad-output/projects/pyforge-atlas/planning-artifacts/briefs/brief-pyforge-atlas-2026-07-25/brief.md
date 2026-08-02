---
title: 'Product Brief: Atlas (pyforge-atlas)'
status: complete
created: 2026-07-25
updated: 2026-07-25
inputs:
  - 'docs/dreams/pyforge-atlas.md'
  - 'docs/dreams/pyforge-charter.md § 3 Atlas'
  - '_bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md'
  - '_bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md'
  - '_bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md'
  - '_bmad-output/projects/pyforge-atlas/planning-artifacts/research/domain-dependency-intelligence-ecosystem-observability-research-2026-07-25.md'
  - '_bmad-output/projects/pyforge-atlas/planning-artifacts/research/technical-kedro-dagster-duckdb-stack-currency-research-2026-07-25.md'
  - 'src/shared/packages/pyforge-atlas/ (shipped package — README.md, pyproject.toml, tests/)'
note: 'RETROSPECTIVE brief — Atlas shipped 2026-07-18 (32/32 stories, PRs #58-#105) before the factory adopted the research-first convention (2026-07-25 campaign). This brief backfills the missing product-brief tier and describes what was actually built and why it was worth building, grounded in the real, shipped evidence — it is not a pre-build planning input.'
---

# Product Brief: Atlas (pyforge-atlas)

> **Consolidated 2026-08-02** — see
> `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/briefs/brief-unity-data-stack-2026-07-25/brief.md`
> and
> `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/briefs/brief-wasm-analytics-stack-2026-07-25/brief.md`
> for the original standalone documents (moved there intact, not deleted).
> This brief now also carries the Unity Data Stack and
> Wasm Analytics Stack product briefs verbatim as `## Satellite:` sections
> below (per explicit user override of the dream-level-only consolidation
> convention — see `docs/dreams/pyforge-atlas.md` § *The estate Atlas hosts*
> and its Realization log). This document's own frontmatter `status:`
> continues to describe the primary Atlas brief only; each satellite section
> states its own status inline.

## Executive Summary

Atlas is the pyforge Guild's intelligence station: the conda-forge packaging factory's
data layer, rebuilt from a ~10,000-line hand-rolled orchestrator into a declarative
Kedro + Dagster + DuckDB pipeline that any autonomous agent — not just the one
developer who wrote it — can safely extend. The migration shipped **2026-07-18**,
**32 of 32 stories complete** across Waves 0 and A–H, merged through **PRs #58–#105**,
driven end-to-end by the `bmad-loop` orchestrator (Marshal). It replaced 23 cataloged
pipeline phases and 28 bespoke CLIs with **seven modular Kedro pipelines**, one
DuckDB-backed compute engine, a Boring Semantic Layer translating raw datasets into
named metrics, a Vizro/Vizro-AI read surface, and MCP/A2A machine interfaces — all
over a **19,726-feedstock** conda-forge population as of the spec's full-population
run. This brief is retrospective: Atlas already exists, is in daily use feeding the
`conda-forge-expert` skill's atlas-intelligence layer (staleness, feedstock health,
CVE watch, release cadence, adoption stage, migration readiness), and this document
grounds *why the bet was worth making*, not whether to make it.

## The Problem (as it stood before the migration)

The legacy `cf_atlas` orchestrator worked — it shipped real signal for years — but its
cost was **chronic, not acute**: every new phase hand-rolled its own checkpointing, TTL
gating, and backoff; data lineage lived in one developer's head; execution was
observable only via stdout; and ad-hoc questions required hand-written SQL against a
single SQLite file. The load-bearing failure mode, named explicitly in the PRD's PRFAQ
kill-test (CONDITIONAL PASS, 2026-07-16): **autonomous agents cannot safely extend a
10,000-line procedural monolith.** As the factory's actual workforce shifted from "one
developer occasionally touching this code" to "loop-driven BMAD agents adding phase 24
unattended," the monolith became the single biggest risk to the whole packaging
factory's autonomy story — not a performance problem, an *agent-maintainability*
problem.

## The Solution (what shipped)

Atlas replaced procedural call-order with a declared DAG, in three structural moves
validated against comparable dependency-intelligence platforms (domain research,
2026-07-25):

- **Seven domain pipelines, one producer per dataset** (Core; PyPI Intelligence;
  Vulnerability; VCS & Health; Universal SBOM; Seed-Gaps; Read-Surface/Derived-
  Artifacts) — every source and output is a `conf/base/catalog.yml` entry, credentials
  scoped per destination host (fixing, not porting, the legacy `_http.py` global JFrog-
  header-injection defect). This decomposition independently matches how ecosyste.ms
  and deps.dev structure their own much-larger cross-ecosystem graphs (typed,
  independently-versioned data services rather than one monolith) — convergent
  validation, not a novel bet.
- **DuckDB + Parquet as the compute singularity** (Neo4j/Kùzu/LanceDB/Polars all
  rejected as separate engines) — one engine for analytical compute, recursive-CTE
  graph traversal, and `vss` vector search, reading partitioned Parquet natively.
  `IncrementalParquetDataset` carries per-dataset TTL semantics (Phase D 7d, Phase P
  30d, EPSS 1d, CWE 90d, …) in one reusable class, deleting the bespoke `phase_state`
  checkpoint table entirely.
- **Dagster (via `kedro-dagster`) orchestrates; the Boring Semantic Layer (Ibis →
  DuckDB) is the one read-surface translation interface** — the 28 legacy CLIs became
  Vizro pages plus a Vizro-AI natural-language field and the `query_vizro_ai` MCP tool;
  23 of the 46 MCP tools in `conda_forge_server.py` were audited and re-authored over
  Kedro session/catalog APIs so agents trigger pipelines and read datasets without
  `kedro-mcp` ever being load-bearing.

Three new signal sources rode the migration as additive riders, never its
justification (PRFAQ discipline): **Basilisk** (conda-native vulnerabilities via
prefix.dev), **release-to-availability velocity** (median ≈ 8.9h, ~72.4% within 24h at
calibration), and **migration-readiness** classification (noarch / rebuild-done /
confirmed-pending / not-in-tracker) over conda-forge-bot-data's migration tracker.

## What Makes This Different

Atlas's "moat," to the extent an internal tool has one, is not novelty — the technical
research (2026-07-25) confirms every stack bet (Kedro, Dagster, DuckDB, Ibis/BSL,
Vizro, CycloneDX 1.7) remains actively maintained seven days after ship, with no
deprecations found. The one genuinely differentiated design choice is **scope
discipline**: unlike libraries.io, ecosyste.ms, or deps.dev — all general-purpose,
many-ecosystem platforms serving many outside consumers — Atlas is conda-forge-only,
by name in FR-15, serving exactly one operator and one agent workforce. That
narrowness is what let the whole migration ship as 32 stories in roughly a month
instead of an open-ended cross-ecosystem platform build, and it is a defensible choice
given Atlas's actual user base of one human plus the BMAD agent fleet — not a gap to
close later. The other genuine differentiator, validated against the domain research,
is that Atlas's **own freshness is a first-class, queryable signal**
(`staleness-report`/`behind-upstream` against per-dataset TTLs) — a property none of
the three external comparables expose about themselves to an outside observer.

## Who This Serves

- **The operator (rxm7706)** — maintains ~769-feedstock coverage without babysitting a
  monolith: watches a Dagster-rendered DAG instead of tailing stdout, re-runs only
  what's stale, and trusts that bad data halts (pandera contracts) instead of silently
  persisting.
- **`conda-forge-expert` authoring-agent sessions** — query package, vulnerability, and
  readiness intelligence through MCP tools with consistent semantics; receive
  structured signals via A2A (e.g., a Basilisk advisory hand-off to the recipe-
  authoring loop).
- **BMAD execution agents** (`bmad-loop` / `bmad-dev-auto`) — the load-bearing user:
  extend the pipeline by adding a node, declaring its datasets, and inheriting
  checkpoint/TTL/backoff/contract machinery for free, verified by deterministic
  fixture gates rather than tribal knowledge.
- **CI** — consumes one schema-validated artifact and one frozen exit-code gate
  (via the optional `pyforge-atlas[gate]` extra into pyforge-warden's
  `ComplianceReport`) instead of scraping 28 CLIs' text output.

This is explicitly an internal, non-commercial product — the PRD's own 2026-07-16
market research found "feeds > pages" demand (machine-consumable data over a public
dashboard), and the D2 "factory status" Vizro page is the intentionally narrow public-
facing surface, not a growth vector.

## Success Criteria (as delivered)

- **SM-1 (Parity before retirement):** the B4 attended parity gate reported zero
  material drift against the legacy `cf_atlas.db` on the `v_actionable_packages`-family
  views before the legacy orchestrator was retired.
- **SM-2 (Agent-maintainability — the load-bearing metric):** the three new-signal
  stories (Basilisk, velocity, migration-readiness) landed as nodes + catalog entries +
  pandera contracts with zero hand-written checkpoint/TTL/backoff code, and all
  loop-drivable stories executed under `bmad-loop` without any gate being weakened or
  removed to hit the target — the anti-metric (SM-C2) held.
- **SM-3 (Incremental re-materialization):** warm-incremental refresh re-runs only
  affected nodes; the F1 benchmark recorded both the warm-incremental win and the
  honest cold-full wall-clock against the network-bound 3–4h legacy baseline — the
  counter-metric (SM-C1) explicitly forbade over-claiming an engine-swap cold-start
  miracle, and the shipped evidence didn't chase one.
- **SM-4/SM-5 (Read-surface + agent-surface completeness):** every read-only legacy
  CLI question is answerable from a Vizro page or its FR-9-named exception artifact;
  `query_vizro_ai` is callable via MCP; the MCP trigger/read surface and the A2A
  payload hand-off both work end-to-end from a BMAD agent session.
- **All 8 per-epic retrospectives remain optional** (recorded in sprint-status, not
  gating) — the only formally open item against the shipped scope.

## Scope (what actually shipped, Waves 0 + A–H)

| Wave | Delivered |
|---|---|
| 0 | SKF legacy-translation skill (execution scaffolding) |
| A | nebi scaffold, data catalog (20 override points + credential scoping), `IncrementalParquetDataset` |
| B | Node ports (conda-side + PyPI/vuln), MCP audit, B4 parity sign-off, external-refresh assets, seed-gaps, SBOM intake, **Basilisk**, **velocity**, **migration-readiness** |
| C | Dagster compilation + schedules (`kedro-dagster`), `kedro-viz` |
| D | BSL models, Vizro dashboard (28 CLIs ported), Vizro-AI + MCP tool |
| E | A2A interface, OpenLineage + OpenTelemetry |
| F | DuckDB consolidation + benchmark, pandera validation hooks, `vss` similarity search, hygiene + policy gate |
| G | WASM/Pyodide portability, static Parquet host, Dagster sensors |
| H | Karpathy wiki scaffold + personas, agno crews, Wagtail/La Suite CMS sync, Dagster-triggered crews |

**Explicitly out of scope (spec § 12, held):** Neo4j/Kùzu/LanceDB/Polars as separate
engines; continued SQLite/`phase_state` orchestration; `spec-kit` as agent framework;
standalone binaries/JVM; new external data sources beyond the committed set (legacy
GitHub/PyPI/Anaconda + Basilisk + conda-forge-bot-data); a public OSV-format export
feed or public dashboard productization; rewriting the recipe-authoring skill itself.

## Vision (where it points next)

The PyForge Charter names Atlas's mandate as durable — "chart the dependencies, map
the world, define the floor" — and the shipped migration is the substrate the rest of
the Guild now builds on: Warden consumes Atlas's KEV/EPSS/Basilisk/velocity/mapping
data as one input to its compliance axes (one-directional data dependency, no code
import back), and any future PyForge Doctor fleet-health verb would query Atlas's
`feedstock-health`/`staleness-report`/`behind-upstream` surfaces directly rather than
re-deriving them. The domain research's one open question — whether an
OpenSSF-Scorecard-style maintenance signal (named as a vision-tier axis in the
Charter's Warden entry) belongs in Atlas as a joined feed or in Warden as a gate — is
recorded as a future-scope question, not a v1 gap: Atlas's own precedent (KEV/EPSS
joined, never re-scored) already answers *how* it would be built if evidence ever
gates it in.

## Open Questions (carried forward, none v1-blocking)

- Should Atlas ever expose a public, versioned API tier (deps.dev-style stable/alpha
  split) beyond today's MCP-tool-mediated agent access? Deferred — no evidence gates
  it yet, and the PRD's own promotion discipline requires measured evidence before any
  such FR is written.
- The 8 optional per-epic retrospectives remain the only recorded open item against
  the shipped 32/32 scope.
- `kedro-dagster`'s single-maintainer bus-factor risk (confirmed live by the
  2026-07-25 technical research, not just assumed) remains a watch item, not an
  active problem — the architecture's named exit ramps (Dagster Components, Kedro's
  Prefect deployer) are the standing mitigation if it deteriorates further.

## Assumptions

- No market-facing sections (TAM/pricing/GTM/competitive-share) — Atlas is an internal
  data platform with one human operator and an agent workforce as its only consumers,
  never sold, marketed, or positioned against libraries.io/ecosyste.ms/deps.dev, which
  this brief and its supporting domain research treat strictly as architectural
  reference points.
- **Retrospective grounding, not speculative planning**: every claim above is sourced
  from the shipped PRD/architecture/epics artifacts, the shipped package at
  `src/shared/packages/pyforge-atlas/`, and the two 2026-07-25 research reports — this
  brief backfills a missing tier for a project that shipped seven days before the
  research-first convention existed; it does not propose new work.
- Headless/express drafting: produced without an interactive discovery conversation,
  consistent with the other backfilled briefs in this campaign (Doctor, Herald, Mason,
  Scribe, Steward).

---

## Satellite: Unity Data Stack

> **Folded in verbatim 2026-08-02** from
> `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/briefs/brief-unity-data-stack-2026-07-25/brief.md`
> (status at fold-in: `draft`). Content below is unmodified from the
> standalone document; only this note and the heading level were added. See
> that archived path for the original file, including its own frontmatter.

### Product Brief: Unity Data Stack

#### Executive Summary

**Unity Data Stack is the conda-native, air-gap-first, spec-governed monorepo platform for
enterprise Python data engineering** — one shared repository where teams across an organization
co-contribute reusable templates, plugins, libraries, components, services, dashboards, reports,
and applications on a single opinionated toolchain. It is the **Inner-Source Model** made
concrete: open-source culture and practice, inside the firewall.

The enterprise problem it solves is not "we need a monorepo." It is that every team building
Python data products inside a large organization independently re-solves the same six problems —
how to resolve native dependencies, how to reproduce an environment offline, how to satisfy
supply-chain compliance, how to deploy to OpenShift, how to test across platforms, and how to let
another team contribute without breaking anything. Each team solves them slightly differently,
and the organization pays for the difference forever: in onboarding time, in audit effort, in
incompatible internal libraries that cannot be shared, and in the sheer cost of discovering that
your colleague already built this.

Three substantial artifacts already exist and were never landed in a repository: a **37 KB
Constitution** (spec-kit format — preamble, 14 articles, mandated standards), a **1,726-line
working pixi root** (~20 environments, ~200 tasks, feature-composed, four platforms), and a
**12 KB toolchain spec** (pixi orchestrator + PEP 751 `pylock.toml` + a five-role agent matrix).
Together they are a substantial but incomplete platform definition — genuinely good work, authored
2026-01 → 2026-05, now measurably drifted. This effort's job is to **absorb, correct, and
complete** them: keep what research confirms, fix what research falsifies, and supply what is
missing — principally the human contribution model, the provenance chain, and a resolved answer
to the one architectural question the gists never asked.

**Why now:** the **EU Cyber Resilience Act's vulnerability-reporting obligations begin
2026-09-11 — roughly seven weeks out** — with full obligations 2027-12-11. "Know what you ship,
continuously" stops being good practice and becomes a dated legal duty that propagates through
the value chain. Unity's compliance posture was designed before that clock was visible; it is now
the platform's sharpest justification.

#### The Problem

**Scenario 1 — the data engineer who cannot install her colleague's library.** She works in the
`customer` domain; a `cdo` team published something she needs. It depends on DuckDB, PyArrow, and
a PostgreSQL client. Her environment resolves *some* of that, then fails on an ABI mismatch. She
spends a day and gives up, then writes her own version. The organization now maintains two.

**Scenario 2 — the air-gapped deployment that works on the build machine.** A service builds
green in CI and fails behind the firewall, because the reproducibility guarantee covered the
Python packages and not the native ones underneath them. The team's fix is a bespoke vendoring
script that only they understand.

**Scenario 3 — the audit.** Someone asks: what open-source components are in the production
estate, at what versions, under what licences, and is anything in it being actively exploited
right now? Answering means a person walking N repositories with N conventions. Under CRA
reporting from 2026-09-11, that answer needs to be **continuous and evidenced**, not assembled on
request.

**Scenario 4 — the contribution that does not happen.** A developer sees a bug in a shared
library owned by another team. Contributing means learning their tooling, their branch model,
their review expectations, and finding someone with commit rights who cares. The realistic
outcomes are a ticket that ages, or a fork. **This is the innersource failure mode, and it is the
one the intake Constitution says least about.**

**The cost of the status quo** is mostly invisible because it is diffuse: no single team
experiences it as a crisis, and every team pays a tax. It surfaces as slow onboarding, as
duplicated internal libraries, as audits that take weeks, and as the quiet conclusion that
sharing code across teams is more trouble than it is worth.

#### The Solution

One opinionated shared monorepo, with the standards chosen *once*:

- **A pixi workspace as the substrate.** Features compose into named environments; the workspace
  resolves conda **and** PyPI packages together, so the native half of a data stack — DuckDB,
  Arrow, PostgreSQL clients, nginx, Node — is reproducible on the same terms as the Python half.
  Mirrors are environment-variable overrides, so the same manifest works on the open internet and
  behind Artifactory with no edit.
- **A machine-enforced Constitution.** Standards are not a wiki page; they are gates. `pixi run
  check-all` runs exactly what CI runs, so "it passed locally" is a guarantee rather than a hope.
- **Domain-owned data products.** Eleven tech domains own their assets under a
  Raw → Curated → Consumption layering with a fixed naming convention and declared data contracts,
  orchestrated by Dagster.
- **Compliance as an artifact, not an activity.** Every build emits a versioned CycloneDX
  Software Bill of Materials (SBOM)
  (runtime-scoped and full), continuously gated against actively-exploited-vulnerability data.
- **Contribution designed in.** A named trusted-committer role, a documented path for a team to
  contribute to code it does not own, and templates that make starting the right way easier than
  starting the wrong way.

**Crucially, Unity assembles far more than it invents.** This repository already contains
realized capability covering much of the intake spec's ambition: **pyforge-warden** (multi-axis
compliance gate with CISA-KEV and EPSS exploitation gating — complete, merged 2026-07-25);
**conda-forge-expert** and 769 maintained feedstocks (the conda-native package supply);
**enterprise-airgap** doctrine (JFrog routing, offline-first design); **pyforge-atlas**
(dependency intelligence). Unity is principally an **integration and governance** effort that
binds these into a coherent platform — plus genuinely new work on the workspace/lock architecture,
the governance split, and the contribution model.

#### What Makes This Different

The wedge is a conjunction; three qualifiers remove an incumbent, one aligns rather than competes:

| Qualifier | Removes | Because |
|---|---|---|
| **conda-native** | Pants, Bazel, Nx | They own the build graph brilliantly — and resolve *wheels*. The native components a data platform is made of are outside their guarantee. |
| **air-gap-first** | SaaS IDPs, Nx Cloud | A posture designed in, not a deployment mode bolted on. |
| **spec-governed** | — (aligns) | The Constitution is already in spec-kit format; spec-kit is at **123.7k stars** (2026-07-25), ~3.6× Backstage's 33.9k — an adoption signal for the format, not proof of fit. |
| **monorepo *platform*** | Backstage | A portal *describes* an estate. Unity *builds* one. Unity should be catalog-**able**, not a catalog. |

Research found no named competitor occupying all four simultaneously — but web-search discovery
was unavailable (budget exhausted), so the comparable set was assembled from directly-fetched
sources and completeness is **not** claimed. A 2026-launched competitor could exist and be absent
(Open Question M1 — full list at the end of this document).

**The honest moat is not technical novelty — it is accumulated integration.** Nothing here is
individually impossible. What is hard to copy is that the conda-forge supply chain, the compliance
gate, the air-gap routing, and the dependency intelligence already exist, in one place, working.

#### Who This Serves

**The domain data engineer (primary).** Wants to ship a data product, not administer a toolchain.
Success: `pixi install && pixi run dev`, and a colleague's library installs on the first try.

**The platform team (primary).** Owns the shared substrate for everyone else. Success: they set a
standard once and it holds, without policing it by hand.

**The trusted committer (primary — and currently unnamed).** Reviews and accepts contributions
into shared code from teams that do not own it. **The intake Constitution requires "at least one
human approval" and never says whose.** For a platform whose entire premise is cross-team
co-contribution, this is the largest substantive gap in the intake set — found independently from
two research angles (innersource practice; the agent role matrix's missing feedback-loop
stations). Success: a contribution from outside the owning team lands in days, not quarters.

**The compliance officer (secondary).** Needs to answer, continuously and with evidence, what is
in the estate and whether it is being exploited. Success: the answer is a generated artifact.

**The platform operator / Steward (secondary).** Deploys to OpenShift behind a firewall.
Success: air-gapped deployment is the ordinary path, not a project.

#### Success Criteria

| # | Signal | Measure |
|---|---|---|
| S1 | **Onboarding** — clone to running local stack | Single-digit commands, under an hour, no tribal knowledge |
| S2 | **Cross-team reuse** — the innersource proof | Contributions merged into code the contributor does not own, trending up; forks-of-internal-libraries trending down |
| S3 | **Local↔CI fidelity** | `pixi run check-all` passing locally predicts CI passing (target: near-total; measured as green-local/red-CI rate) |
| S4 | **Reproducibility** | The same lock reproduces on all supported platforms *and* offline — verified by a gate, not asserted |
| S5 | **Compliance latency** | Time from CVE publication to "we know whether we are affected" measured in minutes; exploited-vuln reporting evidence available on demand (CRA 2026-09-11) |
| S6 | **Air-gap parity** | Every capability available offline that is available online; parity verified, not assumed |

`[ASSUMPTION]` S1–S6 are the right *dimensions*; specific numeric thresholds are deliberately
deferred to the PRD, where they can be set against a real baseline rather than invented here.

#### Scope

##### In — v1

- **The workspace substrate**: pixi root, feature/environment composition, per-package manifests,
  supported-platform matrix, `[system-requirements]` floors.
- **A resolved lock architecture** — the decisive open question (see below).
- **The quality gate**: `check-all` parity with CI; lint / format / type / security; pre-commit.
- **The Constitution, corrected and machine-checkable**, with a stated global-vs-local governance
  split.
- **The contribution model**: trusted-committer role, review path, templates, onboarding docs.
- **The compliance chain**: versioned CycloneDX (1.7 / ECMA-424), SLSA (Supply-chain Levels for
  Software Artifacts) provenance, continuous
  exploited-vulnerability gating — by **integrating pyforge-warden**, not reimplementing it.
- **Air-gap posture**: env-var-only mirror routing, no credentials in URLs, offline bundle path.
- **One reference domain, end to end** (`customer`), proving the domain pattern.

##### Out — v1 (explicitly)

- **Being an IDP.** No catalog UI, no service registry. Emit catalog-consumable facts; integrate
  with Backstage if an adopter runs one.
- **A build-graph engine.** No attempt to out-cache Pants or Nx. Orthogonal and unwinnable.
- **The remaining ten tech domains.** The working root marks all eleven as "scaffolding only" with
  one reference implementation. `[ASSUMPTION]` v1 delivers the *pattern* plus one worked domain;
  the other ten are adoption work, not build work — this changes effort by an order of magnitude
  and must be confirmed in the PRD (research OQ-D10).
- **Deprecated/excluded services**: airflow-server (SQLAlchemy <2.0 conflict with Dagster),
  sharepoint-mcp-server (pyjwt conflict) — documented as excluded, with reasons.
- **SLSA L3.** L1 mandatory, L2 target; hardened builders are out of v1 reach.
- **Commercialization.** Unity is a platform an enterprise runs, not a product sold.

##### The decisive open question

**Is `pixi.lock` the source of truth with `pylock.toml` derived, or the reverse?** The two intake
gists answer differently and neither notices the conflict: the working root is a pixi workspace
(`pixi.toml`, conda+PyPI, `src/…` layout); the toolchain spec is a PDM workspace
(`pyproject.toml`, PEP 751 only, `apps/` + `libs/`) with a **Zero-State rule** that production
must boot from `pylock.toml` *alone*.

They cannot both hold: PEP 751 is a *Python package* lockfile and cannot express the native half
of a data stack. (Mechanics — the layout conflict, the Dockerfile's silent switch away from conda
at deploy time, the three candidate resolutions — are in `addendum.md` § D.2–D.3.)

`[ASSUMPTION]` **pixi-primary**: `pixi.lock` is the source of truth, `pylock.toml` is a derived
export for PEP 751 consumers, and offline deployment uses `pixi-pack` / `pixi-unpack` — both
already present in the working root. Rationale: conda-native is the differentiator, and the
alternative discards it. **This is an architecture decision, not a brief decision** (OQ-D8) —
flagged here because everything downstream depends on it.

#### What Research Changed

Eight verified deltas against the intake artifacts. Full detail in the research reports; the
load-bearing ones:

| Finding | Grade | Consequence |
|---|---|---|
| `pdm export --override-platform` **does not exist**; the format token is `pylock.toml` | **WRONG** | The toolchain spec's flagship `lock-monorepo` task is unimplementable as written |
| PEP 751 does **not** guarantee multi-platform lockfiles — it uses environment markers | **Wrong** (scope) | Multi-platform coverage must be *verified*, not assumed. Compounds with the above: the "Cryptographic Predictability" outcome currently has **no verified mechanism** |
| pip's `pylock.toml` support is **experimental** (25.1 `pip lock`, 26.1 `-r pylock.toml`) | **Risk** | The Zero-State rule rests on an experimental feature; needs a fallback |
| **SLSA provenance is entirely absent** from the intake set | **Gap** | SBOM says what is *in* the artifact; nothing says how it was built. L2 is cheap on hosted CI |
| **No trusted-committer role**; three crew stations (Herald/Doctor/Scribe) unmapped in the role matrix | **Gap** | The human layer is systematically under-specified — see *Who This Serves* |

Three further staleness findings — pixi pinned at `==0.59.0` against a current 0.73.0; Dagster
1.13.15 now supporting Python 3.14; Python 3.12 gone security-only with 3.15 landing 2026-10-01 —
are supporting evidence rather than decision drivers. Detail in `addendum.md` § C.4 and the
research reports.

**Confirmed and kept:** PEP 751 is Final (2025-03-31); the pixi feature/environment model;
the air-gap env-var override design; conda-native as the differentiator; the Constitution's
spec-kit format; Data Mesh principles 1 (domain ownership) and 2 (data as a product) are faithfully
implemented in Article VII.

**In tension:** Data Mesh principle 4 (*federated* computational governance) versus a Constitution
declaring itself "immutable" and "non-negotiable." The *computational* half is done well — policy
is genuinely automated. The *federated* half is missing: there is no concept of a domain-local
exception. Resolving which mandates are platform-wide invariants and which are
domain-overridable defaults is both a Data Mesh requirement and the mechanism that keeps Unity
*innersource* rather than *centrally imposed* (research OQ-D7).

#### Vision

**In two to three years**, Unity Data Stack is what "we build data products here" means at an
adopting enterprise. A new engineer's first day is a clone and a command. A team that needs
something asks whether it exists before building it, and usually it does. Contributing to another
team's library is ordinary. Compliance evidence is a build output nobody thinks about until an
auditor asks and it is already there.

Beyond one enterprise: **pyforge-genesis** bootstraps Unity instances (`genesis init` /
`genesis adopt`), so the platform is reproducible across organizations rather than a bespoke
build each time; the **pyforge crew** (Herald · Marshal · Atlas · Warden · Mason · Doctor ·
Scribe · Steward) operates it, mapping cleanly onto the toolchain spec's five roles and supplying
the three feedback-loop stations the spec omitted. Unity becomes a reference answer to *"what
does a Python data platform look like inside a regulated enterprise in 2027?"* — with the
compliance chain, the air-gap posture, and the innersource contribution model as the parts other
organizations copy.

---

##### Open Questions Carried Into the PRD

Consolidated from both research reports; ordered by decision urgency.

| ID | Question | Owner | Resolution path |
|---|---|---|---|
| **OQ-D8** | pixi-primary, pylock-primary, or split-by-tier? *Everything downstream depends on this* | Architecture | **Resolve first** |
| **OQ-M7** | `pdm lock --platform` + export, or `uv export --format pylock.toml`? | Architecture | Trade-off study |
| **OQ-M4** | Where is the boundary between spec-kit governance and BMAD planning? Both are active here | PRD | Decision |
| **OQ-M5** | What is Unity's trusted-committer-equivalent role? *("-equivalent" is deliberate: whether Unity adopts the InnerSource Commons role as-is or adapts it is itself part of the question)* | PRD | Decision |
| **OQ-D7** | Which mandates are platform-wide invariants vs domain-overridable defaults? | PRD | Decision |
| **OQ-D10** | Which of the 11 tech domains are real vs aspirational? *Order-of-magnitude sizing impact* | PRD | Decision |
| **OQ-D4** | Warden integration boundary — library, CLI, CI action, or MCP tool? | Architecture | Trade-off study |
| **OQ-M8** | Preview `pixi-build` workspaces, or editable path installs? | Architecture | Trade-off study |
| **OQ-M11** | Should the 12-stage SDLC be pixi environments at all? (5 are byte-identical; 3 more are `["runtime"]`) | Architecture | Decision |
| **OQ-D5** | Does `sbom4python --requirement pylock.toml` emit a dependency *graph* or a flat list? | Architecture | Empirical test — cheap, do early |
| **OQ-D6** | Target SLSA level for v1? (recommend L1 mandatory / L2 target) | PRD | Decision |
| **OQ-D3** | Exact CRA Annex I wording — is SBOM actually required, or inferred? | Compliance | Verify before citing CRA as authority |
| **OQ-M10** | Is `linux-aarch64` in scope for v1? The two gists disagree on the platform matrix | PRD | Decision |
| **OQ-D9** | Does the data-classification axis need enforcement (PII masking, access control) or is it documentation? | PRD | Decision |
| **OQ-M9** | Is conda-forge's dagster built for Python 3.14? | Architecture | Verify before pinning |
| **OQ-D1** | Current OCP version / Kubernetes baseline / EUS lifecycle? (`docs.redhat.com` returned 403) | Architecture | Verify before pinning |
| **OQ-D2** | Does `osv-scanner` cover `pylock.toml` / `pixi.lock` / conda? | Architecture | Verify at Warden integration |
| **OQ-M1** | Is the comparable set complete? Web-search discovery was unavailable | Research | Re-run when budget allows |
| **OQ-M2** | Does *every* mandated component exist on conda-forge, on every target platform? | Research | Bulk `cf_atlas` query when available |
| **OQ-M3** | Express the role matrix as a spec-kit *bundle*? | Architecture | Trade-off study |
| **OQ-M6** | Independent 2025/26 innersource adoption data to ground the value claim? | Research | Follow-up |

**Companion artifacts:** the two research reports named in this brief's frontmatter `inputs:`
are still at their original, unmoved paths (`research/*-2026-07-25.md`); `addendum.md` (intake
inventory and detail deferred from this brief) moved intact 2026-08-02 to
`archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/briefs/brief-unity-data-stack-2026-07-25/addendum.md`
alongside the standalone `brief.md` this fold-in copied from — this fold-in copies only the
rendered `brief.md` text, not the addendum.

## Satellite: Wasm Analytics Stack

> **Folded in verbatim 2026-08-02** from
> `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/briefs/brief-wasm-analytics-stack-2026-07-25/brief.md`
> (status at fold-in: `draft`). Content below is unmodified from the
> standalone document; only this note and the heading level were added. See
> that archived path for the original file, including its own frontmatter.

### Product Brief: Wasm Analytics Stack

#### Executive Summary

Wasm Analytics Stack is a modern analytical data pipeline — ingest via **dlt**,
transform via **dbt-duckdb**, observe via native **OpenTelemetry** tracing and
**OpenLineage** provenance — built to run natively hardened on Red Hat OpenShift
under **Restricted SCC** (non-root UID 1001, read-only rootfs), with one **Pixi**
toolchain bridging local development, Podman "digital twin" verification, and
production OCP, all validated through the same command path before a single line
ships to a cluster.

Its differentiating bet, carried from the April 2026 architecture gist that seeded
this Dream, is that the analytical/validation logic sitting closest to untrusted
input (the seed use case: a user-uploaded Excel file, ingested via FastAPI) runs
inside a genuine **WASI Preview 2 sandbox**, not just an OCP-hardened process — a
second, language-level isolation boundary underneath the platform-level one.
**[ASSUMPTION]** This is the Dream's most novel claim and, per the technical
research completed alongside this brief, the one requiring the most honesty: the
WASI-component ecosystem has matured meaningfully since April 2026, but the
specific dependency this project's seed use case needs most — DuckDB's native
engine, inherited by both `dlt`'s DuckDB destination and `dbt-duckdb` — has **no
WASI build and no WASI roadmap anywhere upstream**. The brief below scopes V1
around what the research shows is actually buildable today (a narrow,
pure-Python WASI validation layer plus a conventionally-hosted DuckDB pipeline),
rather than repeating the gist's un-re-verified "Python-Wasm validates via Arrow
buffers" step as settled fact.

The product exists because two things are already true in this workspace and
nowhere else combines them: (1) a shipped, in-repo proof that Python analytical
logic *can* run zero-backend in a WASM-family sandbox — `pyforge-atlas` story G1
(DuckDB-WASM + Pyodide, browser-side, merged PR #96, 2026-07-18) — and (2) a
fully-specified, OCP-hardened enterprise deployment posture already documented for
this repo's other projects (`docs/dreams/enterprise-airgap.md`,
`docs/reference/enterprise-deployment.md`). Wasm Analytics Stack is the first
project to combine both: a real data pipeline, not a read-only dashboard, running
under the strictest OCP security profile, with Wasm sandboxing applied exactly
where the research shows it is defensible today.

#### The Problem

Enterprises running regulated or hardened Kubernetes/OpenShift environments face a
specific, recurring tension when they want to let less-trusted logic (a
user-uploaded file, a third-party transformation rule, an analyst's ad hoc
validation script) into an otherwise locked-down data pipeline:

1. **Restricted SCC gives you process isolation, not code isolation.** A pod
   running as non-root UID 1001 with a read-only rootfs is meaningfully hardened
   against *escape*, but the Python process inside that pod still has the full
   language surface available to anything that runs inside it — there is no
   second boundary between "the pipeline's own trusted code" and "logic derived
   from a file a user just uploaded." **[ASSUMPTION]** This is the gap the Dream's
   WASI-sandboxing bet targets; the domain research below confirms other
   production platforms (Shopify Functions, Fermyon Spin) solve exactly this
   problem by compiling the untrusted-input-adjacent logic to a Wasm sandbox with
   its own, narrower capability grants — a pattern this project can adopt.
2. **Observability and lineage are usually bolted on, not native.** Data teams
   commonly wire OTel tracing and OpenLineage provenance in after the fact, per
   pipeline, inconsistently. The cost is invisible until an audit or an incident
   needs the trace and it doesn't exist end-to-end (browser upload → API →
   ingestion → transform).
3. **Local dev, container verification, and production drift apart.** Without one
   toolchain spanning all three, "works on my machine" and "works in the OCP
   digital twin" and "works in the actual cluster" are three separate, drifting
   claims. The gist's own framing ("Pixi bridging local dev, Podman digital twins,
   and production OCP") names this directly.

The cost of the status quo: teams either accept the weaker isolation (trusted-code
and untrusted-input-derived-code share one process boundary) or hand-roll a
sandboxing layer per project, with no shared toolchain, no shared observability
convention, and no shared "verify locally the same way CI/prod will" loop.

#### The Solution

A layered pipeline, scoped to a single, concrete seed use case first (per the
Dream): a user uploads an Excel file; FastAPI (OIDC-protected) receives it; a
narrow, pure-Python validation stage — compiled via `componentize-py` to a real
WASI Preview 2 component and run under Wasmtime — checks the file's structure and
data quality before anything else touches it; `dlt` then ingests the validated
rows into a DuckDB **Bronze** table; `dbt-duckdb` transforms Bronze → Silver →
Gold with column-level lineage; every stage emits OTel spans and OpenLineage
facets to a Vector sidecar / Marquez, respectively; the whole thing runs identically
under `podman --read-only --user 1001` locally and under OpenShift Restricted SCC
in production, driven by one Pixi toolchain (`pixi run build`, `pixi run test`,
`podman-compose up` for the digital twin).

**[ASSUMPTION] The one deliberate correction to the April 2026 gist, driven by
this brief's research:** the gist's step 2 ("Python-Wasm module validates data
quality via Apache Arrow in-memory buffers") is scoped down. The WASI component
validates using plain Python data structures (rows/dicts, or a pre-parsed scalar
representation) — not Arrow buffers, and not anything touching `numpy`/`pandas`
inside the sandbox — because the research found no working `pyarrow`-in-WASI
precedent anywhere (zero GitHub issues even attempting it) and no Arrow-maintained
WASM/WASI interchange primitive to build on. `dlt`'s ingestion and `dbt-duckdb`'s
transform stay conventional, sandboxed-by-OCP-process (not by Wasm), because
DuckDB's native engine has no WASI build. This is a smaller claim than the gist
made, but a claim this project can actually ship and defend.

#### What Makes This Different

| Dimension | Generic OCP-hardened data pipeline | Browser-only Wasm analytics (e.g. plain DuckDB-WASM dashboards) | **Wasm Analytics Stack** |
|---|---|---|---|
| Process-level hardening (Restricted SCC) | ✓ | N/A (client-side) | ✓ |
| A second, code-level sandboxing boundary around untrusted-input-adjacent logic | ✗ | N/A | ✓ (WASI component, scoped to pure-Python validation) |
| Native OTel + OpenLineage, not bolted on | Varies | ✗ | ✓ |
| One toolchain: local dev = digital twin = production | Varies | N/A | ✓ (Pixi + Podman + OCP) |
| Honest about Wasm ecosystem maturity for the data-stack dependencies (DuckDB, dbt, dlt) | N/A | N/A | ✓ (this brief scopes to what's provably buildable, not the full April-2026 gist claim) |

**[ASSUMPTION]** There is no technology moat here in the sense of a novel
algorithm; the differentiation is disciplined scoping — building the part of the
"Python-in-Wasm for data" story that the ecosystem actually supports today (a
narrow validation-layer sandbox, per the domain research's Shopify-Functions/
Fermyon-Spin comparables), instead of over-claiming the part it doesn't (a fully
Wasm-sandboxed DuckDB pipeline). The honest framing is itself the pitch: most
"Wasm-first data stack" narratives in 2026 (including this project's own seed
gist) understate how far C-extension-heavy data libraries lag pure Rust/JS
Wasm-sandboxing use cases — this project is built with that gap named up front,
not discovered in production.

#### Who This Serves

**Primary user — the platform/data engineering team inside a regulated or
hardened enterprise running OpenShift.** Needs to let business users (or partner
teams) upload data (starting with Excel) into an analytical pipeline without
widening the trust boundary of the pipeline's own trusted code. Success looks
like: an Excel upload is validated inside a real sandbox boundary before it ever
reaches the ingestion layer, the whole round trip is traced and lineage-tracked
without custom instrumentation work, and the same `pixi run` commands that pass
locally are what CI and the OCP deployment run.

**Secondary user — a security/compliance reviewer auditing the pipeline.** Cares
that "sandboxed" is a verifiable claim, not marketing — per the `pyforge-atlas`
G1 precedent, the right proof shape is a headless-browser (or, here, a
Wasmtime-host) smoke test that asserts the sandbox's claimed isolation
mechanically (e.g. no filesystem/network access beyond what the WIT interface
explicitly grants), not just a design document asserting it.

**Tertiary user — a future Unity Data Stack tenant.** Per the kinship to
`docs/dreams/unity-data-stack.md`, this project is a candidate first
"vertical application" on that platform's shared innersource toolchain — the
Pixi-orchestrated, OCP-hardened pattern this project establishes is meant to be
reusable, not bespoke to the Excel-upload seed use case.

#### Success Criteria

**Primary criterion:** the seed use case (Excel upload → validated → DuckDB
Bronze → Silver/Gold via dbt → traced end-to-end) runs correctly, identically,
under `podman --read-only --user 1001` locally and under real OpenShift
Restricted SCC — with the WASI validation component's sandboxing mechanically
verified (not just asserted), the same way `pyforge-atlas` G1's `wasm-smoke` gate
mechanically proves its own no-backend claim.

Supporting criteria:

| Metric | Target | Why this matters |
|---|---|---|
| Excel upload → validated Bronze row, end-to-end | Runs identically local / Podman digital twin / OCP | Proves the one-toolchain claim, not just three separately-tested environments |
| WASI validation sandbox isolation | Mechanically verified via an automated gate (Wasmtime-host smoke test) | An unverified "it's sandboxed" claim is exactly the gap this project exists to close |
| OTel trace + OpenLineage facet coverage | 100% of pipeline stages (API → dlt → dbt) emit both | Native observability is a stated non-negotiable of the Dream |
| Restricted SCC compliance | Zero violations (non-root UID 1001, read-only rootfs) in both digital twin and OCP | The deployment posture is the point of the project, not an afterthought |
| Honesty about scope | Zero shipped claims beyond what the technical research verified as buildable | Directly answers the CLAUDE.md instruction to re-verify spec claims, not propagate the gist's un-re-verified ones |

#### Scope

**V1 (this brief's scope) — the seed use case only:**
- FastAPI `POST /upload/excel` (OIDC-protected).
- A `componentize-py`-compiled, pure-Python WASI Preview 2 component validating
  the upload's structure/data quality (no numpy/pandas/pyarrow inside the
  sandbox — see § The Solution).
- `dlt` ingestion of validated rows into DuckDB **Bronze**, run as a
  conventionally-hosted (Restricted-SCC-process-sandboxed, not Wasm-sandboxed)
  stage.
- `dbt-duckdb` transforms Bronze → Silver → Gold with column-level lineage.
- OTel tracing (W3C Trace Context propagated browser → API → pipeline) +
  OpenLineage facets emitted by `dlt` and `dbt` to a Vector sidecar / Marquez.
- One Pixi toolchain: `pixi install`, `pixi run build` (incl. the WASI
  component), `podman-compose up` for the OCP digital twin.
- A mechanical isolation-verification gate for the WASI component (the
  `wasm-smoke`-style proof from `pyforge-atlas` G1, adapted to a server-side
  Wasmtime host rather than a headless browser).

**Explicitly out of V1:**
- Any WASI-sandboxed DuckDB, `dbt`, or `dlt`-DuckDB-destination execution — the
  research shows this is blocked at the DuckDB dependency, not a scoping choice
  to revisit lightly.
- Apache Arrow buffers as the host↔component interchange — plain
  Python/JSON-shaped data only, per the same research finding.
- The full Vizro/Pyodide in-browser dashboard render (deferred in `pyforge-atlas`
  G1 itself as `DW-G1-1`) — V1 read access to Gold tables is out of this brief's
  scope entirely; a future browser-side read surface would reuse G1's pattern
  directly, not reinvent it.
- Multi-source ingestion beyond Excel, multi-tenant Unity Data Stack integration,
  and the dbt Fusion (Rust) engine migration path — all named as V2+/watch items
  below, not committed.

#### Vision

**[ASSUMPTION]** If the seed use case ships and the WASI validation boundary
proves both real (mechanically verified) and maintainable (doesn't become a
`componentize-py`-limitations tax the team regrets), this becomes the reference
pattern for "let untrusted input into a hardened OCP pipeline" across every
project in this workspace that needs it — a reusable Wasm-sandboxed validation
primitive, not a one-off. Longer-term, two watch items from the research could
reshape the roadmap materially: (1) if `dbt Fusion` (the Rust rewrite, in Beta as
of this research) gains a DuckDB adapter, the transform layer's own
WASI-portability story changes completely, since Rust compiles to WASI far more
cleanly than CPython; (2) if DuckDB itself ever ships a WASI build (no evidence
found that this is even being discussed upstream today), the entire "Bronze on
DuckDB, sandboxed" claim from the original April 2026 gist becomes buildable as
originally imagined, rather than the narrower V1 this brief scopes. Neither is a
V1 dependency; both are why the architecture stage should keep the DuckDB-facing
layer's interfaces clean enough to swap later without a rewrite.

#### Known Risks

- **The WASI-component ecosystem is genuinely ahead of most Python usage today —
  this project would be pushing the frontier, not adopting an established
  pattern.** The domain research found only one of three comparable production
  Wasm-sandboxing deployments (Fermyon Spin) offers Python as a first-class
  option at all; Shopify Functions explicitly recommends Rust over any
  alternative for reliability under load. **Mitigation:** V1 keeps the WASI
  component's Python surface deliberately small (validation logic only, no
  C-extensions) — the exact shape the research shows is actually proven to work
  (`componentize-py`'s SQLite3-in-CPython-WASI and `.abi3.so`-recognition
  progress) rather than the exact shape that isn't (numpy/pandas via the
  unmaintained `wasi-wheels` project).
- **`componentize-py`'s own limitations are real, not hypothetical.** Dynamic
  runtime imports don't work (must resolve at build time); `pydantic` support is
  still an open, unresolved issue as of this research. **Mitigation:** the
  validation component's dependency surface must be audited against this
  constraint during Architecture, not discovered at build time — no `pydantic`
  inside the sandbox until upstream support lands, or hand-roll a plain-dataclass
  validation layer instead.
- **Component Model 1.0 itself is not yet finalized.** WASI 0.3 (native async)
  shipped in June 2026, but the roadmap to a stable 1.0 spec is still in
  progress per the Bytecode Alliance's own public talks. **Mitigation:** pin
  Wasmtime and `componentize-py` versions deliberately (not "latest"), and treat
  a spec-level breaking change as a known, budgeted-for risk during the
  Architecture and build phases, not a surprise.
- **wasi-threads was removed from Wasmtime (47.0.0, 2026-07-20), not merely
  unsupported.** There is no mature multi-threaded execution model inside a WASI
  component today. **Mitigation:** the validation component must be designed as
  single-threaded, async-if-needed (via the new WASI 0.3 primitives) — this
  should be an explicit Architecture-stage constraint, not an implicit
  assumption.
- **The gist this Dream was seeded from is three months stale on exactly the
  claims that matter most.** Its "Apache Arrow buffers across the Wasm boundary"
  step has no supporting implementation anywhere found in this research.
  **Mitigation:** this brief already corrects that claim (§ The Solution); the
  PRD and Architecture stages must not silently re-inherit it from the gist
  without re-reading this brief and its underlying research report first.

#### Kill Criteria

**[ASSUMPTION]** Given this project has not yet had a build phase to generate
real usage/dogfooding signal, kill criteria are scoped to the validation-spike
level rather than a shipped-product level: if, during Architecture or an early
build spike, the `componentize-py`-compiled validation component cannot be made
to satisfy the mechanical isolation-verification gate (§ Success Criteria) within
a reasonable spike budget, OR if the WASI component's maintenance burden (working
around `componentize-py`'s import/library limitations) exceeds the value of the
extra sandboxing boundary versus simply running the same validation logic as a
normal, Restricted-SCC-hardened process step, the project should drop the
WASI-sandboxing claim entirely and ship the pipeline as a conventional
OCP-hardened data stack — still valuable (native OTel/OpenLineage + one
toolchain), just without the Wasm differentiation this brief leads with.
