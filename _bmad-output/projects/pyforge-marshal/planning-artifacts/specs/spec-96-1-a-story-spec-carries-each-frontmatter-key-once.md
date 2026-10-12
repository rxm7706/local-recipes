---
title: "96.1: A story spec carries each frontmatter key once"
type: 'fix'
created: '2026-10-11'
status: 'done'
baseline_revision: 'ceca8770438a8ff72ad3cfd711c0c5c8e9cd1d22'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-91-1-a-corrupt-environment-yaml-never-lands.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-94-1-the-review-gate-orders-review-entries-by-their-real-commit-times.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-42-1-a-repeated-frontmatter-key-in-a-story-spec-turns-detectors-red.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_ruff_format.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_environment_yaml.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/dispatch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_harness_done.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_flag_mandate_overrides.py
  - _bmad/custom/bmad-build-auto.toml
  - _bmad/custom/bmad-build.toml
---

<intent-contract>

## Intent

**Problem:** a dispatched `bmad-build-auto` session writes a story spec's frontmatter key a second time instead of
replacing the line that holds it. The repeats reach `main`, where readers disagree about them: PyYAML keeps the last
occurrence (bmad-loop, doctor's `deferred-work`), and marshal's `_frontmatter_scalar`
(`core/dispatch_harness_done.py:83`, its loop at `:99`) keeps the first. Line numbers below are at `a21524e9d6`.

**The evidence (measured on `main` at `a21524e9d6`):**
- **The count.** A PyYAML `SafeLoader` whose mapping constructor records repeated keys finds 40 repeats in 37 of the
  1,407 tracked story specs with frontmatter: `followup_review_recommended` 29 times and `review_loop_iteration` 11
  times. By project: marshal 15 (13 files), steward 7 (6), herald 6 (6), doctor 5 (5), mason 4 (4), warden 3 (3);
  atlas and scribe none. A line scan of top-level keys agrees and also reads the 46 frontmatter blocks PyYAML cannot
  parse (memlogs with an unquoted colon): none of the other 900 tracked frontmatter files under `_bmad-output/` and
  `docs/` repeats a key, and neither do the 780 under `.claude/`, `src/`, `docsite/`, `_bmad/` and `scripts/`.
- **Who wrote them.** For each repeat, the first commit whose copy of the spec holds the key twice is on a
  `dispatch/pyforge-*` branch: `marshal: supervisor finalize (Story 28.24)` 18 times, `wip: <key> (auto-checkpoint)`
  16 times, and the session's own step-04 commit 6 times (for example `3070c2256b`, `c5d4515a8b`, `31051e9d95`). Those
  commits record the session's edits; marshal's code never writes these keys (it only reads them), and bmad-loop's
  writer (`verify.set_frontmatter_field`) replaces in place behind a YAML oracle. The session is following the
  installed step files: `step-01-clarify-and-route.md:31` ("write `followup_review_recommended: false` now ... set
  `review_loop_iteration` to `0`"), `step-04-review.md:70` ("increment it by 1, and write it back") and `:107` ("Set
  `{spec_file}` frontmatter `followup_review_recommended`"). The same file guards its list key, `deferred`: "never add
  a second `deferred:` key" (`:84`) and a full parse afterwards (`:95`). No spec repeats `deferred`.
- **Which copy the writer meant.** `git blame --line-porcelain` dates each occurrence. In 32 of the 40 repeats the
  session's write is the first occurrence (it inserted the new line above the old one), in 7 it is the last, and in 1
  both arrived in one commit. In 36 the two values are equal. Four hold different values:
  - herald 29.2 `followup_review_recommended`: `true` (line 6, written by the review pass in `6f45b96f11`), then
    `false` (line 10, from the spec at mint). Marshal reads `true`, and `DW-FRR-29-2` in herald's ledger carries the
    follow-up review it recommends; PyYAML readers read `false`.
  - doctor 21.7 and doctor 41.6 `review_loop_iteration`: `0`, then `1` (the `1` written later, `5cde5616c0` and
    `93befa6c7c`).
  - steward 43.7 `review_loop_iteration`: `1`, then `0`, both first committed in `4d68b9c749`, so history cannot say
    which came last.
- **It is still happening.** Herald 37.1's repeat was removed by hand on 2026-10-11, and steward 91.1's spec on
  `dispatch/pyforge-steward/91.1` already repeats `review_loop_iteration` (`0`, then `1`).

**Approach.** Three parts, all in marshal's lane. Marshal wields `bmad-build-auto` through `marshal factory dispatch`,
and the installed step files are never edited (Stories 74.3 and 87.11 put marshal's instructions to the build skills in
`_bmad/custom/`).
1. **Tell the writer.** One persistent fact in `_bmad/custom/bmad-build-auto.toml` and one in
   `_bmad/custom/bmad-build.toml`: a story spec's frontmatter carries each key once; to set a key, replace the line
   that holds it, and add a line only when the key is absent; after every frontmatter write, parse the block and
   confirm no key appears twice, as step-04 already does for `deferred`. Both facts cite this story.
2. **Collapse before verification.** A new pre-verify step, beside Stories 83.9/83.15's ruff step and Story 91.1's
   `environment.yaml` step, wherever those run: the supervisor's `_run_and_journal_verification`
   (`dispatch_supervisor/__main__.py:2452`, the two calls at `:2469` and `:2481`) and the land-only verify
   (`cli/dispatch.py:1195`-`:1206`). For each tracked story spec the story changed against `origin/main`
   (`_bmad-output/projects/*/planning-artifacts/specs/spec-*.md`), it finds every top-level frontmatter key that
   appears more than once and keeps the occurrence git wrote last, read through `VcsPort.line_blame_facts` (Story
   89.1's per-line committer times, fixed by Story 94.1; an uncommitted line, the all-zero sha, counts as newest).
   Occurrences that all hold one value collapse to the newest one. Two occurrences with different values and the same newest time are
   ambiguous, so the step changes nothing in that spec and verification refuses, naming the spec and the key. The
   kept line stays in place, the others are removed, and the body below the fence is byte-identical. The edit is
   accepted only if the new block parses as a mapping with no repeated key, every key that was not repeated keeps its
   value, and each repeated key holds the value of the occurrence that was kept. Otherwise the step refuses. It
   commits the changed specs as `marshal: collapse repeated story-spec frontmatter keys (Story 96.1)` and journals a
   `dispatch-spec-frontmatter` INTENT/OUTCOME pair naming each spec and key.
3. **Clean what is on `main`.** Every tracked story spec that repeats a key at the story's base (the 37 above, plus
   any landed since, steward 91.1 among them if it lands first) is collapsed by the same rule, with history read
   from `main`: herald 29.2 keeps `true`, doctor 21.7 and 41.6 keep `1`. Where both occurrences arrived in one commit
   and hold different values (steward 43.7), the last line is kept, because that is what PyYAML readers already read.
   The memlog names that tie. Each cleaned file gets an `event` entry on the memlog of the Spec that governs it: the
   Spec its Binding names, or the station Spec where it names none. The entry lists the key, both values, the value
   kept and the reason.

Doctor's detector, doctor Story 42.1, is gated on this story because it reds any repeat left on `main`.

Ledger key: `96-1-a-story-spec-carries-each-frontmatter-key-once`.
Type / Effort / Deps: fix / M / — (doctor Story 42.1 waits on this story through its own `blocked` ledger row).

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-161 (← `spec-marshal-single-story-dispatch` CAP-3): verification
  is marshal's, and Stories 83.9, 83.15 and 91.1 run their pre-verify steps under it. CAP-169 (← CAP-11) and CAP-275
  read `followup_review_recommended` from the spec this step collapses. No CAP is minted and no `SPEC.md` text
  changes.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag: a spec whose keys mean two things is
  the defect, and a flag would keep it reachable.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-11 (duplicate frontmatter keys in story
  specs). Operator ask 2026-10-11, verbatim: "Do this task here: Stop story specs gaining duplicate frontmatter keys".

## Acceptance Criteria

- **AC1 — The writer is told.** `_bmad/custom/bmad-build-auto.toml` and `_bmad/custom/bmad-build.toml` each carry one
  `[workflow].persistent_facts` entry that says a story spec's frontmatter key is replaced in place, never added a
  second time, and that the block is parsed for repeated keys after every write. A meta-test beside
  `tests/meta/test_flag_mandate_overrides.py` pins the fact in both files under the table each skill's
  `customize.toml` declares. `PYTHONPATH="$PWD/_bmad/scripts:$PYTHONPATH" python _bmad/scripts/render_skill.py
  --project-root "$PWD" --skill .claude/skills/bmad-build-auto` (and `bmad-build`) prints a render path, not a HALT,
  and the rendered facts contain the text. No file under `.claude/skills/` changes.
- **AC2 — A repeat is collapsed to the newer write.** In a real git repository with a bare `origin`, a story spec
  whose base reads `followup_review_recommended: false` gains a commit that inserts `followup_review_recommended: true`
  above it (herald 29.2's shape). The pre-verify step leaves one line reading `true` where that line was, removes the
  `false` line, keeps the body byte-identical, commits that one spec with the Story 96.1 subject and journals the
  pair. The mirror shape (`review_loop_iteration: 0` at the base, `1` appended below it, doctor 21.7's shape) keeps
  `1`. Three occurrences `0`, `1`, `2` written by successive commits keep `2`.
- **AC3 — Equal values collapse quietly.** Two occurrences of one value (marshal 87.7's shape, a repeated pair of
  keys) collapse to one line each; every other key's value is unchanged under `yaml.safe_load`.
- **AC4 — An ambiguous repeat refuses.** Two occurrences with different values and the same newest commit time (one
  commit wrote both, steward 43.7's shape) leave the spec unchanged. The journal OUTCOME reads `ok: false` with the
  spec and the key, and verification refuses under the next free `MRS-GATE-0nn` code (`MRS-GATE-022` at
  `a21524e9d6`; the dev names the code used in the Spec Change Log), naming the spec and the key. Nothing lands
  (AD-8). The same holds when the trial edit fails the YAML check.
- **AC5 — Nothing to do, nothing done.** A story that changes no story spec, or whose changed specs repeat no key,
  runs the step without a commit or a journal pair, as Story 91.1's step does for an unchanged file. A story spec
  under another project's `planning-artifacts/specs/` is handled the same way as one under its own.
- **AC6 — The step runs wherever verification runs.** The supervisor's `_run_and_journal_verification` and the
  land-only verify in `cli/dispatch.py` both call it, after the ruff and `environment.yaml` steps and before any
  verify command. A test for each caller mirrors Story 91.1's.
- **AC7 — `main` is clean.** After the story, the duplicate-key scan (the same loader doctor Story 42.1 uses, run as a
  test over the tracked tree) reports no repeated key in any tracked story spec. The four specs with differing values
  read: herald 29.2 `followup_review_recommended: true`, doctor 21.7 and 41.6 `review_loop_iteration: 1`, steward
  43.7 `review_loop_iteration: 0`. Marshal's `followup_review_recommended()` and `yaml.safe_load` agree on every
  tracked story spec. Each cleaned file has its memlog `event` entry, and `deferred-work-check` and marshal's
  `test_no_done_and_flagged_spec_is_uncarried_across_the_eight_projects` stay green (`DW-FRR-29-2` still carries
  herald 29.2).
- **AC8 — Mutation.**
  - Remove the pre-verify call: AC2's fixture lands with the repeat, and its test fails.
  - Keep the last occurrence instead of the newest write: AC2's herald 29.2 case keeps `false`, and its test fails.
  - Let the writer add a line again (a fixture session edit that appends `review_loop_iteration: 1` below an existing
    `review_loop_iteration: 0`, with the step removed): AC2's test fails.
  - Drop the fact from either TOML: AC1's meta-test fails.
  - Collapse an ambiguous repeat instead of refusing: AC4's test fails.

## Boundaries & Constraints

**Always:**
- Edit only the frontmatter lines of a repeated key. Every other line, the fence and the body stay byte-identical.
- Judge "newest" only through `VcsPort.line_blame_facts` (git owns repository facts, AD-33). A line whose time cannot
  be read makes the repeat ambiguous, and the step refuses; it never counts as oldest.
- Read every verdict from the exit code, never through a pipe.
- Reconcile every governed path the change touches on the memlogs of the Specs that govern it, then stamp those Specs
  scoped: `spec-pyforge-marshal` and every co-governor `spec-surface-check` names (`spec-pyforge-core` co-governs
  station `src/`) (AGENTS.md pre-PR item 5).

**Never:**
- Never edit a file under `.claude/skills/` (installer-owned; `bmad-method install --action update` overwrites it).
- Never round-trip a spec through a YAML serializer; the edit is line removal checked by a parse.
- Never change a `status:`, `landing_review:` or ledger key to get past a gate, and never hand-edit a `SPEC.md` or a
  `sprint-status-ledger.yaml`.
- Never change `_frontmatter_scalar`, the harness-done gate, `MRS-GATE-015` or the ruff and `environment.yaml` steps
  here.

**Residual risk:**
- A session can still write a repeat between checkpoints; the step and doctor's detector catch it before it lands,
  but a run's own harness-done gate reads the worktree spec before the step runs. The measurement shows that read
  (first occurrence) is the session's newer write in 32 of 40 repeats.
- A hand-landed branch skips dispatch's pre-verify; doctor Story 42.1's detector reds it in `detectors-ci`.

## I/O & Edge-Case Matrix

| Shape in a story-changed spec | Blame | Result |
|---|---|---|
| one key twice, same value | any | one line kept (the newest); no refusal |
| one key twice, different values | one occurrence newer (or uncommitted) | the newer value kept, in place |
| one key three times, `0`, `1`, `2` by successive commits | distinct times | `2` kept |
| one key twice, different values | same commit | unchanged; `MRS-GATE-022`; nothing lands |
| a time cannot be read | — | unchanged; `MRS-GATE-022` |
| trial edit fails the YAML check | — | unchanged; `MRS-GATE-022` |
| no repeated key, or no story spec changed | — | no commit, no journal pair |
| a nested key repeated inside a block (e.g. under `flag:`) | — | not this step's (top-level only); doctor's detector reports it |

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-marshal` CAP-161 (← `spec-marshal-single-story-dispatch` CAP-3), with
  CAP-169 (← CAP-11) and CAP-275. No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-11 (duplicate frontmatter keys in story
  specs) entry.
- Architecture: AD-4, AD-8 and AD-33, unchanged.
- Epic: Epic 96 (new). The behaviour spans the verification of Epics 22 and 83 and the build-skill facts of Epics 74
  and 87, which are `done`. `epic-96` and `epic-96-retrospective` are minted with it.
- Ledger key: `96-1-a-story-spec-carries-each-frontmatter-key-once`.
- Ledger status at mint: `backlog`.
- Deps: — . Doctor Story 42.1 (`42-1-a-repeated-frontmatter-key-in-a-story-spec-turns-detectors-red`) is minted
  `blocked` on this story, a cross-station gate the operator flips once this story is `done` on `main` (marshal's
  `Deps:` parser is station-local).
- Surface: `marshal-policy.toml` `[epic_surfaces]."96"`, added with this mint: the default surface, every tracked
  story spec under `_bmad-output/projects/*/planning-artifacts/specs/`, both build-skill customization files and
  every Spec memlog.
- Spec: the `spec-pyforge-marshal` memlog records the ask verbatim, the design decisions and this mint.
- Minted 2026-10-11 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, with AC1-AC8's tests (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlogs and scoped stamps.
- `PYTHONPATH="$PWD/_bmad/scripts:$PYTHONPATH" python _bmad/scripts/render_skill.py --project-root "$PWD" --skill .claude/skills/bmad-build-auto` and the same for `.claude/skills/bmad-build` — expected: a render path, and the rendered facts include this story's fact.
- `pixi run --frozen -e pyforge-guild deferred-work-check` and `pixi run --frozen -e pyforge-guild story-status-check` — expected: exit 0.
- The five mutations of AC8 — expected: each fails its named test. Restore each.
- `git diff origin/main...HEAD -- .claude/skills` — expected: empty.

## Named, not fixed here

- **Marshal's first-occurrence reader.** `_frontmatter_scalar` keeps the first occurrence and PyYAML keeps the last.
  Once no repeat survives verification and doctor's detector guards `main`, the two have nothing to disagree about, so
  the reader is unchanged.
- **The repeat inside a nested block.** The step collapses top-level keys only. None exists today (the loader scans
  every depth); doctor's detector reports one if it appears.
- **Other frontmatter families.** No Dream, `SPEC.md`, PRD, spine, `epics.md` or memlog repeats a key today, and no
  harness writes their keys, so the step reads story specs only.

## Spec Change Log

- 2026-10-11: implementation — `dispatch_spec_frontmatter` pre-verify step (MRS-GATE-022), build-skill persistent facts, 37 story specs collapsed on main; verified with `pyforge-marshal-test`, `pyforge-deps-test`, `spec_surface_reconcile.py`, `spec-surface-check`.
- 2026-10-11: minted from the operator's ask "Do this task here: Stop story specs gaining duplicate frontmatter keys".
  The repeat is collapsed to the occurrence git wrote last, not to the last line: the session put its write above the
  old line in 32 of 40 repeats, and herald 29.2's last line is the stale `false` its review pass meant to replace
  with `true`.

## Review Triage Log

- No review has run yet.
