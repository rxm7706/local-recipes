---
title: 'Move the estate'
type: 'feature'
created: '2026-09-13'
status: 'backlog'
difficulty: heavy
story: 44.5
spec: python-foundry-cutover
surface: [".claude/skills/**", "_bmad/**", "_bmad-output/projects/**", "docs/dreams/**", "presentations/**"]
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Skills, BMAD, decks and Dreams still resolve only from
`local-recipes`. Agents and loops need the lasting root.

**Approach:** `steward cutover apply --phase 1b` moves those trees into
foundry under `skills/{stations,personas,domain}/`. Leave the CFE cell in
place for 44.6. No tracked adapters. `planning-history-scope` is already
answered (`fnd:AD-20`: Dreams + memlogs + capability ledger). Refuse to
run unless `cutover-readiness.md` P11 and P12 are green. **Do not flip
`pyforge.cutover_root`** — that remains an attended operator act after
this Story lands, with no loop running.

## Boundaries & Constraints

**Always:**
- D3: no Deps on 44.11 (win-64 / junction adapters are later).
- Installer-written `bmad-*` / `skf-*` dirs are untouched.
- CFE cell stays for 44.6.

**Never:**
- Never flip `pyforge.cutover_root` in this Story.
- Never track symlink adapters.
- Never move the CFE cell (44.6).

</intent-contract>

## Acceptance Criteria

1. Estate-authored skills live under `skills/{stations,personas,domain}/` in foundry; SKF export writes there.
2. BMAD marker and planning links are generated, never copied.
3. P11/P12 green or the Story refuses.
4. `pyforge.cutover_root` remains `local-recipes`.
5. Ledger key `44-5-move-the-estate` is the only 44.x key this Story may mark `done`.
