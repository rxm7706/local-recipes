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
   values (`{}`) for every credential key the catalog references
   (`CREDENTIAL_KEYS` below; the per-entry map is
   `tests/unit/catalog/conftest.py`'s `CREDENTIAL_ALLOWLIST`), but ONLY when
   the file is absent or empty.
   Kedro's `DataCatalog.from_config` resolves EVERY entry's `credentials:`
   key eagerly, for the whole catalog, regardless of which `--pipeline` is
   selected -- an entirely absent `conf/local/credentials.yml` makes ANY
   `kedro run` fail immediately with `KeyError: Unable to find credentials
   '...'`, before a single node runs (verified empirically against this
   catalog, 2026-08-29). Every dataset that references these keys degrades
   to an offline no-op or an anonymous call by DEFAULT (`GitHubRequestDataset`'s
   refresh-trigger node hands it an empty repo-identifier batch by default,
   Story 21.2 -- `save()` short-circuits to zero network calls before the
   credential is ever touched; `PyPIBigQueryDownloadsDataset.load()` returns
   an empty frame unless `PHASE_P_ENABLED=1`; the GitLab/Codeberg and registry
   tokens are optional, anonymous when unset, Story 27.2) -- none reads the
   credential VALUE on that default path, so a genuinely empty stub satisfies the
   catalog-construction gate without fabricating a fake-looking token. A
   real operator's own `conf/local/credentials.yml` (with real tokens) is
   NEVER overwritten -- this step is a no-op the moment a non-empty file
   exists.

`--credentials-only` runs step 2 alone (no store directories, no data root).
`.github/workflows/kedro-viz-publish.yml` runs it before `kedro viz build`, so
the workflow and this task write their stub from the one list, `CREDENTIAL_KEYS`
(atlas Story 32.1: the workflow's own two-key list had drifted from the
catalog's eight and failed run 39002722593). `tests/unit/test_viz_publish_build.py`
fails when that list and the catalog's `credentials:` keys differ.

Never touches the network. Never imports `dagster`/`kedro_mcp`. This is an
operator convenience script (`tools/`), not dataset code -- it is exempt
from `tests/catalog/test_no_inline_io.py`'s package-only IO_DENYLIST scan,
the same way `normalize_viz_build.py` is.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_MEMBER_ROOT = Path(__file__).resolve().parent.parent
_STORE_DIRS = ("vdb", "osv")
# The one list of the credential keys conf/base/catalog.yml names (atlas Story 32.1). Every key is
# written `{}`: measured 2026-10-17 against kedro-viz 12.5.0 and this catalog, an all-`{}` stub lets
# `kedro viz build` resolve the whole catalog, as it already did for `kedro run`.
CREDENTIAL_KEYS = (
    "github_token",
    "bigquery_adc",
    "gitlab_token",
    "codeberg_token",
    "npm_token",
    "crates_token",
    "rubygems_token",
    "nuget_token",
)
_CREDENTIALS_HEADER = """\
# Auto-created by tools/bootstrap.py (the `pyforge-atlas-bootstrap` pixi task,
# Story 21.1, or `--credentials-only`, which kedro-viz-publish.yml runs, Story
# 32.1) because this file was absent or empty -- EMPTY placeholders so Kedro's
# catalog construction (which resolves every entry's `credentials:` key eagerly,
# for the WHOLE catalog, regardless of --pipeline) does not KeyError on a fresh
# clone. Every referencing dataset degrades to an offline no-op or an anonymous
# call by default and never reads these values unless you wire real repo
# identifiers (Story 21.6) / opt into PHASE_P_ENABLED=1 / want an authenticated
# GitLab, Codeberg or registry call (Story 27.2) -- fill in real values only if
# you need that path.
"""
_CREDENTIALS_STUB = _CREDENTIALS_HEADER + "".join(f"{key}: {{}}\n" for key in CREDENTIAL_KEYS)


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


_FETCHER_LESS_DISCOVERY_STORES = (
    "discovery_basilisk_packages_raw",
    "discovery_aoss_premium_python_raw",
    "discovery_anaconda_dist_2026x_raw",
)


def _report_stub(stub_path: Path | None) -> None:
    if stub_path is not None:
        print(
            f"pyforge-atlas-bootstrap: wrote an empty credentials stub at {stub_path} "
            f"({', '.join(CREDENTIAL_KEYS)}) -- credentialed-only steps will skip with "
            "AD-13 last-good/empty degrade; populate this file with real values for "
            "a live attended run"
        )
    else:
        print("pyforge-atlas-bootstrap: conf/local/credentials.yml already present, left untouched")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fresh-clone Kedro bootstrap prep for pyforge-atlas.")
    parser.add_argument(
        "--credentials-only",
        action="store_true",
        help="write only the conf/local/credentials.yml stub (when the file is absent or empty); no store directories",
    )
    args = parser.parse_args([] if argv is None else argv)

    if args.credentials_only:
        _report_stub(_ensure_credentials_stub())
        return 0

    data_root = _resolve_data_root()
    created_dirs = _ensure_store_dirs(data_root)
    stub_path = _ensure_credentials_stub()

    print(f"pyforge-atlas-bootstrap: data root = {data_root}")
    print(
        "pyforge-atlas-bootstrap: fetcher-less discovery stores (expected stale on "
        "unattended bootstrap — no live refresher wired): " + ", ".join(_FETCHER_LESS_DISCOVERY_STORES)
    )
    if created_dirs:
        print("pyforge-atlas-bootstrap: created " + ", ".join(str(p) for p in created_dirs))
    else:
        print("pyforge-atlas-bootstrap: stores/{vdb,osv} already present")
    _report_stub(stub_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
