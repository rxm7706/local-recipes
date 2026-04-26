@echo off
setlocal enabledelayedexpansion

if not exist "package.json" (
    echo ERROR: package.json not found in SRC_DIR: %CD%
    dir
    exit /b 1
)

:: Install production npm dependencies (no devDependencies, no scripts)
call npm install --omit=dev --no-fund --no-audit --ignore-scripts
if errorlevel 1 exit /b 1

:: Create the installation directory
set "INSTALL_DIR=%PREFIX%\lib\node_modules\%PKG_NAME%"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Copy package files (source + node_modules), excluding dev-only directories.
:: Use robocopy to avoid Windows MAX_PATH issues in website/ and docs/ trees.
robocopy . "%INSTALL_DIR%" /E ^
  /XD website docs test .husky .github .vscode .augment .claude-plugin coverage test-output ^
  /NFL /NDL /NJH /NJS /NP
:: robocopy exit codes 0-7 are success; 8+ indicate errors.
if %errorlevel% geq 8 exit /b 1

:: Create Scripts directory for wrapper .bat files
if not exist "%PREFIX%\Scripts" mkdir "%PREFIX%\Scripts"

:: Create bmad.bat wrapper
(
  echo @echo off
  echo SET "DIR=%%~dp0.."
  echo node "%%DIR%%\lib\node_modules\bmad-method\tools\installer\bmad-cli.js" %%*
) > "%PREFIX%\Scripts\bmad.bat"

:: Create bmad-method.bat wrapper
(
  echo @echo off
  echo SET "DIR=%%~dp0.."
  echo node "%%DIR%%\lib\node_modules\bmad-method\tools\installer\bmad-cli.js" %%*
) > "%PREFIX%\Scripts\bmad-method.bat"
