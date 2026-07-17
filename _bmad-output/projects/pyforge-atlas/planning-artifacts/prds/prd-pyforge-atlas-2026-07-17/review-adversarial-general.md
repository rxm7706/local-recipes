# Adversarial Review — PRD: cf_atlas Kedro/Dagster/DuckDB Migration

- **Reviewed**: `prd.md` + `addendum.md` (2026-07-17, headless intake)
- **Cross-checked against**: `docs/specs/cfe-atlas-datapipeline-kedro-migration.md` v5.6 (the declared authoritative contract), plus `intake-groundtruth-2026-07-17.md`
- **Reviewer stance**: cynical/adversarial. Compression-by-spec-citation was NOT penalized (declared design). Only things that would actively mislead the downstream architect or epics writer were hunted.
- **Method**: line-level verification of every FR number and substance, the 32-story wave table, § 2.5 execution-model claims, § 11 Q-defaults, all 13 § 12 boundary rows, the attended-event and verify-gate inventories, and every numeric literal in the PRD body against the spec text. Supersedes the earlier inline parent pass at this path; its valid findings are absorbed below (F5, F6, F10–F12).

## Verdict

The PRD is substantially faithful to its contract — FR-1..FR-22 substance,
the 0+A–H/32-story structure, the five attended boundary events, the six
verify gates, all six Q-defaults, and the full § 12 boundary reproduce the
spec verbatim-in-intent, and the easy-to-fumble hazards (FR-18 exit-enum
inversion, FR-19 ecosystem-tag/tri-state constraints, FR-20
first-availability rule, the coincident 83.7% flag) carry forward correctly.
But the document sabotages its own loudest discipline claim: it fabricates a
headline population figure the spec nowhere contains, leaves the entire
Universal SBOM FR family without a validating success metric while claiming
AC-derivation, and never resolves which BMAD project slug the execution loop
must switch to — in a repo whose CLAUDE.md documents that exact desync
silently overwriting other projects' artifacts.

**Counts: 0 Critical · 1 High · 5 Medium · 6 Low.**

---

## Findings

### F1 — HIGH — Fabricated "~29,000 feedstocks" literal in the Vision

**Location**: `prd.md` § 1, first sentence: "23 cataloged pipeline phases
build a database of ~29,000 feedstocks' versions, downloads, maintainers,
vulnerabilities, and readiness signals…"

**Evidence**: The figure appears nowhere in spec v5.6, nowhere in
`intake-groundtruth-2026-07-17.md`, and nowhere in the addendum (grep for
`29,000`/`29000`: zero hits). The spec's measured populations are **19,726
feedstocks** (FR-20 full-population run), **21,163 Python packages** (FR-19
live validation), and the 769-vs-813 maintainer universes. Most plausible
genesis: contamination from "schema **v29**" or conda-forge folklore —
neither citable. The PRD's own § 9.9 boasts "volatile-count discipline:
live-surface counts cite the spec § 3.3 snapshot + intake groundtruth rather
than free-standing literals"; this is a free-standing literal ~47% above the
spec's own figure, in the Vision's first sentence. An architect sizing DuckDB
partitions, parity-diff runtime, or the static-Parquet publish budget from
the Vision starts from a wrong universe.

**Fix**: Replace with the spec-grounded figure ("the 19,726-feedstock /
~21k-Python-package population, FR-20/FR-19") or drop the count. All other
numerals in the PRD were verified clean in this review (see the clean list).

### F2 — MEDIUM — Success metrics orphan the Universal SBOM family (FR-13/16/17) and AC-3's core orchestration

**Location**: `prd.md` § 7 preamble + SM-1..SM-10 "Validates" lines.

**Evidence**: § 7 claims derivation "from the spec's whole-migration
acceptance criteria (AC-1..AC-11)". Mapping the claims: SM-1→AC-1/2,
SM-3→AC-7, SM-4→AC-4, SM-5→AC-5, SM-6→AC-6, SM-7→AC-10, SM-8→AC-8, SM-9→AC-9,
SM-10→AC-11. **AC-3** (Dagster owns scheduling + retries; state observable in
the Dagster UI; `pixi run viz` renders the DAG) maps to no SM — SM-8 touches
FR-6 only via Wave-G sensors, G3's corner of FR-6, not its center (cadence
schedules, profiles-as-job-configs, per-node timeouts, the 1800 s defect
retirement UJ-1 celebrates). And no SM validates **FR-13, FR-16, or FR-17** —
the entire § 4.7 SBOM family except its FR-18 terminal gate (SM-6 lists
FR-10/12/18 only). The spec's own AC list shares the SBOM hole, so this is
partially inherited — but the PRD is the artifact claiming its metrics
validate the FRs, and an epics writer using SM coverage as a done-definition
will treat B7/F4's intake/hygiene substance as metric-optional.

**Fix**: Extend SM-6 or add an SM: "each § 4.10 core-tier fixture manifest
round-trips to a schema-valid CycloneDX BOM preserving `cfe:*` +
`?channel=conda-forge`; the NBSP fixture passes; a deptry finding populates
the hygiene axis." Fold AC-3's substance (cadence table encoded; per-node
timeout defect demonstrably retired — C1 AC) into SM-6 or a new SM, noting
explicitly where the spec's AC list is being extended.

### F3 — MEDIUM — Which project slug does the loop switch to? Spec's stale `bmad-switch local-recipes` never reconciled

**Location**: `prd.md` § 6.2 ("Preconditions: hooks approval,
`scripts/bmad-switch`, worktree symlink bootstrap…") vs § 9.6 and
`addendum.md` § 6.

**Evidence**: Spec § 2.5 and § 14 hard-code `scripts/bmad-switch
local-recipes` — written before this intake created the new project slug
`pyforge-atlas` (PRD § 9.6; addendum § 6:
`planning_artifacts` symlinked to
`projects/pyforge-atlas/planning-artifacts`). The PRD's
§ 6.2 elides the slug entirely; nothing anywhere says "the spec's
`local-recipes` switch target is superseded". CLAUDE.md documents precisely
this failure mode as a live near-miss (2026-07-14): a marker/symlink pointing
at the wrong project makes every BMAD write-skill "silently target the
*other* project" — here, architecture/epics for this migration land in (or
overwrite) `local-recipes` artifacts. An executor following spec § 14
literally will do the wrong thing.

**Fix**: State normatively in § 6.2: "Loop precondition: `scripts/bmad-switch
pyforge-atlas` — supersedes spec § 2.5's pre-intake
`local-recipes` literal; deviation recorded." Add to the § 12 Assumptions
Index.

### F4 — MEDIUM — Spec § 2 obligations dropped: CIS two-spine design specs, TEA/atdd, § 2.1 agent-legible dashboards

**Location**: `prd.md` §§ 4.5, 6.2 (omissions).

**Evidence**: Three spec-committed obligations appear nowhere in the PRD or
addendum — dropped, not compressed (no citation points at them):
1. **Spec § 2.4 (CIS)**: CIS planning agents define the read surface and
   output the two-spine `DESIGN.md` + `EXPERIENCE.md` **before writing
   frontend code** — a sequencing constraint on Waves D/G the epics writer
   must schedule; absent from the D-wave rows and FR-9.
2. **Spec § 2.5 (TEA)**: Wave B runs under per-story-spec-approval "with TEA
   `atdd`-generated fixture gates"; spec § 14 makes TEA test-design/atdd the
   red-phase fixture source. PRD § 6.2 summarizes the autonomy ladder but
   drops TEA entirely — yet those fixtures ARE the verify assets the gate
   model rests on.
3. **Spec § 2.1**: dashboards "must use pristine semantic HTML, clear ARIA
   attributes, and deterministic layouts" for web agents; the spec § 13.2
   factory-status row explicitly tags "agent-readable per § 2.1". PRD FR-9/D2
   carries no agent-legibility requirement.

**Fix**: One sentence each: TEA/atdd into § 6.2's Wave-B description; "D2/G1
frontend work is preceded by the CIS two-spine specs (spec § 2.4)" into the
§ 6.1 D-row or FR-9; "pages meet the spec § 2.1 agent-legibility bar" into
FR-9's consequences.

### F5 — MEDIUM — FR-9's consequence contradicts its own exception list (duplicated in SM-4)

**Location**: `prd.md` § 4.5 FR-9 + § 7 SM-4.

**Evidence**: FR-9 names three CLIs that stay CLI-first (`add-handoff`,
`inventory-match`, `library-futures`, latest-report artifacts surfaced only),
then its consequence — and SM-4 — state flatly "every read-only legacy CLI
question is answerable from a page." `add-handoff` escapes via the
"read-only" qualifier (it's a write path), but `inventory-match` and
`library-futures` are read-shaped and their *questions* (per-invocation
match, futures ranking) are explicitly NOT answerable from a page — only
their stale latest reports are. The spec's D2 AC carries the exception inline
in the same sentence; the PRD split them four lines apart and dropped the
qualifier from SM-4 entirely, which is where the epics writer will read it as
an unqualified completeness gate.

**Fix**: Append "(minus the three FR-9 exceptions, latest-report artifacts
only)" to the FR-9 consequence and to SM-4.

### F6 — MEDIUM — SM-2's loop-share clause is an invented, unadjudicable quasi-target

**Location**: `prd.md` § 7 SM-2.

**Evidence**: Spec § 2.5 says ~21 of 32 stories are loop-**drivable** — a
capability estimate, not a commitment; nowhere does the spec fail the
migration if fewer stories end up loop-run. SM-2 promotes "≥ the planned
share of stories (~21/32) executing loop-driven without gate removal" into a
*primary* success metric — with "~" on both sides of the threshold, it cannot
be scored, and the only firm number in § 6.2 is the 11 spec-approval stories.
The PRD itself senses the danger: SM-C2 exists purely to counteract the
pressure SM-2 creates. A metric needing its own counter-metric in the same
section is a design smell.

**Fix**: Keep SM-2's testable core (B8/B9/B10 land through declared machinery
with zero hand-written checkpoint/TTL/backoff code); demote the share to an
observation — "record the realized loop-driven share vs the ~21/32
drivability estimate" — or floor it at the 11 committed LOOP-S stories.

### F7 — LOW — "Zero material drift" / "materially faster" carried without their operationalizations

**Location**: `prd.md` § 7 SM-1, SM-3.

**Evidence**: Both phrases are spec-verbatim (Q1 default; AC-7) — inherited
weasel, not invented — but the PRD is the tier that should pin them. Q1's
default ("exact row-count + value parity on the actionable views;
timestamp/ordering-only diffs benign") IS SM-1's operationalization, yet SM-1
cites "Q1's tolerance" loosely while the concrete rule sits in § 8. SM-3 has
no ratio or floor at all; pass/fail rests on attended judgment at F1.

**Fix**: SM-1: inline "(= exact row-count + value parity on the actionable
views, § 8 Q1)". SM-3: "threshold fixed in the F1 story spec before the
benchmark runs; F1 records the evidence."

### F8 — LOW — `parity-diff` build span "B1–B4" propagates one side of a spec self-contradiction

**Location**: `prd.md` § 6.1 Wave-B row + `addendum.md` § 3 ("B1–B4") vs spec
Story B4 AC ("built incrementally through B1–B3") vs spec § 2.5 ("through
B1–B4").

**Evidence**: The spec disagrees with itself by one story; the PRD adopted
the § 2.5 reading without flagging it. Harmless functionally, but an epics
writer generating story deliverables will place the final harness increment
in the wrong story depending on which line they read.

**Fix**: Parenthetical in the B-row: "(spec § 2.5 says B1–B4, B4's AC says
B1–B3 — treat B1–B3 as build, B4 as consume + attended sign-off)". Optionally
file the one-word spec fix.

### F9 — LOW — Risk table invents "Phase P never loop-reachable"

**Location**: `prd.md` § 11, last row.

**Evidence**: The spec constrains Phase P to `PHASE_P_ENABLED=1`,
admin-profile-only, never a default schedule, and makes all loop gates
non-credentialed — but never states "never loop-reachable" as a rule. The
stronger formulation is directionally sensible, but it is silently invented
policy in a document whose § 9.1 swears "nothing was invented"; later readers
will cite it as if the spec said it.

**Fix**: Add to § 9 as an explicit derived-hardening decision, or soften to
the spec's actual terms.

### F10 — LOW — Wave-E gate cell "(E rides prior gates)" reads as an omission, not a decision

**Location**: `prd.md` § 6.1, E-row gate column.

**Evidence**: Spec § 2.5 deliberately assigns Wave E no new verify gate (the
six named gates cover A–D, F–G entry points). The PRD's parenthetical doesn't
say that was deliberate; a reviewer hunting gate coverage will flag E as a
hole.

**Fix**: "no new gate by design (§ 2.5's six gates; E stories verify against
existing gates)".

### F11 — LOW — § 8's ordinal numbering shadows the stable Q-numbers; Q5's retirement unexplained at point of use

**Location**: `prd.md` § 8 list ("1. Q1 … 5. Q6 … 6. Q7").

**Evidence**: The spec keeps Q-numbering stable across versions precisely
because other artifacts cross-reference it, and it explains Q5's retirement
in § 11's preamble. The PRD renders a 1–6 ordinal list over Q1–Q7-minus-Q5;
grep for "Q5" in § 8 finds nothing (the resolution hides in § 4.11's "(Q5
resolution)"). A downstream reader reconciling question sets burns time on
the phantom gap.

**Fix**: Drop the ordinals; add one line: "Q5 was resolved and retired — its
outcome is FR-22 (spec § 11 preamble)."

### F12 — LOW — UJ-2 conflates the KEV overlay with the Basilisk dataset

**Location**: `prd.md` § 2.3 UJ-2: "passes a structured
'KEV-affecting-current on libtiff' payload … (FR-7, FR-11, FR-19)".

**Evidence**: KEV-affecting-current is the Phase G / `cisa_kev`-overlay
concept (§ 3.3 vulnerability read-path contract) — FR-19's `basilisk_vulns`
dataset carries OSV advisories, not KEV flags. Spec's live Basilisk examples:
libuuid (CVE-2026-3184, 203M downloads), libtiff, libarchive, perl. Harmless
as narrative, but an architect could read it as "Basilisk carries KEV
status" and design the join wrong.

**Fix**: Reword to "a Basilisk advisory on libtiff" or attribute the KEV
verdict to the `cisa_kev` overlay explicitly.

---

## Checked CLEAN (so downstream doesn't re-litigate)

- **All 22 FRs**: numbering, wave placement, story citations, and binding
  constraints (per-host credential scoping as fix-not-port; 19→20
  `resolve_*_urls`; per-dataset TTLs 7 d/30 d/1 d/90 d; Phase P/K/F/H/B.5
  engineering contracts; ~44-feedstock maintainer delta at B1/B4; GX capped
  at conda-forge 1.18.2, upstream `<3.14` @1.19.0; kedro-mcp never
  load-bearing; four-axis ComplianceReport with `security` from
  `inventory-match`/`cve`, no osv-scanner re-invocation; frozen exit enum
  {0,1,2,130} + inverted-enum reconciliation via
  `INVENTORY_MATCH_LEGACY_EXIT`; FR-17 (a)–(d) incl. the NBSP fixture;
  Basilisk ≤1,000/batch, name-not-ecosystem matching, tri-state
  `fix_available`, 85.3% of 5,101; FR-20 90-day gate + first-availability
  rule + 8.9 h / 72.4% baseline + the 83.7% re-verify flag; FR-21 four-way
  split, inferred `not-in-tracker`, `version_status.v2.json` excluded;
  FR-22's four deliverables + conda-forge-provisioned storage).
- **Story arithmetic**: 1+3+10+2+3+2+4+3+4 = 32; wave contents and H-story
  modes (H1/H3/H4 LOOP-E, H2 dev-auto) match spec § 9.
- **Attended events**: exactly the spec's five (B4, C1, D3, F1, G2).
  **Gates**: exactly the spec's six, at the right stories; Q-gating waves
  correct (Q1→B4, Q2→C, Q3→D3, Q4→G2, Q6→B5, Q7→B8).
- **Q-defaults**: Q1–Q4, Q6, Q7 verbatim-in-intent, incl. Q3's bounds (no
  litellm on the py3.14 floor; copilot-api ineligible) and Q2's
  acquisition-watch dimension.
- **§ 12 boundary**: all 13 spec rows present in § 5; the OSV-export /
  public-dashboard bullet correctly sourced to § 12.1/MR as
  candidate/deferred, not scope. B8/B9/B10 correctly stated not parity-gated,
  B4 legacy-surface-only, twice.
- **§ 10 dates/standards**: ECMA-424/427, CEP-63 in-flight, CRA 2026-09-11,
  Prefect/Dagster 2026-07-13.
- **Numbers spot-checked green**: 1800 s cap; 46/23 MCP tools; 28 CLIs; 23
  phases (22 registered + Phase I); schema v29; 769 feedstocks (JTBD); ~3 GB
  budget and ~5-story null alternative (addendum); STALE_AFTER_DAYS 14;
  ~856k-component BOM; ~21/32 / 11 / ~10 drivability split.
- **Addendum**: rejected-alternatives, glue-risk roster (kedro-dagster
  bus-factor ≈ 1, `dagster <2.0` pin; kedro-mcp 0.1.2; BSL 0.x), GX lesson,
  verify-task table — consistent with spec §§ 4/13/15. ("25.8M tokens",
  "two-person 0.x" trace to research artifacts, not the spec — acceptable per
  the addendum's declared sources; not independently verified here.)

## Severity summary

**Critical 0 · High 1 · Medium 5 · Low 6.**

*Reviewed 2026-07-17 against spec v5.6 at intake HEAD `4cf1b74`. No files
other than this report were modified.*
