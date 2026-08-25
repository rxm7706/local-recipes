@echo off
REM Conda wrapper: official launcher expects LIQUIBASE_HOME = distro root.
set "LIQUIBASE_HOME=%CONDA_PREFIX%\share\liquibase"
if not exist "%LIQUIBASE_HOME%\liquibase.bat" (
  echo Error: Liquibase launcher not found at %LIQUIBASE_HOME%\liquibase.bat 1>&2
  exit /b 1
)
call "%LIQUIBASE_HOME%\liquibase.bat" %*
