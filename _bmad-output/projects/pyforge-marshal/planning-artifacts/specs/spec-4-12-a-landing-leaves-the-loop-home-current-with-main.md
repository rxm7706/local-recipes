---
title: 'A landing leaves the loop home current with `main`'
type: 'feature'
created: '2026-08-09'
status: done
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'b1c885caf5'
final_revision: 'f94c861494'
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `cli/land.py::run_land`'s resync step (`_run_resync_if_enabled`, gated by
`landing_resync`) refreshes the sprint feed via `cli/deploy.py::reconcile_feed`, but nothing
ever advances the loop-home's own checked-out station branch (`loop/<slug>`, at `home =
_home_path(slug)`) to match `main` after a wave merges. `home` shares the SAME `.git` as
`repo_root` (confirmed: `git worktree list` lists both together), so a GitHub-side `gh pr
merge` never updates any LOCAL ref there — `loop/<slug>` and local `main` both go stale
immediately. Measured 2026-08-09: 5 commits behind minutes after its own stories landed, 8 PRs
behind origin between runs, reported clean by every existing detector.

**Approach:** add two small `VcsPort` primitives (`fetch`, `fast_forward`) and call them from
ALL THREE of `run_land`'s outcome exits — the already-landed shortcut, the full-merge path, AND
the `if not wave_keys` "nothing new to land" no-op (CORRECTED 2026-08-09: the no-op branch is
this story's OWN primary scenario — between-runs drift — and the first draft's "both existing
call sites" silently excluded it) — gated by the SAME `landing_resync` policy toggle (no new
policy key), and applicable ONLY when `landing_merge_strategy == "merge"`: `git fetch origin <base>` then `git -C home merge --ff-only
origin/<base>` (`base` = the already-resolved `landing_base_branch`, default `"main"`). Any
failure (divergence, dirty tree, lock contention, no network) is a new WARN finding naming the
branch and git's own precise reason — never silent, never escalated, never a forced correction.

## Boundaries & Constraints

**Always:**
- Runs from ALL THREE of `run_land`'s outcome exits — the already-landed shortcut, the
  full-merge path, and the `if not wave_keys` no-op — gated by `resync_enabled`
  (`landing_resync`) exactly as `_run_resync_if_enabled` already is; `False` means no new I/O
  and no new finding, unchanged from today. **CORRECTED 2026-08-09:** the first draft said
  "both existing call sites", which excluded the no-op branch — the exact case the story names
  as primary ("a home with no live run is in scope: between-runs is exactly where drift
  accumulates unobserved").
- **Applies ONLY when `landing_merge_strategy == "merge"`.** Under `"squash"` or `"rebase"` the
  landed commits are not ancestors of `origin/<base>`, so a fast-forward is impossible **by
  construction, on every invocation, permanently** — not a transient failure worth a finding.
  In those two cases resync is SKIPPED entirely: no fetch, no merge attempt, no finding, and
  `data["home_current"]` is **absent** — byte-identical in shape to `resync_enabled=False`.
  (Operator decision 2026-08-09: a WARN that can never clear is noise, not signal.)
- Targets `origin/<base>` where `base = effective.landing_base_branch.value` (already computed
  in `run_land`) — never a hardcoded `"main"` literal (`land.py`'s existing `_MERGE_BASE_
  BRANCH_FALLBACK = "main"` constant is unused dead code; do not wire it in — use `base`).
- Uses only `git fetch` (updates `refs/remotes/origin/<base>` only) and `git merge --ff-only`
  (moves `loop/<slug>`'s pointer forward only when it is already an ancestor of the fetched
  ref) — the mechanism that makes "no live run" and "live run" both safe by construction: a run
  that kept committing to `loop/<slug>` past the landed wave makes it non-fast-forwardable, and
  `--ff-only` refuses cleanly and reports why, rather than a forced merge/reset.
- Any failure (fetch error, non-fast-forward, dirty working tree, lock contention) fires one
  new WARN finding naming `head_branch` and the underlying git error, and sets a new envelope
  field `data["home_current"] = False`. Success (fast-forwarded OR already current) sets
  `data["home_current"] = True` with no finding. `resync_enabled=False` leaves `data["home_
  current"]` absent (mirrors `resynced`'s own off-switch shape — no new key when skipped).
- `_render_text_land` gains one line reporting `home_current` when the key is present.

**Never:**
- Never pushes the fast-forwarded `loop/<slug>` to any remote — Story 3.8's existing
  stage-boundary push watcher already keeps it current with the remote during a live run; out
  of this story's scope.
- Never force-pushes, never `--no-ff`, never `rebase`, never `reset --hard` — no history
  rewrite, ever.
- Never a new policy key — reuses `landing_resync` verbatim; `landing_resync_commands` and
  `reconcile_feed`'s own root-scoped resync are untouched.
- Never depends on or duplicates Story 4.11's `is_run_live`/`FleetHomeFacts` gather — that
  story's commit (`b78bcdb746`) is not yet merged into this codebase (`cli/land.py` here still
  ends at Story 4.10; confirmed no `is_run_live`/`MRS-LAND-008` present). This story's own
  live-run safety comes entirely from git's atomic ff-only/lock semantics, not a shared
  liveness predicate — avoids inventing logic Story 4.11 will separately, and equivalently,
  already supply once it lands.
- Never escalates a resync failure to `ERROR` or blocks `land`'s own exit — the merge already
  succeeded; this is a best-effort convenience layered on top.
- **Never emits a finding for a condition that cannot change.** Under `"squash"`/`"rebase"` the
  skip is silent by design; the WARN path is reserved for failures a subsequent land could
  actually clear (divergence from a live run, dirty tree, lock contention, no network).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|-----------------|
| Home branch behind `main`, ff possible | `landing_resync=true`, `loop/<slug>` an ancestor of fetched `origin/<base>` | fetch + `merge --ff-only` succeed; `data["home_current"]=True` | No finding |
| Already current | `loop/<slug>` already equals fetched `origin/<base>` | `merge --ff-only` no-ops ("already up to date"); `data["home_current"]=True` | No finding |
| Diverged (e.g. a live run kept committing past the landed wave) | `loop/<slug>` has commits beyond `origin/<base>` | `merge --ff-only` refuses (not a fast-forward) | New WARN naming branch + reason; `data["home_current"]=False` |
| Fetch fails (no network/remote) | `git fetch origin <base>` errors | fast-forward never attempted | New WARN naming the fetch failure; `data["home_current"]=False` |
| `landing_resync=false` | policy off | no fetch/ff attempted, unchanged from today | No new key, no finding |

</intent-contract>

## Code Map

- `src/pyforge/marshal/ports/vcs.py` -- NEW Protocol methods `fetch(repo_root, remote, ref) -> None` (network) and `fast_forward(worktree_path, ref) -> str` (returns new HEAD sha; raises `VcsCommandError` on any non-ff/dirty-tree/lock failure), docstrings mirroring this module's own `push`/`merge_branch` convention.
- `src/pyforge/marshal/adapters/vcs_git.py` -- implement both: `fetch` runs `git -C repo_root fetch <remote> <ref>` under a new `_GIT_FETCH_TIMEOUT_S` (mirror `_GIT_PUSH_TIMEOUT_S=120.0`, a network op); `fast_forward` runs `git -C worktree_path merge --ff-only <ref>` under `_GIT_CHECKOUT_TIMEOUT_S` (tree-mutating, mirrors `merge_branch`'s own tier), returns `git rev-parse HEAD` afterward; both raise `VcsCommandError` with git's stderr on any non-zero exit.
- `src/pyforge/marshal/cli/land.py` -- new `_MRS_LAND_009` constant; new helper `_resync_home_branch(vcs, resync_enabled, merge_strategy, git_repo_root, home, base, head_branch, findings) -> bool | None` called immediately alongside both existing `_run_resync_if_enabled` call sites (~line 509, ~line 869); sets `data["home_current"]`; `_render_text_land` renders it when present.
- `src/pyforge/marshal/core/findings.py` -- register `MRS-LAND-009` (`REGISTERED_CODES` frozenset entry + docstring prose noting `MRS-LAND-008` is reserved by not-yet-landed Story 4.11, to avoid a code collision at landing time).
- `src/pyforge/marshal/core/verdict.py` -- classify `MRS-LAND-009` as `Verdict.WARN` in `_CLASSIFY_TABLE`.
- `tests/unit/test_vcs_git.py` -- new tests for `fetch`/`fast_forward` against real git repos, reusing the existing `remote`/`cloned_repo` bare-origin fixtures (ff success, already-current no-op, diverged-refuses, fetch-with-no-remote-raises).
- `tests/unit/test_land.py` -- extend `_FakeVcs` with configurable `fetch`/`fast_forward` fakes; new tests: ff success (`data["home_current"] is True`, no finding), diverged/non-ff failure (`MRS-LAND-009` WARN, `data["home_current"] is False`), a live-run-shaped divergence scenario (extra commits already on `loop/<slug>` beyond the landed wave -- proves this story's mechanism degrades gracefully without needing Story 4.11's liveness gate), and `landing_resync=false` (no new key, no new fake-vcs calls recorded).

## Tasks & Acceptance

**Execution:**
- [x] `ports/vcs.py` -- add `fetch`/`fast_forward` Protocol methods -- defines the new seam
- [x] `adapters/vcs_git.py` -- implement `fetch`/`fast_forward` -- the real git operations
- [x] `cli/land.py` -- add `_resync_home_branch` + wire into ALL THREE resync-relevant exits (already-landed shortcut, full-merge path, `if not wave_keys` no-op) + `data["home_current"]` + text rendering -- the feature itself
- [x] `core/findings.py` / `core/verdict.py` -- register `MRS-LAND-009` as `Verdict.WARN` -- makes the finding classify and exit correctly
- [x] `tests/unit/test_vcs_git.py` -- real-git tests for the two new primitives -- proves the ff-only/fetch mechanics in isolation
- [x] `tests/unit/test_land.py` -- ff-success, non-ff/live-run-shaped divergence, fetch-failure, `landing_merge_strategy != "merge"` skip, and `landing_resync=false` skip -- proves the I/O matrix end to end

**Acceptance Criteria:**
- Given a landing that merges a wave to `main` with `landing_resync` true, when the resync step runs, then `loop/<slug>` in the loop-home checkout is fast-forwarded to `origin/<base>` where possible, with no history rewrite and no push to any remote.
- Given the station branch cannot fast-forward (e.g. a live run committed further stories onto it after the wave was captured for landing), when the resync step runs, then `MRS-LAND-009` reports the precise git-level reason, the branch is left untouched, and `land`'s own exit CODE is unaffected by this failure (the merge itself already succeeded) -- only the reported verdict STRING moves to `warn`, per AD-7.
- Given `landing_resync` is false, when `marshal land` runs, then no fetch/fast-forward is attempted and no new envelope key or finding appears, byte-for-byte identical to today's behavior.

## Design Notes

**Why no dependency on Story 4.11's `is_run_live`.** Research confirmed Story 4.11 (`is_run_
live`, `MRS-LAND-008`, the `--retire-live-branch` flag) exists only in a sibling, not-yet-merged
worktree of this same bmad-loop run (`b78bcdb746`) -- this codebase's `cli/land.py` still ends
at Story 4.10. Duplicating that not-yet-landed predicate here would either (a) risk a genuine
finding-code collision (`MRS-LAND-008` claimed twice with different meanings) or (b) require
guessing at code this story cannot yet see. Instead, this story's safety comes from `git merge
--ff-only`'s own atomicity: a live run that has advanced `loop/<slug>` beyond the landed wave
makes the branch non-fast-forwardable, which git refuses cleanly and this story reports as a
precise WARN -- exactly the graceful degradation the epic's "must interact correctly with
S-4.11's refusal" AC asks for, achieved without a second liveness mechanism. `MRS-LAND-009` is
chosen deliberately (skipping the already-known-taken `008`) to avoid a collision once 4.11
lands.

**Why `origin/<base>`, not local `main`.** Local `main` is checked out in a SEPARATE worktree
of this same shared repo (the actual main checkout) — `git fetch` cannot update a branch ref
that is checked out elsewhere. `origin/<base>` (a remote-tracking ref, always safe to move) is
therefore both the correct fast-forward target and the one the epic's own motivating evidence
names ("8 PRs behind on **origin**").

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Spec Change Log

## Review Triage Log

### 2026-08-09 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 2 (high 2, medium 0, low 0)
- bad_spec: 0
- patch: 7 (medium 3, low 4)
- defer: 1 (low 1)
- reject: 1 (low 1)
- addressed_findings:
  - none

**Intent gaps (root cause inside `<intent-contract>` -- code reverted, HALTing for spec repair):**

- `[high]` **The Boundaries never addressed `landing_merge_strategy`.** `run_land` already reads
  a policy-selectable `merge_strategy` (`_MERGE_STRATEGIES = frozenset({"merge", "squash",
  "rebase"})`, `core/policy.py:214`, per-project configurable, default `"merge"`). `git merge
  --ff-only` only succeeds after a real `"merge"`-strategy landing, where the new base-branch
  commit's parent chain literally includes `head_branch`'s tip. Under `"squash"` (one new commit,
  no `head_branch` parent at all) or `"rebase"` (every commit recreated with new SHAs), `head_
  branch`'s tip can never be an ancestor of the new base tip -- `fast_forward` is therefore
  GUARANTEED to fail, every single landing, for 2 of the 3 valid policy values, firing
  `MRS-LAND-009` every time and never reaching `home_current: True`. This is not an edge case;
  it is the normal, permanent outcome for any project whose policy sets `landing_merge_strategy`
  to anything but `"merge"`. The spec's Boundaries need to state what should happen for
  `"squash"`/`"rebase"` -- candidates include (a) restricting this resync capability to the
  `"merge"` strategy only (`home_current` stays unattempted/`None` otherwise, mirroring the
  `resync_enabled=False` shape), or (b) a content-equivalence-based realignment reusing `VcsPort.
  is_branch_merged`'s existing squash-aware proof instead of a literal `--ff-only`, which is a
  materially different (and riskier) operation than a fast-forward. These are genuinely different
  designs with different risk profiles -- not resolvable by inference.
- `[high]` **The Boundaries said "both existing... resync call sites" but `run_land` has THREE
  wave-outcome exit branches, not two** -- confirmed at `cli/land.py:453-454`: `if not wave_keys:
  return _emit(...)` (the "clean no-op, nothing merged since the last landing" case) exits before
  either resync helper is ever reached. This is precisely the story's own named primary scenario
  ("a home with no live run is in scope: between-runs is exactly where drift accumulates
  unobserved" -- i.e. the ordinary `marshal land <slug>` invocation that finds nothing new to
  land). As implemented, a home whose station branch is already stale from an earlier cycle stays
  exactly that stale on every no-wave `land` run, even with `landing_resync` enabled. The spec
  needs to name this third call site explicitly (or state that `_resync_home_branch` belongs at a
  point common to all three exits, e.g. immediately after wave discovery / policy resolution,
  regardless of which branch is taken).

**Other findings (moot this pass per cascading order -- tallied for the record, not actioned; will
resurface after the intent-gap repair and re-implementation):**

- `[low]` `[patch]` Every new docstring/comment cites **FR-64**; Story 4.12 is actually **FR-173**
  per `epics.md:990` (FR-64 belongs to Story 2.7). Pervasive across `vcs.py`, `vcs_git.py`,
  `land.py`, `findings.py`, `verdict.py`, and both test files.
- `[medium]` `[patch]` `_FakeVcs.fetch_raises` (test_land.py) is a configurable flag with no test
  ever setting it `True` -- `_resync_home_branch`'s own fetch-failure branch is unexercised
  through `run_land`.
  `[low]` `[patch]` The "live-run" test (`test_home_current_false_models_a_live_run_committing_
  past_the_landed_wave`) exercises the identical code path as the plain-divergence test and its
  own docstring says so -- honest, but does not actually prove any interaction with a live run
  distinct from ordinary divergence; naming/framing should not overclaim the epic's "must interact
  correctly with S-4.11's refusal" AC.
- `[low]` `[reject]` Unrelated-looking bundled changes (`pyforge-doctor/pixi.toml` `mcp` dep,
  `pyforge-steward` entries in `tests/packaging/test_dependency_completeness.py`) are in fact the
  same precedent-matched, git-history-confirmed pre-existing-baseline repair Story 4.11's own
  review pass already applied in its sibling worktree, and are already disclosed in this spec's
  own Verification section -- not a real defect, just noted for completeness.
- `[medium]` `[patch]` The `pyforge-doctor/pixi.toml` edit has no accompanying `pixi.lock` update
  -- reproduced live: any pixi invocation silently re-solves and rewrites a 46-insertion/
  43-deletion `pixi.lock` diff, which would trip a `--frozen` gate for the next invocation.
- `[medium]` `[patch]` `_resync_home_branch` never reconfirms `home` is still checked out on
  `head_branch` immediately before fast-forwarding it (at either call site) -- `--ff-only`
  protects against diverged history, not against advancing the wrong branch if `home`'s checkout
  changed underneath it. `VcsPort.worktree_head_sha` (already used earlier in `run_land` for a
  different purpose) is the existing primitive to reuse for this guard.
- `[low]` `[patch]` `_resync_home_branch`'s docstring says a resync failure "never affects `land`'s
  own exit/verdict" -- `test_home_current_false_when_fast_forward_refuses_a_diverged_branch`
  itself asserts `payload["verdict"] == "warn"`. Only the exit CODE stays 0 (`Verdict.WARN` maps to
  exit 0); the verdict string does change. Reword to distinguish exit code from verdict (AD-7).
- `[low]` `[patch]` `cli/land.py`'s top-of-module docstring is now stale: still says `run_land`
  reuses "three already-shipped primitives... plus ONE new one" (Story 4.8's `merge_pr`), with no
  mention of Story 4.12's post-merge resync step or its two new `VcsPort` primitives.
- `[low]` `[defer]` No coordination/locking around mutating `home`'s working tree beyond git's own
  ref-level atomicity (`--ff-only` + index/ref locks) -- Story 4.9/AD-42 set a precedent
  (`fcntl.flock`) for serializing shared-state writes elsewhere in this package, but this story's
  own `fast_forward` is the first operation that mutates a loop-home's checked-out branch/working
  tree from OUTSIDE the live run itself. Git's own locking prevents corruption (a concurrent
  writer gets a clean lock-contention error, per this story's own Design Notes), but does not
  address a live process observing a momentarily-inconsistent working tree mid-checkout. Real
  fix (if warranted) is a broader architectural question, not a mechanical patch -- filed for
  later focused attention rather than blocking this pass.

### 2026-08-10 — Review pass 2 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 0
- patch: 2 (medium 1, low 1)
- defer: 1 (medium 1)
- reject: 11 (high 0, medium 0, low 11)
- addressed_findings:
  - `[medium]` `[patch]` **Carried forward from pass 1**, resurfaced independently by both
    reviewers this pass: `_resync_home_branch` never reconfirmed `home` was still checked out at
    `head_branch`'s own tip before fast-forwarding whatever HEAD actually was -- a `home` that had
    drifted onto a different ref (or a detached HEAD) would get THAT ref silently advanced while
    `head_branch` stayed stale, yet `home_current` would still report `True`. Fixed: added an
    identity guard (`VcsPort.worktree_head_sha(home)` vs `VcsPort.resolve_ref(git_repo_root,
    head_branch)`, the SAME pair `MRS-DEPLOY-017` already uses in the full-merge path) before any
    fetch/fast-forward is attempted; a mismatch reports the same `MRS-LAND-009` WARN shape as any
    other resync failure. New test:
    `test_resync_home_branch_skips_fast_forward_when_home_has_drifted_off_head_branch`.
  - `[low]` `[patch]` `MRS-LAND-009`'s WARN message (a) misplaced its quote --
    `f"... origin/{base!r}"` rendered as `origin/'main'` instead of `'origin/main'` -- and (b)
    always said "could not fast-forward" even when the actual failure was in `fetch` (the network
    step), misdirecting triage. Fixed: `fetch` and `fast_forward` now run in separate `try` blocks
    with their own accurately-worded WARN message; existing tests
    (`test_resync_home_branch_diverged_reports_warn_and_home_current_false`,
    `test_resync_home_branch_fetch_failure_reports_warn`) already assert message content and still
    pass unchanged.
  - Also folded in, not tied to a specific reviewer finding: fixed `cli/land.py`'s stale
    top-of-module docstring (still said "plus ONE new one" for Story 4.8's `merge_pr`, no mention
    of this story's own two new `VcsPort` primitives -- the exact pass-1 `[low][patch]` item that
    never got applied because that pass HALTed on intent_gap first) and reworded this spec's own
    second Acceptance Criterion to distinguish exit CODE (unaffected) from verdict STRING (moves to
    `warn`), matching AD-7 and the code's own (already-correct) docstring wording -- the exact
    pass-1 `[low][patch]` item for the same reason.
  - `[medium]` `[defer]` **Carried forward from pass 1**, resurfaced independently by both
    reviewers this pass (Blind Hunter + Edge Case Hunter finding #4): no coordination between this
    story's new worktree-mutating `fetch`/`fast_forward` and a live bmad-loop run beyond git's own
    ref-level atomicity. Pass 1 identified this as `[low][defer]` but never actually wrote it to
    `deferred-work.md` because that pass HALTed on an unrelated intent_gap before reaching the
    "process findings" step -- written for real now (`deferred-work.md`, Story 4.12 entry).
  - `[reject] x11`: re-litigations of deliberate, explicitly-documented intent-contract decisions
    already reasoned through in this spec's own Boundaries/Design Notes -- no `is_run_live` gate
    (Design Notes: safety comes from `--ff-only`'s own atomicity, not a shared liveness predicate,
    by design), the no-op path now performing I/O (this pass's own named PRIMARY scenario, not a
    defect), reuse of the SAME `landing_resync` toggle with no independent sub-key ("no new policy
    key" is explicit), no retry/backoff on lock contention ("never a forced correction" is
    explicit), the silent `"squash"`/`"rebase"` skip ("never emits a finding for a condition that
    cannot change" is explicit), and `fast_forward`'s `True` not distinguishing "advanced" from
    "already current" (the I/O matrix explicitly specifies both cases as `home_current=True`, no
    finding); plus findings not applicable to this codebase's actual usage -- resync coverage
    limited to the 3 outcome exits the intent-contract explicitly enumerates by name (blocked-exit
    coverage was never in scope, not a gap against this story's own stated boundary), a narrowed
    custom fetch refspec theoretically missing the remote-tracking ref update (this repo's own
    worktrees use the default clone refspec, confirmed by a real-git passing test), rev-parse
    failing immediately after a successful merge (mirrors the pre-existing, established
    `merge_branch` convention in the same file, not new), and missing tests for the already-rejected
    scope items above.

### 2026-08-10 — Review pass 3 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 0
- patch: 6 (medium 1, low 5)
- defer: 0
- reject: 4 (high 0, medium 0, low 4)
- addressed_findings:
  - `[medium]` `[patch]` The identity guard's `resolve_ref`/`worktree_head_sha` pair shared one
    `try` block, so a failure of either produced the identical WARN message and gave no signal
    which call actually raised -- inconsistent with the fetch/fast_forward pair a few lines below,
    which pass 2 deliberately split for exactly this reason. Split into two `try` blocks with
    distinct wording (mirrors the fetch/fast_forward precedent) and fixed the same quoting bug
    pass 2 fixed for the fast-forward message (`origin/{base}` was unquoted here; now `'origin/
    {base}'` consistently). New tests: `test_resync_home_branch_reports_warn_when_head_branch_
    cannot_be_resolved`, `test_resync_home_branch_reports_warn_when_home_head_sha_cannot_be_read`
    (the identity guard's exception paths had zero coverage before this pass).
  - `[low]` `[patch]` The already-landed shortcut has no `MRS-DEPLOY-017`-style identity pre-check
    of its own (unlike the full-merge path), so `_resync_home_branch`'s own guard is its ONLY
    defense against a drifted `home` -- but no test exercised a mismatch through that specific call
    site (only the matching-identity success path was covered). New test: `test_resync_home_
    branch_already_landed_reports_warn_when_home_has_drifted`. Also corrected a factually wrong
    docstring on the existing no-op-exit mismatch test, which claimed BOTH other call sites already
    ran an earlier identity check (only the full-merge path does).
  - `[low]` `[patch]` `_render_text_land`'s new `home_current` line (an explicit Task item) had zero
    test coverage -- every Story 4.12 test parses the JSON envelope via `_payload`. New test:
    `test_render_text_land_reports_home_current_line` (`format="text"`).
  - `[low]` `[patch]` This spec's own Code Map documented `_resync_home_branch`'s signature without
    the `merge_strategy` parameter the shipped function actually takes (required by the `"merge"`-
    only restriction). Corrected the Code Map entry to match the real signature.
  - `[low]` `[patch]` `_resync_home_branch`'s docstring claimed the identity guard reuses "the SAME
    pair `MRS-DEPLOY-017` already uses in the full-merge path" as if uniform across all three
    callers -- literally true only for the full-merge path; for the other two it is the ONLY
    identity check reached. Reworded to state that distinction explicitly.
  - `[low]` `[reject] x4`: the already-landed shortcut running `_resync_home_branch` unconditionally
    even after a `find_open_pr` `ForgeCommandError` (mirrors the PRE-EXISTING `_run_resync_if_
    enabled` call three lines above it, byte-for-byte the same established pattern this branch
    already followed before this story existed -- not a new defect); `fetch`'s hardcoded `"origin"`
    remote and undifferentiated failure-cause granularity (the Boundaries explicitly require only
    that the WARN name "git's own precise reason," which the carried exception message already
    does -- re-litigates a decision already made); a request for a test simulating a multi-minute
    poll window before the identity guard re-checks (the existing mismatch tests already cover the
    guard's LOGIC regardless of elapsed time; testing the narrative timing framing is disproportionate
    over-testing, not a behavior gap); the no-op exit not also calling `_run_resync_if_enabled` (the
    Boundaries explicitly state "`reconcile_feed`'s own root-scoped resync are untouched" -- out of
    scope by design, not an oversight).

## Auto Run Result

Status: `done`

**Summary.** `marshal land` now fast-forwards the loop-home's own checked-out station branch
(`loop/<slug>`) to `origin/<base>` from all three of `run_land`'s wave-outcome exits, gated on
`landing_resync` and restricted to `landing_merge_strategy == "merge"`. Implementation + review
passes 1-2 (intent-gap repair, then patch/defer/reject triage) completed in a prior session and
landed as commit `12e0a00732` -- see `## Review Triage Log` passes 1-2 for that history. This
session had two jobs.

**Job 1 -- deterministic verification repair.** The prior session's landed commit never moved
`spec-pyforge-marshal`'s own governance memlog, so `python scripts/spec_surface_check.py` (a
DIFFERENT spec's drift detector, unrelated to this story's own Verification commands) failed on
the 8 files this story's diff touches -- the identical failure mode Story 4.11's own landing hit
one session earlier. Fixed by naming the 8 paths in `spec-pyforge-marshal/.memlog.md`'s new
"Surface reconcile" section and scoped-stamping the baseline to that spec only (commit
`6fd80a0be6`). No code inside `<intent-contract>` was touched.

**Job 2 -- Review pass 3.** Per this workflow's normal step-03 -> step-04 continuation (spec
status was `in-progress`, not `done`, when this session started), ran a fresh Blind Hunter + Edge
Case Hunter pass over the full diff since `baseline_revision`. Found 0 intent_gap / 0 bad_spec; 6
low/medium patches applied (identity-guard try-block split + quoting fix mirroring pass 2's own
precedent for fetch/fast_forward, 3 new tests closing coverage gaps on the identity guard's
exception paths and the already-landed shortcut's mismatch path, a `format=text` render test, and
two spec-doc corrections: the Code Map's stale signature and an overclaiming docstring); 4 rejects
(re-litigations of already-settled Boundaries decisions or established sibling-code patterns) --
see `## Review Triage Log` pass 3 for full detail. Committed as `f94c861494`, which also
reconciles the 2 files this pass touched into `spec-pyforge-marshal`'s memlog.

**Verification performed.** `pyforge-marshal-test`: 3097 passed (was 3093 before this session's
work). `pyforge-deps-test`: 67 passed. `lint-imports`: 3 contracts kept, 0 broken.
`python scripts/spec_surface_check.py`: exit 0, `OK: every tracked file governed or allowlisted;
no drift` (only the pre-existing, unrelated `spec-factory-console` drift-presumed set remains,
informational and non-gating).

**Residual risks.** None identified beyond what pass 2's own Design Notes and the deferred-work
ledger already carry (the pre-existing `DW`-tracked lock-contention/coordination item). No
follow-up review recommended -- this pass's fixes are localized, low-consequence, and fully
covered by the new tests above.

