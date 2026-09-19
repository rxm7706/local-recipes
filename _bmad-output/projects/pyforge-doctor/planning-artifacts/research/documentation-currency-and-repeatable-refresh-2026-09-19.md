---
doc_type: research
project: pyforge-doctor
date: 2026-09-19
status: current
subject: Getting the documentation right and making its refresh repeatable — adversarial review of PR #1529 against the doctor docs chain (CAP-48..65) and a target model for documentation currency
triggered_by: PR #1529 review (a parallel session's "persona-based documentation & operational guides")
---

# Documentation currency and a repeatable refresh — 2026-09-19

## 0. The question

PR #1529 (183 files) adds 14 authored pages, 130 boilerplate `README.md` files inside skill
directories, a new Doctor source `docs-map-hygiene` that reds when any `.md` under `docs/` or
`src/platform/` is absent from `docs/MAP.md`, moves five platform runbooks into `docs/`, edits nine
station READMEs, and re-stamps ten Spec baselines. The operator's actual question is broader than
the PR: **how do we get the documentation right, and make refreshing it repeatable — for humans and
for every agent harness?** This document answers that against what the repo already owns.

## 1. What already exists (verified on `main` @ `b105264cca`)

| Layer | What it is | Owner / contract | Currency mechanism today |
|---|---|---|---|
| `docs/MAP.md` | The Diátaxis-adapted map of the **general-facing** layer (four quadrants). Its own text excludes Dreams, Tier-1/2/3, governance, intake, station/package READMEs, skill dirs, publish roots. | doctor — `spec-general-docs-consistency` CAP-63/64/65 (shipped 2026-09-17), `spec-docs-shelf-alignment` CAP-48..54 (Epics 22–23) | none mechanical — a human edits it; CAP-65 checks pointers into it |
| `general-docs-consistency` (doctor source) | Decay of the two authoritative "what Doctor is" sources | CAP-60..62 | detector, **warn-only, fail-open by design (CAP-62)** |
| `governance-currency` (marshal script) | Skill / script / path names in `AGENTS.md`, `CLAUDE.md`, `EXEMPLAR-STANDARD.md`, `test-charter.md` still resolve | `spec-fleet-consistency-standard` CAP-6 | detector, fail |
| `docs/reference/library-llms-full.md` | Catalog of every dependency, **derived from `pixi.toml`** | marshal (`spec-library-catalog-manifest-sync`) | regeneration prompt in the header + `llms-full-check` (fail on ghost/floor drift) — **the exemplar for a generated page** |
| Herald deck `facts.yaml` | Per-deck facts **derived from the ledgers**, stamped `derived_at` + `tree`, re-derived by `deck sync-all`, verified by `deck-facts` | herald (`spec-deck-family-currency`) | generator + stamp + check — **the exemplar for stamped derivation** |
| `docs/how-to/pixi-tasks.md` | Task reference | — | hand-written, already stale (says the `local-recipes` env is the environment) |
| Station READMEs | Package front pages; each is the package's `readme` and ships in the wheel | each station | none |
| `.claude/skills/*/SKILL.md` | 132 skills: 76 BMAD-installed, 11 `bmad-os-*` wielded (steward Story 46.2), 7 SKF `pyforge-*` (exported; `.export-manifest.json`), the rest curated | installer / SKF exporter / steward | the installer **rewrites and deletes** skill-dir contents on upgrade (6.10→6.11: 71 deletions, whole dirs removed) |
| `bmad-os-diataxis` (skill, since 09-07) | "Create, update, fix or refine documentation using Diátaxis + the BMad style guide" | steward wields | LLM-driven, on request |

So the repo already has the two halves a repeatable system needs — a **map with a contract** and
two **generator + stamp + detector exemplars** — but only two pages are generated, and the
map has no enforcement.

## 2. Findings on PR #1529 (adversarial, ranked)

1. **130 `README.md` files inside skill directories carry no information** — every one is the same
   5-line note ("this directory contains SKILL.md; see `docs/MAP.md`"). No harness reads them
   (Claude Code, Cursor, Codex, Gemini, Copilot and Devin's CLI all read `SKILL.md`), and the
   directories are not ours to decorate: the BMAD installer regenerates `.claude/skills/bmad-*` on
   every upgrade (the 6.10→6.11 upgrade deleted 71 files, retiring whole dirs), and the SKF exporter
   regenerates `pyforge-*`. A README left in a retired dir is a ghost skill folder; one in a live dir
   is either overwritten or an unmanaged stray. **Remove all 130.** If a human index of skills is
   wanted, it is one *generated* page (`docs/reference/skills-catalog.md` from `SKILL.md`
   frontmatter) with a drift check — the `library-llms-full.md` pattern — not 130 stubs.
2. **`docs-map-hygiene` contradicts the map it enforces.** It scans every `.md` under `docs/` and
   `src/platform/`, but `docs/MAP.md` § *Outside this map* explicitly excludes governance, intake,
   dashboard, station/package READMEs and skill dirs. On the merged tree it reports **44 unmapped
   files**: `.memlog.md` and `SPEC.md` under `docs/governance/`, foundry frames, intake dumps,
   platform overlay READMEs, section `README.md` index pages — plus ~10 genuinely unmapped how-to /
   reference pages that *are* real map gaps. Wired into `detectors-ci` as **"Always FAIL"** it
   would red every PR until `MAP.md` lists every markdown file in the estate. It also violates the
   doctor docs posture CAP-62 set for this class ("warn-only and fail-open") and ships **no test**.
   Rescope to the map's own contract (the four quadrants; section index pages exempt), warn first,
   fail once green.
3. **The chain is a sketch.** `specs/spec-29-1-check-docs-map.md` is a 32-line hand-written Spec
   (five fields) filed as a story spec; its **CAP-82 and Epic 29 / Story 29.1 collide** with the
   doctor CAP-82 / Epic 29 minted an hour earlier (#1526); no `bmad-spec` derivation, no
   capability-ledger row, a two-line epics stub, and the source docstring cites
   `spec-check-docs-map` — a Spec folder that does not exist. The right home is
   `spec-pyforge-doctor` as an extension of CAP-63/64 (the map) — **CAP-83**, Epic 30.
4. **Laundering re-stamps.** Ten Spec baselines re-stamped (atlas, doctor, herald, marshal,
   testing-charter, mason, scribe, steward, unifying-strategy, warden) on the strength of one
   content-free memlog line each — `(event) Surface reconcile 2026-09-19: updated Diátaxis docs and
   package READMEs` — hand-appended (not through `memlog.py`), naming no path. The same class as
   #1507's marshal re-stamps; the branch is re-merged with `main`'s baseline and only the Specs this
   PR actually touches are stamped, each after a real entry.
5. **The 14 authored pages carry day-one errors** — `fleet-picture` "reads the Tier-3 sprint
   ledgers" (it reads the TRACKED twins; Tier-3 is gitignored), Marshal described as "process
   orchestration, job queuing, deployment coordination", a `pyforge marshal dispatch` grammar
   (`marshal factory dispatch`), paths `src/platform/dashboard/models.py`,
   `src/pyforge/<station>/dashboard/`, `src/shared/packages/pyforge-steward/cli.py` (none exist).
   This is exactly why BMAD's own rule is "agents read code better than prose about code": authored
   overviews rot the day they land unless something regenerates or re-verifies them. The pages are
   worth keeping only with (a) the errors fixed now and (b) a currency mechanism (§ 3).
6. **Platform runbooks moved into `docs/`** (`src/platform/deploy/{README,DR,restore}.md`,
   `overlays/ocp/cluster-bringup.md`, `requirements/README.md` → `docs/how-to/`, `docs/explanation/`).
   This *is* the direction Story 22.5 set (MAP § *Per-file classification: src/platform/*), so the
   moves stand — but four live pointers still name the old paths (`.steward/keys-inventory.yaml`
   recording procedure; steward DW rows' `location:` fields; steward epics/change-proposal prose —
   the latter are historical and stay). The `.steward` pointer is repointed here.
7. **Station READMEs**: nine gain the same `[!NOTE] … see docs/MAP.md` pointer. Harmless, but each
   README is the package's `readme` (ships in the wheel), so the relative link `../../../../docs/MAP.md`
   is dead in every distribution. Keep as a one-line plain-text pointer, not a relative link.
8. **`bmad-os-docs-audit`** (new skill): "scan the footprint, parse the map, find gaps, delegate
   writing to `bmad-os-diataxis`, report". This is the *refresh* half done the LLM way. It is the
   right shape for **authored** pages and the wrong shape for **reference** pages (task lists, CLI
   grammars, detector tables, skill catalogs), which must be generated, not re-written by a model.
   Keep it, scope it to the authored quadrants, and give it a deterministic partner.
9. What the PR got right and is kept: the ten genuine map gaps it found, the section index pages,
   `docs/MAP.md` § *Operator and Framework guides*, the intent behind enforcement, the audit skill.

## 3. Target: documentation currency, repeatable (the model to mint)

Three kinds of page, one registry, one detector, two refresh tools.

**Registry.** `docs/MAP.md` stays the human map; a machine twin `docs/map.yaml` (or frontmatter on
each page — decide in Q2) records for every page inside the map's scope: `quadrant`, `owner`
(station), `kind: generated | authored | pointer`, `sources:` (the files or commands it derives
from), and for generated pages a stamp `derived_at` + `tree` (herald's shape).

**Generated pages** (never hand-edited; a `docs-*` pixi task regenerates each): the pixi task
reference from `pixi.toml` task tables; the station cheat sheet and CLI reference from each station's
`--help` grammar; the detector reference from `scripts/detectors.py`'s registry + `doctor.sources`
registrations (name, scope, owner, exit domain, what it checks); the skills catalog from
`SKILL.md` frontmatter; the environments table from `pixi.toml [environments]`. Each regeneration
writes the stamp; `llms-full-check` is the precedent.

**Authored pages** (explanation, tutorials, how-to narrative): frontmatter names `sources:` (the
Specs/CAPs, modules or how-tos the page explains) and `verified: <date> <tree>`; the refresh is the
`bmad-os-docs-audit` → `bmad-os-diataxis` pass, run on a cadence and after any named source moves,
with the claim-check discipline `bmad-project-context` uses (every command and path in the page
resolves; every count is read from a registry, never typed).

**Detector — `docs-currency` (doctor, replaces the PR's `docs-map-hygiene`).** In one source:
(a) map alignment *within the map's declared scope* (unmapped page inside a quadrant; listed page
missing); (b) generated page stale (a source newer than the stamp, or regenerating changes the
page); (c) authored page stale (a named source moved past `verified:`, or a backticked path /
command in the page no longer resolves — `governance-currency`'s rule applied to every mapped
page); (d) skill-dir hygiene (a file other than the Agent Skills layout in a managed skill dir).
Warn-only first (CAP-62's posture), promoted to fail per check once green — the same ratchet the
coverage gates use. Surfaces in `fleet-picture` ATTENTION like every doctor source.

**Cadence and ownership.** Doctor owns the map, the registry and the detector (it already owns
CAP-48..65). The generators belong to the station whose source they read (pixi tasks → steward,
detectors → doctor, CLIs → each station, skills → steward). The authored refresh is the
`bmad-os-docs-audit` skill, run by the docs-currency finding, not by memory. Every landing
already runs `detectors-ci`; a stale generated page therefore reds the PR that moved its source,
which is the repeatability the operator asked for: the docs are refreshed *by the change that
invalidated them*, not by a periodic campaign.

**Multi-harness.** Generated reference pages are the pages agents should read (they are exact);
authored explanation is for humans. Nothing in `docs/` is copied into a per-tool file — `AGENTS.md`
points at `docs/MAP.md` once (scribe CAP-27 already holds that line).

## 4. Decisions asked of the operator (2026-09-19)

1. Remove the 130 skill-dir READMEs (recommended) or keep them.
2. Registry form: a `docs/map.yaml` machine twin next to `MAP.md`, or frontmatter on each page.
3. Ownership: doctor owns the docs-currency chain end-to-end (recommended; it owns CAP-48..65) or
   split with scribe (whose Dream lists "doc/ADR hygiene" as a curation surface it grows into).
4. Keep the 14 authored pages after correction (recommended) or drop them until generated
   equivalents exist.

## 5. Sources

- `docs/MAP.md` (§ *Outside this map*; § *Per-file classification*), `spec-pyforge-doctor` CAP-48..54, CAP-60..65 (`spec-docs-shelf-alignment`, `spec-general-docs-consistency`), `docs/reference/library-llms-full.md` header + `scripts/llms_full_check.py`, herald `spec-deck-family-currency/facts-ledger.md`, `.claude/skills/.export-manifest.json`, git history of `.claude/skills/` across the 6.10→6.11→6.12 upgrades, `scripts/governance_currency_check.py`.
- Diátaxis — https://diataxis.fr/ (quadrants; "documentation as a map, not a list"); BMAD `bmad-project-context` content rule (no repo overviews in agent instructions — agents read code); Agent Skills layout (`SKILL.md` + `scripts/ references/ assets/`; no README in the spec).
