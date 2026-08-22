---
title: BMAD-METHOD's own core stays current, not stuck at whatever version got installed
type: dream
owner: steward
status: specified   # 2026-08-21 — spec-bmad-method-core-upgrade under pyforge-steward, grounded in the live 6.10.0→6.11.0 upgrade session
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

## Whose job this is — resolved 2026-08-15, owner: steward

Investigated directly, not assumed. First pass found this genuinely unowned:

- **Marshal is ruled out on its own documented boundaries.** Marshal's own gap survey
  ([[one-front-door]]) marks `bmad-method` itself as **"route,"** explicitly distinct from
  what it marks **"own."** Marshal's architecture states installed BMAD skills
  (`_bmad/bmm/**`, `_bmad/core/**`) are **"installer-owned... Genesis must never write
  here."** This exclusion stands.
- **`genesis-installer`'s actual FR coverage is unrelated** — confirmed independently on a
  second pass (its own register: bmad-method is "verified, never installed," Genesis
  asserts a version floor and never vendors the package; its `update` verb (CAP-15) upgrades
  Genesis's own *materialized* artifacts, not bmad-method's installed core). Zero execution
  weight either way — all 36 of its stories are still `backlog`.
- **Steward was initially ruled out too**, by [[bmad-module-provisioning]]'s Constraints —
  "Never absorb `bmad-method`'s own governance core... does not reimplement `bmad-method
  install` or take ownership of `_bmad/bmm/**`/`_bmad/core/**`" — read literally, that line
  excludes this exact gap by name.

A second, deeper investigation (operator-requested, 2026-08-15) found that exclusion was
broader than its own reasoning supported. [[bmad-module-provisioning]]'s Constraint was
written to prevent duplicating Marshal's/genesis-installer's turf for **first-installing**
adjacent modules (Skill Forge, BMB) from nothing — a different job from **reconciling an
already-installed** bmad-method core against a new upstream release, which this Dream is
actually about. Steward's own charter is broad by design ("deploys, provisions, and
operates — environments and runners, service deployments, credential and privilege
lifecycles") and its already-shipped `provision --env`/`--runner` duty (Epic 3) is
structurally the same shape this needs: wrap an external tool non-interactively, report a
clear error, never leave partial state unreported.

**Resolution:** [[bmad-module-provisioning]]'s Constraints were amended the same day to
narrow the "never absorb" line to first-install only, and carve out this Dream by name as
the distinct, ALSO-Steward-owned capability for reconciling an already-installed core.
**Detection is a separate, Doctor-owned Dream** — [[bmad-method-version-drift]] — kept
apart because it stands on its own value (an operator should see "you're behind" as an
ambient signal even before anyone runs the upgrade tool) and matches Doctor's own
report-only shape (PRD Non-Goals: "No auto-remediation actuator... Doctor never opens PRs,
patches files, or mutates any state") rather than Steward's mutating one. This Dream may
still perform its OWN pre-flight diff as part of a safe apply (see "What it looks like when
real" below) — that is a mechanical precondition for applying safely, not a duplicate of
[[bmad-method-version-drift]]'s ambient reporting.

**Concrete, live proof this gap is real right now** (found during the second investigation,
not hypothetical): `pixi.toml` already declares `bmad-method = ">=6.11.0"`, but
`_bmad/_config/manifest.yaml` (the actually-installed core) still reports `version:
6.10.0` — the dependency floor was bumped without the installed `_bmad/bmm/**`/
`_bmad/core/**` content ever being reconciled.

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
  provisioning — that Dream's own Constraints were amended 2026-08-15 to carve THIS
  territory out to this Dream by name, not to hand its own realized scope over.
- Not the ambient "you're behind" signal — that is [[bmad-method-version-drift]] (owner:
  doctor), a standing health finding an operator sees without running anything. This Dream
  may do its own pre-flight diff as a precondition for a safe apply, but owning a
  continuously-refreshed fleet-wide staleness report is Doctor's job, not Steward's.

## Kinships

[[bmad-module-provisioning]] (realized; its Constraints were amended 2026-08-15 to carve out
this exact territory by name — first-install there, already-installed reconciliation here) ·
[[bmad-method-version-drift]] (owner: doctor, split off 2026-08-15 — the ambient
detection half of what was originally one unowned Dream) · [[one-front-door]] (the survey
whose own "route" vs "own" line this Dream's investigation relies on) · [[genesis-installer]]
(the boundary this Dream is outside of) · [[pyforge-marshal]] (owns the multi-project symlink
mechanism an upgrade must not break).

## Realization log

- **2026-08-15** — Dream captured. Surfaced when the user asked, after noticing
  BMAD-METHOD v6.11.0 had released, whether any station owns installing/upgrading it in
  this repo. Investigation (mirroring [[bmad-module-provisioning]]'s own ownership
  reasoning) found the gap is real and, unlike that Dream, genuinely unowned — both Marshal
  and Steward have explicit, on-the-record boundaries excluding it. Captured as its own
  Dream with the ownership question left open rather than defaulted, per the same rigor
  [[bmad-module-provisioning]] itself modeled.

- **2026-08-15 (resolved, same day)** — Owner assigned: **steward**. The dashboard's
  ACCOUNTABILITY gate refused to publish over the `unassigned` owner (Charter §7: "the hall
  does not put a row on the wall it cannot attribute"), which prompted the operator to ask
  directly whether Steward could own the install half after all, with Doctor owning
  update/refresh detection. A second investigation (independent of the first, requested
  explicitly to push back rather than rubber-stamp) found [[bmad-module-provisioning]]'s
  exclusion was narrower in its own reasoning than its Constraint's literal wording — written
  against first-install duplication, never evaluated against already-installed reconciliation
  — and found live, present-tense proof the gap matters now: `pixi.toml` already requires
  `bmad-method >=6.11.0` while the installed `_bmad/_config/manifest.yaml` still reports
  `6.10.0`. Resolved by amending [[bmad-module-provisioning]]'s Constraints (narrowed, this
  Dream carved out by name) and splitting the ambient-detection half into a new sibling Dream,
  [[bmad-method-version-drift]] (owner: doctor), rather than co-owning one Dream across two
  stations — no precedent exists for a Dream naming more than one owner, checked against all
  100 Dreams at the time.
