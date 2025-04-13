%PYTHON% -m pip install . -vv --no-build-isolation --no-deps
if errorlevel 1 exit 1

cd %SCRIPTS%
del *.exe
del *.exe.manifest
del pip2*
del pip3*
:: del %SP_DIR%\__pycache__\pkg_res*
