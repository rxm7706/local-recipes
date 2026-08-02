---
title: One container, eight stations
type: dream
owner: steward
status: dreamt
---

# One container, eight stations

## The Dream

All of PyForge — the eight stations, not just their planning artifacts — eventually lives in
a single Docker/Podman container. One image, one boot, the whole Guild available: Marshal
orchestrating, Atlas surfacing intelligence, Warden gating, Mason packaging, Doctor
diagnosing, Herald proclaiming, Scribe remembering, Steward provisioning. Shipping the
factory itself as a containerized solution, not just running it from a checked-out repo.

Unifying eight stations into one deployable boundary is also a forcing function: it only
works cleanly if the stations share a coherent architecture to begin with. Today (2026-08-02)
Atlas, Herald, Mason, and Marshal were each consolidated from multiple independent
brief/PRD/architecture/Spec chains — some with genuinely different tech-stack paradigms per
satellite — down to one chain per station. That consolidation is a precursor to this Dream,
not a coincidence: a single container boundary is a much saner thing to design against eight
coherent per-station architectures than against a scattered set of independently-paradigmed
satellite chains.

## What it looks like when real

- One `docker build` / `podman build` produces an image containing all 8 stations' installed
  packages (`src/shared/packages/pyforge-*`), wired the way `marshal init`/`genesis` already
  wire a bare-metal install today.
- A single entrypoint (likely `marshal`, since it's already "one composed surface" per
  [[one-front-door]]) can reach every station's CLI surface from inside the container.
- Whatever currently assumes a full git checkout + pixi environment (loop homes, the
  detector suite, the dashboard) has a containerized equivalent — or an explicit, named
  reason it doesn't need one.

## What is real

Nothing built yet. This is a `dreamt`-stage placeholder, captured explicitly to hold the idea
until the 2026-08-02 station-consolidation work (and its Dream-coverage follow-up) is on
stable ground. Owner assigned to `steward` on the reasoning that containerized deployment is
squarely its stated domain ("the estate the factory stands on — provisioning, deployment,
credential lifecycle") — reconsider if a different station turns out to be the better fit
once this gets pressure-tested via `bmad-spec`.

## Realization log

- **2026-08-02** — Dream captured. User's framing: unifying all 8 stations into one
  container is itself a reason to unify architecture first — directly motivated by the same
  session's PRD/brief/architecture/Spec consolidation across Atlas/Herald/Mason/Marshal.
