@echo off
setlocal enabledelayedexpansion

if not exist "src" (
    echo ERROR: src\ directory not found in SRC_DIR: %CD%
    dir
    exit /b 1
)

set SHARE=%PREFIX%\share\bmad-method-test-architecture-enterprise
if not exist "%SHARE%" mkdir "%SHARE%"
xcopy /E /I /Q src\agents "%SHARE%\agents\"
if errorlevel 1 exit /b 1
xcopy /E /I /Q src\workflows "%SHARE%\workflows\"
if errorlevel 1 exit /b 1
copy src\module-help.csv "%SHARE%\"
if errorlevel 1 exit /b 1
copy src\module.yaml "%SHARE%\"
if errorlevel 1 exit /b 1
xcopy /E /I /Q .claude-plugin "%SHARE%\.claude-plugin\"
if errorlevel 1 exit /b 1
copy CHANGELOG.md "%SHARE%\"
if errorlevel 1 exit /b 1
copy LICENSE "%SHARE%\"
if errorlevel 1 exit /b 1
copy README.md "%SHARE%\"
if errorlevel 1 exit /b 1

rem tea-test-review Node CLI (real bin entry since upstream 1.20.0):
rem vendor cli/ + production node_modules next to it so require() resolves.
call npm install --omit=dev --ignore-scripts --no-audit --no-fund
if errorlevel 1 exit /b 1
xcopy /E /I /Q cli "%SHARE%\cli\"
if errorlevel 1 exit /b 1
xcopy /E /I /Q node_modules "%SHARE%\node_modules\"
if errorlevel 1 exit /b 1
for /f "delims=" %%d in ('dir /b /s /ad "%SHARE%\node_modules\.bin" 2^>nul') do rmdir /s /q "%%d"
if exist "%SHARE%\node_modules\.bin" rmdir /s /q "%SHARE%\node_modules\.bin"

if not exist "%PREFIX%\Scripts" mkdir "%PREFIX%\Scripts"
copy "%RECIPE_DIR%\bmad_tea_install.py" "%PREFIX%\Scripts\bmad-tea-install-script.py"
if errorlevel 1 exit /b 1
(
  echo @"%PREFIX%\python.exe" "%PREFIX%\Scripts\bmad-tea-install-script.py" %%*
) > "%PREFIX%\Scripts\bmad-tea-install.bat"
(
  echo @node "%PREFIX%\share\bmad-method-test-architecture-enterprise\cli\test-review.js" %%*
) > "%PREFIX%\Scripts\tea-test-review.bat"
