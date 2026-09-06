---
title: "PRD: the whole bmad-suite is wielded, kept current, and carried into the foundry"
status: "final"
created: "2026-09-06"
updated: "2026-09-06"
chain: "bmad-suite-lifecycle"
owner: "steward"
inputs:
  - "../../../../../../docs/dreams/bmad-suite-lifecycle.md"
  - "../../specs/spec-bmad-suite-lifecycle/SPEC.md"
  - "../../specs/spec-bmad-suite-lifecycle/adoption-register.md"
  - "../../specs/spec-bmad-suite-lifecycle/release-cadence.md"
  - "../../specs/spec-bmad-suite-lifecycle/cutover-readiness.md"
  - "../../specs/spec-bmad-suite-lifecycle/open-items-register.md"
---

# PRD: the whole bmad-suite is wielded, kept current, and carried into the foundry

## 0. Document Purpose

This PRD decomposes `spec-bmad-suite-lifecycle` into functional requirements an epic pass can
group and a `bmad-build` session can implement. **The SPEC is the contract; this document is its
decomposition.** FR-1..FR-10 map 1:1 to CAP-1..CAP-10. Features are grouped by delivery seam —
the same seams the epics use. Mechanisms (provisioning backends, the equivalence-check method,
the `--no-shims` apply, the studio layout, the rehearsal recipe) live in `addendum.md`, so the
architecture pass confirms them rather than reopening them. Station relays are named inside each
FR's acceptance; they are stories in the relayed station's `epics.md`, never extra FRs here.

## 1. Vision

PyForge packages thirteen bmad-suite members and wields a fraction of them. When this PRD is
realized, every member has a verdict and — when wielded — one named station that reaches for it
in daily work; the BMAD-METHOD release cadence is a runbook with owners instead of a heroic
session; and the BMAD estate (`_bmad/`, `.claude/skills/`, `_bmad-output/`, the eight loop homes)
is provably ready for the python-foundry cutover: no shims, no rulebooks, no ungoverned in-place
edits, memlogs that re-render their Specs.

## 2. Target User

**The operator** (rxm7706): decides verdicts, gives outward goes (budget, new repos, upstream
PRs), reads the readiness checklist before opening the foundry.

**The eight station agents** (atlas, doctor, herald, marshal, mason, scribe, steward, warden),
each acting through its persona skill and drained by Marshal: they are the wielders.

### 2.1 Jobs To Be Done

- Reach for the right suite tool without reading a catalog (routing lives where the persona looks).
- Take a new BMAD-METHOD release through the fleet in one pass, every step owned.
- Know, before the cutover opens, exactly which BMAD-estate prerequisite is still red and who owns it.

### 2.2 Non-Users

Downstream conda-forge consumers of the suite recipes (Mason's factory flow serves them);
mybmad-dashboard end users (it stays an opt-in local view).

### 2.3 Key User Journeys

**UJ-1 — Herald ships a release note and a station video.** Herald's persona skill names
`bmad-os-changelog` for the notes and the manticore studio for the video; the studio sits outside
the repo, renders from the deck's speaker notes, and the `.mp4` never enters git.

**UJ-2 — The operator processes bmad-method 6.13.0.** Doctor's drift check warns; the operator
opens `release-cadence.md`, runs the steward pre-flight, applies, proves landed, hands Marshal the
era round, hands Mason the recipe refresh, flips statuses — nothing improvised, every step owned.

**UJ-3 — Warden reviews a PR with two more lenses.** `tea-test-review` and `bmad-os-review-pr`
run as advisory findings beside Warden's gate; the gate's verdict is unchanged by them.

**UJ-4 — Steward checks cutover readiness.** `cutover-readiness.md` reads green on every P line;
`steward upgrade bmad-core` pre-flight lists zero ungoverned local customizations; Story 44.3 is
unblocked on the BMAD side.

## 3. Glossary

- **Suite member** — one of the thirteen active `recipes/bmad-suite/suite-members.yaml` rows.
- **Install class** — how a member reaches the tree: installer-tree, runner-home, own-installer,
  module, cli, plugin-path, scaffold, vscode-extension (`install-class-playbook.md`).
- **Wielder** — the one station whose persona skill routes to a skill (Charter: skills are
  wielded, never worn).
- **Adoption register** — the companion table that governs wiring; a row change is the only way
  wiring changes.
- **Era round** — one round of CAPs on `spec-bmad-611-era-alignment` per BMAD-METHOD release.
- **Readiness P / G lines** — the prerequisites and gaps in `cutover-readiness.md`.

## 4. Features

### 4.1 Wielding — every member has a verdict, a path and a station

#### FR-1: The adoption register governs wiring *(CAP-1)*
The register holds thirteen rows (verdict, wielder, provisioning path, hazards, status) and is the
only place wiring changes. Acceptance: pipeline-truth's `wired` column agrees with the register
13/13; the channel-product "never wire-everything" constraint and the one-front-door row-6 triage
are superseded/closed by memlog; the register's posture section names both.

#### FR-2: The module wave lands by install class *(CAP-2)*
utility-skills, TEA and bmad-builder are provisioned through `steward provision --module`, and CIS
is re-provisioned. Acceptance: `--list-modules` reports the four installed; the retired-ID guard and
integrity meta-tests stay green; the ten CIS `SKILL.md` carry `--project-root`; a test proves bmb's
`cleanup-legacy.py` is never invoked. Relays: steward 46.2, 46.3, 46.4, 46.8.

#### FR-3: Every adopted skill has one wielding station *(CAP-3)*
The routing table (register § 2) maps each adopted skill to one station; that station's persona
skill and the AGENTS.md managed block cite it; CLAUDE.md carries none of it. Relays: herald 18.2,
doctor 20.4, warden 11.1, scribe 7.1, marshal 31.6, atlas 24.1, steward 46.2/46.4/46.5.

### 4.2 TEA — the test-architecture module replaces the generator

#### FR-4: TEA is fully adopted *(CAP-4)*
TEA's `bmad-testarch-*` workflows produce every station's `planning-artifacts/test-architecture.md`;
`tea-test-review` runs as a Marshal review lens and a Warden advisory finding; the repo generator
`_bmad/scripts/bmad_tea_playwright.py`, its two marshal meta-tests and its two pixi tasks retire.
Acceptance: 8/8 documents regenerated by TEA with an equivalence check recorded against the
generator's last output; `tea-test-review --base origin/main --min-score N` exits with a real code
on a fixture PR; generator and tests deleted in the same story; Warden's verdict unchanged.
Relays: steward 46.3, marshal 31.1–31.3, warden 11.2.

### 4.3 Herald's studio and the consented labs skills

#### FR-5: Herald renders through a manticore studio *(CAP-5)*
Manticore is installed in a dedicated studio root outside this repo's `_bmad/`, configured in the
studio's own `_bmad/custom/config.toml`; one station video renders from a deck's speaker notes and
is gitignored. Acceptance: this repo's `_bmad/` is byte-identical before and after; the studio
root is recorded in the register (open question: in-repo gitignored vs `~/pyforge-studio/`).
Relays: steward 46.6, herald 18.1.

#### FR-6: labs-skills arrive by name and by consent *(CAP-6)*
Exactly `mcp-builder` (Atlas), `slides-generator` (Herald), `multi-repo-git-ops` (Marshal) and
`release-please` (Steward) are installed via `npx skills add bmad-labs/skills --skill <name>`.
Acceptance: each has a register row; no other labs skill is present in `.claude/skills/`.
Relays: steward 46.5, atlas 24.1, herald 18.3, marshal 31.6.

### 4.4 Measurement — the reviewer is measured

#### FR-7: The eval-quality pilot runs *(CAP-7)*
Story 45.2 is unblocked: `eval-quality-smoke`, `eval-quality-review-twin-run` and
`eval-quality-review-replay` exist as pixi tasks; one trial cites `pkg/discount.py:17` on the
mutated arm and not on the clean arm; a per-trial `--max-budget-usd` ceiling applies; none of the
three joins `detectors`. Relays: steward 45.2, mason 14.1 (the `__win` variant).

### 4.5 Cadence — one runbook per release

#### FR-8: The release cadence is one runbook *(CAP-8)*
`release-cadence.md` orders detect → catalog → pre-flight → apply → prove-landed → era round →
suite refresh → flips → record, with an owner per step; the `@next` prerelease rehearsal is its
optional dry-run. Acceptance: the next release is processed with zero improvised steps; the
rehearsal recipe has run once, report-only, and its findings are in the core-upgrade memlog.
Relays: steward 46.10.

### 4.6 Cutover readiness — the estate the foundry assumes

#### FR-9: The BMAD estate is provably cutover-ready *(CAP-9)*
`cutover-readiness.md` lists P1–P17 with an owner and G1–G11 with a relay; the gate is every P line
green before Story 44.3. Acceptance: `steward upgrade bmad-core` pre-flight reports zero ungoverned
local customizations; `skf-export` is proven to accept `skills/stations/<x>/`; `_bmad/**` is in
Epic 44's surface; `PROJECTS.md` carries the cutover layout; the foundry Stack has a `bmad-*`
floor row; Epic 44 depends on 14.9 / 30.x; loop-home readiness is defined; the render-HALT and
`frozen-path-changed` detectors exist. Relays: steward 47.1–47.5, marshal 31.4–31.5, doctor
20.2–20.3, and marshal 30.2 (rulebooks).

#### FR-10: The shims are retired *(CAP-10)*
The harness policy names `bmad-build-auto`; the eight loop homes re-render and validate clean;
callers are glossed; the retired-ID guard is widened to the harness file; one `--no-shims` apply
lands `installShims: false` with 21 fewer skill dirs. Acceptance: `bmad-loop validate` 8/8;
`_bmad/_config/manifest.yaml` reads `installShims: false`; the guard stays green. Relays: marshal
30.5 (era-alignment CAP-12), steward 14.9 (core-upgrade CAP-9).

## 4a. Non-Functional Requirements

- **Provision by install class only.** No hand copies into `.claude/skills/`; never
  `cleanup-legacy.py`; never `bmad-module-skill-forge uninstall`.
- **Advisory stays advisory.** TEA and eval-quality outputs never change Warden's gate verdict.
- **Isolation of the studio.** Manticore's upgrade ritual never touches this repo's `_bmad/`.
- **Governed customizations.** Every in-place edit of an installer-owned file is under a spec
  `surface:`; otherwise it lives in `_bmad/custom/**` or is re-applied by core-upgrade CAP-8.
- **History is glossed, not rewritten.** Decks, `docs/specs/`, `pixi.toml` comments keep old names
  with a gloss; live docs and code lead with live names.
- **Ledgers and paths.** Physical-path writes with `BMAD_ACTIVE_PROJECT`; ledgers change only via
  `sprint_plan.py generate` + a scoped `sprint-ledger-sync`.
- **Outward acts need a go.** Upstream PRs, new repos, budget-spending trials.

## 5. Non-Goals (Explicit)

- First-install of bmad-method (the foundry's).
- Refreshing suite conda recipes (Mason's CFE flow).
- mybmad-dashboard into the platform; `bmad-module-template` provisioning; the whole labs marketplace.
- Upstream pull requests.
- The cutover itself (Epic 44).

## 6. MVP Scope

### 6.1 In Scope (first implementation session — the era tail)
FR-10 (harness flip, callers, `--no-shims` apply) with marshal Epic 30 (30.1–30.5) and steward
14.9; FR-2's CIS re-provision and the skf catalog pin (46.7/46.8); FR-8's rehearsal recipe.

### 6.2 Out of Scope for MVP (later sessions, drained by Marshal)
FR-2's three module provisions, FR-3 routing, FR-4 TEA, FR-5 studio, FR-6 labs, FR-7 pilot,
FR-9 readiness stories.

## 7. Success Metrics (binary gates)

- `steward suite pipeline-truth`: 13/13 current and `wired` agrees with the register.
- `steward provision --list-modules`: TEA, bmb, utility-skills, CIS installed.
- One station `.mp4` rendered from Herald's studio; this repo's `_bmad/` unchanged.
- The next bmad-method release processed against the runbook with zero improvised steps.
- `cutover-readiness.md` green on every P line; Story 44.3 unblocked on the BMAD side.
- `_bmad/_config/manifest.yaml` reads `installShims: false`; `bmad-loop validate` 8/8.
- Counter-metric: Warden's PR verdict distribution unchanged by the new advisory lenses.

## 8. Open Questions

- Studio root: `presentations/_studio/` (gitignored, in-repo) or `~/pyforge-studio/`? — owner
  herald + steward, decide at Story 46.6.
- `tea-test-review --min-score`: upstream's 80 or calibrate on ten PRs? — owner marshal, 31.3.
- Routing-note home: persona skill AND AGENTS block, or block only (skf-export rewrites AGENTS.md
  at cutover)? — owner steward, 46.1.
- Trial cost accounting for the pilot: steward budget metering or a local `evals/` ledger? —
  owner steward, 45.2.

## 9. Assumptions Index

- TEA's workflows can cover the generator's output; the equivalence check decides, else FR-4
  narrows to the review lens.
- `steward provision --module manticore` cannot target a studio root; the native `--custom-source`
  path is used until a `--studio` flag earns its keep.
- bmad-builder's five skills and skf's sixteen do not collide by name.
- The 2026-09-06 operator decisions are final; the four open questions are not phase-blockers.
