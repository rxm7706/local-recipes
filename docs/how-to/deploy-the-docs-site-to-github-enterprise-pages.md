# Deploy the docs site to GitHub Enterprise Pages

Use this procedure on the **enterprise copy** of this repository (`ghe.example` in the examples below) so the same unified Pages artifact Story 27.2 builds also publishes to an internal GitHub Enterprise Pages host. Story 31.1 makes the build take the deploying host's site URL and base path from `actions/configure-pages` when `pyforge.herald.pages_second_host` is ON; this page documents only the enterprise-side steps — it does not add a second workflow, artifact, or deploy caller.

## Prerequisites

- An enterprise GitHub host (for example `https://ghe.example`) with a mirror or fork of `rxm7706/local-recipes` that you keep current with `main` on the public upstream.
- GitHub Actions enabled for that repository, with a runner that can execute `dashboard.yml` (Ubuntu, `pixi`, and network access to your internal conda channel — not the public internet).
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

Repeat the fetch, merge, and push whenever you want the internal site to pick up upstream doc changes. The enterprise repo runs the same `.github/workflows/dashboard.yml` as upstream; it must contain the Story 31.1 flag and `export_pages_host_env.py` wiring.

## 2. Enable GitHub Enterprise Pages with GitHub Actions as the source

In the enterprise repository on `ghe.example`:

1. Open **Settings → Pages**.
2. Under **Build and deployment**, set **Source** to **GitHub Actions** (not "Deploy from a branch").
3. Save. No custom workflow file is required — `dashboard.yml` is already the sole `actions/deploy-pages` caller.

## 3. Point CI runners at the internal conda mirror

The `build` job in `.github/workflows/dashboard.yml` runs `pixi run --frozen -e site pages-check`, which resolves packages from the channels configured for this repo. On enterprise runners that cannot reach `conda.anaconda.org` or the public internet, configure the mirror and channel URLs using [`air-gapped-mirror-setup.md`](air-gapped-mirror-setup.md) before the first Pages build.

Typical enterprise patterns (choose what your platform supports):

- Pre-configure `~/.condarc` / `/etc/conda/.condarc` on the runner image to list only internal mirror URLs.
- Set runner environment variables or org-level secrets your mirror setup documents, so `setup-pixi` and `mamba`/`conda` never need outbound access to the public internet.

Confirm a dry run succeeds on a runner:

```bash
pixi run --frozen -e site pages-check
```

## 4. Turn `pyforge.herald.pages_second_host` on for the enterprise copy

On the **enterprise** repository only (leave the public upstream copy at `defaultVariant: "off"`), edit `src/platform/config/flags.json` so the flag resolves to **on**:

```json
"pyforge.herald.pages_second_host": {
  "state": "ENABLED",
  "variants": { "on": true, "off": false },
  "defaultVariant": "on",
  ...
}
```

Commit and push that change to `main` on `ghe.example`. The `Resolve Pages host env` step in `dashboard.yml` runs:

```bash
pixi run --frozen -e pyforge-guild python docsite/tools/export_pages_host_env.py >> "$GITHUB_ENV"
```

with `PAGES_HOST_BASE_URL` and `PAGES_HOST_BASE_PATH` from `actions/configure-pages`. When the flag is on, those values flow into `SITE_URL` for `pages-check` and the Astro build.

To test the same resolution locally before pushing:

```bash
export PAGES_HOST_BASE_URL="https://pages.ghe.example"
export PAGES_HOST_BASE_PATH="/org/local-recipes"
pixi run --frozen -e pyforge-guild python docsite/tools/export_pages_host_env.py
pixi run --frozen -e site pages-check
```

## 5. Deploy

Push to `main` on the enterprise repository (or run **Actions → Dashboard (GitHub Pages) → Run workflow**). The `build` job uploads `docs-site/build/site`; the `deploy` job publishes to the `github-pages` environment.

## 6. Verify the deployed site makes no request to another origin

**Automated check (same as CI):** with the enterprise `configure-pages` outputs and the flag on, `pages-check` must exit 0:

```bash
pixi run --frozen -e site pages-check
```

`pages-check` fails if any script, stylesheet, font, image, `fetch(`, or XHR in the artifact names an origin other than the configured site.

**Browser check on an air-gapped workstation:** open the internal Pages URL from a browser that has **no route to the public internet** (no split tunnel, no corporate proxy to github.io). Open developer tools → **Network**, reload the docs home page and one nested route (for example a herald dossier page under `/herald/`). Confirm every request stays on the `ghe.example` host (or your internal mirror hostnames documented in [`air-gapped-mirror-setup.md`](air-gapped-mirror-setup.md)). There must be no failed requests to `github.io`, `github.com`, or other external origins for assets required to render the page. Plain navigation links to external sites are allowed; cross-origin **loads** are not.

When both checks pass, the enterprise copy is serving a fully static site for its own host, matching Story 31.1's contract.
