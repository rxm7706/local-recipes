---
title: '102.3: `steward pages build|deploy|status` replaces `deploy dashboard` and `deploy status`'
type: 'feature'
created: '2026-10-14'
status: 'done'
baseline_revision: '8ef404d388d1bdafac6aa0d96a8f626f97cad47a'
flag:
  key: pyforge.steward.pages_duty                 # Story 102.2's; this story adds the duty behind it
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through Epic 76's overlay
  scope: global                                   # v1 is global only
  fallback: 'every `pages` verb refuses naming the flag with the documented refusal code; nothing else reads it here'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-102-2-one-pages-workflow-in-upstream-shape-builds-on-every-change-and-deploys-only-what-changed.md
  - docs/dreams/pyforge-steward.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/ci.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/pages.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/interfaces.py
  - src/shared/packages/pyforge-steward/tests/unit/test_cli.py
  - src/shared/packages/pyforge-steward/tests/unit/test_restore_duty.py
  - src/shared/packages/pyforge-steward/tests/unit/test_deploy_status.py
  - src/shared/packages/pyforge-steward/tests/unit/test_deploy_reconcile.py
  - src/shared/packages/pyforge-steward/tests/unit/test_deploy_static.py
  - .github/workflows/pages.yml
  - .github/workflows/kedro-viz-publish.yml
  - docs/governance/ci-surfaces.yaml
  - docs/reference/github-workflows.md
  - docs/dashboard/README.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `steward deploy dashboard` (FR-8..FR-10: build, diff, commit and push `docs/dashboard/`) and `steward
deploy status` (FR-11: the last commit that touched `docs/dashboard/`) describe a deploy that no longer exists. The
generator they wrapped was retired on 2026-08-25 (AD-4's 2026-08-26 amendment left `build_dashboard` a no-op), the
Pages artifact is built and deployed by the workflow, and the verbs' one remaining caller, `kedro-viz-publish.yml`,
commits a `github-actions[bot]` export to `main` — the pattern the operator ruled out on 2026-10-13 ("no bot commits
on `main`"); atlas Story 30.1 turns that producer into an artifact upload. The duct needs a duty that speaks to the
workflow, not to a branch.

**Approach:** A `pages` duty with three verbs, each a subprocess conductor (AD-1), on Story 102.2's `pages.py`.

- **`steward pages build`** runs `pixi run --frozen -e site pages-check` from the repo root by subprocess, then
  `pages.tree_hash` over `docs-site/build/site`, and reports `pages build: pages-check exit <n>; tree <hash>`;
  `ok` follows the child's exit. `--json` prints `{exit, tree_hash, root}`. It never writes `build.json` itself (the
  stamp script does, in CI); `--stamp` runs the stamp as the workflow would, for a local rehearsal.
- **`steward pages deploy`** runs `gh workflow run pages.yml --ref main` (plus `-f` inputs if the workflow declares
  any), then `gh run list --workflow pages.yml --limit 1 --json databaseId,url,status,event` to name the run it
  started, and reports `pages deploy: run <id> <url> (<status>)`. `--dry-run` prints the two argv lines and runs
  nothing (the duty's precedent in `deploy dashboard --dry-run`); `--wait` adds `gh run watch <id> --exit-status` and
  reports the deployment's `page_url` from the run's job summary. `ok` is false when `gh` exits non-zero, the summary
  naming the argv and the child's stderr (the `DeployDuty` shape).
- **`steward pages status`** prints three lines: the live root — `curl -sI <SITE_URL>` for `last-modified` and
  `curl -fsS <SITE_URL>/build.json` for `tree_hash` and `built_from`; the last run — `gh run list --workflow
  pages.yml --limit 1 --json databaseId,conclusion,status,event,createdAt,url`; the registry verdict for the `pages`
  surface — `ci.py`'s status reader for that one row (a thin import inside this package; it refuses the same way `ci
  status` does without an authenticated `gh`, and then the line reads `registry verdict: unavailable (<reason>)`,
  `ok` still true: the two live lines are the duty's own facts). `<SITE_URL>` comes from `--site-url`, else `gh api
  repos/{owner}/{repo}/pages --jq .html_url`. `--json` emits the three blocks.
- **The flag.** Every verb reads `pyforge.steward.pages_duty` through `pyforge.core.flags.read_boolean` first and,
  off, refuses with `EXIT_PAGES_REFUSAL = 3` (the refusal domain `ci.py` uses) naming the flag, before any subprocess
  call (a fake-subprocess test asserts no call).
- **The retirement.** `deploy`'s `_DEPLOY_VERBS` becomes `("perimeter", "static")`; `_run_dashboard`,
  `_run_status`, `build_dashboard`, `dashboard_diff`, `commit_and_push_dashboard`, `_push_pending_commit_if_ahead`,
  `last_deploy_commit`, `DeployRecord` and the `dashboard` and `status` subparsers are deleted (AD-5's 2026-08-09
  rule: a retirement that leaves the old path importable is a deprecation, not a removal), and so are their tests
  `test_deploy_build.py`, `test_deploy_dry_run.py`, `test_deploy_reconcile.py`, `test_deploy_status.py` and
  `test_deploy_ledger_refusal.py` (the ledger-refusal rule guarded the committing verb; nothing commits now).
  `deploy static` stays: it writes `docs/dashboard/<board>/index.html` and its docstring and help now say the file
  lands through a pull request like any tracked file (no verb pushes). `deploy perimeter` is untouched. `cli.py`'s
  `DUTIES` gains `pages` after `ci` (30 entries); the count assertions in `tests/unit/test_cli.py` and
  `tests/unit/test_restore_duty.py` move to 30, `restore` stays the fourteenth slot; `steward --help` lists `pages`.
- **The callers.** `kedro-viz-publish.yml` is atlas's file and is not edited here: atlas Story 30.1 replaces its
  `steward deploy dashboard` step with an artifact upload. If 30.1 has not landed when this story does, the retired
  verb's last call sits in a workflow that is `paused-manually` since 2026-08-24 (registry row, `review_by`
  2026-11-01); the story records that as a deferred-work row for atlas (`DW-steward-102-3-1`, closed by 30.1) and
  leaves the file alone. Every tracked doc that names the verbs as current — `docs/reference/github-workflows.md`,
  `docs/dashboard/README.md`, `scripts/fleet_scan.py`'s and `pyforge-atlas/tools/normalize_viz_build.py`'s comments,
  `fresh_clone.py`'s help text — names `steward pages` instead; each is a co-governor reconcile on its Spec's memlog.
  The PRD's SM-2 (`steward deploy dashboard` replaces the hand-run generator) is history and is recorded so in the
  PRD's 2026-10-14 currency section (this mint).

Ledger key: `102-3-steward-pages-build-deploy-status-replaces-deploy-dashboard-and-deploy-status`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / S-102.2.

### Living CAP citations

- **`spec-pyforge-steward` CAP-168** (FR-41): the duty, its three verbs, the retirement of `deploy dashboard` and
  `deploy status`. Extends CAP-2 (the deploy duty as FR-8..FR-11 read it) and CAP-166 (the `status` verb reads the
  `pages` row's verdict through the same reader).
- **AD-1**: `pixi`, `gh` and `curl` by subprocess; no second status reader (the registry verdict is `ci.py`'s). **AD-4
  as amended 2026-10-14**: `pages deploy` triggers the one workflow; the workflow's hash compare is the no-diff gate.
  **AD-7**: one duty module, `DUTIES` grows by one, the count assertions move. **AD-8**: `main()` alone projects the
  exit; `EXIT_PAGES_REFUSAL` is documented beside `EXIT_CI_REFUSAL`; the duty never calls `sys.exit`.
- **AD-5 (2026-08-09)**: the retired path is deleted, not deprecated.
- **Flag:** `pyforge.steward.pages_duty` (Story 102.2's; `feature-flag-governance:CAP-1`, `:CAP-4`).
- **Origin.** The Dream's 2026-10-13 (the Pages duct) entry ("a `steward pages build|deploy|status` duty replaces
  `deploy dashboard` and `deploy status`"); brainstorm-intent § M2; design thinking § Success Metrics (M2: zero
  `github-actions[bot]` commits on `main` for Pages).

## Acceptance Criteria

- **AC1 — Build.** With a fake subprocess whose `pages-check` exits 0 and a fixture built tree, `steward pages build`
  reports `ok=True`, the recorded argv is exactly `pixi run --frozen -e site pages-check`, and the summary carries the
  tree hash; with the fake exiting 2, `ok=False` and the summary names the exit.
- **AC2 — Deploy.** `steward pages deploy --dry-run` prints the `gh workflow run pages.yml --ref main` and `gh run
  list …` argv and the fake records no call; without `--dry-run` the fake records both in that order and the summary
  names the run id and url from the fixture JSON; a `gh` exit 1 yields `ok=False` with the argv and stderr in the
  summary; `--wait` adds `gh run watch <id> --exit-status`.
- **AC3 — Status.** With fake `curl` and `gh` fixtures, `steward pages status` prints the live root's
  `last-modified`, `tree_hash` and `built_from`, the last run's id, event, conclusion and url, and the `pages` row's
  verdict; with the `ci` reader refusing (unauthenticated fixture), the third line reads `unavailable (<reason>)` and
  `ok` stays true; `--json` emits the three blocks; `--site-url` overrides the `gh api … pages` lookup.
- **AC4 — Flag.** With `pyforge.steward.pages_duty` off, each verb exits `EXIT_PAGES_REFUSAL` (3) naming the flag and
  the fake records no subprocess; `src/shared/packages/pyforge-steward/tests/unit/test_pages_duty_flag_states.py`
  runs `build --dry-run` through `flag_states("pyforge.steward.pages_duty")`: on, the argv is recorded; off, the
  refusal.
- **AC5 — Retirement.** `steward deploy dashboard` and `steward deploy status` are usage errors (`EXIT_USAGE`,
  argparse); `grep -rn "build_dashboard\|dashboard_diff\|commit_and_push_dashboard\|last_deploy_commit"
  src/shared/packages/pyforge-steward/src` returns nothing; the five retired test modules are gone; `deploy static`'s
  tests pass and its help says the file lands through a pull request; `deploy perimeter` tests pass unchanged.
- **AC6 — Duty count.** `len(DUTIES) == 30` in both assertions, `DUTIES.index("restore") == 13`, `pages` follows
  `ci`; `steward --help` lists `pages`; `steward pages` with no verb returns `ok=True` naming the three verbs
  (AD-7's degrade).
- **AC7 — Callers.** `git grep -n "steward deploy dashboard\|steward deploy status"` over tracked files returns only
  dated log entries, `kedro-viz-publish.yml` (atlas's, until 30.1) and this chain's planning artifacts; if
  `kedro-viz-publish.yml` still calls the verb, `DW-steward-102-3-1` is recorded open with atlas 30.1 as its closer.
- **AC8 — The gates.** `pixi run --frozen -e pyforge-steward pyforge-steward-test`, `flag-gate-check`,
  `lint-types`, `detectors-ci` and `spec-surface-check` exit 0; no test calls a live `gh`, `curl` or `pixi`.

## Boundaries & Constraints

**Always:**
- Every outward effect (`gh workflow run`) is an explicit, user-triggered verb; `--dry-run` prints and does nothing.
- `status` reads; it never triggers a run or writes a variable.
- The registry verdict is `ci.py`'s; `pages.py` does not re-derive `stuck`, `drift` or `overdue`.
- The retirement deletes; nothing of the old path stays importable.
- The exit-code constants are documented in `cli.py`'s table beside the `ci` duty's.

**Never:**
- Do not edit `kedro-viz-publish.yml` (atlas's) or `docsite/**` / `docs-site/**` (herald's).
- Do not add a `git commit` or `git push` to any `pages` verb; no verb writes to `main`.
- Do not import `pyforge.herald`, `pyforge.atlas` or docsite code.
- Do not call a live `gh`, `curl` or `pixi` from a test.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| build, green | fake `pages-check` exit 0 | `ok=True`, tree hash in summary | — |
| build, red | fake exit 2 | `ok=False`, exit named | `EXIT_FAILED` from `main()` |
| deploy dry run | `--dry-run` | two argv lines, no call | — |
| deploy, gh fails | `gh workflow run` exit 1 | `ok=False`, argv and stderr | `EXIT_FAILED` |
| deploy, wait | `--wait` | `gh run watch <id> --exit-status` recorded; page url reported | child exit propagates to `ok` |
| status, live site down | `curl` exit 22 | line 1 reads `unreachable`; lines 2–3 still print | `ok=True` (a fact) |
| status, ci reader refuses | `ci` reader refuses (flag off, rate limit); `gh run list` reads | line 3 `unavailable (<reason>)` | `ok=True` |
| status, gh unauthenticated | every `gh` call fails | line 1 `unavailable (…)`, line 2 names the `gh run list` error, line 3 `unavailable (…)` | `ok=False`, exit 1 (the run list is the duty's own fact; corrected 2026-10-15) |
| flag off | tree default | refusal naming the flag before any call | exit 3 |
| retired verb | `steward deploy dashboard` | argparse usage error | exit 2 |
| bare duty | `steward pages` | names the three verbs | exit 0 |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-168 (FR-41), minted 2026-10-14; extends CAP-2 and CAP-166.
- Architecture: AD-1, AD-4 (amended 2026-10-14), AD-5 (2026-08-09 rule), AD-7, AD-8.
- Dream: `docs/dreams/pyforge-steward.md` § Realization log, the 2026-10-13 (the Pages duct) entry.
- Epic: Epic 102, Story 102.3.
- Ledger key: `102-3-steward-pages-build-deploy-status-replaces-deploy-dashboard-and-deploy-status`.
- Ledger status at mint: `backlog`.
- Deps: S-102.2 (`pages.py`, the flag, the workflow the verbs speak to). Ordering noted, not a gate: atlas Story 30.1
  (the producer stops calling the retired verb). `marshal factory dispatch` stamps `baseline_revision` with the launch
  commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."102"`.
- Flag: `pyforge.steward.pages_duty` (Story 102.2's).

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** S-102.2 • **FR/AD:** spec-pyforge-steward CAP-168 (FR-41), extending CAP-2 and CAP-166; AD-1, AD-4 (amended 2026-10-14), AD-7, AD-8 • flag: `pyforge.steward.pages_duty` (Story 102.2's)

**Given** `steward deploy dashboard|status` describing a branch deploy that retired on 2026-08-25, with one caller
that commits a bot export to `main`
**When** a `pages` duty lands — `build` runs `pages-check` by subprocess, `deploy` runs `gh workflow run pages.yml` and
names the run, `status` prints the live root, the last run and the `pages` registry verdict — behind
`pyforge.steward.pages_duty`, and `deploy dashboard`, `deploy status` and their git plumbing are deleted
**Then** the fake-subprocess fixtures assert each verb's argv and refusals, `DUTIES` has 30 entries with both count
assertions moved, the retired verbs are usage errors, and no `pages` verb commits or pushes
**And** `pyforge-steward-test`, `flag-gate-check` and `lint-types` are green, and no tracked file outside dated logs and
atlas's producer calls the retired verbs

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`;
  MRS-GATE-010 binding; it runs `src/shared/packages/pyforge-steward/tests/unit/test_pages_duty.py` (AC1–AC3, AC5,
  AC6), `src/shared/packages/pyforge-steward/tests/unit/test_pages_duty_flag_states.py`, which runs the key
  `pyforge.steward.pages_duty` in both states with `pyforge.testing_kit.flags.flag_states` (AC4),
  `src/shared/packages/pyforge-steward/tests/unit/test_cli.py` and
  `src/shared/packages/pyforge-steward/tests/unit/test_restore_duty.py` (AC6)).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_pages_duty.py src/shared/packages/pyforge-steward/tests/unit/test_pages_duty_flag_states.py src/shared/packages/pyforge-steward/tests/unit/test_cli.py src/shared/packages/pyforge-steward/tests/unit/test_restore_duty.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `git grep -n "steward deploy dashboard\|steward deploy status" -- ':(exclude)_bmad-output' ':(exclude)docs/dreams' ':(exclude).claude/memory'` — expected: only `kedro-viz-publish.yml` (until atlas 30.1) (AC7).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

**Operator, after landing (an authenticated read and one triggered run):**
- `pixi run --frozen -e pyforge-guild pyforge steward pages status`, then `pages deploy --wait` once, then `status`
  again — expected: the second `status` names the run and a newer `built_from`; recorded in this spec.

## Verification run (2026-10-15)

- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_pages_duty.py src/shared/packages/pyforge-steward/tests/unit/test_pages_duty_flag_states.py src/shared/packages/pyforge-steward/tests/unit/test_cli.py src/shared/packages/pyforge-steward/tests/unit/test_restore_duty.py -q`
  — exit 0, 76 passed (AC1–AC6; every verb on a fake subprocess, no live `gh`, `curl` or `pixi`).
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — exit 0, 2722 passed, 2 skipped (no xdist in the env; serial).
- `grep -rn "build_dashboard\|dashboard_diff\|commit_and_push_dashboard\|last_deploy_commit" src/shared/packages/pyforge-steward/src`
  — exit 1 (nothing). `git grep -n "steward deploy dashboard\|steward deploy status" -- ':(exclude)_bmad-output'
  ':(exclude)docs/dreams' ':(exclude).claude/memory'` — only herald's deck exports under
  `presentations/pyforge-steward/` (two of them dated Marp sources) and the two tests that assert the string's
  absence (atlas `test_viz_export_artifact.py`, steward `test_fresh_clone_class_path.py`); `kedro-viz-publish.yml`
  no longer calls the verb (atlas 30.1 landed), so `DW-steward-102-3-1` is not needed (AC7).
- `pixi run --frozen -e pyforge-guild flag-gate-check` — exit 0. `pixi run --frozen -e pyforge-guild lint-types` — exit 0.
  `python scripts/ci_surface_gates.py --check` — exit 0. `pixi run --frozen -e site docs-site-validate` — exit 0.
- The real CLI: `steward pages` names the three verbs (exit 0); `pages build --dry-run` and `pages deploy --dry-run
  --wait` print their argv (exit 0); `steward deploy dashboard` — exit 2 (argparse). `PYFORGE_STATUS_PAGES=1 steward
  pages build` — exit 0: it wrote `docsite/content/fleet-status.json` from the eight tracked ledgers (1,473 stories),
  `pages-check` passed with herald's board rendering from it (bar widths 98/99/94/99/98/100/95/100, 31 attention
  keys), tree `c98000f029a6…`. The workflow's two commands (`sprint-ledger-query -- --format json --output …`, then
  `scripts/pages_fleet_status.py --generated-at "$(git log -1 --format=%cI HEAD)"`) rehearsed locally give the same
  stations, read cleanly by herald's `status_pages.load_fleet_status`.
- Not run here: the memlog reconciles, the scoped stamps, `detectors-ci` and `pr-preflight` (the coordinating session
  runs them for the branch); the operator's authenticated `status` / `deploy --wait` / `status` after landing.

## Named, not fixed here

- The `--json` block shapes (no external consumer yet; freeze a schema only when one appears, as `ci-status-schema.json`
  did).
- Whether `pages deploy` accepts `--ref <branch>` for a rehearsal on a non-`main` ref (the workflow deploys from `main`
  only; a rehearsal would build and skip).

## Spec Change Log

- 2026-10-15 (the Pages one-PR endgame, pass 2a): the Verification command's two package-relative test paths
  (`tests/unit/test_cli.py`, `tests/unit/test_restore_duty.py`) are written from the repo root. At `done`,
  `flag_gate_check.py` reads every test file a flagged spec's Verification names from the repo root, and the bare
  paths failed it with `flag-test-file-missing` (found by herald 43.7's independent review, part B, simulating the
  promotion). No AC, test or command changes.
- 2026-10-14: specced at mint from Epic 102's Story 102.3 text, `spec-pyforge-steward` CAP-168 and the live `deploy.py`
  / `cli.py` (`DUTIES` 29, `restore` at index 13). The implementing session reads the landed Story 102.2 `pages.py`
  first and follows it where it differs from the shape quoted here.
- 2026-10-15 (implemented, in review; one branch with the rest of the Pages redesign chain). Where the landed code
  differs from the text above, the code is the contract:
  - **`DUTIES` is 31, not 30.** `preflight` (Story 103.6) landed after the mint; `pages` sits after `ci`, before
    `preflight` (still last). Every count assertion moved to 31 (`test_cli.py`, `test_restore_duty.py`, and the two
    the mint did not name, `test_estate.py` and `test_preflight_verify_deferred.py`); `restore` stays index 13.
  - **The duty module is `pages_duty.py`**, beside 102.2's pure `pages.py` (which `scripts/pages_build_stamp.py`
    imports and so stays free of the duty's imports). `EXIT_PAGES_REFUSAL = 3` lives there and is documented in
    `cli.py` beside `ci.EXIT_CI_REFUSAL`.
  - **`build` writes the fleet board's input first** (in-process: the ledger engine's `--format json` export, without
    the live `marshal watch` call, reshaped by `pages.fleet_status_document`), so the one recorded subprocess is still
    exactly `pixi run --frozen -e site pages-check` (AC1). It gained `--dry-run` (AC4's `build --dry-run`: prints the
    argv, runs and writes nothing) and `--site-url` for `--stamp`, which runs `scripts/pages_build_stamp.py` through
    the Guild env as the workflow does.
  - **`deploy` lists only dispatched runs** (`gh run list … --event workflow_dispatch … --json
    databaseId,url,status,event,createdAt`) and looks for the run it started up to five times, three seconds apart,
    until one created at or after the dispatch is listed (else it names the newest with a note): a bare `--limit 1`
    right after `gh workflow run` names the previous run. `--wait`'s page url is `gh api repos/{owner}/{repo}/pages
    --jq .html_url` (the url the deploy job's environment reports).
  - **`status`'s `ok`.** An unreachable site (`curl` exit or an HTTP status ≥ 400) and an unavailable registry
    verdict are facts (`ok` true); a `gh run list` that cannot be read is not (`ok` false, the line names the error).
    The registry verdict is `ci.run_status(…, json_out=True)`'s `pages` row; any refusal or failure of that reader
    reads `unavailable (<reason>)`.
  - **Closes the 102.2 gap herald 42.1's spec assigns to steward's deploy workflow.** 102.2 landed without the Guild
    step that writes `docsite/content/fleet-status.json`, and without the `PYFORGE_STATUS_PAGES` export. `pages.yml`
    now runs `docsite/tools/export_status_pages_env.py >> "$GITHUB_ENV"` with the other exports, and a step before
    `pages-check` runs `sprint-ledger-query -- --format json --output "$RUNNER_TEMP/sprint-ledger.json"` then
    `scripts/pages_fleet_status.py` (the same `pages.fleet_status_document` reshape) into the input, in the shape
    herald's reader documents (`stations` a list of `StationProgress` rows plus `total` and `epics`; `stories` rows
    with `story_id`, `station`, `epic_id`, `title`, `status`). The snapshot time is the built commit's
    (`git log -1 --format=%cI HEAD`), not the query's, so a scheduled build of an unmoved tree hashes the same and
    skips its deploy. `steward pages build` writes the same input locally. The station-tests trigger list gains
    `scripts/pages_fleet_status.py`.
  - **From the doctor 48.2 review; keeps Pages liveness honest when builds are identical.** `pages.decide_deploy` also
    deploys an identical tree when the live `build.json`'s `built_at` is more than 24 hours old
    (`LIVENESS_MAX_AGE`) and this build's commit differs from the live `built_from` (a full and an abbreviated SHA of
    one commit compare equal): at most one extra deploy a day, so an input commit that builds an identical site (once
    herald 43.5 drops the built-from footer from the hash) still moves the live `last-modified` doctor's liveness
    probe reads. Without `built_from` and `now` (102.2's call shape) the branch does not apply; a live document
    without a readable `built_at` never triggers it. `scripts/pages_build_stamp.py` passes both.
  - **Callers.** `kedro-viz-publish.yml` no longer calls the verb (atlas 30.1), so no deferred-work row is recorded.
    `docs/reference/github-workflows.md` (both rows), `docs/dashboard/README.md`, `scripts/fleet_scan.py`'s message and
    `normalize_viz_build.py`'s docstring name the Pages workflow and `steward pages`; `fresh_clone.py` already did.
    Left for their owners: herald's deck exports under `presentations/pyforge-steward/` and the dossier line in
    `docsite/content/dossier.yml` (herald's; this story may not edit `docsite/**`), and the generated
    `docs/reference/station-cheat-sheet.md` (doctor's generator; already stale before this story, no gate reads it).
  - **Retired-test references.** `test_deploy_static.py` asserted visibility through the deleted diff helper; it now
    asks `git status` directly. Docstrings in `test_provision_env.py`, `test_provision_verify.py`,
    `test_deploy_perimeter.py` and `test_deploy_static.py` that cited the deleted modules no longer do (no assertion
    changed in the perimeter tests).
  - **Found while running the steward suite:** herald 42.1's `test_status_pages_flag_states.py` hands the repo root to
    the herald build and was not declared in `test_station_tests_trigger_map.py`'s `ROOT_HANDOFF_INPUTS`; it is now
    (`docsite/**`, `presentations/**`, as `test_pages_artifact.py` is).
- 2026-10-15 (the independent review, `review-102-3`, verdict FAIL on four should-fix items; resolved here):
  - **S1 — a dispatch no longer redeploys an identical tree.** AD-4 as amended 2026-10-14 reads "an equal hash
    performs zero deploys" with no dispatch exception, so the code changes, not the contract. The gate renderer
    (`scripts/_ci_surface_gates_render.py`) gains a per-row `dispatch: pause-only` (schema
    `docs/governance/ci-surfaces.schema.json`): such a row renders `(dispatch || (pause switches)) && (inner)` where
    every other row keeps `dispatch || (pause switches && inner)` (the operator's escape hatch; the registry's
    `dispatch_ignores_pauses` convention). Only `pages.deploy` sets it. Its inner condition is now
    `github.event_name != 'pull_request' && github.ref == 'refs/heads/main' && needs.build.outputs.changed == 'true'`
    (the duplicated pause group 102.2 left inside it is gone), rendered by `python scripts/ci_surface_gates.py
    --render`, which is idempotent on every other workflow. `pages_duty.py`'s docstring, the workflow header and
    `docs/dashboard/README.md` say so. Tests: `tests/scripts/test_ci_surface_gates.py` (the shape, its parse round
    trip, a fixture render that a second render leaves unchanged, the live registry choosing it for `pages.deploy`
    only) and `test_pages_workflow.py::test_a_dispatch_bypasses_only_the_pause_switches_of_the_deploy`.
  - **S2.** `DW-9-7-1`, `DW-9-7-2` and `DW-FU-9-1-6` are closed as obsolete in steward's deferred-work ledger, citing
    this story's deletions.
  - **S3 / AC7, restated.** No executable caller of `deploy dashboard` or `deploy status` remains. The prose: herald's
    dossier (`docsite/content/dossier.yml`, the steward paragraph and the two passages about the deleted ledger
    guard) is corrected; the steward deck family is herald's deferred-work row `DW-herald-102-3-1` (a deck refresh
    through the claude-design bridge plus `deck-export`, operator-owned). The generated
    `docs/reference/station-cheat-sheet.md`, `planning-artifacts/test-architecture.md` and
    `planning-artifacts/test-design-qa.md` still name the retired verbs and the five deleted test modules; the
    coordinating session regenerates them after the chain's lanes merge.
  - **S4.** `marshal-policy.toml`'s Epic 102 surface now lists `scripts/pages_fleet_status.py` (this story),
    `scripts/pages_artifact_download.py` (102.4), the gate renderer and the registry schema, herald's dossier, docsite
    README and deferred-work ledger, each with its reason in the entry's comment.
  - **Nits.** The fleet input carries only the station fields herald reads (`station`, `epics`, `total`, `done`,
    `in_progress`, `backlog`, `blocked`): no `next_running`, so no live `marshal watch` fact reaches it, and
    `write_fleet_status` stamps HEAD's commit time (`head_commit_time`), so a local `steward pages build` writes the CI
    run's file. `scripts/pages_fleet_status.py` refuses an empty `--generated-at`. New tests: the production flag read
    through a flagd tree under `flag_states`, the help's duty choices line, a status where every `gh` call fails (the
    matrix row above is corrected), the stamp script's liveness wiring through a `file://` live `build.json` (a
    mutation that drops the two keywords fails it), and the deploy poll's no-run, earlier-dispatch and list-failure
    paths. The workflow header and `docs/reference/github-workflows.md`'s Kedro-Viz row are current (atlas 30.1
    removed the commit step; 102.4 mounts the artifact). The reformat of `scripts/pages_build_stamp.py` (N9) is kept:
    it is the repo-root ruff config's format, and the file is executable like its sibling scripts.
  - **N7, for herald 43.5.** The board's `generated_at` is the built commit's time, so `/status/` changes on every
    `main` commit even when the ledgers did not move; with the build-date footer it forces at most one re-hash a day.
    Herald 43.5 owns that interaction with the tree-hash deploy rule.
- 2026-10-15 (the re-review, `rereview-group1`: 102.3 RESOLVED, with three new nits; done here):
  - **`deploy --wait` reads the deploy job (nit a).** After `gh run watch <id> --exit-status` succeeds, the duty reads
    `gh run view <id> --json jobs` and the `deploy` job's conclusion (`pages_duty.DEPLOY_JOB`): `success` says
    "run N succeeded; deployed; page <url>"; `skipped` (a dispatch of an unchanged tree, the normal outcome since the
    pause-only gate) says "run N succeeded; tree unchanged; deploy skipped" and names no page; an unreadable answer (a
    failing call, invalid JSON, no concluded `deploy` job) or another conclusion is named on the line, and the result
    stays ok because the run itself succeeded. `--dry-run --wait` prints the watch and the jobs read. Tests:
    `test_pages_duty.py::test_ac2_deploy_wait_says_a_skipped_deploy_was_skipped`,
    `::test_ac2_deploy_wait_names_an_unreadable_deploy_job` (four cases),
    `::test_ac2_deploy_dry_run_with_wait_prints_the_watch_and_the_job_read`, and the deployed line in
    `::test_ac2_deploy_wait_watches_the_run_and_reports_the_page`.
  - **The lane evaluator reads the pause-only gate (nit b; chosen over restricting the schema option).**
    `preflight_ci._eval_ci_if_expression` now recurses into a parenthesised `||` / `&&` group under `&&`
    (`_eval_ci_term`), and `github.ref == | != '<literal>'` is an atom: under the simulated `pull_request` event the
    ref is `refs/pull/<number>/merge`, never a branch or tag ref, so `== 'refs/heads/main'` is false and `!=` true; a
    literal naming a pull request's own ref, or any other event, stays unevaluable (the lane runs and says why). A job
    `if:` that mentions `github.ref` is routed to the evaluator too. So `dispatch: pause-only` stays open to every
    registry row, a lane-bearing job included, and `docs/governance/ci-surfaces.schema.json` is unchanged. The live
    `pages.deploy` gate now evaluates to false under the simulation instead of raising. Tests:
    `test_preflight_selection.py::test_the_pause_only_gate_is_read_not_unevaluable` (reads the live `pages.yml`),
    `::test_nested_groups_evaluate_as_github_does` (five shapes), `::test_a_ref_the_simulation_cannot_know_stays_unevaluable`.
  - **The dossier's last ledger-guard line (nit c).** `docsite/content/dossier.yml`'s dependency-table cell for
    "Steward ← Marshal, Doctor" said Steward's console "refuses to publish rather than compute a status Marshal or
    Doctor haven't already certified", the deleted guard. It now reads as the Steward section's "A correction to the parent framing" finding does: Steward reads
    Marshal's tracked sprint ledgers as they stand and wraps Doctor's fleet-scan output, deriving no story status.
- 2026-10-15 (the lane-B re-review, `rereview-laneb`: 102.3 RESOLVED; two nits done here):
  - **`github.ref` on a push-only site is unevaluable.** The evaluator's context carries the trigger a site is judged
    through (`preflight_ci._TRIGGER_KEY`: `pull_request`, or `push` for a push-only workflow such as
    `kedro-viz-publish.yml`); a `github.ref` atom answers only on a pull request site, so a push-only job gated on
    `github.ref == 'refs/heads/main'` reads `unknown` and its lane runs, as before this story's evaluator change.
    Test: `test_preflight_selection.py::test_a_ref_atom_on_a_push_only_site_is_unevaluable` (the atom alone and
    through `_job_holds` on a push-only and a pull-request workflow).
  - **`DEPLOY_JOB` is pinned to `pages.yml`.** `gh run view --json jobs` names a job by its `name:`, else its id, so
    `test_pages_duty.py::test_the_deploy_job_the_duty_reads_is_pages_yml_s_deploy_job` asserts the deploy job carries
    no other `name:` and is the one that runs `actions/deploy-pages`.
- 2026-10-15 (landing preflight, orchestrator): the first full-scope `pr-preflight` of the one-PR branch crashed in
  `preflight_ci._registry_row_for_lane` with `IndexError` — most `ci-surfaces.yaml` rows declare no `local_twin`,
  and `str(row.get("local_twin") or "").split()[0]` raised on the first such row whenever a lane was deselected
  only by a live pause switch (the operator's 2026-10-15 CI pauses made that the normal case). The same code is on
  `origin/main` (Story 99.5), so this was a latent defect, fixed here as healed tissue in a module this story's
  review fixes already edit: an absent or blank twin now matches no lane. Test:
  `src/shared/packages/pyforge-steward/tests/unit/test_preflight_ci.py::test_a_row_without_a_local_twin_matches_no_lane`.
