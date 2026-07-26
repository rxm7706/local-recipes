---
title: Agent tool surface — every craft reachable through one governed API
type: dream
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

- **2026-07-25** — Dream authored, closing the last unowned part of the factory.
  The FastMCP surface was Part 3 of the `local-recipes` rebuild spec (9
  features) and had **no Dream at all** — it survived only as one bullet inside
  [[packaging-factory]]. Found while decomposing `local-recipes`, the one BMAD
  project no station owned: four of its five parts already traced to Dreams; this
  was the gap. Assigned to Marshal because the surface is operating-model
  infrastructure, not any one craft.
