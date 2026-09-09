---
title: Scribe reaches past curated memory into the raw session transcripts underneath it
type: dream
owner: scribe
status: realized   # 2026-09-09 — Epic 3 (3.1 scanner, 3.2 compile source, 3.3 bounds+schedule) all `done` and the criterion is EXERCISED: .claude/data/pyforge-scribe/transcript-scan-cache.json is the artifact only a real scan produces. Was `specified` (2026-08-22 — spec + station decomposition landed same day).
---

# Scribe reaches past curated memory into the raw session transcripts underneath it

## The Dream

Scribe already promotes personal memory into the team's shared knowledge: `scribe capture
--promote` (Story 1.3, shipped) scans a contributor's **curated** personal auto-memory
(`~/.claude/projects/<repo>/memory/*.md`) and proposes team-relevant entries for
`.claude/memory/`. That closes one gap. It leaves a deeper one open: curated memory is
itself a filter — only what an agent judged worth writing down, in the moment, survives
into it. Everything discussed in a session but never promoted even to *personal* memory —
an idea floated and dropped, a design considered and rejected, a fact mentioned once in
passing — exists only in that session's raw transcript, and nothing scans those.

Confirmed live, 2026-08-15: this repo's own personal-memory directory holds 22 raw session
transcripts (`.jsonl`, 161MB total) alongside its curated `.md` files. Every one of those
transcripts is a superset of whatever got curated from it. Scribe's own planned Epic 2
knowledge-graph compile sources (per this Dream's own text: "git history, memlogs, retros,
CHANGELOGs, `docs/dreams/`") don't currently name these transcripts either — so even the
NEXT layer of Scribe, once built, would still miss this. The mechanism to recover from them
already exists as precedent, just not as a systematized capability: CLAUDE.md's own "Story
specs are durable" recovery-source hierarchy names Claude Code session transcripts as the
highest-fidelity recovery source, and it is how pyforge-warden's 13 lost story specs were
actually recovered verbatim on 2026-07-25 — proof the raw signal is real and recoverable,
done once by hand, never generalized.

## Whose job this is

Squarely Scribe's, by its own already-written charter — no investigation needed the way
[[bmad-method-core-upgrade]] needed one. Scribe's Dream states outright: "what the team
knows, every agent and every session knows... knowledge is lossy; the graph is there;
nobody writes it down." A raw session transcript IS exactly the un-written-down knowledge
that Dream already claims as its territory; this is a depth extension of `scribe capture
--promote`'s already-shipped mechanism (mine one layer deeper) and a new named source for
the not-yet-built Epic 2 compile step, not a new station or a new charter.

## What it looks like when real

- `scribe capture --promote` (or a sibling verb) gains a mode that scans raw session
  transcripts, not just curated personal memory — proposing candidate team-relevant facts
  it finds THERE that never made it into a curated entry, with the same proposal-then-
  confirm discipline the existing promote path already uses (never silently promotes).
- Epic 2's compile step, when built, lists session transcripts as a named source alongside
  git history/memlogs/retros/CHANGELOGs — so `scribe recall` can eventually answer "what did
  we discuss about X" even when X was never curated by any agent in the moment.
- A contributor (human or agent) can ask "did we already talk about this" and get a real
  answer grounded in what was actually said, not just what someone remembered to write down
  — closing the exact loss mode [[sentinel]] originally diagnosed, at the layer underneath
  where Scribe currently stops.

## What is real

**Built and exercised** — *corrected 2026-09-09 (fleet readiness pass); the superseded
2026-08-15 reading was "Nothing yet. `scribe capture --promote` (Story 1.3) is real but scoped
to curated personal memory only. Epic 2 (the knowledge graph this would extend) is entirely
backlog — 4 of 4 stories, untouched."*

`transcripts.py` (506 lines) mines raw `.jsonl` sessions for un-curated decisions and routes
every candidate through `promote.py`'s proposal-then-confirm gate; `compile.py` carries the same
scan as a named sixth surface (`compile.py:114-117`, `:174-196`), with `transcript:` provenance
citations. Epic 2 is `done` (4/4) and Epic 3 is `done` (3/3). Proof of a real run:
`.claude/data/pyforge-scribe/transcript-scan-cache.json`, alongside a 1.67 MB `graph.json`.

The live surface has outgrown this Dream's own measurement — **27 files / 631 MB** as recorded
for DW-FU-3-2-2, not the "22 files / 161 MB" quoted above and in § *The Dream* — which is
exactly why Story 3.3 added a file-count cap, a total-byte budget (newest files first) and a
per-file timeout before putting the scan on the unattended nightly path.

## Constraints

- Air-gapped by construction, same as the rest of Scribe — no outbound calls, matching the
  existing capture/compile/recall discipline.
- Must not raw-dump transcript content into team memory — 161MB of tool-call noise across
  22 sessions needs the SAME curation discipline the existing `--promote` path already has
  (propose, don't silently promote; team-voice rewrite; provenance citation), not a bigger,
  noisier version of the same problem it's trying to solve.
- Provenance matters more here, not less — a fact recovered from a raw transcript needs to
  cite which session/turn it came from, the same way the existing mechanism's "every graph
  node traces back to the source file or commit" already requires for committed sources.

## Non-goals

- Not re-scoping Epic 1/2's own already-planned sequencing — this is a new source for the
  SAME planned compile step, not a reason to reorder Scribe's existing backlog.
- Not a real-time/live transcript-watching capability — mining PAST transcripts (a sweep,
  or an on-demand `--promote`-style scan), not live capture during an active session (that's
  what `scribe capture` already does, from the agent's own in-session judgment).

## Kinships

[[pyforge-scribe]] (owner, the charter this Dream extends) · [[pyforge-scribe-team-memory]]
· [[sentinel]] (the original knowledge-loss diagnosis this closes one more layer of) ·
[[dashboard-velocity-captures-hand-driven-work]] / [[bmad-method-core-upgrade]] (captured
the same session this gap itself was noticed, from the same underlying observation: things
discussed but not carried forward).

## Realization log

- **2026-08-15** — Dream captured. Surfaced when the user asked how to scan across all
  prior Claude session memory for pyforge-related content, noting conversational ideas get
  lost when not explicitly saved. Investigation confirmed raw transcripts exist and are
  greppable (22 files, 161MB, this repo's own personal-memory directory) but nothing scans
  them systematically — `scribe capture --promote` only reaches curated personal memory, one
  layer up from where this gap actually lives. Folded into Scribe's own territory per the
  user's explicit direction, rather than treated as a one-off sweep.
- **2026-09-09 (fleet readiness pass — REALIZED)** — `specified → realized`. Epic 3 closed 3/3
  and the criterion is *exercised*, not merely built: the scanner has actually run against this
  machine's transcript store, and `.claude/data/pyforge-scribe/transcript-scan-cache.json`
  (10 KB, 2026-08-27) is the artifact only a real scan produces. The Spec's one open question —
  "incremental by transcript mtime **vs** full sweeps" — was answered as **both**: an
  mtime+size-keyed cache for the incremental half and a triple bound (file-count cap, byte
  budget selecting newest-first, per-file timeout) for the sweep half, sized against the live
  27-file / 631 MB surface rather than this Dream's stale 22-file / 161 MB figure
  (`transcripts.py:25-43`). `spec-scribe-mines-raw-session-transcripts` moves `ready → shipped`
  in the same pass. **One contract collision surfaced and is proposed for amendment upstream:**
  `spec-pyforge-scribe`'s Non-goal — "Scribe never passively mines chat logs, Slack, **or
  session transcripts** for decisions … permanently" — reads as a blanket prohibition this
  Dream's shipped work contradicts; the distinction that actually holds is *ambient* vs
  *deliberate-and-human-gated*, and the Non-goal should be re-worded to say so rather than left
  to be read as a live veto. Recorded on that Spec's memlog this date. **Residual:** the scan is
  invoked by hand — the unattended path exists but no schedule is installed, so "routine
  promotion sweeps" in the Success signal is still aspirational; vessel is scribe **Epic 8**
  (fleet-readiness decision batch 2026-09-09, row C6).
