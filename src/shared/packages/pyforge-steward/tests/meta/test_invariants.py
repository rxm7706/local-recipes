"""Invariants that fail silently if broken, so they are pinned rather than trusted."""

from __future__ import annotations

from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[2] / "src" / "pyforge"


def test_namespace_stays_implicit():
    """PEP 420: shipping src/pyforge/__init__.py would shadow the sibling stations.

    Nothing errors at build time — it only surfaces when two pyforge packages are
    installed together, which is precisely when it is most expensive to find.
    """
    assert not (PKG_ROOT / "__init__.py").exists()
    assert (PKG_ROOT / "steward" / "__init__.py").exists()


def test_no_cli_framework_dependency():
    """FR-41 / NFR-10 — argparse only; click and typer are forbidden.

    Parses the manifest instead of grepping it. The first version of this test
    scanned raw text and failed on this very package, because the comment
    explaining that click is forbidden *contains the word click*. A matcher that
    does not assert WHAT it matched is not evidence.
    """
    try:
        import tomllib
    except ImportError:  # pragma: no cover
        import tomli as tomllib  # type: ignore[no-redef]

    manifest = tomllib.loads((PKG_ROOT.parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    project = manifest.get("project", {})
    declared = list(project.get("dependencies", []))
    for extras in (project.get("optional-dependencies") or {}).values():
        declared += list(extras)

    banned = {"click", "typer"}
    found = [d for d in declared if d.split("[")[0].split(">")[0].split("=")[0].strip().lower() in banned]
    assert not found, f"CLI framework forbidden by FR-41: {found}"


def test_no_duty_module_calls_sys_exit():
    """AD-8: main() is the SOLE owner of the exit code.

    A `sys.exit()` anywhere but cli.py would take the decision away from main()
    and bypass its projection — the exact failure that produces an undocumented
    bare 1.
    """
    import ast

    steward = PKG_ROOT / "steward"
    offenders: list[str] = []
    for path in steward.rglob("*.py"):
        if path.name == "cli.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            # AST, not a substring scan: the first version of this test matched
            # the phrase "sys.exit()" inside a DOCSTRING and failed on a file
            # that never calls it. A matcher that does not assert what it
            # matched is not evidence.
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            if (
                isinstance(fn, ast.Attribute)
                and fn.attr == "exit"
                and isinstance(fn.value, ast.Name)
                and fn.value.id == "sys"
            ):
                offenders.append(f"{path.name}:{node.lineno}")
    assert not offenders, f"sys.exit() call outside cli.py: {offenders}"


def test_no_rotation_scheduler_exists():
    """Story 1.4 / FR-3 / PRD D1: key rotation is on-demand only.

    No calendar, cron, or time-based auto-rotation path may exist anywhere
    in the package — checked via AST `import`/`import from` statements, not
    a raw text scan: the sibling `test_no_cli_framework_dependency` test
    already learned that lesson the hard way (a comment merely NAMING a
    forbidden thing is not evidence of using it — this module's own
    docstring says "no scheduler exists", which a text scan would flag as
    if it imported one). A future "just add a nightly rotation cron" PR
    fails loudly here instead of landing silently.
    """
    import ast

    banned_modules = {"sched", "schedule", "apscheduler", "celery", "cron", "croniter"}
    offenders: list[str] = []
    for path in (PKG_ROOT / "steward").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            for name in names:
                if name.lower() in banned_modules:
                    offenders.append(f"{path.name}:{node.lineno} imports {name!r}")
    assert not offenders, f"scheduler-shaped import found (rotation must be on-demand only): {offenders}"


def test_keys_list_output_never_contains_a_planted_secret_value(tmp_path):
    """Story 1.5 / NFR-7: `steward keys list` must never print a raw secret
    value, under ANY flag combination.

    Plants a real-looking secret string inside the file `identity_path`
    points at (an `age` identity file is exactly what this would be in
    production) and proves by execution -- not by reading `format_inventory`'s
    source -- that neither text nor `--json` output ever dereferences that
    pointer to read its content.
    """
    from pyforge.steward.keys import KeyIdentityEntry, format_inventory

    planted_secret = "AGE-SECRET-KEY-1PLANTEDVALUETHATMUSTNEVERAPPEARINLISTOUTPUT"
    identity_file = tmp_path / "identity.txt"
    identity_file.write_text(f"# created: 2026-08-07\n{planted_secret}\n")

    entry = KeyIdentityEntry(
        name="jfrog",
        scope="jfrog",
        provenance="issued",
        status="active",
        last_rotated="2026-08-07T00:00:00+00:00",
        identity_path=str(identity_file),
        secrets=(),
    )

    text_output = format_inventory((entry,), as_json=False)
    json_output = format_inventory((entry,), as_json=True)

    assert planted_secret not in text_output
    assert planted_secret not in json_output


def test_no_third_party_provider_api_client_imported():
    """Story 1.7 / this story's own second AC: `keys revoke` is a local
    record-and-guide action only -- no JFrog/GitHub/Anthropic (or any other
    provider) API client import anywhere in the package.

    AST-based (imports only), same rationale as `test_no_rotation_scheduler_
    exists` -- a docstring or remediation-guidance STRING naming a provider
    (e.g. "JFrog", "GitHub") is expected and correct; importing a client
    library for one is not.
    """
    import ast

    banned_modules = {
        "requests",
        "httpx",
        "urllib3",
        "github",
        "pygithub",
        "gitlab",
        "python-gitlab",
        "anthropic",
        "boto3",
        "google",
        "artifactory",
        "dohq_artifactory",
        "pyjfrog",
    }
    offenders: list[str] = []
    for path in (PKG_ROOT / "steward").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            for name in names:
                if name.lower() in banned_modules:
                    offenders.append(f"{path.name}:{node.lineno} imports {name!r}")
    assert not offenders, f"third-party provider API client import found: {offenders}"


def test_deploy_has_no_story_status_derivation():
    """Story 5.2 / AD-71 / AD-1: `deploy.py` may check whether its tracked
    ledger EXISTS and is SHAPED like one, but must never re-derive an
    individual story's status itself -- that computation stays inside the
    wrapped `dashboard-gen` subprocess (`pyforge.doctor.sources.fleet_scan`'s own
    `parse_sprint_status`), never reimplemented here.

    AST-based, same rationale as `test_no_rotation_scheduler_exists`/
    `test_no_third_party_provider_api_client_imported`: (1) no `import re`
    or `import yaml` -- either would be the toolkit for parsing individual
    ledger entries rather than just checking presence/shape via a substring
    check; (2) no `ast.Compare` anywhere in the module against a
    story-status vocabulary string literal (`done`, `in-progress`,
    `backlog`, `blocked`, `pending`, `active`, `gated`) -- comparing against
    one of these would BE the re-derivation this story exists to prevent.
    """
    import ast

    deploy_path = PKG_ROOT / "steward" / "deploy.py"
    tree = ast.parse(deploy_path.read_text(encoding="utf-8"))

    banned_modules = {"re", "yaml"}
    status_vocabulary = {
        "done",
        "in-progress",
        "backlog",
        "blocked",
        "pending",
        "active",
        "gated",
    }
    offenders: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in banned_modules:
                    offenders.append(f"deploy.py:{node.lineno} imports {alias.name!r}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in banned_modules:
                offenders.append(f"deploy.py:{node.lineno} imports from {node.module!r}")
        elif isinstance(node, ast.Compare):
            operands = [node.left, *node.comparators]
            for operand in operands:
                if (
                    isinstance(operand, ast.Constant)
                    and isinstance(operand.value, str)
                    and operand.value in status_vocabulary
                ):
                    offenders.append(f"deploy.py:{node.lineno} compares against status literal {operand.value!r}")

    assert not offenders, f"story-status derivation found in deploy.py: {offenders}"


def test_no_cost_integration_sdk_imported_in_budget():
    """Story 4.3 / AD-6 / this story's own second AC: `budget.py`'s
    "honest stub" property is structural, not just behavioral -- no
    cloud-cost SDK or Kubecost/OpenCost/Infracost-class client import may
    exist ANYWHERE in the package, not only in `budget.py` (a helper
    module quietly carrying the import would be just as much of a lie as
    `budget.py` doing it directly).

    AST-based (imports only), identical rationale to
    `test_no_rotation_scheduler_exists`/
    `test_no_third_party_provider_api_client_imported` -- `budget.py`'s
    own module docstring and `_NOT_CONFIGURED_MESSAGE` NAME every one of
    these products in prose, which a text scan would misflag as evidence
    of importing one.
    """
    import ast

    banned_modules = {
        "kubecost",
        "opencost",
        "infracost",
        "boto3",
        "google",
        "azure",
        "stripe",
        "awscostexplorer",
        "cloudability",
        "cloudhealth",
        "cloudcheckr",
        "vantage",
        "kubecostgrpc",
        "kubecost_client",
    }
    offenders: list[str] = []
    for path in (PKG_ROOT / "steward").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            for name in names:
                if name.lower() in banned_modules:
                    offenders.append(f"{path.name}:{node.lineno} imports {name!r}")
    assert not offenders, f"cost-integration SDK import found (AD-6: budget v1 is a stub): {offenders}"


_DASHBOARD_BANNED_MODULES = {"django", "channels"}
_DASHBOARD_BANNED_DOTTED_PREFIX = "pyforge.steward.dashboard"
# Sentinel for a relative import whose level climbs past the top-level
# package -- unresolvable, and therefore reported rather than guessed at.
_DASHBOARD_UNRESOLVABLE_RELATIVE = "<unresolvable-relative-import>"


def _is_banned_dashboard_dotted(name: str) -> bool:
    return name == _DASHBOARD_BANNED_DOTTED_PREFIX or name.startswith(_DASHBOARD_BANNED_DOTTED_PREFIX + ".")


def _find_banned_dashboard_imports(
    source: str,
    own_package_parts: tuple[str, ...],
    label: str,
    *,
    ban_dashboard_package: bool = True,
) -> list[str]:
    """Return one string per offending import statement in `source`.

    `ban_dashboard_package` selects which rule is being enforced. Outside
    `dashboard/` (the default) importing the dashboard package is itself the
    violation. INSIDE `dashboard/`, only `django`/`channels` are of interest —
    a module there importing its own siblings is normal, so the caller turns
    that half off.

    `own_package_parts` is the dotted package the source file itself lives
    in (e.g. `("pyforge", "steward")`), used to resolve relative imports
    (`node.level`) to an absolute dotted path.

    A relative level that climbs past the top-level package is reported as an
    offender rather than silently truncated (review pass 3): the arithmetic
    below would otherwise turn `from ...dashboard import cache` in
    `pyforge/steward/` into the bare `"dashboard"` and let it through. Such an
    import cannot execute at all (Python raises "attempted relative import
    beyond top-level package"), so flagging it reports broken code instead of
    losing it -- a guard must never resolve an import it cannot account for
    into something that looks innocent.
    """
    import ast

    def _is_banned(name: str) -> bool:
        if name.split(".")[0] in _DASHBOARD_BANNED_MODULES:
            return True
        return ban_dashboard_package and _is_banned_dashboard_dotted(name)

    def _resolved_module(node: ast.ImportFrom) -> str | None:
        if node.level == 0:
            return node.module
        keep = len(own_package_parts) - (node.level - 1)
        if keep <= 0:
            return _DASHBOARD_UNRESOLVABLE_RELATIVE
        parts = list(own_package_parts[:keep])
        if node.module:
            parts += node.module.split(".")
        return ".".join(parts) if parts else None

    offenders: list[str] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_banned(alias.name):
                    offenders.append(f"{label}:{node.lineno} imports {alias.name!r}")
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolved_module(node)
            if resolved == _DASHBOARD_UNRESOLVABLE_RELATIVE:
                offenders.append(
                    f"{label}:{node.lineno} has a relative import climbing "
                    f"past the top-level package (level {node.level}) — "
                    f"unresolvable, so it cannot be cleared of importing "
                    f"dashboard/django/channels"
                )
                continue
            if resolved:
                if _is_banned(resolved):
                    offenders.append(f"{label}:{node.lineno} imports from {resolved!r}")
                    continue
            # The banned target may be named as an imported SYMBOL rather
            # than as part of the module path, e.g.
            # `from pyforge.steward import dashboard`.
            for alias in node.names:
                full = f"{resolved}.{alias.name}" if resolved else alias.name
                if _is_banned(full):
                    offenders.append(f"{label}:{node.lineno} imports {full!r}")
    return offenders


def test_no_module_outside_dashboard_imports_dashboard_django_or_channels():
    """Story 9.1: `pyforge.steward.dashboard` ships ONLY behind the
    `pyforge-steward[dashboard]` optional extra, never a base dependency.
    A base-package module importing `pyforge.steward.dashboard`, `django`,
    or `channels` would silently make the extra mandatory for every existing
    duty, breaking an install that never opted into `[dashboard]`.

    Scope note (corrected in review pass 3): this flags EVERY import of those
    names anywhere in the file, not only module-level ones — `ast.walk`
    descends into function bodies, `if TYPE_CHECKING:` blocks and
    `try/except ImportError` shapes alike. That is deliberate and matches the
    three sibling guards in this file: it over-flags rather than under-flags,
    and a lazy or optional import is not exempted today because nothing needs
    one. The docstring previously said "at module level", which the code has
    never actually implemented.

    The one direction it UNDER-flags (stated in review pass 4; the note above
    described only the over-flagging): it reads `ast.Import`/`ast.ImportFrom`
    nodes, so a dynamic import — `importlib.import_module("django")`,
    `__import__`, `exec` — is invisible to it. Every sibling guard here shares
    the limitation, so it is not treated as a defect; it is written down
    because dynamic import is the idiomatic way to reach an OPTIONAL
    dependency. Story 65.1 reached for exactly that shape, and it is one of
    the sanctioned base→dashboard reaches: `sprint_ledger_query.sync_to_postgres`
    calls `importlib.import_module("pyforge.steward.dashboard.passport_sync")`
    inside the function, refusing (never falling back) on `ImportError`, so the
    base package keeps working without the extra. Story 61.1 added a second,
    identically-shaped reach: `corridor.load_extract` calls
    `importlib.import_module("pyforge.steward.dashboard.corridor_load")`. The
    assertions below pin the narrower claim each sanction rests on — neither
    `sprint_ledger_query.py` nor `corridor.py` has a module-level `django` /
    `channels` / `pyforge.steward.dashboard` import — since `ast.walk` alone
    cannot tell a lazy reach from a top-level dependency.

    AST-based (imports only), identical rationale to
    `test_no_rotation_scheduler_exists`/
    `test_no_third_party_provider_api_client_imported` -- this module's own
    docstrings and comments name "django" and "channels" freely in prose,
    which a text scan would misflag as evidence of importing them.

    The detection logic lives in `_find_banned_dashboard_imports` above,
    shared with `test_dashboard_import_guard_catches_symbol_and_relative_
    import_shapes` below, which proves by execution (not by reading this
    docstring) that the two blind spots review pass 1 found are actually
    fixed.
    """
    steward_dir = PKG_ROOT / "steward"
    dashboard_dir = steward_dir / "dashboard"
    offenders: list[str] = []
    for path in steward_dir.rglob("*.py"):
        if dashboard_dir in path.parents:
            continue
        # Derive each file's OWN package rather than assuming every file sits
        # directly in `pyforge.steward` (review pass 2). `rglob` descends into
        # subpackages, and a hardcoded depth resolves their relative imports
        # wrong in both directions -- a real `from ..dashboard import cache`
        # in `steward/sub/` would have resolved to `pyforge.dashboard` and
        # gone unflagged, which is the failure mode a guard must never have.
        own_package_parts = path.relative_to(PKG_ROOT.parent).with_suffix("").parts[:-1]
        offenders += _find_banned_dashboard_imports(path.read_text(encoding="utf-8"), own_package_parts, path.name)
    assert not offenders, f"dashboard/django/channels import found outside dashboard/: {offenders}"

    # The sanctioned dynamic reach (docstring above) stays a lazy, in-function
    # one: nothing at MODULE level of `sprint_ledger_query.py` names django,
    # channels, or the dashboard package -- that would make the extra a base
    # dependency by construction, whatever the function bodies do.
    import ast

    module = ast.parse((steward_dir / "sprint_ledger_query.py").read_text(encoding="utf-8"))
    top_level: list[str] = []
    for node in module.body:
        if isinstance(node, ast.Import):
            top_level += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            top_level.append(node.module)
    banned_top_level = [
        name
        for name in top_level
        if name.split(".")[0] in _DASHBOARD_BANNED_MODULES or _is_banned_dashboard_dotted(name)
    ]
    assert not banned_top_level, (
        f"sprint_ledger_query.py imports {banned_top_level} at module level -- the "
        f"dashboard extra may only be reached lazily, inside sync_to_postgres"
    )
    assert "pyforge.steward.dashboard.passport_sync" in (steward_dir / "sprint_ledger_query.py").read_text(
        encoding="utf-8"
    ), "the sanctioned lazy reach into passport_sync is expected to exist"

    # Story 61.1's corridor.py added a second sanctioned lazy reach, into
    # dashboard/corridor_load.py — same shape, same narrower claim pinned.
    corridor_module = ast.parse((steward_dir / "corridor.py").read_text(encoding="utf-8"))
    corridor_top_level: list[str] = []
    for node in corridor_module.body:
        if isinstance(node, ast.Import):
            corridor_top_level += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            corridor_top_level.append(node.module)
    banned_corridor_top_level = [
        name
        for name in corridor_top_level
        if name.split(".")[0] in _DASHBOARD_BANNED_MODULES or _is_banned_dashboard_dotted(name)
    ]
    assert not banned_corridor_top_level, (
        f"corridor.py imports {banned_corridor_top_level} at module level -- the "
        f"dashboard extra may only be reached lazily, inside load_extract"
    )
    assert "pyforge.steward.dashboard.corridor_load" in (steward_dir / "corridor.py").read_text(encoding="utf-8"), (
        "the sanctioned lazy reach into corridor_load is expected to exist"
    )

    # Story 61.2's passport.py added a third sanctioned lazy reach, into
    # dashboard/passport_mint.py — same shape, same narrower claim pinned.
    passport_module = ast.parse((steward_dir / "passport.py").read_text(encoding="utf-8"))
    passport_top_level: list[str] = []
    for node in passport_module.body:
        if isinstance(node, ast.Import):
            passport_top_level += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            passport_top_level.append(node.module)
    banned_passport_top_level = [
        name
        for name in passport_top_level
        if name.split(".")[0] in _DASHBOARD_BANNED_MODULES or _is_banned_dashboard_dotted(name)
    ]
    assert not banned_passport_top_level, (
        f"passport.py imports {banned_passport_top_level} at module level -- the "
        f"dashboard extra may only be reached lazily, inside mint_vendor_passport"
    )
    assert "pyforge.steward.dashboard.passport_mint" in (steward_dir / "passport.py").read_text(encoding="utf-8"), (
        "the sanctioned lazy reach into passport_mint is expected to exist"
    )

    # Story 61.3's glass.py added a fourth sanctioned lazy reach, into
    # dashboard/glass_query.py — same shape, same narrower claim pinned.
    glass_module = ast.parse((steward_dir / "glass.py").read_text(encoding="utf-8"))
    glass_top_level: list[str] = []
    for node in glass_module.body:
        if isinstance(node, ast.Import):
            glass_top_level += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            glass_top_level.append(node.module)
    banned_glass_top_level = [
        name
        for name in glass_top_level
        if name.split(".")[0] in _DASHBOARD_BANNED_MODULES or _is_banned_dashboard_dotted(name)
    ]
    assert not banned_glass_top_level, (
        f"glass.py imports {banned_glass_top_level} at module level -- the "
        f"dashboard extra may only be reached lazily, inside compute_glass_reading"
    )
    assert "pyforge.steward.dashboard.glass_query" in (steward_dir / "glass.py").read_text(encoding="utf-8"), (
        "the sanctioned lazy reach into glass_query is expected to exist"
    )


def test_dashboard_middleware_and_declarations_stay_django_free():
    """Review pass 3: the guard above SKIPS everything under `dashboard/`, so
    nothing pinned the narrower claim that `middleware.py` and
    `declarations.py` import neither `django` nor `channels` -- even though
    `__init__.py`, both modules' own docstrings, and the story spec's Design
    Notes all assert it, and `tests/unit/test_dashboard_middleware.py` /
    `test_dashboard_declarations.py` rely on it by importing them with no
    `pytest.importorskip`.

    Without this, a later Epic 9 story adding `from django.http import ...`
    to `middleware.py` would turn those two test modules into collection
    ERRORS in any environment without the `[dashboard]` extra, with nothing
    failing first to say why. That environment is exactly the one the story's
    last acceptance criterion is about, and it has no live instance yet -- so
    this static guard is the only thing standing in for it.

    `__init__.py` joined the list in review pass 4. It is the one file in the
    package that executes on EVERY import of any submodule, so a django
    import there produces exactly the failure described above -- and it was
    covered by neither guard: the one above skips all of `dashboard/`, and
    this one named only the two submodules. Mutation-proved at the time:
    appending `import django` to `__init__.py` left all seven dashboard guard
    tests green while a django-blocked import of
    `pyforge.steward.dashboard.middleware` failed with `ImportError`. Its own
    docstring asserts it is django-free, which is precisely the class of
    prose-only claim this test exists to replace with a mechanism.

    Story 9.2 added `navigation.py` and `filtering.py` to the list on the
    same rationale: both modules' own docstrings and the story spec's
    Boundaries & Constraints assert they stay framework-free, and
    `tests/unit/test_dashboard_navigation.py` / `test_dashboard_filtering.py`
    rely on that by importing them with no `pytest.importorskip` either.
    """
    dashboard_dir = PKG_ROOT / "steward" / "dashboard"
    offenders: list[str] = []
    for name in (
        "__init__.py",
        "middleware.py",
        "declarations.py",
        "export.py",
        "navigation.py",
        "filtering.py",
    ):
        path = dashboard_dir / name
        assert path.exists(), f"{name} is missing from {dashboard_dir}"
        own_package_parts = path.relative_to(PKG_ROOT.parent).with_suffix("").parts[:-1]
        offenders += _find_banned_dashboard_imports(
            path.read_text(encoding="utf-8"),
            own_package_parts,
            path.name,
            # Inside `dashboard/`, importing a sibling is normal -- only the
            # framework half of the ban applies here. (`middleware.py` really
            # does `from .declarations import TrustedIngress`.)
            ban_dashboard_package=False,
        )
    assert not offenders, (
        f"django/channels import found in a module documented as framework-free "
        f"(AD-8) — these must import cleanly without the [dashboard] extra: "
        f"{offenders}"
    )

    # And the guard is not vacuous: with the framework ban in force, a planted
    # django import in the same position IS reported.
    assert _find_banned_dashboard_imports(
        "from django.http import HttpResponse\n",
        ("pyforge", "steward", "dashboard"),
        "middleware.py",
        ban_dashboard_package=False,
    ), "the framework-only guard must still catch a real django import"


def test_the_dashboard_module_split_is_pinned_not_merely_documented():
    """Review pass 4: `dashboard/__init__.py` names WHICH submodules import
    `django`, and nothing checked that claim in the growing direction.

    That docstring is the package's load-bearing statement of which modules an
    adopter without the `[dashboard]` extra may touch, and Story 9.3 already
    made it false once by adding three django-importing modules while it still
    read "only `apps.py` and `cache.py`". The sibling guard above pins only the
    django-FREE half, so the drift recurs on the next dashboard module: adding
    a `views.py` with `from django.db import models` left the whole suite green
    with the docstring silently wrong (mutation-proved at the time) -- exactly
    what Story 9.2's own `views.py` (a Django view factory backing CAP-3's
    "absent, not hidden" claim) then did for real, adding it to the set below.

    Deliberately an equality assert against a named set rather than a derived
    one -- the point is to FAIL when the set changes, so whoever adds the next
    django-importing module updates the docstring in the same commit.
    """
    import ast

    dashboard_dir = PKG_ROOT / "steward" / "dashboard"
    documented = {
        "admin.py",
        "apps.py",
        "asgi.py",
        "audit.py",
        "cache.py",
        "consumers.py",
        "corridor_load.py",
        "glass_query.py",
        "models.py",
        "passport_mint.py",
        "passport_sync.py",
        "routing.py",
        "views.py",
        "views_htmx.py",
    }

    actual: set[str] = set()
    for path in sorted(dashboard_dir.rglob("*.py")):
        if path.parent.name == "migrations":
            # `migrations/` is documented as a directory, not per-file, since
            # every future migration lands there and importing django is the
            # whole point of the file format.
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module.split(".")[0]]
            if any(name in {"django", "channels"} for name in names):
                actual.add(path.name)
                break

    assert actual == documented, (
        f"the set of dashboard modules importing django/channels changed to "
        f"{sorted(actual)} (documented: {sorted(documented)}) — update "
        f"`dashboard/__init__.py`'s module-split docstring, which tells an "
        f"adopter without the [dashboard] extra which modules they may touch, "
        f"and this pin, in the same commit"
    )
    # And the docstring really does name each one, so the two cannot agree
    # here while disagreeing there.
    init_docstring = ast.get_docstring(ast.parse((dashboard_dir / "__init__.py").read_text(encoding="utf-8")))
    missing = [name for name in sorted(documented) if name not in init_docstring]
    assert not missing, f"`dashboard/__init__.py`'s docstring does not name these django-importing modules: {missing}"


def test_dashboard_import_guard_flags_a_relative_import_past_the_top_package():
    """Review pass 3: `from ...dashboard import cache` inside
    `pyforge/steward/` climbed past the top-level package, and the level
    arithmetic silently truncated it to the bare `"dashboard"` -- which is
    not a banned name, so the import went unflagged. Proven by execution.

    The import itself cannot run (Python raises "attempted relative import
    beyond top-level package"), so the point is not that it is dangerous but
    that a guard must never turn something it cannot resolve into something
    that looks innocent.
    """
    offenders = _find_banned_dashboard_imports(
        "from ...dashboard import cache\n", ("pyforge", "steward"), "synthetic.py"
    )
    assert offenders, "an unresolvable relative import must be reported, not silently truncated"
    assert "unresolvable" in offenders[0]


def test_dashboard_import_guard_catches_symbol_and_relative_import_shapes():
    """Review pass 1 (Blind Hunter + Edge Case Hunter): the first version of
    `_find_banned_dashboard_imports` only inspected `ast.ImportFrom.module`,
    so two real import shapes sailed through undetected. Proven here by
    execution against synthetic source, not by reading the implementation.
    """
    symbol_import = "from pyforge.steward import dashboard\n"
    relative_import = "from . import dashboard\n"
    relative_submodule_import = "from .dashboard import cache\n"
    legitimate_import = "from pyforge.steward import keys\n"

    for source in (symbol_import, relative_import, relative_submodule_import):
        offenders = _find_banned_dashboard_imports(source, ("pyforge", "steward"), "synthetic.py")
        assert offenders, f"expected {source!r} to be flagged as a dashboard import"

    assert not _find_banned_dashboard_imports(legitimate_import, ("pyforge", "steward"), "synthetic.py")


def test_dashboard_import_guard_resolves_relative_imports_from_a_subpackage():
    """Review pass 2: the guard hardcoded `("pyforge","steward")` for every
    file `rglob` reached, so once `steward/` gains any subpackage besides
    `dashboard/`, relative-import resolution was wrong in both directions.

    Proven by execution from a subpackage's point of view. `steward/sub/`
    has no files today, which is exactly why this would have gone unnoticed
    until a later Epic 9 story added one -- and its failure mode is a silent
    false negative, the worst kind for a guard to have.
    """
    from_subpackage = ("pyforge", "steward", "sub")

    # `from ..dashboard import cache` inside `steward/sub/` IS the banned
    # import (`..` -> pyforge.steward). Previously resolved to
    # `pyforge.dashboard` and sailed through.
    assert _find_banned_dashboard_imports("from ..dashboard import cache\n", from_subpackage, "sub/mod.py"), (
        "a genuine relative dashboard import from a subpackage must be flagged"
    )

    # `from . import dashboard` inside `steward/sub/` means
    # `pyforge.steward.sub.dashboard` -- a DIFFERENT module that is not
    # banned. Previously flagged as a false positive.
    assert not _find_banned_dashboard_imports("from . import dashboard\n", from_subpackage, "sub/mod.py"), (
        "a sibling module that merely shares the name must not be flagged"
    )


def test_dashboard_appconfig_is_ad13_compliant():
    """Story 9.1 ships `apps.py` early specifically so Story 9.3's audit model
    inherits a compliant AD-13 scaffold instead of retrofitting one. Nothing
    imported it (review pass 2), so a typo in `name` or `label` -- or the
    module simply not importing -- would have shipped silently and surfaced
    a story later, which defeats the entire reason for shipping it early.

    Skipped rather than failed without the `[dashboard]` extra: `apps.py` is
    the one module in this package that genuinely requires `django`.
    """
    import pytest

    pytest.importorskip("django", reason="apps.py requires pyforge-steward[dashboard]")

    from pyforge.steward.dashboard.apps import DashboardConfig

    assert DashboardConfig.name == "pyforge.steward.dashboard"
    assert DashboardConfig.default_auto_field == "django.db.models.BigAutoField"

    # AD-13's label rule: explicit, and never colliding with a contrib label.
    # Django derives the label from the module basename by default, which for
    # this package would be the very common "dashboard".
    assert DashboardConfig.label == "pyforge_steward_dashboard"
    assert DashboardConfig.label not in {
        "admin",
        "auth",
        "contenttypes",
        "sessions",
        "messages",
        "staticfiles",
        "dashboard",
    }


def test_dashboard_extra_pins_match_pixi_feature_pins():
    """Every `[dashboard]` extra floor is hand-typed TWICE -- once in
    pyproject.toml's `[dashboard]` extra, once in root pixi.toml's
    `[feature.pyforge-steward.dependencies]`. Review pass 1 (Story 9.1,
    django-only at the time) closed "nothing keeps these in sync" with a
    cross-reference comment; review pass 2 found that comment had ALREADY
    drifted (it claimed the same floor as a third, deliberately narrower
    pin). A comment is not a mechanism -- this is. Story 9.5 generalized this
    from a django-only check into a loop over every package the extra now
    pins, rather than four near-duplicate test functions.

    Deliberately scoped to that pair. `[feature.local-recipes.dependencies]`
    separately pins `django`/`channels`/`daphne` narrower/for unrelated
    reasons (wagtail/coderedcms) and is NOT required to match.

    Each distribution name is matched on a name boundary and
    case-insensitively (review pass 3, django-only at the time). A plain
    `startswith(name)` breaks on two edits that are each a matter of when,
    not if: the canonical PyPI spelling (`Django`, as `dependencies =
    ["PyYAML"]` above already uses elsewhere) would match nothing, and a
    same-prefixed companion package (`django-htmx` for `django`,
    `channels_presence` for `channels`) would match a second time -- either
    way failing on spelling rather than on the drift this exists to catch.
    The boundary also keeps `channels` from matching `channels_redis` (and
    vice versa isn't possible: `channels_redis` is the longer, more specific
    name) since `_` is itself an excluded continuation character.
    """
    import re

    try:
        import tomllib
    except ImportError:  # pragma: no cover
        import tomli as tomllib  # type: ignore[no-redef]

    manifest = tomllib.loads((PKG_ROOT.parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    extra = (manifest["project"]["optional-dependencies"])["dashboard"]

    # PKG_ROOT is <repo>/src/shared/packages/pyforge-steward/src/pyforge, so
    # the repo root carrying pixi.toml is five parents up. Skipped rather
    # than crashed when it is not there (review pass 4, django-only at the
    # time): this is the only assertion in this file that reaches OUTSIDE the
    # package -- every other file-reading test stops at `PKG_ROOT.parents[1]`
    # -- so a bare `read_text()` made the package's own suite raise
    # `FileNotFoundError` anywhere the monorepo layout is absent. Ledger entry
    # DW-1-3-14 is an open item about this package behaving correctly "in a
    # package installed outside a checkout", so that is a planned
    # environment, not a hypothetical one; a cross-manifest pin check simply
    # has nothing to compare there.
    import pytest

    repo_root = PKG_ROOT.parents[5]
    pixi_path = repo_root / "pixi.toml"
    if not pixi_path.is_file():
        pytest.skip(f"no monorepo pixi.toml at {pixi_path} — nothing to cross-check the pins against")

    pixi_manifest = tomllib.loads(pixi_path.read_text(encoding="utf-8"))
    pixi_deps = pixi_manifest["feature"]["pyforge-steward"]["dependencies"]

    checked_names = ("django", "channels", "daphne", "asgiref", "channels_redis")
    # Review pass: the per-name loop below asserts a MISSING pin loudly, but
    # said nothing about an EXTRA one -- a 6th dependency added to the extra
    # without a matching addition to `checked_names` drifted out of sync
    # invisibly, defeating this test's own "generalized to every package the
    # extra pins" docstring claim.
    assert len(extra) == len(checked_names), (
        f"[dashboard] extra has {len(extra)} pin(s) {extra!r} but this test "
        f"only checks {checked_names!r} -- a pin was added or removed "
        f"without updating this test"
    )
    for pkg_name in checked_names:
        # `pkg_name` as a whole distribution name: followed by a version
        # specifier, an extras/marker delimiter, or nothing -- never by
        # another name char, so e.g. `django-htmx` never matches `django`.
        name_re = re.compile(rf"^{re.escape(pkg_name)}(?![0-9A-Za-z._-])", re.IGNORECASE)
        extra_pins = [spec for spec in extra if name_re.match(spec.replace(" ", ""))]
        assert len(extra_pins) == 1, f"expected exactly one {pkg_name} pin in the [dashboard] extra, got {extra_pins!r}"
        extra_pin = extra_pins[0].replace(" ", "")

        # Guard the lookup itself (review pass): a package present in the
        # extra but missing entirely from pixi.toml's feature deps is
        # exactly the drift this test exists to catch -- a raw `KeyError`
        # reports that as an opaque traceback instead of a clear assertion.
        assert pkg_name in pixi_deps, (
            f"{pkg_name} is pinned in pyproject.toml's [dashboard] extra but "
            f"missing entirely from pixi.toml's "
            f"[feature.pyforge-steward.dependencies]"
        )
        feature_pin = pixi_deps[pkg_name]

        # Distribution names are case-insensitive (PEP 503); the SPECIFIER is
        # what must match byte-for-byte, so only the name's case is
        # normalized away.
        assert extra_pin.lower() == f"{pkg_name}{feature_pin}".replace(" ", "").lower(), (
            f"{pkg_name} pin drift: pyproject `[dashboard]` extra says {extra_pin!r}, "
            f"pixi.toml `[feature.pyforge-steward.dependencies]` says {feature_pin!r}"
        )


def test_guildhall_generator_stays_deleted():
    """Steward 30.2 / FR-7: generator, data.js, four pixi tasks, cron are gone."""
    repo = Path(__file__).resolve()
    while repo != repo.parent:
        if (repo / "pixi.toml").is_file() and (repo / "docs" / "dashboard").is_dir():
            break
        repo = repo.parent
    else:
        raise AssertionError("could not locate repo root")
    dashboard = repo / "docs" / "dashboard"
    assert not (dashboard / "generate.py").is_file()
    assert not (dashboard / "data.js").is_file()
    assert (dashboard / "kedro-viz").is_dir()
    pixi = (repo / "pixi.toml").read_text(encoding="utf-8")
    for task in (
        "dashboard-gen",
        "dashboard-watch",
        "dashboard-check",
        "dashboard-drift-check",
    ):
        assert f"[feature.local-recipes.tasks.{task}]" not in pixi
    assert (repo / ".github" / "workflows" / "kedro-viz-publish.yml").is_file()
    dash_wf = (repo / ".github" / "workflows" / "dashboard.yml").read_text(encoding="utf-8")
    assert "schedule:" not in dash_wf
    assert "generate.py" not in dash_wf
