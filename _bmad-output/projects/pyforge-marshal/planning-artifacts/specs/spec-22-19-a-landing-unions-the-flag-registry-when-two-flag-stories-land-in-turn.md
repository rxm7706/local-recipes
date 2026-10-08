---
title: "22.19: A landing unions the flag registry when two flag stories land in turn"
type: 'fix'
created: '2026-10-07'
status: 'in-review'
baseline_revision: '9c29bda7ec3d5c8a108a2f511aa1d29e4a090c37'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-22-18-a-landing-heals-a-spec-surface-baseline-conflict-by-re-stamping-on-main-s-baseline.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/dispatch_landing.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land_heal.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py
  - src/platform/config/flags.json
  - src/platform/config/flag-overlays.json
  - src/shared/packages/pyforge-core/tests/unit/test_flags.py
  - src/platform/tests/test_openfeature_file_flags.py
  - scripts/flag_gate_check.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** two flag stories cannot land one after the other. The second landing conflicts on the flag registry, and
the CAP-4 heal escalates it with `MRS-DISP-038`, so a human has to merge `origin/main` into the branch.

- **Why the registry conflicts.** Every flag story registers its key in the same four tracked files, always by
  appending at the same place:
  - `src/platform/config/flags.json`: a new key at the end of `flags`.
  - `src/platform/config/flag-overlays.json`: one line at the end of each environment object (`dev`, `staging`,
    `production`).
  - `src/shared/packages/pyforge-core/tests/unit/test_flags.py`: an entry at the end of the `_SHIPPED_CLOCKS`
    (about :873), `expected` (about :940) or `per_environment` (about :946) dict literal.
  - `src/platform/tests/test_openfeature_file_flags.py`: an entry at the end of the `_SHIPPED_BOOLEANS` dict literal
    (about :588).

  When `main` gained another flag after the branch's merge base, both sides inserted at the same point, so every one
  of these files conflicts.
- **Why the heal refuses.** `core/dispatch_landing.py` `is_mechanical_conflict_path` (about :173) treats only Spec
  memlogs, the landing project's own sprint and deferred-work ledgers and `.claude/memory/MEMORY.md` as mechanical,
  and Story 22.18 adds the spec-surface baseline. `unknown_conflict_paths` (about :202) returns the four registry
  files, and `dispatch_land.py` (about :1600-:1625) refuses with `MRS-DISP-038`.
- **The live cases.** Both happened on 2026-10-07.
  - Warden 14.3 (PR #1903, run `pyforge-warden-20261007T093623012Z-77c754d3`) was refused with `MRS-DISP-038`
    "unknown conflict path(s) (scripts/.spec-surface-baseline.json, src/platform/config/flag-overlays.json,
    src/platform/config/flags.json, src/shared/packages/pyforge-core/tests/unit/test_flags.py)". Herald 29.1 and
    steward 74.2 had landed first.
  - Herald 29.1 needed an operator merge before that (`e5432aa8d6` on `dispatch/pyforge-herald/29.1`). It unioned
    `flags.json` and `flag-overlays.json` key by key, `main`'s keys first and then the branch's, and kept both entries
    in `test_flags.py`'s `per_environment`.

**Approach:** the heal unions the registry the way that operator did, and re-runs the flag checks on the healed tree
before it pushes.

- `core/dispatch_landing.py` classifies the four registry paths as mechanical. They become one named constant there,
  and only these exact repo-relative paths qualify.
- A pure function there resolves each JSON file. It takes the merge-base, `main` and branch texts and returns a
  three-way, key-wise union of the parsed documents, or a refusal that names the key it cannot resolve.
- A second pure function there resolves each Python registry. It takes git's own three-way merge of the file, with
  diff3 conflict markers, and returns the resolved text or a refusal. The heal gets the marked text through the VCS
  port, for example with `git merge-file -p --diff3` over the three texts.
- `_resolve_mechanical_conflicts` puts both kinds of result in the same `resolutions` map that `_try_union_heal`
  already merges with. One merge resolves every mechanical conflict: memlogs, ledgers, team memory, Story 22.18's
  baseline and the registry.
- After that merge, and after Story 22.18's re-stamp when the baseline also conflicted, `_try_union_heal` runs a
  healed-tree check and only then pushes. `execute_dispatch_land` passes the check in as a callable, the same way
  Story 80.1 passes `await_checks` and Story 22.18 passes the reconcile. The heal never runs a subprocess itself. The
  check runs `flag-gate-check` and the two flag test modules in the worktree. When all three pass, the heal pushes
  once, waits for the healed head's checks (Story 80.1) and retries the merge.

Ledger key: `22-19-a-landing-unions-the-flag-registry-when-two-flag-stories-land-in-turn`.
Type / Effort / Deps: fix / M / S-22.18 (the shared heal path, its single push and its baseline handling: a flag
landing that waits behind another also conflicts on the baseline, as warden 14.3 did).

### The union rules

- **JSON (`flags.json`, `flag-overlays.json`).**
  - Merge each file three-way against the merge base, two levels deep. The top-level members are `flags` in
    `flags.json` and one member per environment in `flag-overlays.json`. Each of those is an object whose own members
    (a flag definition, an overlay variant) are compared as whole parsed values.
  - At each level, a key changed on only one side takes that side's value, and a deletion counts as a change. A key
    both sides set to an equal value takes that value. A key both sides added or changed to different values is not
    resolved. The heal escalates the file with `MRS-DISP-038`, naming the file and the dotted key (for example
    `src/platform/config/flags.json (key flags.pyforge.warden.fix_x)`).
  - Order: `main`'s keys in `main`'s order, then each key only the branch added, in the branch's order.
  - Write the result as `json.dumps(doc, indent=2) + "\n"`. On 2026-10-07 that form reproduced both files byte for
    byte, and it is the form `pyforge.core.flags.render` emits (`flags.py` about :364).
  - A side that does not parse, a top-level member that is not an object, or a `main` or branch text that does not
    round-trip byte for byte through that form escalates the file. The heal never reformats a file.
- **Python (`test_flags.py`, `test_openfeature_file_flags.py`).** A file resolves only when every conflict hunk passes
  all of these checks:
  - The hunk's merge-base section is empty, so both sides only added lines.
  - Each side's section parses as one or more complete dict entries: `ast.parse("{\n" + section + "\n}",
    mode="eval")` yields an `ast.Dict`.
  - The hunk lies inside one dict literal assigned to one of that file's named targets. In core's `test_flags.py`
    the targets are `_SHIPPED_CLOCKS`, `expected` and `per_environment`; in the platform module the target is
    `_SHIPPED_BOOLEANS`.

  The resolution keeps `main`'s section, then the branch's, verbatim. The resolved file must parse, and no named dict
  may hold a key twice. If both sides added the same key with different text, the heal escalates and names the key.
  Any other hunk shape escalates the file with `MRS-DISP-038`, such as a changed or removed line, a comment edited on
  both sides, or an entry outside the named dicts.
- **The healed-tree check.** It runs in the dispatch worktree on the merged commit, before anything is pushed, and
  only when the resolutions touched a registry path. Each command's exit code is read directly:
  - `pixi run --frozen -e pyforge-guild flag-gate-check`. Exit 0 passes and may carry warnings; 1 or 2 fails.
  - `pixi run --frozen -e pyforge-core pytest src/shared/packages/pyforge-core/tests/unit/test_flags.py -q`.
  - `tests/test_openfeature_file_flags.py`, run with the interpreter and working directory that
    `scripts/platform-ci-local.sh`'s test stage uses: the `platform-ci-test` env, cwd `src/platform`, with
    `PYTHONSAFEPATH` unset.

  A non-zero exit, a timeout, or an env that will not run refuses the landing with `MRS-DISP-038`. The finding names
  the command and its exit code, and carries the gate's own FAIL lines, bounded. Nothing is pushed, and the merge is
  not retried.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-137 (← `spec-marshal-drain-self-resolution` CAP-3; Story 28.20,
  the CAP-4 heal: mechanical land-conflict union, unknown paths escalate by name), on CAP-162's dispatch landing (←
  `spec-marshal-single-story-dispatch` CAP-4; Story 22.4). It reuses CAP-284's wait for the healed head's checks
  (Story 80.1). It closes a gap between shipped behaviours, so it needs no new CAP.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag. This story changes no key, value or
  rule of the one flag tree (canopy:AD-11); it only merges two sides' additions to it.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-07 (flag registry conflict).

## Acceptance Criteria

- **Two different keys land.** Given a real-git fixture where, since the merge base, `main` added flag key K1 and the
  branch added a different key K2, each to all four registry files in the shapes above (the herald 29.1 / warden 14.3
  shape), When the landing's first `forge.merge_pr` fails and `try_heal_dispatch_land_merge` runs with a passing
  healed-tree check passed in, Then:
  - one merge of `origin/main` into the branch resolves all four files;
  - `flags.json` and each environment of `flag-overlays.json` hold K1 then K2, written as
    `json.dumps(doc, indent=2) + "\n"`;
  - each named dict holds both entries, `main`'s first;
  - the check is called once, on the merged commit, before the push;
  - the heal pushes once and retries the merge with the pushed head's sha;
  - no `MRS-DISP-038` is raised.
- **Same key, different values.** Given both sides added the same key to `flags.json` (or to one environment of
  `flag-overlays.json`) with different values When the heal runs Then it escalates with `MRS-DISP-038`, naming the
  file and the key. No merge is committed, nothing is pushed, and `forge.merge_pr` is not called again.
- **A hunk that is not an addition.** Given a conflict hunk in `test_flags.py` that is not a pure addition of dict
  entries (both sides edited the same existing entry, or the comment above `per_environment`) When the heal runs
  Then it escalates with `MRS-DISP-038` naming `test_flags.py`, and nothing is merged.
- **A failing check.** Given the healed-tree check returns a finding (`flag-gate-check` or a test module failed) When
  the heal has committed its merge Then the landing is refused with `MRS-DISP-038` naming the command. Nothing is
  pushed, and the merge is not retried.
- **No check passed in.** Given no healed-tree check is passed to the heal (a direct caller, as with
  `await_checks=None`) When the registry conflicts Then the heal escalates the registry files with `MRS-DISP-038` as
  it does today, and resolves nothing.
- **A non-canonical JSON side.** Given a `main` or branch `flags.json` that does not round-trip byte for byte through
  `json.dumps(doc, indent=2) + "\n"` When the heal runs Then it escalates that file and never reformats it.
- **Registry and baseline together.** Given the registry and `scripts/.spec-surface-baseline.json` both conflict (the
  warden 14.3 shape) When the heal runs with Story 22.18's reconcile and the healed-tree check both passed in Then
  one merge resolves every path. The re-stamp runs, then the check, then a single push. The unioned registry files
  count as the branch's own paths for the re-stamp's `--accept`.
- **The landing builds the check.** Given `execute_dispatch_land` with a fake process runner When it builds the
  healed-tree check and calls it Then it runs exactly the three commands in "The union rules", the platform one with
  cwd `src/platform` and `PYTHONSAFEPATH` unset, and reads each exit code.
- **Mutation.** Given the flag-registry paths removed from `is_mechanical_conflict_path` When the station suite runs
  Then the first criterion's test fails with `MRS-DISP-038`.

## Boundaries & Constraints

**Always:**
- The JSON files resolve only through a parsed, key-wise, three-way union, written in the files' own form.
- The Python registries resolve only when every hunk is a pure addition of complete entries inside a named dict.
  `main`'s lines come first, then the branch's, verbatim.
- One merge for every mechanical path, then Story 22.18's re-stamp when the baseline conflicted, then the
  healed-tree check, then a single push, then Story 80.1's wait, then the retried merge.
- Name every changed governed path on the memlogs of the Specs that govern it, then stamp those Specs scoped
  (`spec-pyforge-marshal` and the co-governor `spec-pyforge-core`; AGENTS.md pre-PR item 5).

**Never:**
- Never resolve a key both sides set to different values by precedence. A JSON conflict is never resolved by a
  textual union.
- Never reformat a registry file, and never resolve any path other than the four registry files as newly
  mechanical. Every other unknown path still escalates with `MRS-DISP-038`.
- Never push a healed head before the healed-tree check passes, and never skip the check silently.
- Never change `scripts/flag_gate_check.py`, the flag tree's semantics or either test module's assertions.

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-07 (flag registry conflict) entry.
- Epic: Epic 22 (a fix joins its own epic, which stays `in-progress`; doctor Story 41.5).
- Ledger key: `22-19-a-landing-unions-the-flag-registry-when-two-flag-stories-land-in-turn`.
- Ledger status at mint: `backlog`.
- Deps: S-22.18.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- Mutation: remove the flag-registry paths from `is_mechanical_conflict_path` and re-run the station suite. The real-git landing test fails with `MRS-DISP-038`. Restore it.
- On the next real landing of a flag story behind another, the heal's merge commit shows both keys in all four files, and `pixi run -e pyforge-guild flag-gate-check` is green on `main` after the merge.
- `pixi run --frozen -e pyforge-guild spec-surface-check`: exit 0 after the memlog reconciles and scoped stamps.
