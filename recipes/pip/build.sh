#!/bin/bash

$PYTHON -m pip install . -vv --no-build-isolation --no-deps

cd $PREFIX/bin
rm -f pip2* pip3*
rm -f $SP_DIR/__pycache__/pkg_res*
