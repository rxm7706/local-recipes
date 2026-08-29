---
spec: chain-currency-sweep
status: ready
created: "2026-08-26"
updated: "2026-08-26"
owner-dream: docs/dreams/chain-currency-sweep.md
surface:
  - scripts/chain_currency_sweep_check.py   # CAP-1's shipped as-built detector; ungoverned since spec creation, surfaced 2026-08-28
companions:
  - ../../../CHAIN-CURRENCY-RUNBOOK.md
sources:
  - ../../../../../../docs/dreams/chain-currency-sweep.md
open_questions: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. The source document listed in frontmatter is for traceability only.

# Chain currency sweep — planning spines re-derived on trigger, never decayed

## Why

A vision to realize on top of a proven pain: every Dream→Code chain on the board should stay current the way code stays green — by a standing loop, not by attention. Doctor's chain-layers audit (FR-150/FR-192, CAP-3) already *detects* decay — feeds edges, behind-code, overtaken — but nothing *reconciles*: the 2026-08-26 board carried 26 staleness findings across all eight station flagships and zero audit-sound chains. The marshal project already lives the answer in miniature (deterministic detector + BMAD-skill reconciler + tracked `SYNC-RUNBOOK.md`, run on trigger, re-stamped on completion); this generalizes that two-layer pattern to the fleet's planning spines as one repeatable, parameterized sweep any agent or framework can execute identically.

## Capabilities

- **CAP-1 — the sweep detector (SHIPPED)**
  - **intent:** Any agent can learn, in one command, whether the eight station planning spines are current — the per-project chain audit narrowed to the staleness + coherence checkpoints and looped across all eight station slugs.
  - **success:** `pixi run -e local-recipes chain-currency-sweep-check` (as-built: `scripts/chain_currency_sweep_check.py`, auto-discovered registry) exits 0 when all spines are current, 1 on any staleness/coherence finding, 2 when a station's audit could not run; supports `--json` and `--project <slug>`.

- **CAP-2 — the runbook is the procedure of record**
  - **intent:** A red detector is dispatched straight into remediation from the tracked runbook — the audit's real mechanics (feeds cascade order, 2-day grace window, strict `updated:` frontmatter precedence), the finding→remedy map, and the dispatch/land rules — never re-reverse-engineered per run.
  - **success:** An agent given only `CHAIN-CURRENCY-RUNBOOK.md` and a red detector clears the findings without reading detector internals; the detector's failure output names the runbook.

- **CAP-3 — triggered per-station cascades**
  - **intent:** The sweep runs on its trigger set — a fleet research wave, a spec re-stamp campaign, an epic close landing substantial code, or the detector going red — as eight independent per-station cascades (brief → PRD → arch → epics validation, plus a retro wherever code→retro fired), one commit per station, all inside one grace window.
  - **success:** After a sweep, `chain-currency-sweep-check` exits 0 across all 8 stations; each cascade was dispatched as single-story work.

- **CAP-4 — the grounding triple**
  - **intent:** Every artifact touched is reconciled against all three mandatory sources: (1) the upstream artifact that fired the edge, folded in rather than cited; (2) the Unifying Strategy pack (`spec-pyforge-unifying-strategy` + stack, console-parity inventory, architecture diagrams, resilience invariants) so the station's contract states its hub-and-spoke role; (3) the as-built `src/` code, with contract-vs-code divergence written down, never papered over.
  - **success:** Each reconciled artifact's dated addendum names all three grounding sources; when the strategy spec is itself `overtaken`, it is resolved before any station cascade grounds on it.

- **CAP-5 — no stamp without reconcile**
  - **intent:** Every `updated:` frontmatter bump is accompanied by a dated reconciliation addendum in the same file — an `updated:` bump without a genuine reconcile is lying to the board and is forbidden.
  - **success:** In any sweep PR, every diff hunk that bumps `updated:` pairs with a dated addendum in that same file; a stamp-only diff fails review.

- **CAP-6 — Worked-Example accumulation**
  - **intent:** Each sweep run appends a Worked Example (outcome, deviations, timings) to the runbook, timeless-workflow style, so the procedure compounds.
  - **success:** Run 1 — the 2026-08-26 clearance of 26 findings + 1 overtaken — lands as the runbook's first Worked Example and doubles as its validation pass; every later run appends its own.

## Constraints

- Findings stay advisory (doctor's standing constraint): the sweep is the remedy loop, never a second PR gate or a new red light.
- The sweep's exit code covers staleness + coherence only; layer gaps and orphans are excluded by design (chain-completeness / deck-policy scope) — folding them in would make the sweep permanently red.
- The audit mechanics are the detector's rules, not the sweep's to renegotiate: feeds graph edges, the 2-day grace window, strict `updated:` > path-date > git-last-touch precedence, behind-code suppression once a Dream is `realized`, overtaken cleared only by emptying `open_questions` — all per the runbook.
- Dispatch discipline: one agent per station cascade, physical paths only (`_bmad-output/projects/pyforge-<slug>/planning-artifacts/…`), `BMAD_ACTIVE_PROJECT=<slug>` per invocation, never `scripts/bmad-switch` from a parallel agent, never a shared orchestrator holding the whole backlog; verify placement (`readlink -f`) and frontmatter survival after every edit.
- Landing: one branch per sweep, one commit per station cascade (plus one for retros), `maintenance` label, merge with `--merge` never squash.

## Non-goals

- Not a second gate — no CI red, no PR verdict.
- Not stamp-gaming — CAP-5 forbids the bump-without-reconcile shortcut in as many words.
- Not a replacement for the marshal `SYNC-RUNBOOK.md` loop, which keeps its own scope (skill-facing volatile facts); this sweep owns the planning-spine feeds edges.
- Not layer-gap or orphan remediation — that is policy work owned by the chain-completeness detectors and the pending deck-policy decision.

## Success signal

After any trigger fires, one dispatched sweep returns the fleet's planning spines to green: `pixi run -e local-recipes chain-currency-sweep-check` exits 0 across all eight stations, every touched artifact carries a dated reconciliation addendum grounded in the triple, and the run is appended to the runbook's Worked Examples. Run 1 is the 2026-08-26 26-finding clearance. The sweep itself appears as a chain on the board it maintains (this Dream→SPEC chain under doctor).

## Assumptions

- `status: ready` — the detector half is shipped and the runbook is tracked; the reconciler side (Run 1, the 2026-08-26 clearance) is pending dispatch.
- The Dream's status flip (`dreamt` → onward) is handled by the parent session, not this spec run.
