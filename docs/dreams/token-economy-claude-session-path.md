---
title: Claude spends the tokens the factory already learned to save
type: dream
owner: marshal
status: dreamt   # 2026-09-16 — operator asked for a seed after a live session
                 # found Claude still paying the uncompressed tax while Epic 28/33
                 # machinery sits on marshal dispatch and Cursor-first policy.
---

# Claude spends the tokens the factory already learned to save

## The Dream

The factory already knows how to make an iteration cheap. Five instruments
are on PATH. Marshal can wrap Claude through headroom, seed caveman, retrieve
an epic's 1,500 tokens instead of `epics.md`, and journal what each layer
saved. That kit was built so **Claude** would read less, say less, and
re-learn nothing.

The operator still opens Claude on this repo and burns a Max pool on the
old tax: `CLAUDE.md` and `AGENTS.md` every session, then unbounded file
reads, then polite prose. Dispatch, the path that *can* wrap Claude, is
pointed at **Cursor** on every station so the Claude pool stays unused —
and Cursor cannot take the wire wrap (Story 28.29). The saving exists. The
session that costs money does not use it.

The Dream is a **session path**, not a second compressor. When the operator
runs Claude — interactively or through marshal — the same kit the loop
already has actually sits on that session: wrap on the wire, caveman on
speech, retrieve/recall instead of wholesale planning docs, codegraph
instead of a tree walk. Stations that mean to spend Claude declare Claude
and turn wire on. Stations that mean to spend Cursor keep Cursor and do
not pretend the wrap applies. A pinned compare on a real Claude-wrapped
story is what makes the saving a number, not a recipe README.

> A compressor the session never launches is a story we already shipped.

## Why now — measured, not feared

Found live 2026-09-16 while asking how to use the token-economy libraries
from Claude in this repo:

| Finding | Where it is visible |
|---|---|
| Interactive Claude always loads the fat always-on docs | `CLAUDE.md` ~51 KB, `AGENTS.md` ~30 KB, MEMORY import — every fresh chat |
| All eight stations prefer Cursor | `harness_preference = ["cursor"]` in each `planning-artifacts/marshal-policy.toml` (Claude spend-limited, 2026-09-01) |
| Wire wrap is Claude-shaped and Cursor-dead | `data/harness_profiles/claude.toml` `[wrapper]`; `cursor.toml` has none (28.29) |
| Only marshal declares all five `[context]` layers | Other seven: `output` + `derived-context` + `planning-graph` only |
| Repo defaults have no `[context]` block | `_bmad-output/policy-defaults.toml` — absent means every layer off (CAP-1) |
| Parent Dream is still `specified` | [[marshal-token-economy]] is realized only when a benchmark artifact reports a measured saving — that artifact is still the missing proof |

This is not "build headroom." Headroom, caveman, codegraph, cocoindex, and
graphifyy are already pinned. Epic 28 built the seams; Epic 33 enabled
layers on marshal dispatch and rolled output/derived/planning fleet-wide.
The leftover is **which session the operator actually runs**.

## What it looks like when real

- **Claude dispatch is wrapped.** A station whose `harness_preference`
  leads with `claude` and whose `[context.wire]` is on launches
  `headroom wrap claude --code-memory none --port {wire_port} --`. A
  station that leads with `cursor` does not journal a wrap it cannot do.
- **Interactive Claude has a documented path.** The operator can start
  Claude from repo root through the same wrap, with caveman installed
  (`caveman-install --only claude`), and is told to retrieve/recall
  instead of `@epics.md`. That path is written once (Dream / Spec / a
  thin how-to), not rediscovered in chat.
- **Retrieve is the planning load.** `marshal context retrieve` and
  `scribe recall --mode planning` are what a Claude session uses for
  decisions and epic scope. Wholesale PRD / `epics.md` loads are a miss.
- **One compare exists.** `marshal benchmark compare` on a named
  Claude-wrapped story reports weighted tokens (and dollars if the catalog
  is declared) layers-on vs layers-off. The parent Dream's realized-guard
  can finally cite it.
- **No second kit.** No new compressor, no BSL caveman input proxy, no
  Serena / headroom `--memory` store beside Scribe.

## Constraints / Non-goals

- **Does not remint Epic 28 or 33.** Those stories shipped the machinery.
  This Dream names the *session that uses it*.
- **Does not claim [[marshal-token-economy]] realized.** That flip still
  waits on the compare artifact. This chain produces the Claude-legged
  run that artifact can cite.
- **Does not wrap Cursor.** 28.29 stays: wire is structurally dead there.
  Cursor Ultra remains a pool, not a headroom target.
- **Does not thin `CLAUDE.md` / `AGENTS.md` unless the Spec's open
  question says so.** The always-on doc tax is real; rewriting the
  cross-tool entry files is a different blast radius and a different
  ruling.
- **Does not flip every station to Claude by default.** Preference is an
  operator choice per station (or a dated fleet ruling). Silent
  fleet-wide flips recreate the 2026-09-01 spend scare.
- **No BSL surprises.** The caveman input proxy stays unpackaged.
- **Savings stay advisory.** No second PR gate; CAP-7 journals inform,
  they do not fail CI.

## Open questions (for `bmad-spec`, not answered here)

1. Is interactive Claude on the shared checkout a **supported** path
   (documented wrap + skill), or is the only sanctioned Claude path
   `marshal factory dispatch` / `spin`?
2. When the operator wants Claude savings, is the change **per-station**
   `harness_preference` + `[context.wire]`, or a repo-default that
   stations opt out of?
3. Does v1 include a thinner always-on doc surface for Claude Code, or
   is that a later Dream?

## Kinships

[[marshal-token-economy]] (the machinery and the realized-guard this
session path finally feeds) · [[adaptive-model-tiering]] (difficulty →
model; review floor never drops) · [[cursor-native-tier-map]] (the
Cursor-honest twin — this Dream is the Claude-honest twin) ·
[[pixi-candidate-currency]] (the five instruments' pin home) ·
[[run-state-one-publisher]] (CAP-7 savings numbers on a published run) ·
[[scribe-recall-modes]] / [[scribe-planning-pointers]] (retrieve, not
wholesale planning bodies) · [[scribe-code-navigation-owner]] (codegraph
for symbols) · [[pyforge-marshal]] (the station).

## Realization log

- **2026-09-16** — Seeded. Operator asked how to use the token-economy
  libraries from Claude and then asked for this Dream seed. Live join:
  station policies Cursor-first; only marshal has wire + structure-graph
  on; interactive Claude still pays the always-on doc tax; parent Dream
  still `specified`. Owner **marshal** (the harness profiles, `[context]`
  composition, and dispatch launch are marshal's). Next act: `bmad-spec`
  under `pyforge-marshal` after the three open questions are answered —
  do not mint an epic or flip `harness_preference` from this seed alone.
