---
title: '21.1: `AGENTS.md` opens with what this repository is'
type: 'docs'
created: '2026-09-25'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `AGENTS.md` opens with the recipe factory and carries ~500 lines of notes, while the estate is two roots under a writer lock.

**Approach:** Through `bmad-project-context` for the managed block and by hand outside it: open with A's identity, the A/B roles, modes and writer lock; add the behavioural core; move each removed note to a named pointer target first.

## Boundaries & Constraints

**Always:**
- Use the worker's real status vocabulary (`draft → ready-for-dev → in-progress → in-review → done`).
- State that A is never archived (operator 2026-09-25).
- `CLAUDE.md` keeps the bare `@AGENTS.md` import.
- Co-governor reconcile before landing: a memlog entry on every Spec `spec-surface-check` names, `git add`, then `python scripts/spec_surface_check.py --write-baseline --spec <project>/<spec>` per named Spec, re-run the check and read its exit code; never a bare stamp.

**Never:**
- Do not merge PRs #1563 / #1564 / #1576; port their payload by hand where this story names it.
- Do not flip any Epic 44 `blocked` key or `pyforge.cutover_root`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.
- Do not edit `rxm7706/python-foundry`.
- Do not hand-edit the managed `bmad:context` block.
- Do not delete a pitfall without a pointer target that exists.
- Do not edit the per-tool addenda (`GEMINI.md`, `.github/copilot-instructions.md`, `.cursor/rules/*.mdc`, `.vscode/settings.json`) except where a moved section changes a pointer they carry.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| removed incident note | `git diff origin/main -- AGENTS.md CLAUDE.md`, one row per removed bullet | a target under `.claude/memory/**` or `docs/reference/**` holds the bullet's anchor; the run result records the removed → target map | fail loud |
| parity meta-test | scribe suite | green | fail loud |

</intent-contract>

## Binding

Parent Spec capability: `spec-python-foundry-cutover fnd:CAP-15`.
Dream: `docs/dreams/pyforge-unifying-strategy.md` § *Where next* → *Consolidation — 2026-09-25*.
Ledger key: `21-1-agents-md-opens-with-what-this-repository-is`.
Ledger status at mint: `backlog`.
Minted 2026-09-25 from `epics.md` so `marshal factory dispatch` can resolve `spec-21-1-agents-md-opens-with-what-this-repository-is.md`.

## Epic excerpt

**Type:** docs • **Effort:** M • **Deps:** — • **FR/AD:** fnd:CAP-15 • spec-pyforge-scribe CAP-27 • cross-station: steward index 67.7 flips `done` when this closes; reference payload PR #1563 (branch `docs/agents-pyforge-bmad`)
**Surface:** `AGENTS.md` (managed block through `bmad-project-context`; sections outside it by hand), `CLAUDE.md` (pointer + Claude-only notes), the pointer targets each removed note moves to (`.claude/memory/`, `docs/reference/`), the per-tool addenda `GEMINI.md`, `.github/copilot-instructions.md`, `.cursor/rules/*.mdc` and `.vscode/settings.json` only where a moved section changes a pointer they carry, `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py` only if a parity rule must follow a moved section.
**Given** `AGENTS.md` opens with the recipe factory and carries ~500 lines of accumulated notes, while the estate is two roots under a writer lock
**When** this story lands
**Then** the file opens with A's identity, the A/B roles, the modes (never `move`) and the writer lock, stating that A is never archived; the behavioural core adds heal-the-tissue, state over action, read-only harness ledgers and implement / review separation, using the worker's real status vocabulary (`draft → ready-for-dev → in-progress → in-review → done`); every incident note removed from the file has a named pointer target that exists
**And** the story's run result records the removed → target map (one row per removed note, the target file and anchor), and a one-shot check at landing confirms every target exists; `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` green; `governance-currency` (in `detectors-ci`) green; `CLAUDE.md` still imports `@AGENTS.md` bare; co-governor reconcile: a memlog entry on every Spec `spec-surface-check` names, then a scoped stamp per Spec, never a bare `--write-baseline`

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- The run result's removed → target map: one row per bullet removed from `AGENTS.md` / `CLAUDE.md`, and every target file exists and carries the bullet's anchor (date or incident phrase).
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0 (`governance-currency`).

## Review Triage Log

Implemented 2026-09-26 in an interactive session, through `bmad-project-context` (refresh) for the managed block. The operator approved the block and ledger (lossless option) before any write. PR #1563's draft was a reference only; it was never merged.

**Operator decisions during the run:**
- `CLAUDE.md` stays as the import plus Claude-only notes. It is not retired: Claude Code 2.1.283 already runs `instructionFiles=claude-md-and-agents-md` (verified with `scripts/claude_instruction_mode_check.py`), so both files load every session and the `@AGENTS.md` import is the floor for older runtimes and Bedrock / Vertex.
- `CLAUDE.md` and the three Cursor pointer files (`.cursorrules`, `.cursor/rules/specs.mdc`, `.cursor/rules/trunk-worktree-pr.mdc`) join `spec-pyforge-scribe`'s surface. Before this they were allowlisted and ungoverned, while `GEMINI.md` and `.github/copilot-instructions.md` were scribe's. The change is in memlog entry 111 and a scripted `SPEC.md` render the operator approved. `.cursor/**` stays allowlisted for the files other stations write: the generated `bmad-build*.mdc` adapters, `hooks.json`, `environment.json` and `pyforge-fleet-drain/`.

**Constraints found before writing:**
- Doctor's `bmad-drift` `check_spec_indexed` needs every `docs/specs/*.md` filename in `CLAUDE.md`, so a five-row index stays there.
- Marshal's seed manifest anchors on `## The tiers`, `## Portability contract` and `## Dream-first workflow` in `AGENTS.md`, and on `### Spec-driven, framework-neutral layout` and `### Multi-Project Pattern` in `CLAUDE.md`. All five headings are kept.
- Inbound links name `CLAUDE.md` sections. `CLAUDE.md` § *Where moved sections went* and the map at the top of the notes file resolve them in two hops: `docs/how-to/feedstock-platform-expansion.md`, `.claude/skills/conda-forge-expert/guides/feedstock-platform-expansion.md`, `docs/reference/github-workflows.md`, `.github/workflows/detectors.yml`, `docs/how-to/driving-a-pyforge-station-backlog.md`, `README.md`, the seven station `specs/README.md` files, `_bmad/scripts/resolve_config.py`, and comments in steward `deploy.py` and marshal `core/landing.py`. None was edited, which keeps station code out of this story.
- The two Cursor pointers this story made stale or contradictory were fixed:
  - `.cursorrules` told Cursor to read `CLAUDE.md` for detail it no longer carries.
  - `specs.mdc` offered the planning chain as an alternative to `bmad-spec`.

**Adversarial review:** a separate read-only reviewer (general-purpose subagent) reviewed the staged diff against this contract. It found 0 HIGH, 5 MEDIUM and 9 LOW. Dispositions:

1. MEDIUM, fixed. The orientation misstated Epic 44: 44.4–44.6 are parked and never dispatched, and 44.10 is retired. Its "A is the oracle until the flip" disagreed with the per-capability oracle. It now follows the Spec and the dossier.
2. MEDIUM, fixed. The writer-lock and modes lines are now the first two Policy bullets, and the preamble shrank to one line, so the file opens with A's identity.
3. MEDIUM, fixed. Principle 7 now names a harness run's own ledgers. Dream-first item 5 writes the ledger through the Tier-3 feed and `sprint-ledger-sync`, not by hand.
4. MEDIUM, fixed. Dream-first item 6 now matches the pre-shell hook: from a worktree, never switch; use `BMAD_ACTIVE_PROJECT` and physical paths. `bmad-switch` is for the primary checkout only.
5. MEDIUM, fixed. Always-on rules the move had put out of view are back:
   - in the block: Rule 1's CFE-tree trigger and "the skill wins over a conflicting story", and Rule 2's gating (not deferrable, semver bump, a no-findings retro still writes its CHANGELOG entry);
   - in Dream-first item 6: "know which project before a BMAD write";
   - in § *Read on trigger*: the three-place rule, and `detectors` / `fleet-picture` (paste stdout verbatim).
6. LOW, fixed. `bmad-drift-check --specs` is now `python scripts/bmad_drift_check.py --specs`.
7. LOW, fixed. The `-e local-recipes` line now reads as the exception to the Guild-env rule.
8. LOW, fixed. Removed the date narration in the block, and the judgement trigger "or when one looks arbitrary".
9. LOW, fixed. The notes-file intro now states the two removed home-directory citations.
10. LOW, fixed. The Multi-Project pointers name where the marker-and-symlink mechanism lives: the notes file, not `PROJECTS.md`.
11. LOW, logged above. Inbound links resolve in two hops through the stub.
12. LOW, fixed. "only after its text lands".
13. LOW, partly fixed:
    - Dream-first item 2 now points at principle 6 for the story vocabulary.
    - Principle 7 points at § Policy for the write path.
    - `CLAUDE.md`'s map table moved into the notes file.
    - The three notes-file pointers stay; each serves a different trigger.
14. LOW:
    - This spec is now `done`, and the map is below.
    - The parity test's "five principles" comment describes the state before Story 19.3, so it is accurate history and is left alone.
    - Size: `AGENTS.md` went 516 → 489 lines. Only incident narration moved out; every rule stays, which is the lossless option the operator chose. The block's pitfall evidence tags stay as pitfall evidence.
    - The reviewer also noted that marshal's slow `test_local_recipes_empty_plan` already fails at `HEAD`, because neither file has seed region markers. This change does not cause it.

**Found while fixing:** `AGENTS.md` claimed that `detectors-ci` runs `governance-currency`. It does not: neither `scripts/detectors.py`, any workflow, nor `pr-preflight` runs it. The line now says to run it by hand.

**Follow-ups, for the operator:**
- Wire `governance-currency` into `detectors-ci`, so the documented gate actually runs.
- Point the SKF export at `AGENTS.md` only. `skf-export-skill` writes its managed block into every context file, so both loaded files carry the same 54 lines.

## Outcome

Verified 2026-09-26:
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test`: 398 passed, 11 skipped.
- The instruction-surface pins, run against the final files, pass (73 passed): scribe parity, navigation-owner and guild-env; CFE retired-skill-ids; steward adoption-register; herald's two routing guards.
- These exit 0: `governance-currency`, `docs-map-hygiene-check`, `docs-currency-check` and `bmad-drift-check`. `bmad-drift-check` reports no `spec-unindexed` finding.
- The one-shot landing check: 46 rows; every target exists and carries its anchor.

### Removed → target map

| From | Removed note | Target | Anchor | OK |
|---|---|---|---|---|
| AGENTS.md § Team memory | 2026-09-19 operator-asks finding | `docs/reference/agent-instruction-notes.md` | six such asks and four older leftovers | yes |
| AGENTS.md § Pre-PR item 6 | PR #1507 live incident | `docs/reference/agent-instruction-notes.md` | Live incident (PR #1507, 2026-09-19) | yes |
| AGENTS.md § Dream-first item 5 | 2026-09-12 Story-before-code incident | `docs/reference/agent-instruction-notes.md` | `spec-library-catalog-manifest-sync` CAP-1/CAP-2 were hand-i | yes |
| AGENTS.md § Dream-driven: where work starts | whole section | `docs/reference/agent-instruction-notes.md` | Dream-driven: where work starts | yes |
| AGENTS.md § Dream-driven: where work starts | its rules | `AGENTS.md` | the planning chain (`bmad-product-brief` → `bmad-prd` | yes |
| AGENTS.md § Dream-first item 6 | writer lock | `AGENTS.md` | (the writer lock) | yes |
| AGENTS.md § Dream-first item 6 | modes, never move | `AGENTS.md` | never `move`, never a package fold | yes |
| AGENTS.md § Dream-first item 6 | campaign verbs | `AGENTS.md` | Launch the Foundry, Adopt Frames | yes |
| AGENTS.md § Claude Design ↔ repo bridge | whole section | `docs/how-to/presentation-deck.md` | ### The MCP bridge | yes |
| AGENTS.md § Claude Design ↔ repo bridge | whole section (verbatim) | `docs/reference/agent-instruction-notes.md` | Claude Design ↔ repo bridge (decks, prototypes) | yes |
| AGENTS.md § Library catalog | whole section (verbatim) | `docs/reference/agent-instruction-notes.md` | Library catalog (what's available to import/run) | yes |
| AGENTS.md § Library catalog | its rules | `AGENTS.md` | Recipe-factory work is the one exception to the line above | yes |
| AGENTS.md § How each tool discovers this | whole section (verbatim) | `docs/reference/agent-instruction-notes.md` | How each tool discovers this | yes |
| AGENTS.md § Keeping the BMAD planning docs accurate | 2026-09-07 correction | `docs/reference/agent-instruction-notes.md` | Corrected 2026-09-07 by the CAP-6 | yes |
| AGENTS.md § Pre-PR item 2 | pointer to CLAUDE.md PR CI gates rule 4 | `docs/reference/agent-instruction-notes.md` | Before pushing ANY non-recipe branch | yes |
| AGENTS.md § Trunk, worktrees, PRs | bmad-switch / gh pr create / merge duplicate | `AGENTS.md` | Never run `scripts/bmad-switch` from a parallel agent | yes |
| AGENTS.md § Pre-PR item 7 | environment.yaml / merge-form duplicates | `AGENTS.md` | pixi project export conda-environment -e build > environment | yes |
| CLAUDE.md § Project Overview | whole section | `docs/reference/agent-instruction-notes.md` | AI-assisted, semi-autonomous packaging factory | yes |
| CLAUDE.md § Critical Rule — PR CI gates | rules 1–4 | `docs/reference/agent-instruction-notes.md` | Critical Rule — PR CI gates (ALWAYS-ON | yes |
| CLAUDE.md § Critical Rule — PR CI gates | 2026-09-14 billing-outage incident | `docs/reference/agent-instruction-notes.md` | Found live 2026-09-14 | yes |
| CLAUDE.md § Critical Rule — PR CI gates | PR #1355 incident | `docs/reference/agent-instruction-notes.md` | Added 2026-09-14 after PR #1355 | yes |
| CLAUDE.md § Reading a detector's result | 2026-09-14 false green | `docs/reference/agent-instruction-notes.md` | This produced a false green on 2026-09-14 | yes |
| CLAUDE.md § Repo surfaces | whole paragraph | `docs/reference/agent-instruction-notes.md` | Repo surfaces beyond `recipes/` | yes |
| CLAUDE.md § Common Commands | whole section | `docs/reference/agent-instruction-notes.md` | Common Commands | yes |
| CLAUDE.md § BMAD Method Documentation | whole section | `docs/reference/agent-instruction-notes.md` | BMAD Method Documentation | yes |
| CLAUDE.md § Multi-Project Pattern | whole section | `docs/reference/agent-instruction-notes.md` | Multi-Project Pattern (this repo hosts multiple BMAD project | yes |
| CLAUDE.md § Multi-Project Pattern | 2026-07-14 near-miss | `docs/reference/agent-instruction-notes.md` | Live near-miss (2026-07-14) | yes |
| CLAUDE.md § Multi-Project Pattern | 2026-07-25 fan-out incident | `docs/reference/agent-instruction-notes.md` | Live incident (2026-07-25, the 11-Spec derivation fan-out) | yes |
| CLAUDE.md § Multi-Project Pattern | its rules | `AGENTS.md` | never switch: set `BMAD_ACTIVE_PROJECT=<slug>` | yes |
| CLAUDE.md § Multi-Project Pattern | six config layers | `_bmad-output/PROJECTS.md` | Config layering | yes |
| CLAUDE.md § Spec-driven layout | story specs durable rule | `AGENTS.md` | **Story specs are durable, not Tier 3.** | yes |
| CLAUDE.md § Spec-driven layout | warden 13-of-31 recovery | `docs/reference/agent-instruction-notes.md` | pyforge-warden lost 13 of 31 story specs | yes |
| CLAUDE.md § Dream-first | duplicate of AGENTS.md | `docs/reference/agent-instruction-notes.md` | Dream-first (MANDATORY, always-on) | yes |
| CLAUDE.md § Keeping BMAD artifacts in sync | whole section | `docs/reference/agent-instruction-notes.md` | Keeping BMAD artifacts in sync with the live repo | yes |
| CLAUDE.md § Keeping BMAD artifacts in sync | when to run | `AGENTS.md` | After every CFE retro or skill MINOR bump | yes |
| CLAUDE.md § Skill Reference | whole section | `docs/reference/agent-instruction-notes.md` | Skill Reference | yes |
| CLAUDE.md § BMAD ↔ conda-forge-expert integration | Rules 1–3 | `docs/reference/agent-instruction-notes.md` | Rule 3 — Planner constraints for conda-forge stories | yes |
| CLAUDE.md § Project Documentation Reference | whole section incl. intake-spec index | `docs/reference/agent-instruction-notes.md` | Intake specs (`docs/specs/` | yes |
| CLAUDE.md § Project Documentation Reference | docs/specs filenames | `CLAUDE.md` | `docs/specs/feedstock-refresh.md` | yes |
| CLAUDE.md § conda-forge-expert v7.0.0 layout | incl. three-place rule | `docs/reference/agent-instruction-notes.md` | Three-place rule for a new CI script | yes |
| CLAUDE.md § Skill Reference / § Project Documentation Reference | 2 home-directory citations (deleted, ground 3) | `docs/reference/agent-instruction-notes.md` | home-directory auto-memory was removed here | yes |
| CLAUDE.md § BMAD ↔ conda-forge-expert integration | Rule 1: the skill wins over a story | `AGENTS.md` | the skill wins and the story records the deviation | yes |
| CLAUDE.md § BMAD ↔ conda-forge-expert integration | Rule 2: the retro gates done | `AGENTS.md` | not deferrable; the effort is not done until it lands | yes |
| CLAUDE.md § conda-forge-expert v7.0.0 layout | three-place rule trigger | `AGENTS.md` | the three-place rule: script, CLI wrapper, pixi task | yes |
| CLAUDE.md § Common Commands | fleet-picture stdout verbatim | `AGENTS.md` | paste `fleet-picture` stdout verbatim | yes |
| CLAUDE.md § Multi-Project Pattern | ask which project at session start | `AGENTS.md` | project it targets (ask, or `scripts/bmad-switch --current` | yes |

46 rows, 0 missing

## Correction (2026-09-26, Story 21.2)

The triage log's "Found while fixing" paragraph, and its first follow-up, are wrong.

- `governance-currency` does run in `detectors-ci`. `detectors-ci` is `scripts/detectors.py --scope repo`, which discovers `scripts/governance_currency_check.py` (`DETECTOR = {"scope": "repo"}`) by its `*_check.py` glob. `pr-preflight` depends on `detectors-ci`, and CI's `detectors` job ran the check on PR #1621.
- The claim came from a subagent's survey and was "confirmed" by a name grep of `scripts/detectors.py`, which cannot see glob discovery.
- Story 21.2 restores a true checklist line, proven with `python scripts/detectors.py --scope repo --list`. The "wire it into `detectors-ci`" follow-up is withdrawn: there was nothing to wire.
