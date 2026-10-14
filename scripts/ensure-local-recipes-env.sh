#!/usr/bin/env bash
# verify-env: confirm the shell runs inside the local-recipes pixi env and its recipe
# factory answers (steward Story 100.4's recipe-factory smoke; the pixi task named this
# script before it existed, so verify-env exited 127).
set -euo pipefail

if [ "${PIXI_ENVIRONMENT_NAME:-}" != "local-recipes" ]; then
  echo "verify-env: not inside the local-recipes env (PIXI_ENVIRONMENT_NAME=${PIXI_ENVIRONMENT_NAME:-unset}); run: pixi run -e local-recipes verify-env" >&2
  exit 1
fi

rattler-build --version
python -c "import conda_smithy, sys; print('conda-smithy', conda_smithy.__version__, 'python', sys.version.split()[0])"
echo "verify-env: ok -- local-recipes env at ${CONDA_PREFIX:-?}"
