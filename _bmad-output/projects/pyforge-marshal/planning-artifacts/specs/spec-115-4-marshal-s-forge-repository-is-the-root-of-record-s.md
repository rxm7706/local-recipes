---
title: "115.4: Marshal's forge repository is the root of record's"
type: 'fix'
created: '2026-11-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: medium
story: '115.4'
spec: pyforge-marshal
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/forge_root.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_no_hardcoded_forge_repo.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_forge_root.py
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/dreams/pyforge-unifying-strategy.md
  - src/shared/packages/pyforge-core/src/pyforge/core/cutover_root.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/deploy.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/watch.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py
warnings: []
deferred: []
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-117.2); S-115.1 and S-115.2 sit earlier in this epic.
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** Operator ruling 2 of 2026-11-10: `pyforge.cutover_root` means the writer lock and the root of record, and marshal's default forge remote is one of its three consumers. At `82a2b18828` the slug is a literal in four modules (`_FORGE_REPO` at `dispatch_land.py:72`, `cli/deploy.py:408`, `cli/land.py:166`; `gh pr list --repo` at `cli/watch.py:661`), and marshal imports only `resolve_flags_path` from `pyforge.core.cutover_root`.

**Approach:** A fix under CAP-208 (its amendment is in the memlog of 2026-11-10); no CAP minted. It consumes core-kit Story 117.2 (same project): `root_of_record(path=None) -> RootOfRecord(root, forge_slug, source)`, raising the existing `CutoverRootError` on a malformed tree or unknown variant and answering `source='default'` when no tree is in reach. `adapters/forge_root.py` is the one consumer (`core/` is pure by AD-4): `forge_repo(flags_path=None) -> str` returns `root_of_record(flags_path).forge_slug` and turns `CutoverRootError` into the forge port's own `ForgeCommandError`, so each site reports through the code it already uses for a forge it cannot reach. The read moves inside each site's existing handling: `dispatch_land.py:1601` into the `try` around `find_open_pr` (MRS-DISP-018); `cli/land.py:688` likewise (MRS-DEPLOY-014); `cli/land.py:805` and `cli/deploy.py:2904` ahead of `_evaluate_hygiene` with a MRS-DEPLOY-014 finding and an early emit; `cli/watch.py:661`'s `list_prs` as `ProbeError('gh pr list', ...)` (MRS-WATCH-004). It is read at each use, never cached at import. Tests run in a temp directory with no flag tree, so they get the default.

Ledger key: `115-4-marshal-s-forge-repository-is-the-root-of-record-s`. Type / Effort / Deps: fix / M / S-115.1, S-115.2, S-117.2.

## Boundaries & Constraints

**Always:**
- The slug is read at each use from `root_of_record()`; the forge slug table is core's constant.
- A malformed tree reports through each site's existing forge-failure code; `core/findings.py` does not move.

**Never:**
- No kill switch (operator ruling of 2026-11-10): the behaviour is governed by `pyforge.cutover_root` itself, whose shipped default keeps today's slug.
- Never switch a loop home's git remotes (spec-python-foundry-cutover:CAP-8's clause stays with the control plane).
- Never hold a repository slug in marshal source, code or comment.

## Acceptance Criteria

- **AC1 — No repository slug remains in marshal source, code or comment.**

  ```bash
  ! git grep -nE 'rxm7706/(local-recipes|python-foundry)' -- src/shared/packages/pyforge-marshal/src
  ```

  Expected: exit 0 (at `82a2b18828`: 5 hits).

- **AC2 — The guard fails on a planted slug literal, and the seam consumer answers each tree: `local-recipes` gives `--repo rxm7706/local-recipes`, `foundry` gives the seam's foundry slug, no tree gives the default.**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/meta/test_no_hardcoded_forge_repo.py src/shared/packages/pyforge-marshal/tests/unit/test_forge_root.py -q
  ```

  Expected: exit 0.

- **AC3 — A malformed tree surfaces through each site's existing forge-failure code, and no code is added: dispatch land MRS-DISP-018 (refused), land and deploy batch-pr MRS-DEPLOY-014, watch MRS-WATCH-004 (warn).**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_forge_root.py -q -k malformed && git diff --quiet origin/main -- src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py
  ```

  Expected: exit 0; 4 selected.

- **AC4 — The existing landing, deploy, watch and forge tests pass unchanged.**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_land.py src/shared/packages/pyforge-marshal/tests/unit/test_deploy.py src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_landing.py src/shared/packages/pyforge-marshal/tests/unit/test_watch.py src/shared/packages/pyforge-marshal/tests/unit/test_forge_gh.py src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py -q
  ```

  Expected: exit 0.

- **AC5 — Lint and types hold.**

  ```bash
  pixi run -e pyforge-guild lint-types
  ```

  Expected: exit 0.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` CAP-208 (amended 2026-11-10); consumer of spec-pyforge-core:CAP-13 and spec-python-foundry-cutover:CAP-8. FR-59 body sentence (written by Story 114.1).

- Epic: Epic 115 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 115.4: Marshal's forge repository is the root of record's`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The Spec says what marshal is, and its roots come from one place.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda.

## Notes

- Same-project dependency: Story 117.2 (core-kit's, in this station's `epics.md`) provides `root_of_record()`.
- Cross-station: needed by steward:S-121.4 (the chain-write guard reads the same root of record).
- Deferred rows (written by Story 116.5): DW-marshal-115-4-1 (the station-package directory, B's to settle), DW-marshal-115-4-2 (three shipped capabilities without a kill switch: the inventory debt), DW-marshal-115-4-3 (the remote check DW-FU-4-4-2 narrows to).
- Last of Epic 115 because it shares files with Stories 115.1 and 115.2. `contract.md`'s flag row is Story 114.3's.

## Spec Change Log

- 2026-11-10: minted at `blocked` (forward dependency: until S-115.1, S-115.2 and S-117.2 are done) by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10) and the memlog entries of `spec-pyforge-marshal` came first; `SPEC.md` is rendered by Story 114.1.
