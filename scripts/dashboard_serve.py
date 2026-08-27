#!/usr/bin/env python3
"""Serve the pyforge-atlas Vizro dashboard locally — the missing DW-D2-3 entrypoint.

`dashboard-dryrun` builds the Dashboard OBJECT offline and asserts structure; until
this script existed there was no sanctioned way to actually LOOK at the rendered UI
(DW-D2-3: "no one has visually verified the rendered dashboard in a browser").
This serves it: build via the same `build_dashboard()` the dryrun gate exercises,
then `.run()` a local dev server. Local-only by default (127.0.0.1); no daemon, no
watch loop — foreground until Ctrl-C, matching the operator's manual-not-daemon
preference for board tooling.

Usage: pixi run -e local-recipes dashboard-serve [-- --port 8050]
"""
from __future__ import annotations

import argparse


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="127.0.0.1", help="bind address (default 127.0.0.1)")
    ap.add_argument("--port", type=int, default=8050, help="port (default 8050)")
    args = ap.parse_args()

    # Imports inside main so `--help` works without the dashboard extras installed.
    from vizro import Vizro

    from pyforge.atlas.dashboard.app import build_dashboard

    dashboard = build_dashboard()
    print(f"[dashboard-serve] {len(dashboard.pages)} pages -> http://{args.host}:{args.port}")
    Vizro().build(dashboard).run(host=args.host, port=args.port, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
