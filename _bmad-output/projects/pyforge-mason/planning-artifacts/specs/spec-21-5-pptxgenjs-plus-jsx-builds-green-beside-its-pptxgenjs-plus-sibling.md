---
title: "21.5: pptxgenjs-plus-jsx builds green beside its pptxgenjs-plus sibling"
type: 'feature'
created: '2026-09-28'
status: 'backlog'
flag-exempt: recipe-build
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - docs/dreams/pyforge-mason.md
  - .claude/skills/conda-forge-expert/SKILL.md
  - .claude/skills/conda-forge-expert/templates/nodejs/npm-recipe.yaml
  - recipes/pptxgenjs-plus/recipe.yaml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Herald will adopt `pptxgenjs-plus-jsx`, the JSX authoring layer over the `pptxgenjs-plus` engine, for
decks. `recipes/pptxgenjs-plus` exists (local, 4.2.1, built green 2026-08-25), but its description says the JSX
companion is not included. Neither package is on conda-forge (checked live on 2026-09-28). Upstream facts, checked on
2026-09-28:

- `pptxgenjs-plus-jsx` 4.3.4 on npm, published 2026-09-24, MIT.
- It is ESM (`"type": "module"`) with no `bin`, and `engines.node` is `>=24` (plus `bun >=1.3.0`).
- Its exports are `.`, `./render`, `./jsx-runtime` and `./jsx-dev-runtime`, each with a `default` condition only.
- The tarball ships a built `dist/` and `LICENSE`.
- Dependencies: `markdown-it ^14.1.0`, `@lofcz/mathlive ^0.110.6`, `mathml2omml-plus ^0.6.4`, and `pptxgenjs-plus`
  pinned exactly at `4.3.4`.
- `pptxgenjs-plus` upstream is 4.3.4 (2026-09-24) against the recipe's 4.2.1.

The JSX package's exact pin means Herald would load a 4.3.4 engine through JSX and a 4.2.1 engine directly, unless the
sibling moves too (G69). The operator ruled on 2026-09-28: package it. Packaging is not adopting, and a green local
build ends the story.

**Approach:** through `conda-forge-expert`, first move `recipes/pptxgenjs-plus` to 4.3.4.
- Recompute the npm tarball's sha256 and set `build.number: 0`, since the version changes.
- Re-read `bin`, `engines` and `dependencies` against 4.2.1 before editing (G110).
- Refresh the CFE block and rebuild.

Then author `recipes/pptxgenjs-plus-jsx/recipe.yaml` (v1) in the same canonical npm shape as that sibling, for a
bin-less library (G100 does not apply):
- `noarch: generic`, with the npm registry tarball as source.
- `pnpm install --ignore-scripts`, `npm pack --ignore-scripts`, `npm install --global ./pptxgenjs-plus-jsx-${{ version }}.tgz`
  and `pnpm-licenses generate-disclaimer --prod`.
- `node_modules/.bin` stripped (G6).
- A Windows branch that `call`s every `.cmd` shim and checks `%ERRORLEVEL%`.
- `nodejs >=24` as a floor only, never an engines-derived ceiling (G103).
- `license_file`: `LICENSE` plus `third-party-licenses.txt`.

Ledger key: `21-5-pptxgenjs-plus-jsx-builds-green-beside-its-pptxgenjs-plus-sibling`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / —.

### Living CAP citations

- `spec-pyforge-mason` CAP-31 (FR-53); AD-1; AD-15.
- `spec-fleet-stewardship` governs `recipes/**` (coverage only); `spec-packaging-factory` governs the CFE surface.
- `spec-feature-flag-governance` CAP-1, Q2: `flag-exempt: recipe-build`.
- Downstream: Herald references this story (mason 21.5) for its deck adoption and is not gated on it.

## Acceptance Criteria

- Given `recipes/pptxgenjs-plus/recipe.yaml` When it is read Then `version: "4.3.4"`, the sha256 matches the npm
  tarball, `build.number: 0`, and its CFE block records the rebuild
- Given `pixi run -e local-recipes recipe-build recipes/pptxgenjs-plus` When it runs on linux-64 Then it exits 0 and
  its existing `require('pptxgenjs-plus')` test passes
- Given `recipes/pptxgenjs-plus-jsx/recipe.yaml` When it is read Then it starts with the v1 schema header, is
  `noarch: generic`, sources `https://registry.npmjs.org/pptxgenjs-plus-jsx/-/pptxgenjs-plus-jsx-${{ version }}.tgz` at
  `version: "4.3.4"`, and has both a unix and a Windows build branch
- Given `pixi run -e local-recipes recipe-build recipes/pptxgenjs-plus-jsx` When it runs on linux-64 Then it exits 0
- Given the JSX recipe's test When it runs under Node 24 Then the `.`, `./render` and `./jsx-runtime` exports all load
  without error. ESM ignores `NODE_PATH`, so the test either `require()`s them (Node 22.12 and later load ESM through
  `require`) or imports the file URLs under `${PREFIX}/lib/node_modules/pptxgenjs-plus-jsx/dist/`
- Given the installed tree When it is listed Then no `node_modules/.bin` directory ships, and
  `third-party-licenses.txt` is present
- Given `validate_recipe`, `optimize_recipe` and the CI-parity lint When they run on both recipes Then none reports an
  error
- Given the story closes When the Rule-2 retro runs Then a separate `retro(cfe):` commit lands a CFE `CHANGELOG.md`
  semver entry

## Tasks

1. Invoke `conda-forge-expert` (Rule 1). Re-verify on the day:
   - the npm `latest` for both packages (G109; if they moved past 4.3.4, move both together to the version the JSX
     package pins);
   - the JSX package's exact pin on `pptxgenjs-plus`;
   - both packages' absence from live `channeldata.json`.
2. Bump `recipes/pptxgenjs-plus`: version, sha256 (`curl -sL <tarball> | sha256sum`), `build.number: 0`, the G110
   re-read, and the CFE block. Build it with `pixi run -e local-recipes recipe-build recipes/pptxgenjs-plus`.
3. Author `recipes/pptxgenjs-plus-jsx/recipe.yaml` from the sibling's shape. Write the ESM-aware test. Put the CFE block
   at the bottom (`cfe-upstream-registry: npm`, `cfe-source-kind: npm-registry-tarball`, `cfe-noarch: generic`).
4. Gates on both recipes: `pixi run -e local-recipes validate recipes/<name>`,
   `pixi run -e local-recipes lint-optimize recipes/<name>`, and the CI-parity lint.
5. Build with `pixi run -e local-recipes recipe-build recipes/pptxgenjs-plus-jsx`. Confirm from the artifact (G85), and
   stamp `cfe-local-build-*` on both recipes.
6. Close with the Rule-2 retro in its own `retro(cfe):` commit: the ESM-ignores-`NODE_PATH` test pattern, if it
   generalizes, and the exact-pin sibling cascade (G69) as a confirmation.
7. Reconcile every Spec `spec-surface-check` names: memlog first, `git add`, then a scoped stamp for each.

## Boundaries & Constraints

**Always:**
- Go through `conda-forge-expert`; the skill wins on any conflict and the story records the deviation.
- Move `pptxgenjs-plus` and `pptxgenjs-plus-jsx` together, to the version the JSX package pins exactly.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not copy an `engines` ceiling into run dependencies (G103).
- Do not open a staged-recipes, feedstock or upstream PR.
- Do not wire the package into Herald, `pixi.toml` or `pixi.lock`; Herald adopts it on its own chain.
- Do not touch `src/shared/packages/pyforge-mason/`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| happy path | JSX 4.3.4, sibling 4.3.4 | both build; the exports load under Node 24 | — |
| sibling not bumped | the sibling stays at 4.2.1 | two engine versions in one environment | the story bumps the sibling first (G69) |
| ESM resolution | `import` from a bare name with `NODE_PATH` set | `ERR_MODULE_NOT_FOUND` | `require()` of ESM or an absolute file URL |
| symlinks in noarch | npm writes `node_modules/.bin` | rattler rejects symlinks | strip `.bin` (G6) |
| Windows shim | a bare `npm` or `pnpm` in `build.bat` | the script exits early | `call` plus an `%ERRORLEVEL%` check |
| upstream moves | a JSX release past 4.3.4 | move both to the pinned pair | G109 |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-mason` CAP-31 (FR-53).
Dream: `docs/dreams/pyforge-mason.md` § Realization log → *2026-09-28 (night) — Proposed: Mason packages the intake
toolchain*.
Ledger key: `21-5-pptxgenjs-plus-jsx-builds-green-beside-its-pptxgenjs-plus-sibling`.
Ledger status at mint: `backlog`.
Deps: —.
Flag: `flag-exempt: recipe-build`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: pass (the station's `verify_commands`; this story
  changes no Mason code).

**Manual checks:**
- `pixi run -e local-recipes recipe-build recipes/pptxgenjs-plus` — exit 0 on linux-64 at 4.3.4.
- `pixi run -e local-recipes recipe-build recipes/pptxgenjs-plus-jsx` — exit 0 on linux-64; the test phase loads the
  three exports.
- `pixi run -e local-recipes validate recipes/pptxgenjs-plus-jsx` and
  `pixi run -e local-recipes lint-optimize recipes/pptxgenjs-plus-jsx` — no errors, and the same on
  `recipes/pptxgenjs-plus`.
- `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint --conda-forge recipes/pptxgenjs-plus-jsx` — no
  lint (G65).
- The story's CFE-surface commits: exactly one, subject `retro(cfe):`, carrying `CHANGELOG.md`.
- `pixi run -e pyforge-guild spec-surface-check` — exit 0 after the scoped stamps.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate); the operator reviews the branch before
  landing it as `Merge pyforge-mason/21-5-pptxgenjs-plus-jsx-builds-green-beside-its-pptxgenjs-plus-sibling into main`.
