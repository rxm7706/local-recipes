---
status: ready
implemented_by: bmad-quick-dev
shipped_ref: "full local closure built GREEN (incl. ALL Set-C integrations now authored); conda-forge submission + skew-fix unimplemented; ultraplan-grounded + Q1–Q5 resolved 2026-06-23"
scope: full-closure   # core hard-dep closure + ALL optional run_constraints integrations (Set C now ALL authored locally) + ALL 3 external cf skews. Nothing deferred except the 3 named caveats (handled per § Caveats: elasticsearch gated on cf PR #122; apify-client attempt-or-drop; ragstack kept local-only).
spec_updated: 2026-06-23
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
> provider wrapper + SDK leaf — **including the ~20 not yet authored** (§ Submission set C),
> which must be **authored, their own recursive sub-closures resolved, and submitted**;
> **(3)** **ALL THREE external cf skews fixed** — Skew 1 (langchain-text-splitters) gates the
> core suite; Skews 2 (litellm/fastapi) + 3 (otel/observability) gate the optional integrations
> — all three are in scope.
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
> with one important caveat (see § Packaging shape — the lfx-split decision).

---

## Status

| Field | Value |
| ----- | ----- |
| Status | **Local closure built GREEN; conda-forge submission not started; langflow-suite test-blocked on one external cf skew.** All ~46 core prerequisite recipes AND **all ~18 Set-C optional integrations are now authored + built** into the local channel (ultraplan re-grounding, 2026-06-23 — Set C is no longer "to author"; `spider-client`, `assemblyai`, `impit` are all present + `build=success`). `recipes/langflow-suite/` builds clean for all 3 outputs (`--test skip` GREEN, 2026-06-23). The langflow-suite test-env solve is blocked by the **langchain-text-splitters** skew (§ External Skews). **Residual work is now skew-fix → re-verify GREEN → leaves-first submission** (authoring is effectively complete). Only `firecrawl-py` lacks a build record and needs a verification build. |
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
- **⚠ Cross-feedstock cycle → KEEP the single 3-output recipe (Q1 RESOLVED — do NOT split).**
  `langflow` (a suite output) hard-deps the 4 `lfx-*`; each `lfx-*` deps `lfx` (also a suite
  output). **Decision (rxm7706, 2026-06-23):** keep the **single 3-output `langflow-suite`
  recipe** (lfx + langflow-base + langflow) so the three versions stay locked together — better
  long-term (one feedstock; autotick bumps lfx/langflow-base/langflow in lockstep). This
  overrides the earlier "split lfx out" recommendation.
  The residual is a **bootstrap cycle at the *initial* staged-recipes gate**: `langflow`'s
  test-env solve needs the 4 separate `lfx-*` feedstocks, which need `lfx` (a suite output not
  yet on cf). **Mitigation = sequencing + a temporary test relaxation, NOT splitting:** submit
  the 3-output suite first so `lfx` publishes → submit the 4 `lfx-*` (now `lfx` is on cf) →
  build-number-bump follow-up to tighten/enable `langflow`'s full test (or relax just the
  `langflow` output's lfx-* import test on the first submission, then re-enable). Once all are
  on cf the single-feedstock shape is exactly what's wanted.
- **Dependency lists come from upstream pyproject, not the hand-authored recipe lists.** Earlier
  the recipe's output `run:` lists diverged from upstream (e.g. fabricated `atlaspy`/`dynamicconf`;
  truncated `lfx` deps). For each output, flatten the real upstream `[project.dependencies]`
  (+ `langflow-base[complete]` for the umbrella, **G25** — conda has no extras), mirror upstream
  version caps (**G24** — `pip_check` enforces them), and verify with `check_dependencies` on a
  **flattened single-output** recipe (**G29** — the multi-output checkers are top-level-only).

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
| primp | pending-submission | compiled Rust | MIT | — (leaf) |
| jsonquerylang | pending-submission | noarch | ISC | — (forces py3.11, G41) |
| langflow-sdk | pending-submission | noarch | MIT | — |
| jigsawstack | pending-submission | noarch | MIT | — |
| smolagents | pending-submission | noarch | Apache-2.0 | — |
| llm-sandbox | pending-submission | noarch | MIT | — |
| pybase62 | pending-submission | noarch | BSD-2 | — |
| lomond | pending-submission | noarch | BSD-3 | — |
| pksuid | blocked-pending-prereq | noarch | MIT | pybase62 |
| apify-shared | pending-submission | noarch | Apache-2.0 | — |
| vlmrun-hub | pending-submission | noarch | Apache-2.0 | — |
| vlmrun | blocked-pending-prereq | noarch | Apache-2.0 | vlmrun-hub |
| couchbase | pending-submission | compiled C++ | multi (Apache/MIT/BSD/CC0) | — |
| pymilvus-model | pending-submission | noarch | Apache-2.0 | — |
| milvus-lite | pending-submission | noarch | Apache-2.0 | — (3.0 pure-Python, G42; pip_check off, G28) |
| ibm-cos-sdk-core | pending-submission | noarch | Apache-2.0 | — |
| ibm-cos-sdk-s3transfer | blocked-pending-prereq | noarch | Apache-2.0 | ibm-cos-sdk-core (==) |
| ibm-cos-sdk | blocked-pending-prereq | noarch | Apache-2.0 | core + s3transfer |
| ibm-watsonx-ai | blocked-pending-prereq | noarch | BSD-3 | ibm-cos-sdk (also build 1.3.37 for py3.10, G40) |
| langchain-milvus | pending-submission | noarch | MIT | pymilvus-model |
| ddgs | blocked-pending-prereq | noarch | MIT | primp |
| trustcall | blocked-pending-prereq | noarch | MIT | — |
| qianfan | blocked-pending-prereq | noarch | Apache-2.0 | — |
| ragworkbench | blocked-pending-prereq | noarch | Apache-2.0 | — |
| toolguard | blocked-pending-prereq | noarch | Apache-2.0 | — (fastmcp>=2.14 floor, G36) |
| langwatch | blocked-pending-prereq | noarch | MIT | pksuid, pybase62 |
| langchain-ibm | blocked-pending-prereq | noarch | MIT | ibm-watsonx-ai |
| agent-lifecycle-toolkit | blocked-pending-prereq | noarch | Apache-2.0 | ibm-watsonx-ai, smolagents, llm-sandbox (import `altk`, G7) |
| opendsstar | blocked-pending-prereq | noarch | Apache-2.0 | pymilvus-model, milvus-lite, langchain-milvus, smolagents, ragworkbench (import `OpenDsStar`, G7) |
| firecrawl-py | (built) | noarch | MIT | — (langflow-base hard dep) |
| spider-client | pending-submission | noarch | MIT | — (leaf; langflow-base hard dep) |
| assemblyai | pending-submission | noarch | MIT | — (leaf; langflow-base hard dep) |
| **lfx** *(SPLIT OUT — own feedstock)* | blocked-pending-prereq | noarch | MIT | langflow-sdk, opendsstar, jsonquerylang, markitdown(cf), langchain+langchain-classic(cf) |
| lfx-arxiv | blocked-pending-prereq | noarch | MIT | lfx |
| lfx-docling | blocked-pending-prereq | noarch | MIT | lfx, docling-core(cf) |
| lfx-duckduckgo | blocked-pending-prereq | noarch | MIT | lfx, ddgs |
| lfx-ibm | blocked-pending-prereq | noarch | MIT | lfx, langchain-ibm, ibm-watsonx-ai (import `ibm_db`, G10) |
| langchain-astradb | blocked-pending-prereq | noarch | MIT | (astrapy, cassio — see C) |
| langchain-graph-retriever | blocked-pending-prereq | noarch | Apache-2.0 | — |
| langchain-google-vertexai | blocked-pending-prereq | noarch | MIT | — |
| langchain-sambanova | blocked-pending-prereq | noarch | MIT | — |
| langchain-google-community | blocked-pending-prereq | noarch | MIT | — (G12 numpy-selector, G35) |
| **langflow-base** *(suite)* | blocked-pending-prereq | noarch | MIT | lfx, jsonquerylang, spider-client, assemblyai, firecrawl-py, langchain stack |
| **langflow** *(suite)* | blocked-pending-prereq | noarch | MIT | langflow-base[complete], lfx-arxiv, lfx-docling, lfx-duckduckgo, lfx-ibm |

> **Re-verify before each wave:** **`spider-client`** and **`assemblyai`** (both langflow-base
> BASE deps) are now **authored + `build=success` locally** (ultraplan scan 2026-06-23) — no
> longer "to author". BMAD must still flatten each output's real upstream `[project.dependencies]`
> (umbrella also `langflow-base[complete]`, G25), run `check_dependencies` on the **flattened
> single-output** recipe (G29 — multi-output checkers are top-level-only), and author any
> still-missing leaf before that wave. Only `firecrawl-py` currently lacks a `cfe-local-build-*`
> record — build + verify it in Wave A.

### C. Optional integrations (`run_constraints`) — full-closure scope

Soft constraints; they do not block langflow-suite install, but the full suite experience wants
them on cf. **CORRECTION (ultraplan scan 2026-06-23): the entire Set-C list below is now AUTHORED
+ present locally** — the spec's earlier "not yet authored" claim is stale. Authoring is
effectively complete; Wave C is now **re-verify each leaf → submit leaves-first**, not "author +
submit". Set C (all present): `ag2`, `astrapy`, `cassio`, `cleanlab-tlm`, `composio-langchain`,
`langchain-cohere`, `langchain-google-calendar-tools`, `langchain-nvidia-ai-endpoints`,
`langchain-pinecone`, `langchain-unstructured`, `langchain-weaviate`, `mem0ai`, `metal-sdk`,
`needle-python`, `openlayer`, `opik`, `scrapegraph-py`, `upstash-vector` — plus the 5 already-built
`langchain-*` in table B and the now-relocated-to-B `spider-client` + `assemblyai` (langflow-base
hard deps, not optional). Submit each leaf (SDK) before its `langchain-*` wrapper; re-run
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
- **`apify-client` — was blocked on `impit` py311+** (G38). **Q4 RESOLVED: ATTEMPT — `impit` is now
  present + `build=success` locally.** Verify `impit` covers the consumer's py3.11 matrix (G38),
  then include `apify-client`. **Flag as at-risk: if it can't be unblocked cleanly, DROP it**
  (optional integration; dropping is acceptable).

---

## External conda-forge skews (Wave A — the gate to GREEN)

These are conda-forge **feedstock pin-convergence** problems: each conflicting sub-cluster solves
*in isolation* on cf, but the full langflow graph does not. Per the CFE Build-Failure-Protocol
"external cf ecosystem version-skew" case — fix upstream, do not churn the consumer recipe.

### Skew 1 — langchain-text-splitters (PRIMARY hard blocker; the only one blocking langflow-suite core)

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
- **Approach RESOLVED (rxm7706, 2026-06-23): local rebuild FIRST, then the upstream PR.** Rebuild
  `langchain` locally with the loosened text-splitters pin to confirm `lfx` + the 3-output
  `langflow-suite` go **test-GREEN on the py3.11 leg** fast (no outward action / no waiting on
  external review). THEN file the ~1-line `conda-forge/langchain-feedstock` PR as the durable fix.
  The local rebuild is the iteration loop; the upstream PR is what actually unblocks cf submission.
- **Note:** `langchain 1.2.x` is NOT py3.13-only — it has `pymin310` builds (`python >=3.10,<3.13`)
  covering py3.11; Python is not the blocker, the text-splitters pin is.
- **Diagnosis test:** solve `langchain` + `langchain-classic` + `langchain-text-splitters` in
  isolation on cf — confirms the conflict is feedstock-internal, not a consumer defect.

### Skew 2 — litellm ↔ lfx fastapi/cryptography (full-integration path)

- `lfx 1.10.0` needs `fastapi>=0.135.0,<1.0` + `cryptography>=46.0.7`. cf `litellm` (pulled via the
  `opendsstar`→litellm path in the `[complete]` closure) bakes `fastapi==0.124.4` (litellm 1.83–1.87)
  or conflicting otlp/text-splitters pins (1.88+).
- **Fix:** PR `litellm-feedstock` to widen the `fastapi` pin to admit `>=0.135`, or rebuild
  `litellm` locally at a fastapi-compatible version. Only bites the optional integration closure,
  not the core suite.

### Skew 3 — otel / observability cluster

- `traceloop-sdk` forces `opentelemetry-semantic-conventions ==0.57b0..0.62b0` + `langchain>=0.3.15,<0.4.0`,
  conflicting with `arize-phoenix-otel` / `opik` / `openinference-*` and lfx's newer `langchain`.
- **Fix:** widen the otel / `traceloop-sdk` / `openinference-*` feedstock pins (may require
  coordinating several feedstocks). Optional-integration scope only.

---

## Waved submission plan

> Strip every `extra.cfe-*` key + the `# CFE …` comment blocks before any push. Build + test each
> recipe locally (against the merged local channel) before pushing. After each feedstock push,
> request rerender.

### Wave A — clear the external skews (gate to langflow-suite test-GREEN)

- **A1 — langchain-text-splitters (Skew 1).** **Local rebuild FIRST** (resolved approach): rebuild
  `langchain` locally with the loosened text-splitters pin → rebuild `lfx` → re-attempt the
  3-output `langflow-suite` → require all 3 outputs **build + test GREEN (py3.11 leg)**. This is the
  **only** skew blocking the core suite. THEN file + land the `conda-forge/langchain-feedstock`
  ~1-line pin fix (the durable unblock for cf submission). Also in A1: **build + verify
  `firecrawl-py`** (only closure recipe lacking a build record), and confirm `opendsstar` resolves
  without `ragstack-ai-knowledge-store`. Flip affected cfe-status to `pending-submission-to-conda-forge`.
- **A2 — litellm/fastapi (Skew 2)** and **A3 — otel cluster (Skew 3).** Needed only for the
  optional-integration closure (Wave C). Drive in parallel; not a gate for Wave B.

### Wave B — submit the core hard-dep closure (leaves → roots)

1. **B1 (leaves):** primp, jsonquerylang, langflow-sdk, jigsawstack, smolagents, llm-sandbox,
   pybase62, lomond, apify-shared, vlmrun-hub, ibm-cos-sdk-core, pymilvus-model, milvus-lite,
   couchbase, firecrawl-py, trustcall, qianfan, ragworkbench, toolguard.
2. **B2:** pksuid (→pybase62), vlmrun (→vlmrun-hub), ddgs (→primp), langchain-milvus (→pymilvus-model),
   ibm-cos-sdk-s3transfer (→core), langwatch (→pksuid, pybase62), + author/submit **spider-client**,
   **assemblyai** (langflow-base hard deps).
3. **B3:** ibm-cos-sdk (→core + s3transfer).
4. **B4:** ibm-watsonx-ai (→ibm-cos-sdk); also build 1.3.37 for the py3.10 leg (G40).
5. **B5:** langchain-ibm (→ibm-watsonx-ai), agent-lifecycle-toolkit (→ibm-watsonx-ai, smolagents,
   llm-sandbox), opendsstar (→pymilvus-model, milvus-lite, langchain-milvus, smolagents, ragworkbench).
6. **B6 (single 3-output suite — Q1 RESOLVED, NOT split):** submit `recipes/langflow-suite/`
   producing **lfx + langflow-base + langflow** in one PR (→ langflow-sdk, opendsstar,
   jsonquerylang, spider-client, assemblyai, firecrawl-py + cf langchain stack). Because the 4
   `lfx-*` feedstocks aren't on cf yet, **temporarily relax the `langflow` output's lfx-* import
   test** for this first submission (the bootstrap cycle — see § Packaging shape). This publishes
   `lfx`.
7. **B7:** submit the 4 `lfx-*` feedstocks (now that `lfx` is on cf): lfx-arxiv, lfx-docling,
   lfx-duckduckgo (→ddgs), lfx-ibm (→langchain-ibm, ibm-watsonx-ai) — all → lfx.
8. **B8 (follow-up):** build-number-bump PR on `langflow-suite` to **re-enable / tighten the
   `langflow` output's full lfx-* test** now that all 4 `lfx-*` are on cf. Suite versions stay
   locked together from here on (autotick maintains lfx/langflow-base/langflow in lockstep).

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
  surfaces. The authoring wave already shipped CFE v8.35.0 (G39–G43 + external-skew protocol).

---

## Reproducing the local channel

```bash
# merged-CBC channel at build_artifacts/linux64/ (gitignored; rebuild from recipes/).
# build one recipe into it (tests skipped while the skew is unresolved):
pixi run -e local-recipes rattler-build build \
  --recipe recipes/<name>/recipe.yaml \
  --variant-config .pixi/envs/local-recipes/conda_build_config.yaml \
  --output-dir build_artifacts/linux64 --test skip
pixi run -e local-recipes python -m conda_index build_artifacts/linux64
```

Channel build order (leaves → roots): primp → ddgs; pybase62 → pksuid; vlmrun-hub → vlmrun;
ibm-cos-sdk-{core,s3transfer} → ibm-cos-sdk → ibm-watsonx-ai{1.3.37,1.5.13} →
langchain-ibm / agent-lifecycle-toolkit; pymilvus-model + milvus-lite + langchain-milvus +
smolagents + ragworkbench → opendsstar; jsonquerylang; langflow-sdk → lfx → lfx-* ;
langflow-base → langflow.

---

## Open Questions — ALL RESOLVED 2026-06-23 (rxm7706, via ultraplan)

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
  (https://github.com/conda-forge/elasticsearch-feedstock/pull/122, UP). Submit once #122 merges.

---

## Worked Example: the 2026-06-19 → 2026-06-23 sessions

The 2026-06-19 session authored the full transitive closure (4 recursion layers; each layer's
`check_dependencies` drove the next), surfacing CFE gotchas **G35, G39–G43** + the external-skew
Build-Failure-Protocol note (shipped CFE v8.35.0). The 2026-06-23 session fixed the
`langflow-suite` recipe (schema/lint repair; corrected the `lfx` output's truncated run list to
upstream's ~43 deps with G24 caps + G25 `httpx[http2]` flatten), confirmed **all 3 outputs build
GREEN** (`--test skip`), and pinned the residual blocker to **Skew 1 (langchain-text-splitters)** —
a stale `langchain-feedstock` pin, the precise fix for which is Wave A1.

The **2026-06-23 ultraplan re-grounding** session (this update) read the spec in full under the
`conda-forge-expert` skill, **re-scanned `recipes/` against the closure**, and found the repo
materially ahead of the spec's prose: **all ~46 core recipes AND all ~18 Set-C optional
integrations are now authored + built** (Set C is no longer "to author"); `spider-client`,
`assemblyai`, and `impit` are all present + `build=success`; only `firecrawl-py` lacks a build
record. The residual work is therefore **skew-fix → re-verify GREEN → leaves-first submission**,
not authoring. It also **resolved all five open questions** (Q1 single 3-output recipe / no split;
Q2 ragstack local-only commented-out; Q3 python_min 3.11; Q4 apify-client attempt-or-drop; Q5
langchain-elasticsearch gated on cf `elasticsearch-feedstock` PR #122) and recorded the **Skew 1
approach** (local langchain rebuild first to verify GREEN, then the upstream feedstock PR).
Execution (Waves A–D) is unstarted and gated on explicit per-action go-ahead; no pushes/PRs yet.
