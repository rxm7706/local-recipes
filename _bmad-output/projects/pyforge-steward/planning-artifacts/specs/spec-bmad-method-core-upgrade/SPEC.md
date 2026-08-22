---
spec: bmad-method-core-upgrade
status: ready
owner-dream: docs/dreams/bmad-method-core-upgrade.md
surface: []   # nothing built yet — populate when the steward verb lands
companions:
  - failure-modes.md
sources:
  - ../../../../../../docs/dreams/bmad-method-core-upgrade.md
assumptions:
  - "conda-forge bmad-method (pixi-provisioned) remains the install channel; the
    installer's `--action update -y` is idempotent and safe to re-run (observed
    live 2026-08-21)."
  - "6.11's four-layer TOML config is 'the migration, not the cutover' (release
    notes verbatim) — `_bmad/bmm/config.yaml` still ships and the planning-artifacts
    symlink pattern still works; CAP-1 must flag the eventual TOML cutover release."
open_questions:
  - "Verb naming/placement: extend `steward provision` vs a new verb (e.g.
    `steward upgrade bmad-core`) — decide at epic time (provisioning spec's
    flag-naming precedent)."
  - "Should doctor's ambient drift extend to the SelfExplainML bmad-suite
    packages? bmad-loop lagged 0.9.0→0.11.0 with zero ambient signal until a
    human checked (2026-08-21). Doctor-side scope — relay at decomposition."
  - "Prerelease/@next channel support in scope, or stable-only first cut? The
    Dream names @next; nothing has exercised it."
---

# SPEC — The installed BMAD-METHOD core upgrades repeatably, not by heroics

## Why

The fleet has no repeatable way to take a new BMAD-METHOD release into this
repo's already-installed core. Both upgrades ever performed were manual
one-offs: 6.6.0→6.10.0 (bmad-loop-adoption W1) and 6.10.0→6.11.0 (2026-08-21,
the session this spec is grounded in) — the second re-hit the first's traps,
including the same custom-surface clobber. Doctor's shipped drift detector
(Stories 10.1/10.2) reports "you're behind" ambiently, but nothing can act on
it. Ownership was resolved 2026-08-15 by a two-pass investigation recorded in
the Dream: **steward** owns the mutating apply half (marshal is ruled out by
its own installer-owned boundary; genesis-installer verifies floors and never
installs; `bmad-module-provisioning`'s "never absorb" constraint was narrowed
to first-install, carving this territory out by name).

## Capabilities

- **CAP-1 — Pre-flight diff (report-only).** *Intent:* given the installed
  manifest and a target release, report skill adds/removes/renames (shim
  disposition + `removals.txt` deletions), upstream-touched files the repo has
  locally modified, `_bmad/custom/**` overrides that stop applying (the
  legacy-name unattended-halt trap), and new hard prerequisites (e.g. `uv`).
  *Success:* run against the 6.10.0→6.11.0 pair, it retrodicts the 2026-08-21
  findings (companion, § Traps).
- **CAP-2 — Deliberate, reviewable apply.** *Intent:* wrap
  `bmad-method install --action update -y` non-interactively: branch/snapshot
  first, never a silent overwrite of `_bmad/custom/**`, installer diff landed
  for review — never applied blind in place. *Success:* a clean run lands the
  installer diff on a review branch with the custom-surface checklist executed.
- **CAP-3 — Custom-surface reconciliation.** *Intent:* after apply, detect
  clobbered repo-custom surfaces — `resolve_config.py`'s multi-project layers
  5/6 is the named recurring case, clobbered in BOTH manual upgrades — and
  re-apply or flag them. *Success:* post-apply, `bmad-switch --current` and a
  `BMAD_ACTIVE_PROJECT` override both resolve the six layers; the installer's
  `.bak` is accounted for.
- **CAP-4 — Downstream pin fan-out report (report-only).** *Intent:* enumerate
  every pin site the release moves — root `pixi.toml` floors, marshal's
  pyproject + package `pixi.toml` + `HARNESS_VERSION_RANGE_TEXT` + seed
  manifest/drift-test map, loop-home hook relays — and report moved vs. not.
  *Success:* names exactly the sites the 2026-08-21 session had to touch, none
  discovered later by red tests.
- **CAP-5 — Post-apply verification gate.** *Intent:* run the repo's own gates
  (bmad-drift-check integrity, CFE skill meta-tests, `bmad-loop validate` per
  loop home including the `init` relay refresh) and report one verdict.
  *Success:* reproduces the 2026-08-21 checklist (8/8 loop homes validate
  clean) in one command.

## Constraints

- Never silently overwrite `_bmad/custom/**` — clobber-without-surfacing is
  worse than no upgrade path (the Dream's own top constraint).
- The multi-project marker/symlinks survive an upgrade untouched; the tool
  never calls `bmad-switch` and verifies artifact placement by physical path.
- Refuse or warn before an unattended run when legacy-name customization files
  exist (`_bmad/custom/bmad-dev-auto.toml` etc.) — the 6.11 shim halts instead
  of forwarding on them.
- The upstream installer stays the only writer of `_bmad/bmm/**` and
  `_bmad/core/**` — steward wraps it, never reimplements it.
- Foreign-station surfaces (marshal pin sites, doctor detectors) are
  **reported, never edited** — owners act on the report.
- Runs from the repo's pixi env (installer, `uv`, node all resolve there;
  nothing global).

## Non-goals

- Ambient staleness detection — doctor's `bmad-method-version-drift` (shipped,
  10.1/10.2).
- Module keep/drop triage — `one-front-door`'s open question.
- bmad-suite conda-recipe refresh + SelfExplainML channel publishing — the CFE
  factory flow (the 2026-08-21 suite bumps ran there; companion § Suite orbit).
- Editing foreign-station pin sites.
- First-install of adjacent modules — `bmad-module-provisioning` (shipped).

## Success signal

The first post-6.11.0 BMAD-METHOD release goes from "doctor reports behind" to
"installed core current, custom surfaces verified, gates green" through this
capability with no step improvised from scratch — and CAP-1, pointed at the
6.10.0→6.11.0 pair, retrodicts the 2026-08-21 session's findings.
