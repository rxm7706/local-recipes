---
title: '109.2: Three pilot skills run without the estate environment'
type: 'docs'
created: '2026-10-21'
status: 'in-review'
baseline_revision: '53aed16fe1957ab340c6146cb7bf0c3f810c1746'
flag-exempt: docs-only
review_loop_iteration: 4
followup_review_recommended: false
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

### Fixes (2026-10-28, loop 1)

Every row above landed on PR #2274 on 2026-10-28; the story moves to `in-review` for the follow-up review the loop recommends.

- Row 1: each engine is named once by module (`pyforge.mason.engines.condalock`, `pyforge.mason.engines.pep517`, `pyforge.mason.engines.pixi`); no `engines/*.py` path and no "this repo" remain; each `steps.md` preamble says where the versions were read (the verifying host's `--version` on 2026-10-21). `test_pilot_skills_read_without_the_station_source` pins it.
- Row 2: `pixi` 0.81.0, the version `pixi --version` prints on the host and the `pixi.lock` pin, both re-read 2026-10-28, with that provenance in package `steps.md` step 0.
- Row 3: the test asserts `twine upload` and `pixi upload` with the "Do not run" sentence, `2026-10-21` and `404` in every pilot file, "temporary copy of the lockfile" in the environment steps and "`deptry` and `osv-scanner` are not a warden verdict" in the warden steps.
- Row 4: environment `steps.md` step 2 lists one `-f` per manifest in the station's discovery order (`pyproject.toml`, `environment.yml`, each `requirements*.txt`, `pixi.toml`) with the substitution for each shape; `conda-lock` exits non-zero on a missing file.
- Row 5: a "0. Install the published tools" step in each runbook (PyPI and conda-forge names: `conda-lock`, `build` / `python-build`, `pixi`, `deptry`, `osv-scanner`) and the `[build-system]` backend precondition on `pyproject-build --no-isolation` (`BackendUnavailable`). `test_pilot_steps_install_the_published_tools_first` pins step 0 before step 1.
- Row 6: a "Before you start" line names the unpublished packages and the gated steps before step 0; each gated step heading carries "(waits on `pyforge-<station>`)". AC2 and AC6 hold.
- Row 7 (decided): the provenance note moved to each `listing.yaml` header comment (the card keeps its one line); the verified versions live in `steps.md` only, and each `SKILL.md` says so; the package upload rule and the ship commands are one "Upload" section at the end of package `SKILL.md`.

## Review (2026-10-28, independent, loop 2)

Verdict: failed, narrowly. Every loop-1 row is closed in the tree (the verifier's table below), the Verification command exits 0, and the six files now read without the station source. Two findings send the story back: the environment runbook's new substitution list names two manifests `conda-lock` cannot parse, so a reader who follows it runs a failing command, and the pixi version is pinned by the test as a number the implementer typed rather than read from the lock, the drift row 2 found. The structure rows are editorial and do not block. Source: five lenses (adversarial, edge-case-hunter, verification-gap, structure, tea-test-review) run as fresh subagents over `git diff 0135f82e20..aa964e0ceb`, plus an independent row verifier that read the tree against the loop-1 table without the § Fixes text. Line numbers are `aa964e0ceb`'s.

### Loop-1 rows

| # | Verdict | Evidence |
|---|---|---|
| 1 | closed | `grep -rn "engines/" docs/foundry/marketplace/skills/` and `grep -rni "this repo"` both exit 1; dotted modules at environment `SKILL.md:45`, `steps.md:4,37`, package `SKILL.md:37,45`, `steps.md:4,44,53`; provenance line in each `steps.md` preamble; `test_pilot_skills.py:74-85`. |
| 2 | closed | package `steps.md:21-24` reads 0.81.0; host `pixi --version` 0.81.0; `pixi.lock:263` pins `pixi-0.81.0`; `test_pilot_skills.py:105`. See row 9 below for the test's shape. |
| 3 | closed | `test_pilot_skills.py:55,60-61,67,70-71` assert the AC3–AC6 sentences; run exits 0. |
| 4 | closed as asked | environment `steps.md:39-48`: one `-f` per manifest in the station's order, four substitutions, "exits non-zero on a file that is not there". See row 8 below: two of the substitutions name manifests the tool cannot read. |
| 5 | closed | `## 0. Install the published tools` at environment `steps.md:13-18`, package `:12-24`, warden `:12-17`; `BackendUnavailable` at package `steps.md:17-20`; `test_pilot_skills.py:95,100,103-108`. |
| 6 | closed | `**Before you start.**` before `## 0.` in all three (`test_pilot_skills.py:96-98`); "(waits on …)" tags at environment `:20,53`, package `:26,56`, warden `:19`. |
| 7 | closed | Provenance note in each `listing.yaml:3-4`; versions absent from every `SKILL.md` (`test_pilot_skills.py:82-85`); package `SKILL.md:48-64` is one `## Upload` block. |

### New findings

| # | Lens | Finding | Required fix |
|---|---|---|---|
| 8 | edge-case-hunter | Environment `steps.md:40-48` tells the reader to add `-f requirements.txt` and `-f pixi.toml` "in the discovery order above". `conda-lock` parses `environment.yml`, `pyproject.toml` and `meta.yaml` only: probed, `conda-lock lock -f pixi.toml` exits 1 with a YAML `ParserError` and `-f requirements.txt` with an `AttributeError`, even when the file exists. The station's own discovery hands those two to the engine, so the runbook copied a station defect into a command the no-AI reader types. | Limit the written substitutions to `pyproject.toml` and `environment.yml` (and both); say that a `requirements*.txt` or `pixi.toml` beside them is not a `conda-lock` input and that the station engine fails on them today. Add a negative assertion in `test_pilot_skills.py` that neither `-f requirements` nor `-f pixi.toml` appears in the environment steps. |
| 9 | verification-gap | `test_pilot_skills.py:105` asserts the literal `` `pixi` 0.81.0``, the number the implementer typed; nothing reads `pixi.lock`, so the next estate refresh that moves pixi leaves `steps.md` claiming a version "the local-recipes `pixi.lock` pins" that it no longer pins, with the test green. | Derive the version in the test (`re.search(r"/linux-64/pixi-(\d+\.\d+\.\d+)-", (repo_root() / "pixi.lock").read_text())`) and assert `f"`pixi` {version}" in package`; keep the `0.82.0` negative. |
| 10 | structure (editorial, non-blocking) | Package `SKILL.md` `## Upload` (`:48-64`) sits after `## Until that package is published`, so the unavailable station command follows the fallback that runs today, and the file is the one pilot whose H2 set differs from `templates/SKILL.md`. | Move it above, as `### Upload` under `## When pyforge-mason is installed` (or an H2 directly after it). |
| 11 | structure (editorial, non-blocking) | Environment `SKILL.md:43-60` repeats `steps.md:37-51,59-63` verbatim (the argv, the `-f`/`-p` rules, the temporary-copy sentence); package `SKILL.md:40-42` repeats the `BackendUnavailable` precondition. Package `steps.md:21-24` carries reviewer provenance ("what the local-recipes `pixi.lock` pins, both re-read on 2026-10-28") inside the portable runbook, the category row 7 moved out. | Condense each `SKILL.md` to the argv, "one `-f` per manifest — `steps.md` step 2", and the one `--check-input-hash` rule; condense the pixi bullet to "`pixi` 0.81.0 (re-read 2026-10-28)". |
| 12 | structure (editorial, non-blocking) | The ~55-word install-orientation paragraph (both directories, the matrix caveat) is repeated in `templates/SKILL.md:14-20` and each pilot `SKILL.md`, read by the teammate's tool after install; the card and README hold the same text for the human before install. | Decide: condense `SKILL.md` to "Marketplace id `scope/slug`. The human runbook is [steps.md](steps.md); verified tool versions live there." and leave the paths to the card and README, or keep the duplicate deliberately. |
| 13 | tea-test-review (advisory) | `test_pilot_skills_name_the_commands_that_were_verified` asserts across all three pilots in one test, so the first failing assertion masks the rest. | One test per skill and a parametrized test over `_texts()` for the per-file `404` + `2026-10-21` rule. |

### Fixes (2026-10-28, loop 2)

Every loop-2 row landed on PR #2274 on 2026-10-28; the story moves to `in-review`.

- Row 8: environment `steps.md` step 2 offers only `pyproject.toml` and `environment.yml` as `-f` substitutions and says a `requirements.txt` or `pixi.toml` is not a `conda-lock` input (the station's discovery still hands them to the engine, and step 1 inherits that failure until `pyforge-mason` fixes it); `SKILL.md`'s project-directory line names the two parseable manifests. `test_environment_steps_name_the_verified_commands` refuses `-f requirements` and `-f pixi.toml`.
- Row 9: `test_pilot_steps_install_the_published_tools_first` reads the pixi version from `pixi.lock`'s `linux-64` pin and asserts the runbook states that one.
- Row 10: package `SKILL.md`'s Upload block is `### Upload` under `## When pyforge-mason is installed`, so its H2 set matches `templates/SKILL.md`.
- Row 11: environment `SKILL.md` keeps the argv, defers the substitutions and the `-p` rule to `steps.md` step 2, and keeps the one `--check-input-hash` rule; package `SKILL.md` defers the backend precondition to step 0; the pixi bullet reads "`pixi` 0.81.0 (re-read 2026-10-28)".
- Row 12 (decided): each `SKILL.md` and the template keep the two install directories and drop the tool-matrix caveat; the card and the README hold which directory each tool reads.
- Row 13: one test per skill (`test_environment_steps_name_the_verified_commands`, `test_package_steps_name_the_verified_commands`, `test_warden_scan_steps_name_the_verified_commands`) and a parametrized `test_every_pilot_file_records_the_404_and_its_date`.

## Review (2026-10-28, independent, loop 3)

Verdict: passed. Every loop-2 row is closed in the tree (the verifier's table below); the six pilot files hold the commands the acceptance criteria name, read without the station source, and the test suite pins each criterion's wording and the lock's pixi version. Three editorial rows remain and do not block: two are one-line pointer errors the loop-2 rewrite introduced in 109.2's files, one is duplication; the 109.3 loop-3 pass, which edits the same README and cards, carries them. The story stays `in-review` for the operator's ledger flip; no further review loop is recommended. Source: five lenses (adversarial, edge-case-hunter, verification-gap, structure, tea-test-review) as fresh subagents over `git diff d2702f1f8f..80d46a5f31`, plus an independent row verifier reading the tree against the loop-2 table without the § Fixes text. Line numbers are `80d46a5f31`'s.

### Loop-2 rows

| # | Verdict | Evidence |
|---|---|---|
| 8 | closed | environment `steps.md:39-45` offers `pyproject.toml`, `environment.yml` and both; `:47-51` "not a `conda-lock` input"; `grep -c -- '-f requirements\|-f pixi.toml'` → 0; `test_pilot_skills.py:57-59` refuses both; 13 passed. |
| 9 | closed | `test_pilot_skills.py:119-124` reads the `linux-64` pin from `pixi.lock` (`:263` pins 0.81.0) and asserts the runbook states it. |
| 10 | closed | package `SKILL.md:20` installed section → `:30` `### Upload` → `:48` until-published → `:62` what-not; the H2 set matches `templates/SKILL.md`. |
| 11 | closed | environment `SKILL.md:44-52` keeps the argv and defers the substitutions and the `-p` rule to step 2; package `SKILL.md:55-56` defers the backend precondition to step 0; package `steps.md:21` reads "`pixi` 0.81.0 (re-read 2026-10-28)". |
| 12 | closed (hybrid) | The matrix caveat condensed to a pointer in each `SKILL.md` and the template; the two install paths stay. See row 14 for the pointer. |
| 13 | closed | `test_pilot_skills.py:48,62,71` one test per skill; `:80-84` parametrized over `_texts()` for the `404` + `2026-10-21` rule. |

### New findings (editorial, non-blocking)

| # | Lens | Finding | Required fix |
|---|---|---|---|
| 14 | structure | Each pilot `SKILL.md` (environment `:13-16`, package `:12-15`, warden `:13-16`) and `templates/SKILL.md:14-17` end the install paragraph with "Which directory each tool reads is on the card and in the README": inside an installed folder or the release zip there is no card and no README, and the tool reading `SKILL.md` after install does not need the per-tool directory. | Cut the sentence (or link the card URL once `/marketplace/` is live). |
| 15 | structure | environment `steps.md:47-51` says "the station's discovery hands those files to the engine today, so step 1 inherits that failure": step 1 on this runbook is `--help`, which discovers nothing; the engine step (148 words, three times any other) carries a note about a command it does not run. | Move the station-defect sentence into **Before you start** (which already lists what waits on `pyforge-mason`); step 2 keeps "not a `conda-lock` input: do not pass it with `-f`" and the `pip:` guidance. |
| 16 | structure | package `SKILL.md:54-56,58-60` and warden `SKILL.md:42-44` repeat their `steps.md` sentences verbatim (the console-script note, "not a pixi environment run", the engines' stdout); row 11 landed on environment only. The `### Upload` block's three closing sentences repeat `steps.md` step 4. | Condense each § Until to the argv plus "`steps.md` step N"; trim the Upload block's repeats. |

### Fixes (2026-10-28, loop 3)

The three editorial rows landed on PR #2274 on 2026-10-28 with the 109.3 loop-3 pass; the story stays `in-review` for the operator's ledger flip.

- Row 14: the sentence "Which directory each tool reads is on the card and in the README" is cut from the three pilot `SKILL.md` and `templates/SKILL.md`; `test_pilot_skills_read_without_the_station_source` asserts its absence.
- Row 15: the station-defect note moved into environment `steps.md`'s **Before you start** ("When `pyforge-mason` is published, its `lock` still hands a `requirements.txt` or `pixi.toml` it discovers to `conda-lock`, which cannot parse them; step 2 says which manifests to keep"); step 2 keeps "not a `conda-lock` input: do not pass it with `-f`" and the `pip:` guidance. `test_the_environment_runbooks_station_defect_sits_before_the_steps` pins the order.
- Row 16: package `SKILL.md` § Until names the two argv with `steps.md` step 2 / step 0 / step 3 pointers, and its `### Upload` block ends with "What not to run from this skill is `steps.md` step 4"; warden `SKILL.md` § Until names the two probes with `steps.md` step 2. AC2–AC6 and the 404 + date rule still hold (13 passed).

## Review (2026-10-29, independent, loop 4)

Verdict: passed (confirmation). The three loop-3 editorial rows are closed in the tree, checked by an independent row verifier without the § Fixes text: row 14 (the pointer sentence absent from the three pilot `SKILL.md` and the template; `test_pilot_skills.py:99-103`), row 15 (environment `steps.md:11-13` carries the discovery note in **Before you start**, step 2 `:49-52` keeps the two guidances; `test_pilot_skills.py:106-116`), row 16 (package `SKILL.md:47-55` and warden `SKILL.md:40-43` are argv plus `steps.md` pointers). The Verification command exits 0 (14 passed). One editorial residue, carried by 109.3's loop-4 row 79 and not blocking: environment `SKILL.md:48-52` still repeats `steps.md` step 3 (the temporary-copy sentence) and package `SKILL.md:41-44` still repeats step 4's after-`--yes` sentence. The story stays `in-review` for the operator's ledger flip; no further review loop is recommended for 109.2 itself. Source: the loop-4 structure lens and row verifier over `git diff c05521b877..636258ec79`.

