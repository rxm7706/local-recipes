<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-04 -->
---
title: 'Story 1.5: Single-sourced Tier-3 store via backlink'
type: 'feature'
created: '2026-07-30'
status: 'done'
baseline_revision: '4cdef281b23608a2b5071b81efcd05bc0a575d97'
final_revision: '0fe13727c3'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `marshal init` (Story 1.4) provisions the marker and `planning-artifacts` symlink but deliberately skips `_bmad-output/projects/<slug>/implementation-artifacts` (Tier-3) — the gitignored execution-artifact store bmad-loop polls for spec completion (FR-3, AD-11). Without it, every consumer inside the home sees a per-worktree, missing or forked directory instead of the one canonical copy in the main checkout — this repo's own operating memory documents hitting exactly that desync live.

**Approach:** Add a fourth reconcile-then-act step, `tier3_backlink`, to `run_init`, porting `scripts/bmad-switch`'s `ensure_tier3_backlink` into the existing `VcsPort`/`FsPort` seam: symlink the home's `_bmad-output/projects/<slug>/implementation-artifacts` to the main checkout's copy of the same repo-relative path (`repo_root`, already resolved earlier in `run_init`), creating the canonical directory if absent, refusing to replace a real non-empty local directory.

## Boundaries & Constraints

**Always:**
- The new step runs after the in-home project gate and before the existing `symlink`/`marker` steps, mirroring `ensure_tier3_backlink`'s call order in the reference script.
- Backlink target: `repo_root / "_bmad-output" / "projects" / slug / "implementation-artifacts"`, using the SAME `repo_root` `vcs.repo_common_root` already resolved — no second root-resolution call.
- Local side: `home / "_bmad-output" / "projects" / slug / "implementation-artifacts"`, written as an ABSOLUTE symlink target (unlike the relative `planning-artifacts` symlink), since the canonical directory lives outside the home's own tree.
- New `FsPort`/`LocalFs` primitives (`ensure_dir`, `remove_empty_dir`) follow the existing five methods' idiom: raise `FsError` on any I/O failure; `remove_empty_dir` returns `bool` (removed vs. left-in-place) for the ordinary "non-empty" outcome rather than raising, so the caller can distinguish a real refusal from a real failure.
- A converged backlink (matching symlink target AND the canonical directory still present) reports `skipped` with zero `FsPort` writes for this step, matching 1.4's own idempotency bar (AD-21, NFR-7).
- Register `MRS-INIT-005` in `core/findings.py`, classify it `Verdict.ERROR` in `core/verdict.py`, following the same registration ritual 1.3/1.4 used.

**Block If:** none — this ports a working local script primitive (`ensure_tier3_backlink`) into Marshal's own code; no new product decision is required.

**Never:**
- No top-level `_bmad-output/implementation-artifacts` compatibility symlink. `scripts/bmad-switch` maintains that via a SEPARATE function (`repoint_links`, shared with `planning-artifacts`), out of this story's AC/FR-3 scope — this codebase's Tier-3 vocabulary (CLAUDE.md) names the NESTED `projects/<slug>/implementation-artifacts` path, not the top-level compat link.
- No change to the existing `symlink`/`marker` steps' semantics or the marker/symlink desync guard (`MRS-INIT-003`) — those stay scoped to `planning-artifacts` exactly as 1.4 left them.
- No silent repoint-then-report-as-refusal ambiguity: a real non-empty directory is a blocking finding — return immediately, never leave partial state.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh backlink | Local Tier-3 path absent, canonical absent | Canonical dir created, absolute symlink written, `tier3_backlink: done` | n/a |
| Idempotent re-run | Symlink already matches canonical AND canonical dir still exists | Zero `FsPort` writes for this step, `tier3_backlink: skipped` | n/a |
| Self-heal | Symlink target matches canonical but canonical dir missing on disk | Canonical recreated, symlink rewritten, `tier3_backlink: done` | n/a |
| Stale empty dir | Local path is a real, empty directory (no symlink) | Directory removed, canonical ensured, symlink written, `tier3_backlink: done` | n/a |
| Real non-empty dir | Local path is a real directory containing entries | No write attempted; local directory left untouched | `MRS-INIT-005`, `Verdict.ERROR`, path named |
| Wrong-target symlink | Local path is already a symlink to a different path | Silently repointed to canonical (single correct target, no ambiguity to guard) | n/a |
| Canonical mkdir/symlink failure | `ensure_dir`/`repoint_symlink_atomic` raises `FsError` | Attempt stops immediately | `MRS-INIT-004`, `Verdict.ERROR` |

</intent-contract>

## Code Map

- `src/pyforge/marshal/ports/fs.py` -- EDIT: add `ensure_dir(path) -> None` and `remove_empty_dir(path) -> bool` to `FsPort`
- `src/pyforge/marshal/adapters/fs_local.py` -- EDIT: implement `LocalFs.ensure_dir`/`LocalFs.remove_empty_dir`, both wrapping `OSError` into `FsError` per the module's existing idiom
- `src/pyforge/marshal/cli/init.py` -- EDIT: `_STEP_NAMES` gains `"tier3_backlink"`; `run_init` gains the reconcile-then-act block described above, between the in-home project gate and the existing symlink/marker block
- `src/pyforge/marshal/core/findings.py` -- EDIT: register `MRS-INIT-005`, extend the module docstring's Story 1.4 paragraph into a Story 1.5 one
- `src/pyforge/marshal/core/verdict.py` -- EDIT: classify `MRS-INIT-005` as `Verdict.ERROR`, extend docstring
- `tests/unit/test_fs_local.py` -- EXTEND: `ensure_dir` (creates, idempotent on an existing dir, wraps failure) and `remove_empty_dir` (removes + `True` on empty, `False` + untouched on non-empty, wraps failure) cases
- `tests/unit/test_init.py` -- EXTEND: `FakeFs` gains `ensure_dir`/`remove_empty_dir` fakes (call recording + failure injection); new tests for every I/O-matrix row above, plus `test_init_finding_codes_classify_as_documented` gains `MRS-INIT-005`
- `tests/meta/test_ad11_write_boundary.py` -- EDIT: `_RecordingFs` gains `ensure_dir`; assert every write resolves under EITHER the home OR the canonical Tier-3 store (`repo_root/_bmad-output/projects/<slug>/implementation-artifacts`), AD-11's second allowed target; write counts updated for the two new backlink writes
- `tests/integration/test_init_worktree.py` -- EXTEND: assert `tier3_backlink: done`/`skipped` and that the home's Tier-3 path resolves to the repo's own canonical directory end-to-end

## Tasks & Acceptance

**Execution:**
- [x] `ports/fs.py` -- add `ensure_dir`/`remove_empty_dir` to `FsPort` -- the two primitives `run_init`'s new step needs beyond the existing five
- [x] `adapters/fs_local.py` -- implement both on `LocalFs` -- mirrors `ensure_tier3_backlink`'s `mkdir(parents=True, exist_ok=True)` / empty-dir-removal primitives
- [x] `cli/init.py` -- add the `tier3_backlink` step per the Boundaries above -- the story's actual behavior
- [x] `core/findings.py`, `core/verdict.py` -- register + classify `MRS-INIT-005`
- [x] `tests/unit/test_fs_local.py`, `test_init.py` -- cover the I/O matrix above plus idempotent re-run and self-heal
- [x] `tests/meta/test_ad11_write_boundary.py` -- extend the write-boundary guard for the second allowed root
- [x] `tests/integration/test_init_worktree.py` -- one real end-to-end backlink assertion alongside the existing worktree/symlink/marker ones

**Acceptance Criteria:**
- Given a fresh loop home where the gitignored Tier-3 target does not exist, when `marshal init <slug>` runs, then the home's `_bmad-output/projects/<slug>/implementation-artifacts` realpath equals the main checkout's canonical directory at the same repo-relative path
- Given the canonical directory does not yet exist in the main checkout, when the backlink step runs, then it is created before the symlink is written
- Given a real, non-empty directory already occupies the local Tier-3 path, when `marshal init <slug>` runs, then it refuses with `MRS-INIT-005` naming the path, leaves that directory untouched, and exits non-zero
- Given an already-converged backlink, when `marshal init <slug>` runs again, then `tier3_backlink` reports `skipped`, zero `FsPort` writes occur for that step, and exit code is 0
- Given a successful backlink, when the main checkout's own marker and top-level symlinks are inspected afterward, then they are unchanged

## Spec Change Log

## Review Triage Log

### 2026-07-30 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 2, low 3)
- defer: 3: (high 0, medium 0, low 3)
- reject: 4: (high 0, medium 0, low 4)
- addressed_findings:
  - `[low]` `[patch]` `marshal init --help`'s description text still described only the marker + planning-artifacts symlink, with no mention of the new Tier-3 backlink (every module docstring in the diff was updated for Story 1.5 except this one). Updated the `description=` string in `add_init_subparser`.
  - `[low]` `[patch]` The AD-11 write-boundary meta-test's `_RecordingFs` fake didn't implement `remove_empty_dir`, so its docstring's "fakes every one of its writes" claim was untrue for the removal half of this story's surface, and it would `AttributeError` if a future fixture pre-seeded a stale local Tier-3 directory. Added the missing fake method.
  - `[medium]` `[patch]` No test proved the spec's own fifth Acceptance Criterion ("the main checkout's own marker and top-level symlinks are unchanged"). Extended the integration test to seed a realistic pre-existing main-checkout marker + planning-artifacts symlink (a different active project) and assert both are byte-identical after both `marshal init` runs.
  - `[medium]` `[patch]` `MRS-INIT-005` — the story's headline new refusal — had no real-filesystem (integration) coverage, only `FakeFs`-backed unit tests. Added `test_init_refuses_a_real_nonempty_local_tier3_directory` against the real `GitVcs`/`LocalFs` adapters.
  - `[low]` `[patch]` The new comment in `adapters/fs_local.py::remove_empty_dir` read ambiguously (the second parenthetical could be misread as still describing the "occupied" case rather than the return-value contract). Reworded for clarity.
- deferred: a plain-file (non-directory) occupant at the local or canonical Tier-3 path falls through to generic `MRS-INIT-004` rather than a dedicated refusal (safe, just less specific); the convergence check compares raw symlink-target strings rather than resolved paths like the ported reference script; a `remove_empty_dir` success followed by a subsequent step's failure leaves the local Tier-3 path fully absent with no rollback (self-heals on retry, no data loss since the removed dir was empty). All three logged to `deferred-work.md` with full evidence.
- rejected as noise or previously-adjudicated design: `tier3_backlink` silently repointing a symlink with a foreign target (the spec's Design Notes already reason through why this differs from the marker/planning-artifacts desync guard — one unambiguous canonical target, no second signal to disagree with); a test's "blocks before any write" name reading as broader than its actual (correctly) scoped assertion; a TOCTOU window between `remove_empty_dir` and the symlink write racing a CONCURRENT process (inherited from the reference script, matches this codebase's existing TOCTOU tolerance elsewhere); the entry-count-only empty-directory check treating a `.gitkeep`-only directory as occupied (inherited from the reference script, deliberately conservative).

### 2026-07-30 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 2, low 4)
- defer: 1: (high 0, medium 1, low 0)
- reject: 4: (high 0, medium 0, low 4)
- addressed_findings:
  - `[medium]` `[patch]` `MRS-INIT-005`'s remediation message could loop the operator: "merge its contents into the canonical copy by hand, then re-run" never states the local directory must end up empty or removed (a cautious copy leaves it non-empty → identical refusal forever), and in the fresh-home variant it names a canonical directory that does not exist yet. Reworded: move contents into the canonical directory (creating it if absent), remove the then-empty local directory, re-run.
  - `[medium]` `[patch]` AC-5 says the main checkout's "top-level symlinks" (plural) but the integration test seeded and asserted only the planning-artifacts link — the top-level implementation-artifacts link, the surface this story's writes come closest to, went unchecked. Extended the seed + unchanged-assertions to both links.
  - `[low]` `[patch]` The idempotent-rerun zero-write test froze `write_calls`/`repoint_calls`/`ensure_dir_calls`/`add_worktree_calls` before the second run but not `remove_empty_dir_calls` — the new step's second write primitive, exactly what that test exists to catch regressions on. Added the freeze + assertion.
  - `[low]` `[patch]` The AD-11 meta-test's Bounds paragraph claimed more than the guard can observe: `_RecordingFs.ensure_dir` records only the leaf argument, so a real `mkdir(parents=True)` creating missing ANCESTORS above the canonical store would be structurally invisible. Documented the bound alongside the existing git-internal-bookkeeping exemption.
  - `[low]` `[patch]` `FsPort.remove_empty_dir`'s docstring enumerated missing-path and not-a-directory failures but was silent on a symlink argument (removal refuses to operate through a link → `FsError`, even for a link to an empty directory). Documented, including "callers must check for a symlink first".
  - `[low]` `[patch]` `core/findings.py`'s new docstring split the Tier-3 path literal across a line break inside the double-backtick span, breaking greps for the path and rendering a space into it. Rejoined the literal on one line.
- deferred: a home provisioned by `marshal init` alone still lacks the TOP-LEVEL `_bmad-output/implementation-artifacts` symlink that `_bmad/bmm/config.yaml` hard-codes, so config-resolving consumers see a dangling path (would fork Tier-3 on first write) and `bmad-switch --current` warns desync — the spec deliberately scoped that link out (Never + Design Notes) and no later epics story creates it (1.6 only verifies, 1.7 seeds adapter configs), so this needs a product decision (port `repoint_links`' other half in a later story, or formally narrow FR-3's "every consumer" claim). Logged to `deferred-work.md` with full evidence.
- rejected as noise or previously-adjudicated: the raw-text (unresolved) convergence comparison and the plain-file-occupant → `MRS-INIT-004` fallthrough (both re-raised by reviewers, both already in `deferred-work.md` from the first pass — nothing new added); `tier3_backlink` writing before the marker/symlink desync refusal in the compound both-desynced case (the spec's Boundaries mandate exactly this ordering, mirroring the reference script's `ensure_tier3_backlink`-before-`repoint_links`, and the foreign-target repoint it compounds with was adjudicated in the first pass — the module docstring documents the guard's narrowed scope); `test_symlink_write_failure_stops_before_marker`'s scenario shifting from fresh-provision to pre-provisioned worktree (the tested invariant — symlink failure stops before the marker write — is fully preserved; the code path is identical whether the worktree step reports done or skipped, and worktree creation is covered by many other tests).

## Design Notes

**Why the local target is an ABSOLUTE symlink, unlike `planning-artifacts`.** The `planning-artifacts` symlink (1.4) points at a sibling path inside the SAME checked-out tree (`projects/<slug>/planning-artifacts`, relative), because that content is git-tracked and present in every checkout. The Tier-3 directory is gitignored by design (CLAUDE.md: "nothing there may be git-tracked") and therefore only ever exists as a real, local, untracked directory in exactly one place — the main checkout. A relative target from inside a linked worktree cannot reach it; the backlink must be an absolute path to the main checkout's own copy, exactly as `scripts/bmad-switch::ensure_tier3_backlink` already does.

**Why `remove_empty_dir` returns `bool` instead of raising on non-empty.** `run_init`'s other `FsError` catches all mean "a real operation failed, blocking, `MRS-INIT-004`." A non-empty local directory is not a failure — it is the safe, intended refusal `MRS-INIT-005` names specifically (mirrors this repo's own live incident: a BMAD write-skill populated the local Tier-3 path before the backlink existed, blocking `bmad-switch` from establishing it later). Collapsing the two into one exception type would force the caller to string-match a message to tell them apart; a `bool` return keeps the distinction structural.

**Why no top-level `implementation-artifacts` compatibility symlink.** `scripts/bmad-switch` maintains that link via a separate function (`repoint_links`, shared with `planning-artifacts`), not `ensure_tier3_backlink`. This story's own title, AC, and 1.4's explicit forward-reference ("Tier-3 backlink ... is Story 1.5's `ensure_tier3_backlink` surface") name the narrower nested backlink only; the top-level compatibility link stays out of scope.

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pyforge-marshal-test` -- expected: all unit + meta tests pass
- `pixi run -e pyforge-marshal pyforge-marshal-test-slow` -- expected: the extended integration test passes against a real throwaway repo
- `pixi run -e pyforge-marshal marshal init <existing-project-slug>` run twice in a scratch clone -- expected: second run reports `tier3_backlink: skipped` alongside the existing three steps, exit 0

## Auto Run Result

Status: done (follow-up review pass on an already-`done` spec; two adversarial/edge-case reviewers re-ran against the full `4cdef281b2..HEAD` diff).

**Summary:** No intent gaps, no spec defects, no behavior-logic changes required. Six findings patched (2 medium, 4 low) — all message-wording, test-coverage, and docstring-fidelity fixes; one new finding deferred to the ledger; four rejected (two were duplicates of entries already deferred in the first pass, two re-trod spec-adjudicated design).

**Files changed this pass** (commit `0fe13727c3`):
- `src/pyforge/marshal/cli/init.py` — reworded the `MRS-INIT-005` refusal message so the remediation cannot loop the operator (state the local dir must end up empty/removed; canonical may need creating)
- `src/pyforge/marshal/core/findings.py` — rejoined the Tier-3 path literal split across a docstring line break
- `src/pyforge/marshal/ports/fs.py` — documented `remove_empty_dir`'s symlink-argument behavior
- `tests/meta/test_ad11_write_boundary.py` — Bounds paragraph now states the `ensure_dir` leaf-only observability limit
- `tests/unit/test_init.py` — idempotent-rerun test also freezes `remove_empty_dir_calls`
- `tests/integration/test_init_worktree.py` — AC-5 check now seeds + asserts BOTH main-checkout top-level symlinks (implementation-artifacts included)

**Review breakdown:** patch 6 (medium 2, low 4) — all applied; defer 1 (medium) — the missing TOP-LEVEL `_bmad-output/implementation-artifacts` home symlink that `_bmad/bmm/config.yaml` resolves (product decision needed; logged to `deferred-work.md` as a NEW entry per orchestrator instruction); reject 4 (two prior-pass ledger duplicates, one spec-mandated ordering re-raise, one consequence-free test-scenario narrowing).

**Verification:** `pixi run -e pyforge-marshal pyforge-marshal-test` → 549 passed; `pixi run -e pyforge-marshal pyforge-marshal-test-slow` → 2 passed (both after patches).

**Follow-up review recommendation:** false — all six patches are localized doc/test/message fixes with no logic change; the only `src/` behavior delta is an error-message string.

**Residual risks:** the deferred top-level-symlink gap means a marshal-only home is not yet fully BMAD-write-ready without a subsequent in-home `bmad-switch` (today's documented operational step); the previously-deferred raw-text convergence comparison and plain-file fallthrough remain open in the ledger.

