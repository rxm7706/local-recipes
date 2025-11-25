@echo on

:: Set npm prefix to install globally into the conda environment
call npm config set prefix "%PREFIX%"
if errorlevel 1 exit 1

:: Pack the source
call npm pack
if errorlevel 1 exit 1

:: Install globally with dependencies
:: npm pack creates pimzino-spec-workflow-mcp-VERSION.tgz for scoped packages
call npm install --userconfig nonexistentrc -g pimzino-%PKG_NAME%-%PKG_VERSION%.tgz
if errorlevel 1 exit 1
