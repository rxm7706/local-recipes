---
title: 'Publish the real Kedro-Viz DAG continuously'
type: 'feature'
created: '2026-08-09'
status: done
review_loop_iteration: 2
followup_review_recommended: true
context: []
warnings: ['oversized']
baseline_revision: 'c09088a6e6e3ae6ab8d9923dcb7df61a18052fa0'
final_revision: 'b43674a83d16fa024d4aa1def3b14d4fe43f0e16'
---

<intent-contract>

## Intent

**Problem:** Atlas's real 7-pipeline Kedro DAG (`src/shared/packages/pyforge-atlas`) has no continuously published view — only manual `kedro-viz-proto`/`capture-kedro-viz-proto` tasks against a 77-stub-node dependency-free mirror (`src/prototype/packages/pyforge-atlas-kedro-viz`). Epic 12/FR-62 requires CI to build the view from the **real** package on every pipelines-tree push and publish it, without Atlas standing up a second bespoke publishing path.

**Approach:** New pixi tasks run `kedro viz build` against the real package and stage the static output under `docs/dashboard/kedro-viz/` (tracked). A new CI workflow, triggered on push to `main` touching the pipelines tree, runs those tasks then invokes `steward deploy dashboard` — Epic 2's existing build+diff+commit+push CLI — to commit any change (this is Path B from the Spec's research: no third-party `publish-kedro-viz` Action, since it's been dormant 8.5 months). The already-existing `dashboard.yml` Pages workflow (unconditional push-to-main trigger, uploads the whole `docs/dashboard/` tree) republishes automatically once that commit lands — zero changes to it.

## Boundaries & Constraints

**Always:**
- Build from the real `pyforge-atlas` package (`kedro viz build`, cwd = `src/shared/packages/pyforge-atlas`) — never the stub-mirror prototype.
- Stage output at `docs/dashboard/kedro-viz/` — the only viable location, since `steward`'s `dashboard_diff`/`commit_and_push_dashboard` (`src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py`) are hardcoded to the `docs/dashboard` pathspec.
- The staged directory must already be git-tracked before the workflow's first real run: `dashboard_diff` runs plain `git diff` (tracked-files only) as its go/no-op gate — a brand-new untracked directory would show no diff and short-circuit before `commit_and_push_dashboard` (which otherwise would have picked it up via `git add`) ever runs. This story's own PR must commit an initial build as bring-up.
- The new workflow must attach to a real local branch (`git checkout -B main` + set upstream) and set a git identity before invoking `steward deploy dashboard` — `actions/checkout` leaves HEAD detached even on a push-to-branch trigger, and `commit_and_push_dashboard` resolves `git symbolic-ref --short HEAD` first, refusing cleanly (not committing) on a detached HEAD (verified: Story 2.2 review fix).
- Publish exclusively through `steward deploy dashboard` (`pixi run -e pyforge-steward steward deploy dashboard`) — never reimplement its diff/commit/push logic.
- `kedro viz build`'s static export must be made deterministic before staging, or Steward's "only commit on a real difference" guarantee (this story's own I/O matrix and AC below) is unachievable. Empirically confirmed (built the real DAG twice in a row, zero source changes): (a) node/pipeline membership lists and the edge list reorder between runs — root cause is CPython's per-process randomized string-hash seed feeding kedro-viz's internal `set`-based enumeration; fixed by pinning `PYTHONHASHSEED=0` for the `viz-build` task, verified this alone eliminates all structural reordering; (b) `api/deploy-viz-metadata` embeds a literal build wall-clock timestamp (`{"timestamp": "...", "version": "..."}`), unrelated to hash seeding; fixed by normalizing that one field to a fixed placeholder post-build (`version` is left untouched — it's real signal). Verified together: two builds, zero source changes, byte-identical output.
- Kedro's telemetry plugin (`kedro_telemetry`, active via `kedro`/`kedro viz` CLI hooks) defaults to **implicit consent** (opt-out, not interactive — confirmed by reading `kedro_telemetry/plugin.py`: no `input()`/stdin read exists, so it cannot hang a CI job) and silently sends anonymized usage data unless a project-level `.telemetry` file with `consent: false` exists. A CI-only build step should not silently phone home; add that file once to the `pyforge-atlas` kedro project root.
- **Second determinism defect, found in review pass 2 (the pass-1 fix was necessary but not sufficient):** ~53 of the ~195 exported files under `build/api/nodes/*` embed an ABSOLUTE filesystem path for every file-backed (Parquet/JSON) dataset node — anchored to whatever checkout location `kedro viz build` ran from (confirmed: the literal current worktree's own absolute path, e.g. `/home/<user>/.../src/shared/packages/pyforge-atlas/data/intermediate/...`). This is orthogonal to the pass-1 hash-seed fix (confirmed: `grep -rl "$(pwd)" docs/dashboard/kedro-viz/` found matches ONLY under `api/nodes/`, nothing under `assets/`, `.vite/`, or elsewhere). **Consequence if unfixed:** the very first real CI run (checkout path `/home/runner/work/...`, different from whatever path built this story's bring-up commit) would show a diff on every one of those ~53 files purely from path churn — every subsequent CI run would too, on every developer's differently-pathed local rebuild — permanently defeating the "commit only on a real difference" guarantee this story exists to provide, in a way the pass-1 same-directory verification could not detect (repeated builds in one checkout necessarily agree on a path that never changed). **Fix:** a small dedicated script (`src/shared/packages/pyforge-atlas/tools/normalize_viz_build.py`, mirroring the `tools/` script convention already used by the sibling `src/prototype/packages/pyforge-atlas-kedro-viz/tools/` scripts) replaces the literal, checkout-anchored `src/shared/packages/pyforge-atlas` absolute prefix with a fixed placeholder (e.g. `<REPO_ROOT>`) across every file under `build/api/`, and normalizes the `deploy-viz-metadata` timestamp in the same pass (replacing the pass-1 inline `sed`, which is superseded). The script MUST fail loudly (raise, non-zero exit) if, after substitution, the anchor string is still found anywhere, or if the expected `"timestamp"` field isn't found — a review pass-2 finding was that a silent `sed` no-op (e.g. after a future kedro-viz reformats this file) would look like success while leaving real non-determinism in place; this script must not repeat that.
- `.gitignore` negations must be anchored to the directory (`!/.telemetry`, not `!.telemetry`) — an unanchored negation un-ignores a matching filename at ANY depth under that `.gitignore`'s directory, not just the intended top-level file (review pass 2 finding).

**Block If:** the default `GITHUB_TOKEN` cannot push to `main` (branch protection or an org policy blocks it) — HALT rather than weakening security with an elevated PAT. (Verified clean at spec time: `gh api repos/rxm7706/local-recipes/branches/main/protection` → 404 not protected.)

**Never:**
- No changes to `pyforge.doctor.sources.fleet_scan` or `docs/dashboard/index.html` (Steward-owned; Epic 2 is closed) and no changes to `dashboard.yml` (it already republishes the whole tree unconditionally).
- No adoption of the `publish-kedro-viz` GitHub Action (dormant ~8.5 months per the Spec's research — Path B is the evidenced default).
- No deletion of the stub-mirror prototype or its manual tasks — out of scope; only a one-line pointer note so it isn't mistaken for current.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Real DAG change lands on main | push to main touching `pipelines/**` | Workflow builds, stages, `steward deploy dashboard` commits+pushes; `dashboard.yml`'s next run publishes it | No error |
| No real output change | pipelines touched but build output byte-identical | `steward deploy dashboard` reports "no diff — nothing to deploy"; zero commits | No error |
| Detached HEAD from checkout | default `actions/checkout` state | Workflow re-attaches to a real local `main` tracking `origin/main` before invoking steward | If skipped: steward refuses cleanly (`CalledProcessError`), no orphaned commit |
| `kedro viz build` fails | broken catalog/DAG | Workflow fails before reaching steward; nothing staged or committed | CI red |
| Push to a non-main branch touching pipelines | feature branch | Workflow does not trigger (branch + path filter) | N/A |

</intent-contract>

## Code Map

- `pixi.toml` -- add `[feature.pyforge-atlas.tasks.viz-build]` (`kedro viz build` with `PYTHONHASHSEED=0` pinned via `env = { PYTHONHASHSEED = "0" }`, cwd = package root — see Boundaries: determinism fix) and `[feature.pyforge-atlas.tasks.viz-publish-stage]` (run the new normalization script, then wipe+copy to `docs/dashboard/kedro-viz`, `depends-on = ["viz-build"]`)
- `src/shared/packages/pyforge-atlas/tools/normalize_viz_build.py` -- NEW: replaces the checkout-anchored absolute path prefix under `build/api/` with a fixed placeholder AND normalizes the `deploy-viz-metadata` timestamp; fails loudly if either substitution doesn't verifiably take effect (review pass 2 fix, supersedes pass 1's inline `sed`)
- `src/shared/packages/pyforge-atlas/.telemetry` -- NEW: `consent: false` (kedro's documented opt-out mechanism — see Boundaries)
- `docs/dashboard/kedro-viz/` -- NEW, tracked: initial committed, now-deterministic `kedro viz build` output (bring-up, required — see Boundaries)
- `.github/workflows/kedro-viz-publish.yml` -- NEW: builds + stages + calls `steward deploy dashboard`; pattern-mirrors `.github/workflows/dashboard.yml`'s pixi setup; `timeout-minutes` set on the job (no CI job should be able to hang indefinitely)
- `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py` -- READ-ONLY reference: `build_dashboard`/`dashboard_diff`/`commit_and_push_dashboard`/`DeployDuty` — the mechanism this story calls, never edits
- `src/prototype/packages/pyforge-atlas-kedro-viz/README.md` -- one-line pointer to the new live view, linking to the actual GitHub Pages URL (not a GitHub.com blob-view link, which would not render the SPA)
- `environment.yaml` -- regenerate (`pixi project export conda-environment -e build > environment.yaml`); `pixi.toml` changed

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-atlas/tools/normalize_viz_build.py` -- NEW (supersedes pass 1's inline `sed`): walks `build/api/` replacing the checkout-anchored absolute `src/shared/packages/pyforge-atlas` prefix with a fixed placeholder in every file, normalizes `deploy-viz-metadata`'s `timestamp` field, and raises (non-zero exit) if either substitution is not verifiably complete afterward (re-scan for the anchor / the expected pattern) — no silent no-op. Verified live: real run replaced the anchor in 53 files and normalized 1 timestamp field, printing "re-scan confirmed zero anchor occurrences remain."
- [x] `pixi.toml` -- add `viz-build` (`kedro viz build`, cwd = package root, `env = { PYTHONHASHSEED = "0" }`) + `viz-publish-stage` (`python src/shared/packages/pyforge-atlas/tools/normalize_viz_build.py && rm -rf docs/dashboard/kedro-viz && cp -r src/shared/packages/pyforge-atlas/build docs/dashboard/kedro-viz`, `depends-on = ["viz-build"]`) under `[feature.pyforge-atlas.tasks.*]`
- [x] `src/shared/packages/pyforge-atlas/.telemetry` -- NEW: `consent: false`; anchor the `.gitignore` negation as `!/.telemetry` (not `!.telemetry` — an unanchored negation un-ignores a matching filename at any depth, not just this one package-root file)
- [x] Run `pixi run -e pyforge-atlas viz-publish-stage` locally. **Verify properly this time (pass 1's same-directory rebuild test could not catch the absolute-path leak):** (a) `grep -rl "$(pwd)" docs/dashboard/kedro-viz/` must be EMPTY (zero files reference the current checkout's own absolute path anywhere in the staged output) — this is the decisive, non-circular check; (b) still also run the rebuild-diff-rebuild check (twice, zero source changes, `diff -rq` two staged copies empty) to catch any residual hash-seed-class issue. Then commit the resulting `docs/dashboard/kedro-viz/` as this story's bring-up (tracked, not gitignored).
  - (a) actual command + output: `grep -rl "$(pwd)" docs/dashboard/kedro-viz/` → **no output, exit code 1** (grep's "no matches" convention). Zero files reference this checkout's absolute path.
  - (b) actual command + output: ran `viz-publish-stage` twice (moved run 1's `docs/dashboard/kedro-viz` to `/tmp/kedro-viz-run1`, reran, then `diff -rq /tmp/kedro-viz-run1 docs/dashboard/kedro-viz`) → **no output, exit code 0**. Byte-identical across the two runs.
  - `docs/dashboard/kedro-viz/` staged via `git add` (195 files); `git check-ignore -v docs/dashboard/kedro-viz` → no match (exit 1); `git add src/shared/packages/pyforge-atlas/.telemetry` succeeded with no `-f` needed.
- [x] `.github/workflows/kedro-viz-publish.yml` -- NEW: `on: push: branches: [main], paths: ['src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/**']` + `workflow_dispatch`; `permissions: contents: write`; `timeout-minutes: 15`; `concurrency: kedro-viz-publish` / `cancel-in-progress: false`; steps: checkout → `git checkout -B main` + `git branch --set-upstream-to=origin/main main` → git identity config → `prefix-dev/setup-pixi@v0.10.0` (`environments: >- \n  pyforge-atlas \n  pyforge-steward`, `pixi-version: v0.76.2`, `locked: true`, `cache: true`) → `pixi run -e pyforge-atlas viz-publish-stage` → `pixi run -e pyforge-steward steward deploy dashboard`
- [x] `src/prototype/packages/pyforge-atlas-kedro-viz/README.md` -- one-line pointer to the live view at `https://rxm7706.github.io/local-recipes/kedro-viz/`
- [x] Regenerate `environment.yaml`; verify via `pixi run -e local-recipes llms-full-check` that no new drift is introduced. `environment.yaml` regen produced **zero diff** (confirmed byte-for-byte). `pixi run --frozen -e local-recipes llms-full-check` reported 13 pre-existing findings (12 floor-drift + 1 undocumented-dep: `httpx2`), none referencing this story's changes (`kedro-viz`, `viz-build`, `viz-publish-stage`, or `normalize_viz_build.py`) — no new drift introduced.
- [x] **Review pass 3 patches, applied directly (no bad_spec this round — see Review Triage Log):** (1) `viz-build`'s `cmd` now `rm -rf build && kedro viz build` (clears stale content from a prior local run before rebuilding); (2) `normalize_viz_build.py`'s scan widened from `build/api/` to the whole `build/` tree; (3) `PLACEHOLDER` renamed `<REPO_ROOT>` → `<PYFORGE_ATLAS_ROOT>` (accurately names what's actually being anchored — the atlas package root, not the repo root); (4) `repo_root()` simplified to Steward's own proven single-file marker (`pyforge.doctor.sources.fleet_scan`), replacing a two-condition marker that was fragile in principle (though verified NOT to misfire in this repo's actual directory structure); (5) added a floor-check (`_assert_anchor_handled` raises if zero files ever matched the anchor, mirroring the timestamp check's existing `n_subs == 0` guard). Re-verified after all five: rebuild-diff-rebuild still byte-identical (the only diff between the pre- and post-patch outputs was the intentional placeholder-string rename, confirmed via direct inspection); absolute-path leak check still empty; a standalone unit check confirms `_assert_anchor_handled` actually raises on `files_changed == 0`.
- [x] **Cross-checkout reproducibility, genuinely verified (not just argued):** copied `src/shared/packages/pyforge-atlas` to a physically different absolute path (`/tmp/atlas-realcopy/pyforge-atlas`), ran `kedro viz build` there for real (confirmed the pre-normalization leaked path was the NEW location, not the original — proving the copy wasn't somehow resolving back to the same path), applied the same normalize logic, and diffed the result against the actual staged `docs/dashboard/kedro-viz/api` — **byte-identical, `diff -rq` exit 0**. This directly answers review pass 3's "the core cross-checkout claim is still unverified" finding with an actual different-location build, not a same-directory test or a symlink (symlinks were tried first and found to resolve through to the real path via kedro's own path resolution, making them unsuitable for this test).

**Acceptance Criteria:**
- Given a push to main touching `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/**`, when the new workflow runs, then it builds `kedro viz build` from the real package (with `PYTHONHASHSEED=0` pinned) and normalizes the output (absolute-path anchor stripped, timestamp fixed) before staging under `docs/dashboard/kedro-viz/`.
- Given that build, when the workflow invokes `steward deploy dashboard`, then a real diff is committed and pushed directly to `main` (no reimplementation of Steward's diff/commit/push logic).
- Given that commit lands on `main`, when `dashboard.yml`'s existing unconditional push-to-main trigger next runs, then it publishes the whole `docs/dashboard/` tree including the refreshed `kedro-viz/`, with zero edits made to `dashboard.yml`.
- Given no real DAG change, when the workflow rebuilds from a DIFFERENT checkout path than whatever produced the last commit (e.g. a GitHub Actions runner vs. this story's local bring-up), then the normalized output is still byte-identical and `steward deploy dashboard` reports "nothing to deploy" with zero commits — genuinely verified via a real different-absolute-path build (see Tasks), not merely argued from the absence of the known anchor string.

## Spec Change Log

### 2026-08-09 — bad_spec loopback (review_loop_iteration 1)
- Triggering finding: `kedro viz build`'s static export is not reproducible across runs of identical source (empirically confirmed: two from-scratch builds, zero source changes, produced ~2,000+ differing lines across `api/*`). Root causes isolated to (1) CPython's per-process randomized string-hash seed reordering kedro-viz's internal `set`-based node/pipeline/edge enumeration, and (2) a literal build-wall-clock timestamp in `api/deploy-viz-metadata`. This defeated the story's own "zero commit on no real change" AC and the entire justification for reusing Steward's reconciled-push mechanism over a naive always-commit approach.
- What was amended: added a `PYTHONHASHSEED=0` pin to the `viz-build` task and a timestamp-normalization step to `viz-publish-stage` (Boundaries, Code Map, Design Notes, Tasks, AC, Verification all updated). Folded in three additional low-risk patches discovered in the same review pass rather than deferring them to a second loopback cycle: a `.telemetry` opt-out file (kedro's telemetry defaults to implicit/silent consent), `timeout-minutes` on the new workflow's job, and a corrected README link (points at the real GitHub Pages URL, not a GitHub.com blob view which wouldn't render the SPA).
- Known-bad state avoided: every trigger of the new workflow (including a no-op `workflow_dispatch` or an unrelated docstring-only pipeline edit) silently producing a spurious ~11 MB commit forever, defeating the "reconciled push" property this story exists to provide.
- KEEP (verified correct, must survive re-derivation unchanged): the two-task pixi split (`viz-build` / `viz-publish-stage`) and staging to `docs/dashboard/kedro-viz/`; the workflow's trigger/path-filter/permissions/concurrency shape; the `git checkout -B main` + upstream-tracking + git-identity steps (detached-HEAD fix, independently verified correct by both reviewers); calling `steward deploy dashboard` rather than a bespoke commit step; the bring-up-commit requirement; `environment.yaml` regeneration producing no diff.

### 2026-08-09 — bad_spec loopback (review_loop_iteration 2)
- Triggering finding: pass 1's determinism fix was necessary but NOT sufficient. ~53 of ~195 exported node files embed an absolute filesystem path (anchored to whatever checkout built them) for every file-backed dataset — orthogonal to the pass-1 hash-seed fix, and undetectable by pass 1's own verification method (rebuilding twice in the SAME directory can never surface a checkout-path-dependent difference, since the path never changes between those two runs). Left unfixed, the first real CI run (a different checkout path than whatever produced this story's bring-up commit) — and every developer's differently-pathed local rebuild thereafter — would show a spurious diff on those ~53 files forever, again defeating the "commit only on a real difference" guarantee.
- What was amended: pass 1's inline `sed` timestamp-normalize step is superseded by a new dedicated script, `src/shared/packages/pyforge-atlas/tools/normalize_viz_build.py`, which (a) replaces the checkout-anchored absolute path prefix under `build/api/` with a fixed placeholder, re-scanning afterward to PROVE zero occurrences remain (not just trust the substitution ran), and (b) normalizes the timestamp field the same way, failing loudly if the expected pattern isn't found — directly closing a pass-2 finding that the old `sed` pattern would silently no-op (exit 0, do nothing) against a future kedro-viz output-format change. Folded in one more low-risk patch from the same pass: anchoring the `.gitignore` negation as `!/.telemetry` (the pass-1 unanchored `!.telemetry` would un-ignore a matching filename at any depth, not just the intended package-root file).
- Known-bad state avoided: every real CI run producing a churn commit purely from checkout-path differences, on top of (not instead of) the pass-1 defect — and the story's own verification claims ("byte-identical") being true only in the narrow, non-representative case of rebuilding in the exact same directory twice.
- KEEP (verified correct in pass 2, must survive): everything kept from iteration 1 (see above) PLUS the `PYTHONHASHSEED=0` pin itself (pass 2 confirmed it correctly eliminates all structural/ordering non-determinism — the residual issue found was a wholly separate, additive defect, not a flaw in the hash-seed fix); the `.telemetry` file and its intent; the workflow shape (unchanged in this iteration).

## Review Triage Log

### 2026-08-09 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel, no shared context)
- intent_gap: 0
- bad_spec: 1 (high 1, medium 0, low 0)
- patch: 3 (high 0, medium 0, low 3)
- defer: 4 (high 0, medium 2, low 2)
- reject: 7
- addressed_findings:
  - `[high]` `[bad_spec]` `kedro viz build` output is non-deterministic across runs of identical source (per-process hash-seed randomization + a literal build timestamp) — defeats the "zero commit on no real change" guarantee. Fixed via spec amendment: `PYTHONHASHSEED=0` pin + timestamp normalization, verified empirically to produce byte-identical output across two from-scratch builds.
  - `[low]` `[patch]` Kedro's telemetry plugin defaults to implicit/silent consent (verified non-blocking — no stdin read exists, so it cannot hang CI, contrary to one reviewer's stated concern — but it does silently transmit usage data). Fixed: added a `.telemetry` file with `consent: false` to the `pyforge-atlas` kedro project root.
  - `[low]` `[patch]` New workflow's job had no `timeout-minutes`, risking an indefinitely-hung runner on any future stall. Fixed: added `timeout-minutes: 15`.
  - `[low]` `[patch]` README pointer note linked to a GitHub.com blob view of `index.html`, which renders raw source, not the live SPA — the note's own "live" claim was misleading via that link. Fixed: link now points to the actual GitHub Pages URL (`https://rxm7706.github.io/local-recipes/kedro-viz/`).
- Findings routed to `deferred-work.md` (not this story's problem to solve now): (1) the workflow's path filter (`pipelines/**` only, matching the upstream epic-level Spec's literal wording) won't catch a DAG-shape change made via `pipeline_registry.py`, `settings.py`, or `conf/base/catalog.yml`/`parameters.yml` — a scope question for a future epic-level revisit, not a defect in this story's faithful implementation of the named path; (2) a direct-push-from-CI-to-main workflow will break silently if branch protection is ever added to `main` (none exists today, verified) — an operational dependency worth monitoring, not fixable in code now; (3) a narrow non-fast-forward race exists if two pipeline-touching pushes land in quick succession (the queued run's shallow checkout could be based on a since-superseded SHA) — low-probability, partially self-healing via Steward's own `_push_pending_commit_if_ahead` retry-next-run logic; (4) no end-to-end GitHub Actions execution was exercised (only the underlying pixi tasks and the Steward CLI's `--dry-run` path were verified locally) — a residual risk inherent to not having a live CI run available in this environment.
- Findings rejected as noise (contradicted by verified facts or by this repo's own existing, deliberate precedent): `cancel-in-progress: false` (matches `dashboard.yml`'s own identical choice for the analogous build+publish job); `kedro viz build` failing on missing credentials/config (empirically verified twice to run fully offline with no credential errors); `viz-publish-stage` missing an explicit `cwd` (matches multiple existing, working, cwd-less tasks in the same `pixi.toml` that reference root-relative paths); unguarded `rm -rf` in `viz-publish-stage` (intentional wipe-and-replace regen semantics, scoped to a machine-generated, git-tracked-for-diffing directory only); design rationale living in YAML comments with no spec cross-link (matches `dashboard.yml`'s own established convention); unverified action/tool pins (`actions/checkout@v7`, `setup-pixi@v0.10.0`, `pixi-version: v0.76.2` all match the exact pins already in use in this repo's own `dashboard.yml`); a missing "build output exists" guard before staging and stale-build accumulation across repeated local runs (both refuted: pixi's `depends-on` chain already aborts on a failed `kedro viz build`, and `viz-publish-stage`'s own full wipe-then-copy of the destination makes the published output idempotent regardless of what accumulates in the ephemeral source `build/` dir).

### 2026-08-09 — Review pass 2 (Blind Hunter + Edge Case Hunter, parallel, no shared context, against the pass-1-amended diff)
- intent_gap: 0
- bad_spec: 1 (high 1, medium 0, low 0)
- patch: 3 (high 0, medium 0, low 3)
- defer: 0
- reject: 6
- addressed_findings:
  - `[high]` `[bad_spec]` Pass 1's determinism fix was incomplete: ~53 of ~195 exported node files embed an absolute, checkout-anchored filesystem path (confirmed by direct inspection of the actual committed files — the reviewer did not just trust the diff text — and independently re-confirmed by re-running the same `grep` check). Pass 1's own "byte-identical" verification could not have caught this, since it rebuilt twice in the same directory. Fixed via spec amendment: a new dedicated `normalize_viz_build.py` script strips the checkout-anchored absolute prefix (proven complete by re-scanning for zero remaining occurrences, not merely trusting the substitution) in addition to the timestamp normalization.
  - `[low]` `[patch]` The pass-1 inline `sed` timestamp-normalize pattern would silently no-op (exit 0, no error) if a future kedro-viz release reformats `deploy-viz-metadata`'s JSON, quietly reintroducing non-determinism with no signal. Fixed: folded into the new script, which raises if the expected pattern isn't found.
  - `[low]` `[patch]` The pass-1 `.gitignore` negation (`!.telemetry`, unanchored) would un-ignore a matching filename at any depth under the package, not just the intended package-root file. Fixed: anchored as `!/.telemetry`.
  - `[low]` `[patch]` (folded from the same pass rather than a third loopback) No automated check verifies the determinism guarantee holds going forward beyond a one-time human-run spot-check. Addressed cheaply within the same fix: the normalization script's own fail-loud re-scan (checked into the task chain itself, not a separate CI step) means a future regression in either normalized field surfaces as a hard task failure the next time `viz-publish-stage` runs, rather than a silent reversion to non-determinism.
- Findings rejected as noise (verified against this repo's own precedent or refuted as speculative with no supporting evidence): non-atomic `rm -rf`+`cp -r` in `viz-publish-stage` (same accepted-tradeoff class as pass 1's identical finding — CI is ephemeral per-run and nothing is committed until after this task succeeds; a local interrupted run is git-recoverable); load-bearing reasoning living in `pixi.toml` task-description strings rather than code comments (matches this exact file's own established, repo-wide convention for every other task); no automated guard against `viz-build`'s `cwd` ever pointing at the wrong (stub) project (matches how every other task in this file enforces its target solely via `cwd`, with no separate automated check, and no evidence this has ever actually happened); speculative concern that kedro-viz might have an unrelated worker-process race condition independent of hash-seed — no supporting evidence; across every build attempt made so far (pre-fix, post-hash-seed-fix), every observed diff has been fully attributed to one of the three known causes (ordering, timestamp, absolute path) with no unexplained residual — the re-implementation pass will re-run the full determinism check with the new fix in place and this will be re-confirmed, not assumed.

### 2026-08-09 — Review pass 3 (Blind Hunter + Edge Case Hunter, parallel, no shared context, against the pass-2-amended diff)
- intent_gap: 0
- bad_spec: 0
- patch: 5 (high 0, medium 0, low 5)
- defer: 2 (high 0, medium 0, low 2)
- reject: 6
- addressed_findings:
  - `[low]` `[patch]` `kedro viz build`'s own `LocalDeployer` never clears its output directory first (confirmed by reading the installed source: only `mkdir(parents=True, exist_ok=True)`, no `rmtree`) — a node/dataset removed from a real DAG change would leave its old file behind in `build/` across repeated LOCAL invocations (moot for CI, which always starts from a fresh checkout, but a real hygiene gap otherwise). Fixed: `viz-build`'s `cmd` now `rm -rf build && kedro viz build`.
  - `[low]` `[patch]` `_strip_anchor`'s floor was asymmetric with `_normalize_timestamp`'s: zero anchor matches would silently "succeed" (0 changed, re-scan trivially finds 0 leftover) rather than raise, exactly the silent-no-op class both fixes are supposed to prevent. Fixed: `_assert_anchor_handled` now raises if `files_changed == 0`, verified via a standalone check that it actually does.
  - `[low]` `[patch]` `PLACEHOLDER = "<REPO_ROOT>"` misnamed what it actually anchors (the atlas package root, not the repo root — verified: the real value is `<repo_root>/src/shared/packages/pyforge-atlas`). Fixed: renamed to `<PYFORGE_ATLAS_ROOT>`.
  - `[low]` `[patch]` `repo_root()`'s two-condition marker (`pixi.toml` AND `recipes/`) was more fragile in principle than necessary, given `pyforge-steward`'s own already-proven single-file marker exists in this exact repo. Verified this does NOT currently misfire (walked every ancestor from the script to the true repo root; only the true root satisfies both conditions before it) but simplified anyway for consistency and to remove the theoretical risk. Fixed: now mirrors `deploy.py::repo_root()` exactly, keyed on `pyforge.doctor.sources.fleet_scan`.
  - `[low]` `[patch]` The anchor-strip was scoped only to `build/api/`, based on a one-time manual observation that nothing else leaked — not an enforced guarantee against a future kedro-viz version leaking the same anchor elsewhere (e.g. `build/assets/*.js`). Fixed: widened the scan to the whole `build/` tree; re-verified the fix still produces 53 files changed (unchanged) and a clean re-scan.
- Also directly resolved rather than deferred: pass 3's "the core cross-checkout claim is still unverified" finding (the only prior evidence was grepping for the ALREADY-KNOWN anchor string plus a same-directory rebuild — structurally similar to what let the pass-2 bug through). Performed a genuine cross-checkout test: copied the atlas package to `/tmp/atlas-realcopy` (confirmed via the pre-normalization leaked path that this was a truly different location, not a symlink resolving back — a symlink attempt first was found unsuitable, since kedro's own path resolution follows symlinks to the real path), built there for real, normalized with the same logic, and diffed against the actual staged output — byte-identical. This is now empirically confirmed, not merely argued from construction.
- Findings deferred to `deferred-work.md` (currently inert, no live instance, and either speculative or would reintroduce complexity this fix deliberately avoided): (1) `_iter_text_files`'s `UnicodeDecodeError` skip means a non-UTF-8 file under `build/` would be invisible to both the strip and the verifying re-scan — every file under `build/` today is confirmed UTF-8 JSON/text, so this is inert until a future kedro-viz version changes that; (2) `str.replace()`'s literal substring match has no path-boundary check, so a hypothetical future sibling directory sharing the `pyforge-atlas` prefix (e.g. `pyforge-atlas-legacy`) would have its own unrelated absolute paths partially mangled — no such sibling exists today, and a boundary-safe fix would need regex (reintroducing exactly the escaping fragility `str.replace()` was chosen to avoid for arbitrary filesystem paths).
- Findings rejected as noise: `kedro viz build` crashing after a partial write (before `viz-publish-stage` runs) — speculative, no evidence, and pixi's `depends-on` chain already aborts on any non-zero `viz-build` exit, which is the realistic failure shape for a tool that either completes or errors; `_normalize_timestamp` not requiring `n_subs == 1` (only `!= 0`) — the actual goal is eliminating the timestamp's non-determinism, which any `n_subs >= 1` already achieves, so requiring exactly one adds no real safety value; requiring `errors="replace"` retry on `UnicodeDecodeError` instead of skip — folded into the UTF-8 defer above, not a separate action; version-field (`deploy-viz-metadata`) determinism depending on CI vs. local `kedro-viz` version drift — already addressed by the existing `locked: true` pixi setup, which is specifically the mechanism that guarantees identical resolved versions against the same lockfile; non-atomic `rm -rf`+`cp -r` (re-raised from pass 2) — same accepted reasoning as before, still applies unchanged.

### 2026-08-09 — Review pass 4 (verification repair)

**Scope note:** this pass reviews only the repair diff below, not the full baseline diff (already
covered by passes 1–3). The bmad-loop deterministic gate (`pixi run --frozen -e pyforge-atlas
kedro-test`) failed post-implementation on 2 tests, both outside this story's Code Map
(`tests/dashboard/`), per `.bmad-loop/runs/20260809-034342-8683/feedback/12-2-publish-the-real-dag-continuously-1.md`.

Root-caused before reviewing: (1) `test_dashboard_e2e_navigation_and_rendering` failed because AG
Grid infers a column's `cellDataType` from row 0 alone — the factory-status page's "status" column
has an ISO build-stamp in row 0 and plain status words elsewhere, so auto-inference misread the
column as a date and blanked every non-date-parseable status. (2) `test_factory_status_reads_the_
real_sprint_status` asserted `d1-`/`d2-` sprint-status.yaml keys that PR #322 (2026-08-08, unrelated)
had already renamed to `5-1-`/`5-2-` fleet-wide. Confirmed both are pre-existing and unrelated to
this story: `git diff --stat` from `baseline_revision` to the pre-repair `final_revision` touches
neither `tests/dashboard/` nor `dashboard/app.py`/`factory_status.py`.

Discovered that sibling story 12-1 (`bmad-loop/20260809-034342-8683/12-1-kedro-skills-audit-then-
adopt`, forked from this story's same `baseline_revision`) independently hit and fixed the identical
`kedro-test` failure via commit `f0bb93fc0e`, already reviewed there (bmad-review-adversarial-general
+ bmad-review-edge-case-hunter, triage log in `spec-12-1-kedro-skills-audit-then-adopt.md`). Adopted
via `git cherry-pick f0bb93fc0e` rather than re-deriving an equivalent fix, then amended the commit
message (only) to reference this story instead of 12-1, then re-reviewed the resulting diff fresh
against this tree (findings below).

- intent_gap: 0
- bad_spec: 0
- patch: 2 (low 2)
- defer: 1 (low 1)
- reject: 9 (high 0, medium 0, low 9)
- addressed_findings:
  - `[low]` `[patch]` (Blind Hunter) The cherry-picked commit's message still narrated "story 12-1"
    context verbatim, misleading on 12-2's own branch history. Fixed: amended the message (content
    unchanged) to reference story 12-2, credit the cherry-pick provenance, and point at both stories'
    spec files.
  - `[low]` `[patch]` (Blind Hunter) `spec-12-2-publish-the-real-dag-continuously.md` had zero record
    of this repair, breaking the "spec is the contract" convention for anyone auditing 12-2 through
    its own spec. Fixed: this Review pass 4 entry + the `## Auto Run Result` update below.

**Deferred** (`deferred-work.md`): the live `sprint-status.yaml`'s `story_meta.depends_on` lists
still reference the retired `d1-`/`d2-` spelling for Epic 5 (3 occurrences) even though PR #322
renamed the matching `development_status` keys to `5-1-`/`5-2-` — inert today (no shipped code reads
`depends_on` from this file), same underlying issue already deferred on story 12-1's behalf,
re-flagged here since 12-2 independently hit the same gate failure and `sprint-status.yaml` sits
outside both stories' Code Maps.

**Rejected** (9 findings — either the same tradeoffs already deliberated and accepted during 12-1's
original review of this identical diff, refuted by the code, or documentation-only nits):
- "The `defaultColDef` pin applies to the whole factory-status grid, not scoped to just `status`; a
  future non-text `FRAME_COLUMNS` addition would silently render as text with no failing test" (Blind
  Hunter + Edge Case Hunter, converged) — the more targeted per-column alternative was considered and
  rejected during 12-1's original review specifically because it re-couples `app.py` to
  `factory_status.FRAME_COLUMNS` for no benefit; all four current columns are string-typed, and
  speculative hardening against a hypothetical future non-string column is exactly what this repo's
  Simplicity First principle rules out.
- "The five `_data_page`-built grids (feedstock-health, my-feedstocks, staleness-report,
  query-atlas, detail-cf-atlas) have no `defaultColDef` pin or test coverage for the same hazard"
  (Blind Hunter + Edge Case Hunter, converged) — already adjudicated identically during 12-1's
  review: those pages' data is uniformly typed per column across all rows (re-verified true here),
  so the bug cannot fire there today.
- "`k.endswith(suffix)` iterated over `keyed`'s keys could raise `AttributeError` on a non-string
  key" (Edge Case Hunter) — refuted: `factory_status.py`'s `build_factory_status_frame` unconditionally
  wraps every sprint-status key in `str(key)` before it reaches the frame, so `keyed`'s keys are
  always `str` by construction; not reachable.
- "Suffix-only matching no longer verifies the key's leading epic-story numbering prefix" (Blind
  Hunter + Edge Case Hunter, converged, one low-confidence) — this is the deliberate, stated tradeoff
  of the original fix (rename-resilience over exact-prefix verification), already accepted during
  12-1's review of the same diff.
- "The new offline regression test only asserts the `defaultColDef` kwarg was supplied, not that AG
  Grid actually honors it" — the existing Playwright e2e test (unchanged, still in the suite and
  still green) is the behavioral proof; the offline test is an intentionally fast smoke-layer on top,
  not a replacement, matching this repo's existing dryrun/e2e layering convention.
- "No version citation for the claim that vizro's `dash_ag_grid` deep-merges `Mapping` kwargs" —
  verified empirically (live before/after run) rather than by doc citation, which this repo already
  treats as sufficient evidence elsewhere (same rationale accepted during 12-1's review).
- "The new test's docstring restates the `app.py` comment's rationale almost verbatim" —
  documentation-only nit; harmless duplication in two places that already exist and are already
  reviewed.
- "The comment above `_factory_page`'s return statement bundles three rationales in one paragraph
  over unrelated construction code" — documentation-only nit; the same comment already passed
  review once during 12-1's original pass.
- "The commit's 'reproduces on canonical main'/'3/3 deterministic' claims aren't independently
  re-verifiable from this worktree alone" — not required: this pass independently re-verified the
  fix's *effect* directly in this tree (`kedro-test` red before, green after, see Verification),
  which is stronger evidence than re-tracing someone else's historical reproduction steps.

## Design Notes

**Why not literally the `publish-kedro-viz` Action or a bespoke commit step:** the Spec's own research grounds Path B (reuse `steward deploy dashboard`'s existing shape) as the evidenced default — `publish-kedro-viz` has been dormant 8.5 months and pins a kedro-viz major that a future release could strand; a bespoke commit step here would duplicate Steward's already-reviewed reconciled-push logic (detached-HEAD refusal, pathspec-scoped commit, stuck-push retry) that this story gets for free by calling the CLI instead.

**Why the bring-up commit is load-bearing, not optional:** empirically verified against the real `deploy.py` — `dashboard_diff` is a plain `git diff` (tracked files only), checked *before* `commit_and_push_dashboard` ever runs. A first-ever untracked `kedro-viz/` directory would report "no diff" and the workflow would silently no-op forever, never reaching the `git add` that would otherwise have picked it up.

**Why `git checkout -B main` before calling steward:** empirically verified — `actions/checkout` checks out `github.sha` (detached HEAD) even on `push` triggers; `commit_and_push_dashboard` calls `git symbolic-ref --short HEAD` first and refuses (not commits) if detached. Hardcoding `main` (not a templated ref) matches this workflow's own single trigger branch, mirroring `dashboard.yml`'s identical hardcoding.

**Why `PYTHONHASHSEED=0` and not a general JSON canonicalizer:** isolated two causes of the *structural* (list/array ordering) non-determinism: (1) CPython's default per-process randomized string-hash seed makes kedro-viz's internal `set`-based node/pipeline/edge enumeration iterate in a different order every process invocation — pinning `PYTHONHASHSEED=0` makes that ordering reproducible; (2) `api/deploy-viz-metadata`'s literal build timestamp, unrelated to hashing. A general recursive "sort every array" canonicalizer was considered and rejected: some arrays in kedro-viz's export (e.g. an edge list of `{source, target}` objects) aren't plain string arrays, and blindly resorting arbitrary nested structures risks corrupting an array where order IS semantically meaningful — whereas pinning the hash seed fixes that root cause with no risk of touching real DAG semantics. **Correction from review pass 2:** the pass-1 claim that this made the export "byte-for-byte reproducible" was verified only by rebuilding twice in the SAME checkout directory — which cannot detect checkout-path-dependent content, because the path never changes between two same-directory rebuilds. It did not; see the next note.

**Why a dedicated normalization script, and why it must fail loudly (review pass 2 fix):** pass 2 found a THIRD, independent non-determinism source the pass-1 same-directory test structurally could not catch: ~53 of ~195 exported node files embed an absolute filesystem path (e.g. `/home/<user>/.../pyforge-atlas/data/intermediate/...`) for every file-backed dataset, anchored to whatever checkout location built them — confirmed present ONLY under `build/api/nodes/*` (a full-tree scan found nothing elsewhere). Two real CI checkouts (or any two developers' machines) would never agree on this path, permanently defeating Steward's diff-gate. The fix replaces the literal, checkout-anchored `src/shared/packages/pyforge-atlas` absolute prefix with a fixed placeholder across `build/api/`, proven complete by re-scanning for zero remaining occurrences of that literal string (not merely trusting the substitution ran) — this is a sound, non-empirical proof of path-independence: if no trace of the checkout's own absolute path remains anywhere in the output, the output cannot differ *because of* checkout location, by construction. A dedicated Python script (not another inline `sed`) both makes this two-step normalize-then-verify logic legible and lets it fail loudly (raise) if a future kedro-viz release changes the JSON shape enough that a pattern silently stops matching — the exact "sed exits 0 while doing nothing" risk pass 2 flagged in the pass-1 fix.

**Review pass 3 refinements (patch-tier, no bad_spec):** (1) the anchor-strip's own floor check (`files_changed == 0` raises) closes the one asymmetry pass 2's fix left against its own stated "must fail loudly" standard — the timestamp check already had this, the anchor-strip didn't; (2) the scan was widened from `build/api/` to the whole `build/` tree — cheap, and removes the "only checked once, not enforced" gap around the scope decision itself; (3) `PLACEHOLDER` renamed `<REPO_ROOT>` → `<PYFORGE_ATLAS_ROOT>` to accurately describe what it anchors; (4) `repo_root()` simplified to Steward's own single-marker convention, removing a theoretical (verified non-live, but real) fragility from an invented two-condition marker; (5) `viz-build` now clears `build/` first, closing a stale-node-accumulation gap that only matters for repeated local runs (CI's fresh-checkout-per-run already avoided it). Most importantly: the cross-checkout reproducibility claim, previously only argued by construction (zero occurrences of the known anchor ⟹ no checkout-dependence), is now also empirically verified — a real build from a genuinely different absolute path (`/tmp/atlas-realcopy/pyforge-atlas`, confirmed different via its own pre-normalization leaked path), normalized the same way, is byte-identical to the actual staged output.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks:**
- Open `docs/dashboard/kedro-viz/index.html` locally in a browser; confirm it renders the real 7-pipeline / ~70-node Atlas DAG (not the 77-stub-node prototype's shape, which is coincidentally similar in count but a different — MemoryDataset stub — graph)




## Auto Run Result

Status: `done`

**Summary:** The story's own implementation (CI publishing the real kedro-viz DAG via
`steward deploy dashboard`) was already complete and three-times reviewed as of `8dc004dbc0` — no
changes made to that work or to the `<intent-contract>`. This run repaired an unrelated post-
implementation failure of the bmad-loop deterministic gate (`pixi run --frozen -e pyforge-atlas
kedro-test`) reported in
`.bmad-loop/runs/20260809-034342-8683/feedback/12-2-publish-the-real-dag-continuously-1.md`: 2
failing tests in `tests/dashboard/`, root-caused, and resolved by cherry-picking an identical,
already-reviewed fix from sibling story 12-1's branch rather than re-deriving one, then re-reviewing
the result fresh against this tree (Review pass 4).

**Files changed with one-line descriptions:**
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py` — pin the factory-status
  AgGrid's `defaultColDef.cellDataType` to `"text"` so AG Grid's row-0 type inference stops
  misreading the mixed-content "status" column as a date and blanking non-date rows.
- `src/shared/packages/pyforge-atlas/tests/dashboard/test_dashboard_dryrun.py` — added a fast offline
  regression test for the above; updated `test_factory_status_reads_the_real_sprint_status`'s
  assertions from the retired `d1-`/`d2-` sprint-status.yaml key spelling to a suffix-match that
  survives the current `5-1-`/`5-2-` convention (PR #322) and any future rename.
- (commit-message-only amend, no diff change) adapted the cherry-picked commit's message to
  reference this story instead of 12-1.

**Review findings breakdown:** 2 patches applied (both low — commit-message context mismatch, spec
left undocumented), 1 deferred (low — `sprint-status.yaml` `depends_on` still spells the retired
`d1-`/`d2-` keys, inert today, re-flagged from this story's side of the same shared gate), 9 rejected
(the same tradeoffs already deliberated and accepted during 12-1's original review of this identical
diff, one refuted by the code, and documentation-only nits — see Review pass 4 for each).

**Follow-up review recommendation:** `true` (carried over from Review pass 3's judgment, unchanged
by this pass). This repair pass reviewed and patched only the small, unrelated, already-independently-
reviewed dashboard fix (2 low-severity, non-functional patches) — it did not re-review pass 3's
substantial core-story changes (determinism fixes, cross-checkout verification), so pass 3's original
follow-up recommendation still stands and is not resolved by this pass.

**Verification performed:**
- `pixi run --frozen -e pyforge-atlas kedro-test` — was failing (2 failed) at session start; now
  `912 passed, 19 skipped` (rc=0), confirmed across 2 separate runs (before and after the commit-
  message amend).
- `grep -rl "$(pwd)" docs/dashboard/kedro-viz/` — still empty (re-confirmed unaffected by the repair).
- `git status --porcelain docs/dashboard/kedro-viz` — still clean (re-confirmed unaffected).
- `pixi run --frozen -e pyforge-steward steward deploy dashboard --dry-run` — reported a diff, but
  confirmed (via `git diff --name-only` on the dry-run's own output) that the diff was entirely in
  `docs/dashboard/data.js` (Epic 2's own live fleet-status data, which legitimately drifts over time
  and is outside this story's and this repair's scope) — zero diff under `docs/dashboard/kedro-viz/`.
  The dry-run's own regeneration side-effect on `data.js` was reverted (`git checkout --`) to leave
  the working tree clean, since committing an Epic-2-owned file's regenerated content was not asked
  for by either this story or this repair.
- Root-cause isolation: confirmed via `git diff --stat` from `baseline_revision` to the pre-repair
  `final_revision` that neither `tests/dashboard/` nor `dashboard/app.py`/`factory_status.py` are
  touched by this story's own diff — the 2 failures are pre-existing and unrelated, independently
  corroborated by sibling story 12-1 hitting and fixing the identical failure from the same baseline.

**Residual risk:** low for this repair itself (2 non-functional, low-severity patches; the underlying
functional fix was already independently reviewed once on the sibling branch and is now reviewed a
second time here, both passes converging on acceptance). The carried-over pass-3 follow-up
recommendation is the more significant outstanding item — see that pass's own residual-risk framing.

## Status reconcile 2026-09-20

- frontmatter `status` `shipped` → `done` (ledger row `11-2-publish-the-real-dag-continuously-fr-62: done`).
