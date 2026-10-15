---
title: '102.5: `configure-pages` is authoritative on every host and the artifact ships as a release asset'
type: 'feature'
created: '2026-10-14'
status: 'in-review'
baseline_revision: '8ef404d388d1bdafac6aa0d96a8f626f97cad47a'
flag:
  key: pyforge.steward.pages_duty                 # Story 102.2's; the release-asset step reads its exported state
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through Epic 76's overlay
  scope: global                                   # v1 is global only
  fallback: 'no release asset is uploaded; SITE_URL still comes from configure-pages (the host-env drop is not gated: it removes a step, it adds none)'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-102-2-one-pages-workflow-in-upstream-shape-builds-on-every-change-and-deploys-only-what-changed.md
  - docs/dreams/pyforge-steward.md
  - docs/dreams/pyforge-herald.md
  - _bmad-output/brainstorming/brainstorm-pages-deployment-redesign-2026-10-13/brainstorm-intent.md
  - .github/workflows/pages.yml
  - docsite/tools/export_pages_host_env.py
  - docsite/tools/pages_second_host.py
  - docsite/tools/export_ci_surfaces_tile_env.py
  - docs/how-to/deploy-the-docs-site-to-github-enterprise-pages.md
  - docs/how-to/air-gapped-mirror-setup.md
  - docs/governance/rulesets/protected-refs.json
  - docs/governance/guild-roster.json
deferred:
  - summary: >-
      The how-to's second air-gapped option is not available: an enterprise host cannot publish the pulled
      pages-site.zip through its own GitHub Pages, because pages.yml has no input that takes a prebuilt tree in
      place of a build.
    evidence: |-
      Story 102.5's Approach names two air-gapped paths (serve the unzipped tree, or upload it as the enterprise
      Pages artifact through the mirror's pages.yml). Only the first exists: the build job always runs pages-check
      and uploads what it built. The how-to's Pull the zip section says so and recommends serving the tree as
      static files; sections 1-4 (rebuild on the mirror) remain the GitHub Actions path. Recorded as frontmatter
      by the 42.3 + 102.5 review (2026-10-15) so deferred_work_intake promotes it.
    location: >-
      .github/workflows/pages.yml (a workflow_dispatch input such as a release tag or artifact to deploy instead
      of building) and docs/how-to/deploy-the-docs-site-to-github-enterprise-pages.md section 6
    severity: low
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `pages.yml`'s build job runs a `Resolve Pages host env` step that calls herald's
`docsite/tools/export_pages_host_env.py`, which hands `SITE_URL` to the build only when `pyforge.herald.pages_second_host`
is on (herald Story 31.1, CAP-56); on github.com the flag is off and the build uses a default URL, and the GitHub
Enterprise how-to tells the enterprise operator to flip a flag in `flags.json` on their copy of `main` before the
first build. `actions/configure-pages` already emits `base_url` and `base_path` for whichever host runs the workflow.
The operator ruled 2026-10-13: `configure-pages` is authoritative on every host, the flag retires (herald's story
retires the reader; steward's drops the step and the how-to's flag section), and the same built artifact is zipped as
a release asset so the air-gapped host pulls reviewed bytes instead of rebuilding behind a mirror.

**Approach:** Remove one step, set one env, add one upload, rewrite one section.

- **The host env.** The `Resolve Pages host env` step loses its `export_pages_host_env.py` line (the
  `export_ci_surfaces_tile_env.py` line, herald CAP-59's, and Story 102.2's steward flag export stay; the step is
  renamed `Resolve build env (flags)`). The `build` job gains `env: SITE_URL: ${{ steps.pages.outputs.base_url }}`
  (and the base-path variable herald's reader names, if it names one) so `pages-check` and the Astro build read the
  deploying host's values unconditionally, on github.com and on GitHub Enterprise. The reader's retirement
  (`pages_second_host.py`, `export_pages_host_env.py`, the flag's rows in `flags.json`, `flag-overlays.json` and
  herald's inventory, `test_pages_second_host.py`) is herald Story 42.3 (CAP-60, the second host needs no flag) and is not done here; this
  story depends on it, since dropping the step before the reader stops expecting the flag would leave the GHE build
  on the default URL.
- **The release asset.** After `deploy-pages` succeeds, the `deploy` job (now `permissions: contents: write`, the
  one job that gets it) downloads the build job's `pages-site` artifact (Story 102.2 uploads it on `pull_request`;
  this story uploads it on every event), zips it as `pages-site.zip` with `build.json` inside, and publishes it on a
  rolling pre-release tagged `pages-site` on the deploying commit: `gh release view pages-site` then either `gh
  release create pages-site --prerelease --target $GITHUB_SHA --title "Pages site (rolling)" --notes "<built_from>,
  run <id>"` or `gh release delete pages-site --cleanup-tag --yes` followed by the create, then `gh release upload
  pages-site pages-site.zip --clobber`. The tag `pages-site` is outside the protected-refs rulesets
  (`archive/**`, `preserve/**`, `rescue/**`) and moving it forward along `main` orphans no commit; it is not a version
  (CalVer tags are), so no recipe reads it. The step is gated on Story 102.2's exported flag state: off, no asset.
  The `pull_request` build never reaches this step.
- **The how-to.** `docs/how-to/deploy-the-docs-site-to-github-enterprise-pages.md` loses § 4 (the flag flip) and the
  sentence in § 1 that the enterprise copy "must contain the Story 31.1 flag and `export_pages_host_env.py`
  wiring"; § 2 says `configure-pages` supplies the host's URL and base path with nothing to flip; a new section
  *Pull the zip* documents the air-gapped path: on a machine with github.com access, `gh release download pages-site
  -p pages-site.zip` (or the browser link), carry the zip across, unzip, verify `build.json`'s `built_from` against the
  mirrored `main`, and either serve the tree as static files or upload it as the enterprise Pages artifact through
  `pages.yml`'s `workflow_dispatch` on the mirror with the zip's tree in place of a build (the implementer settles
  which the how-to recommends; both are documented as the two options). The how-to is `spec-pyforge-doctor`'s
  (`docs/how-to/**`): a co-governor reconcile on its memlog, then a scoped stamp.
- **The registry.** No new row: the asset step is part of `pages.deploy`; `workflow_dispatch` runs it like any step.

Ledger key: `102-5-configure-pages-is-authoritative-on-every-host-and-the-artifact-ships-as-a-release-asset`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / S-102.2; herald Story 42.3 (CAP-60, the second host needs no flag) (the coordinator fills the key).

### Living CAP citations

- **`spec-pyforge-steward` CAP-168** (FR-41): the host-env drop, the release asset, the how-to's two edits.
- **AD-1**: `gh` and `zip` by subprocess in a workflow step; no code beyond the YAML and one shell block. **AD-8**: a
  failed upload fails the step (the deploy already succeeded; the step's failure is visible, never silent). **AD-9**:
  no new outbound endpoint; `gh` reads the repository's own host.
- **herald herald:AD-21** (one artifact, N hosts, 2026-09-28 amendment): the asset is that artifact, carried; `spec-pyforge-herald:CAP-56`
  (the second host) is realized by `configure-pages` alone once herald CAP-60 retires the flag.
- **spec-pyforge-steward CAP-165** (protected refs): the rolling tag is outside every protected pattern; the roster's
  `session_denials` are not touched.
- **Flag:** `pyforge.steward.pages_duty` (Story 102.2's).
- **Origin.** The Dream's 2026-10-13 (the Pages duct) entry; the herald Dream's M2 (the flag retires;
  `configure-pages` authoritative; the zip for the air-gapped host); brainstorm-intent § M2 ("the airgap host pulls
  reviewed bytes instead of rebuilding behind a mirror"); operator rulings 2026-10-13.

## Acceptance Criteria

- **AC1 — The step.** A test parses `pages.yml`: no step runs `export_pages_host_env.py`; the `build` job's `env`
  (or the `pages-check` step's) sets `SITE_URL` from `steps.pages.outputs.base_url`; the `export_ci_surfaces_tile_env.py`
  line and Story 102.2's steward flag export remain.
- **AC2 — The asset step.** The `deploy` job's `permissions` are `pages: write`, `id-token: write`, `contents: write`
  and nothing else; the asset step follows `deploy-pages`, is gated on the exported flag state and on
  `github.event_name != 'pull_request'`, and its shell block names `pages-site.zip`, the `pages-site` release and
  `--clobber` (asserted on the YAML text by a test).
- **AC3 — The upload (recorded).** After one deploy from `main` with the flag on in the deploying environment, `gh
  release view pages-site --json tagName,targetCommitish,assets` shows the deploying commit and one asset
  `pages-site.zip`; `unzip -l pages-site.zip` lists `build.json`; a second deploy moves `targetCommitish` and replaces
  the asset (recorded with both run ids). With the flag off at landing, the record says so and AC2 stands.
- **AC4 — Flag.** With `pyforge.steward.pages_duty` off (the exported state), the asset step is skipped by its `if:`;
  `src/shared/packages/pyforge-steward/tests/unit/test_pages_release_flag_states.py` runs the step's gating
  expression helper in `pages.py` through `flag_states("pyforge.steward.pages_duty")`: on, the step would run; off, not.
- **AC5 — The how-to.** `docs/how-to/deploy-the-docs-site-to-github-enterprise-pages.md` contains no
  `pages_second_host`, no `export_pages_host_env.py`, no "Story 31.1 flag" sentence; it has a *Pull the zip* section
  naming `gh release download pages-site -p pages-site.zip` and `build.json`; its sections are renumbered;
  `pixi run --frozen -e site docs-site-validate` exits 0 (doctor's `map.yaml` entry for the page is unchanged).
- **AC6 — Protected refs.** `python scripts/protected_refs_ruleset_check.py` exits 0 unchanged; `pages-site` matches
  none of `refs/tags/archive/**`, `refs/tags/preserve/**`, `refs/tags/rescue/**` (asserted by a test over
  `docs/governance/rulesets/protected-refs.json`).
- **AC7 — The gates.** `pixi run --frozen -e pyforge-steward pyforge-steward-test`, `flag-gate-check`, `python
  scripts/ci_surface_gates.py --check`, `detectors-ci` and `spec-surface-check` exit 0; `spec-pyforge-doctor`'s memlog
  carries the how-to reconcile and is stamped scoped.

## Boundaries & Constraints

**Always:**
- `SITE_URL` comes from `configure-pages` on every event; no flag decides it.
- `contents: write` lives on the `deploy` job only; the `build` job keeps `contents: read`.
- The asset is the deployed bytes: the same `pages-site` artifact the build job uploaded, zipped, `build.json` inside.
- The rolling tag is `pages-site`, not a version; CalVer tags stay the release versions (AGENTS.md § Dates).
- The how-to edit is a co-governor reconcile on `spec-pyforge-doctor`'s memlog and a scoped stamp.

**Never:**
- Do not delete `pages_second_host.py`, `export_pages_host_env.py` or the herald flag's tree rows (herald CAP-60's
  story).
- Do not create a release per deploy, a tag under a protected pattern, or a tag shaped like a version.
- Do not grant `contents: write` to the `build` job or add a personal token.
- Do not rebuild the site in the `deploy` job: the asset is the build job's artifact.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| github.com deploy | `configure-pages` base_url `https://rxm7706.github.io/local-recipes/` | `SITE_URL` set; build as today | — |
| GHE deploy | base_url `https://pages.ghe.example/org/local-recipes` | `SITE_URL` set; no flag | — |
| first deploy after landing | no `pages-site` release | release created, asset uploaded | — |
| later deploy | release exists | tag moved to the deploying commit, asset replaced | — |
| upload fails | `gh release upload` exit 1 | step fails, deploy already live | visible red step |
| PR build | `pull_request` | no deploy, no asset | — |
| flag off | exported state off | asset step skipped | — |
| skipped deploy | `changed=false` | deploy job skipped, so no asset either | — |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-168 (FR-41), minted 2026-10-14.
- Architecture: AD-1, AD-8, AD-9; herald herald:AD-21 (one artifact, N hosts); CAP-165 (protected refs, untouched).
- Dream: `docs/dreams/pyforge-steward.md` § Realization log, the 2026-10-13 (the Pages duct) entry.
- Epic: Epic 102, Story 102.5.
- Ledger key: `102-5-configure-pages-is-authoritative-on-every-host-and-the-artifact-ships-as-a-release-asset`.
- Ledger status at mint: `backlog`.
- Deps: S-102.2; herald Story 42.3 (CAP-60, the second host needs no flag) (cross-station, named in `Deps:`, never a blocked row; the
  coordinator fills the key). `marshal factory dispatch` stamps `baseline_revision` with the launch commit.
- Surface: `marshal-policy.toml` `[epic_surfaces]."102"`.
- Flag: `pyforge.steward.pages_duty` (Story 102.2's).

## Epic excerpt

**Type:** feature • **Effort:** S • **Deps:** S-102.2; herald Story 42.3 (CAP-60, the second host needs no flag) • **FR/AD:** spec-pyforge-steward CAP-168 (FR-41); AD-1, AD-8, AD-9; herald herald:AD-21 • flag: `pyforge.steward.pages_duty` (Story 102.2's)

**Given** a build job that takes the deploying host's URL only through herald's `pages_second_host` flag, a how-to that
asks the enterprise operator to flip it, and an air-gapped host that must rebuild behind a mirror
**When** the host-env step leaves `pages.yml` and `SITE_URL` comes from `configure-pages` on every host, the `deploy`
job uploads the built site as `pages-site.zip` on a rolling `pages-site` pre-release after each deploy from `main`,
and the how-to loses its flag step and gains the pull-the-zip path
**Then** the workflow test finds no `export_pages_host_env.py` step, `contents: write` on the deploy job only and the
asset step gated on the flag and on non-PR events; the how-to names the zip and no flag; the rolling tag matches no
protected pattern
**And** `pyforge-steward-test`, `flag-gate-check`, `docs-site-validate` and `spec-surface-check` are green, and one
deploy's release is recorded with its asset

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`;
  MRS-GATE-010 binding; it runs `src/shared/packages/pyforge-steward/tests/unit/test_pages_release.py` (AC1, AC2,
  AC6) and `src/shared/packages/pyforge-steward/tests/unit/test_pages_release_flag_states.py`, which runs the key
  `pyforge.steward.pages_duty` in both states with `pyforge.testing_kit.flags.flag_states` (AC4)).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_pages_release.py src/shared/packages/pyforge-steward/tests/unit/test_pages_release_flag_states.py -q` — expected: pass.
- `pixi run --frozen -e site docs-site-validate` — expected: exit 0 (AC5).
- `python scripts/protected_refs_ruleset_check.py` — expected: exit 0 (AC6).
- `python scripts/ci_surface_gates.py --check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog reconciles (this Spec;
  `spec-pyforge-doctor` for the how-to) and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

**Operator, after landing (AC3):**
- After one deploy from `main`: `gh release view pages-site --json tagName,targetCommitish,assets` and
  `gh release download pages-site -p pages-site.zip && unzip -l pages-site.zip | grep build.json` — expected: the
  deploying commit, one asset, `build.json` listed; recorded here with the run id.

## Named, not fixed here

- Create-or-move versus delete-and-recreate for the rolling release: the implementer's, held to AC3.
- Which air-gapped path the how-to recommends first (serve the tree, or feed it to the mirror's `pages.yml` run);
  both are documented.
- The release title and notes text.

## Spec Change Log

- 2026-10-14: specced at mint from Epic 102's Story 102.5 text, `spec-pyforge-steward` CAP-168, the live
  `dashboard.yml` step and the live how-to (§ 4 is the flag flip). The rolling pre-release (not a release per deploy,
  not a CalVer tag) is the 2026-10-14 design decision on the Spec's memlog; whether the asset also attaches to a CalVer
  release once one exists is the Spec's open question for the operator. The implementing session reads herald CAP-60's
  landed story first.
- 2026-10-15 (built with herald 42.3 in one commit, lane B; status `in-review`). Where the landed code differs:
  - **Where `SITE_URL` is set.** A job-level `env:` cannot read `steps.*`, so `SITE_URL` (from `base_url`) and herald's
    reader inputs `PAGES_HOST_BASE_URL` / `PAGES_HOST_BASE_PATH` (from `base_url` / `base_path`) sit on the
    `pages-check` step, as AC1 allows. The flag step is `Resolve build env (flags)` and no longer carries host env.
  - **The flag reaches the deploy job** through a new build-job output `pages_duty`, written by a `Carry the duty
    flag to the deploy job` step from `PYFORGE_PAGES_DUTY`. The two asset steps are gated on
    `pages.RELEASE_ASSET_IF`, which `pages.release_asset_runs` evaluates for AC4's two-state test.
  - **Rolling release.** If the release exists it is deleted (`--cleanup-tag`), then `gh release create pages-site
    --prerelease --target $GITHUB_SHA`, then `gh release upload … --clobber`. `gh` targets the running host:
    `GH_HOST` comes from `GITHUB_SERVER_URL`, and `GH_ENTERPRISE_TOKEN` is set beside `GH_TOKEN`.
  - **The how-to's second air-gapped option is not available yet.** `pages.yml` has no input that takes a prebuilt
    tree in place of a build. *Pull the zip* recommends serving the unzipped tree as static files, says the zip is
    built for the public base path, and names sections 1–4 (rebuild on the mirror) as the GitHub Actions path. Feeding
    the zip to the enterprise `pages.yml` is named, not fixed.
  - **102.2's test.** `tests/meta/test_pages_workflow.py`'s PR-upload test now expects `pages-site` on every event.
  - **AC6.** `scripts/protected_refs_ruleset_check.py` exits 1 today on live-ruleset drift that this diff does not
    touch ("missing live ruleset named 'protected-refs-tags'" and three more, plus one extra). The test over
    `protected-refs.json` shows `refs/tags/pages-site` matches no protected pattern.
  - **AC3** (the recorded upload) is the operator's, after landing.
- 2026-10-15 (the independent review, `review-42-3-102-5`: one blocker, six should-fix items and nits across 42.3 and
  102.5; the 102.5 items are resolved here, where this entry and an earlier one disagree, this one holds; the
  blocker, the flag gate's retirement rule, moved to a new doctor story by operator ruling and is not this story's):
  - **Every `gh` step names its host (should-fix).** The how-to says the enterprise copy runs `pages.yml` unchanged.
    That is now true: the two artifact downloads (steward 102.4's re-review) and the release step each export
    `GH_HOST` from `GITHUB_SERVER_URL` before `gh` runs and carry `GH_TOKEN`, `GH_ENTERPRISE_TOKEN` and `GH_REPO`;
    `configure-pages` reads the host itself, and no other step calls `gh`.
    `test_pages_release.py::test_every_gh_step_names_the_host_and_carries_the_token` pins the three steps.
  - **The live protected-refs rulesets (should-fix).** AC6's red is real and outward: live GitHub has none of the four
    declared rulesets (and one undeclared, `protected-refs-no-deletion`), so archive/preserve/rescue tags are
    unprotected. Recorded as steward row `DW-steward-102-5-1` (operator); the coordinating session runs `scribe
    capture --type project` at close. The rolling tag still matches no protected pattern (AC6's test).
  - **The rolling release is kept (nit; "Named, not fixed here" settled).** Delete-then-create left no release, and
    no asset, whenever `create` failed. An existing release is now kept: `gh api -X PATCH
    repos/$GH_REPO/git/refs/tags/pages-site -f sha=$GITHUB_SHA -F force=true` moves the tag, `gh release edit
    pages-site --target $GITHUB_SHA --notes …` moves the release's `targetCommitish` with it (GitHub does not move
    an existing tag from `target_commitish`, so the ref PATCH is what moves it), and `gh release upload … --clobber`
    replaces the asset; only a first deploy runs `gh release create`. AC2 still holds as written (the step names
    `pages-site.zip`, the `pages-site` release and `--clobber`). AC3 now also reads the tag's commit (`gh api
    repos/rxm7706/local-recipes/git/ref/tags/pages-site --jq .object.sha`) beside `targetCommitish`. A moved tag is
    rejected by `git fetch --tags` in a clone that fetched it earlier; nothing reads the tag. Test:
    `test_ac2_the_rolling_release_is_kept_and_its_tag_moved`.
  - **The `pages-site` artifact uploads for a pull request or a changed tree (nit; amends "every event").** A build
    whose tree did not change deploys nothing, so the six-hourly schedule of an unmoved tree no longer stores a
    14-day copy of the whole site: the step's `if:` is `github.event_name == 'pull_request' ||
    steps.stamp.outputs.changed == 'true'`, and the deploy job (its one reader) still runs only on a changed tree.
    Tests: `test_ac2_the_site_artifact_uploads_for_a_pr_or_a_changed_tree` and 102.2's
    `test_pages_yml_pr_artifact_upload_shape`.
  - **`RELEASE_ASSET_IF` is pinned (nit)** as an exact string in `test_ac2_the_gate_reads_the_build_jobs_exported_duty_flag`,
    so the constant and the YAML cannot drift together unnoticed.
  - **AC3's record (nit).** No workflow sets `PYFORGE_ENVIRONMENT`, so CI resolves the `dev` overlay, where
    `pyforge.steward.pages_duty` is on: the asset publishes from the first changed deploy after landing, and AC3's
    "flag off at landing" branch will not apply.
  - **The how-to (nit).** *Pull the zip* says the asset depends on `pyforge.steward.pages_duty`, and that `tree_hash`
    cannot be recomputed from the zip (it covers the build tree's hidden `.pages-build-site-url` and
    `herald/.nojekyll`, which the artifact uploads leave out), so `built_from` is the integrity check.
    `tree_hash` itself is unchanged: changing what it covers would change every deploy decision.
  - **`contents: write` stays job-wide on `deploy`**, as AC2 requires; a separate release job (so `deploy-pages` and
    `download-artifact` would not run with it) needs an AC2 amendment and is not taken here.
  - **The unavailable second air-gapped option** is a `deferred:` frontmatter entry, so `deferred_work_intake`
    promotes it.
  - **`marshal-policy.toml`'s Epic 102 surface** names `docsite/tools/pages_site_url.py`, not the retired
    `pages_second_host.py`.
- 2026-10-15 (the lane-B re-review, `rereview-laneb`: 102.5 RESOLVED; one nit done here): **the tag moves first,
  release or not.** A `pages-site` tag left without its release (a release deleted by hand) sent the step down the
  create path, where `gh release create --target` adopts the existing tag at its old commit. The step now reads
  `repos/$GH_REPO/git/ref/tags/pages-site` and, when the tag exists, moves it to the deploying commit before `gh
  release view`; then it edits the kept release or creates the first one, and uploads with `--clobber`.
  `test_ac2_the_rolling_release_is_kept_and_its_tag_moved` pins the order.
