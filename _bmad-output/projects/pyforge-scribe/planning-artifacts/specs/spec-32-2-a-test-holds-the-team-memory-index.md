---
title: '32.2: A test holds the team-memory index'
type: 'chore'
created: '2026-11-10'
status: 'backlog'
difficulty: 'medium'
story: 32-2-a-test-holds-the-team-memory-index
spec: spec-pyforge-scribe
surface:
  - src/shared/packages/pyforge-scribe/tests/meta/test_team_memory_index.py
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-32-2-a-test-holds-the-team-memory-index.md
  - archive/.claude/memory/project/**
  - .claude/memory/project/**
  - .claude/memory/MEMORY.md
review_loop_iteration: 0
followup_review_recommended: false
context:
  - .claude/memory/README.md
  - .claude/memory/MEMORY.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - docs/dreams/pyforge-unifying-strategy.md
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/models.py
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Nothing tests that `.claude/memory/MEMORY.md` and the record files agree (audit SHOULD S7), and about 45
of its 121 index lines are receipts that later records supersede: 9 CI pause and resume entries (no surface in
`docs/governance/ci-surfaces.yaml` is paused), 18 of the 19 session closes, 16 "story landed in dispatch worktree"
receipts, `operator-inbox-as-of-2026-09-19`, and `2026-09-25-bmad-suite-advance-landed-as-pr-1607` (superseded by the
2026-09-26 merged entry).

**Approach:** A guard test, a manifest, and the prune the operator approved on 2026-11-10 (second addendum, item 7).

- `tests/meta/test_team_memory_index.py` (with `pytestmark = pytest.mark.live_tree`) holds: the link targets of
  `MEMORY.md` equal the record files under `feedback/`, `project/` and `reference/`; every link resolves; every record
  parses with the nested `metadata.type` the code writes (`CaptureRecord.to_frontmatter`); the index stays under 200
  lines. It exits 1 naming the record otherwise, and fixture trees plant an unlinked file, a dangling link, a flat
  `type:` record and a 200-line index.
- The story reads each candidate's body before listing it, and leaves out a record that still carries an open
  operator-owned ask or a rule no later record states (`mason-story-26-1` states a standing rule and is not a
  candidate). The manifest is a table in this spec, under a heading that states its count: record path, reason, the
  record that supersedes it. Two candidates are cited from memlogs (`operator-inbox-as-of-2026-09-19` from the marshal
  and scribe memlogs, a 2026-10-13 session close from herald's) and the manifest says so: memlog history is not
  rewritten when a record moves; `archive/<original path>` keeps the old path readable.
- The manifest's records move with `git mv` to `archive/.claude/memory/project/` (the shape of commit `af2d5799d7`;
  leave to add under `archive/` given by the ruling), and their index lines leave `MEMORY.md`, in one commit.

Ledger key: `32-2-a-test-holds-the-team-memory-index`. Type / Effort / Deps: chore / M / none.

### Living CAP citations

- `spec-pyforge-scribe` CAP-1, as amended at the 2026-11-10 mint (FR-2): the index clause, held by this test. Pruning
  stays as `.claude/memory/README.md` § When to prune says: humans decide, and the record is deleted or archived; the
  operator decided this prune on 2026-11-10, and the form is archive.

## Boundaries & Constraints

**Always:**
- Move with `git mv`; read every candidate's body before listing it.
- `MEMORY.md` writers in this PR, in order: this story, then Story 31.4's closing capture.

**Never:**
- Do not delete a record.
- Do not move a record that is not in the manifest, or one that still carries an open operator-owned ask.
- Do not rewrite a memlog or another dated record to name a moved record's new path.

</intent-contract>

## Acceptance Criteria

- **AC1 — Index and files agree, the schema parses, the size bound holds.**
  `PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/meta/test_team_memory_index.py -q` exits 0.
- **AC2 — The guard fires on four planted fixture trees** (an unlinked file, a dangling link, a flat `type:` record, a
  200-line index):
  `PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/meta/test_team_memory_index.py -q -k test_index_guard_names` exits 0 and its summary line reads `4 passed`.
- **AC3 — The manifest is in this spec, one row per record.**
  `grep -c '^| `project/' _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-32-2-a-test-holds-the-team-memory-index.md`
  prints a number from 1 to 45, equal to the count the manifest's heading states.
- **AC4 — The manifest's records moved to the archive, and nothing was deleted.**
  `git diff -M --diff-filter=R --name-status $(git merge-base origin/main HEAD) HEAD -- .claude/memory archive/.claude/memory | grep -c 'archive/.claude/memory/project/'`
  prints the manifest's count, and
  `git diff -M --diff-filter=D --name-only $(git merge-base origin/main HEAD) HEAD -- .claude/memory archive/.claude/memory | wc -l`
  prints 0 (both pathspecs, so a move reads as a rename).
- **AC5 — Lint and types.** `pixi run --frozen -e pyforge-guild lint-types` exits 0.

## Binding

- Parent capability: `spec-pyforge-scribe` CAP-1 (amended 2026-11-10); FR-2.
- Dream: `docs/dreams/pyforge-scribe.md` § Realization log, the 2026-11-10 (cutover readiness) entry.
- Epic: Epic 32. Ledger key `32-2-a-test-holds-the-team-memory-index`, minted `backlog`.
- Deps: none. Wave BUILD-1.

## Notes

- Closes audit SHOULD S7 in full: the guard lands and the operator-approved records move.
- Shared request (steward-station): the scribe live-test trigger paths cover the whole `.claude/memory` tree (today
  `MEMORY.md` and `feedback/` only).
- The prune moves records; it adds none. The closing capture of this PR is Story 31.4's.

## Manifest

To be written by this story at build, one row per record (`` | `project/<slug>.md` | reason | superseded by | ``),
under a heading that states the count.

## Spec Change Log

- 2026-11-10: minted with Epic 32 at the cutover-readiness mint. The operator approved the manifest and its form
  (`git mv` to `archive/.claude/memory/project/`) the same day, so this story moves the records and AC4 checks the
  moves; the plan's "nothing moves" check and its effort S are superseded (effort M).
