"""Unit tests for ``pyforge.marshal.core.context.MarshalContext`` (Story
5.6, FR-65/AD-50) -- construction, plus the resolution matrix for
``cli/main.py::_resolve_context`` (the impure resolution function, tested
here rather than in ``core`` since it lives in ``cli/`` and does real file
I/O -- AD-4 forbids that under ``core/**``)."""

from __future__ import annotations

import argparse

import pytest

from pyforge.marshal.core.context import MarshalContext
from pyforge.marshal.core import policy as policy_core
from pyforge.marshal.core.policy import EffectivePolicy


def _effective_policy() -> EffectivePolicy:
    effective, _findings = policy_core.compose(project_slug="acme", project={}, flags={})
    return effective


def test_marshal_context_is_frozen():
    context = MarshalContext(slug="acme", loop_home=None, policy=_effective_policy(), story=None)
    with pytest.raises(AttributeError):
        context.slug = "other"  # type: ignore[misc]


def test_marshal_context_carries_every_field():
    policy = _effective_policy()
    context = MarshalContext(slug="acme", loop_home=None, policy=policy, story="1.2")
    assert context.slug == "acme"
    assert context.loop_home is None
    assert context.policy is policy
    assert context.story == "1.2"


def test_marshal_context_construction_does_no_io(tmp_path, monkeypatch):
    """AD-4: construction is a pure value assembly -- no filesystem probe,
    even for a ``loop_home`` path that does not exist on disk."""
    nonexistent = tmp_path / "does-not-exist"
    context = MarshalContext(
        slug="acme", loop_home=nonexistent, policy=_effective_policy(), story=None
    )
    assert context.loop_home == nonexistent
    assert not nonexistent.exists()


# --- cli/main.py::_resolve_context's own resolution matrix -----------------


def _args(*, project: str | None = None, story: str | None = None):
    ns = argparse.Namespace(project=project)
    if story is not None:
        ns.story = story
    return ns


def test_resolve_context_returns_none_without_a_project_flag():
    from pyforge.marshal.cli.main import _resolve_context

    assert _resolve_context(argparse.Namespace()) is None
    assert _resolve_context(_args(project=None)) is None


def test_resolve_context_reads_the_conventional_policy_path(tmp_path, monkeypatch):
    from pyforge.marshal.cli import config as config_module
    from pyforge.marshal.cli.main import _resolve_context

    monkeypatch.setattr(config_module, "repo_root", lambda: tmp_path)
    policy_dir = tmp_path / "_bmad-output" / "projects" / "acme" / "planning-artifacts"
    policy_dir.mkdir(parents=True)
    (policy_dir / "marshal-policy.toml").write_text(
        'verify_commands = ["true"]\n', encoding="utf-8"
    )

    context = _resolve_context(_args(project="acme"))

    assert context is not None
    assert context.slug == "acme"
    assert context.policy.verify_commands.value == ("true",)
    assert context.loop_home is not None
    assert context.loop_home.name == "acme"


def test_resolve_context_with_no_conventional_policy_still_composes_defaults(
    tmp_path, monkeypatch
):
    from pyforge.marshal.cli import config as config_module
    from pyforge.marshal.cli.main import _resolve_context

    monkeypatch.setattr(config_module, "repo_root", lambda: tmp_path)

    context = _resolve_context(_args(project="no-such-project"))

    assert context is not None
    assert context.slug == "no-such-project"
    assert context.policy.verify_commands.value == ()


def test_resolve_context_malformed_slug_omits_loop_home(tmp_path, monkeypatch):
    from pyforge.marshal.cli import config as config_module
    from pyforge.marshal.cli.main import _resolve_context

    monkeypatch.setattr(config_module, "repo_root", lambda: tmp_path)

    context = _resolve_context(_args(project="../escape"))

    assert context is not None
    assert context.loop_home is None


def test_resolve_context_traversal_slug_never_reads_outside_the_project_tree(
    tmp_path, monkeypatch
):
    """Code review (2026-08-07, Edge Case Hunter, the single most severe
    finding against this story): the original version had no
    `_is_valid_project_slug` gate before touching the filesystem, letting
    a traversal-shaped slug fold an out-of-tree file's content into
    `project_data`/`compose()` -- the same class of bug `cli/gate.py`'s
    own comments document as a real, previously-live issue for this exact
    lookup. A real out-of-tree file is planted here; if the guard is
    working, `_resolve_context` never reads it (the malformed slug's
    `conventional_project_policy_path` is never even probed)."""
    from pyforge.marshal.cli import config as config_module
    from pyforge.marshal.cli.main import _resolve_context

    monkeypatch.setattr(config_module, "repo_root", lambda: tmp_path)
    secret = tmp_path.parent / "secret-outside-repo.toml"
    secret.write_text('verify_commands = ["leaked"]\n', encoding="utf-8")
    try:
        context = _resolve_context(_args(project="../secret-outside-repo"))
        assert context is not None
        assert context.policy.verify_commands.value == ()
    finally:
        secret.unlink(missing_ok=True)


def test_resolve_context_permission_error_on_probe_never_crashes(tmp_path, monkeypatch):
    """Code review (2026-08-07, Edge Case Hunter): a bare `is_file()` call
    propagates `PermissionError` (Python 3.12+) for an unsearchable
    ancestor directory -- uncaught, that would crash `main()`'s own
    documented "never raises" contract for any `--project` invocation
    hitting this condition."""
    from pyforge.marshal.cli import config as config_module
    from pyforge.marshal.cli.main import _resolve_context

    monkeypatch.setattr(config_module, "repo_root", lambda: tmp_path)

    def _raises_permission_error(self):
        raise PermissionError("simulated unsearchable ancestor directory")

    monkeypatch.setattr(type(tmp_path), "is_file", _raises_permission_error, raising=False)

    context = _resolve_context(_args(project="acme"))

    assert context is not None
    assert context.policy.verify_commands.value == ()


def test_resolve_context_carries_story_when_present(tmp_path, monkeypatch):
    from pyforge.marshal.cli import config as config_module
    from pyforge.marshal.cli.main import _resolve_context

    monkeypatch.setattr(config_module, "repo_root", lambda: tmp_path)

    context = _resolve_context(_args(project="acme", story="2.3"))

    assert context is not None
    assert context.story == "2.3"
