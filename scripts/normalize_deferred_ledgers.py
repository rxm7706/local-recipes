#!/usr/bin/env python3
"""Normalize the TRACKED deferred-work ledgers so every entry is countable.

The five tracked ledgers grew four incompatible shapes, and 83 of 144 entries carry no id
at all — so they cannot be counted, cited from a board row, deduplicated across runs, or
individually marked resolved. That is why the console has no open-work surface: there was
nothing stable to render.

SCOPE IS DELIBERATELY MINIMAL. Every entry gets exactly two things:

  1. an ID heading  — `## DW-<scope>-<n> — <title>`
  2. a `status:` line — `open` unless the body already declares otherwise

The prose bodies are NOT rewritten. They are the value in these files (measured evidence,
file:line citations, reasoning that took whole review passes to produce), and a regex that
reflows them would quietly destroy exactly the thing worth keeping. Countability needs an id
and a status; it does not need the body reshaped.

WHY `DW-<scope>-<n>` AND NOT the sequential `DW-<seq>` of
`.claude/skills/bmad-loop-sweep/deferred-work-format.md`: that format governs the Tier-3
`implementation-artifacts/deferred-work.md`, which the orchestrator owns. The TRACKED twin
uses scoped ids, and promotion renames between the two — the convention pyforge-atlas's
ledger header already documents. It is not a style preference: 69 files cite scoped ids
outside the ledgers, individual ids up to 99 times, so renumbering would break every one.

`<scope>` is DERIVED from the entry's own `source_spec:` (e.g. `spec-1-1-package-scaffold…`
-> `1-1`), never invented, so the id says where the deferral came from and stays stable when
entries are reordered.

Usage:  python scripts/normalize_deferred_ledgers.py [--write]
Default is a dry run that reports what would change and rewrites nothing.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LEDGERS = sorted(REPO_ROOT.glob("_bmad-output/projects/*/planning-artifacts/deferred-work-ledger.md"))

# An entry heading that already carries an id, at any level the four shapes used.
RE_ID_HEAD = re.compile(r"^(#{2,4})\s+(DW-[A-Za-z0-9][A-Za-z0-9-]*)\s*[—:-]?\s*(.*)$")
# A grouping heading (warden's `## Deferred from: …`) — context, never an entry itself.
RE_GROUP = re.compile(r"^#{2,4}\s+Deferred from:", re.I)
RE_ANY_HEAD = re.compile(r"^#{1,6}\s")
# An anonymous entry: a top-level bullet opening a `source_spec:` field.
RE_ANON = re.compile(r"^-\s+source_spec:\s*(.*)$")
RE_STATUS = re.compile(r"^\s*status:\s*(\S.*)$", re.M)
RE_RESOLVED = re.compile(r"\*\*RESOLVED\b", re.I)
# `…/spec-1-1-package-scaffold-frozen-…md` -> `1-1`; falls back to the first slug chunk.
RE_SCOPE = re.compile(r"spec-([a-z0-9]+(?:-[a-z0-9]+)?)-")


def scope_from(source_spec: str) -> str:
    m = RE_SCOPE.search(source_spec)
    if m:
        return m.group(1).upper()
    m = re.search(r"([a-z0-9]+-[a-z0-9]+)", source_spec)
    return m.group(1).upper() if m else "X"


def title_from(body: str) -> str:
    """First clause of the summary, trimmed to something readable as a heading."""
    m = re.search(r"summary:\s*(.+)", body)
    text = (m.group(1) if m else body).strip().strip('"').strip()
    text = re.sub(r"\s+", " ", text)
    cut = re.split(r"(?<=[a-z0-9)])[.;—]\s", text, maxsplit=1)[0]
    return (cut[:96].rstrip() + "…") if len(cut) > 96 else cut or "untitled deferral"


def normalize(path: Path) -> tuple[str, dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    stats = {"entries": 0, "ids_added": 0, "status_added": 0, "already": 0}
    seq: dict[str, int] = {}
    i = 0
    while i < len(lines):
        ln = lines[i]
        m = RE_ID_HEAD.match(ln)
        anon = RE_ANON.match(ln) if not m and not RE_GROUP.match(ln) else None
        if not m and not anon:
            out.append(ln)
            i += 1
            continue

        # Collect the entry body. An ID'd entry runs to the next HEADING only: its own
        # `- source_spec:` line is a FIELD, not a new entry, and treating it as one split
        # every structured atlas entry in two and then "added" an id to the orphaned half
        # (103 entries and 46 new ids across a file where all 57 already had one).
        # An anonymous entry, having no heading of its own, ends at the next heading OR the
        # next anonymous entry.
        # An ID'd entry owns exactly ONE `- source_spec:` field; a SECOND one before the
        # next heading starts a new, unidentified entry. Ending an ID'd entry only at the
        # next heading made it swallow every anonymous entry that followed it — marshal's
        # seven structured-but-unheaded entries were absorbed into the `### DW-FU-1-1:`
        # block above them and never got ids. Caught by the detector, not by me.
        j = i + 1
        field_taken = bool(anon)
        while j < len(lines):
            if RE_ANY_HEAD.match(lines[j]):
                break
            if RE_ANON.match(lines[j]):
                if field_taken:
                    break
                field_taken = True
            j += 1
        body = "\n".join(lines[i:j])
        stats["entries"] += 1

        if m:
            out.append(ln)
            has_id = True
        else:
            scope = scope_from(anon.group(1))
            seq[scope] = seq.get(scope, 0) + 1
            ident = f"DW-{scope}-{seq[scope]}"
            if out and out[-1].strip():
                out.append("")   # a heading glued to the previous line is not a heading
            out.append(f"## {ident} — {title_from(body)}")
            out.append("")
            stats["ids_added"] += 1
            has_id = False
        out.extend(lines[i + 1:j] if has_id else lines[i:j])

        if RE_STATUS.search(body):
            stats["already"] += 1
        else:
            done = bool(RE_RESOLVED.search(body))
            out.append(f"  status: {'done (resolution recorded inline, date unknown)' if done else 'open'}")
            stats["status_added"] += 1
        i = j
    return "\n".join(out) + "\n", stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="apply changes (default: dry run)")
    args = ap.parse_args()
    total = {"entries": 0, "ids_added": 0, "status_added": 0, "already": 0}
    for f in LEDGERS:
        new, st = normalize(f)
        for k in total:
            total[k] += st[k]
        rel = f.relative_to(REPO_ROOT)
        changed = new != f.read_text(encoding="utf-8")
        print(f"{str(rel.parts[2]):18} entries={st['entries']:>3} "
              f"+ids={st['ids_added']:>3} +status={st['status_added']:>3} "
              f"had-status={st['already']:>3} {'CHANGED' if changed else 'unchanged'}")
        if args.write and changed:
            f.write_text(new, encoding="utf-8")
    print(f"\n{'TOTAL':18} entries={total['entries']:>3} "
          f"+ids={total['ids_added']:>3} +status={total['status_added']:>3} "
          f"had-status={total['already']:>3}")
    print("dry run — nothing written; pass --write to apply" if not args.write else "written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
