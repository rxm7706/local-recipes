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

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMOTER = REPO_ROOT / "scripts" / "deferred_work_promote.py"

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


def _patched_promoter(repo: Path) -> Path:
    """A copy of the promoter script rooted at the fixture repo, not this
    one.

    ``str.replace`` returns its input UNCHANGED, with no error, when the
    target substring is not found -- if a future edit reformats the
    ``REPO_ROOT`` line even slightly, the "patched" copy would silently
    keep pointing at the REAL repo, and every test below would then run
    against (and mutate) the actual committed ``_bmad-output/projects/``
    tree instead of the tmp_path fixture. Assert the substitution actually
    fired."""
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
    return dst


def _run(promoter: Path, repo: Path, *extra_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(promoter), "--fix", *extra_args],
        capture_output=True, text=True, cwd=repo,
    )


def _tracked_text(repo: Path, slug: str) -> str | None:
    p = repo / "_bmad-output" / "projects" / slug / TRACKED_REL
    return p.read_text(encoding="utf-8") if p.is_file() else None


def _tier3_text(repo: Path, slug: str) -> str:
    return (repo / "_bmad-output" / "projects" / slug / TIER3_REL).read_text(encoding="utf-8")


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
    # mason mints suffixed DW-<story>-<n>, never bare -- both orphans share
    # story key 1-8 (same source_spec), so this also proves already_minted
    # threading: the second orphan must NOT collide with the first.
    assert ids == {"DW-1-8-1", "DW-1-8-2"}
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
    assert entries[0].id == "DW-FU-1-8"  # doctor is non-mason: bare DW-FU-<story>


# --- I/O matrix row: no orphans -- no-op ---


def test_project_with_only_identified_entries_is_a_noop(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    herald = repo / "_bmad-output" / "projects" / "pyforge-herald"
    _write_tier3(
        herald,
        "### DW-9-1: already identified, nothing to promote\n\n"
        "- source_spec: `spec-9-1-fixture.md`\n"
        "  summary: already has an id.\n"
        "  evidence: fixture.\n"
        "  status: open\n",
    )
    promoter = _patched_promoter(repo)

    r = _run(promoter, repo, "--project", "herald")
    assert r.returncode == 0, r.stderr
    assert "no orphans to promote" in r.stdout
    assert _tracked_text(repo, "pyforge-herald") is None


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


def test_manufactured_duplicate_summary_against_existing_tracked_entry_aborts_with_no_write(
    tmp_path: Path,
):
    """The real-world case found live in pyforge-mason's own backlog during
    this story's own research: an orphan whose content was already
    promoted by the by-hand process, without Tier-3 ever growing a header
    for it -- mints a FRESH id (no id collision) but carries the SAME
    summary text as an already-tracked entry."""
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
    assert r.returncode != 0
    assert "ABORTED" in r.stdout
    assert "already exists in the tracked ledger" in r.stdout

    assert _tier3_text(repo, "pyforge-mason") == tier3_before
    assert _tracked_text(repo, "pyforge-mason") == tracked_before


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
        capture_output=True, text=True, cwd=repo,
    )
    assert r.returncode == 2
    assert "--fix" in r.stderr
    assert _tracked_text(repo, "pyforge-mason") == _MASON_EXISTING_TRACKED


def test_bare_invocation_explains_purpose_and_does_not_write(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    promoter = _patched_promoter(repo)

    r = subprocess.run([sys.executable, str(promoter)], capture_output=True, text=True, cwd=repo)
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

    problems = mod._validate_batch(minted, tracked_ids=set(), tracked_summaries=set())
    assert any("duplicate id" in p and "DW-FU-COLLIDE" in p for p in problems)


def test_validate_batch_catches_an_id_already_in_the_tracked_ledger():
    mod = _import_promoter_module()
    from pyforge.doctor.sources.chain import LegacyEntry, Tier3Shape

    entry = LegacyEntry(Tier3Shape.LEGACY_FLAT, None, 3, 5, {
        "source_spec": "`spec-a.md`", "summary": "an entry", "evidence": "e1",
    })
    problems = mod._validate_batch(
        [(entry, "DW-FU-ALREADY-TRACKED")],
        tracked_ids={"DW-FU-ALREADY-TRACKED"},
        tracked_summaries=set(),
    )
    assert any("already exists in the tracked ledger" in p for p in problems)


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
