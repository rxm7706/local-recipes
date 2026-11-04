---
title: "25.17: Epic 25's recipes carry the build records their stories claim"
type: 'fix'
created: '2026-11-01'
status: 'done'
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
deferred:
  - id: refresh-wave-mirror-fidelity-and-diagnosis-gaps
    summary: "refresh_wave's --rebuild path on an already-current recipe runs no C1/C2 meta.yaml action, no G53 union and no G96 diff; the driver never compares build.number, entry points, tests, about.license_file, conda-forge.yml or a recipe-folder CBC with the feedstock, reads only top-level requirements (multi-output recipes get no G96 diff), discards each build's output, files a clean build whose test pip check failed as failed, never cleans build_artifacts/<name> (G68) and dates its comment lines in UTC. Blocked on scope: Story 25.17's boundary allows a refresh_wave.py change only where a record field is not written by the build; each gap is its own story under spec-pyforge-mason CAP-35."
    location: .claude/skills/conda-forge-expert/scripts/refresh_wave.py:747
    severity: medium
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

## Run record (2026-11-01)

Driver: `refresh_wave.py` gained `--rebuild` (with `--apply`, a recipe that is already current is also gated and built,
so its `cfe-local-build-*` record is written by a build of the recipe as it stands), and each report row now carries the
`build.datetime` the build stamped. Manifest `_bmad-output/projects/pyforge-mason/implementation-artifacts/refresh-waves/25-17/manifest.yaml`
(`fastmcp-slim` mapped to `feedstock: fastmcp`). Three passes of `--apply --gates --build --rebuild --report-dir <that dir>`:
the first exposed the failures, the second re-ran the recipes fixed by the Build Failure Protocol, and the last
(`--force`) rebuilt all 26 so every record's datetime is in one `report.json`. Each build ran on linux-64 into its own
`build_artifacts/<name>/` (G52). After the last pass the four `cfe-local-build-*` fields of all 26 recipes match the
report's `build.status` and `build.datetime`; `grep -l "2026-10-10T08:35:31Z" recipes/*/recipe.yaml` prints nothing;
every `recipes/**/recipe.yaml` parses.

Result of the third pass: 25 `success`, 1 `failed` (`langflow`). None `not-attempted`. After the review follow-up below, all 26 record `success`. The table is the third pass; the follow-up rows supersede it for the eleven recipes rebuilt again.

| Recipe | Before (status, datetime, version) | After (status, datetime, version) | Outcome and reason | Gates (validate / optimize / check-deps / scan; lint) | Maintainers (G53) |
|---|---|---|---|---|---|
| pillow-heif | failed, 2026-10-10T13:58:48Z (1.8.0) | success, 2026-11-02T01:15:40Z (1.8.1) | refreshed 1.8.0 → 1.8.1; BFP: local-only patch drops setup.py's host `-I/usr/include` (multiarch host shadowed the sysroot); `run_test.py` restored from the feedstock | 0 / 0 / 1 / 0; lint clean | superset |
| django-silk | failed, 2026-10-10T11:35:41Z (5.6.0) | success, 2026-11-02T01:16:20Z (5.6.0) | green with no fix (the `failed` record was stale) | 0 / 1 (STD-002, TEST-002) / 0 / 0; lint clean | superset |
| import-linter | failed, 2026-10-10T11:43:45Z (2.15) | success, 2026-11-02T01:17:08Z (2.15) | green with no fix (the `failed` record was stale) | 0 / 1 (STD-002, TEST-002) / 0 / 0; lint clean | superset |
| grafana-client | failed, 2026-10-10T11:38:11Z (5.1.3) | success, 2026-11-02T01:17:47Z (5.1.4) | refreshed 5.1.3 → 5.1.4 (v0 `meta.yaml` mirrored, C1) | 0 / 1 (STD-002, TEST-002) / 0 / 0; lint clean | superset |
| fastmcp-slim | failed, 2026-10-10T11:36:52Z (4.1.0) | success, 2026-11-02T01:18:06Z (4.1.4) | refreshed 4.1.0 → 4.1.4 via manifest `feedstock: fastmcp` (no `fastmcp-slim-feedstock`) | 0 / 1 (TEST-001) / 0 / 0; lint clean | superset |
| tree-sitter-php | failed, 2026-10-10T14:52:32Z (0.25.1) | success, 2026-11-02T01:18:46Z (0.25.1) | BFP: license patch no longer applied at 0.25.1 (upstream fixed it); patch removed as the feedstock did | 0 / 0 / 0 / 0; lint clean | superset |
| vlmrun | failed, 2026-10-10T14:53:48Z (0.9.0) | success, 2026-11-02T01:19:37Z (0.9.0) | green with no fix (the `failed` record was stale) | 0 / 1 (PIN-001) / 0 / 1; lint clean | superset |
| wagtail | failed, 2026-10-10T14:55:20Z (8.0) | success, 2026-11-02T01:20:48Z (8.0.1) | refreshed 8.0 → 8.0.1 | 0 / 1 (DEP-002) / 0 / 0; lint clean | superset |
| robocorp-workitems | failed, 2026-10-10T14:43:04Z (1.5.1) | success, 2026-11-02T01:21:22Z (1.5.1) | green with no fix (the `failed` record was stale) | 0 / 1 (DEP-002, STD-002, TEST-002) / 0 / 0; lint clean | superset |
| StringZilla | failed, 2026-10-10T14:49:40Z (5.2.0) | success, 2026-11-02T01:22:34Z (5.3.2) | refreshed 5.2.0 → 5.3.2 (`meta.yaml` mirrored); BFP: test imported a `cli` package and declared entry points upstream dropped; now imports `stringzilla` with pip check, as the feedstock does | 0 / 1 (STD-002) / 1 / 0; lint clean | superset |
| django-grpc | failed, 2026-10-10T08:35:31Z (1.2.15) | success, 2026-11-02T01:23:09Z (1.2.20) | BFP: sdist URL 404 (hyphen vs underscore filename) and bare `python 3.11` host pin; URL literal, `.*` pins, G96 sync (poetry-core, grpcio-reflection, django <7); refreshed 1.2.15 → 1.2.20 | 0 / 1 (STD-002, TEST-002) / 0 / 0; lint clean | superset |
| django-csvimport | failed, 2026-10-10T08:35:31Z (3.3) | success, 2026-11-02T01:23:42Z (3.3) | BFP: sdist URL 404 (hyphen vs underscore filename); URL literal, sha256 unchanged | 0 / 1 (DEP-002, STD-002, TEST-002) / 0 / 0; lint clean | superset |
| zxing-cpp | not-attempted, none (3.1.1) | success, 2026-11-02T01:24:30Z (3.1.1) | first build (was `not-attempted` with no reason); green as it stands | 0 / 0 / 0 / 0; lint clean | superset |
| langflow | success, 2026-09-03T09:29:20Z (1.12.4) | failed, 2026-11-02T01:26:59Z (1.13.0) | third pass: refreshed 1.12.4 → 1.13.0 and re-mirrored from the feedstock; `langflow-base` failed its test pip check because cf `openinference-instrumentation-langchain` 0.1.80/0.1.81 declare looser conda depends than their wheels need (G36 / G77, first misread here as external skew); capped and green in the review follow-up | 0 / 1 (TEST-001) / 0 / 0; lint clean | superset |
| solvor | success, 2026-10-10T08:35:31Z (0.6.3) | success, 2026-11-02T01:27:46Z (0.6.3) | green; `jsmolic` re-merged (G53) | 0 / 0 / 1 / 0; lint clean | superset |
| pixitainer | success, 2026-10-10T08:35:31Z (0.9.0) | success, 2026-11-02T01:27:52Z (0.9.0) | green; body restored to the feedstock's indentation (whitespace only) to clear the CRM parse error | 0 / 1 (TEST-001) / 0 / 0; lint clean | superset |
| py-yaml12 | success, 2026-10-10T08:35:31Z (0.2.0) | success, 2026-11-02T01:29:44Z (0.2.0) | green; `jsmolic` re-merged (G53) | 0 / 0 / 1 / 0; lint clean | superset |
| django-weasyprint | success, 2026-10-10T08:35:31Z (2.6.0) | success, 2026-11-02T01:31:29Z (2.6.0) | green as it stands | 0 / 1 (STD-002, TEST-002) / 0 / 0; lint clean | superset |
| django-lasuite | success, 2026-10-10T08:35:31Z (0.0.30) | success, 2026-11-02T01:32:11Z (1.0.0) | G96 sync to the feedstock's 1.0.0 run set (deps moved to extras upstream); refreshed 0.0.30 → 1.0.0 | 0 / 0 / 0 / 0; lint clean | superset |
| microsoft-agents-m365copilot | success, 2026-10-10T08:35:31Z (1.10.0) | success, 2026-11-02T01:32:48Z (1.11.0) | refreshed 1.10.0 → 1.11.0 | 0 / 0 / 0 / 0; lint clean | superset |
| py3langid | success, 2026-10-10T08:35:31Z (0.4.0) | success, 2026-11-02T01:33:24Z (0.4.0) | green as it stands | 0 / 0 / 0 / 0; lint clean | superset |
| robocorp-storage | success, 2026-10-10T08:35:31Z (1.1.1) | success, 2026-11-02T01:33:57Z (1.1.1) | green as it stands | 0 / 1 (DEP-002, STD-002, TEST-002) / 0 / 0; lint clean | superset |
| robocorp-vault | success, 2026-10-10T08:35:31Z (1.4.1) | success, 2026-11-02T01:34:31Z (1.4.2) | refreshed 1.4.1 → 1.4.2 (`meta.yaml` mirrored) | 0 / 1 (DEP-002, STD-002, TEST-002) / 0 / 0; lint clean | superset |
| wagtail-autocomplete | success, 2026-10-10T08:35:31Z (0.12.1) | success, 2026-11-02T01:35:08Z (0.12.1) | green as it stands | 0 / 1 (STD-002, TEST-002) / 0 / 0; lint clean | superset |
| wagtail-json-widget | success, 2026-10-10T08:35:31Z (0.0.9) | success, 2026-11-02T01:36:08Z (0.0.9) | green as it stands | 0 / 1 (STD-002, TEST-002) / 0 / 0; lint clean | superset |
| wagtailtables | success, 2026-10-10T08:35:31Z (0.3.0) | success, 2026-11-02T01:36:47Z (0.3.0) | green as it stands | 0 / 1 (STD-002, TEST-002) / 0 / 0; lint clean | superset |

Gate readings. `validate` is 0 for all 26 and the CI-parity lint (`pixi exec --spec "conda-smithy>=2026.6.14"
conda-smithy recipe-lint --conda-forge`, on a copy without `meta.yaml`) exits 0 for all 26; its only notes are the
TEST-002 hint and, for `zxing-cpp`, a deprecated `azure.store_build_artifacts` that was a local leftover in its `conda-forge.yml`, not the feedstock's (re-mirrored in the review follow-up). The non-zero gates are
known classes, none a build blocker: `optimize` STD-002 (both `meta.yaml` and `recipe.yaml` on a v0-feedstock mirror,
expected, except on `django-csvimport`, whose feedstock is v1: its `meta.yaml` was stale and is removed in the review follow-up), TEST-002 (single `python_version`, as the feedstock writes it), DEP-002 (upstream's `python <4` bound), PIN-001
(`vlmrun`'s upstream-exact pins, kept for `pip check` since Story 25.9), TEST-001 on the three multi-output recipes (the
checker reads only top-level `tests:`, G29); `check-deps` 1 is the documented `cross-python_${{ target_platform }}` →
`cross-python_PLACEHOLDER` false miss; `vlmrun` `scan` 1 is OSV advisories against its upstream-exact `pillow ==11.3.0`.

Story 25.4's gate reds (AC 3):

- `pixitainer`: `validate` 1 was conda-recipe-manager 0.10.6 (conda-smithy 3.62.0's parser) raising
  `DuplicateKeyException` at the second output's `requirements:`, because two comment lines sat four columns deeper than
  their script items (G93 addendum). The body was restored byte-for-byte to the feedstock's indentation (whitespace
  only); `validate` is now 0. `optimize` 1 is TEST-001, the multi-output false positive. CI-parity lint: in fine form.
- `py-yaml12`: `check-deps` 1 is only `cross-python_PLACEHOLDER` (the templated cross-compile build dependency).
  CI-parity lint: in fine form.
- `solvor`: the same `cross-python_PLACEHOLDER` false miss. CI-parity lint: in fine form.

Notes:

- G53 also found `django-grpc` (`pb01ka`) and `py-yaml12` and `solvor` (`jsmolic`) missing a deployed maintainer; each
  was re-merged before the first build. All 26 lists are now supersets of their feedstocks'.
- `langflow`'s third-pass record was `failed` because the driver classifies a test `pip check` failure as a build
  failure; the build phase of every output it reached was clean. The review follow-up fixed the cause (G77 remedy 0).
- `pillow-heif` now carries a local-only patch the feedstock does not, because the feedstock's CI image does not hit
  the host-header leak; recorded in its `# CFE comments`.

### Review follow-up (2026-11-01)

An independent review of the run above found seven problems; each is fixed here. The rebuilt recipes went through the
same driver, `refresh_wave.py --apply --gates --build --rebuild --force`, with manifest and report in
`_bmad-output/projects/pyforge-mason/implementation-artifacts/refresh-waves/25-17/review/` (Tier 3). Every record
below was written by that build, and each report row carries `build.stamped: true`.

| Recipe | Before (third-pass record) | After (review record) | Change | Gates (validate / optimize / check-deps / scan; lint) |
|---|---|---|---|---|
| langflow | failed, 2026-11-02T01:26:59Z | success, 2026-11-02T02:07:49Z | `langflow-base` caps `openinference-instrumentation-langchain >=0.1.29,<0.1.80` (G36 / G77 remedy 0; local deviation with revert trigger in its CFE comments); `build_artifacts/langflow` cleaned first (G68); duplicate `# CFE comments` block merged; stale `loosen-langchain-chroma` update-needed and the skew blocker cleared. All eight outputs, `langflow` included, build and test green | 0 / 1 (TEST-001) / 0 / 0; lint clean |
| django-csvimport | success, 2026-11-02T01:23:42Z | success, 2026-11-02T02:09:22Z | run `django >=2.2.5` → `>=4.2` (feedstock, G96); local `meta.yaml` removed (feedstock is v1, C2 / G94); BFP note added | 0 / 1 (DEP-002, TEST-002) / 0 / 0; lint clean |
| wagtail | success, 2026-11-02T01:20:48Z | success, 2026-11-02T02:10:09Z | `build.python.entry_points` `wagtail = wagtail.bin.wagtail:main` and the `wagtail help` script test synced from the feedstock (G96) | 0 / 1 (DEP-002) / 0 / 0; lint clean |
| zxing-cpp | success, 2026-11-02T01:24:30Z | success, 2026-11-02T02:10:53Z | `conda-forge.yml` re-mirrored byte-for-byte from the feedstock; recipe-dir `conda_build_config.yaml` removed (G94; the build does not need it) | 0 / 0 / 0 / 0; lint clean |
| py-yaml12 | success, 2026-11-02T01:29:44Z | success, 2026-11-02T02:12:39Z | `build.number` 0 → 1 (feedstock value at the same version) | 0 / 0 / 1 / 0; lint clean |
| StringZilla | success, 2026-11-02T01:22:34Z | success, 2026-11-02T02:14:58Z | stale "both CLIs passed" comment annotated (4.6.3; 5.x ships no CLIs) | 0 / 1 (STD-002) / 1 / 0; lint clean |
| pixitainer | success, 2026-11-02T01:27:52Z | success, 2026-11-02T02:15:04Z | CFE note date only | 0 / 1 (TEST-001) / 0 / 0; lint clean |
| pillow-heif | success, 2026-11-02T01:15:40Z | success, 2026-11-02T02:15:53Z | CFE note date only (Windows lines left as they are) | 0 / 0 / 1 / 0; lint clean |
| tree-sitter-php | success, 2026-11-02T01:18:46Z | success, 2026-11-02T02:16:35Z | CFE note date only | 0 / 0 / 0 / 0; lint clean |
| django-grpc | success, 2026-11-02T01:23:09Z | success, 2026-11-02T02:17:11Z | CFE note date only | 0 / 1 (STD-002, TEST-002) / 0 / 0; lint clean |
| django-lasuite | success, 2026-11-02T01:32:11Z | success, 2026-11-02T02:18:24Z | CFE note date only | 0 / 0 / 0 / 0; lint clean |

Other changes in the follow-up:

- Driver: `_run_build` now records `build.stamped`, false (with a note) when any `cfe-local-build-*` key is missing or
  not exactly once in the recipe, or the stamp write is skipped; previously `build.datetime` was reported even when
  nothing was stamped. Unit test added.
- `meta.yaml` re-mirrored byte-for-byte from the v0 feedstock (C1) for `robocorp-storage` (was 1.1.0),
  `django-weasyprint` (2.5.0), `wagtail-autocomplete` (0.12.0), `wagtail-json-widget` (0.0.7) and `wagtailtables`
  (0.2.2); each blob now equals the feedstock's. Their `recipe.yaml` did not change, so their third-pass records stand.
  Every remaining local `meta.yaml` among the 26 equals its feedstock's.
- `wagtail`'s three other differences from the feedstock (`about.license_file` lacked `wagtail/models/copying.py`, the
  about text differed, the build script lacked `--disable-pip-version-check`) were synced afterwards; see below.
- `langflow`'s earlier "external skew" reading was wrong: conda-forge has `openinference-instrumentation-langchain`
  0.1.76, whose wheel needs only `openinference-instrumentation >=0.1.61`, so a cap below 0.1.80 resolves it. The
  built `langflow-base` artifact carries `openinference-instrumentation-langchain >=0.1.29,<0.1.80`.

Verification after the follow-up: the four `cfe-local-build-*` fields of all 26 recipes equal `build.status` and
`build.datetime` of the report that built them last (0 mismatches); `grep -l "2026-10-10T08:35:31Z"
recipes/*/recipe.yaml` exits 1 with no output; every `recipes/**/recipe.yaml` parses; `test_refresh_wave.py` and
`test_refresh_wave_wiring.py` pass (exit 0); CI-parity lint is clean for all seventeen recipes re-gated here.

Second `wagtail` sync. The whole `about` block (text, documentation URL, and `license_file: [LICENSE,
wagtail/models/copying.py]`) and the build script's `--disable-pip-version-check` were copied from the feedstock, and its
CFE note now says so. The body differs from the feedstock only in the literal package name and source URL (CFE canonical
form), the order of the host list, and blank lines and quote style. Rebuilt through the same driver on a one-recipe
manifest (`.../25-17/review-wagtail/`; driver exit 0, `build.stamped: true`):

| Recipe | Before | After | Gates (validate / optimize / check-deps / scan; lint) |
|---|---|---|---|
| wagtail | success, 2026-11-02T02:10:09Z | success, 2026-11-02T02:24:45Z | 0 / 1 (DEP-002) / 0 / 0; lint clean |


**After the second review (2026-11-01, session owner).** `recipes/langflow/recipe.yaml`'s `cfe-forge-recipe-updates-needed` now names the `openinference-instrumentation-langchain <0.1.80` cap the feedstock will need on its next rebuild (it merged 1.13.0 before 0.1.80 published). Only that metadata line moved after the review-pass build; the body and the four `cfe-local-build-*` fields are the build's, so langflow's file hash now differs from its report row's `recipe_sha256` for that reason alone. `refresh_wave.py`'s `_run_build` now stamps all four record keys or none (a new status beside an older datetime is a record no build wrote); its test expects the recipe byte-identical when a key is missing or duplicated. Residual, recorded not fixed: django-silk, grafana-client, fastmcp-slim and vlmrun each carry two `# CFE comments` headers (as on main); merging them changes no record and would need four rebuilds.

## Auto Run Result

Status: done

Summary (2026-11-01, landed in one PR with marshal 113.14, mason 25.18 and steward 118.7/118.8, operator 2026-11-01):
- AC1–AC2: all 26 recipes rebuilt through `refresh-wave --apply --gates --build --rebuild` (the `--rebuild` flag this story added) and record `success` on linux-64; each record equals the report row of the build that wrote it (`implementation-artifacts/refresh-waves/25-17/{,review/,review-wagtail/}report.json`); no recipe carries `2026-10-10T08:35:31Z`; langflow went green after the G36/G77 cap on `openinference-instrumentation-langchain` (a recorded local deviation).
- AC3: pixitainer, py-yaml12 and solvor carry their gate reasons and CI-parity lint verdicts in the 25.4 correction.
- AC4: six run-table specs gained appended `Correction (Story 25.17, 2026-11-01)` sections; no row rewritten, no status moved.
- AC5: validate and the CI-parity lint exit 0 on all 26; the remaining optimize suggestions are the deployed feedstocks' own; every maintainer list is a superset of the deployed one (G53).
- AC6: local only.
- AC7: the `retro(cfe):` commit lands CFE v8.103.0 (G124, the run-table read-back; G125; the skew-versus-G77 test; `--rebuild`, `build.datetime`/`build.stamped` and all-or-none stamping; the remaining driver gaps as `DW-mason-25-17`).
- AC8: `pyforge-mason-test` runs in the landing PR's preflight once the retro commit exists (its CFE-surface guards refuse an uncommitted CFE edit).
- Independent review: two rounds, every finding fixed (see the Review Triage Log).

## Spec Change Log

- 2026-11-01: minted from the EGM fleet audit (marshal Story 113.7), finding MAS-D-C1, cluster
  `mason-c08-epic25-build-records`; fix under `spec-pyforge-mason` CAP-35, no new CAP; parked at `backlog`.

## Review Triage Log

- 2026-11-01 — independent review 1 (separate agent, read-only): AC1–AC6 verified; blocker: AC7 (the retro) not yet done — done in the landing's `retro(cfe):` commit. Minors, all fixed: langflow misfiled as external skew (a G36/G77 cap fixed it), five stale `meta.yaml` mirrors and a `meta.yaml` beside a v1 feedstock, a wrong zxing-cpp attribution and a stale `conda-forge.yml`/CBC, a report datetime recorded even when nothing was stamped (`build.stamped`), csvimport and wagtail drift from their feedstocks, AC3 evidence only in this spec, two stale comments.
- 2026-11-01 — re-review 2: every fix verified (records equal their reports, blob shas equal the feedstocks', langflow-base carries the cap); nits taken: langflow's `cfe-forge-recipe-updates-needed` names the cap its feedstock will need, and the driver now stamps all four keys or none.
