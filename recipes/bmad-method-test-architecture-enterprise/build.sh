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

# Node CLIs (upstream package.json "bin"). 1.20.0 first shipped a working
# tea-test-review; 1.25.0 added tea-fragment-selection-runner + tea-trace-runner;
# 1.27.2 added seven more (atdd-red-check, atdd-runner, ci-runner, nfr-runner,
# routing-runner, test-design-runner, transcript-runner).
# Vendor cli/ + production node_modules next to it so require() resolves.
npm install --omit=dev --ignore-scripts --no-audit --no-fund
cp -r cli "${SHARE}/"
cp -r node_modules "${SHARE}/"
# cli/lib/review-provenance.js (new in 1.25.0) does require('../../package.json')
# to stamp teaCliVersion, so the manifest must sit at the share/ root beside cli/.
cp package.json "${SHARE}/"
# node_modules/.bin holds symlinks that fail the noarch portability check.
find "${SHARE}/node_modules" -type d -name .bin -exec rm -rf {} +

mkdir -p "${PREFIX}/bin"
cp "${RECIPE_DIR}/bmad_tea_install.py" "${PREFIX}/bin/bmad-tea-install"
chmod +x "${PREFIX}/bin/bmad-tea-install"

# One dirname-relative sh wrapper per upstream bin entry. Keep this list in
# lockstep with package.json "bin" on every version bump (CFE G110).
write_wrapper() {
    local bin_name="$1" target="$2"
    cat > "${PREFIX}/bin/${bin_name}" <<EOF
#!/usr/bin/env bash
HERE="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
exec node "\${HERE}/../share/bmad-method-test-architecture-enterprise/cli/${target}" "\$@"
EOF
    chmod +x "${PREFIX}/bin/${bin_name}"
}

write_wrapper tea-test-review test-review.js
write_wrapper tea-fragment-selection-runner fragment-selection-runner.js
write_wrapper tea-trace-runner trace-runner.js
write_wrapper tea-atdd-red-check atdd-red-check.js
write_wrapper tea-atdd-runner atdd-runner.js
write_wrapper tea-ci-runner ci-runner.js
write_wrapper tea-nfr-runner nfr-runner.js
write_wrapper tea-routing-runner routing-runner.js
write_wrapper tea-test-design-runner test-design-runner.js
write_wrapper tea-transcript-runner transcript-runner.js


# Windows entry points, emitted from this SAME noarch build (CFE G116). A .bat is
# just text, so ONE artifact serves every platform -- no __unix/__win split and no
# second build. %~dp0 resolves at RUNTIME to <prefix>\Scripts\, so nothing bakes a
# build-time prefix (the old build.bat baked %PREFIX%, which cannot be right for a
# noarch artifact built on another platform).
mkdir -p "${PREFIX}/Scripts"
cp "${RECIPE_DIR}/bmad_tea_install.py" "${PREFIX}/Scripts/bmad-tea-install-script.py"
printf '@"%%~dp0..\\python.exe" "%%~dp0bmad-tea-install-script.py" %%*\r\n' \
    > "${PREFIX}/Scripts/bmad-tea-install.bat"

# One .bat per upstream bin entry -- keep in lockstep with package.json "bin"
# on every version bump (CFE G110), exactly like write_wrapper above.
write_bat_shim() {
    local bin_name="$1" target="$2"
    printf '@node "%%~dp0..\\share\\bmad-method-test-architecture-enterprise\\cli\\%s" %%*\r\n' \
        "${target}" > "${PREFIX}/Scripts/${bin_name}.bat"
}

write_bat_shim tea-test-review test-review.js
write_bat_shim tea-fragment-selection-runner fragment-selection-runner.js
write_bat_shim tea-trace-runner trace-runner.js
write_bat_shim tea-atdd-red-check atdd-red-check.js
write_bat_shim tea-atdd-runner atdd-runner.js
write_bat_shim tea-ci-runner ci-runner.js
write_bat_shim tea-nfr-runner nfr-runner.js
write_bat_shim tea-routing-runner routing-runner.js
write_bat_shim tea-test-design-runner test-design-runner.js
write_bat_shim tea-transcript-runner transcript-runner.js

