---
title: 'Story 1.9: Manifest discovery, deterministic selection & the resolved scan set (FR1)'
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

### Story 1.9: Manifest discovery, deterministic selection & the resolved scan set (FR1)

As a **maintainer with several manifests in one repo**,
I want the tool to discover, classify, and deterministically select what it scans — and tell me what it chose,
So that a wrong-but-quiet manifest choice can never produce a false-green.

**Acceptance Criteria:**

**Given** a tree with multiple candidate manifests, **When** `scan <path>` runs, **Then** discovery + classification + **precedence is total and deterministic** — the same tree yields the same resolved scan set every time (FR1) — and each dependency source-section routes to the correct extractor (FR2).

**Given** the resolved scan set, **When** the report is emitted, **Then** it is a **first-class field** on `ResolvedInventory` (an operator sees *what was scanned*, never infers it).

**Given** discovery finds **nothing parseable while Python signals are present**, **When** it resolves, **Then** it is an **`error` (exit 2, per PRD D2 fail-closed)** routed to the developer; **Given** discovery is **ambiguous or partial** (candidates found, selection/parse uncertain), **Then** it becomes **`indeterminate` (exit 1), never `clean`** — the load-bearing AC that makes discovery a gate, not cosmetics. *(Split corrected 2026-07-12 to align with D2 — different failure classes, different owners.)*

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
