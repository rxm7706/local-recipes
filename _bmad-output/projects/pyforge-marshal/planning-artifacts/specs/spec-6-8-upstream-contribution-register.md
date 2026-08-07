---
title: 'Upstream contribution register'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md', '{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md']
warnings: []
baseline_revision: 'HEAD as of 2026-08-07, immediately after S-6.7 (local)'
---

<intent-contract>

## Intent

**Problem:** AD-2's own "wrap, do not absorb" decision means every real
limitation in the wrapped `bmad-loop` engine gets a Marshal-side
workaround (idle-strand detection built externally, model tiering
batched at run level, etc.) -- and a workaround with no tracked upstream
status quietly becomes permanent even after the underlying gap closes.
FR-58 requires a tracked register naming each gap, its Marshal workaround,
its upstream status, and the Marshal FR that compensates while the gap is
open -- confirmed live against the PRD's own FR-58 text (§7.9) and its
Roadmap/Deferred-fold entries, which ALREADY name the five initial gaps
verbatim, including one (`non-POSIX multiplexer support`) the PRD itself
records as landed 2026-08-01 (v0.9.0's Windows `psmux` backend) -- this
story's first live proof that the "flags for removal on landed" behavior
is not speculative.

**Approach:** `core/upstream.py` (NEW, pure -- no I/O, AD-4) declares a
closed two-member status vocabulary (`UPSTREAM_STATUS_OPEN`/
`UPSTREAM_STATUS_LANDED`), a frozen `UpstreamGapEntry` dataclass, a pure
`parse_register(raw: object) -> tuple[tuple[UpstreamGapEntry, ...],
tuple[str, ...]]` (shape-validates an ALREADY-`json.loads`-parsed object;
never raises -- a malformed entry is skipped and named in the second,
error-message tuple, mirroring `_read_probe_state`'s own "degrade, never
crash" convention applied to a PARSED value instead of a read), and a
pure `flagged_for_removal(entries) -> tuple[UpstreamGapEntry, ...]` (every
entry whose `upstream_status == UPSTREAM_STATUS_LANDED` -- the AC's own
"an entry whose upstream status becomes landed flags its compensating
workaround for removal", made structural).

`cli/upstream.py` (NEW -- this story's own Surface line names either
`cli/adapters.py` or a new `cli/upstream.py`; a new top-level command is
chosen, mirroring `cli/retire.py`'s own standalone-verb precedent, since
this concern is not adapter-specific) adds the new top-level, read-only
command `marshal upstream [--format]`. It reads the ONE tracked register
file this story also creates (`_bmad-output/projects/pyforge-marshal/
planning-artifacts/upstream-register.json`, hand-curated content, git
review decides -- mirrors the CFE-side `cwe-seed-gap`/`spdx-schema-gap`
suggester pattern's own "the curated map stays hand-owned" precedent, this
package's own `schemas/*.json` convention for the FORMAT choice over the
rest of the repo's YAML -- no new dependency, `json` is already this
package's own durable-record format everywhere else), parses it via
`core.upstream.parse_register`, and reports every entry plus the
`flagged_for_removal` subset through the standard envelope -- readable by
`marshal status`/docs downstream (out of this story's own scope to wire
those consumers; the envelope IS the readable surface FR-58 requires).
`cli/main.py` gains the one, unavoidable wiring line every top-level
command needs (`upstream_cli.add_upstream_subparser(subparsers)`, mirroring
`retire_cli`'s own identical registration).

## Boundaries & Constraints

**Always:**
- **`marshal upstream` NEVER writes the register.** It is hand-curated;
  git review decides content changes, exactly like the CFE-side
  `cwe-seed-gap`/`spdx-schema-gap`/`license-map-gap` suggesters' own
  "the curated map stays hand-owned" precedent this repo's CLAUDE.md
  already documents for a sibling concern. No `FsPort` mutator call
  anywhere in `run_upstream`'s own code path.
- **`parse_register`/`flagged_for_removal` are pure** (no I/O, AD-4) --
  the CLI boundary reads and `json.loads`es the file; these functions only
  classify the already-parsed value.
- **A malformed register never crashes the command.** Absent file,
  invalid JSON, or a non-conforming entry all degrade to an empty/partial
  result plus a named finding -- mirrors this package's every other
  "malformed durable record" convention (`_read_probe_state`/
  `_read_smoke_state`'s own `MRS-ADP-016`/`MRS-SMOKE-007` precedent).
- **Every entry names the Marshal FR that compensates.** `compensating_fr`
  is a required field; `parse_register` rejects (skips, names in errors)
  an entry missing it.

**Never:**
- **No new dependency.** The register is JSON, this package's own existing
  durable-record format (`gate-record.json`, `journal.json`,
  `adapter-probes.json`, ...) -- never YAML, which would need a new,
  undeclared `pyyaml` dependency this package's own `pyproject.toml` does
  not carry today (confirmed live: zero `import yaml` anywhere in `src/`).
- **No per-project parameterization.** Unlike `marshal adapters matrix`
  (a fact about ANY project's own tracked planning artifacts), this
  register is inherently about MARSHAL'S OWN upstream dependency
  (`bmad-loop`, AD-2's "binds: all") -- one fixed, self-referential path
  under `pyforge-marshal`'s own tracked planning artifacts, never a
  `--project`/positional slug argument.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| The register file is well-formed, all entries `open` | Ordinary state | `data.entries` lists every entry; `data.flagged_for_removal == []` | No finding |
| An entry's `upstream_status` is `"landed"` | A gap has closed upstream | That entry appears in `data.flagged_for_removal`, naming its `workaround`/`compensating_fr` | Registered finding (`MRS-UPSTREAM-002`, WARN, informational -- never blocks) |
| The register file is absent | Never created (should not happen post-this-story, but degrade safely) | `data.entries == []` | Registered finding (`MRS-UPSTREAM-001`, WARN) |
| The register file is malformed JSON | Corrupt file | `data.entries == []` | Registered finding (`MRS-UPSTREAM-001`, WARN) |
| One entry is missing a required field (e.g. `compensating_fr`) | Partial corruption | That entry is skipped; every OTHER well-formed entry still reports | Registered finding (`MRS-UPSTREAM-001`, WARN, naming the skipped entry) |
| `--format text` | Human-readable output requested | One line per entry, `[FLAGGED]` prefix for a landed one | No finding beyond the above |

</intent-contract>

## Code Map

- `src/pyforge/marshal/core/upstream.py` -- NEW. `UPSTREAM_STATUS_OPEN =
  "open"`, `UPSTREAM_STATUS_LANDED = "landed"`, `ALL_UPSTREAM_STATUSES`.
  Frozen dataclass `UpstreamGapEntry` (`id: str`, `gap: str`, `workaround:
  str`, `compensating_fr: str`, `upstream_status: str`, `note: str |
  None`). Pure `parse_register(raw: object) -> tuple[tuple[
  UpstreamGapEntry, ...], tuple[str, ...]]`. Pure `flagged_for_removal(
  entries: Iterable[UpstreamGapEntry]) -> tuple[UpstreamGapEntry, ...]`.
- `src/pyforge/marshal/cli/upstream.py` -- NEW. `_REGISTER_RELPATH`
  constant (`_bmad-output/projects/pyforge-marshal/planning-artifacts/
  upstream-register.json`, joined onto `cli/config.py::repo_root()`).
  `add_upstream_subparser(subparsers)`. `_render_text(data, findings) ->
  str`. `run_upstream(args, *, fs=None, context=None)`.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/
  upstream-register.json` -- NEW, tracked. The five initial entries
  (idle-strand detection FR-12/open; per-story model tiering FR-51/open;
  the hard-coded `planning_artifacts` composition FR-2/open; ACP
  evaluation FR-58/open; non-POSIX multiplexer support FR-5/**landed**,
  2026-08-01, v0.9.0's Windows `psmux` backend) -- content verified live
  against the PRD's own FR-58 §7.9 and Roadmap sections, not invented.
- `src/pyforge/marshal/core/findings.py` -- EDIT. Register two new codes:
  `MRS-UPSTREAM-001` (the register is absent, malformed, or one of its
  entries fails the shape check), `MRS-UPSTREAM-002` (an entry's own
  `upstream_status` is `landed` -- its workaround is flagged for removal).
- `src/pyforge/marshal/core/verdict.py` -- EDIT. Both new codes classify
  `Verdict.WARN` -- `MRS-UPSTREAM-001` mirrors `MRS-ADP-016`'s "degrades,
  never blocks" tier; `MRS-UPSTREAM-002` is purely informational (a landed
  gap is GOOD news, never a failure) and never escalates past `WARN`.
- `src/pyforge/marshal/cli/main.py` -- EDIT. Import `from . import upstream
  as upstream_cli`; one new wiring line, `upstream_cli.
  add_upstream_subparser(subparsers)`, alongside every other top-level
  command's identical registration.
- `tests/unit/test_upstream.py` -- NEW. `parse_register` matrix: a
  well-formed list; a missing/malformed top-level shape; one entry missing
  a required field (skipped, named); an unrecognized `upstream_status`
  value (skipped, named -- the closed vocabulary is enforced here, not
  left to the CLI). `flagged_for_removal` matrix: empty when none `landed`;
  returns exactly the `landed` subset, order-preserving.
- `tests/unit/test_upstream_cli.py` -- NEW. `run_upstream` matrix reusing
  a `FakeFs` double (mirrors `test_adapters_cli.py`'s own shape): the real
  five-entry register content round-trips; absent file; malformed JSON;
  one malformed entry (others still report); a `landed` entry surfaces
  `MRS-UPSTREAM-002` and appears in `data.flagged_for_removal`;
  `--format text` rendering; an explicit assertion that `FakeFs` records
  NO mutator call.
- `tests/unit/test_cli.py` (or wherever `main.py`'s subparser wiring is
  smoke-tested) -- EDIT if an existing test enumerates every registered
  top-level command name.

## Design Notes

- **Why the register's initial content is not invented.** The PRD's own
  FR-58 section (§7.9) already names all five initial gaps verbatim,
  including the closed-as-delivered multiplexer entry with a dated note --
  this story transcribes that PRD text into the tracked, machine-readable
  register rather than re-deriving or guessing gap descriptions. Per-entry
  `gap`/`workaround` prose is drawn from the PRD's own surrounding
  sections (§6 Wrap-vs-fork decision table, §7.1 FR-2, §7.2 FR-12, §7.7
  FR-51, §7.14 Q-6) and this codebase's own real, already-shipped
  mechanisms (`core/supervise.py`, `cli/spin.py`'s model-tier composition,
  `cli/init.py`'s marker/symlink convergence, `adapters/harness_
  bmadloop.py`'s single wrap seam, `cli/init.py`'s multiplexer preflight
  check) -- not fabricated.
- **Why `MRS-UPSTREAM-002` (landed) is WARN, never a higher/lower tier.**
  A landed gap is unambiguously good news for the operator -- it never
  represents a failure of anything Marshal did -- but it IS actionable
  (a workaround can now be simplified or removed), so `CLEAN`/silent would
  under-report it. `WARN` is this codebase's own established "reported,
  never blocks" tier for exactly this shape of advisory.
- **Why a NEW top-level command rather than folding into `marshal
  adapters`.** The register is not adapter-specific (three of the five
  entries -- idle-strand detection, `planning_artifacts` composition, ACP
  evaluation -- have nothing to do with any one adapter profile); nesting
  it under `adapters` would misname its own scope. `marshal retire`'s own
  precedent (a standalone, single-purpose top-level verb) is the closer
  fit, and this story's own epics Surface line explicitly names
  `cli/upstream.py` as an accepted alternative.

## Verification

- `pixi run --frozen -e pyforge-marshal python3 -m pytest src/shared/packages/pyforge-marshal/tests -q`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`

**Actual results (2026-08-07):**
- `pixi run --frozen -e pyforge-marshal python3 -m pytest src/shared/packages/pyforge-marshal/tests -q` (the FULL suite) -- **3033 passed** (2995 baseline from S-6.7 + a net 38 new: 13 `parse_register`/`flagged_for_removal` tests in the new `test_upstream.py`, 10 `run_upstream` tests in the new `test_upstream_cli.py` -- including a live round-trip of the ACTUAL tracked register content this story ships -- plus the one existing `test_help_lists_gate_subcommand` subcommand-list assertion updated in place for the new `upstream` top-level verb).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 3 failed, all pre-existing accepted baseline (identical to S-6.5/S-6.6/S-6.7's own record), unrelated to this story.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` -- AD-3, AD-4, AD-9 all KEPT (90 files, 505 dependencies analyzed).

## Review Triage Log

Self-review pass against the diff (no separate adversarial dispatch this session -- see the Epic 6 retro notes). No new correctness bugs found this pass -- the `fs.read_text`-can-raise `FsError` guard (Story 6.7's own live self-review finding) was applied here from the FIRST draft rather than discovered afterward, since the pattern was already fresh from that story.

- **`test_help_lists_gate_subcommand`'s own subcommand-list assertion required an update.** A pre-existing test asserts the EXACT set of top-level subcommand names `marshal --help` lists -- adding `upstream` to `cli/main.py`'s wiring correctly turned it red until the literal string was updated. Not a defect in this story's own code; flagged here because a similar assertion elsewhere in the suite (if any exists and was missed) would silently mask a future subcommand-wiring gap the SAME way. Grepped for other literal subcommand-set strings across `tests/`: none found beyond this one.
- **The register's own content was verified against a live source (the PRD), not invented**, and a dedicated test (`test_the_real_five_entry_register_content_round_trips`) round-trips the ACTUAL committed JSON file (skipped gracefully if the file is somehow absent from a given checkout, never a hard failure on that account) -- this is the closest this session could get to a live functional check without invoking the real CLI end to end against the real repo tree.

**Follow-up review recommendation: false** -- no open items.


### 2026-08-07 -- Adversarial review pass (Blind Hunter + Edge Case Hunter)

Dispatched with the diff file path only, no shared context.

- `low` `patch` **`run_upstream` conflated "unreadable" with "absent" and double-reported.** When `fs.read_text` raised `FsError` (e.g. a permission-denied register file that genuinely exists), the except-block correctly appended an accurate "cannot read" finding and set `text = None` to continue gracefully -- but the unconditional `if text is None:` check right after ALSO fired, appending a second, factually wrong finding claiming the register "is absent." Fixed: a new `unreadable` flag set in the `except FsError` branch now suppresses the redundant "is absent" finding on that path, so a real read failure reports exactly one finding. New test: `test_unreadable_register_reports_exactly_one_finding_never_also_absent`.

**Re-verification (2026-08-07, after the patch):** `pixi run --frozen -e pyforge-marshal python3 -m pytest src/shared/packages/pyforge-marshal/tests -q` -- **3036 passed** (full suite).

**Follow-up review recommendation (updated): false** -- narrow fix, covered by a dedicated regression test.

</intent-contract>
