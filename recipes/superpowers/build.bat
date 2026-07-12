@echo off
setlocal enabledelayedexpansion

if not exist "skills" (
    echo ERROR: skills\ directory not found in SRC_DIR: %CD%
    dir
    exit /b 1
)

set SHARE=%PREFIX%\share\superpowers
if not exist "%SHARE%" mkdir "%SHARE%"
xcopy /E /I /Q skills "%SHARE%\skills\"
if errorlevel 1 exit /b 1
xcopy /E /I /Q hooks "%SHARE%\hooks\"
if errorlevel 1 exit /b 1
xcopy /E /I /Q .claude-plugin "%SHARE%\.claude-plugin\"
if errorlevel 1 exit /b 1
xcopy /E /I /Q docs "%SHARE%\docs\"
if errorlevel 1 exit /b 1
copy CLAUDE.md "%SHARE%\"
if errorlevel 1 exit /b 1
copy AGENTS.md "%SHARE%\"
if errorlevel 1 exit /b 1
copy README.md "%SHARE%\"
if errorlevel 1 exit /b 1
copy LICENSE "%SHARE%\"
if errorlevel 1 exit /b 1

if not exist "%PREFIX%\Scripts" mkdir "%PREFIX%\Scripts"
copy "%RECIPE_DIR%\superpowers_install.py" "%PREFIX%\Scripts\superpowers-install-script.py"
if errorlevel 1 exit /b 1
(
  echo @"%PREFIX%\python.exe" "%PREFIX%\Scripts\superpowers-install-script.py" %%*
) > "%PREFIX%\Scripts\superpowers-install.bat"
