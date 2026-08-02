---
id: SPEC-unity-data-stack
owner-dream: docs/dreams/unity-data-stack.md  # dream archived 2026-08-02 (absorbed, narrative only); consolidated narrative home: docs/dreams/pyforge-atlas.md § The estate Atlas hosts. This SPEC's contract is unchanged and stays the chain's owner-dream link (dream_chain_check INV-1).
surface:
  # NOTE (2026-07-25): globs that would claim THIS repo's shared root files
  # (pixi.toml/pixi.lock/src/**/tests/**/helm/**) were removed — this project's
  # code does not live here, and claiming them silently transferred governance of
  # real pyforge files to an unbuilt project. Re-declare on first landing.
  - constitution.md              # Mandates + machine-readable classification (AD-8)
  - config/**                    # Stages, air-gap, feature-flags, gitops overlays
  - templates/**                 # scaffolding (FR-37)
companions:
  - constitution-provenance.md
  - ../../architecture/architecture-unity-data-stack-2026-07-25/ARCHITECTURE-SPINE.md
sources:
  - ../../../../../../docs/dreams/unity-data-stack.md
  - ../../briefs/brief-unity-data-stack-2026-07-25/brief.md
  - ../../briefs/brief-unity-data-stack-2026-07-25/addendum.md
  - ../../prds/prd-unity-data-stack-2026-07-25/prd.md
  - ../../prds/prd-unity-data-stack-2026-07-25/addendum.md
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits. This project's planning ran to **PRD + architecture depth only** — epics/stories are deliberately not produced; they decompose fresh when this Dream is scheduled.

# Unity Data Stack — the enterprise innersource python-first platform

## Why

A vision to realize, given legs by a mandate with a live clock. Every team building Python data products inside a large enterprise independently re-solves the same six problems — native+Python dependency resolution, offline reproducibility, supply-chain compliance, OpenShift deployment, cross-platform testing, and letting another team contribute without breaking anything — and the organization pays for the difference forever, in onboarding time, audit effort, duplicated internal libraries, and the quiet conclusion that cross-team sharing isn't worth the trouble. Unity Data Stack is the **Inner-Source Model** made concrete: one opinionated, conda-native, air-gap-first, spec-governed monorepo where teams co-contribute reusable templates, libraries, services, and Data Products on a single toolchain, with standards chosen once and machine-enforced rather than written on a wiki page. Three substantial artifacts already existed (a 37 KB spec-kit Constitution, a 1,726-line working pixi root, a toolchain spec) but were never landed in a repository and had measurably drifted — this Spec's job is to absorb what research confirms, correct what it falsifies, and supply what was missing, principally the human contribution model and the provenance chain. The mandate has real urgency: EU Cyber Resilience Act vulnerability-reporting obligations begin **2026-09-11**, with main obligations **2027-12-11** — "know what you ship, continuously" is now a dated legal duty, not aspirational good practice.

## Capabilities

- **CAP-1**
  - **intent:** A platform engineer declares one Workspace root — platform matrix, channels, system-requirement floors, and the set of Packages — from which Environments compose from named Features with no inherited bloat, and every Package carries a declared owner.
  - **success:** FR-1–9 hold: adding a Package requires editing exactly one place; no dependency version string is duplicated; a minimal Environment's installed size is measured against a documented ceiling and a regression fails the gate; Stages are modelled separately from Environments so the number of distinct solves is bounded by genuine dependency variation, not Stage naming (AD-4).
- **CAP-2**
  - **intent:** The Workspace produces one authoritative Workspace Lock covering native and Python packages together, reproducing an Environment offline on every declared platform, with a derived standards-format export and an air-gapped Offline Bundle, and credentials that are host-scoped and never appear in a URL or argument.
  - **success:** FR-10–17 hold: multi-platform coverage is proven by materialization, never assumed (FR-11); the Exported Lock is generated from, and drift-checked against, one pinned Workspace Lock commit SHA, failing the gate on mismatch (FR-12, resolves PRD OQ-1 via AD-2).
- **CAP-3**
  - **intent:** A developer runs one command that executes every check CI executes — lint, format, type checking, coverage thresholds, security scanning, and a tagged behavioural-test tier — with pre-commit mirroring a fast subset.
  - **success:** FR-18–25 hold: a parity check asserts the local and CI check-sets are identical and fails on divergence (AD-9); coverage that decreases relative to the base branch fails the gate.
- **CAP-4**
  - **intent:** Every Constitution Mandate is classified, machine-readably, as a Platform Invariant (no override) or a Domain Default (Domain-overridable with a recorded decision); violations name the clause they violate; amendment is a governed, versioned process.
  - **success:** FR-26–32 hold: an unclassified Mandate, or an override with no linked decision record, fails the Quality Gate (AD-8); the Constitution carries semver, ratified/amended/next-review dates; a coverage report distinguishes automatically-enforced Mandates from human-review-only ones.
- **CAP-5**
  - **intent:** Every Package names a Trusted Committer accountable for reviewing outside contributions, an outside contributor finds a documented path to contribute to code they don't own, and branch/commit/merge conventions are enforced automatically.
  - **success:** FR-33–38 hold: a Package with no Trusted Committer fails the gate; a scaffolded Package or Data Product passes the Quality Gate immediately with no manual fixes (FR-37); cross-team contribution rate and an internal-fork counter-signal are both measured (FR-38).
- **CAP-6**
  - **intent:** Every built artifact carries a versioned SBOM with a populated dependency graph (runtime-scoped and full variants) and a build-provenance attestation, continuously gated against exploitation-aware vulnerability data through one schema-validated Compliance Report, with baselining/grandfathering and opt-in remediation proposals.
  - **success:** FR-39–47 hold, delivered by **integrating** `pyforge-warden` (already a strict superset of the intake approach) rather than reimplementing it; SBOM generation runs against the built artifact and a test asserts a populated transitive dependency edge (AD-11); an artifact with no provenance attestation cannot be promoted to any Stage whose policy requires approval (AD-12).
- **CAP-7**
  - **intent:** Each Domain owns Data Products layered Raw → Curated → Consumption, with an enforced naming convention, a structured metadata contract, and versioned schema contracts; one reference Domain (`customer`) is implemented end to end as the pattern others follow.
  - **success:** FR-48–54 hold: a schema change that breaks a declared consumer is detected before merge, requiring a version increment and migration note (FR-52, AD-16); the reference Domain exercises all three Layers, publishes a contract, and passes every gate — its structure is exactly what the FR-37 scaffolding templates generate.
- **CAP-8**
  - **intent:** Every capability available with public network access is available in Air-Gap Mode (or declares why not); deployment is declarative and environment-promoted under Stage policy; secrets are never committed and are validated present at service startup; a Stage's Data Classification bounds which datastores and network posture it may be configured against.
  - **success:** FR-55–58 hold: a parity test enumerates capabilities and asserts each works air-gapped, targeting 100% with declared exceptions (SM-6); a secret-shaped string committed to the repository fails an automated check (FR-57).
- **CAP-9**
  - **intent:** A developer starts, stops, and inspects the full local service stack — aggregate and per-service — with single commands, and the Workspace names a small, stable public task API.
  - **success:** FR-59–60 hold: status reports actual service health, not process existence; removing or renaming a public task is a breaking change requiring a decision record.

## Constraints

- **One authoritative lock (AD-2):** exactly one Workspace Lock (conda+PyPI together) is authoritative and committed; every other lock artifact (Exported Lock, Offline Bundle) is generated from it and drift-checked against one pinned commit SHA per release — never hand-edited, never a second resolution input.
- **Materialized coverage, never inferred (AD-3):** for every declared platform × every deployable Environment, a gate materializes the Environment from the lock and fails if it cannot; coverage is reported per platform, never as a single boolean.
- **One-way dependency direction (AD-7):** dependencies flow shared → platform-infrastructure → domain, never upward or sideways between Domains; a Domain consumes another Domain's *published* Data Product/API only, never its Package or datastore directly; a cycle detector runs in the Quality Gate.
- **Every Mandate machine-classified (AD-8):** each Constitution Mandate carries a stable identifier and a classification of exactly `platform-invariant` or `domain-default`; an unclassified Mandate, or a check with no declared Mandate, fails the Quality Gate.
- **Tasks, not inline commands (AD-9):** every gate check is a named task with a globally unique name; CI invokes task names only — no inline tool invocation, no inline installation, no environment mutation; a parity check and a name-uniqueness check both run in the gate.
- **Host-scoped credentials (AD-10):** credentials live only in the credential store or masked runner inputs; no committed file contains a credential-bearing URL in any form; no process receives a credential as a command-line argument; a request attaches a credential only when its host matches.
- **Lean-by-declaration Environments (AD-13):** every deployable Environment inherits no default dependency set and composes only what it names; installed size is measured against a recorded ceiling and a regression fails the gate (exempt: the FR-7 compatibility-detection Environment, explicitly non-deployable).
- **One accountable station per plane (AD-17):** each plane and cross-cutting concern resolves to exactly one pyforge-crew station (Marshal / Atlas / Warden / Mason / Steward / Doctor / Scribe / Herald); an unowned capability, or one claimed by two stations, is a defect — full map in the architecture-spine companion.
- **The Constitution's 14 Articles are the requirement spine.** Every FR traces to an Article or to its explicit disposition; 8 amendments are required before re-ratification. Full Article map and the 8 amendments are in `constitution-provenance.md` — not restated here.
- **The intake toolchain spec's flagship lock command does not exist:** `pdm export --format pylock --override-platform=...` has no such flag on `pdm export` (verified 2026-07-25); that exact mechanism cannot be reused as written, and PEP 751 itself does not guarantee multi-platform coverage — this is the empirical grounding for AD-2/AD-3 replacing an unverified format guarantee with gate-verified materialization. Detail in `constitution-provenance.md`.
- **Compliance by integration, not reimplementation (AD-6):** the compliance capability is `pyforge-warden`, consumed as a CLI in its own lean, isolated Environment — never imported as a library, never invoked only in CI; the gate's exit code derives from its Compliance Report file.
- **Python targets revised (Constitution Art. XIV amendment):** primary targets are 3.13 and 3.14; 3.12 is legacy-consumer-only (security-phase upstream); 3.15 first-releases 2026-10-01 and must be planned for inside this horizon.

## Non-goals

- Unity is not an Internal Developer Portal — no catalog UI, no service-discovery portal; it emits catalog-consumable facts, an adopter running Backstage integrates rather than migrates.
- Unity is not a build-graph engine — no attempt to out-cache Pants, Bazel, or Nx on fine-grained caching or remote execution; orthogonal and unwinnable.
- Unity does not maintain a second registry of truth — manifests are the source; catalogs, ownership maps, and portal feeds are all derived.
- Unity is not a product to be sold — it is a platform an enterprise runs.
- Unity does not replace a Domain's judgement about its own data models — global interoperability concerns are Platform Invariants, local modelling is a Domain Default.
- Unity does not target SLSA Build L3 in v1 — L1 mandatory, L2 goal; L3 needs hardened builders, deferred.
- Unity does not perform data-content inspection in v1 — Data Classification is enforced at the configuration boundary only (which datastore, which network), not content-level PII detection/masking/deletion.
- Unity is not a general-purpose polyglot monorepo — Python-first by mandate.
- Bootstrapping new Unity instances — depends on `pyforge-genesis`, unbuilt; a v2 dependency.
- Local Kubernetes development — the required cluster tool isn't available through the mandated channel on every platform; the intake root's documented stub stands.

## Success signal

Onboarding: a new engineer reaches a running local stack with a passing package test using only written documentation, in under an hour, single-digit commands (SM-1). Cross-team reuse — the innersource proof — trends up (contributions merged into Packages the contributor doesn't own) while the internal-fork counter-metric does not rise in step (SM-2 vs. SM-C1); if it stays near zero, the platform has failed at its premise regardless of technical quality. Reproducibility is verified, not assumed: 100% of declared platforms materialize every Environment from the lock, online and offline (SM-4). Compliance latency — time from vulnerability publication to a determination of estate impact — is measured in minutes, ahead of the EU CRA's 2026-09-11 reporting-obligation deadline (SM-5). Air-gap parity reaches 100% of enumerated capabilities, with any exception explicitly declared, never silently degraded (SM-6).

## Assumptions

- **Pixi-primary lock architecture:** the Workspace Lock (`pixi.lock`) is authoritative; `pylock.toml` is a derived PEP 751 export; offline deployment uses `pixi-pack`/`pixi-unpack`. Conda-native resolution is the differentiator and the alternative (PDM/PEP-751-primary) would discard it. This is the architecture's resolution (AD-2) but see Open Questions — it still needs explicit human ratification.
- V1 targets SLSA Build L1 mandatory, L2 (signed provenance from a hosted build platform) as the goal; L3 is out of scope.
- V1 delivers the Domain pattern plus one worked reference Domain (`customer`); the remaining ten Domains are adoption work, not build work — see Open Questions, this changes MVP effort by an order of magnitude if wrong.
- Data Classification is enforced at the configuration boundary; content-level inspection is deferred to v2.
- Primary Python targets are 3.13 and 3.14; 3.12 is legacy-only; 3.15 (2026-10-01) must be planned for inside this horizon.

## Open Questions

- **Lock authority (blocks everything):** is the Workspace Lock authoritative with the PEP 751 export derived, or the reverse, or split by tier? The architecture (AD-2) already resolves this as workspace-lock-primary and this Spec carries it as an assumption, but it still requires explicit **human confirmation** before any build work begins — it has not yet been independently ratified.
- **V1 Domain count (order-of-magnitude sizing):** does v1 ship the pattern plus one worked Domain, or all eleven? Carried as an assumption above but not confirmed at sign-off.
- **Platform Invariant vs. Domain Default classification:** AD-8 supplies the classification *mechanism*, but which specific Mandates get which classification is an unresolved sign-off decision — it directly determines whether Unity is genuinely federated/innersource (Data Mesh principle 4) or centrally imposed in practice.
- **Governance boundary:** where does the Constitution's spec-kit governance end and this repo's BMAD planning chain begin? Both are live simultaneously; unresolved, and the two risk drifting independently without an explicit decision.
