---
title: "19.1: Mason's station skill is SKF-compiled, exported and consulted by the persona"
type: 'feature'
created: '2026-09-28'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-33-1-skf-domain-skill-and-bmad-persona-for-steward.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-23-1-the-skf-managed-block-lives-in-agents-md-only.md
  - .claude/skills/pyforge-steward/skill-brief.yaml
  - .claude/skills/bmad-agent-mason/SKILL.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** every other station has an SKF-compiled station skill (`.claude/skills/pyforge-<station>/`, steward's from
Story 33.1) and a persona that consults it. Mason has only the persona, and the persona is told to consult
`conda-forge-expert` and *not* a compiled `pyforge-mason` skill (`.claude/skills/bmad-agent-mason/SKILL.md`), so Mason's
own grammar — the `package` and `environment` crafts as much as `recipe` — is documented nowhere an agent loads. The
operator ruled on 2026-09-28 that Mason's station skill is SKF-compiled like the other seven (`spec-pyforge-mason`
CAP-29, questions 2a and 3). `AGENTS.md` § Policy carries the dated `A-only` exception for `.claude/skills/pyforge-mason/`
(landed with the Spec, before this story).

**Approach:** compile it the way steward's was (Story 33.1), with SKF's own workflows and nothing hand-rolled:
1. `skf-brief-skill` writes `.claude/skills/pyforge-mason/skill-brief.yaml`: `name: pyforge-mason`, `version` and
   `target_version` `0.1.0`, `source_type: source`, `source_repo: src/shared/packages/pyforge-mason`,
   `source_authority: internal`, `language: python`, `forge_tier: Quick`, `created_by: skf-create-skill`, scope
   `specific-modules` over `src/pyforge/mason/cli.py`, `src/pyforge/mason/__init__.py` and `README.md`, excluding
   `tests/**` and `**/__pycache__/**` (steward's brief, `heuristic: station-package-cli`).
2. `skf-create-skill` compiles `.claude/skills/pyforge-mason/0.1.0/pyforge-mason/{SKILL.md, metadata.json,
   provenance-map.json, context-snippet.md}` and the `active` → `0.1.0` symlink. Forge data lands in SKF's
   `forge_data_folder` (Tier 3, gitignored).
3. `skf-export-skill` for `pyforge-mason` only: `_bmad/skf/config.yaml`'s `ides: [other]` (scribe Story 23.1) targets
   `AGENTS.md` alone, so the export adds the eighth entry to its SKF block (header `8 skills`) and records itself in
   `.claude/skills/.export-manifest.json` and `.claude/skills/export-skill-result-*.json`. The block is never hand-edited.

The compiled skill documents `pyforge mason recipe {new, validate, build, diagnose, optimize, scan, submit, update}`,
`package {build, ship}`, `environment {lock, check}` and `doctor` (the `pyforge mason …` form — the bare `mason` binary is
not a second public grammar), `POST /stations/mason/mcp`, and `mason doctor`'s degradation report; it sends every recipe
question to `.claude/skills/conda-forge-expert/SKILL.md`, and its snippet's gotchas say "do not replace
conda-forge-expert", as steward's and warden's do. Where the compile does not carry the CFE routing, supply it through the
inputs SKF reads (the brief's `description`, the package `README.md`) and recompile — never hand-edit generated files.

Then the persona consults both: `pyforge-mason` for the grammar, CFE for recipe work (`SKILL.md` Step 4 and *Allowed
actions*, `customize.toml`, the golden transcript `transcripts/mason-doctor-e2e.json`). The mason meta-tests follow:
`tests/meta/test_skf_mason_skill.py` (new, the shape of steward's `test_skf_steward_skill.py`), and
`tests/meta/test_persona_consults_cfe.py` accepts exactly two consults — `pyforge-mason` at
`.claude/skills/pyforge-mason/active/pyforge-mason/SKILL.md` and CFE at `.claude/skills/conda-forge-expert/SKILL.md` —
keeps every CFE assertion, and drops only its assertions that `.claude/skills/pyforge-mason` is absent. The notes line
that says Mason has no SKF skill (`docs/reference/agent-instruction-notes.md` § *SKF skills block*) is replaced by a dated
note that the ruling reversed it; `docs/reference/skills-catalog.md` is regenerated.

Ledger key: `19-1-mason-s-station-skill-is-skf-compiled-exported-and-consulted-by-the-persona`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-29 (FR-51); canopy:AD-17 (station skills are SKF content skills; CFE the hand-authored
  exception); `spec-pyforge-steward:CAP-160` reads this skill once Story 72.2 lands.

## Acceptance Criteria

- Given the committed brief When `skf-create-skill` has run Then `.claude/skills/pyforge-mason/active/pyforge-mason/SKILL.md`, `metadata.json` (`"generated_by": "create-skill"`, `"name": "pyforge-mason"`, `source_repo` ending `pyforge-mason`) and `provenance-map.json` exist, and every provenance entry names a file under `src/shared/packages/pyforge-mason/` at a line inside that file
- Given the compiled skill When `skf-validate-frontmatter.py <SKILL.md> --skill-dir-name pyforge-mason` and `skf-validate-output.py <package> --generated-by create-skill` run Then each exits 0 with no high finding
- Given the compiled `SKILL.md` When it is read Then it names `pyforge mason recipe`, `pyforge mason package`, `pyforge mason environment`, `pyforge mason doctor` and `/stations/mason/mcp`, and links `conda-forge-expert` for recipe work
- Given `skf-export-skill` has run for `pyforge-mason` When `skf-rebuild-managed-sections.py AGENTS.md check` runs Then the section is present with valid markers, the header reads `8 skills`, a `[pyforge-mason v0.1.0]` entry has `root: .claude/skills/pyforge-mason/`, and the seven existing entries are unchanged
- Given the persona's golden transcript When `validate_transcript` checks it Then it holds a `pyforge-mason` consult, a CFE consult, `pyforge mason …` grammar and a `POST /stations/mason/mcp` event, and a consult of any third skill, a filesystem event or ad-hoc HTTP fails it
- Given `.claude/skills/conda-forge-expert/` When the mason meta-tests run Then CFE is still hand-authored (no `metadata.json`, `active`, `provenance-map.json` or version directory) and edited only by sanctioned `retro:` commits
- Given `docs/reference/agent-instruction-notes.md` When it is read Then no line says Mason has no SKF skill, and a dated note records the 2026-09-28 reversal

## Boundaries & Constraints

**Always:**
- SKF's own workflows produce every generated file (`skf-brief-skill`, `skf-create-skill`, `skf-export-skill`); the
  `AGENTS.md` SKF block is written only by `skf-export-skill`.
- The skill sends recipe work to `conda-forge-expert`; it documents grammar, never recipe knowledge (no gotcha, pin
  table or selector rule — mason AD-1's rule, carried to the skill).
- Co-governors: `AGENTS.md` is governed by `spec-pyforge-scribe`; mason's tests by `spec-pyforge-mason` and
  `spec-pyforge-core`. Before landing, add a memlog entry on every Spec `spec-surface-check` names, `git add`, run one
  scoped `--write-baseline --spec` per named Spec from a clean tree, re-run the check and read its exit code. A
  co-governor memlog entry moves that Spec's date: run `python scripts/chain_currency_sweep_check.py --project <slug> --json`
  for each and carry its cascade note if it fires.
- The seven other stations' SKF meta-tests must still pass in their own environments (the export rewrites the shared block).

**Never:**
- Do not replace, fork, SKF-compile or version-nest `conda-forge-expert`, and do not edit its surface (AD-15).
- Do not hand-edit the SKF block in `AGENTS.md`, `_bmad/skf/config.yaml`, or any SKF-generated file.
- Do not edit `docs/foundry/frames/**` — the Mason Frame's "Do not SKF-compile" line is B's (operator-owned B-side follow-up).
- Do not touch `src/shared/packages/pyforge-mason/src/**` except `README.md` if the compile needs the CFE routing there.
- Do not change `five_tier.py` (steward Story 72.2) or `pixi.toml`'s Guild feature (steward Story 72.1).
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| compile | brief over `cli.py`, `__init__.py`, `README.md` | versioned package + `active` link + provenance | a validator high finding fails the story |
| export | `ides: [other]` | `AGENTS.md` block `8 skills`; seven entries unchanged | an orphan or second block fails `skf-rebuild-managed-sections.py … check` |
| persona consult | `pyforge-mason` then CFE | transcript valid | a third skill, filesystem or HTTP event is refused |
| CFE untouched | no retro commit | CFE assertions green | an unsanctioned CFE edit fails the meta-test |
| guild front door | `pyforge mason` in `-e pyforge-guild` before steward 72.1 | not required by this story's checks | the skill still documents `pyforge mason …` |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-29 (FR-51).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-09-27 — Proposed: Mason has its own skills, and `conda-forge-expert` is one of them* (the operator's answers of 2026-09-28).
Ledger key: `19-1-mason-s-station-skill-is-skf-compiled-exported-and-consulted-by-the-persona`.
Ledger status at mint: `backlog`.
Kinship: steward Story 72.2 (`spec-pyforge-steward:CAP-160`) is minted `blocked` until this story lands.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`; `test_skf_mason_skill.py` and `test_persona_consults_cfe.py` run inside it).

**Manual checks:**
- `python .claude/skills/shared/scripts/skf-rebuild-managed-sections.py AGENTS.md check` — expected: `has_managed_section: true`, `markers_valid: true`.
- The other seven stations' SKF meta-tests (`test_skf_*` under atlas, doctor, herald, marshal, scribe, steward, warden), each in its own environment — expected: pass.
- `pixi run --frozen -e pyforge-scribe python -m pytest -q src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py` — expected: pass.
- `pixi run -e pyforge-guild docs-skills-catalog -- --check` — expected: exit 0 after regeneration.
- `pixi run -e pyforge-guild governance-currency` and `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0.

## Review Triage Log
