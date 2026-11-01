---
title: '19.4: Every doc that teaches capture or recall names the session env, and a guard holds it'
type: 'fix'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-19-2-scribe-capture-and-recall-run-from-the-session-default-environment.md
  - src/shared/packages/pyforge-scribe/tests/meta/test_guild_env_membership.py
  - src/shared/packages/pyforge-scribe/README.md
  - docs/how-to/one-chain-station-ops.md
  - src/shared/packages/pyforge-atlas/README.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** CAP-28 says `scribe capture` and `scribe recall` run from the session default environment
(`-e pyforge-guild`), and its meta-test is meant to red a governance doc that still sends sessions to
`-e pyforge-scribe`. The meta-test reads only three files: `GOVERNANCE_DOCS = ("AGENTS.md", "CLAUDE.md",
".cursor/rules/scribe-recall.mdc")` (`src/shared/packages/pyforge-scribe/tests/meta/test_guild_env_membership.py`:29).
At `03a7aff5d9` three other docs still teach the old routing and nothing reds:

- `src/shared/packages/pyforge-scribe/README.md`:22 — `pixi run -e pyforge-scribe scribe capture …`. The README is
  the SKF compile source of the scribe skill, so the error reaches the skill.
- `.claude/skills/pyforge-scribe/active/pyforge-scribe/SKILL.md`:37 and :39 — capture and recall on
  `-e pyforge-scribe` (compiled from the README; the skill predates CAP-28).
- `docs/how-to/one-chain-station-ops.md`:76 — recall on `-e pyforge-scribe`.

The same audit cluster found the atlas skill contradicting itself on the working directory: `SKILL.md`:39 says
"Run from the repository root, or any directory", while :100 says "from repo root". Its compile source is
`src/shared/packages/pyforge-atlas/README.md`:28 ("from any directory of the repo checkout"), and `AGENTS.md`
§ *Known pitfalls* says every pixi task runs from the repo root.

`AGENTS.md`'s env line (:60, "Only `pyforge-guild` exists at runtime") compresses the 2026-09-20 ruling and drops
its per-station clause. That line sits inside the `bmad:context` block, so it is fixed by marshal Story 113.7's
`bmad-project-context` refresh, never here.

EGM audit 2026-11-01 findings carried: RUL-D6, RUL-C4 (cluster RUL-CL3). Research:
`_bmad-output/projects/pyforge-scribe/planning-artifacts/research/egm-audit-2026-11-01.md`; the RUL findings'
events are on `spec-pyforge-scribe/.memlog.md` (2026-11-01).

**Approach:** Widen the guard first and see it red, then fix the sources and see it green:

1. Add `docs/how-to/one-chain-station-ops.md` and `.claude/skills/pyforge-scribe/active/pyforge-scribe/SKILL.md`
   (the skill path in text, never a top-level symlink: operator ruling 2026-11-01) to `GOVERNANCE_DOCS`. Run the
   test and read it red on both.
2. Change the scribe README's line 22 and the how-to's line 76 to `-e pyforge-guild`. Change the atlas README's
   line 28 to say the CLI runs from the repository root.
3. Steward Story 29.4 (same PR) recompiles the scribe and atlas skills from the fixed READMEs. The guard's skill
   entry reads green only after that recompile. Never hand-edit a compiled `SKILL.md`.

Ledger key: `19-4-every-doc-that-teaches-capture-or-recall-names-the-session-env-and-a-guard-holds-it`.
Type / Effort / Deps: fix / S / — (cross-station, same PR: steward 29.4; marshal 113.7).

### Living CAP citations

- `spec-pyforge-scribe` CAP-28 success: "a scribe meta-test … reds … when a governance doc still tells sessions that
  capture/recall need `-e pyforge-scribe`". This story makes the guard read every doc that teaches it. No new CAP.
- `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- AC1: Given `GOVERNANCE_DOCS` with the how-to and the scribe skill added and no doc yet fixed When
  `test_governance_docs_no_longer_route_capture_or_recall_to_the_scribe_env` runs Then it fails for
  `docs/how-to/one-chain-station-ops.md` and for `.claude/skills/pyforge-scribe/active/pyforge-scribe/SKILL.md`,
  naming each stale invocation.
- AC2: Given the scribe README's line 22 and the how-to's line 76 name `-e pyforge-guild` When the guard runs Then the
  README-sourced lines and the how-to pass, and `AGENTS.md`, `CLAUDE.md` and `.cursor/rules/scribe-recall.mdc` still
  pass.
- AC3: Given steward Story 29.4 has recompiled the scribe skill from the fixed README When the guard runs Then every
  `GOVERNANCE_DOCS` entry passes.
- AC4: Given the atlas README's line 28 says to run from the repository root When steward Story 29.4 recompiles the
  atlas skill Then the skill no longer says "or any directory", and its line 39 agrees with its "from repo root" usage
  line.
- AC5: Given a line that needs the station env or the heavy extras (`pyforge-scribe-test`, `scribe graph compile`,
  `scribe index …`) When this story lands Then it still names `-e pyforge-scribe`: only capture and recall move.
- AC6: Given this story lands When `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` runs Then it exits 0.

## Boundaries & Constraints

**Always:**
- See the guard red before fixing a doc (AC1), then green (AC2, AC3).
- Reconcile every Spec `spec-surface-check` names: `spec-pyforge-scribe` (the scribe README), `spec-pyforge-doctor`
  (the how-to, which doctor governs) and `spec-pyforge-atlas` (the atlas README). Write the memlog entry first,
  then `git add`, then one scoped `--write-baseline --spec <project>/<spec>` per Spec.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Never hand-edit a compiled `SKILL.md`; the skill lines move only through steward Story 29.4's recompile.
- Never edit `AGENTS.md`'s `bmad:context` block; its env line rides marshal Story 113.7's `bmad-project-context`
  refresh.
- Never add a heavy extra (`graphifyy`, `cocoindex`, `psycopg`) to the Guild feature, and never touch `pixi.toml`.
- Never hand-edit `SPEC.md`, a `.memlog.md` outside `memlog.py append`, or `sprint-status-ledger.yaml`.
- Never run a bare `spec_surface_check.py --write-baseline`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| guard widened, docs stale | how-to and skill in `GOVERNANCE_DOCS` | fails on both, naming the line | — |
| sources fixed, skill not recompiled | README and how-to on `-e pyforge-guild` | skill entry still red | recompile in steward 29.4 |
| everything fixed | recompiled skill | every entry passes | — |
| station-env line | `pyforge-scribe-test`, `graph compile`, `index …` | unchanged | — |

</intent-contract>

## Binding

Parent: `spec-pyforge-scribe` CAP-28 (FR-17); a `fix`, so no new CAP.
Parent capability:
- `spec-pyforge-scribe` CAP-28 — `scribe capture` and `scribe recall` run from the session default environment.
- PRD FR-17 ← CAP-28.
Dream: `docs/dreams/pyforge-scribe.md` (Dream item (7), pixi-env half; the 2026-11-01 EGM audit residue).
Ledger key: `19-4-every-doc-that-teaches-capture-or-recall-names-the-session-env-and-a-guard-holds-it`.
Ledger status at mint: `backlog`.
Deps: — (cross-station, same PR: steward Story 29.4 recompiles the skills; marshal Story 113.7 carries the
`AGENTS.md` env line).
Flag: none. This is a `fix` (`spec-feature-flag-governance` Q1).
EGM audit findings: RUL-D6, RUL-C4 (cluster RUL-CL3).
Surface: `src/shared/packages/pyforge-scribe/tests/meta/test_guild_env_membership.py`, `src/shared/packages/pyforge-scribe/README.md`, `docs/how-to/one-chain-station-ops.md`, `src/shared/packages/pyforge-atlas/README.md`, `.claude/skills/pyforge-scribe/active/pyforge-scribe/SKILL.md` (read by the guard; recompiled by steward Story 29.4).

## Epic excerpt

**Type:** fix • **Effort:** S • **FR/AD:** spec-pyforge-scribe CAP-28 (FR-17); a fix, no new CAP.
See `epics.md` § Story 19.4 for the full Given / When / Then / And.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/meta/test_guild_env_membership.py`
  — expected: red after the guard is widened (AC1), green after the fixes and the recompile (AC3).
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (the station's `verify_commands`).
- `pixi run -e pyforge-guild governance-currency` — expected: exit 0.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

**Manual checks:**
- `grep -n 'pyforge-scribe scribe \(capture\|recall\)' src/shared/packages/pyforge-scribe/README.md docs/how-to/one-chain-station-ops.md .claude/skills/pyforge-scribe/active/pyforge-scribe/SKILL.md`
  — expected: no match once steward 29.4 has recompiled.
- `grep -n 'any directory' .claude/skills/pyforge-atlas/active/pyforge-atlas/SKILL.md` — expected: no match after the
  recompile.

## Spec Change Log

- 2026-11-01 — minted `backlog` from the EGM fleet audit (marshal Story 113.7; operator triage 2026-11-01).

## Auto Run Result

Status: backlog
