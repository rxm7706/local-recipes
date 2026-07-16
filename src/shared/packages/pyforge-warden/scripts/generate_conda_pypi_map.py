"""Converts the conda-forge-expert atlas ``export-purls`` TSV into the
packaged ``data/conda_pypi_map.json`` bundled identity map (Story 2.1).

Dev-only maintenance script -- not part of the installed ``pyforge.warden``
package. Regenerate the map by running the atlas ``export-purls`` CLI (via
the conda-forge-expert skill, per CLAUDE.md Rule 1) and pointing this script
at the resulting ``purls_conda-pypi_mapped.tsv``.

Usage::

    python scripts/generate_conda_pypi_map.py <tsv-path> [--out <json-path>]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

_DEFAULT_OUT = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "pyforge"
    / "warden"
    / "data"
    / "conda_pypi_map.json"
)

_REQUIRED_COLUMNS = frozenset(
    {"conda_purl", "pypi_purl", "match_source", "match_confidence"}
)

# Trust ranking (higher = more trusted) -- the only two confidence tiers a
# bundled entry may carry (a "none"-match_source row never reaches here).
# On a duplicate conda_name, the higher-ranked row wins (never silently
# downgrade an already-resolved identity because a later, weaker row
# happened to iterate last).
_CONFIDENCE_RANK = {"likely": 0, "verified": 1}


def _purl_name(purl: str) -> str:
    """The bare package name from a ``pkg:<type>/<name>[@version][?qualifiers]`` purl."""
    without_qualifiers = purl.split("?", 1)[0]
    without_version = without_qualifiers.split("@", 1)[0]
    return without_version.rsplit("/", 1)[-1]


def convert(tsv_path: Path) -> dict[str, dict[str, str]]:
    """Build the conda-name-keyed map from a ``purls_conda-pypi_mapped.tsv`` file.

    Only rows with a real ``pypi_purl`` (``match_source != "none"``) are
    included -- an absent key is already the correct "no candidate" signal,
    so there is no need to bundle the miss rows. A row that is structurally
    malformed (missing a required column, a short/truncated row, an
    unrecognized ``match_confidence`` tier, or an empty extracted name) is
    skipped and counted -- never guessed, never a crash. On a duplicate
    ``conda_name``, the higher-trust row wins.
    """
    entries: dict[str, dict[str, str]] = {}
    skipped = 0
    with tsv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        header = set(reader.fieldnames or ())
        if not _REQUIRED_COLUMNS <= header:
            raise ValueError(
                f"{tsv_path}: missing required column(s) "
                f"{sorted(_REQUIRED_COLUMNS - header)}"
            )
        for row in reader:
            if any(row.get(col) is None for col in _REQUIRED_COLUMNS):
                skipped += 1  # a short/truncated row -- DictReader fills
                continue  # missing trailing fields with None
            match_source = row["match_source"]
            if match_source == "none":
                continue
            match_confidence = row["match_confidence"]
            if match_confidence not in _CONFIDENCE_RANK:
                skipped += 1
                continue
            conda_name = _purl_name(row["conda_purl"])
            pypi_name = _purl_name(row["pypi_purl"])
            if not conda_name or not pypi_name:
                skipped += 1
                continue
            existing = entries.get(conda_name)
            if existing is not None and (
                _CONFIDENCE_RANK[existing["match_confidence"]]
                >= _CONFIDENCE_RANK[match_confidence]
            ):
                continue
            entries[conda_name] = {
                "pypi_name": pypi_name,
                "match_source": match_source,
                "match_confidence": match_confidence,
            }
    if skipped:
        print(f"skipped {skipped} malformed/unrecognized row(s)", file=sys.stderr)
    return dict(sorted(entries.items()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tsv_path", type=Path, help="path to purls_conda-pypi_mapped.tsv")
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT, help="output JSON path")
    args = parser.parse_args()

    entries = convert(args.tsv_path)
    args.out.write_text(
        json.dumps(entries, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(entries)} entries to {args.out}")


if __name__ == "__main__":
    main()
