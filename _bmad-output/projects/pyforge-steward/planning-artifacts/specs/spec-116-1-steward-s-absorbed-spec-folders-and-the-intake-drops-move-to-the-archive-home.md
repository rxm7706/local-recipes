---
title: "116.1: Steward's absorbed Spec folders and the intake drops move to the archive home"
type: 'chore'
created: '2026-10-27'
status: 'in-progress'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
baseline_revision: '9dd0a8f1f9'
context:
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - docs/dreams/one-chain-per-station.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - docs/governance/chain-sprawl-baseline.json
  - docs/foundry/capability-ledger.yaml
deferred: []
---

<intent-contract>

## Intent

**Problem:** spec-one-chain-per-station:CAP-11 (operator ruling 2026-09-29; CHAIN-STANDARD §11) sends everything the
fleet retires to `archive/<original path>`. Its order is: the archived Dreams first (PR #2328, 2026-10-26), then the
absorbed and archived Spec folders, each with its memlog and every companion. At `9dd0a8f1f9` (2026-10-27), 35 steward
folders still read `status: absorbed` under `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/`: `spec-asgi-multiplexer-monolith`, `spec-bmad-eval-quality`, `spec-bmad-method-core-upgrade`, `spec-bmad-module-provisioning`, `spec-bmad-suite-channel-product`, `spec-bmad-suite-install-class-wiring`, `spec-bmad-suite-lifecycle`, `spec-bmad-suite-metapackage`, `spec-build-league-scorecard`, `spec-db-gpt-django-plugin`, `spec-developer-machine-bootstrap`, `spec-enterprise-airgap`, `spec-enterprise-multi-agent-orchestration`, `spec-intelligence-hub`, `spec-jira-github-projects-sync`, `spec-langflow-django-plugin`, `spec-local-ocp-hybrid-environment`, `spec-mcp-era-isolation`, `spec-mcp-factory-stdio-translator`, `spec-mcp-host-real-station-tools`, `spec-multi-repo-workspaces`, `spec-ocp-as-a-portability-profile`, `spec-platform-datastores-consumed-not-self-hosted`, `spec-platform-dev-boots-local`, `spec-platform-fifteen-factors`, `spec-platform-image-one-pixi-env`, `spec-platform-object-storage-kind`, `spec-python-agent-platform`, `spec-scratch-worktree-lifecycle`, `spec-secure-live-dashboards`, `spec-self-hosted-bmad-marketplace`, `spec-suite-scaffold-and-mybmad-sidecar`, `spec-unified-container`, `spec-vocabulary-one-name-one-job`, `spec-work-passports-dated-extracts`.

**Approach:**
- **Carry the live companions first (operator ruling 2026-10-27).** `spec-bmad-suite-channel-product/install-matrix.md`, `spec-bmad-suite-lifecycle/adoption-register.md`, `spec-bmad-suite-lifecycle/release-cadence.md`, `spec-bmad-suite-install-class-wiring/install-class-playbook.md`, `spec-python-agent-platform/ARCHITECTURE-SPINE.md`, `spec-build-league-scorecard/measure-catalog.md`, `spec-intelligence-hub/vocabulary-map.md` are not records: a program, test or workflow opens each, or an instruction surface names it as the current home. Each moves with `git mv` to `specs/spec-pyforge-steward/<same name>`, and its readers follow it there. The absorbed folder's memlog gains an event naming where the companion went, before the folder moves.
- **Then the move.** Each of the 35 folders moves with `git mv` to `archive/<original path>`, with its pointer `SPEC.md`,
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
- **Also in this story.** `docs/intake/estate-refresh/` and `docs/intake/ci-pause-control-plane/` move to `archive/docs/intake/` (both routed, their appends landed: steward Epics 100 and 99), so `docs/intake/` holds only its README; `docs/dreams/archive/pyforge-unifying-strategy-2026-08-23-topology.md` (steward Story 43.1's split-off snapshot) moves to `archive/docs/dreams/archive/`.

Ledger key: `116-1-steward-s-absorbed-spec-folders-and-the-intake-drops-move-to-the-archive-home`.
Type / Effort / Deps: chore / M / —.

### Living CAP citations

- spec-one-chain-per-station:CAP-11: the Guild's. Steward mints no CAP and no FR, in the relay shape of doctor
  Epic 36, marshal Epic 75, herald Epic 33 and the 2026-10-26 mop. See CHAIN-STANDARD §11.
- `spec-feature-flag-governance` Q1: a `chore` needs no flag.
- Siblings, the other seven station stories of the 2026-10-27 one-PR close-out: atlas 45.1, doctor 54.1, herald 49.1,
  marshal 112.1, mason 36.1, scribe 30.1, steward 116.1, warden 24.1.

## Acceptance Criteria

- Given the 35 folders named above, when `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/` is listed, then none of them is there, and each sits at `archive/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/<same name>/` with the same files, less any carried companion.
- Given a moved file, when it is diffed against its pre-move content, then it is byte-identical, apart from the one memlog event appended before the move.
- Given every live pointer that named a moved path, when the repo is grepped, then it names the new path. `governance-currency`, `spec-surface`, `ad-citation`, `chain-sprawl`, `dream-chain` and `detectors-ci` all exit 0.
- Given the station suite, when `pixi run --frozen -e pyforge-steward pyforge-steward-test` runs, then it passes.

## Tasks

1. Carry each live companion into `specs/spec-pyforge-steward/`, with a memlog event on the absorbed folder first.
2. `git mv` the 35 folders to `archive/<original path>`.
3. Re-point every live pointer, and prune `docs/governance/chain-sprawl-baseline.json`.
4. Append a memlog event to `spec-pyforge-steward` (and to each co-governor the detector names), script-render the
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
| live companion | a program, test or workflow opens it | carried to `specs/spec-pyforge-steward/`; its readers repointed | — |
| dated record naming the old path | memlog, story spec, PRD prose | left as written | — |
| capability ledger row | `source:` names a moved Spec | names the archive path | — |

</intent-contract>

## Binding

- Parent capability: spec-one-chain-per-station:CAP-11 (Guild relay; no steward CAP or FR).
- Dream: `docs/dreams/one-chain-per-station.md`, § *2026-10-27 — The absorbed Spec folders and the last side archives leave the live tree*.
- Ledger key: `116-1-steward-s-absorbed-spec-folders-and-the-intake-drops-move-to-the-archive-home`.
- Deps: none.
- Flag: none. This is a `chore` (`spec-feature-flag-governance` Q1).

## Verification

**Commands:**
- `pixi run -e pyforge-guild chain-sprawl-check`: expect exit 0.
- `pixi run -e pyforge-guild spec-surface-check`: expect exit 0 after the scoped stamps.
- `pixi run --frozen -e pyforge-steward pyforge-steward-test`: expect a pass.

**Manual checks:**
- `grep -l '^status: absorbed' _bmad-output/projects/pyforge-steward/planning-artifacts/specs/*/SPEC.md`: expect no output.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).

## Auto Run Result

Status: in-progress
