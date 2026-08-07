---
title: Atlas's own Kedro tooling gap — skills, viz publishing, IDE integration
type: dream
owner: atlas
status: dreamt
---

# Atlas's own Kedro tooling gap — skills, viz publishing, IDE integration

## The Dream

Kedro is used exclusively (`pyforge-atlas`'s own pipeline stack) but three of the Kedro
organization's own tools that would strengthen how that pipeline gets built and shown are
adopted nowhere: [`kedro-skills`](https://github.com/kedro-org/kedro-skills) (distributes
Kedro-editing AI guidance into `.claude/skills/`/`AGENTS.md`/`.cursor/rules/`),
[`publish-kedro-viz`](https://github.com/kedro-org/publish-kedro-viz) (a GitHub Action that
auto-builds and deploys Kedro-Viz to GitHub Pages on push), and
[`vscode-kedro`](https://github.com/kedro-org/vscode-kedro) (a VS Code extension: pipeline
navigation, dataset/param autocomplete, catalog validation, embedded Kedro-Viz, node
debugging).

A fourth, [`kedro-mcp`](https://github.com/kedro-org/kedro-mcp), was checked and found
already resolved — pinned (`pixi.toml`), genuinely wired into `pyforge.atlas.mcp.server`,
with its own `test_kedro_mcp_absent.py` graceful-degrade test, per a deliberate 2026-07-16
domain-research decision ("wrapped where its guidance scope helps, never load-bearing," FR-7).
Not part of this Dream's scope.

**Owner is `atlas`, not `steward`, deliberately** — investigated directly, not assumed.
The *mechanism* each of the remaining three needs already belongs to Steward:
`kedro-skills` needs the exact provisioning duty [[bmad-module-provisioning]] just proposed
(install a third-party AI-skill package non-interactively, reproducibly); `publish-kedro-viz`
needs exactly the shape `steward deploy dashboard` (Epic 2) already ships — build an
artifact, commit/push it to a GitHub-Pages-published location. But *which* Kedro skills are
actually correct against this repo's real pipelines, whether the viz's default output even
matches what atlas's own DAG looks like, and whether the IDE integration is worth adopting
given this repo is agent-edited far more than hand-edited — those are judgment calls only
the station that owns the Kedro pipelines can make. Per [[unity-data-stack]]'s own precedent
(Atlas owns that Dream without it shipping as `pyforge-atlas`), owning is the accountable
post, not a claim on the product.

## What it looks like when real

- `kedro-skills install <skill-id>` has been run against `pyforge-atlas`'s own Kedro project,
  the generated `.claude/skills/`/`.agents/skills/`/`AGENTS.md` content reviewed for
  accuracy against the real pipeline (not installed blind), and provisioned reproducibly —
  via [[bmad-module-provisioning]]'s own mechanism once it ships, or by hand if that Dream
  hasn't landed yet, but never by an undiscoverable one-off driver script (the same anti-
  pattern [[bmad-module-provisioning]] itself was captured to close).
- `publish-kedro-viz` runs in CI on every push touching `pyforge-atlas`'s pipeline code,
  publishing a live, always-current DAG view to GitHub Pages — replacing (or standing
  alongside) the existing MANUAL capture tasks (`kedro-viz-proto`, `capture-kedro-viz-proto`
  → static PNGs/HTML gallery), the same way `docs/dashboard/` is already auto-published
  rather than hand-regenerated.
- A documented, explicit decision exists on `vscode-kedro` — adopted (with a
  `.vscode/extensions.json` recommendation) or explicitly deferred with a stated reason
  (e.g. "this repo's Kedro code is edited almost exclusively by agents, not humans in VS
  Code") — not silently never-considered the way all three were before this Dream.

## What is real

Nothing built yet. This is a `dreamt`-stage placeholder, captured the moment the gap was
found (alongside the [[bmad-module-provisioning]] gap, same investigation) — the next step
is a Spec (`bmad-spec`), not code. `kedro-mcp`'s own already-resolved status (see above) is
recorded here so a future pass doesn't re-open a question already answered.

## Constraints

- **Wait for [[bmad-module-provisioning]] where the mechanism overlaps.** `kedro-skills`
  provisioning should not hand-roll a second one-off installer script while that Dream's own
  reproducible-provisioning mechanism is in flight — if it lands first, use it; if this Dream
  moves first, its own provisioning story should be written so `bmad-module-provisioning`
  can adopt it as a precedent, not a competing implementation.
- **Review before installing.** `kedro-skills`' generated guidance must be checked against
  `pyforge-atlas`'s real pipeline shape before being committed — it is AI guidance content,
  not a mechanical install-and-forget dependency.

## Non-goals

- Not re-evaluating `kedro-mcp` — already resolved, already wired, already deliberately
  scoped (FR-7, "wrapped, never load-bearing").
- Not deciding `vscode-kedro` in advance — this Dream requires the decision be made and
  recorded, not any particular outcome.

## Kinships

[[pyforge-atlas]] (the pipeline this tooling serves) · [[pyforge-steward]] (the provisioning/
deployment mechanisms this Dream's execution leans on) · [[bmad-module-provisioning]] (the
sibling gap found in the same investigation; `kedro-skills`' own provisioning is a direct
instance of that Dream's own problem statement).

## Realization log

- **2026-08-07** — Dream captured. Surfaced when the user asked why `kedro-mcp`,
  `kedro-skills`, `vscode-kedro`, and `publish-kedro-viz` weren't in use despite Kedro being
  the exclusive data-pipeline stack. Investigation found `kedro-mcp` already resolved (pinned,
  wired, deliberately scoped by 2026-07-16 domain research) and the other three genuinely
  absent everywhere. User asked for holistic ownership reasoning rather than a default pick;
  resolved as owner `atlas` (the domain knowledge these tools need is Atlas's own) with
  Steward named as the mechanism dependency for two of the three (provisioning, deployment)
  rather than the owner.
