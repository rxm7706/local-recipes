# Packaging — CAP-1 build, test and enrolment detail (HOW; the kernel holds WHAT)

**Recipe** `recipes/bmad-eval-quality/recipe.yaml`, labs-skills / manticore encoding (G109):
`context.version: "0.2.0.dev0"`, `context.commit: 3172162fbdc7c4bb70ed11c1367dc3e433797535`,
source `https://github.com/bmad-code-org/bmad-eval-quality/archive/${{ commit }}.tar.gz`,
sha256 `a8b1ddfbeeacbdd2c40423cb5a3ab6ac2c92f6158756b9564d33cb8ba33fbc3c`. Build class follows
`recipes/bmad-method` (npm CLI): `npm ci` (devDependencies needed — `prepack` runs `tsc -p
tsconfig-build.json`; `typescript 7.0.2`) → `npm pack` (tarball is named from package.json:
`eval-quality-0.2.0.tgz`, not the conda version) → `npm install -g <tarball>` → `pnpm-licenses`.
`files` = dist, schemas, corpus, README.md, LICENSE (Apache-2.0). Requirements: host `nodejs`,
run `nodejs >=22.20.0` (`engines.node`; pixi has 24.19). `noarch: generic` per the assumption in
SPEC.md; `__unix`/`__win` run constraints as in bmad-method.

**Tests (recipe):** `eval-quality --version` → `0.2.0`; `eval-quality --help` lists `score`;
`eval-quality compile <prefix>/…/corpus/dev/contracts/satisfied-declarations.json` exits 0
(locate the corpus under the installed `node_modules/eval-quality/corpus`).

**Enrolment (one line + fan-out):** `recipes/bmad-suite/suite-members.yaml` active member
`bmad-eval-quality`; `pixi run -e local-recipes generate-bmad-suite` regenerates the metapackage
run deps and CalVer; pin `bmad-eval-quality = ">=0.2.0.dev0"` in `pixi.toml`
`[feature.local-recipes.dependencies]` (with `# … # https://github.com/bmad-code-org/bmad-eval-quality`
comment for the generator/doctor registry) → `pixi install` → `pixi project export
conda-environment -e build > environment.yaml`; `tests/packaging/test_bmad_suite_full_feature.py`
`BASELINE_LOCAL_RECIPES_BMAD_PINS` += `bmad-eval-quality`; steward `suite.py` `SuitePackageDef`
(github_repo `bmad-code-org/bmad-eval-quality`, no npm name until v0.2.0 publishes) + pipeline-truth
fixture; `install-matrix.md` row (hazards: unreleased 0.2.0 line, exact pin, npm 0.1.0 lacks
`score`); `install-class-playbook.md` row (class: CLI binary, no wiring); `docs/reference/
library-llms-full.md` row; `llms-full-check` green. Publish: `build-bmad-suite` fills
`build_artifacts/`; `anaconda upload` to SelfExplainML is the operator's step.

**Currency:** commit-pinned → `github_updater.py --head` advances; doctor's suite drift needs a
registry mapping (`github`) to watch it — the commit-pinned members are today's known gap.
