---
title: "30.1: Recipes that import playwright depend on playwright-python"
type: 'fix'
created: '2026-10-12'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/pypi_conda_mappings/custom.yaml
  - .claude/skills/conda-forge-expert/tests/meta/test_split_distribution_run_deps.py
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-29-1-pwndbg-passes-pip-check-with-a-local-pwntools-that-carries-the-upstream-unicorn-fix.md
deferred:
  - id: pypi-conda-map-cache-ignores-custom-overrides
    summary: "Neither writer of pypi_conda_map.json (mapping_manager.update_mapping_cache, atlas's export_pypi_conda_map node) applies pypi_conda_mappings/custom.yaml, so mapping_gap.py and atlas still read playwright -> playwright (the Node CLI); only name_resolver's tier 0 honours the override. Blocked on scope: the second writer is atlas's, a cross-station change."
    location: .claude/skills/conda-forge-expert/scripts/mapping_manager.py:230
    severity: medium
  - id: playwright-python-driver-unpinned
    summary: "conda-forge playwright-python depends on an unpinned playwright, so an exact bindings pin (open-webui ==1.49.1, openhands-ai ==1.58.0) installs the newest driver; import and pip check never exercise the skew. Blocked on scope: this story never touches recipes/playwright-python, and the durable fix is a feedstock change (outward, operator-owned)."
    location: recipes/playwright-python/recipe.yaml:41
    severity: low
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** conda-forge `playwright` is the Node CLI and browser driver, with no Python module. The Python bindings
(`import playwright`, PyPI distribution `playwright`) are conda-forge `playwright-python`, which depends on the CLI
(CFE gotcha G107). Story 29.1's `test_split_distribution_run_deps.py` declares this pair but does not lint it. Run
unlinted, it flags 16 `noarch: python` recipes that list `playwright` and not `playwright-python`. Facts checked live
on 2026-10-12:

| Recipe | Upstream `requires_dist` for playwright | Recipe run dep today |
|---|---|---|
| botright 0.5.1 | `playwright >=1.40.0` | `playwright >=1.40.0` |
| cuga 0.3.1 | `playwright>=1.59.0` | `playwright >=1.59.0` |
| dataframe_image 0.2.7 | `playwright` | `playwright` |
| install-playwright 1.0.2 | `playwright<2,>=1.49.1` | `playwright <2,>=1.49.1` |
| markdown_convert 2.0.13 | `playwright>=1.57.0` | `playwright >=1.57.0` |
| mcp-docs 0.0.1 | `playwright>=1.40.0` | `playwright >=1.40.0` |
| md2pdf-mermaid 1.4.3 | `playwright>=1.40.0` | `playwright >=1.40.0` |
| mermaid-cli 0.1.3 | `playwright>=1.30.0` | `playwright >=1.30.0` |
| open-webui 0.6.26 | `playwright==1.49.1` | `playwright ==1.49.1` |
| openhands-ai 1.11.0 | `playwright==1.58.0` | `playwright ==1.58.0` |
| playwright-mcp 0.1.0 | `playwright>=1.50.0` | `playwright >=1.50.0` |
| playwright-mcp-server 0.1.0 | `playwright` | `playwright` |
| pytest-playwright-asyncio 0.9.0 | `playwright>=1.18` | `playwright >=1.18` |
| universal-document-mcp 1.0.0 | `playwright>=1.40.0` | `playwright >=1.40.0` |
| xync-client 0.0.237 | `playwright` | `playwright` |

The sixteenth, `recipes/playwright-python`, is the bindings recipe itself, and its dependency on the CLI is correct.
Every pin above has a `playwright-python` build on conda-forge (1.44.0 to 1.62.0). Because each wheel's metadata
requires the PyPI distribution `playwright`, which only `playwright-python` installs, none of these 15 can pass
`pip check` today.

**Approach:**
1. In each of the 15 recipes, replace the run dep `playwright <spec>` with `playwright-python <spec>`, keeping the
   upstream spec and any comment on the line.
2. Mark the `playwright` entry in `pypi_conda_mappings/custom.yaml` `lint_wrong_half: true`. Teach the G107 check to
   exempt the bindings' own recipe (a recipe whose package name is the bindings' conda name).
3. Run the CFE dependency check on each recipe. Build every recipe whose other dependencies resolve on conda-forge or
   the local channel, on linux-64. A recipe that cannot build records the missing dependency in
   `cfe-forge-blocker-list`.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-mason` CAP-18 (the local mirror as source of truth) and CAP-23 (recipe
  lifecycle machinery), as for Story 29.1. No CAP is minted, and no `SPEC.md` text changes.
- **No flag.** This is a `fix` (`spec-feature-flag-governance` Q1).
- **Origin.** `docs/dreams/pyforge-mason.md` Realization log, the 2026-10-12 (later) entry. Operator ask 2026-10-12:
  "Do this task here: Audit 16 recipes that depend on conda playwright".

## Acceptance Criteria

- **AC1 — The bindings, not the CLI.** Each of the 15 recipes lists `playwright-python` with the upstream spec in the
  table, and no bare `playwright` in its run deps. `recipes/playwright-python` is unchanged.
- **AC2 — The check lints the pair.** `custom.yaml`'s `playwright` entry carries `lint_wrong_half: true`, and
  `test_split_distribution_run_deps.py` passes. It exempts only a recipe whose package name is the bindings' conda
  name.
- **AC3 — Builds.** Each recipe whose other run dependencies resolve builds green on linux-64 with
  `pixi run -e local-recipes recipe-build`, its import test and `pip check` passing. The Run results name each
  recipe's outcome. A recipe that cannot build has its blocker in `cfe-forge-blocker-list` and an accurate
  `cfe-local-build-status`.
- **AC4 — Gates.** Each changed recipe passes `validate_recipe`, except playwright-mcp: its license lint
  (`REPLACE_LICENSE`) is its recorded blocker, because upstream publishes no license.
- **AC5 — Rule 2.** The story closes with a `retro(cfe):` commit carrying a CFE `CHANGELOG.md` semver entry.
- **AC6 — Mutation.** Each change below makes a named check fail:
  - bare `playwright` back in any one of the 15: the G107 check;
  - remove the bindings exemption: the G107 check, on `recipes/playwright-python`;
  - drop `lint_wrong_half` from the `playwright` entry: the check's declared-pairs test.

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert` (Rule 1). Build on linux-64 only.
- Keep each upstream spec, and every human comment on a changed line.
- Read every verdict from the exit code, never through a pipe.
- Reconcile every governed path on the memlogs of the Specs that govern it, then stamp scoped.

**Never:**
- Never open a feedstock, staged-recipes or upstream PR without an explicit ask.
- Never touch `recipes/playwright-python`.
- Never change a recipe's version, source or any dependency other than `playwright` in this story; a blocker is
  recorded, not worked around. A recipe defect that stops a build and is fixable from upstream's own files (a
  missing LICENSE, a broken build script, a missing `noarch_platforms`) is fixed, and the Spec Change Log says so.

## I/O & Edge-Case Matrix

| Case | Expected |
|---|---|
| noarch:python recipe lists `playwright-python` | check passes |
| noarch:python recipe lists `playwright` only | check fails |
| `recipes/playwright-python` lists `playwright` | check passes (the bindings' own recipe) |
| a recipe lists both `playwright` and `playwright-python` | check passes |

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-mason` CAP-18 and CAP-23. No CAP is minted.
- Dream: `docs/dreams/pyforge-mason.md` § *Realization log*, the 2026-10-12 (later) entry.
- Epic: Epic 30 (new), minted with this story.
- Ledger key: `30-1-recipes-that-import-playwright-depend-on-playwright-python`.
- Ledger status at mint: `backlog`.
- Deps: Story 29.1 (the G107 check and `custom.yaml` overrides).
- Surface: `marshal-policy.toml` `[epic_surfaces]."30"`, added with this mint.

## Verification

**Commands:**
- `pytest .claude/skills/conda-forge-expert/tests/meta/test_split_distribution_run_deps.py` — expected: pass.
- `pixi run -e local-recipes recipe-build recipes/<name>` for each buildable recipe — expected: exit 0.
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass.

**Run before the push (not dispatch gates):**
- `validate_recipe` on each changed recipe — expected: pass.
- The three mutations of AC6 — expected: each fails its named check. Restore each.

## Run results

Built on linux-64 with `recipe-build` (rattler-build, local channel), 2026-10-13. Root cause found during the audit:
`recipe-generator.py` resolves PyPI requirements through `name_resolver.resolve_name`, whose cache maps
`playwright → playwright`.

| Recipe | Outcome | Blocker (recorded in its CFE block) |
|---|---|---|
| mermaid-cli, install-playwright, pytest-playwright-asyncio, dataframe_image, md2pdf-mermaid | success: import and `pip check` pass | — |
| open-webui | success: imports and `--help` pass; `pip_check` stays `false` | `pip check` names 13 run deps the recipe omits and two pin skews; playwright is not among them |
| playwright-mcp-server | build clean, test env blocked | `asyncio` (a stdlib backport in upstream metadata) is not on conda-forge |
| mcp-docs | build clean, test env blocked | `utils` is not on conda-forge |
| markdown_convert | build clean, test env blocked | `argsdict`, `string-grab`, `yaml-to-schemdraw` |
| botright | build clean, test env blocked | five deps not on conda-forge |
| cuga | build clean, test env blocked | four deps not on conda-forge; `langfuse` is `langfuse-python` and `sqlite-vec` is `sqlite-vec-python` (G10) |
| openhands-ai | build clean, test env blocked (rebuilt with its `__unix` / `__win` guards) | six deps not on conda-forge; `memory-profiler` is `memory_profiler` and `zope-interface` is `zope.interface` (G10) |
| playwright-mcp | failed | no license anywhere upstream (`REPLACE_LICENSE`) |
| xync-client | failed | no license file, and `license: MIT` unverified; `REPLACE_SUMMARY` placeholders (G90); 11 deps not on conda-forge |
| universal-document-mcp | failed | upstream setuptools flat-layout (four top-level packages); its upstream repo URL returns 404 |

- AC1: all 15 list `playwright-python` with the upstream spec; `recipes/playwright-python` unchanged.
- AC2: `test_split_distribution_run_deps.py` passes with the pair linted.
- AC3: met for the five full successes. open-webui builds and imports, but its `pip check` stays waived
  (`false:open-webui-trimmed-run-deps`): the recipe omits 13 upstream run deps, and adding them is outside this story's
  boundary. The waiver names them; playwright is not among them.
- AC4: `validate_recipe` passes on 14 of 15; playwright-mcp fails on its license, as on `main`.
- AC5: `retro(cfe):` v8.100.1.
- AC6:
  - Bare `playwright` in `recipes/cuga` fails the check ("recipes/cuga/recipe.yaml: run lists `playwright`, not
    `playwright-python`").
  - Without the exemption, the check fails on `recipes/playwright-python`.
  - Without the flag, the declared-pairs test fails.
- Verification: `pyforge-mason-test` passes (1622 passed, 3 deselected; 12 passed). The planning gates and
  `detectors-ci` exit 0.

## Spec Change Log

- 2026-10-12: minted at the operator's ask "Do this task here: Audit 16 recipes that depend on conda playwright".
- 2026-10-13 (implementation): three recipe defects that stopped a build or `validate_recipe` were fixed (healed
  tissue): md2pdf-mermaid ships its LICENSE in the recipe dir (the 1.4.3 sdist omits it; copied from the v1.4.3 tag);
  universal-document-mcp's build script names the source dir; openhands-ai's `conda-forge.yml` declares
  `noarch_platforms` for its `win` run selector (G111). AC4 names playwright-mcp's license lint as its blocker. The Epic
  30 boundary and Surface widened to match.
- 2026-10-13 (review): openhands-ai's run deps gained the `__unix` / `__win` guards that make its `noarch_platforms`
  fix complete (G111), and the recipe was rebuilt (same outcome). Blocker text, timestamps and counts were corrected.

## Review Triage Log

Independent adversarial review, 2026-10-13: 2 medium, 8 low, no high.

- **Fixed (medium):** openhands-ai had `noarch_platforms` but no `__unix` / `__win` guards, so a solver could not tell
  its two noarch builds apart. Guards added and the recipe rebuilt. G111's rule now requires them.
- **Fixed (medium):** two blocker lists broke G10. cuga's `sqlite-vec` is conda-forge `sqlite-vec-python`, and
  openhands-ai's `memory-profiler` is `memory_profiler`. Both are now named as renames.
- **Fixed (low):** counts. The CHANGELOG and Dream now say 14 of 15 were never built, the Dream's pin range is
  corrected, and the Intent table names each recipe's own version (`requires_dist` re-read at those versions).
- **Fixed (low):** every `cfe-last-checked` and new `cfe-generated-at-datetime` read a time after the commit. They now
  read the validation run (04:46Z), and openhands-ai reads its rebuild.
- **Fixed (low):** open-webui's `success` beside a waived pip check. SKILL's `success` definition now covers a recorded
  waiver, and AC3's Run result names the gap.
- **Fixed (low):** xync-client's unverified `license: MIT` and G90 placeholders, and universal-document-mcp's 404 repo URL,
  are now in their blocker lists.
- **Fixed and deferred (low):** the retro overstated its reach. The text now says the tier-0 lookup fixes the generator
  only. The cache's two writers ignore `custom.yaml`; one is atlas's, so the fix is deferred
  (`pypi-conda-map-cache-ignores-custom-overrides`).
- **Fixed (low):** `pyforge-mason-test` evidence added to the Run results.
- **Fixed (low):** md2pdf-mermaid's CFE note moved under `# Header:`.
- **Deferred (low):** conda-forge `playwright-python` leaves its driver unpinned, so exact bindings pins get the newest
  driver. Out of scope (never touch `recipes/playwright-python`; the durable fix is a feedstock change). Noted in
  G107 and deferred (`playwright-python-driver-unpinned`).
