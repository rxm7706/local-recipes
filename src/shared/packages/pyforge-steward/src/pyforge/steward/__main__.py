"""`python -m pyforge.steward` — same entry point as the `steward` script."""

from .cli import main

if __name__ == "__main__":       # pragma: no cover
    raise SystemExit(main())
