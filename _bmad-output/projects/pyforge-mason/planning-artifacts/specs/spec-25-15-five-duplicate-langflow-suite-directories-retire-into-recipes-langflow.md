---
title: "25.15: Five duplicate langflow-suite directories retire into recipes/langflow"
type: 'fix'
created: '2026-10-09'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - docs/specs/feedstock-refresh.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-5-track-b-batch-1-refreshes-airflow-code-editor-through-django-countries.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-7-track-b-batch-3-refreshes-jhub-apps-through-niquests.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-25-14-wave-f-s-other-18-packages-are-built-by-their-feedstock-s-own-mirror.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 25.14's mint found six recipe directories that declare packages another local recipe already
builds, the mirror of the feedstock that publishes them:
- `recipes/lfx`, `recipes/lfx-arxiv`, `recipes/lfx-docling`, `recipes/lfx-duckduckgo` and `recipes/lfx-ibm` each hold
  a copy of `langflow-suite` at 1.11.3 and declare all eight of its outputs. `recipes/langflow`, the mirror of
  `langflow-feedstock`, builds the same eight at 1.11.4.
- `recipes/dbt` and `recipes/dbt-core` both build `dbt-core` 1.12.2.

No repo check refuses this. The copies drift: they sit a version behind. They also mislead. Story 25.2's Wave A matched
the four bundles to these directories by name and bucketed them `v1-ahead`, and Story 25.7 had queued `recipes/lfx` for
a refresh of its own. The operator ruled on 2026-10-09, choosing "Retire in a fix story": "Mint a mason fix story that
removes the six duplicate dirs (folded into recipes/langflow and recipes/dbt-core) and drops recipes/lfx from 25.7's
batch." This is that story.

**Ownership, verified at mint (2026-10-09, read-only GETs).** Before scoping, the mint checked each directory against
three sources: conda-forge's `feedstock-outputs` registry, the atlas's `packages.feedstock_name` (atlas built
2026-10-09), and `gh api repos/conda-forge/<dir>-feedstock`.

| Directory | `conda-forge/<dir>-feedstock` | Registry and atlas owner of the directory's name | What the directory declares | Verdict |
|---|---|---|---|---|
| `recipes/lfx` | 404 | `langflow` | `langflow-suite` 1.11.3, all 8 outputs | retire |
| `recipes/lfx-arxiv` | 404 | `langflow` | the same | retire |
| `recipes/lfx-docling` | 404 | `langflow` | the same | retire |
| `recipes/lfx-duckduckgo` | 404 | `langflow` | the same | retire |
| `recipes/lfx-ibm` | 404 | `langflow` | the same | retire |
| `recipes/dbt` | **exists**: v1, `main` at `8f2435b850` (2026-09-19), publishes `dbt-core` 1.12.5 | `dbt` (the registry gives `dbt` and `dbt-core` to `dbt`) | `dbt-core` 1.12.2 | **kept** |

The registry gives `langflow`, `langflow-base`, `langflow-sdk`, `lfx` and the four `lfx-*` bundles to `langflow` alone.
`langflow-suite` has no entry, because it is a recipe name, not a package. The atlas agrees on every name.

**Why `recipes/dbt` is kept.** It is the local mirror of a real conda-forge feedstock of its own name.
`conda-forge/dbt-feedstock` exists and builds `dbt-core`. The repo's mirror path is `recipes/<feedstock>/` (Story 17.1;
`recipes/langflow` and `recipes/db-gpt` follow it), and `recipes/dbt` is that directory. Its `extra.feedstock-name` is
`dbt`, and its CFE block names `https://github.com/conda-forge/dbt-feedstock`. The 2026-08-20 inventory commit
(`d204da00fd`) stamped that block and dropped the directory's v0 `meta.yaml`, as C2 says for a v1 feedstock.
`recipes/dbt-core`, by contrast, has no feedstock of its own name (404) and no CFE block. It still carries the 1.8.9
`meta.yaml` that both directories held at the repo's first commit. Retiring `recipes/dbt` would delete the dbt-feedstock
mirror and keep the misnamed copy. So this story leaves both dbt directories alone, and open question 1 takes the pair
back to the operator.

**What the five carry that `recipes/langflow` lacks (G53 superset, read at mint).**
- Maintainers: `rxm7706` and `pb01ka` in all six directories.
- Outputs, tests and patches: `recipes/langflow` has every output and test of the five. It adds a py3.14 import test,
  two runtime checks and patches 0004 and 0005. The five list patches 0001 to 0003 but carry no `patches/` directory,
  so none of them builds as it stands.
- Pins: the only differences are older pins that `recipes/langflow` loosened on purpose. In `langflow-base`,
  `bcrypt ==4.0.1` is now `>=4.0.1,<5` and `onnxruntime >=1.20,<1.24` is now `>=1.20`. In the `run_constraints` of
  `langflow-base` and `langflow`, `langchain-chroma >=0.2.6,<0.3.0` is now `<2.0.0`.
- Files: each holds a `LICENSE`, the monorepo's MIT text. `recipes/langflow` pruned its copy on purpose, and
  `langflow-feedstock`'s `recipe/` carries none (G94).
- CFE records, all stale. `recipes/lfx` reads `blocked-pending-prerequisites`. The four bundles read
  `pending-approval-on-conda-forge` and name staged-recipes PRs #33977 to #33980. Read live at mint: #33977
  (`lfx-arxiv`) and #33978 (`lfx-docling`) are still open, authored by `rxm7706`, though `langflow-feedstock` now
  publishes both bundles. #33979 and #33980 are closed.

So nothing needs folding at mint. Each item is recorded instead (AC 2).

**Other references to the five paths (read at mint).** `git grep` finds the five paths in three kinds of place only:
- planning records: `epics.md`, the Epic 25 story specs, memlogs, and the Dream's realization log;
- the verbatim archive `archive/docs/specs/langflow-conda-forge.md`, with five `blob/main/recipes/lfx*` links;
- warden's validation corpus, `src/shared/packages/pyforge-warden/tests/fixtures/corpus/recipes/lfx*`. It is a frozen
  harvest snapshot that only warden re-harvests, and its hashes sit in `scripts/.spec-surface-baseline.json`.

No doc, manifest, test, CFE allowlist, workflow or data file names them. The refresh-wave manifests and reports are
gitignored, and the primary checkout held none at mint.

**Approach:**
1. Re-read the registry, the atlas and the feedstocks live (AC 1), and repeat the superset comparison (AC 2).
2. Remove the five directories in one commit (AC 3).
3. Prove each of the eight names has one declarer (AC 4), and that no reference to the five paths remains (AC 5).
4. Validate and build `recipes/langflow` (AC 6).
5. File the follow-ups (AC 9), and close with the Rule-2 retro (AC 10).

Ledger key: `25-15-five-duplicate-langflow-suite-directories-retire-into-recipes-langflow`.
Ledger status at mint: `backlog`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-35 (FR-57), the refresh campaign; CAP-20, the recurring campaigns; CAP-23, the CFE
  machinery. No new CAP, so no FR moves.
- AD-1 (no recipe knowledge in Mason's code); AD-15 (the CFE surface moves only in the `retro(cfe):` commit).
- CFE Rule 1 and Rule 2; G52, G53, G72 (a suite owns its folded siblings' outputs) and G94 (prune what the feedstock
  no longer has); SKILL.md § *Local-mirror fidelity*.
- `spec-fleet-stewardship` CAP-1 (`recipes/<feedstock>/`, absorbed into `spec-pyforge-mason`) governs `recipes/**`, with
  `surface-drift: exempt`; `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` CAP-1, Q1: a fix carries no flag.
- Siblings: Story 25.7 refreshes `recipes/langflow`, and no longer `recipes/lfx` (ruling 2). Story 25.14 depends on
  this story. Story 25.5 refreshes `recipes/dbt-core` and `recipes/dbt-bigquery` (open questions 1 and 2).

## Acceptance Criteria

1. **Ownership re-read first.** Given the five directories When the story starts Then § *Run results* records, before
   any file changes:
   - for each of the eight names `recipes/lfx` declares, its `feedstock-outputs` entry
     (`https://raw.githubusercontent.com/conda-forge/feedstock-outputs/main/outputs/<c1>/<c2>/<c3>/<name>.json`) and its
     atlas `packages.feedstock_name`;
   - for each of the five directory names, the HTTP status of `gh api repos/conda-forge/<dir>-feedstock`.

   A directory whose own name has become a conda-forge feedstock is not removed. Neither is one that declares a name
   the registry no longer gives to `langflow` alone. Either is recorded `kept`, with the entry that kept it.
2. **Nothing lost (G53 superset).** Given each directory to remove and `recipes/langflow` When the story compares their
   maintainers, each output's `requirements` (`build`, `host`, `run`, `run_constraints`), tests, patches,
   recipe-directory files and `about` Then each item a removed directory has and `recipes/langflow` lacks ends one of
   two ways:
   - folded into `recipes/langflow` through conda-forge-expert, in its own commit before the removal;
   - or recorded in § *Run results* with its reason.

   The mint read (§ *Intent*) found nothing to fold. A fold that changes `recipes/langflow` is rebuilt under AC 6.
3. **The five directories are gone.** Given the removal commit When
   `git ls-files -- recipes/lfx recipes/lfx-arxiv recipes/lfx-docling recipes/lfx-duckduckgo recipes/lfx-ibm` runs
   Then it prints nothing, and none of the five exists in the working tree. The removal is one `git rm -r` commit with a
   `recipes: …` subject. `git diff --name-only origin/main...HEAD -- recipes/` lists only files under the five
   directories, plus `recipes/langflow/` if AC 2 folded anything.
4. **One declarer per name.** Given the tree after the removal When the § *Verification* parse runs over every
   `recipes/*/recipe.yaml`, and every `meta.yaml` with no `recipe.yaml` beside it, reading `package.name` and each
   `outputs[].package.name` Then it exits 0. Each of `langflow-sdk`, `lfx`, `lfx-duckduckgo`, `lfx-arxiv`, `lfx-ibm`,
   `lfx-docling`, `langflow-base` and `langflow` is declared by `recipes/langflow` alone, whose `extra.feedstock-name`
   is `langflow`. At mint the parse exits 1 and names six directories for each name. § *Run results* records the
   command, its output and its exit code.
5. **No reference to the removed paths.** Given the tree after the removal When this command runs Then it finds nothing
   (exit 1):

   ```bash
   git grep -nE 'recipes/(lfx|lfx-arxiv|lfx-docling|lfx-duckduckgo|lfx-ibm)([^-a-z0-9_.]|$)' -- . \
     ':(exclude)archive/**' ':(exclude)docs/dreams/**' \
     ':(exclude,glob)_bmad-output/projects/*/planning-artifacts/**' \
     ':(exclude)src/shared/packages/pyforge-warden/tests/fixtures/corpus/**' \
     ':(exclude)scripts/.spec-surface-baseline.json'
   ```

   The exclusions are records, not references. Planning artifacts and the Dream are the dated decision record.
   `archive/` stays verbatim (`archive/docs/README.md`). Warden's corpus is a frozen harvest snapshot under its own
   path, and only warden re-harvests it. A gitignored refresh-wave manifest or report under
   `.claude/data/conda-forge-expert/feedstock-update/` or `.claude/data/conda-forge-expert/refresh-waves/` that names
   a removed directory is listed in § *Run results*; it stays local.
6. **The survivor validates and builds.** Given `recipes/langflow` after the removal When these run Then none reports
   an error, and an expected finding is recorded with its reason:
   - `pixi run -e local-recipes validate recipes/langflow`;
   - `pixi run -e local-recipes lint-optimize recipes/langflow`;
   - `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge recipes/langflow`.

   Then a linux-64 `rattler-build build --recipe recipes/langflow/recipe.yaml --output-dir <isolated dir>` exits 0
   with all eight outputs, resolving from conda-forge and never from a shared local channel (G52). If the test
   environment cannot solve, the block is recorded as G95 says. § *Run results* records each command's exit code and
   the eight package files. `recipes/langflow`'s `cfe-local-build-*` fields change only if AC 2 changed the recipe:
   Stories 25.7 and 25.14 own its refresh.
7. **The dbt pair untouched.** Given the story's diff When
   `git diff --name-only origin/main...HEAD -- recipes/dbt recipes/dbt-core` runs Then it prints nothing. Both stay
   until the operator answers open question 1.
8. **Nothing leaves the local repo.** Given the story's whole run When it closes Then no `git push`, `gh pr create`,
   `gh repo fork` or `gh api` write reached anything outside `rxm7706/local-recipes`; no issue or comment was opened,
   and staged-recipes PRs #33977 and #33978 were neither closed nor commented; no `mason recipe submit` or
   `mason package ship` and no CFE `submit_pr` or `prepare_submission_branch` ran.
9. **Follow-ups filed, not built.** Given the story closes When it files its findings Then this spec's `deferred:`
   frontmatter carries a row for each of these, unless the mason deferred-work ledger already names it:
   - The missing duplicate-output guard. No repo check refuses two `recipes/*` directories that declare one package
     name. The row proposes a repo-scope check that reds a new duplicate, with today's duplicates as its starting
     allowlist. It records the parse's repo-wide count at run time: 110 names at mint, `dbt-core` among them in five
     directories.
   - Staged-recipes PRs #33977 and #33978. `langflow-feedstock` publishes both bundles, so the PRs are superseded, and
     only the operator closes them.

   The story builds no guard and touches no PR.
10. **Retro and suite.** Given the story closes When the Rule-2 retro runs Then a separate `retro(cfe):` commit lands a
    CFE `CHANGELOG.md` semver entry, with the four version carriers in lockstep. It is PATCH, or MINOR if it adds a
    gotcha. A candidate: a second directory that declares a feedstock's outputs is a duplicate to retire, not a
    mirror, so check the registry before refreshing or creating one. If another Epic 25 story's retro reached `main`
    first, this one takes the next version when it merges `main`. Also
    `pixi run --frozen -e pyforge-mason pyforge-mason-test` passes.

## Tasks

1. Invoke `conda-forge-expert` and read its SKILL.md (Rule 1): § *Local-mirror fidelity*, G52, G53, G72 and G94.
   Where this spec and the skill differ, the skill wins, and the story records the difference.
2. Re-read the registry entries, the atlas rows and the feedstock repos live (AC 1).
3. Repeat the superset comparison, and fold or record each item (AC 2).
4. `git rm -r` the five directories in one commit (AC 3), never with a subject starting `Story 25.15:`.
5. Run the parse (AC 4) and the reference grep (AC 5), and check the gitignored refresh-wave data.
6. Validate, lint and build `recipes/langflow` into an isolated output directory (AC 6). Check that the dbt pair is
   untouched (AC 7).
7. File the follow-ups (AC 9). Close with the Rule-2 retro in its own commit, subject `retro(cfe): v<x.y.z> — …`
   (AC 10).
8. Reconcile every Spec `spec-surface-check` names: memlog first, then `git add`, then a scoped
   `--write-baseline --spec` for each (AGENTS.md checklist item 5).

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert` for every recipe judgement. Where this story and the skill disagree, the skill wins
  and the story records the deviation.
- Read every verdict from the exit code, never through a pipe.
- Read the registry, the atlas and the feedstocks only: raw files, or `gh api` GETs.

**Never:**
- Nothing reaches conda-forge, a feedstock or staged-recipes. No `git push`, `gh pr create`, `gh repo fork` or
  `gh api` write outside `rxm7706/local-recipes`; no issue, comment, PR close or review; no `mason recipe submit` or
  `mason package ship`; no CFE `submit_pr` or `prepare_submission_branch`.
- Do not remove a directory AC 1 records `kept`, and do not touch `recipes/dbt` or `recipes/dbt-core` (open question
  1).
- Do not touch any other recipe directory. Touch `recipes/langflow/` only for an AC 2 fold; its refresh is Story
  25.7's and Story 25.14's.
- Do not edit warden's corpus, `archive/`, or a planning record's history to clear AC 5.
- Do not build the duplicate-output guard. AC 9 files it.
- Do not edit any CFE file outside the `retro(cfe):` commit. Do not touch `src/shared/packages/pyforge-mason/`,
  `pixi.toml`, `pixi.lock` or `environment.yaml`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| happy path | five copies, nothing newer than `recipes/langflow` | removed in one commit; parse exits 0; `recipes/langflow` builds | — |
| a copy gained a feedstock | `conda-forge/<dir>-feedstock` now exists, or its registry entry moved | recorded `kept` with the entry; not removed | AC 1 |
| a copy carries something newer | a pin, test, patch or maintainer `recipes/langflow` lacks | folded through CFE before the removal, then rebuilt | AC 2, AC 6 |
| 25.7 landed first | `recipes/langflow` at 1.12.4 | the parse and the build run on the refreshed suite | — |
| test env pollution | a dependency solve fails for a package on conda-forge | rebuild isolated before recording a block | G52 |
| a new reference appears | a doc or manifest names a removed path at run time | edited to name `recipes/langflow`, or recorded if it is a record | AC 5 |
| other duplicates | names two or more other directories declare | listed in § *Run results*; not acted on | AC 9 |

## Open questions

1. **Which directory mirrors `dbt-feedstock`?** Ruling 2 named `recipes/dbt-core` the survivor. But `recipes/dbt` is
   the `recipes/<feedstock>/` mirror of `conda-forge/dbt-feedstock` (§ *Intent*), so this story keeps both and changes
   neither. Neither directory carries the feedstock's `0001-drop-experimental-parser-hard-dep.patch`, which both
   recipes list. *Recommended:* keep `recipes/dbt` as the mirror, and retire `recipes/dbt-core` instead, in a fix
   story or by re-scoping this one. Story 25.5's `dbt-core` row would then refresh `recipes/dbt`. *Alternative:* keep
   `recipes/dbt-core` and retire `recipes/dbt`, as ruling 2 reads. The dbt-feedstock mirror then lives under its
   package's name, and the CFE block moves with it.
2. **Three dbt adapter recipes carry `dbt-core`'s recipe.** The parse behind AC 4 also finds `recipes/dbt-bigquery`,
   `recipes/dbt-postgres` and `recipes/dbt-redshift` declaring `dbt-core`. Each `recipe.yaml` is a copy of the
   dbt-feedstock recipe (`context.name: dbt-core`, `extra.feedstock-name: dbt`, a `dbt_core` source URL) under a CFE
   block for the adapter. The 2026-08-16 identity snapshot (`20b2f459fa`) wrote all three. Each adapter has a feedstock
   of its own: `dbt-bigquery`'s is now v1 at 1.12.1, and `dbt-postgres`'s and `dbt-redshift`'s are v0. These are
   wrong mirrors, not duplicates, so ruling 2 does not cover them. Story 25.5 refreshes `recipes/dbt-bigquery`, and its
   dry-run will meet a `dbt-core` recipe there. *Recommended:* re-mirror the three from their own feedstocks:
   `dbt-bigquery` inside Story 25.5, and the other two in a fix story. This story records them in AC 4's list and
   changes none of them.

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-35 (FR-57), with CAP-20 and CAP-23. No new CAP.
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-10-09 (night, latest) — Ruled: Wave F stays inside
the mirrors, and five duplicate directories retire*.
Ledger key: `25-15-five-duplicate-langflow-suite-directories-retire-into-recipes-langflow`.
Ledger status at mint: `backlog`.
Deps: none. Story 25.14 depends on this story; see its Deps note.
Flag: none (a fix; `spec-feature-flag-governance` CAP-1, Q1).
Minted 2026-10-09 on the operator's ruling of that day ("Retire in a fix story"). One of the six directories the ruling
named, `recipes/dbt`, was excluded at mint, with the reason in § *Intent*.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test`. Expected: pass. This is the station's `verify_commands`;
  the story changes no Mason code.
- The AC 4 parse, from the repo root. Expected: exit 0 after the removal; exit 1 at mint.

  ```bash
  python - <<'EOF'
  import collections, pathlib, re, sys, yaml
  want = {"langflow-sdk", "lfx", "lfx-duckduckgo", "lfx-arxiv", "lfx-ibm", "lfx-docling", "langflow-base", "langflow"}
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
      if (p.parent / "recipe.yaml").exists():
          continue
      for n in re.findall(r"^\s*(?:-\s*)?name:\s*['\"]?([A-Za-z0-9_.-]+)", p.read_text(), re.M):
          if n.lower() in want:
              hits[n.lower()].add(p.parent.name)
  bad = {n: sorted(hits.get(n, ())) for n in sorted(want) if hits.get(n) != {"langflow"}}
  print(bad or "ok: each of the 8 names is declared by recipes/langflow alone")
  sys.exit(1 if bad else 0)
  EOF
  ```

- The AC 5 grep. Expected: exit 1 (no match).

**Manual checks:**
- `git ls-files -- recipes/lfx recipes/lfx-arxiv recipes/lfx-docling recipes/lfx-duckduckgo recipes/lfx-ibm` prints
  nothing.
- `git diff --name-only origin/main...HEAD -- recipes/` lists only the five removed directories, plus
  `recipes/langflow/` if AC 2 folded anything. The same diff over `recipes/dbt recipes/dbt-core` is empty.
- `pixi run -e local-recipes validate recipes/langflow` and `pixi run -e local-recipes lint-optimize recipes/langflow`
  report no errors; `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge
  recipes/langflow` reports no lint (G65); a linux-64 `rattler-build build --recipe recipes/langflow/recipe.yaml
  --output-dir <isolated dir>` exits 0 with eight outputs, or the recorded block is justified.
- `git log origin/main..HEAD --format=%s -- .claude/skills/conda-forge-expert`: exactly one `retro(cfe):` subject,
  and that commit carries `CHANGELOG.md`.
- § *Run results* carries the live ownership read, the superset comparison, the parse and grep results, the build
  outcome and the filed follow-ups.
- `pixi run -e pyforge-guild spec-surface-check`: exit 0 after the scoped stamps.

## Run results

- Not run yet.

## Review Triage Log

- No review has run yet.
