---
title: "102.1: The Pages workflow is steward's and fires only on the published inputs"
type: 'feature'
created: '2026-10-14'
status: 'ready-for-dev'
baseline_revision: '8ef404d388d1bdafac6aa0d96a8f626f97cad47a'
flag-exempt: detector-or-gate   # a workflow's `on:` block, checkout depth and sparse paths are evaluated by GitHub before any step can read a flag; the station read Story 99.2's gate sweep and 99.6's canary the same way (spec-feature-flag-governance Q2). The flag pyforge.steward.pages_duty is minted by Story 102.2, whose steps are the first a flag can gate.
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - docs/dreams/pyforge-herald.md
  - _bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/brainstorm-intent.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/design-thinking-pyforge-herald-pages-redesign-2026-10-13.md
  - .github/workflows/dashboard.yml
  - .github/workflows/docsite-check.yml
  - docs/governance/ci-surfaces.yaml
  - scripts/ci_surface_gates.py
  - scripts/pixi_version_registry.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/preflight_ci.py
  - src/shared/packages/pyforge-steward/tests/unit/test_preflight_selection.py
  - src/shared/packages/pyforge-steward/tests/meta/test_invariants.py
  - src/shared/packages/pyforge-steward/tests/meta/test_workflow_path_filters_match.py
  - docsite/tools/assemble_pages.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `.github/workflows/dashboard.yml` deploys the Pages artifact on every push to `main`. Measured
2026-10-13 (API `total_count`): 1,342 runs since 2026-09-13, 720 deploys, 621 cancelled, 1 failure, about 24 deploys a
day against about 1,330 first-parent pushes in 30 days (up to 176 in one day); a deploy sat in `waiting` from
2026-10-06 to 2026-10-12 with 199 cancelled runs behind it. The build job checks out the whole repository with
`fetch-depth: 0`, so every run clones `presentations/` (658 MB) with history, and nothing in the build needs history.
The file sits on `spec-pyforge-herald`'s surface while steward owns everything around it: the deploy duty, the budget,
the `dashboard` registry row with its `stuck_rules` (CAP-166), and the pre-push lane selection that reads the workflow
files (CAP-159, Story 71.2). The operator ruled 2026-10-13: steward owns the duct, herald the content, and the file
becomes `pages.yml`, superseding herald's 2026-09-27 ruling that it keeps its `dashboard.yml` path. A replay of the
published-inputs filter over the same 30 days would have deployed 132 times (brainstorm-intent § The finding; design
thinking P-C).

**Approach:** One `git mv`, one trigger, one checkout shape, and every site that names the file follows.

- **The rename.** `git mv .github/workflows/dashboard.yml .github/workflows/pages.yml`; `name: Pages`; the header
  comment says what the file is now: steward's duct (this Spec, CAP-168), herald's content (`pages-build`,
  `pages-check`, `docsite/`, `docs-site/`, `/herald/`), the one `deploy-pages` caller (herald AD-21), no bot commit
  on `main`. The jobs, their CAP-166 fragments (`vars.PAUSE_DASHBOARD`), the `Resolve Pages host env` step and the
  deploy job are not otherwise changed in this story: Story 102.2 reshapes the jobs and renames the switch, 102.5
  drops the host-env step.
- **The trigger.** `on.push.branches: [main]` with `paths:` exactly `docs/tutorials/**`, `docs/how-to/**`,
  `docs/reference/**`, `docs/explanation/**`, `docs/index.md`, `docs/404.md`, `docs/map.yaml`, `docs/dashboard/**`,
  `docs-site/**`, `docsite/**`, `presentations/**`, `.github/workflows/pages.yml`; `workflow_dispatch`; one weekly
  `schedule` (the design-thinking skeleton P-A's `17 6 * * 1`, so the dossier's stats are never more than a week
  behind the tree). No `pull_request` trigger yet and no six-hourly schedule: both need Story 102.2's no-op deploy
  skip, or a six-hourly schedule would deploy six times a day. `docs/dashboard/**` stays until atlas Story 30.1
  deletes the committed Kedro-Viz tree (Story 102.4 removes the entry then).
- **The checkout.** `actions/checkout@v7` with `fetch-depth: 1` and a sparse checkout that keeps everything but
  `presentations/**`, then re-admits `presentations/*/project/*.html` (the standalone infographics and deck pages the
  build serves verbatim); nothing under `presentations/*/src/pptx` reaches the runner. The first check of the story is
  that `pages-check` needs no history and no other `presentations/` file: run it locally on a `--depth 1` clone with
  that sparse set and record the exit in this spec; if a build step reads `git log` (the brainstorm's
  `deck_versions` doubt) or another `presentations/` path, the story widens the sparse set or the depth by the least
  amount and records why, never silently.
- **The registry.** The rows `dashboard`, `dashboard.build` and `dashboard.deploy` in `docs/governance/ci-surfaces.yaml`
  keep their ids, switch (`PAUSE_DASHBOARD`) and `stuck_rules`, and their `workflow:` field moves to
  `.github/workflows/pages.yml`, so `scripts/ci_surface_gates.py --check` stays green (a row whose workflow file does
  not exist is a finding, Story 99.7). Story 102.2 renames the ids and the switch. The row edit is a governance act
  and lands with this story's PR.
- **Every other site.** `scripts/pixi_version_registry.py` registers `pages.yml setup-pixi` in place of
  `dashboard.yml setup-pixi` (same regex, same `kind="exact"`); `tests/meta/test_invariants.py` reads `pages.yml`
  where it read `dashboard.yml`; `tests/unit/test_ci_status.py`'s fixtures may keep the old name (they are recorded
  `gh` output) or move, the implementer's call, recorded. Every tracked file outside dated log entries that names
  `.github/workflows/dashboard.yml` or `Dashboard (GitHub Pages)` is updated to the new name: `docs/MAP.md`,
  `docs/dashboard/README.md`, `docs/explanation/enterprise-deployment.md`, `docs/how-to/README.md`,
  `docs/how-to/deploy-the-docs-site-to-github-enterprise-pages.md` (the name only; its flag step is Story 102.5's),
  `docs/how-to/github-actions-recipe-ci.md`, `docs/how-to/presentation-deck.md`, `docs/reference/github-workflows.md`,
  `docs/governance/flag-inventory/pyforge-herald.md`, `.github/workflows/docsite-check.yml` (its header comment;
  the file itself folds in under 102.2), `.github/workflows/kedro-viz-publish.yml`'s and `platform-ci.yml`'s
  comments, `docsite/tools/pages_second_host.py`'s docstring, `src/platform/tests/test_console_parity_homes.py`,
  `src/shared/packages/pyforge-herald/src/pyforge/herald/webhook.py` and
  `tests/meta/test_pages_artifact.py` where they name the file as current state. Each of those files has its own
  governing Spec (`git grep -l dashboard.yml` is the list; `scripts/.spec-surface-baseline.json` names the governor);
  every one is a co-governor reconcile on that Spec's memlog, then one scoped stamp each. Dated log entries (Dreams,
  memlogs, currency sections, `docs/intake/`) keep the historical name.
- **The surface move.** `spec-pyforge-steward`'s `surface:` already names `.github/workflows/pages.yml` (declared at
  the 2026-10-14 mint, ahead of the file); this story's surface reconcile names the file and stamps
  `--spec pyforge-steward/spec-pyforge-steward`. The baseline entry for `.github/workflows/dashboard.yml` under
  `pyforge-herald/spec-pyforge-herald` leaves with the file: a reconcile line on `spec-pyforge-herald`'s memlog and a
  scoped stamp there, in the same PR (the herald SPEC's `surface:` drop is the coordinator's 2026-10-14 edit).
- **The preflight.** Nothing to code: `preflight_ci` reads `.github/workflows/*.yml` at run time (Story 71.2), so the
  `pages-check` lane now also fires on `pages.yml`'s `paths:`. A test in `test_preflight_selection.py` pins it: a diff
  under `docs/tutorials/` fires `pages.yml`, a diff under `docs/dreams/` does not (the published-inputs filter drops
  exactly the churn the shelf loader excludes: `docs/dreams` 515 touches and `docs/governance` 143 in the replay).

Ledger key: `102-1-the-pages-workflow-is-steward-s-and-fires-only-on-the-published-inputs`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / —.

### Living CAP citations

- **`spec-pyforge-steward` CAP-168** (FR-41): the file on this surface, the published-inputs trigger, the shallow
  sparse checkout, the registry rows following the file. Extends CAP-166 (the `dashboard` row and its `stuck_rules`
  travel with the file); works with CAP-159 (the lane selection reads the workflows, never a second list).
- **AD-4 as amended 2026-10-14**: the deploy's mutation is one `deploy-pages` run of this workflow; nothing else in
  this story touches the duty. **AD-1**: no new logic — a rename, a filter, a checkout shape.
- **herald AD-21** (one Pages artifact, one deploy caller): kept; `spec-pyforge-herald:CAP-52` and `:CAP-56` are the
  content owner's and are not edited.
- **Origin.** Dream `docs/dreams/pyforge-steward.md`, the 2026-10-13 (the Pages duct) entry; the herald Dream's
  2026-10-13 lead entry (M1 trigger, M2 ownership); operator rulings 2026-10-13 (memlog, decision by user 2026-10-14).

## Acceptance Criteria

- **AC1 — The rename.** `.github/workflows/pages.yml` exists and `.github/workflows/dashboard.yml` does not;
  `git log --follow --oneline .github/workflows/pages.yml` reaches the pre-rename history (a `git mv`, not a copy);
  `name: Pages`; the header comment names steward as the duct's owner, herald as the content's, and the one
  `deploy-pages` caller.
- **AC2 — The trigger.** A test parses `pages.yml` and asserts `on.push.branches == ["main"]`, `on.push.paths` equals
  the twelve-entry list above in any order and nothing else, `on.workflow_dispatch` is present, `on.schedule` holds
  exactly one weekly cron, and no `pull_request` key exists.
- **AC3 — The checkout.** The build job's `actions/checkout` carries `fetch-depth: 1` and a sparse configuration;
  on a local `git clone --depth 1` with that sparse set applied, `find presentations -path '*/src/pptx/*'` is empty,
  every tracked `presentations/*/project/*.html` is present, and `pixi run --frozen -e site pages-check` exits 0 —
  the command, the clone shape and the exit are recorded in this spec's Auto Run Result.
- **AC4 — The registry.** `docs/governance/ci-surfaces.yaml`'s `dashboard`, `dashboard.build` and `dashboard.deploy`
  rows read `workflow: .github/workflows/pages.yml` with ids, `switch`, `state` and `stuck_rules` unchanged;
  `python scripts/ci_surface_gates.py --check` exits 0; `tests/meta/test_workflow_path_filters_match.py` and the
  other workflow meta-tests are green; `pixi run --frozen -e pyforge-guild pixi-version-check` exits 0 with the
  `pages.yml setup-pixi` site registered and no `dashboard.yml` site left.
- **AC5 — Every other site.** `git grep -n 'workflows/dashboard.yml'` over tracked files returns only dated log
  entries (Dreams, memlogs, currency sections, `docs/intake/`); `tests/meta/test_invariants.py` reads `pages.yml`.
- **AC6 — The preflight.** In `tests/unit/test_preflight_selection.py`, `select_lanes` over a diff touching
  `docs/tutorials/<x>.md` selects `pages-check` with `pages.yml` among its firing sites, and over a diff touching
  only `docs/dreams/<x>.md`, `pages.yml` is not a firing site.
- **AC7 — Governance.** `spec-pyforge-steward`'s memlog carries the surface reconcile naming
  `.github/workflows/pages.yml` and every co-governed path this story edits; `spec-pyforge-herald`'s memlog carries
  the line that `.github/workflows/dashboard.yml` left its surface; each named Spec is stamped scoped;
  `pixi run --frozen -e pyforge-guild spec-surface-check` exits 0; the PR carries the `maintenance` label.
- **AC8 — Done when (read after landing, operator).** Thirty days after the merge, the API `total_count` of
  `pages.yml` runs that deployed is under 150 and `pyforge steward ci status` has not read `stuck` for the Pages
  surface on a cancelled streak of five (today 720 deploys and 621 cancelled per 30 days; the replay says 132). The
  reading goes into this spec's Auto Run Result when taken.

## Boundaries & Constraints

**Always:**
- The rename is a `git mv`; the jobs, steps and fragments keep their text except where this story names a change.
- The twelve trigger paths are exactly the published inputs the brainstorm and the herald Dream name; a path is added
  only with a reason recorded here and on the memlog.
- Every file this story edits outside steward's surface is a co-governor reconcile on its Spec's memlog, then a
  scoped stamp for that Spec; never a bare `--write-baseline`.
- The registry edit changes `workflow:` only.

**Never:**
- Do not add `pull_request`, a six-hourly schedule, the no-op skip, the artifact download, the release asset or a
  `pages` duty (Stories 102.2–102.5).
- Do not rename the `PAUSE_DASHBOARD` switch or the registry ids (102.2), delete `docsite-check.yml` (102.2), or edit
  `kedro-viz-publish.yml` beyond its comment (atlas's file).
- Do not touch `docsite/**`, `docs-site/**` or any herald code beyond the names this story corrects.
- Do not widen `fetch-depth` or the sparse set without recording what needed it.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| docs edit | push to `main` touching `docs/how-to/x.md` | `pages.yml` runs | — |
| Dream edit | push touching only `docs/dreams/x.md` | no run | — |
| governance edit | push touching only `docs/governance/x.yaml` | no run | — |
| deck source edit | push touching `presentations/<slug>/src/pptx/x` | a run (`presentations/**` fires); the checkout omits `src/pptx` | — |
| manual | `workflow_dispatch` | a run, pauses ignored (CAP-166) | — |
| weekly | the Monday cron | a run; deploys as today (the skip is 102.2's) | — |
| paused | `PAUSE_DASHBOARD=true` | both jobs skip, as today | — |
| history needed | a build step reads `git log` | widen depth by the least amount, record why | the story does not land silent |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-168 (FR-41), minted 2026-10-14.
- Architecture: AD-4 amended 2026-10-14 (see the spine's § Currency reconciliation — 2026-10-14 (the Pages duct)).
- Dream: `docs/dreams/pyforge-steward.md` § Realization log, the 2026-10-13 (the Pages duct) entry; the herald Dream's
  2026-10-13 (the Pages deployment, redesigned) entry.
- Epic: Epic 102, Story 102.1.
- Ledger key: `102-1-the-pages-workflow-is-steward-s-and-fires-only-on-the-published-inputs`.
- Ledger status at mint: `backlog`.
- Deps: none. `marshal factory dispatch` stamps `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."102"`.
- Flag: `flag-exempt: detector-or-gate` (reason in the frontmatter).

## Epic excerpt

**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-steward CAP-168 (FR-41), extending CAP-166, with CAP-159; AD-4 (amended 2026-10-14), AD-1; herald AD-21 kept • flag-exempt `detector-or-gate`

**Given** `dashboard.yml` on herald's surface, firing on every push to `main` (720 deploys, 621 cancelled in 30 days)
with a full-history checkout
**When** the file becomes `.github/workflows/pages.yml` on steward's surface with the published-inputs filter,
`workflow_dispatch`, one weekly cron, `fetch-depth: 1` and a sparse checkout, and every site that names it follows
**Then** `ci_surface_gates.py --check`, `pixi-version-check`, the workflow meta-tests and `spec-surface-check` exit 0,
`pages-check` exits 0 on the shallow sparse clone, and the preflight fires `pages-check` on a tutorials edit and not on
a Dream edit
**And** thirty days on, deploys per 30 days are under 150 and no cancelled streak reaches five

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`;
  MRS-GATE-010 binding; it runs `tests/unit/test_preflight_selection.py` (AC6), `tests/meta/test_invariants.py` (AC5)
  and `tests/meta/test_workflow_path_filters_match.py` (AC4)).

**Run before the push (not dispatch gates):**
- `python scripts/ci_surface_gates.py --check` — expected: exit 0 (AC4).
- `pixi run --frozen -e pyforge-guild pixi-version-check` — expected: exit 0 (AC4).
- `git grep -n 'workflows/dashboard.yml' -- ':(exclude)_bmad-output' ':(exclude)docs/dreams' ':(exclude)docs/intake' ':(exclude).claude/memory'` — expected: no output (AC5).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles and the scoped
  stamps (AC7).
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

**Manual, recorded in this spec (AC3):**
- `git clone --depth 1 --filter=blob:none --sparse <repo> <dir>`, `git sparse-checkout set --no-cone '/*' '!/presentations/' '/presentations/*/project/*.html'` (or the equivalent the implementer settles on), then
  `pixi run --frozen -e site pages-check` — expected: exit 0; `find presentations -path '*/src/pptx/*'` empty.

**Operator, after landing (AC8):**
- `gh api 'repos/rxm7706/local-recipes/actions/workflows/pages.yml/runs?created=>=<merge date>&per_page=1' --jq .total_count`
  and `pixi run --frozen -e pyforge-guild pyforge steward ci status` thirty days after the merge — expected: deploys
  under 150; no `stuck` verdict from a cancelled streak.

## Named, not fixed here

- The sparse-checkout mode (cone or pattern) and the exact `actions/checkout` inputs: the implementer's, held to AC3.
- The weekly cron minute and hour: any Monday slot; P-A's `17 6 * * 1` is the default.
- Whether `tests/unit/test_ci_status.py`'s recorded fixtures keep the old workflow name: the implementer's, recorded.

## Spec Change Log

- 2026-10-14: specced at mint from Epic 102's Story 102.1 text, `spec-pyforge-steward` CAP-168 and the live
  `dashboard.yml`. The measured numbers are the brainstorm's and the design-thinking doc's (2026-10-13). The
  implementing session reads the live workflow and registry first and follows them where they differ from the shape
  quoted here.
