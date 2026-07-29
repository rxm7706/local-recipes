"""pyforge-atlas

Importing this package (or any of its submodules) pins pandas' process-wide
``future.infer_string`` option to ``False`` — see AUD-ATLAS-011 below.
"""

import warnings

import pandas as _pd

# AUD-ATLAS-011: pandas 3.0's default `str` dtype uses `NaN` as its missing-value sentinel
# instead of `None`, breaking None-identity (dict-key lookups, `is None`, `in` membership)
# for string-like columns built from a plain Python list/dict -- including inside Ibis's
# own DuckDB->pandas result conversion, which is why this pin also fixes the semantic-layer
# BSL query results, not just this package's own pipeline code. Pre-existing nullable
# extension dtypes (`Int64`, `boolean`, explicit `string[pyarrow]`) are untouched -- they
# already use `pd.NA` and were never affected.
#
# The option itself is pandas's own documented pandas-3.0 migration escape hatch (it will
# not necessarily survive a future pandas release, per its own docstring) -- guard against
# that so a routine dependency bump degrades to the pre-fix pandas-3.0 default rather than
# crashing this package's import.
try:
    _pd.set_option("future.infer_string", False)
except (_pd.errors.OptionError, ValueError):  # pragma: no cover - only if a future pandas removes/locks it
    warnings.warn(
        "pyforge.atlas could not pin pandas' future.infer_string option off; "
        "string-like columns will use NaN (not None) as their missing-value sentinel, "
        "re-exposing the AUD-ATLAS-011 NULL-identity regressions.",
        RuntimeWarning,
        stacklevel=2,
    )

__version__ = "0.1.0"  # keep in sync with pyproject.toml / pixi.toml [package] version
