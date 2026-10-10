---
title: "25.16: Three dbt adapter recipes are re-mirrored from their own feedstocks"
type: 'fix'
created: '2026-10-10'
status: 'done'
baseline_revision: '647abbc9b21d09c54e75cc59f1e93c1ea4331f4b'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - docs/specs/feedstock-refresh.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-5-track-b-batch-1-refreshes-airflow-code-editor-through-django-countries.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-13-wave-f-mirrors-the-two-co-maintained-feedstocks-that-have-no-local-recipe.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-15-five-duplicate-langflow-suite-directories-retire-into-recipes-langflow.md
deferred:
  - id: feedstock-name-cfe-feedstock-identity-check
    summary: >-
      Repo-scope detector when extra.feedstock-name names a different feedstock than
      cfe-on-conda-forge-feedstock (identity-snapshot wrong-mirror class). At run time
      2 recipes remain after this story fixed dbt-bigquery and dbt-postgres.
    location: recipes/dspy/recipe.yaml
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `recipes/dbt-bigquery`, `recipes/dbt-postgres` and `recipes/dbt-redshift` do not mirror their feedstocks.
Each `recipe.yaml` is a copy of `dbt-feedstock`'s `dbt-core` recipe (`context.name: dbt-core`,
`extra.feedstock-name: dbt`, a `dbt_core` sdist URL, and a patch the directory lacks), so it declares `dbt-core`, not
the adapter. The 2026-08-16 identity snapshot (`20b2f459fa`) wrote all three. Each directory's `meta.yaml` is older
still. Story 25.15's mint found them (its open question 2), and the operator ruled on 2026-10-09, choosing "Fix in a
story": "Mint a mason fix story that re-mirrors the three adapter recipes from dbt-bigquery/postgres/redshift-feedstock
(dbt-bigquery-feedstock is now v1 at 1.12.1), and correct batch 25.5's table." This is that story.

**The three, read live at mint (2026-10-10, raw GETs and `gh api` GETs only; rate limit 5000/5000).**

| Directory | Feedstock `main` | Published (conda-forge = PyPI) | Format and `recipe/` files | Deployed maintainers | Class |
|---|---|---|---|---|---|
| `recipes/dbt-bigquery` | `conda-forge/dbt-bigquery-feedstock` at `3709f35d56` (2026-09-19) | 1.12.1, build 1 | v1 since its PR #58 (`aa7005a714`, 2026-09-19); `recipe.yaml` | rxm7706, maresb, thewchan | C2: no local `meta.yaml` |
| `recipes/dbt-postgres` | `conda-forge/dbt-postgres-feedstock` at `c18adc1194` (2026-07-25) | 1.11.0, build 0 | v0; `meta.yaml` | maresb, rxm7706 | C1: keep the feedstock's `meta.yaml` |
| `recipes/dbt-redshift` | `conda-forge/dbt-redshift-feedstock` at `d9d9bdba74` (2026-08-21) | 1.11.1, build 0 | v0; `meta.yaml`, `LICENSE.md` | rxm7706, maresb, thewchan | C1: keep the feedstock's `meta.yaml` |

None of the three feedstocks had an open PR at mint. Each is `noarch: python`. conda-forge's `feedstock-outputs`
registry gives each adapter name to two feedstocks, `dbt` and the adapter's own. The `dbt` entry is history:
`dbt-feedstock`'s recipe today builds only `dbt-core`. So each adapter's own feedstock is its mirror.

**What each directory holds today (`main` at mint).**

| Directory | `recipe.yaml` | `meta.yaml` | Recipe-dir files the feedstock lacks or has |
|---|---|---|---|
| `recipes/dbt-bigquery` | `dbt-core` 1.12.0; maintainers rxm7706, maresb, thewchan; a CFE block for `dbt-bigquery` (stale: `meta-yaml-to-recipe-yaml`, `version-update-to-1.12.0`, build `failed`) | `dbt-bigquery` 1.8.0, a `pypi.io` URL, maintainer rxm7706 only | a `meta.yaml` the v1 feedstock no longer has |
| `recipes/dbt-postgres` | `dbt-core`'s recipe body at `context.version` 1.11.0, but with `dbt-postgres` 1.11.0's sha256 (`0a8558e0…`) against a `dbt_core-1.11.0` URL; maintainers maresb, rxm7706; a CFE block for `dbt-postgres` | `dbt-postgres` 1.8.0, maintainer rxm7706 only | — |
| `recipes/dbt-redshift` | `dbt-core` 1.12.2 with `dbt-feedstock`'s six maintainers; no CFE block | `dbt-redshift` 1.10.1, with a `python_min = "3.10"` override the feedstock does not have | lacks the feedstock's `LICENSE.md` |

All three `recipe.yaml` files list `0001-drop-experimental-parser-hard-dep.patch`, which none of the directories
carries, so none builds as it stands. No batch story refreshes `recipes/dbt-postgres` or `recipes/dbt-redshift`. Their
`recipe.yaml` versions read as current (1.11.0 against 1.11.0) and ahead (1.12.2 against 1.11.1), so a version-only
read would not queue them. Story 25.5 did queue `recipes/dbt-bigquery`, and recorded its feedstock as v0. Both were
wrong for the same reason: the recipe it would have refreshed is `dbt-core`'s. So `dbt-bigquery` leaves Story 25.5's
batch, and this story takes all three.

**Why a re-mirror, not a refresh.** Story 25.3's driver moves a recipe's `context.version` and keeps the rest. Here the
rest is the wrong package, so the driver would refresh `dbt-core` under an adapter's directory. CFE's mirror rule is the
fix (SKILL.md § *Local-mirror fidelity*; `docs/specs/feedstock-refresh.md` C1 and C2): take each feedstock's `recipe/`
directory, keep a v0 feedstock's `meta.yaml` byte-identical beside a local v1 `recipe.yaml`, and keep no `meta.yaml`
for a v1 feedstock. Story 25.9's AC 13 and Story 25.13 follow the same rule.

**Deps: none, decided on evidence.** Each adapter's run requirements include `dbt-core` (`>=1.10.0rc0,<2.0` for
`dbt-bigquery`, `>=1.8.0` for `dbt-postgres`, `>=1.8.0b3,<2.0` for `dbt-redshift`), and `dbt-redshift` also needs
`dbt-postgres >=1.10.0rc1,<2.0`. A local build resolves every one of them from conda-forge into an isolated output
directory, never from a shared local channel (G52, landmine 13). conda-forge carries `dbt-core` 1.12.5 and
`dbt-postgres` 1.11.0. No adapter recipe names a local recipe path. So Story 25.15's retirement of `recipes/dbt-core`
changes no input of these builds, and this story does not wait for it. Nor does 25.15 wait for this story: its AC 4
allows the three directories as `dbt-core` declarers until this story lands. The three builds need no order among
themselves for the same reason.

**Approach:** mirror first, through conda-forge-expert, one feedstock at a time.
1. Read each feedstock live (AC 1).
2. Replace each directory's files with the feedstock's `recipe/` files, plus a local v1 `recipe.yaml` for the two v0
   feedstocks (AC 2).
3. Bring each `recipe.yaml` to the CFE bar without overriding a maintainer's choice: canonical `source.url` (AC 3),
   maintainers (AC 4), the CFE blocks (AC 5).
4. Run the gates (AC 6) and an isolated linux-64 build (AC 7), and record each outcome (AC 8).
5. Check that each adapter name has one declarer and that none of the three declares `dbt-core` (AC 9). Commit per
   recipe. File the follow-up (AC 11), and close with the Rule-2 retro (AC 12).

Ledger key: `25-16-three-dbt-adapter-recipes-are-re-mirrored-from-their-own-feedstocks`.
Ledger status at mint: `backlog`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-35 (FR-57), the refresh campaign and its local mirrors; CAP-20, the recurring campaigns;
  CAP-23, the CFE machinery. No new CAP, so no FR moves.
- AD-1 (no recipe knowledge in Mason's code); AD-15 (the CFE surface moves only in the `retro(cfe):` commit).
- CFE Rule 1, Rule 2 and Rule 3; G52, G53, G62, G65, G92, G94, G95 and G96; SKILL.md § *Local-mirror fidelity* and
  § *PyPI `source.url` Must Use the `pypi.org/packages/...` Pattern*; `docs/specs/feedstock-refresh.md` § *Track B*,
  C1 and C2, coordination rules 1 to 5 and landmines 1 to 13.
- `spec-fleet-stewardship` CAP-1 (the local mirror is the source of truth, `recipes/<feedstock>/`) governs `recipes/**`;
  `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` CAP-1, Q1: a fix carries no flag.
- Siblings: Story 25.15 retires `recipes/dbt-core` and keeps `recipes/dbt`. Story 25.5 refreshes `recipes/dbt` and no
  longer names `recipes/dbt-bigquery`. Story 25.13 mirrors `recipes/dbt-snowflake`. Only the `retro(cfe):` commits of
  Epic 25's stories meet, at the CFE version carriers.

## Acceptance Criteria

1. **Read live first.** Given the three feedstocks When the story starts Then § *Run results* records, before any file
   changes: each feedstock's `main` SHA, published version and build number, recipe format, deployed
   `extra.recipe-maintainers`, and every file in its `recipe/` directory; conda-forge's latest version of each package;
   and each adapter name's `feedstock-outputs` entry and atlas `packages.feedstock_name`. A feedstock that has published
   past this spec's version is followed to its live version, and the move is noted. A feedstock that has moved from v0
   to v1 since is mirrored as C2 under AC 2.
2. **Mirror first.** Given each feedstock's `recipe/` directory When the story re-mirrors its directory Then every
   file comes from the feedstock, and the `dbt-core` recipe in today's `recipe.yaml` is replaced whole:
   - `recipes/dbt-bigquery` (v1, C2): `recipe.yaml` from the feedstock, and the local `meta.yaml` removed (G94);
   - `recipes/dbt-postgres` and `recipes/dbt-redshift` (v0, C1): `meta.yaml` byte-identical to the feedstock's,
     `dbt-redshift`'s `LICENSE.md` copied, and a v1 `recipe.yaml` authored from that `meta.yaml` through CFE's migration
     path (`migrate_to_v1`).

   No recipe is generated by grayskull (`generate_recipe_from_pypi` is never run into `recipes/`). No file the
   feedstock lacks stays in the directory, and no `recipe.yaml` keeps `extra.feedstock-name: dbt` or the
   `0001-drop-experimental-parser-hard-dep.patch` reference. Each `recipe.yaml` differs from its feedstock's recipe only
   where ACs 3 to 5 say, plus the v0-to-v1 conversion itself. § *Run results* lists each difference. A deliberate
   maintainer choice is kept, such as `dbt-postgres`'s commented `psycopg2-binary` choice. A change the story would
   propose to one is parked in the bottom CFE comments block with a `cfe-forge-recipe-updates-needed` token
   (landmine 12).
3. **Canonical source URL, same bytes.** Given each `recipe.yaml` When its `source.url` is written Then it takes CFE's
   canonical literal form, `https://pypi.org/packages/source/d/<dist>/<file>-${{ version }}.tar.gz`, with only
   `${{ version }}` interpolated. The sha256 equals the feedstock's, verified by hashing the new URL. The difference
   from the feedstock is parked in the CFE comments block with a `cfe-forge-recipe-updates-needed` token. A C1
   `meta.yaml` stays byte-identical to the feedstock's, its URL included.
4. **Maintainers kept (G53).** Given each `recipe.yaml` When its `extra.recipe-maintainers` is compared with its own
   feedstock's deployed list, read live at run time Then the local list is a superset and includes `rxm7706`.
   `drewbanin`, `jthandy` and `zaneselvans`, which `recipes/dbt-redshift/recipe.yaml` lists today, maintain
   `dbt-feedstock`, not `dbt-redshift-feedstock`. They leave with the `dbt-core` recipe they came with, and
   § *Run results* records it. No maintainer of an adapter's own feedstock is dropped.
5. **CFE metadata, once.** Given each `recipe.yaml` When the story stamps its CFE block Then it carries the full `cfe-*`
   identity block for the adapter, with exactly one `#### CFE metadata` header and one `cfe-conda-name` (G92: strip
   both forms first). That includes `cfe-conda-name` and `cfe-upstream-name` (the adapter), `cfe-upstream-registry:
   pypi`, `cfe-on-conda-forge-status: confirmed-on-conda-forge`, `cfe-on-conda-forge-feedstock` (its own feedstock's
   URL), `cfe-forge-recipe-updates-needed` (with `meta-yaml-to-recipe-yaml` for the two C1 mirrors, and no stale
   `version-update-to-…` token), and the `cfe-local-build-*` fields. `recipes/dbt-redshift` gains a block; it has
   none. The bottom comments block names the feedstock commit each mirror was taken from.
6. **Gates.** Given each re-mirrored recipe When `validate_recipe`, `optimize_recipe`, `check_dependencies`,
   `scan_for_vulnerabilities` and `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge`
   run on its `recipe.yaml` Then none reports an error. An expected finding is recorded with its reason: STD-002 on the
   two C1 mirrors, or the fork-only hint that a feedstock of the same name exists.
7. **A linux-64 build, isolated.** Given each re-mirrored recipe When `rattler-build build --recipe
   recipes/<dir>/recipe.yaml --output-dir <isolated dir>` runs on linux-64 Then it exits 0, with the feedstock's import
   test and `pip_check` passing. The test environment resolves `dbt-core`, `dbt-adapters`, `dbt-common` and, for
   `dbt-redshift`, `dbt-postgres` from conda-forge, never from a shared local channel (G52). Otherwise its
   `cfe-local-build-*` fields record `build-clean-test-blocked` (G95) or `not-attempted` with the reason. At most 3
   builds run at once.
8. **Every recipe ends somewhere.** Given the three directories When the story closes Then each ends in one of two
   states, recorded in § *Run results* with its gate and build results:
   - `re-mirrored`: ACs 2 to 7 met;
   - `needs-review`: with the reason it stopped and what it tried, also parked in that recipe's CFE comments block.

   A `needs-review` recipe does not hold back the other two. If a directory cannot be re-mirrored at all, its files
   stay as they were, and the reason is recorded.
9. **One recipe per package name.** Given the tree after the re-mirror When the § *Verification* parse runs over every
   `recipes/*/recipe.yaml` and `meta.yaml` Then it exits 0: `dbt-bigquery`, `dbt-postgres` and `dbt-redshift` are each
   declared by their own directory alone, and none of the three directories declares `dbt-core`. At mint the parse
   exits 1. § *Run results* records the command, its output and its exit code, and which directories then declare
   `dbt-core`: `recipes/dbt` alone if Story 25.15 has landed, `recipes/dbt` and `recipes/dbt-core` if not.
10. **Nothing leaves the local repo.** Given the story's whole run When it closes Then no `git push`, `gh pr create`,
    `gh repo fork` or `gh api` write reached anything outside `rxm7706/local-recipes`; no issue or comment was opened;
    no `mason recipe submit` or `mason package ship` and no CFE `submit_pr` or `prepare_submission_branch` ran. The two
    v1 `recipe.yaml` files for v0 feedstocks are local proposals, never submitted.
11. **Follow-up filed, not built.** Given the story closes When it files its findings Then this spec's `deferred:`
    frontmatter carries one row, unless the mason deferred-work ledger already names it: the identity-snapshot class. A
    `recipe.yaml` whose `extra.feedstock-name` names a different feedstock than its CFE block's
    `cfe-on-conda-forge-feedstock` may mirror the wrong feedstock, and no repo check refuses it. A parse at mint finds
    four: `recipes/dbt-bigquery` and `recipes/dbt-postgres`, which this story fixes, and `recipes/dspy` and
    `recipes/lance-namespace-urllib3-client`, which it does not judge. (`recipes/dbt-redshift` has no CFE block, so
    that parse cannot see it.) The row proposes a repo-scope check and records the count at run time. The story builds
    no check.
12. **Retro and suite.** Given the story closes When the Rule-2 retro runs Then a separate `retro(cfe):` commit lands a
    CFE `CHANGELOG.md` semver entry, with the four version carriers in lockstep. It is PATCH, or MINOR if it adds a
    gotcha. A candidate: before refreshing a recipe, check that its `context.name` or `package.name` is the package its
    directory and CFE block name; the identity snapshot wrote three that were not. If another Epic 25 story's retro
    reached `main` first, this one takes the next version when it merges `main`. Also
    `pixi run --frozen -e pyforge-mason pyforge-mason-test` passes.

## Tasks

1. Invoke `conda-forge-expert` and read its SKILL.md (Rule 1): § *Local-mirror fidelity*, § *PyPI `source.url` Must
   Use the `pypi.org/packages/...` Pattern*, G52, G53, G92, G94 and G95; and `docs/specs/feedstock-refresh.md` C1, C2
   and § *Track B*. Where the file, this spec and the skill differ, the skill wins, and the story records the
   difference.
2. Read the three feedstocks live and record them (AC 1).
3. For each directory: replace its files from the feedstock (AC 2); for the two v0 feedstocks, author the v1
   `recipe.yaml` through CFE's migration path; write the canonical `source.url` and verify the sha256 (AC 3); run
   `enrich_from_feedstock` and audit maintainers (AC 4); stamp the CFE blocks (AC 5).
4. Run the gates (AC 6) and the isolated linux-64 builds (AC 7), and record each outcome (AC 8).
5. Run the package-name parse (AC 9).
6. Review every diff, then commit per recipe: `recipes: …`, never a subject starting `Story 25.16:`.
7. File the follow-up (AC 11). Close with the Rule-2 retro in its own commit, subject `retro(cfe): v<x.y.z> — …`
   (AC 12).
8. Reconcile every Spec `spec-surface-check` names: memlog first, then `git add`, then a scoped
   `--write-baseline --spec` for each (AGENTS.md checklist item 5).

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert` for every recipe judgement. Where this story and the skill disagree, the skill wins
  and the story records the deviation.
- Read every verdict from the exit code, never through a pipe.
- Keep `cfe-*` metadata in the local recipe. It is stripped only if a PR is ever asked for (G62).
- Read feedstocks, the registry and the atlas only: raw files, or `gh api` GETs.

**Never:**
- Nothing reaches conda-forge, a feedstock or staged-recipes. No `git push`, `gh pr create`, `gh repo fork` or
  `gh api` write outside `rxm7706/local-recipes`; no issue or comment; no `mason recipe submit` or
  `mason package ship`; no CFE `submit_pr` or `prepare_submission_branch`.
- Do not drop a maintainer of an adapter's own feedstock from its `recipe-maintainers` (AC 4), and never self-merge on
  a co-maintained feedstock.
- Do not touch a recipe directory other than these three. `recipes/dbt` is Story 25.5's, `recipes/dbt-core` Story
  25.15's, and `recipes/dbt-snowflake` Story 25.13's.
- Do not move a recipe past its feedstock's published version, and do not run `refresh-wave` over these three.
- Do not edit any CFE file outside the `retro(cfe):` commit. Do not touch `src/shared/packages/pyforge-mason/`,
  `pixi.toml`, `pixi.lock` or `environment.yaml`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| happy path | v1 or v0 feedstock, two or three maintainers | re-mirrored; every feedstock maintainer kept; build green | — |
| feedstock moved on | published past this spec's version | mirrored at the live version, noted | landmine 1 |
| feedstock went v1 | a v0 feedstock here converted since mint | mirrored as C2: no local `meta.yaml` | AC 1, AC 2 |
| URL form | `files.pythonhosted.org/packages/source/...` or a templated path | canonical literal URL in `recipe.yaml`, sha256 unchanged; `meta.yaml` byte-identical | needs-review on a hash mismatch |
| foreign maintainers | `dbt-feedstock`'s six handles in `recipes/dbt-redshift` | the adapter feedstock's own list; the three dbt-only handles leave, recorded | AC 4 |
| licence differs | `enrich_from_feedstock` aborts on a licence mismatch | stop for that recipe, record the abort reason | never pick a side silently |
| test env pollution | a dependency solve fails for a package on conda-forge | rebuild isolated before recording a block | G52, landmine 13 |
| 25.15 not landed | `recipes/dbt-core` still declares `dbt-core` | recorded by AC 9's parse; not touched | Story 25.15 |
| cannot re-mirror | a feedstock file or conversion fails | the directory left as it was; `needs-review` with the reason | AC 8 |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-35 (FR-57), with CAP-20 and CAP-23. No new CAP.
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-10-10 — Ruled: recipes/dbt-core retires into
recipes/dbt, and the three dbt adapters are re-mirrored*.
Ledger key: `25-16-three-dbt-adapter-recipes-are-re-mirrored-from-their-own-feedstocks`.
Ledger status at mint: `backlog`.
Deps: none (§ *Intent*, *Deps: none, decided on evidence*).
Flag: none (a fix; `spec-feature-flag-governance` CAP-1, Q1).
Minted 2026-10-10 on the operator's ruling of 2026-10-09 ("Fix in a story") on Story 25.15's open question 2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test`. Expected: pass. This is the station's `verify_commands`;
  the story changes no Mason code.
- The AC 9 parse, from the repo root. Expected: exit 0 after the re-mirror; exit 1 at mint.

  ```bash
  python - <<'EOF'
  import collections, pathlib, re, sys, yaml
  adapters = ("dbt-bigquery", "dbt-postgres", "dbt-redshift")
  want = set(adapters) | {"dbt-core"}
  hits = collections.defaultdict(set)
  for p in sorted(pathlib.Path("recipes").glob("*/recipe.yaml")):
      d = yaml.safe_load(p.read_text()) or {}
      ctx = {k: str(v) for k, v in (d.get("context") or {}).items()}
      names = [(d.get("package") or {}).get("name")]
      names += [(o.get("package") or {}).get("name") for o in d.get("outputs") or []]
      for n in filter(None, names):
          n = re.sub(r"\$\{\{\s*name\s*\|\s*lower\s*\}\}", ctx.get("name", "").lower(), str(n))
          n = re.sub(r"\$\{\{\s*name\s*\}\}", ctx.get("name", ""), n).lower()
          if n in want:
              hits[n].add(p.parent.name)
  for p in sorted(pathlib.Path("recipes").glob("*/meta.yaml")):
      t = p.read_text()
      found = set(re.findall(r"^\s*(?:-\s*)?name:\s*['\"]?([A-Za-z0-9_.-]+)", t, re.M))
      found |= set(re.findall(r"\{%\s*set\s+name\s*=\s*['\"]([^'\"]+)['\"]", t))
      for n in found:
          if n.lower() in want:
              hits[n.lower()].add(p.parent.name)
  bad = {n: sorted(hits.get(n, ())) for n in adapters if hits.get(n) != {n}}
  leak = sorted(hits.get("dbt-core", set()) & set(adapters))
  if leak:
      bad["dbt-core"] = leak
  print("dbt-core declared by:", sorted(hits.get("dbt-core", ())))
  print(bad or "ok: each adapter is declared by its own mirror alone, and none declares dbt-core")
  sys.exit(1 if bad else 0)
  EOF
  ```

**Manual checks:**
- For each of the three directories: its file list matches the feedstock's `recipe/` directory, plus `recipe.yaml`
  for the two C1 mirrors; `cmp` shows each C1 `meta.yaml` (and `dbt-redshift`'s `LICENSE.md`) byte-identical to the
  feedstock's.
- `pixi run -e local-recipes validate recipes/<dir>` and `pixi run -e local-recipes lint-optimize recipes/<dir>` report
  no errors; `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge recipes/<dir>` reports
  no lint (G65); a linux-64 `rattler-build build --recipe recipes/<dir>/recipe.yaml --output-dir <isolated dir>` exits
  0, or the recorded block is justified.
- `grep -c 'cfe-conda-name:' recipes/<dir>/recipe.yaml` prints 1 for each (G92).
- `git diff --name-only origin/main...HEAD -- recipes/` lists only `recipes/dbt-bigquery/`, `recipes/dbt-postgres/`
  and `recipes/dbt-redshift/`.
- `git log origin/main..HEAD --format=%s -- .claude/skills/conda-forge-expert`: exactly one `retro(cfe):` subject,
  and that commit carries `CHANGELOG.md`.
- § *Run results* carries the live read, each difference from the feedstock, the maintainer audit, each outcome, the
  build results and the package-name parse.
- `pixi run -e pyforge-guild spec-surface-check`: exit 0 after the scoped stamps.

## Run results

### Live read (2026-10-10, before any write)

| Directory | Feedstock `main` | Published | Format | Maintainers | `recipe/` files |
|---|---|---|---|---|---|
| `recipes/dbt-bigquery` | `3709f35d56` | 1.12.1 build 1 | v1 | rxm7706, maresb, thewchan | `recipe.yaml` |
| `recipes/dbt-postgres` | `c18adc1194` | 1.11.0 build 0 | v0 | maresb, rxm7706 | `meta.yaml` |
| `recipes/dbt-redshift` | `d9d9bdba74` | 1.11.1 build 0 | v0 | rxm7706, maresb, thewchan | `meta.yaml`, `LICENSE.md` |

conda-forge latest matches the table. No feedstock moved past these versions at read time.

### Mirror diffs from feedstock (allowed / recorded)

- **`recipes/dbt-bigquery` (C2):** Replaced `dbt-core` mirror with feedstock `recipe.yaml` body; removed local `meta.yaml` (G94); literal `package.name`; canonical `source.url` (sha256 verified); full CFE block; feedstock URL token in `cfe-forge-recipe-updates-needed`.
- **`recipes/dbt-postgres` (C1):** `meta.yaml` byte-identical to feedstock; v1 `recipe.yaml` via `conda-recipe-manager convert` + host `python ${{ python_min }}.*` and TEST-002 python_version triad; canonical URL; CFE block with `meta-yaml-to-recipe-yaml`.
- **`recipes/dbt-redshift` (C1):** `meta.yaml` and `LICENSE.md` byte-identical; v1 `recipe.yaml` via convert + same host/test fixes; dropped `dbt-feedstock`-only maintainers with the old `dbt-core` copy; canonical URL; new CFE block.

### Maintainer audit (G53)

All three local `extra.recipe-maintainers` lists match their adapter feedstocks at read time (superset includes `rxm7706`).

### Gates (exit codes)

| Recipe | validate | optimize | check-deps | scan | conda-smithy |
|---|---|---|---|---|---|
| dbt-bigquery | 0 | 0 | 0 | 0 | 0 |
| dbt-postgres | 0 | 1 (STD-002 expected C1) | 0 | 0 | 1 (dual meta+recipe expected C1) |
| dbt-redshift | 0 | 1 (STD-002 expected C1) | 0 | 0 | 1 (dual meta+recipe expected C1) |

### linux-64 builds (isolated `--output-dir`, G52)

Pattern: `rattler-build build -r recipes/<dir>/recipe.yaml --output-dir build_artifacts/<dir> -m .ci_support/linux64.yaml -m conda_build_config.yaml --target-platform linux-64`.

| Recipe | Outcome |
|---|---|
| dbt-bigquery | success |
| dbt-postgres | success |
| dbt-redshift | success |

All three: **re-mirrored**.

### Package-name parse (AC 9)

Exit 0. Output: `dbt-core declared by: ['dbt']`; ok line for adapters. Pre-run would have exited 1 on the three `dbt-core` recipe bodies.

### Identity mismatch count (AC 11)

`extra.feedstock-name` vs `cfe-on-conda-forge-feedstock` parse at close: **2** (`recipes/dspy`, `recipes/lance-namespace-urllib3-client`).

### Retro

`retro(cfe): v8.99.6` — verify adapter directory name matches `package.name` / CFE block before refresh (Story 25.16 identity snapshot).

## Review Triage Log

### 2026-10-10 — Review pass
- verdicts: 2 findings — high 0, medium 0, low 1, false 1, maybe-false 0
- findings:
  - `[low]` `[defer]` Intermediate `wip: 25.16 (auto-checkpoint)` commits carry recipe diffs instead of per-recipe `recipes:` subjects — dispatch checkpoint artifact; content matches AC 2–7.
  - `[false]` `[reject]` Missing linux-64 builds — build logs under `build_artifacts/` and Run results table record three green builds.

## Auto Run Result

- **Summary:** Re-mirrored `recipes/dbt-bigquery`, `recipes/dbt-postgres`, and `recipes/dbt-redshift` from their adapter feedstocks; CFE retro v8.99.6; AC 9 parse exit 0; `pyforge-mason-test` and `spec_surface_reconcile.py` green.
- **Files changed:** Three recipe trees; CFE skill carriers; story spec run results and deferred row; spec-surface memlogs on `spec-pyforge-mason`, `spec-fleet-stewardship`, `spec-conda-forge-expert-rebuild`.
- **Review:** 0 patches; 1 deferred (checkpoint commit subjects); 1 rejected false finding.
- **Follow-up review recommended:** false
- **Verification:** Gates/builds documented in Run results; `pixi run --frozen -e pyforge-mason pyforge-mason-test` exit 0; AC 9 parse exit 0; `python scripts/spec_surface_reconcile.py` exit 0 after memlog.
- **Residual risks:** Two recipes still fail feedstock-name vs CFE identity parse (`recipes/dspy`, `recipes/lance-namespace-urllib3-client`) — deferred, not built here.
