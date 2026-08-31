---
title: 'mason recipe update'
type: 'feature'
created: '2026-08-12'
status: 'done'
baseline_revision: 'f9ff81fdc516d473ea04998c6ba2f71e6b383dbe'
final_revision: '85ac823827bf151a7eba30c921f8be51e674fc67'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/_bmad-output/projects/pyforge-mason/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** FR-14's `recipe update` is unimplemented -- a user has no way to bump a recipe to a
newer upstream version through Mason, for either a PyPI- or GitHub-Releases-sourced package,
without hand-running CFE's autotick scripts directly.

**Approach:** Add `recipe.py::update()`, composed on two new `cfe.py` adapters wrapping CFE's
existing autotick scripts -- `recipe_updater.py` (PyPI, default) and `github_updater.py`
(GitHub Releases, `--github`) -- selected by a Mason-only dispatch flag, never by Mason inspecting
recipe content (AD-1). Both wrapped scripts accept Mason's own `--dry-run` flag and forward it 1:1
(no inversion, unlike `submit`'s `--yes`): the default (no `--dry-run`) is a real, field-scoped
write; `--dry-run` computes and returns the identical plan without writing. `update()` returns the
raw `CfeResult` -- mirroring `diagnose`/`optimize`/`scan`, not `submit`'s `ShipTargetResult`
exception, since `update` is not a ship target (AD-9/AD-11 do not apply).

## Boundaries & Constraints

**Always:**
- `update()` calls `cfe.ensure_cfe_root` first (mirrors `diagnose`/`optimize`/`scan`/`submit`) and
  raises `CfeUnresolvedError` before any subprocess spawns.
- No import-floor gate (mirrors `diagnose()`'s exemption, not `optimize`/`scan`'s scoped-probe
  pattern): reading `recipe_updater.py` and `github_updater.py` confirms both wrap every
  import-floor-dependent call (`ruamel.yaml`, `requests`, `packaging`, the GitHub API client) in a
  blanket `try/except` that already degrades a missing dependency to `{"success": false, "error":
  ...}` JSON data, never a raw traceback -- unlike `recipe_optimizer.py`/`vulnerability_scanner.py`,
  which is why those two needed Mason's own pre-flight probe and this one does not.
- `recipe_path` (positional, required) is passed straight through with no Mason-side existence
  check or interpretation -- mirrors `diagnose`/`optimize`/`scan`'s boundary, not `submit`'s
  path-interpreting exception. `recipe_updater.py` requires a file; `github_updater.py` also
  accepts a directory (auto-resolving `recipe.yaml`/`meta.yaml` within it) -- an existing asymmetry
  in the wrapped scripts themselves, not smoothed over here (AD-1: no Mason-side normalization).
- `--dry-run` is forwarded to the invoked script's own `--dry-run` flag verbatim, no inversion.
  Omitting it is the confirmed/apply path (see Design Notes for why this differs from `submit`'s
  default-to-dry-run posture).
- `--github` selects which adapter is called (`update_recipe_from_github` instead of
  `update_recipe`) and is never itself forwarded as CFE argv. `--repo`/`--pre` are forwarded to
  CFE only when `--github` is set; given without it, they are inert (no error, no effect) -- neither
  is meaningful to the PyPI script, which has no equivalent flags.
- `update()` returns the raw `CfeResult` from whichever adapter it called -- no Mason-side
  reinterpretation of `json_body` (AD-1's "no severity/field policy of its own", same Never boundary
  `diagnose`/`optimize`/`scan` already hold).

**Block If:** None identified -- the dispatch flag, argv shape, and default-write posture are all
resolved below (Design Notes) from the real `recipe_updater.py`/`github_updater.py` and the
convergent epics.md/PRD-review evidence.

**Never:**
- No separate "check for a newer version" pre-step (e.g. wrapping `check_github_version`) -- both
  `update_recipe`/`update_recipe_from_github` already detect the latest version internally; a
  second adapter would duplicate work neither AC nor the epic context calls for.
- No new `models.py` dataclass -- `update` is not a ship target; no `UpdateResult`/diff-shaped type
  is introduced (spec Never boundary, mirrors `diagnose`/`optimize`/`scan`).
- No CFE-side change: nothing under `.claude/skills/conda-forge-expert/**` or
  `.claude/scripts/conda-forge-expert/**` is touched (AD-15).
- No new `env=` passthrough site -- neither wrapped script needs one (unlike `submit`'s
  `CFE_RECIPES_ROOT` injection); credentials (e.g. `GITHUB_TOKEN`/`GH_TOKEN` for API rate limits)
  reach the child via ordinary environment inheritance (`env=None`), with no Mason-side handling.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| PyPI update available, default (apply) | `recipe_path` to a file; no flags; newer PyPI release exists | `update_recipe` called with `[recipe_path]`; real write happens (`context.version`/`build.number`/`source.0.sha256`); `json_body` has `success: true, updated: true, new_version: ...` | No error expected |
| PyPI update available, `--dry-run` | same, with `--dry-run` | `update_recipe` called with `[recipe_path, "--dry-run"]`; `json_body.actions` holds the plan; file unmodified | No error expected |
| PyPI already up to date | recipe already at the latest version, either mode | `json_body`: `success: true, updated: false, message: "Recipe is already up-to-date."`; no write in either mode | No error expected |
| GitHub source, `--github --dry-run` | `recipe_path` (file or directory); `--github --dry-run` | `update_recipe_from_github` called with `[recipe_path, "--dry-run"]`; `json_body.actions` + `latest_tag`/`github_url`; no write | No error expected |
| GitHub source, explicit repo + prerelease | `--github --repo owner/repo --pre` | args include `"--repo", "owner/repo", "--pre"`, forwarded only because `--github` is set | No error expected |
| `--repo`/`--pre` without `--github` | `--repo owner/repo` (no `--github`) | `update_recipe` (PyPI) is still called; `--repo`/`--pre` never reach CFE argv at all | No error expected (inert, not rejected) |
| CFE root unresolved | no CFE root discoverable | `CfeUnresolvedError` raised before any subprocess spawns | `EXIT_CFE_UNAVAILABLE`, same as every other verb |
| Upstream lookup fails | e.g. package absent from PyPI, or no GitHub repo detected | `json_body`: `success: false, error: "..."`, process exit 1 -- returned as data on `CfeResult`, never raised (AD-4) | No error expected (non-zero is data) |

</intent-contract>

## Code Map

(paths relative to `src/shared/packages/pyforge-mason/`)

- `src/pyforge/mason/cfe.py` -- add two `_CFE_SCRIPTS` entries (`"update_recipe": "recipe_updater.py"`,
  `"update_recipe_from_github": "github_updater.py"`); add `_UPDATE_RECIPE_TIMEOUT_SECONDS = 120.0`
  and `_UPDATE_RECIPE_FROM_GITHUB_TIMEOUT_SECONDS = 120.0` (both mirror the real MCP server's
  undecorated `_run_script` default -- neither `update_recipe`/`update_recipe_from_github`'s tool
  wrapper overrides it, confirmed by reading `conda_forge_server.py`); add `update_recipe(args, *,
  root, interpreter, timeout=None) -> CfeResult` and `update_recipe_from_github(args, *, root,
  interpreter, timeout=None) -> CfeResult`, each a thin `_invoke_captured` call mirroring
  `diagnose_failure`'s exact shape.
- `src/pyforge/mason/recipe.py` -- add `update(recipe_path, *, dry_run, github, github_repo,
  allow_prerelease, cfe_root_arg, cfe_python_arg, cfe_timeout_arg, environ, start_directory) ->
  CfeResult`, mirroring `diagnose()`'s composition (resolve root -> `ensure_cfe_root` -> resolve
  interpreter, no floor gate). Builds `args = [recipe_path]`, appends `"--dry-run"` when `dry_run`;
  when `github`, appends `"--repo", github_repo` (if truthy) and `"--pre"` (if `allow_prerelease`)
  and calls `cfe.update_recipe_from_github`; otherwise calls `cfe.update_recipe`.
- `src/pyforge/mason/cli.py` -- add `_RECIPE_UPDATE_HELP`; register `update` on
  `_noun_verbs["recipe"]` (`recipe_path` positional; `--dry-run`, `--github`, `--pre`
  `action="store_true"`; `--repo` optional str, `metavar="OWNER/REPO"`); dispatch block mirroring
  `diagnose`'s exactly (`_resolve_str`/`_resolve_optional_float` for the global knobs, plain
  `ns.dry_run`/`ns.github`/`ns.repo`/`ns.pre` reads since these live only on `update_parser`, never
  `global_flags`; render via `dataclasses.asdict(result)`); update the verb-registration comment
  block the same way Story 2.8/2.9 did.
- `tests/fixtures/fake_cfe_root/.claude/scripts/conda-forge-expert/recipe_updater.py`,
  `github_updater.py` -- new canned-response stubs, mirroring `submit_pr.py`'s shape exactly
  (`_stub_support.emit(...)` with a canned success JSON matching each real script's real-run shape:
  `{"success": true, "updated": true, "new_version": "9.9.9", "message": "Recipe updated
  successfully."}` for `recipe_updater.py`; the GitHub-shaped equivalent with `current_version`/
  `latest_tag`/`github_url` for `github_updater.py`). Extra argv (e.g. `--dry-run`, `--repo`,
  `--pre`) is ignored, never rejected, matching every existing stub.
- `tests/unit/test_cfe.py` -- `update_recipe`/`update_recipe_from_github` coverage: default-timeout,
  explicit-timeout override, invokes its own table entry (not another adapter's), fixture round-trip
  against the new stubs, leading-progress-line tolerance. Update
  `test_cfe_scripts_table_has_exactly_the_five_stubbed_fixture_entries` to seven entries (name
  reflects the new count).
- `tests/unit/test_recipe.py` -- `update()` composition tests per the I/O matrix: default (apply)
  argv, `--dry-run` argv, `--github` dispatch to the GitHub adapter, `--repo`/`--pre` forwarded only
  with `--github` and inert without it, `CfeUnresolvedError` propagation before any subprocess
  spawns, no `probe_import_floor` call (mirrors `test_diagnose_never_calls_ensure_import_floor`),
  one real-`fake_cfe_root` round-trip test per adapter.
- `tests/unit/test_cli.py` -- `recipe update` verb: help text, positional/flag parsing (`--dry-run`,
  `--github`, `--repo`, `--pre`), text/JSON rendering of the raw `CfeResult`, flag-forwarding to
  `recipe.update`, `CfeUnresolvedError` -> `EXIT_CFE_UNAVAILABLE`, real-fixture end-to-end via
  `main()`. Update the verb-metavar assertion string for the fifth registered verb (mirrors Story
  2.9's own update to that same assertion).

## Tasks & Acceptance

**Execution:**
- [x] `cfe.py` -- `update_recipe`/`update_recipe_from_github` adapters, two `_CFE_SCRIPTS` entries,
  two timeout constants -- FR-14.
- [x] `recipe.py` -- `update()` -- FR-14, AD-1.
- [x] `cli.py` -- register + dispatch `recipe update` (`--dry-run`, `--github`, `--repo`, `--pre`)
  -- FR-14.
- [x] `tests/fixtures/fake_cfe_root/.../recipe_updater.py`, `github_updater.py` -- new stubs.
- [x] `test_cfe.py`, `test_recipe.py`, `test_cli.py` -- coverage per the I/O matrix and Code Map --
  FR-14.

**Acceptance Criteria:**
- Given `mason recipe update`, when it runs (default or `--dry-run`), then the wrapped script
  computes its plan before any write occurs -- the default write is field-scoped (only
  `context.version`/`build.number`/`source.*.sha256`), and `--dry-run` never writes at all.
- Given `--dry-run`, when used with either source type (default PyPI or `--github`), then the
  invoked script's own `--dry-run` flag is forwarded and no file is modified.
- Given no `--dry-run` and an update is available, when it applies, then only the fields CFE's
  updater actually changed are written -- Mason adds no writes, defaults, or field policy of its
  own.
- Given `--github`, when set, then `update_recipe_from_github` is called instead of `update_recipe`;
  `--repo`/`--pre` are forwarded only in that mode and are inert otherwise.
- Given an unresolved CFE root, when `update` runs, then `CfeUnresolvedError` propagates before any
  subprocess spawns, mapping to `EXIT_CFE_UNAVAILABLE` like every other verb.

## Spec Change Log

## Review Triage Log

### 2026-08-12 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3 (high 0, medium 2, low 1)
- defer: 2 (high 0, medium 2, low 0)
- reject: 3 (high 0, medium 0, low 3)
- addressed_findings:
  - `[medium]` `[patch]` `recipe_path`'s help text claimed `recipe.yaml/meta.yaml` support, but
    both wrapped autotick scripts parse `context.version` via `ruamel.yaml`, which fails on a
    typical Jinja-templated v0 `meta.yaml` (`{% set %}`/unquoted `{{ }}` is not valid YAML on its
    own) -- verified by loading a real repo `meta.yaml` directly and reproducing `ScannerError`.
    Degrades gracefully to a `{"success": false, "error": ...}` JSON body (AD-4), never a crash,
    but the help text overpromised. Corrected in `cli.py` to name `recipe.yaml` only and explain
    why.
  - `[low]` `[patch]` The spec's own Design Notes cited "epics.md's Technical Decisions" for the
    default-write quote, but that sentence lives in `epic-2-context.md`'s "Technical Decisions"
    section, not `epics.md` (confirmed by grep) -- corrected the citation; the underlying claim
    was accurate, only its sourced file was wrong.
  - `[medium]` `[patch]` `--repo`/`--pre` given without `--github` were silently inert with zero
    signal to the user that their flag had no effect (matches the spec's deliberate "no error, no
    effect" contract, but nothing warned of it) -- added a `logging.warning` (stderr, same channel
    every other diagnostic uses) when either is given without `--github`; three new `test_cli.py`
    tests cover both trigger cases and the no-warning case.
- deferred (see `deferred-work.md` for the full entries):
  - `[medium]` `update`'s default-apply posture has two related residual risks worth a future
    decision: (a) a recipe living outside a git working tree (e.g. a future `recipe new --output`
    target -- Story 2.4 is not yet implemented, so unreachable via Mason today, but reachable via
    any hand-placed `recipe.yaml`) has no VCS safety net against a first, unconfirmed write; (b)
    the default (non-`--dry-run`) path's own stdout narration shows only the target version
    number, not the full field-level plan `--dry-run`'s JSON body carries, a materially thinner
    "displayed before written" guarantee than the dry-run path gives. Reviewed against this
    story's own Design Notes (four independent citations, including the architecture spine's own
    "defaults to it where the operation is irreversible" convention) and judged not to overturn a
    deliberate, evidenced decision inside this pass -- logged for a future dedicated look, not
    reversed here.
  - `[medium]` CFE's own `recipe_updater.py` (wrapped, not owned by Mason) hardcodes the bare
    command `"python"` for its internal `recipe_editor.py` subprocess call, unlike its sibling
    `github_updater.py`, which correctly uses `CONDA_PYTHON_EXE`/`sys.executable` -- a portability
    gap in the wrapped tool itself (verified by reading both scripts). AD-15 forbids a Mason-side
    fix; also flagged for the Rule-2 closing CFE retrospective.
- rejected (noise or already-intended-architecture, not re-litigated):
  - `[low]` `[reject]` "Already up to date" and "a newer pre-release exists but was skipped" share
    the identical top-level `{"success": true, "updated": false, ...}` shape in CFE's own JSON --
    Mason's non-interpretation of `json_body` is the intended architecture (AD-1/spec Never
    boundary), not a gap this story introduced.
  - `[low]` `[reject]` `test_cli.py`'s two real-fixture end-to-end tests only cover the success
    shape, unlike `submit`'s CLI tests, which also cover its `FAILED`/`NOT_ATTEMPTED` states -- but
    `submit` needs that coverage because it *reinterprets* `json_body` into different
    `ShipTargetResult` states; `update` returns the raw `CfeResult` unconditionally (spec Never
    boundary), so CLI-level rendering is content-blind by construction and a failure-shaped body
    would exercise no code path `test_cfe.py`'s per-shape adapter tests don't already prove.
  - `[low]` `[reject]` No test proves a `CfeTimeoutError` raised through the `--github` dispatch
    path names `update_recipe_from_github` specifically -- redundant given
    `test_invoke_captured_timeout_expired_raises_cfe_timeout_error_naming_script_and_timeout`'s
    existing generic proof (the translation is `_invoke_captured`'s alone) plus each adapter's own
    "invokes its own table entry" test; matches the identical, non-defective coverage pattern
    every other existing adapter already uses (none has a per-adapter timeout test either).

## Design Notes

**Why the default writes for real, unlike `submit`'s default-to-dry-run.** Four convergent,
independent signals all point the same direction, so this is a resolved reading, not a guess:
(0) the architecture spine's own Consistency Conventions table states the rule precisely: "Every
mutating verb accepts `--dry-run` and defaults to it **where the operation is irreversible**
(FR-19, NFR-9)" -- `update`'s local file write is git-reversible, unlike `submit`'s
externally-visible PR, so the spine's own qualifier excludes it from the default-dry-run set.
(1) `epic-2-context.md`'s own "Technical Decisions" section (itself compiled from `epics.md`)
describes `submit` and `update` with deliberately different
mechanisms in the same sentence pair -- "`submit` defaults to dry-run... `update` shows the
proposed diff before writing anything (default and `--dry-run`)". Listing "default" and
"`--dry-run`" as two *distinct* things sharing one property ("shows the diff before writing") only
makes sense if they are different modes -- if default *were* dry-run, the parenthetical would be
redundant. (2) The PRD's own adversarial review (`review-adversarial.md`, finding C-6) flags
NFR-9's blanket "every mutating operation defaults to dry-run" as contradicting FR-14's weaker
"`--dry-run` supported" (vs. FR-13's explicit "IS the default"), and its remedy is explicit:
*"Every irreversible or externally-visible operation... defaults to dry-run. Local file writes do
not."* `update` writes a local file, reversible by `git diff`/`git checkout`, unlike `submit`'s
externally-visible PR. (3) Reading `recipe_updater.py`/`github_updater.py` directly confirms both
already print their plan's progress narration ("Checking for updates...", "New version found:
X...") to stdout *before* ever invoking the write subprocess -- so "the proposed change is
displayed before anything is written" is a real, code-grounded ordering guarantee in the default
path too, captured on `CfeResult.stdout` exactly like every other verb's output.

**Why no import-floor gate, unlike `optimize`/`scan`.** `recipe.py`'s own established rule (module
docstring) is: gate only when the wrapped script does NOT already degrade a missing dependency to
JSON error data on its own. Reading both updater scripts confirms their top-level
`try/except (ImportError, ValueError, FileNotFoundError)` (plus a catch-all `except Exception`)
already wraps every import-floor-dependent call, returning `{"success": false, "error": ...}`
instead of a raw traceback -- the same "already handles it" case `diagnose()` established for
`failure_analyzer.py`, not the "would crash uncaught" case that justified `optimize()`/`scan()`'s
own scoped pre-flight probe.

**Why `--github` is Mason-only and never forwarded as CFE argv.** AD-1 forbids Mason from
inspecting recipe content to auto-select a source type (that would require parsing YAML the same
way the wrapped scripts already do, duplicating judgment Mason must not own). A user-supplied flag
is the only AD-1-compatible way to pick between two structurally different scripts; the two
existing CFE scripts have no equivalent selector flag themselves; `--repo`/`--pre` map directly to
`github_updater.py`'s own flags of the same name and are simply not part of `recipe_updater.py`'s
argument surface.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Summary:** Implementation and review (commit `153c2b621a`) landed in the prior session:
`recipe.py::update()` plus `cfe.py`'s `update_recipe`/`update_recipe_from_github` adapters, CLI
wiring, two new CFE fixture stubs, and test coverage across `test_cfe.py`/`test_cli.py`/
`test_recipe.py` -- all five Tasks & Acceptance items complete, mason suite 886 -> 889. That
session's own S-13.7 deterministic verify step (`python scripts/spec_surface_reconcile.py`) then
failed: the 9 files the commit touched are governed by `spec-pyforge-mason`, and the story landed
with no matching `.memlog.md` entry naming them, so the drift baseline gated. This resumed session's
sole job was that repair -- no code, test, or `<intent-contract>` change.

**Files changed (this repair pass):**
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md` --
  appended the S-2.10 landing entry (naming all 9 files the story commit touched) and the
  reconciliation-complete event entry, matching the S-2.7/S-2.8/S-2.9 precedent exactly.
- `scripts/.spec-surface-baseline.json` -- re-stamped via `spec_surface_check.py --write-baseline
  --spec pyforge-mason/spec-pyforge-mason`, scoped to only this one spec.
- Committed as `85ac823827` ("mason: reconcile spec-pyforge-mason drift for story 2-10").

**Review findings breakdown:** No new review pass run this session (see Design Notes below). The
prior session's Review Triage Log entry (2026-08-12) already stands: patch 3, defer 2, reject 3,
all addressed and included in commit `153c2b621a`.

**Follow-up review recommendation:** `false` -- this repair pass touched only spec-governance
bookkeeping (a `.memlog.md` entry and a drift-baseline JSON), not code or test behavior. Re-running
Blind Hunter/Edge Case Hunter against the full diff-since-baseline would re-review code already
reviewed and shipped in `153c2b621a`; judged unnecessary and wasteful rather than skipped
carelessly.

**Verification performed:**
- `python scripts/spec_surface_reconcile.py` -- now exits 0: "OK: every tracked file governed or
  allowlisted; no drift." (previously 9 gating `[drift]` findings, matching the feedback evidence at
  `.bmad-loop/runs/20260811-190427-dc18/feedback/2-10-mason-recipe-update-1.md`).
- `pixi run -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/` -- 889 passed
  (includes `tests/meta/`; unaffected by this repair, re-confirmed green after the fix).
- `git status` -- clean after commit.

**Residual risks:** None introduced by this pass. Two findings from the prior session's review
remain on the deferred-work backlog per that session's commit message (DW-2-10-1: default-apply's
residual VCS-safety-net and thinner-plan-display risk; DW-2-10-2: CFE's own `recipe_updater.py`
hardcoding a bare `"python"` subprocess call, flagged for the Rule-2 CFE retrospective) -- neither
is newly discovered here, and neither yet has a corresponding heading in
`deferred-work-ledger.md`/`deferred-work.md`; that gap pre-dates this session (also open for
S-2.7/S-2.8/S-2.9) and is out of this repair's scope.

