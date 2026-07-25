---
stepsCompleted:
  - step-01-init
  - step-02-scope
  - step-03-seam-options
  - step-04-packaging
  - step-05-portability
  - step-06-net-new-capabilities
  - step-07-recommendation
inputDocuments:
  - ".claude/skills/conda-forge-expert/scripts/ (66 files, measured)"
  - ".claude/scripts/conda-forge-expert/ (57 wrappers, measured)"
  - ".claude/tools/conda_forge_server.py (2,266 LOC, 46 tools)"
  - "pixi.toml (root workspace)"
  - "src/shared/packages/pyforge-warden/{pyproject.toml,pixi.toml,src/pyforge/warden/cli.py}"
  - "src/shared/packages/pyforge-atlas/pyproject.toml"
  - "_bmad-output/projects/pyforge-mason/planning-artifacts/research/domain-packaging-automation-tooling-research-2026-07-25.md"
workflowType: 'research'
lastStep: 7
research_type: 'technical'
research_topic: 'The mason CLI seam — packaging a product CLI over the conda-forge-expert machinery'
research_goals: 'Determine the technically viable seam between a packaged `mason` CLI and the existing CFE script tiers; establish the packaging shape; surface the portability blockers; scope the net-new capabilities'
user_name: 'Rxm7706'
date: '2026-07-25'
web_research_enabled: true
source_verification: true
project: pyforge-mason
---

# Research Report: The Mason CLI Seam (technical)

**Date:** 2026-07-25
**Author:** Rxm7706
**Research Type:** Technical feasibility
**Consumer:** `pyforge-mason` PRD (wrap-vs-build) → architecture

---

## Research Overview

**Question.** Can a packaged CLI — dist `pyforge-mason`, module `pyforge.mason`, entry point
`mason` — expose the existing conda-forge-expert capability without forking it, and what does that
seam physically look like? Plus: what does the net-new dual-ship / environment-lock work require?

**Method.** Direct measurement of the machinery on disk plus structural analysis of the two sibling
packages (`pyforge-warden`, `pyforge-atlas`) that already solved the "in-repo capability →
distributable conda+wheel package" problem in this workspace. Every claim below is checkable
against a named file. Web evidence for the external toolchain is carried in the companion domain
report; this report is about *this repository's* mechanics.

---

## Part 1 — The Seam: subprocess-delegation vs import-based adapters

### The candidate approaches

| | **S — subprocess delegation** | **I — import-based adapters** |
|---|---|---|
| Shape | `mason` shells `[sys.executable, <cfe script>, *args]`, parses stdout | `mason` imports CFE modules and calls their functions |
| Precedent | 57 wrappers + 46 MCP tools + ~105 pixi tasks | **none in this repo** |
| Coupling to CFE internals | argv + stdout contract | Python function signatures |

### Five findings that decide it

**F1 — Five of the modules are physically unimportable.** `recipe-generator.py` (2,653 LOC),
`dependency-checker.py` (658), `license-checker.py` (347), `feedstock-migrator.py` (301), and
`test-skill.py` carry **hyphens in the filename**. A hyphen is not a legal Python identifier, so
`import recipe_generator` cannot resolve and `from recipe-generator import ...` is a syntax error.
The only route is `importlib.util.spec_from_file_location`, i.e. hand-rolled loading by path — which
is subprocess's problem (locate a file on disk) with none of subprocess's isolation. And
`recipe-generator.py` is **the single most important module for `mason recipe`**. Renaming them is
not available to this project: the CFE tree is governed by `spec-packaging-factory` under
`scripts/spec_surface_check.py` with a CHANGELOG sentinel, and CLAUDE.md Rule 1 makes the skill
authoritative over any story that would edit it.

**F2 — Import makes the path problem strictly worse.** Thirteen files define their own copy of

```python
def _get_data_dir() -> Path:
    return Path(__file__).parent.parent.parent.parent / "data" / "conda-forge-expert"
```

resolving relative to **the importing module's own file location**. A script executed in place
resolves this correctly. The same module imported into a `mason` process still resolves against its
own `__file__` — so it works if and only if the file still sits inside `.claude/skills/...`, which
means import buys *zero* portability over subprocess while adding in-process global state. There is
**no environment-variable override for the data directory anywhere in the 66 files**.

**F3 — The repo-root anchor is not consistent, so there is no single import-time contract.**
`parents[4]` is the repo root in `submit_pr.py:34`, `my_feedstocks.py:33`, `env_inspect.py:75`,
`gen_yml_reference.py:30`, `export_purls.py:63`; but `parents[3]` (`.claude/`) is *named* `repo_root`
in `recipe_optimizer.py:234` and `local_builder.py:160`; `bootstrap_data.py:134` uses `parents[5]`
(above the repo). `feedstock_lookup.py:28` and `feedstock_context.py:30` resolve to
`.claude/skills/data/conda-forge-expert` — a directory **different from every other script's**.
An import-based adapter would have to encode, per module, which of four incompatible conventions
applies. (This is worth recording as an upstream CFE defect regardless of mason's decision — see
`open_questions[]` OQ-T5.)

**F4 — Process isolation is load-bearing here.** The canonical tier runs long network fanouts
(atlas phases with concurrency knobs), holds SQLite handles against `cf_atlas.db`, and reads 55+
environment variables including credential material (`GITHUB_TOKEN`, `JFROG_API_KEY`,
`JFROG_PASSWORD`). It also has a documented history of hangs (`project_phase_k_hang_on_admin_runs`
— fixed with a watchdog *inside* the script). In-process import means a CFE hang is a `mason` hang
with no timeout available; subprocess means `timeout=` and a clean kill. Note also that
`_http.py`'s JFrog key injection is known-unconditional (`project_http_jfrog_unconditional_injection`)
— importing it into mason's process would extend that blast radius to every HTTP call mason
itself makes.

**F5 — The subprocess contract is already the public one, and its cost is already measured.**
`conda_forge_server.py` imports **zero** canonical scripts. It holds 41 module-level
`SCRIPTS_DIR / "<name>.py"` constants and one helper, `_run_script(script_path, args,
input_text=None, timeout=120)` at line 83, calling `subprocess.run([_PYTHON, str(script_path),
*args])`. 46 MCP tools go through it. The cost is visible and bounded: a single tolerance shim,
`_extract_json_from_stdout()` (line ~53), that re-parses stdout when a script emits a progress line
before its JSON body — needed today for `submit_pr` / `prepare_submission_branch`.

### Verdict — Part 1

**Subprocess delegation (S) is the only viable seam, and it is not a compromise** — it is the
contract every existing consumer already uses. Import-based adaptation is blocked outright for
5 modules, buys no portability, and would require edits to a governed surface this project is
forbidden to touch.

**What mason must add on top of it** (the shim in the MCP server is the warning):

- **One adapter module**, `pyforge.mason.cfe`, owning: script-path resolution, invocation,
  timeout, and a typed `CfeResult(returncode, stdout, stderr, json: dict | None)`.
- **A tolerant JSON extractor**, ported in behaviour (not copied by import) from
  `_extract_json_from_stdout` — because mason inherits exactly the same stdout-purity problem.
- **A structured "CFE unavailable" error**, not a traceback — because the majority of mason's
  surface must work without CFE present (Part 4).

---

## Part 2 — Packaging shape

The workspace has solved this twice; the shape is settled and mason should mirror it exactly rather
than invent.

**The member package layout** (`pyforge-warden` / `pyforge-atlas`, identical):

```
src/shared/packages/pyforge-mason/
  pyproject.toml      # hatchling backend; [project.scripts] mason = "pyforge.mason.cli:main"
                      # [tool.hatch.build.targets.wheel] packages = ["src/pyforge"]
  pixi.toml           # [package] + [package.build.backend] pixi-build-python 0.*
                      #  — deliberately NO [workspace] table (the root owns that)
  src/pyforge/mason/  # PEP-420 namespace: NO src/pyforge/__init__.py
  tests/
  README.md
```

**Root wiring** (`pixi.toml`): a `[feature.pyforge-mason.dependencies]` table with
`pyforge-mason = { path = "src/shared/packages/pyforge-mason" }`, plus a lean environment
`pyforge-mason = { features = ["pyforge-mason"], no-default-feature = true }`. Note the root's
own comment records that **pixi has no `[workspace] members` key** through 0.72.2 — membership is
expressed via path dependencies. `preview = ["pixi-build"]` is already enabled at line 6.

**The build triad** (both siblings, identical):

| Task | Command | Produces |
|---|---|---|
| `pyforge-mason-build-conda` | `pixi build --output-dir dist-conda` (cwd = member) | `.conda` |
| `pyforge-mason-build-dist` | `python -m build --no-isolation --outdir dist` | wheel + sdist |
| `pyforge-mason-build` | `depends-on = [both]` | both |

**One `pyproject.toml` drives both artifacts** — `pixi-build-python` wraps the same hatchling wheel
that `python -m build` produces. This is directly relevant to mason's own `--ship pypi,conda-forge`
verb: **the repo already dogfoods the exact dual-artifact motion mason proposes to productize**,
which is strong evidence the capability is real and a natural first test case.

**CLI framework: `argparse`.** Not a close call. `pyforge.warden.cli` is argparse; all 60 CLI
scripts in the CFE tier are argparse; neither sibling `pyproject.toml` carries click or typer.
Adding one would violate the workspace's explicit **lean-dep doctrine** (warden's pyproject:
"lean, targeted dependency set… pure-stdlib as fallback"). `mason recipe build` nests natively via
sub-subparsers. Cost: help-text ergonomics are worse than typer's; accepted.

**Python floor: unresolved.** Warden is `>=3.12`, atlas is `>=3.14` (recorded as "BY DESIGN — do
not fix"). Mason shells out to CFE scripts, which run under whatever interpreter the pixi env
provides, so mason's own floor is genuinely free. Recommendation: **`>=3.12`**, matching warden, the
package mason is most likely to sit beside in a user environment. Recorded as OQ-T1.

**Dependency posture.** Mirror warden: mason's *engines* (rattler-build, grayskull, conda-lock,
`build`, `twine`) are **conda run-dependencies in the member `pixi.toml`, never runtime-fetched**;
the wheel's `dependencies` list stays lean. Warden also ships
`tests/meta/test_engine_version_range_sync.py`, enforcing that range pins in `pixi.toml` match
in-code version constants — **a directly transferable pattern** mason should adopt for whichever
engines it pins.

**Cross-package edges.** Atlas's `[project.optional-dependencies] gate = ["pyforge-warden"]`
(AC-8) is the established pattern for an optional dependency on a sibling: default-installed
in-repo at the pixi *feature* level, optional for external installs. If mason ever needs warden
(e.g. scanning a package it is about to ship), that is the mechanism — an extra, not a hard dep.

---

## Part 3 — The portability problem (the highest-risk unknown)

**Statement.** An installed `mason` lives in `site-packages`. The CFE scripts live in
`<some repo>/.claude/skills/conda-forge-expert/scripts/`. Nothing connects them. Additionally
**`recipes/` is hardcoded in 17 canonical scripts** — the CFE tier assumes it is running inside
*this* repository.

This is the single variable that most affects mason's scope, and it is unresolved (domain report
OQ-4). Three deployment targets, three different answers:

| Target | Does the seam work? | What it needs |
|---|---|---|
| **T1 — inside this repo** (replaces/parallels the pixi tasks) | Yes, today | Resolve `.claude/` by walking up from cwd |
| **T2 — another repo with its own `.claude/`** | Mostly | Same walk-up; `recipes/` assumption may break |
| **T3 — arbitrary CI / no `.claude/` at all** | **No** | Mason would have to *vendor* or *reimplement* CFE — i.e. Option B by the back door |

**Proposed resolution chain** (mirrors `_http.py`'s existing env-var-chain philosophy, so it is
idiomatic to this codebase):

1. `--cfe-root <path>` explicit flag (highest)
2. `MASON_CFE_ROOT` environment variable
3. Walk up from `cwd` for a directory containing `.claude/scripts/conda-forge-expert/`
4. Not found → **structured degradation**, not a crash

**The critical design consequence.** Because T3 is a real possibility and step 4 is reachable in
T1/T2 too, mason must be architected so that **CFE availability is a per-command property, not a
process-wide prerequisite**:

- `mason recipe *` → **requires** CFE. Absent → clear, actionable error naming the resolution chain.
- `mason package *`, `mason environment *` → **must not require** CFE (Part 4 shows they have no
  CFE counterpart to call anyway).

That split is the architecture's load-bearing line and should be enforced by a test, not a comment.

---

## Part 4 — The net-new capabilities

Measured claim: **there is no wheel build, no PyPI upload, no twine/`uv publish` path, and no
lock-file orchestration anywhere in the 41,410 LOC of the canonical tier.** `submit_pr.py` (404 LOC)
targets conda-forge/staged-recipes exclusively. So two of mason's three charter verb families are
genuinely net-new code, not wrapping.

### 4a — `mason package --ship pypi,conda-forge`

**The asymmetry finding (important for the PRD).** These two targets are not the same kind of
operation:

| | PyPI | conda-forge |
|---|---|---|
| Mechanism | HTTPS upload of a built wheel | **git PR into `staged-recipes`** |
| Latency | seconds | days–weeks (human review queue) |
| Terminal state on success | package is live | *a PR is open* |
| Reversible | no (yank only) | yes (close PR) |
| Auth | API token / OIDC trusted publishing | GitHub credentials |

`--ship pypi,conda-forge` therefore **cannot be a single synchronous transaction**. The honest
model is: `pypi` completes; `conda-forge` *initiates* and returns a PR reference. A "ship both"
verb that reports success when one half is merely queued is a correctness bug waiting to happen.
The PRD must specify the reporting contract. (Third possibility for the conda half — direct upload
to a non-conda-forge channel, e.g. `pixi publish --target-channel` or `anaconda upload` — is
synchronous and is what an enterprise/private-channel user would want; see OQ-T3.)

Reusable pieces already present: `python -m build --no-isolation` (both siblings' `-build-dist`
task); `pixi build` via `pixi-build-python` (both siblings' `-build-conda` task);
`prepare_pr.py`/`submit_pr.py` for the conda-forge PR half; `pixi publish` for the channel half.
**Mason's net-new code here is orchestration, credential handling, and the asymmetric reporting
model — not building.**

### 4b — `mason environment lock`

The domain report's negative finding applies: conda-lock (conda + pip via a vendored Poetry solver)
and `pixi.lock` both already exist and are maintained. Mason should wrap. The net-new value is
policy and orchestration — which manifests to feed, which platforms, gate integration. Technically
this is the *smallest* of the three verb families and should be scoped accordingly; the risk is
scope inflation into re-solving, which must be an explicit non-goal.

### 4c — MCP surface

`conda_forge_server.py` already exposes 46 tools. **Mason must not ship a second server duplicating
them** — that is the atlas dual-implementation failure mode in miniature. Two defensible options:
(a) mason ships no MCP server in v1 and the existing server stands; (b) mason ships a *small*
server exposing only its net-new verbs (`package`, `environment`). Recommend (a) for v1, (b) as a
later epic. Note `fastmcp >=3.4.4` is already a root conda dep, so (b) costs no new dependency when
it comes.

---

## Part 5 — Recommendation

**Adopt the seam by capability, not by product.**

1. **Wrap, via subprocess, everything CFE already does** (`mason recipe *`). One adapter module,
   `pyforge.mason.cfe`, is the *only* place in mason that knows CFE exists. Zero recipe semantics
   are re-implemented — mason holds no gotcha, no constraint, no pin rule. This satisfies CLAUDE.md
   Rule 1 by construction and keeps the Rule-2 retro loop's output automatically live in mason.
2. **Build, natively, what has no CFE counterpart** (`mason package *`, `mason environment *`) —
   orchestrating existing engines (`build`, `twine`/`uv`, `pixi build`, conda-lock), never
   re-solving or re-building.
3. **Package as a workspace member**, mirroring warden/atlas exactly: hatchling + `pixi-build-python`,
   PEP-420 `src/pyforge/mason/`, argparse CLI, lean deps, engines as conda run-deps, build triad.
4. **Enforce the seam with a test.** The failure mode this repo has already demonstrated (atlas:
   ~29k LOC of rebuild, legacy still live, two implementations) is not prevented by intent. Mason
   needs a meta-test asserting that `pyforge.mason` contains no recipe-domain knowledge — e.g. no
   gotcha IDs, no pin tables, no conda-forge policy constants — and that every recipe operation
   routes through `pyforge.mason.cfe`. **This is the single most valuable test in the product.**

**Why not full rebuild (Option B):** it forks 41,410 LOC whose contract is mutated by a *mandatory*
retro loop (Rule 2), against an authoritative source (Rule 1) this project may not edit, reproducing
the atlas outcome. **Why not pure-porcelain-only:** two of three charter verb families have nothing
to wrap; a strict wrapper cannot deliver the product's stated differentiator (dual-ship).

---

## assumptions[]

1. **A-T1** — Mason may not modify the CFE surface (governed by `spec-packaging-factory` + Rule 1);
   confirmed by the task brief. If that were relaxed, F1/F2/F3 change materially — fixing the
   5 filenames + adding a `CFE_DATA_DIR` env var would make import viable. **Not recommended
   regardless**, since F4/F5 stand independently.
2. **A-T2** — `sys.executable` in the mason process is an interpreter that can run the CFE scripts
   (i.e. the CFE dependency floor — `pyyaml`, `requests`, `packaging`, `truststore`, `ruamel.yaml`,
   `conda-forge-metadata` — is importable there). True inside a pixi env; **false** for a lean
   `no-default-feature` mason env. Mason may need `--cfe-python` or to locate the CFE-capable
   interpreter, not just the scripts. Flagged as a design item.
3. **A-T3** — CFE script stdout is stable enough to parse. Evidenced by 46 MCP tools doing it for
   an extended period, with one known tolerance shim. Not a formal contract; mason inherits the risk.
4. **A-T4** — pixi's `preview = ["pixi-build"]` remains available and its member-package semantics
   stay stable. It is documented as preview software.
5. **A-T5** — The workspace convention (argparse, hatchling, lean deps, build triad) is intended to
   be normative for new members. Inferred from two independent instances plus explicit comments,
   not from a written standard.

## open_questions[]

1. **OQ-T1** — Python floor: 3.12 (warden) or 3.14 (atlas)? Recommend 3.12; needs a decision.
2. **OQ-T2** — Does mason **replace** the ~105 CFE pixi tasks over time, or coexist indefinitely?
   Atlas never answered this and now runs two implementations. Must be answered in the PRD.
3. **OQ-T3** — Does `--ship conda-forge` mean "open a staged-recipes PR" (asynchronous, human-gated)
   or "upload to a conda channel" (synchronous)? These are different features. Possibly both, with
   distinct target names.
4. **OQ-T4** — Credential model for `--ship pypi`: API token, OIDC trusted publishing, or
   artifact-only (build, don't upload)? Drives the security posture.
5. **OQ-T5** — The CFE path inconsistencies (13 duplicated `_get_data_dir()`, `parents[3/4/5]`
   divergence, two scripts resolving to `.claude/skills/data/…`) look like genuine upstream defects.
   Should mason's effort file a CFE finding, or is that out of scope? Note Rule 2 would route it
   through a CFE retro, not a mason story.
6. **OQ-T6** — Interpreter resolution (A-T2): does mason ship in the fat `local-recipes` env, a lean
   env, or both? Determines whether `--cfe-python` is needed in v1.
7. **OQ-T7** — Does mason expose an MCP surface in v1? Recommendation is no (defer); needs
   confirmation since "agent-native" is one of the product's four differentiators.
8. **OQ-T8** — Is there an expectation that `mason` works in a repo **without** `.claude/` (target
   T3)? If yes, the wrap recommendation is materially weakened and vendoring must be re-evaluated.

---

## Sources

Local, all under the `pyforge-mason` worktree, measured 2026-07-25:

- `.claude/skills/conda-forge-expert/scripts/` — 66 `.py`, 41,410 LOC (file/line counts, import
  graph, `Path(__file__)` and `_get_data_dir()` occurrences)
- `.claude/scripts/conda-forge-expert/` — 57 wrappers, 867 LOC; `README.md` (tier contract)
- `.claude/tools/conda_forge_server.py` — 2,266 LOC; `_run_script` (line 83),
  `_extract_json_from_stdout` (line ~53), 46 `@mcp.tool`
- `pixi.toml` — lines 4–9 (`[workspace]`, `preview`), 142–147 (lean envs), 1041–1113
  (`[feature.pyforge-warden.*]`, `[feature.pyforge-atlas.*]`)
- `src/shared/packages/pyforge-warden/pyproject.toml`, `pixi.toml`, `src/pyforge/warden/cli.py`
- `src/shared/packages/pyforge-atlas/pyproject.toml`
- `CLAUDE.md` — Rules 1 & 2; the 3-tier CFE layout
- Companion: `research/domain-packaging-automation-tooling-research-2026-07-25.md`
