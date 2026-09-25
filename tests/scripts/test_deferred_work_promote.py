"""Coverage for ``scripts/deferred_work_promote.py``, the mutation-only
promoter that lifts Tier-3 legacy deferred-work orphans (Story 8.1's
``classify_tier3_entries`` / Story 8.2's ``mint_id_for_entry``) into a
project's tracked ledger (Story 8.3).

Mirrors ``test_deferred_work_baseline.py``'s own pattern exactly: a
``_patched_promoter`` fixture copies the real script into a ``tmp_path``,
string-replaces its ``REPO_ROOT = Path(__file__).resolve().parent.parent``
line with the tmp path (and ASSERTS the substitution actually fired), runs
it via ``subprocess.run([sys.executable, str(promoter), ...])``, and for
error/collision paths asserts non-zero exit AND that the target output
file either doesn't exist or is byte-identical to a pre-run snapshot.

One divergence from the baseline test's fixture-naming freedom:
``mint_id_for_entry``'s own ``_normalize_station`` rejects any project slug
outside the fleet's real 8 known stations, so fixture project directories
here are named after REAL stations (``pyforge-mason``, ``pyforge-doctor``,
``pyforge-herald``) rather than arbitrary ``proj-alpha``/``proj-beta``
names -- the fixture *content* (Tier-3 orphan bodies) is still synthetic
or a real excerpt as each test calls for.

The clean-batch fixtures below use REAL orphan text copied verbatim from
``pyforge-mason``'s live Tier-3 backlog (``_bmad-output/projects/
pyforge-mason/implementation-artifacts/deferred-work.md`` lines ~19-29,
2026-08-15), confirmed via direct ``classify_tier3_entries`` inspection to
carry no summary collision against that project's own tracked ledger.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMOTER = REPO_ROOT / "scripts" / "deferred_work_promote.py"
BASELINE_SCRIPT = REPO_ROOT / "scripts" / "deferred_work_baseline.py"

sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "packages" / "pyforge-doctor" / "src"))
sys.path.insert(0, str(REPO_ROOT / "src" / "shared" / "packages" / "pyforge-core" / "src"))
from pyforge.doctor.sources.chain import Tier3Shape, classify_tier3_entries  # noqa: E402

TIER3_REL = Path("implementation-artifacts") / "deferred-work.md"
TRACKED_REL = Path("planning-artifacts") / "deferred-work-ledger.md"

# --- Real orphan excerpts (verbatim, pyforge-mason's live Tier-3 backlog) ---

_REAL_ORPHAN_A = """- source_spec: `_bmad-output/implementation-artifacts/spec-1-8-mason-doctor.md`
  summary: `render_text`'s shallow one-line-per-key rendering (Story 1.4) renders `mason doctor`'s default text-mode `engines` field as a raw Python tuple-of-dicts `repr()` on one unbroken line -- close to unreadable for a self-diagnosis tool whose main audience is a human troubleshooting their own setup.
  evidence: Confirmed live -- `mason doctor` (no `--format` flag) prints `engines: ({'name': 'pixi', 'available': True, ...}, {...}, ...)`. `render_text` is explicitly "NON-CONTRACT, free-format output" per its own module docstring and has never handled nested data specially; `doctor` is simply the first caller to hand it richly-nested data (every prior caller's `data` was flat). A real fix belongs to `render.py` generically (recursive/indented rendering for nested dicts/tuples), benefiting every future command with structured data, not a `doctor`-specific formatting special-case.
"""

_REAL_ORPHAN_B = """- source_spec: `_bmad-output/implementation-artifacts/spec-1-8-mason-doctor.md`
  summary: `mason doctor` has no overall time budget -- `engines.probe_known_engines()` probes four engines sequentially (up to 10s each) on top of `cfe.probe_import_floor`'s independent 15s subprocess timeout, so a single hung/slow engine binary or interpreter can make a "quick health check" command take up to roughly a minute with no progress output.
  evidence: Confirmed by direct inspection -- `probe_known_engines()` iterates `_KNOWN_ENGINES` with a plain generator expression (no concurrency), and `doctor.build_report` calls it after the (also serial) import-floor probe. No AC or boundary in this story's spec calls for parallelism or a shared timeout budget; a proper fix (e.g. `concurrent.futures`-based fan-out with one overall deadline) is a deliberate design change worth its own story, not a one-off patch here.
"""

_REAL_ORPHAN_C = """- source_spec: `_bmad-output/implementation-artifacts/spec-1-8-mason-doctor.md`
  summary: `resolve_cfe_root`'s explicit-flag and environment-variable steps (Story 1.5) trust the given path without checking the CFE marker directory exists there -- an explicit `--cfe-root`/`MASON_CFE_ROOT` pointing at a bogus path is reported by `mason doctor` as "resolved," with `"recipe"` NOT listed as unavailable, even though CFE isn't actually there.
  evidence: Confirmed intentional and pre-existing -- `resolve.py`'s own module docstring states steps 1 and 2 match on presence alone and are NOT validated against the marker directory; only step 3 (the walk) checks for it. `doctor.py` faithfully reports whatever `resolve_cfe_root` returns, so the gap is inherited, not introduced.
"""

_MASON_EXISTING_TRACKED = """---
doc_type: deferred-work-ledger
project: pyforge-mason
date: 2026-08-01
status: promoted-verbatim
---

# pyforge-mason -- deferred-work ledger (TRACKED, fixture)

### DW-1-1-1: An unrelated pre-existing tracked entry

- source_spec: `spec-1-1-workspace-member-scaffold-and-dual-artifact-build.md`
  summary: An unrelated pre-existing tracked entry, used only to prove appends land after existing content.
  evidence: fixture-only content.
  status: open
"""

# --- Manufactured duplicate-summary orphans (same summary, different source_spec) ---

_DUP_SUMMARY_A = """- source_spec: `spec-fixture-one.md`
  summary: Duplicate summary text used to test the collision guard.
  evidence: first entry's own evidence text.
"""

_DUP_SUMMARY_B = """- source_spec: `spec-fixture-two.md`
  summary: Duplicate summary text used to test the collision guard.
  evidence: second entry's own evidence text, different from the first.
"""

# A whitespace/casing-only variant of `_DUP_SUMMARY_A`'s own summary --
# byte-different, but the SAME finding once normalized (casefold + collapse
# internal whitespace). Used to prove the collision guard now catches this
# real-world variant (Review Triage Log 2026-08-15, item 8).
_DUP_SUMMARY_WHITESPACE_VARIANT = """- source_spec: `spec-fixture-whitespace-variant.md`
  summary:   DUPLICATE   summary text used TO test the collision guard.
  evidence: third entry's own evidence text, also different from the first two.
"""

# A second orphan whose `source_spec` is blank -- `mint_id_for_entry` raises
# `ValueError` for this (no story key to derive), the one declared failure
# mode in the I/O matrix with no dedicated test before this pass (Review
# Triage Log 2026-08-15, item 6).
_BLANK_SOURCE_SPEC_ORPHAN = """- source_spec:
  summary: An orphan with a blank source_spec that cannot be minted.
  evidence: fixture-only content, exercising the mint-time ValueError abort path.
"""

# An orphan with a blank `summary:` field -- must always be treated as
# invalid and block promotion outright, never silently exempted from the
# duplicate-summary guard (Review Triage Log 2026-08-15, item 7).
_BLANK_SUMMARY_ORPHAN = """- source_spec: `spec-fixture-blank-summary.md`
  summary:
  evidence: fixture-only content, exercising the blank-summary guard.
"""

# --- Real orphans carrying a field beyond {source_spec, summary, evidence} ---
#
# Promotion used to silently DROP any such field and unconditionally
# force-overwrite `status: open` (Review Triage Log 2026-08-15, item 3),
# live-confirmed against real data: 13 of 76 real orphans carry a
# `resolution:` field.

# Verbatim excerpt, pyforge-doctor's own live Tier-3 backlog
# (`_bmad-output/projects/pyforge-doctor/implementation-artifacts/
# deferred-work.md`, lines 107-110, 2026-08-15) -- carries a `resolution:`
# field the orphan does not otherwise have a `status:` field of its own.
_REAL_ORPHAN_WITH_RESOLUTION = """- source_spec: `_bmad-output/implementation-artifacts/spec-6-4-the-ledger-verdicts-come-home.md`
  summary: The port silently drops the source script's defining "never green on can't-evaluate" guarantee. `scripts/ledger_regression_check.py` returns exit 2 for both cannot-evaluate branches (unresolvable base; base==head with no parent); `sources/ledger.py` maps both to a WARN `Finding`, and `verdict.exit_code_for` documents that "a `warn` finding never changes this" -- so both branches now project to exit 0.
  evidence: `verdict.py:32-44` -- `exit_code_for` returns `_EXIT_FAIL` only on a FAIL finding, `_EXIT_OK` otherwise. `scripts/ledger_regression_check.py:172` -- `return 2  # never green on can't-evaluate`.
  resolution: Decided consciously by Story 6.9 (2026-08-09), not inherited silently -- the two cannot-evaluate branches keep Story 6.4's own spec-sanctioned WARN mapping as-is. Recorded here as the accepted-risk note this entry asked for.
"""

# Close-verbatim excerpt (evidence trimmed for fixture size), pyforge-marshal's
# own live Tier-3 backlog (`_bmad-output/projects/pyforge-marshal/
# implementation-artifacts/deferred-work.md`, lines 457-460, 2026-08-15) --
# carries a NON-`open` `status:` value that must survive promotion verbatim,
# not be force-overwritten with `status: open`.
_REAL_ORPHAN_WITH_NON_OPEN_STATUS = """- source_spec: `_bmad-output/implementation-artifacts/spec-3-4-supervisor-process-lifecycle.md`
  summary: AD-34's structural egress guard cannot reach the one new secret-bearing surface this story adds -- `SessionObserverPort.pane_content` is the only port method in the package that RETURNS raw agent-terminal text, but the `EGRESS_PORTS` registry's boolean vocabulary models only "accepts a payload bound for a sink", so the port is classified `egress: False`.
  evidence: Read live: `core/egress.py`'s `EGRESS_PORTS` maps `"SessionObserverPort": False` with a documented rationale that is correct by AD-34's letter.
  status: **LIVE as of Story 3.5** (idle-strand detection) -- no longer latent. `core/supervise.py::evaluate_idle`'s own `Sample.pane_content` field is now a REAL consumer of `pane_content`'s return value.
"""


def _write_tier3(project_dir: Path, body: str) -> None:
    d = project_dir / TIER3_REL
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_text("# Deferred Work\n\n" + body, encoding="utf-8")


def _write_tracked(project_dir: Path, body: str) -> None:
    d = project_dir / TRACKED_REL
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_text(body, encoding="utf-8")


def _fixture_repo(tmp_path: Path) -> Path:
    """A miniature ``_bmad-output/projects/`` tree: ``pyforge-mason`` (two
    real, non-colliding orphans + a pre-existing tracked ledger with one
    unrelated entry -- exercises the APPEND path) and ``pyforge-doctor``
    (one real, non-colliding orphan, no pre-existing tracked ledger --
    exercises the fresh-file WRITE path)."""
    projects = tmp_path / "_bmad-output" / "projects"
    mason = projects / "pyforge-mason"
    _write_tier3(mason, _REAL_ORPHAN_A + "\n" + _REAL_ORPHAN_B)
    _write_tracked(mason, _MASON_EXISTING_TRACKED)

    doctor = projects / "pyforge-doctor"
    _write_tier3(doctor, _REAL_ORPHAN_C)

    (tmp_path / "scripts").mkdir()
    return tmp_path


def _patched_baseline_module(repo: Path) -> Path:
    """A copy of ``deferred_work_baseline.py`` staged into the fixture
    repo's own ``scripts/`` dir, ``REPO_ROOT``-patched the same way
    ``_patched_promoter`` patches the promoter itself (Story 8.4).

    The promoter's own ``import deferred_work_baseline`` (module-level,
    resolved via ``sys.path.insert(0, str(REPO_ROOT / "scripts"))``) needs
    a same-named sibling file to actually import from a subprocess launched
    with ``cwd=repo`` and a patched ``REPO_ROOT`` -- and, just as
    importantly, that sibling's OWN ``REPO_ROOT`` must also point at the
    fixture repo, or its ``stamp_projects``/``_live_state()`` would read and
    write the REAL committed ``scripts/.deferred-work-baseline.json``
    instead of the fixture's. Kept as a same-named file (not renamed, unlike
    ``test_deferred_work_baseline.py``'s own ``stamper.py``) because the
    promoter's import statement names it literally."""
    src = BASELINE_SCRIPT.read_text(encoding="utf-8")
    marker = "REPO_ROOT = Path(__file__).resolve().parent.parent"
    assert marker in src, (
        "REPO_ROOT line not found in scripts/deferred_work_baseline.py -- "
        "update this test's substitution target, or every test below that "
        "reaches a successful promotion would silently re-stamp the real "
        "repo's baseline instead of the fixture's"
    )
    src = src.replace(marker, f"REPO_ROOT = Path({str(repo)!r})")
    dst = repo / "scripts" / "deferred_work_baseline.py"
    dst.write_text(src, encoding="utf-8")
    return dst


def _patched_promoter(repo: Path) -> Path:
    """A copy of the promoter script rooted at the fixture repo, not this
    one.

    ``str.replace`` returns its input UNCHANGED, with no error, when the
    target substring is not found -- if a future edit reformats the
    ``REPO_ROOT`` line even slightly, the "patched" copy would silently
    keep pointing at the REAL repo, and every test below would then run
    against (and mutate) the actual committed ``_bmad-output/projects/``
    tree instead of the tmp_path fixture. Assert the substitution actually
    fired.

    Also stages a fixture-patched ``deferred_work_baseline.py`` alongside
    it (Story 8.4's ``_patched_baseline_module``) -- the promoter now
    imports that module unconditionally at load time, so every test below
    needs it present, not just the ones that reach a successful promotion."""
    src = PROMOTER.read_text(encoding="utf-8")
    marker = "REPO_ROOT = Path(__file__).resolve().parent.parent"
    assert marker in src, (
        "REPO_ROOT line not found in scripts/deferred_work_promote.py -- "
        "update this test's substitution target, or every test below would "
        "silently run against the real repo instead of a fixture"
    )
    src = src.replace(marker, f"REPO_ROOT = Path({str(repo)!r})")
    dst = repo / "scripts" / "promoter.py"
    dst.write_text(src, encoding="utf-8")
    _patched_baseline_module(repo)
    return dst


def _subprocess_env() -> dict[str, str]:
    """The patched promoter's `REPO_ROOT` is the FIXTURE repo, so its own
    best-effort `sys.path` insertion (`<REPO_ROOT>/src/shared/packages/
    pyforge-{doctor,core}/src`) finds nothing there. Point the child at the
    real source trees instead -- the `pyforge-ci` env that runs this suite
    in CI installs neither package (pure-stdlib by design), and the
    `local-recipes` env only passes because it has them in site-packages."""
    env = dict(os.environ)
    srcs = [str(REPO_ROOT / "src" / "shared" / "packages" / pkg / "src") for pkg in ("pyforge-doctor", "pyforge-core")]
    env["PYTHONPATH"] = os.pathsep.join(srcs + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    return env


def _run(promoter: Path, repo: Path, *extra_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(promoter), "--fix", *extra_args],
        env=_subprocess_env(),
        capture_output=True, text=True, cwd=repo,
    )


def _tracked_text(repo: Path, slug: str) -> str | None:
    p = repo / "_bmad-output" / "projects" / slug / TRACKED_REL
    return p.read_text(encoding="utf-8") if p.is_file() else None


def _tier3_text(repo: Path, slug: str) -> str:
    return (repo / "_bmad-output" / "projects" / slug / TIER3_REL).read_text(encoding="utf-8")


def _baseline_path(repo: Path) -> Path:
    return repo / "scripts" / ".deferred-work-baseline.json"


def _baseline(repo: Path) -> dict | None:
    """The stamped baseline JSON, or ``None`` if it doesn't exist yet --
    mirrors ``test_deferred_work_baseline.py``'s own ``_baseline`` helper."""
    p = _baseline_path(repo)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


# --- I/O matrix row: clean batch -- N orphans, no collisions, one write ---


def test_clean_batch_promotes_real_orphans_and_writes_once(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    promoter = _patched_promoter(repo)
    tier3_before = _tier3_text(repo, "pyforge-mason")

    r = _run(promoter, repo, "--project", "mason")
    assert r.returncode == 0, r.stderr
    assert "promoted 2 orphan(s)" in r.stdout

    # Tier-3 is append-only by convention -- never touched by this script.
    assert _tier3_text(repo, "pyforge-mason") == tier3_before

    tracked = _tracked_text(repo, "pyforge-mason")
    assert tracked is not None
    assert "### DW-1-1-1:" in tracked  # pre-existing entry preserved verbatim
    assert tracked.startswith(_MASON_EXISTING_TRACKED)  # appended AFTER, not before/instead

    entries = classify_tier3_entries(repo / "_bmad-output" / "projects" / "pyforge-mason" / TRACKED_REL)
    promoted = [e for e in entries if e.id and e.id != "DW-1-1-1"]
    assert len(promoted) == 2
    ids = {e.id for e in promoted}
    # vocabulary Dream Ruling 14: mason mints under its own station token
    # like every other station now (no more forced-suffix special case) --
    # bare first, then suffixed. Both orphans share story key 1-8 (same
    # source_spec), so this also proves already_minted threading: the
    # second orphan must NOT collide with the first.
    assert ids == {"DW-mason-1-8", "DW-mason-1-8-2"}
    for e in promoted:
        assert e.shape is Tier3Shape.IDENTIFIED_BULLETED
        assert e.fields["status"] == "open"
        assert "promoted from Tier-3" in e.fields["promoted"]
        assert "legacy legacy-flat entry, no prior id" in e.fields["promoted"]
        assert e.fields["summary"]  # non-empty, carried through verbatim
        assert e.fields["evidence"]


def test_clean_batch_against_a_fresh_project_with_no_pre_existing_tracked_ledger(tmp_path: Path):
    """The doctor fixture has NO planning-artifacts/deferred-work-ledger.md
    at all before the run -- exercises the fresh-file write path."""
    repo = _fixture_repo(tmp_path)
    promoter = _patched_promoter(repo)
    assert _tracked_text(repo, "pyforge-doctor") is None

    r = _run(promoter, repo, "--project", "doctor")
    assert r.returncode == 0, r.stderr
    assert "promoted 1 orphan(s)" in r.stdout

    tracked = _tracked_text(repo, "pyforge-doctor")
    assert tracked is not None
    entries = classify_tier3_entries(repo / "_bmad-output" / "projects" / "pyforge-doctor" / TRACKED_REL)
    assert len(entries) == 1
    assert entries[0].id == "DW-doctor-1-8"  # vocabulary Dream Ruling 14: real station token, bare


# --- I/O matrix row: an already-identified entry with no tracked twin -- Story 8.7 promotes it ---


def test_project_with_only_a_new_identified_entry_promotes_it_verbatim(tmp_path: Path):
    """Story 8.7: an entry that already carries a real `DW-*` id in Tier-3
    but has no tracked twin is no longer treated as a no-op (pre-8.7
    behavior, when this exact fixture was `test_project_with_only_
    identified_entries_is_a_noop`) -- it promotes, using its own id
    verbatim, no minting involved."""
    repo = _fixture_repo(tmp_path)
    herald = repo / "_bmad-output" / "projects" / "pyforge-herald"
    _write_tier3(
        herald,
        "### DW-9-1: already identified, never copied to the tracked ledger\n\n"
        "- source_spec: `spec-9-1-fixture.md`\n"
        "  summary: already has an id.\n"
        "  evidence: fixture.\n"
        "  status: open\n",
    )
    promoter = _patched_promoter(repo)

    r = _run(promoter, repo, "--project", "herald")
    assert r.returncode == 0, r.stderr
    assert "promoted 1 already-identified entry -- DW-9-1" in r.stdout

    tracked = _tracked_text(repo, "pyforge-herald")
    assert tracked is not None
    entries = classify_tier3_entries(
        repo / "_bmad-output" / "projects" / "pyforge-herald" / TRACKED_REL
    )
    assert len(entries) == 1
    assert entries[0].id == "DW-9-1"  # verbatim, never re-minted
    assert entries[0].fields["status"] == "open"
    assert "never previously copied to the tracked ledger" in entries[0].fields["promoted"]


def test_project_with_only_an_already_tracked_identified_entry_is_a_true_noop(tmp_path: Path):
    """The genuinely-nothing-to-promote case Story 8.7 carves out of the old
    "no orphans to promote" no-op: an identified entry whose id is ALREADY a
    `DW-` token in the tracked ledger. 0 orphans, 0 untracked identified
    entries -- a true no-op, tracked ledger byte-identical."""
    repo = _fixture_repo(tmp_path)
    herald = repo / "_bmad-output" / "projects" / "pyforge-herald"
    body = (
        "### DW-9-1: already identified AND already tracked\n\n"
        "- source_spec: `spec-9-1-fixture.md`\n"
        "  summary: already has an id and a tracked twin.\n"
        "  evidence: fixture.\n"
        "  status: open\n"
    )
    _write_tier3(herald, body)
    _write_tracked(herald, body)
    promoter = _patched_promoter(repo)
    tracked_before = _tracked_text(repo, "pyforge-herald")

    r = _run(promoter, repo, "--project", "herald")
    assert r.returncode == 0, r.stderr
    assert "nothing to promote" in r.stdout
    assert _tracked_text(repo, "pyforge-herald") == tracked_before


# --- I/O matrix row: a mixed batch -- orphans AND already-identified-but-untracked entries together (Story 8.7) ---


_REAL_IDENTIFIED_UNTRACKED = """### DW-FU-9-9: a real already-identified entry with no tracked twin (fixture)

- source_spec: `spec-fixture-identified.md`
  summary: An already-identified Tier-3 entry that was never copied to the tracked ledger.
  evidence: fixture-only content, exercising Story 8.7's promotion path for identified entries.
  status: open
"""


def test_mixed_batch_promotes_orphans_and_identified_entries_together(tmp_path: Path):
    """Story 8.7's own core claim: a batch mixing a genuine orphan with an
    already-identified-but-untracked entry promotes BOTH in the SAME write
    -- the orphan minted, the identified entry copied verbatim under its
    own id -- one combined message, one combined append."""
    repo = _fixture_repo(tmp_path)
    doctor = repo / "_bmad-output" / "projects" / "pyforge-doctor"
    _write_tier3(doctor, _REAL_ORPHAN_C + "\n" + _REAL_IDENTIFIED_UNTRACKED)
    promoter = _patched_promoter(repo)

    r = _run(promoter, repo, "--project", "doctor")
    assert r.returncode == 0, r.stderr
    assert "promoted 1 orphan(s) + 1 already-identified entry -- " in r.stdout

    entries = classify_tier3_entries(
        repo / "_bmad-output" / "projects" / "pyforge-doctor" / TRACKED_REL
    )
    assert len(entries) == 2
    ids = {e.id for e in entries}
    assert "DW-doctor-1-8" in ids  # the minted orphan, same id `_REAL_ORPHAN_C` mints elsewhere
    assert "DW-FU-9-9" in ids  # the identified entry, verbatim, never re-minted


def test_identified_entry_already_matching_a_tracked_summary_is_skipped_not_aborted(
    tmp_path: Path,
):
    """The Story 8.7 analogue of DW-FU-8-4's own `already_tracked` routing:
    an already-identified-but-untracked entry whose SUMMARY already exists
    in the tracked ledger under a DIFFERENT id is silently excluded from
    the write, not aborted -- mirrors `test_orphan_already_matching_a_
    tracked_entry_is_skipped_not_aborted` above, but for an entry that
    already carries its own real id rather than an orphan."""
    repo = _fixture_repo(tmp_path)
    herald = repo / "_bmad-output" / "projects" / "pyforge-herald"
    existing = (
        "### DW-1-1-1: An unrelated pre-existing tracked entry\n\n"
        "- source_spec: `spec-fixture.md`\n"
        "  summary: Duplicate summary text used to test the collision guard.\n"
        "  evidence: fixture-only content.\n"
        "  status: open\n"
    )
    _write_tracked(herald, existing)
    _write_tier3(
        herald,
        "### DW-9-1: identified, content already tracked under a different id\n\n"
        "- source_spec: `spec-9-1-fixture.md`\n"
        "  summary: Duplicate summary text used to test the collision guard.\n"
        "  evidence: fixture.\n"
        "  status: open\n",
    )
    promoter = _patched_promoter(repo)
    tracked_before = _tracked_text(repo, "pyforge-herald")

    r = _run(promoter, repo, "--project", "herald")
    assert r.returncode == 0, r.stdout
    assert "ABORTED" not in r.stdout
    assert "already reached the tracked ledger" in r.stdout

    assert _tracked_text(repo, "pyforge-herald") == tracked_before


# Verbatim excerpt (trimmed for fixture size), pyforge-doctor's own live
# Tier-3 backlog (`_bmad-output/projects/pyforge-doctor/implementation-
# artifacts/deferred-work.md`, lines 573-583, 2026-08-28) -- a REAL
# already-identified entry with no tracked twin (Story 8.6's own fleet-wide
# `--fix` run confirmed this class fleet-wide: 70 such entries remained
# live across 6 projects immediately after Story 8.6 landed).
_REAL_IDENTIFIED_FLEET_EXCERPT = """### DW-FU-10-1: The declared floor is taken as the max across every pixi.toml environment, not scoped to which environment is actually active
- source_spec: `_bmad-output/projects/pyforge-doctor/implementation-artifacts/spec-10-1-the-declared-floor-and-the-installed-core-are-compared-and-reported.md`
  summary: `_declared_floors` walks every `dependencies`/`feature.*.dependencies`/target-scoped table in `pixi.toml` and `gather` compares the installed core against the MAXIMUM floor found across all of them, regardless of which pixi environment an operator actually resolves/activates.
  evidence: Found by Blind Hunter during Story 10.1's own review pass (2026-08-15).
  severity: medium
  status: open
"""


def test_real_fleet_identified_entry_promotes_with_every_field_preserved_verbatim(
    tmp_path: Path,
):
    """Real excerpt (trimmed), pyforge-doctor's own live Tier-3 backlog --
    proves the identified-entry promotion path preserves a real extra
    field (`severity:`) verbatim, the same discipline `_format_promoted_
    entry` already keeps for orphans (Review Triage Log 2026-08-15, item
    3)."""
    repo = _fixture_repo(tmp_path)
    herald = repo / "_bmad-output" / "projects" / "pyforge-herald"
    _write_tier3(herald, _REAL_IDENTIFIED_FLEET_EXCERPT)
    promoter = _patched_promoter(repo)

    r = _run(promoter, repo, "--project", "herald")
    assert r.returncode == 0, r.stderr
    assert "promoted 1 already-identified entry -- DW-FU-10-1" in r.stdout

    entries = classify_tier3_entries(
        repo / "_bmad-output" / "projects" / "pyforge-herald" / TRACKED_REL
    )
    assert len(entries) == 1
    entry = entries[0]
    assert entry.id == "DW-FU-10-1"
    assert entry.fields["severity"] == "medium"
    assert entry.fields["status"] == "open"
    assert "MAXIMUM floor" in entry.fields["summary"]


# --- HIGH (2026-08-28, this story's own adversarial review): a bmad-loop
# `_harvest_spec_deferrals` damping entry (IDENTIFIED_PLAIN, no `summary:`
# field of its own -- the real text lives only in the header title, which
# `classify_tier3_entries` never captures) must be excluded from Story
# 8.7's `identified_untracked`, not treated as a blank-summary hard-abort
# for the WHOLE batch. Verbatim excerpt, pyforge-atlas's own live Tier-3
# backlog (`_bmad-output/projects/pyforge-atlas/implementation-artifacts/
# deferred-work.md`, `DW-6`, 2026-08-28) -- one of 7 real entries of this
# shape that, before this exclusion, aborted atlas's entire batch and
# blocked 57 real orphans in the same run.
_REAL_HARVEST_DAMPING_ENTRY = """### DW-6: write_ops_canvas: records whose P/Work falls back to the "?" sentinel are counted in the total but invisible in every per-bucket breakdown table; build_by_type silently drops recipe types outside the
origin: spec-deferred 81ca01b1f565
location: scripts/openteams_identity_dashboards.py:write_ops_canvas
source_spec: `spec-17-2-handoffs-are-execution-ready.md`
severity: low
reason: Mirrors a pre-existing pattern already present in this same file's render() function.
status: open
"""


# A second, independently-emitted blank-summary `IDENTIFIED_PLAIN` sub-shape
# found during a follow-up fleet-wide dry check, AFTER the first exclusion
# (scoped only to `origin: spec-deferred ...`) landed: bmad-loop's OWN
# "follow-up review still recommended after the damping cap was spent"
# output. Verbatim excerpt, pyforge-doctor's own live Tier-3 backlog
# (`_bmad-output/projects/pyforge-doctor/implementation-artifacts/
# deferred-work.md`, `DW-1`, 2026-08-28) -- confirmed live to exist on 5 of
# 8 projects (doctor 4, marshal 9, mason 3, steward 2, warden 2), which is
# why the exclusion was generalized from "origin starts with spec-deferred"
# to "blank/whitespace-only summary", regardless of origin.
_REAL_FOLLOWUP_BUDGET_ENTRY = """### DW-1: Follow-up review still recommended for 6-4-the-ledger-verdicts-come-home after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-6-4-the-ledger-verdicts-come-home.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 2) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up.
status: open
"""


def test_followup_review_budget_entry_is_also_excluded_not_promoted(tmp_path: Path):
    """The SAME class of bug as `_REAL_HARVEST_DAMPING_ENTRY`'s own test
    below, but a DIFFERENT real origin value -- proves the exclusion is
    genuinely scoped to "blank summary", not merely "spec-deferred origin"."""
    repo = _fixture_repo(tmp_path)
    doctor = repo / "_bmad-output" / "projects" / "pyforge-doctor"
    _write_tier3(doctor, _REAL_ORPHAN_C + "\n" + _REAL_FOLLOWUP_BUDGET_ENTRY)
    promoter = _patched_promoter(repo)

    r = _run(promoter, repo, "--project", "doctor")
    assert r.returncode == 0, r.stdout
    assert "ABORTED" not in r.stdout
    assert "promoted 1 orphan(s) -- DW-FU-1-8" in r.stdout

    entries = classify_tier3_entries(
        repo / "_bmad-output" / "projects" / "pyforge-doctor" / TRACKED_REL
    )
    assert len(entries) == 1
    assert entries[0].id == "DW-FU-1-8"  # only the orphan promoted; DW-1 excluded entirely


def test_harvest_damping_entry_is_excluded_not_promoted_and_does_not_block_a_sibling_orphan(
    tmp_path: Path,
):
    """The real bug found in review: `_REAL_HARVEST_DAMPING_ENTRY` has no
    `summary:` field at all -- pre-fix, this hard-aborted the WHOLE batch
    (blank-summary guard), taking down a perfectly clean sibling orphan
    with it. Post-fix: the harvest-damping entry is silently excluded
    (never promoted here -- it belongs to `deferred_work_intake.py`'s own
    fingerprint-based pipeline), and the sibling orphan promotes normally."""
    repo = _fixture_repo(tmp_path)
    doctor = repo / "_bmad-output" / "projects" / "pyforge-doctor"
    _write_tier3(doctor, _REAL_ORPHAN_C + "\n" + _REAL_HARVEST_DAMPING_ENTRY)
    promoter = _patched_promoter(repo)

    r = _run(promoter, repo, "--project", "doctor")
    assert r.returncode == 0, r.stdout
    assert "ABORTED" not in r.stdout
    assert "promoted 1 orphan(s) -- DW-FU-1-8" in r.stdout

    entries = classify_tier3_entries(
        repo / "_bmad-output" / "projects" / "pyforge-doctor" / TRACKED_REL
    )
    assert len(entries) == 1
    assert entries[0].id == "DW-FU-1-8"  # only the orphan promoted; DW-6 excluded entirely


# --- MEDIUM (2026-08-28, this story's own adversarial review): a bare id
# mention in unrelated PROSE elsewhere in the tracked ledger must not count
# as "already tracked" for Story 8.7's identified-entry membership check ---


def test_identified_entry_promotes_even_when_its_id_is_merely_mentioned_in_unrelated_prose(
    tmp_path: Path,
):
    """`tracked_ids` (`_dw_tokens`, a loose token harvest over the WHOLE
    tracked file's raw text) matches ANY `DW-`-shaped substring, including a
    plain prose mention inside an UNRELATED entry's own text -- reproduced
    live in review: an id merely referenced in someone else's `promoted:`
    note was silently classified "already tracked" and permanently skipped
    (exit 0, no warning), the exact "silently never promoted" failure class
    this capability exists to close. Fixed by checking `identified_
    untracked` membership against `tracked_header_ids` (real `### DW-*:`
    headers only) instead. This entry's real id (`DW-9-1`) is mentioned in
    an UNRELATED tracked entry's own summary text, but has no header of its
    own -- it must still promote."""
    repo = _fixture_repo(tmp_path)
    herald = repo / "_bmad-output" / "projects" / "pyforge-herald"
    _write_tracked(
        herald,
        "### DW-1-1-1: An unrelated tracked entry that merely MENTIONS DW-9-1 in prose\n\n"
        "- source_spec: `spec-fixture.md`\n"
        "  summary: This entry references DW-9-1 in passing, but DW-9-1 has no header of its own here.\n"
        "  evidence: fixture-only content.\n"
        "  status: open\n",
    )
    _write_tier3(
        herald,
        "### DW-9-1: genuinely never promoted, only mentioned in someone else's prose\n\n"
        "- source_spec: `spec-9-1-fixture.md`\n"
        "  summary: A real, still-open finding that must not be swallowed by a false-positive prose match.\n"
        "  evidence: fixture.\n"
        "  status: open\n",
    )
    promoter = _patched_promoter(repo)

    r = _run(promoter, repo, "--project", "herald")
    assert r.returncode == 0, r.stderr
    assert "nothing to promote" not in r.stdout
    assert "promoted 1 already-identified entry -- DW-9-1" in r.stdout

    entries = classify_tier3_entries(
        repo / "_bmad-output" / "projects" / "pyforge-herald" / TRACKED_REL
    )
    ids = {e.id for e in entries}
    assert ids == {"DW-1-1-1", "DW-9-1"}  # DW-9-1 landed as its own real entry


# --- I/O matrix row: missing Tier-3 file -- no-op, not an error ---


def test_project_with_no_tier3_file_is_a_noop_not_an_error(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    (repo / "_bmad-output" / "projects" / "pyforge-warden").mkdir(parents=True)
    promoter = _patched_promoter(repo)

    r = _run(promoter, repo, "--project", "warden")
    assert r.returncode == 0, r.stderr
    assert "no Tier-3 file" in r.stdout


def test_bare_fix_with_no_project_processes_every_discovered_project(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    promoter = _patched_promoter(repo)

    r = _run(promoter, repo)
    assert r.returncode == 0, r.stderr
    assert "mason: promoted 2 orphan(s)" in r.stdout
    assert "doctor: promoted 1 orphan(s)" in r.stdout


# --- I/O matrix row: manufactured duplicate summary -- abort, no write ---


def test_manufactured_duplicate_summary_within_batch_aborts_with_no_write(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    mason = repo / "_bmad-output" / "projects" / "pyforge-mason"
    _write_tier3(mason, _DUP_SUMMARY_A + "\n" + _DUP_SUMMARY_B)
    promoter = _patched_promoter(repo)
    tier3_before = _tier3_text(repo, "pyforge-mason")
    tracked_before = _tracked_text(repo, "pyforge-mason")

    r = _run(promoter, repo, "--project", "mason")
    assert r.returncode != 0
    assert "ABORTED" in r.stdout
    assert "duplicate summary" in r.stdout

    assert _tier3_text(repo, "pyforge-mason") == tier3_before
    assert _tracked_text(repo, "pyforge-mason") == tracked_before


def test_orphan_already_matching_a_tracked_entry_is_skipped_not_aborted(
    tmp_path: Path,
):
    """DW-FU-8-4 (2026-08-28, this collision's own real-world discovery
    session): an orphan whose content was already promoted by the by-hand
    process, without Tier-3 ever growing a header for it -- mints a FRESH
    id (no id collision) but carries the SAME summary text as an already-
    tracked entry. This must NOT abort (the original bug this fix closes:
    a project promoted once could never promote a genuinely new orphan
    added later, because this exact re-collision aborted the WHOLE batch
    forever, every single run) -- it is silently excluded from the write
    instead. With nothing else in the batch, there is nothing new to
    write, so this is a clean no-op (exit 0), not a failure."""
    repo = _fixture_repo(tmp_path)
    mason = repo / "_bmad-output" / "projects" / "pyforge-mason"
    existing_with_dup = _MASON_EXISTING_TRACKED.replace(
        "An unrelated pre-existing tracked entry, used only to prove appends "
        "land after existing content.",
        "Duplicate summary text used to test the collision guard.",
    )
    assert existing_with_dup != _MASON_EXISTING_TRACKED
    _write_tracked(mason, existing_with_dup)
    _write_tier3(mason, _DUP_SUMMARY_A)  # summary matches the tracked entry above
    promoter = _patched_promoter(repo)
    tier3_before = _tier3_text(repo, "pyforge-mason")
    tracked_before = _tracked_text(repo, "pyforge-mason")

    r = _run(promoter, repo, "--project", "mason")
    assert r.returncode == 0, r.stdout
    assert "ABORTED" not in r.stdout
    assert "already reached the tracked ledger" in r.stdout

    assert _tier3_text(repo, "pyforge-mason") == tier3_before
    assert _tracked_text(repo, "pyforge-mason") == tracked_before


def test_a_genuinely_new_orphan_promotes_while_an_already_tracked_sibling_is_skipped(
    tmp_path: Path,
):
    """The actual DW-FU-8-4 fix, proven end to end: a batch mixing one
    already-tracked orphan (would have aborted the WHOLE batch before this
    fix) with one genuinely new orphan (no collision at all) promotes the
    new one -- the tracked ledger gains exactly one new entry -- while the
    already-tracked one is silently excluded, not re-promoted, not
    counted as a problem."""
    repo = _fixture_repo(tmp_path)
    mason = repo / "_bmad-output" / "projects" / "pyforge-mason"
    existing_with_dup = _MASON_EXISTING_TRACKED.replace(
        "An unrelated pre-existing tracked entry, used only to prove appends "
        "land after existing content.",
        "Duplicate summary text used to test the collision guard.",
    )
    assert existing_with_dup != _MASON_EXISTING_TRACKED
    _write_tracked(mason, existing_with_dup)
    # _DUP_SUMMARY_A already reached the tracked ledger above; _REAL_ORPHAN_A
    # is genuinely new (verified collision-free against pyforge-mason's real
    # backlog per this file's own module docstring).
    _write_tier3(mason, _DUP_SUMMARY_A + "\n" + _REAL_ORPHAN_A)
    promoter = _patched_promoter(repo)
    tier3_before = _tier3_text(repo, "pyforge-mason")

    r = _run(promoter, repo, "--project", "mason")
    assert r.returncode == 0, r.stdout
    assert "promoted 1 orphan(s)" in r.stdout
    assert "skipped 1 already-tracked orphan(s)" in r.stdout

    tracked_after = _tracked_text(repo, "pyforge-mason")
    assert "render_text" in tracked_after  # _REAL_ORPHAN_A's own content landed
    assert tracked_after.count("Duplicate summary text used to test") == 1, (
        "the already-tracked orphan must not be re-promoted as a second copy"
    )
    # Tier-3 itself is never touched, success or partial-skip alike.
    assert _tier3_text(repo, "pyforge-mason") == tier3_before


# --- multi-project independence: one project's collision must not block another's clean batch ---


def test_multi_project_run_one_collision_does_not_block_a_sibling_clean_project(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    mason = repo / "_bmad-output" / "projects" / "pyforge-mason"
    _write_tier3(mason, _DUP_SUMMARY_A + "\n" + _DUP_SUMMARY_B)  # mason now collides
    # pyforge-doctor (from _fixture_repo) remains a clean, single-orphan batch.
    promoter = _patched_promoter(repo)
    mason_tier3_before = _tier3_text(repo, "pyforge-mason")
    mason_tracked_before = _tracked_text(repo, "pyforge-mason")

    r = _run(promoter, repo)  # no --project: both discovered
    assert r.returncode != 0, "mason's collision must surface in the exit code"
    assert "mason: ABORTED" in r.stdout
    assert "doctor: promoted 1 orphan(s)" in r.stdout

    # mason: untouched
    assert _tier3_text(repo, "pyforge-mason") == mason_tier3_before
    assert _tracked_text(repo, "pyforge-mason") == mason_tracked_before
    # doctor: written successfully despite mason's failure
    assert _tracked_text(repo, "pyforge-doctor") is not None


# --- Tier-3 provably untouched, success or failure ---


def test_tier3_is_byte_identical_after_a_successful_run(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    promoter = _patched_promoter(repo)
    before = _tier3_text(repo, "pyforge-mason")

    r = _run(promoter, repo, "--project", "mason")
    assert r.returncode == 0, r.stderr
    assert _tier3_text(repo, "pyforge-mason") == before


def test_tier3_is_byte_identical_after_an_aborted_run(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    mason = repo / "_bmad-output" / "projects" / "pyforge-mason"
    _write_tier3(mason, _DUP_SUMMARY_A + "\n" + _DUP_SUMMARY_B)
    promoter = _patched_promoter(repo)
    before = _tier3_text(repo, "pyforge-mason")

    r = _run(promoter, repo, "--project", "mason")
    assert r.returncode != 0
    assert _tier3_text(repo, "pyforge-mason") == before


# --- error paths ---


def test_unknown_project_exits_two_and_names_the_known_set(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    promoter = _patched_promoter(repo)

    r = _run(promoter, repo, "--project", "not-a-real-project")
    assert r.returncode == 2
    assert "unknown project" in r.stderr
    assert "mason" in r.stderr and "doctor" in r.stderr
    # pyforge-mason's tracked ledger is SEEDED by the fixture itself
    # (_MASON_EXISTING_TRACKED) -- a usage error must leave it byte-identical,
    # not merely "not None".
    assert _tracked_text(repo, "pyforge-mason") == _MASON_EXISTING_TRACKED
    assert _tracked_text(repo, "pyforge-doctor") is None


def test_project_given_without_fix_is_a_usage_error(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    promoter = _patched_promoter(repo)

    r = subprocess.run(
        [sys.executable, str(promoter), "--project", "mason"],
        env=_subprocess_env(),
        capture_output=True, text=True, cwd=repo,
    )
    assert r.returncode == 2
    assert "--fix" in r.stderr
    assert _tracked_text(repo, "pyforge-mason") == _MASON_EXISTING_TRACKED


def test_bare_invocation_explains_purpose_and_does_not_write(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    promoter = _patched_promoter(repo)

    r = subprocess.run([sys.executable, str(promoter)], capture_output=True, text=True, cwd=repo, env=_subprocess_env())
    assert r.returncode == 2
    assert "--fix" in r.stderr
    assert _tracked_text(repo, "pyforge-mason") == _MASON_EXISTING_TRACKED
    assert _tracked_text(repo, "pyforge-doctor") is None


def test_no_project_anywhere_has_a_tier3_file_is_a_clean_noop(tmp_path: Path):
    (tmp_path / "_bmad-output" / "projects").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    promoter = _patched_promoter(tmp_path)

    r = _run(promoter, tmp_path)
    assert r.returncode == 0, r.stderr
    assert "nothing to do" in r.stdout


# --- defense-in-depth: manufactured id collision (bypasses the normal mint path) ---


def _import_promoter_module():
    """Import the REAL `scripts/deferred_work_promote.py` in-process (not
    via subprocess) so its PURE `_validate_batch` function -- or, for the
    race-condition tests below, `_promote_project` itself, monkeypatched to
    inject a race -- can be called directly. Safe to import the unpatched
    module (REPO_ROOT pointed at the real repo) here: `_validate_batch`
    does no I/O at all, and `_promote_project` only ever touches paths
    DERIVED FROM its own `project_dir` argument (a tmp_path fixture in
    every caller below), never the module's own `REPO_ROOT` -- unlike
    every OTHER write-exercising test in this file, which goes through
    `_patched_promoter`+subprocess specifically because the CLI layer
    around `_promote_project` (project/slug discovery) DOES resolve paths
    from `REPO_ROOT`.

    `sys.modules[name]` must be registered BEFORE `exec_module` runs: the
    module's own `from __future__ import annotations` + `@dataclass`
    combination resolves string annotations via `sys.modules.get(cls.
    __module__)`, which raises `AttributeError` on `None` if the module
    isn't registered yet at class-body-execution time."""
    import importlib.util
    import sys as _sys

    spec = importlib.util.spec_from_file_location("deferred_work_promote", PROMOTER)
    mod = importlib.util.module_from_spec(spec)
    _sys.modules["deferred_work_promote"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_validate_batch_catches_a_manufactured_id_collision():
    """`mint_id_for_entry`'s own `already_minted` threading makes an
    in-batch id collision structurally impossible via the normal pipeline
    (each call sees every id minted so far) -- per this story's own
    Boundaries, this defense-in-depth check is proven by bypassing the
    mint path entirely and calling the pure validator directly with two
    hand-constructed ``(entry, id)`` pairs that share an id, rather than
    trying to coerce the real pipeline into colliding (it can't, by
    design)."""
    mod = _import_promoter_module()
    from pyforge.doctor.sources.chain import LegacyEntry, Tier3Shape

    entry_1 = LegacyEntry(Tier3Shape.LEGACY_FLAT, None, 3, 5, {
        "source_spec": "`spec-a.md`", "summary": "first manufactured entry", "evidence": "e1",
    })
    entry_2 = LegacyEntry(Tier3Shape.LEGACY_FLAT, None, 7, 9, {
        "source_spec": "`spec-b.md`", "summary": "second manufactured entry", "evidence": "e2",
    })
    minted = [(entry_1, "DW-FU-COLLIDE"), (entry_2, "DW-FU-COLLIDE")]

    validation = mod._validate_batch(minted, tracked_ids=set(), tracked_summaries=set())
    assert any("duplicate id" in p and "DW-FU-COLLIDE" in p for p in validation.problems)
    assert validation.already_tracked == frozenset()


def test_validate_batch_catches_an_id_already_in_the_tracked_ledger():
    mod = _import_promoter_module()
    from pyforge.doctor.sources.chain import LegacyEntry, Tier3Shape

    entry = LegacyEntry(Tier3Shape.LEGACY_FLAT, None, 3, 5, {
        "source_spec": "`spec-a.md`", "summary": "an entry", "evidence": "e1",
    })
    validation = mod._validate_batch(
        [(entry, "DW-FU-ALREADY-TRACKED")],
        tracked_ids={"DW-FU-ALREADY-TRACKED"},
        tracked_summaries=set(),
    )
    assert any("already exists in the tracked ledger" in p for p in validation.problems)


def test_validate_batch_routes_a_summary_match_to_already_tracked_not_problems():
    """DW-FU-8-4's own split, at the pure-function level: a minted entry
    whose normalized summary already exists in the tracked ledger is NOT a
    `problems` entry (which would abort the whole batch) -- it is named in
    `already_tracked` by its own index into `minted`, silently excludable
    by the caller instead."""
    mod = _import_promoter_module()
    from pyforge.doctor.sources.chain import LegacyEntry, Tier3Shape

    entry = LegacyEntry(Tier3Shape.LEGACY_FLAT, None, 3, 5, {
        "source_spec": "`spec-a.md`", "summary": "Already tracked finding.", "evidence": "e1",
    })
    validation = mod._validate_batch(
        [(entry, "DW-FU-NEW-ID")],
        tracked_ids=set(),  # the ID itself is fresh -- only the summary collides
        tracked_summaries={mod._normalize_summary("Already tracked finding.")},
    )
    assert validation.problems == ()
    assert validation.already_tracked == frozenset({0})


# --- HIGH 1: the data-loss race -- re-check before write, abort on drift ---


def test_race_condition_is_detected_and_aborts_without_losing_the_concurrent_write(
    tmp_path: Path,
):
    """Reproduces the exact race Blind Hunter found: `_promote_project`
    reads the tracked ledger once (its snapshot), does all validation, and
    used to write once at the bottom with no re-check -- a concurrent
    writer's change landing in that window was silently destroyed.

    Instrumented via monkeypatching `mint_id_for_entry` -- called strictly
    AFTER the initial snapshot and strictly BEFORE the terminal write -- to
    land a concurrent, unrelated write to the tracked ledger the FIRST time
    it is called, then delegate to the real function. Calling `_promote_
    project` directly (not via subprocess) is safe here even though it DOES
    write: every path it touches is the caller-supplied `project_dir`, never
    the module's own `REPO_ROOT` (unlike every subprocess-based test in this
    file, which goes through `_patched_promoter` because the CLI layer
    around it does resolve paths from `REPO_ROOT`)."""
    mod = _import_promoter_module()

    project_dir = tmp_path / "pyforge-mason"
    _write_tier3(project_dir, _REAL_ORPHAN_A)
    _write_tracked(project_dir, _MASON_EXISTING_TRACKED)
    tracked_path = project_dir / TRACKED_REL

    concurrent_text = (
        _MASON_EXISTING_TRACKED
        + "\n### DW-9-9-9: landed by a concurrent writer mid-run\n\n"
        "- source_spec: `spec-concurrent.md`\n"
        "  summary: landed by a concurrent writer during this run's mint/validate window.\n"
        "  evidence: fixture-only content.\n"
        "  status: open\n"
    )

    real_mint = mod.mint_id_for_entry
    call_count = {"n": 0}

    def _mint_and_race(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            tracked_path.write_text(concurrent_text, encoding="utf-8")
        return real_mint(*args, **kwargs)

    mod.mint_id_for_entry = _mint_and_race
    try:
        outcome = mod._promote_project("mason", project_dir)
    finally:
        mod.mint_id_for_entry = real_mint

    assert call_count["n"] == 1, "the race must have actually been injected"
    assert outcome.status == "aborted"
    assert "changed during this run" in outcome.message
    assert "concurrent" in outcome.message.lower()

    # The concurrent writer's content survives BYTE-IDENTICAL -- the
    # promoter must not have overwritten it (the data-loss this guards
    # against) nor appended its own entries on top of it (no write at all).
    assert tracked_path.read_text(encoding="utf-8") == concurrent_text


def test_race_condition_when_the_tracked_ledger_did_not_exist_at_snapshot_time(
    tmp_path: Path,
):
    """The Never-existed-before variant of the same race: a concurrent
    writer CREATES the tracked ledger in the window between this run's
    snapshot (which saw "does not exist") and its terminal write. Must abort
    the same way, not silently overwrite the concurrently-created file."""
    mod = _import_promoter_module()

    project_dir = tmp_path / "pyforge-doctor"
    _write_tier3(project_dir, _REAL_ORPHAN_C)
    tracked_path = project_dir / TRACKED_REL
    assert not tracked_path.exists()

    concurrent_text = "# concurrently created tracked ledger\n\nfixture-only content.\n"

    real_mint = mod.mint_id_for_entry
    call_count = {"n": 0}

    def _mint_and_race(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            tracked_path.parent.mkdir(parents=True, exist_ok=True)
            tracked_path.write_text(concurrent_text, encoding="utf-8")
        return real_mint(*args, **kwargs)

    mod.mint_id_for_entry = _mint_and_race
    try:
        outcome = mod._promote_project("doctor", project_dir)
    finally:
        mod.mint_id_for_entry = real_mint

    assert call_count["n"] == 1
    assert outcome.status == "aborted"
    assert "changed during this run" in outcome.message
    assert tracked_path.read_text(encoding="utf-8") == concurrent_text


# --- HIGH 2: atomic write (tempfile.mkstemp + os.replace) ---


def test_atomic_write_leaves_no_stray_temp_file_and_correct_content_on_success(
    tmp_path: Path,
):
    """`scripts/seed_claude_consent.py`'s own `tempfile.mkstemp` + `os.
    replace` pattern (Review Triage Log 2026-08-15, item 2): on a
    successful run, the tracked ledger's directory holds EXACTLY the
    tracked ledger file -- no `.tmp`/mkstemp-suffixed sibling left behind
    -- and its content is byte-correct."""
    repo = _fixture_repo(tmp_path)
    promoter = _patched_promoter(repo)

    r = _run(promoter, repo, "--project", "doctor")
    assert r.returncode == 0, r.stderr

    tracked_dir = repo / "_bmad-output" / "projects" / "pyforge-doctor" / TRACKED_REL.parent
    names = sorted(p.name for p in tracked_dir.iterdir())
    assert names == [TRACKED_REL.name], names

    entries = classify_tier3_entries(
        repo / "_bmad-output" / "projects" / "pyforge-doctor" / TRACKED_REL
    )
    assert len(entries) == 1
    assert entries[0].id == "DW-FU-1-8"


# --- HIGH 3: content fidelity -- extra fields preserved, status never force-overwritten ---


def test_content_fidelity_preserves_resolution_field_and_does_not_overwrite_existing_status(
    tmp_path: Path,
):
    """Real-data regression (Review Triage Log 2026-08-15, item 3,
    live-confirmed: 13 of 76 real orphans carry a `resolution:` field).
    Promotion used to silently drop any orphan field outside
    `{source_spec, summary, evidence}` and unconditionally force
    `status: open` -- risking an already-resolved item resurfacing as
    freshly open with no trace of why. Both real fields (a `resolution:`
    from pyforge-doctor's own live backlog, a non-`open` `status:` from
    pyforge-marshal's) must now survive promotion verbatim."""
    repo = _fixture_repo(tmp_path)
    herald = repo / "_bmad-output" / "projects" / "pyforge-herald"
    _write_tier3(
        herald, _REAL_ORPHAN_WITH_RESOLUTION + "\n" + _REAL_ORPHAN_WITH_NON_OPEN_STATUS
    )
    promoter = _patched_promoter(repo)

    r = _run(promoter, repo, "--project", "herald")
    assert r.returncode == 0, r.stderr
    assert "promoted 2 orphan(s)" in r.stdout

    entries = classify_tier3_entries(
        repo / "_bmad-output" / "projects" / "pyforge-herald" / TRACKED_REL
    )
    assert len(entries) == 2

    with_resolution = next(e for e in entries if "resolution" in e.fields)
    assert with_resolution.fields["resolution"].startswith(
        "Decided consciously by Story 6.9"
    )
    # This orphan carried no status: field of its own -- defaults to open.
    assert with_resolution.fields["status"] == "open"

    with_status = next(e for e in entries if e.fields.get("status") != "open")
    assert with_status.fields["status"].startswith("**LIVE as of Story 3.5**")
    # Never dropped in favor of a bare "resolution"-shaped field.
    assert "resolution" not in with_status.fields


# --- HIGH 4: a crash promoting one project must not abort the whole run ---


def test_unreadable_tier3_ancestor_fails_only_that_project_sibling_still_promotes(
    tmp_path: Path,
):
    """Reproduces both HIGH item 4 (an uncaught I/O error crashing the whole
    multi-project run) and MEDIUM item 5 (a permission-denied ancestor
    silently reading as "nothing to promote") in one real scenario:
    `pyforge-mason`'s `implementation-artifacts/` directory is unreadable
    (an ancestor of `tier3_path`, not the file itself -- `chmod 000` on the
    FILE alone would not raise, per `_probe`'s own docstring). `--project`
    is passed explicitly for BOTH projects so `_discover_projects`'s own
    (separate, out-of-scope) `.is_file()` default-scope probe cannot
    silently exclude mason from `targets` before `_promote_project` is ever
    called on it."""
    repo = _fixture_repo(tmp_path)
    mason_impl = repo / "_bmad-output" / "projects" / "pyforge-mason" / TIER3_REL.parent
    promoter = _patched_promoter(repo)
    mason_tracked_before = _tracked_text(repo, "pyforge-mason")

    mason_impl.chmod(0o000)
    try:
        r = _run(promoter, repo, "--project", "mason", "--project", "doctor")
    finally:
        mason_impl.chmod(0o755)

    assert r.returncode != 0
    # The project name AND the exception type/message are both reported --
    # never a raw, unhandled traceback past main(), and never silently
    # "mason: no Tier-3 file ... nothing to promote" (the false-negative
    # MEDIUM item 5 fixes).
    assert "mason: ABORTED" in r.stdout
    assert "PermissionError" in r.stdout
    assert "mason: no Tier-3 file" not in r.stdout
    # The sibling project's clean batch still promotes successfully --
    # the run did not crash past main().
    assert "doctor: promoted 1 orphan(s)" in r.stdout

    assert _tracked_text(repo, "pyforge-mason") == mason_tracked_before
    assert _tracked_text(repo, "pyforge-doctor") is not None


# --- MEDIUM: mint-time ValueError abort path has no partial write ---


def test_mint_failure_on_a_later_orphan_aborts_the_whole_batch_with_no_write(
    tmp_path: Path,
):
    """The one declared failure mode in the I/O matrix with no dedicated
    coverage before this pass (Review Triage Log 2026-08-15, item 6):
    `_REAL_ORPHAN_A` (first in the batch) would mint successfully on its
    own; `_BLANK_SOURCE_SPEC_ORPHAN` (second) cannot. The whole project's
    batch must abort with NO write -- not a partial write containing just
    the first orphan."""
    repo = _fixture_repo(tmp_path)
    mason = repo / "_bmad-output" / "projects" / "pyforge-mason"
    _write_tier3(mason, _REAL_ORPHAN_A + "\n" + _BLANK_SOURCE_SPEC_ORPHAN)
    promoter = _patched_promoter(repo)
    tier3_before = _tier3_text(repo, "pyforge-mason")
    tracked_before = _tracked_text(repo, "pyforge-mason")

    r = _run(promoter, repo, "--project", "mason")
    assert r.returncode != 0
    assert "ABORTED" in r.stdout
    assert "could not mint an id" in r.stdout

    assert _tier3_text(repo, "pyforge-mason") == tier3_before
    assert _tracked_text(repo, "pyforge-mason") == tracked_before


# --- MEDIUM: blank/whitespace-only summary is always invalid ---


def test_blank_summary_orphan_is_always_invalid_and_blocks_promotion(tmp_path: Path):
    """A blank/whitespace-only `summary:` used to silently defeat the
    collision guard (exempted from dedup entirely) rather than being
    treated as invalid on its own (Review Triage Log 2026-08-15, item 7) --
    a SINGLE such orphan, with no duplicate anywhere, must still block."""
    repo = _fixture_repo(tmp_path)
    mason = repo / "_bmad-output" / "projects" / "pyforge-mason"
    _write_tier3(mason, _BLANK_SUMMARY_ORPHAN)
    promoter = _patched_promoter(repo)
    tracked_before = _tracked_text(repo, "pyforge-mason")

    r = _run(promoter, repo, "--project", "mason")
    assert r.returncode != 0
    assert "ABORTED" in r.stdout
    assert "blank/whitespace-only summary" in r.stdout

    assert _tracked_text(repo, "pyforge-mason") == tracked_before


# --- MEDIUM: whitespace/casing-only summary difference is now caught ---


def test_whitespace_and_casing_only_summary_difference_is_caught_as_a_duplicate(
    tmp_path: Path,
):
    """Blind Hunter's own named real-world variant: a summary lightly
    reworded/whitespace-normalized during a by-hand promotion pass. Byte-
    exact comparison missed this; normalized (casefold + collapse internal
    whitespace) comparison now catches it (Review Triage Log 2026-08-15,
    item 8) -- without attempting full fuzzy/near-duplicate matching."""
    repo = _fixture_repo(tmp_path)
    mason = repo / "_bmad-output" / "projects" / "pyforge-mason"
    _write_tier3(mason, _DUP_SUMMARY_A + "\n" + _DUP_SUMMARY_WHITESPACE_VARIANT)
    promoter = _patched_promoter(repo)
    tier3_before = _tier3_text(repo, "pyforge-mason")
    tracked_before = _tracked_text(repo, "pyforge-mason")

    r = _run(promoter, repo, "--project", "mason")
    assert r.returncode != 0
    assert "ABORTED" in r.stdout
    assert "duplicate summary" in r.stdout

    assert _tier3_text(repo, "pyforge-mason") == tier3_before
    assert _tracked_text(repo, "pyforge-mason") == tracked_before


# --- LOW: `_project_slug_map` raises on a short-slug collision ---


def test_project_slug_map_raises_a_clear_error_on_a_short_slug_collision(tmp_path: Path):
    """Two project directories colliding on the same short `--project` slug
    used to silently let a dict comprehension clobber one entry, making a
    project unreachable via `--project` with no error (Review Triage Log
    2026-08-15, item 9)."""
    repo = _fixture_repo(tmp_path)
    projects = repo / "_bmad-output" / "projects"
    # `pyforge-mason` (from `_fixture_repo`) and a stray `mason` directory
    # both map to the short slug "mason".
    _write_tier3(projects / "mason", _REAL_ORPHAN_A)
    promoter = _patched_promoter(repo)

    r = _run(promoter, repo)
    assert r.returncode == 2
    assert "mason" in r.stderr
    assert "pyforge-mason" in r.stderr
    assert "both map to the same" in r.stderr

    # No project was ever reached -- the collision is a startup-time error.
    assert _tracked_text(repo, "pyforge-mason") == _MASON_EXISTING_TRACKED
    assert _tracked_text(repo, "pyforge-doctor") is None


# --- LOW: tracked_path resolving to a directory gets a friendly error ---


def test_tracked_path_is_a_directory_gets_a_friendly_error(tmp_path: Path):
    """A `tracked_path` that already resolves to a directory (an operator
    mistake) gets an explicit, friendly refusal naming the problem, rather
    than a raw `IsADirectoryError` traceback caught only by the generic
    per-project exception boundary (Review Triage Log 2026-08-15, item 10)."""
    repo = _fixture_repo(tmp_path)
    doctor = repo / "_bmad-output" / "projects" / "pyforge-doctor"
    (doctor / TRACKED_REL).mkdir(parents=True)
    promoter = _patched_promoter(repo)
    tier3_before = _tier3_text(repo, "pyforge-doctor")

    r = _run(promoter, repo, "--project", "doctor")
    assert r.returncode != 0
    assert "doctor: ABORTED" in r.stdout
    assert "is a directory, not a file" in r.stdout
    assert "IsADirectoryError" not in r.stdout  # the FRIENDLY message, not a raw traceback

    assert _tier3_text(repo, "pyforge-doctor") == tier3_before


# --- Story 8.4: the baseline re-stamps so a second run is a no-op ---------------


def test_successful_promotion_restamps_baseline_and_clears_anonymous_backlog(
    tmp_path: Path,
):
    """The full CAP-6/CAP-7 loop this story closes: after a clean `--fix`
    promotion, `pyforge-mason`'s grandfather baseline is re-stamped to its
    current `_anonymous()` count -- and, critically, `chain.py`'s own
    `_anonymous(t3_path)` sliced from that new count onward is empty, i.e.
    `tier3-entry-unidentified` would report ZERO findings for this project
    immediately after (the story's own Acceptance Criteria)."""
    from pyforge.doctor.sources.chain import _anonymous

    repo = _fixture_repo(tmp_path)
    promoter = _patched_promoter(repo)
    assert _baseline(repo) is None

    r = _run(promoter, repo, "--project", "mason")
    assert r.returncode == 0, r.stderr
    assert "promoted 2 orphan(s)" in r.stdout

    baseline = _baseline(repo)
    assert baseline is not None

    tier3_path = repo / "_bmad-output" / "projects" / "pyforge-mason" / TIER3_REL
    anon_positions = _anonymous(tier3_path)
    new_count = baseline["pyforge-mason"]
    assert new_count == len(anon_positions)
    assert anon_positions[new_count:] == [], (
        "tier3-entry-unidentified would still report findings for "
        "pyforge-mason immediately after a clean --fix promotion"
    )


def test_promoting_only_identified_entries_never_touches_the_baseline(tmp_path: Path):
    """Story 8.7: the baseline exists solely to grandfather ORPHAN counts
    for `tier3-entry-unidentified`. A run that promotes ONLY an already-
    identified entry (0 orphans) must never touch it -- even though a real
    promotion (and a real ledger write) did happen this time, unlike the
    old `test_no_orphans_project_leaves_baseline_absent` this replaces,
    where nothing was written at all."""
    repo = _fixture_repo(tmp_path)
    herald = repo / "_bmad-output" / "projects" / "pyforge-herald"
    _write_tier3(
        herald,
        "### DW-9-1: already identified, never copied to the tracked ledger\n\n"
        "- source_spec: `spec-9-1-fixture.md`\n"
        "  summary: already has an id.\n"
        "  evidence: fixture.\n"
        "  status: open\n",
    )
    promoter = _patched_promoter(repo)
    assert _baseline(repo) is None

    r = _run(promoter, repo, "--project", "herald")
    assert r.returncode == 0, r.stderr
    assert "promoted 1 already-identified entry" in r.stdout
    assert _tracked_text(repo, "pyforge-herald") is not None  # the promotion DID happen
    assert _baseline(repo) is None  # but the baseline stays untouched


def test_promoting_only_identified_entries_leaves_an_existing_baseline_byte_identical(
    tmp_path: Path,
):
    """Same guarantee as above, against an ALREADY-stamped baseline (from a
    sibling project's own clean orphan promotion) -- proves byte-identical
    preservation, not merely "still absent"."""
    repo = _fixture_repo(tmp_path)
    herald = repo / "_bmad-output" / "projects" / "pyforge-herald"
    _write_tier3(
        herald,
        "### DW-9-1: already identified, never copied to the tracked ledger\n\n"
        "- source_spec: `spec-9-1-fixture.md`\n"
        "  summary: already has an id.\n"
        "  evidence: fixture.\n"
        "  status: open\n",
    )
    promoter = _patched_promoter(repo)

    r0 = _run(promoter, repo, "--project", "doctor")
    assert r0.returncode == 0, r0.stderr
    before = _baseline_path(repo).read_bytes()

    r = _run(promoter, repo, "--project", "herald")
    assert r.returncode == 0, r.stderr
    assert "promoted 1 already-identified entry" in r.stdout
    assert _baseline_path(repo).read_bytes() == before
    assert "pyforge-herald" not in _baseline(repo)


def test_collision_aborted_project_leaves_baseline_byte_identical(tmp_path: Path):
    """A batch that ABORTS on a collision must leave the baseline
    byte-identical -- no findings silently hidden for backlog that was
    never actually promoted (the story's own third Acceptance Criterion)."""
    repo = _fixture_repo(tmp_path)
    mason = repo / "_bmad-output" / "projects" / "pyforge-mason"
    _write_tier3(mason, _DUP_SUMMARY_A + "\n" + _DUP_SUMMARY_B)
    promoter = _patched_promoter(repo)

    # Seed an existing baseline via doctor's own clean promotion, so this
    # proves the mason collision leaves the FILE byte-identical, not merely
    # "still absent".
    r0 = _run(promoter, repo, "--project", "doctor")
    assert r0.returncode == 0, r0.stderr
    before = _baseline_path(repo).read_bytes()

    r = _run(promoter, repo, "--project", "mason")
    assert r.returncode != 0
    assert "mason: ABORTED" in r.stdout

    assert _baseline_path(repo).read_bytes() == before
    assert "pyforge-mason" not in _baseline(repo)


def test_second_fix_run_against_the_same_fixture_is_a_true_noop(tmp_path: Path):
    """Running `--fix` twice in a row against the SAME (untouched) Tier-3
    content: the second run makes 0 new ledger writes (Story 8.3's own
    duplicate-summary collision guard fires, since the first run's
    promotions are now in the tracked ledger) AND 0 baseline writes
    (nothing newly promoted the second time) -- confirmed byte-identical
    on BOTH files across the two runs.

    Pre-DW-FU-8-4 (2026-08-28), a true no-op ACHIEVED this byte-identical
    result via a whole-batch ABORT (exit 1) -- this test originally
    asserted that as correct, which is precisely the bug DW-FU-8-4 names:
    a project that reaches this state can never again promote a
    genuinely NEW orphan added later, because every subsequent run's
    batch always also contains this same, now-permanently-re-colliding
    old orphan. Post-fix, the identical byte-for-byte outcome is achieved
    via a clean no-op (exit 0) instead -- the invariant this test exists
    to prove (0 writes, both files byte-identical) is unchanged; only the
    exit-code/message shape by which that invariant is reached is."""
    repo = _fixture_repo(tmp_path)
    promoter = _patched_promoter(repo)

    r1 = _run(promoter, repo)  # bare --fix: both mason and doctor discovered
    assert r1.returncode == 0, r1.stderr
    assert "mason: promoted 2 orphan(s)" in r1.stdout
    assert "doctor: promoted 1 orphan(s)" in r1.stdout

    mason_tracked_after_1 = _tracked_text(repo, "pyforge-mason")
    doctor_tracked_after_1 = _tracked_text(repo, "pyforge-doctor")
    tier3_mason_after_1 = _tier3_text(repo, "pyforge-mason")
    tier3_doctor_after_1 = _tier3_text(repo, "pyforge-doctor")
    baseline_after_1 = _baseline_path(repo).read_bytes()

    # Content-correctness for a MULTI-project single-invocation restamp
    # (Review Triage Log 2026-08-15, item 8): two sequential read-merge-
    # write cycles against the shared baseline file in one bare --fix run
    # -- exactly what this real, unscoped invocation just did. Both
    # fixtures' Tier-3 bodies carry no headings of their own, so every
    # bullet in each is anonymous: 2 for mason (_REAL_ORPHAN_A +
    # _REAL_ORPHAN_B), 1 for doctor (_REAL_ORPHAN_C) -- matching the
    # "promoted N orphan(s)" counts already asserted above.
    assert json.loads(baseline_after_1) == {"pyforge-mason": 2, "pyforge-doctor": 1}

    r2 = _run(promoter, repo)
    # Both projects' re-classified orphans now share a summary with their
    # own just-promoted tracked twin -- DW-FU-8-4: skipped as already-
    # tracked, a clean no-op, never an abort.
    assert r2.returncode == 0, r2.stdout
    assert "mason: no write -- all 2 orphan(s) already reached the tracked ledger" in r2.stdout
    assert "doctor: no write -- all 1 orphan(s) already reached the tracked ledger" in r2.stdout
    assert "ABORTED" not in r2.stdout

    assert _tracked_text(repo, "pyforge-mason") == mason_tracked_after_1
    assert _tracked_text(repo, "pyforge-doctor") == doctor_tracked_after_1
    assert _tier3_text(repo, "pyforge-mason") == tier3_mason_after_1
    assert _tier3_text(repo, "pyforge-doctor") == tier3_doctor_after_1
    assert _baseline_path(repo).read_bytes() == baseline_after_1, (
        "the second run wrote to the baseline despite promoting nothing new"
    )


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root bypasses permission checks -- chmod(0o555) would not "
           "actually block the write this test exercises",
)
def test_baseline_write_failure_after_successful_ledger_write_is_a_separate_warning(
    tmp_path: Path,
):
    """Simulated baseline-write failure (Story 8.4's "Block If"): a
    read-only `scripts/` parent directory blocks CREATING the baseline
    file. The ledger promotion must still be reported SUCCESSFUL -- never
    rolled back, never reclassified as a failure -- with a separate,
    clearly-labeled warning naming the manual fallback command. The overall
    exit code is still non-zero, though (Review Triage Log 2026-08-15, item
    2): a caller checking only the exit code must still learn the manual
    fallback is needed, even though this project's own status is
    "promoted", not "aborted"."""
    repo = _fixture_repo(tmp_path)
    promoter = _patched_promoter(repo)
    scripts_dir = repo / "scripts"

    scripts_dir.chmod(0o555)
    try:
        r = _run(promoter, repo, "--project", "doctor")
    finally:
        scripts_dir.chmod(0o755)

    assert r.returncode != 0, (
        "a baseline re-stamp warning must make the overall exit code "
        "non-zero even though the ledger promotion itself succeeded"
    )
    assert "doctor: promoted 1 orphan(s)" in r.stdout
    assert "WARNING: baseline re-stamp failed" in r.stdout
    assert "PermissionError" in r.stdout
    assert "could not write:" in r.stdout
    assert (
        "python scripts/deferred_work_baseline.py --write-baseline "
        "--project pyforge-doctor" in r.stdout
    )

    tracked = _tracked_text(repo, "pyforge-doctor")
    assert tracked is not None
    assert not (repo / "scripts" / ".deferred-work-baseline.json").exists()
