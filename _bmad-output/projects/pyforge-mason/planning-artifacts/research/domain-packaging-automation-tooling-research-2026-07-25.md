---
stepsCompleted:
  - step-01-init
  - step-02-scope
  - step-03-landscape
  - step-04-incumbent-analysis
  - step-05-gap-analysis
  - step-06-differentiation
  - step-07-synthesis
inputDocuments:
  - "docs/dreams/packaging-factory.md"
  - "docs/dreams/ecosystem-crew.md (§ 5 Mason)"
  - "_bmad-output/projects/local-recipes/planning-artifacts/specs/spec-packaging-factory/SPEC.md"
  - ".claude/skills/conda-forge-expert/SKILL.md (v8.79.1)"
  - "pixi.toml"
workflowType: 'research'
lastStep: 7
research_type: 'domain'
research_topic: 'Packaging-automation tooling for dual-ecosystem (conda-forge + PyPI) Python distribution'
research_goals: 'Establish the incumbent landscape, locate the unserved gap, and ground the wrap-vs-build decision for the Mason product PRD'
user_name: 'Rxm7706'
date: '2026-07-25'
web_research_enabled: true
source_verification: true
project: pyforge-mason
---

# Research Report: Packaging-Automation Tooling (domain)

**Date:** 2026-07-25
**Author:** Rxm7706
**Research Type:** Domain / competitive landscape
**Consumer:** `pyforge-mason` product brief → PRD (wrap-vs-build decision)

---

## Research Overview

### Question

Mason is proposed as a packaging-station product — dist `pyforge-mason`, module `pyforge.mason`,
CLI `mason` — with three verb families drawn from the crew charter:

```bash
mason recipe build ./recipes/recipe.yaml
mason package --target library --ship pypi,conda-forge
mason environment lock --output conda-lock.txt
```

This report answers: **what already exists in this domain, what does it not do, and where does a
dual-ecosystem, AI-assisted packaging product actually differentiate?** The output is an input to
the PRD's central question (wrap the existing conda-forge-expert machinery vs. rebuild it as a
standalone library).

### Methodology

- **Primary-source review** of each incumbent's own documentation and repository README (cited
  inline; full list in § Sources). Vendor claims are reported as vendor claims.
- **Ground-truth inventory** of the local machinery (the `conda-forge-expert` skill, its script
  tiers, the MCP server, `pixi.toml`) measured directly on disk — see § Local Baseline. Numbers
  in that section are counted, not estimated.
- **Constraint:** this session's web-search budget was exhausted before the survey began, so the
  landscape was built by direct fetch of known primary URLs rather than open-ended discovery.
  This biases coverage toward incumbents already known to the author. See `open_questions[]` —
  a discovery sweep for unknown entrants is explicitly deferred, not claimed as done.

---

## The Domain in One Paragraph

Getting a piece of software to users in the Python world means crossing **two distribution
ecosystems that do not share a build model**. PyPI distributes wheels: per-project, per-author,
push-based, `pyproject.toml`-driven, published in seconds by the maintainer. conda-forge
distributes conda packages: centrally reviewed, pinning-coordinated, feedstock-per-package,
CI-built across a platform matrix, mediated by a volunteer review queue. The two have entirely
separate toolchains, separate metadata formats, separate dependency namespaces (PyPI
`ruamel.yaml` vs. conda `ruamel.yaml`; PyPI `tree_sitter` vs. conda `tree-sitter`), and separate
failure modes. **Every serious Python library eventually needs both, and no single tool spans
them.** The tooling that exists is excellent within its half and silent about the other.

---

## Incumbent Analysis

### 1. grayskull — the recipe skeleton generator

**What it is.** An automated conda recipe generator that extracts package metadata from a source
index and emits a starting recipe. Created explicitly "with the intention to eventually replace
`conda skeleton`." Supports PyPI (including GitHub-hosted Python projects), CRAN, local sdist
archives, and custom/mirrored indexes via `--pypi-mirror-url`. ([conda/grayskull][s1])

**Boundary.** Grayskull's own README documents output as `meta.yaml` — the v0 format — with no
mention of v1 `recipe.yaml` support. It declares no formal non-goals, but the README's forward
note that Conan and CPAN support is "future" places those out of scope today. ([conda/grayskull][s1])

**Where it stops.** Grayskull produces a *first draft*. It does not validate the draft against
conda-forge policy, does not build it, does not diagnose a build failure, does not know about
pinning migrations, and does not submit anything. In the conda-forge documentation's own framing
of the submission workflow, grayskull occupies exactly one cell of the "manual" column — recipe
generation — while "testing locally, license verification, PR submission" remain manual beside
it. ([conda-forge docs][s6])

**Read for Mason.** Grayskull is a *component*, not a competitor. Mason's `recipe` family
subsumes generation as step one of a longer loop. Notably, the local machinery already shells out
to grayskull via a dedicated `pixi run -e grayskull pypi <spec>` environment — the incumbent is
already a vendored dependency, not a thing to replace.

---

### 2. conda-smithy + the regro autotick-bot — the conda-forge operations layer

**conda-smithy** manages *feedstocks*: it "combine[s] a conda recipe with configurations to build
using freely hosted CI services into a single repository," generates and regenerates CI
configuration (the "rerender" operation), and initializes new feedstock repositories from an
existing recipe. Its unit of work is the feedstock — a package that has already been accepted.
([conda-forge/conda-smithy][s4])

**The autotick-bot** (`regro/cf-scripts`) is the ecosystem's maintenance robot: a set of parallel
cron jobs that build a dependency graph from feedstock metadata, fetch latest upstream versions,
compute migration specifications, and open PRs. It automates two classes of change — **version
updates** (detect release → fetch hashes for all source variants → bump) and **migrations** (ABI
migrations, new Python versions, compiler and pinning changes; CFEP-09 lets maintainers declare
YAML-based migrations without writing code). It parses recipes with ruamel + Jinja2 and is
selector-aware, and it only opens a PR when it has obtained new hashes for every variant.
([regro/cf-scripts][s3])

**Boundary — and this is the load-bearing one.** The bot "is **exclusively designed for
conda-forge** and cannot be deployed elsewhere — it depends on conda-forge's specific
infrastructure, the shared dependency graph, and the pinnings repository." Its documented
limitations: it does not modify recipe logic beyond version bumps, does not resolve complex
dependency conflicts, and does not function outside the conda-forge ecosystem.
([regro/cf-scripts][s3])

**Read for Mason.** The incumbent operations layer is **centrally operated, single-ecosystem, and
non-redeployable**. It serves conda-forge-the-institution. Nothing in it helps a maintainer who
wants the same automation for their own channel, their own fork, an air-gapped mirror, or a PyPI
release in the same motion. Mason's differentiation is not "a better autotick-bot" — it is *the
same class of automation, operable by an individual maintainer, across both ecosystems*.

---

### 3. The rattler-build / pixi ecosystem — the modern build substrate

**rattler-build** is a Rust reimplementation of the conda build step: "creates cross-platform
relocatable binaries / packages from a simple recipe format," positioned as "like conda-build but
faster," producing packages for the pixi/mamba/conda ecosystems without depending on conda-build
or Python. It consumes the v1 YAML recipe (context / package / source / build / requirements /
tests / about) and exposes two documented commands — `build` and `test` — plus a TUI for managing
multiple builds. It still shells out to platform tooling (`install_name_tool`, `patchelf`, `git`,
MSVC) and says it "plan[s] to reduce the number of external dependencies over time."
([prefix-dev/rattler-build][s2])

**pixi build** is the workspace/packaging layer above it: it covers "building and uploading a
package to a conda channel," source dependencies, and "managing multiple packages in a
workspace." The `pixi-build-python` backend runs a PEP-517 build (e.g. Hatchling) and then
converts the result into a conda package. `pixi publish` builds a `.conda` and uploads it to a
channel (`--target-channel`) or copies it locally. ([pixi docs][s5])

**Two boundaries matter.**
1. **`pixi publish` targets conda channels. The documentation does not address PyPI publishing.**
   ([pixi docs][s5]) Even the tool that runs a PEP-517 wheel build *internally* does not offer to
   ship that wheel to PyPI. The dual-ship motion is unimplemented at the substrate layer.
2. **It is preview software.** The build feature requires `preview = ["pixi-build"]` and ships
   with "a number of limitations" including limited backends and missing parameters.
   ([pixi docs][s5]) The local repo already runs in exactly this configuration.

**Read for Mason.** rattler-build and pixi are Mason's **substrate, not its competition** — Mason
should call them, never reimplement them. But the substrate stops precisely at the two places
Mason's charter points: dual-ecosystem shipping, and the semantic layer above a build (what to
build, why it failed, what the recipe should say).

---

### 4. maturin / hatch — the PyPI-side publish flows

**maturin** builds Rust-extension Python packages into wheels for Python 3.8+ across
Windows/Linux/macOS/FreeBSD. It is **PyPI-only** and does not even own the publish step: the docs
recommend `uv publish`. There is no conda or conda-forge path in its documentation.
([PyO3/maturin][s7])

**Hatch** is "a modern, extensible Python project manager" spanning build backend, environment
management, publishing "to PyPI or other indices," and version management, plus test running and
static analysis. **No mention of conda or conda-forge integration anywhere in its overview.**
([Hatch docs][s8])

**Read for Mason.** This is the sharpest finding in the survey. The best-in-class PyPI-side
project managers are *structurally unaware conda exists*. A maintainer using Hatch has a complete,
polished answer for half of their distribution problem and no answer at all for the other half —
and the tools are not converging: Hatch is not adding conda, and conda-smithy is not adding PyPI.
**The gap between them is not a feature gap in one tool; it is an unowned seam between two
toolchains.**

---

### 5. conda-lock — the environment-binding incumbent

conda-lock generates "fully reproducible lock files for conda environments" by running a conda
solve per target platform, acting as an external pre-solver. Critically, it *does* cross the
ecosystem line: it "can also lock the `dependencies.pip` section of environment.yml" using a
vendored copy of Poetry's dependency solver, and supports private pip repositories. Output is a
unified `conda-lock.yml` by default, with per-platform `conda-{platform}.lock` explicit renders
for compatibility. The repo shows active development (2,096 commits). ([conda/conda-lock][s9])

**Read for Mason.** `mason environment lock --output conda-lock.txt` from the crew charter maps
directly onto an existing, healthy tool. This is the one charter verb where a competent incumbent
already spans both ecosystems. Mason's value here is **orchestration and policy**, not solving —
and the honest framing is that Mason wraps conda-lock and/or `pixi.lock` rather than competing
with them. (Whether pixi's lock supersedes conda-lock is not answerable from the sources
gathered — see `open_questions[]`.)

---

## Landscape Map

| Capability | grayskull | conda-smithy | autotick-bot | rattler-build / pixi | hatch / maturin | conda-lock | **Mason (proposed)** |
|---|---|---|---|---|---|---|---|
| Generate conda recipe | ✅ (v0) | ❌ | ❌ | partial | ❌ | ❌ | ✅ (v1) |
| Validate against policy | ❌ | lint (feedstock) | ❌ | schema only | ❌ | ❌ | ✅ |
| Build conda pkg | ❌ | via CI | ❌ | ✅ | ❌ | ❌ | ✅ (wraps) |
| Diagnose build failure | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Submit to conda-forge | ❌ | feedstock init | ✅ (bot-owned) | ❌ | ❌ | ❌ | ✅ (maintainer-owned) |
| Version-bump automation | ❌ | ❌ | ✅ (cf only) | ❌ | `hatch version` | ❌ | ✅ (any target) |
| Build wheel / sdist | ❌ | ❌ | ❌ | via PEP-517 | ✅ | ❌ | ✅ (wraps) |
| **Publish to PyPI** | ❌ | ❌ | ❌ | **❌** | ✅ | ❌ | ✅ |
| **One command → both** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ (the gap)** |
| Cross-ecosystem lock | ❌ | ❌ | ❌ | pixi.lock | ❌ | ✅ | ✅ (wraps) |
| Usable outside conda-forge | ✅ | partial | **❌** | ✅ | ✅ | ✅ | ✅ |
| AI-assisted / agent surface | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## Local Baseline — what already exists in this repo

Measured on disk in the `pyforge-mason` worktree, 2026-07-25. These are counts, not estimates.

| Asset | Measure |
|---|---|
| `.claude/skills/conda-forge-expert/scripts/` (canonical impl) | **66 `.py`, 41,410 LOC**, flat, no `__init__.py`, 60/66 argparse CLIs with `main()` |
| `.claude/scripts/conda-forge-expert/` (public CLI tier) | **57 wrappers, 867 LOC** (mean 15.2), each a single `subprocess.run` |
| `.claude/tools/conda_forge_server.py` (MCP) | **2,266 LOC, 46 `@mcp.tool`s**, delegating via one `_run_script()` helper — **zero imports of the canonical scripts** |
| `SKILL.md` | 3,887 LOC; **10 Critical Constraints**; **106 numbered gotchas (G1–G106, contiguous)**; 9-step loop / 12 discrete actions |
| `reference/` + `guides/` + `quickref/` | 26 files, 15,005 LOC |
| Test suite | 142 files, 22,864 LOC, **1,186 test functions**, 9 meta-tests |
| Third-party runtime floor | 6 hard (`pyyaml`, `requests`, `packaging`, `truststore`, `ruamel.yaml`, `conda-forge-metadata`) + 6 lazy/optional |
| Governance | Surface governed by `spec-packaging-factory` with a **CHANGELOG sentinel**; enforced by `scripts/spec_surface_check.py` + `tests/meta/test_spec_surface_check.py` |

**Structural findings relevant to wrap-vs-build:**

1. **The canonical tier is already plain Python** — but it is *scripts*, not a *package*. No
   `__init__.py`; five filenames contain hyphens (`recipe-generator.py`,
   `dependency-checker.py`, `license-checker.py`, `feedstock-migrator.py`, `test-skill.py`),
   making them **unimportable as modules by any means**. "Already in plain Python" is true and
   materially weaker than it sounds.
2. **Every existing consumer already uses the subprocess seam.** The 57 wrappers, all ~105 CFE
   pixi tasks, and all 46 MCP tools invoke canonical scripts as `[sys.executable, script, *args]`.
   The subprocess+JSON boundary is *the established public contract* — not a compromise Mason
   would be introducing.
3. **The seam has a measured cost.** The MCP server carries `_extract_json_from_stdout()`, a
   tolerance shim that re-parses stdout when a script emits a progress line before its JSON body
   (needed for `submit_pr` / `prepare_submission_branch`). Any wrapper inherits this class of
   fragility.
4. **Path/state handling is inconsistent.** `_get_data_dir()` is **duplicated in 13 files**; the
   repo-root anchor is `parents[4]` in five scripts but `parents[3]` in two and `parents[5]` in
   one; `feedstock_lookup.py` and `feedstock_context.py` resolve to
   `.claude/skills/data/conda-forge-expert` — **a different directory from every other script**.
   There is **no env-var override for the data directory anywhere**. Any "just import it as a
   library" plan must first fix an undocumented, inconsistent path contract across 66 files.
5. **`recipes/` is hardcoded in 17 scripts** — the canonical tier assumes it is running inside
   *this repository*, not inside an arbitrary user project.

### The atlas precedent (the most important local datapoint)

`pyforge-atlas` faced the identical question one product earlier and chose to **rebuild**: it
produced `src/shared/packages/pyforge-atlas/src/pyforge/atlas/` at **80 `.py` files / 14,461 LOC**
plus **110 test files / 14,682 LOC**, hatchling + `pixi-build-python`, 32 stories across waves 0
and A–H, all merged (PRs #58–#105).

**And the legacy `conda_forge_atlas.py` (8,902 LOC) is still the live runtime.** Every
`build-cf-atlas` / `atlas-phase` / `query-cf-atlas` pixi task and every atlas MCP tool still shells
out to `.claude/scripts/conda-forge-expert/`. **Nothing routes to `pyforge.atlas`.** After ~29k LOC
of committed work, the rebuild has not displaced the original; the repo now carries two
implementations of the same capability, and the old one is what runs.

`pyforge-warden` is the contrasting case: 28 files / 16,597 LOC, built from nothing, no legacy
counterpart, shipped 31/31 and merged. **Warden built because there was nothing to wrap. Atlas
built despite there being something to wrap, and is now paying dual-maintenance.** Mason is in
atlas's position, not warden's — with an aggravating factor atlas lacked: CLAUDE.md Rule 1 makes
the CFE skill *authoritative* over any conflicting story, and Rule 2 mandates that every
conda-forge effort ends by *editing the skill*. A forked copy of recipe knowledge would be
continuously invalidated by the very retro loop that governs the domain.

---

## Where an AI-Assisted Dual-Ecosystem Product Differentiates

Four differentiators survive contact with the incumbents. Two are structural, two are earned.

**D1 — The dual-ship motion is unowned (structural).** `mason package --ship pypi,conda-forge` has
no incumbent. Hatch and maturin are structurally conda-unaware ([s7], [s8]); `pixi publish` is
documented for conda channels and silent on PyPI ([s5]); conda-smithy and the autotick-bot are
conda-forge-only by design ([s3], [s4]). This is not a feature one incumbent is about to add — it
is a seam between two toolchains with different governance, and nobody's roadmap owns it.

**D2 — Maintainer-operable automation (structural).** The autotick-bot's automation is real and
excellent and **cannot be redeployed** — it is bound to conda-forge's infrastructure, graph, and
pinnings repo ([s3]). A maintainer with a private channel, an air-gapped mirror, a JFrog
Artifactory proxy, or simply a fork has *no* access to that class of automation. Mason delivers
autotick-class behavior as an artifact the maintainer runs. (The local machinery already carries
the enterprise-routing half of this: `_http.py`, 1,024 LOC, truststore + JFrog/GitHub/.netrc auth
chain, imported by 27 of 66 scripts.)

**D3 — Semantics above the substrate (earned).** No incumbent diagnoses a failed build, knows that
a PyPI `source.url` must use the `pypi.org/packages/...` pattern for air-gapped proxying, knows
that a `build.bat` must `call` every `.cmd` shim, or knows the other 104 accumulated gotchas.
That knowledge exists in this repo as **106 numbered gotchas + 10 Critical Constraints**, kept
current by a mandatory retro loop. It is the genuinely defensible asset — and it is *the exact
asset a rebuild would fork and strand*.

**D4 — Agent-native surface (earned).** Every incumbent is a human CLI. The local machinery already
exposes 46 MCP tools. Mason's charter — "a human steering intent, not syntax" — is only reachable
if the product keeps a machine-callable surface as a first-class interface, not an afterthought.

**The honest negative finding:** for `mason environment lock`, differentiation is **weak**.
conda-lock already spans conda + pip via a vendored Poetry solver and is actively maintained
([s9]); pixi already produces a unified `pixi.lock`. Mason should wrap, not compete, and the PRD
should scope this verb as orchestration/policy rather than solving. Recorded as a scoping
constraint, not a strength.

---

## Implication for the Wrap-vs-Build Decision

The research does not settle the PRD's question by itself, but it constrains it sharply:

- **The recipe-lifecycle knowledge must not be forked.** It is D3 — the actual differentiator —
  and it lives in a surface that Rule 2 mutates continuously. Forking it converts the product's
  moat into its maintenance burden. The atlas precedent shows the concrete failure mode: two
  implementations, the old one still live.
- **The subprocess seam is the incumbent contract, not a new compromise.** 57 wrappers, ~105 pixi
  tasks, and 46 MCP tools already speak it. Mason adopting it costs nothing that is not already
  being paid.
- **But `--ship pypi` and parts of `environment lock` have no CFE counterpart at all.** There is no
  wheel build, no twine/`uv publish` path, and no lock orchestration anywhere in the 41,410 LOC.
  These are net-new and must be *built*, not wrapped.

The shape this points to is not A-or-B but a **seam placed by capability**: wrap where knowledge
exists and churns, build where nothing exists. The PRD must state that seam explicitly and name
the test that keeps it honest.

---

## assumptions[]

1. **A-1** — Mason's charter verbs (`recipe build`, `package --ship`, `environment lock`) are taken
   from `docs/dreams/ecosystem-crew.md` § 5 verbatim and treated as binding product scope. No
   stakeholder was available to confirm they are still the intended surface.
2. **A-2** — "Dual-ecosystem" means conda-forge + PyPI specifically. The dream's wider list
   (npm, CRAN, CPAN, LuaRocks) is treated as *source* ecosystems for recipe generation, not as
   *publish* targets for `--ship`.
3. **A-3** — The target operator is the individual maintainer / small team already using pixi,
   not conda-forge core infrastructure. D2's value depends on this; if the target were
   conda-forge itself, the autotick-bot is the incumbent and Mason is redundant.
4. **A-4** — Vendor documentation claims (rattler-build's "faster than conda-build", pixi's
   feature list) are reported as claims. No benchmark was run.
5. **A-5** — `pixi publish`'s silence on PyPI in its documentation is read as absence of the
   feature. Not independently verified against the pixi source.
6. **A-6** — The local LOC/tool counts are point-in-time (2026-07-25, CFE v8.79.1) and will drift;
   they are used for *shape* arguments (flat scripts, subprocess seam, duplicated path logic),
   which are robust to drift, not for exact-number commitments.
7. **A-7** — grayskull's lack of documented v1 `recipe.yaml` output reflects current capability.
   If grayskull ships v1 emission, one component-level argument weakens (none of D1–D4 do).

## open_questions[]

1. **OQ-1** — **Coverage risk.** The web-search budget was exhausted before this survey, so the
   landscape was assembled from known primary URLs. An open discovery sweep for unknown entrants
   (a "dual-publish" tool nobody in this repo has heard of) has **not** been run. Recommend a
   dedicated search pass before the PRD is frozen.
2. **OQ-2** — Does `pixi publish` (or a preview flag) actually support PyPI targets in source,
   contradicting the docs? Determines whether D1 is a durable gap or a 6-month window.
3. **OQ-3** — Is conda-lock superseded by `pixi.lock` in practice? Sources gathered do not
   address the relationship. Determines whether `mason environment lock` wraps conda-lock,
   `pixi.lock`, or both.
4. **OQ-4** — Is `mason` intended to run *outside* this repository (arbitrary user project, CI,
   another org's repo)? The 17 scripts hardcoding `recipes/` and the absence of any data-dir
   env-var make this the single highest-cost requirement in the set. **Must be answered in the
   PRD** — it is the main variable that could flip the wrap-vs-build calculus.
5. **OQ-5** — Does Mason inherit the atlas dual-implementation problem, i.e. is there an
   expectation that `mason` eventually *replaces* the pixi-task surface, or do both persist
   indefinitely? Atlas never answered this and now carries both.
6. **OQ-6** — Is `--ship pypi` expected to handle credentials/trusted publishing (OIDC), or only
   emit artifacts for a human to upload? Materially different scope and security posture.
7. **OQ-7** — Does Mason own multi-ecosystem *autotick* (the dream's frontier item: CRAN/npm/cargo
   updaters), or is that Steward/Marshal territory? The dream lists it under the packaging
   factory; the crew charter does not put it in Mason's CLI cadence.

---

## Sources

- [s1] conda/grayskull — https://github.com/conda/grayskull
- [s2] prefix-dev/rattler-build — https://github.com/prefix-dev/rattler-build
- [s3] regro/cf-scripts (conda-forge autotick-bot) — https://github.com/regro/cf-scripts
- [s4] conda-forge/conda-smithy — https://github.com/conda-forge/conda-smithy
- [s5] pixi build documentation — https://pixi.prefix.dev/latest/build/getting_started/
- [s6] conda-forge maintainer docs, "Adding packages" — https://conda-forge.org/docs/maintainer/adding_pkgs/
- [s7] PyO3/maturin — https://github.com/PyO3/maturin
- [s8] Hatch documentation — https://hatch.pypa.io/latest/
- [s9] conda/conda-lock — https://github.com/conda/conda-lock

Local (non-web) evidence: direct filesystem inventory of
`.claude/skills/conda-forge-expert/`, `.claude/scripts/conda-forge-expert/`,
`.claude/tools/conda_forge_server.py`, `pixi.toml`, and
`src/shared/packages/pyforge-{atlas,warden}/` in the `pyforge-mason` worktree at 2026-07-25.

---

## Refresh addendum — 2026-08-08

Re-validated with live web search (the original pass ran on an exhausted search budget —
OQ-1's deferred discovery sweep is now done; full detail and sources in the companion
`market-mason-packaging-automation-2026-08-08.md`). Status of this report's claims:

**Assumptions triggered / resolved:**
- **A-7 TRIGGERED** — grayskull now emits v1 `recipe.yaml` (`--use-v1-format
  --strict-conda-forge`), and it is conda-forge's documented recommended path for new PyPI
  recipes; rattler-build also grew its own `generate-recipe` subcommand. As A-7 predicted,
  one component-level argument weakens and none of D1–D4 fall. The landscape-map cell
  "grayskull: Generate conda recipe ✅ (v0)" is now "✅ (v0 + v1)".
- **A-6 confirmed drifting as expected** — ground truth 2026-08-08: 67 canonical scripts
  (was 66), 60 public wrappers (was 57), 46 MCP tools (unchanged), skill v8.81.0 (was
  v8.79.1). The shape arguments all still hold.

**Open questions answered:**
- **OQ-1 (discovery sweep)** — DONE. The sweep found two previously-unexamined dual-*build*
  analogues — `whl2conda` (wheel→.conda direct, one-command dual build, dependency renaming)
  and `hatch-conda-build` (Hatch plugin, conda target from pyproject.toml) — and confirmed
  neither ships/uploads/submits anywhere. **No dual-ship entrant exists.** D1 holds.
- **OQ-2 (pixi publish + PyPI)** — ANSWERED: NO. `pixi publish` shipped as a real command
  (channels, `cloudsmith://`, S3 with auto-init/reindex, local dirs) and remains conda-only.
  D1 re-confirmed with a dated source; residual risk tracked as the market report's OQ-M1
  (prefix.dev velocity).
- **OQ-3 (conda-lock vs pixi.lock)** — ANSWERED: conda-lock is maintained (release
  2026-07-01) but its lead maintainer publicly endorses pixi as "the future of lockfiles in
  the Conda ecosystem" (conda/conda-lock#615) and ships a pixi migration path; the May 2026
  conda releases made conda itself consume both `conda-lock.yml` and `pixi.lock` natively.
  Consequence for Mason: `environment lock` wraps **pixi first**, conda-lock second (for
  non-pixi manifest populations). The "wrap, don't compete" negative finding stands,
  stronger than before.
- **OQ-4 (run outside this repo)** — answered in the PRD/architecture after this report:
  the D-1/AD-5 resolution chain (flag → env → upward walk → structured degradation) plus the
  AD-6 capability split; T3 (no `.claude/` at all) keeps `package`/`environment` working and
  degrades `recipe` with exit 3 (epics S-1.5/S-1.7).
- **OQ-5 (atlas dual-implementation risk)** — mitigated by design since: S-2.2's seam guard
  is the critical-path story, and the 2026-08-02 `pyforge-mason-recipe-validator` sibling
  Dream (retired same-day as a D-1 conflict) is live evidence the guard is needed.
- **OQ-6 (credentials/OIDC)** — partially answered by market movement: PyPI trusted
  publishing (OIDC) is now the ecosystem's golden path, prefix.dev supports OIDC for conda
  channels, and rattler-build attaches Sigstore attestations. See the market report § 5 for
  the two spec-level nudges to S-3.4/S-3.7.
- **OQ-7 (multi-ecosystem autotick ownership)** — resolved by the PRD: out of v1
  (non-goals), reaffirmed in the Dream's frontier section.

**One new landscape fact worth carrying:** pixi-build is still preview (opt-in
`workspace.preview`), but CPython, SciPy, Xarray, and Dask now build with it, and the
backends release stable on conda-forge — the substrate bet this report endorsed has
strengthened, not aged.
