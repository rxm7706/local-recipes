---
title: "17.1: Eligibility records its policy, and warden's other open deferrals close"
type: 'fix'
created: '2026-10-03'
status: 'done'
followup_review_recommended: false
baseline_revision: '8efd0d51dbdde6cc799be03c459064a06c6793fa'
review_loop_iteration: 1
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Warden carries open deferred-work rows the operator ruled on 2026-10-03 to close now (deferral burn-down Phases 4 and 5, open medium and low rows together), in exactly one story per station (the same day's ruling on sizing). The rows were measured 2026-10-03 with a parser over `deferred-work-ledger.md` (`## DW-`/`### DW-` entries whose first `status:` reads `open`): 3 medium (one recorded `medium (unverified)`), 8 low and 40 unrated (outside these phases). The mediums: CAP-2 promises eligibility is reproducible from provenance alone, but an explicit `required_authority_sources` override leaves no trace in the returned data (DW-FU-7-2); several observations of one package identity are never reconciled into one result (DW-FU-7-1); and the TEA roster refusal landed on 2026-09-07 but its row was never closed (DW-FU-11-2). The lows: the CycloneDX adapter accepts any `specVersion` (DW-FU-7-1-2); and seven recommended follow-up reviews never ran (DW-FRR-7-1, DW-FRR-9-1, DW-FRR-9-2, DW-FRR-9-3, DW-FRR-10-2, DW-FU-6-3, DW-FU-5-1).

**Approach:** Fix each row where its behaviour lives: the eligibility union (`src/shared/packages/pyforge-warden/src/pyforge/warden/eligibility.py`) records its effective policy and reconciles duplicate identities; the CycloneDX adapter (`src/shared/packages/pyforge-warden/src/pyforge/warden/sources.py`) checks `specVersion`, with the review of Story 7.1; the TEA roster refusal is re-read and pinned, with the reviews of Stories 9.1, 9.2 and 9.3 (the hook book and its plugins); and the reviews of Stories 10.2, 6.3 and 5.1. Each row closes in the warden ledger with a `resolution:` naming this story and a `verified:` line citing the `path:line` that holds the fix.

Ledger key: `17-1-eligibility-records-its-policy-and-warden-s-other-open-deferrals-close`.
Type / Effort / Deps: fix / L / —.

### Living CAP citations

- The capabilities that shipped each behaviour (the stories each row below names); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a caller-supplied `required_authority_sources` override When `compute_eligibility_union` returns Then each result records the effective required set, and a status re-derived from the results alone equals the returned status; under the default `None` the recorded set is the consensus set the union derived
- Given one package identity observed twice (direct and transitive in one CycloneDX document, or by two adapters) When the union runs Then it returns one result for that identity whose provenance keeps both observations
- Given a CycloneDX document whose `specVersion` is outside the declared supported set When the adapter validates it Then it is refused with an error naming the version; a supported version validates as today
- Given DW-FU-11-2, whose fix already landed When this story re-reads the cited lines Then the row closes citing them, and a test pins the roster refusal where none does
- Given each recommended follow-up review (Stories 7.1, 9.1, 9.2, 9.3, 10.2, 6.3, 5.1) When it runs as an independent adversarial pass reading the story's shipped code against its spec Then every finding is fixed here with a test, and the row closes naming the review's result
- Given this story lands When its deferred-work rows are read Then each of `DW-FU-7-2`, `DW-FU-7-1`, `DW-FU-11-2`, `DW-FU-7-1-2`, `DW-FRR-7-1`, `DW-FRR-9-1`, `DW-FRR-9-2`, `DW-FRR-9-3`, `DW-FRR-10-2`, `DW-FU-6-3`, `DW-FU-5-1` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:** Fix each defect where the shipped behaviour lives and pin it with a test that fails without the fix. Keep `warden scan` the sole PR verdict and the frozen report schema additive-only. Reconcile every Spec `spec-surface` names for a governed path (a memlog entry naming the path, then a scoped stamp; AGENTS.md pre-PR item 5).

**Never:** Never add a second verdict or change the exit-code lattice. Never change what an adapter emits per observation (reconciliation belongs to the union). Never close a row without its landed fix and a cited `verified:` line. Never hand-edit `SPEC.md` or `sprint-status-ledger.yaml`.

</intent-contract>

## Deferred-work rows this story closes (operator rulings 2026-10-03, deferral burn-down Phases 4 and 5)

- `DW-FU-7-2` (medium) — `compute_eligibility_union` (`src/shared/packages/pyforge-warden/src/pyforge/warden/eligibility.py:103`) records the effective required authority set on each `EligibilityResult` (an additive field; under the default `None` it records the consensus set it derived), so a holder of the results alone can re-derive every status, as CAP-2's "reproducible from provenance alone" promises.
- `DW-FU-7-1` (medium) — The union reconciles several observations of one `PackageIdentity` (direct and transitive in one CycloneDX document, or across adapters) into one result whose provenance keeps every observation; the adapters (`src/shared/packages/pyforge-warden/src/pyforge/warden/sources.py`) still emit one evidence record per observation.
- `DW-FU-11-2` (medium) — Fixed 2026-09-07 and never closed: `run_tea_test_review` raises `TeaRosterMissingError` when the suite:AD-9 roster has no `tea` entry (`src/shared/packages/pyforge-warden/src/pyforge/warden/tea_advisory.py:213`), `_contribute` re-raises it (`:357`) and the CLI records a config-validation error (`cli.py:1362`). Confirm it, pin it with a test if none does, and close citing the lines.
- `DW-FU-7-1-2` (low) — `CycloneDXSourceAdapter.validate` (`src/shared/packages/pyforge-warden/src/pyforge/warden/sources.py:252`) checks `specVersion` against one declared set of supported versions (those the shipped schema tests cover) and refuses any other with a validation error naming it.
- `DW-FRR-7-1` (low) — The follow-up review of Story 7.1 (SourceContract adapters and the identity API); it sits on DW-FU-7-1's module.
- `DW-FRR-9-1` (low) — The follow-up review of Story 9.1 (warden publishes the PR-gate hook book).
- `DW-FRR-9-2` (low) — The follow-up review of Story 9.2 (current scanners become optional plugins); it sits beside DW-FU-11-2's plugin.
- `DW-FRR-9-3` (low) — The follow-up review of Story 9.3 (default warden stays green without Checkmarx).
- `DW-FRR-10-2` (low) — The follow-up review of Story 10.2 (the first portal slice: start/get one audit, in `django-warden`).
- `DW-FU-6-3` (low) — The follow-up review of Story 6.3 (currency-axis producer gate flags), recommended by bmad-loop when its damping cap was spent.
- `DW-FU-5-1` (low) — The follow-up review of Story 5.1 (actionable diagnostics, safe-by-default posture), recommended the same way.

A follow-up review row closes when that review has run as an independent adversarial pass (the reviewer reads the story's shipped code against its spec, never the implementer's summary) and every finding is fixed here with a test; if a drain-scheduled follow-up review (marshal Stories 73.1/73.2) closed the row first, this story cites that closure instead of repeating the review.

## Binding

Parent: the capabilities that shipped each behaviour (the stories each row names); a `fix`, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.
Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the 2026-10-03 (Phase 4+5) entry.
Ledger key: `17-1-eligibility-records-its-policy-and-warden-s-other-open-deferrals-close`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 from the operator's Phase 4+5 rulings (open medium and low deferrals together; one story per station).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Spec Change Log

- 2026-10-03 — sent back after an independent landing review (findings below). By operator ruling, the follow-up-review rows leave this story: an implementation session cannot close them (they run as review-agent batches). Status back to `ready-for-dev`.

## Review Triage Log

### 2026-10-03 — Landing review (operator session) — sent back
Hold: the fixes for DW-FU-7-2 (in memory), DW-FU-7-1-2 and DW-FU-11-2; the CLI stays the sole gate and `--doctor` never exits 1. The operator session reparented `CycloneDXUnsupportedSpecVersionError` under `PyforgeError` (pyforge-core CAP-5); keep that commit.
- `high` **Seven follow-up-review rows were closed with no review run**: DW-FRR-7-1, DW-FRR-9-1, DW-FRR-9-2, DW-FRR-9-3, DW-FRR-10-2, DW-FU-6-3, DW-FU-5-1. Reopen all seven (`status: open`; drop the new `resolution:` and `verified:` lines), remove them from this story, and remove the false review claim from `tests/unit/test_story_17_1_followup_reviews.py`'s docstring (drop the file if its tests only restate shipped behaviour).
- `medium` **DW-FU-7-1 was closed on a change that does nothing**: both adapters build identity through `resolve_identity`, so `PackageIdentity` equality already equals the new group key, and the result's purl now depends on input order. Revert the merge-key change, and close the row citing Story 7.2's existing grouping (the real `path:line`).
- `medium` **Correct the `verified:` citations**: DW-FU-7-2 is the new field and the re-derivation (`eligibility.py:102`, `:111-130`), DW-FU-7-1-2 the check (`sources.py:273-275`); the follow-up-review rows' citations go away with the reopen.
- `low` DW-FU-7-2 is fixed in memory but not in the saved output: `eligibility_sbom.py` `_build_component` still writes only status and provenance. Add the effective required set as an additive CycloneDX property, or record in `spec-package-inventory-eligibility/.memlog.md` that this half stays open.
- `low` `sources.py`: drop the no-op `try/except CycloneDXUnsupportedSpecVersionError: raise` in `ingest`; correct the `validate` docstring (it now raises on specVersion). Drop the redundant `test_dw_fu_11_2_roster_missing_still_refuses` or make it use `pytest.raises`.


- No review has run yet.

### 2026-10-03 — Review pass (landing-review remediation)
- verdicts: 12 findings — high 0, medium 0, low 1, false 8, maybe-false 3
- findings:
  - `[low]` `[patch]` Eligibility CycloneDX output did not assert `cfe:required_authority_sources` values — extended `test_eligibility_sbom.py` with JSON property checks on render round-trip.
  - `[false]` `[reject]` Re-merge by ecosystem/name/version — landing review required Story 7.2 `PackageIdentity` dict grouping; adapters use `resolve_identity`.
  - `[false]` `[reject]` TEA roster unpinned — `test_tea_advisory.py` already covers `TeaRosterMissingError`; removed redundant 17.1-only duplicate.
  - `[false]` `[reject]` Comma in authority source names — adapter `source_name` values are fixed identifiers without commas.
  - `[false]` `[reject]` Empty frozenset encoding — empty required set is explicit policy; property value `""` matches sorted join contract.
  - `[false]` `[reject]` Spec intent-contract still lists eleven closures — operator send-back (Spec Change Log) scopes this pass to four code deferrals plus ledger reopen of seven follow-up-review rows; intent-contract block is read-only.
  - `[maybe-false]` `[defer]` Sprint ledger `done` vs seven reopened rows — story completes the in-scope deferrals; FRR rows stay open by design until review-agent batches run.
  - `[maybe-false]` `[defer]` DW-FU-7-1 citation line only — provenance merge is the `177–191` loop; ledger cites grouping entrypoint at `eligibility.py:168`.
  - `[maybe-false]` `[defer]` Missing `specVersion` docstring branch — existing unit tests cover absent/unsupported versions; docstring names the raise type.

## Auto Run Result

Status: done

Summary: Closed four in-scope deferred-work rows (DW-FU-7-2, DW-FU-7-1, DW-FU-7-1-2, DW-FU-11-2) per the 2026-10-03 landing review: eligibility records effective required authority on each result and in CycloneDX output, union groups by Story 7.2 `PackageIdentity`, CycloneDX `specVersion` is refused with a named error, and TEA roster refusal stays pinned in existing tests. Reopened seven follow-up-review ledger rows (DW-FRR-7-1, DW-FRR-9-1/9-2/9-3, DW-FRR-10-2, DW-FU-6-3, DW-FU-5-1) for independent review batches; removed the false `test_story_17_1_followup_reviews.py` module.

Files changed:
- `src/shared/packages/pyforge-warden/src/pyforge/warden/eligibility.py` — `effective_required_authority_sources`, re-derivation helpers, PackageIdentity grouping
- `src/shared/packages/pyforge-warden/src/pyforge/warden/eligibility_sbom.py` — `cfe:required_authority_sources` property
- `src/shared/packages/pyforge-warden/src/pyforge/warden/sources.py` — specVersion validate docstring; ingest cleanup
- `src/shared/packages/pyforge-warden/tests/unit/test_eligibility.py` — policy re-derivation tests
- `src/shared/packages/pyforge-warden/tests/unit/test_eligibility_sbom.py` — JSON property assertions on rendered SBOM
- `src/shared/packages/pyforge-warden/tests/unit/test_sources.py` — specVersion refusal (prior commit)
- `_bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md` — four closures, seven FRR reopenings, corrected `verified:` lines
- Memlogs: `spec-pyforge-warden`, `spec-pyforge-core`, `spec-package-inventory-eligibility`

Review: 1 low patch (SBOM test); follow-up review recommended false.

Verification: `pixi run --frozen -e pyforge-warden pyforge-warden-test` — pass; `pixi run --frozen -e pyforge-guild lint-types` — exit 0; `python scripts/spec_surface_reconcile.py` — OK.

Residual risk: Seven follow-up-review deferrals remain open until marshal review-agent batches run; intent-contract AC text still lists eleven row closures — operator ruling in Spec Change Log governs scope.
