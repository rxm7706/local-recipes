---
title: '109.7: The pilot skills and cards fix what Round 0 found'
type: 'fix'
created: '2026-10-29'
status: 'done'
baseline_revision: 'a7c42a06d9'
review_loop_iteration: 3
followup_review_recommended: false
context:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/marketplace_pages.py
  - src/shared/packages/pyforge-steward/tests/unit/test_marketplace_pages.py
  - src/shared/packages/pyforge-steward/tests/unit/test_pilot_skills.py
  - docs/foundry/marketplace/skills/mason/environment/SKILL.md
  - docs/foundry/marketplace/skills/mason/package/SKILL.md
  - docs/foundry/marketplace/skills/warden/scan/SKILL.md
  - docs/foundry/marketplace/skills/warden/scan/steps.md
  - src/shared/packages/pyforge-warden/pixi.toml
  - _bmad-output/projects/pyforge-steward/planning-artifacts/design-thinking-bmad-marketplace-2026-10-20/round0-desk-test-2026-10-29.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Round 0's Claude Code leg and Story 109.6's review left four things a teammate hits in the pilot.

1. Each skill card's Sources block says "GitHub release: not published", while the same card's Install section offers
   the rolling `pages-site` release zip. The card contradicts itself (Round 0 observation 1; part of
   `DW-steward-109-3-4`).
2. `@warden/scan`'s step 0 installs `deptry` and `osv-scanner` with no version, and names `osv-scanner` 2.4.0 as the
   verified one. conda-forge served 2.7.0 on 2026-10-29 (observation 2). `pyforge-warden` pins its engines to
   `deptry >=0.25.1,<0.26` and `osv-scanner >=2.4.0,<2.5` (`src/shared/packages/pyforge-warden/pixi.toml`
   `[package.run-dependencies]`), so the runbook installs an engine warden will not accept.
3. The three pilot `SKILL.md` files say "no path inside local-recipes" in their description and "Do not `cd` into
   local-recipes" in their body. Claude Code relayed that to a teammate who has no local-recipes (observation 3).
4. Nothing checks that a skill's `SKILL.md` frontmatter `name` is its plugin name `<scope>-<slug>`. The card's
   `<plugin>:<plugin>` listing assumes it (`DW-steward-109-6-1`).

**Approach:**

1. `_sources_html` names the GitHub source as a versioned GitHub release of the listing. When it is not published, it
   says the rolling `pages-site` pre-release under Install moves with every deploy and is not a versioned release.
2. Warden's step 0 installs both engines in `pyforge-warden`'s ranges (pip or conda for `deptry`; conda or the release
   binary for `osv-scanner`) and says why.
3. The three `SKILL.md` descriptions and bodies, the three listing descriptions (and their `index.yaml` rows) and
   `templates/SKILL.md` drop the local-recipes clauses and keep "run from the teammate's project directory". The
   pixi-selector guard stays.
4. `validate_listing` reads the `SKILL.md` frontmatter for a skill and refuses, by name, a missing or unparsable
   frontmatter or a `name` that is not exactly `<scope>-<slug>`.

Regenerate `site/`. A fix needs no flag (`spec-feature-flag-governance` Q1).

## Acceptance criteria

1. A skill card's Sources block (only skill cards render one) names a versioned GitHub release of the listing. When
   that release is not published, the block says the rolling `pages-site` pre-release under Install moves with every
   deploy and is not a versioned release of this listing; when it is, the block says published and nothing else.
2. `skills/warden/scan/steps.md` step 0 installs `deptry` in `>=0.25.1,<0.26` and `osv-scanner` in `>=2.4.0,<2.5`, the
   ranges `pyforge-warden` pins: pip and conda forms for `deptry`, conda or the v2.4.0 release binary for
   `osv-scanner`. It says that `osv-scanner` 2.5 or later is outside warden's range.
3. No pilot `SKILL.md`, `steps.md` or `listing.yaml`, no `index.yaml` row and not `templates/SKILL.md` names
   local-recipes; the card descriptions follow from the listings. Each pilot `SKILL.md` still says to run from the
   teammate's project directory, and still says not to prefix commands with a pixi environment selector.
4. `validate_listing(row, root=...)` refuses a skill whose `SKILL.md` has no frontmatter, unparsable frontmatter, or a
   `name` that is not exactly `<scope>-<slug>`, naming the listing and the expected name; the PR template's § Listing
   carries the rule as a checkbox. The three committed listings pass.
5. The committed `docs/foundry/marketplace/site/` matches a fresh render. The tests pin each change and refuse the old
   text.

## Boundaries

- Do not edit the estate skills under `.claude/skills/`, `CatalogEngine.render` or `registry/estate.yaml`. Do not add a
  steward CLI duty.
- Change no listing field but `description` (the local-recipes clause), in `listing.yaml` and its `index.yaml` row
  alike, and nothing about what is published.
- From `DW-steward-109-3-4` this story takes only the Sources block's contradiction with the `pages-site` pre-release; the
  block's placement and the row's other items stay open.

</intent-contract>

## Verification

**Commands:**

- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_marketplace_pages.py src/shared/packages/pyforge-steward/tests/unit/test_pilot_skills.py -q`
  — expected: exit 0.
- `pixi run --frozen -e pyforge-steward python -c "from pathlib import Path; from pyforge.steward.marketplace_pages import write_plugin_manifests, write_site_from_index; r = Path('docs/foundry/marketplace'); write_site_from_index(r / 'index.yaml', r / 'site'); write_plugin_manifests(r / 'index.yaml')"`
  from the repository root, then `git diff --exit-code docs/foundry/marketplace/`. Expected: exit 0.
- `git grep -n local-recipes -- docs/foundry/marketplace/skills/ docs/foundry/marketplace/templates/ docs/foundry/marketplace/index.yaml`
  — expected: no output.

**Manual checks:**

- The `@warden/scan` card reads with one answer about the release.

## Review (loop 1)

2026-10-29, independent (a fresh subagent over the staged diff and this spec). Verdict **FAIL** on four rows. The three
Verification commands passed (189 tests; a scratch re-render `diff -r` empty; no `local-recipes`), the Boundaries held,
and seven mutants were killed.

| Row | Blocking | Location | Finding | Fix asked |
|---|---|---|---|---|
| 1 | yes | `_validate_skill_name` | The unparsable-YAML and non-UTF-8 refusals omit the expected name AC4 asks for | Name it in both |
| 2 | yes | warden `steps.md`; `test_pilot_skills.py` | AC2's "a newer `osv-scanner` is outside warden's range" sentence is pinned by no test | Assert it |
| 3 | yes | README § Listing rules; PR template § Listing | The README says each `validate_listing` rule is a § Listing checkbox; the new rule has none | Add the checkbox |
| 4 | yes | `_sources_html`; the three cards | "The `pages-site` zip … is not a tagged release" is untrue: `pages-site` is a tagged pre-release | Name the listing's own release as versioned; say what the pre-release is |
| 5 | no | the three `SKILL.md` § What this skill is not | "Does not replace the estate procedure under `.claude/skills/…`" is estate wording, the same class as Round 0 observation 3, and names the path the teammate installs into | Drop it |
| 6 | no | `test_pilot_skills.py`; `pyforge-station-tests.yml` | The new read of `pyforge-warden/pixi.toml` is not in `steward_live_paths`, and the derivation misses an inline literal | A module constant; add the path |
| 7 | no | the name-rule cases | A case-folding compare survives | A mixed-case case |
| 8 | no | `_validate_skill_name`; `_load_yaml` | Deeply nested YAML raises a raw `RecursionError` | Catch it |
| 9 | no | `_validate_skill_name` | A BOM is refused as "no frontmatter"; duplicate `name` keys pass when the last matches | Name the BOM; optionally refuse duplicate keys |
| 10 | no | `DW-steward-109-3-4`, `DW-steward-109-6-1` | "Takes the cards' Sources block" over-claims: the block still reads as a second unpublished list; 109-6-1 to close at landing | Narrow the claim; close 109-6-1 |
| 11 | no | `mason/package/SKILL.md` description | One line past the file's wrap | Re-wrap |
| 12 | no | `test_no_pilot_text_names_local_recipes` | Removing the body's "Run from the teammate's project directory" survives (the description also says it) | Assert the body sentence |

## Fixes (loop 1)

Rows 1–8, 10–12 and the BOM half of row 9 landed the same day. Every `_validate_skill_name` refusal names the expected
name; a BOM is named; `RecursionError` is caught there and in `_load_yaml`. The step-0 sentence is pinned. The PR
template's § Listing has the checkbox. The Sources line reads "Versioned GitHub release of this listing: not published;
the rolling `pages-site` pre-release under Install moves with every deploy and is not a versioned release of this
listing" (AC1, the epic, the Dream and the test follow). The three estate-procedure sentences are gone. `_WARDEN_PINS` is
a module constant and `steward_live_paths` names `src/shared/packages/pyforge-warden/pixi.toml` (the trigger-map
meta-test passes). A mixed-case name and a nested document are refused cases. `DW-steward-109-6-1` is closed and
`DW-steward-109-3-4` carries a `partial:` line naming only the release contradiction. The package description is
re-wrapped; the body sentence is pinned.

Not taken: row 9's duplicate-key half. PyYAML keeps the last key, and `_load_yaml` reads every `listing.yaml` the same
way; refusing duplicate keys only in `SKILL.md` would split the rule. How Claude Code reads a duplicate `name` key is
untested; a JavaScript YAML parser may refuse it. A verification pass follows.

## Review (loop 2, verification)

2026-10-29, a fresh subagent (a first attempt stopped on an expired token and was rerun). Eleven loop-1 rows closed or
declined with a true reason (PyYAML keeps the last duplicate key; js-yaml and eemeli/yaml refuse one); every requested
mutant was killed; 243 tests passed; a scratch re-render `diff -r` empty twice; "moves with every deploy" holds as
`pages.yml` and the dev overlay are configured. Verdict **FAIL** on three rows.

| Row | Blocking | Location | Finding | Fix asked |
|---|---|---|---|---|
| 1 | yes | `_validate_skill_name`, the BOM refusal | Does not name the expected name, so AC4 and loop-1 § Fixes overstate | Name it; extend the needle |
| 2 | yes | the name-rule tests | The non-UTF-8 and no-frontmatter suffixes are unpinned; no test writes a non-UTF-8 `SKILL.md` | A bytes case; suffixes in the needles |
| 3 | yes | `epics.md` Story 109.7; this spec's Boundaries | Still say the story "takes the cards' Sources block" from a DW row whose `partial:` line keeps the placement open | Name only the contradiction |
| 4 | no | `_load_yaml` | Its `RecursionError` catch survives removal | A nested index case |
| 5 | no | test names and comments | Still say "tagged release" | "Versioned" |
| 6 | no | card Install vs Sources; README | "Release" in Install, "pre-release" in Sources | One word |
| 7 | no | warden `steps.md`; AC2; the pin | "A newer `osv-scanner`" overstates: 2.4.x is newer and inside the range | "2.5 or later" |
| 8 | no | AC2, Approach 2 | Pip and conda forms for both; `osv-scanner` has conda and the release binary | Say which |
| 9 | no | `epics.md` Surface | Omits the PR template, the workflow and the new `pixi.toml` read | Name them |
| 10 | no | the Dream entry | Quotes text no file says | Paraphrase |
| 11 | no | `_sources_html` fallback | Unpinned | A no-sources case |
| 12 | no | the estate-procedure pin | A reworded sentence survives | Refuse "does not replace" too |

## Fixes (loop 2)

All twelve rows landed the same day, in the reviewer's wording where one was given. The BOM refusal names the expected
name; the no-frontmatter needles carry the suffix; a non-UTF-8 `SKILL.md` and a deeply nested `index.yaml` are refused
cases; the fallback text has a case; test names say "versioned". The card's Install section and the README say "the
rolling `pages-site` pre-release", as Sources does. Warden's step 0 says "`osv-scanner` 2.5 or later … is outside that
range", and AC2 and Approach 2 name the install forms per engine. `epics.md` and the Boundaries name only the Sources
block's contradiction; the Surface names the PR template, the README, the workflow and the `pixi.toml` read; the Dream
entry paraphrases. 366 tests pass with ruff, format and mypy clean. A last verification pass follows.

## Review (loop 3, verification)

2026-10-29, a fresh subagent, the last pass. Verdict **PASS**: all twelve loop-2 rows closed; every `_validate_skill_name`
refusal names the listing and the expected name; 246 tests passed; a scratch re-render with `site/` and both manifests
deleted first is `diff -r` empty; every requested mutant was killed; the Boundaries held. Six non-blocking rows:

| Row | Location | Finding |
|---|---|---|
| 1 | `epics.md` Epic 109 paragraph | Still says "the cards' Sources block", the claim loop-2 row 3 narrowed |
| 2 | `_sources_html`, the empty-mapping fallback | Unpinned |
| 3 | README § Install | The "pre-release" wording is unpinned |
| 4 | the how-to, the DW `partial:` line, `epics.md`, this spec | Still call `pages-site` a "release" |
| 5 | README § Not built yet | Names the source "GitHub release", the ambiguity the cards fixed |
| 6 | `epics.md` Surface | Omits the regenerated `.claude-plugin/marketplace.json` |

## Fixes (loop 3)

All six landed the same day: the epic paragraph names the contradiction only; an empty `sources` mapping and the README's
two sentences are pinned; the how-to, the DW line, `epics.md` and this spec say "pre-release"; README § Not built yet
names "a versioned GitHub release of the listing"; the Surface names the Claude manifest. No further loop. 109.7 is
`done`.

