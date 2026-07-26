@echo off
setlocal enabledelayedexpansion

if not exist "skills" (
    echo ERROR: skills\ directory not found in SRC_DIR: %CD%
    dir
    exit /b 1
)

set SHARE=%PREFIX%\share\bmad-manticore
if not exist "%SHARE%" mkdir "%SHARE%"
xcopy /E /I /Q skills "%SHARE%\skills\"
if errorlevel 1 exit /b 1
xcopy /E /I /Q .claude-plugin "%SHARE%\.claude-plugin\"
if errorlevel 1 exit /b 1
copy README.md "%SHARE%\"
if errorlevel 1 exit /b 1
copy LICENSE "%SHARE%\"
if errorlevel 1 exit /b 1

rem Text user guide only; docs\assets is ~11 MB of marketing media.
if not exist "%SHARE%\docs" mkdir "%SHARE%\docs"
copy docs\user-guide.md "%SHARE%\docs\"
if errorlevel 1 exit /b 1

if not exist "%PREFIX%\Scripts" mkdir "%PREFIX%\Scripts"
copy "%RECIPE_DIR%\bmad_manticore_install.py" "%PREFIX%\Scripts\bmad-manticore-install-script.py"
if errorlevel 1 exit /b 1
(
  echo @"%PREFIX%\python.exe" "%PREFIX%\Scripts\bmad-manticore-install-script.py" %%*
) > "%PREFIX%\Scripts\bmad-manticore-install.bat"
