#!/usr/bin/env python3
"""
pr_artifacts.py — download conda-forge PR build artifacts from Azure DevOps.

Resolves a staged-recipes or feedstock PR (number or URL) → Azure
`buildId` via `gh pr checks`, anonymously lists + streams the
`conda_pkgs_*` ZIP artifacts via the Azure Build Artifacts REST API,
and extracts them into a local `file://` mamba channel layout at
`build_artifacts/pr/<pr-number>/<buildId>/extracted/`.

Read-only against the public `conda-forge/feedstock-builds` Azure
project (no PAT, no `az login`). Idempotent (manifest-keyed cache);
`--force` re-fetches.

See spec: ../../../_bmad-output/projects/local-recipes/implementation-artifacts/spec-cfe-pr-artifact-downloader-v8.14.0.md
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _http import fetch_to_file_resumable, make_request, open_url  # noqa: E402


_PR_URL_RE = re.compile(
    r"^https?://github\.com/(?P<repo>[^/]+/[^/]+)/pull/(?P<pr>\d+)(?:[/?#].*)?$"
)
_BUILD_ID_RE = re.compile(r"buildId=(\d+)")
_AZURE_ARTIFACTS_URL = (
    "https://dev.azure.com/conda-forge/feedstock-builds/_apis/build/builds/"
    "{build_id}/artifacts?api-version=7.1"
)
_DEFAULT_CONDA_PKGS_RE = re.compile(r"^conda_pkgs_(linux|osx|win)$")
_PLATFORM_FROM_NAME = {
    "conda_pkgs_linux": "linux-64",
    "conda_pkgs_osx": "osx-64",
    "conda_pkgs_win": "win-64",
}


def parse_pr_ref(ref: str, default_repo: str = "conda-forge/staged-recipes") -> tuple[str, int]:
    """Parse a PR reference into `(repo, pr_number)`.

    Accepts:
      * bare digits ("33693")           → (default_repo, 33693)
      * GitHub PR URL                   → (parsed owner/repo, parsed number)

    Raises `ValueError` on anything else.
    """
    ref = ref.strip()
    if ref.isdigit():
        return default_repo, int(ref)
    m = _PR_URL_RE.match(ref)
    if m:
        return m.group("repo"), int(m.group("pr"))
    raise ValueError(
        f"Cannot parse PR ref {ref!r}: expected a bare number "
        f"(e.g. 33693) or a GitHub PR URL "
        f"(e.g. https://github.com/conda-forge/staged-recipes/pull/33693)."
    )


def _gh_pr_checks(pr: int, repo: str, *, timeout: int = 60) -> list[dict[str, Any]]:
    """Invoke `gh pr checks` and return the parsed JSON rows.

    Separated from `resolve_build_ids` so tests can monkeypatch the
    subprocess boundary cleanly. `timeout` (default 60 s) bounds the
    subprocess so an auth-prompt hang or stalled network surfaces as a
    clean RuntimeError instead of an indefinite block.
    """
    try:
        result = subprocess.run(
            [
                "gh", "pr", "checks", str(pr),
                "--repo", repo,
                "--json", "name,link,bucket,state",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "gh CLI not found on PATH. Install from https://cli.github.com "
            "and run `gh auth login`."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"gh pr checks {pr} --repo {repo} timed out after {timeout}s "
            f"(network stall or auth prompt). Re-run after verifying "
            f"`gh auth status`."
        )
    if result.returncode != 0:
        raise RuntimeError(
            f"gh pr checks {pr} --repo {repo} failed (rc={result.returncode}): "
            f"{result.stderr.strip()}"
        )
    try:
        return json.loads(result.stdout or "[]")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"gh returned non-JSON output: {e}; stdout={result.stdout!r}")


def _check_name_matches(row_name: str, repo: str, override: str | None) -> bool:
    """Decide whether a `gh pr checks` row's `name` is the Azure build row.

    Resolution order:
      1. Explicit `--check-name` override (case-insensitive equality).
      2. staged-recipes repo → row name == "staged-recipes" (case-insensitive).
      3. feedstock repo (`*-feedstock`) → row name == `<pkg>-feedstock` (case-insensitive).
      4. Unknown repo shape → returns False; caller must pass `--check-name`.

    Comparisons are case-insensitive because Azure / GitHub display names
    occasionally drift in capitalisation. The unknown-repo permissive
    substring fallback was removed in v8.14.0-patch (post-review) because
    it risked false-positive matches across unrelated check rows.
    """
    if override is not None:
        return row_name.lower() == override.lower()
    repo_short = repo.rsplit("/", 1)[-1].lower()
    row_lower = row_name.lower()
    if repo_short == "staged-recipes":
        return row_lower == "staged-recipes"
    if repo_short.endswith("-feedstock"):
        return row_lower == repo_short
    return False


def resolve_build_ids(
    pr: int,
    repo: str = "conda-forge/staged-recipes",
    check_name: str | None = None,
    all_runs: bool = False,
) -> list[int]:
    """Resolve a PR ref → one or more Azure DevOps `buildId`s.

    Returns build IDs in descending order (newest first). `all_runs=False`
    keeps only the highest. Raises `LookupError` when no Azure build row
    is found — the CLI translates this into a clean exit-1 message.
    """
    rows = _gh_pr_checks(pr, repo)
    candidate_ids: set[int] = set()
    for row in rows:
        name = row.get("name", "")
        link = row.get("link", "") or ""
        if not _check_name_matches(name, repo, check_name):
            continue
        for m in _BUILD_ID_RE.finditer(link):
            candidate_ids.add(int(m.group(1)))
    if not candidate_ids:
        raise LookupError(
            f"No Azure build found on PR {pr} ({repo}); CI may still be "
            f"pending. Re-run when checks complete."
        )
    ordered = sorted(candidate_ids, reverse=True)
    return ordered if all_runs else [ordered[0]]


def list_azure_artifacts(
    build_id: int,
    include_all: bool = False,
    *,
    timeout: int = 60,
) -> list[dict[str, Any]]:
    """List published artifacts for an Azure DevOps `buildId`.

    Anonymous read against the public `conda-forge/feedstock-builds`
    project — no PAT, no `az login`. By default filters to
    `conda_pkgs_(linux|osx|win)` (the documented conda-forge naming);
    `include_all=True` returns the raw list.

    Each returned dict carries: `name`, `download_url`, `size`,
    `platform` (mapped from name when known, else None), `raw` (the
    untouched Azure value-item for downstream inspection).
    """
    url = _AZURE_ARTIFACTS_URL.format(build_id=build_id)
    req = make_request(
        url,
        extra_headers={"Accept": "application/json"},
        skip_auth=True,  # public Azure project; never leak JFROG_API_KEY
    )
    with open_url(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    # Azure DevOps anonymous endpoints sometimes return an error envelope
    # with HTTP 200 (e.g. retention-purged builds). Surface it explicitly
    # rather than silently reporting "no artifacts".
    if not isinstance(payload, dict) or "value" not in payload:
        msg = payload.get("message") if isinstance(payload, dict) else None
        raise RuntimeError(
            f"Azure returned an unexpected response shape for buildId={build_id}: "
            f"{msg or payload!r}"
        )
    rows = payload.get("value") or []
    out: list[dict[str, Any]] = []
    for item in rows:
        name = item.get("name", "")
        if not include_all and not _DEFAULT_CONDA_PKGS_RE.match(name):
            continue
        resource = item.get("resource") or {}
        out.append(
            {
                "name": name,
                "download_url": resource.get("downloadUrl"),
                "size": _coerce_size(resource.get("properties", {}).get("artifactsize")),
                "platform": _PLATFORM_FROM_NAME.get(name),
                "raw": item,
            }
        )
    return out


def _coerce_size(raw: Any) -> int | None:
    """Azure's `artifactsize` is a string of digits; coerce safely."""
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def download_artifact(
    artifact: dict[str, Any],
    target_dir: str | Path,
    *,
    timeout: int = 600,
) -> Path:
    """Stream-download one artifact ZIP into `target_dir/<name>.zip`.

    Uses `_http.fetch_to_file_resumable` for `.part`+atomic-rename
    semantics. After the stream completes, validates the on-disk file's
    ZIP integrity: opens it with `zipfile.ZipFile` and runs `testzip()`
    which CRC-validates every member. Raises `RuntimeError` on a
    corrupt/truncated ZIP and leaves the bad `.zip` in place for forensics.

    Azure's `artifact["size"]` is the artifact's logical/content size
    (sum of contained files), not the on-demand ZIP-stream size, so the
    two routinely diverge (PR #33693 buildId 1536673:
    declared 85,000,797 vs delivered 89,492,340; zip was valid). The
    integrity check catches actual truncation/corruption without
    rejecting valid downloads whose declared metadata is stale.
    """
    name = artifact["name"]
    url = artifact["download_url"]
    if not url:
        raise ValueError(f"Artifact {name!r} has no downloadUrl")
    target = Path(target_dir) / f"{name}.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    fetch_to_file_resumable(
        target,
        url,
        timeout=timeout,
        skip_auth=True,  # see list_azure_artifacts
    )
    try:
        with zipfile.ZipFile(target) as zf:
            bad_member = zf.testzip()
    except zipfile.BadZipFile as exc:
        raise RuntimeError(
            f"Corrupt ZIP for {name}: {exc}. The .zip was left at "
            f"{target} for forensics."
        ) from exc
    if bad_member is not None:
        raise RuntimeError(
            f"CRC failure in {name}: member {bad_member!r} is corrupt. "
            f"The .zip was left at {target} for forensics."
        )
    return target


# ── extract + manifest ─────────────────────────────────────────────────────

_AZURE_BUILD_RESULT_URL = (
    "https://dev.azure.com/conda-forge/feedstock-builds/_build/results?buildId={build_id}"
)


def extract_zip(
    zip_path: str | Path,
    dest: str | Path,
    *,
    platform: str | None = None,
    platforms: list[str] | None = None,
) -> list[str]:
    """Extract one Azure `conda_pkgs_<job>.zip` into `dest/<platform>/`.

    Each Azure artifact ZIP ships its files under a single wrapper dir
    named after the artifact — `conda_pkgs_linux/<file>`,
    `conda_pkgs_osx/<file>`, `conda_pkgs_win/<file>` — with NO inner
    platform subdir. We strip that wrapper and re-nest the files under
    `dest/<platform>/` (synthesized from the `platform` kwarg, which the
    caller sources from `art["platform"]`) so the union of all platforms
    forms a valid `file://` mamba channel layout: `extracted/linux-64/*.conda`,
    `extracted/osx-64/...`, etc., each with its own subdir-matched
    `repodata.json`.

    Verified against PR #33693 buildId 1536673: each ZIP carried
    `conda_pkgs_<job>/{<pkg>.conda, repodata.json, repodata_from_packages.json,
    index.html, .cache/cache.db}` at one level. No inner `<platform>/` dir.

    `platforms` is the user's `--platforms` filter (the list passed via
    `--platforms linux-64,osx-64`). When set and the zip's `platform` is
    not in it, extraction is a no-op (returns `[]`).

    Returns the list of `.conda` files written (relative to `dest`).

    Path safety: Azure artifacts originate from arbitrary PR builds and
    must be treated as untrusted. Each member's *post-wrapper* path is
    checked for absolute paths and `..` traversal BEFORE re-nesting
    under `<platform>/` — otherwise a malicious member like
    `wrapper//etc/passwd` (post-wrapper `/etc/passwd`, absolute) would
    be neutralized by the prefix into `dest/<platform>/etc/passwd`,
    silently writing inside `dest`. The final `target.relative_to(dest)`
    check is a belt-and-suspenders backstop. Mirrors the Python 3.12+
    `extractall(filter="data")` guard.
    """
    zip_path = Path(zip_path)
    dest = Path(dest).resolve()
    # Whole-zip platform filter — one ZIP carries exactly one platform,
    # so when the user has restricted via --platforms we can short-circuit.
    if platforms is not None and platform is not None and platform not in platforms:
        return []
    dest.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            # Skip directory entries.
            if name.endswith("/"):
                continue
            parts = name.split("/")
            if len(parts) < 2:
                # Top-level file (no wrapper dir) — keep verbatim.
                inner = name
            else:
                # Drop the first segment (the conda_pkgs_<job>/ wrapper).
                inner = "/".join(parts[1:])
            # Zip-Slip guard on the post-wrapper path (BEFORE re-nesting
            # under <platform>/ — see security note in docstring).
            inner_path = Path(inner)
            if inner_path.is_absolute() or ".." in inner_path.parts:
                raise ValueError(
                    f"Refusing to extract member with unsafe path: {name!r}"
                )
            # Re-nest under <platform>/ when the caller passed one; else
            # write at dest root (legacy / test-only path).
            rel = f"{platform}/{inner}" if platform else inner
            target = (dest / rel).resolve()
            try:
                target.relative_to(dest)
            except ValueError:
                raise ValueError(
                    f"Refusing to extract member that resolves outside "
                    f"destination: {name!r} → {target}"
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(name) as src, open(target, "wb") as dst:
                while True:
                    chunk = src.read(1024 * 1024)
                    if not chunk:
                        break
                    dst.write(chunk)
            if rel.endswith(".conda"):
                written.append(rel)
    return written


def _now_utc_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _manifest_path(build_dir: Path) -> Path:
    return build_dir / "pr-artifacts.json"


_REQUIRED_MANIFEST_KEYS = {"build_id", "azure_url", "artifacts"}


def _read_cached_manifest(build_dir: Path) -> dict[str, Any] | None:
    """Return the cached manifest dict for `build_dir/pr-artifacts.json`, or None.

    Returns None on missing file, malformed JSON, or a shape that lacks
    the documented required keys — keeps downstream consumers
    (`_print_human`, MCP tool) from crashing with KeyError on a corrupt
    or truncated cache file written by a prior crashed run. Treating the
    cache as missing forces a clean re-fetch.
    """
    path = _manifest_path(build_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    if not _REQUIRED_MANIFEST_KEYS.issubset(data.keys()):
        return None
    return data


def _write_noarch_stub(extracted_dir: Path) -> Path:
    """Write an empty `noarch/repodata.json` if absent.

    Conda solvers (mamba, conda, py-rattler) probe every channel for
    every standard subdir, and a missing `noarch/repodata.json` hard-fails
    channel loading: `Could not read a file:// file [...noarch/repodata.json]`
    + `Subdir noarch not loaded!`. Azure's per-platform ZIPs never carry
    a noarch payload, so without this stub the otherwise-correctly-indexed
    `linux-64/` / `osx-64/` / `win-64/` subdirs are wasted: the solver
    refuses to consider the channel and the operator has to fall back to
    `mamba install <path>.conda`. The stub matches the repodata_version=2
    shape that rattler-build emits for each per-platform subdir inside
    the Azure ZIPs (verified PR #33693 buildId 1536673).
    """
    noarch_dir = extracted_dir / "noarch"
    noarch_dir.mkdir(parents=True, exist_ok=True)
    stub = noarch_dir / "repodata.json"
    if stub.exists():
        return stub
    stub.write_text(
        json.dumps(
            {
                "info": {"subdir": "noarch"},
                "packages": {},
                "packages.conda": {},
                "repodata_version": 2,
            }
        )
    )
    return stub


def _write_manifest_atomic(build_dir: Path, manifest: dict[str, Any]) -> Path:
    """Write `pr-artifacts.json` atomically.

    Direct `path.write_text(...)` is not atomic — a SIGKILL between the
    open and the buffer flush leaves a truncated file that
    `_read_cached_manifest` would then treat as a corrupt cache. Write
    to a sibling `.tmp` first, then `os.replace` so consumers either see
    the old file or the new file, never a partial one.
    """
    import os
    path = _manifest_path(build_dir)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(manifest, indent=2) + "\n")
    os.replace(tmp, path)
    return path


def fetch_one_build(
    pr_ref: str,
    repo: str,
    build_id: int,
    output_root: Path,
    *,
    extract: bool = True,
    keep_zips: bool = False,
    platforms: list[str] | None = None,
    include_all: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Fetch + extract every artifact for one buildId. Returns the manifest dict."""
    build_dir = output_root / str(build_id)
    azure_url = _AZURE_BUILD_RESULT_URL.format(build_id=build_id)

    cached = _read_cached_manifest(build_dir)
    if cached and not force:
        return {**cached, "skipped_cached": True}

    build_dir.mkdir(parents=True, exist_ok=True)
    artifacts_meta = list_azure_artifacts(build_id, include_all=include_all)
    if not artifacts_meta:
        return {
            "pr_ref": pr_ref,
            "repo": repo,
            "build_id": build_id,
            "azure_url": azure_url,
            "fetched_at": _now_utc_iso(),
            "result": "no_conda_pkgs_artifacts",
            "artifacts": [],
            "channel_url": None,
            "skipped_cached": False,
            "warnings": [
                "Build published no conda_pkgs_* artifacts. Did the recipe set "
                "azure.store_build_artifacts? (Pass --all-artifacts to fetch every "
                "Azure artifact.)"
            ],
        }

    extracted_dir = build_dir / "extracted"
    manifest_artifacts: list[dict[str, Any]] = []
    for art in artifacts_meta:
        zip_path = download_artifact(art, build_dir)
        entry: dict[str, Any] = {
            "name": art["name"],
            "platform": art["platform"],
            "size_bytes": art["size"],
            "conda_files": [],
            "extracted_to": None,
        }
        if extract:
            platforms_filter = platforms if platforms else None
            conda_files = extract_zip(
                zip_path,
                extracted_dir,
                platform=art["platform"],
                platforms=platforms_filter,
            )
            entry["conda_files"] = conda_files
            entry["extracted_to"] = (
                f"extracted/{art['platform']}/" if art["platform"] else "extracted/"
            )
            if not keep_zips:
                zip_path.unlink(missing_ok=True)
        manifest_artifacts.append(entry)

    # Write an empty noarch/repodata.json if it's missing. Conda solvers
    # (mamba, conda, rattler) probe every channel for a noarch subdir
    # and hard-fail when it's absent; Azure's per-platform ZIPs never
    # carry a noarch payload, so without this stub the resulting
    # channel is unusable via `mamba install -c file://... <pkg>` even
    # though every per-platform `.conda` is correctly indexed.
    if extract and any(e["conda_files"] for e in manifest_artifacts):
        _write_noarch_stub(extracted_dir)

    channel_url = (
        f"file://{extracted_dir.resolve()}" if extract and extracted_dir.exists() else None
    )
    manifest = {
        "pr_ref": pr_ref,
        "repo": repo,
        "build_id": build_id,
        "azure_url": azure_url,
        "fetched_at": _now_utc_iso(),
        "result": "succeeded",
        "artifacts": manifest_artifacts,
        "channel_url": channel_url,
        "skipped_cached": False,
    }
    _write_manifest_atomic(build_dir, manifest)
    return manifest


# ── CLI ─────────────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pr-artifacts",
        description=(
            "Download conda-forge PR build artifacts from Azure DevOps. "
            "Given a staged-recipes or feedstock PR (number or URL), resolves "
            "the Azure buildId via `gh pr checks`, lists artifacts via the "
            "Azure REST API, downloads conda_pkgs_* ZIPs, and extracts them "
            "into a local file:// mamba channel."
        ),
    )
    p.add_argument("pr_ref", help="PR number (e.g. 33693) or full GitHub URL.")
    p.add_argument(
        "--repo",
        default="conda-forge/staged-recipes",
        help="Override repo. Default: conda-forge/staged-recipes (used only when pr_ref is a bare number).",
    )
    p.add_argument(
        "--build-id",
        type=int,
        default=None,
        help="Skip gh-CLI lookup; download this specific Azure buildId directly.",
    )
    p.add_argument(
        "--check-name",
        default=None,
        help="Override the staged-recipes / <pkg>-feedstock check-row auto-detect.",
    )
    p.add_argument(
        "--output-dir",
        default=None,
        help="Destination root. Default: build_artifacts/pr/<pr-number>/",
    )
    p.add_argument(
        "--no-extract",
        dest="extract",
        action="store_false",
        help="Keep ZIPs only; do not unzip into the channel layout. Default: extract.",
    )
    p.add_argument(
        "--keep-zips",
        action="store_true",
        help="After extract, keep the raw .zip files. Default: discard.",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch even when pr-artifacts.json shows the same buildId already downloaded.",
    )
    p.add_argument(
        "--all-runs",
        action="store_true",
        help="If the PR has multiple Azure runs, fetch each. Default: latest run only.",
    )
    p.add_argument(
        "--platforms",
        default=None,
        help="Comma-list (e.g. linux-64,osx-64). Filter which extracted subdirs to write.",
    )
    p.add_argument(
        "--all-artifacts",
        action="store_true",
        help="Fetch non-package artifacts too (logs, _build_artifacts.json). Default: filter to conda_pkgs_*.",
    )
    p.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit a JSON summary to stdout instead of human-readable text.",
    )
    return p


def _print_human(result: dict[str, Any]) -> None:
    runs = result.get("runs", [])
    if not runs:
        print(f"No runs fetched for PR {result.get('pr_ref')}.", file=sys.stderr)
        return
    for run in runs:
        bid = run.get("build_id")
        if run.get("skipped_cached"):
            print(
                f"skipped (cached): {bid} already fetched at {run.get('fetched_at')}",
                file=sys.stderr,
            )
            continue
        print(f"buildId {bid} ({run.get('azure_url')}):")
        for art in run.get("artifacts", []):
            n_conda = len(art.get("conda_files", []))
            size = art.get("size_bytes") or 0
            print(
                f"  - {art['name']}  [{art.get('platform') or '?'}]  "
                f"{size / 1024 / 1024:.1f} MiB  → {n_conda} .conda file(s)"
            )
        if run.get("channel_url"):
            print(f"  channel: mamba install -c {run['channel_url']} <pkg>")
        for w in run.get("warnings", []) or []:
            print(f"  WARN: {w}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.build_id is not None and args.build_id <= 0:
        parser.error("--build-id must be a positive integer")

    try:
        repo, pr_number = parse_pr_ref(args.pr_ref, default_repo=args.repo)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    output_root = (
        Path(args.output_dir)
        if args.output_dir
        else Path("build_artifacts") / "pr" / str(pr_number)
    )

    if args.build_id is not None:
        build_ids = [args.build_id]
    else:
        try:
            build_ids = resolve_build_ids(
                pr_number,
                repo=repo,
                check_name=args.check_name,
                all_runs=args.all_runs,
            )
        except LookupError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        except RuntimeError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1

    if args.platforms:
        platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]
        if not platforms:
            parser.error("--platforms parsed to an empty list; pass e.g. linux-64,osx-64")
    else:
        platforms = None

    runs: list[dict[str, Any]] = []
    errors: list[str] = []
    extract_failed = False  # zipfile.BadZipFile / ValueError from extract_zip
    for bid in build_ids:
        try:
            manifest = fetch_one_build(
                pr_ref=str(pr_number),
                repo=repo,
                build_id=bid,
                output_root=output_root,
                extract=args.extract,
                keep_zips=args.keep_zips,
                platforms=platforms,
                include_all=args.all_artifacts,
                force=args.force,
            )
            runs.append(manifest)
        except (zipfile.BadZipFile, ValueError) as e:
            # Spec § I/O Matrix: corrupt ZIP / extract failure → exit 2;
            # the bad .zip stays in build_dir/ for forensics; no manifest.
            errors.append(f"buildId {bid}: corrupt_zip: {type(e).__name__}: {e}")
            extract_failed = True
        except Exception as e:
            errors.append(f"buildId {bid}: {type(e).__name__}: {e}")

    summary = {
        "pr_ref": str(pr_number),
        "repo": repo,
        "runs": runs,
        "output_dir": str(output_root.resolve()),
        "channel_url": (runs[0].get("channel_url") if runs else None),
        "skipped_cached": bool(runs and all(r.get("skipped_cached") for r in runs)),
        "errors": errors,
    }

    if args.as_json:
        print(json.dumps(summary, indent=2))
    else:
        _print_human(summary)
        for err in errors:
            print(f"error: {err}", file=sys.stderr)

    if extract_failed:
        return 2
    return 0 if runs and not errors else 1


if __name__ == "__main__":
    sys.exit(main())
