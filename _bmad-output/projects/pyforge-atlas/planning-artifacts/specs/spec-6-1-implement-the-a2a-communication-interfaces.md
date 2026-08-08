---
title: 'Story E1 (6.1): Implement the A2A communication interfaces'
type: 'feature'
status: shipped
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #90 body + main commit log; dev narrative recovered, review-triage partial)'
---

> **Contract-spec — no original ever existed (corrected 2026-07-25).** This story
> (wave B9–H4) was built by the atlas migration's **in-session agent loop**, which —
> unlike `bmad-create-story` (used only for waves 0/A/B1–B8) — never emitted a per-story
> spec file. The atlas migration session (`01FYyQvBJuXwySiaMUUYCqBZ`) confirmed this
> exhaustively: no such file exists in `implementation-artifacts/`, `.bmad-loop/runs/`
> (which never existed for atlas), any git worktree, git history, or anywhere on disk.
> **Nothing was lost — there is no original to recover.** This file carries the
> load-bearing contract (Intent + Acceptance Criteria **verbatim** from the tracked
> `planning-artifacts/epics.md`) plus a dev narrative reconstructed from the merged record
> (the "Dev narrative" section below). A fuller BMAD-story-format reconstruction (Dev
> Agent Record + File List + Review Triage Log, built from the agent-loop transcripts) is
> at `../../spec-archive/retro-story-files/6-1-e1.md` — the operator's web-session archive.

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

## Tasks / Subtasks

*(Derived from the ACs — no original task breakdown was authored for this loop-run story.)*

- [x] the `cf_atlas` analytical agent can hand a structured payload to the `conda-forge-expert` agent (publish/subscribe or direct-message — transport resolves in this story's spec, Spine Deferred)
- [x] payload schemas live in the `a2a/` module — the single schema source for alerts and insights (AD-20)
- [x] payloads feeding authoring decisions carry their build timestamp (AD-17).

## Dev Notes

**Planning metadata (from `epics.md`):**

- **FRs:** FR-11.
- **Invariants:** AD-20 (sole structured inter-agent channel), AD-17.
- **Mode:** LOOP-E.
- **Gating question:** none (A2A transport is a story-spec decision, not a Q-gate).
- **Verify gate:** existing gates + payload round-trip fixture in `kedro-test`.
- **Depends on:** B3 (MCP surface), Epic 5 (BSL insights to carry).

### Implementation notes

<!-- DERIVED 2026-07-27 by reading the shipped code (PR #90). No original dev-session
     notes existed for this story; this is what the merged implementation actually does. -->

**One channel, one schema source (AD-20).** `pyforge.atlas.a2a` is the sole structured
inter-agent channel *and* the single schema definition for **both** alerts and insights.
Every payload the analytical agent hands the authoring agent — a BSL-derived insight or an
FR-10/FR-18 alert — is one variant of a single family (`AtlasPayload` → `AtlasAlert` /
`AtlasInsight`). The named hazard this closes is "two competing alert dialects," which is
what happens when alerts and insights are allowed to evolve separate schemas.

**The guard is structural.** `tests/a2a_surface/test_a2a_payloads.py` asserts that **no
other module defines a payload schema**. One implementation detail worth keeping: the test
directory is named `a2a_surface`, not `a2a`, because pytest's prepended sys.path would
otherwise let the test package shadow the real `a2a` SDK.

**A payload cannot be built without provenance (AD-17).** `build_stamp` is **injected**, not
read from `datetime.now()` inside the builder. That makes construction deterministic under
test and means every payload feeding an authoring decision carries the timestamp of the data
it came from — the mechanism behind the kernel's "pipeline snapshots are advisory" rule.

**An insight cannot reference a metric that does not exist (AD-8).** `build_insight_payload`
validates `metric_id` against the BSL registry via `semantic.METRIC_PROVENANCE`. A builder
can only mint an insight pointing at a real, declared metric — so the A2A surface cannot
drift away from the semantic layer by inventing metric names.

**Decode is part of the contract.** `decode_payload` and an explicit `SCHEMA_VERSION` ship
alongside the builders, so the receiving side has a sanctioned way to read a payload rather
than duck-typing a dict.

### References

- [Source: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md#Story-E1]
- [Source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md#§9-Story-E1]
- [Architecture: _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md]

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Delivery Record

<!-- DERIVED from the merged PR via `gh` on 2026-07-27. Exact, not reconstructed. -->

| | |
|---|---|
| Pull request | **#90** — story(E1): A2A structured-payload surface between the two agents (FR-11) |
| Merged | 2026-07-18 |
| Diff | 7 files, +830 / -0 |
| Test files touched | 3 |

**Commits**

- `210b3a3` story(E1): A2A structured-payload surface between the two agents (FR-11)
- `01f8f82` story(E1): harden AD-20 guard + enforce schema_version + close model_…

**File list** *(exact, from the merged diff)*

```
  298 +     0 -  src/shared/packages/pyforge-atlas/tests/a2a_surface/test_a2a_payloads.py
  210 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/a2a/schema.py
  162 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/a2a/transport.py
   63 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/a2a/__init__.py
   59 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/a2a/builders.py
   38 +     0 -  src/shared/packages/pyforge-atlas/tests/catalog/test_no_inline_io.py
    0 +     0 -  src/shared/packages/pyforge-atlas/tests/a2a_surface/__init__.py
```

## Dev Agent Record

### Agent Model Used

In-session BMAD agent loop (draft → 2× adversarial review → 1× independent fresh-eyes review → real-gate verify), not a `bmad-dev-story` story-file run.

### Completion Notes List

- **Impl commit `210b3a3`** — story(E1): A2A structured-payload surface between the two agents (FR-11)
  - Adds the `a2a/` module as the SINGLE schema source (AD-20) for structured
  - inter-agent payloads between the cf_atlas analytical agent and the
  - conda-forge-expert authoring agent — insights and alerts are ONE discriminated
  - pydantic family (_BasePayload -> AtlasInsight kind="insight" / AtlasAlert
  - kind="alert"), never two competing dialects (the risk the architecture review
  - flagged).
  - - schema.py -- the payload family + canonical-JSON round-trip; unknown/absent
  - `kind`, malformed JSON, or a validation failure raises the declared
  - A2ADecodeError (never an uncaught crash). Every payload carries a REQUIRED,
  - INJECTED build_stamp (AD-17) — a validator rejects an empty stamp.
  - - builders.py -- construct a payload FROM a BSL insight (referencing the D1
  - semantic metric by identifier, never re-implementing it — AD-8) and from an
  - alert condition (contract violation / policy breach, FR-10/FR-18 family).
  - - transport.py -- resolves the transport decision as DIRECT IN-PROCESS
  - message-passing (hand_off -> AuthoringInbox): payload <-> a2a.types.Message
  - serde + a real, zero-network analytical->authoring hand-off. The live
  - cross-process wire is DEFERRED (DW-E1-1).
  - - AD-20 import-ban: only the a2a/ subpackage imports the a2a SDK (AST guard
  - extended in tests/catalog/test_no_inline_io.py, beside the C1/D1/D2 bans);
  - the no-second-dialect invariant is structural (no payload schema outside a2a/).
  - Verify: payload round-trip + hand-off fixtures in tests/a2a_surface (no new
  - named gate — Wave E verifies against existing gates + its fixtures). 599 passed
  - (+21 new).

## Review Triage Log

Independent/Gemini review produced follow-up fix commit(s) on PR `#90`:

- `01f8f82` — story(E1): harden AD-20 guard + enforce schema_version + close model_construct bypass (review)

## Dev narrative — recovered from the merged record

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #90: story(E1): A2A structured-payload surface between the two agents (FR-11)

## Deferred Work (DW ledger)

### DW-E1-1 — the live cross-process A2A wire (a running fasta2a server / broker) — DEFERRED
- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story E1, FR-11)
  summary: E1 shipped the load-bearing, buildable-now half of the A2A surface — the `a2a/` module as the SINGLE payload schema source (AD-20: one discriminated family for both insights and alerts, no second dialect), the AD-17-stamped builders (`build_insight_payload` referencing a BSL metric by `semantic.METRIC_PROVENANCE` id per AD-8 / `build_alert_payload`), the exact payload↔`a2a.types.Message` serialize/deserialize round-trip (canonical JSON inside a real a2a-sdk DataPart — protobuf Struct would floatify ints, so JSON preserves the payload EXACTLY), and the resolved transport: **direct in-process message-passing** (`hand_off` → `AuthoringInbox`) proving the cf_atlas-analytical → conda-forge-expert-authoring direction offline + deterministically. The genuine cross-process wire — standing up a live `fasta2a` (FastAPI-style A2A) server or an A2A broker between two OS processes so the two agents exchange messages over a bound socket — is DEFERRED: it needs a bound socket + a second process, neither of which comes up offline in-container, and faking a broker would be dishonest (mirrors the DW-C1-1 live-Dagster-schedule and DW-D3-1 live-LLM-backend attended bring-ups). Because the message ENVELOPE is already the real a2a-sdk `Message`, the follow-up is a delivery-substrate swap (`inbox.receive(msg)` → an HTTP/broker `send`), not a schema change. Do NOT weaken the offline round-trip/hand-off gate to unattended-execute a live server.
  evidence: `tests/a2a_surface/test_a2a_payloads.py` drives the whole surface against the in-process hand-off — `test_insight_round_trip_is_exact` / `test_alert_round_trip_is_exact` (exact incl. AD-17 stamp, no int→float drift, unicode), `test_analytical_to_authoring_hand_off` (ordered exact delivery to the authoring inbox), the AD-20 single-schema-source scans (`test_ad20_no_competing_payload_schema_outside_a2a`, `test_ad20_only_a2a_schema_subclasses_the_base`) + `tests/catalog/test_no_inline_io.py::test_a2a_sdk_only_in_a2a_layer` (only `a2a/` imports the a2a SDK), AD-17 (`test_ad17_stamp_required_and_injected`, `test_ad17_stamp_on_the_wire_envelope`), AD-8 (`test_ad8_insight_metric_must_be_a_bsl_identifier`), and the degrade-not-crash edges (unknown kind / malformed JSON / non-JSON-native field / missing payload part). No socket is bound and no second process is spawned in any test (AD-11 / offline).
