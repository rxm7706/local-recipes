---
title: "25.17: Epic 25's recipes carry the build records their stories claim"
type: 'fix'
created: '2026-11-01'
status: 'backlog'
flag-exempt: recipe-build
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/feedstock-refresh.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/research/egm-audit-2026-11-01.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/scripts/refresh_wave.py
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-4-wave-0-s-leftover-recipes-end-repaired-or-carry-a-recorded-reason.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-6-track-b-batch-2-refreshes-django-fsm-log-through-import-linter.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-7-track-b-batch-3-refreshes-jhub-apps-through-niquests.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-8-track-b-batch-4-refreshes-ocrmypdf-through-pysqlite3.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-9-track-b-batch-5-refreshes-redshift-connector-through-zxing-cpp.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-14-wave-f-s-other-18-packages-are-built-by-their-feedstock-s-own-mirror.md
deferred: []
---

<intent-contract>

## Intent

**Problem:** the run tables of done Stories 25.4, 25.6, 25.7, 25.8, 25.9 and 25.14 report their recipes built, and
the recipes' own `cfe-local-build-*` records disagree. Read at `03a7aff5d9` (2026-11-01):

- Twelve record `cfe-local-build-status: failed`: `pillow-heif`, `django-silk`, `import-linter`, `grafana-client`,
  `fastmcp-slim`, `tree-sitter-php`, `vlmrun`, `wagtail`, `robocorp-workitems`, `StringZilla`, `django-grpc`,
  `django-csvimport`.
- `zxing-cpp` records `not-attempted`, with no reason.
- `langflow` records a `success` dated 2026-09-03, before the stories that moved it.
- 14 recipes share one `cfe-local-build-datetime`, `2026-10-10T08:35:31Z`, a stamp no single build wrote:
  `django-csvimport`, `django-grpc`, `django-weasyprint`, `django-lasuite`, `microsoft-agents-m365copilot`,
  `pixitainer`, `py3langid`, `py-yaml12`, `robocorp-storage`, `robocorp-vault`, `solvor`, `wagtail-autocomplete`,
  `wagtail-json-widget`, `wagtailtables`. Story 25.4 left three gate reds (`pixitainer`, `py-yaml12`, `solvor`) with
  no reason, and its AC 6 never ran the conda-smithy recipe-lint.

The run tables were written without reading each recipe's record back. Severity is Major, not Blocker: the records
are local and no gate reads them (contested in triage; settled with the skeptics).

Found by the EGM fleet audit of 2026-11-01 (marshal Story 113.7): **MAS-D-C1**, cluster
`mason-c08-epic25-build-records`. Residue:
`_bmad-output/projects/pyforge-mason/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:** rebuild, never re-stamp. Invoke `conda-forge-expert` first (Rule 1) and work in `-e local-recipes`, local
only. Rebuild each named recipe on linux-64 through
`pixi run -e local-recipes refresh-wave <manifest> --gates --build --report-dir <dir>`, so every `cfe-local-build-*`
field is written by its own build. Each recipe ends in CAP-35's outcome set (cluster `mason-c03`'s re-derive): a green
isolated linux-64 build; a recorded G95 block, which the operator ruled on 2026-11-01 is a local end state whose static
gate applies only before shipping; or `needs-review` with its reason. Correct the six run tables by appending, never by
rewriting.

Scope is Epic 25's recipes only: 495 recipes estate-wide record `failed` at `03a7aff5d9`, and they are not this
story's.

**Parked (operator ruling 2026-11-01):** L effort, recipe-factory work with its own CFE retro. It stays `backlog` and is
not built in the EGM landing PR.

Ledger key: `25-17-epic-25-s-recipes-carry-the-build-records-their-stories-claim`.
Ledger status at mint: `backlog`.
Type / Effort / Deps: fix / L / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-35 (the feedstock refresh campaign is Mason's), FR-57: every recipe in scope ends with its
  gates green and either a local build or a recorded G95 block.
- No new CAP. `spec-feature-flag-governance` CAP-1, Q1: a `fix` carries no flag; `flag-exempt: recipe-build` records
  the class, as the station's other recipe-build fixes do (Stories 22.1, 22.3, 22.4).
- AD-1, AD-15: no Mason package change; every CFE-surface edit lands in a `retro(cfe):` commit.

## Acceptance Criteria

1. **Builds write the records.** Given each named recipe (the twelve `failed`, `zxing-cpp`, `langflow`, and every
   recipe stamped `2026-10-10T08:35:31Z`; 26 at `03a7aff5d9`), When the story rebuilds it through `refresh-wave
   --gates --build`, Then every `cfe-local-build-*` field it carries was written by that build: `git log -p` shows no
   hand edit to those fields, and the datetime matches the build's report in `--report-dir`.
2. **Every recipe ends in the outcome set.** Then each recipe records a green linux-64 build, a G95 block with its
   reason, or `needs-review` with its reason. None ends `failed` or `not-attempted` without a reason.
3. **25.4's gate reds are explained.** Given `pixitainer`, `py-yaml12` and `solvor`, Then each carries the reason for
   its gate result, and the conda-smithy recipe-lint 25.4 AC 6 left out has run for each, its verdict recorded.
4. **Run tables corrected by appending.** Each of the six story specs gains a dated *Correction (Story 25.17)* section
   after its run table, naming each recipe's record before and after. No row of an existing table is rewritten, and no
   done story's status moves.
5. **Gates and maintainers.** Each rebuilt recipe passes `validate_recipe`, `optimize_recipe` and the CI-parity lint
   (G65), or records why not; every `recipe-maintainers` stays a superset of its feedstock's deployed list (G53).
6. **Local only.** No push, PR, fork, issue or comment outside `rxm7706/local-recipes`; no `mason recipe submit`,
   `mason package ship`, CFE `submit_pr` or `prepare_submission_branch`.
7. **Retro.** A `retro(cfe):` commit edits `.claude/skills/conda-forge-expert/SKILL.md` and `CHANGELOG.md` with a semver
   bump, teaching CFE to read a run table back against the recipe's own record before a story closes.
8. **Green.** `pixi run --frozen -e pyforge-mason pyforge-mason-test` passes.

## Boundaries & Constraints

**Always:**

- Invoke `conda-forge-expert` before any recipe edit; the skill wins where a story conflicts with it.
- Read every verdict from the exit code, never through a pipe.
- Build each recipe into an isolated output directory; never resolve a run requirement from a shared local channel
  (G52).
- After `git add`, stamp `spec-pyforge-mason` (which governs the CFE surface) with a scoped `--spec`, after its memlog
  names the paths.

**Never:**

- Write a `cfe-local-build-*` field by hand, or copy one recipe's stamp to another.
- Rebuild a recipe outside Epic 25's.
- Change `.claude/skills/conda-forge-expert/scripts/refresh_wave.py` except in a `retro(cfe):` commit, and only if a
  record field turns out not to be written by the build.
- Hand-edit any `SPEC.md` or `sprint-status-ledger.yaml`, or move a done story's status.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| builds green | `failed` record | `success`, its own build's datetime | — |
| host-blocked test | BCTB or platform block | G95 block recorded with its reason | local end state (ruling 2026-11-01) |
| still fails | build red after a CFE diagnosis | `needs-review` with the reason | — |
| shared stamp | `2026-10-10T08:35:31Z` | its own build's datetime | — |
| stale success | `langflow`, 2026-09-03 | rebuilt; current record | — |
| no reason | `zxing-cpp` `not-attempted` | built, or a recorded reason | — |

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-mason` CAP-35 (the feedstock refresh campaign is Mason's), FR-57. A fix, no new
  CAP.

Parent: CAP-35

- Dream: `docs/dreams/pyforge-mason.md` § Realization log, the 2026-11-01 entry (the EGM fleet audit).
- Audit finding carried: MAS-D-C1 (cluster `mason-c08-epic25-build-records`); residue
  `_bmad-output/projects/pyforge-mason/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Epic: Epic 25 (the feedstock refresh campaign), done; a new not-done story reopens it (doctor Story 41.5).
- Ledger key: `25-17-epic-25-s-recipes-carry-the-build-records-their-stories-claim`.
- Deps: —.
- Surface: `recipes/{pillow-heif,django-silk,import-linter,grafana-client,fastmcp-slim,tree-sitter-php,vlmrun,wagtail,robocorp-workitems,StringZilla,django-grpc,django-csvimport,zxing-cpp,langflow,solvor,pixitainer,py-yaml12,django-weasyprint,django-lasuite,microsoft-agents-m365copilot,py3langid,robocorp-storage,robocorp-vault,wagtail-autocomplete,wagtail-json-widget,wagtailtables}/recipe.yaml`;
  the six run-table story specs named in `context:` (an appended section each); the CFE retro surface
  (`.claude/skills/conda-forge-expert/{SKILL.md,CHANGELOG.md}` and its version carriers, and
  `.claude/skills/conda-forge-expert/scripts/refresh_wave.py` only if needed), committed alone as `retro(cfe): …`.
- Flag: none (a fix; `spec-feature-flag-governance` CAP-1, Q1); `flag-exempt: recipe-build`.
- Mode: parked at `backlog` (operator ruling 2026-11-01).
- Minted 2026-11-01 by marshal Story 113.7's landing PR, on the operator's acceptance of the audit's recommendations.

## Verification

**Commands:**

- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**

- `pixi run -e local-recipes refresh-wave <manifest> --gates --build --report-dir <dir>` — expected: a report row per
  recipe, each in the outcome set.
- `grep -l "2026-10-10T08:35:31Z" recipes/*/recipe.yaml` — expected: no output.
- `grep -H "cfe-local-build-status:" recipes/<name>/recipe.yaml` for each named recipe — expected: no `failed`, and
  no `not-attempted` without a recorded reason; every G95 block and `needs-review` carries its reason.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the scoped stamp.

## Auto Run Result

Status: backlog

Summary: not yet dispatched (parked by the operator's ruling of 2026-11-01).

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (marshal Story 113.7), finding MAS-D-C1, cluster
  `mason-c08-epic25-build-records`; fix under `spec-pyforge-mason` CAP-35, no new CAP; parked at `backlog`.

## Review Triage Log

- (none yet)
