---
title: '74.3: bmad-spec, bmad-build and bmad-tea carry the flag mandate in their overrides'
type: 'feature'
created: '2026-09-28'
status: 'backlog'
flag-exempt: flag-infrastructure   # the rule's own harness wiring (spec-feature-flag-governance Q2)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/dreams/feature-flag-governance.md
  - _bmad/custom/bmad-build-auto.toml
  - _bmad/custom/config.toml
  - .claude/skills/bmad-spec/customize.toml
  - .claude/skills/bmad-build/customize.toml
  - .claude/skills/bmad-tea/customize.toml
  - .claude/memory/reference/bmad-skill-customization-mechanics-verified-live-2026-09-10.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-feature-flag-governance` CAP-6: every harness hears the mandate — the Architect declares the flag, the
Builder wraps the new logic in it, TEA tests both states — through `_bmad/custom/bmad-spec.toml`, `bmad-build.toml` and
`bmad-tea.toml`, as persistent facts or review layers, never an edit to an installer-owned `SKILL.md` (success: a fresh
`bmad-build` session on a flagged story names the flag key and the two-state test unprompted, and `bmad-method update`
preserves the overrides). None of the three files exists. `marshal factory dispatch` launches `bmad-build-auto`, whose
override (`_bmad/custom/bmad-build-auto.toml`) already carries two persistent facts (Story 46.7 moved the front-door fact
there from its installer-owned `SKILL.md` so it survives updates). CAP-1 also needs the block's shape documented where
`bmad-build` reads story specs; its override is that place.

**Approach:** each skill's own `customize.toml` declares where its overrides go — `[workflow]` for bmad-spec and
bmad-build (`persistent_facts`, and `[[workflow.review_layers]]` for bmad-build), `[agent]` for bmad-tea
(`persistent_facts`). Write:
- `_bmad/custom/bmad-spec.toml` — `[workflow] persistent_facts`: the Architect mandate. A story spec of `type: feature`
  minted on or after 2026-09-28 declares a `flag:` block (key, provider — the one OpenFeature tree, default per
  environment, scope `global`, fallback — the legacy behaviour, cleanup — 90 days after ON everywhere) or a `flag-exempt:`
  value from the closed list; `fix`, `chore` and `docs` stories need neither. The shape is the Guild Spec's CAP-1 (and
  `docs/reference/story-spec-flag-block.md` once doctor Story 34.1 lands).
- `_bmad/custom/bmad-build.toml` — `[workflow] persistent_facts`: the Builder mandate (read the declared key only through
  `pyforge.core` or `django_pyforge.flags`; with the flag OFF the legacy behaviour holds; an OFF CLI verb stays listed in
  `--help`, marked disabled, and refuses with its station's usage code) — and one `[[workflow.review_layers]]` entry that
  asks, on a flagged story, whether the diff reads the declared key and whether the Verification's two-state test exists.
- `_bmad/custom/bmad-build-auto.toml` — the same Builder fact appended to its existing `persistent_facts`, because
  dispatch launches bmad-build-auto.
- `_bmad/custom/bmad-tea.toml` — `[agent] persistent_facts`: the TEA mandate (test both states through
  `pyforge.testing_kit.flags` — `flag_states`, `flagd_tree`, the CLI OFF helper, marshal Story 74.1 — never a mock of
  `waffle` or an environment variable).
- A marshal meta-test, `tests/meta/test_flag_mandate_overrides.py`, that parses the four files, asserts each mandate sits
  under the table its skill's `customize.toml` declares, and asserts no key of these files also appears in
  `_bmad/custom/config.toml` at a different path (the "ambiguous config value" HALT in AGENTS.md § Known pitfalls).
`_bmad/**` is allowlisted in `scripts/spec_surface_allowlist.txt` (the BMAD installer tree), so no Spec's `surface:`
governs these files and there is no surface reconcile.

Ledger key: `74-3-bmad-spec-bmad-build-and-bmad-tea-carry-the-flag-mandate-in-their-overrides`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / 74.1.

### Living CAP citations

- `spec-feature-flag-governance` CAP-6, and CAP-1's clause "documented where `bmad-build` reads story specs" (Guild-owned;
  Marshal's story per the Spec's table). No marshal CAP or FR (PRD § 31.11).
- Kinship: marshal Story 46.7 (`spec-pyforge-marshal` CAP-192: the `_bmad/custom/bmad-build-auto.toml` precedent);
  marshal Story 74.1 (the kit API the TEA fact names); doctor Story 34.1 (the reference page the facts point to).

## Acceptance Criteria

- Given the four override files When the meta-test parses them Then bmad-spec's and bmad-build's mandates sit under `[workflow] persistent_facts`, bmad-build's review layer under `[[workflow.review_layers]]`, bmad-build-auto's Builder fact under `[workflow] persistent_facts`, and bmad-tea's mandate under `[agent] persistent_facts`
- Given the Builder fact moved to `[agent]` in `bmad-build.toml` When the meta-test runs Then it fails (mutation)
- Given a key of these files also present in `_bmad/custom/config.toml` at a different path When the meta-test runs Then it fails
- Given `PYTHONPATH="$PWD/_bmad/scripts:$PYTHONPATH"` When `render_skill.py` renders bmad-build and bmad-build-auto Then neither HALTs and each rendered context carries the flag mandate
- Given the same shell When `resolve_customization.py` resolves bmad-spec (`--key workflow`) and bmad-tea (`--key agent`) Then each result carries its mandate
- Given the change When `git diff --stat -- .claude/skills` runs Then it is empty (no installer-owned file edited)
- Given the change When `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` and `pixi run --frozen -e pyforge-ci pyforge-deps-test` run Then both pass

## Boundaries & Constraints

**Always:**
- Write only the four `_bmad/custom/` files and the meta-test; keep the two existing bmad-build-auto facts verbatim.
- Name the mandates in plain facts that cite the Guild Spec, the reference page and the kit by path.
- Keep bmad-review's `tea-test-review` lens (`_bmad/custom/bmad-review.toml`) unchanged; it is steward's (Story 31.3).

**Never:**
- Do not edit any `SKILL.md`, `customize.toml` or step file under `.claude/skills/` (installer-owned; an update overwrites
  it).
- Do not run `bmad-method install --action update` on the primary checkout; the preservation check runs in a scratch copy
  with `--directory <scratch> --modules core,bmm,skf` (AGENTS.md § Known pitfalls).
- Do not add a key to `_bmad/custom/config.toml`.
- Do not edit `SPEC.md` or `sprint-status-ledger.yaml`; do not run `scripts/bmad-switch`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| bmad-build render | flagged story | mandate in the rendered context | no HALT |
| bmad-build-auto render | dispatched story | Builder fact present beside the two existing facts | no HALT |
| bmad-spec resolve | `--key workflow` | Architect fact present | — |
| bmad-tea resolve | `--key agent` | TEA fact present | — |
| wrong table | fact under `[agent]` for bmad-build | meta-test fails | — |
| config collision | same key in `config.toml` | meta-test fails | — |

</intent-contract>

## Source

Contract authored from `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-6 (and CAP-1's documentation clause),
the Dream's three mandates, the BMAD customization mechanics reference (`.claude/memory/reference/bmad-skill-customization-mechanics-verified-live-2026-09-10.md`)
and Story 46.7's precedent, decomposed 2026-09-28 (night) as Epic 74's mint.

## Binding

Parent Spec capability: `docs/governance/spec-feature-flag-governance/SPEC.md` CAP-6 (Guild-owned; Marshal's story).
Dream: `docs/dreams/feature-flag-governance.md` § Realization log → *2026-09-28 (night)*.
Ledger key: `74-3-bmad-spec-bmad-build-and-bmad-tea-carry-the-flag-mandate-in-their-overrides`.
Ledger status at mint: `backlog`.
Policy: `marshal-policy.toml` `[epic_surfaces]` `"74"`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Manual checks:**
- `PYTHONPATH="$PWD/_bmad/scripts:$PYTHONPATH" uv run --no-cache _bmad/scripts/render_skill.py --project-root "$PWD" --skill .claude/skills/bmad-build` (and `bmad-build-auto`) — expected: exit 0, the mandate in the output.
- `uv run _bmad/scripts/resolve_customization.py --skill .claude/skills/bmad-spec --project-root "$PWD" --key workflow` and `--skill .claude/skills/bmad-tea … --key agent` — expected: the mandate in each.
- In a scratch copy only: `bmad-method install --action update -y --directory <scratch> --modules core,bmm,skf`, then `cmp` each of the four override files against the tree — expected: identical.

## Review Triage Log
