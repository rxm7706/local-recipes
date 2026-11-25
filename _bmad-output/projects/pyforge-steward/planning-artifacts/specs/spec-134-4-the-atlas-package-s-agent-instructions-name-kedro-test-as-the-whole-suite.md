---
title: '134.4: The atlas package''s agent instructions name kedro-test as the whole suite'
type: 'fix'
created: '2026-11-25'
status: 'done'
story: 134-4-the-atlas-package-s-agent-instructions-name-kedro-test-as-the-whole-suite
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-atlas/AGENTS.md'
  - '_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-atlas-review-2026-11-24-2`. `src/shared/packages/pyforge-atlas/AGENTS.md:71`, inside the `bmad:context` block (lines 5 to 102), reads "`pyforge-atlas-test` (the whole suite; `kedro-test` is its alias)". In `pixi.toml`, `[feature.pyforge-atlas.tasks.pyforge-atlas-test]` runs the package half (`-m "not slow and not live_tree"`), `pyforge-atlas-live-test` runs the live-tree half, and `kedro-test` is `depends-on = ["pyforge-atlas-test", "pyforge-atlas-live-test"]`. An agent that follows the file runs half the suite and reports the whole. The documentation story that found it (doctor Story 61.1) left it, because the block is written only by its skill.

**Approach:** Refresh the block with the `bmad-project-context` skill, addressed to the atlas package's `AGENTS.md`, so the line names `kedro-test` as the whole suite, `pyforge-atlas-test` as its package half and `pyforge-atlas-live-test` as its live-tree half. Keep every other fact the block carries that still holds; where the skill's refresh would change another line, check that line against the tree before accepting it. Nothing outside the two markers changes. Close the row in atlas's ledger.

Ledger key: `134-4-the-atlas-package-s-agent-instructions-name-kedro-test-as-the-whole-suite`.

### Living CAP citations

- spec-pyforge-steward CAP-175 (each station's suite has a package half and a live-tree half; realized, no text change); reads `spec-pyforge-scribe:CAP-27` (the instruction surface; no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Write the block through `bmad-project-context`; set `BMAD_ACTIVE_PROJECT=pyforge-atlas` and never run `scripts/bmad-switch` from this worktree.
- After the skill writes, confirm the file it wrote is `src/shared/packages/pyforge-atlas/AGENTS.md` and not the root `AGENTS.md`.
- Append the surface reconcile to the memlog of each Spec that governs the file (`spec-pyforge-atlas` and `spec-pyforge-unifying-strategy`) before the scoped stamps.
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never hand-edit a line between `<!-- bmad:context -->` and `<!-- /bmad:context -->`.
- Never change a pixi task, its name or what it runs.
- Never touch the root `AGENTS.md` in this story.

## Acceptance Criteria

**Given** `DW-atlas-review-2026-11-24-2` reports that the `bmad:context` block of `src/shared/packages/pyforge-atlas/AGENTS.md` calls `pyforge-atlas-test` the whole suite with `kedro-test` its alias, while `pixi.toml` makes `pyforge-atlas-test` the package half and `kedro-test` the task that depends on both halves
**When** the block is refreshed by the `bmad-project-context` skill, never by hand
**Then** the block names `kedro-test` as the whole suite, `pyforge-atlas-test` as its package half and `pyforge-atlas-live-test` as its live-tree half, every line outside the block is byte-identical, and the scribe instruction-surface parity test and `governance-currency` pass
**And** `DW-atlas-review-2026-11-24-2` reads resolved in atlas's ledger

- **AC1 — The old sentence is gone.** Expected: exit 1 (no line matches).

  ```bash
  grep -n -F "pyforge-atlas-test\` (the whole suite" src/shared/packages/pyforge-atlas/AGENTS.md
  ```

- **AC2 — The block names the whole suite and both halves.** Expected: exit 0.

  ```bash
  python3 -c "import pathlib,re,sys; t=pathlib.Path('src/shared/packages/pyforge-atlas/AGENTS.md').read_text(encoding='utf-8'); b=t.split('<!-- bmad:context -->',1)[1].split('<!-- /bmad:context -->',1)[0]; sys.exit(0 if re.search(r'kedro-test\x60 \(the whole suite', b) and 'pyforge-atlas-live-test' in b and 'pyforge-atlas-test' in b else 1)"
  ```

- **AC3 — Nothing outside the block changed.** The lines before the opening marker and after the closing marker equal those of the base of the branch. Expected: exit 0.

  ```bash
  python3 -c "import pathlib,subprocess,sys; p='src/shared/packages/pyforge-atlas/AGENTS.md'; new=pathlib.Path(p).read_text(encoding='utf-8'); old=subprocess.run(['git','show','origin/main:'+p],capture_output=True,text=True,check=True).stdout; cut=lambda t:(t.split('<!-- bmad:context -->',1)[0], t.split('<!-- /bmad:context -->',1)[1]); sys.exit(0 if cut(new)==cut(old) else 1)"
  ```

- **AC4 — The instruction surface holds.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-scribe pyforge-scribe-live-test
  ```

- **AC5 — Every name the file cites resolves.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild governance-currency
  ```

- **AC6 — The row is closed.** Expected: prints 1, exit 0.

  ```bash
  grep -c -E "^  resolution: 2026-[0-9-]+, steward Story 134\.4 " _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-175 (realized, no text change); reads `spec-pyforge-scribe:CAP-27`; no AD moves.
- Dream: `docs/dreams/pyforge-steward.md`, the 2026-11-25 entry (the open rows close, and one verb says whether a machine is ready); operator ruling of 2026-11-25: "fix all these issues / left open items".
- Epic: Epic 134, minted with this story.
- Ledger key: `134-4-the-atlas-package-s-agent-instructions-name-kedro-test-as-the-whole-suite`.
- Deferred-work row: `DW-atlas-review-2026-11-24-2` (atlas's ledger).
- Surface: `marshal-policy.toml` `[epic_surfaces]."134"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry and the operator's ruling of the same date. Not implemented. The surface baseline lists the file under `pyforge-atlas/spec-pyforge-atlas` and `pyforge-steward/spec-pyforge-unifying-strategy`.
- 2026-11-25: reproduced on the tree as it was (main `21087f55c9`): line 71 of the block read "`pyforge-atlas-test` (the whole suite; `kedro-test` is its alias)", while `pixi.toml` makes `pyforge-atlas-test` the package half (`-m "not slow and not live_tree"`), `pyforge-atlas-live-test` the live-tree half and `kedro-test` `depends-on` both.
- 2026-11-25: changed by a `bmad-project-context` refresh addressed to `src/shared/packages/pyforge-atlas/AGENTS.md` (`BMAD_ACTIVE_PROJECT=pyforge-atlas`, no `bmad-switch`; the skill's two resolvers ran through `pixi run --frozen -e pyforge-guild uv run`, because `uv` is not on this machine's PATH). The refresh re-checked every path, pixi task and caveat the block cites and read `git log --diff-filter=DR` since the block's recorded `72f3e3158f` (14 paths, all under `views/`, none cited by the block). Its ledger settled one rewrite on ground 1 (stale, evidence `pixi.toml`): the "Gates and their tests" line now reads "`kedro-test` (the whole suite: `pyforge-atlas-test`, the package half, then `pyforge-atlas-live-test`, the live-tree half)"; every other line is retained unchanged, and the provenance line reads 2026-11-25 against `21087f55c9`. The skill asks for the user's approval of each write; the approval taken is the operator's ruling of 2026-11-25 naming `DW-atlas-review-2026-11-24-2`, which covers this one rewrite, and the refresh proposed no removal, relocation or other rewrite that would need a further one. Diff: 4 lines added, 3 removed, all between the markers.
- 2026-11-25: verified, each from its exit code: AC1 exit 1, AC2 exit 0, AC3 exit 0, AC5 `governance-currency` exit 0 (11 governed documents); the scribe parity module `tests/meta/test_instruction_surface_parity.py` in `-e pyforge-scribe` exit 0 (49 passed); atlas's one test module that reads `AGENTS.md`, `tests/meta/test_skf_skill_and_persona.py`, exit 0 (17 passed).
- 2026-11-25: left open. AC4 as written (the whole `pyforge-scribe-live-test` lane) was not run here: only its parity module was, because the lane uses the one shared PostgreSQL cluster and several agents share this worktree. AC6 is not met: the implementing session was told not to edit a deferred-work ledger, so the `resolved:` / `resolution:` lines and `status: closed` on `DW-atlas-review-2026-11-24-2` are left to the session lead. The surface reconcile (memlog lines on `spec-pyforge-atlas` and `spec-pyforge-unifying-strategy`, then the scoped stamps) is likewise the lead's.
- 2026-11-25: closed. Implemented, independently reviewed against this spec, its findings applied and re-reviewed; the full local `pr-preflight` gates the PR that lands it (branch `open-rows-and-onboarding-2026-11-25`).
