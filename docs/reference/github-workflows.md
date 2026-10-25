# GitHub workflows — inventory, provenance and operating guide

**Originally audited 2026-07-26; refreshed 2026-08-15** (found stale during a repo-wide
docs/ audit — 4 workflows this doc still listed as "deleted 2026-07-26" and 4 real
ones it never mentioned). This repo is a fork of `conda-forge/staged-recipes` that was
renamed to `local-recipes`. That single fact explains most of the surprises below:
inherited workflows hardcode the *upstream* repo name, are gated to the *upstream*
org, or duplicate checks upstream has since folded into its unified linter.

Regenerate this table by reading `.github/workflows/` — do not trust it blind after
a big change. Provenance comes from `git log --diff-filter=A -- <file>`.

## Added since the 2026-07-26 audit

Workflows landed after the original audit and this table never caught up (one, `herald-live-demo.yml`, has since been archived):

| workflow | trigger | what it does |
|---|---|---|
| **`detectors.yml`** | `pull_request`, `push` to main, dispatch | Runs the `detectors-ci` scope=repo subset of the doctor-sources detector suite. Added 2026-07-31 specifically because it *hadn't* existed: this repo had 9 detectors, 7 pixi tasks, 3 dashboard rows, and zero automatic invocation — every green was hand-run by whoever remembered, and PR #170 merged green while breaking `spec_surface_check` because nothing else ran it. |
| **`kedro-viz-publish.yml`** | `push` to main (path-filtered to `pyforge-atlas`'s pipelines), dispatch | Epic 12/FR-62, atlas Story 30.1: builds the real pyforge-atlas Kedro DAG's static kedro-viz export and uploads it as the workflow artifact `kedro-viz-export`; it never commits to git (atlas 30.1 removed its old commit-to-`main` step; steward Story 102.3 then retired the `deploy dashboard` verb that step called). The Pages build downloads the newest unexpired artifact into `docs/dashboard/kedro-viz/` and mounts it (steward Story 102.4); with none, the mount is skipped. |
| **`platform-ci.yml`** | `pull_request`/`push`, path-filtered to `src/platform/**` + the shared packages/pixi files it builds from | Story 10.1: CI for the separately-built Django platform host (`src/platform/`) — ruff/mypy/pytest + a two-engine container build matrix, cost-isolated from the conda-forge factory's own detector/linter CI via the path filter. |

**2026-10-11 (Story 36.1):** Story 13.6's retired CI live-demo workflow moved to `archive/.github/workflows/herald-live-demo.yml` (byte-identical `git mv`; GitHub no longer loads it). Live webhook proof superseded by Story 19.2's [`docs/how-to/run-herald-live-backend-locally.md`](../how-to/run-herald-live-backend-locally.md).

---

## The three provenance groups

| group | when | which |
|---|---|---|
| **Inherited at fork** | 2025-04-13 (`first commit`) | `automate-review-labels`, `correct_directory`, `create_feedstocks`, `do_not_edit_example`, `tokens.yml.notused` — **all five deleted 2026-07-26**, see below |
| **Synced from upstream** | 2026-05-07 (`Add cocoindex (#18)`) | `staged-recipes-linter`, `linter_issue_comment` — **retired 2026-10-14** (Story 99.7; not a staged-recipes fork) |
| **Authored here** | 2025-12-24 → 2026-07-18 | `test-{all,linux,macos,windows}`, `sync-pypi-mappings`, `dashboard` |

---

## Active workflows

*(This section predates the 2026-08-15 refresh and does not yet list the 4 workflows
in "Added since the 2026-07-26 audit" above — treat that section as the current
addendum rather than re-deriving these tables to merge them in.)*

### Runs automatically

| workflow | trigger | what it does | why you care |
|---|---|---|---|
| **`pages.yml`** | `pull_request`/`push` to main (one path filter), six-hourly `schedule`, dispatch | Builds the unified Pages artifact (`docs-site/build/site/`: Starlight shelf at `/`, dossier under `/herald/`, dashboard under `/dashboard/`, the fleet board under `/status/` when herald's flag is on, from the `docs-site/src/content/fleet-status.json` a Guild step writes; one generator, `docs-site/`, since herald Story 43.7) and deploys via the sole `deploy-pages` caller, only on `main` and only when the built tree's hash differs from the live `build.json` | Publishes the public site (`rxm7706.github.io/local-recipes`), or the site of whichever host runs it: `actions/configure-pages` supplies the host's URL and base path, with no flag (Story 102.5). Uses the `site` env with `--frozen`. The `build` job (`contents: read`, `pages: read`, `actions: read`) first downloads atlas's newest `kedro-viz-export` and `vizro-static-export` artifacts from runs on `main` into `docs/dashboard/` (Story 102.4); a dispatch bypasses only the pause switches, so its deploy still needs `main` and a changed tree. After each deploy it attaches the deployed tree as `pages-site.zip` to the rolling `pages-site` pre-release, for an air-gapped host to pull. Steward's file (Stories 102.1–102.5); `steward pages build\|deploy\|status` triggers and reads it. |

### Explicit-run only (`workflow_dispatch`)

| workflow | how to run it | what it's for |
|---|---|---|
| **`test-all.yml`** | Actions tab → Run workflow | Fans out to the three platform workflows via `workflow_call`. Use before a risky recipe submission. |
| **`test-linux.yml`** / **`test-macos.yml`** / **`test-windows.yml`** | dispatch, or called by `test-all` | Per-platform recipe build matrix. `test-linux` also does aarch64 via `docker/setup-qemu-action`. |
| **`sync-pypi-mappings.yml`** | dispatch (`create_pr`, `output_dir` inputs) | Refreshes the PyPI↔conda name mappings the `conda-forge-expert` skill reads; opens a PR with the diff. **Schedule is off until one dispatch proves green** — see below. |

---

## Retired 2026-10-14 — staged-recipes linter family (Story 99.7)

The upstream-synced workflows `staged-recipes-linter.yml`, `linter_issue_comment.yml`,
`reusable-staged-recipes-linter.yml`, `reusable-staged-recipes-linter-selftest.yml`, and
`.github/workflows/scripts/{linter,linter_issue_comment}.py` were removed. This repo is not a
staged-recipes fork; the linter never matched how PyForge lands work.

**Replacements:** merge gate remains `detectors-ci`; non-recipe edits still need the
`maintenance` label; `environment.yaml` sync is `pixi run -e pyforge-steward pyforge steward provision --verify`.
Registry rows: `docs/governance/ci-surfaces.yaml` (`state: retired`). See
[How to pause CI](../how-to/pause-ci.md).

---

## Deleted 2026-07-26 — and why

All five had been **deleted upstream**, some years ago. We carried them because a
fork keeps whatever existed at fork time; nothing re-syncs deletions.

<!-- governance-currency:ignore-start (deleted-workflow table cites now-removed upstream paths, quoted because they were deleted) -->
| file | deleted upstream | upstream's reason | why it was safe here |
|---|---|---|---|
| `correct_directory.yml` | 2024-09-15 | *"feat: unify staged-recipes linting"* | Fully subsumed by `linter.py` check #2. |
| `do_not_edit_example.yml` | 2024-09-15 | same commit | Fully subsumed by `linter.py` check #1 — which also covers `recipes/example-v1/recipe.yaml`, which the standalone bot missed. |
| `create_feedstocks.yml` | 2025-04-18 | moved to `conda-forge/admin-requests` (#29757) | Hard-gated `if: github.repository == 'conda-forge/staged-recipes'` → a permanent no-op here. Its `*/10 * * * *` cron still queued and skipped ~144 runs/day. |
| `automate-review-labels.yml` | 2026-04-14 | plain delete | Labels PRs by `@conda-forge/<team>` pings. No such teams apply to a personal fork; it "succeeded" 100/100 by matching nothing. |
| `tokens.yml.notused` | — | — | Already disabled by filename. |
<!-- governance-currency:ignore-end -->

<!-- governance-currency:ignore-start (orphaned scripts, quoted because they were removed) -->
Also removed as orphans: `scripts/create_feedstocks`, `scripts/create_feedstocks.py`,
`scripts/print_tokens.py`, `scripts/linter_make_comment.py` (referenced by no
workflow, and it hardcoded *both* `{owner}/staged-recipes` and
`conda-forge/staged-recipes`), and `.github/workflows/README.md` (mermaid diagrams
documenting only `automate-review-labels`).
<!-- governance-currency:ignore-end -->

**The result was that `.github/workflows/` matched upstream's linter shape until Story 99.7
retired it** — today the tree is PyForge-authored workflows plus the registry in
`docs/governance/ci-surfaces.yaml`.

---

## The hardcoded-repo trap (fixed 2026-07-26)

`linter_issue_comment.py` did:

```python
repo = gh.get_repo(f"{args.owner}/staged-recipes")   # --owner = github.repository_owner
```

On this fork that resolves to `rxm7706/staged-recipes`, which **does exist** (a
separate fork of upstream) — so `get_repo` succeeds and hides the mistake. It failed
one line later on `get_pull()`, because PR numbers are per-repo. Result: **139 runs,
139 failures, zero successes** over a month.

`linter.py` had already been fixed to take `--repo=${{ github.repository }}`;
`linter_issue_comment.py` was missed. **When syncing anything from upstream, grep the
new code for `staged-recipes` string literals.**

---

## Upstream divergence (deliberate, until 2026-10-14)

History: Story 99.7 retired both synced workflows on 2026-10-14 (see above). Until then they
were trimmed on purpose. Upstream additionally has:

- **`merge_group` support** — `bump_webservices_linter.py` + a
  `matrix-org/pr-details-action` step, for conda-forge's merge queue. Not applicable.
- Upstream pins `actions/checkout` at v6.0.2; we run v7.0.1.

We additionally have `pixi>=0.76.2` in the linter's micromamba `create-args`.
**Write it with no space** — `create-args` is a YAML folded scalar, so `pixi >=0.76.2`
splits into two arguments and micromamba errors `Empty package name`.

---

## Where the pixi floor lives (keep all in step)

`requires-pixi` in `pixi.toml` (`">=0.80.0"` on 2026-10-24) is the floor. Every site that
restates it is listed in `scripts/pixi_version_registry.py`, the one registry: the manifest's
`$schema` URL and feature floors, `pyforge-mason`'s own `pixi.toml`, `environment.yaml`, the
`setup-pixi` pins in the workflows and in `.github/actions/sync-pypi-mappings/action.yml` and
`.github/actions/platform-test-setup/action.yml`, and the Containerfile builder-stage image
tags. Do not hand-edit the sites:

- `pixi run -e pyforge-guild pixi-version-check` fails on any drift (CI-safe).
- `pixi run -e local-recipes bump-pixi-version -- <version>` rewrites every site and
  regenerates `environment.yaml` in one pass.

History: the `sync-pypi-mappings` action pin was missed when the sites were first unified.
Pinned at v0.59.0, it could not parse the manifest (`expected a string, found table`) and
failed **32/32 runs**. It was raised 2026-07-26 together with `setup-pixi@v0.9.3 → v0.10.0`;
the workflow's weekly schedule stays off until one manual dispatch is observed green.

---

## Action versions (audited 2026-07-26)

| action | pinned as | notes |
|---|---|---|
| `actions/checkout` | `@v7` / SHA `3d3c42e5…` (v7.0.1) | SHA-pinned in the two upstream-synced files, tag-pinned elsewhere |
| `actions/setup-python` | `@v7` | |
| `actions/configure-pages` | `@v6` | |
| `actions/upload-pages-artifact` | `@v5` | matched set — bump with the other two Pages actions |
| `actions/deploy-pages` | `@v5` | |
| `actions/upload-artifact` | `@v7` | |
| `mamba-org/setup-micromamba` | SHA `ce51e99f…` (v3.1.0) | |
| `prefix-dev/setup-pixi` | `@v0.10.0` | |
| `conda-incubator/setup-miniconda` | `@v4` | v4 **is** current (v4.0.1) |
| `docker/setup-qemu-action` | `@v4` | v4 **is** current (v4.2.0) |
| `peter-evans/create-pull-request` | `@v8` | |

Before this audit `pages.yml` held every stale action in the repo
(checkout@v4, setup-python@v5, configure-pages@v5, upload-pages-artifact@v3,
deploy-pages@v4) — which is precisely the set GitHub's Node-20 deprecation warning
named on each deploy.
