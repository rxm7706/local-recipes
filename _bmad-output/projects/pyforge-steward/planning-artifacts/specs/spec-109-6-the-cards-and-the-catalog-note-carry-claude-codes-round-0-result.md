---
title: "109.6: The cards and the catalog note carry Claude Code's Round 0 result"
type: 'fix'
created: '2026-10-29'
status: 'done'
baseline_revision: 'f18ae5d3c4'
review_loop_iteration: 2
followup_review_recommended: false
context:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/marketplace_pages.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/catalog.py
  - src/shared/packages/pyforge-steward/tests/unit/test_marketplace_pages.py
  - src/shared/packages/pyforge-steward/tests/unit/test_catalog.py
  - docs/foundry/marketplace/site/skills/
  - docs/foundry/marketplace/README.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/design-thinking-bmad-marketplace-2026-10-20/round0-desk-test-2026-10-29.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/design-thinking-bmad-marketplace-2026-10-20/tool-support-matrix.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Round 0's Claude Code leg (Story 109.5, recorded in
`planning-artifacts/design-thinking-bmad-marketplace-2026-10-20/round0-desk-test-2026-10-29.md`) found that Claude
Code 2.1.311 does not read `.agents/skills/`, and that a plugin install from `docs/foundry/marketplace` exposes the
skill as `<scope>-<slug>:<scope>-<slug>`. PR #2336 moved the README and the tool matrix. The generated text did not
move: each skill card's Install section says the tool matrix marks Claude Code reading `.agents/skills/` as uncertain,
and calls `marketplace.json` a discovery pointer until Round 0 confirms a plugin install. `steward catalog pointers`
prints the same in its `github_note` while `edit_store.mirrors` is empty. A teammate reading either is told to wait
for a result that exists.

**Approach:** Change the strings, not the behaviour. In `render_skill_card`
(`src/pyforge/steward/marketplace_pages.py`), the first Install paragraph says Claude Code does not read
`.agents/skills/` (Round 0, 2.1.311, 2026-10-29) and keeps the tool-matrix link for Devin; the plugin paragraph names
`/plugin marketplace add <checkout>/docs/foundry/marketplace`, then `/plugin install <plugin>@pyforge-bmad-marketplace`,
the `<plugin>:<plugin>` listing and "the plugin or the folder copy in one project, not both", and keeps the Codex
manifest a discovery pointer until its Round 0 row runs, in the README's words. In `CatalogEngine.pointers`
(`src/pyforge/steward/catalog.py`), one Round 0 sentence about the Claude marketplace file closes `github_note` in both
of its branches (mirrors named or not), replacing the discovery-pointer sentence. Regenerate the committed `site/`
cards with the README's command. A fix needs no flag (`spec-feature-flag-governance` Q1); the cards still render only
while `pyforge.steward.marketplace_pages` is on.

## Acceptance criteria

1. A rendered skill card's Install section says Claude Code does not read `.agents/skills/`, names both plugin
   commands with the card's own plugin name and `pyforge-bmad-marketplace`, lists the skill as `<plugin>:<plugin>`, and
   says to use the plugin or the folder copy in one project, not both.
2. The card no longer says the tool matrix marks Claude Code reading `.agents/skills/` as uncertain, and no longer
   says the folder copy is the install until Round 0 confirms a plugin install. It still links the tool matrix and
   `MANUAL-CHECKLIST.md` (Round 0), and the Codex manifest is still called a discovery pointer.
3. `steward catalog pointers` prints a `github_note` that carries the Round 0 sentence with and without mirrors, and
   no longer says "until Round 0 confirms".
4. The committed `docs/foundry/marketplace/site/` matches a fresh render from `index.yaml`.
5. The tests in `test_marketplace_pages.py` and `test_catalog.py` pin the new sentences and refuse the old ones.

## Boundaries

- Do not edit `CatalogEngine.render` or `registry/estate.yaml`. Do not add a steward CLI duty.
- Do not change `codex_note` or what the Codex manifest is called: its Round 0 row has not run.
- Do not change the printed `claude_plugin_add` line or any manifest's content.
- The dated records that quote the 2026-10-20 matrix (the PRD, the 2026-10-21 Dream entry, Story 109.4's spec) stay
  as written.

</intent-contract>

## Verification

**Commands:**

- `pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/unit/test_marketplace_pages.py src/shared/packages/pyforge-steward/tests/unit/test_catalog.py -q`
  — expected: exit 0.
- `pixi run --frozen -e pyforge-steward python -c "from pathlib import Path; from pyforge.steward.marketplace_pages import write_plugin_manifests, write_site_from_index; r = Path('docs/foundry/marketplace'); write_site_from_index(r / 'index.yaml', r / 'site'); write_plugin_manifests(r / 'index.yaml')"`
  (the README's regenerate command, from the repository root), then `git diff --exit-code docs/foundry/marketplace/`
  — expected: exit 0 (the committed tree is a fresh render).

**Manual checks:**

- The `@warden/scan` card's Install section reads the way the README's plugin paragraph reads.

## Review (loop 1)

2026-10-29, independent (a fresh subagent; the diff against `origin/main` `f18ae5d3c4` and this spec, not the
implementer's summary). Verdict **FAIL** on row 1. AC1–AC5 met and the Boundaries held; three mutants (the old
"uncertain" sentence restored, `{plugin}:{plugin}` cut to `{plugin}`, the Round 0 sentence in the no-mirror branch
only) were killed.

| Row | Blocking | Location | Finding | Fix asked |
|---|---|---|---|---|
| 1 | yes | `marketplace_pages.py` plugin paragraph; `site/skills/mason/*.html`; `catalog.py` `github_note` | Round 0 ran the plugin install on `@warden/scan` only (its record lists the other two skills under "Not covered"), but the mason cards say Round 0 found their plugin install works and the note says "each listing's skill" | Credit the result to the skill tested ("run on `@warden/scan`"), keep each card's own commands, say "a listing's skill" |
| 2 | no | `catalog.py` `github_note`, read with `format_pointers` | The sentence closes a note about the github source and follows a one-session line that adds the estate catalog (`pyforge-estate-catalog`, no skill plugins), so a reader can take the github or git source as tested, or install from the wrong marketplace | Say the add was from a local checkout of `docs/foundry/marketplace`, not the estate catalog, and that the github and git sources were not exercised |
| 3 | no | card plugin paragraph; `github_note` | "Not both" with no reason; the README gives one | Add "with both, the skill is likely listed twice (not tested)" |

## Fixes (loop 1)

All three rows landed the same day. The card's plugin paragraph reads "For Claude Code, a plugin install exposes the
skill (Round 0, 2026-10-29, run on `@warden/scan`): …" with the card's own commands, and ends "not both; with both,
the skill is likely listed twice (not tested)". The `github_note` sentence names `@warden/scan`, says "a listing's
skill", says the add was a local checkout of `docs/foundry/marketplace` and not the estate catalog the one-session line
adds, says the github and git sources were not exercised, and carries the same "not both" reason. The tests pin each
(`test_marketplace_pages.py` and both `test_catalog.py` pointer tests); `site/` regenerated.

## Review (loop 2, verification)

2026-10-29, a fresh subagent (row verifier) over the loop-1 diff. Verdict **PASS**: rows 1–3 closed, Boundaries held,
285 passed, 11 mutants of the new clauses killed, the committed `site/` equal to a fresh render (`diff -r` empty).

| Row | Blocking | Location | Finding | Disposition |
|---|---|---|---|---|
| 1 | no | card plugin paragraph; `github_note`; README plugin paragraph | The text presents the `/plugin` slash commands as what Round 0 found, but Round 0 ran `claude plugin marketplace add` / `install --scope local`, and its record lists the interactive `/plugin` session as not covered | Fixed the same day (§ Fixes (loop 2)) |
| 2 | no | `render_skill_card` | `<plugin>:<plugin>` assumes the SKILL.md `name` is the plugin name; true for all three listings and `templates/SKILL.md`, but not enforced | Deferred as `DW-steward-109-6-1`: the fix adds a refusal to the listing validator, new behaviour outside this `type: fix` text story |

## Fixes (loop 2)

Row 1: the card, the `github_note` and the README's plugin paragraph each say the install ran on `@warden/scan` "with
the `claude plugin` CLI at local scope, not in an interactive session". The card and pointer tests pin the clause;
`site/` regenerated; 285 passed. Row 2 is `DW-steward-109-6-1`. No further loop: the row-1 change is a pinned clause in
three sentences. 109.6 is `done` for the landing.
