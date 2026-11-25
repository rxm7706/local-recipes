---
title: '134.1: The promotion records the registry digest after a push, and the image ID when nothing is pushed'
type: 'fix'
created: '2026-11-25'
status: 'done'
story: 134-1-the-promotion-records-the-registry-digest-after-a-push-and-the-image-id-when-nothing-is-pushed
spec: spec-pyforge-steward
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'scripts/platform-golden-path-promotion.sh'
  - 'scripts/platform-deploy-verify-promotion.py'
  - 'scripts/platform-ci-local.sh'
  - '.github/workflows/platform-ci.yml'
  - '.github/workflows/platform-deploy.yml'
  - 'src/platform/deploy/charts/platform/templates/_helpers.tpl'
  - 'src/platform/tests/test_golden_path_promotion_verdict.py'
  - 'src/platform/tests/test_golden_path_promotion_osv_db.py'
  - 'src/platform/tests/test_golden_path_promotion_closure.py'
  - 'src/platform/tests/test_deploy_gates_on_promotion_verdict.py'
  - 'src/platform/tests/test_deploy_verify_promotion_clean_only.py'
  - 'src/platform/tests/test_chart_invariants.py'
  - 'tests/scripts/test_platform_promotion_digest.py'
  - 'docs/explanation/platform-deployment-architecture.md'
  - 'docs/reference/github-workflows.md'
  - 'docs/how-to/github-actions-recipe-ci.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-steward-133-2-1`. The promotion artifact calls an image ID a digest, in four places:

1. `scripts/platform-golden-path-promotion.sh:28-31`: `image_digest` reads `docker inspect --format='{{.Id}}'`, the local image ID, and the payload writes it under `images.platform.digest`, `images.sidecar.digest` and `images.mcpHost.digest`.
2. `.github/workflows/platform-ci.yml`, job `golden-path-promotion`: the step "Record digests + Warden verdict" runs before the step "Push images by digest (optional)", so no registry digest exists when the artifact is written; the push step then prints the image IDs as "digest (local id)".
3. `scripts/platform-ci-local.sh`, `stage_promotion`: it reads the same `{{.Id}}` values and hands them to the deploy verifier as `PLATFORM_DIGEST`, `SIDECAR_DIGEST` and `MCP_HOST_DIGEST`.
4. `scripts/platform-deploy-verify-promotion.py:38-54` compares the three requested digests to `images.*.digest`, and `.github/workflows/platform-deploy.yml` then renders the chart with `image.digest` set to them. An image ID after `@` names nothing a registry serves, so a deploy by a recorded "digest" could not pull.

A registry manifest digest exists only after a push, and the push is optional (`vars.PLATFORM_CI_PUSH_REGISTRY`).

**Approach:** The operator ruled on 2026-11-25 ("Registry digest"): record the real registry manifest digest after a push; when nothing is pushed, record the image ID under a separate `image_id` key and leave `digest` empty; the deploy verifier checks whichever is present.

Reproduce first: a test under `tests/scripts/` runs the promotion script with a stand-in `docker` and a stand-in `warden` on `PATH` and fails on the unchanged tree because `images.platform.digest` equals the image ID. Then:

- The promotion script writes `image_id` for every image, always. It writes `digest` from the pushed reference when one is given for that image (the manifest digest the engine reports for that registry repository, `sha256:` and 64 hex characters) and an empty string otherwise. It never writes an image ID under `digest`.
- `platform-ci.yml` pushes before it records when the push is on, and gives the script the pushed references; with the push off the order of the other steps is unchanged. The step that printed image IDs as digests prints what each value is.
- The verifier takes the three requested digests as today and, beside them, three requested image IDs. For each image it compares the digest when the artifact records one, the image ID when it records none, and refuses a request for a digest the artifact does not hold. The Warden verdict rule is unchanged: only `clean` promotes.
- `platform-deploy.yml` gives the chart `image.digest` only from a recorded registry digest. Where only an image ID is recorded, its verify step still runs and its render step says a registry deploy needs a pushed digest.
- `stage_promotion` of `platform-ci-local.sh` passes its image IDs as image IDs.
- `_helpers.tpl` keeps its rule (a digest or a pinned tag, never `latest`); it changes only if a test shows it would render an image ID after `@`.

Ledger key: `134-1-the-promotion-records-the-registry-digest-after-a-push-and-the-image-id-when-nothing-is-pushed`.

### Living CAP citations

- spec-pyforge-unifying-strategy, the Constraint "deploys pin an image digest with a recorded Warden verdict" (Story 43.4; realized, no text change), and spec-pyforge-steward CAP-175 (the platform suite's local replay; realized, no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce before fixing: the failing test is written and run on the unchanged tree first, and its failure is recorded in the Spec Change Log.
- Keep the artifact's `schema` value and every key it has today; `image_id` is added, nothing is renamed or removed.
- Keep the verifier's refusal of any verdict but `clean`, and its order before the chart render.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never push an image, dispatch a workflow or turn `PLATFORM_CI_PUSH_REGISTRY` on to test this; the tests use stand-in commands.
- Never write an image ID under a key named `digest`, in the artifact, a workflow output or a log line.
- Never import `pyforge` in a changed file under `src/platform/`.
- Never make the push required: with it off, the promotion still records the verdict and the image IDs.

## Acceptance Criteria

**Given** `DW-steward-133-2-1` reports that `scripts/platform-golden-path-promotion.sh` writes `docker inspect --format='{{.Id}}'`, the local image ID, under `images.*.digest`, that `platform-ci.yml` records the artifact before its optional push, and that the promotion stage of `platform-ci-local.sh` hands the same image IDs to the deploy verifier as digests
**When** the defect is first reproduced by a test that fails on the unchanged tree, and then the workflow pushes before it records, the promotion script writes each image's registry manifest digest under `images.*.digest` when a pushed reference is given and its image ID under `images.*.image_id` always, and the verifier compares whichever of the two the artifact holds
**Then** an artifact recorded after a push carries a `sha256:` manifest digest the registry serves under `digest` and the image ID under `image_id`, an artifact recorded with nothing pushed carries an empty `digest` and the image ID under `image_id`, and no code path writes an image ID under `digest`
**And** the deploy verifier accepts a requested digest that equals the recorded one, accepts a requested image ID that equals the recorded one when no digest is recorded, and refuses a mismatch, a request for a digest the artifact does not hold, and any verdict but `clean`, as before
**And** `platform-deploy.yml` hands the chart `image.digest` only from a recorded registry digest, the chart never renders an image ID after `@`, the local promotion stage passes image IDs as image IDs, and `DW-steward-133-2-1` reads resolved naming the outcome

- **AC1 — The promotion script and the verifier are held by tests in the scripts suite.** `tests/scripts/test_platform_promotion_digest.py` runs both scripts with stand-in commands and fails by name on: an image ID under `digest`; a missing `image_id`; a non-empty `digest` when no pushed reference was given; a pushed reference whose manifest digest is not the one recorded; a verifier that accepts an image ID where a digest is recorded and differs; a verifier that accepts a requested digest the artifact does not hold. Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_platform_promotion_digest.py -q
  ```

- **AC2 — No script or workflow of the promotion path reads an image ID into a digest.** The check prints every line of the four files where `{{.Id}}` and the word `digest` (any case) share a line. Expected: exit 1 (no line matches).

  ```bash
  grep -n -i -E "\{\{\.Id\}\}.*digest|digest.*\{\{\.Id\}\}" scripts/platform-golden-path-promotion.sh scripts/platform-ci-local.sh .github/workflows/platform-ci.yml .github/workflows/platform-deploy.yml
  ```

- **AC3 — The workflow pushes before it records.** A test in AC1's module reads `platform-ci.yml` and fails by name when the push step of `golden-path-promotion` stands after the record step, or when the record step is not given the pushed references. Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-ci python -m pytest tests/scripts/test_platform_promotion_digest.py -q -k workflow
  ```

- **AC4 — The platform suite's test stage passes**, with the promotion, verifier and chart tests of `src/platform/tests/` updated to the two keys. Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild platform-ci-local -- --test
  ```

- **AC5 — The scripts suite and steward's live-tree suite pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test && pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```

- **AC6 — The generated workflow reference matches the workflows**, if an input of `platform-deploy.yml` moved. Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild docs-github-workflows -- --check
  ```

- **AC7 — The row is closed.** `DW-steward-133-2-1` carries a `resolution:` line naming this story and reads `status: resolved`. Expected: prints 1, exit 0.

  ```bash
  grep -c -E "^  resolution: 2026-[0-9-]+, steward Story 134\.1 " _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-unifying-strategy, the Constraint "deploys pin an image digest with a recorded Warden verdict" (Story 43.4; realized, no text change), and spec-pyforge-steward CAP-175 (realized, no text change); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the open rows close, and one verb says whether a machine is ready); operator rulings of 2026-11-25: "fix all these issues / left open items" and, on this row, "Registry digest".
- Epic: Epic 134, minted with this story.
- Ledger key: `134-1-the-promotion-records-the-registry-digest-after-a-push-and-the-image-id-when-nothing-is-pushed`.
- Deferred-work row: `DW-steward-133-2-1`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."134"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry and the operator's rulings of the same date. Not implemented.
- 2026-11-25: reproduced on the unchanged tree. `tests/scripts/test_platform_promotion_digest.py`, written first, ran `scripts/platform-golden-path-promotion.sh` against a stand-in `docker` and `warden`: 20 failed, 6 passed, exit 1; the first failure reads `images.mcpHost.digest holds the image ID`. The six that passed were the verifier's existing refusals (a differing digest, any verdict but `clean`).
- 2026-11-25: changed. The promotion script records `image_id` always, `digest` from the `RepoDigests` entry of the pushed reference's repository when `PLATFORM_PUSHED_REF`, `SIDECAR_PUSHED_REF` or `MCP_HOST_PUSHED_REF` is given (it must be `sha256:` and 64 hex characters, or the record fails) and an empty `digest` otherwise; `pushed_ref` is recorded beside them. `platform-ci.yml` pushes (step id `push`) before it records and hands the three pushed references over. The verifier compares the digest where one is recorded and the image ID where none is, refuses a requested digest the artifact does not hold, and writes `by_digest` and the three verified digests to `GITHUB_OUTPUT`. `platform-deploy.yml` gains three optional image ID inputs, its digest inputs become optional, and its render step takes the digests from the verify step's outputs and fails saying a registry deploy needs a pushed digest when the artifact records none. `stage_promotion` passes `PLATFORM_IMAGE_ID`, `SIDECAR_IMAGE_ID` and `MCP_HOST_IMAGE_ID`.
- 2026-11-25: the artifact's `schema` stays `platform-golden-path-promotion/v1`; `image_id` and `pushed_ref` are additions and no key is renamed or removed. An artifact written before this story (no `image_id` key, an image ID under `digest`) is read as an image ID and never as a digest.
- 2026-11-25: `_helpers.tpl` changed, on a test's evidence. With the unchanged helper, `helm template --set-string image.digest=<64 hex>` (the bare form podman prints for an image ID) rendered `image: platform@1111…`, exit 0. The helper now refuses a digest that is not `sha256:` and 64 hex characters, naming the values path. A docker image ID has the same form as a manifest digest, so the chart cannot refuse that one: the artifact's two keys and the deploy workflow's render-from-the-verifier rule hold it.
- 2026-11-25: verified. AC1 26 passed, exit 0. AC2 exit 1 (no line). AC3 5 passed, exit 0. AC4 `platform-ci-local -- --test` on free ports under `LC_ALL=en_US.UTF-8`: every step PASS, 1568 passed and 23 skipped, exit 0. AC6 exit 0 after regenerating `docs/reference/github-workflows.md` (the inputs of `platform-deploy.yml` moved). The steward tests that read these workflows and scripts: 126 passed, 1 skipped.
- 2026-11-25: left open. (1) No container engine or registry exists on this host: `docker push`, the `RepoDigests` a real engine reports after it, the reordered job and `platform-deploy.yml` were not run; the stand-in engine is the only proof of the script's reading. (2) AC5 exits 1 on other stories' work in the shared worktree, none of it this story's: `pyforge-doctor-scripts-test` 9 failed (7 `test_pre_shell_hook.py::test_134_2_*`, 2 `test_tea_playwright_check.py` on story ids missing from the test-architecture matrices, 134.1 among them); `pyforge-steward-live-test` 4 failed and 1 error (Story 135.1's `steward init` and mason's story count). (3) AC7: the implementing agent was told not to edit the deferred-work ledger; the row's `resolution:` and `status: resolved` are the session lead's to write.
- 2026-11-25: review findings closed. (1) The push step of `platform-ci.yml` is named `Push images by digest (optional; CAP-6 registry via vars)` again, the name `docs/governance/ci-surfaces.yaml` rows `platform-ci.golden-path-promotion.push-registry` and `.registry-value` read; it pushes the images whose registry digests the record step then reads, so the name stays accurate. (2) `docs/how-to/github-actions-recipe-ci.md` no longer says all four inputs of `platform-deploy.yml` are required: only `ci_run_id` is, with the three digests for a pushed run or the three image IDs for a run that pushed nothing; it joins this story's surface. (3) Three verifier guards gained tests, each red with its guard removed in a scratch copy: a recorded digest that is not `sha256:` and 64 hex (one carrying a newline and `by_digest=true`, one `sha256:short`) is refused even when requested verbatim and `GITHUB_OUTPUT` stays empty; a pushed artifact with the right digests and a wrong requested image ID is refused; a partly pushed artifact verifies with `by_digest=false`, the platform digest set and the other two empty.
- 2026-11-25: the verifier refuses, with its own `::error::` line and exit 1 and no traceback, an artifact that is not JSON, that is not a JSON object, whose `images` is not a mapping (a missing `images` now fails here too, where it failed later on the first image before), or whose image entry is not a mapping; a Warden `status` or `driver` that is not a mapping reads as empty instead of raising. One parametrized test holds the four refusals; each case is red with its guard removed.
- 2026-11-25: `registry_digest` in `scripts/platform-golden-path-promotion.sh` now reads the pushed reference's image ID and fails with `::error::pushed reference <ref> is not the image recorded as <local ref>` when it differs from the local image's, so the artifact never pairs one image's ID with another's digest. The stand-in engine now gives each pushed reference an image ID; a new test gives one a different ID and the record fails with that error and writes no artifact (red with the comparison removed). `docs/explanation/platform-deployment-architecture.md` says both. Verified: `tests/scripts/test_platform_promotion_digest.py` 35 passed, exit 0.
- 2026-11-25: re-review finding closed. The two verifier guards an earlier entry names without a test (a Warden `status` or `driver` that is not a mapping) gained them, as two more cases of `test_verifier_refuses_a_malformed_artifact_with_its_own_error`: a Warden `status` that is a string, not a mapping, is refused with `Warden verdict is None, not 'clean' (driver: None)`; a `driver` that is a string is refused with `Warden verdict is 'warn', not 'clean' (driver: None)`; each exits 1 with `::error::` and no traceback. Each case was red with its guard reverted in place (the `isinstance(warden_status, dict)` fallback removed: 1 failed; the `isinstance(driver, dict)` test replaced by `is not None`: 1 failed) and the script was restored byte-identical. Verified: `tests/scripts/test_platform_promotion_digest.py` 37 passed, exit 0.
- 2026-11-25: closed. Implemented, independently reviewed against this spec, its findings applied and re-reviewed; the full local `pr-preflight` gates the PR that lands it (branch `open-rows-and-onboarding-2026-11-25`).
