#!/usr/bin/env python3
"""Fake CFE root stub -- the Docker/CI-parity build script (Story 2.6, AD-16).

Lives at the fixture root (`tests/fixtures/fake_cfe_root/build-locally.py`),
mirroring the real script's own top-level placement -- the one `_CFE_SCRIPTS`
entry outside the standard `.claude/scripts/conda-forge-expert/`
subdirectory (spec Always boundary). Sibling-imports `_stub_support` from
that standard subdirectory (one level down from here, unlike every other
fixture stub, which sits alongside it) and calls `emit(...)` for its canned
output. Invocable as `[interpreter, script, config]`; `config`
(`sys.argv[1]`) is accepted and ignored, never validated.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / ".claude" / "scripts" / "conda-forge-expert"))
import _stub_support  # noqa: E402

if __name__ == "__main__":
    sys.exit(_stub_support.emit("build-locally stub ok"))
