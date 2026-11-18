---
title: '125.4: The laptop preflight''s local prerequisites are written down, and the preflight is green'
type: 'fix'
created: '2026-11-17'
status: 'ready-for-dev'
story: 125-4-the-laptop-preflight-s-local-prerequisites-are-written-down-and-the-preflight-is-green
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - 'docs/how-to/run-and-read-pr-preflight.md'
  - 'scripts/.spec-surface-baseline.json'
  - '_bmad-output/projects/pyforge-*/planning-artifacts/specs/spec-pyforge-*/.memlog.md'
  - '_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - docs/how-to/run-and-read-pr-preflight.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Scribe's live suite needs the PostgreSQL cluster `scribe-pg-up` starts and atlas's dashboard tests need Playwright's Chromium, and no page a laptop operator reads says so; Stories 125.1 to 125.3 move governed files.

**Approach:** The preflight how-to names both prerequisites, each governing Spec's memlog names the moved paths and is stamped scoped, and the full preflight is run alone on the final head.

Ledger key: `125-4-the-laptop-preflight-s-local-prerequisites-are-written-down-and-the-preflight-is-green`.

### Living CAP citations

- **`spec-pyforge-steward` CAP-175** — the preflight and a PR's CI answer within a measured budget; this story realizes "answers" on the documented laptop platform, with no capability text change.

## Boundaries & Constraints

**Always:**
- Guard by probing the capability a test needs; name the missing capability in the reason.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never skip by platform name, weaken an assertion that holds on Linux, or change `pixi.toml` / `pixi.lock`.

## Acceptance Criteria

**Given** scribe's live suite needs the PostgreSQL cluster `scribe-pg-up` starts and atlas's dashboard tests need Playwright's Chromium, and no page a laptop operator reads says so; Stories 125.1 to 125.3 move governed files
**When** the preflight how-to names both prerequisites, each governing Spec's memlog names the moved paths and is stamped scoped, and the full preflight is run alone on the final head
**Then** `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` exits 0 on the macOS laptop with the two prerequisites met; `spec-surface-check` and `docs-currency-check` exit 0
**And** every guard is a capability probe with a reason that names the missing capability

- **AC1 — The lanes this story names pass on the laptop.** Expected: exit 0.

  ```bash
  PYFORGE_PREFLIGHT_SCOPE=full pixi run --frozen -e pyforge-guild pr-preflight
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-175 (realizes: the preflight answers; no text change); FR-49 ← CAP-175; no AD moves.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-11-17 (the laptop preflight) entry.
- Epic: Epic 125, minted with this story.
- Ledger key: `125-4-the-laptop-preflight-s-local-prerequisites-are-written-down-and-the-preflight-is-green` (`backlog`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."125"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-17: minted from the station Dream's 2026-11-17 entry (the laptop preflight) and the operator's ruling of the same date.
