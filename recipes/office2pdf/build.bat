@echo off
:: The [patch.crates-io] git-fork deps are supplied as sibling source: entries
:: (_src\umya, _src\docxrs) and repointed to relative paths by
:: patches\0001-vendor-git-fork-deps.patch, so the build is offline-safe.
cd /d "%SRC_DIR%\_src\office2pdf"
if errorlevel 1 exit 1

set CARGO_PROFILE_RELEASE_STRIP=symbols

:: Canonical conda-forge Rust CLI install; Windows install root is LIBRARY_PREFIX.
:: --locked omitted (upstream ships no Cargo.lock; see recipe CFE comments).
cargo auditable install --no-track --bins --root "%LIBRARY_PREFIX%" --path crates\office2pdf-cli
if errorlevel 1 exit 1

cargo-bundle-licenses --format yaml --output "%SRC_DIR%\THIRDPARTY.yml"
if errorlevel 1 exit 1

copy /Y LICENSE "%SRC_DIR%\LICENSE"
if errorlevel 1 exit 1
