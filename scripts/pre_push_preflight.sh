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

# Which refs are being pushed. Under pre-commit a pre-push hook gets NO stdin -- pre-commit
# consumes it and exposes the refs as PRE_COMMIT_REMOTE_BRANCH (refs/heads/...), PRE_COMMIT_TO_REF
# (the local sha; all zeros for a delete) and PRE_COMMIT_FROM_REF. Run bare by git, the same facts
# arrive on stdin as `<local ref> <local sha> <remote ref> <remote sha>` lines. Read both; the two
# skips below never fired on the first live pushes (2026-09-20) because only stdin was read.
remote_ref="${PRE_COMMIT_REMOTE_BRANCH:-}"
local_sha="${PRE_COMMIT_TO_REF:-}"
if [ -z "$remote_ref" ]; then
  stdin_refs="$(cat 2>/dev/null || true)"
  if [ -n "$stdin_refs" ]; then
    remote_ref="$(printf '%s\n' "$stdin_refs" | awk '{print $3}' | paste -sd' ' -)"
    local_sha="$(printf '%s\n' "$stdin_refs" | awk '{print $2}' | paste -sd' ' -)"
  fi
fi

# A branch delete (`git push --delete`, local sha all zeros) pushes no commits: nothing to preflight.
if [ -n "$local_sha" ] && ! printf '%s\n' $local_sha | grep -qvE '^0+$'; then
  echo "[pre-push] branch delete -- nothing to preflight" >&2
  exit 0
fi

# A `dispatch/*` branch is the marshal supervisor's: it pushes `wip:` auto-checkpoints every few
# minutes and its landing is gated by the station's verify_commands, the S-13.7 guard and CI --
# a full preflight per checkpoint would stall every drain. Skipped, journaled, never silent.
if [ -n "$remote_ref" ] && ! printf '%s\n' $remote_ref | grep -qvE '^refs/heads/dispatch/'; then
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
