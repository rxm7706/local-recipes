---
title: One container, eight stations
type: dream
owner: steward
status: realized
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

- **2026-08-10** — **Realized.** Steward Epic 7, "The one-container Guild", is **5/5 done and
  merged**, and `spec-unified-container/SPEC.md` already read `status: shipped`. The Dream's own
  frontmatter had been left at `dreamt` throughout — nobody advanced it as the chain moved,
  which is the exact rot the "no `building` state" rule exists to prevent and which had already
  bitten `pyforge-warden` and `deckcraft` on 2026-07-25. The architecture that shipped resolved
  Q1 as **one lean image**, with `pyforge-factory-full` deferred behind a named trigger ("when
  recipe builds need to run inside the container"); the ASGI stack ships as the
  `pyforge-steward[dashboard]` extra rather than a base dependency, so the container never
  carries it. Evidence: `_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md` (AD-1
  through AD-6) and steward's `sprint-status-ledger.yaml` Epic 7.
- **2026-09-09 (fleet readiness pass)** — **Built, not in effect** (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`, rows stB-B3/B4/B5/B7 / § 2.3 **C7**). Epic 7 remains 5/5 `done` and the artifacts are real (root `Containerfile`, `.dockerignore`, `scripts/container-gates`, the `pyforge-container` pixi env) — but **the image is built by nothing**: `grep -rn Containerfile .github/workflows/*.yml` matches only `src/platform/Containerfile` and the two sidecar files, `pixi.toml` contains no `docker build` / `podman build`, and the two gate tasks (`pixi.toml:556`, `:569`) appear in **no** workflow. CAP-5 is titled "the image proves itself at build time"; there is no build time. **Vessel: new steward Story 48.10** — a job or pixi task invoked by `pyforge-station-tests.yml` that builds the root `Containerfile` and runs `scripts/container-gates secrets-scan` + `container-volumes` on the result, mirroring `platform-ci.yml:305-375`, landed **before** Story 44.10 closes this repo's CI window. Two of the Spec's four open questions retire as already-decided (`uc:AD-2` one image, `ARCHITECTURE-SPINE.md:1318-1334`; baked checkout at `/pyforge` ratified, `:1291`); Q3/Q4 stay open with the named blocker that **neither Mode question is decidable until something builds the image**. Status unchanged in this pass (the batch approved the finding and the vessel, not a demotion).
