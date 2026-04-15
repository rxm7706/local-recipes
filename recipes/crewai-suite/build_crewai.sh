#!/bin/bash
set -euxo pipefail

cd "${SRC_DIR}/crewai_src"
"${PYTHON}" -m pip install . -vv --no-deps --no-build-isolation
