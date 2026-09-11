# Herald's manticore studio

Herald's video-production tool, `bmad-manticore`, is adopted for exactly one
purpose: turning a station deck's speaker notes into a rendered `.mp4`. It
lives in its own studio ROOT, entirely **outside** this repo's git tree —
never provisioned into `.claude/skills/`, never touching this repo's `_bmad/`
or `_bmad-output/`. This doc records the exact, proven procedure (Story
46.6). The first actual render is herald 18.1's job, not this doc's.

## Studio root

Declared once per machine by `$PYFORGE_STUDIO_ROOT` (default
`~/pyforge-studio/`, per spine decision AD-3, 2026-09-06). On this machine
the env var is unset, so the default resolves to `/home/rxm7706/pyforge-studio`.
The directory is a plain filesystem path with its own independent `_bmad`
tree — nothing under it is ever added to this repo's `.gitignore` or tracked
by this repo's git.

## Prerequisites (verify before installing)

Check with `which <tool>` on the studio machine:

- `uv` — required
- `node` — required
- `git` — required
- `ffmpeg` — required for the actual render step (herald 18.1); **not**
  required for the install itself

Live result on this machine (2026-09-07): `uv`, `node`, and `git` all
resolved (via the pixi `local-recipes` env's `bin/`, on PATH for this shell).
**`ffmpeg` was absent from PATH entirely** — not merely missing from a pixi
env, and not declared anywhere in `pixi.toml`. This is a documented gap, not
something this story installs: the render step (herald 18.1, out of this
story's scope) will need `ffmpeg` installed separately, by the operator, on
whatever machine actually renders.

## The one sanctioned install command

```
npx bmad-method install --directory $PYFORGE_STUDIO_ROOT --custom-source https://github.com/bmad-code-org/bmad-manticore --yes --tools claude-code,codex,cursor,github-copilot,adal,antigravity-cli,auggie,goose,cline,codebuddy,codewhale,command-code,crush,droid,firebender,gemini,antigravity,grok,hermes,bob,iflow,junie,kilo,kimi-code,kiro,kode,mistral-vibe,mux,neovate,ona,openclaw,opencode,openhands,pi,pochi,polytoken,qoder,qwen,replit,roo,rovo-dev,cortex,amp,trae,warp,windsurf,zcode,zencoder
```

**Both `--directory` and `--yes --tools <id[,id...]>` are required** to
complete non-interactively. This was empirically discovered the hard way
across three attempts at this story:

- Attempt 1 (bare command, no flags, cwd = studio root): hit an
  unanswerable `◆ Installation directory:` interactive prompt and exited
  without writing anything.
- Attempt 2 (`--yes --tools claude-code,...` added, still no `--directory`,
  cwd = studio root): hit the **identical** `Installation directory:` prompt
  — `--yes` does not suppress that specific first prompt on its own, even
  with `--tools` present.
- Attempt 3 (this run — `--directory $PYFORGE_STUDIO_ROOT` added on top of
  `--yes --tools <48 ids>`): completed cleanly, non-interactively, with cwd
  irrelevant. All 48 tool integrations succeeded.

`--tools` takes the full list of tool IDs from the installer's own
`--list-tools` output — no subset is "the sanctioned command" once `--yes`
is used (the installer's own `--help` documents `--tools` as **required**
for non-interactive `--yes` installs).

## What the install actually writes (real observed shape)

The install writes a `BMad Manticore v3.1.0` module (from the
`bmad-code-org/bmad-manticore` repo's `main` branch / `next` channel — a
different pin from the conda `bmad-manticore` package's own frozen
`3.1.0.dev0` recipe version; the two are separate paths by design, per
AD-3) alongside the BMad Core module (`v6.12.0`), entirely under
`$PYFORGE_STUDIO_ROOT/_bmad/`:

- `_bmad/manticore/config.yaml` — the module's own per-module config
  (`user_name`, `project_name`, `communication_language`,
  `document_output_language`, `output_folder`).
- `_bmad/manticore/module-help.csv` — the module's help-catalog entries.
- `_bmad/config.toml` — gains an `[agents.mc-agent]` section (the studio's
  front-door agent, "Manny," the Visionary Director).
- `_bmad/_config/manifest.yaml` — the actual install-registration record:
  a `modules:` list entry `{name: manticore, version: main, source: custom,
  repoUrl: https://github.com/bmad-code-org/bmad-manticore, channel: next}`,
  plus an `ides:` list naming all 48 configured tool IDs.

**Divergence from the epic's literal phrasing:** the epic/spec text
expected `mc-setup` to write `[modules.manticore]` into the studio's
`_bmad/custom/config.toml`. That file exists but is untouched — it is the
empty team-override template the installer explicitly never writes to (its
own header says so: "Those files are never touched by the installer.").
There is no `[modules.manticore]` TOML table anywhere in the studio's
`_bmad/` tree. The real "module installed" record is the
`_bmad/_config/manifest.yaml` `modules:` array entry described above.

**Skills land per-tool, not in one place.** `claude-code` gets 23 skills
under `$PYFORGE_STUDIO_ROOT/.claude/skills/` — 8 shared BMad Core skills
(`bmad-advanced-elicitation`, `bmad-brainstorming`, `bmad-customize`,
`bmad-deep-recon`, `bmad-forge-idea`, `bmad-help`, `bmad-party-mode`,
`bmad-review`) plus exactly the fifteen `mc-*` manticore skills the epic
named:

```
mc-agent  mc-assets  mc-audio      mc-beats    mc-braindump
mc-cut    mc-graphics mc-new       mc-outline  mc-package
mc-pipeline mc-retro  mc-script    mc-setup    mc-stream-pack
```

Every one of the other 47 tool IDs gets its own copy of the same 23 skills
in its own tool-specific directory (`.agents/skills`, `.cline/skills`,
`.factory/skills`, `.kiro/skills`, ... — several tool IDs share the common
`.agents/skills` target). All 48 tools reported `✓ <tool> (23 skills →
<target-dir>)` and the run ended `Installed to:
$PYFORGE_STUDIO_ROOT/_bmad`.

## The isolation guarantee (checksum-proven)

Digest command (run from this repo's worktree root):

```
find "$REPO_ROOT/_bmad" "$REPO_ROOT/_bmad-output" -type f | sort | xargs -r sha256sum | sha256sum
```

Snapshot A (captured immediately before the one install invocation) and
snapshot B (captured immediately after it returned, with no other edit to
this repo in between) were **byte-identical**:

```
d6619ecbb6b081f9b4ad2e5cd06fe02df525730e547700e10ca377aa762cecea
```

Unlike the two prior (blocked) attempts at this story — where the bracket
technically matched but was a trivial pass because the install never wrote
anything — this is a **meaningful** isolation proof: the install genuinely
wrote a large tree (2 modules × 48 tool integrations × 23 skills, plus
`_bmad/_config/*`) entirely under `$PYFORGE_STUDIO_ROOT`, and none of it
leaked into this repo's own `_bmad/` or `_bmad-output/`.

This repo's own `.claude/skills/` also stayed at zero `mc-*` directories,
before and after — the native install never targets this repo.

## Next step

Herald's first actual render using this studio is **Story herald 18.1's**
job — this doc only proves the studio exists, is reachable, and is
isolated. `ffmpeg` will need to be installed on whatever machine runs that
story before a render can succeed. (That render is the one recorded
immediately below, completed 2026-09-07.)

## Story 18.1: the first real render (2026-09-07)

`ffmpeg` was resolved via the `ffmpeg` pixi env on this machine (the gap the
section above flagged). The full pipeline walked for real, end to end, on
project `warden-never-false-green` (format `voiceover-explainer`), narrating
the real Warden deck's speaker notes
(`presentations/pyforge-warden/src/marp/warden-deck-narration-2026-07-31.md`
in this repo):

- **Narration:** no human creator was recording, so `mc-audio`'s
  `kokoro-local` TTS lane produced it. `ensure_workspace.py` built the
  shared audio-lab venv for real (torch, accelerate, scipy,
  `diffusers==0.31.0`, `transformers==4.43.4`, `kokoro-onnx==0.5.0`,
  `soundfile` — several GB, including CUDA runtime packages the default
  Linux PyPI `torch` wheel bundles even with no GPU present) and downloaded
  the real `kokoro-v1.0.onnx` + `voices-v1.0.bin`. `farm_audio.py` then
  synthesized 512.23s of narration (voice `af_heart`, speed 1.0) from the
  spoken-only text of `script.md` (the ~39s gap to the 473.40s final render
  below is the 149 mechanical silence trims applied at the cutplan gate,
  not lost or unaccounted-for content).
- **The video-stream gap:** `mc-cut`'s `preflight.py` unconditionally
  requires a video stream and has no audio-only lane, a real gap for a
  no-camera format with no human recording video either. Resolved by muxing
  the narration onto a plain brand-canvas base video (`color=c=0xf3f2f2`,
  the real Modernist token, at the delivery resolution/fps) — a mechanical
  necessity, not fabricated content, since the format's actual visual track
  is 100% wall-to-wall graphics overlays regardless.
- **Gates walked, all four, all self-approved** by the operating agent
  (bmad-build-auto's no-human-interaction rule; no separate human creator
  present — a limitation of this walkthrough, not a general policy: a real
  production render should have an independent human approve at least gate
  2 and gate 4) — full provenance in the project's own `project.json.notes`:
  - **outline** (gate 1, 2026-09-07, prior session)
  - **cutplan**: transcribed via `onnx-asr` (this machine's `auto` lane);
    `verify_transcript.py` genuinely failed once (a real 3.18s dropped
    phrase, the exact windowing defect class `mc-cut/SKILL.md` documents)
    and was fixed by re-transcribing the region in isolation and splicing
    the recovery in; 149 mechanical silence trims applied, 4 candidates
    (2 ASR token-splits, 2 deliberate rhetorical repeats) checked against
    the real script and rejected.
  - **beats**: 16 beats, every anchor time derived from the real transcript
    remapped through the EDL (never estimated); `verify_anchors.py` also
    failed once for real (an anchor word landing astride a silence-trim
    boundary) and was fixed by choosing an unambiguous anchor word for the
    same moment.
  - **final**: all 16 graphics rendered as real HTML/SVG comps (Playwright
    + Chromium, real Archivo brand font embedded) — no HyperFrames engine
    workspace built, per this story's own scope. Compositing the graphics
    overlays surfaced a genuine precision bug in this story's own EDL
    frame-quantization (rounding to 4 decimals landed just past the true
    frame boundary, so ffmpeg's trim included one extra frame per affected
    segment, accumulating to +0.93s over 150 segments); fixed by keeping
    full float precision and re-verified before the final render.
- **Result:** `renders/final.mp4` — h264 1920x1080 30fps + aac 48kHz
  stereo, 473.40s, loudnorm applied (measured -20.6 LUFS -> -14.0 LUFS
  target), `ffprobe`-valid, 16,643,022 bytes. These figures (durations, byte
  size, LUFS, beat/trim counts) are only checkable on the machine that ran
  the render, against the real file with `ffprobe`; nothing in this repo's
  own tooling can independently confirm them, since the studio and its
  render live entirely outside this repo by design.
- **Isolation re-proven:** this repo's `_bmad` + `_bmad-output` checksum was
  captured before the render and again after every stage completed,
  byte-identical throughout, despite the multi-GB TTS install, transcription
  model download, and Chromium install all happening in the same session.

The installed Manticore module still tracks `main`/`next` (unpinned, the
open reproducibility risk 46.6 already recorded); this render used whatever
resolved on 2026-09-07 and records no new pin.
