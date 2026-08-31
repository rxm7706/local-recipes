---
title: 'mason recipe submit'
type: 'feature'
created: '2026-08-12'
status: 'done'
baseline_revision: '12dc34cbf7bade6c149e34e12e2077f3337bb118'
review_loop_iteration: 0
followup_review_recommended: false
final_revision: '2b52b03f18870668135ab682f734c7cbaaf3b104'
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/_bmad-output/projects/pyforge-mason/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** FR-13's `recipe submit` is unimplemented. A user with a working recipe has no way to
open a staged-recipes PR through Mason; Epic 3's `conda-forge` ship target also has nothing to call
(AD-11).

**Approach:** Add `recipe.py::submit()`, composed on the already-existing `cfe.py::submit_pr`
adapter (Story 2.1), which wraps CFE's real two-phase `submit_pr.py` (`prepare_branch` then
`open_pr`, `--dry-run`/`--prepare-only` flags). Mason inverts the dry-run default: no `--yes` means
Mason always passes `--dry-run` through; `--yes` omits it. `--prepare-only` passes straight through
un-inverted. The out-of-tree recipe case (correct-course 2026-08-10) is solved by *always* deriving
`CFE_RECIPES_ROOT` from the recipe path's parent directory and setting it in the child's
environment -- harmless when the recipe is already in-tree (parent == the real `recipes/` root), so
no branching is needed. `submit()` returns the new `ShipTargetResult`/`ShipState` shapes (AD-9),
interpreting CFE's JSON body -- the one Mason-side reinterpretation AD-9 itself designs for, not a
recipe-knowledge violation of AD-1.

## Boundaries & Constraints

**Always:**
- `submit()` calls `cfe.ensure_cfe_root` first (mirrors `diagnose`/`build`) and raises
  `CfeUnresolvedError` before any subprocess spawns. No import-floor gate -- `submit_pr.py` is
  stdlib-only (confirmed by reading it), same exemption as `diagnose()` (Story 2.7), not 2.8's
  scoped-probe pattern.
- `recipe_path` (positional, required) is the recipe's OWN directory (matches `recipe new
  --output`'s existing contract, S-2.4): `recipe_dir = Path(recipe_path).expanduser().resolve()`;
  `recipe_dir.name` is the slug passed as `submit_pr.py`'s positional; `recipe_dir.parent` is always
  set as `CFE_RECIPES_ROOT` in the child's environment. This is the one narrow, disclosed exception
  to AD-1's "no Mason-side path interpretation" precedent (`diagnose`/`optimize`/`scan` pass
  `recipe_path` straight through unexamined) -- required because `submit_pr.py`'s own contract is a
  bare recipe NAME, not a path, unlike every other wrapped script. No existence check: an invalid
  path surfaces as CFE's own `{"success": false, "error": "Recipe not found: ..."}` (AD-4, data not
  raised).
- No confirming flag (`--yes` absent) -> Mason always appends `--dry-run` to the wrapped script's
  argv; nothing is pushed or opened (FR-13, PRD "`--dry-run` is the default"). `--yes` present ->
  `--dry-run` is omitted. `--prepare-only`, when given, is passed straight through unconditionally
  (composes with `--dry-run` exactly as the wrapped script's own argparse already allows) -- this is
  the "two-phase flow... separately addressable" requirement; no other new flag (no `--title`,
  `--body`, `--branch`, `--no-force` -- speculative surface CFE's own script supports but no FR/AC
  names, mirrors Story 2.7's `--first-only` rejection).
- `submit()` returns `ShipTargetResult` (models.py, new), not a raw `CfeResult` -- the one
  Mason-side reinterpretation of a CFE JSON body in this epic (AD-9's own designed shape, not
  recipe-knowledge). Mapping (from `json_body` and `confirm`, in this order):
  - `confirm=False` -> `state=NOT_ATTEMPTED`, `reference=None` (a dry-run's `fork_branch_url` is
    hypothetical, never rendered as if real).
  - `confirm=True` and `json_body.get("success")` falsy (or `json_body` unparseable, in which case
    `result.returncode == 0` stands in) -> `state=FAILED`, `reference=json_body.get("fork_branch_url")`
    (present when `open_pr` failed after a successful push; `None` otherwise).
  - `confirm=True`, success, `pr_url` present (full flow) -> `state=PENDING`,
    `reference=json_body["pr_url"]` -- **never** `TERMINAL` (PRD/AC pins this exactly: a PR being
    open is not a PR being merged; AD-10's interrogation-based idempotence is how a later command
    would ever learn `TERMINAL`, out of this story's scope).
  - `confirm=True`, success, no `pr_url` (`--prepare-only`) -> `state=PENDING`,
    `reference=json_body.get("fork_branch_url")` (AD-10: "if a target cannot be interrogated, the
    result is pending with the reason").
  - `message` is `json_body.get("message") or json_body.get("error")`, verbatim (AD-1: no
    re-authoring). `target` is the literal string `"conda-forge"` -- not tied to a `ShipTarget` enum,
    which is explicitly Story 3.3's scope (Never boundary below).
- `cfe.py::_invoke_captured` and `cfe.py::submit_pr` gain a new keyword-only `env: Mapping[str, str]
  | None = None` parameter, forwarded to `subprocess.run(..., env=dict(env) if env is not None else
  None)` -- the EXACT expression text `test_credential_isolation.py`'s
  `_SANCTIONED_PASS_THROUGH_ENV_EXPR` already names generically (not `run_streamed`-specific),
  mirroring `run_streamed`'s own established pass-through pattern exactly (Story 1.10/2.1
  precedent: replaces wholesale, never merges -- the caller builds the full dict). Every other
  existing caller (`validate_recipe`, `diagnose_failure`, `optimize_recipe`,
  `scan_for_vulnerabilities`) passes no `env`, so their behavior is unchanged (bare `None` ->
  inherit, identical to today).
- `recipe.py::submit()` builds `env = {**environ, "CFE_RECIPES_ROOT": str(recipe_dir.parent)}` --
  the *caller* builds inherited-plus-additions, matching `run_streamed`'s documented contract; no
  credential is read, filtered, or added (AD-14's actual rule: full pass-through of the given
  `environ` plus one non-credential key).
- `test_credential_isolation.py`'s Guard 3a allowlist (`_allowlisted_popen_call_ids` and its
  docstrings/fixtures) must be generalized to recognize a SECOND sanctioned site: the one
  `subprocess.run(...)` call inside `cfe.py::_invoke_captured`'s own body, structurally identified
  exactly like the existing `run_streamed`/`Popen` entry (exactly one call of its own kind in the
  function's body, `env=` unparsing to exactly `_SANCTIONED_PASS_THROUGH_ENV_EXPR`, fails closed on
  a second call). This is a deliberate, narrow, disclosed widening -- not a general env-override
  door -- authorized by the 2026-08-10 correct-course note's explicit "the submit adapter sets it in
  the child process environment" directive; the guard's own `_SANCTIONED_PASS_THROUGH_ENV_EXPR`
  constant name (not `_RUN_STREAMED_...`) anticipates a second site. Every fixture asserting "exactly
  one allowlist entry" scoped to `run_streamed` must gain an equivalent for `_invoke_captured`
  (revocation-on-second-call, rewritten-expression-rejection, "is still live") -- see Code Map.

**Block If:** None identified -- the two-phase argv shape, `CFE_RECIPES_ROOT` mechanism, and
`ShipTargetResult` state mapping are all resolved above from the real `submit_pr.py`/`_path_guard.py`
and the epics.md 2026-08-10 correct-course note.

**Never:**
- No `ShipTarget` enum, no `ShipReceipt` aggregate -- both are explicitly out of scope (`ShipTarget`
  vocabulary is Story 3.3; `ShipReceipt` aggregation is `package ship`, Epic 3). `target` is a plain
  string.
- No Mason-side credential check (e.g. probing `gh auth status` itself) -- `submit_pr.py`'s own
  `_gh_auth_user()` already does this; duplicating it would be exactly the reimplementation AD-1/AD-11
  forbid.
- No CFE-side change (AD-15 holds): `CFE_RECIPES_ROOT` already exists in `_path_guard.py` (read
  per-call, confirmed by reading the file) -- nothing under `.claude/skills/conda-forge-expert/**`
  or `.claude/scripts/conda-forge-expert/**` is touched.
- No widening of the AD-14 allowlist beyond the one new site inside `_invoke_captured` -- no other
  module, and no other call inside `cfe.py`, may pass a non-`None` `env=`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Dry run (default) | `recipe submit <path>`, no `--yes` | `--dry-run` forwarded; `ShipTargetResult(state=NOT_ATTEMPTED, reference=None)`; nothing pushed/opened | No error |
| Confirmed, full flow | `recipe submit <path> --yes`, CFE reports `pr_url` | `ShipTargetResult(state=PENDING, reference=pr_url)` | No error (nonzero returncode is data) |
| Confirmed, prepare-only | `recipe submit <path> --yes --prepare-only` | `--prepare-only` forwarded; `ShipTargetResult(state=PENDING, reference=fork_branch_url)`, no `pr_url` | No error |
| Confirmed, push succeeds but PR creation fails | CFE JSON `success=false` with `fork_branch_url` present | `ShipTargetResult(state=FAILED, reference=fork_branch_url)` | No error (data) |
| Out-of-tree recipe | `recipe_path` outside the real `<cfe-root>/recipes/` | `CFE_RECIPES_ROOT` set to `recipe_path`'s parent; CFE's `_path_guard` resolves the slug there; submission proceeds identically to an in-tree recipe | No error |
| CFE root unresolved | no root found | `CfeUnresolvedError` before any subprocess spawns | `EXIT_CFE_UNAVAILABLE` |
| Operation exceeds timeout | `--cfe-timeout` fires | `CfeTimeoutError` | `EXIT_FAILED`, stderr |

</intent-contract>

## Code Map

(paths relative to `src/shared/packages/pyforge-mason/`)

- `src/pyforge/mason/models.py` -- add `ShipState(StrEnum)` (`not_attempted`/`failed`/`pending`/
  `terminal`) and `@dataclass(frozen=True) ShipTargetResult(target: str, state: ShipState,
  reference: str | None, message: str | None)`.
- `src/pyforge/mason/cfe.py` -- add `env: Mapping[str, str] | None = None` to `_invoke_captured` and
  `submit_pr`, forwarded via `subprocess.run(..., env=dict(env) if env is not None else None)`
  (exact `_SANCTIONED_PASS_THROUGH_ENV_EXPR` text). No other adapter signature changes.
- `src/pyforge/mason/recipe.py` -- add `_CFE_RECIPES_ROOT_ENV_VAR = "CFE_RECIPES_ROOT"` (sanctioned
  duplication of `_path_guard.ROOT_ENV_VAR`, same pattern as `resolve.py`'s `_ENV_CFE_ROOT`); add
  `submit(recipe_path, *, confirm, prepare_only, cfe_root_arg, cfe_python_arg, cfe_timeout_arg,
  environ, start_directory) -> ShipTargetResult`; add a private
  `_ship_target_result_from_cfe_result(result, *, confirm) -> ShipTargetResult` implementing the
  Boundaries mapping.
- `src/pyforge/mason/cli.py` -- add `_RECIPE_SUBMIT_HELP`; register `submit` verb on
  `_noun_verbs["recipe"]` with `recipe_path` positional, `--yes` (`action="store_true"`) and
  `--prepare-only` (`action="store_true"`); dispatch in `main()` mirroring `diagnose`/`optimize`
  exactly (`_resolve_str`/`_resolve_optional_float` for the global knobs; no per-branch try/except,
  `CfeUnresolvedError`/`MasonError` caught globally); render via
  `dataclasses.asdict(result)`.
- `tests/meta/test_credential_isolation.py` -- generalize `_allowlisted_popen_call_ids` (rename to
  `_allowlisted_env_override_ids`) to union allowlisted ids from BOTH `run_streamed`'s own `Popen`
  call and `_invoke_captured`'s own `run` (i.e. `subprocess.run`) call, each independently checked by
  a shared per-function helper (exactly one call of its kind, sanctioned expression, fails closed on
  a second). Update the module docstring's "Exactly one allowlist entry" to two. Update
  `test_the_real_cfe_py_allowlist_entry_is_still_live` to assert both entries are live (or split into
  two per-site tests, matching this file's per-name-fixture convention). Add
  `_invoke_captured`-equivalents of: the revocation-on-second-call fixture, the
  rewritten-expression-rejection fixture. Existing `run_streamed`-only fixtures
  (`test_allowlist_is_scoped_to_a_file_literally_named_cfe_py`,
  `test_allowlist_does_not_cover_an_unrelated_env_override_elsewhere_in_cfe_py`,
  `test_allowlist_permits_an_async_run_streamed`) need no change -- they already construct synthetic
  single-function fixtures and the generalized helper degrades gracefully when one of the two named
  functions is absent.
- `tests/unit/test_cfe.py` -- `_invoke_captured`/`submit_pr` `env=` passthrough coverage (mocked
  `subprocess.run`, asserting the exact `env=` value reaches it); extend the AD-14 sentinel test
  (`test_jfrog_credential_sentinel_never_appears_in_cfe_results`) with one more case: calling
  `submit_pr` with an explicit `env={**os.environ, "CFE_RECIPES_ROOT": ...}` still carries the
  sentinel through (proving the new pass-through doesn't accidentally drop inherited credentials) and
  the sentinel still never appears in the returned `CfeResult`'s own fields.
- `tests/unit/test_recipe.py` -- `submit()` composition tests (mocked `cfe.submit_pr`): the five
  I/O-matrix branches' state mapping, `CfeUnresolvedError` propagation, `CFE_RECIPES_ROOT` computed
  correctly for an out-of-tree path (assert the `env=` argv reaching the mock), no import-floor probe
  called (mirrors `test_diagnose_never_calls_ensure_import_floor`). One real-`fake_cfe_root`
  round-trip test (`confirm=True, prepare_only=False`) -- the stub's static canned JSON already
  includes `pr_url`, matching the full-flow-success shape exactly, so it needs no fixture changes.
- `tests/unit/test_cli.py` -- `recipe submit` verb registration + dispatch: no `--yes` -> `--dry-run`
  reaches the (mocked) adapter call; `--yes` -> it does not; `--prepare-only` pass-through; text/JSON
  rendering of `ShipTargetResult` (including the `StrEnum` `state` field serializing as a plain
  string under `--format json`); `CfeUnresolvedError` -> `EXIT_CFE_UNAVAILABLE`; real-fixture
  end-to-end via `main()`. Also updates the pre-existing
  `test_recipe_diagnose_verb_metavar_reflects_the_registered_verb` assertion string (necessary
  consequence of a fourth verb landing on `_noun_verbs["recipe"]`, not a new test).

**Deviation (additive, not a Code Map departure):** `tests/unit/test_models.py` also gains
construction/immutability/`StrEnum`-serialization coverage for `ShipState`/`ShipTargetResult`,
mirroring that file's own existing `CfeResult` tests -- not named in the Code Map above, but the
same shape as every other dataclass already covered there; added because leaving a brand-new
`models.py` shape with zero direct unit coverage (only indirect, through `recipe.py`/`cli.py`
composition tests) would be a real coverage gap, not a simplification.

## Tasks & Acceptance

**Execution:**
- [x] `models.py` -- `ShipState`, `ShipTargetResult` -- FR-13.
- [x] `test_credential_isolation.py` -- generalize the Guard 3a allowlist to a second sanctioned site
  inside `_invoke_captured` (not yet exercised until the next task lands), update/add fixtures --
  AD-14. Lands first so the real-tree assertion is never red between this task and the next.
- [x] `cfe.py` -- `env=` parameter on `_invoke_captured`/`submit_pr`, sanctioned pass-through
  expression -- FR-13, AD-14.
- [x] `recipe.py` -- `_CFE_RECIPES_ROOT_ENV_VAR`, `submit()`, `_ship_target_result_from_cfe_result()`
  -- FR-13, AD-9, AD-11.
- [x] `cli.py` -- register + dispatch `recipe submit` (`--yes`, `--prepare-only`) -- FR-13.
- [x] `test_cfe.py`, `test_recipe.py`, `test_cli.py` -- coverage per the I/O matrix and Code Map --
  FR-13.

**Acceptance Criteria:**
- Given `mason recipe submit <path>` with no `--yes`, when it runs, then it is a dry run: `--dry-run`
  reaches CFE and nothing is pushed or opened.
- Given `--yes`, when submission proceeds, then CFE's two-phase flow (prepare branch, then open PR)
  is preserved and each phase is separately addressable via `--prepare-only`.
- Given a successful full submission, when the result is returned, then it is a `ShipTargetResult`
  with `state=PENDING` and `reference` carrying the PR identifier; `ShipState` is defined in
  `models.py` with exactly `not_attempted`/`failed`/`pending`/`terminal`.
- Given this story, when it completes, then staged-recipes submission has exactly one implementation
  (`recipe.py::submit`), which Epic 3's `conda-forge` ship target calls rather than reimplements
  (AD-11) -- verified by `test_adapter_sole_caller.py` continuing to pass unchanged (no new spawn
  site is introduced outside `cfe.py`).
- Given a recipe at a user-specified, out-of-tree path (S-2.4), when `recipe submit --yes` runs
  against it, then `CFE_RECIPES_ROOT` is set to the recipe's parent directory in the child's
  environment and submission succeeds identically to an in-tree recipe -- no new CLI flag, no CFE
  surface file touched.

## Review Triage Log

### 2026-08-12 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 8 (high 0, medium 3, low 5)
- defer: 1 (low 1)
- reject: 5
- addressed_findings:
  - `[medium]` `[patch]` `recipe submit`'s `recipe_path` help text didn't disambiguate its
    directory-only contract from `diagnose`/`optimize`/`scan`'s identical-looking, file-or-directory
    `recipe_path` -- reworded in `cli.py`.
  - `[medium]` `[patch]` `confirm=False, prepare_only=True` (dry-run + `--prepare-only` composing)
    was documented but never tested -- added `test_submit_dry_run_prepare_only_composes_both_flags`.
  - `[low]` `[patch]` `--prepare-only`'s help text implied a real push always happens -- reworded to
    note it is still a no-op dry run without `--yes`.
  - `[low]` `[patch]` The unparseable/non-dict `json_body` fallback branch was never directly tested
    -- added `test_submit_confirmed_unparseable_body_falls_back_to_returncode` (both `returncode`
    outcomes).
  - `[low]` `[patch]` `message = body.get("message") or body.get("error")` silently discarded a
    present-but-falsy (e.g. empty-string) `"message"` in favor of `"error"` -- changed to
    `body.get("message", body.get("error"))`, which only substitutes on an absent key; added
    `test_submit_preserves_an_explicit_empty_string_message_instead_of_falling_back_to_error`.
  - `[low]` `[patch]` No test proved `CFE_RECIPES_ROOT` actually overrides (not merges past) a
    pre-existing key of the same name already in the real inherited `environ` -- added
    `test_submit_overrides_a_pre_existing_cfe_recipes_root_in_environ`.
  - `[low]` `[patch]` A `json_body` dict that omits the `"success"` key entirely was never
    distinguished, in a test, from one setting it explicitly `false` -- added
    `test_submit_treats_a_missing_success_key_as_failure`.
  - `[medium]` `[patch]` `Path(recipe_path).expanduser().resolve()` was unguarded: a symlink loop or
    embedded NUL byte raises `OSError`/`ValueError` before any subprocess spawns, escaping to `cli.py`'s
    generic `except Exception` handler as a raw traceback instead of `submit()`'s own documented
    "anticipated failure is data" contract (which only actually covered the nonexistent-path case) --
    wrapped in `try`/`except (OSError, ValueError)`, returning a `FAILED` `ShipTargetResult`; added
    `test_submit_recovers_from_an_unresolvable_recipe_path_as_a_failed_result`.
  - `[low]` `[defer]` The unparseable-body `PENDING` fallback (`confirm=True`, unparseable body,
    `returncode == 0`) carries no `reference`/`message` even though AD-10's "pending with the reason"
    framing implies one should be attached -- logged as `DW-2-9-1` (low real-world likelihood: CFE's
    real `submit_pr.py` always prints its JSON body before exiting 0, so this fallback is defensive,
    not reachable in normal operation today).
  - `[n/a]` `[reject]` A confirmed submission reaching `FAILED` still exits `EXIT_OK` -- matches
    `diagnose`/`optimize`/`scan`'s established AD-4 precedent (non-zero/failure is DATA, interrogated
    via `--format json`'s `state` field, never signaled through the process exit code); not a
    deviation this story introduced.
  - `[n/a]` `[reject]` `_CFE_RECIPES_ROOT_ENV_VAR`'s sanctioned duplication of CFE's `_path_guard.
    ROOT_ENV_VAR` has no live cross-check test -- confirmed the same is true of every existing
    sanctioned duplication in this codebase (`_ENV_CFE_ROOT`/`_CFE_MARKER`); not a gap unique to this
    story.
  - `[n/a]` `[reject]` Guard 3a's generalized allowlist matches `_invoke_captured`'s sanctioned call
    by the common name `"run"` (vs. `run_streamed`'s rarer `"Popen"`) -- the guard's own documented
    philosophy is fail-CLOSED on ambiguity (a second same-named call revokes both), which is exactly
    the safety property intended, not a hole.
  - `[n/a]` `[reject]` Same-named `recipe_path` positional means a different contract across verbs --
    folded into the help-text patch above; not separately actionable.
  - `[n/a]` `[reject]` An empty `recipe_dir.name` (recipe_path resolving to `/`) sends an empty slug
    to CFE -- already handled gracefully end-to-end by CFE's own `validate_recipe_name`, which rejects
    it as a normal `FAILED` result (AD-1: no Mason-side reimplementation of that check).

## Design Notes

**Why `ShipState` is `enum.StrEnum`, not a plain `Enum`.** `render.write` -> `render_json` calls
`json.dumps(dataclasses.asdict(result), ...)` with no custom encoder (`render.py`'s own module
docstring: only a fixed five-key envelope, no schema-driven serialization). `dataclasses.asdict`
does not special-case `Enum` members, so a plain `Enum` field would reach `json.dumps` as a
non-serializable object and raise. `StrEnum` (stdlib since 3.12, this package's floor) members are
real `str` instances the JSON encoder handles natively, AND (unlike a bare `(str, Enum)` mixin
pre-3.11) `__str__`/`__format__` return the plain value too, so `render_text`'s `f"{data[key]}"`
line also renders `pending`, not `ShipState.PENDING`.

**Why `_invoke_captured` gains `env=`, not a new adapter function.** `submit_pr` (Story 2.1) already
exists and is already CAPTURE-mode by a prior, shipped decision -- this story does not revisit that
choice (Surgical Changes). Adding one optional, default-`None`, backward-compatible parameter to the
one shared CAPTURE-mode helper is the minimal change; every other adapter's call sites are
byte-identical afterward.

**Why the AD-14 allowlist extension is safe, not a hole.** The guard's structural check (exactly one
call of the sanctioned kind inside a NAMED function's body, EXACT expression match, re-verified by a
dedicated "is still live" test) is what makes a second entry safe rather than a door: an attacker (or
an accidental future edit) cannot smuggle an unrelated `env=` through either site without either (a)
breaking the exact-expression match (caught) or (b) adding a second call inside the same function
body (caught, fails closed). The second site does not widen WHAT can be set -- both sites still only
ever receive `dict(env) if env is not None else None`, and the actual `env` VALUE is built exactly
once, in `recipe.py::submit()`, from the real inherited `environ` plus one literal key.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**Summary.** Implementation and review (Tasks & Acceptance, Review Triage Log) had already
completed in the prior session and landed as commit `4256fb10fc` ("Story 2.9: mason recipe
submit"). bmad-loop's own deterministic verify gate (`python scripts/spec_surface_reconcile.py`)
then failed on that commit: it changed 9 files governed by the `pyforge-mason/spec-pyforge-mason`
Spec (`cfe.py`, `cli.py`, `models.py`, `recipe.py`, `test_credential_isolation.py`, `test_cfe.py`,
`test_cli.py`, `test_models.py`, `test_recipe.py`) without the governing Spec's `.memlog.md` moving
in the same commit -- exactly the "gated, not presumed" mode the governing Spec's own memlog
(entry preceding S-2.7) predicted would apply to mason's next story once the loop home's baseline
was back in sync.

**Repair performed (this pass), no intent-contract change:**
- Appended one entry to `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md`
  naming all 9 changed paths and summarizing the story, matching the S-2.7/S-2.8 precedent pattern
  in the same file.
- Re-stamped the drift baseline scoped to this one spec:
  `python scripts/spec_surface_check.py --write-baseline --spec pyforge-mason/spec-pyforge-mason`.
- Committed both files (`2b52b03f18`, "mason: reconcile spec-surface drift for story 2-9's own
  landing") on this story's own branch, mirroring the `herald: reconcile spec-surface drift for
  story 13-1's own landing` precedent (self-reconcile at the story's own landing, not deferred to a
  later cross-station sync commit on main).

**Verification performed (this pass):**
- `python scripts/spec_surface_reconcile.py` -- was `[drift]` x9 (rc=1), now `OK: every tracked
  file governed or allowlisted; no drift.` (rc=0).
- `pixi run -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/` -- 837 passed.
- `pixi run -e pyforge-mason pytest src/shared/packages/pyforge-mason/tests/meta/` -- 363 passed
  (subset of the above; all AD-1..AD-16 seam guards green).
- `git status` clean after the repair commit.

**No code or intent-contract change in this pass.** The prior session's implementation, the eight
patch-class review findings already addressed, and `DW-2-9-1` (deferred) stand unchanged.

**Follow-up review recommendation:** false -- this pass touched only spec-governance bookkeeping
(the governing Spec's `.memlog.md` and the tracked drift-baseline JSON), not implementation code;
nothing here needs adversarial re-review beyond the review pass already recorded in the Review
Triage Log above.

**Residual risk:** none identified beyond `DW-2-9-1`, already logged.

