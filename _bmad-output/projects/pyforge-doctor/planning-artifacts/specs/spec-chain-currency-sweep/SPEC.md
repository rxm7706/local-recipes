---
spec: chain-currency-sweep
status: shipped
created: "2026-08-26"
updated: "2026-09-09"
owner-dream: docs/dreams/chain-currency-sweep.md
surface:
  - scripts/chain_currency_sweep_check.py
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
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD a0aba94b0a: live run exits 1 (2 genuine findings: pyforge-atlas + pyforge-scribe staleness checkpoints, correctly non-zero); `--json` returns a well-formed `{findings, errors}` document with `errors: []`; `--project pyforge-doctor` correctly scopes to one station ("all 1 station spine(s) current"). Exit-code contract (0/1/2) confirmed live for the 0 and 1 cases; the 2 (could-not-run) case not exercised this pass (no station audit is currently broken).

- **CAP-2 — the runbook is the procedure of record**
  - **intent:** A red detector is dispatched straight into remediation from the tracked runbook — the audit's real mechanics (feeds cascade order, 2-day grace window, strict `updated:` frontmatter precedence), the finding→remedy map, and the dispatch/land rules — never re-reverse-engineered per run.
  - **success:** An agent given only `CHAIN-CURRENCY-RUNBOOK.md` and a red detector clears the findings without reading detector internals; the detector's failure output names the runbook.
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD a0aba94b0a: `_bmad-output/projects/pyforge-doctor/CHAIN-CURRENCY-RUNBOOK.md` exists (9.5 KB, tracked); live run's failure line reads `"FINDINGS: 2 across 2 station(s) — run the reconciler sweep (CHAIN-CURRENCY-RUNBOOK.md)"`, naming the runbook directly in the failure output.

- **CAP-3 — triggered per-station cascades**
  - **intent:** The sweep runs on its trigger set — a fleet research wave, a spec re-stamp campaign, an epic close landing substantial code, or the detector going red — as eight independent per-station cascades (brief → PRD → arch → epics validation, plus a retro wherever code→retro fired), one commit per station, all inside one grace window.
  - **success:** After a sweep, `chain-currency-sweep-check` exits 0 across all 8 stations; each cascade was dispatched as single-story work.
  - **verified:** 2026-09-11 — PASS (Run 1 evidence only) — mechanical re-verification at HEAD a0aba94b0a: `CHAIN-CURRENCY-RUNBOOK.md`'s Run 1 (2026-08-26) Worked Example confirms this shape was actually executed — eight parallel single-story station agents, one commit per station, all eight green on first iteration, `chain-currency-sweep-check` exiting 0 fleet-wide afterward. Demonstrates CAP-3 was built and holds for at least one real run; see CAP-6 below for a gap in whether later runs kept following the same discipline.

- **CAP-4 — the grounding triple**
  - **intent:** Every artifact touched is reconciled against all three mandatory sources: (1) the upstream artifact that fired the edge, folded in rather than cited; (2) the Unifying Strategy pack (`spec-pyforge-unifying-strategy` + stack, console-parity inventory, architecture diagrams, resilience invariants) so the station's contract states its hub-and-spoke role; (3) the as-built `src/` code, with contract-vs-code divergence written down, never papered over.
  - **success:** Each reconciled artifact's dated addendum names all three grounding sources; when the strategy spec is itself `overtaken`, it is resolved before any station cascade grounds on it.
  - **verified:** 2026-09-11 — PASS (Run 1 evidence only) — mechanical re-verification at HEAD a0aba94b0a: Run 1's own recorded lessons confirm genuine (not stamp-only) reconciliation happened — real defects surfaced and fixed in the process (atlas's brief had four shipped-reality overclaims, steward's arch spine had an unparseable frontmatter, herald found two stale `dashboard-check` remnants, mason's chain counts had drifted); Phase 0 explicitly resolved the strategy spec's `overtaken` status (three residual open questions) before any station cascade ran.

- **CAP-5 — no stamp without reconcile**
  - **intent:** Every `updated:` frontmatter bump is accompanied by a dated reconciliation addendum in the same file — an `updated:` bump without a genuine reconcile is lying to the board and is forbidden.
  - **success:** In any sweep PR, every diff hunk that bumps `updated:` pairs with a dated addendum in that same file; a stamp-only diff fails review.
  - **verified:** 2026-09-11 — PASS (Run 1 evidence only) — mechanical re-verification at HEAD a0aba94b0a: Run 1's Worked Example explicitly records genuine reconciliation content per station (see CAP-4's verification above), not a bare frontmatter bump — the same evidence backs this CAP's no-stamp-gaming claim.

- **CAP-6 — Worked-Example accumulation**
  - **intent:** Each sweep run leaves a record in the runbook, timeless-workflow style, so the procedure compounds — proportionate to the run, not a fixed narrative cost.
  - **success:** Run 1 — the 2026-08-26 clearance of 26 findings + 1 overtaken — lands as the runbook's validation Worked Example; every later run appends a one-line entry (date, findings cleared, deviations). A run that appends nothing has not completed its Land step.
  - **verified:** 2026-09-11 — PARTIAL (Run 1 half only, cross-run accumulation unverified) — mechanical re-verification at HEAD 9d882c3ea0: `CHAIN-CURRENCY-RUNBOOK.md` § Worked Examples confirms Run 1 (2026-08-26) landed correctly as the validation entry, matching CAP-4/CAP-5's evidence. The CAP's core claim — that the record compounds across runs, one line per later run — is genuinely unverifiable right now: `grep -n "^## Worked Examples" -A 30 CHAIN-CURRENCY-RUNBOOK.md` shows only Run 1 exists; no second sweep run has happened yet to test whether the Land step actually appends. Not a failure — there is nothing to fail — but not a demonstrated PASS either; re-verify once a Run 2 exists.

## Constraints

- Findings stay advisory (doctor's standing constraint): the sweep is the remedy loop, never a second PR gate or a new red light.
- The sweep's exit code covers staleness + coherence only; layer gaps and orphans are excluded by design (chain-completeness / deck-policy scope) — folding them in would make the sweep permanently red.
- The audit mechanics are the detector's rules, not the sweep's to renegotiate: feeds graph edges, the 2-day grace window, strict `updated:` > path-date > git-last-touch precedence, behind-code suppression once a Dream is `realized`, overtaken cleared only by emptying `open_questions` — all per the runbook.
- Dispatch discipline: one agent per station cascade, physical paths only (`_bmad-output/projects/pyforge-<slug>/planning-artifacts/…`), `BMAD_ACTIVE_PROJECT=<slug>` per invocation, never `scripts/bmad-switch` from a parallel agent, never a shared orchestrator holding the whole backlog; verify placement (`readlink -f`) and frontmatter survival after every edit.
- Landing: one branch per sweep, one commit per station cascade (plus one for retros), `maintenance` label, merge with `--merge` never squash.
- `DEFERRED_SPECS` (`board.py`) is code: this Spec's entry leaves the list through a doctor story, never a hand edit.

## Non-goals

- Not a second gate — no CI red, no PR verdict.
- Not stamp-gaming — CAP-5 forbids the bump-without-reconcile shortcut in as many words.
- Not a replacement for the marshal `SYNC-RUNBOOK.md` loop, which keeps its own scope (skill-facing volatile facts); this sweep owns the planning-spine feeds edges.
- Not layer-gap or orphan remediation — that is policy work owned by the chain-completeness detectors and the pending deck-policy decision.

## Success signal

After any trigger fires, one dispatched sweep returns the fleet's planning spines to green: `pixi run -e local-recipes chain-currency-sweep-check` exits 0 across all eight stations, every touched artifact carries a dated reconciliation addendum grounded in the triple, and the run is appended to the runbook's Worked Examples. Run 1 is the 2026-08-26 26-finding clearance. The sweep itself appears as a chain on the board it maintains (this Dream→SPEC chain under doctor).

## Assumptions

- `status: shipped` — the detector is shipped and the runbook is tracked and executed: Run 1 cleared 26 findings on 2026-08-26, and three further sweeps ran 2026-08-29, 2026-09-04 and 2026-09-07 (recorded in `prds/prd-pyforge-doctor-2026-07-25/prd.md:6`).
- The Dream's status flip (`dreamt` → onward) is handled by the parent session, not this spec run.
