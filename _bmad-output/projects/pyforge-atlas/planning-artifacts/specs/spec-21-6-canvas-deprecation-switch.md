---
title: 'Canvas deprecation switch (both default) (Story 22.6, Epic 22, optional follow-on)'
type: 'feature'
created: '2026-08-30'
status: 'done'
review_loop_iteration: 0
baseline_revision: 'NO_VCS'
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/vizro-canvas-parity.md'
---

<intent-contract>

## Intent

**Problem:** The three Cursor Canvas identity writers (`write_canvas` in
`scripts/conda-forge-packaging-inventory-operations_priority.py`; `write_ops_canvas` /
`write_workbook_canvas` in `scripts/openteams_identity_dashboards.py`, invoked from
`scripts/conda-forge-packaging-inventory-operations_openteams_identity.py`'s
`write_dashboard_markdown()`) run unconditionally whenever the quartet's existing
`--canvas` / gist-publish flags are already satisfied -- there is no way for an operator to
opt out of the Cursor-canvas regeneration cost (extra file writes; `write_workbook_canvas`'s
second `load_workbook` open) once Story 22.5's parity gate is green, short of hand-patching the
scripts.

**Approach:** Add an `INVENTORY_IDENTITY_UI` env-var-controlled mode (`both` | `canvas` |
`vizro`, default `both`) read independently in each of the two quartet scripts (no shared
module exists between `priority.py` and `openteams_identity.py` today -- confirmed by direct
inspection; this mirrors the already-accepted `_cf_atlas_db_path()` duplication precedent
between `vcs_sources.py`/`request_datasets.py`, spec-21-2). `both` and `canvas` behave
identically in this story's code paths (canvas writers run, unchanged); `vizro` skips ONLY the
canvas-writing calls -- it does **not** gate the Vizro dashboard's own availability
(`dashboard-serve` is a separate, always-running process that reads whatever Parquet exists,
independent of this flag) and it does **not** gate Story 22.1's `identity_ranked_export.parquet`
write path (that Parquet must keep writing in every mode, or `vizro` mode would starve the very
pages an operator opted into). This story ships the switch only -- **no canvas writer is
removed or made default-off**; per `stories.yaml`'s own `invoke_dev_with` note ("defer removing
canvas writers until operator opts in"), full removal is an explicit future step gated on the
operator's own choice after N releases of a green Story 22.5 parity gate (N intentionally
unspecified -- an operator judgment call, not this story's decision).

## Boundaries & Constraints

**Always:**
- Mirror the existing `GIST_ID_ENV = "OPENTEAMS_IDENTITY_GIST_ID"` module-constant-then-
  `os.environ.get(...)` style already in `openteams_identity.py` (~L82, ~L292) -- add
  `INVENTORY_IDENTITY_UI_ENV = "INVENTORY_IDENTITY_UI"` the same way in both files.
- Never raise on an unset, blank, or unrecognized value -- degrade to `"both"` (this repo's
  standing convention for a misconfigured env-var gate, e.g. spec-21-2's
  `PYPI_JSON_FANOUT_LIMIT` non-numeric-degrades-to-default rule). Match case-insensitively and
  strip whitespace (`.strip().lower()`).
- Gate ONLY the two identified call sites (`priority.py`'s `write_canvas` invocation;
  `write_dashboard_markdown`'s two canvas try/except blocks) -- never touch gist-markdown
  writing (`write_gist_markdown`/`render()`), `--skip-gist`, `--gist-only`, or any Parquet/JSON
  export path.
- `write_dashboard_markdown`'s existing per-canvas try/except resilience (a canvas write
  failure must never block the gist-markdown publish above it) stays unchanged -- the new mode
  check is an ADDITIONAL early-exit placed before those two try blocks, not a replacement of
  the failure handling.
- `priority.py`'s existing `if args.canvas:` gate stays -- the new mode check composes with it
  as an `and` condition (`vizro` mode only matters when `--canvas` was already going to fire).
- This is a `recipes/`-external change (`src/shared/packages/pyforge-atlas/**` is not touched by
  this story, but `scripts/**` and `tests/packaging/**` are) -- per CLAUDE.md's PR-CI-gates
  rule, the PR must carry the `maintenance` label
  (`gh pr edit <n> --repo rxm7706/local-recipes --add-label maintenance`).

**Block If:** None -- the two call sites and the existing `GIST_ID_ENV` style precedent fully
resolve how and where this flag is read; no human decision is needed.

**Never:**
- Do not remove, deprecate, or make default-off any of `write_canvas` / `write_ops_canvas` /
  `write_workbook_canvas` -- removal is an explicit future story, gated on operator opt-in.
- Do not gate `dashboard-serve` or any Vizro `dashboard/app.py` / `dashboard/data.py` code --
  the Vizro dashboard has no "enable/disable" switch of its own and this story does not add one.
- Do not gate Story 22.1's `identity_ranked_export.parquet` write path, or any gist-markdown /
  `--skip-gist` / `--gist-only` behavior.
- Do not introduce a shared module between `priority.py` and `openteams_identity.py` solely for
  this one flag -- match the existing per-file duplication pattern (Simplicity First; a shared
  module is a heavier change than the flag itself).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Unset env var | No `INVENTORY_IDENTITY_UI` | Default `both`: canvas writers run unchanged (regression) | n/a |
| `INVENTORY_IDENTITY_UI=vizro` | Any case/whitespace, e.g. `"Vizro"`, `" vizro "` | `priority.py`: `write_canvas` NOT called even when `--canvas` is set; skip message printed. `openteams_identity.py`: neither `write_ops_canvas` nor `write_workbook_canvas` called; skip message printed; gist markdown (`dash_path`) still written and published | Never raise |
| `INVENTORY_IDENTITY_UI=canvas` | Explicit | Identical to `both` today: canvas writers run | n/a |
| `INVENTORY_IDENTITY_UI=both` | Explicit | Canvas writers run (regression, same as unset) | n/a |
| Unrecognized value, e.g. `"vizr0"` | Typo | Degrades to `both` (canvas writers run) | Never raise |
| `--skip-gist` set | Any UI mode | `write_dashboard_markdown` is never called from `main()`'s gist-publish branch at all -- the UI-mode gate is moot there (unaffected, pre-existing short-circuit) | n/a |
| `--gist-only` set | Any UI mode | `publish_gist_from_tab()` still calls `write_dashboard_markdown` -- the UI-mode gate applies there identically to the `main()` path | n/a |
| A real canvas-write failure (`vizro` mode NOT set) | e.g. an unwritable path | Existing try/except behavior unchanged: failure logged, publish continues -- distinguishable in output from a `vizro`-mode skip message (different text) | Logged, never raised |

</intent-contract>

## Code Map

- `scripts/conda-forge-packaging-inventory-operations_priority.py` -- module imports (~L20-30,
  no `import os` today -- must be added); `write_canvas` def (~L250); `--canvas` argparse arg
  (~L590-597); the gated invocation site (~L809-812, `if args.canvas: ... write_canvas(...)`).
- `scripts/conda-forge-packaging-inventory-operations_openteams_identity.py` -- `GIST_ID_ENV`
  constant (~L82) and its `os.environ.get(GIST_ID_ENV, "").strip()` read (~L292) as the exact
  style precedent; `write_dashboard_markdown()` def (~L1119-1157) -- the gist-markdown
  `path.write_text(...)` call (~L1141-1144) followed by the two try/except canvas-write blocks
  (~L1149-1157) this story wraps with the new mode check; both existing callers,
  `publish_gist_from_tab()` (~L1230) and `main()` (~L1497), get the gate for free since it lives
  inside `write_dashboard_markdown` itself -- no caller-site changes needed.
- `tests/packaging/test_openteams_handoffs.py` -- `_load_module` helper (~L50-67) and the
  already-loaded `identity`/`priority`/`dashboards` module handles (~L70-73);
  `test_write_dashboard_markdown_survives_a_canvas_write_failure` (~L295-329) -- the direct
  sibling precedent for testing `write_dashboard_markdown`'s canvas-related control flow via
  `monkeypatch.setattr(dashboards, "write_ops_canvas", ...)` -- extend this file rather than
  creating a new one (Surgical Changes; the module-loading infrastructure already exists here).
- `pixi.toml` -- `[feature.local-recipes.tasks.test-packaging]` (~L1118-1120, `cmd = "pytest
  tests/packaging -q"`) -- the verification command for this story's new tests; no change
  needed (new tests land inside the already-collected `tests/packaging/` tree).

## Tasks & Acceptance

**Execution:**
- `scripts/conda-forge-packaging-inventory-operations_priority.py`:
  - Add `import os` to the existing import block.
  - Add `INVENTORY_IDENTITY_UI_ENV = "INVENTORY_IDENTITY_UI"` near the top-level constants
    (mirrors `openteams_identity.py`'s `GIST_ID_ENV` placement style).
  - Add `_identity_ui_mode() -> str`: `os.environ.get(INVENTORY_IDENTITY_UI_ENV, "both").strip()
    .lower()`, returning `"both"` when the result is not one of `{"both", "canvas", "vizro"}`.
  - Change the invocation at ~L809-812 to:
    ```python
    if args.canvas and _identity_ui_mode() != "vizro":
        args.canvas.parent.mkdir(parents=True, exist_ok=True)
        write_canvas(args.canvas, records, counts, args.tab)
        print("wrote", args.canvas)
    elif args.canvas:
        print(f"Skipped canvas write ({INVENTORY_IDENTITY_UI_ENV}=vizro)")
    ```
  - Document the flag in `--canvas`'s argparse `help=` text (one line, mirrors `--gist-id`'s
    existing "Never commit the id" style pointer).
- `scripts/conda-forge-packaging-inventory-operations_openteams_identity.py`:
  - Add `INVENTORY_IDENTITY_UI_ENV = "INVENTORY_IDENTITY_UI"` near `GIST_ID_ENV` (~L82) and an
    `_identity_ui_mode() -> str` helper with identical logic to `priority.py`'s (duplicated, per
    Boundaries -- no shared module).
  - In `write_dashboard_markdown()`, immediately after the gist-markdown `path.write_text(...)`
    call and before the first `try:` block, insert:
    ```python
    if _identity_ui_mode() == "vizro":
        print(f"Skipped ops/workbook canvas write ({INVENTORY_IDENTITY_UI_ENV}=vizro)")
        return
    ```
    Verify at implementation time that nothing follows the two try/except blocks in the current
    function body (confirmed true as of this spec's authoring) so this early `return` is safe.
  - Add one line to the module docstring documenting `INVENTORY_IDENTITY_UI` (mirrors the
    existing `OPENTEAMS_IDENTITY_GIST_ID` docstring mention, ~L21-23).
- `tests/packaging/test_openteams_handoffs.py`:
  - Unit tests for `priority._identity_ui_mode()` and `identity._identity_ui_mode()`: default
    (`"both"` when unset), case/whitespace-insensitive `"vizro"` recognition, and an
    unrecognized value degrading to `"both"`.
  - `test_write_dashboard_markdown_skips_both_canvases_in_vizro_mode` --
    `monkeypatch.setenv("INVENTORY_IDENTITY_UI", "vizro")`; spy on (or `monkeypatch.setattr` a
    call-recording stub for) `dashboards.write_ops_canvas` and `dashboards.write_workbook_canvas`;
    call `write_dashboard_markdown(...)`; assert neither was called AND the gist-markdown
    `path.write_text` output file still exists with content (the gist path is never gated).
  - `test_write_dashboard_markdown_writes_both_canvases_by_default` (and one more parametrized
    case for explicit `"both"`/`"canvas"`) -- regression lock asserting both canvases ARE still
    written when the env var is unset or explicitly `"both"`/`"canvas"`.
  - `test_priority_write_canvas_skipped_in_vizro_mode` -- exercise `priority.py`'s
    `_identity_ui_mode()` gate directly (unit-level, not a full `main()` invocation, to avoid
    needing a real xlsx fixture) by calling the guarded block's logic as extracted into
    `_identity_ui_mode()`, plus one light integration check that `args.canvas and
    _identity_ui_mode() != "vizro"` evaluates `False` under `vizro` mode.

**Acceptance Criteria:**
- Given no `INVENTORY_IDENTITY_UI` set and `--canvas` set, when `priority.py` runs, then
  `write_canvas` executes exactly as before this story (regression).
- Given `INVENTORY_IDENTITY_UI=vizro` and `--canvas` set, when `priority.py` runs, then
  `write_canvas` is NOT called, a skip message is printed, and all other behavior (xlsx write,
  inventory sync) is unchanged.
- Given `INVENTORY_IDENTITY_UI=vizro`, when `openteams_identity.py` reaches
  `write_dashboard_markdown` (via either the `main()` gist-publish path or `--gist-only`), then
  neither `write_ops_canvas` nor `write_workbook_canvas` is called, the gist-markdown file is
  still written and published, and a skip message is printed.
- Given `INVENTORY_IDENTITY_UI` unset, `both`, `canvas`, or an unrecognized value, when
  `openteams_identity.py` reaches `write_dashboard_markdown`, then both `write_ops_canvas` and
  `write_workbook_canvas` are called exactly as before this story (regression, covering default
  + explicit + invalid-degrades-safely in one assertion set).
- Given any `INVENTORY_IDENTITY_UI` value, when Story 22.1's `identity_ranked_export.parquet`
  write path runs, then it is unaffected -- it is not one of this story's two gated call sites.
- Given `pixi run --frozen -e local-recipes test-packaging`, when run after this story, then it
  passes, including the new mode-gating tests.

## Spec Change Log

<!-- Empty -- no review loopback has occurred yet. -->

## Design Notes

`both` and `canvas` have **no behavioral difference** in this story's code paths -- both keep
canvas writers on. The third value exists because `vizro-canvas-parity.md` § 22.6 and
`stories.yaml`'s `done_checkpoint` literally specify a three-way
`INVENTORY_IDENTITY_UI=both|vizro|canvas` contract, and preserving all three values now (rather
than shipping a two-way `vizro|not-vizro` flag) avoids a future rename if a later story ever
gives `canvas` a distinct meaning from `both` (e.g., something Vizro-side to disable once the
dashboard gains its own on/off switch -- no such switch exists today, so there is nothing for
`canvas` to additionally do yet). This story does not need to, and does not, invent a
distinction that the source docs do not require.

This story deliberately stops at the switch. The actual deprecation -- removing
`write_canvas`/`write_ops_canvas`/`write_workbook_canvas` or flipping the default away from
`both` -- is out of scope by design (`stories.yaml`'s `invoke_dev_with`: "defer removing canvas
writers until operator opts in"); no follow-up story number is assigned in `stories.yaml` for
that removal as of this spec's authoring, so it is not referenced here as a specific future
story ID.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- `INVENTORY_IDENTITY_UI=vizro python scripts/conda-forge-packaging-inventory-operations_priority.py --xlsx <fixture.xlsx> --canvas /tmp/should-not-exist.canvas.tsx` --
  confirm the file is NOT created and a skip message appears on stdout.

## Auto Run Result

Status: done
Reconciled 2026-09-20: the `in-review` verdict below is the session's own record at halt time; the story was landed afterwards and the ledger row promoted to `done` by `86d1cdf3ee 2026-09-17 land atlas fold: one chain — 13 Dreams, 10 Specs, rekey 2026-09-17` — that promotion is the ruling this record now reflects.

Summary: Added `INVENTORY_IDENTITY_UI` env-var gate (`both` | `canvas` | `vizro`, default `both`) to
`conda-forge-packaging-inventory-operations_priority.py` and
`conda-forge-packaging-inventory-operations_openteams_identity.py`. In `vizro` mode, canvas writers
are skipped while gist-markdown and Parquet export paths remain unchanged. Eighteen new/extended unit
tests in `tests/packaging/test_openteams_handoffs.py` cover mode parsing, vizro skip, and regression
for default/both/canvas modes.

Verification:
- `pixi run -e local-recipes pytest tests/packaging/test_openteams_handoffs.py -k "identity_ui_mode or write_dashboard_markdown_skips or write_dashboard_markdown_writes_both or priority_write_canvas"`: 18 passed
- `pixi run -e pyforge-atlas kedro-catalog-check`: 68 passed
- `pixi run -e pyforge-atlas kedro-test`: 1719 passed, 1 failed — pre-existing
  `test_identity_catalog_parity_with_write_canvas` (dashboard catalog row ordering), unrelated to this
  story's script-only scope
- `pixi run -e local-recipes test-packaging`: 172 passed, 2 failed — pre-existing
  `ModuleNotFoundError: pyforge.atlas` in gist integration tests, unrelated to Story 22.6

PR note: non-`recipes/` change requires `maintenance` label at PR open.

## Status reconcile 2026-09-20

- frontmatter `status` `in-review` → `done` (ledger row `21-6-canvas-deprecation-switch: done`).
- Auto Run Result `Status: in-review` → `done` (see the reconcile line under it).
