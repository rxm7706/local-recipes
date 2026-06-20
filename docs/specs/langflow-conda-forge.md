# Tech Spec: langflow on conda-forge

> **BMAD intake document.** Written for `bmad-quick-dev` / `bmad-dev` (Quick Flow
> track — bounded packaging effort, dependency-closure already authored; the
> remaining work is external conda-forge ecosystem pin-convergence + staged-recipes
> submission).
> Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/langflow-conda-forge.md
> ```
>
> **Rule 1 (always-on):** every recipe touch here MUST go through the
> `conda-forge-expert` skill. **Rule 2:** closeout runs a CFE-skill retro.

---

## Status

| Field        | Value |
| ------------ | ----- |
| Status       | **Local closure authored & built; blocked on external cf ecosystem skews** (2026-06-19). The full langflow prerequisite closure (~25 net-new recipes across 4 recursion layers) is authored and built into the local channel; `langflow` itself reaches **build-phase GREEN**. The test-env solve is blocked by two **irreducible external conda-forge version-skews** (not local-authoring problems) — see **§ The Two External Blockers**. |
| Owner        | rxm7706 |
| Track        | BMAD Quick Flow (tech-spec only) |
| Upstream     | `langflow-ai/langflow` v1.10.0 (MIT). Split into `langflow` (umbrella) + `langflow-base` + `lfx` (the "Langflow eXecutor" core) + `lfx-*` extension plugins, all in the one monorepo. |
| Target       | `conda-forge/staged-recipes` → `langflow` + its prerequisite closure (most `noarch: python`; `primp` is compiled Rust; `couchbase` compiled C++). |
| Distribution | conda-forge linux-64 first; `noarch: python` for all but the 2 compiled prereqs. |
| Real `python_min` | **3.11** (NOT the upstream-aspirational 3.10 — `jsonquerylang`, a hard dep of `langflow-base`, imports `typing.NotRequired` (PEP 655, py3.11+) unconditionally; see **G41**). |
| Lifetime     | Long-running — feedstocks become autotick-maintained after first PR lands. |

---

## Effort Status (2026-06-19)

This session drove the langflow build from "79 prereqs assumed" to "full transitive
closure authored, langflow build-green, blocked only on external cf skews." All recipes
are built into the **local merged channel** (`build_artifacts/linux64/`, ~222 noarch +
153 linux-64 artifacts) and validated; **all are uncommitted pending review → being
checked in with this spec** so `bmad-dev` can resume.

### What "build-phase GREEN, test-blocked" means here

`langflow`'s wheel installs and the `.conda` packages cleanly. The failure is purely in
the **test-environment solve** — the full dependency graph cannot be satisfied against
the current conda-forge channel because of cross-feedstock pin skew (below). This is the
**External-cf-ecosystem-skew** class in the CFE skill's Build Failure Protocol (added
v8.35.0): when the full graph fails but each conflicting sub-cluster solves *in
isolation*, it is a feedstock-convergence problem, not a recipe defect.

### Recursion map (how the closure was discovered)

```
langflow 1.10.0  (umbrella; build-GREEN, test-blocked)
├── langflow-base 0.10.0   → lfx, ibm-watsonx-ai, langchain-ibm, opendsstar, jsonquerylang(*py3.11 floor)
├── lfx 1.10.0 (core)      → opendsstar, langflow-sdk(✓channel), markitdown(✓cf)
│   ├── lfx-arxiv 0.1.1    → (defusedxml ✓cf) ; opendsstar via lfx
│   ├── lfx-docling 0.1.1  → docling-core ✓cf ; opendsstar via lfx
│   ├── lfx-duckduckgo 0.1.1 → ddgs → **primp** (compiled Rust)
│   └── lfx-ibm 0.1.1      → langchain-ibm, ibm-watsonx-ai
├── opendsstar 1.0.26      → pymilvus-model, milvus-lite, langchain-litellm, langchain-milvus, smolagents, ragworkbench
├── ibm-watsonx-ai 1.5.13  → ibm-cos-sdk → ibm-cos-sdk-core + ibm-cos-sdk-s3transfer (rebuilt @2.14.3), lomond(✓channel)
├── langchain-ibm 1.1.0    → ibm-watsonx-ai
├── agent-lifecycle-toolkit 0.10.1 (import `altk`) → ibm-watsonx-ai, llm-sandbox(✓channel), smolagents(✓channel)
├── jigsawstack 0.4.5      → (all ✓cf)
└── langwatch 0.26.0       → pksuid + pybase62 (✓channel)
```

### Recipe inventory & status

**langflow-family (8):**

| Recipe | Ver | Build | cfe-status | Notes |
|--------|-----|-------|-----------|-------|
| langflow | 1.10.0 | build-GREEN, test-blocked | blocked-pending-prerequisites | the umbrella; `python_min`→3.11; G10 `docstring-parser`→`docstring_parser` fixed |
| langflow-base | 0.10.0 | build-GREEN | blocked-pending-prerequisites | wheel-only; import `langflow`; `python_min`→3.11 (jsonquerylang) |
| lfx | 1.10.0 | build-GREEN | blocked-pending-prerequisites | wheel-only; G10 `docstring-parser`→`docstring_parser` |
| lfx-arxiv | 0.1.1 | build-GREEN | blocked-pending-prerequisites | wheel-only; blocked transitively on opendsstar via lfx |
| lfx-docling | 0.1.1 | build-GREEN | blocked-pending-prerequisites | heavy `docling`/`torch` correctly dropped (un-activated extras, G25) |
| lfx-duckduckgo | 0.1.1 | build-GREEN | blocked-pending-prerequisites | → ddgs → primp |
| lfx-ibm | 0.1.1 | build-GREEN | blocked-pending-prerequisites | → langchain-ibm + ibm-watsonx-ai; G10 `ibm-db`→`ibm_db` |
| langflow-sdk | 0.2.0 | GREEN | (pre-built earlier) | already in channel |

**Net-new leaf/integration recipes (closure):**

| Recipe | Ver | Build | cfe-status | Notes |
|--------|-----|-------|-----------|-------|
| ddgs | 9.14.4 | build-GREEN | blocked-pending-prerequisites | → primp; G25 httpx-extras flatten; `socks`→`socksio` rename |
| primp | 1.3.1 | **GREEN** | pending-submission | compiled Rust/PyO3 abi3-py310; OpenSSL routed to conda via `OPENSSL_NO_VENDOR`; abi3audit clean |
| opendsstar | 1.0.26 | build-GREEN | blocked-pending-prerequisites | import `OpenDsStar` (G7 trap); Apache-2.0; → pymilvus-model + milvus-lite |
| pymilvus-model | 0.3.2 | **GREEN** | pending-submission | import `pymilvus.model` (dotted, G7); `pin_version.py` fixes setuptools_scm-private-API bug (**G39**) |
| milvus-lite | 3.0 | **GREEN** | pending-submission | 3.0 is a **pure-Python rewrite** of the old C++ binary (**G42**); pip_check=false (G28 faiss-cpu/faiss dist-name) |
| ibm-watsonx-ai | 1.5.13 (+1.3.37) | build-GREEN | blocked-pending-prerequisites | BSD-3; G35 pandas-marker collapse; 1.3.37 also built for py3.10 (**G40**) |
| ibm-cos-sdk | 2.14.3 | **GREEN** | blocked-pending-prerequisites | meta over core+s3transfer; import `ibm_boto3` (G7); version-aligned to ibm-watsonx-ai `<2.15` |
| ibm-cos-sdk-core | 2.14.3 | GREEN | blocked-pending-prerequisites | rebuilt 2.16.2→2.14.3 (G26 stale-artifact removal) |
| ibm-cos-sdk-s3transfer | 2.14.3 | GREEN | blocked-pending-prerequisites | rebuilt 2.16.2→2.14.3; hard-pins core== |
| langchain-ibm | 1.1.0 | build-GREEN | blocked-pending-prerequisites | G35 marker-collapse; G40 (needs ibm-watsonx-ai 1.3.37 on py3.10) |
| agent-lifecycle-toolkit | 0.10.1 | build-GREEN | blocked-pending-prerequisites | import `altk` (G7); G25/G26/G35 applied |
| jigsawstack | 0.4.5 | **GREEN** | pending-submission | sdist broken (`requirements.txt` not packaged) → wheel; clean leaf |
| langwatch | 0.26.0 | build-GREEN | blocked-pending-prerequisites | pksuid+pybase62 local; NOT in langflow's actual blocker path |
| jsonquerylang | 1.1.1 | GREEN | (rebuilt) | forces py3.11 floor (**G41**); pin mirrored `>=1.1.1,<2.0.0` |

**Twelve already-had-recipes prereqs built into the channel this session:**
`firecrawl-py` (GREEN), `langchain-astradb` (GREEN), `langchain-graph-retriever` (GREEN),
`langchain-google-vertexai` (GREEN), `langchain-sambanova` (GREEN), `trustcall` (GREEN),
`vlmrun`/`vlmrun-hub` (GREEN), `qianfan` (GREEN), `couchbase` (GREEN, compiled C++ py310-313),
`langchain-elasticsearch` (**TEST-BLOCKED — `elasticsearch >=8.19,<9` does not exist on
conda-forge**; feedstock jumps 8.18.0→9.0.0), `apify-client` (**TEST-BLOCKED — `impit`
only py310 in channel, needs py311+, G38**).

**Wave-2 stragglers (also langflow prereqs), built this session:**
`ragstack-ai-knowledge-store` (GREEN; BUSL-1.1 — non-OSI, future cf-eligibility concern),
`ragworkbench` (GREEN), `toolguard` (GREEN; `fastmcp>=2.14` floor bump, G36), `apify-shared`
(GREEN), `langchain-google-community` (GREEN; G12 numpy-selector fix, G35).

---

## The Two External Blockers (the remaining work)

These are conda-forge **feedstock pin-convergence** problems. No local prerequisite
authoring resolves them; each conflicting sub-cluster solves *in isolation* on cf, but
the full langflow graph does not.

### B-1 — litellm ↔ lfx fastapi/cryptography skew

- `lfx 1.10.0` requires `fastapi>=0.135.0,<1.0` + `cryptography>=46.0.7`.
- Every conda-forge `litellm` build (pulled in via `opendsstar>=1.83.0`) bakes
  `fastapi==0.124.4` (litellm 1.83–1.87) or conflicting `langchain-text-splitters`/otlp
  pins (1.88+).
- `litellm + fastapi + cryptography` solves *in isolation* on cf; the conflict only
  appears where lfx's langchain stack meets litellm's.

### B-2 — observability cluster otel skew

- `traceloop-sdk` forces `opentelemetry-semantic-conventions ==0.57b0..0.62b0` +
  `langchain>=0.3.15,<0.4.0`.
- This conflicts with `arize-phoenix-otel` / `opik` / `openinference-*` and lfx's newer
  `langchain`.

**Resolution paths (for `bmad-dev`):** (a) drive cf-feedstock pin convergence — file
issues/PRs to `litellm-feedstock`, the otel/`traceloop-sdk`/`openinference-*` feedstocks
to widen the offending pins; (b) rebuild the conflicting cf packages locally at compatible
versions (deep, uncertain); (c) wait for upstream langflow to loosen its own constraints.
**(a) is the canonical conda-forge path.**

---

## Implementation Plan (for `bmad-dev`)

### Wave A — Clear the external skews (the gate to GREEN)

- **S1 — litellm/fastapi convergence.** Via the CFE skill: `whodepends litellm`,
  `behind-upstream litellm`; identify the cf `litellm` build whose `fastapi` pin can be
  widened to admit `>=0.135`; file the feedstock issue/PR (or rebuild `litellm` locally at
  a fastapi-compatible version into the channel). Verify `lfx` + `litellm` co-resolve.
- **S2 — otel/observability-cluster convergence.** Same approach for
  `opentelemetry-semantic-conventions` / `traceloop-sdk` / `arize-phoenix-otel` /
  `openinference-*`; widen the `langchain<0.4` + otel pins so lfx's newer langchain
  co-resolves. (May require coordinating several feedstocks.)
- **S3 — langflow GREEN.** After S1+S2, re-attempt the langflow build via the merged-CBC
  local channel; require EXIT=0 + both CFEP-25 test legs passing (py3.11 + `*`). Flip
  `langflow`'s `cfe-on-conda-forge-status` to `pending-submission-to-conda-forge`.

### Wave B — Submit the closure (after GREEN)

- **S4..Sn — staged-recipes submission in dependency order** (leaves first): `primp`,
  `jigsawstack`, `pymilvus-model`, `milvus-lite`, `ddgs`, the IBM chain, `opendsstar`,
  then the langflow-family, then `langflow` last. Strip `extra.cfe-*` on push. Honor the
  two known **cf-eligibility caveats**: `ragstack-ai-knowledge-store` is **BUSL-1.1**
  (non-OSI — likely *not* cf-submittable as-is); `langchain-elasticsearch` is blocked on
  the **`elasticsearch >=8.19` feedstock gap** (file a version-bump request on
  `elasticsearch-feedstock`).
- **S — milvus-lite/`apify-client` follow-ups:** `apify-client` needs an `impit` py311+
  channel build (G38); `milvus-lite` reviewer may prefer `pip_check: true` with a faiss
  exception.

### Wave C — Closeout

- **S — CFE-skill retro** (Rule 2). The authoring wave already shipped **v8.35.0**
  (G39–G43 + external-skew Build-Failure-Protocol note); a Wave-A/B closeout retro folds
  in whatever the feedstock-convergence + submission work surfaces.

---

## Reproducing the local channel

```bash
# merged-CBC channel lives at build_artifacts/linux64/ (gitignored; rebuild from recipes/)
# build any recipe into it:
pixi run -e local-recipes rattler-build build \
  --recipe recipes/<name>/recipe.yaml \
  --variant-config .claude/data/conda-forge-expert/localchannel-cbc/conda_build_config.yaml \
  --output-dir /tmp/bld-<name>
# gather the artifact into the channel + reindex:
cp /tmp/bld-<name>/{noarch,linux-64,broken}/*.conda build_artifacts/linux64/{noarch,linux-64}/
pixi run -e local-recipes python -m conda_index build_artifacts/linux64
```

Channel build order (leaves → roots): primp → ddgs; ibm-cos-sdk-{core,s3transfer}@2.14.3
→ ibm-cos-sdk → ibm-watsonx-ai{1.3.37,1.5.13} → langchain-ibm/agent-lifecycle-toolkit;
pymilvus-model + milvus-lite + (langchain-litellm/milvus, smolagents, ragworkbench) →
opendsstar; jsonquerylang@1.1.1; langflow-sdk → lfx → lfx-* ; langflow-base → langflow.

---

## Open Questions

- **Q1 — external-skew strategy.** Drive cf-feedstock PRs (canonical, slow) vs. rebuild
  litellm/otel cluster locally (fast, uncertain) vs. wait for upstream langflow? Spec
  recommends the feedstock-PR path with a local-rebuild fallback for fast iteration.
- **Q2 — ragstack-ai-knowledge-store BUSL-1.1.** Non-OSI; likely drop from the cf
  submission set (it's a transitive opendsstar dep) — confirm whether opendsstar can
  resolve without it, or whether opendsstar itself is cf-eligible.
- **Q3 — python_min 3.11.** Confirm conda-forge is OK with langflow declaring `python_min
  3.11` (it is the honest floor per G41); the upstream `requires-python>=3.10` is broken.
- **Q4 — apify-client/impit.** Build `impit` for the py311+ matrix, or drop `apify-client`
  from langflow's hard deps (is it an optional tool?).

---

## Worked Example: the 2026-06-19 session

Authored the full closure in 4 recursion layers (each layer's `check_dependencies` drove
the next), surfacing CFE gotchas **G35 (applied), G39–G43 (new)** + the external-skew
protocol. `langflow` reached build-GREEN; the residual is the 2 external skews above.
**13 recipes built fully GREEN** (`primp`, `pymilvus-model`, `milvus-lite`, `jigsawstack`,
`ibm-cos-sdk` chain, the 12 existing prereqs, the Wave-2 stragglers); the rest are
build-GREEN/test-blocked on the external skews. Retro shipped **CFE v8.35.0**.
