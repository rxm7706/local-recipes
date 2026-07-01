---
status: in-progress
implemented_by: bmad-quick-dev
shipped_ref: "staged-recipes: ALL 5 prereq PRs MERGED (#33764/#33765/#33766/#33767/#33768); C1 lyric-py ARM live on all 5 subdirs. db-gpt itself DELIVERED VIA #33883 (@pb01ka, dbgpt-split, 8 outputs incl dbgpt-acc-flash-attn) — NOT our own PR (G58 consume-not-submit, user decision 2026-07-01). Our recipes/db-gpt/ now mirrors #33883, verified GREEN locally (8/8, v0.8.1). #33883 red only on G66 channel lag (auto-gpt-plugin-template + lyric-py-worker not yet uploaded); monitoring channel; consume dbgpt on land."
spec_updated: 2026-07-01
---
# Tech Spec: DB-GPT on conda-forge

> **⚠ TERMINAL — DELIVERED EXTERNALLY. DO NOT RE-RUN BMAD ON THIS SPEC.**
> db-gpt is being delivered by an independent staged-recipes PR — **#33883
> (@pb01ka)** — not by us. Per the 2026-07-01 decision we **consume `dbgpt` once
> it lands and do NOT open a competing PR (G58)**. Running `bmad-quick-dev` to
> "implement" the stories below would re-author and submit a competing db-gpt
> recipe — the exact thing this decision forbids. The story set / FRs / AC /
> Technical Approach below are **HISTORICAL PLANNING CONTEXT** (the original
> 2026-05→06-17 plan, adopted-then-superseded by #33883); the **only**
> authoritative sections are **§ Current State** and **§ Readiness** below.
>
> **BMAD intake note (historical):** written for `bmad-quick-dev` (Quick Flow,
> 13 stories, 6 PRs) — all prerequisite work is DONE (5 prereq PRs merged); db-gpt
> itself is out of our hands.

---

## Current State (2026-07-01) — CANONICAL

> Single source of truth. Everything from **§ Background and Context** onward is
> historical planning context (the original plan), superseded by this block +
> § Readiness. Structural claims below (7 outputs, v0.8.0, "we submit") were
> corrected in place per the 2026-07-01 adversarial review.

| Field        | Value                                                                                                                                                                                   |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Status       | **Delivered via #33883 (@pb01ka) — gated on the pipeline lag, not on us** (live: 2026-07-01) — **ALL 5 prereq PRs MERGED** (#33764/#33765/#33766/#33767/#33768). C1 `lyric-py` ARM now live on all 5 subdirs. db-gpt (delivered via #33883, @pb01ka — NOT ours) held only on `auto-gpt-plugin-template` + `lyric-py-worker` completing feedstock creation → first build → channel upload (both merged 2026-07-01, feedstocks not yet created — G66 lag). Our `recipes/db-gpt/` mirrors #33883 (8 outputs, v0.8.1), verified GREEN locally 8/8 (2026-07-01, cfe v8.62.0); **S12 (our own submission) RETIRED — consume, don't submit (G58).** See **§ Readiness** |
| Owner        | rxm7706                                                                                                                                                                                 |
| Track        | BMAD Quick Flow (tech-spec only, no PRD/architecture phase)                                                                                                                             |
| Upstream     | `eosphoros-ai/DB-GPT` — **shipped recipe (#33883) targets v0.8.1** (MIT license). This spec's original dep/pin analysis was done at **v0.8.0** (2026-06-17) and was NOT re-verified against 0.8.1 (the local 8/8 build proves 0.8.1 self-consistent) |
| Target       | `conda-forge/staged-recipes` — **8 outputs** (incl `dbgpt-acc-flash-attn`) in a single multi-output recipe (#33883), plus 7 prerequisite recipes — 2 already on conda-forge (`abstract-singleton`, `lyric-task`), **5 built + all merged** (1 trivial pure-Python, 3 itkwasm-pattern noarch, 1 cocoindex-class Rust+PyO3) |
| Distribution | conda-forge, all 8 outputs `noarch: python`. `lyric-py` ARM **live on all 5 subdirs** (C1 CLEARED 2026-07-01). **⚠ dbgpt-app ARM installability is UNVERIFIED via the PR path** — staged-recipes has no ARM legs (G82) and only chromadb/spacy/onnxruntime were spot-checked on osx-arm64; needs a post-merge feedstock G40 check across the full compiled-dep set × osx-arm64 + linux-aarch64. See § Readiness → C1 |
| Lifetime     | db-gpt feedstock autotick-maintained **by @pb01ka** post-merge                                                                                                              |

---

## Readiness (live: 2026-07-01)

Re-audited live (CFE gotcha **G78** — verify against `gh pr` state + channeldata, not the
recipes' own `cfe-on-conda-forge-status`). **All 5 prereq PRs have now MERGED** — the two
that were the last human-review gate (#33765 `auto-gpt-plugin-template`, #33766
`lyric-py-worker`) merged 2026-07-01T01:44–45Z. Per-subdir channel verification (anaconda.org
API):

| Recipe | live on cf channel | PR | State |
| ------ | ------------------ | -- | ----- |
| `abstract-singleton` | ✅ on cf | — | prereq, already shipping |
| `lyric-task` | ✅ on cf | — | prereq, already shipping |
| `lyric-py` | ✅ **all 5 subdirs** (linux-64/aarch64, osx-64/arm64, win-64) | [#33764](https://github.com/conda-forge/staged-recipes/pull/33764) | **MERGED** — C1 ARM now LIVE |
| `lyric-js-worker` | ✅ noarch | [#33767](https://github.com/conda-forge/staged-recipes/pull/33767) | **MERGED** |
| `lyric-component-ts-transpiling` | ✅ noarch | [#33768](https://github.com/conda-forge/staged-recipes/pull/33768) | **MERGED** |
| `auto-gpt-plugin-template` | ⏳ **NOT yet on channel** (feedstock not yet created) | [#33765](https://github.com/conda-forge/staged-recipes/pull/33765) | **MERGED 2026-07-01** — feedstock first-build+upload pending (G66) |
| `lyric-py-worker` | ⏳ **NOT yet on channel** (feedstock not yet created) | [#33766](https://github.com/conda-forge/staged-recipes/pull/33766) | **MERGED 2026-07-01** — feedstock first-build+upload pending (G66) |
| `db-gpt` (8 outputs) | ⛔ not on cf yet | [#33883](https://github.com/conda-forge/staged-recipes/pull/33883) (@pb01ka) | DRAFT, red **only** on G66 channel lag — build passes; `dbgpt-app` test-env can't find `auto-gpt-plugin-template`. NOT ours — consume, don't submit |

**db-gpt is being delivered by an independent PR — #33883 (@pb01ka), not us.** Decision
(user, 2026-07-01): do **NOT** open a competing PR (G58); #33883 is the accepted solution and
we **consume `dbgpt` once it lands**. #33883 is an OPEN DRAFT whose CI is red **only on the
G66 channel lag** — the build succeeds; `dbgpt-app`'s test-env solve fails on
`auto-gpt-plugin-template >=0.0.3` not being on the channel (and that CI run even predated the
2026-07-01 prereq merges). Our `recipes/db-gpt/` now mirrors #33883 verbatim (8 outputs incl
`dbgpt-acc-flash-attn`, v0.8.1; cfe-block added, `pb01ka` retained as sole maintainer) and was
verified **GREEN locally** — all 8 outputs built + tested against the full local channel
(2026-07-01) — proving the recipe is correct and the sole blocker is the prereq channel
upload. **Next action = monitor, not submit:** a background poll watches for
`auto-gpt-plugin-template` + `lyric-py-worker` going live (anaconda.org API); once both land,
#33883's CI can be restarted (by @pb01ka / autotick) and should go green. S12 (our own
submission) is retired.

**Contingency + ownership (F6).** #33883 is a **draft** owned by a third party (@pb01ka)
since 2026-06-24 — delivery is now outside our control. If it stalls (pb01ka inactive) or a
reviewer forces the recipe shape to change (e.g. asks to drop the `dbgpt-acc-flash-attn`
output), dbgpt may not land. **Re-evaluate submitting our own recipe if #33883 shows no
progress ~2 weeks after both prereqs go live.** Consequence of consume-not-submit: the db-gpt
feedstock will be **pb01ka's**, so rxm7706 gets **no** autotick/maintenance control over any
`dbgpt-*` output — the "Owner: rxm7706" and "feedstocks … we shipped" framing elsewhere in
this spec refers to the **retired** self-submit plan, not the actual delivery.

### langflow learnings applied to db-gpt

- **pdfminer.six / dbgpt-app `pip_check` (G76).** The original plan disabled `pip_check` on
  the `dbgpt-app` output to dodge conda-forge's pdfminer.six dist-info `Version: 0.0.0` bug
  (pdfplumber pins `pdfminer.six==<exact>`, so `pip check` saw `0.0.0` ≠ the pin). The
  langflow effort established (recorded under **G76**): staged-recipes runs `pip check` for **every** output
  **regardless of the recipe's `pip_check:` setting** — so the waiver would not have survived
  CI. Re-checked live (2026-06-27): the pdfminer.six-feedstock **rebuilt to `number: 1`**,
  and build `_1` now reports `Version: 20260107` correctly (the feedstock's own test asserts
  it). Blocker **gone** → `dbgpt-app` `pip_check` **re-enabled** (all 8 outputs now check),
  waiver dropped.
- **Verify live, not cfe metadata (G78).** This table was rebuilt from `gh pr` + channeldata,
  not `cfe-on-conda-forge-status` (e.g. `lyric-py` still read `pending-approval` post-merge).
- **Source patches, not in-build seds (G59).** Already done — the 13-pin loosening lives in
  `patches/0001-loosen-dbgpt-core-pins.patch` + `0002-loosen-dbgpt-ext-pins.patch`.

### Local rebuild + cfe metadata refresh (2026-06-27)

All 8 db-gpt-scope recipes were authored at `cfe-generated-by-version: 8.30.1` and predate
the `cfe-local-build-*` fields (v8.36.0). Rebuilt locally (rattler-build, linux-64) in
dependency order — **all 8 green** — and re-stamped to **v8.55.0** with the v8.36+ identity
fields + `cfe-local-build-*: success` populated:

| Recipe | local build | cfe-status | notes |
| ------ | ----------- | ---------- | ----- |
| `abstract-singleton` | ✅ success | confirmed-on-cf | full cfe block added (had none) |
| `auto-gpt-plugin-template` | ✅ success | pending-approval | #33765 |
| `lyric-component-ts-transpiling` | ✅ success | confirmed-on-cf | |
| `lyric-js-worker` | ✅ success | confirmed-on-cf | |
| `lyric-task` | ✅ success | confirmed-on-cf | |
| `lyric-py` | ✅ success | confirmed-on-cf | ~17 min (Rust/PyO3); import cached as `lyric` (≠ dist name — G7/G10); github-tag + compiled |
| `lyric-py-worker` | ✅ success | pending-approval | #33766 |
| `db-gpt` (8 outputs, #33883 mirror) | ✅ success | delivered-via-#33883 | 8th output `dbgpt-acc-flash-attn` (zero-dep noarch shim); dbgpt-app `pip_check` re-enabled — passes against fixed pdfminer.six `20260107` |

### C1 — `lyric-py` ARM platform gap (✅ RESOLVED — lyric-py-feedstock #2 merged 2026-06-28)

**Defect (adversarial review, 2026-06-27).** `dbgpt-app` is `noarch: python` and
hard-requires `lyric-py >=0.1.7` **unconditionally**, but `lyric-py` is a **compiled,
per-platform** package that currently ships on **only linux-64 / osx-64 / win-64**
(verified live per-subdir: **0 builds on osx-arm64, 0 on linux-aarch64**). A noarch
artifact bakes its `depends` at build time, so on **Apple Silicon (osx-arm64)** and **ARM
Linux (linux-aarch64)** the `dbgpt-app` solve fails (*nothing provides lyric-py*). It ships
**silently**: staged-recipes CI runs only linux-64/osx-64/win-64 (no ARM legs), where
lyric-py is present, so the db-gpt PR goes green while the artifact is broken on ARM. This
makes the § Status Distribution line ("osx-arm64") and AC-4 ("install **any** package")
false on those two subdirs.

**Root cause.** Not a build failure — the merged `lyric-py-feedstock` `.ci_support` never
enabled `osx_arm64` + `linux_aarch64` (only the 3 staged-recipes subdirs). The local recipe
is already cross-compile-ready (`cross-python_${{ target_platform }}`, no platform skip).

**Feasibility — VERIFIED (2026-06-27).** A local **linux-aarch64 cross-build of `lyric-py`
succeeded**: the wasmtime v26 crate cross-compiled in ~3.5 min and produced `.conda` for
py3.10–3.13. osx-arm64 uses the same Rust cross-compile path, so the wasmtime-under-ARM-sysroot
risk flagged in S4 is retired — lyric-py is genuinely ARM-buildable.

**Resolution — platform-expand `lyric-py`** (preserves B-full `[code]` parity, the Q1 choice).
**MERGED 2026-06-28: conda-forge/lyric-py-feedstock [#2](https://github.com/conda-forge/lyric-py-feedstock/pull/2)** —
adds `osx_arm64` + `linux_aarch64` via a `provider:` block. Its win legs first failed at
`Prepare conda build artifacts` (the G18 INetCache 7z crash) because the
`workflow_settings.store_build_artifacts` list still included `win_64`; dropping `- win_64`
+ rerender turned win green and the PR merged. Per G66 (merged ≠ live), the new
osx-arm64/linux-aarch64 builds landed on the channel only after the post-merge feedstock
build uploaded — at the 2026-06-28 check there were still 0 lyric-py builds on
osx-arm64/linux-aarch64. **✅ VERIFIED LIVE 2026-07-01: `lyric-py` 0.1.7 now ships on ALL 5
subdirs (linux-64, linux-aarch64, osx-64, osx-arm64, win-64) — the C1 gate is fully CLEARED.**
The db-gpt recipe itself needed no change.

- *Fallback if osx-arm64 can't be built on CI:* make `lyric-py` **optional** — strip it from
  `dbgpt-app`'s wheel `[project.dependencies]` (patch) + move to `run_constraints` (the
  langflow **G76** lean pattern). dbgpt-app stays installable everywhere; `[code]` degrades
  where lyric-py is absent. Caveat: `run_constraints` doesn't auto-install lyric-py *on any*
  platform, so this trades full `[code]` parity for universal installability — only if
  platform-expand fails.
- *Last resort:* `B-six-plus-app-patched` (drop `[code]`) **and correct** the Distribution +
  AC-4 claims.

You **cannot** platform-exclude a hard dep on one noarch artifact (G76) — "just skip ARM for
dbgpt-app" is not an option.

---

# ═══════════ HISTORICAL PLANNING CONTEXT (superseded) ═══════════

> Everything below is the **original plan** (2026-05-08 → 06-17), later
> adopted-then-superseded by **#33883**. Retained for the record. Per the
> 2026-07-01 adversarial review, several structural claims here were **factually
> wrong or overtaken**; the highest-signal ones are corrected in place, but the
> narrative below is still written as "we author and submit," which is **no longer
> true** (see § Current State). **Blanket corrections that apply throughout:**
>
> - **"7 outputs" → 8.** The shipped recipe (#33883) ships `dbgpt-acc-flash-attn`
>   as an 8th `noarch: python` output. NG1/OOS-1 excluded it as "CUDA-only,
>   GPU-tier" — that rationale is **WRONG**: upstream `dbgpt-acc-flash-attn`
>   declares `dependencies: []` and is a trivial zero-dep pure-Python shim
>   (verified 2026-07-01). It packages exactly like `dbgpt-acc-auto`.
> - **"v0.8.0" → v0.8.1.** The shipped recipe targets 0.8.1; the dep/pin tables
>   below were verified at 0.8.0 and were not re-checked against 0.8.1.
> - **"we submit db-gpt (S12)" → RETIRED.** db-gpt is delivered by #33883; do not
>   re-author or submit (G58).
> - **NG4 ("no `provider:` override") was VIOLATED** by C1's fix —
>   `lyric-py-feedstock #2` added a `provider:` block for ARM. NG4 is scoped (at
>   most) to the db-gpt feedstock, not the prereqs.

## Submission Status (2026-06-17) — ⚠ SUPERSEDED

> **Historical record only — for current state see § Readiness (live: 2026-06-27) above.**
> This section reflects the 2026-06-17 submission and is **not current**:
> 3 of the 5 prereq PRs have since **MERGED** (#33764/#33767/#33768; only #33765/#33766
> remain open); `dbgpt-app` `pip_check` was **re-enabled** (pdfminer.six fixed in build `_1`);
> the pin-loosening is implemented via **source patches** (`0001`/`0002`, G59), **not** the
> build-time `sed` described below; and the rerun closeout retro is **CFE v8.57.0 / G80**
> (the v8.28.0 retro below covers only the original 2026-06-17 effort). Q2 (= keep all caps)
> and Q3 (= `db-gpt-feedstock`) are **resolved** (see § Open Questions). Counts below ("5
> prereq PRs", "6 recipes") describe the original plan; the actionable remainder is now just
> the db-gpt submission once #33765 + #33766 land on the channel.

All 6 recipes authored via `bmad-quick-dev`, built green on linux-64, and committed to
`rxm7706/local-recipes` `main` (`8b6bb2791a` recipes, `a361f6d555` CFE-skill retro,
`d33a382824` lyric-py protoc fix). 5 prerequisite PRs are open on
`conda-forge/staged-recipes`; the db-gpt multi-output PR is held until they merge.

| PR | Recipe (story) | State |
| -- | -------------- | ----- |
| [#33765](https://github.com/conda-forge/staged-recipes/pull/33765) | auto-gpt-plugin-template (S2) | ✅ green |
| [#33764](https://github.com/conda-forge/staged-recipes/pull/33764) | lyric-py (S4) | ✅ green after the `protobuf`→`libprotobuf` protoc fix |
| [#33766](https://github.com/conda-forge/staged-recipes/pull/33766) | lyric-py-worker (S5) | ✅ green (recipe dir renamed `recipe-lyric-py-worker`→`lyric-py-worker`) |
| [#33767](https://github.com/conda-forge/staged-recipes/pull/33767) | lyric-js-worker (S6) | ✅ green |
| [#33768](https://github.com/conda-forge/staged-recipes/pull/33768) | lyric-component-ts-transpiling (S7) | ✅ green |
| — | db-gpt (S8–S12) | built green 7/7 locally; **PR not yet opened** — blocked on the 5 prereqs merging so its `check_dependencies` resolves against the channel |

**Build/CI issues found and fixed beyond the spec:**

- **S4 `protoc` (PR #33764).** conda-forge's `protobuf` is the Python bindings and ships
  **no `protoc` binary** — `lyric-rpc`'s `tonic-build` needs the compiler, which lives in
  `libprotobuf` (`bin/protoc`). The recipe's build dep was switched `protobuf`→`libprotobuf`.
  The local build had passed only because a stray `.pixi/envs/local-recipes/bin/protoc`
  leaked onto the build PATH (CI is hermetic); verified the fix by hiding the stray protoc
  and rebuilding green. Candidate CFE gotcha G30.
- **S5 recipe-dir name (PR #33766).** The web-uploaded PR dir carried an accidental
  `recipe-` prefix; renamed to `lyric-py-worker/` so the feedstock is `lyric-py-worker-feedstock`.
- **S12 `dbgpt-app` `pip_check` (db-gpt recipe).** Disabled on the `dbgpt-app` output **only**
  due to an external conda-forge `pdfminer.six` dist-info bug (reports `Version: 0.0.0`, while
  the conda version is correct; `pdfplumber` pins `pdfminer.six==…` exactly). No in-recipe fix;
  file an issue on `pdfminer.six-feedstock` and flip back to `pip_check: true` once fixed. The
  rest of the 78-dep graph was verified consistent. The other 6 outputs keep `pip_check`.

**Resolved open questions:** Q1 = `B-full`; Q2 = keep all upstream version caps (conservative
default — `tenacity<=8.3.0`, `fastapi<0.113.0`, `numpy<2.0.0`, `sqlalchemy<2.0.29`,
`onnxruntime<=1.18.1`); Q3 = `db-gpt-feedstock` (recipe sets `extra.feedstock-name: db-gpt`).
13 upstream `==` pins loosened to `>=` via a build-time source-pyproject `sed` in the
`dbgpt-core`/`dbgpt-ext` outputs (the wheel METADATA must be loosened too when `pip_check` is on).

**Retro:** CFE skill v8.28.0 (gotchas G26–G29). Project-memory: `project_dbgpt_conda_forge_8b`.

**Next step:** when #33764–#33768 merge, open the db-gpt multi-output PR (its CI then resolves
the 5 prereqs from the channel).

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

  | Package                            | Build dependency                             | conda-forge status                                                                                                                      |
  | ---------------------------------- | -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
  | `lyric-task`                     | pure Python                                  | trivial — already pip-installable                                                                                                      |
  | `lyric-py`                       | maturin + protoc                             | feasible — `libprotobuf` provides protoc on conda-forge                                                                                             |
  | `lyric-py-worker`                | `componentize-py` + `wasm-tools`         | both**NOT on conda-forge**                                                                                                        |
  | `lyric-js-worker`                | `nodejs` + `@bytecodealliance/jco` (npm) | jco**NOT on conda-forge**                                                                                                         |
  | `lyric-component-ts-transpiling` | `cargo build --target wasm32-wasip1`       | `rust-std-wasm32-wasip1` **NOT on conda-forge** (only `wasm32-unknown-unknown` and `wasm32-unknown-emscripten` are shipped) |

  Two paths exist for shipping the workers on conda-forge:


  - **Vendor the upstream `.wasm` blob** as a `noarch: python` recipe
    (the `itkwasm-downsample-wasi` precedent on main conda-forge —
    see § "WASM toolchain on conda-forge — current state" for the full
    pattern). Each worker recipe is ~30 lines and declares only
    `lyric-task` as a runtime dep (verified against upstream
    `pyproject.toml`, 2026-06-17). The WASI engine that executes the
    blob is **`lyric-py`** — its embedded `wasmtime`/`wasmtime-wasi`
    Rust crates (v26), compiled from source in S4 — **not** the
    standalone `wasmtime-py` conda package. (`itkwasm` uses
    `wasmtime-py`; Lyric is structurally analogous but links its own
    runtime through `lyric-py`.) **This is the realistic path.**
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

**Runtimes and bindings on conda-forge already (✓):** *(versions below are a 2026-06-17
snapshot — several have since advanced, e.g. `python-wasmer` 1.2.0, `wasm-pack` 0.15.0,
`pyodide-build` 0.35.1; the on-cf / not-on-cf status is what's load-bearing, not the exact versions.)*

| Package                                                | Version | Origin            | Purpose                                                                                                                                                                           |
| ------------------------------------------------------ | ------- | ----------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `wasmtime-py`                                        | 45.0.0  | Bytecode Alliance | Python embedding of Wasmtime — bundles `_libwasmtime.so` (the runtime) inside the conda artifact, so installing this gives you both the Python API *and* the Wasmtime engine |
| `wasmer`                                             | 7.1.0   | Wasmer            | Standalone Wasmer CLI/runtime                                                                                                                                                     |
| `python-wasmer`                                      | 1.1.0   | Wasmer            | Wasmer Python bindings                                                                                                                                                            |
| `python-wasmer-compiler-{cranelift,llvm,singlepass}` | 1.1.0   | Wasmer            | Compiler-backend variants                                                                                                                                                         |

**Build tools on conda-forge already (✓):**

| Package                                | Version | Origin              | Purpose                                                 |
| -------------------------------------- | ------- | ------------------- | ------------------------------------------------------- |
| `emscripten`                         | 4.0.9   | Emscripten          | C/C++ → wasm32-emscripten via emcc                     |
| `emsdk`                              | 3.1.46  | Emscripten          | SDK manager                                             |
| `binaryen`                           | 121     | WebAssembly CG      | WASM optimizer (used by emscripten)                     |
| `wabt`                               | 1.0.41  | WebAssembly CG      | WebAssembly Binary Toolkit (`wasm2wat`, `wat2wasm`) |
| `wasm-pack`                          | 0.14.0  | Rust+WebAssembly WG | Rust → WASM packager                                   |
| `pyodide-build`                      | 0.34.3  | Pyodide             | Pyodide build infrastructure                            |
| `pyodide-py`                         | 0.22.0  | Pyodide             | Pyodide Python helpers                                  |
| `micropip`                           | 0.11.1  | Pyodide             | In-browser pip emulator                                 |
| `rust-std-wasm32-unknown-unknown`    | 1.95.0  | Rust                | Rust target — bare WASM, no syscalls                   |
| `rust-std-wasm32-unknown-emscripten` | 1.95.0  | Rust                | Rust target — emscripten ABI                           |
| `cargo-c`                            | 0.10.22 | Rust                | Cargo C-API subcommand (peripheral)                     |

**Existing WASI-target packages on conda-forge (the precedent that
matters):**

| Package                           | Version | Pattern                                                                                                                                   |
| --------------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `itkwasm`                       | 1.0b195 | Python wrapper over wasmtime-py —`_libwasmtime.so` is built into wasmtime-py, so itkwasm runs WASI binaries without needing wasi-sdk   |
| `itkwasm-downsample`            | 1.8.1   | Pure-Python loader; depends on `itkwasm` + `itkwasm-downsample-wasi`                                                                  |
| `itkwasm-downsample-wasi`       | 1.8.1   | **`noarch: python`. Just `pip install`s the upstream PyPI sdist that ships the pre-built `.wasm` blob.** Recipe is ~30 lines. |
| `itkwasm-downsample-emscripten` | 1.8.1   | Emscripten variant — same pattern, different blob                                                                                        |

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

| Tool                                                             | Origin                  | Source-build use                                                                                                       |
| ---------------------------------------------------------------- | ----------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `wasmtime` (standalone CLI)                                    | Bytecode Alliance       | Run/test WASI binaries outside Python —`wasmtime-py` already provides the runtime library, so this is rarely needed |
| `wasi-sdk`                                                     | WebAssembly CG          | C/Rust → wasm32-wasi compilation                                                                                      |
| `wasi-libc`                                                    | WebAssembly CG          | Standalone WASI libc                                                                                                   |
| `wasm-tools`                                                   | Bytecode Alliance       | `wasm-tools strip` / `wasm-tools component new` — used by upstream `lyric-py-worker` Makefile                   |
| `componentize-py`                                              | Bytecode Alliance       | Python → WASM Component packager — used by upstream `lyric-py-worker` Makefile                                     |
| `jco`                                                          | Bytecode Alliance (npm) | JavaScript Component Tools — used by upstream `lyric-js-worker` Makefile                                            |
| `wit-bindgen`                                                  | Bytecode Alliance       | Component interface generator                                                                                          |
| `cargo-component`                                              | Bytecode Alliance       | Cargo subcommand for WASM Component Model                                                                              |
| `rust-std-wasm32-wasi` / `wasm32-wasip1` / `wasm32-wasip2` | Rust                    | Rust target — required for `cargo build --target wasm32-wasi*`                                                      |

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
vendor the upstream PyPI sdist's pre-built `.wasm`. The WASI engine is
supplied by `lyric-py`'s embedded `wasmtime` Rust crate (built from
source in S4) — **not** the standalone `wasmtime-py` package. No
componentize-py, no jco, no wasi-sdk, no rust-std-wasm32-wasip1 —
those are only required if we choose to rebuild the WASM artifacts
from source, which conda-forge has not historically required for this
class of package. The `B-full` cost estimate drops from "≥13 PRs,
multi-week, includes Bytecode Alliance toolchain upstreaming" to
**6 PRs** (5 prerequisite recipes + the DB-GPT multi-output), of which
only `lyric-py` (Rust+maturin+protoc, cocoindex-class) is non-trivial.
The 3 worker recipes are each ~30 lines following the
`itkwasm-downsample-wasi` template; `abstract-singleton` + `lyric-task`
already ship.

### What's available to leverage

- **`conda-forge-expert` skill (v8.x current)** at
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
  to the DB-GPT 7-output recipe.

---

## Goals

- **G1.** Land all 7 dbgpt-* outputs (`dbgpt`, `dbgpt-client`,
  `dbgpt-ext`, `dbgpt-serve`, `dbgpt-app`, `dbgpt-acc-auto`,
  `dbgpt-sandbox`) on conda-forge as a single multi-output recipe in
  `recipes/db-gpt/`, plus the prerequisite recipes (S1–S7; S1 + S3
  already ship on conda-forge, 5 to build). Coherent = all
  outputs share the same source archive, same version, and resolve
  their internal `dbgpt-*` cross-dependencies via `pin_subpackage`.
  **[CORRECTED 2026-07-01: the shipped recipe (#33883) has 8 outputs — it also
  ships `dbgpt-acc-flash-attn` (a zero-dep noarch shim); NG1's exclusion was
  wrong. See § Current State.]**
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

- **NG1.** ~~No `dbgpt-acc-flash-attn` recipe — CUDA-only, GPU-tier.~~
  **OVERTURNED 2026-07-01 (adversarial review).** This rationale was factually
  wrong: upstream `dbgpt-acc-flash-attn` declares `dependencies: []` and is a
  trivial zero-dep **pure-Python noarch shim** (`__init__.py` + `_version.py`) —
  it is NOT the heavy CUDA `flash-attn` library (the spec conflated the two). The
  shipped recipe (#33883) correctly ships it as the 8th `noarch: python` output;
  it built + `pip_check`-passed green locally. (`flash_attn` is imported lazily,
  so the shim installs everywhere; it is only *functional* where the user also
  has the GPU `flash-attn` package.)
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
- **NG4.** No feedstock-level CI customization on the **db-gpt** feedstock
  beyond conda-forge defaults. **[CORRECTED 2026-07-01: this does NOT hold for
  the prereq feedstocks — C1 required a `provider:` override on
  `lyric-py-feedstock #2` to ship osx-arm64 + linux-aarch64. NG4 as originally
  written ("no `provider:` override") was violated by that fix; it is scoped here
  to the db-gpt feedstock only.]**
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
  tracked in `_bmad-output/projects/local-recipes/implementation-artifacts/deferred-work.md`.

---

## User Stories

Q1 is resolved (**B-full** — see § "Open Questions"). 13 stories total.

> **▶ STATUS (live 2026-06-27): S1–S11 are DONE.** All recipes are authored + built green
> locally; S1/S3 (`abstract-singleton`, `lyric-task`) already shipped; the S2/S4–S7 prereq
> PRs are filed (#33764/#33767/#33768 merged, #33765/#33766 open); S8–S11 are complete in
> `recipes/db-gpt/`. **The per-story "Blocked by … entering review queue" lines below are
> HISTORICAL** — several name S1/S3 PRs that never existed (those recipes already ship). The
> only remaining work is **S12 (submit db-gpt)**, gated on (a) #33765 + #33766 **merging and
> landing on the channel** (not merely queued — G66), and (b) the **C1 `lyric-py`
> platform-expansion**. See § Readiness.

Post-audit (2026-06-17): S1 + S3 are already satisfied —
`abstract-singleton` (1.0.1) and `lyric-task` (0.1.7) already ship on
conda-forge — so the actionable work is **5 prerequisite recipes**
(S2, S4, S5, S6, S7) + the DB-GPT multi-output (S8–S12) = **6
staged-recipes PRs**.

**Execution waves** (parallelism within each wave is fine; the next
wave depends on the previous wave's PRs entering staged-recipes review
queue, not necessarily merging):

| Wave | Stories    | Description                            |
| ---- | ---------- | -------------------------------------- |
| 1    | S1, S3     | ✅ Already on conda-forge — no PR (abstract-singleton 1.0.1, lyric-task 0.1.7) |
| 2    | S2, S4     | Unblocked now (their Wave-1 deps already ship) |
| 3    | S5, S6, S7 | Depend on S4 (lyric-py) entering review queue (S3 already ships) |
| 4    | S8–S12    | The DB-GPT multi-output recipe stories |

### Story S0 — Decide Q1 (`dbgpt-app` inclusion path)

**Status**: Resolved 2026-05-08 — **Decision: `B-full`**.

**Rationale**: The `itkwasm-downsample-wasi` precedent on main
conda-forge (verified 2026-06-17 at
`conda-forge/itkwasm-downsample-wasi-feedstock`, a `noarch: python`
**meta.yaml** recipe) makes the lyric-* worker recipes ~30 lines each —
a `noarch: python` recipe that pip-installs the upstream PyPI sdist
whose contents include a pre-built `.wasm` blob. The WASI runtime that
executes the blob is supplied by **`lyric-py`** (its embedded
`wasmtime` Rust crate, built from source in S4), **not** the
standalone `wasmtime-py` package (45.0.0 on conda-forge). This drops
the B-full estimate from "≥13 PRs, multi-week, includes upstreaming
Bytecode Alliance toolchain" to a multi-day effort of which only
`lyric-py` is non-trivial — and the 2026-06-17 audit shrank it
further: `abstract-singleton` + `lyric-task` already ship, so the
actionable set is **6 PRs** (5 prerequisite recipes + the DB-GPT
multi-output). dbgpt-app feature parity (including the code-execution
sandbox) is worth the prerequisite chain at this cost.

**Fallback**: If a conda-forge reviewer rejects the vendor-the-blob
pattern for a lyric-* worker despite the precedent, drop the
offending worker(s) and switch the DB-GPT recipe to
`B-six-plus-app-patched` for the rejected extras (S12 fallback path
documented).

### Story S1 — Recipe: `abstract-singleton`

**Status**: ✅ **RESOLVED — no work needed.** `abstract-singleton`
already ships on conda-forge (v1.0.1, verified 2026-06-17) and is built
clean locally (`abstract-singleton-1.0.1-pyhc364b38_0.conda`). Skip
submission — S2's `auto-gpt-plugin-template` resolves it from the
channel. The acceptance criteria below are retained for the record.

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

**Status**: ✅ **RESOLVED — no work needed.** `lyric-task` already
ships on conda-forge (v0.1.7, verified 2026-06-17) and is built clean
locally (`lyric-task-0.1.7-pyhcba1bba_0.conda`). Skip submission —
`lyric-py` and the 3 workers resolve it from the channel. The
acceptance criteria below are retained for the record.

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
- Source from upstream GitHub tag `v0.1.7` (verified 2026-06-17 — the
  tag scheme is plain `vX.Y.Z`, **not** `pylyric-v0.1.7`). Prefer the
  GitHub archive over the PyPI sdist: the sdist does **not** ship a
  LICENSE file (its `Cargo.toml` `include` lists `/LICENSE` but the
  published tarball omits it), whereas the `v0.1.7` archive ships the
  MIT `LICENSE` at the root.
- Build deps: `${{ compiler('rust') }}`, `${{ compiler('c') }}`,
  `${{ stdlib('c') }}`, `libprotobuf` (provides `protoc`; conda-forge's
  Python `protobuf` package ships **no** protoc binary — see § Submission
  Status S4 protoc note), `cargo-bundle-licenses`, `pkg-config`.
  **`maturin` is a host dep, not a build dep.**
- Host deps: `python`, `pip`, `maturin`.
- Run deps: `python >=3.10`, `msgpack-python`, `cloudpickle`,
  `lyric-task >=0.1.7`.
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

**Estimated effort**: 4–6 h. Cocoindex-class. Confirmed build inputs
(2026-06-17): `maturin >=1.7,<2` backend, `[tool.maturin] bindings =
pyo3`, protoc via `tonic-build` (`crates/lyric-rpc/build.rs` compiles
`proto/task.proto`), and the `wasmtime`/`wasmtime-wasi` crates (v26)
compiled from source via cargo-vendoring — **not** a pre-built
wasmtime, and **not** the conda `wasmtime-py` package. **NOT abi3**
(no `abi3` feature in any Cargo.toml) — build per-Python-version; the
abi3-matrix-collapse pattern does not apply. Pitfalls: protoc/protobuf
version, cross-platform Rust target setup, Windows import-lib
(`python3-dll-a`), and `wasmtime` crate build time under the
conda-forge sysroot.

### Story S5 — Recipe: `lyric-py-worker` (itkwasm-pattern)

**Goal**: Land `lyric-py-worker` as a `noarch: python` recipe that
pip-installs the upstream PyPI sdist (which contains the pre-built
~28 MB `python_worker.wasm` blob). Pattern mirrors
`itkwasm-downsample-wasi-feedstock`.

**Acceptance criteria**:

- `recipes/lyric-py-worker/recipe.yaml` validates clean.
- `noarch: python` (hatchling shim; the `.wasm` is architecture-
  independent WASI data — no compiler, no Rust, no maturin).
- Source from PyPI sdist (`lyric_py_worker-0.1.7.tar.gz`, ~10.8 MB —
  contains pre-built `src/lyric_py_worker/python_worker.wasm`, ~28 MB
  uncompressed; accepted per itkwasm precedent).
- Run-deps: `lyric-task >=0.1.7` only.
  Upstream's `pyproject.toml` declares **`lyric-task`** as the sole
  runtime dep — **not** `lyric-py` and **not** `wasmtime-py`. The WASI
  engine that executes the blob is supplied by `lyric-py` (its embedded
  `wasmtime` Rust crate), which `dbgpt-core[code]` co-installs; the
  worker package itself only locates the `.wasm` via
  `importlib.resources`. Adding undeclared deps would violate the
  mirror-upstream convention and is unnecessary.
- License: MIT, but the PyPI sdist ships **no** LICENSE file — vendor
  the MIT text from the GitHub `v0.1.7` tag (CFE gotcha G4 — license-vendoring; not Goal G4) or ship
  LICENSE in-recipe. PyPI `license` metadata is empty.
- Tests: `import lyric_py_worker`; verify the `.wasm` file exists
  inside the installed package directory; do not invoke the worker
  (would need a full WASI runtime test harness).
- PR body **must** cite the `itkwasm-downsample-wasi` precedent (a
  `noarch: python` **meta.yaml** feedstock that pip-installs a PyPI
  sdist carrying a vendored `.wasm`) and link
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
- Source from PyPI sdist (`lyric_js_worker-0.1.7.tar.gz`, ~3.5 MB —
  contains `src/lyric_js_worker/javascript_worker.wasm`, ~10.3 MB
  uncompressed).
- Run-deps: `lyric-task >=0.1.7` only
  (same rationale as S5 — `lyric-py`/`wasmtime-py` are NOT upstream-
  declared deps).
- Same license (MIT, vendor from GitHub `v0.1.7` — sdist omits
  LICENSE), test, and PR-body pattern as S5.
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
  (`lyric_component_ts_transpiling-0.1.7.tar.gz`, ~1.8 MB — contains
  `src/lyric_component_ts_transpiling/component_ts_transpiling.wasm`,
  ~7.35 MB uncompressed).
- **`requires-python` is `>=3.10`** for this package (a higher floor
  than the `>=3.8` of the other lyric-* members; 3.10 is the
  conda-forge floor anyway, so no `context:` override is needed).
- Run-deps: `lyric-task >=0.1.7` only
  (same rationale as S5).
- Same license (MIT, vendor from GitHub `v0.1.7` — sdist omits
  LICENSE), test, and PR-body pattern as S5.
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
- Each output's `script:` is `cd packages/<member-name> && ${{ PYTHON }} -m pip install . --no-deps --no-build-isolation -vv` (note the
  `dbgpt`-PyPI-name-vs-`dbgpt-core`-source-dir asymmetry — see
  Technical Approach § "Internal name mapping").

**Wave**: 4.

**Estimated effort**: 45 min.

### Story S9 — Resolve internal cross-dependencies via `pin_subpackage`

**Goal**: Wire each output's `requirements.run` so internal `dbgpt-*`
references resolve to *this* recipe's outputs at the same build, not
to an unrelated upstream PyPI package.

**Acceptance criteria**:

**Critical: conda has no "extras" mechanism.** Every upstream
`pkg[extra]` reference must be *flattened* — the recipe output that
depends on `pkg[extra]` carries that extra's deps directly, because the
sibling `pkg` output is built without extras. This applies to
`dbgpt-client` (`dbgpt[client,cli]`) and especially `dbgpt-app` (nine
core extras + two ext extras). See Technical Approach § "dbgpt-app
flattened run-deps" for the authoritative list. Verified against the
v0.8.0 `pyproject.toml` files, 2026-06-17.

- `dbgpt-ext` run-deps: `${{ pin_subpackage('dbgpt', exact=True) }}`
  + external `pymysql` (ext base dep).
- `dbgpt-client` run-deps: `${{ pin_subpackage('dbgpt', exact=True) }}`
  + `${{ pin_subpackage('dbgpt-ext', exact=True) }}` (upstream
  `dbgpt[client,cli]` + `dbgpt_ext`), **plus the flattened
  `dbgpt-core[client,cli]` deps** (`httpx`, `fastapi >=0.100.0,<0.113.0`,
  `tenacity <=8.3.0`, `prettytable`, `click`, `psutil`, `colorama`,
  `tomlkit`, `rich`) + `shortuuid`, `sqlalchemy >=2.0.25,<2.0.29`,
  `msgpack-python`, `cloudpickle`, `beautifulsoup4` (under-declared hard
  import via `dbgpt_ext.rag`, G27).
- `dbgpt-serve` run-deps: `${{ pin_subpackage('dbgpt-ext', exact=True) }}`
  (which transitively pins `dbgpt`). serve has no other declared deps.
- `dbgpt-acc-auto` run-deps: empty (upstream `dependencies = []`).
- `dbgpt-sandbox` run-deps: external only (`psutil`, `colorama`,
  `docker-py`, `fastapi`, `uvicorn`, `pydantic`, `python-multipart`,
  `selenium`, `typing-extensions`).
- `dbgpt-app` run-deps: exact pins on all six siblings (`dbgpt`,
  `dbgpt-ext`, `dbgpt-serve`, `dbgpt-client`, `dbgpt-sandbox`,
  `dbgpt-acc-auto`) **plus the full flattened union of every extra it
  activates** — `dbgpt[client,cli,agent,simple_framework,framework,
  code,proxy_openai,proxy_tongyi,proxy_zhipuai]` + `dbgpt-ext[rag,
  storage_chromadb]` + direct `aiofiles`, `httpx >=0.24.0`,
  `pyparsing`. That union is **69 external deps** (Technical Approach
  § "dbgpt-app flattened run-deps"), and notably includes
  `auto-gpt-plugin-template` (S2), the lyric-* stack (S4–S7),
  `socksio` (the conda dep behind `httpx[socks]`), `chromadb`,
  `beautifulsoup4`, `markdown`, `alembic`, `tenacity`, and `sqlalchemy`.
  `qianfan` is **not** included — `proxy_qianfan` is not among the
  activated extras.

**Wave**: 4.

**Estimated effort**: 30 min.

### Story S10 — Loosen all `==` pins per project convention

**Goal**: Replace every upstream `package==X.Y.Z` pin with `package >=X.Y.Z`, `package >=X.Y` (drop patch level), or a justified narrow range, with an inline `# TODO: tighten once <pin> stays current` comment per the `feedback_loosen_pins.md` rule.

**Acceptance criteria**:

- No `==` pins remain in any output's `requirements.run` except where
  upstream's API genuinely requires it (re-verify in upstream
  changelog before keeping any). Expected zero kept after audit.
- Each loosened pin has a TODO comment naming the original upstream
  pin verbatim (e.g., `# TODO: tighten once aiohttp==3.8.4 is no longer the upstream floor`).
- Pins that are already loose upstream (e.g., `pydantic>=2.6.0`) carry
  through unchanged.

**Pins to audit (authoritative — the flattened dbgpt-app union,
verified 2026-06-17; the Technical Approach pin table is the source of
truth)**: 13 exact pins — `aiohttp==3.8.4`, `chardet==5.1.0`,
`importlib-resources==5.12.0`, `pandas==2.2.3`, `psutil==5.9.4`,
`colorama==0.4.6`, `gTTS==2.3.1`, `alembic==1.12.0`, `openpyxl==3.1.2`,
`xlrd==2.0.1`, `duckdb-engine==0.9.1`, `sqlparse==0.4.4`,
`spacy==3.7` — plus 5 upper-bound-capped ranges: `tenacity<=8.3.0`,
`fastapi>=0.100.0,<0.113.0`, `numpy>=1.21.0,<2.0.0`,
`sqlalchemy>=2.0.25,<2.0.29`, `onnxruntime>=1.14.1,<=1.18.1`.
(`mysqlclient==2.1.0` and `oracledb==3.1.0` were dropped — they live
in datasource extras that `dbgpt-app` does not activate.)

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

### Story S12 — Validate, build, and submit DB-GPT multi-output — ⚠ RETIRED

> **RETIRED 2026-07-01: DO NOT EXECUTE.** db-gpt is delivered by #33883 (@pb01ka).
> Submitting our own db-gpt PR would open a competing recipe (G58). The goal / AC /
> checklist below are historical; our only action is to consume `dbgpt` once
> #33883 lands (see § Current State).

**Goal (historical)**: Run the full conda-forge-expert 9-step loop on the
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

**Blocked by** (corrected — H4/G66): db-gpt's CI test-env needs its prereqs **merged AND
live on the conda-forge channel**, not merely "in the review queue." Live gate (2026-06-27):
#33765 (`auto-gpt-plugin-template`) + #33766 (`lyric-py-worker`) must merge + land on the
channel; the other prereqs already ship. The **C1 `lyric-py` platform-expansion** (osx-arm64
+ linux-aarch64) is **MERGED** (lyric-py-feedstock #2, 2026-06-28) — confirm the ARM artifacts
are **live on the channel** (G66; not yet at the 2026-06-28 check) before db-gpt submission.

**Submission checklist (G62–G65):** strip every `extra.cfe-*` key + the `#### CFE` block
(G62); branch `add-recipe-db-gpt` on `rxm7706/staged-recipes` off conda-forge main; replace
the PR template with a completed-checklist body (G63); run the CI-parity lint via `pixi exec`
with the current conda-smithy (G65); after green, **one** language-team ping (G64); PR body
cross-references #33765/#33766.

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

A single `source.url: https://github.com/eosphoros-ai/DB-GPT/archive/v${{ version }}.tar.gz`
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
`context:` because `conda-forge-pinning` provides the default. Verified 2026-06-27: the
compiled transitive deps (`chromadb`/`spacy`/`onnxruntime`) ship py3.10 on osx-arm64, so the
floor holds across subdirs — no raise needed (the `onnxruntime` cap × py3.10 intersection is
the Q2/C1 re-verify item).

### FR-6: Internal cross-deps use `pin_subpackage(exact=True)`

Each `dbgpt-*` cross-reference inside the recipe pins to the exact
build of the same multi-output run, never to a generic version
constraint. This avoids accidental version drift between sibling
outputs that are conceptually one workspace.

### FR-7: License is single-file, top-level

`about.license: MIT` and `about.license_file: LICENSE` at the top
level. No per-output license overrides — every output is MIT and they
all share the root file.

### FR-8: Two pin-loosening patches in the happy path; a code-extra patch only on fallback

The `B-full` happy path ships **two** source patches that loosen upstream's
exact (`==`) pins so the wheel METADATA matches the loosened conda run-deps
and `pip_check` passes (G26 + G59 — patch, not in-build `sed`):

- `recipes/db-gpt/patches/0001-loosen-dbgpt-core-pins.patch` (dbgpt-core pyproject)
- `recipes/db-gpt/patches/0002-loosen-dbgpt-ext-pins.patch` (dbgpt-ext pyproject)

Both are top-level `source.patches`, applied once to the shared source tree.

The happy path ships **no** patch against `dbgpt-app/pyproject.toml` — all
extras (`code`, `agent`, …) resolve because every transitive dep lands on
conda-forge (S2/S4–S7 + the two already-shipping prereqs). A code-extra patch
is authored **only** if S5/S6/S7 are rejected during review (S12 fallback): a
single `recipes/db-gpt/patches/0003-drop-code-extra-from-dbgpt-app.patch`
removing the `code` extra reference from `dbgpt-app`. That one is *contingent*;
it is not part of S8–S11.

---

## Technical Approach

### Stack

- **Recipe format**: rattler-build v1 (`schema_version: 1`).
- **Build backend**: each output uses upstream's `hatchling.build`
  unmodified. No custom build hooks.
- **Source**: upstream GitHub tarball at
  `https://github.com/eosphoros-ai/DB-GPT/archive/v0.8.0.tar.gz`.
  Compute the SHA256 fresh during S8 — do not paste from anywhere
  outside the recipe or upstream API.

### File layout (post-S12)

```
recipes/
  db-gpt/
    recipe.yaml              # the 7-output multi-output recipe
    patches/
      0001-loosen-dbgpt-core-pins.patch          # happy path (G59 pin-loosening)
      0002-loosen-dbgpt-ext-pins.patch           # happy path (G59 pin-loosening)
      0003-drop-code-extra-from-dbgpt-app.patch  # ONLY if S12 fallback fires
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
Independent (no internal cross-deps):
  dbgpt-acc-auto   — upstream `dependencies = []`
  dbgpt-sandbox    — external runtime deps only

dbgpt (core)       — no internal deps; base of the family
  ├── dbgpt-ext           depends on dbgpt
  │     └── dbgpt-serve   depends on dbgpt-ext (dbgpt transitively)
  └── dbgpt-client        depends on dbgpt AND dbgpt-ext

dbgpt-app ── pin_subpackage(exact=True) on all six siblings:
             dbgpt, dbgpt-ext, dbgpt-serve, dbgpt-client,
             dbgpt-sandbox, dbgpt-acc-auto
          ── PLUS the flattened deps of every extra it activates.
             Conda has no "extras" mechanism (see S9), and the sibling
             `dbgpt` output is built WITHOUT extras, so dbgpt-app must
             carry the union of all activated extras' deps directly.
             dbgpt-app's upstream dep string activates:
               dbgpt[client,cli,agent,simple_framework,framework,
                     code,proxy_openai,proxy_tongyi,proxy_zhipuai]
               dbgpt-ext[rag,storage_chromadb]
             => run-deps must also include auto-gpt-plugin-template (S2,
                from dbgpt-core[agent]) and the lyric-* stack lyric-py +
                3 workers (S4–S7, from dbgpt-core[code]); lyric-task (S3)
                arrives transitively via lyric-py.
```

### dbgpt-app flattened run-deps

This is the authoritative flattened union S9 references. `dbgpt-app` activates
`dbgpt[client,cli,agent,simple_framework,framework,code,proxy_openai,proxy_tongyi,proxy_zhipuai]`
+ `dbgpt-ext[rag,storage_chromadb]`; conda has no extras, so the output carries that
union directly. The **literal source of truth** is the `dbgpt-app` output's `run:`
block in `recipes/db-gpt/recipe.yaml` — **69 external deps** plus the 6
`pin_subpackage(exact=True)` siblings (`dbgpt`, `dbgpt-ext`, `dbgpt-serve`,
`dbgpt-client`, `dbgpt-sandbox`, `dbgpt-acc-auto`).

The 69 external deps (✱ = landed by a prerequisite story; ⚑ = upper-bound cap kept, Q2):

> aiofiles, httpx, pyparsing, aiohttp, chardet, importlib_resources, cachetools,
> pydantic, typeguard, snowflake-id, typing_inspect, tomli, fastapi⚑, tenacity⚑,
> prettytable, click, psutil, colorama, tomlkit, rich, termcolor, pandas, numpy⚑,
> auto-gpt-plugin-template✱, mcp, jinja2, uvicorn, shortuuid, sqlalchemy⚑,
> msgpack-python, cloudpickle, pympler, python-duckdb, duckdb-engine, schedule, sqlparse,
> python-multipart, coloredlogs, seaborn, gtts, pymysql, jsonschema, python-jsonpath,
> tokenizers, alembic, openpyxl, xlrd, gitpython, python-graphviz, cryptography, pyzmq,
> lyric-py✱, lyric-py-worker✱, lyric-js-worker✱, lyric-component-ts-transpiling✱,
> openai, tiktoken, socksio, dashscope, spacy, markdown, beautifulsoup4, python-pptx,
> python-docx, olefile, pypdf, pdfplumber, onnxruntime⚑, chromadb.

The 5 ✱ deps are landed by S2/S4–S7 (`auto-gpt-plugin-template` + `lyric-py` + the 3
workers); `lyric-task` arrives transitively via `lyric-py`. The remaining 64 are on
conda-forge (§ Dependencies and Constraints → "External dependencies that must already
exist"). `python-duckdb` is the conda name for the `duckdb` PyPI binding (bare `duckdb` is
the CLI/old, linux-64+noarch only — G10/M4). `beautifulsoup4` is an under-declared hard import surfaced via `dbgpt_ext.rag`
(G27). **`lyric-py` carries the osx-arm64/linux-aarch64 caveat — see § Readiness → C1.**

### Build matrix

`noarch: python` collapses the *build* matrix to one job (`linux-64`) — there are no
native artifacts to compile. **But a noarch output must still SOLVE on every platform**,
and `dbgpt-app` pulls compiled transitive deps (`lyric-py`, `onnxruntime`, `chromadb`,
`spacy`, `tokenizers`, `pyzmq`, `cryptography`, `numpy`, `pandas`). Before submission, run
the per-subdir check (G40): confirm every compiled transitive dep ships a build at the
recipe's `python_min` on linux-64 / osx-64 / **osx-arm64** / win-64 / **linux-aarch64**.
The earlier "native linux-64 build is sufficient" claim was the **C1** root cause — it
caught nothing because the gap is in the *solve*, not the *build*.

### Pin-loosening reference

The pins below are the audit list for Story S10. The "loosened to" column
is the proposed value subject to `check_dependencies` confirmation.

| Upstream pin                    | Loosened to                      | Notes                                                        |
| ------------------------------- | -------------------------------- | ------------------------------------------------------------ |
| `aiohttp==3.8.4`              | `aiohttp >=3.8.4`              | conda-forge has 3.10+                                        |
| `chardet==5.1.0`              | `chardet >=5.1.0`              |                                                              |
| `importlib-resources==5.12.0` | `importlib_resources >=5.12.0` | hyphen→underscore for conda                                 |
| `pandas==2.2.3`               | `pandas >=2.2.3`               |                                                              |
| `psutil==5.9.4`               | `psutil >=5.9.4`               |                                                              |
| `colorama==0.4.6`             | `colorama >=0.4.6`             |                                                              |
| `gTTS==2.3.1`                 | `gtts >=2.3.1`                 | conda name is lowercase                                      |
| `alembic==1.12.0`             | `alembic >=1.12.0`             |                                                              |
| `openpyxl==3.1.2`             | `openpyxl >=3.1.2`             |                                                              |
| `xlrd==2.0.1`                 | `xlrd >=2.0.1`                 |                                                              |
| `duckdb-engine==0.9.1`        | `duckdb-engine >=0.9.1`        |                                                              |
| `sqlparse==0.4.4`             | `sqlparse >=0.4.4`             |                                                              |
| `spacy==3.7`                  | `spacy >=3.7`                  | from dbgpt-ext[rag]                                          |
| `tenacity<=8.3.0`             | `tenacity >=8.0,<9`            | from dbgpt-core[client]; upper bound retained (Q2)          |
| `fastapi>=0.100.0,<0.113.0`   | `fastapi >=0.100.0,<0.113.0`   | cap KEPT (Q2 resolved: keep all); matches the recipe        |
| `numpy>=1.21.0,<2.0.0`        | `numpy >=1.21,<2`             | keep <2 cap + TODO (Q2; upstream code targets NumPy 1)      |
| `sqlalchemy>=2.0.25,<2.0.29`  | `sqlalchemy >=2.0.25,<2.0.30`  | upstream cap (simple_framework); keep, narrow (Q2)          |
| `onnxruntime>=1.14.1,<=1.18.1`| `onnxruntime >=1.14.1,<=1.18.1`| cap KEPT (Q2 resolved); chromadb-compat — re-verify at S10  |

The capped rows are "audit during S10" — drop a cap only if upstream
runs CI against the newer major (NumPy 2 / ONNX 1.20+ / SQLAlchemy
2.0.29+). If unsure, keep the cap and add a TODO (Q2 default).
`mysqlclient`/`oracledb` were removed — they live in datasource extras
`dbgpt-app` does not activate.

### Internal name mapping

The conda recipe names map to PyPI names map to source directories as
follows. **Do not confuse them.**

| Conda recipe `outputs[i].package.name` | PyPI dist name     | Source subdir                                 | Hatch wheel target     |
| ---------------------------------------- | ------------------ | --------------------------------------------- | ---------------------- |
| `dbgpt`                                | `dbgpt`          | `packages/dbgpt-core`                       | `src/dbgpt`          |
| `dbgpt-client`                         | `dbgpt-client`   | `packages/dbgpt-client`                     | `src/dbgpt_client`   |
| `dbgpt-ext`                            | `dbgpt-ext`      | `packages/dbgpt-ext`                        | `src/dbgpt_ext`      |
| `dbgpt-serve`                          | `dbgpt-serve`    | `packages/dbgpt-serve`                      | `src/dbgpt_serve`    |
| `dbgpt-acc-auto`                       | `dbgpt-acc-auto` | `packages/dbgpt-accelerator/dbgpt-acc-auto` | `src/dbgpt_acc_auto` |
| `dbgpt-sandbox`                        | `dbgpt-sandbox`  | `packages/dbgpt-sandbox`                    | `src/dbgpt_sandbox`  |
| `dbgpt-app`                          | `dbgpt-app`      | `packages/dbgpt-app`                        | `src/dbgpt_app`      |

Note the asymmetry: PyPI's `dbgpt` lives under `packages/dbgpt-core/`
in the source tree.

`packages/dbgpt-accelerator/` contains a **second** member,
`dbgpt-acc-flash-attn`, alongside `dbgpt-acc-auto` (verified at the
v0.8.0 tag, 2026-06-17). **[CORRECTED 2026-07-01: `dbgpt-acc-flash-attn` IS
shipped — it is the 8th output of the adopted #33883 recipe. Upstream declares
`dependencies: []` (a zero-dep noarch shim), so NG1/OOS-1's "CUDA-only" exclusion
was wrong. BOTH `dbgpt-acc-auto` AND `dbgpt-acc-flash-attn` ship.]**

---

## Acceptance Criteria (Whole Feature)

- **AC-1.** Up to **6** staged-recipes PRs are open or merged: one per
  *needed* prerequisite recipe — S2 (`auto-gpt-plugin-template`), S4
  (`lyric-py`), S5/S6/S7 (the 3 lyric workers) — plus one for the
  DB-GPT multi-output recipe (S12). **S1 (`abstract-singleton`) and S3
  (`lyric-task`) need no PR — they already ship on conda-forge.** Each
  PR addresses every bot-lint, conda-smithy-lint, and reviewer comment.
- **AC-2.** All **8** DB-GPT outputs build green on `linux-64`/`osx-64`/`win-64` in
  conda-forge CI. **⚠ ARM installability is NOT verified by the PR:** staged-recipes runs
  no ARM legs (G82), so #33883 going green does NOT prove the noarch outputs SOLVE on
  osx-arm64 + linux-aarch64. `lyric-py` is now live on all 5 subdirs (C1 cleared), but the
  full compiled-transitive-dep set (onnxruntime/chromadb/spacy/tokenizers/pyzmq/cryptography/
  numpy/pandas) × both ARM subdirs × py3.10 was only partially spot-checked — the definitive
  G40 check must run **post-merge on the feedstock**. abstract-singleton + lyric-task already ship.
- **AC-3.** `pip check` passes for every output's test stage and for
  every prerequisite recipe's test stage.
- **AC-4.** A user on a fresh pixi env can install **any** included
  package by name and import its primary module (**on osx-arm64/linux-aarch64 this holds
  only after the C1 `lyric-py` platform-expansion — until then `dbgpt-app` does not install
  there**):
  - `pixi add dbgpt && pixi run python -c "import dbgpt"`
  - …and same for `dbgpt-client`, `dbgpt-ext`, `dbgpt-serve`,
    `dbgpt-acc-auto`, `dbgpt-sandbox`, `dbgpt-app`.
  - Prerequisite recipes installable independently:
    `pixi add lyric-py && pixi run python -c "import lyric"`,
    `pixi add lyric-task lyric-py-worker lyric-js-worker lyric-component-ts-transpiling abstract-singleton auto-gpt-plugin-template`.
- **AC-5.** dbgpt-app's `[code]` extra (defined on dbgpt-core,
  activated by dbgpt-app) works without external pip:
  `pixi add dbgpt-app && pixi run python -c "from dbgpt_app import cli"` succeeds with no `ImportError: lyric_py_worker` (or
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
  only S2 (`auto-gpt-plugin-template`) as a prerequisite PR
  (`abstract-singleton` already ships). Total 2 PRs. Users get
  `dbgpt-app` from conda-forge but without the code-execution sandbox
  feature; documented in PR body and feedstock README.
- **B-full**: Ship all 7 outputs with `dbgpt-app` fully functional —
  the `code` extra is preserved by packaging the lyric-* worker
  stack on conda-forge using the `itkwasm-downsample-wasi` vendor-the-
  blob pattern (~30-line `noarch: python` recipes that pip-install
  upstream PyPI sdists containing pre-built `.wasm`; the WASI runtime
  is supplied by `lyric-py`'s embedded `wasmtime` Rust crate — **not**
  the standalone `wasmtime-py` package). Prerequisite recipes:
  `auto-gpt-plugin-template`, `lyric-py` (cocoindex-class —
  Rust+maturin+protoc; the only non-trivial recipe), and
  `lyric-py-worker`, `lyric-js-worker`,
  `lyric-component-ts-transpiling` (3 itkwasm-pattern noarch recipes).
  `abstract-singleton` and `lyric-task` are **already on conda-forge**
  (no PR). Total **6 PRs** (5 prereq + the DB-GPT multi-output recipe).
  Multi-day, not multi-week. Risk: a conda-forge reviewer rejects the
  vendor-the-blob pattern despite the itkwasm precedent — fallback is
  `B-six-plus-app-patched`.

**Decision: `B-full`** (resolved 2026-05-08).

**Rationale**: The `itkwasm-downsample-wasi` precedent on main
conda-forge collapses the lyric-* worker recipes to ~30 lines each
(noarch python wrapping a vendored upstream sdist). The WASI runtime is
supplied by `lyric-py`'s embedded `wasmtime` Rust crate (built from
source in S4), **not** the standalone `wasmtime-py` package (45.0.0 on
conda-forge). Of the prerequisite recipes only `lyric-py` is
cocoindex-class; the rest are 30–45 min each — and after the 2026-06-17
audit, `abstract-singleton` + `lyric-task` already ship, so the
actionable set is **6 PRs** (5 prereq + the DB-GPT multi-output).
dbgpt-app feature parity (including the code-execution sandbox) is
worth that multi-day effort over shipping a partially-functional
fallback or dropping the package entirely. Risk-mitigated by the S12
fallback (revert to `B-six-plus-app-patched` if any lyric-* worker is
rejected during review).

The B-six and B-six-plus-app-patched options remain documented above
as fallback rationale; they are not active paths for this spec.

The story set, FRs, technical approach, and acceptance criteria have
been updated to cover the prerequisite recipes (see Stories S1–S7; S1
and S3 already ship on conda-forge, leaving 5 to build).

### Q2 (RESOLVED) — Upper-bound caps

**Decision: keep all 5 caps** (resolved 2026-06-17 — the recipe and the
pin-loosening table both reflect this). Conservative default: caps can block some
conda-forge global migrations (notably NumPy 2); revisit per-dep only when upstream
CI proves the newer major, keeping a TODO until then. **Risk to re-verify at S10
(gaps review M3/M4):** confirm `onnxruntime <=1.18.1` and `numpy <2.0.0` still
*solve* against the (unbounded) `chromadb`/`spacy`/`tokenizers` builds on every
target subdir + python — a kept cap that's unsatisfiable is worse than a dropped one.

Five of the loosened pins (`tenacity<=8.3.0`, `fastapi<0.113.0`,
`numpy<2.0.0`, `sqlalchemy<2.0.29`, `onnxruntime<=1.18.1`) carry
upper-bound caps in upstream. Decide per dep whether to keep the cap
(safer, may block conda-forge global migrations — notably the NumPy 2
migration) or drop the cap (riskier, but matches conda-forge's general
"trust semver" stance). Default if unsure: **keep the cap with a
TODO**.

### Q3 (RESOLVED) — `feedstock-name`

Should the conda-forge feedstock be `db-gpt-feedstock` (matches the
upstream repo name and PR title casing) or `dbgpt-feedstock` (matches
the canonical PyPI name and the multi-output package names)? PyPI
metadata canonicalizes to `dbgpt`; the upstream repo name is `DB-GPT`.

**Decision (resolved): `db-gpt-feedstock`** — preserves the upstream repo name,
which is also what most users will search for. The conda packages
themselves are named `dbgpt`, `dbgpt-client`, etc., independent of the
feedstock slug.

---

## Dependencies and Constraints

### External dependencies that must already exist on conda-forge

Verified via `api.anaconda.org` probes; **re-verified 2026-06-17 (all
present)**. `qianfan`, `sentence-transformers`, `sentencepiece`,
`transformers`, and `pillow` were removed — they live in `dbgpt-core`
extras (`proxy_qianfan`, `hf`, `model_vl`) that `dbgpt-app` does not
activate. `httpx[socks]` resolves to **`socksio`** (the spec's
"httpx-socks" was a misnomer; `socksio` is on conda-forge):

`aiofiles`, `aiohttp`, `alembic`, `beautifulsoup4` (for `bs4`),
`cachetools`, `chardet`, `chromadb`, `click`, `cloudpickle`,
`coloredlogs`, `colorama`, `cryptography`, `dashscope`, `docker-py`
(conda name for `docker`), `duckdb`, `duckdb-engine`, `fastapi`,
`gitpython`, `graphviz`, `gtts`, `httpx`, `importlib_resources`,
`jinja2`, `jsonschema`, `markdown`, `mcp`, `msgpack-python` (conda name
for `msgpack`), `numpy`, `olefile`, `onnxruntime`, `openai`, `openpyxl`,
`pandas`, `pdfplumber`, `prettytable`, `psutil`, `pydantic`, `pympler`,
`pymysql`, `pypdf`, `pyparsing`, `python-docx`, `python-jsonpath`,
`python-multipart`, `python-pptx`, `pyzmq`, `rich`, `schedule`,
`seaborn`, `selenium`, `shortuuid`, `snowflake-id`, `socksio` (for
`httpx[socks]`), `spacy`, `sqlalchemy`, `sqlparse`, `tenacity`,
`termcolor`, `tiktoken`, `tokenizers`, `tomli`, `tomlkit`, `typeguard`,
`typing_inspect`, `typing-extensions`, `uvicorn`, `xlrd`.

### External dependencies that are NOT on conda-forge — landed by this spec's prerequisite stories

| PyPI dep                           | Story | Pattern                                 | Effort                   |
| ---------------------------------- | ----- | --------------------------------------- | ------------------------ |
| `abstract-singleton`             | S1    | ✅ already on conda-forge (1.0.1) — no PR | —                      |
| `lyric-task`                     | S3    | ✅ already on conda-forge (0.1.7) — no PR | —                      |
| `auto-gpt-plugin-template`       | S2    | trivial pure-Python noarch              | 20 min                   |
| `lyric-py`                       | S4    | Rust+maturin+protoc, per-platform       | 4–6 h (cocoindex-class) |
| `lyric-py-worker`                | S5    | itkwasm-pattern noarch (vendored .wasm) | 45 min                   |
| `lyric-js-worker`                | S6    | itkwasm-pattern noarch (vendored .wasm) | 30 min                   |
| `lyric-component-ts-transpiling` | S7    | itkwasm-pattern noarch (vendored .wasm) | 30 min                   |

`httpx[socks]` resolves to **`socksio`** (already on conda-forge) — not
a new prerequisite. `qianfan` is **not** needed (`proxy_qianfan` is not
activated by `dbgpt-app`) — dropped from scope. Net: **5** prerequisite
recipes to build (S2, S4, S5, S6, S7).

**No upstreaming of WASI-side toolchain required.** The original
estimate that `B-full` needed `wasi-sdk`, `wasm-tools`,
`componentize-py`, `jco`, and `rust-std-wasm32-wasip1` on conda-forge
was based on assuming we'd source-rebuild the `.wasm` blobs. The
itkwasm-downsample-wasi precedent (see § "WASM toolchain on
conda-forge — current state") demonstrates that conda-forge accepts
vendored `.wasm` from upstream PyPI sdists when:

1. The runtime that executes the WASM is itself built from source on
   conda-forge — for Lyric that runtime is `lyric-py`'s embedded
   `wasmtime` Rust crate (the itkwasm family uses `wasmtime-py`
   instead), **and**
2. Upstream has reproducible WASM build CI (verified for
   `lyric-project/lyric-runtime`).

The Bytecode Alliance toolchain stays out of this spec's scope (NG3).

### Upstream constraints

- DB-GPT v0.8.0 is the chosen baseline. Tag-based source URL. (v0.8.1 shipped
  2026-06-18; this effort deliberately targets v0.8.0 — autotick-bot bumps the
  feedstock post-merge.)
- The repo's root `LICENSE` is MIT (verified). Sub-packages declare
  `license = "MIT"` in their pyproject.toml; no per-package LICENSE
  files (verified).
- The PyPI dist `dbgpt` corresponds to the *source* directory
  `packages/dbgpt-core/`. This naming asymmetry is hard-coded into the
  recipe.
- Lyric prerequisites are versioned at `0.1.7` upstream
  (`lyric-project/lyric-runtime`, MIT; tag scheme is plain `v0.1.7`,
  **not** `pylyric-v0.1.7`). All 5 Python wrappers (`lyric-task`,
  `lyric-py`, `lyric-py-worker`, `lyric-js-worker`,
  `lyric-component-ts-transpiling`) are at the same version
  (`lyric-component-ts-transpiling` has a higher `requires-python`
  floor of `>=3.10`). PyPI `license` metadata is empty for 4 of them;
  `lyric-py` declares `MIT`. **None of the 5 sdists ship a LICENSE
  file** — vendor the MIT text from the GitHub `v0.1.7` tag (CFE gotcha G4) for
  every lyric-* recipe.

### Skill-version constraint

The recipe uses rattler-build v1 features (`pin_subpackage(exact=True)`,
`schema_version: 1`, multi-output without legacy meta.yaml). Requires
`conda-forge-expert` skill v8.x (the v1 multi-output features it relies
on have been available since v6.0.0) and rattler-build ≥ v0.61.0.

---

## Out of Scope (Explicit)

- **OOS-1.** ~~`dbgpt-acc-flash-attn` — CUDA-only, GPU-tier, deferred.~~
  **OVERTURNED 2026-07-01** — see NG1. The `dbgpt-acc-flash-attn` *wrapper* is a
  zero-dep noarch shim and IS shipped (8th output of #33883). The heavy GPU
  `flash-attn` library remains out of scope, but that is a different package.
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

## Suggested BMAD Invocation — ⚠ RETIRED (do NOT run)

> **This effort is DELIVERED EXTERNALLY via #33883 (@pb01ka). There is nothing to
> implement.** Running `bmad-quick-dev` on this spec would re-author and submit a
> competing db-gpt recipe — forbidden by the 2026-07-01 consume-not-submit
> decision (G58). All prerequisite work is done (5 PRs merged); the only remaining
> action is to consume `dbgpt` once #33883 lands. The original invocation + wave
> plan is preserved below strictly as a historical record:

```
# HISTORICAL — DO NOT RUN
run quick-dev — implement the intent in docs/specs/db-gpt-conda-forge.md
#   Wave 1: S1 (abstract-singleton), S3 (lyric-task) — DONE
#   Wave 2: S2 (auto-gpt-plugin-template), S4 (lyric-py) — DONE (merged)
#   Wave 3: S5, S6, S7 (lyric workers) — DONE (merged)
#   Wave 4: S8 → S9, S10, S11 → S12 — S12 RETIRED (delivered via #33883)
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
