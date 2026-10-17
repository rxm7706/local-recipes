#!/usr/bin/env python3
"""Fail `viz-build` when `kedro viz build` wrote no complete build (atlas Story 32.1, CAP-62).

kedro-viz 12.5.0's `kedro viz build` catches every exception its build raises, prints
``ERROR: Failed to build/deploy Kedro-Viz : <cause>`` and exits 0
(``kedro_viz/launchers/cli/utils.py``, ``create_shareableviz_process``). So `viz-build`
read green on a failed build, `viz-publish-stage`'s ``depends-on`` never stopped it, and
the failure surfaced one command later as ``normalize_viz_build.py``'s "build does not
exist" (kedro-viz-publish.yml run 39002722593, 2026-10-17: a credentials key the
workflow's stub lacked).

The `viz-build` task runs this right after `kedro viz build`. The deployer
(``kedro_viz/integrations/deployment/base_deployer.py``, ``deploy``) writes the API
responses first (``api/main``), then the static files (``index.html``), then
``api/deploy-viz-metadata`` last, so all three present means the deploy ran to its end.
`viz-build` removes ``build/`` before it builds, so a failed build leaves none of them.

Exit codes (atlas NFR-6): 0 the build is complete, 1 it is not (each missing file named on
stderr). Stdlib only; never touches the network. An operator convenience script
(``tools/``), outside the package the no-inline-IO gate scans, like ``normalize_viz_build.py``.

    python src/shared/packages/pyforge-atlas/tools/viz_build_check.py [--build-dir DIR]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_MEMBER_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_OUTPUTS = ("api/main", "index.html", "api/deploy-viz-metadata")


def missing_outputs(build_dir: Path) -> list[str]:
    """The files of ``REQUIRED_OUTPUTS`` that are not regular files under ``build_dir``, in order."""
    return [rel for rel in REQUIRED_OUTPUTS if not (build_dir / rel).is_file()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail when `kedro viz build` wrote no complete build.")
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=_MEMBER_ROOT / "build",
        help="the kedro-viz build directory (default: the atlas project's build/)",
    )
    args = parser.parse_args([] if argv is None else argv)
    build_dir: Path = args.build_dir

    missing = missing_outputs(build_dir)
    if missing:
        print(
            f"viz-build: `kedro viz build` wrote no complete build under {build_dir} -- missing: "
            f"{', '.join(missing)}. kedro-viz exits 0 when its build fails; its own "
            "'ERROR: Failed to build/deploy Kedro-Viz' line above names the cause. "
            "'Unable to find credentials <key>' means conf/local/credentials.yml lacks a key "
            "conf/base/catalog.yml names: add it as `<key>: {}` (tools/bootstrap.py's "
            "--credentials-only writes the full stub when the file is absent or empty).",
            file=sys.stderr,
        )
        return 1
    print(f"viz-build: build complete under {build_dir} ({', '.join(REQUIRED_OUTPUTS)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
