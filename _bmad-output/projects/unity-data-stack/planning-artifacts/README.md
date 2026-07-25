# unity-data-stack — planning artifacts

BMAD Tier-2 output for this project (research/, briefs, PRD, architecture, epics, specs/).

**Source Dream:** `docs/dreams/unity-data-stack.md` (Tier 0)
**Intake gists absorbed:** `docs/intake/gists/{spec-kit,unity-data-stack-pixi-toml,bmad-method-spec-enterprise-monorepo-cross-platform-deployme}/`

## Chain status

Planning ran **2026-07-25**, headless/express, to **PRD + architecture depth only**. Epics and
stories were deliberately **not** produced — this is a far-horizon platform whose stories should
decompose fresh when it is scheduled.

| Stage | Artifact | Status |
|---|---|---|
| 1. Research | `research/market-enterprise-innersource-python-platform-research-2026-07-25.md` | complete |
| 1. Research | `research/domain-enterprise-python-platform-engineering-research-2026-07-25.md` | complete |
| 2. Brief | `briefs/brief-unity-data-stack-2026-07-25/{brief.md, addendum.md}` | draft |
| 3. PRD | `prds/prd-unity-data-stack-2026-07-25/{prd.md, addendum.md}` | draft — 60 FRs / 9 features |
| 4. Architecture | `architecture/architecture-unity-data-stack-2026-07-25/ARCHITECTURE-SPINE.md` | draft — 20 ADs, initiative altitude |
| 5. Epics/stories | — | **intentionally not run** |

Each run folder carries a `.memlog.md` (decisions, changes, overrides — the resume authority) and
its reviewer outputs (`review-*.md`).

## Reading order

1. **`briefs/…/brief.md`** — positioning, problem, scope boundary. Start here.
2. **`prds/…/prd.md`** — the requirement set. § 14 traces every Constitution mandate to an FR;
   § 15 lists the 17 verified corrections to the intake artifacts.
3. **`architecture/…/ARCHITECTURE-SPINE.md`** — the invariants (AD-1…AD-20) that keep
   independently-built features from diverging.
4. The two research reports — the evidence base; every quantitative claim upstream cites one.
5. The `addendum.md` files — intake inventory (brief) and options-considered matrices (PRD).

## Before resuming this project, read these first

- **OQ-1 (PRD § 16) blocks everything.** The lock architecture — whether the workspace lock or
  the PEP 751 export is authoritative — was answered by the spine (AD-2: workspace-lock-primary),
  but the PRD still carries it as an assumption requiring human confirmation. Confirm or overturn
  before any build work.
- **OQ-2 changes sizing by an order of magnitude** — whether v1 delivers one worked Domain or all
  eleven.
- **The intake artifacts have known errors.** Do not read the gists as ground truth. PRD § 15
  lists what research falsified, including a flagship command that uses a flag which does not
  exist and a hard version pin that blocks installation outright.
- **The regulatory clock is live.** EU CRA vulnerability-reporting obligations begin 2026-09-11;
  main obligations 2027-12-11. The compliance requirements are dated, not aspirational.
- **Two research limitations are declared, not hidden.** Web-search discovery was unavailable
  (comparable-set completeness is not claimed, OQ-22) and the `cf_atlas` database was absent
  (conda-forge coverage of the mandated stack is spot-checked only, OQ-15).
