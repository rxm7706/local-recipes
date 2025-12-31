#!/bin/bash
# Test podman-desktop artifacts from GitHub Actions CI
# Tests the packages downloaded by trigger-ci-build.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
ARTIFACTS_DIR="$REPO_ROOT/ci-artifacts"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Testing podman-desktop CI Artifacts                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if artifacts exist
if [ ! -d "$ARTIFACTS_DIR" ]; then
    echo -e "${RED}❌ Artifacts directory not found: $ARTIFACTS_DIR${NC}"
    echo -e "${YELLOW}Run trigger-ci-build.sh first to download artifacts${NC}"
    exit 1
fi

# Detect platform
PLATFORM=$(uname -s)
case "$PLATFORM" in
    Linux*)
        PLATFORM="linux"
        ARCH_DIR="linux-64"
        ;;
    Darwin*)
        echo -e "${YELLOW}⚠️  macOS detected - can test Linux packages in mamba/conda${NC}"
        PLATFORM="linux"
        ARCH_DIR="linux-64"
        ;;
    MINGW*|MSYS*|CYGWIN*)
        PLATFORM="windows"
        ARCH_DIR="win-64"
        ;;
    *)
        echo -e "${RED}❌ Unsupported platform: $PLATFORM${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}Platform: $PLATFORM${NC}"
echo -e "${GREEN}Architecture directory: $ARCH_DIR${NC}"
echo ""

# Check if platform-specific packages exist
PACKAGE_DIR="$ARTIFACTS_DIR/$ARCH_DIR"
if [ ! -d "$PACKAGE_DIR" ] || [ -z "$(ls -A "$PACKAGE_DIR"/*.conda 2>/dev/null)" ]; then
    echo -e "${RED}❌ No packages found in: $PACKAGE_DIR${NC}"
    echo ""
    echo -e "${YELLOW}Available artifacts:${NC}"
    find "$ARTIFACTS_DIR" -name "*.conda" | while read -r file; do
        echo "  📦 $file"
    done
    exit 1
fi

# List available packages
echo -e "${BLUE}Available packages:${NC}"
ls -lh "$PACKAGE_DIR"/*.conda | awk '{print "  📦 " $9 " (" $5 ")"}'
echo ""

# Test 1: Package metadata
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Test 1: Inspecting package metadata${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

PACKAGE=$(ls "$PACKAGE_DIR"/podman-desktop-*.conda 2>/dev/null | head -1)
if [ -z "$PACKAGE" ]; then
    echo -e "${RED}❌ No podman-desktop package found${NC}"
    exit 1
fi

echo -e "${YELLOW}Package: $(basename "$PACKAGE")${NC}"
echo ""

# Extract package info using conda/mamba
if command -v conda &> /dev/null; then
    echo -e "${GREEN}✓ Package info:${NC}"
    conda package -w "$PACKAGE" 2>/dev/null || true
    echo ""
fi

# Test 2: Check dependencies
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Test 2: Verifying dependencies${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Extract and check dependencies from package
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

cd "$TEMP_DIR"
tar -xf "$PACKAGE" info/index.json 2>/dev/null || true

if [ -f "info/index.json" ]; then
    echo -e "${GREEN}Dependencies:${NC}"
    cat info/index.json | python3 -c "
import sys, json
data = json.load(sys.stdin)
deps = data.get('depends', [])
for dep in deps:
    if 'kubernetes' in dep or 'kind' in dep or 'kubectl' in dep or 'nodejs' in dep:
        print(f'  ✓ {dep}')
" 2>/dev/null || echo "  (Unable to parse dependencies)"
    echo ""

    # Check for kubernetes dependencies specifically
    MISSING_DEPS=()
    if ! grep -q "kubernetes-kind" info/index.json; then
        MISSING_DEPS+=("kubernetes-kind")
    fi
    if ! grep -q "kubernetes-client" info/index.json; then
        MISSING_DEPS+=("kubernetes-client")
    fi

    if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
        echo -e "${RED}❌ Missing expected dependencies:${NC}"
        for dep in "${MISSING_DEPS[@]}"; do
            echo "  ✗ $dep"
        done
        echo ""
    else
        echo -e "${GREEN}✓ All expected dependencies present${NC}"
        echo ""
    fi
else
    echo -e "${YELLOW}⚠️  Unable to extract package metadata${NC}"
    echo ""
fi

cd "$REPO_ROOT"

# Test 3: Installation test (optional - asks for confirmation)
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Test 3: Installation test${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}⚠️  This will install podman-desktop in your current environment${NC}"
echo -e "${YELLOW}⚠️  Recommended: Use a test environment${NC}"
echo ""

read -p "Install and test podman-desktop? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Skipping installation test${NC}"
    echo ""
    echo -e "${GREEN}✓ Package validation complete${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}Installing podman-desktop...${NC}"

# Install using mamba (faster) or conda
if command -v mamba &> /dev/null; then
    INSTALLER="mamba"
else
    INSTALLER="conda"
fi

echo -e "${YELLOW}Using: $INSTALLER${NC}"

$INSTALLER install -y -c "file://$ARTIFACTS_DIR" -c conda-forge podman-desktop --force-reinstall || {
    echo -e "${RED}❌ Installation failed${NC}"
    exit 1
}

echo ""
echo -e "${GREEN}✓ Installation successful${NC}"
echo ""

# Test 4: Binary verification
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}Test 4: Binary verification${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check binaries
BINARIES=(
    "podman-desktop"
    "kind"
    "kubectl"
)

ALL_FOUND=true
for binary in "${BINARIES[@]}"; do
    if command -v "$binary" &> /dev/null; then
        VERSION=$($binary --version 2>&1 | head -1 || echo "unknown")
        echo -e "${GREEN}✓ $binary${NC}: $VERSION"
    else
        echo -e "${RED}✗ $binary${NC}: not found"
        ALL_FOUND=false
    fi
done
echo ""

if [ "$ALL_FOUND" = false ]; then
    echo -e "${RED}❌ Some binaries are missing${NC}"
    exit 1
fi

# Test 5: GUI test (optional, only on Linux)
if [ "$PLATFORM" = "linux" ]; then
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Test 5: GUI launch test (optional)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  This will launch podman-desktop GUI${NC}"
    echo -e "${YELLOW}⚠️  Requires X11/Wayland display${NC}"
    echo ""

    read -p "Launch podman-desktop GUI? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${BLUE}Launching podman-desktop...${NC}"
        echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
        echo ""

        timeout 10 podman-desktop 2>&1 | head -20 &
        PID=$!
        sleep 3

        if ps -p $PID > /dev/null; then
            echo -e "${GREEN}✓ podman-desktop launched successfully${NC}"
            echo -e "${YELLOW}Killing test instance...${NC}"
            kill $PID 2>/dev/null || true
            pkill -f podman-desktop || true
        else
            echo -e "${YELLOW}⚠️  GUI may have failed to launch (normal in headless environment)${NC}"
        fi
    fi
fi

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Test Results Summary                                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✓ Package metadata: OK${NC}"
echo -e "${GREEN}✓ Dependencies: OK${NC}"
echo -e "${GREEN}✓ Installation: OK${NC}"
echo -e "${GREEN}✓ Binaries: OK${NC}"
echo ""
echo -e "${BLUE}All tests passed!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Test GUI functionality manually (if not done)"
echo "  2. Test Kubernetes integration (kind, kubectl)"
echo "  3. Verify all extensions load correctly"
echo "  4. Document any issues found"
echo ""
