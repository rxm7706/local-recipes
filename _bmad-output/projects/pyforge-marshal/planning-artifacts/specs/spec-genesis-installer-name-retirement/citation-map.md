# Citation map — every genesis-installer FR/NFR/SC/OQ/K reference

Ground truth for the eventual `bmad-prd`/`bmad-architecture`/`bmad-create-epics-and-stories`
rewrite (deferred per the Spec's constraints). Gathered 2026-08-02 by exhaustive read-only
research across the PRD, architecture, Spec, brief, `epics-genesis-installer.md`, readiness
reports, and cross-file mentions. Supersedes any numbering assumption made before this map
existed — in particular it corrects a claim the governing Dream made before this research ran
(see § Corrections to the Dream).

## FR1..FR62 → FR-66..FR-127 mapping

**Confirmed clean**: in the PRD's satellite section, the 62 FR definitions appear in strict
ascending order, no gaps, no duplicates, `FR1` at line 1330 through `FR62` at line 1483. The
natural sequential map is valid: `FRn` (no dash) → `FR-(65+n)` (with dash).

| old | new | old | new | old | new | old | new |
|---|---|---|---|---|---|---|---|
| FR1|FR-66|FR17|FR-82|FR33|FR-98|FR49|FR-114|
| FR2|FR-67|FR18|FR-83|FR34|FR-99|FR50|FR-115|
| FR3|FR-68|FR19|FR-84|FR35|FR-100|FR51|FR-116|
| FR4|FR-69|FR20|FR-85|FR36|FR-101|FR52|FR-117|
| FR5|FR-70|FR21|FR-86|FR37|FR-102|FR53|FR-118|
| FR6|FR-71|FR22|FR-87|FR38|FR-103|FR54|FR-119|
| FR7|FR-72|FR23|FR-88|FR39|FR-104|FR55|FR-120|
| FR8|FR-73|FR24|FR-89|FR40|FR-105|FR56|FR-121|
| FR9|FR-74|FR25|FR-90|FR41|FR-106|FR57|FR-122|
| FR10|FR-75|FR26|FR-91|FR42|FR-107|FR58|FR-123|
| FR11|FR-76|FR27|FR-92|FR43|FR-108|FR59|FR-124|
| FR12|FR-77|FR28|FR-93|FR44|FR-109|FR60|FR-125|
| FR13|FR-78|FR29|FR-94|FR45|FR-110|FR61|FR-126|
| FR14|FR-79|FR30|FR-95|FR46|FR-111|FR62|FR-127|
| FR15|FR-80|FR31|FR-96|FR47|FR-112| | |
| FR16|FR-81|FR32|FR-97|FR48|FR-113| | |

**Caution**: `prd-pyforge-marshal-2026-07-25/.memlog.md` records that on 2026-08-02 an
unrelated capability set (`spec-pyforge-testing-charter`) was briefly assigned `FR-66..FR-69`
in the live PRD, then reverted the same session (PRD restored byte-identical). The numbers are
free today but have already been used once — if `spec-pyforge-testing-charter` is ever
decomposed into this PRD in the future, `FR-66..69` is now permanently claimed by
genesis-installer content.

## Every FR/NFR-O1/SC/OQ/K citation site, by file

**PRD** (`prds/prd-pyforge-marshal-2026-07-25/prd.md`): satellite section starts line 930.
Bare `FRn` cited at lines 5, 867, 940, 945, 947, 1149, 1179, 1240, 1277, every `- **FRn** —`
definition 1330-1483, plus cross-refs at 1418, 1433, 1479, 1497, 1498, 1526, 1557, 1572, 1578.
`NFR-O1` at 941 (numbering note), 1539 (definition). `SC-01..10` at 941, 1012 (primary), 1020-1028
(table), 1044, 1149, 1240, 1249, 1296, 1512, 1535. `OQ-1..9` at 941, 1567-1585 (definitions).
`K-01..03` at 1038 (header), 1042, 1044, 1047 (definitions). Literal "genesis-installer" at 5,
867, 930, 932-948.

**Architecture** (`architecture/architecture-pyforge-marshal-2026-07-25/architecture.md`):
satellite starts line 661, zero bare-FR before it (clean boundary). Bare `FRn` at 711, 739-745
(L-0N table), 795, 832, 840, 877, 887-905 (code comments), 946-1070 (AD-52..63 rules),
1105-1114 (coverage matrix), 1121, 1207. `NFR-O1` at 1133 only. `SC-0N` at 826, 915, 1039-1040,
1131, 1157, 1202. `OQ-1..9` at 679-681 (explicit note: architecture's own Q- sequence stops at
Q-16), 711, 933-1026 (AD-51..59, each resolves one OQ), 1213-1214 (resolution summary). `K-0N`:
none found. Literal "genesis-installer" at 10, 661, 664-681, 683-699 (already-renumbered
AD table), 701.

**Spec** (`specs/spec-pyforge-marshal/SPEC.md`): only one bare-FR occurrence, line 9
(frontmatter). `NFR-O1`/`SC-0N`: none. `OQ-1..9`: none as such — SPEC.md's own Open Questions
use `F-1..F-6` then bare unlabeled `7..17`; item 17 ("Installer verb mapping," line 254) is
self-referential, not an `OQ-*` feed. `K-01..03` at 206-211 (K-01/K-02, success signal), 258,
260 (K-03, open questions). Literal "genesis-installer" at 8-27, 73, 129-258 (dense —
consolidation notes, contradiction flags, section prose).

**Brief** (`briefs/brief-pyforge-marshal-2026-07-25/brief.md`): clean — no bare-FR/NFR-O1/
SC-0N/OQ-N/K-0N anywhere. Literal "genesis-installer" at 5, 171, 175, 178.

**`epics-genesis-installer.md`** (1212 lines): dense, ~120 unique lines with FR citations —
coverage-matrix header block (68-148), every story's `**FR/AD:**` dependency line, inline
acceptance-criteria citations. All confirmed within FR1-62 range, no bare-FR outside it.
`NFR-O1` at 78, 133, 576, 1068, 1075. `SC-01..10` ownership table 139-148, plus ~20 inline
citations across stories S-9.5 through S-12.5. `OQ-*`: none in this file. `K-01`/`K-02` (no
K-03) at 334, 1008, 1162-1163, 1205-1206.

**Readiness/gate reports**: no FR/NFR-O1/SC/OQ/K citations by number anywhere — only file-path
mentions of the genesis-installer artifacts themselves. No renumbering action needed there.

**Cross-file "genesis-installer" mentions** (no numbering, name only): `docs/dreams/
genesis-installer.md` (the Dream itself, dense), `docs/dreams/pyforge-marshal.md` (74-199),
`docs/dreams/one-front-door.md` (92-113, wiki-links), `docs/dreams/README.md` (159, 163),
`_bmad-output/PROJECTS.md` (64, via "the installer"/`spec-genesis-installer`, not the literal
hyphenated string), `_bmad-output/CHARTER-ALIGNMENT-PLAN.md` (57), `marshal-policy.toml` (36,
comment), `docs/dashboard/generate.py` (638, 928-950 — the dashboard row this Dream targets for
removal), `docs/dashboard/index.html` (1041-1042, JS comment).

## The three smaller namespaces — facts, no decision made here

- **`NFR-O1` vs Marshal's `NFR-1..14`**: one item ("plans/reports are machine-readable and
  human-readable by default"). Closest match: **`NFR-12`** ("Machine-readable everything...")
  is near-identical in substance — likely redundant with, not a genuine addition to, Marshal's
  own sequence.
- **`SC-01..10` vs Marshal's own success-criteria labeling**: **Marshal's PRD does not use
  `SC-N` labels at all** — zero occurrences before the satellite boundary. Marshal's equivalent
  section is **§12 "Success Metrics,"** labeled `SM-1..7` + `SM-C1..3` — a different letter
  scheme entirely. `SC-01..10` has no existing namespace to fold into; the rewrite must decide
  whether to adopt `SC-` as new to Marshal or map each item into the `SM-` scheme.
- **`OQ-1..9` vs Marshal's `Q-1..17`**: **correction to the governing Dream's premise** —
  Marshal's own PRD Open-Questions sequence runs **`Q-1..Q-16` only; `Q-17` does not exist**
  anywhere in the live PRD, architecture, or brief. No `OQ-*` item is cross-referenced anywhere
  in the corpus as feeding into any Marshal `Q-` number — that claim is not borne out by the
  live documents. The closest thing to a "17" is **SPEC.md's own separate, bare-numbered 1-17
  Open Questions list** (not `Q-`-prefixed); item 17 ("Installer verb mapping") is new to the
  Spec (added 2026-07-31/2026-08-02) and self-referential about the verb-collision, not an
  `OQ-*` import.
- **`K-01..03`** ("Kill criteria" — the falsifiers of genesis-installer's own Success Criteria,
  PRD lines 1038-1047): **Marshal's own PRD has no equivalent kill-criteria concept or
  namespace at all.** The rewrite must decide whether to adopt `K-` as new to Marshal (it's a
  useful concept — falsifiers with a pause/rescope trigger) or fold the concept elsewhere.

## Provenance

Produced by a dedicated read-only research pass (background agent), 2026-08-02, dispatched
while `spec-genesis-installer-name-retirement` was being drafted. Zero files were edited during
this research.
