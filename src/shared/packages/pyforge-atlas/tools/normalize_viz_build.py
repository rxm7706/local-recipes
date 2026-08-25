#!/usr/bin/env python3
"""Normalize `kedro viz build`'s static export so it is reproducible across
checkouts, not just across repeated runs in the same one.

Epic 12/FR-62's publish pipeline (`viz-publish-stage`) only works if two
builds of an unchanged DAG produce byte-identical output -- Steward's
`deploy dashboard` treats any diff as a real change to commit+push. Two
independent root causes defeat that, on top of (not instead of) pinning
`PYTHONHASHSEED=0` on the `viz-build` task (which alone fixes the *ordering*
of kedro-viz's internal `set`-based node/pipeline/edge enumeration, but
nothing else):

1. ``build/api/deploy-viz-metadata`` embeds a literal build wall-clock
   timestamp (``{"timestamp": "...", "version": "..."}``) -- unrelated to
   hash seeding, and different on every build regardless of source changes.
   ``version`` is left untouched; it's real signal (the kedro-viz release
   that produced the build), not noise.

2. ~53 of the ~136-195 exported files under ``build/api/nodes/*`` embed an
   ABSOLUTE filesystem path for every file-backed (Parquet/JSON/...) dataset
   node -- anchored to whatever checkout location `kedro viz build` ran
   from (e.g. ``/home/<user>/.../src/shared/packages/pyforge-atlas/data/
   intermediate/...``). Confirmed empirically confined to ``build/api/``
   today (a full-tree scan of ``build/assets``, ``build/.vite``, and
   ``build/index.html`` found none) -- but this script scans the WHOLE
   ``build/`` tree anyway (see review pass 3), so a future kedro-viz release
   leaking the same anchor somewhere else (e.g. a JS source map) is still
   caught by the same mechanism rather than silently missed. Two different
   checkouts (a CI runner vs. a developer's machine, or two developers)
   never agree on this path, so it would show a diff on every affected file
   on every build, forever -- permanently defeating the "commit only on a
   real difference" guarantee, in a way a same-directory rebuild-twice test
   cannot detect (the path never changes between two rebuilds in one
   checkout). Verified cross-checkout (review pass 3): building from a
   second, genuinely different absolute path and normalizing there produces
   output byte-identical to a normalized build from this checkout.

Both fixes must fail LOUDLY (raise, non-zero exit) if the substitution they
attempt turns out not to have taken effect -- a silent no-op (e.g. after a
future kedro-viz release reshapes this output, or the anchor's own format
changes) would look like success while leaving real non-determinism in
place. This script supersedes an earlier inline `sed`-based timestamp
normalize step, which could exit 0 having matched nothing.

Run via the `viz-publish-stage` pixi task (after `viz-build`), or standalone
from anywhere:

    python src/shared/packages/pyforge-atlas/tools/normalize_viz_build.py
"""
from __future__ import annotations

import re
from pathlib import Path

# What the leaked absolute path actually anchors to (the atlas project root,
# not the overall repo root) -- named precisely so a future reader isn't
# misled into thinking `<REPO_ROOT>/data/...` is relative to the repo root.
PLACEHOLDER = "<PYFORGE_ATLAS_ROOT>"
_ATLAS_PKG_RELATIVE = Path("src/shared/packages/pyforge-atlas")
_BUILD_RELATIVE = _ATLAS_PKG_RELATIVE / "build"
_METADATA_RELATIVE = _BUILD_RELATIVE / "api" / "deploy-viz-metadata"
_TIMESTAMP_PATTERN = re.compile(r'"timestamp":\s*"[^"]*"')

# Same single-file-marker convention as pyforge-steward's own
# `deploy.py::repo_root()` (review pass 3: a two-condition AND-marker is
# unnecessary complexity here since this exact marker is already proven
# unique in this repo).
_REPO_ROOT_MARKER = Path("docs/dashboard/kedro-viz/index.html")


def repo_root() -> Path:
    """Return the local-recipes checkout root.

    Walks up from this file's own resolved location looking for
    `docs/dashboard/kedro-viz/index.html` -- mirrors `pyforge-steward`'s
    `deploy.py::repo_root()` convention exactly (same marker file).
    """
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / _REPO_ROOT_MARKER).is_file():
            return ancestor
    raise RuntimeError(
        f"normalize_viz_build: could not locate {_REPO_ROOT_MARKER} by "
        f"walking up from {here} -- this script must live inside a "
        f"local-recipes checkout."
    )


def _iter_text_files(directory: Path):
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        try:
            yield path, path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # not a text file -- not a leak surface for a literal path string


def _strip_anchor(build_dir: Path, anchor: str) -> int:
    """Replace every literal occurrence of `anchor` with PLACEHOLDER in every
    file under `build_dir`. Returns the number of files changed."""
    changed = 0
    for path, text in _iter_text_files(build_dir):
        if anchor in text:
            path.write_text(text.replace(anchor, PLACEHOLDER), encoding="utf-8")
            changed += 1
    return changed


def _assert_anchor_handled(build_dir: Path, anchor: str, files_changed: int) -> None:
    """Fail loudly on EITHER failure shape: leftover occurrences after the
    strip (substitution incomplete), or zero occurrences ever found (review
    pass 3: the strip alone can't distinguish "correctly nothing to do" from
    "the anchor's format changed and this silently stopped matching" --
    unlike `_normalize_timestamp`'s own `n_subs == 0` guard, which already
    catches its equivalent case)."""
    if files_changed == 0:
        raise RuntimeError(
            f"normalize_viz_build: the checkout-anchored path {anchor!r} was not "
            f"found in ANY file under {build_dir} -- either kedro-viz stopped "
            f"embedding it (in which case this whole step is now a no-op that "
            f"should be removed, not silently kept), or something about its "
            f"format changed and this needs a real fix, not silent success."
        )
    leftover = [path for path, text in _iter_text_files(build_dir) if anchor in text]
    if leftover:
        raise RuntimeError(
            f"normalize_viz_build: {len(leftover)} file(s) under {build_dir} still "
            f"contain the checkout-anchored path {anchor!r} after substitution "
            f"(first few: {[str(p) for p in leftover[:5]]}) -- the anchor-strip "
            f"is incomplete; this must be fixed, not ignored."
        )


def _normalize_timestamp(metadata_path: Path) -> int:
    if not metadata_path.is_file():
        raise RuntimeError(
            f"normalize_viz_build: expected metadata file not found: {metadata_path}"
        )
    text = metadata_path.read_text(encoding="utf-8")
    normalized, n_subs = _TIMESTAMP_PATTERN.subn('"timestamp": "unset"', text)
    if n_subs == 0:
        raise RuntimeError(
            f'normalize_viz_build: expected "timestamp" field not found in '
            f"{metadata_path} -- kedro-viz may have changed this file's shape; "
            f"this needs a real fix, not a silent no-op."
        )
    metadata_path.write_text(normalized, encoding="utf-8")
    return n_subs


def main() -> int:
    root = repo_root()
    anchor = str(root / _ATLAS_PKG_RELATIVE)
    build_dir = root / _BUILD_RELATIVE

    if not build_dir.is_dir():
        raise RuntimeError(
            f"normalize_viz_build: {build_dir} does not exist -- run the "
            f"`viz-build` pixi task first."
        )

    files_changed = _strip_anchor(build_dir, anchor)
    _assert_anchor_handled(build_dir, anchor, files_changed)

    n_subs = _normalize_timestamp(root / _METADATA_RELATIVE)

    print(
        f"normalize_viz_build: stripped checkout-anchored path from "
        f"{files_changed} file(s) under {build_dir.relative_to(root)}; "
        f"normalized {n_subs} timestamp field(s) in "
        f"{_METADATA_RELATIVE.name}; re-scan confirmed zero anchor "
        f"occurrences remain."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
