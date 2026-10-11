---
status: in-progress
implemented_by: bmad-quick-dev
shipped_ref: ""
spec_updated: 2026-07-01
---
# Tech Spec: Flyte 2 SDK (`flyte`) on conda-forge

> **DECISIONS (2026-07-01, bmad-quick-dev run):** **Q1 = "Base + all extras verified"** —
> build all 6 net-new recipes (5 base + `flyte_controller_base`) AND verify the
> sandbox/connector/mcp/tui/aiosqlite extras' deps resolve on cf (handle the
> `pydantic-monty==0.0.17` pin). **Q3 = `python_min "3.11"`** (cf cel-python floor; no
> cel-python-3.10 rebuild). Q2/Q4/Q5 resolve during implementation.

> **BMAD intake document.** Written for `bmad-quick-dev` / `bmad-dev`. This is the
> **submission** spec for getting the **Flyte 2 SDK** — the PyPI `flyte` package
> (from `flyteorg/flyte-sdk`) — onto conda-forge, together with its net-new
> dependency closure. Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/flyte-conda-forge.md
> ```
>
> **Rule 1 (always-on):** every recipe touch here MUST go through the
> `conda-forge-expert` skill (the skill's gotchas/protocols are authoritative on any
> conflict). **Rule 2:** the effort closes out with a CFE-skill retro.
>
> Modeled on `docs/specs/db-gpt-conda-forge.md` (prerequisite-chain submission model)
> and `docs/specs/langflow-conda-forge.md` (closure-audit + external-skew discipline).

---

## ✅ DELIVERED — LOCAL-ONLY CLOSURE GREEN (2026-07-01, bmad-quick-dev)

> **Decision: local-only build (Q, user 2026-07-01)** — the whole closure is built into
> the local channel with the buf.validate workaround; **NOT submitted to conda-forge**
> (blocked on the upstream buf.validate issue below). Scope Q1 = "base + all extras verified".

**All 6 net-new recipes built + tested GREEN locally (linux-64, rattler-build):**

| Recipe | version | shape | artifact | status |
| --- | --- | --- | --- | --- |
| `protovalidate` | 1.2.0 | noarch | `protovalidate-1.2.0-pyha7a566d_0` | ✅ green (patched to ship buf.validate) |
| `pyqwest` | 0.6.2 | compiled (py310–313) | `pyqwest-0.6.2-py3xx…` | ✅ green |
| `connectrpc` | 0.10.1 | noarch | `connectrpc-0.10.1-pyhcba1bba_0` | ✅ green |
| `flyteidl2` | 2.0.26 | noarch (wheel) | `flyteidl2-2.0.26-pyha7a566d_0` | ✅ green (buf/ stripped → deps protovalidate) |
| `flyte` | 2.5.7 | noarch (wheel) | `flyte-2.5.7-pyha7a566d_0` | ✅ green — **`import flyte` + pip_check pass** |
| `flyte-controller-base` | 2.5.7 | compiled (abi3 wheel repackage) | `flyte-controller-base-2.5.7-py3xx…` | ✅ green (rust-controller extra) |

**Verified:** `flyte` installs from the local channel and `import flyte` + `pip check` pass on
py3.11 + latest — the full buf.validate workaround holds end-to-end. **All extras' deps confirmed
on cf** (sandbox `pydantic-monty==0.0.17` ✓, connector `grpcio`/`grpcio-health-checking`/
`prometheus_client` ✓, mcp/`starlette`/`uvicorn` ✓, tui `textual` ✓, `aiosqlite` ✓).

**The buf.validate workaround (what made it work):** `protovalidate` is patched to own the
newer `buf.validate` stubs (`force-include gen/buf`); `flyteidl2` strips its bundled older `buf/`
and depends on `protovalidate` (verified: protovalidate's buf.validate is a superset that
flyteidl2's protos tolerate). This is a single-owner resolution of the collision — **local-only**;
NOT cf-submittable (see blocker below).

**NOT submitted (cf blocker stands).** Every recipe carries `cfe-on-conda-forge-status:
blocked-pending-prerequisites` + the buf.validate blocker in `cfe-forge-blocker-list`. cf
submission needs the upstream fix (protovalidate ships its stubs / flyteidl2 depends on
protovalidate for buf.validate). `flyte-controller-base` additionally needs a from-source Rust
build (currently a wheel-repackage — R-028 lint).

---

## 🛑 BLOCKER (2026-07-01, Wave 1) — `buf.validate` namespace collision + version skew

> Surfaced building the first "trivial" leaf (`protovalidate`). The intake spec's
> assumption that protovalidate is a clean noarch leaf ("all deps on cf") is **WRONG** —
> there is a fundamental, upstream-rooted `buf.validate` stub problem across the closure.
> **Build paused pending a design decision (see options).**

**Empirically verified (2026-07-01):**

1. **`protovalidate`'s PyPI wheels ship NO `buf`/`cel` stubs — every version 0.13→1.2.0.**
   `import protovalidate` → `from buf.validate import validate_pb2` (validator.py:17,
   internal/rules.py:32). The stubs live in the sdist's `gen/` (written by `buf generate`,
   `buf.gen.yaml out: gen`) but hatchling never packages `gen/` into the wheel. So a clean
   `pip install protovalidate` is **broken standalone** (`ModuleNotFoundError: No module
   named 'buf'`) — confirmed in an isolated venv. This is an upstream packaging bug.
2. **`flyteidl2 2.0.26` is wheel-only (NO sdist) and bundles its OWN top-level
   `buf/validate/` stubs** — a *different, older* version of the buf.validate proto.
3. **The two are incompatible.** With `flyteidl2` installed (providing `buf/validate/`),
   `import protovalidate` STILL fails: `AttributeError: CEL_EXPRESSION_FIELD_NUMBER` —
   protovalidate 1.2.0's code references a buf.validate field that flyteidl2's older
   bundled stubs lack. (`import flyteidl2` works — it uses its own stubs and imports
   protovalidate only lazily, so the skew is latent on PyPI.)

**Why this blocks conda-forge specifically:** exactly ONE conda package may own
`buf/validate/validate_pb2.py` (conda forbids two packages shipping the same file). But
`protovalidate` (needs buf.validate @1.2.0-schema) and `flyteidl2` (bundles buf.validate
@2.0.26-schema) need **incompatible versions** of that same path. There is no clean
recipe-level resolution — it requires an upstream fix or a reviewer-risky workaround.

**Options (decision required):**
- **(1) Version-match + circular dep** — pin `protovalidate` to the version whose code
  matches `flyteidl2 2.0.26`'s bundled buf.validate; give protovalidate a circular
  `run: flyteidl2` + a `package_contents` test (can't import standalone). No wheel
  surgery; fragile version-matching; reviewer-risky (circular dep + justified non-import test).
- **(2) protovalidate owns buf.validate + flyteidl2 wheel surgery** — patch protovalidate's
  build to ship `gen/buf` + `gen/cel` (fix the upstream bug); strip `buf/` from flyteidl2's
  wheel + depend on protovalidate. Cleanest ownership; needs wheel repackaging on a no-sdist
  package + gambling that flyteidl2's protos work against protovalidate's newer buf.validate.
- **(3) File upstream + defer** — report the protovalidate-wheel-omits-stubs bug + the
  flyteidl2/protovalidate buf.validate skew to flyteorg/bufbuild; package the rest of the
  closure (pyqwest, connectrpc) now; **defer flyteidl2 + flyte** until upstream fixes
  (protovalidate ships stubs / flyteidl2 depends on protovalidate for buf.validate).
- **(4) Local-only** — build the closure local-only (personal channel) with option 1 or 2;
  accept it is not cf-submittable until upstream is fixed.

`protovalidate` recipe is authored + builds (artifact written) but its import test fails —
left in place pending the decision. No other recipes started.

---

## ⚡ CURRENT STATE (2026-07-01) — READ THIS FIRST

> Single source of truth. Live facts (versions, feedstock membership, python floors)
> decay — **re-verify before acting** (CFE G66/G74/G78).

**Target:** package **`flyte` 2.5.7** (Apache-2.0) — the *Flyte 2* Python SDK — as a
single `noarch: python` recipe, plus **4 net-new prerequisite recipes**. **Nothing is
built or submitted yet** — this is a complete intake, zero implementation.

**Net-new closure (5 recipes):**

| Recipe | Version | Shape | Why net-new |
| --- | --- | --- | --- |
| **flyte** | 2.5.7 | noarch:python | the target — Flyte 2 SDK, NOT on cf |
| **flyteidl2** | ==2.0.26 | noarch:python (protobuf stubs) | hard base dep; distinct from cf's v1 `flyteidl` |
| **protovalidate** | 1.2.0 | noarch:python | hard dep of `flyteidl2`; Buf CEL validation runtime |
| **connectrpc** | 0.10.x (`<0.11,>=0.9.0`) | noarch:python | hard base dep; Connect-RPC Python runtime |
| **pyqwest** | >=0.5.1 | **compiled Rust/maturin** | hard dep of `connectrpc`; the only non-trivial recipe |

**Everything else in the base closure is already on conda-forge → consume, do NOT
submit** (§ Submission set → A).

**Headline finding (python_min = 3.11, NOT 3.10 — G40/G41):** upstream `flyte`
declares `requires-python >=3.10`, but on conda-forge the chain
`flyte → flyteidl2 → protovalidate → cel-python` floors at **3.11** — cf `cel-python`
ships **py3.11+ only** (`run: python >=3.11`), so no py3.10 solve exists. Set the whole
flyte closure's `python_min` to **"3.11"** (or rebuild `cel-python` for py3.10 — Q3).

**NEXT ACTION:** resolve **Q1** (extras scope — base-only vs base+extras) and **Q3**
(python_min 3.11 vs rebuild cel-python), then execute Wave 1 leaves-first.

---

## Background and Context

### The problem

**Flyte 2** ships a brand-new, ground-up Python SDK published to PyPI as **`flyte`**
("Reliably orchestrate ML pipelines, models, and agents at scale — in pure Python").
It is a *different package* from the classic **`flytekit`** v1 SDK and lives in a
*different repo*. There is no `flyte` feedstock and no prior staged-recipes PR. Without
packaging, conda / air-gapped users cannot install the Flyte 2 SDK through their
channel, and the pinned application-style deps silently downgrade conda-forge packages
when pip-installed on top of a conda env.

### ⚠ Critical identity: `flyte` (v2) ≠ `flytekit` (v1) ≠ `flyteidl` (v1)

The Flyte ecosystem has three separate PyPI names that a reviewer or an agent can
easily conflate. **This effort packages only the v2 line.**

| PyPI name | Line | conda-forge status | This spec |
| --- | --- | --- | --- |
| `flyte` | **v2 SDK** (2.5.7) | **NOT on cf** | ✅ the target |
| `flyteidl2` | **v2 IDL** (2.0.26) | **NOT on cf** | ✅ net-new prereq |
| `flytekit` | v1 SDK (1.x) | ✅ `flytekit-feedstock` (meta.yaml) | consume/ignore — different package |
| `flyteidl` | v1 IDL (1.x) | ✅ `flyteidl-feedstock` (meta.yaml) | consume/ignore — different package |

Do **not** try to "update flytekit to flyte" — they coexist. Do **not** assume cf's
`flyteidl` satisfies `flyteidl2` — the v2 IDL is a separate distribution at a separate
version (2.0.26 vs 1.15.x).

### The two GitHub repos the user named — and which is in scope

- **`flyteorg/flyte-sdk`** — publishes PyPI **`flyte`**. Pure-Python async SDK (with an
  *optional* Rust controller subpackage, `flyte_controller_base`, under `rs_controller/`).
  **This is the packaging target.**
- **`flyteorg/flyte`** — the Flyte **backend / control-plane**: ~84 % **Go**
  (flytepropeller / flyteadmin / executor / manager / flyteplugins / flytestdlib),
  Kubernetes-native, protobuf definitions. **OUT OF SCOPE** — a Go orchestration
  platform is not a conda-forge candidate, and the Python SDK does not live here
  (it's in `flyte-sdk`). See NG1.

### What's been investigated

- **flyte base dependency closure** (verified 2026-07-01 against `flyte` 2.5.7's PyPI
  `requires_dist`). 23 base run-deps; all but four resolve on conda-forge today
  (§ Submission set → A). The four gaps + the target = the 5-recipe net-new set.
- **`connectrpc` sub-closure.** flyte pins `connectrpc<0.11,>=0.9.0`. The 0.10.x line
  needs `protobuf>=5.28` (cf ✓) + **`pyqwest>=0.5.1`** (net-new, compiled Rust). NOTE:
  connectrpc **0.11.0** additionally needs `protobuf-py==0.1.1` (also net-new) — but the
  `<0.11` cap means we package **0.10.x** and **avoid** the `protobuf-py` dependency
  entirely. Do not package 0.11 (G54/version-discipline).
- **`flyteidl2` sub-closure.** Pure-Python protobuf stubs. Deps: `googleapis-common-protos`
  (cf ✓), `protoc-gen-openapiv2` (cf ✓ — `conda-forge/protoc-gen-openapiv2-feedstock`,
  the `unionai-oss` package), `protobuf` (cf ✓), **`protovalidate`** (net-new).
- **`protovalidate` sub-closure.** Buf's CEL protobuf-validation runtime (Apache-2.0,
  `bufbuild/protovalidate-python`). Deps: `cel-python` (cf ✓, **py3.11+**),
  `google-re2` (cf ✓, compiled — proven present by cf `cel-python` building against it),
  `protobuf` (cf ✓). **All deps already on cf** → protovalidate itself is the only
  net-new node in this sub-branch.
- **The python_min-3.11 chain.** `cel-python` on cf declares `python_min: 3.11` /
  `run: python >=3.11`, so `protovalidate` → `flyteidl2` → `flyte` cannot solve on
  py3.10. Effective closure floor = **3.11** (see Q3).

### What's available to leverage

- **`conda-forge-expert` skill** — the full 10-step loop authors each recipe; the maturin
  templates + cocoindex/obstore/lyric-py exemplars directly apply to `pyqwest`.
- **`obstore` precedent** — flyte's own `obstore` dep is an already-shipped
  Rust/maturin object-store binding (`conda-forge/obstore-feedstock`, `developmentseed`).
  `pyqwest` is structurally analogous (Rust HTTP client via maturin/PyO3) — the same
  recipe shape (`cross-python_${{ target_platform }}`, `maturin` host dep,
  `cargo-bundle-licenses`, per-platform build).
- **`pydantic-monty` precedent** — the `sandbox` extra's `pydantic-monty` is already a
  shipped Rust/maturin cf recipe (`cargo-auditable-wrapper` pattern) — reference if the
  sandbox extra is included (Q1).

---

## Packaging shape & key decisions

- **Single-package target, prerequisite-chain model.** `flyte` is ONE importable
  package (`import flyte`) → **one `noarch: python` recipe**, not a multi-output suite
  (contrast db-gpt/langflow). The 4 net-new prerequisites are **separate recipes**
  submitted leaves-first; the db-gpt prereq-chain model applies, not the langflow
  multi-output-suite model.
- **`python_min: "3.11"` across the whole closure** (G40/G41) — the cel-python floor.
  Declare `python_min: "3.11"` in `context:` for `flyte`, `flyteidl2`, `protovalidate`
  (overriding the default 3.10 floor; upstream `requires-python >=3.10` is aspirational
  on cf). `connectrpc`/`pyqwest` don't transit cel-python but inherit 3.11 via flyte —
  keep them at the default floor unless their own deps demand higher.
- **`pyqwest` is the only compiled recipe** — Rust/maturin, per-platform (verify abi3 vs
  per-Python from `Cargo.toml`, G49; likely per-Python like obstore). cocoindex/obstore
  class. All others are `noarch: python`.
- **Source preference `sdist > GitHub-tag > wheel` (G54/G55).** For each recipe, verify
  the PyPI sdist actually ships the module (`tar -tzf … | grep -c '\.py$'`); flyteidl2
  (protobuf stubs) and pyqwest (Rust) especially — if the sdist is metadata-only, fall
  back to the `flyteorg/flyte-sdk` (or upstream) GitHub tag archive. Confirm each
  recipe's `[build-system]` backend and add it to `host` (G55).
- **Import-name divergence (G7/G10).** Verify each import against the sdist's
  `__init__.py`: `flyte`→`flyte`, `flyteidl2`→`flyteidl2`, `connectrpc`→`connectrpc`,
  `protovalidate`→`protovalidate`, `pyqwest`→(verify, likely `pyqwest`). Cache the
  verified value in `cfe-import-names`.
- **cfe metadata + strip-before-push (G62)** — every local recipe carries the `cfe-*`
  block (local-only); strip + verify on the pushed artifact.

---

## Goals

- **G1.** Land **`flyte` 2.5.7** on conda-forge as a `noarch: python` recipe in
  `recipes/flyte/`, plus the 4 net-new prerequisite recipes, all built GREEN locally
  first (local channel), then submitted to `conda-forge/staged-recipes` leaves-first.
- **G2.** Package `flyteidl2 ==2.0.26` (the exact pin `flyte` declares) and
  `connectrpc` at the newest `0.10.x` (`<0.11,>=0.9.0`) so the `flyte` test-env solve
  resolves from the channel.
- **G3.** Package `pyqwest` (compiled Rust/maturin) on the standard 5-subdir matrix
  (linux-64/aarch64, osx-64/arm64, win-64), following the `obstore` recipe pattern.
- **G4.** Set `python_min: "3.11"` on the noarch closure (the cel-python floor, G40/G41);
  document the finding in each recipe's cfe-comments block.
- **G5.** Loosen upstream `==` pins only where a version is genuinely unavailable on cf,
  per the pin-loosening convention — and when doing so under `pip_check: true`, patch the
  wheel METADATA too (G26). Prefer resolving to an existing older cf build over loosening
  (e.g. `rich-click==1.8.9`).
- **G6.** Surgical scope: do not touch `flytekit`/`flyteidl` (v1) recipes; do not attempt
  the Go backend.

## Non-Goals

- **NG1.** No `flyteorg/flyte` Go backend / control-plane (flytepropeller, flyteadmin,
  flytectl, executor, manager). Not a conda-forge candidate; out of scope entirely.
- **NG2.** No changes to the existing `flytekit` (v1) or `flyteidl` (v1) feedstocks.
  Flyte 1 and Flyte 2 coexist; this effort adds the v2 line only.
- **NG3.** No `polyglot-hello` recipe (the `examples-test` extra) — test-only, not a
  runtime dep. Out of scope.
- **NG4.** No upstream PR to `flyte-sdk`/`flyteidl2` to soften pins. Loosening happens
  recipe-side only (G26).
- **NG5.** No connectrpc **0.11** (would drag in the net-new `protobuf-py`); package the
  `<0.11` line the flyte pin requires.
- **NG6.** No Anaconda-channel mirror. conda-forge only.

---

## Submission set

Three buckets. Membership verified live 2026-07-01 (`lookup_feedstock` / `get_conda_name`);
re-verify per G66/G74/G78 before each wave.

### A. Already on conda-forge → CONSUME, do not submit

All 19 non-gap base run-deps of `flyte`:

`aiofiles`, `click`, `cloudpickle`, `docstring_parser` (**G10** — underscore feedstock,
not `docstring-parser`), `fsspec`, `obstore`, `protobuf`, `pydantic`, `pyyaml`,
`rich-click` (⚠ pin — see below), `httpx`, `keyring`, `msgpack-python` (**G10** — PyPI
`msgpack`), `toml`, `async-lru`, `mashumaro`, `aiolimiter`, `packaging`, `sentry-sdk`,
`pyopenssl` (**G10** — PyPI `pyOpenSSL`), `asyncssh`. Plus `flyteidl2`'s already-on-cf
deps `googleapis-common-protos` + `protoc-gen-openapiv2`, and `protovalidate`'s
already-on-cf deps `cel-python` + `google-re2`.

### B. Net-new — to build + submit (leaves-first)

| # | Recipe | Version | Shape | License | Net-new deps (its own) |
| - | ------ | ------- | ----- | ------- | ---------------------- |
| 1 | **pyqwest** | >=0.5.1 (pin latest) | compiled Rust/maturin | verify (likely Apache-2.0/MIT) | — (leaf; Rust crates vendored) |
| 2 | **protovalidate** | 1.2.0 | noarch:python | Apache-2.0 | — (cel-python + google-re2 + protobuf all on cf) |
| 3 | **connectrpc** | 0.10.x (`<0.11`) | noarch:python | Apache-2.0 | **pyqwest** (#1) |
| 4 | **flyteidl2** | ==2.0.26 | noarch:python | Apache-2.0 | **protovalidate** (#2) |
| 5 | **flyte** | 2.5.7 | noarch:python | Apache-2.0 | **flyteidl2** (#4), **connectrpc** (#3) |

### C. Optional extras (Q1-gated — only if the user opts in beyond base)

`flyte` declares several extras; **none is a base runtime dep**. Recommended default:
**base-only** (Q1 = base). If extras are included, these are the additional net-new /
pin-conflict items:

| Extra | Adds | conda-forge status |
| --- | --- | --- |
| `rust-controller` | `flyte_controller_base==2.5.7` | **NET-NEW compiled** Rust/maturin (from `flyte-sdk` `rs_controller/`); version-locked to flyte |
| `sandbox` | `pydantic-monty==0.0.17` | on cf (0.0.18; needs the 0.0.17 build or loosen — pin conflict) |
| `connector` | `grpcio`, `grpcio-health-checking`, `httpx`, `prometheus-client` | all on cf ✓ |
| `mcp` | `mcp`, `starlette`, `uvicorn` | all on cf ✓ |
| `tui` | `textual>=0.80` | on cf ✓ |
| `aiosqlite` | `aiosqlite>=0.21.0` | on cf ✓ |
| `examples-test` | `polyglot-hello`, `pandas`, `pyarrow`, `scikit-learn`, `joblib`, `nest-asyncio`, `deltalake`, `fastapi`, `uvicorn`, `lightning` | test-only → **NG3** (skip) |

### Pin conflicts to resolve (Wave B)

- **`rich-click==1.8.9`** — flyte's base pin is *exact*; cf `rich-click-feedstock` is at
  1.9.8. conda-forge keeps old builds, so `rich-click 1.8.9` **likely still resolves**
  from the channel — verify (`conda search "rich-click==1.8.9"` per G33 misread caveat).
  If absent, loosen upstream `==1.8.9`→`>=1.8.9` and patch the wheel METADATA (G26).
- **`flyteidl2==2.0.26`** — we package exactly 2.0.26; no conflict.
- **`connectrpc<0.11,>=0.9.0`** — we package 0.10.x; no conflict.
- **`pydantic-monty==0.0.17`** (sandbox extra, Q1) — cf has 0.0.18; verify the 0.0.17
  build exists or loosen.

---

## The python_min = 3.11 finding (G40/G41) — load-bearing

`flyte` (and `flyteidl2`, `protovalidate`) declare `requires-python >=3.10`, but the
**effective conda-forge floor is 3.11**:

```
flyte  →  flyteidl2  →  protovalidate  →  cel-python  (cf ships py3.11+ only)
```

cf `cel-python-feedstock` declares `context.python_min: 3.11` and `run: python >=3.11`,
so a py3.10 test-env solve for the flyte closure has **no candidate** for cel-python.

**Resolution (default):** set `python_min: "3.11"` in `context:` for `flyte`,
`flyteidl2`, and `protovalidate`. **Alternative (Q3):** rebuild/PR `cel-python` for
py3.10 (only if a py3.10 flyte install is a hard requirement) — heavier and not
recommended.

Verify at Wave B by checking the built recipe's py3.10 test leg fails to solve on
cel-python (proves the floor), and that py3.11 resolves clean.

---

## Execution waves

Leaves-first; each wave's recipes are built GREEN locally against the local channel
before the next wave, then submitted so each consumer flips ready when its prereq lands
(G66 — merged ≠ installable; verify live before submitting a consumer).

| Wave | Stories | Description |
| ---- | ------- | ----------- |
| **1 — leaves** | S1, S2 | `pyqwest` (compiled Rust) + `protovalidate` (noarch; all deps on cf) — no net-new prereqs |
| **2 — mid** | S3, S4 | `connectrpc` (needs pyqwest) + `flyteidl2` (needs protovalidate) |
| **3 — target** | S5 | `flyte` 2.5.7 (needs flyteidl2 + connectrpc + the whole A-bucket) |
| **4 — extras (Q1-gated)** | S6 | Only if Q1 ≠ base-only: `flyte_controller_base` + verify sandbox/connector/mcp/tui extras resolve |
| **5 — closeout** | S7 | Submission verification + CFE-skill retro |

---

## User Stories

### Story S0 — Resolve Q1 (extras scope) + Q3 (python_min)

**Status:** open. **Decision needed before Wave 1** — Q1 sets whether Wave 4 runs; Q3
sets the floor (default 3.11). Recommended: Q1 = **base-only**, Q3 = **python_min 3.11**.

### Story S1 — Recipe: `pyqwest` (compiled Rust/maturin, cocoindex/obstore-class)

**Goal:** land `pyqwest` (>=0.5.1, pin the latest) — a Rust HTTP client, the sole compiled
recipe. The only non-trivial prerequisite.

**Acceptance criteria:**
- `recipes/pyqwest/recipe.yaml` validates clean; per-platform build (NOT noarch).
- Build deps: `${{ compiler('rust') }}`, `${{ compiler('c') }}`, `${{ stdlib('c') }}`,
  `maturin` (host), `cargo-bundle-licenses`; canonical Rust env block (`PYTHONUTF8: "1"`,
  `CARGO_PROFILE_RELEASE_STRIP: symbols`; LTO commented — G19).
- Verify abi3 vs per-Python from `Cargo.toml` (G49) → pick test shape accordingly.
- Source: verify the PyPI sdist builds; else GitHub tag (find the repo — likely
  `pyqwest` org / a Rust `qwest`/reqwest wrapper). License vendored via `THIRDPARTY.yml`.
- Build matrix: linux-64, linux-aarch64, osx-64, osx-arm64, win-64. Model on
  `conda-forge/obstore-feedstock` (maturin, cross-python).
- Tests: `import pyqwest` (verify name against sdist, G7); `pip_check: true`.
- **Wave 1.** **Est.:** 4–6 h (cocoindex-class; protoc not expected but verify no
  `libprotobuf`/protoc build need, G30).

### Story S2 — Recipe: `protovalidate` (noarch:python)

**Goal:** land `protovalidate` 1.2.0 (Buf CEL protobuf-validation runtime). All deps on cf.

**Acceptance criteria:**
- `recipes/protovalidate/recipe.yaml` validates clean; `noarch: python`.
- `python_min: "3.11"` in `context:` (inherits the cel-python floor, G40/G41).
- Run deps: `cel-python >=0.5`, `google-re2 >=1`, `protobuf >=5` (all on cf).
- Source: PyPI sdist (`bufbuild/protovalidate-python`, Apache-2.0); confirm the
  `[build-system]` backend → `host` (G55).
- Tests: `import protovalidate`; `pip_check: true`; CFEP-25 triad.
- **Wave 1.** **Est.:** 30 min.

### Story S3 — Recipe: `connectrpc` (noarch:python, `<0.11`)

**Goal:** land `connectrpc` at the newest `0.10.x` (the flyte pin `<0.11,>=0.9.0`).

**Acceptance criteria:**
- `recipes/connectrpc/recipe.yaml` validates clean; `noarch: python`.
- Package **0.10.x** (NG5 — avoid 0.11's `protobuf-py==0.1.1` net-new dep).
- Run deps: `protobuf >=5.28` (cf ✓), `pyqwest >=0.5.1` (S1 — resolves from local
  channel during the build; live cf after S1 merges, G66).
- Source: `connectrpc/connect-py` (Apache-2.0); prefer sdist, verify (G54).
- Tests: `import connectrpc`; `pip_check: true`.
- **Wave 2. Blocked by:** S1 (pyqwest) on the channel. **Est.:** 30 min.

### Story S4 — Recipe: `flyteidl2` (noarch:python, protobuf stubs)

**Goal:** land `flyteidl2 ==2.0.26` — the Flyte 2 IDL (protobuf-generated Python stubs).

**Acceptance criteria:**
- `recipes/flyteidl2/recipe.yaml` validates clean; `noarch: python`.
- `python_min: "3.11"` (via protovalidate → cel-python, G40/G41).
- Run deps: `googleapis-common-protos` (cf ✓), `protoc-gen-openapiv2` (cf ✓),
  `protobuf >=4.21.1` (cf ✓), `protovalidate >=1.0.0` (S2).
- Source: verify the PyPI sdist ships the generated stubs (protobuf-stub sdists are
  sometimes metadata-only, G51/G54); else the `flyteorg` GitHub source. Confirm the
  `[build-system]` backend → `host` (G55).
- Tests: `import flyteidl2` (verify the top-level module against the sdist, G7);
  `pip_check: true`; CFEP-25 triad.
- **Wave 2. Blocked by:** S2 (protovalidate). **Est.:** 45 min (watch for a
  setuptools_scm/dynamic-version trap, G39; and the stub-only-sdist trap, G51).

### Story S5 — Recipe: `flyte` (noarch:python) — the target

**Goal:** land `flyte` 2.5.7 (Flyte 2 SDK).

**Acceptance criteria:**
- `recipes/flyte/recipe.yaml` validates clean; `noarch: python`;
  `python_min: "3.11"` (G40/G41).
- Base run deps (the full 23) resolve from the channel — all A-bucket packages +
  `flyteidl2 ==2.0.26` (S4) + `connectrpc <0.11,>=0.9.0` (S3). Apply the G10 conda-name
  spellings (`docstring_parser`, `msgpack-python`, `pyopenssl`).
- `rich-click ==1.8.9` resolves to the existing cf build, or is loosened with a wheel
  METADATA patch (G26) — decide per the pin-conflict note.
- Any base `pkg[extra]` markers flattened to conda run-deps (G25) — audit
  `[project.dependencies]` only, ignore `[tool.uv]` (G37).
- Source: prefer the PyPI sdist (verify it ships the `flyte` package, G54); the
  `flyte-sdk` monorepo has an `rs_controller/` subdir — confirm the base `flyte` sdist
  is standalone and its `[build-system]` backend (likely hatchling; **not** maturin —
  that's the optional controller) → `host` (G55).
- Tests: `import flyte` (verify against sdist, G7); `pip_check: true`; CFEP-25 triad.
  If flyte exposes a CLI entry point, add a `--help` smoke test.
- **Wave 3. Blocked by:** S3 + S4 on the channel (G66 — verify live before submit).
  **Est.:** 1–2 h (large dep graph; run `check_dependencies`, G29 if it were multi-output
  — here single-output so it works directly).

### Story S6 — (Q1-gated) Optional extras

**Goal:** only if Q1 ≠ base-only — land `flyte_controller_base ==2.5.7` (rust-controller
extra, compiled Rust/maturin from `flyte-sdk` `rs_controller/`, version-locked to flyte;
model on `pydantic-monty`), and verify the sandbox/connector/mcp/tui/aiosqlite extras'
deps resolve (pin-check `pydantic-monty==0.0.17`). Extras deps that aren't hard base
deps go to `run_constraints` if flyte is later leaned (not required for base).

**Acceptance criteria:** each opted-in extra's closure resolves on the channel; no
net-new beyond `flyte_controller_base`. **Wave 4. Blocked by:** S5. **Est.:** 2–4 h if
`flyte_controller_base` is included (compiled).

### Story S7 — Submission verification + CFE-skill retro (closeout)

**Goal:** verify all submitted PRs green; run the mandatory CFE-skill retrospective.

**Acceptance criteria:**
- Every submitted recipe's staged-recipes PR is green (or blocked-with-named-blocker,
  G66/G78 — verify live, not cfe metadata).
- `cfe-on-conda-forge-status` + `cfe-submission-pr` re-stamped on each local recipe (G62 —
  local retains, strip-on-push).
- `bmad-retrospective` run; findings landed in `SKILL.md` / reference / CHANGELOG with a
  version bump (per CLAUDE.md Rule 2). **Wave 5.**

---

## Open Questions

- **Q1 — Extras scope.** Base-only, or base + which extras?
  **Recommendation: base-only** (Wave 1–3, 5 recipes). The `rust-controller`,
  `sandbox`, `connector`, `mcp`, `tui` extras are opt-in orchestration features most
  users don't need; `flyte_controller_base` adds a second compiled recipe. Include
  extras (Wave 4) only if the user needs the local-controller / sandbox path.
- **Q2 — `pyqwest` source & abi3.** Confirm the upstream repo + license, whether the
  PyPI sdist is buildable (vs GitHub tag), and abi3 vs per-Python (G49). *Resolve at
  Wave 1 (S1) from the sdist's `Cargo.toml`.* Non-blocking for intake.
- **Q3 — python_min 3.11 vs rebuild cel-python for 3.10.**
  **Recommendation: python_min "3.11"** (declare it; upstream `>=3.10` is aspirational on
  cf). Rebuild cel-python for py3.10 only if a py3.10 flyte install is a hard requirement
  (heavier; touches another maintainer's feedstock).
- **Q4 — `rich-click==1.8.9` resolution.** Resolve to the existing cf 1.8.9 build, or
  loosen `==`→`>=` with a wheel-METADATA patch (G26)? *Resolve at Wave B (S5) after
  confirming whether the 1.8.9 build is on the channel (G33 caveat).* Recommendation:
  resolve to the existing build if present (no patch needed).
- **Q5 — Recipe directory / feedstock names.** `flyte`, `flyteidl2`, `connectrpc`,
  `protovalidate`, `pyqwest` — all match the PyPI names; no `python-`/`-py` disambiguation
  appears needed, but confirm no collision with an unrelated existing feedstock at submit
  (G58). Recommendation: use the bare PyPI names.

---

## Lifecycle Expectations

After the staged-recipes PRs merge:

- `regro-cf-autotick-bot` files autotick PRs on each new upstream tag (flyte moves fast —
  2.5.7 was released 2026-06-29; expect frequent bumps). Note `flyteidl2` is pinned
  `==2.0.26` by flyte, so a flyteidl2 bump must be co-ordinated with a flyte bump.
- `pyqwest` (compiled) is autotick-maintained per-Python; watch for new-Python-matrix
  fan-out (G38/G40).
- The `flyte` feedstock becomes the canonical conda install path for the Flyte 2 SDK,
  coexisting with the `flytekit` (v1) feedstock.

---

## Appendix — verified facts (2026-07-01)

| Fact | Value | Source |
| --- | --- | --- |
| `flyte` latest | 2.5.7 (2026-06-29), Apache-2.0, req-py >=3.10 | PyPI JSON |
| `flyte` real cf floor | **3.11** (via cel-python) | closure analysis |
| `flyteidl2` | 2.0.26, Apache-2.0, pure-Python stubs | PyPI JSON |
| `protovalidate` | 1.2.0, Apache-2.0, deps cel-python/google-re2/protobuf | PyPI JSON |
| `connectrpc` (flyte needs <0.11) | 0.10.x → protobuf>=5.28 + pyqwest>=0.5.1 | PyPI JSON |
| `pyqwest` | net-new, compiled Rust/maturin | `lookup_feedstock` exists=false |
| `cel-python` cf floor | py3.11+ (`python_min: 3.11`) | `lookup_feedstock` |
| On cf (consume) | obstore, mashumaro, rich-click, docstring_parser, msgpack-python, pyopenssl, asyncssh, sentry-sdk, aiolimiter, async-lru, cel-python, google-re2, googleapis-common-protos, protoc-gen-openapiv2, protobuf, pydantic, httpx, click, fsspec, cloudpickle, keyring, toml, packaging, aiofiles, pyyaml | `lookup_feedstock` / `get_conda_name` |
| NOT on cf (net-new) | flyte, flyteidl2, protovalidate, connectrpc, pyqwest | `lookup_feedstock` exists=false |
| Go backend `flyteorg/flyte` | ~84% Go, out of scope (NG1) | GitHub |
