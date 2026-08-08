---
title: 'Story F2 (7.2): Implement the data-validation hook and inline Pandera contracts'
type: 'feature'
status: shipped
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #93 body + main commit log; dev narrative recovered, review-triage partial)'
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
> at `../../spec-archive/retro-story-files/7-2-f2.md` — the operator's web-session archive.

## Contract (from epics.md — verbatim, authoritative)

### Story F2 (7.2): Implement the data-validation hook and inline Pandera contracts

As the operator,
I want inline pandera contracts behind a validator-agnostic `AfterNodeRunHook` with version-capped GX as boundary layer,
So that bad data halts the pipeline before persisting, with an A2A alert.

**Acceptance Criteria:** (spec § 9 Story F2, binding)

**Given** a malformed-payload fixture (e.g. PyPI JSON missing a version field)
**When** the node runs under the validation hook
**Then** the validation failure halts execution by raising a native Python exception
**And** the failure propagates to Dagster, halting the pipeline and raising an A2A alert
**And** the hook interface is validator-agnostic: swapping/adding the GX backend requires no node changes (fixture-proven with a stub second validator)
**And** GX participates only at conda-forge 1.18.2 (no ≥1.19 features); the `kedro-great-expectations`/`kedro-pandera` plugins are banned (AD-9).

- **FRs:** FR-10.
- **Invariants:** AD-9, AD-20 (alert channel), AD-23 (hook rides every entry point).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (halt fixture + stub-validator fixture).
- **Depends on:** E1 (A2A alert channel), C1 (Dagster halt propagation).

## Tasks / Subtasks

*(Derived from the ACs — no original task breakdown was authored for this loop-run story.)*

- [x] the validation failure halts execution by raising a native Python exception
- [x] the failure propagates to Dagster, halting the pipeline and raising an A2A alert
- [x] the hook interface is validator-agnostic: swapping/adding the GX backend requires no node changes (fixture-proven with a stub second validator)
- [x] GX participates only at conda-forge 1.18.2 (no ≥1.19 features); the `kedro-great-expectations`/`kedro-pandera` plugins are banned (AD-9).

## Dev Notes

**Planning metadata (from `epics.md`):**

- **FRs:** FR-10.
- **Invariants:** AD-9, AD-20 (alert channel), AD-23 (hook rides every entry point).
- **Mode:** LOOP-E.
- **Gating question:** none.
- **Verify gate:** `kedro-test` (halt fixture + stub-validator fixture).
- **Depends on:** E1 (A2A alert channel), C1 (Dagster halt propagation).

### Implementation notes

<!-- DERIVED 2026-07-27 by reading the shipped code (PR #93). No original dev-session
     notes existed for this story; this is what the merged implementation actually does. -->

**One hook, every entry point.** The validation hook rides a `kedro run` and the C1 Dagster
plane identically — both validate node outputs against their per-dataset contract and halt
**before** bad data persists. That is the "one execution plane" constraint paying off: the
hook is declared once and inherited, not wired per entry point.

**The registry ships empty, on purpose.** `DEFAULT_CONTRACTS` is an empty registry and the
default alert sink is a no-op. Constructed with no arguments, the hook is offline and
**cannot false-halt until a contract is actually declared**. The story shipped the machinery
and the seam and nothing speculative — which is why turning it on later is a data change, not
a code change.

**Contracts are data, never inline in a node.** They are declared in the registry keyed by
dataset. A node body never carries its own schema assertions, for the same reason it never
carries IO.

**Validator-agnostic by protocol (AC-3).** `Validator` is a `Protocol` with a single
`check(dataset, data) -> list[ContractViolation]`. `PanderaValidator` is the shipped inline
backend; swapping or adding a second backend requires no node change, proven with a stub
validator. The plugin route is explicitly banned — no `kedro_great_expectations`, no
`kedro_pandera` — and (AD-9) no `great_expectations` at all. Imports stay stdlib +
`pandera` + `kedro.framework.hooks` + the in-package `a2a` seam. Pandera usage stays within
conda-forge 1.18.2 features: the version cap is a **policy statement**, not merely a pin, so
no story may depend on features above it.

**A breach raises natively and alerts on the one channel.** `DataContractViolation` is a
`RuntimeError` subclass, so it propagates to the orchestrator and halts the pipeline through
ordinary exception semantics rather than a special-cased return code. It carries a
`ContractViolation` naming the backend, the dataset, the violated rule (`PANDERA_RULE =
"pandera_schema"` — stable and named, so alerts are groupable), and bounded evidence: the
number of pandera failure cases carried is **capped**, so a wholesale schema failure cannot
produce an unbounded alert payload.

**Non-frames are skipped, not crashed on.** The frame check tests for a 2-D `.shape` plus
`.columns`, so a node output that is not a dataframe passes through a frame validator
gracefully instead of exploding inside it (a review finding, and the right call — the hook
sits on *every* node).

### References

- [Source: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md#Story-F2]
- [Source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md#§9-Story-F2]
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
| Pull request | **#93** — story(F2): data-validation hook + inline Pandera contracts (FR-10) |
| Merged | 2026-07-18 |
| Diff | 5 files, +832 / -1 |
| Test files touched | 3 |

**Commits**

- `1e122c8` story(F2): data-validation hook + inline Pandera contracts (FR-10)

**File list** *(exact, from the merged diff)*

```
  448 +     0 -  src/shared/packages/pyforge-atlas/tests/validation/test_validation_hook.py
  337 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/validation.py
   37 +     0 -  src/shared/packages/pyforge-atlas/tests/catalog/test_no_inline_io.py
   10 +     1 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/settings.py
    0 +     0 -  src/shared/packages/pyforge-atlas/tests/validation/__init__.py
```

## Dev Agent Record

### Agent Model Used

In-session BMAD agent loop (draft → 2× adversarial review → 1× independent fresh-eyes review → real-gate verify), not a `bmad-dev-story` story-file run.

### Completion Notes List

- **Impl commit `1e122c8`** — story(F2): data-validation hook + inline Pandera contracts (FR-10)
  - Adds validation.py — a VALIDATOR-AGNOSTIC AfterNodeRun validation hook. A node
  - output that violates its declared pandera contract HALTS the pipeline before ANY
  - output persists: the hook raises a native DataContractViolation from
  - after_node_run (which runs before the runner's catalog-save loop — proven on a
  - real SequentialRunner with a tracking dataset asserting saves == []), so the
  - failure propagates to Dagster (halting the run) and, on its way out, RAISES an
  - A2A alert (E1's build_alert_payload — AD-20, one channel/one schema source).
  - - Validator protocol: pandera is the shipped default; a stub second validator
  - (fixture) proves the seam is agnostic — a backend plugs in with ZERO node/hook
  - edits. Contracts live in a per-dataset registry as DATA; nodes stay pure.
  - - AD-9: the shipped hook does NOT import great_expectations at all (in-env GX
  - 1.19.0 can't be statically guaranteed to conda-forge 1.18.2 features) — GX is a
  - documented NotImplementedError boundary-adapter stub, replaced by a
  - 1.18.2-feature-only adapter when GX is pinned. kedro-great-expectations /
  - kedro-pandera plugins banned (import-ban in test_no_inline_io.py).
  - - AD-23: registered in settings.HOOKS beside ProjectHooks + AtlasObservabilityHooks
  - so kedro run AND the C1 Dagster plane both validate; a halt cleanly triggers
  - E2's on_pipeline_error (OL FAIL + span ERROR, no leak).
  - - A sink failure never masks the halt (guarded emit, then unconditional raise).
  - Reviewer fixes (both in-loop reviewers): _halt now builds the alert via a
  - defensive _build_alert that coerces evidence JSON-native + falls back on an empty
  - rule, so a third-party backend returning a set / numpy scalar / non-finite float
  - / empty rule can no longer convert the FR-10 halt into a pydantic error or drop
  - the alert. Regression test proves a hostile-evidence backend still raises
  - DataContractViolation + delivers a round-trippable alert. Shipped alert_sink
  - wiring (for F4's first real contract) recorded DW-F2-2. 645 passed (+22).

## Review Triage Log

No separate review-fix commit; findings (if any) folded into the impl commit. Full review threads on PR `#93`.

## Dev narrative — recovered from the merged record

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #93: story(F2): data-validation hook + inline Pandera contracts (FR-10)

## Deferred Work (DW ledger)

### DW-F2-1 — the Great Expectations boundary adapter (version-capped at cf 1.18.2) — DEFERRED
- source_spec: `cfe-atlas-datapipeline-kedro-migration.md` (Story F2, FR-10, AD-9)
  summary: F2 shipped the load-bearing, buildable-now half of the data-validation surface — `validation.py` as the SINGLE validation seam: a validator-agnostic `Validator` protocol (a backend REPORTS `ContractViolation`s, never halts itself, so the hook owns the raise+alert in ONE place and a new backend needs ZERO node/hook edits — AC-3), the shipped inline `PanderaValidator` (per-dataset `DataFrameSchema` registry `DEFAULT_CONTRACTS`, declared as DATA never inline in nodes), and `DataValidationHooks` registered ONCE in `settings.HOOKS` (AD-23) so EVERY entry point validates — firing in `after_node_run`, the verified kedro-1.5.0 pre-persist point (`Task._call_node_run` calls `after_node_run` with the full outputs dict BEFORE the runner save loop), raising a native `DataContractViolation` that halts before ANY output persists and, on the way out, emits an `AtlasAlert` on E1's real A2A channel (AD-20, `build_alert_payload` → injected `alert_sink` → `hand_off`/`AuthoringInbox`). The DEFERRED half is the **Great Expectations boundary adapter**: AD-9 caps GX at conda-forge **1.18.2** semantics (no ≥1.19 features), but the in-env GX is **1.19.0** and cannot be *statically guaranteed* to stay within 1.18.2-only features, so — per AD-9's explicit preference — the shipped hook path imports **NO** `great_expectations` at all. `GreatExpectationsBoundaryValidator` is a protocol-conforming STUB (its `check` raises `NotImplementedError` with this DW note) that proves the seam ACCEPTS a GX backend with zero node changes; the real adapter is deferred to an environment where GX is pinned to 1.18.2, at which point the stub is replaced by a 1.18.2-feature-only adapter and slotted into the same `validators=[...]` list — no node/hook change (the point of the seam). The `kedro-great-expectations` / `kedro-pandera` plugins stay BANNED everywhere (the hook is hand-rolled). Do NOT import GX into the shipped path or lift the 1.18.2 cap to unblock this.
  evidence: `tests/validation/test_validation_hook.py` drives a real one-node SequentialRunner pipeline with a persistence-tracking dataset and asserts the F2 behaviours: a malformed payload (PyPI frame missing `version`) HALTS via a native `DataContractViolation` with the output NOT persisted (save loop never ran), emitting an `AtlasAlert` (severity critical + rule `pandera_schema` + evidence naming the column) delivered over the real A2A channel (`hand_off` → `AuthoringInbox`, round-trip-identical); a valid payload passes AND persists (no false halt); a STUB second validator halts the SAME node with zero node edits (AC-3 validator-agnosticism), and a stub-only config proves pandera is not special; the GX boundary stub raises with the 1.18.2 DW note; `test_no_inline_io.py::test_banned_validation_plugins_nowhere` + `test_no_great_expectations_in_shipped_validation_path` pin AD-9. Edge cases proven: no registered contract → pass-through; non-frame output skips gracefully (no crash); empty-frame conformant passes / missing-column halts; a broken validator halts loudly (never silently passes bad data); the default no-op sink and a RAISING sink both never mask the halt; a multi-output node halts before ANY output persists; the default hook is deepcopy-safe (C1 translator copies `settings.HOOKS`); and co-registration with the E2 observability hook still halts order-independently. `DEFAULT_CONTRACTS` ships EMPTY (machinery + seam, nothing speculative) so the settings-armed hook can never false-halt a real run until a contract is declared. No socket is bound and no network is touched in any test (offline).

### DW-F2-2 — wire a real A2A alert_sink into the shipped validation hook (gated on F4's first contract)
- source_spec: `f2-data-validation-hook-inline-pandera-contracts.md`
  summary: F2's `settings.HOOKS` constructs `DataValidationHooks()` with NO `alert_sink`, so a
    production contract violation halts correctly (data never persists) and BUILDS the AtlasAlert
    (carried on the raised `DataContractViolation.alert`) but does NOT DELIVER it on the A2A
    channel — delivery is proven only in the gate via an injected sink. This is MOOT today
    (`DEFAULT_CONTRACTS` is empty — no violation can fire), but the moment F4 registers the first
    real pandera contract, a production halt would drop the AD-20 alert. Wiring an offline-safe
    default sink (e.g. an AuthoringInbox-backed hand_off, NOT a networked sink — that would break
    the AD offline-import guarantee) into `settings.HOOKS` is therefore a GATING step of F4 (its
    ComplianceReport/policy-breach path raises "identical failure semantics to an FR-10
    violation"). Reviewer-A S1.
  evidence: `DataValidationHooks.__init__(alert_sink=None)` → `_halt` skips delivery when
    `_sink is None`; the raised exception carries `.alert`, so nothing is lost at the raise site,
    only unconsumed. Both reviewers flagged; the _build_alert robustness fix (JSON-native evidence
    + rule fallback) landed in F2 so a real sink can't be crashed by a third-party backend.
