"""Port Protocol definitions (Structural Seed): ``ports/`` declares shapes,
never implementations (AD-11); each port's implementation lives solely in
``adapters/`` (AD-4).

Every port's AD-34 egress classification is now a REAL registry --
``core.egress.EGRESS_PORTS``, keyed by Protocol class name -- superseding
this docstring's former "each port will declare egress: true|false"
placeholder. (Its exact contents are deliberately NOT restated here --
review finding: a literal copy drifts the moment a port is added or
reclassified, with nothing to catch it; read ``core.egress.EGRESS_PORTS``
directly.) An egress-classified port accepts exclusively a
``core.egress.Redacted`` payload, never a bare ``str`` --
``tests/meta/test_ad34_egress_registry_completeness.py`` fails the build if
a new Protocol defined under this package has no entry in the registry, or
if an egress-classified port's method accepts a bare ``str`` parameter."""

from __future__ import annotations
