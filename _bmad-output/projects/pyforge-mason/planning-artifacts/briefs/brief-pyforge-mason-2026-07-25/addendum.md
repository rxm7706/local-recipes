---
title: "Addendum: Mason (pyforge-mason) product brief"
status: draft
created: 2026-07-25
updated: 2026-07-25
project: pyforge-mason
parent: brief.md
---

# Addendum — Mason

Depth that belongs downstream (PRD / architecture) or earned a place but did not fit the brief.

## 1. The wrap-vs-build options matrix (rejected-alternative rationale)

The PRD's central question. Three options were considered; the brief states the outcome, this is
the working.

### Option A — pure porcelain (wrap only)

`mason` is a product CLI over the existing CFE scripts and MCP surface. The skill stays canonical.

| | |
|---|---|
| **Size** | Small — an adapter, a CLI, packaging |
| **Recipe knowledge** | Zero duplicated; Rule-2 retro updates land automatically |
| **Rule 1/2 compliance** | By construction |
| **Distribution** | Installable, but **inert without CFE present** |
| **Fatal flaw** | Cannot deliver `--ship pypi` or `environment lock` — **there is nothing to wrap.** No wheel build, no upload path, no lock orchestration exists anywhere in the 41,410 LOC. A pure wrapper cannot deliver the product's stated differentiator. |

### Option B — extract / re-implement as a standalone library

`pyforge.mason` becomes self-contained: recipe generation, validation, build orchestration, failure
analysis, submission, all re-implemented as importable library code.

| | |
|---|---|
| **Size** | Very large — 41,410 LOC of canonical script behaviour |
| **Recipe knowledge** | Forked. 106 gotchas + 10 constraints must be re-earned and then kept in sync |
| **Rule 1/2 compliance** | **Structurally adversarial.** Rule 1 makes SKILL.md authoritative over any conflicting story; Rule 2 mandates that every conda-forge effort *edits the skill*. A fork is invalidated by the governance loop that owns the domain. |
| **Distribution** | Genuinely standalone — the one real advantage |
| **Precedent** | `pyforge-atlas` chose this: 80 files / 14,461 src LOC + 110 files / 14,682 test LOC, 32 stories, PRs #58–#105 all merged. **The legacy `conda_forge_atlas.py` (8,902 LOC) is still the live runtime** — every `build-cf-atlas` / `atlas-phase` / `query-cf-atlas` task and every atlas MCP tool still shells out to the old path. Nothing routes to `pyforge.atlas`. ~29k LOC of committed work did not displace the original. |
| **Contrast** | `pyforge-warden` also built — but from nothing (no legacy counterpart), and shipped 31/31, merged. **Warden built because there was nothing to wrap. Atlas built despite there being something to wrap, and now pays dual-maintenance.** Mason is in atlas's position. |

### Option C — seam by capability (**selected**)

Wrap where knowledge exists and churns; build where nothing exists.

- `mason recipe *` → subprocess-delegate to CFE through one adapter (`pyforge.mason.cfe`)
- `mason package *`, `mason environment *` → native orchestration of established engines
- The boundary is enforced by a meta-test, not by intent

This is not a compromise between A and B; it is the recognition that A and B answer a question the
product does not actually pose. The charter's three verb families have *different* incumbent
situations, so a single global answer is wrong for two of them.

## 2. Why import-based adaptation was ruled out (technical constraints)

Five findings, each independently sufficient. Full detail in
`research/technical-mason-cli-seam-research-2026-07-25.md` Part 1.

1. **Five modules are physically unimportable** — hyphens in the filename
   (`recipe-generator.py` at 2,653 LOC is the most important module for `mason recipe`;
   also `dependency-checker.py`, `license-checker.py`, `feedstock-migrator.py`, `test-skill.py`).
   Only route is `importlib.util.spec_from_file_location` — subprocess's problem without
   subprocess's isolation. Renaming is unavailable: the tree is governed by
   `spec-packaging-factory` with a CHANGELOG sentinel.
2. **Import worsens the path problem.** `_get_data_dir()` is duplicated in 13 files and resolves
   `Path(__file__).parent×4 / "data" / "conda-forge-expert"` against the *importing module's* own
   location — correct in place, meaningless from `site-packages`. No env-var override exists
   anywhere in the 66 files.
3. **No single import-time contract exists.** Repo-root anchor is `parents[4]` in five scripts,
   `parents[3]` in two (where it is *named* `repo_root`), `parents[5]` in one; and
   `feedstock_lookup.py` / `feedstock_context.py` resolve to `.claude/skills/data/conda-forge-expert`
   — a directory different from every other script's.
4. **Process isolation is load-bearing.** Long network fanouts, SQLite handles, 55+ env vars
   including `GITHUB_TOKEN` / `JFROG_API_KEY` / `JFROG_PASSWORD`, and a documented hang history
   (Phase K, fixed with an in-script watchdog). Subprocess gives `timeout=` and a clean kill.
   Separately: `_http.py`'s JFrog key injection is known-unconditional — importing it would extend
   that credential blast radius to every HTTP call Mason itself makes.
5. **Subprocess is already the public contract.** 57 wrappers, ~105 pixi tasks, and 46 MCP tools
   all speak it. `conda_forge_server.py` imports zero canonical scripts; it holds 41 path constants
   and one `_run_script(script, args, input_text=None, timeout=120)` helper. Mason adopting it costs
   nothing not already being paid.

**The measured cost Mason inherits:** `_extract_json_from_stdout()` in the MCP server — a tolerance
shim that re-parses stdout when a script emits a progress line before its JSON body (needed for
`submit_pr` / `prepare_submission_branch`). Mason needs the same behaviour, ported not imported.

## 3. Packaging shape (settled by precedent, for the architecture doc)

```
src/shared/packages/pyforge-mason/
  pyproject.toml      # hatchling; [project.scripts] mason = "pyforge.mason.cli:main"
                      # [tool.hatch.build.targets.wheel] packages = ["src/pyforge"]
  pixi.toml           # [package] + [package.build.backend] pixi-build-python 0.*
                      #   deliberately NO [workspace] table — the root owns that
  src/pyforge/mason/  # PEP-420 namespace; NO src/pyforge/__init__.py
  tests/
```

Root wiring: `[feature.pyforge-mason.dependencies] pyforge-mason = { path = "..." }` plus a lean
`pyforge-mason = { features = ["pyforge-mason"], no-default-feature = true }` environment. pixi has
**no `[workspace] members` key** through 0.72.2 (the root `pixi.toml` records this explicitly) —
membership is path dependencies. `preview = ["pixi-build"]` is already enabled at root line 6.

Build triad, identical in both siblings:

| Task | Command | Produces |
|---|---|---|
| `pyforge-mason-build-conda` | `pixi build --output-dir dist-conda` (cwd = member) | `.conda` |
| `pyforge-mason-build-dist` | `python -m build --no-isolation --outdir dist` | wheel + sdist |
| `pyforge-mason-build` | `depends-on = [both]` | both |

**Note for the PRD:** one `pyproject.toml` drives both artifacts. The repo therefore already
dogfoods, by hand, the exact dual-artifact motion Mason proposes to productize — making Mason's own
release the natural first test case for `mason package --ship`.

**Transferable pattern:** warden ships `tests/meta/test_engine_version_range_sync.py`, enforcing
that range pins in `pixi.toml` match in-code version constants. Mason should adopt it for whichever
engines it pins (rattler-build, grayskull, conda-lock, `build`, `twine`).

**Cross-package edges:** atlas's `[project.optional-dependencies] gate = ["pyforge-warden"]` (AC-8)
is the established mechanism — default-installed in-repo at the pixi *feature* level, optional for
external installs. If Mason ever needs Warden (e.g. scanning a package before shipping it), that is
the route: an extra, not a hard dependency.

## 4. The CFE discovery chain (architecture input)

An installed `mason` lives in `site-packages`; CFE lives in
`<repo>/.claude/skills/conda-forge-expert/scripts/`. Nothing connects them, and `recipes/` is
hardcoded in 17 canonical scripts.

Proposed chain (mirrors `_http.py`'s existing env-var-chain idiom, so it is native to this codebase):

1. `--cfe-root <path>` (explicit, highest)
2. `MASON_CFE_ROOT` environment variable
3. Walk up from cwd for a directory containing `.claude/scripts/conda-forge-expert/`
4. Not found → structured degradation, never a traceback

Three deployment targets, three answers:

| Target | Works? | Needs |
|---|---|---|
| T1 — inside this repo | Yes, today | walk-up |
| T2 — another repo with its own `.claude/` | Mostly | walk-up; `recipes/` assumption may break |
| T3 — arbitrary CI, no `.claude/` | **No** | vendoring or reimplementation — Option B by the back door |

**Consequence:** CFE availability must be a *per-command* property, not a process-wide prerequisite.
`mason recipe *` requires CFE; `mason package *` and `mason environment *` must not. Enforce by test.

**Unresolved secondary:** even when the scripts are found, `sys.executable` must be an interpreter
that can *run* them (CFE's floor: `pyyaml`, `requests`, `packaging`, `truststore`, `ruamel.yaml`,
`conda-forge-metadata`). True in a fat pixi env, false in a lean `no-default-feature` one. Mason may
need `--cfe-python` in addition to `--cfe-root`.

## 5. Competitive detail (parked from the brief)

| Capability | grayskull | conda-smithy | autotick-bot | rattler-build/pixi | hatch/maturin | conda-lock | Mason |
|---|---|---|---|---|---|---|---|
| Generate conda recipe | ✅ v0 | ❌ | ❌ | partial | ❌ | ❌ | ✅ v1 |
| Validate against policy | ❌ | feedstock lint | ❌ | schema only | ❌ | ❌ | ✅ |
| Diagnose build failure | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Version-bump automation | ❌ | ❌ | ✅ cf-only | ❌ | `hatch version` | ❌ | ✅ any target |
| **Publish to PyPI** | ❌ | ❌ | ❌ | **❌** | ✅ | ❌ | ✅ |
| **One command → both** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |
| Cross-ecosystem lock | ❌ | ❌ | ❌ | pixi.lock | ❌ | ✅ | ✅ wraps |
| Usable outside conda-forge | ✅ | partial | **❌** | ✅ | ✅ | ✅ | ✅ |
| Agent surface | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

Key citations (full list in the domain report):
- autotick-bot is "exclusively designed for conda-forge and cannot be deployed elsewhere"
  ([regro/cf-scripts](https://github.com/regro/cf-scripts))
- `pixi publish` builds a `.conda` and uploads to a channel; the docs **do not address PyPI**
  ([pixi build docs](https://pixi.prefix.dev/latest/build/getting_started/))
- Hatch spans build/env/publish/version with **no mention of conda**
  ([Hatch](https://hatch.pypa.io/latest/)); maturin is PyPI-only and defers publishing to `uv publish`
  ([PyO3/maturin](https://github.com/PyO3/maturin))
- grayskull documents `meta.yaml` (v0) output only ([conda/grayskull](https://github.com/conda/grayskull))
- conda-lock locks `dependencies.pip` via a vendored Poetry solver
  ([conda/conda-lock](https://github.com/conda/conda-lock))

## 6. Parked / deferred

- **Multi-ecosystem autotick** (CRAN/npm/cargo updaters, `generate_recipe_from_{cran,cratesio,npm}`)
  — dream frontier; ownership disputed between Mason and Marshal/Steward (brief OQ-6).
- **Smart test extractor** — re-run recipe tests against an existing artifact without rebuilding.
  Dream frontier; high value for slow C++ packages.
- **Static dependency-version checker** — validate version *ranges*, not existence. Dream frontier.
- **Mason MCP server** — deferred. `fastmcp >= 3.4.4` is already a root conda dep, so it costs no
  new dependency when it arrives. v1 leaves the existing 46-tool server standing; a later epic may
  add a *small* server for Mason-only verbs. Duplicating the 46 tools is the atlas failure mode in
  miniature and is permanently out.
- **CFE upstream defects noticed during research** — duplicated `_get_data_dir()` ×13, the
  `parents[3/4/5]` divergence, the two scripts resolving to `.claude/skills/data/…`, and the
  unconditional JFrog header injection. These are genuine findings but belong to a CFE Rule-2 retro,
  not a Mason story. Recorded here so they are not lost.
