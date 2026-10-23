---
id: SPEC-steward
spec: pyforge-steward
status: ready
updated: "2026-10-23"
owner-dream: docs/dreams/pyforge-steward.md
covers-dreams:
  - docs/dreams/pyforge-steward.md
  - docs/dreams/asgi-multiplexer-monolith.md
  - docs/dreams/bmad-eval-quality.md
  - docs/dreams/bmad-method-core-upgrade.md
  - docs/dreams/bmad-module-provisioning.md
  - docs/dreams/bmad-suite-channel-product.md
  - docs/dreams/bmad-suite-install-class-wiring.md
  - docs/dreams/bmad-suite-lifecycle.md
  - docs/dreams/bmad-suite-metapackage.md
  - docs/dreams/build-league-scorecard.md
  - docs/dreams/db-gpt-django-plugin.md
  - docs/dreams/developer-machine-bootstrap.md
  - docs/dreams/enterprise-airgap.md
  - docs/dreams/enterprise-multi-agent-orchestration.md
  - docs/dreams/intelligence-hub.md
  - docs/dreams/jira-github-projects-sync.md
  - docs/dreams/langflow-django-plugin.md
  - docs/dreams/local-ocp-hybrid-environment.md
  - docs/dreams/mcp-era-isolation.md
  - docs/dreams/mcp-host-real-station-tools.md
  - docs/dreams/multi-repo-workspaces.md
  - docs/dreams/ocp-as-a-portability-profile.md
  - docs/dreams/platform-datastores-consumed-not-self-hosted.md
  - docs/dreams/platform-dev-boots-local.md
  - docs/dreams/platform-fifteen-factors.md
  - docs/dreams/platform-image-one-pixi-env.md
  - docs/dreams/platform-object-storage-kind.md
  - docs/dreams/python-agent-platform.md
  - docs/dreams/scratch-worktree-lifecycle.md
  - docs/dreams/secure-live-dashboards.md
  - docs/dreams/self-hosted-bmad-marketplace.md
  - docs/dreams/suite-scaffold-and-mybmad-sidecar.md
  - docs/dreams/unified-container.md
  - docs/dreams/vocabulary-one-name-one-job.md
  - docs/dreams/work-passports-dated-extracts.md
surface:
  - src/shared/packages/pyforge-steward/**
  - scripts/lint_types.py
  - scripts/target_version_check.py
  - scripts/precommit_config_check.py
  - scripts/commit_msg_hook.py
  - scripts/pre_push_preflight.sh
  - scripts/_protected_refs_ruleset_lib.py
  - scripts/protected_refs_ruleset_check.py
  - .pre-commit-config.yaml
  - .github/workflows/lint-types.yml
  - scripts/llms_full_check.py
  - docs/reference/library-llms-full.md
  - .steward/keys-inventory.yaml
  - .steward/sync-config.example.yaml
  - .steward/repo-sets.example.yaml
  - recipes/bmad-eval-quality/**
  - evals/review-catches-planted-defect/**
  - src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/fresh_clone.py
  - src/shared/packages/pyforge-steward/tests/unit/test_fresh_clone_class_path.py
  - .github/workflows/pyforge-pip-install.yml
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-install-class-wiring/install-class-playbook.md
  - recipes/bmad-suite/recipe.yaml
  - recipes/bmad-suite/suite-members.yaml
  - .claude/skills/conda-forge-expert/scripts/bmad_suite_metapackage.py
  - .claude/scripts/conda-forge-expert/bmad_suite_metapackage.py
  - .claude/skills/conda-forge-expert/scripts/_http.py
  - docs/reference/pixi-config-jfrog.example.toml
  - docs/dreams/mcp-era-isolation.md
  - src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py
  - src/platform/config/asgi.py
  - src/platform/deploy/charts/platform/
  - pixi.toml    # its [feature.mcp-host] and [feature.python-agent-platform] tables (re-pointed 2026-10-15: a surface glob names files, not TOML tables)
  - scripts/mcp_factory_stdio_translator.py
  - docs/dreams/mcp-host-real-station-tools.md
  - src/platform/mcp_host/app.py
  - src/platform/mcp_host/settings.py
  - src/platform/compose/mcp-host/Containerfile
  - src/platform/deploy/charts/platform/templates/_helpers.tpl
  - src/platform/deploy/charts/platform/templates/mcp-host-deployment.yaml
  - src/platform/deploy/charts/platform/templates/networkpolicy-egress.yaml
  - src/platform/deploy/charts/platform/templates/networkpolicy-postgres-ingress.yaml
  - src/shared/packages/django-marshal/src/django_marshal_portal/mcp_asgi.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/publisher_host.py
  - src/platform/config/settings/local.py
  - src/platform/tests/policy/test_platform_dev_local_leaf.py
  - scripts/platform_ci_test_requirements_check.py
  - src/platform/Containerfile
  - scripts/platform_image_pip_layer.py
  - scripts/platform_object_storage.py
  - scripts/build-pixi-mirror.py
  - scripts/platform-golden-path-promotion.sh
  - scripts/platform-deploy-verify-promotion.py
  - scripts/platform-ci-local.sh
  - scripts/sbom_laptop_gate.py
  - tests/scripts/test_sbom_laptop_gate.py
  - scripts/sbom_gap_derive.py
  - tests/scripts/test_sbom_gap_derive.py
  - docs/foundry/sbom-gaps.md
  - scripts/upstream_todos_check.py
  - tests/scripts/test_upstream_todos_check.py
  - docs/foundry/upstream-todos.yaml
  - docs/foundry/upstream-drafts/**
  - docs/how-to/track-upstream-todos.md
  - scripts/pixi_env_matrix.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/workspace.py
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md
  - recipes/mybmad-dashboard/wrapper/src/mybmad_dashboard/launcher.py
  - Containerfile
  - .dockerignore
  - scripts/container-gates
  - scripts/guild_image_ci.sh
  - docs/governance/pin-policy.yaml
  - docs/governance/pin-policy.schema.json
  - docs/governance/ci-surfaces.yaml
  - docs/governance/ci-surfaces.schema.json
  - scripts/pin_policy_check.py
  - scripts/ci_surface_gates.py
  - scripts/pages_build_stamp.py
  - scripts/pages_fleet_status.py
  - scripts/pages_artifact_download.py
  - scripts/_ci_surface_gates_lib.py
  - tests/scripts/test_ci_surface_gates.py
  - scripts/pin_policy_lib.py
  - scripts/pin_policy_restore.py
  - tests/scripts/test_pin_policy_check.py
  - tests/scripts/test_pin_policy_restore.py
  - tests/scripts/fixtures/pin_policy/**
  - docs/governance/realization-register.yaml
  - docs/governance/realization-register.schema.json
  - scripts/realization_register_check.py
  - scripts/realization_register_lib.py
  - tests/scripts/test_realization_register_check.py
  - .github/workflows/pages.yml
surface-drift-exclude:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/asgi.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/consumers.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/dashboard/routing.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py
  - src/platform/config/asgi.py
companions:
  - ../../architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
sources:
  - ../../../../../../docs/dreams/pyforge-steward.md
---

> **Canonical contract.** Derived from `.memlog.md` (steward one-chain fold 2026-09-17) and the Dream in `sources:`. Do not hand-edit — append the memlog and re-derive.

# Steward (pyforge-steward) — the estate the factory stands on

## Why

A mandate this repo has already paid for meeting late, twice: `_http.py` attached the `JFROG_API_KEY` auth header to every outbound request regardless of destination host until a human caught it, and on 2026-07-24 a committed `sk-ant` key needed git history rewritten and the key rotated. Both are the same underlying gap — privilege that outlived its intended scope, caught after the fact rather than prevented — and nothing in the pyforge Guild owned "no privilege outlives its deployment" as a first-class responsibility until the 2026-07-23 ownership audit found Deployment & Operations orphaned. Steward (module `pyforge.steward`, CLI `steward`) is that station: it provisions the engines the factory runs on, deploys the services it ships, holds the keys that guard it, and enforces the budget ceilings that bound it. It is not a new platform — domain and technical research both converge on the same verdict: a thin CLI formalizing what this repo's maintainer already does by hand, cloning the already-shipped `pyforge-warden` packaging pattern rather than reimplementing Vault, Backstage, ArgoCD, or Kubecost at a scale this one-person factory doesn't have.

## Capabilities
- **CAP-1 — from spec-pyforge-steward** ← spec-pyforge-steward CAP-1 (shipped 2026-09-16)
  - **intent:** An operator can issue, scope, rotate, audit, inventory, and record revocation of credentials through one CLI (`steward keys`), with the historical `JFROG_API_KEY` cross-host leak pattern closed as a named automated regression test.
  - **success:** A credential declared with an explicit host allowlist is never attached to a request outside it; `encrypt`/`decrypt` round-trips a fixture exactly via `age`; `rotate` re-encrypts every secret under a newly generated identity and the old identity fails to decrypt afterward, with no calendar/cron auto-rotation path; `audit --drift` reports the historical unconditional-injection pattern against a fixture and reports clean against today's fixed `_http.py`; `list` enumerates identities with scope/last-rotated metadata and never prints a raw secret value under any flag; `revoke` marks an identity retired and prints manual remediation guidance with zero third-party API calls; a dedicated conformance test fails loudly if the host-gating logic is ever removed or bypassed.
- **CAP-2 — from spec-pyforge-steward** ← spec-pyforge-steward CAP-2 (shipped 2026-09-16)
  - **intent:** An operator can build and publish the Pages dashboard through one reconciled command (`steward deploy dashboard`) instead of hand-running `dashboard-gen` + `git push`.
  - **success:** Running twice with no source change between runs results in zero commits on the second run; a real change to the generated output results in exactly one new commit containing exactly the changed files, pushed to the existing Pages-serving branch; `--dry-run` performs the build+diff and prints it without committing or pushing; `status` reports the last successful deploy's commit SHA and timestamp read from Git history alone, with no separate state store.
- **CAP-3 — from spec-pyforge-steward** ← spec-pyforge-steward CAP-3 (shipped 2026-09-16)
  - **intent:** An operator or an unattended bmad-loop session can materialize any named pixi environment or a bmad-loop runner+environment together, list what exists, and verify the `environment.yaml` sync gate, without recalling raw pixi/`bmad-loop-worktree` syntax.
  - **success:** A valid environment name materializes via `pixi install -e`; an invalid name reports a clear error listing valid names rather than surfacing pixi's raw error; `--runner bmad-loop --env <name>` wraps `scripts/bmad-loop-worktree` to materialize a worktree plus its named environment in one call, surfacing underlying failures clearly rather than leaving orphaned state unreported; `--list` enumerates every `pixi.toml` `[environments]` entry with its composing features (plus `--json`); `--verify` wraps the existing sync-gate check and reports drift with a non-zero exit when out of sync.
- **CAP-4 — from spec-pyforge-steward** ← spec-pyforge-steward CAP-4 (shipped 2026-09-16)
  - **intent:** An operator can declare and query a machine-readable resource ceiling and get an honest signal about spend rather than a fabricated number.
  - **success:** `budget set --cap <amount><currency>/<period>` records a stable, documented schema and rejects a malformed cap value without writing a corrupt entry; `budget show` prints the declared ceiling(s) in human and `--json` form, and reports clearly (not a crash or misleading zero) when none is declared; `budget check` returns one of three distinct exit codes — not-configured / under-budget / over-budget — never collapsing "no data" into a pass, with no cloud-cost-SDK or Kubecost/OpenCost/Infracost client import anywhere in the codebase.
- **CAP-5 — `pyforge-guild`: one minimal environment is the default for every agent and harness** ← spec-pyforge-steward CAP-5 (shipped 2026-09-16; size bound restated 2026-09-28)
  - **intent:** A pixi feature + environment `pyforge-guild` carries the current state of PyForge — `pyforge-core`, `pyforge-doctor` (with its warden / testing-kit seam), `pyforge-marshal`, `pyforge-steward`, plus `pyyaml`, `ruamel.yaml`, `jsonschema`, `tomli`, `pytest` — **and the token-economy kit Marshal detects at runtime**: the `python` feature (`nodejs` for `npx skills add caveman`, `gh`, `bmad-method`) and `headroom-ai` declared explicitly (corrected 2026-09-16: the lean `pyforge-marshal` env has `bmad-loop` and `tmux` but no `headroom`, and Marshal degrades silently on its absence, `MRS-DISP-033`) — and nothing of the recipe factory. The 51 Guild/planning tasks (every `*-check` detector, `detectors` / `detectors-ci`, `sprint-ledger-sync`, `fleet-picture`, `governance-currency`, and the `pr-preflight` / `pyforge-station-tests` / `pyforge-station-coverage-gates` aggregates) **move** from `[feature.local-recipes.tasks]` to `[feature.guild-tasks.tasks]` — a tasks-only feature, because station packages range-pin engines the factory floats (found at the first solve: warden `osv-scanner <2.5` vs `>=2.5.1`, marshal `tomlkit <0.13.3` vs `>=0.15.1`), so a deps-carrying feature can never be included by `local-recipes`; the `local-recipes` environment *includes* `guild-tasks`, so every existing `pixi run -e local-recipes <task>` keeps working. `pyforge-warden` is not in the env: doctor does not require it at runtime and degrades that seam to cannot-evaluate, as `detectors-ci` always has in `local-recipes` while `local-recipes` becomes what it already is in practice — Mason's factory environment. Foundry mode `rebuild`: B re-derives the same split.
  - **success:** `pixi install -e pyforge-guild` from cold lands under **2 GB** on disk — the bound restated 2026-09-28 (operator ruling) at the measured size plus headroom, so the criterion checks growth instead of failing on its first day. It was 1 GB (**measured 2026-09-16: 859 MB, `detectors-ci` 32/32 — Story 63.1**); a cold install measured 1.5 GB on 2026-09-28 before `pyforge-mason` joined (`du -sm` 1,461 MiB, 243 packages), and Story 72.1 records the size with `pyforge-mason` (estimated +50 packages, ~146 MB) against the new bound (`local-recipes`: 10 GB). And `pixi run -e pyforge-guild detectors-ci` is green on `main`; `pixi run -e pyforge-guild marshal seed check` reports the headroom kit item present and a dispatch dry-run raises no `MRS-DISP-033`; `marshal-token-economy` Epic 46 names `pyforge-guild` as the environment its stories are verified in; `AGENTS.md`, `CLAUDE.md`, `.cursor/rules/*.mdc`, the eight station `SKILL.md` files and the cloud-environment install command name `pyforge-guild` as the session default; scribe recall stays `-e pyforge-scribe`; `environment.yaml` regenerated in the same PR; `pyforge-station-tests` green (shared surface).
- **CAP-6 — Frame draft re-grounding: the estate claims conformance the way the draft now asks** ← spec-pyforge-steward CAP-6 (shipped 2026-09-16)
  - **intent:** (a) the nine Frames drop the invented version token — bare `type: frame` (draft §6.2.1, 09-14: a document written to the draft omits the token until a release assigns one); (b) `docs/foundry/frames/README.md` carries an **Upstream pin** block naming the openteams-ai/frame-spec#28 and #29 head SHAs we conform to, re-pinned only with a memlog line; (c) an opt-in steward task `frame-upstream-check` fetches frame-spec at the pinned #29 SHA into a temp dir and runs its `validate_frame.py` over `docs/foundry/frames/` and `--check-profile` over our profile — never vendored, never a gate, never a write upstream; (d) PyForge **publishes its conformance profile** `docs/foundry/frames/conformance-profile.yaml` (§7 MUST; #29 YAML shape; `specification: draft-mcandrew-frame-spec-00`): reads Markdown, writes none, resolves no composition, `visibility` is declared intent, and — §9 — declares that no trust configuration exists yet so every reachable source is trusted, which is exactly the state the future loader must change.
  - **success:** upstream `validate_frame.py` at the pinned SHA reports 9/9 OK and `--check-profile` accepts the profile; in-repo `frame-preflight` stays green; the deferred-work accepted-risk entry on #28 carries today's date and the two SHAs.
- **CAP-7 — Suite membership** ← spec-bmad-eval-quality CAP-1 (shipped 2026-09-09)
  - **intent:** `eval-quality` installs the suite's way as a `bmad-suite` member (recipe, manifest line, pixi pin, channel) so every fleet consumer gets the tagged binary that has `score`.
  - **success:** `recipe-build` green; `eval-quality --version` prints the **pinned TAG version** (`1.4.1` today — `recipes/bmad-eval-quality/recipe.yaml:5,:35`), `--help` lists `score`, `compile` on a shipped corpus contract exits 0; enrolment is ONE line in `recipes/bmad-suite/suite-members.yaml` (auto-flows to metapackage run deps, doctor's drift watch, steward's pipeline-truth); pixi pin `bmad-eval-quality >=1.4.1` (`pixi.toml:1611`) with `environment.yaml` regenerated; baseline pin set, install-matrix, install-class and `library-llms-full.md` rows present; the PR carries `maintenance`. - **verified:** 2026-09-11 — live in the `local-recipes` env: `eval-quality --version` -> `1.4.1`; `--help` lists `score`; `compile --in .../corpus/dev/contracts/satisfied-declarations.json` exits 0; `recipes/bmad-suite/suite-members.yaml:47` carries the `bmad-eval-quality` entry; `pixi.toml:1679` pin reads `>=1.4.1` (the recipe itself moved to 3.0.0 this session, PR #1205 — the pixi floor is deliberately held at 1.4.1 pending a `__win` build, see the pin's own comment; CAP-1's "1.4.1 today" text is therefore still literally accurate for what's installed, not stale).
- **CAP-8 — Pilot contract `review-catches-planted-defect`** ← spec-bmad-eval-quality CAP-2 (shipped 2026-09-09)
  - **intent:** one Behavioral Evaluation Contract, run twin-arm (clean vs one planted `file:line` defect) against the `edge-case-hunter` review layer bmad-loop relies on, yields a catch rate the fleet can read.
  - **success:** the contract compiles; a one-trial twin-run preflights both arms, the mutated arm's review cites `pkg/discount.py:17` and the clean arm does not; three trials per arm yield a policy-comparable strength vector with a catch rate; pixi tasks `eval-quality-smoke`, `eval-quality-review-twin-run -- --trials N`, `eval-quality-review-replay` exist and are never wired into `detectors`. *Known limitation (empirical, live `--trials 3` runs):* the clean arm is a reproducible false-positive source — `edge-case-hunter`'s exhaustive-enumeration methodology finds a different real boundary concern at the same line every time; see `.memlog.md` for detail. - **verified:** 2026-09-11 — `eval-quality-smoke` (`evals/review-catches-planted-defect/driver.py`) and `test_driver.py` (8/8) both pass; found and fixed a real regression while checking: the pilot contract had drifted to a stale `schemaVersion: 3` against the installed CLI's `4` (`compile` exit 5, `schema-version-mismatch`) — a one-line bump to `4` (no other field changed) restored a clean `compile` exit 0 for both the shipped dev corpus and this contract. The three pixi tasks (`eval-quality-smoke`, `-review-twin-run`, `-review-replay`) exist and stay out of `detectors`/`detectors-ci`, confirmed by their own task descriptions. A live `--trials N` `claude -p` twin-run (the catch-rate / `pkg/discount.py:17` citation claim) is NOT re-exercised in this pass — real API cost and wall-clock, disproportionate to a doc-hygiene sweep; that behavior is unverified, not disproven.
- **CAP-9 — Pre-flight diff (report-only)** ← spec-bmad-method-core-upgrade CAP-1 (shipped 2026-09-09)
  - **intent:** given the installed manifest and a target release, report skill adds/removes/renames (shim disposition + `removals.txt` deletions), upstream-touched files the repo has locally modified, `_bmad/custom/**` overrides that stop applying (the legacy-name unattended-halt trap), and new hard prerequisites (e.g. `uv`).
  - **success:** run against the 6.10.0→6.11.0 pair, it retrodicts the 2026-08-21 findings (companion, § Traps).
- **CAP-10 — Deliberate, reviewable apply** ← spec-bmad-method-core-upgrade CAP-2 (shipped 2026-09-09)
  - **intent:** wrap `bmad-method install --action update -y` non-interactively: branch/snapshot first, never a silent overwrite of `_bmad/custom/**`, installer diff landed for review — never applied blind in place.
  - **success:** a clean run lands the installer diff on a review branch with the custom-surface checklist executed.
- **CAP-11 — Custom-surface reconciliation** ← spec-bmad-method-core-upgrade CAP-3 (shipped 2026-09-09)
  - **intent:** after apply, detect clobbered repo-custom surfaces — `resolve_config.py`'s multi-project layers 5/6 is the named recurring case, clobbered in BOTH manual upgrades — and re-apply or flag them.
  - **success:** post-apply, `bmad-switch --current` and a `BMAD_ACTIVE_PROJECT` override both resolve the six layers; the installer's `.bak` is accounted for.
- **CAP-12 — Downstream pin fan-out report (report-only)** ← spec-bmad-method-core-upgrade CAP-4 (shipped 2026-09-09)
  - **intent:** enumerate every pin site the release moves — root `pixi.toml` floors, marshal's pyproject + package `pixi.toml` + `HARNESS_VERSION_RANGE_TEXT` + seed manifest/drift-test map, loop-home hook relays — and report moved vs. not.
  - **success:** names exactly the sites the 2026-08-21 session had to touch, none discovered later by red tests.
- **CAP-13 — Post-apply verification gate** ← spec-bmad-method-core-upgrade CAP-5 (shipped 2026-09-09)
  - **intent:** run the repo's own gates (bmad-drift-check integrity, CFE skill meta-tests, `bmad-loop validate` per loop home including the `init` relay refresh) and report one verdict.
  - **success:** reproduces the 2026-08-21 checklist (8/8 loop homes validate clean) in one command.
- **CAP-14 — Non-interactive installer drive** ← spec-bmad-method-core-upgrade CAP-6 (shipped 2026-09-09)
  - **intent:** the apply drives the installer on purpose, not by luck — `--directory <repo>`, `--modules <every module the installed manifest lists>` (core, bmm, each `source: custom` module), stdin closed, node and `bmad-method` resolved from the repo's pixi env when absent from PATH — and an exit-0 run that changed nothing is a refusal, never a green.
  - **success:** a re-run of the 2026-09-06 apply from a clean tree lands the 6.12 installer diff with no wrapper script.
- **CAP-15 — Custom-module awareness** ← spec-bmad-method-core-upgrade CAP-7 (shipped 2026-09-09)
  - **intent:** every `source: custom` module in `_bmad/_config/manifest.yaml` (today skf) is selected for the core apply; its config files (named in the release catalog) are snapshotted before and restored after; its own installer runs after the core apply so its module tree, undeclared skills and shared resources land coherently; an optional catalog pin stops the channel-`next` cache drift.
  - **success:** after apply the module's skill dirs equal its packaged source and its config equals the pre-apply bytes plus the installer's own appended keys; the report names each restored file.
- **CAP-16 — Local-customization scan and re-apply** ← spec-bmad-method-core-upgrade CAP-8 (shipped 2026-09-09)
  - **intent:** before apply, every installer-owned file is compared against the cached package of the installed version and the customized ones are listed in the CAP-1 report (the Dream's own first when-real bullet, which CAP-1 had narrowed to marker-carrying scripts); after apply each is re-applied by three-way merge onto the new upstream copy, clean merges written, conflicts flagged with the hunk kept beside the report. `resolve_config.py` takes the same path — the old→new upstream delta is replayed on the restored copy, not discarded.
  - **success:** the 2026-09-06 seven-file case re-applies with six clean merges and one flagged conflict (step-01 `done` routing).
- **CAP-17 — Deliberate shim retirement (`--no-shims`)** ← spec-bmad-method-core-upgrade CAP-9 (shipped 2026-09-09)
  - **intent:** the apply can retire every deprecation shim on purpose — `--no-shims` on the installer argv after `--modules`, the pre-flight names each shim to retire (21 at 6.12.0), a same-version run is accepted as a retirement run, and the flag is refused while a legacy-name custom file exists (trap 2).
  - **success:** the manifest reads `installShims: false`, the shim rows leave `skill-manifest.csv`, CAP-7 and CAP-8 run on the same apply, `prove-landed` validates 8/8 (Story 14.9). **Correction (2026-09-06, found during Story 30.5):** the original Intent also refused `--no-shims` "while the marshal harness / any rendered loop-home policy still emits `bmad-dev-auto`" — this premise is FALSE, verified directly against the installed `bmad_loop` 0.11.1 package source (`bmad_loop/policy.py`). `DevPolicy.skill` is a PERMANENT internal adapter discriminator (`DEV_SKILLS = {"bmad-dev-auto"}`, hard-validated by `PolicyError` on any other value) — it is not a "which skill name is current" field, and the skill actually invoked is resolved separately at runtime from what is on disk (`Engine._dev_skill()` / `install.dev_primitive_or_default`), independent of this field. Every real loop-home's `policy.toml` (and the vendored `harness_bmadloop.py` template that renders it) will ALWAYS emit this literal, forever, by design — a refusal keyed on finding it provides no real signal about `--no-shims` readiness and would refuse every retirement attempt permanently. This clause is REMOVED: the harness-template / loop-home-policy check (`_shim_retirement_blockers` / `refuse_shim_retirement_not_ready`) is deleted from `upgrade.py`. The sole pre-apply refusal for `--no-shims` remains the pre-existing, unconditional legacy-custom-name check (trap 2, `refuse_legacy_custom`), which is unaffected by this correction.
- **CAP-18 — one-command module provisioning** ← spec-bmad-module-provisioning CAP-1 (shipped 2026-09-09)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** See absorbed Spec memlog and git history.
- **CAP-19 — module discovery** ← spec-bmad-module-provisioning CAP-2 (shipped 2026-09-09)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** See absorbed Spec memlog and git history.
- **CAP-20 — partial state is named, never silent** ← spec-bmad-module-provisioning CAP-3 (shipped 2026-09-09)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** See absorbed Spec memlog and git history.
- **CAP-21 — Pipeline-truth report** ← spec-bmad-suite-channel-product CAP-1 (shipped 2026-09-09)
  - **intent:** one command reports, for each of the 13 packages: upstream latest (npm AND GitHub, per its class), recipe version, channel version, installed version, wired-or-not — drift named per stage.
  - **success:** run against the 2026-08-22 state it reproduces the research matrix (including the 6.3.0 relic until refreshed); offline it degrades fail-open per stage. *(Shipped: steward 15.1; class-correct `wired` since 31.2. Known hole, relayed: for the installer-tree class the `installed` stage reads the pixi env's conda-meta, not the applied `_bmad/_config/manifest.yaml`.)* - **verified:** 2026-09-11 — `steward suite pipeline-truth --json` live: 13/13 packages reported, all 5 stages present per package, drift correctly named (`bmad-builder`/ `bmad-creative-intelligence-suite`: `upstream_npm_github_divergence`; `bmad-eval-quality`: `installed` — the live, deliberate G115 pin cap from this session's own PR #1205). Offline fail-open degrade not re-exercised (would require simulating a network outage).
- **CAP-22 — End-to-end advance** ← spec-bmad-suite-channel-product CAP-2 (shipped 2026-09-09)
  - **intent:** one command takes a stale package through autotick (tag-mode, or a new HEAD-advance mode for the six commit-pinned dev recipes) → build → test → publish → listing verified, landing as a reviewable PR — never auto-merged.
  - **success:** replays the 2026-08-21 seven-stage hand ritual for one package with zero improvised steps. *(Shipped: steward 15.2; `anaconda upload` stays the operator's step by design.)* - **verified:** 2026-09-11 — `steward suite advance --help` confirms the chain (autotick tag|head → build → test → publish → listing → reviewable PR, never auto-merged); `tests/unit/test_suite_advance.py` (9/9 pass) directly covers the never-auto-merged contract (`test_advance_dry_run_chain_tag_mode_never_merges`, `test_advance_refuses_open_pr_hook_that_claims_merge`), HEAD-advance mode for commit-pinned recipes, and the 13-package roster. A live end-to-end `advance` run against a real stale package (real network/publish/PR) not re-exercised — disproportionate to a doc-hygiene sweep.
- **CAP-23 — Module wiring through the verb** ← spec-bmad-suite-channel-product CAP-3 (shipped 2026-09-09)
  - **intent:** `steward provision --module` grows `_SUPPORTED_MODULES` from `{bmb}` to `{bmb, tea, cis, utility-skills, manticore}` — each addition manifest-recorded, skill-name-collision-checked, retired-ID guard + integrity meta tests green, reproducible on a fresh clone. WDS is an explicit skip (deprecated in 6.12.0's module registry, folded into `bmad-ux`; retired from the roster 2026-09-05).
  - **success:** all five wire-decided modules provision through the verb and `.claude/skills` gains the expected skill sets. *(Shipped: steward 15.3.)* - **verified:** 2026-09-11 — `steward provision --module` live at `provision.py`, confirmed supporting exactly `{bmb, cis, manticore, tea, utility-skills}` (5, matches WDS-excluded roster); same live check + 104-test coverage as `spec-bmad-module-provisioning` CAP-1 (that spec's own `verified:` line, this same sweep).
- **CAP-24 — Dual-path contract** ← spec-bmad-suite-channel-product CAP-4 (shipped 2026-09-09)
  - **intent:** the per-package install matrix (pixi command + native command with upstream citation + hazard flags, recounted 2026-09-05: npm-invisible ×6, npm-stale-GitHub-canonical ×3, name-collisions ×3, G109 renumber ×2; eight native classes) is a tracked artifact (`install-matrix.md`), and the upgrade verification gate spot-checks one native path per class instead of trusting docs.
  - **success:** the matrix exists cited; a gate run exercises ≥1 command per class. *(Shipped: steward 15.4 + Epic 31; matrix re-verified 2026-09-05 against `pipeline-truth`.)* - **verified:** 2026-09-11 — `install-matrix.md` (71 lines) exists, cites upstream READMEs per package, cross-checked against a live `pipeline-truth` run per its own header; the per-class gate spot-check is real code at `upgrade.py:3452` (`# CAP-4 dual-path native-class advisory spot-checks`). Matrix content itself is a dated 2026-09-05/09 snapshot (a currency question, not this CAP's contract, which only requires the matrix to exist and be cited).
- **CAP-25 — Ambient drift, relayed to doctor** ← spec-bmad-suite-channel-product CAP-5 (shipped 2026-09-09)
  - **intent:** channel-vs-recipe and recipe-vs-upstream join doctor's suite-drift surfaces (fail-open, warn-only), and the GitHub-releases fallback (doctor DW-14-1-1) unblinds the 7 npm-invisible packages.
  - **success:** a fixture of the 6.3.0 relic fires channel-drift; the fallback names bmad-loop's version from GitHub. *(Shipped: doctor 15.1/15.2 + 19.1. Known hole, relayed: suite drift maps 7 of 13 members — commit-pinned members unmapped.)* - **verified:** 2026-09-11 — `test_sources_bmad_method.py` 157/157 pass, including `test_the_6_3_0_relic_fixture_fires_channel_drift_warn` (exact success-clause match) and 9 `fetch_latest_github_release_*` tests covering the fallback (404-falls-back-to-tags, malformed/missing data folds to `None`, never raises).
- **CAP-26 — Suite metapackage (2026-09-01)** ← spec-bmad-suite-channel-product CAP-6 (shipped 2026-09-09)
  - **intent:** one conda metapackage (`bmad-suite`) plus canonical manifest install all 13 channel products at upstream-aligned pins; the generator refreshes from the registry class per member.
  - **success:** decomposed in `spec-bmad-suite-metapackage` and shipped as steward Epic 39 (39.1–39.4): `recipes/bmad-suite/{recipe.yaml, suite-members.yaml}`, `generate-bmad-suite` / `build-bmad-suite`, opt-in `feature.bmad-suite-full`; `bmad-suite 2026.9.5` on the channel; doctor Epic 19 consumes the same manifest for its watched set. - **verified:** 2026-09-11 — this session's own PR #1205 exercised the full chain live: `generate-bmad-suite --dry-run` resolved live upstream pins per registry class, a real `recipe-build recipes/bmad-suite` produced a green metapackage (`bmad-suite-2026.9.11`, all anchor-CLI tests passed), and `feature.bmad-suite-full` is present at `pixi.toml:1989`. Metapackage version is now `2026.9.11`, not `2026.9.5` — a currency fact, not a contract break; the mechanism this CAP describes is what was just used to produce it.
- **CAP-27 — Class-keyed playbook** ← spec-bmad-suite-install-class-wiring CAP-1 (shipped 2026-09-17)
  - **intent:** one tracked companion tells the operator, for each of the six non-module pieces, the pixi path, the native wire (cited from the upstream README / `install-matrix.md`), and the steward verb or task — discoverable from `steward provision --help` (or an equivalent CLI pointer), not tribal knowledge.
  - **success:** the playbook exists, cites the matrix, and `provision --help` names it. - **verified:** 2026-09-11 — `install-class-playbook.md` exists (84 lines), cites `install-matrix.md` and `steward provision --prove-class-path`; live `steward provision --help` names the playbook path verbatim under "Non-module suite pieces".
- **CAP-28 — Class-correct wired-or-not** ← spec-bmad-suite-install-class-wiring CAP-2 (shipped 2026-09-17)
  - **intent:** the pipeline-truth report's `wired-or-not` column uses per-class predicates (installer tree / runner home / plugin enabled / VS Code extension / scaffold N/A), not a boolean only `--module` targets can satisfy.
  - **success:** run against a fresh clone it names each of the six by class without claiming "wired" for template-into-this-repo. - **verified:** 2026-09-11 — live `pipeline-truth --json`: all six non-module classes report distinct per-class predicates (`bmad-method`: "installer tree present"; `bmad-loop`: "runner home provisionable"; skill-forge: "own installer present"; `bmad-labs-skills`: "wired"; both dashboards: "VS Code extension / web runnable"; `bmad-module-template`: "n/a — not a wireable module") — none collapsed to a bare boolean.
- **CAP-29 — Fresh-clone class-path** ← spec-bmad-suite-install-class-wiring CAP-3 (shipped 2026-09-17)
  - **intent:** a fresh clone can reach "method core installed, loop runner provisionable via `--runner`, skf skills present via its own installer, labs plugin path documented, dashboard install task runnable, template N/A unless scaffolding" without hand-driving npm `Installer` classes from a chat transcript.
  - **success:** a recorded fresh-clone run (or CI equivalent) reaches that state with zero improvised steps. - **verified:** 2026-09-11 — live `steward provision --prove-class-path --json`: all six classes report `expected == actual` (`ok: true`) with no improvised step; `.github/ workflows/pyforge-pip-install.yml` runs this same class-path resolution with no pixi workspace present; `test_fresh_clone_class_path.py` 10/10 pass.
- **CAP-30 — Adoption register governs wiring** ← spec-bmad-suite-lifecycle CAP-1 (shipped 2026-09-13)
  - **intent:** every suite member has a recorded verdict (wield | skip), wielding station, provisioning path, hazards and status in `adoption-register.md`; a member's wiring changes only by changing its row.
  - **success:** pipeline-truth's `wired` column agrees with the register for 13/13; the channel-product "never wire-everything" constraint and the one-front-door row-6 triage are recorded as superseded/closed by memlog.
- **CAP-31 — Module wave lands by install class** ← spec-bmad-suite-lifecycle CAP-2 (shipped 2026-09-13)
  - **intent:** `steward provision --module utility-skills | tea | bmb` (and a CIS re-provision) place each module's skills in `.claude/skills/` with manifest sections — never a hand copy.
  - **success:** `--list-modules` reports the four installed; the retired-ID guard and integrity meta-tests stay green; the ten CIS `SKILL.md` carry `--project-root`; a test proves bmb's `cleanup-legacy.py` is never invoked.
- **CAP-32 — Station routing** ← spec-bmad-suite-lifecycle CAP-3 (shipped 2026-09-13)
  - **intent:** each adopted skill has exactly one wielding station, recorded in that station's persona skill (the one durable home); AGENTS.md carries one pointer line to the register, never per-skill lines.
  - **success:** the routing table in `adoption-register.md` maps every adopted skill to one station, each persona skill cites it, a meta-test proves one persona per skill dir, and CLAUDE.md carries none of it.
- **CAP-33 — TEA full adoption** ← spec-bmad-suite-lifecycle CAP-4 (shipped 2026-09-13)
  - **intent:** TEA's `bmad-testarch-*` workflows produce every station's `planning-artifacts/test-architecture.md`; `tea-test-review` runs as a Marshal review lens and a Warden advisory finding; the repo generator, its two meta-tests and two pixi tasks retire.
  - **success:** 8/8 documents regenerated by TEA with an equivalence check recorded against the generator's last output; `tea-test-review --base origin/main --min-score N` exits with a real code on a fixture PR; generator and tests deleted in the same story; Warden's verdict unchanged.
- **CAP-34 — Manticore studio for Herald** ← spec-bmad-suite-lifecycle CAP-5 (shipped 2026-09-13)
  - **intent:** Herald renders a station video from a deck's speaker notes through manticore installed in a dedicated studio root outside this repo's `_bmad/`.
  - **success:** the studio provisions via `--custom-source` with `[modules.manticore]` in its own `_bmad/custom/config.toml`; one station `.mp4` renders and is gitignored; this repo's `_bmad/` is byte-identical before and after.
- **CAP-35 — labs-skills by consent** ← spec-bmad-suite-lifecycle CAP-6 (shipped 2026-09-13)
  - **intent:** exactly the consented skills — `mcp-builder` (Atlas), `slides-generator` (Herald), `multi-repo-git-ops` (Marshal), `release-please` (Steward) — are installed by name.
  - **success:** each has a register row and lands via the one steward-wrapped, pinned writer (`steward provision --plugin labs --skill <name>`); no other labs skill is present.
- **CAP-36 — eval-quality pilot runs** ← spec-bmad-suite-lifecycle CAP-7 (shipped 2026-09-13)
  - **intent:** the designed twin-run contract measures the `edge-case-hunter` reviewer against a planted `file:line` defect under a per-trial budget ceiling.
  - **success:** `eval-quality-smoke`, `eval-quality-review-twin-run`, `eval-quality-review-replay` exist as pixi tasks; one trial cites `pkg/discount.py:17` on the mutated arm and not on the clean arm; none joins `detectors` (Story 45.2, spec-bmad-eval-quality CAP-2).
- **CAP-37 — Release cadence is one runbook** ← spec-bmad-suite-lifecycle CAP-8 (shipped 2026-09-13)
  - **intent:** every BMAD-METHOD release goes detect → apply → align → refresh → flip through `release-cadence.md` with named owners; the `@next` prerelease is its optional rehearsal.
  - **success:** the next release is processed with zero improvised steps against the runbook; the rehearsal recipe (throwaway worktree, `--installer npx bmad-method@next`, planted conflict, PATH without node) has run once, report-only.
- **CAP-38 — BMAD-estate cutover readiness** ← spec-bmad-suite-lifecycle CAP-9 (shipped 2026-09-13)
  - **intent:** every prerequisite the cutover assumes about `_bmad/`, `.claude/skills/`, `_bmad-output/` and the loop homes is listed with an owner in `cutover-readiness.md`; untracked gaps are relayed to the cutover chain by memlog; the gate is every line green before Story 44.3 opens the foundry.
  - **success:** P1–P18 read green; G1–G11 each name a story; `steward upgrade bmad-core` pre-flight reports zero ungoverned local customizations.
- **CAP-39 — Shim retirement (relay)** ← spec-bmad-suite-lifecycle CAP-10 (shipped 2026-09-13)
  - **intent:** the 21 deprecated shims are gone and every live caller is glossed to the live skill id before the foundry opens.
  - **success:** callers are glossed (era-alignment CAP-12 / marshal 30.5), and one `--no-shims` apply lands `installShims: false` with 21 fewer skill dirs (core-upgrade CAP-9 / steward 14.9). **Correction (2026-09-06):** the original Success bar also named "the harness policy names `bmad-build-auto`, the 8 loop homes re-render and validate clean... the guard is widened to the harness file" — this is FALSE. `bmad_loop`'s `DevPolicy.skill` is a permanent internal adapter discriminator that must stay `"bmad-dev-auto"` forever (verified against the installed package); it is never renamed, the harness template is never touched, no loop-home re-render happens, and the retired-ID guard is never widened to that file. See era-alignment CAP-12's own correction and core-upgrade CAP-9's own correction for the full evidence.
- **CAP-40 — Canonical suite manifest** ← spec-bmad-suite-metapackage CAP-1 (shipped 2026-09-09)
  - **intent:** tracked `recipes/bmad-suite/suite-members.yaml` lists every channel product by conda name (13 active + deprecated local-only recipes), with `deprecated: true` for packages removed from SelfExplainML (`bmad-autopilot`, `bmad-dashboard-extension`, `bmalph`). Deprecated rows stay in the manifest for doctor/catalog completeness but are **never** written into the metapackage `requirements.run`.
  - **success:** doctor Story 19.1 reads it; steward pipeline-truth cross-checks active population against install-matrix. - **verified:** 2026-09-11 — `bmad_method.py:372` (`_SUITE_MANIFEST_REL`) and `:411` (`_manifest_suite_members`) read `recipes/bmad-suite/suite-members.yaml` directly; live `pipeline-truth --json` returned exactly 13 active members this session, matching the manifest.
- **CAP-41 — Metapackage recipe** ← spec-bmad-suite-metapackage CAP-2 (shipped 2026-09-09)
  - **intent:** `recipes/bmad-suite/recipe.yaml` is a `noarch: generic` metapackage whose `requirements.run` pins each manifest member at `>=` the resolved upstream version (exact `==` optional for lock-step refresh PRs). Own `context.version` is a CalVer refresh stamp bumped whenever any member version in the generated block changes.
  - **success:** `pixi run -e local-recipes recipe-build recipes/bmad-suite` succeeds; tests assert every manifest member appears in `requirements.run`. - **verified:** 2026-09-11 — this session's own PR #1205: `recipe-build recipes/bmad-suite` built `bmad-suite-2026.9.11` green with all anchor-CLI tests passing (`bmad-loop --version`, `bmad-module-skill-forge --help`, etc.); `requirements.run` carries all 13 active members (verified by direct read).
- **CAP-42 — Generator / refresh command** ← spec-bmad-suite-metapackage CAP-3 (shipped 2026-09-09)
  - **intent:** one command (steward duty or CFE script) resolves upstream latest per member using registry class from each member's `recipes/<name>/recipe.yaml`, rewrites the metapackage pin block + version stamp, and prints a diff summary (member, old pin, new upstream, registry used).
  - **success:** dry-run against live upstream reproduces the 2026-09-01 channel table within one patch version; github-primary packages never consult stale npm. - **verified:** 2026-09-11 — this session's own `generate-bmad-suite --dry-run` resolved live upstream per member (`[npm+floor]`/`[github+floor]`/`[recipe-floor]` tags shown per member in the diff summary), correctly flagged only `bmad-method-test-architecture-enterprise` and `bmad-eval-quality` as changed and everything else unchanged.
- **CAP-43 — Channel publish + pixi feature (optional follow-on)** ← spec-bmad-suite-metapackage CAP-4 (shipped 2026-09-09)
  - **intent:** publish `bmad-suite` to SelfExplainML; add optional `feature.bmad-suite-full` in `pixi.toml` that depends on `bmad-suite` instead of enumerating members.
  - **success:** `pixi install -e local-recipes` with feature enabled resolves the bundle; documented in install-matrix. - **verified:** 2026-09-11 — the served `conda.anaconda.org/selfexplainml/noarch/repodata.json` lists real published `bmad-suite` builds (2026.9.1, 2026.9.5, 2026.9.9 — 2026.9.11 from this session not yet uploaded, an operator step by design); `feature.bmad-suite-full` at `pixi.toml:1989`; `tests/packaging/test_bmad_suite_full_feature.py` 9/9 pass.
- **CAP-44 — published measure catalog** ← spec-build-league-scorecard CAP-1 (shipped 2026-09-15)
  - **intent:** an operator-authored set covering human, agent, and team,
  - **success:** the eight first-cut ids are in `measure-catalog.md` and
- **CAP-45 — add, switch, and archive sources** ← spec-build-league-scorecard CAP-2 (shipped 2026-09-15)
  - **intent:** a new already-counted source is a new row; a dead source is
  - **success:** a new row starts `off`; flipping `on` / `off` / `archived`
- **CAP-46 — consumers cite `on` rows only** ← spec-build-league-scorecard CAP-3 (shipped 2026-09-15)
  - **intent:** Herald, Atlas, Marshal, and Doctor (and Hub Outcome Guards
  - **success:** citing `off` or `archived` — or an id not in the catalog —
- **CAP-47 — scorecard board / league table** ← spec-build-league-scorecard CAP-4 (shipped 2026-09-15)
  - **intent:** a board is not a Canopy CAP and is not this first epic.
  - **success:** the slot exists; v1 does not implement a UI.
- **CAP-48 — bootstrap verbs** ← spec-developer-machine-bootstrap CAP-1 (shipped 2026-09-09)
  - **intent:** `steward init` (prereq detection with floors from the pixi version registry), `shell-init`, `setup` (clone + pixi install + hooks), `initrepo` — fresh machine to validate-fast green.
  - **success:** the flow reproduces in a clean container; every prereq failure names its remedy.
- **CAP-49 — runtime-driven routing** ← spec-enterprise-airgap CAP-1 (shipped 2026-09-09)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** See absorbed Spec memlog and git history.
- **CAP-50 — offline-safe read side** ← spec-enterprise-airgap CAP-2 (shipped 2026-09-09)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** See absorbed Spec memlog and git history.
- **CAP-51 — mirror-friendly data paths** ← spec-enterprise-airgap CAP-3 (shipped 2026-09-09)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** See absorbed Spec memlog and git history.
- **CAP-52 — Vocabulary alignment only** ← spec-intelligence-hub CAP-1 (shipped 2026-09-13)
  - **intent:** the Charter's Lexicon and the station roster map once to the paper's six shared
  - **success:** every row of `vocabulary-map.md` names its Charter term and its gap, and the
- **CAP-53 — Frames as first-class** ← spec-intelligence-hub CAP-2 (shipped 2026-09-13)
  - **intent:** the repo's own context — the `AGENTS.md` verified block, the station personas —
  - **success:** each artifact passes an **IN-REPO four-field preflight** implementing Frame Spec
- **CAP-54 — A declared validation strategy per run** ← spec-intelligence-hub CAP-3 (shipped 2026-09-13)
  - **intent:** a bmad-loop run or `marshal factory spin` declares its Guards by stage, its
  - **success:** one run yields one structured Track record with enumerated fields and a stated
- **CAP-55 — Guards as a library** ← spec-intelligence-hub CAP-4 (shipped 2026-09-13)
  - **intent:** detectors, Warden axes and review lenses exposed as reusable Guards, each with a
  - **success:** a Spec can name which Guard categories it lacks; Warden stays the sole PR
- **CAP-56 — Package the Nebari / Nebi lineage where missing** ← spec-intelligence-hub CAP-5 (shipped 2026-09-13)
  - **intent:** a Mason / `conda-forge-expert` lane builds local recipes for what is actually
  - **success:** a green local build ends the task; nothing is re-packaged that conda-forge
- **CAP-57 — bidirectional propagation of status, assignee, and identity link** ← spec-jira-github-projects-sync CAP-1 (shipped 2026-09-17)
  - **intent:** Moving a GitHub Projects V2 item's status reaches the linked Jira issue, and
  - **success:** a status change made on either board appears on the other without manual
- **CAP-58 — zero-loop guarantee** ← spec-jira-github-projects-sync CAP-2 (shipped 2026-09-17)
  - **intent:** An update one side makes *because of a sync* never triggers a sync back the
  - **success:** a demonstrated (not merely claimed) test in which a synced update provably
- **CAP-59 — idempotent update processing** ← spec-jira-github-projects-sync CAP-3 (shipped 2026-09-17)
  - **intent:** Re-processing the same update payload twice produces the same end state both
  - **success:** delivering an identical payload twice leaves both systems byte-identical to
- **CAP-60 — fail loud, fail alone on broken links** ← spec-jira-github-projects-sync CAP-4 (shipped 2026-09-17)
  - **intent:** An item missing its cross-system link fails loudly in a log — never silently
  - **success:** a batch containing one unlinked item completes for all other items and emits
  - **amended 2026-10-03 (operator ruling, Phase 3, DW-8-5-2):** an item carrying the GitHub-only marker declared in `sync-config.yaml` (a label or single-select field value) is skipped and logged at info, never failed; every other unlinked item still fails loudly. Behind the flag `pyforge.steward.sync_github_only_marker` (OFF in production). Story 84.4.
- **CAP-61 — explicit status-vocabulary translation** ← spec-jira-github-projects-sync CAP-5 (shipped 2026-09-17)
  - **intent:** Status vocabulary differences between the two systems ("Done" vs "Closed") are
  - **success:** every status value crossing the boundary passes through the translation
- **CAP-62 — Cluster bring-up + registry posture (→ Story 12.4)** ← spec-local-ocp-hybrid-environment CAP-1 (shipped 2026-09-17)
  - **intent:** a documented, reproducible bring-up: Podman Desktop OpenShift Local extension (CRC 2.63.0 / OpenShift 4.22.7; 4 cores / 10.5 GB / 35 GB; Linux needs the `crc` binary on PATH) to Running; `oc` authenticated; the **internal-registry push** pattern (`podman login/tag/push` to `default-route-openshift-image-registry.apps-crc.testing` → ImageStream) minted as steward's anticipated OpenShift/registry-posture AD; pull secret, kubeadmin credentials, and the GitHub PAT recorded per the keys discipline (first inventory entries hand-authored).
  - **success:** fresh workstation reproduces it; the platform image pulls in-cluster from the ImageStream.
- **CAP-63 — DB-GPT sidecar joins the chart (→ Story 12.5)** ← spec-local-ocp-hybrid-environment CAP-2 (shipped 2026-09-17)
  - **intent:** the known-owed chart addition — sidecar Deployment (the platform's own image, never `eosphorosai/*` raw), dedicated SQLite PVC at the resolved metadata path, singleton semantics (replicas 1, Recreate), internal-only Service via `DBGPT_SIDECAR_BASE_URL`; 12.1's inventory-test sidecar REJECTION flips to expectation.
  - **success:** renders under restricted-v2; invariant tests updated and green.
- **CAP-64 — Redis hardened, ephemeral kept (→ Story 12.6)** ← spec-local-ocp-hybrid-environment CAP-3 (shipped 2026-09-17)
  - **intent:** emptyDir stays (Celery re-queues); AUTH via `existingSecret` key + NetworkPolicy restricting Redis to platform pods — closing 12.1's named unauthenticated-Redis follow-up.
  - **success:** rendered NetworkPolicy + AUTH-wired `REDIS_URL`; invariant tests cover both. *Superseded for the **broker** role 2026-09-02 by steward Story 40.2 (`spec-pyforge-unifying-strategy` CAP-11): the "Celery re-queues" premise does not cover Streams / PEL / DLQ / applied keys. The cache role stays as 12.6 shipped it.*
- **CAP-65 — Tier-3 attended verification (→ Story 12.7)** ← spec-local-ocp-hybrid-environment CAP-4 (shipped 2026-09-17)
  - **intent:** `helm install` core + overlay on the live cluster proves the four unverified items — Route admission, SCC enforcement, PVC binding, official postgres/redis images under an SCC-assigned arbitrary UID (fallback: RH/bitnami images or the `postgres.dataMountPath` seam) — plus the fresh-install migration-window observation.
  - **success:** a dated verification record in the 12.1 spec's orbit; failures become findings.
- **CAP-66 — dlt Projects V2 bridge (→ Story 12.8)** ← spec-local-ocp-hybrid-environment CAP-5 (shipped 2026-09-17)
  - **intent:** a small custom dlt **GraphQL** source (no verified source covers Projects V2; reuse `steward/sync.py`'s queries) loads the `github_metrics` dataset into cluster Postgres via port-forward; classic PAT with `read:project` (fine-grained PATs cannot reach user-owned projects); 5,000 points/hr + 100-item pages budgeted; the board is created and repo-linked via `gh project link`.
  - **success:** board items queryable in `github_metrics`; kin-declared to `spec-jira-github-projects-sync` Mode B — never a second sync engine.
- **CAP-67 — dual-era atlas face on the host path** ← spec-mcp-era-isolation CAP-1 (shipped 2026-08-27)
  - **intent:** An agent can POST to `/stations/atlas/mcp` on the live host
  - **success:** CRC `/ht/` is 200. POST initialize `protocolVersion`
- **CAP-68 — isolated mcp-host env** ← spec-mcp-era-isolation CAP-2 (shipped 2026-08-27)
  - **intent:** A pixi environment exists that materializes mcp 2.x and the
  - **success:** `pixi install --frozen -e mcp-host` solves. That env's
- **CAP-69 — host proxies; sidecar down is loud** ← spec-mcp-era-isolation CAP-3 (shipped 2026-08-27)
  - **intent:** The host ASGI process keeps the `/stations/<name>/mcp`
  - **success:** With the URL set, dispatch does not import `MCPServer` in
- **CAP-70 — cluster overlay cannot omit mcp-host** ← spec-mcp-era-isolation CAP-4 (shipped 2026-08-27)
  - **intent:** A Helm install / `helm template` of the platform chart (vanilla
  - **success:** `helm template` fails if `mcpHost.image.repository` is empty.
- **CAP-71 — stdio wrap of a FastMCP 3 child** ← spec-mcp-factory-stdio-translator CAP-1 (shipped 2026-08-26)
  - **intent:** A modern client can start a factory tool over stdio and
  - **success:** Child sees `initialize` handshake when the client is
- **CAP-72 — explicit non-CRC claim** ← spec-mcp-factory-stdio-translator CAP-2 (shipped 2026-08-26)
  - **intent:** Operators never treat this process as the host-face pin fix.
  - **success:** Docs and CLI help state it does not change gunicorn
- **CAP-73 — from spec-mcp-host-real-station-tools** ← spec-mcp-host-real-station-tools CAP-1 (shipped 2026-09-12)
  - **intent:** An agent that calls a station's real MCP tool (e.g. marshal's
  - **success:** `POST /stations/marshal/mcp` with `publish_loop_run` on a real deployed
- **CAP-74 — from spec-mcp-host-real-station-tools** ← spec-mcp-host-real-station-tools CAP-2 (shipped 2026-09-12)
  - **intent:** A station with no real in-process MCP app keeps working exactly as
  - **success:** `spec-mcp-era-isolation`'s own CAP-1..3 acceptance criteria (dual-era
- **CAP-75 — from spec-mcp-host-real-station-tools** ← spec-mcp-host-real-station-tools CAP-3 (shipped 2026-09-12)
  - **intent:** CAP-3's own attended-CRC exercise can complete its one unproven item.
  - **success:** `spec-run-state-one-publisher`'s verification record is re-run and its
- **CAP-76 — repo sets + coordinated start** ← spec-multi-repo-workspaces CAP-1 (shipped 2026-09-09)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** one command opens the set; members missing locally are named, not guessed.
- **CAP-77 — set-level status + safe teardown** ← spec-multi-repo-workspaces CAP-2 (shipped 2026-09-09)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** the refusal names the dirty member; --merged-only honors 13.1's archive-not-delete discipline per member.
- **CAP-78 — Optional OCP smoke job** ← spec-ocp-as-a-portability-profile CAP-1 (shipped 2026-09-09)
  - **intent:** Platform CI gains `ocp-portability-smoke`, default **off** (repo variable `PLATFORM_CI_OCP_PORTABILITY_SMOKE=true` or `workflow_dispatch`), reusing `build-platform-image`'s artifact (P1 fan-in), helm/kubectl from `platform-dev` (pap:AD-16), CRC / OpenShift Local as a named system-level exception — never `kind`.
  - **success:** the job exists and is skippable; a dispatch with the variable set reaches cluster-up or fails naming why the cluster never started.
- **CAP-79 — Route and SCC proof** ← spec-ocp-as-a-portability-profile CAP-2 (shipped 2026-09-09)
  - **intent:** the smoke asserts Route admission, edge-terminated HTTPS to `/ht/` and `/admin/login/`, migrate-hook completion, and that postgres/redis pods run without fixed `runAsUser` under SCC-assigned UIDs — never a `port-forward` or a direct Service curl.
  - **success:** a green run records those assertions; a dated note in the 12.1 orbit names any postgres/redis image contingency (official vs RH/bitnami).
- **CAP-80 — Runner honesty** ← spec-ocp-as-a-portability-profile CAP-3 (shipped 2026-09-09)
  - **intent:** the first implementation proves the chosen runner class (GitHub-hosted Ubuntu via `crc-org/crc-github-action`, or a labeled self-hosted RHEL/Fedora runner) before claiming OCP verification.
  - **success:** the job never reports green on a cluster that never started; an unsupported OS is a named skip or a documented self-hosted runner, not a silent pass.
- **CAP-81 — from spec-platform-datastores-consumed-not-self-hosted** ← spec-platform-datastores-consumed-not-self-hosted CAP-1 (shipped 2026-09-11)
  - **intent:** PostgreSQL and Redis are permitted as consumed, never mandatorily self-hosted,
  - **success:** `spec-pyforge-unifying-strategy/SPEC.md` carries the dated 2026-09-11 exception
- **CAP-82 — from spec-platform-datastores-consumed-not-self-hosted** ← spec-platform-datastores-consumed-not-self-hosted CAP-2 (shipped 2026-09-11)
  - **intent:** Mirrors the existing OCP overlay's own additive shape
  - **success:** with the overlay applied, `postgres-statefulset.yaml`/`postgres-service.yaml`/
- **CAP-83 — from spec-platform-datastores-consumed-not-self-hosted** ← spec-platform-datastores-consumed-not-self-hosted CAP-3 (shipped 2026-09-11)
  - **intent:** Same pattern as CAP-2 applied to Redis — a `.Values.redis.external.enabled`
  - **success:** with the overlay applied, `redis-deployment.yaml`/`redis-service.yaml`/
- **CAP-84 — from spec-platform-datastores-consumed-not-self-hosted** ← spec-platform-datastores-consumed-not-self-hosted CAP-4 (shipped 2026-09-11)
  - **intent:** `postgres-backup-cronjob.yaml` must not run a shadow backup of an instance
  - **success:** when CAP-2's overlay is active, the backup CronJob is not deployed, and
- **CAP-85 — Local leaf on platform-dev** ← spec-platform-dev-boots-local CAP-1 (shipped 2026-09-13)
  - **intent:** The operator can load `config.settings.local` and run
  - **success:** `django-debug-toolbar` is declared on
- **CAP-86 — OIDC-delegated identity** ← spec-platform-fifteen-factors CAP-1 (shipped 2026-09-09)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** login flows through the IdP end-to-end locally; createsuperuser retired from the docs path. *Production profile decided 2026-09-09:* **Keycloak in-cluster, deployed by the Foundry chart**, is the default; the `COMPONENT_OIDC_*` seam is the BYO-IdP escape hatch. Landed as **Story 48.9**, co-decided with Story 49.6 (which populates `IDP_CLAIMS_SNAPSHOT` / `IDP_USERINFO`, both `None` today at `base.py:214-215`).
- **CAP-87 — telemetry** ← spec-platform-fifteen-factors CAP-2 (shipped 2026-09-09)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** one request traces web→Celery with correlated ids.
- **CAP-88 — startup refusals** ← spec-platform-fifteen-factors CAP-3 (shipped 2026-09-09)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** each required setting's absence names itself at boot.
- **CAP-89 — policy-as-tests** ← spec-platform-fifteen-factors CAP-4 (shipped 2026-09-09)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** the suite reds on policy drift.
- **CAP-90 — pixi-sourced deps** ← spec-platform-fifteen-factors CAP-5 (shipped 2026-09-09)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** CI + images build from pixi alone.
- **CAP-91 — one frozen env** ← spec-platform-image-one-pixi-env CAP-1 (shipped 2026-08-25)
  - **intent:** The platform image is produced from a single `pixi install --frozen -e
  - **success:** After `pixi lock`, a planted overlap (e.g. pip `mcp` vs conda `mcp`) is a
- **CAP-92 — Containerfile drops the pip installer** ← spec-platform-image-one-pixi-env CAP-2 (shipped 2026-08-25)
  - **intent:** The runtime image no longer runs `python3 -m pip install --no-deps` for
  - **success:** `rg 'pip install --no-deps' src/platform/Containerfile` is empty; the
- **CAP-93 — pixitainer-docker re-eval** ← spec-platform-image-one-pixi-env CAP-3 (shipped 2026-08-25)
  - **intent:** Re-test the **Docker/Podman** pixitainer backend against the Story 10.3
  - **success:** A dated Design Note lists each table row pass/fail with the CLI/package
- **CAP-94 — from spec-platform-object-storage-kind** ← spec-platform-object-storage-kind CAP-1 (shipped 2026-09-10)
  - **intent:** Object storage is permitted as a backing service when consumed via an S3 client
  - **success:** `spec-pyforge-unifying-strategy/SPEC.md` carries the dated 2026-09-10 exception
- **CAP-95 — from spec-platform-object-storage-kind** ← spec-platform-object-storage-kind CAP-2 (shipped 2026-09-10)
  - **intent:** `pgsty/silo` (a maintained MinIO-codebase fork with real Linux/macOS/Windows
  - **success:** `recipes/silo/recipe.yaml` passes `validate_recipe` + `optimize_recipe` +
- **CAP-96 — from spec-platform-object-storage-kind** ← spec-platform-object-storage-kind CAP-3 (shipped 2026-09-10)
  - **intent:** A real local S3-compatible server (never a mock, matching the `scripts/scribe_pg.py`
  - **success:** A new, separate `platform-object-storage` pixi feature (not folded into
- **CAP-97 — from spec-platform-object-storage-kind** ← spec-platform-object-storage-kind CAP-4 (shipped 2026-09-10)
  - **intent:** A minimal `src/platform/` module resolves an S3 endpoint + credentials from
  - **success:** The round-trip test passes against the local backend; no existing feature (Lane
- **CAP-98 — The host renders from the accelerator shape** ← spec-python-agent-platform CAP-1 (shipped 2026-09-12)
  - **intent:** A cookiecutter-django service with FastAPI integration is the platform's one
  - **success:** The rendered host boots against PostgreSQL + Redis with no other
- **CAP-99 — Langflow joins as a pluggable Django application** ← spec-python-agent-platform CAP-2 (shipped 2026-09-12)
  - **intent:** Pattern A of langflow-django-plugin: ASGI mount forwarding `/api/v1/`,
  - **success:** Langflow flows execute through the mounted app with its tables confined to
- **CAP-100 — DB-GPT joins the platform through its configured integration pattern** ← spec-python-agent-platform CAP-3 (shipped 2026-09-12)
  - **intent:** DB-GPT integrates via whichever pattern pap:AD-17's per-engine config switch
  - **success:** Text-to-SQL / data-chat round-trips succeed end-to-end through whichever
- **CAP-101 — Async work never blocks Django** ← spec-python-agent-platform CAP-4 (shipped 2026-09-12)
  - **intent:** Celery over Redis carries LLM/AWEL work (the plugin dreams' Pattern B/D
  - **success:** A long-running agent task completes via the worker path while the host stays
- **CAP-102 — One environment, factory-sourced, 3.14-bound** ← spec-python-agent-platform CAP-5 (shipped 2026-09-12)
  - **intent:** The platform's environment is a single conda-space solve from mirrored
  - **success:** The lockfile solves reproducibly from a mirror-only channel config; the 3.14
- **CAP-103 — Air-gap parity is a test, not a hope** ← spec-python-agent-platform CAP-6 (shipped 2026-09-12)
  - **intent:** Every deployment artifact resolves inside the boundary: internal-registry
  - **success:** A build + deploy executed with external egress blocked succeeds end-to-end;
- **CAP-104 — from spec-scratch-worktree-lifecycle** ← spec-scratch-worktree-lifecycle CAP-1 (shipped 2026-09-09)
  - **intent:** `steward workspace start <slug> [--from <branch>]` creates a worktree at a
  - **success:** One command yields a ready worktree; its path is printed (and in `--json`,
- **CAP-105 — from spec-scratch-worktree-lifecycle** ← spec-scratch-worktree-lifecycle CAP-2 (shipped 2026-09-09)
  - **intent:** `steward workspace ls` enumerates every currently-open scratch worktree this tool
  - **success:** `ls` returns instantly regardless of worktree count and reports only
- **CAP-106 — from spec-scratch-worktree-lifecycle** ← spec-scratch-worktree-lifecycle CAP-3 (shipped 2026-09-09)
  - **intent:** `steward workspace status [<slug>]` reports, per worktree, what `ls` deliberately
  - **success:** For each (or the named) tool-created worktree, `status` reports the three health
- **CAP-107 — from spec-scratch-worktree-lifecycle** ← spec-scratch-worktree-lifecycle CAP-4 (shipped 2026-09-09)
  - **intent:** `steward workspace clean [--merged-only]` removes scratch worktrees whose branch
  - **success:** After `clean --merged-only`, no merged tool-created worktree remains open;
- **CAP-108 — from spec-scratch-worktree-lifecycle** ← spec-scratch-worktree-lifecycle CAP-5 (shipped 2026-09-09)
  - **intent:** The tool keeps a bookkeeping record of which worktrees *it* created, and
  - **success:** With loop-home worktrees present on disk, `ls` and `clean` enumerate zero of
- **CAP-109 — identity and role arrive from the request; the pattern authenticates no one** ← spec-secure-live-dashboards CAP-1 (shipped 2026-09-09)
  - **intent:** An adopting dashboard obtains the caller's identity and group membership from
  - **success:** the same dashboard runs unmodified behind two proxies that use different
- **CAP-110 — row-level isolation is declared, not implemented, by the adopter** ← spec-secure-live-dashboards CAP-2 (shipped 2026-09-09)
  - **intent:** A dashboard states which column carries access and which roles exist; the
  - **success:** two concurrent users of different roles produce **one** upstream fetch and
- **CAP-111 — an unauthorized page is absent, not hidden** ← spec-secure-live-dashboards CAP-3 (shipped 2026-09-09)
  - **intent:** The navigation tree is constructed from the caller's role, so a page a user
  - **success:** the served DOM for a low-privilege caller contains no reference to a
- **CAP-112 — the audit trail records what was seen, not merely that something happened** ← spec-secure-live-dashboards CAP-4 (shipped 2026-09-09)
  - **intent:** Every data load, filter, navigation and export lands in a durable trail
  - **success:** for any completed session the trail can answer "who saw how many rows of
- **CAP-113 — export is gated server-side, and may be encrypted** ← spec-secure-live-dashboards CAP-5 (shipped 2026-09-09)
  - **intent:** Only authorized roles obtain a data export. Authorization is enforced where
  - **success:** a direct request to the export endpoint by an unauthorized caller — with no
- **CAP-114 — the deployment perimeter ships with the pattern** ← spec-secure-live-dashboards CAP-6 (shipped 2026-09-09)
  - **intent:** An adopter receives a production-shaped runtime rather than assembling one:
  - **success:** the same artifact runs on a laptop against a file-backed database and in
- **CAP-115 — the security boundaries are proven by tests that cannot pass vacuously** ← spec-secure-live-dashboards CAP-7 (shipped 2026-09-09)
  - **intent:** Isolation is asserted by a suite that impersonates different identities and
  - **success:** each isolation test fails when its guard is removed, demonstrated rather
- **CAP-116 — the same dashboard definition ships hosted or static, without a fork** ← spec-secure-live-dashboards CAP-8 (shipped 2026-09-09)
  - **intent:** A board that needs no isolation can be published as a free static site on
  - **success:** the same board is published both ways without anyone hand-re-deriving its
- **CAP-117 — estate catalog and config** ← spec-self-hosted-bmad-marketplace CAP-1 (shipped 2026-09-15)
  - **intent:** listings are edited in git we control; backends and sources
  - **success:** `bmad-method install` / `--custom-content` and Claude/Codex
- **CAP-118 — publish path plus steward trust review** ← spec-self-hosted-bmad-marketplace CAP-2 (shipped 2026-09-15)
  - **intent:** a module enters the catalog through Builder / module-template
  - **success:** a listing cannot appear without a recorded review, unless it
- **CAP-119 — ship backends** ← spec-self-hosted-bmad-marketplace CAP-3 (shipped 2026-09-15)
  - **intent:** an air-gapped or estate-local machine gets a snapshot without
  - **success:** default ship path is a noarch pixi/conda index package on
- **CAP-120 — thin browse list** ← spec-self-hosted-bmad-marketplace CAP-4 (shipped 2026-09-15)
  - **intent:** an operator can read the catalog without opening YAML by
  - **success:** a generated index and/or a page in existing chrome lists
- **CAP-121 — Claude-skill source slot (SKU B)** ← spec-self-hosted-bmad-marketplace CAP-5 (shipped 2026-09-15)
  - **intent:** a future `skillsctl` feed can plug in without reminting the
  - **success:** the slot exists in config; v1 does not operate skillsctl or
- **CAP-122 — Hub Layer 3 (SKU C)** ← spec-self-hosted-bmad-marketplace CAP-6 (shipped 2026-09-15)
  - **intent:** buying/selling Frames, Cogs, Ops, Guards across Hubs, and
  - **success:** this Spec does not implement them.
- **CAP-123 — estate Frame index** ← spec-self-hosted-bmad-marketplace CAP-7 (shipped 2026-09-15)
  - **intent:** list, share, and add-as-a-reviewed-listing the Frames that
  - **success:** `docs/foundry/frames/` is a source; a new Frame listing is a
- **CAP-124 — from spec-suite-scaffold-and-mybmad-sidecar** ← spec-suite-scaffold-and-mybmad-sidecar CAP-1 (shipped 2026-09-13)
  - **intent:** `bmad-module-template` is an authoring tool beside
  - **success:** Register row 11 is `wield (authoring tool only)`.
- **CAP-125 — from spec-suite-scaffold-and-mybmad-sidecar** ← spec-suite-scaffold-and-mybmad-sidecar CAP-2 (shipped 2026-09-13)
  - **intent:** mybmad uses the estate PostgreSQL and estate Keycloak/OIDC.
  - **success:** Prisma applies only in schema `mybmad`. Login is
- **CAP-126 — from spec-suite-scaffold-and-mybmad-sidecar** ← spec-suite-scaffold-and-mybmad-sidecar CAP-3 (shipped 2026-09-13)
  - **intent:** The host can show mybmad after the same OIDC session.
  - **success:** django-pyforge chrome lists or embeds mybmad as a
- **CAP-127 — one build, whole Guild** ← spec-unified-container CAP-1 (shipped 2026-09-11)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** See absorbed Spec memlog and git history.
- **CAP-128 — the image ships the repo at a fixed short path** ← spec-unified-container CAP-2 (shipped 2026-09-11)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** See absorbed Spec memlog and git history.
- **CAP-129 — credentials never enter image layers** ← spec-unified-container CAP-3 (shipped 2026-09-11)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** See absorbed Spec memlog and git history.
- **CAP-130 — state outlives the container** ← spec-unified-container CAP-4 (shipped 2026-09-11)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** See absorbed Spec memlog and git history.
- **CAP-131 — the image proves itself at build time** ← spec-unified-container CAP-5 (shipped 2026-09-11)
  - **intent:** See absorbed Spec memlog and git history.
  - **success:** See absorbed Spec memlog and git history.
- **CAP-132 — the Spec ladder is declared** ← spec-vocabulary-one-name-one-job CAP-1 (shipped 2026-09-15)
  - **intent:** the eight live Spec statuses get a stated naming rule, a
  - **success:** `draft`, `ready`, `in-progress` (grandfathered only), `shipped`,
- **CAP-133 — the BMAD↔Lexicon cross-walk** ← spec-vocabulary-one-name-one-job CAP-3 (shipped 2026-09-15)
  - **intent:** BMAD's daily nouns (Epic, Story, Sprint, PRD, Retrospective) map
  - **success:** the Charter carries the walk (map, never join) and records
- **CAP-134 — the unnamed collisions get rulings** ← spec-vocabulary-one-name-one-job CAP-4 (shipped 2026-09-15)
  - **intent:** `Track` and `Gate`/`Guard` are named and scoped.
  - **success:** artifacts write **evidence Track** vs **planning track**; Gate
- **CAP-135 — the Design tier stops drifting** ← spec-vocabulary-one-name-one-job CAP-5 (shipped 2026-09-15)
  - **intent:** practice vocabulary is teaching-only (except method-vs-machinery
  - **success:** the deck says it is teaching-only; Herald owns the pull;
- **CAP-136 — mint-time story identity and new `DW-` ids** ← spec-vocabulary-one-name-one-job CAP-6 (shipped 2026-09-15)
  - **intent:** one function, at mint time, makes the three story spellings
  - **success:** heading `### Story N.N:` is human-canonical; the ledger key is
- **CAP-137 — remaining declared shapes** ← spec-vocabulary-one-name-one-job CAP-7 (shipped 2026-09-15)
  - **intent:** long vs short station form, frontmatter casing, `S-N.N`, commit
  - **success:** one roster of eight stations (LONG for paths/packages/envs,
- **CAP-138 — `check=` is a finding code** ← spec-vocabulary-one-name-one-job CAP-8 (shipped 2026-09-15)
  - **intent:** the field that carries `spec-surface` does not also carry a
  - **success:** the six `atlas.py` call sites put runtime data in `evidence`;
- **CAP-139 — extract corridor and transports** ← spec-work-passports-dated-extracts CAP-1 (shipped 2026-09-15)
  - **intent:** inbound vendor extract and outbound filtered extract load
  - **success:** re-dropping last week's file does not clone passports; an
- **CAP-140 — work passport and frozen core schema** ← spec-work-passports-dated-extracts CAP-2 (shipped 2026-09-15)
  - **intent:** UUID is identity; Jira keys and GitHub numbers are nicknames;
  - **success:** two extracts cannot merge by title; high-value first links
  - *2026-09-19:* Story 65.1 (PR #1507) shipped a `WorkPassport` Django model (minted UUID `passport_id`; `jira_key` / `github_item_id` as aliases), its admin and a flag-gated Postgres sync — a partial realization outside Story 61.2's declared surface (no `vendor_id`, not the existing join store, 61.1's corridor not landed). 61.2 remains the story of record and builds on it.
- **CAP-141 — as-of glass (standup and shipped)** ← spec-work-passports-dated-extracts CAP-3 (shipped 2026-09-15)
  - **intent:** vendor data on the existing Postgres app is dated; empty
  - **success:** testers see shipped-from-last-inbound; standup cites a
- **CAP-142 — outbound slice gate** ← spec-work-passports-dated-extracts CAP-4 (shipped 2026-09-15)
  - **intent:** default deny, named slice, named outbound-signer role
  - **success:** an unsigned or over-cap file does not leave; they load what
- **CAP-143 — quarantine (no auto-link)** ← spec-work-passports-dated-extracts CAP-5 (shipped 2026-09-15)
  - **intent:** unlinked inbound rows wait for a human. First 14 days
  - **success:** no title-match endpoint exists. After the window, a row
- **CAP-144 — live collectors for boards we already own** ← spec-work-passports-dated-extracts CAP-6 (shipped 2026-09-15)
  - **intent:** Jira and Internal GH we can log into feed stamps; never the
  - **success:** the slot exists; v1 does not run collectors. Epic 8 /
- **CAP-145 — BMAD projection onto Internal GH** ← spec-work-passports-dated-extracts CAP-7 (shipped 2026-09-15)
  - **intent:** ledger remains source; GH cards say projected.
  - **success:** the slot exists; factory stories do not ride outbound
- **CAP-146 — one query engine over every station's tracked ledger** ← spec-sprint-ledger-query-module CAP-1 (folded 2026-09-19; shipped 2026-09-19, Story 65.1)
  - **intent:** An operator, agent or dashboard filters and inspects story/epic telemetry across all eight stations through one engine (`pyforge.steward.sprint_ledger_query.SprintLedgerQueryEngine`) reading each station's TRACKED `sprint-status-ledger.yaml` and `epics.md` — never the Tier-3 feed, never `docs/dashboard/data.js` — with presets and station / epic / status / text filters.
  - **success:** Per-station done / backlog / blocked counts equal `fleet-picture`'s for the same tree (agreement test against `scripts/fleet_scan.py::parse_sprint_status`); every preset and filter has a fixture test; every ledger status the fleet uses lands in a bucket.
- **CAP-147 — pluggable, hookable, feature-flagged** ← spec-sprint-ledger-query-module CAP-2 (folded 2026-09-19; shipped 2026-09-19, Story 65.1)
  - **intent:** Formatters, sources and lifecycle hooks are registered, not hard-coded, and every optional integration sits behind a flag resolved from `flags.json` / environment / CLI override (no SDK dependency in v1), so the core query path has no runtime dependency on any exporter's target.
  - **success:** A flag left off refuses the gated export (`ok=false`), never silently runs it; a registered plugin or hook is exercised by test without editing the engine; the module's only third-party import is `yaml`.
- **CAP-148 — every consumer gets its own shape from one engine** ← spec-sprint-ledger-query-module CAP-4 (folded 2026-09-19; shipped 2026-09-19, Story 65.1)
  - **intent:** One query result renders as `markdown` / `summary` / `table`, schema-validated `json` (the schema ships with the package), Herald's facts-ledger shape, an `atlas-dataset` payload (steward exports, Atlas renders — canopy:AD-13 / canopy:AD-23), `jira-csv`, `github-json`, and `get_runnable_backlog()` for Marshal — with strict stdout/stderr separation and no default write into another station's tree.
  - **success:** Each formatter round-trips a fixture; the `json` payload validates against the shipped schema; `get_runnable_backlog()` agrees with marshal's Deps grammar (`S-x.y`, `none`, `station:S-x.y`, keyed per station); diagnostics never reach stdout.
- **CAP-149 — three front doors, one engine** ← spec-sprint-ledger-query-module CAP-5 (folded 2026-09-19; shipped 2026-09-19, Story 65.1)
  - **intent:** `steward ledger-query` (a counted duty), the pixi tasks `sprint-ledger-query` (`pyforge-guild`) / `sprint-ledger-postgres-sync` (`pyforge-steward` — the one env carrying django; a task registered where it cannot succeed is a trap, not a front door), and the `bmad-sprint-ledger-query` skill wrap the engine rather than re-implement it; the HTMX backlog view reads through it.
  - **success:** The duty-count invariants include it; `--format` choices come from the formatter registry; the skill's documented invocations run verbatim.
- **CAP-150 — the ledger query answers done / running / next in one call** ← spec-pyforge-steward CAP-150 (ready 2026-09-20)
  - **intent:** every story the engine returns carries a `next` field — `done`, `running` (a live dispatch or loop run is on it), `ready` (backlog with every declared dependency done — `get_runnable_backlog()`'s predicate), `waits on S-x.y[, …]` (naming the unmet deps), `blocked`, or `?` (running fact unavailable); `--ready` / `--running` filter to those values; the summary carries per-station ready and running counts; table/markdown/json carry the column. The running fact is read from marshal's own CLI (`marshal watch --fleet --format json` through the `pyforge.core` process primitive, one call per query) — steward never parses marshal's journal and never imports `pyforge.marshal`; when marshal is absent or the call fails, `running` reads `?` with one WARN (fail-open, CAP-15's posture); the fact is the current checkout's (marshal's Tier-3 is per clone — documented in `--help`).
  - **success:** `sprint-ledger-query -- --unimplemented --format table` reproduces the 2026-09-20 08:00Z hand-composed view from a fixture of those ledgers, epics and a recorded watch payload; `--ready` equals `get_runnable_backlog()` exactly; `--running` equals the watch payload's running rows; unreachable marshal → `?` + WARN, exit unchanged; the `bmad-sprint-ledger-query` skill documents the column and the two filters; `pyforge-steward-test` green; duty-count invariants unchanged (flags on the existing duty, no new one).
- **CAP-151 — `pyforge-foundry-full`: the fleet's whole dependency closure is one locked artifact** ← spec-pyforge-steward CAP-151 (shipped 2026-09-20, Story 63.5)
  - **intent:** `pixi.toml` declares `pyforge-foundry-full` = the union of every PyForge feature (python, pyforge-guild, guild-tasks, pyforge-core, pyforge-testing-kit, the eight stations), `no-default-feature` — never the runtime (that is `pyforge-guild`), never the recipe factory (`local-recipes`), never installed by default; it exists so every station-only extra resolves together or the lock refuses, and a station's own env carries what its code wields (`bmad-eval-quality` in `pyforge-steward`). **Amended 2026-09-25 (operator):** it is also the default laptop install (`spec-python-foundry-cutover` fnd:CAP-12, Story 67.1) — the "never installed by default" clause retires; `pyforge-guild` stays the session and runtime default (CAP-5 unchanged).
  - **success:** `pixi lock` solves `pyforge-foundry-full` on linux-64, osx-arm64-min and win-64 and the lock carries it; `llms-full-check` clean; `pyforge-station-tests` green on the lock; the first solve's findings (mason's `python-build` window, warden's `py-rattler` floor) fixed at their owners with the reason recorded; `DW-OPS-2026-09-20-1` resolved.
- **CAP-152 — no station code assumes the `local-recipes` environment at runtime** ← spec-pyforge-steward CAP-152 (ready 2026-09-20)
  - **intent:** only `pyforge-guild` exists at runtime; every task a station shells to (`bmad-loop list|status`, `deck-export`, `deck-facts`, `deck-trio`, `platform-ci-local`, `wasm-build`, the bmad-builder / TEA share dirs steward provisions from) is reachable from `pyforge-guild` — registered in `guild-tasks` with its deps in the `pyforge-guild` feature — and a meta-test in the steward suite reds any `-e local-recipes` shell-out or `.pixi/envs/local-recipes` path in any station's `src/`.
  - **success:** the meta-test lists zero offenders once marshal 46.12 and herald 25.1 land (steward's own `provision.py` / `upgrade.py` / `suite.py` fixed in this story); `pixi run -e pyforge-guild <task>` works for every shelled task; `pyforge-guild`'s size delta reported against the Dream's minimal-default intent; `pyforge-station-tests` green.
- **CAP-153 — lint and types gate the ten `pyforge-*` packages, locally and on the runners alike** ← spec-pyforge-steward CAP-153 (ready 2026-09-20)
  - **intent:** every `src/shared/packages/pyforge-*/pyproject.toml` carries `[tool.ruff]` and `[tool.mypy]` on py314 targets (mypy strict for `pyforge-core`); repo-level `ruff`, `ruff-format` and `mypy` tasks in `[feature.guild-tasks.tasks]` run them over all ten packages from `pyforge-guild`; a target-version registry check (like `pixi-version-check`) reds a package whose target drifts from the interpreter; one CI lane runs exactly those tasks and `pr-preflight` gains the same leg, so local and runner cannot diverge.
  - **success:** `pixi run -e pyforge-guild ruff` / `ruff-format` / `mypy` exit 0 on `main`; the CI lane and the `pr-preflight` leg invoke the same tasks; a deliberately planted violation in any package reds both; `src/platform`'s own `platform-ci` lane unchanged.
- **CAP-154 — the pre-commit set: attribution lines and un-preflighted pushes are refused by hooks, not prose** ← spec-pyforge-steward CAP-154 (ready 2026-09-20)
  - **intent:** `.pre-commit-config.yaml` at the repo root with a `commit-msg` hook that refuses `Co-Authored-By:` and AI-attribution trailers, and a `pre-push` hook that runs `pixi run -e pyforge-guild pr-preflight` (opt-out only by an explicit env var, journaled; `dispatch/*` branches are supervisor-gated and skip it, journaled); `steward setup` / `initrepo` install it through the existing hooks step (`bootstrap._run_pre_commit_install`, waiting on this file since Story 17.2); a CI check reds a missing file or a missing hook.
  - **success:** a commit carrying `Co-Authored-By:` is refused locally with the rule named; a push from a branch whose `pr-preflight` is red is refused; the two `TODO:` lines in `AGENTS.md`'s managed block retire under bmad-project-context ground 2 in the same landing.
- **CAP-155 — `workspace clean` archives the work, never the environments, and one undecidable record never stops the sweep** ← spec-pyforge-steward CAP-155 (ready 2026-09-27; amended 2026-09-27, Story 68.1 review 1)
  - **intent:** `_archive_worktree` leaves reinstallable pixi dirs (`.pixi/envs`, `.pixi/solve-group-envs`, `.pixi/bld`) out of the tar while every other file — the tracked `.pixi/config.toml` included — archives as before; a tar that fails removes its partial archive and raises `WorkspaceError`. In `clean_workspaces` a record whose merge check or archive raises is reported as skipped with the reason and kept in bookkeeping, the sweep continues, and a record in flight when any other exception escapes (a Ctrl-C at the confirm prompt) is still saved back; a sweep that reported an error row exits non-zero. (Found 2026-09-27: `.steward/workspace-archive/` held 75 GB in 62 archives; a fleet `clean --merged-only` raised on a record whose branch was gone, examined nothing after it, and its `finally`-save dropped the failing record.)
  - **success:** a worktree carrying populated `.pixi/envs`, `.pixi/solve-group-envs` and `.pixi/bld` archives without them and still carries `.pixi/config.toml`; a fleet `clean --merged-only` over [a record with a missing branch, a merged record] archives the merged one, reports the other skipped with its git error, keeps it in bookkeeping and exits non-zero; an unreadable file leaves no partial archive and keeps the record; an interrupt mid-sweep loses no record; `pyforge-steward-test` green.
- **CAP-156 — the pre-push gate's journal names what was pushed** ← spec-pyforge-steward CAP-156 (ready 2026-09-27; amended 2026-09-27, Story 68.2 review 1; amended 2026-10-04, CAP-165)
  - **intent:** every `.steward/preflight-skips.log` line `scripts/pre_push_preflight.sh` writes — branch delete, `dispatch/*`, the manual `PYFORGE_PREFLIGHT_SKIP=1` — records the pushed remote ref(s) and local sha(s), falling back to the checked-out branch and HEAD only when the hook received no ref information; the delete skip is journaled too. The hook adds no skip of its own: under pre-commit it receives only the FIRST ref of a multi-ref push, so it cannot prove a push carries nothing new — a tool that can prove it sets the journaled opt-out with that proof as its reason (`marshal refresh`, spec-pyforge-marshal CAP-267). (Found 2026-09-27: the manual opt-out journaled `main` for eight `loop/*` pushes; a hook-side nothing-new skip was tried and refused in review — it let a multi-ref push carry a new commit unchecked.) *(Amended 2026-10-04, CAP-165:)* the hook gains one skip of its own, for a push it can prove is tag-only: every pushed ref a tag under `refs/tags/preserve/` or `refs/tags/archive/`, read from stdin in the bare-git form. In the pre-commit form, which sees only the first ref, it skips only on a proof the pushing tool supplies (`pyforge.core.preserve_refs` pushes one refspec per tag and supplies it), never on the first ref alone. The skip is journaled like every other; a mixed push runs the preflight.
  - **success:** the manual opt-out's line names the pushed ref and sha, not the checked-out branch; the `dispatch/*` and delete lines name theirs; a push already on `origin/main` still runs the preflight in both the pre-commit (env) and bare-git (stdin) forms; CAP-154's refusal of a red push is unchanged; `tests/scripts/test_lint_types_gate.py` green. *(2026-10-04:)* a stdin push of only `refs/tags/preserve/…` and `refs/tags/archive/…` tags skips with a journal line naming them; the same push with a branch ref added runs the preflight; a pre-commit-form push whose first ref is such a tag runs the preflight unless the tool's proof is present.
- **CAP-157 — `workspace clean` keeps a note, not a tarball, for a worktree already on its source** ← spec-pyforge-steward CAP-157 (ready 2026-09-27; amended 2026-09-27, Story 69.1 reviews 1 and 2; shadow clause superseded 2026-09-27 by CAP-158, Story 70.1; amended 2026-10-04, CAP-165; amended 2026-10-23, Story 13.6)
  - **intent:** before archiving, `_archive_worktree` asks git for a proof that the worktree holds nothing unlanded, and all of it must hold: `git status --porcelain` empty with untracked files shown and submodules not ignored, whatever the config says; no index entry marked skip-worktree or assume-unchanged; HEAD and the recorded branch (when it exists) both ancestors of the record's `source`, which must resolve to a remote-tracking ref (`--symbolic-full-name`, locale- and config-independent; *2026-10-23, Story 13.6:* the full refname is looked up exactly with `show-ref --verify`, for any configured remote, never through git's name lookup); no gitlink and no per-worktree ref (`refs/worktree/`, `refs/bisect/`); and a git-ignored listing, read NUL-separated as bytes, that succeeds and holds no real file or directory under `_bmad-output/` (a backlink symlink is fine). Output git prints that cannot be decoded is no proof, never a crash of the sweep. A proven worktree leaves a `<slug>-<stamp>.landed.txt` note — slug, branch, path, the HEAD sha, the source and its sha, the git-ignored paths not kept (up to 200, the rest counted), and the worktree's pre-push skip journal copied — instead of a tarball; anything unproven archives exactly as CAP-155 does. In every clean, the recorded branch is deleted only when it is on the source: an unmerged branch's commits exist nowhere else, since a tarball holds files, never history — the kept branch is reported in the clean output. *(Amended 2026-10-04, CAP-165:)* before an unlanded worktree is removed, its commits are parked as an annotated `preserve/<slug>/<N.M>/workspace-<sha8>` (or `preserve/unbound/workspace-<sha8>`) tag through `pyforge.core.preserve_refs`, so a kept branch is no longer their only reachability; a local tag is enough to remove the worktree, and its push goes through the content gate or is reported as debt. The tarball keeps only git-ignored bytes; untracked files go into the snapshot, which the gate scans before any push. (Found 2026-09-27: after Story 68.1 the 25 archives left, 3.1 GB, held nothing `main` lacked. Review 1 found each gap in the first proof by probe — a config hiding untracked files, skip-worktree and assume-unchanged edits, a detached HEAD over an unlanded branch commit, a shadowing `origin/main`, a submodule `ignore=all`, a failed listing, ignored Tier-3 drafts.) *(Amended 2026-10-23, Story 13.6:)* a workspace's landing refs are its recorded source and, when that is not the trunk, `origin/main` read as `refs/remotes/origin/main` (CAP-158): the proof holds when HEAD and the branch are ancestors of a landing ref that resolves under `refs/remotes/` (the first that holds both), and the note names that ref and its sha, and the recorded source when they differ. An `origin/<b>` source and the trunk are compared by the commit their remote-tracking ref names, never by name, so a local ref named like either proves nothing; `clean --merged-only` and the preserve-tag check also require the worktree's HEAD to be landed, so commits on a detached HEAD past a landed branch are kept or parked. `status`'s merged flag, `clean --merged-only`, `clean --delete` and every branch removal read the same refs, so a workspace started `--from` another branch is landed once its branch is on `main`; a trunk git cannot resolve proves nothing and never turns the source's answer into an error. `ahead`/`behind` still read the recorded source. (Found 2026-10-23: Story 71.13's workspace, started `--from` Story 71.12's branch, read `unmerged` after its merge and `clean --delete` skipped it.)
  - **success:** a clean worktree whose HEAD and branch are on its source is cleaned with a `.landed.txt` note and no tarball, the note naming the HEAD sha and a git-ignored file it did not keep; each of these still archives to a tarball: an unlanded commit, an uncommitted edit, an untracked file (also with `status.showUntrackedFiles=no`), a skip-worktree or assume-unchanged edit, a detached HEAD over an unlanded branch commit (the branch is kept), an unlanded commit past a local ref shadowing the source (CAP-158: the proof reads `refs/remotes/<source>`, so a landed worktree past a shadow leaves a note), a source git cannot resolve *(2026-10-23: unless the trunk proves the worktree landed)*, a gitlink, a per-worktree ref, a failed ignored listing, and ignored Tier-3 work that is not a backlink (also under a quoted path); a non-UTF-8 ignored name is named in the note, never a crash; the skip journal is copied into the note; a kept branch is reported; *(2026-10-04:)* with the flag `pyforge.steward.workspace_preserve_tag` on, an unlanded worktree leaves a preserve tag at its HEAD before removal, a tag that cannot be written keeps the worktree, and a tag the push cannot deliver is reported as debt; *(2026-10-23:)* a workspace started `--from` a local branch whose branch then lands on `origin/main` reads merged in `status`, leaves a note naming `origin/main` under `clean --merged-only` and is dropped by `clean --delete`, while one on neither its source nor `origin/main` is still refused `not-merged`; `pyforge-steward-test` green.
- **CAP-158 — steward reads `origin/main` and its own branches by their full refs** ← spec-pyforge-steward CAP-158 (ready 2026-09-27)
  - **intent:** every git read of a workspace's recorded source `origin/<b>` — `start`'s `worktree add`,
    `status`'s ahead/behind and merged check, `clean`'s `--merged-only` check, landed proof and
    branch-drop proof — names `refs/remotes/origin/<b>`, and every read of its branch names
    `refs/heads/<branch>`; recorded sources stay as written. The platform's copy of the kit's diff
    guard (`src/platform/tests/test_warden_portal_audit_start_get.py`) and the `tea-test-review` pixi
    task — and marshal's review lens, the task's one documented caller (a repeated `--base` replaces the
    task's) — name `refs/remotes/origin/main`. A short name resolves to a local branch or tag first: past a
    shadow at an unmerged tip, `clean --merged-only` archived the worktree and deleted its branch.
  - **success:** with a local branch or tag `origin/main` (or a tag named like the branch) in place,
    `clean --merged-only` keeps an unmerged workspace and its branch, `status` reports it unmerged,
    and `start` branches from the remote; with none, every result is unchanged; old bookkeeping reads
    correctly; the platform guard imports no `pyforge.*`.
- **CAP-159 — the preflight answers in under a minute** ← spec-pyforge-steward CAP-159 (ready 2026-09-27)
  - **intent:** `pixi run -e pyforge-guild pr-preflight` — and so CAP-154's `pre-push` hook — runs the lanes CI's own rules select for the branch's diff and no others, runs them concurrently, and journals every run's per-lane wall time and exit code. The lane list stays declared once in `pixi.toml` (the `depends-on` aggregate, read, never copied); which lanes a diff selects is read at run time from `.github/workflows/*.yml` (each workflow's `on.pull_request.paths` and its `changes` job), never from a second hand-kept list; the diff base is `refs/remotes/origin/main` (CAP-158), and an unreadable base, a rule the reader cannot evaluate, or a lane with no CI counterpart runs the lane. Concurrent lanes share no mutable state: environments install one at a time before any lane starts (`.pixi/bld`), each lane gets its own temp dir, pytest basetemp and cache dir, and coverage data file, and lanes sharing a CI service container (scribe's Postgres on 5433) never overlap. A station's suite lane skips the tests its coverage gate's own run already covers, so every test runs once and the floor stays the driver's verdict; the station suites that bound a single-station run declare `pytest-xdist` in their own tasks, so CI runs them the same way; the detector registry runs its detectors concurrently. Verdicts stay each lane's exit code, never a pipe; `PYFORGE_PREFLIGHT_SKIP=1` stays the one journaled opt-out; the not-covered list (container, atlas's Chromium/DuckDB/WASM, herald's browser check, scribe's Postgres) does not grow. (Measured 2026-09-27 on a 16-core laptop, marshal-only branch: 28 lanes run one at a time, 622.8 s; 250.4 s of station suites CI would not run for that diff; marshal's unit suite run twice, 49.5 s then 56.2 s under coverage.)
  - **success:** on a single-station branch (a diff inside one `src/shared/packages/pyforge-<station>/` tree, no shared surface) `pr-preflight` returns its verdict in under 60 s of wall clock on the 16-core reference laptop, and a budget check reading the journal (exit 0 / 1 / 2, never part of `pr-preflight`'s verdict) reds such a run over 60 s naming its slowest lanes; for fixture diffs (one station, `pixi.toml`, a CFE path, a `docsite/` path, a Dream-only edit, no `origin/main`) the preflight selects exactly the lanes the workflows' own rules select, plus every lane with no CI counterpart; the tests the gate's run and the reduced suite run collect are disjoint and together equal the station task's own collection; the detector registry reports the same statuses, findings and exit code at `--jobs 1` and `--jobs 8`; a shared-surface run still runs every lane CI's rules select, its journaled wall time bounded by its slowest lane; a red lane still refuses the push; `pyforge-steward-test` green.
- **CAP-160 — Mason's five-tier skill cell is its station skill and `conda-forge-expert`, both** ← spec-pyforge-steward CAP-160 (ready 2026-09-28)
  - **intent:** `five_tier.detect_tiers` counts Mason's `skill` cell present only when `.claude/skills/pyforge-mason/` holds a `SKILL.md` (the SKF station skill — the rule every other station's cell already follows) **and** `.claude/skills/conda-forge-expert/SKILL.md` exists — neither alone. The Mason 11.1 carve-out at `five_tier.py:104-106` (CFE alone, "do not require pyforge-mason/") and the module comment "Mason's skill cell is conda-forge-expert" are replaced by that rule and cite the operator's ruling of 2026-09-28 (`spec-pyforge-mason:CAP-29`). It lands after mason Story 19.1 has compiled the station skill: until then the live roster would read Mason's cell missing, so the story is a ledger gate the operator flips (marshal's `Deps:` parser is station-local).
  - **success:** with both skills present Mason's cell reads present and the live roster stays 40/40; a fixture tree holding only `conda-forge-expert`, and one holding only `pyforge-mason`, each reads Mason's `skill` cell missing and `check` fails naming `skill`; every other station's cell rule is unchanged; `pyforge-steward-test` green.
- **CAP-161 — the Guild environment answers `pyforge mason`** ← spec-pyforge-steward CAP-161 (ready 2026-09-28; extends CAP-5; amended 2026-09-28)
  - **intent:** `pyforge-guild`, the session default every agent and harness runs (CAP-5), installs `pyforge-mason` beside core, doctor, marshal, steward, herald and scribe, so the front door routes `pyforge mason …` and the `mason` script is on `PATH` — the only grammar `bmad-agent-mason` may use. The front door is correct as built: `pyforge.core.dispatch` maps a station token to the primary console script of a `pyforge-*` distribution installed in the running environment (`dispatch.py:94-105`, with a per-station `distribution()` fallback at `:154-166`), and `[feature.pyforge-guild.dependencies]` (`pixi.toml:841-864`) never installed `pyforge-mason`, so `pixi run -e pyforge-guild pyforge mason --help` answered `unknown station 'mason'; known: doctor, herald, marshal, scribe, steward` (measured 2026-09-28). The feature gains one path dependency — the package's own run-dependencies (its engines and `pyforge-core`) come with it — and its banner comment names what the environment carries. Recipe work still runs in `-e local-recipes`; `mason doctor` reports the recipe verbs' availability in this environment as it finds it (mason's degradation contract). `pyforge-warden` stays out (its `osv-scanner` pin, `pixi.toml:844-849`) and `pyforge-atlas` is not added here. *(Amended 2026-09-28, operator rulings:)* the Guild's pixi does not move when Mason joins: no station or environment caps pixi, and `spec-pyforge-mason:CAP-30` (mason Story 20.1) makes Mason's run-dependency `pixi >=0.80.0`, dropping the `<0.81` ceiling that would have taken the Guild's pixi 0.81.0 → 0.80.0 (a Kinship; this story lands after it). Conda-lock, one of Mason's engines, still moves two Guild pins, and both are accepted: its conda-forge build requires `virtualenv >=20.26.6,<21` (21.12.1 → 20.39.0), and virtualenv 20 requires `filelock >=3.24.2,<4` (4.0.3 → 3.x). Evidence, 2026-09-28: the Guild's only virtualenv consumer is `pre-commit` 4.6.2 (`virtualenv >=20.10.0`), whose two hooks here are `repo: local`, `language: script`, so it builds no virtualenv for them; no repository code imports virtualenv; the Guild's other filelock consumer, `huggingface_hub` (`>=3.10.0`), admits 3.x, and `python-discovery`, which only virtualenv 21 requires, may leave; and `pyforge-foundry-full`, the SBOM and default laptop install, already locks `pre-commit` 4.6.2 with virtualenv 20.39.0 and filelock 3.32.6, as `local-recipes` and `pyforge-mason` lock conda-lock with virtualenv 20.39.0. The ceiling is conda-lock's own, upstream; this estate adds none. The size bound is CAP-5's, restated the same day at 2 GB.
  - **success:** `pixi run -e pyforge-guild pyforge mason --help` and `pixi run -e pyforge-guild pyforge mason doctor --format json` exit 0; a steward meta-test reds a `[feature.pyforge-guild.dependencies]` without `pyforge-mason`; a cold `pixi install -e pyforge-guild` with `pyforge-mason` stays under CAP-5's bound as restated 2026-09-28 (2 GB), measured and recorded in the story beside the before-mason size (1.5 GB, 243 packages); the Guild's resolved pixi does not move (the version the rest of the workspace resolves, 0.81.x at the ruling) and `pixi-version-check` exits 0; the Guild's virtualenv reads 20.x and filelock 3.x, recorded in the story, and no other Guild package changes version; `environment.yaml` regenerated in the same change; `pyforge-station-tests` and `detectors-ci` green; `pyforge-steward-test` green.
- **CAP-162 — `steward session check` reads `marshal seed check`'s envelope, whatever its exit code** ← spec-pyforge-steward CAP-162 (ready 2026-09-28; extends CAP-5; amended 2026-10-01, Story 81.1)
  - **intent:** `session.py::_seed_kit_findings` reads the kit from the seed check's schema-stable envelope — `result.kit` under `{verb, ok, result}` (marshal FR-123 / NFR-12, Story 12.5) — whatever the process exit code: exit 1 is the seed check's own verdict on its HARD findings, not a failed read. `token-kit` and `codegraph-index` report the kit entries' statuses by today's per-item rules (Story 63.4), amended 2026-10-01 (Story 81.1): `ok` and `layer-off` are silent, as marshal's kit contract makes them (`seed/detect/kit.py`: `OK` and `OFF` are `KitStatus`'s "two silent outcomes", "the kit is declared-off, not missing"), so a `layer-off` item is named in the `token-kit` detail and fails neither finding; any other status, including one steward does not know, fails both. An `ok: false` envelope makes both findings non-ok with the envelope's `error` type and message as the detail. Stdout that is not JSON keeps "unparseable output"; a JSON document with no `result.kit` list reads "no kit report" naming the top-level keys it found — never "unparseable". The unit fixtures take the envelope shape, one recorded verbatim from the live CLI. Steward still shells marshal's CLI and never imports it. (Found 2026-09-28: every `marshal factory dispatch` warned `MRS-DISP-049` because the check read `payload["kit"]` at the top level and reported the `KeyError` as "unparseable output", quoting the last lines of a valid document; its fixtures used a flat shape the CLI never emitted.)
  - **success:** the recorded document (live CLI, 2026-10-01, Story 73.1's recorded deviation from the 2026-09-28 statuses; exit 1, `result.failing: true`, kit statuses `missing` / `layer-off` / `missing`) yields `token-kit` non-ok naming its two `missing` items and not its `layer-off` item, and `codegraph-index` non-ok naming `missing`; a kit whose only non-`ok` item is `layer-off` yields both findings ok, and no detail says "unparseable"; the same document with every kit item `ok` yields both findings ok whether the process exited 0 or 1; an `ok: false` envelope names the seed error's type and message; `not json` still reads "unparseable output"; `{"verb": "check", "ok": true, "result": {}}` reads "no kit report"; restoring the top-level `payload["kit"]` read fails the recorded-document test (mutation); `pyforge-steward-test` green.
- **CAP-163 — the object-storage seam gets its first consumer: a station streams bytes in and out by sha256 key** ← spec-pyforge-steward CAP-163 (ready 2026-09-28; extends CAP-94..97)
  - **intent:** a streaming, sha256-addressed put/get contract over the platform seam, in the chrome every portal already imports — `django_pyforge.object_store` — so a `django-<station>` package, or the station API it serves under `/stations/<name>/api/v1/`, reaches the store while `src/platform/` imports no `pyforge.*` and the chrome imports nothing from the host's `config` package. `put` spools the caller's stream to a bounded temporary file while hashing it, then uploads it under `<prefix>/sha256/<hex>` — content-addressed, so identical bytes land once and an existing key is not re-uploaded — and returns the key, sha256, size and content type; `get` streams the object back in chunks for a `StreamingHttpResponse`; nothing loads a whole object into memory or a model field. The client is CAP-97's `config.object_storage.object_storage_client()`, named by a setting (`OBJECT_STORAGE_CLIENT_FACTORY`) and resolved with `import_string` — the chrome never builds a second client (AD-1). The bucket and prefix are settings (`OBJECT_STORAGE_BUCKET`, `OBJECT_STORAGE_PREFIX`) that the Helm chart names per environment, beside the three existing secret references (canopy:AD-19); with `networkPolicy` enabled, the web and worker workloads gain an egress allow to the consumed endpoint and nothing else. No presigned URLs in v1: the portal streams every byte behind OIDC and the station role, so the store needs no browser-reachable endpoint. The store is consumed and never self-hosted in production (CAP-94's dated 2026-09-10 exception; the chart renders no object-store workload); local development keeps CAP-96's `platform-object-storage` feature and its `silo` server. Metadata stays out of the seam: a consumer's rows (Herald's topic, kind, date, size, content type, source commit) live in its own table in `public` under a namespaced Liquibase changeset (canopy:AD-9), on the consumer's chain. PostgreSQL stays at 17 (fnd:CAP-12); no new process. Ships behind the flag `pyforge.steward.object_store_consumer` (`spec-feature-flag-governance` CAP-1), default off until the tree carries per-environment values: OFF, `put` and `get` refuse with a named `ObjectStoreDisabled` and a consumer keeps its git-only behaviour. (Operator rulings 2026-09-28: Herald's exports are the first consumer; bytes never go in PostgreSQL.)
  - **success:** against a real `silo` (CAP-97's ephemeral-instance pattern), a `put` of a stream larger than the spool threshold returns the sha256 the test computed, lands at `<prefix>/sha256/<hex>` and never holds the whole payload in memory; a second `put` of the same bytes uploads nothing; `get` streams the same bytes back; a key that is not `sha256/<64 lowercase hex>` is refused before any client call; an unset bucket or prefix raises `ImproperlyConfigured` naming the setting; with the flag OFF both refuse; a meta-test reds a `src/platform` import of `pyforge.*` and a `django_pyforge` import of `config.*`; the rendered chart names the bucket and prefix per release, carries only secret references for credentials, renders no object-store workload, and with `networkPolicy` enabled allows egress to the configured endpoint from web and worker only; `pyforge-steward-test` green.
- **CAP-164 — `steward keys` learns the GitHub Enterprise host: a read identity for the fleet scan, a PR-draft identity only for an approved proposal** ← spec-pyforge-steward CAP-164 (ready 2026-09-28; extends FR-5, FR-7)
  - **intent:** the host-scoped resolver (FR-7, `keys.py`) knows the enterprise host, read from `_http.py`'s existing `GITHUB_API_BASE_URL` row (`resolve_github_api_urls`; AD-9, no Steward-owned URL config); `keys.py` still decides only host membership, and `.claude/skills/conda-forge-expert/scripts/_http.py` does not change. Because `auth_headers_for` never sends a GitHub token to a GHES host, an inventory-issued enterprise identity is attached by `keys` itself, only when a URL's host is the enterprise host, through the same `HostScopedCredential` gate; every ambient credential still goes through `auth_headers_for` (AD-2, amended 2026-09-28). The inventory (FR-5) gains two `issued` rows, each with its own age-encrypted payload and each rotated by `steward keys rotate --scope`: `ghe-fleet-read` (clone and contents read, for the fleet scan) and `ghe-fleet-pr-draft` (pull-request drafts, used only to open a proposal the operator approved). A consumer receives a token only through `steward keys exec --scope <scope> [--approval <ref>] -- <argv>`: the child's environment carries `GH_HOST` and `GH_ENTERPRISE_TOKEN` for the enterprise host, the ambient `GITHUB_TOKEN`, `GH_TOKEN`, `GH_ENTERPRISE_TOKEN` and `GITHUB_ENTERPRISE_TOKEN` are removed from it first, and the token never appears on argv, stdout, stderr or a log. The draft scope refuses without an approval reference and journals the reference, scope, UTC time and the child's `argv[0]` (never the token) to `.steward/keys-exec.log`; the read scope never yields the draft token, and one payload serving both scopes is a `keys audit` finding. Deployed pods carry secret references only (canopy:AD-19); the chart wiring lands with the story that deploys the fleet scan. Nothing inbound: no webhook and no listener — the scan polls. Secrets never ride CLI flags; no PAT opens their org or writes ours on their behalf (`docs/dreams/work-passports-dated-extracts.md`); no calendar rotation and no provider API call (the Non-goals hold). Ships behind the flag `pyforge.steward.ghe_fleet_credentials` (`spec-feature-flag-governance` CAP-1), default off until the tree carries per-environment values: OFF, `keys exec` stays listed in `--help` as disabled and refuses with exit 2 and a flag-off message, and the resolver resolves no enterprise host (github.com behaviour unchanged). (Operator rulings 2026-09-28: the scan covers the enterprise fleet on GHE; a fleet fix PR opens only after the operator approves that proposal.)
  - **success:** with `GITHUB_API_BASE_URL` naming a fixture enterprise host, a `ghe-fleet-read` credential resolves a Bearer header for that host and nothing for github.com, another host, or a look-alike (a suffix or prefix of the host); with it unset, nothing resolves for any enterprise host; `keys exec --scope ghe-fleet-read` runs a child whose environment carries the read token and `GH_HOST` and none of the four ambient token variables, and a planted token appears in no argv, stdout, stderr or journal; `keys exec --scope ghe-fleet-pr-draft` without `--approval` exits 2 and runs nothing, and with one runs and journals the reference without the token; `keys list` and `keys audit` show both rows and never a value; `audit` reports a payload shared by both scopes; `keys rotate --scope` re-encrypts each; with the flag OFF `exec` exits 2 and the resolver resolves nothing for the enterprise host; the `JFROG_API_KEY` cross-host regression stays green; `pyforge-steward-test` green.
- **CAP-165 — the protected refs are declared once, the live rulesets are proven to match, and no session deletes what would orphan commits** ← spec-pyforge-steward CAP-165 (ready 2026-10-04; extends CAP-5, CAP-156, CAP-157; co-governs spec-pyforge-marshal:CAP-287)
  - **intent:** `docs/governance/guild-roster.json` declares `protected_refs`: each entry a full-refname prefix with a `kind` (`operational-branch`, `preserve-tag`, `archive-tag`, `legacy`), a `scope` (`origin`, `local` or `both`) and the server rules it needs. Every consumer unions the list with its own code floor, so the roster can only add (marshal:AD-27): the session hook (Story 63.3's) and marshal's sweeper read it directly, and marshal's in-code deleters receive it through marshal's policy layer. A ruleset document under `docs/governance/rulesets/` is rendered from the roster, never hand-edited: tag rulesets for `preserve/**`, `archive/**` and `rescue/**` with deletion, update and force-push rules and no bypass actor; `non_fast_forward` added to `loop/**`; creation of `refs/heads/preserve/**` and `refs/heads/archive/**` restricted. A runtime detector compares that document with the live rulesets through an authenticated `gh api` and fails closed when unauthenticated, rate-limited or erroring; applying a ruleset is the operator's settings change, never a session's. The hook denies every deletion form for a listed ref on its scope: branch and tag deletion by push, refspec, `git branch -d/-D`, `git tag -d`, `gh api -X DELETE` or `update-ref -d`; `push --mirror`; a `push --prune` or `fetch --prune-tags` that covers a listed prefix; `rm` or `git worktree remove` of a `~/.bmad-loops/` home; and `gh pr merge --delete-branch` naming a `loop/` head. For every branch and tag the list does not name, it denies a deletion whose tip is not an ancestor of `refs/remotes/origin/main` and that no `preserve/` or `archive/` tag contains, naming `marshal preserve tag` and the sweeper's `--retire` as the sanctioned forms. Each rule is a `session_denials` entry, by the operator's governance rulings of 2026-10-04. The hook is defence in depth: a matcher is a denylist, a git config such as `fetch.pruneTags` bypasses any command matcher, and harnesses with no hook deny surface are guarded by the rulesets alone, so the server ruleset is the guarantee. The pre-push gate skips, and journals, a push it can prove carries only `preserve/` or `archive/` tags (CAP-156 as amended). `workspace clean` parks an unlanded worktree's commits as a `preserve/` tag before it removes the worktree (CAP-157 as amended), behind the flag `pyforge.steward.workspace_preserve_tag`. (Operator ask 2026-10-04 after a hand-rolled cleanup; research `preserved-work-refs-2026-10-04.md` and its review.)
  - **success:** with a roster fixture, the hook denies each listed form for a listed ref, still denies deleting `main` and a `loop/` branch when the roster omits them (the floor), allows deleting an unlisted ref whose tip is an ancestor of `origin/main`, and denies deleting an unlisted branch or tag whose commits no other ref reaches; the ruleset document regenerates byte-identical from the roster; the parity detector exits 0 on a matching fixture, 1 naming each missing or extra pattern, rule or bypass actor, and 2 when `gh api rate_limit` shows no authenticated quota or any call fails, never passing; a tag-only preserve push skips the preflight with a journal line naming the ref while a mixed push still runs it; `workspace clean` writes the tag before removal and keeps the worktree when it cannot; `pyforge-steward-test` and `detectors-ci` green.
- **CAP-166 — every CI surface the operator can pause is declared once, switched by one convention, visible in one place and judged** ← spec-pyforge-steward CAP-166 (ready 2026-10-12; extends CAP-159, CAP-154; works with CAP-131)
  - **intent:** `docs/governance/ci-surfaces.yaml`, with a JSON Schema beside it, declares every GitHub Actions
    surface and its local twin (workflow, job, scheduled run, local stage) with its switch, switch class (`pause` |
    `enable`), owner, cost class, `gate` flag, `state` (`live`, `paused`, `opt-in-off`, `paused-manually`, `retired`),
    `paused_since`, `paused_by`, `reason`, `review_by`, local twin and canary. One convention: `PAUSE_<WORKFLOW>`
    gates every push/PR/schedule job, `PAUSE_<WORKFLOW>_<JOB>` exists only where a `cost: high` row does, `ENABLE_*`
    names an opt-in, `PAUSE_ALL_CI` is the master, `workflow_dispatch` ignores every pause, and the six existing names
    (`PAUSE_CONTAINER_BUILDS`, `PAUSE_PLATFORM_CONTAINER_BUILDS`, the four `PLATFORM_CI_*` opt-ins) stay, mapped in
    the registry. A script renders each job's `if:` fragment from the registry in front of the job's existing
    condition; a repo-scope detector in `detectors-ci` reds a `vars.X` no row names, a row whose job lacks its
    fragment, a naming violation, a comparison other than the literal `'true'`; its `--live` mode (authenticated `gh`,
    exit 2 when it cannot observe) also reds a `disabled_manually` workflow without a `paused-manually` or `retired`
    row. `steward ci status` reads the registry, `gh variable list`, the Actions API's workflow state and recent runs,
    and pending deployments, and prints one row per surface with a verdict: `live`, `paused`, `opt-in-off`,
    `paused-manually`, `retired`, `drift` (declared differs from live), `stuck` (a deployment waiting over 24 h, or
    five or more consecutive cancelled runs), `overdue` (`review_by` passed). It refuses an unauthenticated read at a
    0/60 rate limit, and its `--json` is the one shape the Doctor, Herald and Marshal consumers read. `steward ci vars
    --refresh` writes `.steward/ci-vars.json`. `steward ci pause|resume <surface> --reason --review-by` is a dry run
    until `--yes`, then sets the variable, updates the row, journals `.steward/ci-pauses.log` and captures to team
    memory; a `gate: true` row also needs `--i-am-removing-a-merge-gate`. `preflight_ci` resolves `vars.*` from the
    snapshot (stale after 24 h, then the registry's declared state, then today's unknown-runs rule) and journals each
    lane it skips as paused in CI with its switch, since and review-by date; `pr-preflight` banners and honors paused
    lanes (`--ignore-ci-pauses` runs them); `platform-ci-local` and the guild image build banner and run. A weekly
    canary workflow builds each paused `cost: high` surface once. A how-to and one `AGENTS.md` pointer document it.
    The four staged-recipes-linter workflows retire; `test-all` and `kedro-viz-publish` become `paused-manually` rows;
    tracked docs stop citing the deleted `ACTIONS_ENABLED` as live evidence. Operator rulings Q1–Q8 of 2026-10-12
    (memlog).
  - **success:** after seeding, the detector exits 0 on `main` and reds each planted fixture above; `preflight_ci`
    evaluates every workflow with no `unknown` site once the snapshot exists; a dispatch with `PAUSE_ALL_CI=true`
    still runs; `ci status` on a recorded `gh` fixture yields the expected verdict per row, including `drift`,
    `overdue`, and `stuck` for a replay of the 2026-10-06 waiting deploy; `ci pause` without `--yes` makes no `gh`
    call, and with `--yes` the fixture asserts the `gh variable set` argv, the registry diff, the journal line and the
    capture text; `pr-preflight` journals a paused lane as skipped and `--ignore-ci-pauses` runs it; the canary has
    one green run; no tracked doc cites `ACTIONS_ENABLED` as live evidence.
- **CAP-167 — the estate's library and BMAD pins move on one policy-driven, measured, repeatable path** ← spec-pyforge-steward CAP-167 (ready 2026-10-13; extends CAP-5, CAP-9..17, CAP-21..25, CAP-37; works with FR-14, FR-15 and spec-pyforge-doctor:CAP-66..:CAP-70)
  - **intent:** `docs/governance/pin-policy.yaml`, with a JSON Schema beside it, declares every held package once —
    `hold` (`never-move` | `cap` | `channel` | `exact` | `floor-only`), the clause to keep (`cap: "<3"`,
    `channel: SelfExplainML`, `exact: "4.2.1.*"`), `features`, `reason`, `authority` (a Story, CAP, gotcha or
    fnd:CAP-12) and `until` (the condition or date that retires the row) — and the canonical `pixi upgrade` command is
    rendered from it (`never-move` rows become `--exclude`), so the three comment generations in `pixi.toml:45-48`
    become one pointer line. `scripts/pin_policy_check.py` (repo scope, in `detectors-ci` and `pr-preflight`) reds an
    undeclared hold (a cap, inline table or exact pin with no row), a row with no declaration, a stale pointer, and
    under `--diff <base>` a lost cap, a flattened channel table, a lowered floor or a moved `never-move` package,
    naming package, feature, before and after; under `--fan-out` it compares every station package-level range
    (`src/shared/packages/*/pyproject.toml`, the package `pixi.toml`) with the locked version and reds one outside a
    station's range, naming the station — the refresh refuses to land it and the move is that station's story
    (CAP-12 generalized to every package; ruling Q13). `scripts/pin_policy_restore.py` rewrites each named declaration to its
    policy clause at the newly resolved floor, keeps its comment, re-locks with `pixi lock`, re-checks, and refuses by
    name when the lock cannot solve. `pyforge steward estate plan|refresh|reconcile|verify|status`, behind
    `pyforge.steward.estate_refresh`: `plan` runs `pixi upgrade --dry-run --json` through the policy and prints the
    moves (package, feature, from, to, held-by), the BMAD table (pinned floor, installed `_bmad/_config/manifest.yaml`,
    upstream latest through doctor's reader, fail-open offline) and days since the last journal, `--due` red past 30
    days; `refresh` refuses on a dirty tree or on `main`, renders the command, runs `pixi upgrade --pinning-strategy
    latest-up --json`, the guard, the restore and `pixi lock`, journals, and runs `pixi update` only under
    `--transitive`, operator-only; `reconcile` regenerates every derived surface by its own generator —
    `environment.yaml` by the exporter, the library catalog's floors by a new deterministic `llms_full_check.py
    --fix-floors`, the BMAD-estate catalog by `scribe catalog bmad-estate --write`, the env matrix by
    `pixi_env_matrix.py --update`, the generated docs by `docs-environments` and `docs-pixi-tasks`, the pixi-version
    sites by `bump-pixi-version` when the `pixi` floor moved, the `bmad-suite` metapackage by `generate-bmad-suite`
    when a `bmad-*` floor moved — runs every check by exit code, then appends one memlog event line and one scoped
    stamp per Spec the surface baseline names for the moved files (read from `scripts/.spec-surface-baseline.json`,
    never a list); `verify` installs the default tier `--frozen` in a detached worktree, never the working tree —
    the Guild, core, testing-kit, the eight station envs, `platform-ci-test`, `pyforge-foundry-full`; every
    environment under `--all` (ruling Q12) — then runs the lanes CI would run for a `pixi.toml` change (read from
    the workflows, CAP-159; CAP-166's pauses honored and named), the laptop SBOM gate, the recipe-factory import
    smoke, every realization-register probe, each distinct register test once and the fan-out, one row per
    environment, lane and probe carrying its platform; the atlas browser gate, herald's browser check and scribe's
    Postgres lane are named manual rows, never silently green; other platforms are lock-solved and said so, `estate
    status` names which platforms confirmed the current lock, and a refresh PR merges on lock-solved ×3 plus this
    platform's verify (ruling Q14). `docs/governance/realization-register.yaml`, with a JSON Schema, declares one
    row per library whose install has a side effect beyond the environment — `package`, `env`, `class`
    (`installer-tree` | `module` | `harness` | `kit` | `hooks` | `pin-sites` | `cli` | `service` | `import`),
    `realize` (argv or none; `operator_gate: true` where it rewrites installer-owned or settings files), `probe`
    (argv and `expect`), `test`, `owner`, `authority` — generalizing the install-class playbook (CAP-27, CAP-28) to
    `bmad-method` (realize `upgrade bmad-core --apply` then `prove-landed`; probe `_bmad/_config/manifest.yaml`),
    `bmad-module-skill-forge` (its own `update`; probe `skf-manifest.yaml`), every suite module (`provision
    --module`, CAP-18, CAP-23; probe `suite pipeline-truth`'s `installed` and `wired`, CAP-21, CAP-28), `bmad-loop`
    (`marshal refresh` per loop home and the CAP-12 fan-out sites; probe `bmad-loop --version` and `bmad-loop
    validate`), `caveman-installer` (`caveman-install --only claude --with-hooks`), `headroom-ai` and `codegraph`
    (probe `marshal seed check --json` kit items, CAP-162's envelope), `pre-commit` (`pre-commit install`; probe
    `precommit-config-check`), `pixi` (`bump-pixi-version`; probe `pixi-version-check`), the CLIs (`<bin> --version`
    equals the locked version in its env), the services (version and a boot) and the import-probed platform
    libraries (the laptop SBOM gate's probes, reused); `scripts/realization_register_check.py` (repo scope) reds a
    row no feature declares and a `bmad-*` / `mybmad*` pin (scribe's `read_pins`) or a marshal seed-kit item with
    no row (ruling Q11). `estate realize`: for each row whose package moved, or `--all`, run `realize` (an
    `operator_gate` row only under `--yes`, else journaled `skipped-operator-gate`; ruling Q10) then `probe`, and
    journal `{package, from, to, realize, probe: live | stale | missing}`; `--plan` writes nothing; `verify` reds
    on `stale` or `missing`, so the estate is confirmed live at its pins, not just locked; a moved `bmad-method`
    or `bmad-*` floor is handed to `upgrade bmad-core` pre-flight
    (CAP-9) and `pin-fan-out` (CAP-12) always, to the deliberate apply (CAP-10, CAP-14, CAP-16) and `prove-landed`
    (CAP-13) under `--apply-bmad`, and to `suite pipeline-truth` (CAP-21) with `suite advance` (CAP-22) named as the
    next operator step; an installed core below the pinned floor reds `verify`. One tracked journal per run,
    `.steward/estate-refresh/<date>.json`, validates against a shipped frozen schema. One how-to, one `AGENTS.md`
    pointer, and the release-cadence runbook's step 7 pointing at `estate refresh`; the first refresh lands through
    the path and supersedes the 2026-10-13 hand batch. Plan `docs/intake/estate-refresh/PLAN-2026-10-13.md`; its
    recommended answers Q1–Q9 are this capability's assumptions until the operator overrides them (memlog).
  - **success:** `pin_policy_check.py --diff` over the 2026-10-13 batch (a fixture pair) yields exactly nine
    findings — five lost caps, two flattened tables, two lowered floors — and zero on a floor-only move; the restore
    over that batch brings the check to 0 and `pixi lock` solves; `--fix-floors` over it brings `llms-full-check`
    from 81 findings to 0 with the prose byte-identical; a fake-subprocess fixture asserts the rendered argv of
    `plan` and `refresh` and that `--transitive` is the only path to `pixi update`; `verify` on a recorded fixture
    yields one row per environment and lane and reds on a 6.12.2-pinned, 6.12.0-installed core; the journal
    validates against the schema; the register check exits 0 on the seeded tree and 1 on a `bmad-*` pin or a
    seed-kit item with no row; `--fan-out` over a fixture whose lock holds `bmad-loop` 0.13.0 against marshal's
    `<0.13` range reds naming `pyforge-marshal`; a fake-subprocess fixture asserts `realize`'s argv per class, that
    an `operator_gate` row runs only under `--yes`, and that a probe never writes; `pyforge-steward-test` and
    `detectors-ci` green.
- **CAP-168 — the Pages deploy workflow is steward's duct** ← spec-pyforge-steward CAP-168 (ready 2026-10-14; extends CAP-2, CAP-166; works with CAP-159; reads `spec-pyforge-herald:CAP-52`, `spec-pyforge-herald:CAP-56`)
  - **intent:** `.github/workflows/pages.yml` is the one Pages workflow and the one `deploy-pages` caller, on this
    Spec's surface (off `spec-pyforge-herald`'s, which keeps `pages-build`, `pages-check`, `docsite/`, `docs-site/`
    and `/herald/`), in BMAD-METHOD `docs.yaml`'s shape: a `build` job on `pull_request` and on `push` to `main`,
    each filtered to the published inputs (`docs/tutorials/**`, `docs/how-to/**`, `docs/reference/**`,
    `docs/explanation/**`, `docs/index.md`, `docs/404.md`, `docs/map.yaml`, `docs/dashboard/**` until atlas
    Story 30.1 deletes the committed tree, `docs-site/**`, `docsite/**`, `presentations/**`, the workflow itself),
    on `workflow_dispatch`, on a weekly schedule and on a six-hourly schedule; `fetch-depth: 1` and a sparse checkout
    that takes `presentations/*/project/*.html` and nothing under `presentations/*/src/pptx`; `pages-check` is the
    build; a `pull_request` run uploads the built site as a PR artifact (`pages-site`) and never deploys;
    `docsite-check.yml` folds in and is deleted; a `deploy` job on `main` only, skipped when the built tree's hash
    equals the live site's — the built artifact carries `build.json` (tree hash, built-from sha, run id, built at),
    the hash is taken with `build.json` and the built-from footer excluded, the deploy job reads the live
    `<SITE_URL>/build.json` and compares, and an absent or unreadable one reads as changed — so a scheduled run that
    finds nothing changed costs a build and no deploy; concurrency `pages-build` with `cancel-in-progress` for
    `build` and `pages` without it for `deploy`; `timeout-minutes` on both. Every job carries its CAP-166 fragment;
    the registry rows `dashboard`, `dashboard.build` and `dashboard.deploy` are renamed in place to `pages` (switch
    `PAUSE_PAGES`; `stuck_rules` `deploy_waiting_hours: 24`, `consecutive_cancelled_runs: 5`), `pages.build` and
    `pages.deploy`, and `docsite-check` and `docsite-check.check` retire (`state: retired`, `retired_on`; Story
    99.7's convention for a deleted workflow), so `steward ci status` and the preflight read the new names. The
    `build` job downloads atlas's newest successful
    `kedro-viz-export` artifact (cross-run, `actions: read`) into the mount and, when none exists, skips the mount,
    hides the tile and exits 0. The `Resolve Pages host env` step and `export_pages_host_env.py` leave the workflow:
    `actions/configure-pages`'s `base_url` and `base_path` feed `SITE_URL` directly on github.com and on GitHub
    Enterprise, so the GHE how-to loses its flag step. Each deploy from `main` also uploads the built site as
    `pages-site.zip` on a rolling pre-release `pages-site` re-pointed at the deploying commit, the pull-the-zip path
    for the air-gapped host. A `pages` duty, `pyforge steward pages build|deploy|status`, replaces `deploy dashboard`
    and `deploy status` (FR-8..FR-11's reconciled push; their last caller, `kedro-viz-publish.yml`, stops committing
    to `main` under atlas Story 30.1): `build` runs `pixi run --frozen -e site pages-check` by subprocess and reports
    its exit; `deploy` runs `gh workflow run pages.yml --ref main` and reports the run and its deployment; `status`
    reports the live root's `last-modified` and `build.json`, the last `pages.yml` run (`gh run list`) and the
    registry verdict for `pages` (`ci status`'s reader). Behind `pyforge.steward.pages_duty`, which also gates the
    no-op skip, the artifact mount and the release asset through one Guild step that hands `pages.yml` the flag's
    state (CAP-56's and herald CAP-59's shape); off, the duty refuses naming the flag and the workflow deploys every
    build, mounts nothing and uploads no asset. The pre-push lane selection (CAP-159, Story 71.2) follows the file,
    since it reads `.github/workflows/*.yml` at run time. (Operator rulings 2026-10-13; the herald Dream's lead
    entry; decisions in `.memlog.md`, 2026-10-14.)
  - **success:** measured on `main` 30 days after Story 102.1 lands, Pages deploys are under 150 and no cancelled
    streak reaches five (today 720 deploys and 621 cancelled per 30 days; the filter replay says 132); after 102.2,
    one workflow touches Pages besides atlas's producer, `docsite-check.yml` is gone, and a fixture built tree
    against its own `build.json` yields `changed=false` and against a differing one `changed=true`, the hash
    unchanged by the built-from footer; after 102.3, `kedro-viz-publish.yml` and no other tracked file calls
    `steward deploy dashboard` or `deploy status`, `steward pages build` returns `pages-check`'s exit, `deploy` runs
    the `gh workflow run` argv a fake-subprocess fixture asserts, `status` prints its three lines from recorded
    `curl` and `gh` fixtures, `DUTIES` keeps its length and the two count assertions pass, and zero commits by
    `github-actions[bot]` land on `main` for Pages; after 102.4, a fixture run with the artifact mounts it and one
    without exits 0 with the mount skipped and the tile hidden; after 102.5, `pages.yml` has no `pages_second_host`
    step, the how-to has no flag step and names the zip, and `pages-site.zip` exists after a deploy;
    `scripts/ci_surface_gates.py --check` exits 0 with the renamed rows; `pixi run --frozen -e pyforge-steward
    pyforge-steward-test`, `flag-gate-check` and `detectors-ci` are green.

## Constraints

- **Folded from spec-sprint-ledger-query-module (2026-09-19):** steward never imports vizro (canopy:AD-13 / canopy:AD-23); exporters never write into another station's tree by default (flag + explicit `--output` only); the minted UUID is identity and tracker keys are aliases (CAP-140's rule); reads come from TRACKED ledgers only and `fleet_scan.parse_sprint_status` stays the reader of record; stdout carries payload only.

- **AD-1 (wrap, never reimplement):** every duty adapter's implementation is a subprocess call or a thin import into an existing tool (`_http.py`, `age`, `pixi`, `git`, `gh`, `scripts/bmad-loop-worktree`). A duty module containing its own copy of logic that already exists elsewhere in this repo is a review-blocking finding.
- **AD-2 (keys' single chokepoint):** `steward.keys`'s host-scoping resolver delegates to `_http.py`'s existing `auth_headers_for(url, skip_auth=...)` pattern for anything HTTP-shaped; no duty module constructs its own request carrying ambient auth headers. Host-allowlist configuration reads `_http.py`'s existing `resolve_*_urls`/`*_BASE_URL` table directly — no duplicate Steward-owned URL config. *(Amended 2026-09-28, CAP-164:)* an inventory-issued, host-scoped identity is attached by `keys` itself, only for the host its scope names (the enterprise host read from `_http.py`'s `GITHUB_API_BASE_URL` row), through the same `HostScopedCredential` gate; every ambient credential still goes through `auth_headers_for`, and `_http.py` does not change.
- **AD-3 (age-encrypted at rest, no standing service):** `age`/`age-keygen` are required external pixi run-dependencies, never vendored or reimplemented; `steward keys encrypt/decrypt/rotate` shell out to the `age` CLI. No Vault/Infisical-class secrets-manager server enters the dependency graph.
- **AD-4 (deploy is CLI-invoked reconciliation only):** `steward deploy dashboard` computes a diff (freshly-built output vs. the committed tree) before any git mutation; a no-diff run performs zero commits. No daemon, scheduler, or new GitHub Actions workflow ships in v1 — the operator or an existing workflow invokes the CLI directly against the existing Pages-serving branch.
- **AD-5 (provision wraps, never forks, Marshal-owned machinery):** `steward provision` subcommands shell out to `pixi install -e <name>` and `scripts/bmad-loop-worktree` verbatim; Steward's own code reads `pixi.toml`'s `[environments]` table for inventory but never writes to it and never re-implements pixi's resolution logic.
- **AD-6 (budget v1 is declared-not-enforced):** `steward budget check` returns one of three distinct exit codes — not-configured, under-budget, over-budget — never collapsing "no data" into a pass. No cost-integration import exists in the codebase until a future story adds a real metered spend source.
- **AD-7 (one shared Duty protocol; missing duty degrades, never crashes):** every duty module exposes a `Duty`-protocol-conforming object; `cli.py` dispatches through the protocol only. A duty not yet implemented for a given subcommand returns a result carrying an explicit "not implemented" status rather than raising.
- **AD-8 (exit-code sole ownership):** `main()` is the only place that returns a process exit code — it catches `KeyboardInterrupt`, `SystemExit` raised inside a duty, and any other `Exception` with fixed, documented codes, never the bare interpreter default `1`. A duty module never calls `sys.exit` directly.
- **AD-9 (enterprise routing inherited, never duplicated):** any new outbound HTTP endpoint Steward introduces is added as one new row to `_http.py`'s existing `resolve_*_urls` convention — never a parallel Steward-specific config mechanism.
- **CAP-5 (tasks move, never duplicate):** a task name exists in exactly one feature (`vocabulary-one-name-one-job` CAP-6 applied to pixi tasks); back-compat comes from environment composition, never from a second copy. `dashboard-layout-check`, `tea-playwright-*`, `retired-console-check` and every recipe-factory task stay in `local-recipes` — they import the atlas/CFE stack.
- **CAP-6 (§9 binds the loader before it exists):** the draft's Security Considerations — record the source beside the content; MUST NOT load from an untrusted source; trust-every-source is declared in the profile, never inferred; the composed set is made visible before loading; an `identifier` is asserted, not authenticated — are acceptance criteria for any story that loads a Frame into an agent's context (`marshal-token-economy` `[context.wire]`). No such loader exists; none may land without them. #29's `spec/fixtures/composition` are the conformance fixtures for a composing reader.
- **Credential provenance convention:** `steward keys list` entries carry a `provenance` field, `issued` (an `age` identity Steward itself minted) or `observed` (a pre-existing repo credential Steward's audit discovered but did not create). Both are listed for drift-audit visibility; only `issued` entries are rotatable via `steward keys rotate` in v1.
- **Credential values are never printed:** `steward keys list`/`audit` output never contains a raw secret value under any flag combination — enforced by a dedicated invariant test.
- **Provision's pixi invocations are explicit, user-triggered CLI actions only** — never an import-time or build-time side effect.
- **Config file location:** repo-root `.steward/` dotdir, tracked (not gitignored, not under `_bmad-output/`) — `budget.yaml`, `keys-inventory.yaml`, `*.age` payloads, and `sync-config.example.yaml` all live here, surviving a `bmad-switch` to a different active BMAD project, since a durable operational fact does not belong under a per-project planning-artifacts tree.
- **CAP-166 (pauses are written by the operator, through one path):** `gh variable set|delete` and enabling or
  disabling a workflow run only through `steward ci pause|resume --yes`, operator-invoked; agents read. The GitHub
  UI's disable button is not a pause path: an unregistered `disabled_manually` workflow is drift. A rendered fragment
  is a conjunction in front of a job's existing `if:`; no condition is lost. AD-4 binds the deploy duty only: the
  weekly canary builds paused images and is not a deploy.
- **CAP-167 (the pins move on the policy, by subprocess, through a PR):** steward's own code never writes
  `pixi.toml` — `pixi upgrade` and the repo mutator `scripts/pin_policy_restore.py` do, as subprocesses, the shape
  `bump_pixi_version.py` already has (AD-1; AD-5 as read since Story 72.1). `pixi update` runs only under `estate
  refresh --transitive`, operator-invoked; the session hook denies that form to agents (a `session_denials` row), who
  run `estate plan`, and `refresh` without it inside a worktree that lands through a PR. A lost cap, table or floor is
  restored from its policy clause, never from taste; an unsolvable restore is a refusal naming the row. Every
  regeneration goes through the surface's own generator, never a regex over a derived file; `--fix-floors` moves only
  existing rows' floors and leaves prose byte-identical. PostgreSQL stays 17 and the libpq caps stay (fnd:CAP-12, a
  `never-move` row). No daemon, workflow or cron: the operator runs the refresh monthly and `plan --due` is the clock.
  Installer-owned trees (`_bmad/**`, the bmad and skf skills, the caveman skill and hooks, `.claude/settings.json`)
  are re-applied only through their own installers under `estate realize --yes`, operator-invoked (a
  `session_denials` row denies the form to agents, as for `--transitive`); a probe never writes. No package-level station pin is rewritten by the refresh: a locked version outside a station's range is
  refused and named. The capability is A-side, ledger mode `rebuild`; no B surface, `docs/foundry/PIN.md` untouched.
- **CAP-168 (the duct is one workflow, one caller, by subprocess):** steward reaches `gh`, `git`, `curl` and the
  build task (`pages-check`) by subprocess (AD-1) and never imports herald's or docsite's code; the artifact's
  content stays herald's, the DAG export atlas's, `map.yaml` doctor's — this Spec owns the workflow file, the
  registry rows, the duty and the budget, nothing under `/herald/`. `main()` keeps every exit code (AD-8); the duty
  returns `DutyResult` and never calls `sys.exit`; one duty module (AD-7), the count assertions moving with it. AD-4
  is amended, not reversed: the deploy stays CLI-invoked reconciliation — `steward pages deploy` triggers one run of
  one workflow, and the deploy job's hash compare is the no-diff gate (zero deploys when nothing changed) — while
  PRD D6's "no new GitHub Actions workflow" clause is retired by the 2026-10-13 ruling, since the workflow already
  exists and moves here. One `deploy-pages` caller (herald herald:AD-21). Nothing outward beyond this repository's own
  Pages, release and Actions: no second repository, no bot commit on `main`, no cross-origin load. No job loses its
  existing `if:`; `workflow_dispatch` ignores every pause (CAP-166). The hash comparison reads the live site and
  writes no repository variable: `gh variable set` stays CAP-166's one write path. The registry rows under
  `docs/governance/` are a governance act landed by the story with its PR. The pre-push lane selection is read from
  the workflows (CAP-159), never a second list.

## Non-goals

- No standing secrets-manager service (Vault/Infisical/OpenBao-class server) — `keys` is a CLI + encrypted files only.
- No Backstage-class software catalog or scaffolder platform — `provision` is a CLI face over pixi, not a new IDP.
- No ArgoCD/Flux-class GitOps control plane — `deploy`'s reconciliation is CLI-invoked, not a standing controller.
- No Kubecost/OpenCost/Infracost-class cost-allocation integration in v1 — no live cloud spend exists to allocate against yet.
- No third-party credential-revocation API integration (JFrog, GitHub, Anthropic) — `keys revoke` records intent and guides manual remediation, it does not call provider APIs.
- No `presenton-pixi-image` on OpenShift or air-gap bundle install support in v1 — `deploy`'s v1 scope is the Pages dashboard only.
- No multi-operator / team features — single-operator dogfooded tooling.
- No calendar-based automatic key rotation scheduler — rotation in v1 is on-demand/risk-triggered.
- No required-status-checks ruleset on `main` in CAP-166 (operator ruling Q6, a separate decision), no rename of the
  six existing CI variables (Q7), no runtime feature-flag change, no rebuild of the recipe-build workflows, no
  python-foundry surface.
- No Dependabot, Renovate or scheduled workflow for pixi pins (CAP-167); the policy records today's 28 holds with
  their reasons and moves none of them; no new floor or cap on `pixi` itself; no `anaconda upload` or feedstock
  submission from the refresh (`suite advance` stays the operator's); no recipe-build workflow rebuild; no
  python-foundry surface; the 2026-10-13 hand batch is not committed as-is.
- No change to the artifact's content (herald's `docsite/**`, `docs-site/**`, the dossier, the decks), to `map.yaml`
  (doctor's) or to the Kedro-Viz producer (atlas Story 30.1 owns the `kedro-viz-export` upload and the deletion of
  `docs/dashboard/kedro-viz/`) under CAP-168; no Vizro board and no M3 generator work; no `/status/` renderer (herald
  renders the fleet board and guild status from `sprint-ledger-query --format json`, `scripts/fleet_picture.py` and
  `steward ci status --json`; this Spec supplies the schedule and the skip); no second `deploy-pages` caller and no
  reusable `workflow_call` until a second lane needs Pages; no PR comment bot and no per-PR preview environment
  (Pages has none; the PR artifact is the review surface); no change to `steward deploy perimeter|static`; no
  python-foundry surface (ledger mode `rebuild`).

## Success signal

The `JFROG_API_KEY` cross-host leak pattern has a passing, named regression test in Steward's conformance suite, and `steward deploy dashboard` replaces 100% of manual `dashboard-gen` + push invocations going forward. Supporting: `steward provision --env <name>` succeeds for every entry in the pixi estate without the operator consulting raw pixi syntax; `steward budget show` is queried at least once after any Dream/spec update touching the ceiling doctrine. Counter-signals that must NOT be optimized away: the number of duties/features shipped (a `budget` duty growing Kubecost-scale before real spend exists is over-building), and key-rotation frequency as a vanity metric (more rotations is not better).

## Assumptions

- Steward has exactly one user (this repo's maintainer, acting through every other pyforge persona and every bmad-loop session); no team/multi-tenant surface — not independently re-validated with the user this session.
- Third-party credential-revocation API integration is out of scope for v1 because Steward has no existing credential to call such APIs with today — inferred, not user-confirmed.
- The `1500usd/month` figure in the ceiling-declaration example is illustrative, carried from the Dream's own CLI cadence example — the actual ceiling value is a config input, not a Spec claim about real spend.
- `age`-based at-rest encryption (constraint AD-3) is the PRD's own lowest-confidence decision (flagged for architecture confirmation) — assumed durable only while Steward's secret inventory stays a handful of API keys; revisit if it grows materially.
- Direct-push deploy with no new GitHub Actions workflow (constraint AD-4) is a medium-confidence decision — assumed sufficient until scheduled/push-button deploy automation becomes a real want, at which point it should be revisited, not silently reversed.
- GitHub reports a job skipped by its `if:` as passing for a required status check, so a paused job never blocks a
  merge (CAP-166); GitHub's documented behaviour, not re-verified live on this repository.
- The plan's recommended answers Q1–Q9 (`docs/intake/estate-refresh/PLAN-2026-10-13.md` § 6) hold for CAP-167 until
  the operator overrides any of them; `pixi upgrade --dry-run --json` reports every manifest move as pixi 0.80's
  `--help` documents (not re-verified against a live run); a detached worktree's `pixi install --frozen` reproduces
  CI's fresh clone, and the 36 environments install on linux-64 within the session's disk budget (the Guild's 2 GB
  bound is the only measured size).
- `actions/download-artifact@v8` downloads another workflow's artifact given `run-id` and `github-token` under
  `actions: read` (GitHub's documented v4+ behaviour; not run live here — Story 102.4 is the proof); a six-hourly
  schedule queues at GitHub's discretion and may run minutes late, which the skip makes harmless;
  `actions/configure-pages@v6` emits `base_url` and `base_path` on GitHub Enterprise Server as on github.com
  (documented, not testable from this repository); the live `<SITE_URL>/build.json` is served within seconds of
  `deploy-pages` reporting success; nothing in `pages-check` reads git history once `presentations/*/src/pptx` is
  out of the checkout (Story 102.1's first check) — CAP-168.

## Open Questions

- Why were `test-all`, `kedro-viz-publish` and the four staged-recipes-linter workflows disabled on 2026-08-24,
  12:06–12:07? Nothing records it; the operator records the reason when CAP-166 seeds their `paused-manually` and
  `retired` rows.
- Which held packages retire their hold, and when (CAP-167)? Each policy row carries `until`, but today's reasons
  are scattered: Story 67.1's libpq-17 caps wait on psycopg-c builds against libpq 17 past 3.2.10, the `bmad-loop`
  SelfExplainML pins wait on the feedstock's `__win` build being served, and `cron-descriptor`'s and `openai`'s
  higher floors have no recorded author. The operator answers per row when Story 100.1 seeds the registry; a row
  with no `until` is a warning the check reports.
- Should `pages-site.zip` also attach to a CalVer release once one exists, and should the rolling `pages-site`
  pre-release then retire? And if a `PAUSE_DASHBOARD` variable is set live when Story 102.2 lands, does the
  operator move it to `PAUSE_PAGES` through `steward ci pause|resume --yes` (the only write path) or delete it?
  Both are the operator's (CAP-168).
