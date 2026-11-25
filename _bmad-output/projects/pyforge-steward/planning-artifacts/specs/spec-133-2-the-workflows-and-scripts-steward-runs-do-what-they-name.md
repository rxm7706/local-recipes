---
title: '133.2: The workflows and scripts steward runs do what they name'
type: 'fix'
created: '2026-11-25'
status: 'done'
story: 133-2-the-workflows-and-scripts-steward-runs-do-what-they-name
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '.github/workflows/**'
  - 'scripts/pre_push_preflight.sh'
  - 'scripts/fleet_poll_sync.sh'
  - 'scripts/fleet-poll-hourly.sh'
  - 'scripts/bump_pixi_version.py'
  - 'scripts/pixi_version_registry.py'
  - 'scripts/pages_changes.py'
  - 'scripts/sync-upstream-conda-forge.sh'
  - 'pixi.toml'
  - 'environment.yaml'
  - 'docs/how-to/pixi-tasks.md'
  - '_bmad-output/projects/pyforge-marshal/planning-artifacts/development-guide.md'
  - 'tests/scripts/**'
  - 'src/shared/packages/pyforge-steward/tests/unit/test_pages_changes.py'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-steward-review-2026-11-24-2` lists twelve defects in repo tooling steward runs or owns. The session lead confirmed eight by line:

1. `.github/workflows/sync-pypi-mappings.yml:83,133` compares the boolean input `create_pr` to the strings `'true'` and `'false'`, so neither publish step may run on the default dispatch.
2. `scripts/pre_push_preflight.sh:137` calls a pixi task `preflight`; the task is `preflight-budget`, and `|| true` hides the error, so the budget report never prints.
3. `scripts/fleet_poll_sync.sh:33` runs `git push --ff-only`, which is not a push option; `2>/dev/null || true` hides the error.
4. `scripts/fleet-poll-hourly.sh:28-42` sleeps to the next half hour and then a further hour, so it ticks every two hours.
5. `pixi.toml` task `sync-upstream-public-fork` runs `scripts/sync-public-fork.sh`, which does not exist.
6. 36 `setup-pixi` steps carry no `pixi-version` (29 in `pyforge-station-tests.yml`; the row counted 35).
7. `scripts/bump_pixi_version.py:112-119` opens `environment.yaml` for writing before the export runs, so a failed export leaves it empty.
8. `scripts/pages_changes.py:96,136` mixes the committer's offset with UTC, so the changes page can date an entry after its own snapshot.

A reviewer reported four more, not re-traced:

9. `scripts/platform-golden-path-promotion.sh:30` records the image ID as the registry digest.
10. `scripts/sync-upstream-conda-forge.sh` pops a stash unconditionally.
11. Five workflows have no `permissions:` block.
12. `.claude/hooks/post-tool-call.py` is registered nowhere.

**Approach:** Reproduce each defect first, by a test under `tests/scripts/` that fails on the unchanged tree or by a command whose output shows it, and record that in the Spec Change Log. Then fix inside this surface: read `inputs.create_pr` as a boolean; call `preflight-budget`; drop `--ff-only`; tick once an hour; remove the dead task (no commit ever held its script, so there is nothing to restore) and the one row of marshal's `development-guide.md` that documents it; pin `pixi-version` at every `setup-pixi` step and register each new site so `pixi-version-check` holds it and `bump-pixi-version` moves it; write the export to `environment.yaml` only on exit 0; use one zone for both dates. Items 10 and 11 are fixed the same way once reproduced. A defect the tree does not reproduce is recorded here as not a defect.

Two items are not fixed by this story (session lead's rulings, 2026-11-25):

- **Item 9 is left open, carried to a new deferred-work row by the lead.** The script does write the local image ID under `images.*.digest`, but a registry digest exists only after a push and the push is optional, so what that field means is an operator decision. This story changes no code for it, writes no test for it, and `scripts/platform-golden-path-promotion.sh` is not in its surface.
- **Item 12 is outside this surface.** The hooks directory is not edited in this change; the finding (the file exists and no harness registers it) is recorded here and carried to the open hook row `DW-steward-review-2026-11-24-4`.

Ledger key: `133-2-the-workflows-and-scripts-steward-runs-do-what-they-name`.

### Living CAP citations

- spec-pyforge-steward CAP-175, CAP-167 and CAP-168 (realized, no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce before fixing: one failing test or one shown command per defect, written down first.
- A `pixi.toml` task change regenerates `docs/how-to/pixi-tasks.md` and `environment.yaml` through their own tasks, in the same change.
- Write `pixi.lock` only if a dependency moved; a task-table edit moves none.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never turn the mapping sync's schedule back on, and never dispatch a workflow to test it.
- Never change what `pages_changes.py` anchors its window on: the built commit, never the clock.
- Never edit a file under `.claude/` in this story.
- Never fix a defect that did not reproduce.
- Never change `scripts/platform-golden-path-promotion.sh`, or what `images.*.digest` records, in this story: item 9 waits on the operator's decision.

## Acceptance Criteria

**Given** `DW-steward-review-2026-11-24-2` lists eight defects the lead confirmed by line and four a reviewer reported
**When** each of the ten this story fixes (1 to 8, 10 and 11) is first reproduced by a test under `tests/scripts/` or a command that fails on the unchanged tree, and then fixed inside this surface
**Then** the default dispatch of the mapping sync reaches its publish step, the pre-push hook prints the budget report, the fleet sync pushes with a flag git has and ticks once an hour, every pixi task names a file that exists, every `setup-pixi` step pins the workspace's pixi version and `pixi-version-check` knows the site, a failed export leaves `environment.yaml` as it was, and the changes page dates every entry and its snapshot in one zone
**And** an earlier stash survives the upstream sync on a clean tree, and every workflow states its token permissions
**And** a defect the tree does not reproduce is recorded on this spec as not a defect; item 9 is recorded as left open, carried to a new deferred-work row by the lead; the unregistered hook file (item 12) lies under `.claude/`, outside this surface, so the story records what it found and it is carried to `DW-steward-review-2026-11-24-4`

- **AC1 — Defects 1, 5, 6, 7, 10 and 11 are held by tests in the scripts suite.** New tests under `tests/scripts/` fail by name on: a workflow `if:` that compares a boolean input to a string; a pixi task whose `cmd` names a script that does not exist; a `setup-pixi` step with no `pixi-version`; an `environment.yaml` changed by a failed export; a `git stash pop` with no stash of its own; a workflow with no `permissions:` at the workflow or the job. Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test
  ```

- **AC2 — Defect 2: the hook calls a task that exists.** Expected: exit 1 (no line matches).

  ```bash
  grep -n -E "pyforge-guild preflight( |$)" scripts/pre_push_preflight.sh
  ```

- **AC3 — Defect 2: the budget report prints.** Expected: exit 0 in a checkout whose `.steward/preflight-runs.jsonl` holds a run (the hook calls the task only after a green `pr-preflight`, which writes one); exit 2, "cannot evaluate", in a checkout with no journal, which is the task's documented answer and not a failure of this story. That the hook calls the task after a green preflight is held by `test_the_pre_push_hook_prints_the_budget_report_after_a_green_preflight` (AC1's suite).

  ```bash
  pixi run --frozen -e pyforge-guild preflight-budget
  ```

- **AC4 — Defect 3: the fleet sync uses no push flag git lacks.** Expected: exit 1 (no line matches).

  ```bash
  grep -n -E "push +--ff-only" scripts/fleet_poll_sync.sh
  ```

- **AC5 — Defects 3 and 4: the fleet sync's tests pass**, with one that fails by name on a loop that sleeps more than an hour between ticks. Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_fleet_poll_sync.py -q
  ```

- **AC6 — Defect 6: every pin site agrees.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild pixi-version-check
  ```

- **AC7 — Defect 8: one zone for both dates.** The test fails by name on an entry dated after its snapshot. Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_pages_changes.py -q
  ```

- **AC8 — Defect 5: the generated task page matches `pixi.toml`.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild docs-pixi-tasks -- --check
  ```

- **AC9 — The workflow tests in steward's suite pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```

- **AC10 — Every defect of the row has its line.** For each of the twelve defects, the Spec Change Log holds one line: "reproduced and fixed" with the test or command that showed it on the unchanged tree; "not a defect" with the command that showed the tree does not reproduce it; or "left open" with the decision needed and who makes it (items 9 and 12). A defect recorded as not a defect or left open has no AC above to meet. Expected: prints 12, exit 0.

  ```bash
  grep -c -E "defect (1[0-2]|[1-9]): (reproduced and fixed|not a defect|left open) - " _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-133-2-the-workflows-and-scripts-steward-runs-do-what-they-name.md
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-175, CAP-167 and CAP-168 (realized, no text change); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the review's lower-severity defects are reproduced, then fixed or closed); operator ruling of 2026-11-25.
- Epic: Epic 133, minted with this story.
- Ledger key: `133-2-the-workflows-and-scripts-steward-runs-do-what-they-name`.
- Deferred-work row: `DW-steward-review-2026-11-24-2`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."133"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry and the operator's ruling of the same date. Not implemented.
- 2026-11-25: session lead's rulings applied to this spec. Item 9 is left open on an operator decision and carried to a new deferred-work row by the lead: its AC1 test clause is removed and `scripts/platform-golden-path-promotion.sh` leaves the surface. Item 12 is outside this surface and carried to `DW-steward-review-2026-11-24-4`. AC10's record words are now "reproduced and fixed", "not a defect" and "left open". AC3 states the task's exit 2 in a checkout with no preflight journal. Item 6 counts 36 steps, as the tree had. The one `development-guide.md` row that documented the removed pixi task joins the surface.
- 2026-11-25: defect 1: reproduced and fixed - `tests/scripts/test_workflows_and_scripts_do_what_they_name.py::test_no_workflow_compares_a_boolean_input_to_a_string` and `::test_a_boolean_input_s_default_is_a_boolean` failed on the unchanged tree, naming `sync-pypi-mappings.yml` lines 83 and 133 and its string default. Both `if:` now read `inputs.create_pr` as a boolean and the default is `true`. No workflow was dispatched; the schedule stays off.
- 2026-11-25: defect 2: reproduced and fixed - `pixi run --frozen -e pyforge-guild preflight --budget` exited 127 on the unchanged tree (no such task), and `::test_the_pre_push_hook_runs_only_pixi_tasks_that_exist` and `::test_the_pre_push_hook_prints_the_budget_report_after_a_green_preflight` failed. The hook now runs `preflight-budget`.
- 2026-11-25: defect 3: reproduced and fixed - `tests/scripts/test_fleet_poll_sync.py::test_fleet_poll_sync_pushes_the_loop_branch_to_origin` failed on the unchanged tree: a `loop/*` commit ahead of its bare remote was never pushed, git refusing `push --ff-only` behind `2>/dev/null || true`. The flag is dropped; `::test_fleet_poll_sync_uses_no_push_flag_git_lacks` holds the text.
- 2026-11-25: defect 4: reproduced and fixed - `tests/scripts/test_fleet_poll_sync.py::test_fleet_poll_hourly_never_sleeps_more_than_an_hour_between_ticks` failed on the unchanged tree: with a clock stopped at :30:00 the loop slept 7200 seconds between ticks. The trailing `sleep 3600` is removed.
- 2026-11-25: defect 5: reproduced and fixed - `::test_every_pixi_task_names_a_script_that_exists` failed on the unchanged tree, naming only `sync-upstream-public-fork`; `git log --all -- scripts/sync-public-fork.sh` is empty, so there was nothing to restore. The task table is removed, `docs/how-to/pixi-tasks.md` is regenerated, `environment.yaml` exports byte-identical, and the row that documented the task leaves marshal's `development-guide.md`.
- 2026-11-25: defect 6: reproduced and fixed - `::test_every_setup_pixi_step_pins_the_pixi_version` and `::test_every_setup_pixi_step_is_a_registered_pin_site` failed on the unchanged tree: 36 steps in six workflows carried no `pixi-version` (the row said 35). Each is pinned to `v0.80.0` and registered in `scripts/pixi_version_registry.py`; `pixi-version-check` reads 23 sites, clean.
- 2026-11-25: defect 7: reproduced and fixed - `::test_a_failed_export_leaves_environment_yaml_as_it_was` and `::test_an_export_that_cannot_run_leaves_environment_yaml_as_it_was` failed on the unchanged tree, which left `environment.yaml` at zero bytes. The export is captured and written only on exit 0. In the same file, the image check's blind `except Exception` is narrowed to the failures that mean "could not check" (`::test_an_image_check_that_cannot_run_is_unverified_not_failed`, `::test_an_image_check_does_not_swallow_a_programming_error`) and the file gets the executable bit its shebang names.
- 2026-11-25: defect 8: reproduced and fixed - `src/shared/packages/pyforge-steward/tests/unit/test_pages_changes.py::test_no_entry_is_dated_after_its_snapshot` failed on the unchanged tree: a merge committed at 2020-02-14T20:00:00-08:00 gave a snapshot of that day and an entry dated 2020-02-15. `generated_at` is now the built commit's committer time in UTC, the zone of every entry; the window still anchors on that commit.
- 2026-11-25: defect 9: left open - `scripts/platform-golden-path-promotion.sh:30` does write the local image ID (`docker inspect --format='{{.Id}}'`) under `images.*.digest`, unchanged and untested here. Decision needed, by the operator: what `images.*.digest` means when the registry push is optional (a registry digest exists only after a push). Left open, carried to a new deferred-work row by the lead.
- 2026-11-25: defect 10: reproduced and fixed - `::test_the_upstream_sync_leaves_an_earlier_stash_alone_when_the_tree_is_clean` failed on the unchanged tree: on a clean tree the unconditional `git stash pop` applied the operator's earlier stash. The script pops only when its own `git stash` moved `refs/stash`; `::test_the_upstream_sync_restores_the_changes_it_stashed` holds the other direction.
- 2026-11-25: defect 11: reproduced and fixed - `::test_every_workflow_states_its_token_permissions` failed on the unchanged tree, naming `ci-canary.yml`, `test-all.yml`, `test-linux.yml`, `test-macos.yml` and `test-windows.yml`. Each now states `permissions: contents: read`; none writes with the token.
- 2026-11-25: defect 12: left open - outside this surface (the hooks directory is not edited in this change). Found: `.claude/hooks/post-tool-call.py` exists and `grep -c post-tool-call .claude/settings.json .cursor/hooks.json` prints 0 for both, so no harness runs it, though conda-forge-expert's `tests/unit/test_provenance_hook.py` tests it. Decision needed, by the session lead under the open hook row `DW-steward-review-2026-11-24-4`: register it as a PostToolUse hook or retire it with its tests.
- 2026-11-25: still naming the removed task, not edited by this story: `.claude/skills/conda-forge-expert/quickref/commands-cheatsheet.md:746` (under `.claude/`; a conda-forge-expert edit with its CHANGELOG entry, for the lead to place).
- 2026-11-25: the story is implemented and in review: ten defects reproduced and fixed, two left open as written above.
- 2026-11-25: closed. PR #2385 merged as 080f89c4df (`Merge pyforge-steward/133-1 into main`) after its 51 CI checks passed and the full local `pr-preflight` exited 0 on 48 lanes; an independent reviewer read the diff against this spec before the merge, its findings were applied and re-reviewed.
