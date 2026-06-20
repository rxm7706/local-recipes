---
status: shipped
implemented_by: bmad-quick-dev
shipped_ref: "v8.14.0"
spec_updated: 2026-06-20
---
# Tech Spec: conda-forge-expert v8.14.0 — PR Artifact Downloader

> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow track —
> additive feature; net-new MCP tool + CLI + pixi task). ~9 implementation
> stories across 4 waves. Run BMAD with this file as the intent document:
>
> ```
> run quick-dev — implement the intent in docs/specs/cfe-pr-artifact-downloader.md
> ```
>
> **Per `CLAUDE.md` Rule 1**, any BMAD agent executing this spec MUST invoke
> the `conda-forge-expert` skill before touching skill code. Per Rule 2, the
> effort closes with a CFE-skill retrospective and a `CHANGELOG.md` entry.

---

## Status

| Field | Value |
|---|---|
| Status | **Draft v1** — ready for `bmad-quick-dev` intake |
| Owner | rxm7706 |
| Track | BMAD Quick Flow (tech-spec only, no PRD/architecture phase) |
| Surface area | `conda-forge-expert` skill — new CLI script (`pr_artifacts.py`), new pixi task (`pr-artifacts`), new MCP tool (`download_pr_artifacts`), 1 guide section + 1 quickref entry + 1 reference entry |
| Scope | Given a staged-recipes or feedstock PR (URL or number), resolve the Azure DevOps `buildId` via `gh pr checks`, list published artifacts via the Azure REST API, download all `conda_pkgs_*` ZIPs, optionally extract them into a valid local mamba channel layout. Read-only operation. Anonymous Azure auth. |
| Version | conda-forge-expert v8.13.2 → **v8.14.0** (MINOR — net-new user-facing feature; no breaking changes to existing CLIs / MCP tools / build flow) |
| Out of scope | Auto-installing artifacts into a conda env; re-running CI on the PR; modifying the PR; private Azure project authentication (conda-forge is public); win-host cross-build (already shipped in v8.13.2's `recipe-build-cross`); per-version vdb history of fetched artifacts |
| Created | 2026-06-11 |
| Driven by | gh-copilot-cli staged-recipes#33693 session — reviewers needed an osx-arm64 artifact for hands-on smoke-testing before merge; the Azure UI's per-job artifact download required ~5 clicks per platform with no batch path; same friction every time a PR's `azure.store_build_artifacts: true` is set |
| Predecessor | `docs/specs/conda-forge-expert-v8.0.md` (v8.0.0 — last MINOR-bump feature spec); the v8.13.2 `recipe-build-cross` wrapper landed without a spec (small additive script). This spec re-establishes the spec-driven discipline for v8.14.0 |

---

## Background and Context

### The problem

Staged-recipes' Azure pipeline matrix is hardcoded to `linux_64` / `osx_64` /
`win_64` — the `osx_arm64` and `linux_aarch64` artifacts come only post-merge
from the auto-generated feedstock. For platforms the staged-recipes runners
DO cover, the artifact is published to Azure DevOps as a `.zip` (one per
job: `conda_pkgs_linux`, `conda_pkgs_osx`, `conda_pkgs_win`), but the UI is
optimised for human eyeball-review of build logs, not bulk artifact fetch:

1. Open the Azure URL from the PR's check link.
2. Click "X published" in the artifacts strip.
3. For each artifact: hover, click the kebab, click "Download artifacts".
4. Browser saves a zip per job.
5. Unzip each manually, locate `.conda` inside, organise into a local channel.

Multiply by 3 jobs and any time a reviewer wants to spot-check 2-3 PRs in a
batch, the friction kills the "review the artifact, not just the diff" loop
that `azure.store_build_artifacts: true` (CFE reference
`conda-forge-yml-reference.md` § "Top use cases") was meant to enable.

The v8.13.2 `recipe-build-cross` wrapper closed the gap for platforms
staged-recipes' CI doesn't reach (osx-arm64, linux-aarch64) by building
locally. The remaining gap is the inverse: when CI **did** build, fetch
those exact bytes — same ones the reviewer would see if they merged blind —
without re-building.

### What's been ruled out

- **Inline-only MCP tool with no standalone CLI.** Future CLI ergonomics
  (cron job pulling artifacts on every PR open, sharing the `.conda` over
  Slack, scripted local smoke-test pipelines) all want a shell-callable
  surface. Build the CLI first; the MCP tool is a thin wrapper.
- **Adding artifact-download support to `recipe-build-cross`.** Different
  problem shape: cross-build is recipe-input → `.conda` output; this is
  PR-input → `.conda` output. Different identifier (recipe path vs PR ref),
  different resolution chain (rattler-build vs Azure REST), different
  failure modes (build failures vs network/auth failures). One script per
  concern, one pixi task per concern.
- **Using `az` CLI for Azure auth + API access.** Adds a heavy dep
  (`azure-cli`) for what is a single anonymous REST call to a public
  project. The existing `_http.make_request` helper (CFE reference
  `mcp-tools.md` § "Internal HTTP layer") covers it with the JFrog /
  GitHub / .netrc auth chain already in place.
- **Auto-install the downloaded `.conda` into a mamba env.** Too much
  policy bakes in (which env, which channel priority, --force-reinstall
  semantics). The output layout is already a valid `file://` channel; the
  user can `mamba install -c file:///abs/path/extracted <pkg>` themselves
  in one line. Revisit auto-install as a v8.15 follow-up if the CLI-as-is
  proves cumbersome.

### What's available to leverage

- **`gh pr checks <pr> --repo <owner>/<repo>`** already returns the Azure
  URLs as `link` fields in JSON output. No HTML scraping; no GraphQL.
  Existing dep (already in pixi env).
- **Azure DevOps Build Artifacts REST API** is documented at
  <https://learn.microsoft.com/en-us/rest/api/azure/devops/build/artifacts/list>;
  anonymous read works on the public `conda-forge/feedstock-builds`
  project. URL shape:
  `https://dev.azure.com/conda-forge/feedstock-builds/_apis/build/builds/{buildId}/artifacts?api-version=7.1`.
- **`_http.make_request`** (`.claude/skills/conda-forge-expert/scripts/_http.py`)
  already handles truststore + auth chain + JFrog routing. Streaming
  downloads are supported via `iter_content` pattern used by
  `pypi_intelligence.py` and `feedstock_enrich.py`.
- **`.claude/scripts/conda-forge-expert/`** entrypoint-wrapper layer
  established in v7.0.0 — every new user-facing script lands as
  (canonical-impl-in-skill, thin-wrapper-in-scripts) per the 3-tier
  layout. Meta-test `test_skill_md_consistency.py::test_every_user_script_has_a_pixi_task`
  enforces the pixi-task wiring.
- **Existing FastMCP server pattern** (`.claude/tools/conda_forge_server.py`)
  invokes scripts via subprocess and parses their `--json` output. No new
  MCP plumbing needed beyond defining the tool function + decorating with
  `@mcp.tool()`.

---

## Goals

1. **Single-command PR-to-artifacts**: `pixi run -e local-recipes pr-artifacts 33693` produces a local mamba channel from the PR's Azure-published `.conda` files in one step.
2. **MCP-callable** so Claude can drive the fetch as part of a review workflow (`download_pr_artifacts(pr_ref="33693")` returns the manifest).
3. **Works for both staged-recipes and feedstock PRs** (same Azure project; check-name auto-detect handles the surface).
4. **Idempotent and cacheable**: re-running over a populated output dir is a no-op when the buildId already fetched; `--force` opts back in.
5. **Read-only**: no PR modification, no env mutation, no auto-install. Output is a `file://` channel the user can install from on their own terms.
6. **Anonymous Azure auth**: no PAT, no `az login`, works on a fresh dev box with just `gh` authenticated.

## Non-Goals

- Re-running stale CI (use `@conda-forge-admin, please restart ci`).
- Installing into a conda env.
- Win-host cross-build (already in v8.13.2).
- Private Azure project authentication.
- Per-version vdb-history snapshots.

---

## Lifecycle Expectations

Per `CLAUDE.md` Rule 1, the BMAD agent invokes the `conda-forge-expert`
skill before touching `.claude/skills/conda-forge-expert/*`. Per Rule 2,
the effort closes with a `bmad-retrospective` pass that lands findings in
SKILL.md / reference / guides / CHANGELOG.md.

This is a Quick Flow effort — no PRD / architecture / epics. The spec is
the BMAD intake. Wave sequencing below is the contract.

---

## Design

### CLI surface

```
pr-artifacts <pr-ref> [options]

Positional:
  <pr-ref>            PR number (33693) or full URL
                      (https://github.com/conda-forge/staged-recipes/pull/33693).
                      Repo inferred from URL; defaults to
                      conda-forge/staged-recipes for bare numbers.

Resolution overrides:
  --repo <owner/repo> Override repo (e.g. for feedstock PRs not auto-
                      detected from a bare number). Default:
                      conda-forge/staged-recipes.
  --build-id <id>     Skip gh-CLI lookup; download a specific Azure
                      buildId directly. Useful when working from the
                      Azure URL or selecting a specific re-run.
  --check-name <name> Override "staged-recipes" / "<pkg>-feedstock"
                      auto-detection. Default: auto.

Output:
  --output-dir <path> Destination root. Default:
                      build_artifacts/pr/<pr-number>/
  --extract           Unzip published .zip artifacts and surface the
                      .conda files in a flat channel layout. Default ON.
  --keep-zips         Keep the raw .zip files alongside extracted/.
                      Default: discard zips after extract.
  --force             Re-fetch even when pr-artifacts.json shows the
                      same buildId already downloaded. Default: skip-
                      existing (idempotent).
  --all-runs          If the PR has multiple Azure runs, fetch each.
                      Default: latest run only.

Filtering:
  --platforms <list>  Comma-list, e.g. linux-64,osx-64. Filters which
                      artifact subdirs are extracted. Default: all.
  --all-artifacts     Fetch non-package artifacts too (logs,
                      _build_artifacts.json). Default: filter to
                      conda_pkgs_* by name.

Output mode:
  --json              Emit a JSON summary to stdout (used by the MCP
                      tool wrapper). Default: human-readable text.

Misc:
  -h, --help          Show usage and exit.
```

### MCP tool signature

```python
@mcp.tool()
def download_pr_artifacts(
    pr_ref: str,
    repo: str = "conda-forge/staged-recipes",
    build_id: int | None = None,
    output_dir: str | None = None,   # default build_artifacts/pr/<pr>/
    extract: bool = True,
    platforms: list[str] | None = None,
    all_runs: bool = False,
    force: bool = False,
    check_name: str | None = None,
) -> dict:
    """
    Fetch all CI-published .conda artifacts for a conda-forge staged-recipes
    or feedstock PR into a local mamba channel layout.

    Returns:
        {
          "pr_ref": "33693",
          "repo": "conda-forge/staged-recipes",
          "runs": [
            {
              "build_id": 1536673,
              "azure_url": "https://dev.azure.com/...",
              "result": "succeeded",
              "artifacts": [
                {
                  "name": "conda_pkgs_linux",
                  "platform": "linux-64",
                  "conda_files": ["linux-64/gh-copilot-cli-1.0.61-h....conda"],
                  "size_bytes": 78_641_152,
                },
                ...
              ],
            }
          ],
          "output_dir": "/abs/path/build_artifacts/pr/33693/",
          "channel_url": "file:///abs/path/build_artifacts/pr/33693/1536673/extracted",
          "skipped_cached": false,
          "errors": [],
        }
    """
```

### Resolution chain

```
1. Parse <pr-ref>
     bare digits → (default repo, pr_number)
     github URL  → (parsed repo, parsed pr_number)
   --repo flag overrides parsed repo.

2. Resolve buildId(s):
   IF --build-id given:
       use it directly; skip gh.
   ELSE:
       gh pr checks <pr> --repo <repo> --json name,link,bucket,state
       filter rows where:
           name == --check-name  (if provided)
           OR name == "staged-recipes"  (default for staged-recipes repo)
           OR name matches r"^<pkg>-feedstock$"  (auto for feedstock repo)
       grep `link` for r"dev\.azure\.com/conda-forge/.+?buildId=(\d+)"
       IF --all-runs:
           collect every distinct buildId
       ELSE:
           pick the highest (newest) buildId.

3. For each buildId:
   IF NOT --force AND output_dir/<buildId>/pr-artifacts.json exists:
       emit "skipped (cached)" and continue.
   ELSE:
       GET https://dev.azure.com/conda-forge/feedstock-builds/
           _apis/build/builds/{buildId}/artifacts?api-version=7.1
       parse artifacts list.
       filter to name matches r"^conda_pkgs_(linux|osx|win)$"
           unless --all-artifacts.
       for each artifact:
           stream artifact.resource.downloadUrl → output_dir/<buildId>/<name>.zip
           verify Content-Length matches downloaded bytes.

4. IF --extract (default):
       unzip each <name>.zip into output_dir/<buildId>/extracted/<subdir>/
       (the .zip already contains a subdir like `conda-build_<job>/linux-64/...`;
        we flatten one level so extracted/linux-64/*.conda is the result).
       filter to --platforms if specified.
       IF NOT --keep-zips: rm the .zip after successful extract.

5. Write pr-artifacts.json manifest at output_dir/<buildId>/.
6. Emit JSON or human-readable summary.
```

### Output layout

```
build_artifacts/pr/<pr-number>/
├── <buildId>/
│   ├── conda_pkgs_linux.zip      # only if --keep-zips
│   ├── conda_pkgs_osx.zip
│   ├── conda_pkgs_win.zip
│   ├── extracted/                # default — valid file:// channel
│   │   ├── linux-64/
│   │   │   ├── <pkg>-<ver>-<hash>.conda
│   │   │   └── repodata.json
│   │   ├── osx-64/...
│   │   └── win-64/...
│   └── pr-artifacts.json         # manifest (used by cache check)
└── (additional <buildId>/ dirs if --all-runs)
```

`extracted/<subdir>/repodata.json` is included in the Azure ZIPs — no
re-indexing needed.

### `pr-artifacts.json` manifest schema

```json
{
  "pr_ref": "33693",
  "repo": "conda-forge/staged-recipes",
  "build_id": 1536673,
  "azure_url": "https://dev.azure.com/conda-forge/feedstock-builds/_build/results?buildId=1536673",
  "fetched_at": "2026-06-11T19:42:18Z",
  "result": "succeeded",
  "artifacts": [
    {
      "name": "conda_pkgs_linux",
      "platform": "linux-64",
      "size_bytes": 78641152,
      "conda_files": ["linux-64/gh-copilot-cli-1.0.61-h....conda"],
      "extracted_to": "extracted/linux-64/"
    }
  ],
  "channel_url": "file:///abs/path/build_artifacts/pr/33693/1536673/extracted"
}
```

### Anonymous Azure auth

The `feedstock-builds` Azure project is public; the artifacts REST endpoint
accepts unauthenticated requests. `_http.make_request` must NOT inject
`Authorization: Bearer ...` when the destination host is `dev.azure.com`
(the JFrog / GitHub auth chain would otherwise attach credentials that
expose 401 noise). Add a host-allowlist short-circuit in the helper, or
explicitly pass `auth=False` from the new script.

### Failure modes the script handles explicitly

| Condition | Behavior |
|---|---|
| PR has no Azure check yet (CI pending or never triggered) | exit 1; clear stderr: `"No Azure build found on PR <ref>; CI may still be pending. Re-run when checks complete."` |
| PR has only a failed `linter` check, no `staged-recipes` check | exit 1; clear stderr: `"Build failed before publishing artifacts."` |
| Build succeeded but published 0 conda_pkgs_* artifacts (rare; opt-in needed) | exit 0 with WARN: `"Build published no conda_pkgs_* artifacts. Did the recipe set azure.store_build_artifacts?"` |
| Build was for a different commit (PR has new pushes since the build) | succeed with WARN: `"WARNING: latest buildId is for <sha-short>; PR head is <newer-sha-short>. Use --all-runs to see history."` |
| Network error mid-download | retry per `_http` retry policy; surface clean error after exhaustion |
| ZIP extraction fails (corrupt download) | exit 2; keep the bad ZIP for forensics; don't write the manifest |
| Cached buildId, no `--force` | exit 0; emit `"skipped (cached): <buildId> already fetched at <fetched_at>"` |

### Integration with existing CFE flow

- Step 9 ("Monitor PR build") in SKILL.md already mentions checking CI;
  a new bullet there points at `pr-artifacts` for grabbing the bytes.
- `guides/testing-recipes.md` gains a new § "Downloading artifacts from a
  PR" with a 4-line usage recipe + `mamba install -c file://...` example.
- `reference/mcp-tools.md` adds `download_pr_artifacts` to the tool
  inventory table.
- `quickref/commands-cheatsheet.md` adds one line under the "Local builds
  via pixi" section (which v8.13.2 just added).

---

## Stories — 4 waves, ~9 stories

### Wave A — Core fetch (S1–S3, ships standalone)

| ID | Story | Effort |
|---|---|---|
| **S1** | PR-ref parser + `gh pr checks` → buildId resolver. Accept bare digits or full GitHub URL; default repo `conda-forge/staged-recipes`; `--repo`, `--build-id`, `--check-name`, `--all-runs` flags. Unit-tested with mocked `gh` JSON output covering staged-recipes (`name: "staged-recipes"`) and feedstock (`name: "<pkg>-feedstock"`) cases. | M |
| **S2** | Azure REST artifact lister: `_http.make_request` against `feedstock-builds/_apis/build/builds/<id>/artifacts?api-version=7.1` with explicit `auth=False` (or host-allowlist short-circuit in `_http`). Parse the `value[]` list; filter to `conda_pkgs_*` by default; return artifact dicts with `name`, `downloadUrl`, declared `size`. | S |
| **S3** | Streaming ZIP downloader: writes `output_dir/<buildId>/<name>.zip`; verifies `Content-Length` matches written bytes; retries per `_http` policy; idempotency check against `pr-artifacts.json` cache. | S |

### Wave B — CLI + pixi task (S4–S5, ships behind Wave A)

| ID | Story | Effort |
|---|---|---|
| **S4** | argparse front-end exposing the full flag set above; `--extract` (default ON) wires `zipfile`-based extraction to `extracted/<subdir>/`; `--keep-zips` controls cleanup; `--platforms` filters subdirs; `--json` mode emits the manifest to stdout for MCP consumption. Writes `pr-artifacts.json` to `<buildId>/`. Live test against PR #33693 buildId 1536673 (the gh-copilot-cli session); assert linux/osx/win artifacts present + `.conda` extracted at expected paths. | M |
| **S5** | `[feature.local-recipes.tasks.pr-artifacts]` entry in `pixi.toml` pointing at the wrapper at `.claude/scripts/conda-forge-expert/pr_artifacts.py`. Add `pr_artifacts.py` to `tests/meta/test_all_scripts_runnable.py::SCRIPTS`. | XS |

### Wave C — MCP tool (S6, ships behind Wave B)

| ID | Story | Effort |
|---|---|---|
| **S6** | `download_pr_artifacts` FastMCP tool in `conda_forge_server.py`: subprocess-invokes the CLI with `--json` and parses the manifest. Signature matches the design section above. Two unit tests stubbing `subprocess.run` to verify (a) happy path returns parsed manifest, (b) non-zero exit propagates as an `error` key. Append `download_pr_artifacts` to `reference/mcp-tools.md` tool inventory. | M |

### Wave D — Closeout (S7–S9)

| ID | Story | Effort |
|---|---|---|
| **S7** | Docs: `guides/testing-recipes.md` new § "Downloading artifacts from a PR" (4-line usage + `mamba install -c file://...` example); `quickref/commands-cheatsheet.md` one-line entry; `SKILL.md` step 9 cross-reference. | S |
| **S8** | `CHANGELOG.md` v8.14.0 entry covering the new CLI + MCP tool + the MINOR-bump rationale + the live PR #33693 case study; `config/skill-config.yaml` bump 8.13.2 → 8.14.0. | S |
| **S9** | CFE retrospective per `CLAUDE.md` Rule 2: invoke `bmad-retrospective`; land findings as edits to SKILL.md / reference / guides / a fresh CHANGELOG note if anything cross-cuts. Save cross-skill auto-memory only if the finding crosses skill boundaries. | M |

### Wave sequencing rationale

A → B → C → D is dependency-respecting:

- **A first**: pure-logic primitives (PR parsing, Azure REST, ZIP fetch).
  Unit-testable with mocks; no CLI surface yet. Validating these in
  isolation derisks Wave B's CLI-flag matrix.
- **B second**: CLI flags + pixi task. Wave A's primitives compose into
  the argparse front-end. Live test against PR #33693 happens here —
  closing the user's original request before Wave C adds the MCP
  indirection.
- **C third**: MCP tool is a thin wrapper around the JSON-mode CLI from
  B. Adding it earlier means double-implementing JSON output during dev.
- **D last**: docs + CHANGELOG + retro land after the implementation is
  exercised. Retro findings have material to draw from.

**One-PR strategy**: this is small enough (~9 stories, all additive) to
land as a single PR. No schema change, no breaking surface, no migration
window. The two-PR split that v8.0 needed doesn't apply here.

---

## Acceptance Tests

For each wave, the BMAD agent runs the existing pytest suite plus explicit
new tests:

### Wave A

- `tests/unit/test_pr_artifacts_resolver.py::test_parse_bare_pr_number`
  — `parse_pr_ref("33693")` returns `("conda-forge/staged-recipes", 33693)`.
- `tests/unit/test_pr_artifacts_resolver.py::test_parse_github_url`
  — `parse_pr_ref("https://github.com/conda-forge/staged-recipes/pull/33693")`
  returns `("conda-forge/staged-recipes", 33693)`; also works for a
  feedstock URL.
- `tests/unit/test_pr_artifacts_resolver.py::test_buildid_extraction_from_gh_output`
  — mock `gh pr checks` returning the real shape captured from PR #33693;
  assert single `buildId=1536673` extracted from the `staged-recipes` row.
- `tests/unit/test_pr_artifacts_resolver.py::test_all_runs_returns_multiple`
  — mock `gh` output with 3 distinct Azure URLs across re-runs; assert
  `--all-runs` returns 3 buildIds sorted descending; default returns the
  highest.
- `tests/unit/test_pr_artifacts_resolver.py::test_no_azure_check_errors_clean`
  — mock `gh` output containing only the `linter` check; assert exit 1
  + stderr message mentions "No Azure build found".
- `tests/unit/test_azure_artifacts_lister.py::test_filters_to_conda_pkgs_default`
  — mock Azure REST response containing `conda_pkgs_linux`,
  `conda_pkgs_osx`, `_build_artifacts.json`, `logs`; assert only the
  3 `conda_pkgs_*` are kept by default; `--all-artifacts` keeps all 4.
- `tests/unit/test_azure_download.py::test_content_length_mismatch_raises`
  — stream a short body with a too-large `Content-Length`; assert
  exception raised after exhaustion.

### Wave B

- `tests/unit/test_pr_artifacts_cli.py::test_help_responds`
  — `pr_artifacts.py --help` exit 0, contains "Usage:".
- `tests/unit/test_pr_artifacts_cli.py::test_extract_layout`
  — fixture ZIP containing `linux-64/foo.conda` + `linux-64/repodata.json`;
  assert files land at `extracted/linux-64/foo.conda` after extract.
- `tests/unit/test_pr_artifacts_cli.py::test_keep_zips_default_off`
  — after successful extract, the `.zip` is removed unless `--keep-zips`.
- `tests/unit/test_pr_artifacts_cli.py::test_cached_buildid_skips_when_manifest_present`
  — pre-create `pr-artifacts.json` for buildId 1536673; assert second run
  exits 0 with `"skipped (cached)"` and no network calls.
- `tests/unit/test_pr_artifacts_cli.py::test_force_overrides_cache`
  — same setup with `--force`; assert network call made + manifest
  rewritten with new `fetched_at`.
- `tests/unit/test_pr_artifacts_cli.py::test_json_mode_emits_manifest`
  — `--json` flag; assert stdout is parseable JSON matching the manifest
  schema.
- Live smoke test (not in CI; run from this session's terminal): `pixi
  run -e local-recipes pr-artifacts 33693` against the real PR; assert
  output lands at `build_artifacts/pr/33693/1536673/extracted/{linux-64,
  osx-64,win-64}/*.conda` and `pr-artifacts.json` is well-formed.

### Wave C

- `tests/unit/test_download_pr_artifacts_mcp.py::test_happy_path_returns_manifest`
  — stub `subprocess.run` to return a fixture manifest JSON; assert MCP
  tool returns the parsed dict with expected keys.
- `tests/unit/test_download_pr_artifacts_mcp.py::test_non_zero_exit_propagates`
  — stub `subprocess.run` to return rc=1 + stderr; assert MCP tool result
  has `errors: [...]` key populated; no exception raised.

### Wave D

- `tests/meta/test_skill_md_consistency.py` — `download_pr_artifacts` now
  appears in `reference/mcp-tools.md`; pr_artifacts.py added to
  `tests/meta/test_all_scripts_runnable.py::SCRIPTS`.
- Manual: `pixi task list -e local-recipes` shows `pr-artifacts` with
  description copy matching this spec's CLI surface.
- Manual: CHANGELOG.md TL;DR entry for v8.14.0 reads correctly when
  rendered as Markdown.

---

## Risks

| Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|
| Azure DevOps REST API changes the `artifacts` shape or `api-version=7.1` deprecates before next session | Low | Med | Pin `api-version=7.1` explicitly; have S2's test cover the response shape so a breaking change surfaces as a test failure not a runtime crash. |
| `gh pr checks` JSON shape evolves; the `link` field renamed | Low | Low | S1's mock-based tests fix the expected schema; CI failure is the canary. Document the gh-CLI version we tested against in S1's docstring. |
| `_http.make_request`'s JFrog header injection leaks credentials to dev.azure.com (unlikely on a public project but a smell) | Med | Low | S2 explicitly passes `auth=False` to bypass the chain; alternatively add host-allowlist short-circuit (track as v8.15 hardening if not done here). |
| Some PRs publish artifacts named differently (e.g. `build_artifacts` instead of `conda_pkgs_*`) when `azure.store_build_artifacts: true` is set per-recipe | Med | Low | S2's regex covers the documented names. Add an `--artifact-pattern` flag in a future v8.15 if real PRs surface a different name. `--all-artifacts` is the v1 escape hatch. |
| Multi-output recipes publish multiple `.conda` per platform; the extract path needs to preserve sub-dirs | High | Low | Already handled — the Azure ZIPs preserve the conda-build subdir layout (`linux-64/foo-1.conda`, `linux-64/foo-2.conda`); the extractor doesn't flatten beyond the top level. S4's extract test covers two-`.conda`-per-platform fixture. |
| Caching false-positive: same buildId re-fetched returns stale bytes after a re-run that reused the ID (Azure normally allocates new IDs but theoretically possible) | Very Low | Low | `--force` is the documented escape. Manifest records `fetched_at` so the user can decide. Not worth defending further. |

---

## Rollout

- **One PR** to staged-recipes-style local skill changes — bundles all 9
  stories. No schema change, no breaking surface, no two-PR split needed.
- **Version**: v8.13.2 → **v8.14.0** (MINOR — net-new feature, additive
  only, no breaking changes to existing flows).
- **Backout plan**: revert the v8.14.0 commit. No data migration, no
  state to roll back, no MCP tool deprecation (it's net-new). `gh pr
  revert` or `git revert` is sufficient.
- **Communication**: CHANGELOG TL;DR is the announcement. No external
  zulip / mailing-list post needed (skill-internal feature).

---

## Open Questions

- **Q1** — Default extract behavior: extract by default vs require
  `--extract` opt-in?
  *Recommendation*: extract by default (CLI default `--extract=True`,
  match MCP). Raw ZIPs are rarely the consumer's goal; the channel
  layout is.
  → **Resolved as recommended unless reviewer objects.**
- **Q2** — Output dir default: `build_artifacts/pr/<pr>/` (under existing
  gitignored tree) vs `pr-artifacts/<pr>/` (new top-level tree)?
  *Recommendation*: `build_artifacts/pr/<pr>/` — already gitignored,
  lives alongside other build outputs, no `.gitignore` change needed.
  → **Resolved as recommended.**
- **Q3** — `--all-runs` behavior on a PR with 5 Azure rebuilds: fetch
  all 5? Filter to succeeded-only?
  *Recommendation*: default to latest run; `--all-runs` fetches every
  distinct buildId regardless of result. User can post-filter on
  manifest `result` field.
  → **Resolved as recommended.**
- **Q4** — Feedstock-PR support depth: full parity (same code path) vs
  staged-recipes-only v1 with feedstock support deferred?
  *Recommendation*: full parity. The check-name auto-detect is one regex
  difference. Cost ~0 in S1; deferring would require a follow-up spec.
  → **Resolved as recommended.**
- **Q5** — Auto-install into local mamba channel + smoke-test?
  *Recommendation*: out of scope for v1. Add as v8.15 follow-up only if
  manual `mamba install -c file://...` proves cumbersome. The channel
  layout is already valid.
  → **Resolved as out of scope.**
- **Q6** — Skip-existing cache vs always re-fetch?
  *Recommendation*: skip-existing by default (idempotency is the v1
  default); `--force` overrides. Manifest `fetched_at` lets the user
  decide when stale.
  → **Resolved as recommended.**
- **Q7** — Artifact name filtering: `conda_pkgs_*` only by default vs
  all artifacts?
  *Recommendation*: filter to `conda_pkgs_*` by default; `--all-artifacts`
  opens the floodgates (logs, `_build_artifacts.json`, etc.).
  → **Resolved as recommended.**
- **Q8** — Where does the new CLI's PR-resolution helper live? Standalone
  in `pr_artifacts.py` or extracted into `_pr_resolver.py` for re-use
  by future MCP tools (e.g. a `summarize_pr_checks` analog)?
  *Recommendation*: standalone in `pr_artifacts.py` for v1. Extract only
  if a second caller materialises. Premature abstraction otherwise.
  → **Resolved as recommended.**

---

## References

- `docs/specs/conda-forge-expert-v8.0.md` — last MINOR-bump feature spec; template for the format used here.
- `.claude/skills/conda-forge-expert/CHANGELOG.md` v8.13.2 entry — `recipe-build-cross` precedent; the inverse of this feature's problem (cross-build locally vs fetch CI's build).
- `.claude/skills/conda-forge-expert/reference/conda-forge-yml-reference.md` § "Top use cases" → `azure.store_build_artifacts: true` — the upstream opt-in this skill consumes.
- `.claude/skills/conda-forge-expert/reference/mcp-tools.md` — pattern for FastMCP tool documentation.
- `.claude/scripts/conda-forge-expert/native-build.sh`, `.claude/scripts/conda-forge-expert/cross-build.sh` — entrypoint-wrapper convention; new wrapper follows the same shape.
- `.claude/skills/conda-forge-expert/tests/meta/test_all_scripts_runnable.py` — meta-test that enforces SCRIPTS list updates.
- `.claude/skills/conda-forge-expert/tests/meta/test_skill_md_consistency.py` — meta-test that enforces pixi-task wiring + SKILL.md script-reference correctness.
- Azure DevOps Build Artifacts REST API: <https://learn.microsoft.com/en-us/rest/api/azure/devops/build/artifacts/list>.
- Live case study: <https://github.com/conda-forge/staged-recipes/pull/33693> (buildId 1536673).
