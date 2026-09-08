# Validation Report — the Canopy mounts the eight stations

- **PRD:** `_bmad-output/projects/pyforge-steward/planning-artifacts/prds/prd-pyforge-unifying-strategy-2026-08-24/prd.md`
- **Rubric:** `.claude/skills/bmad-prd/assets/prd-validation-checklist.md`
- **Run at:** 2026-08-24T20:45:00-05:00
- **Grade:** Fair

## Overall verdict

The FRs, glossary, and SM-5 already carry the operating-model bind. That is enough to implement from. What is at risk is the tail: §2 still says sixteen capabilities, §10 still treats OQ-4 and recipe authorship as live, and §14 still reads as if architecture and epics have not run. The brief Update agrees with the FRs; it disagrees with those tail sections.

## Dimension verdicts
- Decision-readiness — adequate
- Substance over theater — strong
- Strategic coherence — strong
- Done-ness clarity — strong
- Scope honesty — adequate
- Downstream usability — thin
- Shape fit — strong

## Findings by severity

### Critical (0)

None.

### High (3)

**Decision-readiness** — Tail sections re-open answered decisions (§10, §14)

Integration still says the compliance portal “may need to move if OQ-4 chooses a uniform prefix”; §14 says architecture must fix the URL scheme. §11 already answers OQ-4.

Fix: PRD Update — rewrite those bullets; point at FR-9a and Epic 18.

**Scope honesty** — Packaging authorship disagrees with the brief and canopy:AD-16 (§10)

“Each is a `conda-forge-expert` session under repo Rule 1.” Brief: S-26.3 / S-27.1 do not author recipes.

Fix: operator-owned gates; Rule 1 only if recipes are authored outside this chain.

**Downstream usability** — Capability count drift (§2)

“five of the sixteen capabilities” after CAP-17. Brief and §12 use seventeen.

Fix: sixteen → seventeen.

### Medium (2)

**Downstream usability** — §14 claims architecture and epic passes are still ahead

Spine is final; Epics 18–30 written.

Fix: next = S-18.1; packaging tails wait; `lane1-serves-dw-h3` remains.

*(Footnote 2026-08-25: `lane1-serves-dw-h3` answered **no**. This 2026-08-24 finding is historical. Do not reopen.)*

**Brief reconcile** — Agent-as-user hedge left in Assumptions Index

Brief says the PRD confirmed the emphasis; the index still calls it unverified.

Fix: drop the hedge on PRD Update.

### Low (1)

**Done-ness** — UJs do not mention `work_class` or Golden Path (§2.3)

Optional. OM lives in glossary + FR-2.

Fix: one clause on UJ-1 that 01/02 is not a switcher tile — or ignore.

## Mechanical notes
- Glossary OM terms are used in FRs; drift is in §2 count and §10/§14 tense, not term spelling.
- §11 answered-OQ numbering (-2, -1, 0, 5…) is historical.
- PRD addendum OM section agrees with the brief addendum.

## Reviewer files
- `review-rubric.md`
- `review-brief-reconcile.md`
