"""Meta test -- every commit-writing call site hands ``CommitPort`` redacted text (Story 82.9,
DW-FU-2-6-4, AD-34).

AD-34 names "VCS commit and PR text" as egress. ``CommitPort`` is classified egress, so its
methods take the message (and a preflight skip reason) as ``Redacted`` and every other text
parameter as a ``VcsRef``; ``GitVcs`` raises ``TypeError`` for anything else. This scan is the
other half: the *callers*. A call to one of the three methods outside the adapter must spell

- ``message=`` (and ``preflight_skip_reason=``, unless it is the literal ``None``) as a
  ``to_redacted_text(...)`` call -- the one plain-text redactor in ``core/egress.py``, so no
  call site redacts on its own and none forgets to;
- ``ref=`` / ``remote=`` (and ``merge_ref_resolving``'s second positional) as a ``VcsRef(...)``
  call.

Without it a caller that built a ``Redacted`` by hand (``Redacted(text=raw)`` performs no
redaction) would satisfy the type and still leak, and a revert of a call site to a bare ``str``
would only surface at runtime on that path.

Bounds (stated, not aspirational): a best-effort STATIC check like its AD-34 siblings. It reads the
argument expression, not what a name was bound to, so ``message=msg`` fails even when ``msg`` is a
``Redacted`` -- by design: the wrap sits at the call, where a reviewer sees it. It does not follow a
method alias, ``functools.partial`` or ``**kwargs``. ``adapters/vcs_git.py`` is the implementer and
is exempt: ``commit_paths_onto_remote_tip`` forwards its own already-``Redacted`` message to
``self.commit_paths``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import pyforge.marshal

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent
_IMPLEMENTER = PACKAGE_DIR / "adapters" / "vcs_git.py"

#: method -> {parameter: (positional index after the receiver or None, required wrapper)}
_PARAMS: dict[str, dict[str, tuple[int | None, str]]] = {
    "commit_paths": {"message": (2, "to_redacted_text")},
    "merge_ref_resolving": {"ref": (1, "VcsRef"), "message": (None, "to_redacted_text")},
    "commit_paths_onto_remote_tip": {
        "remote": (None, "VcsRef"),
        "ref": (None, "VcsRef"),
        "message": (None, "to_redacted_text"),
        "preflight_skip_reason": (None, "to_redacted_text"),
    },
}


def _callee_name(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _is_none(expr: ast.expr) -> bool:
    return isinstance(expr, ast.Constant) and expr.value is None


def _violations(tree: ast.Module) -> list[str]:
    """``line:method(param)`` for every commit-writing call whose text argument is not wrapped."""
    found: list[str] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        method = node.func.attr
        if method not in _PARAMS:
            continue
        keywords = {kw.arg: kw.value for kw in node.keywords if kw.arg}
        for param, (index, wrapper) in _PARAMS[method].items():
            if param in keywords:
                arg = keywords[param]
            elif index is not None and index < len(node.args):
                arg = node.args[index]
            else:
                continue  # an omitted optional (preflight_skip_reason) or a required one the call would TypeError on
            if param == "preflight_skip_reason" and _is_none(arg):
                continue
            if not (isinstance(arg, ast.Call) and _callee_name(arg) == wrapper):
                found.append(f"{node.lineno}:{method}({param})")
    return sorted(found)


def _call_sites(tree: ast.Module) -> list[str]:
    return [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in _PARAMS
    ]


def _modules() -> list[Path]:
    return sorted(path for path in PACKAGE_DIR.rglob("*.py") if path != _IMPLEMENTER)


def _module_id(path: Path) -> str:
    return str(path.relative_to(PACKAGE_DIR))


def test_the_scan_surface_covers_every_commit_writing_method():
    """The guard is alive, not vacuous: each of the three methods has real call sites in the tree."""
    seen: dict[str, int] = dict.fromkeys(_PARAMS, 0)
    for path in _modules():
        for method in _call_sites(ast.parse(path.read_text(encoding="utf-8"))):
            seen[method] += 1
    assert all(count > 0 for count in seen.values()), seen
    assert sum(seen.values()) >= 14, seen  # the Story 82.9 call-site census


@pytest.mark.parametrize("module_path", _modules(), ids=_module_id)
def test_every_commit_writing_call_site_redacts_its_text(module_path: Path):
    violations = _violations(ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path)))
    assert not violations, (
        f"{_module_id(module_path)}: commit-writing call(s) {violations} pass text that is not wrapped -- "
        "`message`/`preflight_skip_reason` go through to_redacted_text(...), `ref`/`remote` through VcsRef(...) "
        "(AD-34: commit text is egress; CommitPort accepts only Redacted)"
    )


def test_guard_is_alive_a_bare_str_message_fires():
    source = "vcs.commit_paths(root, paths, 'marshal: promote')\n"
    assert _violations(ast.parse(source)) == ["1:commit_paths(message)"]


def test_guard_is_alive_a_hand_wrapped_redacted_fires():
    """``Redacted(text=raw)`` satisfies the type and redacts nothing -- only ``to_redacted_text`` counts."""
    source = "vcs.commit_paths(root, paths, message=Redacted(text=raw))\n"
    assert _violations(ast.parse(source)) == ["1:commit_paths(message)"]


def test_guard_is_alive_a_name_bound_elsewhere_fires():
    source = "vcs.commit_paths(root, paths, message=msg)\n"
    assert _violations(ast.parse(source)) == ["1:commit_paths(message)"]


def test_guard_is_alive_bare_refs_and_reason_on_the_remote_tip_publish_fire():
    source = (
        "vcs.commit_paths_onto_remote_tip(root, remote='origin', ref=base, writes=w, "
        "message=to_redacted_text(m), preflight_skip_reason='why')\n"
    )
    assert _violations(ast.parse(source)) == [
        "1:commit_paths_onto_remote_tip(preflight_skip_reason)",
        "1:commit_paths_onto_remote_tip(ref)",
        "1:commit_paths_onto_remote_tip(remote)",
    ]


def test_guard_is_alive_a_bare_positional_ref_on_the_resolving_merge_fires():
    source = "vcs.merge_ref_resolving(wt, probe, resolutions=r, message=to_redacted_text(m))\n"
    assert _violations(ast.parse(source)) == ["1:merge_ref_resolving(ref)"]


def test_guard_stays_silent_on_a_fully_wrapped_call_and_a_none_reason():
    source = (
        "vcs.commit_paths(root, paths, to_redacted_text(m))\n"
        "vcs.merge_ref_resolving(wt, VcsRef(probe), resolutions=r, message=to_redacted_text(m))\n"
        "vcs.commit_paths_onto_remote_tip(root, remote=VcsRef('origin'), ref=VcsRef(base), writes=w, "
        "message=to_redacted_text(m), preflight_skip_reason=to_redacted_text(r))\n"
        "vcs.commit_paths_onto_remote_tip(root, remote=VcsRef('origin'), ref=VcsRef(base), writes=w, "
        "message=egress.to_redacted_text(m), preflight_skip_reason=None)\n"
    )
    assert _violations(ast.parse(source)) == []
