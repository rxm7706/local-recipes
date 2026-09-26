#!/bin/bash
set -euxo pipefail

# The GitHub tag archive extracts into bmad-eval-quality-<version>/;
# rattler-build sets SRC_DIR to that directory, so package.json is in SRC_DIR.
if [[ ! -f "package.json" ]]; then
    echo "ERROR: package.json not found in SRC_DIR: ${PWD}" >&2
    ls -la
    exit 1
fi

# dist/ is not committed upstream: compile TypeScript (needs devDependencies).
npm ci --no-fund --no-audit --ignore-scripts
npm run build

# Ship production dependencies only (one prod dep: zod).
rm -rf node_modules
npm ci --omit=dev --no-fund --no-audit --ignore-scripts

INSTALL_DIR="${PREFIX}/lib/node_modules/eval-quality"
mkdir -p "${INSTALL_DIR}"

# Mirror package.json "files" (dist, schemas, corpus, README.md, LICENSE)
# plus package.json and the production node_modules.
cp -r dist schemas corpus README.md LICENSE package.json node_modules "${INSTALL_DIR}/"
# No symlinks in a noarch artifact (rattler-build rejects them for Windows).
find "${INSTALL_DIR}" -type d -name .bin -exec rm -rf {} +

# One dirname-relative sh wrapper per upstream bin entry. Keep this list in
# lockstep with package.json "bin" on every version bump (CFE G110):
# 4.2.0 added eval-quality-gates (dist/gates/gates-cli.js) beside eval-quality.
mkdir -p "${PREFIX}/bin"
write_wrapper() {
    local bin_name="$1" target="$2"
    cat > "${PREFIX}/bin/${bin_name}" <<EOF
#!/usr/bin/env bash
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
exec node "\${SCRIPT_DIR}/../lib/node_modules/eval-quality/dist/${target}" "\$@"
EOF
    chmod +x "${PREFIX}/bin/${bin_name}"
}

write_wrapper eval-quality cli/main.js
write_wrapper eval-quality-gates gates/gates-cli.js

# Windows entry points, emitted from this SAME noarch build. The recipe is
# noarch: generic, so it builds once on linux and build.bat never runs on any
# platform -- without this the artifact has no Windows entry point at all.
# One .bat per upstream bin entry -- same list as write_wrapper above.
mkdir -p "${PREFIX}/Scripts"
write_bat_shim() {
    local bin_name="$1" target="$2"
    printf '@echo off\r\nSET "DIR=%%~dp0.."\r\nnode "%%DIR%%\\lib\\node_modules\\eval-quality\\dist\\%s" %%*\r\n' \
        "${target}" > "${PREFIX}/Scripts/${bin_name}.bat"
}

write_bat_shim eval-quality cli\\main.js
write_bat_shim eval-quality-gates gates\\gates-cli.js
