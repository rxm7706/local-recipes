#!/usr/bin/env bash
#
# Sync with upstream conda-forge/staged-recipes
# Fetches upstream changes and attempts to rebase local custom commits.
#

set -e

UPSTREAM_URL="https://github.com/conda-forge/staged-recipes.git"
UPSTREAM_REMOTE="upstream"
BRANCH_NAME="main" # Assuming you're syncing against the main branch

echo "=> Checking for upstream remote..."
if ! git remote get-url "$UPSTREAM_REMOTE" > /dev/null 2>&1; then
    echo "=> Adding upstream remote ($UPSTREAM_URL)..."
    git remote add "$UPSTREAM_REMOTE" "$UPSTREAM_URL"
fi

echo "=> Fetching from upstream..."
git fetch "$UPSTREAM_REMOTE"

echo "=> Stashing any unstaged changes..."
git stash -q

# Find the common ancestor between our local branch and upstream/main
COMMON_ANCESTOR=$(git merge-base HEAD "$UPSTREAM_REMOTE/$BRANCH_NAME")

echo "=> Attempting to rebase on top of upstream/$BRANCH_NAME..."
# We use --rebase-merges in case there are merge commits we want to preserve
# We also use an interactive rebase (without the -i flag, it will stop on conflicts)
# It's better to let the user resolve conflicts manually if they arise
if git rebase "$UPSTREAM_REMOTE/$BRANCH_NAME"; then
    echo "=> Rebase successful!"
else
    echo "================================================================="
    echo "=> REBASE CONFLICT DETECTED!"
    echo "=> Please resolve the conflicts manually."
    echo "=> 1. Edit the conflicting files."
    echo "=> 2. git add <resolved-files>"
    echo "=> 3. git rebase --continue"
    echo "================================================================="
    exit 1
fi

echo "=> Restoring stashed changes (if any)..."
git stash pop -q || true

echo "=> Sync complete!"
