---
title: 'Entry-file family drift check, detect-only'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md', '{project-root}/CLAUDE.md', '{project-root}/AGENTS.md']
warnings: []
baseline_revision: 'HEAD as of 2026-08-07, immediately after S-6.6 (local)'
---

<intent-contract>

## Intent

**Problem:** This repo's own root carries a cross-tool "entry-file family" --
`AGENTS.md` (the declared hub) plus four per-tool satellite pointers
(`CLAUDE.md`, `.cursor/rules/specs.mdc`, `GEMINI.md`, `.github/
copilot-instructions.md`) -- and nothing checks that the family stays
mutually consistent as it drifts. Ownership between stations for these
shared, repo-level files is an open question (C-3/AD-11: Marshal never
edits a shared repo-level file), so FR-46 requires DETECTION ONLY: report
presence and divergence, name it, and stop -- never write.

**Approach:** `core/conformance.py` gains a FIFTH, self-contained area (no
new status vocabulary conflict -- this concern has no `pass`/`fail`-shaped
outcome, only "divergence present or absent"): a pure, declared,
non-branched configuration table (`ENTRY_FILE_FAMILY`, the hub-first tuple
of family-relative paths, and `ENTRY_FILE_TOOLS`, one row per CLI tool
naming exactly which family members THAT tool's own runtime loads --
mirrors `MECHANISM_CHECKERS`'/`skill_projection.PROJECTION_MECHANISM_BY_
PLATFORM`'s own "ONE table, one owner, declared not branched" shape, the
literal reading of the AC's "family membership is configuration, not a
literal"), a pure `EntryFileState`/`EntryFileDivergence` dataclass pair, and
a pure `evaluate_entry_file_family` classifier: for each non-hub family
member, a divergence is reported when the file is ABSENT or, if present,
does not reference the hub by name (a satellite that has drifted away from
forwarding to the hub is exactly the "instruction content is not isolated
per-CLI" hazard this story targets). Each divergence names every TOOL whose
own `reads` set includes the affected path -- `cross_contaminating: True`
when that tool's `reads` set has more than one member (the AC's own "one
tool applies the union of two files... a divergence is reported as
cross-contaminating, not merely cosmetic" made structural).

`cli/adapters.py` gains the new standalone, read-only action `marshal
adapters entry-files [--format]`. No project slug (mirrors `adapters
smoke`'s own "a repo/machine fact, independent of any one project" shape) --
this reads the SAME `cli/config.py::repo_root()` this repo's own root every
other cross-cutting command already resolves through. Reads each family
member via `FsPort.read_text`; calls `evaluate_entry_file_family`; folds
every returned divergence into ONE finding code (`MRS-ENTRY-001`, mirroring
`MRS-CONFORM-001`'s own "one code, several triggering shapes" precedent).
Never calls `write_text_atomic`, `repoint_symlink_atomic`, or any other
`FsPort` mutator anywhere in this command's own code path.

## Boundaries & Constraints

**Always:**
- **`marshal adapters entry-files` NEVER writes.** No `FsPort` mutator call
  anywhere in `run_adapters_entry_files`'s own code path -- grepped before
  writing this spec (zero hits). Detection only (C-3/AD-11: ownership
  between stations for a shared repo-level file is unsettled; Marshal never
  edits one).
- **Family membership is a declared table, never inline branching on a
  filename literal.** `ENTRY_FILE_FAMILY`/`ENTRY_FILE_TOOLS` are the ONE
  place this story's own knowledge of "which files, which tool reads
  which" lives -- mirrors this module's own `MECHANISM_CHECKERS` precedent.
- **A divergence names every affected TOOL, not just the affected file.**
  The AC's own "cross-contaminating, not merely cosmetic" requirement is
  satisfied structurally: `EntryFileDivergence.affected_tools` is computed
  from `ENTRY_FILE_TOOLS` itself (never hand-listed per divergence), and
  `cross_contaminating` is `True` exactly when an affected tool's own
  `reads` set has more than one member.
- **`evaluate_entry_file_family` is pure** (no I/O, no `time`/`os`/
  `subprocess`/`pyforge.marshal.adapters` import, AD-4) -- every family
  member's already-read presence/content fact is gathered at the `cli/
  adapters.py` boundary and passed in as `Mapping[str, EntryFileState]`.

**Never:**
- **No repair, no suggested fix written to disk, no `--fix` flag.** This
  story's own scope is detection; a future story may add repair once
  ownership is settled (out of scope here by design, per FR-46's own
  wording).
- **No project slug.** This command is a REPO fact, independent of any one
  BMAD project's own loop home.
- **No new status vocabulary conflict.** This concern has no `pass`/`fail`
  shape -- `evaluate_entry_file_family` returns a tuple of divergences
  (possibly empty), never a `STATUS_*` constant from any of this module's
  four existing closed vocabularies.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Every family member exists and every satellite references the hub | Ordinary, consistent repo | `data.divergences == []` | No finding |
| The hub (`AGENTS.md`) itself is absent | A genuinely broken hub | One divergence for the hub, naming every tool whose `reads` includes it | Registered finding (`MRS-ENTRY-001`, WARN) |
| A satellite file (e.g. `.cursor/rules/specs.mdc`) is absent | Missing pointer | One divergence for that path, naming the one tool that reads it (`cross_contaminating: False`, since Cursor's own `reads` has exactly one member) | Registered finding (`MRS-ENTRY-001`, WARN) |
| A satellite file exists but no longer mentions the hub by name | Drifted content | One divergence, `detail` naming "no longer references AGENTS.md" | Registered finding (`MRS-ENTRY-001`, WARN) |
| `CLAUDE.md` (a tool whose own `reads` includes TWO family members) diverges | The union-reading tool's own effective instructions are affected | The divergence's `affected_tools` names `"claude"`, `cross_contaminating: True` | Registered finding (`MRS-ENTRY-001`, WARN), message states the affected tool explicitly |
| The repo root itself cannot be resolved | Should never happen (`repo_root()` never raises) | N/A | N/A -- not modeled; `repo_root()`'s own contract is "derived, never raises" |

</intent-contract>

## Code Map

- `src/pyforge/marshal/core/conformance.py` -- EDIT. New frozen dataclass
  `EntryFileTool` (`tool: str`, `reads: tuple[str, ...]`). New module
  constant `ENTRY_FILE_FAMILY: tuple[str, ...]` (hub first: `"AGENTS.md"`,
  then `"CLAUDE.md"`, `".cursor/rules/specs.mdc"`, `"GEMINI.md"`,
  `".github/copilot-instructions.md"`). New module constant
  `ENTRY_FILE_TOOLS: tuple[EntryFileTool, ...]` (one row per tool, each
  `reads` a subset of `ENTRY_FILE_FAMILY`). New frozen dataclass
  `EntryFileState` (`path: str`, `exists: bool`, `mentions_hub: bool |
  None` -- `None` for the hub's own row, not applicable to itself). New
  frozen dataclass `EntryFileDivergence` (`path: str`, `detail: str`,
  `affected_tools: tuple[str, ...]`, `cross_contaminating: bool`). New pure
  `evaluate_entry_file_family(states: Mapping[str, EntryFileState]) ->
  tuple[EntryFileDivergence, ...]`.
- `src/pyforge/marshal/cli/adapters.py` -- EDIT. New `add_adapters_
  subparser` nested action `entry-files` (`marshal adapters entry-files
  [--format]`, no positional slug). New `_render_text_entry_files(data,
  findings) -> str`. New `run_adapters_entry_files(args, *, fs=None,
  context=None)`: reads every `ENTRY_FILE_FAMILY` member via `fs.read_text`
  relative to `repo_root()`, builds `EntryFileState` per member, calls
  `evaluate_entry_file_family`, folds every divergence into ONE
  `MRS-ENTRY-001` finding (WARN) naming the affected path(s)/tool(s), emits
  `data.divergences` (every divergence's full shape) regardless of finding
  count.
- `src/pyforge/marshal/core/findings.py` -- EDIT. Register one new code:
  `MRS-ENTRY-001` (a family member is absent, or present but no longer
  references the hub).
- `src/pyforge/marshal/core/verdict.py` -- EDIT. `MRS-ENTRY-001` ->
  `Verdict.WARN` (a detect-only advisory, never blocking -- mirrors
  `MRS-ADP-007`'s/`MRS-DEPLOY-001`'s own "reported, never blocks" tier).
- `tests/unit/test_conformance.py` -- EDIT. `evaluate_entry_file_family`
  matrix: all-consistent -> empty; missing hub; missing satellite; a
  satellite present but not mentioning the hub; a multi-file tool's own
  divergence sets `cross_contaminating: True`; a single-file tool's own
  divergence sets `cross_contaminating: False`; `affected_tools` is
  computed from `ENTRY_FILE_TOOLS`, never hand-listed.
- `tests/unit/test_adapters_cli.py` -- EDIT. `run_adapters_entry_files`
  matrix reusing the existing `FakeFs` double: all-consistent (no
  finding), missing hub, missing satellite, drifted satellite, `--format
  text` rendering, and an explicit assertion that `FakeFs` records NO
  `write_text_atomic`/`repoint_symlink_atomic` call across every scenario.

## Design Notes

- **Why "mentions the hub by name" (a substring check) rather than a
  richer content diff.** A genuine semantic diff between differently-shaped
  files (a full-content `CLAUDE.md` versus a five-line `.cursor/rules/
  specs.mdc` pointer) has no single well-defined notion of "consistent" --
  the two are not expected to be textually similar, only for the satellite
  to still forward to the hub. A substring check for the hub's own filename
  is a real, mechanically verifiable, non-gameable-by-cosmetic-rewording
  proxy for "has this satellite drifted into standalone content that no
  longer even points at the shared source of truth" -- the actual failure
  mode FR-46 names ("divergence... without Marshal editing files whose
  ownership is unsettled").
- **Why `cross_contaminating` is computed from `ENTRY_FILE_TOOLS`'s own
  `reads` cardinality, never a second, separately-maintained flag per
  tool.** The AC's own text ties "cross-contaminating" directly to a tool
  applying the UNION of more than one family file -- that is exactly `len(
  tool.reads) > 1`, already present in the ONE declared table. A second
  per-tool boolean would be a second, driftable copy of the same fact.

## Verification

- `pixi run --frozen -e pyforge-marshal python3 -m pytest src/shared/packages/pyforge-marshal/tests -q`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`

**Actual results (2026-08-07):**
- `pixi run --frozen -e pyforge-marshal python3 -m pytest src/shared/packages/pyforge-marshal/tests -q` (the FULL suite) -- **2995 passed** (2981 baseline from S-6.6 + a net 14 new: 8 `evaluate_entry_file_family` tests in `test_conformance.py`, 8 `run_adapters_entry_files` tests in `test_adapters_cli.py`, minus the `REGISTERED_CODES` snapshot addition already counted elsewhere -- see the Review Triage Log for the one regression test added during self-review).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 3 failed, all pre-existing accepted baseline (identical to S-6.5/S-6.6's own record), unrelated to this story.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` -- AD-3, AD-4, AD-9 all KEPT (88 files, 490 dependencies analyzed).
- **Live sanity check (not a test, informational):** this repo's own real family members were confirmed live (`grep -c "AGENTS.md"`) to each reference the hub -- `CLAUDE.md` (2), `.cursor/rules/specs.mdc` (1), `GEMINI.md` (2), `.github/copilot-instructions.md` (2) -- so a real `marshal adapters entry-files` run against this repo's own root would report zero divergences today, grounding the FakeFs-only test suite's own "all-consistent" fixture in the real, current state of the repo.

## Review Triage Log

Self-review pass against the diff (no separate adversarial dispatch this session -- see the Epic 6 retro notes). One real bug caught and fixed before any test ran red:

- **Unguarded `fs.read_text` could crash the whole command.** `FsPort.read_text`'s own documented contract is `None` for "does not exist" but `FsError` for a REAL read failure (a permission error, or the path naming a directory) -- the identical class of failure `gather_conformance_findings`'s own docstring already documents as a live Blind Hunter finding from Story 6.3. The first draft of `run_adapters_entry_files` called `fs.read_text` unguarded inside its per-family-member loop; an unreadable family member would have crashed this detect-only command entirely, directly contradicting FR-46's own "report... without Marshal editing files" framing (a crash is a much worse failure mode than a false report). Fixed: wrapped in `try`/`except FsError`, degrading to the same `exists=False` shape a genuinely absent file already reports. New regression test: `test_entry_files_unreadable_family_member_degrades_to_absent_never_crashes` (required extending `FakeFs` with a `fail_read_text` injection point, mirroring its existing `fail_read_symlink`/`fail_repoint` precedents).

**Follow-up review recommendation: false** -- the one finding is fixed and covered by a dedicated regression test; the "substring hub-mention, not a semantic diff" scope boundary is a recorded design decision (see Design Notes above), not an open defect.

</intent-contract>
