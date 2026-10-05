"""Strip local-recipes-only CFE metadata before staged-recipes / feedstock push (G60, G62)."""

from __future__ import annotations

import re

_CFE_BLOCK_START = re.compile(r"^#### CFE metadata")
_CFE_EXTRA_KEY = re.compile(r"^  cfe-")


def strip_recipe_yaml_for_push(text: str) -> str:
    """Remove ``extra.cfe-*`` keys and bottom ``#### CFE …`` blocks; keep header and ``context:``."""
    lines = text.splitlines(keepends=True)
    kept: list[str] = []
    for line in lines:
        if _CFE_BLOCK_START.match(line.rstrip("\n")):
            break
        if _CFE_EXTRA_KEY.match(line):
            continue
        kept.append(line)
    while kept and kept[-1].strip() == "":
        kept.pop()
    body = "".join(kept)
    if body and not body.endswith("\n"):
        body += "\n"
    return body


def strip_conda_forge_yml_for_push(text: str) -> str:
    """Remove the bottom ``#### CFE metadata AND comments`` block from conda-forge.yml."""
    return strip_recipe_yaml_for_push(text)


_CFE_SURVIVOR = re.compile(
    r"^\s*(cfe-|#### CFE|# CFE metadata|# CFE comments)",
)


def assert_no_cfe_metadata_surfaces(text: str) -> None:
    """G62 grep gate — abort if CFE metadata keys or comment blocks remain."""
    for i, line in enumerate(text.splitlines(), start=1):
        if _CFE_SURVIVOR.match(line):
            raise ValueError(f"cfe metadata survived strip at line {i}: {line!r}")
