#!/usr/bin/env bash

set -ex

echo "START_MESSAGE: run_test.sh"
echo "START_MESSAGE: export flask settings"
export FLASK_APP='superset'
export SUPERSET_SECRET_KEY=$(openssl rand -base64 42)
echo "START_MESSAGE: superset db upgrade"
superset db upgrade
echo "START_MESSAGE: flask fab create-admin"
flask fab create-admin \
  --username admin \
  --firstname admin \
  --lastname admin \
  --email admin@fab.org \
  --password admin
# superset load_examples
echo "START_MESSAGE: superset init"
superset init
echo "END_MESSAGE: run_test.sh"
