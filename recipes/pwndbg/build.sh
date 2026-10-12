#!/bin/bash
set -euxo pipefail
# Drop upstream-optional dependencies that are not packaged on conda-forge
# (ziglang, decompiler integration, uv) and relax exact pins that
# conda-forge does not carry; the gdb-pt-dump git URL becomes plain `pt`.
python - <<'PY'
import re, pathlib
p = pathlib.Path("pyproject.toml")
s = p.read_text()
drop = ("uv>=", "ziglang", "decomp2dbg", "jpype1")
lines = [l for l in s.splitlines() if not any(f'"{d}' in l for d in drop)]
s = "\n".join(lines) + "\n"
s = re.sub(r'"pt @ git\+[^"]*"', '"pt"', s)
s = s.replace('"ropgadget==7.6"', '"ropgadget>=7.6"')
s = re.sub(r'"ipython>=8.39.0,<\d+ ; python_full_version [<>=]+ \'3.1\d\'",\n', "", s)
s = s.replace('# Optional? only for \'ipi\' command\n', '# Optional? only for \'ipi\' command\n    "ipython>=8.39.0",\n')
p.write_text(s)
PY
grep -n -A30 '^dependencies' pyproject.toml | head -30
${PYTHON} -m pip install . -vv --no-deps --no-build-isolation
