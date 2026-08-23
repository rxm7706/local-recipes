# Platform Python dependencies — pixi is the sole authority

The former `base.txt` / `production.txt` / `local.txt` install chains were retired
by steward Story 16.1 (CAP-5 / `spec-platform-fifteen-factors`).

| Need | Use |
|------|-----|
| Platform CI `test` job | `[feature.platform-ci-test]` / env `platform-ci-test` in repo-root `pixi.toml` |
| Local platform host + engines | env `platform-dev` (composes `python-agent-platform` + `platform-dev`) |
| Container image pip layer (`--no-deps` atop the conda env) | `[feature.platform-image-pip]` via `scripts/platform_image_pip_layer.py` |

Do **not** reintroduce `*.txt` requirement files here as an install source.
`pixi run -e local-recipes platform-ci-test-requirements-check` fails if they return.
