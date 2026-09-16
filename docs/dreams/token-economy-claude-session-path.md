---
title: Claude spends the tokens the factory already learned to save
type: dream
owner: marshal
status: archived   # 2026-09-16 — folded into [[marshal-token-economy]] (operator-ruled
                   # token-savings consolidation: one starting point). Was `dreamt`;
                   # seeded the same day. Its Spec stays live and re-derives against
                   # the parent Dream.
---

# Claude spends the tokens the factory already learned to save

> **Consolidated into [[marshal-token-economy]] on 2026-09-16** (§ *Fold
> (2026-09-16) — the token-savings Dreams come home*). This file is archived in
> place. Its Spec folded too (operator ruling: no satellite Specs) —
> `spec-token-economy-claude-session-path` is `superseded`, its capabilities
> re-minted as `spec-marshal-token-economy` **CAP-19..CAP-24**, dispatch home
> marshal Epic 46; the superseded folder keeps the eleven-entry decision
> memlog. Kept, not deleted, so the reasoning stays readable.

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

## Why this Dream widened — the 2026-09-16 analysis

Seeded as "Claude pays the uncompressed tax," the Dream went through a
deep analysis and adversarial review the same day, and the operator named
its center: **the biggest gap is sharing cache, knowledge, and memory
across every agent, harness, and model.** Three conclusions now shape the
Spec, recorded here so the reordering can be revisited at the aspiration
level:

- **Token savings is not one currency.** Claude meters billed tokens
  (with prompt-cache discounts); Cursor meters subscription quota;
  Copilot meters premium requests; Gemini meters rate limits; Devin
  meters ACUs. A layer that helps one currency can be irrelevant to
  another — wire compression is dollars on Claude, unreachable on
  Cursor, quota headroom on Copilot. Every saving gets reported in its
  harness's own currency, never one blended number.
- **The five layers are two economies.** The shared substrate —
  codegraph, cocoindex distills, the planning graph, team memory —
  amortizes understanding *once* and serves every harness. The
  per-harness wire (headroom, caveman) is the secondary,
  capability-bound residue. The substrate is primary: compression
  optimizes the marginal turn; the substrate eliminates whole categories
  of turns (the 65k-token `epics.md` re-read is the emblem).
- **The substrate's gaps are named.** It does not *travel* (cloud agents
  get a bare clone — no bootstrap path exists); *write-back* is
  harness-fragmented (`scribe capture` is the neutral ritual, habitual
  in no harness); the only portable cache is a canonical, digest-pinned
  context bundle (prefix stability), not a shared provider cache; and
  *freshness* is the trust boundary (Scribe owns it; the SLA holds).
  Centralizing knowledge also centralizes error — provenance (Scribe
  never answers uncited), the freshness SLA, and capture hygiene (no
  secrets, decision-grade facts only) are the mitigations, stated here
  so they survive the substrate becoming the default.

The review also corrected the record: output compression is multi-harness
(caveman ships 21 targets — copilot, cursor, gemini, devin among them),
and the sharpest open risk is the **prompt-cache collision** — a wire
compressor that rewrites prefixes unstably can cost more in lost cache
discounts than it saves in tokens. Claude wire savings stay *unverified*
until per-layer benchmark legs with cache-hit reporting exist.

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
- **2026-09-16 (analysis)** — Deep analysis + adversarial review; full
  detail in the Spec memlog (entries 4–10). All three open questions
  answered: dispatch is the *measured* path, interactive a documented
  convenience path on the same instruments; repo-default `[context]`
  with wire as a capability-aware `"auto"`; doc thinning deferred to a
  later Dream. Multi-harness matrix ruled (claude full kit; copilot full
  kit pending one `[wrapper]` story; cursor harness-agnostic only —
  intended economics, not a gap; cloud agents bounded by the instruction
  surface). Caveman correction: the output layer is multi-harness.
  Substrate-primary reordering with four named gaps (travel, write-back,
  canonical bundle, freshness) and the centralization caveat — see
  § *Why this Dream widened* above. The re-derive should mint: the
  front-door CAP, the silent-saves CAP (tri-state, journal taxonomy,
  per-currency rollup, persistence advisory), the copilot `[wrapper]`
  story, the substrate CAP (bootstrap, write-back ritual, canonical
  bundle, freshness SLA), and per-layer benchmark legs with cache-hit
  rates.
- **2026-09-16 (fold)** — Folded into [[marshal-token-economy]] (operator-ruled
  token-savings consolidation) and archived in place, the same day it was
  seeded. Prior status: `dreamt`.
- **2026-09-16 (Spec fold)** — The operator ruled no satellite Specs, so the
  contract folded too: `spec-token-economy-claude-session-path` is
  `superseded`, its capabilities re-minted as `spec-marshal-token-economy`
  CAP-19..CAP-24, dispatch home marshal Epic 46 (46.1–46.10). The superseded
  folder keeps the eleven-entry decision memlog (OQ answers, multi-harness
  matrix, adversarial review, substrate-primary reordering).
