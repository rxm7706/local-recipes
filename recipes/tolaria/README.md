# tolaria conda-forge recipe

Builds the [Tolaria](https://tolaria.md) Tauri desktop app from source for `osx-arm64`.

## Per-version vendoring workflow

This recipe builds fully offline — `pnpm install --offline` and `cargo build --offline` resolve every dependency from two pre-fetched tarballs supplied as additional `source:` entries. They must be regenerated and re-uploaded for every version bump.

1. Download and extract the upstream source tarball pinned in `recipe.yaml`:
   ```bash
   VERSION=2026.4.25
   curl -L "https://github.com/refactoringhq/tolaria/archive/refs/tags/stable-v${VERSION}.tar.gz" | tar -xz
   cd "tolaria-stable-v${VERSION}"
   ```
2. Run `vendor.sh` from inside that tree (needs `rust`, `node 24`, `pnpm 10`, `tar`):
   ```bash
   bash /path/to/recipes/tolaria/vendor.sh "${VERSION}"
   ```
3. Upload `tolaria-cargo-vendor-${VERSION}.tar.gz` and `tolaria-pnpm-store-${VERSION}.tar.gz` to a stable HTTPS host. The recipe URLs default to `github.com/rxm7706/conda-recipes-vendored/releases/download/tolaria-${VERSION}/`; change `recipe.yaml` if you use a different host.
4. Paste the two SHA256 values printed by `vendor.sh` into `recipe.yaml`'s `source[1].sha256` and `source[2].sha256` fields, replacing the all-zero placeholders.

## Why vendoring

Conda-forge build sandboxes are inconsistent about network access, and Tauri builds pull hundreds of crates and thousands of npm packages on first run. Pre-fetching guarantees a deterministic, reviewable, fully-offline build at the cost of one extra step per version.

## Maintenance notes

- The autotick bot will not regenerate vendor tarballs — version bumps must be done manually until upstream publishes vendored release artifacts of their own.
- If `pnpm-lock.yaml` or `src-tauri/Cargo.lock` changes between alpha and stable releases, the pre-fetched store will be incomplete and `pnpm install --offline` will fail loud — re-run `vendor.sh`.
