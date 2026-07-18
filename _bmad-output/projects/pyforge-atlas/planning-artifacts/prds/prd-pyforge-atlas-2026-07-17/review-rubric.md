# PRD Quality Review — cf_atlas Kedro/Dagster/DuckDB Migration

Reviewed against `.claude/skills/bmad-prd/assets/prd-validation-checklist.md`.
Reviewed: `prd.md` + `addendum.md` (2026-07-17, unattended intake from spec v5.6).

Calibration applied: this PRD was produced headless from an authoritative intake
spec and deliberately delegates binding detail (story ACs, per-phase contracts,
§ 3.3 counts) to cited spec sections. Delegation itself is not penalized below;
findings target only places where the PRD's *own* text is ambiguous,
self-contradictory, untestable, or would mislead a downstream architect or
epic-writer who reads the PRD first.

## Overall verdict

This is an unusually strong PRD for an unattended run: the agent-maintainability
thesis is carried consistently from Vision through SM-2, UJ-5, and the
counter-metrics; trade-offs are surfaced with real teeth (null alternative
fairly priced, opportunity cost named once in § 10, PRFAQ CONDITIONAL PASS
reflected in scoping rather than buried); and the unattended-intake decision
log (§ 9) makes the headless provenance auditable. What's at risk is
done-ness precision at the seams: the FR-9/SM-4 "every read-only legacy CLI"
claim contradicts its own three exceptions, the § 4 preamble promises testable
consequences that roughly a third of FRs don't carry in the PRD body, and one
dangling reference (Q5) plus one broken Assumptions Index entry would send a
downstream reader on a detour. All fixable with targeted edits; none requires
re-elicitation.

## Decision-readiness — strong

Decisions are stated as decisions, with what was given up named. § 10 "Why Now"
names the opportunity cost explicitly ("~32 stories displace feedstock-refresh
throughput") and states why it's acceptable, including the B4 abort ramp
bounding sunk cost. § 11 pairs every major risk with a tripwire and a ramp
rather than a reassurance — the Dagster-under-Prefect row even names the bus
factor and the two exit ramps. The addendum § 1 prices the null alternative
honestly ("~5 stories, zero parity risk, zero new deps") and states the exact
condition under which rejecting it would be wrong — that is the opposite of
smoothing to neutral. § 8's open questions are genuinely open (each has an
adopted default *and* a scheduled re-check at its gating wave, not a rhetorical
answer). The PRFAQ verdict is recorded as CONDITIONAL PASS and visibly shapes
AC-7/SM-3 scoping and SM-C1.

### Findings

- **low** "None v1-blocking" vs. per-wave gating language (§ 8) — the preamble
  says the open questions are "none v1-blocking," yet each is labeled as
  "gates B4," "gates Wave C," "gates D3," etc. The preamble's "the wave gate
  drains the question before dependent stories run" mostly resolves this, but
  a reader can still ask whether a story is blocked until the re-check
  completes or merely flagged. *Fix:* one sentence in § 8: "'gates' means the
  named wave/story may not start until the question's re-check is recorded;
  nothing blocks PRD approval or earlier waves."

## Substance over theater — strong

No furniture detected. The four § 2.1 roles each drive identifiable decisions
(Operator → UJ-1/FR-6 per-node timeouts; CFE agents → FR-7/FR-11; BMAD
execution agents → UJ-5/SM-2; CI → FR-18), and § 2.2 Non-Users does real
scoping work by naming who is deliberately *not* served and why (market
scenario ranking, SIG gating). The Vision (§ 1) could not swap into another
PRD — it names the 10,000-LOC orchestrator, the 3–4 h network-bound rebuild,
and explicitly disclaims the "engine-swap cold-start miracle." NFR-adjacent
content carries product-specific bounds (GX capped at conda-forge 1.18.2 with
the upstream `<3.14` reason, EPSS 0–100 normalization, per-dataset TTLs with
concrete values). The counter-metrics section (SM-C1..C4) is the strongest
anti-theater device in the document: each one names a specific failure mode of
its paired metric.

## Strategic coherence — strong

The thesis is stated in § 1 and load-bearing throughout: "the migration's
load-bearing justification is **agent-maintainability**." SM-2 validates
exactly that thesis (a new signal lands with zero hand-written machinery,
demonstrated in-effort by B8/B9/B10), UJ-5 is explicitly labeled "the
agent-maintainability journey the whole migration exists for," and § 4.10
subordinates the attractive new-signal work to it ("riders on the migration,
never its justification"). Counter-metrics exist and are pointed (SM-C1 blocks
the performance overclaim the PRFAQ killed; SM-C3 blocks scope creep via
signal-count vanity). MVP scope kind is coherent: a platform migration with
severable waves and value at each boundary, and the wave ordering follows the
thesis (harness first, parity gate before retirement, riders not gating).

## Done-ness clarity — adequate

The best FRs here are genuinely unforgiving: FR-1's "a non-JFrog host never
receives `X-JFrog-Art-Api`," FR-3's "unit test proves stale rows re-fetch,
fresh rows skip," FR-5's grep-gated "no `sqlite3` import outside the retired
legacy tree," FR-17's NBSP-fixture consequence. The named verify gates
(Glossary + addendum § 3) give most waves a deterministic pass/fail. But the
dimension the rubric says to be unforgiving on has three real soft spots, one
of which is a self-contradiction.

### Findings

- **high** FR-9/SM-4 contradict their own exceptions (§ 4.5, § 7 SM-4) — FR-9
  names three CLIs that "stay CLI-first with latest-report artifacts surfaced
  read-only" (`add-handoff`, `inventory-match`, `library-futures`), yet its
  first consequence is "every read-only legacy CLI question is answerable from
  a page," and SM-4 repeats "every read-only legacy CLI question answerable
  from a Vizro page." At least `inventory-match` and `library-futures` are
  read-side CLIs, so a downstream epic-writer reading the PRD first cannot
  tell whether the D2 acceptance bar is 28 CLIs or 25, and whether a surfaced
  latest-report artifact *counts* as "answerable from a page." *Fix:* rephrase
  both to "every read-only legacy CLI question is answerable from a page,
  where for the three named exceptions 'answerable' means the latest-report
  artifact is surfaced read-only" (or scope to "except the three § 4.5
  exceptions").
- **medium** § 4 preamble overpromises per-FR testability (§ 4 intro vs.
  FR-12, FR-13, FR-22) — the preamble states "Each FR states the capability
  contract and its key testable consequences," but FR-12 (lineage/OTel),
  FR-13 (SBOM normalization), and FR-22 (factory layer) carry no consequence
  bullet and no inline testable bound in the PRD body; FR-16/18/19/20/21 have
  no bullets either, though their prose embeds fixtures/guards and SM-6/SM-7
  cover them. Delegation to story ACs is the declared design, but the preamble
  as written is false, and FR-12/FR-13/FR-22 give an epic-writer nothing
  testable without opening the spec. *Fix:* either add one minimal consequence
  per bare FR (e.g., FR-12: "a run produces OpenLineage events for every node
  and one end-to-end OTel trace resolving to a named API call"; FR-13: "each
  core-tier manifest fixture normalizes to CycloneDX preserving `cfe:*` and
  `?channel=conda-forge`"; FR-22 can point at SM-10's four fixture tests) or
  soften the preamble to "states the capability contract; testable
  consequences appear where the PRD adds them, otherwise the cited story ACs
  are the test surface."
- **medium** SM-3's bar is an adjective (§ 7) — "materially faster than the
  legacy full-rebuild pattern" is exactly the "reasonable performance" pattern
  the rubric flags. The PRFAQ-honest framing (evidence, not promises) is
  right, but a primary metric still needs a decision rule. *Fix:* state how
  pass is decided, e.g. "F1 (attended) records warm-incremental vs.
  legacy-full-rebuild wall-clock; the operator accepts or rejects at the F1
  boundary event against the recorded evidence" — making the attended event
  the explicit adjudicator, or set a floor (e.g., single-phase refresh re-runs
  <N% of nodes).
- **medium** SM-2's autonomy threshold is approximate (§ 7, § 6.2) —
  "≥the planned share of stories (~21/32) executing loop-driven without gate
  removal" combines a ≥ with a tilde; § 6.2 itself says "11 at spec-approval,
  ~10 relaxable." As written no one can say whether 19/32 passes. *Fix:* pin
  the floor to the firm number ("≥ the 11 committed LOOP-S stories, target 21")
  or declare the count recorded-not-gated.

## Scope honesty — strong

§ 5 Non-Goals is doing real work — twelve concrete exclusions, several with the
reason and the re-entry condition attached ("promotion requires measured
evidence → FR + story"; "recorded hook: `variants.yankedReason`"). § 6.3 adds
the MVP-specific deferrals. The unattended-intake protocol is handled about as
honestly as it can be: § 9 opens with "No human elicitation occurred," tags the
two genuinely invented calibrations (§ 9.7, § 9.8) with `[ASSUMPTION]`, and
§ 9.6 admits the groundtruth CLIs could not run and converts that into a
Wave-0 precondition rather than papering over it. Open-items density (6 open
questions, all with adopted defaults + scheduled re-checks; 4 indexed
assumptions) is appropriate for a chain-top PRD whose contract lives in a
v5.6 analysis-complete spec.

## Downstream usability — adequate

This is a chain-top PRD (feeds architecture → epics → loop execution), so this
dimension carries weight. The Glossary is genuinely load-bearing — Phase/Node/
Dataset/Wave/Verify gate are used identically across FRs, § 6, and § 7, and
SM↔FR↔AC cross-mapping is explicit in every metric ("Validates FR-x (AC-y)").
FR-1..FR-22 are all present exactly once. But several references dangle inside
the PRD's own text, and each one forces a spec detour the compression design
didn't intend.

### Findings

- **medium** Q5 is cited but never defined (§ 4.11 vs. § 8, § 9.3) — FR-22
  opens "Committed scope (Q5 resolution): …" but § 8 lists only Q1–Q4, Q6, Q7
  ("numbering stable"), and § 9.3 likewise omits Q5. A reader cannot tell
  whether Q5 was resolved-and-closed, forgotten, or deliberately excluded —
  and § 8's claim to carry "the spec's § 11 set" reads as complete when it
  isn't. *Fix:* one line in § 8 or § 9: "Q5 (Wave-H scope) was resolved to
  full commitment during spec v5.x and is closed — recorded in FR-22; it is
  omitted here because it is no longer open."
- **low** "Live-confirmed consumer CLIs port first" (§ 4.5 FR-9) —
  "live-confirmed" is not in the Glossary and not defined anywhere in the PRD
  or addendum; an epic-writer sequencing D2 cannot derive the ordering from
  the PRD. *Fix:* gloss it inline ("CLIs with observed consumer usage per the
  spec's § X audit") or drop the sentence and let the story AC carry it.
- **low** "the two coincident 83.7% literals" (§ 4.10 FR-20, echoed by SM-7's
  guard list) — the literals appear nowhere else in the PRD or addendum, so
  the re-verify instruction is unactionable without the spec. *Fix:* either
  name what the two literals measure or reduce to "re-verify the calibration
  literals at B9 (spec § …)."
- **low** Interim-store sequencing is inferable but never stated (§ 4.1 FR-4,
  § 4.2 FR-5, § 4.5 FR-8) — legacy (and `phase_state`) retire at B4 parity
  (Wave B); BSL is already "Ibis → DuckDB" in Wave D; but "DuckDB replaces
  SQLite" is Wave F. A reader can misread FR-5 as DuckDB's first appearance,
  or wonder what serves reads in Waves C–E after retirement. The spec
  presumably resolves this; the PRD's own text leaves a gap an architect
  would have to close by guessing. *Fix:* one sentence in § 4.2 or § 6.1:
  what the canonical store is between B4 retirement and F1 consolidation
  (e.g., "Parquet partitions are canonical from Wave A; Wave F removes the
  last SQLite read paths and consolidates compute").

## Shape fit — strong

The shape is right and — better — explicitly declared: § 2.3 announces
"*Lighter form (internal tooling, solo operator + agent workforce)*" and § 9.7
records the calibration as an assumption. Capability-spec structure with five
compact journeys is appropriate for a single-operator internal platform; the
UJs that exist are load-bearing (each is cited by the FRs that realize it,
and UJ-5 anchors the thesis). Success metrics are operational/acceptance-shaped
rather than user-facing, which matches the product. Brownfield references
(legacy 1800 s `cf_atlas_core` cap, `_http.py` JFrog injection, `phase_state`
table, the 28 CLIs) are specific and consistent with the repo's documented
architecture. No over-formalization detected — if anything the restraint
(four roles, five UJs, no invented personas) is a model for headless runs.

## Mechanical notes

- **FR continuity:** FR-1..FR-22 all present, each exactly once. Ordering is
  thematic, not numeric (FR-11 appears in § 4.4 before FR-8 in § 4.5;
  FR-16/17/18 in § 4.7 before FR-14 in § 4.8). Declared as spec-numbering
  preservation — acceptable, but a section-header FR map (one line listing
  which § holds which FR) would save downstream lookups.
- **Story arithmetic:** § 6.1 wave table sums to 32 (1+3+10+2+3+2+4+3+4),
  matching the claimed "Waves 0 + A–H, 32 stories." Verify-gate names are
  consistent across Glossary, § 6.1, and addendum § 3 (six tasks).
- **Assumptions Index roundtrip: one broken entry.** § 12's fourth entry cites
  "§ 6.1 — trendshift Phase T remains conditional surface," but § 6.1 (and the
  rest of the PRD body) never mentions trendshift or Phase T — the index
  points at content that isn't there. Either add the caveat to § 6.1/§ 0 (it
  belongs with the § 3.3-snapshot count discipline) or re-point the index
  entry. Also: § 9.6 and the § 6.1 entry are indexed without inline
  `[ASSUMPTION]` tags (only § 9.7/§ 9.8 carry tags) — harmless drift, but the
  roundtrip convention is inconsistent.
- **Open-question numbering:** Q5 gap in § 8/§ 9.3 vs. the FR-22 citation —
  covered as a Medium finding above (Downstream usability).
- **Glossary drift:** none found. "Verify gate," "parity," "bootstrap
  profile," "derived layer," and "ComplianceReport" are used identically in
  every occurrence. The frozen exit-code enum {0, 1, 2, 130} appears once
  (Glossary) and is referenced, not restated — good discipline.
- **UJ protagonists:** all five UJs have a named protagonist (rxm7706, a BMAD
  agent, the operator/Claude Code, CI, an agent). "CI" as protagonist is fine
  for this shape.
- **Cross-references that resolve:** every "(FR-x, FR-y)" in § 2.3 and every
  "Validates FR-x (AC-y)" in § 7 resolves to a present FR; addendum § 6 config
  values match PRD § 9.6.

## Severity summary

| Severity | Count |
|---|---|
| Critical | 0 |
| High | 1 |
| Medium | 4 |
| Low | 4 |

(Plus mechanical notes: 1 broken Assumptions Index roundtrip, 1 tag-convention
drift.)
