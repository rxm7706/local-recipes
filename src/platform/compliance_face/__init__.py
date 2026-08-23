"""Compliance factory web face (warden Stories 8.1 + 8.2).

Host decision (2026-08-22): platform-app — reuse Django + Celery already in
``src/platform``, never a standalone service.

CAP-1: upload a supported manifest; Celery job calls EXISTING warden engines
via keys-not-blobs (store path/key on disk, never put file bytes on the
broker). CAP-2: progress derives from phase position (``_phase_guard``);
reports reuse the same CLI renderers.
"""

from __future__ import annotations

default_app_config = "compliance_face.apps.ComplianceFaceConfig"
