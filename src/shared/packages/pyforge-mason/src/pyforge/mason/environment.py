"""`mason environment` -- resolve conflicting worlds into one lockfile
(FR-25 - FR-29).

Seeded docstring-only (Story 1.7) solely to prove AD-6's import-safety
invariant: unlike `package.py`, `environment.py` has no CFE-dependent target
at all -- every verb here must import cleanly with no CFE anywhere on the
filesystem. `tests/meta/test_capability_tiers.py` guards this file for
exactly that: no module-level `cfe` import, ever. Importing `engines.
condalock` here does not violate that guard -- that module itself has no
CFE dependency (Story 4.1).

Story 4.3 adds `lock()`, the `mason environment lock` use-case: a thin
wrapper around `engines.condalock.lock()`, mirroring `package.py::build()`'s
own engine-wrapping shape. Manifest auto-discovery (Story 4.2) is not yet
built, so `lock()` requires its caller to supply manifest paths explicitly
-- `cli.py`'s own `manifest_path` positional (`nargs="+"`) enforces "at
least one" before this function is ever reached. Lock staleness checking
(`mason environment check`, Story 4.4) has no presence here yet.
"""

from __future__ import annotations

from collections.abc import Sequence

from .engines import condalock
from .models import LockResult


def lock(
    manifest_paths: Sequence[str], output_path: str, *, platforms: str | None = None
) -> LockResult:
    """Resolve `manifest_paths` into a lockfile at `output_path` via
    `engines.condalock.lock()` (FR-25, FR-27, FR-29).

    `platforms` is the caller's own raw `--platform` value: a comma-separated
    string (`cli.py`'s own precedent for a repeatable flag, matching `--to`'s
    established idiom -- spec Always boundary) or `None` when the flag was
    omitted. Split and stripped into a tuple here, in the use-case layer, not
    in `cli.py` -- mirrors `package.py::parse_ship_targets`'s own
    raw-string-in/parsed-in-the-use-case-layer split for `--to`. Empty
    tokens are silently dropped (no closed platform vocabulary exists for
    Mason to validate against, spec Never boundary): an invalid or malformed
    platform value surfaces as `conda-lock`'s own non-zero returncode
    (AD-4), never a Mason-side check. `platforms=None` or `""` both resolve
    to `()`, letting `conda-lock`'s own default apply (FR-27) -- Mason never
    invents one.

    No pre-validation of `manifest_paths` existence or `output_path`'s
    parent directory (spec Always boundary, mirrors `engines.condalock.
    lock()`'s own identical precedent) -- a bad path surfaces as
    `conda-lock`'s own non-zero returncode, never raised here.

    Raises `EngineAbsentError`/`EnvironmentLockTimeoutError` (both already
    defined, Story 4.1), propagated unchanged from `engines.condalock.
    lock()`.
    """
    if platforms:
        parsed_platforms = tuple(
            stripped for token in platforms.split(",") if (stripped := token.strip())
        )
    else:
        parsed_platforms = ()

    result = condalock.lock(manifest_paths, output_path, platforms=parsed_platforms)

    return LockResult(
        manifest_paths=tuple(manifest_paths),
        output_path=output_path,
        platforms=parsed_platforms,
        engine_name=result.engine_name,
        engine_version=result.engine_version,
        returncode=result.returncode,
        stdout=result.stdout,
    )
