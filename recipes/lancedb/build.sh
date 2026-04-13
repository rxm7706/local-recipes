#!/bin/bash

set -euxo pipefail

export OPENSSL_DIR=$PREFIX

pushd python
${PYTHON} -m pip install . -vv --no-deps --no-build-isolation
