# GitHub Actions recipe CI

Task-oriented guide for on-demand recipe CI workflows. These workflows run **on-demand only** to preserve GitHub Actions quota — no automatic triggers on push/PR for recipe platform builds.

## Repo workflow inventory (README summary)

The repo ships **19** workflow files under `.github/workflows/`. They fall into automatic PR gates, push/schedule maintenance, and on-demand recipe builds — verified against each file's `on:` block.

### Automatic PR gates

These run on `pull_request` events (several also re-run on push to `main`):

| Workflow | Triggers | Role |
|----------|----------|------|
| `detectors.yml` | `pull_request`, push to `main` | Repo health detectors (`detectors-ci` subset) |
| `staged-recipes-linter.yml` | `pull_request` | Recipe lint (staged-recipes parity) |
| `coverage-gates.yml` | `pull_request`, push to `main` | PyForge station coverage gates |
| `pyforge-station-tests.yml` | `pull_request`, push to `main` (path-filtered) | PyForge station test matrix |
| `platform-ci.yml` | `pull_request`, push to `main` (path-filtered) | Django platform CI |
| `pyforge-pip-install.yml` | `pull_request` (path-filtered) | Pip-install smoke for PyForge packages |
| `cfe-regression-net.yml` | `pull_request`, push to `main` (path-filtered) | CFE network regression tests |

`test-{linux,macos,windows}.yml` are reusable `workflow_call` targets invoked by `test-all.yml`, not standalone entry points.

### Push / schedule / other automatic triggers

| Workflow | Triggers | Role |
|----------|----------|------|
| `dashboard.yml` | push to `main`, `workflow_dispatch` | Fleet dashboard Pages deploy |
| `kedro-viz-publish.yml` | push to `main` (path-filtered), `workflow_dispatch` | Kedro viz publish |
| `herald-live-demo.yml` | push to `main`, PR closed on `main`, weekly schedule | Herald live demo |
| `linter_issue_comment.yml` | `issue_comment` | Re-runs linter on maintainer comment |

### On-demand / manual workflows

Manual recipe CI to preserve quota — dispatch with `gh workflow run`:

| Workflow | Command | Description |
|----------|---------|-------------|
| Test All | `gh workflow run test-all.yml -f recipes="NAME"` | All platforms (dispatches `test-{linux,macos,windows}.yml`) |
| Test Windows | `gh workflow run test-windows.yml -f recipes="NAME"` | Native Windows builds |
| Sync PyPI mappings | `gh workflow run sync-pypi-mappings.yml` | Refresh conda-forge-expert PyPI mappings |
| Platform deploy | `gh workflow run platform-deploy.yml` | Deploy platform from a CI promotion artifact |
| Linter self-test | `gh workflow run reusable-staged-recipes-linter-selftest.yml` | Self-test for the reusable linter workflow |

## Recipe CI workflows (developer guide detail)

| Workflow | File | Description |
|----------|------|-------------|
| **Test All** | `test-all.yml` | Orchestrates builds on all platforms |
| **Test Linux** | `test-linux.yml` | Linux builds with Docker |
| **Test Windows** | `test-windows.yml` | Native Windows builds |
| **Test macOS** | `test-macos.yml` | Native macOS builds (x86_64 + ARM64) |

### Running workflows

#### Via GitHub UI

1. Navigate to **Actions** tab
2. Select the workflow (e.g., "Test All Platforms")
3. Click **"Run workflow"** button
4. Configure options and click **"Run workflow"**

#### Via GitHub CLI

```bash
# Test all platforms with specific recipes
gh workflow run test-all.yml -f recipes="pandas,numpy" -f platforms="all"

# Test Linux only with CUDA
gh workflow run test-linux.yml -f recipes="pytorch" -f cuda_version="12.9"

# Test macOS with custom deployment target
gh workflow run test-macos.yml -f recipes="scipy" -f osx_arm64_deployment_target="12.0"

# Test Windows with Python 3.11
gh workflow run test-windows.yml -f recipes="requests" -f python_version="3.11"

# Test all recipes (first 20) on Linux
gh workflow run test-linux.yml -f recipes="all" -f architecture="linux-64"
```

## CI/CD usage tips

1. **On-demand only** — Recipe platform workflows don't run automatically
2. **Specify recipes** — Don't use "all" in production
3. **Monitor quotas** — Check GitHub Actions usage
4. **Cache artifacts** — Download and reuse build artifacts

For the full workflow inventory (including stale flags), see [`docs/reference/github-workflows.md`](../reference/github-workflows.md).
