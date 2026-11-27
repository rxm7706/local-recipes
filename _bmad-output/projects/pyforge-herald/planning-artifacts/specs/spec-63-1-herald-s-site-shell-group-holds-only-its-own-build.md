---
title: '63.1: Herald''s site-shell group holds only its own build'
type: 'chore'
created: '2026-11-27'
status: 'done'
story: 63-1-herald-s-site-shell-group-holds-only-its-own-build
spec: spec-pyforge-herald
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-herald/tests/meta/test_site_shell.py'
  - 'src/shared/packages/pyforge-herald/tests/meta/test_site_builders_share_a_worker.py'
  - 'tests/durations/pyforge-herald.json'
  - '_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-53-3-kedro-viz-opens-under-the-site-header-with-a-way-back.md'
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - docs/dreams/pyforge-herald.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Herald's third live shard is the longest job on a PR that runs herald's live half: 111 s, 72 s of it tests, where the other two shards take 38 to 53 s. A probe run that printed every test's time on the runner (run 46072884555, never merged) shows why. In that shard, `test_site_shell.py`'s `shell` xdist group runs in turn on one worker:

| Step | Runner time |
|---|---|
| the `shell` fixture's build | 25.6 s |
| `test_53_3_no_framed_page_without_the_export_or_without_the_shell`, its own build | 16.0 s |
| `test_53_1_pages_check_passes_and_names_a_page_without_the_header`, two pages-check runs | 12.1 s |

That is about 55 s of the shard's 66 s. The second test reads `shell` for one check, that the tracked tree mounts no Kedro-Viz export, and then builds a fixture tree with the shell off. Taking `shell` puts it in the fixture's group, so its build waits for the group's. Story 60.1 took this shape out of `test_agent_surface_and_changes.py` and `test_one_generator.py`; this is the one test left that both takes a module fixture of a builder module and starts a build.

**Approach:**
- The test becomes two, each with its assertions: `test_53_3_no_framed_page_without_the_export` reads `shell`; `test_53_3_no_framed_page_without_the_shell` takes no module fixture and builds its own tree.
- `test_site_builders_share_a_worker.py` gains `test_no_grouped_test_starts_a_build_of_its_own`. It reads every builder module's source and reds a test that takes one of its module's module-scoped fixtures and calls `astro_build`, directly or through a module function that reaches it. `test_the_grouped_build_rule_fires` feeds it a synthetic module.
- `tests/durations/pyforge-herald.json` drops the old test's key and names the two new ones, measured with the module run at four workers.
- Story 53.3's spec names the new test where it named the old one.

Ledger key: `63-1-herald-s-site-shell-group-holds-only-its-own-build`.

### Living CAP citations

- spec-pyforge-steward:CAP-175 (realized here; no text change in this station's Spec).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Every assertion holds as before.

**Never:**
- Never skip or re-mark a test.

## Acceptance Criteria

**Given** herald's live half
**When** it runs with the docs site installed
**Then** the `shell` group holds one build, and the guard holds the rule for every builder module

- **AC1 — The two modules pass, with the built-site tests required.** Expected: exit 0.

  ```bash
  HERALD_DOCS_SITE_REQUIRED=1 PYTHONPATH=src/shared/packages/pyforge-herald/src:scripts pixi run --frozen -e pyforge-herald pytest src/shared/packages/pyforge-herald/tests/meta/test_site_shell.py src/shared/packages/pyforge-herald/tests/meta/test_site_builders_share_a_worker.py -n 4 --dist loadgroup -q
  ```

- **AC2 — The live half passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-herald pyforge-herald-live-test
  ```

</intent-contract>

## Result (2026-11-27)

- The guard names the old test on `origin/main`'s `test_site_shell.py` and nothing on the new one.
- By the probe run's runner times, the longest xdist group of the shard holding `test_site_shell.py` falls from 55.1 s to 39.2 s.
- AC1: 53 passed, 1 skipped (the agent-surface module's check, which needs that module in the run).
