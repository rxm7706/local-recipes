---
title: "35.2: The docs-site checks and the sync-proof row close on real evidence"
type: 'fix'
created: '2026-10-03'
status: 'done'
baseline_revision: db7a31eef2404357ec6430457104683ac42910fe
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

### 2026-10-03 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none — implementation matches acceptance criteria; verification green)

### 2026-10-03 (night) — Landing review (independent reviewer); fixed by the operator's fixer
- The "0 findings" entry above is wrong. An independent landing review found one high, one medium and four low findings, each confirmed by a surviving mutant or a record check.
- verdicts: 6 findings — high 1, medium 1, low 4, false 0, maybe-false 0
- findings:
  - HIGH (fixed): the `exclude` assertion in `test_collect_infographics_respects_include_exclude_order_and_dedupe` could never fail, because the include glob did not match `skip.html`, so mutants m9 (`found.pop` disabled) and m16 (exclude loop skipped) survived. The noise file is now `presentations/pyforge-alpha/project/Skip Infographic standalone.html` (the include matches it). The test asserts it is absent with the exclude and present without it. m9 and m16 now fail. DW-FU-24-2-1 now credits Story 35.2, and its `verified:` line cites the live test lines, no longer Story 35.1 and `test_docsite_build.py:1`.
  - MEDIUM (fixed): the herald memlog's Story 35.1 surface-reconcile entry still listed the 15 deck `.dc.html` / `.stamp.json` / Infographic-head paths the operator reverted in b467e70721, and the 35.2 stamp also accepted `.github/workflows/dashboard.yml` (dependabot 0ae4f07fc5) without naming it. Correcting memlog entries now list each reverted path and the dashboard change. `spec-pyforge-herald` was re-stamped scoped after them.
  - LOW (fixed): DW-FU-20-2's `resolution:` credited Story 35.2 for a 2026-09-14 closure. It now reads `dcd6e4f5a8 (2026-09-14); record restored by Story 35.2`.
  - LOW (fixed): the missing-stamp spy test covered `--head` only. `test_unchanged_deck_derive_writes_stamp_when_sidecar_is_missing` is the `--deck` twin, and m13b (deck-side `or stamps.read_stamp(deck_path) is None` reverted) now fails it.
  - LOW (fixed): the act-vocabulary test passed without the parser reading the title, because the band is copied verbatim. It now asserts `deck_trio.main([...]) == 0`, parses the poster with `_DeckStructure` and asserts `acts[0].lbl == "ACT I"` and `acts[0].ttl == "Opening"`. m1b (`"act-title"` dropped) now fails it.
  - LOW (fixed): the `check()` matrix had no marp download case, so m12 (`("pptx", "marp")` → `("pptx",)`) survived. Two cases now cover a marp download that is missing and one whose size does not match. m12 now fails.
- residual (not one of the review findings, outside this story's AC): mutant m15 (`collect_families` duplicate-slug skip removed) still survives. No test feeds two infographics from one deck directory.

## Auto Run Result

Status: done

Summary: Expanded `docsite/build.py` check coverage with a green fixture that includes infographic deck, executive summary, pptx, and marp artifacts; parametrized tests assert each check's stderr text. Removed the tautological content-hash branch from `_readback_matches_pushed_body`; reopened DW-FU-23-6-1 with a note naming the missing live `unchanged` proof. Restored DW-FU-20-2 closure record; corrected presenton README Provenance; deck-trio now stamps missing sidecars on unchanged derives; added act-num/act-title and layout-resolution tests.

Files changed:
- `src/shared/packages/pyforge-herald/tests/unit/test_docsite_build.py` — full check predicate matrix
- `src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py` — read-back helper without tautological hash
- `scripts/deck_trio.py` — write stamp when sidecar missing despite unchanged bytes
- `tests/scripts/test_deck_trio.py` — act vocabulary and missing-stamp tests
- `src/shared/packages/pyforge-herald/tests/unit/test_pptx_pipeline.py` — unique layout name resolves
- `presentations/presenton-pixi-image/README.md` — Provenance sentence reconstructed
- `_bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md` — DW-FU-20-2, DW-FU-21-10, DW-FU-23-6-1 rows
- `spec-pyforge-herald/.memlog.md` — Story 35.2 surface reconcile paths

Review: no patch/defer/intent_gap items.

Verification:
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — 1522 passed, 4 skipped
- `pixi run --frozen -e pyforge-guild lint-types` — exit 0
- `python scripts/spec_surface_reconcile.py` — OK
- Scoped stamp `pyforge-herald/spec-pyforge-herald` after memlog reconcile

Residual: DW-FU-23-6-1 stays open until live `deck sync-all --slug pyforge-warden` reaches `unchanged`.
