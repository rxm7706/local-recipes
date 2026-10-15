---
title: '102.2: One Pages workflow in upstream shape builds on every change and deploys only what changed'
type: 'feature'
created: '2026-10-14'
status: 'in-review'
baseline_revision: '22e5c19c285e722bcf7d58203689d57e9cc4dd55'
flag:
  key: pyforge.steward.pages_duty                 # new; minted by this story (102.3, 102.4 and 102.5 reuse it)
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through Epic 76's overlay (src/platform/config/flag-overlays.json)
  scope: global                                   # v1 is global only
  fallback: 'the deploy job deploys every successful build, as dashboard.yml does today; build.json is still written, the live hash is not consulted'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-102-1-the-pages-workflow-is-steward-s-and-fires-only-on-the-published-inputs.md
  - docs/dreams/pyforge-steward.md
  - docs/dreams/pyforge-herald.md
  - _bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/brainstorm-intent.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/design-thinking-pyforge-herald-pages-redesign-2026-10-13.md
  - .github/workflows/pages.yml
  - .github/workflows/docsite-check.yml
  - docs/governance/ci-surfaces.yaml
  - docs/governance/ci-surfaces.schema.json
  - scripts/ci_surface_gates.py
  - scripts/_ci_surface_gates_lib.py
  - scripts/pixi_version_registry.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/ci.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_ci.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight_selection.py
  - src/shared/packages/pyforge-steward/tests/unit/test_ci_status.py
  - docsite/tools/export_ci_surfaces_tile_env.py
  - docsite/tools/assemble_pages.py
  - src/platform/config/flags.json
  - src/platform/config/flag-overlays.json
  - docs/governance/flag-inventory/pyforge-steward.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** After Story 102.1 the Pages workflow still has the shape of the retired console's: a `build` job that
only runs on `main`, a `deploy` job that deploys every green build, and a separate PR-time twin, `docsite-check.yml`
(522 runs since 2026-09-13), with its own copy of the path filter that drifts from the deploy workflow's. A scheduled
refresh of the fleet board and guild status (operator ruling 2026-10-13: per deploy and every six hours) would deploy
six times a day whether the fleet moved or not. BMAD-METHOD's `docs.yaml` has the shape the operator asked for on
2026-09-20 and ruled on 2026-10-13: build on `pull_request` and `push`, deploy on `main` only.

**Approach:** One workflow, two jobs, one filter, one skip.

- **The `build` job** runs on `pull_request` and on `push` to `main`, with the same twelve `paths:` on both triggers
  (Story 102.1's list, one copy), on `workflow_dispatch`, and on one `schedule` entry: six-hourly (`23 */6 * * *`
  or any slot the implementer settles on), replacing 102.1's weekly cron, since six-hourly subsumes it. The job runs
  `pixi run --frozen -e site pages-check` and then `pixi run --frozen -e site docs-site-validate` (the two steps
  `docsite-check.yml` ran, so the fold loses nothing), writes `build.json` into the built site's root, and uploads the
  built site: through `actions/upload-pages-artifact@v5` when the event is not `pull_request`, and as a plain
  artifact `pages-site` (`actions/upload-artifact@v7`, 14-day retention) when it is, so a reviewer downloads the
  reviewed bytes. Concurrency `pages-build-${{ github.ref }}` with `cancel-in-progress: true`; `timeout-minutes: 20`
  (docsite-check's today).
- **`build.json` and the hash.** A new module `src/shared/packages/pyforge-steward/src/pyforge/steward/pages.py`
  holds the pure functions: `tree_hash(root, exclude=...)` (sha256 over sorted relative paths and file bytes of the
  built tree, with `build.json` itself excluded and, once herald's M3 footer exists, the built-from footer excluded by
  a documented list), `build_json(tree_hash, built_from, run_id, built_at)`, and `decide_deploy(local, live_text,
  flag_on) -> bool` (`live_text` absent, unreadable, not JSON or without `tree_hash` reads as changed; flag off reads
  as changed). A repo script `scripts/pages_build_stamp.py` (a `scripts/` reader, as `export_ci_surfaces_tile_env.py`
  is for herald's flag) runs in the Guild env from the build job: it reads `pyforge.steward.pages_duty` through
  `pyforge.core.flags.read_boolean` (Story 75.1's shape), writes `build.json`, reads the live
  `${{ steps.pages.outputs.base_url }}/build.json` with one `curl` (a subprocess, AD-1; any failure reads as
  changed), and prints `tree_hash=…` and `changed=true|false` to `GITHUB_OUTPUT`. The hash must be stable: the story
  builds the same tree twice and compares; a file that differs between two builds of one tree is named and excluded
  in `pages.py`'s list with its reason, never silently.
- **The `deploy` job** runs only when `github.event_name != 'pull_request' && needs.build.outputs.changed == 'true'`,
  conjoined with its CAP-166 fragment (the fragment stays in front; Story 99.2's rule); `environment: github-pages`;
  `actions/deploy-pages@v5`; concurrency `pages` with `cancel-in-progress: false`; `timeout-minutes: 15`. A
  scheduled run whose fleet did not move therefore costs one build and no deploy.
- **The fold.** `.github/workflows/docsite-check.yml` is deleted. `scripts/pixi_version_registry.py` drops the
  `docsite-check.yml setup-pixi` site. `tests/unit/test_preflight_selection.py`'s oracle for the `pages-check` lane
  moves from `docsite-check.yml` to `pages.yml` (Story 71.2's test reads the live workflows; the three validators it
  names still run under the new file's `paths:`).
- **The registry.** `docs/governance/ci-surfaces.yaml`: the `dashboard` row is renamed `pages` with `switch:
  PAUSE_PAGES` and its `stuck_rules` kept (`deploy_waiting_hours: 24`, `consecutive_cancelled_runs: 5` — the
  2026-10-06 incident's two rules); `dashboard.build` and `dashboard.deploy` are renamed `pages.build` and
  `pages.deploy`; `docsite-check` and `docsite-check.check` become `state: retired` with `retired_on: <landing
  date>` (Story 99.7's convention for a deleted workflow). The fragments in `pages.yml` read `vars.PAUSE_PAGES`;
  `python scripts/ci_surface_gates.py --render` writes them and `--check` exits 0. `ci.py`'s stuck reader needs no
  change: it reads `stuck_rules` by row. If a live `PAUSE_DASHBOARD` variable exists at landing, `--check --live`
  reports it as unregistered; the operator moves or deletes it through `steward ci pause|resume --yes` (the Spec's
  open question), never this story's code.
- **The flag.** `pyforge.steward.pages_duty` lands in `src/platform/config/flags.json` (`defaultVariant` off,
  metadata owner `steward`, story this key, created the landing date) and in `flag-overlays.json` (dev on, staging and
  production off); `docs/governance/flag-inventory/pyforge-steward.md` gains its row. `pages.py` is its reader
  (`flag-gate-check` counts readers under `src/` and `scripts/`). Off: `decide_deploy` returns changed, so the deploy
  job deploys every green build as today. A two-state test runs `decide_deploy` through
  `pyforge.testing_kit.flags.flag_states("pyforge.steward.pages_duty")`.

Ledger key: `102-2-one-pages-workflow-in-upstream-shape-builds-on-every-change-and-deploys-only-what-changed`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / S-102.1.

### Living CAP citations

- **`spec-pyforge-steward` CAP-168** (FR-41): the upstream shape, the fold, the skip, the registry rename, the flag.
  Extends CAP-166 (the `pages` row keeps the stuck rules; `ci status` reads the new names); works with CAP-159 (the
  lane oracle moves with the file).
- **AD-4 as amended 2026-10-14**: the hash compare is the diff-before-mutate gate; zero deploys when nothing changed.
  **AD-1**: `curl`, `pixi` and `gh` by subprocess; no second build. **AD-8**: the stamp script owns its exit code
  (0 on a decision, 1 on a hashing failure), the duty boundary is untouched here.
- **canopy:AD-11** (one flag tree); `feature-flag-governance:CAP-1` (the flag rule), `:CAP-4` (the two-state test).
- **herald herald:AD-21**: one `deploy-pages` caller; `spec-pyforge-herald:CAP-49` (the PR gate) is realized by the fold,
  the herald SPEC's wording is the coordinator's.
- **Origin.** The Dream's 2026-10-13 (the Pages duct) entry; the herald Dream's M2; brainstorm-intent § M2 and
  § Constraints; design thinking P-A and Key Feature 6 (the hash excludes the footer); operator rulings 2026-10-13.

## Acceptance Criteria

- **AC1 — The shape.** A test parses `pages.yml`: `on.pull_request.paths` and `on.push.paths` are the same twelve
  entries; `on.schedule` holds one six-hourly cron and no weekly one; the `build` job has no `if:` beyond its CAP-166
  fragment; the `deploy` job's `if:` conjoins the fragment, `github.event_name != 'pull_request'` and
  `needs.build.outputs.changed == 'true'`; `build` has `cancel-in-progress: true`, `deploy` has `false`; both carry
  `timeout-minutes`.
- **AC2 — The PR artifact.** On a `pull_request` event the `build` job's `upload-artifact` step (`pages-site`) runs
  and `upload-pages-artifact` does not; on `push` and `schedule` the reverse (asserted on the YAML's step `if:`
  expressions by a test, and once by a dispatched PR run recorded here).
- **AC3 — The hash.** `tree_hash` over a fixture tree is byte-stable across two calls and unchanged when `build.json`
  or a footer-listed file changes; `build_json` carries `tree_hash`, `built_from`, `run_id`, `built_at` (UTC);
  `decide_deploy(h, json_with(h), True)` is `False`, with a differing hash `True`, with `None`, non-JSON or a missing
  key `True`, and with `flag_on=False` always `True`. Two consecutive `pages-check` builds of one tree yield equal
  hashes (recorded in this spec), or the differing files are named in the exclusion list with their reasons.
- **AC4 — The stamp script.** `scripts/pages_build_stamp.py --root <site> --live-url <url>` writes `<site>/build.json`,
  prints `tree_hash=` and `changed=` lines, and with a fake `curl` returning 404 prints `changed=true`; it never
  writes anywhere but `<site>/build.json`; exit 0 on a decision, 1 when the root is not a directory.
- **AC5 — The fold.** `.github/workflows/docsite-check.yml` is absent; `pixi-version-check` exits 0 with no
  `docsite-check.yml` site; `test_preflight_selection.py` reads `pages.yml` as the `pages-check` oracle and is green;
  the `docs-site-validate` step runs in `pages.yml`'s `build` job.
- **AC6 — The registry.** `ci-surfaces.yaml` holds rows `pages` (`switch: PAUSE_PAGES`, the two `stuck_rules`),
  `pages.build`, `pages.deploy`, and `docsite-check` and `docsite-check.check` with `state: retired` and
  `retired_on`; no row names `.github/workflows/dashboard.yml` or `docsite-check.yml` as live; `python
  scripts/ci_surface_gates.py --check` exits 0; `test_ci_status.py` gains a case where the `pages` row with five
  consecutive cancelled runs reads `stuck`.
- **AC7 — The flag.** The tree and the overlay hold `pyforge.steward.pages_duty` (off; dev on); the inventory row
  exists; `src/shared/packages/pyforge-steward/tests/unit/test_pages_flag_states.py` runs `decide_deploy` with
  `flag_states("pyforge.steward.pages_duty")` in both states; `pixi run --frozen -e pyforge-guild flag-gate-check`
  exits 0 (no orphan: `pages.py` reads the key).
- **AC8 — Nothing deploys twice.** One dispatched `workflow_dispatch` run after landing with the flag on in the
  deploying environment, then a second with no tree change: the second's `deploy` job is skipped
  (`changed=false`), recorded here with both run ids. (With the flag off in production at landing, the record says
  so and the skip is proven on the fixture, AC3.)
- **AC9 — The gates.** `pixi run --frozen -e pyforge-steward pyforge-steward-test`, `flag-gate-check`,
  `detectors-ci` and `spec-surface-check` exit 0; the memlog reconciles every governed path (this Spec; the
  `docs/governance/` rows are this Spec's surface) before one scoped stamp.

## Boundaries & Constraints

**Always:**
- One copy of the path filter, on both triggers. One `deploy-pages` caller.
- The CAP-166 fragment stays the first term of every job's `if:`; the skip condition is conjoined after it.
- The hash compare reads the live site; it writes no repository variable and no cache (CAP-166's one write path).
- The stamp script and `pages.py` are stdlib plus `pyforge.core.flags`; no herald import, no docsite import.
- Every file named here that another Spec governs (`flags.json`, `flag-overlays.json` — the Guild's; the flag
  inventory) is reconciled on that Spec's memlog and stamped scoped.

**Never:**
- Do not add the `pages` duty verbs (102.3), the artifact download (102.4), the release asset or the host-env drop
  (102.5).
- Do not edit `docsite/**` or `docs-site/**`: the build steps are herald's tasks, called by name.
- Do not set, move or delete a repository variable from any workflow step or test.
- Do not weaken `stuck_rules` or drop a `review_by`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| PR touching docs | `pull_request` | build, `pages-site` artifact, no deploy | — |
| merge to main, tree changed | `push`, live hash differs | build, deploy | — |
| merge to main, docs unchanged in output | `push`, live hash equal | build, deploy skipped | — |
| six-hourly, fleet unchanged | `schedule`, hash equal | build, deploy skipped | — |
| six-hourly, fleet moved | `schedule`, hash differs | build, deploy | — |
| live site unreachable | `curl` non-zero / 404 | `changed=true`, deploy | logged, not an error |
| first deploy after landing | no `build.json` live | `changed=true`, deploy | — |
| flag off | tree default | `changed=true` always | — |
| `PAUSE_PAGES=true` | registry `paused` | both jobs skip; dispatch still runs | — |
| non-deterministic file | two builds differ | file named in the exclusion list with reason | the story does not land silent |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-168 (FR-41), minted 2026-10-14.
- Architecture: AD-4 amended 2026-10-14; AD-1, AD-8; canopy:AD-11.
- Dream: `docs/dreams/pyforge-steward.md` § Realization log, the 2026-10-13 (the Pages duct) entry.
- Epic: Epic 102, Story 102.2.
- Ledger key: `102-2-one-pages-workflow-in-upstream-shape-builds-on-every-change-and-deploys-only-what-changed`.
- Ledger status at mint: `backlog`.
- Deps: S-102.1 (the renamed file and its filter). `marshal factory dispatch` stamps `baseline_revision` with the launch
  commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."102"`.
- Flag: `pyforge.steward.pages_duty` (`feature-flag-governance:CAP-1`), minted here.

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** S-102.1 • **FR/AD:** spec-pyforge-steward CAP-168 (FR-41), extending CAP-166, with CAP-159; AD-4 (amended 2026-10-14), AD-1, AD-8; canopy:AD-11 • flag: `pyforge.steward.pages_duty` (new)

**Given** Story 102.1's `pages.yml` deploying every green build on `main` and a separate `docsite-check.yml` PR twin
**When** the workflow takes `docs.yaml`'s shape — `build` on `pull_request` and `push` with one filter and a six-hourly
schedule, `deploy` on `main` only when the built tree's hash differs from the live `build.json` — `docsite-check.yml`
folds in, and the registry rows become `pages`, `pages.build`, `pages.deploy` with `PAUSE_PAGES` and the stuck rules
**Then** a PR run uploads `pages-site` and never deploys, a scheduled run with an unchanged tree skips the deploy, the
fixture tests of the hash and the decision pass in both flag states, `ci_surface_gates.py --check`, `pixi-version-check`
and `flag-gate-check` exit 0
**And** `pyforge-steward-test` is green and the Spec memlog reconciles every governed path before one scoped stamp

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`;
  MRS-GATE-010 binding; it runs `src/shared/packages/pyforge-steward/tests/unit/test_pages.py` (AC3, AC4) and
  `src/shared/packages/pyforge-steward/tests/unit/test_pages_flag_states.py`, which runs the key
  `pyforge.steward.pages_duty` in both states with `pyforge.testing_kit.flags.flag_states` (AC7), the workflow shape
  test (AC1, AC2), `test_preflight_selection.py` (AC5) and `test_ci_status.py` (AC6)).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_pages.py src/shared/packages/pyforge-steward/tests/unit/test_pages_flag_states.py -q` — expected: pass.
- `python scripts/ci_surface_gates.py --check` — expected: exit 0 (AC6).
- `pixi run --frozen -e pyforge-guild pixi-version-check` — expected: exit 0 (AC5).
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0 (AC7).
- `pixi run --frozen -e site pages-check` twice on one tree, then `python scripts/pages_build_stamp.py --root docs-site/build/site --live-url https://invalid.invalid` — expected: equal `tree_hash=` lines, `changed=true` (AC3, AC4).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

**Operator, after landing (AC8):**
- `gh workflow run pages.yml --ref main` twice with no tree change between; the second run's `deploy` job is skipped.
  Both run ids go into this spec's Auto Run Result.

## Named, not fixed here

- The six-hourly cron slot; the PR artifact's retention days; the `timeout-minutes` values (20 and 15 are the defaults
  this spec names).
- The exclusion list's first entries (herald's M3 footer does not exist yet; the list may start empty).
- `retired_on` is the landing date.

## Auto Run Result

Status: in-review  
Verification: `python scripts/spec_surface_reconcile.py` OK; `python scripts/ci_surface_gates.py --check` OK; `pixi-version-check` OK; `flag-gate-check` OK; steward pages/preflight/ci_status meta tests green; full `pyforge-steward-test` green after trigger-map and invariants fixes (2026-10-14 run).  
AC8 (live double `workflow_dispatch` with flag on in production): deferred — `pyforge.steward.pages_duty` remains off in production at landing; skip behaviour proven on fixtures (AC3/AC7). Operator records both run ids when production overlay flips.  
Governance: memlog reconciles on `spec-pyforge-steward`, `docs/governance/spec-feature-flag-governance`, `spec-pyforge-herald` (co-governor tests); scoped stamp on `pyforge-steward/spec-pyforge-steward`. Herald scoped stamp blocked by pre-existing presentation drift vs baseline (warn-only in `spec-surface-check`, not introduced by this story).

## Spec Change Log

- 2026-10-14: specced at mint from Epic 102's Story 102.2 text, `spec-pyforge-steward` CAP-168 and the live
  `dashboard.yml` / `docsite-check.yml`. The live-site hash read (not a repository variable, not a cache) and the
  rename-in-place of the `dashboard*` rows are the 2026-10-14 decisions on the Spec's memlog. The implementing session
  reads the landed Story 102.1 file first and follows it where it differs from the shape quoted here.
