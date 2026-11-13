---
title: 'pyforge-herald — Retrospective (2026-11-12: Epics 50 to 52, the cutover readiness change)'
project: pyforge-herald
created: '2026-11-12'
updated: '2026-11-12'
epics: [50, 51, 52]
date: '2026-11-12'
verdict: rejected
criteria: declared
headless: true
scope: 'Epics 50, 51 and 52 of the single cutover-readiness PR (branch cutover-readiness-2026-11-10): the herald Spec says what is true (Epic 50), no dossier figure is typed and the dossier claims are true (Epic 51), the suite splits on live_tree and the landing record names this checkout''s forge (Epic 52). Written by bmad-retrospective, headless, as Story 50.2 step (k). The package pyproject.toml moved on 2026-11-11 (cf3caf4f45, Story 52.1), so this is the code->retro retrospective the chain-currency sweep owes.'
evidence:
  - 'range f7507c9446^..HEAD on cutover-readiness-2026-11-10 (HEAD 7b6286bd7b at the time of reading): 47 commits, 0 merges; scripts/git_evidence.py output kept in the build scratch folder'
  - 'story commits: cf3caf4f45 (50.1, 50.3, 51.1, 52.1), 9c2eb215fe (52.2), 2bde9641e9 (50.4), 0a47b5a7c4 (52.2 gate fix), a55b810efd (51.2); the mint f7507c9446; Story 50.2 is uncommitted at the time of writing (the wave gate commits it)'
  - 'pixi run --frozen -e pyforge-herald pytest tests/meta/test_public_contract.py tests/unit/test_verify_claims_emit.py -q: exit 0, 47 passed (2026-11-12)'
  - 'pixi run --frozen -e pyforge-herald pyforge-herald-test and pyforge-herald-live-test (2026-11-12): see § Behavior verification'
---

# pyforge-herald — Retrospective, Epics 50 to 52 (2026-11-12)

## Epic summary

- **Epics:** 50 (*The herald Spec says what is true*), 51 (*No dossier figure is typed*), 52 (*Herald's suite and
  landing record follow the tree*), all minted 2026-11-10 in `f7507c9446` from the station Dream's entry of that date
  (`docs/dreams/pyforge-herald.md`, Realization log, *2026-11-10 (cutover readiness)*) and the operator rulings of
  2026-11-10 (`docs/dreams/pyforge-unifying-strategy.md`, Realization log, the three 2026-11-10 entries).
- **Diff range:** `f7507c9446^..HEAD` (the mint's parent through the last herald build commit `a55b810efd` and the
  later non-herald waves). 47 commits, no merges (`merge_count` 0, `merges_measured` 0), no binary revisions on a
  herald path.
- **Stories built and reviewed on the branch:** 50.1, 50.3, 51.1 and 52.1 (`cf3caf4f45`, waves BUILD-1 and BUILD-2),
  52.2 (`9c2eb215fe`, BUILD-4; gate fix `0a47b5a7c4`), 50.4 (`2bde9641e9`, BUILD-5), 51.2 (`a55b810efd`, BUILD-7b).
  Each build commit says the story passed an independent review and the wave gate. Story 50.2 is the story writing
  this document (BUILD-10).
- **Stories not `done` in the feed** (`sprint_status.py detect-epic --epic <n>` on
  `implementation-artifacts/sprint-status.yaml`, 2026-11-12): Epic 50: 50-1, 50-2, 50-3, 50-4; Epic 51: 51-1, 51-2;
  Epic 52: 52-1, 52-2. The tracked ledger reads the same (3 `backlog`, 5 `blocked`; 152 of 160 stories done). Every
  key is promoted by the change's CLOSE-LEDGERS job, after this retro.
- **Evidence inventory.** Available: the epics and story specs (`planning-artifacts/epics.md` § Epic 50 to § Epic 52;
  `planning-artifacts/specs/spec-50-*` to `spec-52-*`), the per-story commits, the story specs' review and gate
  records (52.1 § Review findings rounds 1 and 2; 52.2 § Gate findings; 50.1, 50.3 and 50.4 § Spec Change Log), the
  Spec memlog, the oracle tests and both suite halves run today. Missing: the build agents' session logs (not kept in
  the tree), so process lessons come from the review and gate records the story specs carry, nothing else.

## Findings

Each finding carries its source and two dispositions: this instance (fix now / defer / accept), and what prevents the
next one.

### Spec-to-implementation reconciliation

1. **The Spec ran without Constraints, Non-goals or Assumptions for 56 days, and no check noticed.** Source: `git log
   -S'## Non-goals'` on `spec-pyforge-herald/SPEC.md` names `4251c42229` (the 2026-09-17 fold) as the commit that
   dropped them; the memlog kept 11 constraint, 4 non-goal and 7 assumption entries; the cutover readiness audit of
   2026-11-10 found it (MUST 3, which names the two places that still cite them: the Spec's "Consolidated
   2026-08-02" note, line 96 then and 98 now, and spec-pyforge-herald:CAP-30). The fold lost more than the three
   sections, and none of the rest was a typed entry of herald's memlog, so a re-derive from that memlog could not
   recover it. From herald's own `SPEC.md` at `4251c42229^`: the two station-level constraints and the two
   station-level non-goals the consolidation note calls unchanged ("both Constraints/two of the Non-goals below");
   five more 2026-08-02 items of its Constraints and Non-goals (the constraints "Multi-surface readiness" and "No silent
   shipping", the non-goals "Replacing Moment 1", "Implementing automation yet" and "Marketing proclamation"); and
   `§ Residual dependencies (2026-09-09)`, the Guildhall dependency a memlog decision of 2026-09-09 orders rendered in
   Assumptions. From the Specs it absorbed: `spec-design-sync-loop`'s assumption naming the design-system home
   (`presentations/_design-systems/<name>/`), which spec-pyforge-herald:CAP-30's success cites ("see Assumptions") and
   which that Spec's archived memlog holds
   (`archive/_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-design-sync-loop/.memlog.md:25`) but
   herald's never did; and the SPEC text of all nine: the fold stubbed their `SPEC.md`, whose Constraints, Non-goals
   and Assumptions at `4251c42229^` held 89 bullets, 54 of them carried by no typed entry of their own memlogs, and 6
   prose paragraphs in the two pptx Specs. Beyond the Spec text, the archived memlogs of the Specs folded into herald
   hold 60 constraint, non-goal and assumption entries besides those of the two Specs the 2026-08-02 consolidation
   replayed: 26 in the nine Specs the 2026-09-17 fold absorbed (21 constraints, 5 assumptions) and 34 in spec-deckcraft
   and spec-design-code-bridge (19 constraints, 9 non-goals, 6 assumptions). Two of them are in herald's memlog today
   (design-code-bridge's Story 1.3 transport constraint, and the design-system home); 58 are not. Story 50.2's first
   build missed every one of these losses; its review found the design-system home (round 1), then the station-level
   entries and the dependency (round 2), then herald's five other pre-fold items and the nine Specs' stubbed SPEC text
   (round 3). *Instance:* fixed by Story 50.2 for herald's own Spec text only: three sections of 11, 7 and 11 bullets;
   eight items retired by dated change entries (six typed entries, and "No silent shipping" and "Implementing
   automation yet", which had none); the four station-level entries, the Guildhall dependency and the design-system
   home restored by memlog entries of 2026-11-12, and on round 3 "Replacing Moment 1" and "Marketing proclamation"
   restored and "Multi-surface readiness" narrowed past spec-pyforge-herald:CAP-6, so every Constraints and Non-goals
   bullet of herald's `SPEC.md` at `4251c42229^` is rendered or retired and the note's "below" and
   spec-pyforge-herald:CAP-30's "see Assumptions" resolve again. Not restored, and tracked by `DW-herald-50-2-2`
   (medium): the nine absorbed Specs' 54 bullets and 6 paragraphs, and the 58 archived typed entries; recovering,
   retiring or ruling out each one is a Spec pass that a Story of its own carries (action 6). *Prevention:* a
   re-derive's self-validate pass names the five fields it found and resolves every "below" and "see <section>" the Spec
   cites, as Story 50.2's round-2 and round-3 passes do; a detector that reds a station Spec missing one of the five
   fields would have caught the fold the same day; and a fold that carries the folded Specs' typed memlog entries and
   their untyped Constraints, Non-goals and Assumptions text, and the receiving Spec's untyped sections, into the
   receiving memlog as typed entries would have kept all of it (action 3).
2. **spec-pyforge-herald:CAP-46 and spec-pyforge-herald:CAP-62 say what Stories 50.3, 51.1 and 52.2 built.**
   Source: `test_public_contract.py` and `test_verify_claims_emit.py`, 47 passed on 2026-11-12; every check key
   spec-pyforge-herald:CAP-46 names is a key `docs-site/scripts/verify_claims.py` has (Story 50.2 AC8);
   `contract.md` § Repository keys names `roots.this` as Story 52.2 reads it. *Instance:* accept; both markers read
   `(shipped 2026-11-11)`.
3. **Six memlog entries no longer held.** Source: the change entries of 2026-11-12 on the Spec's memlog: two
   constraints and one assumption served spec-pyforge-herald:CAP-6's video production, which retired on 2026-11-10;
   the 2026-08-02 automation-trigger constraint was replaced by ruling 4's operator-run form; the "new export
   backends" non-goal was overtaken by spec-pyforge-herald:CAP-40..CAP-42 and spec-pyforge-herald:CAP-57; the
   2026-10-14 snapshot assumption was superseded on 2026-11-01. *Instance:* fixed (retired, not rendered).
   *Prevention:* a capability retirement names the memlog entries that served it in the same change.
4. **The Why's figures were 2026-09-09 figures, read as current.** Source: the pre-render SPEC.md (`cli.py` "1764
   lines wiring 26 subparsers"; the live-backend contract `in-progress`); `wc -l` and the `add_parser` count on
   2026-11-12 give 1,950 and 30. *Instance:* fixed by Story 50.2, each figure dated. *Prevention:* a figure in a Spec
   carries its date.

### Story boundaries (diff-scope review, inline)

5. **Story 52.1's marked set grew from 40 to 43 over two review rounds.** Source:
   `spec-52-1-herald-s-live-tree-readers-carry-the-live-tree-marker.md` § Review findings round 1, minor 2, and round
   2, minor 2: `test_deck_store_import_boundary.py`, `test_cli_epic6.py` and `test_cli_watch.py` fail off the tree
   but were in neither the story's `surface:` nor the plan's `files_owned`. *Instance:* fixed in round 2; Story 50.2's
   Story 52.1 reconcile line names all 43. *Prevention:* derive a marker story's file set by running the off-tree
   package half at mint, not by a grep of the module bodies (action 4).
6. **Two whole modules sit in the live-tree half for two tests.** Source: spec-52-1 § Review findings round 2, minor
   3: 39 pure CLI-dispatcher tests in `test_cli_epic6.py` and `test_cli_watch.py` leave B's package half because two
   tests read the flag tree. *Instance:* defer, `DW-herald-52-1-2` (written by Story 50.2). *Prevention:* none beyond
   the row.
7. **A herald error class missed the core exception root, and a later story's build found it.** Source:
   `spec-52-2-herald-s-landing-record-names-this-checkout-s-forge-and-its-package-names-python-3-14.md` § Gate
   findings; `0a47b5a7c4`: `ForgeSlugError(ValueError)` failed `spec-pyforge-core:CAP-5`'s guard
   `test_no_unreparented_exception_root`, which the BUILD-4 gate did not run. *Instance:* fixed
   (`ForgeSlugError(PyforgeError, ValueError)`). *Prevention:* already adopted: later wave gates run core's and the
   testing kit's suites every wave.
8. **The plan told Story 50.4 to re-key two attribute docstrings that the coverage gate reads as code.** Source:
   `spec-50-4-...` § Spec Change Log, second review of 2026-11-11: `transport/base.py:117` and
   `transport/mcp_transport.py:129` are string statements after an assignment, so `scripts/coverage_gate.py`'s
   `ast_fingerprint` counts them. *Instance:* fixed by keeping both (`DW-herald-50-4-1`, seven sites in all).
   *Prevention:* a comment-only sweep is planned from a tokenize and `ast` pass over each site, as the second review
   did.
9. **The closer could not write the `deferred:` frontmatter its own spec and four sibling specs ask for.** Source:
   Story 50.2's Intent (i) and the § Planned deferral sections of specs 50.3, 50.4, 52.1 and 52.2 ("Story 50.2 writes
   it ... and adds it to this spec's `deferred:` frontmatter"); the build rules of this change forbid editing another
   story's spec and adding a `deferred:` frontmatter entry. *Instance:* defer: Story 50.2 wrote the six ledger rows
   with the intake's fingerprint over each summary and location (`origin: spec-deferred <fingerprint>`), so a later
   frontmatter row dedupes against them; the frontmatter edit is the integrator's (action 1). The same finding is
   mason's finding 1 (`retro-pyforge-mason-2026-11-12.md`). *Prevention:* mint a closer with the `files_owned` for
   every row it is asked to write, or have each build record the row in its own body only (action 4).
10. **Story 50.2's own id list missed a row a sibling added at build.** Source: spec-50-2 Intent (i) names
    `DW-herald-52-1-1` but not `DW-herald-52-1-2`, which Story 52.1's round 2 review added (spec-52-1 § Review findings
    round 2, minor 3). *Instance:* fixed: Story 50.2 wrote every row the Planned deferral sections name, including
    `DW-herald-52-1-2`, and its review round 1 corrected AC10 to count it (the pattern gains `50-4-1` and `52-1-2`,
    and the count moves from 5 to 7). *Prevention:* a closer reads its
    siblings' Planned deferral sections, not only its own id list.

### Aggregate views

11. **Two new meta-tests of 653 and 993 lines.** Source: `git_evidence.py` `files`: `test_public_contract.py` net
    +993, `test_dossier_cutover_claims.py` net +653; `wc -l` today 993 and 653. Read: each is one oracle with its
    planted cases (50.3's walks the parser, the MCP face, the flag readers, every environment-read form and the error
    classes; 51.2's resolves each A→B claim against the steward ledger, the capability ledger and the flag tree).
    *Instance:* accept; the size follows the number of surfaces each oracle refuses. *Prevention:* none.
12. **No new import edge across stations.** Source: `git grep -n 'pyforge\.steward\|from pyforge\.(marshal|doctor|...)'`
    over `src/shared/packages/pyforge-herald/src` finds nothing; Story 52.2's only new import is
    `pyforge.core.cutover_root` and `pyforge.core.errors` (core's seam). `docs-site/scripts/verify_claims.py` is 153
    lines, inside herald:AD-23's 300-line bound. *Instance:* accept.
13. **One comment block repeated in 43 modules.** Source: Story 52.1's diff: the same three-line `pytestmark`
    comment naming `spec-pyforge-steward:CAP-175` above `pytestmark = pytest.mark.live_tree`. It is the fleet
    convention of steward Story 117.4, one marker per module. *Instance:* accept.

### Outside herald's surface

14. **Herald's live half reds on steward's preflight lane list.** Source: § Behavior verification, the second
    `pyforge-herald-live-test` run: `test_preflight_pages_lane.py` drives steward's `run_preflight` over the shipped
    lanes, which refuses because `pyforge-mason-coverage-gate` and `pyforge-warden-coverage-gate` depend on a test
    task no CI step runs. Neither `pixi.toml` nor `.github/workflows` is changed in the working tree, so the state is
    this branch's HEAD after the suite-split waves. *Instance:* defer to the wave gate and the steward unit (the
    split's CI jobs are steward Story 124.2's); herald's test asserts what it should. *Prevention:* a wave that adds a
    coverage-gate dependency runs herald's preflight-lane test in its gate.

## Behavior verification

- `pixi run --frozen -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/meta/test_public_contract.py
  src/shared/packages/pyforge-herald/tests/unit/test_verify_claims_emit.py -q`: exit 0, 47 passed (spec-pyforge-herald:CAP-62, spec-pyforge-herald:CAP-46).
- `pixi run --frozen -e pyforge-herald herald deck --help`: exit 0; the usage lists the 12 deck verbs from the parser
  (seed, pull, status, watch, push, publish, exports, sync-all, qa, pptx-spec, pptx-fill, pptx-native), and each
  verb's help names its folded capability ids (Story 50.3).
- `local_ship.this_forge_slug()` from the worktree root returns `rxm7706/local-recipes` (`roots.this` through
  `pyforge.core.cutover_root.forge_slug_for`); from `/tmp`, with no roster above, it raises the named
  `ForgeSlugError` and never falls back to a slug (Story 52.2).
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` (the package half): exit 0, 1524 passed, 5 skipped, 751
  deselected.
- `pixi run --frozen -e pyforge-herald pyforge-herald-live-test` (the live-tree half, with docs-site's npm install
  present in the worktree, so the built-site tests ran): first run with `TMPDIR` on tmpfs, exit 1 with 12 failed and
  17 errors, every one an Astro build that died on `EXDEV: cross-device link not permitted` renaming its output from
  `docs-site/.astro/` to the pytest temp directory (an environment trap, not a herald defect). Re-run with `TMPDIR`
  on the worktree's disk: exit 1, 750 passed and 1 failed. The one failure is
  `tests/meta/test_preflight_pages_lane.py::test_the_install_runs_before_herald_s_suite_in_one_slot_and_many`:
  steward's `run_preflight` refuses the shipped lane list before any lane starts, because
  `pyforge-mason-coverage-gate` and `pyforge-warden-coverage-gate` depend on a test task no CI step runs. That is
  the steward lane registry and the workflows at this branch's HEAD (neither is in this change's herald surface), not
  herald code; it is recorded for the wave gate (finding 14).
- Not exercised: `pixi run -e site pages-check` on the live dossier and `pyforge-herald-test-built` with
  `HERALD_DOCS_SITE_REQUIRED=1`; both are the wave gate's and CI's.

## Previous-retro follow-through

`implementation-artifacts/sprint-status.yaml` carries no `action_items` key (read 2026-11-12), so there was nothing
to follow through on by id. The prior retro, `retro-pyforge-herald-2026-10-11.md`, left three candidate fix stories as
prose (§ *Candidate fix stories (not minted here)*: dispatch refusals and a mint-time binding check, all marshal's) and
no tracked items; none is re-checked here.

## Action items

All proposed; none is applied by this retrospective.

| # | Action | Owner | Kind |
|---|---|---|---|
| 1 | Write the `deferred:` frontmatter rows that specs 50.2, 50.3, 50.4, 52.1 and 52.2 ask for, each with the summary and location of its ledger twin (`DW-herald-50-2-1`, `-50-3-2`, `-50-4-1`, `-52-1-1`, `-52-1-2`, `-52-2-1`), so the intake dedupes against the tracked rows. | change integrator | spec reconciliation |
| 2 | Re-key `registry.py:437`'s push-and-prove heading to spec-pyforge-herald:CAP-34 and migrate the README sections that carry it, in a feature story (`DW-herald-50-4-1`). | herald | remediation |
| 3 | Add a check that reds a station Spec missing Constraints, Non-goals or Assumptions, or citing a "below" or "see <section>" that resolves to nothing, and have a fold carry the folded Specs' typed memlog entries (constraint, non-goal, assumption), the folded Specs' untyped Constraints, Non-goals and Assumptions text, and the receiving Spec's untyped sections (station-level entries, residual dependencies) into the receiving memlog as typed entries (finding 1), under the Spec that owns the chain detectors. | doctor | process lesson |
| 4 | Mint a marker story's file set from an off-tree package-half run, and give a closer the `files_owned` for every row it is asked to write (findings 5, 9, 10). | marshal (plan mint) | process lesson |
| 5 | Pin a fixture flag tree for the two flag-tree tests and return `test_cli_epic6.py` and `test_cli_watch.py` to the package half (`DW-herald-52-1-2`). | herald | remediation |
| 6 | Recover the nine absorbed Specs' SPEC-text Constraints, Non-goals and Assumptions items at `4251c42229^` that no typed entry carries (54 bullets and 6 prose paragraphs) and the 58 archived constraint, non-goal and assumption entries: write each into herald's memlog as a typed entry with its provenance, retire it by a dated change entry, or rule it outside herald, then re-derive the three sections once (`DW-herald-50-2-2`, finding 1). Replaying the typed entries alone does not close it. | herald | spec reconciliation |

## Acceptance verdict

**Machine verdict: rejected** (headless, criteria declared in the epics and story specs). Forced by the rubric:
eight story keys of the three epics are not `done` in the feed (Epic summary). That is the state of record until the
change's CLOSE-LEDGERS job promotes them.

On the evidence alone, the declared criteria of the seven built stories hold: the oracles of spec-pyforge-herald:CAP-46 and spec-pyforge-herald:CAP-62 pass,
the deck help lists every verb from the parser, the landing record names this checkout's forge and refuses without a
roster, and each gap the audit named is either closed in this change or an open ledger row by ruling (`DW-FU-23-6-1`
and `DW-steward-43-6-1` not met; `DW-herald-egm-2026-11-01-1` open to the operator). No blocking finding stands. A
human may override to **accepted-with-open-items** once the keys are promoted; this run records no such decision.

## Open questions

- Should the integrator write the five specs' `deferred:` frontmatter rows (action 1), or should those specs read
  their deferrals from the ledger twins? Either answer closes finding 9; the build rules allowed neither to this run.

## Assumptions

- The epics were taken from the invocation (50, 51 and 52), not auto-detected; `detect-epic --epic <n>` returned
  `story_count` 4, 2 and 2 with every key in `pending_stories` (listed in Epic summary).
- The machine verdict is **rejected** because `pending_stories` was non-empty; no human decision was available.
- `bmad-review` was not invoked: each story had an independent review and a wave gate at build (the build commits
  say so), and the build rules of this change confine Story 50.2 to its own files. The diff-scope review ran inline
  over the story boundaries only (findings 5 to 10); the code lenses were not re-run over each hunk.
- The EGM drift stage of the skill's append steps applies to `pyforge-marshal` epics only, so it was skipped.
- Phase 5's `sprint_status.py update` was not run: this change writes no Tier-3 feed or ledger outside its
  CLOSE-LEDGERS job, so `epic-50-retrospective`, `epic-51-retrospective` and `epic-52-retrospective` stay as they are
  and the action items above are recorded here only.
- The document lives at `planning-artifacts/retros/retro-pyforge-herald-2026-11-12.md`, the path Story 50.2 names
  (the station's tracked retro home, which the chain-currency sweep reads), not the skill's default Tier-3 path.
