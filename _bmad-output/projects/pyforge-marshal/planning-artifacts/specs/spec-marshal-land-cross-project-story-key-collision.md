---
title: 'GitHub PR-merge branches are scoped to project_slug before being trusted as a story key'
type: 'bugfix'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `core/promotion.py::extract_story_key_from_github_merge_subject` extracts a `StoryKey` from any GitHub PR-merge branch's final path segment with no check that the branch belongs to the project being queried. Reproduced live: `marshal land pyforge-mason` reported story `4.2` as `already_landed`/`merged: true` because PR #274's branch `marshal/4-2-teardown-reachability-spec-recovery` — a **marshal** story — parsed as mason's own `4.2`. Its sibling `extract_story_key_from_bmadloop_merge_subject` already scopes itself to `project_slug` for the identical reason; this pattern never got the same treatment. Known, previously-deferred gap (`implementation-artifacts/deferred-work.md`, 2026-08-10, review passes 2+4) — this is its first concrete, consequential failure.

**Approach:** Add a `project_slug: str` parameter to `extract_story_key_from_github_merge_subject`, matching the bmad-loop sibling's signature. Widen `_GITHUB_MERGE_SUBJECT_RE`'s owner capture from greedy (`\S+`) to non-greedy (`\S+?`) so the `branch` group retains the FULL path after the GitHub owner segment (e.g. `marshal/4-2-teardown-...`, not just `4-2-teardown-...`) instead of only the final segment. Before parsing a key, require `branch` to start with `f"{project_slug.removeprefix('pyforge-')}/"` — the real, observed convention (`marshal/<epic>-<seq>-<desc>`) — else return `None`. Thread `project_slug` through the one call site (`_classify_merge_subject`).

## Boundaries & Constraints

**Always:**
- The existing key-extraction logic (`segment = branch.rsplit("/", 1)[-1]`, then `normalize(segment)`) stays byte-identical — only an upstream project-prefix gate is added before it runs.
- `project_slug` is required, not optional, matching `extract_story_key_from_bmadloop_merge_subject`'s own signature exactly.
- Every currently-passing `test_promotion.py` assertion for `extract_story_key_from_github_merge_subject`/`merged_story_keys`/`count_conforming_subjects` still passes once updated to pass `_PROJECT_SLUG` (`"pyforge-marshal"`) as the new required argument — verified by hand against every real fixture in that file before writing code (`marshal/2-3-...`, `marshal/3-8-...`, `marshal/refresh-dashboard-3-7`, `marshal/epic-3-retro` all resolve identically under `.removeprefix("pyforge-")` scoping to `"pyforge-marshal"`).
- Pure-function discipline (AD-4): no I/O, no subprocess, no `pathlib` methods added anywhere in `core/promotion.py`.

**Ask First:** none — the fix is fully scoped by the Spec and verified against real fixtures before implementation; no open decision remains.

**Never:**
- Do not add recognition for new merge-subject shapes (e.g. teaching this function to parse `land/<slug>-<epic>-<seq>` too) — that is the larger, still-open deferred-work item this fix deliberately stays narrower than. `land/<slug>-<epic>-<seq>` branches (e.g. `land/mason-4-4`) are confirmed to already return `None` today (their segment's leading token is the slug name, not a digit, so `normalize()` already rejects it) — this fix must not change that outcome.
- Do not touch `extract_story_key_from_bmadloop_merge_subject` or its own scoping — only bring the GitHub pattern up to the same standard.
- Do not add a plausibility bound on raw epic/story numbers in `core.identity.normalize` (out of scope; separate contract).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Own-project branch, `<slug>/<epic>-<seq>-<desc>` | `subject="Merge pull request #269 from rxm7706/marshal/2-3-frozen-surface-scope-check"`, `project_slug="pyforge-marshal"` | Returns `StoryKey(2, 3)` (unchanged from today) | N/A |
| Cross-project collision — the live bug | `subject="Merge pull request #274 from rxm7706/marshal/4-2-teardown-reachability-spec-recovery"`, `project_slug="pyforge-mason"` | Returns `None` (today wrongly returns `StoryKey(4, 2)`) | N/A |
| Same subject, correct project | Same subject, `project_slug="pyforge-marshal"` | Returns `StoryKey(4, 2)` | N/A |
| Branch digits present but not leading | `subject` with branch `marshal/refresh-dashboard-3-7"`, `project_slug="pyforge-marshal"` | Returns `None` (unchanged — `normalize` rejects non-leading digits) | N/A |
| `land/<slug>-<epic>-<seq>` shape | `subject="Merge pull request #516 from rxm7706/land/mason-4-4"`, any `project_slug` | Returns `None` (unchanged — already fails `normalize` before this fix) | N/A |
| Unrelated branch (date/version bump) | `subject="Merge pull request #441 from rxm7706/2026-08-11-Pixi-v0.76.2"`, any `project_slug` | Returns `None` (unchanged) | N/A |
| Non-GitHub-shaped or non-merge subject | `"fastmcp-v4"`, any `project_slug` | Returns `None` (regex mismatch, unchanged) | N/A |

</frozen-after-approval>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py` — `_GITHUB_MERGE_SUBJECT_RE` (widen owner capture to non-greedy), `extract_story_key_from_github_merge_subject` (add `project_slug` param + prefix gate), `_classify_merge_subject` (thread `project_slug` through its one call).
- `src/shared/packages/pyforge-marshal/tests/unit/test_promotion.py` — update every existing `extract_story_key_from_github_merge_subject(...)` call to pass `_PROJECT_SLUG`; add new regression tests for the cross-project rejection/acceptance pair and the `land/<slug>-...` no-op confirmation.

## Tasks & Acceptance

**Execution:**
- [x] `core/promotion.py` — widen `_GITHUB_MERGE_SUBJECT_RE`'s owner group to non-greedy (`\S+?`), update its explanatory comment (the greedy-backtracking rationale it currently documents becomes false).
- [x] `core/promotion.py` — add `project_slug: str` param to `extract_story_key_from_github_merge_subject`; gate on `branch.startswith(f"{project_slug.removeprefix('pyforge-')}/")` before calling `normalize`; update its docstring.
- [x] `core/promotion.py` — update `_classify_merge_subject`'s call site to pass `project_slug`; update its docstring's "scopes the bmad-loop pattern only" claim, now false.
- [x] `tests/unit/test_promotion.py` — update all 6 existing `extract_story_key_from_github_merge_subject` calls to pass `_PROJECT_SLUG`.
- [x] `tests/unit/test_promotion.py` — add regression tests: PR #274's real subject rejected under `project_slug="pyforge-mason"`, accepted under `project_slug="pyforge-marshal"`; PR #516's real subject still `None` under any project_slug (the already-harmless shape, confirmed unaffected).
- [x] `deferred-work.md` — marked the two 2026-08-10 entries against this function `resolved`; two new low-severity findings from review pass 1 (case-sensitivity, fork-owner-equals-station-name) logged as new `open` entries.

**Acceptance Criteria:**
- Given PR #274's real subject and `project_slug="pyforge-mason"`, when `extract_story_key_from_github_merge_subject` runs, then it returns `None`.
- Given the same subject and `project_slug="pyforge-marshal"`, then it returns `StoryKey(4, 2)`.
- Given `main`'s real full commit history and `project_slug="pyforge-mason"`, when `merged_story_keys` runs, then `StoryKey(4, 2)` is NOT in the result (live re-verification of the exact bug).

## Spec Change Log

**Review pass 1 (Blind Hunter + Edge Case Hunter, parallel, no shared context) — 2 patches, no intent_gap/bad_spec, no loopback.** Both reviewers independently found the same real gap: `core/status.py`/`cli/status.py` narrated this exact contamination as a still-open deferral, now stale since the fix closes it automatically for their call sites too — corrected both docstrings. Edge Case Hunter found a genuine reopening: an empty `station` (degenerate `project_slug` of `""`/`"pyforge-"`) degraded to `branch.startswith("/")`, letting a crafted double-slash subject slip through — closed with an explicit empty-station guard + regression test. Two low-severity, no-live-occurrence findings (case-sensitive station matching; a PR whose fork-owner literally equals the station name) deferred to `deferred-work.md` rather than fixed, per this Spec's own Never bullet against scope creep beyond the cross-project false-positive.

## Design Notes

**Why non-greedy owner, not a second capture group.** The current regex's greedy `\S+` before `branch` deliberately backtracks to the LAST `/`, so `branch` only ever holds the trailing key-shaped segment — this is WHY the project-identifying prefix (`marshal/`, `land/`) is invisible to the function today. Verified live: `re.match(r"...\S+/(?P<branch>\S+)$", "... from rxm7706/marshal/4-2-...")` captures `branch="4-2-teardown-..."`, losing `marshal/` entirely. Switching the owner group to non-greedy (`\S+?`) makes it match the SHORTEST possible prefix — just the GitHub owner (`rxm7706`, never containing `/`) — so `branch` becomes the full remainder (`marshal/4-2-teardown-...`), and `segment = branch.rsplit("/", 1)[-1]` (unchanged) still derives the identical trailing key. This is the minimal change that preserves 100% of existing key-derivation behavior while making the project-identifying prefix visible for the new gate.

**Why `.removeprefix("pyforge-")`.** Every `project_slug` this function receives is the CLI's full form (`"pyforge-mason"`, confirmed live from `land.py`'s `slug = args.slug` and `head_branch = f"loop/{slug}"` matching real `loop/pyforge-mason` branches) — but real GitHub branch prefixes use the short station name (`marshal/`, `doctor/`, confirmed via `git log --merges` across `main`'s real history). All 8 current stations follow `pyforge-<name>` uniformly, so this is a safe, verified derivation, not a guess.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: all green, including new regression tests, zero regressions in `test_promotion.py` or any other suite touching `merged_story_keys`/`count_conforming_subjects`/`marshal_native_merged_keys`.
- `pixi run -e pyforge-marshal marshal land pyforge-mason --format text` — expected: reports a fresh landing for the `4.2` wave, not `already landed -- confirming retirement/resync only` (the live bug this fix closes).
