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

# No code signing in conda builds. Tauri only signs when an identity is
# configured in tauri.conf.json (none is), so nothing extra to disable here.

echo "=== Installing JS workspace dependencies ==="
pnpm install --frozen-lockfile --strict-peer-dependencies=false

echo "=== Generating Rust third-party license inventory ==="
pushd src-tauri
cargo-bundle-licenses --format yaml --output ../THIRDPARTY-RUST.yml
popd

echo "=== Generating npm third-party license disclaimer ==="
pnpm licenses list --prod --long > THIRDPARTY-NPM.txt

[[ -f LICENSE ]]
[[ -f THIRDPARTY-RUST.yml ]]
[[ -f THIRDPARTY-NPM.txt ]]

echo "=== Building Tauri app bundle (.app only, no .dmg, no updater) ==="
# `pnpm tauri build` runs the configured beforeBuildCommand
# (pnpm build && pnpm bundle-mcp), then compiles the Rust crate and
# packages the .app. `--bundles app` skips .dmg and updater artifacts
# we do not need for a conda install.
pnpm tauri build --bundles app

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
