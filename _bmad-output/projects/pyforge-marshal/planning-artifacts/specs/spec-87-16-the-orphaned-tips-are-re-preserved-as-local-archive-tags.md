---
title: "87.16: The orphaned tips are re-preserved as local archive tags"
type: 'chore'
created: '2026-10-04'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04-review.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-87-1-the-sweeper-reaches-remote-branches-and-never-deletes-a-protected-ref.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The 2026-10-04 cleanup left tips reachable from no `origin` ref, no tag and no local branch:
- 98 of the 454 deleted tips;
- 8 of the 30 `attempt-preserve/*` tips the operator retired the same day, listed in Story 87.1's spec.

Their objects are still in the primary clone and gc-eligible there. GitHub keeps them only at its own discretion; the retention period is undocumented. The clone held 7,718 loose objects, above `gc.auto`'s default of 6,700, so a routine command can start `git gc --auto`. The operator ruled on 2026-10-04 (review Q4): approve local annotated archive tags now, with no outward write, and push them only after the content review.

**Approach:**
- **Script.** A one-off, dry-run-default script under `scripts/` reads the day's branch-deletion activity (the `before` sha per branch) through an injectable reader. At runtime the reader is an authenticated `gh api`; it checks `gh api rate_limit` first and fails closed. The script adds Story 87.1's retirement table.
- **Manifest.** For every tip that no ref reaches, it writes a tracked manifest under `_bmad-output/projects/pyforge-marshal/planning-artifacts/preserve-manifests/`. Each row names the branch, the `before` sha, its reachability evidence, and the annotated `refs/tags/archive/heads/<branch>` tag it would write, with `Archive-From`, `Archive-Reason` and `Archive-Evidence` trailers.
- **Execute.** `--execute`, run by the operator, writes those tags **locally only**, and only for tips that are still unreachable.
- **Push.** Pushing is a separate step. The operator marks each row reviewed, and Story 87.15's content gate passes it.
- The script has no code dependency, so it can land first. It renders the archive shape AD-81 names; once Story 87.3 lands, a test pins that every name it writes parses with `pyforge.core.preserve_refs`.

Ledger key: `87-16-the-orphaned-tips-are-re-preserved-as-local-archive-tags`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-287 (FR-234, AD-81). A one-off recovery, so it is a `chore` with no flag.

## Acceptance Criteria

- Given a fixture of deletion events (branch, `before` sha) over a repository with a bare `origin`, where some tips are ancestors of `origin/main`, some reachable from another ref and some from nothing When the script runs without flags Then the tracked manifest lists exactly the unreachable ones with the tag each would get, and no ref changes.
- Given `--execute` When it runs Then each listed tip has a local annotated `refs/tags/archive/heads/<branch>` tag with its three trailers; a tip that became reachable since the dry run is skipped; nothing is pushed or deleted; running it again is a no-op.
- Given `gh api rate_limit` showing no authenticated quota, or a failed API call When the runtime reader runs Then the script exits 2 and writes no manifest; tests use the injected reader, never GitHub.
- **Operator-gated (not a dispatch step):** running `--execute` on the primary clone, and pushing any row, each wait for the operator's explicit confirmation. A row is pushed only after the operator marks it reviewed in the manifest and Story 87.15's gate passes it. Pausing local auto-gc (`git config gc.auto 0`) until the tags exist is the operator's choice.

## Boundaries & Constraints

**Always:** Dry run by default. Commit the manifest before any push. Fail closed on GitHub reads.

**Ask First:** `--execute` on the primary clone; every push.

**Never:** Never push from the script. Never delete a ref. Never create a branch to hold a tip.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` CAP-287 (FR-234, AD-81).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (preserved-work refs) entry.
Research: research § 2.8 and § 7.5; drafts' Story 87.12, split by the review (minor 5: this is its 87.12a); review Q4.
Ledger key: `87-16-the-orphaned-tips-are-re-preserved-as-local-archive-tags`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-04 under the operator's ruling of the same day.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- The script's test under `tests/scripts/` — expected: pass; `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass.
- Operator, after landing: run the script dry, review the manifest, then `--execute`; push reviewed rows only after Story 87.15 lands.

## Spec Change Log

- No change yet.

## Review Triage Log

- No review has run yet.
