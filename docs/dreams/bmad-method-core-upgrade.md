---
title: BMAD-METHOD's own core stays current, not stuck at whatever version got installed
type: dream
owner: unassigned   # investigated, not defaulted -- see "Whose job this is" below
status: dreamt
---

# BMAD-METHOD's own core stays current, not stuck at whatever version got installed

## The Dream

Something in this fleet can safely run `npx bmad-method install`/`@next` against THIS
existing repo — not a fresh clone — reconcile whatever changed in `_bmad/bmm/**`/
`_bmad/core/**` against this repo's own customizations (`_bmad/custom/**`, the
multi-project active-symlink mechanism, any skill this repo has locally overridden or
extended), report what's new/changed/deprecated, and give an operator a real upgrade path
instead of a one-off manual effort redone from scratch every time upstream ships a release.

Today there is no such capability, anywhere in the fleet. The only precedent is
`docs/specs/bmad-loop-adoption.md`'s historical 6.6.0→6.10.0 upgrade — a single, manual,
non-repeatable effort scoped to one specific jump, already closed out. BMAD-METHOD has
released since (v6.11.0, 2026-08-15) with nothing in this repo positioned to even notice,
let alone act on it.

## Whose job this is, and why it isn't settled

Investigated directly, not assumed — and unlike [[bmad-module-provisioning]] (which found
a clear owner), this one comes up genuinely unowned:

- **Marshal is ruled out on its own documented boundaries.** Marshal's own gap survey
  ([[one-front-door]]) marks `bmad-method` itself as **"route,"** explicitly distinct from
  what it marks **"own."** Marshal's architecture states installed BMAD skills
  (`_bmad/bmm/**`, `_bmad/core/**`) are **"installer-owned... Genesis must never write
  here."**
- **Steward is ALSO ruled out, by its own already-shipped Dream's explicit Constraints.**
  [[bmad-module-provisioning]] (owner: steward, realized 2026-08-10, ships `steward
  provision --module <name>` for Skill Forge/BMB-class *adjacent* modules) says in its own
  words: **"Never absorb `bmad-method`'s own governance core. This Dream provisions
  modules; it does not reimplement `bmad-method install` or take ownership of
  `_bmad/bmm/**`/`_bmad/core/**`, which stay installer-owned."** That is this exact
  gap, explicitly declined by name.
- **`genesis-installer`'s actual FR coverage is unrelated** — a Copier-based file/region
  templating engine for stamping this repo's OWN conventions into a target repo, not a
  wrapper around a third-party npm installer.

Two explicit exclusions from the two stations that would most plausibly own it. This needs
an operator call, not a default assignment — either a new, narrowly-scoped owner, or an
explicit decision that ONE of Marshal/Steward should extend its boundary to cover it after
all (which would itself need to amend that station's own Constraints, not just add a story).

## What it looks like when real

- A non-interactive, re-runnable command reports what an upstream BMAD-METHOD release
  would change against this repo's CURRENT installed state before touching anything —
  new/removed modules, skill files this repo has locally modified that upstream also
  touched (a real conflict, not a silent overwrite), and whether `_bmad/custom/**`
  overrides still apply cleanly.
- Applying the upgrade is a deliberate, reviewable step (matches this repo's own
  archive-don't-delete / review-before-mutate convention running through every other
  provisioning-shaped capability in the fleet) — never a silent `npx bmad-method install`
  overwrite in place.
- The multi-project active-symlink/marker mechanism ([[pyforge-marshal]]'s own territory)
  survives an upgrade without needing to be manually re-established afterward.

## What is real

Nothing. Confirmed 2026-08-15: this repo has no mechanism to detect, diff, or apply a
BMAD-METHOD core release, and the only prior upgrade (6.6.0→6.10.0) was a manual,
non-repeatable one-off.

## Constraints

- Must not silently overwrite `_bmad/custom/**` (team + user override layers) — an upgrade
  that clobbers local customization without surfacing the conflict is worse than no
  upgrade path at all.
- Must respect the multi-project symlink/marker mechanism's own fragility (already
  documented as a live footgun in [[pyforge-marshal]]/CLAUDE.md's own "parallel agents"
  warnings) — an upgrade run mid-way through other agent activity must not desync it.

## Non-goals

- Not deciding which currently-unexercised modules to keep or drop (`bmad-manticore`,
  `bmad-labs-skills`, etc.) — that's [[one-front-door]]'s own open question, orthogonal to
  how the CORE gets upgraded.
- Not re-scoping [[bmad-module-provisioning]]'s already-shipped adjacent-module
  provisioning — this Dream is specifically the territory that Dream's own Constraints
  declined, not a duplicate of what it already covers.

## Kinships

[[bmad-module-provisioning]] (realized, explicitly excludes this exact territory) ·
[[one-front-door]] (the survey whose own "route" vs "own" line this Dream's investigation
relies on) · [[genesis-installer]] (the boundary this Dream is outside of) ·
[[pyforge-marshal]] (owns the multi-project symlink mechanism an upgrade must not break).

## Realization log

- **2026-08-15** — Dream captured. Surfaced when the user asked, after noticing
  BMAD-METHOD v6.11.0 had released, whether any station owns installing/upgrading it in
  this repo. Investigation (mirroring [[bmad-module-provisioning]]'s own ownership
  reasoning) found the gap is real and, unlike that Dream, genuinely unowned — both Marshal
  and Steward have explicit, on-the-record boundaries excluding it. Captured as its own
  Dream with the ownership question left open rather than defaulted, per the same rigor
  [[bmad-module-provisioning]] itself modeled.
