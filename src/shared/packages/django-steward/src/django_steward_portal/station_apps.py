"""Station apps the platform host installs for steward (Story 127.1).

The host's settings read ``STATION_APPS`` from every portal package that has
this module and add each name to ``INSTALLED_APPS``, so a station's own Django
app migrates into the host's database without ``src/platform`` naming station
code. This module is read before Django's app registry loads: it holds names
only and imports nothing.

``pyforge.steward.dashboard`` owns the corridor's models (corridor loads, work
passports, the quarantine shelf, the audit log). The steward Dream and its
corridor capabilities put those records in the platform's PostgreSQL database
(operator ruling of 2026-11-21 on ``DW-steward-126-3-1``).
"""

from __future__ import annotations

STATION_APPS: tuple[str, ...] = ("pyforge.steward.dashboard",)
