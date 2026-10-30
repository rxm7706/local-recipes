# Deploy the docs site to GitHub Enterprise Pages

Use this procedure on the **enterprise copy** of this repository (`ghe.example` in the examples below) so the same unified Pages artifact Story 27.2 builds also publishes to an internal GitHub Enterprise Pages host. The build takes the deploying host's site URL and base path from `actions/configure-pages` on every host, with nothing to turn on; this page documents only the enterprise-side steps — it does not add a second workflow, artifact, or deploy caller. A host that cannot build at all pulls the public deploy's bytes instead ([section 6](#6-pull-the-zip-for-a-host-that-cannot-build)). [Section 7](#7-add-the-bmad-marketplace-from-an-internal-mirror) is for a teammate on that host who adds the BMAD marketplace from the mirror rather than deploys it.

## Prerequisites

- An enterprise GitHub host (for example `https://ghe.example`) with a mirror or fork of `rxm7706/local-recipes` that you keep current with `main` on the public upstream.
- GitHub Actions enabled for that repository, with a runner that can execute `pages.yml` (Ubuntu, `pixi`, the GitHub CLI `gh`, and network access to your internal conda channel — not the public internet). `gh` downloads the Kedro-Viz and Vizro export artifacts before the build (steward Story 102.4). A token alone does not tell `gh` which host to talk to, and a runner has no `gh` configuration, so each download step names the host and repository the workflow runs on (`GH_HOST` from `GITHUB_SERVER_URL`, and `GH_REPO`) and hands `gh` the job's token as both `GH_TOKEN` and `GH_ENTERPRISE_TOKEN`; that is what makes it authenticate against your enterprise host. A runner without `gh` fails that step naming the command.
- The internal conda mirror and channel configuration from [`air-gapped-mirror-setup.md`](air-gapped-mirror-setup.md) (follow that guide; do not duplicate its steps here).

## 1. Keep the enterprise repository aligned with `main`

On a machine that can reach both remotes:

```bash
git clone https://ghe.example/org/local-recipes.git
cd local-recipes
git remote add upstream https://github.com/rxm7706/local-recipes.git   # if missing
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

Repeat the fetch, merge, and push whenever you want the internal site to pick up upstream doc changes. The enterprise repo runs the same `.github/workflows/pages.yml` as upstream, unchanged: nothing in it is specific to either host.

## 2. Enable GitHub Enterprise Pages with GitHub Actions as the source

In the enterprise repository on `ghe.example`:

1. Open **Settings → Pages**.
2. Under **Build and deployment**, set **Source** to **GitHub Actions** (not "Deploy from a branch").
3. Save. No custom workflow file is required — `pages.yml` is already the sole `actions/deploy-pages` caller.

`actions/configure-pages` (the `pages` step of the `build` job) supplies this host's site URL and base path, and the workflow hands them to `pages-check` and the Astro build as `PAGES_HOST_BASE_URL` and `PAGES_HOST_BASE_PATH`. There is no flag to flip and no file to edit for the enterprise copy.

## 3. Point CI runners at the internal conda mirror

The `build` job in `.github/workflows/pages.yml` runs `pixi run --frozen -e site pages-check`, which resolves packages from the channels configured for this repo. On enterprise runners that cannot reach `conda.anaconda.org` or the public internet, configure the mirror and channel URLs using [`air-gapped-mirror-setup.md`](air-gapped-mirror-setup.md) before the first Pages build.

Typical enterprise patterns (choose what your platform supports):

- Pre-configure `~/.condarc` / `/etc/conda/.condarc` on the runner image to list only internal mirror URLs.
- Set runner environment variables or org-level secrets your mirror setup documents, so `setup-pixi` and `mamba`/`conda` never need outbound access to the public internet.

Confirm a dry run succeeds on a runner:

```bash
pixi run --frozen -e site pages-check
```

## 4. Deploy

Push to `main` on the enterprise repository (or run **Actions → Pages → Run workflow**). The `build` job uploads `docs-site/build/site`; the `deploy` job publishes to the `github-pages` environment.

## 5. Verify the deployed site makes no request to another origin

**Automated check (same as CI):** with this host's `configure-pages` values in the environment, `pages-check` must exit 0. To run it on a workstation before pushing:

```bash
export PAGES_HOST_BASE_URL="https://pages.ghe.example"
export PAGES_HOST_BASE_PATH="/org/local-recipes"
pixi run --frozen -e site pages-check
```

With both variables set, every link in the built artifact resolves under `https://pages.ghe.example/org/local-recipes/`. An empty base path (`configure-pages` gives `""` for a site served at its host's root, such as a custom domain) builds for that origin alone; with no base URL the build is for the public github.io URL.

`pages-check` fails if any script, stylesheet, font, image, `fetch(`, or XHR in the artifact names an origin other than the configured site.

**Browser check on an air-gapped workstation:** open the internal Pages URL from a browser that has **no route to the public internet** (no split tunnel, no corporate proxy to github.io). Open developer tools → **Network**, reload the docs home page and one nested route (for example a herald dossier page under `/herald/`). Confirm every request stays on the `ghe.example` host (or your internal mirror hostnames documented in [`air-gapped-mirror-setup.md`](air-gapped-mirror-setup.md)). There must be no failed requests to `github.io`, `github.com`, or other external origins for assets required to render the page. Plain navigation links to external sites are allowed; cross-origin **loads** are not.

When both checks pass, the enterprise copy is serving a fully static site for its own host, matching Story 31.1's contract.

## 6. Pull the zip for a host that cannot build

A host whose runners cannot reach a conda mirror can skip sections 1–4 and take the bytes the public site deployed. After every deploy from `main`, the public repository's `pages.yml` attaches the deployed site, `pages-site.zip`, to a rolling pre-release tagged `pages-site` that moves to the deploying commit (steward Story 102.5). The release step runs only while steward's flag `pyforge.steward.pages_duty` reads on in the deploying environment (the public CI resolves the `dev` overlay, where it is on); with it off, no asset is attached. The zip is the deployed tree, with its `build.json` (`tree_hash`, `built_from`, `run_id`, `built_at`) inside. `tree_hash` cannot be recomputed from the zip: it covers the build tree's hidden files too (`.pages-build-site-url`, `herald/.nojekyll`), which GitHub's artifact uploads leave out of both the Pages artifact and the zip. The integrity check is `built_from`, below.

1. On a machine with access to github.com, download it:

   ```bash
   gh release download pages-site --repo rxm7706/local-recipes -p pages-site.zip
   ```

   (or use the asset's link on the repository's **Releases** page).
2. Carry `pages-site.zip` across to the internal network the way your site moves reviewed files.
3. Unzip it and check where it was built from:

   ```bash
   unzip -q pages-site.zip -d pages-site
   python -c "import json; print(json.load(open('pages-site/build.json'))['built_from'])"
   git -C /path/to/the/mirrored/local-recipes merge-base --is-ancestor <built_from> main && echo "on main"
   ```

   The `built_from` commit must be on your mirrored `main`; a zip built from a commit your mirror does not hold is not the reviewed tree.
4. Serve the `pages-site/` tree as static files from any internal web server. This is the recommended path: nothing is rebuilt, so the bytes are the ones the public deploy published.

The zip is built for the public github.io URL, so its absolute internal links carry the `/local-recipes/` base path: serve it at that path (for example `https://docs.internal.example/local-recipes/`). To publish the same tree through the enterprise host's own GitHub Pages instead, `pages.yml` would need an input that takes a prebuilt tree in place of a build; it has none today, so on a host that can run the workflow, sections 1–4 (which rebuild for the host's own URL) are the GitHub Actions path.

## 7. Add the BMAD marketplace from an internal mirror

This monorepo hosts the marketplace at `docs/foundry/marketplace/`; its `README.md` holds the flag semantics (§ Regenerate the site) and the 2026-10-21 decision (§ Provenance). While the flag is on, the Pages build mounts the generated site at `/marketplace/` in the same artifact as the docs shelf; off, `/marketplace/` is absent from the artifact (a 404, not a stale page). This section is what differs on an enterprise host. With a site URL of `https://pages.ghe.example` and a base path of `/org/local-recipes`, the index is:

```text
https://pages.ghe.example/org/local-recipes/marketplace/
```

The same build serves `marketplace.json` at `/marketplace/marketplace.json`. That file is the URL form: a Claude `url` marketplace source downloads only the file, so each plugin entry uses `git-subdir` (`url` and `path`). `git-subdir` is a plugin source, not a marketplace source. On GitHub Actions the build rewrites the plugin `url` from `https://github.com/rxm7706/local-recipes.git` to `https://<this host>/<this repo>.git`.

The form that works against the mirror's git repository, without Pages, is a Claude `git` marketplace source. `path` is the marketplace file inside the repository. `sparsePaths` is the sparse checkout. Both fields are documented for the `git` and `github` marketplace sources (Claude Code marketplace reference, checked 2026-10-21). Do not put `git-subdir` on this object.

```json
{
  "extraKnownMarketplaces": {
    "pyforge-bmad-marketplace": {
      "source": {
        "source": "git",
        "url": "https://ghe.example/org/local-recipes.git",
        "path": "docs/foundry/marketplace/.claude-plugin/marketplace.json",
        "sparsePaths": [
          "docs/foundry/marketplace/.agents",
          "docs/foundry/marketplace/.claude-plugin",
          "docs/foundry/marketplace/site",
          "docs/foundry/marketplace/skills"
        ]
      }
    }
  }
}
```

Replace `ghe.example/org/local-recipes` with the mirror you were told to use. `steward catalog pointers` prints this block once that mirror is an `edit_store.mirrors` entry, and it prints the `github` source (`repo: rxm7706/local-recipes`, the same `path` and `sparsePaths`) for the public repository. The sparse set carries both generated manifests, so the Codex pointer the duty prints (`codex plugin marketplace add <checkout>/docs/foundry/marketplace`) finds `.agents/plugins/marketplace.json` on a sparse checkout too. Paste the block into `.claude/settings.json` yourself. The duty does not edit that file.

The rolling `pages-site` pre-release also carries one `<scope>-<slug>.zip` per skill folder, each with its `<scope>-<slug>.zip.sha256` beside it, when the marketplace flag is on for that deploy; what each holds and how it is checked are the README's § Install, and how the release is pruned and uploaded is its § Regenerate the site. On an enterprise host the cards' repository links point at the mirror's own blob view of the deployed commit (which links the mount rewrites is the README's § Regenerate the site).
