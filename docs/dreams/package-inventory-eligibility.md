---
title: Every package has one provenance trail and one eligibility answer, from any source
type: dream
owner: warden
status: archived
archived-reason: folded-into-station-dream
sibling-acknowledged: 141f93799f88b44c3476ccbc36a787a6431f9b4e25030a9b0f14a426d9577ef2
---

> **Consolidated into [[pyforge-warden]]** on 2026-09-17 (one-chain-per-station warden fold; folded from `package-inventory-eligibility`).


# Every package has one provenance trail and one eligibility answer, from any source

## The Dream

"Can I use this package" has no single, auditable answer today when the evidence for it is
scattered across several disconnected sources — a curated allow-list, an existing SBOM, a
manifest, download telemetry — each with its own identity format for the same package. Warden
already computes an authoritative answer to a NARROWER, related question — "does the package set
in THIS project pass THIS project's compliance gate" — via its own hygiene/security/license/currency
axes. This Dream is the wider question: given several INDEPENDENT evidence sources, not just one
project's own manifest, is a given package eligible for use at all, with full provenance back to
whichever source(s) said so — expressed as one CycloneDX artifact, the same output shape Warden
already produces for its narrower question.

## What it looks like when real

- A pluggable `SourceContract` (`fetch`/`parse`/`validate`/`ingest`) that new evidence sources
  implement without touching the union-computation core — mirroring `feeds.py`'s already-proven
  fetch/cache/provenance shape (KEV, endoflife.date, EPSS), generalized from "one feed, one
  reader" to "N heterogeneous sources, one adapter interface each."
- A normalization layer resolving `scikit-learn`/`scikit_learn`/`sklearn` to one canonical
  identity — largely already exists as `inventory.py`'s `Component` identity
  (`(ecosystem, canonical_name, concrete_version)`, PEP-503-canonical, purl-derived); the gap is
  exposing it as a standalone, adapter-facing API rather than something baked into
  `ResolvedInventory`'s own internals.
- Eligibility computed as the union of required-authority sources, each result carrying
  `ProvenanceEntry`s back to every source and timestamp that contributed — a genuinely new
  vocabulary (`eligible-union`/`observed-in-use`/`flagged-for-review`), distinct from `models.py`'s
  existing `Status` verdict rungs (`error`/`policy-violation`/`indeterminate`/`warn`/`bypassed`/
  `clean`/`not-applicable`), which answer "did this project's OWN scan pass," not "is this
  package allowed to exist in the estate at all."
- Output through `sbom.py`'s existing CycloneDX renderer and purl discipline (`packageurl.PackageURL`,
  never PEP-503 dot-collapsing) — this Dream needs a new INPUT pipeline, not a new output format.

## What is real

Substantial infrastructure already exists in `pyforge-warden` and this Dream extends it rather
than starting fresh:

- **`sbom.py`** already renders CycloneDX (1.6) with correct purl discipline and self-validation
  — but as a projection over one project's own `ResolvedInventory`, not a multi-source union.
- **`feeds.py`** already has the generic cache-dir/staleness/provenance substrate three feeds
  share (KEV, endoflife.date, EPSS) — structurally the closest existing analog to the Dream's
  `SourceContract`, but built for one feed shape at a time, not a registry of heterogeneous
  adapters.
- **`inventory.py`**'s `Component` identity is already close to the Dream's `PackageIdentity` —
  canonical, purl-derived, ecosystem-aware — though scoped internally rather than exposed as a
  standalone normalization API.
- **`mapping.py`** already ships a static, packaged conda↔PyPI identity map (sourced from atlas's
  `export-purls`) — narrower than the Dream's alias-resolution engine (no `[-_.]+` collapsing, no
  general name-alias table) but the same "bundled asset, no network" discipline.
- **`discovery.py`** scans a LOCAL filesystem target for manifests — nothing like the Dream's
  external adapters (gist, existing-SBOM, Artifactory), which is the genuinely new surface here.

The `SourceContract` ABC + adapter registry + union-eligibility computation
(`sources.py`'s ~1100 LOC of prior art) and the standalone normalization engine remain the real
gap — new modules, not a port of existing code, though every one of them has a structurally
similar sibling already proven inside `pyforge-warden`.

## Full feature audit against `package-inventory-eligibility`

Every capability the source dream names, and this Dream's disposition on each:

| Source feature | Disposition | Why |
|---|---|---|
| `SourceContract` ABC (`fetch`/`parse`/`validate`/`ingest`) | **Included, new** | The genuine gap — `feeds.py` is the closest existing shape but is single-feed, not a registry. |
| `GistSourceAdapter` (canonical gist, free/premium/default tiers) | **Omitted, WF-specific** | The "canonical gist" concept is a WF-org artifact (Google Assured OSS package lists); no PyForge equivalent source identified. The adapter *interface* is included; this specific adapter is not. |
| `CycloneDXSourceAdapter` (existing SBOM documents) | **Included** | Directly reusable — Warden already reads/writes CycloneDX elsewhere (`sbom.py`); parsing an EXTERNAL CycloneDX doc as one evidence source is a natural adapter. |
| `ManifestSourceAdapter` (requirements.txt, environment.yaml) | **Included** | Directly reusable — `discovery.py` already parses `environment.yaml`/`pyproject.toml`/lockfiles for the narrower per-project scan; the parsing logic is adjacent, adapting it as one evidence SOURCE among several is new wiring, not new parsing. |
| `ArtifactorySourceAdapter` (JSON package evidence) | **Omitted, no target confirmed** | No Artifactory instance is currently wired into this repo's `_http.py` enterprise-routing layer for this purpose; the adapter interface supports adding one later without presupposing it exists now. |
| Normalization / `PackageIdentity` / alias resolution | **Included, partially exists** | `inventory.py`'s `Component` identity already does most of this; the alias-resolution table (`scikit-learn`/`sklearn`) is the incremental piece. |
| Eligibility computation (union-based, 3 statuses) | **Included, new** | Genuinely new vocabulary, deliberately kept separate from `models.py`'s `Status` enum — see Constraints. |
| Conflict flag detection (10 string markers) | **Included** | Small, self-contained, ports directly — no PyForge-specific blocker. |
| `ProvenanceEntry` (source, locator, timestamp, metadata) | **Included, new** | No direct analog in Warden today; every existing axis reports a verdict, not a source-attributed provenance chain. |
| CycloneDX output | **Included, reused** | Via `sbom.py`'s existing renderer — see Constraints. Source targets 1.5; Warden's existing renderer already targets 1.6, so this Dream inherits 1.6 rather than regressing to match the source exactly. |
| Multi-environment SBOM generation (EDL/SAS/GCP/ODP parsers) | **Omitted, WF-specific** | Four named enterprise data-environment formats with no PyForge analog — this repo has no equivalent set of deployment environments to enumerate. |
| Cross-environment summary reports (markdown, discrepancy detection) | **Omitted** | Depends entirely on the multi-environment mode above; nothing to summarize without it. |
| Pre-generation count validation | **Included** | General-purpose sanity check (does an adapter's own result meet an expected minimum), ports independent of any WF-specific source. |

## Constraints

- **Reuse `sbom.py`'s CycloneDX renderer and purl discipline** — no second, divergent CycloneDX
  serializer.
- **Reuse `feeds.py`'s cache/staleness/provenance substrate** where an adapter's own fetch
  behavior fits that shape (a gist or Artifactory-JSON adapter plausibly does; an ad-hoc manifest
  parse does not need caching at all).
- **This eligibility vocabulary and `models.py`'s `Status` enum stay separate.** They answer
  different questions (estate-wide "may this exist" vs. project-scoped "did the scan pass") and
  must not be collapsed into one enum just because both live in Warden.

## Non-goals

- **Not real-time approval** — batch inventory, not a gating API (source dream's own framing,
  carried over unchanged).
- **Not vulnerability/CVE correlation** — Warden's existing `vuln.py`/CISA-KEV axis is the
  separate, already-shipped mechanism for that; this Dream's eligibility question is orthogonal.
- **Not license compliance analysis** — Warden's existing `license.py` axis already owns this for
  the narrower per-project question; this Dream's CycloneDX output can carry license fields if a
  source provides them, but computing compliance from them is out of scope here.
- **Not deciding which specific evidence sources this deployment needs** (a WF-equivalent gist,
  an internal SBOM registry, Artifactory telemetry) — that's a Spec-time question once a real
  target environment is named, not something this Dream should presuppose.

## Kinships

[[pyforge-warden]] (the estate this extends — `sbom.py`/`feeds.py`/`mapping.py`/`inventory.py` are
all direct prior art) · [[pyforge-doctor]] (per the source dream's own Kinships, Doctor would
validate this pipeline's output health, mirroring its existing role validating other stations'
verdict artifacts)

## Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit.
  Grounded directly against `pyforge-warden`'s existing modules (`sbom.py`, `feeds.py`,
  `mapping.py`, `inventory.py`, `discovery.py`) rather than assumed from the source dream's own
  framing — found closer structural overlap than expected (`inventory.py`'s `Component` identity
  is nearly the Dream's `PackageIdentity` already) but confirmed the union-eligibility computation
  and external-source adapter registry are genuinely new. No specific already-bitten incident
  motivates this one (unlike [[bmad-switch-scope-enforcement]]); captured because the gap is real
  and the existing infrastructure fit is unusually clean, not because of a documented pain point.
- **2026-09-09** — Fleet readiness pass (operator-approved batch, `fleet-readiness-decision-batch-2026-09-09.md`
  row warden-B8). Stories 7.1–7.3 `done`; the three genuinely-new pieces this Dream named
  all exist as real modules — `SourceContract` + registry (`sources.py`), the union with
  `ProvenanceEntry` trails and the separate `eligible-union`/`observed-in-use`/
  `flagged-for-review` vocabulary (`eligibility.py`), and CycloneDX output through the
  existing renderer (`eligibility_sbom.py`). **The Constraint that this vocabulary stay
  separate from `models.py`'s `Status` rungs HELD** — verified by reading, not assumed.
  Gap: no CLI verb reaches any of it (`cli.py` contains no `eligib*` string), so the Spec's
  Success signal — "one CLI question, one CycloneDX answer" — cannot be exercised; Spec
  moved `ready` → `in-progress`. The Spec's one open question (required-authority policy)
  is **answered in code** — `eligibility.py:113-121` defaults to unanimous consensus over
  every source present in the evidence — with the config surface deliberately deferred
  (`eligibility.py:128-131`); the deferral is accepted and recorded as a named residual,
  and the config story is minted only together with the missing CLI front door, since a
  settable policy no CLI can set is unreachable. This Dream stays `specified`.
