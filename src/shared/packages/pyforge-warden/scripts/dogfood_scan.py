"""Dogfood scan (Story 5.2, epics.md AC3): Warden scanning its OWN package
manifest. The ``pyforge-warden-dogfood`` pixi task and ``tests/conformance/
test_dogfood.py`` both use this module's ``stage_dogfood_copy`` /
``BASELINE_PATH`` rather than duplicating the staging logic.

The literal ``warden scan src/shared/packages/pyforge-warden`` command
would also recursively sweep up this package's OWN ``tests/`` tree
(``discovery.discover`` has no ignore mechanism -- FR1's full-tree-walk
design has no exclude list, by design) -- including the deliberately
malformed/vulnerable/adversarial fixtures ``test_scan_harness.py`` and
friends exist to exercise (live-verified while authoring this story: 86
findings from ``tests/fixtures/projects/`` alone, before even considering
the ~2,000-file corpus this same story adds under ``tests/fixtures/
corpus/``). None of that is "this package's own dependency hygiene", so
the dogfood scan targets a STAGED COPY of just ``pyproject.toml`` + ``src/``
(this package's real, shipped surface) -- never the whole package
directory.

Even narrowed to ``{pyproject.toml, src/}``, a handful of findings are
currently unavoidable and grandfathered via the committed
``.warden-baseline.yaml`` (see that file's own header for the full
rationale): this package's dependencies are intentionally unpinned (a
library convention, no lockfile of its own), so Warden's own vulnerability/
currency axes cannot resolve a concrete version for any of them, and a bare
subprocess invocation (unlike the test suite, which gets ambient KEV/
currency/OSV-DB fixtures from ``tests/conftest.py``) has no OSV DB
provisioned either. A genuinely NEW finding is unaffected by the baseline
and still gates normally -- see ``test_dogfood.py``'s seeded-violation half.

Dev-only maintenance script -- not part of the installed ``pyforge.warden``
package (mirrors ``scripts/refresh_kev_feed.py``'s/``scripts/
harvest_corpus.py``'s dev-only-script convention)."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = _SCRIPTS_DIR.parent
_SRC_DIR = PACKAGE_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from pyforge.warden.cli import main as warden_main  # noqa: E402

BASELINE_PATH = PACKAGE_ROOT / ".warden-baseline.yaml"


def stage_dogfood_copy(dest: Path) -> None:
    """Copies this package's own manifest + source (never ``tests/``/
    ``scripts/``/build artifacts) into ``dest`` -- the surface a dogfood
    scan means to assess. ``dest`` is created if it does not already exist;
    the caller owns its lifecycle (a ``tempfile.TemporaryDirectory`` in
    both callers below).

    ``dirs_exist_ok=True`` on the ``copytree`` (review finding): both
    current callers always pass a freshly-created tempdir, so this is
    defensive rather than load-bearing today -- but ``shutil.copytree``'s
    default ``dirs_exist_ok=False`` would raise ``FileExistsError`` on a
    second call against the same ``dest``, which the plain ``mkdir(...,
    exist_ok=True)`` line above otherwise implies this function tolerates."""
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PACKAGE_ROOT / "pyproject.toml", dest / "pyproject.toml")
    shutil.copytree(
        PACKAGE_ROOT / "src",
        dest / "src",
        ignore=shutil.ignore_patterns("__pycache__"),
        dirs_exist_ok=True,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--emit-baseline",
        action="store_true",
        help=(
            "regenerate the .warden-baseline.yaml stanza: run the SAME "
            "staged {pyproject.toml, src/} scan the gate uses, WITHOUT "
            "--baseline (so every current finding appears in the stanza) "
            "and WITH warden's --baseline-emit (follow-up review finding: "
            "the previously-documented raw `warden scan <package-dir> "
            "--baseline-emit` sweeps tests/ fixtures into the stanza -- "
            "the very noise stage_dogfood_copy exists to exclude). Review "
            "and re-stamp the printed expires_at dates before committing; "
            "warden's emitted default is now + 14 days"
        ),
    )
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="pyforge-warden-dogfood-") as tmp:
        dest = Path(tmp) / "pyforge-warden"
        stage_dogfood_copy(dest)
        if args.emit_baseline:
            return warden_main(["scan", str(dest), "--baseline-emit"])
        return warden_main(["scan", str(dest), "--baseline", str(BASELINE_PATH)])


if __name__ == "__main__":
    raise SystemExit(main())
