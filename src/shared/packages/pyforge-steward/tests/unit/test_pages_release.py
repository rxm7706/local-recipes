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
    upload = lines.index('gh release upload pages-site "${uploads[@]}" --clobber')
    fis = [i for i, line in enumerate(lines) if line == "fi" and i > probe]  # the zip block's own fi sits before
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


def test_the_per_skill_zips_are_built_first_then_stale_assets_pruned_then_everything_uploaded() -> None:
    """Loop 2, row 24; loop 3, rows 49 and 50: every zip is built before the release is touched (before the tag
    moves, so a failing zip leaves the previous deploy whole); the asset listing's failure fails the step; the
    listing is read line by line and only per-skill names (``<scope>-<slug>.zip`` or ``.zip.sha256``) not in the
    new set are deleted, never ``pages-site.zip`` or any other asset; then the site zip and the skill set go up in
    one upload, so a new site never sits beside stale skill zips."""
    lines = _zip_step_lines()
    zipped = next(line for line in lines if line.startswith('(cd "$stage" && zip -qr'))
    assert zipped == (
        '(cd "$stage" && zip -qr "$outdir/$name.zip" "$name" -i "$name/SKILL.md" "$name/steps.md" '
        '"$name/listing.yaml" "$name/references/*" -x \'*/.*\')'
    )
    assert "zip -qry" not in " ".join(lines)  # no -y: a symlink fails the step before zip runs (row 50)
    assert 'cp -R "$dir/." "$stage/$name/"' in lines
    assert '(cd "$outdir" && sha256sum "$name.zip" > "$name.zip.sha256")' in lines
    name_refusal = lines.index(
        'if [ "$name" = "pages-site" ]; then echo "::error::$name: a skill folder named like the site asset"; exit 1; fi'
    )
    symlink_refusal = lines.index(
        'if [ -n "$(find "$stage/$name" -type l -print -quit)" ]; '
        'then echo "::error::$name: a symlink in the skill folder"; exit 1; fi'
    )
    size_refusal = lines.index(
        'if [ -n "$(find "$stage/$name" -type f -size +1048576c -print -quit)" ]; '
        'then echo "::error::$name: a file over 1 MiB"; exit 1; fi'
    )
    folder_refusal = lines.index(
        "if ! find \"$stage/$name\" -type f -printf '%s\\n' | awk -v cap=4194304 '{ s += $1 } END { exit (s > cap) ? 1 : 0 }'; "
        'then echo "::error::$name: the folder ships over 4 MiB"; exit 1; fi'
    )
    assert name_refusal < lines.index('cp -R "$dir/." "$stage/$name/"') < symlink_refusal < size_refusal
    assert size_refusal < folder_refusal < lines.index(zipped)
    tag_move = lines.index(
        'gh api -X PATCH "repos/$GH_REPO/git/refs/tags/pages-site" -f sha="$GITHUB_SHA" -F force=true >/dev/null'
    )
    listing = lines.index("assets=$(gh release view pages-site --json assets --jq '.assets[].name') || exit 1")
    loop = lines.index("while IFS= read -r asset; do")
    delete = lines.index(
        'gh release delete-asset pages-site "$asset" --yes </dev/null'
    )  # row 74: never the loop's stdin
    loop_end = lines.index('done <<< "$assets"')
    upload = lines.index('gh release upload pages-site "${uploads[@]}" --clobber')
    assert lines.index(zipped) < tag_move < listing < loop < delete < loop_end < upload
    assert "pages-site.zip|pages-site.zip.sha256) ;;" in lines  # row 60: the site asset and its sidecar shielded
    # the prune arm: the per-skill shape, membership against the new set, nothing else (row 49)
    assert (
        '*) if [[ "$asset" =~ ^[a-z0-9][a-z0-9-]*-[a-z0-9][a-z0-9-]*\\.zip(\\.sha256)?$ ]] '
        '&& [ ! -f "$outdir/$asset" ]; then'
    ) in lines
    assert "*.zip|*.zip.sha256)" not in " ".join(lines)
    assert "for asset in $assets" not in " ".join(lines)  # word-splitting the listing (row 49)
    assert "for asset in $(gh release view" not in " ".join(lines)  # a failed listing fails the step
    # one upload after the prune: the site zip and the skill set together (row 50)
    assert 'uploads=("$RUNNER_TEMP/pages-site.zip" "$outdir"/*)' in lines
    assert (
        lines.index("shopt -s nullglob") < lines.index('uploads=("$RUNNER_TEMP/pages-site.zip" "$outdir"/*)') < upload
    )
    assert [line for line in lines if line.startswith("gh release upload")] == [
        'gh release upload pages-site "${uploads[@]}" --clobber'
    ]
    assert 'zip -qr "$zip_path" .' not in " ".join(lines)  # the old form zipped the folder's contents loose


def _deleted(asset: str) -> list[str]:
    return [f"release delete-asset pages-site {asset} --yes"]


@pytest.mark.parametrize(
    ("asset", "expected_calls"),
    [
        ("mason-environment.zip", _deleted("mason-environment.zip")),
        ("mason-environment.zip.sha256", _deleted("mason-environment.zip.sha256")),
        ("a-b-c.zip", _deleted("a-b-c.zip")),
        ("pages-site.zip", []),  # the site zip, the first case arm
        ("pages-site.zip.sha256", []),  # loop 4, row 60: its sidecar, should one ever exist
        ("kept-one.zip", []),  # in the new set (planted in $outdir)
        ("release-notes.txt", []),  # not a zip
        ("Mason-Env.zip", []),  # outside the slug grammar
        ("nohyphen.zip", []),  # not <scope>-<slug>
        ("my notes.zip", []),  # a space: not the shape, and never split into two words
        ("x.zip.sha256.bak", []),
        ("", []),
    ],
)
def test_the_prune_loop_deletes_only_per_skill_names_not_in_the_new_set(
    tmp_path: Path, asset: str, expected_calls: list[str]
) -> None:
    """Loop 3, row 49: the workflow's own prune loop, run over a listing with ``gh`` stubbed, deletes exactly the
    per-skill assets that are not in ``$outdir`` (the expectation is the row's own, loop 4 row 80)."""
    lines = _zip_step_lines()
    start = lines.index("while IFS= read -r asset; do")
    end = lines.index('done <<< "$assets"')
    loop = "\n".join(lines[start : end + 1])
    outdir = tmp_path / "out"
    outdir.mkdir()
    (outdir / "kept-one.zip").write_bytes(b"x")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "gh.log"
    (bin_dir / "gh").write_text(f'#!/bin/bash\nprintf \'%s\\n\' "$*" >> "{log}"\n', encoding="utf-8")
    (bin_dir / "gh").chmod(0o755)
    script = f"assets={json.dumps(asset)}\n{loop}\n"
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "outdir": str(outdir)}
    done = subprocess.run(
        ["bash", "-euo", "pipefail", "-c", script], env=env, capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr
    calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    assert calls == expected_calls


def test_the_prune_loop_never_hands_its_listing_to_the_delete(tmp_path: Path) -> None:
    """Loop 5, row 91 (row 74's redirect, observed): a ``gh`` that reads its stdin would eat the rest of the listing
    the loop reads, so only the first stale asset would be deleted; ``</dev/null`` on the delete keeps every line."""
    lines = _zip_step_lines()
    start = lines.index("while IFS= read -r asset; do")
    end = lines.index('done <<< "$assets"')
    loop = "\n".join(lines[start : end + 1])
    outdir = tmp_path / "out"
    outdir.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "gh.log"
    (bin_dir / "gh").write_text(f'#!/bin/bash\ncat >/dev/null\nprintf \'%s\\n\' "$*" >> "{log}"\n', encoding="utf-8")
    (bin_dir / "gh").chmod(0o755)
    script = f"assets=$'a-b.zip\\nc-d.zip\\ne-f.zip.sha256'\n{loop}\n"
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "outdir": str(outdir)}
    done = subprocess.run(
        ["bash", "-euo", "pipefail", "-c", script], env=env, capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr
    assert log.read_text(encoding="utf-8").splitlines() == [
        *_deleted("a-b.zip"),
        *_deleted("c-d.zip"),
        *_deleted("e-f.zip.sha256"),
    ]


def test_the_zip_allowlist_is_the_mounts_and_the_validators() -> None:
    """Loop 2, row 23; loop 3, row 48: one allowlist, one suffix set and two caps in three places (the workflow's
    -i list and refusals, ``marketplace.ts``, the validator's constants)."""
    from pyforge.steward.marketplace_pages import (
        MAX_SHIPPED_FILE_BYTES,
        MAX_SHIPPED_FOLDER_BYTES,
        REFERENCES_DIR,
        SHIPPED_TEXT_SUFFIXES,
        SKILL_FILES,
    )

    lines = _zip_step_lines()
    zipped = next(line for line in lines if line.startswith('(cd "$stage" && zip -qr'))
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
    ts_suffixes = [
        name.strip().strip("'\"")
        for name in re.search(r"SHIPPED_TEXT_SUFFIXES: readonly string\[\] = \[([^\]]+)\]", ts).group(1).split(",")
    ]
    assert sorted(ts_suffixes) == sorted(SHIPPED_TEXT_SUFFIXES)
    assert f"export const MAX_SHIPPED_FILE_BYTES = {MAX_SHIPPED_FILE_BYTES};" in ts
    assert f"export const MAX_SHIPPED_FOLDER_BYTES = {MAX_SHIPPED_FOLDER_BYTES};" in ts
    # the workflow's refusals name the same caps and the same suffix set, matched without regard to case as the
    # validator (.suffix.lower()) and the mount (toLowerCase()) do (loop 4, row 59); the site asset is never a name
    assert f'find "$stage/$name" -type f -size +{MAX_SHIPPED_FILE_BYTES}c -print -quit' in " ".join(lines)
    assert f"awk -v cap={MAX_SHIPPED_FOLDER_BYTES} " in " ".join(lines)
    suffix_line = next(line for line in lines if 'find "$stage/$name/references" -type f !' in line)
    assert sorted(re.findall(r"-iname '\*(\.[a-z]+)'", suffix_line)) == sorted(SHIPPED_TEXT_SUFFIXES)
    assert "-name '*." not in suffix_line  # every suffix pattern is -iname
    assert f'if [ "$name" = "{pages.RELEASE_TAG}" ]; then' in " ".join(lines)
    assert f"export const RELEASE_ASSET_STEM = '{pages.RELEASE_TAG}';" in ts


def _refusal_lines() -> list[str]:
    lines = _zip_step_lines()
    return [
        line
        for line in lines
        if line.startswith(
            ('if [ -n "$(find "$stage/$name', 'if ! find "$stage/$name"', 'if [ "$name" = "pages-site" ]')
        )
    ]


@pytest.mark.skipif(shutil.which("zip") is None, reason="zip on PATH")
def test_the_workflow_refuses_a_skill_folder_named_like_the_site_asset(tmp_path: Path) -> None:
    """Loop 4, row 60: a ``skills/pages/site/`` folder would yield ``pages-site.zip``; the validator refuses the
    listing and the step refuses the name before anything is staged."""
    lines = _zip_step_lines()
    zipped = next(line for line in lines if line.startswith('(cd "$stage" && zip -qr'))
    stage = _plant_stage(tmp_path, "pages-site")
    outdir = tmp_path / "out"
    outdir.mkdir()
    env = {**os.environ, "stage": str(stage), "name": "pages-site", "outdir": str(outdir)}
    done = _run_step_lines([*_refusal_lines(), zipped], env)
    assert done.returncode == 1, done.stderr + done.stdout
    assert "::error::pages-site: a skill folder named like the site asset" in done.stdout
    assert not (outdir / "pages-site.zip").exists()


def _plant_stage(tmp_path: Path, name: str = "mason-environment", *, references: bool = True) -> Path:
    stage = tmp_path / "stage"
    folder = stage / name
    folder.mkdir(parents=True)
    files = [
        ("SKILL.md", "# skill\n"),
        ("steps.md", "# steps\n"),
        ("listing.yaml", "id: mason/environment\n"),
        ("notes.txt", "stray\n"),
        (".DS_Store", "x"),
    ]
    if references:
        (folder / "references" / "deep").mkdir(parents=True)
        files += [
            ("references/deep/more.md", "# more\n"),
            ("references/NOTES.MD", "# upper-case suffix (loop 4, row 59)\n"),
            ("references/.hidden", "x"),
        ]
    for rel, text in files:
        (folder / rel).write_text(text, encoding="utf-8")
    return stage


def _run_step_lines(lines: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-euo", "pipefail", "-c", "\n".join(lines)], env=env, capture_output=True, text=True, check=False
    )


@pytest.mark.skipif(shutil.which("zip") is None or shutil.which("unzip") is None, reason="zip and unzip on PATH")
def test_the_workflows_zip_lines_ship_the_folder_and_only_the_allowlist(tmp_path: Path) -> None:
    """Loop 2, row 24; loop 3, row 50: the workflow's own refusal, zip and checksum lines, run over a planted folder,
    hold ``<scope>-<slug>/`` at the root with the shipped files, carry nested ``references/``, drop a stray file
    and a dot entry, and the checksum line verifies."""
    lines = _zip_step_lines()
    zipped = next(line for line in lines if line.startswith('(cd "$stage" && zip -qr'))
    checksum = '(cd "$outdir" && sha256sum "$name.zip" > "$name.zip.sha256")'
    name = "mason-environment"
    stage = _plant_stage(tmp_path)
    outdir = tmp_path / "out"
    outdir.mkdir()
    env = {**os.environ, "stage": str(stage), "name": name, "outdir": str(outdir)}
    done = _run_step_lines([*_refusal_lines(), zipped, checksum], env)
    assert done.returncode == 0, done.stderr + done.stdout
    listed = subprocess.run(
        ["unzip", "-Z1", str(outdir / f"{name}.zip")], capture_output=True, text=True, check=True
    ).stdout.split()
    assert sorted(entry for entry in listed if not entry.endswith("/")) == [
        f"{name}/SKILL.md",
        f"{name}/listing.yaml",
        f"{name}/references/NOTES.MD",
        f"{name}/references/deep/more.md",
        f"{name}/steps.md",
    ]
    extracted = tmp_path / "extracted"
    subprocess.run(["unzip", "-q", str(outdir / f"{name}.zip"), "-d", str(extracted)], check=True)
    assert not (extracted / name / "notes.txt").exists()
    verify = subprocess.run(
        ["sha256sum", "-c", f"{name}.zip.sha256"], cwd=outdir, capture_output=True, text=True, check=False
    )
    assert verify.returncode == 0, verify.stdout + verify.stderr


@pytest.mark.skipif(shutil.which("zip") is None or shutil.which("unzip") is None, reason="zip and unzip on PATH")
def test_the_workflows_zip_lines_run_clean_over_the_committed_shape_with_no_references(tmp_path: Path) -> None:
    """Loop 4, row 71: the three committed skills carry no ``references/``; the refusal, zip and checksum lines run
    clean over that shape and the zip holds exactly the three files."""
    lines = _zip_step_lines()
    zipped = next(line for line in lines if line.startswith('(cd "$stage" && zip -qr'))
    checksum = '(cd "$outdir" && sha256sum "$name.zip" > "$name.zip.sha256")'
    name = "mason-environment"
    stage = _plant_stage(tmp_path, references=False)
    outdir = tmp_path / "out"
    outdir.mkdir()
    env = {**os.environ, "stage": str(stage), "name": name, "outdir": str(outdir)}
    done = _run_step_lines([*_refusal_lines(), zipped, checksum], env)
    assert done.returncode == 0, done.stderr + done.stdout
    listed = subprocess.run(
        ["unzip", "-Z1", str(outdir / f"{name}.zip")], capture_output=True, text=True, check=True
    ).stdout.split()
    assert sorted(entry for entry in listed if not entry.endswith("/")) == [
        f"{name}/SKILL.md",
        f"{name}/listing.yaml",
        f"{name}/steps.md",
    ]


@pytest.mark.skipif(shutil.which("zip") is None, reason="zip on PATH")
@pytest.mark.parametrize(
    ("plant", "message"),
    [
        (
            lambda folder, outside: (folder / "references" / "link.md").symlink_to(outside),
            "a symlink in the skill folder",
        ),
        (lambda folder, outside: (folder / "linked-dir").symlink_to(outside.parent), "a symlink in the skill folder"),
        (lambda folder, outside: (folder / "steps.md").write_bytes(b"x" * (1_048_576 + 1)), "a file over 1 MiB"),
        (
            lambda folder, outside: (folder / "references" / "pic.png").write_bytes(b"\x89PNG"),
            "references/ ships text files only",
        ),
        (
            lambda folder, outside: (folder / "references" / "deep" / "tool.whl").write_bytes(b"x"),
            "references/ ships text files only",
        ),
        (
            lambda folder, outside: [
                (folder / "references" / f"{n}.md").write_bytes(b"x" * (1_048_576 - 1)) for n in range(5)
            ],
            "the folder ships over 4 MiB",  # loop 4, row 75: the validator's folder cap, at the zip step too
        ),
    ],
)
def test_the_workflow_refuses_a_symlink_an_oversized_file_and_a_binary_reference_before_zip(
    tmp_path: Path, plant, message: str
) -> None:
    """Loop 3, rows 48 and 50; loop 4, row 75: the zip step fails, naming the breach, rather than storing a link
    entry, an oversized file, an over-cap folder or a binary under ``references/``; nothing is zipped."""
    lines = _zip_step_lines()
    zipped = next(line for line in lines if line.startswith('(cd "$stage" && zip -qr'))
    name = "mason-environment"
    stage = _plant_stage(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("secret\n", encoding="utf-8")
    plant(stage / name, outside)
    outdir = tmp_path / "out"
    outdir.mkdir()
    env = {**os.environ, "stage": str(stage), "name": name, "outdir": str(outdir)}
    done = _run_step_lines([*_refusal_lines(), zipped], env)
    assert done.returncode == 1, done.stderr + done.stdout
    assert f"::error::{name}: {message}" in done.stdout
    assert not (outdir / f"{name}.zip").exists()


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
