---
title: 'Story 4.1: CycloneDX SBOM emission'
type: 'feature'
status: 'regenerated'
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'lost to the Tier-3 paper-trail gap; dev-notes / review-triage-log not recovered'
---

> **Regenerated contract-spec (2026-07-25).** The original per-story spec file was
> lost when its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed on
> worktree teardown. This file **recovers the load-bearing contract** — the Intent and
> Acceptance Criteria below are lifted **verbatim** from the tracked, authoritative
> `planning-artifacts/epics.md` (the source the original spec was derived from), and the
> Realized-in section maps it to the shipped implementation on `main`. What is **not**
> recovered: the original implementation dev-notes and the review-triage log (those lived
> only in the lost file). Behaviour is verified by the current green suite; the story is
> done and merged.

## Contract (from epics.md — verbatim, authoritative)

### Story 4.1: CycloneDX SBOM emission

As a **CI pipeline / SBOM consumer**,
I want an honest CycloneDX SBOM of the resolved inventory,
So that I can feed downstream supply-chain tooling.

**Acceptance Criteria:**

**Given** `--sbom-output <file>`, **When** a scan completes, **Then** a schema-valid **CycloneDX 1.6** BOM is emitted via cyclonedx-python-lib as a **read-only projection over the frozen inventory** — source-registry-correct purls (`pkg:pypi/…` vs `pkg:conda/…?channel=`), **self-declared partiality** when coverage < 100% (FR27). **And** `len(SBOM.components) == inventory_count` (root excluded).

**Given** an adversarial component name (control chars, `</script>`, purl-reserved), **When** serialized, **Then** the schema-aware encoder neutralizes it (NFR-S7) — the tool is never an injection vector against a downstream consumer.

**Given** the estate SBOM conventions, **When** the BOM is emitted, **Then** conda↔pypi identity is expressed via the **`cfe:*` property namespace** (`cfe:pypi_purl`, `cfe:match_source`, `cfe:match_confidence` on the conda component), purls follow **G98 normalization** (lowercase, `_`→`-`, dots preserved; `?channel=` qualifier on conda purls), and the **round-trip holds**: `scan-project --sbom-in <our-BOM>` ingests cleanly. *(Added 2026-07-12 per readiness/X7 — three SBOM producers share these conventions.)*

## Realized in

- **Package:** `src/shared/packages/pyforge-warden/` (import `pyforge.warden`).
- **Status:** done + merged to `main`.
- **Verification:** the shipped behaviour for this story is covered by the current
  `pixi run --frozen -e pyforge-warden pyforge-warden-test` suite (green on `main`).
  For the precise file-level Code Map, read the implementation on `main` — this
  regenerated spec deliberately does not guess a per-file map it cannot verify from the
  lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Root cause: story specs lived in Tier-3
gitignored `implementation-artifacts/`; they are now tracked here in
`planning-artifacts/specs/` so they survive worktree teardown and are in every clone.
