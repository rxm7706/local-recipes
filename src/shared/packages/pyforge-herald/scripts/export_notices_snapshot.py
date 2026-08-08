#!/usr/bin/env python3
"""Export the visible (published + closed) notices from
``.herald/notices-index.json`` to ``web/public/notices.json`` -- the
static-JSON-snapshot the Operations web tab (Story 10.5) fetches at load,
since Herald has no running server to query live.

**Not (yet) consolidated with a shared exporter.** At the time this script
was written, no shared ``export-web-snapshot`` script existed on ``main``
for the other two Moments (Progress/Success, Epics 8/9) to have
established a convention this could extend -- each Moment's own storage
module (``progress.py``/``claims.py``/``notices.py``) has a different
filter shape (drafts excluded here; Success's own draft/published split is
a separate concept). A later story can fold all three into one generic
"dump this module's public listing to a JSON file" script once the shape
each Moment needs is settled; deliberately not attempted here (Simplicity
First -- speculative generalization ahead of a second, confirmed use).

Usage::

    python scripts/export_notices_snapshot.py [--repo-root PATH] [--out PATH]

Run manually (or by a future CI/build step) whenever the notices index
changes and the web dashboard needs to reflect it -- there is no watcher or
build-time hook wiring this in automatically yet.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_SRC = _PACKAGE_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from pyforge.herald import notices


def export_snapshot(repo_root: Path, out_path: Path) -> int:
    results = notices.list_notices(repo_root, status="all")
    payload = [
        {
            "type": n.type,
            "component": n.component,
            "what": n.what,
            "why": n.why,
            "migration": n.migration,
            "deadline": n.deadline,
            "reason_link": n.reason_link,
            "status": n.status,
            "created_at": n.created_at,
            "published_at": n.published_at,
            "closed_at": n.closed_at,
            "closed_by": n.closed_by,
            "close_reason": n.close_reason,
        }
        for n in results
        if n.status != "draft"  # drafts never ship to the public web snapshot
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return len(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--out",
        type=Path,
        default=_PACKAGE_ROOT / "web" / "public" / "notices.json",
    )
    args = parser.parse_args(argv)
    count = export_snapshot(args.repo_root, args.out)
    print(f"exported {count} notice(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
