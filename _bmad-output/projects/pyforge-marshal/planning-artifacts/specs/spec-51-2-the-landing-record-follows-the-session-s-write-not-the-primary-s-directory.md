---
title: '51.2: The landing record follows the session''s write, not the primary''s directory'
type: 'fix'
created: '2026-09-19'
status: 'done'
baseline_revision: '3acbff7d044a45634dbbb41dc0a0876f947ca44d'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `dispatch_land_finalize` only scans the primary checkout's `implementation-artifacts/` for Tier-3 specs to promote. When a session wrote its spec into the dispatch worktree's own Tier-3 dir instead, finalize sees nothing there, promotes nothing, and the story lands with no promoted spec and no journaled PR facts on the REFUSED result that recorded the failure.

**Approach:** Give `_scan_promotions` a second, optional discovery source — the dispatch worktree's own `implementation-artifacts/`, read before worktree teardown — merged after the primary's candidates so a worktree copy wins on key collision. Separately, the four `DispatchLandingResult(verdict=REFUSED)` constructors in `dispatch_land.py` that return after the PR is already known (`data["pr_number"] = pr.number` at line 317) start dropping that fact; make each carry `pr_number`/`subject` (known since line 317/324) and `marshal_native` (known since the line 326 check ran) instead of falling back to the dataclass's `None`/`False` defaults.

## Boundaries & Constraints

**Always:** The primary-directory promotion path stays byte-identical when no `worktree` is supplied (existing fixtures, all three other `_scan_promotions` callers). A worktree Tier-3 dir with no twin promotes nothing and raises no finding (silence is not a finding). `marshal_native` on a REFUSED result reflects the line-326 check's actual outcome at that point in execution, never a guess.

**Never:** Don't perform a merge or duplicate `_discover_candidates`'s parsing — call it twice, don't reimplement it. Don't change `_scan_promotions`'s three other callers (`unreachable_promotions_for_slug`, `run_promote`, `run_reconcile_completions`) — none pass `worktree`, all keep today's behavior. Don't add `merge_sha` to the REFUSED constructors — that fact becomes known later (`data["merged"] = True` at line 411), not "already known at :317"; adding it would overreach the story's own framing. Don't change the verdict on any of the four REFUSED sites — git/the merge outcome stay the sole authority on what merged; this story only stops dropping already-known facts from the record of a refusal.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Worktree has the only copy | Primary Tier-3 dir has no `spec-<key>.md`; worktree Tier-3 dir has one | `_scan_promotions(..., worktree=wt)` includes it in `plan.to_promote` (once merged) | No error expected |
| Both have a copy, same key | Primary and worktree Tier-3 dirs both have `spec-<key>.md` | The worktree's candidate is the one classified (later entry wins) | No error expected |
| No worktree twin | `worktree` given, but its Tier-3 dir has no matching file (or doesn't exist) | Scan behaves exactly as if `worktree=None`; no finding | No error expected |
| `worktree=None` (default) | Any existing caller | Byte-identical to current behavior | No error expected |
| Refusal after PR opened, before merge attempted | `merge_subject_is_marshal_native` returns `False` (line 326) | REFUSED result carries `pr_number`, `subject`; `marshal_native` stays `False` | No error expected — reflects the real check outcome |
| Refusal after PR merged, finalize subprocess fails | `process.run(...)` raises `ProcessError` after `data["merged"] = True` | REFUSED result carries `pr_number`, `subject`, `marshal_native=True` | `ProcessError` already caught and turned into an `MRS-DISP-020` finding — unchanged |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py::_scan_promotions` (line 665) — add keyword-only `worktree: Path | None = None`; after `candidates = _discover_candidates(fs, tier3_dir)` (line 707), when `worktree is not None`, compute `worktree_tier3_dir = worktree / "_bmad-output" / "projects" / project_slug / "implementation-artifacts"` and append `_discover_candidates(fs, worktree_tier3_dir)` to `candidates` (worktree candidates last → later-wins per `core/promotion.py::classify_promotion_candidates`'s `candidate_by_key` dict-merge). `_discover_candidates` (line 555) already tolerates a missing directory (`except OSError: spec_paths = []`) — no change needed there.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py` — the three other `_scan_promotions` callers (`unreachable_promotions_for_slug` ~line 801, `run_promote` ~line 1026, `run_reconcile_completions` ~line 3661) are out of scope; leave their call sites unchanged (default `worktree=None`).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py::finalize_dispatch_land` (line 26) — add `worktree: Path | None = None` param, thread into `_scan_promotions(root, project_slug, vcs=vcs, fs=fs, worktree=worktree)` (line 39). `main()` (line 76) — add an optional positional CLI arg (`parser.add_argument("worktree", nargs="?", default=None)`), convert to `Path` when present, pass through. Needs `from pathlib import Path` added to imports.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py` (subprocess call, lines 413-423) — append `str(worktree)` as a fourth `process.run([...])` list element (the enclosing function already has `worktree` in scope — it's a parameter of `execute_dispatch_land`, used earlier at line 358 for `try_heal_dispatch_land_merge`).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py` — four `DispatchLandingResult(verdict=DispatchLandingVerdict.REFUSED)` constructors, all after `data["pr_number"] = pr.number` (line 317) and `subject = identity.render_merge_subject(...)` (line 324):
  - Line 343 (`MRS-DISP-019`, marshal-native check just failed at line 326) → add `pr_number=pr.number, subject=subject` (leave `marshal_native` at its default `False` — accurate here).
  - Line 390 (`MRS-DISP-038`, escalated heal conflict, inside the `except ForgeCommandError` block that only runs after the line-326 check passed) → add `pr_number=pr.number, subject=subject, marshal_native=True`.
  - Line 405 (`MRS-DISP-020`, heal did not resolve) → same three fields as line 390.
  - Line 441 (`MRS-DISP-020`, finalize subprocess `ProcessError`, after `data["merged"] = True` at line 411) → same three fields as line 390. This is the fixture scenario named in the story (refusal after the PR merged).
  - Reference shape: the existing successful-path constructor at lines 450-456 (`DispatchLandingResult(verdict=..., merge_sha=head_sha, pr_number=pr.number, subject=subject, marshal_native=True)`) shows the dataclass's full field set — this story's fix populates the same `pr_number`/`subject`/`marshal_native` fields (never `merge_sha`, see Boundaries) on the four early-return REFUSED sites.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_landing.py` — `DispatchLandingResult` dataclass definition (frozen; fields `verdict, merge_sha=None, pr_number=None, subject=None, marshal_native=False`) — read-only reference, no change.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py` — `classify_promotion_candidates` (~line 400s) builds `candidate_by_key = {c.story_key: c for c in candidates}`, confirming later-tuple-entry-wins semantics that the worktree-appended-last ordering in `_scan_promotions` relies on. Read-only reference.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_finalize.py` — existing `test_finalize_passes_base_main_to_isolated_promote` calls `finalize_dispatch_land("pyforge-steward", "42.5")` (2 positional args, monkeypatches `_scan_promotions` to a `*args/**kwargs`-tolerant lambda) — stays green unmodified with `worktree` defaulting to `None`. Add a new test alongside it exercising the `worktree` threading.
- `src/shared/packages/pyforge-marshal/tests/unit/test_deploy.py` — has `_write_tier3_spec(base_dir, slug, filename_key, text)` and `_write_tracked_spec` helpers (reusable against any base dir, not just `tmp_path`) and a `_VALID_SPEC`-style fixture text constant already used by nearby tests — reuse both for the new `_scan_promotions(..., worktree=...)` tests (no existing direct test of `_scan_promotions`; it's currently only exercised via `run_promote`).
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_landing.py` — `FakeVcs`, `FakeForge` (`create_pr` → `PrInfo(number=42, ...)`), `FakeProcess` (`.run()` always succeeds) fixtures already present. `test_unverified_never_lands` (asserts `result.pr_number is None`) passes `verification_verdict=DispatchVerificationVerdict.REFUSED` directly — that path returns before line 317 and is unaffected by this fix. `test_execute_dispatch_land_pushes_branch_when_verified` (asserts `result.pr_number == 42`) is the LANDED-path reference. No existing fake raises from `.run()` — add a `BrokenProcess` (raises `ProcessError` from `.run()`) for the new post-merge-finalize-failure test.

## Tasks & Acceptance

**Execution:**
- `cli/deploy.py` -- add `worktree` param to `_scan_promotions`, merge a second `_discover_candidates` call over the worktree's Tier-3 dir (appended after primary candidates) -- gives finalize a second discovery source without duplicating the parser.
- `dispatch_land_finalize/__main__.py` -- add `worktree` param to `finalize_dispatch_land` + optional CLI positional, thread through to `_scan_promotions` -- exposes the new source end-to-end.
- `dispatch_land.py` -- pass `str(worktree)` as a fourth subprocess arg at the finalize call site -- lets the spawned finalize process know which worktree to also scan before it's torn down.
- `dispatch_land.py` -- add `pr_number`/`subject`(/`marshal_native` where already known-true) to the four early-return REFUSED constructors at lines 343, 390, 405, 441 -- stops the record of a refusal from dropping PR facts already established earlier in the same call.
- `tests/unit/test_deploy.py` -- unit-test `_scan_promotions`'s worktree-aware discovery: worktree-only copy, both-have-a-copy (worktree wins), worktree given but no twin (silence), `worktree=None` byte-identical.
- `tests/unit/test_dispatch_land_finalize.py` -- test that `finalize_dispatch_land(slug, key, worktree)` forwards `worktree` into `_scan_promotions`.
- `tests/unit/test_dispatch_landing.py` -- add a `BrokenProcess` fake and a test asserting the post-merge finalize-failure REFUSED result carries `pr_number == 42`, the rendered `subject`, and `marshal_native is True`.

**Acceptance Criteria:**
- Given a dispatch worktree whose `implementation-artifacts/` holds a Tier-3 spec the primary checkout's own `implementation-artifacts/` does not have, when `dispatch_land_finalize` runs with that worktree passed through, then the spec is discovered and included in the promotion plan (once its story key is in `merged_keys`).
- Given a worktree with no Tier-3 twin for the story key, when `_scan_promotions` runs with `worktree` set, then it behaves exactly as `worktree=None` would and raises no finding.
- Given the existing three `_scan_promotions` callers that never pass `worktree`, when they run, then their output is byte-identical to before this change.
- Given a PR that was opened and then merged (`data["merged"] = True`), when the finalize subprocess subsequently raises `ProcessError`, then the returned `DispatchLandingResult` has `verdict=REFUSED`, `pr_number` equal to the opened PR's number, `subject` equal to the rendered merge subject, and `marshal_native=True`.
- Given a PR that was opened but the rendered merge subject fails the marshal-native check, when the function returns its REFUSED result, then that result carries the same `pr_number`/`subject` and `marshal_native=False` (the check's real outcome).

## Spec Change Log

- 2026-09-19 (step-03 Verify / Matrix Test Audit): the implementation subagent's tests covered every I/O matrix row except "Refusal after PR opened, before merge attempted" (the line-343 `MRS-DISP-019` marshal-native-check-failure path) — no test exercised it. Added `test_execute_dispatch_land_refused_result_keeps_pr_facts_before_merge_native_check` to `tests/unit/test_dispatch_landing.py`, monkeypatching `pyforge.marshal.dispatch_land.merge_subject_is_marshal_native` to force the branch (this path is otherwise unreachable through legitimate business logic, since `render_merge_subject` and the check share the same `template`/`project_slug` and round-trip by construction). KEEP: all four implementation files and the other seven tests from the original pass were correct as written — this was a coverage gap only, not a code defect.

## Review Triage Log

### 2026-09-19 — Review pass
- verdicts: 10 findings — high 0, medium 4, low 4, false 2, maybe-false 0
- findings:
  - `[medium]` `[patch]` (Blind Hunter) `test_execute_dispatch_land_refuses_unknown_merge_conflicts` (MRS-DISP-038 escalated-conflict REFUSED site, dispatch_land.py:396-401) asserted only `verdict` and the finding message, never `pr_number`/`subject`/`marshal_native` — a regression in this story's own new field population there would go undetected — applied: extended that test with `pr_number`/`subject`/`marshal_native` assertions; green.
  - `[medium]` `[patch]` (Verification Gap, pre-verified) same MRS-DISP-038 site — filed as: existing test doesn't cover the new fields; disposition patch — applied: same extension above served both rows.
  - `[medium]` `[patch]` (Intent Alignment divergence) the "heal attempted, escalated_paths empty, not healed" REFUSED branch (MRS-DISP-020, dispatch_land.py:418-424) has zero test coverage of any kind, before or after this diff — its new `pr_number`/`subject`/`marshal_native=True` are wholly unverified — applied: added `test_execute_dispatch_land_refused_result_keeps_pr_facts_when_heal_fails` (`FakeVcs(merged=False)` + `BrokenForge()`, which reaches `heal.healed=False`/`escalated_paths=()` by construction) asserting REFUSED with the three fields plus the `MRS-DISP-020` finding; green.
  - `[low]` `[reject]` (Blind Hunter) a worktree Tier-3 candidate whose `fs.read_text` raises `FsError` (`text=None`) overrides a valid primary candidate on key collision (`candidate_by_key` dict-merge in `core/promotion.py::classify_promotion_candidates` keys purely on story_key, last-in-wins unconditionally), producing a spurious `MRS-DEPLOY-002` instead of promoting the good primary copy — verified real via `classify_promotion_candidates` reading. Rejected: the Boundaries text ("worktree copy wins on key collision") is unconditional with no validity carve-out, the confluence needed (colliding key AND an unreadable-at-scan-time worktree file) is unlikely in everyday use, and a validity-aware precedence fix is new branching logic, not a direct correction.
  - `[low]` `[patch]` (Blind Hunter) `DispatchLandingResult`'s docstring (dispatch_land.py:47, `"""Outcome of a dispatch land attempt."""`) never documented that `pr_number`/`subject`/`marshal_native` are now also populated on `REFUSED` once known, while `merge_sha` stays `None` until an actual merge SHA exists — applied: extended the docstring with that field-population note.
  - `[false]` `[false]` (Blind Hunter) claimed `_already_promoted_keys` processing duplicate story-key candidates from both sources wastes work and "doesn't share the later-wins precedence" — verified false: the function keys purely on `candidate.story_key` and never reads `candidate.text`, so precedence is structurally irrelevant there; two candidates sharing a key produce identical, correct results from that function regardless of which one's text is used — merely two redundant (not incorrect) filesystem globs.
  - `[low]` `[reject]` (Blind Hunter) a worktree candidate silently overriding a primary candidate on key collision produces no INFO/WARN finding even when the two copies' content genuinely differs, making the silent override harder to debug later. Rejected: cosmetic, unlikely to be hit in everyday use, and the fix (collision detection plus a new `Finding`) is new branching and state, not a direct correction.
  - `[low]` `[patch]` (Blind Hunter) `finalize_dispatch_land` had no docstring and the `dispatch_land_finalize/__main__.py` argparse `description`/args carried no mention of the new `worktree` parameter — applied: added a docstring to `finalize_dispatch_land` describing the optional worktree discovery source.
  - `[false]` `[false]` (Edge Case Hunter) claimed `main()`'s guard is a truthy check (`if args.worktree`) that would let an empty-string CLI arg coerce to `Path('.')` (the subprocess cwd) and scan the wrong directory — verified false: the actual guard at `dispatch_land_finalize/__main__.py:85` is `Path(args.worktree) if args.worktree is not None else None`, not a truthy check as cited, and regardless the sole real caller (`dispatch_land.py:442`'s `str(worktree)`, where `worktree` is `execute_dispatch_land`'s required, always-genuine `Path` parameter) can never produce an empty string, so the scenario is unreachable through this diff's actual integration.
  - `[medium]` `[patch]` (Verification Gap, pre-verified) the new subprocess-boundary argv element (`dispatch_land.py:442`'s `str(worktree)` appended to the `process.run(...)` tokens list) had no test asserting it — `FakeProcess.run` discarded `tokens` entirely and no test in `test_dispatch_landing.py` captured or asserted on it, so a silently dropped or misordered argv element would have made the whole worktree feature a no-op across the process boundary with nothing to catch it; disposition patch — applied: `FakeProcess` now records `(tokens, cwd)` per call; `test_execute_dispatch_land_pushes_branch_when_verified` asserts exactly one call whose trailing argv element equals `str(worktree)`.

## Design Notes

The four REFUSED sites split into two groups by what's actually known at each: line 343 returns *before* the marshal-native check passes, so it may honestly carry `pr_number`/`subject` but not `marshal_native=True` (the check failed — that's *why* it's returning REFUSED there). Lines 390/405/441 all execute only after that check already passed (326), so `marshal_native=True` is an established fact, not a guess, at each. `merge_sha` is deliberately left off every one of the four — it only becomes a known fact at line 411 (`data["merged"] = True`), which lines 343/390/405 never reach, and which line 441 reaches but the story's own Approach text scopes the fix to "facts already known at :317", not :411. Keeping `merge_sha` off all four keeps the fix narrow and matches the letter of the Boundaries rather than extending it by inference.


## Auto Run Result

**Summary:** `_scan_promotions` (`cli/deploy.py`) now accepts an optional keyword-only `worktree: Path | None`; when given, it is scanned as a second Tier-3 candidate source after the primary checkout's, so a story spec written into a dispatch worktree's own `implementation-artifacts/` (instead of the primary's) is still discovered and promoted, with the worktree's copy winning on a story-key collision. `dispatch_land_finalize.finalize_dispatch_land` threads a new optional `worktree` param into that call; `dispatch_land.py`'s subprocess invocation of it now passes `str(worktree)` as a fourth argv element, parsed back via `argparse`. Separately, the four `DispatchLandingResult(verdict=REFUSED)` construction sites in `dispatch_land.py` that fire after the PR is already known now carry `pr_number`/`subject` (all four), and `marshal_native=True` on the three that fire after the marshal-native check (dispatch_land.py:326) has already passed — the one site that fires because that check *failed* is left at the dataclass's `marshal_native=False` default, since guessing `True` there would misrepresent a check that never passed.

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py` -- `_scan_promotions` gained the optional `worktree` param and appends its Tier-3 candidates after the primary's.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py` -- `finalize_dispatch_land` threads `worktree` into `_scan_promotions`; `main()` parses it as an optional third positional CLI arg; added a docstring (review patch).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py` -- subprocess call appends `str(worktree)` as a fourth argv element; all four REFUSED-verdict `DispatchLandingResult` constructors now carry `pr_number`/`subject` (and `marshal_native=True` where the check already passed); `DispatchLandingResult`'s docstring documents the new field-population behavior (review patch).
- `src/shared/packages/pyforge-marshal/tests/unit/test_deploy.py` -- 4 new tests covering `_scan_promotions`'s worktree-only-copy, collision precedence, no-twin-silence, and default-byte-identical behavior.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_finalize.py` -- 2 new tests covering `worktree` forwarding into `_scan_promotions` and its `None` default.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_landing.py` -- 2 new tests for the two REFUSED-before-merge sites (marshal-native-check-fails, unknown-merge-conflicts field assertions); 1 new test for the heal-attempted-but-not-healed REFUSED site (review patch); the post-merge-finalize-subprocess-fails REFUSED site's existing new test; `FakeProcess` now records its calls and the LANDED-path reference test asserts the subprocess argv's trailing element is `str(worktree)` (review patch).

**Review findings breakdown (10 findings, 1 pass):**
- Patched (4 entries: 2 medium, 2 low) -- REFUSED-field test coverage at the MRS-DISP-038 escalated-conflict and MRS-DISP-020 heal-not-healed sites (Blind Hunter + Verification Gap + Intent Alignment, grouped, medium); `DispatchLandingResult` docstring (Blind Hunter, low); `finalize_dispatch_land` docstring (Blind Hunter, low); subprocess argv-boundary test coverage (Verification Gap, medium).
- Rejected (2, both low): a corrupt/unreadable worktree candidate overriding a valid primary candidate on key collision -- the Boundaries' "worktree wins on collision" is unconditional and the fix is new branching, not a direct correction (Blind Hunter); a silent collision override with no diagnostic finding -- cosmetic, and the fix is new branching/state (Blind Hunter).
- False (2): `_already_promoted_keys` processing a colliding key twice -- verified the function keys purely on `story_key`, never `candidate.text`, so precedence is structurally irrelevant there (Blind Hunter); an empty-string CLI `worktree` arg reaching `Path('.')` -- the cited guard snippet didn't match the actual `is not None` guard, and the sole real caller can never pass an empty string (Edge Case Hunter).

**Follow-up review recommendation: `true`.** Two medium-severity patched entries in this first pass (the REFUSED-field test-coverage group and the subprocess argv-boundary test) triggers the scoring rule's "two or more medium entries patched" clause. Named unverified risk: both patches were authored and applied by this same pass with no second independent review layer checking the fixes themselves -- specifically, whether `BrokenForge()` + `FakeVcs(merged=False)` genuinely reaches `heal.healed=False` with `escalated_paths=()` by construction (traced by hand against `dispatch_land_heal.py`, not independently re-reviewed), and whether `FakeProcess.calls` capturing is representative of the real `PosixProcess` argv shape.

**Verification performed:** `pixi run -e pyforge-marshal python -m pytest tests/unit/test_dispatch_landing.py tests/unit/test_deploy.py tests/unit/test_dispatch_land_finalize.py -q` (159 passed) after each patch; then both spec-named commands directly: `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` (8122 passed, 1 skipped, 12 deselected) and `pixi run --frozen -e pyforge-ci pyforge-deps-test` (130 passed, 3 skipped) -- both read directly from their own exit codes and full output, not through a pipe. `{diff_file}` rewritten from `baseline_revision` after patching; `git diff --stat` confirms only the 3 implementation files and 3 test files under `src/shared/packages/pyforge-marshal/` changed.

**Residual risks:** the two rejected findings (corrupt-worktree-candidate precedence; silent collision override) remain real, low-probability edge cases -- not tracked in `deferred` per the reject path (rejection is a terminal disposition, not a deferral) but visible in this triage log for any future pass. The named follow-up risk above (patch fixes not independently re-reviewed) is otherwise unmitigated beyond this pass's own direct test runs.

**Manual checks (if no CLI):**
- Confirm the story's own Given/When/Then/And (epics.md Story 51.2) is satisfied by the new tests, not just by manual inspection.

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-250`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py` (accepts the worktree beside `slug`/`key`), `.../dispatch_land.py` (spawns finalize with the worktree; the two REFUSED `DispatchLandingResult` constructors keep `pr_number` / `marshal_native`), `.../cli/deploy.py::_scan_promotions` / `_discover_candidates` (a second Tier-3 source: the dispatch worktree's `implementation-artifacts/`, read before teardown), tests.
Ledger key: `51-2-the-landing-record-follows-the-session-s-write-not-the-primary-s-directory`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-51-2-the-landing-record-follows-the-session-s-write-not-the-primary-s-directory.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 51.2 in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.
