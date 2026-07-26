@echo off
setlocal enabledelayedexpansion

if not exist "bin\devin.exe" (
    echo ERROR: bin\devin.exe not found in SRC_DIR: %CD%
    dir
    exit /b 1
)

if not exist "%LIBRARY_BIN%" mkdir "%LIBRARY_BIN%"
copy /Y "bin\devin.exe" "%LIBRARY_BIN%\devin.exe"
if errorlevel 1 exit /b 1

if exist "share\devin" (
    if not exist "%PREFIX%\share" mkdir "%PREFIX%\share"
    xcopy /E /I /Q "share\devin" "%PREFIX%\share\devin\"
    if errorlevel 1 exit /b 1
)

copy /Y "%RECIPE_DIR%\LICENSE.txt" "%SRC_DIR%\LICENSE.txt"
if errorlevel 1 exit /b 1
