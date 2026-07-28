---
title: Agent tool surface — every craft reachable through one governed API
type: practice
owner: marshal
status: realized
---

# Agent tool surface — the factory, callable

## The Dream

**Every capability the factory has is reachable by an agent through one
governed, typed surface** — not a pile of bespoke integrations, and not a set of
powers only a human at a shell can invoke. A Smith should be able to ask for a
recipe's vulnerabilities, a feedstock's health, or a project's dependency
closure the same way it asks for anything else: a named tool, a typed argument,
a structured answer.

This is Marshal's reach, not Mason's or Atlas's. The *tools* belong to the
crafts — 21 recipe-authoring, 21 atlas-intelligence, 2 project-scanning, 2
infrastructure — but **the surface belongs to the operating model**: it is how
any agent reaches any craft, which is the same concern as
[[agent-portability]] ("runs on whichever agent") viewed from the other side.
Splitting it by craft would leave the surface itself ownerless, which is exactly
how it went unnoticed for so long.

## What exists

- **`.claude/tools/conda_forge_server.py`** — the legacy FastMCP server, **46
  tools** over stdio, each a thin subprocess wrapper over the Tier-1 scripts so
  the CLI and the tool surface can never diverge.
- **`pyforge-atlas`'s own 11-tool FastMCP server** — additive, not a
  replacement. The factory now runs **two** servers.
- Registration is **manual**, in `~/.claude.json` under
  `mcpServers.conda_forge_server`, with machine-absolute paths into
  `.pixi/envs/local-recipes/`. There is deliberately no `.mcp.json` in the repo.

## Coverage — measured 2026-07-28

The Dream's headline is *"every capability the factory has is reachable."* Measured
against the eleven realized Dreams, it holds for **two stations of six**:

| Station | Realized capability | On the governed surface |
|---|---|---|
| mason | packaging-factory · fleet-stewardship | ✅ 21 tools |
| atlas | pyforge-atlas | ✅ 21 tools |
| warden | pyforge-warden | ⚠️ 2 scanning tools — `warden scan` itself is CLI-only |
| herald | design-code-bridge · modernist-identity | ❌ 0 — the bridge runs on an **external** MCP the factory does not govern |
| steward | enterprise-airgap | ❌ 0 |
| marshal | agent-tool-surface · factory-console · pyforge-marshal · regenerable-factory | ❌ 0 — bmad-loop and dashboard-gen are CLI / pixi tasks |

**Marshal, which owns this practice, has none of its own capabilities on it.** That is
the sharpest evidence for the reclassification to `type: practice` (2026-07-28): a
surface at 2-of-6 coverage is not a finished thing that shipped, it is a standing
concern that is tended. The 46 + 11 tools are real; *"every capability"* is not yet true.

Herald's case is the most interesting: `design-code-bridge` is **realized** and works —
through `claude-design`, an MCP registered outside the repo. So the capability is
reachable by an agent but not through *one governed* surface, which is the half of the
promise that fails silently.

## Enforcement — who ensures no drift

These three Marshal practices — this one, [[agent-portability]] and
[[agentic-sdlc-autonomy]] — are **cross-cutting**: owned by one station, binding on all
eight. Every other gate in the repo is vertical (each station's suite checks its own
code). Nothing checked horizontally, which is why the coverage table above went
unmeasured until now.

The model, using the Charter's existing split of *ownership* from *verdict*
(§5: "the hand that builds is never the gate that judges"):

1. **Marshal detects** — the horizontal checks live in Marshal's own detectors, rolled up
   **by owner**, exactly as `dream_chain_check.py` already does.
2. **Each station remediates its own row** — ownership never moves; a finding against
   Herald is Herald's to close.
3. **Doctor holds the verdict on Marshal's row** — the one station that would otherwise
   grade itself. This is Doctor's standing mandate ("continuously monitor … diagnose …
   prescribe"), and it mirrors existing precedent: *the `JFROG_API_KEY` leak was a
   Steward remediation, on a Doctor finding.* Detection and remediation already separate
   across stations there.
4. **The Guildhall gates** — Charter §7 as amended: it refuses to publish a row it cannot
   attribute. Accountability made real, not merely rendered.

**Ratified 2026-07-28** (Charter §6, Realization log). Warden was considered and is **not**
the answer — and the reason is **craft, not scope**. Warden's craft is dependency and
security judgment; process conformance is a different craft, which stays true however
general Warden's ecosystem coverage becomes. Its present Python-only reach is
implementation scope, not mandate. Doctor's mandate already covers conformance drift as a
health signal, and §4 governs: *each works one craft, not all.*

**Governance is kept separate.** The Marshal may not weaken, re-threshold or disable a
check that judges the Marshal. A conformance gate is amendable by its subject only through
the Doctor's verdict — the same rule that stops Mason passing its own build by lowering
Warden's bar. Without that clause the model would be self-grading with extra steps, since
Marshal owns the detectors.

## The frontier

- **Two servers, no governing decision.** The second arrived with
  [[pyforge-atlas]]'s rebuild and is additive by accident rather than by design.
  Whether the surface federates, merges, or stays split is an open architectural
  question that this Dream now owns.
- **A fresh clone has zero tools.** Manual `~/.claude.json` registration means
  the surface does not survive a clone — the sharpest gap between "the factory
  is regenerable" ([[regenerable-factory]]) and what a new machine actually
  gets.
- **Machine-absolute paths** in that registration are the same portability
  defect [[agent-portability]] exists to kill.
- No typed contract test asserts CLI ⇄ tool parity; the thin-wrapper pattern is
  a convention held by review, not by a gate.

## Kinships

[[agent-portability]] (the same concern from the agent's side — Marshal's other
half) · [[regenerable-factory]] (a surface that needs hand-registration is not
yet regenerable) · [[packaging-factory]] (Mason's craft, which this surface
exposes — it carried this Dream as a single bullet until 2026-07-25) ·
[[pyforge-atlas]] (Atlas's craft, and the second server) ·
[[enterprise-airgap]] (the surface must resolve behind a firewall too).

## Realization log

- **2026-07-28** — reclassified `type: dream` → **`practice`**. The surface is never
  finished: every new craft capability adds tools, so it is tended, not shipped. Measured
  coverage the same day put the *"every capability"* claim at **2 stations of 6** — with
  Marshal, the practice's own owner, at zero. Enforcement model recorded (Marshal detects ·
  stations remediate · Doctor judges Marshal's row · the Guildhall gates, per the Charter §7
  amendment). The three cross-cutting Marshal practices had no horizontal check of any kind
  until this date; every gate in the repo was vertical, which is exactly how a 2-of-6
  surface went unnoticed inside a Dream marked `realized`.

- **2026-07-25** — Dream authored, closing the last unowned part of the factory.
  The FastMCP surface was Part 3 of the `local-recipes` rebuild spec (9
  features) and had **no Dream at all** — it survived only as one bullet inside
  [[packaging-factory]]. Found while decomposing `local-recipes`, the one BMAD
  project no station owned: four of its five parts already traced to Dreams; this
  was the gap. Assigned to Marshal because the surface is operating-model
  infrastructure, not any one craft.
