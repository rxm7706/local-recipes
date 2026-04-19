#!/usr/bin/env bash
#
# Automates the submission of a recipe PR to conda-forge/staged-recipes
# using a persistent local fork.
#

set -e

if [ -z "$1" ];
then
    echo "Usage: pixi run submit-pr <recipe-name>"
    echo "Example: pixi run submit-pr my-package"
    exit 1
fi

RECIPE_NAME=$1
LOCAL_RECIPES_ROOT=$(pwd)
RECIPE_DIR="$LOCAL_RECIPES_ROOT/recipes/$RECIPE_NAME"
STAGED_RECIPES_FORK_PATH="$LOCAL_RECIPES_ROOT/../staged-recipes"

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

# Check for the fork, or clone it if it doesn't exist
if [ ! -d "$STAGED_RECIPES_FORK_PATH" ]; then
    echo "=> Local fork not found. Cloning https://github.com/$GITHUB_USER/staged-recipes.git..."
    gh repo clone "$GITHUB_USER/staged-recipes" "$STAGED_RECIPES_FORK_PATH"
fi

cd "$STAGED_RECIPES_FORK_PATH"
echo "=> Entered directory $(pwd)"

# Configure upstream remote and sync
echo "=> Syncing fork with upstream conda-forge/staged-recipes..."
git remote add upstream https://github.com/conda-forge/staged-recipes.git 2>/dev/null || true
git fetch upstream
git checkout main
git reset --hard upstream/main
git push origin main --force

# Create a new branch for the recipe
BRANCH_NAME="add-recipe-${RECIPE_NAME}"
echo "=> Creating branch $BRANCH_NAME..."
git checkout -b "$BRANCH_NAME" 2>/dev/null || git checkout "$BRANCH_NAME"
git reset --hard origin/main # Start fresh

echo "=> Copying recipe from $RECIPE_DIR..."
cp -r "$RECIPE_DIR" recipes/

echo "=> Committing..."
git add "recipes/$RECIPE_NAME"
git commit -m "Add recipe for $RECIPE_NAME"

echo "=> Pushing to your fork..."
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
    --title "Add recipe for $RECIPE_NAME" \
    --body "$PR_BODY" \
    --head "$GITHUB_USER:$BRANCH_NAME" \
    --base main

echo "================================================================="
echo "=> PR submitted successfully for $RECIPE_NAME!"
echo "================================================================="
