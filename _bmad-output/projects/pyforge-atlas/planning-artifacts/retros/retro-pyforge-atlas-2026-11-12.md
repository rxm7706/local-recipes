---
title: 'pyforge-atlas — Retrospective (2026-11-12: Epics 46 to 48 and Story 41.2, the cutover readiness change)'
project: pyforge-atlas
created: '2026-11-12'
updated: '2026-11-12'
epics: [41, 46, 47, 48]
date: '2026-11-12'
verdict: rejected
criteria: declared
headless: true
scope: 'Epics 46, 47 and 48 and Story 41.2 of the single cutover-readiness PR (branch cutover-readiness-2026-11-10): the Spec says what is built, open and retired (Epic 46), the public contract is written and held to the code (Epic 47), the package stands apart from A''s tree and from the retired views runtime (Epic 48), and the satellite PRD sections become record sections (Story 41.2). Written by bmad-retrospective, headless, inside Story 48.4. The package pyproject.toml moved on 2026-11-11 (a9349acaff, Stories 48.1 and 48.3), so this is the code->retro retrospective the chain-currency sweep owes.'
evidence:
  - 'range 7630678744^..HEAD on cutover-readiness-2026-11-10 (HEAD 7b6286bd7b at the time of reading): 44 commits, 0 merges, 0 binary revisions; scripts/git_evidence.py output kept in the build scratch folder'
  - 'story commits: 7630678744 (the atlas mint, Epics 46-48, Story 41.2 re-scoped and 41.3 retired), a9349acaff (46.1, 46.2, 48.1, 48.2, 48.3), d063699879 (41.2, 47.1), 7554595df4 (47.2); steward 2fe6e661a3 (124.5) adds two rows to contract.md'
  - 'pixi run --frozen -e pyforge-atlas pyforge-atlas-test: exit 0, 2928 passed and 17 skipped, then 57 passed and 1 skipped (2026-11-12)'
  - 'pixi run --frozen -e pyforge-atlas pyforge-atlas-live-test: exit 0, 368 passed, then 164, then 103 (2026-11-12)'
  - 'pixi run --frozen -e pyforge-atlas kedro-catalog-check: exit 0, 70 passed (2026-11-12)'
---

# pyforge-atlas — Retrospective, Epics 46 to 48 and Story 41.2 (2026-11-12)

## Epic summary

- **Epics:** 46 (*The atlas Spec says what is built, what is open and what is retired*), 47 (*The atlas public
  contract is written and held to the code*, `spec-pyforge-atlas:CAP-73`, FR-78), 48 (*The atlas package and its suite
  stand apart from A's tree and from what the operator retired*), all minted 2026-11-10 in `7630678744` from the station
  Dream's entry of that date (`docs/dreams/pyforge-atlas.md`, Realization log, *2026-11-10 (cutover readiness)*) and
  the operator rulings of 2026-11-10 (`docs/dreams/pyforge-unifying-strategy.md`, Realization log, the entry and its two
  addenda). Story 41.2 (Epic 41) was re-scoped by the same mint and built in the same change; Story 41.3 retired at
  the mint (ruling: "Retire both").
- **Diff range:** `7630678744^..HEAD` (the mint's parent through the last atlas build commit `7554595df4` and the later
  non-atlas waves). 44 commits, no merges (`merge_count` 0, `merges_measured` 0), no binary revisions on an atlas path.
  Atlas churn: 57 package paths, +1457 −1955; 27 planning and Dream paths, +3275 −214.
- **Stories built and reviewed on the branch:** 46.1, 46.2, 48.1, 48.2, 48.3 (`a9349acaff`), 41.2 and 47.1
  (`d063699879`), 47.2 (`7554595df4`). Each build commit says the story passed an independent review and the wave gate.
  48.4 is the story writing this document.
- **Stories not `done` in the feed** (`sprint_status.py detect-epic --epic <n>` on
  `implementation-artifacts/sprint-status.yaml`, 2026-11-12): Epic 41: 41-2, 41-3; Epic 46: 46-1, 46-2; Epic 47: 47-1,
  47-2; Epic 48: 48-1, 48-2, 48-3, 48-4. The tracked ledger reads the same (`sprint-status-ledger.yaml` lines 153-154 and
  161-168: `blocked` or `backlog`). Every built key is promoted by the change's CLOSE-LEDGERS job, after this retro; 41.3 stays
  retired.
- **Evidence inventory.** Available: the epics and story specs (`planning-artifacts/epics.md` lines 3074-3151 and 3288-3474;
  `planning-artifacts/specs/spec-41-2-*`, `spec-46-*` to `spec-48-*`), the per-story commits, the review and gate
  records Story 41.2's spec carries (§ Review findings (build, round 1) and § Gate findings (build, BUILD-3)), the
  Auto Run Results of 41.2, 46.1 and 46.2, the Spec memlog, both test halves and the catalog gate run today. Missing:
  the build agents' session logs (not kept in the tree), and any build record in the Auto Run Results of 47.1, 47.2,
  48.1, 48.2 and 48.3 (each still reads only its mint line), so the process lessons for those five stories come from
  their commits and the live tree, nothing else.

## Findings

Each finding carries its source and two dispositions: this instance (fix now / defer / accept), and what prevents the
next one.

### Spec-to-implementation reconciliation

1. **CAP-73 is built and its marker now says so.** Source: `SPEC.md` CAP-73 heading (`(shipped 2026-11-11; …)`), the
   memlog's 2026-11-12 `change` entry and its two self-validate passes; the success command
   (`pytest tests/meta/test_public_contract.py tests/meta/test_catalog_contract.py` in `-e pyforge-atlas`) exits 0,
   21 passed. *Instance:* accept. *Prevention:* none.
2. **The retired views runtime is gone, and nothing reaches for it.** Source: `a9349acaff` (Story 48.3) deletes the
   seven modules of `src/pyforge/atlas/views/` and the seven files of `tests/unit/views/` (−796 lines under `src/`);
   `git grep 'pyforge.atlas.views'` over `src`, `scripts`, `pixi.toml`, `.github` and `docs/` finds only
   `scripts/.spec-surface-baseline.json` entries; `importlib.util.find_spec("pyforge.atlas.views")` is `None`; the
   Spec reads CAP-44..CAP-47 `(retired 2026-09-09 …)` (Story 48.4 AC3 exits 0). *Instance:* accept; the stale baseline
   entries are doctor Story 58.4's prune. *Prevention:* none.
3. **Two planned deferral rows are addressed to a closer whose files do not include the ledger.** Source:
   `spec-47-1-…` § Planned deferral (written at build) (`DW-atlas-47-1-1`, the `env` mapping reads and `wasm/build.py`'s
   exit outside the contract test's derivation, open) and `spec-41-2-…` § Planned deferral (written at build)
   (`DW-atlas-41-2-1`, doctor's stale `fr-duplicate-id` assertion; resolved: the flip
   `assert dups["pyforge-atlas"] == []` is in `src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_one_chain_fr_arrows.py:179`).
   Both say "the atlas station closer … writes it to `deferred-work-ledger.md`"; Story 48.4's `files_owned` in the plan
   names no ledger, and `grep` finds neither id in the ledger. *Instance:* defer to the change integrator (action 1).
   *Prevention:* a deferral a build hands to a closer is minted into that closer's `files_owned` (the mason retro of the
   same day, finding 1, found the same gap).
4. **Two of the change's build records carry no done date.** Source: `spec-47-1-…` and `spec-47-2-…` § Auto Run
   Result (each reads only `Status: blocked (forward dependency …; minted 2026-11-10)`), against 41.2, 46.1 and 46.2,
   whose Auto Run Results carry a dated `Build 2026-11-11` record. CAP-73's shipped date had to come from the build
   commits (`git log -1 --format=%cs`: `d063699879` and `7554595df4`, both 2026-11-11), as the memlog's change entry
   records. *Instance:* accept (the date is git's, not a guess). *Prevention:* every build writes its dated Build line
   in the Auto Run Result, as 46.1 did.

### Story boundaries (diff-scope review, inline)

5. **Story 41.2's retitle redded another station's live test for two waves.** Source: `spec-41-2-…` § Review findings
   (build, round 1) and § Gate findings (build, BUILD-3): the `Fold provenance` retitle ended atlas's
   `fr-duplicate-id` findings by design, and doctor's `test_live_tree_reference_headings_never_duplicate_and_satellites_do`
   asserted the old state (`assert 'fr-duplicate-id:FR-1' in []`); the flip landed with doctor's BUILD-3/BUILD-5
   commits (`6607b20b6a`, `cac36f033e`). *Instance:* fixed. *Prevention:* a story whose change makes another station's
   live test stale names that fix in the other station's story at the mint (41.2's orchestrator decision caught one
   such test and missed this one).
6. **A literal acceptance command re-locked `pixi.lock` again.** Source: this story's AC2
   (`pixi run -e pyforge-guild memlog-fidelity-check`, no `--frozen`): on the branch's moved path-dependency manifests
   the run rewrote `pixi.lock` (herald, mason and scribe source hashes); the file was restored from `HEAD` and the
   check re-run with `--frozen` (exit 0). The mason retro of the same day records the same trap (finding 6, Story 38.2
   AC9). *Instance:* fixed in this story; the lock regeneration stays steward Story 124.3's. *Prevention:* minted
   acceptance commands carry `--frozen` on a branch that edits a path-dependency manifest (action 4).

### Verification gaps

7. **`gate-contract.md` can carry a row for a task that is not a gate.** Source:
   `src/shared/packages/pyforge-atlas/tests/meta/test_catalog_contract.py` lines 268-273: a table row is checked only
   for its task existing in the feature it names. Reproduced 2026-11-12 with the module's own helpers: the derived gate
   set does not hold `kedro-test` (a `depends-on` alias), yet its row is accepted, and replacing it with `viz` (a
   `pyforge-atlas` task that runs no pytest) gives no problem (`_gate_problems` returns `[]` both ways). Story 47.2's
   reviewer listed the same mutation as missed. CAP-73's success names the code-has-more direction, which the test
   holds; this is the other direction. *Instance:* defer (a test change; no story of this change carries it, ruling
   R4). *Prevention:* a contract meta-test checks both directions (action 2).

### Aggregate views

8. **Size: two new meta-tests and their companion.** Source: `git_evidence.py` `files`: `test_public_contract.py`
   +726, `contract.md` +483 (two commits, Story 47.1 and steward 124.5), `catalog-contract.md` +259 −26,
   `test_catalog_contract.py` +329. Each test is one oracle per family with a planted synthetic name per family
   (CAP-73's success). *Instance:* accept. *Prevention:* none.
9. **Duplication: one member-root rule, four resolvers.** Source: Story 48.2 adds `_member_root()` twice with the same
   body (`query_plane_boot.py:81`, `dashboard/identity_gist.py:204`: trust `parents[n]` only when it holds
   `conf/base/catalog.yml`, else the working directory), beside `dashboard/data.default_data_root` (`data.py:127`) and
   `admission._resolve_base` (`admission.py:328`), the four resolvers CAP-69 names. Each docstring points at the
   others. *Instance:* defer: folding them is a refactor no story of this change carries. *Prevention:* the next story
   that touches a resolver folds the four into one helper (action 3).
10. **Architecture delta: none beyond the deletion.** Source: `git diff 7630678744^ HEAD --stat --
    src/shared/packages/pyforge-atlas/src`: 9 files, +34 −796 — the seven deleted views modules and the two root
    resolvers. No import edge is added; `pyforge.atlas.views` has no importer left (finding 2). *Instance:* accept.

## Behavior verification

- `pixi run --frozen -e pyforge-atlas pyforge-atlas-test` (the package half): exit 0, 2928 passed and 17 skipped,
  then 57 passed and 1 skipped.
- `pixi run --frozen -e pyforge-atlas pyforge-atlas-live-test` (the live-tree half): exit 0, 368 passed, then 164,
  then 103.
- `pixi run --frozen -e pyforge-atlas kedro-catalog-check`: exit 0, 70 passed.
- CAP-73's success command: exit 0, 21 passed.
- From `/tmp`, with the package's `src` on the path: `query_plane_boot.DEFAULT_PLANE_PATH` is the absolute
  `<member>/data/plane/atlas.duckdb` and `identity_gist._member_root()` the member, whatever the working directory
  (Story 48.2); `pyforge.atlas.views` does not import (Story 48.3).
- Not exercised: an installed-wheel layout (where both resolvers fall back to the working directory), and any live
  public fetch.

## Previous-retro follow-through

`implementation-artifacts/sprint-status.yaml` carries no `action_items` (read 2026-11-12: zero entries), so there was
nothing to follow through on by id. The prior retro, `retro-pyforge-atlas-2026-10-25.md`, left six candidate fix
stories (its § Candidate fix stories), none tracked as an item:

- 1 (`pyforge-deps-test` in `pr-preflight-lanes`): landed, `pixi.toml` `pr-preflight-lanes` `depends-on` names
  `{ task = "pyforge-deps-test", environment = "pyforge-ci" }` (steward Story 71.14).
- 2 (declare `brotli>=1.2`): landed, `src/shared/packages/pyforge-atlas/pyproject.toml:73` and `pixi.toml:97`.
- 4 (AD-3 names the twelve pipelines): landed, spine line 90 (Story 46.2).
- 5 ("the MCP-triggerable pipelines" wording): landed, `src/pyforge/atlas/mcp/tools.py:88`.
- 3 (a red `kedro-viz-publish` run shown to the next landing) and 6 (the 103.1 memlog correction): no evidence found;
  not checked further.

No status transition is proposed: none of the six is a tracked item.

## Action items

All proposed; none is applied by this retrospective.

| # | Action | Owner | Kind |
|---|---|---|---|
| 1 | Write `DW-atlas-47-1-1` (open) and `DW-atlas-41-2-1` (resolved, pointing at the flip in `test_live_sources_one_chain_fr_arrows.py:179`) into `deferred-work-ledger.md`, from the two story specs' § Planned deferral. | change integrator (the ledger close) | spec reconciliation |
| 2 | Make `test_catalog_contract.py` refuse a gate-table row whose task runs no pytest over the package (the `kedro-test` alias row named as such, or moved out of the table). | atlas | remediation |
| 3 | Fold the four member-root resolvers (`query_plane_boot`, `dashboard/identity_gist`, `dashboard/data`, `admission`) into one helper in the next story that touches one. | atlas | remediation |
| 4 | Mint acceptance commands with `--frozen` on any branch that edits a path-dependency manifest; give a closer the `files_owned` for every row a build hands it (findings 3 and 6). | marshal (plan mint) | process lesson |
| 5 | Each build writes a dated Build line in its story spec's Auto Run Result (finding 4). | marshal (dispatch rules) | process lesson |

## Acceptance verdict

**Machine verdict: rejected** (headless, criteria declared in the epics and story specs). Forced by the rubric: ten
story keys of the four epics are not `done` in the feed (Epic summary). That is the state of record until the
change's CLOSE-LEDGERS job promotes the built keys; 41.3 stays retired.

On the evidence alone, the declared criteria of the built stories hold: both test halves and the catalog gate pass
today, CAP-73's success holds and its marker reads shipped, the views runtime is gone with nothing reaching for it, and
each gap the audit named is either closed in this change or an open ledger row by ruling. No blocking finding stands.
A human may override to **accepted-with-open-items** once the keys are promoted; this run records no such decision.

## Open questions

- Who writes the two planned deferral rows (action 1): the integrator at the ledger close, or a widened `files_owned`
  for this story? Either closes the gap; this run's rules allowed neither.

## Assumptions

- The epics were taken from the invocation (41, 46, 47 and 48), not auto-detected; `detect-epic --epic <n>` returned
  `story_count` 3, 2, 2 and 4 with the keys listed in Epic summary in `pending_stories` (41-1 is `done`).
- The machine verdict is **rejected** because `pending_stories` was non-empty; no human decision was available.
- The activation step that runs marshal's EGM drift stage applies to `pyforge-marshal` epics only; skipped.
- `bmad-review` was not invoked: each story had an independent review and a wave gate at build (the build commits say
  so), and this change's build rules confine Story 48.4 to its own files. The diff-scope review ran inline over the
  story boundaries and the two new meta-tests only (findings 5 to 7); the code lenses were not re-run over each hunk.
- Phase 5's `sprint_status.py update` was not run: this change writes no Tier-3 feed or ledger outside its
  CLOSE-LEDGERS job, so the `epic-41-retrospective` to `epic-48-retrospective` keys stay as they are and the action
  items above are recorded here only.
- The document lives at `planning-artifacts/retros/retro-pyforge-atlas-2026-11-12.md`, the path Story 48.4 names (the
  station's tracked retro home, which the chain-currency sweep reads), not the skill's default Tier-3 path.
