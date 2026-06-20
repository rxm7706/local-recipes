---
status: ready
spec_updated: 2026-06-20
---
# Tech Spec: Microsoft GitHub Org → conda-forge

> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow track —
> portfolio packaging effort, ~14 implementation stories spanning 3 waves
> and ~10–14 staged-recipes PRs).
> Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/microsoft-conda-forge.md
> ```

---

## Status

| Field | Value |
|---|---|
| Status | **Draft v1** — ready for `bmad-quick-dev` intake; 3 open questions (Q1–Q3) noted, none v1-blocking. |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (tech-spec only, no PRD/architecture phase) |
| Upstream | Multiple `github.com/microsoft/*` repos (per-story); all MIT or Apache-2.0. |
| Target | `conda-forge/staged-recipes` (new feedstocks). Each story = one independently-submittable recipe; PRs land staggered. |
| Distribution | conda-forge (noarch:python for pure-Python; per-platform for Rust CLI + C++ libs). |
| Lifetime | One-shot land + handoff. Feedstocks become autotick-maintained after first PR lands. |

---

## Background and Context

### The problem

Microsoft publishes a large, high-quality OSS portfolio (~200+ active
public repos) including several flagship Python AI/ML projects with
significant user demand. The June 2026 audit (this spec's basis,
documented separately in the parent conversation) cross-checked the top
~120 Microsoft repos by stars against conda-forge feedstocks via
`lookup_feedstock`. The result:

- **Already shipped on conda-forge** (20+ feedstocks): markitdown,
  autogen-agentchat / pyautogen / autogen-core, graphrag,
  presidio-analyzer, pyright, FLAML, LightGBM, DeepSpeed, ONNX Runtime,
  onnxscript, LoRA, LLMLingua, hummingbird-ml, TorchGeo, TypeScript,
  Playwright (+ Python), debugpy, GSL (`ms-gsl`), picologging, the
  Microsoft 365 Agents kiota family (shipped from this repo in
  May 2026), and **`agent-framework-core` v1.8.0** (which arrived
  between the start of the audit and the spec write-up — a positive
  surprise that converts the agent-framework story from
  "2 recipes" to "1 thin umbrella recipe").

- **Material gaps with clear PyPI / Cargo presence and clean MIT/Apache
  license**: ~10–14 candidates across 3 difficulty tiers. This spec
  packages them.

- **Cannot ship** (categorical, not in scope): Windows-only system
  tools (PowerToys, terminal, WSL, winget-cli, …); .NET-heavy
  (`garnet`, `aspire`, `kiota` CLI); research code without library
  shape (TRELLIS, JARVIS, BioGPT, Swin-Transformer, OmniParser,
  table-transformer, …); docs/training repos (every `*-for-beginners`);
  vendor-distributed binaries (vscode, vcpkg, MS-DOS); browser-only
  npm libs (monaco-editor, fluentui, FluidFramework). See § "Out of
  Scope" for the full exclusion list.

### What's been investigated and ruled out

- **Microsoft/typescript-go.** 25.6k★ native Go port of the TS
  compiler — looks like a perfect conda-forge fit (Go, MIT,
  cross-platform). **Repo description says "Staging repo for
  development of native port of TypeScript"**; no 1.0, breaking
  changes expected. Defer until upstream tags a stable release. The
  existing `typescript` feedstock (6.0.2, conda-forge) covers users
  in the interim.

- **Microsoft/VibeVoice.** 49k★ frontier voice AI. Microsoft pulled
  the upstream code in 2025 (per GitHub history); current state is
  research-snapshot, not a maintained library. Out of scope — no
  stable PyPI release to track.

- **Microsoft/BitNet.** 39k★ 1-bit LLM inference. C++ kernels + Python
  wrapper, MIT. **Build is non-trivial** (custom MLIR-like passes,
  hand-tuned per-CPU kernels). Realistic timeline is multi-week, not
  multi-day. Listed in Wave 3 as a stretch target; not commit-required.

- **Microsoft/recommenders.** 28-dep Python lib, MIT, py≥3.6, on PyPI
  as `recommenders` 1.2.1. Dep tree is wide (`cornac`, `transformers`,
  `scikit-learn`, plus optional spark/gpu/nni extras). Feasible but
  the breadth of `[experimental]` / `[gpu]` / `[spark]` extras makes
  the run_constraints block heavy. Listed in Wave 2 as
  effort-pending; not commit-required.

- **Microsoft/semantic-kernel** (Python). 28k★, on PyPI as
  `semantic-kernel` 1.43.0, MIT, py≥3.10. 47 dependencies with **18
  optional extras** (`anthropic`, `aws`, `chroma`, `google`,
  `hugging-face`, `milvus`, `mistralai`, `mongo`, `ollama`, `onnx`,
  `oracledb`, `pandas`, `pinecone`, `postgres`, `qdrant`, `redis`,
  `sql`, `usearch`, `weaviate`). Wide surface but every extra is
  resolvable on conda-forge today. Listed in Wave 2 as a deliberate
  single-recipe submission (extras flatten into `run_constraints:`).

- **Microsoft/PromptWizard.** 3.9k★, MIT. Quick check of PyPI's
  `promptwizard` 1.0.0 returns *a different upstream* (generic "Prompt
  Wizard is a package for evaluating custom prompts") — not
  Microsoft's repo. **Open Q1 below.** Need to confirm whether
  Microsoft's PromptWizard has its own published PyPI artifact before
  promising a recipe.

### What's available to leverage

- **`conda-forge-expert` skill v8.11+** provides
  `generate_recipe_from_pypi`, `validate_recipe`, `optimize_recipe`,
  `check_dependencies`, `scan_for_vulnerabilities`, `trigger_build`,
  `prepare_submission_branch`, `submit_pr`. Each recipe in this spec
  runs the standard 9-step autonomous loop.

- **Rust CLI canonical pattern** (SKILL.md Critical Constraints + the
  v8.7+ Rust template at
  `.claude/skills/conda-forge-expert/templates/rust/cli-recipe.yaml`):
  `cargo auditable install --locked --no-track --bins` +
  `cargo-bundle-licenses` + unix/win install-root split + `script.env`
  for `CARGO_PROFILE_RELEASE_{STRIP, LTO}`. Directly applicable to S1
  (microsoft/edit) without invention.

- **Cocoindex-class precedent** for non-trivial Rust+Python recipes
  (PR #33231 — see SKILL.md G1/G3/G4). Sets the bar for Wave-3
  compiled stories.

- **Microsoft kiota / Agents family** already on conda-forge from this
  repo's May 2026 work (microsoft-kiota-bundle,
  microsoft-agents-m365copilot{,-core}). Sets the precedent that
  Microsoft polyglot-monorepo recipes are reviewable and mergeable
  under existing patterns.

- **Existing canonical templates**:
  `templates/rust/cli-recipe.yaml` (Wave 1 S1),
  `templates/python/noarch-recipe.yaml` (every Wave 1 + Wave 2
  Python story),
  `templates/multi-output/lib-python-recipe.yaml` (Wave 2 promptflow,
  Wave 3 DiskANN).

---

## Goals

- **G1.** Land **microsoft/edit** as a `recipes/microsoft-edit/` Rust
  CLI recipe following the canonical 5-element pattern. Builds clean
  on linux-64, osx-64, osx-arm64, win-64.
- **G2.** Land **microsoft/agent-framework** (the umbrella meta) as a
  thin `noarch: python` recipe whose only run dep is the
  already-shipped `agent-framework-core[all]`. Wave 1 quick win.
- **G3.** Land **microsoft/qlib** (PyPI `pyqlib`) as a `noarch: python`
  recipe. Highest-demand unpackaged Microsoft Python project (44k★).
- **G4.** Land **microsoft/PyRIT** (`pyrit`), **microsoft/promptflow**
  (4 outputs: `promptflow-tracing`, `promptflow-core`,
  `promptflow-devkit`, `promptflow`), **microsoft/semantic-kernel**,
  and **microsoft/torchscale** in Wave 2. All `noarch: python`.
- **G5.** Land **microsoft/SEAL** (C++ homomorphic encryption library
  via CMake) and **microsoft/DiskANN** (C++ ANN library + `diskannpy`
  Python bindings, multi-output) in Wave 3.
- **G6.** Each PR cites the upstream Microsoft repo + license in the
  body; each recipe carries `rxm7706` as a maintainer (additive
  to whoever else co-maintains).
- **G7.** Apply the conda-forge-expert retro rule at end of effort:
  bmad-retrospective updates SKILL.md / CHANGELOG.md with any
  novel gotchas surfaced during the 14 stories.

## Non-Goals

- **NG1.** No CUDA-variant recipes. SEAL and DiskANN ship CPU-only
  recipes first; GPU variants are deferred to follow-on PRs (and to
  whoever picks up the feedstock long-term).
- **NG2.** No `microsoft/BitNet` recipe in this v1 effort. The
  custom-MLIR build is multi-week — separate spec when prioritized.
- **NG3.** No `microsoft/typescript-go` recipe. Upstream not yet 1.0;
  await tagged stable release. Documented in
  `_bmad-output/projects/local-recipes/implementation-artifacts/deferred-work.md`.
- **NG4.** No upstream PRs to Microsoft repos. No README fixes, no
  license corrections, no pyproject loosening. Recipes absorb
  upstream artifacts as published.
- **NG5.** No re-packaging of already-shipped feedstocks. The
  20+ existing Microsoft-origin feedstocks (markitdown, autogen,
  graphrag, …) are out of scope; this spec ships only the gaps.
- **NG6.** No Microsoft semantic-kernel C# / .NET packaging. The
  conda-forge channel does not ship the .NET runtime; this spec
  covers only the Python sibling (`semantic-kernel` PyPI dist).
- **NG7.** No `microsoft-edit` Windows-installer mimicry. The conda
  recipe produces a `edit` (or `msedit` per Q3) shell binary; users
  who want the WinGet experience can keep using WinGet.
- **NG8.** No feedstock-level CI customization beyond what
  staged-recipes provides by default. Standard `.ci_support` matrix
  for every recipe; no `provider:` override.
- **NG9.** No Anaconda-channel mirror. conda-forge only.

---

## Lifecycle Expectations

After each staged-recipes PR merges:

- `regro-cf-autotick-bot` files autotick PRs on each new upstream tag.
  For S2 (agent-framework meta) the autotick is one-line; for
  S6 (DiskANN multi-output) the bot only handles version + sha256, so
  the maintainer (rxm7706) handles structural deps on bump.
- `conda-forge-webservices` runs lint + rerender automatically.
- Each recipe ships with the maintainer set `[rxm7706, <any co-maintainer
  identified during PR review>]`. No commitment to long-term solo
  maintenance — additional maintainers welcome at PR review time.
- The shipped feedstocks become canonical install paths; users on
  conda-managed / air-gapped / JFrog Artifactory environments get the
  packages through their existing channel without falling back to pip.

---

## User Stories

3 waves, 14 stories. Parallelism within a wave is fine. Each wave only
depends on the *previous wave's PRs entering staged-recipes review
queue*, not on them merging — staged-recipes review is multi-day per
PR, and serializing on merges would stretch the effort to months.

| Wave | Stories | Description |
|---|---|---|
| 1 | S1–S4 | Quick wins: 1 Rust CLI + 3 thin Python recipes. Independent leaves. |
| 2 | S5–S11 | Mid-tier Python: PyRIT, promptflow (4 outputs), semantic-kernel, torchscale. |
| 3 | S12–S14 | Native/compiled: SEAL, DiskANN (multi-output), follow-on. |

### Story S1 — Recipe: `microsoft-edit` (Rust CLI)

**Goal**: Land microsoft/edit (Rust terminal text editor, 14.3k★, MIT)
as a per-platform recipe following the v8.7+ canonical Rust CLI
pattern.

**Acceptance criteria**:
- `recipes/microsoft-edit/recipe.yaml` validates clean.
- Source from `github.com/microsoft/edit/archive/refs/tags/v${{ version }}.tar.gz`
  (v2.0.0, released 2026-04-28). Verify sha256.
- Build deps: `${{ compiler('rust') }}`, `${{ compiler('c') }}`,
  `${{ stdlib('c') }}`, `cargo-bundle-licenses`, `cargo-auditable`.
- `script.env`: `CARGO_PROFILE_RELEASE_STRIP: symbols`,
  `CARGO_PROFILE_RELEASE_LTO: fat`.
- `script.content`: unix path uses `--root ${{ PREFIX }}`; win path
  uses `--root %LIBRARY_PREFIX%`. Both invoke
  `cargo auditable install --locked --no-track --bins --path .`.
- `cargo-bundle-licenses --format yaml --output ./THIRDPARTY.yml`
  runs after install.
- `package_contents.strict: true`; primary binary `edit` (or `msedit`
  per Q3) is shipped under `bin/`.
- Tests: `edit --version` returns the recipe version; on Windows,
  `where edit` succeeds.
- License: MIT — already in archive root as `LICENSE`.
- Build matrix: linux-64, linux-aarch64, osx-64, osx-arm64, win-64.
- Builds clean locally via `pixi run -e local-recipes recipe-build
  recipes/microsoft-edit` on at least one host platform.
- `submit_pr(recipe_name="microsoft-edit")` returns a `pr_url`.

**Wave**: 1.

**Estimated effort**: 1–2 h. Direct application of the canonical Rust
CLI template; primary risk is the binary-name decision (see Q3).

### Story S2 — Recipe: `agent-framework` (umbrella meta)

**Goal**: Land microsoft/agent-framework (11.2k★, MIT, py≥3.10) as a
thin `noarch: python` umbrella whose only dep is the already-shipped
`agent-framework-core[all]==<version>`. Sister to the conda-forge
`agent-framework-core` v1.8.0 feedstock that arrived during this
effort's scoping window.

**Acceptance criteria**:
- `recipes/agent-framework/recipe.yaml` validates clean.
- Source from PyPI sdist
  `agent_framework-${{ version }}.tar.gz`. Version starts at 1.8.1
  (current latest).
- `noarch: python`.
- Build: `pip install . --no-deps --no-build-isolation`.
- Host: `python ${{ python_min }}.*`, `pip`, `flit-core <4,>=3.11`
  (match upstream backend).
- Run: `python >=${{ python_min }}`, `agent-framework-core ==${{ version }}`
  (exact pin — upstream uses `==1.8.1`, this is the version-pinned
  umbrella pattern documented at upstream).
- Tests: `python -c "import agent_framework"` + `pip check`.
- License: MIT.
- `submit_pr(recipe_name="agent-framework")` returns a `pr_url`.

**Wave**: 1.

**Estimated effort**: 30 min.

### Story S3 — Recipe: `pyqlib` (Microsoft qlib)

**Goal**: Land microsoft/qlib (44k★, MIT, on PyPI as `pyqlib` 0.9.7)
as a `noarch: python` recipe. Highest-demand unpackaged Microsoft
Python project.

**Acceptance criteria**:
- `recipes/pyqlib/recipe.yaml` validates clean.
- Source from PyPI (`pyqlib-${{ version }}.tar.gz`).
- `noarch: python`.
- Build: `pip install . --no-deps --no-build-isolation`.
- Run-deps audited via `check_dependencies` and the PyPI→conda
  mapping rules from SKILL.md G10 (verify 4 spelling forms before
  declaring a dep missing). Expected deps already on conda-forge:
  `pyyaml`, `numpy`, `pandas`, `mlflow`, `lightgbm`, `scikit-learn`,
  `loguru`, `tqdm`, `requests`, `joblib`, `cvxpy`, `redis-py`,
  `python-socks`, `tornado`, `dill`, `gym`, `plotly` (~40 total).
- If `cvxpy` or any other dep surfaces unmapped, flag inline; do
  NOT silently skip.
- `python_min: "3.10"` (conda-forge floor; upstream allows 3.8 but
  conda-forge dropped 3.9 in Aug 2025).
- Tests: `import qlib`, `pip check`. Optional: `qlib --help` if a
  CLI is exposed (check `[project.scripts]` in the sdist's
  pyproject.toml).
- License: MIT — `LICENSE` at root.
- Feedstock-name asymmetry: recipe = `pyqlib`, top-level import =
  `qlib`. Document in recipe header comment.
- `submit_pr(recipe_name="pyqlib")` returns a `pr_url`.

**Wave**: 1.

**Estimated effort**: 1.5–2 h (most of it is the dep audit + any
remediation for unmapped transitives).

### Story S4 — Recipe: `pyrit` (Microsoft PyRIT)

**Goal**: Land microsoft/PyRIT (4k★, MIT, py 3.10–3.14, on PyPI as
`pyrit` 0.14.0) as a `noarch: python` recipe.

**Acceptance criteria**:
- `recipes/pyrit/recipe.yaml` validates clean.
- Source from PyPI.
- `noarch: python`.
- Build: `pip install . --no-deps --no-build-isolation`.
- Run-deps (72 in upstream `requires_dist`): `aiofiles`, `alembic`,
  `appdirs`, `art`, `av`, `azure-core`, `azure-identity`,
  `azure-ai-contentsafety`, `azure-storage-blob`, `base2048`,
  `colorama`, `confusables`, `confusable-homoglyphs`, `ecoji`,
  `datasets`, `fastapi`, `httpx`, `jinja2`, `numpy`, `openai`,
  `openpyxl`, `pillow`, `pydantic`, `PyJWT`, `pyodbc`, `pypdf`,
  `python-docx`, `python-dotenv`, `reportlab`, `segno`, `scipy`,
  `SQLAlchemy`, `starlette`, `termcolor`, `tenacity`, `tinytag`,
  `tqdm`, `transformers`, `treelib`, `uvicorn`, `websockets`,
  `build`, `pytorch`. Plus `run_constraints:` for the extras
  (`huggingface`, `gcg`, `playwright`, `fairness-bias`, `opencv`,
  `speech`).
- Audit each dep via `check_dependencies` (G10 4-spelling rule).
  `base2048`, `confusables`, `ecoji`, `segno`, `art`, `tinytag`,
  `treelib`, `confusable-homoglyphs`, `pyodbc` are the
  highest-risk unmapped candidates.
- For each missing dep, decide: package it as a S4-prereq mini-PR,
  or drop it from `run:` and document the gap. Default: package
  it (avoids shipping a recipe that fails `pip check`).
- `python_min: "3.10"`. Upstream upper bound `<3.15` is OK to
  declare in `run:` per SKILL.md "upstream-explicit upper bound" rule.
- Tests: `import pyrit`, `pip check`.
- License: MIT.
- `submit_pr(recipe_name="pyrit")` returns a `pr_url`.

**Wave**: 2.

**Blocked by**: Wave 1 PRs (S1–S3) entering staged-recipes review
queue (review-queue throughput, not technical dependency).

**Estimated effort**: 2–4 h, depending on how many of the unmapped
transitives need their own S4-prereq mini-PRs. Worst-case adds 5
trivial pure-Python recipes.

### Story S5 — Recipe: `promptflow-tracing` (leaf)

**Goal**: Land `promptflow-tracing` (Microsoft promptflow's tracing
subpackage) as a `noarch: python` recipe. Required by
`promptflow-core` (S6).

**Acceptance criteria**:
- `recipes/promptflow-tracing/recipe.yaml` validates clean.
- Source from PyPI.
- `noarch: python`.
- Run-deps per upstream `requires_dist` (audit).
- `python_min: "3.10"` (upstream `>=3.9, <4.0` → bump to 3.10 floor).
- License: MIT.
- `submit_pr` succeeds.

**Wave**: 2.

**Estimated effort**: 45 min.

### Story S6 — Recipe: `promptflow-core`

**Goal**: Land `promptflow-core` (depends on `promptflow-tracing`).

**Acceptance criteria**:
- `recipes/promptflow-core/recipe.yaml` validates clean.
- `noarch: python`.
- Run-deps include `promptflow-tracing` (in staged-recipes review
  via S5).
- License: MIT.
- `submit_pr` succeeds.

**Wave**: 2.

**Blocked by**: S5 PR entering review queue.

**Estimated effort**: 45 min.

### Story S7 — Recipe: `promptflow-devkit`

**Goal**: Land `promptflow-devkit` (depends on `promptflow-core` +
`promptflow-tracing`).

**Acceptance criteria**:
- `noarch: python`.
- Run-deps include `promptflow-core`, `promptflow-tracing`.
- License: MIT.
- `submit_pr` succeeds.

**Wave**: 2.

**Blocked by**: S5 + S6 PRs entering review queue.

**Estimated effort**: 1 h.

### Story S8 — Recipe: `promptflow` (umbrella meta)

**Goal**: Land `promptflow` (11.1k★, MIT, py>=3.9,<4.0, on PyPI
`promptflow` 1.18.5) — thin meta over
`promptflow-{tracing,core,devkit}`.

**Acceptance criteria**:
- `noarch: python`.
- Run-deps: `promptflow-tracing`, `promptflow-core`, `promptflow-devkit`
  (all exact pins to S5/S6/S7's versions).
- `python_min: "3.10"`.
- License: MIT.
- `submit_pr` succeeds.

**Wave**: 2.

**Blocked by**: S5 + S6 + S7 PRs entering review queue.

**Estimated effort**: 30 min.

### Story S9 — Recipe: `semantic-kernel` (Python)

**Goal**: Land microsoft/semantic-kernel Python SDK (28k★, MIT, py≥3.10,
on PyPI as `semantic-kernel` 1.43.0) as a `noarch: python` recipe.

**Acceptance criteria**:
- `recipes/semantic-kernel/recipe.yaml` validates clean.
- Source from PyPI.
- `noarch: python`.
- Build: `pip install . --no-deps --no-build-isolation`.
- Run-deps (core, 22 packages): `aiohttp`, `cloudevents`, `pydantic`,
  `pydantic-settings`, `defusedxml`, `azure-identity`, `numpy`,
  `openai`, `openapi_core`, `websockets`, `aiortc`,
  `opentelemetry-api`, `opentelemetry-sdk`, `prance`, `pybars4`,
  `jinja2`, `nest-asyncio`, `scipy`, `typing-extensions`, `mcp`,
  `azure-ai-projects`, `azure-ai-agents`.
- `run_constraints:` for the 18 extras: `anthropic`,
  `autogen-agentchat`, `boto3`, `azure-ai-inference`,
  `azure-core-tracing-opentelemetry`, `azure-search-documents`,
  `azure-cosmos`, `chromadb`, `microsoft-agents-copilotstudio-client`,
  `faiss-cpu`, `google-cloud-aiplatform`, `google-genai`,
  `transformers`, `sentence-transformers`, `pytorch` (for HF),
  `pymilvus`, `mistralai`, `pymongo`, `motor`, `ipykernel`,
  `ollama`, `onnxruntime`, `oracledb`, `pandas`, `pinecone`,
  `psycopg`, `qdrant-client`, `redis`, `redisvl`, `pyodbc`,
  `usearch`, `pyarrow`, `weaviate-client`.
- `microsoft-agents-copilotstudio-client` is not yet on conda-forge
  — drop from `run_constraints:` with a TODO, or package as a
  S9-prereq mini-PR if the user wants it. Default: drop with TODO.
- `python_min: "3.10"`.
- Tests: `import semantic_kernel`, `pip check`.
- License: MIT.
- `submit_pr` succeeds.

**Wave**: 2.

**Estimated effort**: 2–3 h (the extras audit is the meat of it).

### Story S10 — Recipe: `torchscale`

**Goal**: Land microsoft/torchscale (3.1k★, MIT) — foundation
architecture for (M)LLMs — as a `noarch: python` recipe. On PyPI.

**Acceptance criteria**:
- `recipes/torchscale/recipe.yaml` validates clean.
- Source from PyPI.
- `noarch: python`.
- Run-deps: `pytorch`, plus any others surfaced by audit (expected
  small dep tree — research-flavored library).
- `python_min: "3.10"`.
- License: MIT.
- `submit_pr` succeeds.

**Wave**: 2.

**Estimated effort**: 1 h.

### Story S11 — Recipe: `promptwizard` (Microsoft PromptWizard) — gated on Q1

**Goal**: Land microsoft/PromptWizard (3.9k★, MIT) if Q1 confirms it
has a Microsoft-published PyPI artifact. The bare PyPI `promptwizard`
1.0.0 belongs to a different upstream — packaging it would mis-attribute.

**Acceptance criteria** (conditional on Q1 = "yes, distinct
Microsoft package"):
- Recipe sourced from the correct PyPI distribution (name TBD per Q1).
- `noarch: python`.
- License: MIT.
- `submit_pr` succeeds.

**Wave**: 2 (or deferred to follow-on spec if Q1 resolves
negative — e.g., Microsoft ships PromptWizard only as `git clone +
pip install -e .`).

**Estimated effort**: 1 h (if PyPI artifact exists) / N/A (if not).

### Story S12 — Recipe: `microsoft-seal` (C++ HE library)

**Goal**: Land microsoft/SEAL (4k★, MIT, C++, CMake) as a C++ library
recipe. Cross-platform via CMake; no Python bindings upstream (the
ecosystem `python-seal` is third-party and out of scope here).

**Acceptance criteria**:
- `recipes/microsoft-seal/recipe.yaml` validates clean.
- Source from `github.com/microsoft/SEAL/archive/refs/tags/v${{ version }}.tar.gz`.
  Current latest is v4.1.x.
- Build via CMake: `cmake -GNinja %CMAKE_ARGS% -DSEAL_BUILD_DEPS=OFF
  -DSEAL_USE_INTRIN=ON -DSEAL_BUILD_EXAMPLES=OFF -DSEAL_BUILD_TESTS=OFF`.
- Bundled deps OFF — install `zlib`, `zstd`, `gsl` (microsoft/GSL,
  already on conda-forge as `ms-gsl`), `hexl` from conda-forge.
- Build deps: `${{ compiler('cxx') }}`, `${{ stdlib('c') }}`,
  `cmake`, `ninja`, `pkg-config`.
- Host deps: `ms-gsl`, `zlib`, `zstd`. (HEXL is optional.)
- Run deps: usual library run-exports.
- `package_contents` lists the installed `include/SEAL-*/seal/seal.h`
  + `lib/cmake/SEAL-*/SEALConfig.cmake` + the shared/static library.
- Build matrix: linux-64, linux-aarch64, osx-64, osx-arm64, win-64.
- Builds clean locally on at least one platform.
- `submit_pr` succeeds.

**Wave**: 3.

**Estimated effort**: 4–8 h (first C++/CMake recipe in this spec;
risk centers on CMake config-package layout, dep-toggle flags,
Windows MSVC compatibility).

### Story S13 — Recipe: `diskannpy` + `libdiskann` (multi-output)

**Goal**: Land microsoft/DiskANN (1.8k★, MIT) as a 2-output recipe:
the C++ shared library (`libdiskann`) + the Python bindings
(`diskannpy`).

**Acceptance criteria**:
- `recipes/diskann/recipe.yaml` validates clean.
- Source from GitHub tag.
- Output 1 — `libdiskann`: C++ shared library via CMake. Build deps
  `${{ compiler('cxx') }}`, `${{ stdlib('c') }}`, `cmake`, `ninja`,
  Intel MKL or OpenBLAS, Boost. Per-platform.
- Output 2 — `diskannpy`: Python bindings via pybind11.
  `${{ pin_subpackage('libdiskann', exact=True) }}` in run-deps.
  Per-platform.
- Build matrix: linux-64, osx-64, osx-arm64 (skip win-64 in v1 if
  upstream's Windows story has known gaps; document the skip with
  a TODO).
- Tests: `import diskannpy`, smoke test (build a small index).
- License: MIT.
- `submit_pr` succeeds.

**Wave**: 3.

**Estimated effort**: 6–12 h (multi-output + native compile +
pybind11; nontrivial but precedented by faiss / hnswlib feedstocks).

### Story S14 — Closeout retro

**Goal**: Run `bmad-retrospective` once Wave 1 + Wave 2 PRs have all
either merged or entered review-on-hold state. Per the SKILL.md
always-on Rule 2.

**Acceptance criteria**:
- Retro file written at
  `_bmad-output/projects/local-recipes/implementation-artifacts/retro-microsoft-conda-forge-<date>.md`.
- Identifies corrections / refinements / additions surfaced across
  S1–S13. Particular attention to:
  - Whether any of the four Rust CLI canonical-pattern elements
    needed tweaking for microsoft/edit.
  - Whether the agent-framework meta pattern is reusable for
    similar Microsoft umbrella-packages.
  - Whether qlib's dep audit surfaced new PyPI→conda mapping gaps
    that should land in `feedback_pypi_conda_mapping_unreliable.md`.
  - Whether the semantic-kernel extras audit produced a reusable
    pattern (e.g., "drop unmapped extras with TODO + open
    follow-on") worth codifying.
  - Any new gotchas to add to SKILL.md G16+ (Microsoft-specific or
    general).
- `CHANGELOG.md` PATCH bump (or MINOR if a new gotcha-section was
  added).
- Spec marked **Shipped** at top with merge SHAs for each landed PR.

**Wave**: 3 (closeout).

**Estimated effort**: 1.5–2 h.

---

## Functional Requirements

### FR-1. Each recipe carries `rxm7706` as a maintainer

Additive — preserve any existing maintainers if the recipe is being
refreshed; for new recipes, sole maintainer is `rxm7706` unless the
PR review surfaces a community co-maintainer.

### FR-2. Each recipe uses v1 `recipe.yaml` format

`schema_version: 1` + the schema-header comment per SKILL.md Critical
Constraints. v0 `meta.yaml` is only acceptable when migrating an
existing v0 feedstock — irrelevant here since all stories are new
recipes.

### FR-3. PyPI source URL uses the literal `pypi.org/packages/...` pattern

Per SKILL.md "PyPI `source.url` Must Use..." critical constraint.
Path segments literal; only `${{ version }}` interpolates.

### FR-4. `python_min` defaults to `"3.10"` (conda-forge floor)

Override only when upstream's `python_requires` declares a strictly
higher floor (e.g., pyrit's `>=3.10,<3.15` is fine at 3.10; if it
were `>=3.11`, the recipe declares `python_min: "3.11"` in
context).

### FR-5. CFEP-25 dual-version test matrix for every noarch:python recipe

`tests[].python.python_version: [${{ python_min }}.*, "*"]`. Avoids
the TEST-002 optimizer warning. The generator emits this by default
as of v8.8.0.

### FR-6. Run-dep audit via `check_dependencies` before submission

Every recipe runs `check_dependencies` against conda-forge before
`submit_pr`. Any "missing" hit triggers the 4-spelling
verification per SKILL.md G10. Truly-missing deps either get a
prerequisite mini-recipe in the same wave or get dropped from `run:`
with a documented TODO (preferred default: package the prerequisite,
unless the dep is genuinely peripheral).

### FR-7. License compliance per SKILL.md "Canonical License-File Placement"

Pattern 1 (`license_file: LICENSE` from extracted source) when
upstream's archive ships LICENSE — true for every story here.
No secondary-source LICENSE fetches expected (none of the stories
match G4 — sdist-missing-license — based on the audit).

### FR-8. PR body cites upstream Microsoft repo + license + the conda-forge-expert version that authored the recipe

Standard PR body template — already encoded in the skill's `submit_pr`
behavior; included in this FR for explicitness.

---

## Technical Approach

### Recipe slug convention

| Story | Recipe slug | PyPI/crate name | Conda package name | Top-level import (Python) |
|---|---|---|---|---|
| S1 | `microsoft-edit` | `edit` (crate) | `microsoft-edit` (or `msedit` per Q3) | n/a (CLI) |
| S2 | `agent-framework` | `agent-framework` | `agent-framework` | `agent_framework` |
| S3 | `pyqlib` | `pyqlib` | `pyqlib` | `qlib` |
| S4 | `pyrit` | `pyrit` | `pyrit` | `pyrit` |
| S5 | `promptflow-tracing` | `promptflow-tracing` | `promptflow-tracing` | `promptflow.tracing` |
| S6 | `promptflow-core` | `promptflow-core` | `promptflow-core` | `promptflow.core` |
| S7 | `promptflow-devkit` | `promptflow-devkit` | `promptflow-devkit` | `promptflow.devkit` (verify) |
| S8 | `promptflow` | `promptflow` | `promptflow` | `promptflow` |
| S9 | `semantic-kernel` | `semantic-kernel` | `semantic-kernel` | `semantic_kernel` |
| S10 | `torchscale` | `torchscale` | `torchscale` | `torchscale` |
| S11 | `promptwizard` | TBD per Q1 | TBD | TBD |
| S12 | `microsoft-seal` | n/a (CMake) | `microsoft-seal` | n/a (C++ lib) |
| S13 | `diskann` | n/a (CMake + pybind11) | `libdiskann` + `diskannpy` | `diskannpy` |

The `microsoft-edit` and `microsoft-seal` slugs disambiguate from
generic names already taken or likely to collide elsewhere on
conda-forge. The `pyqlib` slug matches PyPI canonical (recipe author
does NOT silently rename to `qlib` — that would diverge from upstream
and break autotick).

### Wave 1 execution order (parallel-safe)

S1, S2, S3, S4 have **no internal dependencies**. Submit in parallel.
S2's run-dep on `agent-framework-core` is already satisfied (existing
feedstock at 1.8.0; upstream is 1.8.1 so an autotick lands in days —
or S2 can include a same-PR bump request via a feedstock PR).

### Wave 2 dependency graph

```
S5 (promptflow-tracing) ──┐
                          ├──> S6 (promptflow-core) ─┐
                          │                          ├──> S8 (promptflow umbrella)
                          └─────────────────────────┐│
                                                    ├─> S7 (promptflow-devkit) ────┘
                                                    │
S9 (semantic-kernel)   — independent of S5–S8
S10 (torchscale)       — independent of S5–S9
S11 (promptwizard)     — gated on Q1, independent of S5–S10
```

Wave 2 cannot merge S6 / S7 / S8 until S5 lands on conda-forge
(autotick won't help; `check_dependencies` requires it). But
*submission* of S6 / S7 / S8 to staged-recipes can proceed as soon as
S5 is in review (the staged-recipes review queue is multi-day per PR
anyway).

### Wave 3 sequencing

S12 (SEAL) before S13 (DiskANN) — DiskANN may benefit from
SEAL-precedent for CMake-style C++ recipes in this repo's history.
S14 retro waits on all of Wave 1 + Wave 2 + S12 + S13 reaching a
terminal state (merged / on-hold / explicitly deferred).

### Sub-workflow for each Python story

Standard 9-step autonomous loop from `conda-forge-expert` SKILL.md.
No deviations. The skill's `generate_recipe_from_pypi` does the
heavy lifting for steps 1–3; the per-story acceptance criteria above
spell out the manual edits expected after generation (mostly:
dep-name fixes per G10, CFEP-25 test triad if generator missed it,
LICENSE handling).

### Sub-workflow for each Rust / C++ story

S1 follows the canonical Rust CLI template directly. S12 + S13
require manual hand-authoring — the existing skill template
`templates/rust/library-recipe.yaml` doesn't cover CMake C++
projects. S14 retro should consider adding a `templates/cpp/cmake-library-recipe.yaml`
based on whatever pattern S12 settles on (handoff for future
similar packaging efforts).

---

## Acceptance Criteria (Whole Feature)

- **AC-1.** 10–14 staged-recipes PRs are open or merged
  (depending on Q1 outcome for S11 and whether S13's Windows skip
  becomes a 2-PR split): one per story S1–S13. Each addresses every
  bot-lint, conda-smithy-lint, and reviewer comment.
- **AC-2.** All Python recipes build green on at least `linux-64`
  in conda-forge CI. S1 (microsoft-edit) builds green on linux-64,
  osx-64, osx-arm64, win-64. S12 (SEAL) and S13 (DiskANN) build green
  on the platforms in their respective matrices (S13 may legitimately
  skip win-64 in v1).
- **AC-3.** `pip check` passes for every noarch:python recipe's test
  stage.
- **AC-4.** Each shipped recipe is installable in a fresh pixi env:
    - `pixi add microsoft-edit && edit --version` succeeds.
    - `pixi add agent-framework && pixi run python -c "import agent_framework"` succeeds.
    - `pixi add pyqlib && pixi run python -c "import qlib"` succeeds.
    - `pixi add pyrit && pixi run python -c "import pyrit"` succeeds.
    - …same for every other shipped recipe and its primary import.
- **AC-5.** S11 has either (a) shipped (Q1 resolves to "yes, packageable"
  and the PR lands), or (b) been explicitly deferred with rationale
  filed in `deferred-work.md`.
- **AC-6.** S14 retro is filed at
  `_bmad-output/projects/local-recipes/implementation-artifacts/retro-microsoft-conda-forge-<date>.md`.
  Any novel gotchas land in SKILL.md / reference/ / guides/ + a
  CHANGELOG entry.
- **AC-7.** Spec status at top updated to **Shipped <date>** with
  merge SHAs / PR links for each landed recipe.

---

## Open Questions

### Q1 (gates S11) — Does Microsoft PromptWizard ship a PyPI artifact?

The bare PyPI `promptwizard` 1.0.0 belongs to a different upstream
(summary: "Prompt Wizard is a package for evaluating custom prompts
using various evaluation methods"). Microsoft's PromptWizard
(`github.com/microsoft/PromptWizard`, 3.9k★) needs investigation:

- Does Microsoft publish under a different PyPI name? (e.g.,
  `ms-promptwizard`, `microsoft-promptwizard`, `pyromptwizard`.)
- Is it intended as `git clone + pip install -e .` only? (Common
  for research-attached repos.)
- Does upstream maintain a wheel anywhere?

**Default if Q1 resolves negative**: defer S11 to a follow-on spec
(filed in `deferred-work.md`). Do not silently mis-package the bare
PyPI `promptwizard`.

**Investigation**: in S5's first 30 min, run
`WebFetch https://pypi.org/simple/?q=promptwizard` and
`gh search code 'pyproject.toml name "promptwizard"' repo:microsoft/PromptWizard`
to confirm.

### Q2 (gates S13) — Does microsoft/DiskANN have a clean Windows build path?

Upstream's README claims Windows support, but the build invokes Intel
MKL paths that may need recipe-side massaging on conda-forge's MSVC
toolchain. Three options:

- **A**: Skip win-64 in v1; document; add as a follow-on PR when MKL
  CMake config is confirmed.
- **B**: Block S13 on win-64 working — risks the entire DiskANN
  packaging effort on a Windows-only obstacle.
- **C**: Drop MKL dependency; fall back to OpenBLAS on every
  platform — uniform but may underperform vs. upstream.

**Default**: **A**. Document the win-64 skip in the recipe's
top-of-file comment + the PR body. Follow-on Windows PR is a
separate effort.

### Q3 (gates S1) — `microsoft-edit` binary name + recipe slug

Upstream's WinGet manifest installs the binary as `msedit`. Linux/macOS
Homebrew install it as `edit`. The conda recipe must pick one:

- **Option A**: Recipe slug `microsoft-edit`; binary `edit`. Matches
  the linux/macOS convention. Risks shadowing whatever other `edit`
  is in the user's PATH (typically system POSIX `ed`/`ex`/`vi` —
  not actually conflicting).
- **Option B**: Recipe slug `microsoft-edit`; binary `msedit`.
  Matches the Windows convention. Avoids any PATH conflict risk.
- **Option C**: Ship both — `bin/edit` + `bin/msedit` (symlink one
  to the other). Most user-friendly; minor recipe complexity.

**Default**: **C**. The Cargo build emits one binary; the recipe
post-install drops a `msedit` → `edit` symlink (or vice versa on
Windows where symlinks need privilege; alt: ship `msedit.cmd` that
calls `edit.exe`). Document the rationale in the recipe header
comment.

---

## Dependencies and Constraints

### External dependencies that must already exist on conda-forge

Verified via spot-check during the June 2026 audit; subject to
re-verification per-story:

Common across stories: `numpy`, `pandas`, `pydantic`, `pydantic-settings`,
`pytorch`, `transformers`, `tiktoken`, `openai`, `azure-core`,
`azure-identity`, `aiohttp`, `httpx`, `fastapi`, `starlette`,
`uvicorn`, `websockets`, `tenacity`, `jinja2`, `pyyaml`,
`python-dotenv`, `typing-extensions`, `opentelemetry-api`,
`opentelemetry-sdk`, `cmake`, `ninja`, `pkg-config`, `ms-gsl`,
`zlib`, `zstd`, `boost`, `mkl` (optional), `openblas`.

Specific to stories: `agent-framework-core` (S2, exact-version
pin); `mlflow`, `lightgbm` (S3); `azure-ai-projects`,
`azure-ai-agents`, `mcp`, `aiortc`, `pybars4`, `prance` (S9);
`Microsoft.GSL` (= `ms-gsl`, S12); `pybind11` (S13).

### External dependencies likely NOT on conda-forge — handled per-story

| Likely missing | Story | Resolution |
|---|---|---|
| `base2048`, `ecoji`, `segno`, `art`, `tinytag`, `treelib`, `confusable-homoglyphs` | S4 (pyrit deps) | Audit during S4; package as S4-prereq mini-PRs if needed |
| `microsoft-agents-copilotstudio-client` | S9 (semantic-kernel extra) | Drop from `run_constraints:` with TODO; document |
| Any DiskANN-specific BLAS shim | S13 | Investigate during S12 → S13 transition; may need a recipe-side patch |

### Upstream constraints

- All listed upstreams are MIT or Apache-2.0 (verified June 2026).
- All Python recipes target `python_min: "3.10"` (conda-forge floor;
  upstream py_min may be lower but conda-forge dropped 3.9 in Aug
  2025).
- microsoft/edit ships GitHub release binaries; conda recipe
  source-builds from the tag tarball (standard for Rust CLIs).
- microsoft/SEAL v4.1.x is the chosen baseline. CMake 3.22+.
- microsoft/DiskANN's current main is the baseline; tag a recent
  release at story start.

### conda-forge constraints

- Standard staged-recipes review queue (multi-day per PR).
- linux-64 is mandatory; per-platform recipes (S1, S12, S13) also
  build osx-64, osx-arm64, and (per Q2) win-64.
- macOS deployment target ≥ 11.0 (conda-forge floor, Feb 2026 policy).
- Build time limit 6 h on Azure Pipelines (none of these stories
  approach it).

---

## Out of Scope (Explicit)

The following are deliberately excluded from this spec, with reason:

| Repo | Reason |
|---|---|
| microsoft/vscode | Vendor-distributed (own installer + auto-updater); not appropriate for conda-forge. |
| microsoft/TypeScript | Already on conda-forge (`typescript` 6.0.2). |
| microsoft/playwright + playwright-python | Already on conda-forge. |
| microsoft/onnxruntime | Already on conda-forge. |
| microsoft/LightGBM | Already on conda-forge. |
| microsoft/DeepSpeed | Already on conda-forge. |
| microsoft/autogen (all variants) | Already on conda-forge (`autogen-agentchat`, `autogen-core`, `pyautogen`). |
| microsoft/markitdown | Already on conda-forge. |
| microsoft/graphrag | Already on conda-forge. |
| microsoft/presidio | Already on conda-forge. |
| microsoft/pyright | Already on conda-forge. |
| microsoft/FLAML | Already on conda-forge. |
| microsoft/torchgeo | Already on conda-forge (community-maintained). |
| microsoft/agent-framework-core | Already on conda-forge (1.8.0) — only the umbrella `agent-framework` needs adding (= S2). |
| microsoft/Agents (M365), microsoft/kiota* | Already on conda-forge from this repo's May 2026 work. |
| microsoft/typescript-go | Upstream not yet 1.0; defer. |
| microsoft/BitNet | Multi-week C++ build; separate spec when prioritized. |
| microsoft/recommenders | Wide extras tree; evaluate post Wave-2 closure (Wave-3 candidate). |
| microsoft/VibeVoice | Upstream withdrew code in 2025; no stable artifact to track. |
| microsoft/PowerToys + every Windows-only repo (terminal, calculator, WSL, winget-cli, react-native-windows, microsoft-ui-xaml, WindowsAppSDK, wil, sudo, coreutils, hcsshim, …) | Native Win32; no Linux/macOS build path. |
| microsoft/garnet, aspire, kiota (CLI), perfview, fluentui-blazor, every .NET-centric repo | conda-forge doesn't ship the .NET runtime. |
| microsoft/JARVIS, Swin-Transformer, Bringing-Old-Photos-Back-to-Life, BioGPT, MMdnn, OmniParser, CodeBERT, fara, Webwright, SkillOpt, LMOps, table-transformer, TRELLIS, promptbase, muzic, unilm | Research code without library shape; users `git clone` rather than `pip install`. |
| Every `*-for-beginners`, mcp-for-beginners, RustTraining, ai-edu, AcademicContent, Mastering-GitHub-Copilot-for-Paired-Programming, workshop-library, AI-System | Docs/training; no installable artifact. |
| microsoft/monaco-editor, fluentui, fast, FluidFramework, SandDance, reactxp | Browser-only npm libs; npm is the right channel. |
| microsoft/cascadia-code, fluentui-emoji | Fonts/assets; separate distribution channels apply; some licensing complications. |
| microsoft/azurelinux | Linux distribution, not a package. |
| microsoft/AirSim, DirectX-Graphics-Samples, DirectXShaderCompiler | Game-engine / graphics-stack specific; channel-fit mismatch. |
| microsoft/SPTAG | Alternative to DiskANN; cover one ANN library this round (DiskANN). SPTAG is a future-spec candidate if user demand surfaces. |
| microsoft/retina | Kubernetes eBPF; operator-channel territory, not conda-forge. |
| microsoft/pg_durable | Postgres extension; different channel ecosystem. |
| microsoft/ethr | Single-binary Go CLI — viable conda-forge candidate but `iperf3` already covers the use case; defer unless user demand surfaces. |
| Archived repos (CNTK, nni, TaskWeaver, com-rs, napajs, cpprestsdk, bond, BosqueLanguage, ELL, …) | Upstream signals do-not-package. |

---

## References

### Internal

- `.claude/skills/conda-forge-expert/SKILL.md` — Operating Principles,
  Critical Constraints, 10-step autonomous loop, Build Failure
  Protocol, G1–G15 gotchas, Rust CLI standards, Python Version Policy.
- `.claude/skills/conda-forge-expert/templates/rust/cli-recipe.yaml`
  — S1 template.
- `.claude/skills/conda-forge-expert/templates/python/noarch-recipe.yaml`
  — S2–S11 base template.
- `.claude/skills/conda-forge-expert/templates/multi-output/lib-python-recipe.yaml`
  — S8 (promptflow umbrella shape), S13 (DiskANN multi-output shape).
- `docs/specs/db-gpt-conda-forge.md` — closest-precedent packaging
  effort spec; multi-recipe wave pattern adopted here.
- `_bmad-output/projects/local-recipes/implementation-artifacts/retro-npm-and-microsoft-bundles-2026-05-17.md`
  — prior retro from the Microsoft Agents bundle; informs S2 patterns.
- `~/.claude/projects/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/memory/feedback_pypi_conda_mapping_unreliable.md`
  — live cross-skill reference for G10 dep-name verification, gates
  S3/S4/S9 audits.

### Upstream

- `github.com/microsoft/edit` v2.0.0 — S1.
- `github.com/microsoft/agent-framework` + PyPI `agent-framework`
  1.8.1 — S2.
- `github.com/microsoft/qlib` + PyPI `pyqlib` 0.9.7 — S3.
- `github.com/microsoft/PyRIT` + PyPI `pyrit` 0.14.0 — S4.
- `github.com/microsoft/promptflow` + PyPI `promptflow` 1.18.5 +
  `promptflow-{tracing,core,devkit}` — S5–S8.
- `github.com/microsoft/semantic-kernel` + PyPI `semantic-kernel`
  1.43.0 — S9.
- `github.com/microsoft/torchscale` — S10.
- `github.com/microsoft/PromptWizard` — S11 (gated on Q1).
- `github.com/microsoft/SEAL` v4.1.x — S12.
- `github.com/microsoft/DiskANN` — S13.

### conda-forge

- `conda-forge.org/docs/maintainer/example_recipes/rust/` — canonical
  Rust CLI pattern (S1).
- `conda-forge.org/docs/maintainer/example_recipes/pure-python/` —
  canonical noarch:python pattern (S2–S11).
- `conda-forge.org/docs/maintainer/example_recipes/cpp/` (or the
  general CMake guidance) — S12 / S13.
- `conda-forge/staged-recipes` — submission target for every story.

---

## Suggested BMAD Invocation

```
@bmad-quick-dev — implement the intent in docs/specs/microsoft-conda-forge.md.

Wave 1 first (S1–S4 in parallel). Confirm Q3 (microsoft-edit binary
name) before S1 lands. Run the conda-forge-expert 10-step autonomous
loop per recipe.

When Wave 1 PRs are all in staged-recipes review, proceed to Wave 2
(S5–S11). Investigate Q1 (PromptWizard PyPI presence) during S5; if
negative, defer S11 to deferred-work.md and reduce Wave 2 to 6
stories.

When Wave 2 is in review, proceed to Wave 3 (S12–S13). Resolve Q2
(DiskANN win-64) at S13 start; default to skipping win-64 with TODO.

After all PRs reach terminal state, run S14 closeout retro per
SKILL.md always-on Rule 2. Update this spec's Status header to
Shipped <date> with merge SHAs.
```
