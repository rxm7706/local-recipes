---
title: 'Product Brief: Warden (pyforge-warden)'
status: complete
created: 2026-07-25
updated: "2026-08-26"
inputs:
  - 'docs/dreams/pyforge-warden.md'
  - 'docs/dreams/pyforge-charter.md § 4 Warden'
  - 'docs/specs/pyforge-warden.md (legacy Tier-1, FR1-FR40)'
  - '_bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md'
  - '_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md'
  - '_bmad-output/projects/pyforge-warden/planning-artifacts/research/market-dependency-compliance-sca-landscape-research-2026-07-25.md'
  - '_bmad-output/projects/pyforge-warden/planning-artifacts/research/domain-dependency-compliance-verdict-semantics-research-2026-07-25.md'
  - '_bmad-output/projects/pyforge-warden/planning-artifacts/research/technical-warden-dependency-gate-refresh-2026-08-08.md (folded 2026-08-26)'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/ (SPEC.md, stack.md, convergence.md — folded 2026-08-26)'
  - 'src/shared/packages/pyforge-warden/ (shipped package — README.md, pyproject.toml, src/pyforge/warden/*.py, tests/)'
note: 'RETROSPECTIVE brief — Warden shipped its complete v1 on 2026-07-25 (31/31 stories, PR #110 merged) before the factory adopted the research-first convention (same-day campaign). This brief backfills the missing product-brief tier and describes what was actually built and why it was worth building, grounded in the real, shipped evidence — it is not a pre-build planning input.'
---

# Product Brief: Warden (pyforge-warden)

## Executive Summary

Warden is the pyforge Guild's compliance station: a single, non-interactive CLI
(`pyforge-warden`, module `pyforge.warden`) that runs dependency trust checks across
Python projects sourced from **either PyPI or conda-forge** and returns one honest
verdict behind one frozen exit code. Its v1 shipped complete on **2026-07-25**
(**31 of 31 stories**, six epics, merged via **PR #110**, "complete (31/31) — Epics
5 & 6, all axes + fleet-readiness"), delivering a schema-validated `ComplianceReport`
at **schema version 1.1.0**. The soul of the product is a negative promise, not a
positive one: **Warden refuses to fake a pass** — an honest "not verified"
(`indeterminate`) beats a false "all clear," and the 2026-07-25 domain research found
no comparable SCA tool implements an equivalent non-collapsible partial-coverage
state. This brief is retrospective: Warden already exists, is dogfooded against this
repo's own ~1,950-manifest recipe corpus, and this document grounds *why the bet was
worth making*, not whether to make it.

**[FINDING — reconciling the Charter's "6-Axis" framing against what v1 actually
ships]**: the PyForge Charter names Warden a "6-Axis Ecosystem Security & Hygiene
Auditor" (hygiene · security · license · currency · provenance · maintenance). The
shipped v1 delivers **four axes with working gates** — hygiene, security, license,
currency — confirmed directly in the shipped `pyforge/warden/` package (`hygiene.py`,
`vuln.py`, `license.py`, `currency.py`) and the PRD's own D12 rebaseline ("v1 absorbs
the axis gates... FR space grown to FR1-FR40"). Axes 5–6 (Sigstore/SLSA provenance;
OpenSSF Scorecard maintenance) are named explicitly in Warden's own PRD as **Vision
(Future)**, not v1 scope. The Charter's "6-Axis" framing describes Warden's *durable
identity/mandate*, not the v1 delivered surface — this brief states both numbers
honestly rather than picking the more flattering one.

## The Problem (as it stood before Warden)

Dependency hygiene and dependency security were two disjointed tool categories, and
conda/pixi projects were second-class in both: **neither `deptry` nor `osv-scanner`
natively parses `pixi.toml`, `environment.yml`, v0 `meta.yaml`, or v1 `recipe.yaml`**
— a gap the 2026-07-25 market research independently, freshly reconfirmed still holds
against OSV-Scanner's current (v2.4.0-era) documentation. A conda-feedstock or
pixi-project maintainer wanting the same hygiene+CVE gate their PyPI-shipping peers
had could only hand-translate their manifest into a lossy `requirements.txt` fiction —
stale the instant the recipe changed, quietly wrong. Meanwhile, incumbents that *do*
scan conda projects (Trivy, Syft) only scan an already-**installed** environment via
`conda-meta/`, never the pre-build source manifest — so no tool served conda-feedstock
maintainers before their first build, and none brought dependency-*hygiene* to conda
at all.

## The Solution (what shipped)

One conda/pixi-native manifest front-door feeding independent per-axis assessment
paths, emitting one schema-validated report behind one exit code:

- **Manifest resolution bridge (E1)** — a stdlib-lean, non-executing extractor covers
  six formats: PyPI's native `pyproject.toml`/`requirements.txt` (delegated straight to
  deptry/osv-scanner, no bespoke parsing) plus the conda/pixi wedge — `environment.yml`,
  v0 `meta.yaml`, v1 `recipe.yaml`, and `pixi.toml`/`pixi.lock` — two-pass-evaluating
  Jinja/`${{ }}` templating and selectors, degrading to name-only+marked rather than
  failing. Corpus-conformance is enforced against **~1,950 real `recipe.yaml`/
  `meta.yaml` files** in this repo, 0 uncaught exceptions.
- **Four axes, each independently gateable** — hygiene (`deptry`), security
  (`osv-scanner`, enriched with CISA KEV + FIRST EPSS — both freshly confirmed live
  domain-standard feeds in the 2026-07-25 domain research), license
  (`license-expression`/SPDX), and currency (bundled LTS registry → endoflife.date →
  N/N-1 tiers). Hygiene and security gate by default; license and currency are
  flag-activated — unconfigured, their unknowns surface as `warn`, never a silent pass
  (D12 rebaseline, 2026-07-16).
- **The 7-rung verdict lattice and the frozen exit-code contract** —
  `error > policy-violation > indeterminate > warn > bypassed > clean > not-applicable`,
  projecting to exactly `{0, 1, 2, 130}`. The domain research's clearest finding: no
  comparable SCA tool surveyed (Renovate, Dependabot, Snyk, Trivy, Grype) implements an
  equivalent non-collapsible `indeterminate` state — every one defaults to a binary or
  ternary model that lets partial coverage render identically to a clean scan. Warden's
  own architecture doc records the adversarial-review catch that motivated this: the
  pre-lattice design "shipped a green-by-default on a bare `recipe.yaml`" — the
  beachhead's single most common artifact.
- **Waivers-as-code, expiring by default** — `--bypass --reason` commits a
  `.warden-waivers.yaml` stanza (default 14-day expiry, `authorized_by` field), read
  but never written by the tool; an expired waiver re-blocks. The market research
  freshly confirmed Renovate's own `ignoreDeps`/`packageRules` have **no** equivalent
  expiry mechanism — Renovate's own docs implicitly concede the gap by suggesting users
  "implement external processes to periodically audit and rotate" ignore lists, exactly
  the manual-process risk Warden's FR24 removes.
- **Baseline & grandfathering (FR39), the fix-PR actuator (FR40, opt-in
  `--open-fix-prs`)**, and a CycloneDX 1.6+ SBOM (FR27) with correct source-registry
  purls — all landed in the D12 rebaseline that grew the FR space from FR1–FR31 to
  FR1–FR40.

## What Makes This Different

Warden's differentiated wedge — pre-build, source-manifest resolution across six
formats including both v0/v1 conda recipes — is not a claim the market research had to
take on faith: it was **freshly reconfirmed against OSV-Scanner's current
documentation** that the gap still exists six weeks after Warden's original PRD made
the claim. The domain research adds the second, sharper differentiator: Warden's
`indeterminate` verdict state has no matched equivalent anywhere in the surveyed
comparable set. What Warden explicitly does **not** claim: it is not a ScanCode-depth
license scanner (metadata-only, not full source-text scanning) and not a Snyk/FOSSA
feature-surface replacement (no dashboards, no org-wide policy UI) — the differentiator
is ecosystem coverage and honest-coverage semantics, not feature parity with funded
commercial SCA suites.

## Who This Serves

- **Conda-feedstock / pixi maintainers (the beachhead)** — a hygiene + CVE gate on
  manifests neither engine parses natively; this repo's own `recipes/` corpus is the
  dogfood proof.
- **PyPI-world developers** — collapse two CI steps plus a brittle `jq` script into one
  trustworthy gate; Warden adds no bespoke parsing here, purely delegating to deptry/
  osv-scanner's native inputs.
- **Platform engineers (fleet distribution)** — a deterministic exit-code contract and
  self-routing typed errors (`error_kind` → developer/platform/CLI-maintainer
  ownership) designed for 20,000+-repo fleet rollouts without false-green or red-storm
  failure modes.
- **The local developer at a terminal (P8, workstation mode)** — `warden scan .
  --warn-only` as the recommended first contact; `--doctor` as a zero-network
  environment self-check before trusting any verdict.

## Success Criteria (as delivered)

- **31/31 stories shipped**, six epics complete (Epic 1 core scaffold/engines
  through Epic 6 multi-axis expansion — license/currency gates, KEV+EPSS, baseline,
  fix-PR actuator, engine version-range pinning), merged via PR #110.
- **Schema 1.1.0** — the one sanctioned additive bump from 1.0.0 (Story 6.1),
  confirmed directly in the shipped `report.py` (`REPORT_SCHEMA_VERSION = "1.1.0"`).
- **The C0 gate-integrity invariant held**: never false-green across the adversarial
  fixture set — the acceptance property the whole architecture was built around.
- **`warden scan --doctor`** ships as a flag (not a verb): verifies engine
  versions, the offline OSV database, and KEV/EPSS/endoflife feed caches with zero
  network access and zero project scanning, returning only `{0, ERROR}` — "doctor
  reports operability, not policy," per the shipped README.
- **Dogfooded against this repo's own corpus** — `scripts/dogfood_scan.py` and the
  `.warden-baseline.yaml` at `src/shared/packages/pyforge-warden/` are shipped,
  working artifacts, not aspirational examples.

## Scope (what actually shipped, six epics)

| Epic | Delivered |
|---|---|
| 1 | Frozen contract + verdict lattice, interfaces/null-engine harness, **deptry** as the first engine, offline OSV-DB provisioning spike, **osv-scanner** as the second engine, severity gate + end-to-end verdict composition, typed errors + no-scan guard, human/machine report renderers, manifest discovery + the resolved scan set |
| 2 | Conda↔PyPI ecosystem-identity predicate, non-rendering extraction (the differential oracle), the full supported-construct matrix, the honest split-coverage `indeterminate` producer, name-level CVE tier + stale-DB + cross-ecosystem non-merge guards, lockfile extraction (the vuln hero path) |
| 3 | Configurable policy, auditable expiring waivers, waiver-expiry warn-only adoption on-ramp |
| 4 | CycloneDX SBOM emission |
| 5 | Actionable diagnostics + safe-by-default posture, fleet-scale validation corpus + oracle maturation |
| 6 | Versioned `ComplianceReport` schema amendment (1.1.0), license-axis gate flags, currency-axis gate flags, KEV feed provisioning + `--fail-on-kev`, two-mode policy integration, engine version-range pinning, EPSS feed + `--min-epss`, baseline & grandfathering, fix-PR actuator, design-spike amendment (finding-ID families, verdict encoding, rung discriminator, fold semantics) |

**Explicitly out of v1 (PRD's Growth/Vision tiers, not built):** public PyPI/
conda-forge publish; a channel/index-provenance axis; SARIF output; engine-
swappability (`--engine` for `fawltydeps`/`pip-check-reqs`); **the provenance axis
(Sigstore/SLSA) and the maintenance axis (OpenSSF Scorecard)** — the Charter's named
axes 5–6, both Vision-tier; typosquat detection; the fleet control plane / OSPO
practice layer.

## Vision (where it points next)

The PyForge Charter's six-axis identity is Warden's durable mandate, not a v1
overclaim — axes 5–6 remain named, intentional future scope, and the domain research
found a concrete external precedent for how they'd likely be built if evidence ever
gates them in: deps.dev's own pattern of joining an existing OpenSSF Scorecard feed
rather than building a parallel scorer (cross-referenced from the companion
`pyforge-atlas` domain research, since both Atlas and Warden would consume the same
external signal). Warden's data relationship with Atlas is already established and
one-directional (Atlas provides package/vulnerability/velocity data; Warden consumes it
as one input to its axes; no code import runs the other way) — any future provenance
or maintenance axis would likely extend that same pattern rather than invent a new one.

## Open Questions (carried forward, none v1-blocking)

- Should the Charter's "6-Axis" framing be revised to explicitly mark axes 5–6 as
  Vision/not-yet-built in future deck or docs passes, to prevent the same
  reconciliation this brief had to do from recurring? (Flagged for Herald/Marshal's
  docs-sync loop, not a Warden change.)
- Does Snyk's `.snyk` policy file support an expiry field equivalent to Warden's FR24?
  Could not be independently verified this session (market research, two 404'd doc
  fetches) — worth a fresh check before citing it competitively.
- `architecture.md`'s pinned-engine-contracts frontmatter still cites `fpgmaas/deptry`;
  the project has organizationally transferred to `osprey-oss/deptry` (confirmed live,
  2026-07-25) — a low-urgency doc-currency fix, not a behavior change.

## Assumptions

- No market-facing sections beyond the comparable-tool framing already grounded in
  the two 2026-07-25 research reports — Warden's actual go-to-market (internal gate,
  eventual cf_atlas promotion per FR-16/FR-18) is unchanged by this brief.
- **Retrospective grounding, not speculative planning**: every claim above is sourced
  from the shipped PRD/architecture/epics artifacts, the shipped package at
  `src/shared/packages/pyforge-warden/`, PR #110's own merge record, and the two
  2026-07-25 research reports — this brief backfills a missing tier for a project that
  shipped its full v1 the same day, not a proposal for new work.
- Headless/express drafting: produced without an interactive discovery conversation,
  consistent with the other backfilled briefs in this campaign (Doctor, Herald, Mason,
  Scribe, Steward).

## Currency reconciliation — 2026-08-26

The body above is the retrospective record of the **v1 close** (2026-07-25, 31/31
stories, six epics, PR #110) and is retained as history. This pass folds in what has
happened since — the 2026-08-08 technical research refresh (which post-dated this
brief) and the post-v1 growth through 2026-08-26 — as concrete deltas:

**1. The 2026-08-08 technical research is now folded in**
(`research/technical-warden-dependency-gate-refresh-2026-08-08.md` — the post-ship
technical audit the 2026-07-25 research pair left open). Its load-bearing findings for
this brief's claims:

- The shipped surface is measured, not asserted: ~11,700 lines across 20 modules, with
  three **machine-enforced** concentrations of authority — verdict sole-ownership
  (`verdict.py` + its meta-test), subprocess sole-siting (`engines.py`/`_engine_env()`),
  and the frozen `report-schema.json`/`models.py`/`verdict.py` trio. The C0
  never-false-green claim in this brief held in every recorded incident.
- Four recurring bug **families** were named from the 8 retros + the verified
  deferred-work ledger: (A) cross-ecosystem name/version identity normalization —
  the deepest, with an "identity sole-ownership module" proposed as a third wall;
  (B) remediation/advice correctness (the verdict is safe; the advice strings are the
  false-statement hotspot); (C) shared constants + calendar time bombs; (D)
  validation-wiring gaps — "the gate that doesn't gate itself."
- Two P0 debt items remain **open** as of the 2026-08-26 ledger:
  **DW-5-2-5** (nothing schedules `pyforge-warden-test-corpus-oracle` — the strongest
  honesty check is never executed by CI) and **DW-5-2-7** (all 19
  `.warden-baseline.yaml` entries expire simultaneously 2027-07-24 — a deterministic
  future red-day).
- Upstream watch: **osv-scanner v2.5.0** (2026-08-07) migrated end-to-end onto
  OSV-Scalibr — the next in-range engine bump is a pipeline replacement, defended by
  the 6.6 version-range pin; **deptry** transferred to `osprey-oss/deptry` (still
  v0.25.1, no release since 2026-03).

**2. Scope has grown past this brief's "31/31, six epics" frame.** The sprint ledger
(2026-08-26) shows **41/41 stories done across ten epics**:

- **Epic 7** (2026-08-22, decomposes `spec-package-inventory-eligibility`) — the
  estate-wide eligibility union: `sources.py` SourceContract adapters + the identity
  API, `eligibility.py` provenance-carrying union, `eligibility_sbom.py` CycloneDX out
  + the FABRIC fixture corpus.
- **Epic 8** (2026-08-22, decomposes `spec-compliance-factory-web-face`) — the web
  face: upload runs the real engines async (Celery, keys-not-blobs), results render
  with derived progress. Relocated 2026-08-24 to `src/shared/packages/django-warden`
  (`django_warden_fabric`) at `/stations/warden/`, with `/compliance/` kept as a
  permanent redirect (steward Story 19.1).
- **Epic 9** (2026-08-24) — Warden publishes the **PR-gate hook book** on
  `pyforge.core.hooks`; today's engines and commercial scanners (Checkmarx, Sonar,
  Black Duck, GHAS) become optional **plugins**; default Warden stays green with no
  named commercial scanner present.
- **Epic 10** (2026-08-26) — station-owned SKF skill + `bmad-agent-warden` persona
  (Path B uses `pyforge warden …` grammar + `POST /stations/warden/mcp` only), and the
  first portal slice: start/get one audit through PortalClient.

**3. The Unifying Strategy pack now names Warden's estate roles**
(`spec-pyforge-unifying-strategy`, steward): Warden is **the only PR quality-gate
verdict on the Golden Path** — external scanners register as Warden plugins under
Warden-owned hook specifications, never a competing pass/fail, and the core gate never
fails solely because a named scanner plugin is absent (CAP-18). The Canopy host serves
Warden's portal and MCP face; the historical `/compliance/` URL survives as a
permanent redirect. This is the durable framing of the brief's "fleet distribution"
persona: distribution is now the platform, not just a CI template.

**4. Open-question closures from the list above:** the `fpgmaas/deptry` citation
question is resolved — `architecture.md`'s pinned contract cites `deptry.com` and the
upstream org move (`osprey-oss`) is recorded in its 2026-08-26 reconciliation; the
Charter "6-Axis" framing note still stands (axes 5–6 provenance/maintenance remain
Vision-tier, unbuilt as of 2026-08-26); the Snyk expiry-field verification remains
unperformed.
