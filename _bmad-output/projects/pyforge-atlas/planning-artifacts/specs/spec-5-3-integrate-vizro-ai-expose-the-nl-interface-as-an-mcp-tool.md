---
title: 'Story D3 (5.3): Integrate Vizro-AI + expose the NL interface as an MCP tool'
type: 'feature'
status: shipped
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #88 body + main commit log; dev narrative recovered, review-triage partial)'
---

> **Contract-spec — no original ever existed (corrected 2026-07-25).** This story
> (wave B9–H4) was built by the atlas migration's **in-session agent loop**, which —
> unlike `bmad-create-story` (used only for waves 0/A/B1–B8) — never emitted a per-story
> spec file. The atlas migration session (`01FYyQvBJuXwySiaMUUYCqBZ`) confirmed this
> exhaustively: no such file exists in `implementation-artifacts/`, `.bmad-loop/runs/`
> (which never existed for atlas), any git worktree, git history, or anywhere on disk.
> **Nothing was lost — there is no original to recover.** This file carries the
> load-bearing contract (Intent + Acceptance Criteria **verbatim** from the tracked
> `planning-artifacts/epics.md`) plus a dev narrative reconstructed from the merged record
> (the "Dev narrative" section below). A fuller BMAD-story-format reconstruction (Dev
> Agent Record + File List + Review Triage Log, built from the agent-loop transcripts) is
> at `../../spec-archive/retro-story-files/5-3-d3.md` — the operator's web-session archive.

## Contract (from epics.md — verbatim, authoritative)

### Story D3 (5.3): Integrate Vizro-AI + expose the NL interface as an MCP tool

As a CFE authoring agent (and the operator),
I want a Vizro-AI natural-language query field and a `query_vizro_ai` MCP tool over the BSL knowledge graph,
So that ad-hoc questions need no SQL and are callable from Claude Code.

**Acceptance Criteria:** (spec § 9 Story D3, binding)

**Given** the D1 BSL graph and the D2 dashboard
**When** Vizro-AI is integrated
**Then** a natural-language query (e.g. the § 4.3 example) returns a generated chart/insight
**And** the `query_vizro_ai` MCP tool is callable from Claude Code
**And** the LLM backend routes through repo model-backend configuration — never a hardcoded public endpoint (Q3 default).

- **FRs:** FR-9.
- **Invariants:** AD-8, AD-7 (MCP body carries no metric logic).
- **Mode:** ATTENDED (backend boundary event — one of the five § 2.5 attended events).
- **Gating question:** **Q3** (Vizro-AI LLM backend) — § 11 default adopted: route through repo model-backend configuration; defining the `_http.py`-analog LLM routing chain is the real work; bounds: no litellm (py3.14 floor), copilot-api bridge ineligible, llama.cpp/ollama/mlx-lm in-env.
- **Verify gate:** `bsl-metric-check` (existing; NL path verified at the attended event).
- **Depends on:** D1, D2.

## Tasks / Subtasks

*(Derived from the ACs — no original task breakdown was authored for this loop-run story.)*

- [x] a natural-language query (e.g. the § 4.3 example) returns a generated chart/insight
- [x] the `query_vizro_ai` MCP tool is callable from Claude Code
- [x] the LLM backend routes through repo model-backend configuration — never a hardcoded public endpoint (Q3 default).

## Dev Notes

**Planning metadata (from `epics.md`):**

- **FRs:** FR-9.
- **Invariants:** AD-8, AD-7 (MCP body carries no metric logic).
- **Mode:** ATTENDED (backend boundary event — one of the five § 2.5 attended events).
- **Gating question:** **Q3** (Vizro-AI LLM backend) — § 11 default adopted: route through repo model-backend configuration; defining the `_http.py`-analog LLM routing chain is the real work; bounds: no litellm (py3.14 floor), copilot-api bridge ineligible, llama.cpp/ollama/mlx-lm in-env.
- **Verify gate:** `bsl-metric-check` (existing; NL path verified at the attended event).
- **Depends on:** D1, D2.

### Implementation notes

<!-- DERIVED 2026-07-27 by reading the shipped code (PR #88). No original dev-session
     notes existed for this story; this is what the merged implementation actually does. -->

**A thin tool over a seam (AD-7).** The `query_vizro_ai` MCP tool body does nothing but
delegate to the `pyforge.atlas.nl` subpackage. All NL/LLM logic — backend resolution and
BSL grounding — lives in the seam, so the tool stays a passthrough. The gate asserts this
thinness rather than trusting it.

**No hardcoded endpoint, ever (Q3 §11 — binding).** `nl/backend.py` resolves the LLM
endpoint **only** from repo model-backend environment configuration
(`OPENAI_BASE_URL`/`OPENAI_API_KEY` or the `ANTHROPIC_*` pair). Two details make this
robust rather than merely stated:
- **A partial config degrades to unconfigured.** Both a base URL *and* a key are required.
  A half-configured backend never falls back to a guessed or public default.
- **The gate AST-scans for host-bearing URL literals** in `backend.py` and `query.py`. You
  cannot bake an endpoint in without failing the build.

**The unconfigured path is a designed behavior, not an error path.** With no backend
configured — the in-container default — the tool returns a **structured
"backend not configured — attended Q3 bring-up (DW-D3)" advisory**: no network, no crash,
no fabricated chart. Sockets are blocked in the gate to prove the no-network claim.

**Grounding, not free-form prompting.** The NL context is built from the D1 BSL models
(`build_bsl_context`, `bsl_model_names`), so the natural-language surface answers in terms
of declared metrics rather than inventing its own (AD-8).

**A version reality shaped the seam.** `from vizro_ai import VizroAI` does not resolve in
the pinned 0.4.1 — only `vizro_ai.agents.chart_agent`, a pydantic-ai Agent that needs a
backend. So the live entrypoint is discovered and imported **lazily and guarded** inside
`nl/query.py`, and only `nl/` may import `vizro_ai` at all (AD-1). `query_vizro_ai` returns
`chart=None` on both paths today.

**Two deferrals, both recorded.** The live NL→chart invocation is the attended Q3 backend
event (DW-D3-1); the dashboard's NL query field is DW-D3-2, and the `nl/` seam was kept
deliberately UI-agnostic so the dashboard can reuse it unchanged. Do not weaken
`vizro-ai-dryrun` to execute unattended, and do not bake in a public endpoint to make the
deferral go away.

### References

- [Source: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md#Story-D3]
- [Source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md#§9-Story-D3]
- [Architecture: _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md]

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Delivery Record

<!-- DERIVED from the merged PR via `gh` on 2026-07-27. Exact, not reconstructed. -->

| | |
|---|---|
| Pull request | **#88** — story(D3): Vizro-AI NL interface + query_vizro_ai MCP tool (FR-9) |
| Merged | 2026-07-18 |
| Diff | 12 files, +678 / -0 |
| Test files touched | 4 |

**Commits**

- `d58a4bd` story(D3): Vizro-AI NL interface + query_vizro_ai MCP tool (FR-9)

**File list** *(exact, from the merged diff)*

```
  336 +     0 -  src/shared/packages/pyforge-atlas/tests/nl/test_query_vizro_ai_dryrun.py
  127 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/nl/query.py
   99 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/nl/backend.py
   46 +     0 -  src/shared/packages/pyforge-atlas/tests/catalog/test_no_inline_io.py
   32 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/nl/__init__.py
   14 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/tools.py
    8 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/server.py
    6 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/audit.py
    5 +     0 -  pixi.toml
    3 +     0 -  src/shared/packages/pyforge-atlas/tests/mcp/test_no_business_logic_in_tool_bodies.py
    2 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/__init__.py
    0 +     0 -  src/shared/packages/pyforge-atlas/tests/nl/__init__.py
```

## Dev Agent Record

### Agent Model Used

In-session BMAD agent loop (draft → 2× adversarial review → 1× independent fresh-eyes review → real-gate verify), not a `bmad-dev-story` story-file run.

### Completion Notes List

- **Impl commit `d58a4bd`** — story(D3): Vizro-AI NL interface + query_vizro_ai MCP tool (FR-9)
  - Adds the natural-language read surface over the BSL knowledge graph as an MCP
  - tool callable from Claude Code, with the LLM backend routed through repo
  - model-backend configuration (Q3 §11 — never a hardcoded public endpoint).
  - - nl/backend.py -- the backend RESOLVER: reads the LLM endpoint + key ONLY from
  - repo model-backend env config (OPENAI_BASE_URL/OPENAI_API_KEY or
  - ANTHROPIC_BASE_URL/key, OpenAI-compatible bridge convention per
  - docs/copilot-to-api.md). NO literal provider host anywhere; a provider is
  - "configured" only when its base-url is a well-formed host-bearing http(s) URL
  - AND its key is non-empty. Anything else (unset/partial/malformed) resolves to
  - None so the caller degrades to a structured advisory rather than routing.
  - - nl/query.py -- the NL seam: BSL-grounded context (D1 semantic models/metrics,
  - AD-8, never raw SQL) + the DEFERRED vizro_ai call (lazy, guarded import — the
  - live NL->chart invocation is the attended Q3 event, DW-D3). The in-container
  - default (no backend) returns a "backend not configured" advisory: no network,
  - no live LLM, no fabricated chart.
  - - mcp/tools.py -- the query_vizro_ai tool body is AD-7-thin: a single delegation
  - to the nl/ seam (the _nl call-root allowance mirrors the existing _session
  - seam; the AST gate still rejects every other root). Registered in server.py +
  - recorded in the audit mapping.
  - - vizro-ai-dryrun gate (tests/nl): the tool is registered+callable; the
  - unconfigured path degrades with no socket; the resolver carries NO host-bearing
  - URL literal (AST scan over BOTH backend.py and query.py); the tool stays thin;
  - the NL context is grounded in the BSL layer.
  - - AD-1/AD-6 import-ban: only nl/ imports vizro_ai (lazy, in query.py); AST guard
  - extended in tests/catalog/test_no_inline_io.py.
  - Reviewer fixes applied: the strong "no host-bearing URL literal" AST scan now
  - covers query.py too, not just backend.py (Reviewer-A NIT); a scheme-only /
  - hostless base-url (http://, http://<spaces>, ftp://host) is now rejected as
  - unconfigured instead of handing out a false "configured" receipt that would only
  - fail at the attended Q3 call (Reviewer-B finding 1) + a 5-case regression.
  - ATTENDED scope: the live LLM backend + Vizro-AI NL->chart invocation and the
  - in-dashboard NL field are DEFERRED to the attended Q3 event (deferred-work.md
  - DW-D3-1/-2); the dryrun gate is never weakened to call a live endpoint (NFR-12).
  - 578 passed (+28 new).

## Review Triage Log

No separate review-fix commit; findings (if any) folded into the impl commit. Full review threads on PR `#88`.

## Dev narrative — recovered from the merged record

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #88: story(D3): Vizro-AI NL interface + query_vizro_ai MCP tool (FR-9)

## Deferred Work (DW ledger)

### DW-D3-1 — the live Vizro-AI NL→chart backend bring-up (ATTENDED, Q3) — DEFERRED to the wave-boundary event
- source_spec: `d3-vizro-ai-nl-interface-query-vizro-ai-mcp-tool.md`
  summary: D3 shipped the buildable-now half — the thin `query_vizro_ai` MCP tool (AD-7), the `pyforge.atlas.nl` seam (backend resolver + BSL-grounded context), its registration (tools.py + server.py + audit.NL_INTERFACE_TOOLS + the mcp package export), and the `vizro-ai-dryrun` gate — all offline with NO live LLM call. The actual live Vizro-AI NL→chart invocation is the **attended Q3 backend event**: it happens only once a model backend is configured through repo model-backend config (`OPENAI_BASE_URL`+`OPENAI_API_KEY` or `ANTHROPIC_BASE_URL`+`ANTHROPIC_API_KEY` — Q3 §11 default, BINDING; never a hardcoded public endpoint). In-container with no backend configured the tool returns a structured `backend-not-configured` advisory; with a backend configured it returns a `backend-configured-live-call-deferred` receipt naming the repo-config endpoint but STILL makes no live call. At the event: configure the backend env, instantiate the Vizro-AI NL agent against the resolved backend + the BSL-grounded context (`build_bsl_context`), invoke NL→chart, and replace the deferred receipt's `chart: None` with the generated chart/insight. The `vizro_ai` top-level `VizroAI` entrypoint is absent in the pinned 0.4.1 (only `vizro_ai.agents.chart_agent`, a pydantic-ai Agent needing a backend), so the live-entrypoint wiring is finalized at the event; the import stays lazy+guarded in `nl/query.py` (AD-1: only `nl/` imports `vizro_ai`). Do NOT weaken the `vizro-ai-dryrun` gate to unattended-execute, and do NOT bake a public endpoint in (NFR-12 / Q3 §11).
  evidence: `tests/nl/test_query_vizro_ai_dryrun.py` proves the tool is registered + callable, the unconfigured path returns the advisory with no network (sockets blocked), a configured `OPENAI_BASE_URL` is the endpoint used, no host-bearing URL literal exists in the resolver (Q3 §11), the tool body is AD-7-thin, and the NL context is BSL-grounded (AD-8). `nl/query.py::query_vizro_ai` returns `chart=None` in both paths; `vizro_ai_available()` is a guarded probe. Mirrors the C1 dagster-schedule bring-up (DW-C1-1) and the B5/B7/B8 injected-fetcher deferrals.

### DW-D3-2 — the dashboard NL query field (the D2 Vizro dashboard's NL entry point) — DEFERRED (carries DW-D3-1 + the CIS spine)
- source_spec: `d3-vizro-ai-nl-interface-query-vizro-ai-mcp-tool.md`
  summary: D3 delivers the NL interface as an MCP tool (`query_vizro_ai`) — the agent-facing surface. The other NL surface, a natural-language query FIELD embedded in the D2 Vizro dashboard (a user types a question on a page and gets a generated chart), is DEFERRED: it depends on the live Vizro-AI backend (DW-D3-1) AND on the CIS two-spine design specs that gate the dashboard's page design (DW-D2-1). When both land, add the NL field as a dashboard component that calls the same `pyforge.atlas.nl` seam (so the MCP tool and the dashboard field share one backend-routing + BSL-grounding path, never a second execution plane — AD-23). Until then the dashboard ships without an NL field.
  evidence: D3's shipped surface is the MCP tool only (`server.py` `query_vizro_ai` @mcp.tool + `tools.query_vizro_ai`); `dashboard/app.py` is unchanged by D3 (no NL component added). The shared seam (`pyforge.atlas.nl`) is deliberately UI-agnostic so the dashboard field can reuse it at the event.

### DW-D3-1 — the live LLM backend + Vizro-AI NL invocation (ATTENDED, Q3) — DEFERRED
- source_spec: `d3-integrate-vizro-ai-nl-interface-mcp-tool.md`
  summary: D3 shipped the offline-buildable half: the thin `query_vizro_ai` MCP tool (AD-7 — delegates to the `nl/` seam), the backend-config RESOLVER that reads the LLM endpoint ONLY from repo model-backend env config (OPENAI_BASE_URL/OPENAI_API_KEY or ANTHROPIC_BASE_URL/key — Q3 §11, never a hardcoded public endpoint), the BSL-grounded NL context (D1 semantic models/metrics, AD-8), and the structured "backend not configured" advisory that the in-container default returns (no network, no live LLM, no fabricated chart). The ACTUAL live NL→chart invocation — instantiating Vizro-AI against a configured backend and returning a generated chart/insight — is the attended Q3 bring-up: configure the repo model-backend (a local OpenAI-compatible bridge per docs/copilot-to-api.md), then the deferred code path (guarded, lazy `import vizro_ai` in `nl/query.py`) runs. Do NOT wire a public endpoint or weaken the "no host-bearing URL literal" gate (NFR-12 / Q3).
  evidence: `vizro-ai-dryrun` gate asserts the tool is registered+callable, the unconfigured path degrades with no socket, the resolver reads from env + carries NO host-bearing URL literal (AST scan over backend.py AND query.py), and the tool body stays AD-7-thin. `from vizro_ai import VizroAI` does not resolve in this version — the live entrypoint is discovered + imported lazily at the attended event.

### DW-D3-2 — the Vizro-AI NL query FIELD in the dashboard UI — DEFERRED (DEV-AUTO / with D2)
- source_spec: `d3-integrate-vizro-ai-nl-interface-mcp-tool.md`
  summary: D3 delivers the NL surface as an MCP tool (callable from Claude Code). Surfacing the same NL query as an interactive FIELD in the D2 Vizro dashboard is deferred with the D2 CIS-two-spine page work (DW-D2-1) + its live LLM backend (DW-D3-1) — it needs both the rendered dashboard breadth and a configured backend, and the visual verification is the DEV-AUTO pass D2 defers.
  evidence: D3 AC "a Vizro-AI natural-language query field AND a query_vizro_ai MCP tool"; the MCP tool is shipped, the in-UI field rides on D2's deferred CIS-spine dashboard breadth.
