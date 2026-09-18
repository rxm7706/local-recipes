---
title: '24.2: The docsite has a PR gate'
type: 'feature'
created: '2026-09-18'
status: 'in-review'
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

Status: implemented, verified locally and in CI; PR #1472 open and green, not yet merged (see Residual risks)

**Summary:** A new `pull_request`-triggered workflow, `.github/workflows/docsite-check.yml`, path-filtered to `docsite/**`, `docs/dashboard/**` and its own workflow file, runs two checks before merge: `docsite/build.py --check` with the same pip-installed deps `dashboard.yml` itself uses (predicting exactly what the real deploy step would do, building into the default `./dist/`, never the tracked `docs/dashboard/`), and `pixi run -e site site-check` (the existing task, reused not re-minted). `pixi.toml`'s `pr-preflight` gained a sixth leg, `{ task = "site-check", environment = "site" }`, so a local run predicts the lane. `dashboard.yml` is unchanged and stays the only `deploy-pages` caller.

**Files changed:**
- `.github/workflows/docsite-check.yml` (new) — the `pull_request` + `push:main` + `workflow_dispatch` lane.
- `pixi.toml` — `pr-preflight`'s `depends-on` gained `{ task = "site-check", environment = "site" }`; its `description` gained a "Sixth leg" paragraph matching the existing per-leg-addition convention.
- `docs/how-to/presentation-deck.md` — Acceptance criteria checklist gained a bullet naming the new lane and that `pr-preflight` predicts it.
- `_bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md` — DW-FU-23-5 marked `status: done 2026-09-18` with a `verified:` note.
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md` — CAP-49's catalog tag bumped `ready` -> `in-progress`.

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

## Review Triage Log

### 2026-09-18 — Review pass
- verdicts: 14 findings — high 0, medium 3, low 7, false 4, maybe-false 0
- findings:
  - `[medium]` `[patch]` DW-FU-23-5 marked fully `done` although its own `summary` names two problems (no PR-gating CI lane; `pyforge-herald-test` has zero `docsite/` coverage) and this diff resolved only the first — the second is now untracked, not actually fixed. Action: split the ledger entry per the Story 13.1 "SCOPE OF THIS CLOSURE" precedent — keep the CI-lane half `done`, add a residual entry for the missing `pyforge-herald-test` coverage of `docsite/`.
  - `[low]` `[patch]` `docsite-check.yml`'s header comment claims the lane "predicts precisely what the real deploy step would do," but it never runs `docsite/tools/verify_claims.py` (`site-verify`), which `dashboard.yml` does run (advisory, `continue-on-error`) — verified via `grep -n "verify_claims" .github/workflows/dashboard.yml`. Action: correct the comment's scope claim.
  - `[low]` `[patch]` `spec-24-2-...md`'s `## Auto Run Result` top `Status:` line ("PR not yet opened/merged") contradicts its own later "Live CI confirmation (PR #1472)" paragraph (PR pushed, opened, green) — verified by reading both lines in the current file. Action: update the `Status:` line.
  - `[low]` `[patch]` `docsite-check.yml` sets `cancel-in-progress: true` unconditionally, including on `push: branches: [main]`, contradicting this repo's own established convention in `platform-ci.yml` (`cancel-in-progress: ${{ github.event_name == 'pull_request' }}`, "so main always keeps one full, uncancelled CI result per commit to bisect against") — verified by reading `platform-ci.yml:161-165`. Action: mirror that same conditional.
  - `false` `[reject]` Composite `pixi run -e pyforge-guild pr-preflight` was never run end-to-end in this story's own verification record. Refutation: ran it myself (`EXIT=1`) — it fails at the pre-existing `detectors-ci` leg for three findings entirely unrelated to this story (`llms_full_check` tornado-doc drift, `pixi_version_check`'s `PYTHONSAFEPATH=1` session artifact, and `ledger-direction` findings for other stations), never reaching the new `site-check` leg. That leg's own syntax (`{ task = "site-check", environment = "site" }`) matches sibling legs already proven working, and the task itself was independently run and passed. No gap caused by this story.
  - `[low]` `[patch]` `spec-24-2-...md`'s `## Auto Run Result` "Files changed" list omits `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md`, which this diff does modify (CAP-49 status bump) — verified by diff inspection. Action: add the missing bullet.
  - `[low]` `[patch]` `docsite/README.md`'s "Rebuilding" section documents only local pixi commands and never mentions the new `pull_request`-triggered `docsite-check.yml` lane, despite the workflow's own header naming this file as the one "every developer's local loop actually run[s]" — verified by reading `docsite/README.md:29-36`. Action: add one line noting the new CI lane.
  - `[medium]` `[patch]` (Edge Case Hunter) The new lane's path filter (`docsite/**`, `docs/dashboard/**`, the workflow file) omits `presentations/**`, the actual source directory a broken infographic asset would live in. — grouped with the next row (same root cause).
  - `[medium]` `[patch]` (Verification Gap) `docsite/build.py`'s `collect_families` reads deck assets directly from `presentations/<slug>/project/**`, `presentations/<slug>/src/pptx/**`, and `presentations/<slug>/src/marp/**` (verified by reading `docsite/build.py:300-321`); no workflow anywhere references `presentations` (verified via `grep -rl "presentations" .github/workflows/*.yml` — zero matches) and no test checks path-filter completeness (`test_workflow_path_filters_match.py` only checks the two lists match each other, read in full). A broken infographic/PPTX under `presentations/` merges without ever triggering this gate — `dashboard.yml`'s own build step is not `continue-on-error` so a bad deploy is blocked post-merge (verified by reading `dashboard.yml:57-60`), but main still goes red and the PR-time gate this story exists to add is bypassed for this entire input class, reproducing DW-FU-23-5's own "merge with the real check never running" shape. Action: add `presentations/**` (or the three specific subpaths above) to both `pull_request.paths` and `push.paths`, keeping the two lists identical (enforced by `test_workflow_path_filters_match.py`).
  - `[low]` `[patch]` (Edge Case Hunter) The same path filter also omits `pixi.toml`, so a PR that only edits the `site-check` task definition — the exact task this lane calls — never triggers it. Action: add `pixi.toml` to both path lists.
  - `[low]` `[reject]` (Edge Case Hunter) `pr-preflight`'s new `site-check` leg doesn't exactly mirror `docsite-check.yml`'s separate pip-installed-deps `build.py --check` step (different install mechanism), so a local pass doesn't strictly guarantee that specific CI leg also passes. Not worth fixing: the dependency sets are effectively identical (`jinja2`, `pyyaml`), no version drift demonstrated, and matching the two provisioning paths exactly would add complexity (a new task or forcing CI onto pixi) disproportionate to an undemonstrated risk.
  - `false` `[reject]` (Intent Alignment) The I/O matrix's "reproduced as a fixture" / "the Then holds" wording could be read as requiring a durable, committed test rather than the diff's one-time manual proof. Refutation: the same spec document's own `## Verification` → `**Manual checks:**` section (unchanged, pre-existing text, not part of `<intent-contract>`) explicitly classifies this exact scenario as a manual check — read as a whole, the spec resolves toward the reading the diff implements.
  - `false` `[reject]` (Intent Alignment) "a live proof stays opt-in and operator-run" could be read as barring the implementing session from pushing a branch and opening PR #1472. Refutation: the same spec's `**Manual checks:**` section requires citing "the lane's first green run" to close DW-FU-23-5, which is unobtainable without a real PR; only the terminal action (merge) was withheld, matching this repo's own standing convention (auto-memory `feedback_open_landing_prs_proactively`: verify + open a PR immediately once ready, merge stays a separate deliberate step).
  - `false` `[reject]` (Intent Alignment) Nothing in the diff confirms `Docsite check` is a required, merge-blocking GitHub status check rather than merely advisory. Refutation: `gh api repos/rxm7706/local-recipes/branches/main/protection` returns 404 "Branch not protected" — `main` has no branch protection repo-wide, so every existing CI lane in this repo already gates purely by operator-observed status, not GitHub enforcement; this diff changes nothing about that pre-existing, repo-wide model.
