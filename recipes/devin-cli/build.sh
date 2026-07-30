#!/usr/bin/env bash
set -euxo pipefail

# The release bundle is already laid out as bin/ + share/; just relocate it.
if [ ! -f "bin/devin" ]; then
    echo "ERROR: bin/devin not found in SRC_DIR: $(pwd)" >&2
    ls -la
    exit 1
fi

mkdir -p "${PREFIX}/bin"
cp bin/devin "${PREFIX}/bin/devin"
chmod +x "${PREFIX}/bin/devin"

# Bundled docs (share/devin/docs/*.mdx). share/man is shipped empty upstream.
if [ -d "share/devin" ]; then
    mkdir -p "${PREFIX}/share"
    cp -r share/devin "${PREFIX}/share/"
fi

# Our own proprietary-status notice; upstream ships no license file.
cp "${RECIPE_DIR}/LICENSE.txt" "${SRC_DIR}/LICENSE.txt"
