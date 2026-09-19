# Gemini — read AGENTS.md

This repo is **Dream-first and framework-neutral**. Read **`AGENTS.md`** at the repo root for full conventions.

Key points:
- **Everything starts with a Dream in `docs/dreams/*.md`** — the raw aspiration; BMAD-method turns it into the spec (`bmad-spec`, or the planning chain for product scope).
- **The active spec is a BMAD artifact** in `_bmad-output/projects/<slug>/planning-artifacts/`.
- **Tier model (do not cross)**: Tier-0 Dream = `docs/dreams/`; Tier-1 = `docs/specs/` (**LEGACY**); Tier-2 spec & planning = `_bmad-output/projects/<slug>/planning-artifacts/`; Tier-3 execution output = `_bmad-output/projects/<slug>/implementation-artifacts/` (gitignored/local-only).
- A spec never belongs in a Tier-3 output dir.

## Mandatory Pre-PR Verification Protocol (ALWAYS EXECUTE LOCALLY)
Before opening or pushing any PR touching non-recipe paths (`src/`, `docs/`, `_bmad-output/`):

1. **Full Pre-Flight Suite:**
   `pixi run -e pyforge-guild pr-preflight`
2. **Station Test Suite:**
   `pixi run -e pyforge-<station> pyforge-<station>-test`
3. **Doctor & Dream Hygiene:**
   `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` (ensure new dreams are in `docs/dreams/README.md`)
4. **Coverage Gates:**
   `pixi run -e pyforge-steward python scripts/coverage_gates_ci.py --suites unit`
5. **Spec Surface Baseline Audit:**
   Audit with `pixi run -e pyforge-guild python -m pyforge.doctor.sources spec-surface` and re-stamp scoped baselines (`--write-baseline --spec <project>/<spec>`) for **all** touched spec surfaces after `git add`.
6. **PR Mechanics:**
   Add `maintenance` label for non-recipe PRs: `gh pr edit <n> --repo rxm7706/local-recipes --add-label maintenance`. Merge with `--merge`, never squash.
