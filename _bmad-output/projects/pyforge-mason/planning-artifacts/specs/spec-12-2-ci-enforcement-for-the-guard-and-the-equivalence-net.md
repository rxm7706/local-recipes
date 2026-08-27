---
title: CI enforcement for the guard and the equivalence net
type: feature
created: '2026-08-27'
status: ready
updated: '2026-08-27'
baseline_revision: cc8b3b2b1c09d6e56a5aebf752e25f507c846571
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-conda-forge-expert-rebuild/campaign-state.yaml
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-6-2-the-divergence-and-endgame-guard-proven-red-first.md
warnings: []
deferred: []
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
