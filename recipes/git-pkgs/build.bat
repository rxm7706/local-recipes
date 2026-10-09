@echo off
setlocal

set "module=github.com/git-pkgs/git-pkgs"
set "CGO_ENABLED=0"
set "GOTOOLCHAIN=local"
set "GOFLAGS=-mod=mod"

cd /d "%SRC_DIR%"

call go mod tidy
if errorlevel 1 exit /b 1
call go run scripts/generate-man/main.go
if errorlevel 1 exit /b 1
call go run scripts/generate-docs/main.go
if errorlevel 1 exit /b 1

if exist "%SRC_DIR%\library_licenses" rmdir /s /q "%SRC_DIR%\library_licenses"
mkdir "%SRC_DIR%\library_licenses"

call go-licenses save . --save_path "%SRC_DIR%\library_licenses" --force --ignore=github.com/oapi-codegen/nullable
if errorlevel 1 exit /b 1

if not exist "%LIBRARY_BIN%" mkdir "%LIBRARY_BIN%"

call go build -trimpath ^
    -ldflags "-s -w -X %module%/cmd.version=%PKG_VERSION%" ^
    -o "%LIBRARY_BIN%\git-pkgs.exe" ^
    .
if errorlevel 1 exit /b 1
