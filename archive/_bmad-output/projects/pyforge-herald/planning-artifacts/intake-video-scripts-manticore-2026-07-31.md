# Intake — video-scripts / bmad-manticore studio (operator draft, 2026-07-31)

> **Status: bmad-spec INPUT, not a Spec.** Operator-authored intent for the
> `spec-video-scripts` derivation (owner: herald; Dream:
> `docs/dreams/video-scripts.md`). Preserved near-verbatim so the derivation
> consumes the operator's own words. Do not treat the five-field draft below as
> the canonical contract — `bmad-spec` produces that, from this plus the Dream.

## Manticore's content-supply model (operator briefing)

To generate marketing, demo, and content videos, manticore needs three classes
of content:

### 1. Raw inputs (the "content")

- **A spoken "brain dump"** — talk through the video idea for twenty minutes
  (`mc-braindump`). Manticore weaves a script that uses the speaker's exact
  words, rather than sounding like an LLM.
- **Existing raw footage** — a livestream VOD, a recorded talk, standard
  A-roll. "Footage-first mode" ingests it and produces a word-level cut plan.
- **Real screen recordings (crucial for demos)** — standing rule from the
  manticore README: *"Anything showing a user interface or text that must read
  correctly comes from real screen recordings, because AI-generated UI renders
  as convincing-at-a-glance gibberish."*

### 2. The "taste" & style files (the "identity")

- **Voice Bible** — a deconstruction of how the creator actually talks, built
  by fetching past published transcripts (`yt-dlp`); includes measured
  words-per-minute and real speech patterns.
- **Production Bible & brand tokens** — visual identity: brand usage scope,
  motion feel, overlay aesthetics, image-type policies, visual density, CTA
  configuration.
- **Blacklist** — "LLM tells" and phrases the creator never says; the script
  linter enforces it.
- **Format profiles** — markdown files declaring the video kind:
  `talking-head`, `screen-tutorial`, `voiceover-explainer`, `short`.

### 3. Generated / external media (orchestrated by manticore)

- **Motion graphics & overlays** — HyperFrames, locally: brand-themed alpha
  overlays (ProRes 4444), kinetic captions, 3D device mockups.
- **Audio** — narration via Kokoro-82M; instrumental beds via MusicGen-small;
  SFX via AudioLDM2.
- **B-roll & stills** — optionally via configured CLI tools (xAI Grok, Google
  Antigravity, OpenAI Codex) for atmospheric b-roll, thumbnails, title cards.

Manticore takes the raw spoken ideas, existing video/screen recordings, and
brand guidelines, and acts as director and editor — assembling, cutting, and
packaging a finished, motion-graphics-rich video.

## Operator five-field draft (input to the Spec kernel)

### 1. WHY

- **Goal:** Configure the BMad-Manticore local studio environment and prepare
  the required content assets to automatically generate brand-aligned
  marketing and product demo videos.
- **Problem solved:** High-quality, motion-graphics-rich video normally needs
  manual timeline editing and expensive external tools. Leverage manticore's
  local pipeline (HyperFrames, Kokoro-82M, Parakeet) to convert a raw brain
  dump or existing UI screen recordings into a finalized, fully-packaged
  video.
- **Target audience:** the end-user (developer/marketer) using the module, and
  the audience of the resulting videos.

### 2. CAPABILITIES

- **Studio configuration (`mc-setup`):** define the visual identity by writing
  `_bmad/custom/config.toml`; establish the Production Bible (brand usage,
  motion feel), Voice Bible (from YT transcripts), and Blacklist (LLM tells).
- **Format profiles integration:** support standard manticore markdown formats
  — `talking-head`, `screen-tutorial` (UI only, no generated b-roll),
  `voiceover-explainer`.
- **Script & cut generation (`mc-braindump` / `mc-cut`):** ingest raw
  audio/video or a conversational interview → verbatim word-level cut plan
  (`edl.json`) + a linted script in the creator's exact words.
- **Motion graphics & b-roll (`mc-beats` / `mc-graphics`):** HyperFrames
  locally for brand-themed alpha overlays (ProRes 4444) anchored to specific
  spoken words; b-roll farmed strictly from approved local/API assets (Grok
  CLI, Antigravity CLI).
- **UI recording ingestion:** for tech demos, ingest raw `.mp4` screen
  recordings and pair with generated TTS (Kokoro-82M) or custom narration.

### 3. CONSTRAINTS

- **Local-first execution:** local processing by default (`uv`, `ffmpeg`,
  `node`, `git`); all motion graphics rendered via HyperFrames without
  external API calls unless explicitly opted into.
- **UI/demo authenticity:** no AI-generated UI. AI-generated b-roll banned for
  screen tutorials. Real screen recordings required for any interface
  walkthrough.
- **Gate approvals:** hard stops (Gates 1–4) for user approval — Outline, Cut
  Plan, Graphics Beats, Final Render.
- **File locations:** studio configs in `_bmad/custom/config.toml`; brand kits
  and bibles in `manticore/brand/` so they survive reinstalls.

### 4. NON-GOALS

- **Not an NLE replacement** — generates the `edl.json` and assets to finish
  in DaVinci Resolve / Premiere if the auto-render isn't used.
- **Not live streaming** — recorded marketing/demo video only (OBS packs out
  of this scope).
- **No fictional/fabricated product demos.**

### 5. SUCCESS SIGNAL

- `mc-new` runs and a `screen-tutorial` or `voiceover-explainer` format
  profile is selectable.
- The pipeline generates a script, a word-level cut plan, composites
  HyperFrames graphics over real UI footage, and outputs a final incremental
  render with an accompanying FCPXML/EDL file and `.mp4`.

## Companion configurations the execution needs

| File | Purpose |
|---|---|
| `manticore/brand/production-bible.md` | visual density, HEX codes, fonts, CTA styles |
| `manticore/brand/voice-bible.md` | pacing, tone, specific vocabulary |
| `manticore/brand/blacklist.md` | banned words ("delve", "unlock", "in today's fast-paced world", …) |
| `_bmad/custom/config.toml` | tool mapping (audio lane → Kokoro-82M, graphics lane → HyperFrames) |

## Production Bible — operator template (verbatim)

> **Adaptation note for the Spec/mc-setup:** the values below are the
> operator's generic template. The factory's actual identity is the
> **Modernist system** (Design project `fbc1d6c8`): Archivo / Archivo
> Expanded / JetBrains-style mono, palette `#ec3013` / `#c22a10` / `#f3f2f2` /
> `#201e1d` / `#d3d0cf`. Materialization into `manticore/brand/` should carry
> the Modernist tokens, not the placeholders — the template's *structure* is
> what's adopted.

**Purpose:** Defines the visual identity, motion graphics constraints, and
asset generation policies for this Manticore studio. Read by the AI pipeline
so all auto-generated overlays, graphics, and B-roll match the creator's
brand.

### 1. Brand identity

- **1.1 Color palette** — Primary `#FF3366` (action items, highlights, bold
  text) · Secondary `#2A2D34` (backgrounds, lower-third base plates) · Accent
  `#00E5FF` (secondary highlights, UI callouts) · Text/Body `#FFFFFF`.
- **1.2 Typography** — Header `Inter-Bold.ttf` (title cards, large kinetic
  text) · Body `Inter-Regular.ttf` (subtitles, bullets) · Code/Terminal
  `JetBrainsMono-Regular.ttf` (syntax + CLI mockups). All referenced
  `.ttf`/`.otf` files in `manticore/brand/fonts/`.
- **1.3 Logos & watermarks** — Primary `manticore/brand/assets/logo-main.svg`;
  bug/watermark `logo-bug-white.svg` at 50% opacity, bottom-right.

### 2. Visual density & pacing

- **Target density tier: Medium.** (Low: subtle lower-thirds only, let footage
  breathe · Medium: graphics for key concepts, lists, CTAs; kinetic captions
  for emphasis · High: fast-paced, constant visual reinforcement, data-viz, 3D
  mockups.)
- **Pacing constraint:** no visual beats closer than 4 seconds apart.

### 3. Motion feel & aesthetics (HyperFrames)

- Animation: snappy, `ease-out-expo`, no slow fades.
- Transitions: hard cuts for b-roll; subtle directional wipes or WebGL glitch
  shaders for chapter transitions.
- Lower thirds: flat design, sharp corners, solid plates; drop shadows
  forbidden.
- Kinetic captions: highlight the spoken word in the Primary hex as spoken;
  max 3–4 words on screen.
- Background removal: solid Secondary background or dark blurred gradient
  behind the extracted speaker.

### 4. Generative asset policy

- **Rule 1 — strict UI authenticity:** never AI-generate user interfaces, code
  snippets, or dashboards; all software UI from provided `.mp4` recordings.
- **Rule 2 — b-roll restraint:** generated b-roll only for abstract concepts
  ("a busy server room", "a high-speed train").
- **Rule 3 — photorealism:** generated stills/clips lean cinematic
  photorealistic; vector-art/cartoon banned unless the outline requests it.

### 5. CTA inventory

Placed automatically at research-backed seams (high-retention moments, final
10%):

- **CTA_Subscribe** — 3D subscribe-button animation with cursor click; 5s;
  trigger when the script mentions subscribing/following.
- **CTA_Newsletter** — floating device mockup with signup page + QR overlay;
  "Join the waitlist at example.com/join"; 8s.
- **CTA_Discord** — pulsing logo, "Join the Community"; very end of video
  (Gate 4 finish).
