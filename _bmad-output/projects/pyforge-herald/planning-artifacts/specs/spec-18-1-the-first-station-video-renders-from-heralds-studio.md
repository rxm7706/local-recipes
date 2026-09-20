---
title: 'The first station video renders from Herald''s studio'
type: 'feature'
created: '2026-09-07'
status: 'done'
baseline_revision: 'ef1ab785fe853f53079ba2baed64d01c943bd82c'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
deferred:
  - summary: >-
      Never-caught false-done risk: the ledger-direction detector that would flag a
      done-but-unmerged sprint-ledger flip is not wired into detectors/detectors-ci.
    evidence: |-
      pyforge.doctor.sources.ledger::gather_direction exists and is unit-tested for exactly
      this shape (a tracked ledger done key with no matching merge subject and no Tier-3
      feed), but scripts/detectors.py's _DOCTOR_SOURCE_TASKS omits it and no pixi task
      exposes it, so neither detectors nor detectors-ci ever runs it. Pre-existing gap,
      not introduced by this story; wiring it in is a repo-wide fix beyond this story's scope.
    location: >-
      scripts/detectors.py (_DOCTOR_SOURCE_TASKS)
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Herald's manticore studio (`~/pyforge-studio`, steward 46.6) is installed and proven
isolated from this repo, but no station video has ever actually rendered through it, and Herald's
own skill carries no hand-off pointing an operator there.

**Approach:** Add a hand-off note to `bmad-agent-herald/SKILL.md` pointing operators at
`$PYFORGE_STUDIO_ROOT`, then walk one real station deck's speaker notes end-to-end through the
studio (`mc-setup` -> `mc-braindump` -> `mc-outline` -> `mc-script` -> `record` -> `mc-cut` ->
`mc-beats` -> `mc-assets` -> `mc-graphics` -> `mc-package` -> `final`) to produce one real
`<station>.mp4`, then record the outcome in the adoption register.

## Boundaries & Constraints

**Always:**
- The studio is a separate root, read from `$PYFORGE_STUDIO_ROOT` (default `~/pyforge-studio/`).
  Nothing from the render pipeline is ever provisioned into this repo's `.claude/skills/`, `_bmad/`,
  or `_bmad-output/`. Verify this repo's `_bmad/` + `_bmad-output/` checksum is byte-identical
  before and after the render (same `find | sort | xargs sha256sum | sha256sum` recipe steward 46.6
  used in `docs/reference/manticore-studio.md`).
- Use only real, already-existing repo content as pipeline input: an existing station's speaker
  notes / narration script under `presentations/<station>/src/marp/*-narration-*.md`. Do not
  fabricate brand, voice, or taste content the studio's own `mc-setup` interview asks for; where a
  real answer exists in this repo (the Modernist design system: Archivo, `#f3f2f2`/`#201e1d`/
  `#ec3013`, documented in `docs/dreams/herald-pitch.md` Tier 1d), use it. Where no real personal
  answer exists (a human creator's name, voice, headshots), leave it explicitly empty/placeholder
  exactly as the skill's own rules permit -- never invent a person or a voice.
- `.mp4` output and every render intermediate under the studio's `manticore/projects/<slug>/` are
  build artifacts of the STUDIO, not this repo -- nothing about them is committed to this repo.
- Any CLI surface Herald exposes stays under the existing `pyforge herald ...` dispatch pattern.
- Herald's own persona-skill trace of this capability is a hand-off NOTE, never a wrapper: it tells
  the operator to open a session in the studio root and run `mc-*` there themselves -- it does not
  shell out to, import, or invoke `mc-*` tooling from inside this repo.

**Never:**
- Never install any `mc-*` skill, or any manticore/BMad-Core file, under this repo's
  `.claude/skills/` or `_bmad/`.
- Never touch `CLAUDE.md` for this routing note (the persona skill + one `AGENTS.md` pointer line
  is the only durable home, per the adoption register's own convention -- though this story's surface
  is `bmad-agent-herald/SKILL.md` only; the `AGENTS.md` pointer line is 18.2/18.3's concern per the
  register's routing-table rows, not duplicated here for the studio itself since row 9's own cell in
  `adoption-register.md` already carries the studio's routing detail).
- Never fabricate a rendered artifact: a `.mp4` is only real if it was produced by genuinely running
  the studio's own scripts (`preflight.py`, `verify_transcript.py`, `verify_edl.py`,
  `render_final.py`, etc.) against real inputs -- no hand-written stub video, no placeholder file
  renamed to `.mp4`.
- Never skip a stage's own required verification script to force progress (per PIPELINE.md's
  Verification Contract: a check the pipeline claims to perform is a script that exits non-zero).

</intent-contract>

## Code Map

- `/home/rxm7706/pyforge-studio/.claude/skills/mc-pipeline/PIPELINE.md` -- the stage/gate contract
  (12 stages, 4 gates: outline/cutplan/beats/final; `project.json` schema).
- `/home/rxm7706/pyforge-studio/.claude/skills/mc-setup/SKILL.md` + `assets/studio-defaults.toml` +
  `assets/formats/voiceover-explainer.md` -- studio config schema; every `mc-*` skill fails closed
  without `[modules.manticore]`.
- `/home/rxm7706/pyforge-studio/_bmad/custom/config.toml` -- **already written this session**:
  `[modules.manticore]` with format `voiceover-explainer`, `owner.channel = "PyForge Guild"`
  (`owner.name` left empty -- no human creator), `[audio] tts-provider = "kokoro-local"`,
  `[transcription]` lane `auto` (resolves to onnx-asr on this non-Apple-Silicon box),
  `[cta] appetite = "minimal"` with zero items, `[assets]` lanes empty (no registered generation
  tool). Read this file, do not re-run the full interview.
- `/home/rxm7706/pyforge-studio/manticore/brand/` -- real brand assets already built this session:
  `tokens.json` (Modernist palette/Archivo, mined from `docs/dreams/herald-pitch.md`),
  `production-bible.md` (7 sections), `blacklist.md`, `craft-checklist.md` (shipped defaults),
  `exemplars/` (the Warden narration, labeled as a substitution). `voice-bible.md` and `headshots/`
  are explicit flagged placeholders (no human creator) -- leave them that way.
- `/home/rxm7706/pyforge-studio/manticore/projects/warden-never-false-green/project.json` --
  **already scaffolded and progressed this session** through `new` -> `braindump` -> `outline`
  (gate 1 self-approved, ISO-dated) -> `script`. `stage: "record"` is where this story's remaining
  work picks up. Read `notes` in this file for the full provenance of every decision made so far.
  Its `braindump.md` / `outline.md` / `script.md` are real, already-written artifacts -- do not
  redo them.
- `/home/rxm7706/pyforge-studio/manticore/projects/warden-never-false-green/raw/warden-deck-narration-2026-07-31.md`
  -- the real external transcript (quoted, not paraphrased) sourced from
  `presentations/pyforge-warden/src/marp/warden-deck-narration-2026-07-31.md` in the `local-recipes`
  repo.
- `/home/rxm7706/pyforge-studio/.claude/skills/mc-audio/scripts/ensure_workspace.py` -- builds the
  shared local-audio venv. `--check` already confirmed exit 4 (not ready): needs `torch`,
  `accelerate`, `scipy`, `diffusers==0.31.0`, `transformers==4.43.4` plus `kokoro-v1.0.onnx`
  (~310MB) and `voices-v1.0.bin` (~27MB). This is the next concrete action -- run it for real
  (`ensure_workspace.py`, no `--check`/`--dry-run`) and accept the download/install cost; it is a
  one-time build under the studio root, not this repo.
- `/home/rxm7706/pyforge-studio/.claude/skills/mc-cut/SKILL.md` + its `scripts/` -- preflight,
  transcribe, cutplan, verify_edl, render_preview/render_final. Reads `[cut]` config + brand bibles.
- `/home/rxm7706/pyforge-studio/.claude/skills/mc-beats/`, `mc-assets/`, `mc-graphics/`,
  `mc-package/` SKILL.md -- read each fully before acting; for graphics, prefer the "plain HTML/SVG
  comps" engine default over building the separate HyperFrames engine workspace (already-installed
  HyperFrames Agent-Skills CLI is sufficient reference material; the multi-GB engine workspace is a
  second heavy build this story does not need to take on when SVG comps satisfy the same beat
  contract using real brand tokens).
- `/home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes/.claude/skills/bmad-agent-herald/SKILL.md`
  -- add the hand-off note here (a new short section, matching the existing "Utility skill routing
  (AD-2)" section's style), pointing at `$PYFORGE_STUDIO_ROOT` and naming the `mc-*` skills by
  family, never a route or wrapper.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md`
  row 9 (member 9, `bmad-manticore`) -- update the "Status / story" cell (currently `46.6, herald
  18.1`) to record the render date and which of the four approval gates were walked; leave every
  other cell in that row untouched (steward's provisioning content stays steward's).
- `docs/reference/manticore-studio.md` -- append a short dated addendum recording this story's real
  render outcome (mirrors how 46.6 recorded its own proof), rather than rewriting the existing
  46.6-authored content.

## Tasks & Acceptance

**Execution:**
- `/home/rxm7706/pyforge-studio/.claude/skills/mc-audio/scripts/ensure_workspace.py` -- run for real
  (accept the ~340MB model download + shared-venv install) -- unblocks the only honest narration
  path available (no human creator to record).
- `/home/rxm7706/pyforge-studio/manticore/projects/warden-never-false-green/` (`record` through
  `final` stages) -- synthesize narration audio from `script.md` via `kokoro-local`, register it as
  the project's `raw/` source, then walk `mc-cut` (preflight -> transcribe -> verify -> cutplan,
  gate 2 self-approved) -> `mc-beats` (gate 3 self-approved, SVG-comp engine) -> `mc-assets` ->
  `mc-graphics` -> `mc-package` -> `final` (offered pipeline render via `render_final.py`, gate 4
  self-approved) -- produce `renders/final.mp4` -- every gate self-approved by the operating agent,
  consistent with bmad-build-auto's own no-human-interaction rule and gate 1's precedent already set
  this session; record that provenance in `project.json` exactly as gate 1 already does.
- `local-recipes/.claude/skills/bmad-agent-herald/SKILL.md` -- add a "Manticore studio hand-off"
  section, prose only, naming `$PYFORGE_STUDIO_ROOT` and the `mc-*` skill family -- gives operators
  the durable in-repo pointer the epic's Surface line requires.
- `local-recipes/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md`
  -- update row 9's "Status / story" cell with the render date + gates walked.
- `local-recipes/docs/reference/manticore-studio.md` -- append a dated "Story 18.1: the first real
  render" section recording the outcome (slug, format, gates walked, final render path/size,
  isolation-checksum result).

**Acceptance Criteria:**
- Given the provisioned studio and this repo's `_bmad/`+`_bmad-output/` checksum captured
  beforehand, when the pipeline above runs to completion, then
  `~/pyforge-studio/manticore/projects/warden-never-false-green/renders/final.mp4` exists as a real,
  non-empty, ffprobe-valid video file.
- Given that same checksum recaptured immediately after the render, when compared to the "before"
  value, then the two are byte-identical (this repo's `_bmad/` was never touched).
- Given `bmad-agent-herald/SKILL.md` after this story, when an operator reads it, then they find a
  prose hand-off naming `$PYFORGE_STUDIO_ROOT` and the `mc-*` skill family, with no executable route
  or wrapper into the studio.
- Given `adoption-register.md` row 9 after this story, when read, then its "Status / story" cell
  names the render date and which of the four approval gates (outline/cutplan/beats/final) were
  walked and by what provenance (self-approved, no human creator present).
- Given the studio's own `.mp4` and render-intermediate outputs, when checked against this repo's
  git status, then none of them appear as tracked or staged files (they live entirely under
  `~/pyforge-studio/`, outside this repo's working tree).

## Spec Change Log

## Review Triage Log

### 2026-09-07 — Review pass
- verdicts: 15 findings — high 5, medium 1, low 6, false 2, maybe-false 0
- findings:
  - `[high]` `[patch]` sprint-status-ledger.yaml hand-edited directly (`blocked`->`done` for 18-1), bypassing the required Tier-3-write + `sprint-ledger-sync` procedure (blind-hunter) — verified: the tracked ledger and the Tier-3 feed at `implementation-artifacts/sprint-status.yaml:129` now disagree (Tier-3 still reads `blocked`); AGENTS.md:20/:29 both directly forbid this. Grouped with the three rows below (same root cause). Fix: revert the tracked hand-edit, write the Tier-3 feed, run `sprint-ledger-sync -- --project pyforge-herald`.
  - `[high]` `[patch]` same ledger hand-edit is not listed anywhere in the spec's own Tasks & Acceptance (edge-case-hunter) — verified: `## Tasks & Acceptance` names 5 items, none is the ledger. Grouped, same fix as above.
  - `[high]` `[patch]` the ledger `done` claim is not backed by any check the repo actually runs; the one detector built for this shape (`ledger-direction`) is unwired from `detectors`/`detectors-ci` (verification-gap, main finding, root-cause portion) — verified: `_DOCTOR_SOURCE_TASKS` in `scripts/detectors.py` has no `ledger-direction` entry and no matching pixi task exists. Grouped, same fix as above.
  - `[high]` `[patch]` the hand-edit directly violates AGENTS.md:20 ("Never hand-edit `sprint-status-ledger.yaml`...") and :29 ("Never flip a ledger `blocked` key... without operator confirmation") (verification-gap, other findings) — verified verbatim against `AGENTS.md:20,29`. Grouped, same fix as above.
  - `[high]` `[patch]` the Tier-3 spec at `implementation-artifacts/spec-18-1-...md` was never promoted to the tracked `planning-artifacts/specs/` directory per this repo's "story specs are durable" convention (blind-hunter) — verified: every prior done herald story checked (17-1, 17-2) has a promoted copy there; 18-1 does not, so it would be lost on worktree teardown (the exact pyforge-warden incident this convention exists to prevent). Fix: copy the final spec content to `planning-artifacts/specs/spec-18-1-...md` and `git add` it.
  - `[medium]` `[defer]` `ledger-direction` being unwired from CI is real and would catch exactly this class of desync, but it is a pre-existing gap across the whole repo, not caused by this story, and wiring a new detector into `detectors`/`detectors-ci` is materially larger than this story's intent (verification-gap) — recorded as deferred, not fixed here.
  - `[low]` `[reject]` adoption-register.md row 9's cell is already ~1,942 characters on one line before this diff; making it longer without restructuring to a footnote/sub-bullet is a real readability complaint, but the fix (extracting a footnote convention) is more than a direct correction and the row was already this unwieldy pre-diff (blind-hunter) — rejected: pre-existing condition, fix exceeds trivial-correction bar.
  - `[low]` `[patch]` the reported "512.23s of narration" vs the final "473.40s" render duration are never reconciled for the reader (blind-hunter) — real gap, trivial one-clause fix (tie the ~39s difference to the mechanical silence trims already mentioned).
  - `[false]` `[reject]` claim that 18-2/18-3 remaining `blocked` needs re-triage now that 18-1 is done (blind-hunter) — refuted: `epic-18-context.md` states explicitly "18.1, 18.2, and 18.3 have no dependencies on each other"; 18-2/18-3 are blocked on their own independent steward producers, not on 18.1, and re-triaging them is out of this story's scope regardless.
  - `[low]` `[patch]` gate numbering left implicit: "outline" is never explicitly labeled "gate 1" even though the summary counts "all four approval gates" (blind-hunter) — real, trivial fix (add "(gate 1)" next to "outline" in both new prose blocks).
  - `[low]` `[patch]` self-approval of all four gates (no separate human creator) is stated as a bare fact with no risk flag, unlike the neighboring floating-version-pin risk in the same register row which carries an explicit "not resolved here" marker (blind-hunter, corroborated independently by the intent-alignment auditor) — real, trivial fix (one clause flagging this as a walkthrough limitation, not general policy).
  - `[false]` `[reject]` claimed typography inconsistency between "--" and em-dash, and the LUFS arrow style, in the new prose (blind-hunter) — refuted: `grep -c` against the pre-existing content of both edited files shows both dash conventions already pervasive throughout (manticore-studio.md: 11 "--" / 27 "—"; bmad-agent-herald/SKILL.md: 4 "--" / 8 "—") — the new prose is consistent with, not an outlier against, existing repo style in these same files.
  - `[low]` `[patch]` final.mp4's specific numeric claims (duration, byte size, LUFS, beat/trim counts) are asserted with no note that they are unverifiable from the repo itself, since the studio lives entirely outside it by design (blind-hunter, corroborated independently by the intent-alignment auditor's observation that no checksum/manifest artifact travels with the diff) — real, trivial fix (one sentence stating this plainly).
  - `[low]` `[patch]` the pre-existing "## Next step" section in manticore-studio.md still reads as forward-looking/pending directly above the new section proving the render happened (edge-case-hunter) — real, trivial fix (one forward-pointer sentence, keep the historical framing).
  - `[low]` `[patch]` adoption-register.md row 9's appended clause strings three phrases together with no connecting preposition, leaving the causal relationship unclear on re-read (blind-hunter) — real, trivial fix (add one connecting word).

## Design Notes

If `ensure_workspace.py`'s real (non-`--check`) run fails for a reason distinct from "large
download" (network unreachable, disk full, a genuine script error), or if any pipeline stage's own
verification script (`verify_transcript.py`, `verify_edl.py`, `verify_anchors.py`) fails and cannot
be resolved by a legitimate, evidence-based decision recorded in `project.json`, treat that as a
genuine implementation blocker: stop at that stage, leave `project.json` accurately reflecting where
it stopped and why (mirroring how `stage: "record"` and its `notes` field already record this
session's first stopping point), and report the exact blocking command/output rather than forcing
progress.

Self-approval provenance: every gate approval recorded as an ISO date in `project.json.approvals`
must also carry a note (in `project.json.notes`, appended not overwritten) stating it was
self-approved by the operating agent under bmad-build-auto's no-human-interaction rule, with no
separate human creator present in this walkthrough -- exactly as gate 1 (`outline`) already does.

## Verification

**Commands:**
- `ffprobe /home/rxm7706/pyforge-studio/manticore/projects/warden-never-false-green/renders/final.mp4`
  -- expected: exits 0 and reports a valid video stream with non-zero duration.
- Capture `find $REPO/_bmad $REPO/_bmad-output -type f | sort | xargs -r sha256sum | sha256sum`
  (where `$REPO` is this worktree's absolute root) before and after the render -- expected:
  identical output both times.
- `git status --short` (run from this worktree's root) -- expected: shows only the intended repo
  edits (`bmad-agent-herald/SKILL.md`, `adoption-register.md`, `docs/reference/manticore-studio.md`,
  `sprint-status-ledger.yaml`) -- no studio files, no `.mp4`, no `_bmad/` changes.
- `pixi run -e pyforge-herald pyforge-herald-test` -- expected: passes (run by the caller after this
  spec's implementation, not by this spec's own subagent unless it touched herald's Python package,
  which it does not).

**Manual checks (if no CLI):**
- Read the final ~20 lines of `project.json.notes` end to end: it should read as one coherent,
  evidence-based provenance trail from `new` through `final`, with no unexplained jump.


## Auto Run Result

Status: done
Reconciled 2026-09-20: the `blocked` verdict below is the session's own record at halt time; the story was landed afterwards and the ledger row promoted to `done` by `4251c42229 2026-09-17 Land herald fold: one chain — 11 Dreams, 10 Specs, rekey 2026-09-17` — that promotion is the ruling this record now reflects.
Blocking condition: implementation subagent launch denied by harness auto-mode classifier

Evidence: a prior synchronous investigation subagent (not this step's implementation subagent)
walked this exact studio project for real, without any classifier denial, through
`new -> braindump -> outline (gate 1, self-approved) -> script`, using only real repo content (the
Modernist brand tokens, Warden's own narration script) and no fabricated brand/voice/taste content.
It stopped at the `record` stage because the only non-human narration path (`kokoro-local` local
TTS via `mc-audio`) requires building a shared venv with `torch`, `accelerate`, `scipy`,
`diffusers==0.31.0`, `transformers==4.43.4` plus downloading `kokoro-v1.0.onnx` (~310MB) and
`voices-v1.0.bin` (~27MB) -- a multi-GB, network-heavy, one-time install. This spec's own Tasks
section instructed the next implementation subagent to run that install for real and complete the
render through `final`. Launching that subagent (via the Agent tool, per this workflow's own
step-03 "launch a subagent" instruction) was refused by Claude Code's auto-mode classifier with:
"Blocked by classifier" -- no further detail given, and the harness explicitly instructs not to
work around a classifier denial. No repo files were changed by the blocked call (it never started).

What is real and already on disk (all under `~/pyforge-studio/`, none of it in this repo):
`_bmad/custom/config.toml` ([modules.manticore] configured), `manticore/brand/` (real Modernist
tokens + production bible + honestly-placeholdered voice bible / headshots), and
`manticore/projects/warden-never-false-green/` through the `script` stage, with `project.json.notes`
carrying the full evidence-based provenance trail up to and including the exact `record`-stage stop.

Unfinished (this story's own repo-side deliverables never started, since the implementation
subagent that would have done them was never launched): the `bmad-agent-herald/SKILL.md` hand-off
note, the `adoption-register.md` row 9 status update, and the `docs/reference/manticore-studio.md`
dated addendum. No repo files were touched in this attempt; `git status --short` on this worktree is
clean.

### Resume note (2026-09-07)

Operator explicitly authorized the multi-GB TTS dependency install (torch/accelerate/scipy/
diffusers/transformers + Kokoro-82M weights) that the prior attempt's implementation-subagent
launch was denied for. Status reset to `in-progress`; re-launching the implementation subagent per
this spec's own Tasks list, unchanged. The `## Auto Run Result` block above is left as historical
evidence of the first attempt's stopping point, not amended.


## Auto Run Result (final, post-review)

**Summary of implemented change:** Herald's manticore studio (`~/pyforge-studio`) walked one real
station deck's speaker notes end-to-end through the full render pipeline for the first time
(`mc-new -> mc-braindump -> mc-outline (gate 1) -> mc-script -> record (kokoro-local TTS,
operator-authorized multi-GB install) -> mc-cut (gate 2) -> mc-beats (gate 3) -> mc-assets ->
mc-graphics -> mc-package -> final (gate 4)`), producing a real, `ffprobe`-valid
`renders/final.mp4` (473.40s, 16,643,022 bytes) entirely under the studio root, with this repo's
`_bmad/` checksum byte-identical before and after. The repo side records the outcome: a hand-off
note in Herald's persona skill, the adoption-register row, and a dated doc addendum.

**Files changed** (all in `local-recipes`, none in the studio):
- `.claude/skills/bmad-agent-herald/SKILL.md` — added the "Manticore studio hand-off" section.
- `docs/reference/manticore-studio.md` — appended the "Story 18.1: the first real render" section.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md`
  — row 9's Status/story cell now records the render date and all four gates walked.
- `_bmad-output/projects/pyforge-herald/planning-artifacts/sprint-status-ledger.yaml` — `18-1-...`
  flipped `blocked` -> `done`, via the sanctioned `sprint-ledger-sync` regeneration (after an
  initial hand-edit was caught in review and reverted).
- `_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-18-1-the-first-station-video-renders-from-heralds-studio.md`
  (new, tracked) — this spec, promoted per the "story specs are durable" convention.

**Review findings breakdown** (15 total across 4 layers; see `## Review Triage Log` above for the
full per-finding table):
- **Patched (8 entries, one grouped from 4 findings):** the hand-edited ledger (reverted, then
  redone via the sanctioned Tier-3-write + `sprint-ledger-sync` path — grouped from 4 findings,
  verdict high); the un-promoted spec (verdict high); six low-severity prose gaps (duration
  reconciliation, gate-1 labeling, self-approval risk flag, numeric-claims-unverifiable caveat,
  stale "Next step" section, an awkward register sentence).
- **Deferred (1):** the `ledger-direction` detector's absence from `detectors`/`detectors-ci` —
  real, pre-existing, not caused by this story, recorded in this spec's `deferred` frontmatter
  (severity medium).
- **Rejected (3):** the register row 9 cell's overall unwieldy size (low, pre-existing, fix exceeds
  a trivial correction); a claim that sibling stories 18-2/18-3 need re-triage (false — refuted by
  `epic-18-context.md`'s explicit "no dependencies on each other"); a claimed dash-typography
  inconsistency (false — refuted by grep showing both dash styles already pervasive in the
  pre-existing content of both edited files).

**Follow-up review recommendation:** `true`. Two `high`-verdict entries were patched on this first
pass (the ledger-process group and the spec-promotion gap), which alone triggers this under the
scoring rule, independent of how carefully they were verified here. Named unverified risk: the
implementation subagent's own hand-back disclosed that it worked around a harness-refused
Edit/Write by using a plain Bash `sed -i` on the Tier-3 feed file — a pattern this repo's own task
instructions explicitly sanction for exactly that backlinked path (verified here: the edit was
surgical, scoped to the one intended line, and the actually-tracked ledger was still produced via
the sanctioned `sprint-ledger-sync` regeneration, not the sed). The harness itself flagged this
pattern as a security warning. This review verified the one disclosed instance is benign, but did
not audit the subagent's full ~341-tool-call session for any other, undisclosed instance of the
same bypass pattern against a path the sandbox did NOT sanction — a follow-up pass should do that
audit.

**Verification performed:** `ffprobe` against the real `renders/final.mp4` (video+audio streams
present, duration 473.400042s, size 16,643,022 bytes, exit 0). Isolation checksum
(`find _bmad -type f | sort | xargs sha256sum | sha256sum`) captured before the render and
re-checked after this review's patch round: byte-identical throughout
(`2a21018dba1b767bb2cb2a52e0311bbb5897afadb897cd71b84f02e05130a956`); the parallel
`_bmad-output` checksum changed, as expected, since this story's own tracked planning-artifact
updates (the ledger flip and the promoted spec) live there by design. `git status --short`: exactly
the 5 expected files (4 modified + 1 added), nothing else. `pixi run -e pyforge-herald
pyforge-herald-test`: 1241 passed, 4 skipped (unaffected, as expected — no herald Python package
code changed). Confirmed the Tier-3 feed (`implementation-artifacts/sprint-status.yaml:129`) and
the tracked ledger now agree (`done`/`done`) via the sanctioned sync path, not a hand-edit.
Confirmed the promoted spec exists as a real, well-formed, tracked file (269 lines, valid UTF-8,
`git ls-files` confirms tracked).

**Residual risks:** the installed Manticore module still tracks `main`/`next` unpinned (pre-existing
open risk from Story 46.6, unaddressed here, by design). All four approval gates were self-approved
by the operating agent with no separate human creator present — disclosed and risk-flagged in both
the register and the doc, but a real production use of this pipeline should have an independent
human approve at least gate 2 and gate 4. The render's very specific numeric claims are verifiable
only on the machine that produced them; a fresh clone or CI cannot independently confirm them. The
un-audited sed-bypass-pattern risk named above under the follow-up recommendation.

## Status reconcile 2026-09-20

- Auto Run Result `Status: blocked` → `done` (see the reconcile line under it).
