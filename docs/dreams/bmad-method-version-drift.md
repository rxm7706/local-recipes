---
title: Doctor notices when BMAD-METHOD's own installed core falls behind upstream
type: dream
owner: doctor
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-doctor]]** on 2026-09-17 (one-chain-per-station doctor fold).

# Doctor notices when BMAD-METHOD's own installed core falls behind upstream

## The Dream

Doctor already reports staleness for everything else this fleet depends on — feedstocks
behind upstream, dependency floors behind CVE fixes, artifacts behind their own baseline.
It says nothing today about BMAD-METHOD itself: whether the fleet's declared dependency
floor and its actually-installed `_bmad/bmm/**`/`_bmad/core/**` content agree, or how far
behind the latest upstream release either one is. An operator finds out only by noticing —
the way this Dream's own sibling, [[bmad-method-core-upgrade]], got captured: because the
user happened to remember to check.

The Dream is a standing Finding, wired into Doctor's existing Source/Finding registry the
same way `behind-upstream` already reports stale feedstocks: `pixi.toml`'s declared
`bmad-method` floor, the actually-installed `_bmad/_config/manifest.yaml` version, and the
latest release upstream publishes, diffed and surfaced as one more row in `doctor report` /
the fleet-picture ATTENTION block — never requiring an operator to think to ask.

## What is real

Nothing. Confirmed 2026-08-15, and not hypothetical: `pixi.toml` already declares
`bmad-method = ">=6.11.0"`, but `_bmad/_config/manifest.yaml` — the actually-installed core
— still reports `version: 6.10.0`. The dependency floor was bumped without the installed
content ever being reconciled, and nothing in the fleet noticed or reported it. This Dream
exists to make that class of drift visible on its own, the next time it happens.

## What it looks like when real

- A new read-only Source (mirrors `adoption-stage`'s own wiring, per FR-12's precedent —
  same Finding shape, no new plumbing invented) reads `pixi.toml`'s declared `bmad-method`
  floor, `_bmad/_config/manifest.yaml`'s installed version, and the latest upstream release
  (however Doctor's existing upstream-version machinery already answers that question for
  other dependencies), and reports a Finding whenever any two of the three disagree.
- Surfaces through Doctor's existing report/verdict shape and `fleet-picture`'s ATTENTION
  block — a `warn`, never a `fail` (matches the PRD's own "an incomplete axis gathers as
  `incomplete`, never overstates confidence" discipline; a version-drift Finding is
  informational, not a build-breaking gate).
- Feeds [[bmad-method-core-upgrade]] as an input signal an operator can act on, but does not
  itself trigger anything — Doctor never mutates state (PRD Non-Goals: "No auto-remediation
  actuator in v1... Doctor never opens PRs, patches files, or mutates any state").

## Constraints

- **Read-only, always.** This Dream reports; it never runs `npx bmad-method install` or
  touches `_bmad/**` — that is [[bmad-method-core-upgrade]]'s (owner: steward) territory
  entirely. Mirrors the detect/fix split Epic 8 already established for doctor's own
  deferred-work backlog (`pyforge.doctor` stays read-only by construction; any actuator is a
  sibling script outside the package).
- **Do not duplicate [[bmad-method-core-upgrade]]'s own pre-flight diff.** That Dream may
  still perform its own dry-run diff immediately before an apply — this Dream's job is the
  AMBIENT, continuously-refreshed signal an operator sees without running anything, not the
  upgrade tool's own safety check.

## Non-goals

- Not applying, merging, or reconciling anything — see Constraints.
- Not deciding which currently-unexercised BMAD modules to keep or drop
  ([[one-front-door]]'s own open question).
- Not a general "any dependency is behind" detector — this Dream is specifically about
  BMAD-METHOD's own installed core, because it is a special case (an installed *governance*
  layer with local customizations to protect, not an ordinary pinned dependency) that the
  existing `behind-upstream`-style machinery does not obviously already cover end to end.

## Kinships

[[bmad-method-core-upgrade]] (owner: steward, split off the same day — the apply half of
what was originally one unowned Dream; this Dream is its detection half) ·
[[bmad-module-provisioning]] (realized; the Constraint whose amendment made the split
possible) · [[pyforge-doctor]] (the station; FR-12's `adoption-stage` wiring is this
Dream's direct precedent for "new read-only Source, same Finding shape").

## Realization log

- **2026-08-15** — Dream captured, split off [[bmad-method-core-upgrade]]. That Dream was
  originally one unowned capability spanning both "detect drift" and "apply an upgrade."
  Investigation into resolving its ownership (prompted by the dashboard's ACCOUNTABILITY
  gate refusing to publish over its `unassigned` owner) found the two halves belong to
  different stations by their own existing shape — Doctor already owns ambient, read-only
  staleness reporting elsewhere in the fleet, and its PRD Non-Goals explicitly keep it
  mutation-free, matching this half exactly; Steward owns the mutating apply half. No
  precedent exists for a Dream naming more than one owner (checked against all 100 Dreams at
  the time), so rather than co-own one Dream, it was split into two, kept in sync via
  Kinships. Concrete motivating proof, found during the same investigation: `pixi.toml`
  already requires `bmad-method >=6.11.0` while the installed `_bmad/_config/manifest.yaml`
  still reports `6.10.0` — live drift, right now, that nothing in the fleet currently
  reports.
