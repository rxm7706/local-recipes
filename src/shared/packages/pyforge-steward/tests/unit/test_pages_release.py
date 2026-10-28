"""Story 102.5 (CAP-168): configure-pages is authoritative on every host, and the deployed site ships
as the ``pages-site.zip`` asset of the rolling ``pages-site`` pre-release.

AC1 and AC2 read ``.github/workflows/pages.yml`` as YAML; AC6 reads the protected-refs rulesets.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from pyforge.steward import pages

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree

REPO_ROOT = Path(__file__).resolve().parents[6]
PAGES_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pages.yml"
PROTECTED_REFS = REPO_ROOT / "docs" / "governance" / "rulesets" / "protected-refs.json"


def _workflow() -> dict:
    return yaml.safe_load(PAGES_WORKFLOW.read_text(encoding="utf-8"))


def _steps(job: str) -> list[dict]:
    return [step for step in _workflow()["jobs"][job]["steps"] if isinstance(step, dict)]


# --- AC1: the host env -------------------------------------------------------------------------


def test_ac1_no_step_runs_the_retired_host_env_exporter() -> None:
    for job in ("build", "deploy"):
        for step in _steps(job):
            assert "export_pages_host_env.py" not in str(step.get("run", "")), step.get("name")
    assert "export_pages_host_env" not in PAGES_WORKFLOW.read_text(encoding="utf-8")


def test_ac1_pages_check_reads_the_deploying_hosts_values() -> None:
    build = next(step for step in _steps("build") if "pages-check" in str(step.get("run", "")))
    assert build["env"] == {
        "SITE_URL": "${{ steps.pages.outputs.base_url }}",
        "PAGES_HOST_BASE_URL": "${{ steps.pages.outputs.base_url }}",
        "PAGES_HOST_BASE_PATH": "${{ steps.pages.outputs.base_path }}",
    }
    configure = next(step for step in _steps("build") if step.get("id") == "pages")
    assert str(configure["uses"]).startswith("actions/configure-pages@")


def test_ac1_the_flag_exports_stay_in_the_renamed_step() -> None:
    step = next(step for step in _steps("build") if step.get("name") == "Resolve build env (flags)")
    run = step["run"]
    assert 'python -m pyforge.herald.pages_env >> "$GITHUB_ENV"' in run  # herald Story 43.7: one export for its flags
    assert 'scripts/pages_artifact_download.py --flag-env >> "$GITHUB_ENV"' in run
    assert "env" not in step  # no host value reaches a flag export
    names = [s.get("name") for s in _steps("build")]
    assert not [name for name in names if name and "Resolve Pages host env" in name]


# --- AC2: the asset step ----------------------------------------------------------------------


def test_ac2_contents_write_is_the_deploy_jobs_alone() -> None:
    jobs = _workflow()["jobs"]
    assert jobs["deploy"]["permissions"] == {"pages": "write", "id-token": "write", "contents": "write"}
    assert jobs["build"]["permissions"]["contents"] == "read"
    assert _workflow()["permissions"]["contents"] == "read"


def test_ac2_the_asset_steps_follow_the_deploy_and_carry_the_gate() -> None:
    steps = _steps("deploy")
    deploy_at = next(i for i, step in enumerate(steps) if str(step.get("uses", "")).startswith("actions/deploy-pages@"))
    download_at = next(
        i for i, step in enumerate(steps) if str(step.get("uses", "")).startswith("actions/download-artifact@")
    )
    publish_at = next(i for i, step in enumerate(steps) if pages.RELEASE_ASSET in str(step.get("run", "")))
    assert deploy_at < download_at < publish_at
    for index in (download_at, publish_at):
        assert steps[index]["if"] == pages.RELEASE_ASSET_IF
    assert steps[download_at]["with"] == {"name": "pages-site", "path": "pages-site"}
    run = steps[publish_at]["run"]
    assert "pages-site.zip" in run
    assert re.search(r"gh release (create|upload) pages-site\b", run)
    assert "--clobber" in run
    assert "--prerelease" in run and '--target "$GITHUB_SHA"' in run
    assert "test -f pages-site/build.json" in run


def test_ac2_the_rolling_release_is_kept_and_its_tag_moved() -> None:
    """102.5's review: delete-then-create left no release (and no asset) whenever create failed. An
    existing release is kept: the tag moves to the deploying commit first (also a tag left without its
    release, which ``gh release create --target`` would adopt where it stands; lane-B re-review), the
    release's target follows, and the asset is replaced with ``--clobber``; only a first deploy creates
    the release."""
    run = next(step["run"] for step in _steps("deploy") if pages.RELEASE_ASSET in str(step.get("run", "")))
    # the release is never deleted; `gh release delete-asset` (Story 109.3's per-skill zips) is not that
    assert not re.search(r"gh release delete(?!-asset)", run) and "--cleanup-tag" not in run
    lines = [line.strip() for line in run.splitlines()]
    probe = lines.index('if gh api "repos/$GH_REPO/git/ref/tags/pages-site" >/dev/null 2>&1; then')
    move = lines.index(
        'gh api -X PATCH "repos/$GH_REPO/git/refs/tags/pages-site" -f sha="$GITHUB_SHA" -F force=true >/dev/null'
    )
    view = lines.index("if gh release view pages-site >/dev/null 2>&1; then")
    edit = lines.index('gh release edit pages-site --target "$GITHUB_SHA" --notes "$notes"')
    create = next(i for i, line in enumerate(lines) if line.startswith("gh release create pages-site --prerelease"))
    upload = lines.index('gh release upload pages-site "$RUNNER_TEMP/pages-site.zip" --clobber')
    fis = [i for i, line in enumerate(lines) if line == "fi"]
    assert probe < move < fis[0] < view < edit < lines.index("else") < create < fis[1] < upload


def test_ac2_the_gate_reads_the_build_jobs_exported_duty_flag() -> None:
    build = _workflow()["jobs"]["build"]
    assert build["outputs"]["pages_duty"] == "${{ steps.duty.outputs.pages_duty }}"
    duty = next(step for step in _steps("build") if step.get("id") == "duty")
    assert duty["run"] == 'echo "pages_duty=${PYFORGE_PAGES_DUTY:-0}" >> "$GITHUB_OUTPUT"'
    names = [step.get("name") or step.get("id") for step in _steps("build")]
    assert names.index("Resolve build env (flags)") < names.index("Carry the duty flag to the deploy job")
    # 102.5's review: the exact string, so a change to the flag clause in both the YAML and the
    # constant (``== '0'``, say) cannot leave every test green.
    assert pages.RELEASE_ASSET_IF == (
        "${{ needs.build.outputs.pages_duty == '1' && github.event_name != 'pull_request' }}"
    )


def test_ac2_the_site_artifact_uploads_for_a_pr_or_a_changed_tree() -> None:
    """102.5's review: a build whose tree did not change deploys nothing, so the six-hourly schedule of
    an unmoved tree uploads no 14-day copy of the whole site."""
    steps = _steps("build")
    upload_at = next(
        i for i, step in enumerate(steps) if str(step.get("uses", "")).startswith("actions/upload-artifact@")
    )
    upload = steps[upload_at]
    assert upload["with"]["name"] == "pages-site"
    assert upload["with"]["path"] == "docs-site/build/site"
    assert upload["if"] == "${{ github.event_name == 'pull_request' || steps.stamp.outputs.changed == 'true' }}"
    stamp_at = next(i for i, step in enumerate(steps) if step.get("id") == "stamp")
    assert stamp_at < upload_at  # the gate reads the stamp step's output
    # The deploy job, the one reader of this artifact, runs only on a changed tree.
    assert "needs.build.outputs.changed == 'true'" in _workflow()["jobs"]["deploy"]["if"]


_GH_CALL = re.compile(r"(?:^|[\s;(&|])gh\s+(?:api|run|release|workflow)\b")


def test_every_gh_step_names_the_host_and_carries_the_token() -> None:
    """GitHub Enterprise (102.4's and 102.5's reviews): a runner has no ``gh`` configuration, so every
    step that runs ``gh`` (directly, or through the artifact download script) exports ``GH_HOST`` from
    ``GITHUB_SERVER_URL`` and carries the job token as ``GH_TOKEN`` and ``GH_ENTERPRISE_TOKEN``, with
    ``GH_REPO``. That is what lets the enterprise copy run ``pages.yml`` unchanged."""
    host = 'export GH_HOST="${GITHUB_SERVER_URL#*://}"'
    found = []
    for job in ("build", "deploy"):
        for step in _steps(job):
            run = str(step.get("run", ""))
            if not (_GH_CALL.search(run) or "pages_artifact_download.py --workflow" in run):
                continue
            found.append(step.get("name"))
            assert host in run, step.get("name")
            call = _GH_CALL.search(run)
            first = min(i for i in (call.start() if call else -1, run.find("pages_artifact_download.py")) if i >= 0)
            assert run.index(host) < first, step.get("name")  # the host is named before gh runs
            env = step.get("env") or {}
            assert env.get("GH_TOKEN") == env.get("GH_ENTERPRISE_TOKEN") == "${{ github.token }}", step.get("name")
            assert env.get("GH_REPO") == "${{ github.repository }}", step.get("name")
    assert found == [
        "Download the Kedro-Viz export artifact",
        "Download the Vizro static export artifact",
        "Publish the site as the pages-site release asset",
    ]


@pytest.mark.parametrize(
    ("pages_duty", "event_name", "runs"),
    [
        ("1", "push", True),
        ("1", "workflow_dispatch", True),
        ("1", "schedule", True),
        ("1", "pull_request", False),
        ("0", "push", False),
        ("", "push", False),
    ],
)
def test_release_asset_runs_evaluates_the_gate(pages_duty: str, event_name: str, runs: bool) -> None:
    assert pages.release_asset_runs(pages_duty=pages_duty, event_name=event_name) is runs


# --- Story 109.3: the marketplace flag and the per-skill zips (its review of 2026-10-28, rows 6 and 9) ---------


def test_the_marketplace_flag_reaches_the_build_env_beside_heralds_lines() -> None:
    step = next(step for step in _steps("build") if step.get("name") == "Resolve build env (flags)")
    lines = [line.strip() for line in step["run"].splitlines() if line.strip()]
    assert lines == [
        'pixi run --frozen -e pyforge-guild python -m pyforge.herald.pages_env >> "$GITHUB_ENV"',
        'pixi run --frozen -e pyforge-guild python scripts/pages_artifact_download.py --flag-env >> "$GITHUB_ENV"',
        'pixi run --frozen -e pyforge-guild python -m pyforge.steward.marketplace_pages --flag-env >> "$GITHUB_ENV"',
    ]
    assert "PYFORGE_ENVIRONMENT" not in PAGES_WORKFLOW.read_text(encoding="utf-8").replace("# PYFORGE_ENVIRONMENT", "")


def _zip_step_lines() -> list[str]:
    run = next(step["run"] for step in _steps("deploy") if pages.RELEASE_ASSET in str(step.get("run", "")))
    return [line.strip() for line in run.splitlines()]


def test_the_per_skill_zips_are_built_first_then_stale_assets_pruned_then_uploaded() -> None:
    """Loop 2, row 24: every zip is built before the release is touched; the asset listing's failure fails the
    step; only per-skill names not in the new set are deleted; ``pages-site.zip`` is never deleted."""
    lines = _zip_step_lines()
    zipped = next(line for line in lines if line.startswith('(cd "$stage" && zip -qry'))
    assert zipped == (
        '(cd "$stage" && zip -qry "$outdir/$name.zip" "$name" -i "$name/SKILL.md" "$name/steps.md" '
        '"$name/listing.yaml" "$name/references/*" -x \'*/.*\')'
    )
    assert 'cp -R "$dir/." "$stage/$name/"' in lines
    assert '(cd "$outdir" && sha256sum "$name.zip" > "$name.zip.sha256")' in lines
    listing = lines.index("assets=$(gh release view pages-site --json assets --jq '.assets[].name') || exit 1")
    delete = lines.index(
        '*.zip|*.zip.sha256) [ -f "$outdir/$asset" ] || gh release delete-asset pages-site "$asset" --yes ;;'
    )
    upload = lines.index('gh release upload pages-site "$outdir"/* --clobber')
    site_upload = lines.index('gh release upload pages-site "$RUNNER_TEMP/pages-site.zip" --clobber')
    assert "pages-site.zip) ;;" in lines
    assert site_upload < lines.index(zipped) < listing < delete < upload
    assert "for asset in $(gh release view" not in " ".join(lines)  # a failed listing fails the step
    assert 'zip -qr "$zip_path" .' not in " ".join(lines)  # the old form zipped the folder's contents loose


def test_the_zip_allowlist_is_the_mounts_and_the_validators() -> None:
    """Loop 2, row 23: one allowlist in three places (the workflow's -i list, ``marketplace.ts``, ``SKILL_FILES``)."""
    from pyforge.steward.marketplace_pages import REFERENCES_DIR, SKILL_FILES

    zipped = next(line for line in _zip_step_lines() if line.startswith('(cd "$stage" && zip -qry'))
    patterns = re.findall(r'-i ((?:"\$name/[^"]+" ?)+)', zipped)[0].split()
    assert patterns == [f'"$name/{name}"' for name in SKILL_FILES] + [f'"$name/{REFERENCES_DIR}/*"']
    ts = (REPO_ROOT / "docs-site" / "src" / "lib" / "marketplace.ts").read_text(encoding="utf-8")
    assert re.search(r"export const SKILL_FILES: readonly string\[\] = \[([^\]]+)\];", ts)
    ts_files = [
        name.strip().strip("'\"")
        for name in re.search(r"SKILL_FILES: readonly string\[\] = \[([^\]]+)\]", ts).group(1).split(",")
    ]
    assert ts_files == list(SKILL_FILES)
    assert f"export const SKILL_REFERENCES_DIR = '{REFERENCES_DIR}';" in ts


@pytest.mark.skipif(shutil.which("zip") is None or shutil.which("unzip") is None, reason="zip and unzip on PATH")
def test_the_workflows_zip_line_ships_the_folder_and_only_the_allowlist(tmp_path: Path) -> None:
    """Loop 2, row 24: the workflow's own zip line, run over a planted folder, holds ``<scope>-<slug>/`` at the
    root with the shipped files, carries nested ``references/``, and drops a stray file, a dot entry and a
    symlink; the checksum line verifies."""
    zipped = next(line for line in _zip_step_lines() if line.startswith('(cd "$stage" && zip -qry'))
    checksum = '(cd "$outdir" && sha256sum "$name.zip" > "$name.zip.sha256")'
    stage = tmp_path / "stage"
    name = "mason-environment"
    folder = stage / name
    (folder / "references" / "deep").mkdir(parents=True)
    for rel, text in (
        ("SKILL.md", "# skill\n"),
        ("steps.md", "# steps\n"),
        ("listing.yaml", "id: mason/environment\n"),
        ("references/deep/more.md", "# more\n"),
        ("notes.txt", "stray\n"),
        (".DS_Store", "x"),
        ("references/.hidden", "x"),
    ):
        (folder / rel).write_text(text, encoding="utf-8")
    (tmp_path / "outside.txt").write_text("secret\n", encoding="utf-8")
    (folder / "references" / "link.md").symlink_to(tmp_path / "outside.txt")
    outdir = tmp_path / "out"
    outdir.mkdir()
    env = {**os.environ, "stage": str(stage), "name": name, "outdir": str(outdir)}
    for line in (zipped, checksum):
        done = subprocess.run(
            ["bash", "-euo", "pipefail", "-c", line], env=env, capture_output=True, text=True, check=False
        )
        assert done.returncode == 0, done.stderr
    listed = subprocess.run(
        ["unzip", "-Z1", str(outdir / f"{name}.zip")], capture_output=True, text=True, check=True
    ).stdout.split()
    assert sorted(entry for entry in listed if not entry.endswith("/")) == [
        f"{name}/SKILL.md",
        f"{name}/listing.yaml",
        f"{name}/references/deep/more.md",
        f"{name}/references/link.md",  # stored as a link (-y), never the target's bytes
        f"{name}/steps.md",
    ]
    extracted = tmp_path / "extracted"
    subprocess.run(["unzip", "-q", str(outdir / f"{name}.zip"), "-d", str(extracted)], check=True)
    assert (extracted / name / "references" / "link.md").is_symlink()
    assert not (extracted / name / "notes.txt").exists()
    verify = subprocess.run(
        ["sha256sum", "-c", f"{name}.zip.sha256"], cwd=outdir, capture_output=True, text=True, check=False
    )
    assert verify.returncode == 0, verify.stdout + verify.stderr


# --- AC6: protected refs ----------------------------------------------------------------------


def _pattern(glob: str) -> re.Pattern[str]:
    """GitHub ruleset ``ref_name`` globs: ``**`` spans slashes, ``*`` does not."""
    parts = re.split(r"(\*\*|\*)", glob)
    body = "".join(".*" if part == "**" else "[^/]*" if part == "*" else re.escape(part) for part in parts)
    return re.compile(f"^{body}$")


def test_ac6_the_rolling_tag_matches_no_protected_pattern() -> None:
    document = json.loads(PROTECTED_REFS.read_text(encoding="utf-8"))
    patterns = [
        glob
        for ruleset in document["rulesets"]
        for glob in ruleset.get("conditions", {}).get("ref_name", {}).get("include", [])
    ]
    assert "refs/tags/archive/**" in patterns  # the read is real
    tag_ref = f"refs/tags/{pages.RELEASE_TAG}"
    assert not [glob for glob in patterns if _pattern(glob).match(tag_ref)]
    assert _pattern("refs/tags/archive/**").match("refs/tags/archive/x")  # the matcher is alive


def test_ac6_the_rolling_tag_is_not_a_version() -> None:
    assert pages.RELEASE_TAG == "pages-site"
    assert not re.fullmatch(r"v?\d{4}\.\d{1,2}\.\d{1,2}(\.\d+)?", pages.RELEASE_TAG)
