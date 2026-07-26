set OPENSSL_DIR=%LIBRARY_PREFIX%
set OPENSSL_NO_VENDOR=1

REM build dashboard assets using bun
pushd .\src\daft-dashboard\frontend
if errorlevel 1 exit 1
call npm install
if errorlevel 1 exit 1
call npm run build
if errorlevel 1 exit 1
popd
if errorlevel 1 exit 1

cargo-bundle-licenses --format yaml --output THIRDPARTY.yml
if errorlevel 1 exit 1

%PYTHON% -m pip install . -vv --no-deps --no-build-isolation
if errorlevel 1 exit 1
