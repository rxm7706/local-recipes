@echo off
setlocal enabledelayedexpansion

if not exist "skills" (
    echo ERROR: skills\ directory not found in SRC_DIR: %CD%
    dir
    exit /b 1
)

set SHARE=%PREFIX%\share\andrej-karpathy-skills
if not exist "%SHARE%" mkdir "%SHARE%"
xcopy /E /I /Q skills "%SHARE%\skills\"
if errorlevel 1 exit /b 1
xcopy /E /I /Q .claude-plugin "%SHARE%\.claude-plugin\"
if errorlevel 1 exit /b 1
copy CLAUDE.md "%SHARE%\"
if errorlevel 1 exit /b 1
copy CURSOR.md "%SHARE%\"
if errorlevel 1 exit /b 1
copy EXAMPLES.md "%SHARE%\"
if errorlevel 1 exit /b 1
copy README.md "%SHARE%\"
if errorlevel 1 exit /b 1
copy "%RECIPE_DIR%\LICENSE" "%SHARE%\"
if errorlevel 1 exit /b 1

if not exist "%PREFIX%\Scripts" mkdir "%PREFIX%\Scripts"
copy "%RECIPE_DIR%\andrej_karpathy_skills_install.py" "%PREFIX%\Scripts\andrej-karpathy-skills-install-script.py"
if errorlevel 1 exit /b 1
(
  echo @"%PREFIX%\python.exe" "%PREFIX%\Scripts\andrej-karpathy-skills-install-script.py" %%*
) > "%PREFIX%\Scripts\andrej-karpathy-skills-install.bat"
