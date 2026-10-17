---
title: "102.4: The Pages build mounts atlas's Kedro-Viz export from a workflow artifact and tolerates its absence"
type: 'feature'
created: '2026-10-14'
status: 'done'
baseline_revision: '8ef404d388d1bdafac6aa0d96a8f626f97cad47a'
flag:
  key: pyforge.steward.pages_duty                 # Story 102.2's; the download step reads its exported state
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through Epic 76's overlay
  scope: global                                   # v1 is global only
  fallback: 'no artifact is downloaded; the build mounts whatever docs/dashboard/ holds, as today'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-102-2-one-pages-workflow-in-upstream-shape-builds-on-every-change-and-deploys-only-what-changed.md
  - docs/dreams/pyforge-steward.md
  - docs/dreams/pyforge-herald.md
  - docs/dreams/pyforge-atlas.md
  - _bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/brainstorm-intent.md
  - .github/workflows/pages.yml
  - .github/workflows/kedro-viz-publish.yml
  - docsite/tools/assemble_pages.py
  - docsite/content/site.yml
  - docs/dashboard/README.md
  - .gitignore
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The Kedro-Viz export (11 MB, 215 files) has been committed under `docs/dashboard/kedro-viz/` since
2026-08-15, frozen because its producer `kedro-viz-publish.yml` was disabled on 2026-08-24; the Pages build copies the
committed tree into the artifact (`assemble_pages.py` `_copy_dashboard`) and exits 1 when
`dashboard/kedro-viz/index.html` is missing (`_ensure_kedro_viz_redirect`). The operator ruled 2026-10-13: the export
arrives as atlas's workflow artifact `kedro-viz-export`, no bytes in git, and the mount is skipped, never failed, when
none exists. Atlas Story 30.1 makes the producer upload the artifact and deletes the committed tree; this story is
the consumer step in steward's workflow.

**Approach:** One download step before `pages-check`, three env outputs, one permission, one filter entry removed.

- **The step.** In `pages.yml`'s `build` job, before `pages-check`, with `actions: read` added to the job's
  permissions: find the newest successful run of atlas's producer that has the artifact — `gh run list --workflow
  kedro-viz-publish.yml --status success --limit 10 --json databaseId,createdAt` then `gh api
  repos/{owner}/{repo}/actions/runs/<id>/artifacts --jq` for `kedro-viz-export` not expired — and download it with
  `gh run download <id> -n kedro-viz-export -D docs/dashboard/kedro-viz` (or `actions/download-artifact@v8` with
  `run-id` and `github-token`, the implementer's call; both need `actions: read`). The mount source stays
  `docs/dashboard/kedro-viz/`, the path the assembler already reads, so herald's build sees the export where it did.
  The step writes `KEDRO_VIZ_EXPORT=present|absent`, `KEDRO_VIZ_EXPORT_RUN=<id>` and `KEDRO_VIZ_EXPORT_AT=<createdAt>`
  to `GITHUB_ENV` and exits 0 in both cases; it is gated on the Guild step's exported flag state (Story 102.2), so
  with `pyforge.steward.pages_duty` off nothing is downloaded. The logic is a function in `pyforge/steward/pages.py`
  (`newest_export_run(runs_json, artifacts_json) -> id | None`) the step calls through the Guild env, so the
  selection is unit-tested on recorded `gh` JSON; the download itself is one `gh` subprocess (AD-1).
- **Absence.** No successful run, no artifact, or an expired one: the step prints `kedro-viz-export: none found;
  mount skipped`, exports `absent` and exits 0. The assembler's refusal on a missing mount and the `Kedro-Viz`
  neighbour tile in `docsite/content/site.yml` are herald's: herald Story 42.2 (CAP-60, the Kedro-Viz mount tolerates absence) (the coordinator numbers it)
  makes `assemble_pages.py` skip the `dashboard/kedro-viz/` mount and the redirect when `KEDRO_VIZ_EXPORT=absent` and
  hides the tile. Until it lands, this step's `absent` path is proven in isolation (exit 0, the env lines) and the
  end-to-end "build exits 0 with no export" is recorded here once herald's half is on `main`. `KEDRO_VIZ_EXPORT_AT` is
  for herald's "export age shown" (the site map's IA7 row); steward only passes it through.
- **The filter.** Once atlas Story 30.1 has deleted `docs/dashboard/kedro-viz/` from the tree (`git ls-files
  docs/dashboard/kedro-viz` is empty), `docs/dashboard/**` leaves both `paths:` lists in `pages.yml` (nothing
  published lives there any more; `docs/dashboard/README.md` says where the export comes from now) and
  `.gitignore` gains `docs/dashboard/kedro-viz/` so a local download never shows as untracked. If 30.1 has not landed,
  the entry stays and the story records why.
- **The registry.** No new row: the step is part of `pages.build` (CAP-166's row), and `workflow_dispatch` runs it
  like any step.

Ledger key: `102-4-the-pages-build-mounts-atlas-s-kedro-viz-export-from-a-workflow-artifact-and-tolerates-its-absence`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / S-102.2; atlas Story 30.1 (the producer uploads `kedro-viz-export`; the committed
tree is deleted); herald Story 42.2 (CAP-60, the Kedro-Viz mount tolerates absence) (the assembler skips an absent mount, the tile hides).

### Living CAP citations

- **`spec-pyforge-steward` CAP-168** (FR-41): the consumer step, its permission, its env outputs, the filter change.
- **AD-1**: `gh` by subprocess; the selection logic is the only code, and it reads recorded JSON. **AD-8**: the step's
  exit is 0 on present and absent alike; a `gh` failure that is not "none found" fails the step (a real error is never
  read as absence).
- **herald herald:AD-21**: the mount prefix `/dashboard/kedro-viz/` keeps its URL; the content is atlas's, served by herald's
  assembler. **spec-pyforge-atlas** (Story 30.1): the producer and the artifact name `kedro-viz-export` are atlas's
  contract; steward reads them.
- **Flag:** `pyforge.steward.pages_duty` (Story 102.2's).
- **Origin.** The Dream's 2026-10-13 (the Pages duct) entry; the herald Dream's M2 ("the Kedro-Viz export arrives as
  a workflow artifact from atlas's producer and the mount is skipped, never failed, when none exists");
  brainstorm-intent § M2 and open question 1 (atlas's call, answered: the artifact handoff); design thinking Key
  Feature 2 (cross-run download within retention and `actions: read`).

## Acceptance Criteria

- **AC1 — Selection.** `newest_export_run` over recorded `gh run list` and artifacts JSON returns the newest
  successful run whose `kedro-viz-export` is not expired; returns `None` for no runs, for runs without the artifact,
  and for an expired artifact; ignores runs whose `conclusion` is not `success`. *(Amended 2026-10-15 by 102.4's
  re-review, orchestrator ruling: the selection reads the artifact listing, not a run window. Over recorded
  `gh api repos/{owner}/{repo}/actions/artifacts?name=<artifact>` pages and each candidate's run payload,
  `newest_export_run(artifacts_json, runs_json, *, artifact, workflow, branch)` returns the run holding the newest
  live artifact of that name from a successful `--workflow` run on `--branch` (not a fork's); `None` for no such
  artifact or only expired ones; a live artifact whose run cannot be read is a wrong-shape error, never a skip. See
  the Spec Change Log.)*
- **AC2 — Present.** With a fake `gh` returning a run and an artifact, the step's script downloads into
  `docs/dashboard/kedro-viz/` (the fake records `gh run download <id> -n kedro-viz-export -D docs/dashboard/kedro-viz`),
  writes `KEDRO_VIZ_EXPORT=present`, `KEDRO_VIZ_EXPORT_RUN=<id>`, `KEDRO_VIZ_EXPORT_AT=<createdAt>`, exit 0.
- **AC3 — Absent.** With a fake `gh` returning no matching run, the script prints `kedro-viz-export: none found; mount
  skipped`, writes `KEDRO_VIZ_EXPORT=absent`, records no download, exit 0. With a fake `gh` exiting 1 on `run list`
  (an auth or API error), the script exits 1 naming the argv — never `absent`.
- **AC4 — Flag.** With `pyforge.steward.pages_duty` off (the Guild step's exported state), the step is skipped by its
  `if:` and no `gh` call is made; `src/shared/packages/pyforge-steward/tests/unit/test_pages_export_flag_states.py`
  runs the script's entry through `flag_states("pyforge.steward.pages_duty")`: on, the selection runs; off, it
  returns before any call.
- **AC5 — Permission and placement.** A test parses `pages.yml`: the `build` job's `permissions` include
  `actions: read` and nothing beyond `contents: read`, `pages: write`, `id-token: write`, `actions: read`; the
  download step precedes the `pages-check` step.
- **AC6 — The filter.** If `git ls-files docs/dashboard/kedro-viz` is empty at landing, `docs/dashboard/**` is absent
  from both `paths:` lists and `.gitignore` names `docs/dashboard/kedro-viz/`; otherwise both are unchanged and this
  spec's Auto Run Result says why.
- **AC7 — End to end (recorded).** One `workflow_dispatch` run after atlas 30.1 and herald's half have landed, with the
  flag on: the run's log shows the download and `pages-check` exits 0 with `/dashboard/kedro-viz/` in the artifact; a
  second record, taken when no artifact exists (or by `gh run download` of a run whose artifact expired), shows the
  `absent` path and a green build.
- **AC8 — The gates.** `pixi run --frozen -e pyforge-steward pyforge-steward-test`, `flag-gate-check`, `python
  scripts/ci_surface_gates.py --check`, `detectors-ci` and `spec-surface-check` exit 0.

## Boundaries & Constraints

**Always:**
- The mount source stays `docs/dashboard/kedro-viz/`; the URL stays `/dashboard/kedro-viz/`.
- A real `gh` error fails the step; only "no run / no artifact / expired" reads as absent.
- `actions: read` is the only permission added, on the `build` job only.
- Every cross-station fact (the artifact name, the producer workflow, the assembler's behaviour) is read from the
  landed files and recorded here where it differs from this text.

**Never:**
- Do not edit `kedro-viz-publish.yml` (atlas's), `assemble_pages.py` or `site.yml` (herald's).
- Do not commit any file under `docs/dashboard/kedro-viz/`.
- Do not add a token, a secret or a second artifact name. *(Annotated 2026-10-15 with the review's ruling,
  `review-102-4` should-fix 3 and atlas 30.2's review: `GH_ENTERPRISE_TOKEN` is the job's own `github.token` under
  the name `gh` reads on a GitHub Enterprise Server, not a new token or secret, and the second artifact name
  `vizro-static-export` is atlas 30.2's consumer step, which 30.2's review moved into this workflow. Both are
  recorded in the Spec Change Log.)*
- Do not fail the build on absence.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| export exists | newest success run has the artifact | download, `present`, run id and date exported | — |
| producer never ran | no runs | `absent`, mount skipped, exit 0 | — |
| artifact expired | 90-day retention passed | `absent`, exit 0 | — |
| last run failed, earlier succeeded | mixed conclusions | the earlier success is chosen | — |
| gh API error | `run list` exit 1 | step fails naming the argv | never `absent` |
| flag off | exported state off | step skipped, no call | — |
| tree still committed | 30.1 not landed | filter entry kept, reason recorded | — |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-168 (FR-41), minted 2026-10-14.
- Architecture: AD-1, AD-8; herald herald:AD-21 (the mount's URL).
- Dream: `docs/dreams/pyforge-steward.md` § Realization log, the 2026-10-13 (the Pages duct) entry.
- Epic: Epic 102, Story 102.4.
- Ledger key: `102-4-the-pages-build-mounts-atlas-s-kedro-viz-export-from-a-workflow-artifact-and-tolerates-its-absence`.
- Ledger status at mint: `backlog`.
- Deps: S-102.2; atlas Story 30.1 (cross-station, named in `Deps:`, never a blocked row); herald Story 42.2 (CAP-60, the Kedro-Viz mount tolerates absence)
  (the coordinator fills the key). `marshal factory dispatch` stamps `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."102"`.
- Flag: `pyforge.steward.pages_duty` (Story 102.2's).

## Epic excerpt

**Type:** feature • **Effort:** S • **Deps:** S-102.2; atlas Story 30.1; herald Story 42.2 (CAP-60, the Kedro-Viz mount tolerates absence) • **FR/AD:** spec-pyforge-steward CAP-168 (FR-41); AD-1, AD-8; herald herald:AD-21 • flag: `pyforge.steward.pages_duty` (Story 102.2's)

**Given** a Kedro-Viz export committed since 2026-08-15 and copied into the artifact, and an assembler that exits 1 when
the mount is missing
**When** `pages.yml`'s `build` job, with `actions: read`, downloads atlas's newest successful `kedro-viz-export`
artifact into the mount source before `pages-check` and exports `present|absent`, the run id and the export date,
and `docs/dashboard/**` leaves the filter once the committed tree is gone
**Then** the selection is unit-tested on recorded `gh` JSON, a present artifact is downloaded and an absent one exits 0
with the mount skipped, a real `gh` error fails the step, and the flag-off path makes no call
**And** `pyforge-steward-test`, `flag-gate-check` and `ci_surface_gates.py --check` are green, and one dispatched run
with and one without the artifact are recorded

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`;
  MRS-GATE-010 binding; it runs `src/shared/packages/pyforge-steward/tests/unit/test_pages_export.py` (AC1–AC3, AC5)
  and `src/shared/packages/pyforge-steward/tests/unit/test_pages_export_flag_states.py`, which runs the key
  `pyforge.steward.pages_duty` in both states with `pyforge.testing_kit.flags.flag_states` (AC4)).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_pages_export.py src/shared/packages/pyforge-steward/tests/unit/test_pages_export_flag_states.py -q` — expected: pass.
- `python scripts/ci_surface_gates.py --check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.
- `git ls-files docs/dashboard/kedro-viz | wc -l` — expected: 0 when atlas 30.1 has landed (AC6 branch).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

**Operator, after landing (AC7):**
- `gh workflow run pages.yml --ref main` once atlas 30.1 and herald's half are on `main`; read the run's download
  step and `pages-check` exit; record both run ids (present and absent) here.

## AC7 records (2026-10-17)

- **`present`:** `pages.yml` run `39020410506` (`workflow_dispatch` via `pyforge steward pages deploy --wait`, on `main`
  `6fa7150e2b`, 2026-10-17), conclusion `success`. Its "Download the Kedro-Viz export artifact" step logged
  `kedro-viz-export: run 39019867740 (2026-10-17T09:06:31Z) downloaded into docs/dashboard/kedro-viz`, and the later
  steps read `KEDRO_VIZ_EXPORT: present`, `KEDRO_VIZ_EXPORT_RUN: 39019867740`. `pages-check` printed
  `exempt vendored root dashboard/kedro-viz/` and `… docs-site/build/site passes`, and the uploaded artifact lists
  `./dashboard/kedro-viz/index.html`, `api/main` and `api/deploy-viz-metadata`. The producer run `39019867740`
  (`kedro-viz-publish.yml`, dispatched after atlas Story 32.1, #2248) uploaded `kedro-viz-export` (3.4 MB). Live after
  the deploy: `https://rxm7706.github.io/local-recipes/dashboard/kedro-viz/` and `…/api/main` answer 200, `build.json`
  reads `run_id` `39020410506` and `built_from` `6fa7150e2b`, and the page renders Kedro-Viz 12.5.0 with the
  `__default__` pipeline (82 nodes, 122 datasets; seen in a browser).
- **`absent`:** `pages.yml` run `38831558913` (`pull_request`, the Pages chain PR #2240 at `44e13daa9b`, 2026-10-16),
  conclusion `success`: `kedro-viz-export: none found; mount skipped`, `KEDRO_VIZ_EXPORT: absent`, and `pages-check`
  `… docs-site/build/site passes`.

## Verification run (2026-10-15)

- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_pages_export.py src/shared/packages/pyforge-steward/tests/unit/test_pages_export_flag_states.py -q`
  — exit 0 (AC1–AC5; with `test_pages_workflow.py` and `test_pages.py`, 35 passed).
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — exit 0, 2742 passed, 2 skipped.
- `python scripts/ci_surface_gates.py --check` — exit 0. `pixi run --frozen -e pyforge-guild flag-gate-check` — exit 0.
  `pixi run --frozen -e pyforge-guild lint-types` — exit 0. `pixi run --frozen -e site docs-site-validate` — exit 0.
- `git ls-files docs/dashboard/kedro-viz | wc -l` — 0 (atlas 30.1 landed): the AC6 branch that drops the filter entry.
- Group 1's end gate (102.3 + 102.4): `pixi run --frozen -e pyforge-herald pyforge-herald-test` — exit 0, 1984 passed,
  5 skipped; `pixi run --frozen -e site pages-check` — exit 0 with no export (`kedro-viz absent: no tile, no menu
  entry, no pipelines page`).
- A live, read-only rehearsal of the step's selection (`scripts/pages_artifact_download.py --github-env <scratch>`):
  exit 0, `kedro-viz-export: none found; mount skipped`, `KEDRO_VIZ_EXPORT=absent`. The producer's newest successful
  run is `31905522038` (2026-08-15), from before it uploaded an artifact; it has been `paused-manually` since
  2026-08-24 (registry `review_by` 2026-11-01), so no artifact exists yet. `--flag-env` printed `PYFORGE_PAGES_DUTY=1`.
- Not run here: the memlog reconciles, the scoped stamps, `detectors-ci` and `pr-preflight` (the coordinating
  session runs them for the branch); AC7's two dispatched runs (operator, below).

## Named, not fixed here

- `gh run download` versus `actions/download-artifact@v8` with `run-id`: the implementer's; both need `actions: read`.
- How many producer runs to scan for an unexpired artifact (10 is the default this spec names). *(Superseded
  2026-10-15 by the re-review: no run window is scanned; the selection reads the artifact listing by name. See the
  Spec Change Log.)*
- The step's name and the env variable names beyond the three listed.

## Spec Change Log

- 2026-10-14: specced at mint from Epic 102's Story 102.4 text, `spec-pyforge-steward` CAP-168 and the live
  `assemble_pages.py` (which exits 1 on a missing mount) and `site.yml` (the Kedro-Viz neighbour tile). The split —
  steward downloads and exports, herald tolerates and hides — is the 2026-10-14 design decision on the Spec's memlog.
  The implementing session reads the landed atlas 30.1 producer and herald half first.
- 2026-10-15 (implemented, in review; one branch with the rest of the Pages redesign chain). Read first, as the
  mint asked: atlas 30.1 landed (the producer uploads `kedro-viz-export`, 90-day retention, behind
  `pyforge.atlas.viz_export_artifact`; the committed tree is gone and `.gitignore` already names
  `docs/dashboard/kedro-viz/`), and herald 42.2 landed (`assemble_pages.py` decides presence from the directory
  itself, skipping the mount, the redirect, the tile and the menu entry when it is empty or absent). Where the landed
  code differs from the text above, the code is the contract:
  - **The script is `scripts/pages_artifact_download.py`** (beside `pages_build_stamp.py`), on
    `pages.newest_export_run(runs_json, artifacts_json, *, artifact=…) -> int | None`. It lists runs with
    `--json databaseId,createdAt,conclusion` (the conclusion is how AC1 ignores a failed run) and reads each run's
    full `gh api repos/{owner}/{repo}/actions/runs/<id>/artifacts` payload newest-first, stopping at the first live
    `kedro-viz-export` (so the selection runs on recorded JSON, not a `--jq` string). An artifact counts only when
    the API says `expired: false`. It refuses (exit 1) a `--dest` that already holds files rather than clearing it:
    in CI the directory never exists; on a laptop it may hold a local `viz-publish-stage`.
  - **A second artifact mount is a copy of the step.** `--workflow`, `--artifact`, `--dest` and `--env-prefix`
    default to atlas's producer, `kedro-viz-export`, `docs/dashboard/kedro-viz` and `KEDRO_VIZ_EXPORT`; a later
    mount (atlas 30.2's Vizro export into `docs/dashboard/vizro/`) passes its own four. No second artifact name is
    added here.
  - **The flag's exported state.** No Guild step exported `pyforge.steward.pages_duty` before this story (102.2's stamp
    script reads it directly), so the script's `--flag-env` prints `PYFORGE_PAGES_DUTY=1|0` from the env-resolve
    step, and the download step's `if:` reads it. With the flag off the step is skipped; called anyway, the script
    returns before any `gh` call.
  - **Permission and token.** The `build` job gains a job-level `permissions:` block (`contents: read`,
    `pages: write`, `id-token: write`, `actions: read`); the workflow-level block and the `deploy` job are unchanged.
    The step hands `gh` the job's own `${{ github.token }}` as `GH_TOKEN`: no secret is added.
  - **What herald reads.** Herald 42.2 decides presence by the directory and dates the export from its
    `manifest.json`, so `KEDRO_VIZ_EXPORT`, `KEDRO_VIZ_EXPORT_RUN` and `KEDRO_VIZ_EXPORT_AT` are written for the run's
    log and any later reader; no herald file reads them today.
  - **The filter (AC6).** `docs/dashboard/**` left both `paths:` lists (one YAML anchor). One consequence recorded:
    a `steward deploy static` board under `docs/dashboard/<board>/` still lands through a pull request and is still
    copied into the artifact, but its merge no longer triggers a Pages run on its own; the six-hourly schedule or
    `steward pages deploy` publishes it. Stale lines naming the old filter or the folded `docsite-check.yml` lane are
    corrected in `docs/dashboard/README.md`, `docsite/README.md` and `docs/how-to/presentation-deck.md`;
    `pyforge-station-tests.yml`'s steward list gains the script.
  - **AC7 waits on the producer.** No `kedro-viz-export` exists until `kedro-viz-publish.yml` runs once with atlas's
    flag on, and that workflow is `paused-manually` (registry row `kedro-viz-publish`, `review_by` 2026-11-01). The
    `absent` record above stands for the second AC7 run; the `present` run is the operator's after resuming the
    producer.
- 2026-10-15 (the independent review, `review-102-4`, verdict FAIL on five should-fix items; resolved here; where this
  entry and the one above disagree, this one holds):
  - **The filter keeps `docs/dashboard/**` (AC6 reversed).** The mint's premise, "nothing published lives there any
    more", is false against the landed code: `steward deploy static` writes tracked `docs/dashboard/<board>/index.html`,
    the assembler copies it into the artifact, and without the entry a board PR ran no `pages-check` in CI or in
    `pr-preflight` (CAP-159 selects lanes from these paths). The Boundaries' rule that landed facts win applies, so the
    entry stays in both lists and in `test_pages_workflow.py`'s `_EXPECTED_PATHS`; the downloaded exports under it are
    gitignored, so no diff ever touches them. The filter also gains `scripts/pages_*.py` and steward's
    `pyforge/steward/pages.py` (the build runs them; a PR touching only them ran no Pages build). `docs/dashboard/README.md`
    no longer says the directory left the filter.
  - **Only a run on `main` is mounted.** `gh run list` gains `--branch main` and `headBranch`, the script `--branch`
    (default `main`, the `pages.EXPORT_BRANCH` constant), and `newest_export_run` passes over a run on any other branch:
    the producer accepts a dispatch on any ref, and its HTML/JS is published verbatim on the production origin. AC1
    gains the case. `newest_export_run` now also takes a `fetch(run_id)` callable and owns the success filter, the
    branch filter and the newest-first order, so the script no longer repeats them.
  - **GitHub Enterprise.** The download steps hand `gh` the job token as `GH_ENTERPRISE_TOKEN` beside `GH_TOKEN`; a
    runner without `gh` fails the step naming the command (a `FileNotFoundError` is mapped, never a traceback); the GHE
    how-to lists `gh` as a runner prerequisite. Steward 102.5 (the other lane) leaves this step and the script alone.
  - **AC7.** The local rehearsal recorded above is not the dispatched `absent` record: it never exercised the job's
    `actions: read`, the token wiring, `gh`'s repository resolution on a runner or the step's `if:`. The `absent`
    record is the chain PR's own `pages.yml` pull_request run (the PR changes `pages.yml`, so the build runs both
    download steps); the coordinating session fills its id at PR time. The `present` run is steward deferred-work row
    `DW-steward-102-4-1`, keyed to resuming atlas's producer (`kedro-viz-publish`, `paused-manually`, `review_by`
    2026-11-01).
  - **Surface.** `scripts/pages_artifact_download.py` and `docsite/README.md` are on Epic 102's surface
    (`marshal-policy.toml`, widened in 102.3's review). The script's place on spec-pyforge-steward's own surface comes
    with the chain's `bmad-spec` re-derive, beside `scripts/pages_fleet_status.py`.
  - **Nits.** The `build` job's permissions are `contents: read`, `pages: read`, `actions: read` (`configure-pages`
    reads the site; `pages: write` and `id-token: write` belong to `deploy`); the chain PR's run confirms
    `configure-pages` under it. An exit-0 `gh` answer of the wrong shape (a run list that is not a list, an artifacts
    payload that is not an object or has no `artifacts` list) fails naming the argv instead of reading as `absent`. New
    tests: the script's own `read_boolean` (no injected state), the second artifact's present path (`-n`, `-D`,
    `_RUN`), a missing `gh`, the four wrong shapes. `--env-prefix` defaults to `pages.KEDRO_VIZ_ENV_PREFIX`.
    `docs/reference/github-workflows.md`'s `pages.yml` row names 102.4, the downloads and the permissions.
  - **Atlas 30.2's consumer step, per 30.2's review.** A second download step, the same script with
    `--workflow kedro-viz-publish.yml --artifact vizro-static-export --dest docs/dashboard/vizro --env-prefix VIZRO_EXPORT
    --branch main`, the same `if:` and both tokens, runs after the Kedro-Viz step and before `pages-check`
    (`test_pages_export.py::test_the_workflow_mounts_the_vizro_export_the_same_way`). Until atlas 30.2's producer job
    uploads the artifact it takes the absent path. The mount itself is herald's: `assemble_pages.py` copies
    `docs/dashboard/vizro/` under `/dashboard/vizro/` with no vendored-root exemption, as 30.2 asks.
- 2026-10-15 (the re-review, `rereview-group1`: 102.4 NOT RESOLVED on two should-fix items, plus a nit; resolved
  here; where this entry and an earlier one disagree, this one holds):
  - **`gh` is told the host (should-fix).** A token alone does not tell `gh` which host to use: a GitHub Enterprise
    Server runner has no `gh` configuration, so `gh` stopped asking for `GH_HOST`. Both download steps now run
    `export GH_HOST="${GITHUB_SERVER_URL#*://}"` before the script, the form steward 102.5's release step uses, and
    carry `GH_REPO: ${{ github.repository }}` beside `GH_TOKEN` and `GH_ENTERPRISE_TOKEN`, so the `{owner}/{repo}`
    placeholders and `gh run download` resolve without reading git remotes. The GHE how-to's sentence that said the
    token alone authenticates is corrected. Test: `test_pages_export.py::test_both_downloads_name_the_host_that_runs_the_workflow`
    (and the env equality in `test_the_workflow_mounts_the_vizro_export_the_same_way`).
  - **Selection by artifact, not by a run window (should-fix).** The step read only the ten newest successful producer
    runs (`--limit 10`). Atlas 30.2's `changes` job makes one-sided runs (each export job runs only when its own paths
    change), so after ten runs that rebuilt only one export the other live artifact fell out of the window, the step
    read `absent` and the next changed-tree deploy dropped that mount from production with no error. The script now
    lists every page of `gh api repos/{owner}/{repo}/actions/artifacts?name=<artifact>&per_page=100&page=<n>`
    (`pages.export_artifacts_endpoint`; a short page ends the listing, and a listing longer than
    `MAX_ARTIFACT_PAGES` full pages exits 1 rather than reading part of it), then reads the run behind each candidate
    (`gh api repos/{owner}/{repo}/actions/runs/<id>`) newest-first and downloads with `gh run download <id> -n
    <artifact>`. `pages.newest_export_run(artifacts_json, runs_json, *, artifact, workflow, branch)` stays the one
    owner of the rule: an artifact counts when its name matches, `expired` is `false`, `workflow_run.head_branch` is
    the branch and the run is not a fork's (`head_repository_id` equals `repository_id`); candidates are read by newest
    `created_at`; the run must be `--workflow`'s (`path` is `.github/workflows/<workflow>`), concluded `success` and
    on the branch, which keeps the old guarantees (only the producer's successful runs on `main`). `--limit` is gone.
    `<PREFIX>_AT` is the chosen run's `created_at`, as before. Every `gh` error and every wrong-shape answer (a
    listing that is not an object or has no `artifacts` list, a run payload that is not an object or has no `path`)
    still exits 1 naming the argv, never `absent`. Tests (all in `test_pages_export.py`, rewritten on artifact-listing
    JSON): `test_ac1_a_live_export_behind_one_sided_runs_is_still_selected`,
    `test_ac2_the_live_export_behind_ten_one_sided_runs_is_downloaded` (the script never calls `gh run list`),
    `test_ac2_every_page_of_the_listing_is_read`, `test_a_listing_longer_than_the_page_cap_fails_and_is_never_truncated`,
    `test_ac1_an_artifact_another_workflow_uploaded_is_never_mounted`, `test_ac1_a_fork_s_run_is_never_mounted`, the
    AC1–AC3 cases and the five wrong shapes; `test_pages_export_flag_states.py` reads the listing call first.
  - **The Never bullet (nit)** is annotated with the review's ruling on `GH_ENTERPRISE_TOKEN` and
    `vizro-static-export`, and "Named, not fixed here"'s run-window item is marked superseded.
  - **Nit d** (`scribe capture --type project` for `DW-steward-102-4-1`) is the coordinating session's at session
    close; no capture is run from a builder.
- 2026-10-15 (the lane-B re-review, `rereview-laneb`: 102.4 RESOLVED; two nits done here):
  - **A live artifact whose run cannot be read is a wrong shape, never a skip.** `newest_export_run` raises
    `ValueError` for a name-matched, unexpired artifact with no readable `workflow_run.id`, and the script's listing
    reader exits 1 naming the listing argv before selection; skipping every such artifact would have read as `absent`
    and dropped the mount. Tests: `test_ac1_a_live_artifact_without_a_readable_run_is_a_wrong_shape_never_a_skip`,
    `test_a_live_artifact_without_a_readable_run_fails_naming_the_listing`.
  - **AC1 is annotated in place** with the selection-by-artifact rule (the AC is the oracle), and so is steward
    `epics.md`'s Story 102.4 When line.
- 2026-10-17 (AC7 recorded): both dispatched records are filled in § AC7 records: `present` `39020410506`, `absent` `38831558913`. `DW-steward-102-4-1` is closed. The producer had been `paused-manually` until the operator resumed every CI surface (#2247); its first run then failed on stale stub credentials, which atlas Story 32.1 (#2248) fixed.
