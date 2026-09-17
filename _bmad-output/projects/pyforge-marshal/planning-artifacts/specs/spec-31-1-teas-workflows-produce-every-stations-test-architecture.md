---
title: "TEA's workflows produce every station's test architecture"
type: 'feature'
created: '2026-09-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      Marshal's own generator-produced Story Coverage Matrix is nearly empty independent of
      TEA: 207 of 208 rows read "none observed" despite 181 real test files existing, because
      `_stories_linked_to_test`'s filename heuristic doesn't match this repo's real test-naming
      conventions.
    evidence: |-
      Confirmed by direct inspection of `_bmad-output/projects/pyforge-marshal/planning-artifacts/test-architecture.md`
      (207/208 "none observed" rows) and `_bmad/scripts/bmad_tea_playwright.py`'s
      `_stories_linked_to_test` (matches only `test_1_2_*`/`test_story_19_1_*`-shaped filenames).
      Pre-existing generator limitation, not a regression from this story.
    location: '_bmad/scripts/bmad_tea_playwright.py::_stories_linked_to_test'
    severity: low
  - summary: >-
      Herald and Doctor's generator-reported `story_count` (64, 73) disagrees with what each
      TEA run counted directly from their own `epics.md` (50, 113).
    evidence: |-
      Both TEA subagent runs independently read `epics.md` for their station and reported the
      differing counts; root cause not investigated (could be either side's parsing). Doctor's
      run additionally noted 108 of its 113 stories are already `done`/shipped, out of its own
      declared scope for this pass.
    location: '_bmad/scripts/bmad_tea_playwright.py (story-parsing regexes) vs epics.md for pyforge-herald and pyforge-doctor'
    severity: low
  - summary: >-
      Atlas's QA-effort estimate reconciliation (fixed this pass to match the detailed table)
      and Steward's/Doctor's manual risk-score-override notation (fixed this pass to a shared
      convention) are cosmetic; no sweep checks every station's remaining internal-consistency
      nits (e.g. whether every P0-P3 count in every station's Executive Summary matches its own
      detailed table) beyond what four independent reviewers happened to surface this pass.
    evidence: |-
      11 Blind Hunter + 4 Edge Case Hunter findings were verified and patched directly (see
      Review Triage Log); a full line-by-line audit of all 8 stations' ~250KB of TEA-generated
      prose for further such nits was not attempted -- out of proportion for advisory documents
      whose core claim (equivalence coverage) does not depend on internal cross-reference polish.
    location: 'all 8 stations'' test-design-architecture.md / test-design-qa.md'
    severity: low
baseline_revision: '1363b6c5ca'
---

<intent-contract>

## Intent

**Problem:** TEA (`bmad-testarch-*`) is now provisioned repo-wide (steward 46.3), but nobody has
proven whether its `bmad-testarch-test-design`/`-framework` workflows can actually replace the
hand-built `bmad_tea_playwright.py` generator's `test-architecture.md` for any of the 8 PyForge
stations — CAP-4 needs that proof, station by station, before Story 31.2 can retire anything.

**Approach:** Refresh the generator's baseline once more, then run `bmad-testarch-test-design`
for real (system-level, autonomous, via the Skill tool — never `render_skill.py`, per steward
46.3's disclosed format incompatibility) against all 8 stations, compare each station's output
against its baseline Story Coverage Matrix + Test Inventory for story-id/test-path coverage and
the TBD-free invariant, and record the per-station verdict in a single equivalence report.

## Boundaries & Constraints

**Always:** a station's `test-architecture.md` is only overwritten by a full equivalence pass for
that station (AD-5); TEA's own new documents are kept as additive artifacts regardless of
equivalence outcome; every run must be a genuine, grounded workflow execution (no fabricated
content) invoked via the Skill tool's native activation, substituting `_bmad/custom/config.toml`'s
`[modules.tea]` values for the missing `_bmad/tea/config.yaml` (a disclosed, reasonable
workaround, not a silent one); each station's `.bmad-config.toml` gains a `[tea]` table pinning
`test_architecture_path` and the current `test_architecture_writer` (AD-9, whose spine text
explicitly names this as the mechanism: "Each station's `test-architecture.md` has one writer
... and one path pinned in that station's `.bmad-config.toml`").

**Never:** never delete the generator, its pixi tasks, or its meta-tests in this story (that is
Story 31.2's own gated act, contingent on this report); never invoke `bmad-testarch-test-design`
through `render_skill.py` (confirmed incompatible by steward 46.3); never let a parallel
per-station subagent call `scripts/bmad-switch` (addressed every non-active station by physical
path instead, per this repo's parallel-agent convention); never claim a verification result
without directly re-checking it (an earlier draft of the equivalence report claimed "0 TBD
everywhere" from a partial spot-check — corrected to a full 32-file sweep after review).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| TEA config file missing | `_bmad/tea/config.yaml` absent (confirmed, repo-wide) | Substitute `_bmad/custom/config.toml`'s `[modules.tea]` values + `output_folder` from the target station's `.bmad-config.toml`; proceed | Disclosed in the equivalence report, not a silent workaround |
| Full story-id + test-path coverage for a station | TEA's output happens to name every baseline story id and test path | That station's `test-architecture.md` is regenerated from TEA's output; `.bmad-config.toml`'s `test_architecture_writer` flips to `tea` | N/A (did not occur for any of the 8 stations this pass) |
| Partial/no coverage for a station | TEA's risk-tiered template samples only a subset of stories (observed: 0-37% per station) | That station's generator output is kept unchanged; the gap is recorded in the equivalence report; CAP-4 narrows for that station | Recorded, not silent (AD-5) |
| `bmad-testarch-framework` applicability | No station has a Playwright/Cypress config or JS/TS E2E surface (confirmed repo-wide scan) | Not invoked live; applicability finding recorded in the equivalence report instead | N/A |
| A new planning-artifact shape is introduced fleet-wide | Doctor's `classify()`/`is_orphan_file()` have no rule for `test-design-*.md` / `test-design/` / `reviews/` | `test_bmad_artifacts_integrity` HARD-fails (`uncovered`) and the orphan-file hygiene check WARNs | Both classifiers extended with dated rules + new unit tests (this pass, post-review) |

</intent-contract>

## Code Map

- `_bmad/scripts/bmad_tea_playwright.py` -- the generator; `STATIONS` tuple, `OUTPUT_NAME`,
  `_stories_linked_to_test` (the weak filename heuristic behind the "Observations" deferred item),
  `parse_matrix_story_ids`/`check_station` (the CAP-5 drift-gate logic the equivalence check
  mirrors). Read, never edited, this story.
- `.claude/skills/bmad-testarch-test-design/{SKILL.md,workflow.yaml,instructions.md,steps-c/*,
  test-design-architecture-template.md,test-design-qa-template.md,test-design-handoff-template.md}`
  -- TEA's real skill; `workflow.yaml`'s `config_source: "{project-root}/_bmad/tea/config.yaml"`
  is the confirmed-missing file; the three templates confirmed structurally risk-tiered, no
  per-story matrix in any of them.
- `.claude/skills/bmad-testarch-framework/workflow.yaml` -- confirmed Playwright/Cypress-scoped
  (`default_output_file: "{test_dir}/README.md"`); applicability-checked, not invoked.
- `_bmad/custom/config.toml` `[modules.tea]` -- steward 46.3's unresolved-template config
  (`test_artifacts = "{output_folder}/planning-artifacts"` + 13 other TEA keys); the substitution
  source for every run this story performed.
- `_bmad-output/projects/<slug>/.bmad-config.toml` (all 8) -- gained a new `[tea]` table each
  (`test_architecture_path`, `test_architecture_writer = "generator"`).
- `_bmad-output/projects/<slug>/planning-artifacts/test-architecture.md` (all 8) -- refreshed once
  via `python _bmad/scripts/bmad_tea_playwright.py --all` (commit `1363b6c5ca`) as the equivalence
  baseline; unchanged after that (every station narrowed).
- `_bmad-output/projects/<slug>/planning-artifacts/{test-design-architecture,test-design-qa}.md`,
  `test-design/<slug>-handoff.md`, `test-design-progress-system.md` (all 8, new) -- TEA's real,
  kept output; marshal's four received a post-review pass removing an inaccurate "probe/draft,
  not adopted" framing left over from the initial investigatory run (see Review Triage Log).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/reviews/tea-equivalence-2026-09-07.md`
  (new) -- the consolidated equivalence report this story's AC names; corrected post-review for
  the TBD-invariant miscount (see Review Triage Log).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py::classify()` --
  post-review addition: five dated rules recognizing the new TEA test-design file shapes, fixing
  a real `test_bmad_artifacts_integrity` regression this story's new files caused.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/hygiene_definitions.py` --
  post-review addition: `test-design-architecture.md`/`test-design-qa.md`/
  `test-design-progress-system.md` added to `_CONVENTIONAL_FILENAMES`; `test-design`/`reviews`
  added to `_CONVENTIONAL_DIRECTORIES`, fixing a real orphan-file WARN regression.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/{prds/prd-pyforge-doctor-2026-07-25/prd.md,
  architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md}` -- post-review
  currency-cascade reconcile (chain-currency-sweep-check fired after the three governing specs'
  memlogs moved; no FR/AD content change, both re-stamped per the station's own established
  restamp convention).
- Three specs' `.memlog.md` (`pyforge-doctor/spec-bmad-drift-new-artifact-shape`,
  `spec-pixi-candidate-currency`, `spec-pyforge-doctor`) -- post-review reconcile entries +
  `scripts/.spec-surface-baseline.json` scoped re-stamps for the `factory.py`/
  `hygiene_definitions.py`/test-file changes above.

## Tasks & Acceptance

**Execution:**
- `_bmad-output/projects/*/planning-artifacts/test-architecture.md` (x8) -- refresh via the
  generator once more, as the equivalence baseline (done, commit `1363b6c5ca`).
- Invoke `bmad-testarch-test-design` for real (system-level, Skill tool, autonomous) against all
  8 stations; write its real output to each station's `planning-artifacts/` (done).
- `_bmad-output/projects/*/.bmad-config.toml` (x8) -- add `[tea]` with `test_architecture_path` +
  `test_architecture_writer` (done, all 8 record `"generator"`).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/reviews/tea-equivalence-2026-09-07.md`
  -- the equivalence report (done, corrected post-review).
- `factory.py::classify()` + `hygiene_definitions.py` -- recognize the new TEA file shapes so
  `pyforge-marshal-test`/`pyforge-doctor-test`/`detectors-ci` stay green (done, post-review).
- Doctor's PRD + architecture spine -- currency-cascade reconcile after the spec-surface
  memlog touches above (done, post-review).

**Acceptance Criteria:**
- Given TEA provisioned and the generator's last outputs kept, when `bmad-testarch-test-design`
  runs per station, then eight documents regenerate (real files: `test-design-architecture.md`
  + `test-design-qa.md` + `test-design/<slug>-handoff.md` per station) and the equivalence report
  names every station's story-id/test-path coverage against the generator baseline, with the
  TBD-free invariant held (verified: the generator's own hard-fail rule holds trivially since no
  station's `test-architecture.md` was regenerated; separately, TEA's own "owner: TBD" convention
  appears 7 times across 2 stations, disclosed and distinguished from a fabricated content gap).
- Given a failing equivalence for a station, when the report is written, then that station's
  generator output is kept unchanged and the gap is recorded, not silent -- true for all 8
  stations this pass; Story 31.2 is refused in full per its own spec, not silently.
- Given the new file shapes this story introduces, when `pyforge-marshal-test` / the pyforge-doctor
  meta-test suite / `detectors-ci` run, then all pass with zero findings attributable to this
  story's diff (verified post-review; two pre-existing, unrelated findings on the base branch are
  untouched).

## Spec Change Log

## Review Triage Log

### 2026-09-07 — Review pass
- verdicts: 21 findings — high 1, medium 5, low 12, false 3, maybe-false 0
- findings:
  - `[low]` `[patch]` Blind Hunter: Atlas's two companion docs disagreed on net-new effort (3 items/25-55h vs. the QA doc's own table totaling 2/12-25h) — verified real; fixed by aligning the architecture doc's Executive Summary to the QA doc's detailed table (the authoritative one).
  - `[low]` `[patch]` Blind Hunter: Atlas's P0-001 code example imported `playwright.sync_api` (unused) into a Dagster multiprocess-lock test, an un-adapted copy-paste from the WASM example above it — verified real; removed the mismatched import and comment.
  - `[low]` `[patch]` Blind Hunter: Doctor's R-3 risk-table Score cell embedded a prose explanation instead of a number, breaking every other row's Probability×Impact convention — verified real; reformatted to `2→4*` with the explanation moved to a footnote, matching Steward's own R-13 override notation (see the notation-consistency finding below).
  - `[low]` `[patch]` Blind Hunter: Doctor's Executive Summary garbled Epic 20's story-status breakdown ("3 backlog, 1 blocked, 1 backlog") — verified against the live sprint ledger (4 backlog, 1 blocked); fixed.
  - `[medium]` `[patch]` Blind Hunter (+ Edge Case Hunter, same root cause): the equivalence report's "TBD-free invariant held... 0 everywhere" claim was false — a direct `grep -c TBD` sweep found 7 real occurrences across atlas (4) and herald (3); Blind Hunter's own attribution of some of these to Doctor was independently checked and found false (Doctor has zero). Fixed: the report and spec now distinguish the generator's own hard-fail rule (holds trivially since no station was regenerated) from TEA's legitimate "owner: TBD" placeholder convention (7 real occurrences, disclosed with exact locations), and the file-count denominator (24 vs. the real 32 = 8 stations × 4 files) is corrected throughout.
  - `[low]` `[patch]` Blind Hunter: Mason's `test-design-qa.md` collapsed its Date/Author/Status/Project header onto one line, an unexplained deviation from every other station's four-line format — verified real; reformatted to match.
  - `[medium]` `[patch]` Blind Hunter: Scribe's R-006 (score 6) was placed under "HIGH PRIORITY" while the doc's own text says "4 high-priority (score ≥6)" and every other score-6 risk sits in Blockers — verified real; moved R-006 into Blockers as item 4.
  - `[low]` `[patch]` Blind Hunter: Scribe's Executive Summary said "P3 tests: ~6" while the detailed Test Coverage Plan enumerates only 3 P3 items and states "Total P3: ~3" — verified real; summary and the doc's own Total corrected to 3/42 (from 6/45).
  - `[medium]` `[patch]` Blind Hunter (+ Edge Case Hunter's independent R-2/R-11 findings, same station, different root causes — see below): Steward's R-13 used an ad hoc "3→6*" footnote notation for a manually-overridden score while Doctor used unmarked inline prose for the same kind of override, with no consistent fleet-wide convention — verified real; Doctor's R-3 (above) was reformatted to match Steward's asterisk+footnote convention, making the two consistent.
  - `[medium]` `[patch]` Blind Hunter: Warden's R-001 (score 9, the single highest-scored risk across all 8 stations' documents, labeled CRITICAL in its own Mitigation Plans section) was entirely absent from the "🚨 BLOCKERS" skim-level summary, which listed only three score-6 risks — verified real; added as Blockers item 1, renumbering the rest.
  - `[low]` `[patch]` Edge Case Hunter: all 7 non-marshal stations' `.bmad-config.toml` `[tea]` comments pointed to `planning-artifacts/reviews/tea-equivalence-2026-09-07.md` as a same-project-relative path, but the report only exists under pyforge-marshal — verified real; all 7 corrected to an explicit cross-project path.
  - `[medium]` `[patch]` Edge Case Hunter: Steward's `test-design-architecture.md`/`test-design-qa.md` cited "R-11" (Quick Guide item 3, Dependencies, QA checklist) but no R-11 row exists in any risk table — verified real (confirmed the risk IDs run R-1..R-10, R-12..R-19 with no R-11, and the cited content matches R-7's actual table row verbatim); all three citations corrected to R-7.
  - `[medium]` `[patch]` Edge Case Hunter: Steward's Quick Guide item 1 labeled the "package scope sprawl" risk as R-2, but that description matches R-1's table row verbatim, and the doc's real R-2 is an unrelated AD-5 boundary risk — verified real; Quick Guide item 1 relabeled R-1.
  - `[high]` `[patch]` Verification Gap: this story's 32 new files (8 stations × 4 file shapes) plus the marshal equivalence report have no matching rule in `pyforge.doctor.sources.factory::classify()`, so `test_bmad_artifacts_integrity` — an existing, normally-run meta-test — fails with 5 HARD `uncovered` findings for marshal's own new files (and the identical, currently-unwired-to-any-check defect exists for the other 7 stations' equivalent files, per `gather()`'s marshal-only scope, a pre-existing limitation not caused by this story). Verified live: the cited test failed before, passed after. Fixed: five dated `classify()` rules added (test-design-architecture.md, test-design-qa.md, test-design-progress-system.md, test-design/*-handoff.md, planning-artifacts/reviews/*.md) plus one new unit test; the broader "extend `gather()` to all 8 stations" suggestion is a separate, larger scope not required to fix this story's own regression and is not undertaken here.
  - `[false]` `[reject]` Intent Alignment: the diff's file-identity ("no file literally named test-architecture.md appears... 32 new files, not the 8 the Then clause names") and success-vs-failure ("the report documents the opposite... of a passing comparison") observations read as divergences from the story's literal Then clause — refuted: the story's own second sentence ("a failing equivalence... keeps that station's generator output... the story still completes with the report") is a co-equal, explicitly sanctioned escape hatch, not an exception path; the diff correctly implements it, verified empirically across all 8 stations rather than assumed.
  - `[false]` `[reject]` Intent Alignment: "partial execution of the When" (`bmad-testarch-framework` never run live) reads as an unmet clause — refuted: the equivalence report explicitly discloses this as a reasoned applicability-check (no Playwright/Cypress surface exists anywhere in the repo to scaffold, confirmed by a repo-wide scan), not a silent gap.
  - `[medium]` `[patch]` Intent Alignment: marshal's own four TEA documents carried an explicit "PROBE OUTPUT, not yet reviewed or adopted" framing (author/status lines, a stale "scoped to marshal only, the other 7 pending" Not-in-Scope row, a mis-set `workflowStatus: in-progress` frontmatter field, and several body passages describing the run's own limitations in first-person "probe" language) while the structurally identical documents for the other 7 stations carried no such caveat, despite this story treating all 8 as equally adopted, kept artifacts — verified real; every such passage reworded to match the other 7 stations' professional, adopted framing, and the stale Not-in-Scope row corrected to reflect that all 8 stations were in fact run.
  - `[false]` `[reject]` Intent Alignment: the `.bmad-config.toml` `[tea]` table is "a new, story-unspecified mechanism... unverifiable against [the story text] since CAP-4 itself lives in `spec-bmad-suite-lifecycle`, a document outside this diff" — refuted: `spec-bmad-suite-lifecycle`'s own `ARCHITECTURE-SPINE.md` AD-9 explicitly names this exact mechanism ("Each station's `test-architecture.md` has one writer... and one path pinned in that station's `.bmad-config.toml`"), one layer up from the story bullet itself; cited directly in this spec's Boundaries & Constraints.

## Design Notes

**Why all 8 stations were run for real instead of extrapolating from one:** the story's own AC
requires "eight documents regenerate" and a per-station verdict; the structural
template-shape argument (risk-tiered, not story-enumerating) predicts narrowing everywhere, but
station-specific content (how MANY stories get named, whether any station's risk profile happens
to touch every story) could only be confirmed by actually running it -- and it was: coverage
density varied 0%-37% by station, none reaching the "every story id" bar.

**Why `bmad-testarch-framework` was applicability-checked instead of run 8 more times:** its own
`workflow.yaml` names a Playwright/Cypress JS/TS scaffold as its sole purpose; a repo-wide scan
(no `playwright.config.*`/`cypress.config.*` anywhere, the only two `package.json`s already using
Vitest or being non-test build deps) confirms it has nothing to initialize for any of the 8
Python-CLI stations. Spending substantial tokens x 8 more runs to independently rediscover
"nothing to do" per station would not have produced new information the story's own report needs.

**Why the `.bmad-config.toml` `[tea]` table, not a code change:** AD-9 of
`spec-bmad-suite-lifecycle`'s architecture spine explicitly calls for "one path pinned in that
station's `.bmad-config.toml`" as the governance mechanism recording which of `test-architecture.md`
(generator) or a future TEA-authored equivalent is canonical per station -- this pass records
`test_architecture_writer = "generator"` everywhere, since equivalence narrowed for all 8.

**Why the classify()/hygiene fixes and PRD/arch currency reconcile landed inside this story
rather than as a follow-up:** both were real regressions this story's own new files caused
(verified live, not theoretical), and `pyforge-marshal-test` is this story's own stated
Verification gate -- leaving them for later would land the story against a red suite.

## Verification

**Commands:**
- `grep -c TBD` on all 32 TEA-produced documents (8 stations x 4 files) -- expected and confirmed: 7 occurrences across atlas (4) and herald (3), 0 everywhere else -- disclosed, not a silent gap.
- `git status --short` -- expected: only the new TEA-output files + the 8 `.bmad-config.toml` edits + the equivalence report + the refreshed `test-architecture.md` baselines + the post-review classify()/hygiene/PRD/arch/memlog files are staged/committed; no existing `epics.md`/`sprint-status-ledger.yaml` touched.
- `pixi run -e pyforge-marshal pyforge-marshal-test` -- expected and confirmed: 7510 passed.
- `pixi run -e pyforge-doctor pyforge-doctor-test` -- expected and confirmed: 1344 passed (1343 + 1 new).
- `pixi run -e local-recipes pytest .claude/skills/conda-forge-expert/tests/meta/test_bmad_artifacts_in_sync.py::test_bmad_artifacts_integrity` -- expected and confirmed: failed before the classify() fix (5 HARD uncovered), passes after.
- `python3 scripts/chain_currency_sweep_check.py` -- expected and confirmed: red after the spec-surface memlog reconciles (doctor's PRD/arch fell behind), green after the PRD/arch currency-cascade restamp.
- `pixi run -e local-recipes detectors-ci` -- expected and confirmed: the only two remaining findings (`dream-chain` re: `bmad-cursor-interactive-routing`, `spec-surface` re: `pyforge-steward/spec-pyforge-steward`) touch zero files in this story's diff -- pre-existing on the base steward branch.
- Manual: read `_bmad-output/projects/pyforge-marshal/planning-artifacts/reviews/tea-equivalence-2026-09-07.md` and confirm all 8 stations have a named verdict.

## Auto Run Result

Status: done

**Summary:** Ran TEA's `bmad-testarch-test-design` for real against all 8 PyForge stations
(system-level mode, autonomous, invoked via the Skill tool per steward 46.3's disclosed
`render_skill.py` incompatibility), substituting `_bmad/custom/config.toml`'s `[modules.tea]`
values for the confirmed-missing `_bmad/tea/config.yaml`. Every run produced real, grounded
content, but TEA's risk-tiered templates structurally cannot enumerate every story id or test path
the mechanical generator's Story Coverage Matrix / Test Inventory does -- confirmed empirically
(0%-37% story-id density per station, 0 literal test-file-path matches anywhere) -- so the
equivalence check narrows CAP-4 for all 8 stations. Every station's `test-architecture.md` stays
generator-authored, refreshed once as the equivalence baseline; TEA's own documents are kept as
new, additive artifacts. Each station's `.bmad-config.toml` gained a `[tea]` table pinning the
writer (AD-9). `bmad-testarch-framework` was applicability-checked rather than run live 8 more
times. A 4-reviewer pass (Blind Hunter, Edge Case Hunter, Verification Gap, Intent Alignment)
found and this pass fixed: a false "TBD-free everywhere" claim in the equivalence report (7 real,
disclosed occurrences in 2 stations), a marshal-only "not yet adopted" framing inconsistent with
the other 7 stations' equal treatment, 9 internal-consistency nits across 6 stations' documents
(mismatched effort estimates, a mis-adapted code example, broken risk-ID cross-references,
inconsistent score-override notation, a missing top-risk blocker entry), and one real regression
in an existing repo-wide meta-test (`test_bmad_artifacts_integrity`) plus a real orphan-file
hygiene WARN, both fixed at the classifier level with new unit test coverage, triggering a
downstream chain-currency cascade reconcile on Doctor's PRD and architecture spine (no FR/AD
content change).

**Files changed:**
- `_bmad-output/projects/*/planning-artifacts/test-architecture.md` (x8) -- refreshed (generator
  rerun, commit `1363b6c5ca`).
- `_bmad-output/projects/*/planning-artifacts/test-design-architecture.md`,
  `test-design-qa.md`, `test-design/<slug>-handoff.md`, `test-design-progress-system.md` (x8
  stations, new) -- real TEA output; marshal's four corrected post-review (see triage log).
- `_bmad-output/projects/*/.bmad-config.toml` (x8) -- new `[tea]` table each; 7 corrected
  post-review for the cross-project report path.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/reviews/tea-equivalence-2026-09-07.md`
  (new) -- the equivalence report; corrected post-review for the TBD-invariant miscount.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/sprint-status-ledger.yaml` -- flip
  `31-1-tea-s-workflows-produce-every-station-s-test-architecture` to `done`.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py`,
  `hygiene_definitions.py`, `tests/unit/test_sources_factory.py`,
  `tests/unit/test_hygiene_definitions.py` -- post-review fix for the new-file-shape regressions.
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md`,
  `architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md` -- post-review
  currency-cascade reconcile (no FR/AD change).
- Three specs' `.memlog.md` under `pyforge-doctor/` -- post-review reconcile entries;
  `scripts/.spec-surface-baseline.json` -- scoped re-stamps for the above.

**Review findings breakdown** (this pass, 21 findings from 4 independent context-free reviewers):
- Patched (1 high, 5 medium, 6 low; two more low findings share the notation-consistency fix):
  the classify()/hygiene regression (high); the false TBD-invariant claim, the marshal
  probe-disclaimer inconsistency, Scribe's risk-bucket misplacement, Steward's two broken R-11/R-2
  cross-references, Warden's missing top blocker (medium); Atlas's effort-estimate mismatch and
  mismatched code example, Doctor's broken score math and garbled Epic 20 wording, Mason's header
  formatting, Scribe's P3 count, the fleet-wide score-override notation inconsistency, and the
  `.bmad-config.toml` cross-station comment path (low).
- Rejected (3, all `false`): two Intent Alignment observations that the diff's escape-hatch
  reading and the framework-applicability disclosure were divergences from intent, both refuted by
  the story's own explicit escape-hatch clause and the report's own disclosure; one claim that the
  `.bmad-config.toml` mechanism is unverifiable against intent, refuted by AD-9's spine text.
- Deferred (3, all low, pre-existing or genuinely out of proportion): the generator's own weak
  story-to-test-file linkage; the herald/doctor story-count discrepancy; the residual possibility
  that further internal-consistency nits exist in the ~250KB of TEA-generated prose beyond what
  four reviewers surfaced.

**Follow-up review recommendation: false.** The one `high` finding (classify()/hygiene regression)
was verified fixed live (the cited tests fail-before/pass-after); no other patched entry was
`high`, and fewer than two `medium` entries share an unverified risk profile — each medium fix was
independently verified (grep counts, direct file reads, live test runs). No specific unverified
risk can be named.

**Verification performed:** `grep -c TBD` on all 32 documents (7 real occurrences, disclosed);
`pixi run -e pyforge-marshal pyforge-marshal-test` (7510 passed); `pixi run -e pyforge-doctor
pyforge-doctor-test` (1344 passed); `test_bmad_artifacts_integrity` (fail-before/pass-after,
directly observed); `python3 scripts/chain_currency_sweep_check.py` (red-before/green-after, all
8 stations current); `pixi run -e local-recipes detectors-ci` (only 2 pre-existing, unrelated
findings remain); `git status` after every per-station TEA run confirmed no existing file was
modified and the active project was never switched mid-run.

**Residual risks:** none rated medium or higher. The three low-severity `deferred` items above are
pre-existing generator observations or genuinely out-of-proportion further-polish work, not
blocking.
