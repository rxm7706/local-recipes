---
title: 'PROJECTS.md index and artifact-symlink derivation'
type: 'feature'
created: '2026-08-21'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
difficulty: ''
baseline_revision: '5f23cd638abf626cf13e8a0e08c4919592807f36'
final_revision: 'ea59db5c1377c99fd2871d1057cee190240e1764'
---

<intent-contract>

## Intent

**Problem:** `_bmad-output/PROJECTS.md`'s Projects table is 100% hand-maintained prose (no
region marker exists in it today), so it silently goes stale as projects are added/removed —
the exact class of drift that produced the ten-hour marker/symlink desync incident CLAUDE.md
documents. Separately, nothing in this codebase currently creates or verifies the two BMAD
artifact symlinks (`_bmad-output/planning-artifacts`, `_bmad-output/implementation-artifacts`),
and `seed/fs.py`'s write guard has no symlink-writing primitive at all (its own docstring states
plainly: "No real V1 target artifact is itself expected to be a symlink, so this module does not
special-case it" — true until this story).

**Approach:** Add `seed/derive/projects_index.py`: (1) derive the Projects table from the set of
`_bmad-output/projects/*/.bmad-config.toml` files and splice it into `PROJECTS.md` as a managed
region (the manifest's existing `projects-index` entry is reclassified from `generated-derived`
to `hybrid-managed-region` in `templates/manifest.yaml` to match — the table is a fragment inside
a hand-authored file, not a whole file); (2) add a `symlink()` primitive to `seed/fs.py`
(never-write-guarded, matching `write`/`replace_span`/`remove`'s existing shape) and use it to
ensure the two symlinks exist and point at the active project; (3) compute a `SymlinkDesync`
finding when the marker and the two symlinks disagree, naming every value involved.

## Boundaries & Constraints

**Always:**
- Every filesystem write (including the new symlink creation) goes through `seed/fs.py` — no
  `os.symlink`/`Path.symlink_to` call anywhere else under `seed/`. Extend `fs.py` with a new
  guarded `symlink(link_path, target, *, repo_root, never_write)` function following the exact
  shape/docstring density of `write`/`replace_span`/`remove`.
- `derive never writes into projects/*/planning-artifacts/**`: this is already covered by the
  manifest's existing `never_write` pattern `**/planning-artifacts/**` (confirmed matching
  `_bmad-output/projects/<slug>/planning-artifacts/**`) — no new pattern needed, but add a test
  proving it (a deliberately malicious call attempting to derive INTO that path must raise
  `NeverWriteViolation`).
- `PROJECTS.md`'s hand-written prose (the config-layering table, "Adding a new project" section,
  everything outside the Projects table) is byte-identical before and after a derive run — only
  the table region changes.
- The active project is identified the same way `_bmad/scripts/resolve_config.py` already
  resolves it: `--project` flag (if this module exposes one) → `BMAD_ACTIVE_PROJECT` env var →
  `_bmad/custom/.active-project` marker file. Do not invent a second resolution order.
- A symlink pointing at a different project than the OTHER symlink, or than the marker, is a HARD
  finding naming all disagreeing values (marker's project, each symlink's actual target) — never
  silently "fixed" by picking one as authoritative.
- **All tests operate on synthetic fixture repos under `tmp_path` — never on this actual
  worktree's real `_bmad-output/{planning,implementation}-artifacts` paths or `_bmad/custom/
  .active-project` marker.** This repo currently has other agents doing concurrent work in
  sibling git worktrees; even though each worktree's untracked/gitignored files (including these
  symlinks and the marker) are filesystem-independent per worktree, house convention for every
  `test_seed_*.py` file already uses `tmp_path`-rooted synthetic repos exclusively, and this story
  follows it with no exception.

**Block If:** none identified — the manifest reclassification, the new `fs.symlink` primitive,
and the active-project resolution order are all determined by existing, inspectable code and the
epics AC; no decision here requires a human call.

**Never:**
- Never resolve the active project by re-implementing `_bmad/scripts/resolve_config.py`'s logic
  independently — import/subprocess/replicate its exact precedence, do not diverge.
- Never auto-repair a detected desync (no silent re-pointing of a symlink to "fix" it) — the HARD
  finding is the only output; repair (if any) is a human or a future story's job.
- Never widen `NeverWrite`'s exempt set or bypass the guard for these two symlink paths.
- Never touch `seed/migrate/` or add a new CLI verb.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| N projects present | 3 `.bmad-config.toml` files with distinct slug/status/description | Projects table region has exactly 3 rows, correct columns | No error expected |
| Hand-written prose preserved | `PROJECTS.md` with prose outside the table | Prose is byte-identical after derive; only the table region changed | No error expected |
| Symlinks absent | Neither symlink exists, marker names project X | Both symlinks are created pointing at project X's `planning-artifacts`/`implementation-artifacts` | No error expected |
| Symlinks already correct | Both symlinks already point at project X, marker names X | No-op (idempotent — a second run makes zero changes) | No error expected |
| Symlink desync | `planning-artifacts` symlink points at project Y, `implementation-artifacts` points at project X, marker names X | HARD finding naming marker=X, planning-artifacts-target=Y, implementation-artifacts-target=X | Finding raised/reported, not silently resolved |
| Derive targets the never-write set | A deliberately malicious call attempts to write inside `projects/<slug>/planning-artifacts/**` | Raises `NeverWriteViolation` naming the offending path | Hard error, no partial write |
| Zero `.bmad-config.toml` files | No projects present | Projects table region has zero data rows (header only), no crash | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/derive/projects_index.py` -- NEW: derives the Projects table body, active-project resolution (with validation), the two symlink-ensure operations, and desync detection.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/fs.py` -- CHANGED: add a new `symlink()` guarded primitive alongside `write`/`replace_span`/`remove`, and give the shared `_guard` helper a `resolve_leaf` parameter (default `True`, unchanged behavior for the three existing callers) so `symlink()` can pass `resolve_leaf=False` and check the link's own path instead of following it. `symlink()` itself must: `mkdir(parents=True, exist_ok=True)` on `link_path.parent` before writing (a brand-new `_bmad-output/` has no parent directory yet); perform an ATOMIC replace when a symlink already exists at `link_path` and needs re-pointing (temp-symlink-then-`os.replace()`, mirroring `scripts/bmad-switch::repoint_links`'s own precedent exactly -- read that function before implementing this one -- never a bare `unlink()` then `symlink_to()`, which leaves a real absence window this repo's own CLAUDE.md documents as a live incident hazard for this exact symlink pair); raise a named error (not a bare `FileExistsError`) if a REGULAR file or directory already occupies `link_path`. `symlink()`'s never-write guard checks `link_path` only, deliberately NOT `target` -- document this explicitly in the function's docstring: this story's own real callers pass a `target` that IS a never-write path by design (a symlink whose whole purpose is to point AT the protected planning-artifacts directory), so guarding `target` would make the feature impossible to build; two independent review passes flagged this as looking like a gap, so the docstring must make the reasoning impossible to miss on a future read.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/templates/manifest.yaml` -- CHANGED: reclassify `projects-index` from `generated-derived` to `hybrid-managed-region` with one region, `name: projects-table`, `anchor: ["## Projects"]` (the real, current heading immediately above the table in `_bmad-output/PROJECTS.md`).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/adopt.py` -- CHANGED (added this loopback -- was wrongly marked "NOT modified" in the prior pass; this omission is this amendment's whole root cause, see Spec Change Log below): `_default_commit`'s `HYBRID_MANAGED_REGION` branch must special-case the `projects-table` region the same way Story 11.1 special-cased its three whole-file ids -- a data-driven check (e.g. `if region_name == "projects-table":`) that calls `derive_projects_index.derive_projects_table(...)` for this region's body INSTEAD OF `_region_body_from_template(template_path, region_name)`, mirroring Story 11.1's `entry.id in derive_adapters.ADAPTER_COMPOSITION` bypass pattern exactly. Every OTHER hybrid region (`tiers`, `portability-contract`, `dream-first-workflow`, `bmad-multiproject`) is untouched and still reads its static fragment via `_region_body_from_template` as before -- only `projects-table` is repo-computed rather than packaged-static, because it is the one region whose content depends on the ADOPTING repo's own state, not on shipped prose.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/errors.py` -- inspect only; do not modify unless a suitable shape already exists (unlikely, per the prior pass's finding -- `SymlinkDesync` stays a local dataclass in `derive/projects_index.py`, not a `detect.findings.Finding`, because `derive` sits below `detect` in the architecture's layering and importing upward would violate it -- this reasoning from the prior pass was sound and survives this amendment unchanged, see KEEP below).
- `_bmad-output/PROJECTS.md` (this actual repo's real file) -- NOT modified, NOT read by any test, and `marshal seed adopt --apply` is NOT run against this real repo as part of this story. This is a narrower, more precise version of the prior pass's boundary: the CODE PATH that would derive `PROJECTS.md`'s table for real must now be genuinely wired and correct (fixed above), but actually invoking that code path against THIS repo's own real file -- which carries hand-curated historical/dissolved-project rows with no `.bmad-config.toml` backing them, a real content-reconciliation decision -- stays a future, separate adoption event. Every test in this story uses a synthetic fixture `PROJECTS.md` with no such historical rows.
- **NO static `templates/files/projects-table.md.j2` file this time.** The prior pass's version of this file was the actual defect (a wrong, never-updated placeholder silently shipping as real output through the pre-existing, unmodified `_region_body_from_template` mechanism). Since `verbs/adopt.py` now bypasses `_region_body_from_template` for this one region entirely (see above), no static body file is needed OR wanted for `projects-table` -- follow Story 11.1's own precedent instead: exempt this one region from `test_seed_templates_manifest.py`'s "every hybrid region needs a matching body file" conformance check, the same way Story 11.1 exempted its three wrapper-template filenames from the sibling "every `.j2` file is claimed" check. Do not re-introduce a static fragment for this region under any filename.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_derive_projects_index.py` -- NEW: unit-tests the I/O matrix using synthetic `tmp_path` fixtures exclusively, PLUS explicit coverage for every validation/robustness gap named in the Tasks below.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_fs.py` -- CHANGED: coverage for the new `symlink()` primitive as described above.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_verbs_adopt.py` -- CHANGED: add ONE real-git integration test proving `projects-table` region content comes from `derive_projects_table` (a synthetic repo with 2-3 fixture `.bmad-config.toml` files under `_bmad-output/projects/`) via a real `run_adopt` call -- mirroring Story 11.1's own `test_run_adopt_writes_a_derive_composed_whole_file_and_a_managed_region_in_the_same_run` end-to-end-proof pattern. This is the test that would have caught the prior pass's defect; it did not exist before.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_templates_manifest.py` -- CHANGED: update `EXPECTED_CLASS_COUNTS`/region-anchor fixtures for the reclassified manifest entry (mechanical, same as the prior pass), AND add the `projects-table` region-body exemption described above.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_plan_build.py` -- CHANGED: update its own real-manifest hybrid-region-count fixture (mechanical, same as the prior pass).

## Tasks & Acceptance

**Execution:**
- [x] `seed/fs.py` -- add `symlink()` per the Code Map's full description above (atomic replace, `mkdir(parents=True)`, named error on a non-symlink collision, `resolve_leaf=False` guard on `link_path` only, docstring explaining why `target` is deliberately unguarded)
- [x] `seed/templates/manifest.yaml` -- reclassify `projects-index` to `hybrid-managed-region` with a `projects-table` region anchored on real, current `PROJECTS.md` content
- [x] `seed/derive/projects_index.py` -- implement:
  - (a) `derive_projects_table(projects_dir: Path) -> str` -- reads every `<projects_dir>/*/.bmad-config.toml`, sorts deterministically by slug, renders the markdown table body. Escape **every** cell of **every** column (slug, status, AND description -- not description alone) for both `|` and any newline/carriage-return character (replace with a space or escaped form -- pick one, apply uniformly, and name the choice in a docstring) before rendering, so no malformed TOML value can corrupt the table's row/column structure.
  - (b) `resolve_active_project(...) -> str` -- matches `resolve_config.py`'s precedence (`--project` param if this function exposes one → `BMAD_ACTIVE_PROJECT` env var → `_bmad/custom/.active-project` marker file). Strip whitespace from EVERY source consistently (not just the marker) and treat a whitespace-only or empty value as absent (fall through to the next source, exactly like a genuinely-missing one). After resolution, validate the final value against a slug charset matching real project slugs in this repo (lowercase alnum + hyphen, e.g. `^[a-z][a-z0-9-]*$`) -- an empty, absolute-path-shaped, `..`-containing, or otherwise invalid resolved value raises a clear, named error (never a bare `TypeError`/silently-broken symlink target) naming the offending value and its source.
  - (c) `ensure_symlinks(repo_root: Path, active_slug: str, ...) -> None` -- uses `fs.symlink`. Assume `active_slug` has already passed `resolve_active_project`'s validation (do not re-derive the charset check here, but DO defensively reject an empty string with a clear error, since this function's signature makes `active_slug` a directly-callable parameter, not only reachable via `resolve_active_project`). Before calling `fs.symlink`, verify each computed target directory (`_bmad-output/projects/<active_slug>/planning-artifacts`, `.../implementation-artifacts`) exists, and raise a clear, named error if not (never silently create a dangling symlink).
  - (d) `detect_symlink_desync(...) -> SymlinkDesync | None` -- when parsing a symlink's raw target to extract its project slug, verify the target's final path segment matches the artifact name being checked (`planning-artifacts` vs `implementation-artifacts`) before treating the parsed slug as meaningful -- a target whose shape doesn't match the expected `projects/<slug>/<name>` pattern (including an absolute-path target, which must be resolved and compared, not rejected as a parse failure) is itself a distinct "unrecognized shape" condition, never silently coerced into agreement or into a false desync.
- [x] `seed/verbs/adopt.py` -- wire the `projects-table` region bypass into `_default_commit` per the Code Map above
- [x] `tests/unit/test_seed_derive_projects_index.py` -- cover the ORIGINAL I/O matrix (N-projects rendering, prose preservation, symlinks-absent creation, idempotent re-run, desync detection with all three values named, never-write refusal, zero-projects edge case) PLUS: pipe/newline in a slug/status/description cell; whitespace-only `BMAD_ACTIVE_PROJECT`/marker; empty resolved active-project; absolute-path-shaped active-project value; `active_slug=""` passed directly to `ensure_symlinks`; a symlink target directory that doesn't exist yet; a symlink target whose final path segment doesn't match the artifact name being checked; an absolute-path symlink target that legitimately resolves to the correct project (must NOT be reported as desync)
- [x] `tests/unit/test_seed_fs.py` -- `symlink()` tests: guard trips on a never-write `link_path`, idempotent no-op, ATOMIC replacement of a stale symlink (assert no absence window via a mocked/instrumented replace call, not just the end-state), a name-collision with a pre-existing regular file/directory is a named error, `mkdir(parents=True)` bootstraps a missing parent directory, a proof that the guard checks the link's own path rather than its resolved target
- [x] `tests/unit/test_seed_verbs_adopt.py` -- the new real-git `projects-table`-via-`derive_projects_table` integration test described in the Code Map

**Acceptance Criteria:**
- Given a repo with N `_bmad-output/projects/*/.bmad-config.toml` files, when a REAL `run_adopt` call applies the `projects-index` entry (not merely a direct unit call to `derive_projects_table`), then the target file's `projects-table` region has exactly N rows with slug/status/description read from each file
- Given hand-written prose elsewhere in `PROJECTS.md`, when the table region is derived, then that prose is byte-identical before and after (proven via the real `regions.apply.substitute_region`/`insert_region` mechanism on a synthetic fixture)
- Given the two symlinks are ensured, when they don't yet exist, then both are created pointing at the active project's `planning-artifacts`/`implementation-artifacts`, atomically if replacing an existing symlink, guarded via `fs.symlink`
- Given a symlink pointing at a different project than the `.active-project` marker, when desync detection runs, then a HARD finding is produced naming both (or all three) disagreeing values -- and given an absolute-path symlink target that actually resolves to the correct project, no false desync is reported
- Given `derive` is asked to write inside `projects/*/planning-artifacts/**`, when that call is attempted, then `NeverWriteViolation` is raised
- Given a malformed/empty/absolute active-project value from any resolution source, when `resolve_active_project`/`ensure_symlinks` is called, then a clear, named error is raised -- never a silently-broken symlink target or a bare unhandled exception
- Given the existing `pyforge-marshal` test suite and meta-tests (P-01 write-primitive scan, layer-import rules), when run after this change, then they all still pass with no new violation

## Design Notes

**Why `fs.symlink` is a new primitive, not a workaround.** `fs.py`'s own module docstring
states plainly that no V1 target artifact was expected to be a symlink, so the module doesn't
special-case one — this story is exactly the case that assumption stops holding. Add `symlink()`
as a sibling to `write`/`replace_span`/`remove`, guarded the same way (resolve `link_path` to
its parent's absolute form for the never-write check — the link itself may not exist yet, so
resolve via the parent directory, matching how a brand-new file's guard already has to handle
"target doesn't exist yet"). Use `Path.symlink_to`/`os.symlink` only inside this one function.

**Idempotence.** "Ensuring" a symlink means: if it already exists and already points at the
correct target (compare resolved target, not just the raw string, to tolerate `../` vs absolute
forms), do nothing. If it exists and points elsewhere, replace it (unlink + re-create, still
through the guarded primitive). If a REGULAR FILE or directory already occupies that path (not a
symlink), that is a named error, not a silent overwrite — this mirrors `write`'s own refusal
posture for unexpected pre-existing state elsewhere in this package.

**Desync detection shape.** Reuse whatever findings/severity vocabulary earlier epics already
established (check `seed/errors.py` and any `Finding`-shaped dataclass before inventing a new
one) so this integrates with however `marshal seed check`/`adopt` already surfaces findings to a
caller, rather than introducing a parallel reporting shape for just this one check.

**KEEP (from the reverted first pass — these worked and must survive re-implementation):**
- `_guard` grows a `resolve_leaf: bool = True` parameter rather than a duplicate guard function — `write`/`replace_span`/`remove` call sites stay byte-for-byte unchanged (default preserves prior behavior), `symlink()` is the only caller passing `resolve_leaf=False`. No drift risk between two guards.
- `SymlinkDesync` stays a local, frozen dataclass in `derive/projects_index.py`, NOT a `detect.findings.Finding` reuse — the architecture's module-dependency layering (`verbs -> (detect, plan, apply, migrate) -> (model, state, regions, engine, derive) -> fs`, no upward imports) places `derive` below `detect`; importing `detect.findings` from `derive` would itself violate that rule. `seed/errors.py` has no suitable existing shape (only the closed `SeedError` exit-code hierarchy). A future `detect`-layer story can wrap one in a real `Finding` once desync detection is wired into `marshal seed check` (which this story does NOT do — see the Never bullet below).
- `tomllib`-based `.bmad-config.toml` parsing, mirroring `resolve_config.py`'s own approach — no new third-party TOML dependency.
- Every test operates on synthetic `tmp_path` fixtures exclusively; the first pass verified (and this pass must re-verify) that no real `_bmad-output/planning-artifacts`, `_bmad-output/implementation-artifacts`, or `_bmad/custom/.active-project` is created or touched anywhere in this actual worktree as a side effect of the test run.

**Never (added this pass):** wiring `detect_symlink_desync` into `marshal seed check`'s live output is explicitly OUT of scope for this story — Story 11.2's Surface per `epics.md` is `seed/derive/projects_index.py` (plus, per this amendment, the minimal `verbs/adopt.py` dispatch hook the table-derivation gap requires); `verbs/check.py` integration is a future story's job. The function must exist, be correct, and be tested — it does not need a live caller yet. This differs from the table-derivation fix above precisely because `verbs/adopt.py`'s existing dispatch ALREADY calls into the `projects-index` entry today (so leaving it wrong means active, wrong production behavior), whereas nothing anywhere calls `detect_symlink_desync` today (so leaving it unwired means inert, not wrong).

## Design Notes addendum (implementation pass 2, 2026-08-21)

Every path in the Code Map matched the plan exactly — no path changes. Implementation-discovered deviations, same convention as Story 11.1's own spec:

- **`SymlinkTargetOccupiedError`, a NEW named exception, added to `seed/fs.py` itself (not `seed/errors.py`).** The Code Map's "named error (not a bare `FileExistsError`)" requirement for `symlink()`'s regular-file/directory-collision case wasn't fully specified as to WHERE that error type should live. `fs.py`'s own module docstring restricts its import surface to `atomic_write_bytes` and `NeverWriteViolation` only — "nothing else from either `pyforge.core` or `pyforge.marshal`" — so importing a new leaf from `errors.py` (which would also grow the closed six-member `SeedError` taxonomy `test_seed_errors.py` enumerates) was the wrong shape. Defined `SymlinkTargetOccupiedError(FileExistsError)` locally in `fs.py` instead, mirroring `regions/apply.py`'s own precedent of small, module-local named exceptions (`RegionShaMismatchError`, `AnchorInsideExistingRegionError`) for a caller-observable pre-existing-state conflict that isn't a `SeedError`-taxonomy concern.
- **`resolve_active_project`'s "nothing resolved" case is validated through the SAME `_validate_slug` choke point as a malformed value**, rather than a second, differently-worded error path — the empty string never matches `_ACTIVE_PROJECT_SLUG_PATTERN`, so routing it through the identical validator (with a synthesized "no source" locator string) satisfies the AC's "a clear, named error is raised" without a second message to keep in sync.
- **`detect_symlink_desync`'s "unrecognized target shape" and "absent/not-a-symlink" conditions are both represented as `<...>`-bracketed sentinel strings** inside `SymlinkDesync`'s own `str` fields, rather than a separate enum/optional field — a real project slug can never contain `<` (the slug charset excludes it), so a sentinel can never collide with, and therefore never be silently coerced into agreement with, a real marker slug. This satisfies the Task's "never silently coerced into agreement or into a false desync" requirement with no additional dataclass shape.
- **The real-`run_adopt` integration test in `test_seed_verbs_adopt.py` uses the REAL packaged manifest** (`real_manifest` fixture, already defined later in that file) with every OTHER entry skipped, mirroring that file's own pre-existing `test_dreams_readme_materializes_against_the_real_manifest_previously_refused_unconditionally` pattern — this is a stronger proof than a from-scratch synthetic manifest, since it also exercises the real `manifest.yaml` reclassification (the `projects-table` region's real anchor `## Projects` against this repo's real heading text) end to end, not just a hand-built stand-in.
- **`test_seed_templates_manifest.py`'s two region-body-file conformance checks needed a shared `_REPO_COMPUTED_REGIONS = frozenset({"projects-table"})` exemption set**, applied symmetrically on both sides of the "every region has a body file" / "every body file is claimed" pair — mirroring Story 11.1's own wrapper-template-filename exemption precedent for the identical reason: `projects-table` is a real, declared hybrid region with deliberately NO `files/*.j2` counterpart to ship.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: full suite green, including new `test_seed_derive_projects_index.py`, the new `symlink()` coverage in `test_seed_fs.py`, and the new real-`run_adopt` integration test in `test_seed_verbs_adopt.py`
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: green, no new disallowed import

## Auto Run Result

**Summary:** Added `seed/derive/projects_index.py`: `derive_projects_table` (renders `_bmad-output/PROJECTS.md`'s Projects table from live `.bmad-config.toml` files), `resolve_active_project` (mirrors `resolve_config.py`'s precedence with added validation), `ensure_symlinks` (creates/atomically re-points the two BMAD artifact symlinks via a new `fs.symlink` primitive), and `detect_symlink_desync` (a HARD-finding-shaped desync detector). Reclassified the `projects-index` manifest entry to `hybrid-managed-region` and wired its `projects-table` region directly into `verbs/adopt.py`'s dispatch (bypassing the static-fragment mechanism, since this region's content is computed from the adopting repo's own state). Went through one bad_spec loopback (a full revert + re-derivation) after review pass 1 found the first implementation shipped a wrong static placeholder that would have silently overridden the real derived content in production — fixed and re-verified by a second, independent review pass, which found 9 further hardening gaps (all patched directly) and 3 pre-existing/out-of-scope gaps (deferred as `DW-FU-11-2`/`DW-FU-11-2-2`).

**Files changed:**
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/derive/projects_index.py` -- new module.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/fs.py` -- new `symlink()` primitive, `SymlinkTargetOccupiedError`, `_guard`'s `resolve_leaf` parameter.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/adopt.py` -- `projects-table` region dispatch (id-guarded).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/templates/manifest.yaml` -- `projects-index` reclassified.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_derive_projects_index.py` -- new, full I/O-matrix + pass-2 hardening coverage.
- `src/shared/packages/pyforge-marshal/tests/unit/test_seed_fs.py`, `test_seed_templates_manifest.py`, `test_seed_plan_build.py`, `test_seed_verbs_adopt.py` -- updated fixtures/counts, new `symlink()` and dispatch-hijack coverage.

**Review findings breakdown:** Pass 1: 1 bad_spec (high, full loopback), 4 rejected. Pass 2: 9 patched (4 medium, 5 low), 3 deferred (`DW-FU-11-2`, `DW-FU-11-2-2` -- one entry covers two related findings), 4 rejected.

**Verification performed:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` → 5102 passed, 9 deselected. `pixi run --frozen -e pyforge-ci pyforge-deps-test` → 84 passed. `ruff check` on every touched file → clean. Confirmed no real `_bmad-output/{planning,implementation}-artifacts` or `_bmad/custom/.active-project` created/touched at any point (both implementation passes and the patch pass).

**Residual risks:** Low. The two deferred items are pre-existing/out-of-scope architectural gaps (the `insert_region`-splices-above-existing-content hazard shared with Story 11.1's own targets, and the not-yet-wired `check`/symlink-manifest-entry integration), both filed with clear remedies for a future story. No known live defect remains in this story's own scope.

**Baseline:** `5f23cd638abf626cf13e8a0e08c4919592807f36`
**Final:** (set after commit below)

## Spec Change Log

### 2026-08-21 — bad_spec loopback (review pass 1)
**Triggering finding:** the first implementation pass's Code Map explicitly said `_bmad-output/PROJECTS.md` was "NOT modified by this story directly... wiring this story's output into a real `marshal seed adopt` run against this actual repo is a future adoption event, not this story's job." The implementer, working from that Code Map, shipped a static `templates/files/projects-table.md.j2` placeholder purely to satisfy a pre-existing conformance test — but `verbs/adopt.py`'s existing, UNMODIFIED `_default_commit`/`_region_body_from_template` dispatch already runs for real against the reclassified `projects-index` entry on any real `adopt`/`check` call, so that static placeholder — never the real `derive_projects_table()` function — is what would actually ship, unconditionally, even in a repo with real projects. `derive_projects_table` was fully implemented, fully unit-tested, and completely unreachable from any real code path. Caught by the Blind Hunter review pass, corroborated independently by the Edge Case Hunter pass finding multiple related validation gaps (unescaped table cells, unvalidated `active_slug`, non-atomic symlink replacement, desync-detection false positive/negative shapes).

**What was amended:** the Code Map now requires wiring `derive_projects_table` directly into `verbs/adopt.py`'s `_default_commit` dispatch for the `projects-table` region specifically (bypassing `_region_body_from_template` for that one region, mirroring Story 11.1's own `ADAPTER_COMPOSITION`-style bypass precedent) — no static placeholder file at all. The Tasks list gained explicit sub-items for: escaping every table-cell column (not description alone) against `|` and newlines; `resolve_active_project` validating its resolved value against a slug charset and treating whitespace-only sources as absent; `ensure_symlinks` rejecting an empty `active_slug` and verifying the target directory exists before creating a symlink to it; `fs.symlink` using an atomic temp-symlink-then-replace swap (mirroring `scripts/bmad-switch::repoint_links`) instead of unlink-then-recreate, plus `mkdir(parents=True)` for a not-yet-existing parent; and `detect_symlink_desync` correctly handling an absolute-path symlink target and verifying the target's final path segment against the artifact name being checked. A new Never bullet explicitly scopes `marshal seed check` integration OUT of this story (distinguishing "actively wrong because something already calls it" from "merely not yet wired up," which is why the table-derivation gap needed fixing now and the check-integration gap does not).

**Known-bad state avoided:** a repo running `marshal seed adopt --apply` for real against this reclassified manifest entry would have silently written a wrong, static, single-sentence placeholder into `PROJECTS.md`'s table region on every apply — the exact "silent drift because nothing derives from ground truth" failure mode this whole story exists to close, reproduced by the story meant to close it.

**KEEP instructions:** see the Design Notes' own "KEEP (from the reverted first pass)" list above — the `_guard`/`resolve_leaf` extension, `SymlinkDesync` as a local dataclass (with its layering rationale), `tomllib`-based config parsing, and the synthetic-fixture-only test discipline all worked correctly in the first pass and must be reproduced unchanged in the re-implementation.

## Review Triage Log

### 2026-08-21 — Review pass 1
- intent_gap: 0
- bad_spec: 1 (high 1)
- patch: 0
- defer: 0
- reject: 4 (low 4)
- addressed_findings:
  - `[high]` `[bad_spec]` The static `projects-table.md.j2` placeholder silently shipping as real, wrong `PROJECTS.md` content through the pre-existing, unmodified `verbs/adopt.py` dispatch, while the real `derive_projects_table()` was fully implemented but completely unreachable — Code Map and Tasks amended to require wiring into `_default_commit`'s dispatch directly (mirroring Story 11.1's precedent), no static placeholder; see Spec Change Log entry above for full detail. This single root cause also subsumes and resolves: the escaping bugs, `active_slug` validation gaps, the non-atomic symlink swap, and the desync-detection shape gaps flagged by both review passes — all folded into the SAME amended Tasks list rather than run as separate loopbacks, since fixing the wiring meant touching the same functions anyway.
  - `[low]` `[reject]` (x2, Edge Case Hunter) `fs.symlink` not guarding `target` against the never-write set — rejected as a misreading of the intended semantics: this story's only real callers pass a `target` that IS a never-write path BY DESIGN (the symlink's whole purpose is to point at protected content), so guarding `target` would make the feature impossible to build. The amended Code Map now requires the function's own docstring to state this explicitly so it stops looking like an oversight to future reviewers.
  - `[low]` `[reject]` (Blind Hunter) Lossy/terse `.bmad-config.toml` description vs. the real `PROJECTS.md`'s curated prose, and the real file's historical/dissolved-project rows having no `.bmad-config.toml` backing — both are consequences of actually running `adopt --apply` against THIS repo's real file, which the spec already scopes out as a future adoption event; no synthetic fixture test needs to model either concern, and the amended spec's Code Map now states this distinction explicitly (code correctness vs. real-repo invocation) to prevent the same ambiguity recurring.
  - `[low]` `[reject]` (Blind Hunter) `ensure_symlinks`'s partial-failure behavior (first symlink succeeds, second raises, caller doesn't know which changed) — accepted as a reasonable, already-documented trade-off ("closer to correct, not rolled back"); a caller needing to know exact state can call `detect_symlink_desync` separately.

### 2026-08-21 — Review pass 2
- intent_gap: 0
- bad_spec: 0
- patch: 9 (high 0, medium 4, low 5)
- defer: 3 (low 3)
- reject: 4 (low 4)
- addressed_findings:
  - `[medium]` `[patch]` `_default_commit`'s `projects-table` dispatch keyed on `region_name` alone (region names are a namespace shared across manifest entries by this package's own design) — added `and entry.id == "projects-index"`, matching `ADAPTER_COMPOSITION`'s own unique-id-keyed precedent; new test `test_a_region_named_projects_table_on_a_different_entry_id_is_not_hijacked`.
  - `[medium]` `[patch]` `ensure_symlinks`'s two `fs.symlink` calls could leave a half-migrated pair with no diagnostic on partial failure (re-raised, upgraded from pass 1's reject on independent re-confirmation by both reviewers) — wrapped with a clear `PreconditionFailure` naming which link(s) already changed before the failure (never a rollback — this module's own Never bullet against auto-repair); new test `test_ensure_symlinks_names_which_link_already_changed_on_a_partial_failure`.
  - `[medium]` `[patch]` `resolve_active_project`'s marker read only caught `OSError`, not `UnicodeDecodeError` — a non-UTF-8 marker raised an uncaught exception instead of falling through like a missing one; fixed, new test `test_resolve_active_project_treats_a_non_utf8_marker_as_absent_not_a_crash`.
  - `[medium]` `[patch]` `derive_projects_table` had no duplicate-slug detection, unlike this package's established "ambiguity is refused loudly" convention elsewhere (`_read_fragment`'s identical refusal) — added, raising `PreconditionFailure` naming both directories and the shared slug; new test `test_derive_projects_table_raises_on_two_directories_sharing_the_same_slug`.
  - `[low]` `[patch]` `_escape_cell` didn't escape backticks, while the slug column wraps its value in a markdown code span — added; new test `test_derive_projects_table_escapes_a_literal_backtick_in_a_slug`.
  - `[low]` `[patch]` `derive_projects_table` crashed on an unlistable `projects_dir` (e.g. a permission error) instead of degrading to the header-only table like a missing directory — wrapped `iterdir()` in `try/except OSError`; new test `test_derive_projects_table_treats_an_unlistable_projects_dir_as_header_only`.
  - `[low]` `[patch]` `_project_row`'s docstring overclaimed that a valid-TOML-but-missing-`[project]`-table file contributes no row — it always did (falls back to dirname/blank fields); corrected the docstring to match actual behavior rather than changing behavior.
  - `[low]` `[patch]` The "index cannot go stale" framing didn't acknowledge that `detect/inventory.py`'s existing presence-only hybrid-region conformance check means this only holds for one `adopt` run (a pre-existing S-9.3 architectural characteristic, not introduced by this story) — added an explicit docstring caveat.
  - `[low]` `[patch]` The Never bullet didn't cover the pre-existing `planning-artifacts-symlink`/`implementation-artifacts-symlink` manifest entries also lacking a dispatch hook into `ensure_symlinks` — extended the same "inert, not wrong; future story's job" reasoning to them explicitly, since nothing schedules an `Action` for either id today.
  - `[low]` `[defer]` The real, live `_bmad-output/PROJECTS.md` has no region markers under its `## Projects` heading today, and `insert_region` INSERTS at the anchor rather than replacing following content — the first real `adopt --apply` against this repo's own file would splice a new region above the existing hand-written table rather than cleanly replacing it. Confirmed this is a pre-existing `insert_region` (Story 8.4) characteristic that applies equally to `AGENTS.md`/`CLAUDE.md`'s own regions from Story 11.1 (both files already carry hand-written prose under their anchor headings today) — not something this story introduces or worsens. Filed as `DW-FU-11-2`.
  - `[low]` `[defer]` The two pre-existing `planning-artifacts-symlink`/`implementation-artifacts-symlink` manifest entries (`generated-derived`) have no dispatch hook wiring them to `ensure_symlinks`/`fs.symlink` — if `build_plan` ever schedules an `Action` for either, `_default_commit`'s generic whole-file fallback runs instead, most likely raising a loud `InternalError`/`TemplateBoundaryError` (matching Story 11.1's own "known, inherited limitation" class for other content-less `generated-derived` entries), not silently writing wrong content. A future story should wire both into `_default_commit`'s dispatch via `ensure_symlinks`, likely alongside wiring `detect_symlink_desync` into `marshal seed check`. Filed as `DW-FU-11-2-2`.
  - `[low]` `[defer]` (same root cause, third instance) `marshal seed check` integration for `detect_symlink_desync` — already explicitly scoped out in this spec's own Never bullet; recorded here for completeness alongside the other two related, adjacent wiring gaps above rather than re-litigated as a new finding. Folded into the same `DW-FU-11-2-2` entry rather than a fourth, redundant one.
  - `[low]` `[reject]` (Blind Hunter) Derived table dropping the real `PROJECTS.md`'s dissolved-project historical rows / description terseness vs. curated prose — already explicitly scoped out in pass 1 (the spec's Code Map distinguishes code correctness from actually invoking `adopt --apply` against this repo's real file); re-raised in materially the same form, no new information.
  - `[low]` `[reject]` (Blind Hunter) A `.bmad-config.toml`'s declared `slug` drifting from its directory name — real but latent (all 8 live configs agree today), and moderately costly to fully address (would need a cross-check against `resolve_active_project`'s own directory-name assumption); left as a known, narrow edge case rather than expanding scope further this pass.
  - `[low]` `[reject]` (Blind Hunter) Stale `AD-63` citation in `epics.md` — a planning-document nit, not this story's code.
  - `[low]` `[reject]` (Edge Case Hunter) TOCTOU between `fs.symlink`'s existence check and `os.replace()` — matches this module's own already-documented, already-accepted TOCTOU trade-off for `write`/`replace_span` (same file, same rationale: not a sandbox defending against a co-located adversarial process); `symlink()`'s own docstring already inherits that framing implicitly via the module docstring, no further doc addition needed. Concurrent same-process `symlink()` calls colliding on the same tmp-file name — no real call site in this codebase produces two calls for the same `link_path` within one process, so this is unreachable in practice.

**Verification after this pass:** `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` → 5102 passed, 9 deselected (+6 new tests since pass 2 began). `pixi run --frozen -e pyforge-ci pyforge-deps-test` → 84 passed. `ruff check` on every touched file → clean. No real `_bmad-output/{planning,implementation}-artifacts` or `_bmad/custom/.active-project` created or touched (`git status --porcelain` + directory listing both confirm).
</content>
