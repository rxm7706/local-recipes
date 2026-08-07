---
title: 'Teardown reachability and spec-recovery assistance'
type: 'feature'
created: '2026-08-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: []
baseline_revision: 'f38ec4bc714fc4b5268d43532d3621cd7beb7b98'
---

<intent-contract>

## Intent

**Problem:** `run_teardown`'s AD-29 refusal check has a hardcoded-empty extension point, `_unreachable_promotions` — its docstring names Epic 4 as the story that replaces the body: "a repo-wide grep at planning time found zero existing promotion/reachability machinery." That machinery now exists (Story 4.1's `core/promotion.py`). Separately, when a spec IS genuinely missing (not merely unpromoted), there is no assistance today — a human has to reconstruct it from memory, exactly the failure this epic's own motivating incident (13 of 31 specs lost, 8 more zero-byte) already proved is too easy to get wrong.

**Approach:** (1) real `_unreachable_promotions` body reusing Story 4.1's own `core.promotion.classify_promotion_candidates`/`merged_story_keys` machinery, scoped to the slug being torn down — computed fresh at call time (AD-29: "reachability computed at teardown time, never a journal flag"), never cached; (2) `--force` on an unreachable-promotion refusal now requires the operator to name every story key being abandoned via a new `--abandon KEY [KEY ...]` flag, journaled; (3) a new `marshal deploy recover-spec <slug> <key>` command that searches this slug's own Tier-3 `runs/*/` scratch tree for a surviving snapshot first, falling back to a contract-only regeneration from `epics.md`'s Intent + ACs — labelled as regenerated in its own frontmatter, never presented as if it were the original.

## Boundaries & Constraints

**Always:**
- `_unreachable_promotions(repo_root: Path, branch: str, project_slug: str) -> tuple[str, ...]` (signature grows a `project_slug` parameter — the docstring's own promise that "Epic 4 replaces only this function's BODY" holds for the body; the call site already has `slug` in scope to pass through) delegates to a new `cli/deploy.py::unreachable_promotions_for_slug(root: Path, project_slug: str) -> tuple[StoryKey, ...]` — this is a DELIBERATE reuse, not a reimplementation: it runs the exact same candidate-discovery (`Tier-3 spec-*.md` scan) and classification (`merged_story_keys` + `classify_promotion_candidates`) `deploy promote` itself uses, and returns every key in `plan.to_promote` (durable, not yet promoted) or named by a `plan.gaps` finding (durable, no spec at all) for THAT slug. Computed fresh every call — no caching, matching AD-29's own "never a journal flag" text.
- `run_teardown`'s existing refusal-reason accumulation (the `reasons: list[str]` pattern already in the function) gains the unreachable-promotion names verbatim — no new refusal SHAPE, just a real predicate feeding the existing one.
- **`--force` alone is no longer sufficient to override an unreachable-promotion refusal specifically** (dirty-worktree and genuinely-unmerged-branch refusals are unaffected — `--force` still overrides those exactly as today). A new `--abandon KEY [KEY ...]` flag must name every unreachable story key being abandoned; teardown refuses (even with `--force`) if any unreachable key is NOT named in `--abandon`, and refuses if `--abandon` names a key that ISN'T actually unreachable (no vacuous/decorative abandonment). Both `--force` and the correct `--abandon` set are required together to proceed past an unreachable-promotion refusal — `--force` alone still overrides dirty/unmerged refusals as before. The abandonment is journaled (one `observation` entry, `story_key`+`reason` per abandoned key) — AD-27's own trust model (attributable, not authenticated) applies here exactly as it does to every other operator-attributed entry in this codebase.
- `marshal deploy recover-spec <slug> <key>` (new action on the existing `deploy` subcommand, mirrors `promote`'s own registration shape): searches `<tier3>/runs/*/` (this slug's own Tier-3 run-scratch tree, `cli/spin.py::_tier3_path`'s own path convention) for any file matching `spec-<key>*.md`, sorted by modification time descending (most recent snapshot first — "surviving run-worktree snapshots first" per the AC). Each match is reported as a candidate location with its path and mtime; recovery does NOT auto-select one — the operator reads the report and copies the one they trust into the canonical Tier-3 `implementation-artifacts/` path themselves (this command reports, it does not silently overwrite the canonical location).
- **When zero snapshot candidates are found**, the command falls back to a contract-only regeneration: locate the story's own section in `epics.md` (by story key, reusing whatever epics-file parsing already exists — check `core/identity.py`/`cli/*` for an existing epics-section locator before writing a new one), extract its Intent (the "As the operator, I want... So that..." block) and Acceptance Criteria verbatim, and write a NEW file to `implementation_artifacts/spec-<key>-recovered.md` — never overwriting an existing Tier-3 file — with frontmatter carrying `status: 'draft'` and a new `recovery_source: 'epics-derived-contract-only'` key, so it is structurally distinguishable from a hand-authored spec at a glance (matches the AC verbatim: "any regenerated contract-only spec is labelled as such in its own frontmatter"). This is a genuinely reduced artifact — Intent + ACs only, no Code Map, no Design Notes, no Boundaries & Constraints — and must not claim to be more than that.
- Recovery **reports, never fabricates**: if a story key has no `epics.md` section either (a genuinely orphaned key), the command reports that explicitly as a finding rather than writing an empty or invented file.

**Never:**
- No caching of the reachability result anywhere (policy, journal, or otherwise) — every `run_teardown` invocation recomputes it.
- `recover-spec` never writes into `planning-artifacts/specs/` (the tracked archive) directly — a recovered spec is Tier-3 scratch like any other, and reaches the tracked archive only through the normal `deploy promote` path, after a human has reviewed it.
- `recover-spec` never overwrites an existing file at its own target path or at any snapshot candidate's path — read-only against every candidate location, one new write at most (the regenerated fallback, only when it doesn't already exist).
- Do not touch `cli/land.py`/`core/landing.py` — those don't exist yet and are later Epic 4 stories' own Surface.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Teardown, all specs durable | No unreachable promotions for this slug | `_unreachable_promotions` returns `()`; refusal decision unaffected by this check | No error |
| Teardown, one spec unpromoted but durable | Story key durable (git-truthful), not yet in tracked archive | Named in the refusal reasons; teardown refuses without `--force`+`--abandon` | No error, refusal is the correct behavior |
| Teardown, one spec entirely missing for a durable story | Key durable, no Tier-3 spec file at all | Same refusal path — a promotion gap is exactly as "unreachable" as an unpromoted-but-present one | No error |
| `--force` alone, unreachable promotions exist | No `--abandon` | Refusal still holds — `--force` alone insufficient for this specific reason | Registered finding naming exactly what `--abandon` must list |
| `--force --abandon <key>`, matching the real unreachable set | Named keys == unreachable keys exactly | Teardown proceeds; one journaled abandonment entry per key | No error |
| `--force --abandon <wrong-key>` | Named key is NOT actually unreachable | Refused — no vacuous abandonment permitted | Registered finding |
| `recover-spec`, snapshot found | A `runs/*/spec-<key>*.md` match exists | Reported, most-recent first, path + mtime; no file written | No error |
| `recover-spec`, no snapshot, epics.md has the story | Fallback regeneration | New `spec-<key>-recovered.md` written, `recovery_source` frontmatter set | No error |
| `recover-spec`, no snapshot, no epics.md section either | Genuinely orphaned key | Registered finding; no file written | Reported, not fatal |
| `recover-spec`, target already exists | `spec-<key>-recovered.md` already present | Not overwritten; reported as already-present | No error |

</intent-contract>

## Code Map

- `src/pyforge/marshal/cli/deploy.py` — EDIT. `unreachable_promotions_for_slug(root: Path, project_slug: str) -> tuple[StoryKey, ...]` (reuses existing candidate-discovery + `promotion.merged_story_keys`/`classify_promotion_candidates`); new `recover-spec` action + `run_recover_spec`.
- `src/pyforge/marshal/cli/init.py` — EDIT. `_unreachable_promotions` gains `project_slug`, delegates to `deploy.unreachable_promotions_for_slug`; `add_teardown_subparser` gains `--abandon`; `run_teardown` requires the abandon-set to exactly match the unreachable set before proceeding past that refusal reason, journals abandonment.
- `src/pyforge/marshal/adapters/vcs_git.py` — EDIT only if a new read-only primitive is needed for the snapshot search (check first — `Path.glob` over the Tier-3 tree may not need any new `VcsPort` method at all, since it's plain filesystem scanning, not git).
- `src/pyforge/marshal/core/findings.py` / `core/verdict.py` — EDIT. New codes: abandon-set mismatch, recover-spec orphaned-key gap.
- `tests/unit/test_init.py` (or wherever `test_run_teardown` lives) — EDIT. Real predicate wiring, `--abandon` matrix.
- `tests/unit/test_deploy.py` — EDIT. `unreachable_promotions_for_slug`, `recover-spec` end-to-end.

## Tasks & Acceptance

**Execution:**
- [x] `cli/deploy.py` — `unreachable_promotions_for_slug`, reusing Story 4.1's machinery.
- [x] `cli/init.py` — real `_unreachable_promotions` body, `--abandon` flag, journaled abandonment.
- [x] `cli/deploy.py` — `recover-spec` action: snapshot search, epics-derived fallback, orphaned-key gap.
- [x] `core/findings.py` / `core/verdict.py` — register new codes.
- [x] Unit tests for every new/edited module, including the full I/O matrix above.
- [x] `deferred-work.md` — log any scope narrowed during implementation (none needed this pass — see Spec Change Log).

**Acceptance Criteria:**
*(Story 4.2's ACs from `epics.md`, preserved as the contract of record.)*
- [x] Given a loop home with merged stories, when teardown runs, then the refusal predicate is reachability computed at teardown time, never a journal flag (AD-29)
- [x] And a forced teardown over an unreachable promotion requires the operator to name the story keys being abandoned, and records them
- [x] Given a story whose spec is missing, when recovery assistance runs, then it reports the ordered candidate locations — surviving run-worktree snapshots first, then the epics-derived contract fallback
- [x] And it reports, never fabricates: any regenerated contract-only spec is labelled as such in its own frontmatter

## Design Notes

**Why `_unreachable_promotions` reuses `deploy promote`'s own machinery rather than a parallel implementation.** Two independent implementations of "is this story's spec durable" would inevitably drift — exactly the class of bug this project's own AD-24 ("one render/parse owner") and AD-33 (domain partition) both exist to prevent elsewhere. Teardown asking the same question `deploy promote` already answers, through the same function, means a fix to one detection bug (like this session's own cross-project collision fix) automatically fixes both call sites.

**Why `--abandon` requires an exact-match set, not just "any names at all."** A `--force --abandon story-that-was-never-at-risk` would let an operator's habitual, unread flag satisfy the letter of "name the keys" while abandoning something they never looked at — the AC's own intent ("the operator being made to look") is defeated by a rubber-stamp value. Requiring the named set to equal the real unreachable set forces the operator to have actually read the refusal's own finding before proceeding.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: all green, new tests included, zero regressions.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` — expected: all import-linter contracts hold.

**Manual checks (if no CLI):**
- Run `marshal teardown <slug>` against a real loop home with a durable-but-unpromoted spec and confirm the refusal names it; confirm `--force --abandon <key>` proceeds and journals the abandonment.

## Spec Change Log

- **`PromotionPlan` (Story 4.1's own `core/promotion.py`) gained a new field, `missing_spec_keys: frozenset[StoryKey]`.** The spec's Always bullet says `unreachable_promotions_for_slug` returns every key "named by a `plan.gaps` finding" for the no-spec-at-all case, but `Finding` (`core/model.py`) carries only a human `message`/`path`, no structured `story_key` field — extracting the key would have meant regexing it back out of a message written for humans, or (worse) a second parallel classification loop in `cli/deploy.py` that could drift from `classify_promotion_candidates`'s own partition. Since the story's own Design Notes explicitly reject two independent implementations of "is this story durable," the fix was to let the ONE existing classification loop (which already knows, per key, whether it hit the missing-spec branch) also populate a structured set alongside the `Finding` it already emits. `missing_spec_keys` deliberately does NOT include invalid-spec (`MRS-DEPLOY-002`) keys — a spec that exists but fails validation is a distinct paper-trail gap the spec's own Always bullet does not name as "unreachable."
- **`_unreachable_promotions`'s real signature threads `vcs`/`fs` too, not just the promised `project_slug`.** The spec's own Always bullet names the docstring's literal promise ("the call site... contract... are permanent — Epic 4 replaces only this function's BODY") as growing only a `project_slug` parameter. In practice the function's new body performs real I/O (via `deploy.unreachable_promotions_for_slug`), and `run_teardown` already takes `vcs`/`fs` as its own DI seam for exactly this reason (testability without a real git process/filesystem) — a version of `_unreachable_promotions` that silently defaulted to `GitVcs()`/`LocalFs()` internally would make it untestable through the same fakes every other `run_teardown` test already uses, and would be a real (if narrow) violation of AD-11's "every write observable through Marshal's own ports" spirit for its read-side counterpart. Threading the same seam through was simpler and more consistent than inventing a second injection path.
- **`_scan_promotions`'s "no assessment attempted" case reuses the SAME `plan is None` value `run_promote`'s own "could not read local main" case already used**, rather than adding a distinct tri-state. Both mean "no promotion plan exists for this call" from the caller's point of view (`run_promote` already treats them identically — it just skips the promote/commit block either way), and `unreachable_promotions_for_slug`'s own docstring already documents degrading to `()` for `plan is None` regardless of WHICH sub-case produced it. Splitting this into two distinct signals would have added a state no caller currently needs to distinguish.
- **`unreachable_promotions_for_slug` degrades to `()`, never raises or surfaces a finding, when durability genuinely cannot be determined** (e.g. `git log main` fails). The function's own declared signature (`-> tuple[StoryKey, ...]`) carries no findings channel, and `_unreachable_promotions`'s call site inside `run_teardown` has no way to thread a `Finding` back out of a plain tuple return either — matching the spec's own instruction that the stub's "call site and contract... are permanent." This is a real, intentional trade-off (an operator whose git history is unreadable sees `unreachable: ()`, not a warning that the check itself failed) rather than a silent oversight; it is the same "reachability, once genuinely unanswerable, must not itself dead-end teardown" shape AD-29's own F-14 amendment already established for the promotion side of this exact question.
  **SUPERSEDED, 2026-08-06 (see Review Triage Log, P1, both reviewers' independent top finding):** this trade-off turned out to be the story's single most serious defect, not an acceptable one — a destructive `marshal teardown` treated an UNDETERMINED safety-check result as CONFIRMED-clean and proceeded on `--force` alone with zero visible signal. The signature now returns `None` (UNDETERMINED) distinct from `()` (CONFIRMED-empty), and the "call site and contract are permanent" promise was read too literally: the CONTRACT (refuse when unreachable) is preserved and strengthened; only the exact return SHAPE changed, which the story's own text never actually froze.
- **`recover-spec`'s malformed-slug/malformed-key/I/O-failure paths reuse existing registered codes (`MRS-POLICY-006`, `MRS-IDENT-001`, `MRS-DEPLOY-003`) rather than minting new ones.** The Code Map names exactly two new codes for this story (abandon-set mismatch, orphaned-key gap); every other failure mode `recover-spec` can hit already has a precise, previously-registered code with an identical shape elsewhere in this codebase (`cli/gate.py` already reuses `MRS-IDENT-001` for the same "malformed story key" fact rather than minting a per-caller duplicate; `MRS-DEPLOY-003` already folds together `deploy promote`'s own read-failure and write-failure cases under AD-31's "one code, one classification" rule, and `recover-spec`'s own read/write I/O failures are the same class of "Marshal could not positively confirm this operation completed" condition).
- **No existing `epics.md` story-section parser was found to reuse** (grepped `core/gate.py`, `core/identity.py`, `core/policy.py`, `core/egress.py` — all reference `epics.md` only in prose/comments, none parse it). Per the spec's own fallback instruction, a minimal one was written directly in `cli/deploy.py` (`_epics_story_section`/`_split_intent_and_acceptance_criteria`), scoped to exactly this story's need: one story's own `### Story <key>: ...` heading block, split into its Intent (As/I want/So that) and Acceptance Criteria text, verbatim.
- **No new `deferred-work.md` entries were needed this pass.** Every deviation above is a within-scope adaptation of the spec's own stated intent (documented here instead), not a narrowing of what the story delivers.

## Review Triage Log

### 2026-08-06 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 0
- patch: 6 (critical/high 2, medium 4)
- defer: 3
- reject: 0
- addressed_findings:
  - `[critical]` `[patch]` **`unreachable_promotions_for_slug` failed OPEN on an UNDETERMINED reachability read, silently reported the same as a CONFIRMED-empty one, and a destructive `marshal teardown` proceeded on it with `--force` alone.** Both reviewers independently flagged this as their #1 finding. When the REQUIRED local-`main` route (`VcsPort.commit_subjects`) raised, the function degraded to `()` — "nothing unreachable" — with no findings channel to explain why, and `run_teardown` then required only a bare `--force` (no `--abandon`) to remove the worktree and branch as though the AD-29 safety check had run clean. Fixed: the function's return type grew a third state, `None` (UNDETERMINED, distinct from `()` CONFIRMED-empty and a non-empty CONFIRMED-unreachable tuple), threaded through `cli/init.py::_unreachable_promotions`/`run_teardown`. An undetermined result now refuses at LEAST as strictly as a real unreachable set: a new registered finding, `MRS-TEARDOWN-005` (`Verdict.ERROR`, the same tier as `MRS-TEARDOWN-003`/`004`, never the looser `UNEVALUABLE`), and `--force` alone never carries past it — the operator must additionally pass `--abandon UNDETERMINED` (a literal sentinel token, since no real story keys can be named when the check never ran) to explicitly acknowledge proceeding without that check. New tests: `test_unreachable_promotions_for_slug_returns_none_when_main_history_unreadable`, `test_teardown_ad29_undetermined_reachability_blocks_even_with_plain_force` (covers the bare-`--force` silent-pass-through scenario directly, a wrong-key `--abandon` attempt, and the sentinel-authorized proceed-and-journal path).
  - `[high]` `[patch]` **The AD-29 unreachable-promotion refusal message implied a causal link between the branch being torn down and the named unreachable story keys that does not exist.** The check is project-slug-wide (every Tier-3 spec for the whole project), not scoped to the specific branch — `branch` is accepted but never used to narrow it — yet the old message read "branch {branch} would become unreachable from: ..." as though those keys came from that branch specifically. An operator could reasonably (and wrongly) assume a printed key belonged to the branch being removed. Fixed: reworded to "project {slug!r} has N unreachable promotion(s) (not necessarily originating from this branch/worktree): ..." — the underlying scope stays project-wide (not changed), only the message's truthfulness. New test: `test_teardown_ad29_unreachable_message_does_not_imply_branch_causation`.
  - `[medium]` `[patch]` **A corrupt/truncated Tier-3 spec (`MRS-DEPLOY-002`) was excluded from the unreachable-promotions set entirely, needing no `--force`/`--abandon` to tear down.** A truncated spec is arguably in WORSE shape than a missing one — a missing spec is unambiguous, a truncated one might carry partial, misleading content — yet it was invisible to teardown's refusal gate. Fixed: `PromotionPlan` gained a new structured field, `invalid_spec_keys` (alongside the existing `missing_spec_keys`), populated by the same one classification loop `classify_promotion_candidates` already runs (no second implementation); `unreachable_promotions_for_slug` folds it into the unreachable set too. New tests: `test_invalid_spec_keys_names_the_zero_byte_or_truncated_case` (core), `test_unreachable_promotions_for_slug_includes_invalid_spec_keys` (CLI boundary).
  - `[medium]` `[patch]` **`recover-spec`'s snapshot glob had no boundary after the story key's own digits, so a lookup for key `1.2` also matched `spec-1-20-*.md`/`spec-1-23-*.md` — any key sharing "1-2" as a numeric PREFIX.** Fixed: the glob candidates are now filtered through an anchored regex requiring the segment immediately after the key's stem to be either end-of-name (the bare `spec-1-2.md` form) or a `-` title separator, never another digit. New test: `test_recover_spec_snapshot_search_does_not_match_a_numeric_prefix_collision`.
  - `[medium]` `[patch]` **The `recover-spec` epics.md-derived fallback could write a "recovered" spec whose Intent and/or Acceptance Criteria section came back empty and still report bare `recovered: true`, with no signal that the regenerated content is likely hollow.** Fixed: when either extracted section is empty after parsing, a new registered finding (`MRS-DEPLOY-005`, `Verdict.WARN`, the same tier as `MRS-DEPLOY-001`/`002`/`004`) names exactly which section(s) came back empty; the file is still written (matches this command's own "reports, never fabricates" framing) but the operator is now warned rather than trusting a hollow recovery silently. New test: `test_recover_spec_warns_when_acceptance_criteria_comes_back_empty`.
  - `[medium]` `[patch]` **The AD-27 abandonment journal entry was appended with `fsync=False`, despite authorizing a DESTRUCTIVE removal and AD-27's own guarantee that every widening is a recorded, durable event.** This codebase's existing precedent (AD-30: `phase: intent` entries fsync) treats operator-attributed, safety-critical journal entries as durable-at-write-time; this entry — which exists specifically to record an operator overriding a safety refusal — belongs in that same class. Fixed: `_append_abandonment_journal_entry`'s call site in `_journal_abandonments` now passes `fsync=True`. Existing test `test_teardown_ad29_unreachable_promotion_blocks_without_force` extended to assert `fsync is True` on every appended abandonment line.
- deferred (not fixed in this pass, appended to `deferred-work.md` as three NEW entries, D1-D3):
  - `[low]` The optional "pushed to origin/main" reachability route swallows `VcsCommandError` silently and falls back to the required local-`main`-only check — a softer, lower-severity version of the same fail-open shape P1 closed for the REQUIRED route. Lower severity because the required local-`main` check still runs and still gates teardown; closing it needs a `VcsPort` primitive that can distinguish "no origin configured" (the ordinary, correctly-silent case) from "origin configured but genuinely unreachable" (arguably worth a WARN), which does not exist today.
  - `[low]` `recover-spec`'s "never overwrite an existing file" guarantee is a check-then-act race (`fs.exists(dest)` then, later, `fs.write_text_atomic`), not an atomic exclusive create. Low practical risk for this single-operator CLI with no documented concurrent-invocation use case; a real fix needs a `FsPort.write_text_exclusive` (or similar) primitive that does not exist today.
  - `[low]` No collision handling if two abandonment-journal entries would land in the same run directory/id (`mint_run_id` collision) — a collision simply raises `FsError`/`MRS-TEARDOWN-002` rather than retrying with a fresh id. Astronomically unlikely given the millisecond-timestamp + 32-bit-random-token id space and this CLI's one-teardown-at-a-time usage pattern; not worth the added complexity in this pass.

</intent-contract>

## Suggested Review Order

**The safety-critical fix (P1) — start here**

- `unreachable_promotions_for_slug`'s three-state return (confirmed-empty / confirmed-unreachable / undetermined) — the fix for a destructive command silently proceeding when its own safety check couldn't run.
  [`deploy.py:394`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py#L394)

- `run_teardown`'s refusal wiring: `MRS-TEARDOWN-005` for undetermined reachability, the `--abandon` exact-match gate, and the P2 message-truthfulness fix.
  [`init.py:1733`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/init.py#L1733)

- `_unreachable_promotions`'s real body (was a hardcoded-empty stub).
  [`init.py:1568`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/init.py#L1568)

**Promotion classification (P3: invalid specs now unreachable too)**

- `PromotionPlan.invalid_spec_keys` and its fold into the unreachable set.
  [`promotion.py:1`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py#L1)

**Spec recovery**

- `recover-spec`: snapshot search (P4 glob-anchoring fix), epics.md fallback, P5 empty-content warning.
  [`deploy.py:721`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py#L721)

- Snapshot-candidate glob matching.
  [`deploy.py:681`](../../../../src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py#L681)

**Tests (peripherals)**

- Teardown wiring, including the P1 undetermined-reachability regression tests.
  [`test_init.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_init.py#L1)

- `unreachable_promotions_for_slug`/`recover-spec` end-to-end.
  [`test_deploy.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_deploy.py#L1)

- Promotion classification, including P3's invalid-spec-keys coverage.
  [`test_promotion.py:1`](../../../../src/shared/packages/pyforge-marshal/tests/unit/test_promotion.py#L1)
