---
title: 'The conformance matrix'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/architecture.md', '{project-root}/_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-6-5-conformance-smoke-in-an-ephemeral-home.md']
warnings: []
baseline_revision: 'HEAD as of 2026-08-07, immediately after S-6.5 (merged)'
---

<intent-contract>

## Intent

**Problem:** Stories 6.4/6.5 write RAW, machine-scoped probe and smoke
observations (`adapter-probes.json`/`adapter-smoke.json`, one host's own
transient facts, outside git) -- there is still no single, ACCUMULATED,
git-tracked artifact where those repeated observations turn into "adapter X
is proven to work here." FR-45 requires exactly one dated, tracked place
Marshal makes a portability claim, distinguishing `not-attempted` (no claim
made) from `unavailable` (attempted, absent) from `fail` from `pass` (AD-31),
so SM-6 ("adapters with a dated passing conformance smoke") can count `pass`
rows only and never be gamed by an uninstalled adapter's silent absence.

**Approach:** `core/conformance.py` gains a FOURTH, independent closed status
vocabulary (`STATUS_MATRIX_NOT_ATTEMPTED`/`STATUS_MATRIX_UNAVAILABLE`/
`STATUS_MATRIX_FAIL`/`STATUS_MATRIX_PASS` -- never merged into
`ALL_STATUSES` or either of the two prior pairs, AD-31's own "never
conflated, never sharing a constant" rule, mirroring `STATUS_SMOKE_*`'s own
precedent from S-6.5 even though three of the four string literals happen to
coincide), a pure `MatrixRow` dataclass, a pure `build_matrix_row` classifier
(no I/O -- takes an already-read smoke record, an already-read probe record,
an already-read clock instant, and a staleness threshold; the AC's own
"reporting clean for a check that cannot fail is a meta-test failure" rule
applied here as "a row can only be `pass` from a REAL smoke record", never
inferred), and a pure `render_matrix_markdown` formatter (markdown-table
shaping is not I/O -- mirrors `evaluate_conformance`'s own "the boundary
gathers facts, this module only classifies/shapes" split).

`build_smoke_record` (S-6.5) gains two new, additive, backward-compatible
keyword parameters -- `harness_version: str | None = None`,
`recorded_at: str | None = None` -- mirroring S-6.5's own `adapter=`
precedent on `render_policy_toml`/`write_policy_toml`. `cli/adapters.py::
run_adapters_smoke` is the one caller that now supplies both: `harness.
harness_version()` (an EXISTING `HarnessPort` method, never raises) and a
UTC ISO-8601 timestamp from a new local `_now_utc()` helper (mirrors `cli/
spin.py`'s/`cli/retire.py`'s own identically-named, un-injected helpers --
no `ClockPort` precedent exists for this file, and this story's own effort
does not introduce one).

`cli/adapters.py` gains the new standalone action `marshal adapters matrix
<slug> [--stale-after-days N] [--format]`. `run_adapters_matrix` needs no
loop home at all (unlike `sync`/`conform`/`probe`) -- it reads ONLY the two
existing machine-scoped files (`adapter-probes.json`/`adapter-smoke.json`,
via the EXISTING `_read_probe_state`/`_read_smoke_state` helpers verbatim)
plus this repo's own root (`cli/config.py::repo_root`, the SAME helper
`cli/deploy.py::run_promote` already uses to resolve `_bmad-output/
projects/<slug>/planning-artifacts/...`, AD-11's own target-(c) real path,
never the gitignored symlink) and this HOST's own hostname (`socket.
gethostname()`). For the UNION of adapter names named in either file,
`build_matrix_row` classifies each into a `MatrixRow`; `render_matrix_
markdown` renders the accumulated set; `fs.write_text_atomic` writes it to
`planning-artifacts/conformance/matrix/<hostname>.md` under the named
project's own tracked planning artifacts -- the ONLY place this package
writes a portability claim (AD-37's F-7 amendment).

## Boundaries & Constraints

**Always:**
- **The matrix's status vocabulary is a FOURTH, independent closed pair,
  never merged into `ALL_STATUSES`, `STATUS_AVAILABLE`/`STATUS_UNAVAILABLE`,
  or `STATUS_SMOKE_*`** (AD-31) -- even though `"unavailable"`/`"fail"`/
  `"pass"` coincide character-for-character with `STATUS_SMOKE_*`'s own
  values, AD-31's rule is about the CONSTANT/classification never being
  conflated, not about incidental string equality (S-6.5's own precedent for
  the identical situation against S-6.4's `STATUS_UNAVAILABLE`).
- **A row is `pass` if and only if a REAL smoke record with `status ==
  "pass"` exists for that adapter on this host.** No adapter is ever
  reported `pass` from a probe record alone, from silence, or from any
  inference -- `not-attempted` is the row for "no smoke record exists at
  all", structurally distinct from a genuine `unavailable`/`fail`/`pass`
  outcome (this is the AC's own gaming-resistance requirement, made
  structural).
- **`build_matrix_row`/`render_matrix_markdown` are pure** (no I/O, no
  `time`/`os`/`subprocess`/`pyforge.marshal.adapters` import, AD-4) -- every
  fact (the two already-read records, `now`, `stale_after_days`, `hostname`,
  `generated_at`) is gathered at the `cli/adapters.py` boundary and passed
  in.
- **The matrix is written to the TRACKED, per-host path
  `_bmad-output/projects/<slug>/planning-artifacts/conformance/matrix/
  <hostname>.md`** (AD-37's F-7 amendment, AD-11 target (c), the real path,
  never the gitignored `_bmad-output/planning-artifacts/` symlink) -- the
  ONLY place this package ever writes a portability claim.
- **`run_adapters_matrix` reuses `_read_probe_state`/`_read_smoke_state`
  verbatim** (S-6.4/S-6.5's own established "absent/unreadable/malformed all
  degrade to an empty collection, malformed registers a WARN" convention) --
  no third read-with-degrade routine.

**Never:**
- **No new machine-scoped write.** This story reads the two EXISTING
  machine-scoped files; it writes nothing under `_machine_state_dir()`.
- **No requirement that a loop home exist for the named slug.** Unlike
  `sync`/`conform`/`probe`, `matrix` needs no `HarnessPort`, no `FsPort.
  is_dir(home)` check, and no `_home_path` resolution at all -- only a
  valid project SLUG (naming which project's own tracked planning artifacts
  to write into) and this repo's own root.
- **No finding for staleness itself.** A stale row is DATA in the rendered
  table (the AC's own "rows older than a configured age are marked stale"),
  never a registered finding that would make an otherwise-successful matrix
  write report anything other than `clean` -- staleness is something an
  operator reads, not something this command blocks or warns on.
- **No second redaction vocabulary and no advisory lock.** The matrix write
  is a single, whole-file `write_text_atomic` of freshly-computed content
  (never a read-merge-write growing collection like `adapter-probes.json`),
  so neither `core.egress.to_redacted` nor `FsPort.acquire_advisory_lock`
  applies here the way they do to S-6.4/S-6.5's own machine-scoped writes.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| An adapter has a `status: "pass"` smoke record and a probe record | Ordinary success | Row: `status: "pass"`, `adapter_version` from the probe, `harness_version`/`date` from the smoke record, `failing_stage: null`, `stale` per age | No finding |
| An adapter has a `status: "fail"` smoke record | A real, observed failure | Row: `status: "fail"`, `failing_stage` named | No finding (the fail itself was already reported by `MRS-SMOKE-003` at smoke time; the matrix only records it) |
| An adapter has a `status: "unavailable"` smoke record | Attempted, host lacks the binary | Row: `status: "unavailable"` | No finding |
| An adapter appears in `adapter-probes.json` but has NO smoke record at all | Probed, never smoked | Row: `status: "not-attempted"` | No finding |
| An adapter's smoke record's `recorded_at` is older than `--stale-after-days` | Aging evidence | Row: `stale: true` | No finding (data, not a finding) |
| `adapter-probes.json` and/or `adapter-smoke.json` is malformed JSON or absent | Corrupt/missing bookkeeping | Treated as empty (mirrors `_read_probe_state`/`_read_smoke_state`); every adapter present in the OTHER file still gets a row | Registered finding (`MRS-MATRIX-001`, WARN) for a malformed (not merely absent) file |
| Writing the tracked matrix file fails (unwritable path, disk full) | I/O failure | The envelope still reports the computed `data.rows` (the OBSERVATION succeeded even if the WRITE did not) | Registered finding (`MRS-MATRIX-002`, ERROR) |
| The named project slug is malformed | Bad input | No filesystem/state read at all | Registered finding (`MRS-ADP-001`, ERROR -- reused verbatim, same tier, second call site, per `MRS-DEPLOY-003`'s own precedent) |
| Neither machine-scoped file has ever been written (fresh host) | No prior probe/smoke ever run | `data.rows == []`; an empty matrix file is still written (a real, dated "nothing attempted yet" claim) | No finding |

</intent-contract>

## Code Map

- `src/pyforge/marshal/core/conformance.py` -- EDIT. New status constants
  `STATUS_MATRIX_NOT_ATTEMPTED`/`STATUS_MATRIX_UNAVAILABLE`/
  `STATUS_MATRIX_FAIL`/`STATUS_MATRIX_PASS`. New frozen dataclass
  `MatrixRow` (`adapter: str`, `status: str`, `adapter_version: str | None`,
  `harness_version: str | None`, `date: str | None`, `failing_stage: str |
  None`, `stale: bool`). New pure `build_matrix_row(adapter, *, smoke_record,
  probe_record, now, stale_after_days) -> MatrixRow`. New pure
  `render_matrix_markdown(rows, *, hostname, generated_at) -> str`.
  `build_smoke_record` gains `harness_version=None`/`recorded_at=None`
  keyword parameters, both folded into the returned dict.
- `src/pyforge/marshal/cli/adapters.py` -- EDIT. Module-level `import
  socket`; `from datetime import datetime, timezone`; `from .config import
  repo_root` (extends the existing `from .config import
  _suppress_downstream_pipe_close` import). New `_now_utc() -> datetime`
  helper (mirrors `cli/spin.py`/`cli/retire.py`'s own identical helpers).
  New constant `_MATRIX_STALE_AFTER_DAYS_DEFAULT = 30`. New
  `add_adapters_subparser` nested action `matrix` (`marshal adapters matrix
  <slug> [--stale-after-days N] [--format]`). New `_render_text_matrix(data,
  findings) -> str`. New `run_adapters_matrix(args, *, fs=None,
  context=None)`. `run_adapters_smoke` gains two new calls at its existing
  `build_smoke_record` call site: `harness.harness_version()` and
  `_now_utc().isoformat()`, threaded through as the two new keyword
  arguments.
- `src/pyforge/marshal/core/findings.py` -- EDIT. Register two new codes:
  `MRS-MATRIX-001` (a pre-existing `adapter-probes.json`/`adapter-smoke.json`
  was malformed JSON), `MRS-MATRIX-002` (writing the tracked matrix file
  failed).
- `src/pyforge/marshal/core/verdict.py` -- EDIT. `MRS-MATRIX-001` ->
  `Verdict.WARN` (mirrors `MRS-ADP-016`/`MRS-SMOKE-007`'s "degrades, never
  blocks" tier). `MRS-MATRIX-002` -> `Verdict.ERROR` (mirrors
  `MRS-ADP-015`/`MRS-SMOKE-006`'s "a real write was attempted and failed"
  tier).
- `src/pyforge/marshal/schemas/conformance.json` -- NEW. A JSON Schema
  document describing one `MatrixRow`'s JSON shape (mirrors `schemas/
  gate-record.json`'s own documentation-only, tested-in-`tests/`-only
  convention -- `src/` never runtime-validates against it).
- `tests/unit/test_conformance.py` -- EDIT. `build_matrix_row` matrix: no
  smoke record -> `not-attempted`; each of the three real smoke statuses;
  `adapter_version`/`harness_version`/`date`/`failing_stage` threaded
  through; stale/not-stale by age; a malformed/non-string `recorded_at`
  degrades to `stale: false`, `date: None`, never raises.
  `render_matrix_markdown` shape matrix (empty rows, multiple rows, sorted
  by adapter name). `STATUS_MATRIX_*` never appear in `ALL_STATUSES`,
  `STATUS_AVAILABLE`/`STATUS_UNAVAILABLE`, or `STATUS_SMOKE_*`.
  `build_smoke_record`'s new keyword parameters default to `None` and are
  additive (an existing call site omitting them is unaffected).
- `tests/unit/test_adapters_cli.py` -- EDIT. `run_adapters_matrix` matrix
  reusing the existing `FakeFs` double: pass/fail/unavailable/not-attempted
  rows, stale vs not-stale, malformed probe/smoke JSON (`MRS-MATRIX-001`,
  merge preserves the other file's entries), write failure
  (`MRS-MATRIX-002`), malformed slug (`MRS-ADP-001`), empty-state fresh
  host, `--format text` rendering, and a round-trip proving the WRITTEN
  markdown's content matches `render_matrix_markdown`'s own output.
  `run_adapters_smoke`'s existing test matrix extended: the written
  `adapter-smoke.json` entry now carries `harness_version`/`recorded_at`.
- `tests/unit/test_conformance_schema.py` -- NEW. `jsonschema.validate`s a
  `build_matrix_row` output's `to_json_dict`-equivalent shape (a plain
  `dataclasses.asdict`) against `schemas/conformance.json`.

## Design Notes

- **Why `matrix` needs no loop home.** `sync`/`conform`/`probe` all operate
  ON a provisioned loop home's own live filesystem state. `matrix`
  accumulates ALREADY-WRITTEN machine-scoped observations (S-6.4/S-6.5's own
  raw facts) into a tracked artifact -- it never touches a loop home at all,
  the same "machine-and-adapter fact, independent of any one project" shape
  `adapters smoke` already established for its own no-slug design. The one
  difference from `smoke`: the WRITE target (a tracked artifact under a
  named project's own `planning-artifacts/`) genuinely needs a project slug
  to resolve, so `matrix` keeps the `sync`/`conform`/`probe` positional-slug
  shape rather than `smoke`'s slug-free one.
- **Why staleness is data, never a finding.** AD-31's "the context lives in
  the code, never in a second argument" already governs this codebase's
  every other status/severity split. A stale-but-still-`pass` row is not a
  NEW fact this command discovered wrong -- it is the SAME `pass` outcome,
  aging. Turning it into a WARN finding would make `marshal adapters matrix`
  report red on every host that has not re-run `smoke` recently, which
  contradicts the AC's own framing ("rows older than a configured age are
  marked stale" -- marked IN THE ROW, not escalated).
- **Why `harness_version`/`recorded_at` were added to `build_smoke_record`
  rather than gathered fresh by `matrix` itself.** The matrix's own "harness
  version" and "date" columns are per-SMOKE facts (which bmad-loop version
  ran the smoke, and when) -- gathering them at MATRIX-BUILD time would
  report the CURRENT host's harness version/today's date for every row,
  which is wrong for a row whose smoke ran days or weeks ago on a since-
  upgraded host. The smoke run itself is the only point in time that fact is
  actually known, so it is captured there, mirroring `build_probe_record`'s own
  "the caller already gathered every fact, this function only shapes"
  convention that this whole module already establishes.

## Verification

- `pixi run --frozen -e pyforge-marshal python3 -m pytest src/shared/packages/pyforge-marshal/tests -q`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test`
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache`

**Actual results (2026-08-07):**
- `pixi run --frozen -e pyforge-marshal python3 -m pytest src/shared/packages/pyforge-marshal/tests -q` (the FULL suite) -- **2981 passed** (2952 baseline from S-6.5 + a net 29 new: 15 `build_matrix_row`/`render_matrix_markdown`/vocabulary tests in `test_conformance.py`, 6 jsonschema tests in the new `test_conformance_schema.py`, 11 `run_adapters_matrix`/smoke-record tests in `test_adapters_cli.py` -- minus the one existing `test_build_smoke_record_shape` updated in place rather than duplicated).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 3 failed, all pre-existing accepted baseline (identical to S-6.5's own record: 2 `pyforge-steward`, 1 `pyforge-doctor`), unrelated to this story.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` -- AD-3, AD-4, AD-9 all KEPT (88 files, 490 dependencies analyzed).

## Review Triage Log

Self-review pass against the diff (no separate adversarial dispatch requested this session -- three stories landed in one continuous pass; see the Epic 6 retro notes). Findings addressed during implementation itself, before any test ran red:

- **Defensive status mapping in `build_matrix_row`.** An unrecognized/non-string `smoke_record["status"]` (a hand-edited or future-shape `adapter-smoke.json` entry) degrades to `STATUS_MATRIX_NOT_ATTEMPTED` rather than raising or silently fabricating a `pass` -- covered by `test_matrix_row_unrecognized_smoke_status_degrades_to_not_attempted`.
- **No read-modify-write race on the matrix file itself.** Unlike `adapter-probes.json`/`adapter-smoke.json` (both growing, advisory-locked collections), the matrix write is a single, whole-file `write_text_atomic` of freshly-computed content on every run -- there is no prior state to merge, so no lock is needed; stated explicitly in this spec's own Boundaries & Constraints so a future editor does not add one under a mistaken "every machine-scoped-adjacent write needs a lock" generalization.
- **Malformed-file finding re-coding.** `_read_probe_state`/`_read_smoke_state` register `MRS-ADP-016`/`MRS-SMOKE-007` for a malformed file -- `run_adapters_matrix` re-wraps those into its own `MRS-MATRIX-001` rather than letting a sibling command's own code leak into this envelope (a caller filtering `codes` for `"adapters matrix"`'s own area would otherwise see a code from a command it never invoked).

**Follow-up review recommendation: false** -- no open items; the two deliberate scope boundaries (staleness is data, never a finding; the write target is the named project's own tracked planning artifacts, not a hardcoded self-referential path) are recorded decisions, not deferred work.


### 2026-08-07 -- Adversarial review pass (Blind Hunter + Edge Case Hunter)

Dispatched with the diff file path only, no shared context. Two findings landed here:

- `medium` `patch` **`build_matrix_row` silently dropped a known `adapter_version` when the adapter had been probed but never smoked.** The `smoke_record is None` short-circuit hardcoded `adapter_version=None`, ignoring `probe_record` entirely -- contradicting both the function's own docstring and the packaged schema, which state `adapter_version` should be `null` only "if never probed or unavailable," not "if never smoked." Fixed: `adapter_version` is now extracted from `probe_record` FIRST, before either not-attempted short-circuit, so a real probe fact is never discarded. New test: `test_matrix_row_no_smoke_record_still_reports_a_known_probed_version`.
- `medium` `patch` **A row could report `status=not-attempted` while simultaneously claiming `stale=True` with a populated `date`/`harness_version`.** When `smoke_record` carried an UNRECOGNIZED `status` (e.g. a hand-edited/corrupt `adapter-smoke.json`), the function correctly degraded `status` to `not-attempted` but still fell through and computed `date`/`stale`/`harness_version` from the record's other fields -- self-contradictory with the documented "stale is always false for not-attempted -- no claim exists to age" invariant. Fixed: the not-attempted-via-unrecognized-status path now short-circuits identically to the no-smoke-record-at-all path (still preserving `adapter_version` from `probe_record`, per the fix above). New test: `test_matrix_row_unrecognized_status_never_reports_stale_or_date`.

**Re-verification (2026-08-07, after both patches):** `pixi run --frozen -e pyforge-marshal python3 -m pytest src/shared/packages/pyforge-marshal/tests -q` -- **3036 passed** (full suite, including this Epic's 6.7/6.8 stories).

**Follow-up review recommendation (updated): false** -- both findings are narrow, each covered by a dedicated regression test.

</intent-contract>
