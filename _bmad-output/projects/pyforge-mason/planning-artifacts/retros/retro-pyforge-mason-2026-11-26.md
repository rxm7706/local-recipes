---
title: 'pyforge-mason — Retrospective (2026-11-26: Epics 40 to 45, since the 2026-11-12 retro)'
project: pyforge-mason
created: '2026-11-26'
updated: '2026-11-26'
epics: [40, 41, 42, 43, 44, 45]
date: '2026-11-26'
verdict: accepted-with-open-items
criteria: declared
headless: true
scope: 'Every mason epic built since retro-pyforge-mason-2026-11-12.md: Epic 40 (CFE scripts merge the pixi config layers), 41 (the pypi-test rehearsal asks the index it uploads to), 42 (a failed wrapped tool makes mason exit 1), 43 (exit codes held to the declared domain), 44 (both JSON spellings), all on origin/main, and Epic 45 (build-engine plugins registered under mason''s name) on branch plugin-names-2026-11-26 only. Written by bmad-retrospective, headless, because the chain-currency sweep reports feeds code->retro: the package pyproject.toml moved on 2026-11-26 (5ae0f4334f, Story 45.1).'
evidence:
  - 'range cb87e7e2e0..HEAD (the 2026-11-12 retro commit through HEAD 24af8d0a90 on plugin-names-2026-11-26): 281 commits, 31 merges, 28 measured; scripts/git_evidence.py output kept in the session scratchpad'
  - 'story commits: ded8971009 (40.1), 91b387fea9 (41.1), cc916b2394 and 840848920c (42.1), a2741bf4be (43.1), 558156c8fa (44.1), 5ae0f4334f (45.1, not on origin/main)'
  - 'pixi run --frozen -e pyforge-mason pyforge-mason-test: exit 0, 1729 passed, 73 deselected (2026-11-26)'
  - 'pixi run --frozen -e pyforge-mason pyforge-mason-live-test: exit 0, 73 + 2 + 12 passed (2026-11-26)'
  - 'mypy on pyforge.mason.cli with its override emptied (scratch config): exit 1, 9 errors (2026-11-26)'
---

# pyforge-mason — Retrospective, Epics 40 to 45 (2026-11-26)

## Epic summary

- **Epics and stories.** One story each, all type fix except 44.1 (feature) and 45.1 (chore):
  - Epic 40 / Story 40.1, minted 2026-11-18 (`83f3d6b971`), built in `ded8971009` (conda-forge-expert v8.105.2),
    landed with PR #2373 (merge `424ce69fc2`, *Merge pyforge-doctor/59-8 into main*).
  - Epic 41 / Story 41.1, minted and built 2026-11-25 (`91b387fea9`), landed with PR #2385 (merge `080f89c4df`,
    *Merge pyforge-steward/133-1 into main*).
  - Epic 42 / Story 42.1, built 2026-11-25 (`cc916b2394`, `840848920c`), landed with merge `6db8d6e60f`
    (*Merge pyforge-steward/135-1 into main*).
  - Epic 43 / Story 43.1, minted `6ee98d33a0`, built `a2741bf4be`, landed with merge `ce2ca7f9cb`
    (*Merge pyforge-steward/142-1 into main*).
  - Epic 44 / Story 44.1, minted `95c92b7fb8`, built `558156c8fa`, landed with merge `3556bd1f2e`
    (*Merge pyforge-steward/144-1 into main*).
  - Epic 45 / Story 45.1, minted and built in `5ae0f4334f` on this branch; `git merge-base --is-ancestor 5ae0f4334f
    origin/main` is false, so it has not landed.
- **Completeness.** `sprint_status.py detect-epic --epic <n>` on `implementation-artifacts/sprint-status.yaml` returns
  `story_count` 1 and an empty `pending_stories` for each of 40 to 45. The tracked ledger agrees
  (`sprint-status-ledger.yaml` lines 141-146 `done`, 229-240 `epic-4x: done`, every `epic-4x-retrospective: optional`).
  Epic 45 reads `done` before it has landed. That is this repository's in-PR promotion rule (`AGENTS.md` § Pre-PR
  checklist item 7), not a gap.
- **Mason surface moved.** `cli.py` (+50 −31), `package.py` (+52 −15), `pypi_index.py` (+27 −6), `recipe.py`,
  `exit_codes.py`, `engines/gh.py`, `models.py` docstrings, and `pyproject.toml` (two entry-point names). Tests: `test_cli.py`
  +288 −25, `test_package.py` +145, `test_pypi_index.py` +33, the new `tests/meta/test_exit_codes_match_the_exit_declaration.py` (65 lines).
  Story 42.1 also changed `django_pyforge/station_cli.py` and its platform test. The compiled station skill went to
  0.1.1, with `active -> 0.1.1` and `.claude/skills/.export-manifest.json` `active_version: "0.1.1"`.
  CFE: `scripts/_http.py` +75 −19 and `tests/unit/test_http_resolvers.py` +148 −21 (40.1).
- **Out of scope, but in the range and on mason paths:** steward 125.3 (`b4e2cd5870`, mason's suite runs on a macOS
  laptop), steward 136.4 (`dbfcacacb9`, `test_persona_consults_cfe.py`), steward 29.5 (`651c5640e8`, the 0.1.0
  skill text, 2026-11-12), the cutover-readiness ledger close (`89be2feb3c`, `df2a292e18`), and the CFE retros
  `ebe8a46400`, `f8ec252d21`, `af6e66dbd7`, `df6d96e271` and `2335c039dd` (recipe-factory work under the
  conda-forge-expert skill, not a mason epic). This retro reads them only where they touch a mason story.
- **Evidence inventory.** Available: `epics.md` lines 4360-4520, the six story specs `spec-40-1-*` to `spec-45-1-*`,
  the per-story commits, `deferred-work-ledger.md`, the Spec memlog and `SPEC.md`'s `updated:` trail, both test
  halves and each story's acceptance command run today. Missing: the build agents' session logs, so process lessons
  come from the story specs' change logs and review sections only. Story 45.1's `## Review (2026-11-26)` section was in
  the working tree uncommitted when this retro read it (another agent's write); it is cited as read, not as landed.

## Findings

Each finding has its source and two dispositions: what to do about this instance (fix now, defer or accept), and
what would prevent the next one.

### Spec-to-implementation reconciliation

1. **Story 42.1 grew the masked mypy errors on `pyforge.mason.cli` from 6 to 9.** Source: the 2026-11-12 retro, finding
   9, records 6 errors (5 `assignment`, 1 `attr-defined`) behind `pyproject.toml`'s override
   `disable_error_code = ["assignment", "attr-defined"]` (lines 96-98). Today, with that override emptied in a scratch
   config, `python -m mypy src/pyforge/mason/cli.py` exits 1 with 9 errors. The 3 new ones are all `attr-defined` and
   are read through the untyped dispatch variable: `cli.py:1496` (`result.state`) and `cli.py:1561`
   (`result.pep517_returncode`, `result.pixi_returncode`). Both are the exit projections Story 42.1 added (each line is
   commented "Story 42.1"). Two code stories touched `cli.py` (42.1, 44.1), and neither tightened the override, though
   the prior retro's action 5 and `AGENTS.md`'s ratchet rule ("tighten the entry when you touch its module") asked for it.
   *Instance:* fix now, as action item 1. The override hides the very attributes the new exit contract reads, so a
   typo there would fail no gate. *Prevention:* a story whose surface includes `cli.py` carries an acceptance line that
   the `pyforge.mason.cli` override shrinks or stays empty.
2. **Epic 42 changed a declared contract, and the chain moved with it.** Source: `spec-42-1-*` § Spec Change Log
   (test-first: 8 failed on the unchanged `cli.py`, then 17 passed; the platform row 3 failed, then 90 passed),
   `SPEC.md` `updated:` (CAP-2 and CAP-5 amended 2026-11-25), `contract.md` (+15 −12 over the range), the compiled skill
   0.1.1, and `DW-mason-41-1-1` (`status: closed`, resolution naming Story 42.1 and the operator ruling "Exit 1 on
   failure"). Story 41.1 had first closed the finding as not a defect, because `contract.md` § *Exit codes* stated
   exit 0. It handed the choice to the operator as a ledger row instead of changing the contract on its own reading
   (`spec-41-1-*` § Spec Change Log, defect 2). *Instance:* accept; it is the expected route. *Prevention:* none needed.
   This is the pattern to keep: a reviewer's finding that contradicts a written contract becomes an operator row, not a fix.
3. **`spec-pyforge-mason`'s `companions:` comments still trail the chain.** Source: `SPEC.md` lines 32-33 still read
   `FR-1..FR-50 / NFR-1..NFR-16 / D-1..D-13` and `AD-1..AD-16 + AD-25/AD-26`, and `DW-mason-37-2` reads `status: open`. The
   Spec was re-rendered twice in this range (42.1 and 45.1), and each render says "nothing else re-derived"
   (`SPEC.md` `updated:`). The prior retro's action 2 named "the next re-derive". The anchored, scoped renders these
   stories used do not count as that re-derive. *Instance:* defer. The row stays open; no surface reads the comments.
   *Prevention:* the open row names the event that closes it, a full `bmad-spec` re-derive, not "the next re-derive".
4. **Epic 45 needed a Spec amendment its Epic said it would not.** Source: `spec-45-1-*` § Review (2026-11-26), finding
   1, in the working tree: "Mason CAP-37 named the old entry points". The fix was a memlog decision plus an anchored
   render, and Epic 45's HARD boundaries now name CAP-37 (`epics.md` lines 4484-4486). The review also found three
   stations' tests pinning the old names (finding 2). *Instance:* fixed in the story. *Prevention:* when a story renames
   an identifier, the mint greps the Spec and the tests for the old literal before it writes "no capability text moves".

### Story records

5. **Story 40.1's spec stops at its mint.** Source: `spec-40-1-*` § Spec Change Log has one line ("2026-11-18: minted")
   and § Binding still reads ledger key "(`backlog`)". The ledger reads `done`, and the closing evidence lives
   elsewhere: commit `ded8971009`, `DW-doctor-59-3-1`'s resolution (doctor ledger line 3401: "mason Story 40.1, commit
   ded8971009"), and the CFE `CHANGELOG.md` entry. The story has no review record. Stories 43.1 and 44.1 have a
   `## Review (2026-11-26)` section but no change-log close. *Instance:* defer. The landing evidence is real, only the
   story spec does not carry it. *Prevention:* the close of a multi-station PR appends one closing line to each story
   spec (commit, merge, review), as 41.1's and 42.1's change logs do.
6. **No mason story in this range landed under a mason merge subject.** Source: the merges in Epic summary, all named
   `pyforge-doctor/59-8` or `pyforge-steward/*`. That is allowed (`AGENTS.md` § Pre-PR checklist item 7: one PR, many
   stations, the merge subject names one key). Mason's keys were promoted inside each PR, and
   `merge-base --is-ancestor` proves each commit landed (40.1 to 44.1 on `origin/main`). *Instance:* accept.
   *Prevention:* none. Finding 5's per-story closing line is what keeps the evidence readable.

### Aggregate views and boundaries (inline)

7. **A cross-station convention lands as one story on each of six stations.** Source: Epics 43 to 45, each minted in a
   fleet commit with steward (`6ee98d33a0`, `95c92b7fb8`, `5ae0f4334f`). Mason's share is small: a 65-line meta-test
   that imports `pyforge.core.exit_domains` in process (no repository-root read at import, so the prior retro's action
   3 import rule holds; it passed inside the package half), one call to `pyforge.core.cli_output.align_json_options`,
   and two renamed entry points. *Instance:* accept. *Prevention:* none.
8. **The 0.1.0 skill text was edited after 0.1.1 became the record, or so the range suggests.** Source:
   `git_evidence.py` reports `.claude/skills/pyforge-mason/0.1.0/pyforge-mason/SKILL.md` +180 −79 in the range.
   `git log` attributes all of it to `651c5640e8` and `84fa9d8c13` (2026-11-12), which ran before 0.1.1 existed, and
   nothing after 42.1 touched 0.1.0. *Instance:* accept, no defect. Story 42.1's claim that the skill-forge version
   model keeps 0.1.0 unchanged holds for its own range. *Prevention:* none.

## Behavior verification

All run 2026-11-26 from the worktree root. Each verdict is read from the exit code.

- `pixi run --frozen -e pyforge-mason pyforge-mason-test`: exit 0, 1729 passed, 73 deselected. The prior retro read 1693.
- `pixi run --frozen -e pyforge-mason pyforge-mason-live-test`: exit 0, 73, then 2, then 12 passed.
- 40.1: `pixi run --frozen -e local-recipes pytest .claude/skills/conda-forge-expert/tests/unit/test_http_resolvers.py
  .../test_http_jfrog_host_gate.py -q`: exit 0, 139 passed. 40.1's own AC (`test-ci` in `-e local-recipes`) was not run.
- 41.1: `pytest .../test_pypi_index.py .../test_package.py -k rehearsal_index`: exit 0, 9 passed.
- 42.1: `pytest .../test_cli.py -k "failed_wrapped_tool or wrapped_tool_exit"`: exit 0, 23 passed. The platform
  `start_build` test was not re-run (it needs PostgreSQL).
- 43.1 AC1: exit 0, 4 passed.
- 44.1 AC1 (`test_public_contract.py -m "live_tree or not live_tree"`): exit 0, 21 passed. AC2
  (`tests/scripts/test_json_output_spellings.py` in `-e pyforge-guild`): exit 0, 21 passed.
  `mason doctor --json`: exit 0, JSON envelope `"command": "doctor"`.
- 45.1 AC1 (`pyforge-core` `test_plugin_registration_conformance.py -m live_tree`): exit 0, 15 passed. AC2
  (`test_build_hooks.py`): exit 0, 10 passed. `importlib.metadata.entry_points(group='pyforge.core.hooks')` in
  `-e pyforge-mason` lists `mason-engine-conda-build` and `mason-engine-rattler-build` and no bare engine name.
- Not exercised: a real wrapped-tool failure end to end (it needs a failing rattler-build run), and a real TestPyPI
  upload. Both stories hold these with planted fakes.

## Previous-retro follow-through

`implementation-artifacts/sprint-status.yaml` carries no `action_items` (0 matches today), so nothing can be followed
through by id. The 2026-11-12 retro's five proposed items, checked by hand:

| # (2026-11-12) | Item | Landed? | Evidence |
|---|---|---|---|
| 1 | 37.1 frontmatter `deferred:` row | no | `spec-37-1-*` line 23 `deferred: []`; ledger twin `DW-mason-37-1` `status: open` |
| 2 | restate `companions:` ranges | no | finding 3 |
| 3 | `live_tree` import rule; closer `files_owned` | holds | finding 7; no new `live_tree` module in range |
| 4 | `--frozen` on acceptance commands | yes | every AC command in `spec-40-1-*` to `spec-45-1-*` carries `--frozen` (grep for a `pixi run` without it: none) |
| 5 | type the dispatch result in `cli.py`, drop the override | no, and it regressed | finding 1 |

No status transition is proposed, since there are no tracked ids to transition.

## Action items

All proposed; this retrospective applies none of them.

| # | Action | Owner | Kind |
|---|---|---|---|
| 1 | Type the dispatch result in `cli.py` (one variable per result type, or a typed union narrowed per branch), so `cli.py:1339, 1475, 1496, 1552, 1561, 1590, 1647, 1656` type-check, then delete the `pyforge.mason.cli` override. A Story under spec-pyforge-mason CAP-5, minted through the Dream. | mason | remediation |
| 2 | Re-word `DW-mason-37-2` so it names the closing event (a full `bmad-spec` re-derive of `spec-pyforge-mason`), or run that re-derive. | mason (next re-derive) | spec reconciliation |
| 3 | Append a closing line (commit, merge, review) to `spec-40-1-*`, `spec-43-1-*` and `spec-44-1-*`, and fix 40.1's Binding `(backlog)`. | change integrator | spec reconciliation |
| 4 | A rename story's mint greps the Spec, `contract.md` and every station's tests for the old literal before it declares "no capability text moves" (finding 4). | marshal (plan mint) | process lesson |
| 5 | A story whose surface includes a module with a mypy override carries an AC that the override does not grow (finding 1). | marshal (plan mint) | process lesson |

## Strategy convergence

Mason's part of the Unifying Strategy is the conda-forge station that B rebuilds from A's oracle, and that oracle moved
in this range. In `docs/foundry/capability-ledger.yaml`, `pyforge-mason:CAP-2`, `CAP-5` and `CAP-37` are mode
`rebuild`. Epic 42 changed CAP-2's and CAP-5's exit contract, and Epic 45 changed the entry-point names that CAP-37
records. Both changes went through the Spec memlog, `contract.md` and the compiled skill (0.1.1), so a rebuild that reads
`contract.md` and runs the contract and exit-domain meta-tests re-derives the new behaviour without reading mason's
code. Epics 43 to 45 put mason on three fleet conventions:
- one exit-code declaration (`spec-pyforge-steward:CAP-184`);
- one way to ask for JSON (`spec-pyforge-steward:CAP-185`);
- station-named plugin registrations (`spec-pyforge-unifying-strategy:CAP-18`).

Each is held by a test that lives outside mason. That is the convergence the strategy asks for: the same shape on every
station, checked once. Mason gains no new capability toward B. The one thing working against convergence is finding 1:
the exit contract a rebuild must reproduce is read through attributes mypy is told not to check.

## Acceptance verdict

**Machine verdict: accepted-with-open-items** (headless; criteria declared in each story spec's Acceptance Criteria).
Every story of Epics 40 to 45 is `done` in the feed and the ledger. Every acceptance command run today exits 0
(Behavior verification; 40.1's `test-ci` AC was narrowed to its CFE unit tests). Both test halves pass. The open items
are tracked or proposed: the masked mypy errors (finding 1, action 1), the `companions:` row `DW-mason-37-2`
(finding 3) and the story-record gaps (finding 5). None of them fails a declared criterion. Epic 45 is accepted on the
branch's evidence; it has not landed on `origin/main`. No human decision was available to this run.

## Assumptions

- The epics came from the invocation's scope ("everything since the last retro" plus Epic 45 on HEAD), not from
  auto-detection. Epics 40 and 41 are included because both were built after 2026-11-12, although the invocation named
  42 to 44 as examples.
- Each epic got its own `detect-epic --epic <n>` (40 to 45): `story_count` 1, `pending_stories` empty.
- `bmad-review` was not invoked. Each story spec records an independent review (41.1, 42.1, 43.1, 44.1, and 45.1 in the
  working tree), except 40.1, which records none. The diff-scope review ran inline over the story boundaries and the
  aggregate views only; the code lenses were not re-run over each hunk.
- The marshal-only EGM drift stage (`_bmad/custom/bmad-retrospective.toml`) does not apply to a mason epic.
- `AGENTS.md` asks for the conda-forge-expert skill on recipe work. This retro covers mason's station epics, not a
  recipe effort, so it neither consults nor edits that skill or its `CHANGELOG.md`. Story 40.1's CFE retro entry
  (v8.105.2, `ded8971009`) is cited as evidence only.
- Phase 5's `sprint_status.py update` was not run, and no ledger, feed, epics, Spec, memlog or Dream was edited. The
  `epic-40-retrospective` to `epic-45-retrospective` keys stay `optional`, and the action items are recorded here only.
- The document lives at `planning-artifacts/retros/retro-pyforge-mason-2026-11-26.md`, which is the station's tracked
  retro home and the place the chain-currency sweep reads, not the skill's default Tier-3 path.
