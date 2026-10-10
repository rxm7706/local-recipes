## Title

conda-smithy CalVer 2026.x line needs `conda` package for py-rattler / conda co-solve in laptop SBOM

## Body

PyForge's laptop SBOM (`pyforge-foundry-full`) cannot compose the `conda-smithy` pixi feature because resolving conda-smithy's CalVer 2026.x line requires the standalone `conda` package, while the estate also needs a conda-smithy / py-rattler / conda pin set that keeps the SBOM solvable. The `feature:conda-smithy` row in `docs/foundry/sbom-gaps.md` is disposition `upstream` with owner mason.

## Reproduce or evidence

- `docs/foundry/sbom-gaps.md:11` — `feature:conda-smithy` upstream
- `pixi.toml:121-122` — `[feature.conda-smithy.dependencies]` pins `conda-smithy` CalVer 3.x; comment notes 2026.x needs `conda`
- `pixi.toml:1114-1119` — SBOM comment names conda-smithy caps on py-rattler and conda
- `pixi.toml:2642` — py-rattler floor comment (conda solver variant caps py-rattler `<0.26`)

## Local workaround

Keep `conda-smithy` outside `pyforge-foundry-full`; use `pixi exec --spec "conda-smithy>=2026.6.14" conda-smithy recipe-lint` for CI-parity lint (`pixi.toml` conda-smithy lint task). feedrattler and current conda-recipe-manager stay in `grayskull`, not the SBOM.

## What resolution unblocks here

Promote or re-disposition `feature:conda-smithy` in `docs/foundry/sbom-gaps.md` once conda-smithy (feedstock or solver) allows composing the feature into `pyforge-foundry-full` without breaking py-rattler / conda co-solve.
