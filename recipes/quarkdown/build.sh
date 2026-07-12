#!/usr/bin/env bash
set -euxo pipefail

# The zip may extract with or without its single `quarkdown/` root dir
# depending on the extractor's strip behavior; the vendored LICENSE source
# sits alongside either way.
if [ -d "quarkdown/bin" ]; then
    APP_ROOT="quarkdown"
elif [ -d "bin" ] && [ -d "lib" ]; then
    APP_ROOT="."
else
    echo "ERROR: quarkdown app image not found in SRC_DIR: $(pwd)" >&2
    ls -la
    exit 1
fi

OPT="${PREFIX}/opt/quarkdown"
mkdir -p "${OPT}"
cp -r "${APP_ROOT}/bin" "${APP_ROOT}/lib" "${APP_ROOT}/runtime" "${OPT}/"
[ -d "${APP_ROOT}/docs" ] && cp -r "${APP_ROOT}/docs" "${OPT}/"
chmod +x "${OPT}/bin/quarkdown" "${OPT}/runtime/bin/"* 2>/dev/null || chmod +x "${OPT}/bin/quarkdown"

mkdir -p "${PREFIX}/bin"
cat > "${PREFIX}/bin/quarkdown" << 'WRAPPER'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/../opt/quarkdown/bin/quarkdown" "$@"
WRAPPER
chmod +x "${PREFIX}/bin/quarkdown"
