"""``pyforge.marshal.cli`` -- the argparse dispatch tree, envelope
rendering, and exit-code emission (Structural Seed). Story 1.1 scaffolded
``cli/main.py`` with only ``--version``/``--help`` wired; Story 1.3 adds
the subparser tree and the first real subcommand, ``config``
(``cli/config.py``)."""

from __future__ import annotations
