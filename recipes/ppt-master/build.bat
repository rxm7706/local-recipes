@echo off
setlocal enabledelayedexpansion

if not exist "skills\ppt-master" (
    echo ERROR: skills\ppt-master\ directory not found in SRC_DIR: %CD%
    dir
    exit /b 1
)

set SHARE=%PREFIX%\share\ppt-master
if not exist "%SHARE%\skills" mkdir "%SHARE%\skills"
xcopy /E /I /Q skills\ppt-master "%SHARE%\skills\ppt-master\"
if errorlevel 1 exit /b 1
copy LICENSE "%SHARE%\"
if errorlevel 1 exit /b 1
copy README.md "%SHARE%\"
if errorlevel 1 exit /b 1

set SKILL=%SHARE%\skills\ppt-master

rem Drop the legacy halves of the AI image reference gallery (~20 MB of 44 MB).
rem Upstream's references/ai-image-comparison/README.md says the Confirm UI
rem "displays rendering only"; palette/ is "legacy diagnostic material ... not a
rem runtime catalog" and type/ is an internal reference. rendering/ is KEPT --
rem scripts/confirm_ui/server.py actively serves it.
if exist "%SKILL%\references\ai-image-comparison\palette" rd /s /q "%SKILL%\references\ai-image-comparison\palette"
if exist "%SKILL%\references\ai-image-comparison\type" rd /s /q "%SKILL%\references\ai-image-comparison\type"

rem --- ASCII-normalize the brand/deck kit paths ------------------------------
rem Upstream names three brand kits and two deck kits in Chinese and ships six
rem logo files whose names are non-ASCII and/or contain spaces (34 conda path
rem warnings). Rename them and rewrite every internal reference. Uses sed
rem (m2-sed on Windows) rather than Python: an unpinned `python` build dep
rem makes rattler-build split this noarch:generic package into py3XX variants.
for %%b in (brands decks) do (
    set "D=%SKILL%\templates\%%b"
    if exist "!D!\中国电信" move /Y "!D!\中国电信" "!D!\china-telecom" >nul
    if exist "!D!\中国电建" move /Y "!D!\中国电建" "!D!\powerchina" >nul
    if exist "!D!\中汽研" move /Y "!D!\中汽研" "!D!\catarc" >nul
)

for %%b in (brands decks) do (
    set "P=%SKILL%\templates\%%b\powerchina\images"
    if exist "!P!\电建logo.png" move /Y "!P!\电建logo.png" "!P!\powerchina-logo.png" >nul
    if exist "!P!\华东院logo.png" move /Y "!P!\华东院logo.png" "!P!\east-china-institute-logo.png" >nul
    if exist "!P!\中国水务logo.png" move /Y "!P!\中国水务logo.png" "!P!\china-water-logo.png" >nul
    if exist "!P!\水电三局logo.png" move /Y "!P!\水电三局logo.png" "!P!\sinohydro-bureau3-logo.png" >nul
    set "C=%SKILL%\templates\%%b\catarc\images"
    if exist "!C!\大型 logo.png" move /Y "!C!\大型 logo.png" "!C!\large-logo.png" >nul
    if exist "!C!\右上角 logo.png" move /Y "!C!\右上角 logo.png" "!C!\header-logo.png" >nul
)

rem Whole tree, not just templates\: scripts\prompt_audit_manifest.json
rem references the brand design_spec.md files by path.
rem *.py included for one stale --help usage string in svg_quality_checker.py.
for /r "%SKILL%" %%f in (*.md *.svg *.json *.py) do (
    sed -i.bak -f "%RECIPE_DIR%\normalize_paths.sed" "%%f"
    if errorlevel 1 exit /b 1
)
del /s /q "%SKILL%\*.bak" >nul 2>&1

if not exist "%PREFIX%\Scripts" mkdir "%PREFIX%\Scripts"
copy "%RECIPE_DIR%\ppt_master_install.py" "%PREFIX%\Scripts\ppt-master-install-script.py"
if errorlevel 1 exit /b 1
(
  echo @"%PREFIX%\python.exe" "%PREFIX%\Scripts\ppt-master-install-script.py" %%*
) > "%PREFIX%\Scripts\ppt-master-install.bat"
