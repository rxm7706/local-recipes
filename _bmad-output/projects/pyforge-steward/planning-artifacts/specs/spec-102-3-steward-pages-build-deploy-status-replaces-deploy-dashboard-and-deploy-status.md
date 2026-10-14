---
title: '102.3: `steward pages build|deploy|status` replaces `deploy dashboard` and `deploy status`'
type: 'feature'
created: '2026-10-14'
status: 'ready-for-dev'
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
| status, gh unauthenticated | `ci` reader refuses | line 3 `unavailable (<reason>)` | `ok=True` |
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
  `pyforge.steward.pages_duty` in both states with `pyforge.testing_kit.flags.flag_states` (AC4), `tests/unit/test_cli.py`
  and `tests/unit/test_restore_duty.py` (AC6)).

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

## Named, not fixed here

- The `--json` block shapes (no external consumer yet; freeze a schema only when one appears, as `ci-status-schema.json`
  did).
- Whether `pages deploy` accepts `--ref <branch>` for a rehearsal on a non-`main` ref (the workflow deploys from `main`
  only; a rehearsal would build and skip).

## Spec Change Log

- 2026-10-14: specced at mint from Epic 102's Story 102.3 text, `spec-pyforge-steward` CAP-168 and the live `deploy.py`
  / `cli.py` (`DUTIES` 29, `restore` at index 13). The implementing session reads the landed Story 102.2 `pages.py`
  first and follows it where it differs from the shape quoted here.
