# docs/reference — Reference quadrant

Exact CLI/config/schema surfaces, inventories, and policy charters. Part of the
Diátaxis-adapted general docs layer — see [`docs/MAP.md`](../MAP.md) for the full
four-quadrant map and per-file classification.

Architecture-rationale ("why") content lives in [`docs/explanation/`](../explanation/README.md).
Tutorials live at [`docs/tutorials/`](../tutorials/README.md); how-to guides at [`docs/how-to/`](../how-to/README.md).

Descriptions of what exists — never aspirations (`docs/dreams/`) and never BMAD
contracts (`_bmad-output/projects/<slug>/planning-artifacts/`; legacy: `archive/docs/specs/`).

## Reference files

- `container-base-layer-convention.md` — base-tag pinning, multi-stage pixi-materialization, and `--mount=type=secret`-only credential rules shared by all four Containerfiles; guard test: `tests/packaging/test_containerfile_base_layer_convention.py`.
- `conda-forge-packaging-inventory-operations_prompt.md` — standalone re-run prompt the inventory runner must obey.
- `conda-forge-packaging-inventory-operations_replay.md` — replay / sync contract for that runner + prompt + curated config.
- `developer-guide.md` — recipe format examples, platform matrix, configuration reference (operational content split to tutorials/how-to in Story 22.5).
- `pixi-config-jfrog.example.toml` — JFrog pixi config example.
- `library-llms-full.md` — library catalog derived from `pixi.toml`; the detector `pixi run -e pyforge-guild llms-full-check` reports drift.
- `bmad-estate-llms-full.md` — generated picture of the BMAD estate: installed core/modules, skills by family, the suite roster with wielder + provisioning path, `bmad-*` pins, the marshal harness range, the release cadence (scribe Story 24.1, `spec-pyforge-scribe` CAP-32). Never hand-edited: regenerate with `pixi run -e pyforge-guild scribe catalog bmad-estate --write`; detector `pixi run -e pyforge-guild bmad-estate-check` (structured, prose exempt).
- `github-workflows.md` — generated inventory of `.github/workflows/*.yml` (name, triggers, gating, jobs). Regenerate with `pixi run -e pyforge-guild docs-github-workflows`.
- `test-charter.md` — testing charter backing `archive/docs/dreams/pyforge-testing-charter.md` / `spec-pyforge-testing-charter`.
- `station-verify-commands.md` — verify-command lookup for PyForge stations, derived from each station's `marshal-policy.toml`.
- `station-cheat-sheet.md` — generated lookup of each station's console script, package and environments.
- `environments.md` — generated list of every pixi environment and the features it composes.
- `detectors.md` — generated list of every detector `detectors` and `detectors-ci` can run.
- `skills-catalog.md` — generated list of every skill under `.claude/skills/`.
- `judgement-vocabulary.md` — what gate, verdict, finding and the other judging words mean, and their exit codes.
- `story-spec-flag-block.md` — the feature-flag block every story spec carries.
- `agent-instruction-notes.md` — detail `AGENTS.md` and `CLAUDE.md` no longer carry: the incident behind a rule, and moved sections.
- `agent-memory-lifecycle.md` — the team-memory schema and the `scribe capture` promotion workflow.
- `herald-web-dashboard.md` — Herald's web dashboard: tabs, filters, states and the snapshot exporters.
- `herald-webhook-endpoint.md` — Herald's webhook: routes, auth, responses, payload rules and deduplication.
- `marshal-seed-findings.md` — every `marshal seed` finding and its remedy.
- `marshal-seed-managed-regions.md` — the managed-region contract `marshal seed` writes and refreshes.
- `sync-jira-github-workflow-templates/` — reusable GitHub Actions workflow templates for the Jira↔GitHub Projects sync; see `archive/docs/intake/jira-github-projects-sync/` (archived 2026-09-19, doctor 23.4).

## Relocated to How-to (redirect stubs remain here)

- `antigravity-developer-startup.md` → [`docs/how-to/antigravity-developer-startup.md`](../how-to/antigravity-developer-startup.md)
- `manticore-studio.md` → [`docs/how-to/manticore-studio.md`](../how-to/manticore-studio.md)

## Relocated to Explanation (redirect stubs remain here)

- `mcp-server-architecture.md` → [`docs/explanation/mcp-server-architecture.md`](../explanation/mcp-server-architecture.md)

## Relocated to Explanation (redirect stubs deleted, Story 23.2)

- `enterprise-deployment.md` → [`docs/explanation/enterprise-deployment.md`](../explanation/enterprise-deployment.md)
- `airgap-distribution-contract.md` → [`docs/explanation/airgap-distribution-contract.md`](../explanation/airgap-distribution-contract.md)

## Archived (superseded, kept at `archive/docs/reference/`)

- ~~`GuildHall_Fleet_Status.md`~~ — static fleet-status snapshot superseded by the live dashboard and `pixi run -e pyforge-guild fleet-picture`. Archived 2026-08-15.
