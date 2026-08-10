#!/usr/bin/env python3
"""bmad-loop's own S-13.7 verify-step reconciliation gate -- install-free.

Appended into every station's rendered `policy.toml` by
`pyforge.marshal.adapters.harness_bmadloop::render_policy_toml`
(`_SURFACE_RECONCILE_COMMAND`), so this runs as one of bmad-loop's own
verify commands, inside a fresh git worktree, on every story. Deep
bmad-loop worktrees panic pixi on path length (a known, separately
documented project constraint), so this must work with ZERO environment --
no `pip install`, no `pixi run`.

It reaches `pyforge.doctor.sources.chain.gather_spec_surface` (Story 6.9's
read-only port of the coverage/drift verdict `scripts/spec_surface_baseline.py`
used to compute directly) by inserting this checkout's own
`src/shared/packages/pyforge-doctor/src` onto `sys.path` -- the checkout's
own files on disk, always present in any worktree of this repo, nothing to
install. Mirrors `tests/scripts/test_detectors_doctor_sources.py`'s own
established pattern for reaching `pyforge.doctor` the same install-free way.

NOT FULLY INSTALL-FREE, one honest caveat (review pass 2): `sources/chain.py`
imports `yaml` (PyYAML) at module level -- a real transitive dependency
this sys.path trick does not vendor or avoid. Every environment this has
been tried on so far has PyYAML available on its system Python, but that is
not a guarantee (e.g. a minimal container with no site-packages at all). If
the import fails, this degrades to a clear "cannot evaluate here" message
and exit 2 -- Doctor's own unknown-never-green convention -- rather than a
raw traceback.

NEVER `--write-baseline`, and this script does not expose one. A producer
that can stamp its own baseline is exactly the laundering S-13.2 exists to
end: the loop must RECONCILE by naming the changed paths in the owning
Spec's `.memlog.md`, never accept its own drift as correct. Baseline
stamping stays a human-invoked operation via the mutation-only residual
`scripts/spec_surface_baseline.py -- --write-baseline [--spec NAME]`.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_DOCTOR_SRC = REPO_ROOT / "src" / "shared" / "packages" / "pyforge-doctor" / "src"
if str(_DOCTOR_SRC) not in sys.path:
    sys.path.insert(0, str(_DOCTOR_SRC))


def main() -> int:
    try:
        from pyforge.doctor.models import DoctorStatus
        from pyforge.doctor.sources.chain import gather_spec_surface
    except ImportError as exc:
        print(
            f"UNKNOWN: cannot evaluate here -- {exc}. "
            f"gather_spec_surface needs PyYAML on this Python; the "
            f"sys.path trick above reaches this checkout's own pyforge-doctor "
            f"package but does not vendor its transitive dependencies. "
            f"Never treat this as green.",
            file=sys.stderr,
        )
        return 2

    findings = gather_spec_surface(REPO_ROOT)
    gating = [f for f in findings if f.status is DoctorStatus.FAIL]
    for f in gating:
        print(f"[{f.check}] {f.message}")
    if gating:
        print(
            f"\nFINDINGS ({len(gating)}): a tracked file is ungoverned, or "
            f"governed code drifted without its spec moving. Reconcile by "
            f"naming the changed paths in the owning Spec's .memlog.md."
        )
        return 1
    print("OK: every tracked file governed or allowlisted; no drift.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
