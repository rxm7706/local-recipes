#!/usr/bin/env bash
# pre-push hook: no push leaves the machine before `pr-preflight` is green
# (steward Story 66.2, spec-pyforge-steward CAP-154). Observed evidence:
# 2026-09-20, PR #1551 pushed after `pyforge-station-tests` + `detectors-ci`
# and went red on the touched-module coverage floor `pr-preflight` covers.
#
# The one opt-out is explicit and journaled, never silent:
#   PYFORGE_PREFLIGHT_SKIP=1 git push ...
# appends branch, head SHA, timestamp and reason ($PYFORGE_PREFLIGHT_SKIP_REASON)
# to .steward/preflight-skips.log (gitignored) and lets the push through.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"
branch="$(git rev-parse --abbrev-ref HEAD)"
head_sha="$(git rev-parse --short HEAD)"

# git feeds the refs being pushed on stdin: <local ref> <local sha> <remote ref> <remote sha>.
# A `dispatch/*` branch is the marshal supervisor's: it pushes `wip:` auto-checkpoints every few
# minutes and its landing is gated by the station's verify_commands, the S-13.7 guard and CI --
# a full preflight per checkpoint would stall every drain. Skipped, journaled, never silent.
remote_refs="$(cat || true)"
if [ -n "$remote_refs" ] && ! printf '%s\n' "$remote_refs" | awk '{print $3}' | grep -qvE '^refs/heads/dispatch/'; then
  mkdir -p .steward
  printf '%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$branch" "$head_sha" "dispatch/* branch: supervisor-gated" >> .steward/preflight-skips.log
  echo "[pre-push] dispatch/* branch -- pr-preflight left to the supervisor gate and CI (journaled)" >&2
  exit 0
fi

if [ "${PYFORGE_PREFLIGHT_SKIP:-}" = "1" ]; then
  mkdir -p .steward
  printf '%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$branch" "$head_sha" \
    "${PYFORGE_PREFLIGHT_SKIP_REASON:-no reason given}" >> .steward/preflight-skips.log
  echo "[pre-push] pr-preflight SKIPPED by PYFORGE_PREFLIGHT_SKIP=1 -- journaled in .steward/preflight-skips.log" >&2
  exit 0
fi

# git exports its own locator variables to a hook (GIT_DIR, GIT_WORK_TREE, GIT_INDEX_FILE,
# GIT_PREFIX; GIT_DIR points at .git/worktrees/<name> from a worktree). Any suite that
# `git init`s a temp repository would "re-init" that path instead and every `git add` there
# would hit the wrong repository -- the CFE regression suite did exactly that on the hook's
# first live run (2026-09-20). pr-preflight runs on the checked-out tree, never on git's env.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_PREFIX GIT_COMMON_DIR GIT_OBJECT_DIRECTORY

echo "[pre-push] running pr-preflight for $branch@$head_sha (PYFORGE_PREFLIGHT_SKIP=1 to opt out, journaled)" >&2
if ! pixi run --frozen -e pyforge-guild pr-preflight; then
  echo "[pre-push] pr-preflight is red -- push refused. Fix locally, or PYFORGE_PREFLIGHT_SKIP=1 with PYFORGE_PREFLIGHT_SKIP_REASON set." >&2
  exit 1
fi
