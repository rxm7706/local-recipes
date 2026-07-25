---
title: 'Story 2.4: Honest split coverage + the indeterminate producer (C0b)'
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

### Story 2.4: Honest split coverage + the indeterminate producer (C0b)

As a **conda/pixi maintainer**,
I want a truthful verdict that never claims "clean" for deps it couldn't assess,
So that a green check is trustworthy.

**Acceptance Criteria:**

**Given** a manifest where some deps resolve and some don't, **When** reported, **Then** coverage is **split** into hygiene vs vulnerability dimensions (FR15) and a partial result renders a **coverage-qualified verdict governed by the FR20 lattice** (partial vuln coverage ⇒ `indeterminate`, non-zero), never bare "clean" — the retired "clean at N%" phrasing is outlawed by FR16 (wording aligned 2026-07-16). **And** the coverage marks `direct-only` vs `locked-closure` (a loose manifest lists direct deps only; transitive vulns invisible without a lockfile).

**Given** a name-only / range / unmapped dep, **When** classified, **Then** it becomes `indeterminate` with a `WithholdReason` (`no-version`/`unmapped-ecosystem`/`native-nonpypi`/`range-only`) and is **never dropped or defaulted to clean** (C0b — FR13); the verdict exits **red-by-design** without needing E3's waivers. **And** an empty extraction is distinguished from "deps present but unresolved" (FR6).

**Given** a manifest-only repo with **no adjacent Python source** (the fleet's majority shape — feedstocks), **When** the hygiene axis runs, **Then** hygiene coverage is honestly **`not-applicable`/skipped, the reduced scope recorded — never a 100%-DEP002 noise wall** — matching Kedro FR-16's already-specced semantics for this schema's second producer. *(Added 2026-07-12 per readiness Major 3.)*

### Story 2.5: Name-level CVE tier + stale-DB + cross-ecosystem non-merge

As a **conda/pixi maintainer**,
I want a risk signal for my unpinned deps and honesty about the vuln-data freshness,
So that "vuln-coverage 12%" becomes an actionable worry-list, not a dead end.
*(Consumes the 1.4 provisioning decision for its stale-DB semantics.)*

**Acceptance Criteria:**

**Given** a mapped-but-unversioned dep, **When** the name-level tier runs, **Then** it flags whether the package carries **any known critical CVE across any version** ("pin/lock to prove immunity") — never assuming a version (FR13 guardrail).

**Given** an offline DB older than `--db-max-age` (per the 1.4 definition of "stale"), **When** scanned, **Then** the run routes to **`indeterminate` (exit 1) with a typed `vuln-data-stale` driver** — never a confident clean, never a silent 0 (FR12, aligned 2026-07-16 with NFR-S8 + C0); the report records the DB source + timestamp (FR11).

**Given** the same package name in a conda manifest AND a PyPI manifest, **When** inventoried, **Then** they stay **distinct per-ecosystem components** — no silent merge (FR7).

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
