@echo off
setlocal enabledelayedexpansion

if not exist "dist" (
    echo ERROR: dist\ directory not found in SRC_DIR: %CD%
    dir
    exit /b 1
)

set SHARE=%PREFIX%\share\aidlc-workflows
if not exist "%SHARE%" mkdir "%SHARE%"
xcopy /E /I /Q dist "%SHARE%\dist\"
if errorlevel 1 exit /b 1
xcopy /E /I /Q core "%SHARE%\core\"
if errorlevel 1 exit /b 1
xcopy /E /I /Q harness "%SHARE%\harness\"
if errorlevel 1 exit /b 1
xcopy /E /I /Q plugins "%SHARE%\plugins\"
if errorlevel 1 exit /b 1
xcopy /E /I /Q docs "%SHARE%\docs\"
if errorlevel 1 exit /b 1
copy README.md "%SHARE%\"
if errorlevel 1 exit /b 1
copy LICENSE "%SHARE%\"
if errorlevel 1 exit /b 1
copy CHANGELOG.md "%SHARE%\"
if errorlevel 1 exit /b 1

if not exist "%PREFIX%\Scripts" mkdir "%PREFIX%\Scripts"
copy "%RECIPE_DIR%\aidlc_workflows_install.py" "%PREFIX%\Scripts\aidlc-workflows-install-script.py"
if errorlevel 1 exit /b 1
(
  echo @"%PREFIX%\python.exe" "%PREFIX%\Scripts\aidlc-workflows-install-script.py" %%*
) > "%PREFIX%\Scripts\aidlc-workflows-install.bat"
