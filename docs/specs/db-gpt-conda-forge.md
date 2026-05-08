# Tech Spec: DB-GPT on conda-forge

> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow track —
> bounded scope, packaging effort, ~9 implementation stories spanning 1–3
> staged-recipes PRs).
> Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/db-gpt-conda-forge.md
> ```

---

## Status

| Field | Value |
|---|---|
| Status | **Draft v1** — ready for `bmad-quick-dev` intake; one open question (Q1) blocks story finalization |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (tech-spec only, no PRD/architecture phase) |
| Upstream | `eosphoros-ai/DB-GPT` v0.8.0 (released 2026-03-27, MIT license) |
| Target | `conda-forge/staged-recipes` — 7 outputs in a single multi-output recipe, plus 7 prerequisite recipes (3 trivial pure-Python, 3 itkwasm-pattern noarch, 1 cocoindex-class Rust+PyO3) |
| Distribution | conda-forge (linux-64, osx-64, osx-arm64, win-64) — `noarch: python` for all outputs |
| Lifetime | Long-running — feedstocks become autotick-maintained after first PR lands |

---

## Background and Context

### The problem

DB-GPT (`eosphoros-ai/DB-GPT`) is a Python LLM-application platform with a
broad user base. There is currently no conda-forge feedstock and no prior
staged-recipes PR. Without packaging:

- Users in conda-managed / air-gapped environments cannot install DB-GPT
  through their channel — they fall back to pip, which breaks
  reproducibility and JFrog Artifactory mirroring.
- The repo's pinned application-style dependencies (`aiohttp==3.8.4`,
  `pandas==2.2.3`, `psutil==5.9.4`, etc.) silently downgrade conda-forge
  packages when installed via pip on top of a conda env.
- Sibling tooling that depends on `dbgpt` (e.g., notebooks, agent
  scaffolding) cannot pin to conda-forge SHAs.

### What's been investigated and ruled out

- **Single-package "just `dbgpt` core" submission.** Considered; rejected
  because it leaves `dbgpt-client`, `dbgpt-ext`, `dbgpt-serve`,
  `dbgpt-app`, `dbgpt-acc-auto`, `dbgpt-sandbox` strands on PyPI-only
  while their parent Python imports cross-reference each other. A
  multi-output recipe is closer to upstream's intent (uv workspace, all
  members release together at the same version).

- **Full prerequisite chain to enable `dbgpt-app`'s `[code]` extra.** The
  `code` extra hard-pulls `lyric-py`, `lyric-py-worker`, `lyric-js-worker`,
  `lyric-component-ts-transpiling`. The PyPI sdists for the three worker
  packages ship pre-compiled WASM blobs (`python_worker.wasm`, 28 MB)
  wrapped in a Python shim — the sdist size matches the wheel size
  because it _is_ the binary. Conda-forge would reject building from those
  vendored sdists.

  Deeper investigation of the upstream `lyric-project/lyric-runtime` repo
  (24★, MIT, Bytecode Alliance ecosystem) confirms all five Python
  packages have full first-party source and a published Makefile-driven
  build process. The workers rebuild from source via the toolchain
  surveyed in **§ "WASM toolchain on conda-forge"** below; this section
  states the bottom line.

  | Package | Build dependency | conda-forge status |
  |---|---|---|
  | `lyric-task` | pure Python | trivial — already pip-installable |
  | `lyric-py` | maturin + protoc | feasible — `protobuf` 6.33 on conda-forge |
  | `lyric-py-worker` | `componentize-py` + `wasm-tools` | both **NOT on conda-forge** |
  | `lyric-js-worker` | `nodejs` + `@bytecodealliance/jco` (npm) | jco **NOT on conda-forge** |
  | `lyric-component-ts-transpiling` | `cargo build --target wasm32-wasip1` | `rust-std-wasm32-wasip1` **NOT on conda-forge** (only `wasm32-unknown-unknown` and `wasm32-unknown-emscripten` are shipped) |

  Two paths exist for shipping the workers on conda-forge:
  - **Vendor the upstream `.wasm` blob** as a `noarch: python` recipe
    (the `itkwasm-downsample-wasi` precedent on main conda-forge —
    see § "WASM toolchain on conda-forge — current state" for the full
    pattern). Each worker recipe is ~30 lines; the only runtime
    requirement is `wasmtime-py` (already on conda-forge), which
    ships `_libwasmtime.so` inside the conda artifact. **This is the
    realistic path.**
  - **Rebuild the `.wasm` from source** by upstreaming the WASI-side
    Bytecode Alliance toolchain (`wasi-sdk`, `wasm-tools`,
    `componentize-py`, `jco`) plus adding `rust-std-wasm32-wasip1`
    to `rust-feedstock`. Net-new packaging work in a domain conda-forge
    has only recently begun to support; not required given the
    vendoring precedent.

  Q1's `B-full` option uses the vendor-the-blob path and is multi-day,
  not multi-week.

- **`dbgpt-acc-flash-attn` accelerator.** Not pulled by `dbgpt-app`'s base
  dependencies (only `dbgpt-acc-auto` is). flash-attn itself is heavy
  (CUDA-only, GPU-tier). Out of scope for this v1 effort.

### WASM toolchain on conda-forge — current state

The following audit is the basis for Q1's `B-full` cost estimate.
References: `https://prefix.dev/blog/pixi_wasm` (rattler-build native
WASM support announcement); `https://github.com/pyodide/pyodide/issues/795`
(closed, 2020 — Pyodide on conda-forge integration ruled out, leading
to the parallel `emscripten-forge` distribution).

**Runtimes and bindings on conda-forge already (✓):**

| Package | Version | Origin | Purpose |
|---|---|---|---|
| `wasmtime-py` | 44.0.0 | Bytecode Alliance | Python embedding of Wasmtime — bundles `_libwasmtime.so` (the runtime) inside the conda artifact, so installing this gives you both the Python API *and* the Wasmtime engine |
| `wasmer` | 7.1.0 | Wasmer | Standalone Wasmer CLI/runtime |
| `python-wasmer` | 1.1.0 | Wasmer | Wasmer Python bindings |
| `python-wasmer-compiler-{cranelift,llvm,singlepass}` | 1.1.0 | Wasmer | Compiler-backend variants |

**Build tools on conda-forge already (✓):**

| Package | Version | Origin | Purpose |
|---|---|---|---|
| `emscripten` | 4.0.9 | Emscripten | C/C++ → wasm32-emscripten via emcc |
| `emsdk` | 3.1.46 | Emscripten | SDK manager |
| `binaryen` | 121 | WebAssembly CG | WASM optimizer (used by emscripten) |
| `wabt` | 1.0.41 | WebAssembly CG | WebAssembly Binary Toolkit (`wasm2wat`, `wat2wasm`) |
| `wasm-pack` | 0.14.0 | Rust+WebAssembly WG | Rust → WASM packager |
| `pyodide-build` | 0.34.3 | Pyodide | Pyodide build infrastructure |
| `pyodide-py` | 0.22.0 | Pyodide | Pyodide Python helpers |
| `micropip` | 0.11.1 | Pyodide | In-browser pip emulator |
| `rust-std-wasm32-unknown-unknown` | 1.95.0 | Rust | Rust target — bare WASM, no syscalls |
| `rust-std-wasm32-unknown-emscripten` | 1.95.0 | Rust | Rust target — emscripten ABI |
| `cargo-c` | 0.10.22 | Rust | Cargo C-API subcommand (peripheral) |

**Existing WASI-target packages on conda-forge (the precedent that
matters):**

| Package | Version | Pattern |
|---|---|---|
| `itkwasm` | 1.0b195 | Python wrapper over wasmtime-py — `_libwasmtime.so` is built into wasmtime-py, so itkwasm runs WASI binaries without needing wasi-sdk |
| `itkwasm-downsample` | 1.8.1 | Pure-Python loader; depends on `itkwasm` + `itkwasm-downsample-wasi` |
| `itkwasm-downsample-wasi` | 1.8.1 | **`noarch: python`. Just `pip install`s the upstream PyPI sdist that ships the pre-built `.wasm` blob.** Recipe is ~30 lines. |
| `itkwasm-downsample-emscripten` | 1.8.1 | Emscripten variant — same pattern, different blob |

The **`itkwasm-downsample-wasi` recipe is the load-bearing precedent
for Lyric.** It demonstrates that conda-forge accepts a noarch Python
package whose PyPI sdist contains a pre-built `.wasm` binary, when:

1. The runtime that *executes* the WASM (here, `wasmtime-py`) is
   itself built from source on conda-forge, and
2. Upstream maintains a reproducible WASM build via their own CI, and
3. The `.wasm` is treated as a packaged data asset (analogous to
   shipping a `.so` inside a Python wheel — which conda-forge already
   accepts when sourced from the upstream wheel).

Maintainers `khaled196` and `thewtex` (InsightSoftwareConsortium) have
pushed multiple `*-wasi` and `*-emscripten` packages through
staged-recipes review without escalation. There is no public reviewer
write-up of the policy, but the pattern has stuck.

**Tools NOT on conda-forge today (only relevant if rebuilding the
`.wasm` blobs from source rather than vendoring them via the itkwasm
pattern):**

| Tool | Origin | Source-build use |
|---|---|---|
| `wasmtime` (standalone CLI) | Bytecode Alliance | Run/test WASI binaries outside Python — `wasmtime-py` already provides the runtime library, so this is rarely needed |
| `wasi-sdk` | WebAssembly CG | C/Rust → wasm32-wasi compilation |
| `wasi-libc` | WebAssembly CG | Standalone WASI libc |
| `wasm-tools` | Bytecode Alliance | `wasm-tools strip` / `wasm-tools component new` — used by upstream `lyric-py-worker` Makefile |
| `componentize-py` | Bytecode Alliance | Python → WASM Component packager — used by upstream `lyric-py-worker` Makefile |
| `jco` | Bytecode Alliance (npm) | JavaScript Component Tools — used by upstream `lyric-js-worker` Makefile |
| `wit-bindgen` | Bytecode Alliance | Component interface generator |
| `cargo-component` | Bytecode Alliance | Cargo subcommand for WASM Component Model |
| `rust-std-wasm32-wasi` / `wasm32-wasip1` / `wasm32-wasip2` | Rust | Rust target — required for `cargo build --target wasm32-wasi*` |

**Why emscripten doesn't help here.** Lyric's workers target **WASI
Preview 1** (`wasm32-wasip1`), not Emscripten. The two ABIs are not
interchangeable — emscripten uses JS shims for syscalls
(browser-oriented), while WASI uses component-model interfaces
(server/standalone-runtime-oriented). The `emscripten-forge` channel
(`github.com/emscripten-forge/recipes`, 82★) hosts emscripten-built
packages and isn't relevant. The relevant precedent is the
`itkwasm-downsample-wasi` family on **main conda-forge**.

**rattler-build supports `emscripten-wasm32` and `wasi-wasm32` build
platforms natively** (per the prefix.dev pixi_wasm announcement), so
recipe-format support exists if a future submission ever needs to
compile WASM from C/Rust source on conda-forge CI itself.

**Bottom line — the itkwasm precedent reframes B-full.** The lyric-*
workers can be packaged as ~30-line `noarch: python` recipes that
vendor the upstream PyPI sdist's pre-built `.wasm`, with `wasmtime-py`
(or whatever runtime `lyric-py` links) supplying the engine. No
componentize-py, no jco, no wasi-sdk, no rust-std-wasm32-wasip1 —
those are only required if we choose to rebuild the WASM artifacts
from source, which conda-forge has not historically required for this
class of package. The `B-full` cost estimate drops from "≥13 PRs,
multi-week, includes Bytecode Alliance toolchain upstreaming" to
"~8 PRs, of which only `lyric-py` (Rust+maturin+protoc, cocoindex-class)
is non-trivial. The 3 worker recipes are each ~30 lines following the
`itkwasm-downsample-wasi` template."

### What's available to leverage

- **`conda-forge-expert` skill v6.x** at
  `.claude/skills/conda-forge-expert/` already provides
  `generate_recipe_from_pypi`, `validate_recipe`, `optimize_recipe`,
  `check_dependencies`, `scan_for_vulnerabilities`, `trigger_build`, and
  `submit_pr`. Each of the recipes in this spec runs the full 9-step
  autonomous loop without manual intervention.

- **Existing pin-loosening memory entry** at
  `feedback_loosen_pins.md` — when an exact-pin upstream dep is not
  available on conda-forge at that exact version, loosen to `>=N` and
  add a `# TODO: tighten once N.x is available` comment.

- **Existing v0↔v1 about-field mapping memory** at
  `reference_v0_v1_about_fields.md` — every output in the multi-output
  recipe must use v1 names (`homepage`, `repository`, `documentation`).

- **Existing canonical recipe patterns** in the skill's
  `templates/multi-output/lib-python-recipe.yaml` — directly applicable
  to the DB-GPT 6/7-output recipe.

---

## Goals

- **G1.** Land all 7 dbgpt-* outputs (`dbgpt`, `dbgpt-client`,
  `dbgpt-ext`, `dbgpt-serve`, `dbgpt-app`, `dbgpt-acc-auto`,
  `dbgpt-sandbox`) on conda-forge as a single multi-output recipe in
  `recipes/db-gpt/`, plus 7 prerequisite recipes. Coherent = all
  outputs share the same source archive, same version, and resolve
  their internal `dbgpt-*` cross-dependencies via `pin_subpackage`.
- **G2.** Use upstream's GitHub source archive (`v${{version}}.tar.gz`)
  for the DB-GPT multi-output, not 7 separate PyPI sdists. The 7
  prerequisite recipes each source from PyPI individually (or from the
  upstream `lyric-project/lyric-runtime` archive for `lyric-py`).
- **G3.** Package as `noarch: python` for every dbgpt-* output and
  every lyric-* worker (the latter following the
  `itkwasm-downsample-wasi` precedent — vendor the upstream sdist's
  pre-built `.wasm` blob). `lyric-py` is the only platform-specific
  recipe (Rust+PyO3).
- **G4.** Loosen all upstream `==` pins to `>=` per the project's
  pin-loosening convention. Document each loosening with an inline
  `# TODO` comment naming the upstream pin.
- **G5.** dbgpt-app feature parity — the `[code]` extra resolves
  cleanly because every lyric-* dep lands on conda-forge. No recipe-
  side patches against upstream `dbgpt-app/pyproject.toml`.
- **G6.** Surgical scope: do not touch the existing `cocoindex` recipe
  workflow, do not introduce new skill scripts. Do follow the cocoindex
  PR #33231 authoring patterns when writing the `lyric-py` recipe.

## Non-Goals

- **NG1.** No `dbgpt-acc-flash-attn` recipe — CUDA-only, GPU-tier, not
  pulled by `dbgpt-app`'s base. Defer indefinitely.
- **NG2.** No upstream PR to DB-GPT to soften the pinned dependencies.
  Loosening happens recipe-side only.
- **NG3.** No upstreaming of WASI-side Bytecode Alliance toolchain
  (`wasi-sdk`, `wasm-tools`, `componentize-py`, `jco`,
  `rust-std-wasm32-wasip1`) to conda-forge. The lyric-* worker recipes
  vendor the upstream PyPI sdist's pre-built `.wasm` per the itkwasm
  precedent — no source-rebuild required. If a reviewer rejects the
  vendor-the-blob pattern despite the precedent, the fallback is
  `B-six-plus-app-patched` (drop `dbgpt-app[code]`); upstreaming the
  full WASI toolchain is out of scope for this spec.
- **NG4.** No feedstock-level CI customization beyond what conda-forge
  provides by default. Standard `.ci_support` matrix; no `provider:`
  override.
- **NG5.** No PyPI-side coordination with eosphoros-ai or
  lyric-project for licensing cleanup, README updates, or sdist
  contents. Recipes absorb upstream artifacts as published.
- **NG6.** No Anaconda-channel mirror. conda-forge only.
- **NG7.** No recipe for `lyric-runtime` standalone (the umbrella Rust
  workspace). Only the published Python wrappers (`lyric-task`,
  `lyric-py`, the 3 workers) ship to conda-forge.

---

## Lifecycle Expectations

After the staged-recipes PR(s) merge, the following autopilot kicks in
without further effort from this spec:

- `regro-cf-autotick-bot` files autotick PRs on each new upstream tag.
- `conda-forge-webservices` runs lint and rerender on every PR.
- The feedstock(s) become canonical install paths for every dbgpt-*
  output we shipped.
- The `dbgpt-acc-flash-attn` accelerator (NG1) gets a future feedstock
  attempt only when CUDA infrastructure on conda-forge stabilizes —
  tracked in `_bmad-output/projects/local-recipes/
  implementation-artifacts/deferred-work.md`.

---

## User Stories

Q1 is resolved (**B-full** — see § "Open Questions"). 13 stories total.

**Execution waves** (parallelism within each wave is fine; the next
wave depends on the previous wave's PRs entering staged-recipes review
queue, not necessarily merging):

| Wave | Stories | Description |
|---|---|---|
| 1 | S1, S3 | Independent leaf recipes |
| 2 | S2, S4 | Depend on Wave 1 |
| 3 | S5, S6, S7 | Depend on S3 + S4 |
| 4 | S8–S12 | The DB-GPT multi-output recipe stories |

### Story S0 — Decide Q1 (`dbgpt-app` inclusion path)

**Status**: Resolved 2026-05-08 — **Decision: `B-full`**.

**Rationale**: The `itkwasm-downsample-wasi` precedent on main
conda-forge (verified at
`conda-forge/itkwasm-downsample-wasi-feedstock`) makes the lyric-*
worker recipes ~30 lines each — a `noarch: python` recipe that
pip-installs the upstream PyPI sdist whose contents include a pre-
built `.wasm` blob, with `wasmtime-py` (already on conda-forge,
44.0.0) supplying the runtime. This drops the B-full estimate from
"≥13 PRs, multi-week, includes upstreaming Bytecode Alliance
toolchain" to "8 PRs, multi-day, of which only `lyric-py` is
non-trivial". dbgpt-app feature parity (including the code-execution
sandbox) is worth the prerequisite chain at this cost.

**Fallback**: If a conda-forge reviewer rejects the vendor-the-blob
pattern for a lyric-* worker despite the precedent, drop the
offending worker(s) and switch the DB-GPT recipe to
`B-six-plus-app-patched` for the rejected extras (S12 fallback path
documented).

### Story S1 — Recipe: `abstract-singleton`

**Goal**: Land `abstract-singleton` (10 KB pure-Python, no deps) on
conda-forge as a prerequisite for `auto-gpt-plugin-template`.

**Acceptance criteria**:
- `recipes/abstract-singleton/recipe.yaml` validates clean.
- `optimize_recipe` reports zero check-code warnings.
- `pixi run -e local-recipes recipe-build recipes/abstract-singleton`
  produces an artifact under `build_artifacts/`.
- `submit_pr(recipe_name="abstract-singleton")` returns a `pr_url`.
- License resolved (PyPI metadata says `license:` empty — verify by
  reading `LICENSE` from sdist; expected MIT).

**Wave**: 1 (independent leaf).

**Estimated effort**: 30 min.

### Story S2 — Recipe: `auto-gpt-plugin-template`

**Goal**: Land `auto-gpt-plugin-template` (3 KB pure-Python, depends on
`abstract-singleton`) as the second prerequisite for `dbgpt[agent]`
inside `dbgpt-app`.

**Acceptance criteria**:
- `recipes/auto-gpt-plugin-template/recipe.yaml` validates clean.
- Run-deps include `abstract-singleton` (in conda-forge review queue
  via S1).
- License resolved (PyPI metadata empty — verify in sdist).
- Build + submit succeed.

**Wave**: 2.

**Blocked by**: S1 PR entering `staged-recipes` review queue.

**Estimated effort**: 20 min.

### Story S3 — Recipe: `lyric-task`

**Goal**: Land `lyric-task` (7 KB pure-Python; runtime helpers shared
across the lyric-* family). Required by `lyric-py` and all 3 lyric
workers.

**Acceptance criteria**:
- `recipes/lyric-task/recipe.yaml` validates clean.
- `noarch: python`.
- Source from PyPI (`lyric_task-0.1.7.tar.gz`).
- Run-deps: `cloudpickle`, `msgpack-python`.
- License: MIT (read from upstream `lyric-project/lyric-runtime`
  LICENSE; PyPI metadata says license None).
- `python_min: "3.10"` even though upstream allows 3.8 (conda-forge
  floor).
- Build + submit succeed.

**Wave**: 1 (independent leaf).

**Estimated effort**: 30 min.

### Story S4 — Recipe: `lyric-py` (cocoindex-class)

**Goal**: Land `lyric-py` (PyO3 Rust binding to the Lyric runtime;
embeds wasmtime via the Rust crate). The only non-trivial prerequisite.
Source-builds from the `lyric-project/lyric-runtime` workspace via
maturin.

**Acceptance criteria**:
- `recipes/lyric-py/recipe.yaml` validates clean.
- Source from upstream tag `pylyric-v0.1.7` (or whatever upstream tags
  for the 0.1.7 release — verify in `lyric-project/lyric-runtime`
  releases before commit; the PyPI sdist is also acceptable).
- Build deps: `${{ compiler('rust') }}`, `${{ compiler('c') }}`,
  `${{ stdlib('c') }}`, `maturin`, `protobuf` (provides protoc 28+),
  `pkg-config`.
- Host deps: `python`, `pip`, `maturin`.
- Run deps: `python >=3.10`, `msgpack-python`, `cloudpickle`,
  `${{ pin_compatible('lyric-task', max_pin='x.x') }}`.
- Per-platform build (NOT noarch) — wheel ships compiled extension
  `lyric/_py_lyric.so`.
- Build matrix: linux-64, linux-aarch64, osx-64, osx-arm64, win-64.
- Tests: `import lyric`, smoke test (instantiate a runtime, no
  network).
- Author following cocoindex PR #33231 patterns: single multi-line
  `then: |` for env-var-passing build steps; v1 about-field names;
  noarch where possible (not here).
- Build + submit succeed.

**Wave**: 2.

**Blocked by**: S3 PR entering `staged-recipes` review queue.

**Estimated effort**: 4–6 h. Cocoindex-class. Pitfalls: protoc version
mismatch, cross-platform Rust target setup, PyO3 ABI3 vs platform-
specific tags, `wasmtime` Rust crate's pre-built artifacts vs
source-build under conda-forge sysroot.

### Story S5 — Recipe: `lyric-py-worker` (itkwasm-pattern)

**Goal**: Land `lyric-py-worker` as a `noarch: python` recipe that
pip-installs the upstream PyPI sdist (which contains the pre-built
~28 MB `python_worker.wasm` blob). Pattern mirrors
`itkwasm-downsample-wasi-feedstock`.

**Acceptance criteria**:
- `recipes/lyric-py-worker/recipe.yaml` validates clean.
- `noarch: python`.
- Source from PyPI sdist (`lyric_py_worker-0.1.7.tar.gz`, 10.7 MB —
  contains pre-built `python_worker.wasm`, accepted per itkwasm
  precedent).
- Run-deps: `${{ pin_compatible('lyric-task', max_pin='x.x') }}`,
  `${{ pin_compatible('lyric-py', max_pin='x.x') }}`, `wasmtime-py`.
- License: MIT (read from upstream repo; PyPI metadata empty).
- Tests: `import lyric_py_worker`; verify the `.wasm` file exists
  inside the installed package directory; do not invoke the worker
  (would need a full WASI runtime test harness).
- PR body **must** cite the `itkwasm-downsample-wasi` precedent and
  link the recipe at
  `https://github.com/conda-forge/itkwasm-downsample-wasi-feedstock`
  to preempt reviewer pushback on the vendored binary.
- Build + submit succeed.

**Wave**: 3.

**Blocked by**: S3 (lyric-task) and S4 (lyric-py) entering review
queue.

**Estimated effort**: 45 min.

### Story S6 — Recipe: `lyric-js-worker` (itkwasm-pattern)

**Goal**: Land `lyric-js-worker` as a `noarch: python` recipe
following the same itkwasm pattern. Sdist contains a pre-built
JS-targeted `.wasm` (3.5 MB).

**Acceptance criteria**:
- `noarch: python`.
- Source from PyPI sdist (`lyric_js_worker-0.1.7.tar.gz`, 3.5 MB).
- Run-deps: `${{ pin_compatible('lyric-task', max_pin='x.x') }}`,
  `${{ pin_compatible('lyric-py', max_pin='x.x') }}`, `wasmtime-py`.
- Same license/test/PR-body pattern as S5.
- Build + submit succeed.

**Wave**: 3.

**Blocked by**: S3 and S4 entering review queue.

**Estimated effort**: 30 min.

### Story S7 — Recipe: `lyric-component-ts-transpiling` (itkwasm-pattern)

**Goal**: Land `lyric-component-ts-transpiling` as a `noarch: python`
recipe (1.8 MB sdist; smallest of the three itkwasm-pattern workers).

**Acceptance criteria**:
- `noarch: python`.
- Source from PyPI sdist
  (`lyric_component_ts_transpiling-0.1.7.tar.gz`).
- Run-deps: `${{ pin_compatible('lyric-task', max_pin='x.x') }}`,
  `${{ pin_compatible('lyric-py', max_pin='x.x') }}`, `wasmtime-py`.
- Same license/test/PR-body pattern as S5.
- Build + submit succeed.

**Wave**: 3.

**Blocked by**: S3 and S4 entering review queue.

**Estimated effort**: 30 min.

### Story S8 — Generate the multi-output DB-GPT recipe skeleton

**Goal**: Bootstrap `recipes/db-gpt/recipe.yaml` from the upstream
GitHub source archive (`v0.8.0.tar.gz`) using the multi-output
template at
`.claude/skills/conda-forge-expert/templates/multi-output/lib-python-recipe.yaml`.

**Acceptance criteria**:
- `recipes/db-gpt/recipe.yaml` exists with `schema_version: 1`.
- Top-level `source.url` points to
  `https://github.com/eosphoros-ai/DB-GPT/archive/v${{ version }}.tar.gz`.
- `source.sha256` computed fresh during this story.
- Seven `outputs:` entries: `dbgpt`, `dbgpt-client`, `dbgpt-ext`,
  `dbgpt-serve`, `dbgpt-acc-auto`, `dbgpt-sandbox`, `dbgpt-app`.
- Each output's `script:` is `cd packages/<member-name> && ${{ PYTHON }}
  -m pip install . --no-deps --no-build-isolation -vv` (note the
  `dbgpt`-PyPI-name-vs-`dbgpt-core`-source-dir asymmetry — see
  Technical Approach § "Internal name mapping").

**Wave**: 4.

**Estimated effort**: 45 min.

### Story S9 — Resolve internal cross-dependencies via `pin_subpackage`

**Goal**: Wire each output's `requirements.run` so internal `dbgpt-*`
references resolve to *this* recipe's outputs at the same build, not
to an unrelated upstream PyPI package.

**Acceptance criteria**:
- `dbgpt-ext` run-deps include
  `${{ pin_subpackage('dbgpt', exact=True) }}`.
- `dbgpt-client` run-deps include
  `${{ pin_subpackage('dbgpt', exact=True) }}` plus
  `${{ pin_subpackage('dbgpt-ext', exact=True) }}` (matches upstream
  `dbgpt[client,cli]` + `dbgpt_ext`).
- `dbgpt-serve` run-deps include
  `${{ pin_subpackage('dbgpt-ext', exact=True) }}`.
- `dbgpt-acc-auto` run-deps: empty (upstream `dependencies = []`).
- `dbgpt-sandbox` run-deps: external only (`psutil`, `colorama`,
  `docker-py`, `fastapi`, `uvicorn`, `pydantic`, `python-multipart`,
  `selenium`, `typing-extensions`).
- `dbgpt-app` run-deps include exact pins on `dbgpt`, `dbgpt-ext`,
  `dbgpt-serve`, `dbgpt-client`, `dbgpt-sandbox`, `dbgpt-acc-auto`,
  plus external `aiofiles`, `httpx >=0.24.0`, `pyparsing`, plus the
  lyric-* recipes from S5–S7 (+ S2's `auto-gpt-plugin-template`).

**Wave**: 4.

**Estimated effort**: 30 min.

### Story S10 — Loosen all `==` pins per project convention

**Goal**: Replace every upstream `package==X.Y.Z` pin with `package
>=X.Y.Z`, `package >=X.Y` (drop patch level), or a justified narrow
range, with an inline `# TODO: tighten once <pin> stays current`
comment per the `feedback_loosen_pins.md` rule.

**Acceptance criteria**:
- No `==` pins remain in any output's `requirements.run` except where
  upstream's API genuinely requires it (re-verify in upstream
  changelog before keeping any). Expected zero kept after audit.
- Each loosened pin has a TODO comment naming the original upstream
  pin verbatim (e.g., `# TODO: tighten once aiohttp==3.8.4 is no
  longer the upstream floor`).
- Pins that are already loose upstream (e.g., `pydantic>=2.6.0`) carry
  through unchanged.

**Pins to audit (non-exhaustive — the FR-2 list is the source of
truth)**:
`aiohttp==3.8.4`, `chardet==5.1.0`, `importlib-resources==5.12.0`,
`pandas==2.2.3`, `psutil==5.9.4`, `colorama==0.4.6`, `gTTS==2.3.1`,
`alembic==1.12.0`, `openpyxl==3.1.2`, `xlrd==2.0.1`,
`duckdb-engine==0.9.1`, `sqlparse==0.4.4`, `mysqlclient==2.1.0`,
`oracledb==3.1.0`, `spacy==3.7`, `tenacity<=8.3.0`,
`fastapi<0.113.0`, `numpy<2.0.0`, `onnxruntime<=1.18.1`.

**Wave**: 4.

**Estimated effort**: 1 h.

### Story S11 — License files

**Goal**: Each output ships the correct license file. The repo has a
single root `LICENSE` (MIT) and no per-package `LICENSE` files
(verified via API listing — all `packages/*/LICENSE` return 404).

**Acceptance criteria**:
- Top-level `about.license: MIT` (matches every output's
  `pyproject.toml`).
- Top-level `about.license_file: LICENSE` — single file, shared by
  all outputs.
- No per-output `about.license_file` overrides (rattler-build inherits
  the top-level value).

**Wave**: 4.

**Estimated effort**: 10 min.

### Story S12 — Validate, build, and submit DB-GPT multi-output

**Goal**: Run the full conda-forge-expert 9-step loop on the
multi-output recipe and submit the PR.

**Acceptance criteria**:
- `validate_recipe(recipe_path="recipes/db-gpt")`: zero errors, zero
  warnings.
- `optimize_recipe`: zero check-code warnings (especially STD-002
  format-mixing, ABT-002 v0/v1 about-field mismatch).
- `check_dependencies`: every external dep resolves on conda-forge,
  including the lyric-* recipes from S5–S7 (which must be in review
  queue or merged).
- `scan_for_vulnerabilities`: no Critical/High CVE; any Medium
  findings documented inline in the PR body.
- `trigger_build(mode="native")` produces all 7 artifacts on the host
  platform.
- `submit_pr(recipe_name="db-gpt", dry_run=True)` then
  `submit_pr(recipe_name="db-gpt")`.
- PR body cross-references S1–S7's PRs.

**Wave**: 4 (final story).

**Blocked by**: S1, S2, S3, S4, S5, S6, S7 PRs entering
`staged-recipes` review queue (do not need to fully merge first;
reviewers can sequence cross-PR).

**Fallback (if S5/S6/S7 are rejected)**: Switch DB-GPT to
`B-six-plus-app-patched` — add a recipe-side patch that strips the
rejected lyric-* references from `dbgpt-app/pyproject.toml` and ship
the 7-output recipe without those `[code]` extras. The patch is the
same minimal diff originally drafted for the patched-only path; carry
it in `recipes/db-gpt/patches/0001-drop-code-extra-from-dbgpt-app.patch`
only if needed.

**Estimated effort**: 1 h, plus async wait for CI.

---

## Functional Requirements

### FR-1: DB-GPT recipe sources from upstream GitHub archive, not PyPI sdists

A single `source.url:
https://github.com/eosphoros-ai/DB-GPT/archive/v${{ version }}.tar.gz`
keeps all 7 outputs in lockstep (same SHA, same version, same uv
workspace). Per-output PyPI sdists are not used here because they
de-couple the outputs and break the internal `dbgpt-*` cross-references
that `pin_subpackage(exact=True)` is meant to enforce. (The
prerequisite recipes S1–S7 each use their own PyPI sdist — that's
fine because they're independent feedstocks.)

### FR-2: Pin-loosening convention is mandatory

Every upstream `==` pin is loosened to `>=` (or a justified narrow
range) with a TODO comment naming the original upstream pin. This
matches `feedback_loosen_pins.md` and is enforced by the recipe
reviewer, not by the optimizer.

### FR-3: All DB-GPT outputs and all itkwasm-pattern lyric workers are `noarch: python`

No DB-GPT output requires a compiler — `noarch: python` shrinks the
build matrix to one job and matches every output's `pyproject.toml`
(no `[build-system] requires` beyond `hatchling`). The lyric workers
(S5–S7) are also `noarch: python` per the itkwasm precedent —
they pip-install upstream sdists that vendor pre-built `.wasm`. The
**only** non-noarch recipe in this entire effort is `lyric-py` (S4),
which is a per-platform Rust+PyO3 build.

### FR-4: v1 about-field names only

Every `about:` block uses `homepage`, `repository`, `documentation` —
never the v0 names `home`, `dev_url`, `doc_url`. This enforces the
`reference_v0_v1_about_fields.md` rule.

### FR-5: `python_min` floor is `3.10`

Matches every member's `requires-python = ">= 3.10"`. No override in
`context:` because `conda-forge-pinning` provides the default.

### FR-6: Internal cross-deps use `pin_subpackage(exact=True)`

Each `dbgpt-*` cross-reference inside the recipe pins to the exact
build of the same multi-output run, never to a generic version
constraint. This avoids accidental version drift between sibling
outputs that are conceptually one workspace.

### FR-7: License is single-file, top-level

`about.license: MIT` and `about.license_file: LICENSE` at the top
level. No per-output license overrides — every output is MIT and they
all share the root file.

### FR-8: No upstream patches in the happy path

The `B-full` happy path ships **no** patches against upstream
`dbgpt-app/pyproject.toml`. All extras (`code`, `agent`, etc.) resolve
because every transitive dep lands on conda-forge (S1–S7).

A patches/ directory is only authored if S5/S6/S7 are rejected during
review (S12 fallback) — in that case, exactly one patch ships under
`recipes/db-gpt/patches/0001-drop-code-extra-from-dbgpt-app.patch`,
the minimal diff that removes the `code` extra reference from
`dbgpt-app`. Authoring this patch is *contingent*; it is not part of
S8–S11.

---

## Technical Approach

### Stack

- **Recipe format**: rattler-build v1 (`schema_version: 1`).
- **Build backend**: each output uses upstream's `hatchling.build`
  unmodified. No custom build hooks.
- **Source**: upstream GitHub tarball at
  `https://github.com/eosphoros-ai/DB-GPT/archive/v0.8.0.tar.gz`.
  Compute the SHA256 fresh during S3 — do not paste from anywhere
  outside the recipe or upstream API.

### File layout (post-S12)

```
recipes/
  db-gpt/
    recipe.yaml              # the 7-output multi-output recipe
    patches/                 # only authored if S12 fallback fires
      0001-drop-code-extra-from-dbgpt-app.patch
  abstract-singleton/
    recipe.yaml
  auto-gpt-plugin-template/
    recipe.yaml
  lyric-task/
    recipe.yaml
  lyric-py/
    recipe.yaml
  lyric-py-worker/
    recipe.yaml
  lyric-js-worker/
    recipe.yaml
  lyric-component-ts-transpiling/
    recipe.yaml
```

### Output dependency graph

```
            ┌── dbgpt-acc-auto (no deps)
            │
            └── dbgpt (core)
                  ├── dbgpt-ext
                  │     └── dbgpt-serve
                  │
                  └── dbgpt-client
                        └── (joins dbgpt-app fan-in)

dbgpt-app ──── pin_subpackage(dbgpt, dbgpt-ext, dbgpt-serve,
                              dbgpt-client, dbgpt-sandbox,
                              dbgpt-acc-auto)
              + auto-gpt-plugin-template (run-only, external; from S2)
              + lyric-task, lyric-py, lyric-py-worker,
                lyric-js-worker, lyric-component-ts-transpiling
                (run-only, external; from S3-S7)

dbgpt-sandbox (no internal cross-deps; external runtime deps only)
```

### Build matrix

`noarch: python` collapses the matrix to one job (`linux-64`). Native
host build (step 7a in the skill's autonomous loop) is sufficient; no
Docker / CI-parity build needed because there are no native artifacts.

### Pin-loosening reference

The pins below are the audit list for Story S5. The "loosened to" column
is the proposed value subject to `check_dependencies` confirmation.

| Upstream pin | Loosened to | Notes |
|---|---|---|
| `aiohttp==3.8.4` | `aiohttp >=3.8.4` | conda-forge has 3.10+ |
| `chardet==5.1.0` | `chardet >=5.1.0` | |
| `importlib-resources==5.12.0` | `importlib_resources >=5.12.0` | hyphen→underscore for conda |
| `pandas==2.2.3` | `pandas >=2.2.3` | |
| `psutil==5.9.4` | `psutil >=5.9.4` | |
| `colorama==0.4.6` | `colorama >=0.4.6` | |
| `gTTS==2.3.1` | `gtts >=2.3.1` | conda name is lowercase |
| `alembic==1.12.0` | `alembic >=1.12.0` | |
| `openpyxl==3.1.2` | `openpyxl >=3.1.2` | |
| `xlrd==2.0.1` | `xlrd >=2.0.1` | |
| `duckdb-engine==0.9.1` | `duckdb-engine >=0.9.1` | |
| `sqlparse==0.4.4` | `sqlparse >=0.4.4` | |
| `mysqlclient==2.1.0` | `mysqlclient >=2.1.0` | |
| `oracledb==3.1.0` | `oracledb >=3.1.0` | |
| `spacy==3.7` | `spacy >=3.7` | |
| `tenacity<=8.3.0` | `tenacity >=8.0,<9` | upper bound retained — upstream uses ≤ |
| `fastapi<0.113.0` | `fastapi >=0.100.0,<1` | upper bound: drop the 0.113 cap (likely stale) |
| `numpy<2.0.0` | `numpy >=1.21,<3` | re-evaluate during S5 — drop NumPy 1 cap if upstream tested |
| `onnxruntime<=1.18.1` | `onnxruntime >=1.14.1` | drop upper cap; re-evaluate |

The last three rows are "audit during S5" — the upper-bound caps are
likely stale and should be dropped if upstream runs CI against
NumPy 2 / ONNX 1.20+. If unsure, keep the cap and add a TODO.

### Internal name mapping

The conda recipe names map to PyPI names map to source directories as
follows. **Do not confuse them.**

| Conda recipe `outputs[i].package.name` | PyPI dist name | Source subdir | Hatch wheel target |
|---|---|---|---|
| `dbgpt` | `dbgpt` | `packages/dbgpt-core` | `src/dbgpt` |
| `dbgpt-client` | `dbgpt-client` | `packages/dbgpt-client` | `src/dbgpt_client` |
| `dbgpt-ext` | `dbgpt-ext` | `packages/dbgpt-ext` | `src/dbgpt_ext` |
| `dbgpt-serve` | `dbgpt-serve` | `packages/dbgpt-serve` | `src/dbgpt_serve` |
| `dbgpt-acc-auto` | `dbgpt-acc-auto` | `packages/dbgpt-accelerator/dbgpt-acc-auto` | `src/dbgpt_acc_auto` |
| `dbgpt-sandbox` | `dbgpt-sandbox` | `packages/dbgpt-sandbox` | `src/dbgpt_sandbox` |
| `dbgpt-app` *(Q1)* | `dbgpt-app` | `packages/dbgpt-app` | `src/dbgpt_app` |

Note the asymmetry: PyPI's `dbgpt` lives under `packages/dbgpt-core/`
in the source tree.

---

## Acceptance Criteria (Whole Feature)

- **AC-1.** Eight staged-recipes PRs are open or merged: one per
  recipe in S1–S7 (prerequisites), plus one for the DB-GPT multi-
  output recipe (S12). Each addresses every bot-lint,
  conda-smithy-lint, and reviewer comment.
- **AC-2.** All 7 DB-GPT outputs build green on at least `linux-64`
  in conda-forge CI. All 7 prerequisite recipes likewise build green
  (lyric-py builds on every platform in its matrix; the others are
  noarch and need only one job).
- **AC-3.** `pip check` passes for every output's test stage and for
  every prerequisite recipe's test stage.
- **AC-4.** A user on a fresh pixi env can install **any** included
  package by name and import its primary module:
    - `pixi add dbgpt && pixi run python -c "import dbgpt"`
    - …and same for `dbgpt-client`, `dbgpt-ext`, `dbgpt-serve`,
      `dbgpt-acc-auto`, `dbgpt-sandbox`, `dbgpt-app`.
    - Prerequisite recipes installable independently:
      `pixi add lyric-py && pixi run python -c "import lyric"`,
      `pixi add lyric-task lyric-py-worker lyric-js-worker
      lyric-component-ts-transpiling abstract-singleton
      auto-gpt-plugin-template`.
- **AC-5.** dbgpt-app's `[code]` extra works without external pip:
  `pixi add dbgpt-app && pixi run python -c "from dbgpt_app import
  cli"` succeeds with no `ImportError: lyric_py_worker` (or
  equivalent), and the documented code-sandbox entrypoint starts.
  Verified in a pixi env containing only conda-forge channel
  packages.
- **AC-6.** All Open Questions are annotated with `**Decision: …**`
  and a one-paragraph rationale before any code lands. Q1 is
  resolved (B-full); Q2 and Q3 are answered before/during S10 and
  S12 respectively.
- **AC-7.** If S12 fallback fires (S5/S6/S7 rejected): the
  `recipes/db-gpt/patches/0001-drop-code-extra-from-dbgpt-app.patch`
  diff applies cleanly and AC-5 degrades to the
  `B-six-plus-app-patched` form (`import dbgpt_app` succeeds; the
  `[code]` extra is documented as unavailable in the PR body and
  feedstock README).
---

## Open Questions

### Q1 (v1-blocking) — `dbgpt-app` inclusion path

The `dbgpt-app` package hard-pulls `dbgpt[code]` (lyric-* workers) and
`dbgpt[agent]` (`auto-gpt-plugin-template`). Three options now exist
(see "Background" for the source-build investigation):

- **B-six**: Drop `dbgpt-app` entirely from this v1 effort. Ship 6
  outputs. Zero prerequisite recipes. Single PR. Users who want
  `dbgpt-app` install it via pip on top of conda-installed dbgpt-*.
  Cleanest from a conda-forge review perspective.

- **B-six-plus-app-patched**: Ship 7 outputs, with a recipe-side patch
  that removes `code` from `dbgpt-app`'s `dependencies` array. Adds
  S1+S2 (abstract-singleton, auto-gpt-plugin-template) as 2 prerequisite
  PRs. Total 3 PRs. Users get `dbgpt-app` from conda-forge but without
  the code-execution sandbox feature; documented in PR body and
  feedstock README.

- **B-full**: Ship all 7 outputs with `dbgpt-app` fully functional —
  the `code` extra is preserved by packaging the lyric-* worker
  stack on conda-forge using the `itkwasm-downsample-wasi` vendor-the-
  blob pattern (~30-line `noarch: python` recipes that pip-install
  upstream PyPI sdists containing pre-built `.wasm`; runtime supplied
  by `wasmtime-py`, already on conda-forge). Requires packaging:
  `abstract-singleton`, `auto-gpt-plugin-template`, `lyric-task`
  (3 trivial), `lyric-py` (cocoindex-class — Rust+maturin+protoc;
  the only non-trivial recipe), and `lyric-py-worker`,
  `lyric-js-worker`, `lyric-component-ts-transpiling` (3 itkwasm-
  pattern noarch recipes). Total **8 PRs** (7 prereq + the DB-GPT
  multi-output recipe). Multi-day, not multi-week. Risk: a
  conda-forge reviewer rejects the vendor-the-blob pattern despite
  the itkwasm precedent — fallback is `B-six-plus-app-patched`.

**Decision: `B-full`** (resolved 2026-05-08).

**Rationale**: The `itkwasm-downsample-wasi` precedent on main
conda-forge collapses the lyric-* worker recipes to ~30 lines each
(noarch python wrapping a vendored upstream sdist), with `wasmtime-py`
44.0.0 (already on conda-forge) supplying the runtime. Of the 7
prerequisite recipes, only `lyric-py` is cocoindex-class; the other 6
are 30 min to 45 min each. dbgpt-app feature parity (including the
code-execution sandbox) is worth 8 PRs / multi-day effort over
shipping a partially-functional fallback or dropping the package
entirely. Risk-mitigated by the S12 fallback (revert to
`B-six-plus-app-patched` if any lyric-* worker is rejected during
review).

The B-six and B-six-plus-app-patched options remain documented above
as fallback rationale; they are not active paths for this spec.

The story set, FRs, technical approach, and acceptance criteria have
been updated to cover the 7 prerequisite recipes (see Stories S1–S7).

### Q2 (audit during S5) — Upper-bound caps

Three of the loosened pins (`tenacity`, `fastapi`, `numpy`,
`onnxruntime`) carry upper-bound caps in upstream. Decide per dep
whether to keep the cap (safer, may block conda-forge global migrations)
or drop the cap (riskier, but matches conda-forge's general "trust
semver" stance). Default if unsure: **keep the cap with a TODO**.

### Q3 (genuinely open) — `feedstock-name`

Should the conda-forge feedstock be `db-gpt-feedstock` (matches the
upstream repo name and PR title casing) or `dbgpt-feedstock` (matches
the canonical PyPI name and the multi-output package names)? PyPI
metadata canonicalizes to `dbgpt`; the upstream repo name is `DB-GPT`.

**Default**: `db-gpt-feedstock` — preserves the upstream repo name,
which is also what most users will search for. The conda packages
themselves are named `dbgpt`, `dbgpt-client`, etc., independent of the
feedstock slug.

---

## Dependencies and Constraints

### External dependencies that must already exist on conda-forge

Verified via `api.anaconda.org` probes during investigation; subject to
re-verification in S8:

`aiohttp`, `cachetools`, `chardet`, `cloudpickle`, `coloredlogs`,
`colorama`, `cryptography`, `dashscope`, `docker-py` (conda name for
`docker`), `duckdb`, `duckdb-engine`, `fastapi`, `gitpython`, `graphviz`,
`gtts`, `httpx`, `httpx-socks` (for `httpx[socks]`), `importlib_resources`,
`jinja2`, `jsonschema`, `mcp`, `msgpack-python` (conda name for
`msgpack`), `numpy`, `olefile`, `onnxruntime`, `openai`, `openpyxl`,
`pandas`, `pdfplumber`, `pillow`, `prettytable`, `psutil`, `pydantic`,
`pympler`, `pymysql`, `pypdf`, `pyparsing`, `python-docx`, `python-jsonpath`,
`python-multipart`, `python-pptx`, `pyzmq`, `qianfan` *(verify)*,
`rich`, `schedule`, `seaborn`, `selenium`, `sentence-transformers`,
`sentencepiece`, `shortuuid`, `snowflake-id`, `spacy`, `sqlalchemy`,
`sqlparse`, `termcolor`, `tiktoken`, `tokenizers`, `tomli`, `tomlkit`,
`transformers`, `typeguard`, `typing_inspect`, `typing-extensions`,
`uvicorn`, `xlrd`.

### External dependencies that are NOT on conda-forge — landed by this spec's prerequisite stories

| PyPI dep | Story | Pattern | Effort |
|---|---|---|---|
| `abstract-singleton` | S1 | trivial pure-Python noarch | 30 min |
| `auto-gpt-plugin-template` | S2 | trivial pure-Python noarch | 20 min |
| `lyric-task` | S3 | trivial pure-Python noarch | 30 min |
| `lyric-py` | S4 | Rust+maturin+protoc, per-platform | 4–6 h (cocoindex-class) |
| `lyric-py-worker` | S5 | itkwasm-pattern noarch (vendored .wasm) | 45 min |
| `lyric-js-worker` | S6 | itkwasm-pattern noarch (vendored .wasm) | 30 min |
| `lyric-component-ts-transpiling` | S7 | itkwasm-pattern noarch (vendored .wasm) | 30 min |

**No upstreaming of WASI-side toolchain required.** The original
estimate that `B-full` needed `wasi-sdk`, `wasm-tools`,
`componentize-py`, `jco`, and `rust-std-wasm32-wasip1` on conda-forge
was based on assuming we'd source-rebuild the `.wasm` blobs. The
itkwasm-downsample-wasi precedent (see § "WASM toolchain on
conda-forge — current state") demonstrates that conda-forge accepts
vendored `.wasm` from upstream PyPI sdists when:
1. The runtime that executes the WASM (`wasmtime-py`) is itself built
   from source on conda-forge, **and**
2. Upstream has reproducible WASM build CI (verified for
   `lyric-project/lyric-runtime`).

The Bytecode Alliance toolchain stays out of this spec's scope (NG3).

### Upstream constraints

- DB-GPT v0.8.0 is the chosen baseline. Tag-based source URL.
- The repo's root `LICENSE` is MIT (verified). Sub-packages declare
  `license = "MIT"` in their pyproject.toml; no per-package LICENSE
  files (verified).
- The PyPI dist `dbgpt` corresponds to the *source* directory
  `packages/dbgpt-core/`. This naming asymmetry is hard-coded into the
  recipe.
- Lyric prerequisites are versioned at `0.1.7` upstream
  (`lyric-project/lyric-runtime`, MIT). All 5 Python wrappers
  (`lyric-task`, `lyric-py`, `lyric-py-worker`, `lyric-js-worker`,
  `lyric-component-ts-transpiling`) are at the same version. PyPI
  metadata for these has empty/None license fields — read MIT from
  the upstream LICENSE file directly.

### Skill-version constraint

The recipe uses rattler-build v1 features (`pin_subpackage(exact=True)`,
`schema_version: 1`, multi-output without legacy meta.yaml). Requires
`conda-forge-expert` skill v6.x and rattler-build ≥ v0.61.0.

---

## Out of Scope (Explicit)

- **OOS-1.** `dbgpt-acc-flash-attn` — CUDA-only, GPU-tier, deferred
  indefinitely.
- **OOS-2.** Source-rebuilding the lyric-* WASM blobs on conda-forge CI.
  The recipes vendor the upstream PyPI sdists' pre-built `.wasm` per
  the itkwasm precedent (NG3). Source-rebuild would require packaging
  `wasi-sdk`, `wasm-tools`, `componentize-py`, `jco`, and adding
  `rust-std-wasm32-wasip1` to `rust-feedstock` — all out of scope.
- **OOS-3.** Authoring lyric-runtime (the Rust-only umbrella) or the
  Bytecode Alliance toolchain (`componentize-py`, `wasm-tools`, `jco`)
  as conda-forge recipes. Tracked in deferred-work for a future
  ecosystem-improvement effort.
- **OOS-4.** Modifying the `conda-forge-expert` skill scripts. This
  effort exercises the skill as-is; any skill-side bugs surfaced are
  filed separately, not fixed inline.
- **OOS-5.** A `db-gpt` _application_ launcher / CLI integration test.
  conda-forge's standard import test is sufficient for a v1 PR.

---

## References

- Upstream repo: `https://github.com/eosphoros-ai/DB-GPT`
  (license: MIT, v0.8.0 release tag `v0.8.0`).
- Upstream uv workspace `pyproject.toml`:
  `https://github.com/eosphoros-ai/DB-GPT/blob/v0.8.0/pyproject.toml`.
- conda-forge multi-output recipe template:
  `.claude/skills/conda-forge-expert/templates/multi-output/lib-python-recipe.yaml`.
- Pin-loosening convention:
  `~/.claude/projects/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/memory/feedback_loosen_pins.md`.
- v0/v1 about-field mapping:
  `~/.claude/projects/.../memory/reference_v0_v1_about_fields.md`.
- Sibling tech-spec for format precedent:
  `docs/specs/conda-forge-tracker.md`.
- Cocoindex PR #33231 — recent precedent for a Python recipe with Rust
  components and the `script.env` / `call`-shim authoring patterns this
  recipe avoids by being noarch.
- Lyric upstream: `https://github.com/lyric-project/lyric-runtime`
  (24★, MIT, Bytecode Alliance ecosystem). Workspace contains `crates/`
  (Rust), `bindings/python/` (5 Python packages with Makefiles),
  `bindings/javascript/`, `components/rust/component-ts-transpiling/`.
- Personal mirror of Lyric: `https://github.com/fangyinc/lyric` —
  `Cargo.toml` workspace `repository` URL still points here, but
  active development is at `lyric-project/lyric-runtime`.
- WASM on Pixi/rattler-build announcement:
  `https://prefix.dev/blog/pixi_wasm` — `emscripten-wasm32` and
  `wasi-wasm32` are first-class build platforms; ambition is to make
  WASM a normal conda-forge target.
- itkwasm precedent on conda-forge — vendor-the-blob pattern that
  Lyric workers can follow:
  `https://github.com/conda-forge/itkwasm-feedstock`,
  `https://github.com/conda-forge/itkwasm-downsample-feedstock`,
  `https://github.com/conda-forge/itkwasm-downsample-wasi-feedstock`.
  The `-wasi` recipe is ~30 lines of `noarch: python` that
  pip-installs the upstream PyPI sdist containing the pre-built
  `.wasm`; runtime is supplied by `wasmtime-py`.
- `wasmtime-py` upstream (Bytecode Alliance):
  `https://github.com/bytecodealliance/wasmtime-py`. The conda-forge
  `wasmtime-py` package bundles `_libwasmtime.so` inside the conda
  artifact — installing it gives both the Python API and the
  Wasmtime engine.
- Pyodide on conda-forge issue (closed):
  `https://github.com/pyodide/pyodide/issues/795` (opened 2020-11-09,
  closed) — outlined five blockers (emscripten update cadence,
  unconventional cross-compile, .data/.js artifact format, browser
  resolution); led to the parallel `emscripten-forge` distribution
  rather than direct conda-forge integration.
- emscripten-forge: `https://github.com/emscripten-forge/recipes`
  (82★) — community-driven channel for emscripten-built packages
  (browser/Pyodide-targeted). Not a fit for Lyric (WASI Preview 1
  target, not emscripten ABI).
- Bytecode Alliance tools referenced by Lyric Makefiles:
  `componentize-py` (`https://github.com/bytecodealliance/componentize-py`),
  `wasm-tools` (`https://github.com/bytecodealliance/wasm-tools`),
  `jco` (`https://github.com/bytecodealliance/jco`),
  `wasi-sdk` (`https://github.com/WebAssembly/wasi-sdk`).

---

## Suggested BMAD Invocation

```
run quick-dev — implement the intent in docs/specs/db-gpt-conda-forge.md

# Q1 is resolved (B-full). 13 stories in 4 waves:
#   Wave 1 (parallel): S1 (abstract-singleton), S3 (lyric-task)
#   Wave 2 (parallel): S2 (auto-gpt-plugin-template, blocked by S1),
#                      S4 (lyric-py, blocked by S3) — cocoindex-class
#   Wave 3 (parallel): S5, S6, S7 (lyric workers, blocked by S3+S4)
#   Wave 4 (sequential within wave): S8 → S9, S10, S11 → S12
```

The story sequencing constraints inside `bmad-quick-dev`:
- S2 depends on S1 entering review queue.
- S4 depends on S3 entering review queue (and is the only
  cocoindex-class effort).
- S5, S6, S7 each depend on S3 and S4 entering review queue.
- S8 (DB-GPT skeleton) is the entry point to Wave 4.
- S9 (cross-deps) depends on S8.
- S10 (loosen pins) and S11 (license files) can run in parallel with
  S9.
- S12 (validate/build/submit) depends on S8+S9+S10+S11 locally and on
  S1–S7 entering staged-recipes review queue (so `check_dependencies`
  resolves).
- S12 contains the fallback path: if S5/S6/S7 are rejected during
  review, author the
  `recipes/db-gpt/patches/0001-drop-code-extra-from-dbgpt-app.patch`
  diff and degrade to `B-six-plus-app-patched` for the rejected
  extras.
