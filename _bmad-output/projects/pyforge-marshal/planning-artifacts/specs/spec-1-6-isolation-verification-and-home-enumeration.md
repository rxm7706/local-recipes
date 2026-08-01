<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-04 -->
---
title: 'Story 1.6: Isolation verification and home enumeration'
type: 'feature'
created: '2026-07-30'
status: 'done'
baseline_revision: '66a4cb700c5f37be2a9d958ee232673341554d86'
final_revision: 'b0106d6961a074a9a6dc04201b402a092aa756c0'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `marshal init` (1.4/1.5) provisions and self-heals ONE home at a time; nothing lets the operator prove, across every home already provisioned, that homes stay isolated from each other and from the main checkout (FR-4), or lists them at all (FR-8). A known blind spot compounds this: `init`'s own desync guard (`MRS-INIT-003`) only compares a home's marker against its own symlink, never against the slug the home is actually keyed by, so a home whose marker and symlink consistently agree on the WRONG project would pass silently today.

**Approach:** A new read-only `marshal homes` command auto-discovers every `loop/<slug>` worktree via a new `VcsPort.list_worktrees`, gathers each home's (and the main checkout's own) marker/symlink/Tier-3-backlink state via `FsPort` (gaining `resolve_path` for realpath comparison), and hands that plain data to a new pure `core/status.py` module that classifies isolation findings and builds one table row per home. Ports `cli/init.py`'s existing marker/symlink/Tier-3 comparison logic rather than reinventing it, but strengthens it two ways: realpath (not raw-string) Tier-3 comparison, and a three-way slug check (marker vs. symlink vs. the home's own branch-derived slug) that closes the `MRS-INIT-003` blind spot named above.

## Boundaries & Constraints

**Always:**
- Home discovery is fully automatic: `marshal homes` takes no slug arguments. It lists every worktree `GitVcs.list_worktrees` returns whose branch matches `loop/<slug>`, deriving each home's identity slug from ITS OWN branch name, never from its marker or symlink content.
- `core/status.py` is pure (AD-4): no I/O, subprocess, clock, env, or `adapters` import. All raw facts (worktree list, marker text, raw + resolved symlink targets, `is_dir` checks) are gathered at the `cli/init.py` CLI boundary first, then passed to `core/status.py` as plain data.
- Per home: marker slug, symlink slug (via the existing `_slug_from_symlink_target` shape check), and the branch-derived slug must all agree (extends `MRS-INIT-003`'s two-way check to three-way — the change from deferred-work is scoped to this NEW command only; `cli/init.py`'s own `MRS-INIT-003` check is untouched). Tier-3 isolation is checked by realpath (`FsPort.resolve_path`), not raw target string, closing the gap `tier3_backlink`'s own convergence check still has (that gap stays open in `init` itself — out of scope here).
- The main checkout (the `list_worktrees` entry whose branch is NOT `loop/*`) is checked with the SAME two-way marker/symlink consistency rule applied to homes; "untouched" means self-consistent at invocation time — there is no stored baseline to diff against.
- One violation anywhere in the set is a non-zero exit; the finding names the specific home (or the main checkout) and the specific mismatch. A home with no marker/symlink/backlink at all (never `marshal init`-provisioned) is reported with null fields, not a violation.
- Output is one full envelope (AD-14): `data.homes` = one row per home (`path`, `branch`, `slug`, `active_project`, `desynced`), `data.main_checkout` = the same shape for the main checkout, `findings` names every violation. `--format text` renders the same data as a table (mirrors `cli/init.py::_render_text`).
- Zero filesystem/git writes for this command — proven by a meta-test extending `tests/meta/test_ad11_write_boundary.py`'s recording-fake pattern to assert empty write lists.
- Register `MRS-HOMES-001` (marker/symlink/branch-slug three-way mismatch, home or main checkout), `MRS-HOMES-002` (Tier-3 backlink realpath mismatch), `MRS-HOMES-003` (a git/filesystem operation failed while gathering state); classify all `Verdict.ERROR`, following `MRS-INIT-003/004/005`'s precedent (a real check ran and found a real violation or could not complete).

**Block If:** none — every comparison here ports already-adjudicated 1.4/1.5 logic or closes a deferred-work gap already scoped to this story; no new product decision is required.

**Never:**
- No remediation. `marshal homes` never writes a marker, symlink, or Tier-3 backlink, and never suggests running `marshal init` to fix a violation beyond naming it — that stays the operator's/`init`'s job.
- No change to `cli/init.py`'s own `MRS-INIT-003` two-way check, `tier3_backlink`'s raw-string convergence comparison, or the `add_worktree`/`worktree_path_for_branch` TOCTOU race — all three are separately deferred, and this read-only command cannot fix a write-side race by construction.
- No top-level `_bmad-output/implementation-artifacts` compatibility-symlink check or creation — explicitly out of scope per Story 1.5's own deferred-work entry, which reserves that decision for a later story.
- No selection flags (by slug, by glob) in this story — full enumeration only, matching FR-8's "list all loop homes" and keeping the surface minimal for an `S`-effort story.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Two clean homes | 2 `loop/*` worktrees, each fully converged (marker=symlink=branch slug, Tier-3 realpath matches canonical), main checkout self-consistent | Exit 0, 2 rows + main-checkout entry, `desynced: false` everywhere, zero findings | n/a |
| Home marker/symlink desync | One home's marker names a different slug than its symlink | Exit non-zero, `MRS-HOMES-001` naming that home's path and both slugs, that row's `desynced: true` | n/a |
| Home agrees with itself but not its branch | Marker and symlink both name slug `foo`, but the worktree's branch is `loop/bar` | Exit non-zero, `MRS-HOMES-001` naming the branch/marker mismatch (closes the deferred three-way gap) | n/a |
| Tier-3 realpath mismatch | Home's local Tier-3 symlink resolves to a directory other than the canonical `repo_root/_bmad-output/projects/<slug>/implementation-artifacts` | Exit non-zero, `MRS-HOMES-002` naming the home and both realpaths | n/a |
| Main checkout desynced | Main checkout's own marker/symlink disagree | Exit non-zero, `MRS-HOMES-001` naming the main checkout | n/a |
| Unprovisioned home | A `loop/<slug>` worktree exists with no marker file and no symlink | Exit 0 for that row (absent both is not a mismatch), `active_project: null`, `desynced: false` | n/a |
| Zero or one home | No `loop/*` worktrees, or exactly one | Exit 0, `data.homes` empty or single-element list, main checkout still reported | n/a |
| Repo/FS read failure | `git worktree list` or any `FsPort` read raises | Exit non-zero, `MRS-HOMES-003` naming the failed operation, no partial table | Command halts, no partial `data.homes` |

</intent-contract>

## Code Map

- `src/pyforge/marshal/ports/vcs.py` -- EDIT: add `list_worktrees(repo_root) -> tuple[WorktreeEntry, ...]` to `VcsPort`, plus a small frozen `WorktreeEntry(path: Path, branch: str | None)` value type (branch `None` for a detached-HEAD worktree)
- `src/pyforge/marshal/adapters/vcs_git.py` -- EDIT: implement `GitVcs.list_worktrees` by generalizing `worktree_path_for_branch`'s existing `git worktree list --porcelain` block parser to return every block instead of the first match
- `src/pyforge/marshal/ports/fs.py` -- EDIT: add `resolve_path(path) -> Path` to `FsPort` (best-effort full realpath resolution, non-strict -- must not raise for a target that doesn't fully exist, since a broken backlink is exactly a violation this command needs to name)
- `src/pyforge/marshal/adapters/fs_local.py` -- EDIT: implement `LocalFs.resolve_path` as `path.resolve()`
- `src/pyforge/marshal/core/findings.py` -- EDIT: register `MRS-HOMES-001/002/003`, extend the module docstring
- `src/pyforge/marshal/core/verdict.py` -- EDIT: classify the three new codes `Verdict.ERROR`, extend the module docstring
- `src/pyforge/marshal/core/status.py` -- NEW, pure (AD-4): given the gathered facts for every discovered home plus the main checkout, compute the three-way slug check, the Tier-3 realpath check, and the main-checkout self-consistency check; return the `data.homes`/`data.main_checkout` rows and the `Finding` list
- `src/pyforge/marshal/cli/init.py` -- EDIT: add `add_homes_subparser`/`run_homes` (mirrors `add_init_subparser`/`run_init`'s DI-seam and envelope shape) -- gathers raw facts via `VcsPort`/`FsPort`, calls `core.status`, builds and prints the envelope; extend the module docstring's registry paragraph for Story 1.6
- `src/pyforge/marshal/cli/main.py` -- EDIT: wire `init_cli.add_homes_subparser(subparsers)` alongside the existing `init` registration
- `tests/unit/test_vcs_git.py` -- EXTEND: `list_worktrees` against a real multi-worktree temp repo (0, 1, 2+ `loop/*` worktrees, plus the main checkout's own entry, plus a detached-HEAD worktree)
- `tests/unit/test_fs_local.py` -- EXTEND: `resolve_path` (resolves a real symlink chain, tolerates a broken/dangling target, matches on a plain non-symlink path)
- `tests/unit/test_status.py` -- NEW: pure unit tests for `core/status.py` covering every I/O-matrix row above via plain fact objects (no `FakeFs`/`FakeVcs` needed -- the module takes no ports)
- `tests/unit/test_init.py` -- EXTEND: `FakeVcs` gains a multi-worktree fixture (`list_worktrees`), `FakeFs` reused as-is plus a `resolve_path` fake; CLI-layer tests for `run_homes` driving the full envelope/exit-code path; `test_init_finding_codes_classify_as_documented`-style coverage gains the three new codes
- `tests/meta/test_ad11_write_boundary.py` -- EXTEND: assert `run_homes` produces zero recorded writes on both `_RecordingVcs`/`_RecordingFs`
- `tests/integration/test_init_worktree.py` -- EXTEND: a real two-worktree scenario (`marshal init` twice against two slugs in one temp repo) driving `marshal homes` end-to-end for both the clean exit-0 case and one injected desync

## Tasks & Acceptance

**Execution:**
- [x] `ports/vcs.py` -- add `WorktreeEntry` + `list_worktrees` to `VcsPort` -- the enumeration primitive FR-8 needs beyond single-branch lookup
- [x] `adapters/vcs_git.py` -- implement `GitVcs.list_worktrees` -- generalizes the existing porcelain parser
- [x] `ports/fs.py`, `adapters/fs_local.py` -- add `resolve_path` -- the realpath primitive FR-4's Tier-3 check needs
- [x] `core/findings.py`, `core/verdict.py` -- register + classify `MRS-HOMES-001/002/003`
- [x] `core/status.py` -- new pure module implementing the three isolation checks + row/finding construction
- [x] `cli/init.py` -- add `add_homes_subparser`/`run_homes` per the Boundaries above
- [x] `cli/main.py` -- wire the new subparser
- [x] `tests/unit/test_vcs_git.py`, `test_fs_local.py` -- cover the two new port primitives
- [x] `tests/unit/test_status.py` -- cover the I/O matrix above at the pure-logic layer
- [x] `tests/unit/test_init.py` -- cover the same matrix at the CLI/envelope layer
- [x] `tests/meta/test_ad11_write_boundary.py` -- extend the zero-write guard for `run_homes`
- [x] `tests/integration/test_init_worktree.py` -- one real two-worktree end-to-end assertion

**Acceptance Criteria:**
- Given two or more provisioned loop homes with independent markers/symlinks, identical (by realpath) Tier-3 backlinks, and a self-consistent main checkout, when `marshal homes` runs, then it exits 0 and `data.homes` lists one row per home
- Given any home's marker, symlink, or branch-derived slug disagrees with the other two, when `marshal homes` runs, then it exits non-zero with `MRS-HOMES-001` naming that home and the disagreeing values
- Given a home's Tier-3 local backlink resolves (by realpath) to a directory other than its expected canonical directory, when `marshal homes` runs, then it exits non-zero with `MRS-HOMES-002` naming that home
- Given the main checkout's own marker and planning-artifacts symlink disagree, when `marshal homes` runs, then it exits non-zero with `MRS-HOMES-001` naming the main checkout
- Given zero or one `loop/*` worktree exists, when `marshal homes` runs, then it exits 0 with `data.homes` containing that many rows (never an error for having too few homes)
- Given any invocation of `marshal homes`, when it completes, then neither `VcsPort` nor `FsPort` recorded a single write call

## Spec Change Log

## Review Triage Log

### 2026-07-31 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 1, medium 2, low 4)
- defer: 0
- reject: 10
- addressed_findings:
  - `[high]` `[patch]` A real (non-symlink) directory or file occupying a home's — or the main checkout's — `planning-artifacts` path was read as `symlink_target=None` and treated as benign absence, so the exact hand-configuration state the two-way/three-way rule exists to name reported clean. Same defect class the 2026-07-30 pass fixed for Tier-3, left open for the OTHER symlink the command checks. Added `FsPort.exists` (occupancy probe `is_dir` can't provide — it misses regular files), a `link_occupied` fact on `HomeFacts`/`MainCheckoutFacts` gathered as `symlink_target is None and fs.exists(link_path)`, and an occupied-link branch in `_mismatch_reason` that reports before any value comparison (mirrors the existing unrecognized-shape precedence). Surfaces as `MRS-HOMES-001`. Tests: `test_occupied_planning_artifacts_is_a_violation`, `test_main_checkout_occupied_planning_artifacts_is_a_violation` (pure), `test_homes_reports_a_real_directory_at_planning_artifacts`, `test_homes_reports_a_real_directory_at_main_checkout_planning_artifacts` (CLI), plus four `LocalFs.exists` adapter tests.
  - `[medium]` `[patch]` A regular FILE at the local Tier-3 path was still read as "never provisioned" — the 2026-07-30 occupancy fix probed `is_dir` only, covering directories but not files, so Tier-3 remained not provably single-sourced. Switched the occupancy probe to `fs.exists` (the file resolves to itself and fails the ordinary realpath comparison → `MRS-HOMES-002`). Test: `test_homes_reports_a_plain_file_occupying_tier3`.
  - `[medium]` `[patch]` A Tier-3 backlink dangling AT the correct canonical path (store deleted after provisioning) resolved equal and was blessed clean, though every write through it would fail and `marshal init`'s own convergence check (`fs.is_dir(canonical)`) has never accepted that state. Gathered `tier3_canonical_is_dir` and extended `_tier3_mismatch_reason` to name it as `MRS-HOMES-002` ("dangling backlink") when a backlink exists; absence of both stays benign. This also makes `ports/fs.py::resolve_path`'s "a broken/dangling backlink is exactly the violation this check needs to name" claim fully true. Tests: `test_backlink_dangling_at_the_canonical_path_is_a_violation`, `test_missing_canonical_store_without_a_backlink_is_not_a_violation` (pure), `test_homes_reports_a_backlink_dangling_at_the_canonical_path` (CLI).
  - `[low]` `[patch]` `_mismatch_reason` returned only the FIRST disagreement, so the all-three-disagree case never named the branch value — shortfalling the AC's "naming ... the disagreeing values" in exactly the multi-corruption case. Now collects and joins every disagreeing pair (existing message texts preserved as substrings). Test: `test_all_three_slugs_disagreeing_names_every_pair`.
  - `[low]` `[patch]` `test_homes_takes_no_slug_argument` was vacuous — it asserted a property of the test file's own namespace helper, which could never fail regardless of what `add_homes_subparser` does. Replaced with `test_homes_parser_rejects_a_positional_argument`, which drives the REAL parser via `cli.main.main(["homes", "stray-slug"])` and asserts the argparse rejection (exit 2).
  - `[low]` `[patch]` The discovery filter's exclusion branches (detached-HEAD `branch=None` — the filter's own None guard — and non-`loop/*` linked worktrees) had zero CLI-layer coverage. `FakeVcs` gained `extra_worktree_entries`; added `test_homes_excludes_detached_head_and_non_loop_worktrees`.
  - `[low]` `[patch]` `_iter_worktree_blocks`'s docstring claimed the `detached`→`"true"` normalization lets `list_worktrees` distinguish a detached-HEAD block — `list_worktrees` never reads that key (it derives `branch=None` purely from the absent `branch` line). Reworded to state the actual behavior and keep the normalization honest as "preserved for callers", not consumed today.
- deferred: none.
- rejected as noise, unrealistic, spec-mandated, or previously adjudicated: the all-or-nothing `FsError` abort hiding sibling homes plus `MRS-HOMES-003` carrying both a no-table shape (read failure) and a partial-table shape (phantom worktree) — the abort is the spec matrix's own "no partial table" row, the phantom case is not a "read raises", and the spec fixes the code set at exactly three; the main checkout sitting on a `loop/<slug>` branch being checked only two-way (unreachable via the toolchain, and the branch is visible in the emitted row); the helper-duplication direction argument plus the sample-based drift guard's non-exhaustiveness (design adjudicated by the spec's Boundaries and the prior pass; an `inspect.getsource` comparison would false-fail on the copies' deliberately different docstrings); no loop-home-root location check for discovered homes (out of the spec's stated FR-8 scope — checks are branch-keyed, and the row prints the path); the TOCTOU window between the phantom-worktree guard and the fact reads (inherent to any non-atomic filesystem scan; a read-only report self-corrects on the next run — same reasoning as the spec's Never on the `add_worktree` race); a hand-crafted nested `loop/a/b` branch yielding a multi-segment slug (never minted by the toolchain, and the failure mode is a NOISY over-report, not a silent clean); the type-narrowing `assert entry.branch is not None` under `python -O` (the invariant is enforced by the filter three lines above; failure requires a future refactor AND -O); the early-abort text output printing the `homes:` header with empty data and omitting `repo_root` from `data` (cosmetic; the envelope shape is spec-fixed and findings name the failed operation); `_emit_homes` being a third near-copy of the emit machinery (DRY nit, same family the prior pass rejected twice); `_iter_worktree_blocks` mis-parsing a worktree path containing an embedded newline absent `--porcelain -z` (legal-but-exotic; loop paths are minted from validated slugs, and the failure mode is a spurious finding, not a silent clean).

### 2026-07-30 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 1, medium 2, low 1)
- defer: 0
- reject: 8
- addressed_findings:
  - `[high]` `[patch]` A real, non-symlink directory occupying a home's local Tier-3 path (e.g. left behind by `init`'s own `MRS-INIT-005` refusal) was read as `tier3_local_realpath=None` and silently reported as "never provisioned" rather than as the Tier-3 single-sourcing violation it actually is — exactly the class of divergence FR-4's Tier-3 check exists to catch. Fixed `_gather_home_facts` to also resolve when `fs.is_dir(tier3_local_path)` is true (not only when it's a symlink); the resolved self-path then fails the ordinary realpath comparison and surfaces as `MRS-HOMES-002`. Added `test_homes_reports_a_real_non_symlink_tier3_occupant`.
  - `[medium]` `[patch]` A `loop/<slug>` worktree git still registers but whose directory was deleted by hand (a stale/prunable entry — `run_init` already guards this exact known failure mode) was read as all-`None` facts and reported as a clean, unprovisioned home instead of being flagged. Added an `fs.is_dir(entry.path)` guard in `run_homes`'s gathering loop, mirroring `run_init`'s own message; the entry is excluded from `data.homes` and named via a new `MRS-HOMES-003` finding instead. Added `test_homes_reports_a_phantom_prunable_worktree`; fixed five pre-existing `FakeFs`-backed tests (`_seed_clean_home` and four callers) plus the AD-11 meta-test's `_RecordingFs` fixture to seed the home directory's existence, since none previously modeled it and would otherwise now trip this guard.
  - `[medium]` `[patch]` `FsPort.resolve_path`'s docstring claimed it "raises `FsError` for a genuine I/O failure ... e.g. a symlink loop, a permission error" — confirmed live (`Path.resolve(strict=False)` swallows both and returns a best-effort path instead of raising) that this is false, making the `except OSError` branch dead code for both scenarios. Reworded the docstring to state the actual behavior and why a divergence is still caught downstream as a realpath-mismatch finding rather than an op-failure finding.
  - `[low]` `[patch]` The core/cli slug-parsing duplication (`_slug_from_marker`/`_slug_from_symlink_target`, intentionally duplicated per the module docstring's core/cli layering rule) had no test proving the two copies stay behaviorally identical. Added `test_slug_from_marker_matches_cli_init_copy`/`test_slug_from_symlink_target_matches_cli_init_copy` as a drift guard.
- deferred: none — the remaining findings below were rejected as noise, unrealistic given the codebase's own invariants, or already covered by the spec's explicit scoping.
- rejected as noise, unrealistic, or already spec-scoped: the `"loop/"` branch-prefix literal appearing independently in three call sites (cosmetic DRY nit, no correctness risk, all three exercised by tests); a synthetically-constructed empty-slug `"loop/"` branch name collapsing the Tier-3 path (unreachable via any path `marshal init`'s own slug validation permits — requires hand-crafting a malformed branch); non-`loop/*`/non-main worktrees (detached HEAD, hand-made linked worktrees) being silently excluded from `data.homes` (the spec's own Boundaries explicitly scope enumeration to `loop/<slug>` branches only — this is FR-8's stated scope, not a gap); a redundant `dict(row)` re-wrap in `_emit_homes` given rows are already dicts and `Envelope` deep-copies regardless (pure style, zero functional impact); inconsistent `io.StringIO`-swap vs. `capsys` capture style across new tests in the same file (test-only, zero production impact); the `data.homes`/`data.main_checkout` row shape having no formally versioned schema ahead of a not-yet-planned future Fleet Visibility story (speculative, out of this `S`-effort story's scope per its own Never section); a duplicated error-message string between `list_worktrees` and `worktree_path_for_branch`'s otherwise-shared `_run` call (cosmetic DRY nit, both paths already tested); two `git worktree list` entries both resolving to the same realpath as `repo_root` (unreachable — git's own worktree registration refuses two worktrees at one path).

## Design Notes

**Why `homes` lives in `cli/init.py`, not a new `cli/status.py`.** The architecture's own Traceability Matrix maps "Loop homes & isolation (FR-1..FR-8)" to component `cli/init` specifically; `cli/status` is reserved for the LATER, broader "Fleet visibility (FR-36..FR-40)" row (fleet-state derivation + ledger-vs-git reconciliation, AD-33) -- a different epic's concern. `core/status.py` is created now scoped to this story's "homes view" only, per the epic's own surface note, and is expected to grow a second view under that later story without this one needing to anticipate its shape.

**Why the three-way slug check is new command scope, not a `cli/init.py` change.** Deferred-work explicitly named this exact gap and explicitly named Story 1.6 as its likely home ("Needs a product decision on whether a third cross-check ... belongs to this story or to Story 1.6"). Widening `init`'s OWN `MRS-INIT-003` would change `marshal init`'s reconcile-then-act behavior (a converged-looking home might newly fail preflight), which is a different risk profile than a read-only report naming the same condition. Keeping the stronger check exclusively in the new read-only `homes` command gets the detection FR-4 requires without touching `init`'s idempotency contract.

**Why "main checkout untouched" is self-consistency, not a diff.** There is no stored pre-run snapshot for a live CLI invocation to compare against (Story 1.5's own AC-5 proved this property only inside a single test's before/after, not as a runtime capability). Applying the same marker-vs-symlink agreement rule Marshal already uses for homes to the main checkout's own marker/symlink pair is the checkable proxy: if nothing has repointed the main checkout's own links, they still agree with each other, which is exactly the invariant `AD-11` exists to protect.

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pyforge-marshal-test` -- expected: all unit + meta tests pass
- `pixi run -e pyforge-marshal pyforge-marshal-test-slow` -- expected: the new integration test passes against two real throwaway worktrees
- `pixi run -e pyforge-marshal marshal homes --format json` run against a scratch clone with 2+ provisioned homes -- expected: one row per home, `desynced: false`, exit 0

## Auto Run Result

**Status:** done (follow-up review pass, 2026-07-31 — routed here by `status: in-review`; the 2026-07-30 pass had recommended an independent follow-up).

**Summary of implemented change (this pass).** Two fresh reviewers (Blind Hunter, Edge Case Hunter) ran against the full baseline→HEAD diff; 22 raw findings deduplicated to 17. Seven were patched, ten rejected, none deferred (the deferred-work ledger was not touched). The load-bearing patches close three silent-clean detection blind spots in the very checks FR-4 exists for: (1) a real (non-symlink) directory or file occupying the `planning-artifacts` path of a home **or the main checkout** now surfaces as `MRS-HOMES-001` instead of reading as benign absence — the same defect class the first pass fixed for Tier-3, left open on the other symlink; (2) a plain file occupying the local Tier-3 path now fails the realpath comparison (`MRS-HOMES-002`) instead of reading as "never provisioned"; (3) a Tier-3 backlink dangling at the *correct* canonical path (store deleted after provisioning) is now named (`MRS-HOMES-002` "dangling backlink"), porting `marshal init`'s own `is_dir(canonical)` convergence condition. Supporting fixes: mismatch findings now name every disagreeing pair; the vacuous no-slug test now drives the real parser; the discovery filter's exclusion branches gained CLI-layer coverage; one adapter docstring overclaim corrected.

**Files changed (commit `b0106d69`):**
- `ports/fs.py` — new `exists` occupancy primitive (+docstrings)
- `adapters/fs_local.py` — `LocalFs.exists` (suppress-OSError-to-False, mirrors `is_dir`)
- `cli/init.py` — `_gather_home_facts`/`_gather_main_checkout_facts` gather `link_occupied` + `tier3_canonical_is_dir`; Tier-3 occupancy probe widened from `is_dir` to `exists`
- `core/status.py` — `HomeFacts`/`MainCheckoutFacts` new fields; `_mismatch_reason` occupied-link branch + multi-reason reporting; `_tier3_mismatch_reason` dangling-at-canonical case
- `adapters/vcs_git.py` — `_iter_worktree_blocks` docstring corrected
- `tests/unit/test_init.py` — `FakeFs.exists`, `FakeVcs.extra_worktree_entries`, canonical-store seeding in fixtures, 5 new + 1 replaced CLI-layer tests
- `tests/unit/test_status.py` — helper params for the new facts, 5 new pure tests
- `tests/unit/test_fs_local.py` — 4 `exists` adapter tests
- `tests/meta/test_ad11_write_boundary.py` — `_RecordingFs.exists` (read, never recorded; zero-write guard still passes)

**Review findings breakdown:** patch 7 (high 1, medium 2, low 4) — all fixed; defer 0; reject 10 (full rationale in the 2026-07-31 triage-log entry above).

**Follow-up review recommendation: true.** This pass's fixes are behavior-affecting (three new flagged violation states, a new port method, new fact fields) and include a high-severity detection change spanning core + cli + ports + adapters — comparable in significance to the first pass, which merited this one.

**Verification performed:** `pixi run -e pyforge-marshal pyforge-marshal-test` → 614 passed, 3 deselected; `pixi run -e pyforge-marshal pyforge-marshal-test-slow` → 3 passed (real two-worktree end-to-end unchanged and green). The live-scratch-clone smoke command was not re-run this pass (no change to discovery or envelope shape; the integration test covers the real-git path).

**Residual risks:** the strengthened occupancy rule means a repo whose `_bmad-output/planning-artifacts` is a REAL directory (vanilla single-project BMAD layout, never `bmad-switch`-converted) now exits non-zero from `marshal homes` — correct for this factory's convention (marshal's own provisioning always maintains symlinks) but stricter than before; the rejected findings (all-or-nothing abort on one unreadable home, `MRS-HOMES-003`'s two envelope shapes, TOCTOU window, `_emit` triplication) remain as designed/spec-mandated and are documented in the triage log for any future story that revisits them.

