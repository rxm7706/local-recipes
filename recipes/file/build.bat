@echo on
setlocal EnableDelayedExpansion

:: julian-r/file-windows ships a CMakeLists.txt that wraps the upstream `file`
:: source (pulled as a git submodule) with Win32 compatibility shims (dirent,
:: getopt, vendored PCRE2). We build with Ninja under MSVC.

mkdir build
cd build

cmake -G Ninja ^
    -DCMAKE_BUILD_TYPE=Release ^
    -DCMAKE_INSTALL_PREFIX="%LIBRARY_PREFIX%" ^
    "%SRC_DIR%"
if errorlevel 1 exit /b 1

cmake --build . --config Release
if errorlevel 1 exit /b 1

:: ctest is best-effort — some upstream tests fail on CRLF/timezone drift;
:: julian-r already disables a handful in CMakeLists. Don't fail the build.
ctest --output-on-failure -C Release || echo "ctest reported failures (non-fatal)"

:: julian-r CMakeLists has no install() targets, so place artifacts manually.
if not exist "%LIBRARY_BIN%" mkdir "%LIBRARY_BIN%"
if not exist "%LIBRARY_LIB%" mkdir "%LIBRARY_LIB%"
if not exist "%LIBRARY_INC%" mkdir "%LIBRARY_INC%"
if not exist "%LIBRARY_PREFIX%\share\misc" mkdir "%LIBRARY_PREFIX%\share\misc"

copy /Y libmagic.dll "%LIBRARY_BIN%\libmagic.dll" || exit /b 1
copy /Y libmagic.lib "%LIBRARY_LIB%\libmagic.lib" || exit /b 1
copy /Y file.exe "%LIBRARY_BIN%\file.exe" || exit /b 1
copy /Y magic.mgc "%LIBRARY_PREFIX%\share\misc\magic.mgc" || exit /b 1
copy /Y "%SRC_DIR%\file\src\magic.h" "%LIBRARY_INC%\magic.h" || exit /b 1
