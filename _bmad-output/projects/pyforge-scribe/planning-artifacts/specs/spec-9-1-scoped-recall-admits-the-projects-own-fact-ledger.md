---
title: 'Scoped recall admits the project''s own fact ledger'
type: 'feature'
created: '2026-09-13'
status: 'done'
---

<intent-contract>

## Intent

`--scope <slug>` admits exactly one extra citation shape:
`presentations/<slug>/facts.yaml`. Marshal retrieve does not change argv.

## Boundaries & Constraints

**Always:** identity slug; planning-tree prefix still required for everything else.

**Never:** all of `presentations/`; nested `facts.yaml`; a `--facts` flag; alias table.

</intent-contract>

## Spec Change Log

- **2026-09-13:** implemented — `_citation_in_scope` admits
  `presentations/<scope>/facts.yaml` only. Marshal `--scope` argv unchanged.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `95f1db76aa` (2026-08-13, "Merge branch 'bmad-loop/20260813-094919-bfcb/9-1-findings-model-severity-types-remedies' into bmad-loop/202608"). Ledger row `9-1-scoped-recall-admits-the-projects-own-fact-ledger: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`, `scripts/.spec-surface-baseline.json`, `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/findings.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_seed_detect_findings.py`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `ready-for-dev` → `done` (ledger row `9-1-scoped-recall-admits-the-projects-own-fact-ledger: done`).
- `## Auto Run Result` reconstructed from git (none survived).
