"""`python -m pyforge.mason` — same entry point as the `mason` script."""

from .cli import main

if __name__ == "__main__":       # pragma: no cover
    raise SystemExit(main())
