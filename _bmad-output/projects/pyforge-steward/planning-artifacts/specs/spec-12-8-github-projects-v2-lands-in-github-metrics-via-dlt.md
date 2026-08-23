---
title: GitHub Projects V2 lands in github_metrics via dlt
type: feature
created: '2026-08-23'
status: ready
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

- Pipeline dry-run / load test with mocked or live PAT (document setup)
- Steward test suite green
