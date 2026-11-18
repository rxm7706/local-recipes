---
sources:
  - .github/workflows/test-all.yml
  - .github/workflows/test-linux.yml
  - .github/workflows/test-macos.yml
  - .github/workflows/test-windows.yml
  - .github/workflows/sync-pypi-mappings.yml
  - .github/workflows/platform-deploy.yml
verified: 2026-11-17
---

# GitHub Actions recipe CI

Task-oriented guide for on-demand recipe CI workflows. These workflows run **on-demand only** to preserve GitHub Actions quota — no automatic triggers on push/PR for recipe platform builds.

## Repo workflow inventory

The full inventory — every workflow file under `.github/workflows/`, its triggers, path filters, pause switches and jobs — is the generated [GitHub workflows](../reference/github-workflows.md) reference. To pause or resume an automatic workflow, see [Pause CI](pause-ci.md). This page covers the workflows you start by hand.

### On-demand / manual workflows

Manual recipe CI to preserve quota — dispatch with `gh workflow run`:

| Workflow | Command | Description |
|----------|---------|-------------|
| Test All | `gh workflow run test-all.yml -f recipes="NAME"` | All platforms (calls `test-{linux,macos,windows}.yml`) |
| Test Linux | `gh workflow run test-linux.yml -f recipes="NAME"` | Linux builds in Docker |
| Test macOS | `gh workflow run test-macos.yml -f recipes="NAME"` | Native macOS builds |
| Test Windows | `gh workflow run test-windows.yml -f recipes="NAME"` | Native Windows builds |
| Sync PyPI mappings | `gh workflow run sync-pypi-mappings.yml` | Refresh conda-forge-expert PyPI mappings |
| Platform deploy | `gh workflow run platform-deploy.yml -f ci_run_id=ID -f platform_digest=SHA -f sidecar_digest=SHA -f mcp_host_digest=SHA` | Deploy platform from a CI promotion artifact. All four inputs are required. |

`test-{linux,macos,windows}.yml` are also reusable `workflow_call` targets: `test-all.yml` calls them, and each can be dispatched alone.

The staged-recipes linter workflow family was **retired 2026-10-14** (Story 99.7); recipe hygiene
is enforced by `detectors-ci`, station tests, and `pixi run -e pyforge-steward pyforge steward provision --verify`
for `environment.yaml` sync.

## Recipe CI workflows (developer guide detail)

| Workflow | File | Description |
|----------|------|-------------|
| **Test All** | `test-all.yml` | Orchestrates builds on all platforms |
| **Test Linux** | `test-linux.yml` | Linux builds with Docker: linux-64, linux-aarch64 under QEMU, and a CUDA job |
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
gh workflow run test-linux.yml -f recipes="pytorch" -f cuda_version="12.6"

# Test macOS with custom deployment target
gh workflow run test-macos.yml -f recipes="scipy" -f osx_arm64_deployment_target="12.0"

# Test Windows with Python 3.11
gh workflow run test-windows.yml -f recipes="requests" -f python_version="3.11"

# Test all recipes (first 50) on Linux
gh workflow run test-linux.yml -f recipes="all" -f architecture="linux-64"
```

`recipes="all"` is capped: `test-all.yml` takes the first 20 recipe directories, and a platform workflow dispatched alone takes the first 50.

## Operating notes

- **Skip keywords.** `test-all.yml` builds nothing when the head commit message contains `[skip ci]` or `[ci skip]`. `test-linux.yml` also honours `[skip linux]`, and `test-windows.yml` honours `[skip windows]`.
- **Artifacts.** A build job uploads its packages as a workflow artifact named for the platform and the recipe, for example `linux-64-pandas`.
- **Publishing is opt-in.** The three platform workflows take an `upload_channel` input. Left empty, a run publishes only the workflow artifact. Set, it uploads to that anaconda.org channel and needs the `ANACONDA_API_TOKEN` repository secret. `test-all.yml` has no such input.
- **`sync-pypi-mappings.yml` is manual only.** Its weekly schedule and push trigger were removed after 32 consecutive failures, caused by a stale pixi pin in `.github/actions/sync-pypi-mappings/action.yml`. The workflow's header says the schedule stays off until one manual dispatch comes back green.
- **Where the Linux build layout comes from.** The repository started from the layout of conda-forge's staged-recipes repository. The Linux jobs still use it: they run `.scripts/run_docker_build.sh`, or mount the checkout at the container's staged-recipes directory. No workflow inherited from upstream remains. The retired ones are recorded with `state: retired` in `docs/governance/ci-surfaces.yaml`.

## CI/CD usage tips

1. **On-demand only** — Recipe platform workflows don't run automatically
2. **Specify recipes** — Don't use "all" in production
3. **Monitor quotas** — Check GitHub Actions usage
4. **Cache artifacts** — Download and reuse build artifacts
