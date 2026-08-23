# GitHub Projects V2 → `github_metrics` (Story 12.8)

Read-only dlt ingest kin to [`spec-jira-github-projects-sync`](../../../../_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-jira-github-projects-sync/SPEC.md) Mode B — **not** a second sync engine and never calls Jira or `steward sync reconcile`.

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Classic GitHub PAT | Scope `read:project`. **Fine-grained PATs cannot reach user-owned projects** — record as `github-pat-read-project` in `.steward/keys-inventory.yaml` (metadata only). |
| GitHub Projects board | Create with `gh project create`, link to this repo with `gh project link <number> --owner <user\|org> --repo rxm7706/local-recipes`. |
| Cluster Postgres | Port-forward the chart postgres Service, e.g. `oc port-forward -n platform svc/platform-postgresql 5432:5432`. |
| Pixi env | `python-agent-platform` (Python 3.12 — dlt is blocked on the repo-default 3.14 env). |

## Environment variables

```bash
export GITHUB_TOKEN='<classic-pat-with-read:project>'
export GITHUB_METRICS_DATABASE_URL='postgresql://<user>:<pass>@127.0.0.1:5432/<db>'
```

Never commit `.dlt/secrets.toml` or PAT values. The `github_metrics` schema is created by dlt (`dataset_name="github_metrics"`) — do not hand-`CREATE SCHEMA`.

## Run

Dry-run (mocked or live PAT, no Postgres):

```bash
pixi run -e python-agent-platform github-metrics-dlt -- \
  PVT_yourProjectId --dry-run --max-pages 1
```

Full load (after port-forward):

```bash
pixi run -e python-agent-platform github-metrics-dlt -- PVT_yourProjectId
```

Verify:

```sql
SELECT count(*) FROM github_metrics.project_v2_items;
SELECT item_id, field_name, value_option_name
FROM github_metrics.project_v2_item_field_values
WHERE value_option_name IS NOT NULL;
```

## GraphQL budget

Pagination uses `first ≤ 100` (GitHub's Relay cap) and reads `rateLimit.remaining` each page, stopping before the primary 5,000 points/hr budget is exhausted. Use `--max-pages` for smoke tests.

## Board setup (one-time)

```bash
gh project create --owner @me --title "PyForge Steward" --format json
gh project link <number> --owner @me --repo rxm7706/local-recipes
```

Copy the returned `id` (`PVT_…`) into `.steward/sync-config.example.yaml` / your gitignored `.steward/sync-config.yaml` when running the Jira↔GitHub sync duty — the dlt pipeline uses the same project id.
