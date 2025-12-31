#!/bin/bash
# Trigger GitHub Actions workflow and download artifacts for podman-desktop
# Requires: gh CLI (GitHub CLI) - https://cli.github.com/

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
RECIPE="podman-desktop"
PLATFORMS="linux,windows,macos"
WORKFLOW="test-all.yml"
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
ARTIFACTS_DIR="$REPO_ROOT/ci-artifacts"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  GitHub Actions CI Build Trigger for podman-desktop       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ Error: GitHub CLI (gh) is not installed${NC}"
    echo -e "${YELLOW}Install it with:${NC}"
    echo "  Ubuntu/Debian: sudo apt install gh"
    echo "  macOS: brew install gh"
    echo "  Other: https://cli.github.com/manual/installation"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${YELLOW}⚠️  Not authenticated with GitHub CLI${NC}"
    echo -e "${BLUE}Running: gh auth login${NC}"
    gh auth login
fi

# Confirm settings
echo -e "${GREEN}Settings:${NC}"
echo "  Recipe: $RECIPE"
echo "  Platforms: $PLATFORMS"
echo "  Workflow: $WORKFLOW"
echo "  Artifacts will be saved to: $ARTIFACTS_DIR"
echo ""

read -p "Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo -e "${BLUE}Step 1: Triggering workflow...${NC}"

# Trigger the workflow
RUN_ID=$(gh workflow run "$WORKFLOW" \
    -f recipes="$RECIPE" \
    -f platforms="$PLATFORMS" \
    -f python_version="3.12" \
    -f linux_version="alma9" \
    --json id \
    --jq '.id' 2>&1)

# Get the actual run ID (gh workflow run returns immediately)
echo -e "${YELLOW}⏳ Waiting for workflow run to be created...${NC}"
sleep 5

# Find the most recent run
LATEST_RUN=$(gh run list --workflow="$WORKFLOW" --limit 1 --json databaseId,status,conclusion --jq '.[0]')
RUN_ID=$(echo "$LATEST_RUN" | jq -r '.databaseId')

if [ -z "$RUN_ID" ] || [ "$RUN_ID" = "null" ]; then
    echo -e "${RED}❌ Failed to get workflow run ID${NC}"
    echo "Please check GitHub Actions manually:"
    echo "  https://github.com/rxm7706/local-recipes/actions"
    exit 1
fi

echo -e "${GREEN}✓ Workflow triggered successfully!${NC}"
echo -e "${BLUE}Run ID: $RUN_ID${NC}"
echo -e "${BLUE}View progress: https://github.com/rxm7706/local-recipes/actions/runs/$RUN_ID${NC}"
echo ""

echo -e "${BLUE}Step 2: Monitoring workflow progress...${NC}"
echo -e "${YELLOW}This will take approximately 30 minutes${NC}"
echo ""

# Monitor the workflow
START_TIME=$(date +%s)
LAST_STATUS=""

while true; do
    # Get current status
    RUN_DATA=$(gh run view "$RUN_ID" --json status,conclusion,databaseId 2>/dev/null || echo '{}')
    STATUS=$(echo "$RUN_DATA" | jq -r '.status // "unknown"')
    CONCLUSION=$(echo "$RUN_DATA" | jq -r '.conclusion // "null"')

    # Calculate elapsed time
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    ELAPSED_MIN=$((ELAPSED / 60))
    ELAPSED_SEC=$((ELAPSED % 60))

    # Print status update if changed
    if [ "$STATUS" != "$LAST_STATUS" ]; then
        case "$STATUS" in
            "queued")
                echo -e "${YELLOW}⏳ Status: Queued (${ELAPSED_MIN}m ${ELAPSED_SEC}s)${NC}"
                ;;
            "in_progress")
                echo -e "${BLUE}🔄 Status: In Progress (${ELAPSED_MIN}m ${ELAPSED_SEC}s)${NC}"
                ;;
            "completed")
                echo -e "${GREEN}✓ Status: Completed (${ELAPSED_MIN}m ${ELAPSED_SEC}s)${NC}"
                break
                ;;
            *)
                echo -e "${YELLOW}Status: $STATUS (${ELAPSED_MIN}m ${ELAPSED_SEC}s)${NC}"
                ;;
        esac
        LAST_STATUS="$STATUS"
    fi

    # Check if it's taking too long
    if [ $ELAPSED -gt 3600 ]; then
        echo -e "${RED}❌ Build taking longer than 1 hour. Something might be wrong.${NC}"
        echo "Check the workflow manually:"
        echo "  https://github.com/rxm7706/local-recipes/actions/runs/$RUN_ID"
        exit 1
    fi

    # Wait before checking again
    sleep 30
done

echo ""

# Check conclusion
if [ "$CONCLUSION" != "success" ]; then
    echo -e "${RED}❌ Workflow completed with status: $CONCLUSION${NC}"
    echo "Check the logs at:"
    echo "  https://github.com/rxm7706/local-recipes/actions/runs/$RUN_ID"
    exit 1
fi

echo -e "${GREEN}✓ Build succeeded!${NC}"
echo ""

echo -e "${BLUE}Step 3: Downloading artifacts...${NC}"

# Create artifacts directory
mkdir -p "$ARTIFACTS_DIR"
cd "$ARTIFACTS_DIR"

# Download all artifacts
echo -e "${YELLOW}Downloading artifacts to: $ARTIFACTS_DIR${NC}"
gh run download "$RUN_ID" --dir "run-$RUN_ID"

echo -e "${GREEN}✓ Artifacts downloaded!${NC}"
echo ""

# List downloaded artifacts
echo -e "${BLUE}Downloaded artifacts:${NC}"
find "run-$RUN_ID" -name "*.conda" -o -name "*.tar.bz2" | while read -r file; do
    SIZE=$(du -h "$file" | cut -f1)
    echo "  📦 $(basename "$file") ($SIZE)"
done
echo ""

# Extract artifacts
echo -e "${BLUE}Step 4: Organizing artifacts...${NC}"

# Create platform directories
mkdir -p linux-64 win-64 osx-64 osx-arm64

# Move/copy artifacts to platform directories
if [ -d "run-$RUN_ID/linux-64-conda-packages" ]; then
    echo -e "${YELLOW}Extracting Linux artifacts...${NC}"
    cp -v "run-$RUN_ID/linux-64-conda-packages"/*.conda linux-64/ 2>/dev/null || true
fi

if [ -d "run-$RUN_ID/win-64-conda-packages" ]; then
    echo -e "${YELLOW}Extracting Windows artifacts...${NC}"
    cp -v "run-$RUN_ID/win-64-conda-packages"/*.conda win-64/ 2>/dev/null || true
fi

if [ -d "run-$RUN_ID/osx-64-conda-packages" ]; then
    echo -e "${YELLOW}Extracting macOS x64 artifacts...${NC}"
    cp -v "run-$RUN_ID/osx-64-conda-packages"/*.conda osx-64/ 2>/dev/null || true
fi

if [ -d "run-$RUN_ID/osx-arm64-conda-packages" ]; then
    echo -e "${YELLOW}Extracting macOS arm64 artifacts...${NC}"
    cp -v "run-$RUN_ID/osx-arm64-conda-packages"/*.conda osx-arm64/ 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}✓ All done!${NC}"
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Artifacts Summary                                         ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Summary
echo "📁 Artifacts location: $ARTIFACTS_DIR"
echo ""

if [ -n "$(ls -A linux-64/*.conda 2>/dev/null)" ]; then
    echo -e "${GREEN}✓ Linux packages:${NC}"
    ls -lh linux-64/*.conda | awk '{print "  " $9 " (" $5 ")"}'
fi

if [ -n "$(ls -A win-64/*.conda 2>/dev/null)" ]; then
    echo -e "${GREEN}✓ Windows packages:${NC}"
    ls -lh win-64/*.conda | awk '{print "  " $9 " (" $5 ")"}'
fi

if [ -n "$(ls -A osx-64/*.conda 2>/dev/null)" ]; then
    echo -e "${GREEN}✓ macOS x64 packages:${NC}"
    ls -lh osx-64/*.conda | awk '{print "  " $9 " (" $5 ")"}'
fi

if [ -n "$(ls -A osx-arm64/*.conda 2>/dev/null)" ]; then
    echo -e "${GREEN}✓ macOS arm64 packages:${NC}"
    ls -lh osx-arm64/*.conda | awk '{print "  " $9 " (" $5 ")"}'
fi

echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""
echo "  Linux testing:"
echo "    mamba install -c file://$ARTIFACTS_DIR -c conda-forge podman-desktop"
echo "    podman-desktop"
echo ""
echo "  Windows testing (on Windows machine):"
echo "    mamba install -c file:///%CD%/ci-artifacts -c conda-forge podman-desktop"
echo "    podman-desktop"
echo ""
echo "  macOS testing:"
echo "    mamba install -c file://$ARTIFACTS_DIR -c conda-forge podman-desktop"
echo "    open -a 'Podman Desktop'"
echo ""
echo "  Or use the test script:"
echo "    ./recipes/podman-desktop/test-ci-artifacts.sh"
echo ""
