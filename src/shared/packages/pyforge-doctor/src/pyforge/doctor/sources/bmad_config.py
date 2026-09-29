"""The bmad-render-config-ambiguity gather filter -- Doctor's verdict on
whether ``_bmad/scripts/render_skill.py``'s own central-config merge
contains an AMBIGUOUS bare key: the same key name occurring at two
different dotted paths (Story 20.2, Epic 20).

**Why this detector exists.** ``load_central_config()`` merges four layers
(``_bmad/config.toml``, ``_bmad/config.user.toml``,
``_bmad/custom/config.toml``, ``_bmad/custom/config.user.toml``) and every
rendering skill (``bmad-build``, ``bmad-build-auto``, ...) resolves
``{{.key}}`` short tokens against that merged tree via
``_find_config_values``: if the bare key sits at more than one dotted path,
resolution HALTs the skill mid-session with ``RenderError: ambiguous config
value``. This happened live on 2026-09-06 -- ``[core] user_skill_level``
collided with a regenerated ``[modules.bmm] user_skill_level``, fixed by
commit ``99e595cc6a`` -- and nothing caught this class proactively before
now; an operator only learned about it when a skill invocation HALTed.

**The independence rule.** This module REPRODUCES ``config_utils.py``'s
``structural_merge``/``merge_layers``/``load_toml`` and
``render_skill.py``'s ``_find_config_values`` scan, but never imports either
module -- this detector must keep working (and keep catching the SAME
ambiguity class) even if the renderer's own merge/scan code is what is
broken, mirroring every other source in this package's "structurally
independent of the mechanism it inspects" rule.
``tests/meta/test_source_independence.py`` enforces this fleet-wide, same as
every sibling source.

**Fail-open per layer, always.** Each of the four layers folds to ``{}`` on
a missing file, an unreadable file, or malformed TOML -- including
``_bmad/config.toml`` itself, which ``render_skill.py``'s own
``load_central_config()`` treats as ``required=True``. This detector's job
is signalling ambiguity risk in whatever central config actually exists
right now, not re-enforcing the renderer's own installation-completeness
contract -- a missing ``config.toml`` here just means there is nothing to be
ambiguous about yet (a degenerate, harmless case), not a misconfiguration
this detector should raise on. There is therefore no outer
``degrade_on_exception``-worthy raise path inside ``_gather`` for a missing/
malformed layer at all; ``gather``'s own wrapper exists only as the same
last-resort net every sibling source carries for a genuinely unexpected
failure.

**The one exclusion: the ``agents`` top-level key.** Running the real
merge+scan against this repo's own tracked ``_bmad/config.toml`` +
``_bmad/custom/config.toml`` surfaces exactly 6 colliding leaf names
(``module``, ``team``, ``name``, ``title``, ``icon``, ``description``),
every one confined to the ``[agents.bmad-agent-*]`` blocks -- five sibling
persona entries that structurally repeat the same field set by design.
Excluding the ``agents`` top-level key entirely (neither counted as a leaf
nor recursed into) is what makes "ok on today's tree" true; it is the one
exclusion this story adds, not a guess at what "feels" like noise, and it
degrades gracefully if a future settings namespace is added -- it only
needs revisiting if that new namespace repeats ``agents``' own "named
collection of homogeneous entries" shape (Boundaries: never add a second
exclusion speculatively).

**Never gates.** Status is always ``ok`` or ``warn``, never ``fail`` --
mirrors ``BMAD_METHOD_VERSION_DRIFT``'s own always-informs discipline.

**Never resolves path placeholders.** ``{project-root}``-style expansion is
``render_skill.py::_resolve_config_value``'s own job, irrelevant to
detecting ambiguity itself -- this module never performs it.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = ("gather",)

#: The four layers ``load_central_config()`` merges, in its own order --
#: reproduced here, never imported (Boundaries).
_LAYER_RELATIVE_PATHS: tuple[Path, ...] = (
    Path("_bmad/config.toml"),
    Path("_bmad/config.user.toml"),
    Path("_bmad/custom/config.toml"),
    Path("_bmad/custom/config.user.toml"),
)

#: The one top-level key excluded from the scan entirely -- BMAD's persona
#: registry, not a settings namespace (Design Notes above).
_EXCLUDED_TOP_LEVEL_KEY = "agents"


def _load_layer(path: Path) -> dict[str, Any]:
    """Fail-open TOML read: a missing file, an unreadable file, malformed
    TOML, or a non-UTF-8-encoded file all fold to ``{}`` -- the caller keeps
    merging the remaining layers regardless (I/O matrix: "Missing layer
    file", "Malformed TOML in one layer"). ``UnicodeDecodeError`` (a
    ``ValueError`` subclass, not an ``OSError``/``TOMLDecodeError``) is
    caught explicitly: ``tomllib.load`` genuinely raises it for a
    non-UTF-8-encoded layer file, and without this it would escape to the
    outer ``degrade_on_exception`` wrapper and degrade the WHOLE gather to
    one generic WARN instead of folding just this one layer to ``{}``."""
    try:
        with path.open("rb") as stream:
            parsed = tomllib.load(stream)
    except OSError, tomllib.TOMLDecodeError, UnicodeDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


def _structural_merge(base: Any, override: Any) -> Any:
    """Mirrors ``config_utils.structural_merge``'s dict-recursive shape,
    override wins -- but WITHOUT that function's keyed-array-merge branch:
    no layer this scan reads needs array-of-tables merging (Tasks), so a
    plain dict/scalar merge is sufficient and simpler. Any non-dict/non-dict
    pairing (including list-vs-list, or a scalar replacing a dict wholesale
    and vice versa) falls through to ``return override``, exactly like the
    reproduced function's own fall-through."""
    if isinstance(base, dict) and isinstance(override, dict):
        result = dict(base)
        for key, value in override.items():
            result[key] = _structural_merge(result[key], value) if key in result else value
        return result
    return override


def _merge_layers(target: Path) -> dict[str, Any]:
    """Fold the four ``_LAYER_RELATIVE_PATHS`` in
    ``load_central_config()``'s own order."""
    merged: dict[str, Any] = {}
    for relative_path in _LAYER_RELATIVE_PATHS:
        merged = _structural_merge(merged, _load_layer(target / relative_path))
    return merged


def _find_leaf_paths(data: Any, prefix: str = "") -> dict[str, list[str]]:
    """Mirrors ``render_skill.py``'s ``_find_config_values`` scan shape, but
    collects every bare leaf key name at once (``{leaf_name: [dotted_path,
    ...]}``) instead of filtering for one caller-supplied key.

    A "leaf" is a non-dict, non-list value -- a list is a dead end, never
    recursed into, exactly like the reproduced scan (a TOML array-of-tables
    is never a scannable collection of leaves, Boundaries). The top-level
    ``_EXCLUDED_TOP_LEVEL_KEY`` is skipped entirely -- neither counted as a
    leaf nor recursed into -- so the ``agents.*`` per-entry field repetition
    never reaches this function at all."""
    result: dict[str, list[str]] = {}
    if not isinstance(data, dict):
        return result
    for name, value in data.items():
        if prefix == "" and name == _EXCLUDED_TOP_LEVEL_KEY:
            continue
        path = f"{prefix}.{name}" if prefix else name
        if not isinstance(value, (dict, list)):
            result.setdefault(name, []).append(path)
        for nested_name, nested_paths in _find_leaf_paths(value, path).items():
            result.setdefault(nested_name, []).extend(nested_paths)
    return result


def gather(target: Path) -> tuple[Finding, ...]:
    """Reproduce ``load_central_config()``'s merge and ``_find_config_
    values``'s unqualified-leaf-key scan (minus the ``agents`` namespace);
    emit one WARN Finding per ambiguous key naming it and every colliding
    path, or one OK Finding naming the checked-key count when none collide.

    Read-only: only the four already-tracked/gitignored
    ``_bmad/config*.toml`` / ``_bmad/custom/config*.toml`` files. No
    subprocess, no git history, no writes."""
    return degrade_on_exception(
        Source.BMAD_RENDER_CONFIG_AMBIGUITY,
        "bmad-render-config-ambiguity",
        lambda: _gather(target),
    )


def _gather(target: Path) -> tuple[Finding, ...]:
    merged = _merge_layers(target)
    leaf_paths = _find_leaf_paths(merged)
    checked = len(leaf_paths)
    ambiguous = {name: paths for name, paths in leaf_paths.items() if len(paths) > 1}

    if not ambiguous:
        suffix = f"({checked} checked -- no central config layers found)" if checked == 0 else f"({checked} checked)"
        return (
            Finding(
                source=Source.BMAD_RENDER_CONFIG_AMBIGUITY,
                check="bmad-render-config-ambiguity",
                status=DoctorStatus.OK,
                message=(f"no ambiguous config keys in the merged central config {suffix}"),
                evidence={"checked": checked},
            ),
        )

    findings: list[Finding] = []
    for name in sorted(ambiguous):
        paths = ambiguous[name]
        paths_text = ", ".join(paths)
        findings.append(
            Finding(
                source=Source.BMAD_RENDER_CONFIG_AMBIGUITY,
                check="bmad-render-config-ambiguity",
                status=DoctorStatus.WARN,
                message=(f"ambiguous config value `{name}` found at: {paths_text}"),
                evidence={"key": name, "paths": list(paths)},
            )
        )
    return tuple(findings)
