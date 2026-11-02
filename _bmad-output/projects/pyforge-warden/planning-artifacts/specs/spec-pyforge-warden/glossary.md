# Glossary — Warden

Companion to `SPEC.md`, pointer-only: one line per station term the Spec uses, each saying where the term is
defined. Fleet terms (station, `CAP-n`, `FR-n`, `AD-n`, A and B, the tiers, Path B, Lane 1 and Lane 2) are in
`docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md` § 0. Rungs, the lattice and the exit projection are in
`verdict-contract.md`, the axes in `axes.md`, and extraction, identity and withhold reasons in
`extraction-contract.md`. Code paths below sit under `src/shared/packages/pyforge-warden/src/pyforge/warden/`
(`pyforge.warden`) or `src/shared/packages/django-warden/src/django_warden_fabric/` (`django-warden`).

- **`vuln:` finding** — a security-axis finding whose id is `vuln:<advisory>:<name>@<version>`; the id families are in `_bmad-output/projects/pyforge-warden/planning-artifacts/finding-id-verdict-encoding-decision.md`.
- **`advisory` section** — the report's open `advisory` array (`data/report-schema.json`): TEA and opengrep notes that never become a finding, a rung or the exit code.
- **`actuation` section** — the report's open `actuation` object (`data/report-schema.json`): the fix-PR actuator's outcomes, outside status and exit composition (CAP-12).
- **suite:AD-4** — "Advisory lenses never gate", in the steward spine's bmad-suite decisions (`_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md`).
- **TEA** — BMAD's Test Architect module, `bmad-method-test-architecture-enterprise`, whose `tea-test-review` CLI warden runs as an advisory lens (`docs/reference/bmad-estate-llms-full.md`).
- **TEA advisory, default runner** — `tea_advisory.py`'s optional scanner and its `_default_runner`, which spawns TEA through `engines.run_tea_test_review_engine`.
- **Roster** — the one BMAD module roster, suite:AD-9 (same spine); the TEA advisory refuses (`TeaRosterMissingError`) when it lacks `tea`.
- **Omit-not-error** — an enabled optional scanner whose binary is absent contributes nothing and raises nothing (`scanner_plugins.py`; `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-9-3-default-warden-stays-green-without-checkmarx.md`).
- **`WARDEN_OPTIONAL_SCANNERS`** — the environment list of optional scanner ids a run enables (`scanner_plugins.OPTIONAL_SCANNER_IDS`).
- **SAST slot, `ghas` stub** — the `opengrep` optional scanner id beside `ghas`, an id with no engine behind it (`scanner_plugins.py`).
- **PR-gate hook book** — the PR-gate hook specs warden publishes (canopy:FR-44; `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-9-1-warden-publishes-the-pr-gate-hook-book.md`).
- **Estate rules** — the opengrep rules the package ships in `data/sast-rules/`, each with a tripping fixture under `src/shared/packages/pyforge-warden/tests/fixtures/sast-trips/`.
- **Estate** (CAP-24, CAP-26) — the estate's own repos, the estate allowlist below; in CAP-7 and the Scope Constraint "estate" is the downstream data estate that reads reports.
- **Estate allowlist** — the `fix-pr-estate-repos` key, `EffectiveConfig.fix_pr_estate_repos` in `config.py`; `run_actuator`'s `authorized_fleet_repo` is the per-call fleet exception.
- **Forge, forge API** — the code host's REST API the actuator opens PRs through (`GitHubForgeClient`, `actuator.py`); not the Dream's `forge` tool.
- **Solver** — `fix_solver.default_pixi_lock_solver`, a `pixi lock` over a throwaway copy; its range is `engines.PIXI_VERSION_RANGE`.
- **Throwaway copy, throwaway clone** — a `mkdtemp` (`0700`) copy of the scan target (`manifest_fixup.copy_scan_target`) or shallow clone of a fleet repo (`fleet.shallow_clone`), removed on success and failure.
- **Native lockfile, native ecosystem** — a lockfile osv-scanner parses itself, npm, Go or Cargo (`native_lockfiles.py`).
- **django-warden** — the station's Django package (`django_warden_fabric`): models, Celery tasks, management commands and the Lane 2 portal at `/stations/warden/` (`portal_urls.py`).
- **ComplianceJob pattern** — `models.ComplianceJob`: one row per job, run by a Celery task, its status the job vocabulary.
- **Keys-not-blobs** — a Celery message carries row ids only, never a report, an export or a token.
- **Job vocabulary** — `models.JobStatus`: pending, running, succeeded, failed; never a verdict.
- **Fleet run** — a `FleetRun` row with one `FleetRepoScan` per inventoried repo (`models.py`, `tasks.run_fleet_run`).
- **Proposal** — a `FixProposal` row, one queued fleet fix, its lifecycle in `FixProposal.State` (`models.py`; `proposals.py`).
- **Operator-designated organisation** — the github.com organisation named only in the gitignored `.warden/fleet-target.toml` (`WARDEN_FLEET_TARGET_CONFIG`; `fleet_inventory.py`); fixtures say `example-org`.
- **Fleet exports** — the gitignored `.warden/fleet-inventory.json` and `.warden/fleet-project-items.json` (`fleet_inventory.py`, `fleet_project_items.py`).
- **`head_sha`** — a listed repo's default-branch tip, read by `fleet_github_rest.py`.
- **Leak guard** — the platform test that forbids the organisation's name and the listed terms in tracked files (`src/platform/tests/test_warden_fleet_inventory.py`; `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-18-1-the-leak-guard-forbids-the-listed-terms-everywhere-and-the-organisation-s-name-in-warden-s-files.md`).
- **Platform suite** — `pixi run -e pyforge-guild platform-ci-local -- --test`, the local twin of `src/platform`'s CI lane (AGENTS.md § *Running and verifying*).
- **`pyforge-warden-test`** — the station suite, `pixi run --frozen -e pyforge-warden pyforge-warden-test`.
