---
title: GitHub Projects V2 lands in github_metrics via dlt
type: feature
created: '2026-08-23'
status: in-progress
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-12-4-the-cluster-bring-up-is-documented-reproducible-and-key-disciplined.md'
warnings: []
baseline_revision: b3e069981e
---

<intent-contract>

## Intent

**Problem:** GitHub Projects V2 data must load into `github_metrics` dataset for board visibility (CAP-5).

**Approach:** Small dlt pipeline with custom GraphQL source (reuse steward/sync.py query patterns); classic PAT with `read:project`; load items/fields/status to Postgres via port-forward within 5k points/hr budget.

## Acceptance Criteria

- Custom dlt GraphQL source loads Projects V2 items/fields/status into `github_metrics` on cluster Postgres.
- Board created and repo-linked via `gh project link`; queryable end-to-end.
- Respects 5,000 GraphQL points/hr budget.
- Kin-declared to spec-jira-github-projects-sync Mode B — no second sync engine.

## Boundaries & Constraints

**Never:** Duplicate steward/sync.py as a parallel engine. Fine-grained PATs cannot reach user-owned projects — document classic PAT requirement.

</intent-contract>

## Verification

- `pixi run -e python-agent-platform github-metrics-dlt-test`
- `pixi run -e pyforge-steward pyforge-steward-test`
- Pipeline dry-run: `GITHUB_TOKEN=… pixi run -e python-agent-platform github-metrics-dlt -- PVT_… --dry-run --max-pages 1`

## Code Map

- `src/platform/ingest/github_projects/` — custom dlt GraphQL source + pipeline CLI
- `src/platform/tests/test_github_metrics_dlt.py` — mocked GraphQL + dry-run tests
- `src/platform/deploy/overlays/ocp/cluster-bringup.md` — §12 operator quick path
- `pixi.toml` — `dlt`, `duckdb`, `pyforge-steward` on `python-agent-platform`; `github-metrics-dlt` tasks

## Tasks & Acceptance

**Execution:**
- [x] Custom dlt source (`project_v2_fields`, `project_v2_items`, `project_v2_item_field_values`) via shared page cache
- [x] GraphQL client reuses `pyforge.steward.sync.github_graphql_request` + pagination budget guard
- [x] `github-metrics-dlt` / `github-metrics-dlt-test` pixi tasks on `python-agent-platform` (py3.12)
- [x] README: classic PAT, port-forward, `gh project link`, kin to Mode B
- [x] cluster-bringup.md §12 cross-link

**Acceptance Criteria:**
- Given a classic PAT with `read:project`, when the pipeline runs against a linked ProjectV2 board, then items/fields/status land in `github_metrics` tables queryable in Postgres.
- Given `--dry-run`, when mocked or live GraphQL succeeds, then extract+load completes without Postgres credentials.
- Given pagination, when `rateLimit.remaining` drops below threshold, then fetching stops before exhausting the 5k/hr budget.

## Spec Change Log

- 2026-08-23: Story 12.8 implementation — dlt ingest pipeline + tests + bring-up doc §12.

## Review Triage Log

## Design Notes

- Read-only ingest kin to `spec-jira-github-projects-sync` Mode B — never calls `steward sync reconcile` or Jira.
- dlt lives on `python-agent-platform` (Python 3.12); repo-default `local-recipes` env stays py3.14 where dlt remains blocked.
