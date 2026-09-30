"""Feature-flag test family: run a story in both flag states through one fixture.

``spec-feature-flag-governance`` CAP-4 (marshal Story 74.1). Every flagged story is tested with its
flag ON and again with it OFF, through OpenFeature's own client API and the one provider the estate
allows (canopy:AD-11: one provider, one tree, no egress). Waffle, LaunchDarkly, an environment
variable and a mock of ``waffle.flag_is_active`` are not flag sources here.

Four pieces:

* ``installed_flags`` / ``make_flag_provider_fixture`` -- OpenFeature's ``InMemoryProvider`` holding
  the test's flag values, the prior provider put back afterwards so nothing leaks between tests.
  A station binds the fixture once in its ``conftest.py``::

      flag_provider = make_flag_provider_fixture()

* ``flag_states(key)`` -- an ON/OFF parametrize helper (ids ``on`` and ``off``): one decorated test,
  two runs.
* ``flagd_tree`` -- a temporary flagd FILE tree in the shape of ``src/platform/config/flags.json``,
  for integration tests and for Playwright against a server started on it.
* ``assert_flag_off_verb`` -- the CLI OFF case of the Spec's Q3: the verb stays listed in ``--help``,
  marked disabled, and refuses with the station's usage exit code.

``openfeature`` and ``pytest`` are imported inside the functions that need them, never at module
level: ``tests/packaging/test_dependency_completeness.py`` reads module-level imports only, and
this keeps a bare ``import pyforge.testing_kit`` free of both.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TypeVar

from pyforge.testing_kit.cli_runner import CliResult, invoke_cli

F = TypeVar("F", bound=Callable[..., Any])

ON = "on"
OFF = "off"

# The variants of a boolean flag in the tree: `src/platform/config/flags.json`'s own shape.
_VARIANTS: dict[str, bool] = {ON: True, OFF: False}

FLAG_PROVIDER_FIXTURE = "flag_provider"


@contextmanager
def installed_flags(values: Mapping[str, bool]) -> Iterator[Any]:
    """Install OpenFeature's ``InMemoryProvider`` holding ``values`` as the default provider.

    ``values`` maps a flag key to ``True`` (ON) or ``False`` (OFF). Yields the provider. On exit the
    default provider that was live on entry is set again -- ``set_provider`` shuts the provider it
    replaces down, so putting the prior one back is what keeps a test from leaking state into the next.
    """
    from openfeature import api
    from openfeature.provider.in_memory_provider import InMemoryFlag, InMemoryProvider

    flags: dict[str, InMemoryFlag[bool]] = {}
    for key, value in values.items():
        if not isinstance(value, bool):
            raise ValueError(f"flag {key!r}: expected True (ON) or False (OFF), got {value!r}")
        flags[key] = InMemoryFlag(default_variant=ON if value else OFF, variants=dict(_VARIANTS))

    prior = api.get_client().provider
    provider = InMemoryProvider(flags)
    api.set_provider_and_wait(provider)
    try:
        yield provider
    finally:
        api.set_provider_and_wait(prior)


def make_flag_provider_fixture() -> Callable[..., Any]:
    """Build the ``flag_provider`` pytest fixture; bind it in a ``conftest.py``.

    The fixture installs the ``InMemoryProvider`` for the test and yields the ``{key: bool}`` mapping
    it was given: ``request.param`` when parametrized (``flag_states`` does this), empty otherwise. A
    factory, not a module-level fixture, so ``pytest`` stays out of the kit's module-level imports.
    """
    import pytest

    @pytest.fixture(name=FLAG_PROVIDER_FIXTURE)
    def flag_provider(request: Any) -> Iterator[dict[str, bool]]:
        values = dict(getattr(request, "param", None) or {})
        with installed_flags(values):
            yield values

    return flag_provider


def flag_states(key: str) -> Callable[[F], F]:
    """Decorator: run the test twice, with ``key`` ON then OFF (pytest ids ``on`` and ``off``).

    It parametrizes the ``flag_provider`` fixture indirectly and adds it through ``usefixtures``, so
    the test needs no argument to be run twice; a test that wants the state takes ``flag_provider``
    and reads ``flag_provider[key]``.
    """
    import pytest

    parametrize = pytest.mark.parametrize(
        FLAG_PROVIDER_FIXTURE,
        [{key: True}, {key: False}],
        ids=[ON, OFF],
        indirect=True,
    )
    usefixtures = pytest.mark.usefixtures(FLAG_PROVIDER_FIXTURE)

    def decorate(test: F) -> F:
        return usefixtures(parametrize(test))  # type: ignore[no-any-return]

    return decorate


def flagd_tree(tmp_path: Path, flags: Mapping[str, str], *, name: str = "flags.json") -> Path:
    """Write a temporary flagd FILE tree and return its path.

    ``flags`` maps a flag key to its default variant, ``"on"`` or ``"off"``. The file has the shape of
    ``src/platform/config/flags.json`` -- ``flags`` -> key -> ``state``, ``variants``, ``defaultVariant``
    -- for integration tests and for Playwright against a server started on it. It writes JSON only
    and imports no provider.
    """
    if not isinstance(flags, dict):
        raise ValueError(f"flags must be a dict of {{key: 'on' | 'off'}}, got {type(flags).__name__}")
    tree: dict[str, dict[str, Any]] = {"flags": {}}
    for key, variant in flags.items():
        if variant not in _VARIANTS:
            raise ValueError(f"flag {key!r}: variant must be {ON!r} or {OFF!r}, got {variant!r}")
        tree["flags"][key] = {
            "state": "ENABLED",
            "variants": dict(_VARIANTS),
            "defaultVariant": variant,
        }
    path = Path(tmp_path) / name
    path.write_text(json.dumps(tree, indent=2) + "\n", encoding="utf-8")
    return path


def _entry_blocks(output: str, verb: str) -> list[str]:
    """The ``--help`` entries for ``verb``: each line that opens with it, plus its wrapped continuation."""
    lines = output.splitlines()
    blocks: list[str] = []
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.split(None, 1)[:1] != [verb]:
            continue
        indent = len(line) - len(stripped)
        block = [line]
        for follow in lines[index + 1 :]:
            if not follow.strip() or len(follow) - len(follow.lstrip()) <= indent:
                break
            block.append(follow)
        blocks.append("\n".join(block))
    return blocks


def assert_flag_off_verb(
    main: Callable[[list[str]], int | None],
    verb: str,
    usage_code: int,
    *,
    args: Sequence[str] = (),
) -> CliResult:
    """Assert the Spec's Q3 OFF case for ``verb`` on the CLI ``main``; raise ``AssertionError`` if not met.

    With its flag OFF the verb is still listed in ``--help``, marked disabled, and running it exits with
    the station's usage code (``usage_code``). ``args`` follow the verb when it needs arguments to get
    past argument parsing. Returns the result of running the verb.
    """
    listing = invoke_cli(main, ["--help"]).output
    if not re.search(rf"(?<![\w-]){re.escape(verb)}(?![\w-])", listing):
        raise AssertionError(f"verb {verb!r} is absent from --help; a flag-OFF verb stays listed, marked disabled")
    if not any("disabled" in block.lower() for block in _entry_blocks(listing, verb)):
        raise AssertionError(f"verb {verb!r} is listed in --help but not marked disabled")
    result = invoke_cli(main, [verb, *args])
    if result.exit_code != usage_code:
        raise AssertionError(
            f"verb {verb!r} with its flag OFF exited {result.exit_code}; expected the station's usage code {usage_code}"
        )
    return result
