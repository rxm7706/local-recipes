---
title: "Addendum: Unity Data Stack PRD"
created: 2026-07-25
updated: 2026-07-25
status: draft
project_slug: unity-data-stack
purpose: "Mechanism, options-considered matrices, and technical-how deferred from the PRD. Feeds the architecture stage."
---

# Addendum — Unity Data Stack PRD

The PRD states capabilities. This addendum carries the **mechanism** — the options each open
decision has, the trade-offs between them, and the technical detail an architect needs but a
requirement should not encode.

**Not duplicated here:** the intake inventory (Constitution article map, ~200-task taxonomy,
platform-conditional dependency knowledge, rejected/superseded ledger) lives in
`../../briefs/brief-unity-data-stack-2026-07-25/addendum.md`. The evidence base and every
citation live in the two research reports.

---

## A. Options considered — the lock architecture (OQ-1 / OQ-16)

The decision everything else depends on. Three coherent positions.

### A.1 The three options

| | **(a) Workspace-Lock-primary** | **(b) Standards-Lock-primary** | **(c) Split by tier** |
|---|---|---|---|
| Source of truth | `pixi.lock` (conda + PyPI) | `pylock.toml` (PEP 751, PyPI only) | Both, by artifact class |
| Derived artifact | `pylock.toml` export | — | — |
| Manifest root | `pixi.toml` | `pyproject.toml` (`[tool.pixi.*]` + `[tool.pdm.workspace]`) | Both |
| Deployment | `pixi-pack` / `pixi-unpack` bundle | `pip install -r pylock.toml` into a slim base | Per tier |
| Native components covered? | **Yes** | **No** — production base abandons conda | Infra yes, apps no |
| Air-gap posture | One mirror surface (conda channel) | Two mirror surfaces (conda for dev, PyPI for prod) | Two |
| Zero-State rule | Becomes an *export* guarantee | Holds literally | Holds for apps |
| Standards alignment | Via the derived export | Direct | Mixed |
| Intake gist backing this | The working root | The toolchain spec | Neither |

### A.2 Arguments

**For (a).** Conda-native resolution is the wedge (market research § 1.2); (b) discards it.
`pixi-pack` / `pixi-unpack` are already dependencies of the intake working root (`>=0.7.5`) and
are purpose-built for offline transport. One mirror surface is strictly less operational risk
than two. The Zero-State rule's *intent* — runtimes boot from an artifact, not from the developer
workspace — is preserved by the bundle; only the file format changes.

**Against (a).** The Exported Lock is derived, so a consumer reading only `pylock.toml` gets the
Python half. Any consumer requiring true PEP 751 fidelity for the whole environment is unserved.
Requires FR-12's drift check as ongoing machinery.

**For (b).** Simplest runtime; standards-aligned; the smallest production image; matches the
toolchain spec as written. Consumers need no pixi knowledge.

**Against (b).** Contradicts Constitution Art. II (pixi mandated for air-gap capability).
Silently changes the production runtime base (research D17 — `python:3.11-slim`, which also
contradicts the mandated Python range). Doubles the mirror surface. **And the mechanism to
produce a verified multi-platform `pylock.toml` is not yet demonstrated** — see § A.3.

**For (c).** Honest about a real difference: an infrastructure service that embeds DuckDB is not
the same artifact class as a pure-Python API. Each tier gets the mechanism that fits.

**Against (c).** Two deployment paths, two sets of failure modes, two things to document, and a
boundary that will be argued about on every new Package.

### A.3 The generation mechanism (OQ-16)

Whichever option wins, an Exported Lock with verified multi-platform coverage must be produced.
The intake spec's command is unimplementable (research D3). Two candidates:

| | **PDM route** | **uv route** |
|---|---|---|
| Command | `pdm lock --platform <p>` (per platform) → `pdm export -f pylock.toml` | `uv export --format pylock.toml` |
| Confirmed by | PDM CLI reference | uv project docs |
| Platform targeting | On `lock`, not `export` | Not yet confirmed |
| Already in the intake root? | No (`pdm` only in the toolchain spec's root deps) | **Yes** — `uv >=0.9.21` |
| Also exports | requirements.txt | requirements.txt, **CycloneDX SBOM** |

The uv route's CycloneDX export is notable: it could satisfy part of FR-39/FR-41 from the same
tool that produces the lock, potentially sidestepping OQ-6's dependency-graph concern. **Worth
testing first.**

Either way FR-11 requires that coverage be *proven* by materialization, not inferred from the
presence of environment markers.

### A.4 Consumer-side risk

pip's `-r pylock.toml` is **experimental** (added 26.1, 2026-04-26; latest 26.1.2, 2026-05-31),
as is `pip lock` (25.1). A production path depending on it needs:
- a pinned pip version,
- a documented fallback (`uv pip install`, or a requirements.txt export), and
- a watch item for pip 27.x behaviour changes.

---

## B. Options considered — Stages vs Environments (OQ-9)

### B.1 The measured problem

Twelve Stages, ~20 declared Environments, **~4 distinct dependency sets**:

| Distinct set | Stages mapping to it |
|---|---|
| `runtime, test, lint, dev, container` | vendor, dev, integration, testing, uat |
| `runtime` | production, dr, oss |
| `runtime, test, lint` | ci |
| `runtime, agentic, container` | agents |
| *(plus)* `runtime, test, lint, dev, agentic` | local |
| *(plus)* the everything-composition | public |

### B.2 Options

**(i) Collapse.** Define ~5 Environments; Stages reference them. Stage-specific difference is
carried by activation variables and deployment configuration, not by a distinct solve.
*Pro:* fewest solves, smallest cache, clearest mental model. *Con:* `pixi run -e uat` no longer
exists as an operator affordance; Stage names become configuration rather than environment names.

**(ii) Keep the 1:1 naming, share solve groups.** Twelve named Environments, but identical ones
share a solve group so the resolver work is shared.
*Pro:* preserves the operator affordance. *Con:* still N installs and N cache entries; the
duplication is merely cheaper, not removed.

**(iii) Alias.** One Environment per distinct set, plus named aliases resolving to them.
*Pro:* both properties. *Con:* depends on whether the workspace manager supports aliasing; may
need a wrapper.

`[ASSUMPTION]` (iii) is preferable if supported, (i) otherwise. Architecture must verify tooling
support.

### B.3 What a Stage actually carries

Independent of the above, a Stage needs a first-class representation carrying: branch policy,
Data Classification, network posture, datastore, promotion policy (auto vs manual approval), and
the Environment it resolves to. That is a small schema, not a pixi construct — likely a
configuration file validated on load (Constitution Art. VI § 6.3 already requires exactly this).

---

## C. Options considered — compliance-gate integration (OQ-4)

The capability exists (`pyforge-warden`, complete 2026-07-25). Four integration shapes:

| Shape | Pro | Con |
|---|---|---|
| **Library dependency** | Tightest; Unity can extend axes | Couples Unity's dependency graph to Warden's |
| **CLI in a dedicated Environment** | Clean isolation; matches the host repo's `no-default-feature` lean-env pattern | Report passed as a file; version skew possible |
| **CI action/step** | Zero local coupling | No local pre-flight; violates NFR-3 (local/CI fidelity) |
| **Tool-server (MCP)** | Agent-consumable; matches the host repo's existing surface | Adds a runtime service to the gate path |

`[ASSUMPTION]` CLI-in-a-lean-Environment is the most likely fit: it preserves NFR-3 (the same
command runs locally and in CI), avoids dependency-graph coupling, and mirrors a pattern already
proven in the host repository. The report is a file, which FR-44 requires anyway.

**Verification needed before committing** (OQ-21): does the scanner read the Workspace Lock
format and/or the Exported Lock format? Warden is documented as covering Python/Conda/**Pixi**
manifests, which is promising, but the underlying scanner's lockfile coverage was not
enumerable from its public page.

---

## D. Options considered — provenance level (OQ-7)

| Level | Requirement | Cost on hosted CI | Verdict |
|---|---|---|---|
| **L0** | none | — | Insufficient for a compliance-positioned platform |
| **L1** | Provenance exists: building entity, build process, top-level inputs. May be unsigned | Low — metadata emission | **Mandatory for v1** |
| **L2** | Signed provenance from a hosted build platform | Low-moderate — the CI already *is* a hosted build platform | **Target for v1** |
| **L3** | Hardened builds: run isolation, protected signing key material | High — needs a hardened builder | **Out of scope** |

The gap between L1 and L2 on a hosted CI runner is smaller than it looks: the platform requirement
is already met, so the work is attestation generation and signing configuration. The gap between
L2 and L3 is a different class of problem entirely (builder hardening, key custody).

Note the spec version: **SLSA v1.2 is current; v1.1 is retired.** Pin to v1.2.

---

## E. Options considered — SBOM generation (OQ-6)

The concern (research § 2.2): the intake spec's generator, in the mode the spec uses
(`--requirement <file>`), documents that "no transitive components will be identified."

**Why this may be less severe than it reads.** `pylock.toml` is fully resolved — PEP 751 records
exact packages without requiring resolution at install time — so transitive *components* are
already enumerated in the file. The generator need not walk them.

**Why it may still be severe.** What is at risk is the dependency *graph*: the CycloneDX
`dependencies` edges recording which component requires which. A flat inventory answers "do I
ship X?" but not "what reaches X?" — and the latter is what VEX exploitability analysis turns on,
which is what the CRA reporting obligation ultimately needs.

**Three generation strategies:**

| Strategy | Graph fidelity | Notes |
|---|---|---|
| From the Exported Lock (`--requirement pylock.toml`) | **Unverified — test this** | The intake spec's approach |
| From the installed environment (`--system` / `--module`) inside the built container | **High** — the graph is recoverable from installed metadata | Requires generating at build time, in the image |
| From the resolver itself (e.g. `uv export --format cyclonedx`) | Likely high — the resolver knows the graph | Depends on the § A.3 decision |

`[ASSUMPTION]` Generating inside the built container (strategy 2) is the safest default, and has
the side benefit that the SBOM describes *the artifact that ships* rather than *the lock it was
built from*. The intake spec's Dockerfile already does this. **Do the cheap empirical test first.**

**Format target:** CycloneDX **1.7** (2025-10-21) = **ECMA-424** (2025-12-10). Newly available and
relevant: `declarations` (compliance-as-code — a natural home for Constitution attestations),
ML-BOM (the mandated stack ships ML assets), VEX/VDR (exploitability exchange).

---

## F. Options considered — Package linking (OQ-9b)

| | **Editable path installs** | **Native workspace members** |
|---|---|---|
| Status | Proven, stable | **Preview** — "will change until it is stabilized" |
| Mechanism | `{ path = "…", editable = true }` under PyPI dependencies | `{ path = "…" }` members + `{ workspace = true }` shared versions |
| Build backends | Python only | CMake, Python, Rust, C++, ROS, R, Mojo |
| Used by the intake root | **Yes** (3 members) | No |
| Risk | Less integrated; members are PyPI-installed rather than workspace-resolved | Preview instability on the critical path |

`[ASSUMPTION]` Start on editable path installs (what the intake root already does and what is
stable), and treat native workspace members as a migration once the feature stabilizes. Rationale:
this is not where Unity's differentiation lives, and R-4 argues against preview features on the
critical path when a stable alternative exists.

**Counter-argument worth weighing:** if Unity ever needs to build non-Python Packages
(a compiled extension, a Rust component), native workspace members are the only path, and
migrating later is more expensive than starting there.

---

## G. Governance boundary — spec-kit and BMAD (OQ-18)

Two governance systems are live:

| | **spec-kit** | **BMAD** |
|---|---|---|
| Artifact | `constitution.md` + `/speckit.*` command chain | Dream → spec → PRD → architecture → epics/stories |
| Scope | Standing rules that govern *all* work | A single effort, from intent to implementation |
| Cadence | Amended rarely, reviewed quarterly | Per effort |
| Adoption signal | 123.7k stars; 30+ agents; extensions/presets/**bundles** | In-repo, proven across ~14 projects |

**The natural split** `[ASSUMPTION]`: spec-kit's Constitution governs **standing rules** (what is
always true of this codebase); BMAD governs **change** (how a specific effort goes from intent to
merged code). They are orthogonal — a BMAD story is *subject to* the Constitution, and a
Constitution amendment is itself a BMAD-planned effort.

Two consequences if this split is adopted:
1. Unity's Constitution stays a spec-kit artifact and remains the source for FR-26's
   classification.
2. Any Unity automation that invokes spec-kit must use the **namespaced** command forms
   (`/speckit.constitution`, not `/constitution`) — the syntax changed upstream.

**Also worth evaluating (OQ-20):** spec-kit now ships **bundles** (role-based complete setups).
The toolchain spec's five-role agent matrix is conceptually the same construct. Expressing the
role matrix as a bundle would avoid maintaining a bespoke mechanism — but would couple Unity's
role model to an upstream extension format.

---

## H. Mechanism notes carried from the intake set

Technical detail worth preserving for the architecture, extracted from the gists.

### H.1 Air-gap override variables (keep as-is)

| Variable | Overrides |
|---|---|
| `CONDA_CHANNEL_ALIAS` | Primary conda channel |
| `SELFEXPLAINML_CHANNEL_URL` | Secondary conda channel |
| `PIP_INDEX_URL` / `UV_INDEX_URL` | PyPI index |
| `GHE_HOST` / `GHE_API_BASE` | GitHub Enterprise host (also sets `GH_HOST` for the CLI) |

Centralized in a single configuration file with an apply script; a `vendors/` tree holds
pre-staged binaries for components unavailable through any mirror. **This design is sound and
should be carried forward unchanged** — it is the mechanism behind FR-14.

### H.2 The zero-state build trick

The intake spec's `pixi run --manifest-path /dev/null -p <pkg> -- <cmd>` pattern executes a tool
in an ephemeral environment with no workspace manifest in scope. Useful for build stages that
must prove they are not depending on the developer workspace. Worth keeping **if** option (b) or
(c) wins in § A; less relevant under (a), where `pixi-pack` provides the isolation.

### H.3 Known errata in the intake spec's artifacts

- `COPY libs/libs/ ./libs/` — doubled path segment (typo).
- `python:3.11-slim` + `--python-version 311` — contradicts the mandated Python range.
- `--index-url` with interpolated credentials in CI — redundant *and* unsafe: the same job already
  authenticates correctly via the setup action's `auth-host` / `auth-username` / `auth-password`
  inputs.
- `pdm export --override-platform` — flag does not exist.
- `--format pylock` — token is `pylock.toml`.

### H.4 System requirement floors (keep, re-verify)

`linux = "3.10"` (kernel; RHEL 7+ / Ubuntu 18.04+), `macos = "11.0"` (Big Sur+). These are
deliberate air-gap/enterprise-compatibility choices. Newer workspace-manager versions support
**rich platforms** (system requirements including glibc and CUDA versions), which may express
these floors more precisely.

---

## I. FR → Constitution reverse index

For readers coming from the Constitution rather than from the PRD. (Forward direction: PRD § 14.)

| Constitution locus | FRs |
|---|---|
| Art. II § 2.1–2.4 (pixi-first, forbidden commands) | FR-1, FR-10, FR-14, § 8 Constraints |
| Art. II § 2.5 (exceptions via ADR) | FR-27, FR-31 |
| Art. III § 3.1 (coverage, tests-first) | FR-20, FR-21 |
| Art. III § 3.2 (test structure) | FR-25, FR-53 |
| Art. III § 3.3 (asset test dimensions) | FR-53 |
| Art. III § 3.5 (CI gate, no coverage decrease) | FR-18, FR-20 |
| Art. IV § 4.1–4.3 (lint, format, types) | FR-19 |
| Art. IV § 4.4 (security scanning) | FR-22, FR-43 |
| Art. IV § 4.5 (pre-commit) | FR-23 |
| Art. IV § 4.6 (`check-all` == CI) | FR-18 |
| Art. V § 5.1–5.2 (docstrings, asset metadata) | FR-51 |
| Art. V § 5.3 (README per directory) | FR-32 |
| Art. V § 5.4 (ADRs) | FR-31 |
| Art. VI § 6.1 (12-stage model) | FR-9 |
| Art. VI § 6.2 (data classification) | FR-58 |
| Art. VI § 6.3–6.4 (config management, env vars) | FR-14, FR-57 |
| Art. VI § 6.5 (secrets) | FR-57 |
| Art. VII § 7.1, § 7.4 (domains, boundaries) | FR-48 |
| Art. VII § 7.2 (three layers) | FR-49 |
| Art. VII § 7.3 (naming) | FR-50 |
| Art. VII § 7.5 (data as a product) | FR-52 |
| Art. VIII § 8.1–8.2 (gitflow, conventional commits) | FR-35 |
| Art. VIII § 8.3 (PR gates) | FR-36; **FR-33 supplies the missing approver** |
| Art. VIII § 8.4 (review standards) | FR-34, FR-36 |
| Art. IX (Dagster patterns) | FR-50, FR-51, FR-53 |
| Art. X § 10.1–10.2 (CI workflows) | FR-18, FR-32 |
| Art. X § 10.3 (local CI) | FR-24 |
| Art. X § 10.4–10.6 (deployment, GitOps, containers) | FR-56 |
| Art. XI (performance) | *(not carried — see PRD § 14.2)* |
| Art. XII § 12.1 (secrets) | FR-57 |
| Art. XII § 12.4–12.5 (deps, scans) | FR-17, FR-22, FR-43, FR-46 |
| Art. XII § 12.6 (privacy) | FR-58 *(partial — see OQ-8)* |
| Art. XIII (simplicity gate) | FR-27, FR-31 |
| Art. XIV (Python versions) | § 8 Constraints *(revised)* |
| Governance (authority, amendment, enforcement, agent mandate) | FR-26, FR-28, FR-29, FR-30 |

---

## J. Deferred with reasons

| Item | Why deferred | Revisit when |
|---|---|---|
| Content-level PII detection, masking, right-to-deletion | Asserted by the Constitution with no mechanism anywhere in the intake set; a genuine sub-project | A Domain handles Restricted data in anger (OQ-8) |
| SLSA L3 | Requires a hardened builder — different class of problem | L2 is in place and an adopter requires L3 |
| Local Kubernetes development | Required cluster tool unavailable on the mandated channel; container engine unavailable for one platform on that channel | The tool lands on the channel, or vendoring is accepted |
| The remaining ten Domains | Adoption work, not build work; the pattern is what v1 proves | Per-Domain, on demand (OQ-2) |
| Catalog/portal integration | Non-goal for v1; emit catalog-consumable facts and stop | An adopter runs a portal and asks |
| Remote build caching / distributed execution | Non-goal; orthogonal to the wedge | Build times become the binding constraint |
| Instance bootstrapping | Depends on `pyforge-genesis`, unbuilt | Genesis ships |
| Independent innersource adoption data | Web-search discovery unavailable during research | Budget allows (OQ-23) |
