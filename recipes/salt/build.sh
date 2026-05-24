#!/bin/bash
set -euo pipefail

$PYTHON -m pip install . -vv --no-build-isolation

# Override syspaths to point to the conda prefix
cp $RECIPE_DIR/_syspaths.py $SP_DIR/salt/_syspaths.py

# Create directory structure for salt within the conda prefix
for path in \
    etc/salt \
    var/cache/salt \
    var/run/salt \
    srv/salt \
    srv/pillar \
    var/log/salt \
    var/run
do
    mkdir -p $PREFIX/$path
    touch $PREFIX/$path/.condakeep
done

# Copy default config files
cp $SRC_DIR/conf/master $PREFIX/etc/salt/master.example
cp $SRC_DIR/conf/minion $PREFIX/etc/salt/minion.example
