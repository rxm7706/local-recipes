---
title: Unity Data Stack
created: 2026-07-25
updated: 2026-08-01
status: draft
project_slug: unity-data-stack
currency_review: Reviewed 2026-08-04 — spec/brief timestamp bump was structural (project relocation / memlog story-completion recording), not content drift; PRD unchanged.
mode: headless / express — [ASSUMPTION] tags mark inferences; no user was present
inputs:
  - "planning-artifacts/briefs/brief-unity-data-stack-2026-07-25/brief.md"
  - "planning-artifacts/briefs/brief-unity-data-stack-2026-07-25/addendum.md"
  - "planning-artifacts/research/market-enterprise-innersource-python-platform-research-2026-07-25.md"
  - "planning-artifacts/research/domain-enterprise-python-platform-engineering-research-2026-07-25.md"
  - "docs/intake/gists/spec-kit/constitution.md (v1.2.0, ratified 2025-11-20)"
  - "docs/intake/gists/unity-data-stack-pixi-toml/Unity-Data-Stack-Pixi.toml (1,726 lines)"
  - "docs/intake/gists/bmad-method-spec-enterprise-monorepo-cross-platform-deployme/*.md"
  - "docs/dreams/unity-data-stack.md (Tier-0 Dream)"
---

# PRD: Unity Data Stack

## 0. Document Purpose

This PRD is for the architecture stage that follows it, for the platform team who will build
Unity, and for the enterprise stakeholders who must decide whether to adopt it. It is
**capability-oriented**: it states what the platform must do and how that will be verified.
Mechanism — which tool, which flag, which file layout — belongs in `addendum.md` and in the
architecture document, except where a specific technology is itself a **requirement inherited
from the Constitution**, in which case the provenance is cited (see § 14).

Structure: a Glossary anchors vocabulary (§ 3); features group globally-numbered Functional
Requirements (§ 5); cross-cutting quality lives in its own section (§ 6); enterprise and
regulated-domain concerns get dedicated sections (§ 7–9, § 13); and two sections exist that a
generic PRD would not have — **§ 14 Constitution Provenance Map** (every mandate traced to the
requirement that carries it) and **§ 15 Research Deltas** (every intake claim that research
falsified, with the correction).

**This PRD builds on prior artifacts and does not duplicate them.** The product brief
(`briefs/brief-unity-data-stack-2026-07-25/brief.md`) carries positioning and the problem
narrative; its `addendum.md` carries the full intake inventory — the Constitution's 14-article
map, the ~200-task taxonomy, the platform-conditional dependency knowledge, and the
rejected/superseded ledger. The two research reports carry the evidence base and every citation.

`[ASSUMPTION]` This PRD was produced headless with no user present. Every inferred value is
tagged inline and indexed in § 17. **Nothing tagged `[ASSUMPTION]` should be treated as
confirmed scope.**

---

## 1. Vision

Unity Data Stack is the **conda-native, air-gap-first, spec-governed monorepo platform for
enterprise Python data engineering** — one shared repository where teams across an organization
co-contribute reusable templates, plugins, libraries, components, services, dashboards, reports,
and applications on a single opinionated toolchain.

The value is not the monorepo. It is that **six problems get solved once instead of once per
team**: resolving native dependencies, reproducing an environment offline, satisfying
supply-chain compliance, deploying to OpenShift, testing across platforms, and letting another
team contribute without breaking anything. Each team currently solves these slightly
differently, and the organization pays for the difference forever — in onboarding time, in
duplicated internal libraries, in audits measured in weeks, and in the quiet conclusion that
sharing code across teams is more trouble than it is worth.

Unity's distinguishing property is that its reproducibility guarantee covers the **whole** stack.
Wheel-native monorepo platforms resolve Python packages; a data platform is also made of DuckDB,
Arrow's ABI, PostgreSQL client libraries, nginx, and Node. Unity resolves both halves together,
offline, on every supported platform — and emits the compliance evidence to prove what it
resolved.

**Unity assembles more than it invents.** Realized capability in the host repository —
`pyforge-warden` (multi-axis compliance gating), `conda-forge-expert` and 769 maintained
feedstocks (conda-native supply), the `enterprise-airgap` routing doctrine, `pyforge-atlas`
(dependency intelligence) — covers a large fraction of the intake ambition. Unity is principally
an **integration and governance** effort, plus genuinely new work on the lock architecture, the
governance split, and the contribution model.

---

## 2. Why Now

Timing is load-bearing, for two independent reasons.

**The regulatory clock.** The EU Cyber Resilience Act entered into force 2024-12-10.
**Vulnerability-reporting obligations begin 2026-09-11** — approximately seven weeks after this
document's date — requiring manufacturers to report actively exploited vulnerabilities. Main
obligations, covering the full product lifecycle, apply **2027-12-11**. Obligations propagate
through the value chain, so an internal platform feeding products placed on the EU market
inherits the evidentiary burden. "Know what you ship, continuously" moves from good practice to
dated legal duty inside this PRD's planning horizon.

`[ASSUMPTION]` CRA is treated as a **design forcing-function and a capability Unity must be able
to discharge** — not as an assertion that every Unity deployment is regulated. Applicability
depends on whether the adopting enterprise places products with digital elements on the EU
market. See OQ-3 and OQ-16.

**The artifact decay clock.** Three substantial intake artifacts exist — a 37 KB Constitution,
a 1,726-line working pixi root, a 12 KB toolchain spec — authored 2026-01 → 2026-05 and never
landed in a repository. Research has now verified that they have measurably drifted (§ 15):
pixi has moved 14 minor versions past a hard exact pin that blocks installation outright; a
flagship command depends on a flag that does not exist; Python 3.12 has gone security-only and
3.15 first-releases 2026-10-01. **The work either lands soon or the intake set needs
re-verification from scratch.**

---

## 3. Target User

### 3.1 Jobs To Be Done

- **Ship a data product** without becoming a toolchain administrator first.
- **Install a colleague's internal library** and have it work on the first attempt.
- **Reproduce an environment** offline, on a different OS, months later, byte-for-byte.
- **Contribute a fix** to shared code owned by another team, and have it land in days.
- **Answer "what is in our estate, and is any of it being exploited right now?"** continuously,
  with evidence, without a person walking N repositories.
- **Set a standard once** and have it hold, without policing it by hand.
- **Deploy behind a firewall** as the ordinary path, not as a project.
- **Onboard a new engineer** without transferring tribal knowledge.

### 3.2 Non-Users (v1)

`[ASSUMPTION]` These audience boundaries were inferred from the Dream and the intake artifacts,
not confirmed with a stakeholder.

- **Teams outside Python/data.** Unity is Python-first by mandate; a front-end-only or JVM team
  is not a v1 audience (Node tooling exists only in service of Python-backed applications).
- **Organizations wanting a hosted SaaS platform.** Unity is a platform an enterprise runs.
- **Teams needing a service catalog/portal.** That is Backstage's job; see § 10.
- **Single-team projects.** Unity's cost is justified by cross-team sharing. One team with one
  service should not adopt it.

### 3.3 Key User Journeys

Unity is developer infrastructure, so journeys are scoped to the moments where the platform's
value or failure is actually felt. Four carry the product.

- **UJ-1. Dana joins the `cdo` team and is productive before lunch.**
  Dana is a data engineer, first day, laptop freshly imaged, no prior context on this
  organization's toolchain. Entry state: repository access, nothing installed but git.
  Path: she clones, runs the documented bootstrap command, and pixi materializes the
  `local-dev` environment; she runs the task that starts the local stack; she opens the Dagster
  UI and sees assets running against a local DuckDB. Climax: she edits an asset, runs the
  package's test task, and it passes — without having asked anyone a question. Resolution: she
  has a working environment identical to CI's and knows the four commands that matter.
  **Edge case:** her machine is behind the corporate proxy with no public internet — she sources
  the air-gap configuration and the same commands work against the internal mirror.

- **UJ-2. Marcus installs a library another domain published, and it just works.**
  Marcus works in `customer`; the `cdo` team published a shared analytics library that depends on
  DuckDB, PyArrow, and a PostgreSQL client. Entry state: an existing working environment.
  Path: he adds the dependency, the Workspace re-solves, and the native components resolve
  alongside the Python ones. Climax: `import` works first try; no ABI error, no manual system
  package, no day lost. Resolution: he uses the shared Package instead of writing a second one.
  **Edge case:** the solve genuinely conflicts — the platform reports which package and which
  constraint, and the compatibility-detection Environment (§ 5.1, FR-7) has usually caught it
  before he did.

- **UJ-3. Priya fixes a bug in code her team does not own.**
  Priya finds a defect in a shared Package owned by another Domain. Entry state: she has the fix
  in her head and no commit rights on that Package. Path: she reads the Package's declared
  ownership, opens a branch following the documented contribution path, writes the regression
  test the standard requires, and opens a PR; the automated gates run; the **Trusted Committer**
  for that Package is auto-requested as reviewer. Climax: the Trusted Committer reviews and
  merges — days, not quarters. Resolution: the fix is in the shared Package; there is no fork.
  **Edge case:** the Trusted Committer disagrees with the approach — the disagreement is resolved
  in the PR against the Constitution's stated Mandates rather than by seniority.

- **UJ-4. Sam answers the auditor before the meeting ends.**
  Sam owns compliance. Entry state: an auditor asks what open-source components are in the
  production estate, under what licences, and whether anything is being actively exploited.
  Path: Sam retrieves the Compliance Report and SBOM produced by the most recent build of each
  deployed artifact. Climax: the answer is a generated artifact carrying Provenance, not a
  three-week reconciliation exercise. Resolution: Sam files it. **Edge case:** a component *is*
  affected by an actively-exploited vulnerability — the platform already flagged it and the
  remediation PR is open.

---

## 4. Glossary

Downstream artifacts must use these terms exactly.

- **Workspace** — the single Unity repository root; the unit that defines shared configuration,
  the supported-platform matrix, and the set of Packages.
- **Package** — one independently-manifested unit inside the Workspace (a shared library, an
  infrastructure service, or a domain service). Has an owner, a manifest, and tests.
- **Feature** — a named, reusable block of dependency and configuration declarations.
  Features compose into Environments. (Pixi terminology, adopted deliberately.)
- **Environment** — a named, solvable composition of Features that a developer or CI job
  activates. One Environment is active at a time.
- **Stage** — one of the twelve points in the delivery lifecycle (`public`, `local`, `agents`,
  `vendor`, `dev`, `ci`, `integration`, `testing`, `uat`, `production`, `dr`, `oss`). A Stage
  carries a branch policy, a Data Classification, a network posture, and a datastore.
  **A Stage is not an Environment** — see FR-9.
- **Data Classification** — one of `Public`, `Deidentified`, `Proprietary`, `Restricted`,
  attached to a Stage and governing what data may be present.
- **Domain** — a business-owned area (e.g. `customer`, `cdo`) that owns Data Products and the
  Packages that produce them.
- **Data Product** — a Domain's published analytical output, versioned and contract-bearing.
- **Layer** — one of `Raw`, `Curated`, `Consumption`; the stage of refinement of a Data Product.
- **Asset** — an orchestrated unit of computation producing part of a Data Product.
- **Lockfile** — a resolved, hash-bearing record sufficient to reproduce an Environment without
  re-resolution.
- **Workspace Lock** — the authoritative Lockfile covering both native and Python packages.
- **Exported Lock** — a derived, standards-format Lockfile (PEP 751 `pylock.toml`) generated
  from the Workspace Lock for consumers that cannot read the Workspace Lock.
- **Compliance Report** — the schema-validated machine-readable output of the compliance gate,
  covering hygiene, security, licence, and currency findings.
- **SBOM** — a Software Bill of Materials describing the components of a built artifact.
- **Provenance** — a signed or unsigned attestation describing how an artifact was built.
- **Constitution** — the governing standards document; the source of Unity's mandates.
- **Mandate** — a Constitution rule. Either a **Platform Invariant** (binding everywhere, not
  overridable) or a **Domain Default** (overridable by a Domain with recorded justification).
- **Trusted Committer** — the named role, per Package, accountable for reviewing and accepting
  contributions from outside the owning team.
- **Quality Gate** — the single command that runs every automated check, byte-identical to what
  CI runs.
- **Air-Gap Mode** — operation with no public network egress, all dependencies served from
  internal mirrors.
- **Offline Bundle** — a self-contained, transportable artifact sufficient to materialize an
  Environment with no network access at all.

---

## 5. Features

Nine features, FR-1 through FR-60.

### 5.1 Workspace Substrate

**Description.** The Workspace is the foundation: one root that declares the supported platform
matrix, the shared channels and mirrors, the Features, the Environments, and the set of
Packages. Every other feature stands on it. Realizes UJ-1, UJ-2.

The intake working root proves the shape works and simultaneously demonstrates three defects the
substrate must not reproduce: an exact toolchain pin that blocks installation, a fat base
dependency block inherited by environments declared minimal, and ~35 lines of commented-out
duplicate declarations standing in for a feature the toolchain now provides natively (see
brief addendum § C.4).

**Functional Requirements**

#### FR-1: Single Workspace root

A platform engineer can declare, in one Workspace root, the supported platform matrix, the
package channels, the minimum system requirements, and the set of Packages.

**Consequences (testable):**
- The root declares a platform matrix; every declared platform resolves.
- The root declares minimum OS/kernel floors, and a machine below the floor fails with a
  diagnostic naming the unmet requirement rather than an opaque solver error.
- Adding a Package requires editing exactly one place in the root.

#### FR-2: Toolchain version pinned as a range, never an exact equality

The Workspace declares its required workspace-manager version as a floor with a tested ceiling.

**Consequences (testable):**
- A developer on any toolchain version within the declared range can open the Workspace.
- A developer below the floor gets a diagnostic naming the required minimum.
- **Provenance/delta:** supersedes the intake root's `requires-pixi = "==0.59.0"`, which blocks
  every current install (research D4). See § 15.

#### FR-3: Environments compose from Features with no inherited bloat

Environments are composed from named Features, and an Environment declared minimal contains only
what it declares.

**Consequences (testable):**
- Every Environment declares which Features it composes and why it exists.
- Environments declared minimal-footprint (`production`, `dr`, `oss`) do **not** contain build
  tooling, package-authoring tooling, or developer utilities.
- The installed size of a minimal Environment is measured and asserted against a documented
  ceiling; regressions fail the Quality Gate.
- **Provenance/delta:** supersedes the intake root's fat base dependency block, inherited by
  every Environment including those declared minimal (brief addendum § C.4.2).

#### FR-4: No duplicated dependency declarations

A dependency version is declared once in the Workspace and referenced elsewhere.

**Consequences (testable):**
- No dependency version string appears twice across the root's Features and targets.
- A lint check fails the Quality Gate on duplication.

#### FR-5: Per-Package manifests with declared ownership

Each Package carries its own manifest declaring its dependencies, its tests, its owning Domain
or team, and its Trusted Committer.

**Consequences (testable):**
- Every Package resolves an owner and a Trusted Committer; a Package with neither fails the gate.
- Package-scoped tasks (test, lint) exist for every Package and are discoverable uniformly.

#### FR-6: Platform-conditional dependency handling

The Workspace expresses dependencies that are unavailable on a subset of platforms, with the
reason recorded, and still resolves on every declared platform.

**Consequences (testable):**
- Each platform-conditional declaration carries a machine-readable reason code and a
  human-readable note (e.g. "conda-forge lacks `python-quickjs` on osx-arm64").
- Every declared platform resolves; a platform that cannot resolve is either removed from the
  matrix or has its blocker recorded.
- **Provenance:** preserves the hard-won portability knowledge in the intake root
  (brief addendum § C.5) rather than rediscovering it.

#### FR-7: Cross-stack compatibility detection

The Workspace provides an Environment that composes the full mandated library set for the
purpose of detecting cross-library conflicts before they reach a Domain.

**Consequences (testable):**
- The compatibility Environment solves, or fails with a named conflicting pair.
- It runs on a schedule and on dependency-changing PRs.
- It is explicitly not a deployable Environment.
- **Provenance:** the intake root's `monorepo-full-stack` environment, kept — an unusually good
  idea, and an honest acknowledgement of the mandated stack's compatibility surface.

#### FR-8: Excluded Packages carry their exclusion reason

A Package excluded from the default composition records why, and the exclusion is discoverable.

**Consequences (testable):**
- Each exclusion states the blocking conflict and the condition under which it would be revisited.
- **Provenance:** `airflow-server` (SQLAlchemy <2.0 conflict with the orchestrator) and
  `sharepoint-mcp-server` (pyjwt conflict) are carried forward as documented exclusions.

#### FR-9: Stages are modelled separately from Environments

The twelve Stages are represented as a first-class concept distinct from Environments, carrying
branch policy, Data Classification, network posture, and datastore.

**Consequences (testable):**
- A Stage resolves to exactly one Environment; multiple Stages may share one Environment.
- Changing a Stage's Data Classification does not require re-solving an Environment.
- The number of distinct solved Environments is bounded by genuine dependency-set variation, not
  by the Stage count.
- **Provenance/delta:** the intake root declares ~20 Environments in which five are byte-identical
  (`vendor`/`dev`/`integration`/`testing`/`uat`) and three more are identical (`production`/`dr`/
  `oss`) — twelve Stages collapsing to roughly four dependency sets (brief addendum § B.1).
  See OQ-9.

**Notes.** `[NOTE FOR PM]` FR-9 is the one requirement in this feature that changes the intake
design rather than correcting it. It is stated as a requirement because the conflation has a
measurable cost (eight redundant solves), but the counter-argument — that semantic Environment
names are a valuable operator contract — is real. Architecture must decide (OQ-9).

---

### 5.2 Dependency Resolution and Lock Architecture

**Description.** The reproducibility guarantee. Unity resolves native and Python packages
together and produces a Workspace Lock that reproduces an Environment on every supported
platform, offline. Consumers that cannot read the Workspace Lock get an Exported Lock in the
PEP 751 standard format, derived from it. Realizes UJ-1, UJ-2.

This is the feature the intake set got most wrong, and the correction is load-bearing: PEP 751
does **not** guarantee multi-platform coverage (it uses environment markers), and the intake
toolchain spec's flagship generation command uses a flag that does not exist. The
"Cryptographic Predictability" outcome it promised currently has no verified mechanism (§ 15,
D1 + D3).

**Functional Requirements**

#### FR-10: One authoritative Workspace Lock covering both native and Python packages

The Workspace produces a single Lockfile that records resolved native (conda) and Python (PyPI)
packages together, with hashes.

**Consequences (testable):**
- The lock reproduces an identical Environment on a clean machine with no resolution step.
- Native components (database engines, columnar libraries, web servers, language runtimes) are
  covered by the same guarantee as Python packages.
- The lock is committed to version control.

#### FR-11: Multi-platform coverage is verified, not assumed

For every declared platform, the Workspace proves the lock is sufficient to materialize the
Environment on that platform.

**Consequences (testable):**
- A gate materializes each Environment on each declared platform (natively or via emulation) and
  fails if any platform is uncovered.
- Coverage is reported per platform, not as a single boolean.
- **Provenance/delta:** the intake toolchain spec asserted the lockfile format guarantees
  multi-platform targets; PEP 751 explicitly does not (§ 15, D1).

#### FR-12: Exported Lock in PEP 751 format, derived from the Workspace Lock

The Workspace generates a PEP 751 `pylock.toml` from the Workspace Lock for standards-consuming
tools.

**Consequences (testable):**
- The Exported Lock validates against PEP 751 `lock-version` 1.0.
- Regenerating it from an unchanged Workspace Lock is byte-stable.
- A drift check fails the Quality Gate when the Exported Lock does not match the Workspace Lock.
- `[ASSUMPTION]` The Workspace Lock is authoritative and the Exported Lock is derived
  (pixi-primary). The reverse direction and a split-by-tier variant are live alternatives —
  **this is the single decision everything downstream depends on** (OQ-1).

#### FR-13: Offline Bundle for air-gapped materialization

The Workspace produces a transportable Offline Bundle that materializes a named Environment with
no network access.

**Consequences (testable):**
- A machine with no network egress materializes the Environment from the bundle alone.
- The bundle records which Environment and which lock it was built from.
- Bundle production is a documented, repeatable task.

#### FR-14: Mirror routing by environment variable only

All package sources are redirectable to internal mirrors through environment variables, with no
edit to any committed manifest.

**Consequences (testable):**
- The same committed manifest resolves against public sources and against internal mirrors,
  selected only by environment.
- No mirror hostname is required in any committed file for Air-Gap Mode to work.
- **Provenance:** Constitution Art. II § 2.2 (air-gap capability); the intake root's
  `CONDA_CHANNEL_ALIAS` / `PIP_INDEX_URL` / `UV_INDEX_URL` / `GHE_HOST` design, kept.

#### FR-15: Credentials never appear in URLs or command lines

Registry credentials are supplied through a credential store or masked runner inputs, never
interpolated into index URLs, manifests, lockfiles, or command arguments.

**Consequences (testable):**
- No committed file contains a credential-bearing URL, including variable-interpolated forms.
- No CI step passes a credential as a command-line argument.
- A scan for credential-bearing URL patterns fails the Quality Gate.
- **Provenance/delta:** the intake toolchain spec declares a Token Isolation Rule and then
  violates its spirit with `https://${USER}:${TOKEN}@…` in `extra-index-urls` and a
  `--index-url` interpolation in CI (brief addendum § D.1, research § 4.3).

#### FR-16: Credentials are attached per host

Outbound requests receive credentials only for the host those credentials belong to.

**Consequences (testable):**
- A request to a host other than the configured registry carries no registry credential.
- A test asserts non-attachment for a non-matching host.
- **Provenance:** closes the known `JFROG_API_KEY` unconditional-injection defect recorded in
  the `enterprise-airgap` Dream, at the platform level.

#### FR-17: Dependency update policy is explicit and recorded

Packages held back from automatic updating are listed with a reason and a revisit condition.

**Consequences (testable):**
- Every held-back package has a recorded reason (LTS pin, transitive constraint, known breakage).
- A held-back package with no reason fails the gate.
- **Provenance/delta:** the intake root holds ten packages back in an inline command comment with
  no recorded rationale (brief addendum § C.6).

---

### 5.3 Quality Gate

**Description.** One command runs every automated check, and it is byte-identical to what CI
runs. This is what makes "it passed locally" a guarantee instead of a hope, and it is the
mechanism by which the Constitution stops being a wiki page. Realizes UJ-1, UJ-3.

**Functional Requirements**

#### FR-18: Single Quality Gate command with CI parity

A developer runs one command that executes every check CI executes.

**Consequences (testable):**
- The set of checks run locally equals the set run in CI; a parity test asserts this and fails
  when they diverge.
- Local pass predicts CI pass; the green-local/red-CI rate is measured (SM-3).
- **Provenance:** Constitution Art. IV § 4.6 — "This matches exactly what CI runs."

#### FR-19: Lint, format, and type checking

The Quality Gate enforces linting, formatting, and static type checking across Python, and
configuration formats (TOML, YAML, SQL).

**Consequences (testable):**
- A style or type violation fails the gate with a file and line reference.
- Formatting is auto-correctable by a documented command.
- **Provenance:** Constitution Art. IV § 4.1–4.3.

#### FR-20: Test coverage thresholds enforced

The Quality Gate enforces the Constitution's coverage requirements and fails on regression.

**Consequences (testable):**
- Asset-producing code meets the mandated 100% coverage threshold; other Python modules meet the
  mandated 80% minimum.
- Coverage that decreases relative to the base branch fails the gate.
- **Provenance:** Constitution Art. III § 3.1, § 3.5.

#### FR-21: Tests precede implementation for new code, and regressions precede fixes

New capability lands with its tests; a bug fix lands with a test that fails without the fix.

**Consequences (testable):**
- The contribution standard states the requirement and review verifies it.
- `[ASSUMPTION]` Enforcement is by review rather than by automation — automated
  test-before-implementation detection is unreliable. See OQ-13.
- **Provenance:** Constitution Art. III § 3.1.

#### FR-22: Security scanning in the Quality Gate

Static code security analysis and dependency vulnerability scanning run in the gate.

**Consequences (testable):**
- A finding above the configured severity threshold fails the gate.
- Findings carry a stable identifier so they can be baselined and tracked.
- **Provenance:** Constitution Art. IV § 4.4, Art. XII § 12.5. Implementation via the
  Compliance Report (§ 5.6) rather than a separate mechanism.

#### FR-23: Pre-commit hooks mirror a subset of the gate

Fast checks run at commit time; the full gate runs on demand and in CI.

**Consequences (testable):**
- Commit-time checks complete within a documented time budget (NFR-4).
- Every commit-time check is also in the full gate.
- **Provenance:** Constitution Art. IV § 4.5.

#### FR-24: Local CI execution

A developer can execute the CI workflows locally before pushing.

**Consequences (testable):**
- A documented command runs the CI workflow set locally.
- **Provenance:** Constitution Art. X § 10.3; the intake root's `act-ci-*` tasks.

#### FR-25: Behavioural test tier with selectable slices

The Workspace supports behaviour-level tests alongside unit tests, selectable by tag.

**Consequences (testable):**
- A smoke slice runs in under the documented budget and is usable as a fast pre-merge signal.
- Slices are selectable by tag (smoke, integration, per-Domain).
- **Provenance/delta:** present in the intake root (behave, with `@smoke`/`@integration` tags) and
  **absent from the Constitution's Art. III**, which describes only unit/integration/asset tiers.
  Article III should be amended (§ 14.3).

---

### 5.4 Constitution and Governance

**Description.** Unity's standards are machine-enforced, and the Constitution is the source. The
central new work is the **global-versus-local split**: which Mandates are Platform Invariants
binding everywhere, and which are Domain Defaults a Domain may override with recorded
justification. Without that split Unity is centrally imposed rather than innersource, and it
violates the federated half of federated computational governance. Realizes UJ-3.

**Functional Requirements**

#### FR-26: Every Mandate is classified as Platform Invariant or Domain Default

The Constitution classifies each Mandate, and the classification is machine-readable.

**Consequences (testable):**
- Every Mandate resolves to exactly one classification; an unclassified Mandate fails the gate.
- Platform Invariants cannot be overridden by any Package or Domain.
- **Provenance/delta:** the Constitution currently declares itself uniformly "immutable" and
  "non-negotiable", which conflicts with Data Mesh principle 4 (research § 3.1). See OQ-5.

#### FR-27: Domain Default overrides require a recorded decision

A Domain overriding a Domain Default records the decision, its rationale, its alternatives, and
its consequences.

**Consequences (testable):**
- An override without a linked decision record fails the gate.
- Overrides are enumerable — a reader can list every active override and its reason.
- **Provenance:** Constitution Art. V § 5.4 (ADRs), Art. II § 2.5, Art. XIII § 13.3, generalized
  from pixi-scoped exceptions to all Domain Defaults.

#### FR-28: Violations report the clause they violate

An automated check that fails a Mandate names the Constitution section and clause.

**Consequences (testable):**
- Every Mandate-enforcing check carries the identifier of the clause it enforces.
- A failure message includes that identifier.
- **Provenance:** Constitution Governance § Agent Mandate — "Agents MUST report audit failures by
  referencing the specific section and clause."

#### FR-29: Mandates without an enforcing check are visible

The platform reports which Mandates are automatically enforced and which rely on human review.

**Consequences (testable):**
- A coverage report lists every Mandate and its enforcement status.
- A Mandate claimed as enforced with no corresponding check fails the report.

#### FR-30: Constitution amendment is a governed, versioned process

Amendments follow a defined process and the document carries a version and ratification date.

**Consequences (testable):**
- The Constitution carries semantic version, ratified date, amended date, and next-review date.
- An amendment produces a log entry describing what changed and why.
- A review date in the past raises a warning.
- **Provenance/delta:** Constitution Governance § Amendment Process. The intake Constitution is
  v1.2.0 with `Next Review: 2026-02-20` — **already five months overdue** (brief addendum § A.2.5).

#### FR-31: Architecture decisions are recorded

Significant technical decisions are captured as decision records with context, alternatives,
decision, and consequences.

**Consequences (testable):**
- The decision record set is discoverable and indexed.
- A change matching the Constitution's complexity-gate criteria without a decision record fails
  review.
- **Provenance:** Constitution Art. V § 5.4, Art. XIII § 13.3.

#### FR-32: Documentation exists where the Constitution requires it

Every major directory carries documentation covering purpose, setup, usage, dependencies, and
ownership.

**Consequences (testable):**
- A check fails when a Package or major directory lacks the required documentation.
- Documentation links resolve (link check in the gate).
- **Provenance:** Constitution Art. V § 5.3, Art. X § 10.1.

---

### 5.5 Innersource Contribution Model

**Description.** The largest gap in the intake set, found independently from two research angles.
The Constitution requires "at least one human approval" and never says whose; the toolchain
spec's role matrix omits every feedback-loop role. For a platform whose entire premise is
cross-team co-contribution, **the social layer is essentially unspecified**. This feature
supplies it. Realizes UJ-3, UJ-1.

**Functional Requirements**

#### FR-33: Every Package has a named Trusted Committer

Each Package declares one or more Trusted Committers accountable for reviewing and accepting
outside contributions.

**Consequences (testable):**
- Every Package resolves at least one Trusted Committer; a Package without one fails the gate.
- The Trusted Committer is auto-requested as reviewer on a PR touching that Package.
- The role's responsibilities and expected response window are documented.
- **Provenance/delta:** supplies what Constitution Art. VIII § 8.3 leaves undefined
  (research OQ-M5).

#### FR-34: A documented contribution path for outside contributors

A contributor from outside the owning team can find, in one place, how to contribute to a
Package they do not own.

**Consequences (testable):**
- The path covers: finding the owner, branch convention, required tests, review expectation, and
  escalation when the Trusted Committer does not respond.
- A new contributor completes a first contribution using only written documentation.
- **Provenance:** InnerSource Commons practice (Trusted Committer, host team, contributor);
  absent from the intake set.

#### FR-35: Branch and commit conventions are enforced

The Workspace enforces its branching model and commit message convention automatically.

**Consequences (testable):**
- A non-conforming PR title or commit fails an automated check.
- The default integration branch is explicit and documented.
- **Provenance:** Constitution Art. VIII § 8.1–8.2. `[NOTE FOR PM]` The Constitution mandates
  Gitflow with `develop` as default — **this conflicts with the host repository's trunk-based
  `main` convention**. Unity is a separate repository so there is no direct collision, but the
  choice should be re-confirmed rather than inherited (OQ-11).

#### FR-36: Merge gates are explicit and automated

The conditions for merge are enumerated and machine-checked where possible.

**Consequences (testable):**
- All seven Constitution PR gates are represented; each is marked automated or human.
- A PR cannot merge with any automated gate failing.
- **Provenance:** Constitution Art. VIII § 8.3.

#### FR-37: Scaffolding templates for new Packages and Data Products

A contributor generates a conforming new Package or Data Product from a template.

**Consequences (testable):**
- A generated Package passes the Quality Gate immediately, with no manual fixes.
- Templates cover at minimum: shared library, service, and Data Product.
- Starting from a template is the documented default path.
- **Provenance:** Constitution § 1.3 (`templates/` for agentic code generation).

#### FR-38: Contribution and reuse are measured

The platform reports cross-team contribution and shared-library reuse over time.

**Consequences (testable):**
- Reports distinguish contributions to owned versus non-owned Packages.
- Reports surface internal forks/duplicates as a counter-signal.
- Validates SM-2 and SM-C1.

---

### 5.6 Supply-Chain Compliance and Evidence

**Description.** Compliance is a build artifact, not an activity. Every built artifact carries an
SBOM and Provenance; the estate is continuously gated against actively-exploited vulnerability
data. This is the feature the regulatory clock (§ 2) makes urgent — and it is largely
**integration** work: `pyforge-warden` already implements a strict superset of the intake spec's
approach. Realizes UJ-4.

**Functional Requirements**

#### FR-39: Versioned SBOM for every built artifact

Every artifact produced for deployment carries an SBOM in a declared, version-pinned standard
format.

**Consequences (testable):**
- The SBOM validates against the declared specification version.
- The specification version is pinned and recorded, not implicit.
- The SBOM is attached to or discoverable from the artifact.
- **Provenance/delta:** the intake spec emits unversioned CycloneDX; CycloneDX 1.7 is now
  **ECMA-424**, so "CycloneDX" alone no longer identifies a single contract (research § 2.1).

#### FR-40: Runtime-scoped and full SBOM variants

The platform produces both a runtime-scoped SBOM (deployed components only) and a full SBOM
(including development and test components).

**Consequences (testable):**
- The runtime SBOM contains no development-only or test-only component.
- Both are produced from the same resolved source and are mutually consistent.
- **Provenance:** the intake spec's `sbom-prod` / `sbom-full` split, kept.

#### FR-41: SBOM carries a dependency graph, not a flat component list

The SBOM records dependency relationships between components, not merely their presence.

**Consequences (testable):**
- The SBOM's dependency relationships are populated and non-trivial.
- A test asserts that a known transitive relationship appears as an edge.
- **Provenance/delta:** the intake spec's generator, in the mode the spec uses, carries a
  documented "no transitive components will be identified" caveat. A flat inventory answers
  "do I ship X?" but not "what reaches X?" — which is what exploitability analysis requires
  (research § 2.2). **Verify empirically and early** (OQ-6).

#### FR-42: Build Provenance attestation

Every built artifact carries an attestation describing how it was built.

**Consequences (testable):**
- The attestation records the building entity, the build process, and the top-level inputs
  (SLSA Build L1 minimum).
- `[ASSUMPTION]` v1 targets **L1 mandatory, L2 (signed provenance from a hosted build platform)
  as the goal**; L3 is out of scope. See OQ-7.
- **Provenance/delta:** provenance is **entirely absent** from the intake set. SBOM says what is
  *in* an artifact; nothing said how it came to be (research § 2.3).

#### FR-43: Continuous vulnerability gating with exploitation status

The platform continuously evaluates the estate against vulnerability data enriched with
exploitation status, and gates on configurable thresholds.

**Consequences (testable):**
- Findings distinguish known-exploited vulnerabilities from merely-published ones.
- Thresholds are configurable per Stage; a `production`-bound artifact with an exploited-vulnerability
  finding fails its gate.
- Time from vulnerability publication to a determination of affectedness is measured (SM-5).
- **Provenance/delta:** supersedes the intake spec's `pip-audit`-based scan — which covers neither
  pixi manifests nor exploitation status — with the existing Compliance Report capability
  (research § 5.1.3). See OQ-4 for the integration boundary.

#### FR-44: Schema-validated Compliance Report

The compliance gate emits one machine-readable report covering hygiene, security, licence, and
currency findings.

**Consequences (testable):**
- The report validates against a published schema.
- The gate's exit code reflects the report's verdict.
- The report is retained as evidence with a timestamp and the inputs it evaluated.

#### FR-45: Baselining and grandfathering

Existing findings can be baselined so that a gate can be adopted without a flag day, while new
findings still fail.

**Consequences (testable):**
- A baselined finding does not fail the gate; a new finding does.
- Baseline entries carry an owner and a revisit condition.
- The baseline shrinks over time and its size is reported.

#### FR-46: Licence policy enforcement

Component licences are evaluated against a declared policy.

**Consequences (testable):**
- A component under a disallowed licence fails the gate, naming the component and licence.
- The policy is declared in one place and is auditable.
- **Provenance:** Constitution Art. XII § 12.4 ("Review dependency licenses").

#### FR-47: Remediation proposals are automated and opt-in

The platform can propose dependency remediations as reviewable change proposals.

**Consequences (testable):**
- A remediation proposal is a reviewable PR, never an automatic merge.
- The proposal states which finding it addresses.
- Actuation is opt-in per Package.
- **Provenance/delta:** the intake spec's daily auto-patch workflow, retained in spirit and
  superseded in mechanism — it had no severity gate, no exploitation awareness, and no evidence
  trail.

---

### 5.7 Data Product Platform

**Description.** Domains own Data Products, layered Raw → Curated → Consumption, orchestrated as
Assets with declared contracts. This is the part of the intake Constitution that is most complete
and most faithful to its source architecture — Article VII implements Data Mesh principles 1 and
2 well (research § 3). The requirements here mostly ratify it. Realizes UJ-2.

**Functional Requirements**

#### FR-48: Domain-owned Data Products with enforced boundaries

Each Data Product belongs to exactly one Domain; cross-Domain consumption happens through
published interfaces, not direct datastore access.

**Consequences (testable):**
- Every Data Product resolves an owning Domain.
- A cross-Domain direct datastore access is detectable and fails review.
- **Provenance:** Constitution Art. VII § 7.1, § 7.4.

#### FR-49: Three-Layer refinement model

Every Data Product declares its Layer as `Raw`, `Curated`, or `Consumption`.

**Consequences (testable):**
- An Asset with no Layer, or an invalid Layer, fails the gate.
- **Provenance:** Constitution Art. VII § 7.2. Recorded as a deliberate Unity convention — the
  Data Mesh source text is silent on internal layer naming (research § 3.2).

#### FR-50: Enforced Asset naming convention

Asset names follow `<domain>_<layer>_<entity>_<verb>`.

**Consequences (testable):**
- A non-conforming name fails an automated check.
- The `<domain>` segment must match a declared Domain and `<layer>` a declared Layer.
- **Provenance:** Constitution Art. VII § 7.3.

#### FR-51: Asset metadata contract

Every Asset declares owner, domain, layer, and update frequency as structured metadata.

**Consequences (testable):**
- An Asset missing any required metadata field fails the gate.
- Metadata is queryable across the Workspace — the answer to "what does this Domain publish?"
  is generated, not maintained.
- **Provenance:** Constitution Art. V § 5.2, Art. IX § 9.1.

#### FR-52: Data Product contracts with compatibility policy

Each Data Product publishes a schema contract; breaking changes are versioned.

**Consequences (testable):**
- A schema change that breaks a declared consumer is detected before merge.
- Breaking changes require a version increment and a migration note.
- **Provenance:** Constitution Art. VII § 7.5.

#### FR-53: Asset test requirements

Every Asset has tests covering input validation, transformation logic, output schema, edge cases,
and upstream integration.

**Consequences (testable):**
- An Asset without tests for each required dimension fails the gate.
- **Provenance:** Constitution Art. III § 3.3.

#### FR-54: Reference Domain implementation

The Workspace ships one Domain implemented end to end as the pattern others follow.

**Consequences (testable):**
- The reference Domain exercises all three Layers, publishes a contract, and passes every gate.
- Its structure is what the scaffolding templates (FR-37) generate.
- `[ASSUMPTION]` v1 delivers **the pattern plus one worked Domain** (`customer`); the remaining
  ten are adoption work. This changes effort by an order of magnitude — see OQ-2.

---

### 5.8 Deployment, Environments, and Air-Gap

**Description.** Getting the platform to where it runs — including where the internet does not
reach. Realizes UJ-1 (edge case), UJ-4.

**Functional Requirements**

#### FR-55: Air-Gap Mode parity

Every capability available with public network access is available in Air-Gap Mode.

**Consequences (testable):**
- A parity test enumerates capabilities and asserts each works air-gapped.
- A capability that cannot work air-gapped is declared as such with its reason, not silently
  degraded.
- Validates SM-6.
- **Provenance:** Constitution Art. II § 2.2; the `enterprise-airgap` Dream's stated posture.

#### FR-56: Declarative, environment-promoted deployment

Deployment state is declared in version control and reconciled to the runtime, with promotion
between Stages governed by that Stage's policy.

**Consequences (testable):**
- Deploying is a change to declared state, not an imperative action.
- Stages with a manual-approval policy cannot auto-promote.
- Configuration differences between Stages are expressed as overlays over a shared base.
- **Provenance:** Constitution Art. X § 10.4–10.5.

#### FR-57: Secrets are never committed and are validated at startup

Secrets are supplied at runtime, absent from version control, and their presence is checked at
process start.

**Consequences (testable):**
- A secret-shaped string committed to the repository fails an automated check.
- A service missing a required secret fails fast with a diagnostic naming it, rather than at
  first use.
- **Provenance:** Constitution Art. VI § 6.5, Art. XII § 12.1.

#### FR-58: Data Classification is enforced, not merely documented

A Stage's Data Classification constrains what data may be present and what controls apply.

**Consequences (testable):**
- A Stage classified below `Restricted` cannot be configured against a datastore holding
  restricted data.
- Stages carrying restricted data have access logging enabled.
- `[ASSUMPTION]` v1 enforces classification at the **configuration boundary** (which datastore, which
  network) rather than performing data-content inspection. Content-level PII detection and masking
  is a candidate for v2 — see OQ-8.
- **Provenance:** Constitution Art. VI § 6.2, Art. XII § 12.6. `[NOTE FOR PM]` The Constitution
  asserts PII masking, retention, right-to-deletion and audit logging with **no mechanism
  specified anywhere**. This is the largest unbacked assertion in the intake set.

---

### 5.9 Developer Experience Surface

**Description.** The commands and services a developer touches daily. The intake root proves the
shape at scale — roughly 200 tasks covering the full local lifecycle — and simultaneously shows
its risk: a surface that large is unlearnable without a stable public subset. Realizes UJ-1.

**Feature-specific NFRs**
- The task surface must be discoverable: every task carries a description, and tasks are grouped.
- The **public** task subset (the commands a developer is expected to know) is explicitly named
  and kept small; everything else is an implementation detail reachable but not advertised.

**Functional Requirements**

*This feature's requirements are satisfied by FR-18 (Quality Gate), FR-24 (local CI), FR-37
(scaffolding), and the local-lifecycle capability below.*

#### FR-59: One-command local stack lifecycle

A developer starts, stops, and inspects the full local service stack with single commands, and
each service individually.

**Consequences (testable):**
- Start, stop, status, and restart exist at both aggregate and per-service granularity.
- Status reports actual health, not merely process existence.
- The aggregate start brings up services in dependency order.
- **Provenance:** the intake root's local-dev lifecycle task family (brief addendum § C.2).

#### FR-60: Stable public task API

The Workspace names a small set of tasks as its public developer API and keeps it stable.

**Consequences (testable):**
- The public set is documented and enumerable.
- Removing or renaming a public task is a breaking change requiring a decision record.
- **Provenance/delta:** the intake root marks four tasks as the "Agent & Developer Public API"
  (`start`, `stop`, `status`, `verify`) out of ~200 — an excellent instinct, made a requirement.

---

## 6. Cross-Cutting NFRs

- **NFR-1 — Reproducibility.** An Environment materialized from the Workspace Lock is identical
  across machines, platforms, and time, given the same lock. Verified by FR-11.
- **NFR-2 — Offline-first.** No capability may assume public network egress. Air-Gap Mode is the
  design default, not a mode. Verified by FR-55.
- **NFR-3 — Local/CI fidelity.** The Quality Gate is byte-identical locally and in CI. Verified
  by FR-18.
- **NFR-4 — Feedback latency.** Commit-time checks complete within a budget low enough that they
  are not routinely bypassed; the full gate completes within a budget low enough to run before
  every push. Verified by FR-23 and counter-measured by SM-C3. `[ASSUMPTION]` Both budgets must be
  set against a measured baseline rather than invented — see OQ-12. **Until OQ-12 resolves, this
  NFR has no numeric bound and cannot be tested.**
- **NFR-5 — Onboarding cost.** A new engineer reaches a working local stack using only written
  documentation, with no tribal knowledge. Verified by FR-13, FR-37, FR-59; measured by SM-1.
- **NFR-6 — Auditability.** Every gate decision, override, and exception is recorded with who,
  when, and why, and is enumerable after the fact. Verified by FR-8, FR-17, FR-27, FR-44, FR-45.
- **NFR-7 — Diagnosability.** Failures name the cause: the unmet requirement, the conflicting
  constraint, the violated clause. An opaque solver error is a defect. Verified by FR-1, FR-2,
  FR-19, FR-28, FR-46, FR-57.
- **NFR-8 — Platform coverage.** Every capability works on every declared platform, or declares
  its exception with a reason. Verified by FR-6, FR-11.
- **NFR-9 — Extensibility without forking.** A Domain adds Packages, Environments, and Data
  Products without modifying platform-owned files. Verified by FR-5, FR-27, FR-37; measured by
  SM-8.
- **NFR-10 — Supply-chain integrity.** Every dependency is hash-verified; every artifact carries
  SBOM and Provenance. Verified by FR-10, FR-39, FR-41, FR-42.

---

## 7. Compliance and Regulatory

- **CR-1 — EU Cyber Resilience Act.** Unity must be *able* to discharge CRA obligations for
  adopters within scope: continuous awareness of actively-exploited vulnerabilities in the estate
  (FR-43), retained evidence (FR-44), component inventory (FR-39–FR-41), and lifecycle
  vulnerability handling (FR-47). Dates: in force 2024-12-10; **reporting obligations
  2026-09-11**; main obligations 2027-12-11.
  `[NOTE FOR PM]` The fetched Commission page does **not** explicitly state an SBOM requirement.
  The inference that CRA Annex I's component-documentation duty is satisfied by SBOM is
  **widely held but unverified here** — confirm the Annex I wording before citing CRA as the
  authority for FR-39 (OQ-3).
- **CR-2 — GDPR and data privacy.** The Constitution asserts GDPR compliance, retention policy,
  PII masking outside production, access audit logging, and right-to-deletion. FR-57 and FR-58
  address the configuration boundary; **content-level obligations have no specified mechanism**
  in the intake set and are scoped out of v1 (OQ-8).
- **CR-3 — Licence compliance.** FR-46.
- **CR-4 — Supply-chain provenance.** FR-42, targeting SLSA Build L1 mandatory / L2 goal (OQ-7).
- **CR-5 — Standards conformance.** SBOM output conforms to a pinned specification version
  (FR-39); the Exported Lock conforms to PEP 751 `lock-version` 1.0 (FR-12).

---

## 8. Constraints and Guardrails

**Safety.** Automated remediation never merges without human review (FR-47). Automated
enforcement fails closed: an unevaluable gate is a failing gate, never a passing one.

**Privacy.** Restricted data never leaves a Stage classified for it (FR-58). Secrets never enter
version control, lockfiles, logs, or command lines (FR-15, FR-57).

**Cost.** Environment count is bounded by genuine dependency variation, not by Stage naming
(FR-9) — every distinct Environment is a solve, an install, and a cache entry, paid on every
machine and every CI run. Minimal Environments must be genuinely minimal (FR-3).

**Dependency policy.** All package installation goes through the workspace manager; direct
installer invocation is prohibited (Constitution Art. II § 2.1, § 2.3). Exceptions require a
recorded decision (FR-27).

**Language and runtime targets.** `[ASSUMPTION]` Primary Python targets are **3.13 and 3.14**;
3.12 is supported for legacy consumers only and is **security-phase** upstream (no further
binary releases); **3.15 first-releases 2026-10-01** and must be planned for inside this horizon.
This revises the Constitution's stated preference — see § 15 D7 and OQ-10.

**Platform matrix.** `[ASSUMPTION]` The matrix is at minimum `linux-64`, `osx-arm64`, `win-64`.
Whether `linux-aarch64` is in v1 is unresolved (OQ-14) — the two intake gists disagree with each
other, and the mandated deployment target is Kubernetes, where ARM nodes are mainstream.

---

## 9. Integration and Dependencies

| Dependency | Nature | Risk |
|---|---|---|
| **Compliance gate capability** (`pyforge-warden`) | Consumed, not rebuilt. Supplies FR-43–FR-47 | Integration boundary undecided (OQ-4) |
| **Conda-native package supply** (`conda-forge-expert`, 769 feedstocks) | The channel Unity resolves against; the escalation path when a component is missing | Coverage of the full mandated stack is spot-checked only (OQ-15) |
| **Dependency intelligence** (`pyforge-atlas`) | Feeds currency, staleness, and alternative-suggestion signals | Optional for v1 |
| **Air-gap routing doctrine** (`enterprise-airgap`) | The mirror/credential model behind FR-14–FR-16 | Carries a known credential-injection defect that FR-16 must close |
| **Bootstrapper** (`pyforge-genesis`) | Would instantiate Unity instances | Unbuilt — a v2 dependency, not v1 |
| **Workspace manager** (pixi) | The substrate itself | Multi-package workspace support is **preview** (OQ-9b); version moves fast |
| **Standards-format export** (PEP 751) | FR-12 | Consumer-side reader support is **experimental** (§ 15 D2) |
| **Orchestrator** (Dagster) | The Asset execution engine | Constitution mandates it as sole platform |
| **Container platform** (OpenShift/Kubernetes + GitOps) | Deployment target | Current version/lifecycle unverified (OQ-17) |
| **Governance toolkit** (spec-kit) | The Constitution's format | Boundary with BMAD planning undecided (OQ-18) |

---

## 10. Non-Goals (Explicit)

- **Unity is not an Internal Developer Portal.** No service catalog UI, no discovery portal.
  Unity emits catalog-consumable facts derived from its manifests; an adopter running Backstage
  integrates rather than migrates.
- **Unity is not a build-graph engine.** No attempt to compete with Pants, Bazel, or Nx on
  fine-grained caching, affected-target computation, or remote execution. Orthogonal, and
  unwinnable.
- **Unity does not maintain a second registry of truth.** The manifests are the source; anything
  else is derived.
- **Unity is not a product to be sold.** It is a platform an enterprise runs.
- **Unity does not replace the Domains' judgement about their own data models.** Global
  interoperability concerns are Platform Invariants; local modelling is a Domain Default (FR-26).
- **Unity does not target SLSA Build L3 in v1.**
- **Unity does not perform data-content inspection in v1** (classification is enforced at the
  configuration boundary — FR-58).
- **Unity is not a general-purpose polyglot monorepo.** Python-first by mandate.

---

## 11. MVP Scope

### 11.1 In Scope

- Workspace substrate with corrected pinning, Environment composition, and Package manifests
  (FR-1–FR-9).
- Resolved lock architecture with verified multi-platform coverage, standards export, offline
  bundle, and safe credential handling (FR-10–FR-17).
- Quality Gate with CI parity (FR-18–FR-25).
- Constitution classified into Platform Invariants and Domain Defaults, machine-checkable, with
  a governed amendment process (FR-26–FR-32).
- Innersource contribution model: Trusted Committer role, contribution path, scaffolding,
  measurement (FR-33–FR-38).
- Compliance chain: versioned SBOM with dependency graph, provenance, continuous
  exploitation-aware gating, schema-validated report, baselining, licence policy, opt-in
  remediation (FR-39–FR-47) — **by integration**.
- Data Product platform requirements plus **one** reference Domain end to end (FR-48–FR-54).
- Air-gap parity, declarative deployment, secret handling, configuration-boundary classification
  enforcement (FR-55–FR-58).
- Developer surface: local stack lifecycle and a stable public task API (FR-59–FR-60).

### 11.2 Out of Scope for MVP

- **The remaining ten Domains.** `[ASSUMPTION]` v1 ships the pattern plus one worked Domain; the
  intake root marks all eleven as "scaffolding only" with one reference implementation
  (OQ-2). `[NOTE FOR PM]` This is the largest single sizing lever in the document.
- **Content-level PII detection, masking, and right-to-deletion** — asserted by the Constitution
  with no mechanism; deferred to v2 (OQ-8).
- **SLSA Build L3** — requires hardened builders.
- **Local Kubernetes development** — the required cluster tool is not available through the
  mandated channel, and the deployment target is not available on all platforms. Keep the intake
  root's documented stub and its reasoning.
- **Excluded services** (`airflow-server`, `sharepoint-mcp-server`) — carried as documented
  exclusions with reasons (FR-8).
- **Bootstrapping new Unity instances** — depends on `pyforge-genesis`, unbuilt.
- **A catalog/portal UI** — see § 10.
- **Remote build caching / distributed execution** — see § 10.

---

## 12. Success Metrics

**Primary**

- **SM-1 — Time to productive.** Elapsed time from clone to a running local stack with a passing
  package test, by a new engineer using only written documentation. `[ASSUMPTION]` Target: under
  one hour, single-digit commands. Validates FR-1, FR-13, FR-59, NFR-5. Measured by timed
  onboarding of each new joiner.
- **SM-2 — Cross-team contribution rate.** Count of merged PRs authored by someone outside the
  owning team, per Package, per quarter — **trending up**. Validates FR-33–FR-38. *This is the
  innersource proof; if it stays near zero the platform has failed at its premise regardless of
  technical quality.*
- **SM-3 — Local/CI fidelity.** Rate of green-locally / red-in-CI outcomes — **trending to zero**.
  Validates FR-18, NFR-3.
- **SM-4 — Reproducibility coverage.** Percentage of declared platforms for which every
  Environment is verified materializable from the lock, online and offline. Target: 100%.
  Validates FR-11, FR-13, FR-55.
- **SM-5 — Compliance latency.** Elapsed time from vulnerability publication to a determination
  of whether the estate is affected. `[ASSUMPTION]` Target: minutes, automated. Validates FR-43,
  FR-44. *Directly serves the CRA reporting obligation.*

**Secondary**

- **SM-6 — Air-gap parity.** Percentage of enumerated capabilities verified working in Air-Gap
  Mode. Target: 100%, with any exception declared. Validates FR-55, NFR-2.
- **SM-7 — Mandate enforcement coverage.** Percentage of Mandates with an automated enforcing
  check. Validates FR-29. *Trending up; not expected to reach 100% — some Mandates are
  irreducibly human.*
- **SM-8 — Reuse depth.** Count of distinct Domains consuming each shared Package. Validates the
  premise that sharing is worth its cost.
- **SM-9 — Compliance baseline burn-down.** Size of the grandfathered finding baseline over time
  — **trending down**. Validates FR-45.

**Counter-metrics (do not optimize)**

- **SM-C1 — Internal fork/duplicate count.** Number of near-duplicate internal libraries.
  Counterbalances SM-2: contribution rate can be gamed by trivial PRs while people still fork
  rather than contribute. **If SM-2 rises and SM-C1 does not fall, SM-2 is not measuring what it
  claims to.**
- **SM-C2 — Environment count and aggregate installed size.** Counterbalances FR-9 and FR-3:
  the platform can always be made more capable by adding Environments and dependencies, and each
  is paid on every machine and every CI run.
- **SM-C3 — Quality Gate wall-clock time.** Counterbalances SM-3 and SM-7: fidelity and coverage
  both improve by adding checks, and a gate slow enough to be bypassed enforces nothing.
- **SM-C4 — Override count.** Counterbalances FR-26/FR-27: a governance split that produces
  hundreds of Domain Default overrides has classified the wrong things as defaults — but zero
  overrides means the split is theatre and Unity is centrally imposed after all. **Neither
  extreme is healthy.**

---

## 13. Risk and Mitigations

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R-1 | **The lock mechanism is unproven.** The intake set's multi-platform guarantee rests on a non-existent flag and a misread of the format's scope | **High** | Resolve OQ-1 and OQ-16 before any other architecture work; FR-11 makes coverage a verified gate rather than an assumption |
| R-2 | **Two lockfiles, two solvers can silently disagree** — the seam where "reproducible" stops being true | **High** | FR-12's drift check; a single authoritative lock with the other derived |
| R-3 | **Mandated stack breadth.** Orchestrator + data-science toolbox + dbt + two web frameworks + CMS + ten infra services is a very large compatibility surface | **High** | FR-7's compatibility-detection Environment; FR-8's documented exclusions; scope discipline in § 11.2 |
| R-4 | **Experimental and preview dependencies in the critical path** — standards-format reader support is experimental; multi-package workspace support is preview | Medium | Pin versions; document a fallback for each; avoid preview features on the critical path where an alternative exists (OQ-9b) |
| R-5 | **Governance double-stack.** Two governance systems (spec-kit constitution, BMAD planning chain) are both live | Medium | Resolve OQ-18 explicitly rather than letting both drift |
| R-6 | **The social layer does not materialize.** Trusted Committers named but unresponsive; contribution path documented but unused | **High** | SM-2 with SM-C1 as counter-metric; FR-33's documented response-window expectation; escalation path in FR-34 |
| R-7 | **Constitution ossifies.** Already five months past its own review date | Medium | FR-30's overdue-review warning; FR-29's enforcement-coverage report as a forcing function |
| R-8 | **Stack currency drift resumes** — the intake set decayed in roughly six months | Medium | FR-17's recorded update policy; FR-7 running on schedule; treat currency as a gate axis |
| R-9 | **The platform is adopted technically and rejected socially** — teams use it because they must and route around it where they can | **High** | SM-2, SM-8, SM-C4; FR-26's Domain Defaults exist precisely so autonomy is real rather than rhetorical |
| R-10 | **Credential leakage.** A known unconditional-injection defect exists in inherited routing code | Medium | FR-15, FR-16, with tests asserting non-attachment |

---

## 14. Constitution Provenance Map

Every Constitution mandate traced to the requirement that carries it, or to its disposition.
Source: `docs/intake/gists/spec-kit/constitution.md` v1.2.0 (ratified 2025-11-20).

### 14.1 The Article II mandate table (rows sourced from several Articles)

| Mandate | Priority (as stated) | Carried by | Disposition |
|---|---|---|---|
| Local First — per-package environments, testing, docs | CRITICAL | FR-3, FR-5, FR-18, FR-59 | Adopted |
| Package Management — pixi, conda-forge, air-gap | CRITICAL | FR-1, FR-10, FR-14, § 8 | Adopted |
| Production — OpenShift + GitOps | CRITICAL | FR-56 | Adopted; version unverified (OQ-17) |
| MCP — agent message transport | CRITICAL | § 9 | Adopted. **Terminology corrected**: the Constitution expands MCP as "Multi-Agent Communication Protocol"; the correct expansion is **Model Context Protocol** |
| A2A — agent collaboration semantics | CRITICAL | § 9 | Adopted as an integration dependency; no v1 FR |
| REST — API architecture | CRITICAL | — | `[ASSUMPTION]` Applies to Packages Unity hosts, not to Unity's own surface. Not an FR |
| Environments — 12-stage SDLC | CRITICAL | FR-9, FR-58 | Adopted **as Stages**, modelled separately from Environments |
| Orchestration — Dagster ≥1.12.0, sole platform | HIGH | § 9, FR-48–FR-53 | Adopted; floor to be re-set (1.13.x current) |
| Data Mesh — DDD, three layers | HIGH | FR-48–FR-52 | Adopted |
| Data Science — Kedro, sole toolbox | HIGH | § 9 | Adopted as dependency; no v1 FR |
| Web Application — Django + React, preferred | HIGH | § 9 | Adopted as dependency; "preferred" ⇒ **Domain Default**, not Platform Invariant |
| RESTful API — FastAPI, preferred | MEDIUM | § 9 | Same |

### 14.2 Articles I–XIV

| Article | Subject | Carried by |
|---|---|---|
| I | Identity, stack, repository structure | § 1, § 9, FR-1, FR-5 |
| II | Pixi-first package management | FR-1, FR-10, FR-14, FR-27, § 8 |
| III | Spec validation (tests) | FR-20, FR-21, FR-53; **amend** for FR-25 |
| IV | Agentic quality enforcement | FR-18, FR-19, FR-22, FR-23 |
| V | Specification standards | FR-31, FR-32, FR-51 |
| VI | 12-stage SDLC | FR-9, FR-57, FR-58 |
| VII | Data mesh | FR-48–FR-52 |
| VIII | Spec-driven collaboration | FR-33–FR-36 |
| IX | Dagster best practices | FR-50, FR-51, FR-53 |
| X | Continuous spec enforcement | FR-18, FR-24, FR-32, FR-56 |
| XI | Performance and scalability | **Not carried in v1** — no FR. `[NOTE FOR PM]` Article XI is entirely good-practice guidance with no platform mechanism. Candidate for demotion to a guide rather than a Mandate |
| XII | Security and compliance | FR-15, FR-16, FR-22, FR-39–FR-47, FR-57, FR-58 |
| XIII | Simplicity gate | FR-27, FR-31; § 8 |
| XIV | Python version support | § 8, § 15 D7 — **revised** |
| Governance | Authority, amendment, enforcement | FR-26, FR-28, FR-29, FR-30 |

### 14.3 Amendments this PRD requires to the Constitution

1. **Art. II mandate table** — classify every row as Platform Invariant or Domain Default
   (FR-26). "Preferred" rows are Domain Defaults by their own wording; "sole" rows are Invariants.
2. **Art. III** — add the behavioural test tier that the working root already implements (FR-25).
3. **Art. XIV** — revise the support policy: 3.12 is security-phase upstream; 3.15 arrives
   2026-10-01; the stated 2-year rule, applied literally, already expires the declared baseline
   (§ 15 D7).
4. **Art. XI** — demote to guidance, or supply mechanisms and requirements.
5. **Art. XII § 12.6** — either supply mechanisms for PII masking / retention / right-to-deletion
   or scope them explicitly (OQ-8).
6. **Art. II MCP row** — correct the protocol expansion.
7. **Art. VIII § 8.3** — name whose approval (FR-33).
8. **Governance § Next Review** — overdue since 2026-02-20; re-ratify with this PRD's amendments.

---

## 15. Research Deltas

Verified corrections to the intake artifacts. Full evidence and citations in the research
reports; graded **CONFIRMED** / **STALE** / **WRONG** / **NEW**.

| ID | Intake claim | Grade | Verified reality | Carried by |
|---|---|---|---|---|
| **D1** | "Universal Cryptographic Lockfile … tracks multi-platform targets" as a format guarantee | **WRONG (scope)** | PEP 751 is **Final** (2025-03-31) but explicitly does **not** provide universal multi-platform lockfiles automatically — it uses environment markers | FR-11 |
| **D2** | "pip v26.1+ (Deploy Engine)" reads `pylock.toml` | **STALE→NEW** | Correct — pip 25.1 added experimental `pip lock`; **26.1 added experimental `-r pylock.toml`**; latest 26.1.2 (2026-05-31). **Both experimental** | R-4; § 9 |
| **D3** | `pdm export --format pylock --override-platform=linux --override-platform=macos --override-platform=windows` | **WRONG** | **No `--override-platform` flag on `pdm export`**; platform targeting is on `pdm lock --platform`; format token is `pylock.toml`. Alternative: `uv export --format pylock.toml` | FR-12, OQ-16 |
| **D4** | `requires-pixi = "==0.59.0"` | **STALE** | Current is **0.73.0** (2026-07-15), 7 conda-forge subdirs. 0.73.0 adds `workspace = true` (removes the duplication smell), TOML 1.1, rich platforms (glibc/CUDA) | FR-2, FR-4 |
| **D5** | Workspace members as editable path installs | **NEW alternative** | Native multi-package workspaces now exist (`{ path = … }` + `{ workspace = true }`), **preview status** | OQ-9b, R-4 |
| **D6** | "dagster … doesn't support 3.14 yet" ⇒ `python <3.14` ceiling | **STALE** | dagster **1.13.15** declares `requires_python = "<3.15,>=3.10"` — 3.14 is supported. Ceiling's stated cause has expired | § 8, OQ-19 |
| **D7** | Python 3.14 preferred / 3.12 "legacy baseline" / 3.13 supported | **STALE** | **3.12 is security-phase** (no further binaries); 3.13 and 3.14 bugfix; **3.15 first-releases 2026-10-01**. The Constitution's own 2-year rule already expires 3.12 | § 8, § 14.3 |
| **D8** | Platform matrix (the two gists **disagree**: 4 platforms vs 3) | **STALE** | conda-forge ships the workspace manager for 7 subdirs incl. `linux-aarch64` and `win-arm64`; the mandated deployment target is Kubernetes, where ARM is mainstream | OQ-14 |
| **D9** | `pip-audit` + daily auto-patch as the security/compliance mechanism | **SUPERSEDED** | An existing capability is a strict superset: pixi-manifest coverage, **CISA-KEV** exploited-vulnerability gating, EPSS, licence and currency axes, schema-validated report, CI exit-code gate, opt-in fix-PR actuator | FR-43–FR-47, OQ-4 |
| **D10** | Unversioned CycloneDX output | **STALE** | CycloneDX **1.7** (2025-10-21) is **ECMA-424** (2025-12-10); adds formulation, declarations (compliance-as-code), citations; VEX/VDR and ML-BOM available | FR-39 |
| **D11** | SBOM from the lockfile is sufficient evidence | **GAP** | The generator's requirements mode carries a documented "no transitive components will be identified" caveat — risk is a **flat component list with no dependency graph** | FR-41, OQ-6 |
| **D12** | *(no provenance claim made)* | **GAP** | Provenance is entirely absent. SLSA **v1.2** current (v1.1 retired); L1 = provenance exists, L2 = signed provenance from a hosted build platform — **L2 is cheap on the CI already in use** | FR-42, OQ-7 |
| **D13** | Token Isolation Rule | **SELF-VIOLATED** | The spec's own manifest puts credentials in `extra-index-urls`; its CI interpolates them into `--index-url` on a command line | FR-15, FR-16 |
| **D14** | Constitution Art. VII implements Data Mesh | **CONFIRMED (2 of 4)** | Principles 1 (domain ownership) and 2 (data as a product) are faithfully implemented. Principle 3 (self-serve platform) is implicit — it is what Unity *is*. **Principle 4 (federated computational governance) is in tension**: the computational half is done well, the federated half is absent | FR-26, FR-27, OQ-5 |
| **D15** | Constitution is spec-kit format | **CONFIRMED + drift** | Format validated by adoption (**123.7k stars**, ~3.6× Backstage's 33.9k). But commands are now namespaced (`/speckit.constitution`), and upstream now ships **bundles** (role-based setups) that may subsume the toolchain spec's role matrix | OQ-18, OQ-20 |
| **D16** | Toolchain spec's 5-role agent matrix | **CONFIRMED + incomplete** | All five roles map onto the independently-evolved 8-station crew; two map excellently. The three unmapped stations are all **feedback-loop** roles (communication, diagnostics, memory) — the same under-specification of the human layer as the missing Trusted Committer | FR-33, § 9 |
| **D17** | Production container on `python:3.11-slim` | **CONTRADICTION** | The Constitution mandates Python 3.12–3.14; the spec's Dockerfile hardcodes 3.11 and `--python-version 311`, and switches away from conda for the production stage | § 8, OQ-1 |

**Confirmed and kept unchanged:** PEP 751 is Final; the feature/environment composition model;
the environment-variable mirror-override design; conda-native resolution as the differentiator;
the runtime/full SBOM split; the compatibility-detection environment; the documented
platform-conditional dependency knowledge; the `act`-based local CI mechanism; the four-task
public API instinct.

---

## 16. Open Questions

Ordered by decision urgency. IDs are PRD-local; the research-report IDs they consolidate are
noted for traceability.

| # | Question | Blocks | Owner |
|---|---|---|---|
| **OQ-1** | **Is the Workspace Lock authoritative with the standards format derived, or the reverse, or split by tier?** The two intake gists answer differently and neither notices the conflict *(OQ-D8)* | **Everything.** Resolve first | Architecture |
| **OQ-2** | How many Domains are in v1 — the pattern plus one, or all eleven? *(OQ-D10)* | MVP sizing; **order-of-magnitude** | PRD sign-off |
| **OQ-3** | Exact CRA Annex I component-documentation wording — is SBOM required or inferred? *(OQ-D3)* | Whether CR-1 may cite CRA as FR-39's authority | Legal/compliance |
| **OQ-4** | Compliance-gate integration boundary — library, CLI, CI action, or tool-server? *(OQ-D4)* | FR-43–FR-47 | Architecture |
| **OQ-5** | Which Mandates are Platform Invariants and which are Domain Defaults? *(OQ-D7)* | FR-26, FR-27; the innersource-vs-imposed question | PRD sign-off |
| **OQ-6** | Does SBOM generation from the lock emit a dependency **graph** or a flat list? *(OQ-D5)* | FR-41. **Cheap empirical test — do early** | Architecture |
| **OQ-7** | Target SLSA level for v1? Recommendation: L1 mandatory, L2 goal *(OQ-D6)* | FR-42 | PRD sign-off |
| **OQ-8** | Does Data Classification require content-level enforcement (PII detection, masking, deletion), or is configuration-boundary enforcement sufficient for v1? *(OQ-D9)* | FR-58; CR-2; Constitution Art. XII § 12.6 | PRD sign-off |
| **OQ-9** | Should Stages be modelled as separate Environments at all, given five are byte-identical and three more are identical? *(OQ-M11)* | FR-9 | Architecture |
| **OQ-9b** | Adopt preview multi-package workspace support, or stay on editable path installs? *(OQ-M8)* | FR-5; R-4 | Architecture |
| **OQ-10** | Confirm the Python support policy revision (primary 3.13/3.14; 3.12 legacy-only; plan for 3.15) | § 8; Constitution Art. XIV amendment | PRD sign-off |
| **OQ-11** | Confirm the branching model — the Constitution mandates Gitflow with `develop` default | FR-35 | PRD sign-off |
| **OQ-12** | What are the actual latency budgets for commit-time checks and the full gate? | NFR-4; SM-C3 | Measure, then set |
| **OQ-13** | Is tests-before-implementation enforceable automatically, or review-only? | FR-21 | Architecture |
| **OQ-14** | Is `linux-aarch64` in v1's platform matrix? The gists disagree *(OQ-M10)* | § 8; FR-11 | PRD sign-off |
| **OQ-15** | Does **every** mandated component exist on the mandated channel, on every target platform? *(OQ-M2)* | R-3; FR-6 | Verify — bulk query |
| **OQ-16** | Which mechanism produces the verified multi-platform Exported Lock? *(OQ-M7)* | FR-11, FR-12 | Architecture |
| **OQ-17** | Current OpenShift version, Kubernetes baseline, EUS lifecycle? *(OQ-D1 — source returned 403)* | FR-56 | Verify before pinning |
| **OQ-18** | Where is the boundary between spec-kit governance and BMAD planning? Both are live *(OQ-M4)* | § 14; R-5 | PRD sign-off |
| **OQ-19** | Is the mandated orchestrator built for Python 3.14 on the mandated channel? *(OQ-M9)* | § 8's ceiling | Verify before pinning |
| **OQ-20** | Express the agent role matrix as an upstream governance-toolkit bundle? *(OQ-M3)* | § 9 | Architecture |
| **OQ-21** | Does the vulnerability scanner cover the Workspace Lock and the Exported Lock formats? *(OQ-D2)* | FR-43 | Verify at integration |
| **OQ-22** | Is the comparable set complete? Discovery search was unavailable during research *(OQ-M1)* | § 10's non-goals — every "Unity is not X" statement assumes X is correctly identified | Re-run when budget allows |
| **OQ-23** | Is there independent innersource adoption data to ground SM-2's target? *(OQ-M6)* | SM-2 | Research follow-up |

---

## 17. Assumptions Index

Every `[ASSUMPTION]` in **this document**. **None is confirmed scope.**

`addendum.md` carries its own `[ASSUMPTION]` tags (in § A.3, § B.2, § C, § E, § F, § G) covering
mechanism preferences rather than scope. They are deliberately not indexed here — this index is
the complete list of *scope* assumptions; the addendum's are *implementation-option leanings* that
the architecture stage resolves.

| # | Section | Assumption | Resolve via |
|---|---|---|---|
| A-1 | § 0 | Produced headless with no user present; all inferences tagged | User review |
| A-2 | § 2 | CRA is a forcing-function and a capability to be able to discharge — not a claim that every deployment is regulated | OQ-3, OQ-16 |
| A-3 | § 5.2 / FR-12 | The Workspace Lock is authoritative; the standards-format lock is derived (pixi-primary) | **OQ-1** |
| A-4 | § 5.6 / FR-42 | SLSA L1 mandatory, L2 goal, L3 out of scope for v1 | OQ-7 |
| A-5 | § 5.7 / FR-54, § 11.2 | v1 delivers the Domain pattern plus one worked Domain, not all eleven | **OQ-2** |
| A-6 | § 5.8 / FR-58 | Data Classification is enforced at the configuration boundary; content inspection is v2 | OQ-8 |
| A-7 | § 5.3 / FR-21 | Tests-before-implementation is review-enforced, not automated | OQ-13 |
| A-8 | § 6 / NFR-4 | Latency budgets exist but specific numbers must be set against a measured baseline | OQ-12 |
| A-9 | § 8 | Primary Python targets are 3.13 and 3.14; 3.12 legacy-only; plan for 3.15 | OQ-10 |
| A-10 | § 8 | Platform matrix is at minimum linux-64, osx-arm64, win-64; ARM64 Linux unresolved | OQ-14 |
| A-11 | § 12 / SM-1 | Target: under one hour, single-digit commands | User review |
| A-12 | § 12 / SM-5 | Target: minutes, automated | User review |
| A-13 | § 14.1 | The REST mandate applies to Packages Unity hosts, not to Unity's own surface | User review |
| A-14 | § 3.2 | The listed non-user groups are correct audience boundaries | User review |

---

**Companion artifacts:** `addendum.md` (mechanism, options-considered, deferred depth) ·
`../../briefs/brief-unity-data-stack-2026-07-25/{brief.md,addendum.md}` ·
`../../research/{market,domain}-…-2026-07-25.md`
