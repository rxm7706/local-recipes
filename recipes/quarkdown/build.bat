@echo off
setlocal enabledelayedexpansion

if exist "quarkdown\bin" (
    set APP_ROOT=quarkdown
) else if exist "bin" (
    set APP_ROOT=.
) else (
    echo ERROR: quarkdown app image not found in SRC_DIR: %CD%
    dir
    exit /b 1
)

set OPT=%PREFIX%\opt\quarkdown
if not exist "%OPT%" mkdir "%OPT%"
xcopy /E /I /Q "%APP_ROOT%\bin" "%OPT%\bin\"
if errorlevel 1 exit /b 1
xcopy /E /I /Q "%APP_ROOT%\lib" "%OPT%\lib\"
if errorlevel 1 exit /b 1
xcopy /E /I /Q "%APP_ROOT%\runtime" "%OPT%\runtime\"
if errorlevel 1 exit /b 1
if exist "%APP_ROOT%\docs" xcopy /E /I /Q "%APP_ROOT%\docs" "%OPT%\docs\"

if not exist "%PREFIX%\Scripts" mkdir "%PREFIX%\Scripts"
(
  echo @call "%PREFIX%\opt\quarkdown\bin\quarkdown.bat" %%*
) > "%PREFIX%\Scripts\quarkdown.bat"
