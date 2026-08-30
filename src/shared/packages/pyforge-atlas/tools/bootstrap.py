#!/usr/bin/env python3
"""Fresh-clone Kedro bootstrap prep for pyforge-atlas (Story 21.1, CAP-1).

Two small, idempotent steps the `pyforge-atlas-bootstrap` pixi task runs
BEFORE the pipeline chain, so a machine with an EMPTY
`PYFORGE_ATLAS_DATA_ROOT` and no `CF_ATLAS_DB` can complete the chain with
exit 0 (the spec's "Bootstrap smoke" row):

1. Create the two § 3.4 external-refresh STORE directories
   (`${data_root}/stores/vdb`, `${data_root}/stores/osv`) up front. The
   `vulnerability` pipeline's own refresh-trigger nodes would eventually
   create them anyway -- every write in this codebase routes through
   `pyforge.core.atomic_write.atomic_write`, which already
   `mkdir(parents=True, exist_ok=True)`s the parent -- but the spec calls
   this out as an explicit, independently-verifiable bootstrap step rather
   than an implicit side effect of node execution order.

2. Seed a MINIMAL `conf/local/credentials.yml` stub with EMPTY placeholder
   values for the two credential keys the catalog references
   (`github_token` on `vcs_github_api_raw`, `bigquery_adc` on
   `pypi_bigquery_downloads_raw` -- see `tests/catalog/conftest.py`'s
   `CREDENTIAL_ALLOWLIST`), but ONLY when the file is absent or empty.
   Kedro's `DataCatalog.from_config` resolves EVERY entry's `credentials:`
   key eagerly, for the whole catalog, regardless of which `--pipeline` is
   selected -- an entirely absent `conf/local/credentials.yml` makes ANY
   `kedro run` fail immediately with `KeyError: Unable to find credentials
   '...'`, before a single node runs (verified empirically against this
   catalog, 2026-08-29). Both datasets that reference these keys already
   degrade to an offline no-op by DEFAULT (`GitHubRequestDataset`'s
   refresh-trigger node hands it an empty repo-identifier batch by default,
   Story 21.2 -- `save()` short-circuits to zero network calls before the
   credential is ever touched; `PyPIBigQueryDownloadsDataset.load()` returns
   an empty frame unless `PHASE_P_ENABLED=1`) -- neither reads the
   credential VALUE on that default path, so a genuinely empty stub satisfies the
   catalog-construction gate without fabricating a fake-looking token. A
   real operator's own `conf/local/credentials.yml` (with real tokens) is
   NEVER overwritten -- this step is a no-op the moment a non-empty file
   exists.

Never touches the network. Never imports `dagster`/`kedro_mcp`. This is an
operator convenience script (`tools/`), not dataset code -- it is exempt
from `tests/catalog/test_no_inline_io.py`'s package-only IO_DENYLIST scan,
the same way `normalize_viz_build.py` is.
"""

from __future__ import annotations

import os
from pathlib import Path

_MEMBER_ROOT = Path(__file__).resolve().parent.parent
_STORE_DIRS = ("vdb", "osv")
_CREDENTIALS_STUB = """\
# Auto-created by the `pyforge-atlas-bootstrap` pixi task (tools/bootstrap.py,
# Story 21.1) because this file was absent or empty -- EMPTY placeholders so
# Kedro's catalog construction (which resolves every entry's `credentials:` key
# eagerly, for the WHOLE catalog, regardless of --pipeline) does not KeyError on
# a fresh clone. Both referencing datasets degrade to an offline no-op by
# default and never read these values unless you wire real repo identifiers
# (Story 21.6) / opt into PHASE_P_ENABLED=1 -- fill in real values only if you
# need that path.
github_token: {}
bigquery_adc: {}
"""


def _resolve_data_root() -> Path:
    """Mirror `globals.yml`'s `paths.data_root` resolution: env override
    else the literal default `data`, relative to the member root (the
    pixi task's own `cwd`, matching Kedro's own project-root requirement)."""
    raw = os.environ.get("PYFORGE_ATLAS_DATA_ROOT") or "data"
    root = Path(raw)
    return root if root.is_absolute() else (_MEMBER_ROOT / root)


def _ensure_store_dirs(data_root: Path) -> list[Path]:
    created = []
    for name in _STORE_DIRS:
        path = data_root / "stores" / name
        if not path.is_dir():
            path.mkdir(parents=True, exist_ok=True)
            created.append(path)
    return created


def _ensure_credentials_stub() -> Path | None:
    creds_path = _MEMBER_ROOT / "conf" / "local" / "credentials.yml"
    if creds_path.is_file() and creds_path.stat().st_size > 0:
        return None
    creds_path.parent.mkdir(parents=True, exist_ok=True)
    creds_path.write_text(_CREDENTIALS_STUB, encoding="utf-8")
    return creds_path


def main() -> int:
    data_root = _resolve_data_root()
    created_dirs = _ensure_store_dirs(data_root)
    stub_path = _ensure_credentials_stub()

    print(f"pyforge-atlas-bootstrap: data root = {data_root}")
    if created_dirs:
        print("pyforge-atlas-bootstrap: created " + ", ".join(str(p) for p in created_dirs))
    else:
        print("pyforge-atlas-bootstrap: stores/{vdb,osv} already present")
    if stub_path is not None:
        print(
            f"pyforge-atlas-bootstrap: wrote an empty credentials stub at {stub_path} "
            "(github_token/bigquery_adc) -- credentialed-only steps will skip with "
            "AD-13 last-good/empty degrade; populate this file with real values for "
            "a live attended run"
        )
    else:
        print("pyforge-atlas-bootstrap: conf/local/credentials.yml already present, left untouched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
