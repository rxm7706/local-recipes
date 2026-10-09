#!/usr/bin/env bash
# Hourly fleet poll at :30 past each hour — sync git, then wake Cursor agent.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=fleet_poll_sync.sh
source "${REPO}/scripts/fleet_poll_sync.sh"
LOOP_ROOT="${HOME}/.bmad-loops"
LOG_FILE="${REPO}/.cursor/fleet-poll.log"
PROMPT='Fleet poll (:30): run full fleet-picture (all sections verbatim), pyforge marshal status --format json, summarize delta since last poll (compare .cursor/fleet-poll-last.json if present), report if anything waits on the operator. Git sync already ran at tick time.'

sleep_until_next_half_hour() {
  local min sec wait
  min=$(date +%-M)
  sec=$(date +%-S)
  if (( min < 30 )); then
    wait=$(( (30 - min) * 60 - sec ))
  else
    wait=$(( (90 - min) * 60 - sec ))
  fi
  if (( wait < 1 )); then
    wait=3600
  fi
  sleep "$wait"
}

mkdir -p "$(dirname "$LOG_FILE")"

while true; do
  sleep_until_next_half_hour
  {
    echo "=== fleet-poll tick $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
    fleet_poll_sync "$REPO"
    if [[ -d "$LOOP_ROOT" ]]; then
      for home in "$LOOP_ROOT"/pyforge-*/; do
        [[ -d "$home/.git" ]] || continue
        fleet_poll_sync "$home"
      done
    fi
    echo "AGENT_LOOP_TICK_fleet-poll {\"prompt\":$(printf '%s' "$PROMPT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')}"
  } >>"$LOG_FILE" 2>&1
  sleep 3600
done
