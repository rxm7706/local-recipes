# Glossary — Mason

Companion to `SPEC.md`. Downstream artifacts use these terms **verbatim**; synonyms are a
discipline violation.

## Product identity

- **Mason** — the display brand (PyForge Mason on first mention per document).
  **`pyforge-mason`** is the distribution, **`pyforge.mason`** the import module, **`mason`** the
  CLI. Display copy uses *Mason*; file and package names use the lowercase technical form.

## The wrapped capability

- **CFE** — the `conda-forge-expert` skill: its canonical scripts, its public wrapper tier, and its
  MCP server. Governed by its own Spec (adopted companion) and **authoritative over Mason on all
  recipe semantics** under the repo's Rule 1.
- **CFE root** — the filesystem directory containing the CFE public wrapper tier. What the
  resolution chain locates.
- **The adapter** (the CFE port) — `pyforge.mason.cfe`, the single module permitted to invoke CFE.
  Everything else in Mason reaches CFE through it or not at all.
- **Recipe knowledge** — packaging judgement specific to conda-forge: gotchas, constraints, pin
  rules, policy constants, format semantics. Owned by CFE. **Never** present in `pyforge.mason`.
- **Degradation** — the defined behaviour when the CFE root cannot be resolved: a structured,
  actionable error for CFE-dependent commands, and unaffected operation for everything else.

## Shipping

- **Ship target** — a named destination for a built artifact. Exactly four exist in v1: `pypi`,
  `pypi-test`, `conda-forge`, `channel:<name>`.
- **Synchronous target** — one that reaches a terminal state within the command's lifetime
  (`pypi`, `pypi-test`, `channel:<name>`).
- **Asynchronous target** — one whose command completion means *initiated*, not *done*
  (`conda-forge`, which opens a pull request into a human review queue measured in days).
- **Ship receipt** — the structured record a ship operation returns: per-target state, plus a
  reference (URL, PR number, channel path).

| Ship state | Meaning |
|---|---|
| `not_attempted` | The target was not reached in this invocation. |
| `failed` | The target failed to **initiate**. Drives an aggregate failure exit code. |
| `pending` | Initiated, not yet terminal. **Never collapsed into success in any rendering.** |
| `terminal` | Complete. |

## Engines and layout

- **Engine** — an external tool Mason orchestrates and **never reimplements**: `rattler-build`,
  `grayskull`, `build`, `twine`, `conda-lock`, `pixi`. Discovered on `PATH`, provisioned as conda
  run-dependencies, never downloaded at runtime.
- **Workspace member** — a package under the repo's shared packages tree, wired into the root
  manifest by a path dependency, per the two sibling packages' convention.

## Capability tiers

The distinction that keeps two thirds of the product standalone. It is **structural**, enforced by
test — not a convention.

| Tier | What it covers | Behaviour with the CFE root absent |
|---|---|---|
| **CFE-dependent** | all `mason recipe` verbs, **and only** the `conda-forge` ship target | Exits non-zero naming all four resolution steps |
| **CFE-independent** | everything else in `mason package`, all of `mason environment`, `mason doctor` | Runs unaffected |

The CFE port is resolved **per target**, not per command: a `pypi` ship must succeed with CFE
absent. The exception list holds exactly one entry, and a blanket "except where CFE is needed"
formulation is explicitly forbidden — that phrasing is the erosion the rule exists to stop.

## Cutover, skills and the refresh campaign (pointers only)

Added 2026-11-01 (EGM fleet audit, marshal Story 113.7; cluster mason-c04, findings MAS-M-Z6, MAS-M-C3,
MAS-M-C4). Each line names a term CAP-29 or CAP-35 uses and points at the place that defines it; nothing is
restated here.

- **`A-only`** — a cutover mode: `AGENTS.md` § Policy (the modes bullet, and Mason's dated skill exception); CAP-29's row is `pyforge-mason:CAP-29` in `docs/foundry/capability-ledger.yaml`.
- **`pyforge.cutover_root`** — the cutover flag: declared in `src/platform/config/flags.json`, read by `src/shared/packages/pyforge-core/src/pyforge/core/cutover_root.py`; what its flip to `foundry` means, `AGENTS.md` § *local-recipes (PyForge)*.
- **SKF content skill, hand-authored skill** — the two skill kinds in CAP-29: canopy:AD-17 in `_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md`; the version-nested layout, `_bmad/skf/knowledge/version-paths.md`; which Mason skill is which, CAP-29.
- **G53** — `.claude/skills/conda-forge-expert/SKILL.md`, heading `### G53.`
- **G95** — `.claude/skills/conda-forge-expert/SKILL.md`, heading `### G95.`
- **G96** — `.claude/skills/conda-forge-expert/SKILL.md`, heading `### G96.`
- **Track A** — `feedstock-refresh.md` beside this file, anchor `#track-a` (sole-maintainer).
- **Track B** — `feedstock-refresh.md` beside this file, anchor `#track-b` (co-maintainer).
- **Wave H** — `feedstock-refresh.md`, Track A § *Wave H — total-coverage follow-up*.
- **Landmines** — `feedstock-refresh.md`, Track A § *Landmines* and Track B § *Landmines*.
