---
title: "31.4: Scribe's part of the cutover-readiness change closes at the integration head"
type: 'chore'
created: '2026-11-10'
status: 'blocked'
difficulty: 'medium'
story: 31-4-scribe-s-part-of-the-cutover-readiness-change-closes-at-the-integration-head
spec: spec-pyforge-scribe
surface:
  - docs/reference/bmad-estate-llms-full.md
  - docs/reference/library-llms-full.md
  - .claude/memory/MEMORY.md
  - .claude/memory/project/**
  - src/shared/packages/pyforge-scribe/tests/meta/data/spec_behind_memlog_known.json
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/.memlog.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-31-4-scribe-s-part-of-the-cutover-readiness-change-closes-at-the-integration-head.md
  - AGENTS.md
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/governance/guild-roster.json
  - .claude/memory/README.md
warnings: []
deferred: []
declared_low_risk: false
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-32.1, S-32.2, S-32.3, S-33.1,
> S-33.2). The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** The catalogs scribe owns, the team-memory close, the known-rows file of the memlog check, scribe's Spec
surface and the late `AGENTS.md` edit can only be made true after every unit has built (audit NICE N7; the
session-close ritual; Pre-PR checklist items 2, 5 and 7).

**Approach:** Generated files, one capture, one bookkeeping memlog event and one late `AGENTS.md` edit; no code.

1. Regenerate either catalog only if its check is red: `scribe catalog bmad-estate --write`, and the library catalog
   by its own generator (`docs/reference/library-llms-full.md` is governed by `spec-pyforge-marshal` and
   `spec-pyforge-steward`; a regeneration sends those two Specs a reconcile request).
2. Re-measure `tests/meta/data/spec_behind_memlog_known.json` with full history: drop every row a unit's re-derive
   cleared and keep the rest with their owner. No row is scribe's. Steward Story 120.3 re-derives
   `docs/governance/spec-one-chain-per-station` and `docs/governance/spec-coverage-gate-independence` (operator ruling
   2026-11-10), so their rows are expected to leave.
3. Append one `(event) Surface reconcile <date>` entry to the scribe memlog naming every scribe-governed path Stories
   31.1 to 33.2 and this story moved (bookkeeping: the Spec is not behind and no re-derive follows).
4. The one late `AGENTS.md` edit, after Story 32.1's refresh of the same file: the `[SKF Skills]` block re-exported
   after steward:S-29.5 (atlas lists 13 MCP tools), Pre-PR item 1 and the lint paragraph naming both suite halves and
   the package `pixi.toml` floors, the `src/platform` import-guard pitfall, and § Session guardrails' rule count and
   denial list after steward:S-121.4 adds `chain-write-off-the-writer` (the roster holds 20 session denials).
5. One `scribe capture --type project` for the close, carrying the capture text other units send; no other unit runs
   `scribe capture` in this change. `MEMORY.md` writers in order: Story 32.2, then this story.
6. `marshal context advisory`.

Doctor:S-58.4 takes the scoped stamp `--spec pyforge-scribe/spec-pyforge-scribe` after this story's last governed edit;
the CLOSE-LEDGERS job promotes the keys. This story writes neither.

Ledger key: `31-4-scribe-s-part-of-the-cutover-readiness-change-closes-at-the-integration-head`.
Type / Effort / Deps: chore / M / 31.1, 31.2, 31.3, 32.1, 32.2, 32.3, 33.1, 33.2 (cross-station deps in Notes).

### Living CAP citations

- `spec-pyforge-scribe` CAP-32 (the estate catalog), CAP-1 (team memory), CAP-35 (the known-rows file), CAP-27
  (`AGENTS.md`); no CAP moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Judge the known rows with full history (`git rev-parse --is-shallow-repository` prints false).

**Never:**
- Do not write `sprint-status-ledger.yaml` or the Tier-3 feed.
- Do not run `spec_surface_check.py --write-baseline`.
- Do not hand-edit either catalog or the `bmad:context` block.

</intent-contract>

## Acceptance Criteria

- **AC1 — The BMAD-estate catalog is current.** `pixi run --frozen -e pyforge-guild scribe catalog bmad-estate --check` exits 0.
- **AC2 — The library catalog is current against `pixi.toml`.** `pixi run --frozen -e pyforge-guild llms-full-check` exits 0.
- **AC3 — The closing capture landed and the index still holds.**
  `test $(git diff --name-only --diff-filter=A $(git merge-base origin/main HEAD) HEAD -- .claude/memory/project | wc -l) -ge 1 && PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/meta/test_team_memory_index.py -q` exits 0.
- **AC4 — No Spec is behind its memlog at the integration head, judged with full history.**
  `test "$(git rev-parse --is-shallow-repository)" = false && PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/meta/test_spec_not_behind_memlog.py -q` exits 0.
- **AC5 — Every known row names an owner, and none is scribe's.**
  `python3 -c "import json,sys;b=json.load(open('src/shared/packages/pyforge-scribe/tests/meta/data/spec_behind_memlog_known.json'));rows=[r for v in b.values() for r in v];ok=all(set(r)=={'fingerprint','kind','committed','owner'} for r in rows) and not any('spec-pyforge-scribe' in k for k in b);print(len(rows), sorted({r['owner'] for r in rows}));sys.exit(0 if ok else 1)"`
  exits 0; any row left names the unit that chose not to clear it.
- **AC6 — No unreconciled drift row names scribe's Spec (after doctor:S-58.4's scoped stamp).**
  `pixi run --frozen -e pyforge-guild python -m pyforge.doctor.sources spec-surface --json > "${TMPDIR:-/tmp}/ss.json"; python3 -c "import json,sys;d=json.load(open(sys.argv[1]));rows=d if isinstance(d,list) else (d.get('findings') or d.get('rows') or []);n=[r for r in rows if r.get('check') in ('drift','drift-presumed') and sys.argv[2] in json.dumps(r)];print(len(n));sys.exit(1 if n else 0)" "${TMPDIR:-/tmp}/ss.json" pyforge-scribe/spec-pyforge-scribe`
  prints 0 and exits 0.
- **AC7 — The station suite, both halves, with the server up.**
  `pixi run --frozen -e pyforge-scribe-pg scribe-pg-up && pixi run --frozen -e pyforge-scribe pyforge-scribe-test && pixi run --frozen -e pyforge-scribe pyforge-scribe-live-test` exits 0 (the live task exists once steward:S-124.1 splits it).
- **AC8 — The session-close advisory ran.** `pixi run --frozen -e pyforge-guild marshal context advisory` exits 0.
- **AC9 — The SKF block matches the recompiled snippets and the instruction parity holds.**
  `pixi run --frozen -e pyforge-scribe env PYTHONPATH=src/shared/packages/pyforge-scribe/src:scripts pytest src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py -q && pixi run --frozen -e pyforge-guild governance-currency` exits 0.
- **AC10 — The guardrails name the chain-write denial and no stale count.**
  `grep -c 'chain-write-off-the-writer' AGENTS.md && test $(grep -c 'Sixteen of this file' AGENTS.md) -eq 0` prints 1 or more and exits 0.

## Binding

- Parent capabilities: `spec-pyforge-scribe` CAP-1, CAP-27, CAP-32, CAP-35; no CAP moves.
- Dream: `docs/dreams/pyforge-scribe.md` § Realization log, the 2026-11-10 (cutover readiness) entry.
- Epic: Epic 31. Ledger key `31-4-scribe-s-part-of-the-cutover-readiness-change-closes-at-the-integration-head`,
  minted `backlog`, then set `blocked` by the mint fix pass (forward dependency: its Deps name Epics 32 and 33;
  unblocked only with operator confirmation).
- Deps (same station): 31.1, 31.2, 31.3, 32.1, 32.2, 32.3, 33.1, 33.2. Wave BUILD-16.

## Notes

- Cross-station deps: steward:S-29.5 (the station skills recompiled, then the SKF block re-exported), atlas:S-48.3
  (the views runtime leaves atlas before the library catalog is regenerated once), marshal:S-116.2, marshal:S-116.3,
  marshal:S-116.4 (marshal's suite halves, named in Pre-PR item 1), steward:S-120.3 (the two Guild Specs re-derived,
  so their known rows leave), steward:S-121.4 (the `chain-write-off-the-writer` session denial), steward:S-121.7 (the
  capability ledger regenerated from the swept Specs; the mint already wrote the `spec-pyforge-scribe` rows, CAP-33
  and CAP-35 `rebuild` and CAP-34 `retire`, the mode steward:S-121.3 sets, so `capability-ledger-check` exits 0 from
  the mint on and the regeneration must keep those three rows), steward:S-124.1 (the scribe
  test task split into two halves), steward:S-124.3 (`pixi.lock` regenerated once for every package manifest),
  steward:S-124.5 (persona MCP lines).
- Also needed before it: doctor regenerates `docs/governance/flag-inventory/pyforge-scribe.md`; the co-governor
  reconcile events for `spec-pyforge-core` (core-kit) and `spec-pyforge-unifying-strategy` (steward-station) are
  written by their own closers.
- `.claude/memory/**` is scribe's for the whole PR: each unit sends its capture text here, so the index (145 lines
  at plan time, bound 200) gains one or two lines, not one per story.
- Closes audit NICE N7.

## Spec Change Log

- 2026-11-10: minted with Epic 31 at the cutover-readiness mint; the known-rows expectation follows the operator
  ruling that steward Story 120.3 re-derives both Guild Specs.
- 2026-11-10 (mint fix pass, independent review): the plan's twelve acceptance checks became ten ACs. The plan's two
  `llms-full-check` entries (its checks 2 and 10) are one command, merged into AC2, which runs at the integration
  head after every manifest edit of this PR. The plan's first spec-surface check (its check 6, any finding naming a
  scribe-governed path) is replaced by AC6's drift-row filter on `spec-pyforge-scribe` (its check 11), because the
  later form, written for the integration head after doctor:S-58.4's scoped stamp, supersedes it.
- 2026-11-10 (mint fix pass, third review round): the fleet forward-dependency policy applies. The Deps in `epics.md`
  read `S-31.1, S-31.2, S-31.3, S-32.1, S-32.2, S-32.3, S-33.1, S-33.2`, the grammar `forward-dependency-check`
  parses, and the key is `blocked` (feed, synced ledger, this spec's status, the `epics.md` Status line) until
  Epics 32 and 33 are done; the dated blockquote above says so. The Notes clause that `capability-ledger-check`
  exits 2 until steward:S-121.7 is corrected: the mint wrote scribe's CAP-33..CAP-35 rows and the check exits 0.

## Planned deferral (written at build)

Written 2026-11-13. No frontmatter `deferred:` row; the ledger rows below are proposed for whoever writes scribe's
`deferred-work-ledger.md` next (it is not in this story's files).

- **`DW-scribe-31-4-1`** (proposed; low; location `AGENTS.md`, inside the `bmad:context` block: the *Running and
  verifying* lint paragraph and the *Policy* line on `src/platform/`). The plan's late edit names "the lint paragraph"
  and "the src/platform import-guard pitfall", but both lines sit inside the `bmad:context` block, which this story's
  Never forbids hand-editing; the operator's per-PR approval (b) of 2026-11-10 covers Story 32.1's headless refresh
  only, and `bmad-project-context` otherwise needs the user to approve every write. The facts landed outside the
  block instead, in Pre-PR checklist item 1: both suite halves for every station (`pyforge-<station>-test` and
  `pyforge-<station>-live-test`; the kernel packages' `pyforge-<x>-package-test`), that `target-version-check` also
  holds the `python` floors of each `src/shared/packages/pyforge-*/pixi.toml`, and the import-guard pitfall. The lint
  paragraph is incomplete, not wrong: it still names the `pyproject.toml` targets and floors only. Closes on the next
  operator-approved `bmad-project-context` refresh, which copies the two facts into the block.
- **`DW-scribe-31-4-2`** (proposed; low; location `.claude/skills/.export-manifest.json`). The `[SKF Skills]` section
  was re-exported with the exporter's own script (`_bmad/skf/shared/scripts/skf-rebuild-managed-sections.py assemble`,
  then `replace`), which reads the export manifest and does not write it, so its `last_exported` dates still read
  2026-08-26 (2026-10-05 for mason). The manifest is under `.claude/skills/**`, steward:S-29.5's files, not this
  story's. Closes on the next `skf-export-skill` run.

Planned red windows (not deferrals; each closes with a later story of this PR):

- AC4 and AC7's live half: `test_live_tree_no_spec_is_behind_its_memlog` fails only on `spec-pyforge-steward`, behind
  three memlog events (`6b8cc9e9dc14555e` Story 122.2, `03c01d7cef54a9a5` Story 122.3, `fd0f73ef01b524f0` Story
  122.4). steward:S-122.5 (BUILD-17) re-derives that Spec. No known row was added for them: the file only shrinks.
- Reconcile request: `docs/reference/library-llms-full.md` moved (the `tornado` ghost entry removed and one dated
  header clause). It is governed by `spec-pyforge-marshal` and `spec-pyforge-steward`; their closers (marshal:S-116.5,
  steward:S-122.5) name it in their `Surface reconcile` events.

Build facts the reviewer needs:

- The library catalog has no generator for a ghost entry: `llms_full_check.py --fix-floors` rewrites floors only, and
  the catalog header says "undocumenteds and ghosts still require a human". The ghost was removed by that human pass
  (atlas's shared request: "Reword or regenerate the three entries"); the catalog never carried `starlette`, and
  `bokeh`'s § 8 entry names no atlas use, so only `tornado` moved.
- The steward-station request asked the pitfall to "cite the 21 tests". Measured: 21 tests carry the guard's names,
  but 19 red on any changed `src/platform/` `.py` that imports `pyforge`; doctor's `test_portal_fleet_pulse.py` reds
  only on an import the branch adds, and herald's `test_this_story_platform_delta_does_not_import_pyforge` reads one
  fixed file. Item 1 cites the 19.
- `spec_behind_memlog_known.json` is `{}`: all 32 rows (25 `spec-pyforge-marshal`, 7 `spec-pyforge-unifying-strategy`)
  were no longer behind with full history; the Guild Specs' rows had already left at Story 32.3's BUILD-1 gate.
- No capture text from another unit was found in the branch's story specs or shared requests; the one
  `scribe capture --type project` carries scribe's close only.
