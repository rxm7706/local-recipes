<!-- Promoted from implementation-artifacts/ to tracked specs on 2026-08-02. Recovered via PR #168 (d68187f4b3, 2026-07-31) after a bmad-loop dev-session timeout reset the 1-3 worktree branch and discarded the original commit from reachable history; a follow-on Story 1.4 session traced and escalated the recovery (see implementation-artifacts/bmad-dev-auto-result-1-4-pointer-stub-write-back-idempotent-re-invocation.md). Status corrected done->backlog->done drift found and fixed 2026-08-02: code has been on main since 2026-07-31 (47/47 tests passing, independently verified), but all three status trackers still read backlog until this session. -->
---
title: 'Promotion workflow — proposal-then-confirm, team-voice rewrite (Story 1.3)'
type: 'feature'
created: '2026-07-30'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
final_revision: 'd68187f4b3'
context: []
warnings: ['oversized']
baseline_revision: '491f3ec45b6a9db0a4d1b8311efde1c97ea3a96e'
---

<intent-contract>

## Intent

**Problem:** `scribe capture` only writes direct, verbatim entries (Story 1.1). There is no way to move a team-relevant entry already sitting in a developer's user-local auto-memory into checked-in `.claude/memory/` without hand copy-pasting it — losing the review/rewrite step FR-3/FR-4 require.

**Approach:** Add `promote.py`: scan the user-local auto-memory directory, classify each entry (`team-relevant` / `personal` / `already-promoted` / `stale`), mechanically rewrite `team-relevant` ones into team voice, print a structured proposal, and — only on explicit interactive confirmation — write the promoted file(s) + `MEMORY.md` line(s) by reusing `capture()`'s existing locked write path. Wire this to a new `--promote` flag on the existing `scribe capture` command.

## Boundaries & Constraints

**Always:**
- `--promote` is a new flag on the existing `capture` command, mutually exclusive with `--type`/`--text` (neither required when `--promote` is set).
- Reads only the user-local source directory (default `Path.home()/".claude"/"projects"/<encoded-cwd>/"memory"`, overridable via `--source`); writes only under `.claude/memory/**`, and only via `capture()` (extended, not duplicated) — no direct filesystem writes in `promote.py`.
- Zero writes under `.claude/memory/` until the user answers yes to an interactive `typer.confirm()` prompt (testable via `CliRunner(input=...)`); declining prints a cancellation notice and exits `0` with nothing written.
- Classification priority: `promoted: true` (either frontmatter shape, any indentation) → `already-promoted`; unparseable frontmatter or a backtick-quoted, clearly-repo-relative path (`src/`, `recipes/`, `docs/`, `.claude/`, `_bmad/`, `_bmad-output/`, `pixi.toml` prefixes only) that doesn't exist under the repo root → `stale`; `description` matching a fixed personal-tone keyword list (`terse`, `terseness`, `tone`, `verbosity`, `communication style`, `emoji`) → `personal`; else → `team-relevant`.
- Team-voice rewrite (team-relevant entries only, mechanical/regex, no LLM/network call — AD-6): strip `"I prefer X"`/`"I want X"` first-person framing, drop `"(the )?user prefers"` framing, drop parenthetical asides containing a bare git-short-hash token (7–40 hex chars). Everything else — paths, commands, backticked identifiers, `**Why:**`/`**How to apply:**` labels — is left untouched.
- Promoted slug = source filename with its `<type>_` prefix dropped and `_`→`-` (legacy spec Q9), collision-checked the same way `capture()` already checks slugs.
- Source frontmatter reader must tolerate both shapes actually present on disk: flat `type: feedback` and nested `metadata:\n  type: feedback` (verified: 31 vs 47 of the 78 real files in this project owner's own auto-memory corpus use each shape respectively).

**Block If:** none — the ambiguities below (path-encoding, rewrite scope) are resolved in Design Notes rather than left open.

**Never:**
- Do not implement pointer-stub write-back or the idempotent-skip-on-reinvocation proof — both are Story 1.4. The source user-local file must be byte-for-byte unchanged after a confirmed promotion in this story.
- Do not call any LLM or network service for classification or rewriting (AD-6).
- Do not touch `CLAUDE.md`, `.claude/skills/`, `.claude/scripts/`, `recipes/`, `_bmad/`, `_bmad-output/` outside this project's own artifacts, or any other worktree/`main`.
- Do not use the real `~/.claude/projects/.../memory/` tree in any test — `tmp_path` only, matching the existing test convention.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | one team-relevant source entry, confirm "y" | proposal printed; file lands under `.claude/memory/<type>/`, `MEMORY.md` gains its index line, source untouched | No error expected |
| Decline | same as above, confirm "n" | exit 0, zero files changed under `.claude/memory/` | No error expected |
| Already-promoted | source entry has `promoted: true` (either shape) | classified `already-promoted`, excluded from proposal | No error expected |
| Personal | `description` contains "terse" | classified `personal`, excluded from proposal | No error expected |
| Stale | body backtick-references a `src/...` path that doesn't exist under repo root | classified `stale`, flagged, excluded | No error expected |
| Malformed frontmatter | file missing a closing `---` or a `type` | classified `stale` with a parse-failure reason, excluded | Never crashes the scan |
| Mixed shapes in one source dir | one flat-`type:` file + one nested-`metadata:` file | both classified correctly | No error expected |
| Missing source dir, no `--source` override | default derived path does not exist | `ValueError` before any read | CLI catches, prints message, exits 2 |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/promote.py` (NEW) — scan/classify/draft/apply; `default_user_local_root()`, `PromotionProposal`/`ClassifiedEntry` dataclasses, `classify_and_draft()`, `apply_promotion()`
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/capture.py` — extend `capture()` with optional `slug`/`description` keyword overrides (default `None` preserves current behavior byte-for-byte) so `promote.py` reuses the existing locked, no-clobber write path instead of duplicating it
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` — add `--promote`/`--source` options to `capture_cmd`; make `--type`/`--text` optional when `--promote` is set; print the proposal; gate the write behind `typer.confirm()`
- `src/shared/packages/pyforge-scribe/tests/unit/test_promote.py` (NEW)
- `src/shared/packages/pyforge-scribe/tests/unit/test_cli.py` — extend with `--promote` CliRunner cases
- `.claude/memory/README.md` — "Promotion workflow (arrives Story 1.3)" section — flip to a short usage note now that it's implemented
- `_bmad-output/planning-artifacts/epics.md` (L116-133) — Story 1.3's source ACs
- `~/.claude/projects/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/memory/*.md` — reference only (confirms both frontmatter shapes in the wild; zero files currently carry `promoted: true`); never read by tests

## Tasks & Acceptance

**Execution:**
- [x] `capture.py` -- add optional `slug: str | None = None, description: str | None = None` params to `capture()` -- lets `promote.py` reuse the atomic locked write path
- [x] `promote.py` -- new module implementing classification, team-voice rewrite, proposal dataclasses, and confirmed-write application -- realizes FR-3/FR-4
- [x] `cli.py` -- `--promote`/`--source` flags on `capture`; print proposal; `typer.confirm()` gate before calling `apply_promotion()`
- [x] `test_promote.py` -- unit tests for all four classifications (incl. both frontmatter shapes, malformed input) and the rewrite rules
- [x] `test_cli.py` -- CliRunner cases: confirm-yes, confirm-no, mixed classifications in one run
- [x] `.claude/memory/README.md` -- update the Story 1.3 section to describe the shipped `--promote` flag

**Acceptance Criteria:**
- Given a developer runs `scribe capture --promote` against a source directory containing one team-relevant entry, when classification completes, then it prints a structured proposal (target path, full rewritten content, `MEMORY.md` line) and performs zero writes until confirmed (FR-3).
- Given the user confirms, when the write executes, then exactly the proposed file lands under `.claude/memory/<type>/`, `MEMORY.md` gains the matching index line, and the source user-local file is byte-for-byte unchanged (FR-7 boundary for this story).
- Given the user declines, when the command exits, then exit code is `0` and no file under `.claude/memory/` changed.
- Given an entry whose `description` matches a personal-tone keyword, when classified, then it is `personal` and excluded from the proposal, not silently promoted.
- Given an entry already carrying `promoted: true` in either frontmatter shape, when classified, then it is `already-promoted` and excluded.

## Design Notes

- **Path-encoding for the default `--source`** is Claude Code's undocumented `~/.claude/projects/<encoded-path>/` scheme. Empirically (verified against this repo's own `~/.claude/projects/` listing, including dotted worktree segments like `.bmad-loop` → `--bmad-loop`): replace every character in the absolute cwd path that isn't `[A-Za-z0-9]` with `-`. Implemented as one small helper; `--source` is the escape hatch if this heuristic is ever wrong or Claude Code's scheme changes.
- **Team-voice rewrite is mechanical, not LLM-driven**, by design: AD-6 requires zero network calls by default for `scribe capture`, and the architecture's Capability Map assigns FR-3/FR-4 to `promote.py` under AD-2 only — `LLMAdapter` is scoped exclusively to `recall.py` (Wave 2). "Drop incident-specific anecdotes" is narrowed to parenthetical asides containing a bare git-short-hash token (7–40 hex chars) — the concrete pattern this repo's own entries actually use (e.g. this project's own `d43899c1cb` reference) — rather than general anecdote detection. An imperfect mechanical rewrite is caught at the human confirm step, not silently shipped.
- **Personal-tone keyword list is deliberately small and literal**, validated against the one concrete worked example in both the epics AC and the legacy spec ("a terseness/tone preference") and against a real entry in this exact corpus (`feedback_no_courtesy_comments.md`, whose description contains "terse").
- **Stale-path check is scoped to a known prefix allow-list** (`src/`, `recipes/`, `docs/`, `.claude/`, `_bmad/`, `_bmad-output/`, `pixi.toml`) to bound false positives from unrelated backticked text in prose.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` -- expected: full suite green (existing 18 tests + new `test_promote.py`/`test_cli.py` cases)
- `git diff --stat` -- expected: only the files in Code Map changed

**Manual checks (if no CLI):**
- From the repo root: `pixi run -e pyforge-scribe scribe capture --promote --source <tmp-dir-with-sample-entries>`, answer the confirm prompt, and inspect that only the proposed file + `MEMORY.md` changed.
