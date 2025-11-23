#!/bin/bash
set -ex

# Create the target directory
mkdir -p "${PREFIX}/lib/node_modules/@openai/apps-sdk-ui"

# Copy package contents
cp -r . "${PREFIX}/lib/node_modules/@openai/apps-sdk-ui/"
