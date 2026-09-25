"""Story 28.8 (SPEC-marshal-token-economy CAP-5) -- ``marshal context
refresh``, and the story's three behavioral acceptance criteria.

The ACs are proven against ``_FakeScribeEngine``, a CONTRACT DOUBLE of the
``scribe index refresh`` grammar: it implements exactly the semantics
``pyforge.scribe.extras.cocoindex_flow.refresh_incremental`` declares --
fingerprint each declared artifact's current sources, compare against the
fingerprint persisted by the previous call, ``derive()`` (here: report as
refreshed) only on a mismatch, skip an artifact whose sources are
unchanged -- and prints scribe's own ``refreshed: ...; skipped
(unchanged): ...`` report line. It is a double for the ENGINE, never a
second copy of anything marshal owns: what is under test is marshal's
declaration (are the right files declared as an artifact's sources?) and
its consumption of the answer.

That is what makes AC 1 and AC 2 real rather than tautological -- landing
an unrelated story spec must NOT stale an epic's context distill (today's
whole-directory mtime rule does exactly that), and editing ``epics.md``
must stale exactly that one artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pytest
from pyforge.core.process import ProcessResult

from pyforge.marshal.adapters import scribe_cli
from pyforge.marshal.adapters.fs_local import FsError
from pyforge.marshal.adapters.scribe_cli import ScribeCli
from pyforge.marshal.cli import context as context_cli
from pyforge.marshal.cli.main import main
from pyforge.marshal.core import derived_context as derived
from pyforge.marshal.core.verdict import EXIT_OK

_SLUG = "pyforge-marshal"


class _FakeScribeEngine:
    """``scribe index refresh --declare <manifest>``, implemented to
    ``refresh_incremental``'s declared contract. Persists a
    ``{name: fingerprint}`` index between calls, exactly as the real extra
    does."""

    def __init__(self, index_path: Path) -> None:
        self.index_path = index_path
        self.calls: list[tuple[str, ...]] = []

    def run(self, argv, *, cwd, timeout_s=None):
        argv = tuple(argv)
        self.calls.append(argv)
        manifest = Path(argv[argv.index(derived.SCRIBE_DECLARE_OPTION) + 1])
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        previous: dict[str, str] = {}
        if self.index_path.is_file():
            previous = json.loads(self.index_path.read_text(encoding="utf-8"))
        current = dict(previous)
        refreshed: list[str] = []
        skipped: list[str] = []
        for artifact in payload["artifacts"]:
            fingerprint = self._fingerprint(Path(cwd), artifact["sources"])
            if previous.get(artifact["name"]) == fingerprint:
                skipped.append(artifact["name"])
            else:
                refreshed.append(artifact["name"])
            current[artifact["name"]] = fingerprint
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(current, sort_keys=True), encoding="utf-8")
        report = (
            f"refreshed: {', '.join(refreshed) or '(none)'}; "
            f"skipped (unchanged): {', '.join(skipped) or '(none)'} "
            f"-> {self.index_path}\n"
        )
        return ProcessResult(returncode=0, stdout=report, stderr="")

    @staticmethod
    def _fingerprint(root: Path, sources) -> str:
        signature = []
        for source in sources:
            path = root / source
            try:
                stat = path.stat()
            except OSError:
                signature.append([source, None, None])
            else:
                signature.append([source, stat.st_size, stat.st_mtime_ns])
        return hashlib.sha256(json.dumps(signature, sort_keys=True).encode("utf-8")).hexdigest()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A minimal fixture repo carrying the planning surface an epic's
    context distill is derived from, plus noise the distill never reads."""
    planning = tmp_path / derived.planning_artifacts_relpath(_SLUG)
    _write(planning / "epics.md", "# Epics\n" + ("story\n" * 50))
    _write(planning / "PRD.md", "# PRD\n" + ("requirement\n" * 50))
    _write(planning / "architecture.md", "# Architecture\n")
    _write(planning / "sprint-status-ledger.yaml", "development_status:\n")
    _write(planning / "index.md", "# Index\n")
    _write(planning / "specs" / "spec-28-1-a.md", "# 28.1\n")
    _write(planning / "specs" / "spec-27-4-b.md", "# 27.4\n")
    _write(tmp_path / derived.implementation_artifacts_relpath(_SLUG) / ".keep", "")
    return tmp_path


def _declare_layer(repo: Path, *, enabled: bool) -> None:
    policy_path = repo / (f"_bmad-output/projects/{_SLUG}/planning-artifacts/marshal-policy.toml")
    _write(
        policy_path,
        f"[context.derived-context]\nenabled = {str(enabled).lower()}\n",
    )


def _args(repo: Path, *, epic: str = "28", project: str | None = _SLUG):
    return argparse.Namespace(project=project, epic=epic, root=str(repo), format="json")


def _run(repo: Path, engine, capsys, **kwargs) -> dict:
    code = context_cli.run_context_refresh(_args(repo, **kwargs), scribe=ScribeCli(engine))
    envelope = json.loads(capsys.readouterr().out)
    envelope["exit_code"] = code
    return envelope


def _bundle_args(
    repo: Path,
    *,
    epic: str = "28",
    project: str | None = _SLUG,
    expect_digest: str | None = None,
    format: str = "json",
):
    return argparse.Namespace(
        project=project,
        epic=epic,
        root=str(repo),
        expect_digest=expect_digest,
        format=format,
    )


def _run_bundle(repo: Path, capsys, **kwargs) -> dict:
    code = context_cli.run_context_bundle(_bundle_args(repo, **kwargs))
    envelope = json.loads(capsys.readouterr().out)
    envelope["exit_code"] = code
    return envelope


@pytest.fixture
def engine(tmp_path: Path, monkeypatch) -> _FakeScribeEngine:
    monkeypatch.setattr(scribe_cli.shutil, "which", lambda _n: "/usr/bin/scribe")
    return _FakeScribeEngine(tmp_path / "scribe-index.json")


class TestLayerOffMeansUnchanged:
    """AC 3: with the layer declared off, today's compile-on-hunch
    behavior is unchanged -- nothing new happens at all."""

    def test_reports_compile_on_hunch_and_invokes_nothing(self, repo, engine, capsys):
        _declare_layer(repo, enabled=False)
        envelope = _run(repo, engine, capsys)
        assert envelope["exit_code"] == EXIT_OK
        assert envelope["verdict"] == "clean"
        assert envelope["data"]["mode"] == derived.MODE_COMPILE_ON_HUNCH
        assert envelope["data"]["layer"]["enabled"] is False
        assert envelope["data"]["artifacts"] == []
        assert envelope["findings"] == []
        assert engine.calls == []

    def test_an_absent_context_block_is_the_same_as_declared_off(self, repo, engine, capsys):
        """Story 28.1's "absent block = every layer off" composes through
        here with no second rule."""
        envelope = _run(repo, engine, capsys)
        assert envelope["data"]["layer"]["enabled"] is False
        assert envelope["data"]["mode"] == derived.MODE_COMPILE_ON_HUNCH
        assert engine.calls == []

    def test_writes_no_manifest_and_reads_no_planning_document(self, repo, engine, capsys, monkeypatch):
        _declare_layer(repo, enabled=False)
        read: list[str] = []
        original = Path.read_text
        monkeypatch.setattr(
            Path,
            "read_text",
            lambda self, *a, **k: (read.append(str(self)), original(self, *a, **k))[1],
        )
        _run(repo, engine, capsys)
        assert not any(name.endswith("epics.md") for name in read)
        assert not (repo / context_cli._MANIFEST_DIR_RELPATH).exists()


class TestZeroRecomputeOnUnchangedSources:
    """AC 1: two consecutive iterations with unchanged planning sources --
    the second recomputes nothing."""

    def test_second_iteration_reports_every_artifact_fresh(self, repo, engine, capsys):
        _declare_layer(repo, enabled=True)
        first = _run(repo, engine, capsys)
        assert first["data"]["mode"] == derived.MODE_INCREMENTAL
        # First-ever run has no recorded fingerprint: both artifacts derive.
        assert {a["state"] for a in first["data"]["artifacts"]} == {derived.STATE_STALE}

        second = _run(repo, engine, capsys)
        assert second["exit_code"] == EXIT_OK
        assert second["verdict"] == "clean"
        assert second["data"]["mode"] == derived.MODE_INCREMENTAL
        assert [a["state"] for a in second["data"]["artifacts"]] == [
            derived.STATE_FRESH,
            derived.STATE_FRESH,
        ]
        assert second["findings"] == []

    def test_an_unrelated_story_spec_landing_does_not_stale_the_epic_context(self, repo, engine, capsys):
        """The over-eager recompile this story removes: today's rule
        ("no file in planning-artifacts is newer") invalidates every epic's
        distill the moment ANY spec lands."""
        _declare_layer(repo, enabled=True)
        _run(repo, engine, capsys)
        _write(
            repo / derived.planning_specs_relpath(_SLUG) / "spec-19-2-unrelated.md",
            "# a different epic's story\n",
        )
        _write(
            repo / derived.planning_artifacts_relpath(_SLUG) / "retro-2026.md",
            "# a retro the distill never reads\n",
        )

        after = _run(repo, engine, capsys)
        states = {a["name"]: a["state"] for a in after["data"]["artifacts"]}
        assert states[derived.epic_context_artifact_name(_SLUG, "28")] == derived.STATE_FRESH
        assert states[derived.continuity_artifact_name(_SLUG, "28")] == derived.STATE_FRESH

    def test_marshal_never_reads_a_planning_documents_contents(self, repo, engine, capsys, monkeypatch):
        """ "No full-document read" is the AC's own observable. Marshal
        lists filenames and declares paths; the engine stats them. Nothing
        in this path opens the 65k-token epics file."""
        _declare_layer(repo, enabled=True)
        read: list[str] = []
        original = Path.read_text
        monkeypatch.setattr(
            Path,
            "read_text",
            lambda self, *a, **k: (read.append(str(self)), original(self, *a, **k))[1],
        )
        _run(repo, engine, capsys)
        assert not any(name.endswith(("epics.md", "PRD.md", "architecture.md")) for name in read)


class TestExactlyOneRefreshOnASourceEdit:
    """AC 2: a planning-source edit yields exactly one refresh, and the
    derived artifact reflects the edit."""

    def test_editing_epics_stales_only_the_epic_context_artifact(self, repo, engine, capsys):
        _declare_layer(repo, enabled=True)
        _run(repo, engine, capsys)
        _write(
            repo / derived.planning_artifacts_relpath(_SLUG) / "epics.md",
            "# Epics\n" + ("story\n" * 80) + "### Story 28.99: a new one\n",
        )

        after = _run(repo, engine, capsys)
        states = {a["name"]: a["state"] for a in after["data"]["artifacts"]}
        assert states[derived.epic_context_artifact_name(_SLUG, "28")] == derived.STATE_STALE
        assert states[derived.continuity_artifact_name(_SLUG, "28")] == derived.STATE_FRESH
        assert sum(1 for s in states.values() if s == derived.STATE_STALE) == 1

        # ...and the refresh settles: a third iteration recomputes nothing.
        settled = _run(repo, engine, capsys)
        assert {a["state"] for a in settled["data"]["artifacts"]} == {derived.STATE_FRESH}

    def test_a_same_epic_spec_landing_stales_only_the_continuity_artifact(self, repo, engine, capsys):
        _declare_layer(repo, enabled=True)
        _run(repo, engine, capsys)
        _write(
            repo / derived.planning_specs_relpath(_SLUG) / "spec-28-8-new.md",
            "# 28.8\n",
        )

        after = _run(repo, engine, capsys)
        states = {a["name"]: a["state"] for a in after["data"]["artifacts"]}
        assert states[derived.continuity_artifact_name(_SLUG, "28")] == derived.STATE_STALE
        assert states[derived.epic_context_artifact_name(_SLUG, "28")] == derived.STATE_FRESH

    def test_deleting_a_declared_source_is_a_change_not_a_silent_no_op(self, repo, engine, capsys):
        _declare_layer(repo, enabled=True)
        _run(repo, engine, capsys)
        (repo / derived.planning_artifacts_relpath(_SLUG) / "architecture.md").unlink()

        after = _run(repo, engine, capsys)
        states = {a["name"]: a["state"] for a in after["data"]["artifacts"]}
        assert states[derived.epic_context_artifact_name(_SLUG, "28")] == derived.STATE_STALE


class TestManifestAndGrammar:
    def test_manifest_lands_in_the_gitignored_derived_data_dir(self, repo, engine, capsys):
        _declare_layer(repo, enabled=True)
        envelope = _run(repo, engine, capsys)
        manifest = Path(envelope["data"]["manifest"])
        assert manifest.is_file()
        assert context_cli._MANIFEST_DIR_RELPATH in str(manifest)
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        names = [a["name"] for a in payload["artifacts"]]
        assert names == sorted(names)

    def test_the_manifest_is_byte_stable_across_unchanged_iterations(self, repo, engine, capsys):
        """A declaration that churns would itself look like a change."""
        _declare_layer(repo, enabled=True)
        first = Path(_run(repo, engine, capsys)["data"]["manifest"]).read_bytes()
        second = Path(_run(repo, engine, capsys)["data"]["manifest"]).read_bytes()
        assert first == second

    def test_invokes_the_declared_scribe_grammar_once_per_iteration(self, repo, engine, capsys):
        _declare_layer(repo, enabled=True)
        _run(repo, engine, capsys)
        assert len(engine.calls) == 1
        argv = engine.calls[0]
        assert argv[1:3] == derived.SCRIBE_REFRESH_ARGV
        assert derived.SCRIBE_DECLARE_OPTION in argv


class TestDegradationNeverBlocks:
    def test_a_missing_scribe_falls_back_to_compile_on_hunch_with_a_warning(self, repo, capsys, monkeypatch, tmp_path):
        _declare_layer(repo, enabled=True)
        monkeypatch.setattr(scribe_cli.shutil, "which", lambda _n: None)
        envelope = _run(repo, _FakeScribeEngine(tmp_path / "i.json"), capsys)
        assert envelope["exit_code"] == EXIT_OK
        assert envelope["verdict"] == "warn"
        assert envelope["data"]["mode"] == derived.MODE_COMPILE_ON_HUNCH
        assert [f["code"] for f in envelope["findings"]] == ["MRS-CTX-002"]

    def test_a_grammar_that_answers_for_neither_list_is_reported_not_assumed_fresh(self, repo, capsys, monkeypatch):
        _declare_layer(repo, enabled=True)
        monkeypatch.setattr(scribe_cli.shutil, "which", lambda _n: "/usr/bin/scribe")

        class _Silent:
            def run(self, argv, *, cwd, timeout_s=None):
                return ProcessResult(
                    returncode=0,
                    stdout="refreshed: (none); skipped (unchanged): (none)\n",
                    stderr="",
                )

        envelope = _run(repo, _Silent(), capsys)
        assert envelope["verdict"] == "warn"
        assert {a["state"] for a in envelope["data"]["artifacts"]} == {derived.STATE_UNKNOWN}
        assert [f["code"] for f in envelope["findings"]] == ["MRS-CTX-002"]

    def test_a_malformed_epic_is_unevaluable_not_a_crash(self, repo, engine, capsys):
        _declare_layer(repo, enabled=True)
        envelope = _run(repo, engine, capsys, epic="twenty-eight")
        assert [f["code"] for f in envelope["findings"]] == ["MRS-CTX-001"]
        assert envelope["data"]["mode"] == derived.MODE_COMPILE_ON_HUNCH
        assert engine.calls == []

    def test_a_project_with_no_planning_artifacts_is_unevaluable(self, repo, engine, capsys):
        """The layer is declared on repo-wide, but the named station has no
        planning-artifacts directory -- there is nothing to declare as a
        source, so there is no freshness answer either way."""
        _write(
            repo / "_bmad-output/policy-defaults.toml",
            "[context.derived-context]\nenabled = true\n",
        )
        envelope = _run(repo, engine, capsys, project="pyforge-nowhere")
        assert [f["code"] for f in envelope["findings"]] == ["MRS-CTX-001"]
        assert envelope["data"]["mode"] == derived.MODE_COMPILE_ON_HUNCH
        assert engine.calls == []

    def test_a_malformed_slug_is_unevaluable_never_an_interpolated_path(self, repo, engine, capsys):
        _write(
            repo / "_bmad-output/policy-defaults.toml",
            "[context.derived-context]\nenabled = true\n",
        )
        envelope = _run(repo, engine, capsys, project="../escape")
        assert [f["code"] for f in envelope["findings"]] == ["MRS-CTX-001"]
        assert engine.calls == []


class TestCliSurface:
    def test_is_registered_as_a_top_level_verb_with_a_required_action(self, capsys):
        assert main(["context"]) != EXIT_OK
        capsys.readouterr()

    def test_epic_is_required(self, capsys):
        assert main(["context", "refresh", "--project", _SLUG]) != EXIT_OK
        capsys.readouterr()

    def test_runs_end_to_end_through_main_with_the_layer_off(self, repo, capsys):
        code = main(
            [
                "context",
                "refresh",
                "--project",
                _SLUG,
                "--epic",
                "28",
                "--root",
                str(repo),
                "--format",
                "json",
            ]
        )
        envelope = json.loads(capsys.readouterr().out)
        assert code == EXIT_OK
        assert envelope["data"]["mode"] == derived.MODE_COMPILE_ON_HUNCH

    def test_text_rendering_names_the_layer_and_the_mode(self, repo, engine, capsys):
        _declare_layer(repo, enabled=True)
        context_cli.run_context_refresh(
            argparse.Namespace(project=_SLUG, epic="28", root=str(repo), format="text"),
            scribe=ScribeCli(engine),
        )
        out = capsys.readouterr().out
        assert derived.DERIVED_CONTEXT_LAYER in out
        assert derived.MODE_INCREMENTAL in out
        assert "artifacts:" in out


class TestContextBundle:
    """Story 46.2 (spec-pyforge-marshal CAP-192) -- ``marshal context
    bundle``: no scribe subprocess, no freshness state, just the declared
    sources plus the resolved layer config, hashed. Two independent runs
    against the SAME fixture tree must produce byte-identical digests, and
    ``--expect-digest`` names any drift as ``MRS-CTX-008`` (WARN, never
    blocking) rather than silently reporting a new number."""

    def test_two_runs_against_the_same_fixture_tree_produce_an_identical_digest(self, repo, capsys):
        first = _run_bundle(repo, capsys)
        second = _run_bundle(repo, capsys)
        assert first["exit_code"] == EXIT_OK
        assert first["verdict"] == "clean"
        assert first["data"]["digest"] == second["data"]["digest"]
        assert first["data"]["bundle"] == second["data"]["bundle"]
        assert first["findings"] == []

    def test_the_bundle_names_the_epic_and_carries_both_layers(self, repo, capsys):
        _declare_layer(repo, enabled=True)
        envelope = _run_bundle(repo, capsys)
        bundle = envelope["data"]["bundle"]
        assert bundle["epic"] == "28"
        assert bundle["derived_context"]["enabled"] is True
        assert isinstance(bundle["derived_context"]["declarations"], list)
        assert "planning_graph" in bundle

    def test_expect_digest_matching_reports_match_true_with_no_finding(self, repo, capsys):
        first = _run_bundle(repo, capsys)
        digest = first["data"]["digest"]
        second = _run_bundle(repo, capsys, expect_digest=digest)
        assert second["exit_code"] == EXIT_OK
        assert second["verdict"] == "clean"
        assert second["data"]["match"] is True
        assert second["findings"] == []

    def test_expect_digest_mismatched_emits_mrs_ctx_008_warn_and_match_false(self, repo, capsys):
        envelope = _run_bundle(repo, capsys, expect_digest="0" * 64)
        assert envelope["exit_code"] == EXIT_OK
        assert envelope["verdict"] == "warn"
        assert envelope["data"]["match"] is False
        assert [f["code"] for f in envelope["findings"]] == ["MRS-CTX-008"]

    def test_a_malformed_epic_is_unevaluable_with_no_digest_computed(self, repo, capsys):
        envelope = _run_bundle(repo, capsys, epic="twenty-eight")
        assert [f["code"] for f in envelope["findings"]] == ["MRS-CTX-001"]
        assert envelope["data"]["digest"] is None
        assert envelope["data"]["bundle"] is None

    def test_a_project_with_no_planning_artifacts_is_unevaluable(self, repo, capsys):
        envelope = _run_bundle(repo, capsys, project="pyforge-nowhere")
        assert [f["code"] for f in envelope["findings"]] == ["MRS-CTX-001"]
        assert envelope["data"]["digest"] is None

    def test_a_malformed_slug_is_unevaluable_never_an_interpolated_path(self, repo, capsys):
        envelope = _run_bundle(repo, capsys, project="../escape")
        assert [f["code"] for f in envelope["findings"]] == ["MRS-CTX-001"]
        assert envelope["data"]["digest"] is None

    def test_runs_end_to_end_through_main_with_the_layer_off(self, repo, capsys):
        code = main(
            [
                "context",
                "bundle",
                "--project",
                _SLUG,
                "--epic",
                "28",
                "--root",
                str(repo),
                "--format",
                "json",
            ]
        )
        envelope = json.loads(capsys.readouterr().out)
        assert code == EXIT_OK
        assert envelope["data"]["bundle"]["derived_context"]["enabled"] is False

    def test_text_rendering_names_the_digest_and_the_match(self, repo, capsys):
        context_cli.run_context_bundle(_bundle_args(repo, format="text"))
        out = capsys.readouterr().out
        assert "digest=" in out
        assert "match=None" in out


def _advisory_args(repo: Path, *, project: str | None = _SLUG, format: str = "json"):
    return argparse.Namespace(project=project, root=str(repo), format=format)


def _run_advisory(repo: Path, capsys, *, scribe=None, process=None, fs=None, **kwargs) -> dict:
    code = context_cli.run_context_advisory(
        _advisory_args(repo, **kwargs),
        scribe=scribe,
        process=process,
        fs=fs,
    )
    envelope = json.loads(capsys.readouterr().out)
    envelope["exit_code"] = code
    return envelope


def _declare(repo: Path, layer: str, *, enabled: bool) -> None:
    """Declares one ``[context.<layer>]`` block, appending to (rather than
    overwriting) any prior declaration in the same fixture -- so a test can
    declare more than one layer active at once."""
    policy_path = repo / (f"_bmad-output/projects/{_SLUG}/planning-artifacts/marshal-policy.toml")
    existing = policy_path.read_text(encoding="utf-8") if policy_path.is_file() else ""
    _write(policy_path, existing + f"\n[context.{layer}]\nenabled = {str(enabled).lower()}\n")


class _ScribeBinaryDouble:
    """A minimal ``ScribeCli`` double -- ``_lapsed_layer_findings`` only
    ever calls ``resolve_binary``, so nothing else needs a real
    implementation."""

    def __init__(self, binary: str | None) -> None:
        self._binary = binary

    def resolve_binary(self, repo_root=None, *, fallback_bin_dirs=None):
        return self._binary


class _FakeGitLogProcess:
    """Answers ``git log -1 --format=%ct`` with a fixed HEAD timestamp, so
    a codegraph-index staleness comparison is deterministic without a real
    git history in the fixture tree."""

    def __init__(self, head_ts: int) -> None:
        self._head_ts = head_ts

    def run(self, argv, *, cwd, timeout_s=None):
        return ProcessResult(returncode=0, stdout=f"{self._head_ts}\n", stderr="")


class _AppendLineRaisesFs:
    """A minimal ``FsPort`` double -- Story 46.6 review triage fix 3.
    Directory creation and the sidecar write behave like a normal
    filesystem, but ``append_line`` (the final step of the journal write,
    outside the original ``try`` block's coverage) always raises
    ``FsError``. Proves the write's ``FsError`` guard now covers the WHOLE
    write, not just ``ensure_dir``/``create_dir_exclusive`` -- the command
    must degrade cleanly (no journal, clean exit code) rather than crash."""

    def ensure_dir(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def create_dir_exclusive(self, path: Path) -> None:
        path.mkdir(parents=False, exist_ok=False)

    def write_text_atomic(self, path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")

    def append_line(self, path: Path, line: str, *, fsync: bool) -> None:
        raise FsError("simulated append_line failure (Story 46.6 review triage fix 3)")


class TestContextAdvisory:
    """Story 46.6 (spec-pyforge-marshal CAP-193, fold-remint of
    spec-marshal-token-economy CAP-20) -- ``marshal context advisory``: a
    persistence advisory naming which declared-active [context] layers have
    lapsed, journaled once per invocation under a sibling
    ``session-advisories/`` Tier-3 run directory -- never ``dispatch-runs/``,
    so no existing dispatch-run reader is ever affected."""

    def test_every_layer_off_emits_no_findings_and_writes_no_journal(self, repo, capsys):
        envelope = _run_advisory(repo, capsys)
        assert envelope["exit_code"] == EXIT_OK
        assert envelope["verdict"] == "clean"
        assert envelope["findings"] == []
        assert envelope["data"]["journal"] is None

    def test_a_missing_kit_item_emits_one_finding_and_writes_the_journal(self, repo, capsys, monkeypatch):
        from pyforge.marshal.seed.detect import kit as kit_module

        _declare(repo, "structure-graph", enabled=True)
        monkeypatch.setattr(kit_module.shutil, "which", lambda _n: "/usr/bin/codegraph")
        # No .codegraph/codegraph.db written under repo -> MISSING.
        envelope = _run_advisory(repo, capsys)
        assert envelope["exit_code"] == EXIT_OK
        assert envelope["verdict"] == "warn"
        assert [f["code"] for f in envelope["findings"]] == ["MRS-CTX-009"]
        assert envelope["data"]["journal"] is not None
        journal = Path(envelope["data"]["journal"])
        assert journal.is_file()
        assert "session-advisories" in str(journal)
        assert "dispatch-runs" not in str(journal)

    def test_a_stale_kit_item_emits_one_finding(self, repo, capsys, monkeypatch):
        from pyforge.marshal.seed.detect import kit as kit_module

        _declare(repo, "structure-graph", enabled=True)
        monkeypatch.setattr(kit_module.shutil, "which", lambda _n: "/usr/bin/codegraph")
        index = repo / ".codegraph" / "codegraph.db"
        index.parent.mkdir(parents=True, exist_ok=True)
        index.write_bytes(b"stale")
        envelope = _run_advisory(repo, capsys, process=_FakeGitLogProcess(9999999999))
        assert envelope["exit_code"] == EXIT_OK
        assert envelope["verdict"] == "warn"
        assert [f["code"] for f in envelope["findings"]] == ["MRS-CTX-009"]
        assert envelope["data"]["journal"] is not None

    def test_layer_enabled_but_instrument_unavailable_emits_nothing(self, repo, capsys, monkeypatch):
        """Story 46.6 review triage fix 1: ``KitStatus.UNAVAILABLE`` means
        the instrument itself cannot exist on this platform (a linux-64-only
        tool probed on macOS, say) -- ``kit.py``'s own
        ``_FINDING_FOR_STATUS`` already classifies that ``Severity.INFO``,
        not ``DRIFT``. Treating it as lapsed here would emit a persistent,
        unfixable WARN every single run on a platform that will never have
        the instrument, so it must produce no finding at all."""
        from pyforge.marshal.seed.detect import kit as kit_module

        _declare(repo, "wire", enabled=True)
        monkeypatch.setattr(kit_module.shutil, "which", lambda _n: None)
        envelope = _run_advisory(repo, capsys)
        assert envelope["exit_code"] == EXIT_OK
        assert envelope["verdict"] == "clean"
        assert envelope["findings"] == []
        assert envelope["data"]["journal"] is None

    def test_an_enabled_scribe_backed_layer_with_no_resolvable_binary_emits_one_finding(self, repo, capsys):
        _declare(repo, "derived-context", enabled=True)
        envelope = _run_advisory(repo, capsys, scribe=_ScribeBinaryDouble(None))
        assert envelope["exit_code"] == EXIT_OK
        assert envelope["verdict"] == "warn"
        assert [f["code"] for f in envelope["findings"]] == ["MRS-CTX-009"]
        assert envelope["data"]["journal"] is not None

    def test_an_enabled_planning_graph_layer_with_no_resolvable_binary_emits_one_finding(self, repo, capsys):
        """Story 46.6 review triage fix 4: the scribe-binary branch pair
        (``derived-context``, ``planning-graph``) had only ``derived-context``
        exercised, even though Tasks & Acceptance names both layers."""
        _declare(repo, "planning-graph", enabled=True)
        envelope = _run_advisory(repo, capsys, scribe=_ScribeBinaryDouble(None))
        assert envelope["exit_code"] == EXIT_OK
        assert envelope["verdict"] == "warn"
        assert [f["code"] for f in envelope["findings"]] == ["MRS-CTX-009"]
        assert envelope["data"]["journal"] is not None

    def test_every_declared_active_layer_still_resolving_emits_nothing(self, repo, capsys, monkeypatch):
        from pyforge.marshal.seed.detect import kit as kit_module

        _declare(repo, "wire", enabled=True)
        _declare(repo, "derived-context", enabled=True)
        monkeypatch.setattr(kit_module.shutil, "which", lambda _n: "/usr/bin/headroom")
        (repo / ".marshal" / "wire").mkdir(parents=True, exist_ok=True)
        envelope = _run_advisory(repo, capsys, scribe=_ScribeBinaryDouble("/usr/bin/scribe"))
        assert envelope["exit_code"] == EXIT_OK
        assert envelope["verdict"] == "clean"
        assert envelope["findings"] == []
        assert envelope["data"]["journal"] is None

    def test_two_simultaneously_lapsed_layers_write_one_journal_entry_naming_both(self, repo, capsys, monkeypatch):
        """Story 46.6 review triage fix 5: every existing test lapses only
        one layer at a time -- none proves the "one entry naming every
        lapsed layer" AC for the 2+-simultaneous case. Lapses a kit layer
        (``structure-graph``, MISSING) and a scribe-backed layer
        (``derived-context``, unresolvable binary) together."""
        from pyforge.marshal.seed.detect import kit as kit_module

        _declare(repo, "structure-graph", enabled=True)
        _declare(repo, "derived-context", enabled=True)
        monkeypatch.setattr(kit_module.shutil, "which", lambda _n: "/usr/bin/codegraph")
        # No .codegraph/codegraph.db written under repo -> MISSING.
        envelope = _run_advisory(repo, capsys, scribe=_ScribeBinaryDouble(None))
        assert envelope["exit_code"] == EXIT_OK
        assert envelope["verdict"] == "warn"
        assert [f["code"] for f in envelope["findings"]] == ["MRS-CTX-009", "MRS-CTX-009"]
        assert envelope["data"]["journal"] is not None

        journal = Path(envelope["data"]["journal"])
        lines = journal.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        lapsed = record["payload"]["lapsed"]
        assert len(lapsed) == 2
        messages = [entry["message"] for entry in lapsed]
        assert any("structure-graph" in message for message in messages)
        assert any("derived-context" in message for message in messages)

    def test_the_journal_entry_is_a_single_valid_observation_never_matched_by_the_dispatch_runs_glob(
        self, repo, capsys, monkeypatch
    ):
        from pyforge.marshal.seed.detect import kit as kit_module

        _declare(repo, "structure-graph", enabled=True)
        monkeypatch.setattr(kit_module.shutil, "which", lambda _n: "/usr/bin/codegraph")
        # No .codegraph/codegraph.db written under repo -> MISSING.
        envelope = _run_advisory(repo, capsys)
        journal = Path(envelope["data"]["journal"])
        lines = journal.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["phase"] == "observation"
        assert "intent_id" not in record
        assert record["kind"] == "context-advisory"
        assert record["payload"]["lapsed"][0]["code"] == "MRS-CTX-009"

        implementation_dir = repo / f"_bmad-output/projects/{_SLUG}/implementation-artifacts"
        dispatch_runs_dir = implementation_dir / "dispatch-runs"
        matched = list(dispatch_runs_dir.glob("*/journal.jsonl")) if dispatch_runs_dir.is_dir() else []
        assert matched == []
        assert journal.relative_to(implementation_dir).parts[0] == "session-advisories"

    def test_findings_without_an_active_project_are_still_emitted_with_a_skip_reason_and_no_journal(
        self, repo, capsys, monkeypatch
    ):
        """Story 46.6 review triage fix 2: no ``--project``, no
        ``BMAD_ACTIVE_PROJECT``, no active-project marker file -- a common
        state -- resolves ``slug`` to ``""``. Repo-default ``[context]``
        layers still compose in that state (``resolve_context_layers``
        folds ``_bmad-output/policy-defaults.toml`` even with no project
        layer), so a real lapse can still be found with nothing safe to
        journal it under. That must not look identical to "nothing lapsed"
        -- ``journal`` stays ``None`` but ``journal_skipped_reason`` names
        why."""
        from pyforge.marshal.seed.detect import kit as kit_module

        monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
        _write(repo / "_bmad-output" / "policy-defaults.toml", "[context.wire]\nenabled = true\n")
        monkeypatch.setattr(kit_module.shutil, "which", lambda _n: "/usr/bin/headroom")
        # No .marshal/wire directory written under repo -> MISSING.
        envelope = _run_advisory(repo, capsys, project=None)
        assert envelope["exit_code"] == EXIT_OK
        assert envelope["data"]["project"] == ""
        assert [f["code"] for f in envelope["findings"]] == ["MRS-CTX-009"]
        assert envelope["data"]["journal"] is None
        assert envelope["data"]["journal_skipped_reason"] == context_cli._NO_ACTIVE_PROJECT_REASON

    def test_an_fs_error_during_the_journal_write_degrades_cleanly_rather_than_crashing(
        self, repo, capsys, monkeypatch
    ):
        """Story 46.6 review triage fix 3: the original ``try/except
        FsError`` only wrapped ``ensure_dir``/``create_dir_exclusive``. An
        ``FsError`` from ``append_line`` (the final write step) must also
        degrade cleanly -- no journal path, no reason, a normal exit code --
        rather than propagate uncaught through ``cli/main.py::run()``."""
        from pyforge.marshal.seed.detect import kit as kit_module

        _declare(repo, "structure-graph", enabled=True)
        monkeypatch.setattr(kit_module.shutil, "which", lambda _n: "/usr/bin/codegraph")
        # No .codegraph/codegraph.db written under repo -> MISSING.
        envelope = _run_advisory(repo, capsys, fs=_AppendLineRaisesFs())
        assert envelope["exit_code"] == EXIT_OK
        assert envelope["verdict"] == "warn"
        assert [f["code"] for f in envelope["findings"]] == ["MRS-CTX-009"]
        assert envelope["data"]["journal"] is None
        assert envelope["data"]["journal_skipped_reason"] is None

    def test_runs_end_to_end_through_main_with_every_layer_off(self, repo, capsys):
        code = main(
            [
                "context",
                "advisory",
                "--project",
                _SLUG,
                "--root",
                str(repo),
                "--format",
                "json",
            ]
        )
        envelope = json.loads(capsys.readouterr().out)
        assert code == EXIT_OK
        assert envelope["data"]["journal"] is None

    def test_text_rendering_names_the_project_and_the_journal(self, repo, capsys):
        context_cli.run_context_advisory(_advisory_args(repo, format="text"))
        out = capsys.readouterr().out
        assert f"project={_SLUG}" in out
        assert "journal=None" in out
