---
title: "87.11: The build skills and recovery recipes preserve before they revert or rebuild"
type: 'feature'
created: '2026-10-04'
status: 'done'
baseline_revision: 'db08e46a974ea2d59c84005242bfc7a545b69ba9'
review_loop_iteration: 0
followup_review_recommended: false
flag:
  key: pyforge.marshal.preserve_refs
  provider: openfeature-file
  default: {production: off, staging: off, dev: off}
  scope: global
  fallback: "the persistent fact's command meets the disabled `marshal preserve` verb, which refuses with a flag-off message; the skill records that and proceeds as today"
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04-review.md
  - _bmad/custom/bmad-build-auto.toml
  - .claude/skills/bmad-build-auto/step-04-review.md
  - .claude/skills/bmad-build/step-04-review.md
  - .claude/skills/bmad-build/step-05-present.md
  - .claude/skills/bmad-loop-resolve/SKILL.md
  - src/shared/packages/pyforge-core/src/pyforge/core/landing_evidence.py
  - scripts/bmad_loop_baseline_drift_check.py
  - docs/how-to/pixi-tasks.md
  - docs/how-to/troubleshoot-bmad-agent-loops.md
  - .claude/memory/reference/bmad-loop-escalation-and-landing-traps.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The build skills discard attempts.
- `bmad-build` reverts on `intent_gap` and `bad_spec` with no patch (`.claude/skills/bmad-build/step-04-review.md:63-64`).
- `bmad-build-auto` keeps an unnamed patch on `intent_gap` and reverts on `bad_spec` (`.claude/skills/bmad-build-auto/step-04-review.md:71-72`).
- The hand recovery recipe for rebuilding a stranded story as `land/<station>-<epic>-<seq>` never keeps its source (`landing_evidence.py:172-181`, the baseline-drift remedy text, `docs/how-to/pixi-tasks.md:64`).
- The troubleshooting doc (`:38`) and team memory advise `--restore-patch` on re-arm, while the resolve skill refuses it for worktree-isolation runs (`bmad-loop-resolve/SKILL.md:200-206`).

**Approach:**
- **Build skills.** Deliver the rule as installer-safe persistent facts, never by editing an installer-owned step file: in `_bmad/custom/bmad-build-auto.toml` and a new `_bmad/custom/bmad-build.toml`. Before any `intent_gap` or `bad_spec` revert, the session runs `marshal preserve tag --producer build --story <slug> <N.M> --from .` and cites the tag in the Review Triage Log. The tag is local. `bmad-build` never auto-pushes (`step-05-present.md:9`), and under dispatch the supervisor pushes (Story 87.5), so a governed session never pushes a preserve itself.
- **Recovery recipe.** Step 1 of the recipe becomes "preserve the source (`--producer hand`) before cutting `land/…`". This changes the convention text in `landing_evidence.py`, the baseline-drift remedy and the pixi-tasks doc.
- **Docs and memory.** The troubleshooting doc says `--restore-patch` is refused for worktree-isolation runs. The team-memory reference is corrected through `scribe capture`, never by hand.

Ledger key: `87-11-the-build-skills-and-recovery-recipes-preserve-before-they-revert-or-rebuild`.
Type / Effort / Deps: feature / S / S-87.3.

### Living CAP citations

- `spec-pyforge-marshal` CAP-287 (FR-234, AD-81). Flag `pyforge.marshal.preserve_refs`: the facts call the flag-gated verb.

## Acceptance Criteria

- Given the rendered `bmad-build-auto` and `bmad-build` skills When `render_skill.py` resolves their customization Then the persistent facts say: before any `intent_gap` or `bad_spec` revert, run `marshal preserve tag --producer build --story <slug> <N.M> --from .`, cite the tag in the triage log, and leave the push to the dispatch supervisor or the operator.
- Given the installed step files When the story's diff is read Then no file under `.claude/skills/bmad-build*/` changed.
- Given the recovery-landing convention in `landing_evidence.py`, the baseline-drift remedy text and `docs/how-to/pixi-tasks.md` When they are read Then step 1 is "preserve the source (`--producer hand`) before cutting `land/…`"; `landing_evidence`'s parse behaviour is unchanged.
- Given `docs/how-to/troubleshoot-bmad-agent-loops.md` When it is read Then it states that `--restore-patch` is refused for worktree-isolation runs, matching the resolve skill; the team-memory reference is corrected by a `scribe capture` entry.
- Given the flag off When the fact's command runs Then it reports the verb disabled and the session proceeds; a test pins both states of the verb's response.
- `governance-currency`, the instruction-parity meta-test and `render_skill.py` stay green.

## Boundaries & Constraints

**Always:** Customization through `_bmad/custom/*.toml` only. A fact names one command and one citation.

**Never:** Never edit an installer-owned skill file. Never make a session push a preserve. Never hand-edit a `.claude/memory/` file.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` CAP-287 (FR-234, AD-81).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (preserved-work refs) entry.
Research: drafts' Story 87.11; review mode table (the build skills write a local tag; the supervisor or the operator pushes).
Ledger key: `87-11-the-build-skills-and-recovery-recipes-preserve-before-they-revert-or-rebuild`.
Ledger status at mint: `backlog`.
Deps: S-87.3.
Minted 2026-10-04 under the operator's ruling of the same day.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- `PYTHONPATH="$PWD/_bmad/scripts:$PYTHONPATH" uv run _bmad/scripts/resolve_customization.py --skill .claude/skills/bmad-build-auto --project-root . --key workflow` — expected: the new fact is present (and the same for `bmad-build`).
- `pixi run --frozen -e pyforge-guild governance-currency` — expected: exit 0.
- The two-state flag test: `src/shared/packages/pyforge-marshal/tests/unit/test_preserve_cli.py` (the verb's disabled response).

## Spec Change Log

- No change yet.

## Review Triage Log

- No review has run yet.
