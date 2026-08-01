<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-04 -->
---
title: 'CLAUDE.md wiring — team memory loads automatically (Story 1.2)'
type: 'feature'
created: '2026-07-30'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
final_revision: 'ef470529c2bde000941f5402ac7da9a56ed9e4f8'
context: []
warnings: []
baseline_revision: 'e868b607a10a8fbfba046a191d5ac637bde42f80'
---

<intent-contract>

## Intent

**Problem:** Story 1.1 scaffolded `.claude/memory/MEMORY.md`, but nothing in root `CLAUDE.md` surfaces it, so a fresh session can't see captured team-memory entries. `CLAUDE.md` also still carries the `## BMAD ↔ conda-forge-expert integration` section verbatim, which the legacy spec's Q3 flagged for de-duplication once that content lives in `.claude/memory/` instead.

**Approach:** Add a short `## Team Memory` section near the end of root `CLAUDE.md` that `@import`s `.claude/memory/MEMORY.md`. Leave the BMAD↔CFE section untouched for now — its own AC gates removal/reduction on Story 1.5 having *already* promoted the two BMAD↔CFE entries into `.claude/memory/feedback/`, which hasn't happened yet (build order: 1.1→1.2→1.3→1.4→1.5).

## Boundaries & Constraints

**Always:**
- Edit only root `CLAUDE.md` (this worktree's copy) — this is the human/agent-driven edit FR-7 reserves outside Scribe's own write boundary; no change to `src/shared/packages/pyforge-scribe/` or any `.claude/memory/**` file.
- Add a `## Team Memory` H2 section near the end of `CLAUDE.md`, containing an `@.claude/memory/MEMORY.md` import, mirroring this same file's existing `@.claude/docs/bmad-method-llms-full.txt` import convention.
- Preserve every other existing line and section of `CLAUDE.md` unchanged.

**Block If:** none — the de-dup ambiguity below is resolved against the AC's own literal precondition, not left open.

**Never:**
- Do not remove or shrink the `## BMAD ↔ conda-forge-expert integration` section's rule content. Its own AC ("When this story lands **and** Story 1.5 has populated the two BMAD↔CFE entries") requires both conditions; Story 1.5 has not run, so the section is the *only* place that content exists in the checked-in repo today — deleting it now is real data loss, not a safe de-dup.
- Do not hand-write `feedback_bmad_uses_cfe_skill`/`feedback_bmad_runs_cfe_retro`-equivalent entries into `.claude/memory/feedback/` to "unblock" the de-dup — Story 1.5's own AC binds that promotion to being produced by invoking `scribe capture --promote` itself, not authored by hand.
- Do not touch any other worktree or the `main` checkout — this run's branch already matches the story slug.

</intent-contract>

## Code Map

- `CLAUDE.md` (repo root) -- target of the edit; add `## Team Memory` near the end, leave `## BMAD ↔ conda-forge-expert integration` untouched
- `.claude/memory/MEMORY.md` -- import target, scaffolded by Story 1.1; currently has empty `## Feedback`/`## Project`/`## Reference` sections
- `_bmad-output/planning-artifacts/epics.md` (L100-114) -- Story 1.2's source ACs, incl. the de-dup Given/When/Then this spec resolves
- `_bmad-output/planning-artifacts/prds/prd-pyforge-scribe-2026-07-25/prd.md` (L100, L211) -- `[NOTE FOR PM]` / Open Question 6 carrying the legacy Q3 default forward as a human-reviewed call

## Tasks & Acceptance

**Execution:**
- [x] `CLAUDE.md` -- add a `## Team Memory` section near the end with a one-paragraph description and an `@.claude/memory/MEMORY.md` import line -- makes captured team-memory entries visible in every fresh session (Story 1.2 AC1)
- [x] `CLAUDE.md` -- leave `## BMAD ↔ conda-forge-expert integration` unchanged; record the deferral decision in this spec's Design Notes -- satisfies AC2's literal precondition (Story 1.5 hasn't populated the entries yet) without discarding content

**Acceptance Criteria:**
- Given Story 1.1 has scaffolded `.claude/memory/MEMORY.md`, when the `## Team Memory` section with `@.claude/memory/MEMORY.md` is added near the end of root `CLAUDE.md`, then a fresh Claude Code session in the repo has the index content in context (manually verifiable by asking Claude to list every entry currently in team memory).
- Given the legacy spec's Q3 default ("remove — single source of truth in `.claude/memory/`") and the epics AC's compound precondition, when Story 1.5 has not yet populated the two BMAD↔CFE entries in `.claude/memory/feedback/`, then the `## BMAD ↔ conda-forge-expert integration` section stays intact in `CLAUDE.md` and the de-dup is explicitly deferred to Story 1.5, recorded here rather than silently dropped.
- Given the edit is complete, when `git diff` is inspected, then only root `CLAUDE.md` changed — no file under `.claude/memory/**` or `src/shared/packages/pyforge-scribe/` was touched.

## Spec Change Log

### 2026-07-30 — Crash recovery
A prior dev attempt (bmad-loop attempt 1) crashed after marking this spec `in-review` with all tasks checked, but the working tree was rolled back to `baseline_revision` before the `CLAUDE.md` edit landed — confirmed via clean `git status` and an empty `git diff` against `baseline_revision` at the start of attempt 2. Status reset to `in-progress`; task checkmarks below do not yet reflect the real file state and will be re-verified after implementation actually runs. `<intent-contract>` and `baseline_revision` are unchanged and still consistent with current `epics.md`.

## Review Triage Log

### 2026-07-30 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 0, low 3)
- defer: 1: (high 0, medium 0, low 1)
- reject: 8: (high 0, medium 0, low 8)
- addressed_findings:
  - `low` `patch` `CLAUDE.md` inherited "no trailing newline at EOF" onto its new last line (pre-existing file property, not introduced by this diff, but now sitting under lines this story touches) — appended a trailing newline.
  - `low` `patch` New paragraph named the internal tracking id "Story 1.1" in permanent, always-loaded prose and implied more content auto-loads than actually does — reworded to drop the story reference and precisely describe what the `@import` loads (one-line index entries), matching `MEMORY.md`'s own "one line per entry" convention.
  - `low` `patch` New section gave no pointer to the schema/promotion-workflow doc — added a `.claude/memory/README.md` reference inline.
  - Rejected as noise or factually incorrect against the actual diff/repo state (not re-litigated here): asymmetric H2-vs-bullet structure vs. the pre-existing Auto-memory bullet (blocked by the spec's own "preserve every other section unchanged" constraint); "vacuous" manual-verification method (MEMORY.md is expected-empty pre-Story-1.5, already documented in this spec's Design Notes); missing TODO marker inside the untouched BMAD↔CFE section (would violate the same preserve-unchanged constraint; the deferral is already logged in Design Notes); claim that `implementation-artifacts/` is empty (verified false — the spec file itself lives there); "redundant" wording next to the Auto-memory bullet (two distinct systems, not true redundancy); claim the section lands after "### conda-forge-expert v7.0.0 layout" (verified false — it's the last section in the file, after "Repo-wide pointers"); "first @import ever used" concern (the file already exercises the same `@path` convention for `.claude/docs/bmad-method-llms-full.txt`); missing-import fallback documentation (speculative, mirrors an already-accepted pre-existing risk, not introduced by this story).

### 2026-07-30 — Review pass 2 (fresh follow-up review of the done spec)
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 5: (high 0, medium 0, low 5)
- reject: 7: (high 0, medium 0, low 7)
- addressed_findings:
  - `low` `patch` The existing `@.claude/docs/bmad-method-llms-full.txt` reference (line 37) is backticked — an inert code span, not a live import — so the new line is the file's first *live* `@import` and a future style edit backticking it would silently sever team memory with no failure signal. Added one guard sentence to the `## Team Memory` paragraph ("The import line must stay bare — a backticked `@path` is an inert code span, not an import") and corrected the Design Note that claimed an existing live-import precedent.
- deferred (appended to ledger as NEW entries): loop-home double-load of the imported index; untracked+unignored `claude_hash.txt` orchestrator scratch at worktree root; no automated guard that the `@import` resolves (silent severance on rename/move); team memory wired only for Claude Code (no AGENTS.md/cross-tool pointer, no epic story covers it); bare `@`-tokens in future MEMORY.md entries would be treated as nested imports (authoring rule needed).
- rejected (not re-litigated): EOF-newline deviation (already patched + logged in pass 1); 200-line cap unenforced (already ledgered in pass 1); README "promotion workflow" pointer oversell (README self-labels as not-yet-implemented); adjacent Auto-memory bullet unreconciled/encoded-path mismatch (contract-protected line, pass-1 rejection stands); maintenance label needed at PR open (standing always-on repo rule, noted in run result, not a diff defect); MEMORY.md mtime anomaly with byte-identical content (no consequence); commit-message causal story unverifiable in-tree (Tier-3-until-promoted spec convention working as designed).

## Design Notes

- **De-dup deferral is a literal reading of the AC, not a scope cut.** The epics AC's `When` clause is a conjunction: "this story lands **and** Story 1.5 has populated the two BMAD↔CFE entries." Story 1.5 is downstream in the build order, so the second conjunct is false today and the `Then` (remove/reduce) doesn't yet apply. Leaving the section untouched, decision logged here, is the only option satisfying the AC's precondition without deleting content that exists nowhere else in the checked-in repo.
- A one-line pointer now (instead of leaving it intact) would name a destination that doesn't yet hold the content, and hand-writing that destination would contradict Story 1.5's own requirement that the promotion be produced by `scribe capture --promote` itself, not authored by hand. Revisit at Story 1.5.
- The `@import` line mirrors this file's own existing `@.claude/docs/bmad-method-llms-full.txt` convention. **Precision added in review pass 2:** that line-37 reference sits inside backticks, which makes it an inert code span, not a live import — so this story's line is the file's *first live* `@import` and must stay bare. A guard sentence stating this was added to the `## Team Memory` paragraph so a future style edit doesn't backtick the import and silently sever team memory.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` -- expected: full suite still green (regression check; this story doesn't touch Scribe's code)
- `git diff --stat` -- expected: only `CLAUDE.md` listed

**Manual checks (if no CLI):**
- Open `CLAUDE.md` and confirm the new `## Team Memory` section appears near the end, contains `@.claude/memory/MEMORY.md`, and every other section is byte-identical to before the edit except that one insertion.
- In a fresh Claude Code session rooted at this worktree, ask "list every entry currently in team memory" and confirm the model can answer from context (today: empty `Feedback`/`Project`/`Reference` sections, since no entries have been captured yet).

## Auto Run Result

Status: done (fresh follow-up review pass over the completed story, per the `done` → step-04 route)

**Summary:** Review pass 2 confirmed the Story 1.2 change is sound — the `## Team Memory` section with the `@.claude/memory/MEMORY.md` import loads the index into session context (verified live: the reviewing session had the imported index in context), the `## BMAD ↔ conda-forge-expert integration` section is intact, and no file outside root `CLAUDE.md` changed. One low-severity patch applied: a guard sentence added to the Team Memory paragraph stating the import line must stay bare, because the pre-existing `@.claude/docs/bmad-method-llms-full.txt` reference is backticked (an inert code span, not a live import) — making this story's line the file's first live import, which a future style edit could silently sever by backticking it. The Design Note claiming an existing live-import precedent was corrected accordingly.

**Files changed this pass:**
- `CLAUDE.md` — one sentence appended to the `## Team Memory` paragraph (bare-import guard). Commit `ef470529c2`.

**Review findings breakdown:** intent_gap 0 · bad_spec 0 · patch 1 (low, fixed) · defer 5 (low, appended to `deferred-work.md` as NEW entries: loop-home double-load of the imported index; untracked+unignored `claude_hash.txt` orchestrator scratch; no automated guard that the import resolves; team memory wired for Claude Code only, no cross-tool pointer and no epic story covering it; bare `@`-tokens in future entries would nest-import) · reject 7 (incl. two duplicates of pass-1-adjudicated findings: EOF newline, 200-line cap).

**Verification:** `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` → 18 passed; `git diff --stat` this pass → only `CLAUDE.md`; cumulative diff since `baseline_revision` → only `CLAUDE.md` tracked.

**Residual risks:**
- When this branch is PR'd to `rxm7706/local-recipes`, the change is outside `recipes/**` — the opener must add the `maintenance` label (`gh pr edit <n> --repo rxm7706/local-recipes --add-label maintenance`) per the always-on CI gate. `pixi.toml` untouched, so the `environment.yaml` sync gate does not apply.
- The five deferred items above are real but out of this story's edit-only-`CLAUDE.md` boundary; the ledger owns them.

