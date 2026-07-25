---
title: "Product Brief: Unity Data Stack"
status: "draft"
created: "2026-07-25"
updated: "2026-07-25"
project_slug: "unity-data-stack"
inputs:
  - "{project-root}/docs/dreams/unity-data-stack.md (Tier-0 Dream)"
  - "{project-root}/docs/intake/gists/spec-kit/constitution.md (37 KB, v1.2.0, ratified 2025-11-20)"
  - "{project-root}/docs/intake/gists/unity-data-stack-pixi-toml/Unity-Data-Stack-Pixi.toml (1,726 lines)"
  - "{project-root}/docs/intake/gists/bmad-method-spec-enterprise-monorepo-cross-platform-deployme/*.md"
  - "planning-artifacts/research/market-enterprise-innersource-python-platform-research-2026-07-25.md"
  - "planning-artifacts/research/domain-enterprise-python-platform-engineering-research-2026-07-25.md"
  - "{project-root}/pixi.toml + src/ (live worked example of the same shape)"
  - "{project-root}/docs/dreams/{ecosystem-crew,enterprise-airgap,packaging-factory,pyforge-genesis}.md"
mode: "headless / fast path — [ASSUMPTION] tags mark inferences"
---

# Product Brief: Unity Data Stack

## Executive Summary

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
Together they are perhaps 60% of a platform definition — genuinely good work, authored
2026-01 → 2026-05, now measurably drifted. This effort's job is to **absorb, correct, and
complete** them: keep what research confirms, fix what research falsifies, and supply what is
missing — principally the human contribution model, the provenance chain, and a resolved answer
to the one architectural question the gists never asked.

**Why now:** the **EU Cyber Resilience Act's vulnerability-reporting obligations begin
2026-09-11 — roughly seven weeks out** — with full obligations 2027-12-11. "Know what you ship,
continuously" stops being good practice and becomes a dated legal duty that propagates through
the value chain. Unity's compliance posture was designed before that clock was visible; it is now
the platform's sharpest justification.

## The Problem

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

## The Solution

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
- **Compliance as an artifact, not an activity.** Every build emits a versioned CycloneDX SBOM
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

## What Makes This Different

The wedge is a conjunction, and each qualifier removes an incumbent:

| Qualifier | Removes | Because |
|---|---|---|
| **conda-native** | Pants, Bazel, Nx | They own the build graph brilliantly — and resolve *wheels*. The native components a data platform is made of are outside their guarantee. |
| **air-gap-first** | SaaS IDPs, Nx Cloud | A posture designed in, not a deployment mode bolted on. |
| **spec-governed** | — (aligns rather than competes) | The Constitution is already in spec-kit format; spec-kit is at **123.7k stars**, ~3.6× Backstage's 33.9k. Format choice validated by adoption. |
| **monorepo *platform*** | Backstage | A portal *describes* an estate. Unity *builds* one. Unity should be catalog-**able**, not a catalog. |

Research found nothing occupying all four simultaneously. **Honest caveat:** web-search discovery
was unavailable during research (budget exhausted), so the comparable set was assembled from named
sources. Completeness is not claimed — a 2026-launched competitor could exist and be absent
(research OQ-M1).

**The honest moat is not technical novelty — it is accumulated integration.** Nothing here is
individually impossible. What is hard to copy is that the conda-forge supply chain, the compliance
gate, the air-gap routing, and the dependency intelligence already exist, in one place, working.

## Who This Serves

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

## Success Criteria

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

## Scope

### In — v1

- **The workspace substrate**: pixi root, feature/environment composition, per-package manifests,
  supported-platform matrix, `[system-requirements]` floors.
- **A resolved lock architecture** — the decisive open question (see below).
- **The quality gate**: `check-all` parity with CI; lint / format / type / security; pre-commit.
- **The Constitution, corrected and machine-checkable**, with a stated global-vs-local governance
  split.
- **The contribution model**: trusted-committer role, review path, templates, onboarding docs.
- **The compliance chain**: versioned CycloneDX (1.7 / ECMA-424), SLSA provenance, continuous
  exploited-vulnerability gating — by **integrating pyforge-warden**, not reimplementing it.
- **Air-gap posture**: env-var-only mirror routing, no credentials in URLs, offline bundle path.
- **One reference domain, end to end** (`customer`), proving the domain pattern.

### Out — v1 (explicitly)

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

### The decisive open question

**Is `pixi.lock` the source of truth with `pylock.toml` derived, or the reverse?** The two intake
gists answer differently and neither notices the conflict: the working root is a pixi workspace
(`pixi.toml`, conda+PyPI, `src/…` layout); the toolchain spec is a PDM workspace
(`pyproject.toml`, PEP 751 only, `apps/` + `libs/`) with a **Zero-State rule** that production
must boot from `pylock.toml` *alone*.

They cannot both hold. PEP 751 is a *Python package* lockfile — it cannot express DuckDB, Arrow's
ABI, nginx, or Node. The spec's own Dockerfile resolves this silently by switching to a
`python:3.11-slim` production base, i.e. abandoning conda at deploy time — which discards the
exact property conda was mandated for.

`[ASSUMPTION]` **pixi-primary**: `pixi.lock` is the source of truth, `pylock.toml` is a derived
export for PEP 751 consumers (audit tooling, SBOM generation, non-pixi runtimes), and offline
deployment uses `pixi-pack` / `pixi-unpack` — both already present in the working root. Rationale:
conda-native is the differentiator, and the alternative discards it. **This is an architecture
decision, not a brief decision** (research OQ-D8) — flagged here because everything downstream
depends on it.

## What Research Changed

Eight verified deltas against the intake artifacts. Full detail in the research reports; the
load-bearing ones:

| Finding | Grade | Consequence |
|---|---|---|
| `pdm export --override-platform` **does not exist**; the format token is `pylock.toml` | **WRONG** | The toolchain spec's flagship `lock-monorepo` task is unimplementable as written |
| PEP 751 does **not** guarantee multi-platform lockfiles — it uses environment markers | **Scope error** | Multi-platform coverage must be *verified*, not assumed. Compounds with the above: the "Cryptographic Predictability" outcome currently has **no verified mechanism** |
| pixi is **0.73.0**; the working root pins `==0.59.0` exactly | Stale | Nobody on current pixi can open the workspace. New `workspace = true` also removes the root's worst duplication smell |
| pip's `pylock.toml` support is **experimental** (25.1 `pip lock`, 26.1 `-r pylock.toml`) | New + risk | The Zero-State rule rests on an experimental feature; needs a fallback |
| Dagster 1.13.15 supports Python ≤3.14 | Stale | The `<3.14` ceiling's stated reason has expired — re-test |
| Python 3.12 is **security-only**; 3.15 lands **2026-10-01** | Stale | The declared "legacy baseline" gets no further binaries; 3.15 is inside the horizon |
| **SLSA provenance is entirely absent** from the intake set | Gap | SBOM says what is *in* the artifact; nothing says how it was built. L2 is cheap on hosted CI |
| **No trusted-committer role**; three crew stations (Herald/Doctor/Scribe) unmapped in the role matrix | Gap | The intake set systematically under-specifies the human layer — converged from two independent angles |

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

## Vision

**In two to three years**, Unity Data Stack is what "we build data products here" means at an
adopting enterprise. A new engineer's first day is a clone and a command. A team that needs
something asks whether it exists before building it, and usually it does. Contributing to another
team's library is ordinary. Compliance evidence is a build output nobody thinks about until an
auditor asks and it is already there.

Beyond one enterprise: **pyforge-genesis** bootstraps Unity instances (`genesis init` /
`genesis adopt`), so the platform is reproducible across organizations rather than a bespoke
build each time; the **pyforge crew** (Herald · Marshal · Atlas · Warden · Mason · Doctor ·
Scribe · Steward) operates it, mapping cleanly onto the toolchain spec's five roles and supplying
the three feedback-loop stations the spec omitted. Unity becomes the reference answer to *"what
does a Python data platform look like inside a regulated enterprise in 2027?"* — with the
compliance chain, the air-gap posture, and the innersource contribution model as the parts other
organizations copy.

---

## Open Questions Carried Into the PRD

Consolidated from both research reports; ordered by decision urgency.

| ID | Question | Owner |
|---|---|---|
| **OQ-D8** | pixi-primary, pylock-primary, or split-by-tier? *Everything downstream depends on this* | Architecture — **resolve first** |
| **OQ-M7** | `pdm lock --platform` + export, or `uv export --format pylock.toml`? | Architecture |
| **OQ-M4** | Where is the boundary between spec-kit governance and BMAD planning? Both are active here | PRD |
| **OQ-M5** | What is Unity's trusted-committer-equivalent role? | PRD |
| **OQ-D7** | Which mandates are platform-wide invariants vs domain-overridable defaults? | PRD |
| **OQ-D10** | Which of the 11 tech domains are real vs aspirational? *Order-of-magnitude sizing impact* | PRD |
| **OQ-D4** | Warden integration boundary — library, CLI, CI action, or MCP tool? | Architecture |
| **OQ-M8** | Preview `pixi-build` workspaces, or editable path installs? | Architecture |
| **OQ-M11** | Should the 12-stage SDLC be pixi environments at all? (5 are byte-identical; 3 more are `["runtime"]`) | Architecture |
| **OQ-D5** | Does `sbom4python --requirement pylock.toml` emit a dependency *graph* or a flat list? | Empirical test — cheap, do early |
| **OQ-D6** | Target SLSA level for v1? (recommend L1 mandatory / L2 target) | PRD |
| **OQ-D3** | Exact CRA Annex I wording — is SBOM actually required, or inferred? | Verify before citing CRA as authority |
| **OQ-M10** | Is `linux-aarch64` in scope for v1? The two gists disagree on the platform matrix | PRD |
| **OQ-D9** | Does the data-classification axis need enforcement (PII masking, access control) or is it documentation? | PRD |
| **OQ-M9** | Is conda-forge's dagster built for Python 3.14? | Verify before pinning |
| **OQ-D1** | Current OCP version / Kubernetes baseline / EUS lifecycle? (`docs.redhat.com` 403) | Verify before architecture pins |
| **OQ-D2** | Does `osv-scanner` cover `pylock.toml` / `pixi.lock` / conda? | Verify at Warden integration |
| **OQ-M1** | Is the comparable set complete? Web-search discovery was unavailable | Re-run when budget allows |
| **OQ-M2** | Does *every* mandated component exist on conda-forge, on every target platform? | Bulk `cf_atlas` query when available |
| **OQ-M3** | Express the role matrix as a spec-kit *bundle*? | Architecture |
| **OQ-M6** | Independent 2025/26 innersource adoption data to ground the value claim? | Research follow-up |

**Companion artifacts:** `../../research/market-…-2026-07-25.md` ·
`../../research/domain-…-2026-07-25.md` · `addendum.md` (detail deferred from this brief).
