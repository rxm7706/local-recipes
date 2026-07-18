"""``publish`` task entrypoint — emit the demo static-host layout (Story G2, FR-14).

Emits the D1 ``core_feedstock_health`` dataset (the same seed the G1 WASM surface reads,
``wasm/data/feedstock_health.csv``) as the chunked-Parquet + ``manifest.json`` layout the
emitter owns, into a target directory = "the static host filesystem".

This is the BUILD of the publishable layout — it is fully local and offline. The LIVE
publish (pushing ``target_dir`` to GitHub Pages / a real host) is the ATTENDED boundary
event and is DEFERRED (see DW-G2). Point a static host — or the WASM runtime's Range
consumer — at ``target_dir`` to serve it.

Run: ``pixi run -e local-recipes publish [-- --target <dir>]``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from .emitter import emit_static_site

_HERE = Path(__file__).resolve().parent
# publish -> atlas -> pyforge -> src -> pyforge-atlas
_PKG_ROOT = _HERE.parents[3]
_DEFAULT_SEED = _PKG_ROOT / "wasm" / "data" / "feedstock_health.csv"
_DEFAULT_TARGET = _HERE / "_site"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="publish", description=__doc__)
    parser.add_argument("--target", type=Path, default=_DEFAULT_TARGET,
                        help=f"static-host output directory (default: {_DEFAULT_TARGET})")
    parser.add_argument("--seed", type=Path, default=_DEFAULT_SEED,
                        help=f"seed CSV for the demo dataset (default: {_DEFAULT_SEED})")
    parser.add_argument("--rows-per-chunk", type=int, default=250_000)
    parser.add_argument("--row-group-size", type=int, default=100_000)
    args = parser.parse_args(argv)

    if not args.seed.exists():
        print(f"seed CSV not found: {args.seed}", file=sys.stderr)
        return 1

    df = pd.read_csv(args.seed)
    manifest = emit_static_site(
        {"core_feedstock_health": df},
        args.target,
        rows_per_chunk=args.rows_per_chunk,
        row_group_size=args.row_group_size,
    )

    print(f"Emitted static-host layout -> {args.target}")
    for name, ds in manifest["datasets"].items():
        print(f"  {name}: {ds['row_count']} rows, {len(ds['chunks'])} chunk(s)")
        for chunk in ds["chunks"]:
            print(f"    {chunk['path']}  ({chunk['bytes']} bytes, sha256 {chunk['sha256'][:12]}…)")
    print(f"  {args.target}/manifest.json  (single-owner layout contract)")
    print(
        "\nServe this directory from any static host (host-agnostic, AD-2). "
        "The LIVE GitHub Pages publish is the ATTENDED boundary event and is DEFERRED (DW-G2)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
