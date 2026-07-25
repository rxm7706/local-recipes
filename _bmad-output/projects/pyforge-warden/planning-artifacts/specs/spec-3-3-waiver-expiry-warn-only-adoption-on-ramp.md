---
title: 'Story 3.3: Waiver expiry + warn-only adoption on-ramp'
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

### Story 3.3: Waiver expiry + warn-only adoption on-ramp

As a **conda/pixi maintainer adopting the gate**,
I want expired waivers to re-block and a warn-only first-run mode,
So that suppression can't rot silently and I can adopt without a day-one red wall.

**Acceptance Criteria:**

**Given** a waiver past its `expires_at`, **When** the next scan runs, **Then** the finding **re-blocks** (exit 1) and applied/expired waivers are flagged for review (FR25). *(Waiver expiry changes the input rung; `verdict.py` still owns the projection.)*

**Given** `--warn-only`, **When** run on a repo with pre-existing findings, **Then** findings surface as `warn`, exit **0**, and the report nudges how to graduate to an enforcing gate (FR23); this defends the `gate-disabled = 0` anti-metric.

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
