---
title: The gated upstream filing
type: chore
created: '2026-08-23'
status: done
shipped_ref: 'PR #684 / b0c10436ec'
updated: '2026-08-23'
context: []
warnings: []
baseline_revision: 936b47178a0d62e49e40a87fa8db706ff88921c8
followup_review_recommended: true
deferred:
  - summary: >-
      Parent Spec CAP-3 memlog/SPEC success oracle still describes the draft as unfiled; sync on a later docs pass if needed.
    evidence: |-
      Blind-hunter finding: spec-bmad-loop-baseline-drift CAP-3 text may still say gated/unfiled; outside this chore's Code Map surfaces.
  - summary: >-
      If #701 closes only one half of the coordinated report, split or re-note the register entry so FR-189 is not silently retired.
    evidence: |-
      Edge-case hunter: single upstream_status on a dual-mode coordinated filing.
---

<intent-contract>

## Intent

**Problem:** CAP-3 (`spec-bmad-loop-baseline-drift`) requires the drafted upstream issue in `docs/dreams/bmad-loop-baseline-drift.md` to be filed against `bmad-code-org/bmad-loop` only after two gates — or a duplicate linked instead. Until gates clear, the draft stays unfiled by design. Story 10.1 intent-gap evidence shares this report path.

**Approach:** Record both gates as checked: (1) repo access / org relationship → issue vs PR vs discussion; (2) duplicate search first. Then either file the coordinated issue (append URL to both Dreams' Realization logs; register in `upstream-register.json`) or link a found duplicate. Never edit the installed `bmad_loop` package. Never implement 20.4–20.10.

## Acceptance Criteria

- Gate (1) and gate (2) recorded as checked in Dream Realization log(s) and/or story evidence.
- Outcome is either a filed upstream URL **or** a linked duplicate URL — never a silent skip without gate records.
- Both Dreams' Realization logs updated (`bmad-loop-baseline-drift` + `bmad-loop-intent-gap-work-preservation` as applicable).
- `upstream-register.json` (Story 6.8 register) gains/updates the entry.
- No edits to `bmad_loop` package source; no auto-land of deferred work.

## Boundaries & Constraints

**Never:** Patch `bmad_loop`. Never implement 20.4–20.10. Never `scripts/bmad-switch`. Finalize marshal ledger only. Do not touch steward 16-2.

</intent-contract>

## Code Map

- `docs/dreams/bmad-loop-baseline-drift.md` — gates + filed URL + Realization log
- `docs/dreams/bmad-loop-intent-gap-work-preservation.md` — shared report Realization log
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/upstream-register.json` — `baseline-commit-midflight-drift`

## Verification

- Gates documented; URL present (filed or duplicate): https://github.com/bmad-code-org/bmad-loop/issues/701
- Register + Realization logs updated
- No `bmad_loop` package mutations in the PR (`git diff` excludes site-packages / package source)

## Gate evidence (Story 20.3)

### Gate (1) — repo access / org relationship

- Viewer: `rxm7706` (token scopes include `repo`)
- `bmad-code-org/bmad-loop` permissions: `pull=true`, `push=false`, `triage=false`, `maintain=false`, `admin=false`
- `has_issues=true`, `has_discussions=false`
- **Channel decision:** GitHub Issue (cannot push a PR to upstream; Discussions disabled)

### Gate (2) — duplicate search

- Searched: `baseline_commit`, orchestrator-recorded / mid-flight, `intent_gap` / `attempt-preserve` / `keep_failed`
- No duplicate of mid-flight automatic-retry drift or intent-gap-without-preserve
- Adjacent only: https://github.com/bmad-code-org/bmad-loop/issues/640 (`rearm_escalation` baseline vs `baseline_revision` — re-arm path)

### Outcome

Filed: https://github.com/bmad-code-org/bmad-loop/issues/701

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 1, medium 2, low 1)
- defer: 2: (medium 2)
- reject: count absorbed (epics/ledger done-signal belongs to finalize; Dream frontmatter status; abbreviated review CONTENT; SPEC/memlog CAP-3 oracle sync beyond this chore's Code Map; splitting the coordinated issue into two register rows against the shared-report intent)
- addressed_findings:
  - `[high]` `[patch]` Removed non-schema `upstream_url` key; put full #701 URL in `note` so `parse_register` / `marshal upstream` retain it
  - `[medium]` `[patch]` `compensating_fr` → `FR-188` primary; note clarifies FR-189 evidence rides the coordinated issue without dual-status conflation
  - `[medium]` `[patch]` Gap/workaround prose adds occurrence evidence + maturity split (20.1–20.2 shipped vs 20.4+ planned)
  - `[low]` `[patch]` Intent-gap Dream Kinships updated from "likely share" to filed #701 / register id
  - deferred (not patched here): parent Spec CAP-3 memlog oracle sync; future partial-close of #701 requiring register split — tracked in note

## Auto Run Result

Status: done

Summary: Gates recorded; coordinated upstream issue #701 filed; both Dreams' Realization logs updated; `upstream-register.json` entry `baseline-commit-midflight-drift` added (URL in `note` per UpstreamGapEntry schema). No `bmad_loop` package edits; 20.4–20.10 untouched.

Files changed:
- `docs/dreams/bmad-loop-baseline-drift.md`
- `docs/dreams/bmad-loop-intent-gap-work-preservation.md`
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/upstream-register.json`
