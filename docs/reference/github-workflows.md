# GitHub workflows — inventory, provenance and operating guide

**Audited 2026-07-26.** This repo is a fork of `conda-forge/staged-recipes` that was
renamed to `local-recipes`. That single fact explains most of the surprises below:
inherited workflows hardcode the *upstream* repo name, are gated to the *upstream*
org, or duplicate checks upstream has since folded into its unified linter.

Regenerate this table by reading `.github/workflows/` — do not trust it blind after
a big change. Provenance comes from `git log --diff-filter=A -- <file>`.

---

## The three provenance groups

| group | when | which |
|---|---|---|
| **Inherited at fork** | 2025-04-13 (`first commit`) | `automate-review-labels`, `correct_directory`, `create_feedstocks`, `do_not_edit_example`, `tokens.yml.notused` — **all five deleted 2026-07-26**, see below |
| **Synced from upstream** | 2026-05-07 (`Add cocoindex (#18)`) | `staged-recipes-linter`, `linter_issue_comment` |
| **Authored here** | 2025-12-24 → 2026-07-18 | `test-{all,linux,macos,windows}`, `sync-pypi-mappings`, `dashboard` |

---

## Active workflows

### Runs automatically

| workflow | trigger | what it does | why you care |
|---|---|---|---|
| **`staged-recipes-linter.yml`** | `pull_request` (opened, synchronize, reopened, labeled, unlabeled) | Runs `scripts/linter.py` | **The PR gate.** See *The two always-on gates* below. |
| **`dashboard.yml`** | `push` to main, `schedule`, dispatch | Regenerates `data.js` from git history + live detectors, deploys to Pages | Publishes <https://rxm7706.github.io/local-recipes/>. Uses the lean `pyforge-ci` env with `--locked`. |
| **`linter_issue_comment.yml`** | `issue_comment` — **only** when the body contains `please rerun linter` or `/rerun-linter` | Re-requests the linter check suite | Re-lint without pushing. Rarely needed: toggling any label re-triggers the linter too. |

### Explicit-run only (`workflow_dispatch`)

| workflow | how to run it | what it's for |
|---|---|---|
| **`test-all.yml`** | Actions tab → Run workflow | Fans out to the three platform workflows via `workflow_call`. Use before a risky recipe submission. |
| **`test-linux.yml`** / **`test-macos.yml`** / **`test-windows.yml`** | dispatch, or called by `test-all` | Per-platform recipe build matrix. `test-linux` also does aarch64 via `docker/setup-qemu-action`. |
| **`sync-pypi-mappings.yml`** | dispatch (`create_pr`, `output_dir` inputs) | Refreshes the PyPI↔conda name mappings the `conda-forge-expert` skill reads; opens a PR with the diff. **Schedule is off until one dispatch proves green** — see below. |

---

## The two always-on gates (`scripts/linter.py`)

CLAUDE.md's PR rules are not convention — they are these code paths:

1. **Check #1** — *"Do not edit files outside of the `recipes/` directory."*
   **Suppressed by the `maintenance` label.** Any PR touching docs, `.github/`,
   `pixi.toml`, dashboards, etc. needs:
   `gh pr edit <n> --repo rxm7706/local-recipes --add-label maintenance`
2. **Check #3** — `environment.yaml` must equal
   `pixi project export conda-environment -e build`. **The `maintenance` label does
   NOT suppress this one.** Change `pixi.toml` → regenerate `environment.yaml`.

Check #2 validates recipe placement (`recipes/<name>/<recipe>.yaml`, not
`recipes/<name>.yaml`).

---

## Deleted 2026-07-26 — and why

All five had been **deleted upstream**, some years ago. We carried them because a
fork keeps whatever existed at fork time; nothing re-syncs deletions.

| file | deleted upstream | upstream's reason | why it was safe here |
|---|---|---|---|
| `correct_directory.yml` | 2024-09-15 | *"feat: unify staged-recipes linting"* | Fully subsumed by `linter.py` check #2. |
| `do_not_edit_example.yml` | 2024-09-15 | same commit | Fully subsumed by `linter.py` check #1 — which also covers `recipes/example-v1/recipe.yaml`, which the standalone bot missed. |
| `create_feedstocks.yml` | 2025-04-18 | moved to `conda-forge/admin-requests` (#29757) | Hard-gated `if: github.repository == 'conda-forge/staged-recipes'` → a permanent no-op here. Its `*/10 * * * *` cron still queued and skipped ~144 runs/day. |
| `automate-review-labels.yml` | 2026-04-14 | plain delete | Labels PRs by `@conda-forge/<team>` pings. No such teams apply to a personal fork; it "succeeded" 100/100 by matching nothing. |
| `tokens.yml.notused` | — | — | Already disabled by filename. |

Also removed as orphans: `scripts/create_feedstocks`, `scripts/create_feedstocks.py`,
`scripts/print_tokens.py`, `scripts/linter_make_comment.py` (referenced by no
workflow, and it hardcoded *both* `{owner}/staged-recipes` and
`conda-forge/staged-recipes`), and `.github/workflows/README.md` (mermaid diagrams
documenting only `automate-review-labels`).

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

We additionally have `pixi>=0.73.0` in the linter's micromamba `create-args`.
**Write it with no space** — `create-args` is a YAML folded scalar, so `pixi >=0.73.0`
splits into two arguments and micromamba errors `Empty package name`.

---

## Where the pixi floor lives (keep all in step)

`requires-pixi = ">=0.73.0"` in `pixi.toml` is the source of truth. It is restated in:

1. `pixi.toml` `[feature.python]`
2. `pixi.toml` `[feature.local-recipes]`
3. `pixi.toml` (third feature block)
4. `environment.yaml`
5. `.github/workflows/staged-recipes-linter.yml` → `create-args: pixi>=0.73.0`
6. `.github/workflows/dashboard.yml` → `pixi-version: v0.73.0`
7. **`.github/actions/sync-pypi-mappings/action.yml` → `pixi-version: v0.73.0`**

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
