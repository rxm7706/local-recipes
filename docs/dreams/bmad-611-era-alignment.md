---
title: PyForge's artifacts, patterns, and station code stay aligned to the installed BMAD era — 6.12 today, v7-ready tomorrow
type: dream
owner: marshal
status: realized   # 2026-08-24 — the 6.11 round shipped (marshal Epic 25, 7/7 done). Perpetual: every BMAD-era shift reopens a round under the same Spec — 6.12.0 (released 2026-09-04) minted CAP-8..11 on 2026-09-05, awaiting decomposition
---

# PyForge's artifacts, patterns, and station code stay aligned to the installed BMAD era

## The Dream

Upgrading the BMAD core and suite (done 2026-08-21/22: core 6.11.0, bmad-loop
0.11.0, PRs #606/#607) makes the stack *run* current — it does not make the
fleet *aligned*. Every station was built against pre-6.11 / bmad-loop-0.9-era
conventions, and the residue is concrete: retired skill names baked into
planning artifacts and seed templates, spec folders whose memlogs the 6.11
tooling refuses to touch, living factory docs whose reconciler skill no longer
exists, and marshal surfaces that cannot see or govern what bmad-loop 0.10/0.11
added. The dream: after any BMAD-era shift, one owned effort brings artifacts,
locations, patterns, and station code back into alignment — and the alignment
holds, guarded by tests, until the next era.

## Grounding — what was verified (2026-08-22, two research passes + local inventory)

**Local misalignment (all verified, none assumed):**

1. **bmad-loop's three repo-installed skills are stale vs the 0.11 package**
   (`bmad-loop-setup` 217 diff lines, `-resolve` 134, `-sweep` 7, against
   `bmad_loop/data/skills/`; `init` deliberately refuses to overwrite without
   `--force-skills`).
2. **Marshal's seed template ships a retired name to every NEW station** —
   `seed/templates/files/dream-first-workflow.md.j2` says "`bmad-loop` /
   `bmad-dev-auto`".
3. **6 station planning artifacts name retired skills** in dispatch-instruction
   text: epics.md of warden/steward/atlas/doctor/marshal + marshal's PRD.md.
   Plus one reference in AGENTS.md and three auto-memory entries.
4. **22 spec folders carry pre-6.11 memlog debt**: 14 have `SPEC.md` with no
   `.memlog.md` at all; 8 more have memlogs without frontmatter, which 6.11's
   `memlog.py` refuses outright (hit live 4× during the upgrade landing —
   hand-appends were the workaround). Any future `bmad-spec` update against
   these folders fails or violates the derive discipline. All 8 stations affected.
5. **Living factory docs lost their reconciler**: `bmad-document-project` /
   `bmad-generate-project-context` are retired; `architecture-bmad-infra.md`
   is a 6.10-era description of a now-6.11 infra (pre-render, pre-TOML, old
   names; last re-grounded 2026-07-25), and the 8 per-station
   `project-context.md` rulebooks — still consumed by build-auto's
   persistent_facts, proven by the 2026-08-22 canary — have no regenerator.
6. **Marshal's policy layer knows none of the bmad-loop 0.10/0.11 knobs**
   (`review.on_timeout`, `[review] on_status_contradiction`,
   `limits.dev_contract_nudge`, `[operator] enabled`,
   `[verify] stream_capture_kb`) — stock defaults apply, but the AD-16
   defaults→project→flags chain cannot govern them.
7. **Marshal's status vocabulary predates 0.11**: `awaiting-operator` phase,
   `confirm` verb, `preserve_ref`, `sweeps_refused` are invisible to
   `marshal status` / fleet-picture (marshal DW-BL011-1 covers only the
   stall-check mislabel). `preserve_ref` is the fleet's standing
   escalation-preservation policy, now upstream-native and unadopted.

**Upstream v7 trajectory (researched 2026-08-22; cited in the spec's companion):**

- **The only COMMITTED v7 breakage is the 20-shim removal** ("removal rides
  the v7 cut — never a 6.x minor"; shims are now opt-out on fresh installs,
  keep-by-default on updates, identified by `metadata.lifecycle: shim`).
- **The v7 planning lane is the `bmad-ticket` tree** (`ticket-master` branch,
  active through 2026-08-19): `.bmad-obeya/` work store, epic folders +
  `ticket.md`, `KEY-n-slug.md` stories, status the only stored fact, derived
  board/frontier verbs; `bmad-create-epics-and-stories` becomes a shim;
  **`sprint-status.yaml` survives only for in-flight v6 stories**;
  **`stories.yaml` is being removed** before this repo ever adopted it.
- **The config.yaml→TOML cutover is probable-at-v7 but unscheduled** — nothing
  on main moves it yet; when it lands, the multi-project planning-artifacts
  symlink mechanism dies (soft landing available: the repo-custom six-layer
  `resolve_config.py` already speaks TOML layers 5/6).
- **bmad-loop already bridges the deferred-work contract**:
  `Engine._harvest_spec_deferrals` (since 0.9.1) harvests spec-frontmatter
  `deferred:` lists into the ledger its sweep reads — so the frontmatter gap
  bites only HAND-DRIVEN build-auto runs (exactly the 2026-08-22 canary,
  whose deferred item needed a manual relay to doctor's DW ledger).
- No v7 date, milestone, or migration doc exists; `next` is a 6.11.1 patch
  line; Paige's replacement, the "explain this system" capability, and
  bmad-ux/WDS absorption all have zero implementation signal.

### The 6.12.0 era shift — verified 2026-09-05 (tagged tree + CHANGELOG + local diff, not the release page)

BMAD-METHOD **6.12.0** shipped 2026-09-03 (GitHub release 2026-09-04). The
`_bmad/` install is still 6.11.0 — the apply is steward Epic 14's
(`steward upgrade`, operator-gated) — but the era of record has moved, and
the residue this Dream owns is already visible:

1. **Shim roster: still 20, one seat swapped.** `bmad-checkpoint-preview` is
   a new shim forwarding to the new `bmad-walkthrough` (`CK` → `WT`);
   `bmad-generate-project-context` (a 6.11 shim) ships as neither a shim nor
   a `removals.txt` entry, so an update leaves its 6.11 directory orphaned in
   `.claude/skills/`. Shims are now **opt-in on fresh installs** (`--shims`);
   existing installs keep them by default. CAP-1's guard list and the two
   living docs naming `bmad-checkpoint-preview` (`architecture-bmad-infra.md`,
   `development-guide.md`) are behind.
2. **`persistent_facts` ships empty** (`bmad-build-auto/customize.toml`: the
   `file:**/project-context.md` glob is gone). The eight station
   `project-context.md` rulebooks — CAP-7's premise, "still consumed by
   build-auto" — lose their only runtime consumer. The 2026-09-05 upgrade
   planning session decided **D1: accept the empty default**; the AGENTS.md
   `bmad:context` block is the project-context surface. Consumers to
   migrate: doctor `sources/factory.py` (+ its `pin-behind (context)` row),
   `scripts/fleet_scan.py`, `scripts/bmad_drift_check.py`, and SYNC-RUNBOOK's
   living-doc cadence.
3. **The AGENTS.md HOLD is moot.** The managed `bmad:context` block was set up
   2026-09-04 (verified against `bd37dfd607`), and 6.12's
   `bmad-project-context` gains an `adopt` intent with a
   retain/rewrite/relocate/delete ledger — the rework this Dream was waiting
   out has landed.
4. **`llms.txt` / `llms-full.txt` are no longer published.** CLAUDE.md's
   "live source" pointer is dead; `.claude/docs/bmad-method-llms-full.txt`
   (generated 2026-08-17) is the last snapshot there will be.
5. **`{diff_output}` → `{diff_file}`** in review-layer overrides: no
   `_bmad/custom/` override and no bmad-loop reference uses it — no action.
6. **Build-auto spec-template drift fired** (a horizon-watch trigger): the
   "Block If" tier is gone (two tiers, Always/Never), the review log records
   a verdict + evidence per finding, and `followup_review_recommended` no
   longer HALTs on `false`. The frontmatter keys our readers consume
   (`status`, `deferred`, "blocking condition") are unchanged, and
   `bmad-spec`'s template and `memlog.py` are byte-identical at 6.12 — marshal
   `core/status.py`, `scripts/deferred_work_intake.py` and CAP-3 need nothing.
7. **Not shipped in 6.12:** the bmad-ticket tree (no `ticket` / `.bmad-obeya`
   path in the tag) and the config.yaml→TOML cutover (the installer still
   generates `_bmad/{bmm,core}/config.yaml`; no cutover language in the
   CHANGELOG). Both watches stay watches.
8. **bmad-loop 0.11.1** (2026-08-24) is installed; the repo copy of
   `bmad-loop-setup` is one line behind (`module_version: 0.11.0`) — CAP-2's
   recurrence. 0.11.1 adds no policy key (CAP-4 holds); it adds a git ≥ 2.34
   floor (`git.version` in `validate`), a hard-stop mode on
   `stop-request.json`, and a mode-exact `graceful_stop_pending` — no marshal
   surface reads stop state today, so there is no CAP-5 gap yet.
9. **The v7 signal is unchanged:** no date, no milestone; the only committed
   breakage is still the shim removal at the v7 cut.

## Whose job this is

**Marshal.** The misaligned surfaces are overwhelmingly marshal's own orbit:
the bmad-loop wrapper and policy chain (AD-16), the status/fleet surfaces, the
seed templates that propagate conventions to new stations, and the factory
docs + SYNC-RUNBOOK that describe the BMAD infra (all live in pyforge-marshal's
planning artifacts). The deferred-work scripts are governed by marshal's
`spec-regenerable-factory`. Detection-side pieces that belong to doctor are
relayed, not absorbed (the split precedent: `bmad-method-version-drift`,
owner doctor). Steward's Epic 14 keeps the *upgrade-apply* half; this Dream is
the *post-upgrade alignment* half — kin, not overlap.

## What it looks like when real

- **No retired skill ID survives in live docs, templates, memory, or code** —
  and a regression guard (the 20-shim list as a meta-test) reds any
  reintroduction between now and the v7 cut.
- **Every spec folder accepts a 6.11 `bmad-spec` update**: all memlogs carry
  frontmatter; memlog-less folders got a genesis-baseline bootstrap.
- **bmad-loop's repo skills match the installed package** after every
  bmad-loop bump (refresh is part of the upgrade verification gate's orbit).
- **Marshal governs the full 0.10/0.11 policy surface** through the four-layer
  chain with deliberate repo defaults, and **speaks the 0.11 status
  vocabulary** (`awaiting-operator` parked runs are named as such everywhere an
  operator looks; `preserve_ref` feeds the escalation-preservation flow).
- **Deferred-work intake reads both sources** (Tier-3 `deferred-work.md` AND
  spec-frontmatter `deferred:` lists), so a hand-driven run's deferrals reach
  the tracked ledger without a human relay.
- **The living factory docs have a named re-grounding owner** and are current
  to 6.11 (plain re-grounding agents per SYNC-RUNBOOK — not waiting on
  upstream's promised-but-unstarted successor capability).

## What is real

**The 6.11 round — all of it (marshal Epic 25, 7/7 done 2026-08-24).** The
retired-ID guard (`test_no_retired_bmad_skill_ids.py`) reds a planted ID; the
three bmad-loop skills were refreshed to 0.11.0; all 22 spec folders accept a
6.11 `bmad-spec` update; the five 0.10/0.11 policy knobs flow through the
AD-16 chain; `marshal status` / fleet-picture speak `awaiting-operator` /
`preserve_ref` / `sweeps_refused` (PR #612); hand-driven deferrals reach the
tracked ledger (PR #721); the living docs were re-grounded with marshal as
the named owner (PR #722). DW-BL011-1/-2 closed with it.

**The 6.12 round — nothing yet.** Every item in § *The 6.12.0 era shift* is
open: the guard still lists the 6.11 shim roster, the rulebooks still have
consumers, CLAUDE.md still points at the dead URL, and the apply itself
waits on the operator (steward Epic 14).

## Constraints

- **Do not adopt what upstream is removing**: no `stories.yaml`, no folder+id
  dispatch, no `{spec-folder}/stories/` migration — the epic-story path is the
  surviving v6 route and v7's build-auto keeps it (V7-10).
- **The AGENTS.md HOLD is lifted (2026-09-05).** The managed `bmad:context`
  block has been live since 2026-09-04 and 6.12's `adopt` intent is the
  rework this Dream waited out; `bmad-project-context audit` is the
  post-upgrade step, and the eight station `project-context.md` rulebooks
  follow D1 — retire, with every consumer migrated first; never leave a file
  nothing loads.
- **Watch, don't build, for the unscheduled**: the TOML cutover and the
  bmad-ticket tree get named triggers (below), not code.
- Retired-name sweeps annotate historical/narrative text with the new name
  rather than rewriting history (a shipped spec's story text may keep its
  original wording with a gloss).
- Shims stay installed through the v7 cut (upstream's own rule). The guard is
  green, so the pre-sweep bar is met, but every apply still passes `--shims`
  explicitly — 6.12 made them opt-in on fresh installs; clones of this repo
  inherit the tracked `.claude/skills/`, so that default bites only a NEW
  repo's `npx bmad-method install`.

## Non-goals

- The **bmad-ticket tracking adapter** — its own future marshal Dream, trigger:
  bmad-ticket lands in a tagged release (sprint feeds, ledgers, promote,
  story-status, fleet-picture, dashboard all ride sprint-status.yaml and stay
  as-is until then).
- The **TOML-cutover symlink migration** — steward Epic 14's watch (CAP-1 must
  flag the cutover release; the named consequence lands in that spec's
  failure-modes).
- **TEA module install / tea-test-review CI gate** — optional adoption, not
  alignment; the repo-custom `bmad_tea_playwright.py` generator stays.
- Upgrading bmad-method/suite versions themselves (steward Epic 14) and
  detecting they're behind (doctor Epic 14 — both shipped or in chain).
- Paige replacement, "explain this system" — zero upstream implementation
  signal; nothing to align to. (The bmad-ux/WDS half resolved: 6.12's module
  registry marks WDS deprecated, folded into `bmad-ux`, and the suite retired
  it 2026-09-05 — see [[bmad-suite-channel-product]].)

## Kinships

[[bmad-method-core-upgrade]] (steward — the apply half; this Dream begins where
an applied upgrade ends) · [[bmad-method-version-drift]] (doctor — the ambient
detection half, incl. CAP-4 suite coverage) · marshal DW-BL011-1/-2 (the two
pre-filed gaps this Dream's chain absorbs) · [[bmad-loop-liveness-footgun]] /
marshal Epic 24 (status-truthfulness kin — the 0.11 vocabulary work sits beside
it) · `_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md` (the reconciler
loop whose 6.11 gaps item 5 closes) · [[bmad-suite-channel-product]] (steward —
the suite side of the same era shift; its roster moved 2026-09-05).

## Realization log

- **2026-08-22** — Dream, Spec and decomposition landed in one commit (`2dc63365fb`):
  `spec-bmad-611-era-alignment` under pyforge-marshal (7 CAPs, 2 companions, status `ready`),
  decomposed as marshal Epic 25 (7 independent stories).
- **2026-08-24** — Epic 25 done, 7/7: 25.1 guard + sweep, 25.2 skill refresh, 25.3 memlog
  migration, 25.4 policy knobs, 25.5 status vocabulary (PR #612), 25.6 deferral intake
  (PR #721), 25.7 living docs + SYNC-RUNBOOK owner (PR #722). Status → `realized` (recorded
  2026-09-05; the flip was owed at the time).
- **2026-09-05** — BMAD-METHOD 6.12.0 re-check (released 2026-09-04): § *The 6.12.0 era shift*
  added; the Spec's memlog gained CAP-8..11 (6.12 retired-ID roster, project-context surface
  follows D1, documentation pointers, bmad-loop 0.11.1 parity) and lifted the AGENTS.md HOLD;
  `horizon-watches.md` re-checked row by row; `alignment-inventory.md` gained the 6.12 table.
  Next: decomposition as a new marshal epic, and the apply itself (steward Epic 14).
