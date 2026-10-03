---
title: "35.2: The docs-site checks and the sync-proof row close on real evidence"
type: 'fix'
created: '2026-10-03'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-35-1-the-deck-transport-sync-all-deck-tooling-and-docs-site-close-their-open-deferrals.md
  - docsite/build.py
  - scripts/deck_trio.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 35.1 auto-landed (PR #1796, merge 4a3498f7f5) after its send-back pass, before a landing review. The post-landing review found four send-back items only partly done, so two medium rows closed without the fix the spec requires. DW-FU-24-2-1: `docsite/build.py` `check()` has 15 problem checks and only 4 have a test that makes them fire; the green fixture has no executive summary or pptx, so the family-view and download checks never run; five mutants survive (the out_name dedupe, `exclude`, the gallery check, the download-size check, `executive_summary` forced to None). DW-FU-23-6-1: the read-back normalisation tolerates only CRLF and trailing newlines, with no byte evidence of what the server changes, and the "content hash" branch (`deck_pipeline.py`, about 1871-1872) compares the hash of the same bytes. DW-FU-21-2: the `.act-num`/`.act-title` vocabulary has no test (the unifying-strategy poster depends on it). DW-FU-21-10: the README sentence keeps an invented clause and now says the reverse of the original. The healed-tissue edit also removed DW-FU-20-2's own closure record, the session flipped `epic-35` on its branch, the herald memlog names reverted deck paths and no scoped stamp was written, a unique layout name resolving is untested, and an unstamped deck that derives unchanged is never stamped.

**Approach:** Give each check a test that fails without it; reopen DW-FU-23-6-1 until a live proof exists; correct the records.

Ledger key: `35-2-the-docs-site-checks-and-the-sync-proof-row-close-on-real-evidence`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- The capabilities that shipped each behaviour (Story 35.1's rows); a defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given `docsite/build.py` `check()` When each of its problem checks is broken alone Then a test fails, asserting that check's stderr text (suspiciously small, shrank, missing from gallery, family page missing/small/Jinja, missing from decks index, view not published/shrank, download missing/size mismatch); the green fixture carries a real infographic deck, executive summary, pptx and marp with published views and downloads; two colliding slugs produce `-1.html`; an `exclude` removes a file the include matched; `collect_families` asserts the exact `executive_summary`, `pptx` and `marp` names and byte counts
- Given DW-FU-23-6-1 When this story lands Then the tautological content-hash branch and its parameter are gone, and the row is `status: open` with a note naming the missing proof (a live `deck sync-all --slug pyforge-warden` reaching `unchanged`), unless that proof is captured
- Given a poster fixture using `.act-num`/`.act-title` When `deck-trio --deck` runs Then it derives with non-empty act labels and titles and exits 0 (dropping that vocabulary fails the test)
- Given `presentations/presenton-pixi-image/README.md` When it is read Then its Provenance sentence says the trio was not seeded on 2026-07-25 and awaits a DesignSync pass (no invented clause), and DW-FU-21-10's `verified:` line says the sentence was reconstructed
- Given DW-FU-20-2 When the ledger is read Then its closure record (the `closed: 2026-09-14` paragraph removed from DW-21-7-2 by Story 35.1) is restored under it as `resolution:`/`verified:`
- Given a deck with no stamp that derives unchanged When `deck-trio` runs Then it writes the stamp (a test); and `_resolve_layout` resolves a unique name to that layout (a test)
- Given the herald memlog When this story lands Then a correcting entry names the reverted `presentations/` paths as not changed by Story 35.1, and `spec-pyforge-herald` is stamped scoped

## Boundaries & Constraints

**Always:** Pin each behavioural fix with a test that fails without it. Re-cite each `verified:` line at its live `path:line`. Name every governed path on the owning memlog, then a scoped stamp.

**Never:** Never re-push a poster to Claude Design. Never flip `epic-35` or any ledger key on the branch. Never run deck generation into the tracked tree.

</intent-contract>

## Binding

Parent: Story 35.1 (its rows).
Dream: `docs/dreams/pyforge-herald.md` § *Realization log*, the 2026-10-03 (night) entry.
Ledger key: `35-2-the-docs-site-checks-and-the-sync-proof-row-close-on-real-evidence`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-03 from the post-landing review of Story 35.1.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

- No review has run yet.
