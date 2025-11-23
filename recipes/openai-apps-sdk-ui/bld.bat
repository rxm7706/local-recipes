mkdir "%PREFIX%\lib\node_modules\@openai\apps-sdk-ui"
if errorlevel 1 exit 1

xcopy /E /I /Y . "%PREFIX%\lib\node_modules\@openai\apps-sdk-ui\"
if errorlevel 1 exit 1
