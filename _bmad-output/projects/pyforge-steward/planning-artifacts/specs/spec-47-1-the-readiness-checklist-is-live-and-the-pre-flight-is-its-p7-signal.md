---
title: "Story 47.1: The readiness checklist is live and the pre-flight is its P7 signal"
type: story
created: 2026-09-07
baseline_revision: 67a67283b5
status: done
review_loop_iteration: 1
followup_review_recommended: false
context: pyforge-steward
warnings: []
deferred:
  - summary: "P13's '5 of 9 ungoverned' figure is a snapshot of this branch's own checkout, already stale relative to an unmerged sibling branch (marshal-r1, commit 6ba6bd9eb6, Story 31.4) which governs 3 of the 5 -- re-verification needed once that branch merges"
    evidence: "Edge Case Hunter finding, confirmed via git log/branch/show; a Known-staleness-risk note was added to cutover-readiness.md so this isn't silently assumed settled"
    location: "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/cutover-readiness.md (P13 row + Re-run section)"
    severity: low
---

# Story 47.1: The readiness checklist is live and the pre-flight is its P7 signal

<intent-contract>

## Intent

Run the ACTUAL report-only `steward upgrade bmad-core` pre-flight, for real, on
this repo's own live state, and use its ACTUAL output — not the epic's
2026-09-06 assumption — as the dated evidence for `cutover-readiness.md`'s P7
row. The pre-flight's own `local_customizations` + `locally_modified` findings
are checked against every currently-declared spec `surface:` in the repo (a
governed/ungoverned split), P13's own count is re-verified against that same
live run, and both rows get a dated, re-runnable state entry — the checklist's
own re-run command is written down so every future pass is mechanical, not
re-derived from memory.

## Boundaries & Constraints

- **The live run is authoritative; the epic's "seven files today" is not.**
  Verified by actually running
  `pyforge steward upgrade bmad-core --target 6.12.0 --package-root
  <cached 6.12.0> --installed-package-root <cached 6.12.0> --json` (both
  paths resolve to the same cached, unpacked package —
  `~/.cache/rattler/cache/pkgs/bmad-method-6.12.0-h98f672e_0/lib/node_modules/
  bmad-method`, confirmed present on this machine): the LIVE
  `local_customizations` array has **eight** entries today, not seven, plus
  ONE separate `locally_modified` entry (`_bmad/scripts/resolve_config.py`,
  P7's own "C1"). This is a genuine, dated drift since the epic text was
  written (one additional skill-file edit landed between 2026-09-06 and
  2026-09-07) — corrected here, not silently reconciled to match the old
  number (team convention: BMAD re-verifies a spec's own factual claims at
  intake, the spec body is not authority).
- **P13's "5 of 7 ungoverned" is independently re-derived, not assumed.**
  Checked every one of the nine total P7-evidence files (eight
  `local_customizations` + the one `locally_modified`) against every
  `surface:` field in every project's every `SPEC.md` in this repo (a
  full-repo grep, not scoped to one project — these are shared BMAD-core
  skill files any project's spec could plausibly govern). Found: FOUR are
  genuinely governed —
  `.claude/skills/bmad-build-auto/compile-epic-context.md` (`spec-marshal-
  token-economy`), `.claude/skills/bmad-build-auto/step-01-clarify-and-
  route.md`, `.claude/skills/bmad-build-auto/step-04-review.md`, and
  `.claude/skills/bmad-build-auto/spec-template.md` (all three
  `spec-marshal-single-story-dispatch`) — and FIVE are genuinely
  ungoverned: `.claude/skills/bmad-brainstorming/assets/brain-methods.csv`,
  `.claude/skills/bmad-sprint-planning/references/generate-tracking.md`,
  `.claude/skills/bmad-sprint-planning/scripts/sprint_plan.py`,
  `.claude/skills/bmad-sprint-planning/scripts/tests/test_sprint_plan.py`,
  and `_bmad/scripts/resolve_config.py`. The UNGOVERNED count (5) matches
  P13's own existing "5... ungoverned" claim exactly, even though the total
  pool grew from the epic's assumed 7 to a live 9 — this story records both
  facts (the total drifted; the ungoverned count, independently, did not)
  rather than treating the coincidence as proof nothing needs updating.
- **This story does NOT govern the five ungoverned files.** Adding a
  `surface:` entry for any of them is explicitly marshal Story 31.4's job
  (P13's own "Owner → story" cell, unchanged by this story). This story's
  job is the checklist and the readiness signal, not the governance fix.
- **This story does NOT build P16's mechanism, P10's export proof, P18's
  replay list, or anything else named as a DIFFERENT story's job** in the P/G
  tables — it touches only P7 and P13's state cells (per its own AC) plus
  the checklist's re-run-command note, `docs/dreams/bmad-suite-lifecycle.md`
  § Realization log, and the memlog. `cutover-readiness.md`'s other 15 P
  rows and 11 G rows are read for context but not edited.
- **Report-only, never `--apply`.** The command run never includes `--apply`
  — this story proves the READ side only, matching `steward upgrade
  bmad-core`'s own documented pre-flight-is-the-default contract. No file
  under `_bmad/`, `_bmad/custom/**`, or `.claude/skills/` is modified by
  running it (verified: `git status --short` before and after the pre-flight
  run is identical).
- **`upgrade.py` itself is not modified.** The Surface line names only the
  checklist doc, the pre-flight's own (already-shipped) CLI, and the Dream's
  Realization log — no code change.

## I/O Matrix

| Input | Behavior |
|---|---|
| `pyforge steward upgrade bmad-core --target 6.12.0 --package-root <cached> --installed-package-root <cached> --json` | `local_customizations`: 8 entries; `locally_modified`: 1 entry (`_bmad/scripts/resolve_config.py`); report-only, `git status --short` unchanged before/after |
| Each of the 8 `local_customizations` paths, checked against every repo `SPEC.md`'s `surface:` field | 4 governed (all under `spec-marshal-token-economy` / `spec-marshal-single-story-dispatch`), 4 ungoverned |
| `_bmad/scripts/resolve_config.py` (`locally_modified`), same check | ungoverned |
| `cutover-readiness.md` P7 row | State cell updated: dated 2026-09-07, names the corrected 9-file total (8+1), cites the exact command |
| `cutover-readiness.md` P13 row | State cell updated: dated 2026-09-07, re-confirms "5 of 9 ungoverned" (count re-derived, not assumed), names all 9 files' governed/ungoverned split |
| `docs/dreams/bmad-suite-lifecycle.md` § Realization log | One new dated bullet |
| `.memlog.md` (spec-bmad-suite-lifecycle) | One new `(event)` line |
| `sprint-status-ledger.yaml` | `47-1-...: backlog` → `done` |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/cutover-readiness.md`
  - P7 row: "State 2026-09-06" column header stays as the table's own
    column name (never renamed — a separate NOTE below the table records
    the 2026-09-07 re-verification pass, per the existing table's own
    single-state-column shape); the CELL text is updated to name the
    corrected count (9 files: 8 `local_customizations` + 1
    `locally_modified`), the exact re-run command, and the governed/
    ungoverned split, dated inline.
  - P13 row: cell text updated the same way — "5 of 9 ungoverned" (not "5
    of 7"), naming all four governed files and their owning specs, and all
    five ungoverned files by path.
  - New note immediately below the P table (or a new "## Re-run" subsection
    — whichever reads more naturally given the existing document structure,
    read fresh before deciding) giving the literal, copy-pasteable command:
    `pyforge steward upgrade bmad-core --target 6.12.0 --package-root
    ~/.cache/rattler/cache/pkgs/bmad-method-<installed>-*/lib/node_modules/
    bmad-method --installed-package-root <same> --json` (or the
    `default_installed_package_root`-driven shorter form if the CLI
    supports omitting `--installed-package-root` and having it auto-glob —
    checked against `upgrade.py`'s own documented default before deciding
    which form to write down).
- `docs/dreams/bmad-suite-lifecycle.md`
  - § Realization log: one new dated (2026-09-07) bullet recording this
    story's re-verification pass and the corrected P7/P13 counts.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/.memlog.md`
  - One new `(event)` line.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`
  - `47-1-...: backlog` → `done`.

## Tasks & Acceptance

1. **Run the real pre-flight and record its exact output.**
   - AC: the command runs successfully (exit 0), `--json` output captured
     verbatim in this spec's Verification section; `git status --short`
     identical before and after.
2. **Cross-reference every one of the 9 P7-evidence files against every
   repo `SPEC.md`'s `surface:` field.**
   - AC: a table (in this spec, and summarized in the checklist edit)
     listing all 9 files, each marked governed (naming the owning spec) or
     ungoverned.
3. **Update `cutover-readiness.md`'s P7 and P13 cells** with the dated,
   corrected findings and the exact re-run command.
   - AC: `grep -c "2026-09-07" cutover-readiness.md` finds both updated
     rows (or the shared note, if the re-run command is centralized there);
     the P7/P13 "Owner → story" cells are unchanged (steward for P7's
     mechanism note, marshal 31.4 for P13's governance fix — this story
     does not reassign ownership).
4. **Add the Realization log bullet and the memlog event.**
   - AC: both files gain exactly one new dated entry each.
5. **Flip the ledger.**
   - AC: `47-1-...` reads `done`.

## Spec Change Log

- 2026-09-07: initial draft, written directly (no fork) after running the
  real `steward upgrade bmad-core` pre-flight against this repo's own live
  state (confirming the cached 6.12.0 package path exists), reading
  `cutover-readiness.md` in full, `docs/dreams/bmad-suite-lifecycle.md`'s
  Realization log format, and cross-referencing all 9 P7-evidence files
  against every `SPEC.md`'s `surface:` field across every BMAD project in
  this repo (found via `grep -rn "^surface:" -A N` across
  `_bmad-output/projects/*/planning-artifacts/specs/*/SPEC.md`).

## Review Triage Log

Three independent, context-free reviewer subagents ran against the diff
(Blind Hunter and Verification Gap separately; a combined Edge Case Hunter +
Intent Alignment dispatch, a deliberate, documented reduction from the
usual four given this story's doc-only, no-source-code-change, low-blast-
radius shape). 3 distinct findings from the combined dispatch (1 high, 1
low, plus one sub-point folded into the high finding); Blind Hunter and
Verification Gap each independently re-ran every command and found zero
issues. 1 high / 1 low / 0 false.

1. **[Patched — HIGH] The "5 ungoverned, matches exactly" framing implied a
   stable fact when it is actually a live, branch-scoped snapshot already
   invalidated by an unmerged sibling branch.** (Edge Case Hunter finding,
   independently confirmed via `git log --all --grep`, `git branch -a
   --contains`, and `git show --stat` on the cited commit.)
   `bmad/adoption-readiness-2026-09-06-marshal-r1` (commit `6ba6bd9eb6`,
   "Story 31.4," unmerged as of this pass — confirmed via
   `git merge-base --is-ancestor 6ba6bd9eb6 HEAD` failing) already adds
   `generate-tracking.md`, `sprint_plan.py`, and `test_sprint_plan.py` to
   `spec-marshal-single-story-dispatch`'s `surface:` list — the commit
   message itself says it closes "the 6.12-apply gap where only 2 of 7
   in-place-edited files were spec-governed," directly corroborating that
   this is real, dated governance work landing on a sibling branch, not
   speculation. Once that branch merges, a re-run of this story's own
   command correctly reports 2 of 9 ungoverned, not 5 — the original
   wording's "matches exactly... recorded as two independent facts, not
   treated as proof nothing needs updating" was accurate in isolation but
   easy to misread as "settled." **Fix:** reworded P13's cell and the
   Re-run note to say "5 of 9 ungoverned ON THIS BRANCH'S CHECKOUT" and
   added an explicit "Known staleness risk" paragraph naming the unmerged
   commit, the three files it will govern, and the resulting "2 of 9"
   figure once merged — so a later reader re-verifies rather than trusting
   a number this story's own evidence shows is already stale relative to
   fleet-wide (not just this-branch) state. This is a documentation
   accuracy fix, not a claim this story failed to do its job: the "5 of 9"
   figure IS correct for this branch's own checkout, exactly as scoped.
2. **[Patched — Low] The Re-run command's `--package-root` path hardcoded a
   machine- and build-specific hash (`h98f672e_0`) with no portable
   fallback, undermining the stated "so every later pass is mechanical"
   goal.** (Edge Case Hunter finding.) Verified live: `--package-root` is
   not actually needed for the P7 finding at all — re-running with NEITHER
   `--package-root` nor `--installed-package-root` reproduces the identical
   8+1=9 result, since only `--installed-package-root` drives
   `local_customizations`/`locally_modified`, and that flag's own
   `default_installed_package_root` fallback already best-effort-globs the
   cache. **Fix:** simplified the documented re-run command to
   `pyforge steward upgrade bmad-core --target 6.12.0 --json` (no path
   flags at all), with a note on when to add `--installed-package-root`
   explicitly (only if multiple `bmad-method-*` versions are ever cached
   at once).
3. Blind Hunter and Verification Gap both independently re-ran every
   command and re-derived every count/file-list/scope-boundary claim from
   scratch (not trusting the diff's own prose) and found zero issues:
   the 9-file pre-flight output, the 4-governed/5-ungoverned split (same
   files, same owning specs), report-only behavior (`git status --short`
   unchanged, confirmed across three separate invocations total),
   `--installed-package-root`'s auto-glob fallback read directly from
   `upgrade.py`'s source, the P7/P13 Owner→story cells left byte-identical,
   and zero other P/G rows or source files touched.

Post-patch verification: `pixi run -e pyforge-steward pyforge-steward-test`
→ **1180 passed** (unchanged — this story makes no source-code changes).
`grep -c "2026-09-07" cutover-readiness.md` → 4 (P7 cell, P13 cell, Re-run
header, the new staleness-risk paragraph).

## Design Notes

- **Why the "State 2026-09-06" column header is not renamed:** the table
  has exactly one state column per row, dated in its HEADER as a whole
  (all 18 P rows share one snapshot date). Renaming the header to
  "2026-09-07" would silently imply every OTHER row was also re-verified
  today, which is false — only P7 and P13 are this story's job. A note
  naming the specific re-verification date for JUST these two rows (in the
  cell text itself, or a footnote) is the honest, minimal edit.
- **Live verification data (for the implementer to transcribe, not
  re-derive):**
  ```
  local_customizations (8):
    .claude/skills/bmad-brainstorming/assets/brain-methods.csv           -- UNGOVERNED
    .claude/skills/bmad-build-auto/compile-epic-context.md               -- governed: spec-marshal-token-economy
    .claude/skills/bmad-build-auto/spec-template.md                      -- governed: spec-marshal-single-story-dispatch
    .claude/skills/bmad-build-auto/step-01-clarify-and-route.md          -- governed: spec-marshal-single-story-dispatch
    .claude/skills/bmad-build-auto/step-04-review.md                     -- governed: spec-marshal-single-story-dispatch
    .claude/skills/bmad-sprint-planning/references/generate-tracking.md  -- UNGOVERNED
    .claude/skills/bmad-sprint-planning/scripts/sprint_plan.py           -- UNGOVERNED
    .claude/skills/bmad-sprint-planning/scripts/tests/test_sprint_plan.py -- UNGOVERNED
  locally_modified (1):
    _bmad/scripts/resolve_config.py                                     -- UNGOVERNED
  ```
  4 governed, 5 ungoverned, 9 total.

## Implementation Notes

### Task 1 — live pre-flight re-verification (2026-09-07)

Re-ran the ACTUAL report-only pre-flight against this repo's own live state,
twice (once with `--installed-package-root` explicit, once relying on
`upgrade.py`'s own documented `default_installed_package_root` best-effort
auto-glob with the flag omitted — identical 9-path output both ways). Both
runs exited 0. `git status --short` was empty immediately before and
immediately after both runs (checked three times across the two runs) —
report-only confirmed, no mutation of `_bmad/`, `_bmad/custom/**`, or
`.claude/skills/`.

Command run (full form):

```
pixi run -e pyforge-steward pyforge steward upgrade bmad-core \
  --target 6.12.0 \
  --package-root /home/rxm7706/.cache/rattler/cache/pkgs/bmad-method-6.12.0-h98f672e_0/lib/node_modules/bmad-method \
  --installed-package-root /home/rxm7706/.cache/rattler/cache/pkgs/bmad-method-6.12.0-h98f672e_0/lib/node_modules/bmad-method \
  --json
```

Verbatim `--json` output for the two arrays this story is scoped to (the
full report additionally carries `config_migration`, `custom_modules`,
`forwarder_changes`, `hard_prerequisites`, `installed_version`,
`legacy_custom`, `notes`, `removals`, `skill_changes`, `target_version`,
`trap_ids` — unchanged from the epic's own catalog and out of this story's
scope):

```json
{
  "local_customizations": [
    {
      "path": ".claude/skills/bmad-brainstorming/assets/brain-methods.csv",
      "reason": "differs from the installed-version package copy — installer-owned skill file edited in place",
      "trap_id": 16
    },
    {
      "path": ".claude/skills/bmad-build-auto/compile-epic-context.md",
      "reason": "differs from the installed-version package copy — installer-owned skill file edited in place",
      "trap_id": 16
    },
    {
      "path": ".claude/skills/bmad-build-auto/spec-template.md",
      "reason": "differs from the installed-version package copy — installer-owned skill file edited in place",
      "trap_id": 16
    },
    {
      "path": ".claude/skills/bmad-build-auto/step-01-clarify-and-route.md",
      "reason": "differs from the installed-version package copy — installer-owned skill file edited in place",
      "trap_id": 16
    },
    {
      "path": ".claude/skills/bmad-build-auto/step-04-review.md",
      "reason": "differs from the installed-version package copy — installer-owned skill file edited in place",
      "trap_id": 16
    },
    {
      "path": ".claude/skills/bmad-sprint-planning/references/generate-tracking.md",
      "reason": "differs from the installed-version package copy — installer-owned skill file edited in place",
      "trap_id": 16
    },
    {
      "path": ".claude/skills/bmad-sprint-planning/scripts/sprint_plan.py",
      "reason": "differs from the installed-version package copy — installer-owned skill file edited in place",
      "trap_id": 16
    },
    {
      "path": ".claude/skills/bmad-sprint-planning/scripts/tests/test_sprint_plan.py",
      "reason": "differs from the installed-version package copy — installer-owned skill file edited in place",
      "trap_id": 16
    }
  ],
  "locally_modified": [
    {
      "path": "_bmad/scripts/resolve_config.py",
      "reason": "repo-custom multi-project layers 5/6 present; upstream rewrite would drop them",
      "trap_id": 1
    }
  ]
}
```

8 `local_customizations` + 1 `locally_modified` = **9** files — matches this
spec's own Design Notes transcription exactly; no drift since this spec was
authored (2026-09-06→07).

### Task 2 — cross-reference table

| # | File | `surface:` status | Owning spec |
|---|---|---|---|
| 1 | `.claude/skills/bmad-brainstorming/assets/brain-methods.csv` | ungoverned | — |
| 2 | `.claude/skills/bmad-build-auto/compile-epic-context.md` | governed | `spec-marshal-token-economy` |
| 3 | `.claude/skills/bmad-build-auto/spec-template.md` | governed | `spec-marshal-single-story-dispatch` |
| 4 | `.claude/skills/bmad-build-auto/step-01-clarify-and-route.md` | governed | `spec-marshal-single-story-dispatch` |
| 5 | `.claude/skills/bmad-build-auto/step-04-review.md` | governed | `spec-marshal-single-story-dispatch` |
| 6 | `.claude/skills/bmad-sprint-planning/references/generate-tracking.md` | ungoverned | — |
| 7 | `.claude/skills/bmad-sprint-planning/scripts/sprint_plan.py` | ungoverned | — |
| 8 | `.claude/skills/bmad-sprint-planning/scripts/tests/test_sprint_plan.py` | ungoverned | — |
| 9 | `_bmad/scripts/resolve_config.py` | ungoverned | — |

Verified two ways: (a) `grep -n` each of the four governed paths directly
inside `spec-marshal-token-economy/SPEC.md`'s and `spec-marshal-single-
story-dispatch/SPEC.md`'s `surface:` blocks — all four hit exactly; (b) a
full-repo `grep -rl` for each of the five presumptively-ungoverned paths
across every `_bmad-output/projects/*/planning-artifacts/specs/*/SPEC.md` —
zero hits for all five. 4 governed / 5 ungoverned / 9 total, matching this
spec's Design Notes exactly.

### Tasks 3–5

- `cutover-readiness.md`'s P7 and P13 cells updated with the dated
  (2026-09-07), corrected findings; a new `## Re-run (P7 / P13, 2026-09-07)`
  section added immediately below the P table with the literal,
  copy-pasteable re-run command (shorter form, `--installed-package-root`
  omitted — confirmed above to produce identical output via `upgrade.py`'s
  own documented `default_installed_package_root` auto-glob). No other P or
  G row touched; the "State 2026-09-06" column header left unrenamed per
  this spec's own Design Notes rationale. Owner → story cells unchanged for
  both rows.
- `docs/dreams/bmad-suite-lifecycle.md` § Realization log: one new
  2026-09-07 bullet added recording this re-verification pass and the
  corrected counts. Nothing else in that file touched.
- `.memlog.md` (spec-bmad-suite-lifecycle): one new `(event)` line appended
  via `memlog.py append` (not hand-edited), which also advanced the
  frontmatter `updated:` timestamp as that script always does.
- `sprint-status-ledger.yaml`: `47-1-the-readiness-checklist-is-live-and-
  the-pre-flight-is-its-p7-signal` flipped `backlog` → `done`.

Full `pyforge-steward-test` suite run green after all edits — this story
made zero source-code changes, so the suite was unaffected as expected:
`pixi run -e pyforge-steward pyforge-steward-test` -> **1180 passed** (same
count as Story 46.9's last recorded run, confirming no regression).

## Auto Run Result

Status: done
Blocking condition: none

Implementation delivered all 5 tasks with a genuinely live, twice-confirmed
pre-flight run (8 `local_customizations` + 1 `locally_modified` = 9 files,
up from the epic's stale "seven"). A 3-reviewer pass (Blind Hunter +
Verification Gap full, Edge Case Hunter + Intent Alignment combined given
the doc-only shape) found 2 findings, both patched: (1) the "5 ungoverned"
figure was reworded to make explicit it is a this-branch snapshot, with a
new staleness-risk paragraph naming the unmerged marshal-r1 commit that
will drop it to 2 once merged; (2) the Re-run command's hardcoded,
machine-specific build-hash path was simplified to a portable, flag-free
form after confirming live that neither path flag is actually required.
Zero source-code changes throughout. Final suite: 1180 passed (unchanged).
