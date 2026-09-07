---
title: 'bmad-eval-quality builds a __win variant'
type: 'feature'
created: '2026-09-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
baseline_revision: 'a35c8218566ff2a0c37e72380de7f42f0d70fe57'
context: []
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** `recipes/bmad-eval-quality/recipe.yaml` already scaffolds Windows support
(`if: win`/`if: unix` run selectors, `build.bat` with the `call`-for-`.cmd`-shims
convention, `conda-forge.yml`'s `noarch_platforms: [linux_64, win_64]`) from its
original authoring (Story 45.1, commit `97675b5dc1`), but only the `__unix` noarch
variant was ever actually built and uploaded to SelfExplainML (commit `6d092e571c`
pinned it unix-only in `pixi.toml`'s target tables with the comment "the `__win`
one needs a Windows build"). Nobody has produced a real Windows build to date.

**Approach:** Verify the recipe is fully Windows-build-ready (it already is —
confirm, don't guess), bump `build.number` (0 → 1) to mark this as a new,
re-verified build revision per house convention (same-version content change ⇒
bump build number), re-verify the recipe still builds green natively
(`recipe-build`, which on this Linux host means the linux-64 leg — this repo's
own `local_builder.py::build_all_platforms` deliberately short-circuits noarch
recipes to the native platform only, so no local tool here can actually execute
`build.bat` under real `cmd.exe`; that is why Windows CI / a real Windows machine
and the anaconda upload are explicitly the operator's step per the Epic 14
binding, not something this story can complete), and land the CFE-required
Rule 2 retrospective. Update the cross-project `install-matrix.md` hazard cell
to describe the current, more-precise state (recipe is win-ready; the win-64
artifact itself has not been built/uploaded yet).

## Boundaries & Constraints

**Always:**
- Go through the `conda-forge-expert` skill for any recipe.yaml/build script
  judgment calls (CLAUDE.md Rule 1).
- Keep the upstream commit pin `0.2.0.dev0 @ 3172162f` exactly as-is — it is
  explicitly out of scope per the Epic 14 HARD boundary.
- Land a CFE retrospective before calling this story done (CLAUDE.md Rule 2),
  even if the finding is "existing guidance held, one clarifying gotcha added."

**Never:**
- Do not attempt to actually execute `build.bat` or fabricate a win-64 build
  artifact/upload — there is no Windows execution environment available here,
  and the Epic explicitly reserves the anaconda upload for the operator.
- Do not move the `bmad-eval-quality` pin out of `pixi.toml`'s linux-64/osx-arm64
  target tables into the shared table, and do not regenerate `environment.yaml`
  — both are conditioned on the win-64 artifact actually existing on the
  channel, which this story does not produce. `tests/packaging/test_bmad_suite_full_feature.py::test_eval_quality_pin_lives_in_the_unix_target_tables`
  must keep passing unchanged.
- Do not touch `recipes/bmad-suite/suite-members.yaml` (the story's own Surface
  note: "unchanged row").
- Do not claim `steward suite pipeline-truth` reports 3-platform coverage —
  that is contingent on the operator's future upload, not this story.

</intent-contract>

## Code Map

- `recipes/bmad-eval-quality/recipe.yaml` -- `build.number: 0` bumps to `1`;
  `if: win`/`if: unix` run selectors and `noarch: generic` already correct
  (added at authoring time, Story 45.1); CFE metadata block near the bottom
  (`cfe-local-build-datetime`, `cfe-last-checked`) gets refreshed to today's
  verification pass.
- `recipes/bmad-eval-quality/build.bat` -- already uses `call` for every
  `npm`-shim invocation (`call npm ci ...`, `call npm run build`); verified
  correct, no change expected, but re-read fully in step 3 before concluding
  that.
- `recipes/bmad-eval-quality/build.sh` -- unix build script, unchanged;
  re-verify it still matches `build.bat`'s structure (same `INSTALL_DIR`
  layout, same files copied) after any edits to either.
- `recipes/bmad-eval-quality/conda-forge.yml` -- `noarch_platforms: [linux_64,
  win_64]` already present (required by CFE gotcha G111 whenever a noarch
  recipe carries `if: unix`/`if: win` selectors); no change expected.
- `.claude/skills/conda-forge-expert/scripts/local_builder.py` (read-only
  reference) -- `build_all_platforms()` (~line 472) short-circuits any
  `noarch` recipe to the native platform only; this is why "builds green
  locally via recipe-build" can only mean the linux-64 leg in this repo,
  never a real win-64 execution. This is the CFE retro's likely finding.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-channel-product/install-matrix.md`
  line 20 -- the `bmad-eval-quality` row's Hazards cell currently has no
  win-64 caveat at all (unlike the `bmad-module-skill-forge` row above it,
  which says "linux-64 only — the one gap, closed"); add an analogous note
  describing the current state honestly (recipe win-ready, artifact not yet
  built/uploaded).
- `tests/packaging/test_bmad_suite_full_feature.py::test_eval_quality_pin_lives_in_the_unix_target_tables`
  (read-only reference, ~line 149) -- asserts the pin stays in the unix
  target tables; must keep passing since `pixi.toml` is untouched this pass.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` + `SKILL.md` -- Rule 2
  retro landing spot; current version `v8.86.4`, next PATCH `v8.86.5` (no
  behavior-changing gotcha discovered beyond documenting the noarch
  short-circuit limitation, which is a refinement/addition, not a
  correction).
- `_bmad-output/projects/pyforge-mason/planning-artifacts/sprint-status-ledger.yaml`
  line 40 -- `14-1-bmad-eval-quality-builds-a-__win-variant: backlog` flips to
  `done` once verified complete.

## Tasks & Acceptance

**Execution:**
- `recipes/bmad-eval-quality/recipe.yaml` -- bump `build.number: 0` → `1`;
  refresh `cfe-last-checked` / `cfe-local-build-datetime` to the verification
  run's actual date/platform -- marks this as a re-verified, Windows-ready
  build revision per house convention (same-version content change ⇒ bump
  build number).
- `pixi run -e local-recipes recipe-build recipes/bmad-eval-quality` -- run
  and confirm green -- proves the bumped build.number doesn't regress the
  linux-64 leg (the only leg this environment can actually execute).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-channel-product/install-matrix.md`
  -- update the `bmad-eval-quality` row's Hazards cell to note the recipe is
  Windows-build-ready but the win-64 artifact is not yet built/uploaded --
  keeps the cross-project hazard tracking accurate (the story's own named
  Surface item).
- `.claude/skills/conda-forge-expert/CHANGELOG.md` + `SKILL.md` -- land the
  Rule 2 retro entry (version bump + dated summary) -- CLAUDE.md's always-on
  closeout requirement for any BMAD effort touching conda-forge work.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/sprint-status-ledger.yaml`
  -- flip `14-1-...` from `backlog` to `done` -- reflects real completion
  state once the above lands and verifies green.

**Acceptance Criteria:**
- Given the recipe's `noarch_platforms`/`if: win`/`if: unix`/`call`-shim
  scaffolding (already correct from authoring), when `build.number` is bumped
  to `1` and `recipe-build` is run locally, then the build succeeds on
  linux-64 with no new lint/selector errors.
- Given `pixi.toml`'s existing unix-only target-table placement, when this
  story's changes land, then
  `test_eval_quality_pin_lives_in_the_unix_target_tables` still passes
  unchanged (pin is not moved).
- Given the Epic 14 HARD boundary that anaconda upload is the operator's
  step, when this story completes, then no win-64 artifact is claimed built
  or uploaded, and `install-matrix.md` accurately reflects "win-ready,
  not yet uploaded" rather than "closed."
- Given CLAUDE.md Rule 2, when this story's conda-forge work concludes, then
  the CFE skill CHANGELOG carries a dated retro entry and the skill version
  is bumped per semver.

## Spec Change Log

## Review Triage Log

### 2026-09-06 — Review pass
- verdicts: 11 findings — high 3, medium 1, low 5, false 2, maybe-false 0
- findings:
  - `[high]` `[patch]` (blind-hunter) Sprint ledger flips `14-1-bmad-eval-quality-builds-a-__win-variant` to `done`, but the story's own AC ("Then the pixi pin can leave the target tables, `steward suite pipeline-truth` reads the member current on all three platforms after the operator uploads") is unmet — no `__win` artifact was built/uploaded, `pixi.toml`'s pin is untouched. Verified real: precedent story 45.1 (identical shape — recipe authored/built green locally, upload not yet done) was kept `in-progress` in commit `97675b5dc1` and only flipped to `done` in `6d092e571c`, the SAME commit that recorded the actual operator upload. Action: revert the Tier-3 feed and tracked ledger to `in-progress`.
  - `[high]` `[patch]` (verification-gap) Same defect, independently found: no automated check in the repo (checked `pyforge.doctor.sources.marshal::gather_story_status`, `sources.ledger::gather`/`gather_direction`) reads a story's recorded AC before accepting `done`, so this false-done would go undetected. Action: same fix as above (revert to `in-progress`).
  - `[high]` `[patch]` (intent-alignment) Same defect, independently found via descriptive divergence analysis: the diff's real accomplishment (re-verify win-readiness, bump build.number, land a CFE retro) is narrower than the AC's closing Then-clauses (pin leaves target tables; pipeline-truth reads 3 platforms), and the diff's own CHANGELOG text admits neither happened this pass. The continued pass of `test_eval_quality_pin_lives_in_the_unix_target_tables` is evidence the intended reversal was NOT reached, not evidence of correctness. Action: same fix as above (revert to `in-progress`); root cause traced to this spec's own Tasks & Acceptance section instructing the `done` flip — a bad instruction in the spec, not the implementer's error, but the fix is a trivial one-line revert with no new surface, so it routes to patch rather than bad_spec.
  - `[medium]` `[patch]` (edge-case-hunter) v8.86.5 is labeled "(PATCH...)" despite adding a brand-new numbered gotcha (G114). CLAUDE.md Rule 2 item 4 ("MINOR for new gotchas / new sections") and this file's own v8.86.0 precedent ("MINOR ... three new gotchas G111-G113") require MINOR. Verified: confirmed both the rule text and the v8.86.0 precedent line are as claimed. Action: renumber `8.86.4 -> 8.86.5` to `8.86.4 -> 8.87.0` across CHANGELOG.md, SKILL.md, MANIFEST.yaml, config/skill-config.yaml (+ label PATCH -> MINOR), regenerate failure-catalog.yaml if it embeds the version, and update the two memlogs that cite "v8.86.5".
  - `[low]` `[patch]` (blind-hunter) SKILL.md's Version History bullet for this version omits the `config/failure-catalog.yaml` regeneration follow-through that CHANGELOG.md's TL;DR paragraph for the same version records — the two "twin" records diverge. Verified: confirmed by direct comparison of both files. Action: add the matching one-sentence follow-through note to SKILL.md's bullet (bundled into the same edit as the version renumber above).
  - `[false]` `[reject]` (blind-hunter) Claimed the diff breaks a "one-commit-per-PATCH-bump" convention by folding two commits under one version. Refuted: v8.86.2's own CHANGELOG entry already reads "... in companion commits" (plural), establishing that a version bump spanning more than one commit is normal, pre-existing practice; the "follow-through" addendum here is transparently labeled with its own commit reference, not a violation.
  - `[low]` `[patch]` (blind-hunter) `install-matrix.md` was edited (new Windows hazard sentence) but `spec-bmad-suite-channel-product`'s own `.memlog.md` got no matching note, unlike the parallel edits under the other two specs this diff touches. Verified: confirmed the memlog has no new entry; confirmed via `scripts/.spec-surface-baseline.json` that this spec's bucket carries `files: {}` (nothing there is governed by content-hash, so `spec-surface-check` does not flag it — low, not a functional risk) but the omission still breaks this diff's otherwise-consistent convention. Action: add one dated memlog line documenting the install-matrix.md edit, matching the style already used in `spec-bmad-eval-quality`'s memlog.
  - `[false]` `[reject]` (blind-hunter) Claimed a missing deferred-work-ledger entry for the leftover AC gap. Refuted: deferred-work-ledger entries track residual gaps in CLOSED/done work; once the ledger correctly reads `in-progress` (per the fix above), the open remainder is already signaled by the story's own status — a separate deferred-work entry would be redundant, not required.
  - `[low]` `[patch]` (blind-hunter) `pixi.toml`'s two `bmad-eval-quality` pin comments (~lines 1791, 1812) still read "...the `__win` one needs a Windows build), so win-64 is excluded" without noting the recipe itself is now re-verified win-ready (only the actual Windows build/upload is outstanding) — a future maintainer reading only this comment could believe the recipe code isn't win-ready. Verified: confirmed both occurrences read identically and unchanged by this diff. Action: reword both to state the recipe is win-ready and only the artifact/upload is outstanding, matching `install-matrix.md`'s wording.
  - `[low]` `[reject]` (blind-hunter) G114's Symptom section is a hypothetical reasoning trap rather than a concrete observed error/output, unlike G111-G113, weakening `failure-catalog.yaml`'s automated symptom matching. Real but not worth fixing: a "concrete" symptom would have to be fabricated (none was actually observed — this is a silent tooling-gap gotcha, not a build-time error), and the existing text already carries distinctive keywords (`call`, `cmd.exe`, `if: win`) per the reviewer's own account; rewriting further is stylistic churn with no functional gain.
  - `[low]` `[reject]` (blind-hunter) `install-matrix.md`'s `bmad-eval-quality` row is now ~861 characters, much longer than any other row, harder to scan. Real but not worth fixing here: a fix would mean restructuring the table's column schema, a larger and more speculative change than this story's scope warrants.

## Design Notes

No non-obvious design decisions — this is a small, mechanical recipe
finalization pass; the substantive judgment call (what's actually completable
here vs. reserved for the operator) is already resolved above in Intent/
Boundaries, tracking the Epic 14 spec's own explicit HARD boundaries.

## Auto Run Result

**Summary of implemented change:** `recipes/bmad-eval-quality/recipe.yaml`'s `build.number` bumped 0 -> 1 and its CFE metadata timestamps refreshed, re-verifying that the recipe's pre-existing Windows-readiness (`if: win`/`if: unix` selectors, `call`-safe `build.bat`, `conda-forge.yml` `noarch_platforms: [linux_64, win_64]` — all authored in Story 45.1) still holds and still builds green on linux-64 via `recipe-build`. A CFE Rule-2 retrospective landed (new gotcha G114: this repo's `local_builder.py::build_all_platforms()` short-circuits every noarch recipe to its native platform, so a green `recipe-build` for an `if: win`/`if: unix` noarch recipe only ever proves the native leg, never the untested other-OS branch). `install-matrix.md`'s hazard cell and `pixi.toml`'s pin comments were updated to describe the current, honest state. No `__win` artifact was built or uploaded (no Windows execution environment exists here; that stays the operator's step per the Epic 14 HARD boundary), so the pixi pin was NOT moved out of the unix-only target tables, and the story's ledger status was corrected to `in-progress` (not `done`) after independent review caught the initial implementation marking it complete — matching this repo's own precedent (Story 45.1 stayed `in-progress` until the commit that recorded the actual operator upload).

**Files changed** (9 commits, `a35c8218566ff2a0c37e72380de7f42f0d70fe57`..`83d8c29d4f95b1b423ce75cc671392b7cb9f1d00`):
- `recipes/bmad-eval-quality/recipe.yaml` -- `build.number` 0 -> 1; `cfe-last-checked`/`cfe-local-build-datetime` refreshed.
- `.claude/skills/conda-forge-expert/{CHANGELOG.md,SKILL.md,MANIFEST.yaml,config/skill-config.yaml}` -- Rule 2 retro, v8.86.4 -> v8.87.0 (MINOR, corrected from an initial mislabeled PATCH), new gotcha G114.
- `.claude/skills/conda-forge-expert/config/failure-catalog.yaml` -- regenerated for G114 (114 rows).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-channel-product/install-matrix.md` -- `bmad-eval-quality` row's Hazards cell gained a Windows-readiness note.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/sprint-status-ledger.yaml` + Tier-3 `implementation-artifacts/sprint-status.yaml` -- `14-1-...` set to `in-progress` (corrected from an initial, wrong `done`).
- `pixi.toml` -- both `bmad-eval-quality` pin comments (linux-64/osx-arm64 target tables) reworded to reflect win-readiness without overclaiming shipped status.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml` + `.memlog.md` -- `brief_mirrored_through` advanced across three retro commits; `pyforge-steward/spec-bmad-eval-quality/.memlog.md` + `spec-bmad-suite-channel-product/.memlog.md` -- dated notes for this story's edits.
- `scripts/.spec-surface-baseline.json` -- scoped re-stamps for every touched spec bucket (9 buckets in the final reconciliation pass, including 6 unrelated specs that share `pixi.toml` governance and drifted from the comment reword -- matches precedent commit `59713a7cf2`).

**Review findings breakdown** (11 findings across 4 independent layers — Blind Hunter, Edge Case Hunter, Verification Gap, Intent Alignment Auditor):
- **Patched (7, across two rounds):** (1) [high, 3 converged rows] ledger falsely marked `done` -- reverted to `in-progress`. (2) [medium] skill version mislabeled PATCH for a new gotcha -- renumbered 8.86.5 -> 8.87.0 (MINOR). (3) [low] SKILL.md/CHANGELOG.md twin-record divergence (missing follow-through note) -- synced. (4) [low] `spec-bmad-suite-channel-product` memlog missing a note for its own edit -- added. (5) [low] stale `pixi.toml` pin comments -- reworded. Plus an 8th patch found during my own post-patch verification (not one of the original 11, so not in the triage-log count): `068b84c673`'s CFE-surface touch left `campaign-state.yaml`'s `brief_mirrored_through` unmirrored, failing `cfe_rebuild_guard_check` -- fixed by advancing both slices' pointers.
- **Rejected as false (2):** "two commits under one version bump breaks convention" -- refuted by existing precedent (v8.86.2's own "companion commits" plural). "missing deferred-work-ledger entry" -- refuted: deferred-work tracks gaps in closed work; an `in-progress` story doesn't need one.
- **Rejected as low/not worth fixing (2):** G114's symptom text is reasoning-based rather than a concrete error string (fixing it would mean fabricating a symptom that was never observed). `install-matrix.md`'s row is now long/hard to scan (fix would need a table-schema change, out of proportion to this story's scope).

**Follow-up review recommendation: true.** Patched entries included `high`-severity ones (the false-`done` ledger status). Specific unverified risk: the patches themselves (ledger revert, semver renumber, and the `cfe_rebuild_guard_check` mirror fix) were applied by the same subagent that made the original mistakes, and re-verified by the orchestrating agent's own diff inspection plus detector/test re-runs -- not by a fresh, independent 4-layer review pass. A follow-up review pass would confirm these specific patches from a genuinely independent vantage point.

**Verification performed:**
- `pixi run -e local-recipes recipe-build recipes/bmad-eval-quality` -- green, linux-64, build 1, tests pass.
- `python -m pytest tests/packaging/test_bmad_suite_full_feature.py` -- 9/9 passed, including `test_eval_quality_pin_lives_in_the_unix_target_tables`.
- `pixi run -e pyforge-mason pyforge-mason-test` -- 1579 passed, 3 deselected (re-run twice, before and after the final fix).
- `pixi run -e local-recipes test-skill --meta` -- 7617 passed, 3 pre-existing skips.
- `pixi run -e local-recipes spec-surface-check` / `story-status-check` -- clean (re-run after every commit round).
- `pixi run -e local-recipes detectors-ci` (18 detectors) -- all clean except the pre-existing, unrelated `dream-chain` finding (`bmad-cursor-interactive-routing`, owner=marshal). `cfe_rebuild_guard_check` failed after the semver-renumber commit (unmirrored retro) and was independently caught and fixed before this pass closed.
- Every commit's diff (all 9, since `baseline_revision`) read directly, not just the implementer's self-report.

**Residual risks:**
- No `__win` artifact exists on the channel; the pixi pin, `environment.yaml`, and `steward suite pipeline-truth`'s 3-platform read all remain exactly where they were before this story (unix-only) -- correctly reflected by the `in-progress` status, not a defect.
- G114's characterization of `local_builder.py`'s noarch short-circuit is derived from reading the code, not from an observed Windows CI failure -- logically sound but unproven by an actual failed run.
- The `platform-ci-test` pixi env warn (unrelated, pre-existing, environmental) and the `bmad-drift` gotcha-count warn (expected after any new gotcha, owned by marshal's separate SYNC-RUNBOOK reconciliation loop) are both advisory and untouched.

## Verification

**Commands:**
- `pixi run -e local-recipes recipe-build recipes/bmad-eval-quality` -- expected: build succeeds (green), matching the linux-64 result already recorded from the original authoring pass.
- `pixi run -e pyforge-mason pyforge-mason-test` -- expected: unaffected station test suite stays green (this story does not touch pyforge-mason's own CLI code).
- `python -m pytest tests/packaging/test_bmad_suite_full_feature.py -k eval_quality` -- expected: `test_eval_quality_pin_lives_in_the_unix_target_tables` still passes.

**Manual checks (if no CLI):**
- Read `recipes/bmad-eval-quality/build.bat` end-to-end and confirm every
  `.cmd`/`.bat`-shim invocation (`npm`) is `call`-prefixed (already true;
  confirm, don't just trust the spec's Code Map).
- Read the updated `install-matrix.md` row and confirm it does not overclaim
  (no "closed", no "3-platform" wording) — it must read as "ready, not yet
  shipped."
