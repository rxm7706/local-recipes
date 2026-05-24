#!/usr/bin/env bash

set -euo pipefail
export OPENSSL_DIR=${PREFIX}
export OPENSSL_NO_VENDOR=1

# build dashboard assets using bun
pushd ./src/daft-dashboard/frontend
npm install
npm run build
popd

# aws-lc-sys jitterentropy raises when compiled with -O1/-O2/-O3
# use -O0 in all CFLAGS* env vars
#
# in the future, should be able just set AWS_LC_SYS_NO_JITTER_ENTROPY=1 instead
# (this won't work until daft bumps its aws-lc-rs dependency to 0.32.3)
# https://github.com/aws/aws-lc-rs/issues/912#issuecomment-3403526421
for var in $(env | grep -o '^CFLAGS[^=]*'); do
    eval "export $var=\"$(eval echo \$$var | sed 's/-O[0-3]/-O0/g')\""
done

cargo-bundle-licenses --format yaml --output THIRDPARTY.yml
${PYTHON} -m pip install . -vv --no-deps --no-build-isolation
