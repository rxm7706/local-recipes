#!/bin/bash
# Load environment variables from .env file if it exists
# Additionally: when inside this repository set PIXI_PROJECT_MANIFEST to the
# local pixi.toml and pick a default PIXI env from the [environments]
# section (fall back to "local-recipes" when present). If PIXI_ENV is not
# already set, set it to that default so tools that call `pixi` will use the
# local manifest and a sensible default environment.

# Determine project root. Prefer PIXI_PROJECT_ROOT if set (pixi may set it),
# otherwise try git top-level, otherwise use current directory.
if [ -z "${PIXI_PROJECT_ROOT:-}" ]; then
    if git_root=$(git rev-parse --show-toplevel 2>/dev/null); then
        PIXI_PROJECT_ROOT="$git_root"
    else
        PIXI_PROJECT_ROOT="$PWD"
    fi
fi

ENV_FILE="$PIXI_PROJECT_ROOT/.env"

if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

# Prefer local pixi.toml manifest in the project when present
MANIFEST_FILE="$PIXI_PROJECT_ROOT/pixi.toml"
if [ -f "$MANIFEST_FILE" ]; then
    export PIXI_PROJECT_MANIFEST="$MANIFEST_FILE"

    # Try to detect a default environment from the [environments] table.
    # We'll pick the first key defined under [environments]. If that fails,
    # prefer "local-recipes" if present. If still not found, leave unset.
    if [ -r "$MANIFEST_FILE" ]; then
        # 1) Check for an explicit "# default-env: <name>" directive in the
        #    [environments] section of pixi.toml. This lets the repo author
        #    declare which env should be activated by default.
        default_env=$(awk '
            /^\[environments\]/{in_env=1; next}
            /^\[/{in_env=0}
            in_env && /^#[[:space:]]*default-env:/ {
                sub(/^#[[:space:]]*default-env:[[:space:]]*/,"")
                gsub(/[[:space:]]+$/,"")
                print
                exit
            }
        ' "$MANIFEST_FILE") || default_env=""

        # 2) Fallback: use the first environment key defined under [environments]
        if [ -z "$default_env" ]; then
            default_env=$(awk '
                /^\[environments\]/{in_env=1; next}
                /^\[/{in_env=0}
                in_env && /^[[:space:]]*[^#].*=/ {
                    line=$0
                    sub(/=.*/,"",line)
                    gsub(/^[ \t]+|[ \t]+$/,"",line)
                    print line
                    exit
                }
            ' "$MANIFEST_FILE") || default_env=""
        fi

        # 3) Last resort: look for "local-recipes" anywhere
        if [ -z "$default_env" ]; then
            if grep -qE '^[[:space:]]*local-recipes\s*=' "$MANIFEST_FILE"; then
                default_env="local-recipes"
            fi
        fi

        if [ -n "$default_env" ]; then
            export PIXI_DEFAULT_ENV="$default_env"
            # If PIXI_ENV is not explicitly provided by caller, set it to default
            if [ -z "${PIXI_ENV:-}" ]; then
                export PIXI_ENV="$PIXI_DEFAULT_ENV"
            fi
        fi
    fi
fi

# Helpful (non-fatal) debug output when this script is sourced interactively
if [ -n "${PS1:-}" ]; then
    echo "[pixi] using manifest: ${PIXI_PROJECT_MANIFEST:-(none)}"
    if [ -n "${PIXI_DEFAULT_ENV:-}" ]; then
        echo "[pixi] default env: $PIXI_DEFAULT_ENV (PIXI_ENV=${PIXI_ENV:-})"
    fi
fi

