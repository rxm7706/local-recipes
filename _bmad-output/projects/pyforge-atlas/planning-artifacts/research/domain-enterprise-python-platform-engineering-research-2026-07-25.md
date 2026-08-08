---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - "{project-root}/docs/dreams/unity-data-stack.md"
  - "{project-root}/docs/dreams/ecosystem-crew.md"
  - "{project-root}/docs/dreams/enterprise-airgap.md"
  - "{project-root}/docs/dreams/packaging-factory.md"
  - "{project-root}/docs/dreams/pyforge-genesis.md"
  - "{project-root}/docs/intake/gists/spec-kit/constitution.md"
  - "{project-root}/docs/intake/gists/unity-data-stack-pixi-toml/Unity-Data-Stack-Pixi.toml"
  - "{project-root}/docs/intake/gists/bmad-method-spec-enterprise-monorepo-cross-platform-deployme/BMAD-METHOD SPEC: Enterprise Monorepo, Cross-Platform Deployment, and Compliance Toolchain.md"
  - "{planning_artifacts}/research/market-enterprise-innersource-python-platform-research-2026-07-25.md"
workflowType: 'research'
lastStep: 5
research_type: 'domain'
research_topic: 'Enterprise Python platform engineering — innersource monorepo, data mesh, air-gapped supply chain and SBOM compliance, agent role matrices'
research_goals: 'Establish the domain forces (regulatory, standards, architectural) that constrain Unity Data Stack; test the intake Constitution and toolchain spec against them; map the toolchain spec role matrix onto the pyforge crew.'
user_name: 'Rxm7706'
date: '2026-07-25'
web_research_enabled: true
source_verification: true
project_slug: 'unity-data-stack'
---

# Research Report: Domain

**Date:** 2026-07-25
**Author:** Rxm7706
**Research Type:** Domain
**Project:** unity-data-stack

---

## Research Overview

### Question

The market report (companion artifact) establishes *who else plays* and *what changed since the
gists*. This report establishes the **domain forces** — the regulatory, standards, and
architectural pressures that a platform of this kind must satisfy regardless of competitive
positioning — and tests the intake artifacts against them.

Five domain axes are examined:

1. **The regulatory clock** — what compliance obligations bind, and when.
2. **Supply-chain standards** — SBOM and provenance formats an enterprise platform must emit.
3. **Data mesh** — whether the Constitution's Article VII is faithful to the source architecture.
4. **The air-gapped supply chain** — what "pixi-first + air-gap" actually buys and costs.
5. **The agent role matrix** — mapping the toolchain spec's five roles onto the eight-station
   pyforge crew that already exists in this repository.

### Methodology

Primary-source verification throughout; each finding cites the source fetched. Intake artifacts
are treated as hypotheses under test. Sibling Dreams (`enterprise-airgap`, `packaging-factory`,
`ecosystem-crew`, `pyforge-genesis`) are treated as **binding local context** — they describe
capability that already exists in this repository, so Unity should consume rather than duplicate.

### Limitations (declared)

- **`WebSearch` budget exhausted** before this run began; all findings come from directly-fetched
  named sources. See the market report § Limitations (**OQ-M1**) — same constraint, same caveat
  about completeness.
- **`cf_atlas` unavailable** in this worktree, so conda-forge coverage of the mandated stack is
  spot-checked only (**OQ-M2**).
- **OpenShift version facts could not be obtained** — `docs.redhat.com` returned HTTP 403.
  The Constitution mandates OCP as the sole production platform, so its current version,
  Kubernetes baseline, and EUS lifecycle remain unverified. Recorded as **OQ-D1**.
- `osv-scanner`'s exact Python/conda lockfile coverage could not be confirmed from the fetched
  page (it advertises "11+ language ecosystems and 19+ lockfile types" without enumerating them).
  Recorded as **OQ-D2**.

---

## Part 1 — The Regulatory Clock

This is the **single most time-sensitive finding in either research report.**

### 1.1 The EU Cyber Resilience Act

| Milestone | Date | Obligation |
|---|---|---|
| Entry into force | **2024-12-10** | Act effective |
| **Reporting obligations begin** | **2026-09-11** | Manufacturers must **report actively exploited vulnerabilities** |
| Main obligations apply | **2027-12-11** | Full cybersecurity requirements across the product lifecycle; CE marking |

**Scope:** "connectable hardware and software" with digital elements — "from baby-monitors to
smart watches, from apps to computer programs." Obligations cover "the planning, design,
development and maintenance of such products," extend **throughout the value chain**, and require
vulnerability handling across the product lifecycle. Enforcement is by national market
surveillance authorities.

**Why this dominates the domain.** The reporting deadline is **2026-09-11 — approximately seven
weeks after this report's date.** Any enterprise platform being planned in mid-2026 is being
planned *into* a live regulatory transition, not ahead of one. Two structural consequences for
Unity:

1. **"Know what you ship" becomes a legal obligation, not an engineering preference.** The
   Constitution's Article XII (Security and Compliance) and the toolchain spec's Compliance Agent
   are, as of 2026-09-11, backed by regulation for anything Unity's users place on the EU market.
2. **Value-chain propagation.** Because obligations extend through the value chain, an *internal*
   platform that feeds products placed on the market inherits the evidentiary burden. Unity's
   `sbom-runtime.json` / `sbom-full.json` split is therefore not a nice-to-have — it is the
   artifact that discharges it.

**Caveat, stated plainly:** the fetched EC page does **not** explicitly mention an SBOM
requirement. The widely-held reading is that CRA Annex I requires manufacturers to identify and
document components, which SBOM satisfies — but that inference is **not verified here** and must
not be asserted as fact in the PRD. Recorded as **OQ-D3**: confirm the precise CRA Annex I
component-documentation wording before writing an SBOM requirement that cites CRA as its
authority.

**A second caveat on applicability:** whether CRA binds a *given* Unity deployment depends on
whether that enterprise places products with digital elements on the EU market. For a purely
internal platform serving internal consumers, applicability is genuinely uncertain. The PRD
should treat CRA as a **design forcing-function and a capability Unity must be able to
discharge**, not as an assertion that every Unity instance is regulated. Recorded as
**assumption A-D1**.

> Source: [European Commission — Cyber Resilience Act](https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act)

### 1.2 What this changes about the intake artifacts

The toolchain spec was written with a **compliance** posture already — a dedicated Compliance
Agent, segregated SBOM arrays, `sbom-runtime.json` vs `sbom-full.json`. That instinct is **now
validated by a dated regulatory obligation** rather than by good practice alone. The intake
artifacts do not mention CRA; the PRD should, with the dates above.

The most under-served CRA obligation in the intake set is the **2026-09-11 one**: *reporting
actively exploited vulnerabilities*. That is a **continuous, operational** duty — it requires
knowing, at any moment, whether anything in your deployed estate is affected by an
actively-exploited CVE. The toolchain spec's daily `auto-patch.yml` (cron `0 0 * * *`, `pip-audit`
→ `pdm update` → PR) is a *remediation* loop, and a good one. It is not a *reporting* loop: it has
no notion of exploitation status, no severity gate, no evidence trail, and no notification path.

This is precisely the capability **[[pyforge-warden]] already ships** in this repository —
"pluggable multi-axis Python dependency compliance gate" with **CISA-KEV** (Known Exploited
Vulnerabilities) and **EPSS** gates, baseline & grandfathering, and one schema-validated
`ComplianceReport` behind a CI exit-code gate. Warden completed 31/31 stories and merged
2026-07-25. **CISA-KEV is the actively-exploited signal the CRA reporting obligation requires.**

**This is the single highest-leverage integration in the report:** Unity should consume Warden as
its compliance axis rather than reimplement `pip-audit`-based scanning. Recorded as
**OQ-D4** (integration boundary) and carried into Part 5.

---

## Part 2 — Supply-Chain Standards

### 2.1 SBOM: CycloneDX is now a formal standard

| Fact | Value |
|---|---|
| Current spec version | **1.7**, released **2025-10-21** |
| Standardization | **ECMA-424**, published **2025-12-10** |
| Stewards | OWASP Foundation + Ecma International, TC54 |
| BOM types | SBOM, **SaaSBOM**, HBOM, **ML-BOM**, **VDR/VEX** |
| New in recent versions | **formulation** (manufacturing/deployment processes), **declarations** (compliance-as-code), **citations** (data provenance) |
| Media types | Registered with IANA — JSON, XML, Protocol Buffers |

Three of these land directly on Unity:

- **ECMA-424 status changes the argument.** CycloneDX is no longer "a popular format"; it is a
  published international standard. For a platform whose selling point is enterprise compliance,
  targeting a standard rather than a format is materially stronger.
- **ML-BOM matters here specifically.** The Constitution mandates MLflow, Kedro, and a data-science
  toolbox; the working root carries `vizro-ai`, `wagtail-ai`, and an entire `agentic` feature. A
  platform shipping ML assets can now describe them in-band.
- **`declarations` (compliance-as-code)** is the natural home for the Constitution's own
  attestations. A Constitution that claims to be machine-enforced and a BOM format that carries
  compliance declarations are a strong pairing — a genuinely novel capability worth a PRD
  requirement rather than a footnote.

The intake toolchain spec emits `--sbom cyclonedx --format json`, unversioned. Post-ECMA-424 that
should be an **explicit version target (1.7 / ECMA-424)**, because "CycloneDX" alone no longer
identifies a single artifact contract.

> Source: [cyclonedx.org/specification/overview](https://cyclonedx.org/specification/overview/)

### 2.2 The SBOM generator has a fidelity caveat

`sbom4python` (mandated in the toolchain spec root manifest at `>=0.10.0`) emits **SPDX and
CycloneDX** in tag/value, JSON, and YAML. It operates in two modes:

- **installed-environment** (`--module` / `--system`) — scans installed packages;
- **requirements** (`--requirement`) — reads **`pylock.toml`**, `requirements.txt`,
  `pyproject.toml`, `setup.cfg`, or `setup.py`.

`pylock.toml` is explicitly supported as an input, which vindicates the toolchain spec's design.
**But the documentation carries a hard caveat on the requirements mode: "no transitive components
will be identified."**

The severity of this depends on a distinction the PRD must get right:

- `pylock.toml` is a **fully-resolved** lockfile — PEP 751 records exact packages "without
  requiring dependency resolution at install time," so the transitive *components* are already
  enumerated in the file. The tool does not need to walk them.
- What is **at risk is the dependency graph** — the CycloneDX `dependencies` edges describing
  *which component requires which*. A generator that does not resolve transitives may emit a
  **flat component list with no relationship graph**.

For CRA/VEX purposes a flat inventory is weaker evidence than a graph: you can answer "do I ship
X?" but not "what reaches X, and is it actually invoked?" — which is the question VEX
exploitability analysis turns on.

**This must be empirically verified, not assumed in either direction.** Recorded as **OQ-D5**:
generate a CycloneDX BOM from a real `pylock.toml` and inspect whether `dependencies` edges are
populated. If they are not, either switch generator or generate from the installed environment
(`--system`) inside the built container, where the graph is recoverable.

> Source: [github.com/anthonyharrison/sbom4python](https://github.com/anthonyharrison/sbom4python)

### 2.3 Provenance: SLSA — and a gap in the intake set

SLSA build levels (current spec **v1.2**; v1.1 is marked **Retired**):

| Level | Requirement | Protects against |
|---|---|---|
| **L0** | No guarantees | — (dev/test builds on a single machine) |
| **L1** | **Provenance exists** — what entity built it, what process, what top-level inputs. May be unsigned | Mistakes; no tamper protection |
| **L2** | **Signed provenance from a hosted build platform** | Post-build tampering |
| **L3** | **Hardened builds** — runs cannot influence one another; signing key material protected | Tampering *during* the build, by insiders or compromised credentials |

**The intake set has no provenance story at all.** The toolchain spec produces SBOMs (what is
*in* the artifact) but no provenance (how the artifact *came to be*). Its Dockerfile does label
the image with `org.opencontainers.image.sbom="/app/sbom.json"` — inventory, not provenance.

For a platform claiming "Immutable Compliance Proofs" and "Cryptographic Predictability," this is
a real omission: the pinned hashes in `pylock.toml` prove *what went in*; nothing proves *who
built it or how*. Since the spec's CI already runs on GitHub Actions — a hosted build platform
capable of signed provenance — **SLSA L2 is within reach at low cost** and should be a PRD
requirement. Recorded as **OQ-D6**: target SLSA level for v1 (recommendation: **L1 mandatory,
L2 target**; L3 out of scope for v1 given hardened-builder requirements).

> Source: [slsa.dev/spec/v1.1/levels](https://slsa.dev/spec/v1.1/levels) (page notes v1.2 is current)

### 2.4 Standards summary

| Concern | Standard | Version/status | Intake coverage | Gap |
|---|---|---|---|---|
| Inventory | CycloneDX | **1.7 / ECMA-424** (2025-12-10) | Yes, unversioned | Pin the version; consider `declarations` + ML-BOM |
| Inventory (alt) | SPDX | supported by sbom4python | Not specified | Decide one or both |
| Vulnerability exchange | **VEX/VDR** (in CycloneDX) | 1.7 | **Absent** | Needed for CRA exploitation reporting |
| Provenance | **SLSA** | **v1.2** (v1.1 retired) | **Absent** | L1 mandatory / L2 target |
| Lockfile | PEP 751 `pylock.toml` | Final 2025-03-31 | Yes — mechanism unproven (market D3) | Verify multi-platform coverage |

---

## Part 3 — Data Mesh: Is Article VII Faithful?

Data Mesh (Dehghani, **2020-12-03**) rests on four principles. Testing the Constitution's
Article VII against each:

| # | Principle | Source definition | Constitution coverage | Verdict |
|---|---|---|---|---|
| 1 | **Domain-oriented decentralized ownership** | Responsibility for analytical data, metadata, and computation distributes across business domains along organizational boundaries | § 7.1 names **11 tech domains** (ccibt, cdo, cdxo, ct, cto, customer, dti, eft, ics, ohot, tcoo); § 7.4 gives each clear ownership, forbids cross-domain direct DB access | **Faithful — strongest coverage** |
| 2 | **Data as a product** | Domains treat data outputs as products, consumers as customers; addresses discovery, quality, trustworthiness, usability | § 7.5 requires data contracts, backward compatibility, versioned breaking changes, quality monitoring, usage docs; § 5.2 mandates asset metadata (`owner`, `domain`, `layer`, `update_frequency`) | **Faithful** |
| 3 | **Self-serve data infrastructure as a platform** | Abstracted infrastructure letting domain teams build/deploy/operate independently, via "higher level of abstraction" and declarative interfaces | **Not in Article VII** — but this is *what Unity itself is*. The ~200 pixi tasks and per-package environments are the self-serve interface | **Implicit — should be explicit** |
| 4 | **Federated computational governance** | Distributed decision-making balancing domain autonomy with global standardization; "embraces change and multiple interpretive contexts" rather than static canonical models; platform automates policy enforcement | **In tension.** The Constitution is *centralized* governance: "immutable principles," "non-negotiable," "supersedes all other development practices," amendments requiring central consensus | **Partial — genuine tension** |

### 3.1 The principle-4 tension, stated precisely

The Constitution gets the **computational** half of federated computational governance exactly
right — policy *is* automated, enforced by agents on every PR, with violations reported against
specific clauses. That is a faithful, well-executed implementation of "the platform automates
policy enforcement across the mesh."

What is missing is the **federated** half. Data Mesh explicitly "embraces change and multiple
interpretive contexts rather than enforcing static canonical data models." The Constitution
declares itself "the single, immutable source of truth" with "non-negotiable" mandates.

For most of Article II's technology mandates this is *correct and desirable* — an opinionated
platform's whole value is reducing decision fatigue, and the Dream says so ("The Opinionated start
picks certain technologies and practices as defaults to streamline adoption"). The tension is not
fatal; it is **located**. Specifically:

- **Global concerns** (interoperability, security, the asset naming convention, the raw/curated/
  consumption layering, data contracts) — centralized mandate is right.
- **Local concerns** (a domain's internal modelling, its processing library choice, its update
  cadence) — Data Mesh says these should be domain-autonomous. The Constitution's Art. II
  mandates (Polars *and* Pandas *and* Dask *and* Ibis *and* daft are all listed in § 1.2, but
  Dagster is "the sole platform" and Kedro "the sole approved toolbox") do not draw this line.

**The Constitution has no concept of a domain-local exception**, other than the generic ADR
escape hatch in Art. II § 2.5 (which is scoped narrowly to *pixi* exceptions) and Art. XIII § 13.3
(complexity justification). Recorded as **OQ-D7**: define the global-vs-local governance split —
which mandates are platform-wide invariants and which are domain-overridable defaults. This is a
first-class PRD requirement, and it is also the mechanism by which Unity stays *innersource*
rather than becoming *centrally imposed* — which connects directly to market **OQ-M5** (the
missing Trusted Committer role).

### 3.2 A terminology note

The Constitution's three layers are **Raw → Curated → Consumption** (Amendment 1.2.0 renamed them
from Processed/Analytics). This is a well-formed medallion-style layering. It is *not* from the
Data Mesh source text, which is silent on internal layer naming — so this is Unity's own
convention, correctly scoped as a platform-wide invariant (a global concern per § 3.1). No
conflict; worth recording as a deliberate local extension rather than an inherited principle.

> Source: [martinfowler.com/articles/data-mesh-principles.html](https://martinfowler.com/articles/data-mesh-principles.html) (2020-12-03)

---

## Part 4 — The Air-Gapped Supply Chain

### 4.1 What the posture buys

The `enterprise-airgap` Dream (status: **realized**) frames this as "not a port; a posture:
air-gapped is the default deployment story, not an afterthought." The Constitution's Art. II
makes pixi/conda-forge the mandated package manager precisely for "air-gap capability."

The working root implements this well, and by the right mechanism — **environment variables only,
never committed config**:

| Variable | Purpose |
|---|---|
| `CONDA_CHANNEL_ALIAS` | Override conda-forge channel → Artifactory |
| `SELFEXPLAINML_CHANNEL_URL` | Override the secondary channel |
| `PIP_INDEX_URL` / `UV_INDEX_URL` | Override PyPI index |
| `GHE_HOST` / `GHE_API_BASE` | GitHub Enterprise host (also sets `GH_HOST` for `gh`) |

centralized in `config/airgap.conf` with `scripts/set-artifactory.sh --apply`, plus a
`vendors/` tree for pre-staged binaries. This matches the doctrine in this repo's
`docs/reference/enterprise-deployment.md` and the runtime-driven routing in `_http.py`.

### 4.2 The two-lockfile problem — the central domain tension

This is the deepest architectural issue the intake set contains, and neither gist addresses it.

**The two gists disagree about what the source of truth is:**

| | Working root (`Unity-Data-Stack-Pixi.toml`) | Toolchain spec |
|---|---|---|
| Manifest | `pixi.toml` (`[workspace]`) | `pyproject.toml` (`[tool.pixi.workspace]` + `[tool.pdm.workspace]`) |
| Source of truth | The pixi manifest | "The root `/pyproject.toml` handles all structural configurations" |
| Lockfile | `pixi.lock` (implied, conda+PyPI) | `/pylock.toml` (PEP 751, PyPI only) |
| Deploy rule | pixi environments | **"Zero-State"** — runtimes "must boot securely using only the `pylock.toml` file … independently of local `pixi.lock` layers or workspace manifests" |
| Members | `[pypi-dependencies]` editable paths | `[tool.pdm.workspace] members = ["apps/*", "libs/*"]` |
| Directory layout | `src/shared/…`, `src/platform/…`, `src/tech-domains/…` | `apps/`, `libs/` |

These are **two different architectures**, not two views of one. Reconciling them is arguably the
primary job of the architecture stage.

**Why it is genuinely hard, not merely a choice:**

1. **`pylock.toml` cannot express the conda half.** PEP 751 is a *Python package* lockfile. The
   native components a data platform is built from — DuckDB, PyArrow's ABI, PostgreSQL client
   libs, `nginx`, `supervisor`, `traefik`, `nodejs`/`pnpm`, `podman` — are conda packages in the
   working root. A `pylock.toml`-only runtime, as the Zero-State rule demands, **cannot
   reproduce them**. The toolchain spec's Dockerfile resolves this implicitly by switching to a
   `python:3.11-slim` base for the production stage — i.e. it silently abandons conda for
   deployment. That is a coherent choice, but it is a *different platform* than the one the
   Constitution mandates, and it discards the air-gap posture that conda/pixi was chosen for.
2. **Two solvers can disagree.** pixi solves conda + PyPI together against a channel; PDM/uv
   solves PyPI alone against an index. Nothing in the intake set forces them to agree. The seam
   between them is exactly where "reproducible" silently stops being true.
3. **Air-gap asymmetry.** conda-forge mirroring into Artifactory and PyPI mirroring into
   Artifactory are separate operational undertakings with separate failure modes. A design that
   depends on both is strictly more fragile than one that depends on one.

**Three candidate resolutions** for the architecture stage (**OQ-D8**, must resolve):

- **(a) pixi-primary.** `pixi.lock` is the source of truth; `pylock.toml` is a *derived export*
  for consumers that need PEP 751 (audit tools, SBOM generators, non-pixi runtimes). Deployment
  uses `pixi-pack`/`pixi-unpack` (both already in the working root's `[dependencies]`). Keeps the
  air-gap posture and the native half; makes the Zero-State rule an *export* guarantee rather than
  a runtime rule.
- **(b) pylock-primary.** The toolchain spec as written; pixi is a dev-time convenience only.
  Simpler runtime, standards-aligned — but abandons conda for production and contradicts
  Constitution Art. II.
- **(c) Split by tier.** Applications/services ship via `pylock.toml` containers; data-platform
  infrastructure ships via pixi. Honest about the real difference between the two, at the cost of
  two deployment paths.

**Prior art already in this repository favours (a):** `pixi-pack`/`pixi-unpack` are present
(`>=0.7.5`) and are purpose-built for exactly this — pack a solved environment into a portable
archive, unpack it behind the firewall, no index access required. The market report's framing
("conda-native is the wedge") points the same way: option (b) discards the differentiator.

### 4.3 The known defect that must be inherited as a requirement

The `enterprise-airgap` Dream records an open health issue that Unity inherits by construction:

> **`JFROG_API_KEY` unconditional injection in `_http.py`** — the header attaches to every
> outbound request regardless of host. Cross-resolver credential leak; fix before wider
> enterprise rollout.

The toolchain spec independently states a **Token Isolation Rule**: "Absolute enforcement of
credential isolation. No Artifactory infrastructure tokens or target environment variables may be
hardcoded into configuration files or version control systems."

The spec's own root manifest then does this:

```toml
[tool.pixi.pypi-options]
extra-index-urls = ["https://${PRIVATE_REGISTRY_USER}:${PRIVATE_REGISTRY_TOKEN}@my-artifactory-domain.jfrog.io/..."]
```

Credentials-in-URL, expanded from environment variables. This satisfies the letter of the rule
(nothing is *hardcoded*) while creating the classic failure mode: index URLs leak into lockfiles,
logs, error messages, and `pip`/`uv` debug output. The working root is **better** here — it uses
bare `PIP_INDEX_URL` / `UV_INDEX_URL` overrides and pushes auth to `config/airgap.conf` — and the
spec's CI job is worse still, interpolating `${{ secrets.ARTIFACTORY_USER }}` and
`${{ secrets.ARTIFACTORY_TOKEN }}` directly into a `--index-url` on the command line, where it
lands in process listings.

Two concrete PRD requirements follow: **(i)** credentials never appear in URLs — use pixi's
auth store / `setup-pixi`'s `auth-host`/`auth-username`/`auth-password` inputs (which the spec's
CI *also* uses correctly in its `setup-pixi` step, making the later `--index-url` interpolation
redundant as well as unsafe); **(ii)** host-scoped credential attachment, closing the `_http.py`
defect class at the platform level.

### 4.4 Python-version reality check for the air-gapped stack

Confirming the market report's D6/D7 with the data-science half of the stack:

| Component | Latest | requires-python | Working-root pin | Note |
|---|---|---|---|---|
| dagster | **1.13.15** | `>=3.10,<3.15` | `>=1.12.8,<2` | **3.14 now supported upstream** — the working root's "doesn't support 3.14 yet" comment is stale |
| kedro | **1.5.0** | `>=3.10` | `>=1.1.1` | Moved a full minor series |
| pixi | **0.73.0** | — | `==0.59.0` (exact) | 14 minors behind; blocks install |

The `monorepo-full-stack` environment exists precisely to detect cross-library conflicts, and its
`<3.14` ceiling was set by the dagster limitation. **That reason has expired.** Re-testing the
ceiling is a concrete, cheap early task — and it matters because Python 3.15 first-releases
**2026-10-01**, inside the planning horizon.

> Sources: [PyPI dagster](https://pypi.org/pypi/dagster/json), [PyPI kedro](https://pypi.org/pypi/kedro/json), [conda-forge pixi](https://api.anaconda.org/package/conda-forge/pixi)

---

## Part 5 — The Agent Role Matrix → the pyforge Crew

The toolchain spec defines five agent roles. This repository independently evolved an
**eight-station crew** (`docs/dreams/ecosystem-crew.md`, grown 6→8 on 2026-07-23 when an
ownership audit found two unowned stations). The Dream states the toolchain spec's matrix
"prefigures the crew." Testing that claim:

| Toolchain spec role | Spec's stated duties | pyforge station | Fit |
|---|---|---|---|
| **Architect Agent** | Workspace boundary conditions, acceptable risk tolerances, unified schema mappings | **Atlas** (Dependency Mapper & Data Pipeline Architect) + **Marshal** (orchestrator) | **Split.** Boundaries/schema → Atlas; risk tolerance & orchestration → Marshal |
| **Developer Agent** | Local toolchain, internal workspace config, localized coding | **Marshal** (BMAD orchestrator, drives the build) | Good |
| **DevOps Agent** | Cross-platform matrix, multi-stage container optimization, zero-state deployment | **Steward** (Platform, Deployment & Operations Officer) | **Excellent** — Steward was adopted 2026-07-23 for exactly this, and `enterprise-airgap` names deployment/install ops as Steward's station |
| **Security Agent** | Static analysis against the lockfile; self-healing patching bots | **Warden** (6-Axis Ecosystem Security & Hygiene Auditor) | **Excellent** — and Warden already implements the opt-in fix-PR actuator the spec calls a "self-healing patching bot" |
| **Compliance Agent** | Supply-chain mapping, operational scope filtering, segregated SBOM export | **Warden** (license + currency axes) + **Mason** (Package & Release Craftsman) | Good — SBOM export is close to Mason's `cyclonedx-universe-inventory` work |
| — | — | **Herald** (Visual Media & Messenger) | **Unmapped in the spec** — no reporting/communication role at all |
| — | — | **Doctor** (Ecosystem Health & Diagnostics) | **Unmapped in the spec** |
| — | — | **Scribe** (Knowledge Curator & Team Memory) | **Unmapped in the spec** |

### 5.1 Findings from the mapping

1. **The Dream's claim holds.** Five of five spec roles map cleanly onto crew stations; two map
   *excellently* (DevOps→Steward, Security→Warden) onto stations that were defined independently
   and later. That is real convergent-design evidence, and it is worth stating in the PRD as
   justification for reusing the crew rather than standing up a parallel role system.

2. **The spec's matrix is missing three stations, and the omissions are not random.** All three
   unmapped stations (Herald, Doctor, Scribe) are **feedback-loop** roles — communication,
   diagnostics, memory. The spec's matrix covers *doing* (architect, develop, deploy, secure,
   comply) but not *observing, explaining, or remembering*. For a platform whose social premise is
   cross-team innersource contribution, the absence of a communication station is the same gap
   the market report found from the InnerSource Commons angle (**OQ-M5**, no Trusted Committer):
   **the intake set systematically under-specifies the human/social layer.** Two independent
   analyses converging on the same gap raises confidence that it is real.

3. **Warden absorbs two of five roles and already exists.** Per repo memory, pyforge-warden is
   **COMPLETE 31/31, merged to main via PR #110 (2026-07-25)** — v1 axes: hygiene (`deptry`),
   security (`osv-scanner` + CISA-KEV + EPSS gates), license, currency, baseline &
   grandfathering, opt-in fix-PR actuator, one schema-validated `ComplianceReport` + CI
   exit-code gate, over Python/Conda/**Pixi** manifests.

   Compare the toolchain spec's Security+Compliance implementation: `pip-audit` + `sbom4python`
   + a cron workflow. Warden is a **strict superset** — it covers pixi manifests (which
   `pip-audit` cannot), adds exploitation-status gating (which CRA reporting requires), and
   produces a schema-validated report (which `pip-audit` output is not).

   **Recommendation, carried as OQ-D4:** Unity's Security and Compliance agents *are* Warden.
   The PRD should specify integration, not reimplementation, and the toolchain spec's
   `audit-prod`/`pip-audit` task should be superseded with that reason recorded.

4. **`pixi-first` is common ground.** Warden already scans Pixi manifests; the Constitution
   mandates pixi; the working root is a pixi workspace. The integration seam is natural.

> Sources: `{project-root}/docs/dreams/ecosystem-crew.md`; `{project-root}/docs/dreams/enterprise-airgap.md`; repo auto-memory `project_pyforge_warden.md`

---

## Part 6 — Domain Synthesis

### 6.1 The forces, ranked

| # | Force | Nature | Pressure on Unity |
|---|---|---|---|
| 1 | **EU CRA — reporting from 2026-09-11, full 2027-12-11** | Regulatory, dated | Continuous exploited-vuln awareness + evidence trail. **Seven weeks out.** |
| 2 | **The two-lockfile problem** | Architectural, unresolved in intake | Must pick pixi-primary / pylock-primary / split-by-tier before anything else is designed |
| 3 | **CycloneDX 1.7 = ECMA-424** | Standards, settled | Version-pin the SBOM target; VEX + ML-BOM now available |
| 4 | **SLSA provenance absent** | Standards, gap | L1 mandatory / L2 target |
| 5 | **Data Mesh principle 4 tension** | Architectural + social | Define the global-vs-local governance split |
| 6 | **The human layer is under-specified** | Social, converged from two angles | Trusted Committer role; contribution & review model |
| 7 | **Stack currency drift** | Operational | pixi 0.59→0.73, dagster 1.12→1.13, kedro 1.1→1.5, Python 3.12 security-only, 3.15 in Oct |

### 6.2 What Unity should consume rather than build

This repository already contains realized capability covering a large fraction of the intake
spec's ambitions. Building any of it again would be waste:

| Need | Existing capability | Status |
|---|---|---|
| Security + compliance gate | **pyforge-warden** — deptry, osv-scanner, CISA-KEV, EPSS, license, currency, `ComplianceReport`, CI gate | **Realized** (31/31, PR #110, 2026-07-25) |
| Conda-native package supply | **packaging-factory** / `conda-forge-expert` — 769 feedstocks, 30+ MCP tools | **Realized** (perpetual) |
| Air-gap routing doctrine | **enterprise-airgap** — `_http.py` truststore + JFrog chain, `docs/reference/enterprise-deployment.md` | **Realized** (one known defect, § 4.3) |
| Dependency intelligence | **pyforge-atlas** — cf_atlas, 15 phases, 17 CLIs | **Realized** (SHIPPED 2026-07-18) |
| Bootstrap the operating model | **pyforge-genesis** — `genesis init` / `genesis adopt` | **Frontier** — Unity is a prime consumer |
| Reporting / comms surface | **pyforge-herald** | Partly realized (deck bridge) |

**The strategic read:** Unity Data Stack is **not** mostly-new software. It is largely an
*integration and governance* effort that binds realized pyforge capability into a coherent
enterprise platform, plus genuinely new work in: the workspace/lock architecture (§ 4.2), the
governance split (§ 3.1), the contribution model (§ 6.1 #6), and the compliance evidence chain
(§ 2). Sizing the PRD accordingly — integration-heavy, not greenfield-heavy — is itself a finding.

---

## Assumptions

| ID | Assumption | Basis | Falsifiable by |
|---|---|---|---|
| **A-D1** | CRA is a design forcing-function Unity must be *able* to discharge, not a claim that every Unity instance is regulated | Applicability depends on EU market placement | An enterprise scope that never places products on the EU market |
| **A-D2** | `pixi.lock` should be the source of truth with `pylock.toml` derived (option (a), § 4.2) | conda-native is the wedge; `pixi-pack`/`pixi-unpack` already present | Evidence a target runtime cannot accept a pixi-packed environment |
| **A-D3** | Warden is consumed, not reimplemented, as Unity's Security + Compliance agents | Warden is realized and a strict superset of the spec's approach | An interface mismatch discovered at integration |
| **A-D4** | The eight-station crew supersedes the spec's five-role matrix (superset, § 5) | 5/5 map; 3 stations add feedback-loop coverage the spec lacks | A Unity-specific role with no crew home |
| **A-D5** | CycloneDX 1.7 / ECMA-424 is the SBOM target; SPDX is optional secondary | ECMA standardization; sbom4python emits both | An enterprise consumer that mandates SPDX only |

## Open Questions

| ID | Question | Why it matters | Owner |
|---|---|---|---|
| **OQ-D1** | Current OCP version, Kubernetes baseline, EUS lifecycle? (`docs.redhat.com` returned 403) | Constitution mandates OCP as the *sole* production platform | Verify before architecture pins |
| **OQ-D2** | Does `osv-scanner` cover `pylock.toml` / `pixi.lock` / conda? | Determines whether Warden's security axis covers Unity's real lockfiles | Verify at integration |
| **OQ-D3** | Exact CRA Annex I component-documentation wording — is SBOM actually required? | Don't cite CRA as SBOM authority without the text | PRD (verify before asserting) |
| **OQ-D4** | Warden integration boundary — library, CLI, CI action, or MCP tool? | Highest-leverage reuse in the report | Architecture (must resolve) |
| **OQ-D5** | Does `sbom4python --requirement pylock.toml` emit a populated `dependencies` graph, or a flat list? | Flat inventory is weak CRA/VEX evidence | Empirical test (cheap, do early) |
| **OQ-D6** | Target SLSA level for v1? (recommend L1 mandatory, L2 target) | Provenance is wholly absent from the intake set | PRD |
| **OQ-D7** | Which mandates are platform-wide invariants vs domain-overridable defaults? | Data Mesh principle 4; also the innersource-vs-imposed question | PRD (must resolve) |
| **OQ-D8** | **pixi-primary, pylock-primary, or split-by-tier?** | The deepest unresolved tension; everything downstream depends on it | Architecture (must resolve first) |
| **OQ-D9** | Does the 12-stage SDLC's *data classification* axis need enforcement (PII masking, access control), or is it documentation? | Constitution § 6.2 / § 12.6 assert it; no mechanism is specified | PRD |
| **OQ-D10** | Which of the 11 tech domains are real vs aspirational? (working root: 11 domains are "scaffolding only", 1 reference impl) | Sizing: 1 real domain vs 11 changes the effort by an order of magnitude | PRD (must resolve) |

---

## Sources

All fetched 2026-07-25.

1. [European Commission — Cyber Resilience Act](https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act) — in force 2024-12-10; reporting 2026-09-11; full 2027-12-11
2. [CycloneDX specification overview](https://cyclonedx.org/specification/overview/) — v1.7 (2025-10-21); ECMA-424 (2025-12-10)
3. [SLSA specification — build levels](https://slsa.dev/spec/v1.1/levels) — L0–L3; v1.2 current, v1.1 retired
4. [Data Mesh Principles and Logical Architecture — Dehghani](https://martinfowler.com/articles/data-mesh-principles.html) — 2020-12-03, four principles
5. [github.com/anthonyharrison/sbom4python](https://github.com/anthonyharrison/sbom4python) — SPDX + CycloneDX; `pylock.toml` input; transitive caveat
6. [github.com/google/osv-scanner](https://github.com/google/osv-scanner) — 11+ ecosystems, 19+ lockfile types (not enumerated)
7. [PyPI dagster JSON API](https://pypi.org/pypi/dagster/json) — 1.13.15, `<3.15,>=3.10`
8. [PyPI kedro JSON API](https://pypi.org/pypi/kedro/json) — 1.5.0, `>=3.10`
9. [conda-forge pixi package](https://api.anaconda.org/package/conda-forge/pixi) — 0.73.0, 7 subdirs
10. [PEP 751](https://peps.python.org/pep-0751/) — Final, 2025-03-31 (see companion market report)

**Local evidence:** `docs/dreams/{unity-data-stack,ecosystem-crew,enterprise-airgap,packaging-factory,pyforge-genesis}.md`;
the three intake gists under `docs/intake/gists/`; `{project-root}/pixi.toml`; repo auto-memory
(`project_pyforge_warden.md`).

**Companion artifact:** `research/market-enterprise-innersource-python-platform-research-2026-07-25.md`

---

## Refreshed 2026-08-08 — status change of the subject, clock update, findings stand

- **The subject's planning status changed on 2026-08-02:** the Unity Data Stack satellite this
  report grounds was folded — by explicit user override of the dream-level-only convention — into
  Atlas's own single brief/PRD/Architecture/Spec chain as `## Satellite:` sections (capabilities
  renumbered `CAP-18`..`CAP-31`, invariants `AD-24`..`AD-56`); its standalone planning folders
  moved intact to `archive/` under this project's `planning-artifacts/`, and
  `docs/dreams/unity-data-stack.md` is `status: archived / absorbed`. **Still zero epics/stories
  and zero code** (confirmed by the 2026-08-02 Dream-coverage audit's greps) — this report's
  findings therefore remain *pre-build* inputs, none exercised or falsified in the interval.
- **The regulatory clock advanced:** CRA exploited-vulnerability reporting (Part 1's #1 force,
  dated 2026-09-11) is now **~5 weeks out**, not seven. Unchanged as a design forcing-function;
  sharper as a scheduling fact for anyone activating the satellite.
- **§ 6.2's "consume, don't rebuild" table needs one nuance** (from the post-ship debt audit,
  `technical-atlas-post-ship-debt-and-cross-station-integration-research-2026-08-08.md`): the
  "Dependency intelligence — pyforge-atlas — Realized (SHIPPED 2026-07-18)" row is true of the
  code, but the migrated pipeline is not yet the production data path (legacy retirement gated on
  the unrun DW-B4 parity chain), and its live-fetch seams are injection-deferred to the Dagster
  bring-up. A Unity activation consuming Atlas datasets should sequence after — or become the
  demand driver for — that bring-up, rather than assume an operating Kedro data platform today.
- **§ 6.1 #7 stack-currency drift row refreshed:** kedro 1.5.0 / dagster 1.13.17 / pixi and
  friends all still actively shipping per the 2026-08-08 telemetry sweep in
  `technical-kedro-ecosystem-and-stack-currency-research-2026-08-08.md` § 2.
- Open questions OQ-D1–D3 remain open; no interval evidence.
