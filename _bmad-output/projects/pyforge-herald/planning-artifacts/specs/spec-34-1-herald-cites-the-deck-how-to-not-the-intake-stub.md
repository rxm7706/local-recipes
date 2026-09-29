---
title: "34.1: Herald cites the deck how-to, not the intake stub"
type: 'chore'
created: '2026-09-29'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - docs/how-to/presentation-deck.md
  - src/shared/packages/pyforge-herald/src/pyforge/herald/deck_pipeline.py
  - .claude/skills/bmad-agent-herald/SKILL.md
  - src/shared/packages/pyforge-herald/tests/meta/test_slides_generator_routing.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-one-chain-per-station:CAP-11` (operator ruling 2026-09-29) retires `docs/specs/`. Its
`presentation-deck.md` is a stub whose body lives at `docs/how-to/presentation-deck.md`; doctor Story 37.1 moves the stub
to `archive/docs/specs/`. Herald's files still cite the stub:
- `deck_pipeline.py` (four comment and docstring citations);
- `scripts/deck_export.py`, `scripts/deck_facts.py` and `scripts/deck_trio.py` (one each);
- three `pixi.toml` task descriptions;
- the AD-2 section of `.claude/skills/bmad-agent-herald/SKILL.md`, which
  `tests/meta/test_slides_generator_routing.py` pins through its `DECK_PIPELINE_SPEC` constant;
- a docstring in `tests/meta/test_deck_registry_sections.py`, and README fixture text in `tests/unit/test_deck_pipeline.py`;
- 15 `presentations/*/README.md` files.

None of them reads the file. CHAIN-STANDARD §11 requires every reader to follow before the PR that moves it.

**Approach:** repoint each citation to `docs/how-to/presentation-deck.md`, keeping its section name. The sections exist
there: *The MCP bridge*, *Standard export set*, *Artifact dependency tree*, and the large-file uploads note. The skill
section and the routing test's constant change together. After the `pixi.toml` descriptions change,
`docs/how-to/pixi-tasks.md` is regenerated with `scripts/docs_pixi_tasks.py`. `environment.yaml` is regenerated and must
come out unchanged. No behaviour changes.

Ledger key: `34-1-herald-cites-the-deck-how-to-not-the-intake-stub`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- `spec-one-chain-per-station:CAP-11` (the Guild's; Herald mints no CAP and no FR, the relay shape doctor's Epics 24, 25,
  32, 34 and 36 use); CHAIN-STANDARD §11.
- `spec-feature-flag-governance` Q1: a `chore` needs no flag.
- Siblings: doctor Story 37.1 (blocked on this story), atlas Story 26.1, steward Story 77.1, marshal Story 76.1.

## Acceptance Criteria

- Given herald's code, skill, tests, deck READMEs and deck task descriptions When `git grep "docs/specs/presentation-deck"`
  runs over them Then it finds nothing
- Given each repointed citation When its section name is looked up in `docs/how-to/presentation-deck.md` Then the section
  exists
- Given `test_slides_generator_routing.py` When it runs Then it passes, with the skill and the constant naming the how-to
- Given `pixi.toml` descriptions changed When `docs/how-to/pixi-tasks.md` and `environment.yaml` are regenerated Then the
  tasks page reflects the new descriptions and `environment.yaml` is byte-identical
- Given the herald suite When `pixi run --frozen -e pyforge-herald pyforge-herald-test` runs Then it passes

## Tasks

1. `git grep -n "docs/specs/presentation-deck"` to list every herald-owned citation; confirm each cited section in the
   how-to.
2. Repoint each citation; change the skill's AD-2 section and the routing test's constant together.
3. Regenerate `docs/how-to/pixi-tasks.md` (`scripts/docs_pixi_tasks.py`) and `environment.yaml`
   (`pixi project export conda-environment -e build > environment.yaml`); confirm the latter is unchanged.
4. `pixi.toml` changed, so run `pixi run -e pyforge-guild pyforge-station-tests` as well as
   `pixi run --frozen -e pyforge-herald pyforge-herald-test`. Read each exit code.
5. Reconcile every Spec `spec-surface-check` names: memlog first, `git add`, then a scoped `--write-baseline --spec` for
   each (expected: `spec-pyforge-herald`, `spec-design-code-bridge`, `spec-modernist-identity`, and doctor's Spec for
   `docs/how-to/pixi-tasks.md`).

## Boundaries & Constraints

**Always:**
- Keep each citation's section name.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not move or edit `docs/specs/presentation-deck.md` in this story.
- Do not re-render any deck poster or export.
- Do not change a `pixi.toml` dependency or task command; descriptions only.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| code comment | `docs/specs/presentation-deck.md` § *Standard export set* | `docs/how-to/presentation-deck.md` § *Standard export set* | — |
| skill + test pin | SKILL.md AD-2 and `DECK_PIPELINE_SPEC` | both name the how-to | the routing test fails if only one changes |
| path-list fixture | `test_deck_status.py`'s synthetic mirrored-tree paths | left as is: it lists file paths, it does not cite the contract | — |
| a missing section | a citation whose section is absent from the how-to | stop and report it | do not invent a section |

</intent-contract>

## Binding

Parent capability: `spec-one-chain-per-station:CAP-11` (Guild relay; no herald CAP or FR).
Dream: `docs/dreams/one-chain-per-station.md` → § *2026-09-29 — One archive home*.
Ledger key: `34-1-herald-cites-the-deck-how-to-not-the-intake-stub`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: none. This is a `chore` (`spec-feature-flag-governance` Q1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild pyforge-station-tests` — expected: pass (`pixi.toml` changed).
- `git diff --exit-code environment.yaml` after the regeneration — expected: exit 0.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
