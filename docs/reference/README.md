# docs/reference — how the factory works today

Living reference documentation (Diátaxis: reference/how-to). Descriptions of
what exists — never aspirations (those are `docs/dreams/`) and never contracts
(BMAD planning-artifacts; legacy: `docs/specs/`).

- `developer-guide.md` — local testing + recipe development guidelines.
- `mcp-server-architecture.md` — the FastMCP server + PyPI name mapping.
- `enterprise-deployment.md` — air-gapped environments + JFrog Artifactory.
- `pixi-config-jfrog.example.toml` — the JFrog pixi config example.
- `library-llms-full.md` — the generated library catalog (detector:
  `pixi run -e local-recipes llms-full-check`).
- `github-workflows.md` — inventory of `.github/workflows/*.yml`. **Refresh
  needed as of 2026-08-15**: still lists 4 retired workflows
  (`automate-review-labels.yml`, `correct_directory.yml`,
  `create_feedstocks.yml`, `do_not_edit_example.yml`) and omits 4 that now
  exist (`detectors.yml`, `herald-live-demo.yml`, `kedro-viz-publish.yml`,
  `platform-ci.yml`) — self-dated "Audited 2026-07-26," due for regeneration
  against the live `.github/workflows/` tree.
- `test-charter.md` — the testing charter backing `docs/dreams/pyforge-testing-charter.md`
  / `spec-pyforge-testing-charter`.
- `sync-jira-github-workflow-templates/` — reusable GitHub Actions workflow
  templates for the (still-open, undecided) Jira↔GitHub Projects sync effort;
  see `docs/intake/jira-github-projects-sync/`.

Archived (superseded, kept at `archive/docs/reference/` — structure-preserving,
never deleted):
- ~~`GuildHall_Fleet_Status.md`~~ — a static fleet-status snapshot, self-dated
  "Last refreshed 2026-08-08" but already order-of-magnitude wrong for that
  date (e.g. atlas shown at 7/7 stories against a real 55-story scope).
  Nothing in the repo points to it as authoritative — the live published
  dashboard (`https://rxm7706.github.io/local-recipes/`) and
  `pixi run -e local-recipes fleet-picture` are the current sources. Archived
  2026-08-15 rather than refreshed, since a static markdown snapshot of fleet
  counts will always drift again.
