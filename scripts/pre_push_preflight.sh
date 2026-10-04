#!/usr/bin/env bash
# pre-push hook: no push leaves the machine before `pr-preflight` is green
# (steward Story 66.2, spec-pyforge-steward CAP-154). Observed evidence:
# 2026-09-20, PR #1551 pushed after `pyforge-station-tests` + `detectors-ci`
# and went red on the touched-module coverage floor `pr-preflight` covers.
#
# The one opt-out is explicit and journaled, never silent:
#   PYFORGE_PREFLIGHT_SKIP=1 git push ...
# appends timestamp, the pushed ref(s) and sha(s), and the reason
# ($PYFORGE_PREFLIGHT_SKIP_REASON) to .steward/preflight-skips.log (gitignored) and lets
# the push through. Automatic, journaled skips: branch deletes, `dispatch/*` branches, and
# a push proved tag-only under `refs/tags/preserve/` or `refs/tags/archive/` (Story 85.3,
# CAP-165). In the pre-commit form the pushing tool sets PYFORGE_PREFLIGHT_PRESERVE_TAGS_PROOF=1
# (pyforge.core.preserve_refs, marshal Story 87.15) -- never inferred from the first ref alone.
# Every journal line names the pushed ref(s) and sha(s) (Story 68.2).
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
stdin_refs=""
remote_ref="${PRE_COMMIT_REMOTE_BRANCH:-}"
local_sha="${PRE_COMMIT_TO_REF:-}"
if [ -z "$remote_ref" ]; then
  stdin_refs="$(cat 2>/dev/null || true)"
  if [ -n "$stdin_refs" ]; then
    remote_ref="$(printf '%s\n' "$stdin_refs" | awk '{print $3}' | paste -sd' ' -)"
    local_sha="$(printf '%s\n' "$stdin_refs" | awk '{print $2}' | paste -sd' ' -)"
  fi
fi

# Every skip is journaled with WHAT was pushed -- the remote ref(s) and local sha(s) -- falling back
# to the checked-out branch and HEAD only when no ref information arrived (Story 68.2, CAP-156;
# the journal used to record the checked-out branch, e.g. `main` for eight `loop/*` pushes).
journal_skip() {
  local refs="${remote_ref:-$branch}" shas=""
  local s
  for s in $local_sha; do shas="${shas:+$shas }${s:0:10}"; done
  mkdir -p .steward
  printf '%s\t%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$refs" "${shas:-$head_sha}" "$1" >> .steward/preflight-skips.log
}

# A branch delete (`git push --delete`, local sha all zeros) pushes no commits: nothing to preflight.
if [ -n "$local_sha" ] && ! printf '%s\n' $local_sha | grep -qvE '^0+$'; then
  journal_skip "branch delete: nothing to preflight"
  echo "[pre-push] branch delete -- nothing to preflight (journaled)" >&2
  exit 0
fi

# A `dispatch/*` branch is the marshal supervisor's: it pushes `wip:` auto-checkpoints every few
# minutes and its landing is gated by the station's verify_commands, the S-13.7 guard and CI --
# a full preflight per checkpoint would stall every drain. Skipped, journaled, never silent.
if [ -n "$remote_ref" ] && ! printf '%s\n' $remote_ref | grep -qvE '^refs/heads/dispatch/'; then
  journal_skip "dispatch/* branch: supervisor-gated"
  echo "[pre-push] dispatch/* branch -- pr-preflight left to the supervisor gate and CI (journaled)" >&2
  exit 0
fi

_is_preserve_or_archive_tag() {
  # case globs do not match `/` in nested tag names (bash pathname rules).
  printf '%s\n' "$1" | grep -qxE 'refs/tags/preserve/.+|refs/tags/archive/.+'
}

_nonzero_sha() {
  [ -n "$1" ] && ! printf '%s\n' "$1" | grep -qvE '^0+$'
}

# Bare-git form: every stdin line must name a preserve/archive tag with a non-zero local sha.
_stdin_is_tag_only_preserve_archive() {
  [ -n "$stdin_refs" ] || return 1
  local line loc_ref loc_sha rem_ref rem_sha
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    loc_ref="$(printf '%s\n' "$line" | awk '{print $1}')"
    loc_sha="$(printf '%s\n' "$line" | awk '{print $2}')"
    rem_ref="$(printf '%s\n' "$line" | awk '{print $3}')"
    rem_sha="$(printf '%s\n' "$line" | awk '{print $4}')"
    _is_preserve_or_archive_tag "$rem_ref" || return 1
    _nonzero_sha "$loc_sha" || return 1
  done <<EOF
$stdin_refs
EOF
  return 0
}

# Pre-commit form: skip only when the tool supplied proof -- not when the first ref alone looks like a tag.
_precommit_has_proven_preserve_archive_push() {
  [ "${PYFORGE_PREFLIGHT_PRESERVE_TAGS_PROOF:-}" = "1" ] || return 1
  _is_preserve_or_archive_tag "$remote_ref" || return 1
  _nonzero_sha "$local_sha" || return 1
  return 0
}

if [ -z "${PRE_COMMIT_REMOTE_BRANCH:-}" ] && _stdin_is_tag_only_preserve_archive; then
  journal_skip "preserve/archive tag-only push"
  echo "[pre-push] preserve/archive tag-only push -- pr-preflight skipped (journaled)" >&2
  exit 0
fi

if [ -n "${PRE_COMMIT_REMOTE_BRANCH:-}" ] && _precommit_has_proven_preserve_archive_push; then
  journal_skip "preserve/archive tag-only push"
  echo "[pre-push] preserve/archive tag-only push -- pr-preflight skipped (journaled)" >&2
  exit 0
fi

# No "nothing new" skip lives here (Story 68.2 review 1): under pre-commit this hook sees only the
# FIRST ref of a multi-ref push, so it cannot prove what the others carry. A tool that proves a
# push carries nothing new -- `marshal refresh` fast-forwarding a loop home to origin/main -- sets
# the journaled opt-out below with that proof as its reason (marshal Story 57.1).
if [ "${PYFORGE_PREFLIGHT_SKIP:-}" = "1" ]; then
  journal_skip "${PYFORGE_PREFLIGHT_SKIP_REASON:-no reason given}"
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
