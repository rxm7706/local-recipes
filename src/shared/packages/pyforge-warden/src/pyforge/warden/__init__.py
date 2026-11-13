"""pyforge.warden — unified dependency-hygiene + vulnerability scanner.

Orchestrates ``deptry`` (unused / missing / transitive deps) and Google's
``osv-scanner`` (known CVEs) over Python / Conda / Pixi manifests, emitting a
single schema-validated ``ComplianceReport`` and a strict CI/CD exit-code gate.

The contract is the station Spec in
``_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/``;
every surface a caller reaches is listed in its ``contract.md`` beside ``SPEC.md``.
"""

__version__ = "0.1.0"
