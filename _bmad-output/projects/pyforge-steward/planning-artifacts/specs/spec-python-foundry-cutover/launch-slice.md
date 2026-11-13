---
companion-of: spec-python-foundry-cutover
created: "2026-11-11"
updated: "2026-11-11"
---

# Launch slice — the one story B lands on itself

Written by steward Story 120.1 from the operator's rulings of 2026-11-10 (ruling 3 and the second
addendum's ruling 1; `docs/dreams/pyforge-unifying-strategy.md` § Realization log). The contract
is `fnd:CAP-2`; the decision is the steward spine's `fnd:AD-26`.

**The proof.** Launch is proven by one merge on B's `main` with subject
`Merge <station>/<key> into main`, made by B's own `marshal factory dispatch`, with B's own
`detectors-ci` exit 0 at that SHA, and every capability-ledger row marked `launch: true` reading
`verified-in-foundry` with a case-list id. Once it is proven, the operator flips
`pyforge.cutover_root` by hand, with no loop running; nothing flips it automatically (`fnd:CAP-8`,
`fnd:AD-17`). Host boot is not a Launch criterion.

## The steps

Derived from a real dispatch journal on A, not from memory: steward Story 117.5, dispatch run
`pyforge-steward-20261031T184522008Z-c9355f3f`, landed as PR #2354 with subject
`Merge pyforge-steward/117-5 into main`, and its land-finalize run
`pyforge-steward-20261031T191251874Z-399c13ae` (both under
`_bmad-output/projects/pyforge-steward/implementation-artifacts/`, Tier 3, so cited by run id).
Their journal kinds, in order: `dispatch-launch`, `dispatch-supervisor-attach`, `dispatch-push`,
`dispatch-ruff-format`, `dispatch-spec-frontmatter`, `dispatch-verification` (refused, then one
`dispatch-verify-fix` turn, then verified), `dispatch-finalize`, `dispatch-land`,
`dispatch-completion`, `dispatch-timing`, then `land-sprint-ledger-promotion` and
`dispatch-land-finalize-resync`. The mint precedes the journal; the hand ledger sync follows it.

Node ids are repo-relative pytest paths on A. `oracle gap` means A has no test of that step; the
gap is carried by `DW-steward-121-4`, never filled by inventing a row.

| step | A verb or detector | capability | A test nodeid or `oracle gap` |
|---|---|---|---|
| mint the story | the Story's `### Story` block in `epics.md`, its Tier-3 feed key then `pixi run -e pyforge-guild sprint-ledger-sync -- --project <station>`, and its tracked story spec (CHAIN-STANDARD § 3 step 5); `chain-completeness-check` holds story ids and ledger keys equal | `spec-one-chain-per-station:CAP-9` | `src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_chain_completeness.py::test_epics_story_without_ledger_key_reports_fail` |
| dispatch | `pixi run -e pyforge-guild marshal factory dispatch <station> <key>` — journal `dispatch-launch`: a fresh worktree, the story spec `backlog` to `ready-for-dev`, the session launched detached | `spec-pyforge-marshal:CAP-159` | `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py::test_run_dispatch_journals_and_returns` |
| build and review | the dispatch supervisor watches the detached session — journal `dispatch-supervisor-attach` | `spec-pyforge-marshal:CAP-164` | `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_survival.py::test_reconcile_unsupervised_verdict_from_git_merge` |
| build and review | the branch reaches `origin` before verify — journal `dispatch-push` | `spec-pyforge-marshal:CAP-138` | `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_push.py::test_run_and_journal_dispatch_push_pushes_before_verify` |
| build and review | after the session exits `done`, at most one follow-up review (`followup_review_recommended`) | `spec-pyforge-marshal:CAP-169` | `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_harness_done.py::test_followup_true_allows_one_more_session` |
| build and review | the implementation and review the `bmad-build-auto` session performs (BMAD's skill as installed, not A code) | `spec-pyforge-marshal:CAP-159` | oracle gap |
| preflight and detectors | journal `dispatch-verification`: the story spec's verify commands in full mode (gate `MRS-GATE-001`); a refusal gets one `dispatch-verify-fix` turn and is verified again | `spec-pyforge-marshal:CAP-160` | `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification.py::test_judge_refused_when_gate_fails` |
| preflight and detectors | `pixi run -e pyforge-guild detectors-ci` (`scripts/detectors.py --scope repo`), B's own, exit 0 at the merge SHA | `spec-pyforge-doctor:CAP-93` | `src/shared/packages/pyforge-doctor/tests/unit/test_sources_dispatch.py::test_dispatch_covers_exactly_the_registered_sources` |
| PR | journal `dispatch-finalize`: the supervisor commits and pushes the finished branch (trigger `harness-done`) | `spec-pyforge-marshal:CAP-141` | `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_supervisor_finalize.py::test_session_detects_harness_done` |
| PR | the landing opens the PR on the root's own repository and waits on its required checks (`landing_checks`) | `spec-pyforge-marshal:CAP-209` | `src/shared/packages/pyforge-marshal/tests/unit/test_land.py::test_happy_path_opens_pr_polls_checks_and_merges` |
| merge | journal `dispatch-land`: a merge commit with the templated subject `Merge <station>/<key> into main`, verification verdict `verified` | `spec-pyforge-marshal:CAP-143` | `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_landing.py::test_merge_subject_is_marshal_native_with_policy_template` |
| finalize | `python -m pyforge.marshal.dispatch_land_finalize`, spawned by the landing — journal `dispatch-land-finalize-resync`: tracked story spec and feed row promoted, landing corroborated | `spec-pyforge-marshal:CAP-162` | `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_finalize.py::test_finalize_resyncs_the_primary_after_ledger_promotion` |
| ledger sync | journal `land-sprint-ledger-promotion`: the tracked ledger promoted on the remote tip (`marshal: promote sprint-status ledger for '<slug>'`), never the operator checkout | `spec-pyforge-marshal:CAP-233` | `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_finalize.py::test_finalize_passes_base_main_to_isolated_promote` |
| ledger sync | `pixi run -e pyforge-guild sprint-ledger-sync -- --project <station>`, by hand after the merge | `spec-pyforge-marshal:CAP-265` | `src/shared/packages/pyforge-marshal/tests/unit/test_promote_sprint_status_regressions.py::test_main_bare_sync_doctor_24_2_fixture` |
| ledger sync | `pixi run -e pyforge-guild story-status-check`: no story reads `done` without having landed | `spec-pyforge-doctor:CAP-93` | `src/shared/packages/pyforge-doctor/tests/unit/test_sources_marshal_story_status.py::test_false_green_story_reports_fail` |

Notes on the table:

- **Before the flip.** A writes every Dream, Frame, Spec and the capability ledger (`fnd:AD-24`), so
  the Launch story's Dream entry and capability are written on A. B mints the Story, its ledger key
  and its story spec on itself, against that Spec at the SHA it pins.
- **No `pr-preflight` row.** A `dispatch/*` branch skips the pre-push `pr-preflight`, journaled; the
  supervisor's verification gate stands in for it. `spec-pyforge-steward:CAP-159` is therefore not
  a Launch row.
- **The rows marked `launch: true`** are exactly the capabilities of the third column:
  `spec-one-chain-per-station:CAP-9`, `spec-pyforge-doctor:CAP-93`, `spec-pyforge-marshal:CAP-138`,
  `spec-pyforge-marshal:CAP-141`, `spec-pyforge-marshal:CAP-143`, `spec-pyforge-marshal:CAP-159`,
  `spec-pyforge-marshal:CAP-160`, `spec-pyforge-marshal:CAP-162`, `spec-pyforge-marshal:CAP-164`,
  `spec-pyforge-marshal:CAP-169`, `spec-pyforge-marshal:CAP-209`, `spec-pyforge-marshal:CAP-233` and
  `spec-pyforge-marshal:CAP-265`. Story 121.7 marks them; `depends_on` stays empty in this change
  (`spec-foundry-capability-ledger:CAP-1`).
- **The case list.** Every step with an A test has a row in
  `spec-foundry-regenerate-not-fold` `case-list.md` (Story 120.5); a row reaches
  `verified-in-foundry` only through the oracle gate (`fnd:AD-21`).

## The detectors Launch runs

`detectors-ci` runs every Doctor source in `scripts/detectors.py` `_DOCTOR_SOURCE_TASKS` (29 at
this change) plus the repo-scope scripts the registry discovers (`scripts/detectors.py --list`);
the scripts are not Doctor sources. Doctor Story 56.5 adds `writer-lock`
(`spec-pyforge-doctor:CAP-100`). Each source's import closure is in `spec-pyforge-doctor`
`contract.md` (Doctor's public contract, doctor Story 57.2); this file does not restate it.

**The Launch subset** is the sources that judge an artifact a Launch step writes on B. B's
`detectors-ci` exit 0 is the gate; these are the sources that make it say something about the slice.

| Doctor source | pixi task | Launch subset | the step it judges |
|---|---|---|---|
| `chain-completeness` | `chain-completeness-check` | yes | mint the story |
| `dream-chain` | `dream-chain-check` | yes | mint the story |
| `forward-dependency` | `forward-dependency-check` | yes | mint the story |
| `frontmatter-duplicate-keys` | `frontmatter-duplicate-keys-check` | yes | mint the story; build and review |
| `spec-surface` | `spec-surface-check` | yes | build and review |
| `deferred-work` | `deferred-work-check` | yes | finalize |
| `story-status` | `story-status-check` | yes | ledger sync |
| `ledger-regression` | `ledger-regression-check` | yes | ledger sync |
| `ledger-direction` | `ledger-direction-check` | yes | ledger sync |
| `writer-lock` | added by doctor Story 56.5 | yes | every step that writes a chain path |
| `capability-effect` | `capability-effect-check` | no | — |
| `status-body-consistency` | `status-body-consistency-check` | no | — |
| `dashboard-drift` | `retired-console-check` | no | — |
| `check-layout` | `dashboard-layout-check` | no | — |
| `bmad-drift` | `bmad-drift-check` | no | — |
| `platform-policy-suite` | `platform-policy-suite-check` | no | — |
| `bmad-render-config-ambiguity` | `bmad-render-config-ambiguity-check` | no | — |
| `frozen-path-changed` | `frozen-path-changed-check` | no | — |
| `pixi-currency-ledger` | `pixi-currency-staleness-check` | no | — |
| `general-docs-consistency` | `general-docs-consistency-check` | no | — |
| `capability-ledger` | `capability-ledger-check` | no | — |
| `chain-sprawl` | `chain-sprawl-check` | no | — |
| `fr-without-cap` | `fr-without-cap-check` | no | — |
| `fold-complete` | `fold-complete-check` | no | — |
| `docs-map-hygiene` | `docs-map-hygiene-check` | no | — |
| `docs-shelf-occupancy` | `docs-shelf-occupancy-check` | no | — |
| `live-proof-surface` | `live-proof-surface-check` | no | — |
| `docs-currency` | `docs-currency-check` | no | — |
| `bmad-output-hygiene` | `bmad-output-hygiene-check` | no | — |
| `dreams-hygiene` | `dreams-hygiene-check` | no | — |
