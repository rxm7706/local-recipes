# Thin oracle — foundry kernel case list (fnr:CAP-1 / 54.1)

This is the **named gate** for Stories **54.2–54.4** and the oracle of
the Launch slice (`spec-python-foundry-cutover` `launch-slice.md`,
operator ruling 3 of 2026-11-10). Frame YAML preflight is not a row
here and is not acceptance. Do not wait for 44.14. 44.4 and 44.5 are
retired (2026-11-10); never dispatch them. A `steward ab` CLI can wait;
the list is enough.

Cite existing tests on A (`local-recipes`). 54.2–54.4 rebuild the
packages on B and must record an A/B row that is not `diverge`.
`A-only` rows expire when the story their expiry names
(`<station>:<story>`) lands, so B can grow.

Node ids are pytest paths under `src/shared/packages/` on A. `…/`
stands for the `tests/` directory of the package the nearest full node
id above it names; a bare file name after `…/` sits under `tests/unit/`.

The `herald` slice is herald's package half (herald Story 52.1). The
`launch` slice has one row per `launch-slice.md` step whose A test
exists, in step order; a step whose A test is an `oracle gap` has no
row, and the gap is never filled here (`DW-steward-121-4`).

`src/shared/packages/pyforge-steward/tests/meta/test_cutover_case_list.py`
holds the count line equal to the rows, resolves every node id
statically (the file exists and defines the test) and holds a row for
every launch-slice step that has an A test.

| id | slice | argv / nodeid | expected row | A-only expiry | note |
|---|---|---|---|---|---|
| k-estate-smoke | estate | `pixi run estate-smoke` (B) | B-only | — | — |
| k-cutover-flag | core | read `src/platform/config/flags.json` `pyforge.cutover_root` default | pass (`local-recipes`) | — | — |
| k-no-root-recipes | estate | `recipes/` absent at B repo root | A-only vs B-only | `steward:44.8` | — |
| k-no-host | estate | no `/console/` Launch surface on B | A-only | `steward:121.5` | — |
| k-core-cutover-default | core | `pyforge-core/tests/unit/test_cutover_root.py::test_default_is_local_recipes` | pass | — | — |
| k-core-cutover-foundry | core | `…/test_cutover_root.py::test_foundry_variant` | pass | — | — |
| k-core-cutover-unknown | core | `…/test_cutover_root.py::test_unknown_variant_fails` | pass | — | — |
| k-core-cutover-missing | core | `…/test_cutover_root.py::test_missing_flag_fails` | pass | — | — |
| k-core-port-env | core | `…/test_station_port.py::test_is_station_remote_reads_env` | pass | — | — |
| k-core-port-unreg | core | `…/test_station_port.py::test_invoke_without_registration_raises` | pass | — | — |
| k-core-port-remote | core | `…/test_station_port.py::test_invoke_while_remote_raises` | pass | — | — |
| k-core-port-invoke | core | `…/test_station_port.py::test_registered_invoker_is_called` | pass | — | — |
| k-core-port-error | core | `…/test_station_port.py::test_station_port_error_is_pyforge_error` | pass | — | — |
| k-core-error-root | core | `…/test_errors.py::test_pyforge_error_is_an_exception_subclass` | pass | — | — |
| k-core-verdict-rank | core | `…/test_verdict.py::test_lattice_rank_returns_zero_indexed_position` | pass | — | — |
| k-core-verdict-domain | core | `…/test_verdict.py::test_lattice_exit_codes_is_the_frozen_value_domain` | pass | — | — |
| k-core-verdict-dispatch | core | `…/test_verdict.py::test_dispatch_exit_code_matches_most_specific_first` | pass | — | — |
| k-core-dispatch-argv | core | `…/test_dispatch.py::test_dispatch_argv_forwards_noun_and_verb` | pass | — | — |
| k-core-dispatch-unknown | core | `…/test_dispatch.py::test_dispatch_argv_unknown_station_raises` | pass | — | — |
| k-core-dispatch-usage | core | `…/test_dispatch.py::test_main_unknown_station_is_usage_and_does_not_run` | pass | — | — |
| k-core-parity-verbs | core | `…/meta/test_cli_parity_matrix.py::test_ci_generates_parity_matrix_and_every_verb_is_reachable` | pass | — | live tree: reads `_bmad-output/projects` (core-kit Story 117.1), so it runs in core's live-tree half |
| k-steward-version | steward | `pyforge-steward/tests/unit/test_cli.py::test_version_exits_zero` | pass (54.3) | — | — |
| k-steward-help | steward | `…/test_cli.py::test_help_lists_all_duties` | pass (54.3) | — | — |
| k-steward-fail-1 | steward | `…/test_cli.py::test_failing_duty_projects_to_exit_1` | pass (54.3) | — | — |
| k-steward-crash-70 | steward | `…/test_cli.py::test_crash_never_returns_bare_1` | pass (54.3) | — | — |
| k-steward-sigint | steward | `…/test_cli.py::test_keyboard_interrupt_projects_to_130` | pass (54.3) | — | — |
| k-steward-workspace | steward | `…/test_cli.py::test_workspace_is_wired_into_help` | pass (54.3) | — | — |
| k-steward-no-flip | steward | `…/test_cutover.py::test_flip_refused_while_loop_running` | pass (54.3) | — | — |
| k-steward-one-verdict | steward | `…/test_guards.py::test_every_row_refuses_a_second_verdict` | pass (54.3) | — | — |
| k-steward-not-ci | steward | `…/test_guards.py::test_not_a_detectors_ci_member` | pass (54.3) | — | — |
| k-cli-steward-help | steward | `pyforge steward --help` | pass (54.3) | — | — |
| k-marshal-version | marshal | `pyforge-marshal/tests/unit/test_cli.py::test_version_returns_zero_and_prints_version` | pass (54.4) | — | — |
| k-marshal-help | marshal | `…/test_cli.py::test_help_returns_zero_and_prints_usage` | pass (54.4) | — | — |
| k-marshal-usage-2 | marshal | `…/test_cli.py::test_bogus_flag_returns_two_with_stderr_diagnostic` | pass (54.4) | — | — |
| k-marshal-no-sysexit | marshal | `…/test_cli.py::test_main_never_raises_systemexit` | pass (54.4) | — | — |
| k-marshal-domain | marshal | `…/test_cli.py::test_exit_code_always_in_guarded_domain` | pass (54.4) | — | — |
| k-marshal-verdict-domain | marshal | `…/test_verdict.py::test_cli_boundary_constants_and_guarded_domain` | pass (54.4) | — | — |
| k-marshal-warn-exit | marshal | `…/test_verdict.py::test_warn_never_shares_unevaluables_nonzero_exit` | pass (54.4) | — | — |
| k-marshal-tool-parity | marshal | `…/meta/test_cli_tool_parity.py::test_live_cli_tool_parity_passes` | pass (54.4) | — | — |
| k-cli-marshal-help | marshal | `pyforge marshal --help` | pass (54.4) | — | — |
| k-herald-version | herald | `pyforge-herald/tests/unit/test_smoke.py::test_version_flag_exits_zero` | pass | — | — |
| k-herald-usage-2 | herald | `…/test_smoke.py::test_bare_invocation_is_a_usage_error` | pass | — | — |
| k-herald-deck-help | herald | `…/test_smoke.py::test_deck_help_exits_zero` | pass | — | — |
| k-herald-conflict-3 | herald | `…/test_cli_dispatch.py::test_dispatch_maps_every_conflict_error_to_3_and_names_it_on_stderr` | pass | — | — |
| k-herald-transport-4 | herald | `…/test_cli_dispatch.py::test_dispatch_maps_every_transport_error_to_4_and_names_the_concrete_subclass` | pass | — | — |
| k-herald-unmapped-1 | herald | `…/test_cli_dispatch.py::test_dispatch_maps_an_unmapped_herald_error_to_1` | pass | — | — |
| k-herald-determinism | herald | `…/test_bridge.py::test_bridge_core_never_names_a_concrete_transport_adapter` | pass | — | — |
| k-launch-mint | launch | `pyforge-doctor/tests/unit/test_sources_board_chain_completeness.py::test_epics_story_without_ledger_key_reports_fail` | pass (Launch) | — | step: mint the story |
| k-launch-dispatch | launch | `pyforge-marshal/tests/unit/test_dispatch.py::test_run_dispatch_journals_and_returns` | pass (Launch) | — | step: dispatch |
| k-launch-supervise | launch | `pyforge-marshal/tests/unit/test_dispatch_survival.py::test_reconcile_unsupervised_verdict_from_git_merge` | pass (Launch) | — | step: build and review (`dispatch-supervisor-attach`) |
| k-launch-push | launch | `pyforge-marshal/tests/unit/test_dispatch_push.py::test_run_and_journal_dispatch_push_pushes_before_verify` | pass (Launch) | — | step: build and review (`dispatch-push`) |
| k-launch-followup | launch | `pyforge-marshal/tests/unit/test_dispatch_harness_done.py::test_followup_true_allows_one_more_session` | pass (Launch) | — | step: build and review (one follow-up review) |
| k-launch-verify | launch | `pyforge-marshal/tests/unit/test_dispatch_verification.py::test_judge_refused_when_gate_fails` | pass (Launch) | — | step: preflight and detectors (`dispatch-verification`) |
| k-launch-detectors | launch | `pyforge-doctor/tests/unit/test_sources_dispatch.py::test_dispatch_covers_exactly_the_registered_sources` | pass (Launch) | — | step: preflight and detectors (`detectors-ci`) |
| k-launch-pr-finalize | launch | `pyforge-marshal/tests/unit/test_dispatch_supervisor_finalize.py::test_session_detects_harness_done` | pass (Launch) | — | step: PR (`dispatch-finalize`) |
| k-launch-pr-open | launch | `pyforge-marshal/tests/unit/test_land.py::test_happy_path_opens_pr_polls_checks_and_merges` | pass (Launch) | — | step: PR (`landing_checks`) |
| k-launch-merge | launch | `pyforge-marshal/tests/unit/test_dispatch_landing.py::test_merge_subject_is_marshal_native_with_policy_template` | pass (Launch) | — | step: merge (`dispatch-land`) |
| k-launch-land-finalize | launch | `pyforge-marshal/tests/unit/test_dispatch_land_finalize.py::test_finalize_resyncs_the_primary_after_ledger_promotion` | pass (Launch) | — | step: finalize (`dispatch-land-finalize-resync`) |
| k-launch-ledger-promote | launch | `pyforge-marshal/tests/unit/test_dispatch_land_finalize.py::test_finalize_passes_base_main_to_isolated_promote` | pass (Launch) | — | step: ledger sync (`land-sprint-ledger-promotion`) |
| k-launch-ledger-sync | launch | `pyforge-marshal/tests/unit/test_promote_sprint_status_regressions.py::test_main_bare_sync_doctor_24_2_fixture` | pass (Launch) | — | step: ledger sync (`sprint-ledger-sync`) |
| k-launch-story-status | launch | `pyforge-doctor/tests/unit/test_sources_marshal_story_status.py::test_false_green_story_reports_fail` | pass (Launch) | — | step: ledger sync (`story-status-check`) |

**Count:** 61 rows (3 estate + 18 core + 10 steward + 9 marshal + 7 herald + 14 launch).

`diverge` is empty until the same id runs on A and B (54.2–54.4 for
the kernel rows, B's Launch story for the launch rows).
Pages / dossier (`pgs:CAP-1..5`) is rebuild cargo after the kernel,
not a row here.
