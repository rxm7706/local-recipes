---
name: "2026-11-28-landed-a-crowded-station-tests-run-fits-the-accou"
description: "2026-11-28 LANDED: a crowded station-tests run fits the account's job limit, and three CI jobs stop repeating work. PR…"
metadata:
  type: project
---

2026-11-28 LANDED: a crowded station-tests run fits the account's job limit, and three CI jobs stop repeating work. PR #2448 merged as b6572a4655 (Merge pyforge-steward/117-41 into main; steward Stories 117.41 to 117.44, spec-pyforge-steward CAP-175 realized with no text change), with 46 checks passed and 9 skipped. 117.41: the changes job's table gives eight suites one shard fewer when a run would start more than 29 station test jobs; the pull request's own run started 29, waited at most 4 s for a slot (62 s on PR #2446) and took 146 s (178 s). A one-shard job passes no pytest-split options. 117.42: kedro-catalog-check runs once, on atlas-live-test's second shard. 117.43: Platform CI's test job installs pyforge-warden with platform-ci-test at setup, under the cache key platform-ci-test-warden-; on dispatch 46144825032 test job 2's suite took 64 s in pytest (82.5 s), and its first cache entry is written by the push of b6572a4655, not yet checked. 117.44: the docker legs of the guild, platform and dbgpt image builds store their images uncompressed; layer export took 50.8 s (167.3 s), 17.8 s (48.8 s) and 14.1 s (45.4 s). Measured and left: the local preflight's late doctor lanes (the laptop is at capacity), and the golden-path promotion's builds (it records their image IDs and may push them).
