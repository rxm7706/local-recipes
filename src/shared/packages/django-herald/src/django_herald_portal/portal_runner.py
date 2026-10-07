"""In-process ``PortalClient.invoke`` runner for ``herald deck exports --json``."""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from typing import Any

InvokeRunner = Callable[..., dict[str, Any]]


def deck_exports_json_runner(*, station: str, argv: list[str], token: str, **_: Any) -> dict[str, Any]:
    """Shell ``pyforge herald deck exports … --json`` when the CLI is on PATH."""
    del station, token
    if len(argv) < 3 or argv[:2] != ["deck", "exports"]:
        msg = f"unexpected argv for deck exports: {argv!r}"
        raise ValueError(msg)
    pyforge = shutil.which("pyforge")
    cmd = [pyforge, "herald", *argv] if pyforge else ["herald", *argv]
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        msg = f"{' '.join(cmd)!r} exited {completed.returncode}: {completed.stderr.strip()}"
        raise RuntimeError(msg)
    # Validate JSON early so refresh fails loudly on bad output.
    json.loads(completed.stdout)
    return {"stdout": completed.stdout}
