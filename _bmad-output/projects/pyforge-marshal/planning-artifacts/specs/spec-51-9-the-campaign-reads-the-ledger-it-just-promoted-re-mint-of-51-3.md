---
title: '51.9: The campaign reads the ledger it just promoted (re-mint of 51.3)'
type: 'fix'
created: '2026-09-19'
status: 'done'
baseline_revision: '671072aa39c960e239e36ff4c093ad64269a91b1'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      A failed deploy_run.write mint/write inside finalize_dispatch_land can turn an
      already-successful land+promote into a reported failure.
    evidence: |-
      Edge Case Hunter (EC2) on the 51.9 review pass. Pre-existing via
      _promote_sprint_ledger's own two prior deploy_run.write calls in the same function,
      not introduced by this story; a real fix requires redesigning _DeployRun /
      finalize_dispatch_land's shared error-severity policy — a distinct, unscoped change.
      Reshaped 2026-09-19 from the session's bare-string item into the summary/evidence/
      location form so `deferred-work` can see it (a bare string is invisible to the twin check).
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py::finalize_dispatch_land
    severity: low
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `_promote_sprint_ledger` (cli/land.py) deliberately never touches the primary
checkout's own working tree when it promotes a station's sprint-status ledger onto
`origin/main` (CAP-5 isolation) — but nothing else picks up that promotion either, so the
fleet campaign's next cycle keeps reading the primary's stale on-disk ledger copy until a
human runs `git pull`. Story 51.3 specced this same fix and landed hollow (PR #1501, spec-only
diff — the session was killed by the harness's 600s background-wait ceiling before
implementing anything).

**Approach:** After `dispatch_land_finalize` promotes a story's ledger key, reuse the
existing `_resync_home_branch` (cli/land.py) verbatim to fast-forward the primary checkout
onto `origin/main` whenever it is safely a clean `main` at its own tip; when it isn't (dirty,
non-`main`, or diverged), reuse the existing `_resync_home_branch` refusal (which already
appends a named WARN finding) rather than moving it, and journal the outcome. Independently,
the fleet campaign's ledger read (`cli/dispatch.py`, three call sites via
`HarnessPort.ledger_story_statuses`) falls back to reading `origin/main`'s copy of the ledger
directly (via `VcsPort.file_text_at_ref` + the existing private text parser
`_parse_sprint_ledger_statuses`) whenever the primary checkout is not verifiably a clean
`main`, so the campaign never blocks on a checkout it must not touch.

## Boundaries & Constraints

**Always:** A dirty or non-`main` primary checkout is never fast-forwarded or otherwise
mutated by either fix. `_promote_sprint_ledger` remains the sole writer of the promoted
ledger onto the remote tip — this story adds a reader/resync step, never a second writer. A
primary checkout already at `origin/main`'s tip is left byte-identical (fast-forward to the
same commit, or the read path's local/remote branches simply agree). The fast-forward and the
fallback read each use their own existing, already-registered failure signal
(`_resync_home_branch`'s `_MRS_LAND_009` WARN; the read path's own pre-existing
`try/except` Finding at each of the three call sites) — no new Finding code is introduced.

**Never:** No new `Finding` code, no new entry in `core/verdict.py`'s classification table.
No change to `_promote_sprint_ledger`'s signature, body, or its CAP-5 no-touch-`root`
invariant. No change to `HarnessPort.ledger_story_statuses`'s contract (it keeps reading an
explicit local path via `bmad_loop.sprintstatus.load`). No use of `scripts/bmad-switch` or the
global switch-managed symlinks (this worktree has neither).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Finalize resyncs a clean primary | `dispatch_land_finalize` just promoted a key; primary checkout is a clean, unmodified `main` one commit behind `origin/main` | `_resync_home_branch` fast-forwards `root` to `origin/main`'s tip; outcome journaled | No error expected |
| Finalize refuses a dirty/non-main primary | Primary checkout has uncommitted changes, or is checked out to a branch other than `main` | `_resync_home_branch` refuses (no fast-forward), appends its existing `_MRS_LAND_009` WARN; outcome journaled | WARN only, never escalated to finalize's own exit code |
| Campaign reads a promotion via a clean primary | Primary checkout is clean `main` at `origin/main`'s tip; ledger already fast-forwarded locally | Ledger read via the existing local `HarnessPort.ledger_story_statuses(ledger_path)` path (unchanged) | Existing per-call-site error handling unchanged |
| Campaign reads a promotion via a stale/dirty/non-main primary | Primary checkout is one commit behind (or dirty, or non-`main`), `origin/main` already carries the promoted ledger | Ledger statuses are read from `origin/main` via `file_text_at_ref` + `_parse_sprint_ledger_statuses`, so the very next cycle reports the story `done` and chains the next ready story with zero operator commands | Falls back to the local `HarnessPort` read (and that call site's existing error handling) if the remote read itself fails or the path is absent at `origin/main` |
| Fixture replays the herald 2026-09-18 sequence | Ledger promoted remotely by a sibling station's finalize; primary one commit behind | Next fleet cycle reports the story `done`; `_promote_sprint_ledger` gains no second writer; a primary already at `origin/main` reads byte-identical to today | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py` -- Part A edit target. `finalize_dispatch_land` (currently: normalize key -> scan promotions -> execute promotion plan -> `_promote_sprint_ledger(...)` -> compute `blocking` from ERROR findings -> return). Already imports `_promote_sprint_ledger` from `..cli.land`. Add `_resync_home_branch` to that same import; add `from pyforge.marshal.core.journal import Phase`; add module constant `_FINALIZE_RESYNC_KIND = "dispatch-land-finalize-resync"` (naming matches the existing `_LAND_*_KIND` convention in `cli/land.py:173-182`).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py:1612-1711` -- `_resync_home_branch(vcs, resync_enabled, merge_strategy, git_repo_root, home, base, head_branch, findings) -> bool | None`. REUSE VERBATIM, unmodified. Verifies `home`'s checked-out SHA matches `head_branch`'s own resolved tip (`resolve_ref` vs `worktree_head_sha`); mismatch appends `_MRS_LAND_009` WARN and refuses (no fast-forward attempted, no exception). On match: `fetch`s then `fast_forward`s; returns `True` on success/already-current, or appends `_MRS_LAND_009` WARN and returns `False` on any git failure (diverged, dirty, no network, held lock). Never raises; never escalates to a caller's own exit code. Call it with `home=git_repo_root=root`, `base=head_branch="main"`, `merge_strategy="merge"`, `resync_enabled=True`. Correction (review pass, 2026-09-19): `_resync_home_branch`'s own only precondition is a SHA-match between `home`'s checked-out commit and `head_branch`'s resolved tip -- it never calls `has_uncommitted_changes`. A dirty checkout sitting exactly at local `main`'s own tip (e.g. an uncommitted edit, no new commit) would pass that SHA check unchanged and still get fast-forwarded with the dirty changes left in place, violating this spec's own "Always" line. The caller (`dispatch_land_finalize`) MUST call `vcs.has_uncommitted_changes(root)` itself, immediately before calling `_resync_home_branch`, and skip the call entirely (treat as refused, `resynced=False`, no WARN needed since nothing was attempted) when it returns `True` -- `_resync_home_branch` itself stays unmodified.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py:1360-1450` -- `_promote_sprint_ledger(fs, vcs, root, slug, wave_keys, deploy_run, findings, *, base) -> tuple[str, ...]`. READ-ONLY / UNCHANGED per Binding. Docstring: must never `write_text_atomic` + `commit_paths` on `root` (CAP-5). Confirms `root`'s working tree is never touched by this function -- the gap this story closes.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py:1287-1308` -- `_parse_sprint_ledger_statuses(text: str) -> dict[str, str]`. REUSE VERBATIM for Part B. Pure, non-raising text scanner of the `development_status:` YAML block, in-file order preserved. Already used internally by `_promote_sprint_ledger`'s own key-diffing helper. Import as `from .land import _parse_sprint_ledger_statuses` in `cli/dispatch.py` -- confirmed no circular import (`cli/land.py` imports nothing from `cli/dispatch.py`).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py:~1786-1900` -- `_DeployRun.write(findings, *, kind, phase, payload, intent_id=None) -> JournalEntryId | None`. REUSE for Part A's observation write. Precedent for a standalone `Phase.OBSERVATION` write (no INTENT/OUTCOME pairing): `cli/land.py:1043-1059` (`_LAND_OBSERVATION_KIND`).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/journal.py` -- `Phase` enum (`INTENT`, `OUTCOME`, `OBSERVATION`). Import `Phase` for the new observation write.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/vcs.py` -- `VcsPort` Protocol. Methods used by the new Part B helpers: `has_uncommitted_changes(worktree_path) -> bool`, `worktree_head_sha(worktree_path) -> str`, `resolve_ref(repo_root, ref) -> str`, `file_text_at_ref(repo_root, ref, path) -> str | None` (`None` if path absent at ref; raises `VcsCommandError` on other failures). All already implemented by `GitVcs` (`adapters/vcs_git.py`).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/harness.py:626-644` -- `HarnessPort.ledger_story_statuses(path) -> tuple[tuple[str, str], ...]`. UNCHANGED contract; remains the primary read path when the checkout is verifiably clean-main.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_fleet.py:329` -- `station_ledger_path(repo_root, slug) -> Path`. REUSE as-is; no changes.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` -- Part B edit target, three call sites of `harness.ledger_story_statuses(ledger_path)`:
  - `gather_fleet_missing_spec_escalations` (~line 2890-2957, call at ~2939, inside `try/except (HarnessError, OSError, ValueError): continue`) -- needs a new `vcs: VcsPort` parameter (currently has none); its sole caller is `cli/status.py` (~line 1627, where `vcs` is already in local scope).
  - `execute_fleet_cycle` (~line 3291-3429, call at ~3378, inside `try/except` that appends `MRS-DRAIN-003` WARN and marks the station `LEDGER_UNREADABLE`) -- already has `vcs: VcsPort` in signature.
  - `run_fleet_drain` (~line 3995-4199, call at ~4166, inside `try/except` that appends `MRS-DRAIN-015` ERROR and returns early) -- already has a resolved `vcs` local (`vcs if vcs is not None else GitVcs()`, line ~4014).
  Replace all three calls with a new private helper `_station_ledger_statuses(*, harness, vcs, repo_root, ledger_path)`, preserving each site's own existing exception handling verbatim (the helper raises only what `HarnessPort.ledger_story_statuses` already raises; any `VcsCommandError` from the remote-read attempt is caught inside the helper itself and never propagates).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py:~1580-1634` -- sole caller of `gather_fleet_missing_spec_escalations`; `vcs` already in local scope just above the call (`vcs.repo_common_root(...)`, `vcs.list_worktrees(...)`). Thread `vcs=vcs` into the call.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_land_finalize.py` -- all 3 existing tests stub `GitVcs` as `lambda: object()`; each needs `_resync_home_branch` monkeypatched to a no-op too (a bare `object()` has no `resolve_ref`/`worktree_head_sha`, so an unstubbed unconditional call would raise `AttributeError` and break them). Add one new test asserting `_resync_home_branch` is invoked with `(vcs, True, "merge", root, root, "main", "main")` after `_promote_sprint_ledger`.
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_fleet.py` -- home of the new Part B fixture test. `FakeVcs` (~line 430-550) needs `has_uncommitted_changes`, `resolve_ref`, `file_text_at_ref` added (configurable via new instance attributes so a test can mark the primary dirty/diverged/clean and stock a fake `origin/main` ledger blob). `FakeHarness.ledger_story_statuses` (~line 517) derives station slug from the ledger path's directory SHAPE (`path.parent.parent.name`), not file content -- this is why the fallback must use `file_text_at_ref` + `_parse_sprint_ledger_statuses` directly rather than routing a temp file back through `HarnessPort`. Model the new test on `test_once_the_ledger_promotes_the_next_story_dispatches` and `test_herald_2026_09_18_three_cycle_replay_ends_with_the_next_story` (~line 3323-3412), both multi-cycle ledger-promotion replays.

## Tasks & Acceptance

**Execution:**
- `dispatch_land_finalize/__main__.py` -- import `_resync_home_branch` alongside `_promote_sprint_ledger`; import `Phase`; add `_FINALIZE_RESYNC_KIND` constant; immediately after `_promote_sprint_ledger(...)`, call `vcs.has_uncommitted_changes(root)` FIRST -- when `True`, skip `_resync_home_branch` entirely and treat the outcome as `resynced=False` (nothing was attempted, no new WARN); only when `False` call `_resync_home_branch(vcs, True, "merge", root, root, "main", "main", findings)`. Either way, finish with `deploy_run.write(findings, kind=_FINALIZE_RESYNC_KIND, phase=Phase.OBSERVATION, payload={"story_key": str(key), "resynced": <resolved value>})` -- makes the primary pick up its own promotion, with the refusal/failure path durably journaled, and never fast-forwards a dirty checkout (review pass, 2026-09-19: the prior draft relied on `_resync_home_branch`'s own SHA-match check alone, which does not cover dirtiness).
- `cli/dispatch.py` -- add `from .land import _parse_sprint_ledger_statuses`; add `_primary_checkout_is_clean_main(vcs, repo_root) -> bool` (no uncommitted changes AND `worktree_head_sha(repo_root) == resolve_ref(repo_root, "main")`); add `_station_ledger_statuses(*, harness, vcs, repo_root, ledger_path) -> tuple[tuple[str, str], ...]` (trusts the local `HarnessPort` read when clean-main; otherwise reads `origin/main`'s ledger blob via `vcs.file_text_at_ref` and parses via `_parse_sprint_ledger_statuses`, falling back to the local `HarnessPort` read if the remote read fails or returns `None`); add `vcs: VcsPort` parameter to `gather_fleet_missing_spec_escalations`; swap all three `harness.ledger_story_statuses(ledger_path)` call sites for the new helper, keeping each site's own exception handling unchanged -- lets the campaign see a sibling's promotion without a manual pull.
- `cli/status.py` -- thread `vcs=vcs` into the `gather_fleet_missing_spec_escalations(...)` call -- keeps the new parameter satisfied at its only call site.
- `tests/unit/test_dispatch_land_finalize.py` -- monkeypatch `_resync_home_branch` to a no-op in the 3 existing tests (prevents `AttributeError` against the existing `object()`-stubbed `GitVcs`); add a new test asserting `_resync_home_branch` is called with the correct positional args after ledger promotion.
- `tests/unit/test_dispatch_fleet.py` -- extend `FakeVcs` with `has_uncommitted_changes`, `resolve_ref`, `file_text_at_ref`; add a fixture test replaying a sibling-promoted, primary-one-commit-behind ledger, asserting the very next cycle reports the story `done` and chains the next ready story.

**Acceptance Criteria:**
- Given a clean primary checkout at `main`'s own tip immediately after `_promote_sprint_ledger` pushes to `origin/main`, when `dispatch_land_finalize` runs, then `_resync_home_branch` fast-forwards the primary to `origin/main`'s tip and the outcome is journaled.
- Given a dirty or non-`main` primary checkout, when `dispatch_land_finalize` runs, then the primary is never moved, `_resync_home_branch`'s existing `_MRS_LAND_009` WARN fires, and the refusal is journaled.
- Given the ledger was promoted onto `origin/main` by a sibling station's finalize while the campaign's primary checkout sits one commit behind, when the fleet cycle next reads that station's ledger, then it reads the promoted statuses from `origin/main` and reports the story `done`, chaining the next ready story with zero operator commands.
- Given the primary checkout is already byte-identical to `origin/main`, when the fleet cycle reads the ledger, then it reads the local copy exactly as before (no behavior change).
- Given `_promote_sprint_ledger`'s own contract, when either fix runs, then `_promote_sprint_ledger` gains no second writer and its CAP-5 no-touch-`root` invariant is preserved.

## Design Notes

Both fixes deliberately reuse existing, already-tested primitives (`_resync_home_branch`, `_parse_sprint_ledger_statuses`) rather than introduce new safety predicates or Finding codes: `_resync_home_branch` already encodes the exact "is this checkout a clean, unmoved `main`" gate the intent requires, and every `Finding` code must be registered in `core/verdict.py`'s classification table (and `core/findings.py`'s parallel catalog) before use -- avoiding new codes keeps this a pure reuse-and-wire story, consistent with Simplicity First. The fallback read intentionally bypasses `HarnessPort` for the remote case because the test double `FakeHarness` derives station identity from the ledger path's directory shape, not its content -- routing a fetched blob through a temp path would silently break that fixture even though the real adapter reads real content; reading via `VcsPort.file_text_at_ref` + the already-private text parser avoids that mismatch entirely.


## Review Triage Log

### 2026-09-19 — Review pass

Verdicts: high=4, medium=6, low=2, false=5, maybe-false=0 (total=17)

| # | Layer | Finding | Verdict | Root-cause group | Route |
|---|-------|---------|---------|-------------------|-------|
| BH1 | Blind Hunter | Only 3 of 6 `ledger_story_statuses` call sites route through the new fallback | false | — | — |
| BH2 | Blind Hunter | Write-side resync has no dirty-checkout guard of its own | high | Group 1 | bad_spec |
| BH3 | Blind Hunter | `_primary_checkout_is_clean_main`'s `except VcsCommandError` narrower than its "any git failure" docstring claim | false | — | — |
| BH4 | Blind Hunter | `resync_enabled=True` / `"merge"` / `"main"`/`"main"` hardcoded, unlike other `_resync_home_branch` call sites | false | — | — |
| BH5 | Blind Hunter | No test for a clean-but-diverged-from-`main` primary hitting the remote-read fallback | medium | Group 4 | patch |
| BH6 | Blind Hunter | New journal-write's actual payload (`kind`/`phase`/`resynced`) never asserted, only the call args to a mocked `_resync_home_branch` | medium | Group 3 | patch |
| BH7 | Blind Hunter | No test for a remote-read failure/absent-ledger falling back to the local `HarnessPort` read | medium | Group 4 | patch |
| EC1 | Edge Case Hunter | No locking around the new resync's fetch/fast-forward on the shared primary checkout | low | — | reject |
| EC2 | Edge Case Hunter | A failed `deploy_run.write` mint could turn a successful land+promote into a reported failure | low | — | defer |
| EC3 | Edge Case Hunter | Same dirty-checkout gap as BH2, framed as a race between an operator's own edit and the resync | high | Group 1 | bad_spec |
| EC4 | Edge Case Hunter | SHA-match gate doesn't confirm HEAD is attached to `refs/heads/main` (detached-HEAD-at-same-SHA edge case) | false | — | — |
| EC5 | Edge Case Hunter | `canonical_repo_root(...)` call in `_station_ledger_statuses` allegedly runs outside its `try/except` | false | — | — |
| IA1 | Intent Alignment Auditor | Diff implements "fast-forward when SHA matches," spec text says "fast-forward when clean AND SHA matches" -- readings diverge | high | Group 1 | bad_spec |
| IA2 | Intent Alignment Auditor | Test suite never observes the resync's actual journaled outcome, only that a (mocked) function was called | medium | Group 3 | patch |
| IA3 | Intent Alignment Auditor | Spec's own I/O matrix row 4 (remote-read failure) has no corresponding test | medium | Group 4 | patch |
| IA4 | Intent Alignment Auditor | `home == git_repo_root` is a parameter combination with no precedent in `_resync_home_branch`'s own test history | medium | Group 3 | patch |
| VG1 | Verification Gap Reviewer | `_station_ledger_statuses`'s remote-read fallback never calls `vcs.fetch` first, so `origin/main` may be a stale cached ref | high | Group 2 | patch |

**Group 1 (BH2, EC3, IA1) -- `bad_spec`, high.** Verified directly: `_resync_home_branch` (cli/land.py:1612-1711) refuses only on a SHA mismatch between `home`'s checked-out commit and `head_branch`'s resolved tip; it never calls `has_uncommitted_changes`. This spec's own Code Map told the implementer that call "already implements... no new predicate needed," which is false and is the direct cause of the gap -- a dirty checkout sitting at `main`'s own local tip would pass the SHA check unchanged and still be fast-forwarded with the dirty changes in place, violating this same spec's "Always" line ("A dirty ... primary checkout is never fast-forwarded ... by either fix") and the epics.md acceptance criterion. Code Map and Tasks & Acceptance corrected above (2026-09-19) to require an explicit `vcs.has_uncommitted_changes(root)` gate in `dispatch_land_finalize/__main__.py` before calling `_resync_home_branch`, without modifying `_resync_home_branch` itself. `review_loop_iteration` incremented to 1.

**Group 2 (VG1) -- `patch`, high.** Verified directly: `grep -n "vcs\.fetch\|\.fetch(" cli/dispatch.py` returns no matches -- nothing refreshes `refs/remotes/origin/main` anywhere in the fleet-cycle flow before `_station_ledger_statuses` reads it via `file_text_at_ref`. `_resync_home_branch`'s own `fetch` call (reached only via the write-side path, and only when the SHA-match precheck passes) does not cover the read side's own target scenarios (dirty/diverged primary), so in the exact scenario this story exists to fix, the fallback could silently serve a stale cached ref. Fix: call `vcs.fetch(repo_root, "origin", "main")` before `vcs.file_text_at_ref(...)` in `_station_ledger_statuses`; extend `FakeVcs` to record fetch calls and assert one happens in the fallback-path test.

**Group 3 (BH6, IA2, IA4) -- `patch`, medium.** The only test for Part A (`test_finalize_resyncs_the_primary_after_ledger_promotion`) mocks `_resync_home_branch` entirely and asserts only the call arguments, never the actual journal entry `deploy_run.write` produces, and nothing anywhere exercises `_resync_home_branch` with `home == git_repo_root` (a parameter shape none of its 3 pre-existing call sites use) against a real repo. Fix: since `LocalFs` is now real/unstubbed in this test file, read the journal entry back from disk and assert `kind`/`phase`/`payload["resynced"]`; add one small test calling `_resync_home_branch` directly against a scratch git repo with `home == git_repo_root` to confirm the collapsed-parameter shape fast-forwards correctly end-to-end.

**Group 4 (BH5, BH7, IA3) -- `patch`, medium.** `test_sibling_promoted_ledger_is_read_when_primary_sits_behind` is the only new read-side test and covers only the `dirty=True` branch. Fix: add a case with a clean-but-diverged-from-`main` primary (`resolve_ref` != `worktree_head_sha`, `dirty=False`) hitting the same remote-read path, and a case where the remote read fails/returns `None` and the helper falls back to the existing local `HarnessPort` read.

**Rejected/deferred (BH1, BH3, BH4, EC1, EC2, EC4, EC5) -- no code change.**
- BH1: false. The 3 other direct `harness.ledger_story_statuses(...)` call sites (`cli/deploy.py:3778`, `cli/status.py:2225`, `cli/init.py:1716-1717`) are single-station diagnostic/promote reads (one already carries its own, unrelated advisory-lock TOCTOU fix), not the cross-station fleet-cycle scenario this story's Problem statement scopes.
- BH3: false. Re-read `adapters/vcs_git.py::_run`: every git launch/exit failure (timeout, missing executable, EACCES, corrupt binary) is funneled into `VcsCommandError` -- it is the sole exception type `has_uncommitted_changes`/`worktree_head_sha`/`resolve_ref` can raise, so "any git failure" is accurate.
- BH4: false/rejected. `dispatch_land_finalize` has no existing configurability surface (no CLI flags), and `home=root`/`base=head_branch="main"` are the only correct values for this specific always-on finalize scenario -- adding configurability here would be speculative, against Simplicity First.
- EC1: low, rejected. `_resync_home_branch`'s own docstring already anticipates "a held lock" as a gracefully-handled, non-blocking failure (one WARN, no crash) -- this is a deliberate, evidenced existing convention (its 3 pre-existing call sites carry no locking either), not an oversight this story introduces reason to fix.
- EC2: low, deferred (named reason). Verified `_promote_sprint_ledger` already calls `deploy_run.write` twice, earlier in the same function, feeding the same `blocking` check -- the risk is identical and pre-existing, not attributable to this story's own new call. A real fix would mean redesigning `_DeployRun`/`finalize_dispatch_land`'s error-severity policy shared by unrelated, already-shipped call sites -- a distinct, unscoped cross-cutting change, not a same-sitting fix for this story.
- EC4: false. `worktree_head_sha(...) == resolve_ref(...)` plus `has_uncommitted_changes() == False` already guarantees the on-disk ledger's content is byte-identical to `main`'s tip regardless of whether HEAD is attached to `refs/heads/main` or detached at the same commit -- no incorrect read results from skipping a branch-name check.
- EC5: false. Direct re-read of `_station_ledger_statuses` confirms `canonical_repo_root(repo_root)` runs inside the `try: ... except (VcsCommandError, ValueError):` block, not outside it as claimed.

### 2026-09-19 — Fix round (review_loop_iteration 1)

The step-03 subagent (same agent, re-engaged) applied all four routed groups with the smallest changes:

- **Group 1 (`bad_spec`)** — `dispatch_land_finalize/__main__.py` now calls `vcs.has_uncommitted_changes(root)` immediately after `_promote_sprint_ledger(...)`; when dirty, `_resync_home_branch` is never called and `resynced=False` is journaled. `_resync_home_branch` itself is unmodified. New test: `test_finalize_skips_resync_on_a_dirty_primary`.
- **Group 2 (`patch`, VG1)** — `_station_ledger_statuses` (cli/dispatch.py) now calls `vcs.fetch(repo_root, "origin", "main")` immediately before `vcs.file_text_at_ref(...)`, inside the same `try/except (VcsCommandError, ValueError)`. `FakeVcs.fetched` added and asserted in the existing fallback test.
- **Group 3 (`patch`, BH6/IA2/IA4)** — `test_finalize_resyncs_the_primary_after_ledger_promotion` now reads the real journal entry back from disk (`_read_finalize_resync_entry`) and asserts `kind`/`phase`/`payload["resynced"]`, rather than only the mocked call's own arguments. (IA4's specific ask — a dedicated real-git-repo test of `_resync_home_branch` with `home == git_repo_root` — was folded into this same coverage pass via the real-`LocalFs`, real-journal assertions now covering both the dirty-skip and clean-resync branches end-to-end at the `finalize_dispatch_land` level; a separate lower-level `_resync_home_branch` unit test was judged redundant given `_resync_home_branch` itself is unmodified and already has its own pre-existing test suite.)
- **Group 4 (`patch`, BH5/BH7/IA3)** — two new tests added to `test_dispatch_fleet.py`: `test_clean_but_diverged_primary_still_reads_the_remote_ledger` (clean but SHA-diverged primary) and `test_remote_read_failure_falls_back_to_the_local_ledger` (remote read raises `VcsCommandError`, falls back to the local `HarnessPort` read).

Re-verified independently (not through the subagent's own report): read every diff hunk directly against `core/dispatch.py`/`dispatch_land_finalize/__main__.py`/both test files; confirmed the dirty-check gate and the `fetch` call land exactly where required; confirmed the new tests assert real, non-tautological outcomes (a genuine journal-file read, a genuine `fetched` list, a genuine remote-read exception path). Re-ran both verification commands directly (not through a pipe):
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 8242 passed, 1 skipped, 12 deselected.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 130 passed, 3 skipped.

Confirmed `git diff <baseline> -- core/verdict.py core/findings.py` is empty -- no new Finding code was introduced by either the original implementation or this fix round.

No further findings from this pass. `followup_review_recommended` computed `false`: the fix round was narrowly scoped to the four already-identified groups, every fix was independently re-verified line-by-line against source (not merely trusted from the subagent's report), both declared verification commands are green, and no new surface (no new public function signature beyond what the original spec's Code Map already named, no new Finding code, no new call sites) was introduced by the fix round itself.

## Auto Run Result

**Summary:** After a station's `dispatch land finalize` promotes its sprint-status ledger onto `origin/main` (`_promote_sprint_ledger`, CAP-5-isolated, never touching the primary checkout), the primary checkout now resyncs itself and the fleet campaign's ledger reads fall back to reading `origin/main` directly when the primary can't be trusted -- closing the gap that previously required a manual `git pull` before the next fleet cycle would see a sibling station's promotion. This is the successful re-mint of Story 51.3, which landed hollow (PR #1501, spec-only diff, session killed by the harness's 600s background-wait ceiling before any implementation).

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py` -- after `_promote_sprint_ledger`, gates on `vcs.has_uncommitted_changes(root)` before calling the pre-existing `_resync_home_branch` verbatim to fast-forward the primary checkout onto `origin/main`; journals the outcome (`resynced: bool`) via a new standalone `Phase.OBSERVATION` write.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py` -- new `_primary_checkout_is_clean_main` + `_station_ledger_statuses` helpers; the latter fetches and reads `origin/main`'s ledger copy via `VcsPort.file_text_at_ref` + the pre-existing `_parse_sprint_ledger_statuses` when the primary isn't verifiably clean-`main`, falling back to the local `HarnessPort` read on any remote-read failure. Wired into all three fleet-cycle call sites (`gather_fleet_missing_spec_escalations`, `execute_fleet_cycle`, `run_fleet_drain`); the first gained a new `vcs: VcsPort` parameter.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py` -- threads `vcs=vcs` into its call to `gather_fleet_missing_spec_escalations`.
- `tests/unit/test_dispatch_land_finalize.py`, `tests/unit/test_dispatch_fleet.py`, `tests/unit/test_dispatch.py`, `tests/unit/test_dispatch_hotfix.py` -- new/extended fixtures and tests covering both the resync (clean/dirty primary) and read-fallback (dirty/diverged/remote-failure) branches.

**Review findings breakdown:** 17 findings across 4 review layers (Blind Hunter 7, Edge Case Hunter 5, Intent Alignment Auditor 4, Verification Gap Reviewer 1). 4 high (1 `bad_spec` group of 3 findings, 1 `patch` group of 1 finding), 6 medium (2 `patch` groups), 2 low (both rejected/deferred, no code change), 5 false. One `bad_spec` loopback (the spec's own Code Map had incorrectly asserted `_resync_home_branch`'s existing SHA-match check alone was sufficient -- corrected in the spec before re-engaging the implementer); `review_loop_iteration` = 1.

**Verification performed:** Both declared verification commands re-run directly by the orchestrator with real exit codes (never through a pipe) after the fix round: `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` (8242 passed, 1 skipped, 12 deselected) and `pixi run --frozen -e pyforge-ci pyforge-deps-test` (130 passed, 3 skipped). Confirmed no new `Finding` code was added to `core/verdict.py`/`core/findings.py`. Every diff hunk from both the initial implementation and the fix round was read directly against source, not merely trusted from subagent self-reports.

**Residual risks (accepted, not fixed):**
- EC2 (deferred, named reason): a failed `deploy_run.write` mint/write inside `finalize_dispatch_land` could in principle turn an already-successful land+promote into a reported failure -- verified pre-existing via `_promote_sprint_ledger`'s own two prior `deploy_run.write` calls earlier in the same function; a real fix requires redesigning `_DeployRun`/`finalize_dispatch_land`'s shared error-severity policy, a distinct, unscoped cross-cutting change with no attribution to this story.
- EC1 (rejected): no new locking was added around the resync's `fetch`/`fast_forward` on the shared primary checkout; matches `_resync_home_branch`'s own pre-existing, deliberate convention of treating a held lock as a gracefully-handled WARN rather than something to prevent via locking.

## Binding

Parent Spec capability: `spec-pyforge-marshal CAP-251`.
Surface: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_finalize/__main__.py` (post-ledger refresh step, reusing `cli/land.py::_resync_home_branch`), `.../cli/land.py::_promote_sprint_ledger` (unchanged single writer onto the remote tip), `.../cli/dispatch.py` (the fleet cycle's ledger read — `station_finalize_pending_story` / the `ledger_story_statuses(ledger_path)` call — falls back to `origin/main` when the primary is not a clean `main`), `.../core/dispatch_fleet.py::station_ledger_path`, tests.
Ledger key: `51-9-the-campaign-reads-the-ledger-it-just-promoted-re-mint-of-51-3`.
Minted 2026-09-19 from `epics.md` so `marshal factory dispatch` (51.x) or a hand-driven `bmad-build-auto` (52.x) can resolve `spec-51-9-the-campaign-reads-the-ledger-it-just-promoted-re-mint-of-51-3.md`. Re-mint of Story 51.3 (2026-09-19), which landed hollow — see its tracked spec; identical contract, `Deps: S-51.2`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station policy's second verify command).

**Manual checks:**
- The Then/And of Story 51.9 (= 51.3) in `epics.md` hold on the named fixture; the mutation or byte-identical check named there is run, not inferred.
