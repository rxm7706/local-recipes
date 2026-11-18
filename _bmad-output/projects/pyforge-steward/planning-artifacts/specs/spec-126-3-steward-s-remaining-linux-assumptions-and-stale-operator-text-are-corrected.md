---
title: '126.3: Steward''s remaining Linux assumptions and stale operator text are corrected'
type: 'fix'
created: '2026-11-18'
status: 'ready-for-dev'
story: 126-3-steward-s-remaining-linux-assumptions-and-stale-operator-text-are-corrected
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - 'src/shared/packages/pyforge-steward/**'
  - 'scripts/platform-ci-local.sh'
  - 'pixi.toml'
  - 'docs/reference/sync-jira-github-workflow-templates/**'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/adoption-register.md'
  - 'docs/how-to/run-and-read-pr-preflight.md'
  - 'docs/how-to/move-vendor-extracts-through-the-corridor.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `shell-init` completes 13 of 31 duties; `restore` names a runbook path that moved; `stage_container` and `export_context` use `ss` and GNU `tar`; the leak guard reads `/proc` only; the `pr-preflight`, `governance-currency` and pixi-floor texts in `pixi.toml` say what is no longer true; `bmad-preflight` runs a script that does not exist; the sync templates install on Python 3.12; the adoption register cites a redirect stub and does not say the studio is a per-machine prerequisite; nobody knows which environment gives the corridor duties a Django project.

**Approach:** Each is corrected at its source and the studio joins the preflight how-to's prerequisites.

Ledger key: `126-3-steward-s-remaining-linux-assumptions-and-stale-operator-text-are-corrected`.

### Living CAP citations

- spec-pyforge-steward CAP-175 and CAP-5 (realized, no text change); FR-49 ← CAP-175; no AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Close the deferred-work row this story names with the commit that resolves it.

**Never:**
- Never weaken an assertion that holds on Linux, hand-edit a compiled skill, a `SPEC.md`, a generated page or `sprint-status-ledger.yaml`.

## Acceptance Criteria

**Given** `shell-init` completes 13 of 31 duties; `restore` names a runbook path that moved; `stage_container` and `export_context` use `ss` and GNU `tar`; the leak guard reads `/proc` only; the `pr-preflight`, `governance-currency` and pixi-floor texts in `pixi.toml` say what is no longer true; `bmad-preflight` runs a script that does not exist; the sync templates install on Python 3.12; the adoption register cites a redirect stub and does not say the studio is a per-machine prerequisite; nobody knows which environment gives the corridor duties a Django project
**When** each is corrected at its source and the studio joins the preflight how-to's prerequisites
**Then** `shell-init` completes every duty the parser has (a test derives the list); the named texts match the code; the two stages have portable fallbacks; the corridor how-to names a working environment or says plainly that none exists
**And** `DW-steward-125-1-1`, the rest of `DW-steward-125-1-2`, and steward's items of `DW-doctor-59-3-1` and `DW-doctor-59-5-1` reads resolved in its ledger with the commit that closed it

- **AC1 — The story's own check passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-test && pixi run --frozen -e pyforge-steward pyforge-steward-live-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-175 and CAP-5 (realized, no text change); FR-49 ← CAP-175; no AD moves.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-11-18 entry; operator ruling of 2026-11-18: "THIS MACHINE WILL BE A FIRST CLASS DEVELOPMENT HOST -- JUST FIX ALL THE DEFERRED ROW ITEMS NOW.. AND NOT LEAVE ANYTHING FOR LATER", "JUST USE ctranslate2 and remove the other one", "we should continue to support manticore and antigravity", "we still want to do everything in this session as one PR".
- Epic: Epic 126, minted with this story.
- Ledger key: `126-3-steward-s-remaining-linux-assumptions-and-stale-operator-text-are-corrected` (`backlog`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."126"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-18: minted from the station Dream's 2026-11-18 entry and the operator's rulings of the same date.
