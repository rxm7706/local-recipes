#!/usr/bin/env bash
set -euxo pipefail

npm pack --ignore-scripts
npm install --global ./caveman-installer-*.tgz

# npm's global install creates bin/caveman as a symlink into lib/node_modules;
# noarch packages must not ship symlinks (unsupported on most Windows systems).
# Replace it with a wrapper script.
rm -f "${PREFIX}/bin/caveman"
cat > "${PREFIX}/bin/caveman" << 'WRAPPER'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec node "${SCRIPT_DIR}/../lib/node_modules/caveman-installer/bin/install.js" "$@"
WRAPPER
chmod +x "${PREFIX}/bin/caveman"
