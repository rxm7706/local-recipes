"""The BMAD-project-drift gather filter -- Doctor's verdict on the
``pyforge-marshal`` project docs' own currency (Story 6.8, FR-15, the tenth
and last of Epic 6's Charter §6 sweep).

**Why this module exists, and why it is HERE rather than in ``pyforge.marshal``.**

Charter §6, ratified 2026-07-28: *"the Doctor holds the verdict on the Marshal's
own conformance -- the one station that would otherwise grade itself."* Ported
from ``scripts/bmad_drift_check.py``: 13 check functions covering 18 distinct
finding kinds -- a tracked doc's missing/behind ``source_pin``, a misfiled
archive artifact or stray file, a stale spec status, a stale deferred-work
reconciliation stamp, a stale count or atlas-phase list, stale rule content, a
drifted sync baseline, an uncovered project file, a Tier-1/Tier-3 filing
misalignment, an unindexed intake spec, and Dream vocabulary/ownership drift.

**Single-``Source`` naming** (mirrors ``sources/ledger.py``, not
``sources/chain.py``/``sources/board.py``): ``bmad_drift_check.py`` is one
cohesive script/detector, unlike ``chain.py``'s three or ``board.py``'s three
originally-separate scripts, so this module registers exactly one new
``Source`` member (``BMAD_DRIFT``) and exports only ``gather`` -- no
per-check ``gather_<name>`` suffix (``__all__ = ("gather",)``).

**Severity -> status mapping (the one real design decision left open by the
spec).** The origin script's own three-value severity (``HARD``/``DRIFT``/
``INFO``) maps directly onto Doctor's three-value ``DoctorStatus``
(``FAIL``/``WARN``/``OK``): ``HARD`` (breaks the drift contract outright -- a
missing pin, a misfiled archive artifact, an uncovered file) -> ``FAIL``;
``DRIFT`` (the doc is stale but the contract still holds -- a behind pin, a
stale spec status, a stale rule, a drifted baseline) -> ``WARN``; ``INFO``
(non-gating review-only findings -- a stale count worth a second look, the
one-time bootstrap note that no baseline exists yet) -> ``OK``. This mirrors
the origin script's OWN gating logic exactly: ``cmd_check`` only fails the
exit code on ``HARD``/``DRIFT`` findings, never on ``INFO`` ones -- so ``OK``
(Doctor's own "nothing here needs action" status) is the correct home for a
severity that never gated the origin script's own exit code either. The raw
severity string survives losslessly in ``evidence["severity"]`` for a
consumer that wants the original three-way distinction back; the origin's own
``target``/``fixable`` fields survive in ``evidence["subject"]``/
``evidence["fixable"]`` (``"subject"``, not ``"target"``, to avoid colliding
with this module's own ``target: Path`` repo-root parameter -- mirrors
``sources/chain.py``'s own ``evidence["subject"]`` convention for the same
concept).

**Per-check isolation, not per-file** (mirrors ``sources/chain.py``'s Design
Notes, structured in from the first draft here rather than converged on
through review passes): the origin script's ``run_checks()`` is already
decomposed into 13 independent functions, each taking only a repo root and
returning its own list with no shared mutable state -- the natural isolation
boundary is the check function itself. ``_gather`` runs each of the 13 by
NAME, looked up in this module's own globals AT CALL TIME rather than
captured into a closure at import time, so a test can
``monkeypatch.setattr(factory, "check_pins", ...)`` and have ``_gather`` pick
up the stub -- inside its own try/except, appending one
``bmad-drift-unevaluable`` WARN naming the failed check on any exception and
continuing. One check's malformed input never discards another's real
findings.

**Git access.** The origin script's ``git_head()``/``git_tracked()`` called
``subprocess.run(["git", ...])`` directly; both route through
``cli_bridge.run_git`` here (AD-5, the sole subprocess site). Both already
degrade to ``None``/``[]`` on any failure, matching the original's own broad
``except Exception``. ``check_tier_alignment`` is the one check whose
FINDINGS would go silently, confidently clean on a ``[]`` from a git failure
-- the same false-clean-on-cannot-evaluate class ``sources/chain.py``'s own
``_listdir``/``_tracked_files`` guard against -- so it degrades to a named
``bmad-drift-unevaluable`` WARN for that half instead when git is
unavailable, while its non-git docs/specs half still runs. ``check_baseline``
also reaches ``git_head()`` (via ``_fingerprint``), but never reads the LIVE
value it returns: ``FINGERPRINT_KEYS`` excludes ``"git_head"`` from the
comparison, and the finding message echoes the BASELINE FILE's own persisted
``git_head`` (a historical snapshot written by a prior ``--write-baseline``
run), never the live one. A live git failure there is therefore silently
harmless, matching the original's own behavior exactly -- verified by tracing
the original's own logic, not merely assumed.

**``docs/governance/guild-roster.json``, read as the original does, never
restated** (Part 1 of this story, merged in ``607007caa1``/PR #360):
``stations``/``guild_dreams``/``dream_statuses``/``dream_types`` are read
fresh, per call, from ``target / "docs" / "governance" / "guild-roster.json"``
inside ``check_dream_vocab``/``check_dream_owners`` -- never at module import
time, unlike the original's own module-level ``_ROSTER`` load, because a
library's ``target`` is a runtime parameter, unknown at import time. A
missing/malformed roster degrades to that one check's own
``bmad-drift-unevaluable`` WARN via the per-check isolation above, never a
crash.

**The independence rule, which is the entire point of this module:**

    This module reads the DURABLE ARTIFACTS -- tracked project docs, the sync
    baseline, ``git ls-files``, and the governance roster -- and never
    imports ``pyforge.marshal`` (or any other station package).

Mirrors ``sources/ledger.py``'s and ``sources/chain.py``'s own independence
rationale exactly: a drift verdict assembled from Marshal's own code would be
Marshal's self-report wearing Doctor's badge, and would fail in exactly the
case that matters -- when Marshal's own machinery is what broke.
``tests/unit/test_sources_factory_independence.py`` pins it.

**Degrades, never crashes** -- the house rule for every Doctor source.
``gather`` wraps ``_gather`` in ``sources.degrade_on_exception`` as an outer
safety net, on top of the per-check isolation described above: an exception
this module's own authors did not anticipate degrades to one WARN naming it,
rather than propagating.

**"Cannot evaluate" is never "clean"** -- the corollary, and the thing two
review passes were spent closing. Every stdlib primitive this module used to
answer "is this here?" or "what is in here?" (``Path.is_dir``/``is_file``,
``Path.glob``/``rglob``) swallows ``OSError`` and answers ``False``/nothing,
so an unreadable input is indistinguishable from an absent one -- and absent
reads as clean. All of them are replaced here by raising counterparts ported
from ``sources/chain.py``, which converged on the same trio through its own
review passes: ``_probe``/``_is_dir``/``_is_file`` for the existence gates,
``_listdir``/``_listdir_match`` for one directory, ``_walk`` for a recursive
one, and ``_read`` for a file's CONTENT -- the last of these being the origin
script's own blanket ``except OSError: return ""``, which survived two review
passes here because it hides in every check rather than at any one gate, and
which fabricated FALSE ``pin-missing`` HARD findings as readily as it hid real
ones. Each raise lands in ``_gather``'s per-check try/except and surfaces as
that ONE check's ``bmad-drift-unevaluable`` WARN -- except where the check
ITERATES over many files, where that boundary is too coarse: one unreadable
doc would take its readable siblings' real findings down with it, so the
seven looping checks read through ``_read_item``, which narrows the blast
radius to the one file and names it in the WARN. Likewise for GROUND TRUTH:
``_live_version`` and ``_max_single_phase`` raise when the live skill version
or the atlas phase registry cannot be read, rather than substituting the
origin CLI's own ``(0, 0, 0)``/``"N"`` placeholders -- those were safe only
because that CLI printed them in a report header an operator could see, and a
library ``gather()`` has no header. Each individual case is recorded, with
its reproduction, on the helper that closes it.

**Project dir absent is an honest WARN, not a confident empty-OK** (mirrors
``sources/chain.py``'s own "not a monorepo root" guard): the original
script's own ``main()`` treats a missing ``pyforge-marshal`` project as
"nothing to check" (a silent exit 0). A library ``gather()`` takes whatever
``target`` it is handed and cannot assume it names a real BMAD-project-hosting
repo, so a missing project tree degrades to a named WARN here instead --
claiming "every tracked doc is in sync" about a project that is not there
would be a clean bill of health for a question that was never actually asked.

**Not in this module's surface** (Boundaries: Never): ``do_fix()``/``--fix``
and ``--write-baseline`` are the origin script's own MUTATION paths -- Doctor
sources are read-only gathers, mirroring ``sources/chain.py``'s own
precedent for ``spec_surface_check.py``'s ``--write-baseline``.
"""

from __future__ import annotations

import fnmatch
import importlib.util
import json
import os
import re
import stat
import sys
from pathlib import Path

from ..cli_bridge import CliBridgeError, run_git
from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = ("gather", "ground_truth")

Ver = tuple[int, int, int]

HARD, DRIFT, INFO = "HARD", "DRIFT", "INFO"

_SEVERITY_TO_STATUS: dict[str, DoctorStatus] = {
    HARD: DoctorStatus.FAIL,
    DRIFT: DoctorStatus.WARN,
    INFO: DoctorStatus.OK,
}

#: The project this detector is deliberately scoped to -- verbatim from the
#: original's own ``PROJ`` constant. Never a per-project walk like
#: ``sources/chain.py``'s ``dream_chain``/``deferred_work``.
PROJ_REL = "_bmad-output/projects/pyforge-marshal"
IMPL_REL = f"{PROJ_REL}/implementation-artifacts"


def _proj(target: Path) -> Path:
    return target / "_bmad-output" / "projects" / "pyforge-marshal"


def _plan(target: Path) -> Path:
    return _proj(target) / "planning-artifacts"


def _impl(target: Path) -> Path:
    return _proj(target) / "implementation-artifacts"


def _skill(target: Path) -> Path:
    return target / ".claude" / "skills" / "conda-forge-expert"


def _docs_specs(target: Path) -> Path:
    return target / "docs" / "specs"


# Tracked pinned docs and their sync category -- verbatim from the original's
# own TRACKED list (see that script's own comment for the living/plan/snapshot
# category meanings). "context" retired with Story 30.2 (2026-09-06) --
# project-context.md is gone, and neither file's classify() returns it anymore.
TRACKED: list[tuple[str, str]] = [
    ("planning-artifacts/index.md", "living"),
    ("planning-artifacts/architecture.md", "living"),
    ("planning-artifacts/architecture-cf-atlas.md", "living"),
    ("planning-artifacts/architecture-conda-forge-expert.md", "living"),
    ("planning-artifacts/architecture-mcp-server.md", "living"),
    ("planning-artifacts/architecture-bmad-infra.md", "living"),
    ("planning-artifacts/integration-architecture.md", "living"),
    ("planning-artifacts/development-guide.md", "living"),
    ("planning-artifacts/deployment-guide.md", "living"),
    ("planning-artifacts/source-tree-analysis.md", "living"),
    ("planning-artifacts/project-overview.md", "living"),
    ("planning-artifacts/project-parts.json", "living"),
    ("planning-artifacts/PRD.md", "plan"),
    ("planning-artifacts/epics-regenerable-factory.md", "plan"),
    ("planning-artifacts/implementation-readiness-report.md", "snapshot"),
    ("planning-artifacts/validation-report-PRD.md", "snapshot"),
]
TRACKED_CAT = dict(TRACKED)
TRACKED_REL = set(TRACKED_CAT)
CONFIG_FILES = {".bmad-config.toml", ".bmad-config.user.toml"}
IGNORE_PARTS = {"__pycache__"}

# Known-stale CONTENT patterns -- verbatim from the original's own
# STALE_RULE_PATTERNS.
STALE_RULE_PATTERNS: list[tuple[str, str]] = [
    (r"<recipe-name>-<version>", "stale branch-naming rule — CFE convention is add-recipe-<name> (auto-memory)"),
]

STRAY_SUFFIXES = {".patch", ".diff", ".bak", ".orig", ".tmp", ".rej"}

NONTERMINAL_STATUS = re.compile(r"\b(in[-\s]?flight|in[-\s]?progress|wip|pending|draft)\b", re.I)
TERMINAL_STATUS = re.compile(r"\b(done|shipped|complete|completed|cancelled|canceled|merged)\b", re.I)

# Two-phase pin parsing (Story 25-7 follow-up): a single backtracking regex
# for "the version after an optional conda-forge-expert prefix" cannot
# safely support a COMPOUND pin like `'BMAD 6.11.0 / conda-forge-expert
# v8.84.0'` (architecture-bmad-infra.md's own new, deliberate format) --
# making `conda-forge-expert` optional in front of the version capture means
# a lazy `.*?` skip-prefix would happily stop at the FIRST version-shaped
# text it finds, which is `6.11.0` (BMAD's own version, appearing earlier in
# the string), silently returning the wrong number instead of ever reaching
# `conda-forge-expert v8.84.0`. Splitting into "find the key's value text"
# then "find `conda-forge-expert` in it and read the version right after"
# (falling back to a bare version only when `conda-forge-expert` is absent
# entirely) cannot make that mistake: the anchor is a literal substring
# search, not backtracking priority.
_PIN_KEY_RE = re.compile(r"(?:source_pin|last_synced_skill_version)[\"']?\s*:\s*(.+)")
_PIN_VER_AFTER_CFE_RE = re.compile(r"conda-forge-expert\s+v?(\d+)\.(\d+)\.(\d+)")
_PIN_BARE_VER_RE = re.compile(r"^['\"]?v?(\d+)\.(\d+)\.(\d+)")
_VER_RE = re.compile(r"\*\*v(\d+)\.(\d+)\.(\d+)\*\*")
_SKILL_DECLARED_VER_RE = re.compile(r"^version:\s*(\d+)\.(\d+)\.(\d+)", re.M)

FINGERPRINT_KEYS = (
    "skill_version",
    "schema_version",
    "mcp_tools",
    "atlas_phases",
    "gotcha_max",
    "pixi_envs",
    "phase_ids",
)


def _probe(p: Path) -> os.stat_result | None:
    """``p.stat()``, or ``None`` when ``p`` genuinely does not exist --
    RAISING when the answer cannot be determined (mirrors
    ``sources/chain.py``'s own ``_probe``, review-patched into this module
    too, Story 6.8 follow-up). ``Path.is_dir()`` swallows every ``OSError``
    and answers ``False``, so an unreadable ANCESTOR directory reads as
    absent -- and absent reads as clean, the same false-clean-on-cannot-
    evaluate class this module's per-check isolation exists to turn into an
    honest WARN, but only if the probe raises instead of lying first."""
    try:
        return p.stat()
    except FileNotFoundError, NotADirectoryError:
        return None


def _is_dir(p: Path) -> bool:
    """``p.is_dir()`` that raises rather than lying -- see ``_probe``. Every
    check's own top-level "does my input tree exist" gate reads through
    this, not the bare stdlib method, so an unreadable ancestor surfaces as
    that ONE check's ``bmad-drift-unevaluable`` WARN (via ``_gather``'s
    per-check isolation) instead of a silently empty, confidently clean
    result."""
    st = _probe(p)
    return st is not None and stat.S_ISDIR(st.st_mode)


def _is_file(p: Path) -> bool:
    """``p.is_file()`` that raises rather than lying -- see ``_probe``, and
    ``sources/chain.py``'s own ``_is_file``, whose port this is.

    The first review pass brought over ``_probe``/``_is_dir`` but not this
    third member of the same trio, leaving ``check_deferred_work``'s and
    ``check_baseline``'s own existence gates on the bare stdlib method.
    Reproduced by the follow-up pass: ``chmod 000`` on a project's
    ``implementation-artifacts/`` turned a real ``deferred-stale`` WARN into
    NO finding at all while three sibling checks WARNed -- an operator saw
    "3 checks unevaluable" with no way to learn deferred-work was a fourth."""
    st = _probe(p)
    return st is not None and stat.S_ISREG(st.st_mode)


def _listdir(d: Path) -> list[Path]:
    """A directory's entries, sorted, RAISING on an unreadable directory --
    verbatim in intent from ``sources/chain.py``'s own ``_listdir``.

    ``Path.glob``/``Path.iterdir`` swallow ``OSError`` mid-traversal and
    simply yield nothing, so an unreadable directory is indistinguishable
    from an empty one -- and "empty" reads as clean, i.e. a confident OK for
    a question that could not actually be asked. Sorting is not incidental:
    the raw ``glob`` order this replaces is ``readdir`` order, so the same
    repo state produced a different finding ORDER on different clones."""
    return sorted(d.iterdir())


def _listdir_match(d: Path, pattern: str) -> list[Path]:
    """``d.glob(pattern)`` for a NON-recursive pattern, routed through
    ``_listdir`` so an unreadable ``d`` raises instead of yielding nothing.
    Every call site keeps the origin script's own glob pattern verbatim;
    ``fnmatchcase`` is what ``pathlib`` itself matches names with, dotfiles
    included."""
    return [p for p in _listdir(d) if fnmatch.fnmatchcase(p.name, pattern)]


def _walk(d: Path) -> list[Path]:
    """Every path under ``d``, recursively -- the raising counterpart to
    ``Path.rglob("*")``, built on ``_listdir`` so an unreadable directory
    ANYWHERE in the tree raises rather than silently truncating the walk.

    ``rglob``'s swallow is the deeper half of the class ``_probe``/``_is_dir``
    close at the top level only: reproduced by the follow-up review pass,
    ``chmod 000`` on one nested ``planning-artifacts/specs/`` erased a real
    ``stale-rule`` WARN and two real ``uncovered`` HARD findings from the
    run with no WARN of any kind. Symlinked directories are not descended
    into, matching ``rglob``'s own default."""
    out: list[Path] = []
    for entry in _listdir(d):
        out.append(entry)
        if not entry.is_symlink() and _is_dir(entry):
            out.extend(_walk(entry))
    return out


def _read(path: Path) -> str:
    """The file's text, or ``""`` when it GENUINELY does not exist --
    RAISING when it exists but could not be read. The file-CONTENT member of
    the ``_probe``/``_is_dir``/``_is_file``/``_listdir``/``_walk`` family
    above; the origin script's own ``_read``, widened for two cases, each
    reproduced live.

    *Non-UTF-8 bytes.* The origin caught ``OSError`` only, so a single
    non-UTF-8 byte in a tracked doc raised ``UnicodeDecodeError`` (a
    ``ValueError``) and killed the whole script. Here that exception would
    instead be caught by ``_gather``'s per-check net, which is honest but
    discards every OTHER real finding the same check had already computed --
    reproduced by the first follow-up review pass: one stray latin-1 byte in
    one project ``.md`` erased that check's real ``stale-rule`` finding for a
    different, wholly readable file. Decoding the undecodable bytes with
    U+FFFD keeps the file's readable content scannable, so neither the file
    nor its siblings go silently unexamined -- strictly better than
    ``chain.py``'s own ``return set()`` degradation, which would read the
    file as empty and therefore clean.

    *Unreadable file.* The origin's blanket ``except OSError: return ""``
    survived two review passes here, leaving this module's headline
    invariant -- "cannot evaluate" is never "clean" -- true of every
    EXISTENCE and LISTING primitive but false of the one that answers *what
    is in this file*, which every check ultimately reads through. It failed
    BOTH ways, both reproduced by the second follow-up pass: ``chmod 000`` on
    one project ``.md`` erased its real ``stale-rule`` WARN and left a
    confident aggregate OK, while ``chmod 000`` on ``planning-artifacts/``
    manufactured FOURTEEN FALSE ``pin-missing`` HARD findings about docs
    whose pins were perfectly intact -- ``_doc_pin`` reads ``""`` as "this
    doc states no pin", so an unreadable doc is not merely lost, it is
    actively slandered. Only the genuinely-absent cases still answer ``""``:
    ``FileNotFoundError`` (an absent tracked doc or ground-truth file, which
    every caller already treats as "nothing stated here") and
    ``IsADirectoryError``/``NotADirectoryError`` (a directory named
    ``*.md``, which ``check_stale_rules`` reaches by suffix alone, and which
    the origin also read as empty). Everything else lands in ``_gather``'s
    per-check net as that ONE check's named ``bmad-drift-unevaluable``
    WARN."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_bytes().decode("utf-8", errors="replace")
    except FileNotFoundError, IsADirectoryError, NotADirectoryError:
        return ""


def _read_item(path: Path, check_name: str, target: Path, out: list[Finding]) -> str | None:
    """``_read`` for one file among MANY in the same check -- appending one
    WARN that names THAT FILE and returning ``None``, instead of letting the
    raise escape and take the whole check with it.

    ``_read`` raises on an unreadable file precisely so "cannot evaluate" is
    never reported as "clean" -- but ``_gather``'s isolation boundary is the
    CHECK, so inside a loop that raise costs every readable SIBLING's real
    finding too. Reproduced by the third review pass: three project docs
    each carrying a stale branch-naming rule produced three ``stale-rule``
    findings; ``chmod 000`` on the middle one produced ZERO, and one WARN in
    their place. That is the same argument ``_read``'s own U+FFFD decode
    rests on ("discards every OTHER real finding the same check had already
    computed"), applied at the granularity these checks actually iterate at.

    Single-input checks (``check_deferred_work``, ``check_baseline``,
    ``check_spec_indexed``'s ``CLAUDE.md``) deliberately keep the bare
    ``_read``: there is no sibling to save, so the whole check genuinely is
    unevaluable and ``_gather``'s per-check net is the right boundary."""
    try:
        return _read(path)
    except OSError as exc:
        out.append(_unevaluable(check_name, f"{_rel(path, target)}: {exc.__class__.__name__}", target))
        return None


def _rel(path: Path, target: Path) -> str:
    for base in (_proj(target), target):
        try:
            return path.relative_to(base).as_posix()
        except ValueError:
            continue
    return str(path)


def _parse_ver(s: str | None) -> Ver:
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", s or "")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (0, 0, 0)


# ---------------------------------------------------------------- ground truth
def _skill_version(target: Path) -> str | None:
    """The live conda-forge-expert version — derived from ``SKILL.md`` frontmatter
    ``version:`` (Story 33.10), never from a stamped doc pin or CHANGELOG."""
    text = _read(_skill(target) / "SKILL.md")
    fm = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not fm:
        return None
    m = _SKILL_DECLARED_VER_RE.search(fm.group(1))
    return f"{m.group(1)}.{m.group(2)}.{m.group(3)}" if m else None


def _schema_version(target: Path) -> int | None:
    m = re.search(r"SCHEMA_VERSION\s*=\s*(\d+)", _read(_skill(target) / "scripts" / "conda_forge_atlas.py"))
    return int(m.group(1)) if m else None


def _mcp_tool_count(target: Path) -> int:
    return _read(target / ".claude" / "tools" / "conda_forge_server.py").count("@mcp.tool")


def _phase_ids(target: Path) -> list[str]:
    """Top-level + sub phase IDs from the PHASES registry -- verbatim."""
    text = _read(_skill(target) / "scripts" / "conda_forge_atlas.py")
    m = re.search(r"PHASES\s*[:=].*?\[(.*?)\n\]", text, re.S)
    return re.findall(r'\(\s*"([^"]+)"', m.group(1)) if m else []


def _phase_count(target: Path) -> int:
    return len(_phase_ids(target))


def _max_single_phase(target: Path) -> str:
    """The highest single-letter atlas phase ID, RAISING when the phase
    registry could not be read.

    The origin returned a hardcoded ``"N"`` here, which was safe in a CLI
    that printed ``0 phases`` in its own report header right next to the
    finding. This module has no header, so that fallback fabricated a
    specific, actionable-looking verdict out of ground truth that was never
    read -- reproduced by the follow-up review pass: deleting
    ``conda_forge_atlas.py`` made a clean phase list acquire
    ``phase-list-stale: … omits phases through N``. Raising routes it to
    ``check_phase_lists``'s own ``bmad-drift-unevaluable`` WARN instead."""
    ids = _phase_ids(target)
    singles = [p for p in ids if re.fullmatch(r"[A-Z]", p)]
    if not singles:
        raise ValueError(
            "no single-letter atlas phase IDs in "
            f"{_rel(_skill(target) / 'scripts' / 'conda_forge_atlas.py', target)} "
            "— the PHASES registry is missing or unreadable, so no phase list "
            "can be judged stale"
        )
    return max(singles)


def _gotcha_max(target: Path) -> int | None:
    nums = [int(n) for n in re.findall(r"^###\s+G(\d+)", _read(_skill(target) / "SKILL.md"), re.M)]
    return max(nums) if nums else None


def _env_count(target: Path) -> int:
    out, in_block = 0, False
    for line in _read(target / "pixi.toml").splitlines():
        if line.strip() == "[environments]":
            in_block = True
            continue
        if in_block:
            if line.startswith("["):
                break
            if "=" in line and not line.lstrip().startswith("#"):
                out += 1
    return out


def _ground_truth(target: Path) -> dict:
    # No `recipes_churny` key (unlike the original's own `ground_truth()`):
    # that value only ever fed the original's human-readable `_print_report`
    # -- a full `recipes/` directory scan (`iterdir()` + two `glob()` passes
    # over a directory this repo's own docs describe as holding hundreds of
    # feedstocks) for a value no check in this library module reads. Review
    # pass (Story 6.8) found it computed on every `_ground_truth()` call --
    # up to four times per `gather()` -- for nothing; cut rather than carried
    # forward, since this module has no printer to feed.
    return {
        "skill_version": _skill_version(target),
        "schema_version": _schema_version(target),
        "mcp_tools": _mcp_tool_count(target),
        "atlas_phases": _phase_count(target),
        "gotcha_max": _gotcha_max(target),
        "pixi_envs": _env_count(target),
    }


def ground_truth(target: Path) -> dict:
    """Public export of ``_ground_truth`` -- Story 6.9's ``bmad-groundtruth``
    pixi task (the ``--groundtruth`` flag on ``python -m
    pyforge.doctor.sources bmad-drift``) needs a non-private entrypoint to
    print the same six live-fact keys the origin script's own
    ``--json``/``--groundtruth`` printed (``pyforge.doctor.sources.fleet_scan``'s
    baseline-delta compare reads five of them: ``skill_version``,
    ``pixi_envs``, ``mcp_tools``, ``atlas_phases``, ``schema_version``; the
    sixth, ``gotcha_max``, is carried too since the origin's own output did
    and an extra key is harmless to that consumer's ``dict.get`` reads).
    Every check in this module keeps calling the private ``_ground_truth``
    directly -- this is purely a CLI-facing export, not a rename."""
    return _ground_truth(target)


def _live_version(target: Path) -> Ver:
    """The live skill version every pin is compared against, RAISING when it
    could not be read.

    ``_skill_version`` returns ``None`` for an absent/unreadable/unparseable
    ``SKILL.md`` frontmatter ``version:``, and the origin's own
    ``_parse_ver(None)`` turns that into ``(0, 0, 0)`` -- a live version no
    real pin can ever be behind. Raising routes it to ``check_pins``'/
    ``check_deferred_work``'s own ``bmad-drift-unevaluable`` WARN instead --
    the honest answer for a comparison whose right-hand side is unknown.

    Reads ``_skill_version`` DIRECTLY rather than through ``_ground_truth``:
    that dict eagerly computes all six surface facts, so routing the live
    version through it coupled every pin comparison to five files it does
    not need. Once ``_read`` was narrowed to raise on an unreadable file
    (second follow-up pass), that coupling became a live regression --
    reproduced by the third pass: ``chmod 000`` on ``pixi.toml``, which only
    ``_env_count`` reads, raised ``PermissionError`` past ``check_pins``'
    ``except ValueError`` and erased a real ``pin-missing`` HARD finding,
    the exact outcome that check's own docstring promises cannot happen."""
    version = _skill_version(target)
    if version is None:
        raise ValueError(
            "no live conda-forge-expert version in "
            f"{_rel(_skill(target) / 'SKILL.md', target)} frontmatter "
            "— nothing to compare the tracked docs' pins against"
        )
    return _parse_ver(version)


# -------------------------------------------------------------- sync baseline
def _git_head(target: Path) -> str | None:
    """The short HEAD sha, or ``None`` on any git failure -- routed through
    ``cli_bridge.run_git`` (AD-5) instead of the original's own direct
    ``subprocess.run`` call, but degrading identically. See this module's
    own docstring for why a git failure here never changes an observable
    ``check_baseline`` finding (the value is computed but never read)."""
    try:
        out = run_git(target, ["rev-parse", "--short", "HEAD"])
    except CliBridgeError, UnicodeDecodeError:
        return None
    return out.strip() or None


def _git_tracked(target: Path, relpath: str) -> list[str] | None:
    """``git ls-files`` output for ``relpath``, or ``None`` when git is
    unavailable/``target`` is not a repository -- routed through
    ``cli_bridge.run_git`` (AD-5), unlike the original's own direct
    ``subprocess.run`` call, which swallowed every exception into an EMPTY
    list. An empty list here is indistinguishable from "nothing is tracked
    under this path," so silently returning it on a git FAILURE would let
    ``check_tier_alignment`` report a confident, clean "no tracked-impl-
    artifact" for a state that was never actually checked. ``None`` means
    "cannot evaluate"; the caller must surface that honestly."""
    try:
        out = run_git(target, ["ls-files", "--", relpath])
    except CliBridgeError, UnicodeDecodeError:
        return None
    return [ln for ln in out.splitlines() if ln.strip()]


def _fingerprint(target: Path) -> dict:
    gt = _ground_truth(target)
    fp = {k: gt[k] for k in FINGERPRINT_KEYS if k in gt}
    fp["phase_ids"] = _phase_ids(target)
    fp["git_head"] = _git_head(target)
    return fp


# ----------------------------------------------------------------- doc parsing
def _doc_pin(path: Path, text: str) -> Ver | None:
    """Return (major, minor, patch) from the frontmatter pin, or ``None`` if
    absent/corrupt -- adapted from the original's own ``doc_pin`` (the caller
    supplies the already-read text: an unreadable doc must reach
    ``check_pins``' own per-file WARN rather than being read here as ``""``
    i.e. "this doc states no pin" and slandered as ``pin-missing``), extended
    to a two-phase parse (see ``_PIN_KEY_RE``'s own comment) so a compound pin
    naming BOTH a BMAD-core version and the skill version -- e.g.
    ``'BMAD 6.11.0 / conda-forge-expert v8.84.0'`` -- reads the skill version
    that actually follows ``conda-forge-expert``, never an earlier, unrelated
    version number in the same value."""
    if not text:
        return None
    if path.suffix == ".json":
        scope = text
    else:
        parts = text.split("---", 2)
        scope = parts[1] if len(parts) >= 3 and text.lstrip().startswith("---") else text[:1500]
    key_match = _PIN_KEY_RE.search(scope)
    if key_match is None:
        return None
    value = key_match.group(1)
    m = _PIN_VER_AFTER_CFE_RE.search(value) or _PIN_BARE_VER_RE.match(value)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def _spec_status(text: str) -> str | None:
    m = re.search(r"^status\s*:\s*(.+)$", text[:2000], re.M | re.I)
    if not m:
        m = re.search(r"\*\*status\*\*\s*:?\s*(.+)$", text[:2000], re.M | re.I)
    return m.group(1).strip() if m else None


def _slug(name: str) -> str:
    s = re.sub(r"\.md$", "", name)
    s = re.sub(r"^(spec|retro)-", "", s)
    s = re.sub(r"-v?\d+\.\d+\.\d+", "", s)
    s = re.sub(r"-\d{4}-\d{2}-\d{2}", "", s)
    return s.strip("-")


def _finding(severity: str, kind: str, subject: str, detail: str, *, fixable: bool = False) -> Finding:
    """Build one ``Source.BMAD_DRIFT`` Finding from the origin's own
    ``(severity, kind, target, detail, fixable)`` shape -- see this module's
    own docstring for the severity -> status mapping rationale."""
    return Finding(
        source=Source.BMAD_DRIFT,
        check=kind,
        status=_SEVERITY_TO_STATUS[severity],
        message=detail,
        evidence={"subject": subject, "fixable": fixable, "severity": severity},
    )


def _unevaluable(check_name: str, detail: str, target: Path) -> Finding:
    """The WARN item for one ported check that raised, or degraded past its
    own internal handling -- the per-check isolation boundary this module's
    own docstring describes.

    ``target`` is carried on EVERY ``bmad-drift-unevaluable`` finding, this
    one and ``_gather``'s own missing-project variant alike, so a consumer
    reading ``evidence["check"]`` or ``evidence["target"]`` cannot
    ``KeyError`` depending on which of the two fired -- the rule
    ``sources/ledger.py`` states explicitly for its own pair of
    cannot-evaluate WARNs."""
    return Finding(
        source=Source.BMAD_DRIFT,
        check="bmad-drift-unevaluable",
        status=DoctorStatus.WARN,
        message=f"{check_name} could not be evaluated — {detail}",
        evidence={"check": check_name, "target": str(target)},
    )


# --------------------------------------------------------------------- checks
def check_pins(target: Path) -> list[Finding]:
    """Every tracked doc must carry a ``source_pin``.

    For ``living`` and ``plan`` docs, ``source_pin`` records the skill version
    the doc was last re-grounded against (Story 33.10) — a historical fact,
    not a currency claim — so ``pin-behind`` is suppressed for those
    categories. Snapshot docs still compare against the live ``SKILL.md``
    ``version:`` at INFO severity. Genuine living-doc staleness is reported
    by ``count-stale``, ``phase-list-stale``, and ``stale-rule``, not here.

    When the LIVE version cannot be read, only the behind-ness half is
    unanswerable -- a doc with no pin at all is still definitively broken.
    So that half degrades to one honest ``bmad-drift-unevaluable`` WARN and
    the ``pin-missing`` half still runs, mirroring ``check_tier_alignment``'s
    own git-unavailable shape one screen down rather than discarding a real
    HARD finding over an unrelated missing file.

    Catching ``OSError`` beside ``ValueError`` is what makes that promise
    true rather than merely stated: ``_live_version`` reads ``CHANGELOG.md``
    through ``_read``, which raises ``PermissionError`` on an unreadable
    one, and the bare ``except ValueError`` let it past (third review pass,
    reproduced). Each tracked doc is likewise read through ``_read_item``,
    so ONE unreadable doc costs that doc's verdict only, not the other
    seventeen's."""
    proj = _proj(target)
    out: list[Finding] = []
    try:
        live: Ver | None = _live_version(target)
    except (ValueError, OSError) as exc:
        live = None
        out.append(_unevaluable("check_pins", str(exc), target))
    for rel, cat in TRACKED:
        text = _read_item(proj / rel, "check_pins", target, out)
        if text is None:
            continue
        pin = _doc_pin(proj / rel, text)
        if pin is None:
            if cat != "snapshot":
                out.append(_finding(HARD, "pin-missing", rel, "missing/corrupt source_pin — breaks the drift contract"))
        elif cat == "snapshot" and live is not None and (pin[0], pin[1]) < (live[0], live[1]):
            out.append(
                _finding(
                    INFO,
                    "pin-behind",
                    rel,
                    f"pinned v{pin[0]}.{pin[1]}.{pin[2]} < live v{live[0]}.{live[1]}.{live[2]} [{cat}]",
                )
            )
    return out


def check_archive_hygiene(target: Path) -> list[Finding]:
    """Misfiled archive artifacts and throwaway strays, across the project's
    two artifact trees.

    The two trees are INDEPENDENT inputs, so each is scanned in its own
    try/except -- the split shape ``check_pins`` and ``check_tier_alignment``
    already use for their own independent halves, and the one this check was
    missing. Reproduced by the second follow-up review pass: ``chmod 000`` on
    ``planning-artifacts/`` erased two real HARD findings (a ``stray-file``
    and an ``archive-misplaced``) from a wholly READABLE
    ``implementation-artifacts/``, leaving a single WARN in their place and
    no way for an operator to learn that a readable tree had gone unvisited.

    ``OSError`` is exactly the cannot-evaluate class this module's raising
    primitives (``_is_dir``/``_listdir``/``_listdir_match``/``_is_file``)
    signal with; anything else is a real bug and still propagates to
    ``_gather``'s own coarser per-check net."""
    out: list[Finding] = []
    try:
        plan = _plan(target)
        if _is_dir(plan):
            for p in _listdir_match(plan, "sprint-change-proposal-*.md"):
                out.append(
                    _finding(
                        HARD,
                        "archive-misplaced",
                        f"planning-artifacts/{p.name}",
                        "sprint-change-proposal belongs in change-history/",
                        fixable=True,
                    )
                )
    except OSError as exc:
        out.append(_unevaluable("check_archive_hygiene", f"{exc.__class__.__name__}: {exc}", target))
    try:
        impl = _impl(target)
        if _is_dir(impl):
            for p in _listdir_match(impl, "retro-*.md"):
                out.append(
                    _finding(
                        HARD,
                        "archive-misplaced",
                        f"implementation-artifacts/{p.name}",
                        "retro belongs in retros/",
                        fixable=True,
                    )
                )
            for p in _listdir(impl):
                if _is_file(p) and p.suffix in STRAY_SUFFIXES:
                    out.append(
                        _finding(
                            HARD,
                            "stray-file",
                            f"implementation-artifacts/{p.name}",
                            "throwaway artifact (already in git history) — remove",
                            fixable=True,
                        )
                    )
    except OSError as exc:
        out.append(_unevaluable("check_archive_hygiene", f"{exc.__class__.__name__}: {exc}", target))
    return out


def check_spec_status(target: Path) -> list[Finding]:
    out: list[Finding] = []
    impl = _impl(target)
    if not _is_dir(impl):
        return out
    retro_slugs = []
    retros_dir = impl / "retros"
    if _is_dir(retros_dir):
        retro_slugs = [_slug(p.name) for p in _listdir_match(retros_dir, "retro-*.md")]
    for spec in _listdir_match(impl, "spec-*.md"):
        text = _read_item(spec, "check_spec_status", target, out)
        if text is None:
            continue
        status = _spec_status(text)
        if not status or TERMINAL_STATUS.search(status) or not NONTERMINAL_STATUS.search(status):
            continue
        sslug = _slug(spec.name)
        shipped = any(sslug and (sslug in rs or rs in sslug) for rs in retro_slugs)
        if shipped:
            out.append(
                _finding(
                    DRIFT,
                    "spec-status-stale",
                    f"implementation-artifacts/{spec.name}",
                    f"status '{status}' but a matching retro exists — it shipped",
                )
            )
    return out


def check_deferred_work(target: Path) -> list[Finding]:
    # `_live_version` is resolved HERE, not at the top: it is needed only for
    # the final staleness comparison, so a repo with no deferred-work.md (or
    # one with no reconciliation stamp at all) reaches its verdict without
    # depending on -- or degrading over -- the live skill version. Also spares
    # the common no-file case a whole `_ground_truth` computation.
    df = _impl(target) / "deferred-work.md"
    if not _is_file(df):
        return []
    text = _read(df)
    m = re.search(r"last\s+reconciled[^\n]*?v(\d+)\.(\d+)\.(\d+)", text, re.I)
    if not m:
        return [
            _finding(
                DRIFT,
                "deferred-stale",
                "implementation-artifacts/deferred-work.md",
                "no 'Last reconciled: ... vX.Y.Z' stamp — cannot tell if it is current",
            )
        ]
    live = _live_version(target)
    pin = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    if (pin[0], pin[1]) < (live[0], live[1]):
        return [
            _finding(
                DRIFT,
                "deferred-stale",
                "implementation-artifacts/deferred-work.md",
                f"reconciled at v{pin[0]}.{pin[1]}.{pin[2]} < live v{live[0]}.{live[1]}.{live[2]}",
            )
        ]
    return []


def check_counts(target: Path) -> list[Finding]:
    gt = _ground_truth(target)
    proj = _proj(target)
    out: list[Finding] = []
    probes = [
        (r"schema v(\d+)\b", gt["schema_version"], "schema"),
        (r"(\d+)\s+MCP tools", gt["mcp_tools"], "MCP tools"),
        (r"G1[–-]G(\d+)", gt["gotcha_max"], "gotcha range"),
        (r"(\d+)\s+pixi envs", gt["pixi_envs"], "pixi envs"),
    ]
    for rel, cat in TRACKED:
        if cat != "living":
            continue
        text = _read_item(proj / rel, "check_counts", target, out)
        if text is None:
            continue
        for pat, live_val, label in probes:
            if live_val is None:
                continue
            for mm in re.finditer(pat, text):
                if int(mm.group(1)) < live_val:
                    out.append(
                        _finding(
                            INFO,
                            "count-stale",
                            rel,
                            f"states {label} {mm.group(1)} < live {live_val} (review in context)",
                        )
                    )
                    break
    return out


def check_stale_rules(target: Path) -> list[Finding]:
    out: list[Finding] = []
    proj = _proj(target)
    if not _is_dir(proj):
        return out
    for path in _walk(proj):
        if path.suffix != ".md":
            continue
        if any(p in IGNORE_PARTS for p in path.parts):
            continue
        text = _read_item(path, "check_stale_rules", target, out)
        if text is None:
            continue
        for pat, why in STALE_RULE_PATTERNS:
            if re.search(pat, text):
                out.append(_finding(DRIFT, "stale-rule", _rel(path, target), why))
    return out


def check_phase_lists(target: Path) -> list[Finding]:
    out: list[Finding] = []
    # `hi` is resolved LAZILY, on the first doc that actually contains a
    # judgeable phase list. `_max_single_phase` raises when the atlas PHASES
    # registry cannot be read, and this check should degrade to a
    # `bmad-drift-unevaluable` WARN only when there was in fact something to
    # judge -- a repo with no phase lists anywhere has nothing to say about a
    # registry it never needed.
    hi: str | None = None
    proj = _proj(target)
    for rel, cat in TRACKED:
        if cat == "snapshot":
            continue
        text = _read_item(proj / rel, "check_phase_lists", target, out)
        if text is None:
            continue
        for m in re.finditer(r"\bB(?:/[A-Z](?:\.\d)?'?){4,}", text):
            seg = m.group(0)
            if "/C/" not in seg or "/D" not in seg:
                continue
            if hi is None:
                hi = _max_single_phase(target)
            if f"/{hi}" not in seg and not seg.endswith(hi):
                out.append(
                    _finding(
                        DRIFT, "phase-list-stale", rel, f"atlas-phase list '{seg[:32]}…' omits phases through {hi}"
                    )
                )
                break
    return out


def check_baseline(target: Path) -> list[Finding]:
    """Port of the original's own ``check_baseline()``. ``_fingerprint``'s
    own ``git_head`` field is computed via ``_git_head`` (routed through
    ``cli_bridge.run_git``, AD-5) but -- exactly as in the original -- never
    READ here: ``FINGERPRINT_KEYS`` excludes ``"git_head"`` from the
    comparison loop below, and the finding message echoes the BASELINE
    FILE's own persisted ``git_head`` (a historical snapshot), never the
    live value. A live git failure therefore never changes an observable
    finding for this check."""
    baseline = _proj(target) / ".sync-baseline.json"
    if not _is_file(baseline):
        return [
            _finding(
                INFO,
                "no-baseline",
                ".sync-baseline.json",
                "no reconciliation baseline — run `bmad-drift-check -- --write-baseline` after a sync",
            )
        ]
    # `_read` is deliberately OUTSIDE the try: it now raises on a file that
    # exists but cannot be read, and the origin's blanket `except OSError`
    # here turned that into a `baseline-corrupt` HARD accusation against a
    # byte-for-byte VALID baseline (third review pass, reproduced live with
    # `chmod 000`). "I could not read it" is not "it is corrupt"; the raise
    # belongs in `_gather`'s per-check net as an honest WARN. Only a genuine
    # parse failure -- `ValueError` from `json.loads` -- is corruption.
    text = _read(baseline)
    try:
        base = json.loads(text)
    except ValueError:
        return [_finding(HARD, "baseline-corrupt", ".sync-baseline.json", "cannot parse baseline JSON")]
    if not isinstance(base, dict):
        # Syntactically valid JSON that isn't an object (`[]`, `"oops"`, `42`)
        # doesn't raise above, so without this guard it falls through to
        # `base.get(k)` and raises AttributeError -- caught only by the
        # coarse per-check safety net in `_gather`, losing the precise
        # `baseline-corrupt` HARD finding this case is supposed to produce.
        # `sources/chain.py` already established this exact guard for the
        # identical "valid JSON, wrong shape" class one module over (Story
        # 6.8 review pass).
        return [_finding(HARD, "baseline-corrupt", ".sync-baseline.json", "baseline JSON is not an object")]
    live, out = _fingerprint(target), []
    for k in FINGERPRINT_KEYS:
        if base.get(k) != live.get(k):
            out.append(
                _finding(
                    DRIFT,
                    "surface-changed",
                    k,
                    f"{k}: baseline {base.get(k)} -> live {live.get(k)} "
                    f"(out-of-band change since git {base.get('git_head')})",
                )
            )
    return out


def classify(path: Path, target: Path) -> str:
    """Filing-convention classifier for one file under the project tree --
    verbatim from the original's own ``classify()``, comments included: they
    record non-obvious filing rules that are load-bearing context for future
    maintainers (each block below names the date/incident that added it)."""
    rel = _rel(path, target)
    if any(part in IGNORE_PARTS for part in path.parts):
        return "ignored"
    if rel in CONFIG_FILES:
        return "config"
    if rel == ".sync-baseline.json":
        return "baseline"
    if rel == "SYNC-RUNBOOK.md":
        return "runbook"
    if rel in TRACKED_REL:
        return f"tracked:{TRACKED_CAT[rel]}"
    if rel.startswith("planning-artifacts/change-history/"):
        return "archive:change-history"
    # --- the 6.10 sharded station shape -------------------------------------
    # Added 2026-07-28 when this detector was retargeted from the dissolved
    # `local-recipes` placeholder onto `pyforge-marshal`. It had only ever seen one
    # project's shape; a station carries its OWN chain artifacts too — sharded PRD and
    # architecture run folders, per-chain epics, briefs, upstream reports. Fourteen files
    # landed as `uncovered` on the first run, which is the coverage rule working: an
    # unclassified file is a hole, not a pass.
    if re.fullmatch(r"planning-artifacts/prds/prd-[a-z0-9-]+-\d{4}-\d{2}-\d{2}/[A-Za-z0-9._-]+", rel):
        return "tracked:plan"  # bmad-prd run folder: prd.md + memlog + reviews
    if re.fullmatch(r"planning-artifacts/architecture/architecture-[a-z0-9-]+-\d{4}-\d{2}-\d{2}/.*", rel):
        return "tracked:plan"  # bmad-architecture run folder (incl. reviews/)
    if re.fullmatch(r"planning-artifacts/briefs/brief-[a-z0-9-]+-\d{4}-\d{2}-\d{2}/[A-Za-z0-9._-]+", rel):
        return "tracked:plan"
    if re.fullmatch(r"planning-artifacts/epics(-[a-z0-9-]+)?\.md", rel):
        # The station's own epics.md, plus chain-scoped epics-<slug>.md for chains that
        # moved in under Charter §5 (the destination keeps its own epics.md).
        return "tracked:plan"
    if re.fullmatch(r"planning-artifacts/product-brief-[a-z0-9-]+\.md", rel):
        return "tracked:plan"
    if re.fullmatch(r"planning-artifacts/research/[A-Za-z0-9._-]+\.md", rel):
        return "archive:research"  # undated research + briefs filed under research/
    if re.fullmatch(r"planning-artifacts/upstream-report-[a-z0-9-]+\.md", rel):
        return "archive:change-history"  # frozen upstream defect report
    if re.fullmatch(r"planning-artifacts/implementation-readiness-report-\d{4}-\d{2}-\d{2}\.md", rel):
        # A dated re-run of the readiness gate alongside the undated TRACKED one (line ~84).
        # Not pin-gated by this rule, same as sharded prd/arch/epics — a future re-run needs
        # no new TRACKED entry to stay covered.
        return "tracked:snapshot"
    if rel == "planning-artifacts/README.md":
        return "tracked:living"
    # --- shapes that landed as `uncovered` on 2026-08-08 ----------------------
    # Same lesson as the 6.10 sharding block above: an unclassified file is a hole,
    # not a pass. These eleven were the standing HARD findings that made
    # test_bmad_artifacts_integrity red.
    if rel == "README.md":
        # The station's own README (`# PyForge Station: <slug>`) — hand-maintained
        # orientation for the project dir, sibling of planning-artifacts/README.md.
        return "tracked:living"
    if rel == "planning-artifacts/specs/README.md":
        # The story-spec index that documents the tracked/durable spec convention
        # (specs survive worktree teardown). Hand-authored prose, not pin-gated.
        return "tracked:living"
    if rel == "planning-artifacts/test-architecture.md":
        # bmad test-architecture output — a chain artifact alongside prd/architecture,
        # so it classifies with them rather than earning its own category.
        return "tracked:plan"
    if rel in (
        "planning-artifacts/test-design-architecture.md",
        "planning-artifacts/test-design-qa.md",
    ) or re.fullmatch(r"planning-artifacts/test-design/[A-Za-z0-9._-]+-handoff\.md", rel):
        # Story 31.1 (spec-bmad-suite-lifecycle CAP-4): TEA's real
        # bmad-testarch-test-design output (system-level mode) — the same chain-artifact
        # role as test-architecture.md above, kept as an additive artifact regardless of
        # the equivalence outcome (see planning-artifacts/reviews/tea-equivalence-*.md).
        return "tracked:plan"
    if rel == "planning-artifacts/test-design-progress-system.md":
        # TEA workflow's own per-run checkpoint (Story 31.1) — regenerated on every
        # bmad-testarch-test-design invocation, same "dated re-run" shape as the
        # implementation-readiness-report snapshot above.
        return "tracked:snapshot"
    if re.fullmatch(r"planning-artifacts/reviews/[A-Za-z0-9._-]+\.md", rel):
        # Story 31.1: a top-level review artifact (e.g. the TEA equivalence report),
        # distinct from the sharded per-run `architecture-.../reviews/` folders already
        # matched above. Classifies with the other chain review artifacts.
        return "tracked:plan"
    if rel == "planning-artifacts/upstream-register.json":
        # Marshal's hand-curated register of upstream bmad-loop gaps + workarounds
        # (FR-58/AD-2), read by `marshal upstream`. Curated data, so git review — not
        # a version pin — decides content changes.
        return "tracked:register"
    if re.fullmatch(r"implementation-artifacts/epic-\d+-retro-\d{4}-\d{2}-\d{2}\.md", rel):
        # Dated per-epic retros written at the implementation-artifacts ROOT. The
        # pre-existing rule only matched the retros/ subdir, so these fell through.
        return "archive:retros"
    if re.fullmatch(r"implementation-artifacts/runs/[A-Za-z0-9._-]+/.*", rel):
        # bmad-loop run records (journal.jsonl et al) — Tier-3, gitignored, written by
        # the engine per run. Never hand-edited and never pin-gated.
        return "local:run-journal"
    if re.fullmatch(r"implementation-artifacts/dispatch-runs/[A-Za-z0-9._-]+/.*", rel):
        # Marshal single-story dispatch run records (session.log,
        # dispatch-supervisor.log, journal.jsonl) — Story 22.x's sibling to the
        # bmad-loop `runs/` shape above, at a different directory name
        # (`dispatch-runs/`) the existing rule doesn't match. Same Tier-3,
        # gitignored, engine-written, never hand-edited, never pin-gated shape.
        return "local:run-journal"
    if re.fullmatch(r"implementation-artifacts/fleet-drain-runs/[A-Za-z0-9._-]+/.*", rel):
        # Marshal `factory drain` campaign records (fleet-drain-supervisor.log,
        # journal.jsonl) — a third sibling of the `runs/`/`dispatch-runs/` shapes
        # above, at yet another directory name the existing rules don't match.
        # Same Tier-3, gitignored, engine-written, never hand-edited, never
        # pin-gated shape.
        return "local:run-journal"
    if re.fullmatch(r"implementation-artifacts/epic-\d+-context\.md", rel):
        return "local:sprint-feed"  # Tier-3 story context, gitignored
    if re.fullmatch(r"planning-artifacts/prfaq-[a-z0-9-]+(-distillate)?\.md", rel):
        # PRFAQ kill-test records + distillates (bmad-prfaq): frozen stress-test
        # outputs — no pin gating.
        return "archive:prfaq"
    if re.fullmatch(r"planning-artifacts/campaign-[a-z0-9-]+-\d{4}-\d{2}-\d{2}\.md", rel):
        # Campaign records (a dated, program-scale effort across many projects —
        # e.g. the 2026-07-25 spec-completion campaign): frozen after the campaign
        # closes, like a retro. Historical account, so no pin gating.
        return "archive:campaign"
    if re.fullmatch(r"planning-artifacts/research/[a-z0-9-]+-research-\d{4}-\d{2}-\d{2}\.md", rel):
        # Research reports (bmad-domain/market/technical-research skills, plus
        # backfilled distillations): dated point-in-time snapshots — never
        # re-grounded, so no pin gating.
        return "archive:research"
    if re.fullmatch(r"planning-artifacts/specs/spec-[a-z0-9-]+/[A-Za-z0-9._-]+\.md", rel):
        # bmad-spec output folders: SPEC.md (the Spec) + append-only .memlog.md
        # + companions. The memlog is the decision-of-record and SPEC.md re-derives
        # from it (never hand-patched), so no pin gating here.
        return "tracked:spec"
    if re.fullmatch(r"planning-artifacts/specs/spec-[a-z0-9_-]+\.md", rel):
        # FLAT spec files directly under specs/ — the rule above only matched spec
        # FOLDERS, so a flat one fell through to UNKNOWN and failed coverage. Two
        # real shapes live here: per-story specs (the durable Tier-2 home) and
        # standalone effort specs such as the 2026-07-26 code-audit remediation
        # record. Both are tracked, hand-authored, and not pin-gated. Character
        # class widened to `[a-z0-9_-]+` 2026-09-12 (mason 15.1 recovery landing,
        # same fleet-hygiene pass as the sibling rule below): a story-title slug
        # can carry an underscore verbatim when it names a real code symbol
        # (`spec-33-8-...-dispatch-max_parallel-key.md`,
        # `spec-34-4-...-station_state-sibling-has.md`) — the original hyphen-only
        # class rejected both and tripped `uncovered`.
        return "tracked:spec"
    if re.fullmatch(r"planning-artifacts/specs/spec-[a-z0-9_-]+\.memlog\.md", rel):
        # A flat spec's OWN `.memlog.md` sibling, filed beside it rather than
        # inside a `spec-<name>/` folder (Story 33.3, 2026-09-12 recovery pass):
        # `spec-33-3-....md` + `spec-33-3-....memlog.md` as flat siblings. The
        # folder-shaped rule above only matches a memlog living INSIDE a
        # `spec-<name>/` directory; this is the flat-file counterpart to it, same
        # as the flat-spec rule just above is the flat counterpart to the
        # folder-spec rule. Same append-only decision-of-record role, same
        # tracked/hand-authored/not-pin-gated treatment.
        return "tracked:spec"
    if rel.startswith("implementation-artifacts/retros/"):
        return "archive:retros"
    if rel.startswith("planning-artifacts/retros/"):
        # The TRACKED home for retrospectives, and where all seven other stations
        # already kept theirs. Added 2026-09-07 (marshal Story 32.3): marshal's four
        # epic retros lived in gitignored implementation-artifacts/, so they were
        # absent from every clone and one worktree teardown from the loss that cost
        # pyforge-warden 13 story specs. Promoting them surfaced the gap -- this
        # detector only ever scans pyforge-marshal, which was the one station with
        # no planning-artifacts/retros/ directory for the rule to have been needed.
        return "archive:retros"
    if rel == "implementation-artifacts/deferred-work.md":
        return "tracked:deferred"
    if re.fullmatch(r"planning-artifacts/rekey-\d{4}-\d{2}-\d{2}\.md", rel):
        # A fold PR's re-key map (doctor Story 25.3, spec-one-chain-per-station CAP-3(g)):
        # `old-key -> new-key` lines that sprint-ledger-sync --rekey and the ledger-regression /
        # story-status verdicts read so a renumbered `done` row moves as `done`. Dated in its
        # filename (AGENTS.md § Dates), hand-authored once per fold, never pin-gated. Found
        # 2026-09-16 on the marshal pilot (PR #1389): the first re-key map ever written reddened
        # bmad-drift `uncovered` because 25.3 shipped the readers but no classification rule.
        return "tracked:plan"
    if rel == "planning-artifacts/deferred-work-ledger.md":
        # The DURABLE twin of the Tier-3 ledger above, promoted 2026-07-29 because
        # bmad-loop's follow-up-review damping refiles into the gitignored one (see
        # scripts/deferred_work_check.py). Hand-authored and not pin-gated: entries
        # are dated in their own bodies, and the file is deliberately a copy whose
        # curation lags — a version pin would report drift on every skill bump for a
        # document that tracks stories, not the skill surface.
        return "tracked:deferred"
    if re.fullmatch(r"implementation-artifacts/sprint-status(-[a-z0-9-]+)?\.yaml", rel):
        # Tier-3 sprint feed (gitignored, local-only) — the program console's
        # dashboard-gen reads it; no pin gating.
        return "local:sprint-feed"
    if rel == "planning-artifacts/marshal-policy.toml":
        # Marshal's PROJECT-POLICY layer -- the middle tier of AD-16's
        # defaults -> project -> flags chain, added 2026-07-30. Tracked on
        # purpose: it is the governed SOURCE the gitignored, derived
        # `.bmad-loop/policy.toml` is rendered from (AD-12/AD-35), so a fresh
        # clone or a newly provisioned loop home can reproduce its harness
        # policy. Hand-authored and not pin-gated -- it carries a station's
        # verify command and gate posture, which track that project's own
        # surface rather than the skill's.
        return "tracked:marshal-policy"
    if rel == "planning-artifacts/fleet-drain-queue.yaml":
        # Marshal's OPTIONAL fleet-drain order-override / skip-policy file
        # (pyforge.marshal.core.dispatch_fleet.QUEUE_CONFIG_FILENAME), added
        # 2026-08-30 by the atlas workbook-retirement course correction. Tracked
        # on purpose: it is the one place a station's cross-story dependency
        # order is made explicit to `marshal factory drain`, which otherwise
        # walks the tracked ledger in story-key order. Hand-authored and not
        # pin-gated -- it tracks a station's backlog, not the skill surface.
        return "tracked:marshal-queue"
    if rel == "planning-artifacts/sprint-status-ledger.yaml":
        # The DURABLE twin of the Tier-3 sprint feed above, promoted 2026-07-30 for
        # the same reason as deferred-work-ledger.md: implementation-artifacts/ is
        # gitignored wholesale, so the only record that a story finished was
        # invisible to CI, which is why the console's deploy-time render had to
        # reconstruct DONE from commit subjects — and why it broke when squash
        # merging left a bmad-loop merge subject unreachable from main.
        # GENERATED by scripts/promote_sprint_status.py (`sprint-ledger-sync`) and
        # read by pyforge.doctor.sources.fleet_scan:apply_tracked_ledger; freshness is
        # enforced against the Tier-3 feed by scripts/dashboard_drift_check.py, not
        # by a version pin — it tracks stories, not the skill surface.
        return "tracked:sprint-ledger"
    if re.fullmatch(r"implementation-artifacts/spec-.*\.md", rel):
        return "tracked:spec"
    # --- the spike-report shape (Story 6.11, added 2026-08-11) ----------------
    # Same lesson a third time: on 2026-08-11 (PR #427, Marshal Story 7.6) a
    # design-spike's PASS/FAIL verdict landed at a project's `planning-artifacts/`
    # root (`spike-0-copier-api-fit-report.md`) and fell through to `UNKNOWN`,
    # tripping `uncovered`. Generalized over the spike index and the descriptive
    # slug -- not hard-coded to `spike-0` -- so a future `spike-1`/`spike-2`
    # report following the same convention stays covered without another
    # incident. A frozen, dated record of a one-off design decision, so it
    # archives rather than tracks (no pin gating).
    if re.fullmatch(r"planning-artifacts/spike-\d+-[a-z0-9-]+-report\.md", rel):
        return "archive:spike-report"
    # Readiness assessments at the planning-artifacts root: the fourth
    # instance of the spike-report lesson. Marshal Story 3.13 (2026-08-12)
    # left `parallel-fan-out-readiness-assessment.md` — a frozen, dated,
    # read-only record explicitly disclaiming certification — which fell
    # through to UNKNOWN and tripped `uncovered` (caught 2026-08-21 by the
    # meta-test gate during the BMAD 6.11.0 upgrade). Generalized over the
    # descriptive slug so a future assessment following the same convention
    # stays covered. A dated one-off record, so it archives (no pin gating).
    if re.fullmatch(r"planning-artifacts/[a-z0-9-]+-readiness-assessment\.md", rel):
        return "archive:readiness-assessment"
    # The sweep-verdicts shape (2026-09-05): the fifth instance of the spike-report
    # lesson. `scripts/worktree_sweep.py --format json` is the repeatable worktree-
    # hygiene tool (settled in the 2026-09-05 shutdown sweep; marshal-native home
    # `marshal retire`, tracked ledger DW-HYGIENE-2026-09-05-1); the operator saves
    # its per-worktree verdict table as a dated JSON record at marshal's
    # implementation-artifacts root (`worktree-verdicts-<date>.json`), and the first
    # such file fell through to UNKNOWN and tripped `uncovered`. Generalized over the
    # date so every later sweep's record stays covered. Tier-3, gitignored,
    # machine-written, never hand-edited, never pin-gated.
    if re.fullmatch(r"implementation-artifacts/worktree-verdicts-\d{4}-\d{2}-\d{2}\.json", rel):
        return "local:sweep-verdicts"
    # The benchmark-artifact shape (Story 28.31, 2026-09-12 recovery pass): the
    # sixth instance of the spike-report lesson. Marshal's structure-graph
    # dispatch benchmark landed its measured comparison as a committed JSON
    # record at `planning-artifacts/benchmarks/<story-slug>.json`, a sibling
    # convention to `reviews/` for one-off measurement results, and fell
    # through to UNKNOWN. Frozen, dated-by-story, never re-derived, so it
    # archives (no pin gating) like the other one-off record shapes above.
    if re.fullmatch(r"planning-artifacts/benchmarks/[a-z0-9-]+\.json", rel):
        return "archive:benchmark"
    return "UNKNOWN"


def check_coverage(target: Path) -> list[Finding]:
    """Walk the whole project; HARD-fail any file no rule classifies -- so
    coverage can't lapse. Walks through ``_walk``, not ``Path.rglob``: the
    latter swallows ``OSError`` mid-traversal and simply yields nothing for
    an unreadable directory, which this check would then read as full
    coverage. The story's Design Notes left that question to the review
    pass, which reproduced it (see ``_walk``) and closed it here."""
    findings: list[Finding] = []
    proj = _proj(target)
    if not _is_dir(proj):
        return findings
    for path in sorted(_walk(proj)):
        if not _is_file(path):
            continue
        cls = classify(path, target)
        if cls == "ignored":
            continue
        if cls == "UNKNOWN" and path.suffix not in STRAY_SUFFIXES:
            findings.append(
                _finding(
                    HARD, "uncovered", _rel(path, target), "not covered by drift-check — add a classification rule"
                )
            )
    return findings


def check_tier_alignment(target: Path) -> list[Finding]:
    """Enforce the BMAD-method tier model: Tier-1 intake specs live in
    ``docs/specs/`` (neutral, tracked), Tier-3 execution output lives in
    ``implementation-artifacts/`` (gitignored, local-only). A git-tracked
    file under ``implementation-artifacts/`` is misfiled.

    Unlike the original's own ``check_tier_alignment()``, a git failure while
    listing tracked implementation-artifact files degrades to an honest
    ``bmad-drift-unevaluable`` WARN for that half of the check, rather than
    silently reporting a clean "nothing tracked" -- see this module's own
    docstring. The non-git docs/specs half still runs regardless."""
    out: list[Finding] = []
    tracked = _git_tracked(target, IMPL_REL)
    if tracked is None:
        out.append(
            _unevaluable(
                "check_tier_alignment",
                f"git ls-files -- {IMPL_REL} failed; git may be unavailable or {target} is not a repository",
                target,
            )
        )
    else:
        for f in tracked:
            name = f.rsplit("/", 1)[-1]
            remedy = (
                "intake spec -> git mv to docs/specs/"
                if name.startswith("spec-")
                else "Tier-3 output -> keep local (git rm --cached)"
            )
            out.append(
                _finding(
                    HARD,
                    "tracked-impl-artifact",
                    f,
                    f"implementation-artifacts is gitignored/local-only; this file is git-tracked ({remedy})",
                )
            )
    docs_specs = _docs_specs(target)
    if _is_dir(docs_specs):
        for p in _listdir(docs_specs):
            if _is_file(p) and p.suffix != ".md":
                out.append(
                    _finding(
                        DRIFT,
                        "docs-specs-nonmd",
                        f"docs/specs/{p.name}",
                        "docs/specs holds BMAD intake specs (markdown) — non-.md is misfiled",
                    )
                )
    return out


def check_spec_indexed(target: Path) -> list[Finding]:
    """Every Tier-1 intake spec must be referenced in CLAUDE.md's Project
    Documentation Reference -- verbatim from the original."""
    docs_specs = _docs_specs(target)
    if not _is_dir(docs_specs):
        return []
    claude = _read(target / "CLAUDE.md")
    return [
        _finding(
            DRIFT,
            "spec-unindexed",
            f"docs/specs/{p.name}",
            "not referenced in CLAUDE.md Project Documentation Reference",
        )
        for p in _listdir_match(docs_specs, "*.md")
        if p.name not in claude
    ]


def _roster(target: Path) -> dict:
    """The Guild's own vocabulary, read fresh from
    ``docs/governance/guild-roster.json`` -- Part 1 of this story (merged
    ahead of this branch) consolidated ``stations``/``guild_dreams``/
    ``dream_statuses``/``dream_types`` into this one file; this module reads
    it exactly as the original does, never restating the values. Read per
    call (not cached at import time) because ``target`` is a runtime
    parameter -- see this module's own docstring."""
    return json.loads((target / "docs" / "governance" / "guild-roster.json").read_text(encoding="utf-8"))


def check_dream_vocab(target: Path) -> list[Finding]:
    """Dream ``status:``/``type:`` must use the canonical vocabulary --
    verbatim from the original's own ``check_dream_vocab()``."""
    out: list[Finding] = []
    dreams_dir = target / "docs" / "dreams"
    if not _is_dir(dreams_dir):
        return out
    roster = _roster(target)
    dream_statuses = tuple(roster["dream_statuses"])
    dream_types = tuple(roster["dream_types"])
    for f in _listdir_match(dreams_dir, "*.md"):
        if f.name == "README.md":
            continue
        text = _read_item(f, "check_dream_vocab", target, out)
        if text is None:
            continue
        # A trailing `# comment` after the value is ordinary YAML (26 Dreams carry
        # one -- "absorbed into X on <date>" style notes); it must not read as
        # "no status:" (2026-09-05).
        m = re.search(r"^status:\s*(\S+)\s*(?:#.*)?$", text, re.M)
        if not m:
            out.append(_finding(DRIFT, "dream-vocab", _rel(f, target), "no status: in frontmatter"))
        elif m.group(1) not in dream_statuses:
            out.append(
                _finding(
                    DRIFT,
                    "dream-vocab",
                    _rel(f, target),
                    f"status {m.group(1)!r} is not one of {'/'.join(dream_statuses)}",
                )
            )
        m = re.search(r"^type:\s*(\S+)\s*(?:#.*)?$", text, re.M)
        if m and m.group(1) not in dream_types:
            out.append(
                _finding(
                    DRIFT, "dream-vocab", _rel(f, target), f"type {m.group(1)!r} is not one of {'/'.join(dream_types)}"
                )
            )
    return out


def check_dream_owners(target: Path) -> list[Finding]:
    """Every Dream must name the station accountable for carrying it to code
    -- verbatim from the original's own ``check_dream_owners()``."""
    out: list[Finding] = []
    dreams_dir = target / "docs" / "dreams"
    if not _is_dir(dreams_dir):
        return out
    roster = _roster(target)
    stations = tuple(roster["stations"])
    guild_dreams = tuple(roster["guild_dreams"])
    for f in _listdir_match(dreams_dir, "*.md"):
        if f.name == "README.md":
            continue
        text = _read_item(f, "check_dream_owners", target, out)
        if text is None:
            continue
        m = re.search(r"^owner:\s*(\S+)\s*$", text, re.M)
        owner = m.group(1) if m else ""
        if not owner:
            out.append(
                _finding(
                    DRIFT,
                    "dream-unowned",
                    _rel(f, target),
                    f"no owner: in frontmatter — name one of {', '.join(stations)}",
                )
            )
        elif owner == "guild" and f.stem not in guild_dreams:
            out.append(
                _finding(
                    DRIFT,
                    "dream-unowned",
                    _rel(f, target),
                    f"owner 'guild' is reserved for {'/'.join(guild_dreams)} — assign a station",
                )
            )
        elif owner not in stations and owner != "guild":
            out.append(
                _finding(DRIFT, "dream-unowned", _rel(f, target), f"owner {owner!r} is not one of the eight Smiths")
            )
    return out


def _load_pixi_env_matrix_module(target: Path):
    script = target / "scripts" / "pixi_env_matrix.py"
    mod_name = "pixi_env_matrix_doctor"
    spec = importlib.util.spec_from_file_location(mod_name, script)
    if spec is None or spec.loader is None:
        raise OSError(f"cannot load {script}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def check_pixi_env_matrix(target: Path) -> list[Finding]:
    """Dream measured matrix must track ``pixi.lock`` (Story 43.5 / canopy AD-23)."""
    out: list[Finding] = []
    dream = target / "docs" / "dreams" / "pyforge-unifying-strategy.md"
    lock = target / "pixi.lock"
    if not dream.is_file() or not lock.is_file():
        return out
    try:
        mod = _load_pixi_env_matrix_module(target)
        if mod.matrix_is_stale(dream, lock):
            out.append(
                _finding(
                    DRIFT,
                    "pixi-env-matrix-stale",
                    _rel(dream, target),
                    "measured Pixi environment matrix is older than pixi.lock — "
                    "run `python scripts/pixi_env_matrix.py --update --dream "
                    "docs/dreams/pyforge-unifying-strategy.md`",
                )
            )
    except OSError as exc:
        out.append(_unevaluable("check_pixi_env_matrix", str(exc), target))
    return out


# ------------------------------------------------------------------- gather
#: The 13 ported checks, by NAME -- looked up in this module's own globals at
#: call time inside ``_gather`` (never captured into a tuple of function
#: objects at import time), so a test can ``monkeypatch.setattr(factory,
#: "check_pins", stub)`` and have ``_gather`` observe the stub. Order matches
#: the original's own ``run_checks()`` concatenation order exactly --
#: ``check_coverage`` last (the original computes it first but concatenates
#: it last), ``check_dream_owners`` before ``check_dream_vocab``. Findings
#: are unordered, so this is a fidelity choice, not a behavioral one.
_CHECK_NAMES: tuple[str, ...] = (
    "check_pins",
    "check_archive_hygiene",
    "check_spec_status",
    "check_deferred_work",
    "check_counts",
    "check_stale_rules",
    "check_phase_lists",
    "check_baseline",
    "check_tier_alignment",
    "check_spec_indexed",
    "check_dream_owners",
    "check_dream_vocab",
    "check_pixi_env_matrix",
    "check_coverage",
)


def gather(target: Path) -> tuple[Finding, ...]:
    """Judge whether the tracked ``pyforge-marshal`` project docs are in
    sync with the live factory -- the library form of
    ``scripts/bmad_drift_check.py``'s own ``run_checks()``, minus the
    print/exit CLI surface (and minus ``do_fix()``/``--fix``/
    ``--write-baseline``, Doctor sources being read-only gathers)."""
    return degrade_on_exception(Source.BMAD_DRIFT, "bmad-drift", lambda: _gather(target))


def _gather(target: Path) -> tuple[Finding, ...]:
    proj = _proj(target)
    if not _is_dir(proj):
        return (
            Finding(
                source=Source.BMAD_DRIFT,
                check="bmad-drift-unevaluable",
                status=DoctorStatus.WARN,
                message=(f"no {PROJ_REL}/ under {target} — the BMAD project drift check cannot be evaluated here"),
                evidence={"check": "bmad-drift", "target": str(target)},
            ),
        )

    findings: list[Finding] = []
    for name in _CHECK_NAMES:
        try:
            fn = globals()[name]
            findings.extend(fn(target))
        except Exception as exc:  # noqa: BLE001 -- the per-check isolation
            # boundary itself: one check's malformed input -- or, degenerately,
            # a future edit desyncing _CHECK_NAMES from an actual function
            # name (KeyError) -- must not discard the other checks' already-
            # computed findings. The lookup lives INSIDE this try on purpose:
            # review pass (Story 6.8) found it outside, where a KeyError would
            # have escaped this loop entirely and been caught only by
            # gather()'s own outer degrade_on_exception, discarding every
            # finding already accumulated from checks that ran successfully
            # earlier in this same pass.
            findings.append(_unevaluable(name, f"{exc.__class__.__name__}: {exc}", target))

    if not findings:
        return (
            Finding(
                source=Source.BMAD_DRIFT,
                check="bmad-drift",
                status=DoctorStatus.OK,
                message=(f"all tracked BMAD project docs under {PROJ_REL}/ are in sync with the live factory"),
                evidence={"target": str(target)},
            ),
        )
    return tuple(findings)
