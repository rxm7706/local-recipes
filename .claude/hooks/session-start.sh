#!/bin/bash
# SessionStart hook for Claude Code on the web (remote containers only).
#
# Why: a remote session clones the repo fresh; `.pixi/envs` is gitignored, so
# no pixi environment exists until something runs `pixi install`. The default
# `local-recipes` env is ~9.8 GB / 1,100 packages and is NOT what a review or
# planning session needs. This hook installs pixi (if absent) and materializes
# the LEAN envs from the frozen lock so the repo's detectors and station tests
# work: `pyforge-doctor` carries `python -m pyforge.doctor.sources …`
# (bmad-drift, dream-chain, chain-completeness, spec-surface). Measured
# 2026-09-02: 8.5 s from an empty cache.
#
# Extra envs for a dev session (e.g. `python-agent-platform` / `platform-dev`
# for src/platform work) are opt-in: PYFORGE_SESSION_ENVS="pyforge-doctor platform-dev".
# Idempotent: `pixi install --frozen` is a no-op when the env already matches.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

PIXI_HOME="${PIXI_HOME:-$HOME/.pixi}"
export PIXI_HOME
export PATH="$PIXI_HOME/bin:$PATH"

# The remote agent proxy terminates TLS with its own CA; pixi/rattler and
# python both honour these (see /root/.ccr/README.md).
CA_BUNDLE="${CLAUDE_CODE_CA_BUNDLE:-/root/.ccr/ca-bundle.crt}"
if [ -f "$CA_BUNDLE" ]; then
  export SSL_CERT_FILE="$CA_BUNDLE"
  export REQUESTS_CA_BUNDLE="$CA_BUNDLE"
fi

if ! command -v pixi >/dev/null 2>&1; then
  echo "[session-start] installing pixi into $PIXI_HOME/bin"
  curl -fsSL https://pixi.sh/install.sh | PIXI_NO_PATH_UPDATE=1 bash
fi
echo "[session-start] $(pixi --version)"

cd "$CLAUDE_PROJECT_DIR"
ENVS="${PYFORGE_SESSION_ENVS:-pyforge-doctor}"
for env in $ENVS; do
  echo "[session-start] pixi install --frozen -e $env"
  pixi install --frozen -e "$env"
done

# Persist for the rest of the session so `pixi run …` works without re-export.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo "export PIXI_HOME=\"$PIXI_HOME\""
    echo "export PATH=\"$PIXI_HOME/bin:\$PATH\""
    if [ -f "$CA_BUNDLE" ]; then
      echo "export SSL_CERT_FILE=\"$CA_BUNDLE\""
      echo "export REQUESTS_CA_BUNDLE=\"$CA_BUNDLE\""
    fi
  } >> "$CLAUDE_ENV_FILE"
fi
echo "[session-start] ready: envs=$ENVS"
