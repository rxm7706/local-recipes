#!/usr/bin/env python3
"""Build the self-contained, backend-free DuckDB-WASM read-surface artifact (Story G1, FR-14).

This is the BUILD step — it MAY use the network (npm + the DuckDB extension host).
The runtime it produces (``build/``) is fully OFFLINE: the ``wasm-smoke`` gate serves
``build/`` over a loopback static host and never touches an external network.

What it does (all output under ``build/``, which is gitignored):

  1. ``npm install`` the pinned build deps (``@duckdb/duckdb-wasm`` + ``esbuild``).
  2. esbuild-bundle ``entry.mjs`` → ``build/duckdb/duckdb-bundle.mjs`` (inlines
     apache-arrow so the page needs no import-map / no CDN / no bare specifiers).
  3. Copy the MVP wasm module + its worker into ``build/duckdb/``.
  4. Vendor the matching ``parquet`` DuckDB extension into
     ``build/ext/<DUCKDB_VERSION>/wasm_mvp/`` so the page loads it locally
     (never from extensions.duckdb.org).
  5. Convert ``data/feedstock_health.csv`` → ``build/core_feedstock_health.parquet``
     (the statically-hosted Parquet the client-side query reads).
  6. Copy ``index.html`` into ``build/``.

Run: ``pixi run -e local-recipes wasm-build`` (or ``python wasm/build.py``).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
NODE_BIN = "/opt/node22/bin"

# DuckDB *engine* version bundled inside @duckdb/duckdb-wasm 1.33.1-dev57.0.
# The extension repo lays out artifacts as <version>/wasm_mvp/<name>.duckdb_extension.wasm.
# Kept in lockstep with the package.json pin; a drift makes the vendor step below 404.
DUCKDB_VERSION = "v1.5.4"
EXT_URL = (
    f"https://extensions.duckdb.org/{DUCKDB_VERSION}/wasm_mvp/parquet.duckdb_extension.wasm"
)

# Files copied out of node_modules into the served artifact.
DIST = "node_modules/@duckdb/duckdb-wasm/dist"
WASM_ASSETS = ["duckdb-mvp.wasm", "duckdb-browser-mvp.worker.js"]


def _run(cmd: list[str], **kw) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, **kw)


def _npm() -> str:
    npm = shutil.which("npm") or f"{NODE_BIN}/npm"
    if not Path(npm).exists() and not shutil.which("npm"):
        sys.exit(
            "npm not found. Node 22 is expected at /opt/node22/bin — "
            "add it to PATH or install Node before building the WASM artifact."
        )
    return npm


def main() -> int:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    (BUILD / "duckdb").mkdir(parents=True)
    (BUILD / "ext" / DUCKDB_VERSION / "wasm_mvp").mkdir(parents=True)

    import os

    env = dict(os.environ)
    env["PATH"] = f"{NODE_BIN}:{env.get('PATH', '')}"

    npm = _npm()

    # 1. install pinned build deps
    _run([npm, "install", "--no-audit", "--no-fund"], cwd=HERE, env=env)

    # 2. esbuild bundle (single self-contained ESM module)
    esbuild = HERE / "node_modules" / ".bin" / "esbuild"
    _run(
        [
            str(esbuild),
            "entry.mjs",
            "--bundle",
            "--format=esm",
            f"--outfile={BUILD / 'duckdb' / 'duckdb-bundle.mjs'}",
        ],
        cwd=HERE,
        env=env,
    )

    # 3. copy wasm module + worker
    for name in WASM_ASSETS:
        src = HERE / DIST / name
        if not src.exists():
            sys.exit(f"missing DuckDB-WASM asset: {src}")
        shutil.copy2(src, BUILD / "duckdb" / name)

    # 4. vendor the parquet extension locally (build-time network is allowed).
    #    Use curl: it honours the agent proxy + CA bundle where urllib gets a 403.
    ext_dst = BUILD / "ext" / DUCKDB_VERSION / "wasm_mvp" / "parquet.duckdb_extension.wasm"
    print(f"+ vendoring {EXT_URL}")
    curl = shutil.which("curl") or "curl"
    proc = subprocess.run(
        [curl, "-fsSL", "-o", str(ext_dst), EXT_URL],
        env=env,
    )
    if proc.returncode != 0 or not ext_dst.exists():
        sys.exit(
            f"could not vendor the parquet extension from {EXT_URL} (curl exit "
            f"{proc.returncode}).\nIf DUCKDB_VERSION drifted from the @duckdb/duckdb-wasm "
            f"pin, fix it in build.py + index.html."
        )
    if ext_dst.stat().st_size < 100_000:
        sys.exit(f"vendored parquet extension looks too small: {ext_dst.stat().st_size} bytes")

    # 5. CSV -> Parquet (the statically-hosted dataset the client-side query reads)
    _csv_to_parquet(HERE / "data" / "feedstock_health.csv", BUILD / "core_feedstock_health.parquet")

    # 6. the page itself
    shutil.copy2(HERE / "index.html", BUILD / "index.html")

    print(f"\nBuilt WASM artifact → {BUILD}")
    print("Verify with: pixi run -e local-recipes wasm-smoke")
    return 0


def _csv_to_parquet(csv_path: Path, parquet_path: Path) -> None:
    import pandas as pd

    df = pd.read_csv(csv_path)
    # match the D1 core_feedstock_health nullable-int shape (open_prs / open_issues)
    for col in ("open_prs", "open_issues"):
        if col in df.columns:
            df[col] = df[col].astype("Int64")
    df.to_parquet(parquet_path, index=False)
    print(f"+ {csv_path.name} -> {parquet_path.name} ({df.shape[0]} rows)")


if __name__ == "__main__":
    raise SystemExit(main())
