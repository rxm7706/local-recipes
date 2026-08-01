# Narration script — Deckcraft

> Extracted from `Deckcraft.dc.html` speaker notes (regenerable — do not hand-edit; edit the deck's `data-speaker-notes` in Design and re-extract). 10 scenes.

## Scene 01 — Cover

One line: deckcraft turns a prompt or a document into an editable PowerPoint deck, built from conda-forge primitives rather than by repackaging someone's SaaS, and running with zero outbound calls by default. It is the PyForge deck family's designated editable-PPTX engine — the 2026-07-23 export revisit named it, because marp --pptx renders image-slides that nobody can edit. Spec'd, not started: 6 epics, 28 stories, 0 shipped.

## Scene 02 — Act I — The last mile

Act I: the AI writes the prose and then drops the user before the file exists. The gap is small per deck and invisible in aggregate — it shows up as 'AI doesn't really help with slides' rather than as a fixable plumbing gap.

## Scene 03 — Three people, one gap

Three concrete scenarios drive the product. The engineer with Claude Code and Copilot open who still pastes into PowerPoint for thirty to sixty minutes a deck. The air-gapped colleague who has Copilot and M365 but cannot reach any public AI API, so cloud tools are unusable by policy. And the technical author, for whom every tool rasterizes the diagram — editability is the thing everyone claims and almost nobody delivers.

## Scene 04 — Never rasterized

The non-negotiable, and it is machine-checkable, not a marketing adjective. SC-05: one hundred percent of text, shapes, charts and diagrams in the generated pptx are native DrawingML, zero rasterized content, verified by automated structural inspection of the file itself. Every pptx also ships a Marp markdown sibling you can hand-edit and re-render — and the round-trip flags lossy elements in a sidecar warning file rather than silently dropping them.

## Scene 05 — Act II — From primitives

Act II: the build. Deckcraft is not a wrapped web app — it is a small layered Python package over conda-forge primitives, with exactly three designed swap points, surfaced through every assistant the user already has.

## Scene 06 — Three swap points

The architecture in one slide. Surfaces consume the Pipeline API only; renderers consume engine adapters only. Three swap points and nothing else is a designed swap point: the LLM adapter, the pptx engine adapter, the platform adapter. Each one is the escape hatch for a known fragility — provider variability, python-pptx's dormancy, per-platform path and GPU differences. The pptx-engine-only rule is the discipline that keeps the vendor fallback clean: nothing outside deckcraft.engines.pptx_engine may import pptx at all.

## Scene 07 — Act III — The honest ledger

Act III: what the 2026-07-25 research pass found, blockers included. Two findings landed: the moat moved, and a license landmine was sitting in an already-pinned dependency. Neither is hidden here — a never-false-green house cannot false-green its own plan.

## Scene 08 — The moat moved

ppt-master was a minor Option C in the intake gist. Since then it has grown to forty-one thousand stars and three and a half thousand forks in under eight months, it is genuinely MIT, and it compiles constrained SVG into DrawingML — meeting or exceeding deckcraft's own editability bar. What it does not have is any documented local-LLM-first or offline mode: it depends on a cloud-hosted coding-agent model and recommends cloud models specifically for quality. So editability and from-primitives are no longer uniquely ours. Air-gap is — and it is the one claim we enforce in CI, under unshare -n.

## Scene 09 — The blocker on the desk

The unresolved item, stated plainly. pymupdf is the pinned primary library for PDF style extraction, and PyPI's own metadata says it is dual-licensed AGPL-3.0 or Artifex commercial. Deckcraft's founding acceptance criterion is MIT or Apache-2.0 only — that constraint is the reason the project exists at all, since its predecessor tool was rejected for being proprietary. AGPL is not proprietary, but many regulated organizations treat it as equally blocking to embed. Three named options, none chosen: accept it for this one opt-in path with documented rationale; substitute pdfplumber, already in the environment, MIT-family and requester-maintained, at a documented quality cost; or scope the OCR-fallback depth out. It is a human license call, it blocks before Story 3.2, and the risk is silence, not difficulty.

## Scene 10 — The family's engine

Close on the first consumer. The 2026-07-23 export revisit designated deckcraft the editable-PPTX engine for the deck family's Standard export set, because marp --pptx renders each slide as an image — fine for distribution, useless for editing. Until deckcraft lands, every family PPTX is an interim artifact. The master switch is dogfooding: one real ship-quality deck a week for four consecutive weeks, or the kill criteria fire.
