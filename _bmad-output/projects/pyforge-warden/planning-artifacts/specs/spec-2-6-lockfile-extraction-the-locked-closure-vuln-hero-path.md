---
title: 'Story 2.6: Lockfile extraction — the locked-closure vuln hero path'
type: 'feature'
created: '2026-07-16'
status: 'done'
baseline_revision: 'fbd9c11b1ee55917303a9b5485b6039270a5cdcc'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md'
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md'
  - '{project-root}/_bmad-output/projects/pyforge-warden/implementation-artifacts/epic-2-context.md'
warnings: [oversized]
---

<intent-contract>

## Intent

**Problem:** No code path extracts `pixi.lock`/`conda-lock.yml` today — the tool sees only `pyproject.toml`'s `[project].dependencies` (Story 1.2's stub). Every conda/pixi maintainer's lockfile (the PRD's own "vuln hero path" — exact, transitive, `==`-pinned) is invisible; the report can only ever claim `direct-only` coverage, and a range/bare pyproject entry that a lockfile would otherwise resolve to an exact version stays `indeterminate` instead of `vuln_matchable`. This story was split out of 2.1 (2026-07-16, readiness Major-2) because no story AC owned it.

**Approach:** Add `extract/lockfiles.py` (`PixiLockExtractor` + `CondaLockExtractor`) parsing both formats via `yaml.safe_load` only into the existing `Component`/`ResolvedInventory` model — no new merge logic needed, since `inventory.merge_components`'s existing Gap-B fold already lets a lockfile's exact version subsume a looser `pyproject.toml` entry of the same identity for free. Wire the two new manifest kinds through `discovery.py` (additive stat-honesty check, not a rewrite), `routing.py` (per-manager section tokens), and `extract/__init__.py` (dispatch); surface `resolution_depth="locked-closure"` through a new opt-in `assemble_report(has_locked_closure=...)` parameter computed in `cli.py`. Validate against py-rattler's `LockFile` as a test-only oracle.

## Boundaries & Constraints

**Always:**
- `extract/lockfiles.py` parses via `yaml.safe_load` ONLY — no `yaml.load`, no execution, no network (NFR-S1/S2; the existing AST-denylist meta-test covers this file automatically, no registration needed).
- **pixi.lock `conda:` rows** carry no `name:`/`version:` fields — parse them from the entry's `conda:` URL/path value: `basename = value.rsplit("/", 1)[-1]` **FIRST**, then `re.match(r"^(.+)-([^-]+)-[^-]+\.(?:conda|tar\.bz2)$", basename)` — this basename-first order is the fix for **the URL-basename pitfall**: running the pattern against the un-stripped value lets a subdir path segment (e.g. `linux-64/`) bleed into the captured name. A non-matching basename is kept as `ExtractionMode.RAW_MALFORMED`, `WithholdReason.NO_VERSION` — never dropped.
- **pixi.lock `pypi:` rows** use the entry's own `name:`/`version:` fields directly (already PEP-503-canonical in practice) — `identity_source=IdentitySource.LOCK`. If both are absent, the row is `RAW_MALFORMED`/withheld (no second basename-guessing heuristic — out of scope, see Never).
- **conda-lock.yml rows** always carry explicit `name:`/`version:`/`manager:` fields (`conda`|`pip`) — no basename parsing needed for this format at all. `manager: pip` → `Ecosystem.PYPI`, `identity_source=LOCK`; `manager: conda` → `Ecosystem.CONDA`.
- Manager-aware routing goes through the `Router` seam (FR2), not a bypass: add 4 synthetic `(kind, section)` pairs to `DefaultRouter.route()` — `(PIXI_LOCK_KIND, "packages[kind=conda]")`→CONDA, `(PIXI_LOCK_KIND, "packages[kind=pypi]")`→PYPI, `(CONDA_LOCK_KIND, "package[manager=conda]")`→CONDA, `(CONDA_LOCK_KIND, "package[manager=pip]")`→PYPI. The section tokens are module constants in `extract/lockfiles.py`, imported into `routing.py` exactly as `PROJECT_DEPENDENCIES_SECTION` already is.
- A conda-ecosystem row with no PyPI identity calls `mapping.load_conda_pypi_map()` (today an empty `{}` stub pending Story 2.1) and, finding nothing, sets `pypi_identity=None`, `identity_source=IdentitySource.NONE`, `cve_match_level=CveMatchLevel.NONE`, `vuln_matchable=False`, `indeterminate_reason=WithholdReason.UNMAPPED_ECOSYSTEM` — never guessed, never dropped. Once 2.1 populates the map, these rows resolve richer with zero changes to this story's code.
- `vuln_matchable=True` is set ONLY when a concrete `pypi_identity` AND a concrete version both resolved (the frozen Gap-C predicate `Component.__post_init__` already enforces this) — a pip/pypi row with both fields present gets `cve_match_level=EXACT`.
- `discovery.py`'s `discover()` gains two more additive stat-honesty checks (new `PIXI_LOCK_KIND`/`CONDA_LOCK_KIND` constants, same file next to `PYPROJECT_KIND`) for `pixi.lock`/`conda-lock.yml` directly under `target`, appended to the returned tuple — the existing `pyproject.toml` check, its fail-closed semantics (dangling symlink, non-regular-file, permission-denied), and its existing tests are untouched. This is a narrow, additive extension (2 more filenames, same pattern) — NOT Story 1.9's full multi-manifest deterministic-selection policy (precedence across many candidate kinds, recursive search); factor the repeated stat logic into one private helper to avoid tripling it.
- `assemble_report` (`report.py`) gains `has_locked_closure: bool = False`; when `True`, `resolution_depth` becomes `ResolutionDepth.LOCKED_CLOSURE.value` for both axes (the single per-axis value the function already renders) instead of the current `DIRECT_ONLY if manifests_parsed>0 else None`. Default `False` preserves every existing caller/test byte-for-byte. `cli.py` computes it: track the KINDS of manifests that actually parsed (`parsed_kinds: set[str]`, not just the existing count) and pass `bool(parsed_kinds & {PIXI_LOCK_KIND, CONDA_LOCK_KIND})`.
- NFR-S5: cap total lockfile size and per-line byte length before `yaml.safe_load` (a lockfile exceeding either cap raises `UnparsableManifestError`, never hangs/OOMs); no compiled pattern in this module has nested unbounded quantifiers.
- `extract/lockfiles.py` is validated against **py-rattler's `LockFile`** (a test-only dependency — add `py-rattler` to `pixi.toml`'s `[feature.pyforge-warden.dependencies]`, the SAME env `pyforge-warden-test` already runs in; `pyproject.toml`'s runtime `dependencies` list is untouched, preserving the lean-dep/never-a-runtime-dependency policy). The repo's already-installed `py-rattler==0.22.0` (root `local-recipes` env) parses lockfile schema up to **v6** — write oracle-validated fixtures in v6 format; this repo's own v7 `pixi.lock` is a real-world example that predates the pin and is NOT usable as a fixture as-is.
- Scope pixi.lock parsing to the **flat top-level `packages:` list** (every package the file ever resolved, across all environments/platforms) — no per-environment/per-platform selection. This mirrors this repo's own sibling parser (`.claude/skills/conda-forge-expert/scripts/scan_project.py::parse_pixi_lock`), avoids introducing host-platform-dependent behavior (a determinism concern), and errs toward more coverage, not less.

**Block If:** none identified — the codebase/planning research already settled every open mechanism question (routing-seam design, discovery scope boundary, resolution_depth wiring, py-rattler schema-version ceiling).

**Never:** Story 1.9's full multi-manifest deterministic-selection policy (recursive search, precedence across many candidate kinds — `discovery.py`'s two new checks are narrowly additive, not that); a second basename-guessing heuristic for a pypi: row missing both `name:`/`version:` (kept `RAW_MALFORMED` instead); per-environment/per-platform pixi.lock selection; populating `mapping.py`'s real conda→pypi map (Story 2.1's job — this story only calls the existing stub); recipe.yaml/meta.yaml/environment.yml/pixi.toml (loose-manifest) extraction (Stories 2.2/2.3); the differential-oracle at corpus scale (Epic 5); touching `verdict.py`/`interfaces.DefaultPolicy` (untouched — new withheld/matchable components ride the existing false-green backstop).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| pixi.lock conda row, ordinary URL | `conda: https://…/linux-64/numpy-1.26.0-py311h_0.conda` | name=`numpy`, version=`1.26.0`, ecosystem=conda, unmapped→`indeterminate:unmapped-ecosystem` | No error |
| **URL-basename pitfall (regression)** | `conda: https://conda.anaconda.org/conda-forge/linux-64/_openmp_mutex-4.5-20_gnu.tar.bz2` | basename extracted FIRST → name=`_openmp_mutex`, version=`4.5` exactly — never `linux` or `linux-64/_openmp_mutex` | Must pass; this is the shipped-parser regression fixture |
| pixi.lock pypi row, explicit name/version | `pypi: <url>` + `name: boring-semantic-layer` + `version: 0.3.15` | ecosystem=pypi, `identity_source=lock`, `pypi_identity=(boring-semantic-layer, 0.3.15)`, `vuln_matchable=true`, `cve_match_level=exact` | No error |
| pixi.lock conda row, unparseable basename | `conda: <path with no name-version-build shape>` | Kept as `RAW_MALFORMED`, withheld `no-version` | Never dropped, never crash |
| conda-lock.yml `manager: conda` row | `{name: numpy, version: 1.26.0, manager: conda}` | ecosystem=conda, exact version, unmapped→`indeterminate:unmapped-ecosystem` | No error |
| conda-lock.yml `manager: pip` row | `{name: requests, version: 2.31.0, manager: pip}` | ecosystem=pypi, `identity_source=lock`, `vuln_matchable=true` | No error |
| Oversized lockfile | file/line exceeds the NFR-S5 cap | `UnparsableManifestError` (typed `unparsable-manifest`) | Report still emitted, never a hang |
| Same identity in `pyproject.toml` (range) + a lockfile (exact) | `numpy>=1` in pyproject + `numpy==1.26.0` in the lockfile | `merge_components`'s existing bare-fold picks up the exact version for free — no new code | No error |
| Any lockfile parses successfully | pixi.lock or conda-lock.yml present, well-formed | `AxisCoverage.resolution_depth == "locked-closure"` on BOTH axes | No error |
| No lockfile, pyproject.toml only | — | `resolution_depth` stays `"direct-only"` — unchanged 1.2 behavior | No error |
| Empty `packages:`/`package:` list | valid YAML, zero entries | Parses successfully, 0 components contributed, `manifests_parsed` still increments (FR6: empty ≠ unresolved) | No error |

</intent-contract>

## Code Map

- `src/pyforge/warden/discovery.py` -- MODIFY: add `PIXI_LOCK_KIND = "pixi.lock"` / `CONDA_LOCK_KIND = "conda-lock.yml"`; factor the stat-honesty check into a helper, call it 3x (pyproject + the 2 new kinds), append to the returned tuple.
- `src/pyforge/warden/extract/lockfiles.py` -- NEW: `PixiLockExtractor`, `CondaLockExtractor` (both implement `Extractor`); NFR-S5 size/line caps; the basename-first conda-URL regex; the 4 section-token constants.
- `src/pyforge/warden/extract/__init__.py` -- MODIFY: `extractor_for` dispatches `PIXI_LOCK_KIND`→`PixiLockExtractor(router)`, `CONDA_LOCK_KIND`→`CondaLockExtractor(router)`.
- `src/pyforge/warden/routing.py` -- MODIFY: 4 new `(kind, section)`→`Ecosystem` branches in `DefaultRouter.route`, importing the section tokens from `extract.lockfiles`.
- `src/pyforge/warden/report.py` -- MODIFY: `assemble_report` gains `has_locked_closure: bool = False`, drives `resolution_depth`.
- `src/pyforge/warden/cli.py` -- MODIFY: track `parsed_kinds: set[str]` in `_run_scan`'s extraction loop; compute + pass `has_locked_closure`.
- `pixi.toml` -- MODIFY: add `py-rattler = ">=0.22.0"` to `[feature.pyforge-warden.dependencies]` (test-only; `pyproject.toml` runtime deps untouched); re-resolve `pixi.lock` for that env.
- `tests/fixtures/projects/pixi_lock_basic/pixi.lock` -- NEW: mixed conda+pypi rows, v6 schema (py-rattler-compatible).
- `tests/fixtures/projects/pixi_lock_url_basename_pitfall/pixi.lock` -- NEW: the `_openmp_mutex`-style regression case.
- `tests/fixtures/projects/conda_lock_basic/conda-lock.yml` -- NEW: mixed `manager: conda`/`manager: pip` rows.
- `tests/unit/test_discovery_extract_cli.py` -- MODIFY: add discovery coverage for the 2 new kinds (present/absent/dangling-symlink/non-regular-file), mirroring existing `pyproject.toml` cases.
- `tests/unit/test_lockfiles_extractor.py` -- NEW: both extractors against every I/O-matrix row above, direct (no CLI).
- `tests/conformance/test_lockfile_oracle.py` -- NEW: `PixiLockExtractor` vs. py-rattler's `LockFile` over `pixi_lock_basic` — hard-fail if `py-rattler` is absent (matches the 1.4/1.5 provisioned-engine convention, never skip).

## Tasks & Acceptance

**Execution:**
- [x] `discovery.py` -- add the 2 new kind constants + additive discovery checks -- narrow, non-1.9 extension needed before anything downstream can see these files.
- [x] `extract/lockfiles.py` -- `PixiLockExtractor`/`CondaLockExtractor`, NFR-S5 bounds, basename-first regex -- the story's core deliverable.
- [x] `extract/__init__.py` + `routing.py` -- dispatch + manager-aware routing wiring -- required for the CLI to actually invoke the new extractors.
- [x] `report.py` + `cli.py` -- `has_locked_closure` threading -- required to make the AC's "coverage marked locked-closure" true in the emitted report.
- [x] `pixi.toml` -- add `py-rattler` test-only dep, re-resolve -- required by the AC's test-side oracle. (`pixi.toml` edited; the re-resolve itself could NOT run in this sandbox — see Dev Notes below.)
- [x] fixtures (3 new dirs) + `test_lockfiles_extractor.py` + `test_lockfile_oracle.py` + `test_discovery_extract_cli.py` additions -- cover the I/O matrix + the oracle AC.

**Acceptance Criteria** *(from `epics.md`, preserved verbatim):*

**Given** a `pixi.lock` or `conda-lock.yml` (the **vuln hero path**), **When** extracted via `extract/lockfiles.py`, **Then** the **locked closure** lands in the inventory with exact `==` versions, manager-aware routing (conda vs pip rows → the correct ecosystem), `vuln_matchable=true` where `pypi_identity` resolves, and coverage marked `locked-closure`; fixtures include the **URL-basename pitfall** (a subdir segment must never be mis-captured as a package name — a documented shipped-parser regression). **And** `extract/lockfiles.py` is validated against **py-rattler's `LockFile`** parse as a *test-side* oracle (never a runtime dependency).

**Given** the standing cross-cutting gates, **When** this story lands, **Then** C0/C0c and the NFR-S* suite hold on the new `extract/lockfiles.py` surface (AST-denylist; no execution of untrusted input; line/size bounds per NFR-S5).

## Design Notes

**Why no new merge/"prefer lockfile" code is needed:** `inventory.merge_components`'s existing `_fold_bare` already folds a bare/range `(name, None)` record into the sole matching concrete-version record of the same `(ecosystem, name)` — a `pyproject.toml` range entry and a lockfile's exact pin of the same package fold automatically, with the fold's own conservative-merge rules (never upgrades confidence) already correct. Architecture's "prefer lockfile input" is a byproduct of Gap-B, not new logic.

**Why `resolution_depth` needs a caller-supplied flag, not inference inside `report.py`:** `report.py` explicitly has no lockfile-kind vocabulary (and shouldn't gain one — that's `discovery.py`'s domain). `assemble_report` already receives `inventory.resolved_scan_set`, but that includes manifests that FAILED to parse; only `cli.py`'s extraction loop knows which kinds actually succeeded, so it computes the boolean and passes it — the same caller-derives-domain-knowledge pattern `vuln_data` already uses.

**Router bypass considered and rejected:** a lockfile's rows are ecosystem-mixed per-file, unlike `pyproject.toml`'s one-shot `[project].dependencies`. Rather than have the extractor assign `Ecosystem` directly (bypassing `Router` — precedent-breaking, since every existing extractor calls it), this story adds 4 synthetic `(kind, section)` pairs so the FR2 routing seam stays the single classification authority.

**py-rattler schema ceiling:** the currently-pinned `py-rattler==0.22.0` (already installed in this repo's root env, proven against the same conda-forge channel) parses pixi.lock up to schema v6; this repo's own `pixi.lock` is v7 and is NOT a valid oracle fixture. Author the new fixtures by hand in v6 shape; if `py-rattler` later needs a bump for v7 support, that's a follow-up, not this story's scope.

**Dev Note (2026-07-16) — `pixi install`/`update -e pyforge-warden` could not regenerate `pixi.lock` in this sandboxed worktree:** every pixi subcommand that mutates the lockfile (`install`, `update`, and `run` without `--frozen`) re-validates ALL environments in the single shared `pixi.lock`, not just `pyforge-warden` — pixi has no per-environment lock file. That full-workspace validation fails on the UNRELATED `bmad-ui` environment: its `file:///…/build_artifacts/linux64/` channel is a gitignored, build-time-only local conda channel that does not exist in a fresh git worktree checkout (confirmed via `git check-ignore`/`.gitignore`), so `bmad-ui` is already "out of date" independent of this story's `py-rattler` addition (`pixi_core::lock_file::outdated: environment 'bmad-ui' is out of date because the channels in the lock file do not match the environments channels`). `pixi.toml`'s `[feature.pyforge-warden.dependencies]` edit is correct and complete; only the lockfile re-resolve is blocked, by an environment this story never touches. Verified instead by running the full `pyforge-warden` suite (PYTHONPATH-injected) under the root `local-recipes` pixi env, which already has `py-rattler==0.22.0` (and every other pyforge-warden runtime dep) installed via its own dependency on it: all 616 tests pass, including both new oracle tests — see Verification below for the exact commands and counts.

**Dev Note (2026-07-16) — `.gitignore`'s blanket `pixi.lock` rule silently ignored the new hand-authored fixture files:** `.gitignore` line 684 (`pixi.lock`, unanchored) matches any file named `pixi.lock` anywhere in the tree — it never blocked the repo-root `pixi.lock` only because that file was already tracked before the rule existed. The two new v6 fixture files under `tests/fixtures/projects/pixi_lock_basic/` and `.../pixi_lock_url_basename_pitfall/` are BRAND NEW, so the blanket rule would have silently kept them untracked. Fixed with a narrow negation (`!src/shared/packages/pyforge-warden/tests/fixtures/**/pixi.lock`) right below the existing rule — confirmed via `git check-ignore -v` that both fixtures are no longer ignored, with no change to the ignore behavior for any real per-env `pixi.lock`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` -- expected: all prior 1.x/2.x suites unchanged + the 3 new test files green; sole-ownership/no-execution/socket-deny meta-guards stay green automatically (no wiring needed for new files under `extract/` or `tests/`).
- `pixi install -e pyforge-warden` (after the `pixi.toml` edit) -- expected: resolves cleanly (py-rattler is already proven resolvable from conda-forge via the root `local-recipes` env's own dependency on it).
- Manual: `git diff --stat` shows zero changes to `pyproject.toml`'s runtime `dependencies` list, `verdict.py`, or `interfaces.py`.
