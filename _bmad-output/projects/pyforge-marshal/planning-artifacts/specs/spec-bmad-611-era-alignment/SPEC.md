---
spec: bmad-611-era-alignment
status: ready
owner-dream: docs/dreams/bmad-611-era-alignment.md
surface: []   # populated as stories land (policy.py, status surfaces, DW scripts, guard test)
companions:
  - alignment-inventory.md
  - horizon-watches.md
sources:
  - ../../../../../../docs/dreams/bmad-611-era-alignment.md
assumptions:
  - "memlog.py's format stays stable through 6.11.x (unchanged among the 140
    files moved on main since v6.11.0) — the CAP-3 migration will not churn."
  - "The v7 cut is months out (no date, no milestone; npm `next` is a 6.11.1
    patch line; monthly-plus minor cadence with a 6.12-ish bmad-ticket landing
    expected first) — CAP-1 is cheap insurance, not an emergency."
open_questions: []
---

# SPEC — PyForge stays aligned to the installed BMAD era

## Why

The 2026-08-21/22 upgrade (BMAD 6.11.0 + bmad-loop 0.11.0, PRs #606/#607) made
the stack run current, not *be* current: retired skill names sit in planning
artifacts and in the seed template every new station inherits; 22 spec folders
carry memlog debt the 6.11 tooling refuses; the factory's living docs lost
their reconciler when `bmad-document-project` retired; and marshal can neither
govern the five new bmad-loop policy knobs nor name the new run states an
operator now encounters. Upstream adds a deadline: the 20 v6 shims are the one
*committed* v7 removal, and the v7 planning lane (`bmad-ticket` tree) is
already being built on a live branch. Owner: **marshal** — these are the
factory-governance surfaces (Dream § Whose job); detection-side pieces relay
to doctor, the upgrade-apply half stays steward Epic 14's.

## Capabilities

- **CAP-1 — Retired-ID purge + regression guard.** *Intent:* no retired skill
  ID (the published 20-shim list) survives in live docs, seed templates,
  memory, or code, and a meta-test reds any reintroduction between now and the
  v7 cut. *Success:* the sweep (6 planning artifacts, `dream-first-workflow.md.j2`,
  AGENTS.md, 3 auto-memory entries) lands; the guard passes on a clean tree
  and fails when a retired ID is planted.
- **CAP-2 — bmad-loop skill refresh.** *Intent:*
  `.claude/skills/bmad-loop-{setup,resolve,sweep}` match the installed
  package's canon (`bmad_loop/data/skills/`; today 217/134/7 diff lines
  stale). *Success:* diff-reviewed refresh lands; `bmad-loop validate` stays
  clean across all 8 homes.
- **CAP-3 — Memlog-format migration.** *Intent:* every spec folder accepts a
  6.11 `bmad-spec` update. *Success:* the 8 frontmatter-less memlogs gain
  frontmatter, the 14 memlog-less folders gain a genesis-baseline
  `.memlog.md` (the marshal S-13.7 bootstrap pattern), and `memlog.py append`
  succeeds against all 22.
- **CAP-4 — Policy-surface parity.** *Intent:* the five bmad-loop 0.10/0.11
  knobs (`review.on_timeout`, `review.on_status_contradiction`,
  `limits.dev_contract_nudge`, `operator.enabled`,
  `verify.stream_capture_kb`) are governable through the AD-16
  defaults→project→flags chain with deliberate repo defaults. *Success:*
  policy composition + render pipeline expose them with exact TOML scalar
  types (0.11 rejects coercible mismatches); rendered policies pass
  `bmad-loop validate`; marshal suite green.
- **CAP-5 — 0.11 status vocabulary.** *Intent:* `awaiting-operator`,
  `confirm`, `preserve_ref`, and `sweeps_refused` are visible wherever an
  operator looks (`marshal status`, fleet-picture); a parked run is named
  `awaiting-operator (run bmad-loop confirm)` — absorbing DW-BL011-1 — and
  `preserve_ref` feeds the escalation-preservation flow (the fleet's standing
  non-destructive policy, now upstream-native). *Success:* fixture-driven
  status tests; the stall-check reports parked runs distinctly.
- **CAP-6 — Deferred-work intake reads both sources.** *Intent:* a
  hand-driven build-auto run's spec-frontmatter `deferred:` list reaches the
  tracked ledger without a human relay. Loop-driven runs are already bridged
  upstream (`Engine._harvest_spec_deferrals`, since 0.9.1) — the scope is the
  hand-driven gap plus our scripts' intake. *Success:* a fixture in the shape
  of the 2026-08-22 canary's DW-14-1-1 is ingested from frontmatter;
  DW-BL011-2 closes.
- **CAP-7 — Living factory docs re-grounded, with a named owner.** *Intent:*
  `architecture-bmad-infra.md` describes the 6.11 infra (render pipeline,
  TOML layers, current skill set) and the 8 per-station `project-context.md`
  rulebooks are refreshed — via plain re-grounding agents per SYNC-RUNBOOK,
  not by waiting on upstream's zero-signal successor capability — with
  recurrence owned. *Success:* docs re-grounded with bumped `source_pin`s;
  SYNC-RUNBOOK names the owner and cadence.

## Constraints

- **Do not adopt what upstream is removing**: no `stories.yaml`, no folder+id
  dispatch, no `{spec-folder}/stories/` migration — the epic-story path is the
  surviving v6 route (V7-10 keeps it in build-auto).
- **HOLD the AGENTS.md managed block / project-context ledger** — upstream is
  reworking it live (#2715/#2733/#2750/#2754); re-ground the existing
  rulebooks instead.
- **Watch, don't build, the unscheduled**: the TOML cutover and the
  bmad-ticket tree live as named triggers in `horizon-watches.md`, never as
  code in this chain.
- Retired-name sweeps gloss historical/narrative text with the new name
  rather than rewriting shipped history.
- Shims stay installed until CAP-1's guard is green — never answer
  "remove shims" to the installer before then.
- Policy work emits exact TOML scalar types and keeps
  `[dev] skill = "bmad-dev-auto"` (the adapter discriminator; bmad-loop
  resolves the invoked skill on disk).

## Non-goals

- The **bmad-ticket tracking adapter** — its own future marshal Dream;
  trigger: bmad-ticket in a tagged release (all sprint-feed/ledger/promote/
  status/fleet/dashboard machinery stays as-is until then).
- The **TOML-cutover symlink migration** — steward Epic 14's watch; the named
  consequence rides that spec's failure-modes.
- **TEA adoption** (module install, `tea-test-review` CI gate) — optional,
  not alignment; the repo-custom `bmad_tea_playwright.py` generator stays.
- Upgrade-apply (steward Epic 14) and version-drift detection (doctor
  Epic 14) — kin chains, already owned.
- Paige replacement, "explain this system", bmad-ux/WDS — zero upstream
  implementation signal; nothing to align to.

## Success signal

A planted retired skill ID reds the test suite; a hand-driven run's deferral
reaches the tracked ledger unaided; `bmad-spec` update succeeds against every
spec folder in the fleet; and marshal both governs and names everything
bmad-loop 0.11 exposes — demonstrated against the live repo, with the
alignment-inventory findings each traceable to the story that closed it.
