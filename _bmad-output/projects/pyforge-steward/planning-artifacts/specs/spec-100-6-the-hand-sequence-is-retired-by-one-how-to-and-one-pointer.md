---
title: '100.6: The hand sequence is retired by one how-to and one pointer'
type: 'chore'
created: '2026-10-13'
status: 'ready-for-dev'
baseline_revision: '233e07909b5f7e89e49744cdeb642cdc0985b177'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/intake/estate-refresh/PLAN-2026-10-13.md
  - docs/how-to/pause-ci.md
  - docs/map.yaml
  - AGENTS.md
  - docs/reference/agent-instruction-notes.md
  - CLAUDE.md
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** The refresh is documented nowhere as one path: `pixi.toml:45-48` carried the command in three comment
generations (Story 100.1 replaces them with a pointer), `AGENTS.md` § *Policy* says only "a `pixi.toml` change
regenerates `environment.yaml` in the same PR", `docs/reference/agent-instruction-notes.md` § *PR CI gates* names the
hand steps, the library catalog's header named an LLM prompt for its floors (Story 100.3 replaces it), and the
BMAD-side runbook (`release-cadence.md` step 7, Story 100.5 points it) is the only written ritual.

**Approach:** One how-to, registered, and pointers where readers already look.

- **`docs/how-to/refresh-the-estate.md`** (Diátaxis how-to; `docs/how-to/pause-ci.md`'s shape): when a refresh is
  due (`estate plan --due`, monthly); the policy file and its hold classes and how to add or retire a hold
  (`until`); the realization register and its classes and how to add a row; the six verbs in order — `plan`,
  `refresh`, `realize`, `reconcile`, `verify`, `status` — with the operator-only `--transitive` and
  `realize --yes` and what agents may run; the station pin fan-out and what a red one means (the station's story);
  the verify tiers, `--all`, the manual rows and the per-platform confirmation; the journal and where it lives; the
  PR landing (`maintenance` label, the marshal merge subject, lock-solved ×3 plus this platform's verify); what
  the operator finishes on the branch after a dispatched run.
- **`docs/map.yaml`**: the how-to's row (`docs-map-render-test` and `docs-gen-test` stay green).
- **`AGENTS.md`**: one pointer line in § *Running and verifying* naming the how-to and `estate plan`; § *Policy*'s
  `pixi.toml` line says `environment.yaml` regenerates through `estate reconcile` (or the exporter it wraps) —
  scribe's parity meta-test and `governance-currency` stay green; no duplicated section.
- **`docs/reference/agent-instruction-notes.md`** § *PR CI gates*: points at the how-to; the hand steps become
  history under a dated line.
- **Removal.** No tracked doc outside a dated log entry carries the 28-exclude command after this story.

Ledger key: `100-6-the-hand-sequence-is-retired-by-one-how-to-and-one-pointer`.
Type / Effort / Deps: chore / S / S-100.3, S-100.4, S-100.5.

### Living CAP citations

- **`spec-pyforge-steward` CAP-167** (FR-40): the how-to and the pointers.
- **`spec-pyforge-scribe` CAP-27** (one `AGENTS.md`, pointers elsewhere): one pointer line, no restated rule.
- **Flag:** none — a chore (spec-feature-flag-governance Q1); the how-to is `docs-only`.

## Acceptance Criteria

- **AC1 — The how-to exists and is registered.** `docs/how-to/refresh-the-estate.md` covers every item in the
  Approach; `docs/map.yaml` has its row; `pixi run --frozen -e pyforge-guild docs-map-render-test` and
  `docs-gen-test` pass.
- **AC2 — Pointers, not copies.** `AGENTS.md` gains exactly one line in § *Running and verifying* and one amended
  clause in § *Policy*; the scribe parity meta-test and `governance-currency` pass; every command the how-to names
  resolves (`governance-currency`'s rule).
- **AC3 — The hand sequence is gone.** `grep -rn 'pinning-strategy latest-up --exclude' --include='*.md'
  --include='*.toml' .` matches only dated log entries (the Dream, the plan, the memlogs) and the rendered pointer's
  own text.
- **AC4 — Notes updated.** `docs/reference/agent-instruction-notes.md` § *PR CI gates* points at the how-to and
  keeps the old steps under a dated line.

## Boundaries & Constraints

- No code, no pin, no registry change; docs only.
- No second copy of a rule `AGENTS.md` already states; the how-to describes, `AGENTS.md` points.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| a how-to command naming a pixi task that does not exist | `governance-currency` reds; fix the name |
| `docs/map.yaml` row missing | `docs-map-render-test` reds |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-167 (FR-40), minted 2026-10-13.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-13 (estate refresh) entry.
- Epic: Epic 100, Stories 100.1–100.7.
- Ledger key: `100-6-the-hand-sequence-is-retired-by-one-how-to-and-one-pointer`.
- Ledger status at mint: `backlog`.
- Deps: S-100.3, S-100.4, S-100.5. Re-base `baseline_revision` to the commit where the last of them landed before
  dispatch.
- Surface: `marshal-policy.toml` `[epic_surfaces]."100"` (added with the mint).
- Minted 2026-10-13 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-guild docs-map-render-test` and `pixi run --frozen -e pyforge-guild docs-gen-test` — expected: pass (AC1).
- `pixi run --frozen -e pyforge-guild governance-currency` — expected: exit 0 (AC2).
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test -- -k instruction_surface_parity` — expected: pass (AC2; the parity meta-test).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild python scripts/spec_surface_reconcile.py` and `spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

## Spec Change Log

- 2026-10-13: minted with CAP-167 / FR-40 and Epic 100. `type: chore`, no flag. Widened the same day to document the
  realization register, `estate realize`, the fan-out, the verify tiers and the per-platform confirmation.
