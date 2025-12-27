@echo on

REM Step 1: Install WebAssembly build dependencies
echo Installing WebAssembly build dependencies...
rustup target add wasm32-wasip1
cargo install --locked wasm-tools || cargo install wasm-tools || echo wasm-tools may already be installed

REM Step 2: Build WebAssembly bindgen library
echo Building WebAssembly bindgen...
cargo build --target wasm32-wasip1 --release -p bindgen
if %ERRORLEVEL% neq 0 exit 1

REM Step 3: Ensure wasm-tools is in PATH
set "PATH=%USERPROFILE%\.cargo\bin;%BUILD_PREFIX%\Library\bin\cargo\bin;%PATH%"

REM Step 4: Create WebAssembly component
echo Creating WASM component...
wasm-tools component new .\rust\target\wasm32-wasip1\release\bindgen.wasm -o target\component.wasm --adapt wasi_snapshot_preview1=adapters\wasi_snapshot_preview1.wasm
if %ERRORLEVEL% neq 0 exit 1

REM Step 5: Generate native bindings from the component
echo Generating native bindings...
cargo run -p=bindgen --features=cli .\target\component.wasm
if %ERRORLEVEL% neq 0 exit 1

REM Step 6: Install Python package with production flag
echo Installing Python package...
set PROD=1
%PYTHON% -m pip install . -vv --no-deps --no-build-isolation
if %ERRORLEVEL% neq 0 exit 1
