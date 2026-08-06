"""Landing rules as structured values (Story 4.7, architecture spine AD-40).

``LandingRule`` is the ONE shape unifying AD-40's "labels" and "repo-specific
triggers" categories -- splitting them into two parallel lists would let a
future rule need "half" of each shape with nowhere clean to live (see this
package's own spec's Design Notes). ``rule_applies`` is the pure glob match
every later consumer (Stories 4.4/4.8) must import and reuse rather than
reimplement -- this story only proves the shape is meaningful via its own
tests; it wires nothing to any CLI action.

This repo's own two real landing rules (``CLAUDE.md``'s PR CI gates section)
are the worked example, and each needs the OPPOSITE match direction
(**corrected in review, 2026-08-06**): a ``maintenance-label`` rule
(``trigger_mode="exclude"``) fires when a change touches anything OUTSIDE
``recipes/**``, while an ``environment-yaml-sync`` rule
(``trigger_mode="include"``) -- UNGATED, i.e. it applies regardless of any
label another rule would add -- fires when ``pixi.toml`` DOES change. A
single unparameterized match direction cannot represent both of this repo's
own real rules correctly; ``trigger_mode`` is therefore required, with no
default, so every rule states its own direction explicitly.

This module is pure data: no I/O, no subprocess, no clock, no
``pyforge.marshal.adapters`` (AD-4) -- only ``dataclasses``, ``fnmatch``, and
``typing`` (a pure string-matching stdlib module, not a filesystem walk).
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import Literal


@dataclass(frozen=True)
class LandingRule:
    """One landing rule: a glob-scoped trigger plus its gating consequence.

    ``name`` -- non-empty, unique within a ``landing_rules`` tuple (enforced
    by ``core/policy.py``'s ``_valid_landing_rules``, not here -- this
    dataclass has no notion of "the other rules in the tuple").

    ``trigger_path_glob`` -- a glob (``fnmatch`` syntax, matched
    case-sensitively via ``fnmatchcase`` -- repository paths are
    case-sensitive on the git level regardless of the host OS).

    ``trigger_mode`` -- ``"exclude"`` or ``"include"``, no default: every
    rule states its own match direction explicitly rather than inheriting an
    assumption. ``"exclude"`` fires when at least one changed path does NOT
    match ``trigger_path_glob`` (mirrors this repo's own real
    ``maintenance-label`` rule: "any change outside ``recipes/**``").
    ``"include"`` fires when at least one changed path DOES match
    ``trigger_path_glob`` (mirrors this repo's own real
    ``environment-yaml-sync`` rule: "``pixi.toml`` changed").

    ``label``/``required_check`` -- each optional, but ``core/policy.py``'s
    validator rejects a rule with NEITHER set (a rule that does neither is
    meaningless).

    ``ungated`` -- defaults ``False``. ``True`` means this rule applies
    regardless of any label another rule would add -- the literal shape of
    this repo's own ``environment.yaml`` sync check, the exception rather
    than the norm (see this package's own spec's Design Notes for why the
    default is ``False``, not ``True``). ``core/policy.py``'s validator
    rejects ``ungated=True`` on a rule with no ``required_check`` set --
    "ungated" describes a check that can't be suppressed by a label, which
    is meaningless on a label-only rule.
    """

    name: str
    trigger_path_glob: str
    trigger_mode: Literal["exclude", "include"]
    label: str | None = None
    required_check: str | None = None
    ungated: bool = False


def rule_applies(rule: LandingRule, changed_paths: tuple[str, ...]) -> bool:
    """``True`` if ``rule`` fires against ``changed_paths``, per its own
    ``trigger_mode``:

    - ``"exclude"``: at least one entry does NOT match ``trigger_path_glob``
      (this repo's own real ``maintenance`` rule: "any change outside
      ``recipes/**``").
    - ``"include"``: at least one entry DOES match ``trigger_path_glob``
      (this repo's own real ``environment-yaml-sync`` rule: "``pixi.toml``
      changed").

    An empty ``changed_paths`` never fires either way (there is no path to
    be outside or inside the glob). Matching is case-sensitive
    (``fnmatchcase``, never the platform-normalizing ``fnmatch``)."""
    if rule.trigger_mode == "include":
        return any(fnmatchcase(path, rule.trigger_path_glob) for path in changed_paths)
    return any(not fnmatchcase(path, rule.trigger_path_glob) for path in changed_paths)


def landing_rule_to_dict(rule: LandingRule) -> dict[str, object]:
    """The single canonical ``LandingRule`` -> plain-``dict`` conversion
    (review finding P4): ``core/policy.py``'s ``_to_plain`` (for
    ``content_hash``) and ``cli/config.py``'s ``_json_safe`` (for the wire
    payload) both needed this exact field list, and before this function
    existed each hand-rolled its own copy -- a duplicate serialization with
    no single owner, so a future ``LandingRule`` field addition would have
    had two call sites to remember in lockstep. Both now call this instead."""
    return {
        "name": rule.name,
        "trigger_path_glob": rule.trigger_path_glob,
        "trigger_mode": rule.trigger_mode,
        "label": rule.label,
        "required_check": rule.required_check,
        "ungated": rule.ungated,
    }
