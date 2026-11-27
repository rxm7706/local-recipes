---
title: "118.9: The gitops branch is guarded before any cloud run"
type: 'feature'
created: '2026-11-27'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag:
  key: pyforge.steward.nkp_gitops_branch
  provider: openfeature-file
  default: {production: on, staging: on, dev: on}
  scope: global
  fallback: "deploy nic refuses every action (validate, up, kubeconfig, outputs, down) on a repository.existing config with usage code 2; kind's repository.local is unaffected"
  cleanup: "90 days after ON in every environment (Q4; minted ON everywhere 2026-11-27, due 2027-02-25); the owning station files the removal story"
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-3-the-gitops-branch-of-the-monorepo-is-the-gitops-source-and-a-hetzner-cluster-runs-on-it.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-8-the-gitops-branch-has-one-named-writer-enforced.md
  - docs/dreams/pyforge-steward.md
  - docs/governance/guild-roster.json
  - scripts/_protected_refs_ruleset_lib.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_nic.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py
---

<intent-contract>

## Intent

**Problem:** Story 118.3 bundles two halves: the guards that must hold before any cloud run (the protected branch and its declared ruleset, the branch refusal on every action, the kill switch, the secret scans, the deploy key's inventory row and the consent gate) and the attended Hetzner run itself. The guards are code an agent can build and test today; the run waits on inputs only the operator can supply (a Hetzner API token, a domain with DNS, the deploy key and its inventory row, the live `gitops/**` ruleset, the attended `deploy nic up --yes`). Held together, the code waits on the run.

**Approach:** The operator ruled on 2026-11-27 ("Yes, build code half") that the agent-buildable half lands now. This story carries Story 118.3's AC1, AC2, AC5, AC6, AC7 and AC8 as written there (moved here 2026-11-27; their text is not rewritten), plus the tracked Hetzner config and its how-to section; Story 118.3 keeps AC3 and AC4, the attended run, and gains Deps S-118.9. `refs/heads/gitops/` joins `docs/governance/guild-roster.json` `protected_refs` (kind `operational-branch`, rules `creation`, `update`, `deletion`, `non_fast_forward`, bypass `DeployKey`), so the session hook denies its deletion and the roster-derived ruleset document declares `protected-refs-gitops-branches` with the repository's deploy keys as its only bypass actor; `scripts/_protected_refs_ruleset_lib.py` and `scripts/protected_refs_ruleset_check.py` learn that bypass actor for this ruleset only and count the repository's write-enabled deploy keys on the live read. `run_nic` refuses a `repository.existing` config before `nic` starts, for every action, when `pyforge.steward.nkp_gitops_branch` is OFF or the branch is `main` or outside `gitops/`; refuses an `up` on any provider but local kind without the operator's `--yes` (on the parser for `up` only); resolves `GITOPS_DEPLOY_KEY` only while `.steward/keys-inventory.yaml` holds its issued row (the row is operator-written); redacts `nic`'s last line in its summary; and after a cloud `up` scans `origin/main..origin/<branch>`. The scanner is `steward keys audit --secrets`'s pattern table (`_SECRET_PATTERNS` in `keys.py`: an Anthropic API key, an age identity, a PEM private-key header in any case, a base64-encoded PEM block, a GitHub classic or fine-grained token, a Hetzner-shaped 64-character mixed-case token; the last five added on review, 2026-11-27), used by `keys`, by `deploy nic` before its own kind GitOps commit and after a cloud `up`, and by the pre-commit hook `nic-config-secret-scan` over `src/platform/deploy/nic/` (a standard-library script that reads the table from `keys.py`'s source, so the table is declared once); an env-var name is not secret-shaped and passes.

Ledger key: `118-9-the-gitops-branch-is-guarded-before-any-cloud-run`.
Type / Effort / Deps: feature / L / S-118.8.

### Living CAP citations

- **`spec-pyforge-steward` CAP-178** — the cloud GitOps source on a branch only `nic`'s deploy key writes, its enforcement, the branch refusal on every action, the no-secret rule, the inventory row and the unechoed summary; this story is its pre-run half.
- **`spec-pyforge-steward` CAP-176** — the consent gate: a non-local `up` runs only under the operator's `--yes`.
- **`spec-pyforge-steward` CAP-165** (the protected refs declared once, proven live) and **CAP-1** (`keys`) — extended by one roster entry with its bypass actor and one inventoried credential; kept as written otherwise.

## Acceptance Criteria

- **AC1 — The roster and the ruleset (Story 118.3 AC1, moved here 2026-11-27).** `guild-roster.json` `protected_refs` lists `refs/heads/gitops/` with kind `operational-branch`; the hook tests deny `git push origin --delete gitops/x`; the force-push denial's real source is the server ruleset, not the hook (the hook has no force-push matcher for the branch): `docs/governance/rulesets/protected-refs.json` and CAP-165's live-ruleset proof list `refs/heads/gitops/**` with `creation`, `update`, `deletion` and `non_fast_forward` rules whose only bypass actor is the repository's deploy keys, with `GITOPS_DEPLOY_KEY` its only write-enabled deploy key; `scripts/_protected_refs_ruleset_lib.py` and its parity check declare and verify a `DeployKey` bypass actor for `gitops/**` only; every other ruleset keeps the empty-bypass rule.
- **AC2 — The refusal (Story 118.3 AC2, moved here 2026-11-27).** `run_nic` refuses, for every action (`validate`, `up`, `kubeconfig`, `outputs`, `down`) and before `nic` starts, `repository.existing.branch: main` and `feature/x` with usage code 2 and the reason named, and accepts `gitops/my-nebari-hetzner`; a unit test pins `up` refused on branch `main` with usage code 2 and no subprocess; kind's `repository.local` is unaffected.
- **AC3 — The flag (Story 118.3 AC5, moved here 2026-11-27).** `pyforge.steward.nkp_gitops_branch` joins `src/platform/config/flags.json` and the three shipped-flag tables; OFF refuses every action on a `repository.existing` config with usage code 2; a test builds both states.
- **AC4 — No secret in the tracked config or the rendered tree (Story 118.3 AC6, moved here 2026-11-27).** A scan runs over `src/platform/deploy/nic/` in the pre-commit configuration and before any commit `deploy nic` makes (kind's local GitOps commit), and after a cloud `up` over `origin/main..origin/gitops/<project_name>`; each refuses a planted secret-shaped value (a test plants one); the verb's `DutyResult` summary names `nic`'s exit code and never echoes `nic`'s output unredacted (a test feeds a secret-shaped last line and asserts it is absent from the summary). The scanner is the `steward keys audit --secrets` pattern table; an env-var name passes; the hook exits 1 on a finding and 2 when it cannot run, the post-`up` scan exits 1 on a finding or an unreadable range, and the pre-commit scan of the kind commit refuses with usage code 2 (STW-D-F4).
- **AC5 — The deploy key's inventory row (Story 118.3 AC7, moved here 2026-11-27).** `GITOPS_DEPLOY_KEY` gains a `.steward/keys-inventory.yaml` row on CAP-164's pattern, its expiry and scope operator-owned; `keys` refuses to resolve it without the row; no `GIT_TOKEN` remains in the Hetzner config or the how-to. The row itself is the operator's to write.
- **AC6 — The consent gate (Story 118.3 AC8, moved here 2026-11-27).** `deploy nic up` on a config whose provider is not local kind refuses with usage code 2 without `--yes` and runs with it; `--yes` is accepted by the parser for `up` only; `tests/scripts/test_pre_shell_hook.py`'s `steward-deploy-nic-up-yes` cases stay green.
- **AC7 — The tracked Hetzner config.** `src/platform/deploy/nic/my-nebari-hetzner.yaml` follows NIC 0.17.0's Hetzner example: `cluster.hetzner` with one master and two `cpx31` workers, Let's Encrypt, `/shared` on `longhorn`, `repository.existing` on `rxm7706/local-recipes` with `branch` and `path` `gitops/my-nebari-hetzner` and `auth.ssh.env: GITOPS_DEPLOY_KEY`; it holds no secret, and the operator-owned values (the domain, the ACME contact) are named placeholders on the reserved `.invalid` domain, never invented; `steward deploy nic validate` on it refuses with usage code 2 (no inventory row) and reaches no cloud.
- **AC8 — The how-to.** `docs/how-to/host-nebari.md` gains a section naming each guard, its exit code and the operator-owned inputs.

## Boundaries & Constraints

**Always:**
- Read every credential through `keys`; name the operator-owned inputs in this spec and the how-to, never their values.
- Refuse before `nic` starts; refuse by name.

**Never:**
- Never run `deploy nic up` against any cloud, never run `deploy nic up --yes`, never create a repository, ruleset, token, deploy key or Hetzner resource from an agent session; never write the `GITOPS_DEPLOY_KEY` inventory row; never point `repository.existing` at `main`; never add a dependency to `pixi.toml`; never hand-edit `SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-steward` CAP-178.

Parent: `spec-pyforge-steward` CAP-178

- Dream: `docs/dreams/pyforge-steward.md` § *2026-10-31 — Nebari hosted: NKP on kind, then Hetzner, with the data-science pack*.
- Epic: Epic 118.
- Ledger key: `118-9-the-gitops-branch-is-guarded-before-any-cloud-run`.
- Deps: S-118.8.
- Blocks: Story 118.3 (its Deps gain S-118.9, 2026-11-27).
- Split from Story 118.3 on the operator's ruling of 2026-11-27 ("Yes, build code half").
- Surface: `marshal-policy.toml` `[epic_surfaces]."118"`; the files are `docs/governance/guild-roster.json`, `docs/governance/rulesets/protected-refs.json`, `scripts/_protected_refs_ruleset_lib.py`, `scripts/protected_refs_ruleset_check.py`, `tests/scripts/test_protected_refs_ruleset_check.py` (its fixtures now written to `tmp_path`; the six tracked files under `tests/scripts/fixtures/protected_refs_ruleset/` removed), `tests/scripts/test_pre_shell_hook.py`, `.pre-commit-config.yaml`, `scripts/nic_config_secret_scan.py`, `tests/scripts/test_nic_config_secret_scan.py`, `tests/scripts/scripts-lib-test.txt`, `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_nic.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy_nic_packs.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/keys.py`, `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py`, `src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic.py`, `src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic_packs.py`, `src/shared/packages/pyforge-steward/tests/unit/test_keys_plaintext_secret_scan.py`, `src/platform/config/flags.json`, `src/platform/config/flag-overlays.json`, `src/shared/packages/pyforge-core/tests/unit/test_flags.py`, `src/platform/tests/test_openfeature_file_flags.py`, `src/platform/deploy/nic/my-nebari-hetzner.yaml`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/contract.md` and `docs/how-to/host-nebari.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: exit 0 (the station suite; the gate's binding, MRS-GATE-010/011).

**Story checks (the session runs these; they are not the gate's binding):**
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic.py src/shared/packages/pyforge-steward/tests/unit/test_deploy_nic_packs.py src/shared/packages/pyforge-steward/tests/unit/test_keys_plaintext_secret_scan.py -q` — expected: pass (both flag states, the branch refusal on every action with `up` on `main` refused with usage code 2 and no subprocess, the `--yes` gate and the parser, the inventory-row refusal, the redacted summary, the post-`up` range scan, the kind-commit scan).
- `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_pre_shell_hook.py tests/scripts/test_protected_refs_ruleset_check.py -q` — expected: pass (the `gitops/` deletion denial, the `steward-deploy-nic-up-yes` denial, the `DeployKey` bypass declared and verified for `gitops/**` only).
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_nic_config_secret_scan.py -q` — expected: pass (the pre-commit hook refuses a planted secret-shaped value; the tracked configs are clean).
- `pixi run -e pyforge-guild python scripts/nic_config_secret_scan.py src/platform/deploy/nic/my-nebari-local.yaml src/platform/deploy/nic/my-nebari-hetzner.yaml` — expected: exit 0.
- `pixi run --frozen -e pyforge-core pyforge-core-live-test` — expected: exit 0 (the shipped-flag tables).
- `pixi run -e pyforge-steward pyforge steward deploy nic validate -f src/platform/deploy/nic/my-nebari-hetzner.yaml` — expected: exit 2, refused before `nic` starts (no `GITOPS_DEPLOY_KEY` inventory row); no cloud is reached.
- `python scripts/flag_gate_check.py --spec _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-118-9-the-gitops-branch-is-guarded-before-any-cloud-run.md` — expected: `pass`.

**Run before the push:**
- `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check`, `spec-surface-check`, `governance-currency`, `precommit-config-check` — expected: exit 0 each.

## Auto Run Result

Status: in-review

Summary (2026-11-27, hand-built in the landing worktree `gitops-guard-2026-11-27`, cut from `origin/main` d9d94514c7; nothing committed):

- AC1: `docs/governance/guild-roster.json` `protected_refs` gains `refs/heads/gitops/` (kind `operational-branch`, scope `origin`, rules `creation`, `update`, `deletion`, `non_fast_forward`, `bypass: ["DeployKey"]`). `scripts/_protected_refs_ruleset_lib.py` renders a branch entry's declared bypass (only `DeployKey`, only on a branch; anything else raises), names the group `protected-refs-gitops-branches`, normalises live bypass actors, and compares them to the declaration (an empty declaration keeps the old "must be empty" finding). `scripts/protected_refs_ruleset_check.py` lists `repos/<repo>/keys` when a declared ruleset names a `DeployKey` bypass and reds more than one write-enabled deploy key (exit 2 when the list cannot be read). `docs/governance/rulesets/protected-refs.json` is regenerated (`--write-document`) and declares the ruleset. Where the live proof runs: `protected-refs-ruleset-check` is `scope=runtime`, excluded from `detectors-ci` and from `pr-preflight`, and no CI job compares the declaration with GitHub, so declaring it reds no gate; the document is derived from the roster alone (byte-identical test), so the roster entry the hook needs cannot land without it. Until the operator applies the ruleset, the operator-run live check exits 1 naming `missing live ruleset named 'protected-refs-gitops-branches'`. Tests: `tests/scripts/test_pre_shell_hook.py` (`git push origin --delete gitops/x`, the refspec and `gh api -X DELETE` forms denied; the roster shape), `tests/scripts/test_protected_refs_ruleset_check.py` (seven new tests; the six old fixture tests now write to `tmp_path`, and the six tracked files under `tests/scripts/fixtures/protected_refs_ruleset/`, which every run rewrote, are removed; an unused local removed).
- AC2: `deploy_nic.refuse_gitops_branch` runs in `run_nic` after the config loads and before secrets, the `nic` lookup or any subprocess; `main`, `refs/heads/main`, `feature/x`, `gitops/` and an empty branch refuse with usage code 2 on all five actions (`test_every_action_refuses_a_branch_outside_gitops_before_nic_starts`, 25 cases; `test_up_on_main_is_refused_with_usage_code_two_and_no_subprocess`); `gitops/my-nebari-hetzner` reaches `nic` (`test_a_gitops_branch_is_accepted`).
- AC3: `pyforge.steward.nkp_gitops_branch` in `src/platform/config/flags.json` (owner steward, story `118-9-…`, created and ON everywhere 2026-11-27, cleanup_by 2027-02-25) and ON in the three `flag-overlays.json` environments; the tables in `src/shared/packages/pyforge-core/tests/unit/test_flags.py` (`_SHIPPED_CLOCKS`, `_LATER_KILL_SWITCHES`, the per-environment table) and `src/platform/tests/test_openfeature_file_flags.py` (`_SHIPPED_BOOLEANS`); `contract.md` § Feature-flag keys. `test_the_gitops_branch_flag_in_both_states` runs both states through `flag_states` (OFF refuses every action on a `repository.existing` config; kind unaffected in both).
- AC4: the scanner is `steward keys audit --secrets`'s pattern table (`keys._SECRET_PATTERNS`: `anthropic-api-key`, `age-identity`, `pem-private-key-header`); an env-var name matches none. `keys.scan_text_for_secrets` (the file scanner now delegates to it) and `keys.redact_secret_shapes` are new. `.pre-commit-config.yaml` gains `nic-config-secret-scan` (stage `pre-commit`, `files: ^src/platform/deploy/nic/`, `language: script`) and `pre-commit` in `default_install_hook_types`; `scripts/nic_config_secret_scan.py` is standard-library only and reads the table from `keys.py`'s source with `ast` (exit 0 clean, 1 refused, 2 could-not-run). `git_commit_applications` scans the written Applications before `git add` (usage code 2). After a cloud `up`, `scan_gitops_range` fetches `main` and the branch and scans `git log -p origin/main..origin/<branch>` (exit 1 on a finding or an unreadable range). The summary carries `nic`'s last line only through `redact_secret_shapes`, with every resolved secret value too. Tests: `tests/scripts/test_nic_config_secret_scan.py` (listed in `tests/scripts/scripts-lib-test.txt`; it needs PyYAML), `test_git_commit_applications_refuses_a_planted_secret_before_git_runs`, `test_the_range_scan_refuses_a_planted_secret`, `test_the_range_scan_fails_closed_when_it_cannot_read`, `test_the_summary_never_echoes_a_secret_shaped_last_line`, `test_the_summary_never_echoes_a_secret_the_verb_resolved`, and two scanner tests in `test_keys_plaintext_secret_scan.py`.
- AC5: `keys.issued_row_refusal` refuses a credential with no, a retired, an observed, or two issued active rows, and an unreadable inventory; `load_secret_env` checks `INVENTORIED_CREDENTIALS` (`GITOPS_DEPLOY_KEY`) first, before `.env` is read (usage code 2); `NicDeps.inventory` injects the inventory. Tests: `test_keys_refuses_the_deploy_key_without_its_inventory_row` (four cases), `test_keys_refuses_an_unreadable_inventory`, `test_the_deploy_key_resolves_through_keys_with_its_row`. The row is not written. No `GIT_TOKEN` in the Hetzner config or the how-to.
- AC6: `--yes` on the `up` parser only (`test_the_parser_takes_yes_on_up_only`); `refuse_without_consent` refuses `up` without it on any config whose `cluster` is not exactly `{local: …}` (`test_a_non_local_up_needs_the_operators_yes`, `test_kind_up_and_every_other_action_need_no_yes`, `test_run_deploy_nic_hands_yes_to_run_nic`); the hook's `steward-deploy-nic-up-yes` cases pass unchanged. `contract.md` records the flag, the `--yes` and the new exit-1 case.
- AC7: `src/platform/deploy/nic/my-nebari-hetzner.yaml` from NIC 0.17.0's `examples/hetzner-config.yaml` (read 2026-11-27); domain and ACME contact are `.invalid` placeholders; `deploy nic validate` on it exits 2 before `nic` starts and writes no journal.
- AC8: `docs/how-to/host-nebari.md` § *Hetzner: the gitops branch is guarded before any cloud run*; its `sources:` list the profile, the hook script, `.pre-commit-config.yaml` and the ruleset document.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/marshal-policy.toml` `[epic_surfaces]."118"` names the new surface. Fixture configs in `test_deploy_nic_packs.py` gained `cluster: {local: {}}` (a config with no cluster is not local kind, so its `up` now needs `--yes`).

Command exit codes (2026-11-27, read from `$?`, never through a pipe):

- `pixi run -e pyforge-guild sprint-ledger-sync -- --project steward` — 0 (wrote the 118-9 key; it also carried `117-30-…: done` from the shared feed, a story merged to `origin/main` as 43e89b275a after this branch's base).
- `pixi run --frozen -e pyforge-guild story-status-check` — 0.
- `pixi run --frozen -e pyforge-guild python _bmad/scripts/bmad_tea_playwright.py --project pyforge-steward` — 0; `… --check` — 0 (546 story ids).
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — 0 (2273 passed, 3 skipped).
- `pixi run --frozen -e pyforge-steward pyforge-steward-live-test` — 1: one failure, `test_sprint_ledger_query.py::test_engine_counts_agree_with_fleet_scan_parse_sprint_status_over_the_live_tree` (547 ledger keys against 546 stories: the `117-30` key above); 1938 passed. It clears when `origin/main` is merged into the branch.
- `scripts/coverage_gates_ci.py --paths-file <the touched paths> --suites unit` with both reports, `COVERAGE_GATES_STATIONS=steward`, in `pyforge-steward` — 0 (`cli`, `deploy_nic`, `deploy_nic_packs`, `keys` all ≥ 80%). The `pyforge-steward-coverage-gate` task diffs commits, and nothing is committed.
- `pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_pre_shell_hook.py -q` — 0 (597 passed); `… tests/scripts/test_protected_refs_ruleset_check.py -q` — 0 (21 passed).
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_nic_config_secret_scan.py tests/scripts/test_worktree_sweep.py tests/scripts/test_lint_types_gate.py tests/scripts/test_flag_gate_check.py tests/scripts/test_session_denial_forms.py -q` — 0 (305 passed).
- `pixi run --frozen -e pyforge-core pyforge-core-test` — 0.
- `pixi run --frozen -e platform-ci-test` `pytest tests/test_openfeature_file_flags.py` from `src/platform` — 0 (52 passed).
- `pixi run --frozen -e pyforge-guild lint-types` — 1 first (ruff format on three steward files), 0 after `ruff format`.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — 0; `python scripts/flag_gate_check.py --spec` on this spec and on Story 118.3's — `pass` each.
- `pixi run --frozen -e pyforge-guild chain-completeness-check` — 2: INV-B `ledger-key-without-story` for `117-30` alone (the same merge clears it).
- `pixi run --frozen -e pyforge-guild governance-currency` — 0; `precommit-config-check` — 0.
- `pixi run -e pyforge-steward pyforge steward deploy nic validate -f src/platform/deploy/nic/my-nebari-hetzner.yaml` — 2 (refused: no `GITOPS_DEPLOY_KEY` inventory row; `nic` never started).
- `python scripts/chain_currency_sweep_check.py --project pyforge-steward` — 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — 2: co-governor drift for the session owner (`spec-pyforge-doctor`: `docs/how-to/host-nebari.md`; `spec-pyforge-unifying-strategy`: `src/platform/config/flags.json`, `src/platform/config/flag-overlays.json`, `src/platform/tests/test_openfeature_file_flags.py`; `spec-pyforge-core`: `src/shared/packages/pyforge-core/tests/unit/test_flags.py`), plus a pre-existing warn on `src/platform/compose/mcp-host/Containerfile` this branch did not touch. Nothing stamped.
- `pixi run --frozen -e pyforge-guild detectors-ci` — 1: three detectors red, each named above or pending a commit: `chain-completeness` (the `117-30` key), `spec-surface` (the co-governor drift), `docs-currency` (`docs/how-to/host-nebari.md` lists `src/platform/deploy/nic/my-nebari-hetzner.yaml` and `scripts/nic_config_secret_scan.py`, which are not in git history until committed); every other detector passed, `flag_gate_check` included.
- `src/shared/packages/pyforge-scribe/tests/meta/test_spec_not_behind_memlog.py` (in `pyforge-scribe`, `PYTHONPATH=scripts`) — 1: the `(decision)` memlog entry recording this split is not bookkeeping, so `spec-pyforge-steward` reads behind its memlog until `SPEC.md` is rendered.

Owed outside this story: the steward skill's `[SRC:…cli.py:Lnnnn]` anchors after the `deploy nic` parser move by two lines (the recompile, STW-R-F2 and STW-R-F3, stays with Story 118.3); the `precommit-config-check` task description in `pixi.toml` still names two hooks (not edited: a `pixi.toml` change fires every station suite); whether `steward init`'s `git-hooks` row should require the `pre-commit` hook type on every machine is the operator's call.

## Spec Change Log

- 2026-11-27: minted, split from Story 118.3 on the operator's ruling of 2026-11-27 ("Yes, build code half"): 118.3's AC1, AC2, AC5, AC6, AC7 and AC8 move here as this story's AC1 to AC6 (their text kept; AC4 names the scanner, the env-var allowance and the exit codes, carrying deferred STW-D-F4), with the tracked Hetzner config (AC7) and the how-to section (AC8); the `flag:` block moves here, since this story mints the key. Story 118.3 keeps AC3 and AC4 and gains Deps S-118.9.

## Review Triage Log

- 2026-11-27, independent review, finding 1 (the summary leaked a multi-line key): fixed — `keys.redact_secret_shapes` masks each resolved value whole, `\n`-escaped and line by line (lines of 8+ characters), and a PEM-header or base64-PEM match to the end of its line; tests `test_the_summary_never_echoes_a_multiline_key_the_verb_resolved` (three cases), `test_redaction_masks_a_pem_header_to_the_end_of_its_line`, `test_redaction_masks_a_resolved_multiline_value_whole_escaped_and_line_by_line`.
- 2026-11-27, finding 2 (the pattern table missed real shapes): fixed — `_SECRET_PATTERNS` gains a case-insensitive PEM header, `pem-block-base64`, `github-token`, `github-fine-grained-token` and `hetzner-api-token` (64 alphanumerics with both cases, not bordered by `+`, `/` or a trailing `=`), inline flags only; tests `test_the_table_finds_each_shape_a_cloud_run_can_leak`, `test_a_digest_a_base64_run_and_an_env_name_are_not_secret_shaped` (the `sha256:` digest among them).
- 2026-11-27, finding 3 (the branch was checked by prefix only): fixed — `deploy_nic.gitops_branch_problem` checks the raw value against `gitops/` plus ref-safe segments, no `..`, no leading-`.` segment or `.lock` suffix, and `gitops/<project_name>` exactly; test `test_every_action_refuses_a_branch_outside_gitops_before_nic_starts` (nine new branches) and `test_a_gitops_branch_is_accepted`.
- 2026-11-27, finding 4 (the inventory gate keyed on the env name): fixed — `refuse_gitops_branch` refuses a `repository.existing` whose `auth` is not exactly `auth.ssh.env: GITOPS_DEPLOY_KEY`; test `test_a_repository_existing_auth_other_than_the_deploy_key_is_refused`.
- 2026-11-27, finding 5 (the post-`up` scan could read another repository): fixed — `refuse_foreign_repository` compares `repository.existing.url`'s GitHub owner/repo with `origin`'s (four spellings, case-insensitive) before `nic` starts, through the injectable `NicDeps.origin_url`; tests `test_a_repository_existing_url_other_than_origin_is_refused_before_nic_starts`, `test_every_github_spelling_of_origins_repository_is_accepted`, `test_an_origin_steward_cannot_compare_is_refused`, `test_the_default_origin_reader_reads_the_checkout_remote`.
- 2026-11-27, finding 6 (`git log -p` blind spots): fixed — the range scan runs `git log -p --text --no-ext-diff --no-textconv --diff-merges=first-parent`; test `test_a_cloud_up_scans_the_pushed_range`.
- 2026-11-27, finding 7 (the table loader could drift): fixed — `scripts/nic_config_secret_scan.py` refuses (exit 2) a table entry that is not `re.compile` with the pattern alone; tests `test_a_table_entry_with_an_argument_the_reader_would_drop_cannot_run` and `test_the_pattern_table_is_the_one_keys_audit_uses` (now compares each pattern's text and flags with `keys._SECRET_PATTERNS`).
- 2026-11-27, finding 8 (the ruleset lib allowed a bypass on any branch; the deploy-key read saw one page): fixed — only `refs/heads/gitops/` may declare a bypass (any other is a finding, exit 1), and `fetch_deploy_keys` reads every page (`gh api --paginate`); tests `test_a_deploy_key_bypass_on_any_ref_but_the_gitops_entry_is_a_finding`, `test_the_deploy_key_read_pages_through_every_key`.
- 2026-11-27, finding 9 (a cloud config with no `repository.existing` ran): fixed — refused with usage code 2 on every action; test `test_a_cloud_config_without_repository_existing_is_refused`.
- 2026-11-27, operator ruling "Yes, require the hook in precommit-config-check": `scripts/precommit_config_check.py` requires the `pre-commit` hook type and `nic-config-secret-scan` at stage `pre-commit` (tests in `tests/scripts/test_lint_types_gate.py`); `docs/governance/machine-readiness.yaml`'s `git-hooks` row probes `pre-commit`, `commit-msg` and `pre-push` (fixture in `tests/meta/test_machine_readiness_data.py`); the `pixi.toml` task description and `docs/how-to/pixi-tasks.md` name three hooks. The Auto Run Result's AC4 line names the table as first built; it now holds the shapes the Approach lists.
- 2026-11-27, finding 10 (spec housekeeping): fixed — AC1 regains Story 118.3 AC1's parenthetical; the Verification scan line runs through `pixi run -e pyforge-guild`.
- 2026-11-27, second review, finding 1 (a URL refusal could print a token): fixed — `deploy_nic` strips `user[:password]@` before comparing (a token-bearing origin of the right repository is accepted) and prints only host/owner/repo through `redact_secret_shapes` (`shown_remote`); tests `test_a_token_bearing_origin_of_the_right_repository_is_accepted`, `test_a_url_refusal_never_prints_a_credential` (four cases), `test_a_url_with_a_query_is_not_a_github_repository_url`.
- 2026-11-27, second review, finding 2 (the range scan skipped a failed `up`): fixed — the scan runs after every cloud `up` with a `repository.existing`; a finding is exit 1 whatever `nic` exited, an unreadable range keeps `nic`'s code after a failed `up` and is exit 1 after a successful one; tests `test_a_failed_cloud_up_is_still_scanned_and_a_finding_is_exit_one`, `test_an_unreadable_range_after_a_failed_up_keeps_nics_code`, `test_a_clean_range_after_a_failed_up_keeps_nics_code`.
- 2026-11-27, second review, finding 3 (redaction order): fixed — the PEM and base64-PEM patterns mask to the end of the line before any literal mask, and a resolved value under 4 characters is not masked literally; tests `test_a_json_dumped_key_with_escaped_slashes_leaves_no_body_in_the_summary`, `test_redaction_masks_a_json_dumped_key_with_escaped_slashes_before_any_literal_mask`, `test_a_resolved_value_under_four_characters_is_not_masked_literally`.
- 2026-11-27, second review, finding 4 (the branch rule without a project name): fixed — a `repository.existing` config needs `project_name`, a non-empty string with no surrounding whitespace, and a branch segment may not end in `.`; tests `test_a_repository_existing_config_needs_a_project_name_as_written`, `test_a_branch_segment_ending_in_a_dot_is_refused`.
- 2026-11-27, second review, finding 5 (pattern false positives and misses): fixed — `hetzner-api-token` skips an SRI `sha256-`/`sha384-`/`sha512-` value, `pem-block-base64` skips a base64 certificate, public key, CRL, certificate request or PGP public block, and the PEM header matches a PGP `PRIVATE KEY BLOCK`; tests `test_an_sri_value_is_not_hetzner_shaped`, `test_a_base64_public_block_is_not_secret_shaped`, `test_a_base64_private_key_block_is_found`, `test_a_pgp_private_key_block_header_is_found`.
- 2026-11-27, second review, finding 6 (`deploy_key_findings` failed open): fixed — a key is write-enabled unless GitHub reports `read_only: true`, and a sole write-enabled key not titled `GITOPS_DEPLOY_KEY` is a finding (118.9 AC1 and 118.3 AC1 name it the only writer); the how-to says the operator titles it so; tests `test_a_deploy_key_counts_as_write_enabled_unless_github_says_read_only`, `test_the_one_write_enabled_deploy_key_must_be_titled_gitops_deploy_key`.
- 2026-11-27, second review, finding 7 (stale text): fixed — `.pre-commit-config.yaml` says "any policy hook" and `docs/tutorials/onboard-a-machine.md`'s sample lists `pre-commit, commit-msg, pre-push` (no other two-hook claim on that page); test `test_every_hook_type_is_named_where_a_reader_learns_the_hooks`.
