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
    FAIL  flag-verification-names-no-test
                                a ``done`` post-rule flagged spec whose ``## Verification`` names no test file
    FAIL  flag-test-file-missing
                                the same, when a test file it names does not exist
    FAIL  flag-test-not-two-state
                                the same, when no test file it names runs the spec's key in both states
    FAIL  flag-metadata-missing a tree flag whose ``metadata.owner`` or ``metadata.story`` is missing or empty
    FAIL  flag-clock-overdue    a tree flag whose ``on_everywhere`` date is more than 90 days before the run date
    FAIL  flag-default-env-mismatch
                                a ``done`` flagged spec whose declared ``default`` for an environment disagrees
                                with the tree's rendered value for that environment (Story 34.3)
    WARN  flag-pre-rule         a pre-rule ``type: feature`` spec that carries neither, grouped
                                by station (the list Story 34.4's inventory counts); never a FAIL

``--spec <path>`` judges one story spec and prints one JSON object (``verdict`` ``pass``, ``warn``
or ``red``, ``findings``, ``rule_date``) -- the interface marshal Story 74.2's dispatch preflight
consults. The metadata checks (per-environment defaults, the 90-day clock) are Story 34.3's; ``--run-date``
injects the clock's run date.

The two-state-test check (Story 34.5, ``spec-feature-flag-governance`` CAP-4's gate clause) judges only a
``done``, post-rule spec that carries a complete ``flag:`` block: it reads the spec's ``## Verification``
section, collects the test files it names (backticked paths and ``pytest`` targets), and reads each one
statically -- never imported, never run. A file runs both states when it names the spec's ``flag.key`` together
with the testing kit's helper (``pyforge.testing_kit.flags.flag_states``, marshal Story 74.1) or with two flagd
trees written for it (the pre-kit shape, one ``*flagd_tree*`` call for ``"on"`` and another for ``"off"``). It is
presence-based: it cannot prove a tree is written for the key, only that the file names the key and carries the
shape. A spec still in backlog, and an exempt one, is never judged on it (its test does not exist yet, or it
carries no flag).

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
import re
import subprocess
import sys
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date
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
K_NO_TEST = "flag-verification-names-no-test"
K_TEST_MISSING = "flag-test-file-missing"
K_NOT_TWO_STATE = "flag-test-not-two-state"
K_METADATA_MISSING = "flag-metadata-missing"
K_CLOCK_OVERDUE = "flag-clock-overdue"
K_DEFAULT_ENV = "flag-default-env-mismatch"

# Story 34.6: epic and story numbers from ``spec-<epic>-<story>-*.md`` (integer order, not text).
_STORY_KEY_RE = re.compile(r"^spec-(\d+)-(\d+)-")

# How many pre-rule specs a station lists by default before `-v` is needed.
_WARN_LIST_LIMIT = 3


TreeUnreadable = flag_rule.TreeUnreadable  # Story 34.4 imports this symbol from the gate module


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
    """The ``flags`` mapping of the one tree (Story 34.3: through ``flag_rule.load_flags``)."""
    return flag_rule.load_flags(root)


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


def _story_key_tuple(rel: str) -> tuple[int, int] | None:
    """Epic and story numbers from a story-spec filename, for ordering declarations (Story 34.6)."""
    name = rel.rsplit("/", 1)[-1]
    match = _STORY_KEY_RE.match(name)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def env_default_judge_targets(
    root: Path,
    exemptions: Sequence[str],
    spec_rels: Sequence[str],
) -> frozenset[str]:
    """Story specs whose per-environment ``flag.default`` the gate compares to the tree (Story 34.6).

    Within one station, several ``done`` specs may declare the same key; only the highest story key
    is judged. Cross-station keys are grouped per station, so each station's latest is judged.
    """
    groups: dict[tuple[str, str], list[tuple[tuple[int, int], str]]] = {}
    for rel in spec_rels:
        frontmatter, _ = flag_rule.read_frontmatter(rel, repo_root=root)
        if frontmatter is None:
            continue
        if str(frontmatter.get("status", "")).strip().lower() != "done":
            continue
        if flag_rule.classify_frontmatter(frontmatter, exemptions).verdict != flag_rule.FLAG:
            continue
        key = _flag_key(frontmatter)
        if not key:
            continue
        story_key = _story_key_tuple(rel)
        if story_key is None:
            continue
        station = station_of(rel)
        groups.setdefault((station, key), []).append((story_key, rel))
    winners: set[str] = set()
    for entries in groups.values():
        _story_key, latest_rel = max(entries, key=lambda item: item[0])
        winners.add(latest_rel)
    return frozenset(winners)


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


# --- metadata, per-environment defaults, the 90-day clock (Story 34.3) -------------------------


def _metadata_strings(entry: Mapping[str, Any]) -> tuple[dict[str, str] | None, str]:
    """(field values, why unreadable) for a flag entry's ``metadata`` block."""
    metadata = entry.get("metadata")
    if not isinstance(metadata, dict):
        return None, "metadata"
    values: dict[str, str] = {}
    for field in ("owner", "story"):
        raw = metadata.get(field)
        if not isinstance(raw, str):
            return None, field
        values[field] = raw
    on_raw = metadata.get("on_everywhere")
    if not isinstance(on_raw, str):
        return None, "on_everywhere"
    values["on_everywhere"] = on_raw
    return values, ""


def judge_tree_metadata(flags: Mapping[str, Any], overlays: Mapping[str, Any], *, run_date: date) -> list[Finding]:
    """Clock and required metadata findings for every flag in the one tree."""
    findings: list[Finding] = []
    for key, entry in flags.items():
        if not isinstance(entry, dict):
            continue
        values, missing = _metadata_strings(entry)
        if values is None:
            findings.append(
                Finding(
                    K_METADATA_MISSING,
                    FAIL,
                    f"tree flag `{key}` metadata.{missing} is missing",
                    path=TREE_REL.as_posix(),
                    key=key,
                )
            )
            continue
        for field in ("owner", "story"):
            if not values[field].strip():
                findings.append(
                    Finding(
                        K_METADATA_MISSING,
                        FAIL,
                        f"tree flag `{key}` metadata.{field} is missing",
                        path=TREE_REL.as_posix(),
                        key=key,
                    )
                )
        on_date = flag_rule.parse_metadata_date(values["on_everywhere"])
        if on_date is None:
            continue
        if any(not flag_rule.renders_on(key, entry, overlays, env) for env in flag_rule.ENVIRONMENTS):
            continue
        if (run_date - on_date).days > flag_rule.CLEANUP_DAYS:
            findings.append(
                Finding(
                    K_CLOCK_OVERDUE,
                    FAIL,
                    f"tree flag `{key}` is past its {flag_rule.CLEANUP_DAYS}-day clock "
                    f"(owner {values['owner']!r}, story {values['story']!r}, on_everywhere {values['on_everywhere']!r})",
                    path=TREE_REL.as_posix(),
                    key=key,
                    station=values["owner"],
                )
            )
    return findings


def judge_spec_env_defaults(
    rel: str,
    frontmatter: Mapping[str, Any],
    flags: Mapping[str, Any],
    overlays: Mapping[str, Any],
    exemptions: Sequence[str],
    *,
    env_default_targets: frozenset[str],
) -> list[Finding]:
    """Per-environment default mismatch for a ``done`` flagged story spec (Story 34.3)."""
    if rel not in env_default_targets:
        return []
    if str(frontmatter.get("status", "")).strip().lower() != "done":
        return []
    if flag_rule.classify_frontmatter(frontmatter, exemptions).verdict != flag_rule.FLAG:
        return []
    block = frontmatter.get("flag")
    if not isinstance(block, Mapping):
        return []
    key = _flag_key(frontmatter)
    if not key or key not in flags:
        return []
    entry = flags[key]
    if not isinstance(entry, dict):
        return []
    station = station_of(rel)
    findings: list[Finding] = []
    for environment in flag_rule.ENVIRONMENTS:
        declared = flag_rule.declared_default_for_env(block, environment)
        if declared is None:
            continue
        rendered = flag_rule.tree_default_for_env(key, entry, overlays, environment)
        if declared != rendered:
            findings.append(
                Finding(
                    K_DEFAULT_ENV,
                    FAIL,
                    f"`done` spec declares `{environment}: {declared}` for flag `{key}` but the tree renders `{rendered}`",
                    path=rel,
                    station=station,
                    key=key,
                )
            )
    return findings


# --- the two-state test (Story 34.5) ----------------------------------------------------------


# The testing kit's ON/OFF helper, as marshal Story 74.1 landed it: `flag_states(key)` in
# `pyforge.testing_kit.flags`, re-exported by `pyforge.testing_kit`. Read from that module, never guessed.
_KIT_HELPER = "flag_states"
_KIT_MODULE = r"pyforge\.testing_kit(?:\.flags)?"
_KIT_IMPORT = re.compile(rf"^[ \t]*(?:from[ \t]+{_KIT_MODULE}[ \t]+import\b|import[ \t]+{_KIT_MODULE}\b)", re.MULTILINE)
_KIT_CALL = re.compile(rf"\b{_KIT_HELPER}\(")
# The pre-kit shape: a `*flagd_tree*` writer called once with "on" and once with "off".
_TREE_CALL = re.compile(r"\b\w*flagd_tree\w*[ \t]*\(")
_VARIANT = re.compile(r"""["'](on|off)["']""")
_DEF_KEYWORD = re.compile(r"\bdef$")  # the keyword itself, never an identifier that merely ends in "def"
_TEST_NAME = re.compile(r"^(?:test_.*\.py|.*_test\.py|.*\.(?:test|spec)\.\w+)$")
_VERIFICATION_HEADING = re.compile(r"^##[ \t]+Verification[ \t]*$", re.MULTILINE)
_LEVEL_TWO_HEADING = re.compile(r"^##[ \t]", re.MULTILINE)
_FENCED = re.compile(r"^[ \t]*(`{3,}|~{3,})[^\n]*\n(.*?)^[ \t]*\1[ \t]*$", re.MULTILINE | re.DOTALL)
_INLINE = re.compile(r"`([^`\n]+)`")


def _verification_text(text: str) -> str:
    """The body of every ``## Verification`` section of a story spec (each ends at the next ``## `` heading)."""
    sections = []
    for heading in _VERIFICATION_HEADING.finditer(text):
        end = _LEVEL_TWO_HEADING.search(text, heading.end())
        sections.append(text[heading.end() : end.start() if end else len(text)])
    return "\n".join(sections)


def _named_test_files(verification: str) -> list[str]:
    """The test files a Verification section names, in order, once each.

    Candidates are the words of its code spans (inline and fenced), so a backticked path and a ``pytest``
    target both count. A pytest node id loses its ``::test`` suffix; an option (``--ignore=...``) and a URL are
    not a file the run executes. A word counts by its file name (``test_*.py``, ``*_test.py``, ``*.test.*``,
    ``*.spec.*``): a directory target names no file.
    """
    spans = [m.group(2) for m in _FENCED.finditer(verification)]
    spans += _INLINE.findall(_FENCED.sub("", verification))
    named: list[str] = []
    for span in spans:
        for word in span.split():
            candidate = word.split("::", 1)[0].strip("\"'`,;()<>")
            if candidate.startswith("-") or "://" in candidate:
                continue
            candidate = candidate.removeprefix("./")
            if candidate and _TEST_NAME.match(candidate.rsplit("/", 1)[-1]) and candidate not in named:
                named.append(candidate)
    return named


def _read_test(root: Path, named: str) -> str | None:
    """The text of a named test file, or None when it is not a readable file inside ``root``."""
    path = Path(named)
    try:
        resolved = (path if path.is_absolute() else root / path).resolve()
        resolved.relative_to(root.resolve())
        return resolved.read_text(encoding="utf-8", errors="replace") if resolved.is_file() else None
    except (OSError, ValueError):  # ValueError: outside the repo root
        return None


def _names_key(text: str, key: str) -> bool:
    return re.search(rf"(?<![\w.-]){re.escape(key)}(?![\w-]|\.\w)", text) is not None


def _call_arguments(text: str, opening: int) -> str:
    """The text between the parenthesis at ``opening`` and its match (to the end of ``text`` if unbalanced)."""
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "(":
            depth += 1
        elif text[index] == ")":
            depth -= 1
            if depth == 0:
                return text[opening + 1 : index]
    return text[opening + 1 :]


def _writes_both_trees(text: str) -> bool:
    """Two distinct ``*flagd_tree*`` calls, one naming ``"on"`` and another ``"off"`` (a ``def`` is no call)."""
    variants = [
        set(_VARIANT.findall(_call_arguments(text, call.end() - 1)))
        for call in _TREE_CALL.finditer(text)
        if not _DEF_KEYWORD.search(text[: call.start()].rstrip())
    ]
    on = {i for i, seen in enumerate(variants) if "on" in seen}
    off = {i for i, seen in enumerate(variants) if "off" in seen}
    return any(i != j for i in on for j in off)


def runs_both_states(text: str, key: str) -> bool:
    """True when the test text names ``key`` with the kit's helper or with two flagd trees (either shape)."""
    if not _names_key(text, key):
        return False
    return bool(_KIT_IMPORT.search(text) and _KIT_CALL.search(text)) or _writes_both_trees(text)


def judge_two_state(
    root: Path, rel: str, frontmatter: Mapping[str, Any], *, exemptions: Sequence[str]
) -> list[Finding]:
    """The two-state-test findings for one story spec (Story 34.5, CAP-4's gate clause).

    Only a ``done`` spec with a complete ``flag:`` block is judged; a backlog spec has no test yet and an
    exempt one carries no flag. At most one finding, in this order: the Verification names no test file; a
    named path is not a readable file under the repo root; no named file runs the spec's key in both states.
    """
    if str(frontmatter.get("status", "")).strip().lower() != "done":
        return []
    if flag_rule.classify_frontmatter(frontmatter, exemptions).verdict != flag_rule.FLAG:
        return []
    key = _flag_key(frontmatter)
    if not key:
        return []
    station = station_of(rel)
    try:
        spec_text = (root / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []  # the frontmatter was read a moment ago; a file that vanished is judged elsewhere

    def finding(kind: str, message: str) -> list[Finding]:
        return [Finding(kind, FAIL, message, path=rel, station=station, key=key)]

    named = _named_test_files(_verification_text(spec_text))
    if not named:
        return finding(
            K_NO_TEST,
            f"a `done` spec that declares flag `{key}` must name, in its `## Verification`, a test file that runs "
            "both states (`test_*.py`, `*_test.py`, `*.test.*` or `*.spec.*` -- the testing kit's `flag_states`, "
            "or two flagd trees); it names none",
        )
    texts = {path: _read_test(root, path) for path in named}
    missing = [path for path, text in texts.items() if text is None]
    if missing:
        return finding(
            K_TEST_MISSING,
            f"the `## Verification` of a `done` spec that declares flag `{key}` names test file(s) that are not a "
            f"readable file under the repo root: {', '.join(missing)}",
        )
    if not any(runs_both_states(text or "", key) for text in texts.values()):
        return finding(
            K_NOT_TWO_STATE,
            f"no test file the `## Verification` names runs flag `{key}` in both states ({', '.join(named)}): each "
            f"must name the key together with the testing kit's `{_KIT_HELPER}` "
            '(`pyforge.testing_kit.flags`) or with two flagd trees, one `"on"` and one `"off"`',
        )
    return []


# --- the two modes --------------------------------------------------------------------------


@dataclass(frozen=True)
class Inputs:
    exemptions: tuple[str, ...]
    baseline: frozenset[str]
    rule_date: str | None
    tree: dict[str, Any]
    overlays: dict[str, Any]
    run_date: date


def load_inputs(root: Path, *, run_date: date | None = None) -> Inputs:
    """Roster, baseline, tree and overlays, in that order; the first that cannot be read raises."""
    exemptions = flag_rule.load_exemptions(root)
    document = flag_rule.read_baseline(root)
    tree = load_tree(root)
    overlays = flag_rule.load_overlays(root)
    rule_date = document.get("rule_date")
    resolved_run = run_date if run_date is not None else date.today()
    return Inputs(
        exemptions,
        frozenset(document["specs"]),
        None if rule_date is None else str(rule_date),
        tree,
        overlays,
        resolved_run,
    )


def judge_one(
    root: Path,
    inputs: Inputs,
    rel: str,
    *,
    env_default_targets: frozenset[str],
) -> list[Finding]:
    frontmatter, why = flag_rule.read_frontmatter(rel, repo_root=root)
    post_rule = flag_rule.is_post_rule(rel, baseline=inputs.baseline, repo_root=root)
    findings = judge_spec(
        rel,
        frontmatter,
        why,
        exemptions=inputs.exemptions,
        post_rule=post_rule,
        tree_keys=inputs.tree,
    )
    if frontmatter is not None:
        findings += judge_spec_env_defaults(
            rel,
            frontmatter,
            inputs.tree,
            inputs.overlays,
            inputs.exemptions,
            env_default_targets=env_default_targets,
        )
    if post_rule and frontmatter is not None:
        findings += judge_two_state(root, rel, frontmatter, exemptions=inputs.exemptions)
    return findings


def judge_tree(root: Path, inputs: Inputs) -> tuple[int, list[Finding]]:
    """(story specs judged, findings) for every tracked story spec and the tree."""
    specs = story_specs(root)
    env_targets = env_default_judge_targets(root, inputs.exemptions, specs)
    findings = [f for rel in specs for f in judge_one(root, inputs, rel, env_default_targets=env_targets)]
    findings += judge_tree_metadata(inputs.tree, inputs.overlays, run_date=inputs.run_date)
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


def run_spec(root: Path, raw: str, *, run_date: date | None = None) -> int:
    """Judge one story spec; print one JSON object; exit 0 (pass, warn) / 1 (red) / 2 (cannot judge)."""
    rel = _resolve_spec(root, raw)
    rule_date: str | None = None
    try:
        inputs = load_inputs(root, run_date=run_date)
        rule_date = inputs.rule_date
        if not flag_rule.is_story_spec(rel):
            raise flag_rule.FlagRuleError(
                f"{rel} is not a story spec "
                f"(`{SPECS_ROOT_REL}/<project>/planning-artifacts/specs/spec-<epic>-<story>-*.md`)"
            )
        if not (root / rel).is_file():
            raise flag_rule.FlagRuleError(f"cannot read {rel}: no such file")
        env_targets = env_default_judge_targets(root, inputs.exemptions, story_specs(root))
        findings = judge_one(root, inputs, rel, env_default_targets=env_targets)
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


def run_tree(root: Path, *, as_json: bool, verbose: bool, run_date: date | None = None) -> int:
    try:
        inputs = load_inputs(root, run_date=run_date)
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
    parser.add_argument(
        "--run-date",
        default=None,
        metavar="YYYY-MM-DD",
        help="injectable run date for the 90-day clock (default: today)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    root = Path(args.root).resolve() if args.root else _SCRIPTS_DIR.parent
    try:
        run_date = flag_rule.parse_run_date(args.run_date)
    except flag_rule.FlagRuleError as exc:
        print(f"[flag-gate] unknown -- {exc}", file=sys.stderr)
        if args.spec is not None or args.json:
            _emit_json({"verdict": "unknown", "rule_date": None, "findings": [], "error": str(exc)})
        return 2
    try:
        if args.spec is not None:
            return run_spec(root, args.spec, run_date=run_date)
        return run_tree(root, as_json=args.json, verbose=args.verbose, run_date=run_date)
    except Exception as exc:  # noqa: BLE001 -- a crash is unknown, never a false green or a false red
        message = f"the gate crashed: {exc.__class__.__name__}: {exc}"
        if args.spec is not None or args.json:
            _emit_json({"verdict": "unknown", "rule_date": None, "findings": [], "error": message})
        print(f"[flag-gate] unknown -- {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
