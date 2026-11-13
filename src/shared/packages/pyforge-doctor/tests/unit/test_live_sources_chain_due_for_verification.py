"""Doctor Story 58.1 (spec-pyforge-doctor:CAP-97) -- the live-tree half of
``test_sources_chain_due_for_verification.py``.

These two tests reach this repository: the cross-project close loads the real
``scripts/apply_verification_verdicts.py``, and the ``_PATH_EXTENSIONS`` sweep
reads the tracked deferred-work ledgers and ``git ls-files``. They run in the
station's live-tree half; every other test of the sweep builds its own tree
and stays in ``test_sources_chain_due_for_verification.py`` (the package half).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from test_sources_chain_due_for_verification import (  # noqa: F401 -- _isolate_git_env is the module's autouse scrub
    _isolate_git_env,
    _write_code_root_file,
    _write_tracked,
)

from pyforge.doctor.sources import chain

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


# --- (c) integration: a cross-project close via apply_verification_verdicts.py --


def _load_apply_verdicts_module():
    """Dynamically loads the real ``scripts/apply_verification_verdicts.py``
    as a fresh module object, via ``importlib.util.spec_from_file_location``
    -- never ``sys.path`` manipulation, and never a subprocess (unlike
    ``tests/scripts/test_apply_verification_verdicts.py``'s own precedent,
    which needs a subprocess specifically to patch the script's hard-coded
    ``REPO_ROOT`` line before it runs as ``__main__``): this test calls
    ``_apply_project`` directly, so patching the loaded module OBJECT's own
    ``REPO_ROOT`` attribute after import is enough, and a fresh module object
    per call means that patch can never leak into a sibling test. Registered
    in `sys.modules` only for the DURATION of `exec_module` below, then
    popped back out (review finding, patch): the caller keeps its own
    reference to the returned `module` object regardless, so nothing needs
    the registry entry to persist afterward, and leaving a fixed key
    resident in `sys.modules` for the rest of the test session would risk a
    stale entry (e.g. a since-deleted `tmp_path` still referenced by its
    `REPO_ROOT`) colliding with any future test that loads under the same
    name."""
    script_path = Path(__file__).resolve().parents[6] / "scripts" / "apply_verification_verdicts.py"
    spec = importlib.util.spec_from_file_location(
        "apply_verification_verdicts_under_test",
        script_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered in `sys.modules` BEFORE `exec_module` -- the script's own
    # `from __future__ import annotations` makes every annotation a string,
    # and `@dataclass` (`_Outcome`) resolves a string annotation by looking
    # up `cls.__module__` in `sys.modules`; skipping this step raises
    # `AttributeError: 'NoneType' object has no attribute '__dict__'` at
    # import time, verified empirically.
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        del sys.modules[spec.name]
    return module


def test_cross_project_evidence_closes_the_entry_via_apply_verification_verdicts(
    tmp_path: Path,
) -> None:
    """Reproduces the real ``atlas DW-I5-1`` shape end to end (Intent): a due
    entry lives in project ``alpha``, the real fix is committed under project
    ``beta``'s own code root, ``alpha``'s Finding evidence names ``beta``'s
    code root under ``other_project_roots`` (the discoverability half this
    story adds), and a verifying agent citing ``beta``'s ``file:line`` as
    evidence is accepted UNMODIFIED by ``apply_verification_verdicts.py``'s
    own ``_apply_project`` -- proving CAP-5's own claim that "nothing
    structurally blocks a cross-project close" (Intent)."""
    _write_tracked(tmp_path, "alpha", "## DW-1\nstatus: open\n")
    _write_code_root_file(
        tmp_path,
        "beta",
        "src/pyforge/beta/core/policy.py",
        "def fixed(): ...\n",
    )

    findings = chain._due_for_verification_findings(tmp_path, today=date(2026, 8, 15))
    assert len(findings) == 1
    beta_root = findings[0]["other_project_roots"]["beta"]
    assert beta_root == "src/shared/packages/beta"

    verdicts_module = _load_apply_verdicts_module()
    verdicts_module.REPO_ROOT = tmp_path

    outcome = verdicts_module._apply_project(
        "alpha",
        [
            {
                "id": "DW-1",
                "verdict": "resolved",
                "evidence": f"Fixed in {beta_root}/src/pyforge/beta/core/policy.py:1",
            }
        ],
        date(2026, 8, 21),
        # DW-doctor-38-1: the writer now applies Story 38.1's own citation
        # predicate, passed in. This evidence cites a real `path:line`, so it
        # satisfies it -- the point of the test is unchanged.
        chain.verified_line_cites,
    )

    assert outcome.status == "applied"
    tracked_text = (tmp_path / "_bmad-output" / "projects" / "alpha" / verdicts_module.TRACKED_REL).read_text(
        encoding="utf-8"
    )
    assert "verified: 2026-08-21 — resolved — Fixed in src/shared/packages/beta" in tracked_text


def test_path_extensions_cover_every_cited_tracked_file() -> None:
    """`_PATH_EXTENSIONS` is derived from measurement, so it must not silently
    fall behind the ledgers it was derived from.

    Sweeps the live tracked ledgers for dotted-only citations whose trailing
    segment names a real tracked file, and asserts the set admits it. A new
    file type cited in a future entry fails HERE rather than silently
    dropping out of the churn check.
    """
    root = Path(__file__).resolve().parents[6]
    ledgers = sorted(root.glob("_bmad-output/projects/*/planning-artifacts/deferred-work-ledger.md"))
    assert ledgers, "tracked ledgers unavailable (packaged install)"
    # `git ls-files`, not `rglob` -- the working tree carries `.pixi`
    # environments that dwarf the repo, and "tracked" is the set this
    # assertion actually means.
    listing = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert listing.returncode == 0, "git unavailable"
    tracked_basenames = {line.rsplit("/", 1)[-1] for line in listing.stdout.split()}
    missing: dict[str, str] = {}
    for ledger in ledgers:
        text = ledger.read_text(encoding="utf-8", errors="replace")
        for m in chain._PATH_TOKEN_RE.finditer(text):
            token = m.group(1)
            if "/" in token or "." not in token:
                continue
            ext = token.rsplit(".", 1)[-1].lower()
            if ext in chain._PATH_EXTENSIONS:
                continue
            if token in tracked_basenames:
                missing[ext] = token
    assert not missing, (
        "cited real files whose extension _PATH_EXTENSIONS omits: "
        f"{missing} — add the extension (and say why in its comment)"
    )
