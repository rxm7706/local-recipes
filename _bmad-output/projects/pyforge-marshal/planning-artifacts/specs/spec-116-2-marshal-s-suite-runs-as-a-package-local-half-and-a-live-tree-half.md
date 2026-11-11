---
title: "116.2: Marshal's suite runs as a package-local half and a live-tree half"
type: 'chore'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: heavy
story: '116.2'
spec: pyforge-marshal
surface:
  - src/shared/packages/pyforge-marshal/tests/**/*.py
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-marshal/pyproject.toml
  - src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Steward and Doctor split their suites; steward's trigger map still lists marshal as unsplit (`test_station_tests_trigger_map.py:1782`, `UNSPLIT_ON_A_PLANNING_EDIT = {"marshal"}`). The package half a second repository could run does not exist yet.

**Approach:** The module list is derived, not chosen: run steward's `derive_reads` (`test_station_tests_trigger_map.py:1046`) over marshal's job and mark exactly the modules with an outside read or a root hand-off; the regex pre-count finds 35 candidate modules (1289 tests). A candidate with 20 tests or fewer is marked whole; one with more is split as Story 116.1 does (only its reading tests move to `*_live_tree.py`): here `test_promote_sprint_status_regressions.py` (36), `test_landing_ci_pauses.py` (23) and `test_repo_root.py` (22); the four largest (`test_dispatch_landing.py` 137, `test_dispatch_land_heal.py` 132, `test_factory_challenge.py` 79, `test_dispatch_verify_fix.py` 72) are Story 116.3's. The modules that hand the repository root to code under test are recorded in this spec for steward's `ROOT_HANDOFF_INPUTS`. The package half drops `scripts` from `PYTHONPATH`: a package-half test that imports a repo script is a live read.

Ledger key: `116-2-marshal-s-suite-runs-as-a-package-local-half-and-a-live-tree-half`. Type / Effort / Deps: chore / L / S-114.2, S-114.3, S-115.1, S-115.2, S-115.3, S-115.4, S-116.1.

## Boundaries & Constraints

**Always:**
- The halves partition the suite; the package half keeps at least 90% of the collected tests.
- Acceptance runs the two marker selections directly; steward:S-124.1 adds the task halves after the last marking story.

**Never:**
- Never delete, skip or re-mark a test to make a half pass (steward Story 117.4's Never list).
- Never mark one of the four largest modules whole.

## Acceptance Criteria

- **AC1 — The halves partition the suite, the live half is not empty, and the package half keeps at least 90% of the collected tests.**

  ```bash
  python3 -c "import subprocess,re,sys;n=lambda m:int(re.search(r'(\d+)(?:/\d+)? tests? collected',subprocess.run(['pixi','run','--frozen','-e','pyforge-marshal','pytest','src/shared/packages/pyforge-marshal/tests','--collect-only','-q','-p','no:cacheprovider','-m',m],capture_output=True,text=True).stdout).group(1));a=n('not slow and not live_tree');b=n('live_tree and not slow');c=n('not slow');print(a,b,c,round(a/c,3));sys.exit(0 if a+b==c and b>0 and a>=0.9*c else 1)"
  ```

  Expected: exit 0; prints A B C and the share.

- **AC2 — No module with more than 20 tests is marked whole, except the three whose every test reads the tree (named in the command).**

  ```bash
  python3 -c "import re,sys,pathlib;W=set(sys.argv[1:]);bad=[str(p) for p in pathlib.Path('src/shared/packages/pyforge-marshal/tests').rglob('test_*.py') if re.search(r'^pytestmark = .*live_tree',p.read_text(),re.M) and not p.name.endswith('_live_tree.py') and len(re.findall(r'^\s*(?:async )?def test_',p.read_text(),re.M))>20 and p.name not in W];print(bad);sys.exit(1 if bad else 0)" test_derived_context_skill_contract.py test_planning_graph_skill_contract.py test_local_recipes_empty_plan.py
  ```

  Expected: exit 0; prints `[]` (the four modules Story 116.3 splits are not marked by this story).

- **AC3 — No test was lost.**

  ```bash
  python3 -c "import subprocess,re,pathlib,sys;rx=re.compile(r'^\s*(?:async )?def test_',re.M);h=sum(len(rx.findall(p.read_text())) for p in pathlib.Path('src/shared/packages/pyforge-marshal/tests').rglob('*.py'));fs=[f for f in subprocess.run(['git','ls-tree','-r','--name-only','origin/main','src/shared/packages/pyforge-marshal/tests'],capture_output=True,text=True).stdout.split() if f.endswith('.py')];b=sum(len(rx.findall(subprocess.run(['git','show','origin/main:'+f],capture_output=True,text=True).stdout)) for f in fs);print(b,h);sys.exit(0 if h>=b else 1)"
  ```

  Expected: exit 0.

- **AC4 — Both halves pass, selected by marker.**

  ```bash
  pixi run --frozen -e pyforge-marshal env PYTHONPATH=src/shared/packages/pyforge-marshal/src pytest src/shared/packages/pyforge-marshal/tests/unit src/shared/packages/pyforge-marshal/tests/meta -q -m 'not slow and not live_tree' && pixi run --frozen -e pyforge-marshal env PYTHONPATH=src/shared/packages/pyforge-marshal/src:scripts pytest src/shared/packages/pyforge-marshal/tests/unit src/shared/packages/pyforge-marshal/tests/meta src/shared/packages/pyforge-marshal/tests/integration -q -m 'live_tree and not slow'
  ```

  Expected: exit 0.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal:CAP-305` (memlog 2026-11-10; rendered by Story 114.1); mechanism spec-pyforge-steward:CAP-175. FR-247 (written by Story 114.1).

- Epic: Epic 116 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 116.2: Marshal's suite runs as a package-local half and a live-tree half`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The Spec says what marshal is, and its roots come from one place.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda.

## Notes

- Owns a glob over marshal's tests, so it depends on every story that owns a marshal test file (114.2, 114.3, 115.1 to 115.4, 116.1).
- Cross-station: steward:S-124.1 reads the marking list, the paths and the `--cov` target from this spec and adds the task halves; steward:S-29.5 asks which stories move marshal source lines.

## Marking record (written at build)

Built 2026-11-11 on `cutover-readiness-2026-11-10` (base `1c9cb4ade3`). All paths are under
`src/shared/packages/pyforge-marshal/tests/`.

**How the list was derived.** Steward's `derive_reads` (`test_station_tests_trigger_map.py`), run over marshal's
job with the untracked new modules added to its file list, named 82 modules with an outside read and 16 that hand the
repository root to code. Read one by one, they fell into two kinds. Some read the tree (a `parents[6]` root,
a repo script loaded by path, a root hand-off); they are marked or split below. The rest only hold a fixture literal
that names a tracked path, which `scan_strings` counts as a read. In those, the literal is joined from its segments
(`"/".join((...))`), the practice of doctor Story 58.1 and Story 116.3. No test moved for a literal. After the build,
the same derivation over the unmarked modules (the package half) finds outside reads only in the four modules Story
116.3 splits (`unit/test_dispatch_landing.py`, `unit/test_dispatch_land_heal.py`, `unit/test_factory_challenge.py`,
`unit/test_dispatch_verify_fix.py`). The one package-half hand-off is `unit/test_dispatch_verify_fix.py`, also 116.3's.

**Marked whole (20 tests or fewer).** Each carries `pytestmark = pytest.mark.live_tree` and finds the repository root
when a test runs, never at import:

- `integration/test_login_pkce_live_keycloak.py`
- `meta/test_27_2_portal_loop_homes.py`, `meta/test_ad65_lean_env_conda_forge.py`,
  `meta/test_dispatch_supervisor_main_coverage_floor.py` (it loaded `scripts/coverage_gate.py` at import; it now
  loads it in the test), `meta/test_flag_mandate_overrides.py`, `meta/test_kit_artifacts_ignored_not_the_tracked_skills.py`,
  `meta/test_rendered_policy_untracked.py`, `meta/test_skf_domain_skill.py`,
  `meta/test_skill_projection_manifest_untracked.py`, `meta/test_spec_surface_stamp.py`, `meta/test_station_persona.py`,
  `meta/test_tea_architecture_drift.py`, `meta/test_tea_architecture_generator.py`,
  `meta/test_wire_store_ignored_not_the_seed_namespace.py`
- the five `meta/test_fleet_picture_*.py` modules (`attention_dispatch_refused`, `landing_findings`, `missing_spec`,
  `stale_dispatch`, `stranded_work`)
- `unit/test_dispatch_retry.py`, `unit/test_dispatch_ruff_format_trees.py`, `unit/test_dispatch_spec_frontmatter.py`,
  `unit/test_index_freshness.py`, `unit/test_mcp_registration.py`
- `meta/test_followup_review_carried.py`: found by reading, not by the derivation. Its root reached the reader through a
  default argument, which the static scan does not follow.

**Split (more than 20 tests).** Only the tests that read the tree moved, each into a `*_live_tree.py` sibling:

- `unit/test_chain_regen.py`: 22 tests moved into `unit/test_chain_regen_live_tree.py`, which Story 116.1 created. Each
  renders a sprint ledger with the repository's own `scripts/promote_sprint_status.py` or guards with its
  `regressions`. The two helpers both files use (the planning-tree seed and the recording invoker) moved to
  `unit/_chain_regen_support.py`. 21 tests stay.
- `unit/test_promote_sprint_status_regressions.py`: all 36 tests load `scripts/promote_sprint_status.py` and
  `scripts/fleet_scan.py`, so no package-local test is left. The module stays at its path, marked whole, with the
  19 tests of the regression guards and the bare-sync repair. Among them is `test_main_bare_sync_doctor_24_2_fixture`,
  which steward's `case-list.md` and `launch-slice.md` cite by node id. The other 17 moved to
  `unit/test_promote_sprint_status_regressions_live_tree.py`: the epic roll-ups, doctor Story 25.3's `--rekey`, and
  Story 107.1's stale-slug and `--feed-only` cases. That sibling imports the helpers from the module. Neither file
  holds more than 20 tests, so AC2 holds without naming either. The module used to load `fleet_scan` at import;
  it now loads it when a test runs. (Review round 1: the first build moved all 36 tests, which broke the cited node
  id.)
- `unit/test_landing_ci_pauses.py`: `test_101_1_ac5_steward_master_on_fixture` reads pyforge-steward's
  `tests/fixtures/ci_status_master_on.json`. It moved to `unit/test_landing_ci_pauses_live_tree.py`.
- `unit/test_repo_root.py`: `test_the_editable_layout_returns_the_same_root_as_the_bare_index` resolves the real
  repository. It moved to `unit/test_repo_root_live_tree.py`.
- `unit/test_policy.py`: `test_the_tracked_station_policies_opt_in_exactly_the_four_pages_stations` reads every
  station's tracked `marshal-policy.toml`. It moved to `unit/test_policy_live_tree.py`. This one was found by
  reading: the parametrize value is a tuple sum, which the scan does not evaluate.
- `unit/test_dispatch_verification.py`: 51 tests hand this checkout's root to `evaluate_dispatch_verification` and its
  gates, which load the root's `scripts/commit_msg_hook.py`, `src/platform/config/flags.json` and harness-profile
  overlays. They moved to `unit/test_dispatch_verification_live_tree.py`, which Story 116.1 created, together with
  the pinned command literals and the fake processes only they use. 34 tests stay, with the fakes both files use;
  the sibling imports those by name.
- `unit/test_dispatch_cfe_commit.py`: 10 tests read this checkout's conda-forge-expert `SKILL.md` version through
  `read_cfe_skill_version`, or hand the root to `evaluate_dispatch_verification`. They moved to
  `unit/test_dispatch_cfe_commit_live_tree.py`. The `repo` fixture body became `_story_repo`, so both files declare
  the fixture over one helper. 14 tests stay.

  Both of these modules found the root at import with a `next(...)` search that the static scan does not evaluate.
  An off-tree copy of the package half therefore failed to collect them (`StopIteration`). Their siblings now use
  `parents[6]`, the same directory, so the derivation sees the hand-off.

**Helpers.**

- `_support/contract_inventory.py`: only the live `meta/test_public_contract.py` uses it, so it carries the mark for the
  derivation, as steward's `tests/integration/nkp_probes.py` does.
- `integration/conftest.py`: its import-path inserts are now direct `sys.path.insert` calls. The derivation treats
  that form as plumbing, where it had read the old tuple loop as reads of `src/platform`, `pyforge-core/src` and
  `django-pyforge/src`.

**Already-marked modules.** These now find the root when a test runs, not at import: `unit/test_chain_regen_live_tree.py`,
`unit/test_upstream_cli_live_tree.py`, `unit/test_land_epic_rollups_live_tree.py`,
`meta/test_derived_context_skill_contract.py` and `meta/test_planning_graph_skill_contract.py`.

**Literal joins (package half).** The fixture paths in these modules are now joined: `unit/test_adapters_cli.py`, `test_conformance.py`,
`test_derived_context.py`, `test_dispatch.py`, `test_dispatch_cfe_commit.py`, `test_dispatch_flag_gate.py`,
`test_dispatch_fleet.py`, `test_dispatch_land_finalize.py`, `test_dispatch_preserve_tag.py`, `test_dispatch_reverify.py`,
`test_dispatch_station_guard.py`, `test_dispatch_supervisor_blocked_halt.py`, `test_dispatch_supervisor_main_loop.py`,
`test_dispatch_supervisor_verify_fix.py`, `test_dispatch_verification.py`, `test_dispatch_verify_commands.py`,
`test_dispatch_verify_merge_tree.py`, `test_gate.py`, `test_harness_bmadloop_preflight.py`, `test_init.py`,
`test_local_branch_refs.py`, `test_promotion.py`, `test_scope.py`, and the twelve `test_seed_*.py` modules
(`derive_adapters`, `detect_inventory`, `fs`, `model_artifact`, `model_manifest`, `state_acceptances`, `state_store`,
`verbs_accept`, `verbs_adopt`, `verbs_init`, `verbs_preconditions`, `verbs_update`), all under `unit/`.

**For steward S-124.1 (the task halves).**

| | Package half | Live half |
|---|---|---|
| Selection | `-m "not slow and not live_tree"` | `-m "live_tree and not slow"` |
| Paths | `tests/unit` and `tests/meta` | `tests/unit`, `tests/meta` and `tests/integration` |
| `PYTHONPATH` | `src/shared/packages/pyforge-marshal/src` only (no `scripts`) | `src/shared/packages/pyforge-marshal/src:scripts` |
| `--cov` target | `pyforge.marshal` | `pyforge.marshal` |

Collected at build (AC1): 13852 in the package half, 410 in the live half, 14262 in all, so the package half keeps
97.1%. The live half held 71 before this story. Test functions: 8279 on this branch, 8188 on `origin/main` (AC3).

**For steward's `ROOT_HANDOFF_INPUTS` (the re-key in S-124.2).** The live half derives these 16 hand-off files:
`integration/test_local_recipes_empty_plan.py`, `integration/test_login_pkce_live_keycloak.py`,
`meta/test_27_2_portal_loop_homes.py`, `meta/test_kit_artifacts_ignored_not_the_tracked_skills.py`,
`meta/test_rendered_policy_untracked.py`, `meta/test_skf_domain_skill.py`,
`meta/test_skill_projection_manifest_untracked.py`, `meta/test_spec_names_live_paths.py`, `meta/test_station_persona.py`,
`meta/test_tea_architecture_drift.py`, `meta/test_tea_architecture_generator.py`,
`meta/test_wire_store_ignored_not_the_seed_namespace.py`, `unit/test_chain_regen_live_tree.py`,
`unit/test_dispatch_cfe_commit_live_tree.py`, `unit/test_dispatch_spec_frontmatter.py` and
`unit/test_dispatch_verification_live_tree.py`. Two of these are new to the list: `unit/test_dispatch_cfe_commit_live_tree.py`
reads `.claude/skills/conda-forge-expert/SKILL.md` and loads `scripts/commit_msg_hook.py`, and the verification
sibling adds `scripts/commit_msg_hook.py` and `src/platform/config/flags.json` to `_bmad-output/harness-profiles/*.toml`.
Today's `marshal` entry still names `unit/test_chain_regen.py` and `unit/test_dispatch_verification.py`, both stale
since Story 116.1. It lacks `meta/test_spec_names_live_paths.py`, the two 116.1 siblings and the CFE sibling. `unit/test_dispatch_verify_fix.py` keeps its
hand-off in the package half until Story 116.3.

**Outside this story's files.** These tracked files cite a module or a node id that this story marked or moved.
None is edited here. The closer (Story 116.5 / 58.4) or each file's owner can re-point them.

- Still resolve, half changed. `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-regenerate-not-fold/case-list.md`
  (row `k-launch-ledger-sync`) and
  `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/launch-slice.md` (the
  ledger-sync step's A-test) cite
  `src/shared/packages/pyforge-marshal/tests/unit/test_promote_sprint_status_regressions.py::test_main_bare_sync_doctor_24_2_fixture`.
  The id resolves, and steward's `tests/meta/test_cutover_case_list.py` exits 0 (4 passed). The test now runs in the
  live half. Story 114.2's AC6 command
  (`pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_promote_sprint_status_regressions.py -q`)
  still names the module and exits 0 (19 passed); the pytest call selects no marker.
- Still resolve, half changed. Doctor's `SPEC.md` CAP-93 success (and `spec-pyforge-doctor/.memlog.md` and
  `research/egm-audit-2026-11-05.md`) cites
  `src/shared/packages/pyforge-marshal/tests/unit/test_promote_sprint_status_regressions.py` under
  `pyforge-marshal-test` as the guard-retention proof. The refusal tests stay in that module. It is marked
  `live_tree`, so once steward S-124.1 lands it runs under the live task, not `pyforge-marshal-test`'s package half.
- Still resolve, path only. Steward `epics.md` (lines 3171, 3175, 3427) and
  `specs/spec-48-1-the-ledger-syncer-guards-blocked-and-missing-keys.md` (lines 50, 58, 71, 89) cite the promote
  module, with a stale `:55` line pin in places. Marshal `epics.md` (7102, 10247), `specs/spec-107-1-*.md`,
  `specs/spec-54-1-*.md`, `test-architecture.md` (352) and `docs/governance/flag-inventory/pyforge-marshal.md`
  (CAP-132, CAP-134) cite it too. So do `scripts/.spec-surface-baseline.json` and the history in the steward
  research and proposal files. The module still exists at that path.
- Node id moved. `docs/dreams/pyforge-marshal.md:1481` and
  `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-98-1-two-marshal-tests-stop-failing-every-local-preflight.md`
  (lines 44 and 118; 118 is a runnable command) cite
  `tests/unit/test_dispatch_verification.py::test_evaluate_dispatch_verification_pre_existing_packaging_gate_warns`.
  That test is now in `unit/test_dispatch_verification_live_tree.py`.
- Test name with the old module, not a node id. Marshal `specs/spec-28-14-*.md` (143, 155, 201),
  `specs/spec-53-1-*.md` (99, 104), `specs/spec-83-2-*.md` (143), `specs/spec-83-23-*.md` (104) and
  `epics.md` (9962) name `test_evaluate_dispatch_verification_*` tests of `test_dispatch_verification.py` that now
  sit in its sibling. So do warden's `specs/spec-16-1-*.md` (583) and the append-only marshal memlog line 1668.
  `specs/spec-101-1-*.md` (307) names `test_101_1_ac5_steward_master_on_fixture`, now in
  `unit/test_landing_ci_pauses_live_tree.py`.

**For Story 116.4 (the off-tree evidence).** The first build ran the package half from a copy that held only
`tests/` and `pyproject.toml`. It imported `pyforge.marshal` from this worktree's editable install, so the code
under test still found the real repository. That run hid the runtime reads below, and its claim that the rest
"pass wherever the package is whole" was wrong. Review round 1 copied the whole package, `src/` included, into an
empty git repository at `<repo>/src/shared/packages/pyforge-marshal`. The package half was run there with
`PYTHONPATH` set to the copy's `src`. It collected cleanly: 13739 passed, 14 skipped and 68 failed. 32 failures
are in Story 116.3's four modules. The other 36 sit in 8 package-half modules. In each, the code under test
resolves the repository root and reads a file outside the package. The static derivation does not see these reads,
because the test hands no root and names no path. They are handed to Story 116.4, whose guard is meant to catch
such runtime reads. No test changes in this story.

- `unit/test_land.py` (10): `marshal land`'s ledger publish and epic roll-up load the root's
  `scripts/promote_sprint_status.py` (`land._load_promote_sprint_status_module`). Without it the landing journals
  MRS-LAND-011/012, not the verdict the test pins. The tests are `test_sprint_ledger_promoted_on_merge`,
  `test_a_failed_ledger_publish_pairs_its_intent_with_an_outcome_ok_false`,
  `test_a_landed_ledger_publish_journals_an_outcome_ok_true`,
  `test_a_feed_only_ledger_sync_names_the_wave_keys_in_its_preflight_reason`,
  `test_land_already_landed_path_rolls_the_last_open_story_s_epic_to_done`,
  `test_promote_feed_sync_guard_judges_origin_main_not_stale_local_ledger`,
  `test_promote_feed_sync_guard_mutation_local_ledger_parser_would_sync_the_drop`,
  `test_promote_feed_sync_refuses_un_finish_against_origin_main`,
  `test_roll_up_epic_rows_reads_rows_below_a_column_zero_comment` and
  `test_roll_up_epic_rows_mutation_land_parser_misses_comment_below_rows`.
- `unit/test_land_epic_rollups.py` (11): the same loader, called through the module's `_sync()` helper and the
  landing. The tests are `test_a_stale_backlog_feed_epic_row_is_published_as_the_syncs_in_progress_roll_up`,
  `test_the_last_open_story_promoted_to_done_rolls_its_epic_to_done`,
  `test_with_no_feed_at_all_the_advancement_still_rolls_its_epic_up`,
  `test_a_done_epic_keeps_done_over_a_stale_feed_row_and_the_promotion_commit_regresses_nothing`,
  `test_an_unloadable_promotion_module_writes_no_uncomputed_epic_row_and_journals_a_warn` (3 cases:
  `missing`, `no-rollup`, `raises-on-load`), `test_a_rollup_that_reverts_the_only_feed_change_publishes_nothing`,
  `test_the_replayed_inputs_reproduce_b9869e5c6d_without_the_roll_up`,
  `test_the_doctor_41_5_replay_publishes_epic_41_in_progress` and
  `test_a_stale_slug_feed_key_is_left_out_of_the_published_twin`.
- `unit/test_deploy.py` (4): `deploy reconcile-completions` loads the root's `scripts/promote_sprint_status.py`
  for `apply_epic_rollups`. Without it the run journals MRS-DEPLOY-028. The tests are
  `test_reconcile_completions_advances_and_promotes_a_not_loop_native_story`,
  `test_reconcile_completions_rolls_epic_to_done_when_last_open_story_advances`,
  `test_reconcile_completions_already_promoted_spec_still_advances_the_ledger` and
  `test_reconcile_completions_closes_the_tier3_feed_divergence_after_a_successful_advance`.
- `unit/test_dispatch_land_finalize.py` (2): the landing finalize loads the same script.
  `test_the_64_1_replay_a_publish_timeout_inside_finalize_is_a_failed_landing` gets an extra MRS-LAND-011, and
  `test_a_plain_sprint_ledger_sync_reports_unchanged_once_the_feed_row_is_promoted` cannot load the module.
- `unit/test_harness_policy_render.py` (2): `repo_root()` resolves the root, and the convention layer composes the
  project policy from it. `test_conventional_project_policy_path_lands_on_the_repo_root` finds no `pixi.toml` at
  the resolved root. `test_cli_writes_the_harness_policy_via_the_convention_layer` finds no project layer.
- `unit/test_tier_routing.py` (1): `test_no_live_tier_renders_a_model_its_adapter_cannot_run` composes each
  station's tier map from the stations' tracked `marshal-policy.toml` under the root. Off the tree,
  `pyforge-herald` composes none.
- `unit/test_spin.py` (1): `test_spin_states_the_wire_layer_disposition_on_every_run` composes the policy from the
  root. The repo-default layer, `_bmad-output/policy-defaults.toml`, sets `[context.wire]` to `auto`; off the tree
  that layer is absent, so the wire layer is not applied.
- `meta/test_tool_surface_coverage.py` (5): `coverage.resolve_repo_root` needs `pixi.toml` and `.claude` at the
  root and raises `FileNotFoundError` without them. The tests are `test_tool_surface_coverage_report_is_a_number`,
  `test_coverage_is_published_not_gated_on_one`, `test_live_dream_six_includes_atlas`,
  `test_mason_and_marshal_surfaces_detectable` and `test_format_coverage_report_is_json`.

## Spec Change Log

- 2026-11-10: minted at `backlog` by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10) and the memlog entries of `spec-pyforge-marshal` came first; `SPEC.md` is rendered by Story 114.1.

## Review findings (build, round 1, 2026-11-11)

An independent reviewer failed the first build. Each finding, then what this round did.

1. **Blocker.** Where: `unit/test_promote_sprint_status_regressions.py`, deleted and moved whole to its
   `_live_tree.py` sibling. Problem: steward's `case-list.md` (row `k-launch-ledger-sync`) and `launch-slice.md` (the
   ledger-sync step's A-test) cite
   `src/shared/packages/pyforge-marshal/tests/unit/test_promote_sprint_status_regressions.py::test_main_bare_sync_doctor_24_2_fixture`.
   Steward's live-tree `tests/meta/test_cutover_case_list.py` resolves those ids statically, so it went red with 2
   failures. Story 114.2's AC6 command also named the deleted file, and the record listed none of these.
   Fixed with the reviewer's option (a). The module is back at its path, marked whole with
   `pytestmark = pytest.mark.live_tree`. It holds 19 tests, the regression guards and the bare-sync repair, among
   them `test_main_bare_sync_doctor_24_2_fixture`. The other 17 sit in the sibling, which imports the module's
   helpers. Verified: `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_cutover_case_list.py`
   exits 0 (4 passed). 114.2's AC6 pytest call exits 0 (19 passed). AC2 still exits 0, and every cited path is
   listed under *Outside this story's files*.
2. **Minor.** Where: the *For Story 116.4* paragraph. Problem: it said the off-tree failures outside 116.3's modules
   were only reads of the package's own `src/` and `pixi.toml`, which pass wherever the package is whole. The
   reviewer's whole-package copy failed 36 tests in 8 package-half modules, each a runtime read of the repository
   root by code under test. Fixed: the paragraph is rewritten. This round reproduced the copy: 68 failed, 32 of
   them in 116.3's modules. The paragraph names all 36 other tests, their 8 modules and the read each one makes,
   and hands them to Story 116.4. No test changed. The reviewer is right. The first copy imported `pyforge.marshal`
   from the worktree's editable install, which hid these reads.
3. **Minor.** Where: `docs/dreams/pyforge-marshal.md:1481`, marshal `specs/spec-98-1-*.md` (44, 118), steward
   `epics.md:3171` and `specs/spec-48-1-*.md`. Problem: they cite node ids or paths that moved, and the outside list
   omitted them. Fixed: *Outside this story's files* now lists them, and a `git grep` of every moved test name
   across tracked files adds the rest. Each entry says whether it still resolves. With finding 1's fix, every
   citation of the promote module's path resolves again. The one node-id citation that no longer resolves is
   `test_dispatch_verification.py::test_evaluate_dispatch_verification_pre_existing_packaging_gate_warns`, in the
   Dream and spec-98-1. Name-only citations in done story specs and memlogs are listed too.

No acceptance command was changed. The reviewer named no fault in an oracle.
