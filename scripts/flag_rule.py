"""The flag rule's machine form (doctor Story 34.1, spec-feature-flag-governance CAP-1).

Every story spec of `type: feature` minted on or after the rule date (2026-09-28) carries
either a `flag:` block (six fields: key, provider, default, scope, fallback, cleanup) or a
`flag-exempt:` value from the closed list in docs/governance/guild-roster.json. This module
is the pure reader of that rule. It judges nothing: no finding, no exit code, no `sys.exit`.
Story 34.2's gate turns a verdict into a finding, and the two named errors below into exit 2.

    classify(path)        -> Classification("flag" | "exempt" | "neither", reasons)
    is_post_rule(path)    -> True when the spec is absent from the rule-date baseline
    in_scope(spec)        -> True when the spec is `type: feature` (Q1)
    read_frontmatter(path) -> (mapping, "") or (None, why), for a caller that reads a spec once

The exemption list is read from the roster at call time; this file holds no copy of it, and
a unit test fails one. The baseline (docs/governance/flag-rule-baseline.json) is stamped by
scripts/flag_rule_baseline.py, never by hand. The shape of a block is written once, in
docs/reference/story-spec-flag-block.md.

Lives outside every `pyforge.<station>` package (Charter section 6): stdlib and PyYAML only,
and no station import.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Collection, Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
ROSTER_REL = Path("docs/governance/guild-roster.json")
BASELINE_REL = Path("docs/governance/flag-rule-baseline.json")

FLAG = "flag"
EXEMPT = "exempt"
NEITHER = "neither"

# The six fields of a `flag:` block, in the order the reference page lists them.
FLAG_FIELDS = ("key", "provider", "default", "scope", "fallback", "cleanup")

# A story spec: spec-<epic>-<story>-<slug>.md directly under a project's specs/ folder. A
# memlog matches the glob but is not a story spec; a folder-spec's own files never match.
_STORY_SPEC_RE = re.compile(r"^_bmad-output/projects/[^/]+/planning-artifacts/specs/spec-\d+-\d+-[^/]*\.md$")


class FlagRuleError(Exception):
    """Base of the two named errors Story 34.2 turns into exit 2."""


class RosterUnreadable(FlagRuleError):
    """docs/governance/guild-roster.json is missing, not JSON, or has no `flag_exemptions` list."""


class BaselineUnreadable(FlagRuleError):
    """docs/governance/flag-rule-baseline.json is missing, not JSON, or has no `specs` list."""


class Classification(NamedTuple):
    verdict: str  # FLAG | EXEMPT | NEITHER
    reasons: tuple[str, ...]  # empty unless the verdict is NEITHER; one entry per defect


def is_story_spec(rel: str) -> bool:
    """True for a repo-relative posix path that is one story spec (not a memlog)."""
    return bool(_STORY_SPEC_RE.match(rel)) and not rel.endswith(".memlog.md")


def repo_relative(path: str | os.PathLike[str], repo_root: Path | None = None) -> str:
    """The repo-relative posix form of `path` (the form git and the baseline use).

    A relative path is taken as already repo-relative. An absolute one under the repo root is
    relativised; anything else is returned as given, which the baseline will not contain.
    """
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    p = Path(path)
    if not p.is_absolute():
        return Path(os.path.normpath(p)).as_posix()
    for candidate, base in ((Path(os.path.normpath(p)), root), (p.resolve(), root.resolve())):
        try:
            return candidate.relative_to(base).as_posix()
        except ValueError:
            continue
    return p.as_posix()


def _read_json(rel: Path, repo_root: Path | None, error: type[FlagRuleError]) -> Any:
    path = (Path(repo_root) if repo_root is not None else REPO_ROOT) / rel
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:  # ValueError covers JSON and UTF-8 decode errors
        raise error(f"cannot read {rel.as_posix()}: {exc}") from exc


def load_exemptions(repo_root: Path | None = None) -> tuple[str, ...]:
    """The closed exemption list, read from the roster now (never cached, never copied)."""
    data = _read_json(ROSTER_REL, repo_root, RosterUnreadable)
    values = data.get("flag_exemptions") if isinstance(data, dict) else None
    if not isinstance(values, list) or not values or not all(isinstance(v, str) for v in values):
        raise RosterUnreadable(f"{ROSTER_REL.as_posix()} carries no `flag_exemptions` list of strings")
    return tuple(values)


def read_baseline(repo_root: Path | None = None) -> dict[str, Any]:
    """The whole baseline document (`ruling_sha`, `rule_date`, `specs`, ...)."""
    data = _read_json(BASELINE_REL, repo_root, BaselineUnreadable)
    specs = data.get("specs") if isinstance(data, dict) else None
    if not isinstance(specs, list) or not all(isinstance(s, str) for s in specs):
        raise BaselineUnreadable(f"{BASELINE_REL.as_posix()} carries no `specs` list of strings")
    return data


def load_baseline(repo_root: Path | None = None) -> frozenset[str]:
    """The pre-rule population: every story spec that existed at the ruling SHA."""
    return frozenset(read_baseline(repo_root)["specs"])


def is_post_rule(
    path: str | os.PathLike[str],
    *,
    baseline: Collection[str] | None = None,
    repo_root: Path | None = None,
) -> bool:
    """A spec is post-rule exactly when it is absent from the baseline.

    The spec's own `created:` string is never read: it is a date the spec declares about
    itself, and specs minted before the Spec reached `ready` carry the rule date too.

    This answers for a story spec only (`spec-<epic>-<story>-*.md`, see `is_story_spec`): the
    baseline holds no other file, so a path outside that naming is reported post-rule. Callers
    filter with `is_story_spec` first.
    """
    known = baseline if baseline is not None else load_baseline(repo_root)
    return repo_relative(path, repo_root) not in known


def _frontmatter(path: Path) -> tuple[dict[str, Any] | None, str]:
    """(mapping, "") for a readable frontmatter, else (None, why). Never raises."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"cannot read the spec: {exc}"
    lines = text.removeprefix("\ufeff").splitlines()
    if not lines or lines[0].rstrip() != "---":
        return None, "no frontmatter"
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip() == "---"), None)
    if end is None:
        return None, "no frontmatter (the opening `---` fence is never closed)"
    try:
        data = yaml.safe_load("\n".join(lines[1:end]))
    except (yaml.YAMLError, ValueError, OverflowError) as exc:
        # ValueError/OverflowError: safe_load builds dates eagerly, so `created: 2026-02-30` raises.
        return None, f"frontmatter is not valid YAML: {next(iter(str(exc).splitlines()), type(exc).__name__)}"
    if data is None:
        return None, "frontmatter is empty"
    if not isinstance(data, dict):
        return None, "frontmatter is not a mapping"
    return data, ""


def read_frontmatter(
    path: str | os.PathLike[str], *, repo_root: Path | None = None
) -> tuple[dict[str, Any] | None, str]:
    """(mapping, "") for a readable story-spec frontmatter, else (None, why). Never raises.

    The public reader Story 34.2's gate uses, so it reads each spec once and hands the mapping to
    `classify_frontmatter` and `in_scope`. A relative `path` is taken as repo-relative, as in `classify`.
    """
    return _frontmatter(_absolute(path, repo_root))


def _blank(value: Any) -> bool:
    # Not `not value`: YAML reads an unquoted `off` as False, and `default: off` is a value.
    if isinstance(value, str):
        return not value.strip()
    return value is None or (isinstance(value, (dict, list)) and not value)


def _classify_block(block: Any) -> Classification:
    if not isinstance(block, Mapping):
        return Classification(NEITHER, (f"`flag:` is not a mapping of its six fields ({', '.join(FLAG_FIELDS)})",))
    reasons = []
    for field in FLAG_FIELDS:
        if field not in block:
            reasons.append(f"`flag:` block is missing `{field}`")
        elif _blank(block[field]):
            reasons.append(f"`flag:` block field `{field}` is empty")
    return Classification(NEITHER if reasons else FLAG, tuple(reasons))


def _classify_exempt(value: Any, exemptions: Sequence[str]) -> Classification:
    if _blank(value):
        return Classification(NEITHER, ("`flag-exempt:` is empty; it takes one value from the roster's closed list",))
    if value not in exemptions:
        return Classification(
            NEITHER, (f"`flag-exempt: {value}` is not on the roster's closed list ({', '.join(exemptions)})",)
        )
    return Classification(EXEMPT, ())


def classify_frontmatter(frontmatter: Mapping[str, Any], exemptions: Sequence[str]) -> Classification:
    """The verdict for an already-parsed frontmatter mapping and a given exemption list."""
    has_flag = "flag" in frontmatter
    has_exempt = "flag-exempt" in frontmatter
    if has_flag and has_exempt:
        return Classification(
            NEITHER, ("carries both a `flag:` block and a `flag-exempt:` value; a spec declares exactly one",)
        )
    if has_flag:
        return _classify_block(frontmatter["flag"])
    if has_exempt:
        return _classify_exempt(frontmatter["flag-exempt"], exemptions)
    return Classification(NEITHER, ("carries neither a `flag:` block nor a `flag-exempt:` value",))


def _absolute(path: str | os.PathLike[str], repo_root: Path | None) -> Path:
    p = Path(path)
    return p if p.is_absolute() else (Path(repo_root) if repo_root is not None else REPO_ROOT) / p


def classify(
    path: str | os.PathLike[str],
    *,
    exemptions: Sequence[str] | None = None,
    repo_root: Path | None = None,
) -> Classification:
    """Read one story spec's frontmatter and return `flag`, `exempt` or `neither` with reasons.

    A spec with no, unclosed, empty or malformed frontmatter is `neither` (never a raise).
    Raises RosterUnreadable when the exemption list cannot be read. Pass `exemptions` to
    classify many specs against one read of the roster.
    """
    allowed = tuple(exemptions) if exemptions is not None else load_exemptions(repo_root)
    frontmatter, why = _frontmatter(_absolute(path, repo_root))
    if frontmatter is None:
        return Classification(NEITHER, (why,))
    return classify_frontmatter(frontmatter, allowed)


def in_scope(spec: Mapping[str, Any] | str | os.PathLike[str], *, repo_root: Path | None = None) -> bool:
    """True when the spec is `type: feature` (Q1: `fix`, `chore` and `docs` need no flag).

    `spec` is a story spec's path, or its already-parsed frontmatter mapping.
    """
    if isinstance(spec, Mapping):
        frontmatter: Mapping[str, Any] | None = spec
    else:
        frontmatter, _ = _frontmatter(_absolute(spec, repo_root))
    return frontmatter is not None and str(frontmatter.get("type", "")).strip() == "feature"
