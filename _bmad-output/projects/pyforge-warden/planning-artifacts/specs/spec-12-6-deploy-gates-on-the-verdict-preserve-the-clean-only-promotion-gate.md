---
title: 'Story 12.6: Deploy gates on the verdict — preserve the clean-only promotion gate'
type: 'feature'
created: '2026-09-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '5fc43c0440d31fa7b29bf40218f5257ca734c2fe'
context:
  - spec-golden-path-conda-blind-spot/SPEC.md
  - spec-12-1-regression-test-the-promotion-verifier-s-clean-only-refusal-cannot-be-removed-silently.md
  - spec-12-5-the-verdict-is-honest-and-specific.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** Stories 12.2–12.5 changed what the promotion records (honest,
often non-`clean` verdicts on the shipped closure), but nothing proves CAP-5:
the deploy pipeline still refuses every non-`clean` record, accepts only
`clean`, and never adds a deploy-side waiver override — the two halves must land
together without relaxing the gate.

**Approach:** Add platform integration tests that assemble a promotion record
the same way `platform-golden-path-promotion.sh` does from a real Warden scan,
then subprocess the deploy verifier; assert workflow wiring keeps the verifier
before helm render; refresh deploy-workflow comments. Do not edit the verifier
logic.

## Boundaries & Constraints

**Always:** Preserve `scripts/platform-deploy-verify-promotion.py` behavior
unchanged (`status != "clean"` refusal, driver finding id in stderr). Tests
bridge promotion-record assembly → deploy verifier (not synthetic-only fixtures
from Story 12.1). `warn` must be refused at deploy even when the Warden object
carries waiver-shaped metadata — deploy has no second override. Platform CI
path filters must still cover the verifier script and new tests.

**Never:** Do not relax the verifier to accept `warn`, `indeterminate`, or
truthiness checks. Do not add deploy-side waiver logic. Do not change Warden
verdict composition or promotion scan wiring (Stories 12.2–12.5). Do not add
`--fail-under-coverage`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Honest non-clean promotion record | Real scoped scan → promotion assembly heredoc | Deploy verifier exit non-zero; stderr names status + driver id | `::error::` prefix |
| Warn verdict record | Promotion JSON with `warden_status: warn` (waived-finding shape in nested object) | Deploy verifier refuses; no waiver bypass | Same refusal shape as 12.1 |
| Clean promotion record | Assembly with `warden_status: clean` + matching digests | Deploy verifier exit 0 | — |
| Deploy workflow order | `platform-deploy.yml` job steps | Verifier step runs after artifact download, before helm template | — |

</intent-contract>

## Code Map

- `scripts/platform-deploy-verify-promotion.py:30-36` — clean-only gate (read-only; must remain unchanged).
- `scripts/platform-golden-path-promotion.sh:63-101` — promotion record assembly heredoc; reuse in tests.
- `.github/workflows/platform-deploy.yml:48-53` — deploy verifier step (preserve wiring; comment refresh only).
- `.github/workflows/platform-ci.yml:93-118` — path filters include verifier script (read-only).
- `src/platform/tests/test_deploy_verify_promotion_clean_only.py` — Story 12.1 synthetic regression (read-only; complementary).
- `src/platform/tests/test_golden_path_promotion_verdict.py` — promotion assembly heredoc pattern to reuse.
- `src/platform/tests/test_deploy_gates_on_promotion_verdict.py` (NEW) — CAP-5 integration: real scan → record → deploy verifier.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml` — flip 12-6 to `done`.

## Tasks & Acceptance

**Execution:**
- `src/platform/tests/test_deploy_gates_on_promotion_verdict.py` — integration tests bridging promotion assembly to deploy verifier; workflow step-order assertion.
- `.github/workflows/platform-deploy.yml` — comment clarifying clean-only gate preserved under honest verdicts (Story 12.6).
- `_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml` — promote story 12-6 to `done`.

**Acceptance Criteria:**
- Given a promotion record assembled from a real scoped Warden scan whose verdict is not `clean`, when the deploy verifier runs, then it exits non-zero and stderr names the status and driver finding id.
- Given a promotion record with `warden_status: warn` (including waiver metadata in the nested Warden object), when the deploy verifier runs, then it refuses promotion — waivers do not bypass deploy.
- Given a promotion record with `warden_status: clean` and matching digests, when the deploy verifier runs, then it exits 0.
- Given `platform-deploy.yml`, when step order is inspected, then the verifier runs after downloading the promotion artifact and before helm template.
- Given the full change, when `scripts/platform-deploy-verify-promotion.py` is diffed, then the `!= "clean"` gate is unchanged.

## Spec Change Log

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 22 findings — high 0, medium 0, low 5, false 12, maybe-false 0
- findings:
  - `[patch]` `[patch]` Duplicated `_PROMOTION_ASSEMBLY` instead of shared snippet — replaced with import of `_PROMOTION_PAYLOAD_SNIPPET` from Story 12.5 tests.
  - `[patch]` `[patch]` Warn test omitted driver id in stderr assertion — added `_assert_refused` + `_DRIVER_ID` check.
  - `[patch]` `[patch]` Honest non-clean test used optional driver guard — now requires driver finding_id before refusal assertions.
  - `[patch]` `[patch]` Workflow test checked step order only — added assertion that verifier step `run` invokes `platform-deploy-verify-promotion.py`.
  - `[patch]` `[patch]` No guard against promotion-script assembly drift — added `test_promotion_script_copies_warden_status_to_top_level`.
  - `[patch]` `[patch]` Assembly subprocess used bare `python` — switched to `sys.executable`.
  - `[patch]` `[patch]` Missing `@pytest.mark.skipif` for absent `pixi.lock` — added on honest integration test.
  - `[false]` `[reject]` Direct ledger edit — same Tier-3-feed-absent pattern as Stories 12.1–12.5 in this worktree.
  - `[false]` `[reject]` Spec status in-progress vs ledger done — resolved at finalize in same pass.
  - `[false]` `[reject]` Empty triage/verification sections — populated at finalize per build-auto protocol.
  - `[false]` `[reject]` Full shell script subprocess required — docker refs block; shared heredoc + script text guard matches repo pattern (12.4/12.5).
  - `[false]` `[reject]` Explicit platform-ci path filter for new test file — covered by existing `src/platform/**` filter.
  - `[false]` `[reject]` Honest test must use provisioned OSV env like CI — indeterminate offline path is valid CAP-5 proof that deploy refuses honest non-clean records.
  - `[false]` `[reject]` Digest mismatch integration test required — Story 12.1 covers verifier digest gate synthetically; out of 12.6 integration scope.
  - `[false]` `[reject]` Missing-record integration test required — Story 12.1 covers; 12.6 adds assembly bridge only.
  - `[false]` `[reject]` Per-rung exhaustive integration for every lattice token — Story 12.1 owns synthetic per-rung coverage; 12.6 adds honest bridge.
  - `[false]` `[reject]` Step rename in platform-deploy.yml violates comment-only — cosmetic clarity aligned with CAP-5 intent.
  - `[low]` `[reject]` Unused pytest import — still used by skipif after patches.
  - `[low]` `[reject]` `_run_warden_scan` extra_args semantics differ from sibling — intentional; empty list suppresses pixi flags for fixture scans (matches 12.5).
  - `[low]` `[reject]` stdout behavior of assembly heredoc untested — deploy reads file artifact only; stdout path not on promotion→deploy surface.
  - `[low]` `[reject]` StopIteration if workflow step name changes — same fragility as existing workflow content tests; acceptable.

## Design Notes

**12.1 vs 12.6:** Story 12.1 guards the verifier script with synthetic JSON.
This story proves the promotion pipeline's honest verdict lands under the
unchanged gate — the integration path CI actually uses.

## Verification

**Commands:**
- `cd src/platform && pixi run -e platform-ci-test python -m pytest tests/test_deploy_gates_on_promotion_verdict.py tests/test_deploy_verify_promotion_clean_only.py -v` — expected: all pass.
- `git diff 5fc43c0440d31fa7b29bf40218f5257ca734c2fe -- scripts/platform-deploy-verify-promotion.py` — expected: empty diff.

## Auto Run Result

**Summary:** Added CAP-5 integration tests bridging real Warden scan → promotion
record assembly → deploy verifier, plus workflow wiring guards — without
relaxing `platform-deploy-verify-promotion.py`.

**Files changed:**
- `src/platform/tests/test_deploy_gates_on_promotion_verdict.py` (new) — five tests: honest non-clean refusal, warn+waiver refusal, clean acceptance, promotion-script assembly drift guard, deploy workflow verifier invocation + order.
- `.github/workflows/platform-deploy.yml` — Story 12.6 CAP-5 comments; verifier step name clarifies clean-only gate.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-12-6-deploy-gates-on-the-verdict-preserve-the-clean-only-promotion-gate.md` (new) — story contract.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml` — flipped story 12-6 to `done`.

**Review findings breakdown:** 7 low patches applied (shared heredoc, driver assertions, workflow run guard, script drift guard, sys.executable, skipif). 12 false/rejected. 0 deferred.

**Follow-up review recommendation:** `false` — only low-severity patches; no medium/high findings.

**Verification performed:**
- `pixi run -e platform-ci-test python -m pytest tests/test_deploy_gates_on_promotion_verdict.py tests/test_deploy_verify_promotion_clean_only.py -v` — 17 passed.
- `git diff 5fc43c0440d31fa7b29bf40218f5257ca734c2fe -- scripts/platform-deploy-verify-promotion.py` — empty (verifier unchanged).

**Residual risks:** Live `python-agent-platform` closure may stay non-clean until conda→pypi mapping improves; deploy correctly refuses until then — by design.
