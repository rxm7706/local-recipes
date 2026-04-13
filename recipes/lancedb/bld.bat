set OPENSSL_DIR=%LIBRARY_PREFIX%

cd python
%PYTHON% -m pip install . -vv --no-deps --no-build-isolation
