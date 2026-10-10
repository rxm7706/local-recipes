---
title: "67.9: The conda-recipe-manager click notes state the cap as it stands"
type: 'fix'
created: '2026-10-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-67-4-upstream-tickets-for-the-gaps-that-need-one.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-67-5-the-estate-points-at-the-sbom.md
  - pixi.toml
  - docs/reference/library-llms-full.md
  - docs/dreams/pixi-candidate-currency.md
  - recipes/conda-recipe-manager/recipe.yaml
  - docs/foundry/sbom-gaps.md
  - scripts/llms_full_check.py
  - .claude/skills/conda-forge-expert/SKILL.md
  - docs/dreams/pyforge-steward.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** ten places in the tree still describe conda-recipe-manager's click pin as it stood on 2026-08-30. They
call the pin `click==8.2.1` and a feedstock bug, call conda-forge/conda-recipe-manager-feedstock#44 "the unpin PR", and
wait for #44 to merge. #44 closed unmerged on 2026-09-01, and the maintainers chose a cap. An agent that reads these
notes waits on a dead PR, or asks upstream for an unpin the maintainers already declined.

- **The ruling.** On 2026-10-10 the operator ruled, verbatim: "mint the stale #44 cleanup story now". It follows the
  same day's correction to Story 67.4's `sbom-crm-click-cap` seed (`spec-pyforge-steward` memlog), which recorded this
  text as stale and did not edit it.
- **What is true, verified 2026-10-10 by read-only GET (the dev re-verifies at dispatch, read-only):**
  - conda-forge/conda-recipe-manager-feedstock PR #44 ("Modify click dependency to match source") was opened by
    rxm7706 on 2026-08-30. It unpinned click and, in its third commit (`547eb6b9f9`), capped `pytest-socket` below
    0.8.0. It closed unmerged on 2026-09-01, after the maintainer declined to unpin click (minor click releases have
    broken crm before).
  - PR #46 ("Widens range of click versions…") merged on 2026-09-03. The feedstock (main `3c6421e854`) carries only the
    v0 `recipe/meta.yaml` and no `recipe.yaml`: version 0.10.6, build 1, line 29 `click >=8.2.1,<=8.4.1`. It has no
    open issue or PR.
  - Upstream caps click as well. conda/conda-recipe-manager PR #555 (merged 2026-08-31) pins `click==8.4.1` at tag
    v0.10.6; PR #559 (merged 2026-09-02) makes main `>=8.2.1,<=8.4.1`. "Upstream declares plain click" was true of
    v0.10.5 and is not true now.
  - The latest click is 8.5.0 (conda-forge/click-feedstock `recipe/recipe.yaml`).
  - `pixi.lock` on `e2e58f81c6`, parsed: click 8.4.1 and crm 0.10.6 (`pyhd8ed1ab_1`, `click >=8.2.1,<=8.4.1`) appear
    only in `grayskull` and `local-recipes`. `local-recipes` composes the `grayskull` feature, not `crm`, and gets crm
    through grayskull 3.1.1, which depends on an unversioned `conda-recipe-manager`. click 8.5.0 is in 26 other
    environments; `pyforge-foundry-full` and `-stack` hold crm 0.5.0 (`pixi.toml:1114`-`:1119`, already correct). A
    text grep counts 8 `click-8.4.1` and 65 `click-8.5.0` records.
  - The open ask, lifting the `<=8.4.1` upper bound so click 8.5.x resolves, is Story 67.4's `sbom-crm-click-cap` seed
    (`drafted`; only the operator files it).
- **The stale text (the ten places; line numbers on `e2e58f81c6`):**

  | # | Path | Lines | What it says |
  |---|---|---|---|
  | 1 | `pixi.toml` | `:100`-`:105` (the `[feature.crm.dependencies]` header) | crm's "exact click==8.2.1 pin (feedstock bug, …#44)"; that `local-recipes` "stops inheriting" crm |
  | 2 | `pixi.toml` | `:2120` (the retired `#conda-recipe-manager` line) | the exact pin, "feedstock bug, upstream pyproject declares click unpinned; …#44"; restore "after feedstock#44 merges" |
  | 3 | `pixi.toml` | `:2152` (the retired `#feedrattler` line) | "the click==8.2.1 wall" |
  | 4 | `pixi.toml` | `:2203` (headroom-ai, `[feature.local-recipes.dependencies]`) | "crm's exact click==8.2.1 feedstock pin, feedstock#44" |
  | 5 | `pixi.toml` | `:2219`-`:2225` (the dbt block) | "0.10.5 pinned `click ==8.2.1` exactly (a FEEDSTOCK BUG … #44 is the unpin PR)"; crm removed from the env "entirely" |
  | 6 | `pixi.toml` | `:2446` (headroom-ai, the linux-64 target) | as 4, with the full #44 name |
  | 7 | `docs/reference/library-llms-full.md` | `:215`-`:220` (the crm entry) | "exact click==8.2.1 pin (feedstock bug, …#44)" |
  | 8 | `docs/reference/library-llms-full.md` | `:352`-`:355` (the dbt entry) | "exact click==8.2.1 feedstock pin" |
  | 9 | `docs/dreams/pixi-candidate-currency.md` | `:104` | "the upstream fix (…#44) remains the long-term path back" |
  | 10 | `recipes/conda-recipe-manager/recipe.yaml` | `:96`-`:99` (the `# CFE comments` block) | "#44's diff, which unpins click but does not touch test deps" |

- **Left as written (dated history, not live text):** every `.memlog.md` (for example `spec-marshal-token-economy`
  `:49`, `spec-pyforge-steward` `:517`); `docs/dreams/marshal-token-economy.md:211` (an archived Dream, its gate
  resolved 2026-08-30); the 2026-08-29/30 snapshot lines of `docs/dreams/pixi-candidate-currency.md` (`:43`, `:61`,
  `:82`, `:99`, `:126`, `:174`, `:175`, `:277`, `:389`; an archived Dream whose ledgers record that session); the
  absorbed Spec companion `spec-marshal-token-economy/integration-layers.md:14`; the Story 67.1 and 67.4 specs, which
  are already correct; `docs/foundry/sbom-gaps.md:12` and `scripts/sbom_gap_derive.py:190`, which are accurate and name
  no PR. Other recipes' own `click >=8.2.1` floors are unrelated.

**Approach:** rewrite each of the ten places so that it states the facts above. Change nothing else.

- **`pixi.toml`, sites 1-6.** Comments only. Each says what is true today: crm 0.10.6 (feedstock PR #46) caps click
  `>=8.2.1,<=8.4.1`, and so does upstream; feedstock PR #44 closed unmerged on 2026-09-01; the open ask is Story 67.4's
  `sbom-crm-click-cap` seed. Where a comment keeps the 2026-08-30 history (the `crm` feature split, headroom-ai and the
  dbt trio unblocked), it names crm 0.10.5's exact click pin as history, without the literal `click==8.2.1` and without
  "feedstock bug". Site 1 and site 5 also stop saying `local-recipes` no longer carries crm: it resolves crm 0.10.6
  through grayskull 3.1.1, with click 8.4.1 (and the dbt trio and headroom-ai solve inside that cap). Site 2's restore
  condition stops waiting on #44.
- **`docs/reference/library-llms-full.md`, sites 7-8.** The catalog's reconciler is the regeneration prompt in its own
  header (`:36`-`:38`). Apply it to the crm entry and the dbt entry, and add a dated entry (the landing date) to the
  header's `Generated:` line that names this story and the two entries, in the form earlier scoped re-syncs use there.
  A full rewrite of the catalog is not asked for. `scripts/llms_full_check.py` reads `pixi.toml` through `tomllib`, so
  comments never reach it; it must still exit 0.
- **`docs/dreams/pixi-candidate-currency.md`, site 9.** An archived Dream (owner doctor, not yet folded) whose
  2026-08-30 addendum names #44 as the long-term path back. Rewrite that clause in place to the facts and mark it with
  the correction date. Leave the rest of the file as written. No Spec governs the file, and `fold-complete-check` reads
  only `archive/docs/dreams/`.
- **`recipes/conda-recipe-manager/recipe.yaml`, site 10.** Invoke `conda-forge-expert` before editing (Rule 1). The
  comment keeps its pytest-socket rationale, which is unrelated to click. It states #44's real fate: closed unmerged,
  and its final diff did cap pytest-socket, as this recipe does. It follows CFE's comment rules (`SKILL.md` § *Never Add
  AI Comments Inline*; no `${{ … }}` token in a CFE comment). The recipe's requirements, version and build number do not
  move.
- **The Rule-2 retro.** The recipe edit is conda-forge work, so the story closes with a CFE retro (Rule 2): a PATCH
  `CHANGELOG.md` entry naming this story ("no skill changes; verified existing guidance held" if the retro finds
  nothing), with every version carrier moved together (`SKILL.md`, `CHANGELOG.md`, `MANIFEST.yaml`,
  `config/skill-config.yaml`). It lands in its own commit with subject `retro(cfe): v<next PATCH> — …`, because
  `pyforge.testing_kit.branch_diff_guard` refuses a CFE-surface commit without that subject and the `CHANGELOG.md`
  move. Take the version from `CHANGELOG.md` at landing, not now (refresh waves bump it often).
- **Co-governors.** `pixi.toml` has eight governors on `e2e58f81c6` (`spec-pixi-candidate-currency`,
  `spec-deck-family-currency`, `spec-deck-family-lockstep`, `spec-pyforge-pages`, `spec-bmad-loop-baseline-drift`,
  `spec-pyforge-core`, `spec-pyforge-marshal`, `spec-pyforge-unifying-strategy`); `library-llms-full.md` has two
  (`spec-pyforge-marshal`, `spec-pyforge-steward`); the CFE carriers are governed by mason Specs. Trust the detector
  over this list: add a memlog entry naming the path and the reason on every Spec `spec-surface-check` names, `git add`,
  then one scoped stamp per named Spec from a clean tree. The recipe and the Dream are in no Spec surface.

Ledger key: `67-9-the-conda-recipe-manager-click-notes-state-the-cap-as-it-stands`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **Shipped behaviour:** `spec-python-foundry-cutover` fnd:CAP-13, the gap list (`docs/foundry/sbom-gaps.md`) and its
  `upstream` disposition, which an operator files outward. Its `feature:crm` row is correct; the `pixi.toml` comments
  and the catalog that describe the same gap are not. Story 67.4's `sbom-crm-click-cap` seed is where the open ask
  lives. This story mints no CAP and changes no `SPEC.md` text.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag. Nothing runtime changes.
- **Epic.** Epic 67 is `in-progress` (Story 67.4 is `backlog`), so the fix joins it; no new epic.
- **Ownership.** One steward story, not a mason one. `recipes/` is in no Spec surface, and Rule 1 and Rule 2 bind the
  agent that edits a recipe, whatever its station. Steward 67.5 (CFE v8.92.0), marshal 86.7 (v8.91.9) and doctor
  41.1/41.4 (v8.91.4/v8.91.5) each closed their own Rule-2 retro and reconciled mason's Specs as co-governors.

## Acceptance Criteria

- **(1) No live line keeps the stale claims.**
  `git grep -n -i -E 'unpin PR|feedstock#44|#44 merges|feedstock bug|declares (plain|click unpinned)|click ?== ?8\.2\.1' -- pixi.toml docs/reference/library-llms-full.md recipes/conda-recipe-manager/recipe.yaml`
  prints nothing (exit 1). On `e2e58f81c6` it prints 12 lines.
- **(2) Any #44 left says what happened to it.**
  `git grep -n -P '#44(?!.*closed unmerged)' -- pixi.toml docs/reference/library-llms-full.md recipes/conda-recipe-manager/recipe.yaml docs/dreams/pixi-candidate-currency.md`
  prints nothing (exit 1). On `e2e58f81c6` it prints 8 lines.
- **(3) The facts are stated.** `pixi.toml` and `docs/reference/library-llms-full.md` each contain `#46`, `<=8.4.1`,
  `8.5.0` and `sbom-crm-click-cap` (`git grep -c` returns at least 1 for each, per file).
  `docs/dreams/pixi-candidate-currency.md` contains `sbom-crm-click-cap`. Sites 1 and 5 say `local-recipes` resolves
  crm through grayskull; no comment says `local-recipes` carries no crm.
- **(4) Text only.** With `BASE=$(git merge-base HEAD origin/main)`, `pixi.toml` parses to the same value as at
  `$BASE`, and so does the recipe:
  `pixi run -e pyforge-guild python -c "import subprocess,tomllib,yaml,sys; b=sys.argv[1]; t=tomllib.loads(subprocess.check_output(['git','show',b+':pixi.toml'],text=True))==tomllib.load(open('pixi.toml','rb')); r=yaml.safe_load(subprocess.check_output(['git','show',b+':recipes/conda-recipe-manager/recipe.yaml'],text=True))==yaml.safe_load(open('recipes/conda-recipe-manager/recipe.yaml')); sys.exit(0 if t and r else 1)" "$BASE"`
  exits 0. `git diff --exit-code "$BASE" -- pixi.lock environment.yaml` exits 0, and
  `pixi project export conda-environment -e build` matches `environment.yaml` (the staged-recipes linter's sync check).
- **(5) The catalog is current.** `pixi run -e pyforge-guild llms-full-check` exits 0, and the catalog header's
  `Generated:` line names this story and the crm and dbt entries with the landing date.
- **(6) Rule 1 and Rule 2.** `conda-forge-expert` is invoked before the recipe edit. The branch carries one
  `retro(cfe):` commit that moves `CHANGELOG.md` with every version carrier, and its entry names Story 67.9. The recipe
  passes `pixi run -e local-recipes validate recipes/conda-recipe-manager` as it did at `$BASE`. The
  `test_conda_forge_expert_not_replaced` guards in the station suites stay green.
- **(7) Spec surface.** Every Spec `pixi run -e pyforge-guild spec-surface-check` names has a memlog entry naming its
  path and this story, and one scoped stamp (`python scripts/spec_surface_check.py --write-baseline --spec
  <project>/<spec>`); the check then exits 0. No bare `--write-baseline`.
- **(8) Suites and gates.** `pixi run -e pyforge-guild pyforge-station-tests` exits 0 (a `pixi.toml` change fires every
  station suite in CI); `pixi run -e pyforge-guild pr-preflight` exits 0; `governance-currency` and `detectors-ci` stay
  green.

## Boundaries & Constraints

**Always:**
- Change only these paths:
  - `pixi.toml`, the comments of sites 1-6 only;
  - `docs/reference/library-llms-full.md`, sites 7-8 and the header's `Generated:` line;
  - `docs/dreams/pixi-candidate-currency.md`, line 104's clause only;
  - `recipes/conda-recipe-manager/recipe.yaml`, the CFE comment at `:96`-`:99` only;
  - the CFE version carriers the Rule-2 retro moves (`.claude/skills/conda-forge-expert/{SKILL.md,CHANGELOG.md,MANIFEST.yaml,config/skill-config.yaml}`), and anything else the retro lands under `.claude/skills/conda-forge-expert/`;
  - the `.memlog.md` of every Spec `spec-surface-check` names, and `scripts/.spec-surface-baseline.json` through scoped stamps.
- Re-verify every fact in § Intent by read-only GET before writing it; if one has moved (a new feedstock build, a new
  click, the seed filed), write what is true at dispatch and record the difference in the Spec Change Log.
- Read every verdict from an exit code, never through a pipe.
- The PR carries the `maintenance` label (it touches paths outside `recipes/`).

**Never:**
- Never change a dependency, pin, package version, build number, pixi task, environment or lock: `pixi.lock` and
  `environment.yaml` stay byte-identical, and neither TOML nor YAML values move. (The CFE skill's own version moves
  only through the Rule-2 retro.)
- Never edit a memlog's past entries, the archived Dreams' other lines, a done story spec, `sbom-gaps.md` or the
  Story 67.4 spec.
- Never open, comment on or close anything outside this repository: no feedstock, upstream or staged-recipes PR, and
  no issue. The `sbom-crm-click-cap` seed is the operator's to file.
- Never hand-edit `SPEC.md` or `sprint-status-ledger.yaml`.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| AC (1) grep on `e2e58f81c6` | 12 lines (exit 0) |
| AC (1) grep after the story | no output (exit 1) |
| AC (2) grep on `e2e58f81c6` | 8 lines, including `pixi-candidate-currency.md:104` |
| AC (2) grep after the story | no output (exit 1) |
| A corrected comment that keeps `crm 0.10.5's exact click 8.2.1 pin` as history | passes (1): the pattern needs `==` |
| A corrected line that names `feedstock PR #44` without `closed unmerged` | fails (2) |
| `pixi.toml` with one value changed (a floor, a feature list) | fails (4) |
| `environment.yaml` rewritten with identical content | passes (4); a content change fails it |
| The archived Dream's `:43` and `:174` still say `click==8.2.1` | expected: they are dated history, outside (1) |

</intent-contract>

## Binding

- Parent Spec capability: `spec-python-foundry-cutover` fnd:CAP-13 (the gap list and its operator-filed `upstream`
  disposition). Story 67.4's `sbom-crm-click-cap` seed holds the open ask.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-10 (stale crm-click text) entry.
- Epic: Epic 67 (`in-progress`).
- Ledger key: `67-9-the-conda-recipe-manager-click-notes-state-the-cap-as-it-stands`.
- Ledger status at mint: `backlog`.
- Deps: —. The text names the seed by id and story; it does not need Story 67.4's registry file to exist.
- Spec: `spec-python-foundry-cutover/.memlog.md` records the ruling, the evidence and the mint; `spec-pyforge-steward/
  .memlog.md` records the mint. `SPEC.md` is untouched and no CAP is minted.
- Surface: Epic 67's `[epic_surfaces]` entry already holds `pixi.toml`, `pixi.lock`, `environment.yaml`,
  `docs/reference/library-llms-full.md`, `scripts/.spec-surface-baseline.json` and `.claude/skills/conda-forge-expert/**`;
  this mint adds `docs/dreams/pixi-candidate-currency.md`, `recipes/conda-recipe-manager/recipe.yaml` and every Spec
  memlog.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks (not a dispatch gate):**
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlogs and scoped stamps. (Moved here 2026-10-10 for the same reason as `llms-full-check`: steward's `verify_commands` is only `pyforge-steward-test`; the dispatch's own surface guard still runs spec-surface.)
- `pixi run -e pyforge-guild llms-full-check` — expected: exit 0. (Moved here 2026-10-10: dispatch binds `**Commands:**` only to the station's `verify_commands` plus the surface guard, and refused launch with MRS-DISP-050 / MRS-GATE-011 while this was listed above.)
- AC (1) and AC (2) greps — expected: no output, exit 1 each.
- AC (4) comparison and `git diff --exit-code "$BASE" -- pixi.lock environment.yaml` — expected: exit 0.
- `pixi run -e pyforge-guild pyforge-station-tests` and `pixi run -e pyforge-guild pr-preflight` — expected: exit 0.
- `pixi run -e local-recipes validate recipes/conda-recipe-manager` and `pixi run -e local-recipes test` — expected: the
  same verdict as at `$BASE`, and the CFE offline suite green after the retro.

## Named, not fixed here

- `recipes/conda-recipe-manager/` mirrors 0.10.5 build 0 with a plain `click`, while the feedstock is 0.10.6 build 1
  with `click >=8.2.1,<=8.4.1` and runs its tests differently. Refreshing the local mirror is a dependency change and is
  mason's (the refresh campaign); the Rule-2 retro may record it.
- Lifting the cap upstream is Story 67.4's `sbom-crm-click-cap` seed, filed only by the operator.

## Spec Change Log

- 2026-10-10: minted from the operator's ruling "mint the stale #44 cleanup story now".

## Review Triage Log

- 2026-10-10: bmad-build-auto pass — AC (1)–(6) verified locally; `spec_surface_reconcile.py` OK after memlogs; `pyforge-steward-test` green post `retro(cfe):` commit.

## Auto Run Result

Status: done

Implemented comment-only updates at all ten stale sites; CFE retro v8.99.11 in commit `96e7267592`. Branch: `dispatch/pyforge-steward/67.9` (merge `origin/main` before PR — branch tip predates main’s doctor chain.py additions).
