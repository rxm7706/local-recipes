---
title: "Plan Validation Notes: deckcraft, 2026-07-25"
project: deckcraft
date: 2026-07-25
status: notes-only
purpose: >
  Research-first backfill for deckcraft (PRD/architecture/epics authored 2026-05-09,
  before this repo's research-first convention existed). Cross-checks the two
  companion reports (technical-research-toolchain, domain-research-comparables)
  against specific FR/AD/story IDs. NOTES ONLY — does not edit the PRD, architecture,
  or epics. For the operator and the future build line to apply at story-kickoff.
sources:
  - "research/technical-research-toolchain-2026-07-25.md"
  - "research/domain-research-comparables-2026-07-25.md"
---

# Plan Validation Notes — deckcraft (2026-07-25)

Implementation has not started (`apps/deckcraft/`, `recipes/deckcraft/` don't exist; `sprint-status.md` / `implementation-artifacts/` show 0/28 stories). This is a pre-build validation pass, not a retrospective.

## Verdict summary

| # | Finding | Verdict | Affects |
|---|---|---|---|
| 1 | `python-pptx` dormancy (last release 2024-08-07, MIT, 534 open issues) | **CONFIRMED**, and worse than described (23 months quiet, growing issue backlog) | FR-15, AD-07 |
| 2 | `pymupdf` is AGPL-3.0/commercial dual-licensed, not MIT/Apache | **CONTRADICTS** the project's founding license constraint (unflagged until now) | FR-46c, AD-13, S-3.2 |
| 3 | `fastmcp` PRD citation says "v3.2.4"; current is 3.4.4 (pixi.toml already correct) | **DATED** prose only — no build/architecture impact | PRD prose line 230 |
| 4 | All other pinned deps (markitdown, pydantic-ai, mermaid-py, diffusers, sentence-transformers, mlx-lm, llama.cpp) | **CONFIRMED** current, actively maintained, correctly licensed | FR-01–FR-44 broadly |
| 5 | `litellm` conda-forge feedstock pydantic-pin conflict | **CONFIRMED still unresolved** — deferral decision stands | Open Question (deferred, no AD number) |
| 6 | Design-tokens ↔ POTX pipeline ("found asset" in Sentinel Design project) | **UNVERIFIED** — no library precedent exists (confirms it's bespoke); actual scripts not pulled/audited this pass | Dream cross-reference only, no FR/AD yet |
| 7 | `Office-PowerPoint-MCP-Server` (intake gist's top OSS pick) | **DATED** — archived 2025-12-31; no longer a live precedent | Intake gist context only, no FR/AD |
| 8 | `hugohe3/ppt-master` (intake gist's minor "Option C") | **DATED, materially so** — grown to 41k+ stars, now the dominant open comparable; matches or exceeds deckcraft's own editability bar | Differentiation framing in product-brief-deckcraft.md § "What Makes This Different"; no FR/AD contradicted (deckcraft's FRs describe deckcraft's own behavior, not a competitive claim) |
| 9 | `presenton`'s README now claims "fully editable PPTX export" + Ollama/LM Studio support | **POSSIBLY DATED, unverified** — narrows the editability gap the product brief used to justify deckcraft as a separate effort; needs re-verification against `presenton-pixi-image`'s own findings, not asserted as resolved here | Differentiation framing only |
| 10 | Air-gap posture (DR-01/NFR-08/NFR-11) vs. all four comparables | **CONFIRMED as deckcraft's sharpest remaining differentiator** — none of the four comparables (ppt-master, presenton fully, Gamma-class SaaS, archived Office-PowerPoint-MCP-Server) match a CI-enforced, default-offline, local-LLM-first posture the way deckcraft's architecture specifies it | DR-01, NFR-08, NFR-11, AD-15 |

## Detail

### Finding 2 is the one action item before implementation touches it

`pymupdf` is pinned in `pixi.toml` (`>=1.28.0`) and named explicitly in `architecture.md` AD-13 (the PDF style-extraction decision tree) as the primary extraction library for FR-46c. PyPI's own license metadata states: *"Dual Licensed - GNU AFFERO GPL 3.0 or Artifex Commercial License."* Neither the PRD, architecture, nor pixi.toml's inline comment flags this. The project's own founding document — `docs/intake/gists/open-source-powerpoint-agent-skills/Open-Source_PowerPoint_Agent_Skills.md` § 4 — states the acceptance bar as *"must contain exactly zero proprietary code (must be MIT or Apache 2.0)."* AGPL isn't proprietary, but it's a copyleft license many air-gapped/regulated organizations (deckcraft's own secondary user segment) treat as equally blocking to embed in a distributed tool.

**This does not require a PRD/architecture edit right now** (out of scope for this research-only pass) but should be resolved explicitly before **Story 3.2** (PDF style loader, Sprint 4) starts. Options: accept AGPL for this one opt-in capability path with documented rationale; substitute `pdfplumber` (already in the env, MIT-family, requester-maintained) with a documented quality trade-off; or scope out FR-46c's OCR-fallback depth. Any of the three is a small decision — the risk is silence, not difficulty.

### Finding 8/9/10 together: the differentiation narrative should be refreshed, not the architecture

None of the competitive findings touch a locked technical decision (A-01 through A-04, AD-01 through AD-15, P-01 through P-10 all stand unchallenged). What they touch is the *narrative* in `product-brief-deckcraft.md` § "What Makes This Different" and the PRD's Innovation Analysis — both of which predate `ppt-master`'s existence as a major project (it was created 2025-12-10, a month before the brief, but its growth to 41k stars is entirely post-authoring). The domain-research companion report's synthesis table shows deckcraft's air-gap claim (DR-01) is now carrying more of the differentiation weight than the brief assumed; editability and from-primitives are no longer uniquely deckcraft's. Recommend refreshing the comparison table at the next natural touch-point to the brief/PRD (not urgent enough to warrant an out-of-cycle edit), and keeping the air-gap CI test (NFR-08, `tests/air_gapped/test_offline.py`) as a non-negotiable V1 deliverable — it is now doing double duty as both a functional requirement and the project's primary competitive moat.

### Finding 6: verify before assuming, don't block on it

The tokens-to-potx/potx-to-tokens pipeline referenced in `docs/dreams/deckcraft.md` and `docs/dreams/modernist-identity.md` lives in an external Claude Design project (Sentinel) with no source checked into this repo. This research confirmed there's no existing open-source library filling this niche (a `gh search repos` sweep for design-tokens/PowerPoint-theme tooling returned zero results), which means the general *technique* is sound (OOXML `theme1.xml` is directly addressable via `lxml`, already a pixi dependency) but the specific *found asset*'s maturity is unverified. No story currently depends on it (it isn't referenced in epics.md's FR/AD coverage), so this is a watch item for whenever a future story picks it up, not a blocker for the current 28-story plan.

## Open questions this research does NOT resolve

- Whether `pymupdf`'s AGPL license is acceptable for deckcraft's own eventual license choice (still open per PRD's own "S-01" note on MIT vs Apache-2.0) — a human call, not a research finding.
- Whether presenton's "fully editable PPTX" README claim reflects real structural quality — needs hands-on verification (generate a deck, inspect the XML), which is `presenton-pixi-image` project's job, not deckcraft's.
- Whether the Sentinel tokens-to-potx pipeline is worth pulling into deckcraft's `style_loader` scope now or later — needs the actual scripts read via the `claude-design` MCP tools, which this session's scope (no live MCP browsing performed) did not do.
