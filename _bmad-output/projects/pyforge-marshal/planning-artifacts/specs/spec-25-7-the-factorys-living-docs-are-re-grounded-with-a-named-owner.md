---
title: The factory's living docs are re-grounded with a named owner
type: docs
created: '2026-08-24'
status: done
updated: '2026-08-24'
context: []
warnings:
  - oversized
baseline_revision: e57c6dc4bce0e717d13d290decc14fab7b7352a2
review_loop_iteration: 0
followup_review_recommended: true
deferred:
  - summary: >-
      `_bmad-output/PROJECTS.md` still maps the historical multi-project layout;
      architecture now points readers there for the 8-station vs archived map
      but PROJECTS.md itself was not refreshed in 25-7.
    evidence: |-
      Blind Hunter finding; intent surfaces were living docs + SYNC-RUNBOOK +
      parent SPEC open question — not PROJECTS.md.
    location: >-
      _bmad-output/PROJECTS.md
    severity: medium
  - summary: >-
      SYNC-RUNBOOK Step 3 `--write-baseline` was not run after this living-doc
      re-ground; detector baseline may still predate the 6.11 prose refresh.
    evidence: |-
      Reconciler runbook treats baseline stamp as a post-reconcile mutation;
      CAP-7 ACs required owner+cadence + re-grounded pins, not baseline write.
    severity: low
  - summary: >-
      Station status lines publish opaque done/backlog totals that include epic
      keys without a grammar note agents can rely on.
    evidence: |-
      Thin stub re-ground used ledger Counter totals; Design Notes already
      accept thin depth — clarify grammar in a later marshal cadence pass.
    severity: low
  - summary: >-
      Deeper architecture sections (Guildhall / surface-checker narrative) may
      still lag portfolio dissolution beyond the At-a-Glance + Installed Skills
      re-ground.
    evidence: |-
      Implementer residual risk; not required to satisfy CAP-7 success clauses.
    severity: medium
  - summary: >-
      Parent SPEC body has no dated CAP-7 decision prose beyond cleared
      open_questions frontmatter + memlog append.
    evidence: |-
      AC requires frontmatter/memlog close; body prose is optional polish.
    severity: low
---

<intent-contract>

## Intent

**Problem:** After BMAD 6.11 retired `bmad-document-project`, living factory docs (`architecture-bmad-infra.md`, 8× `project-context.md`) drifted with no reconciler; SYNC-RUNBOOK has no named owner/cadence for re-grounding (FR-611 CAP-7; spec-bmad-611-era-alignment open question).

**Approach:** Re-ground `architecture-bmad-infra.md` to describe 6.11 infra (render pipeline, TOML layers, current skill set). Refresh all 8 station `project-context.md` rulebooks via plain agents with bumped `source_pin`s. Update SYNC-RUNBOOK to name recurring owner + cadence. **Open-question decision (2026-08-24):** fold living-doc re-grounding into the SYNC-RUNBOOK cadence as a **marshal** duty (matches parent SPEC "Owner: marshal") — not a per-station relay. Deps: 25.6 done (#721). Completes Epic 25 → marshal DRAINED.

## Boundaries & Constraints

**Always:** Physical paths under `_bmad-output/projects/<slug>/…`; `BMAD_ACTIVE_PROJECT=pyforge-marshal` only — never `scripts/bmad-switch`. Bump every touched living doc's `source_pin` (or `last_synced_skill_version` where that is the existing pin key) to live groundtruth (`BMAD 6.11.0` / `conda-forge-expert v8.84.0`). Close parent SPEC `open_questions` with a dated memlog + frontmatter update. `maintenance` label on the PR.

**Block If:** Any change would edit the AGENTS.md managed / project-context ledger block (upstream HOLD).

**Never:** Adopt stories.yaml / folder+id dispatch / v7-removal paths. Never wait on upstream successor. Never touch AGENTS.md managed block. Finalize marshal ledger only after merge — mark `25-7` + `epic-25: done`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | Live install is BMAD 6.11.0; CFE v8.84.0; 8 station rulebooks present | architecture + 8 contexts re-grounded; SYNC-RUNBOOK names marshal+cadence; parent open question cleared | No error expected |
| HOLD_AGENTS | Temptation to refresh AGENTS.md managed block during re-ground | AGENTS.md unmanaged by this story — left untouched | Skip; do not edit |
| OWNER_DECISION | CAP-7 open question still in SPEC frontmatter | Decision recorded: marshal owns living-doc cadence; open_questions emptied; memlog append | No error expected |

</intent-contract>

## Code Map

- `_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture-bmad-infra.md` — Part-4 BMAD infra; **re-grounded this story** to 6.11.0 / render pipeline / 5 agents / 20 shims / skf 2.1.0 (manifest).
- `_bmad-output/projects/*/project-context.md` (×8) — **pins bumped** to `BMAD 6.11.0 / conda-forge-expert v8.84.0` (marshal also `last_synced_skill_version`).
- `_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md` — **names marshal owner + living-doc cadence**.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-611-era-alignment/SPEC.md` + `.memlog.md` — CAP-7 open question **closed** (2026-08-24 marshal-duty decision).
- HOLD: `AGENTS.md` managed block — do not edit.
- Finalize surface (post-merge only): `planning-artifacts/sprint-status-ledger.yaml` keys `25-7-…` and `epic-25`.

## Tasks & Acceptance

**Execution:**
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture-bmad-infra.md` -- Re-ground to BMAD 6.11.0: At-a-Glance, Mission, Installed Skills (incl. render pipeline + renamed skills `bmad-build`/`bmad-build-auto`/`bmad-project-context`/`bmad-deep-recon`; 5 agents; 20 shims; nonskill dirs), TOML six-layer + `render_skill.py` snapshot pipeline; bump `source_pin` + re-grounded banner with live factory facts -- CAP-7 accuracy
- `_bmad-output/projects/{pyforge-atlas,pyforge-doctor,pyforge-herald,pyforge-marshal,pyforge-mason,pyforge-scribe,pyforge-steward,pyforge-warden}/project-context.md` -- Re-ground status/counts/6.11 notes against live ledgers; add or bump `source_pin` (marshal: also `last_synced_skill_version` → v8.84.0) -- all 8 rulebooks current
- `_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md` -- Name recurring owner **marshal** + living-doc re-ground cadence (with detector triggers); document marshal-duty decision -- CAP-7 recurrence
- `…/spec-bmad-611-era-alignment/SPEC.md` + `.memlog.md` -- Clear `open_questions`; append dated decision/event for CAP-7 owner = marshal -- close parent open question
- This story spec -- Auto Run Result documents admin merge + billing blocker after merge -- operator merge policy

**Acceptance Criteria:**
- Given a reader opens `architecture-bmad-infra.md`, when they check version/skill/agent/render claims, then they match the live 6.11 install (manifest 6.11.0; render_skill.py documented; no stale 6.10.0 / Paige / `data/` stray as current).
- Given each of the 8 `project-context.md` files, when frontmatter is inspected, then `source_pin` (or marshal's dual pin) reflects BMAD 6.11.0 / CFE v8.84.0 and body status matches the station ledger.
- Given SYNC-RUNBOOK, when an operator looks for living-doc ownership, then **marshal** is named with an explicit cadence tied to detector/`surface-changed` / CFE MINOR bumps.
- Given parent SPEC `spec-bmad-611-era-alignment`, when frontmatter + memlog are read, then CAP-7's open question is closed with the 2026-08-24 marshal-duty decision.
- Given the PR, when it is opened, then it carries the `maintenance` label and does not modify AGENTS.md managed content.

## Spec Change Log

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 4, low 2)
- defer: 5: (high 0, medium 2, low 3)
- reject: 4
- addressed_findings:
  - `[medium]` `[patch]` Multi-project ASCII tree showed SYNC-RUNBOOK under all stations — fixed to marshal-only subtree
  - `[medium]` `[patch]` Process/facilitation dropped `bmad-shard-doc` silently — added removed/no-forwarder gloss
  - `[medium]` `[patch]` Marshal tech-stack still claimed five workspace packages — recount against `src/shared/packages/`
  - `[medium]` `[patch]` Warden `project_phase: shipped` vs residual backlog — set `shipped-core` + clarify status
  - `[low]` `[patch]` Restored At-a-Glance Currently-active as ephemeral resolver note
  - `[low]` `[patch]` Restored concrete `forge_data_folder` path + clarified skf 2.1.0 authority is `manifest.yaml`
  - deferred (not this story): PROJECTS.md refresh; `--write-baseline` re-stamp; opaque ledger total grammar; deeper Guildhall/surface-checker narrative lag; parent SPEC body prose beyond frontmatter/memlog
  - rejected: rename marshal `project_name` away from `local-recipes` (factory-wide rulebook identity); atlas missing living-docs note (already in blurb); empty Auto Run Result pre-merge; verification-gap "none" as defect

## Design Notes

**Pin convention:** Prefer `source_pin: 'BMAD 6.11.0 / conda-forge-expert v8.84.0'` on station rulebooks. Marshal's existing `last_synced_skill_version` stays as the CFE pin key and is bumped; add `source_pin` alongside if absent.

**Re-ground depth:** Thin station stubs (doctor/herald/mason/scribe/steward/warden) get accurate status + a short 6.11 living-docs ownership note — not a full rewrite. Atlas and marshal keep their deeper rulebooks, with stale counts/versions corrected.

**Cadence text (golden):** after every CFE MINOR / `surface-changed` trip, and at least once per BMAD core minor bump, marshal re-grounds `architecture-bmad-infra.md` + the 8 `project-context.md` pins — stations do not each own a relay.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- Spot-check architecture At-a-Glance against `_bmad/_config/manifest.yaml` (6.11.0) and live skill directory counts.

## Auto Run Result

Status: `done`

**Summary.** Re-grounded `architecture-bmad-infra.md` to BMAD **6.11.0** (render pipeline, six-layer TOML, 5 agents, 20 shims, current skill set). Bumped all 8 station `project-context.md` pins to `BMAD 6.11.0 / conda-forge-expert v8.84.0`. SYNC-RUNBOOK names **marshal** as living-doc owner with cadence. Parent SPEC CAP-7 `open_questions` cleared; memlog records 2026-08-24 marshal-duty decision. AGENTS.md HOLD honored. Completes Epic 25 → **marshal DRAINED**.

**Review.** Patches applied: 4 medium + 2 low (score 14 → `followup_review_recommended: true`). Deferred: 5. Rejected: 4. No intent_gap / bad_spec.

**PR:** https://github.com/rxm7706/local-recipes/pull/722 — merged with `--merge --admin` (GitHub Actions billing blocker; docs-only verification green). **`maintenance` label applied.**

**Merge SHA:** `ac6c223c54502be026398159ca24273cd93f4663` (implementation commit `be983f9a3e` on branch `marshal/25-7-the-factorys-living-docs-are-re-grounded-with-a-named-owner`).

**Verification performed.**
- architecture stale-string grep: only historical/gloss hits
- all 8 contexts show bumped `source_pin` / marshal dual pin
- SYNC-RUNBOOK owner+cadence present
- `open_questions: []`
- `git diff --stat AGENTS.md` empty

**Finalize.** Sprint ledger: `25-7-…: done`, `epic-25: done`. Marshal station DRAINED (steward `12-7` remains operator-skipped).

**Residual risks.** Deferrals in frontmatter; thin station stubs are pin/status/ownership refreshes, not full rulebook rewrites.
