---
spec: bmad-611-era-alignment
status: ready   # CAP-1..7 shipped (marshal Epic 25, 7/7 done 2026-08-24); CAP-8..11 — the 6.12 round, minted 2026-09-05 — await decomposition as a new marshal epic
owner-dream: docs/dreams/bmad-611-era-alignment.md
surface: []   # none claimed: the story surfaces (policy.py, status surfaces, DW scripts, guard test) are measured by fleet-level spec-surface coverage, not double-governed here
companions:
  - alignment-inventory.md
  - horizon-watches.md
sources:
  - ../../../../../../docs/dreams/bmad-611-era-alignment.md
assumptions:
  - "memlog.py and bmad-spec's spec-template are byte-identical 6.11 → 6.12 —
    CAP-3's migration holds; re-check at each core minor."
  - "The v7 cut is still months out: 6.12.0 shipped 2026-09-03 without
    bmad-ticket or the TOML cutover, no date or milestone exists, cadence stays
    monthly-plus — CAP-1 / CAP-8 remain cheap insurance, not an emergency."
open_questions:
  - "CAP-8: derive the guard tuple from steward's release catalog
    (`data/bmad_core_releases/<ver>.yaml` skill_renames + removals) instead of
    a hand-kept tuple? Default yes at story time — derive, don't declare — once
    the 6.12.0 catalog lands (its 2026-09-05 draft was lost with the swept
    worktree; re-derive it from the unpacked package)."
---

# SPEC — PyForge stays aligned to the installed BMAD era

## Why

The 2026-08-21/22 upgrade (BMAD 6.11.0 + bmad-loop 0.11.0, PRs #606/#607) made
the stack run current, not *be* current: retired skill names sat in planning
artifacts and in the seed template every new station inherits; 22 spec folders
carried memlog debt the 6.11 tooling refused; the factory's living docs lost
their reconciler when `bmad-document-project` retired; and marshal could neither
govern the five new bmad-loop policy knobs nor name the new run states an
operator now encounters. Upstream adds a deadline: the 20 v6 shims are the one
*committed* v7 removal, and the v7 planning lane (`bmad-ticket` tree) is being
built on a live branch. Owner: **marshal** — these are the factory-governance
surfaces (Dream § Whose job); detection-side pieces relay to doctor, the
upgrade-apply half stays steward Epic 14's.

That 6.11 round shipped as marshal Epic 25 (7/7, 2026-08-24). BMAD-METHOD
**6.12.0** (released 2026-09-04; `_bmad/` still 6.11.0 pending steward Epic 14's
apply) reopened the Dream: the shim roster swapped a seat, `persistent_facts`
ships empty so the eight `project-context.md` rulebooks lose their consumer,
`llms-full.txt` is discontinued, and bmad-loop 0.11.1 outran the repo skill
copy. This Spec stays the Dream's single contract across era shifts — one round
of CAPs per shift, IDs never reused.

## Capabilities

**Round 6.11 — CAP-1..7, shipped (marshal Epic 25, 7/7 done 2026-08-24).**

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
  SYNC-RUNBOOK names the owner and cadence. *(Owner decided 2026-08-24:
  marshal; the 6.12 round moves the rulebook half to CAP-9.)*

**Round 6.12 — CAP-8..11, added 2026-09-05, awaiting decomposition.**

- **CAP-8 — 6.12 retired-ID roster.** *Intent:* the guard follows the
  installed era's shim list: `bmad-checkpoint-preview` (a new shim forwarding
  to `bmad-walkthrough`) joins the tuple; `bmad-generate-project-context` stays
  guarded although it is neither a 6.12 shim nor a `removals.txt` entry — an
  update orphans its 6.11 directory, so the apply must delete it; the two
  living docs naming checkpoint-preview bare (`architecture-bmad-infra.md`,
  `development-guide.md`) are renamed or glossed. *Success:* the guard passes
  on the swept tree with the 6.12 list and fails on a planted
  `bmad-checkpoint-preview`; no orphaned shim directory survives the apply.
- **CAP-9 — Project-context surface follows 6.12.** *Intent:*
  `persistent_facts` ships empty and stays empty (D1); the eight station
  `project-context.md` rulebooks retire with every consumer migrated first —
  doctor `sources/factory.py` classification and its `pin-behind (context)`
  row, `scripts/fleet_scan.py`, `scripts/bmad_drift_check.py`, SYNC-RUNBOOK's
  living-doc cadence (rows 7–9 / 45–49 / 83–85) — and `bmad-project-context
  audit` becomes the post-upgrade step. *Success:* `bmad-drift-check` and the
  detectors are green with zero `project-context.md` rows; SYNC-RUNBOOK's
  cadence names `architecture-bmad-infra.md` + the AGENTS.md block only; no
  `pin-missing` HARD finding is left behind.
- **CAP-10 — Documentation pointers follow 6.12.** *Intent:* `llms.txt` /
  `llms-full.txt` are discontinued, so CLAUDE.md § BMAD Method Documentation
  re-points (local copy = the last snapshot, generated 2026-08-17, 6.11-era,
  frozen; live = the task-organized docs site + the package CHANGELOG);
  `bmad-checkpoint-preview` → `bmad-walkthrough` in living docs;
  `architecture-bmad-infra.md` re-grounded to 6.12 after the apply (CAP-7's
  cadence: once per core minor). *Success:* no live doc cites the dead URL;
  `source_pin` reads BMAD 6.12.0.
- **CAP-11 — bmad-loop 0.11.1 parity, durable.** *Intent:* refresh
  `.claude/skills/bmad-loop-setup` (`module_version` 0.11.0 → 0.11.1;
  `-resolve` / `-sweep` already identical) and add a meta-test that diffs the
  three repo skills against the installed `bmad_loop/data/skills` so CAP-2
  holds by test, not memory. *Success:* the diff is empty; `bmad-loop
  validate` is clean across all 8 homes; the test reds a planted one-line
  divergence.

## Constraints

- **Do not adopt what upstream is removing**: no `stories.yaml`, no folder+id
  dispatch, no `{spec-folder}/stories/` migration — the epic-story path is the
  surviving v6 route (V7-10 keeps it in build-auto).
- **The AGENTS.md HOLD is lifted (2026-09-05).** The managed `bmad:context`
  block has been live since 2026-09-04 (verified against `bd37dfd607`) and
  6.12's `adopt` intent is the rework the HOLD waited out. D1 applies: the
  AGENTS.md block is the project-context surface; the eight rulebooks retire
  only after their consumers are migrated — never a file nothing loads.
- **Watch, don't build, the unscheduled**: the TOML cutover and the
  bmad-ticket tree live as named triggers in `horizon-watches.md`, never as
  code in this chain (6.12 shipped neither).
- Retired-name sweeps gloss historical/narrative text with the new name
  rather than rewriting shipped history.
- Shims stay installed through the v7 cut (upstream's own rule). The guard is
  green, so the pre-sweep bar is met, but every apply passes `--shims`
  explicitly — 6.12 made shims opt-in on fresh installs; clones of this repo
  inherit the tracked `.claude/skills/`, so that default bites only a NEW
  repo's `npx bmad-method install`.
- Policy work emits exact TOML scalar types and keeps
  `[dev] skill = "bmad-dev-auto"` (the adapter discriminator; bmad-loop
  resolves the invoked skill on disk).

## Non-goals

- The **bmad-ticket tracking adapter** — its own future marshal Dream;
  trigger: bmad-ticket in a tagged release (all sprint-feed/ledger/promote/
  status/fleet/dashboard machinery stays as-is until then; not in 6.12).
- The **TOML-cutover symlink migration** — steward Epic 14's watch; the named
  consequence rides that spec's failure-modes (not in 6.12).
- **TEA adoption** (module install, `tea-test-review` CI gate) — optional,
  not alignment; the repo-custom `bmad_tea_playwright.py` generator stays.
- Upgrade-apply (steward Epic 14, incl. the 6.12.0 catalog and the apply
  itself) and version-drift detection (doctor Epic 14) — kin chains, already
  owned.
- Paige replacement, "explain this system" — zero upstream implementation
  signal; nothing to align to. (The bmad-ux/WDS half resolved: 6.12's module
  registry deprecates WDS into `bmad-ux`; the suite retired it 2026-09-05 —
  `spec-bmad-suite-channel-product`.)

## Success signal

A planted retired skill ID reds the test suite; a hand-driven run's deferral
reaches the tracked ledger unaided; `bmad-spec` update succeeds against every
spec folder in the fleet; and marshal both governs and names everything
bmad-loop 0.11 exposes — demonstrated against the live repo, with the
alignment-inventory findings each traceable to the story that closed it
(**met — Epic 25, 2026-08-24**).

For the 6.12 round: a planted `bmad-checkpoint-preview` reds the guard and no
orphaned shim directory survives the apply; `bmad-drift-check` is green with
zero `project-context.md` rows and SYNC-RUNBOOK's cadence names only
`architecture-bmad-infra.md` + the AGENTS.md block; no live doc cites the
discontinued `llms-full.txt`; and the three bmad-loop repo skills diff empty
against the installed package under a test — each traceable to the
alignment-inventory row (#9–#14) it closes.
