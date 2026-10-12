#!/bin/bash
set -euo pipefail
req='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"conda-test","version":"0"}}}'
out=$( (echo "$req"; sleep 5) | timeout 30 rea mcp 2>/dev/null | head -n1 || true)
echo "$out"
echo "$out" | grep -q '"serverInfo"'
