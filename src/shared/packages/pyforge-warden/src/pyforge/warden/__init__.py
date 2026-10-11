"""pyforge.warden — unified dependency-hygiene + vulnerability scanner.

Orchestrates ``deptry`` (unused / missing / transitive deps) and Google's
``osv-scanner`` (known CVEs) over Python / Conda / Pixi manifests, emitting a
single schema-validated ``ComplianceReport`` and a strict CI/CD exit-code gate.

This module is the Option-B build-wiring skeleton; the E1-E4 implementation
(extractor, runners, report, CLI) is delivered by bmad-quick-dev against
``docs/specs/pyforge-warden.md``.
"""

__version__ = "0.1.0"
