---
title: '30.1: The DAG export reaches Pages as a workflow artifact'
type: 'feature'
created: '2026-10-14'
status: 'done'
followup_review_recommended: false
baseline_revision: 'f7be77efadb4c111c7913f0853ad1cb3a1058f05'
flag:
  key: pyforge.atlas.viz_export_artifact          # new; minted by this story
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through the overlay (src/platform/config/flag-overlays.json)
  scope: global                                   # v1 is global only
  fallback: 'viz-publish-stage stages to docs/dashboard/kedro-viz/ exactly as today, writes no manifest.json, and the workflow upload step is skipped'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - docs/dreams/pyforge-atlas.md
  - docs/dreams/pyforge-herald.md
  - _bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/brainstorm-intent.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - .github/workflows/kedro-viz-publish.yml
  - src/shared/packages/pyforge-atlas/tools/normalize_viz_build.py
  - docs/dashboard/README.md
  - docs/governance/ci-surfaces.yaml
  - src/shared/packages/pyforge-steward/src/pyforge/steward/ci.py
  - src/platform/config/flags.json
  - pixi.toml
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** CAP-41 ("Kedro-Viz publish stays in sync", shipped 2026-09-09) presumed a producer that commits the export
to `main`. That producer, `.github/workflows/kedro-viz-publish.yml`, has been `disabled_manually` since 2026-08-24 with
no recorded reason (registry row `kedro-viz-publish`: `paused-manually`, `switch: null`, `review_by: 2026-11-01`), and
the committed export `docs/dashboard/kedro-viz/` (11 MB, 215 tracked files) was last written 2026-08-15. Since the
pause, 23 first-parent merges touched the paths the workflow watches (re-measured 2026-10-14 on `origin/main`: 23), so
the graph the site publishes lags its DAG by two months. The commit path also needs `contents: write`, a re-attached
`main`, a bot identity and steward's reconciled push — the bot-commit pattern the Pages redesign retires (herald Dream
2026-10-13, M2: "no commit by `github-actions[bot]` lands on `main` for Pages").

**Approach:** the producer keeps everything that reads the DAG and drops everything that writes git.

- **The workflow.** `kedro-viz-publish.yml` keeps its `on.push.paths` filter (`pipelines/**`, `conf/base/catalog.yml`,
  `conf/base/globals.yml`, `datasets/**`) and `workflow_dispatch`, keeps the stub `conf/local/credentials.yml` step
  exactly as written (`kedro viz build` still resolves two credentialed catalog entries), keeps
  `pixi run -e pyforge-atlas viz-publish-stage`, and replaces the `steward deploy dashboard` step with one
  `actions/upload-artifact` step: `name: kedro-viz-export`, `retention-days: 90`, `path:` the staged tree. The
  "Re-attach to main" and "Configure git identity" steps go. `permissions.contents` drops to `read`. The
  `pyforge-steward` environment leaves `setup-pixi`'s list (nothing in the job calls steward any more). The job's `if:`
  carries the CI-pause fragment reading `vars.PAUSE_KEDRO_VIZ_PUBLISH`, in the shape steward Story 99.2 rendered onto
  every other job (read the fragment off `dashboard.yml` or `detectors.yml`; do not invent a second shape).
- **The manifest.** `viz-publish-stage` writes `manifest.json` beside the staged `index.html`, from a small tool in
  `src/shared/packages/pyforge-atlas/tools/` (a function in `normalize_viz_build.py` or a sibling `viz_manifest.py`):
  `export_commit` — the 40-hex commit the DAG was read from, `GITHUB_SHA` when set, else `git rev-parse HEAD`;
  `export_date` — that commit's committer date as ISO 8601 UTC (`git show -s --format=%cI <sha>` normalized to `Z`);
  `kedro_viz_version` — the `version` field of `build/api/deploy-viz-metadata`, read, never hard-coded. The normalizer
  still strips the checkout path and sets the wall-clock timestamp to `unset`, so two builds of one DAG stay
  byte-identical except for the manifest, which is a function of the commit.
- **The committed export leaves git.** `git rm -r --cached docs/dashboard/kedro-viz` and a `.gitignore` entry for
  `docs/dashboard/kedro-viz/` (the staging path stays, so a local `viz-publish-stage` and the consumer's download agree
  on one path; only the tracking changes). `docs/dashboard/README.md` says the export arrives as the workflow artifact
  `kedro-viz-export` and names the manifest; it no longer names `steward deploy dashboard`. The `.gitignore` comment at
  the `docs/dashboard/` line is corrected in the same edit.
- **The registry row.** `docs/governance/ci-surfaces.yaml` row `kedro-viz-publish` gains `switch: PAUSE_KEDRO_VIZ_PUBLISH`
  (the 99.2 convention: `PAUSE_` plus the upper-snake id). This is steward's file: the PR carries the edit with
  `spec-pyforge-steward`'s memlog reconcile as co-governor. The row's `state` is NOT changed by this story: the
  `paused-manually → live` move is the operator's gate (§ Named, not fixed here).
- **The flag.** `pyforge.atlas.viz_export_artifact` lands in `src/platform/config/flags.json` (`defaultVariant` off,
  metadata owner `atlas`, story this key, the shape `pyforge.atlas.dependency_history` uses) and in
  `flag-overlays.json` (dev on, staging and production off), and in `docs/governance/flag-inventory/pyforge-atlas.md`.
  A reader under `src/shared/packages/pyforge-atlas/src/pyforge/atlas/` goes through `pyforge.core.flags.read_boolean`
  (the flag gate counts only readers under `src/` or `scripts/`); the manifest tool takes the resolved state as an
  argument, and the workflow's upload step takes it as a step `if:` from a Guild-env step that prints it. Off: no
  manifest, no upload, the staged tree byte-identical to today's.
- **The consumer is not this story.** Steward Story 102.4 on the renamed `pages.yml` (steward 102.2) downloads the
  newest successful `kedro-viz-export` into `/dashboard/kedro-viz/`, skips the mount and hides the tile when none
  exists, and renders the manifest's `export_commit` and `export_date` on that page. Atlas never patches kedro-viz's
  `index.html` to show them.

Ledger key: `30-1-the-dag-export-reaches-pages-as-a-workflow-artifact`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / — (cross-station, prose: steward 102.2 and 102.4; no blocked row).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-62** (FR-70): the artifact handoff, the manifest, the retired commit path, the flag. Amends
  CAP-41 (the producer that commits); works with CAP-16 (the read surface runs with no backend at all); AD-21 as
  amended 2026-10-14 (every static surface atlas publishes reaches Pages as a workflow artifact), AD-17 (payloads carry
  their build provenance), AD-1 (nothing new imports Dagster or `kedro-mcp`; `pipelines/`, `datasets/`, `hooks.py`
  untouched), AD-11 (the stub-credentials step stays; no credential enters the workflow).
- **`pyforge-steward:CAP-166`** (steward Epic 99): the CI-surfaces registry, the `PAUSE_*` convention (Story 99.2), the
  `ci` duty (Stories 99.3, 99.4). Read and cited, never imported; the row edit is steward's co-governed reconcile.
- **herald AD-21** (one Pages artifact, one deploy caller, zero third-party origins): atlas calls no `deploy-pages` and
  commits nothing; the artifact is the only handoff.
- **canopy:AD-11** (one flag tree); `feature-flag-governance:CAP-1` (the flag rule), `feature-flag-governance:CAP-4`
  (the two-state test).
- **Origin.** Dream `docs/dreams/pyforge-atlas.md`, the 2026-10-13 entry (the DAG export reaches Pages as an artifact);
  herald Dream 2026-10-13 (the Pages deployment, redesigned; M2 and the placement rule); the intake
  (`brainstorm-intent.md`, M2 and the constraints); operator ruling 2026-10-13.

## Acceptance Criteria

- **AC1 — The export leaves git.** On the story's tree `git ls-files docs/dashboard/kedro-viz | wc -l` prints `0`, and
  `git check-ignore docs/dashboard/kedro-viz/index.html` exits 0. `docs/dashboard/README.md` stays tracked.
- **AC2 — The manifest.** With the flag on, after `pixi run -e pyforge-atlas viz-publish-stage`,
  `docs/dashboard/kedro-viz/manifest.json` parses as JSON with exactly the keys `export_commit`, `export_date`,
  `kedro_viz_version`; `export_commit` matches `^[0-9a-f]{40}$` and equals `git rev-parse HEAD` (or `GITHUB_SHA` when
  that is set); `export_date` parses as ISO 8601 UTC and equals that commit's committer date; `kedro_viz_version` equals
  the `version` field of `docs/dashboard/kedro-viz/api/deploy-viz-metadata`, whose `timestamp` still reads `unset`.
- **AC3 — Flag off.** With the flag off, `viz-publish-stage` writes no `manifest.json` and the staged tree is
  byte-identical to a run of today's task on the same commit (`diff -r` is empty).
- **AC4 — The workflow shape.** A test reads `.github/workflows/kedro-viz-publish.yml` as YAML and asserts: exactly one
  step whose `uses` starts with `actions/upload-artifact`, with `with.name == "kedro-viz-export"`,
  `with.retention-days == 90` and `with.path` equal to the staged path; no step whose `run` contains
  `steward deploy dashboard`, `git checkout -B main`, `git config user.name` or `git push`; `permissions.contents ==
  "read"` and no `write` permission; `on.push.paths` and `on.workflow_dispatch` unchanged from `baseline_revision`;
  the stub-credentials step present with its `credentials.yml` heredoc unchanged; `setup-pixi`'s `environments` naming
  `pyforge-atlas` and not `pyforge-steward`; the job's `if:` containing `PAUSE_KEDRO_VIZ_PUBLISH`; the upload step's
  `if:` gated on the flag's resolved value.
- **AC5 — The registry row.** `docs/governance/ci-surfaces.yaml` row `kedro-viz-publish` has
  `switch: PAUSE_KEDRO_VIZ_PUBLISH` and `switch_class: pause`; its `state` is unchanged by this story
  (`paused-manually`); `docs/governance/ci-surfaces.schema.json` still validates the file (steward's own check).
- **AC6 — The README.** `docs/dashboard/README.md` names `kedro-viz-export` and `manifest.json` and does not contain the
  string `steward deploy dashboard`.
- **AC7 — Two states.** A test under `src/shared/packages/pyforge-atlas/tests/unit/` runs the manifest tool with
  `pyforge.testing_kit.flags.flag_states("pyforge.atlas.viz_export_artifact")`: on, a fixture `build/` gains a
  manifest whose three fields are checked (AC2); off, no file is written and the fixture tree is unchanged (AC3).
- **AC8 — The gates.** `pixi run -e pyforge-atlas kedro-test` and `pixi run -e pyforge-atlas kedro-catalog-check` exit 0
  (AD-1 import-direction and no-inline-IO meta-tests included); `pixi run --frozen -e pyforge-guild flag-gate-check`
  exits 0; `pixi run --frozen -e pyforge-guild spec-surface-check` exits 0 after the memlog reconciles and scoped stamps
  of every Spec it names (`spec-pyforge-atlas`; `spec-pyforge-steward` for the registry row; any governor of
  `docs/dashboard/README.md` and `.gitignore` it reports).

## Boundaries & Constraints

**Always:**
- The stub `conf/local/credentials.yml` step stays byte-for-byte; no credential, token or secret enters the workflow.
- The path filter, `workflow_dispatch`, `concurrency` group and `timeout-minutes` stay as written.
- `tools/normalize_viz_build.py`'s two normalizations stay (checkout path, wall-clock timestamp); the manifest is the
  only provenance that varies, and it varies only with the commit.
- The staging path stays `docs/dashboard/kedro-viz/`; only its tracking changes.
- The flag is read through `pyforge.core.flags.read_boolean` in atlas's package; the tool and the workflow step receive
  a resolved value.
- Every Spec `spec-surface-check` names is reconciled through its memlog and stamped scoped; the PR carries the
  `maintenance` label.

**Never:**
- Do not commit, push or call `actions/deploy-pages` from this workflow; do not add a second deploy caller.
- Do not edit `.github/workflows/dashboard.yml`, `pages.yml`, `docsite/`, `docs-site/` or any steward `deploy` duty: the
  consumer is steward 102.4 and the mount is herald's.
- Do not change the registry row's `state`, add or remove a registry row, or edit `ci-surfaces.schema.json`; do not run
  `steward ci pause|resume --yes` or `gh workflow enable` from the story (operator gate).
- Do not patch kedro-viz's `index.html` or the `build/` output beyond the existing normalizer and the manifest.
- Do not import Dagster, `kedro-mcp`, `pyforge.steward` or `subprocess` under `src/pyforge/atlas` (the `git` calls live
  in `tools/`, outside the package the no-inline-IO gate scans, or go through `pyforge.core.process`).
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| flag on, CI | `GITHUB_SHA` set, `build/` normalized | `manifest.json` with the three keys; `export_commit == GITHUB_SHA` | exit 0 |
| flag on, local | no `GITHUB_SHA` | `export_commit == git rev-parse HEAD` | exit 0 |
| flag off | any | no `manifest.json`; tree byte-identical to today's | exit 0 |
| metadata missing | `build/api/deploy-viz-metadata` absent or without `version` | no manifest written | exit 1 naming the file |
| not a 40-hex sha | `GITHUB_SHA=abc` | no manifest written | exit 1 naming the value |
| dirty metadata | `deploy-viz-metadata.timestamp != "unset"` | the normalizer already raised; the manifest tool is not reached | exit 1 (normalizer) |
| workflow drift | a `run:` step containing `steward deploy dashboard` | AC4 test reds | test failure names the step |
| export tracked again | a file under `docs/dashboard/kedro-viz/` staged in git | AC1 test reds | test failure names the path |
| row without switch | `kedro-viz-publish` row lacks `switch` | AC5 test reds | test failure names the row |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-62 (FR-70), minted 2026-10-14; amends CAP-41; reads
  `pyforge-steward:CAP-166`.
- Architecture: AD-21 (amended 2026-10-14), AD-17, AD-1, AD-11; herald AD-21 (one deploy caller, zero third-party
  origins). See the spine's § Currency reconciliation — 2026-10-14.
- Dream: `docs/dreams/pyforge-atlas.md` § Realization log, the 2026-10-13 entry (the DAG export reaches Pages as an
  artifact); herald Dream 2026-10-13 (the Pages deployment, redesigned).
- Epic: Epic 30, Story 30.1.
- Ledger key: `30-1-the-dag-export-reaches-pages-as-a-workflow-artifact`.
- Ledger status at mint: `backlog`.
- Deps: none inside atlas. Cross-station, prose: steward Story 102.2 (the renamed `pages.yml`) exists to consume the
  artifact and steward Story 102.4 is the consumer step; neither is a blocked row. `marshal factory dispatch` stamps
  `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."30"`.
- Flag: `pyforge.atlas.viz_export_artifact` (`feature-flag-governance:CAP-1`).

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-pyforge-atlas CAP-62 (FR-70), amending CAP-41; AD-21
(amended 2026-10-14), AD-17, AD-1, AD-11; reads `pyforge-steward:CAP-166` • flag: `pyforge.atlas.viz_export_artifact`

**Given** `kedro-viz-publish.yml` as it stands (path filter, stub credentials, `viz-publish-stage`, then `steward deploy
dashboard` committing `docs/dashboard/kedro-viz/` with `contents: write`), disabled by hand since 2026-08-24, and a
committed export last written 2026-08-15
**When** the story's tree is built with the flag on
**Then** `git ls-files docs/dashboard/kedro-viz` lists nothing and the path is gitignored; `viz-publish-stage` leaves
`manifest.json` beside `index.html` with `export_commit`, `export_date` and `kedro_viz_version`; the workflow has one
`actions/upload-artifact` step (`kedro-viz-export`, 90 days), no commit step, `permissions.contents: read`, the path
filter and the stub-credentials step unchanged, and a job `if:` carrying `PAUSE_KEDRO_VIZ_PUBLISH`
**And** the registry row names the switch; the README names the artifact; flag off changes nothing; `kedro-test` and
`kedro-catalog-check` are green and the flag test runs the key in both states

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (the station's `verify_commands`; import smoke and scaffold
  layout).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (the station's `verify_commands`; the AD-1
  import-direction and no-inline-IO meta-tests, which must stay green with the manifest tool in `tools/`).

**Run before the push (not dispatch gates):**
- `pixi run -e pyforge-atlas pyforge-atlas-test -k "viz_manifest or kedro_viz_publish or viz_export_artifact"` — expected:
  pass (AC1–AC7; the flag test through `pyforge.testing_kit.flags.flag_states`).
- `pixi run -e pyforge-atlas viz-publish-stage` on a checkout with the flag on, then
  `python3 -c "import json; m=json.load(open('docs/dashboard/kedro-viz/manifest.json')); print(sorted(m))"` — expected:
  `['export_commit', 'export_date', 'kedro_viz_version']` (AC2).
- `git ls-files docs/dashboard/kedro-viz | wc -l` — expected: `0`; `git check-ignore docs/dashboard/kedro-viz/index.html`
  — expected: exit 0 (AC1).
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0, read from the exit code.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and the scoped
  stamps (`spec-pyforge-atlas`, `spec-pyforge-steward`, and any governor the detector names for `.gitignore` and
  `docs/dashboard/README.md`).
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

**Operator, after landing (outward acts a session never performs):**
- Re-enable the hand-disabled workflow on GitHub (`gh workflow enable kedro-viz-publish.yml --repo rxm7706/local-recipes`)
  and move the registry row `kedro-viz-publish` from `paused-manually` to `live` through steward's `ci` duty — as landed
  on 2026-10-14, `run_resume` accepts only a `paused` row with one switch, so this needs the steward answer the Spec's
  open question names, or a hand edit of the row. Then `gh workflow run kedro-viz-publish.yml` once, and confirm the run
  uploaded `kedro-viz-export` (`gh run view <id>` lists the artifact) in the 92–137 s the build took before the pause.
- Turn `pyforge.atlas.viz_export_artifact` on in the environments that should produce the manifest.

## Named, not fixed here

- **The consumer.** Steward Story 102.4 on the renamed `pages.yml` (steward 102.2): download the newest successful
  `kedro-viz-export` into `/dashboard/kedro-viz/`, skip the mount and hide the tile when none exists, render
  `export_commit` and `export_date` on that page. The URL keeps.
- **The registry row's state.** `paused-manually → live` is the operator's gate; which duty performs it is the Spec's
  open question of 2026-10-14 (steward's `run_resume` refuses a row that is not `paused`).
- **The Vizro producer.** Story 30.2 adds `vizro-static-export` and the `vizro-static-export` artifact, as a second job
  on this workflow or its own (operator's call).
- **A later move of the URL** (`/pipelines/` in the intake's IA7) is herald's M3 decision; the placement rule keeps
  `/dashboard/kedro-viz/` for now.

## Spec Change Log

- 2026-10-14: specced at mint from Epic 30's Story 30.1 text, `spec-pyforge-atlas` CAP-62, the landed workflow
  (`kedro-viz-publish.yml` at `e134549afc`), `tools/normalize_viz_build.py`, the registry row and steward's `ci.py`
  (`run_resume`, lines 1067–1090). The implementing session reads the CI-pause fragment steward Story 99.2 rendered on
  another workflow and copies its shape; where the landed code differs from the shape quoted here, the landed code wins
  and the deviation is recorded in this log.
- 2026-10-15: landed Story 30.1 — `normalize_viz_build.py` repo-root marker is `docs/dashboard/README.md` (not
  `kedro-viz/index.html`) so CI can normalize on a fresh clone after the export leaves git.

## Review Triage Log

### 2026-10-15 — Review pass
- verdicts: 2 findings — high 0, medium 0, low 1, false 1, maybe-false 0
- findings:
  - `[low]` `[reject]` `actions/upload-artifact@v4` while `pages.yml` uses `@v7` — versions differ by workflow age; upload shape matches AC4.
  - `[false]` `[reject]` Stub-credentials heredoc drift claim — byte match to baseline workflow preserved.

## Auto Run Result

Status: done

Summary: Kedro-Viz publish now stages locally, optionally writes `manifest.json` when `pyforge.atlas.viz_export_artifact` is on, and uploads `kedro-viz-export` (90 days) instead of committing. The tracked export tree was removed from git and gitignored; CI pause switch `PAUSE_KEDRO_VIZ_PUBLISH` was wired on the registry row and job `if:`.

Files changed (high level):
- `.github/workflows/kedro-viz-publish.yml` — artifact upload, read-only permissions, pause fragment, flag-gated upload
- `src/shared/packages/pyforge-atlas/tools/{viz_manifest,viz_publish_finish,print_viz_export_flag}.py` — manifest + flag wiring
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/viz_export_artifact.py` — `read_boolean` reader
- `tests/unit/test_viz_export_artifact.py` — AC1–AC7 + matrix rows
- `docs/dashboard/README.md`, `.gitignore`, `docs/governance/ci-surfaces.yaml`, flag tree + overlays, `pixi.toml` task chain
- Removed tracked `docs/dashboard/kedro-viz/**`

Review: 0 patches applied; 0 deferred.

Verification:
- `pytest …/test_viz_export_artifact.py` — 8 passed
- `kedro-catalog-check` — 69 passed
- `python scripts/spec_surface_reconcile.py` — OK (memlogs on spec-pyforge-atlas, spec-pyforge-steward, spec-pyforge-core, spec-pyforge-unifying-strategy, spec-pyforge-pages, spec-pyforge-marshal, spec-pixi-candidate-currency)
- `pixi run --frozen -e pyforge-guild spec-surface-check` — exit 0
- `pixi run --frozen -e pyforge-guild flag-gate-check` — exit 0 (1 unrelated pre-existing steward spec fail outside this story)

Residual risks: Operator must re-enable `kedro-viz-publish.yml` on GitHub and flip registry `paused-manually → live` (Named, not fixed here). Steward 102.4 consumes the artifact.

followup_review_recommended: false
