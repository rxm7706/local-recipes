#!/bin/bash
exec java -jar "$CONDA_PREFIX/share/java/apache-tika/tika-app-@VERSION@.jar" "$@"
