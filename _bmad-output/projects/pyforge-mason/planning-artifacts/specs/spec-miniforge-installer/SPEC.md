---
spec: miniforge-installer
status: extension-point
owner-dream: docs/dreams/miniforge-installer.md
trigger: "steward's enterprise-airgap/12.3 work surfaces a private-channel-locking need for a Python distributable"
companions: []
sources:
  - ../../../../../../docs/dreams/miniforge-installer.md
---

# SPEC — A custom-branded Python distributable (PARKED)

Parked by the Dream's own constraint — it is a parity capture whose premise
is not yet real here. pixi from public channels already serves the role fleet-wide. Zero stories minted; when the trigger fires, this
spec gets a real pass and decomposition. Parking recorded 2026-08-22 so
INV-1 holds without speculative work.

**Trigger:** steward's enterprise-airgap/12.3 work surfaces a private-channel-locking need for a Python distributable

## Extension contract (added 2026-08-22)

The fleet ships the SOCKET, not the installer: a documented air-gap
distribution contract — what any distributable must provide (mirrored
channel set, pixi bootstrap path, post-install verification hooks) — plus
an empty backend registry (the `_SUPPORTED_MODULES` one-entry-at-a-time
precedent) and a shape-validating test (mason Story 9.2, coordinated with
steward 12.3's air-gap run). A Miniforge/constructor-based installer — or
any vendor's — is then a SEPARATE deliverable that registers and validates,
never a core build.

## Trigger ownership — 2026-09-09

Status stays `extension-point` and this Spec is **correct as written**: the socket is
real and the capability is correctly absent — `pyforge/mason/airgap_contract.py:54`
declares `SUPPORTED_DISTRIBUTABLES = {}`, empty by design.

The finding is an **ownership asymmetry**. The declared trigger — *steward's
enterprise-airgap/12.3 work surfaces a private-channel-locking need for a Python
distributable* — is STEWARD-OWNED and UN-WATCHED: nothing on the steward side points
back at this extension-point, so the trigger can fire in steward's chain with no
signal reaching mason. A **reciprocal pointer** is requested in steward's
enterprise-airgap chain, naming `spec-miniforge-installer` as the extension-point that
activates when 12.3 surfaces the need — cross-station, mason cannot write it; routed to
steward in the fleet-readiness apply report.
