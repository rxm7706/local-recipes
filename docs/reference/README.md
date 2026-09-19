# docs/reference — Reference quadrant

Exact CLI/config/schema surfaces, inventories, and policy charters. Part of the
Diátaxis-adapted general docs layer — see [`docs/MAP.md`](../MAP.md) for the full
four-quadrant map and per-file classification.

Architecture-rationale ("why") content lives in [`docs/explanation/`](../explanation/).
Tutorials live at [`docs/tutorials/`](../tutorials/); how-to guides at [`docs/how-to/`](../how-to/).

Descriptions of what exists — never aspirations (`docs/dreams/`) and never BMAD
contracts (`_bmad-output/*/planning-artifacts/`; legacy: `docs/specs/`).

## Reference files

- `container-base-layer-convention.md` — base-tag pinning, multi-stage pixi-materialization, and `--mount=type=secret`-only credential rules shared by all three Containerfiles; guard test: `tests/packaging/test_containerfile_base_layer_convention.py`.
- `conda-forge-packaging-inventory-operations_prompt.md` — standalone re-run prompt the inventory runner must obey.
- `conda-forge-packaging-inventory-operations_replay.md` — replay / sync contract for that runner + prompt + curated config.
- `developer-guide.md` — recipe format examples, platform matrix, configuration reference (operational content split to tutorials/how-to in Story 22.5).
- `pixi-config-jfrog.example.toml` — JFrog pixi config example.
- `library-llms-full.md` — generated library catalog (detector: `pixi run -e pyforge-guild llms-full-check`). **Refresh needed** — regenerate via catalog header prompt.
- `github-workflows.md` — inventory of `.github/workflows/*.yml`. **Refresh needed as of 2026-08-15**: still lists 4 retired workflows and omits 4 that now exist — self-dated "Audited 2026-07-26."
- `test-charter.md` — testing charter backing `docs/dreams/pyforge-testing-charter.md` / `spec-pyforge-testing-charter`.
- `station-verify-commands.md` — derived verify-command lookup for PyForge stations. **Refresh needed** — keep in sync with `marshal-policy.toml` files.
- `sync-jira-github-workflow-templates/` — reusable GitHub Actions workflow templates for the (still-open) Jira↔GitHub Projects sync effort; see `archive/docs/intake/jira-github-projects-sync/` (archived 2026-09-19, doctor 23.4).

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
