@echo off
setlocal

set "module=github.com/git-pkgs/forge"
set "CGO_ENABLED=0"
set "GOTOOLCHAIN=local"
set "GOFLAGS=-mod=mod"

cd /d "%SRC_DIR%"

if exist "%SRC_DIR%\library_licenses" rmdir /s /q "%SRC_DIR%\library_licenses"
mkdir "%SRC_DIR%\library_licenses"

call go-licenses save ./cmd/forge --save_path "%SRC_DIR%\library_licenses" --force
if errorlevel 1 exit /b 1

if not exist "%LIBRARY_BIN%" mkdir "%LIBRARY_BIN%"

call go build -trimpath ^
    -ldflags "-s -w -X %module%/internal/cli.Version=%PKG_VERSION%" ^
    -o "%LIBRARY_BIN%\forge.exe" ^
    ./cmd/forge
if errorlevel 1 exit /b 1
