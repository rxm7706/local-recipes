# Knowledge: Gotchas (G1-G110 subset relevant to Slice 2)

## Contents

- [Cross-slice dependency re-derivation](#cross-slice-dependency-re-derivation)
- [Gotcha citations](#gotcha-citations)

Verbatim from slice 2's brief (`skill-brief.yaml` `scope.notes`), itself extracted
programmatically from the live `.claude/skills/conda-forge-expert/SKILL.md` at CFE
v8.84.0 (Story 12.6, 2026-08-28) -- not retyped by hand. This is the single largest
knowledge input to this skill: ~104 gotcha IDs (of which only ~14 have a literal
in-code `G<N>` reference in the live scripts tree; the rest are narrative guidance an
authoring/reviewing agent applies by judgment).

## Cross-slice dependency re-derivation

SLICE 2 of the conda-forge-expert rebuild campaign (Recipe Lifecycle),
mason Epic 12 Story 12.6. Companion to cfe-recipe-generation (Slice 1). Governing
artifacts: _bmad-output/projects/pyforge-mason/planning-artifacts/specs/
spec-conda-forge-expert-rebuild/{SPEC.md,slice-map.md,campaign-state.yaml}.

=== MCP tools (19, invocation surface -- not separately compiled; each has a
backing canonical script above except trigger_build/get_build_summary, which
have no canonical script per slice-map.md) ===
validate_recipe, check_dependencies, run_system_health_check,
scan_for_vulnerabilities, trigger_build, get_build_summary, lookup_feedstock,
enrich_from_feedstock, get_feedstock_context, edit_recipe, update_mapping_cache,
analyze_build_failure, optimize_recipe, update_recipe, prepare_submission_branch,
submit_pr, check_github_version, migrate_to_v1, download_pr_artifacts.

=== Cross-slice dependency re-derivation (this story's own duty; re-run against
the live tree at CFE v8.84.0, not just re-cited from slice-map.md's v8.82.3
snapshot) ===

1. CONFIRMED, still holding: _cfy_template.py <- submit_pr.py; _paths.py <-
   recipe_optimizer.py, feedstock_lookup.py, feedstock_context.py; _http.py <-
   mapping_manager.py, dependency-checker.py, recipe_updater.py, npm_updater.py,
   pr_artifacts.py, github_version_checker.py. Verified via precise per-file
   import-line grep (`grep -nE '^\s*(import|from)\s+(_http|_paths|_cfy_template)'`),
   not filename-containment matching.

2. CONFIRMED, no NEW cross-slice sibling imports among slice 2's own 22 scripts
   beyond what slice-map.md already names (a full local-import scan of every
   slice-2 script against every canonical-script basename in the live tree found
   only the already-documented set, plus the intra-slice
   feedstock_enrich.py -> feedstock_lookup.py and submit_pr.py/recipe_editor.py
   -> _path_guard.py imports slice-map.md's own Slice-5 notes already account
   for). Slice 1's github_version_checker.py surprise does not recur here.

3. NEW FINDING -- previously-undocumented, unclassified script (this story's
   own version of slice 1's BLOCKED-then-retry precedent, budgeted per this
   story's own boundary): `.claude/skills/conda-forge-expert/scripts/
   failure_catalog_generator.py` exists in the live tree (added 2026-08-22,
   mason Story 7.1, `spec-machine-checked-recipe-knowledge` CAP-1 -- one
   commit AFTER slice-map.md's 2026-08-21 derivation) and is NOT classified in
   slice-map.md at all. Live-tree totals are therefore 69 canonical scripts /
   58 CLI wrappers / 46 MCP tools today, not the 68/57/46 slice-map.md's
   Coverage Reconciliation table states. Facts gathered: it has a CLI wrapper
   (.claude/scripts/conda-forge-expert/failure_catalog_generator.py) and a
   pixi task (generate-failure-catalog) but NO MCP tool; it imports Slice 5's
   _paths.py (get_repo_root); it is a deterministic parser of SKILL.md's
   gotcha corpus that cross-references Slice 2's own recipe_optimizer.py
   check-code registry to derive config/failure-catalog.yaml (included above
   as a knowledge asset). Because it operationally supports Slice 2's build-
   failure-diagnosis knowledge (recipe_optimizer.py's check codes,
   failure_analyzer.py's domain) more than any other slice's, the natural
   classification is Slice 2 -- but slice-map.md is this story's own
   documented READ-ONLY source (Code Map), so this brief does NOT add it to
   scope.include or silently absorb it; it is flagged here for a follow-up
   slice-map.md correction pass (out of this story's writable surface) before
   any story compiles it into either slice's package.

4. CVE-DB / Slice-3 ordering risk (slice-map.md "Known ordering risk") --
   RE-CONFIRMED CLEAN, not a blocker for this brief. vulnerability_scanner.py
   (Slice 2, scan_for_vulnerabilities) has no Python IMPORT of cve_manager.py
   (Slice 3) -- grep confirms zero `import cve_manager` lines; its three
   references are comments/docstrings naming cve_manager.py as the tool that
   BUILDS the local CVE database file vulnerability_scanner.py reads at
   runtime. This is a DATA dependency (a database file on disk), not a CODE
   dependency requiring a source-level port the way slice 1's
   github_version_checker.py did. Under this campaign's parallel-run
   constraint (CAP-3: the live original stays authoritative at every commit
   until the single end cutover), the CVE database is built by whichever
   cve_manager.py is live today regardless of Slice 2's or Slice 3's own
   rebuild status -- nothing has cut over, so Slice 3 remaining `mapped`
   (unbriefed, now atlas-owned per Story 12.5) does not block Slice 2's own
   brief/compile/equivalence work. Residual, non-blocking risk carried
   forward (not this story's to close): a future CVE-DB schema change by
   whichever party eventually rebuilds Slice 3 could affect Slice 2's reader
   at end-cutover time -- re-check at that point, not now.

5. native-build.sh / build-locally.py cutover-scope DECISION (AC's own
   explicit requirement, decided no later than this brief): PERMANENTLY OUT
   OF SCOPE for this campaign's rebuild-and-cutover. Both are live Mason
   callers (cfe.py's build_native/build_docker adapters, Story 2.6) but
   neither is a rebuild target:
     - build-locally.py lives at the literal CFE-root/repo-root top level,
       outside all three of SPEC.md's own declared `surface:` globs
       (.claude/skills/conda-forge-expert/**, .claude/scripts/
       conda-forge-expert/**, .claude/tools/conda_forge_server.py) -- it is
       not part of the skill being rebuilt in the Spec's own contractual
       sense.
     - native-build.sh, while physically inside the
       .claude/scripts/conda-forge-expert/** surface glob, is a bash
       CLI-invocation wrapper (platform detection + `rattler-build build`
       dispatch) with no extractable recipe-authoring knowledge -- Skill
       Forge's compilation model (source code + knowledge -> skill) has no
       natural target here, and slice-map.md's own CAP-1 derivation already
       excludes .sh files from the counted "CLI wrappers" surface for
       exactly this reason (only *.py wrappers count).
     - Consequence for the end-cutover plan (campaign-state.yaml's own
       "Not yet accounted for" gap, closed by this decision): neither script
       gets a `campaign.callers` entry. Only the 8 _CFE_SCRIPTS adapters that
       resolve to Slice-2 Python canonical scripts need a caller-flip entry
       at end cutover; build_native/build_docker keep calling their fixed-
       location scripts unconditionally, indefinitely, unless a SEPARATE,
       future decision revisits them (out of this campaign's scope).

=== Gotcha citations (verbatim SKILL.md headings, extracted programmatically
from the live file -- not retyped by hand) ===

Slice-map.md's own blanket claim ("G1-G53, G55-G90, G92-G97, G99-G108") is
CONFIRMED as substantively correct by this pass, with two refinements:

(a) G94 stays whole for Slice 2 (mirror-dir staleness classes 1-2 are
    operational Slice-2 concerns -- pre-submission/mirror-refresh checks);
    only its third sub-item (case-variant generator output dirs, an internal
    "G94c" shorthand comment that is NOT itself a numbered SKILL.md gotcha)
    is Slice 1's, per slice-map.md's own note. Live-tree confirmation: G94's
    case-variant-dirs concern is ALSO referenced in Slice 2's own
    _path_guard.py (line 36, "see G94's case-variant output dirs") -- a
    second, independent Slice-2 anchor for the same sub-item slice-map.md
    attributed only to Slice 1's recipe-generator.py.

(b) G109 and G110 (SKILL.md gotchas 109-110, added CFE v8.83.0, 2026-08-27 --
    ONE version AFTER slice-map.md's v8.82.3 derivation) are NOT in
    slice-map's frozen "up to G108" range at all, and belong in Slice 2's
    citation list: G109's own live-tree references are in Slice 1's
    github_updater.py (lines 270/299, "Story 15.2 / CAP-2 HEAD-advance path
    for commit-pinned recipes (G109)") -- but github_updater.py's
    update_recipe() is implemented via the sanctioned cross-slice import of
    Slice 2's OWN github_version_checker.py (see slice-map.md's Slice-5
    cross-slice-shared-imports table), so G109's tag/version-resolution risk
    class bears directly on Slice 2's own version-comparison logic, not just
    Slice 1's HEAD-advance caller. G110 ("re-read the bin map on every
    version bump") is squarely Slice 2's npm_updater.py update-workflow
    territory even though it has no code-level ID reference yet (most of the
    corpus below is narrative guidance with no code anchor at all -- expected
    for a knowledge-driven skill; see (c)).

    Both carry `enforced_by: null` in config/failure-catalog.yaml (Story
    7.1's generator) -- unenforced backlog items, not yet wired to a
    recipe_optimizer.py check code.

(c) Borderline cases surfaced by cross-referencing each ID against the live
    scripts that literally reference its number (`grep -rlE '\bG<N>\b'
    scripts/*.py`), kept in Slice 2's list (not excluded) because the topical
    fit still holds even though the code anchor sits in a Slice-1/3 file:
    G4 (sdist-may-omit-LICENSE) -- root cause is Slice 1's source selection,
    but the symptom ("build fails") is failure_analyzer.py's (Slice 2)
    diagnosis territory. G7/G8 (Grayskull import-name / redundant host deps)
    -- generation-time root cause, but recipe_optimizer.py/
    dependency-checker.py (Slice 2) are plausible catchers of the resulting
    defect at review time. G10 (PyPI<->conda name divergence, four
    spellings) -- genuinely cross-slice (Slice 1 name_resolver.py, Slice 2
    dependency-checker.py, Slice 3 atlas mapping tools all rely on it). G61
    (GitHub archive sha256 drift), G62 (never-ship-cfe-metadata, verify on
    the pushed artifact), G83 (conda-forge.yml mostly inert during PR build),
    G90 (freshly-generated recipes need a sanitize/verify pass) -- each has a
    concrete Slice-2 operational anchor (github_version_checker.py's
    re-check-on-update path; submit_pr.py's pre-push strip-and-verify step;
    submit_pr.py's own G83 reference; validate_recipe.py as the natural
    sanitize-pass runner) independent of where the code-level ID citation
    happens to live today.

Of the ~104 non-excluded IDs, only ~14 have any literal in-code `G<N>`
reference anywhere in the live scripts tree (the majority of the corpus is
narrative guidance an authoring/reviewing agent applies by judgment, not a
hard-coded check -- consistent with CFE's knowledge-driven design, not a gap
in this derivation).

## Gotcha citations

- G1. `script:` list entries run in separate shells — env vars do NOT carry across entries
- G2. v0/meta.yaml field names in v1 recipe.yaml are silently ignored
- G3. `py < N` skip selectors do nothing in v1 recipe.yaml
- G4. Sdist may omit LICENSE — `pip install` succeeds, build fails with "No license files were copied"
- G5. tree-sitter PyPI sdists inconsistently strip `src/tree_sitter/*.h` headers — default to GitHub source
- G6. npm packages with rich transitive deps ship `node_modules/.bin/` symlinks that fail noarch builds
- G7. Grayskull's inferred Python import name can be wrong — verify against the sdist
- G8. Grayskull adds redundant `wheel` + `setuptools` host deps for poetry-core projects
- G9. Monorepo upstreams may have no per-language Git tag — pin the LICENSE to a commit hash
- G10. PyPI → conda-forge name divergence — verify across four spellings before declaring a dep missing
- G11. PyPI sdist symlinks fail hatchling's wheel build on Windows
- G12. Platform-conditional `run:` deps in noarch:python recipes need `noarch_platforms` in `conda-forge.yml`
- G13. CWD persists across `script:` list entries — and `(cmd)` is not a subshell on Windows cmd.exe
- G14. Autotick bot v0 version bumps can fail the conda-forge-linter `package.version` float-parse rule
- G15. Rebuilding the same recipe re-hashes the `.conda` artifact but leaves `repodata.json` stale
- G16. PyPI Varnish CDN degradation on `/packages/source/<letter>/...` route
- G17. `pnpm install --ignore-scripts` doesn't suppress the root project's lifecycle scripts
- G18. `workflow_settings.store_build_artifacts: true` (unscoped) crashes Windows Azure builds via 7z + INetCache ACLs
- G19. Windows pip-install fails `Error reading output: stream did not contain valid UTF-8` — set `PYTHONUTF8: "1"` (+ canonical Rust env block while you're there)
- G20. v0 jinja `{{ X }}` syntax in v1 recipe.yaml is silently rendered as literal text
- G21. conda-smithy mis-aligns the zip-keyed `is_python_min` flag when `python_min` is overridden upward
- G22. Recipe-local CBC `python:` override using `*_cpython` suffix crashes smithy on py3.13+
- G23. Inline `sed` + `powershell` in `build.script` hits cmd.exe escape hell — use `sed` (with `m2-sed` on Windows) for a single cross-platform line
- G24. Conda label ≠ wheel `dist-info` version — when upstream's `pyproject.toml` hardcodes a placeholder, `pip check` fails downstream
- G25. Conda has no "extras" — flatten every `pkg[extra]` upstream dep into `run:`, and resolve each extra to its *actual* conda packages (which may be renamed)
- G26. Loosening upstream `==` pins to `>=` requires patching the source pyproject when `pip_check: true` — the wheel METADATA bakes in the `==`
- G27. A top-level `import` in a split package can eagerly pull a sibling's submodule whose deps are only declared under an extra
- G28. An external dep's broken `dist-info` version (e.g. conda-forge `pdfminer.six` → 0.0.0) breaks `pip_check` for any dependent that pins it exactly
- G29. Multi-output recipe checkers are top-level-only — `optimize_recipe` TEST-001 and `check_dependencies` silently ignore `outputs[]`
- G30. conda-forge `protobuf` is the Python bindings (no `protoc`) — Rust prost/tonic builds need `libprotobuf`; a stray host `protoc` masks it locally
- G31. Overriding `python_min` upward on an existing feedstock — v1 needs a recipe-local `conda_build_config.yaml` (+ rerender); v0 needs `{% set python_min %}`; `context.python_min` is silently ignored in v1
- G32. Triaging autotick-bot version-bump PRs (flake vs. real fix) — and pushing the fix to the bot's branch
- G33. Local rattler-build of a v1 feedstock recipe — don't pass `.ci_support` as a variant config; its strict `channel_sources` excludes the just-built package from its own test
- G34. `pkg_resources.declare_namespace` packages (e.g. `fs` / Pyfilesystem2) break under setuptools 81+ → `ModuleNotFoundError: No module named 'pkg_resources'`
- G35. noarch numpy env-marker selector collapse (a G12 refinement) — per-Python numpy run-dep selectors track numpy's *own* wheel-availability floor, not a package feature
- G36. Stale conda-forge build whose wheel METADATA caps a dep tighter than its conda `run:` dep → `pip check` fails even though the conda solve succeeds
- G37. `[tool.uv]` no-build / source flags in an sdist are NOT runtime dependencies — read deps only from `[project.dependencies]`
- G38. A compiled local-only prereq built for only ONE Python blocks consumers on other Python versions (compiled ≠ noarch)
- G39. setuptools_scm private-API `_version_helper` import breaks at metadata generation (cf ships setuptools_scm 8.x)
- G40. A dependency can DROP a Python version in a newer release — a noarch consumer's declared floor then can't resolve the dep's latest build (refines G38)
- G41. A hidden py3.11 floor via an unconditional PEP-655 / new-stdlib import overrides the consumer's declared `requires-python`
- G42. Verify the CURRENT version's artifact shape before assuming compiled — build shape can change across versions
- G43. v1 inline `# comment` on a list item trips conda-smithy's comment-selector lint — use a full-line comment ABOVE instead
- G44. .NET / C# CLI tools have NO source-build path on conda-forge — repackage the self-contained release binaries per-platform
- G45. A browser SPA (Vue/React/Svelte + Vite) is usually NOT conda-forge-submittable — run the viability gate first, then build local-only as a static-site + launcher
- G46. A stale local `meta.yaml`'s `noarch: python` flag can be WRONG for a genuinely-compiled package — the CURRENT sdist is the source of truth (the "local-meta-is-wrong" sibling of G42)
- G47. A stale git-tracked recipe-dir `conda_build_config.yaml` (a verbatim copy of the global pinning CBC) breaks the build — lint errors + a variant `duplicate entry` collision; rattler-build auto-discovers it
- G48. "Rust / Go upstream" does NOT imply a heavy from-source compile — verify the actual PEP-517 build backend before sizing the build or adding `compiler('cxx')`
- G49. Per-Python compiled ≠ abi3 — verify against `Cargo.toml` / setup.py before adding `version_independent` + `python-abi3`; a per-Python artifact needs a SIMPLE imports+pip_check test, not the CFEP-25 cross-version triad
- G50. A newer CPython that drops a private C-API symbol breaks a compiled build / a host pin — cap the python matrix to upstream's supported range with `match(python, ">=N")` (NOT `py<N`, per G3)
- G51. A GitHub monorepo subdir may ship NONE of the release-time-generated assets — source the PyPI wheel instead, or you ship a broken empty package (a possibly-already-deployed REAL BUG)
- G52. Bulk recipe sweeps poison a shared local channel — build each recipe into an ISOLATED per-recipe output dir
- G53. Refreshing an existing feedstock must RE-MERGE the deployed maintainer list — a regen emits only the invoker and silently drops co-maintainers
- G55. "No valid build backend found for Python recipe … using pip" → a SOURCE build needs an explicit build backend in `host` (wheel installs do NOT)
- G56. Multi-output `noarch: python` build scripts must be cross-platform — bash `cd "$SRC_DIR/<sub>"` + `"$PYTHON"` fails on win-64; use `${{ PYTHON }} -m pip install ./<sub>`
- G57. A build-control env var set only via bash `export` is UNSET on win-64 — the build silently falls back to a network fetch (CMake FetchContent 404)
- G58. `lookup_feedstock` BEFORE submitting — a package already on conda-forge is rejected by the GHA linter ("feedstock exists"), even while the linting-service bot says "excellent"
- G59. Prefer a SOURCE PATCH over an in-build `sed` for editing upstream source — bare `sed -i` fails on macOS/BSD sed (noarch builds on every platform), and reviewers ask for patches
- G60. The strip-before-push must remove ONLY `extra.cfe-*` keys + `# CFE …` blocks — never the schema header or `context:` block
- G61. GitHub commit-archive (`archive/<commit>.tar.gz`) sha256 can drift — GitHub re-gzips, breaking the recorded checksum
- G62. NEVER ship `cfe-*` metadata — the strip is mandatory AND must be VERIFIED on the pushed artifact (verify, don't assume)
- G63. Open staged-recipes PRs with the conda-forge **template + completed checklist** — `--body` REPLACES the template, it does not merge
- G64. Request review with ONE language-matched ping AFTER CI is all-green — and check the PR's LABELS first (the bot's labels are the dedup signal)
- G65. Local-vs-CI linter parity — lint with the CURRENT conda-smithy via `pixi exec`, and run the `linter.py` checks conda-smithy doesn't
- G66. A MERGED staged-recipes PR is NOT immediately installable — verify the prereq is LIVE on the cf channel before submitting its dependent
- G67. An external feedstock's stale `run_constrained` can block a consumer — it lives in `constrains`, NOT `depends`, so verify with the REAL consumer solve (a narrow dry-run misses it)
- G68. After an upstream/feedstock skew resolves, PURGE the obsolete local workaround build — stale higher-build artifacts shadow the real cf package under strict channel priority
- G69. A multi-output / suite version bump can CASCADE to a sibling recipe bump via a tightened cross-dep — bump + rebuild the sibling locally AND flag the submitted PR
- G70. Reconcile a recipe's OWN `run_constraints` to upstream's real extra pins — it's soft (metadata-only, lint-verified), so it's a safe high-value faithfulness pass
- G71. A dependency's event-loop reactor needs libev (Unix-only) or asyncore (removed in py3.12) — on win+py3.12+ `import <pkg>.cluster` raises, failing a noarch consumer's CFEP-25 `*` test (win-only)
- G72. Fold a same-monorepo sibling into a multi-output suite (per-output version + `pin_subpackage`) to dissolve a cross-feedstock submission gate
- G73. A noarch app built from a GitHub monorepo TAG ships NONE of the release-time-generated frontend/web assets (wheel-only) — and `import`/`pip_check` can't catch it (a G51 trap for apps with a UI)
- G74. "Is X on conda-forge?" — the offline atlas can be STALE for recently-created feedstocks; cross-check live `channeldata.json` before any membership-driven destructive edit
- G75. A lean staged-recipes SUBMISSION copy may go BEYOND the default cfe-strip — remove ALL comments + filter optional run_constraints to on-cf-only; branch off conda-forge MAIN, push to your fork, no PR
- G76. A Unix-only dependency in a `noarch: python` recipe CANNOT be a hard dep — `noarch` bakes `depends` at build time, so the package becomes unsolvable on Windows; make it OPTIONAL (strip from the wheel + `run_constraints`)
- G77. A TRANSITIVE dep whose conda feedstock dropped a win-only wheel marker breaks `pip check` on Windows — you can't fix it in your noarch recipe; exclude win via `conda-forge.yml noarch_platforms`, or fix the upstream feedstock
- G78. `cfe-submission-pr` / `cfe-on-conda-forge-status` are LOCAL hints that go STALE — answer "is X on staged-recipes / conda-forge?" from LIVE signals, never the cfe fields
- G79. `go-licenses save` fatals on a package's OWN non-OSI / non-standard license — pass `--ignore <module-path>` and ship the LICENSE separately
- G80. A waived external-feedstock metadata bug is often fixed by a same-version REBUILD — re-check the latest BUILD (build number), not the latest VERSION
- G81. conda-forge ships pnpm 11, which no longer reads `package.json`'s `pnpm` field — a lockfile made under pnpm <11 fails `--frozen-lockfile` with `ERR_PNPM_LOCKFILE_CONFIG_MISMATCH`; pin `pnpm <11`
- G82. staged-recipes CANNOT build osx-arm64 (or any arm/aarch64) pre-merge — it's local-only (on a Mac) before merge, opt-in on the feedstock after
- G83. A staged-recipes per-recipe `conda-forge.yml` is almost entirely INERT during the PR build — `build_all.py` reads ONLY `conda_build_tool`; every other key just SEEDS the post-merge feedstock
- G84. `migrate_to_v1` / `feedrattler` is a REMOTE-feedstock tool — it CANNOT convert a local `recipes/<name>/` directory
- G85. A native `trigger_build` reports "No build summary found — build may have crashed" even on SUCCESS — confirm from the `.conda` artifact + `rattler-build test --package-file`
- G86. Omit `bot.run_deps_from_wheel` when the recipe PATCHES the wheel's dependency metadata — the bot would regenerate run deps from the wheel and DROP your hand-managed dep
- G87. v0→v1 FEEDSTOCK migration: verify the feedstock's CURRENT version FIRST (the local mirror can be stale → a silent downgrade), then bump build.number, rerender, and drop `conda_build.error_overlinking`
- G88. Shared protobuf-namespace stubs (`buf.validate`, generated `<ns>/`) collide across a closure — one owner at the newest superset version; strip from siblings (often NOT cf-submittable)
- G89. Stale red autotick PRs with Azure-pruned runs are UNRESTARTABLE — `restart ci` is a silent no-op; kick fresh CI with `please rerender` (which can disable bot-automerge)
- G90. Freshly-GENERATED recipes need a sanitize/verify pass before building — five verified generator emission gaps (including NO cfe block)
- G92. Any YAML re-serialization FOLDS the `#### CFE` comment block into plain inline keys — a subsequent stamp append then DUPLICATES them (parse-fatal); strip BOTH forms before stamping
- G93. conda-recipe-manager CRASHES on column-0 comments inside indented blocks — conda-smithy lint calls the recipe unparseable while rattler-build builds it fine; col-0 comments are safe ONLY at the document tail
- G94. Local mirror dirs accumulate STALE feedstock files that fail local gates — prune against the LIVE feedstock on every refresh
- G95. `build-clean-test-blocked` means metadata-UNVERIFIED — a recipe whose local test env never solved has an unexercised import list and pip check; statically verify both before shipping it anywhere
- G96. When BUMPING an existing feedstock, the dep authority is the previous feedstock recipe + an upstream `requires_dist` diff — NEVER the regenerated recipe alone
- G97. An unsolvable env can be a C-ABI ERA DIAMOND between ecosystem pin epochs — diagnose at the repodata level (libabseil/libgrpc/libarrow pins), don't debug the recipe
- G99. Fixture-scale tests hide O(n²) VALIDATOR behavior — jsonschema's `uniqueItems` makes universe-scale CycloneDX validation intractable; strip + exact O(n) hash check + chunked parallel walk
- G100. npm CLIs are per-arch recipes (openspec/bmalph pattern) — noarch + bash-wrapper + `__unix` cannot serve Windows and fights the symlink check
- G101. npm dists that are shims over per-platform Bun static binaries — detect via `optionalDependencies`; the native may segfault and CANNOT be built from source
- G102. The staged-recipes win-64 leg builds noarch recipes too — a unix-only build script renders EMPTY on Windows and dies as "No license files were copied"
- G103. Don't copy npm `engines` version caps into conda run deps — the host nodejs run-export makes the combined constraint unsolvable
- G104. Strict channel priority: ANY stale local-channel package shadows every conda-forge version of that name
- G105. rattler-build python tests run `pip check` BY DEFAULT — an omitted `pip_check:` means true, and the repo convention is explicit true + dual `python_version`
- G106. A build-hook SKIP env var does NOT stop `hatch-build-scripts` from DELETING the hook's prebuilt artifacts first — `clean_artifacts` defaults to true, so skipping silently ships an incomplete package
- G107. A conda package EXISTING under the bare name does not mean it ships the Python module — the name may belong to a different artifact entirely, and the env solves green while `import` fails
- G108. Autotick's internal `recipe_editor.py` subprocess call must resolve the interpreter the same way as its sibling — a bare `"python"` argv0 breaks on any environment without a `python` alias
- G109. Upstream can renumber PAST your dev-snapshot version — a `X.Y.Z.dev0` recipe waiting for tag `X.Y.Z` may be waiting for a version that will never exist
- G110. An npm package can publish a bin entry EMPTY in one release and real in the next — re-read the `bin` map on every version bump, and smoke-test every bin you ship

=== Skill Forge tooling note ===
forge-tier.yaml did not exist in this worktree at brief time (per-worktree
gitignored state, .gitignore:805 -- consistent with Story 12.3's finding for
a prior worktree); it was generated fresh via the real skf-detect-tools.py /
skf-forge-tier-rw.py scripts for this run (tier: Quick -- no ast-grep/qmd/ccc,
same result Story 12.3 found). Whichever worktree runs Story 12.7's compile +
real skf-audit-skill pass will need the same skf-setup step re-run there from
scratch, exactly as Story 12.3 and this story both had to.
