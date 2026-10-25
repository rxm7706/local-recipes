#!/usr/bin/env python3
"""``vizro-static-export``: the Vizro boards as static pages (Story 30.2, CAP-63).

Order, every step before anything is written:

1. the flag ``pyforge.atlas.vizro_static_boards`` (off: the flag-off message, atlas's usage
   exit code 2, nothing written);
2. the access-column refusal (``sld:AD-10``: exit 1 naming the board);
3. plotly's ``package_data/plotly.min.js`` in this env (missing: exit 1 naming it);
4. ``export_commit`` through Story 30.1's helper (``GITHUB_SHA``, else ``git rev-parse HEAD``;
   unresolved: exit 1 naming the field), and ``exported_at`` as that commit's committer time (the same
   helper's ``git show``), so the export of one commit is byte-identical on every run with the same data;
5. ``dashboard.static_export.export_boards`` renders every board in memory and swaps the
   finished tree in for ``docs/dashboard/vizro/``.

``--print-flag`` prints ``enabled=true|false`` for a workflow's ``$GITHUB_OUTPUT`` and exits 0.
Exit codes are atlas's frozen four: 0 written, 1 refused, 2 usage or crash, 130 interrupted.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
_ATLAS_SRC = _TOOLS.parent / "src"
for _entry in (_ATLAS_SRC, _TOOLS):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

import viz_manifest  # noqa: E402 -- Story 30.1's export_commit helper, one directory over

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_USAGE = 2
EXIT_INTERRUPTED = 130
STAGED_RELATIVE = Path("docs/dashboard/vizro")
_PREFIX = "vizro-static-export"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=_PREFIX, description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=None, help=f"output directory (default: <repo>/{STAGED_RELATIVE})")
    parser.add_argument("--data-root", type=Path, default=None, help="data root (default: the dashboard's own)")
    parser.add_argument("--flags-path", default=None, help="flag tree (default: PYFORGE_FLAGS_PATH or the repo's)")
    parser.add_argument("--export-commit", default=None, help="40-hex commit (default: GITHUB_SHA, else HEAD)")
    parser.add_argument("--print-flag", action="store_true", help="print enabled=true|false and exit 0")
    parser.add_argument(
        "--clock",
        choices=("commit", "now"),
        default="commit",
        help="what exported_at is: the export commit's committer time (default; one commit's export is "
        "byte-identical) or now (Story 37.2: the weekly build, whose data is newer than its commit; a local export "
        "of data built after the commit needs it too, or the upload ages read negative)",
    )
    return parser


def _resolve_export_commit(explicit: str | None) -> str | None:
    try:
        return viz_manifest._resolve_export_commit(explicit)
    except SystemExit:
        return None


def _resolve_exported_at(export_commit: str) -> datetime | None:
    try:
        return datetime.fromisoformat(viz_manifest._committer_date_iso_utc(export_commit))
    except SystemExit:
        return None


def _run(args: argparse.Namespace) -> int:
    from pyforge.atlas.vizro_static_boards import FLAG_KEY, boards_enabled

    enabled = boards_enabled(flags_path=args.flags_path)
    if args.print_flag:
        print(f"enabled={'true' if enabled else 'false'}")
        return EXIT_OK
    if not enabled:
        print(f"{_PREFIX}: flag {FLAG_KEY} is off; nothing written", file=sys.stderr)
        return EXIT_USAGE

    # The vizro closure is imported only once the flag reads on.
    from pyforge.atlas.dashboard import static_export

    try:
        static_export.refuse_access_columns()
        static_export.plotly_bundle()
    except static_export.StaticExportError as exc:
        print(f"{_PREFIX}: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    export_commit = _resolve_export_commit(args.export_commit)
    if export_commit is None:
        print(
            f"{_PREFIX}: export_commit could not be resolved (no 40-hex GITHUB_SHA or --export-commit, "
            "and git rev-parse HEAD failed); nothing written",
            file=sys.stderr,
        )
        return EXIT_REFUSED

    exported_at = None if args.clock == "now" else _resolve_exported_at(export_commit)
    if exported_at is None and args.clock == "commit":
        print(
            f"{_PREFIX}: exported_at could not be resolved (no committer time for export_commit "
            f"{export_commit[:12]}); nothing written",
            file=sys.stderr,
        )
        return EXIT_REFUSED

    out_dir = args.out if args.out is not None else viz_manifest.repo_root() / STAGED_RELATIVE
    try:
        manifest = static_export.export_boards(
            out_dir,
            export_commit=export_commit,
            exported_at=exported_at,
            data_root=args.data_root,
            flags_path=args.flags_path,
        )
    except static_export.StaticExportError as exc:
        print(f"{_PREFIX}: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    print(f"{_PREFIX}: wrote {len(manifest['boards'])} boards to {out_dir} (export_commit {export_commit[:12]})")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        return _run(args)
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED
    except Exception as exc:  # noqa: BLE001 -- a crash is atlas's 2, never Python's default 1
        print(f"{_PREFIX}: crashed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
