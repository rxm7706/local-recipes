# pyforge-marshal — planning artifacts

**Marshal** — the orchestration CLI productizing the `bmad-loop` capability
(`marshal init/factory/gate/deploy`): loop-home provisioning, run supervision,
gate evaluation, landing, fleet status, adapter portability, and policy
composition. Owns the console and the loop every other station depends on.
dist `pyforge-marshal` / module `pyforge.marshal` / CLI `marshal`.

BMAD Tier-2 output for this project: `briefs/`, `prds/`, `architecture/`,
`epics.md`, `specs/`. See `../SYNC-RUNBOOK.md` for the factory-doc sync
procedure this project's PRD/architecture set is subject to.

## Deliberate asymmetries

Conformance-table row 10 requires this section: the next reader is an agent with no
session context, and an unexplained deviation reads as drift. Recorded 2026-09-07
(Story 32.3, `spec-fleet-consistency-standard` CAP-4).

- **`PRD.md` at this root is the FACTORY PRD, not marshal's station PRD.** Its
  frontmatter says `project_name: local-recipes` — it describes the whole packaging
  factory and is the document `SYNC-RUNBOOK.md` keeps current against the live
  `conda-forge-expert` skill. Marshal's own station PRD is the sharded
  `prds/prd-pyforge-marshal-2026-07-25/`, which is INV-3 conformant. Two different
  documents; the flat one is not a pre-6.10 leftover and must not be "fixed" into
  `prds/`. The same applies to the other loose factory docs here
  (`architecture.md` and the four `architecture-*.md`, `index.md`,
  `project-overview.md`, `source-tree-analysis.md`, `development-guide.md`,
  `deployment-guide.md`): marshal is the factory-docs project, so it carries more
  root-level documents than a station does. `bmad_drift_check.py` classifies every
  one of them; none is a stray file.

- **`reviews/` holds review artifacts, `retros/` holds retrospectives.** They are
  different things and both are correct here. `reviews/` currently holds the TEA
  equivalence report (Story 31.1).

- **The four epic retros moved out of Tier-3 on 2026-09-07.** `epic-2`/`-3`/`-4`/`-5`
  retros lived in `implementation-artifacts/`, which is gitignored — so they were
  absent from every clone and one worktree teardown from being lost, the same failure
  that cost `pyforge-warden` 13 story specs. They now sit in `retros/` alongside every
  other station's, which is where all seven others already kept theirs.
