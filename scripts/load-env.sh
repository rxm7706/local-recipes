#!/bin/bash
# Load environment variables from .env file if it exists

ENV_FILE="$PIXI_PROJECT_ROOT/.env"

if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi
