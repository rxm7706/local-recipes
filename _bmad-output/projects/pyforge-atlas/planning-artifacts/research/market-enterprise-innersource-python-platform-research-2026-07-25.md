---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - "{project-root}/docs/dreams/unity-data-stack.md"
  - "{project-root}/docs/intake/gists/spec-kit/constitution.md"
  - "{project-root}/docs/intake/gists/unity-data-stack-pixi-toml/Unity-Data-Stack-Pixi.toml"
  - "{project-root}/docs/intake/gists/bmad-method-spec-enterprise-monorepo-cross-platform-deployme/BMAD-METHOD SPEC: Enterprise Monorepo, Cross-Platform Deployment, and Compliance Toolchain.md"
workflowType: 'research'
lastStep: 5
research_type: 'market'
research_topic: 'Enterprise innersource Python monorepo platform (Unity Data Stack)'
research_goals: 'Identify comparable plays (IDPs, monorepo build platforms, SDD toolkits, innersource practice), establish what changed between the gists (2026-01 -> 2026-05) and now (2026-07), and ground the PRD in verifiable current facts.'
user_name: 'Rxm7706'
date: '2026-07-25'
web_research_enabled: true
source_verification: true
project_slug: 'unity-data-stack'
---

# Research Report: Market

**Date:** 2026-07-25
**Author:** Rxm7706
**Research Type:** Market
**Project:** unity-data-stack

---

## Research Overview

### Question

Unity Data Stack proposes an *opinionated shared monorepo platform* on which enterprise teams
co-contribute reusable templates, plugins, libraries, components, services, dashboards, reports,
and applications — Python-first, pixi-native, air-gap-capable, agent-enforced. Three substantial
artifacts already exist (a 37 KB Constitution, a 100 KB working pixi root, a 12 KB toolchain
spec), authored 2026-01 → 2026-05 and never landed in a repo.

This research answers three questions:

1. **Who else plays here?** What are the comparable categories, and what does each actually
   deliver? (Establishes what Unity must *not* rebuild.)
2. **What changed since the gists were written?** Which of their claims are now stale, wrong, or
   newly-true? (Establishes the delta list the PRD must absorb.)
3. **Where is the defensible position?** Given mature incumbents in adjacent categories, what is
   the wedge Unity occupies that nothing else does?

### Methodology

- **Primary-source verification.** Every quantitative claim below traces to a fetched primary
  source (PEP text, project changelog, package index API, official docs). Sources listed per
  finding and consolidated in § Sources.
- **Artifact archaeology.** The three intake gists were read in full and treated as *hypotheses
  to be tested*, not as ground truth — per the repo's standing rule that spec bodies are a
  starting point and quantitative claims get re-verified at intake.
- **Live-repo evidence.** `local-recipes` (this repository) is itself a working pixi
  multi-package monorepo — a same-shape worked example available for direct inspection rather
  than inference.

### Limitations (declared)

- **`WebSearch` budget was exhausted** for the session before the first query ran. All findings
  therefore come from *directly fetched named sources* rather than from discovery search. This
  biases coverage toward projects already known by name and means **no claim is made about
  completeness of the competitive set** — e.g. a newer IDP or Python monorepo tool launched in
  2026 could exist and be absent here. Recorded as **OQ-M1**.
- **The `cf_atlas` intelligence database was unavailable** in this worktree
  (`.claude/data/conda-forge-expert/cf_atlas.db` absent — it is gitignored runtime state).
  Conda-forge availability facts were therefore sourced from `api.anaconda.org` per package
  rather than from a bulk atlas query, so per-package conda-forge coverage of the Constitution's
  full mandated stack is **spot-checked, not exhaustive**. Recorded as **OQ-M2**.
- Two vendor pages (`backstage.io` root, `nx.dev` root) returned marketing content too thin to
  extract version/roadmap facts; findings for those rely on their GitHub repositories instead.

---

## Part 1 — The Comparable Set

Unity Data Stack is not a single-category product. It sits at the intersection of four mature
categories, each of which solves *part* of the problem and none of which solves the whole.

### 1.1 Internal Developer Portals (Backstage-class)

**What the category delivers.** A *catalog-and-discovery* plane over an organization's software
estate, plus templated project creation.

Backstage is "an open source framework for building developer portals," created by Spotify and
now a **CNCF Incubation-level project** (promoted from Sandbox in March 2022), at **33.9k GitHub
stars / 7.5k forks**. Its four load-bearing features are:

| Backstage feature | What it does | Unity's overlap |
|---|---|---|
| **Software Catalog** | Registry of microservices, libraries, data pipelines, websites, ML models | Unity's package inventory is the *same list*, but expressed as pixi workspace members rather than as YAML entity descriptors |
| **Software Templates** (Scaffolder) | Rapid project creation that enforces org best practice | Unity mandates **Copier** templates (`templates/`) for the identical job |
| **TechDocs** | "Docs-like-code" technical documentation | Unity mandates README-per-directory + ADRs (Constitution Art. V) |
| **Plugin ecosystem** | Extension surface | Unity's extension surface is pixi *features* + MCP servers |

**The category's shape — and its gap.** An IDP is a **portal over** an estate. It describes what
exists; it does not *build* it, does not resolve its dependencies, and does not make it
reproducible. Backstage's catalog entries are assertions about reality maintained by humans and
CI glue. **Backstage has no opinion about how your Python resolves, locks, builds, or ships.**

**Implication for Unity.** The catalog/portal plane is a *solved, adopted, CNCF-incubating*
problem. Unity should be **catalog-*able*, not a catalog** — i.e. emit
`catalog-info.yaml`-shaped facts derived from the pixi manifest rather than maintain a second
registry. This is a strong candidate for an explicit non-goal in the PRD.

> Source: [github.com/backstage/backstage](https://github.com/backstage/backstage)

---

### 1.2 Monorepo Build Platforms (Pants / Bazel / Nx class)

**What the category delivers.** A *build graph* over a monorepo: fine-grained dependency
inference, content-addressed caching, affected-target computation, and remote execution.

**Pants** (stable **2.32**) is the strongest Python-first entry. Its pitch is directly aimed at
Unity's problem space:

- **Minimal BUILD metadata** — "Pants requires very minimal BUILD file metadata/boilerplate. It
  uses a combination of static analysis and sensible defaults to infer most of that information
  on the fly."
- **Multiple dependency resolves with lockfiles** for hermetic, reproducible builds explicitly
  framed as supply-chain-attack resistance.
- **File-level granularity** — handles dependency tangles that block clean modularization.
- **Native Git integration** for change-scoped testing (run only tests affected between branches).
- **Enterprise proof**: Coinbase, IBM, Slack, Salesforce.

**Nx** is the volume leader — **2.5M+ daily developers, 70%+ of the Fortune 500, 34M+ monthly
npm downloads** — with project graph, affected computation, dual-layer caching (local + Nx Cloud
remote), and generators. But Nx is **JavaScript-ecosystem-native**; its own front page markets
"any editors, any stacks" without claiming Python support, and its distribution channel is npm.

**The category's shape — and its gap.** These systems own the **build graph**, and they own it
better than Unity ever will. But their reproducibility guarantee stops at the **Python-package
boundary**. Pants resolves PyPI wheels; it does not resolve the *native* half of the data stack —
the compiled DuckDB, the Arrow/PyArrow ABI, the PostgreSQL client libs, `nginx`, `supervisor`,
`traefik`, `podman`, `nodejs`/`pnpm`. Those are precisely the components a *data* platform is
made of, and they are precisely what a conda/pixi solve delivers and a wheel resolver does not.

**Implication for Unity.** The wedge is real: **Unity is a conda-native monorepo platform, and
the incumbent monorepo platforms are wheel-native.** Unity's `[system-requirements]` block
(`linux = "3.10"` kernel floor, `macos = "11.0"`) has no equivalent in Pants or Nx. This is the
single most defensible differentiator found in this research. It is also the reason Unity should
**not** attempt to out-build Pants on caching and remote execution — that competition is
unwinnable and orthogonal.

> Sources: [pantsbuild.org](https://www.pantsbuild.org/), [nx.dev](https://nx.dev/)

---

### 1.3 Spec-Driven Development toolkits (spec-kit class)

**What the category delivers.** A governance-and-generation loop in which the *specification is
executable* rather than advisory.

This is the category the Constitution was authored *into* — it is a spec-kit-format document —
and it is the category that moved most violently since the gists were written.

**GitHub `spec-kit` is at 123.7k stars.** For calibration, that is **~3.6× Backstage's 33.9k**.
Its workflow is a command chain executed by an AI agent:

```
/speckit.constitution  ->  establishes project principles
/speckit.specify       ->  defines requirements and user stories
/speckit.plan          ->  creates technical implementation strategy
/speckit.tasks         ->  generates actionable task lists
/speckit.implement     ->  executes all tasks
```

The constitution file is the **foundational governance layer**, capturing "project governing
principles and development guidelines that will guide all subsequent development." The toolkit
integrates **30+ AI coding agents**, installs via `uv tool install specify-cli`, is MIT-licensed,
and now has a three-tier extension model: **extensions** (new commands), **presets** (workflow
customization), and **bundles** (role-based complete setups).

**Two material deltas versus the intake Constitution:**

1. **Commands are now namespaced.** `/constitution` → `/speckit.constitution`. The intake
   Constitution's Preamble empowers "`spec-kit` and `specify`" as agents without pinning command
   syntax, so this is a *documentation* delta, not a structural one — but any Unity-side
   automation that shells out to spec-kit commands must use the namespaced forms.
2. **"Bundles" (role-based complete setups) now exist upstream.** The intake toolchain spec's
   **Role Assignment Matrix** (Architect / Developer / DevOps / Security / Compliance) is
   conceptually the same construct. Unity should evaluate expressing its role matrix *as* a
   spec-kit bundle rather than as a bespoke mechanism. Recorded as **OQ-M3**.

**Implication for Unity.** The Constitution's format choice is *validated by adoption at scale* —
this is the strongest external endorsement found for any decision in the intake set. But it also
means Unity's governance layer should **consume** spec-kit rather than reimplement it, and the
PRD must decide where the boundary sits between spec-kit's constitution-as-governance and BMAD's
Dream → spec → epics chain, since **both are now in play in this repository.** Recorded as
**OQ-M4** (this is the highest-priority open question in the report).

> Source: [github.com/github/spec-kit](https://github.com/github/spec-kit)

---

### 1.4 InnerSource practice (InnerSource Commons)

**What the category delivers.** Not software — *the operating model* Unity's Dream names
explicitly ("open-source culture and practices inside the enterprise").

InnerSource Commons is a **501(c)(3) nonprofit** (incorporated 2020) supporting **3,000+
individuals across 800+ organizations**. Its framing: "InnerSource takes the lessons learned from
developing open source software and applies them to the way companies develop software
internally" — targeting silo-breaking, collaboration, and **accelerated engineer onboarding**.

Its published body of practice includes InnerSource Patterns, Getting Started with InnerSource,
Managing InnerSource Projects, the InnerSource Checklist, and Adopting InnerSource. Role
vocabulary centres on the **Trusted Committer** (alongside host team / contributor). Active
events: InnerSource Gathering London 2025; **InnerSource Summit 2026** announced.

**Implication for Unity.** There is a **named, documented, nonprofit-stewarded pattern language**
for exactly the social model Unity's Dream describes, and the intake Constitution **does not
reference it once**. The Constitution encodes the *technical* half of innersource (shared
standards, one toolchain, enforced quality gates) with great specificity, and the *social* half —
how a team outside the owning team actually contributes, who reviews, who has commit rights, how
onboarding works — barely at all.

Constitution Art. VIII § 8.3 requires "at least one human approval (Contractual Sign-off)" but
never says *whose*. For a platform whose entire premise is cross-team co-contribution, the
absence of a Trusted-Committer-equivalent role is the **largest substantive gap** in the intake
set. Recorded as **OQ-M5**; the PRD should carry an explicit requirement for it.

> Source: [innersourcecommons.org](https://innersourcecommons.org/)

**Note on 2026 data.** The fetched landing page surfaced events and learning resources but **no
quantitative state-of-innersource 2025/2026 dataset**. The 3,000-individual / 800-organization
figures are the organization's own self-description. No independent adoption statistics were
obtainable within the constraints of this run (see § Limitations). Recorded as **OQ-M6**.

---

### 1.5 Category summary

| Category | Exemplar | Owns | Does **not** own | Unity's posture |
|---|---|---|---|---|
| Internal Developer Portal | Backstage (CNCF Incubating, 33.9k★) | Catalog, discovery, scaffolding, docs plane | Dependency resolution, native builds, reproducibility | **Integrate** — be catalog-*able*, don't be a catalog |
| Monorepo build platform | Pants 2.32; Nx (F500 70%+) | Build graph, caching, affected-computation, remote execution | The **native/conda half** of a data stack | **Differentiate** — conda-native is the wedge |
| SDD toolkit | spec-kit (123.7k★) | Constitution-as-governance, agent command chain | Runtime, environments, deployment | **Consume** — Constitution already in its format |
| InnerSource practice | InnerSource Commons (800+ orgs) | The social contribution model | Any tooling at all | **Adopt** — and close the named gap |

**The synthesized wedge:** *Unity Data Stack is the conda-native, air-gap-first,
spec-governed monorepo platform for Python data engineering.* Each qualifier removes an
incumbent: **conda-native** removes Pants/Nx; **air-gap-first** removes the SaaS IDPs and Nx
Cloud; **spec-governed** aligns with rather than opposes spec-kit; **monorepo platform** (as
opposed to portal) removes Backstage. Nothing found in this research occupies all four
simultaneously.

---

## Part 2 — What Changed Since the Gists (2026-01 → 2026-07)

The gists were authored between 2026-01 and 2026-05. This section is the **delta list** the PRD
must absorb. Findings are graded:

- **CONFIRMED** — the gist was right and remains right.
- **STALE** — the gist was right when written; reality moved.
- **WRONG** — the gist was incorrect when written; verified against primary source.
- **NEW** — a fact that did not exist when the gist was written.

### D1 — PEP 751 is **Final**. CONFIRMED, with a scope correction.

PEP 751 **Status: "Final"**, **Resolution: 31-Mar-2025**. The `pylock.toml` format is real,
standardized, and the toolchain spec's bet on it was correct.

**But the toolchain spec's central claim about it is WRONG.** The spec asserts:

> "**Universal Cryptographic Lockfile**: A singular `/pylock.toml` format (compliant with PEP 751
> specifications) tracks multi-platform targets (linux, macos, windows), specific target hashes,
> and file references."

PEP 751 explicitly does **not** "provide universal multi-platform lockfiles automatically;
rather, it supports environment markers to specify compatibility." Multi-platform coverage in
`pylock.toml` is achievable *only* by including packages for every target guarded by environment
markers — it is an emergent property of how the file was generated, **not a format guarantee**.
The distinction matters operationally: nothing in the format prevents a producer from emitting a
single-platform `pylock.toml` that installs cleanly on the producing machine and fails everywhere
else. Unity must therefore **verify** multi-platform coverage rather than assume it.

What PEP 751 *does* provide: install without resolution, mandatory hashes + file sizes for
machine verification, `lock-version` (currently `"1.0"`), `requires-python`, `environments`
markers, `extras`/`dependency-groups` for multi-use locks, `created-by` tool attribution, and the
`[[packages]]` array. Named variants follow `pylock.[identifier].toml`. It explicitly does **not**
lock build requirements for sdists — relevant to any air-gapped source build.

> Source: [peps.python.org/pep-0751](https://peps.python.org/pep-0751/)

### D2 — pip's `pylock.toml` support arrived, and it is **experimental**. STALE → NEW.

The toolchain spec names "**pip v26.1+ (Deploy Engine)**" as the runtime installer. This was a
*forward-looking bet that landed*:

- **pip 25.1** (2025-04-26): "Add a new, _experimental_, `pip lock` command, implementing **PEP 751**."
- **pip 26.1** (2026-04-26): "Add experimental support to read requirements from standardized
  `pylock.toml` files (`-r pylock.toml`)." — this is exactly the capability the spec's Dockerfile
  and CI both depend on (`pip install ... -r pylock.toml`).
- Latest pip: **26.1.2**, **2026-05-31**.

**The correction is the word "experimental."** Both capabilities carry that designation, meaning
breaking changes are permitted. The toolchain spec's "Zero-State Local Deployment Rule" — that
production, CI, and test runtimes "must boot securely using only the `pylock.toml` file" —
therefore rests on an **experimental pip feature**. That is a legitimate architecture, but it is a
*risk-bearing* one and the PRD must say so, with a fallback path. Recorded as **assumption A-M1**.

> Source: [pip changelog](https://pip.pypa.io/en/stable/news/)

### D3 — The toolchain spec's flagship command **does not exist**. WRONG.

The root manifest's headline task is:

```toml
lock-monorepo = "pdm export --format pylock --override-platform=linux --override-platform=macos --override-platform=windows -o pylock.toml"
```

Verified against PDM's CLI reference: `pdm export` supports `-f/--format` (choices: `requirements`
or `pylock.toml`), `--no-hashes`/`--without-hashes`, `-o/--output`, `--self`/`--editable-self`,
`--expandvars`, and the `-G/--group`/`--without`/`--no-default`/`-d/--dev`/`--prod` group flags.

**There is no `--override-platform` flag on `pdm export`.** Platform targeting lives on
`pdm lock --platform`. The format token is also `pylock.toml`, not `pylock`.

This is the single most consequential error in the intake set, because **D1 and D3 compound**:
the spec assumed the format guaranteed multi-platform coverage (it does not), *and* used a
non-existent flag to request it (it cannot). The multi-platform guarantee that the entire
"Cryptographic Predictability" outcome rests on has **no verified mechanism behind it**. Producing
one is a genuine engineering task, not a configuration line — and it is a top-tier architecture
risk for the PRD to carry.

Two viable mechanisms exist and must be traded off in the architecture (**OQ-M7**):
- `pdm lock --platform ...` (multiple invocations) → `pdm export -f pylock.toml`, then verify
  coverage; or
- **uv**, which supports `uv export --format pylock.toml` directly alongside requirements.txt and
  CycloneDX SBOM export. uv is already present in the working root at `uv >=0.9.21`.

> Sources: [pdm-project.org CLI reference](https://pdm-project.org/latest/reference/cli/),
> [docs.astral.sh/uv](https://docs.astral.sh/uv/concepts/projects/sync/)

### D4 — Pixi moved **14 minor versions** ahead of the working root's hard pin. STALE.

The working root pins pixi twice, both exactly:

```toml
requires-pixi = "==0.59.0"
pixi = "==0.59.0"       # in [dependencies]
```

**Current pixi: 0.73.0, released 2026-07-15**, available on conda-forge for **seven** platforms:
`linux-64`, `linux-aarch64`, `osx-64`, `osx-arm64`, `win-64`, `win-arm64`, `linux-ppc64le` (the
last pinned back at 0.61.0). Recent releases:

| Version | Date | Notable |
|---|---|---|
| **0.73.0** | 2026-07-15 | **`workspace = true` in environment dependency tables** — declare a version once instead of repeating it across features/targets; **TOML 1.1** (multiline inline tables, trailing commas) |
| 0.72.2 | 2026-07-09 | — |
| 0.72.0 | 2026-07-01 | Inline package manifests for Pixi Build (build metadata without separate manifests) |
| 0.71.0 | — | **Rich platforms** — system requirements beyond OS/arch, incl. CUDA and glibc versions |

Three of these land directly on Unity's stated pain points:

- **`workspace = true`** is the direct remedy for the working root's most visible smell: a
  `[feature.runtime.dependencies]` block whose first ~35 lines are *commented-out duplicates*
  annotated `# Note: Already included in base dependencies`. That whole pattern is now
  expressible natively.
- **Rich platforms (glibc/CUDA)** subsumes part of what `[system-requirements]` does by hand.
- **Inline package manifests** reduce per-package boilerplate for workspace members.

**The exact pin is also self-defeating.** `requires-pixi = "==0.59.0"` means a developer on
current pixi cannot open the workspace at all. A floor (`>=`) with a tested ceiling is the
conventional shape; the PRD should require it. Recorded as **assumption A-M2**.

> Sources: [github.com/prefix-dev/pixi/releases](https://github.com/prefix-dev/pixi/releases),
> [api.anaconda.org/package/conda-forge/pixi](https://api.anaconda.org/package/conda-forge/pixi)

### D5 — Pixi multi-package workspaces exist and are **preview**. NEW.

Pixi now supports genuine multi-package workspaces: a top-level manifest manages workspace
config; members declare dependencies as `{ path = "packages/<name>" }` and share versions via
`{ workspace = true }`. Build backends cover **CMake, Python, Rust, C++, ROS, R, Mojo**.

**Status is explicitly preview**: *"pixi-build is a preview feature, and will change until it is
stabilized."*

This matters because the working root does **not** use this mechanism. It uses
`[pypi-dependencies]` with `{ path = ..., editable = true }` for three members (`common`,
`duckdb-server`, `profile-service`) — i.e. **editable PyPI installs**, not pixi workspace
members. That is the pre-`pixi-build` idiom.

So Unity has a genuine fork in the road, and it is an **architecture decision, not a detail**:
adopt preview `pixi-build` workspaces (native, forward-looking, unstable) or stay on editable
path installs (proven, stable, less integrated). Recorded as **OQ-M8**.

> Sources: [pixi multi-environment docs](https://pixi.prefix.dev/latest/workspace/multi_environment/),
> [pixi build workspace docs](https://pixi.prefix.dev/latest/build/workspace/)

### D6 — Dagster reached 1.13 and **now supports Python 3.14**. STALE.

The working root pins `dagster = ">=1.12.8,<2"` and carries this note in
`[feature.monorepo-full-stack]`:

> "Dagster 1.12.0+: ✅ Supports Python 3.9-3.13 (from PyPI) … Note: Conda-forge dagster builds
> limited to Python 3.10 … Therefore: Constrained to Python >=3.12,<3.14"
> — plus the inline comment *"limitation on dagster that doesnt support 3.14 yet."*

**Current PyPI `dagster` is 1.13.15 with `requires_python = "<3.15,>=3.10"`** — i.e. Python 3.10
through **3.14 inclusive**. The stated blocker for Python 3.14 in the full-stack environment is
**resolved upstream**.

The `<3.14` ceiling on the `monorepo-full-stack` environment is therefore stale and should be
re-tested rather than inherited. The *conda-forge-build* half of the note (whether conda-forge's
dagster is built for 3.14) could not be verified in this run — the anaconda.org API response for
dagster exceeded the fetch size limit, and cf_atlas was unavailable (§ Limitations). Recorded as
**OQ-M9**: re-verify conda-forge dagster's Python build matrix before setting the ceiling.

> Source: [pypi.org/pypi/dagster/json](https://pypi.org/pypi/dagster/json)

### D7 — Python 3.12 is now **security-only**. STALE.

Constitution § 14.1 designates:
- Python **3.14+** preferred, **3.12** "Fully supported (legacy baseline)", **3.13** fully supported;
- CI matrix `[py312, py313, py314]` (§ 14.3);
- deprecation policy: "Support each Python version for 2 years after release" (§ 14.4).

Current CPython status as of mid-2026:

| Version | Status | First release | EOL |
|---|---|---|---|
| 3.12 | **Security** | 2023-10-02 | Oct 2028 |
| 3.13 | Bugfix | 2024-10-07 | Oct 2029 |
| 3.14 | Bugfix | 2025-10-07 | Oct 2030 |
| 3.15 | **Prerelease** (first release 2026-10-01) | — | Oct 2031 |

In **security** phase, "only security fixes are accepted" and **no new binaries are released**.
3.12 crossed that line in 2025-10 — meaning Unity's declared "legacy baseline" is a version that
receives no further binary releases.

Two consequences:
1. The Constitution's own 2-year rule, applied literally, **already expires 3.12** (released
   2023-10). The stack pins in the working root say otherwise (`python = ">=3.12.12,<3.15"`,
   `[feature.py312]`). Rule and implementation disagree; the PRD must resolve which governs.
2. **Python 3.15 first-releases 2026-10-01** — roughly ten weeks after this report. Any
   `<3.15` ceiling in the working root (`python = ">=3.12.12,<3.15"`) becomes a live constraint
   inside the planning horizon, not a theoretical one. Recorded as **assumption A-M3**.

> Source: [devguide.python.org/versions](https://devguide.python.org/versions/)

### D8 — The platform matrix leaves ARM Linux on the table. STALE.

Working root: `platforms = ["linux-64", "osx-64", "osx-arm64", "win-64"]`. Toolchain spec:
`platforms = ["linux-64", "osx-arm64", "win-64"]` (narrower still — the two gists **disagree**).

conda-forge ships pixi itself for seven subdirs including **`linux-aarch64`** and **`win-arm64`**.
Given that the Constitution mandates OpenShift/OCP production deployment, and ARM server nodes are
mainstream in 2026, the absence of `linux-aarch64` is a notable gap for a platform whose
deployment target is Kubernetes. Recorded as **OQ-M10** (is ARM64 Linux in scope for v1?).

### D9 — Delta summary table

| ID | Finding | Grade | Source of truth | PRD action |
|---|---|---|---|---|
| D1 | PEP 751 Final (2025-03-31); but **not** an automatic multi-platform guarantee | CONFIRMED + scope correction | PEP 751 | Requirement must say "verified multi-platform coverage", not assume it |
| D2 | pip 25.1 `pip lock`; pip 26.1 `-r pylock.toml`; both **experimental**; latest 26.1.2 | STALE→NEW | pip changelog | Carry as risk + fallback (A-M1) |
| D3 | `pdm export --override-platform` **does not exist**; format token is `pylock.toml` | **WRONG** | PDM CLI ref | Re-spec the lock task; trade off vs `uv export` (OQ-M7) |
| D4 | pixi 0.73.0 vs pinned `==0.59.0`; `workspace = true`, TOML 1.1, rich platforms | STALE | pixi releases | Re-pin to floor+ceiling; adopt `workspace = true` (A-M2) |
| D5 | pixi multi-package workspaces exist, **preview** | NEW | pixi build docs | Architecture decision (OQ-M8) |
| D6 | dagster 1.13.15 supports Python ≤3.14 | STALE | PyPI JSON | Re-test 3.14 ceiling (OQ-M9) |
| D7 | Python 3.12 security-only; 3.15 lands 2026-10-01 | STALE | devguide | Reset support policy (A-M3) |
| D8 | `linux-aarch64` absent; the two gists disagree on the matrix | STALE | anaconda.org | Decide ARM scope (OQ-M10) |

---

## Part 3 — Positioning

### 3.1 The four-qualifier wedge

*Conda-native · air-gap-first · spec-governed · monorepo platform.* Derivation in § 1.5. The
claim is not that each qualifier is novel — it is that **the conjunction is unoccupied** in the
comparable set examined.

### 3.2 Evidence the shape works: this repository

`local-recipes` is a **live worked example of the same shape**, and it is inspectable rather than
asserted. Its `pixi.toml` composes ~12 environments from features (`linux`, `osx`, `win`, `build`,
`grayskull`, `conda-smithy`, `local-recipes`, `vuln-db`, `gcloud`, `pyforge-warden`,
`pyforge-atlas`, `bmad-ui`), with multiple packages under `src/` (`shared`, `pyforge-atlas`,
`pyforge-warden`, `sentinel`, `prototype`).

Three transferable lessons, each of which contradicts something in the intake set:

1. **`no-default-feature = true` is the antidote to environment bloat.** Three of this repo's
   environments use it explicitly to *exclude* the fat default `[dependencies]` block, with the
   recorded rationale that loop worktrees must materialize a lean environment. The Unity working
   root's `[dependencies]` block carries ~30 packages (conda, conda-build, rattler-build, twine,
   uv, hatch, act, gh, direnv…) that **every** environment inherits, including `production`,
   `dr`, and `oss` — which are declared as minimal-footprint. The intent ("minimal production
   footprint") and the mechanism (fat base `[dependencies]`) are in direct contradiction. This is
   a concrete, evidenced defect in the working root and a strong PRD requirement.

2. **Environments should be justified individually.** This repo annotates each environment with
   *why it exists* and what it deliberately excludes. Unity declares ~20 environments, several of
   which (`vendor`, `dev`, `integration`, `testing`, `uat`) have **byte-identical feature lists**
   (`runtime, test, lint, dev, container`). Five names, one environment. Whether that is
   worthwhile (semantic naming for the 12-stage SDLC, differing only by env-vars) or waste
   (five solves of the same set) is a real design question the PRD must answer. Recorded as
   **OQ-M11**.

3. **The 12-stage SDLC is a *deployment* taxonomy, not an *environment* taxonomy.** The
   Constitution's 12 stages differ along **GitFlow branch, data classification, network posture,
   and database** — none of which is a dependency-set difference. Modelling them as pixi
   environments conflates "which packages are installed" with "which data am I allowed to touch."
   The evidence for the split: `production`, `dr`, and `oss` are all exactly `["runtime"]` — three
   stages, one environment — while their *actual* differences (Restricted vs Public data, AirGap
   vs Internet) are invisible to pixi. **OQ-M11** should be resolved in favour of separating the
   two axes.

### 3.3 Risks to the positioning

| Risk | Evidence | Severity |
|---|---|---|
| **The lockfile mechanism is unproven.** D1+D3 compound: no verified way to produce the multi-platform `pylock.toml` the design rests on | PEP 751 scope + PDM CLI ref | **High** — invalidates the "Cryptographic Predictability" outcome if unresolved |
| **Two lockfiles, two solvers.** `pixi.lock` (conda) and `pylock.toml` (PyPI) can disagree; nothing in the intake set reconciles them | Intake gists | **High** — this is the seam where "reproducible" breaks |
| **Experimental dependency in the production path.** pip's `-r pylock.toml` is experimental | pip changelog | Medium — mitigable with a pinned pip + fallback |
| **Preview dependency if pixi-build adopted** | pixi docs | Medium — avoidable by deferring |
| **Scope: the Constitution mandates a very large stack** (Dagster + Kedro + dbt + Django + Wagtail + FastAPI + React + MLflow + Nebari + 10 infra services + 11 domains) | Constitution §1.2/§1.3 | **High** — a platform mandating this much has a large compatibility surface; the working root's own `monorepo-full-stack` env exists *precisely* to detect the resulting conflicts, which is an admission of the risk |
| **Governance double-stack.** spec-kit constitution *and* BMAD Dream→spec→epics both active | § 1.3 / repo CLAUDE.md | Medium — resolvable, but must be resolved explicitly (OQ-M4) |

---

## Assumptions

| ID | Assumption | Basis | Falsifiable by |
|---|---|---|---|
| **A-M1** | pip's experimental `-r pylock.toml` is acceptable for the v1 production path, given a pinned pip version and a documented fallback (`uv pip install`, or requirements.txt export) | pip 26.1 shipped it; 26.1.2 current | A breaking change in pip 27.x |
| **A-M2** | `requires-pixi` should be a floor with a tested ceiling, not an exact pin | `==0.59.0` blocks all current installs (0.73.0) | Evidence that Unity depends on 0.59-only behaviour |
| **A-M3** | Unity targets Python 3.13/3.14 as primary, keeps 3.12 only for legacy consumers, and plans for 3.15 (2026-10-01) inside the horizon | devguide status table | A hard enterprise floor at 3.12 |
| **A-M4** | The comparable set (IDP / monorepo-build / SDD / innersource) is the right decomposition, even though the set is not provably complete | Categories derived from the intake artifacts' own vocabulary | Discovery of a direct competitor occupying all four qualifiers |
| **A-M5** | Unity is a *platform for an enterprise to run*, not a SaaS product — so competitive analysis is about **what not to rebuild**, not about market share capture | Dream: "the platform an enterprise runs on it" | A decision to productize/commercialize Unity |

## Open Questions

| ID | Question | Why it matters | Owner |
|---|---|---|---|
| **OQ-M1** | Is the comparable set complete? WebSearch was unavailable; only named sources were fetched | A missed direct competitor changes positioning | Re-run discovery search when budget allows |
| **OQ-M2** | Does **every** component of the Constitution's mandated stack exist on conda-forge, on every target platform? | Pixi-first + air-gap is void wherever it doesn't | Bulk `cf_atlas` query once the DB is available |
| **OQ-M3** | Should Unity's role matrix be expressed as a **spec-kit bundle** rather than a bespoke construct? | Avoids reinventing an upstream mechanism | Architecture |
| **OQ-M4** | **Where is the boundary between spec-kit governance and BMAD planning?** Both are active in this repo | Highest-priority ambiguity; two governance systems can contradict | PRD (must resolve) |
| **OQ-M5** | What is Unity's **Trusted-Committer-equivalent** role? Who approves a cross-team contribution? | The social half of innersource is essentially unspecified in the Constitution | PRD (must add) |
| **OQ-M6** | Is there independent 2025/26 innersource adoption data to ground the value claim? | Currently only self-reported figures | Research follow-up |
| **OQ-M7** | `pdm lock --platform` + export, or `uv export --format pylock.toml`? | D3 leaves the flagship task unimplementable as written | Architecture (must resolve) |
| **OQ-M8** | Adopt preview `pixi-build` multi-package workspaces, or stay on editable path installs? | Preview instability vs native integration | Architecture (must resolve) |
| **OQ-M9** | Is conda-forge's dagster built for Python 3.14? | Sets the real ceiling on `monorepo-full-stack` | Verify before pinning |
| **OQ-M10** | Is `linux-aarch64` in scope for v1? The two gists disagree on the matrix | OCP/K8s deployment target is increasingly ARM | PRD |
| **OQ-M11** | Should the 12-stage SDLC be modelled as pixi environments at all, given 5 are byte-identical and 3 more are `["runtime"]`? | Conflates package-set with data-classification/network axes | Architecture (must resolve) |

---

## Sources

All fetched 2026-07-25.

1. [PEP 751 — A file format to record Python dependencies for installation reproducibility](https://peps.python.org/pep-0751/) — Status: Final; Resolution: 31-Mar-2025
2. [pip release notes](https://pip.pypa.io/en/stable/news/) — 25.1 `pip lock`; 26.1 `-r pylock.toml`; 26.1.2 (2026-05-31)
3. [PDM CLI reference](https://pdm-project.org/latest/reference/cli/) — `pdm export` flags; workspaces
4. [uv — project sync/export concepts](https://docs.astral.sh/uv/concepts/projects/sync/) — `uv export --format pylock.toml`
5. [pixi — multi-environment docs](https://pixi.prefix.dev/latest/workspace/multi_environment/) — features, environments, solve-groups
6. [pixi — build workspace docs](https://pixi.prefix.dev/latest/build/workspace/) — multi-package workspaces (preview)
7. [pixi releases](https://github.com/prefix-dev/pixi/releases) — 0.73.0 (2026-07-15)
8. [conda-forge pixi package](https://api.anaconda.org/package/conda-forge/pixi) — 0.73.0, 7 subdirs
9. [github.com/backstage/backstage](https://github.com/backstage/backstage) — CNCF Incubating, 33.9k★
10. [github.com/github/spec-kit](https://github.com/github/spec-kit) — 123.7k★, `/speckit.*` commands, bundles
11. [pantsbuild.org](https://www.pantsbuild.org/) — Pants 2.32
12. [nx.dev](https://nx.dev/) — 2.5M+ daily devs, 70%+ F500
13. [innersourcecommons.org](https://innersourcecommons.org/) — 3,000+ individuals, 800+ orgs
14. [CNCF Platform Engineering Maturity Model](https://tag-app-delivery.cncf.io/whitepapers/platform-eng-maturity-model/) — 5 aspects × 4 levels
15. [PyPI dagster JSON API](https://pypi.org/pypi/dagster/json) — 1.13.15, `<3.15,>=3.10`
16. [Python Developer's Guide — Status of Python versions](https://devguide.python.org/versions/) — 3.12 security-only; 3.15 prerelease

**Local evidence (not web):** `{project-root}/pixi.toml`, `{project-root}/src/`,
`{project-root}/docs/dreams/unity-data-stack.md`, and the three intake gists under
`{project-root}/docs/intake/gists/`.
