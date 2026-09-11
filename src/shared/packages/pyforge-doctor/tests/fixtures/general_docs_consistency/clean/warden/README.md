# pyforge-warden

Unified dependency-hygiene + vulnerability scanner that orchestrates
deptry and osv-scanner over Python / Conda / Pixi manifests, emitting one
schema-validated `ComplianceReport` and acting as a strict CI/CD exit-code gate.
