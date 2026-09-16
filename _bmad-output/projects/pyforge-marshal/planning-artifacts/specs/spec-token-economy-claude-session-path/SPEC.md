---
id: SPEC-token-economy-claude-session-path
spec: token-economy-claude-session-path
status: draft
owner-dream: docs/dreams/token-economy-claude-session-path.md
covers-dreams:
  - docs/dreams/token-economy-claude-session-path.md
companions: []
surface: []
sources:
  - ../../../../../../docs/dreams/token-economy-claude-session-path.md
  - ../../../../../../docs/dreams/marshal-token-economy.md
open_questions:
  - "Is interactive Claude on the shared checkout a supported path (documented wrap + caveman skill), or is the only sanctioned Claude path marshal factory dispatch / spin?"
  - "When the operator wants Claude savings, is the change per-station harness_preference + [context.wire], or a repo-default that stations opt out of?"
  - "Does v1 include a thinner always-on doc surface for Claude Code (CLAUDE.md / AGENTS.md), or is that a later Dream?"
---

> **Canonical contract (draft).** This SPEC is the seed contract derived from the
> Dream. It stays `draft` until the three `open_questions` are answered and
> `bmad-spec` re-derives it to `ready`. Do not hand-edit after that re-derive —
> append `.memlog.md` instead.

# SPEC — Claude spends the tokens the factory already learned to save

## Why

Epic 28 and Epic 33 built and enabled a context pipeline so a Claude-backed
iteration would read less, say less, and re-learn nothing. The operator's
Claude sessions still pay the uncompressed tax: always-on repo docs, Cursor-first
`harness_preference` on every station (so `headroom wrap claude` never launches),
and wire structurally unavailable on Cursor (28.29). This Spec names the
**session path** that puts the existing kit on a Claude run. It does not mint a
second compressor.

## Capabilities

- **CAP-1 — a documented Claude session path uses the kit.**
  - **intent:** An operator starting Claude — on the sanctioned path the open
    questions select — launches through the existing wrap/seed/retrieve
    surfaces, not a bare `claude` that re-discovers the repo.
  - **success:** The path is written once and followed; a session on that path
    is demonstrably wrapped or seeded according to the declared `[context]`
    layers; wholesale `epics.md` / PRD loads are a miss against retrieve/recall.
- **CAP-2 — Claude-preferring dispatch actually wraps.**
  - **intent:** A station that leads `harness_preference` with `claude` and
    enables `[context.wire]` launches the `claude.toml` `[wrapper]`. A station
    that leads with `cursor` does not journal a wrap it cannot perform.
  - **success:** Rendered-launch diff shows `headroom wrap claude` iff both
    conditions hold; Cursor-first stations stay honest (28.29).
- **CAP-3 — wire (and structure-graph) are declared where Claude is spent.**
  - **intent:** Stations that drain on Claude declare the layers that only
    Claude can use. Stations that stay on Cursor keep output / derived /
    planning and do not fake wire.
  - **success:** No station journals `wire` enabled on a Cursor-only preference;
    at least one Claude-preferring station declares `[context.wire]`.
- **CAP-4 — one Claude-legged compare exists.**
  - **intent:** `marshal benchmark compare` runs on a named story launched
    through the Claude wrap, layers on vs off.
  - **success:** The artifact reports weighted tokens (and dollars if the
    catalog is declared). [[marshal-token-economy]] may cite it; this Spec
    does not flip that Dream to `realized`.

## Constraints

- Do not remint marshal Epic 28 or 33.
- Do not wrap Cursor; do not package the BSL caveman input proxy.
- Do not enable headroom `--memory` or Serena code-memory (Scribe owns recall).
- Do not fleet-flip `harness_preference` without an operator ruling on OQ 2.
- Savings telemetry stays advisory (no second PR gate).
- Thinning `CLAUDE.md` / `AGENTS.md` is out of v1 unless OQ 3 says otherwise.

## Success signal

A Claude session the operator actually runs — dispatch or the documented
interactive path — uses the kit already on PATH, and one compare artifact
measures it. The parent token-economy Dream remains the realized-guard.
