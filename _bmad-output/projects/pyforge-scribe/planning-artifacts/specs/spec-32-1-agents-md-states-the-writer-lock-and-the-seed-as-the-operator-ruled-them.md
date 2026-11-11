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

## Auto Run Result

Built 2026-11-11 on `cutover-readiness-2026-11-10` (wave BUILD-1), awaiting independent review; frontmatter status
unchanged (the ledger close promotes it).

### The refresh

`bmad-project-context` ran in refresh mode, headless, on the operator's per-PR approval (b) of 2026-11-10 (second
addendum, item 7), with the 2026-11-10 rulings as the rules brought. No custom layer exists
(`_bmad/scripts/resolve_customization.py` returned empty arrays). Step 1 as a diff: the provenance line read
`2026-11-01 against 03a7aff5d9`; `git log --diff-filter=DR --name-only 03a7aff5d9..72f3e3158f` deletes or renames
recipe files and two doctor and warden test fixtures, none named in the block. Every path the block names was
re-checked against the tree; the misses are the foundry target tree (under its ignore marker), relative or
placeholder paths, a runtime log, gitignored `.claude/data/conda-forge-expert/`, and the two B paths this refresh
removes. The block is stamped `Verified 2026-11-11 against 72f3e3158f`. The complete block is `AGENTS.md` between
the `bmad:context` markers at the branch head; approval (b) asks the PR to show it whole.

### Settled ledger

| Entry | Decision | Reason and evidence |
|---|---|---|
| Orientation, "its engines rebuilt from Frame + Spec" | rewrite | Ruling 1 and the second addendum, item 7: the seed is Dream plus memlog, `archive/**/.memlog.md` included with no backfill, and a Frame is a pointer. The rest of the paragraph is retained word for word. |
| Policy, writer-lock line | rewrite | Ruling 1 reverses who writes: A writes every Dream, Frame, Spec and capability-ledger row until `pyforge.cutover_root` flips, and B reads A at a pinned SHA. Lost parts, deleted on ground 1 (incorrect since the ruling): "foundry-product Dreams, Frames, Spec five-fields ... are B's — never mint a second one here" and "A pins B's SHA (B's `docs/foundry/PIN.md`)". Kept: kernel package commits stay on B (`spec-foundry-regenerate-not-fold` Constraints) and A invents the factory, CFE and recipes until a foundry CFE exists. |
| Policy, mode line, "The table is B's `docs/foundry/modes.md`" | rewrite | Ground 1: the file does not exist on A and the ruled mode table is A's `docs/foundry/capability-ledger.yaml`; the rules are `spec-foundry-capability-ledger`'s `modes.md`. The four modes and "never `move`" are retained. |
| The ignore markers around those two lines | delete | Ground 1: no B-only path remains in them, so `governance-currency` reads them in full. |
| The foundry-tree line, "never mint a lasting `src/shared/packages/` path" | rewrite | RUL-A-F3, the operator's accepted text of 2026-11-05 (`DW-scribe-egm-2026-11-05-3`). The narrowing (a new file in an existing station package is no longer covered) is a deletion on ground 4, approved by that acceptance, and on ground 3: read literally the old line contradicted the workspace-package conventions. |
| That line's ignore-marker reason | rewrite | Ground 1: `.claude/skills/pyforge-mason/` resolves since its 2026-10-05 compile; the marker stays for `src/packages/`. |
| Provenance line | rewrite | Refresh date and verified SHA. |
| Outside the block, § Dates: "1,926 recipes ... (57 as `/v{{ version }}`)" | rewrite | Ground 1, stale: on 2026-11-11 a `git grep` over tracked recipe files counted 10,521 of 11,000 with a version-templated URL, 609 in the `/v` form. The count is dropped and the rule kept, since a typed count goes stale with every recipe. |
| Every other line of the block | retain | Paths re-checked; no deletion or rename since `03a7aff5d9` touches them. |

The superseded sentences are quoted under 2026-11-10 in `docs/reference/agent-instruction-notes.md` § *Moved from
AGENTS.md*. In the same file, a pre-existing dead path found by doctor's `docs-currency` scan (the archived
`spec-upstream-discovery` folder, moved 2026-10-27) now names its archive home.

Requests left for others: steward-station's lint-paragraph request (both suite halves, the package `pixi.toml`
floors) sits inside the block and can only be true after Epic 124 builds; control-plane's request (3) names
`cutover plan --regenerate` and `plan --check`, which Stories 121.2 and 121.7 have not built; the guardrail count and
the SKF row are Story 31.4's. Contradictions in other files, owned by their stories: CHAIN-STANDARD § 0's Frame row
(steward 120.3), `modes.md`'s "re-derive from Frame/Spec" (control-plane), the dossier's "rebuilt from Frame + Spec"
(herald 51.2).

### Commands run (exit codes)

- AC1 block check: exit 0, prints `[] []`.
- AC2 `git grep -n 'Frame + Spec' -- AGENTS.md`: exit 1.
- AC3 provenance grep: prints 1.
- AC4 `git grep -n '1,926 recipes' -- AGENTS.md`: exit 1.
- AC5 RUL-A-F3 grep: prints 1.
- AC6 `grep -c '2026-11-10' docs/reference/agent-instruction-notes.md`: prints 3.
- AC7 pointer-file grep: exit 1.
- AC8 `test_cutover_wording.py` (12 cases) and `test_instruction_surface_parity.py`: exit 0, 61 passed. The one warning
  is the unregistered `live_tree` marker, which Story 33.1 registers.
- AC9 `pixi run --frozen -e pyforge-guild governance-currency`: exit 0.
- The guard run against the pre-refresh `AGENTS.md` (`git show HEAD:AGENTS.md`) names all five required clauses as
  missing and all four superseded clauses as present.
- `ruff check` and `ruff format --check` on the new test: exit 0.
