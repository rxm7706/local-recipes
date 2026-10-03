#!/usr/bin/env python3
"""Mutation-only residual: stamp the spec-surface drift baseline.

Story 6.9 ("the `scripts/` shims retire") ported this script's own
read-only VERDICT — coverage (every tracked file governed by a spec
surface or explicitly allowlisted) and drift (a governed file changed
without its spec's `.memlog.md` moving) — into
`pyforge.doctor.sources.chain::gather_spec_surface`
(`python -m pyforge.doctor.sources spec-surface`). That port is the one
place the verdict lives now; this file is NOT a detector any more (no
`DETECTOR = {...}` marker, and `scripts/detectors.py`'s AST scan correctly
no longer discovers it).

What survives here, and why it could not simply move with the rest: Doctor
sources are deliberately READ-ONLY gathers (Charter §6 — the producing
station keeps the operational guard; only Doctor holds the verdict), so
`gather_spec_surface` never got a `--write-baseline`/`--spec NAME`
mutation path, and nothing else in the repo has one either. That capability
is live and depended on today — `_bmad-output/projects/pyforge-marshal/
SYNC-RUNBOOK.md` Step 3, `CLAUDE.md`'s own Sync-loop section, and
`spec-surface-drift-reconciliation` (an ACTIVE, `in-progress` Marshal
spec) all instruct or require `--write-baseline --spec NAME` as a real,
working command. So it stays here, reduced to exactly that: compute the
same live "what does every governed spec's contract + file set look like
right now" state the read-only port also computes internally, and (only
when asked) merge it into the committed `scripts/.spec-surface-baseline.json`.

Story 12.5 closed the concurrent-stamp race (CAP-5's `DW-13-5-2`, recorded
in the atlas ledger as `DW-13-5-3`): the whole read-modify-write span now
holds an advisory flock on a sidecar `.spec-surface-baseline.json.lock`,
and the write itself is atomic (temp file + `os.replace`), so two
concurrent `--write-baseline` invocations serialize instead of silently
clobbering each other, and a concurrent reader never sees a torn baseline.
(A full, `--spec`-less stamp still deliberately replaces EVERY entry with
its own pre-lock live snapshot -- that is its documented accept-everything
semantics, unchanged by the serialization; only the scoped path reads and
merges.)

**What the lock does NOT span (DW-12-5-3).** `fcntl.flock` is per-inode, so
it serializes stamps against ONE baseline file. Two git worktrees of this
repo each hold their OWN `scripts/.spec-surface-baseline.json` at their own
inode, and a stamp in each one takes a different lock: both succeed, and the
two divergent files meet later as a git merge conflict, which no advisory
lock can prevent or detect. That is the documented boundary of this
serialization, not a gap in it -- resolve such a conflict by re-stamping the
specs each side reconciled, never by hand-merging the JSON.

**Refusals that leave the baseline byte-identical.** A corrupt committed
baseline is a diagnostic naming the file and the recovery path, exit 1,
never an `except -> {}` fallback that silently turns a scoped stamp into a
full one (DW-FU-12-5). A `--spec`-less full stamp that discovers zero Specs
over a non-empty baseline refuses rather than wiping it (DW-FU-12-5-2). A
spec whose `surface:` declares nothing readable is never stamped, scoped or
not (DW-FU-6-6-9).

Marshal Story 82.3 (DW-9-1-1): a SCOPED stamp no longer accepts a path
nobody narrated. A `--spec NAME` stamp merges every file NAME's surface
matches, so a drifted file under a broad glob was absorbed as reconciled with
no trace. Now, under the same lock, a path that differs from NAME's baseline
entry (changed, added or removed) is reconciled only when it is named with
`--accept PATH`, or the spec's contract hash moved since the baseline AND the
spec's `.memlog.md` text names the path (the rule `gather_spec_surface` reads
as clean; a memlog that names the path but did not move reads as `drift`, so
it does not count here either). Any other differing path refuses the whole
stamp -- exit 1, baseline untouched, every path listed with the explicit form
that accepts it. A spec with no usable baseline entry stamps as before, and
the unscoped `--write-baseline` is unchanged.

Usage (plain `python`, no pixi task -- the `spec-surface-check` pixi task
invokes the dispatcher below instead, which does not understand this flag):
        python scripts/spec_surface_check.py --write-baseline [--spec NAME ...] [--accept PATH ...]
Verdict (coverage/drift/blindness, unchanged behavior):
        pixi run -e local-recipes spec-surface-check
        python -m pyforge.doctor.sources spec-surface
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

# Explicit opt-out: this file still matches detectors.py's `*_check.py` glob
# by name (kept for doc/CLI continuity), but Story 6.9 reduced it to a
# mutation-only residual -- it is not a detector and must not trip the
# registry's "looks like one but declares nothing" gap.
DETECTOR = None

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_GLOB = "_bmad-output/projects/*/planning-artifacts/specs/spec-*/SPEC.md"
BASELINE = REPO_ROOT / "scripts" / ".spec-surface-baseline.json"


#: `chain.py`'s own `_GLOB_METACHARS`/`_SURFACE_DIR_SUFFIX`, restated (this
#: script must stay stdlib-only and cannot import the installed package).
#: DW-FU-12-4: a glob-less trailing-slash entry governs that directory's
#: subtree. The stamp and the verdict MUST agree on what a surface covers --
#: a stamp that read `dir/` as matching nothing would write a baseline the
#: verdict then reads as a storm of `drift ... added`.
_GLOB_METACHARS = frozenset("*?")
_SURFACE_DIR_SUFFIX = "**"


def glob_to_re(pattern: str) -> re.Pattern:
    if pattern.endswith("/") and not (_GLOB_METACHARS & set(pattern)):
        pattern += _SURFACE_DIR_SUFFIX
    out, i = [], 0
    while i < len(pattern):
        c = pattern[i]
        if pattern[i:i + 2] == "**":
            out.append(".*")
            i += 2
        elif c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + "$")


class SurfaceUnevaluable(Exception):
    """`chain.py`'s own `SurfaceUnevaluable`, restated: a SPEC.md declares
    `surface:` but no glob can be read from it (DW-FU-6-6-9). The read-only
    port turns this into one `spec-surface-unevaluable` WARN; here it refuses
    the stamp for that spec, since a baseline written from an unreadable
    surface records "governs nothing" as if it were reconciled."""


def _strip_surface_comment(value: str) -> str:
    """`value` with a trailing `#` comment removed -- only one starting a word
    OUTSIDE any quoted run (`chain.py::_strip_surface_comment`)."""
    quote = ""
    for i, ch in enumerate(value):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or value[i - 1] in " \t"):
            return value[:i]
    return value


def _unquote_surface(token: str) -> str:
    """One matched pair of surrounding YAML quotes removed
    (`chain.py::_unquote_surface`)."""
    token = token.strip()
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        return token[1:-1]
    return token


def _split_flow_items(inner: str) -> list[str]:
    """A flow sequence's body split on the commas OUTSIDE any quoted run
    (`chain.py::_split_flow_items`)."""
    items, buf, quote = [], [], ""
    for ch in inner:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = ""
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch == ",":
            items.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    items.append("".join(buf))
    return items


def _surface_flow_sequence(value: str) -> list[str] | None:
    """A `[a, "b"]` flow sequence's items, `[]` for an explicit empty one, or
    `None` when `value` is not a flow sequence (`chain.py` twin)."""
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        return None
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [g for g in (_unquote_surface(p) for p in _split_flow_items(inner)) if g]


def parse_surface(spec_md: Path) -> tuple[list[str], list[str], str]:
    """(`surface:` globs, `surface-drift-exclude:` globs, drift mode) from
    SPEC.md frontmatter -- the ground truth `--write-baseline` stamps against,
    so it must read the contract identically to the read-only port
    (`chain.py::_parse_surface`, whose docstring carries the full rationale).

    DW-FU-6-6-9: a block sequence item at any indent, a quoted item, a flow
    sequence and a scalar are all read; a `surface:` that yields no glob and
    was not written as an explicit `[]` raises `SurfaceUnevaluable`."""
    globs, excludes, drift = [], [], "memlog"
    surface_declared = surface_explicitly_empty = False
    in_fm, section = False, None
    for line in spec_md.read_text(encoding="utf-8").splitlines():
        if line.strip() == "---":
            if in_fm:
                break
            in_fm = True
            continue
        if not in_fm:
            continue
        stripped = line.strip()
        if section and (stripped.startswith("- ") or stripped == "-"):
            item = _unquote_surface(_strip_surface_comment(stripped[1:]))
            if item:
                (globs if section == "surface" else excludes).append(item)
            continue
        if section and (not stripped or stripped.startswith("#")):
            continue
        section = None
        # Frontmatter keys sit at column 0; an indented `surface:` belongs to
        # some other key's mapping and is not this contract.
        key, sep, raw = line.partition(":")
        if not sep or key not in ("surface", "surface-drift-exclude", "surface-drift"):
            continue
        value = _strip_surface_comment(raw).strip()
        if key == "surface-drift":
            drift = _unquote_surface(value)
            continue
        target = globs if key == "surface" else excludes
        if key == "surface":
            surface_declared = True
        flow = _surface_flow_sequence(value)
        if flow is not None:
            target.extend(flow)
            if key == "surface" and not flow:
                surface_explicitly_empty = True
            continue
        if value:
            target.append(_unquote_surface(value))
            continue
        section = "surface" if key == "surface" else "exclude"
    if surface_declared and not globs and not surface_explicitly_empty:
        raise SurfaceUnevaluable(
            f"{spec_md.name} declares surface: but no glob could be read from it "
            f"— write one `- <glob>` per line, or an explicit `surface: []` to "
            f"say it governs nothing"
        )
    return globs, excludes, drift


def tracked_files() -> list[str]:
    """Every tracked path, read the way `chain.py::_tracked_files` reads it
    (DW-FU-6-6-4): `-c core.quotePath=false` so a non-ASCII byte arrives
    literal instead of C-quoted and octal-escaped, and `-z` so the fields
    split on NUL. A quoted path matches no glob, so the stamp and the verdict
    would otherwise disagree about which files a surface governs."""
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "-c", "core.quotePath=false", "ls-files", "-z"],
        capture_output=True, text=True, check=True).stdout
    return [path for path in out.split("\0") if path]


def sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def contract_hash(s: dict) -> str:
    h = sha1(s["memlog"]) if s["memlog"].exists() else ""
    if s["drift"].startswith("sentinel:"):
        sentinel = REPO_ROOT / s["drift"].split(":", 1)[1].strip()
        h += "+" + (sha1(sentinel) if sentinel.is_file() else "missing")
    return h


def _live_state(unevaluable: dict[str, str] | None = None) -> dict[str, dict]:
    """Every spec's CURRENT `{memlog, files}` baseline entry -- the ground
    truth `--write-baseline` merges into the committed file. Mirrors
    `gather_spec_surface`'s own internal computation (Doctor's read-only
    port), which is a deliberate, unavoidable duplication: the verdict and
    the stamp must agree on what "current" means, and Doctor's own gather
    cannot write, so this is not one function two ways -- it is the one
    remaining mutation caller of the same read.

    A spec whose `surface:` is unevaluable (DW-FU-6-6-9) is recorded in
    `unevaluable` (when a dict is passed) and left OUT of the returned state
    entirely, so it can never be stamped: a baseline written from a surface
    nobody could read would record "this spec governs nothing" as a
    reconciled fact. `main()` refuses on any such spec in scope."""
    specs: dict[str, dict] = {}
    for spec_md in sorted(REPO_ROOT.glob(SPEC_GLOB)):
        # Key by <project>/<spec-dir>, never the bare dir name -- the same
        # slug can legitimately exist in two projects, and a bare-name key
        # would silently drop one surface.
        project = spec_md.relative_to(REPO_ROOT).parts[2]
        name = f"{project}/{spec_md.parent.name}"
        try:
            globs, excludes, drift = parse_surface(spec_md)
        except SurfaceUnevaluable as exc:
            if unevaluable is not None:
                unevaluable[name] = str(exc)
            continue
        specs[name] = {
            "spec": spec_md,
            "globs": globs,
            "drift": drift,
            "exclude": set(excludes),
            "res": [glob_to_re(g) for g in globs],
            "memlog": spec_md.parent / ".memlog.md",
        }

    files = tracked_files()
    governed: dict[str, list[str]] = {}
    for f in files:
        for n, s in specs.items():
            if any(r.match(f) for r in s["res"]):
                governed.setdefault(n, []).append(f)

    return {
        name: {
            "memlog": contract_hash(s),
            "files": {} if s["drift"] == "exempt" else
                     {f: sha1(REPO_ROOT / f) for f in sorted(governed.get(name, []))
                      if f not in s["exclude"] and (REPO_ROOT / f).is_file()},
        }
        for name, s in specs.items()
    }


class BaselineCorrupt(Exception):
    """The committed baseline exists but is not the `{name: entry}` JSON
    object every read path assumes (DW-FU-12-5).

    Deliberately NOT an `except -> {}` fallback. Collapsing a corrupt
    baseline to `{}` makes a scoped stamp's merge start from nothing, so the
    one spec named is written and EVERY other spec's entry is dropped -- the
    stamp silently becomes the full, accept-everything stamp it exists to
    avoid, at exit 0. The message names the file and the recovery path
    instead, and nothing is written."""


def _read_baseline() -> dict:
    """The committed baseline, `{}` only when the file genuinely does not
    exist. Raises `BaselineCorrupt` when it exists and cannot be read as a
    JSON object (DW-FU-12-5) -- `main()` turns that into a diagnostic and a
    non-zero exit, never a silent empty merge base."""
    if not BASELINE.exists():
        return {}
    try:
        data = json.loads(BASELINE.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BaselineCorrupt(
            f"{BASELINE.relative_to(REPO_ROOT)} exists but could not be read as "
            f"JSON ({exc.__class__.__name__}: {exc}); nothing written. Recover it "
            f"from git (`git checkout -- {BASELINE.relative_to(REPO_ROOT)}`), then "
            f"re-stamp the spec you reconciled with --write-baseline --spec NAME"
        ) from exc
    if not isinstance(data, dict):
        raise BaselineCorrupt(
            f"{BASELINE.relative_to(REPO_ROOT)} holds a JSON "
            f"{type(data).__name__}, not the expected object of "
            f"{{spec: {{memlog, files}}}} entries; nothing written. Recover it "
            f"from git (`git checkout -- {BASELINE.relative_to(REPO_ROOT)}`), then "
            f"re-stamp the spec you reconciled with --write-baseline --spec NAME"
        )
    return data


@contextmanager
def _baseline_lock():
    # Lock the SIDECAR, never the baseline itself -- `_write_baseline`'s
    # os.replace swaps the baseline's inode, so a lock held on the baseline
    # would not exclude the next locker. Holding an advisory flock across the
    # whole read -> merge -> write span closes the DW-13-5-2/DW-13-5-3
    # lost-write race. No timeout, no staleness detection, no retry, and the
    # lockfile is never unlinked (unlink-while-others-wait recreates the
    # race) -- the herald/marshal precedent (pyforge.herald.locking,
    # fs_local.acquire_advisory_lock) mirrored inline, since this script must
    # stay stdlib-only. Path resolved here at call time so the sidecar always
    # sits beside whatever BASELINE currently points at (the test harness
    # repoints REPO_ROOT in a patched copy of this script, which moves
    # BASELINE and the sidecar together).
    fd = os.open(BASELINE.with_name(BASELINE.name + ".lock"),
                 os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)  # closing the fd releases the flock


def _write_baseline(merged: dict) -> None:
    # Atomic: sibling temp file + os.replace, so the read-only Doctor
    # detector never sees a torn baseline. The fixed .tmp name is safe
    # because it is only ever written under _baseline_lock().
    tmp = BASELINE.with_name(BASELINE.name + ".tmp")
    tmp.write_text(json.dumps(merged, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    os.replace(tmp, BASELINE)


class StampAborted(Exception):
    """A stamp refused for a reason that needs no per-path rendering -- its
    `str()` IS the stderr text. Raised inside the locked section, before any
    write, so the baseline is left byte-identical."""


class StampRefused(Exception):
    """A scoped stamp found paths that differ from a spec's baseline entry and
    are not reconciled (Story 82.3). Raised inside the locked section, before
    any write, so the baseline is left byte-identical."""

    def __init__(self, refusals: list[tuple[str, str, str]]) -> None:
        super().__init__(f"{len(refusals)} unreconciled path(s)")
        self.refusals = refusals

    def render(self) -> str:
        """The stderr text: one `NAME: PATH (what)` line per path, then, per
        spec, the explicit command that accepts exactly those paths."""
        by_name: dict[str, list[str]] = {}
        lines = [
            "refusing to stamp: these path(s) differ from the spec's baseline "
            "and its memlog does not name them (the memlog must move AND name "
            "the path):"
        ]
        for name, path, what in self.refusals:
            lines.append(f"  {name}: {path} ({what})")
            by_name.setdefault(name, []).append(path)
        lines.append("reconcile the spec's memlog, or accept the path(s) explicitly:")
        for name, paths in by_name.items():
            accepts = " ".join(f"--accept {path}" for path in paths)
            lines.append(
                f"  python scripts/spec_surface_check.py --write-baseline --spec {name} {accepts}"
            )
        lines.append("baseline untouched")
        return "\n".join(lines)


def _memlog_text(name: str) -> str:
    """The raw text of spec NAME's `.memlog.md` (`<project>/<spec-dir>`, the
    file beside its SPEC.md) -- what `gather_spec_surface` tests a path's
    mention against; absent or unreadable reads as empty."""
    project, _, spec_dir = name.partition("/")
    memlog = (REPO_ROOT / "_bmad-output" / "projects" / project
              / "planning-artifacts" / "specs" / spec_dir / ".memlog.md")
    try:
        return memlog.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _unreconciled_paths(name: str, base: dict, cur: dict,
                        accept: frozenset[str]) -> list[tuple[str, str]]:
    """`(path, changed|added|removed)` for every path where spec NAME's live
    state differs from its baseline entry `base` and nothing reconciles it:
    not `--accept`ed, and not (contract hash moved since the baseline AND the
    memlog text names the path) -- the same clean-pass bar
    `gather_spec_surface` applies, so "moved but silent" and "names it but did
    not move" both stay unreconciled."""
    base_files = base.get("files") if isinstance(base.get("files"), dict) else {}
    moved = base["memlog"] != cur["memlog"]
    named = _memlog_text(name) if moved else ""
    out: list[tuple[str, str]] = []
    for path in sorted(set(base_files) | set(cur["files"])):
        old, new = base_files.get(path), cur["files"].get(path)
        if old == new or path in accept:
            continue
        if moved and path in named:
            continue
        out.append((path, "changed" if old and new else ("added" if new else "removed")))
    return out


def _stamp_baseline(spec_names: list[str] | None, current: dict[str, dict],
                    accept: frozenset[str] = frozenset()) -> str:
    """The locked critical section: read -> merge -> write, fully serialized
    against every other concurrent stamp. Returns the scope message. A scoped
    stamp raises `StampRefused` (nothing written) when a named spec has a
    differing path that is neither `accept`ed nor narrated on its memlog."""
    with _baseline_lock():
        # S-13.1 -- SCOPED stamping. Stamping every spec in one write made the
        # sanctioned fix for a single `[no-baseline]` unusable: it necessarily
        # accepted every OTHER spec's pending drift as correct, so the honest
        # move was to leave the finding standing. With --spec, one spec
        # reconciles in isolation.
        if spec_names:
            # MERGE, never rewrite: building from `current` alone would
            # silently drop every spec this invocation did not name.
            merged = _read_baseline()
            # Story 82.3 (DW-9-1-1): check EVERY named spec before writing
            # any, so one refusal stamps none. A spec with no usable baseline
            # entry has no per-path diff to judge and stamps as before.
            refusals: list[tuple[str, str, str]] = []
            for name in sorted(set(spec_names)):
                base = merged.get(name)
                if not isinstance(base, dict) or not isinstance(base.get("memlog"), str):
                    continue
                refusals.extend((name, path, what) for path, what
                                in _unreconciled_paths(name, base, current[name], accept))
            if refusals:
                raise StampRefused(refusals)
            for name in spec_names:
                merged[name] = current[name]
            scope = f"{len(set(spec_names))} spec(s): {', '.join(sorted(set(spec_names)))}"
        else:
            # DW-FU-12-5-2: a full stamp replaces the WHOLE baseline with its
            # own live snapshot. Discovery returning zero Specs over a
            # non-empty committed baseline is never a real "the repo governs
            # nothing now" -- it is a run from the wrong directory, a renamed
            # `_bmad-output/projects/` tree, or an unreadable specs dir -- and
            # the write would have wiped the baseline to `{}` at exit 0,
            # turning every governed file in the fleet into `no-baseline`.
            if not current and _read_baseline():
                raise StampAborted(
                    "refusing to stamp: discovery found zero Specs, but the "
                    f"committed {BASELINE.relative_to(REPO_ROOT)} is not empty — "
                    "writing would wipe every entry. Run this from the repository "
                    "root and check that "
                    "_bmad-output/projects/*/planning-artifacts/specs/spec-*/SPEC.md "
                    "is readable.\nbaseline untouched"
                )
            merged = current
            scope = f"{len(current)} spec(s) — ALL (accepts every spec's pending drift)"
        _write_baseline(merged)
    return scope


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write-baseline", action="store_true",
                    help="stamp the drift baseline after a spec reconciliation")
    ap.add_argument("--spec", action="append", metavar="NAME", default=None,
                    help=("limit --write-baseline to this spec (repeatable). "
                          "WITHOUT it the stamp covers EVERY spec, which accepts "
                          "every other spec's pending drift as correct."))
    ap.add_argument("--accept", action="append", metavar="PATH", default=None,
                    help=("with --spec: accept this drifted path as reconciled "
                          "although the spec's memlog does not name it (repeatable). "
                          "A scoped stamp otherwise refuses any path that differs "
                          "from its baseline and is not narrated on the memlog."))
    args = ap.parse_args()

    if args.spec and not args.write_baseline:
        ap.error("--spec only makes sense with --write-baseline")
    if args.accept and not args.write_baseline:
        ap.error("--accept only makes sense with --write-baseline")
    if args.accept and not args.spec:
        ap.error("--accept only makes sense with --spec (an unscoped stamp "
                 "already accepts every path)")

    if not args.write_baseline:
        print(
            "this script no longer computes the coverage/drift verdict -- run "
            "`python -m pyforge.doctor.sources spec-surface` for that. Pass "
            "--write-baseline [--spec NAME ...] to stamp the baseline after a "
            "spec reconciliation.",
            file=sys.stderr,
        )
        return 2

    # Expensive live-state walk and arg validation stay OUTSIDE the lock --
    # they read the working tree and the spec set, never the baseline.
    unevaluable: dict[str, str] = {}
    current = _live_state(unevaluable)

    if args.spec:
        named = set(args.spec)
        dark = sorted(named & set(unevaluable))
        if dark:
            print("refusing to stamp: these spec(s) declare a surface nothing "
                  "could be read from, so what they govern is unknown:",
                  file=sys.stderr)
            for name in dark:
                print(f"  {name}: {unevaluable[name]}", file=sys.stderr)
            print("baseline untouched", file=sys.stderr)
            return 2
        unknown = sorted(named - set(current))
        if unknown:
            print(f"unknown spec(s): {', '.join(unknown)}\n"
                  f"known: {', '.join(sorted(current))}", file=sys.stderr)
            return 2
    elif unevaluable:
        # An unscoped stamp writes EVERY entry, so one dark surface would be
        # stamped as "governs nothing" along with the rest.
        print("refusing to stamp every spec: these spec(s) declare a surface "
              "nothing could be read from, so what they govern is unknown:",
              file=sys.stderr)
        for name in sorted(unevaluable):
            print(f"  {name}: {unevaluable[name]}", file=sys.stderr)
        print("fix the surface, or stamp the unaffected specs individually "
              "with --spec NAME\nbaseline untouched", file=sys.stderr)
        return 2

    accept = frozenset(os.path.normpath(p) for p in args.accept or ())
    try:
        scope = _stamp_baseline(args.spec, current, accept)
    except StampRefused as refused:
        print(refused.render(), file=sys.stderr)
        return 1
    except (StampAborted, BaselineCorrupt) as aborted:
        print(str(aborted), file=sys.stderr)
        return 1
    print(f"baseline stamped: {BASELINE.relative_to(REPO_ROOT)} — {scope}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
