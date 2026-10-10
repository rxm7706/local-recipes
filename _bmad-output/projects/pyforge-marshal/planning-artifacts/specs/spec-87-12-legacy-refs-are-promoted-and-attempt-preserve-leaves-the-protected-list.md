---
title: "87.12: Legacy refs are promoted and attempt-preserve leaves the protected list"
type: 'chore'
created: '2026-10-04'
status: 'done'
baseline_revision: 'ed652e85a16964ee2732e29ad9d65fcda1ab83f0'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04-review.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-87-1-the-sweeper-reaches-remote-branches-and-never-deletes-a-protected-ref.md
  - docs/governance/guild-roster.json
  - src/shared/packages/pyforge-core/src/pyforge/core/preserve_refs.py
deferred:
  - summary: >-
      Extend dirty-ref story inference with journal/run-id lookup when more legacy refs appear.
    evidence: |-
      Heuristic `_infer_story_from_dirty_name` may label some dirty refs as unbound when a story slug is recoverable from run metadata.
    location: >-
      scripts/legacy_preserve_promote.py
    severity: low (unverified)
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Legacy preserved work sits outside any durable namespace (research § 2.1, § 7.5):
- 17 `refs/attempt-preserve-dirty/*` refs; 16 hold commits on no `origin` ref.
- 3 local-only tags: `bmad-loop-preserve/5-9-intent-gap-2026-08-12`, and two flattened `archive/` tags.
- `refs/backup/pre-split-*` and `refs/bundle/pyforge-pages`, each holding 2 local-only commits.
- the `backup/*` branches, and `archive/crewai-toolkit-wip-2026`, an `archive/` name used as a branch.
- the 3 `attempt-preserve/*` branches the operator kept on `origin`, protected by ruleset 24451573.

The operator ruled on 2026-10-04 (review Q11, Q18): create `preserve/` twins for the 3 kept branches, then drop `refs/heads/attempt-preserve/**` from the ruleset and the protected list. The rest is promoted from a reviewed manifest, and nothing is deleted.

**Approach:**
- **Script.** A one-off, dry-run-default script under `scripts/` builds a tracked manifest under `_bmad-output/projects/pyforge-marshal/planning-artifacts/preserve-manifests/`, one row per item, through `pyforge.core.preserve_refs`. Each row names the twin it would write:
  - `preserve/pyforge-marshal/47.1/hand-<sha8>`, `preserve/pyforge-mason/6.3/hand-<sha8>` and `preserve/unbound/hand-<sha8>` (the 2026-07-12 pilot) for the 3 branches;
  - `preserve/<slug>/<N.M>/bmad-loop-<sha8>` where a dirty ref's story is known, else `preserve/unbound/bmad-loop-<sha8>`;
  - `preserve/pyforge-marshal/5.9/hand-<sha8>` for the `bmad-loop-preserve` tag;
  - a structure-preserving `archive/heads/…` or `archive/tags/…` twin for each flattened archive tag;
  - `preserve/unbound/hand-<sha8>` or `archive/heads/<branch>` for the backup, bundle and crewai refs.
- **Classification.** The manifest also classifies the 682 `rescue/dangling-*` tags (synthetic, stash, merge, patch-equivalent, unresolved) without changing any of them.
- **Execute.** `--execute` writes the twins locally. A row reaches `origin` only through Story 87.15's content gate, and only after the operator marks it reviewed in the manifest (review B1). The two protection removals each wait for explicit operator confirmation.

Ledger key: `87-12-legacy-refs-are-promoted-and-attempt-preserve-leaves-the-protected-list`.
Type / Effort / Deps: chore / M / S-87.3, S-87.15.

### Living CAP citations

- `spec-pyforge-marshal` CAP-287 (FR-234, AD-81). A one-off migration, so it is a `chore` with no flag.

## Acceptance Criteria

- Given a fixture repository with a bare `origin` holding each item kind above When the script runs without flags Then the tracked manifest names every item, the twin it would write and the evidence for the name, and no ref changes.
- Given `--execute` When it runs Then each twin exists locally as an annotated tag with its trailers, and nothing is deleted; running it again is a no-op.
- Given a row not marked reviewed, or one the content gate refuses When a push is attempted Then it is refused and stays local; a reviewed, clean row is pushed by one explicit refspec and verified by `ls-remote`.
- Given the 682 `rescue/dangling-*` tags When the manifest is written Then each carries a classification, and no tag is created, moved or deleted.
- **Operator-gated (not a dispatch step):** once the 3 `attempt-preserve/*` twins are on `origin`, removing `refs/heads/attempt-preserve/**` from ruleset 24451573 (a GitHub settings change), and removing the `refs/heads/attempt-preserve/` entry from the roster's `protected_refs` (a governance act), each wait for the operator's explicit confirmation. The manifest records each confirmation; a dispatched session never makes either change.

## Boundaries & Constraints

**Always:** Dry run by default. Write the manifest, and commit it, before any push. Use the one grammar.

**Ask First:** Every push of previously local-only content (row by row), and both protection removals.

**Never:** Never delete a ref, legacy tag or branch. Never push past the gate. Never change a GitHub setting from a session.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` CAP-287 (FR-234, AD-81).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (preserved-work refs) entry.
Research: drafts' Story 87.12, split by the review (minor 5: this is its 87.12b); review B1, M4, Q11, Q18.
Ledger key: `87-12-legacy-refs-are-promoted-and-attempt-preserve-leaves-the-protected-list`.
Ledger status at mint: `backlog`.
Deps: S-87.3, S-87.15.
Minted 2026-10-04 under the operator's ruling of the same day.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- The script's test under `tests/scripts/` — expected: pass; `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass.
- Operator, after landing: run the script dry and review each manifest row; then `--execute`; then push the reviewed rows; then the two protection removals, each by explicit confirmation.

## Spec Change Log

- No change yet.

## Review Triage Log

### 2026-10-09 — Review pass
- verdicts: 3 findings — high 0, medium 0, low 1, false 1, maybe-false 1
- findings:
  - `[low]` `[patch]` `legacy_preserve_promote.execute_twins` guessed producer from substring — use `parse_preserve_ref` for trailer producer — fixed in review pass.
  - `[false]` `[reject]` Fixture tests do not cover full 682-tag inventory — AC is satisfied by classification helper + dry-run manifest shape; live inventory is operator dry-run on primary clone.
  - `[maybe-false]` `[defer]` Dirty-ref story inference heuristics may miss some run/story mappings — evidence: only name-based rules; operator manifest review (B1) catches mis-twin rows before push.
    - summary: >-
        Extend dirty-ref story inference with journal/run-id lookup when more legacy refs appear.
      evidence: |-
        Heuristic `_infer_story_from_dirty_name` may label some dirty refs as unbound when a story slug is recoverable from run metadata.
      location: >-
        scripts/legacy_preserve_promote.py
      severity: low (unverified)

## Auto Run Result

Status: done

**Summary:** Shipped `scripts/legacy_preserve_promote.py` to inventory legacy preserved-work refs, write `legacy-preserve-promote-<date>.json`, optionally create local `preserve/` / `archive/` twins via `pyforge.core.preserve_refs`, classify every `rescue/dangling-*` tag without mutating it, and refuse push until a row is marked reviewed.

**Files changed:**
- `scripts/legacy_preserve_promote.py` — dry-run-default promotion script
- `tests/scripts/test_legacy_preserve_promote.py` — fixture git tests (dry run, execute idempotence, push refusal, synthetic classification)
- `scripts/spec_surface_allowlist.txt` — allowlist entry
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/preserve-manifests/README.md` — operator workflow note
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md` — surface reconcile + expand (Story 87.12)

**Review:** 1 patch applied (producer parsing); 1 false reject; 1 defer (inference heuristics).

**Verification:** `pytest tests/scripts/test_legacy_preserve_promote.py` (4 passed); `pyforge-doctor-scripts-test` (1439 passed); `pyforge-marshal-test` (12174 passed); `pyforge-deps-test` (130 passed); `lint-types` (exit 0); `python scripts/spec_surface_reconcile.py` (exit 0).

**Residual risks:** Live primary-clone manifest row count depends on operator environment; ruleset/roster changes remain operator-gated rows only.
