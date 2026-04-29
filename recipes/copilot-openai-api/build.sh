#!/bin/bash
set -euxo pipefail

INSTALL_DIR="${PREFIX}/share/copilot-openai-api"
mkdir -p "${INSTALL_DIR}"
cp main.py run.py "${INSTALL_DIR}/"

mkdir -p "${PREFIX}/bin"
# run.py calls uvicorn.run("main:app", ...) — that string is resolved against
# sys.path. Launching from INSTALL_DIR puts main.py on sys.path[0] without
# polluting site-packages with a top-level "main" module.
cat > "${PREFIX}/bin/copilot-openai-api" << EOF
#!/bin/bash
cd "${INSTALL_DIR}" && exec "${PREFIX}/bin/python" run.py "\$@"
EOF
chmod +x "${PREFIX}/bin/copilot-openai-api"
