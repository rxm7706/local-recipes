---
title: 'Story E1 (6.1): Implement the A2A communication interfaces'
type: 'feature'
status: 'regenerated'
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'lost to the Tier-3 paper-trail gap + the 2026-07-19 truncation incident; dev-notes / review-triage-log not recovered'
enriched: '2026-07-25 (merged PR #90 body + main commit log; dev narrative recovered, review-triage partial)'
---

> **Regenerated contract-spec (2026-07-25).** The original per-story spec was lost when
> its Tier-3 (gitignored) `implementation-artifacts/` copy was destroyed (worktree
> teardown + the 2026-07-19 truncation incident — atlas story files were 0-byte or gone).
> This file **recovers the load-bearing contract**: the Intent and Acceptance Criteria
> below are lifted **verbatim** from the tracked, authoritative `planning-artifacts/epics.md`
> (the source the original spec was derived from). What is **not** recovered: the original
> implementation dev-notes and review-triage log. Ground truth for what shipped is the
> merged PRs (#58–#105); behaviour is exercised by the migrated pipeline on `main`.

## Contract (from epics.md — verbatim, authoritative)

### Story E1 (6.1): Implement the A2A communication interfaces

As a CFE authoring agent,
I want a structured A2A surface between the cf_atlas analytical agent and the conda-forge execution agents,
So that insights, contract violations, and policy breaches arrive as structured payloads, not prose.

**Acceptance Criteria:** (spec § 9 Story E1, binding)

**Given** the two agents (cf_atlas analytical, `conda-forge-expert` authoring)
**When** the A2A surface is built
**Then** the `cf_atlas` analytical agent can hand a structured payload to the `conda-forge-expert` agent (publish/subscribe or direct-message — transport resolves in this story's spec, Spine Deferred)
**And** payload schemas live in the `a2a/` module — the single schema source for alerts and insights (AD-20)
**And** payloads feeding authoring decisions carry their build timestamp (AD-17).

- **FRs:** FR-11.
- **Invariants:** AD-20 (sole structured inter-agent channel), AD-17.
- **Mode:** LOOP-E.
- **Gating question:** none (A2A transport is a story-spec decision, not a Q-gate).
- **Verify gate:** existing gates + payload round-trip fixture in `kedro-test`.
- **Depends on:** B3 (MCP surface), Epic 5 (BSL insights to carry).

### Story E2 (6.2): Integrate OpenLineage + OpenTelemetry

As the operator,
I want Kedro nodes, Dagster runs, and DuckDB queries instrumented with OpenLineage and OTel,
So that lineage, per-node metrics, and end-to-end traces are observable down to specific API calls.

**Acceptance Criteria:** (spec § 9 Story E2, binding)

**Given** the compiled DAG and hooks layer
**When** instrumentation lands
**Then** lineage + per-node metrics (rows, latency, cache hits) are captured via OpenLineage
**And** end-to-end distributed traces are visible via OTel down to specific API calls
**And** emitted-event/span fixtures are this story's gate assets (AD-20 — fixture-verified, since Wave E has no new named gate).

- **FRs:** FR-12.
- **Invariants:** AD-20, AD-6 (hooks declared in run config — every entry point inherits them, AD-23).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** existing gates + emitted-event/span fixtures in `kedro-test`.
- **Depends on:** C1 (Dagster runs to instrument).

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

## Dev narrative — recovered from the merged record (2026-07-25)

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #90: story(E1): A2A structured-payload surface between the two agents (FR-11)

## Summary

Opens Wave E. Adds the `a2a/` module as the **single schema source** (AD-20) for structured inter-agent payloads between the cf_atlas analytical agent and the conda-forge-expert authoring agent — insights and alerts are **one discriminated pydantic family** (`_BasePayload` → `AtlasInsight` `kind="insight"` / `AtlasAlert` `kind="alert"`), never two competing dialects (the risk the architecture review flagged).

- **`schema.py`** — the payload family + canonical-JSON round-trip; unknown/absent `kind`, malformed JSON, or a validation failure raises the declared `A2ADecodeError` (never an uncaught crash). Every payload carries a **required, injected `build_stamp`** (AD-17) — a validator rejects an empty stamp.
- **`builders.py`** — construct a payload **from a BSL insight** (referencing the D1 semantic metric by identifier, never re-implementing it — AD-8) and **from an alert condition** (contract violation / policy breach).
- **`transport.py`** — resolves the transport decision as **direct in-process message-passing** (`hand_off` → `AuthoringInbox`): payload ↔ `a2a.types.Message` serde + a real, zero-network analytical→authoring hand-off. The **live cross-process wire is deferred** (DW-E1-1).
- **AD-20 import-ban** — only the `a2a/` subpackage imports the a2a SDK (AST guard extended, beside the C1/D1/D2 bans); the no-second-dialect invariant is structural.

## Scope

Live cross-process transport (a running A2A server/broker) is deferred to DW-E1-1; the schema + round-trip + in-process hand-off is the AC's real, gated core.

## Tests

`599 passed` (+21 new) — payload round-trip + hand-off fixtures in `tests/a2a_surface` (no new named gate; Wave E verifies against existing gates + its fixtures).

### Commits on `main`

- `08a4e844f9` story(E1): harden AD-20 guard + enforce schema_version + close model_construct bypass (review)  _(review-fix)_
- `32d28c5264` story(E1): A2A structured-payload surface between the two agents (FR-11)  _(dev-landing)_

_This PR also carried an automated Gemini review; not reproduced here per repo policy ([[feedback_no_gemini_reviews]])._

