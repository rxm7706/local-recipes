---
sources:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-46-6-heralds-manticore-studio-has-a-root-and-a-proven-native-path.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-18-1-the-first-station-video-renders-from-heralds-studio.md
  - presentations/pyforge-warden/src/marp/warden-deck-narration-2026-07-31.md
verified: 2026-11-18
---

# Herald's manticore studio

Use the lock's `bmad-method` installer to set up Herald's video studio, `bmad-manticore`, in a studio root outside this repository. Manticore is adopted for one purpose: turning a station deck's speaker notes into a rendered `.mp4`.

## When to Use This

- You are setting up a machine that will render a station video.
- `steward suite pipeline-truth` reports `bmad-manticore` as `studio-module | unwired` and you want it wired.
- You are re-running the install to pick up a newer manticore.

## When to Skip This

Skip it on a machine that never renders video. One other thing reads it: steward's live suite checks the adoption register's `wired` row against this install on any machine where `CI` is unset ([How to run and read the pre-push preflight](run-and-read-pr-preflight.md)). Otherwise nothing from it is provisioned into this repository's `.claude/skills/`, `_bmad/` or `_bmad-output/`.

:::note[Prerequisites]
- The `pyforge-guild` pixi environment, installed from this repository's lock. Its `bmad-method` is 6.12.2 (`pixi run -e pyforge-guild bmad-method --version`).
- `uv`, `node` and `git` on `PATH` on the studio machine.
- `ffmpeg`, for the render only. The install does not need it. `ffmpeg` is in no pixi environment and `pixi.toml` does not declare it, so install it yourself on the machine that renders.
- Network access to GitHub: the installer fetches `bmad-code-org/bmad-manticore`.
:::

## Steps

### 1. Choose the studio root

The studio root is declared once per machine by `$PYFORGE_STUDIO_ROOT`; unset or empty, it is `~/pyforge-studio`. Steward's probe reads the same variable and the same default, so install where the probe will look. The root is a plain directory with its own `_bmad` tree, outside this repository's git tree.

### 2. Run the installer from the lock

From the repository root:

```bash
pixi run -e pyforge-guild bmad-method install --directory "$HOME/pyforge-studio" --custom-source https://github.com/bmad-code-org/bmad-manticore --yes --tools claude-code,codex,cursor,github-copilot,adal,antigravity-cli,auggie,goose,cline,codebuddy,codewhale,command-code,crush,droid,firebender,gemini,antigravity,grok,hermes,bob,iflow,junie,kilo,kimi-code,kiro,kode,mistral-vibe,mux,neovate,ona,openclaw,opencode,openhands,pi,pochi,polytoken,qoder,qwen,replit,roo,rovo-dev,cortex,amp,trae,warp,windsurf,zcode,zencoder
```

If you set `$PYFORGE_STUDIO_ROOT`, pass that path to `--directory` instead. The command runs without prompts and exits `0`.

:::caution
Use the installer the lock carries, as shown. The Node package-runner form of the same command is an ad hoc install, and this repository's session hook denies it.
:::

### 3. Check that it worked

```bash
ls -d "$HOME"/pyforge-studio/.claude/skills/mc-*
grep -A4 'name: manticore' "$HOME/pyforge-studio/_bmad/_config/manifest.yaml"
pixi run -e pyforge-guild pyforge steward suite pipeline-truth
```

The first command lists fifteen `mc-*` directories. The second shows the manifest entry with `version: main` and `source: custom`. In the third, the `bmad-manticore` block reads `wired:            studio-module | wired`.

Steward reads "wired" when the studio root has a `_bmad/` directory and at least one `.claude/skills/mc-*` directory; either one missing reads `unwired`. Run `pipeline-truth` without `--baseline`: that flag replays a recorded matrix, and on 2026-11-18 it still printed `unwired` for a studio the live probe read as wired.

### 4. Install `ffmpeg` before you render

The render step needs `ffmpeg` on `PATH`. Install it yourself on the machine that renders.

## What You Get

On the operator's macOS laptop on 2026-11-18 the install wrote 55 MB under `~/pyforge-studio`:

- `_bmad/manticore/config.yaml`, the module's own config.
- `_bmad/config.toml`, with an `[agents.mc-agent]` section for the studio's front-door agent.
- `_bmad/_config/manifest.yaml`, the install record: a `modules:` entry with `name: manticore`, `version: main`, `source: custom` and `channel: next`, and an `ides:` list of the 48 tool ids.
- `.claude/skills/`, holding 23 skills: eight BMad Core skills and the fifteen manticore skills below.

```
mc-agent  mc-assets  mc-audio      mc-beats    mc-braindump
mc-cut    mc-graphics mc-new       mc-outline  mc-package
mc-pipeline mc-retro  mc-script    mc-setup    mc-stream-pack
```

Every other tool id gets its skills in its own directory (`.agents/skills`, `.cline/skills`, `.kiro/skills` and so on).

The install record is the manifest entry. The 2026-09-07 run found no `[modules.manticore]` table anywhere in the studio, and the installer does not write to the studio's `_bmad/custom/config.toml`.

:::caution[Unpinned]
The module tracks `main` on the `next` channel, with no lockfile. Re-running the command later can install a different manticore. The conda `bmad-manticore` package is a separate path with its own recipe version.
:::

## Why these flags

Both `--directory` and `--yes --tools <ids>` are required for a run without prompts. Steward Story 46.6 found this over three attempts on Linux on 2026-09-07:

1. The bare command, run from the studio root, stopped at an `Installation directory:` prompt and wrote nothing.
2. With `--yes --tools …` but no `--directory`, it stopped at the same prompt. `--yes` does not suppress it.
3. With `--directory` added, it completed with all 48 tool integrations.

`--tools` takes the full id list from the installer's own `--list-tools` output; its `--help` marks `--tools` as required for a fresh `--yes` install. The list above matched `--list-tools` in bmad-method 6.12.2 on 2026-11-18.

## Record of the first render

This section is a dated record, not a procedure. Both runs below were on the operator's Linux workstation on 2026-09-07, and the render figures can be checked only on that machine, against the real file with `ffprobe`.

### Isolation (steward Story 46.6)

A digest of this repository's `_bmad/` and `_bmad-output/` was taken immediately before and after the install:

```
find "$REPO_ROOT/_bmad" "$REPO_ROOT/_bmad-output" -type f | sort | xargs -r sha256sum | sha256sum
```

Both snapshots were `d6619ecbb6b081f9b4ad2e5cd06fe02df525730e547700e10ca377aa762cecea`. The install wrote two modules and 48 tool integrations under the studio root and nothing into this repository, whose `.claude/skills/` held no `mc-*` directory before or after. That run installed `BMad Manticore v3.1.0` beside BMad Core `v6.12.0`.

### The render (herald Story 18.1)

The pipeline ran end to end on project `warden-never-false-green` (format `voiceover-explainer`), narrating the Warden deck's speaker notes, `presentations/pyforge-warden/src/marp/warden-deck-narration-2026-07-31.md`. `ffmpeg` was supplied on that machine by hand.

| Stage | What happened |
| --- | --- |
| Narration | No human recorded, so `mc-audio`'s `kokoro-local` lane synthesized 512.23s (voice `af_heart`, speed 1.0). Its audio venv is several GB: torch, `diffusers==0.31.0`, `transformers==4.43.4`, `kokoro-onnx==0.5.0`. |
| Video stream | `mc-cut`'s `preflight.py` requires a video stream and has no audio-only lane. The narration was muxed onto a plain brand-canvas base video (`color=c=0xf3f2f2`). |
| Cutplan | Transcribed with `onnx-asr`. `verify_transcript.py` failed once on a 3.18s dropped phrase, fixed by re-transcribing that region. 149 silence trims were applied and 4 candidates rejected. |
| Beats | 16 beats, each anchor derived from the transcript through the EDL. `verify_anchors.py` failed once on an anchor astride a trim boundary, fixed by choosing another anchor word. |
| Final | 16 graphics rendered as HTML/SVG comps with Playwright and Chromium. A frame-quantization rounding bug added 0.93s over 150 segments; it was fixed before the final render. |

The result was `renders/final.mp4`: h264 1920x1080 at 30 fps with aac 48 kHz stereo, 473.40s, 16,643,022 bytes, loudness normalized from -20.6 LUFS to the -14.0 LUFS target. The 39s between the narration and the render is the 149 silence trims.

All four gates (outline, cutplan, beats, final) were approved by the operating agent, because no human creator was present. That is a limit of this walkthrough: a production render should have a person approve at least the cutplan gate and the final gate. The repository digest was taken again after every stage and never changed.
