#!/usr/bin/env bash
# Git sync for fleet-poll-hourly (Story 87.13 / AD-46): fast-forward loop/*
# station branches only; never rebase; never push main.
set -euo pipefail

fleet_poll_sync() {
  local dir="$1"
  local branch
  branch=$(git -C "$dir" branch --show-current 2>/dev/null || true)
  if [[ -z "$branch" ]]; then
    return 0
  fi

  git -C "$dir" fetch --quiet origin 2>/dev/null || true

  if [[ "$branch" != loop/* ]]; then
    return 0
  fi

  if git -C "$dir" rev-parse --verify "origin/main" >/dev/null 2>&1; then
    if git -C "$dir" merge-base --is-ancestor HEAD "origin/main" 2>/dev/null; then
      if ! git -C "$dir" merge --ff-only origin/main 2>/dev/null; then
        echo "fleet-poll: diverged: ${dir} (branch ${branch})" >&2
      fi
    else
      echo "fleet-poll: diverged: ${dir} (branch ${branch})" >&2
    fi
  fi

  git -C "$dir" push --ff-only origin "$branch" 2>/dev/null || true
}
