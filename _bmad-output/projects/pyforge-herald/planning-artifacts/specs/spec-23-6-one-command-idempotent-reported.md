---
title: '23.6: One command, idempotent, reported'
type: 'feature'
created: '2026-09-16'
status: 'in-review'
baseline_revision: '537da5f6ebee2df7115fc5d75671fc68af18ccb1'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred:
  - summary: >-
      The idempotency AC is proven over hand-written fakes and one live
      smoke test that only exercised the skipped path, never a real
      seeded deck's unchanged path.
    evidence: |-
      No live Claude Design credentials are available in this or any
      other automated dispatch environment. If the gap is real it would
      be medium: a verification-depth gap, not a code defect. It would
      be settled by running `herald deck sync-all` twice against a deck
      with live Design credentials and real tracked state.
    location: >-
      src/shared/packages/pyforge-herald/src/pyforge/herald/sync_all.py
    severity: medium (unverified)
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Every stage exists as its own verb and an agent runs them from memory.

**Approach:** herald deck sync-all runs enumerate → pull moved etags → refresh → derive → push → prove → publish for every registered deck or one --slug. Per-deck report includes overwrote-local. Two consecutive runs: second is unchanged with zero writes. --dry-run prints without writing.

## Boundaries & Constraints

**Always:**
- Second consecutive run reports every deck unchanged.
- --dry-run writes nothing.

**Never:**
- Do not re-implement kernel verbs; call them.
- Do not treat facts.yaml as pullable.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| second run | no Design etag move | all unchanged; zero writes | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-design-sync-loop CAP-8 CAP-3`.
Surface: herald/cli.py deck sync-all --slug --dry-run; pixi deck-sync-all; run report; presentation-deck.md runbook..
Ledger key: `23-6-one-command-idempotent-reported`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-6-one-command-idempotent-reported.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's policy `verify_commands` entry; MRS-GATE-010 binds the dispatch gate to this Success signal, and it is read from the primary tree's tracked spec, so it must be declared here before dispatch, not by the session).

**Manual checks:**
- Two consecutive `herald deck sync-all` runs: the second reports every deck `unchanged` with zero writes to git or Design; `--dry-run` prints the same per-deck report without writing; the README/spec runbook points at the command rather than the steps.

## Review Triage Log

### 2026-09-18 — Review pass
- verdicts: 20 findings — high 2, medium 8, low 7, false 2, maybe-false 1
- findings:
  - `[high]` `[patch]` Blind Hunter: `--dry-run` reports `failed` (not `unchanged`/`would-sync`) for any deck that has ever had an export pushed — `_dry_run_preview` calls `deck_status()`, which walks every tracked etag key including `export:*`; `_remote_path_for_artifact` (deck_pipeline.py:1394-1397) raises `HeraldError` on any `export:*` key. Verified by reading `_status_for_slug`'s per-key loop (deck_pipeline.py:1433-1434) and `push_exports` writing `export:<filename>` etags (deck_pipeline.py:2061-2063). Action: `_dry_run_preview` now compares only pull-tracked keys instead of delegating to `deck_status()`.
  - `[high]` `[patch]` Edge Case Hunter: same defect, filed independently (sync_all.py:454-457) — same evidence and same fix as above.
  - `[medium]` `[patch]` Blind Hunter: per-deck `except errors.HeraldError` also swallows `errors.AuthError` (a `HeraldError` subclass per `errors.py:39`), contradicting the module's own docstring ("an `AuthError` reaching Design propagates ... through `dispatch`"). Verified via the class hierarchy (`AuthError(TransportError)`, `TransportError(HeraldError)`). Action: re-raise `AuthError` before the generic `HeraldError` catch in `sync_all()`.
  - `[medium]` `[patch]` Edge Case Hunter: same defect, filed independently (sync_all.py:585-586) — same evidence and same fix as above.
  - `[false]` `[reject]` Blind Hunter: "`overwrote-local` detection is effectively dead for 2 of 3 pull kinds." Verified `pull_standalone_bundle`/`pull_marp_source` write to a date-stamped filename (`deck_pipeline.py:877,977`); `_local_path_for_pull` mirrors the identical formula, so the dirty-check inspects exactly the path the pull is about to overwrite. On a different calendar day nothing at the new dated path was ever locally edited, so correctly reporting no overwrite there is accurate, not a detection gap — there is nothing to have overwritten.
  - `[medium]` `[patch]` Blind Hunter: a failure in `facts_refresher.refresh()`/`deriver.derive()`/`push_exports()` after the pull loop already ran discards that deck's already-true `pulled`/`overwrote_local` facts — the outer per-deck `except` in `sync_all()` (lines 576-586) replaces the whole report with a bare `error=...`, silently dropping an already-real `overwrote-local` warning. Verified by reading `_sync_one_deck`'s control flow (sync_all.py:490-520) and the enclosing `try/except` (sync_all.py:576-586). Action: `_sync_one_deck` now catches the tail-step failure itself and returns the already-gathered pull facts alongside the error.
  - `[medium]` `[patch]` Edge Case Hunter: same defect, filed independently (sync_all.py:505-520,585-586) — same evidence and same fix as above.
  - `[low]` `[patch]` Blind Hunter: a bad `--repo-root`/cwd with no `--slug` silently reports success doing nothing — `_known_slugs` returns `[]` when `presentations/` doesn't exist, so `sync_all()` returns an empty report and the CLI prints nothing, exit 0. Verified by reading `_known_slugs` (deck_pipeline.py:1480-1492) and `_run_deck_sync_all` (cli.py:132-167). Not rejected: the fix (print an explicit "0 decks found" line when the target list is empty) is a direct correction, not a guard/branch addition. Action: `_run_deck_sync_all` now prints a line when `report.decks` is empty.
  - `[low]` `[reject]` Blind Hunter: "no incremental progress output for a potentially long, fully sequential run." True but no named concrete harm beyond "can go silent for a while" — cosmetic, and streaming output would need restructuring `sync_all()`'s return-everything-at-the-end shape, which is more than a direct correction. Rejected.
  - `[false]` `[reject]` Blind Hunter: "no commit step, so the one command still leaves manual git work." The intent-contract's Approach names exactly `enumerate → pull → refresh → derive → push → prove → publish` — no commit step — and every called kernel verb (`pull_prototype` et al.) treats `commit` as strictly opt-in by its own docstring ("commit is opt-in, never implicit"). Not auto-committing is consistent with both the named steps and the called verbs' own convention, not a shortfall.
  - `[low]` `[patch]` Blind Hunter: `--dry-run`'s `would_sync=one.sync in ("changed", "conflict")` conflates a `"conflict"` status (Design unreachable, or the tracked file gone — `deck_pipeline.py:1441-1446`) with a genuine pending change. Verified by reading `_status_for_slug`. Action: `_dry_run_preview` now reports a conflict distinctly rather than as `would-sync`.
  - `[low]` `[patch]` Blind Hunter: `date_str` is computed once via `now()` in `_sync_one_deck` (sync_all.py:488) for the dirty-check path, then `pull_marp_source`/`pull_standalone_bundle` call `now()` again internally (deck_pipeline.py:875,974) for the actual write path; the two can disagree across a UTC-midnight boundary. Verified by reading both call sites. Fix is a direct correction (freeze the resolved datetime once, pass a callable returning the frozen value), so not rejected despite the narrow window. Action: freeze `now()` once per deck sync and thread the frozen value into the `pull_*` calls.
  - `[medium]` `[patch]` Blind Hunter: "first-time discovery of a new artifact kind is out of scope." Verified and found stronger than filed: `seed()` writes `state.DeckState(..., etags={}, ...)` (deck_pipeline.py:292-294) — a freshly-seeded deck's `existing.etags` starts **empty**, so `_sync_one_deck`'s `for artifact_key in sorted(existing.etags)` loop never runs at all, not even for the prototype. Since none of `pulled`/`overwrote_local`/`overrode`/`derived`/`pushed` get set, `DeckSyncReport.unchanged` evaluates `True` and the deck reports plain `unchanged` — indistinguishable from a deck that is genuinely fully synced. Action: a deck with no tracked artifacts at all now reports a distinct state instead of `unchanged`.
  - `[medium]` `[patch]` Edge Case Hunter: same defect, filed independently (sync_all.py:492) — same evidence and same fix as above.
  - `[medium]` `[patch]` Edge Case Hunter: `resolved_site_publisher.publish(repo_root=repo_root)` (sync_all.py:593-594) is not wrapped in any error handling; a failure there propagates out of `sync_all()` entirely, discarding every already-gathered per-deck `DeckSyncReport` — `_run_deck_sync_all` never gets to print a single deck's line even when every individual deck synced correctly. Verified: no try/except surrounds that call, unlike every per-deck step. Action: publish failure is now caught so the already-built per-deck reports still reach the caller.
  - `[low]` `[reject]` Edge Case Hunter: TOCTOU between `is_dirty()`'s check and the pull's own write (sync_all.py:428-430). Real but the window is sub-second and requires a human editing the exact file at the exact moment a batch sync runs; closing it needs a lock or re-check-after-write pattern, which is more than a direct correction. Rejected.
  - `[medium]` `[patch]` Verification Gap Reviewer (pre-verified per its own evidence rules): no test in `test_sync_all.py` seeds a `STANDALONE_BUNDLE_ARTIFACT_KEY` or `"marp:<kind>"` etag, so the corresponding branches in `_local_path_for_pull`/`_pull_one` are never exercised by any test in the repo — a future divergence between that duplicated path formula and `pull_standalone_bundle`'s/`pull_marp_source`'s own formula would ship silently. Action: add one test per non-prototype artifact kind.
  - `[maybe-false]` `[defer]` Intent Alignment Auditor: the idempotency AC ("second run reports unchanged with zero writes") is proven at the orchestration-logic level over hand-written fakes, and the one live two-consecutive-run smoke test in this worktree only exercised the `skipped` path (no seeded bridge state exists here) — never the `unchanged` path a real synced deck would take. If true this would be `medium` (a verification-depth gap, not a code defect). What would settle it: running `sync-all` twice against a deck with live Claude Design credentials and real tracked state. Deferred: no live Design credentials are available in this or any other automated dispatch environment (a pre-existing constraint, not caused by this story).
  - `[low]` `[reject]` Intent Alignment Auditor: dry-run's `would-sync`/`unchanged` vocabulary is narrower than epics.md Story 23.6's AC text ("prints the same report") and this spec's own Manual Checks wording ("prints the same per-deck report"). Checked feasibility: simulating the `overrode`/`derived` fields read-only would require either teaching `deck-facts`/`deck-trio` a dry-run mode (outside this story's declared surface per the module's own docstring) or reimplementing their comparison logic separately (forbidden by the intent-contract's own "Never: Do not re-implement kernel verbs; call them"), so full field parity is not achievable without violating a Never-constraint the diff correctly honors. The implemented, narrower scope is consistently documented everywhere a user would look (CLI `--help`, pixi task description, `docs/how-to/presentation-deck.md`), so nobody is misled in practice. Rejected: "the same report" reads more naturally as "the same per-deck report *format*" (one line per deck, in the run's own style) than as a literal field-for-field parity claim, and the stricter reading is infeasible under the spec's own constraints.
