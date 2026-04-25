#!/usr/bin/env bash
# Run the conda-forge-expert quarterly doc audit locally via the `claude` CLI.
# Mirrors the remote routine `trig_015z9XF8ExDJuN9qsZYGYKcu`.
#
# Usage:
#   .claude/skills/conda-forge-expert/automation/run-audit-local.sh [--branch NAME] [--dry-run]
#
# Flags:
#   --branch NAME   Check out (or create) NAME before invoking the agent.
#                   Defaults to running on the current branch.
#   --dry-run       Print the prompt and exit without calling claude.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT_FILE="$SCRIPT_DIR/quarterly-audit.prompt.md"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

branch=""
dry_run=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --branch) branch="$2"; shift 2 ;;
        --dry-run) dry_run=1; shift ;;
        -h|--help)
            sed -n '2,12p' "$0"
            exit 0
            ;;
        *) echo "unknown flag: $1" >&2; exit 2 ;;
    esac
done

if [[ ! -f "$PROMPT_FILE" ]]; then
    echo "missing prompt file: $PROMPT_FILE" >&2
    exit 1
fi

# Strip the YAML frontmatter so the agent receives the body only.
prompt=$(awk '
    BEGIN { in_fm = 0; seen = 0 }
    /^---$/ {
        if (seen == 0) { in_fm = 1; seen = 1; next }
        else { in_fm = 0; next }
    }
    in_fm == 0 && seen == 1 { print }
' "$PROMPT_FILE")

if [[ "$dry_run" -eq 1 ]]; then
    printf '%s\n' "$prompt"
    exit 0
fi

cd "$REPO_ROOT"

if [[ -n "$branch" ]]; then
    if git show-ref --quiet "refs/heads/$branch"; then
        git checkout "$branch"
    else
        git checkout -b "$branch"
    fi
fi

if ! command -v claude >/dev/null 2>&1; then
    echo "claude CLI not found on PATH — install from https://claude.ai/code" >&2
    exit 1
fi

claude -p "$prompt"
