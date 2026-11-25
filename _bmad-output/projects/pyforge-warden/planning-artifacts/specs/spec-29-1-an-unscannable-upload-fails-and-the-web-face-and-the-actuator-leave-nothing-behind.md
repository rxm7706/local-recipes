---
title: '29.1: An unscannable upload fails, and the web face and the actuator leave nothing behind'
type: 'fix'
created: '2026-11-25'
status: 'done'
story: 29-1-an-unscannable-upload-fails-and-the-web-face-and-the-actuator-leave-nothing-behind
spec: spec-pyforge-warden
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/django-warden/src/django_warden_fabric/views.py'
  - 'src/shared/packages/django-warden/src/django_warden_fabric/tasks.py'
  - 'src/shared/packages/django-warden/src/django_warden_fabric/proposals.py'
  - 'src/shared/packages/django-warden/src/django_warden_fabric/templates/warden_fabric/fleet_proposals.html'
  - 'src/shared/packages/pyforge-warden/src/pyforge/warden/actuator.py'
  - 'src/shared/packages/pyforge-warden/src/pyforge/warden/discovery.py'
  - 'src/platform/tests/test_warden_portal_job_outcomes.py'
  - 'src/platform/tests/test_warden_fleet_proposal_recovery.py'
  - 'src/platform/tests/test_warden_fleet_proposal_stale_portal.py'
  - 'src/shared/packages/pyforge-warden/tests/unit/test_actuator.py'
  - 'src/shared/packages/pyforge-warden/tests/unit/test_actuator_github_client.py'
  - 'src/shared/packages/pyforge-warden/tests/unit/test_non_python_lockfiles.py'
  - '_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/contract.md'
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-warden.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The review of main `7da08791f3` reported five defects in the compliance web face (`django-warden`) and the fix-PR actuator, written as `DW-warden-review-2026-11-24-1`. They were reviewer-reported and not re-traced by the session lead, so each is a claim until a test shows it.

1. **A job succeeds on a file the scan cannot read.** The upload and the job admit any file whose suffix is listed (`SUPPORTED_SUFFIXES` in `tasks.py`, used by `views.py`), which is wider than the manifest names warden's discovery reads; `run_compliance_job` discards the scan's exit code, so such a file ends `SUCCEEDED` with a not-applicable report. `_run_warden_engines` returns `"{}"` as the SBOM every time, and `job_report` returns it for `?kind=sbom` with 200.
2. **An uploaded blob is never deleted.** Nothing removes the stored file or its directory under `COMPLIANCE_FACE_BLOB_ROOT` when the job ends.
3. **A failed fix-PR open leaves its mark.** `GitHubForgeClient.open_pull_request` in `actuator.py` leaves the branch it created when a later call fails, and the next run reads the branch as a prior actuation and skips the finding; a missing base sha yields a commit with `parents: []`; `_api` sends the bearer token through `urllib`'s default redirect handling, so a redirect to another host carries it.
4. **An approved proposal can stay approved forever.** `approve_proposal` refuses a proposal already `APPROVED` and `dismiss_proposal` refuses any state but `QUEUED` (`proposals.py`), so a proposal whose worker died before it opened can never be closed. (The row also asks for a retry; the lead's ruling of 2026-11-25 retires it, see the Approach.)
5. **A whole-run actuator failure loses its cause.** A failure that stops the run before any proposal is tried is recorded without the exception's type and message, and the fleet open task (`open_fix_proposal` in `tasks.py`) writes a fixed string on the proposal instead of that record.

**Approach:** For each defect write the failing test first, on the tree as it stands. A defect the test cannot show is recorded in the Spec Change Log as not a defect, with the command that was run, and no code moves for it. For the ones shown, under the lead's rulings of 2026-11-25:

- **Defect 1.** Admit only the manifest names warden's discovery reads under the current flags. `pyforge.warden.discovery` gains one public function, `discovered_manifest_names()`, and `django-warden` calls it through a function-local import, never a second list and never a private name; a native non-Python lockfile name is admitted only while `pyforge.warden.non_python_ecosystems` is on. Fail a job whose scan read no manifest. Store the engine's own SBOM or answer `?kind=sbom` with 404.
- **Defect 2.** Remove the blob when the job ends, succeeded or failed.
- **Defect 3.** Delete the ref only when the pull-request POST itself raised; a 2xx with no url raises and leaves the branch, because the forge accepted the open and deleting a pull request's head branch closes it. Fail the open before any commit when the base sha is missing. Send the token to no host but the configured API host.
- **Defect 4.** Let an `APPROVED` proposal older than the approval expiry be dismissed, and list such a proposal on the proposals page with a Dismiss form only, so the operator can reach it. It is never approved again: the open task refuses any approval of a proposal queued longer than that same expiry, so a second approve could not open a pull request, and `approve_proposal` keeps refusing it.
- **Defect 5.** Record the exception type and message of a whole-run failure in `actuation`, and in `open_fix_proposal`, when no outcome names the finding, store that whole-run record's detail as the proposal's error.

Ledger key: `29-1-an-unscannable-upload-fails-and-the-web-face-and-the-actuator-leave-nothing-behind`.

### Living CAP citations

- spec-pyforge-warden CAP-12, CAP-16, CAP-17, CAP-24, CAP-29 (realized, no text change); no AD moves; no warden FR.

## Boundaries & Constraints

**Always:**
- Reproduce a defect with a failing test before changing the code it names.
- Keep the platform's tests free of any `pyforge` import, and keep every `pyforge.warden` import in `django-warden` function-local.
- Keep a failed PR open out of the verdict and the exit code: it lands in `actuation` only (CAP-12).
- Keep a job status and a proposal state a lifecycle, never a verdict (CAP-29).
- Read the upload's admitted names from `pyforge.warden.discovery.discovered_manifest_names()`, a public function, so the upload and the scan follow the same flag.
- Delete the fix branch only when the pull-request POST itself raised.

**Never:**
- Never add a flag, a model field or a migration in this story.
- Never fix a defect the tree does not reproduce.
- Never widen the estate allowlist or let anything open on a fleet repo without the operator's approve.
- Never approve a stale `APPROVED` proposal again; it may only be dismissed.
- Never delete the branch of a pull request the forge accepted, even when its reply carried no url.
- Never read a private name of `pyforge.warden` from `django-warden`.

## Acceptance Criteria

**Given** `DW-warden-review-2026-11-24-1` reports the five defects above
**When** each is first reproduced by a failing test and then fixed as the Approach says
**Then** the warden suite and the platform suite exit 0 with a test per defect that fails on the tree before the fix
**And** a defect the tree does not reproduce is recorded in the Spec Change Log as not a defect, with the command that was run, and its criterion below is met by that record

- **AC1 — An unscannable upload fails as a job, and the SBOM is real or absent (defect 1).** `test_warden_portal_job_outcomes.py` holds `test_upload_of_a_name_discovery_does_not_read_is_refused`, `test_upload_of_a_native_lockfile_follows_the_flag`, `test_job_whose_scan_read_no_manifest_fails`, `test_job_whose_real_scan_reads_no_manifest_fails` and `test_sbom_kind_is_the_engine_sbom_or_404`; `test_non_python_lockfiles.py` holds `test_discovered_manifest_names_follow_the_flag`. Expected: exit 0 from each command.

  ```bash
  grep -q "def test_upload_of_a_name_discovery_does_not_read_is_refused" src/platform/tests/test_warden_portal_job_outcomes.py && grep -q "def test_upload_of_a_native_lockfile_follows_the_flag" src/platform/tests/test_warden_portal_job_outcomes.py && grep -q "def test_job_whose_scan_read_no_manifest_fails" src/platform/tests/test_warden_portal_job_outcomes.py && grep -q "def test_job_whose_real_scan_reads_no_manifest_fails" src/platform/tests/test_warden_portal_job_outcomes.py && grep -q "def test_sbom_kind_is_the_engine_sbom_or_404" src/platform/tests/test_warden_portal_job_outcomes.py
  grep -q "def test_discovered_manifest_names_follow_the_flag" src/shared/packages/pyforge-warden/tests/unit/test_non_python_lockfiles.py
  pixi run -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/unit/test_non_python_lockfiles.py -q
  pixi run -e pyforge-guild platform-ci-local -- --test
  ```

- **AC2 — The blob is gone when the job ends (defect 2).** The same module holds `test_blob_is_removed_after_a_succeeded_job` and `test_blob_is_removed_after_a_failed_job`. Expected: exit 0 from each command.

  ```bash
  grep -q "def test_blob_is_removed_after_a_succeeded_job" src/platform/tests/test_warden_portal_job_outcomes.py && grep -q "def test_blob_is_removed_after_a_failed_job" src/platform/tests/test_warden_portal_job_outcomes.py
  pixi run -e pyforge-guild platform-ci-local -- --test
  ```

- **AC3 — A pull-request POST that raised leaves no branch, an accepted open keeps its branch, and there is no parentless commit and no token on another host (defect 3).** `test_actuator_github_client.py` holds `test_failed_open_deletes_the_ref_it_created`, `test_an_accepted_open_with_no_url_keeps_its_branch`, `test_missing_base_sha_fails_before_any_commit` and `test_bearer_is_not_sent_to_another_host_on_redirect`. Expected: exit 0.

  ```bash
  grep -q "def test_failed_open_deletes_the_ref_it_created" src/shared/packages/pyforge-warden/tests/unit/test_actuator_github_client.py && grep -q "def test_an_accepted_open_with_no_url_keeps_its_branch" src/shared/packages/pyforge-warden/tests/unit/test_actuator_github_client.py && grep -q "def test_missing_base_sha_fails_before_any_commit" src/shared/packages/pyforge-warden/tests/unit/test_actuator_github_client.py && grep -q "def test_bearer_is_not_sent_to_another_host_on_redirect" src/shared/packages/pyforge-warden/tests/unit/test_actuator_github_client.py
  pixi run -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/unit/test_actuator_github_client.py -q
  ```

- **AC4 — A stale approved proposal can be dismissed, from the proposals page too, and is never approved again (defect 4).** `test_warden_fleet_proposal_recovery.py` holds `test_stale_approved_proposal_can_be_dismissed`, `test_stale_approved_proposal_is_still_refused_on_approve` and `test_fresh_approved_proposal_is_still_refused`; `test_warden_fleet_proposal_stale_portal.py` holds `test_proposals_page_lists_a_stale_approval_with_dismiss_only` and `test_a_stale_approval_is_dismissed_through_the_page`. Expected: exit 0 from each command.

  ```bash
  grep -q "def test_stale_approved_proposal_is_still_refused_on_approve" src/platform/tests/test_warden_fleet_proposal_recovery.py && grep -q "def test_stale_approved_proposal_can_be_dismissed" src/platform/tests/test_warden_fleet_proposal_recovery.py && grep -q "def test_fresh_approved_proposal_is_still_refused" src/platform/tests/test_warden_fleet_proposal_recovery.py
  grep -q "def test_proposals_page_lists_a_stale_approval_with_dismiss_only" src/platform/tests/test_warden_fleet_proposal_stale_portal.py && grep -q "def test_a_stale_approval_is_dismissed_through_the_page" src/platform/tests/test_warden_fleet_proposal_stale_portal.py
  pixi run -e pyforge-guild platform-ci-local -- --test
  ```

- **AC5 — A whole-run actuator failure keeps its cause, in `actuation` and on the proposal (defect 5).** `test_actuator.py` holds `test_whole_run_failure_records_its_cause`; `test_warden_fleet_proposal_recovery.py` holds `test_whole_run_actuator_failure_reaches_the_proposal`. Expected: exit 0 from each command.

  ```bash
  grep -q "def test_whole_run_failure_records_its_cause" src/shared/packages/pyforge-warden/tests/unit/test_actuator.py && grep -q "def test_whole_run_actuator_failure_reaches_the_proposal" src/platform/tests/test_warden_fleet_proposal_recovery.py
  pixi run -e pyforge-guild platform-ci-local -- --test
  pixi run -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/unit/test_actuator.py -q
  ```

- **AC6 — Both halves of the warden suite pass.** Expected: exit 0 from each command.

  ```bash
  pixi run -e pyforge-warden pyforge-warden-test
  pixi run -e pyforge-warden pyforge-warden-live-test
  ```

- **AC7 — A defect that is not reproduced is on record.** For each of AC1 to AC5 whose defect the tree did not show, the Spec Change Log carries a dated line that starts "not a defect (defect <n>)" after its date and names the command that was run; that defect's `grep` command is then not required. Expected: the command prints the number of defects left unfixed, exit 0; when every defect was reproduced and fixed it prints 0 and exits 1.

  ```bash
  grep -c "^- 20[0-9-]*: not a defect (defect [1-5])" _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-29-1-an-unscannable-upload-fails-and-the-web-face-and-the-actuator-leave-nothing-behind.md
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-warden CAP-12, CAP-16, CAP-17, CAP-24, CAP-29 (realized, no text change); no AD moves; no warden FR.
- Dream: `docs/dreams/pyforge-warden.md`, the 2026-11-25 entry (the web face and the actuator fail honestly and leave nothing behind); operator ruling of 2026-11-25.
- Epic: Epic 29, minted with this story.
- Ledger key: `29-1-an-unscannable-upload-fails-and-the-web-face-and-the-actuator-leave-nothing-behind`.
- Deferred-work row: `DW-warden-review-2026-11-24-1`, closed by this story's landing.
- Flag: none (a `fix` story, `spec-feature-flag-governance` Q1).
- Surface: `marshal-policy.toml` `[epic_surfaces]."29"`, plus `pyforge/warden/discovery.py`, `tests/unit/test_non_python_lockfiles.py` and the station's `contract.md` (three rows) under the lead's ruling of 2026-11-25, and `templates/warden_fabric/fleet_proposals.html` with `src/platform/tests/test_warden_fleet_proposal_stale_portal.py` after the second review. `django-warden` is on `spec-pyforge-unifying-strategy`'s surface, so a moved file there is reconciled on that Spec's memlog as well as warden's.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry and the operator's ruling of the same date, for `DW-warden-review-2026-11-24-1`.
- 2026-11-25: lead's rulings after the independent review, which override this spec's first text: (a) `open_fix_proposal` stores a whole-run failure's detail as the proposal's error; (b) the re-approve arm of defect 4 is dropped, a stale `APPROVED` proposal may only be dismissed; (c) the fix branch is deleted only when the pull-request POST itself raised; (d) `pyforge.warden.discovery` gains the public `discovered_manifest_names()` and `django-warden` calls it, so `discovery.py`, `test_non_python_lockfiles.py` and three `contract.md` rows join the surface; (e) the mis-described job test is renamed and a real-scan case added. Intent, Approach, Always, Never, AC1, AC3, AC4 and AC5 were reworded to match.
- 2026-11-25: defect 1: reproduced and fixed - `src/platform/tests/test_warden_portal_job_outcomes.py` on the unchanged tree: `test_upload_of_a_name_discovery_does_not_read_is_refused` (five names answered 202), `test_job_whose_scan_read_no_manifest_fails` (the job ended SUCCEEDED), `test_sbom_kind_is_the_engine_sbom_or_404` and `test_a_real_scan_stores_its_own_sbom` (`?kind=sbom` answered 200 with `{}`); after the review, `test_upload_of_a_native_lockfile_follows_the_flag` failed on the first fix (a native lockfile name answered 202 with the flag off).
- 2026-11-25: defect 2: reproduced and fixed - `test_blob_is_removed_after_a_succeeded_job` and `test_blob_is_removed_after_a_failed_job` in `src/platform/tests/test_warden_portal_job_outcomes.py` (the blob directory was still under `COMPLIANCE_FACE_BLOB_ROOT`).
- 2026-11-25: defect 3: reproduced and fixed - `pixi run -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/unit/test_actuator_github_client.py -q`: `test_failed_open_deletes_the_ref_it_created` (no DELETE after a 502 on the POST), `test_missing_base_sha_fails_before_any_commit` (a commit with `parents: []` was posted), `test_bearer_is_not_sent_to_another_host_on_redirect` (the redirect request carried the bearer); after the review, `test_an_accepted_open_with_no_url_keeps_its_branch` failed on the first fix (it deleted the branch of an accepted open).
- 2026-11-25: defect 4: reproduced and fixed - `test_stale_approved_proposal_can_be_dismissed` in `src/platform/tests/test_warden_fleet_proposal_recovery.py` (`dismiss_proposal` raised "cannot dismiss proposal in state approved"). The retry half of the row is not built: a second approve of a stale approval is always refused by the open task's own expiry rule, so `approve_proposal` keeps refusing it (`test_stale_approved_proposal_is_still_refused_on_approve`); the retry, if wanted, is a new decision for the operator.
- 2026-11-25: defect 5: reproduced and fixed - `test_whole_run_failure_records_its_cause` in `src/shared/packages/pyforge-warden/tests/unit/test_actuator.py` (a solver `OSError` escaped `run_actuator`; the two whole-run records carried no exception type) and `test_whole_run_actuator_failure_reaches_the_proposal` in `src/platform/tests/test_warden_fleet_proposal_recovery.py` (the proposal's error was "actuator produced no outcome for finding").
- 2026-11-25: the story is implemented and in review.
- 2026-11-25: second review, one low problem, fixed: the dismissal defect 4 permits had no operator path, because the proposals page listed `QUEUED` proposals only. `stale_approved_proposals()` in `proposals.py` and the three proposal views now give the page the stale approvals, and `fleet_proposals.html` shows each with a Dismiss form and no Approve form. `test_proposals_page_lists_a_stale_approval_with_dismiss_only`, `test_the_expiry_setting_decides_what_the_page_lists` and `test_a_stale_approval_is_dismissed_through_the_page` in `src/platform/tests/test_warden_fleet_proposal_stale_portal.py` failed on the tree before the change (the page read "No queued proposals."). The template and that test module join the surface.
- 2026-11-25: closed. PR #2385 merged as 080f89c4df (`Merge pyforge-steward/133-1 into main`) after its 51 CI checks passed and the full local `pr-preflight` exited 0 on 48 lanes; an independent reviewer read the diff against this spec before the merge, its findings were applied and re-reviewed.
