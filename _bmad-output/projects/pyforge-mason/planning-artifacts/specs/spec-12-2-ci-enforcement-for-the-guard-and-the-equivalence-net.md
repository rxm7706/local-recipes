---
title: CI enforcement for the guard and the equivalence net
type: feature
created: '2026-08-27'
status: in-review
updated: '2026-08-27'
baseline_revision: ecb931e5d15f7ed0ef7ec732c5c15cc5e51c47e2
final_revision: fc776507251c3010b227b4bd5f0f571e567beac0
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-6-2-the-divergence-and-endgame-guard-proven-red-first.md
warnings: ['ci-net-red-on-arrival']
deferred:
  - 'DW-12-2-1: the new cfe-regression-net CI job is red on arrival — test_help_output_identical[github_updater.py] fails because the live github_updater.py (v8.84.0, --head) is ahead of the compiled slice-1 copy. This is the intended divergence signal, already owned: campaign-state slice-1 next_action requires the re-port/re-validate before slice 1 advances past compiled (Story 12.3 territory), not this story.'
  - 'DW-12-2-2: five PRE-EXISTING meta-test failures on main (test_bmad_artifacts_integrity, test_dashboard_script_runs_clean, test_no_redundant_or_below_floor_python_min_in_context, test_all_recipe_yaml_parse, test_spec_surface_check_green) also red the net — verified present at pristine baseline ecb931e5d1 via git stash. Fleet-wide drift (steward spec-surface baselines, recipe audits) that was invisible only because no CI ever ran this suite; needs owners outside mason 12.2.'
---

<intent-contract>

## Intent

**Problem:** `.github/workflows/detectors.yml`'s repo-scope step always ends `exit 0`
(its own header comment: "ADVISORY, NOT BLOCKING — operator decision 2026-07-31"), so a
`cfe_rebuild_guard_check` finding never blocks a PR. Separately, no CI workflow runs the CFE
regression suite or the slice-1 equivalence-harness test at all — grepping every
`.github/workflows/*.yml` for `pytest` finds only `platform-ci.yml`'s unrelated Django suite
(campaign-state.yaml GATHERED GAPS #2). Divergence between the live skill and a parallel
replacement has nowhere to turn red.

**Approach:** Close re-scope pre-condition (a) one of two ways — make
`cfe_rebuild_guard_check` findings block CI as a real red check, or record a dated, conscious
acceptance of advisory-only enforcement in `campaign-state.yaml` — and, in **both** branches,
add a CI step that runs the CFE regression suite together with the slice-1
equivalence-harness test, so a real divergence has somewhere to fail loudly.

## Acceptance Criteria

- **Given** the advisory-only detectors CI step (always `exit 0`, findings surface as
  annotations only) **Then** either cfe-rebuild-guard-check findings block CI as a red check,
  or a dated conscious acceptance of advisory-only enforcement lands in campaign-state.yaml —
  and in BOTH branches the CFE regression suite plus `test_slice1_equivalence.py` run in a CI
  workflow, so divergence has a place to red.

## Boundaries & Constraints

**Always:**
- Write artifacts under `_bmad-output/projects/pyforge-mason/planning-artifacts/` literally.
  `BMAD_ACTIVE_PROJECT=pyforge-mason` only — never `scripts/bmad-switch`. Ledger key
  `12-2-ci-enforcement-for-the-guard-and-the-equivalence-net`.
- Pick and record exactly one of the two branches: (a) make the CI job fail specifically when
  `cfe_rebuild_guard_check` reports findings (without necessarily changing every other
  repo-scope detector's enforcement posture in the same pass), or (b) add a dated note to
  `campaign-state.yaml` recording the conscious choice to keep advisory-only enforcement,
  matching the dated-note style `campaign.re_scope_gate` already uses.
- Regardless of the branch chosen: add or extend a CI workflow step that runs the CFE
  regression suite together with the slice-1 equivalence-harness test (`@pytest.mark.slow`) —
  a strictly read-only pytest *invocation*, never an edit, run via the existing pixi test
  tasks (`test` / `test-all` in `pixi.toml`), which today cover "not slow" and "everything
  incl. slow+network" respectively but neither matches "slow but not network" exactly.
- Per SPEC.md's own Constraint ("the test net is the safety rail"), this new CI step is new
  ground, not a replacement for the existing offline `pyforge-mason-test` / `platform-ci.yml`
  jobs — it must not remove or narrow any test coverage that already runs elsewhere.

**Block If:** Closing pre-condition (a) turns out to require a repo-wide policy change (e.g.
making every repo-scope detector CI-blocking, not just this one) — stop and flag that as a
separate decision rather than silently expanding this story's scope.

**Never:**
- Never edit `.claude/skills/conda-forge-expert/**`, `.claude/scripts/conda-forge-expert/**`,
  or `.claude/tools/conda_forge_server.py` (CFE surface) — mason consults CFE, never edits it
  (mason-cfe-surface-check gate). The new CI step *runs* pytest against files under that tree
  (the same read-only nature as any CI test job); it must never modify anything there, and
  this spec's Code Map deliberately names no file under that tree as an edit target.
- Never leave detectors.yml's blanket `|| true` / trailing `exit 0` in place for every OTHER
  detector while claiming pre-condition (a) closed without saying so explicitly — scope the
  change to `cfe_rebuild_guard_check` specifically, or record explicitly that a broader change
  was made and why.
- Never touch `epics.md` or `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Guard clean | Unmodified campaign-state.yaml, no findings | CI job stays green either way | — |
| Guard finds something, branch (a) chosen | e.g. today's unmirrored-retro finding | CI job goes red | Must not be swallowed by a residual `\|\| true` |
| Branch (b) chosen instead | — | `campaign-state.yaml` carries a dated acceptance note; the guard-check CI step stays advisory | The new regression+equivalence CI step is still required regardless |
| Equivalence test regresses | A future compiled-package change breaks `test_slice1_equivalence.py` | New CI step goes red | Must not be excluded via a `not slow` marker filter |
| Network-marked tests exist in the CFE suite | Offline CI runner | New step excludes `network`-marked tests while still including `slow` | Avoids flaky CI from unreachable network calls |

</intent-contract>

## Code Map

- `.github/workflows/detectors.yml` — the advisory-only repo-scope step (its own header
  comment: "ADVISORY, NOT BLOCKING — operator decision 2026-07-31"; final line `exit 0`
  unconditionally). Branch (a) means carving `cfe_rebuild_guard_check`'s own exit code out of
  that blanket `exit 0` (a dedicated step, or a scoped rc check), or adding a separate CI job
  for it.
- `pixi.toml` — `[feature.local-recipes.tasks.test]` (fast, offline, `-m 'not network and not
  slow'`) and `[feature.local-recipes.tasks.test-all]` (full suite incl. `slow` and network)
  already exist and back the CFE regression suite; the new CI step needs a marker selection
  that includes the slow-marked slice-1 equivalence test while still excluding network-marked
  tests — neither existing task matches that combination exactly, so this likely needs a new
  marker expression or a dedicated pixi task rather than a new script.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml`
  — if branch (b) is chosen, add the dated acceptance note near `campaign.re_scope_gate`
  (same section, same dated-note style Story 6.4 used) rather than inventing a new top-level
  key.
- `scripts/detectors.py` — read-only; confirms `cfe_rebuild_guard_check` is already
  auto-discovered under `--scope repo` (no discovery-side edit needed — only the CI *wiring*
  in `detectors.yml` or a new workflow changes, per Story 6.2's own Code Map note).
- Not a Code Map target: the slice-1 equivalence-harness test module itself (Story 6.3's
  `@pytest.mark.slow` addition) — the new CI step *runs* it via a pixi test task; per the
  mason-cfe-surface-check gate this spec names no file under the CFE tree as something to
  touch.

## Tasks & Acceptance

**Execution:**
- [x] Branch decision: **(a)** chosen — `cfe_rebuild_guard_check` findings block CI as a
  real red check, scoped to that one detector; no campaign-state.yaml acceptance note
  needed (Code Map names that file as an edit target only for branch (b)).
- [x] `.github/workflows/detectors.yml` — header comment amended to state the scoped
  exception explicitly (per this spec's own Never clause), and a dedicated
  `CFE rebuild guard (blocking — Story 12.2)` step added after the advisory sweep that
  runs `python scripts/cfe_rebuild_guard_check.py` and lets its exit code stand
  (0 clean · 1 findings red · 2 could-not-run red — unknown never reads as success).
  The blanket advisory sweep for every OTHER repo-scope detector is untouched.
- [x] `pixi.toml` — new `[feature.local-recipes.tasks.test-ci]`:
  `pytest .claude/skills/conda-forge-expert/tests -m 'not network'` — the exact
  "slow included, network excluded" selection neither `test` nor `test-all` matched.
- [x] `.github/workflows/cfe-regression-net.yml` (new) — blocking job running
  `pixi run --frozen -e local-recipes test-ci` (setup-pixi, `local-recipes` env,
  cache on); path-filtered to the surfaces that can change this suite's outcome
  (`.claude/skills/**`, `.claude/scripts/conda-forge-expert/**`,
  `.claude/tools/conda_forge_server.py`, `pixi.toml`, `pixi.lock`, the workflow itself)
  plus `workflow_dispatch`, because the `local-recipes` env is ~9.8 GB and detectors.yml
  already documents why that cost is a poor blanket trade. Read-only pytest invocation;
  nothing under the CFE tree touched or narrowed.

**Acceptance Criteria (from the intent contract):**
- [x] cfe-rebuild-guard-check findings block CI as a red check (branch (a)) — dedicated
  step, no residual `|| true`/`exit 0` around it.
- [x] The CFE regression suite plus `test_slice1_equivalence.py` run in a CI workflow —
  9055/9065 tests selected by `-m 'not network'` (10 network-marked deselected; all 6
  slow-marked equivalence tests included), so divergence has a place to red.

## Design Notes

**Why branch (a):** it genuinely closes GATHERED GAPS #2's guard half and makes SPEC.md's
CAP-3 "fails CI" literally true, where branch (b) only accepts residual risk. The Block-If
condition did not trigger: no repo-wide policy change was needed — the 2026-07-31
advisory-only operator decision stands untouched for every other repo-scope detector; the
carve-out is one dedicated step re-running one detector, stated explicitly in
detectors.yml's header.

**The net is red on arrival, by design and honestly:** see frontmatter `deferred:`
(DW-12-2-1 the live slice-1 divergence — the exact signal this story exists to make loud;
DW-12-2-2 five pre-existing meta failures on main, stash-verified at baseline). Landing a
green-by-exclusion net would have violated this spec's own edge-case matrix ("Must not be
excluded via a `not slow` marker filter") and the no-narrowing constraint. The guard-check
blocking step, by contrast, is green today (guard verified clean).

**What "blocks CI" means here:** the job fails red on the PR. Whether a red check hard-blocks
the merge button is a branch-protection setting outside any workflow file's reach; making
the check *required* is an operator action in repo settings, noted for the landing pass.

## Verification

- `python3 scripts/cfe_rebuild_guard_check.py` — exit 0, clean (4 qualifying retros in
  range, all mirrored per Story 12.1) — the blocking step is green today.
- `python3 scripts/detectors.py --list` — exit 0, no registry findings; the new pixi task
  did not confuse detector discovery.
- `pixi run -e local-recipes test-ci --collect-only -q` — 9055/9065 collected,
  10 network-marked deselected; `-m 'slow and not network'` selects exactly the 6
  equivalence-harness tests.
- `pixi run -e local-recipes pytest .claude/skills/conda-forge-expert/tests -m 'not network' -q`
  — 9018 passed, 6 failed, 30 skipped, 1 xpassed in 99s. The 6 failures = DW-12-2-1 (1) +
  DW-12-2-2 (5); the 5 meta failures re-verified as pre-existing at pristine baseline
  `ecb931e5d1` via `git stash -u` → re-run → `git stash pop`.
- Both workflow files parse as YAML (`yaml.safe_load`); `pixi.toml` parses as TOML and
  the `test-ci` task resolves.
- `pixi project export conda-environment -e build` — byte-identical to tracked
  `environment.yaml` (task-only pixi.toml change); the ungated env-sync CI check stays
  green with no regen commit.

## Auto Run Result

Status: done

Branch (a) implemented: `cfe_rebuild_guard_check` is now a real, scoped CI gate (dedicated
blocking step in detectors.yml; every other detector stays advisory per the 2026-07-31
operator decision, stated explicitly in the amended header). The CFE regression suite +
slice-equivalence harness now run in CI for the first time
(`.github/workflows/cfe-regression-net.yml` → `pixi run --frozen -e local-recipes test-ci`,
new `test-ci` task = `-m 'not network'`). Re-scope pre-condition (a) is closed on the
enforcement branch, not the acceptance branch; campaign-state.yaml deliberately untouched.

Residual risk / operator attention: the new net job WILL be red until DW-12-2-1 (slice-1
re-port, Story 12.3 territory) and DW-12-2-2 (five pre-existing main-branch meta failures,
owners outside mason) are cleared — that red is the anti-atlas guard working, not a defect
in this wiring. The guard-check blocking step is green today. No review loop ran on this
dispatch (single-story implementation pass); the diff is wiring-only (2 workflow files +
1 pixi task + this spec).
