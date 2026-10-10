---
title: "87.5: Dispatch and drain preserve a stopped story's work as a tag on origin"
type: 'feature'
created: '2026-10-04'
status: 'done'
baseline_revision: '0b5a037749155ee12fcda4f4567a8faef6737115'
review_loop_iteration: 0
followup_review_recommended: false
flag:
  key: pyforge.marshal.preserve_refs
  provider: openfeature-file
  default: {production: off, staging: off, dev: off}
  scope: global
  fallback: "dispatch keeps today's behaviour: only a FAILED run with progress writes failed/<story>/changes.patch and a dispatch-preserve journal pair; stopped and blocked runs preserve nothing"
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04-review.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_preserve.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py
  - src/shared/packages/pyforge-core/src/pyforge/core/preserve_refs.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Dispatch preserves only on a `FAILED` verdict with git progress (`dispatch_supervisor/__main__.py:2735-2746`). It writes a gitignored `failed/<story>/changes.patch` that leaves out untracked files (`adapters/vcs_git.py:815-848`). A run that ends `stopped_externally` or `blocked` preserves nothing beyond what its branch already holds. The drain records no preserve fact for a story it holds, blocks or stops. On 2026-10-04 there were 120 such patches on one disk.

**Approach:**
- **When.** A dispatch run that ends `failed`, `stopped_externally` or `blocked` with progress above its baseline gets a preserve. Progress means commits, uncommitted changes or untracked non-ignored files.
- **What.** The supervisor snapshots the worktree and writes `preserve/<slug>/<N.M>/dispatch-<sha8>` through `pyforge.core.preserve_refs`, locally first.
- **Push.** The supervisor then pushes the tag through Story 87.15's content gate, never the session itself (AD-9). A governed bmad-build-auto session under dispatch never pushes a preserve.
- **Journal and status.** The `dispatch-preserve` outcome payload names `preserve_tag`, and the patch is still written. `marshal status` shows `dispatch_preserve_tag` on the row.
- **Drain.** Each `dispatch-fleet-cycle` entry that holds, blocks or stops a story names that story's tag, or carries a finding naming the story when none exists.
- **Every harness.** No harness profile branches the path.

Ledger key: `87-5-dispatch-and-drain-preserve-a-stopped-storys-work-as-a-tag-on-origin`.
Type / Effort / Deps: feature / M / S-87.3, S-87.15.

### Living CAP citations

- `spec-pyforge-marshal` CAP-287 (FR-234, AD-81), extending FR-193 / AD-75 (dispatch is a governed verb). Flag `pyforge.marshal.preserve_refs`.

## Acceptance Criteria

- Given a dispatch run whose terminal verdict is `failed`, `stopped_externally` or `blocked`, and whose worktree has commits, uncommitted changes or an untracked file above baseline When the supervisor concludes Then a `preserve/<slug>/<N.M>/dispatch-<sha8>` tag exists, its tree includes the untracked file, and the supervisor pushes it through the content gate; the `dispatch-preserve` payload carries `preserve_tag`; the patch is still written.
- Given each profile in `harness_preference` (`claude`, `cursor`, `copilot`, `gemini`, `devin`) run through the harness fake When the same run ends Then the same tag results; no profile branches the preserve path.
- Given the same terminal verdict reached again (a re-run, a supervisor restart) When the supervisor concludes Then no second tag is written.
- Given a push the gate refuses, or no network When the supervisor concludes Then the local tag is named in the payload and status reports debt; the run's verdict is not changed by it.
- Given a campaign (`--stories`, `--campaign`, `--max-in-flight`) whose cycle holds, blocks or stops a story When the `dispatch-fleet-cycle` entry is written Then it names that story's preserve tag, or carries a finding naming the story when none exists.
- Given `marshal status` for that station Then the row shows `dispatch_preserve_tag`.
- Given the flag off When the same runs end Then today's behaviour holds; one test file runs both states; removing the stopped or blocked trigger or the no-second-tag rule fails a test (mutation).

## Boundaries & Constraints

**Always:** The supervisor writes and pushes; the session never does. One refspec per tag through the gate. Journal the preserve before reporting it (AD-6).

**Never:** Never remove a dispatch worktree here. Never retire a patch. Never call GitHub in tests.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` CAP-287 (FR-234, AD-81); FR-193 / AD-75.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (preserved-work refs) entry.
Research: drafts' Story 87.5; review B1 (the gate scans untracked content), M7 (no second tag), the mode table (the supervisor pushes).
Ledger key: `87-5-dispatch-and-drain-preserve-a-stopped-storys-work-as-a-tag-on-origin`.
Ledger status at mint: `backlog`.
Deps: S-87.3, S-87.15.
Minted 2026-10-04 under the operator's ruling of the same day.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- The two-state flag test: `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_preserve_tag.py` — runs `pyforge.marshal.preserve_refs` on and off.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.

## Spec Change Log

- 2026-10-09: Story 87.5 implemented (CAP-287 FR-234) — dispatch supervisor preserve tags behind `pyforge.marshal.preserve_refs`; drain fleet-cycle enrichment (MRS-DRAIN-020); `test_dispatch_preserve_tag.py`.

## Review Triage Log

- 2026-10-09 bmad-build-auto: ACs covered by unit tests; harness-profile AC is structural (single supervisor path, no profile branch). Follow-up: none.

## Auto Run Result

Status: done

Verification: `pyforge-marshal-test` 12112 passed; `pyforge-deps-test` 130 passed; `lint-types` exit 0; `spec_surface_reconcile.py` OK; memlog surface reconcile on `spec-pyforge-marshal` and co-governor `spec-pyforge-core`.
