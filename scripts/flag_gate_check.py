#!/usr/bin/env python3
"""The flag gate (doctor Story 34.2, ``spec-feature-flag-governance`` CAP-2).

From the rule date every story spec of ``type: feature`` carries a ``flag:`` block or a
``flag-exempt:`` value from the closed list in ``docs/governance/guild-roster.json``
(``scripts/flag_rule.py`` is the pure reader of that rule, Story 34.1). This check judges the
specs and keeps the one flag tree (``src/platform/config/flags.json``, canopy:AD-11) honest.

Tree mode (no arguments) walks every tracked
``_bmad-output/projects/*/planning-artifacts/specs/spec-<epic>-<story>-*.md`` and the tree:

    FAIL  flag-missing          a post-rule ``type: feature`` spec that carries neither
    FAIL  flag-exempt-unknown   a ``flag-exempt:`` value that is not on the roster's list
    FAIL  flag-key-not-in-tree  a ``done`` spec whose ``flag.key`` the tree does not hold
    FAIL  flag-key-orphan       a tree key that no tracked file under ``src/`` or ``scripts/`` reads
    WARN  flag-pre-rule         a pre-rule ``type: feature`` spec that carries neither, grouped
                                by station (the list Story 34.4's inventory counts); never a FAIL

``--spec <path>`` judges one story spec and prints one JSON object (``verdict`` ``pass``, ``warn``
or ``red``, ``findings``, ``rule_date``) -- the interface marshal Story 74.2's dispatch preflight
consults. The metadata checks (per-environment defaults, the 90-day clock) are Story 34.3's; the
two-state-test check is Story 34.5's.

Lives outside every ``pyforge.<station>`` package (Charter section 6): this check can red any
station's pull request, so no station it judges may host it, and it imports no station module. A
meta-test in ``pyforge-doctor`` (and its companion in ``pyforge-core``) pins that. Gates are
themselves exempt from the rule (the roster's gate value): a gated gate reports a silent green.

EXIT  0 clean (warnings allowed) / ``pass`` or ``warn`` · 1 findings / ``red`` · 2 could-not-run
      (the roster, the baseline, the tree or the list of tracked files cannot be read: unknown,
      never green)
"""

from __future__ import annotations

# Registry declaration -- see scripts/detectors.py. Tracked files only.
DETECTOR = {"scope": "repo"}

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import flag_rule  # noqa: E402

TREE_REL = Path("src/platform/config/flags.json")
# Story 76.1: the value-only overlay document names every tree key per environment, so it is a
# non-reader exactly as the tree is (else it would hide every orphan).
OVERLAYS_REL = Path("src/platform/config/flag-overlays.json")
SPECS_ROOT_REL = "_bmad-output/projects"
READER_ROOTS = ("src", "scripts")

# A file that reads a flag is code. These parts and names mark files that only *mention* a key.
_NON_READER_PARTS = frozenset({"tests", "test", "docs", "fixtures"})

FAIL = "fail"
WARN = "warn"

K_MISSING = "flag-missing"
K_EXEMPT_UNKNOWN = "flag-exempt-unknown"
K_NOT_IN_TREE = "flag-key-not-in-tree"
K_ORPHAN = "flag-key-orphan"
K_PRE_RULE = "flag-pre-rule"

# How many pre-rule specs a station lists by default before `-v` is needed.
_WARN_LIST_LIMIT = 3


class TreeUnreadable(flag_rule.FlagRuleError):
    """``src/platform/config/flags.json`` is missing, not JSON, or has no ``flags`` mapping."""


class ListingFailed(flag_rule.FlagRuleError):
    """``git ls-files`` failed, so the set of tracked files is unknown."""


@dataclass(frozen=True)
class Finding:
    kind: str
    severity: str  # FAIL | WARN
    message: str
    path: str = ""
    station: str = ""
    key: str = ""

    def as_dict(self) -> dict[str, str]:
        return {k: v for k, v in asdict(self).items() if v != ""}


def _verdict(findings: Iterable[Finding]) -> str:
    severities = {f.severity for f in findings}
    if FAIL in severities:
        return "red"
    return "warn" if WARN in severities else "pass"


# --- reading the inputs ---------------------------------------------------------------------


def load_tree(root: Path) -> dict[str, Any]:
    """The ``flags`` mapping of the one tree, read as JSON. Raises TreeUnreadable."""
    path = root / TREE_REL
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:  # ValueError covers JSON and UTF-8 decode errors
        raise TreeUnreadable(f"cannot read {TREE_REL.as_posix()}: {exc}") from exc
    flags = data.get("flags") if isinstance(data, dict) else None
    if not isinstance(flags, dict):
        raise TreeUnreadable(f"{TREE_REL.as_posix()} carries no `flags` mapping")
    return flags


def _list_files(root: Path, prefixes: Sequence[str]) -> list[str]:
    """Repo-relative posix paths under ``prefixes``: tracked files when ``root`` is a git checkout,
    else a filesystem walk (a fixture tree). A tracked file deleted from the working tree is skipped."""
    if (root / ".git").exists():
        try:
            proc = subprocess.run(
                ["git", "-C", str(root), "ls-files", "-z", "--", *prefixes],
                capture_output=True,
                check=False,
            )
        except OSError as exc:
            raise ListingFailed(f"cannot run `git ls-files` in {root}: {exc}") from exc
        if proc.returncode != 0:
            detail = proc.stderr.decode("utf-8", "replace").strip() or f"exit {proc.returncode}"
            raise ListingFailed(f"`git ls-files` failed in {root}: {detail}")
        rels = [r for r in proc.stdout.decode("utf-8", "surrogateescape").split("\0") if r]
    else:
        rels = [
            Path(dirpath, name).relative_to(root).as_posix()
            for prefix in prefixes
            for dirpath, _dirs, names in os.walk(root / prefix)
            for name in names
        ]
    return sorted(r for r in rels if (root / r).is_file())


def story_specs(root: Path) -> list[str]:
    """Every story spec (``spec-<epic>-<story>-*.md``, never a memlog) under the projects folder."""
    return [r for r in _list_files(root, (SPECS_ROOT_REL,)) if flag_rule.is_story_spec(r)]


def _is_reader_candidate(rel: str) -> bool:
    if rel in (TREE_REL.as_posix(), OVERLAYS_REL.as_posix()):
        return False
    parts = rel.split("/")
    name = parts[-1]
    if any(part in _NON_READER_PARTS for part in parts):
        return False
    return not (name.startswith("test_") and name.endswith(".py") or name == "conftest.py" or name.endswith(".md"))


def orphan_keys(root: Path, keys: Iterable[str]) -> list[str]:
    """The keys whose text appears in no tracked reader file under ``src/`` or ``scripts/``.

    Skipped as non-readers: the tree itself and its overlay document (``flag-overlays.json``, Story 76.1),
    any path part ``tests``/``test``/``docs``/``fixtures``, ``test_*.py``, ``conftest.py`` and ``*.md``.
    This module names no live key, so it never reads one.
    """
    remaining = {key: key.encode("utf-8") for key in keys}
    if not remaining:
        return []
    for rel in _list_files(root, READER_ROOTS):
        if not _is_reader_candidate(rel):
            continue
        try:
            data = (root / rel).read_bytes()
        except OSError:
            continue
        for key in [k for k, encoded in remaining.items() if encoded in data]:
            del remaining[key]
        if not remaining:
            break
    return sorted(remaining)


# --- judging one spec -----------------------------------------------------------------------


def station_of(rel: str) -> str:
    """The project folder a story spec lives in (``pyforge-<station>``)."""
    parts = rel.split("/")
    return parts[2] if len(parts) > 2 and parts[0] == "_bmad-output" and parts[1] == "projects" else ""


def _unknown_exemption(frontmatter: Mapping[str, Any], exemptions: Sequence[str]) -> Any:
    """The ``flag-exempt:`` value when it is non-blank and off the roster's list, else None.

    A blank value, or a spec that declares both a block and an exemption, stays ``neither``
    (`classify_frontmatter` reasons on it), so an unknown value never reports twice.
    """
    if "flag" in frontmatter or "flag-exempt" not in frontmatter:
        return None
    value = frontmatter["flag-exempt"]
    blank = (
        value is None
        or (isinstance(value, str) and not value.strip())
        or (isinstance(value, (list, dict)) and not value)
    )
    return None if blank or value in exemptions else value


def _flag_key(frontmatter: Mapping[str, Any]) -> str:
    block = frontmatter.get("flag")
    key = block.get("key") if isinstance(block, Mapping) else None
    return key.strip() if isinstance(key, str) else ""


def judge_spec(
    rel: str,
    frontmatter: Mapping[str, Any] | None,
    why: str,
    *,
    exemptions: Sequence[str],
    post_rule: bool,
    tree_keys: Collection[str],
) -> list[Finding]:
    """The findings for one story spec. ``frontmatter`` None (with ``why``) reads as ``neither``,
    in scope: a spec whose frontmatter cannot be read is never silently out of the rule."""
    station = station_of(rel)
    if frontmatter is None:
        in_scope = True
        verdict, reasons = flag_rule.NEITHER, (why,)
        unknown = None
    else:
        in_scope = flag_rule.in_scope(frontmatter)
        verdict, reasons = flag_rule.classify_frontmatter(frontmatter, exemptions)
        unknown = _unknown_exemption(frontmatter, exemptions)

    findings: list[Finding] = []
    if unknown is not None:
        findings.append(
            Finding(
                K_EXEMPT_UNKNOWN,
                FAIL,
                f"`flag-exempt: {unknown}` is not on the roster's closed list ({', '.join(exemptions)})",
                path=rel,
                station=station,
            )
        )
    elif in_scope and verdict == flag_rule.NEITHER:
        detail = "; ".join(reasons)
        if post_rule:
            findings.append(
                Finding(
                    K_MISSING,
                    FAIL,
                    f"a post-rule `type: feature` spec must carry a `flag:` block or a `flag-exempt:` value: {detail}",
                    path=rel,
                    station=station,
                )
            )
        else:
            findings.append(
                Finding(
                    K_PRE_RULE,
                    WARN,
                    f"a pre-rule `type: feature` spec carries no flag block or exemption yet (retrofit): {detail}",
                    path=rel,
                    station=station,
                )
            )

    if frontmatter is not None:
        key = _flag_key(frontmatter)
        # Only a landed story is judged: a story still in backlog has not added its key to the tree yet.
        if key and str(frontmatter.get("status", "")).strip().lower() == "done" and key not in tree_keys:
            findings.append(
                Finding(
                    K_NOT_IN_TREE,
                    FAIL,
                    f"a `done` spec names flag key `{key}`, which {TREE_REL.as_posix()} does not hold",
                    path=rel,
                    station=station,
                    key=key,
                )
            )
    return findings


# --- the two modes --------------------------------------------------------------------------


@dataclass(frozen=True)
class Inputs:
    exemptions: tuple[str, ...]
    baseline: frozenset[str]
    rule_date: str | None
    tree: dict[str, Any]


def load_inputs(root: Path) -> Inputs:
    """Roster, baseline and tree, in that order; the first that cannot be read raises."""
    exemptions = flag_rule.load_exemptions(root)
    document = flag_rule.read_baseline(root)
    tree = load_tree(root)
    rule_date = document.get("rule_date")
    return Inputs(exemptions, frozenset(document["specs"]), None if rule_date is None else str(rule_date), tree)


def judge_one(root: Path, inputs: Inputs, rel: str) -> list[Finding]:
    frontmatter, why = flag_rule.read_frontmatter(rel, repo_root=root)
    return judge_spec(
        rel,
        frontmatter,
        why,
        exemptions=inputs.exemptions,
        post_rule=flag_rule.is_post_rule(rel, baseline=inputs.baseline, repo_root=root),
        tree_keys=inputs.tree,
    )


def judge_tree(root: Path, inputs: Inputs) -> tuple[int, list[Finding]]:
    """(story specs judged, findings) for every tracked story spec and the tree."""
    specs = story_specs(root)
    findings = [f for rel in specs for f in judge_one(root, inputs, rel)]
    for key in orphan_keys(root, inputs.tree):
        findings.append(
            Finding(
                K_ORPHAN,
                FAIL,
                f"tree key `{key}` is read by no tracked file under {' or '.join(f'{r}/' for r in READER_ROOTS)} "
                "(the tree, tests, docs, fixtures and *.md do not count)",
                path=TREE_REL.as_posix(),
                key=key,
            )
        )
    findings.sort(key=lambda f: (f.severity != FAIL, f.kind, f.station, f.path, f.key))
    return len(specs), findings


def _resolve_spec(root: Path, raw: str) -> str:
    path = Path(raw)
    if not path.is_absolute() and not (root / path).is_file() and (Path.cwd() / path).is_file():
        path = Path.cwd() / path
    return flag_rule.repo_relative(path, root)


def _emit_json(payload: Mapping[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=False))


def run_spec(root: Path, raw: str) -> int:
    """Judge one story spec; print one JSON object; exit 0 (pass, warn) / 1 (red) / 2 (cannot judge)."""
    rel = _resolve_spec(root, raw)
    rule_date: str | None = None
    try:
        inputs = load_inputs(root)
        rule_date = inputs.rule_date
        if not flag_rule.is_story_spec(rel):
            raise flag_rule.FlagRuleError(
                f"{rel} is not a story spec "
                f"(`{SPECS_ROOT_REL}/<project>/planning-artifacts/specs/spec-<epic>-<story>-*.md`)"
            )
        if not (root / rel).is_file():
            raise flag_rule.FlagRuleError(f"cannot read {rel}: no such file")
        findings = judge_one(root, inputs, rel)
    except flag_rule.FlagRuleError as exc:
        _emit_json({"verdict": "unknown", "spec": rel, "rule_date": rule_date, "findings": [], "error": str(exc)})
        print(f"[flag-gate] unknown -- {exc}", file=sys.stderr)
        return 2
    verdict = _verdict(findings)
    _emit_json({"verdict": verdict, "spec": rel, "rule_date": rule_date, "findings": [f.as_dict() for f in findings]})
    return 1 if verdict == "red" else 0


def _print_tree_report(judged: int, findings: Sequence[Finding], rule_date: str | None, verbose: bool) -> None:
    fails = [f for f in findings if f.severity == FAIL]
    warns = [f for f in findings if f.severity == WARN]
    for f in fails:
        print(f"[flag-gate] fail -- {f.kind}: {f.path or f.key}: {f.message}")
    by_station: dict[str, list[Finding]] = {}
    for f in warns:
        by_station.setdefault(f.station or "(no project)", []).append(f)
    for station in sorted(by_station):
        group = by_station[station]
        print(
            f"[flag-gate] warn -- {station}: {len(group)} pre-rule `type: feature` spec(s) "
            "carry neither a flag block nor an exemption"
        )
        shown = group if verbose else group[:_WARN_LIST_LIMIT]
        for f in shown:
            print(f"    {f.path}")
        if len(shown) < len(group):
            print(f"    ... and {len(group) - len(shown)} more (-v lists them all)")
    state = "fail" if fails else "ok"
    print(
        f"[flag-gate] {state} -- {judged} story spec(s) judged (rule date {rule_date or 'unknown'}): "
        f"{len(fails)} fail, {len(warns)} warn"
    )


def run_tree(root: Path, *, as_json: bool, verbose: bool) -> int:
    try:
        inputs = load_inputs(root)
        judged, findings = judge_tree(root, inputs)
    except flag_rule.FlagRuleError as exc:
        if as_json:
            _emit_json({"verdict": "unknown", "rule_date": None, "findings": [], "error": str(exc)})
        print(f"[flag-gate] unknown -- {exc}", file=sys.stderr)
        return 2
    verdict = _verdict(findings)
    if as_json:
        _emit_json(
            {
                "verdict": verdict,
                "rule_date": inputs.rule_date,
                "specs_judged": judged,
                "findings": [f.as_dict() for f in findings],
            }
        )
    else:
        _print_tree_report(judged, findings, inputs.rule_date, verbose)
    return 1 if verdict == "red" else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python scripts/flag_gate_check.py",
        description="The flag gate (doctor Story 34.2, spec-feature-flag-governance CAP-2).",
    )
    parser.add_argument("--root", default=None, help="repo root to judge (default: the checkout this script lives in)")
    parser.add_argument("--spec", default=None, help="judge one story spec and print one JSON object")
    parser.add_argument("--json", action="store_true", help="tree mode: print one JSON object instead of text")
    parser.add_argument("-v", "--verbose", action="store_true", help="tree mode: list every pre-rule warning")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    root = Path(args.root).resolve() if args.root else _SCRIPTS_DIR.parent
    try:
        if args.spec is not None:
            return run_spec(root, args.spec)
        return run_tree(root, as_json=args.json, verbose=args.verbose)
    except Exception as exc:  # noqa: BLE001 -- a crash is unknown, never a false green or a false red
        message = f"the gate crashed: {exc.__class__.__name__}: {exc}"
        if args.spec is not None or args.json:
            _emit_json({"verdict": "unknown", "rule_date": None, "findings": [], "error": message})
        print(f"[flag-gate] unknown -- {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
