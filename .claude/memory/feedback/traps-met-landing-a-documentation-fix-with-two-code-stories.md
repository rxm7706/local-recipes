---
name: "traps-met-landing-a-documentation-fix-with-two-code-stories"
description: "Traps met landing a documentation fix with two code stories (2026-11-24, doctor 61.1, steward 132.1, warden 28.1): (1)…"
metadata:
  type: feedback
---

Traps met landing a documentation fix with two code stories (2026-11-24, doctor 61.1, steward 132.1, warden 28.1): (1) a memlog entry on a Spec with no SPEC.md re-derive in the same change reds scribe's test_spec_not_behind_memlog (pyforge-scribe-live-test); record an owed Spec correction as a deferred-work row instead; Surface reconcile entries are bookkeeping and pass. (2) A new story must appear in its station's generated story matrix: python _bmad/scripts/bmad_tea_playwright.py --project pyforge-<station>, or pyforge-doctor-scripts-test reds. (3) A new environment variable or Django setting read in steward or warden code needs a row in that station's contract.md, or its test_public_contract reds in the live-tree half. (4) ad_citation_check accepts canopy:AD-15, not 'canopy AD-15'. (5) Editing a file another page lists in sources: makes that page read stale to docs-currency after the commit; re-read each and move its verified: date. (6) On macOS, platform-ci-local -- --test needs a UTF-8 locale (initdb otherwise builds SQL_ASCII) and refuses without docker though the stage never uses it; pr-preflight does not run the platform suite. (7) Run ruff from the package directory: --config from the repo root sorts first-party imports differently.
