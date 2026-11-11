---
title: '32.1: AGENTS.md states the writer lock and the seed as the operator ruled them'
type: 'chore'
created: '2026-11-10'
status: 'backlog'
difficulty: 'medium'
story: 32-1-agents-md-states-the-writer-lock-and-the-seed-as-the-operator-ruled-them
spec: spec-pyforge-scribe
surface:
  - AGENTS.md
  - docs/reference/agent-instruction-notes.md
  - src/shared/packages/pyforge-scribe/tests/meta/test_cutover_wording.py
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-32-1-agents-md-states-the-writer-lock-and-the-seed-as-the-operator-ruled-them.md
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - .claude/skills/bmad-project-context/SKILL.md
  - src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py
  - docs/reference/agent-instruction-notes.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Ruling 1 of 2026-11-10 (`docs/dreams/pyforge-unifying-strategy.md` § Realization log) says A writes every
Dream, Frame, Spec and the capability ledger until the flip, B reads A at a pinned SHA, and the seed is Dream plus
memlog with a Frame as a pointer; the second addendum (item 7) adds that the seed includes `archive/**/.memlog.md`,
with no backfill. `AGENTS.md` still says B is rebuilt from Frame + Spec, that the writer lock and the
mode table are B's, and that A pins B's SHA (audit MUST 8). Those lines sit inside the `bmad:context` block, which only
a `bmad-project-context` refresh may change. The recipe count outside the block is stale (NICE N1).

**Approach:** Run `bmad-project-context` in refresh mode, headless, with the 2026-11-10 rulings as the approved input:
the operator gave per-PR approval (b) on 2026-11-10 (second addendum, item 7), and the complete proposed block is shown
in the PR. The refresh re-verifies the whole block and stamps its provenance line with the refresh date and SHA.

- Line 10 names the seed as Dream plus memlog, archived memlogs (`archive/**/.memlog.md`) included with no backfill
  (second addendum, item 7); the Policy lines say A writes every Dream, Frame, Spec and capability-ledger row until
  `pyforge.cutover_root` flips, B reads A at a pinned SHA, a Frame is a pointer, and the mode table is
  `docs/foundry/capability-ledger.yaml`; the `governance-currency` ignore markers around them go if no B-only path
  remains.
- The refresh also applies the text the operator accepted on 2026-11-05 (RUL-A-F3: "a lasting `src/shared/packages/`
  package (a new package directory; files in an existing station package are not new paths)").
- Outside the block, the recipe count is re-measured with its command and date, or dropped.
- `docs/reference/agent-instruction-notes.md` § *Moved from AGENTS.md* gains a dated 2026-11-10 entry quoting the
  superseded sentences and the ruling.
- `tests/meta/test_cutover_wording.py` reads the block and requires five clauses: A writes until
  `pyforge.cutover_root` flips, B reads A at a pinned SHA, the seed as Dream plus memlog with `archive/**/.memlog.md`
  included, a Frame is a pointer, and the mode table `docs/foundry/capability-ledger.yaml`. It removes each required
  clause from a copy and plants each superseded clause in a copy, and asserts that exactly that clause is named (the
  shape of `test_skf_end_state_guard_names_each_broken_clause`); it carries `pytestmark = pytest.mark.live_tree`.

This story is the one writer of `AGENTS.md` before Story 31.4's late edit. It builds late: after the collected
`AGENTS.md` requests of every unit are in hand and after the stories of other units that change a fact the block
states (Notes), so the stamp certifies the tree that lands. There is no fallback: steward:S-121.4's chain-write denial
must not land while `AGENTS.md` still gives the writer lock and the seed to B.

Ledger key: `32-1-agents-md-states-the-writer-lock-and-the-seed-as-the-operator-ruled-them`.
Type / Effort / Deps: chore / M / none in this station (cross-station order in Notes).

### Living CAP citations

- `spec-pyforge-scribe` CAP-27, as amended at the 2026-11-10 mint (FR-16): the contract holds the 2026-11-10 end state,
  guarded by `test_cutover_wording.py`.

## Boundaries & Constraints

**Always:**
- Change the block only through `bmad-project-context` refresh; show the whole proposed block in the PR.
- Quote the superseded sentences in the notes file before they leave `AGENTS.md`.

**Never:**
- Do not hand-edit a line inside the `bmad:context` markers.
- Do not edit `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` or `.cursor/rules` (read: they say nothing
  about the seed or the lock).
- Do not write the `Surface reconcile` event for `AGENTS.md` (Story 31.4 does).

</intent-contract>

## Acceptance Criteria

- **AC1 — The block states the ruled writer, seed and mode table, and none of the superseded clauses.**
  `python3 -c "import sys;t=open('AGENTS.md').read();b=t[t.index('<!-- bmad:context -->'):t.index('<!-- /bmad:context -->')];need=['Dream plus memlog','archive/**/.memlog.md','a Frame is a pointer','pinned SHA','`pyforge.cutover_root` flips','docs/foundry/capability-ledger.yaml'];gone=['Frame + Spec','are B\'s','A pins B\'s SHA','The table is B\'s'];miss=[n for n in need if n not in b];left=[g for g in gone if g in b];print(miss,left);sys.exit(1 if miss or left else 0)"`
  exits 0 and prints `[] []`.
- **AC2 — The old seed is gone from the whole file.** `git grep -n 'Frame + Spec' -- AGENTS.md` exits 1 (no match).
- **AC3 — The block was refreshed, not hand-edited.**
  `grep -cE '^<!-- Verified 2026-(11-(1[0-9]|2[0-9]|30)|12-[0-9]{2}) against [0-9a-f]{10}' AGENTS.md` prints 1.
- **AC4 — The stale recipe count is gone.** `git grep -n '1,926 recipes' -- AGENTS.md` exits 1 (no match).
- **AC5 — The accepted RUL-A-F3 text landed.** `grep -c 'files in an existing station package are not new paths' AGENTS.md` prints 1.
- **AC6 — The superseded sentences are kept under the ruling's date.** `grep -c '2026-11-10' docs/reference/agent-instruction-notes.md` prints 1 or more.
- **AC7 — Pointer files say nothing about the seed or the lock.**
  `git grep -nE 'Frame|writer lock' -- CLAUDE.md GEMINI.md .github/copilot-instructions.md .cursorrules .cursor/rules` exits 1 (no match).
- **AC8 — The wording guard and the parity suite pass.**
  `PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/meta/test_cutover_wording.py src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py -q` exits 0.
- **AC9 — Every path `AGENTS.md` names resolves.** `pixi run --frozen -e pyforge-guild governance-currency` exits 0.

## Binding

- Parent capability: `spec-pyforge-scribe` CAP-27 (amended 2026-11-10); FR-16.
- Dream: `docs/dreams/pyforge-scribe.md` § Realization log, the 2026-11-10 (cutover readiness) entry.
- Epic: Epic 32. Ledger key `32-1-agents-md-states-the-writer-lock-and-the-seed-as-the-operator-ruled-them`, minted
  `backlog` (not blocked: per-PR approval b was given 2026-11-10).
- Deps: none in this station. Wave BUILD-1 by the plan, built late by the order in Notes.

## Notes

- Cross-station order: this story builds after steward:S-120.3 (Epic 44, the epic bindings and CHAIN-STANDARD say
  what is true, including section 0's Frame row), steward:S-121.2 (`steward cutover` plans the ledger; `apply` and the
  move-manifest form of `plan` retire), steward:S-121.4 (the chain-write session denial), steward:S-124.1 (the
  station test tasks split, which depends on 121.4), and marshal:S-117.2 (core-kit's one function for the root of
  record, in `pyforge.core.cutover_root`). steward:S-121.4 builds before this story, but the PR does not close until
  this story's block lands, because 121.4's denial must not ship with the old block.
- Closes audit MUST 8 and NICE N1, and DW-scribe-egm-2026-11-05-3 (the RUL-A-F3 text waited for this refresh; Story
  31.3 writes the closure).
- `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` and `.cursor/rules` were read at the plan and need no
  edit.

## Spec Change Log

- 2026-11-10: minted with Epic 32 at the cutover-readiness mint; status `backlog`, not `blocked`, because the operator
  gave per-PR approval (b) the same day.
- 2026-11-10 (mint fix pass, independent review): the ruled seed includes `archive/**/.memlog.md` with no backfill
  (second addendum, item 7). The Approach's line-10 bullet, AC1's need-list and the clauses `test_cutover_wording.py`
  requires now carry it, and CAP-27 took the matching amendment (memlog, rendered by script). The cross-station
  note now says steward:S-121.4 builds before this story and the PR closes only once this story's block lands.
