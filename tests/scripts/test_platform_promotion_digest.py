"""Steward Story 134.1: the promotion records a registry digest only after a push.

``DW-steward-133-2-1``: ``scripts/platform-golden-path-promotion.sh`` wrote the local image ID under
``images.*.digest``, Platform CI recorded the artifact before its optional push, and the local promotion
stage handed the same image IDs to the deploy verifier as digests. An image ID after ``@`` names nothing
a registry serves.

Operator ruling of 2026-11-25 ("Registry digest"): ``images.*.digest`` holds the registry manifest digest
after a push and is empty when nothing is pushed; ``images.*.image_id`` always holds the image ID; the
deploy verifier compares whichever of the two the artifact holds.

Both scripts run here against stand-ins for ``docker`` and ``warden``: no engine, no registry, no push.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMOTION_SCRIPT = REPO_ROOT / "scripts" / "platform-golden-path-promotion.sh"
VERIFY_SCRIPT = REPO_ROOT / "scripts" / "platform-deploy-verify-promotion.py"
CI_LOCAL_SCRIPT = REPO_ROOT / "scripts" / "platform-ci-local.sh"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "platform-ci.yml"
DEPLOY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "platform-deploy.yml"

IMAGES = ("platform", "sidecar", "mcpHost")
LOCAL_REFS = {
    "platform": "platform:ci",
    "sidecar": "platform-dbgpt-sidecar:ci",
    "mcpHost": "platform-mcp-host:ci",
}
REF_ENV = {
    "platform": "PLATFORM_REF",
    "sidecar": "SIDECAR_REF",
    "mcpHost": "MCP_HOST_REF",
}
PUSHED_REF_ENV = {
    "platform": "PLATFORM_PUSHED_REF",
    "sidecar": "SIDECAR_PUSHED_REF",
    "mcpHost": "MCP_HOST_PUSHED_REF",
}
DIGEST_ENV = {
    "platform": "PLATFORM_DIGEST",
    "sidecar": "SIDECAR_DIGEST",
    "mcpHost": "MCP_HOST_DIGEST",
}
IMAGE_ID_ENV = {
    "platform": "PLATFORM_IMAGE_ID",
    "sidecar": "SIDECAR_IMAGE_ID",
    "mcpHost": "MCP_HOST_IMAGE_ID",
}
REGISTRY = "registry.example.test:5000/team"
PUSHED_REFS = {
    "platform": f"{REGISTRY}/platform:0123abc",
    "sidecar": f"{REGISTRY}/platform-dbgpt-sidecar:0123abc",
    "mcpHost": f"{REGISTRY}/platform-mcp-host:0123abc",
}
IMAGE_IDS = {
    "platform": "sha256:" + "1" * 64,
    "sidecar": "sha256:" + "2" * 64,
    "mcpHost": "sha256:" + "3" * 64,
}
MANIFEST_DIGESTS = {
    "platform": "sha256:" + "a" * 64,
    "sidecar": "sha256:" + "b" * 64,
    "mcpHost": "sha256:" + "c" * 64,
}
OTHER_DIGEST = "sha256:" + "f" * 64

# `docker inspect --format=<template> <ref>`: the image ID, or one `repository@digest` line per entry of
# RepoDigests, each read from a file the test wrote for that reference. Anything else is a usage error,
# so a script that starts pushing or pulling from this path fails here.
_DOCKER_STUB = """#!/usr/bin/env bash
[ "$1" = inspect ] && [ "$#" -eq 3 ] || { echo "stub docker: unexpected call: $*" >&2; exit 64; }
key="$(printf '%s' "$3" | tr '/:@' '___')"
case "$2" in
  *RepoDigests*) [ -f "$STUB_DOCKER_DIR/$key.repodigests" ] && cat "$STUB_DOCKER_DIR/$key.repodigests"; exit 0 ;;
  *.Id*) cat "$STUB_DOCKER_DIR/$key.id" ;;
  *) echo "stub docker: unexpected format: $2" >&2; exit 64 ;;
esac
"""
_WARDEN_STUB = """#!/usr/bin/env bash
printf '%s\\n' '{"status": {"value": "clean"}, "inventory_count": 1}'
"""


def _key(ref: str) -> str:
    return re.sub(r"[/:@]", "_", ref)


def _write_executable(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _record(
    tmp_path: Path,
    *,
    pushed: dict[str, str] | None = None,
    repo_digests: dict[str, list[str]] | None = None,
    pushed_ids: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    """Run the promotion script. ``pushed`` maps an image to its pushed reference; ``repo_digests`` maps
    a pushed reference to the ``RepoDigests`` lines the stand-in engine reports for it. A pushed
    reference is the same image as its local one unless ``pushed_ids`` gives it another image ID."""
    bin_dir = tmp_path / "bin"
    state = tmp_path / "docker-state"
    state.mkdir()
    _write_executable(bin_dir / "docker", _DOCKER_STUB)
    _write_executable(bin_dir / "warden", _WARDEN_STUB)
    (bin_dir / "python").symlink_to(sys.executable)
    for image, ref in LOCAL_REFS.items():
        (state / f"{_key(ref)}.id").write_text(
            IMAGE_IDS[image] + "\n", encoding="utf-8"
        )
    for image, ref in (pushed or {}).items():
        (state / f"{_key(ref)}.id").write_text(
            (pushed_ids or {}).get(image, IMAGE_IDS[image]) + "\n", encoding="utf-8"
        )
    for ref, lines in (repo_digests or {}).items():
        (state / f"{_key(ref)}.repodigests").write_text(
            "".join(f"{line}\n" for line in lines), encoding="utf-8"
        )
    target = tmp_path / "target"
    target.mkdir()
    out = tmp_path / "golden-path-promotion.json"
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(tmp_path),
        "STUB_DOCKER_DIR": str(state),
        "WARDEN_TARGET": str(target),
        "OUT": str(out),
        **{REF_ENV[image]: ref for image, ref in LOCAL_REFS.items()},
        **{PUSHED_REF_ENV[image]: ref for image, ref in (pushed or {}).items()},
    }
    result = subprocess.run(
        ["/bin/bash", str(PROMOTION_SCRIPT)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return result, out


def _images(out: Path) -> dict[str, dict[str, Any]]:
    return json.loads(out.read_text(encoding="utf-8"))["images"]


def _all_pushed_repo_digests() -> dict[str, list[str]]:
    """Each pushed reference reports its own repository's digest after another repository's."""
    return {
        ref: [
            f"other.example.test/elsewhere@{OTHER_DIGEST}",
            f"{ref.rsplit(':', 1)[0]}@{MANIFEST_DIGESTS[image]}",
        ]
        for image, ref in PUSHED_REFS.items()
    }


# -- the promotion script ----------------------------------------------------


def test_nothing_pushed_never_records_an_image_id_under_digest(tmp_path: Path) -> None:
    result, out = _record(tmp_path)
    assert result.returncode == 0, result.stderr
    for image, entry in _images(out).items():
        assert entry["digest"] != IMAGE_IDS[image], (
            f"images.{image}.digest holds the image ID: an image ID is not a registry digest"
        )


def test_nothing_pushed_records_an_empty_digest(tmp_path: Path) -> None:
    result, out = _record(tmp_path)
    assert result.returncode == 0, result.stderr
    for image, entry in _images(out).items():
        assert entry["digest"] == "", (
            f"images.{image}.digest is {entry['digest']!r} with no pushed reference given"
        )


def test_the_image_id_is_always_recorded_under_image_id(tmp_path: Path) -> None:
    result, out = _record(tmp_path)
    assert result.returncode == 0, result.stderr
    images = _images(out)
    assert set(images) == set(IMAGES)
    for image, entry in images.items():
        assert entry.get("image_id") == IMAGE_IDS[image], (
            f"images.{image}.image_id is missing"
        )
        assert entry["ref"] == LOCAL_REFS[image]


def test_a_pushed_reference_records_the_manifest_digest_of_its_own_repository(
    tmp_path: Path,
) -> None:
    result, out = _record(
        tmp_path, pushed=PUSHED_REFS, repo_digests=_all_pushed_repo_digests()
    )
    assert result.returncode == 0, result.stderr
    for image, entry in _images(out).items():
        assert entry["digest"] == MANIFEST_DIGESTS[image], (
            f"images.{image}.digest is not the manifest digest the registry reports for {PUSHED_REFS[image]}"
        )
        assert entry["image_id"] == IMAGE_IDS[image]
        assert entry["pushed_ref"] == PUSHED_REFS[image]


def test_only_the_pushed_image_carries_a_digest(tmp_path: Path) -> None:
    pushed = {"platform": PUSHED_REFS["platform"]}
    digests = {
        PUSHED_REFS["platform"]: _all_pushed_repo_digests()[PUSHED_REFS["platform"]]
    }
    result, out = _record(tmp_path, pushed=pushed, repo_digests=digests)
    assert result.returncode == 0, result.stderr
    images = _images(out)
    assert images["platform"]["digest"] == MANIFEST_DIGESTS["platform"]
    assert images["sidecar"]["digest"] == ""
    assert images["mcpHost"]["digest"] == ""


def test_a_pushed_reference_the_registry_reports_no_digest_for_fails_the_record(
    tmp_path: Path,
) -> None:
    """A push that left no digest for that repository is not papered over with the image ID."""
    digests = _all_pushed_repo_digests()
    digests[PUSHED_REFS["sidecar"]] = [f"other.example.test/elsewhere@{OTHER_DIGEST}"]
    result, out = _record(tmp_path, pushed=PUSHED_REFS, repo_digests=digests)
    assert result.returncode != 0
    assert "no registry manifest digest" in result.stderr
    assert PUSHED_REFS["sidecar"] in result.stderr
    assert not out.exists()


def test_a_malformed_registry_digest_fails_the_record(tmp_path: Path) -> None:
    digests = _all_pushed_repo_digests()
    digests[PUSHED_REFS["platform"]] = [f"{REGISTRY}/platform@sha256:short"]
    result, out = _record(tmp_path, pushed=PUSHED_REFS, repo_digests=digests)
    assert result.returncode != 0
    assert "no registry manifest digest" in result.stderr
    assert not out.exists()


def test_a_pushed_reference_that_is_another_image_fails_the_record(
    tmp_path: Path,
) -> None:
    """The digest is read from the pushed reference: it must be the image whose ID the artifact records."""
    result, out = _record(
        tmp_path,
        pushed=PUSHED_REFS,
        repo_digests=_all_pushed_repo_digests(),
        pushed_ids={"mcpHost": OTHER_DIGEST},
    )
    assert result.returncode != 0
    assert (
        f"::error::pushed reference {PUSHED_REFS['mcpHost']} is not the image recorded as "
        f"{LOCAL_REFS['mcpHost']}"
    ) in result.stderr
    assert not out.exists()


def test_the_artifact_keeps_its_schema_marker_and_keys(tmp_path: Path) -> None:
    """``image_id`` and ``pushed_ref`` are additions: nothing the artifact had is renamed or removed."""
    result, out = _record(tmp_path)
    assert result.returncode == 0, result.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == "platform-golden-path-promotion/v1"
    assert {
        "recorded_at",
        "git_sha",
        "run_id",
        "run_attempt",
        "images",
        "warden",
        "warden_exit_code",
        "warden_status",
    } <= set(payload)
    for entry in payload["images"].values():
        assert {"ref", "digest", "image_id", "pushed_ref"} <= set(entry)
    assert json.loads(result.stdout) == payload


# -- the deploy verifier -----------------------------------------------------


def _artifact(
    images: dict[str, dict[str, str]], *, status: str = "clean"
) -> dict[str, Any]:
    return {
        "schema": "platform-golden-path-promotion/v1",
        "images": images,
        "warden": {"status": {"value": status, "driver": {"finding_id": "driver:x"}}},
        "warden_status": status,
    }


def _pushed_images() -> dict[str, dict[str, str]]:
    return {
        image: {
            "ref": LOCAL_REFS[image],
            "pushed_ref": PUSHED_REFS[image],
            "digest": MANIFEST_DIGESTS[image],
            "image_id": IMAGE_IDS[image],
        }
        for image in IMAGES
    }


def _unpushed_images() -> dict[str, dict[str, str]]:
    return {
        image: {
            "ref": LOCAL_REFS[image],
            "pushed_ref": "",
            "digest": "",
            "image_id": IMAGE_IDS[image],
        }
        for image in IMAGES
    }


def _verify(
    tmp_path: Path,
    artifact: dict[str, Any],
    *,
    digests: dict[str, str] | None = None,
    image_ids: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
    return _verify_text(
        tmp_path, json.dumps(artifact), digests=digests, image_ids=image_ids
    )


def _verify_text(
    tmp_path: Path,
    text: str,
    *,
    digests: dict[str, str] | None = None,
    image_ids: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
    promotion = tmp_path / "golden-path-promotion.json"
    promotion.write_text(text, encoding="utf-8")
    github_output = tmp_path / "github-output"
    github_output.write_text("", encoding="utf-8")
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PROMOTION_JSON": str(promotion),
        "GITHUB_OUTPUT": str(github_output),
        **{DIGEST_ENV[image]: value for image, value in (digests or {}).items()},
        **{IMAGE_ID_ENV[image]: value for image, value in (image_ids or {}).items()},
    }
    result = subprocess.run(
        [sys.executable, str(VERIFY_SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    outputs = dict(
        line.split("=", 1)
        for line in github_output.read_text(encoding="utf-8").splitlines()
        if "=" in line
    )
    return result, outputs


def test_verifier_accepts_the_recorded_digests(tmp_path: Path) -> None:
    result, outputs = _verify(
        tmp_path, _artifact(_pushed_images()), digests=MANIFEST_DIGESTS
    )
    assert result.returncode == 0, result.stderr
    assert "clean Warden verdict" in result.stdout
    assert outputs == {
        "by_digest": "true",
        "platform_digest": MANIFEST_DIGESTS["platform"],
        "sidecar_digest": MANIFEST_DIGESTS["sidecar"],
        "mcp_host_digest": MANIFEST_DIGESTS["mcpHost"],
    }


def test_verifier_accepts_the_recorded_image_ids_when_no_digest_is_recorded(
    tmp_path: Path,
) -> None:
    result, outputs = _verify(
        tmp_path, _artifact(_unpushed_images()), image_ids=IMAGE_IDS
    )
    assert result.returncode == 0, result.stderr
    assert "image ID" in result.stdout
    assert outputs == {
        "by_digest": "false",
        "platform_digest": "",
        "sidecar_digest": "",
        "mcp_host_digest": "",
    }, "an image ID must never leave the verifier as a digest"


def test_verifier_refuses_a_digest_that_differs_from_the_recorded_one(
    tmp_path: Path,
) -> None:
    requested = {**MANIFEST_DIGESTS, "sidecar": OTHER_DIGEST}
    result, _ = _verify(tmp_path, _artifact(_pushed_images()), digests=requested)
    assert result.returncode != 0
    assert "sidecar" in result.stderr
    assert result.stderr.startswith("::error::")


def test_verifier_refuses_an_image_id_where_a_digest_is_recorded(
    tmp_path: Path,
) -> None:
    """The recorded image IDs, requested as image IDs, do not stand in for the recorded digests."""
    result, _ = _verify(tmp_path, _artifact(_pushed_images()), image_ids=IMAGE_IDS)
    assert result.returncode != 0
    assert "records a registry digest" in result.stderr


def test_verifier_refuses_an_image_id_passed_as_the_digest(tmp_path: Path) -> None:
    result, _ = _verify(tmp_path, _artifact(_pushed_images()), digests=IMAGE_IDS)
    assert result.returncode != 0
    assert result.stderr.startswith("::error::")


def test_verifier_refuses_a_requested_digest_the_artifact_does_not_hold(
    tmp_path: Path,
) -> None:
    """The defect's own request: the image IDs handed over as digests, against a record with none."""
    result, _ = _verify(tmp_path, _artifact(_unpushed_images()), digests=IMAGE_IDS)
    assert result.returncode != 0
    assert "holds no registry digest" in result.stderr


def test_verifier_refuses_an_image_id_that_differs_from_the_recorded_one(
    tmp_path: Path,
) -> None:
    requested = {**IMAGE_IDS, "mcpHost": OTHER_DIGEST}
    result, _ = _verify(tmp_path, _artifact(_unpushed_images()), image_ids=requested)
    assert result.returncode != 0
    assert "mcpHost" in result.stderr


def test_verifier_refuses_a_request_that_names_neither(tmp_path: Path) -> None:
    result, _ = _verify(tmp_path, _artifact(_unpushed_images()))
    assert result.returncode != 0
    assert "PLATFORM_IMAGE_ID" in result.stderr


def test_verifier_reads_an_older_artifact_s_digest_as_the_image_id_it_was(
    tmp_path: Path,
) -> None:
    """An artifact written before this story has no ``image_id`` key and an image ID under ``digest``."""
    older = {
        image: {"ref": LOCAL_REFS[image], "digest": IMAGE_IDS[image]}
        for image in IMAGES
    }
    as_ids, outputs = _verify(tmp_path, _artifact(older), image_ids=IMAGE_IDS)
    assert as_ids.returncode == 0, as_ids.stderr
    assert outputs["by_digest"] == "false"
    as_digests, _ = _verify(tmp_path, _artifact(older), digests=IMAGE_IDS)
    assert as_digests.returncode != 0
    assert "holds no registry digest" in as_digests.stderr


@pytest.mark.parametrize(
    "status", ["indeterminate", "warn", "error", "policy-violation"]
)
def test_verifier_still_refuses_every_verdict_but_clean(
    tmp_path: Path, status: str
) -> None:
    result, outputs = _verify(
        tmp_path, _artifact(_pushed_images(), status=status), digests=MANIFEST_DIGESTS
    )
    assert result.returncode != 0
    assert "does not promote" in result.stderr
    assert outputs == {}


@pytest.mark.parametrize(
    "recorded",
    [
        MANIFEST_DIGESTS["platform"] + "\nby_digest=true",
        "sha256:short",
    ],
    ids=["newline-forges-an-output", "short"],
)
def test_verifier_refuses_a_malformed_recorded_digest_and_writes_no_output(
    tmp_path: Path, recorded: str
) -> None:
    """Even requested verbatim, a recorded digest that is not sha256 + 64 hex never reaches GITHUB_OUTPUT."""
    images = _pushed_images()
    images["platform"]["digest"] = recorded
    result, _ = _verify(
        tmp_path,
        _artifact(images),
        digests={**MANIFEST_DIGESTS, "platform": recorded},
    )
    assert result.returncode != 0
    assert result.stderr.startswith("::error::platform")
    assert "not a sha256 manifest digest" in result.stderr
    assert (tmp_path / "github-output").read_text(encoding="utf-8") == ""


def test_verifier_refuses_a_wrong_image_id_alongside_the_recorded_digests(
    tmp_path: Path,
) -> None:
    requested_ids = {**IMAGE_IDS, "sidecar": OTHER_DIGEST}
    result, outputs = _verify(
        tmp_path,
        _artifact(_pushed_images()),
        digests=MANIFEST_DIGESTS,
        image_ids=requested_ids,
    )
    assert result.returncode != 0
    assert "sidecar image ID" in result.stderr
    assert outputs == {}


def test_verifier_reports_a_partly_pushed_artifact_as_not_by_digest(
    tmp_path: Path,
) -> None:
    images = _unpushed_images()
    images["platform"] = _pushed_images()["platform"]
    result, outputs = _verify(
        tmp_path,
        _artifact(images),
        digests={"platform": MANIFEST_DIGESTS["platform"]},
        image_ids={"sidecar": IMAGE_IDS["sidecar"], "mcpHost": IMAGE_IDS["mcpHost"]},
    )
    assert result.returncode == 0, result.stderr
    assert outputs == {
        "by_digest": "false",
        "platform_digest": MANIFEST_DIGESTS["platform"],
        "sidecar_digest": "",
        "mcp_host_digest": "",
    }


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("nope", "is not JSON"),
        ("[]", "is not a JSON object"),
        (json.dumps({"images": [1], "warden": {}}), "no `images` mapping"),
        (
            json.dumps(
                {
                    "images": {"platform": "x", "sidecar": {}, "mcpHost": {}},
                    "warden": {"status": {"value": "clean"}},
                    "warden_status": "clean",
                }
            ),
            "images.platform is not a mapping",
        ),
        (
            json.dumps(
                {
                    "images": _pushed_images(),
                    "warden": {"status": "indeterminate"},
                }
            ),
            "Warden verdict is None, not 'clean' (driver: None)",
        ),
        (
            json.dumps(
                {
                    "images": _pushed_images(),
                    "warden": {"status": {"value": "warn", "driver": "driver:x"}},
                }
            ),
            "Warden verdict is 'warn', not 'clean' (driver: None)",
        ),
    ],
    ids=[
        "not-json",
        "not-an-object",
        "images-not-a-mapping",
        "entry-not-a-mapping",
        "warden-status-not-a-mapping",
        "driver-not-a-mapping",
    ],
)
def test_verifier_refuses_a_malformed_artifact_with_its_own_error(
    tmp_path: Path, text: str, message: str
) -> None:
    result, outputs = _verify_text(tmp_path, text, image_ids=IMAGE_IDS)
    assert result.returncode == 1
    assert result.stderr.startswith("::error::")
    assert message in result.stderr
    assert "Traceback" not in result.stderr
    assert outputs == {}


# -- the workflows and the local stage that write or check the artifact -------


def _job_block(workflow: Path, job: str) -> str:
    text = workflow.read_text(encoding="utf-8")
    match = re.search(
        rf"^  {re.escape(job)}:\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)",
        text,
        re.DOTALL | re.MULTILINE,
    )
    assert match, f"job {job} not found in {workflow.name}"
    return match.group(1)


def _step(block: str, name_fragment: str) -> str:
    """The text of the one step whose ``name:`` contains ``name_fragment``."""
    steps = re.split(r"(?m)^      - ", block)
    matches = [
        step for step in steps if re.match(rf"name: .*{re.escape(name_fragment)}", step)
    ]
    assert len(matches) == 1, (
        f"expected one step named like {name_fragment!r}, found {len(matches)}"
    )
    return matches[0]


def test_workflow_pushes_before_it_records() -> None:
    block = _job_block(CI_WORKFLOW, "golden-path-promotion")
    push = block.index("- name: Push images")
    record = block.index("- name: Record digests + Warden verdict")
    upload = block.index("actions/upload-artifact")
    assert push < record < upload, (
        "the optional push must stand before the record step: a registry digest exists only after a push"
    )
    assert "vars.PLATFORM_CI_PUSH_REGISTRY == 'true'" in _step(block, "Push images"), (
        "the push stays optional"
    )


def test_workflow_record_step_is_given_the_pushed_references() -> None:
    block = _job_block(CI_WORKFLOW, "golden-path-promotion")
    push = _step(block, "Push images")
    record = _step(block, "Record digests + Warden verdict")
    step_id = re.search(r"(?m)^        id: (\S+)$", push)
    assert step_id, "the push step needs an id for its outputs"
    for name, output in (
        ("PLATFORM_PUSHED_REF", "platform_pushed_ref"),
        ("SIDECAR_PUSHED_REF", "sidecar_pushed_ref"),
        ("MCP_HOST_PUSHED_REF", "mcp_host_pushed_ref"),
    ):
        assert f"{output}=" in push, f"the push step does not write {output}"
        assert (
            f"{name}: ${{{{ steps.{step_id.group(1)}.outputs.{output} }}}}" in record
        ), f"the record step is not given {name} from the push step"


def test_workflow_and_scripts_never_read_an_image_id_into_a_digest() -> None:
    """Acceptance criterion 2, as a test: no line of the promotion path pairs ``{{.Id}}`` with a digest."""
    offenders = [
        f"{path.relative_to(REPO_ROOT)}:{number}: {line.strip()}"
        for path in (PROMOTION_SCRIPT, CI_LOCAL_SCRIPT, CI_WORKFLOW, DEPLOY_WORKFLOW)
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if "{{.Id}}" in line and "digest" in line.lower()
    ]
    assert offenders == []


def test_workflow_deploy_renders_the_chart_only_from_a_recorded_digest() -> None:
    block = _job_block(DEPLOY_WORKFLOW, "deploy")
    verify = _step(block, "Warden verdict")
    render = _step(block, "helm template")
    step_id = re.search(r"(?m)^        id: (\S+)$", verify)
    assert step_id, "the verify step needs an id for its outputs"
    outputs = f"steps.{step_id.group(1)}.outputs"
    for name in IMAGE_ID_ENV.values():
        assert name in verify, f"the verify step is not given {name}"
    for output in ("platform_digest", "sidecar_digest", "mcp_host_digest"):
        assert f"{outputs}.{output}" in render, (
            f"the render step must take {output} from the verifier, which reads it from the artifact"
        )
    assert "inputs." not in render, (
        "the render step must not read a digest straight from an input"
    )
    assert f"{outputs}.by_digest" in render
    assert "a registry deploy needs a pushed digest" in render


def test_workflow_local_promotion_stage_passes_image_ids_as_image_ids() -> None:
    text = CI_LOCAL_SCRIPT.read_text(encoding="utf-8")
    stage = text.split("stage_promotion() {", 1)[1].split("\n  }\n", 1)[0]
    verifier_line = next(
        line
        for line in stage.splitlines()
        if "platform-deploy-verify-promotion.py" in line
    )
    for name in IMAGE_ID_ENV.values():
        assert f"{name}=" in verifier_line
    for name in DIGEST_ENV.values():
        assert f"{name}=" not in verifier_line, (
            f"the local stage pushes nothing, so it has no digest to pass as {name}"
        )
