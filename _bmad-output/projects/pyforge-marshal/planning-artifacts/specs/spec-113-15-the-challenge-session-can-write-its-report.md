---
title: "113.15: the challenge session can write its report"
type: 'fix'
created: '2026-11-04'
status: 'done'
baseline_revision: 'f604a1ab86'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/challenge_harness.py
deferred: []
declared_low_risk: true
---

<intent-contract>

## Intent

**Problem:** the first real challenge (the 2026-11-04 pilot, a mint review of atlas CAP-72) ran all three reviewers and
ended unevaluable, because the session could not write `report.json`. `widen_settings`
(`src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/challenge_harness.py:126`, `:130`) renders
`Write(<path>)` rules, and Claude Code 2.1.318 says of both that the rule "is not matched by file permission checks — only
Edit(path) rules are". The allow never bound, and the `slices/` deny protected nothing. `MultiEdit` in `DENIED_TOOLS`
"matches no known tool". Every run on this Claude Code would end the same way.

**Approach:** render `Edit(<run folder>/**)` and `Edit(<run folder>/slices/**)`, which cover the `Write` tool, and drop
`MultiEdit`. The bare `Edit` deny stays: the session needs the `Write` tool and never the `Edit` tool. A probe in the
pilot's folder layout proved the form with the bare deny kept, and the re-run pilot proved it on a real session. A `fix`
under CAP-299: no CAP, no flag.

Ledger key: `113-15-the-challenge-session-can-write-its-report`. Type / Effort / Deps: fix / S / —.

## Acceptance Criteria

- **AC1 — The report lands.** A live challenge run writes `report.json` into its run folder and exits 0.
- **AC2 — The bound holds.** The rendered settings allow `Edit(<run folder>/**)`, deny `Edit(<run folder>/slices/**)` and
  carry no `Write(<path>)` rule; with no run folder they carry neither.
- **AC3 — No unknown tool.** `DENIED_TOOLS` names no `MultiEdit`, and `session.log` carries no permission-rule warning
  from the rendered settings.
- **AC4 — The contract follows.** CAP-299 names the `Edit(<path>)` form, and the cascade and the scoped stamp land.

## Boundaries & Constraints

- The session's tools, cwd, hooks and `Read` denies do not change.
- No live call in a test: AC1 is proved by the re-run pilot, and the unit tests pin the rendered rules.

## Binding

- spec-pyforge-marshal CAP-299 (FR-241); Epic 113. The fix lands in the done epic and at `done`, so `epic-113` stays `done`.

## Verification

```bash
pixi run --frozen -e pyforge-marshal pyforge-marshal-test
```

</intent-contract>

## Spec Change Log

- 2026-11-04: minted from the first EGM pilot; landed with Story 113.16 in one PR.
- 2026-11-04: `done` on the re-run pilot, run `pyforge-atlas-20261105T003923891Z-1b2adcaa` (the same mint review of atlas
  CAP-72 on the fix): exit 0 in 198 s, `report.json` in its run folder with the bare `Edit` deny in force (AC1), and no
  permission-rule warning in `session.log` (AC3). The report is Tier 3, in the primary checkout under pyforge-atlas's
  `implementation-artifacts/egm/`.
- 2026-11-04: independent review (a fresh reviewer, on the diff against this spec) asked for this evidence; recorded here
  and in the memlog.
