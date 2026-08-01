---
title: Video content — the factory films its own documentation
type: dream
owner: herald
status: dreamt
---

# Video content — the factory films its own documentation

## The Dream

Every Dream that ships should be able to **announce itself in video** —
marketing, demo, and content pieces — with the same zero-manual-transfer
discipline the deck bridge already has. The instrument is **`bmad-manticore`**
(the AI video production pipeline, 16 `mc-*` skills, conda-packaged here),
acting as director and editor: it takes raw spoken ideas, real footage, and
brand guidelines, and assembles, cuts, and packages a finished,
motion-graphics-rich video — in the creator's own voice, never an LLM's.

This is bigger than scripts. Manticore feeds on **three classes of content**,
and the Dream is that this factory produces all three as first-class,
regenerable artifacts:

1. **Raw inputs** — a spoken *brain dump* (`mc-braindump` weaves a script from
   the speaker's exact words); existing footage (VODs, talks, A-roll) via
   footage-first mode and a word-level cut plan; and **real screen
   recordings** for anything showing a UI — because *AI-generated UI renders
   as convincing-at-a-glance gibberish*. That standing rule is our own
   anti-vibe doctrine wearing a headset.
2. **Taste & identity** — a *Voice Bible* deconstructed from published
   transcripts (measured WPM, real speech patterns); a *Production Bible* with
   brand tokens, motion feel, density and CTA policy; a *Blacklist* of LLM
   tells the script linter enforces; and *format profiles* (talking-head,
   screen-tutorial, voiceover-explainer, short).
3. **Orchestrated media** — HyperFrames motion graphics rendered locally
   (brand-themed alpha overlays, kinetic captions, device mockups); local
   audio lanes (Kokoro-82M narration, MusicGen beds, AudioLDM2 SFX); and
   b-roll farmed only from approved sources.

Local-first, gate-approved (Outline → Cut Plan → Graphics Beats → Final
Render — four hard stops), and honest by construction: no fabricated product
demos, ever.

## What is real (seeded 2026-07-31)

- **The narration corpus** — 27 `*-narration-2026-07-31.md` files, **322
  scenes**, extracted mechanically from every deck prototype's speaker notes.
  Regenerable: edit the notes in Design, re-extract; never hand-edit.
- **The first master script** —
  `presentations/pyforge-marshal/src/marp/pyforge-ecosystem-master-script-2026-07-31.md`:
  22 scene/visual/voiceover triples interleaving the Charter story, the
  Marshal narration, and the infographic fact base.
- **The consumer** — `bmad-manticore` 2.0.0 installed and packaged
  (`recipes/bmad-manticore/`); marp trios and infographic standalones supply
  visual pulls; the deck families supply real-screen source material.
- **The operator intake** — the drafted five-field kernel, companion-config
  list, and Production Bible template are preserved verbatim as the Spec's
  input:
  `_bmad-output/projects/pyforge-herald/planning-artifacts/intake-video-scripts-manticore-2026-07-31.md`.

## The frontier

- **The studio, configured** — `mc-setup` materializes the identity:
  `_bmad/custom/config.toml` (tool lanes: audio → Kokoro-82M, graphics →
  HyperFrames) and `manticore/brand/` (production-bible, voice-bible,
  blacklist, fonts) — carrying the **Modernist tokens** (Archivo, the
  red/off-white/near-black palette), not the template's placeholders, so
  videos and decks are one brand.
- **The voice, captured** — the Voice Bible built from the operator's actual
  published transcripts; the Blacklist seeded and enforced by the script
  linter, so the output sounds like a person, not a model.
- **Real screens, recorded** — a library of genuine screen recordings of the
  factory's own surfaces (the console, `marshal` sessions, the Guildhall
  board), because demos of this factory must obey its own authenticity rule.
- **The handoff proven** — one video end-to-end: master script + screen
  recordings + bibles → `mc-new` → script, `edl.json` cut plan, HyperFrames
  over real UI → incremental render + FCPXML/EDL + `.mp4`, run recorded in the
  deck README ledger. Until then this Dream ships inputs, not claims.
- **Extraction as a factory task** — `narration-extract` as a pixi task with a
  staleness detector: a deck whose Design etag moved after its narration's
  date is a finding, not a surprise.
- **A master script per station** — each deck family gains the fourth derived
  class; the Marshal exemplar sets the shape. The artifact-tree map in
  `docs/specs/presentation-deck.md` gains the narration + master-script
  branches so the READ-BEFORE-EDITING map stays complete.

## What this is not

Not a new deck class — deck families and propagation paths are untouched
([[design-code-bridge]]). Not manticore itself — the pipeline is upstream
bmad-code-org craft; this Dream feeds and configures it. **Not an NLE
replacement** — when the auto-render isn't used, the deliverable is the
`edl.json`/FCPXML and assets, finished in Resolve or Premiere. **Not live
streaming** — recorded marketing and demo video only. **Not fabricated
demos** — no AI-generated UI, no fictional product footage, no exceptions.
And not Scribe's memory: video tells the *world*, in Herald's voice
([[pyforge-herald]]).

## Kinships

[[pyforge-herald]] (the owning station — proclaim the release) ·
[[design-code-bridge]] (the same zero-manual-transfer discipline, applied to
video) · [[pyforge-marshal]] (the ecosystem master script's subject; anti-vibe
is the same law both obey) · [[pyforge-charter]] (the story every script
retells) · [[modernist-identity]] (one brand across decks and video).

## Realization log

- **2026-07-31** — Dream seeded on an operator call ("I want more content that
  manticore can use — create this artifact class"). Same session: the
  322-scene narration corpus extracted fleet-wide; the first master script (22
  scenes) authored as the class exemplar.
- **2026-07-31 (later)** — **Dream expanded from scripts-only to the full
  manticore content-supply model** on operator briefing: the three content
  classes, the taste/identity files, the orchestrated-media lanes, the four
  approval gates, and the authenticity constraints. The operator's five-field
  draft and Production Bible template preserved verbatim as the Spec's intake
  (path above) — the future `bmad-spec` run derives from the operator's own
  words. Chain status: dreamt — this Dream sits in `dream-chain-check`'s INV-1
  backlog (owner herald) by design; `spec-video-scripts` is the deferred work.
