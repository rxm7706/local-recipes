#!/bin/bash
set -ex

# CycloneDX BOM Studio is a Vue 3 + Vite browser SPA. Build the static site,
# then stage it under $PREFIX/share and drop a small launcher in $PREFIX/bin
# that serves the bundled assets locally.

# Relative asset base so the built site works regardless of the path it is
# served from (vite.config.ts reads base from BASE_URL).
export BASE_URL=./

# Reproducible install from the committed lockfile.
npm ci

# Build only with Vite; skip the upstream `vue-tsc -b` type-check step
# (dev-time only — it does not affect the produced dist/ and can break on a
# main-HEAD checkout if the pinned TS toolchain is stricter than upstream CI).
npx vite build

# Stage the built static site.
SHARE="${PREFIX}/share/cyclonedx-bom-studio"
mkdir -p "${SHARE}"
cp -r dist/. "${SHARE}/"

# Local launcher: serve the bundled SPA over a plain static HTTP server.
mkdir -p "${PREFIX}/bin"
cat > "${PREFIX}/bin/cyclonedx-bom-studio" <<'LAUNCHER'
#!/bin/bash
# Serve the bundled CycloneDX BOM Studio SPA on a local port (default 8173).
# Usage: cyclonedx-bom-studio [PORT]
PORT="${1:-8173}"
PREFIX="${CONDA_PREFIX:-$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)}"
DIR="${PREFIX}/share/cyclonedx-bom-studio"
echo "CycloneDX BOM Studio  ->  http://localhost:${PORT}/"
echo "(serving static assets from ${DIR}; Ctrl-C to stop)"
exec python -m http.server "${PORT}" --directory "${DIR}"
LAUNCHER
chmod +x "${PREFIX}/bin/cyclonedx-bom-studio"
