#!/bin/bash
# Offline build script for air-gapped environments
# Usage: ./offline-build.sh recipes/my-package [--target-platform linux-64]

set -e

# Configuration
MIRROR_PATH="${CONDA_MIRROR_PATH:-/opt/conda-mirror}"
OUTPUT_DIR="${CONDA_OUTPUT_DIR:-./output}"
BUILD_TOOL="${CONDA_BUILD_TOOL:-rattler-build}"  # or conda-build

# Parse arguments
RECIPE_PATH=""
TARGET_PLATFORM=""
EXTRA_ARGS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --target-platform)
            TARGET_PLATFORM="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --mirror)
            MIRROR_PATH="$2"
            shift 2
            ;;
        --conda-build)
            BUILD_TOOL="conda-build"
            shift
            ;;
        --rattler-build)
            BUILD_TOOL="rattler-build"
            shift
            ;;
        -*)
            EXTRA_ARGS="$EXTRA_ARGS $1"
            shift
            ;;
        *)
            RECIPE_PATH="$1"
            shift
            ;;
    esac
done

if [[ -z "$RECIPE_PATH" ]]; then
    echo "Usage: $0 <recipe-path> [--target-platform PLATFORM] [--output DIR] [--mirror PATH]"
    echo ""
    echo "Options:"
    echo "  --target-platform  Target platform (e.g., linux-64, osx-arm64)"
    echo "  --output          Output directory for packages"
    echo "  --mirror          Path to local conda mirror"
    echo "  --conda-build     Use conda-build instead of rattler-build"
    echo "  --rattler-build   Use rattler-build (default)"
    exit 1
fi

# Validate recipe path
if [[ ! -d "$RECIPE_PATH" ]] && [[ ! -f "$RECIPE_PATH" ]]; then
    echo "Error: Recipe not found: $RECIPE_PATH"
    exit 1
fi

# Detect recipe format
RECIPE_FORMAT="unknown"
if [[ -f "$RECIPE_PATH/recipe.yaml" ]] || [[ "$RECIPE_PATH" == *.yaml && -f "$RECIPE_PATH" ]]; then
    RECIPE_FORMAT="v1"
elif [[ -f "$RECIPE_PATH/meta.yaml" ]]; then
    RECIPE_FORMAT="legacy"
fi

echo "=========================================="
echo "Offline Build"
echo "=========================================="
echo "Recipe: $RECIPE_PATH"
echo "Format: $RECIPE_FORMAT"
echo "Build tool: $BUILD_TOOL"
echo "Mirror: $MIRROR_PATH"
echo "Output: $OUTPUT_DIR"
echo "Target: ${TARGET_PLATFORM:-native}"
echo "=========================================="

# Setup environment
export CONDA_OFFLINE=1
export CONDA_PKGS_DIRS="$MIRROR_PATH/pkgs"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Build based on format and tool
if [[ "$BUILD_TOOL" == "rattler-build" ]]; then
    # rattler-build command
    RECIPE_FILE="$RECIPE_PATH"
    if [[ -d "$RECIPE_PATH" ]]; then
        if [[ -f "$RECIPE_PATH/recipe.yaml" ]]; then
            RECIPE_FILE="$RECIPE_PATH/recipe.yaml"
        else
            echo "Error: rattler-build requires recipe.yaml"
            exit 1
        fi
    fi

    CMD="rattler-build build -r $RECIPE_FILE"
    CMD="$CMD -c file://$MIRROR_PATH/conda-forge"
    CMD="$CMD --output-dir $OUTPUT_DIR"

    if [[ -n "$TARGET_PLATFORM" ]]; then
        CMD="$CMD --target-platform $TARGET_PLATFORM"
    fi

    # Add variant config if exists
    if [[ -f ".ci_support/${TARGET_PLATFORM:-linux_64_}.yaml" ]]; then
        CMD="$CMD --variant-config .ci_support/${TARGET_PLATFORM:-linux_64_}.yaml"
    fi

    CMD="$CMD $EXTRA_ARGS"

    echo "Running: $CMD"
    eval $CMD

elif [[ "$BUILD_TOOL" == "conda-build" ]]; then
    # conda-build command
    CMD="conda-build $RECIPE_PATH"
    CMD="$CMD -c file://$MIRROR_PATH/conda-forge"
    CMD="$CMD --output-folder $OUTPUT_DIR"
    CMD="$CMD --no-anaconda-upload"

    # Offline mode
    CMD="$CMD --offline"

    CMD="$CMD $EXTRA_ARGS"

    echo "Running: $CMD"
    eval $CMD

else
    echo "Error: Unknown build tool: $BUILD_TOOL"
    exit 1
fi

# List output
echo ""
echo "=========================================="
echo "Build Output"
echo "=========================================="
find "$OUTPUT_DIR" -name "*.conda" -o -name "*.tar.bz2" 2>/dev/null | head -20

echo ""
echo "Build complete!"
