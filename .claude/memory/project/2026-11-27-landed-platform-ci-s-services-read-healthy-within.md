---
name: "2026-11-27-landed-platform-ci-s-services-read-healthy-within"
description: "2026-11-27 LANDED: Platform CI's services read healthy within seconds of starting. PR #2429 merged as 1df8345d16 (Merge…"
metadata:
  type: project
---

2026-11-27 LANDED: Platform CI's services read healthy within seconds of starting. PR #2429 merged as 1df8345d16 (Merge pyforge-steward/117-31 into main; steward Story 117.31, spec-pyforge-steward CAP-175 realized with no text change), with 51 checks passed. Every PostgreSQL and Redis service in Platform CI's test and checks jobs and in scribe-live-test adds --health-start-period 30s --health-start-interval 1s. On the PR's own run each job's service wait fell from 13.4 s to 2 s, container start-up from 21 to 27 s to 10 to 15 s, test shards from 117 to 146 s to 104 to 114 s, and checks from 98 to 124 s to 94 s; scribe-live-test's container start-up took 8 s. The full preflight passed all 38 lanes in 321.5 s. Measured and left: the platform-ci-test cache is 835 MB (18 s to restore) because it carries Playwright's full Chromium beside the headless shell the suite launches, which is steward Story 131.1's ruling; dropping it is the operator's call. Still open from the 2026-11-27 lever survey: every job's checkout plus setup-pixi (30 to 40 s), and no lane lints _bmad/scripts/.
