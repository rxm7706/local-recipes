---
title: '142.1: The declaration names the exit-code domains of mason, herald, steward, scribe and atlas'
type: 'feature'
created: '2026-11-26'
status: 'done'
story: 142-1-the-declaration-names-the-exit-code-domains-of-mason-herald-steward-scribe-and-atlas
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # the exit-code declaration every verdict and the aggregator read; a gated declaration is a silent green (roster list)
surface:
  - 'docs/governance/guild-roster.json'
  - 'src/shared/packages/pyforge-core/src/pyforge/core/exit_domains.py'
  - 'src/shared/packages/pyforge-core/tests/unit/test_exit_domains.py'
  - 'tests/scripts/test_exit_code_domains_are_declared.py'
  - 'docs/reference/judgement-vocabulary.md'
  - 'src/shared/packages/pyforge-steward/tests/meta/test_exit_codes_match_the_exit_declaration.py'
  - 'src/shared/packages/pyforge-steward/src/pyforge/steward/interfaces.py'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Story 137.1 declared five exit-code domains and left the mason, herald, steward, scribe and atlas command lines out by a stated boundary. `3` means conda-forge-expert not found in mason, a conflict in herald, a refusal in steward and gate-failed in marshal; only marshal's is declared, and nothing shows the ten side by side.

**Approach:** Declare the five by member name and number in `guild-roster.json` and its in-process mirror, add their rows to the glossary page, and hold steward's own constants to the `steward` domain with a meta-test: the dispatcher's six names, the documented exit set, and every module-level `EXIT_*` integer in the package. The station sources are not rewritten to read the declaration, because each station's `contract.md` test reads its exit constants as literals.

Ledger key: `142-1-the-declaration-names-the-exit-code-domains-of-mason-herald-steward-scribe-and-atlas`.

### Living CAP citations

- spec-pyforge-steward:CAP-184 (amended 2026-11-26); FR-58 ← CAP-184.
- spec-pyforge-core:CAP-3 (no text change).
- No AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Keep every exit number the station returns today.

**Never:**
- Never change an exit number.
- Never make an installed package read `guild-roster.json`.
- Never rewrite a station's exit constants to calls: its `contract.md` test reads them as literals.

## Acceptance Criteria

**Given** five command lines spell their exit codes in their own modules, and Epic 137 left them undeclared
**When** the declaration, its mirror and the glossary gain the five domains, and steward's suite gains the meta-test
**Then** ten domains are declared; a differing mirror, glossary row or steward constant fails a test by name
**And** no exit number changes, and `interfaces.py`'s stale list of duties is gone

- **AC1 — Core's exit-domain tests pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-core pytest src/shared/packages/pyforge-core/tests/unit/test_exit_domains.py src/shared/packages/pyforge-core/tests/unit/test_exit_domains_match_the_guild_roster.py -q -m "live_tree or not live_tree"
  ```

- **AC2 — The script-level declaration test passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild pytest tests/scripts/test_exit_code_domains_are_declared.py -q
  ```

- **AC3 — Steward's meta-test passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_exit_codes_match_the_exit_declaration.py -q
  ```

</intent-contract>

## Review (2026-11-26)

Independent review by a fresh reviewer running `bmad-review`, given the diff and the stated intent and not the implementer's reasoning. Fourteen findings; all accepted and applied in the same change. For this story: the `steward` domain names the codes steward itself decides, and the notes and the glossary now say that `keys exec` and `deploy nic` return a child's code unchanged and that `ci`, `pages` and `estate` refuse with 3; the meta-test reads tuple and annotated `EXIT_*` assignments (`frames.py` has one); the comment in `cli.py` that still said eight duties is corrected.
