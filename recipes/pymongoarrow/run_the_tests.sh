#!/bin/bash
set -ex
URL=https://fastdl.mongodb.org/osx/mongodb-macos-x86_64-6.0.7.tgz
curl --retry 3 -sS --max-time 300 --retry-all-errors $URL --output mongodb-binaries.tgz
tar xfz mongodb-binaries.tgz
rm -f mongodb-binaries.tgz
mv mongodb* mongodb
chmod -R +x mongodb
 ./mongodb/bin/mongod --version

export DB_PATH="$SRC_DIR/temp-mongo-db"
export LOG_PATH="$SRC_DIR/mongolog"
export PID_FILE_PATH="$SRC_DIR/mongopidfile"

mkdir "$DB_PATH"

 ./mongodb/bin/mongod --dbpath="$DB_PATH" --fork --logpath="$LOG_PATH" --pidfilepath="$PID_FILE_PATH"

# Remove the local copy of the source files
rm -rf pymongoarrow
python -m pytest -W default --ignore test/test_pandas.py --ignore=test/pandas_types

# Terminate the forked process after the test suite exits
kill `cat $PID_FILE_PATH`