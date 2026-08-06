---
title: 'Story-spec promotion with a durability predicate'
type: 'feature'
created: '2026-08-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: []
baseline_revision: '51d51597b0b71794cedda5d071dbde0645eef0d4'
---

<intent-contract>

## Intent

**Problem:** promotion (copying a merged story's spec from gitignored Tier-3 scratch into the tracked `planning-artifacts/specs/` archive) is today a manual step a human has to remember — the exact failure that destroyed 13 of 31 story specs outright and reduced 8 more to zero-byte husks (AD-13's own motivating incident). This session reproduced the gap live: none of Epic 3's 8 story specs, nor Story 2.3's, had been promoted despite being merged and `done`; all were recovered by hand.

**Approach:** `marshal deploy promote` (new `cli/deploy.py`) scans Tier-3 `implementation-artifacts/spec-*.md` files for promotion candidates, determines each candidate's durability git-truthfully (AD-33: git is sole authority for repository facts — never sprint-status.yaml, a process artifact) by parsing `main`'s commit-subject history through the already-shipped `render_merge_subject`/`parse_merge_subject` (AD-24, Story 1.2), and for every durable, not-yet-promoted, non-empty spec: copies it to the tracked archive path and commits it in one dedicated commit containing only promotion paths (AD-29).

## Boundaries & Constraints

**Always:**
- **Candidate discovery is Tier-3-native, promotion decision is git-native.** `cli/deploy.py` lists every `implementation_artifacts/spec-<key>.md` file (the "run scratch" AD-12 names) as a candidate; whether each is `promoted` is answered ONLY from git — never from `sprint-status.yaml`'s `development_status` (a process fact, AD-33's own partition: "no derived artifact sources a repository fact from the journal [or a process file]").
- **Reachability check recognizes TWO merge shapes, not one.** Verified live against this repo's own history (`git log --merges --oneline`): every real merge commit here is a GitHub PR merge, `"Merge pull request #N from <owner>/<branch>"` — never `render_merge_subject`'s templated form (`"Merge {key} into main"`), which no landing path in this repo actually writes. `merged_story_keys(subjects: tuple[str, ...], template: str) -> frozenset[StoryKey]` (placement: `core/promotion.py`, pure, AD-4) now tries BOTH patterns per subject, in order: (1) `core.identity.parse_merge_subject(subject, template)` — the AD-24 templated form, for a future `marshal land`-driven landing path; (2) a new pure `core/promotion.py::extract_story_key_from_github_merge_subject(subject: str) -> StoryKey | None` — matches `r"^Merge pull request #\d+ from \S+/(?P<branch>\S+)$"`, then attempts to parse a story-key slug out of the branch's final path segment (this repo's own observed convention: `marshal/<epic>-<seq>-<description>`, e.g. `marshal/2-3-frozen-surface-scope-check` — extract the leading `<epic>-<seq>` via `core.identity`'s existing key-normalization, never a second ad hoc key parser). A subject matching neither pattern is skipped (not every commit is a story merge), never a hard failure for the whole scan. `adapters/vcs_git.py` supplies the raw subjects via `VcsPort.commit_subjects(repo_root: Path, ref: str) -> tuple[str, ...]` (`git log <ref> --format=%s`, read-only) — unchanged from the original design, only the classification of each subject gained a second pattern.
- **AD-29's two implementable reachability routes, not all three.** "Pushed to the remote" is checked via `commit_subjects(repo_root, "origin/main")` when a remote named `origin` exists (fall back to local `main` if not — most loop-home clones in this project's own practice push immediately after merge, per this session's own recent pattern); "merged to the integration branch" is `commit_subjects(repo_root, "main")`. The third route — "reachable from the declared durable local ref" — has no implementation anywhere in this codebase yet (grepped: absent); it is explicitly OUT of scope here and logged to `deferred-work.md`, not silently dropped.
- **Promotion writes are scoped exactly, never `git add -A`.** A new `VcsPort.commit_paths(repo_root: Path, paths: tuple[Path, ...], message: str) -> str` (returns the new commit sha) stages exactly `paths` via individual `git add <path>` calls and commits ONLY those paths (`git commit -- <path> <path> ...`, never a bare `git commit` that would sweep in a pre-existing index) — the literal AD-29 requirement: "a dedicated commit containing only promotion paths — it never commits a pre-existing index." One commit per `deploy promote` invocation covering every newly-promoted spec in that run (not one commit per file — a single "promote N specs" run is one paper-trail event).
- **Validation before promotion, per AD-13.** A candidate spec that is zero-byte or fails a minimal parse (no frontmatter block, or frontmatter missing a `status:` key) is reported as a paper-trail gap (a registered `Finding`) and is **never promoted over an existing good copy** in the tracked archive — if `planning-artifacts/specs/spec-<key>.md` already exists and is valid, a broken Tier-3 copy changes nothing.
- **A durable story with no promotable spec is reported, never silently skipped.** If `merged_story_keys` contains a key with no corresponding `implementation_artifacts/spec-<key>.md` file at all, emit a registered `Finding` naming the gap (mirrors this session's own live discovery of exactly this condition for 9 stories).
- **Promotion happens logically "before" teardown**, per AD-13's ordering — this story does not itself touch `cli/init.py`'s teardown path (that is Story 4.2's own Surface, `cli/init.py` + `cli/deploy.py` + `adapters/vcs_git.py`), but `deploy promote` must be safely callable standalone, synchronously, with no dependency on teardown having run first or after.

**Never:**
- No new promotion-state flag/field in `sprint-status.yaml` or the journal — "promoted" is answered fresh from git every time `deploy promote` runs (AD-29: "the refusal predicate is reachability computed at teardown time, never a journal flag" — the sibling principle for promotion is the same computed-not-cached shape).
- No `git add -A`/`git commit` (bare, no pathspec) anywhere in this story's code.
- Do not implement the "declared durable local ref" route — log it, don't build it.
- Do not touch `cli/init.py`'s teardown refusal logic — that is Story 4.2.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Merged story, spec exists, not yet promoted | `implementation_artifacts/spec-<key>.md` present, key in `merged_story_keys`, no tracked copy | Copied to `planning-artifacts/specs/spec-<key>.md`, included in the dedicated promotion commit | No error |
| Merged story, already promoted | Tracked copy already exists and is valid | Skipped — no-op, not re-copied, not re-committed | No error |
| Merged story, spec missing entirely | No `spec-<key>.md` for a key in `merged_story_keys` | Registered `Finding` naming the gap; promotion continues for other candidates | Reported, not fatal to the run |
| Merged story, spec is zero-byte/truncated | File exists, fails minimal parse | Registered `Finding`; not promoted (existing good tracked copy, if any, is untouched) | Reported, not fatal |
| Not-yet-merged story, spec exists in Tier-3 | Key not in `merged_story_keys` | Skipped — not a promotion candidate yet (correct: not durable) | No error |
| No `origin` remote configured | `git remote` has none | Falls back to local `main` only for the "pushed" route | No error, no `VcsCommandError` |
| `git log` fails (corrupted repo, no `main`) | `commit_subjects` raises `VcsCommandError` | Propagates to the CLI layer as a hard `unevaluable` finding for the whole `deploy promote` run | Never silently returns an empty set (which would look like "nothing merged yet" and promote nothing) |
| Zero candidates to promote | No Tier-3 spec files at all, or all already promoted | Clean envelope, `verdict: clean`, `data.promoted_count: 0` | No error |
| A commit subject that isn't a story merge at all | e.g. `"fastmcp-v4"`, `"pixi update requires-pixi"` | `parse_merge_subject` raises `MergeSubjectConformanceError` for that one subject; skipped, scan continues | Never aborts the whole scan |

</intent-contract>

## Code Map

- `src/pyforge/marshal/ports/vcs.py` — EDIT. `VcsPort.commit_subjects(repo_root: Path, ref: str) -> tuple[str, ...]`; `VcsPort.commit_paths(repo_root: Path, paths: tuple[Path, ...], message: str) -> str`.
- `src/pyforge/marshal/adapters/vcs_git.py` — EDIT. Implement both: `commit_subjects` via `git log <ref> --format=%s`; `commit_paths` via per-path `git add` then `git commit -- <paths>`, returning `git rev-parse HEAD` after commit. Both raise `VcsCommandError` on failure, matching every other method in the file.
- `src/pyforge/marshal/core/journal.py` — EDIT (or a new small `core/promotion.py` if `journal.py` is already large enough that a new unrelated concern doesn't belong there — check the file's current size/scope before deciding placement). `merged_story_keys(subjects: tuple[str, ...], template: str) -> frozenset[StoryKey]` — pure, per-subject `parse_merge_subject` with per-subject exception tolerance.
- `src/pyforge/marshal/core/gate.py` or a new `core/promotion.py` — NEW/EDIT. `classify_promotion_candidates(candidates: tuple[SpecCandidate, ...], merged_keys: frozenset[StoryKey], already_promoted: frozenset[StoryKey]) -> PromotionPlan` (pure): partitions into to-promote / already-promoted-skip / missing-spec-gap / invalid-spec-gap. New frozen dataclasses `SpecCandidate(story_key, path, text)`, `PromotionPlan(to_promote, gaps: tuple[Finding, ...])`.
- `src/pyforge/marshal/cli/deploy.py` — NEW. `add_deploy_subparser`, `run_promote`: reads Tier-3 spec files (impure edge), calls `VcsPort.commit_subjects` for both routes, calls `core`'s pure `merged_story_keys`/`classify_promotion_candidates`, copies files for the `to_promote` set, calls `VcsPort.commit_paths` once for the whole batch, emits the standard envelope (AD-14).
- `src/pyforge/marshal/cli/main.py` — EDIT. Register `add_deploy_subparser`.
- `src/pyforge/marshal/core/findings.py` / `core/verdict.py` — EDIT. New codes: missing-spec-for-merged-story (paper-trail gap), invalid/truncated-spec (paper-trail gap), `commit_subjects` read failure (unevaluable).
- `tests/unit/test_vcs_git.py` — EDIT. `commit_subjects`/`commit_paths` against a real temp git repo, including the "commit only named paths, not the whole index" proof.
- `tests/unit/test_promotion.py` — NEW. `merged_story_keys`/`classify_promotion_candidates` transition matrix, including the "non-story-merge subject is skipped, not fatal" case.
- `tests/unit/test_deploy.py` — NEW. End-to-end `deploy promote` CLI tests via fake `VcsPort`/`FsPort`.

## Tasks & Acceptance

**Execution:**
- [x] `ports/vcs.py` + `adapters/vcs_git.py` — `commit_subjects`, `commit_paths`.
- [x] `core/journal.py` (or `core/promotion.py`) — `merged_story_keys`, pure.
- [x] `core/promotion.py` (or `core/gate.py`) — `SpecCandidate`/`PromotionPlan`/`classify_promotion_candidates`, pure.
- [x] `cli/deploy.py` — `marshal deploy promote`, wired into `cli/main.py`.
- [x] `core/findings.py` / `core/verdict.py` — register the 3 new codes.
- [x] Unit tests for every new/edited module, including the full I/O matrix above.
- [x] `deferred-work.md` — log the "declared durable local ref" route as explicitly unimplemented (not silently dropped).

**Acceptance Criteria:**
*(Story 4.1's ACs from `epics.md`, preserved as the contract of record.)*
- [x] Given a merged story with a spec in run scratch, when promotion runs, then the spec is copied to the tracked `planning-artifacts/specs/` archive path and committed by Marshal itself, in a dedicated commit containing only promotion paths — it never commits a pre-existing index (AD-29)
- [x] And the story is marked `promoted` only when its bytes are reachable from a ref that survives the loop home (pushed to the remote, or merged to the integration branch) — a staged file, or a commit only on `loop/<slug>`, is not promoted (AD-29)
- [x] And promotion happens before any code path may remove that story's worktree (AD-13) — `cli/deploy.py` does not touch `cli/init.py`'s teardown logic at all (Story 4.2's own surface); `deploy promote` is safely callable standalone with no ordering dependency.
- [x] And a merged story with no promotable spec is reported as a paper-trail gap, never passed over silently (`MRS-DEPLOY-001`)
- [x] And zero-byte or truncated specs are detected and reported rather than promoted over a good copy (`MRS-DEPLOY-002`)
- [x] And the canonical archive is authoritative; run scratch is derived and never treated as the source (AD-12) — `classify_promotion_candidates` only ever copies FROM Tier-3 TO the tracked archive, never the reverse.

## Design Notes

**Why reachability is computed fresh from git every run, never cached.** Mirrors AD-29's own sibling rule for teardown ("reachability computed at teardown time, never a journal flag") — a cached "promoted" flag can go stale the moment history is rewritten or a branch is force-pushed, exactly the class of drift AD-33's domain-partition rule exists to prevent.

**Why this session's own manual promotion work (PRs #266/#267/#269) is the lived spec for this story.** Every promotion this session performed by hand followed the same shape this story automates: find a merged-but-unpromoted story (by inspecting `git log` for its merge PR), copy the Tier-3 spec, commit it in a dedicated commit. This story is not speculative design — it is the direct automation of work already proven necessary and correct by hand, three times, in this same session.

**Why "declared durable local ref" is deferred, not built.** No code anywhere in this package references a real mechanism for it (only one comment in `cli/init.py` names the concept). Building it from scratch is a meaningful design surface of its own (what names it, who declares it, how teardown respects it) that AD-29's own text treats as one of three independent routes — the other two (push, merge-to-main) are sufficient for every promotion this session actually performed, and building the third speculatively here would be exactly the kind of scope growth this project's own "Simplicity First" principle warns against.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: all green, new tests included, zero regressions.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: green modulo the pre-existing, unrelated `pyforge-steward` failures already logged in `deferred-work.md`.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` — expected: all import-linter contracts hold (AD-4 core purity for `merged_story_keys`/`classify_promotion_candidates`).

**Manual checks (if no CLI):**
- Run `marshal deploy promote` against this very repo's own `pyforge-marshal` project (a real, live target — 3.1-3.8 and 2.3's specs are ALREADY promoted by hand this session, so the correct, verifiable behavior is "0 promoted, N already-promoted skips, 0 gaps" for those keys).
  **NOT run** during implementation (see Spec Change Log below) — `commit_paths` makes a REAL commit, and live inspection at implementation time showed this repo's tracked archive is actually missing every Epic-2 spec except a Tier-3-only 2.3 (2.1/2.2/2.4/2.5/2.6 never promoted), while this repo's real merge commits don't conform to the default `merge_subject_template` shape at all (GitHub's own `Merge pull request #N from ...` subjects, not `Merge {key} into main`) — so a live run's outcome was unpredictable and would have produced a real, uncontrolled commit. Relied on the unit-test suite's real-temp-repo (`test_vcs_git.py`) and fake-`VcsPort` (`test_deploy.py`) coverage instead, mirroring Story 2.3's own `changed_files` verification without touching the real repo.

## Spec Change Log

- **Placement: `core/promotion.py` (new), not `core/journal.py` or `core/gate.py`.** `journal.py` is 1100+ lines covering the run journal's write protocol/fold/frozen-surface accumulation, none of which this story's promotion concern touches; `gate.py` is a separate, already-focused verify/scope-check module. Both `merged_story_keys` and `classify_promotion_candidates`/`SpecCandidate`/`PromotionPlan` live together in the new module — the Code Map offered `core/promotion.py` as an explicit alternative for both, and keeping the whole story's pure core in one small, self-contained file (matching this story's own scope) was simpler than splitting one cohesive concern across two existing files.
- **`MRS-DEPLOY-003` covers both the `commit_subjects` read failure the story's own edge-case matrix names AND the promotion write path (the Tier-3→tracked copy or `VcsPort.commit_paths`'s stage-and-commit) failing.** The Code Map names only "`commit_subjects` read failure (unevaluable)"; no code was specified for a copy/commit failure, and AD-31 forbids classifying the same code two different ways depending on context, so a would-be ERROR-tier sibling for the write-path case was rejected in favor of folding both failure modes into the one UNEVALUABLE code: "Marshal could not positively confirm this run's promotion completed." No acceptance criterion or I/O-matrix row exercises the write-path failure directly; documented here rather than left implicit.
- **Policy resolution reuses `cli/config.py`'s simple convention-lookup shape, not `cli/gate.py`'s elevated symlink/containment check.** `gate evaluate` needs that hardening because it EXECUTES arbitrary `verify_commands` the policy declares; `deploy promote` only reads one string field (`merge_subject_template`) to parse commit subjects — the arbitrary-command-injection threat model `_resolve_policy_source` exists for does not apply here.
- **The real-repo manual check was not run** — see the Manual checks note above.

- **Review-fix pass (2026-08-06): merge-detection recognized ZERO of this repo's real merges.** Adversarial review after the shipped code landed found that `merged_story_keys` only ever tried `render_merge_subject`'s templated form (`"Merge {key} into main"`) — but `git log --merges --oneline` shows every real merge commit in this repo's own history is a GitHub PR merge (`"Merge pull request #N from <owner>/<branch>"`), including the 3 landed earlier this session (PRs #266/#267/#269). The templated form has no writer anywhere in this repo today. Fixed by adding a second pure function, `core/promotion.py::extract_story_key_from_github_merge_subject(subject: str) -> StoryKey | None` (regex `^Merge pull request #\d+ from \S+/(?P<branch>\S+)$`, then `core.identity.normalize()` on the matched branch's final path segment — no new key-parsing logic) and trying it as a second pattern whenever `parse_merge_subject` raises `MergeSubjectConformanceError`. Verified against three real subjects pulled verbatim from this repo's own history: `"...#269 from rxm7706/marshal/2-3-frozen-surface-scope-check"` → `2.3`, `"...#266 from rxm7706/marshal/3-8-stage-bound-durability"` → `3.8`, and the deliberately ambiguous `"...#265 from rxm7706/marshal/refresh-dashboard-3-7"` → `None` (the digits `3-7` appear but not as the branch segment's LEADING token, so `normalize()` correctly refuses rather than silently minting a wrong key) — pinned as regression tests in `tests/unit/test_promotion.py` using these exact real strings, not synthetic fixtures, per the review's own "no test exercises template variance beyond the hand-authored happy path" finding.

- **Review-fix pass (2026-08-06): three smaller findings fixed alongside the merge-detection regression.** (1) `_already_promoted_keys` trusted a tracked file's mere on-disk EXISTENCE as proof of promotion — a partial-batch failure (`copy_file` succeeding immediately before the batched `commit_paths` call fails) left an orphaned, uncommitted file that every future run permanently mistook for "already promoted," never retrying its commit (both reviewers, independently). Fixed by adding `VcsPort.path_has_uncommitted_changes(repo_root, path)` (the per-path counterpart to the existing whole-worktree `has_uncommitted_changes`, via `git status --porcelain -- <path>`) and redefining "already promoted" as valid content AND git-confirmed committed — an unconfirmable status (the check itself raising) is treated as not-yet-promoted, never silently trusted. (2) `is_valid_spec_text`'s `status:` check was a raw substring test (`"status:" in frontmatter`), matching a line like `substatus: draft` or the literal text inside a comment; fixed to match `status:` as an actual line-start frontmatter key (`^status:\s` against each stripped line). (3) A run where zero commit subjects conformed to either merge-subject pattern was indistinguishable from a genuinely clean "nothing merged yet" — added diagnostic-only `data.subjects_examined`/`data.subjects_matched` envelope fields (via a new pure `core/promotion.py::count_conforming_subjects`) so an operator can tell the two apart; no `Finding`/verdict change.

- **Deferred, not fixed this pass:** the "declared durable local ref" route (already logged, unchanged); the pre-existing, Story-2.3-inherited hardcoded `main`/no-`--base`-override limitation (already logged there, not re-logged); and four newly-logged findings — `commit_subjects`'s unbounded `git log` history walk, `_discover_candidates`'s non-recursive Tier-3 glob, `_already_promoted_keys`'s glob not matching differently-suffixed historical filename variants, and `commit_paths`'s no-rollback-on-partial-`git add`-failure. See `deferred-work.md` for each entry's full evidence.

## Review Triage Log

### 2026-08-06 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 1
- patch: 3 (medium 3, low 0)
- defer: 5
- reject: 0
- bad_spec (triggered a loopback, resolved same-session per operator direction):
  - **Merge-detection recognized zero of this repo's real merges.** `merged_story_keys` only tried `render_merge_subject`'s templated form; every real merge in this repo's history is a GitHub PR merge, which no landing path here ever writes in that template shape. Root cause was the spec's own `## Boundaries & Constraints` assumption (AD-24 reuse), not the implementation of that assumption — a genuine spec-level gap, confirmed independently by both reviewers. Per operator decision, amended the spec to recognize both merge shapes rather than reverting to a full re-plan; re-derived only the affected function (`merged_story_keys` + new `extract_story_key_from_github_merge_subject`) rather than the whole story, since the rest of the pipeline (candidate discovery, classification, atomic commit) was unaffected and independently correct. Verified against three real subjects pulled from this repo's own `git log --merges` output, including a deliberately ambiguous one (`"...refresh-dashboard-3-7"`) that correctly returns `None`. See `## Spec Change Log` for full detail.
- addressed_findings (patch):
  - `[medium]` `[patch]` Partial-batch failure (a copy succeeding before a later copy or the batched commit failed) left an orphaned, uncommitted file that `_already_promoted_keys` permanently mistook for "already promoted," never retrying its commit — both reviewers independently found this. Fixed via a new `VcsPort.path_has_uncommitted_changes` and redefining "promoted" as content-valid AND git-confirmed committed.
  - `[medium]` `[patch]` `is_valid_spec_text`'s `status:` check was a raw substring test, matching e.g. `substatus: draft`. Fixed to match `status:` as a line-start frontmatter key.
  - `[medium]` `[patch]` A run where zero commit subjects conformed to either merge pattern was indistinguishable from a genuinely clean "nothing merged yet." Added diagnostic-only `data.subjects_examined`/`data.subjects_matched` envelope fields.
- deferred (not fixed this pass, appended to `deferred-work.md`):
  - `[medium]` `origin/main` read failures are unconditionally treated as "no push route," even for failures that aren't a missing remote (corrupted repo, filesystem error) — no operator-visible signal.
  - `[low]` `commit_subjects` has no history bound (`-n`/`--since`) and is invoked twice per run — cost grows unbounded with repo age.
  - `[low]` `_discover_candidates` globs Tier-3 specs non-recursively; a future subdirectory-organized layout would silently drop candidates.
  - `[low]` `_already_promoted_keys` matches tracked-archive filenames by slug glob; a differently-suffixed historical variant (as this session's own hand-promotions sometimes were) could be missed.
  - `[low]` `commit_paths`'s per-path `git add` loop has no rollback on a mid-loop failure, leaving a partially-staged index.
- rejected: none — both reviewers were precise; no noise or already-deliberate findings surfaced.

</intent-contract>

## Suggested Review Order

**Merge detection — the bad_spec fix**

- Entry point: the two-pattern classifier, and the GitHub-merge-subject extractor that fixed the review-found regression.
  [`promotion.py:80`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py#L80)

- `merged_story_keys`, trying the templated form first, then the GitHub form.
  [`promotion.py:120`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py#L120)

- Diagnostic-only match counting, so a zero-match run is distinguishable from "nothing merged."
  [`promotion.py:138`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py#L138)

**Pure classification core**

- `SpecCandidate`/`PromotionPlan` and the partition logic (to-promote / already-promoted / missing-spec gap / invalid-spec gap).
  [`promotion.py:212`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py#L212)

- `is_valid_spec_text` — the line-start `status:` key check (fixed from a raw substring match during review).
  [`promotion.py:188`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py#L188)

**Git primitives**

- `commit_subjects`/`commit_paths` and the new `path_has_uncommitted_changes` (the fix for the orphaned-uncommitted-file bug).
  [`vcs_git.py:1`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py#L1)

**CLI orchestration**

- `run_promote`: gathers subjects/candidates, delegates to pure core, copies + commits the batch.
  [`deploy.py:211`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py#L211)

- `_already_promoted_keys` — redefined during review from "exists on disk" to "exists AND git-confirmed committed."
  [`deploy.py:157`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py#L157)

**Tests (peripherals)**

- Real-subject regression tests (pulled verbatim from this repo's own `git log`, not synthetic).
  [`test_promotion.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_promotion.py#L1)

- End-to-end CLI orchestration via fake `VcsPort`.
  [`test_deploy.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_deploy.py#L1)

- `commit_subjects`/`commit_paths`/`path_has_uncommitted_changes` against real temp git repos.
  [`test_vcs_git.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_vcs_git.py#L1)

## Post-Merge Finding (2026-08-06)

**First real run against this repo (`marshal deploy promote`, invoked live to close out Epic 2) found a real filename-derivation bug.** `run_promote` computed the tracked-archive destination as a freshly-derived bare `spec-{render_filename_slug(story_key)}.md` (e.g. `spec-2-3.md`), discarding the Tier-3 source file's own descriptive title slug (`spec-2-3-frozen-surface-scope-check-narrowing-only.md`) — every prior promotion in this archive (Epic 3's 8 specs, promoted by hand) preserved the full title. Fixed by using `Path(spec_candidate.path).name` (the Tier-3 file's own filename) as the destination name instead of re-deriving one. `_already_promoted_keys`'s glob (checking both the bare and titled forms) was unaffected either way. Updated `test_promote_copies_and_commits_a_durable_unpromoted_spec` to assert the titled destination name. Caught before the mis-named commit was pushed anywhere — reset locally and re-run with the fix in place.
