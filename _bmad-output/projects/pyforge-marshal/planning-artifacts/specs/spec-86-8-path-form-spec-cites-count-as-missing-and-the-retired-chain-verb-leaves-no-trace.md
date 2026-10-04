---
title: "86.8: Path-form spec cites count as missing, and the retired chain verb leaves no trace"
type: 'fix'
created: '2026-10-04'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-86-5-the-chain-tooling-sheds-its-retired-and-noisy-paths.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/chain_regen.py
  - src/shared/packages/pyforge-marshal/pyproject.toml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 86.5 landed as #1821 on 2026-10-04. Its independent review finished after the merge and sent it back; the full report is in 86.5's Review Triage Log.

- **MEDIUM:** `core/chain_regen.py` `_spec_cites` (around :428-455) drops any candidate that is neither a known spec id nor shaped `spec-<digits>-<digits>`. So real missing cites are now silently skipped:
  - pyforge-atlas `epics.md` holds 26 "Full record: `specs/spec-a1-scaffold-…md`"-style links (lines 252, 280, 461, 559, …) plus `spec-a2` / `spec-b6` short forms (:1122). Commit 893c96110d0 renamed those files to canonical ids, and the old names exist nowhere in the tree. Main counted them missing; after 86.5, atlas reads 1 missing instead of 45.
  - pyforge-steward `epics.md:4304` cites `spec-sprint-ledger-query-module`, a folded Spec folder that no longer exists. By design, a Spec-folder cite can now never be missing.
  - So 86.5's closing note on DW-FU-21-2 ("names each missing one"; every uncounted candidate is a prose word) is false on the live tree.
- **LOW:** `src/shared/packages/pyforge-marshal/pyproject.toml:239-241` still carries the mypy override for the deleted `pyforge.marshal.cli.chain`. With `warn_unused_configs = true`, lint-types prints an unused-section note.
- **LOW:** the retired `marshal chain regenerate` verb is still documented in these places:
  - `docs/reference/station-cheat-sheet.md:92,97,124` (generated; `scripts/docs_station_cli.py --check` exits 1);
  - `docsite/content/dossier.yml:676`;
  - `presentations/pyforge-marshal/project/PyForge Marshal - Infographic.dc.html:594` and `…Infographic standalone.html:591`;
  - the comment at `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py:1037`.

**Approach:**
- In `_spec_cites`, treat a candidate written as a path (the match preceded by `specs/`) as a story-spec cite even when its id is not numeric, and count it missing when it resolves nowhere. A probe over every project found this adds exactly the 26 atlas links and no prose words. Do not key on a `.md` suffix, which would wrongly count `spec-template` in marshal.
- Repair the 26 stale atlas links and the steward cite, so they point at the renamed canonical spec, or at the folded Spec's new home.
- Drop the dead mypy override.
- Regenerate the cheat sheet with `pixi run -e pyforge-guild docs-station-cli`.
- Fix the dossier and infographic mentions at their source of record (regenerate if generated) and the `verdict.py` comment.
- Amend the DW-FU-21-2 resolution text.

Ledger key: `86-8-path-form-spec-cites-count-as-missing-and-the-retired-chain-verb-leaves-no-trace`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- The chain-linkage verify (Story 21.2; DW-FU-21-2, closed by 86.5). A defect of shipped behaviour, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given an `epics.md` citing `specs/spec-a1-old-name.md`, a file that exists nowhere When the code-linkage verify runs Then it counts that cite missing and names it; a fixture test pins it, and removing the path rule fails the test
- Given marshal's `spec-template` prose mention When the verify runs Then it is still not counted (no `.md`-suffix keying)
- Given the live tree after the repairs When the verify runs across every station Then no station reports a missing cite that names a stale or folded spec
- Given lint-types When it runs Then there is no unused-section note for `pyforge.marshal.cli.chain`
- Given `scripts/docs_station_cli.py --check` When it runs Then it exits 0, and no live doc, dossier or deck describes `marshal chain regenerate` as a current verb
- Given the deferred-work ledger When DW-FU-21-2 is read Then its resolution states the path-form rule and cites its live `path:line` and test

## Boundaries & Constraints

**Always:** Keep one cite rule in `chain_regen.py`. Fix a generated doc by regenerating it. Name every co-governed path (atlas, steward, herald, docs) in its governing spec's memlog.

**Never:** Never weaken the verify to hide a real missing cite. Never edit a historical record: the PRD, older story specs and the architecture spine keep their mentions.

</intent-contract>

## Binding

Parent: Story 86.5 (#1821) and its post-landing review.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (night) entry.
Ledger key: `86-8-path-form-spec-cites-count-as-missing-and-the-retired-chain-verb-leaves-no-trace`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-04 at the operator's request ("chain it Story 86.8 in Epic 86").

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0 with no unused-section note.
- `python3 scripts/docs_station_cli.py --check` — expected: exit 0.

## Review Triage Log

- No review has run yet.
