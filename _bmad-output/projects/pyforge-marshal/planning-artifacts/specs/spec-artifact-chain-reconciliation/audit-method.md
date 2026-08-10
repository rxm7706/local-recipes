# Audit method — verdicts, matrices, sampling, phases

Companion to `SPEC.md` (spec-artifact-chain-reconciliation). Holds the
catalogs and schemas the kernel cites. Downstream reads both.

## Verdict enum (CAP-2, CAP-3)

| Verdict | Meaning | Evidence required |
|---|---|---|
| `STILL-VALID` | Premise holds; story buildable as written | Citation of the premise's anchor in current code |
| `ALREADY-DONE` | Delivered under another story's flag | `file:line` of the implementing code + the landing commit/PR |
| `CONTRADICTED` | An invariant hardened after authoring breaks the story | Citation of the contradicting code/convention |
| `NEEDS-RESPEC` | Intent survives, contract stale (ACs, deps, naming) | Citation of each stale element |
| `DROP` | Premise gone; recommend removal | Citation of what removed it |

`DROP` and `NEEDS-RESPEC` are recommendations — operator disposes (SPEC
constraint). A verdict row without evidence is rejected in review.

## Traceability matrix row (gate-report body)

| Claim (FR / story / AC) | Ledger status | Code reality (citation) | Verdict | Action → owning skill |
|---|---|---|---|---|

One row per claim, no prose findings. A half-audited epic is visible as
missing rows — that is the point.

## Coverage-debt row (CAP-4)

| Epic | AC | Covering test | Status |
|---|---|---|---|

`Status` ∈ `covered(test path)` / `coverage-debt`. Coverage-debt is visible
and non-gating; it is not a drift verdict.

## Done-claim sampling protocol (CAP-2/CAP-3)

- Depth: ≥3 stories per epic or 20% of the epic, whichever greater (SPEC
  assumption; deepen per station if findings warrant).
- All ACs checked on each sampled story, in code, cold — the sampler does not
  read the story's own Dev Notes / self-assessment first.
- A failed AC on a completed station raises the open demotion question at
  first occurrence; record the finding either way.

## Phase runbook

| Phase | Scope | Gate to next |
|---|---|---|
| 0 | Detector sweep baseline; 51 warns closed (atlas 24 name-then-stamp, mason 1, marshal 26 regenerate→verify→judge→stamp); dangling commits dispositioned | Six detectors + meta-suite green, zero drift-presumed |
| 1 | Backlog-truth audit: steward (4) → mason (28) → marshal (35 + blocked 8-5) | Per-station gate report landed |
| 2 | Completed-station audit at equal rigor, after Phase 1: atlas, doctor, herald, scribe, warden | Per-station gate report landed |
| 2b | Full non-station inventory (CAP-8): all 61 Dreams — status truth, chain completeness, satellite consolidation, stranded artifacts | Inventory gate report landed |
| 3 | Decomposition chains: atlas → herald → doctor → steward, each citing its landed gate report | Chain's planning artifacts landed |
| 4 | `--write-baseline`, `dashboard-gen`, board render, fleet-picture, per-station go/no-go summary | Operator resume decision |

Strictly serial through Phase 2b (operator decision); Phase 3 for a station
never precedes that station's audit landing (CAP-6).

## Two-sided repair rule (CAP-5)

The correction direction follows the verdict, and both directions are
pre-authorized (operator, 2026-08-10):

- **Artifact diverged from correct code** → rebuild the artifact through its
  owning skill (+ memlog naming paths, scoped stamp).
- **Code diverged from a still-valid contract** → correct the code via
  quick-dev with tests, then blind review.
- **Decision proven wrong by evidence** → correct through
  `bmad-correct-course`, recorded.

Every correction traces to a verdict row; a change without one is out of
contract. Nothing silent.

## Landing checklist (every audit PR)

1. Fixes via owning skills only: `bmad-correct-course` (epic/story surgery),
   `bmad-sprint-planning` + `pixi run -e local-recipes sprint-ledger-sync`
   (ledger), `bmad-document-project` / `bmad-generate-project-context`
   (arch/context), `pixi run -e local-recipes dashboard-gen` (board).
2. Memlog entry in the owning Spec naming every changed path; scoped stamp
   that spec only.
3. Blind lens-diverse parallel review: one structural hunter, one
   coverage/edge-case hunter, no shared context, neither shown the artifacts'
   self-assessment.
4. Station suite + six detectors + meta-suite green.
5. PR with `maintenance` label; merge via `--merge`, never squash.
