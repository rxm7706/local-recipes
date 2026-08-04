"""The impure edge -- one adapter per port (Structural Seed, AD-4). Only
``harness_bmadloop.py`` exists this story (the AD-3 seam declaration); the
other adapters (``vcs_git``, ``process_posix``, ``observer_mux``,
``fs_local``, ``clock_system``, ``forge_gh``) are later stories' explicit
scope. ``notify_file_desktop.py`` shipped in Story 3.7 (``NotifyPort``'s
sole implementation, AD-34)."""

from __future__ import annotations
