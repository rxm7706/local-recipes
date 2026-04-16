#!/bin/bash
# Build script for presenton (Unix / macOS)
# This is a multi-component application:
#   - Python FastAPI backend  (servers/fastapi/)
#   - Next.js 14 frontend     (servers/nextjs/)
# Both are installed under $PREFIX/share/presenton/, with launcher scripts in $PREFIX/bin/.
set -euo pipefail

PRESENTON_SHARE="$PREFIX/share/presenton"
BACKEND_DST="$PRESENTON_SHARE/backend"
NEXTJS_DST="$PRESENTON_SHARE/nextjs"

# ---------------------------------------------------------------------------
# Step 1: Build Next.js frontend
# ---------------------------------------------------------------------------
echo "==> Building Next.js frontend..."
cd "$SRC_DIR/servers/nextjs"

# Patch next.config.mjs to enable standalone output mode so the built bundle
# is a self-contained Node server (no node_modules needed at runtime).
python3 - <<'PYEOF'
import re, sys

path = "next.config.mjs"
content = open(path).read()

if "output:" in content:
    print("next.config.mjs: 'output' already set, leaving as-is")
    sys.exit(0)

# Insert `output: "standalone",` right after the opening brace of nextConfig
content = re.sub(
    r'(const nextConfig\s*=\s*\{)',
    r'\1\n  output: "standalone",',
    content,
    count=1,
)
open(path, "w").write(content)
print("next.config.mjs: patched to add output: 'standalone'")
PYEOF

# Install npm dependencies (requires network access — this is a local build only)
npm ci

# Build — produces .next-build/ with a standalone/ subdirectory
npm run build

cd "$SRC_DIR"

# ---------------------------------------------------------------------------
# Step 2: Create installation directories
# ---------------------------------------------------------------------------
echo "==> Creating installation directories..."
mkdir -p "$BACKEND_DST"
mkdir -p "$NEXTJS_DST"

# ---------------------------------------------------------------------------
# Step 3: Copy Python backend
# ---------------------------------------------------------------------------
# The pyproject.toml has no [build-system], so we cannot pip-install this as
# a wheel.  The app is designed to be run from its source directory, so we
# copy the source tree and launch via PYTHONPATH.
echo "==> Copying Python backend..."
FASTAPI_SRC="$SRC_DIR/servers/fastapi"

# Core application packages (from [tool.setuptools.packages.find])
for pkg in api enums models services constants utils; do
    if [ -d "$FASTAPI_SRC/$pkg" ]; then
        cp -r "$FASTAPI_SRC/$pkg" "$BACKEND_DST/"
    fi
done

# Entry-point and supporting scripts
cp "$FASTAPI_SRC/server.py" "$BACKEND_DST/"
for f in mcp_server.py migrations.py alembic.ini openai_spec.json; do
    [ -f "$FASTAPI_SRC/$f" ] && cp "$FASTAPI_SRC/$f" "$BACKEND_DST/" || true
done
[ -d "$FASTAPI_SRC/alembic" ] && cp -r "$FASTAPI_SRC/alembic" "$BACKEND_DST/" || true

# ---------------------------------------------------------------------------
# Step 4: Copy Next.js frontend (standalone bundle)
# ---------------------------------------------------------------------------
echo "==> Copying Next.js frontend..."
NEXT_BUILD="$SRC_DIR/servers/nextjs/.next-build"
NEXTJS_SRC="$SRC_DIR/servers/nextjs"

if [ -d "$NEXT_BUILD/standalone" ]; then
    # Standalone mode: copy the self-contained server bundle
    cp -r "$NEXT_BUILD/standalone" "$NEXTJS_DST/"
    # The standalone server needs static assets to be placed alongside it
    mkdir -p "$NEXTJS_DST/standalone/.next-build/static"
    cp -r "$NEXT_BUILD/static" "$NEXTJS_DST/standalone/.next-build/"
    [ -d "$NEXTJS_SRC/public" ] && cp -r "$NEXTJS_SRC/public" "$NEXTJS_DST/standalone/" || true
else
    # Fallback: full build output + node_modules (large; only reached if the
    # standalone patch above was not applied / failed)
    echo "WARNING: standalone output not found; copying full build + node_modules"
    cp -r "$NEXT_BUILD" "$NEXTJS_DST/"
    cp -r "$NEXTJS_SRC/node_modules" "$NEXTJS_DST/"
    [ -d "$NEXTJS_SRC/public" ] && cp -r "$NEXTJS_SRC/public" "$NEXTJS_DST/" || true
    cp "$NEXTJS_SRC/package.json" "$NEXTJS_DST/"
fi

# ---------------------------------------------------------------------------
# Step 5: Create launcher scripts
# ---------------------------------------------------------------------------
echo "==> Creating launcher scripts..."
mkdir -p "$PREFIX/bin"

# -- presenton-backend --------------------------------------------------------
cat > "$PREFIX/bin/presenton-backend" << 'SCRIPT'
#!/bin/bash
# Presenton FastAPI backend launcher
# Usage: presenton-backend [extra uvicorn args]
PRESENTON_SHARE="${CONDA_PREFIX:-${PREFIX}}/share/presenton"
export PYTHONPATH="${PRESENTON_SHARE}/backend${PYTHONPATH:+:${PYTHONPATH}}"
cd "${PRESENTON_SHARE}/backend"
exec python server.py --port "${PRESENTON_PORT:-8000}" "$@"
SCRIPT
chmod +x "$PREFIX/bin/presenton-backend"

# -- presenton-frontend -------------------------------------------------------
cat > "$PREFIX/bin/presenton-frontend" << 'SCRIPT'
#!/bin/bash
# Presenton Next.js frontend launcher
# Usage: presenton-frontend
PRESENTON_SHARE="${CONDA_PREFIX:-${PREFIX}}/share/presenton"
STANDALONE="${PRESENTON_SHARE}/nextjs/standalone"

if [ -d "${STANDALONE}" ]; then
    cd "${STANDALONE}"
    HOSTNAME=0.0.0.0 PORT="${PRESENTON_FRONTEND_PORT:-3000}" \
        exec node server.js
else
    # Fallback: use `next start` (requires node_modules)
    cd "${PRESENTON_SHARE}/nextjs"
    PORT="${PRESENTON_FRONTEND_PORT:-3000}" exec npx next start
fi
SCRIPT
chmod +x "$PREFIX/bin/presenton-frontend"

# -- presenton (combined) -----------------------------------------------------
cat > "$PREFIX/bin/presenton" << 'SCRIPT'
#!/bin/bash
# Presenton — start both backend and frontend
BACKEND_PORT="${PRESENTON_PORT:-8000}"
FRONTEND_PORT="${PRESENTON_FRONTEND_PORT:-3000}"

echo "Starting Presenton..."
echo "  API backend:  http://localhost:${BACKEND_PORT}"
echo "  UI frontend:  http://localhost:${FRONTEND_PORT}"
echo "Press Ctrl+C to stop all servers."
echo ""

presenton-backend &
BACKEND_PID=$!

# Brief pause so the backend can initialize before the frontend connects
sleep 2

presenton-frontend &
FRONTEND_PID=$!

trap 'echo "Stopping..."; kill ${BACKEND_PID} ${FRONTEND_PID} 2>/dev/null; wait; exit 0' INT TERM

wait ${BACKEND_PID} ${FRONTEND_PID}
SCRIPT
chmod +x "$PREFIX/bin/presenton"

echo "==> presenton installation complete."
echo "    Run 'presenton' to start both servers, or 'presenton --help' for options."
