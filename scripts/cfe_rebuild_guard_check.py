#!/usr/bin/env python3
"""cfe-rebuild-guard-check — guard the CFE-rebuild campaign (Epic 6,
pyforge-mason) against its two known failure modes: silent divergence
between the live skill and a parallel replacement, and an endgame that
never arrives (the fate of the ~29,000-line `pyforge-atlas` rebuild,
stranded behind legacy code for months).

Reads `campaign-state.yaml` (the real, tracked instance at
`_bmad-output/projects/pyforge-mason/planning-artifacts/specs/
spec-conda-forge-expert-rebuild/campaign-state.yaml`), every brief a slice's
`brief_path` names, and -- only when at least one slice carries a
`brief_path` -- git history from `--since` to HEAD. With no `brief_path` on
any slice (true since Story 15.1 closed the campaign) no clause needs a
retro, so no history is walked at all (`retros_scanned: null` in `--json`).
Status strings are matched stripped and case-folded. Enforces four clauses,
clause (b) in two halves ((b) against git history, (b') against the brief):

    (a) stale-equivalence          any slice whose `status` is `parallel`,
                                    `audited`, or `cut-over` must have
                                    `equivalence: "green"`. The detector
                                    never computes staleness itself from
                                    timestamps -- it trusts the recorded
                                    enum value (writing/refreshing it is the
                                    equivalence harness's job, out of this
                                    story's scope).

    (b) unmirrored-retro           a "landed CFE Rule-2 retro" = a commit in
                                    `<since>..HEAD` (default: the Story-6.1
                                    landing merge, PR #570; overridable via
                                    `--since` so tests can bound a scratch
                                    repo) whose diff touches the CFE surface
                                    (.claude/skills/conda-forge-expert/**,
                                    .claude/scripts/conda-forge-expert/**,
                                    .claude/tools/conda_forge_server.py)
                                    AND touches
                                    .claude/skills/conda-forge-expert/
                                    CHANGELOG.md (status A or M) in the same
                                    commit. No commit-subject pattern is
                                    ever part of the test -- that was the
                                    defect in a prior, reverted attempt,
                                    which wrongly gated on a literal
                                    `retro:` subject prefix that no real CFE
                                    retro commit in this repo's history
                                    actually uses. For every slice with a
                                    non-null `brief_path`, if the newest
                                    qualifying retro SHA in range is not
                                    named by that slice's
                                    `brief_mirrored_through` (read as a SHA
                                    candidate from YAML and compared by the
                                    shared prefix rule below), that is a
                                    finding. Slices with `brief_path: null`
                                    are never checked -- no brief exists yet
                                    for anything to go stale.

    (b') brief-defect              the brief a set `brief_path` names is
                                    opened: a non-string path, a missing or
                                    empty file, invalid YAML, a non-mapping,
                                    a required skill-brief key missing or
                                    null/empty, or a scope without a `type`
                                    is a finding; so is any qualifying retro
                                    at or older than `brief_mirrored_through`
                                    (same SHA reading as clause (b)) that no
                                    `retro-mirror` amendment names in a SHA
                                    field (the full SHA or a prefix of at
                                    least 10 hex characters as the field's
                                    whole value -- never a substring of free
                                    text such as `reason`). Two SHA candidates
                                    name the same commit when, stripped and
                                    lower-cased, both are hex tokens of 10 to
                                    40 characters and one is a prefix of the
                                    other.

    (c) legacy-caller-at-endgame   only evaluated when
                                    `campaign.endgame_declared: true`; any
                                    entry in `campaign.callers` with
                                    `resolves_to: "legacy"` is a finding.
                                    While `endgame_declared` is false (true
                                    throughout Epic 6), this clause is
                                    vacuously clean -- the real
                                    caller-resolution population is future
                                    cutover work, not this story's.

    (d) gate-bypassed              a `brief_path` set on any slice whose
                                    `order` is >= 2 while
                                    `campaign.re_scope_gate.pre_conditions`
                                    does not record all four named
                                    pre-conditions "closed" or "waived" is a
                                    finding. Machine enforcement for CAP-4's
                                    re-scope gate (Story 6.4's GATHERED GAPS
                                    #5: previously honored by session/human
                                    discipline alone -- nothing read
                                    `re_scope_gate`). Reads ONLY the
                                    structured `pre_conditions` block, never
                                    `re_scope_gate.note`'s free prose (the
                                    same anti-pattern the `decision` field was
                                    added to avoid). Slice 1 (order 1) is
                                    exempt -- it is the measured pilot the
                                    gate's own cost accounting is based on.

Never gates clause (b) on any commit-subject-line pattern, or clause (d) on
`re_scope_gate.note`'s free-text prose via substring matching. Never confuses
its own clause-(b) scope with `mason_cfe_surface_check.py`'s narrower,
self-scoped `retro:`-subject sanctioned-exception check (FR-45/Story 5.5) --
that check stays untouched. Never implements real caller-introspection for
clause (c) or a real equivalence-harness runner for clause (a) -- both are
declared-state readers only.

Exit codes: 0 clean, 1 findings, 2 could not run (bad/missing
campaign-state.yaml, or the history walk's `git log` failed). `--json` machine output
supported.
"""
from __future__ import annotations

# Registry declaration — see scripts/detectors.py. `repo`: every input
# (campaign-state.yaml, git log) is tracked/committed state — nothing
# runtime-only, so this runs identically in CI and locally.
DETECTOR = {"scope": "repo"}

import argparse
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CAMPAIGN_STATE_PATH = (
    ROOT
    / "_bmad-output/projects/pyforge-mason/planning-artifacts/specs/"
      "spec-conda-forge-expert-rebuild/campaign-state.yaml"
)

# Story-6.1 landing merge (PR #570) — the default lower bound for clause
# (b)'s retro scan. Overridable via --since so tests can bound a scratch repo.
DEFAULT_SINCE = "806cb630469688d596cac00a53573f01f39386e2"

CFE_CHANGELOG = ".claude/skills/conda-forge-expert/CHANGELOG.md"
CFE_SURFACE_PREFIXES = (
    ".claude/skills/conda-forge-expert/",
    ".claude/scripts/conda-forge-expert/",
)
CFE_SURFACE_FILES = frozenset({".claude/tools/conda_forge_server.py"})

# Clause (b'): a retro-mirror amendment names a retro SHA when one of its
# fields holds the full SHA, or a prefix of at least this many hex characters,
# as the field's whole value (or as one item of a list value).
MIN_SHA_PREFIX = 10

# Clause (a): slice statuses that require equivalence: "green".
EQUIVALENCE_GATED_STATUSES = frozenset({"parallel", "audited", "cut-over"})
EQUIVALENCE_GATED_FOLDS = frozenset(s.casefold() for s in EQUIVALENCE_GATED_STATUSES)
# Clause (b'): the top-level keys `skill-brief.v1.json` requires; each must be
# present AND carry a value (null or an empty string/list/mapping is hollow).
_BRIEF_REQUIRED_TOP_KEYS = (
    "name",
    "version",
    "source_repo",
    "language",
    "description",
    "forge_tier",
    "created",
    "created_by",
    "scope",
)

# Clause (d): slices at this order or higher are gated by the re-scope gate's
# pre-conditions before their `brief_path` may be set (CAP-4's "second slice
# onward" gate). Slice 1 (order 1) is exempt -- it is the measured pilot the
# gate's own cost accounting is based on.
RE_SCOPE_GATED_ORDER_FLOOR = 2

# Clause (d): the four named pre-conditions (Story 6.4's re-scope gate note)
# `campaign.re_scope_gate.pre_conditions` must record. Keys, not prose --
# read structurally, never via substring-matching `re_scope_gate.note`.
RE_SCOPE_GATE_PRE_CONDITION_KEYS = (
    "a_ci_enforcement",
    "b_skf_setup",
    "c_cross_slice_rederivation",
    "d_ownership_decision",
)

# Clause (d): a pre-condition entry's `status` value that counts as satisfied
# (closed by real evidence, or explicitly waived by a human).
RE_SCOPE_GATE_SATISFIED_STATUSES = frozenset({"closed", "waived"})

# Case-/whitespace-insensitive view of RE_SCOPE_GATE_SATISFIED_STATUSES.
_RE_SCOPE_GATE_SATISFIED_FOLDS = frozenset(
    status.casefold() for status in RE_SCOPE_GATE_SATISFIED_STATUSES
)


def _run(root: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(["git", *args], cwd=root, capture_output=True,
                               text=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None


def git(root: pathlib.Path, *args: str) -> str:
    """git stdout, or "" on any failure — matches every sibling detector's
    `git()` wrapper (e.g. mason_cfe_surface_check.py): a failed per-commit
    lookup and a genuinely empty one are handled identically."""
    proc = _run(root, *args)
    return proc.stdout.strip() if proc and proc.returncode == 0 else ""


def is_cfe_path(path: str) -> bool:
    return path in CFE_SURFACE_FILES or any(path.startswith(p) for p in CFE_SURFACE_PREFIXES)


def _construct_yaml_int(loader: object, node: object) -> int:
    from yaml.constructor import SafeConstructor

    scalar = node.value  # type: ignore[union-attr]
    value = SafeConstructor.construct_yaml_int(loader, node)  # type: ignore[arg-type]
    if isinstance(value, int) and not isinstance(value, bool):
        int_scalars = getattr(loader, "int_scalars", None)
        if isinstance(int_scalars, dict):
            int_scalars[value] = scalar
    return value


def _yaml_load(text: str) -> object:
    import io

    import yaml

    class _ShaPreservingLoader(yaml.SafeLoader):
        int_scalars: dict[int, str]

        def __init__(self, stream: object) -> None:
            super().__init__(stream)
            self.int_scalars = {}

    _ShaPreservingLoader.add_constructor(
        "tag:yaml.org,2002:int",
        _construct_yaml_int,
    )
    loader = _ShaPreservingLoader(io.StringIO(text))
    data = loader.get_single_data()
    if isinstance(data, dict):
        data["__yaml_int_scalars__"] = loader.int_scalars
    return data


def _yaml_int_scalars(root: object) -> dict[int, str]:
    if isinstance(root, dict):
        raw = root.get("__yaml_int_scalars__")
        if isinstance(raw, dict):
            return raw
    return {}


def _strip_yaml_loader_metadata(root: object) -> None:
    if isinstance(root, dict):
        root.pop("__yaml_int_scalars__", None)


def campaign_state(path: pathlib.Path) -> dict | None:
    """Parsed campaign-state.yaml, or None if the file is missing, unreadable,
    or not valid YAML mapping at its top level — the exit-2 "could not run"
    case."""
    try:
        import yaml  # noqa: F401 — presence check only
    except ModuleNotFoundError:
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data = _yaml_load(text)
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None


def _parse_name_status_lines(lines: list[str]) -> list[tuple[str, str]]:
    """Parse `git diff --name-status`-style lines into (status, path) pairs.
    A rename/copy line has THREE tab-separated fields (status, old path, new
    path) rather than two -- the current path is always the last field,
    whichever shape the line has. Neither call site below passes `-M`/`-C`,
    so a 3-field line cannot occur through this module today; this still
    handles it correctly rather than relying on that staying true."""
    return [(ln.split("\t")[0], ln.split("\t")[-1]) for ln in lines]


def diff_name_status(root: pathlib.Path, sha: str) -> list[tuple[str, str]]:
    """(status, path) pairs for `sha`'s diff. Falls back to the first-parent
    diff when plain `diff-tree` returns empty (a real multi-parent merge, for
    which plain `diff-tree` prints nothing) so a conflict-resolving merge is
    never silently read as "touches nothing" — same pattern as
    mason_cfe_surface_check.py's own helper."""
    for args in (
        ("diff-tree", "--no-commit-id", "--name-status", "-r", "--root", sha),
        ("diff", "--name-status", f"{sha}^1", sha),
    ):
        lines = [ln for ln in git(root, *args).splitlines() if ln.strip()]
        if lines:
            return _parse_name_status_lines(lines)
    return []


def _slice_ref(sl: dict) -> str:
    raw = sl.get("id")
    if raw is None:
        return "<unknown-slice>"
    if isinstance(raw, str):
        return raw.strip() if raw.strip() else "<unknown-slice>"
    return str(raw)


def _precondition_status_satisfied(entry: object) -> bool:
    if not isinstance(entry, dict):
        return False
    status = entry.get("status")
    if not isinstance(status, str):
        return False
    return status.strip().casefold() in _RE_SCOPE_GATE_SATISFIED_FOLDS


def _is_hex_sha_token(value: str) -> bool:
    return (MIN_SHA_PREFIX <= len(value) <= 40
            and all(ch in "0123456789abcdef" for ch in value))


def _sha_candidate_from_yaml_value(value: object) -> str | None:
    """A YAML field value read as a SHA candidate, or None if it is not one."""
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    if isinstance(value, int):
        if isinstance(value, _YamlInt):
            return value.yaml_scalar.strip()
        return str(value)
    return None


def _sha_matches(token: str, sha: str) -> bool:
    """Two SHA candidates name the same commit when both are hex tokens of
    10–40 characters and one is a prefix of the other (case-insensitive)."""
    token = token.strip().lower()
    sha = sha.strip().lower()
    if not _is_hex_sha_token(token) or not _is_hex_sha_token(sha):
        return False
    return token.startswith(sha) or sha.startswith(token)


def _amendment_sha_tokens(amend: dict) -> list[str]:
    """Every SHA candidate an amendment carries as a whole field value, or as
    one item of a list value -- the only places a SHA field can live. Free
    text (`reason: "mirrored 565ef7d194 into ..."`) is not a SHA candidate,
    so a SHA quoted inside prose never matches."""
    tokens: list[str] = []
    for value in amend.values():
        if isinstance(value, list):
            for item in value:
                cand = _sha_candidate_from_yaml_value(item)
                if cand is not None:
                    tokens.append(cand)
        else:
            cand = _sha_candidate_from_yaml_value(value)
            if cand is not None:
                tokens.append(cand)
    return tokens


def _brief_covers_retro_sha(brief: dict, sha: str) -> bool:
    scope = brief.get("scope")
    if not isinstance(scope, dict):
        return False
    amendments = scope.get("amendments")
    if not isinstance(amendments, list):
        return False
    for amend in amendments:
        if not isinstance(amend, dict) or amend.get("action") != "retro-mirror":
            continue
        if any(_sha_matches(token, sha) for token in _amendment_sha_tokens(amend)):
            return True
    return False


def _required_mirror_shas(mirrored: str, retros: list[str]) -> list[str]:
    """The retro SHAs a brief mirrored through `mirrored` must name: every
    qualifying retro at or older than it (`retros` is newest first). When
    `mirrored` is not a qualifying retro in range (older than `--since`, or a
    retro that no longer qualifies), the pointer itself is still owed."""
    for idx, sha in enumerate(retros):
        if _sha_matches(mirrored, sha):
            return retros[idx:]
    return [mirrored]


def _is_blank(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return not value
    return False


def _brief_defect(slice_id: str, ref: str, detail: str, remedy: str) -> dict:
    return {
        "kind": "brief-defect",
        "ref": slice_id,
        "refs": [slice_id, ref],
        "detail": f"slice '{slice_id}': {detail}",
        "remedy": remedy,
    }


def _brief_defect_findings(root: pathlib.Path, slices: list, retros: list[str]) -> list[dict]:
    """Clause (b'): open each brief a slice's `brief_path` names and check it
    is a real skill brief that mirrors every qualifying retro up to its
    `brief_mirrored_through` (module docstring)."""
    findings: list[dict] = []
    for sl in slices:
        if not isinstance(sl, dict):
            continue
        brief_path = sl.get("brief_path")
        if not brief_path:
            continue
        slice_id = _slice_ref(sl)
        if not isinstance(brief_path, str):
            findings.append(_brief_defect(
                slice_id, repr(brief_path),
                f"brief_path {brief_path!r} is not a path string",
                "set brief_path to the brief's repo-relative path, or null until one exists"))
            continue
        abs_path = root / brief_path
        if not abs_path.is_file() or abs_path.stat().st_size == 0:
            findings.append(_brief_defect(
                slice_id, brief_path,
                f"brief_path {brief_path!r} is missing or empty",
                "restore the slice skill-brief.yaml or clear brief_path until one exists"))
            continue
        try:
            import yaml
        except ModuleNotFoundError:
            continue
        try:
            brief = _yaml_load(abs_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            findings.append(_brief_defect(
                slice_id, brief_path,
                f"brief_path {brief_path!r} is not valid YAML",
                "repair the slice skill-brief.yaml or clear brief_path until one exists"))
            continue
        if not isinstance(brief, dict):
            findings.append(_brief_defect(
                slice_id, brief_path,
                f"brief_path {brief_path!r} is hollow (not a mapping)",
                "restore a non-empty skill-brief.yaml or clear brief_path until one exists"))
            continue
        hollow_keys = [k for k in _BRIEF_REQUIRED_TOP_KEYS if _is_blank(brief.get(k))]
        if hollow_keys:
            findings.append(_brief_defect(
                slice_id, brief_path,
                f"brief at {brief_path!r} is missing required skill-brief keys "
                f"(absent, null or empty): {hollow_keys!r}",
                "restore a complete skill-brief.yaml or clear brief_path until one exists"))
            continue
        scope = brief.get("scope")
        if not isinstance(scope, dict) or _is_blank(scope.get("type")):
            findings.append(_brief_defect(
                slice_id, brief_path,
                f"brief at {brief_path!r} has a hollow or missing scope",
                "restore a complete skill-brief scope block or clear brief_path until one exists"))
            continue
        mirrored = _sha_candidate_from_yaml_value(sl.get("brief_mirrored_through"))
        if mirrored is None:
            continue
        missing = [sha for sha in _required_mirror_shas(mirrored, retros)
                   if not _brief_covers_retro_sha(brief, sha)]
        if missing:
            short = [sha[:MIN_SHA_PREFIX] for sha in missing]
            findings.append({
                "kind": "brief-defect",
                "ref": slice_id,
                "refs": [slice_id, *short],
                "detail": f"slice '{slice_id}': brief at {brief_path!r} has no retro-mirror "
                          f"amendment naming {', '.join(short)} (each qualifying retro at or "
                          f"older than brief_mirrored_through must be named in a SHA field)",
                "remedy": "mirror each retro into the brief as a retro-mirror amendment whose "
                          "SHA field holds the retro's SHA (or a >=10-char prefix)",
            })
    return findings


def any_slice_has_brief_path(state: dict) -> bool:
    slices = state.get("slices")
    if not isinstance(slices, list):
        return False
    return any(isinstance(sl, dict) and sl.get("brief_path") for sl in slices)


def retro_commits_since(root: pathlib.Path, since: str) -> list[str] | None:
    """SHAs (newest first) in `since..HEAD` that qualify as a landed CFE
    Rule-2 retro: diff touches the CFE surface AND touches CFE_CHANGELOG with
    status A or M in the same commit. None if `git log` itself could not run
    (e.g. `since` unknown to this repo, or `root` is not a git repository) —
    the exit-2 case.

    Merge commits never qualify (``--no-merges``). A merge restates the churn
    of the commits it merged in, so counting it made the newest "retro" a SHA
    nobody authored: every CFE retro PR went red on `main` the moment it merged
    (the merge became newer than the pointer, forcing a post-merge re-point —
    PR #1009 → 9ec3606b79), and on the `pull_request` event GitHub checks out a
    synthetic `refs/pull/N/merge` commit, so a PR carrying a retro could never
    match at all (run 33912193119, 2026-09-04). Squash merges are disabled in
    this repo, so the authored retro commit is always in the range."""
    proc = _run(root, "log", "--no-merges", "--format=%H", "--topo-order", f"{since}..HEAD")
    if proc is None or proc.returncode != 0:
        return None
    shas = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    retros: list[str] = []
    for sha in shas:
        status_lines = diff_name_status(root, sha)
        files = [path for _status, path in status_lines]
        if not any(is_cfe_path(f) for f in files):
            continue
        changelog_status = next(
            (status[:1] for status, path in status_lines if path == CFE_CHANGELOG), None)
        if changelog_status in ("A", "M"):
            retros.append(sha)
    return retros


def scan(state: dict, retros: list[str], *, root: pathlib.Path) -> list[dict]:
    findings: list[dict] = []
    slices = state.get("slices")
    slices = slices if isinstance(slices, list) else []
    newest_retro = retros[0] if retros else None

    findings.extend(_brief_defect_findings(root, slices, retros))

    # Clause (a): stale-equivalence.
    for sl in slices:
        if not isinstance(sl, dict):
            continue
        slice_id = _slice_ref(sl)
        status = sl.get("status")
        if not isinstance(status, str):
            continue
        if status.strip().casefold() not in EQUIVALENCE_GATED_FOLDS:
            continue
        equivalence = sl.get("equivalence")
        if equivalence == "green":
            continue
        findings.append({
            "kind": "stale-equivalence",
            "ref": slice_id,
            "refs": [slice_id],
            "detail": f"slice '{slice_id}' has status={status!r} but "
                      f"equivalence={equivalence!r} (must be 'green')",
            "remedy": "re-run the equivalence harness for this slice and "
                      "record a fresh 'green' result before it may stay "
                      "parallel/audited/cut-over",
        })

    # Clause (b): unmirrored-retro. Only meaningful when at least one
    # qualifying retro landed in range -- otherwise there is nothing new for
    # any brief to be behind.
    if newest_retro is not None:
        for sl in slices:
            if not isinstance(sl, dict):
                continue
            brief_path = sl.get("brief_path")
            if not brief_path:
                continue
            slice_id = _slice_ref(sl)
            mirrored_raw = sl.get("brief_mirrored_through")
            mirrored_through = _sha_candidate_from_yaml_value(mirrored_raw)
            if (mirrored_through is not None
                    and _sha_matches(mirrored_through, newest_retro)):
                continue
            accepted = newest_retro[:MIN_SHA_PREFIX]
            findings.append({
                "kind": "unmirrored-retro",
                "ref": slice_id,
                "refs": [slice_id, newest_retro[:10]],
                "detail": f"slice '{slice_id}': newest qualifying CFE retro "
                          f"{newest_retro[:10]} (CFE surface + CHANGELOG.md "
                          f"touched) differs from brief_mirrored_through="
                          f"{mirrored_raw!r} — the slice's brief may be stale",
                "remedy": "mirror the retro's CFE-surface delta into the "
                          "slice's brief, then set brief_mirrored_through to "
                          f"{accepted!r} (a >=10-character hex prefix the "
                          "check accepts)",
            })

    # Clause (c): legacy-caller-at-endgame. Only evaluated once the campaign
    # has declared its endgame.
    campaign = state.get("campaign")
    campaign = campaign if isinstance(campaign, dict) else {}
    if campaign.get("endgame_declared") is True:
        for idx, caller in enumerate(campaign.get("callers") or []):
            if not isinstance(caller, dict) or caller.get("resolves_to") != "legacy":
                continue
            ref = caller.get("name") or caller.get("id") or f"caller[{idx}]"
            findings.append({
                "kind": "legacy-caller-at-endgame",
                "ref": ref,
                "refs": [ref],
                "detail": f"caller {ref!r} still resolves_to 'legacy' while "
                          "campaign.endgame_declared is true",
                "remedy": "flip this caller to the replacement before the "
                          "endgame is declared complete",
            })

    # Clause (d): gate-bypassed. A `brief_path` set on any slice of order >= 2
    # while campaign.re_scope_gate.pre_conditions does not record all four
    # named pre-conditions "closed" or "waived" is a finding -- machine
    # enforcement for CAP-4's re-scope gate (Story 6.4's GATHERED GAPS #5).
    re_scope_gate = campaign.get("re_scope_gate")
    re_scope_gate = re_scope_gate if isinstance(re_scope_gate, dict) else {}
    pre_conditions = re_scope_gate.get("pre_conditions")
    pre_conditions = pre_conditions if isinstance(pre_conditions, dict) else {}

    for sl in slices:
        if not isinstance(sl, dict):
            continue
        order = sl.get("order")
        if not isinstance(order, int) or order < RE_SCOPE_GATED_ORDER_FLOOR:
            continue
        brief_path = sl.get("brief_path")
        # Clause (d) applies only to a slice that sets brief_path. Story 15.1
        # closed the campaign (campaign-state.yaml `current_focus:
        # "campaign-closed"`), so no order>=2 slice carries one to gate.
        if not brief_path:
            continue
        slice_id = _slice_ref(sl)
        unmet = []
        for key in RE_SCOPE_GATE_PRE_CONDITION_KEYS:
            entry = pre_conditions.get(key)
            if not _precondition_status_satisfied(entry):
                unmet.append(key)
        if unmet:
            findings.append({
                "kind": "gate-bypassed",
                "ref": slice_id,
                "refs": [slice_id, *unmet],
                "detail": f"slice '{slice_id}' (order={order}) has brief_path "
                          f"set but campaign.re_scope_gate.pre_conditions has "
                          f"unclosed pre-condition(s): {', '.join(unmet)}",
                "remedy": "close or explicitly waive (by a human, with a "
                          "dated reason) every campaign.re_scope_gate."
                          "pre_conditions entry before writing this slice's "
                          "brief",
            })

    return findings


def _unknown(message: str, as_json: bool) -> int:
    if as_json:
        print(json.dumps({"error": message, "retros_scanned": None, "findings": []}))
    else:
        print(f"UNKNOWN: {message}", file=sys.stderr)
    return 2


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="cfe-rebuild-guard-check",
        description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--since", default=DEFAULT_SINCE,
                     help="lower bound (exclusive) of the clause-(b) retro scan; "
                          "defaults to the Story-6.1 landing merge (PR #570)")
    args = ap.parse_args()

    state = campaign_state(CAMPAIGN_STATE_PATH)
    if state is None:
        return _unknown(f"could not read/parse {CAMPAIGN_STATE_PATH} as a YAML "
                         "mapping — file missing, unreadable, or malformed.",
                         args.json)

    history_skipped = not any_slice_has_brief_path(state)
    if history_skipped:
        retros: list[str] = []
    else:
        walked = retro_commits_since(ROOT, args.since)
        if walked is None:
            return _unknown(f"`git log {args.since}..HEAD` could not run — not a "
                             f"git repository, or {args.since} is unreachable from "
                             "HEAD.", args.json)
        retros = walked

    findings = scan(state, retros, root=ROOT)

    if args.json:
        payload = {
            "retros_scanned": None if history_skipped else len(retros),
            "findings": findings,
        }
        print(json.dumps(payload, indent=2))
        return 1 if findings else 0

    if history_skipped:
        print("cfe-rebuild-guard-check: skipped retro history walk (no slice carries brief_path)\n")
    else:
        print(f"cfe-rebuild-guard-check: {len(retros)} qualifying CFE retro commit(s) "
              f"in {args.since[:10]}..HEAD\n")
    if not findings:
        print("  clean — no slice has a stale equivalence result, no briefed "
              "slice is behind a landed retro, no legacy caller survives "
              "a declared endgame, and no order>=2 slice's brief bypasses "
              "the re-scope gate.")
        return 0

    for f in findings:
        print(f"  ✗ [{f['kind']}] {f['ref']}")
        print(f"      {f['detail']}")
        print(f"      → {f['remedy']}")
    print(f"\nFAIL: {len(findings)} finding(s). See docs/dreams/fidelity-enforcement.md "
          "and the Epic 6 campaign-state.yaml for context.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
