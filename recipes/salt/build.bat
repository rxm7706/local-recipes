%PYTHON% -m pip install . -vv --no-build-isolation
if errorlevel 1 exit 1

for %%D in (
       etc\salt
       var\cache\salt
       var\run\salt
       srv\salt
       srv\pillar
       var\log\salt
       var\run
) do (
       if not exist %PREFIX%\"%%D" mkdir %PREFIX%\"%%D"
)
