---
title: Build League and Balanced Product Scorecard
type: dream
owner: steward
status: specified
---

# Build League and Balanced Product Scorecard

## The Dream

The estate optimizes to **published** measures. Build League and the Balanced Product Scorecard
are operating-model faces (Unifying Strategy Q5, 2026-08-24): we know the rules, and unpublished
metrics do not steer work. Herald (narrative), Atlas (metrics), Marshal (velocity), and Doctor
(SLO burn) consume those rules later. Steward discovery already has owner / `work_class` for the
denominator.

## What it looks like when real

- A published measure set covering **human, agent, and team** dimensions.
- Rules consistent with Q1–Q4: spec coverage, promotion class, Golden Path, Warden-gated
  change, owner on 03.
- A board that is **not** a Canopy CAP — sibling to `pyforge-unifying-strategy`, never CAP-18
  (CAP-18 is hooks in `pyforge-core`).

## What is real

Q5 is **in** the operating model. WFT named the faces and defined no metrics. The operator
scoped 2026-08-24: **scorecard draft is later**; no first-cut measure set in this pass.

## Constraints

- **Never** invent metrics or optimize to unpublished ones.
- **Never** score 01/02 work against 5-tier completeness.
- **Never** treat a Jira key as a quality signal.
- **Never** a scorecard UI capability in the Unifying Strategy chain.

## Open question for the Spec

Answered 2026-09-15. Recorded in § *Operator rulings* below.

1. **operator-measure-set** — which already-counted signals are published, and
   how do we add or retire them without inventing a score?

## Operator rulings (accepted 2026-09-15)

Operator approved the session menu (rows 1–8) and required the catalog to be
**configurable**: each measure can be on, off, or archived; a new source is
an add; a dead source is archived (id kept, never reused). No weights. No
league total. No dashboard in this first epic.

**Human**
1. `warden-verdict` — Warden rung on the PR (Q8 stays the gate).
2. `owner-work-class` — steward discovery `owner` + `work_class` on **03** work.

**Agent**
3. `gate-record-outcomes` — `gate-record.json` command pass/fail per story.
4. `journal-timing` — `journal.json` run/phase timing.
5. `run-cost-usd` — per-run `total_cost_usd`.

**Team**
6. `ledger-throughput` — stories moving to `done`.
7. `detector-pass-fail` — detector / `detectors-ci` pass/fail.
8. `five-tier-completeness` — 8×5 ladder **only** on 03 work. Never 01/02.

States: **on** (may steer), **off** (named, not steering), **archived**
(retired; must not steer; id reserved). First cut: all eight **on**. A new
row starts **off** until the operator flips it. Tables: Spec companion
`measure-catalog.md`.

Do not invent composites. Do not treat a Jira key as quality. Do not flip
Epic 44 `blocked` keys. Hub Outcome Guards **read** this catalog later;
they are not this epic.

## Non-goals

- A dashboard or league table in this first epic.
- Replacing Warden as the PR quality gate (Q8).
- Inventing weights or a single composite score.
- Implementing Hub Outcome Guards here.

## Realization log

- **2026-08-25** — Sibling Dream parked so Q5 is not an unbounded open question on the Canopy
  SPEC. Chain: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-build-league-scorecard/`
  (`status: draft`). Measures remain unpublished until the operator drafts them.
- **2026-09-09** — **Fleet readiness pass** (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, row stA-B5 / § C13/C14). Still correctly parked; the measure set stays the operator's. Proposed unblocking move that publishes no metric and violates no Never: a **measure inventory** — a read-only enumeration of every signal the estate already counts, with `file:line` per source (five-tier completeness 8×5 at `five_tier.py:17-33`, the ~30 detector pass/fail vector, ledger throughput, `gate-record.json` per-story command outcomes, `journal.json` run/phase timing, Warden verdict rungs, `driver.py:198`'s per-run `total_cost_usd`, steward discovery's `owner`/`work_class`) — so the operator selects rather than invents. Noted: [`intelligence-hub.md`](intelligence-hub.md)'s **Outcome** Guard category is the one category the repo lacks entirely and is blocked on this Dream, which puts a parked Dream on a second Dream's critical path.
- **2026-09-15** — Operator approved the eight already-counted signals as the
  first published set, with on/off/archived config and add/archive of sources.
  Spec `ready`. Steward Epic **62** (62.1–62.3 `backlog`) is the marshal
  dispatch home. Dream `dreamt` → `specified`. Q5 on
  [[pyforge-unifying-strategy]] cites this catalog.
