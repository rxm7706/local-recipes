---
title: "19.4: The two feedstock campaigns become Mason skills"
type: 'docs'
created: '2026-09-28'
status: 'done'
baseline_revision: '915e6292e3c103c2b22a73266eb52a4b92e9e600'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - docs/how-to/feedstock-platform-expansion.md
  - docs/how-to/feedstock-failure-remediation.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-17-3-the-recurring-campaigns-have-a-home-and-a-record.md
  - .claude/skills/conda-forge-expert/guides/feedstock-platform-expansion.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the two feedstock campaigns — platform expansion (refresh a feedstock and widen its build matrix in one PR)
and red-PR remediation (drive failing bot PRs to green, pushed, or deferred-as-blocked) — are written as
`docs/how-to/feedstock-platform-expansion.md` (658 lines) and `docs/how-to/feedstock-failure-remediation.md` (454 lines),
BMAD intake documents an agent has to be pointed at. Each calls itself the orchestration layer on top of
`conda-forge-expert`, which "owns the procedural detail" and is authoritative on any conflict. The operator ruled on
2026-09-28 that the two become Mason skills (`spec-pyforge-mason` CAP-29, question 2d).

**Approach:** with `conda-forge-expert` invoked first (CLAUDE.md Rule 1 — the campaigns are conda-forge work), move each
how-to's body into a Mason skill, verbatim — a move, not a rewrite (doctor Story 23.3 moved the same bodies from
`docs/specs/` to `docs/how-to/` the same way):
- `.claude/skills/mason-feedstock-platform-expansion/SKILL.md` and `.claude/skills/mason-feedstock-failure-remediation/SKILL.md`:
  `name:` / `description:` frontmatter, then the how-to's parameters, waves, open questions, risks and acceptance;
  each skill's `references/worked-examples.md` carries its how-to's Worked Examples, where new cases keep appending
  (CAP-20's record). Only the links and the "run this" line change: they point at the skill instead of the how-to.
- The timeless workflow stays in CFE — `.claude/skills/conda-forge-expert/guides/feedstock-platform-expansion.md` and
  SKILL.md's diagnostic chain and gotchas — linked from the skills, never copied (the gotcha-heading guard enforces it).
- `docs/how-to/feedstock-*.md` each become a short pointer to their skill (frontmatter kept, the
  `docs/specs/feedstock-*.md` stub pattern); the two `docs/specs/` stubs point at the skill; `CLAUDE.md`'s legacy index
  rows keep both filenames (`bmad-drift-check`'s `check_spec_indexed`) with their description updated.
- `test_mason_skills.py` gains both rows; `docs/reference/skills-catalog.md` is regenerated;
  `docs/reference/agent-instruction-notes.md` § *Skill Reference* gains two rows.

The operator's ruling supersedes, for these two campaigns only, Story 17.3's *Never* ("never absorb the three workflow
procedures into a new mason-owned rewrite"): this is a verbatim move, and `docs/specs/feedstock-refresh.md` does not move.

Ledger key: `19-4-the-two-feedstock-campaigns-become-mason-skills`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: docs / M / S-19.3.

### Living CAP citations

- `spec-pyforge-mason` CAP-29 (FR-51); CAP-20 (the recurring campaigns); AD-1; canopy:AD-17.

## Acceptance Criteria

- Given the two how-tos at this story's base When their bodies are compared with the two skills Then every section (parameters, waves, open questions, risks, acceptance, worked examples) is present in the skill and its `references/worked-examples.md`, changed only in links and the invocation line
- Given `docs/how-to/feedstock-platform-expansion.md` and `docs/how-to/feedstock-failure-remediation.md` When they are read Then each is a short pointer to its skill, and the two `docs/specs/` stubs resolve to the skill
- Given `CLAUDE.md` When `bmad-drift-check` runs Then both stub filenames are still indexed and no `spec-unindexed` finding appears
- Given `test_mason_skills.py` When it runs Then its table holds all four hand-authored skills and each passes, including no `### G<n>.` heading and a link to `.claude/skills/conda-forge-expert/`
- Given CFE's `guides/feedstock-platform-expansion.md` When this story lands Then it is byte-identical (CFE's pointer back to the skill is Story 19.5's retro)

## Boundaries & Constraints

**Always:**
- Invoke `conda-forge-expert` before editing; where a campaign step conflicts with the skill, CFE wins and the story records the deviation.
- Co-governors: `docs/how-to/**` is governed by `spec-pyforge-doctor`, `CLAUDE.md` by `spec-pyforge-scribe`. Add a memlog
  entry on every Spec `spec-surface-check` names, `git add`, one scoped stamp per named Spec from a clean tree, re-check,
  read the exit code; run the chain-currency sweep for each project whose memlog moved and carry its cascade note if it fires.

**Never:**
- Do not rewrite, summarize or reorder the campaign bodies; do not copy CFE guide or gotcha text into a skill.
- Do not edit the CFE surface (AD-15) — its pointer back is Story 19.5's `retro(cfe):` commit.
- Do not move `docs/specs/feedstock-refresh.md` or edit any `recipes/**`.
- Do not author a new file under `docs/specs/`; do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| body moved | how-to at base | skill + worked examples carry it verbatim | a missing section fails review |
| old link | a Dream or doc linking `docs/how-to/feedstock-*.md` | resolves to the pointer page | `governance-currency` stays green |
| stub index | `CLAUDE.md` legacy rows | both filenames present | `bmad-drift-check` `spec-unindexed` fails |
| gotcha copied | CFE gotcha text pasted into a skill | meta-test fails | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-29 (FR-51).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-09-27 — Proposed: Mason has its own skills, and `conda-forge-expert` is one of them*.
Ledger key: `19-4-the-two-feedstock-campaigns-become-mason-skills`.
Ledger status at mint: `backlog`.
Deps: S-19.3.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild bmad-drift-check` — expected: no `spec-unindexed` finding.
- `pixi run -e pyforge-guild docs-skills-catalog -- --check` — expected: exit 0 after regeneration.
- `pixi run -e pyforge-guild governance-currency` and `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0.

## Review Triage Log

### 2026-10-08 — Review pass
- verdicts: 3 findings — high 0, medium 2, low 0, false 0, maybe-false 1
- findings:
  - `[medium]` `[patch]` Platform skill step 4 still said append at bottom of SKILL.md — updated to name references/worked-examples.md.
  - `[medium]` `[patch]` Failure-remediation skill step 4 omitted references path — updated for parity.
  - `[maybe-false]` `[defer]` Scoped spec-surface baseline stamp vs 915e629 — reconcile guard and spec-surface-check green via memlog entries; operator stamps baseline at PR time per AGENTS checklist, not in this auto run.

## Auto Run Result

Status: done

Summary: Moved feedstock platform-expansion and failure-remediation campaign bodies from long `docs/how-to/` pages into Mason skills (`mason-feedstock-platform-expansion`, `mason-feedstock-failure-remediation`) with worked examples in each skill's `references/worked-examples.md`. How-to and legacy `docs/specs/` stubs now point at the skills; `CLAUDE.md` index updated; `test_mason_skills.py` covers all four hand-authored Mason skills; skills catalog and agent-instruction-notes refreshed.

Files changed:
- `.claude/skills/mason-feedstock-*` — campaign SKILL.md + worked-examples (verbatim move, link/run-line updates only)
- `docs/how-to/feedstock-*.md`, `docs/specs/feedstock-*.md`, `docs/how-to/README.md` — short pointers
- `CLAUDE.md` — legacy stub index descriptions
- `src/shared/packages/pyforge-mason/tests/meta/test_mason_skills.py` — two campaign skill rows
- `docs/reference/skills-catalog.md`, `docs/reference/agent-instruction-notes.md`
- Co-governor memlogs on spec-pyforge-mason, spec-pyforge-doctor, spec-pyforge-scribe

Review: 2 medium patches applied (worked-example append targets); 1 defer (baseline stamp left to PR author).

Verification: `pyforge-mason-test` pass; `docs-skills-catalog --check` pass; `bmad-drift-check` pass (no spec-unindexed); `governance-currency` pass; `python scripts/spec_surface_reconcile.py` pass after memlog reconcile.

Follow-up review recommended: false
