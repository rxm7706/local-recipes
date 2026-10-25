# Design thinking — BMAD marketplace reset (2026-10-20)

Verbatim session record for the 2026-10-21 revisit of
`docs/dreams/self-hosted-bmad-marketplace.md`. That seed stays archived.
The living aspiration is the 2026-10-21 entry on `docs/dreams/pyforge-steward.md`
(CAP-169..CAP-173, FR-42..FR-46, Epic 109). These files are not a second Dream.

The product brief is
`planning-artifacts/briefs/brief-bmad-marketplace-reset-2026-10-21/brief.md`.

## Session files

| File | What it is |
|---|---|
| [bmad-marketplace-dream-reset.md](bmad-marketplace-dream-reset.md) | Reset brief: v1 evidence, Q1–Q7 review, reuse inventory, build-ready exit criteria |
| [design-thinking-2026-10-20.md](design-thinking-2026-10-20.md) | Full session record. Concepts A–F were all selected. Success signal: a teammate other than rxm7706 contributes a skill, and a different teammate installs and uses it |
| [station-inventory.md](station-inventory.md) | Eight stations. First listings: warden scan, mason environment, mason package |
| [tool-support-matrix.md](tool-support-matrix.md) | Six tools read `SKILL.md`. Install into `.agents/skills/` and `.claude/skills/` |

## Prototypes

Sample data. The paper skill card's lock command is not the runbook. Checksums, review records, and example hosts in P2 are not listings.

| File | Used by |
|---|---|
| [prototypes/p1-cli-transcript.md](prototypes/p1-cli-transcript.md) | Stories 109.3 and 109.4 (`bmp`, `index.yaml`). `@bmp/skillify` is `bmp new skill --from-session` |
| [prototypes/p2-index-schema.yaml](prototypes/p2-index-schema.yaml) | Stories 109.3 and 109.4. Superset of `registry/estate.yaml`. `listing.yaml` per folder |
| [prototypes/p2-index-schema.md](prototypes/p2-index-schema.md) | Tier map: `community` → `unverified`, `estate-reviewed` → `community-reviewed`, `bmad-certified` → `bmad-certified` |
| [prototypes/p3-skill-card.html](prototypes/p3-skill-card.html) | Story 109.3 Pages skill cards. Sections to render; commands on the mock are sample |
| [prototypes/p3-skill-card.png](prototypes/p3-skill-card.png) | The same card, as reviewed in the session |
| [prototypes/p4-wizard-of-oz-pilot.md](prototypes/p4-wizard-of-oz-pilot.md) | Story 109.5. Exit criteria before automating `bmp`, lint, or publish |
| [analysis-against-main-2026-10-25.md](analysis-against-main-2026-10-25.md) | Re-check after merging `origin/main` `81f66ee411`. Round 0 and Round 1 runbooks. No renumber |

## What the committed tree took from this record

- Pilots stay `tier: community` / `trust_tier: unverified`. No review record is invented, so they are not `estate-reviewed`.
- All three pilots are `lane: code-backed` because each requires a package. Instructions-only is a skill with no package.
- `steps.md` is the runbook the card renders. P3's `--conda` / `env.lock` line is not copied.
- Install sources are a GitHub release and Artifactory conda and pip. None of the three is published, so the card has no URL and no checksum.
- `bmp` and `@bmp/skillify` are named on Stories 109.4 and 109.5. They are not built. P4's numeric gates still apply.
