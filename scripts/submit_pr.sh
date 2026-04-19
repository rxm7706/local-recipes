#!/usr/bin/env bash
#
# Automates the submission of a recipe PR to conda-forge/staged-recipes
#

set -e

if [ -z "$1" ]; then
    echo "Usage: pixi run submit-pr <recipe-name>"
    echo "Example: pixi run submit-pr my-package"
    exit 1
fi

RECIPE_NAME=$1
REPO_ROOT=$(pwd)
RECIPE_DIR="$REPO_ROOT/recipes/$RECIPE_NAME"

if [ ! -d "$RECIPE_DIR" ]; then
    echo "Error: Recipe directory $RECIPE_DIR does not exist."
    exit 1
fi

# Ensure gh CLI is authenticated
if ! gh auth status >/dev/null 2>&1; then
    echo "Error: GitHub CLI (gh) is not authenticated. Please run 'gh auth login' first."
    exit 1
fi

GITHUB_USER=$(gh api user -q .login)
if [ -z "$GITHUB_USER" ]; then
    echo "Error: Could not determine GitHub username."
    exit 1
fi

TEMP_DIR=$(mktemp -d)
echo "=> Created temporary workspace at $TEMP_DIR"

# Cleanup on exit
trap 'rm -rf "$TEMP_DIR"' EXIT

echo "=> Forking and cloning conda-forge/staged-recipes..."
cd "$TEMP_DIR"

# Fork the repository and clone it. If already forked, it just clones.
gh repo fork conda-forge/staged-recipes --clone --default-branch-only
cd staged-recipes

# Make sure we're up to date with upstream
echo "=> Syncing fork with upstream..."
git remote add upstream https://github.com/conda-forge/staged-recipes.git 2>/dev/null || true
git fetch upstream
git checkout -B main upstream/main

BRANCH_NAME="add-recipe-${RECIPE_NAME}"
echo "=> Creating branch $BRANCH_NAME..."
git checkout -b "$BRANCH_NAME"

echo "=> Copying recipe..."
cp -r "$RECIPE_DIR" recipes/

echo "=> Committing..."
git add "recipes/$RECIPE_NAME"
git commit -m "Add $RECIPE_NAME recipe"

echo "=> Pushing to origin (your fork)..."
git push -u origin "$BRANCH_NAME" --force

echo "=> Creating Pull Request..."
PR_BODY="This PR adds a new recipe for \`$RECIPE_NAME\`.

### Pre-Submission Checklist
- [x] The recipe builds locally successfully.
- [x] The recipe passes all \`conda-smithy recipe-lint\` checks.
- [x] License and checksums are verified.

*Submitted automatically via local-recipes automation.*"

gh pr create \
    --repo conda-forge/staged-recipes \
    --title "Add $RECIPE_NAME" \
    --body "$PR_BODY" \
    --head "$GITHUB_USER:$BRANCH_NAME" \
    --base main

echo "================================================================="
echo "=> PR submitted successfully for $RECIPE_NAME!"
echo "================================================================="
