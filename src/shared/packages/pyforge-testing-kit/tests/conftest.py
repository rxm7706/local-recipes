"""The kit's own suite needs no session-wide setup.

Until Story 118.1 (spec-pyforge-testing-charter:CAP-7) this file put the host's portal package on ``sys.path``
and configured its web framework at session start, so no kit test collected on a root without the host. The one
module that needs the host, ``tests/unit/test_station_api_contract.py``, now does that setup in a module-scoped
fixture and is marked ``live_tree``; ``pyforge-core`` is a run-dependency of the kit, so it imports from the
environment with no path insertion.
"""
