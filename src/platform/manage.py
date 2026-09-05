#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys
from pathlib import Path


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    # CAP-3 locality: manage.py's default leaf is local development. setdefault
    # only — a production release that sets DJANGO_SETTINGS_MODULE=production
    # keeps COMPONENT_RUNTIME unset (fail-closed deployed).
    if os.environ.get("DJANGO_SETTINGS_MODULE") == "config.settings.local":
        os.environ.setdefault("COMPONENT_RUNTIME", "local")

    try:
        from django.core.management import execute_from_command_line  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(  # noqa: TRY003
            "Couldn't import Django. Are you sure it's installed and "  # noqa: EM101
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?",
        ) from exc

    # This allows easy placement of apps within the interior
    # platformapp directory.
    current_path = Path(__file__).parent.resolve()
    sys.path.append(str(current_path / "platformapp"))

    # CAP-2: instrument management commands too.
    from config.observability import configure_observability  # noqa: PLC0415

    # Story 41.4: configure_observability() reads the settings module first, so
    # a CAP-3 stage-1 refusal is this process's exit status rather than a debug
    # log (see that function's own note).
    configure_observability()

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
