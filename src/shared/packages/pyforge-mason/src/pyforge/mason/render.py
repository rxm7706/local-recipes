"""The sole formatter (AD-8): every command result flows through `write()`.

Story 1.4 adds the first real caller (`doctor`'s stub, wired in `cli.py`).
No use-case module exists yet that could call this directly -- when
`recipe.py`/`package.py`/`environment.py`/`doctor.py` land in later epics,
they must return data for `cli.py` to hand to `write()`, never format their
own output. `tests/meta/test_render_ownership.py` enforces the allowlist
(`cli.py`, `render.py` only) so that invariant is checked mechanically,
not by convention.

``render_json``'s ``json.dumps(doc, sort_keys=True, ensure_ascii=True,
indent=2, separators=(",", ": "))`` call mirrors the
``pyforge.warden.report.render_json`` precedent exactly, for the same
reason: identical inputs must produce byte-identical output (sorted keys
recursively, no locale-dependent float/ensure_ascii surprises). Unlike that
precedent, this module does NOT self-validate against a packaged JSON
Schema -- no schema file exists for Mason yet and this story's AC does not
call for one (see the story spec's Never clause).

``render_text`` is explicitly NON-CONTRACT, free-format output -- only the
JSON envelope is a contract (five keys: ``schema_version``, ``command``,
``status``, ``data``, ``errors``). It builds its lines from the same
inputs ``render_json`` renders, never a second, independently-maintained
view of the result.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, TextIO

# The JSON envelope's schema version. A plain "1" (not "1.0.0") -- there is
# no companion JSON Schema file yet to version alongside (see module
# docstring); this is the simplest correct value until one exists.
SCHEMA_VERSION = "1"


def render_json(
    command: str,
    status: str,
    data: Mapping[str, Any],
    errors: Sequence[Mapping[str, Any]],
) -> str:
    """Render the five-key envelope as one deterministic JSON document.

    Two calls with identical arguments return byte-identical strings --
    ``sort_keys=True`` makes key order irrelevant, and every other
    ``json.dumps`` argument is fixed rather than left to a default that
    could vary by interpreter/locale.
    """
    document = {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "status": status,
        "data": data,
        "errors": list(errors),
    }
    return json.dumps(
        document,
        sort_keys=True,
        ensure_ascii=True,
        indent=2,
        separators=(",", ": "),
    )


def render_text(
    command: str,
    status: str,
    data: Mapping[str, Any],
    errors: Sequence[Mapping[str, Any]],
) -> str:
    """Render a human-readable, explicitly NON-CONTRACT summary.

    One summary line (``<command>: <status>``), then one line per ``data``
    key (sorted, for the same determinism reason ``render_json`` sorts),
    then one line per error. Never schema-validated -- only
    ``render_json``'s document is the contract.
    """
    lines = [f"{command}: {status}"]
    for key in sorted(data):
        lines.append(f"  {key}: {data[key]}")
    for error in errors:
        identifier = error.get("identifier", "?")
        message = error.get("message", "")
        lines.append(f"  error: {identifier} -- {message}")
    return "\n".join(lines)


def write(
    fmt: str,
    stream: TextIO,
    command: str,
    status: str,
    data: Mapping[str, Any],
    errors: Sequence[Mapping[str, Any]],
) -> None:
    """The sole call site for both renderers (AD-8) -- ``render_text`` is
    never invoked directly by ``cli.py``.

    Writes the rendered text plus a single trailing newline to ``stream``
    and flushes it, so under ``--format json`` stdout carries exactly one
    JSON document (never buffered behind an unflushed stream at process
    exit).

    ``fmt`` values other than exactly ``"json"`` render as text -- the CLI's
    ``--format`` flag is argparse-``choices``-validated, but its
    ``MASON_FORMAT`` environment-variable form is not (Story 1.2 punted this
    exact validation to "Story 1.4's consumption site"). An out-of-choices
    env value falls back to the documented default rather than raising,
    matching ``_resolve_str``/``_resolve_bool``'s established
    invalid-value-falls-back-to-default philosophy -- there is no
    ``MasonError`` taxonomy yet (Story 1.3) to raise a typed error instead.
    """
    text = render_json(command, status, data, errors) if fmt == "json" \
        else render_text(command, status, data, errors)
    stream.write(text + "\n")
    stream.flush()
