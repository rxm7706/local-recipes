#!/usr/bin/env bash
set -euxo pipefail

if [ ! -d "src" ]; then
    echo "ERROR: src/ directory not found in SRC_DIR: $(pwd)" >&2
    ls -la
    exit 1
fi

SHARE="${PREFIX}/share/bmad-method-test-architecture-enterprise"
mkdir -p "${SHARE}"
cp -r src/agents "${SHARE}/"
cp -r src/workflows "${SHARE}/"
cp src/module-help.csv src/module.yaml "${SHARE}/"
cp -r .claude-plugin "${SHARE}/"
cp CHANGELOG.md LICENSE README.md "${SHARE}/"

# tea-test-review Node CLI (real bin entry since upstream 1.20.0):
# vendor cli/ + production node_modules next to it so require() resolves.
npm install --omit=dev --ignore-scripts --no-audit --no-fund
cp -r cli "${SHARE}/"
cp -r node_modules "${SHARE}/"
# node_modules/.bin holds symlinks that fail the noarch portability check.
find "${SHARE}/node_modules" -type d -name .bin -exec rm -rf {} +

mkdir -p "${PREFIX}/bin"
cp "${RECIPE_DIR}/bmad_tea_install.py" "${PREFIX}/bin/bmad-tea-install"
chmod +x "${PREFIX}/bin/bmad-tea-install"

cat > "${PREFIX}/bin/tea-test-review" <<'EOF'
#!/usr/bin/env bash
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec node "${HERE}/../share/bmad-method-test-architecture-enterprise/cli/test-review.js" "$@"
EOF
chmod +x "${PREFIX}/bin/tea-test-review"
