---
title: 'The repo at a fixed short path — document and guard the /pyforge checkout path in the Containerfile'
type: 'feature'
created: '2026-08-09'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/implementation-artifacts/epic-7-context.md']
warnings: []
baseline_revision: 'bb3924a1007d45b33d438ce86e7ce2fd6331deaf'
final_revision: '758cc5318c948eaec8689a681c313f474cb723d2'
---

<intent-contract>

## Intent

**Problem:** Story 7.1's Containerfile already hardcodes `WORKDIR /pyforge` in both stages — a fixed, short, host-independent checkout path that trivially avoids the documented `pixi-build-python` path-length panic (repo root >~173 bytes triggers an unchecked `usize` underflow in `pixi-build-backends`) — but that rationale exists only in review-trail prose (spec-7-1's Design Notes) and a research doc, never in the Containerfile itself, and nothing catches a future regression if the path is lengthened or made host-derived.

**Approach:** Add a citation-backed rationale comment to the Containerfile at the `WORKDIR` decision, documenting why `/pyforge` is fixed (not derived from the build host or a build ARG) and short enough to carry wide margin under the panic threshold; add a small stdlib-only regression test that parses the Containerfile and fails if either stage's `WORKDIR` stops being that literal short path.

## Boundaries & Constraints

**Always:**
- Keep the checkout path exactly `/pyforge` in both Containerfile stages — the value 7.1 already shipped; no artifact names a different candidate.
- Document the rationale as a Containerfile comment (this story's declared Surface per `epics.md`), citing the panic mechanism and the in-repo research doc (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/technical-steward-pixi-workspace-member-research-2026-07-25.md` § A3.1) rather than asserting the number bare.
- The regression test must be pure stdlib (no Docker build, no third-party imports), matching this repo's existing `tests/packaging` gates so it runs in the lean `pyforge-ci` env.

**Block If:** none.

**Never:**
- Do not change the path away from `/pyforge`, add a build ARG/ENV override for it, or otherwise make it host- or build-time-derived — the AC requires "fixed... rather than derived from the build host."
- Do not implement Story 7.5's build-time smoke gate (`scripts/container-gates`) or run an actual `docker build` inside the test — this story's check is static text analysis only.
- Do not touch `.dockerignore`, `pixi.toml`, or any station's own code — out of this story's declared surface.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Containerfile as shipped | Both stages' `WORKDIR` is literal `/pyforge` | Regression test passes | N/A |
| Regressed to a long/derived path | `WORKDIR` changed to something host-derived or long | Regression test fails, naming the offending line and byte length | Failure message states the ceiling and the actual length |
| Stages disagree | Builder and runtime stages have different `WORKDIR` values | Regression test fails | Message names both values |

</intent-contract>

## Code Map

- `Containerfile` -- add a rationale comment at the `WORKDIR /pyforge` lines documenting the path-length-panic avoidance
- `tests/packaging/test_containerfile_checkout_path.py` (new) -- stdlib-only regression test parsing the Containerfile

## Tasks & Acceptance

**Execution:**
- [x] `Containerfile` -- add a comment block at the builder stage's `WORKDIR /pyforge` explaining the fixed-short-path rationale (panic mechanism, ~173-byte ceiling, `/pyforge`'s 8-byte margin, citation to the steward research doc); add a short cross-reference comment at the runtime stage's `WORKDIR /pyforge` pointing back to it -- makes the decision auditable in the artifact itself, not only in review-trail prose
- [x] `tests/packaging/test_containerfile_checkout_path.py` -- parse `Containerfile` text (regex/stdlib only); assert both `WORKDIR` lines equal the literal `/pyforge`; assert neither contains `$` or `{{` (host- or arg-derived); assert the byte length stays well under the documented ceiling -- turns the "fixed and documented" AC into something that fails loudly on regression, reusing the existing `pyforge-deps-test` pixi task (directory-wide `pytest tests/packaging -q`) with zero manifest changes

**Acceptance Criteria:**
- Given the Containerfile, when read, then a rationale comment documents why the checkout path is fixed and short, citing the path-length panic and its byte ceiling.
- Given the built image, when a shell runs inside either stage, then the checkout root is `/pyforge`.
- Given `pixi run -e pyforge-ci pyforge-deps-test`, when the suite runs, then the new regression test passes, and it fails if `WORKDIR` is ever changed to a non-literal or materially longer path.

## Spec Change Log

## Review Triage Log

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 3, low 1)
- defer: 1: (high 0, medium 1, low 0)
- reject: 8: (high 0, medium 0, low 8)
- addressed_findings:
  - `[medium]` `[patch]` `MAX_SAFE_WORKDIR_BYTES`'s justifying comment cited `/pyforge-workspace-checkout` as an example that "already trips" the 32-byte margin; independently measured at 27 bytes (`27 > 32` is false), so the example does not actually trip the check it's meant to illustrate. Replaced with `/home/containeruser/pyforge-checkout` (36 bytes, verified > 32).
  - `[medium]` `[patch]` None of the four original tests exercised a failing input — the guard logic's own failure branches were unverified by the diff, and the byte-math bug above is a direct, demonstrated consequence of that gap. Added `test_guard_logic_actually_fires_on_synthetic_regressions`, a parametrized test driving the same regex/threshold logic against synthetic (never-written-to-disk) WORKDIR lines covering the too-long-only, `$`-derived, and `{{ }}`-derived branches independently.
  - `[medium]` `[patch]` `_workdir_lines()` had no existence guard outside `test_discovery_is_not_vacuous`; running any of the other three tests in isolation (`pytest -k`, xdist sharding) would raise an unguarded `FileNotFoundError` instead of a clear assertion message. Moved the `.is_file()` guard into `_workdir_lines()` itself.
  - `[low]` `[patch]` The runtime-stage Containerfile comment claimed "not repeated here to avoid two sources of truth" while restating the substance (panic mechanism, ~173-byte ceiling, § A3.1 pointer) in condensed form anyway — a real second source of truth that could drift from the builder-stage comment. Trimmed to a genuine one-line pointer with no restated substance.
  - `[medium]` `[defer]` `epics.md` still lists Story 7.1 (already `done` per `sprint-status.yaml`) and Story 7.2 as `**Status:** backlog`, and the tracked `sprint-status-ledger.yaml` still has `7-2-the-repo-at-a-fixed-short-path: backlog` — both stale relative to the live implementation state. Pre-existing orchestration gap, not caused by this story: neither the dev-auto workflow's own steps nor Story 7.1 touched these files, and `sprint-status-ledger.yaml`'s own header says it is regenerated by a separate `sprint-ledger-sync` command, not hand-edited per-story. Logged to deferred-work.md.
  - `[low]` `[reject]` "The regression test only checks Containerfile text, never proves the AC's build-time claim (no Docker build)." Already an explicit, justified design decision in this spec's own Design Notes ("Why no Docker build in the regression test") — Story 7.5 owns the build-time smoke gate; requiring an actual build here would duplicate that scope.
  - `[low]` `[reject]` "`ruff format --check` flags this new file." Verified real, but not evidence of a live gate: the sibling file `tests/packaging/test_dependency_completeness.py` (already merged, presumably passing CI) fails the identical check today. `pre-commit-config.yaml` is documented in `scripts/spec_surface_allowlist.txt` as "inherited staged-recipes hooks config (upstream-owned)" with no CI workflow found that invokes it against this file's directory — the claim that this diff "would bounce off CI" is unsupported by the actual baseline.
  - `[low]` `[reject]` "`MAX_SAFE_WORKDIR_BYTES` has no mechanical coupling to the cited ~173-byte figure." True, but there is no canonical shared constant for that figure anywhere in this monorepo to couple to — every other citation of it (research docs, deferred-work-ledger entries) is prose, not code. Out of proportion for an S-effort documentation/hardening story.
  - `[low]` `[reject]` "The WORKDIR regex doesn't handle lowercase/indented directives." True in isolation, but the claimed silent-pass failure mode doesn't actually manifest: any line the regex fails to match drops the total below the `test_discovery_is_not_vacuous` floor of 2, which fails loudly. The reviewer's own note acknowledges this for a total miss; a partial miss (one stage) triggers the same guard.
  - `[low]` `[reject]` "`test_no_workdir_is_host_or_build_derived`'s failure message overclaims relative to its substring check." The message describes the contract being enforced (no host/build-time derivation), which the `$`/`{{` substring test is a reasonable, accurate proxy for; not misleading in a consequential way.
  - `[low]` `[reject]` "No mechanism verifies the cited research-doc path keeps resolving." A universal citation-rot concern applicable to every cross-reference in this codebase, not specific to this diff; disproportionate to address here.
  - `[low]` `[reject]` "Docstring's `pytest` mention implied an import that didn't exist." Resolved as a side effect of the negative-path-test patch above: the file now genuinely imports and uses `pytest` (`@pytest.mark.parametrize`), so the docstring's claim is now literally true rather than needing a wording fix.

### 2026-08-09 — Repair pass (deterministic-verification failure)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 2: (high 0, medium 1, low 1)
- reject: 10: (high 0, medium 0, low 10)
- addressed_findings:
  - none

`python scripts/spec_surface_check.py` failed after this story landed (`038f47ad15`): `Containerfile` is also declared in `pyforge-steward/spec-unified-container`'s `surface:` (a different, pre-existing spec that formalized 7.1's container work), and that spec's `.memlog.md` had not been updated to name the Containerfile content change this story made — the detector's drift check, not this story's own intent contract. Repaired outside `<intent-contract>` and outside this story's own Code Map: appended a `RECONCILED BY NAME` entry to `spec-unified-container`'s `.memlog.md` naming the `Containerfile` change (rationale comment, comment-only, no stage/dependency change) and the new test file, then re-stamped `scripts/.spec-surface-baseline.json` scoped to that spec only (`--write-baseline --spec pyforge-steward/spec-unified-container`). Verified: `python scripts/spec_surface_check.py` exits 0 (previously exited 1 with one `[drift]` finding); full `python scripts/detectors.py --scope repo` run confirms `spec_surface_check` now passes and that the two still-failing detectors (`deferred_work_check`, `ledger_regression_check`) are pre-existing, unrelated to this story (reproduced identically at commit `038f47ad15` before this repair, with only this story's own `.memlog.md`/baseline edits stashed out). `pixi run -e pyforge-ci pyforge-deps-test` re-run green (67 passed). Reviewed the repair diff itself (memlog + baseline only, not re-reviewing the already-triaged Containerfile/test diff) with Blind Hunter + Edge Case Hunter in parallel: Blind Hunter's 10 findings all rejected (each either unaware of already-verified facts given in the prompt — e.g. "no evidence the Containerfile change is comment-only" when `git show` confirms it — or a misreading of this memlog's own established multi-topic-per-bullet convention, or a slug-style claim contradicted by the file's pre-existing `Story 7-1-one-build-whole-guild` entries). Edge Case Hunter's 2 findings are real, pre-existing gaps in `spec_surface_check.py`'s own design (substring-scoped "named" check has no entry-boundary, and `--write-baseline` merges are unlocked) — neither caused by this story's two-line repair; both logged to `deferred-work.md`, owned by `pyforge-marshal/spec-surface-drift-reconciliation`.

## Design Notes

**Why no Docker build in the regression test.** Story 7.5 owns the build-time smoke gate; this story's property (a fixed, short, literal path) is fully verifiable by reading the Containerfile text, so requiring an actual `docker build` would duplicate 7.5's scope and slow this gate down for no added coverage.

**Why `/pyforge` and not a different or configurable path.** 7.1's Design Notes already settled this: "no artifact names any candidate path besides `/pyforge`." Making it configurable (an ARG) would reopen exactly the host-derivation risk the AC forbids.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Status:** done

**Summary.** Story 7.2's implementation (rationale comment on both `Containerfile` `WORKDIR /pyforge` lines + `tests/packaging/test_containerfile_checkout_path.py`) was already complete and committed (`038f47ad15`) from the prior session. That session's deterministic verification gate, `python scripts/spec_surface_check.py`, failed afterward — not because of a defect in this story's own diff, but because `Containerfile` is also declared in a *different* spec's governed surface (`pyforge-steward/spec-unified-container`), and that spec's `.memlog.md` hadn't been updated to name the change. This session repaired that gap without touching spec-7-2's `<intent-contract>` or any file in its own Code Map, then re-ran the full review/finalize sequence.

**Files changed this session** (outside spec-7-2's own surface, by design):
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-unified-container/.memlog.md` -- new `RECONCILED BY NAME` entry naming the Containerfile rationale-comment change
- `scripts/.spec-surface-baseline.json` -- re-stamped, scoped to `pyforge-steward/spec-unified-container` only

**Review findings breakdown (repair-pass diff only, since the story's own diff was already reviewed 2026-08-09):** intent_gap 0, bad_spec 0, patch 0, defer 2 (both pre-existing `spec_surface_check.py` design gaps, logged to `deferred-work.md`, owned by `pyforge-marshal/spec-surface-drift-reconciliation`), reject 10 (all Blind Hunter findings — evidentiary nitpicks against context already verified, or contradicted by the memlog's own established convention).

**Follow-up review recommendation:** `false` -- zero patches applied to any governed file; the repair is a two-line memlog reconciliation plus a mechanical baseline re-stamp.

**Verification performed:**
- `python scripts/spec_surface_check.py` -- rc=0 (previously rc=1, one `[drift]` finding)
- `pixi run -e pyforge-ci pyforge-deps-test` -- 67 passed
- `python scripts/detectors.py --scope repo` -- confirms `spec_surface_check` now passes; the two other still-failing detectors (`deferred_work_check`, `ledger_regression_check`) reproduce identically at the pre-repair commit, confirming they are pre-existing and unrelated to this story
- `git status` -- clean at final_revision

**Residual risks:** none introduced by this repair. Two pre-existing detector-design gaps and one pre-existing ledger-sync gap are logged to `deferred-work.md`, all explicitly out of this story's scope.

