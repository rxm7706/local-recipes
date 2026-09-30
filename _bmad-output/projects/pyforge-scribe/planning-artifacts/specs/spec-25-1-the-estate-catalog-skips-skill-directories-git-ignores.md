---
title: '25.1: The estate catalog skips skill directories git ignores'
type: 'fix'
created: '2026-09-30'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/dreams/pyforge-scribe.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-24-1-the-bmad-estate-catalog-is-generated-not-written.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-24-2-the-catalog-cannot-drift-silently.md
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/catalog.py
  - src/shared/packages/pyforge-scribe/tests/unit/test_catalog_bmad_estate.py
  - .gitignore
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `catalog.read_skills()` (`src/shared/packages/pyforge-scribe/src/pyforge/scribe/catalog.py`) walks every
directory under `.claude/skills/` on disk. CAP-32 derives the catalog from in-tree sources, but two kinds of directory are
on disk and not in the tree:

- **Gitignored skills.** Marshal's token-economy kit deploys the `caveman` skill into the primary checkout and every
  dispatch worktree. `.gitignore` ignores it (`**/.claude/skills/caveman/`), so CI never sees it.
- **Directories holding only ignored files.** Mason Story 15.1 retired `cfe-recipe-generation` and
  `cfe-recipe-lifecycle`, but the primary still holds both, with only `__pycache__/*.pyc` in them. The catalog lists them
  among the directories with no `SKILL.md`.

Measured 2026-09-30: the primary holds 121 `SKILL.md` files against 120 tracked, plus the two leftovers. So
`bmad-estate-check` (and `detectors-ci` and `pr-preflight`) reds on the primary and in every dispatch worktree while CI
stays green. A session that trusts the local red could "fix" the committed catalog to include a local tool.

**Approach:** when the root is a git work tree, `read_skills()` asks git once for every file under `.claude/skills/`
that it does not ignore: `git ls-files --cached --others --exclude-standard -z -- .claude/skills`, run with
`-C <root>`. It keeps the set of first-level directory names that appear there. A directory outside that set is
skipped, as a skill and as a no-`SKILL.md` directory. An untracked, not-yet-added skill still counts, because
`--others --exclude-standard` lists it. When the root is not a work tree, or git is missing or fails, the disk walk
stays exactly as it is today, which keeps every existing fixture test unchanged. The call is local, not networked, so
the generator stays offline-safe.

Ledger key: `25-1-the-estate-catalog-skips-skill-directories-git-ignores`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-scribe` CAP-32: "generated … from live in-tree sources". This story makes the realization match the
  intent. No new CAP.
- `spec-feature-flag-governance` Q1: a `fix` needs no flag. It changes no runtime behavior on a clean checkout.

## Acceptance Criteria

- Given a clean checkout (no ignored skill directory) When `pixi run -e pyforge-guild scribe catalog bmad-estate --write` runs Then `docs/reference/bmad-estate-llms-full.md` gains no byte, and `--check` exits 0
- Given the primary checkout with `caveman` deployed and the two `__pycache__`-only leftovers When `scribe catalog bmad-estate --check` runs Then it exits 0
- Given a temporary git work tree with a tracked skill, an untracked (not ignored) skill, a gitignored skill and a directory holding only ignored files When `read_skills()` runs Then it returns the tracked and untracked skills, and neither the ignored skill nor the ignored-files-only directory appears as a skill or as a no-`SKILL.md` directory
- Given a root that is not a git work tree (today's fixtures) When `derive()` runs Then its output is what it was before this change
- Given git is unavailable or `git ls-files` exits non-zero When `read_skills()` runs Then it falls back to the disk walk, never raises and never returns an empty catalog
- Given the git filter is removed When the new work-tree test runs Then it fails (mutation)

## Tasks

1. Read `read_skills()` and the `estate_root` fixture in `tests/unit/test_catalog_bmad_estate.py`.
2. Add a private helper in `catalog.py` that returns the set of first-level directory names under `.claude/skills/`
   that git lists (`--cached --others --exclude-standard -z`), or `None` when the root is not a work tree or git fails.
   Use `subprocess.run` with an argument list, `check=False`, and no shell.
3. In `read_skills()`, when the helper returns a set, skip every directory outside it before the `SKILL.md` test.
4. Add tests that `git init` a temporary work tree (skip with a reason if git is absent), commit one skill, add an
   untracked skill, a gitignored skill and an ignored-files-only directory, and assert the criteria above. Add a test
   that patches the helper's git call to fail and asserts the disk walk. Remove the filter once, locally, to see the
   work-tree test fail, then restore it.
5. Run `pixi run --frozen -e pyforge-scribe pyforge-scribe-test`, then `scribe catalog bmad-estate --check` on the
   dispatch worktree (which carries `caveman`). Read each exit code.
6. Reconcile every Spec `spec-surface-check` names for `catalog.py`: memlog first, `git add`, then a scoped
   `--write-baseline --spec` for each.

## Boundaries & Constraints

**Always:**
- Keep the catalog's sources, sections, digests and exit-code domain (0 / 1 / 2) unchanged.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not delete, move or `.gitignore` anything under `.claude/skills/`; the leftovers are the operator's to clean.
- Do not import any `pyforge.<station>` module and make no network call.
- Do not hand-edit `docs/reference/bmad-estate-llms-full.md`, `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| clean checkout | no ignored skill directory | catalog unchanged; `--check` exit 0 | — |
| `caveman` deployed | gitignored skill directory | skipped; `--check` exit 0 | — |
| `__pycache__`-only leftover | directory with only ignored files | skipped, not listed as a no-`SKILL.md` directory | — |
| new skill, not yet added | untracked, not ignored | counted | — |
| not a work tree | fixture root | today's disk walk | — |
| git missing or failing | `git` absent or non-zero exit | today's disk walk | never raises |

</intent-contract>

## Binding

Parent capability: `spec-pyforge-scribe` CAP-32 (defect; no new CAP).
Dream: `docs/dreams/pyforge-scribe.md` § *Realization log*, the 2026-09-30 entry.
Ledger key: `25-1-the-estate-catalog-skips-skill-directories-git-ignores`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: none. This is a `fix` (`spec-feature-flag-governance` Q1).

## Epic excerpt

**Type:** fix • **Effort:** S • **Deps:** — • **FR/AD:** spec-pyforge-scribe CAP-32 • Dream 2026-09-30 (Realization log)
**Surface:** `src/shared/packages/pyforge-scribe/src/pyforge/scribe/catalog.py` (`read_skills`), `tests/unit/test_catalog_bmad_estate.py` (the git-work-tree cases).
See `epics.md` § Story 25.1 for the full Given / When / Then / And.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-guild scribe catalog bmad-estate --check` in the dispatch worktree, which carries `caveman` — expected: exit 0.
- `pixi run -e pyforge-guild bmad-estate-check` — expected: exit 0.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamps.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
