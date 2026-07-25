---
title: Editorial Review — Unity Data Stack PRD
reviewer: editorial
date: 2026-07-25
verdict: conditional-pass
---

# Editorial Review: Unity Data Stack PRD

Scope: `prd.md` (1,360 lines, §0–§17) and `addendum.md` (359 lines, §A–§J). Read-only review;
this file is the only output. Per instructions, `[ASSUMPTION]` tags, `[NOTE FOR PM]` callouts,
§16 Open Questions, and §17 Assumptions Index are treated as deliberate and load-bearing, not
flagged for existing.

## Verdict

**Conditional pass.** The document is structurally sound: capability-oriented framing is held
consistently, the FR/Consequences pattern is disciplined, and the two-way traceability apparatus
(§14 Constitution Provenance Map, §15 Research Deltas, §16 Open Questions, §17 Assumptions Index)
is genuinely load-bearing rather than decorative. No rewrite is warranted. But the consistency
audit surfaces three concrete, verifiable defects (an incorrect FR-range claim, a mislabeled
table heading, and an Assumptions-Index entry with no matching body tag), and Glossary discipline
— which the document explicitly claims to hold ("downstream artifacts must use these terms
exactly") — has a real, concentrated failure zone in §3.3 Key User Journeys. All findings below
are fixable with targeted edits; none requires restructuring.

---

## 1. Consistency Audit (verified programmatically against the files)

### 1.1 FR ID sequence — CONFIRMED DISCREPANCY

§5's preamble states: *"Nine features, FR-1 through FR-58."* The feature count (nine, §5.1–§5.9)
is correct. **The range is wrong.** `#### FR-` headers were counted directly from `prd.md`: there
are exactly 60, sequential, no gaps, no duplicates (FR-1…FR-60). FR-59 and FR-60 are defined in
§5.9 (Developer Experience Surface):

- `#### FR-59: One-command local stack lifecycle`
- `#### FR-60: Stable public task API`

§11.1 MVP Scope independently — and correctly — cites `(FR-59–FR-60)` for the same feature,
confirming the range is FR-1–FR-60 and that §5's preamble sentence is the stale artifact (most
likely left over from a draft where §5.9 didn't yet exist, or existed without new FRs). One-line
fix: `Nine features, FR-1 through FR-58.` → `Nine features, FR-1 through FR-60.`

### 1.2 Cross-reference resolution

Checked programmatically (`grep -oE` over every `FR-N`, `UJ-N`, `SM-N`/`SM-CN`, `NFR-N`, `OQ-N`,
`CR-N`, `R-N`, `D-N` token in both files against each section's defining list):

| ID family | Defined range | Result |
|---|---|---|
| FR-N | FR-1–FR-60 | All references resolve. No dangling FR references found. |
| UJ-N | UJ-1–UJ-4 | All references resolve; no UJ-5+ referenced anywhere. |
| SM-N / SM-C*N* | SM-1–SM-9, SM-C1–SM-C4 | All references resolve. |
| NFR-N | NFR-1–NFR-10 | All references resolve. NFR-6–NFR-10 are defined in §6 but never cross-referenced elsewhere in the document (no "Verified by FR-N" clause, unlike NFR-1/2/3/5) — not a broken reference, but an inconsistent pattern within §6 itself (see §2.3 below). |
| OQ-N | OQ-1–OQ-23 (+ OQ-9b) | All references resolve into §16. One index entry (OQ-22) is never referenced from anywhere else in either file — see 1.4. |
| CR-N | CR-1–CR-5 | All references resolve (CR-1, CR-2 are referenced from §16's OQ-3/OQ-8 rows; CR-3/4/5 are not referenced elsewhere, which is fine — they're terminal). |
| R-N | R-1–R-10 | All references resolve; R-4 is also correctly referenced from `addendum.md` §F. |
| D-N | D1–D17 | All references resolve into §15's table. |

No dangling or out-of-range references were found in any ID family.

### 1.3 `[ASSUMPTION]` tag ↔ §17 Assumptions Index — CONFIRMED DISCREPANCY

Counted every literal `` `[ASSUMPTION]` `` occurrence in the document body (excluding the
frontmatter `mode:` line and §17's own header sentence): **14 inline tags**, at lines 43, 91, 394,
499, 753, 887, 940, 996, 1052, 1057, 1123, 1145, 1158, 1222.

§17 lists 14 index rows, A-1 through A-14. Matching each inline tag to an index row:

- A-1…A-13 each match at least one inline tag (A-5 legitimately covers **two** tags — §5.7/FR-54
  at line 887 and §11.2 at line 1123 restate the same assumption, and the index row correctly
  cites both locations: `§ 5.7 / FR-54, § 11.2`).
- **A-14** (`§ 3.2 | The listed non-user groups are correct audience boundaries | User review`)
  has **no corresponding inline `[ASSUMPTION]` tag anywhere in the document.** §3.2 (Non-Users)
  is plain prose with no tag. This directly contradicts §0's own claim — *"Every inferred value
  is tagged inline and indexed in § 17"* — and §17's header — *"Every `[ASSUMPTION]` in this
  document."* Either add the inline tag to §3.2, or remove A-14 from the index (or re-scope it —
  the assumption itself, that the four non-user groups are correctly drawn, is reasonable content
  for a tag; it's just missing from the body).

### 1.4 OQ referenced in body ↔ §16 — ONE ORPHAN FOUND

Checked whether every `OQ-N` defined in §16 is referenced somewhere outside its own table row (in
`prd.md` proper or in `addendum.md`), and vice versa.

- Every OQ *referenced* in the body resolves to a row in §16 (no dangling OQ references — see 1.2).
- Reverse direction: **OQ-22** (`Is the comparable set complete? Discovery search was unavailable
  during research`) is defined in §16 and appears **nowhere else** in `prd.md` or `addendum.md` —
  not from §10 Non-Goals (its own "Blocks" column target), not from the research-report ID it
  claims to consolidate (`OQ-M1`) anywhere else, not from `addendum.md`. Every other OQ (including
  OQ-21 and OQ-23, which are similarly thin — one occurrence each in `prd.md` — but are picked up
  by `addendum.md` §C and §J respectively) has at least one external anchor. OQ-22 does not. This
  isn't a broken reference, but it is the one truly free-floating open question in the index —
  worth either wiring a pointer from §10, or accepting it as intentionally index-only.

---

## 2. Structural Lens

### 2.1 §5 / §14 / §15 overlap — mostly earns its place, with two soft spots

The three-way overlap the brief flagged is real but, for the most part, deliberately
non-duplicative: §5's per-FR "Provenance:" bullets are the *forward* index (FR → Constitution
locus / research finding), §14 is the *reverse* index (Constitution → FR), and §15 is graded
*evidence* (intake claim → verified reality). That's a coherent three-axis design and each axis
answers a question the others don't. Two places don't hold the line cleanly:

- **§14.1's heading is mislabeled.** It's titled "Article II mandate table" but its eleven rows
  (Local First, Package Management, Production, MCP, A2A, REST, Environments, Orchestration, Data
  Mesh, Data Science, Web Application, RESTful API) span what §14.2 — two subsections later, in
  the same document — separately attributes to Articles I, II, VI, VII, VIII, IX. Only one row
  ("Package Management — pixi, conda-forge, air-gap") is actually about Article II. This reads as
  the Constitution's top-level *stack/priority* mandate table (likely Article I "Identity, stack,
  repository structure" per §14.2's own row), not an Article II table. As written, a reader
  skimming section headings would conclude Article II mandates MCP, A2A, REST, Dagster, and Kedro
  — it does not, per the document's own §14.2. Rename the heading (e.g. "Core stack mandate
  table" or "Article I priority mandates") to match its content.

- **FR-26's Provenance/delta bullet and §15's D14 carry the same finding without cross-citing.**
  Both describe the Constitution's self-declared "immutable"/"non-negotiable" posture conflicting
  with Data Mesh principle 4 (federated computational governance). FR-26 cites `research § 3.1`
  and `OQ-5`; D14 cites `FR-26, FR-27, OQ-5`. Neither cites the other by ID, unlike the pattern
  used elsewhere (FR-2 → "research D4", FR-11 → "§15, D1"). A reader hitting FR-26 first has no
  signal that D14 exists and adds detail (the "2 of 4 principles" scorecard); a reader hitting D14
  first has to infer FR-26 is the same finding from the FR list alone. Minor, but it's the kind of
  gap that compounds as the document is edited by different hands later.

### 2.2 `addendum.md` §I is mislabeled and substantially duplicates PRD §14.2

§I's heading is *"FR → Constitution reverse index... (Forward direction: PRD § 14.)"* But §I's
own table is keyed by **Constitution locus** (`Art. II § 2.1–2.4` → `FR-1, FR-10, FR-14, § 8`) —
i.e., Constitution → FR, the *same* direction as PRD §14 (also Constitution/Mandate → FR, not
FR → Constitution). There is no genuinely FR-keyed index anywhere in either document — the closest
thing is the "Provenance:" bullet scattered across each individual FR in §5. Two consequences:

1. The heading's directionality claim is backwards relative to its own content, and the
   parenthetical pointer to "PRD § 14" as the *forward* direction is wrong — §14 is the same
   direction as §I, not the opposite one.
2. Once relabeled correctly, §I (Constitution locus → FRs, fine-grained by article *subsection*)
   and PRD §14.2 (Constitution → FRs, coarse-grained by whole *article*) are two versions of the
   same index at different granularity, split across two files, with no note that they're related
   or which one to prefer. Either fold §I's finer granularity into PRD §14 (it's the same kind of
   fact, arguably belongs where §0 says the provenance work lives), or add a one-line
   cross-reference each way.

### 2.3 §5.9 breaks the established Feature-section pattern

Every other feature (§5.1–§5.8) follows: Description → Functional Requirements. §5.9 inserts an
unprecedented "**Feature-specific NFRs**" subsection with no analog elsewhere in §5, and then
states its "requirements" are mostly pointers to FRs already counted under *other* features
("*This feature's requirements are satisfied by FR-18 (Quality Gate), FR-24 (local CI), FR-37
(scaffolding), and the local-lifecycle capability below.*") — meaning three of the five FRs
attributed to this feature are not new content, only FR-59 and FR-60 are. This is defensible as
"Developer Experience Surface" being a genuinely cross-cutting user-facing concept rather than a
standalone capability, but as written it reads as a thinner section stapled onto the back of §5
to hold two leftover FRs, breaking the section's own template. Consider either dropping the
"Feature-specific NFRs" subsection into §6 (Cross-Cutting NFRs, which is where every other NFR
lives) or explicitly noting in the Description why this feature is structured differently.

### 2.4 A few "Consequences (testable)" bullets restate the FR rather than adding a test

Most FRs earn the "(testable)" label — they convert a capability statement into an independently
checkable condition (pass/fail criterion, artifact, or measurement). A handful don't add anything
beyond rephrasing the FR:

- **FR-4** ("A dependency version is declared once... referenced elsewhere") → first consequence,
  "No dependency version string appears twice across the root's Features and targets," is the
  same claim in the negative. The second bullet ("a lint check fails the gate on duplication")
  *is* the actual test; the first is redundant scaffolding.
- **FR-24** ("A developer can execute the CI workflows locally") → its single consequence, "A
  documented command runs the CI workflow set locally," restates the requirement with no added
  pass/fail criterion (contrast with FR-18, which sits right next to it and states a measurable
  parity test).
- **FR-49** ("Every Data Product declares its Layer...") → single consequence is the requirement
  restated as a negative-case gate ("An Asset with no Layer... fails the gate"). Minimally
  testable, but there's no positive-path check (e.g., that the Layer value is queryable/reported),
  unlike FR-50/FR-51 next to it which both have a richer Consequences set.

None of these are wrong, and the bar the document sets for itself elsewhere (FR-11, FR-44, FR-45)
is high enough that these three stand out by contrast. Low-severity — worth a pass before
architecture sign-off since Consequences are explicitly the acceptance-criteria layer.

### 2.5 Mechanism occasionally leaks into the PRD despite its own stated split

§0 states mechanism belongs in `addendum.md` "except where a specific technology is itself a
requirement inherited from the Constitution, in which case the provenance is cited (see § 14)."
Two spots name a tool without that citation:

- Glossary, "Feature" definition: *"(Pixi terminology, adopted deliberately.)"* — names pixi
  directly in §4, with no §14 pointer.
- §9 Integration table: `**Workspace manager** (pixi)` — same.

Both are arguably fine as *dependency* declarations (§9 is explicitly an Integration/Dependencies
table, not a requirement), but neither follows the citation convention the document sets for
itself. Low-severity; either add the `(see § 14)` pointer or note in §0 that the Glossary/§9 are
exempt (they're naming a dependency, not encoding a requirement in the tool's terms).

Related: the air-gap override variable table (`CONDA_CHANNEL_ALIAS`, `PIP_INDEX_URL`,
`UV_INDEX_URL`, `GHE_HOST`) appears **twice** — once inline in FR-14's Provenance bullet (PRD) and
again as a dedicated table in `addendum.md` §H.1. Minor duplication across the file boundary the
document otherwise holds well (§0's "this PRD... does not duplicate" claim, and the "Not
duplicated here" note atop the addendum, are true everywhere else checked).

---

## 3. Prose Lens

### 3.1 Glossary-discipline lapses — concentrated almost entirely in §3.3 Key User Journeys

§4's Glossary states plainly: *"Downstream artifacts must use these terms exactly."* This holds
well through §5–§17 (spot-checked Workspace, Package, Feature, Environment, Stage, Mandate,
Layer, Quality Gate, Compliance Report elsewhere — all correctly capitalized when invoking the
defined concept). It **breaks down inside §3.3**, which was evidently drafted as narrative prose
before or independent of the Glossary pass:

- **UJ-3** uses lowercase "**trusted committer**" three times in a row — including bolded —
  where the Glossary defines the capitalized term **Trusted Committer**: *"the **trusted
  committer** for that package is auto-requested as reviewer... the trusted committer reviews and
  merges... the trusted committer disagrees with the approach."* This is the single journey whose
  entire climax depends on this role, and it never once uses the term the way §5.5 (FR-33–FR-36)
  and the Glossary itself do.
- **UJ-4**: *"Sam retrieves the compliance report and SBOM..."* — lowercase; Glossary defines
  **Compliance Report**.
- **UJ-2** title and body: *"Marcus installs a library another domain published"* — lowercase;
  Glossary defines **Domain**. **UJ-3** repeats the same lapse: *"a defect in a shared library
  owned by another domain."*
- **UJ-2** edge case: *"the conflict-detection environment (§ 5.1) has usually caught it"* —
  lowercase; this is the same construct FR-7 defines and capitalizes as the **compatibility
  Environment**.
- **UJ-2** body: *"pixi re-solves the workspace"* — lowercase "workspace" is defensible as pixi's
  own technical vocabulary (see 3.2 below on the term collision), but sits one sentence away from
  three other lapses in the same journey, so it reads as part of the same drafting-pass gap rather
  than a deliberate distinction.

None of these change meaning — a reader infers the intended concept without difficulty — but the
document explicitly claims strict discipline, and this is the one place that fails to hold it,
consistently, across all four journeys. A single find-and-recapitalize pass over §3.3 fixes it.

- One more instance, inside the Glossary itself: the **Package** definition's parenthetical —
  *"(a shared library, an infrastructure service, or a **domain** service)"* — uses lowercase
  "domain" as an example noun, one line before the Glossary defines **Domain** as the next term.
  Minor, but it's inside the section that's supposed to be the strictest.

### 3.2 "Workspace" and "workspace" collide, and the document doesn't flag it

The Glossary's **Workspace** (capitalized) is Unity's repository root. Separately, pixi (and PEP
tooling generally) has its own lowercase technical term "workspace" for multi-package project
support — used throughout `addendum.md` §F/§A.3 and PRD §9/§13 ("multi-package workspace support
is **preview**"). Because Unity's Workspace *is* (in option (a) of addendum §A) built on pixi's
workspace feature, a reader can genuinely conflict-resolve "is this the Unity Workspace, or pixi's
workspace-support feature?" only from capitalization and context — which is fragile once this
document is excerpted or quoted out of context (e.g., in a future architecture doc). Consider a
one-line Glossary note under **Workspace** disambiguating it from the pixi-native "workspace"
feature referenced in OQ-9b — the same pattern already used for **Feature** ("Pixi terminology,
adopted deliberately").

### 3.3 FR-2 names its own subject two different ways

FR-2's title is *"Toolchain version pinned as a range, never an exact equality."* Its requirement
sentence says: *"The Workspace declares its required **workspace-manager** version..."* Its first
Consequence says: *"A developer on any **toolchain** version within the declared range..."*
Neither "toolchain" nor "workspace manager" is a Glossary term (the Glossary defines Workspace,
not "workspace manager"), and the FR uses both, plus its own title's "Toolchain," to refer to what
is — per §9's Integration table and `addendum.md` — specifically pixi. Pick one term (or add it to
the Glossary) and use it consistently within the FR at minimum.

### 3.4 NFR-6 through NFR-10 drop the "Verified by" pattern without explanation

§6 states NFR-1, NFR-2, NFR-3, and NFR-5 each with a closing "Verified by FR-N" clause; NFR-4 has
an `[ASSUMPTION]` + OQ-12 pointer instead. NFR-6 (Auditability), NFR-7 (Diagnosability), NFR-8
(Platform coverage — which *does* parenthetically cite FR-6, but not in the "Verified by" phrasing
used elsewhere), NFR-9 (Extensibility), and NFR-10 (Supply-chain integrity) all end flat, with no
verification pointer at all. This isn't wrong — not every NFR needs one — but the pattern breaks
inconsistently rather than by evident design (NFR-8 half-follows it), which reads as an unfinished
edit rather than a deliberate choice. Either complete the pattern (point NFR-6/7/9/10 at whichever
FRs or gates verify them — e.g. NFR-9 is arguably verified by FR-27's override mechanism) or note
explicitly that some NFRs are process/cultural commitments without a single verifying FR.

### 3.5 Hedging — largely absent; the document is unusually direct

Scanned every FR, NFR, CR, and Constraint statement for hedge words ("should," "might," "likely,"
"generally," "typically," "ideally," "tends to"): **none found** outside the Risk/Provenance
narrative prose, where they're appropriate (e.g. R-4's mitigation is phrased as guidance, not a
requirement). "May" appears exactly three times, and only in genuinely permissive contexts (NFR-2
uses "No capability *may* assume..." as a prohibition, not a hedge; the other two are in §16's OQ
descriptions, not requirements). This is a genuine strength — worth naming as such rather than
only flagging problems.

### 3.6 Requirements-as-descriptions — deliberate and consistent, one exception worth naming

Every FR statement is phrased descriptively ("The Workspace declares...", "A developer can...")
rather than deontically ("The Workspace MUST declare..."), with the actual obligations pushed
entirely into the "Consequences (testable)" bullets. This is applied with total consistency across
all 60 FRs, so it reads as a deliberate style choice rather than a defect — flagging it only
because §3.2.4 (Constraints) breaks the pattern by using direct imperatives ("Restricted data
**never** leaves a Stage classified for it," "Secrets **never** enter version control...").
The shift from descriptive-FR to imperative-Constraint is not itself wrong (Constraints are a
different rhetorical class — guardrails, not features), but a reader moving from §5 to §8 will
notice the register change without an explanation for why. Not a fix-required item, just worth
the PM's awareness given the FR/Consequence split is otherwise this document's load-bearing
convention.

---

## 4. Findings Summary

| # | Severity | Location | Finding |
|---|---|---|---|
| F1 | High | §5 preamble | "Nine features, FR-1 through FR-58" — should read FR-60 (FR-59/FR-60 defined in §5.9; §11.1 already cites the correct range) |
| F2 | High | §14.1 heading | "Article II mandate table" mislabeled — content spans multiple Articles per §14.2's own mapping; only one row is Article II |
| F3 | High | §17 / §3.2 | Assumptions Index entry A-14 has no matching inline `[ASSUMPTION]` tag anywhere in the body — contradicts the document's own tagging claim |
| F4 | Medium | §3.3 (UJ-2, UJ-3, UJ-4) | Glossary-term capitalization lapses concentrated in the Key User Journeys: "trusted committer" ×3, "compliance report" ×1, "domain" ×2, "conflict-detection environment" ×1 |
| F5 | Medium | `addendum.md` §I | Title "FR → Constitution reverse index" is backwards — table is actually Constitution-locus-keyed, same direction as PRD §14; also substantially overlaps §14.2 with no cross-reference |
| F6 | Medium | FR-2 | "workspace-manager version" (requirement) vs "toolchain version" (consequence) vs "Toolchain version" (title) — three names for one concept, none Glossary-defined |
| F7 | Medium | §16 | OQ-22 defined but never referenced anywhere else in either file — the one orphaned Open Question |
| F8 | Medium | §4 Glossary | "Package" definition's own example text uses lowercase "domain service" one line before "Domain" is defined |
| F9 | Low | FR-4, FR-24, FR-49 | Consequences bullets restate the FR rather than adding an independently testable criterion |
| F10 | Low | FR-26 / §15 D14 | Same finding (Constitution "immutable" vs Data Mesh principle 4) stated in both places without cross-citing by ID, unlike the pattern used elsewhere |
| F11 | Low | §5.9 | Breaks the §5 feature-section template (adds "Feature-specific NFRs"; 3 of 5 attributed FRs are pointers to other features) |
| F12 | Low | §4 Glossary, §9 | Tool name ("pixi") named directly without the §14-citation convention §0 sets for itself |
| F13 | Low | FR-14 / addendum §H.1 | Air-gap override variable table duplicated (inline in PRD, and as a standalone table in addendum) |
| F14 | Low | §6 | NFR-6/7/9/10 (and half of NFR-8) drop the "Verified by FR-N" pattern used by NFR-1/2/3/5 with no stated reason |
| F15 | Low | §4 Glossary vs §9/§13 | "Workspace" (Unity's root) and pixi's own lowercase "workspace" (multi-package feature) collide without a disambiguating note |

Counts: **3 High, 5 Medium, 7 Low** (15 total findings).

---

## 5. What's working well (not exhaustive, noted for balance)

- FR numbering, Consequences structure, and Provenance/delta sourcing are disciplined and
  verifiable — 60/60 FRs sequential with no gaps or duplicates, and the programmatic
  cross-reference check found no dangling FR/UJ/SM/R/D references anywhere.
- §14/§15/§16/§17's four-way traceability apparatus genuinely does the job the document claims
  for it — this is unusually rigorous for a headless PRD.
- Hedging discipline is excellent — the document commits to specific, falsifiable claims almost
  everywhere, including in `[ASSUMPTION]`-tagged material, which is not automatically softened
  just because it's marked as an inference.
- The Constitution-delta grading (CONFIRMED/STALE/WRONG/NEW/GAP in §15) is a genuinely useful
  invention not found in a typical PRD, and it's applied consistently.
