## What changed

<!-- One or two sentences. For a story, name its key (`pyforge-<station>/<E>-<S>`). -->

## Recipe change (`recipes/`)

- [ ] The license file is packaged.
- [ ] The source is an official release tarball (`url` with `sha256`), not a repository checkout.
- [ ] The recipe built locally and the build was green.

## Anything outside `recipes/`

- [ ] The PR carries the `maintenance` label.
- [ ] `PYFORGE_PREFLIGHT_SCOPE=full pixi run -e pyforge-guild pr-preflight` exited 0 locally.
- [ ] If `pixi.toml` changed, `environment.yaml` is regenerated in this PR
      (`pixi run -e pyforge-steward pyforge steward estate reconcile`).
