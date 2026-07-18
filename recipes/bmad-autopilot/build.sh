#!/usr/bin/env bash
set -euxo pipefail

if [ ! -f "install.sh" ] || [ ! -d "skills" ]; then
    echo "ERROR: install.sh / skills/ not found in SRC_DIR: $(pwd)" >&2
    ls -la
    exit 1
fi

SHARE="${PREFIX}/share/bmad-autopilot"
mkdir -p "${SHARE}"
cp -r skills commands scripts workflows docs "${SHARE}/"
cp install.sh VERSION config.example README.md LICENSE CLAUDE.md "${SHARE}/"
chmod +x "${SHARE}/install.sh"
chmod +x "${SHARE}"/scripts/*.sh

# Wrapper that runs the upstream installer from the packaged tree.
mkdir -p "${PREFIX}/bin"
cat > "${PREFIX}/bin/bmad-autopilot-install" << 'WRAPPER'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${SCRIPT_DIR}/../share/bmad-autopilot/install.sh" "$@"
WRAPPER
chmod +x "${PREFIX}/bin/bmad-autopilot-install"
