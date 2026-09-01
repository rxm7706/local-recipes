---
doc_type: sprint-change-proposal
project_name: pyforge-marshal
date: 2026-09-01
trigger: 'Epic 28 dispatch campaign — live incidents + code-first hotfixes ahead of story specs'
scope: moderate
status: approved
mode: brownfield-catch-up
artifacts_changed:
  - docs/dreams/pyforge-marshal.md
  - docs/dreams/marshal-token-economy.md
  - planning-artifacts/fleet-drain-queue.yaml
  - planning-artifacts/specs/spec-28-1-the-context-policy-block-rendered-once-for-both-engines.md
  - planning-artifacts/specs/spec-28-4-savings-telemetry-in-journals-and-status.md
  - planning-artifacts/specs/spec-28-8-derived-context-recomputes-only-on-source-change.md
  - planning-artifacts/specs/spec-28-13-sanctioned-retry-after-an-operator-initiated-stop.md
  - planning-artifacts/specs/spec-22-7-fleet-wide-drain-is-a-marshal-orchestrated-mode.md
  - planning-artifacts/deferred-work-ledger.md
gates_to_regenerate: []
---

# Sprint Change Proposal — dispatch autonomy hotfixes (2026-09-01)

## Section 1 — Issue Summary

During the Epic 28 fleet-drain campaign (Stories 28.1–28.15), marshal dispatch
supervisors and fleet drain exposed **autonomy gaps** that required operator
intervention: verified stories stuck without auto-land (sidecar payloads >4 KiB),
harness quota/auth failures permanently blocking drain (`MRS-DRAIN-005`), Claude
spend-limit exits with zero git progress, uncommitted WIP breaking verify, power-loss
ledger rollback re-dispatching landed stories, and no per-invocation `--harness`
override.

**Code-first hotfixes** landed (commit `b04a30c6b0` sidecar auto-land; follow-on
bundle in the same session for harness failover, transient block classification,
supervisor stuck-land retry, pre-verify WIP commit, campaign merge reconciliation,
warn-mode verify widen, `--harness` flag). The **Dream → PRD → spec chain lagged**
the implementation — this SCP catches artifacts up without falsely marking
Stories 28.13/28.14 as fully shipped.

**Orchestrator state (2026-09-01T06:25Z):** no `dispatch_supervisor`,
`dispatch_fleet_supervisor`, or `bmad-loop` processes running; no fleet campaign
advisory lock. Story **28.7** last dispatch (`pyforge-marshal-20260901T054148193Z-62226fac`)
ended `failed` (~60s, harness quota, zero git progress) — safe to re-dispatch after
hotfixes merge.

## Section 2 — Impact Analysis

| Hotfix | Artifact home | Status |
|--------|---------------|--------|
| Sidecar fold + auto-land verdict | AD-30 / Story 3.2 journal read-side; Story 22.4 land | **Shipped** (`b04a30c6b0`) |
| Harness profile failover + `--harness` | Story 22.8 (partial) | **Shipped** (interim) |
| Transient vs terminal `MRS-DRAIN-005` | Story 28.13 (partial — not SIGTERM journal) | **Interim** |
| `git fetch origin` + stuck-land retry | Story 22.4 supervisor (partial) | **Shipped** (interim) |
| Pre-verify WIP commit | Story 22.3 verify (partial) | **Shipped** (interim) |
| Warn-mode scope widen at verify | Story 28.15 (partial; 28.14 still authoritative) | **Shipped** (interim) |
| Campaign blocked-map reconciliation | Story 22.7 | **Shipped** |
| `--stories` spec preflight | Story 22.11 | **Shipped** |
| Zombie supervisor exit | Story 3.4 supervisor | **Shipped** (interim) |

**PRD impact:** none structural — hotfixes operationalize existing CAP-2/CAP-7 intent.
Optional future FR note under CAP-2: "journal read-side resolves AD-30 sidecars."

**Epic 28 remaining queue** (after 28.4 lands on main, confirmed `done` in ledger):

`28.7 → 28.9 → 28.5 → 28.6 → 28.10 → 28.11 → 28.12 → 28.13`

Dependencies satisfied: 28.3/28.4/28.8/28.14/28.15 are `done`; 28.9 deps 28.8;
28.6 deps 28.4; 28.11 deps 28.10.

**Spec status drift fixed:** `spec-28-1`, `spec-28-4`, `spec-28-8` frontmatter
`status:` aligned to tracked ledger (`done`).

**Stories needing no spec rewrite before dispatch:** 28.7, 28.9, 28.5, 28.6, 28.10,
28.11, 28.12 — contracts remain `ready-for-dev` and match epics.md ACs.

## Section 3 — Recommended Approach

**Brownfield catch-up, not replan.** Do not mint Epic 29. Record hotfixes in SCP +
deferred-work; keep 28.13/28.14 as backlog stories for the *sanctioned* mechanisms.
Resume drain only after hotfix commit is on `main` and `fleet-drain-queue.yaml`
lists the eight remaining keys.

- **Effort:** doc-only + one code commit (hotfix bundle).
- **Risk:** low — interim transient-block logic must not be mistaken for 28.13's
  SIGTERM journal taxonomy (deferred-work entry added).
- **Timeline:** drain paused until this SCP merges; then
  `marshal factory dispatch pyforge-marshal --stories <queue> --harness cursor,claude`
  or fleet drain with updated queue file.

## Section 4 — Detailed Change Proposals

1. **`fleet-drain-queue.yaml`** — replace pyforge-marshal `order_overrides` with the
   eight remaining story keys in operator-approved order (drop shipped 28.1–28.4,
   28.8, 28.14, 28.15).
2. **Dream addenda** — `docs/dreams/pyforge-marshal.md` + `marshal-token-economy.md`:
   "dispatch autonomy hardening 2026-09-01" paragraph under What is real.
3. **Story specs** — status sync for shipped 28.1/28.4/28.8; operational note on
   28.13 for interim hotfix; optional cross-ref on 22.7.
4. **`deferred-work-ledger.md`** — three new entries for gaps vs 28.13, 28.14, full
   supervisor exit semantics.

## Section 5 — Handoff

- **Resume drain:** after hotfix PR merges to `main`, run one cycle with
  `--once` to validate preflight, then supervised drain or `--stories` chain.
- **Do not re-dispatch 28.7** until hotfix code is on the worktree baseline
  (`origin/main` includes sidecar + hotfix bundle).
- **28.13 remains backlog** — finish SIGTERM journal class + diff surfacing per spec ACs.
