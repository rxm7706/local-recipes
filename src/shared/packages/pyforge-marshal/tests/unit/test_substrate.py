"""Story 46.1 (spec-pyforge-marshal CAP-192) -- the pure substrate contract:
the member table, the manifest's render/parse round trip and every
malformed-manifest refusal in the I/O matrix's "Unsafe manifest" row."""

from __future__ import annotations

import json

import pytest

from pyforge.marshal.core import substrate
from pyforge.marshal.core.model import Severity, Verdict
from pyforge.marshal.core.verdict import compute_verdict

_HEX = "a" * 64


def _entry(path: str, digest: str = _HEX, size: int = 3) -> dict[str, object]:
    return {"path": path, "sha256": digest, "size": size}


def _document(**overrides: object) -> dict[str, object]:
    document: dict[str, object] = {
        "schema": substrate.MANIFEST_SCHEMA,
        "schema_version": substrate.MANIFEST_SCHEMA_VERSION,
        "source_commit": "abc123",
        "archive": {"name": substrate.ASSET_ARCHIVE, "sha256": _HEX, "size": 10},
        "members": {
            substrate.MEMBER_STRUCTURE_GRAPH: {"files": [_entry(".codegraph/codegraph.db")]},
            substrate.MEMBER_PLANNING_GRAPH: {"files": [_entry(".claude/data/pyforge-scribe/graph.json")]},
            substrate.MEMBER_DERIVED_CONTEXT: {
                "files": [
                    _entry(".claude/data/pyforge-scribe/move-list.json"),
                    _entry(".claude/data/pyforge-scribe/cocoindex-index.json"),
                ]
            },
        },
    }
    document.update(overrides)
    return document


def _members_with(member: str, files: list[dict[str, object]]) -> dict[str, object]:
    return {member: {"files": files}}


class TestMemberTable:
    def test_three_members_with_the_specified_sentinels(self):
        assert {m.name: m.sentinel for m in substrate.SUBSTRATE_MEMBERS} == {
            "structure-graph": ".codegraph/codegraph.db",
            "planning-graph": ".claude/data/pyforge-scribe/graph.json",
            "derived-context": ".claude/data/pyforge-scribe/move-list.json",
        }

    def test_cocoindex_distill_is_the_only_optional_file(self):
        derived = substrate.member_by_name(substrate.MEMBER_DERIVED_CONTEXT)
        assert derived is not None
        assert derived.optional == (".claude/data/pyforge-scribe/cocoindex-index.json",)
        assert all(not m.optional for m in substrate.SUBSTRATE_MEMBERS if m is not derived)

    def test_planning_graph_rebuilds_before_the_distills(self):
        # `index refresh` upserts into graph.json -- a compile after it would overwrite that.
        names = [m.name for m in substrate.SUBSTRATE_MEMBERS]
        assert names.index("planning-graph") < names.index("derived-context")

    def test_rebuild_commands_name_the_real_grammar(self):
        by_name = {m.name: m.rebuild_command() for m in substrate.SUBSTRATE_MEMBERS}
        assert by_name == {
            "structure-graph": "codegraph init -y <repo-root>",
            "planning-graph": "scribe graph compile --nightly",
            "derived-context": "scribe index refresh",
        }


class TestManifestRoundTrip:
    def test_render_then_parse_is_lossless(self):
        files = {
            substrate.MEMBER_PLANNING_GRAPH: [
                substrate.ManifestFile(".claude/data/pyforge-scribe/graph.json", "b" * 64, 7)
            ],
        }
        text = substrate.render_manifest(
            source_commit="deadbeef", archive_sha256="c" * 64, archive_size=99, members=files
        )
        parsed = substrate.parse_manifest(text)
        assert parsed.source_commit == "deadbeef"
        assert parsed.archive_sha256 == "c" * 64
        assert parsed.archive_size == 99
        assert parsed.member_names() == (substrate.MEMBER_PLANNING_GRAPH,)
        assert parsed.files_of(substrate.MEMBER_PLANNING_GRAPH) == tuple(files[substrate.MEMBER_PLANNING_GRAPH])
        assert text.endswith("\n")
        assert text == substrate.render_manifest(
            source_commit="deadbeef", archive_sha256="c" * 64, archive_size=99, members=files
        )

    def test_render_refuses_what_parse_refuses(self):
        with pytest.raises(substrate.ManifestError):
            substrate.render_manifest(
                source_commit="x",
                archive_sha256="not-hex",
                archive_size=1,
                members={
                    substrate.MEMBER_PLANNING_GRAPH: [
                        substrate.ManifestFile(".claude/data/pyforge-scribe/graph.json", _HEX, 1)
                    ]
                },
            )

    def test_a_full_document_parses(self):
        parsed = substrate.parse_manifest(json.dumps(_document()))
        assert set(parsed.member_names()) == {m.name for m in substrate.SUBSTRATE_MEMBERS}
        index = parsed.file_index()
        assert index[".codegraph/codegraph.db"][0] == substrate.MEMBER_STRUCTURE_GRAPH


class TestMalformedManifest:
    @pytest.mark.parametrize(
        ("path", "needle"),
        [
            ("/etc/passwd", "absolute"),
            ("C:/x/graph.json", "absolute"),
            ("../.codegraph/codegraph.db", "'..'"),
            (".codegraph/../codegraph.db", "'..'"),
            ("./.codegraph/codegraph.db", "'.'"),
            (".codegraph//codegraph.db", "empty"),
            (".codegraph\\codegraph.db", "backslash"),
            (".claude/data/pyforge-scribe/graph.json", "foreign-member"),
            (".bashrc", "foreign-member"),
        ],
    )
    def test_unsafe_paths_are_refused(self, path, needle):
        document = _document(members=_members_with(substrate.MEMBER_STRUCTURE_GRAPH, [_entry(path)]))
        with pytest.raises(substrate.ManifestError, match=needle):
            substrate.parse_manifest(json.dumps(document))

    @pytest.mark.parametrize("digest", ["A" * 64, "a" * 63, "g" * 64, 12, None])
    def test_bad_hex_is_refused(self, digest):
        document = _document(
            members=_members_with(substrate.MEMBER_STRUCTURE_GRAPH, [_entry(".codegraph/codegraph.db", digest=digest)])
        )
        with pytest.raises(substrate.ManifestError, match="sha256"):
            substrate.parse_manifest(json.dumps(document))

    @pytest.mark.parametrize("size", [-1, True, 1.5, "3"])
    def test_bad_size_is_refused(self, size):
        document = _document(
            members=_members_with(substrate.MEMBER_STRUCTURE_GRAPH, [_entry(".codegraph/codegraph.db", size=size)])
        )
        with pytest.raises(substrate.ManifestError, match="size"):
            substrate.parse_manifest(json.dumps(document))

    def test_bad_archive_hex_is_refused(self):
        document = _document(archive={"name": substrate.ASSET_ARCHIVE, "sha256": "zz", "size": 1})
        with pytest.raises(substrate.ManifestError, match="archive sha256"):
            substrate.parse_manifest(json.dumps(document))

    def test_wrong_archive_name_is_refused(self):
        document = _document(archive={"name": "evil.tar.gz", "sha256": _HEX, "size": 1})
        with pytest.raises(substrate.ManifestError, match="archive name"):
            substrate.parse_manifest(json.dumps(document))

    def test_unknown_member_is_refused(self):
        document = _document(members={"home-dir": {"files": [_entry(".codegraph/codegraph.db")]}})
        with pytest.raises(substrate.ManifestError, match="unknown member"):
            substrate.parse_manifest(json.dumps(document))

    def test_missing_sentinel_is_refused(self):
        document = _document(
            members=_members_with(
                substrate.MEMBER_DERIVED_CONTEXT, [_entry(".claude/data/pyforge-scribe/cocoindex-index.json")]
            )
        )
        with pytest.raises(substrate.ManifestError, match="omits its sentinel"):
            substrate.parse_manifest(json.dumps(document))

    def test_duplicate_path_is_refused(self):
        document = _document(
            members=_members_with(
                substrate.MEMBER_STRUCTURE_GRAPH,
                [_entry(".codegraph/codegraph.db"), _entry(".codegraph/codegraph.db")],
            )
        )
        with pytest.raises(substrate.ManifestError, match="twice"):
            substrate.parse_manifest(json.dumps(document))

    @pytest.mark.parametrize(
        ("text", "needle"),
        [
            ("not json", "not JSON"),
            ("[]", "not a JSON object"),
            (json.dumps(_document(schema="other")), "schema"),
            (json.dumps(_document(schema_version=2)), "schema_version"),
            (json.dumps(_document(source_commit="")), "source_commit"),
            (json.dumps(_document(members={})), "members"),
            (json.dumps(_document(members={substrate.MEMBER_STRUCTURE_GRAPH: {"files": []}})), "no files"),
        ],
    )
    def test_structural_problems_are_refused(self, text, needle):
        with pytest.raises(substrate.ManifestError, match=needle):
            substrate.parse_manifest(text)


class TestDigestChecks:
    def test_archive_digest(self):
        manifest = substrate.parse_manifest(json.dumps(_document()))
        assert substrate.check_archive_digest(manifest, sha256=_HEX, size=10) is None
        assert "bytes" in (substrate.check_archive_digest(manifest, sha256=_HEX, size=11) or "")
        assert "does not match" in (substrate.check_archive_digest(manifest, sha256="b" * 64, size=10) or "")

    def test_file_digest(self):
        expected = substrate.ManifestFile(".codegraph/codegraph.db", _HEX, 3)
        assert substrate.check_file_digest(expected, sha256=_HEX, size=3) is None
        assert substrate.check_file_digest(expected, sha256=_HEX, size=4) is not None
        assert substrate.check_file_digest(expected, sha256="b" * 64, size=3) is not None


class TestGhArgv:
    def test_default_lets_gh_resolve_the_clones_remote(self):
        argv = substrate.render_gh_download_argv(tag="substrate-nightly", repo=None, dest_dir="/tmp/x")
        assert argv == (
            "gh",
            "release",
            "download",
            "substrate-nightly",
            "--pattern",
            "substrate-manifest.json",
            "--pattern",
            "substrate.tar.gz",
            "--dir",
            "/tmp/x",
        )

    def test_explicit_repo(self):
        argv = substrate.render_gh_download_argv(tag="t", repo="o/r", dest_dir="d")
        assert argv[4:6] == ("--repo", "o/r")


class TestFindings:
    def _member(self, name: str) -> substrate.SubstrateMember:
        member = substrate.member_by_name(name)
        assert member is not None
        return member

    def test_rebuild_is_warn_and_names_command_and_fetch_reason(self):
        finding = substrate.rebuild_finding(self._member("planning-graph"), fetch_reason="gh exited 1 (boom)")
        assert finding.code == "MRS-CTX-003"
        assert finding.severity is Severity.WARN
        assert "scribe graph compile --nightly" in finding.message
        assert "gh exited 1 (boom)" in finding.message
        assert compute_verdict([finding]) is Verdict.WARN

    def test_neither_fetched_nor_rebuilt_is_unevaluable(self):
        finding = substrate.unevaluable_finding(
            self._member("structure-graph"), fetch_reason="--offline", rebuild_reason="codegraph missing"
        )
        assert finding.code == "MRS-CTX-004"
        assert compute_verdict([finding]) is Verdict.UNEVALUABLE

    def test_refused_pack_is_warn(self):
        finding = substrate.refused_pack_finding("bad digest", path="/p")
        assert finding.code == "MRS-CTX-005"
        assert compute_verdict([finding]) is Verdict.WARN

    def test_gap_is_warn_and_nothing_packable_is_unevaluable(self):
        gap = substrate.gap_finding(self._member("derived-context"), reason="absent")
        assert gap.code == "MRS-CTX-006"
        assert compute_verdict([gap]) is Verdict.WARN
        nothing = substrate.nothing_packable_finding()
        assert nothing.code == "MRS-CTX-007"
        assert compute_verdict([nothing]) is Verdict.UNEVALUABLE
        assert "disk full" in substrate.nothing_packable_finding(write_error="disk full").message
