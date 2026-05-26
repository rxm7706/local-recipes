set OPENSSL_DIR=%LIBRARY_PREFIX%
set OPENSSL_NO_VENDOR=1

REM Per conda-forge.org/docs/maintainer/example_recipes/rust/ — strip
REM symbols from the release cdylib. LTO is intentionally NOT set here:
REM daft's 500+ crate dep tree exceeds the conda-forge Windows runner's
REM RAM budget during fat-LTO final link (Azure build 1526273 OOM'd all
REM 10 Windows configs).
set CARGO_PROFILE_RELEASE_STRIP=symbols

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
