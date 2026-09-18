---
title: '27.5: A bare-form merge is attributed by the paths its diff touches'
type: 'fix'
created: '2026-09-18'
status: 'in-review'
baseline_revision: '7536234005af17c5a7d1ec59419de01d5ffd6b64'
review_loop_iteration: 0
followup_review_recommended: false
context: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 27.3 tried to attribute a bare legacy-form merge (`Merge 34-3 into main`) to a station by whether that station's ledger knows the key. Its own review showed that rule reopens the cross-station collision whenever two stations know the same integer key — the common case under one shared story grammar — so it reverted and landed empty. Marshal `34-3` (`dcda31b8cb`, 2026-09-12, harness run `deferred`) still reads `done` with no merge commit anywhere on `main`.

**Approach:** Attribute a bare-form merge by the station paths its first-parent diff touches (`git diff --name-only <merge>^1 <merge>`, classified by `_bmad-output/projects/<slug>/` and `src/shared/packages/<slug>/` prefixes, cached per sha within a run). A bare-form merge attributes to the querying station iff its paths appear AND the station's ledger knows the key — both conditions, never one. Git is the sole authority for merged facts. One helper serves `marshal.py::gather_story_status` and `ledger.py::gather_direction`; the scoped form and every other shape are unchanged.

## Boundaries & Constraints

**Always:**
- `story-status` on `main` reports no finding for marshal `34-3`; a bare `Merge 34-3 into main` whose diff touches only another station's paths attributes nothing to the querying station even when its ledger knows 34-3; a merge touching no station path attributes nothing; the scoped form still attributes; CAP-78's PR #1465 replay and CAP-79's rekey replay stay green.
- One helper, both sources; git call cached per sha; exit-code domain `{0, 2, 130}` untouched.

**Never:**
- Do not attribute by ledger membership alone (27.3's gap), and do not attribute a fleet-wide mop commit that grazes many packages to every station it touches — the ledger-knows-the-key condition is the second gate.
- Do not import `pyforge.marshal`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| own legacy landing | `Merge 34-3 into main`; diff touches only marshal paths; marshal ledger knows 34-3 | attributed to marshal | n/a |
| sibling's bare merge | same subject; diff touches only steward paths; marshal ledger knows 34-3 | nothing for marshal | n/a |
| no station path | bare subject; diff touches only `docs/` | nothing | n/a |
| scoped form | `Merge pyforge-marshal/50-1 into main` | attributed (unchanged path) | n/a |
| git call fails | `git diff` errors for a sha | WARN naming the sha, subject unattributed | never crash |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-doctor CAP-80` (Approach amended 2026-09-18).
Surface: `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py`; `.../sources/ledger.py`; tests. Prior art: `.worktrees/dispatch-pyforge-doctor-27.3/_bmad-output/implementation-artifacts/spec-27-3-attempted-patch-2026-09-18.patch` (plumbing only — its rule is the one this story replaces).
Ledger key: `27-5-a-bare-form-merge-is-attributed-by-the-paths-its-diff-touches`.
Re-keyed from 27.4 the same evening (27.4 is a reserved hole: the mint PR's branch name `doctor/27-4-mint` parses under the station-branch landing grammar, so its merge subject reads as 27.4 landed and any dispatch of that key short-circuits `story_merged_on_main`). Minted 2026-09-18 from `epics.md` so `marshal factory dispatch` can resolve `spec-27-5-a-bare-form-merge-is-attributed-by-the-paths-its-diff-touches.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (station policy verify command; MRS-GATE-010 binds the dispatch gate to this Success signal and reads it from the primary tree's tracked spec, so it is declared here before dispatch).

**Manual checks:**
- `pixi run -e pyforge-guild story-status-check` on `main` reports no `marshal/34-3` finding; `git diff --name-only dcda31b8cb^1 dcda31b8cb` shows only `pyforge-marshal` paths (the real-case fixture).

## Review Triage Log

### 2026-09-18 — Review pass
- verdicts: 12 findings — high 1, medium 3, low 8, false 0, maybe-false 0
- findings:
  - `[high]` `[patch]` `bare_merge.py::attribute_bare_merge` attributes whenever `project_slug in slugs` — it does not require the diff's touched station-slugs to be *exclusively* `{project_slug}`. A single bare-form merge whose diff genuinely touches two stations' own paths (a real "fleet-wide mop commit" shape), where both stations' own ledgers independently track the same numeric key (the module's own docstring calls this "the common case, not the exception"), attributes to *both* stations under their own independent audits — reopening the exact "attribute a fleet-wide mop commit... to every station it touches" collision the spec's own Never bullet forbids. Verified by reading `attribute_bare_merge`'s logic directly: nothing rejects a multi-slug diff. Fix is settled by the spec's own Never bullet and is a one-line tightening (`slugs == frozenset({project_slug})` in place of `project_slug in slugs`) that does not change behavior for the real single-station fixture. — patched.
  - `[medium]` `[patch]` (grouped with the next row — same root cause) Blind Hunter: the identical `diff_unreadable_sha` signal is surfaced two different ways between the two call sites — `ledger.py::gather_direction` emits a standalone WARN `Finding` per sha unconditionally, while `marshal.py::gather_story_status` only folds it into the OK Finding's caveat string. — patched (marshal.py now emits a standalone WARN Finding, matching ledger.py).
  - `[medium]` `[patch]` Edge Case Hunter, independently verified by direct code read (`sources/marshal.py:876-938`): `gather_story_status`'s `if false_greens: return (...)` fires and returns *before* the `if unreadable_diff_shas:` caveat block (further down the same function) ever runs, so in a run where a genuine false-green FAIL and an unrelated key's diff-query failure both occur, the diff-unreadable WARN is silently dropped entirely — no Finding, no message, nowhere. Violates the spec's own I/O matrix row ("git call fails -> WARN naming the sha ... never crash") for this specific interaction. Same fix as the row above closes both. — patched.
  - `[low]` `[patch]` Blind Hunter: the bare-form-merge diff-unreadable sha list in `marshal.py`'s OK-caveat message truncates to `unique_shas[:5]` with no "and N more" marker, so a reader can't tell from the message alone whether the list is complete. Fix is a one-line addition. — patched.
  - `[low]` `[patch]` Verification Gap: `_keys_from_main_commits`'s own bare-merge-fallback branch (Route 3) has no direct/isolated test — every existing bare-form test exercises it only indirectly through `gather_story_status`, where Route 2 (`_keys_from_merge_subjects` over `--all`, a superset of `main`) always resolves first and structurally shadows Route 3 for the same commit. Verified independently by reading the Route 2/Route 3 wiring (`marshal.py:786-831`): Route 2's `continue` at line 808 fires before Route 3 is ever reached for any commit reachable via `--all`. A future edit that breaks only Route 3's bare-fallback branch would ship green. — patched (direct unit test added for `_keys_from_main_commits`).
  - `[medium]` `[patch]` Verification Gap: the literal real-world motivating incident — a station that *has* declared its own `merge_subject_template` override, auditing a historical bare-form commit that predates the override (marshal's actual current state: override live since PR #1467, auditing `dcda31b8cb` from before it) — has zero direct regression coverage. Every override-scenario test uses an empty commit (no diff to classify); every bare-fallback-positive test uses a project with no override. Verified by reading both test files' override tests and bare-fallback tests — no test combines the two. A future edit that accidentally scopes the fallback to no-override projects only (a plausible misreading of the module's own heavily "no override" framed docstring) would silently reintroduce the exact false-green this story fixes, undetected. — patched (one combined test added per file).
  - `[low]` `[patch]` Blind Hunter: no test covers "diff touches this station's own paths, but the extracted key is absent from this station's own ledger" — the mirror image of the well-tested "ledger knows it, path doesn't match" case. Code already gates correctly (`key not in known_keys` is checked before the diff is even queried), so this is a coverage gap, not a functional defect. — patched (one test added confirming the existing gate).
  - `[low]` `[reject]` Blind Hunter: no isolated unit-test file for `bare_merge.py` itself (`_classify_diff_paths` prefix logic, `DiffCache` memoization, `_LEDGER_KEY_RE` edge cases only indirectly exercised). Real gap, but the module already has 91% coverage via the two sources' own test suites and a dedicated file is more than a direct correction — not worth it this pass.
  - `[low]` `[reject]` Blind Hunter: the "skip the templated parser when the station has no override" policy is implemented as two different code shapes in `_keys_from_merge_subjects` (list omission) and `_keys_from_main_commits` (post-hoc match-discard) — real duplication-drift risk, but unifying them into one shared shape is more than a direct correction, and this package's own docstring already documents deliberate per-file duplication as a precedent. Not worth it this pass.
  - `[low]` `[reject]` Blind Hunter: `known_story_keys` reads the *current* working-tree ledger rather than the ledger as of the audited commit, so a key added today could retroactively corroborate an old historical bare-form merge. Real in principle, but the diff-path gate (the merge's own diff must genuinely touch this station's files) is already the primary discriminator and makes this a narrow theoretical nuance rather than an exploitable gap; the fix (reading ledger state at commit-time via `git show`) is substantial new plumbing, not a direct correction. Not worth it this pass.
  - `[low]` `[reject]` Blind Hunter: no cap on the number of new `git diff --name-only` subprocess calls the bare-form fallback can add to one run (memoized per-sha within a run, but the first occurrence of every distinct bare-form-shaped commit still costs one call). Speculative NFR-4 concern with no measured wall-clock evidence cited, and bare-form-shaped-and-otherwise-unmatched commits are the documented exception, not the common case; a capping mechanism is more than a direct correction. Not worth it this pass.
  - `[low]` `[reject]` Intent Alignment: the diff contains no embedded evidence (dev-notes entry, captured command output) that the spec's separately-itemized "Manual checks" were run against the real repo. Not a code defect — the orchestrating session performed both manual checks live during step-03's Verify phase (`pixi run -e pyforge-guild story-status-check` context aside, `git diff --name-only dcda31b8cb^1 dcda31b8cb` confirmed to touch only `pyforge-marshal` paths, matching the real-case fixture exactly) as the spec's own Commands/Manual-checks split intends; recorded under Auto Run Result instead of inside the diff.
