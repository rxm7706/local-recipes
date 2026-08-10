"""Meta-test: the repo-wide spec-surface detector stays green.

spec-regenerable-factory CAP-3: every tracked file is governed by a spec
surface manifest or explicitly allowlisted, and no governed file drifted
without its spec's contract (memlog / sentinel) moving. This mirrors how
test_bmad_artifacts_in_sync.py enforces bmad-drift-check integrity.

Story 6.9: `scripts/spec_surface_check.py` retired into
`pyforge.doctor.sources.chain::gather_spec_surface` (ported verbatim in
behavior, Story 6.6) — this test now exercises `gather_spec_surface`
directly (in-process, no subprocess: there is no script left to shell out
to) instead of running the deleted script.

The fixture-based S-13.1/S-13.2/S-13.5 behavioral suites this file used to
carry (scoped `--write-baseline` stamping, per-file memlog reconciliation,
drift-blind detection) are NOT re-created here. S-13.1's scoped-stamping
tests are gone for real: `--write-baseline`/`--spec` is a CLI mutation path
Story 6.6's own Boundaries deliberately did not port ("Doctor sources are
read-only gathers"; mutation is deferred to a future CLI-wiring story), so
there is nothing left in the codebase for those three tests to exercise.
S-13.2 (per-file reconciliation: drift / drift-presumed) and S-13.5
(drift-blind) are READ-time semantics that `gather_spec_surface` still
fully implements — but their behavioral coverage already lives at
`src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_spec_surface.py`,
built the same way these tests once were (a hand-written
`.spec-surface-baseline.json` fixture standing in for `--write-baseline`'s
output), so duplicating it here would be redundant, not migrated. This file
keeps its own single, narrower job: the LIVE repo's own surface is clean.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]

try:
    from pyforge.doctor.models import DoctorStatus
    from pyforge.doctor.sources import chain as spec_surface_chain
except ImportError:
    spec_surface_chain = None  # type: ignore[assignment]


@pytest.mark.skipif(
    spec_surface_chain is None,
    reason="pyforge.doctor not present (skill used standalone)",
)
def test_spec_surface_check_green():
    findings = spec_surface_chain.gather_spec_surface(REPO_ROOT)
    gating = [f for f in findings if f.status is DoctorStatus.FAIL]
    assert not gating, (
        "spec-surface reports findings — a tracked file is ungoverned "
        "or governed code drifted without its spec moving. Reconcile per "
        "the finding (update the spec / bmad-spec re-derive, then "
        "--write-baseline; or add a reason-tagged allowlist entry):\n"
        + "\n".join(f"[{f.check}] {f.message}" for f in gating)
    )
