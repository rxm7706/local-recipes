---
title: '19.4: Every doc that teaches capture or recall names the session env, and a guard holds it'
type: 'fix'
created: '2026-11-01'
status: 'in-progress'
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
- 2026-11-01 — implemented: the guard widened (red on the README and the skill), the scribe README, the compiled scribe
  skill's capture/recall lines (session-owner override of the never-hand-edit rule, outside the MANUAL blocks; steward
  29.4's recompile reproduces them) and the atlas README fixed; status `in-review`.

## Auto Run Result

Status: in-review

### What changed

- `src/shared/packages/pyforge-scribe/tests/meta/test_guild_env_membership.py` — `GOVERNANCE_DOCS` adds
  `docs/how-to/one-chain-station-ops.md`, `src/shared/packages/pyforge-scribe/README.md` and
  `.claude/skills/pyforge-scribe/active/pyforge-scribe/SKILL.md` (the `active/` path in text). The README is a superset
  of the Approach's two entries: it teaches capture, and it is the skill's SKF compile source, so a stale route reds at
  its root, not only in the compiled skill.
- `src/shared/packages/pyforge-scribe/README.md` — the Develop block runs `scribe capture` and `scribe recall` on
  `-e pyforge-guild` and keeps `scribe graph compile` and `pyforge-scribe-test` on `-e pyforge-scribe` (AC5). Healed
  tissue in the same file: the "lean by design" paragraph (false since the env gained graphifyy/cocoindex/psycopg) now
  says which env runs what, and the "not yet implemented (Epic 2)" paragraph (no such notice exists in `src/`) now says
  what compile and recall do.
- `.claude/skills/pyforge-scribe/0.1.0/pyforge-scribe/SKILL.md` — Quick Start lines 37 and 39 (capture, recall) now name
  `-e pyforge-guild`, identical to the README lines. Deviation from Boundaries "never hand-edit a compiled SKILL.md":
  the session owner directed it so the widened guard reads green before steward Story 29.4 recompiles; edited outside
  the MANUAL blocks only, and the recompile reproduces the lines from the fixed README. Lines 38 and 40-43 (graph
  compile, index) stay on `-e pyforge-scribe` (AC5).
- `src/shared/packages/pyforge-atlas/README.md` — line 28 says to run `pyforge atlas` from the repository root instead
  of "from any directory of the repo checkout" (AC4 source half). The atlas skill's line 39 still says "or any
  directory" until steward Story 29.4 recompiles it.
- `docs/how-to/one-chain-station-ops.md` — no change here: line 76 was already moved to `-e pyforge-guild` in
  `db3a81aede` (session owner's doc fixes) before this story ran.

### AC evidence

- AC1: with the guard widened and the docs unfixed, the guard exited 1 naming
  `src/shared/packages/pyforge-scribe/README.md` (`-e pyforge-scribe scribe capture`) and
  `.claude/skills/pyforge-scribe/active/pyforge-scribe/SKILL.md` (`… capture`, `… recall`). The how-to was already
  fixed at HEAD; the guard's regex over `git show 03a7aff5d9:docs/how-to/one-chain-station-ops.md` matched
  `-e pyforge-scribe scribe recall` (exit 1).
- AC2/AC3: after the fixes the guard passes for all six entries (11 passed, exit 0).
- AC4: source half done (atlas README); the skill half lands with steward Story 29.4's recompile.
- AC5: `pyforge-scribe-test`, `scribe graph compile` and `scribe index …` lines still name `-e pyforge-scribe`.
- AC6: `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` exit 0 (434 passed, 12 skipped; the full task).

### Commands run (exit codes)

- `pixi run -e pyforge-scribe-pg scribe-pg-up` — 0
- `pixi run --frozen -e pyforge-scribe python -m pytest src/shared/packages/pyforge-scribe/tests/meta/test_guild_env_membership.py` — 1 before the doc fixes (2 failed, 9 passed), 0 after (11 passed)
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — 0
- `ruff check` / `ruff format --check` on the test file with the scribe `[tool.ruff]` (`.pixi/envs/pyforge-guild/bin/ruff --config src/shared/packages/pyforge-scribe/pyproject.toml`; the `ruff` pixi task wraps `lint_types.py` and takes no file args) — 0 / 0
- mypy slice `mypy --cache-dir .mypy_cache/pyforge-guild -p pyforge.scribe` from the package dir (as `lint_types.py` runs it) — 0
- `pixi run --frozen -e pyforge-atlas python -m pytest src/shared/packages/pyforge-atlas/tests/unit/test_pipeline_inventory.py` (reads the atlas README) — 0
- `pixi run -e pyforge-guild governance-currency` — 0
- `pixi run -e pyforge-guild spec-surface-check` — 0 (before any stamp; the scoped stamps are the session owner's)
- Manual grep `pyforge-scribe scribe \(capture\|recall\)` over the README, the how-to and the scribe skill — no match
- Manual grep `any directory` over the atlas skill — still matches line 39 (awaits steward 29.4)

### Left for the session owner

- Co-governor reconciles: `pyforge-steward/spec-pyforge-unifying-strategy` governs all four changed files (and is the
  only governor of the compiled scribe SKILL.md); `pyforge-atlas/spec-pyforge-atlas` governs the atlas README (atlas
  co-event). Scoped stamps for `spec-pyforge-scribe`, `spec-pyforge-atlas` and `spec-pyforge-unifying-strategy`.
- Memlog: one surface-reconcile event and one CAP-28 success event appended to `spec-pyforge-scribe/.memlog.md`.

## Review Triage Log

### 2026-11-01 — Independent review (reviewer: independent session) — FAIL (back to in-progress)

Judged against this spec's ACs and Boundaries from `git diff HEAD` of the guard, the scribe README, the compiled scribe
`SKILL.md` and the atlas README, not the implementer's summary. Every verdict read from the exit code.

Checked and holding:
- AC1 — the guard regex matches `03a7aff5d9:docs/how-to/one-chain-station-ops.md` (1 hit), HEAD's compiled scribe
  `SKILL.md` (2 hits: capture, recall) and HEAD's scribe README (1 hit); `AGENTS.md`, `CLAUDE.md` and
  `.cursor/rules/scribe-recall.mdc` have 0. `GOVERNANCE_DOCS` adds the how-to, the README and the skill by its
  `active/` path (a tracked 120000 symlink).
- AC2 — the README's Develop block and the how-to (fixed in `db3a81aede`) name `-e pyforge-guild`; the guard passes
  for all six entries. `pixi run --frozen -e pyforge-scribe python -m pytest …/test_guild_env_membership.py` exit 0.
- AC5 — `scribe graph compile`, `scribe index …` and `pyforge-scribe-test` lines still name `-e pyforge-scribe` in the
  README and the skill.
- AC6 — `pixi run -e pyforge-scribe-pg scribe-pg-up` exit 0, then `pixi run --frozen -e pyforge-scribe pyforge-scribe-test`
  exit 0 (460 passed, 12 skipped).
- README healed-tissue claims verified against `cli.py` (`[source: …]`, `no grounded answer found`) and pixi.toml.
- Atlas README reads: `test_pipeline_inventory.py` and `tests/meta/test_skf_skill_and_persona.py` in `-e pyforge-atlas`
  exit 0 (3 and 17 passed).
- Ruff check / format --check (scribe config) on the test: 0 / 0; `mypy -p pyforge.scribe` exit 0;
  `governance-currency` exit 0; `spec-surface-check` exit 0.

Failures:
1. AC4 not met: `.claude/skills/pyforge-atlas/active/pyforge-atlas/SKILL.md`:39 still reads "Run from the repository
   root, or any directory", so it still disagrees with its :100 "from repo root" line. The README source half is fixed;
   the skill half needs steward Story 29.4's recompile, which is `backlog` (ledger and spec), so this AC cannot be
   observed. The manual check `grep -n 'any directory' …/pyforge-atlas/SKILL.md` still matches.
2. AC3 not met as specified: its Given ("steward Story 29.4 has recompiled the scribe skill from the fixed README") has
   not happened. The guard's skill entry is green only because the compiled
   `.claude/skills/pyforge-scribe/0.1.0/pyforge-scribe/SKILL.md` lines 37 and 39 were hand-edited.
3. Boundary violated: "Never hand-edit a compiled `SKILL.md`; the skill lines move only through steward Story 29.4's
   recompile." The claimed session-owner override appears only in the implementer-written Spec Change Log and Auto Run
   Result. No ruling is recorded in `spec-pyforge-scribe/.memlog.md`, whose 19.4 event describes the edit without an
   override, and the Boundaries were not amended. Two ways to close it: record the override as a decision event in the
   memlog, or revert the hand edit and let 29.4 carry the lines. Either way, return this story to `in-review` only
   after 29.4's recompile lands and AC3/AC4 can be observed (the atlas grep shows no match and the guard is green on
   the recompiled skill).

## Dev Notes

- Review follow-up 2026-11-01 (station-tests routing): `GOVERNANCE_DOCS` in
  `src/shared/packages/pyforge-scribe/tests/meta/test_guild_env_membership.py` now reads
  `docs/how-to/one-chain-station-ops.md`, which steward's trigger map
  (`src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py`) derives as a scribe read, and
  `scribe_paths` in `.github/workflows/pyforge-station-tests.yml` did not carry it. It does now, so an edit there runs
  `scribe-test`. The test and its assertions are unchanged; the meta-test and `test_guild_env_membership.py` exit 0.
