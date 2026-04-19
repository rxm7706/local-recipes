#!/bin/bash
# Test suite for scripts/load-env.sh
# Run: bash tests/test_load_env.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOAD_ENV="$SCRIPT_DIR/scripts/load-env.sh"
PIXI_TOML="$SCRIPT_DIR/pixi.toml"

PASS=0
FAIL=0

assert_eq() {
    local desc="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then
        echo "  ✓ $desc"
        ((PASS++))
    else
        echo "  ✗ $desc (expected='$expected', got='$actual')"
        ((FAIL++))
    fi
}

reset_vars() {
    unset PIXI_PROJECT_MANIFEST PIXI_ENV PIXI_DEFAULT_ENV PIXI_PROJECT_ROOT PS1 2>/dev/null || true
}

# --- Test 1: Syntax check ---
echo "Test 1: Syntax check"
if bash -n "$LOAD_ENV"; then
    echo "  ✓ No syntax errors"
    ((PASS++))
else
    echo "  ✗ Syntax errors found"
    ((FAIL++))
fi

# --- Test 2: Picks up default-env directive ---
echo "Test 2: Picks up 'default-env: local-recipes' directive"
reset_vars
export PIXI_PROJECT_ROOT="$SCRIPT_DIR"
source "$LOAD_ENV"
assert_eq "PIXI_PROJECT_MANIFEST set" "$PIXI_TOML" "$PIXI_PROJECT_MANIFEST"
assert_eq "PIXI_DEFAULT_ENV=local-recipes" "local-recipes" "$PIXI_DEFAULT_ENV"
assert_eq "PIXI_ENV=local-recipes" "local-recipes" "$PIXI_ENV"

# --- Test 3: Respects caller-provided PIXI_ENV ---
echo "Test 3: Does not override caller-provided PIXI_ENV"
reset_vars
export PIXI_PROJECT_ROOT="$SCRIPT_DIR"
export PIXI_ENV=build
source "$LOAD_ENV"
assert_eq "PIXI_ENV still 'build'" "build" "$PIXI_ENV"
assert_eq "PIXI_DEFAULT_ENV=local-recipes" "local-recipes" "$PIXI_DEFAULT_ENV"

# --- Test 4: Fallback to first env key when directive removed ---
echo "Test 4: Fallback to first env key when directive is absent"
reset_vars
export PIXI_PROJECT_ROOT="$SCRIPT_DIR"
# Temporarily patch pixi.toml
cp "$PIXI_TOML" "$PIXI_TOML.bak"
sed -i 's/^# default-env: local-recipes/# (no directive)/' "$PIXI_TOML"
source "$LOAD_ENV"
assert_eq "PIXI_DEFAULT_ENV=linux (first key)" "linux" "$PIXI_DEFAULT_ENV"
assert_eq "PIXI_ENV=linux" "linux" "$PIXI_ENV"
# Restore
mv "$PIXI_TOML.bak" "$PIXI_TOML"

# --- Test 5: Changing the directive value ---
echo "Test 5: Changing directive to 'grayskull'"
reset_vars
export PIXI_PROJECT_ROOT="$SCRIPT_DIR"
cp "$PIXI_TOML" "$PIXI_TOML.bak"
sed -i 's/^# default-env: local-recipes/# default-env: grayskull/' "$PIXI_TOML"
source "$LOAD_ENV"
assert_eq "PIXI_DEFAULT_ENV=grayskull" "grayskull" "$PIXI_DEFAULT_ENV"
assert_eq "PIXI_ENV=grayskull" "grayskull" "$PIXI_ENV"
mv "$PIXI_TOML.bak" "$PIXI_TOML"

# --- Test 6: Auto-detects PIXI_PROJECT_ROOT from git ---
echo "Test 6: Auto-detects PIXI_PROJECT_ROOT via git"
reset_vars
cd "$SCRIPT_DIR"
source "$LOAD_ENV"
assert_eq "PIXI_PROJECT_ROOT detected" "$SCRIPT_DIR" "$PIXI_PROJECT_ROOT"

# --- Summary ---
echo ""
echo "Results: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi


