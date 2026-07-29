"""Make the offline orchestration gate hermetic.

Why this file exists
--------------------
``orchestration/definitions.py`` builds its Dagster ``Definitions`` at MODULE
IMPORT time (``defs = build_definitions()``) — that is Dagster's own code-location
convention, not an accident, so it cannot be made lazy. Building resolves the
full Kedro catalog, and two entries in ``conf/base/catalog.yml`` declare a
``credentials:`` key. Kedro raises ``KeyError`` when a declared credentials key
is absent, so the failure lands at pytest **COLLECTION** — before any fixture,
mark, or skip can intervene.

Those credentials live in ``conf/local/credentials.yml``, which is gitignored (it
holds real material on a developer machine). The result was a gate that passed
only where someone had already done manual setup: green on the authoring
machine, and red at collection in every fresh clone, CI runner, and bmad-loop
story worktree. Found 2026-07-28, when the loop's own ``[verify]`` gate could not
pass inside a worktree the loop itself had just created.

The fix, and why it is here rather than in ``conf/``
---------------------------------------------------
Stub credentials are a **test-harness** concern, not shipped configuration:

* ``tests/catalog/conftest.py`` already establishes this pattern — it injects
  ``STUB_CREDENTIALS`` into a purpose-built config loader, which is why
  ``kedro-catalog-check`` is already hermetic.
* Shipping stubs in ``conf/base/credentials.yml`` would also hand them to LIVE
  runs (``kedro run``, ``dagster dev``), turning a clear config-time failure into
  a confusing 401 at the HTTP layer. A real run SHOULD fail loudly when real
  credentials are missing.
* ``tests/catalog/test_credential_scoping.py`` forbids any ``*credentials*`` file
  under ``conf/`` outside ``conf/local`` — a bright line worth keeping absolute.

So we seed the gitignored ``conf/local/credentials.yml`` only when it does not
already exist. An existing file — real credentials — is never read, never
overwritten, and never logged.

pytest imports a directory's ``conftest.py`` before collecting the test modules
in that directory, so this runs early enough to unblock collection.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CATALOG = PROJECT_ROOT / "conf" / "base" / "catalog.yml"
LOCAL_CREDENTIALS = PROJECT_ROOT / "conf" / "local" / "credentials.yml"

# Matches `  credentials: bigquery_adc` — the key NAME a catalog entry demands.
# Derived from the catalog rather than hardcoded so a newly credentialed dataset
# does not silently re-break collection (the failure mode this file exists for).
_CREDENTIALS_KEY_RE = re.compile(r"^\s*credentials:\s*([A-Za-z_][A-Za-z0-9_]*)\s*$")

# Kedro's `api.APIDataset` takes credentials as a 2-element [username, password]
# basic-auth pair. Values are never exercised: the dryrun performs no network IO,
# it only needs the KEY to resolve. Deliberately self-describing so that a stub
# reaching a real endpoint is unmistakable in a log.
_STUB_PAIR = '["stub-user", "not-a-real-credential"]'


def _required_credential_keys() -> list[str]:
    if not CATALOG.is_file():
        return []
    found = {
        m.group(1)
        for line in CATALOG.read_text(encoding="utf-8").splitlines()
        if (m := _CREDENTIALS_KEY_RE.match(line))
    }
    return sorted(found)


def _seed_stub_credentials() -> None:
    """Create a stub credentials file iff none exists. Never touches a real one."""
    if LOCAL_CREDENTIALS.exists():
        return
    keys = _required_credential_keys()
    if not keys:
        return
    LOCAL_CREDENTIALS.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"{key}: {_STUB_PAIR}" for key in keys)
    LOCAL_CREDENTIALS.write_text(
        "# AUTO-GENERATED STUB — created by tests/orchestration/conftest.py because\n"
        "# no conf/local/credentials.yml was present. Offline gates only; these are\n"
        "# NOT credentials and will not authenticate anywhere.\n"
        "#\n"
        "# Replace with real values for live runs. This path is gitignored, and the\n"
        "# generator never overwrites an existing file.\n"
        f"{body}\n",
        encoding="utf-8",
    )


_seed_stub_credentials()
