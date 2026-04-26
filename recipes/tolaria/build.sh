#!/bin/bash
set -euxo pipefail

# Tolaria is osx-arm64 only; sanity-check we are on macOS.
[[ "$(uname -s)" == "Darwin" ]]

echo "=== Build environment ==="
node --version
pnpm --version
cargo --version
rustc --version

# Vite + React 19 frontend build needs more heap than the Node default.
export NODE_OPTIONS="--max-old-space-size=6144"

# Confirm the vendored sources from source[1] and source[2] are present.
[[ -d cargo-vendor ]]
[[ -d pnpm-store ]]

echo "=== Wiring cargo to the vendored crate sources ==="
mkdir -p .cargo
cat > .cargo/config.toml << 'EOF'
[source.crates-io]
replace-with = "vendored-sources"

[source.vendored-sources]
directory = "cargo-vendor"
EOF

echo "=== Installing JS workspace dependencies (offline) ==="
# --store-dir + --offline forces pnpm to resolve every package from the
# pre-fetched store unpacked from source[2]; any missing tarball errors out
# instead of silently hitting the npm registry.
pnpm install \
  --offline \
  --frozen-lockfile \
  --strict-peer-dependencies=false \
  --store-dir "$(pwd)/pnpm-store"

echo "=== Generating Rust third-party license inventory ==="
( cd src-tauri && cargo-bundle-licenses --format yaml --output ../THIRDPARTY-RUST.yml )

echo "=== Generating npm third-party license disclaimer ==="
pnpm licenses list --prod --long > THIRDPARTY-NPM.txt

[[ -f LICENSE ]]
[[ -f THIRDPARTY-RUST.yml ]]
[[ -f THIRDPARTY-NPM.txt ]]

echo "=== Building Tauri app bundle (offline; .app only) ==="
# CARGO_NET_OFFLINE=true makes cargo refuse network fetches; combined with
# the .cargo/config.toml above, every crate must come from cargo-vendor/.
# `--bundles app` skips .dmg and updater artifacts we don't need.
CARGO_NET_OFFLINE=true pnpm tauri build --bundles app

APP_SRC="src-tauri/target/release/bundle/macos/Tolaria.app"
[[ -d "${APP_SRC}" ]]

echo "=== Installing .app bundle into PREFIX ==="
mkdir -p "${PREFIX}/lib"
cp -R "${APP_SRC}" "${PREFIX}/lib/Tolaria.app"

echo "=== Creating launcher script ==="
mkdir -p "${PREFIX}/bin"
cat > "${PREFIX}/bin/tolaria" << 'EOF'
#!/bin/bash
# Tolaria launcher: exec the bundled macOS binary with all args forwarded.
exec "$(dirname "$0")/../lib/Tolaria.app/Contents/MacOS/Tolaria" "$@"
EOF
chmod +x "${PREFIX}/bin/tolaria"

echo "=== Build complete ==="
ls -la "${PREFIX}/bin/tolaria"
ls -la "${PREFIX}/lib/Tolaria.app/Contents/MacOS/"
