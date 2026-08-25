# Steward — Canopy chain implementation readiness (2026-08-24)

Gate of `spec-pyforge-unifying-strategy` (CAP-1..18, Epics 18–30 plus Epic 32)
after Phase 5 eight-station `bmad-correct-course` and the later-day CAP-18 bind.
Method: `bmad-sprint-planning` readiness gate — could a developer implement
these epics without inventing decisions nothing records?

**Verdict: CONCERNS — proceed.** Packaging gates and `lane1-serves-dw-h3` remain
the only concerns. CAP-18 is now decomposed (FR-43..45, steward Epic 32, Warden
Epic 9, per-station process stories).

## Re-stamp — operating model (2026-08-24, later the same day)

Same implementability question after Dream Grounding Q1–Q8, steward
`sprint-change-proposal-2026-08-24-operating-model.md` (approved), and **eight**
station operating-model correct-courses (§6 revisited: not Warden-only).

| Bound | Where a developer reads it |
|---|---|
| Q1 estate practice; Golden Path; WFT tools as adapters | Dream Grounding; steward SCP |
| Q2 five-tier = 03 only | SPEC Never; PRD glossary + FR-37/38/39 + SM-5; Epic 29 / S-29.3 |
| Q3 owner/`work_class` on discovery; SLA body in spec | SPEC CAP-1 note; PRD FR-1/2; S-18.1 / S-19.2 |
| Q4 `spec_id` + git sha + SBOM purl; Jira optional | SPEC CAP-8; PRD FR-17; S-24.1 |
| Q5 measurement in the OM; scorecard **unpublished** | Dream Grounding; do not invent metrics |
| Q6 Path B = Agent Canopy + persona; Tachyon = LLM adapter | SPEC CAP-16; PRD glossary |
| Q7 HTMX portal; FastAPI compute; DRF on Atlas data-models only | SPEC CAP-3; `stack.md` |
| Hooks/plugins as replaceable-layer principle (AD-21); Q8 is the PR-gate instance | Dream Grounding; canopy AD-21; SPEC Always; all eight `epics.md` OM blocks |

Station planning (all eight): `change-history/sprint-change-proposal-2026-08-24-operating-model.md`,
`epics.md` § Operating-model obligations, **`DW-OM-2026-08-24`**. Warden owns PR-gate
hook *specs*; plugins implement them. Every station records the Never: competing
verdict. Atlas already *is* Kedro (pipeline hooks ≠ PR-gate book). Not a Kedro
re-template of any station.

No MUST-FIX from this pass. Scorecard numbers are explicitly deferred (human + agent +
team). Do not implement S-29.3 against pre-OM “any missing tier fails” wording — the
story ACs are already 03-scoped.

## Re-stamp — CAP-18 hook specs (2026-08-24, later still)

Operator: one shared plugin API, then Warden PR-gate retrofit, then station
process hooks. **Not in Epics 18–30.** Bound as CAP-18 / FR-43–45.

| Bound | Where a developer reads it |
|---|---|
| Shared hook-spec + registration in `pyforge-core` | SPEC CAP-18; PRD FR-43; steward **S-32.1** |
| Warden PR-gate; scanners optional; green without Checkmarx | FR-44; Warden **Epic 9** |
| Per-station process layer; today's backend = default plugin | FR-45; steward S-32.2; atlas 18.1; mason 10.1; marshal 26.1; doctor 17.1; herald 16.1; scribe 4.1 |
| `DW-OM-2026-08-24` | Implementation `close_when`, not markdown-only |

First chrome dispatch: **S-18.1**. First CAP-18 dispatch: **S-32.1** (may parallel
18.1). Then Warden 9.x, then other station process stories. Do not regenerate the
whole steward sprint feed.

## Artifact inventory

| Artifact | Path | Status |
|---|---|---|
| Dream | `docs/dreams/pyforge-unifying-strategy.md` | specified (this pass) |
| Spec | `specs/spec-pyforge-unifying-strategy/SPEC.md` + 5 companions + 4 research files + architecture spine | ready (this pass) |
| Brief | `briefs/brief-pyforge-unifying-strategy-2026-08-24/brief.md` | ready |
| PRD | `prds/prd-pyforge-unifying-strategy-2026-08-24/prd.md` | ready (this pass) |
| Architecture | `architecture/architecture-pyforge-unifying-strategy-2026-08-24/ARCHITECTURE-SPINE.md` | final (prior pass) |
| Epics | `epics.md` Epics 18–32 (Epic 31 suite-install + Epic 32 CAP-18) | 18–30 unchanged in scope |
| Phase 5 | eight `sprint-change-proposal-2026-08-24-canopy.md` + Canopy obligations + `DW-CANOPY-2026-08-24` | approved |
| Operating model | steward SCP + PRD/epic/spine edits; eight station OM SCPs + `DW-OM-2026-08-24` | approved (same day; §6 revisited to all eight) |
| CAP-18 hook specs | steward `sprint-change-proposal-2026-08-24-hook-specs.md` + eight station hook-spec SCPs | approved; retracts Warden “record only” |

No UX artifact. Portal chrome is specified by canopy AD-1 / FR-1; no UX-only
stories exist. Not a finding.

## Traceability

PRD §12 covers CAP-1..18 → FR-1..FR-45 plus FR-9a/9b/21a. FR-44 is Warden Epic 9.
FR-45 is steward S-32.2 plus peer station process stories. Every FR has an epic.

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
| steward | 30 | Epic 11 stays done; Epic 27 supersedes DDL producer only. OM: deploy-profile plugins. Last local epic still 30 (31 is suite-install, not Canopy). |
| warden | 8 | Rename is S-19.1; `/compliance/` redirect. OM: owns PR-gate hook specs. |
| marshal | 25 | `spec-factory-console` superseded → CAP-2; generator until S-30.2. OM: loop pass ≠ PR gate. |
| atlas | 17 | `lane1-serves-dw-h3` **not answered**; Vizro CLI off-host. OM: already-Kedro pipeline hooks (reference shape, not PR-gate); DRF only on data-models. |
| mason | 9 | No MinIO; `conda-forge-expert` stays hand-authored. OM: build-engine plugins ≠ Warden. |
| scribe | 3 | No Epic 4; graph → steward Epic 28; `FlatFileGraphStore` only. OM: store/recall plugins. |
| doctor | 16 | No Epic 17+. OM: remedy hooks are advisory / Warden inputs. |
| herald | 15 | No Epic 16+. OM: export-format plugins. |

## Next

Story 18.1 (`django-pyforge` chrome) is the first dispatchable story. S-18.1 now
also carries owner / `work_class` / promotion date on the registration seam.
S-26.3 and S-27.1 wait on the operator. Scorecard draft is not a Canopy story.
