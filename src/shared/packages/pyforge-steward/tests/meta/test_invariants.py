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
    except ImportError:                       # pragma: no cover
        import tomli as tomllib               # type: ignore[no-redef]

    manifest = tomllib.loads(
        (PKG_ROOT.parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    project = manifest.get("project", {})
    declared = list(project.get("dependencies", []))
    for extras in (project.get("optional-dependencies") or {}).values():
        declared += list(extras)

    banned = {"click", "typer"}
    found = [d for d in declared
             if d.split("[")[0].split(">")[0].split("=")[0].strip().lower() in banned]
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
            if isinstance(fn, ast.Attribute) and fn.attr == "exit" and \
               isinstance(fn.value, ast.Name) and fn.value.id == "sys":
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
        "requests", "httpx", "urllib3", "github", "pygithub", "gitlab",
        "python-gitlab", "anthropic", "boto3", "google", "artifactory",
        "dohq_artifactory", "pyjfrog",
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
    wrapped `dashboard-gen` subprocess (`docs/dashboard/generate.py`'s own
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
        "done", "in-progress", "backlog", "blocked", "pending", "active", "gated",
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
                if isinstance(operand, ast.Constant) and isinstance(operand.value, str) \
                        and operand.value in status_vocabulary:
                    offenders.append(
                        f"deploy.py:{node.lineno} compares against status literal "
                        f"{operand.value!r}"
                    )

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
        "kubecost", "opencost", "infracost", "boto3", "google", "azure",
        "stripe", "awscostexplorer", "cloudability", "cloudhealth",
        "cloudcheckr", "vantage", "kubecostgrpc", "kubecost_client",
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


def _is_banned_dashboard_dotted(name: str) -> bool:
    return name == _DASHBOARD_BANNED_DOTTED_PREFIX or name.startswith(
        _DASHBOARD_BANNED_DOTTED_PREFIX + "."
    )


def _find_banned_dashboard_imports(source: str, own_package_parts: tuple[str, ...], label: str) -> list[str]:
    """Return one string per offending import statement in `source`.

    `own_package_parts` is the dotted package the source file itself lives
    in (e.g. `("pyforge", "steward")`), used to resolve relative imports
    (`node.level`) to an absolute dotted path.
    """
    import ast

    def _resolved_module(node: ast.ImportFrom) -> str | None:
        if node.level == 0:
            return node.module
        parts = list(own_package_parts[: len(own_package_parts) - (node.level - 1)]) if node.level > 1 \
            else list(own_package_parts)
        if node.module:
            parts += node.module.split(".")
        return ".".join(parts) if parts else None

    offenders: list[str] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in _DASHBOARD_BANNED_MODULES or _is_banned_dashboard_dotted(alias.name):
                    offenders.append(f"{label}:{node.lineno} imports {alias.name!r}")
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolved_module(node)
            if resolved:
                top = resolved.split(".")[0]
                if top in _DASHBOARD_BANNED_MODULES or _is_banned_dashboard_dotted(resolved):
                    offenders.append(f"{label}:{node.lineno} imports from {resolved!r}")
                    continue
            # The banned target may be named as an imported SYMBOL rather
            # than as part of the module path, e.g.
            # `from pyforge.steward import dashboard`.
            for alias in node.names:
                full = f"{resolved}.{alias.name}" if resolved else alias.name
                top = full.split(".")[0]
                if top in _DASHBOARD_BANNED_MODULES or _is_banned_dashboard_dotted(full):
                    offenders.append(f"{label}:{node.lineno} imports {full!r}")
    return offenders


def test_no_module_outside_dashboard_imports_dashboard_django_or_channels():
    """Story 9.1: `pyforge.steward.dashboard` ships ONLY behind the
    `pyforge-steward[dashboard]` optional extra, never a base dependency.
    A base-package module importing `pyforge.steward.dashboard`, `django`,
    or `channels` at module level would silently make the extra mandatory
    for every existing duty, breaking an install that never opted into
    `[dashboard]`.

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
        offenders += _find_banned_dashboard_imports(
            path.read_text(encoding="utf-8"), ("pyforge", "steward"), path.name
        )
    assert not offenders, f"dashboard/django/channels import found outside dashboard/: {offenders}"


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
