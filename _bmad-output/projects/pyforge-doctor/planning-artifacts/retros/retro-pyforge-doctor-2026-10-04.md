---
title: 'pyforge-doctor — Retrospective (Epic 41: Phases 4 and 5 of the deferral burn-down)'
project: pyforge-doctor
epic: 41
date: '2026-10-04'
created: '2026-10-04'
updated: '2026-10-04'
verdict: accepted-with-open-items
criteria: declared
headless: true
scope: 'Epic 41, Stories 41.1-41.5 (all done at retro time), landed 2026-10-03 to 2026-10-04. Written as the reconciler half of the chain-currency sweep: the code stage moved on 2026-10-04 (Story 41.4 edited the package pyproject.toml) past the 2026-09-20 retro, so the code->retro feeds edge fired.'
evidence:
  - 'git log --first-parent 5bb7952118..bdacbb283e -- src/shared/packages/pyforge-doctor (five merges: b19bbe9402 41.1, 62842523a4 41.5, 15925ced4c 41.2, bc562fc6b8 41.3, a9253f7efc 41.4)'
  - '.claude/skills/bmad-retrospective/scripts/git_evidence.py --range 5bb7952118..bdacbb283e --stories 41.1,41.2,41.3,41.4,41.5'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-41-{1..5}-*.md (intent, ACs, Review Triage Log, Auto Run Result)'
  - '_bmad-output/projects/pyforge-doctor/implementation-artifacts/dispatch-runs/pyforge-doctor-2026100{3,4}T*/journal.jsonl (seven Epic 41 dispatch runs)'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md (row statuses read with a parser, 2026-10-04)'
  - 'pixi run --frozen -e pyforge-guild detectors-ci; chain-completeness-check; chain_currency_sweep_check.py --project pyforge-doctor (run on origin/main 1d62151fe2)'
---

# pyforge-doctor — Retrospective (Epic 41)

## Epic summary

**Epic.** Epic 41, *Phases 4 and 5 of the deferral burn-down: doctor's medium and low deferrals*
(`epics.md` § Epic 41). The operator ruled on 2026-10-03 that every open medium deferral is fixed, each fix
also closes the lows in the modules it touches, and no row closes without a landed fix, a `resolution:` and a
cited `verified:` line. Four package-area stories (41.1-41.4) placed 106 rows. Story 41.5 joined on 2026-10-04
at the operator's request (a new story reopens its done epic).

**Diff range.** `5bb7952118..bdacbb283e`: from `main` just before the 41.1 merge to the ledger promotion after
the 41.4 merge. The range also carries other stations' parallel work (369 commits, 97 merges). The doctor share
is the five first-parent merges above: 22 files under `src/pyforge/doctor/` (+2480/−677) and 30 test files
(+2895/−157).

**Stories.** All five are `done` in the tracked ledger (`sprint-status-ledger.yaml` rows `41-1-…` to `41-5-…`);
`detect-epic` reported no pending story at retro time.

| Story | Landed | Path to `main` | Review on record |
|---|---|---|---|
| 41.1 chain sources | `b19bbe9402` (PR #1795) | two dispatches, both landings refused (MRS-DISP-038 unknown conflict path in the marshal memlog; MRS-DISP-020 not mergeable), then hand-landed from `land/pyforge-doctor-41-1` | review pass, then two independent landing reviews; the first sent it back on three highs |
| 41.2 ledger sources | `15925ced4c` (PR #1838) | first dispatch stopped partway and set the spec `blocked`; unblocked (`97416bb777`) and re-dispatched; that landing refused (MRS-DISP-056, `steward-test` red), then merged | review pass by the build |
| 41.3 board/factory/hygiene | `bc562fc6b8` (PR #1847) | first dispatch stopped partway and set the spec `blocked`; unblocked (`bdf705f450`) and re-dispatched; landed | **none**: the tracked spec's Review Triage Log reads "No review has run yet" |
| 41.4 check CLI/score/bmad-method | `a9253f7efc` (PR #1850) | one dispatch, landed clean | review pass by the build |
| 41.5 epic reopen | `62842523a4` (PR #1826) | built by hand in the chain PR | independent adversarial review, sent back twice, fixed |

Every dispatch ran on Cursor, model `composer-2.5-fast` (each run's `dispatch-launch` payload), per the
2026-10-03 operator ruling in `marshal-policy.toml`.

**Deferred-work rows.** Of the 106 rows the four stories named, 104 are closed. The two left open,
`DW-FU-23-6-2` and `DW-FU-30-3`, both need a `bmad-spec` render of `spec-pyforge-doctor/SPEC.md`; Story 41.2's own
Always clause leaves them for the operator's render. Story 41.1 minted two new rows, `DW-doctor-41-1-1` (medium)
and `DW-doctor-41-1-2` (low), both open with their reasons recorded.

**Evidence inventory.** Available: the five tracked story specs, the seven dispatch journals, the ledger, the
deferred-work ledger, and the detector runs above. Missing: the dispatch session transcripts (`session.log` holds
the supervisor's view only), so the reason each Cursor session stopped is known from its `dispatch-blocked`
reason alone.

## Findings

### Spec-to-implementation reconciliation

1. **Story 41.3 made INV-A blind to the one-chain fold's citation window.** Six station Specs now read
   `spec-not-decomposed` FAIL on `main`: atlas, doctor, marshal, scribe, steward and warden (warden's is
   CAP-2, CAP-5..22). Source: `chain-completeness-check` on `1d62151fe2`, detail section.
   - **Cause.** `_extract_decomposition_prose` (`sources/board.py:393`) now keeps only the sections that
     `_DECOMP_SECTION_OPEN_RE` (`sources/board.py:242`) opens: `## Epic N`, `## Capabilities` /
     `## Scope (capabilities)`, `### Story N`. Introduced in `26a298ed12` (`wip: 41.3`), landed with
     `bc562fc6b8`. Before it, each file's prose ran from its first `## ` heading.
   - **What it dropped.** Each station's `epics.md` carries a `## Fold provenance (2026-09-17)` section that
     cites `spec-pyforge-<station> CAP-1..N` and calls itself "the INV-A citation window". The one-chain pilot
     made that the sanctioned remedy (`docs/governance/spec-one-chain-per-station/.memlog.md`, 2026-09-16
     pilot lesson 11: add a `## Fold provenance` window; `DEFERRED_SPECS` is the wrong hatch).
   - **Measured.** Re-run with the pre-41.3 slicing: zero findings. Re-run with the 41.3 allowlist plus
     `## Fold provenance`: zero findings. The shipped status of the CAPs plays no part.
   - **Disposition.** Fix now: Story 41.6.
   - **Prevention.** 41.3's AC named only the negative cases (a `## Changelog` leak, a heading-less file). No
     test pinned that a real citation window still counts, and no live-tree test measured INV-A.
2. **41.3's DW-CHAIN-COMPLETENESS-4 fix is right in kind.** It allowlists decomposition headings, as that row's
   own suggested redesign asked. The defect is one missing heading. Disposition: keep the allowlist (41.6 adds
   to it).

### Verification gap

3. **No Epic 41 gate measured a detector on the live tree.** Every story's `## Verification` lists only
   `pyforge-doctor-test` and `lint-types` (doctor's `verify_commands`, MRS-GATE-010). The dispatch gate
   therefore could not see 41.3's INV-A regression. The station suite has a live-tree pattern for this
   (`tests/unit/test_sources_board.py` `test_live_tree_reports_zero_spec_status_missing`), but INV-A had none.
   - **Disposition.** Fix now: 41.6 adds the live-tree test.
   - **Prevention.** A story that changes a detector's predicate adds a live-tree test of that detector's
     finding.
4. **Story 41.3 landed with no review on record.** Its tracked spec ends with "No review has run yet" and an
   Auto Run Result of `in-review`, while its frontmatter and the ledger read `done`. The landing did not wait for
   an independent review (behavioural guideline 8). The regression in finding 1 is the kind such a review
   exists to catch.
   - **Disposition.** Defer to the per-station review batch the operator set up on 2026-10-03 for follow-up
     reviews.
   - **Prevention.** Proposed to marshal: a landing refuses a story spec whose Review Triage Log records no
     review.

### Process lessons

5. **The Cursor fast model stopped partway on both L-size stories it could not finish in one session.**
   - **41.2.** Its first dispatch (`…T133719516Z-076e5cfc`) set the spec `blocked` with the core fixes green
     and seven acceptance rows still open.
   - **41.3.** Its first dispatch (`…T165545900Z-dead565a`) did the same: "factory/hygiene/docs_shelf/fleet_scan
     deferrals and ledger closures remain".
   - **The remedy worked both times.** The operator's session unblocked the spec to `in-progress` (MRS-DISP-045
     recorded in the spec) and re-dispatched on the same branch. The second session finished from the first
     one's work.
   - **41.1 and 41.4 finished in one session.** Both are also L. Rows per story (27, 24, 27, 28) do not by
     themselves predict a stop.
   - **Disposition.** Accept, recorded.
   - **Prevention.** Expect one re-dispatch per L story on `composer-2.5-fast`. Keep the
     unblock-and-re-dispatch remedy rather than re-scoping a partial branch.
6. **The detectors summary row hid five of six FAILs.** `scripts/detectors.py:346` takes a detector's last
   output line as its summary. The `chain-completeness` row on `main` therefore names warden alone, and the
   first triage of this regression scoped it to warden.
   - **Disposition.** Defer.
   - **Prevention.** Read a red detector's detail section, never the summary row alone. Proposed: the summary
     names the finding count.
7. **Story 41.4's `pyproject.toml` edit fired the `code→retro` edge.** It raised the hatchling floor for
   `DW-1-1-3`. `scripts/fleet_scan.py` dates doctor's code stage by that file's last commit, so the edge fired
   at 2026-10-04 against the 2026-09-20 retro.
   - **Disposition.** Fixed by this retro.
   - **Prevention.** Close an epic whose stories touch the package `pyproject.toml` with its retro inside the
     2-day grace window.

8. **`sprint-ledger-sync --repair-feed` drops the feed's `action_items`.** Found while recording this retro.
   - **What happened.** The feed still read `epic-41: in-progress` after the 41.4 landing had rolled the twin to
     `done`, so minting 41.6 refused as an un-finish. `--repair-feed` reconciled that stale row, but
     `repair_feed` (`scripts/promote_sprint_status.py:282-284`) rewrites everything after
     `development_status:`. It deleted the `action_items` block the retro skill had just appended. The block was
     re-added with the skill's own script.
   - **Disposition.** Defer to marshal, which owns the script (`spec-pyforge-marshal`).
   - **Prevention.** `repair_feed` keeps every top-level key after the status block.

### Aggregate views

9. **`sources/chain.py` keeps growing.** It went from 5712 to 6372 lines (41.1, +813/−153). It was already
   doctor's largest module. Disposition: accept for now, recorded.
10. **The spec-surface parser lives twice.** One copy is in `scripts/spec_surface_check.py`, the other in
   `sources/chain.py`. Story 41.1 pinned the two together with parity tests
   (`test_stamp_script_parse_surface_matches_chain`, `test_stamp_script_glob_to_re_matches_chain`) rather than
   sharing one. Disposition: accept; the parity tests red any drift.
11. **One frontmatter reader now serves every doctor reader.** Story 41.3 consolidated five readers that used to
    disagree. This is a consolidation win.

## Behavior verification

Run on `origin/main` `1d62151fe2` in this worktree:

- **`chain-completeness-check`** exits non-zero with six `spec-not-decomposed` FAILs (finding 1).
- **Monkeypatched re-runs.** With `_extract_decomposition_prose` restored to the pre-41.3 slicing, INV-A reports
  zero findings. With `## Fold provenance` added to the allowlist, it also reports zero.
- **`chain_currency_sweep_check.py --project pyforge-doctor`** exits 1 with `staleBy`
  `{feeds, code, retro, 2026-10-04, 2026-09-20}`.
- **`pyforge-doctor-test`** passes on the same tree (3407 passed, 1 skipped). The suite is green while the detector
  is red: finding 3.

The epic's other runtime behaviour (the check CLI, score, ledger sources) was not re-exercised here beyond the
station suite. Each story's own Auto Run Result records its runs.

## Previous-retro follow-through

The feed (`implementation-artifacts/sprint-status.yaml`) carries no `action_items` key. There is nothing to
follow through by selector. The 2026-09-20 retro's two carry-forwards were prose:

- **Run `lint-types` before pushing.** Landed: every Epic 41 story spec records `lint-types` exit 0.
- **Drop an unused `# type: ignore` when seen.** Not checked: no evidence gathered.

## Action items

Proposed unless marked minted. The human decides what executes.

| # | Action | Owner | Kind |
|---|---|---|---|
| 1 | Story 41.6: add the `## Fold provenance` heading to INV-A's decomposition allowlist (`sources/board.py` `_DECOMP_SECTION_OPEN_RE`), with a fixture, a live-tree test and a mutation check | doctor | remediation, **minted** in the same PR as this retro |
| 2 | Independent review of Story 41.3 in the per-station review batch | operator | review |
| 3 | A landing refuses a story spec whose Review Triage Log records no review | marshal | process (proposed) |
| 4 | A story that changes a detector predicate adds a live-tree test of that detector's finding | doctor | process; 41.6 applies it |
| 5 | The `detectors.py` summary row names the finding count, not only the last line | doctor | remediation (proposed) |
| 6 | Render `spec-pyforge-doctor/SPEC.md` with `bmad-spec` to close `DW-FU-23-6-2` and `DW-FU-30-3` | operator | spec reconciliation |
| 7 | Rule on `DW-doctor-40-1-2` (high, unverified); schedule `DW-doctor-41-1-1` (medium) | operator | decision |
| 8 | `sprint-ledger-sync --repair-feed` keeps the feed's `action_items` block | marshal | remediation (proposed) |

## Acceptance verdict

**accepted-with-open-items** (criteria declared, rendered headless with no human decision).

- **Stories.** Every story's declared ACs pass in the station suite and are recorded in its spec, and all five
  stories are `done`.
- **Rows.** 104 of the 106 named rows closed, each with a `resolution:` and a `verified:` line. The two open rows
  are left open by 41.2's own Always clause.
- **Open items.** Finding 1, a live regression outside 41.3's ACs as written, is tracked as Story 41.6. Finding 4
  (no review on 41.3) is deferred to the review batch.
- **Override.** A human may override to `rejected` on the ground that 41.3's AC ("only real decomposition
  citations count") also implies real citations still count.

## Open questions

- **The INV-A finding text says "uncovered by any epic or FR".** Since 41.3, a citation in a PRD's requirement
  section no longer counts: PRD headings are not in the allowlist. With the fold window restored, no live CAP
  depends on a PRD-only citation, so 41.6 leaves it. A ruling decides between two fixes: admit PRD requirement
  sections, or reword the finding.

## Assumptions

- **Epic.** Selected from the invocation: Epic 41.
- **Completeness.** `detect-epic --epic 41` returned no pending story before Story 41.6 was minted. 41.6 is added
  to Epic 41 after this retro and reopens it; it is an output of this retro, not a story the retro skipped.
- **Verdict.** Rendered on the evidence with no human decision.
- **Action items.** Each is a proposal. Only item 1 is minted, as the task that produced this retro asked.
- **Sprint status.** The skill's `sprint_status.py update` set `epic-41-retrospective: done` and appended the eight
  action items to the Tier-3 feed. `sprint-ledger-sync` carried the retro key to the tracked twin; the twin does not
  carry `action_items`.
- **Format.** No team discussion (Phase 3) ran. `bmad-review` was not re-run over the epic diff; the diff-scope
  lenses lean on each story's own recorded review, and on finding 4 where none exists.
