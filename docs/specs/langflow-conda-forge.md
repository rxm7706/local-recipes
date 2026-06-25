---
status: ready
implemented_by: bmad-quick-dev
shipped_ref: "langflow-suite all 3 outputs (lfx+langflow-base+langflow) build+test GREEN locally (2026-06-23) via LEAN re-architecture (integrations->run_constraints) + local skew-workaround channel builds; cf-submission blocked on 2 feedstock fixes (langchain-text-splitters stale pin, litellm proxy-extras flatten)"
scope: full-closure   # core hard-dep closure + ALL optional run_constraints integrations (Set C now ALL authored locally) + ALL 3 external cf skews. Nothing deferred except the 3 named caveats (handled per § Caveats: elasticsearch gated on cf PR #122; apify-client attempt-or-drop; ragstack kept local-only).
submission_started: 2026-06-24   # Wave B in progress (as of 2026-06-25): 19 staged-recipes PRs — 4 MERGED→on cf (primp #33836, pybase62 #33838, pymilvus-model #33837, jsonquerylang #33846); 12 OPEN CI-GREEN (langflow-sdk #33856, jigsawstack #33857, ibm-cos-suite #33886 [3-output core+s3transfer+sdk; win_64 cd→pip-install-./subdir fix], smolagents #33887, llm-sandbox #33888, lomond #33889 [win_64 G19 PYTHONUTF8 fix landed], apify-shared #33890, vlmrun-hub #33891, milvus-lite #33892, langchain-milvus #33894, pksuid #33895 [pip_check G26 3-file fix landed], ddgs #33896); 1 OPEN fix-re-running (couchbase #33893 [win_64 OpenSSL FetchContent→conda-openssl fix; linux/osx green]); 1 OPEN CI-RED (opendsstar #33840 [prereqs not on cf]); 1 REJECT→CLOSE (impit #33897 — already on cf as conda-forge/impit-feedstock; osx-arm64+linux-aarch64 platform-expansion prepped locally + linux-aarch64 cross-build verified GREEN). NOTE: a separate standalone ibm-cos-sdk #33885 duplicates suite #33886 → CLOSE one. Wave A skew feedstock PRs still TO FILE; elasticsearch-feedstock #122 still OPEN.
spec_updated: 2026-06-25
---
# Tech Spec: langflow-suite on conda-forge (submission + external-skew remediation)

> **BMAD intake document.** Written for `bmad-quick-dev` / `bmad-dev`. This is the
> **submission** spec for the `langflow-suite` multi-output recipe and its full prerequisite
> closure: clear the external conda-forge version-skews, then submit the closure to
> `conda-forge/staged-recipes` leaves-first. The local authoring is largely done (the closure
> builds GREEN in the local channel); the remaining work is **feedstock pin-convergence +
> staged-recipes submission**.
>
> ### 🔴 SCOPE — FULL CLOSURE (do not narrow)
>
> This effort covers the **entire** langflow-suite closure end-to-end — **nothing is deferred
> or out-of-scope except the 3 explicitly-named caveats below.** "Full closure" means:
> **(1)** the **core hard-dep closure** that makes `langflow-suite` installable (the lfx
> closure, IBM chain, `opendsstar`, `jsonquerylang`, the langflow-family, the 4 `lfx-*`
> feedstocks, …); **(2)** **ALL optional `run_constraints` integrations** — every `langchain-*`
> provider wrapper + SDK leaf (§ Submission set C) — **all now authored + built locally**; their
> recursive sub-closures resolved + submitted leaves-first;
> **(3)** **the external cf skews** — Skew 1 (langchain-text-splitters) **and** Skew 2 (litellm
> proxy-extras flatten) **both gate the CORE suite** via lfx's hard deps; Skew 3 (otel cluster) is
> now **optional-only** (lean → `run_constraints`). All are in scope; 1 + 2 are worked around
> locally already (§ External skews).
>
> **Set C is already authored** (the integrations below are present locally + built) — Wave C is
> "re-verify + submit leaves-first", not "author from scratch". The lean re-architecture (§ Packaging
> shape) makes every Set-C integration a non-blocking `run_constraints` member.
>
> The **only** things NOT submitted are the 3 caveats (§ Submission set → Caveats):
> `ragstack-ai-knowledge-store` (BUSL-1.1, non-OSI → drop), `langchain-elasticsearch`
> (cf `elasticsearch>=8.19` gap → file a feedstock bump or drop), `apify-client`
> (needs `impit` py311+ → build it or drop). **Web-planning runs (Ultraplan) and BMAD must
> plan to the full closure — do not scope down to "core only" or "Wave A only".**
>
> Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/langflow-conda-forge.md
> ```
>
> **Rule 1 (always-on):** every recipe touch here MUST go through the `conda-forge-expert`
> skill (the skill's gotchas/protocols are authoritative on any conflict). **Rule 2:** the
> effort closes out with a CFE-skill retro.
>
> **Supersedes** the earlier "separate-recipes / authoring" model of this file. langflow,
> langflow-base, and lfx are now packaged as **one multi-output recipe** (`recipes/langflow-suite/`),
> built **lean** — integrations are optional `run_constraints`, not forced (see § Packaging shape).
> The lean-architecture + skew-fix work landed in **local-recipes PR #25** (merged to `main`).

---

## Status

| Field | Value |
| ----- | ----- |
| Status | **GREEN locally — all 3 langflow-suite outputs (lfx, langflow-base, langflow) build + test pass** (imports + pip_check, 2026-06-23) against the local channel, via the **LEAN re-architecture** (integrations → `run_constraints`; § Packaging shape) + **local skew-workaround channel builds** of `langchain` 1.2.18 / `litellm` 1.89.3 (base deps; § External skews). `cfe-local-build-status: success`. **conda-forge submission stays `blocked-pending-prerequisites`** on 2 cf feedstock fixes (langchain-text-splitters stale pin; litellm proxy-extras flatten) that gate lfx's hard deps; the local channel works around both. **Wave B submission IN PROGRESS (2026-06-25)** — 19 staged-recipes PRs: **4 MERGED → on conda-forge** (primp [#33836](https://github.com/conda-forge/staged-recipes/pull/33836), pybase62 [#33838](https://github.com/conda-forge/staged-recipes/pull/33838), pymilvus-model [#33837](https://github.com/conda-forge/staged-recipes/pull/33837), jsonquerylang [#33846](https://github.com/conda-forge/staged-recipes/pull/33846)); **12 OPEN CI-GREEN** (langflow-sdk [#33856](https://github.com/conda-forge/staged-recipes/pull/33856), jigsawstack [#33857](https://github.com/conda-forge/staged-recipes/pull/33857), smolagents [#33887](https://github.com/conda-forge/staged-recipes/pull/33887), llm-sandbox [#33888](https://github.com/conda-forge/staged-recipes/pull/33888), apify-shared [#33890](https://github.com/conda-forge/staged-recipes/pull/33890), vlmrun-hub [#33891](https://github.com/conda-forge/staged-recipes/pull/33891), milvus-lite [#33892](https://github.com/conda-forge/staged-recipes/pull/33892), langchain-milvus [#33894](https://github.com/conda-forge/staged-recipes/pull/33894), ddgs [#33896](https://github.com/conda-forge/staged-recipes/pull/33896); lomond [#33889](https://github.com/conda-forge/staged-recipes/pull/33889) win_64 G19 PYTHONUTF8 fix **landed**; pksuid [#33895](https://github.com/conda-forge/staged-recipes/pull/33895) pip_check G26 3-file fix **landed**; ibm-cos-suite [#33886](https://github.com/conda-forge/staged-recipes/pull/33886) 3-output core+s3transfer+sdk, win_64 `cd`→`pip install ./subdir` fix); **1 OPEN fix-re-running** (couchbase [#33893](https://github.com/conda-forge/staged-recipes/pull/33893) win_64 OpenSSL FetchContent→conda-openssl fix; linux/osx green); **1 OPEN CI-RED** (opendsstar [#33840](https://github.com/conda-forge/staged-recipes/pull/33840) pending prereqs on cf); **1 REJECT→CLOSE** (impit [#33897](https://github.com/conda-forge/staged-recipes/pull/33897) already on cf — osx-arm64+linux-aarch64 platform-expansion prepped locally, linux-aarch64 cross-build verified GREEN). A separate standalone ibm-cos-sdk [#33885](https://github.com/conda-forge/staged-recipes/pull/33885) **duplicates** suite #33886 → CLOSE one. The 2 durable skew feedstock PRs (langchain / litellm) remain **TO FILE**. |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (tech-spec only) |
| Upstream | `langflow-ai/langflow` v1.10.0 (MIT). Monorepo split into `lfx` (executor core, `src/lfx`), `langflow-base` (`src/backend/base`, ships the `langflow` import), `langflow` (umbrella, `.`), and the `lfx-*` extension plugins. |
| Recipe | `recipes/langflow-suite/recipe.yaml` — multi-output (`recipe:` + `outputs: [lfx, langflow-base, langflow]`). Source = GitHub monorepo tag archive (a PyPI wheel can't be used: outputs build `src/lfx`, `src/backend/base`, and `.`). sha256(`v1.10.0`) = `45a317111a5d7cbc2709e683a72a80779801a658f61e506b612978588788ab71`. |
| Target | `conda-forge/staged-recipes` → the langflow closure (most `noarch: python`; `primp` compiled Rust, `couchbase` compiled C++). |
| Real `python_min` | **3.11** — NOT the upstream-aspirational 3.10. `jsonquerylang` (a hard dep) imports `typing.NotRequired` (PEP 655, py3.11+) unconditionally (**G41**). |
| Lifetime | Long-running — feedstocks become autotick-maintained after the first PR lands. |

---

## Packaging shape & key decisions

- **Multi-output suite.** `recipes/langflow-suite/` produces `lfx` → `langflow-base` → `langflow`
  from one source. python_min 3.11; source = GitHub tag archive; `build.number: 0`. Each output
  carries its own `tests:` (per-output is required for multi-output — conda-smithy rejects a
  top-level `tests:`).
- **The 4 `lfx-*` extension plugins are SEPARATE feedstocks** (`lfx-arxiv`, `lfx-docling`,
  `lfx-duckduckgo`, `lfx-ibm`). The `langflow` umbrella **hard-deps** all four
  (upstream `langflow` `[project.dependencies]` = `langflow-base[complete]` + the 4 `lfx-*`).
- **LEAN base + umbrella (rxm7706 directive, 2026-06-23) — integrations are NOT forced.**
  Upstream `langflow-base` bundles ~90 integration extras and `langflow-base[complete]` pulls
  **all** of them (= `langflow[full]`); no one needs every integration. So the recipe ships a
  **lean** langflow-base + langflow: hard `run` = the **framework core only**; ALL integrations
  (langchain providers, vector/analytics DB clients, external SDKs, the 4 `lfx-*` component
  packs) are **`run_constraints`** (version-pinned, optional — constrained only if a user adds
  them). To keep `pip_check: true` green, each output's build **`sed`-strips the integration
  deps from the wheel METADATA** (range-restricted to `[project.dependencies]`), and the umbrella
  rewrites `langflow-base[complete]`→`langflow-base` + drops the 4 `lfx-*`. The lean core was
  validated empirically (`import langflow`/pip_check); `jq` + `onnxruntime` were also demoted
  once the build proved they're component-level, not load-time core.
- **This dissolves the langflow→lfx-*→lfx bootstrap cycle** (the umbrella no longer hard-deps
  `lfx-*`), so the earlier Q1 split-vs-keep question is moot — the single 3-output recipe stands
  and submits cleanly, versions locked in lockstep.
- **`lfx` keeps its upstream hard deps** (it IS the executor core): `langchain` +
  `langchain-classic` + `opendsstar` (→ `litellm`), etc. This is **why the two external cf skews
  still gate `lfx` on conda-forge** even though langflow-base/langflow are now lean
  (§ External skews) — the local channel works around them with rebuilt `langchain`/`litellm`.

---

## Submission set

Three buckets. (cfe-status from the live recipe scan, 2026-06-23.)

### A. Already on conda-forge → CONSUME, do not submit

`markitdown`, `langfuse-python` (NOT `langfuse` — G10 rename), `litellm`, `openai`,
`traceloop-sdk`, `openinference-instrumentation-langchain`, `composio`, `docling-core`,
`docling-slim`, `chromadb`, `qdrant-client`, `weaviate-client`, `opensearch-py`, `elasticsearch`,
`clickhouse-connect`, `pymongo`, `aiosqlite`, `pgvector`, `duckdb`, `fastavro`, `fastparquet`,
and the on-cf `langchain-*`: `langchain`, `-core`, `-classic`, `-community`, `-text-splitters`,
`-anthropic`, `-aws`, `-chroma`, `-experimental`, `-google-genai`, `-groq`, `-huggingface`,
`-mcp-adapters`, `-mistralai`, `-mongodb`, `-ollama`, `-openai`, `-perplexity`, `-qdrant`,
`langchainhub`, `langgraph-checkpoint`, `langsmith`. Plus all on-cf leaf deps of `lfx`/`langflow-base`
(pandas, pydantic, fastapi, uvicorn, rich, httpx, pypdf, json-repair, emoji, uncurl, nanoid,
grandalf, mcp, cryptography, …).

### B. Net-new — to build + submit (all built GREEN locally)

| Recipe | cfe-status | shape | license | depends on (net-new) |
|---|---|---|---|---|
| primp | on-conda-forge | compiled Rust | MIT | — (leaf) |
| jsonquerylang | on-conda-forge | noarch | ISC | — (forces py3.11, G41) |
| langflow-sdk | pending-approval (#33856) | noarch | MIT | — |
| jigsawstack | pending-approval (#33857) | noarch | MIT | — |
| smolagents | pending-approval (#33887) | noarch | Apache-2.0 | — |
| llm-sandbox | pending-approval (#33888) | noarch | MIT | — |
| pybase62 | on-conda-forge | noarch | BSD-2 | — |
| lomond | pending-approval (#33889, CI-green) | noarch | BSD-3 | — (win_64 G19 fix landed) |
| pksuid | pending-approval (#33895, CI-green) | noarch | MIT | pybase62 (on cf) |
| apify-shared | pending-approval (#33890) | noarch | Apache-2.0 | — |
| vlmrun-hub | pending-approval (#33891) | noarch | Apache-2.0 | — |
| vlmrun | blocked-pending-prereq | noarch | Apache-2.0 | vlmrun-hub |
| couchbase | pending-approval (#33893, win fix re-running) | compiled C++ | multi (Apache/MIT/BSD/CC0) | — (win_64 OpenSSL FetchContent fix) |
| pymilvus-model | on-conda-forge | noarch | Apache-2.0 | — |
| milvus-lite | pending-approval (#33892) | noarch | Apache-2.0 | — (3.0 pure-Python, G42; G28 faiss-cpu→faiss source-patch, pip_check re-enabled) |
| ibm-cos-sdk-core | pending-approval (suite #33886) | noarch | Apache-2.0 | — (now a `ibm-cos-suite` output) |
| ibm-cos-sdk-s3transfer | pending-approval (suite #33886) | noarch | Apache-2.0 | ibm-cos-sdk-core (==) (suite output) |
| ibm-cos-sdk | pending-approval (suite #33886) | noarch | Apache-2.0 | core + s3transfer (suite output) |
| ibm-watsonx-ai | blocked-pending-prereq | noarch | BSD-3 | ibm-cos-sdk (also build 1.3.37 for py3.10, G40) |
| langchain-milvus | pending-approval (#33894) | noarch | MIT | pymilvus-model (on cf) |
| ddgs | pending-approval (#33896) | noarch | MIT | primp (on cf) |
| trustcall | blocked-pending-prereq | noarch | MIT | — |
| qianfan | blocked-pending-prereq | noarch | Apache-2.0 | — |
| ragworkbench | blocked-pending-prereq | noarch | Apache-2.0 | — |
| toolguard | blocked-pending-prereq | noarch | Apache-2.0 | — (fastmcp>=2.14 floor, G36) |
| langwatch | blocked-pending-prereq | noarch | MIT | pksuid (pybase62 on cf) |
| langchain-ibm | blocked-pending-prereq | noarch | MIT | ibm-watsonx-ai |
| agent-lifecycle-toolkit | blocked-pending-prereq | noarch | Apache-2.0 | ibm-watsonx-ai, smolagents, llm-sandbox (import `altk`, G7) |
| opendsstar | pending-approval (#33840, CI-red) | noarch | Apache-2.0 | milvus-lite, langchain-milvus, smolagents, ragworkbench (pymilvus-model on cf; import `OpenDsStar`, G7) |
| firecrawl-py | pending-submission | noarch | MIT | — (built; post-lean a langflow-base `run_constraints` integration, NOT a hard dep) |
| spider-client | pending-submission | noarch | MIT | — (leaf; post-lean langflow-base `run_constraints`, not a hard dep) |
| assemblyai | pending-submission | noarch | MIT | — (leaf; post-lean langflow-base `run_constraints`, not a hard dep) |
| **lfx** *(suite output — Q1: NOT split)* | blocked-pending-prereq | noarch | MIT | langflow-sdk, opendsstar (→litellm), jsonquerylang, markitdown(cf), langchain+langchain-classic(cf) |
| lfx-arxiv | blocked-pending-prereq | noarch | MIT | lfx |
| lfx-docling | blocked-pending-prereq | noarch | MIT | lfx, docling-core(cf) |
| lfx-duckduckgo | blocked-pending-prereq | noarch | MIT | lfx, ddgs |
| lfx-ibm | blocked-pending-prereq | noarch | MIT | lfx, langchain-ibm, ibm-watsonx-ai (import `ibm_db`, G10) |
| langchain-astradb | blocked-pending-prereq | noarch | MIT | (astrapy, cassio — see C) |
| langchain-graph-retriever | blocked-pending-prereq | noarch | Apache-2.0 | — |
| langchain-google-vertexai | blocked-pending-prereq | noarch | MIT | — |
| langchain-sambanova | blocked-pending-prereq | noarch | MIT | — |
| langchain-google-community | blocked-pending-prereq | noarch | MIT | — (G12 numpy-selector, G35) |
| **langflow-base** *(suite; LEAN)* | blocked-pending-prereq | noarch | MIT | lfx + framework core ONLY (all integrations incl. spider-client/assemblyai/firecrawl-py → `run_constraints`; METADATA source-stripped) |
| **langflow** *(suite; LEAN umbrella)* | blocked-pending-prereq | noarch | MIT | langflow-base ONLY (lfx-* + integrations → `run_constraints`; `[complete]`→`langflow-base` source-rewrite; cycle dissolved) |

> **Re-verify before each wave:** the langflow-suite outputs are **LEAN** — `spider-client`,
> `assemblyai`, `firecrawl-py` and the whole integration set are `run_constraints` (NOT hard deps),
> and are `sed`-stripped from the wheel METADATA at build. All are authored + built; `firecrawl-py`
> + `mem0ai` build records were added in PR #24. When adding a NEW hard dep to a lean output, run
> `check_dependencies` on a flattened single-output recipe (G29) and decide core-vs-integration per
> § Packaging shape before placing it in `run` vs `run_constraints`.

### C. Optional integrations (`run_constraints`) — full-closure scope

Soft constraints; they do not block langflow-suite install, but the full suite experience wants
them on cf. **CORRECTION (ultraplan scan 2026-06-23): the entire Set-C list below is now AUTHORED
+ present locally** — the spec's earlier "not yet authored" claim is stale. Authoring is
effectively complete; Wave C is now **re-verify each leaf → submit leaves-first**, not "author +
submit". Set C (all present): `ag2`, `astrapy`, `cassio`, `cleanlab-tlm`, `composio-langchain`,
`langchain-cohere`, `langchain-google-calendar-tools`, `langchain-nvidia-ai-endpoints`,
`langchain-pinecone`, `langchain-unstructured`, `langchain-weaviate`, `mem0ai`, `metal-sdk`,
`needle-python`, `openlayer`, `opik`, `scrapegraph-py`, `upstash-vector` — plus the 5 already-built
`langchain-*` in table B, and `spider-client` + `assemblyai` (once thought langflow-base hard deps,
but **post-lean they are `run_constraints` integrations** — submit them here in Wave C). Submit each
leaf (SDK) before its `langchain-*` wrapper; re-run
`check_dependencies` per leaf since each carries its own recursive sub-closure. Skews 2 + 3 gate
this wave (not the core suite).

### Caveats (special handling — do NOT submit naively) — RESOLVED 2026-06-23

- **`ragstack-ai-knowledge-store` — BUSL-1.1, NOT conda-forge-eligible** (non-OSI). **Q2 RESOLVED:**
  **keep the recipe locally** (it's present) **but commented-out / clearly marked
  `BUSL-1.1 / non-OSI — out of scope for conda-forge`; NEVER submit.** Confirm `opendsstar`
  resolves without it (is it a hard or optional opendsstar dep? — verify in Wave A).
- **`langchain-elasticsearch` — blocked on a cf gap:** requires `elasticsearch >=8.19,<9` which
  did not exist on conda-forge (feedstock jumps 8.18.0 → 9.0.0). **Q5 RESOLVED: INCLUDE, gated on
  the live `elasticsearch-feedstock` bump — `conda-forge/elasticsearch-feedstock` PR #122
  (https://github.com/conda-forge/elasticsearch-feedstock/pull/122) is UP.** Submit
  `langchain-elasticsearch` once #122 merges and `elasticsearch >=8.19` is on cf.
- **`apify-client` — was blocked on `impit` py311+** (G38). **RESOLVED 2026-06-25: `impit` is ALREADY
  ON CONDA-FORGE** (`conda-forge/impit-feedstock` v0.13.0, maint. Pijukatel) — no submission needed
  (the local `recipes/impit/` net-new attempt was redundant; PR #33897 closed as "feedstock exists").
  impit ships py3.10–3.14 across linux-64/osx-64/win-64 (0.9.3 covers py3.11; 0.13.0 is py3.13+), so
  the consumer's py3.11 matrix is covered. **`apify-client` is unblocked → include** (re-verify its
  own sub-closure with `check_dependencies` before submit). Platform gap: impit lacks osx-arm64 +
  linux-aarch64 — expansion prepped locally (`recipes/impit/conda-forge.yml`, linux-aarch64
  cross-build verified GREEN); a feedstock PR would widen the closure's ARM coverage.

---

## External conda-forge skews (Wave A — the gate to GREEN)

These are conda-forge **feedstock pin-convergence** problems: each conflicting sub-cluster solves
*in isolation* on cf, but the full langflow graph does not. Per the CFE Build-Failure-Protocol
"external cf ecosystem version-skew" case — fix upstream, do not churn the consumer recipe.

> **STATUS 2026-06-23:** both **core-gating** skews (1 + 2) are **worked around locally** —
> rebuilt `langchain` 1.2.18 / `litellm` 1.89.3 (base deps) into the channel → langflow-suite is
> GREEN. Each still needs its **durable cf feedstock PR** (below) before cf submission can succeed.
> Skew 3 (otel cluster) is now **optional-only** — the lean re-architecture moved it to
> `run_constraints`, so it no longer gates the core.
>
> **RE-VERIFIED 2026-06-24:** neither durable feedstock PR has been filed yet — `conda-forge/langchain-feedstock`
> (Skew 1) and `conda-forge/litellm-feedstock` (Skew 2) carry **no rxm7706 PR**; both remain **TO FILE**
> and still gate cf submission of the `langflow-suite` outputs (lfx/langflow-base/langflow). Wave B
> leaves that don't transit lfx (primp, pybase62, pymilvus-model, jsonquerylang) were submitted +
> merged regardless — they don't depend on the skewed packages.

### Skew 1 — langchain-text-splitters (core-gating via lfx; one of TWO core skews — see Skew 2)

- **Symptom:** `lfx` test-env solve fails. `lfx` pins **both** `langchain~=1.2.0` and
  `langchain-classic~=1.0.7`. On cf, **every `langchain 1.2.x` build (all 37) pins
  `langchain-text-splitters <1.0.0,>=0.3.9`**, while `langchain-classic ~=1.0.7` and local
  `opendsstar 1.0.26` require `langchain-text-splitters >=1.1.0` → unsatisfiable.
- **Root cause (verified 2026-06-23):** the cf `langchain` feedstock carries a **stale**
  `langchain-text-splitters <1.0.0` run-dep that **upstream langchain 1.2.0 no longer declares**
  (its metadata lists only `langchain-core`; `requires_python = <4.0.0,>=3.10.0`). The pin is a
  carry-over from the langchain 0.3.x era.
- **Fix (concrete, ~one line):** PR `conda-forge/langchain-feedstock` to **drop or loosen** the
  `langchain-text-splitters` run-dep so it admits `>=1.1.0` (match upstream + `langchain-classic`),
  rerender, merge. **Verify first** against the exact cf-pinned 1.2.x upstream metadata
  (`pypi.org/pypi/langchain/<ver>/json`).
- **Approach DONE (rxm7706, 2026-06-23): local rebuild first, then the upstream PR.** Rebuilt
  `langchain` 1.2.18 locally **from its real upstream base deps** (grayskull) — which declare only
  `langchain-core`/`langgraph`/`pydantic` and **NO `langchain-text-splitters` at all** (so the cf
  feedstock's `<1.0.0` pin simply *vanishes*, not "loosened"). `lfx` + the 3-output `langflow-suite`
  then go **test-GREEN** (py3.11). The build is in the channel as `recipes/langchain/` (LOCAL-ONLY,
  do-not-submit). **Still TO FILE:** the ~1-line `conda-forge/langchain-feedstock` PR dropping the
  stale pin — the durable unblock for cf submission.
- **Note:** `langchain 1.2.x` is NOT py3.13-only — it has `pymin310` builds (`python >=3.10,<3.13`)
  covering py3.11; Python is not the blocker, the text-splitters pin is.
- **Diagnosis test:** solve `langchain` + `langchain-classic` + `langchain-text-splitters` in
  isolation on cf — confirms the conflict is feedstock-internal, not a consumer defect.

### Skew 2 — litellm proxy-extras flattened as hard deps (gates the CORE suite via lfx)

- **Root cause (verified 2026-06-23):** upstream `litellm` lists `fastapi`, `cryptography`, and
  `opentelemetry-api==1.28.0` ONLY under its `proxy` / `proxy-runtime` **extras** — the core SDK
  needs none of them. The cf `litellm` feedstock **flattens those extras into HARD deps**. `lfx`
  hard-pulls `litellm` (via `opendsstar`), so the baked `opentelemetry-api==1.28.0` collides with
  langflow-base's `opentelemetry-api>=1.30`, and the proxy `fastapi` pin with lfx's
  `fastapi>=0.135`. This gates the **core** suite (lfx is a hard dep), not just optional integrations.
- **Done locally:** rebuilt `litellm` 1.89.3 with **base deps only** (no proxy extras) into the
  local channel → langflow-base + langflow go GREEN. **Durable fix:** PR `conda-forge/litellm-feedstock`
  to stop flattening the `proxy` / `proxy-runtime` extras into hard run deps (keep them optional).
- This also **subsumes the old "otel/observability skew" for the core**: with base-only litellm
  there is no `otel-api==1.28.0`, and lean langflow-base keeps `otel-api>=1.30`.

### Skew 3 — otel observability cluster (OPTIONAL integrations only — no longer gates the core)

- `traceloop-sdk` / `arize-phoenix-otel` / `opik` / `openinference-*` carry mutually-incompatible
  otel-semantic-conventions / `langchain<0.4` pins. With the **lean** re-architecture these are all
  `run_constraints` (never force-installed), so this **no longer blocks** langflow-suite — it only
  matters for a user who opts into that observability cluster.
- **Fix (deferred, optional):** widen the otel / `traceloop-sdk` / `openinference-*` feedstock pins
  if/when the cluster is made co-installable. Not a submission gate.

---

## Waved submission plan

> Strip every `extra.cfe-*` key + the `# CFE …` comment blocks before any push. Build + test each
> recipe locally (against the merged local channel) before pushing. After each feedstock push,
> request rerender.

### Wave A — clear the external skews (gate to langflow-suite test-GREEN) — DONE LOCALLY 2026-06-23

All 3 langflow-suite outputs now build + test GREEN locally (imports + pip_check). What remains in
Wave A is the **two durable conda-forge feedstock PRs** — the local channel rebuilds are the
iteration loop; the PRs are what actually unblock cf submission:

- **A1 — langchain-text-splitters (Skew 1). Local rebuild DONE** (`langchain` 1.2.18, base deps,
  in channel). **Durable fix to file:** ~1-line `conda-forge/langchain-feedstock` PR dropping the
  stale `langchain-text-splitters <1.0.0` pin (verify vs the exact cf-pinned 1.2.x upstream metadata).
- **A2 — litellm proxy-extras flatten (Skew 2). Local rebuild DONE** (`litellm` 1.89.3, base deps,
  in channel). **Durable fix to file:** `conda-forge/litellm-feedstock` PR to stop flattening the
  `proxy` / `proxy-runtime` extras into hard run deps.
- **A3 — otel cluster (Skew 3):** no longer a Wave-A gate (lean → `run_constraints`); deferred/optional.
- Carryover checks: confirm `opendsstar` resolves without `ragstack-ai-knowledge-store` (BUSL-1.1,
  out of scope). `firecrawl-py` build record now recorded (it's a `run_constraints` integration).

### Wave B — submit the core hard-dep closure (leaves → roots) — IN PROGRESS (started 2026-06-24)

> **Progress 2026-06-24:** 7 PRs filed. **B1 leaves MERGED → on cf:** primp [#33836](https://github.com/conda-forge/staged-recipes/pull/33836),
> pybase62 [#33838](https://github.com/conda-forge/staged-recipes/pull/33838), pymilvus-model
> [#33837](https://github.com/conda-forge/staged-recipes/pull/33837), jsonquerylang
> [#33846](https://github.com/conda-forge/staged-recipes/pull/33846). **B1 leaves OPEN (CI-green, in review):**
> langflow-sdk [#33856](https://github.com/conda-forge/staged-recipes/pull/33856), jigsawstack
> [#33857](https://github.com/conda-forge/staged-recipes/pull/33857). **B5 opendsstar OPEN but CI-red**
> ([#33840](https://github.com/conda-forge/staged-recipes/pull/33840)) — submitted ahead of its prereqs
> (milvus-lite/langchain-milvus/smolagents/ragworkbench not yet on cf); leave open until they land or
> close + resubmit in dependency order. Remaining B1 leaves (smolagents, llm-sandbox, lomond,
> apify-shared, vlmrun-hub, ibm-cos-sdk-core, milvus-lite, couchbase, firecrawl-py, trustcall, qianfan,
> ragworkbench, toolguard) not yet submitted.

1. **B1 (leaves):** primp, jsonquerylang, langflow-sdk, jigsawstack, smolagents, llm-sandbox,
   pybase62, lomond, apify-shared, vlmrun-hub, ibm-cos-sdk-core, pymilvus-model, milvus-lite,
   couchbase, firecrawl-py, trustcall, qianfan, ragworkbench, toolguard.
2. **B2:** pksuid (→pybase62), vlmrun (→vlmrun-hub), ddgs (→primp), langchain-milvus (→pymilvus-model),
   ibm-cos-sdk-s3transfer (→core), langwatch (→pksuid, pybase62). (`spider-client` + `assemblyai` are
   now `run_constraints` integrations post-lean, NOT hard deps — submit in Wave C with the rest.)
3. **B3:** ibm-cos-sdk (→core + s3transfer).
4. **B4:** ibm-watsonx-ai (→ibm-cos-sdk); also build 1.3.37 for the py3.10 leg (G40).
5. **B5:** langchain-ibm (→ibm-watsonx-ai), agent-lifecycle-toolkit (→ibm-watsonx-ai, smolagents,
   llm-sandbox), opendsstar (→pymilvus-model, milvus-lite, langchain-milvus, smolagents, ragworkbench).
6. **B6 (single 3-output suite — Q1 RESOLVED, NOT split):** submit `recipes/langflow-suite/`
   producing **lfx + langflow-base + langflow** in one PR. Lean hard deps only (→ langflow-sdk,
   opendsstar, jsonquerylang + the cf langchain/framework stack); spider-client/assemblyai/
   firecrawl-py and the 4 `lfx-*` are `run_constraints`, NOT submission prerequisites. **No test
   relaxation needed** — the lean umbrella never hard-deps the lfx-*, so the bootstrap cycle is
   already dissolved (§ Packaging shape); each output's `import lfx`/`import langflow` test passes
   against the cf framework stack alone. Publishes lfx + langflow-base + langflow together.
7. **B7:** submit the 4 `lfx-*` feedstocks (depend on `lfx`, now on cf): lfx-arxiv, lfx-docling,
   lfx-duckduckgo (→ddgs), lfx-ibm (→langchain-ibm, ibm-watsonx-ai). Once on cf they satisfy the
   umbrella's `run_constraints`.
8. **B8 (optional follow-up):** nothing to "re-enable" (the lean umbrella never hard-required the
   lfx-* test). Optionally tighten the `langflow` `run_constraints` lower bounds on the published
   lfx-*. Suite versions stay locked together (autotick maintains lfx/langflow-base/langflow in lockstep).

### Wave C — submit optional integrations (full-closure scope)

- Submit the already-built `langchain-*` (astradb, graph-retriever, google-vertexai, sambanova,
  google-community) once their SDK leaves are on cf.
- **Re-verify + submit** the rest of Set C (§ Submission set C) — **all now authored** — leaves-first
  (SDK leaf before its `langchain-*` wrapper); re-run `check_dependencies` per leaf.
- Caveats (resolved): **ragstack** kept local-only, commented-out (BUSL-1.1/non-OSI — never submit);
  **langchain-elasticsearch** submitted once `elasticsearch-feedstock` PR #122 merges
  (elasticsearch >=8.19 on cf); **apify-client** attempted (impit built — G38 py311 verify), dropped
  if it can't be unblocked.

### Wave D — closeout

- CFE-skill retro (Rule 2) folding in whatever the feedstock-convergence + submission work
  surfaces. The authoring wave shipped CFE v8.35.0 (G39–G43 + external-skew protocol); the closure
  has since driven the skill to **v8.42.x** (through G55 — notably G54/G55, the wheel→GitHub-source
  switch this closure produced for `langflow-sdk` + the 4 `lfx-*`).

---

## Reproducing the local channel

```bash
# merged-CBC channel at build_artifacts/linux64/ (gitignored; rebuild from recipes/).
# build one recipe into it (--test skip for fast channel population; the suite itself tests GREEN):
pixi run -e local-recipes rattler-build build \
  --recipe recipes/<name>/recipe.yaml \
  --variant-config .pixi/envs/local-recipes/conda_build_config.yaml \
  --output-dir build_artifacts/linux64 --test skip
pixi run -e local-recipes python -m conda_index build_artifacts/linux64
```

**Local skew-workaround rebuilds FIRST** (they shadow cf's stale-pinned builds; LOCAL-ONLY,
do-not-submit — `recipes/langchain/`, `recipes/litellm/`): `langchain` 1.2.18 + `litellm` 1.89.3
(base deps). **Without these the suite test-env solve fails on Skews 1 + 2.**

Channel build order (leaves → roots): primp → ddgs; pybase62 → pksuid; vlmrun-hub → vlmrun;
ibm-cos-sdk-{core,s3transfer} → ibm-cos-sdk → ibm-watsonx-ai{1.3.37,1.5.13} →
langchain-ibm / agent-lifecycle-toolkit; pymilvus-model + milvus-lite + langchain-milvus +
smolagents + ragworkbench → opendsstar; jsonquerylang; langflow-sdk → lfx → lfx-* ;
langflow-base → langflow.

---

## Open Questions — Q1–Q5 RESOLVED; Q6 is NEW + OPEN (2026-06-23)

- **Q1 — suite shape. RESOLVED: KEEP the single 3-output recipe (do NOT split lfx).** lfx +
  langflow-base + langflow ship from one `langflow-suite` feedstock so the three versions stay
  locked together (better long-term; autotick bumps them in lockstep). The `langflow → lfx-* → lfx`
  bootstrap cycle is handled at the *initial* staged-recipes gate by **sequencing + a temporary
  relaxation of the `langflow` output's lfx-* test** (Wave B6 → B7 → B8 follow-up), not by splitting.
- **Q2 — ragstack-ai-knowledge-store BUSL-1.1. RESOLVED: keep the recipe LOCAL-ONLY, commented-out,
  marked non-OSI/out-of-scope; NEVER submit.** Confirm `opendsstar` resolves without it (Wave A).
- **Q3 — python_min 3.11. RESOLVED: declare `python_min 3.11` across the suite** (honest floor per
  G41 — jsonquerylang hard-imports `typing.NotRequired`/PEP 655; upstream `requires-python>=3.10` is
  broken). Reviewer pushback is answerable.
- **Q4 — apify-client / impit. RESOLVED: ATTEMPT** (impit now present + `build=success`; verify py3.11
  matrix per G38), **flag at-risk; DROP if it can't be unblocked cleanly.**
- **Q5 — langchain-elasticsearch / elasticsearch ≥8.19. RESOLVED: INCLUDE, gated on
  `conda-forge/elasticsearch-feedstock` PR #122**
  (https://github.com/conda-forge/elasticsearch-feedstock/pull/122 — **re-verify it's still open/merged
  before relying on it**). Submit once #122 merges.
- **Q6 — lean `lfx` too? (NEW, OPEN.)** The lean cut applied to langflow-base + langflow, but `lfx`
  keeps its upstream hard dep on `opendsstar`, which pulls `litellm` + a heavy closure (docling,
  milvus-lite, sentence-transformers, datasets, …). So `conda install langflow` still drags that in
  via lfx even though the umbrella is lean. The "no one needs all integrations" rationale arguably
  applies to `lfx → opendsstar` as well — **should `opendsstar` (and its heavy closure) be demoted
  to an lfx `run_constraints` integration?** Note upstream lfx hard-deps `OpenDsStar` under a marker,
  so this is a deliberate-deviation decision, not free. Affects how heavy the minimal install is
  **and** whether Skews 1/2 still gate the core (opendsstar is the path that pulls litellm). Unresolved.

---

## Worked Example: the 2026-06-19 → 2026-06-23 sessions

The 2026-06-19 session authored the full transitive closure (4 recursion layers; each layer's
`check_dependencies` drove the next), surfacing CFE gotchas **G35, G39–G43** + the external-skew
Build-Failure-Protocol note (shipped CFE v8.35.0; the closure later drove **G54+G55 / v8.42.0** —
the wheel→GitHub-monorepo source switch for `langflow-sdk` + the 4 `lfx-*`). The 2026-06-23 session fixed the
`langflow-suite` recipe (schema/lint repair; corrected the `lfx` output's truncated run list to
upstream's ~43 deps with G24 caps + G25 `httpx[http2]` flatten), confirmed **all 3 outputs build
GREEN** (`--test skip`), and pinned the residual blocker to **Skew 1 (langchain-text-splitters)** —
a stale `langchain-feedstock` pin, the precise fix for which is Wave A1.

The **2026-06-23 ultraplan re-grounding** session (this update) read the spec in full under the
`conda-forge-expert` skill, **re-scanned `recipes/` against the closure**, and found the repo
materially ahead of the spec's prose: **all ~46 core recipes AND all ~18 Set-C optional
integrations are now authored + built** (Set C is no longer "to author"); `spider-client`,
`assemblyai`, and `impit` are all present + `build=success`; **all closure recipes — incl.
`firecrawl-py` + `mem0ai` — now carry a local build record** (the last two added via merged PR #24).
The residual work is therefore **skew-fix → re-verify GREEN → leaves-first submission**,
not authoring. It also **resolved all five open questions** (Q1 single 3-output recipe / no split;
Q2 ragstack local-only commented-out; Q3 python_min 3.11; Q4 apify-client attempt-or-drop; Q5
langchain-elasticsearch gated on cf `elasticsearch-feedstock` PR #122) and recorded the **Skew 1
approach** (local langchain rebuild first to verify GREEN, then the upstream feedstock PR).

The **2026-06-23 GREEN session (PR #25, now merged to `main`)** executed the fix end-to-end and is
the current state of record. It: rebuilt `langchain` 1.2.18 + `litellm` 1.89.3 locally (Skews 1 + 2 — the latter newly
traced to the cf litellm feedstock flattening the `proxy`/`proxy-runtime` **extras** into hard deps,
which gates the **core** via `lfx`); source-patched the two G28 dist-name false positives
(`milvus-lite` `faiss-cpu`→`faiss`, `opendsstar` `docling`→`docling-slim`) and re-enabled their
pip_check; and applied the **LEAN re-architecture** — langflow-base + langflow hard-`run` = framework
core only, ALL integrations + the 4 lfx-* demoted to `run_constraints`, with the integration deps
`sed`-stripped from the wheel METADATA (empirically validated; `jq` + `onnxruntime` also demoted).
**Result: all 3 langflow-suite outputs build + test GREEN locally.** A Gemini review round on PR #25
was addressed (jq/onnxruntime run-vs-run_constraints dedup; portable `sed -i.bak`; dropped the
litellm proxy-CLI test). **Still outstanding for cf submission:** the 2 durable feedstock PRs
(langchain stale pin; litellm proxy-extras flatten) — TO FILE — and Waves B–D (staged-recipes
submissions), unstarted.

The **2026-06-24 submission wave (Wave B start)** opened the first staged-recipes PRs for the closure,
leaves-first. **4 merged → on conda-forge:** primp [#33836](https://github.com/conda-forge/staged-recipes/pull/33836),
pybase62 [#33838](https://github.com/conda-forge/staged-recipes/pull/33838), pymilvus-model
[#33837](https://github.com/conda-forge/staged-recipes/pull/33837), jsonquerylang
[#33846](https://github.com/conda-forge/staged-recipes/pull/33846) (none transit the skewed `lfx`
path, so they merged cleanly). **2 open + CI-green in review:** langflow-sdk
[#33856](https://github.com/conda-forge/staged-recipes/pull/33856), jigsawstack
[#33857](https://github.com/conda-forge/staged-recipes/pull/33857). **1 open but CI-red:** opendsstar
[#33840](https://github.com/conda-forge/staged-recipes/pull/33840) (a Wave-B5 root submitted ahead of
its prereqs; 5 build legs red until milvus-lite/langchain-milvus/smolagents/ragworkbench reach cf).
The local-recipes side reached its current state via merged PRs **#21–#28** (the wheel→source G54
sweep + v8.42.2 retro landed in #27/#28). **Unchanged blockers:** the 2 skew feedstock PRs remain TO
FILE (re-verified 2026-06-24), and `elasticsearch-feedstock` [#122](https://github.com/conda-forge/elasticsearch-feedstock/pull/122)
(Q5 gate for `langchain-elasticsearch`) is still OPEN.

---

## Appendix: Recipe Registry & Submission Tracker

Every local recipe in the langflow-suite closure, with its wave, current status, and submission PR.
Recipe links point at `main`. **Wave B submission STARTED 2026-06-24** — 7 staged-recipes PRs up:
**4 MERGED → on conda-forge** (primp #33836, pybase62 #33838, pymilvus-model #33837, jsonquerylang
#33846), **2 OPEN + CI-green** (langflow-sdk #33856, jigsawstack #33857), **1 OPEN + CI-red**
(opendsstar #33840, submitted ahead of its prereqs). Every other cell is `—` (authored + built
locally, not yet submitted). The local recipe state — incl. the lean re-architecture + skew
workarounds — lives on `main` (landed via merged local-recipes PRs #21–#28). Fill each PR cell as a
recipe is submitted. Keep this table the single source of truth for "where is each recipe in the pipeline".

Status legend (mirrors the recipe's `cfe-on-conda-forge-status`):
**on conda-forge** = staged-recipes PR merged (feedstock being created) ·
**submitted** = staged-recipes PR open (in review / CI) ·
**ready** = `pending-submission-to-conda-forge` (built GREEN, no blockers) ·
**blocked** = `blocked-pending-prerequisites` (built clean locally; gated on a prereq/skew) ·
**not-built** = authored, no local build record yet ·
**local-only** = never submit (license/eligibility).

### Wave B — core hard-dep closure (leaves → roots)

| Recipe | Wave | recipe.yaml | Status | Submission PR |
|---|---|---|---|---|
| primp | B1 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/primp/recipe.yaml) | on conda-forge | [#33836](https://github.com/conda-forge/staged-recipes/pull/33836) MERGED |
| jsonquerylang | B1 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/jsonquerylang/recipe.yaml) | on conda-forge | [#33846](https://github.com/conda-forge/staged-recipes/pull/33846) MERGED |
| langflow-sdk | B1 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/langflow-sdk/recipe.yaml) | submitted (CI-green, in review) | [#33856](https://github.com/conda-forge/staged-recipes/pull/33856) OPEN |
| jigsawstack | B1 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/jigsawstack/recipe.yaml) | submitted (CI-green, in review) | [#33857](https://github.com/conda-forge/staged-recipes/pull/33857) OPEN |
| smolagents | B1 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/smolagents/recipe.yaml) | submitted | [#33887](https://github.com/conda-forge/staged-recipes/pull/33887) OPEN |
| llm-sandbox | B1 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/llm-sandbox/recipe.yaml) | submitted | [#33888](https://github.com/conda-forge/staged-recipes/pull/33888) OPEN |
| pybase62 | B1 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/pybase62/recipe.yaml) | on conda-forge | [#33838](https://github.com/conda-forge/staged-recipes/pull/33838) MERGED |
| lomond | B1 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/lomond/recipe.yaml) | **CI-GREEN** (win_64 G19 PYTHONUTF8 fix landed — buildId 1543779) | [#33889](https://github.com/conda-forge/staged-recipes/pull/33889) OPEN |
| apify-shared | B1 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/apify-shared/recipe.yaml) | submitted (CI-green) | [#33890](https://github.com/conda-forge/staged-recipes/pull/33890) OPEN |
| vlmrun-hub | B1 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/vlmrun-hub/recipe.yaml) | submitted (CI-green) | [#33891](https://github.com/conda-forge/staged-recipes/pull/33891) OPEN |
| ibm-cos-sdk-core | B1 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/ibm-cos-suite/recipe.yaml) | submitted via `ibm-cos-suite` | [#33886](https://github.com/conda-forge/staged-recipes/pull/33886) OPEN |
| pymilvus-model | B1 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/pymilvus-model/recipe.yaml) | on conda-forge | [#33837](https://github.com/conda-forge/staged-recipes/pull/33837) MERGED |
| milvus-lite | B1 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/milvus-lite/recipe.yaml) | submitted (CI-green) | [#33892](https://github.com/conda-forge/staged-recipes/pull/33892) OPEN |
| couchbase | B1 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/couchbase/recipe.yaml) | fix pushed, CI re-running (win_64 OpenSSL FetchContent→conda-openssl fix — buildId 1543796; linux/osx already green) | [#33893](https://github.com/conda-forge/staged-recipes/pull/33893) OPEN |
| firecrawl-py | C* | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/firecrawl-py/recipe.yaml) | ready (built PR#24; post-lean a `run_constraints` integration, not a B1 core leaf) | — |
| trustcall | B1 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/trustcall/recipe.yaml) | blocked | — |
| qianfan | B1 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/qianfan/recipe.yaml) | blocked | — |
| ragworkbench | B1 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/ragworkbench/recipe.yaml) | blocked | — |
| toolguard | B1 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/toolguard/recipe.yaml) | blocked | — |
| pksuid | B2 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/pksuid/recipe.yaml) | **CI-GREEN** (pip_check G26 3-file-patch fix landed — buildId 1543801) | [#33895](https://github.com/conda-forge/staged-recipes/pull/33895) OPEN |
| vlmrun | B2 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/vlmrun/recipe.yaml) | blocked (→vlmrun-hub) | — |
| ddgs | B2 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/ddgs/recipe.yaml) | submitted (CI-green) | [#33896](https://github.com/conda-forge/staged-recipes/pull/33896) OPEN |
| langchain-milvus | B2 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/langchain-milvus/recipe.yaml) | submitted (CI-green) | [#33894](https://github.com/conda-forge/staged-recipes/pull/33894) OPEN |
| ibm-cos-sdk-s3transfer | B2 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/ibm-cos-suite/recipe.yaml) | submitted via `ibm-cos-suite` | [#33886](https://github.com/conda-forge/staged-recipes/pull/33886) OPEN |
| langwatch | B2 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/langwatch/recipe.yaml) | blocked (→pksuid; pybase62 on cf) | — |
| spider-client | C* | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/spider-client/recipe.yaml) | ready (post-lean a `run_constraints` integration, not a B2 hard dep) | — |
| assemblyai | C* | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/assemblyai/recipe.yaml) | ready (post-lean a `run_constraints` integration, not a B2 hard dep) | — |
| ibm-cos-sdk | B3 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/ibm-cos-suite/recipe.yaml) | submitted via `ibm-cos-suite` | [#33886](https://github.com/conda-forge/staged-recipes/pull/33886) OPEN |
| ibm-watsonx-ai | B4 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/ibm-watsonx-ai/recipe.yaml) | blocked (→ibm-cos-sdk via suite [#33886](https://github.com/conda-forge/staged-recipes/pull/33886), pending merge; also build 1.3.37 for py3.10, G40) | — |
| langchain-ibm | B5 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/langchain-ibm/recipe.yaml) | blocked (→ibm-watsonx-ai) | — |
| agent-lifecycle-toolkit | B5 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/agent-lifecycle-toolkit/recipe.yaml) | blocked (→ibm-watsonx-ai, smolagents, llm-sandbox) | — |
| opendsstar | B5 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/opendsstar/recipe.yaml) | submitted, CI-red (→pymilvus-model on cf; milvus-lite, langchain-milvus, smolagents, ragworkbench NOT on cf yet) | [#33840](https://github.com/conda-forge/staged-recipes/pull/33840) OPEN |
| **langflow-suite** (lfx + langflow-base + langflow) | B6 / B8 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/langflow-suite/recipe.yaml) | blocked (Skew 1; 3-output submission unit) | — |
| lfx-arxiv | B7 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/lfx-arxiv/recipe.yaml) | blocked (→lfx) | — |
| lfx-docling | B7 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/lfx-docling/recipe.yaml) | blocked (→lfx, docling-core) | — |
| lfx-duckduckgo | B7 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/lfx-duckduckgo/recipe.yaml) | blocked (→lfx, ddgs) | — |
| lfx-ibm | B7 | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/lfx-ibm/recipe.yaml) | blocked (→lfx, langchain-ibm, ibm-watsonx-ai) | — |

> **Folded into `langflow-suite`** (Q1 — single 3-output recipe; these dirs are kept for *local*
> build-verification only, NOT submitted standalone):
> [lfx](https://github.com/rxm7706/local-recipes/blob/main/recipes/lfx/recipe.yaml) ·
> [langflow-base](https://github.com/rxm7706/local-recipes/blob/main/recipes/langflow-base/recipe.yaml) ·
> [langflow](https://github.com/rxm7706/local-recipes/blob/main/recipes/langflow/recipe.yaml).

### Wave C — optional integrations (`run_constraints`)

| Recipe | Wave | recipe.yaml | Status | Submission PR |
|---|---|---|---|---|
| langchain-astradb | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/langchain-astradb/recipe.yaml) | blocked (→astrapy, cassio) | — |
| langchain-graph-retriever | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/langchain-graph-retriever/recipe.yaml) | blocked | — |
| langchain-google-vertexai | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/langchain-google-vertexai/recipe.yaml) | blocked | — |
| langchain-sambanova | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/langchain-sambanova/recipe.yaml) | blocked | — |
| langchain-google-community | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/langchain-google-community/recipe.yaml) | blocked (G12 numpy-selector, G35) | — |
| ag2 | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/ag2/recipe.yaml) | ready | — |
| astrapy | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/astrapy/recipe.yaml) | ready | — |
| cassio | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/cassio/recipe.yaml) | ready | — |
| cleanlab-tlm | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/cleanlab-tlm/recipe.yaml) | ready | — |
| composio-langchain | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/composio-langchain/recipe.yaml) | ready | — |
| langchain-cohere | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/langchain-cohere/recipe.yaml) | ready | — |
| langchain-google-calendar-tools | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/langchain-google-calendar-tools/recipe.yaml) | ready | — |
| langchain-nvidia-ai-endpoints | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/langchain-nvidia-ai-endpoints/recipe.yaml) | ready | — |
| langchain-pinecone | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/langchain-pinecone/recipe.yaml) | ready | — |
| langchain-unstructured | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/langchain-unstructured/recipe.yaml) | ready | — |
| langchain-weaviate | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/langchain-weaviate/recipe.yaml) | ready | — |
| mem0ai | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/mem0ai/recipe.yaml) | ready (built PR#24) | — |
| metal-sdk | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/metal-sdk/recipe.yaml) | ready | — |
| needle-python | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/needle-python/recipe.yaml) | ready | — |
| openlayer | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/openlayer/recipe.yaml) | ready | — |
| opik | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/opik/recipe.yaml) | blocked (Skew 3 otel) | — |
| scrapegraph-py | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/scrapegraph-py/recipe.yaml) | ready | — |
| upstash-vector | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/upstash-vector/recipe.yaml) | ready | — |

### Caveats / special handling

| Recipe | Wave | recipe.yaml | Status | Submission PR |
|---|---|---|---|---|
| impit | C (prereq) | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/impit/recipe.yaml) | **ALREADY ON CONDA-FORGE** (conda-forge/impit-feedstock v0.13.0, maint. Pijukatel); staged-recipes PR [#33897](https://github.com/conda-forge/staged-recipes/pull/33897) → CLOSE (linter "feedstock exists"). **Platform-expansion prepped locally**: `recipes/impit/` now mirrors the feedstock + a `conda-forge.yml` adding **osx-arm64 + linux-aarch64** (linux-aarch64 cross-build verified GREEN locally 2026-06-25; ring/aws-lc/rustls-fork all cross-compiled) — push as a feedstock PR (rerender). | feedstock PR (not staged-recipes) |
| apify-client | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/apify-client/recipe.yaml) | unblocked (→impit on cf; verify py3.11 build coverage per G38 before submit — impit 0.13.0 is py313+, 0.9.3 is py310-313) | — |
| langchain-elasticsearch | C | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/langchain-elasticsearch/recipe.yaml) | blocked (gated on [elasticsearch-feedstock #122](https://github.com/conda-forge/elasticsearch-feedstock/pull/122) — still OPEN 2026-06-24) | — |
| langchain | — | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/langchain/recipe.yaml) | **local-only skew-workaround — NEVER submit** (on cf; 1.2.18 base deps drop the stale text-splitters pin — Skew 1) | n/a |
| litellm | — | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/litellm/recipe.yaml) | **local-only skew-workaround — NEVER submit** (on cf; 1.89.3 base deps drop the proxy-extras flatten — Skew 2) | n/a |
| ragstack-ai-knowledge-store | — | [recipe.yaml](https://github.com/rxm7706/local-recipes/blob/main/recipes/ragstack-ai-knowledge-store/recipe.yaml) | **local-only — NEVER submit** (BUSL-1.1 / non-OSI) | n/a |
