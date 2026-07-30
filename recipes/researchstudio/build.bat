@echo off
setlocal enabledelayedexpansion

if not exist "ResearchStudio-Idea\skills" (
    echo ERROR: ResearchStudio-Idea\skills not found in SRC_DIR: %CD%
    dir
    exit /b 1
)
if not exist "ResearchStudio-Reel\skills" (
    echo ERROR: ResearchStudio-Reel\skills not found in SRC_DIR: %CD%
    exit /b 1
)

set SHARE=%PREFIX%\share\researchstudio
if not exist "%SHARE%" mkdir "%SHARE%"

xcopy /E /I /Q ResearchStudio-Idea "%SHARE%\ResearchStudio-Idea\"
if errorlevel 1 exit /b 1
xcopy /E /I /Q ResearchStudio-Reel "%SHARE%\ResearchStudio-Reel\"
if errorlevel 1 exit /b 1
xcopy /E /I /Q docs "%SHARE%\docs\"
if errorlevel 1 exit /b 1
copy LICENSE "%SHARE%\"
if errorlevel 1 exit /b 1
copy README.md "%SHARE%\"
if errorlevel 1 exit /b 1

if not exist "%PREFIX%\Scripts" mkdir "%PREFIX%\Scripts"
copy "%RECIPE_DIR%\researchstudio_install.py" "%PREFIX%\Scripts\researchstudio-install-script.py"
if errorlevel 1 exit /b 1
(
  echo @"%PREFIX%\python.exe" "%PREFIX%\Scripts\researchstudio-install-script.py" %%*
) > "%PREFIX%\Scripts\researchstudio-install.bat"
