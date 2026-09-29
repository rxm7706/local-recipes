# Thin oracle — foundry kernel case list (fnr:CAP-1 / 54.1)

This is the **named gate** for Stories **54.2–54.4**. Frame YAML
preflight is not a row here and is not acceptance. Do not wait for
44.14. Do not dispatch 44.4 / 44.5. A `steward ab` CLI can wait; the
list is enough.

Cite existing tests on A (`local-recipes`). 54.2–54.4 rebuild the
packages on B and must record an A/B row that is not `diverge`.
`A-only` rows expire when the named later-cap lands so B can grow.

Node ids are pytest paths under `src/shared/packages/` on A.

| id | slice | argv / nodeid | expected row | A-only expiry |
|---|---|---|---|---|
| k-estate-smoke | estate | `pixi run estate-smoke` (B) | B-only | — |
| k-cutover-flag | core | read `src/platform/config/flags.json` `pyforge.cutover_root` default | pass (`local-recipes`) | — |
| k-no-root-recipes | estate | `recipes/` absent at B repo root | A-only vs B-only | until a foundry CFE + working-set story |
| k-no-host | estate | no `/console/` Launch surface on B | A-only | host/portals later-cap |
| k-core-cutover-default | core | `pyforge-core/tests/unit/test_cutover_root.py::test_default_is_local_recipes` | pass | — |
| k-core-cutover-foundry | core | `…/test_cutover_root.py::test_foundry_variant` | pass | — |
| k-core-cutover-unknown | core | `…/test_cutover_root.py::test_unknown_variant_fails` | pass | — |
| k-core-cutover-missing | core | `…/test_cutover_root.py::test_missing_flag_fails` | pass | — |
| k-core-port-env | core | `…/test_station_port.py::test_is_station_remote_reads_env` | pass | — |
| k-core-port-unreg | core | `…/test_station_port.py::test_invoke_without_registration_raises` | pass | — |
| k-core-port-remote | core | `…/test_station_port.py::test_invoke_while_remote_raises` | pass | — |
| k-core-port-invoke | core | `…/test_station_port.py::test_registered_invoker_is_called` | pass | — |
| k-core-port-error | core | `…/test_station_port.py::test_station_port_error_is_pyforge_error` | pass | — |
| k-core-error-root | core | `…/test_errors.py::test_pyforge_error_is_an_exception_subclass` | pass | — |
| k-core-verdict-rank | core | `…/test_verdict.py::test_lattice_rank_returns_zero_indexed_position` | pass | — |
| k-core-verdict-domain | core | `…/test_verdict.py::test_lattice_exit_codes_is_the_frozen_value_domain` | pass | — |
| k-core-verdict-dispatch | core | `…/test_verdict.py::test_dispatch_exit_code_matches_most_specific_first` | pass | — |
| k-core-dispatch-argv | core | `…/test_dispatch.py::test_dispatch_argv_forwards_noun_and_verb` | pass | — |
| k-core-dispatch-unknown | core | `…/test_dispatch.py::test_dispatch_argv_unknown_station_raises` | pass | — |
| k-core-dispatch-usage | core | `…/test_dispatch.py::test_main_unknown_station_is_usage_and_does_not_run` | pass | — |
| k-core-parity-verbs | core | `…/meta/test_cli_parity_matrix.py::test_ci_generates_parity_matrix_and_every_verb_is_reachable` | pass | — |
| k-steward-version | steward | `pyforge-steward/tests/unit/test_cli.py::test_version_exits_zero` | pass (54.3) | — |
| k-steward-help | steward | `…/test_cli.py::test_help_lists_all_duties` | pass (54.3) | — |
| k-steward-fail-1 | steward | `…/test_cli.py::test_failing_duty_projects_to_exit_1` | pass (54.3) | — |
| k-steward-crash-70 | steward | `…/test_cli.py::test_crash_never_returns_bare_1` | pass (54.3) | — |
| k-steward-sigint | steward | `…/test_cli.py::test_keyboard_interrupt_projects_to_130` | pass (54.3) | — |
| k-steward-workspace | steward | `…/test_cli.py::test_workspace_is_wired_into_help` | pass (54.3) | — |
| k-steward-no-flip | steward | `…/test_cutover.py::test_flip_refused_while_loop_running` | pass (54.3) | — |
| k-steward-one-verdict | steward | `…/test_guards.py::test_every_row_refuses_a_second_verdict` | pass (54.3) | — |
| k-steward-not-ci | steward | `…/test_guards.py::test_not_a_detectors_ci_member` | pass (54.3) | — |
| k-cli-steward-help | steward | `pyforge steward --help` | pass (54.3) | — |
| k-marshal-version | marshal | `pyforge-marshal/tests/unit/test_cli.py::test_version_returns_zero_and_prints_version` | pass (54.4) | — |
| k-marshal-help | marshal | `…/test_cli.py::test_help_returns_zero_and_prints_usage` | pass (54.4) | — |
| k-marshal-usage-2 | marshal | `…/test_cli.py::test_bogus_flag_returns_two_with_stderr_diagnostic` | pass (54.4) | — |
| k-marshal-no-sysexit | marshal | `…/test_cli.py::test_main_never_raises_systemexit` | pass (54.4) | — |
| k-marshal-domain | marshal | `…/test_cli.py::test_exit_code_always_in_guarded_domain` | pass (54.4) | — |
| k-marshal-verdict-domain | marshal | `…/test_verdict.py::test_cli_boundary_constants_and_guarded_domain` | pass (54.4) | — |
| k-marshal-warn-exit | marshal | `…/test_verdict.py::test_warn_never_shares_unevaluables_nonzero_exit` | pass (54.4) | — |
| k-marshal-tool-parity | marshal | `…/meta/test_cli_tool_parity.py::test_live_cli_tool_parity_passes` | pass (54.4) | — |
| k-cli-marshal-help | marshal | `pyforge marshal --help` | pass (54.4) | — |

**Count:** 38 rows (4 estate/CLI + 16 core + 9 steward + 9 marshal).

`diverge` is empty until 54.2–54.4 run the same id on A and B.
Pages / dossier (`pgs:CAP-1..5`) is rebuild cargo after the kernel,
not a row here.
