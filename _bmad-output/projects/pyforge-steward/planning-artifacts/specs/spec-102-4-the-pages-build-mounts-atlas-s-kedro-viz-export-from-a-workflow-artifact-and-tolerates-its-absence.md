---
title: "102.4: The Pages build mounts atlas's Kedro-Viz export from a workflow artifact and tolerates its absence"
type: 'feature'
created: '2026-10-14'
status: 'ready-for-dev'
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
- **herald AD-21**: the mount prefix `/dashboard/kedro-viz/` keeps its URL; the content is atlas's, served by herald's
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
  and for an expired artifact; ignores runs whose `conclusion` is not `success`.
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
- Do not add a token, a secret or a second artifact name.
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
- Architecture: AD-1, AD-8; herald AD-21 (the mount's URL).
- Dream: `docs/dreams/pyforge-steward.md` § Realization log, the 2026-10-13 (the Pages duct) entry.
- Epic: Epic 102, Story 102.4.
- Ledger key: `102-4-the-pages-build-mounts-atlas-s-kedro-viz-export-from-a-workflow-artifact-and-tolerates-its-absence`.
- Ledger status at mint: `backlog`.
- Deps: S-102.2; atlas Story 30.1 (cross-station, named in `Deps:`, never a blocked row); herald Story 42.2 (CAP-60, the Kedro-Viz mount tolerates absence)
  (the coordinator fills the key). `marshal factory dispatch` stamps `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."102"`.
- Flag: `pyforge.steward.pages_duty` (Story 102.2's).

## Epic excerpt

**Type:** feature • **Effort:** S • **Deps:** S-102.2; atlas Story 30.1; herald Story 42.2 (CAP-60, the Kedro-Viz mount tolerates absence) • **FR/AD:** spec-pyforge-steward CAP-168 (FR-41); AD-1, AD-8; herald AD-21 • flag: `pyforge.steward.pages_duty` (Story 102.2's)

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

## Named, not fixed here

- `gh run download` versus `actions/download-artifact@v8` with `run-id`: the implementer's; both need `actions: read`.
- How many producer runs to scan for an unexpired artifact (10 is the default this spec names).
- The step's name and the env variable names beyond the three listed.

## Spec Change Log

- 2026-10-14: specced at mint from Epic 102's Story 102.4 text, `spec-pyforge-steward` CAP-168 and the live
  `assemble_pages.py` (which exits 1 on a missing mount) and `site.yml` (the Kedro-Viz neighbour tile). The split —
  steward downloads and exports, herald tolerates and hides — is the 2026-10-14 design decision on the Spec's memlog.
  The implementing session reads the landed atlas 30.1 producer and herald half first.
