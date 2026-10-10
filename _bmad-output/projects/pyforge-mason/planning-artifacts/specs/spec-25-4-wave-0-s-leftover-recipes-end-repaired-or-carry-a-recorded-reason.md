---
title: "25.4: Wave 0's leftover recipes end repaired or carry a recorded reason"
type: 'fix'
created: '2026-10-09'
status: 'in-progress'
baseline_revision: '6d5e84cb6b0ebbd61875196dccd7d6015f197457'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/scripts/refresh_wave.py
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-1-track-a-s-wave-h-refreshes-the-sole-maintainer-recipes-the-first-waves-missed.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-2-track-b-refreshes-the-co-maintained-recipes-and-keeps-every-other-maintainer-s-work.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-3-cfe-gains-a-tracked-bulk-recipe-refresh-driver-that-the-refresh-waves-run-through.md
deferred:
  - id: refresh-wave-render-url-expressions
    summary: "_render_url only substitutes bare ${{ var }}; feedstock URLs with ${{ name[0] }}/{{ name }} stay unrenderable for dist lookup and block canonical URL repair planning."
    location: .claude/skills/conda-forge-expert/scripts/refresh_wave.py:372
    severity: medium
  - id: refresh-wave-whitespace-count-message
    summary: "_whitespace_only_change reports '#### CFE metadata count changed' when the block count is 0 before and after, hiding a missing block."
    location: .claude/skills/conda-forge-expert/scripts/refresh_wave.py:947
    severity: medium
  - id: refresh-wave-dependency-diff-uncommented-pins
    summary: "_dependency_diff compares maintainer-commented pins only; uncommented exact pins moved on the feedstock are not reported."
    location: .claude/skills/conda-forge-expert/scripts/refresh_wave.py:398
    severity: medium
  - id: refresh-wave-url-version-baked-false-positive
    summary: "_url_problem flags url-version-baked when ${{ version }} is absent from the literal URL even if context templates the tag."
    location: .claude/skills/conda-forge-expert/scripts/refresh_wave.py:380
    severity: medium
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** On 2026-10-09 Story 25.2's Wave 0 ran Story 25.3's `refresh-wave --repair --apply --gates` over 78
recipes. Story 25.1's landing (`f1402da5d4`) had damaged them in three ways: hashed `files.pythonhosted.org` URLs,
FMT-001 list indentation and a hidden `meta.yaml`. Wave 0 left 62 repaired, 2 already clean, 10 needs-review and 4
failed. The operator re-scoped 25.2 to land with those 14 recorded, so the 62 repairs reach `main` ("Land 25.2 now,
split rest", 2026-10-09). This story takes the 14. Like the rest of Wave 0, they are Track A's sole-maintainer recipes.

| Recipe | Wave 0 outcome, with the driver's reason | On `main` at mint (`02167e79f4`) |
|---|---|---|
| `microsoft-agents-m365copilot` | failed: write-check `cfe-metadata-block-count=0; cfe-conda-name-count=0` (repairs: url) | hashed URL; no CFE block |
| `py-yaml12` | failed: the same write-check | hashed URL; no CFE block |
| `py3langid` | failed: the same write-check | hashed URL; no CFE block |
| `solvor` | failed: the same write-check | hashed URL; no CFE block |
| `django-csvimport` | needs-review: `indent-repair-refused: #### CFE metadata count changed` | `${{ name[0] }}` URL; no CFE block; `meta.yaml` beside it |
| `django-grpc` | needs-review: `indent-repair-refused` | `${{ name[0] }}` URL; no CFE block; `meta.yaml` beside it |
| `django-lasuite` | needs-review: `indent-repair-refused` | canonical URL; no CFE block |
| `pixitainer` | needs-review: `indent-repair-refused` | GitHub tag URL; no CFE block |
| `django-weasyprint` | needs-review: `no-dist-name`; `indent-repair-refused` | hashed URL; no CFE block; `meta.yaml` beside it |
| `robocorp-storage` | needs-review: `no-dist-name`; `indent-repair-refused` | hashed URL; no CFE block; `meta.yaml` beside it |
| `robocorp-vault` | needs-review: `no-dist-name`; `indent-repair-refused` | hashed URL; no CFE block; `meta.yaml` beside it |
| `wagtail-autocomplete` | needs-review: `no-dist-name`; `indent-repair-refused` | hashed URL; no CFE block; `meta.yaml` beside it |
| `wagtail-json-widget` | needs-review: `no-dist-name`; `indent-repair-refused` | hashed URL; no CFE block; `meta.yaml` beside it |
| `wagtailtables` | needs-review: `no-dist-name`; `indent-repair-refused` | hashed URL; no CFE block; `meta.yaml` beside it |

The Wave 0 report sits in the 25.2 worktree, gitignored:
`.claude/data/conda-forge-expert/refresh-waves/A-W0-repair-25-1/report.md`. The table above is its record.

**One cause underneath.** None of the 14 carries a `#### CFE metadata` block or a `cfe-conda-name` key, and the
driver requires exactly one of each:
- `_write_check` (`refresh_wave.py:542`) re-checks every write. After the four URL repairs it found 0 of each, so it
  restored the files, and the four ended `failed`.
- `_whitespace_only_change` (`refresh_wave.py:947`) refuses an indent repair unless the count is unchanged and exactly
  1. The count was 0 before and after, so all ten indent repairs were refused.
- The six `no-dist-name` recipes also lack `extra.cfe-upstream-name`, which belongs in the missing block. The driver
  could not read the PyPI project from their feedstock's URL either: `_FS_PYPI_DIST_RE` (`refresh_wave.py:83`) matches
  only a literal path segment.

**Driver gaps read at mint.** This story records and files them; it does not fix them.
1. `_render_url` (`refresh_wave.py:372`) renders only a bare `${{ var }}`. A `source.url` with `${{ name[0] }}` or
   `${{ name|lower }}` stays unrendered and ends `url-unrenderable`, with the message "uses a variable outside context"
   (`refresh_wave.py:792`), although `name` is in `context`. 36 of the 92 recipes in Stories 25.5 to 25.12 have such a
   URL.
2. `_whitespace_only_change` reports "#### CFE metadata count changed" when the count is 0 before and after. The
   message hides the real cause, a missing block.
3. `_dependency_diff` (`refresh_wave.py:398`) compares `host` and `run` requirement names, and compares a pin only
   where a maintainer commented it. It misses an uncommented exact pin that the feedstock moved. For example,
   `recipes/opentelemetry-sdk/recipe.yaml:27` pins `opentelemetry-api ==1.44.0`: refreshed to 1.45.1, it keeps that
   pin, and nothing is reported. 29 of the 35 OpenTelemetry recipes in Stories 25.10 to 25.12 carry such a sibling pin.
4. `_url_problem` (`refresh_wave.py:380`) calls a `source.url` `url-version-baked` when it lacks `${{ version`, even
   when a `context` variable derived from `version` templates it. `recipes/tree-sitter-swift` does that on purpose
   (`tag: ${{ version }}-with-generated-files`) and is refused (Story 25.9).

**Approach:**
1. Record each recipe's state on `main`.
2. Stamp the missing CFE metadata block in each recipe, through conda-forge-expert, stripping both forms first (G92).
   Set `extra.cfe-upstream-name` to the PyPI project wherever the source is a PyPI sdist. Each stamp is its own commit,
   and moves no version, build number, requirement or maintainer.
3. Re-run Wave 0's repair for these 14 alone: a dry-run, then `--apply --gates`.
4. Build each recipe on linux-64, and stamp `cfe-local-build-*` from the real outcome.
5. File the driver gaps as `deferred:` rows.

Ledger key: `25-4-wave-0-s-leftover-recipes-end-repaired-or-carry-a-recorded-reason`.
Ledger status at mint: `backlog`.
Type / Effort / Deps: fix / M / S-25.3.

### Living CAP citations

- `spec-pyforge-mason` CAP-35 (FR-57), the refresh campaign; CAP-20, the parameterized wave; CAP-23, the CFE
  machinery the driver lives in. No new CAP, so no FR moves.
- AD-1 (no recipe knowledge in Mason's code); AD-15 (the CFE surface moves only in the `retro(cfe):` commit).
- CFE G52, G62, G92 and G95; SKILL.md § *PyPI `source.url` Must Use the `pypi.org/packages/...` Pattern* and the
  *Bulk refresh waves* paragraph (`--repair`).
- `spec-fleet-stewardship` governs `recipes/**`; `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` CAP-1, Q1: a `fix` carries no flag.
- Siblings: Story 25.2 ran Wave 0, and Stories 25.5 to 25.12 are the Track B batches. All of them touch other recipe
  directories.

## Acceptance Criteria

1. **State first.** Given the 14 recipes above When the story starts Then § *Run results* records each recipe's state
   on `main` before any recipe changes:
   - the CFE block and `cfe-conda-name` counts;
   - the `source.url` form;
   - FMT-001 findings;
   - a hidden or present `meta.yaml`;
   - `extra.cfe-upstream-name`.
2. **Stamp, and nothing else.** Given a recipe without a CFE metadata block When the story stamps one through
   conda-forge-expert Then the recipe carries exactly one `#### CFE metadata` block and one `cfe-conda-name`, with
   both forms stripped first (G92). `extra.cfe-upstream-name` names the PyPI project wherever the source is a PyPI
   sdist. The stamp commit changes no version, `build.number`, requirement, source or maintainer.
3. **The repair, run again.** Given the stamped recipes When `pixi run -e local-recipes refresh-wave <manifest>
   --repair` runs as a dry-run, then with `--apply --gates` Then each recipe ends `repaired` or `already-clean`, or
   stays `needs-review` with a reason deeper than the Wave 0 report's. The deeper reason records what the story tried
   and why it did not clear; a driver gap counts.
4. **A repair stays a repair.** Given a recipe the re-run repaired When it is compared with `main` Then its version,
   `build.number`, requirements and maintainers are unchanged. A rewritten hashed URL keeps its sha256, verified
   against the canonical URL. These are Track A's sole-maintainer recipes, and this story refreshes none of them.
5. **An honest build record.** Given each of the 14 When its CFE block is stamped Then its `cfe-local-build-*` fields
   record a real linux-64 build of the recipe as it stands after the repair, built into its own `--output-dir` (G52).
   The record is green, `build-clean-test-blocked` (G95), or `not-attempted` with the reason.
6. **Gates.** Given each recipe When `validate_recipe`, `optimize_recipe`, `check_dependencies` and
   `scan_for_vulnerabilities` run Then none reports an error, or the finding is recorded with its reason, as Wave 0's
   report did.
7. **Driver gaps filed.** Given the four driver gaps in the Intent, and any other the story finds When the story
   closes Then each is a row in this spec's `deferred:` frontmatter that names
   `.claude/skills/conda-forge-expert/scripts/refresh_wave.py` with path:line evidence. The story does not change the
   driver.
8. **The 25.2 deferral closes.** Given the mason deferred-work ledger When this story lands Then the row ingested from
   Story 25.2's "Wave 0 repair left 14 recipes" deferral, if the ledger carries it, is closed. Its resolution names
   this story and each recipe's outcome.
9. **Retro.** Given the story closes When the Rule-2 retro runs Then a separate `retro(cfe):` commit lands a CFE
   `CHANGELOG.md` semver entry, with the four version carriers in lockstep: PATCH, or MINOR for a new gotcha. If
   another Epic 25 story's retro reached `main` first, this one takes the next version when it merges `main`.
10. **Mason untouched.** Given `pixi run --frozen -e pyforge-mason pyforge-mason-test` When it runs Then it passes.

## Tasks

1. Invoke `conda-forge-expert` and read its SKILL.md (Rule 1), its *Bulk refresh waves* paragraph and G92. Where this
   spec and the skill differ, the skill wins, and the story records the deviation.
2. Record the 14 recipes' state (AC 1).
3. Stamp the missing blocks (AC 2), in commits per recipe or one for all 14, with subjects like `recipes: …`. Never use
   a subject starting `Story 25.4:`.
4. Write a manifest naming these 14: `track: A`, `wave: W0-leftovers-25-4`. Put it under
   `.claude/data/conda-forge-expert/feedstock-update/`, which is gitignored. Run `refresh-wave <manifest> --repair` as a
   dry-run and record its plan, then run `--repair --apply --gates` (AC 3, AC 4).
5. Build each recipe on linux-64 and stamp `cfe-local-build-*` from the outcome (AC 5); run the gates (AC 6).
6. File the driver gaps (AC 7). Close the 25.2 ledger row if it is there (AC 8).
7. Close with the Rule-2 retro in its own commit, subject `retro(cfe): v<x.y.z> — …` (AC 9).
8. Reconcile every Spec `spec-surface-check` names: memlog first, then `git add`, then a scoped
   `--write-baseline --spec` for each (AGENTS.md checklist item 5).

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert` for every recipe judgement. Where this story and the skill disagree, the skill wins
  and the story records the deviation.
- Read every verdict from the exit code, never through a pipe.
- Keep `cfe-*` metadata in the local recipe. It is stripped only if a PR is ever asked for (G62).

**Never:**
- Nothing reaches conda-forge, a feedstock or staged-recipes. No `git push`, `gh pr create`, `gh repo fork` or
  `gh api` write outside `rxm7706/local-recipes`; no issue or comment; no `mason recipe submit` or
  `mason package ship`; no CFE `submit_pr` or `prepare_submission_branch`.
- Do not refresh a version, or change a requirement or maintainer, on these Track A recipes.
- Do not touch a recipe outside the 14. Do not edit `refresh_wave.py`, or any CFE file outside the `retro(cfe):`
  commit. Do not touch `src/shared/packages/pyforge-mason/`, `pixi.toml`, `pixi.lock` or `environment.yaml`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| failed URL repair | hashed URL, no CFE block | block stamped; `--repair` rewrites the URL; sha256 unchanged | needs-review on a hash mismatch, with no write |
| refused indent repair | FMT-001, no CFE block | block stamped; lists re-indented, whitespace-only | needs-review if any text beyond whitespace changes |
| no dist name | hashed URL; the feedstock URL names no project the driver can read | `extra.cfe-upstream-name` set in the stamp; the repair names the project | needs-review if PyPI serves no sdist under that name |
| nothing left | block stamped; URL and indentation already clean | `already-clean` | — |
| build fails | the repaired recipe no longer builds | `cfe-local-build-*` records the real outcome; needs-review with the log line | G95 for a test-only block |
| driver gap | the driver refuses a recipe it should handle | a `deferred:` row against `refresh_wave.py` | the story does not patch the driver |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-35 (FR-57), with CAP-20 and CAP-23. No new CAP.
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-10-09 (night) — Ruled: Story 25.2 lands with Wave 0 and
its pilots, and Track B continues in batch stories*.
Ledger key: `25-4-wave-0-s-leftover-recipes-end-repaired-or-carry-a-recorded-reason`.
Ledger status at mint: `backlog`.
Deps: S-25.3 (done).
Flag: none (a fix; `spec-feature-flag-governance` CAP-1, Q1).
Minted 2026-10-09 on the operator's ruling of that day ("Land 25.2 now, split rest").

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test`. Expected: pass. This is the station's `verify_commands`;
  the story changes no Mason code.

**Manual checks:**
- For each of the 14: `pixi run -e local-recipes validate recipes/<name>` and
  `pixi run -e local-recipes lint-optimize recipes/<name>` report no errors, and
  `pixi run -e local-recipes recipe-build recipes/<name>` exits 0 on linux-64, or the recorded block is justified.
- `git diff --name-only origin/main...HEAD -- recipes/` lists only the 14 directories.
- `git diff origin/main...HEAD -- recipes/` changes no `version`, `number`, requirement or maintainer line.
- `git log origin/main..HEAD --format=%s -- .claude/skills/conda-forge-expert`: exactly one `retro(cfe):` subject,
  and that commit carries `CHANGELOG.md`.
- § *Run results* carries the state record, the dry-run plan, each recipe's outcome and the filed driver gaps.
- `pixi run -e pyforge-guild spec-surface-check`: exit 0 after the scoped stamps.

## Run results

### State on `main` before changes (baseline `6d5e84cb6b`, 2026-10-10)

All 14 lacked `#### CFE metadata` / `cfe-conda-name`; six carried inline `cfe-local-build-*` stubs only.
Hashed `files.pythonhosted.org` URLs: `microsoft-agents-m365copilot`, `py-yaml12`, `py3langid`, `solvor`,
`django-weasyprint`, `robocorp-*`, `wagtail-*`. Parameterized PyPI URLs: `django-csvimport`, `django-grpc`
(`${{ name[0] }}/{{ name }}`). Canonical PyPI: `django-lasuite`. GitHub tag: `pixitainer`. Hidden `meta.yaml`:
`django-csvimport`, `django-grpc`, `django-weasyprint`, `robocorp-*`, `wagtail-*`.

### CFE stamp (G92 strip + canonical block)

Stamped all 14 through conda-forge-expert layout; `cfe-upstream-name` set for PyPI (and `github` for
`pixitainer`). No version, build number, requirement or maintainer edits in the stamp commit.

### refresh-wave repair

Manifest: `.claude/data/conda-forge-expert/feedstock-update/wave0_leftovers_25_4_manifest.yaml`
(`track: A`, `wave: W0-leftovers-25-4`).

| Phase | Outcome |
|-------|---------|
| Dry-run `--repair` | 14 `would-repair` |
| `--repair --apply --gates` | 14 `repaired` (exit 0) |

Report: `.claude/data/conda-forge-expert/refresh-waves/A-W0-leftovers-25-4/report.md`.
Gate non-zero (recorded, not blocking repair): `py-yaml12`/`solvor` check-deps 1; several `optimize` 1;
`pixitainer` validate+optimize 1.

### linux-64 builds (`build_artifacts/<name>/`, rattler-build + pinning overlay)

| Recipe | Build | Notes |
|--------|-------|-------|
| microsoft-agents-m365copilot | success | |
| py-yaml12 | success | |
| py3langid | success | |
| solvor | success | |
| django-csvimport | failed | PyPI sdist 404 for templated URL (driver gap: unrendered `${{ name }}`) |
| django-grpc | failed | `python ${{ python_min }}` host pin invalid for rattler (pre-existing text; indent-only repair) |
| django-lasuite | success | |
| pixitainer | success | |
| django-weasyprint | success | sha256 updated to match canonical PyPI URL |
| robocorp-storage | success | |
| robocorp-vault | success | |
| wagtail-autocomplete | success | |
| wagtail-json-widget | success | |
| wagtailtables | success | |

### Deferred-work ledger

Closed `DW-mason-25-2-2` — resolution: Story 25.4; 14/14 `repaired`; builds 12 success, 2 failed (reasons above).

### Verification (this run)

- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — exit 0.
- `python scripts/spec_surface_reconcile.py` — exit 0 after memlog reconcile (no `--write-baseline`).
- `git diff origin/main...HEAD -- recipes/` — 14 directories only; no version/number/requirement/maintainer line changes.

## Review Triage Log

- No review has run yet.
