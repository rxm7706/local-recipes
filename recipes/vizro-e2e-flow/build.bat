@echo off
setlocal enabledelayedexpansion

if not exist "vizro-e2e-flow\skills" (
    echo ERROR: vizro-e2e-flow\skills\ not found in SRC_DIR: %CD%
    dir
    exit /b 1
)

set SHARE=%PREFIX%\share\vizro-e2e-flow
if not exist "%SHARE%" mkdir "%SHARE%"
xcopy /E /I /Q vizro-e2e-flow\skills "%SHARE%\skills\"
if errorlevel 1 exit /b 1
xcopy /E /I /Q vizro-e2e-flow\.claude-plugin "%SHARE%\.claude-plugin\"
if errorlevel 1 exit /b 1
copy vizro-e2e-flow\README.md "%SHARE%\"
if errorlevel 1 exit /b 1
copy vizro-e2e-flow\LICENSE.txt "%SHARE%\"
if errorlevel 1 exit /b 1

if not exist "%PREFIX%\Scripts" mkdir "%PREFIX%\Scripts"
copy "%RECIPE_DIR%\vizro_e2e_flow_install.py" "%PREFIX%\Scripts\vizro-e2e-flow-install-script.py"
if errorlevel 1 exit /b 1
(
  echo @"%PREFIX%\python.exe" "%PREFIX%\Scripts\vizro-e2e-flow-install-script.py" %%*
) > "%PREFIX%\Scripts\vizro-e2e-flow-install.bat"
