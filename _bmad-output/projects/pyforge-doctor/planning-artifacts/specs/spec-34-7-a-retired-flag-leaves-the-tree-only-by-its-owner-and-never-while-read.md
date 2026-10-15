---
title: '34.7: A retired flag leaves the tree only by its owner, and never while read'
type: 'feature'
created: '2026-10-15'
status: 'in-review'
baseline_revision: 'b673b9b1ee50e232bddb26ca9124bc1c225375c8'
flag-exempt: detector-or-gate   # the flag gate itself; a gated gate reports a silent green (spec-feature-flag-governance Q2 and its Constraint "a flag-OFF check is never a silent green ... gates themselves are exempt"), the rule 34.2, 34.3 and 34.5 followed
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/dreams/feature-flag-governance.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-34-2-the-flag-gate-ships-in-scripts-outside-every-station-and-runs-in-detectors-ci.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-34-6-a-flag-key-shared-by-several-done-stories-is-judged-against-the-latest-one.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-42-3-the-second-host-needs-no-flag.md
  - scripts/flag_gate_check.py
  - scripts/flag_rule.py
  - scripts/flag_inventory.py
  - tests/scripts/test_flag_gate_check.py
  - tests/scripts/test_flag_inventory.py
  - tests/scripts/test_flag_rule.py
  - docs/reference/story-spec-flag-block.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the flag gate had no path for a removed flag, and the first removal opened one from the wrong side.

- **The gap.** Q4 removes a flag 90 days after it is ON everywhere; the owning station files the removal story. CAP-2's
  "a flag key that is not in the tree" check (`flag-key-not-in-tree`, Story 34.2) reds every `done` spec whose `flag:`
  block names the key, so the first removal could not pass.
- **What herald 42.3 did.** Removing `pyforge.herald.pages_second_host` (commit `7de68be07a`), it taught
  `scripts/flag_gate_check.py` a `retires-flag:` frontmatter field (`RETIRES_FIELD`): a key some story spec declares
  retired and the tree no longer holds leaves its `done` specs unjudged. `scripts/flag_inventory.py` names such a key by
  its retiring story. The judged party changed the gate (Charter section 6), with no entry on
  `spec-feature-flag-governance`.
- **The leak.** Any story spec of any station, at any status, could declare `retires-flag: <key>`, delete the key and
  silence the check while code still called `read_boolean` on it. `read_boolean` on a missing key returns its default
  with a warning, never an error, so a left-behind reader silently reads off. The independent review proved it: a
  `backlog` spec declaring the key took the gate from exit 1 to exit 0 with a reader still in `src/`.

**Approach:** keep the declaration, count it only from the owner, and red every reader left behind.

- **The owner.** A key's owning station is its `pyforge.<station>.` prefix. A key with no station segment has the
  tree's `metadata.owner` as its owner while the tree holds it. A story spec's station is its project folder
  (`station_of`). A declaration counts only when the two match.
- **A foreign declaration** (another station's, any status) FAILs `flag-retirement-not-owner`, naming the spec and the
  key, and retires nothing: the key is judged as if it had no declaration.
- **A reader left behind.** For each key its owner retired that the tree no longer holds, the orphan check's reader
  walk runs inverted. It reads the same tracked files under `src/` and `scripts/` and skips the same non-readers.
  Each file that names the key as a whole token FAILs `flag-retired-still-read`, naming the file and the retiring spec.
  Tree mode reports it once. `--spec` on the retiring spec reports the same findings for its own keys.
- **Unchanged:** a retirement declared while the key is still in the tree changes nothing; the inventory's retired cell
  (owner retirements only now); every other finding, the rule-date baseline, the exit codes.
- `docs/reference/story-spec-flag-block.md` documents `retires-flag:`.

Ledger key: `34-7-a-retired-flag-leaves-the-tree-only-by-its-owner-and-never-while-read`.
Type / Effort / Deps: feature / S / —.

### Living CAP citations

- **Contract.** `spec-feature-flag-governance` CAP-2's retirement path (memlog decision 2026-10-15, operator ruling
  "Doctor story in this PR") and CAP-7 (the inventory names the retiring story). Doctor is the mechanism Smith (Epic
  34's relay); the Guild Spec's memlog enumerates the story, and Doctor mints no CAP or FR (the Epic 24/25/32
  precedent).
- **No flag.** A gate is exempt, `detector-or-gate` (Q2; Constraint "a flag-OFF check is never a silent green"): a
  gated gate reports a silent green when off. 34.2, 34.3 and 34.5 carry the same exemption.
- **Origin.** Herald Story 42.3 and the independent review of commit `7de68be07a` (its blocker and first should-fix).

## Acceptance Criteria

- Given a `done` spec of station T flagging key `pyforge.test.k`, the key gone from the tree, and a story spec of
  `pyforge-test` (any status) declaring `retires-flag: pyforge.test.k`, with no reader naming the key When the gate runs
  in tree mode Then it exits 0 with no finding, and `--spec` on either spec reads `pass`.
- Given the same tree with a reader under `src/` or `scripts/` that names the key When the gate runs Then each such
  file is one `flag-retired-still-read` FAIL naming the file, the key and the retiring spec. A test file, a `*.md`, and
  a file naming only a longer key that starts with it are not readers. `--spec` on the retiring spec reads `red` with
  the same findings.
- Given the declaration in a story spec of another station, at `backlog` or `done` When the gate runs Then it FAILs
  `flag-retirement-not-owner` naming that spec and the key's owning station. The `done` spec is red
  `flag-key-not-in-tree` (and its two-state findings) as if no retirement existed. `--spec` on the declaring spec reads
  `red`.
- Given a foreign declaration and the owner's together, with a reader left When the gate runs Then the reader is
  `flag-retired-still-read` and the foreign spec is `flag-retirement-not-owner`.
- Given an owner's or a foreign declaration on a key the tree still holds When the gate runs Then the key, its readers
  and its `done` spec are judged as before; only a foreign declaration adds `flag-retirement-not-owner`.
- Given a key with no station segment that the tree holds with `metadata.owner: test` When `pyforge-test` declares it
  Then that is the owner's. Once the key leaves the tree, nothing names an owner, and a declaration reds
  `flag-retirement-not-owner`, naming the owner unknown.
- Given the inventory When a foreign station declares the retirement Then the row reads `none (key <key> not in
  tree)`. When the owner declares it Then the row reads `none (retired by <story>)` (Story 42.3's case, unchanged).
- Given the live tree (herald 42.3 retires `pyforge.herald.pages_second_host`; no reader names it) When `pixi run -e
  pyforge-guild flag-gate-check` runs Then it exits 0, and `flag-inventory` writes the herald report unchanged but for
  its SHA line.

## Boundaries & Constraints

**Always:**
- Fix it where the behaviour lives: `scripts/flag_gate_check.py` (`owning_station`, `declared_by_owner`,
  `retired_keys`, `judge_retirements`, `reader_files`, `judge_retired_reads`, wired into `judge_one`, `judge_tree` and
  `run_spec`). `scripts/flag_inventory.py` changes only its `flag_cell` docstring: its retired map is the gate's.
- Reuse the reader walk the orphan check uses (`READER_ROOTS`, `_list_files`, `_is_reader_candidate`).
- Keep the gate naming no live flag key (`test_the_gate_holds_no_copy_of_the_exemption_list_and_names_no_live_key`).
- Add `retires-flag:` to `docs/reference/story-spec-flag-block.md`, with a third YAML example (a retiring story).
  `tests/scripts/test_flag_rule.py` checks that every example on that page classifies as written, so it
  learns the third.
- Regenerate doctor's `planning-artifacts/test-architecture.md`
  (`python _bmad/scripts/bmad_tea_playwright.py --project pyforge-doctor`) so its Story Coverage Matrix names 34.7:
  `tea-playwright-check` reds an epic story id the matrix lacks.

**Never:**
- Never import a `pyforge.<station>` module into the gate (Charter section 6, the Story 34.2 meta-test).
- Never edit herald 42.3's `retires-flag:` line, `flags.json`, `flag-overlays.json` or the rule-date baseline.
- Never read git history to find an owner: a fixture tree without git judges the same way.
- Never weaken an existing test. Herald 42.3's two gate tests move their retiring spec into the owning station's folder
  and keep every assertion.

## I/O & Edge-Case Matrix

| Declaration of `retires-flag: K` | K in the tree | Reader naming K | Findings |
|---|---|---|---|
| owner, any status | no | none | none; a `done` spec naming K is history |
| owner | no | `src/pkg/host.py`, `scripts/export_host.py` | `flag-retired-still-read` per file |
| owner | no | only `tests/`, `*.md`, or a longer key `K_two` | none |
| another station, `backlog` or `done` | no | any | `flag-retirement-not-owner` on that spec; the `done` spec: `flag-key-not-in-tree` and its two-state findings |
| another station plus the owner | no | `src/pkg/host.py` | `flag-retired-still-read` and `flag-retirement-not-owner` |
| owner | yes | yes | as before |
| another station | yes | yes | as before, plus `flag-retirement-not-owner` |
| none | no | — | `flag-key-not-in-tree` (as before) |
| owner by tree `metadata.owner` (no station segment) | yes | yes | none |
| any (no station segment) | no | — | `flag-retirement-not-owner`, owner unknown |

A key with no station segment (the estate's cutover string flag is the one live case) can be declared retired only
while the tree holds it. No `flag:` block names such a key, since the block's key is `pyforge.<station>.<capability>`
(CAP-1), so none needs a retirement to clear `flag-key-not-in-tree`.

</intent-contract>

## Binding

- Dream: `docs/dreams/feature-flag-governance.md` § *Realization log*, the 2026-10-15 entry (the retirement leg).
- Guild Spec: `docs/governance/spec-feature-flag-governance/` — memlog decision 2026-10-15 (CAP-2 amended), the
  story-mint event (CAP-2 -> doctor 34.7), the surface-comment note, and the two self-validate events; `SPEC.md`
  re-derived by an anchor-asserting script (operator-approved 2026-10-15).
- Epic: Epic 34. A new story reopens its done epic (Story 41.5's rule; the 34.6 precedent), so `epic-34` reads
  `in-progress`.
- Ledger key: `34-7-a-retired-flag-leaves-the-tree-only-by-its-owner-and-never-while-read`, minted `backlog` in the
  same commit as the epics heading.
- Deps: —. Lands with herald 42.3 in the one-PR Pages redesign (operator ruling 2026-10-15).
- Surface: Epic 34's `[epic_surfaces]` (doctor `marshal-policy.toml`) already admits both scripts, both test files, the
  block page and the Guild Spec's memlog; its comment now names 34.6 and 34.7.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_flag_gate_check.py tests/scripts/test_flag_inventory.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass (the Detectors scripts-suite lane).
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0 on the landing tree.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Test files:** `tests/scripts/test_flag_gate_check.py` (the owner's retirement passes; a reader left fails per file;
a foreign declaration fails and retires nothing; foreign plus owner; a key still in the tree; a key with no station
segment), `tests/scripts/test_flag_inventory.py` (a foreign retirement reads "not in tree"; the owner's reads
"retired by") and `tests/scripts/test_flag_rule.py` (the block page's three examples classify as written).

**Mutations (each restored afterwards):** count every declaration, not only the owner's; drop `judge_retired_reads`
from `judge_tree`; match the key as a bare substring; drop `judge_retirements` from `judge_one`. Each fails at least
one of the tests above.

## Named, not fixed here

- **The flag inventory reports are stale on this branch.** A fresh `flag-inventory` run rewrites the marshal and
  steward reports (CAP rows that move to `unresolved`), from epics text changed outside this story. The herald report
  differs only by its SHA line. This story regenerates nothing; the reports belong to the next inventory run.

## Spec Change Log

- 2026-10-15: minted and built in one change on the one-PR Pages redesign branch (lane C), after the independent review
  of herald 42.3 + steward 102.5 found the gate change ungoverned (blocker) and the leak (should-fix). Chain: Dream
  entry, Guild memlog decision and events, `SPEC.md` re-derived by script, epics Story 34.7, ledger row, this spec.

## Build Record

Built 2026-10-15 in the lane-C worktree of the one-PR Pages redesign, from `b673b9b1ee`. Every verdict is an exit code.

- `pytest tests/scripts/test_flag_gate_check.py tests/scripts/test_flag_inventory.py tests/scripts/test_flag_rule.py`
  (pyforge-guild): 311 passed, exit 0.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test`: 1579 passed, 28 skipped, exit 0. Its first run went
  red on two things this story caused: the block page's third YAML example (`test_flag_rule.py`) and the TEA matrix
  missing 34.7 (`test_tea_playwright_check.py`). Both were fixed here.
- `pixi run --frozen -e pyforge-guild flag-gate-check`: exit 0, 1479 specs, 0 fail. `--spec` on this spec and on
  herald 42.3 reads `pass`.
- Live probe: a line naming `pyforge.herald.pages_second_host` appended to a tracked herald module made the gate exit 1
  with one `flag-retired-still-read` naming that file. The file was restored byte for byte.
- Mutations: count every declaration; drop `judge_retired_reads`; match a bare substring; drop `judge_retirements`.
  Each failed 1-4 of the new tests. All were restored.
- `lint-types`, `chain-completeness-check`, `dream-chain-check`, `dreams-hygiene-check`, `deferred-work-check`,
  `ledger-regression-check`, `story-status-check`, `chain-currency-sweep-check`, `tea-playwright-check` and
  `docs-site-validate` (site) all exit 0. Working-tree ledger durability (`MARSHAL_DURABILITY`) reads OK: `epic-34`'s
  reopen is excused by the new not-done 34.7 key.
- `pyforge-doctor`'s `tests/meta/test_flag_gate_stays_outside_every_station.py`: exit 0.
