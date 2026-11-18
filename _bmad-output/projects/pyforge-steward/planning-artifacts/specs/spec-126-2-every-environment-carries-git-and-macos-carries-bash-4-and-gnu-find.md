---
title: '126.2: Every environment carries git, and macOS carries bash 4 and GNU find'
type: 'fix'
created: '2026-11-18'
status: 'ready-for-dev'
story: 126-2-every-environment-carries-git-and-macos-carries-bash-4-and-gnu-find
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - 'pixi.toml'
  - 'pixi.lock'
  - 'environment.yaml'
  - 'docs/reference/library-llms-full.md'
  - 'docs/reference/environments.md'
  - 'docs/how-to/pixi-tasks.md'
  - 'docs/map.yaml'
  - 'src/shared/packages/pyforge-steward/tests/**'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** No station environment carries `git`, so it resolves to pixi's global trampoline, which aborts on a non-UTF-8 argument; stock macOS ships bash 3.2 and BSD find, so 40 steward tests skip and a touched-scope preflight cannot cut its lane set.

**Approach:** `git` joins every environment on every platform, `bash` and `findutils` join them on osx-arm64, the lock is re-solved without moving an unrelated pin, and the derived surfaces are regenerated.

Ledger key: `126-2-every-environment-carries-git-and-macos-carries-bash-4-and-gnu-find`.

### Living CAP citations

- spec-pyforge-steward CAP-175 and CAP-5 (realized, no text change); FR-49 ← CAP-175; no AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Close the deferred-work row this story names with the commit that resolves it.

**Never:**
- Never weaken an assertion that holds on Linux, hand-edit a compiled skill, a `SPEC.md`, a generated page or `sprint-status-ledger.yaml`.

## Acceptance Criteria

**Given** no station environment carries `git`, so it resolves to pixi's global trampoline, which aborts on a non-UTF-8 argument; stock macOS ships bash 3.2 and BSD find, so 40 steward tests skip and a touched-scope preflight cannot cut its lane set
**When** `git` joins every environment on every platform, `bash` and `findutils` join them on osx-arm64, the lock is re-solved without moving an unrelated pin, and the derived surfaces are regenerated
**Then** inside any `pixi run` on macOS `git`, `bash` and `find` resolve inside the environment, the git-argument, GNU-find and bash-4 probes pass, and only tests that need a file name APFS refuses still skip
**And** `DW-steward-125-1-3` and the bash 4 half of `DW-steward-125-1-2` reads resolved in its ledger with the commit that closed it

- **AC1 — The story's own check passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-test && pixi run --frozen -e pyforge-steward pyforge-steward-live-test && pixi run --frozen -e pyforge-guild llms-full-check
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-175 and CAP-5 (realized, no text change); FR-49 ← CAP-175; no AD moves.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-11-18 entry; operator ruling of 2026-11-18: "THIS MACHINE WILL BE A FIRST CLASS DEVELOPMENT HOST -- JUST FIX ALL THE DEFERRED ROW ITEMS NOW.. AND NOT LEAVE ANYTHING FOR LATER", "JUST USE ctranslate2 and remove the other one", "we should continue to support manticore and antigravity", "we still want to do everything in this session as one PR".
- Epic: Epic 126, minted with this story.
- Ledger key: `126-2-every-environment-carries-git-and-macos-carries-bash-4-and-gnu-find` (`backlog`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."126"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-18: minted from the station Dream's 2026-11-18 entry and the operator's rulings of the same date.
