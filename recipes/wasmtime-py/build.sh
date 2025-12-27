#!/bin/bash
set -euxo pipefail

# Step 1: Install wasm32-wasip1 target and wasm-tools using cargo
echo "Installing WebAssembly build dependencies..."
rustup target add wasm32-wasip1 || true
cargo install --locked wasm-tools || cargo install wasm-tools || echo "wasm-tools may already be installed"

# Step 2: Build WebAssembly bindgen library
echo "Building WebAssembly bindgen..."
cargo build --target wasm32-wasip1 --release -p bindgen

# Step 3: Create WebAssembly component
echo "Creating WASM component..."
wasm-tools component new ./rust/target/wasm32-wasip1/release/bindgen.wasm \
  -o target/component.wasm \
  --adapt wasi_snapshot_preview1=adapters/wasi_snapshot_preview1.wasm

# Step 4: Generate native bindings from the component
echo "Generating native bindings..."
cargo run -p=bindgen --features=cli ./target/component.wasm

# Step 5: Install Python package
echo "Installing Python package..."
${PYTHON} -m pip install . -vv --no-deps --no-build-isolation
