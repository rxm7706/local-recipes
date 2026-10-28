---
title: '109.2: Three pilot skills run without the estate environment'
type: 'docs'
created: '2026-10-21'
status: 'in-progress'
baseline_revision: '53aed16fe1957ab340c6146cb7bf0c3f810c1746'
flag-exempt: docs-only
review_loop_iteration: 1
followup_review_recommended: true
context:
  - .claude/skills/mason-environment/SKILL.md
  - .claude/skills/mason-package/SKILL.md
  - .claude/skills/pyforge-warden/active/pyforge-warden/SKILL.md
  - docs/foundry/marketplace/skills/mason/environment/SKILL.md
  - docs/foundry/marketplace/skills/mason/package/SKILL.md
  - docs/foundry/marketplace/skills/warden/scan/SKILL.md
  - src/shared/packages/pyforge-steward/tests/unit/test_pilot_skills.py
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `@mason/environment`, `@mason/package`, and `@warden/scan` as they live under `.claude/skills/` assume this repository's pixi environments. A teammate cannot follow them in their own project.

**Approach:** Portable copies under `docs/foundry/marketplace/skills/<scope>/<slug>/`, each with `SKILL.md` and `steps.md`. Commands are the ones the station engines assemble, verified 2026-10-21. Unpublished `pyforge-mason`, `pyforge-warden`, and `pyforge-core` are named, with the 404 check. The estate skill files are not edited.

## Acceptance criteria

1. Each of the three folders contains `SKILL.md` and `steps.md`.
2. Neither file contains `pixi run -e` or `pixi run --frozen -e`.
3. Environment steps include `conda-lock lock -f pyproject.toml --lockfile conda-lock.yml` and say the station check uses a temporary copy. They do not include the paper prototype's `env.lock` sample command. `steps.md` is the runbook the Pages card renders.
4. Package steps include `pyproject-build --no-isolation` and `pixi build --output-dir dist`, and tell the reader not to run `twine upload` or `pixi upload`.
5. Warden steps include `warden scan .` and say `deptry` and `osv-scanner` are not a warden verdict.
6. Each file records that the station package was unpublished on 2026-10-21.

## Boundaries

- Do not change `.claude/skills/mason-environment/`, `.claude/skills/mason-package/`, or `.claude/skills/pyforge-warden/`.
- Do not publish a package. Do not add a recipe.

</intent-contract>

## Verification

**Commands:**

- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_pilot_skills.py -q` — expected: exit 0.

**Manual checks:**

- The versions in `steps.md` match a fresh `--version` of `conda-lock`, `build`, `pixi`, `twine`, `deptry`, and `osv-scanner` on the day the story is reviewed. A mismatch is a doc edit, not a new command.

## Review (2026-10-28, independent)

Verdict: failed. The six pilot files hold the commands the acceptance criteria name and `test_pilot_skills.py` passes, but the review found the portable copies still lean on this repository, one verified version that no environment here reproduces, and tests that cannot fail on the wording AC4 and AC6 protect. The story returns to in-progress (review loop iteration 1). Every row is open: the fix column is what the review asks for, not what landed. The reviewer did not implement this story. Source: the 2026-10-28 five-lens review of PR #2274 (adversarial, edge-case-hunter, verification-gap, structure, tea-test-review) against this spec, Epic 109 and `analysis-against-main-2026-10-27.md`; "re-verified" marks a claim the reviewer checked in the tree, the rest is the lens's reading of the diff.

| # | Lens | Finding | Required fix |
|---|---|---|---|
| 1 | adversarial | The portable copies cite station source files by bare relative path (`engines/condalock.py` in environment `steps.md:25`; `engines/pep517.py` in package `SKILL.md:46` and `steps.md:27`; `engines/pixi.py` in package `SKILL.md:51` and `steps.md:37`) and say "this repo" (environment `SKILL.md:51`, `steps.md:4`). A teammate's installed copy has neither, and the PR template's own check says `steps.md` reads without the station source. Re-verified. | Name the module once (`pyforge.mason.engines.condalock`, `pyforge.mason.engines.pep517`, `pyforge.mason.engines.pixi`), drop "this repo", and say where each version was read ("host `pixi --version` on 2026-10-21"). |
| 2 | adversarial | Package `steps.md:38` and `SKILL.md:52` claim `pixi` 0.82.0. `pixi.lock` pins 0.81.0 on every platform and the host runs 0.81.0, so the manual check ("versions match a fresh `--version`") cannot reproduce the claim. Re-verified. | Record the version a fresh `--version` prints, with its provenance, or re-verify on a host that has 0.82.0 and say so in `steps.md`. |
| 3 | adversarial, verification-gap | `test_pilot_skills.py` accepts `"Do not run them" or "Do not upload"` and `"404" or "Unpublished"`, so it pins neither the `twine upload` / `pixi upload` names AC4 requires nor the `2026-10-21` date AC6 requires in each file. AC3's "the station check uses a temporary copy" and AC5's "`deptry` and `osv-scanner` are not a warden verdict" are asserted by no test; the test asserts the command names only. Re-verified. | Assert `"twine upload" in package and "pixi upload" in package`, `"2026-10-21" in text` for every pilot file, the temporary-copy sentence in the environment steps, and the not-a-verdict sentence in the warden steps. |
| 4 | edge-case-hunter | Environment `steps.md:30` hard-codes `conda-lock lock -f pyproject.toml --lockfile conda-lock.yml` while `SKILL.md:21` says the project may hold `pyproject.toml`, `environment.yml`, or `pixi.toml`. A literal reader with no `pyproject.toml` runs a command that fails, and the runbook gives no substitution. | One `-f <manifest>` per manifest the project holds, written as the substitution the reader makes; `conda-lock` exits non-zero on a missing file. |
| 5 | edge-case-hunter | No step installs the published tools. A no-AI-tool reader on a fresh machine meets `command not found` (`conda-lock`, `pyproject-build`, `pixi`, `deptry`, `osv-scanner`) or `BackendUnavailable` (`pyproject-build --no-isolation` needs the `[build-system]` backend installed) at the first published step. | A "0. Install the published tools" step in each runbook naming each tool's install source, and the backend precondition on `pyproject-build --no-isolation`. |
| 6 | structure | The **Unpublished.** callout sits after the station-command block in all three `steps.md` (environment lines 19–21, package 16–17, warden 29–32). The reader types step 1, it fails, then reads why; warden's reader passes three code blocks before learning none of them runs. | Move the callout to the preamble as a "Before you start" line naming the unpublished packages and the numbered steps that wait on them; each gated step keeps a one-line "waits on `pyforge-mason`" tag. AC2 and AC6 still hold. |
| 7 | structure (open question) | Reviewer provenance sits inside the teammate runbook: "The 2026-10-20 paper skill card is sample data. Its lock command is not this runbook." opens each `steps.md`, and the card prints the same sentence above the rendered steps, so the card shows it twice. Verified version strings are duplicated between each `SKILL.md` and its `steps.md` while the manual check names only `steps.md`. Package `SKILL.md` separates the upload rule (lines 54–57) from the ship commands it governs (lines 30–40). | Decide: move the provenance note to the `listing.yaml` header comment or the README; keep the verified versions in `steps.md` only; merge the package upload rule and its commands into one block. |
