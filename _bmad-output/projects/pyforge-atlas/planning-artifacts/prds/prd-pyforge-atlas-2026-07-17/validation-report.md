# Validation Report — cf_atlas Kedro/Dagster/DuckDB Migration PRD

- **PRD:** `_bmad-output/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md`
- **Rubric:** `.claude/skills/bmad-prd/assets/prd-validation-checklist.md`
- **Run at:** 2026-07-17T02:15:00Z (headless; browser-open skipped)
- **Grade:** Good — *as-reviewed the strict rule gave Fair (2 distinct High
  findings, 0 Critical, no thin/broken dimensions); every finding from both
  reviewers was applied to the PRD in the same run, leaving no open findings.*

## Overall verdict

An unusually strong PRD for an unattended run: the agent-maintainability
thesis is carried consistently from Vision through SM-2, UJ-5, and the
counter-metrics; trade-offs are surfaced with real teeth (null alternative
fairly priced, opportunity cost named once, PRFAQ CONDITIONAL PASS reflected
in scoping rather than buried); and the unattended-intake decision log (§ 9)
makes the headless provenance auditable. What was at risk was done-ness
precision at the seams — the FR-9/SM-4 exception contradiction, a § 4
preamble promising per-FR testability a third of the FRs didn't carry, an
adjective-bar metric — plus dangling references (Q5, the trendshift index
entry).

The adversarial cross-check against spec v5.6 materially sharpened the
picture: FR substance, story arithmetic (32), the five attended events, the
six verify gates, Q-defaults, and the § 12 boundary all verify clean (no
scope drift in either direction), but it caught a fabricated headline
population figure ("~29,000 feedstocks"), an SM coverage hole (the Universal
SBOM family FR-13/16/17 and AC-3's orchestration substance had no validating
metric), an unreconciled `bmad-switch` project-slug hazard the repo documents
as an artifact-overwrite near-miss, and three dropped spec § 2 obligations
(TEA/atdd fixtures, CIS two-spine before frontend, § 2.1 agent-legibility).
All findings from both reviewers were applied directly to the PRD in this
run; none required re-elicitation.

## Dimension verdicts (rubric walker)

- Decision-readiness — strong
- Substance over theater — strong
- Strategic coherence — strong
- Done-ness clarity — adequate
- Scope honesty — strong
- Downstream usability — adequate
- Shape fit — strong

## Findings by severity

All findings below are **RESOLVED** — fixes applied to `prd.md` (and
`addendum.md` where noted) on 2026-07-17.

### Critical (0)

—

### High (2)

**[Adversarial F1 / Substance]** — Fabricated "~29,000 feedstocks" literal (§ 1 Vision)
Appears in no source; violates the PRD's own § 9.9 volatile-count discipline;
would mis-size DuckDB partitions / parity runtime / publish budgets.
Fix applied: replaced with the spec-grounded 19,726 full-population figure.

**[Rubric / Done-ness]** — FR-9/SM-4 contradict their own exceptions (§ 4.5, § 7 SM-4)
"Every read-only legacy CLI question answerable from a page" vs. the three
CLI-first exceptions left the D2 bar ambiguous (28 vs 25 CLIs). (Adversarial
F5 concurred.)
Fix applied: both now state the exceptions count via surfaced latest-report
artifacts; the bar covers all 28.

### Medium (8)

**[Adversarial F2]** — SM set orphaned FR-13/16/17 (Universal SBOM family) and AC-3's orchestration substance.
Fix applied: SM-11 (SBOM intake) and SM-12 (orchestration operations, AC-3)
added; § 7 preamble discloses they extend the spec's AC list.

**[Adversarial F3]** — `bmad-switch` slug never reconciled: spec § 2.5/§ 14 say `local-recipes`, the intake created `pyforge-atlas`; CLAUDE.md documents this desync as an artifact-overwrite near-miss.
Fix applied: § 6.2 now names `scripts/bmad-switch pyforge-atlas`
as the loop precondition, explicitly superseding the spec literal; recorded
as § 9.11 and in the Assumptions Index.

**[Adversarial F4]** — Three spec § 2 obligations dropped, not compressed: TEA `atdd` red-phase fixtures (Wave B), CIS two-spine `DESIGN.md`+`EXPERIENCE.md` before frontend (Waves D/G), § 2.1 agent-legibility for dashboards.
Fix applied: TEA/atdd + per-wave operating loop added to § 6.2; CIS two-spine
sentence added to FR-9; agent-legibility consequence added to FR-9.

**[Rubric / Done-ness]** — § 4 preamble overpromised per-FR testability (9 FRs bare).
Fix applied: consequence bullets added to FR-12/13/15/16/18/19/20/21/22;
preamble reworded; FR location map added.

**[Rubric / Done-ness]** — SM-3's bar was an adjective ("materially faster").
Fix applied: threshold fixed in the F1 story spec before the benchmark;
adjudication at the attended F1 event; operator sign-off is acceptance.
(Also closes adversarial F7's SM-3 half.)

**[Rubric + Adversarial F6]** — SM-2's "≥ ~21/32 loop-driven" unadjudicable.
Fix applied: floor pinned to the 11 committed LOOP-S stories; ~21/32 declared
a recorded target, not a gate.

**[Rubric / Downstream usability]** — Q5 cited (FR-22) but unexplained in § 8/§ 9. (Adversarial F11 concurred.)
Fix applied: § 8 preamble states Q5 resolved → FR-22/Wave H and retired;
ordinal numbering dropped; "gates" defined.

**[Rubric mechanical, raised]** — Assumptions Index roundtrip broken (trendshift entry pointed at absent content; untagged entries).
Fix applied: conditional-surface note added under the § 6.1 table; index
split into tagged elicitation gaps vs recorded verification debt.

### Low (7)

**[Adversarial F7 / SM-1 half]** — "zero material drift" cited loosely. Fix:
Q1 operationalization inlined into SM-1.
**[Adversarial F8]** — `parity-diff` span propagated one side of a spec
self-contradiction (B1–B4 vs B1–B3). Fix: B-row + addendum § 3 now read
build B1–B3 / consume B4, with the spec discrepancy flagged.
**[Adversarial F9]** — "Phase P never loop-reachable" was silently invented
policy. Fix: derived-hardening derivation stated in the risk row and recorded
as § 9.12.
**[Adversarial F10 + Rubric]** — Wave-E gate cell read as an omission. Fix:
"no new gate (§ 2.5 assigns Wave E none)".
**[Adversarial F12]** — UJ-2 conflated the KEV overlay with the Basilisk
dataset. Fix: reworded — Basilisk advisory; KEV via `cisa_kev` overlay.
**[Rubric]** — "live-confirmed" undefined (FR-9). Fix: defined inline with
the seven named CLIs.
**[Rubric]** — "the two coincident 83.7% literals" unactionable (FR-20). Fix:
both measurements named; re-verify pointer to spec § 15 evidence gists.
(Plus: "none v1-blocking" vs "gates" ambiguity — resolved by the § 8 "gates"
definition; "actionable views" glossed in Q1.)

## Mechanical notes

- FR-1..FR-22 present exactly once; FR location map now in § 4 preamble.
- Story arithmetic 1+3+10+2+3+2+4+3+4 = 32 ✓; attended events = the spec's
  five (B4, C1, D3, F1, G2); verify gates = the spec's six, correctly placed;
  Q-gating waves correct.
- Glossary drift: none. UJ protagonists: all named.
- Numbers verified green post-fix (see review-adversarial-general.md
  "Checked CLEAN" for the full list: exit enum, TTLs, 46/23 MCP tools, 28
  CLIs, schema v29, GX 1.18.2 cap, 8.9 h / 72.4% / 85.3% / 90-day / ≤1,000
  batch, 1800 s cap, ECMA/CEP/CRA dates).

## Reviewer files

- `review-rubric.md` (rubric walker subagent — verdict: approve after
  targeted edits; 0 Critical / 1 High / 4 Medium / 4 Low + 2 mechanical)
- `review-adversarial-general.md` (adversarial subagent, line-level
  cross-check vs spec v5.6 at intake HEAD `4cf1b74` — 0 Critical / 1 High /
  5 Medium / 6 Low + a checked-clean inventory)
