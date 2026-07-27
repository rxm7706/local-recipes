---
title: 'Story D3 (5.3): Integrate Vizro-AI + expose the NL interface as an MCP tool'
type: 'feature'
status: 'shipped'
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

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Provenance & recovery note

Recovered 2026-07-25 as part of the spec-durability remediation (see
`planning-artifacts/specs/README.md`). Same root cause + fix as pyforge-warden: story specs
now live tracked in `planning-artifacts/specs/`, not Tier-3 gitignored `implementation-artifacts/`.

## Dev narrative — recovered from the merged record (2026-07-25)

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #88: story(D3): Vizro-AI NL interface + query_vizro_ai MCP tool (FR-9)

## Summary

Adds the natural-language read surface over the BSL knowledge graph as an MCP tool callable from Claude Code, with the LLM backend routed through **repo model-backend configuration** (Q3 §11 — **never a hardcoded public endpoint**). Final Wave-D story.

- **`nl/backend.py`** — the backend **resolver**: reads the LLM endpoint + key **only** from repo model-backend env config (`OPENAI_BASE_URL`/`OPENAI_API_KEY` or `ANTHROPIC_BASE_URL`/key, the OpenAI-compatible bridge convention per `docs/copilot-to-api.md`). **No literal provider host anywhere**; a provider is "configured" only when its base-url is a well-formed **host-bearing** http(s) URL AND its key is non-empty — anything else (unset/partial/malformed) resolves to `None` so the caller degrades to a structured advisory rather than routing.
- **`nl/query.py`** — the NL seam: **BSL-grounded** context (D1 semantic models/metrics, AD-8, never raw SQL) + the **deferred** vizro_ai call (lazy, guarded import — the live NL→chart invocation is the attended Q3 event). The in-container default (no backend) returns a "backend not configured" advisory: no network, no live LLM, no fabricated chart.
- **`mcp/tools.py`** — the `query_vizro_ai` tool body is **AD-7-thin**: a single delegation to the `nl/` seam (the `_nl` call-root allowance mirrors the existing `_session` seam; the AST gate still rejects every other root). Registered in `server.py` + the audit mapping.
- **`vizro-ai-dryrun` gate** — tool registered+callable; unconfigured path degrades with no socket; resolver carries **no host-bearing URL literal** (AST scan over **both** `backend.py` and `query.py`); tool stays thin; NL context grounded in the BSL layer.
- **AD-1/AD-6 import-ban** — only `nl/` imports vizro_ai (lazy, in `query.py`); AST guard extended.

## Reviews

Three independent reviews. Reviewer A (Q3/AD-7) clean across all four categories. Applied: the strong "no host-bearing URL literal" AST scan now covers `query.py` too (Reviewer-A NIT); a **scheme-only/hostless base-url** (`http://`, `http://<spaces>`, `ftp://host`) is now rejected as unconfigured instead of a false "configured" receipt that would only fail at the attended Q3 call (Reviewer-B finding 1) + a 5-case regression.

## Scope (honest deferral)

The **live LLM backend + Vizro-AI NL→chart invocation** and the **in-dashboard NL field** are DEFERRED to the attended Q3 event (`deferred-work.md` DW-D3-1/-2); the dryrun gate is never weakened to call a live endpoint (NFR-12).

## Tests

`578 passed` (+28 new).

### Commits on `main`

- `8cf5819284` story(D3): Vizro-AI NL interface + query_vizro_ai MCP tool (FR-9)  _(dev-landing)_

_This PR also carried an automated Gemini review; not reproduced here per repo policy ([[feedback_no_gemini_reviews]])._

