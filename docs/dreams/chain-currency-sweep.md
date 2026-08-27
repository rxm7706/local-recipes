---
title: Chain currency sweep — contracts that are re-derived, not decayed
type: dream
owner: doctor
status: specified
---

# Chain currency sweep — contracts that are re-derived, not decayed

## The Dream

Every Dream→Code chain on the board stays **current the way code stays green** — not by
attention, but by a standing loop. When research moves, the brief that was built from it gets
re-derived. When a spec is re-cut, its PRD follows. When code ships, the retro closes the loop.
The Guildhall's chain audit already *detects* all of this (feeds edges, behind-code,
overtaken — doctor's chain-layers audit, FR-150/FR-192); what it detects, nothing yet
*reconciles*. The 2026-08-26 board carried 26 staleness findings across all eight station
flagships and zero audit-sound chains — every one of them a contract that quietly went out of
date while the factory's eyes were on the code.

The marshal project already lives the answer in miniature: a cheap deterministic detector plus
a BMAD-skill reconciler plus a tracked runbook (`SYNC-RUNBOOK.md`), run on trigger, re-stamped
on completion. This Dream is that two-layer pattern **generalized to the fleet's planning
spines** — one repeatable, parameterized sweep any agent (or any framework, per `AGENTS.md`)
can execute identically.

Three grounding sources, all mandatory, per artifact touched:

1. **The newer upstream artifact** that fired the feeds edge (research wave, spec re-stamp).
2. **The Unifying Strategy** (`spec-pyforge-unifying-strategy` + its companion set — stack,
   console-parity inventory, architecture diagrams, resilience invariants): every station's
   contract states its hub-and-spoke role in the Canopy estate.
3. **The as-built code** in `src/` — the contract is reconciled against what actually shipped,
   never re-derived purely from other documents. Divergence gets written down, not papered
   over.

## What it looks like when real

- A `chain-currency-sweep` detector in the auto-discovered registry: the per-project
  chain-layers audit looped across the eight station slugs, red on any finding — staleness
  surfaces every time anyone runs `detectors`, instead of when someone thinks to look.
- A tracked **runbook** (doctor project) encoding the audit's real mechanics — the feeds
  cascade order, the 2-day grace window, the strict `updated:` frontmatter precedence, the
  finding→remedy map — so a sweep is dispatched, not re-reverse-engineered.
- Each sweep run = eight independent per-station cascades (brief → PRD → arch → epics
  validation, one commit per station, inside one grace window), dispatched as single-story
  work with physical paths, never a shared orchestrator or `bmad-switch`.
- Retros land while they're cheap: any retro-reached station whose code has moved past its
  retro gets one in the same sweep.
- Worked Examples accumulate per run, timeless-workflow style. Run 1 is the 26-finding
  clearance of 2026-08-26 — which is also the runbook's validation pass.
- The sweep itself appears as a chain on the board it maintains.

## What this is not

- Not stamp-gaming: an `updated:` bump without a genuine reconcile is lying to the board; the
  runbook forbids it in as many words.
- Not a second gate: findings stay advisory (doctor's standing constraint) — the sweep is the
  remedy loop, not a new red light.
- Not a replacement for the marshal SYNC-RUNBOOK loop, which keeps its own scope (skill-facing
  volatile facts); this sweep owns the planning-spine feeds edges.

## Realization log

- **2026-08-26 — specified.** `bmad-spec` produced
  `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-chain-currency-sweep/SPEC.md`
  (status `ready`; success bound to `chain-currency-sweep-check` exit 0 across all 8 stations,
  stamp-only diffs forbidden). The detector shipped the same day
  (`scripts/chain_currency_sweep_check.py`, auto-discovered by the registry), and Run 1 — the
  26-finding clearance — executed as eight parallel per-station cascades, validating the
  runbook on its first outing.
