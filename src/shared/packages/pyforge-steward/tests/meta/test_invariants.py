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
