---
title: "Video content — the factory films its own documentation"
type: "spec"
owner_dream: "video-scripts"
capabilities: 5
constraints: 8
date_created: "2026-08-04"
status: "draft"
---

# SPEC: Video content — the factory films its own documentation

## Why

Every Dream that ships should be able to announce itself in video — marketing, demo, and content pieces — with the same zero-manual-transfer discipline the deck bridge already has. The factory's first-class, regenerable video pipeline enables creators to produce polished motion-graphics-rich content in their own voice, never an LLM's.

## Capabilities

1. **Braindump scripting** — Convert raw spoken ideas into polished scripts via `mc-braindump`, preserving the creator's exact voice and speech patterns.

2. **Multi-modal content assembly** — Orchestrate real footage (VODs, talks, screen recordings) with HyperFrames motion graphics, Kokoro-82M narration, and brand-themed alpha overlays into a unified video.

3. **Production automation** — A full pipeline (`bmad-manticore`) that takes raw inputs and distills them into a finished video artifact with cut plans, graphics beats, and delivery formats (talking-head, screen-tutorial, voiceover-explainer, short).

4. **Voice & production consistency** — Codify creator identity via Voice Bible (speech patterns, measured WPM), Production Bible (brand tokens, motion feel, CTA policy), and enforced Blacklist (LLM tells the script linter catches).

5. **Local-first rendering** — All media (motion graphics, narration, SFX, B-roll) sourced from approved local/internal sources or gate-approved external feeds; never synthetic UI renders.

## Constraints

1. **No synthetic UI renders** — Screen content must be real recordings (with annotations) or approved mockups; AI-generated UI renders as convincing-at-a-glance gibberish and violates the anti-vibe doctrine.

2. **Real speech preservation** — Narration must respect the creator's or measured voice profile; no generic LLM voice substitution.

3. **Gate-approved media only** — All sources (B-roll, music, SFX, graphics libraries) must pass factory gate review before assembly.

4. **Braindump fidelity** — The script linter must enforce that the final script preserves substantive content from the creator's braindump input; no rewriting for "clarity."

5. **Format-specific rules** — Each format profile (talking-head, screen-tutorial, etc.) carries its own density, pacing, and effect constraints; the pipeline enforces these.

6. **Regenerable-first** — All artifacts (scripts, cut plans, graphics beats, final video) must be reproducible from source inputs and configuration; no manual edits become permanent without being versioned back into the source.

7. **Conductor role** — `bmad-manticore` is the orchestrator only; it does not create raw content (it cannot do the braindump, shoot the footage, or record narration). The creator provides inputs; manticore stages them.

8. **Local toolchain** — Rendering, encoding, and final output must run locally (not cloud-dependent) to preserve privacy and control.

## Non-Goals

- Creating raw content for the creator (braindump scripts, footage, narration must exist or be provided).
- Replacing human creativity or aesthetic judgment; the pipeline is mechanical orchestration, not artistic direction.
- Building a general-purpose video platform; this is purpose-built for the factory's Dream announcements.
- Supporting arbitrary video formats or codecs beyond the defined profiles.

## Success Signal

- First factory Dream's video announcement is published via the pipeline (end-to-end, including braindump→script→video).
- All artifacts (script, cut plan, graphics beats, final video) are regenerable from source inputs without manual intervention.
- Creator can reproduce the video with a config update + pipeline re-run.
- The result is polished and on-brand (no synthetic UI, consistent voice, factory-identity motion graphics).

## Companions

- **Video Bible** (`video-scripts/production-bible.yaml`): Brand tokens, motion feel, CTA policy, format profiles.
- **Voice Bible** (`video-scripts/voice-bible.md`): Speech patterns, measured WPM, tone directives.
- **Blacklist** (`video-scripts/llm-tells-blacklist.txt`): Script linter rules.
- **`bmad-manticore` integration spec** (TBD): Detailed hand-off protocol between the factory and manticore CLI/MCP layer.

---

*This spec was distilled from docs/dreams/video-scripts.md (status: dreamt, owner: herald). Promote to ready after Dream reaches "specified" status and design + UX sections are authored.*
