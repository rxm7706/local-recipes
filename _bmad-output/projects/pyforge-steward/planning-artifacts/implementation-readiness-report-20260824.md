# Steward — Canopy chain implementation readiness (2026-08-24)

Gate of `spec-pyforge-unifying-strategy` (CAP-1..17, Epics 18–30) after Phase 5
eight-station `bmad-correct-course`. Method: `bmad-sprint-planning` readiness
gate — could a developer implement these epics without inventing decisions
nothing records?

**Verdict: CONCERNS — proceed.** The plan is implementable as recorded. Two
concerns are already bound as gates, not gaps. One open question is jointly
deferred and does not block Epics 18–30.

## Artifact inventory

| Artifact | Path | Status |
|---|---|---|
| Dream | `docs/dreams/pyforge-unifying-strategy.md` | specified (this pass) |
| Spec | `specs/spec-pyforge-unifying-strategy/SPEC.md` + 5 companions + 4 research files + architecture spine | ready (this pass) |
| Brief | `briefs/brief-pyforge-unifying-strategy-2026-08-24/brief.md` | ready |
| PRD | `prds/prd-pyforge-unifying-strategy-2026-08-24/prd.md` | ready (this pass) |
| Architecture | `architecture/architecture-pyforge-unifying-strategy-2026-08-24/ARCHITECTURE-SPINE.md` | final (prior pass) |
| Epics | `epics.md` Epics 18–30 (13 epics, 35 stories) | appended; Epics 1–17 untouched |
| Phase 5 | eight `sprint-change-proposal-2026-08-24-canopy.md` + Canopy obligations + `DW-CANOPY-2026-08-24` | approved |

No UX artifact. Portal chrome is specified by canopy AD-1 / FR-1; no UX-only
stories exist. Not a finding.

## Traceability

PRD §12 covers CAP-1..17 → FR-1..FR-42 plus FR-9a/9b/21a. `epics.md` FR map
covers the same set. Every FR has an epic; every Canopy epic names its FRs.

FR-6 (inventory) is already delivered as `console-parity-inventory.md`; Epic 30
is the cutover, not a second inventory. Packaging FRs (FR-21, FR-33) bind to
Stories 27.1 and 26.3 as **blocked-on-operator**, Effort: —.

## Concerns (do not block dispatch of the rest)

1. **Packaging gates (S-26.3, S-27.1).** Four OpenFeature feedstocks + `cachebox`
   5.x + Liquibase ≥5.0.4 are operator-owned. Downstream stories (26.4, 27.2–27.4)
   stay blocked until those recipes exist. Recorded; do not start recipes in this
   planning PR.
2. **`lane1-serves-dw-h3` remains open.** Joint steward↔atlas. Atlas Epic 16 /
   `LaSuiteClient` REST is not Wagtail's API; Canopy must not absorb
   `spec-wagtail-corporate-brain`. Epic 20 (Wagtail Lane 1) can proceed; the
   question is whether that instance also serves DW-H3, not whether Lane 1 exists.
3. **Sprint-key truncation.** `sprint_plan.py generate` slugs titles at 60
   characters and would orphan 13 already-`done` steward keys. Canopy keys were
   appended by hand; do not regenerate the whole steward feed until the slugger
   preserves existing keys.

## Review (SPEC / PRD / architecture / epics)

Architecture spine already passed lint + currency PASS-WITH-FLAGS + adversarial
close + rubric PASS-WITH-FLAGS (Phase 4d). This pass checks the planning package
for implementability, not a second architecture hunt.

| Lens | Result |
|---|---|
| Verification-gap | No orphan FR. CAP-2 removal (FR-7) waits on S-30.1 parity. Kedro-Viz explicitly out of retirement. |
| Edge-case | RFC-3 HMAC → RS256 is in S-18.3. Redis cache≠broker is S-20.2. MinIO forbidden in mason obligations and S-25.4. |
| Adversarial (delta only) | Dream README still described a `services/` FastAPI tier as residual — corrected this pass. Grounding prose in the Dream remains historical; SPEC + spine win where they disagree. |
| Structure / prose | Companion list on SPEC includes the spine. Bare `AD-n` remains review-blocking (canopy vs parent). |

No MUST-FIX that would keep the Spec at `draft`. Open question stays listed.

## Phase 5 station check (8/8)

| Station | Last local epic | Load-bearing |
|---|---|---|
| steward | 30 | Epic 11 stays done; Epic 27 supersedes DDL producer only |
| warden | 8 | Rename is S-19.1; `/compliance/` redirect |
| marshal | 25 | `spec-factory-console` superseded → CAP-2; generator until S-30.2 |
| atlas | 17 | `lane1-serves-dw-h3` **not answered**; Vizro CLI off-host |
| mason | 9 | No MinIO; `conda-forge-expert` stays hand-authored |
| scribe | 3 | No Epic 4; graph → steward Epic 28; `FlatFileGraphStore` only |
| doctor | 16 | No Epic 17+ |
| herald | 15 | No Epic 16+ |

## Next

Story 18.1 (`django-pyforge` chrome) is the first dispatchable story. S-26.3 and
S-27.1 wait on the operator.
