---
title: A BMAD write can never land in the wrong project's artifacts, mechanically
type: dream
owner: marshal
status: specified
---

# A BMAD write can never land in the wrong project's artifacts, mechanically

## The Dream

Every BMAD skill that writes planning artifacts resolves through two gitignored
compatibility symlinks (`_bmad-output/planning-artifacts`, `_bmad-output/implementation-artifacts`)
that must agree with the `.active-project` marker and with whatever project the caller actually
intended. Today that agreement is checked two different ways in two different places, and both
checks stop short of the one guarantee that actually matters: that a write lands in the project
the caller meant to write to.

`scripts/bmad-switch --current` (repo root) warns on marker/symlink disagreement, but the
warning is advisory — it's stderr text, the exit code stays 0, and nothing calls it automatically
before a write. Marshal's own ported copy (`cli/init.py`'s `MRS-INIT-003` check, provisioning a
loop home) is stricter — it hard-fails a home's `marshal init` when the marker and symlinks
disagree — but Story 1.4's own adversarial review found it checks the wrong pair: marker-vs-symlink
internal agreement, never marker-vs-*the slug the caller actually asked for*. A home whose marker
and symlinks consistently agree on the WRONG project — silently repurposed by some earlier `bmad-switch`
call, a stale worktree, or (per the live 2026-07-25 fan-out incident) a second concurrent agent
racing the same shared marker — sails through both checks clean and gets silently reconciled onto
the new target with no warning it was ever pointed elsewhere. The dream is a single verification
primitive, shared by the repo-root script and Marshal's ported copy, that checks the ONE thing
that actually matters — "does this resolve to the slug I asked for, right now" — hard-fails loud
when it doesn't, and gets called automatically at every write boundary instead of only when someone
remembers to run `--current` by hand.

## What it looks like when real

- One shared verification function — `verify_scope(root, expected_slug) -> None | ScopeDrift` —
  used by both `scripts/bmad-switch` and Marshal's `cli/init.py`, replacing today's two divergent,
  partial checks with one. It compares the marker, both symlink targets, AND the caller's
  `expected_slug` in one pass, closing DW-1-4-2's blind spot (2): a home whose marker and symlinks
  agree with EACH OTHER but not with the requested slug is now a drift, not a silent pass.
- Symlink-target parsing recognizes more than the exact `projects/<slug>/planning-artifacts`
  shape (closing DW-1-4-2's blind spot (1)) — an absolute path or a target written by different
  tooling is reported as "unrecognized," never silently treated as agreement.
- `bmad-switch --current` (and any BMAD write-skill's own preflight) exits non-zero on drift,
  not just stderr text at exit 0 — a scripted caller (or a parallel agent doing its own
  `readlink -f` discipline today, per this repo's own auto-memory) gets a real signal instead of
  having to parse warning text.
- The check is cheap enough (three file reads, no subprocess) to run before every write-skill
  invocation without meaningfully slowing anything down — closing the actual gap the 2026-07-25
  incident exposed: the switch is a mutex nobody holds, and today's mitigation is "the agents
  checked," which is discipline, not enforcement.

## What is real

Substantial prior art already exists and this Dream does not start from zero:

- **2026-07-14**: `scripts/bmad-switch` was fixed to write the marker LAST, after symlinks
  re-point successfully, so a failed re-point can no longer leave the marker disagreeing with the
  links (the 10h pyforge-warden near-miss this fixed is `bmad-switch`'s own docstring history).
- **Story 1.4** (`pyforge-marshal`, already shipped) ported this into `cli/init.py` as the
  `MRS-INIT-003` guard for loop-home provisioning — stricter than the repo-root script (hard
  exit, not just a warning), but scoped only to init-time, and only to internal marker/symlink
  agreement.
- **DW-1-4-2** (`pyforge-marshal`'s own deferred-work ledger, found during Story 1.4's
  adversarial review) already names both blind spots this Dream closes, and already says the
  fix "needs a product decision" — this Dream is that decision.
- **CLAUDE.md**'s standing rule ("PARALLEL AGENTS: never touch the switch — address projects by
  physical path... pass `BMAD_ACTIVE_PROJECT` per invocation") is today's operational workaround:
  agents are told to avoid the shared mutex rather than the mutex being made safe to share.
- **The 2026-07-25 fan-out incident** (5 concurrent agents running `bmad-switch`, the shared
  symlink observed moving `pyforge-doctor → pyforge-marshal → pyforge-mason → deckcraft` mid-run)
  is the concrete evidence this class of bug is not hypothetical — it was caught only because
  every agent independently ran `readlink -f` and noticed.
- Distant prior art: a sibling org's `bmad-workspace-integration` dream (`wf-dev-cli`'s
  `extensions/bmad.py`, 650 LOC) does a related but broader thing — automatic switch-on-workspace-open
  plus checkpoint stash/restore plus scope.yml path-boundary enforcement. That dream's automatic-switch
  trigger depends on a workspace-management capability ([[developer-workspace-management]]-shaped)
  this repo doesn't have yet; its `checkpoint` verb has no documented local pain point. This Dream
  deliberately scopes down to only the piece with a real, already-bitten, already-triaged local gap.

## Constraints

- **One verification function, not two.** `scripts/bmad-switch` and Marshal's `cli/init.py` must
  call the SAME logic, not maintain parallel copies that can drift from each other the way the
  current two checks already have.
- **Hard-fail, never a warning that can be ignored.** The whole point is replacing discipline
  ("the agents checked") with enforcement; a check that only prints to stderr at exit 0 does not
  close this gap, it just documents it more visibly.
- **Cheap enough to call on every write, not just at init/switch time.** Three file reads and a
  string compare — no subprocess, no network — so wiring it into a write-skill's preflight is
  free, not a tax anyone will disable under load.

## Non-goals

- **Not automatic switch-on-workspace-open.** That trigger needs a workspace-management capability
  this repo doesn't have; wiring it in without that capability existing would be speculative.
- **Not a `checkpoint`-style stash/restore of AI session work.** No documented local pain point
  motivates it; bmad-loop's own `keep_failed` patch-preservation already covers the adjacent
  "don't lose work on failure" concern for loop-driven stories.
- **Not a general `scope.yml` path-boundary enforcer** for arbitrary file writes outside BMAD
  artifacts — this Dream is scoped to the marker/symlink/expected-slug triangle specifically.
- **Not re-litigating whether Marshal should own `bmad-switch`'s source** — `spec-pyforge-marshal`
  already states this ("Marshal owns the source of `scripts/bmad-switch`... Genesis owns their
  delivery as COPIED·MANAGED artifacts"); this Dream operates inside that already-decided boundary.

## Kinships

[[bmad-module-provisioning]] (the other realized BMAD-infra Dream owned by a non-Marshal station,
useful as a format precedent) · [[pyforge-marshal]] (the estate; DW-1-4-2 already lives in its own
deferred-work ledger, found during Story 1.4's adversarial review) · [[genesis-installer]] (the
delivery-vs-source boundary this Dream operates inside, per `spec-pyforge-marshal`'s own SPEC.md) ·
[[scratch-worktree-lifecycle]] (a Steward-owned scratch worktree opened against a specific BMAD
project is exactly the caller this Dream's `verify_scope` primitive was designed for — cross-station
kinship, not a merge)

## Realization log

- **2026-08-14** — Dream captured. Surfaced while evaluating a sibling org's `bmad-workspace-integration`
  dream as a PyForge candidate; investigation found the broader dream's automatic-switch and
  checkpoint pieces lack local justification, but its core "verify before write" concern maps
  directly onto an already-open, already-triaged gap in `pyforge-marshal`'s own deferred-work
  ledger (DW-1-4-2, found during Story 1.4's adversarial review, explicitly awaiting "a product
  decision"). Scoped down to just that gap. Owner assigned to `marshal` per `one-front-door.md`'s
  own multi-project-wiring ownership survey and `spec-pyforge-marshal/SPEC.md`'s explicit
  "Marshal owns the source of `scripts/bmad-switch`" statement — not Steward, despite most other
  BMAD-infra Dreams in this repo defaulting there.
- **2026-08-14** — Spec authored (spec-bmad-switch-scope-enforcement, pyforge-marshal) by the 2026-08-14 dream-backlog audit: one shared verify_scope primitive consumed by bmad-switch and cli/init.py, closing DW-1-4-2's product-decision hook.
