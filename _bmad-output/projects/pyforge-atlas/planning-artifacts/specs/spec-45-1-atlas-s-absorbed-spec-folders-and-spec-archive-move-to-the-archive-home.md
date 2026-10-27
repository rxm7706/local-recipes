---
title: "45.1: Atlas's absorbed Spec folders and spec-archive move to the archive home"
type: 'chore'
created: '2026-10-27'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
baseline_revision: '9dd0a8f1f9'
context:
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - docs/dreams/one-chain-per-station.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - docs/governance/chain-sprawl-baseline.json
  - docs/foundry/capability-ledger.yaml
deferred: []
---

<intent-contract>

## Intent

**Problem:** spec-one-chain-per-station:CAP-11 (operator ruling 2026-09-29; CHAIN-STANDARD §11) sends everything the
fleet retires to `archive/<original path>`. Its order is: the archived Dreams first (PR #2328, 2026-10-26), then the
absorbed and archived Spec folders, each with its memlog and every companion. At `9dd0a8f1f9` (2026-10-27), 10 atlas
folders still read `status: absorbed` under `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/`: `spec-artifactory-download-intelligence`, `spec-atlas-kedro-catalog-expansion`, `spec-atlas-query-dashboards`, `spec-conda-forge-packaging-inventory-operations`, `spec-enterprise-data-models-and-apis`, `spec-kedro-org-tooling-adoption`, `spec-microsoft-org-sweep`, `spec-pyforge-atlas-intelligence-platform`, `spec-upstream-discovery`, `spec-wagtail-corporate-brain`.

**Approach:**
- **Carry the live companions first (operator ruling 2026-10-27).** `spec-atlas-kedro-catalog-expansion/catalog-sources.md` is not a record: a program, test or workflow opens it, or an instruction surface names it as the current home. It moves with `git mv` to `specs/spec-pyforge-atlas/<same name>`, and its readers follow it there. The absorbed folder's memlog gains an event naming where the companion went, before the folder moves.
- **Then the move.** Each of the 10 folders moves with `git mv` to `archive/<original path>`, with its pointer `SPEC.md`,
  its `.memlog.md` and its record companions. Nothing is deleted, and no moved file's text changes, apart from the memlog
  event appended before the move.
- **Pointers follow, records do not.** These follow the move:
  - every live pointer that named a moved path (code, tests, workflows, docs, deck headers);
  - `docs/foundry/capability-ledger.yaml`'s source paths;
  - the `SPEC.md` lines that name a moved path, script-rendered under the memlog with anchors asserted once and both
    self-validate passes logged.

  Memlogs, story specs, epic bodies, PRD prose, ledgers, research and the Dreams' own logs keep the path they were written
  with. `archive/<original path>` is structure-preserving, so the old path still reads.
- **Detector baselines.** `chain-sprawl`'s baseline drops the entries for the moved folders.
- **Also in this story.** `_bmad-output/projects/pyforge-atlas/spec-archive/` (29 files) moves to `archive/_bmad-output/projects/pyforge-atlas/spec-archive/`, the second side archive CHAIN-STANDARD §11 folds in.

Ledger key: `45-1-atlas-s-absorbed-spec-folders-and-spec-archive-move-to-the-archive-home`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- spec-one-chain-per-station:CAP-11: the Guild's. Atlas mints no CAP and no FR, in the relay shape of doctor
  Epic 36, marshal Epic 75, herald Epic 33 and the 2026-10-26 mop. See CHAIN-STANDARD §11.
- `spec-feature-flag-governance` Q1: a `chore` needs no flag.
- Siblings, the other seven station stories of the 2026-10-27 one-PR close-out: atlas 45.1, doctor 54.1, herald 49.1,
  marshal 112.1, mason 36.1, scribe 30.1, steward 116.1, warden 24.1.

## Acceptance Criteria

- Given the 10 folders named above, when `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/` is listed, then none of them is there, and each sits at `archive/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/<same name>/` with the same files, less any carried companion.
- Given a moved file, when it is diffed against its pre-move content, then it is byte-identical, apart from the one memlog event appended before the move.
- Given every live pointer that named a moved path, when the repo is grepped, then it names the new path. `governance-currency`, `spec-surface`, `ad-citation`, `chain-sprawl`, `dream-chain` and `detectors-ci` all exit 0.
- Given the station suite, when `pixi run --frozen -e pyforge-atlas pyforge-atlas-test` runs, then it passes.

## Tasks

1. Carry each live companion into `specs/spec-pyforge-atlas/`, with a memlog event on the absorbed folder first.
2. `git mv` the 10 folders to `archive/<original path>`.
3. Re-point every live pointer, and prune `docs/governance/chain-sprawl-baseline.json`.
4. Append a memlog event to `spec-pyforge-atlas` (and to each co-governor the detector names), script-render the
   `SPEC.md` lines that name a moved path, then run a scoped `--write-baseline --spec`.
5. Run the planning detectors and the station suite, and read every verdict from the exit code.

## Boundaries & Constraints

**Always:**
- Move with `git mv`.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not archive a live companion.
- Do not delete a file.
- Do not rewrite a dated record to name the new path.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| record-only folder | pointer, memlog and record companions | whole folder under `archive/` | — |
| live companion | a program, test or workflow opens it | carried to `specs/spec-pyforge-atlas/`; its readers repointed | — |
| dated record naming the old path | memlog, story spec, PRD prose | left as written | — |
| capability ledger row | `source:` names a moved Spec | names the archive path | — |

</intent-contract>

## Binding

- Parent capability: spec-one-chain-per-station:CAP-11 (Guild relay; no atlas CAP or FR).
- Dream: `docs/dreams/one-chain-per-station.md`, § *2026-10-27 — The absorbed Spec folders and the last side archives leave the live tree*.
- Ledger key: `45-1-atlas-s-absorbed-spec-folders-and-spec-archive-move-to-the-archive-home`.
- Deps: none.
- Flag: none. This is a `chore` (`spec-feature-flag-governance` Q1).

## Verification

**Commands:**
- `pixi run -e pyforge-guild chain-sprawl-check`: expect exit 0.
- `pixi run -e pyforge-guild spec-surface-check`: expect exit 0 after the scoped stamps.
- `pixi run --frozen -e pyforge-atlas pyforge-atlas-test`: expect a pass.

**Manual checks:**
- `grep -l '^status: absorbed' _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/*/SPEC.md`: expect no output.

## Review Triage Log

- **2026-10-27 — Independent review** (fresh reviewer, diff `9dd0a8f1f9..6a3ed54289`, read-only, scripted checks over the whole set): 0 deleted files, 399 pure renames + 10 memlogs changed only by the appended event; SPEC.md diffs limited to the documented lines with CAP counts unchanged. Fleet findings, all fixed in this PR:
  - `[high]` `[patch]` the conda-forge-expert surface lost its drift governor when spec-packaging-factory and spec-conda-forge-expert-rebuild moved: operator ruling 2026-10-27, `spec-pyforge-mason` governs it with normal drift.
  - `[high]` `[patch]` steward `test_fresh_clone_class_path.py` made the same directory twice once the playbook and the matrix both lived in `spec-pyforge-steward/`; it now passes `exist_ok=True`.
  - `[medium]` `[patch]` live pointers the rewrite rule missed were fixed: paths split across lines, relative `spec-archive/` links, marshal `index.md` rows in the wrong station, a layout listing.
  - `[medium]` `[patch]` two more live companions were carried: steward `failure-modes.md` and `cluster-bringup-facts.md`. The atlas kedro audit report and VS Code decision are records and stay archived.
  - `[low]` `[patch]` the carried spine is the pap host spine, not the canopy spine; the claims that moved text is unchanged are corrected in the Dream entry.
  - `[low]` `[defer]` `scripts/.spec-surface-baseline.json` still holds entries for Specs no longer discovered. A scoped stamp cannot drop a vanished Spec, and a bare stamp is forbidden. The verdict ignores them.
  - Station specifics: `spec-archive/` links in `specs/README.md`, `retros/README.md`, `DESIGN.md` and the deferred-work-ledger preamble name the archive path; the README tree no longer lists `spec-upstream-discovery/`; two closed deferred entries' `verified:` citations name the carried `catalog-sources.md`.

## Auto Run Result

Status: done

Summary: atlas's 10 absorbed Spec folders and `spec-archive/` (29 files) moved to the archive home; `catalog-sources.md` carried into `spec-pyforge-atlas/`. No folder under the station `specs/` reads `status: absorbed`; spec-surface, chain-sprawl, ad-citation and governance-currency exit 0.
