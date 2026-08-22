#!/usr/bin/env python3
"""failure-catalog-generator — derive failure-catalog.yaml from SKILL.md's
gotcha corpus (Story 7.1, `spec-machine-checked-recipe-knowledge` CAP-1).

SKILL.md's "## Recipe Authoring Gotchas" section (`### G1.` .. `### G110.`) is
prose with no machine linkage to the checks that enforce it. This generator
is a deterministic (pure-function-of-SKILL.md-text) parser that emits one
row per gotcha to
``.claude/skills/conda-forge-expert/config/failure-catalog.yaml``:

  id                 "G<N>"
  title              the gotcha's heading text
  symptom_signature  greppable tokens (double-quoted error strings + backtick
                      code spans) pulled from the gotcha's **Symptom** paragraph
  enforced_by        ".claude/skills/conda-forge-expert/scripts/recipe_optimizer.py:<CODE>"
                      ONLY when the body contains the exact declarative phrase
                      "The optimizer's **<CODE>** check" AND <CODE> is a live
                      entry in recipe_optimizer.py's `code="..."` registry
                      (derived by regex from that script's source at generation
                      time -- never hand-copied here). Every other case is an
                      honest `null` -- the null rows ARE the backlog.

Two modes:
  (default)  write ``config/failure-catalog.yaml``
  --check    regenerate into memory, diff against the on-disk file, exit
             non-zero (with a diff) on mismatch; never writes

No wall-clock timestamp is emitted -- `source_sha256` (a hash of the
extracted gotcha-section text) is the only "derived from" anchor, so a
regeneration of an unchanged SKILL.md is byte-identical every time.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import io
import re
import sys
from pathlib import Path
from typing import Any

# Sibling helper — canonical path resolution shared across scripts/*.py.
# Guarded: an unconditional insert appends a duplicate every time the module
# is (re-)imported in a long-lived process.
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
from _paths import get_repo_root  # noqa: E402

from ruamel.yaml import YAML  # noqa: E402
from ruamel.yaml.scalarstring import DoubleQuotedScalarString as DQ  # noqa: E402

# --- relative paths (repo-root-relative; used both to locate inputs and to
# stamp the `enforced_by` pointer string) -------------------------------
SKILL_MD_REL = ".claude/skills/conda-forge-expert/SKILL.md"
OPTIMIZER_REL = ".claude/skills/conda-forge-expert/scripts/recipe_optimizer.py"
OUTPUT_REL = ".claude/skills/conda-forge-expert/config/failure-catalog.yaml"

SECTION_HEADING = "## Recipe Authoring Gotchas"
_TOP_HEADING_RE = re.compile(r"^## (?!#)")
_GOTCHA_HEADING_RE = re.compile(r"^### G(\d+)\. (.+)$")
_GOTCHA_PREFIX_RE = re.compile(r"^### G")
_ENFORCED_BY_RE = re.compile(r"The optimizer's \*\*([A-Z]+-[0-9]+)\*\* check")
_REGISTRY_CODE_RE = re.compile(r'code=["\']([A-Z]+-[0-9]+)["\']')
_SIGNATURE_TOKEN_RE = re.compile(r'"([^"\n]+)"|`([^`\n]+)`')
_SYMPTOM_LABEL_RE = re.compile(r"\*\*Symptom\*\*:")
_WHY_LABEL_RE = re.compile(r"\*\*Why\*\*:")
_BLANK_LINE_RE = re.compile(r"\n[ \t]*\n")
_FENCE_RE = re.compile(r"\s*```[^\n]*\n(.*?)```", re.DOTALL)

MAX_SIGNATURE_TOKENS = 8

CATALOG_HEADER = (
    "# GENERATED FILE — DO NOT HAND-EDIT.\n"
    "# Regenerate with: pixi run -e local-recipes generate-failure-catalog\n"
    "# Derived deterministically from .claude/skills/conda-forge-expert/SKILL.md's\n"
    '# "Recipe Authoring Gotchas" section. Hand edits are detectably wrong —\n'
    "# regenerating overwrites them; see tests/meta/test_failure_catalog_freshness.py.\n"
)


class CatalogError(RuntimeError):
    """SKILL.md's gotcha section could not be parsed."""


# --- extraction --------------------------------------------------------


def extract_gotcha_section(skill_md_text: str) -> str:
    """Return the ``## Recipe Authoring Gotchas`` section, heading through
    (but excluding) the next top-level ``## `` heading. Raises CatalogError
    if the section heading is absent."""
    lines = skill_md_text.splitlines(keepends=True)
    start_idx = None
    for i, line in enumerate(lines):
        if line.rstrip() == SECTION_HEADING:
            start_idx = i
            break
    if start_idx is None:
        raise CatalogError(
            f"SKILL.md: heading {SECTION_HEADING!r} not found — cannot "
            "locate the gotcha corpus."
        )
    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        if _TOP_HEADING_RE.match(lines[i]):
            end_idx = i
            break
    return "".join(lines[start_idx:end_idx])


def split_gotcha_entries(section_text: str) -> list[tuple[int, str, str]]:
    """[(gotcha number, title, body text)] in ascending numeric order.

    Raises CatalogError if zero ``### G<N>.`` entries are found, if a line
    looks like a gotcha heading (``### G...``) but doesn't fully match the
    ``### G<N>. <title>`` format, or if a gotcha number is repeated."""
    lines = section_text.splitlines(keepends=True)
    headings: list[tuple[int, int, str]] = []  # (line_idx, number, title)
    for i, line in enumerate(lines):
        stripped = line.rstrip("\n")
        m = _GOTCHA_HEADING_RE.match(stripped)
        if m:
            headings.append((i, int(m.group(1)), m.group(2).strip()))
        elif _GOTCHA_PREFIX_RE.match(stripped):
            raise CatalogError(
                f"SKILL.md: line {i + 1} of the gotcha section looks like a "
                "heading but doesn't match '### G<N>. <title>': "
                f"{stripped!r}"
            )
    if not headings:
        raise CatalogError(
            "SKILL.md: zero '### G<N>.' entries found under "
            f"{SECTION_HEADING!r} — gotcha-heading format is inconsistent."
        )
    seen_numbers: set[int] = set()
    for _, number, _ in headings:
        if number in seen_numbers:
            raise CatalogError(
                f"SKILL.md: duplicate gotcha number G{number} found under "
                f"{SECTION_HEADING!r} — each gotcha number must be unique."
            )
        seen_numbers.add(number)
    entries: list[tuple[int, str, str]] = []
    for idx, (line_idx, number, title) in enumerate(headings):
        body_start = line_idx + 1
        body_end = headings[idx + 1][0] if idx + 1 < len(headings) else len(lines)
        body = "".join(lines[body_start:body_end])
        entries.append((number, title, body))
    entries.sort(key=lambda e: e[0])
    return entries


def extract_optimizer_registry(optimizer_source: str) -> set[str]:
    """The live set of check codes, regex-scanned from recipe_optimizer.py's
    source text (never from its docstring, never hand-copied)."""
    return set(_REGISTRY_CODE_RE.findall(optimizer_source))


def extract_enforced_by(body: str, registry: set[str]) -> str | None:
    """`.../recipe_optimizer.py:<CODE>` iff the body contains the exact
    declarative phrase exactly once (or repeated with the SAME code) and
    <CODE> is live in `registry`. No phrase, an unresolvable code, or the
    phrase pointing at more than one distinct code all resolve to None."""
    codes = _ENFORCED_BY_RE.findall(body)
    if not codes:
        return None
    unique_codes = set(codes)
    if len(unique_codes) != 1:
        return None
    code = next(iter(unique_codes))
    if code not in registry:
        return None
    return f"{OPTIMIZER_REL}:{code}"


def _signature_tokens(text: str) -> list[str]:
    """Double-quoted substrings and backtick code spans, in order of
    appearance, deduped, capped at MAX_SIGNATURE_TOKENS."""
    tokens: list[str] = []
    for m in _SIGNATURE_TOKEN_RE.finditer(text):
        value = (m.group(1) if m.group(1) is not None else m.group(2)).strip()
        if not value or value in tokens:
            continue
        tokens.append(value)
        if len(tokens) >= MAX_SIGNATURE_TOKENS:
            break
    return tokens


def _symptom_paragraph(body: str) -> str | None:
    """The **Symptom**: paragraph text, through the next **Why**: label or a
    blank line (whichever comes first). If the paragraph's prose trails off
    without a full sentence (ends with ':'), and a fenced code block
    immediately follows, that block's content is appended as evidence."""
    label = _SYMPTOM_LABEL_RE.search(body)
    if label is None:
        return None
    rest = body[label.end():]
    why = _WHY_LABEL_RE.search(rest)
    blank = _BLANK_LINE_RE.search(rest)
    boundaries = [m.start() for m in (why, blank) if m is not None]
    end = min(boundaries) if boundaries else len(rest)
    paragraph = rest[:end]
    tail = rest[end:]
    if paragraph.strip().endswith(":"):
        fence = _FENCE_RE.match(tail)
        if fence:
            paragraph = paragraph + "\n" + fence.group(1)
    return paragraph


def extract_symptom_signature(body: str) -> list[str]:
    """Signature tokens for one gotcha body. Prefers the **Symptom**:
    paragraph; falls back to scanning the whole body when there is no
    **Symptom**: label (a handful of gotchas use a Question/Answer shape
    instead) or when the paragraph itself yields nothing extractable."""
    paragraph = _symptom_paragraph(body)
    if paragraph is not None:
        tokens = _signature_tokens(paragraph)
        if tokens:
            return tokens
    return _signature_tokens(body)


# --- catalog assembly ---------------------------------------------------


def build_catalog(skill_md_text: str, optimizer_source: str) -> dict[str, Any]:
    """The full catalog dict: {"source_sha256": ..., "rows": [...]}.

    Raises CatalogError on an unparseable SKILL.md gotcha section.
    """
    section_text = extract_gotcha_section(skill_md_text)
    entries = split_gotcha_entries(section_text)
    registry = extract_optimizer_registry(optimizer_source)

    rows = []
    for number, title, body in entries:
        signature = extract_symptom_signature(body)
        if not signature:
            raise CatalogError(
                f"G{number}: extracted zero symptom_signature tokens — "
                "SKILL.md body may need a quoted/backtick span for grep "
                "matching."
            )
        rows.append({
            "id": f"G{number}",
            "title": title,
            "symptom_signature": signature,
            "enforced_by": extract_enforced_by(body, registry),
        })

    source_sha256 = hashlib.sha256(section_text.encode("utf-8")).hexdigest()
    return {"source_sha256": source_sha256, "rows": rows}


def _make_yaml() -> YAML:
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.width = 4096  # never soft-wrap a long title/signature line
    yaml.indent(mapping=2, sequence=4, offset=2)

    def _represent_none(representer, data):
        return representer.represent_scalar("tag:yaml.org,2002:null", "null")

    yaml.representer.add_representer(type(None), _represent_none)
    return yaml


def render_catalog(catalog: dict[str, Any]) -> str:
    """The full file text: header comment block + the YAML document.
    A pure function of `catalog` — no timestamps, no non-deterministic
    ordering — so byte-identical input always yields byte-identical output.
    """
    doc: dict[str, Any] = {
        "source_sha256": DQ(catalog["source_sha256"]),
        "rows": [
            {
                "id": row["id"],
                "title": DQ(row["title"]),
                "symptom_signature": [DQ(t) for t in row["symptom_signature"]],
                "enforced_by": DQ(row["enforced_by"]) if row["enforced_by"] else None,
            }
            for row in catalog["rows"]
        ],
    }
    buf = io.StringIO()
    _make_yaml().dump(doc, buf)
    return CATALOG_HEADER + buf.getvalue()


# --- CLI -----------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Derive failure-catalog.yaml from SKILL.md's Recipe "
                     "Authoring Gotchas corpus. Pure function of SKILL.md's "
                     "text; never modifies SKILL.md or recipe_optimizer.py."
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Regenerate into memory and diff against the on-disk catalog. "
             "Exit 0 if identical, non-zero (with a diff) otherwise. Never "
             "writes.",
    )
    args = parser.parse_args(argv)

    repo_root = get_repo_root()
    if repo_root is None:
        print("failure_catalog_generator: could not resolve the repo root "
              "(see _paths.get_repo_root)", file=sys.stderr)
        return 1

    skill_md_path = repo_root / SKILL_MD_REL
    optimizer_path = repo_root / OPTIMIZER_REL
    output_path = repo_root / OUTPUT_REL

    try:
        skill_md_text = skill_md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"failure_catalog_generator: cannot read {skill_md_path}: {exc}",
              file=sys.stderr)
        return 1
    try:
        optimizer_source = optimizer_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"failure_catalog_generator: cannot read {optimizer_path}: {exc}",
              file=sys.stderr)
        return 1

    try:
        catalog = build_catalog(skill_md_text, optimizer_source)
    except CatalogError as exc:
        print(f"failure_catalog_generator: {exc}", file=sys.stderr)
        return 1

    rendered = render_catalog(catalog)

    if args.check:
        if not output_path.exists():
            print(f"failure_catalog_generator --check: {output_path} does "
                  "not exist yet — run without --check to create it.",
                  file=sys.stderr)
            return 1
        try:
            on_disk = output_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"failure_catalog_generator: cannot read {output_path}: {exc}",
                  file=sys.stderr)
            return 1
        if on_disk == rendered:
            print(f"failure_catalog_generator --check: {output_path.name} "
                  f"is in sync with SKILL.md ({len(catalog['rows'])} rows).")
            return 0
        diff = "".join(difflib.unified_diff(
            on_disk.splitlines(keepends=True),
            rendered.splitlines(keepends=True),
            fromfile=str(output_path),
            tofile="<regenerated>",
        ))
        print("failure_catalog_generator --check: DRIFT DETECTED — the "
              "committed catalog does not match a fresh regeneration.\n"
              + diff, file=sys.stderr)
        return 1

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    except OSError as exc:
        print(f"failure_catalog_generator: cannot write {output_path}: {exc}",
              file=sys.stderr)
        return 1
    print(f"failure_catalog_generator: wrote {output_path} "
          f"({len(catalog['rows'])} rows).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
