"""The impure edge -- one adapter per port (Structural Seed, AD-4). Only
``harness_bmadloop.py`` exists this story (the AD-3 seam declaration); the
other adapters (``vcs_git``, ``observer_mux``, ``fs_local``,
``clock_system``, ``forge_gh``) are later stories' explicit scope.
``notify_file_desktop.py`` shipped in Story 3.7 (``NotifyPort``'s sole
implementation, AD-34). ``process_posix.py`` shipped in Story 2.1 and
retired in Story 14.4, its ``ProcessPort``/``PosixProcess`` moved to the
shared ``pyforge.core.process``."""

from __future__ import annotations
