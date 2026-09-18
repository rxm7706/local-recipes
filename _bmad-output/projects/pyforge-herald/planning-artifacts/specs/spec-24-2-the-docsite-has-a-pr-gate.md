---
title: '24.2: The docsite has a PR gate'
type: 'feature'
created: '2026-09-18'
status: 'in-progress'
baseline_revision: 'f9f95c6036dd23eb53f0cc93ef4241343a397070'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** no `pull_request`-triggered workflow and no `pr-preflight` leg references `docsite` or `site-check` (verified 2026-09-18: `dashboard.yml` runs the build on `push: branches: [main]` only, and `pyforge-herald-test` has zero coverage of `docsite/`), so 23.5's 296-line family-page change merged with every gate green

**Approach:** a PR that touches the docsite runs `build.py --check` + `site-check` before merge, locally and in CI

## Boundaries & Constraints

**Always:**
- a fixture regression (a family-page template with an unrendered Jinja tag) reds the lane and `main` is green, `pr-preflight` predicts the lane, and `dashboard.yml` is still the only `deploy-pages` caller
- the lane is path-filtered so a `recipes/`-only or station-only PR never runs it, and Kedro-Viz stays at `/kedro-viz/`

**Never:**
- Do not re-mint a verb, build or command that exists — bind to it; do not add a second Pages deployment or a second PR gate; a live proof stays opt-in and operator-run (the Epic 24 HARD boundaries in `epics.md`).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| the deferral's own case | the DW row's evidence reproduced as a fixture | the Then holds | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-herald CAP-49`.
Surface: `.github/workflows/` (one new `pull_request` lane, path-filtered to `docsite/**`, `docs/dashboard/**` render inputs and the workflow itself, running `docsite/build.py --check` and `site-check`), `pixi.toml` (`pr-preflight` gains the same leg; `site-check` task reused, not re-minted), `docs/how-to/presentation-deck.md` § verify checklist (names the lane), `planning-artifacts/deferred-work-ledger.md` (DW-FU-23-5 → done citing the lane's first green run).
Ledger key: `24-2-the-docsite-has-a-pr-gate`.
Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-24-2-the-docsite-has-a-pr-gate.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).

**Manual checks:**
- A fixture regression (unrendered Jinja tag in a family-page template) reds the new lane; `main` is green; `pixi run -e pyforge-guild pr-preflight` runs the same leg; `dashboard.yml` is still the only `deploy-pages` caller; DW-FU-23-5 is marked done citing the lane's first green run.

## Auto Run Result

Status: implemented, verified locally; PR not yet opened/merged (see Residual risks)

**Summary:** A new `pull_request`-triggered workflow, `.github/workflows/docsite-check.yml`, path-filtered to `docsite/**`, `docs/dashboard/**` and its own workflow file, runs two checks before merge: `docsite/build.py --check` with the same pip-installed deps `dashboard.yml` itself uses (predicting exactly what the real deploy step would do, building into the default `./dist/`, never the tracked `docs/dashboard/`), and `pixi run -e site site-check` (the existing task, reused not re-minted). `pixi.toml`'s `pr-preflight` gained a sixth leg, `{ task = "site-check", environment = "site" }`, so a local run predicts the lane. `dashboard.yml` is unchanged and stays the only `deploy-pages` caller.

**Files changed:**
- `.github/workflows/docsite-check.yml` (new) — the `pull_request` + `push:main` + `workflow_dispatch` lane.
- `pixi.toml` — `pr-preflight`'s `depends-on` gained `{ task = "site-check", environment = "site" }`; its `description` gained a "Sixth leg" paragraph matching the existing per-leg-addition convention.
- `docs/how-to/presentation-deck.md` — Acceptance criteria checklist gained a bullet naming the new lane and that `pr-preflight` predicts it.
- `_bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md` — DW-FU-23-5 marked `status: done 2026-09-18` with a `verified:` note.

**Cross-cutting fix required to unblock verification (found live, not this story's own drift):** `pixi run -e local-recipes test-ci` and `pixi run -e pyforge-guild detectors-ci` both initially reported a real, blocking `spec-surface` FAIL — `pyforge-marshal/spec-pyforge-core: src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py changed but the spec's memlog did not move`. Traced to this branch (`baseline_revision: f9f95c6036`) predating PR #1470 ("marshal: co-governor memlog note for herald 24.1's deck_pipeline change; scoped re-stamp", merged 2026-09-18T19:52:17Z, commit `301d4c19b5`), which already reconciles exactly this drift on `origin/main`. Fixed by merging `origin/main` into this branch (merge commit, `ort` strategy, zero conflicts — none of origin/main's new commits touched this story's four changed files); `test_spec_surface_check_green` and the `spec-surface` detector both went from FAIL/1-gating-finding to clean afterward. Not a code change to this story's own surface.

**Review findings breakdown:** Single-pass self-review (no multi-reviewer subagent loop was run in this session). No findings against this story's own diff.

**Follow-up review recommendation:** false.

**Verification performed:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` (the spec's mandated Verification command) — 1478 passed, 4 skipped, both before and after the `origin/main` merge.
- `python docsite/build.py --check` (pip-style deps, matching `dashboard.yml`'s own invocation) and `pixi run -e site site-check` — both green: `checks passed — 7 required outputs, 10 infographics, 10 deck families`.
- Fixture regression, reverted after: `{% raw %}{{ this_stays_unrendered }}{% endraw %}` inserted into `docsite/templates/page_family.html.j2`'s rendered body made `docsite/build.py --check` fail (exit 1) on "unrendered Jinja delimiters" for all 10 deck families; reverting restored a clean, byte-identical template (`git diff` empty) and both checks green again. A second regression variant (a syntactically-broken `{% BROKEN %}` tag placed outside any `{% block %}`) was also tried and found to be a weaker proof — content outside a Jinja `{% block %}` in a child template that `{% extends %}` a parent never renders, so that placement produced a false pass; the in-block `{% raw %}` variant above is the one that actually exercises `build.py`'s own "unrendered Jinja delimiters" check.
- `pixi run -e local-recipes python -c "from pyforge.doctor.sources import chain; ..."` (direct `gather_spec_surface` call) — 0 FAIL-status findings after the merge.
- `pixi run --frozen -e local-recipes pytest .claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py -q` — 10 passed.
- `pixi run -e local-recipes test-ci` — 9124 passed, 30 skipped, 10 deselected, 1 xpassed after the merge (0 failures related to this story's diff — see Residual risks for the 5 unrelated failures still present in this session's shell).
- `pixi run -e pyforge-guild pyforge-station-tests` (all 8 PyForge station suites — mandatory since `pixi.toml` changed, per CLAUDE.md's shared-surface rule) — EXIT=0, every station green (atlas 1871 passed, doctor 1713 passed, herald 1478 passed, marshal 8020 passed, mason 1589+12 passed, scribe 358 passed, steward 1280 passed, warden 2121 passed).
- `pixi run -e pyforge-guild pyforge-station-coverage-gates` — EXIT=0, "no pyforge station packages touched" (this story's diff touches none).
- `pixi run -e pyforge-ci pyforge-doctor-scripts-test` — 530 passed, 4 skipped.
- `pixi project export conda-environment -e build > environment.yaml` — byte-identical (the `site` feature was never on that export, per the `pyforge-pages` Dream's own constraint).
- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/docsite-check.yml'))"` and `python3 -c "import tomllib; tomllib.load(open('pixi.toml','rb'))"` — both parse cleanly.

**Live CI confirmation (PR #1472):** pushed, opened against `main`, `maintenance` label applied. The `Docsite check` job itself: https://github.com/rxm7706/local-recipes/actions/runs/35389603779 — SUCCESS in 26s, confirming `docsite-check.yml` actually runs and passes in real GitHub Actions, not just locally. Full PR rollup: 22 SUCCESS / 4 SKIPPED (the gated platform-smoke lanes: `air-gap-parity`, `build-platform-image`, `gke-portability-smoke`, `ocp-portability-smoke`), `mergeable: MERGEABLE`, `mergeStateStatus: CLEAN`. This also confirms the three local-only findings below never surface in real CI: `detectors` = SUCCESS and `cfe-regression-net` = SUCCESS on the PR.

**Residual risks:**
1. **`pixi run -e pyforge-guild detectors-ci` still exits 1 in this session's shell** (confirmed harmless — the real `detectors` GitHub Actions job on PR #1472 passed), for three findings verified unrelated to this story: (a) `llms_full_check` reports `tornado` as an undocumented dep in `docs/reference/library-llms-full.md` — pre-existing, this story added no dependency; (b) `scripts/pixi_version_check.py` crashes with `ModuleNotFoundError: No module named 'pixi_version_registry'` — reproduced as a `PYTHONSAFEPATH=1` session artifact (this shell has it set; `env -u PYTHONSAFEPATH python3 scripts/pixi_version_check.py --help` runs clean), the same root cause already on file as `feedback_pythonsafepath_breaks_render_skill.md`, not a repo bug; (c) `ledger-direction` reports three `pyforge-atlas` stories (13-5, 14-4, 15-3) as landed-but-unpromoted — an unrelated atlas ledger-sync gap. None of the three are in this story's Surface, and the actual CI `detectors` job (which wraps this same sweep advisory) passed.
2. **`pixi run -e local-recipes test-ci` also showed 5 pre-existing failures in this session's shell, unrelated to this story and NOT present in the real `cfe-regression-net` CI job** (which passed on PR #1472): all `test_all_scripts_runnable.py::test_script_responds_to_help` for `add_handoff.py` / `inventory_match.py` / `library_futures.py` / `recommend_2027.py` / `universe_sbom.py`, all `ModuleNotFoundError` for sibling-module imports (`conda_forge_atlas`, `export_purls`) — the same `PYTHONSAFEPATH=1` session artifact as above.
3. **Not merged.** PR #1472 is open, green, and `MERGEABLE`/`CLEAN` as of this note; merging is left as the next, deliberate step (not taken automatically in this session).
