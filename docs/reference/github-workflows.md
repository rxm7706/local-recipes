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

Four workflows landed after the original audit and this table never caught up:

| workflow | trigger | what it does |
|---|---|---|
| **`detectors.yml`** | `pull_request`, `push` to main, dispatch | Runs the `detectors-ci` scope=repo subset of the doctor-sources detector suite. Added 2026-07-31 specifically because it *hadn't* existed: this repo had 9 detectors, 7 pixi tasks, 3 dashboard rows, and zero automatic invocation — every green was hand-run by whoever remembered, and PR #170 merged green while breaking `spec_surface_check` because nothing else ran it. |
| **`herald-live-demo.yml`** | `push` to main, `pull_request` (closed), weekly cron (Mon 07:00 UTC), dispatch | Story 13.6: bounded, CI-contained proof that Herald's webhook + scheduler run as real processes, not just unit-tested in isolation — each job uses a throwaway job-local `.herald/herald.db`, never persisted or reused. Not a persistent deployment. |
| **`kedro-viz-publish.yml`** | `push` to main (path-filtered to `pyforge-atlas`'s pipelines), dispatch | Epic 12/FR-62: builds and publishes the real pyforge-atlas Kedro DAG's static kedro-viz export via `steward deploy dashboard`, reusing Steward's own reconciled-push logic rather than a bespoke commit step or the dormant third-party `publish-kedro-viz` Action. |
| **`platform-ci.yml`** | `pull_request`/`push`, path-filtered to `src/platform/**` + the shared packages/pixi files it builds from | Story 10.1: CI for the separately-built Django platform host (`src/platform/`) — ruff/mypy/pytest + a two-engine container build matrix, cost-isolated from the conda-forge factory's own detector/linter CI via the path filter. |

---

## The three provenance groups

| group | when | which |
|---|---|---|
| **Inherited at fork** | 2025-04-13 (`first commit`) | `automate-review-labels`, `correct_directory`, `create_feedstocks`, `do_not_edit_example`, `tokens.yml.notused` — **all five deleted 2026-07-26**, see below |
| **Synced from upstream** | 2026-05-07 (`Add cocoindex (#18)`) | `staged-recipes-linter`, `linter_issue_comment` |
| **Authored here** | 2025-12-24 → 2026-07-18 | `test-{all,linux,macos,windows}`, `sync-pypi-mappings`, `dashboard` |

---

## Active workflows

*(This section predates the 2026-08-15 refresh and does not yet list the 4 workflows
in "Added since the 2026-07-26 audit" above — treat that section as the current
addendum rather than re-deriving these tables to merge them in.)*

### Runs automatically

| workflow | trigger | what it does | why you care |
|---|---|---|---|
| **`staged-recipes-linter.yml`** | `pull_request` (opened, synchronize, reopened, labeled, unlabeled) | Runs `.github/workflows/scripts/linter.py` | **The PR gate.** See *The two always-on gates* below. |
| **`dashboard.yml`** | `push` to main, `schedule`, dispatch | Regenerates `data.js` from git history + live detectors, deploys to Pages | Publishes <https://rxm7706.github.io/local-recipes/>. Uses the lean `pyforge-ci` env with `--locked`. |
| **`linter_issue_comment.yml`** | `issue_comment` — **only** when the body contains `please rerun linter` or `/rerun-linter` | Re-requests the linter check suite | Re-lint without pushing. Rarely needed: toggling any label re-triggers the linter too. |

### Explicit-run only (`workflow_dispatch`)

| workflow | how to run it | what it's for |
|---|---|---|
| **`test-all.yml`** | Actions tab → Run workflow | Fans out to the three platform workflows via `workflow_call`. Use before a risky recipe submission. |
| **`test-linux.yml`** / **`test-macos.yml`** / **`test-windows.yml`** | dispatch, or called by `test-all` | Per-platform recipe build matrix. `test-linux` also does aarch64 via `docker/setup-qemu-action`. |
| **`sync-pypi-mappings.yml`** | dispatch (`create_pr`, `output_dir` inputs) | Refreshes the PyPI↔conda name mappings the `conda-forge-expert` skill reads; opens a PR with the diff. **Schedule is off until one dispatch proves green** — see below. |

---

## The two always-on gates (`.github/workflows/scripts/linter.py`)

CLAUDE.md's PR rules are not convention — they are these code paths; see CLAUDE.md
§ *Critical Rule — PR CI gates* for the actionable commands.

1. **Check #1** — *"Do not edit files outside of the `recipes/` directory."* Maps to
   CLAUDE.md rule 1 (the `maintenance` label).
2. **Check #3** — verifies `environment.yaml` matches a fresh regeneration. Maps to
   CLAUDE.md rule 2. The `maintenance` label does NOT suppress this one.

Check #2 validates recipe placement (`recipes/<name>/<recipe>.yaml`, not
`recipes/<name>.yaml`).

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

**The result is that `.github/workflows/` now matches upstream's shape** —
`staged-recipes-linter` + `linter_issue_comment` + `scripts/` — plus the four
workflows authored here.

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

## Upstream divergence (deliberate)

Our two synced workflows are trimmed on purpose. Upstream additionally has:

- **`merge_group` support** — `bump_webservices_linter.py` + a
  `matrix-org/pr-details-action` step, for conda-forge's merge queue. Not applicable.
- Upstream pins `actions/checkout` at v6.0.2; we run v7.0.1.

We additionally have `pixi>=0.76.2` in the linter's micromamba `create-args`.
**Write it with no space** — `create-args` is a YAML folded scalar, so `pixi >=0.76.2`
splits into two arguments and micromamba errors `Empty package name`.

---

## Where the pixi floor lives (keep all in step)

`requires-pixi = ">=0.76.2"` in `pixi.toml` is the source of truth. It is restated in:

1. `pixi.toml` `[feature.python]`
2. `pixi.toml` `[feature.local-recipes]`
3. `pixi.toml` (third feature block)
4. `environment.yaml`
5. `.github/workflows/staged-recipes-linter.yml` → `create-args: pixi>=0.76.2`
6. `.github/workflows/dashboard.yml` → `pixi-version: v0.76.2`
7. **`.github/actions/sync-pypi-mappings/action.yml` → `pixi-version: v0.76.2`**

№7 was missed when the others were unified. Pinned at v0.59.0, it could not parse the
manifest (`expected a string, found table`) and failed **32/32 runs**. Raised
2026-07-26 together with `setup-pixi@v0.9.3 → v0.10.0`; the weekly cron stays off
until one manual dispatch is observed green.

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

Before this audit `dashboard.yml` held every stale action in the repo
(checkout@v4, setup-python@v5, configure-pages@v5, upload-pages-artifact@v3,
deploy-pages@v4) — which is precisely the set GitHub's Node-20 deprecation warning
named on each deploy.
