# Integration layers — instrument matrix and pipeline diagram

Companion to `SPEC.md` (spec: marshal-token-economy). One row per layer; each attacks a
different sink and they compose because they operate at different points of the pipeline.

## Layer matrix

| Layer | Instrument (recipe) | Version / license | Sink attacked | Mechanism | Availability gate |
|---|---|---|---|---|---|
| 0 — output compression | `recipes/caveman/` | 2.4.0, MIT (installer only) | Agent's own output (weighted heaviest) | Claude Code skill deployed per loop home by Genesis; ~65% output cut; upstream input proxy (`@caveman-ai/cli`) is BSL-1.1 and excluded | **Active in pixi since 2026-08-30** (patched SelfExplainML build 2, host nodejs held at 24.* to coexist with codegraph), **linux-64 only** — degrade gracefully elsewhere |
| 1 — wire compression | `recipes/headroom-ai/` | 0.37.0 via conda-forge (recipe 0.32.1), Apache-2.0 | Tool outputs, logs, file reads, diffs (40–95%) | `headroom wrap <cli>` / transparent proxy at the harness seam; reversible CCR store scoped to the loop home; live-zone-only so the provider cache hot zone stays byte-identical | **Active in pixi since 2026-08-30, all platforms** (the `conda-recipe-manager==8.2.1` click-pin chain fell when crm+feedrattler moved to the grayskull-only `crm` feature) |
| 2 — structure graph | `recipes/codegraph/` | 1.6.0, MIT | Codebase re-exploration per session | Pre-indexed local code knowledge graph, synced on change, agent integrations wired at loop-home provisioning | Active in pixi, **linux-64 only** — policy must degrade gracefully |
| 3 — incremental derived context | `recipes/cocoindex/` | 1.0.20, Apache-2.0 (on conda-forge) | Epic-context / continuity recompute churn and staleness | Derived artifacts recomputed only when planning sources change | Active in pixi |
| 4 — planning graph | `recipes/graphifyy/` | 0.9.44, MIT | Full-document planning loads (`epics.md` ~65k tok, `prd.md` ~46k tok) | Queryable graph over the planning corpus, consumed via the **Scribe-owned GraphStore seam**; fallback to epic-context files | Active in pixi; seam ownership is Scribe's |

Bonus (out of this spec's scope, noted for operators): `recipes/rtk/` shrinks
`git`/`ls`/shell output at the terminal level.

## Pipeline diagram

```
                    ┌─ Layer 4: graphifyy ── planning-artifacts as a queryable
                    │            graph: retrieve the ~1.5k tokens a story needs,
                    │            never load epics.md / prd.md wholesale
                    │
  bmad-build-auto ──┤─ Layer 3: cocoindex ── epic-context / continuity distills
     (per story)    │            recomputed ONLY when sources change
                    │
                    ├─ Layer 2: codegraph ── structure questions answered from
                    │            the pre-built graph, not file re-reads
                    │
  coding CLI  ──────┼─ Layer 1: headroom ─── every tool output / log / diff
  (claude/copilot)  │            compressed 40–95%, reversible via CCR
                    │
                    └─ Layer 0: caveman ──── the agent's own output stripped
                                 ~65%, heaviest-weighted tokens
  marshal ──────────── policy renders it (CAP-1), Genesis seeds it (CAP-3/4),
                       supervisor meters it (CAP-7) and escalates it (CAP-8)
```

## Marshal seams touched (where each CAP lands)

| CAP | Seam |
|---|---|
| CAP-1 | `core/policy.py` (`EffectivePolicy` + `render_policy_toml`), `schemas/policy.json` |
| CAP-2 | `core/harness_profile.py`, `data/harness_profiles/*.toml`, spin/dispatch launch path |
| CAP-3, CAP-4 | `seed/` (Genesis apply + check), loop-home provisioning |
| CAP-5, CAP-6 | bmad-build-auto step-01 / epic-context compile (skill-side), marshal renders the flags |
| CAP-7, CAP-8 | `supervisor/` tick + `core/supervise.py`, journal kinds, `cli/status.py` rendering |
| CAP-9 | benchmark harness (new, station-owned test/tool surface) |
| CAP-10 | `cli/check.py` → detector registry (advisory findings) |
