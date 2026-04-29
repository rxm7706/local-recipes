#!/bin/bash
set -euxo pipefail

INSTALL_DIR="${PREFIX}/share/copilot-api-proxy"
mkdir -p "${INSTALL_DIR}"
cp app.py "${INSTALL_DIR}/"

mkdir -p "${PREFIX}/bin"
# app.py runs uvicorn against module-level `app` via `if __name__ == "__main__"`.
# Launching from INSTALL_DIR keeps the script self-contained without polluting
# site-packages with a top-level `app` module.
cat > "${PREFIX}/bin/copilot-api-proxy" << EOF
#!/bin/bash
cd "${INSTALL_DIR}" && exec "${PREFIX}/bin/python" -u app.py "\$@"
EOF
chmod +x "${PREFIX}/bin/copilot-api-proxy"
