---
title: "84.2: The model-list refresh tests can fail, and a partial listing is never complete"
type: 'fix'
created: '2026-10-03'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/model_list_live.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/model_list_http.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/adapters.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/model_list_refresh.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 84.1 landed by operator ruling with its behaviour proved safe by probes, but its fourth independent review found the tests cannot catch a regression and left small gaps: the CLI sentinel test stubs `fetch_live_ids_for_profile`, runs JSON only, and passes with a mutant that reintroduces the original key leak; the redirect test models no target; a later page with the `data`/`models` key missing, or an error body, reads as a complete listing; a cursor `Warning …` line parses as an id; a harness unavailable on a new day has its last ok ids written under today's date as a live read; the single-importer meta-test misses `import` and package-relative forms; `model_map` refs name the overlay whenever its file exists, even when the overlay was rejected; the fetch port is built inside the handler; spec-pyforge-marshal memlog entries name `adapters/oidc_pkce.py`, which the story never touched.

**Approach:** Make the tests able to fail and close the gaps, as listed in Story 84.1's spec (Review Triage Log, the 2026-10-03 night entry).

Ledger key: `84-2-the-model-list-refresh-tests-can-fail-and-a-partial-listing-is-never-complete`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-285 (Story 84.1's follow-ups, by operator ruling 2026-10-03). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a patched `HTTPSConnection` that raises with a sentinel key in its message, a redirect to a second port, and a second healthy harness When `run_adapters_models` runs in text and JSON Then the sentinel never appears, the second port receives no request, and the healthy harness reports; and a mutant that passes the transport exception text into `reason` fails this test
- Given a later page with the list key missing, null, or an error body When the listing runs Then the harness is `unavailable` ("unexpected page shape"), never `ok` with page 1's ids; and a cursor line that is not an id (`Warning …`, `Error …`) is never parsed as one
- Given a harness unavailable on a new day with `--write` When the snapshot is written Then its last ok block is carried only for a same-day re-run, or recorded with the date it came from, never as today's live read
- Given an `import pyforge.marshal.adapters.model_list_live`, `from ..adapters import model_list_live` or a `model_list_http` import outside `cli/adapters.py` When the meta-test runs Then it fails
- Given the change When `pixi run --frozen -e pyforge-marshal pyforge-marshal-coverage-gate` runs Then it exits 0

## Boundaries & Constraints

**Always:** Prove each test can fail with a mutant. Append a correcting memlog entry for the `oidc_pkce.py` lines (never edit an existing entry).

**Never:** Never put a credential in a test fixture that could be mistaken for a real key; use an obvious sentinel.

</intent-contract>

## Binding

Parent: Story 84.1 (`spec-pyforge-marshal` CAP-285).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-03 (night, later) entry.
Ledger key: `84-2-the-model-list-refresh-tests-can-fail-and-a-partial-listing-is-never-complete`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 at the operator's request.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
