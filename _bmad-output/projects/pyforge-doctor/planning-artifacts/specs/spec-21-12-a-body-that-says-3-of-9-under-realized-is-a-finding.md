---
title: 'A body that says "3 of 9" under `realized` is a finding'
type: 'feature'
created: '2026-09-10'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `bmad-drift-check` polices frontmatter vocabulary and counts, and
`dreams-hygiene` polices row presence — but nothing polices whether a document's
**prose** still agrees with its own `status:` frontmatter. Six documents failed that
test in one 2026-09-09 pass. The clearest live example: `docs/dreams/pyforge-scribe.md:69`
reads *"3 of 9 stories complete overall"* under `status: realized`, and
`spec-pyforge-scribe` repeats the same stale figure under `shipped`.

**Approach:** A new source module (shared across Stories 21.12-21.16, the
`spec-status-body-consistency` CAPs) implements CAP-1: a bounded pattern reads "N of
M stories/capabilities" (and the bare `N/M` form) with `N < M` under `status:
realized|shipped|done`. It fires on the live `pyforge-scribe.md:69` and
`spec-pyforge-scribe` cases. The finding **names the line it read** and never renders
a verdict on the document itself (it reports the contradiction, not a judgment about
whether the document is "wrong"). It stays silent across the rest of the live tier,
with that count recorded. It is warn-only, read-only, and fail-open — an unparseable
document is a named finding, never silence.

## Boundaries & Constraints

**Always:**
- The pattern matches "N of M stories/capabilities" (and the bare `N/M` form) with
  `N < M`, scoped to documents whose frontmatter `status:` is `realized`, `shipped`,
  or `done`.
- The finding names the exact line it read.
- The check is warn-only and read-only.
- An unparseable document is a named finding, never silence.
- It must fire on both `docs/dreams/pyforge-scribe.md:69` ("3 of 9 stories complete
  overall" under `status: realized`) and on `spec-pyforge-scribe` (same stale figure
  under `shipped`), and it must stay silent across the rest of the live tier — that
  silent count is recorded.

**Never:**
- The check never renders a verdict on the document (e.g. never says the document is
  "wrong" or "broken") — it reports the line-level contradiction only.
- Never write to or modify the documents it reads.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Live case 1 | `docs/dreams/pyforge-scribe.md:69`, "3 of 9 stories complete overall" under `status: realized` | Fires, names the line | n/a |
| Live case 2 | `spec-pyforge-scribe`, same stale figure under `status: shipped` | Fires, names the line | n/a |
| Rest of live tier | All other documents under `realized`/`shipped`/`done` | Stays silent; the silent count is recorded | n/a |
| N == M or N > M | A document reads e.g. "9 of 9" or "10 of 9" | No finding (pattern requires `N < M`) | n/a |
| Unparseable document | A document that cannot be parsed for frontmatter/body | Named finding | Fail-open, never silent |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/` — new source module for `spec-status-body-consistency` (shared home for Stories 21.12-21.16).
- `src/shared/packages/pyforge-doctor/tests/unit/` — new unit tests.
- `src/shared/packages/pyforge-doctor/tests/fixtures/` — fixtures including the `pyforge-scribe.md`/`spec-pyforge-scribe` live case shape.

## Tasks & Acceptance

**Execution:**
- `feature` — create the new source module and implement CAP-1's bounded "N of M" / "N/M" pattern match, scoped to `realized|shipped|done` documents.
- `feature` — emit a warn finding naming the exact line read, with no verdict rendered on the document itself.
- `feature` — handle unparseable documents as a named finding rather than silence.
- `feature` — add fixtures/tests proving the check fires on the `pyforge-scribe.md:69` and `spec-pyforge-scribe` live cases and stays silent elsewhere, with the silent count recorded.

**Acceptance Criteria:**
- Given `bmad-drift-check` polices frontmatter vocabulary and counts and `dreams-hygiene` polices presence, so nothing polices whether a document's prose still agrees with its own `status:` — six documents failed that test in one 2026-09-09 pass — when a bounded pattern reads "N of M stories/capabilities" (and the N/M form) with N < M under `status: realized|shipped|done`, then it fires on `docs/dreams/pyforge-scribe.md:69` ("3 of 9 stories complete overall" under `status: realized`) and on `spec-pyforge-scribe`, which repeats the same stale figure under `shipped`.
- The finding names the line it read and never renders a verdict on the document.
- It stays silent across the rest of the live tier, with that count recorded.
- It is warn-only, read-only and fail-open — an unparseable document is a named finding, never silence.

## Spec Change Log

## Review Triage Log
