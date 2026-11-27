---
title: '117.31: Platform CI''s services read healthy within seconds of starting'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 117-31-platform-ci-s-services-read-healthy-within-seconds-of-starting
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - '.github/workflows/platform-ci.yml'
  - '.github/workflows/pyforge-station-tests.yml'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Platform CI test shard takes 117 to 146 s, but the suite itself runs for only 47 to 70 s. On PR #2425's
run, "Initialize containers" took 21 to 27 s per job, and 13.4 s of that was spent waiting for the services.

PostgreSQL and Redis are probed every 10 s, so the first probe comes 10 s after a service starts. The runner checks
health with backoffs of 2, 3 and 7 s, so it saw both services healthy 13 s after they started. The `checks` job and
scribe's live job run the same kind of service.

**Approach:** each service adds `--health-start-period 30s --health-start-interval 1s`. During its first 30 s, Docker
probes the service every second, and probes that fail in that window do not count against its retries. A service
then reads healthy within a second of being ready, and the runner's first or second check finds it healthy. The
steady health check (`--health-interval 10s --health-timeout 5s --health-retries 5`) is unchanged.

Ledger key: `117-31-platform-ci-s-services-read-healthy-within-seconds-of-starting`.

### Living CAP citations

- spec-pyforge-steward CAP-175 / FR-49 (realized, no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- The services, their images, their ports and their steady health checks stay as they are.

**Never:**
- Never change a test, a job or a lane.

## Acceptance Criteria

**Given** a job with PostgreSQL and Redis services
**When** the runner starts them
**Then** it reads them healthy within seconds of starting, not 13 s after.

- **AC1 — Every service of the three jobs probes while it starts.** Expected: five services, each with both options.

  ```bash
  python3 -c "import yaml; [print(j, n, '--health-start-interval 1s' in s['options'] and '--health-start-period 30s' in s['options']) for p in ('.github/workflows/platform-ci.yml', '.github/workflows/pyforge-station-tests.yml') for j, job in yaml.safe_load(open(p))['jobs'].items() for n, s in (job.get('services') or {}).items()]"
  ```

- **AC2 — The option works as described.** On local Docker 29.9.1, a container that becomes ready 3 s after start
  reads healthy after 10.5 s at the 10 s interval, and after 3.3 s with the start interval.

- **AC3 — This PR's own Platform CI run is shorter at start-up.** The "Waiting for all services to be ready" group of
  a test shard ends within a few seconds of the services starting.

</intent-contract>

## Result (2026-11-27)

- **AC1:** all five services, `test` and `checks` in Platform CI and `scribe-live-test`, print `True`.
- **AC2:** the local probe read healthy after 10.47 s before the change and 3.28 s after it.
- **AC3:** read from this PR's own run.
