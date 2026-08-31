---
title: 'CFE root resolution chain'
type: 'feature'
created: '2026-08-09'
status: 'done'
baseline_revision: 'c09088a6e6e3ae6ab8d9923dcb7df61a18052fa0'
final_revision: '72194e59ef'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-pyforge-mason-2026-07-25/ARCHITECTURE-SPINE.md'
warnings: []
---

<intent-contract>

## Intent

**Problem:** Nothing in Mason yet locates a conda-forge-expert installation. `cli.py` accepts and
resolves `--cfe-root`/`MASON_CFE_ROOT` as raw strings (Story 1.2) but nothing turns that input into
a CFE root path — every later CFE-dependent story (degradation, `doctor`, the CFE port) needs one
pure, independently-testable place that answers "where is CFE, and how did we find it."

**Approach:** Add `resolve.py` as that one place (AD-5): a pure function over `(explicit_arg,
environment_mapping, start_directory)` implementing FR-2's four-step chain — flag, env var, upward
filesystem walk for the CFE marker directory, not-found — returning an outcome that names which
step matched. No wiring into `cli.py` yet; that lands with Stories 1.7/1.8, which consume this
module without needing to re-resolve.

## Boundaries & Constraints

**Always:** `resolve.py` performs filesystem *reads* only — no writes, network, or process spawns
(AD-5, AD-2's subprocess guard already covers this file once it exists). `resolve_cfe_root(explicit,
environ, start_directory)` is a pure function: same inputs, same output, no global state. The chain
is first-match-wins: (1) `explicit` if non-whitespace, (2) `environ["MASON_CFE_ROOT"]` if
non-whitespace, (3) walk `start_directory` and each `.parent` upward, at each level testing whether
`<level>/.claude/scripts/conda-forge-expert` exists and `is_dir()`, (4) not-found. Steps 1 and 2
match on the presence of a non-whitespace value alone — they are not validated against the marker
directory; only step 3 checks for it. Whitespace-only values are treated as absent, mirroring
`cli.py`'s existing `_resolve_str` convention. The returned outcome always names which step matched,
via one of four string constants. The walk terminates cleanly (no exception) when it reaches the
filesystem root (`path.parent == path`) without a match.

**Block If:** none identified — FR-2, epics.md's Story 1.5 AC, and AD-5 fully specify this work.

**Never:** Wire `cli.py`'s `--cfe-root`/`MASON_CFE_ROOT` flags to call `resolve_cfe_root` — that is
Story 1.7 (degradation) and Story 1.8 (`doctor`)'s job. Implement interpreter selection or the CFE
import-floor probe (`--cfe-python`, `MASON_CFE_PYTHON`) — Story 1.6. Implement `doctor`'s real report
or `cfe.py` — Stories 1.8 and Epic 2. Validate that a flag- or env-supplied root actually contains
the CFE marker directory — only the walk step checks for it. Read `os.environ` directly inside
`resolve.py` — the environment mapping is always an explicit parameter, never a global read (this is
what keeps the function pure and every test hermetic with no monkeypatch/env-isolation needed).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Flag wins over env and walk | `explicit="/x"`, `environ={"MASON_CFE_ROOT": "/y"}` | `root=Path("/x")`, `step=STEP_FLAG` | none |
| Env wins over walk | `explicit=None`, `environ={"MASON_CFE_ROOT": "/y"}`, `start_directory` has the marker | `root=Path("/y")`, `step=STEP_ENVIRONMENT` | none |
| Whitespace-only flag/env falls through | `explicit="   "`, `environ={"MASON_CFE_ROOT": ""}`, `start_directory` has the marker | walk matches; `step=STEP_CWD_WALK` | none |
| Walk finds the marker N levels up | `start_directory=tmp/a/b` (no marker), `tmp/a` has the marker | `root=tmp/a`, `step=STEP_CWD_WALK` | none |
| Walk exhausts to filesystem root | isolated synthetic tree, marker absent at every ancestor | `root=None`, `step=STEP_NOT_FOUND` | no exception raised |
| Marker path exists but is a file, not a directory | `<level>/.claude/scripts/conda-forge-expert` is a regular file | that level does not match; walk continues upward | none |

</intent-contract>

## Code Map

(paths relative to `src/shared/packages/pyforge-mason/`)

- `src/pyforge/mason/resolve.py` (new) -- the CFE-root resolution chain (AD-5, FR-2): `ResolvedCfeRoot`,
  step-name constants, `resolve_cfe_root`.
- `tests/unit/test_resolve.py` (new) -- one test per chain step, precedence ordering, whitespace
  handling, walk termination, and the marker-must-be-a-directory edge case, all against synthetic
  `tmp_path` trees.

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/mason/resolve.py` -- create the module: `ResolvedCfeRoot` (`@dataclass(frozen=True)`,
  fields `root: Path | None`, `step: str`); constants `STEP_FLAG = "flag"`, `STEP_ENVIRONMENT =
  "environment"`, `STEP_CWD_WALK = "cwd-walk"`, `STEP_NOT_FOUND = "not-found"`; a private
  `_ENV_CFE_ROOT = "MASON_CFE_ROOT"` and `_CFE_MARKER = Path(".claude/scripts/conda-forge-expert")`;
  `resolve_cfe_root(explicit: str | None, environ: Mapping[str, str], start_directory: Path) ->
  ResolvedCfeRoot` implementing the four-step chain -- FR-2, AD-5.
- [x] `tests/unit/test_resolve.py` -- cover every I/O-matrix row plus: flag-only match, env-only
  match (no flag), a `start_directory` that itself has the marker (zero-level walk), and confirming
  `resolve_cfe_root` never raises for any input in these scenarios -- FR-2, AD-5.

**Acceptance Criteria:**
- Given `resolve.py`, when the CFE root is resolved, then the chain is `--cfe-root` ->
  `MASON_CFE_ROOT` -> upward walk from `start_directory` for a directory containing
  `.claude/scripts/conda-forge-expert/` -> not found, and first match wins.
- Given the resolution outcome, when it is returned, then it records which step matched, so callers
  (Stories 1.7, 1.8) need not re-resolve.
- Given AD-5, when the resolver runs, then it performs filesystem reads only -- no writes, network,
  or process spawns -- and each step is independently unit-testable against a synthetic tree.
- Given an upward walk that reaches the filesystem root without a match, when resolution completes,
  then a not-found outcome is returned, not an exception.

## Spec Change Log

## Review Triage Log

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1 (medium: 1, low: 0)
- defer: 0
- reject: 11
- addressed_findings:
  - `[medium]` `[patch]` Both Blind Hunter and Edge Case Hunter independently found that
    `resolve_cfe_root`'s walk step used `start_directory` as-given rather than resolving it
    to absolute first: `Path("a/b").parent.parent == Path(".") == Path(".").parent`, so a
    relative `start_directory` hits a lexical stopping point after one or two `.parent` hops
    and never reaches the real filesystem root -- silently contradicting the AC's "walk
    reaches the filesystem root, not an exception" guarantee (technically no exception is
    raised, but the walk covers far fewer ancestors than intended). Reproduced independently
    before patching. Fixed by resolving `start_directory` to absolute immediately before the
    walk loop; added `test_relative_start_directory_still_reaches_the_real_filesystem_root`
    (`monkeypatch.chdir` + a relative `Path("a/b")` input) proving it now reaches a marker
    that only a full walk to the real ancestor would find.

**Rejected findings (11 -- spec-mandated verbatim, speculative, stylistic nits, or
information-asymmetry artifacts of reviewing a diff without the rest of the codebase; dropped
silently per instructions, listed here only for this pass's audit trail):** flag/env steps
accepting any non-whitespace value without validating it against the marker directory (the
spec's `<intent-contract>` explicitly mandates this: "Validate that a flag- or env-supplied
root actually contains the CFE marker directory... only the walk step checks for it").
`step: str` not a `Literal`/`Enum` (stylistic; matches this codebase's existing
validated-string-not-enum precedent, e.g. `MasonError.identifier`). `_ENV_CFE_ROOT` duplicating
`cli.py`'s private literal with no cross-module equality test (the spec's own Design Notes
already identify and accept this exact duplication as intentional, non-drift-risk). Relative
explicit/env values having no anchoring/`.resolve()` semantics (out of scope -- no AC requires
it, and steps 1/2's deliberate no-validation design, per the point above, means the value is
passed through as given). Two smoke-test-style tests (`test_resolve_cfe_root_never_raises`,
`test_resolved_cfe_root_is_frozen`) adding limited incremental coverage beyond the
assertion-rich named tests / verifying stdlib `dataclass(frozen=True)` behavior rather than this
module's logic (harmless, matches this codebase's existing precedent of similar low-value-but-
harmless regression assertions). Symlinked or cyclic marker directories unspecified/untested
(speculative -- no realistic CFE installation creates a marker symlink loop; `is_dir()`
following symlinks is standard stdlib behavior). Returned `root` never canonicalized for the
flag/env branches (same family as the accepted "steps 1/2 aren't validated" design choice --
only the walk-termination correctness bug, now patched, was in scope). The "mirrors `cli.py`'s
`_resolve_str` convention" docstring claim being unverifiable from the diff alone (an
information-asymmetry artifact of the reviewer not having `cli.py` in context; the claim was
verified against the real file during spec planning). No drift protection tying `_CFE_MARKER`
to the real CFE layout (speculative future-proofing; renaming the CFE public-wrapper directory
is an out-of-scope hypothetical with no precedent). All flag/env tests using synthetic,
nonexistent paths rather than a real, valid marker directory (low value given steps 1/2 are
spec-mandated to skip marker validation entirely -- a valid-marker test would prove nothing
different from the existing synthetic-path tests).

## Design Notes

`resolve_cfe_root` takes the environment as an explicit `Mapping[str, str]` parameter rather than
reading `os.environ` internally (AD-5's pure-function signature). This is a deliberate purity choice,
not just style: spec-1-4's review log hit a real hermeticity bug from a test that forgot to scrub an
ambient `MASON_FORMAT` env var. Taking the mapping as a parameter makes that whole bug class
structurally impossible here -- every test passes a plain synthetic `dict`, with no
`monkeypatch.setenv`/`delenv` needed anywhere in `test_resolve.py`. `cli.py` (when Story 1.7/1.8
wires it) will call `resolve_cfe_root(getattr(ns, "cfe_root", None), os.environ, Path.cwd())`.

`"MASON_CFE_ROOT"` as a literal already exists in `cli.py`'s private `_ENV_CFE_ROOT` (used only for
`--cfe-root`'s help text). `resolve.py` cannot import that constant -- dependency direction is
inward-only (`cli` may import anything; nothing below it may import `cli.py` back) -- so `resolve.py`
owns its own copy for the actual env-var lookup. Two copies of one string literal, in exactly two
places, both changed together if the name ever changes: acceptable duplication under AD-1, not drift
risk.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

- **Implemented change:** added `resolve.py`, the pure CFE-root resolution chain (AD-5, FR-2):
  `ResolvedCfeRoot` (frozen dataclass), four `STEP_*` string constants, and
  `resolve_cfe_root(explicit, environ, start_directory)` implementing the first-match-wins chain
  (flag -> `MASON_CFE_ROOT` env -> upward filesystem walk for the CFE marker directory ->
  not-found). Not wired into `cli.py` -- deferred to Stories 1.7/1.8 per the spec's Never clause.
- **Files changed:**
  - `src/shared/packages/pyforge-mason/src/pyforge/mason/resolve.py` (new) -- the resolution
    chain module.
  - `src/shared/packages/pyforge-mason/tests/unit/test_resolve.py` (new) -- 17 tests: every
    I/O-matrix row, precedence ordering, whitespace handling, walk termination, the
    marker-must-be-a-directory edge case, and a review-driven regression test for relative
    `start_directory` handling.
- **Review findings breakdown:** 2 independent reviewers (Blind Hunter, Edge Case Hunter, no
  shared context) both surfaced the same real defect -- 1 patch applied (medium), 0 deferred,
  11 rejected (spec-mandated verbatim, speculative, or stylistic; see the Review Triage Log for
  the full audit trail).
- **Follow-up review recommendation:** false -- one localized, well-tested, correctness-only fix
  confined to the walk step's path handling; no API, behavior-contract, or security impact, and
  `resolve.py` has no live caller yet (not wired into `cli.py` this story), so the change carries
  zero current production exposure.
- **Verification:** `pixi run -e pyforge-mason pyforge-mason-test` -> 136 passed (full suite:
  119 pre-existing + 17 new, including the patch's regression test).
- **Residual risks:** none identified beyond the rejected findings' explicitly out-of-scope
  items (steps 1/2 do not validate a flag/env-supplied root against the marker directory, by
  spec design -- downstream stories, particularly Story 1.7's degradation handling and Epic 2's
  CFE port, will encounter a resolved-but-wrong root as a distinct failure mode at actual-use
  time, not at resolution time).
