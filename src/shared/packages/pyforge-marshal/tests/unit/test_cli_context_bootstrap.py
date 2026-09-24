"""Story 46.1 (spec-pyforge-marshal CAP-192) -- ``marshal context bootstrap``
and ``marshal context pack``, one test (at least) per I/O-matrix row.

The seams are the real ones: ``gh`` and ``codegraph`` reach the handler
through a ``ProcessPort`` double, and the two scribe members through the real
``ScribeCli`` adapter over that same double -- so a test that passes here
exercises the production call path down to the argv."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import pytest
from pyforge.core.process import ProcessError, ProcessResult

from pyforge.marshal.adapters import scribe_cli
from pyforge.marshal.cli import context_bootstrap as cli
from pyforge.marshal.cli.main import main
from pyforge.marshal.core import substrate

_HOME_FILES = {
    ".codegraph/codegraph.db": b"SQLite format 3\x00" + bytes(range(256)) * 4,
    ".claude/data/pyforge-scribe/graph.json": b'{"nodes": ["loop-home"]}\n',
    ".claude/data/pyforge-scribe/move-list.json": b'{"moves": ["loop-home"]}\n',
    ".claude/data/pyforge-scribe/cocoindex-index.json": b'{"index": "loop-home"}\n',
}
#: What the fakes write when a member is REBUILT -- deliberately not the loop
#: home's bytes, so a test can tell a fetched member from a rebuilt one.
_REBUILT = {
    "codegraph": (".codegraph/codegraph.db", b"rebuilt codegraph\n"),
    ("graph", "compile", "--nightly"): (".claude/data/pyforge-scribe/graph.json", b'{"rebuilt": "graph"}\n'),
    ("index", "refresh"): (".claude/data/pyforge-scribe/move-list.json", b'{"rebuilt": "distills"}\n'),
}
_SCRIBE = "/usr/bin/scribe"
_ALL = [m.name for m in substrate.SUBSTRATE_MEMBERS]


def _write_tree(root: Path, files: dict[str, bytes]) -> Path:
    for rel, data in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return root


def _read_tree(root: Path, rels) -> dict[str, bytes]:
    return {rel: (root / rel).read_bytes() for rel in rels if (root / rel).is_file()}


class _Fake:
    """``ProcessPort`` double for every tool bootstrap/pack may run.

    ``gh`` copies the pair from ``release`` into ``--dir`` (or fails as
    configured); ``codegraph`` and ``scribe`` write the member's sentinel
    unless told to fail or to "succeed" without writing it."""

    def __init__(
        self,
        *,
        release: Path | None = None,
        gh_error: Exception | None = None,
        gh_result: ProcessResult | None = None,
        fail: dict[object, Exception | ProcessResult] | None = None,
        silent: set[object] | None = None,
        head: str | None = "0123456789abcdef",
    ) -> None:
        self.release = release
        self.gh_error = gh_error
        self.gh_result = gh_result
        self.fail = fail or {}
        self.silent = silent or set()
        self.head = head
        self.calls: list[tuple[str, ...]] = []

    def run(self, argv, *, cwd, timeout_s=None):
        argv = tuple(argv)
        self.calls.append(argv)
        ok = ProcessResult(returncode=0, stdout="", stderr="")
        if argv[0] == "gh":
            if self.gh_error is not None:
                raise self.gh_error
            if self.gh_result is not None:
                return self.gh_result
            dest = Path(argv[argv.index("--dir") + 1])
            if self.release is not None:
                for name in (substrate.ASSET_MANIFEST, substrate.ASSET_ARCHIVE):
                    shutil.copyfile(self.release / name, dest / name)
            return ok
        if argv[0] == "git":
            if self.head is None:
                raise ProcessError("executable not found: 'git'")
            return ProcessResult(returncode=0, stdout=self.head + "\n", stderr="")
        key: object = "codegraph" if argv[0] == "codegraph" else argv[1:]
        root = Path(argv[-1]) if argv[0] == "codegraph" else Path(cwd)
        outcome = self.fail.get(key)
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, ProcessResult):
            return outcome
        if key not in self.silent:
            rel, data = _REBUILT[key]  # type: ignore[index]
            _write_tree(root, {rel: data})
        return ok

    def tools(self) -> list[str]:
        return [c[0] if c[0] != _SCRIBE else " ".join(("scribe", *c[1:])) for c in self.calls]


@pytest.fixture(autouse=True)
def _scribe_on_path(monkeypatch):
    monkeypatch.setattr(scribe_cli.shutil, "which", lambda _name: _SCRIBE)


@pytest.fixture
def home(tmp_path: Path) -> Path:
    return _write_tree(tmp_path / "home", _HOME_FILES)


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    path = tmp_path / "clone"
    path.mkdir()
    return path


def _pack_args(root: Path, out: Path | None, commit: str | None = "feedface") -> argparse.Namespace:
    return argparse.Namespace(root=str(root), out=str(out) if out else None, source_commit=commit, format="json")


def _pack(root: Path, out: Path, capsys, process: _Fake | None = None, commit: str | None = "feedface"):
    code = cli.run_context_pack(_pack_args(root, out, commit), process=process or _Fake())
    return code, json.loads(capsys.readouterr().out)


@pytest.fixture
def release(home: Path, tmp_path: Path, capsys) -> Path:
    out = tmp_path / "release"
    code, _ = _pack(home, out, capsys)
    assert code == 0
    return out


def _boot_args(
    root: Path,
    *,
    from_dir: Path | str | None = None,
    offline: bool = False,
    repo: str | None = None,
    tag: str = substrate.DEFAULT_TAG,
):
    return argparse.Namespace(
        root=str(root),
        from_dir=str(from_dir) if from_dir is not None else None,
        offline=offline,
        tag=tag,
        repo=repo,
        format="json",
    )


def _boot(clone: Path, fake: _Fake, capsys, **kwargs):
    code = cli.run_context_bootstrap(_boot_args(clone, **kwargs), process=fake)
    captured = capsys.readouterr()
    return code, json.loads(captured.out), captured.err


def _states(envelope: dict) -> dict[str, str]:
    return {m["name"]: m["state"] for m in envelope["data"]["members"]}


def _codes(envelope: dict) -> list[str]:
    return [f["code"] for f in envelope["findings"]]


def _messages(envelope: dict, code: str) -> list[str]:
    return [f["message"] for f in envelope["findings"] if f["code"] == code]


class TestFetchServesAll:
    def test_every_member_installed_byte_identical_to_the_loop_home(self, clone, release, capsys):
        # AC1: the fetched substrate is byte-identical to the loop home's.
        fake = _Fake(release=release)
        code, envelope, err = _boot(clone, fake, capsys)

        assert code == 0
        assert envelope["verdict"] == "clean"
        assert envelope["findings"] == []
        assert _states(envelope) == dict.fromkeys(_ALL, substrate.STATE_FETCHED)
        assert _read_tree(clone, _HOME_FILES) == _HOME_FILES
        manifest = substrate.parse_manifest((release / substrate.ASSET_MANIFEST).read_text(encoding="utf-8"))
        for path, (_, entry) in manifest.file_index().items():
            assert hashlib.sha256((clone / path).read_bytes()).hexdigest() == entry.sha256
        assert fake.tools() == ["gh"]

    def test_the_network_use_is_announced_and_recorded(self, clone, release, capsys):
        fake = _Fake(release=release)
        _, envelope, err = _boot(clone, fake, capsys, repo="rxm7706/local-recipes")
        source = envelope["data"]["source"]
        assert source["kind"] == "release"
        assert source["network"] is True
        assert source["tag"] == substrate.DEFAULT_TAG
        assert source["repo"] == "rxm7706/local-recipes"
        assert source["source_commit"] == "feedface"
        assert "gh release download" in err and "(network)" in err
        assert "rxm7706/local-recipes" in err
        gh = fake.calls[0]
        assert gh[:4] == ("gh", "release", "download", substrate.DEFAULT_TAG)
        assert gh[4:6] == ("--repo", "rxm7706/local-recipes")

    def test_a_non_default_tag_reaches_the_gh_argv(self, clone, release, capsys):
        fake = _Fake(release=release)
        _, envelope, _ = _boot(clone, fake, capsys, tag="substrate-2026-09-01")
        assert fake.calls[0][3] == "substrate-2026-09-01"
        assert envelope["data"]["source"]["tag"] == "substrate-2026-09-01"


class TestFromDir:
    def test_same_install_with_no_network(self, clone, release, capsys):
        # AC2: pack -> bootstrap --from installs the loop home's bytes.
        fake = _Fake()
        code, envelope, err = _boot(clone, fake, capsys, from_dir=release)
        assert code == 0
        assert _states(envelope) == dict.fromkeys(_ALL, substrate.STATE_FETCHED)
        assert _read_tree(clone, _HOME_FILES) == _HOME_FILES
        source = envelope["data"]["source"]
        assert source["kind"] == "local"
        assert source["network"] is False
        assert source["dir"] == str(release.resolve())
        assert fake.calls == []
        assert err == ""

    def test_a_dir_without_the_pair_falls_back_to_rebuild(self, clone, tmp_path, capsys):
        empty = tmp_path / "empty"
        empty.mkdir()
        fake = _Fake()
        code, envelope, _ = _boot(clone, fake, capsys, from_dir=empty)
        assert code == 0
        assert _codes(envelope) == ["MRS-CTX-003"] * 3
        assert all("holds no" in m for m in _messages(envelope, "MRS-CTX-003"))
        assert "gh" not in fake.tools()

    def test_an_empty_from_never_calls_gh(self, clone, tmp_path, capsys, monkeypatch):
        # `--from "$UNSET"` is still --from: no network, never a fall-through to the fetch.
        cwd = tmp_path / "cwd"
        cwd.mkdir()
        monkeypatch.chdir(cwd)
        fake = _Fake()
        code, envelope, err = _boot(clone, fake, capsys, from_dir="")
        assert code == 0
        assert "gh" not in fake.tools()
        assert envelope["data"]["source"]["kind"] == "local"
        assert envelope["data"]["source"]["network"] is False
        assert "gh release download" not in err


class TestOffline:
    def test_every_missing_member_is_rebuilt_with_a_named_warn(self, clone, capsys):
        fake = _Fake()
        code, envelope, err = _boot(clone, fake, capsys, offline=True)
        assert code == 0
        assert envelope["verdict"] == "warn"
        assert _states(envelope) == dict.fromkeys(_ALL, substrate.STATE_REBUILT)
        assert _codes(envelope) == ["MRS-CTX-003"] * 3
        messages = _messages(envelope, "MRS-CTX-003")
        for member, message in zip(substrate.SUBSTRATE_MEMBERS, messages, strict=True):
            assert member.rebuild_command() in message
            assert "--offline was given" in message
        assert envelope["data"]["source"] == {
            "kind": "offline",
            "network": False,
            "tag": None,
            "repo": None,
            "dir": None,
            "source_commit": None,
        }
        # Planning graph compiles BEFORE the distills refresh (which upserts into graph.json).
        assert fake.tools() == ["codegraph", "scribe graph compile --nightly", "scribe index refresh"]
        assert err == ""

    def test_a_rebuild_failure_is_unevaluable(self, clone, capsys):
        fake = _Fake(fail={"codegraph": ProcessError("executable not found: 'codegraph'")})
        code, envelope, _ = _boot(clone, fake, capsys, offline=True)
        assert code == 1
        assert envelope["verdict"] == "unevaluable"
        assert _codes(envelope) == ["MRS-CTX-004", "MRS-CTX-003", "MRS-CTX-003"]
        [message] = _messages(envelope, "MRS-CTX-004")
        assert "executable not found: 'codegraph'" in message
        assert "--offline was given" in message
        assert _states(envelope)[substrate.MEMBER_STRUCTURE_GRAPH] == substrate.STATE_MISSING

    def test_a_scribe_non_zero_exit_is_unevaluable(self, clone, capsys):
        failed = ProcessResult(returncode=2, stdout="", stderr="Error: graphifyy is not installed\n")
        fake = _Fake(fail={("index", "refresh"): failed})
        code, envelope, _ = _boot(clone, fake, capsys, offline=True)
        assert code == 1
        [message] = _messages(envelope, "MRS-CTX-004")
        assert "graphifyy is not installed" in message
        assert "scribe index refresh" in message

    def test_exit_zero_without_the_sentinel_is_unevaluable(self, clone, capsys):
        fake = _Fake(silent={("graph", "compile", "--nightly")})
        code, envelope, _ = _boot(clone, fake, capsys, offline=True)
        assert code == 1
        [message] = _messages(envelope, "MRS-CTX-004")
        assert "exited 0 but .claude/data/pyforge-scribe/graph.json does not exist" in message


class TestFetchFails:
    @pytest.mark.parametrize(
        ("fake", "needle"),
        [
            (_Fake(gh_error=ProcessError("executable not found: 'gh'")), "executable not found: 'gh'"),
            (_Fake(gh_error=ProcessError("timed out after 600.0s")), "timed out after 600.0s"),
            (
                _Fake(gh_result=ProcessResult(returncode=1, stdout="", stderr="release not found\n")),
                "exited 1 (release not found)",
            ),
            (_Fake(), "was not downloaded"),
        ],
        ids=["gh-absent", "gh-timeout", "gh-non-zero", "gh-no-assets"],
    )
    def test_rebuild_fallback_carries_the_fetch_reason(self, clone, capsys, fake, needle):
        code, envelope, err = _boot(clone, fake, capsys)
        assert code == 0
        assert envelope["data"]["source"]["network"] is True
        assert _states(envelope) == dict.fromkeys(_ALL, substrate.STATE_REBUILT)
        messages = _messages(envelope, "MRS-CTX-003")
        assert len(messages) == 3
        assert all("the fetch failed" in m and needle in m for m in messages)
        assert "gh release download" in err


class TestRefusedPack:
    def test_tampered_bytes_install_nothing_and_rebuild(self, clone, release, capsys):
        archive = release / substrate.ASSET_ARCHIVE
        blob = bytearray(archive.read_bytes())
        blob[-10] ^= 0x01
        archive.write_bytes(bytes(blob))
        fake = _Fake()
        code, envelope, _ = _boot(clone, fake, capsys, from_dir=release)
        assert code == 0
        assert _codes(envelope) == ["MRS-CTX-005", "MRS-CTX-003", "MRS-CTX-003", "MRS-CTX-003"]
        [refusal] = _messages(envelope, "MRS-CTX-005")
        assert "does not match" in refusal
        assert all("the pack was refused" in m for m in _messages(envelope, "MRS-CTX-003"))
        # Nothing from the pack landed: every member holds the REBUILT bytes.
        assert (clone / ".codegraph/codegraph.db").read_bytes() == _REBUILT["codegraph"][1]
        assert not (clone / ".claude/data/pyforge-scribe/cocoindex-index.json").exists()

    @pytest.mark.parametrize(
        "path",
        [
            "/etc/codegraph.db",
            "../.codegraph/codegraph.db",
            ".claude/data/pyforge-scribe/graph.json",  # a foreign member's path
        ],
    )
    def test_an_unsafe_manifest_is_refused_as_malformed(self, clone, release, capsys, path):
        manifest = release / substrate.ASSET_MANIFEST
        document = json.loads(manifest.read_text(encoding="utf-8"))
        document["members"][substrate.MEMBER_STRUCTURE_GRAPH]["files"][0]["path"] = path
        manifest.write_text(json.dumps(document), encoding="utf-8")
        code, envelope, _ = _boot(clone, _Fake(), capsys, from_dir=release)
        assert code == 0
        [refusal] = _messages(envelope, "MRS-CTX-005")
        assert "malformed" in refusal
        assert _states(envelope) == dict.fromkeys(_ALL, substrate.STATE_REBUILT)

    def test_bad_hex_is_refused_as_malformed(self, clone, release, capsys):
        manifest = release / substrate.ASSET_MANIFEST
        document = json.loads(manifest.read_text(encoding="utf-8"))
        document["members"][substrate.MEMBER_PLANNING_GRAPH]["files"][0]["sha256"] = "XYZ"
        manifest.write_text(json.dumps(document), encoding="utf-8")
        code, envelope, _ = _boot(clone, _Fake(), capsys, from_dir=release)
        [refusal] = _messages(envelope, "MRS-CTX-005")
        assert "malformed" in refusal and "sha256" in refusal


class TestAlreadyPresent:
    def test_a_present_substrate_is_untouched_and_nothing_runs(self, clone, release, capsys):
        mine = {rel: b"the clone's own " + rel.encode() for rel in _HOME_FILES}
        _write_tree(clone, mine)
        fake = _Fake(release=release)
        code, envelope, err = _boot(clone, fake, capsys)
        assert code == 0
        assert envelope["findings"] == []
        assert _states(envelope) == dict.fromkeys(_ALL, substrate.STATE_PRESENT)
        assert _read_tree(clone, mine) == mine
        assert fake.calls == []
        assert err == ""
        assert envelope["data"]["source"]["kind"] == "none"

    def test_only_the_missing_members_are_fetched(self, clone, release, capsys):
        own = {".codegraph/codegraph.db": b"the clone's own index"}
        _write_tree(clone, own)
        fake = _Fake(release=release)
        code, envelope, err = _boot(clone, fake, capsys)
        assert code == 0
        assert _states(envelope) == {
            substrate.MEMBER_STRUCTURE_GRAPH: substrate.STATE_PRESENT,
            substrate.MEMBER_PLANNING_GRAPH: substrate.STATE_FETCHED,
            substrate.MEMBER_DERIVED_CONTEXT: substrate.STATE_FETCHED,
        }
        assert (clone / ".codegraph/codegraph.db").read_bytes() == own[".codegraph/codegraph.db"]
        assert substrate.MEMBER_STRUCTURE_GRAPH not in err.split("for:")[-1]

    def test_a_blocking_stray_file_is_not_overwritten_and_the_member_rebuilds(self, clone, release, capsys):
        stray = {".claude/data/pyforge-scribe/cocoindex-index.json": b"stray"}
        _write_tree(clone, stray)
        code, envelope, _ = _boot(clone, _Fake(), capsys, from_dir=release)
        assert code == 0
        assert _states(envelope)[substrate.MEMBER_DERIVED_CONTEXT] == substrate.STATE_REBUILT
        [message] = _messages(envelope, "MRS-CTX-003")
        assert "never overwrites" in message
        assert (clone / ".claude/data/pyforge-scribe/cocoindex-index.json").read_bytes() == b"stray"


class TestPack:
    def test_pair_describes_every_member_and_the_archive(self, home, tmp_path, capsys):
        code, envelope = _pack(home, tmp_path / "out", capsys)
        assert code == 0
        assert envelope["verdict"] == "clean"
        data = envelope["data"]
        assert data["source_commit"] == "feedface"
        assert data["absent"] == []
        archive = Path(data["archive"])
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == data["archive_sha256"]
        assert data["archive_size"] == archive.stat().st_size
        listed = {f["path"]: f["sha256"] for m in data["members"] for f in m["files"]}
        assert listed == {rel: hashlib.sha256(b).hexdigest() for rel, b in _HOME_FILES.items()}

    def test_packing_twice_gives_an_equal_archive_sha256(self, home, tmp_path, capsys):
        # AC3.
        _, first = _pack(home, tmp_path / "one", capsys)
        _, second = _pack(home, tmp_path / "two", capsys)
        assert first["data"]["archive_sha256"] == second["data"]["archive_sha256"]

    def test_a_gap_writes_the_pair_without_the_member(self, tmp_path, clone, capsys):
        gappy = _write_tree(
            tmp_path / "gappy",
            {k: v for k, v in _HOME_FILES.items() if "pyforge-scribe/move-list" not in k and "cocoindex" not in k},
        )
        out = tmp_path / "out"
        code, envelope = _pack(gappy, out, capsys)
        assert code == 0
        assert envelope["verdict"] == "warn"
        assert _codes(envelope) == ["MRS-CTX-006"]
        assert envelope["data"]["absent"] == [substrate.MEMBER_DERIVED_CONTEXT]
        manifest = substrate.parse_manifest((out / substrate.ASSET_MANIFEST).read_text(encoding="utf-8"))
        assert substrate.MEMBER_DERIVED_CONTEXT not in manifest.member_names()

        # The consumer installs what the pack carries and rebuilds the gap, naming it.
        code, boot, _ = _boot(clone, _Fake(), capsys, from_dir=out)
        assert code == 0
        assert _states(boot)[substrate.MEMBER_DERIVED_CONTEXT] == substrate.STATE_REBUILT
        [message] = _messages(boot, "MRS-CTX-003")
        assert "does not carry member 'derived-context'" in message

    def test_nothing_packable_is_unevaluable_and_writes_nothing(self, tmp_path, capsys):
        empty = tmp_path / "empty"
        empty.mkdir()
        out = tmp_path / "out"
        code, envelope = _pack(empty, out, capsys)
        assert code == 1
        assert envelope["verdict"] == "unevaluable"
        # Each member keeps its own reason (MRS-CTX-006); MRS-CTX-007 is added, not a replacement.
        assert _codes(envelope) == ["MRS-CTX-006"] * 3 + ["MRS-CTX-007"]
        [message] = _messages(envelope, "MRS-CTX-007")
        assert "no substrate member is packable" in message
        assert not out.exists()

    def test_a_write_failure_is_unevaluable(self, home, tmp_path, capsys):
        blocker = tmp_path / "blocker"
        blocker.write_text("a file where the output directory should be")
        code, envelope = _pack(home, blocker / "out", capsys)
        assert code == 1
        [message] = _messages(envelope, "MRS-CTX-007")
        assert "could not be written" in message

    def test_text_output_names_files_and_archive_sha(self, home, tmp_path, capsys):
        # The default format -- the one docs/air-gapped-deployment.md tells operators to use.
        args = _pack_args(home, tmp_path / "out")
        args.format = "text"
        code = cli.run_context_pack(args, process=_Fake())
        out = capsys.readouterr().out
        assert code == 0
        assert "context pack verdict=" in out
        for member in substrate.SUBSTRATE_MEMBERS:
            count = sum(1 for rel in _HOME_FILES if rel in member.files)
            assert f"{member.name}: {count} file(s)" in out
        archive_sha = hashlib.sha256((tmp_path / "out" / substrate.ASSET_ARCHIVE).read_bytes()).hexdigest()
        assert f"sha256={archive_sha}" in out

    def test_source_commit_defaults_to_git_head(self, home, tmp_path, capsys):
        fake = _Fake(head="abc123")
        _, envelope = _pack(home, tmp_path / "out", capsys, process=fake, commit=None)
        assert envelope["data"]["source_commit"] == "abc123"
        assert fake.calls == [("git", "rev-parse", "HEAD")]

    def test_source_commit_is_unknown_without_git(self, home, tmp_path, capsys):
        _, envelope = _pack(home, tmp_path / "out", capsys, process=_Fake(head=None), commit=None)
        assert envelope["data"]["source_commit"] == "unknown"

    def test_default_out_dir_is_under_the_gitignored_data_tree(self, home, capsys):
        code, envelope = _pack(home, None, capsys)
        assert code == 0
        assert Path(envelope["data"]["out"]) == home / cli.DEFAULT_PACK_DIR_RELPATH


class TestWiring:
    def test_main_routes_context_bootstrap(self, clone, capsys):
        _write_tree(clone, _HOME_FILES)
        code = main(["context", "bootstrap", "--root", str(clone), "--format", "json"])
        envelope = json.loads(capsys.readouterr().out)
        assert code == 0
        assert envelope["command"] == "context bootstrap"
        assert _states(envelope) == dict.fromkeys(_ALL, substrate.STATE_PRESENT)

    def test_main_routes_context_pack(self, home, tmp_path, capsys):
        out = tmp_path / "out"
        code = main(
            ["context", "pack", "--root", str(home), "--out", str(out), "--source-commit", "x", "--format", "json"]
        )
        envelope = json.loads(capsys.readouterr().out)
        assert code == 0
        assert envelope["command"] == "context pack"
        assert (out / substrate.ASSET_ARCHIVE).is_file()

    def test_from_and_offline_are_mutually_exclusive(self, clone, tmp_path, capsys):
        code = main(["context", "bootstrap", "--root", str(clone), "--offline", "--from", str(tmp_path)])
        assert code == 2
        assert "not allowed with" in capsys.readouterr().err

    def test_text_output_names_state_and_findings(self, clone, capsys):
        code = cli.run_context_bootstrap(
            argparse.Namespace(root=str(clone), from_dir=None, offline=True, tag="t", repo=None, format="text"),
            process=_Fake(),
        )
        out = capsys.readouterr().out
        assert code == 0
        assert "context bootstrap verdict=" in out
        assert "source: offline network=False" in out
        assert "structure-graph: rebuilt" in out
        assert "MRS-CTX-003" in out
