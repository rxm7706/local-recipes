#!/usr/bin/env python3
"""Build OpenTeams identity rows: PURL Associator join + inventory-derived PURLs.

One row per inventory-2026-08-12 Core_Python_Package_Name.
Associator (conda-forge names) is preferred. Names not in that index are
minted from PyPI_PURL + Source_Repository_URL. Conda PURLs are copied only
when CondaForge_Verified is Yes.

Packaging location URLs (same columns the conda-forge packages page and
the two recipe trees expose):

- Conda-Forge_FeedStock_URL / Conda-Forge_Metadata_URL from
  https://conda-forge.org/packages/ (feedstock-outputs map + metadata Browse)
- Staged_Recipes_PR_URL from conda-forge/staged-recipes PRs
- Local_Recipes_URL from rxm7706/local-recipes/tree/main/recipes

After writing the workbook tab, publish (edit in place, never create) the
pinned secret gist file mgmt-wf-python-modernization-identity.md unless
--skip-gist. The gist id is not in git: set OPENTEAMS_IDENTITY_GIST_ID,
conf/conda-forge-packaging-inventory-operations.local.env, or --gist-id.

Output snapshot tab identity-2026-08-12 is not a source input.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import load_workbook

COLUMNS = [
    "Core_Python_Package_Name",
    "OpenTeams_Title",
    "identity_source",
    "associator_key",
    "associator_status",
    "primary_purl",
    "primary_type",
    "alternative_purls",
    "cpes",
    "conda_purl",
    "source_repository_url",
    "OpenTeams_Issue_URL",
    "Conda-Forge_FeedStock_URL",
    "Conda-Forge_Metadata_URL",
    "Staged_Recipes_PR_URL",
    "Local_Recipes_URL",
    "Verification_Timestamp_UTC",
]

GIT_RE = re.compile(
    r"https?://(?:www\.)?(github\.com|gitlab\.com|bitbucket\.org|codeberg\.org)/([^/]+)/([^/#?\s]+)",
    re.I,
)
TAB_IN = "inventory-2026-08-12"
TAB_OUT = "identity-2026-08-12"
OSS_MILESTONE = "OSS Enhancements (Conda Forge, Pixi, ect)"
PACKAGING_TITLE_RE = re.compile(r"^\[Conda-Forge Packaging\]\s+(.+?)\s*$", re.I)
DEFAULT_GH = Path(__file__).resolve().parent.parent / ".pixi/envs/local-recipes/bin/gh"
REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = Path("/tmp/openteams-identity")
GIST_FILENAME = "mgmt-wf-python-modernization-identity.md"
GIST_ID_ENV = "OPENTEAMS_IDENTITY_GIST_ID"
LOCAL_ENV_PATH = REPO_ROOT / "conf/conda-forge-packaging-inventory-operations.local.env"
GIST_SCHEMA = [
    ("Core_Python_Package_Name", "string", "yes", "Primary key. Conda/PyPI package identity as stored (unique)."),
    ("OpenTeams_Title", "string", "yes", "Issue title `[Conda-Forge Packaging] {name}`."),
    ("identity_source", "enum", "yes", "`purl-associator` | `inventory` | `none` | `openteams-board`."),
    ("associator_key", "string", "no", "Key matched in prefix-dev/purl-associator mappings-index. Blank if unused."),
    ("associator_status", "string", "no", "Associator status, or `inventory-derived` / `unmapped`."),
    ("primary_purl", "purl", "no", "Upstream PURL (`pkg:pypi/…` or `pkg:github/…`). Not a conda PURL."),
    ("primary_type", "enum", "no", "`pypi` | `github` | `git` | blank."),
    ("alternative_purls", "purl[]", "no", "`; `-joined extra PURLs."),
    ("cpes", "string[]", "no", "`; `-joined CPEs from the associator."),
    ("conda_purl", "purl", "no", "`pkg:conda/{name}?channel=conda-forge` only when on conda-forge."),
    ("source_repository_url", "url", "no", "Upstream VCS URL. Not a feedstock and not PyPI/anaconda."),
    ("OpenTeams_Issue_URL", "url", "no", "GitHub issue on OpenTeams-WFT-CDO/mgmt-wf-python-modernization."),
    ("Conda-Forge_FeedStock_URL", "url[]", "no", "`; `-joined github.com/conda-forge/{repo}-feedstock from conda-forge.org/packages."),
    ("Conda-Forge_Metadata_URL", "url", "no", "Packages-page Browse link: conda-metadata-app.streamlit.app/?q=conda-forge/{pkg}."),
    ("Staged_Recipes_PR_URL", "url", "no", "Best conda-forge/staged-recipes PR (open file path, else title; prefer open then merged)."),
    ("Local_Recipes_URL", "url[]", "no", "`; `-joined github.com/rxm7706/local-recipes/tree/main/recipes/{dir}."),
    ("Verification_Timestamp_UTC", "datetime", "yes", "ISO 8601 UTC generation time for this snapshot."),
]
FEEDSTOCK_OUTPUTS_URL = (
    "https://raw.githubusercontent.com/conda-forge/feedstock-outputs/"
    "single-file/feedstock-outputs.json"
)
METADATA_URL = "https://conda-metadata-app.streamlit.app/?q=conda-forge/{pkg}"
LOCAL_RECIPES_URL = "https://github.com/rxm7706/local-recipes/tree/main/recipes/{dir}"
STAGED_PR_API = "/repos/conda-forge/staged-recipes/pulls?state=all&per_page=100"
RECIPE_FILE_RE = re.compile(r"^recipes/([^/]+)/")
TITLE_PREFIX_RE = re.compile(
    r"""(?ix)^(?:
        add(?:s|ed|ing)?|
        new|
        create[ds]?|creating|
        initial(?:\s+commit)?(?:\s+of|\s+for)?|
        conda(?:-forge)?\s+recipe(?:s)?(?:\s+for)?
    )\s+
    (?:(?:the|a|an)\s+)?
    (?:
        (?:conda(?:-forge)?\s+)?(?:python\s+)?(?:r\s+)?(?:new\s+)?
        recipes?(?:\.ya?ml)?\s+(?:for\s+)?
        |
        meta\.yaml\s+(?:for\s+)?
    )?
    """
)
TITLE_VERSION_RE = re.compile(r"\s+v?\d+(?:\.\d+)+(?:[a-z0-9.-]*)\s*$", re.I)
TITLE_JUNK_RE = re.compile(
    r"""(?ix)
    \s+(?:as\s+a\s+)?packages?\s*$|
    \s+\([^)]*\)\s*$
    """
)
TITLE_STOP = {
    "recipe",
    "recipes",
    "package",
    "packages",
    "python",
    "conda",
    "forge",
    "meta",
    "yaml",
    "example",
    "new",
    "the",
    "a",
    "an",
    "for",
    "and",
    "with",
    "using",
    "from",
    "initial",
    "commit",
    "support",
    "fix",
    "update",
    "bump",
    "r",
}
SKIP_RECIPE_DIRS = {"example", "example-v1"}
RECIPE_NAME_RE = re.compile(
    r"(?m)^(?:package:\s*\n(?:[ \t].*\n)*?[ \t]+name:\s*|"
    r"[ \t]+- name:\s*|"
    r"[ \t]+name:\s*)[\"']?([A-Za-z0-9][A-Za-z0-9._+-]*)"
)


def na(value: str | None) -> bool:
    v = (value or "").strip()
    return (not v) or v in {"N/A", "n/a", "NA"}


def join_list(values: list[str]) -> str:
    return "; ".join(v for v in values if v)


def git_purl(url: str) -> str | None:
    if na(url):
        return None
    m = GIT_RE.search(url)
    if not m:
        return None
    host, ns, repo = m.group(1).lower(), m.group(2), m.group(3)
    repo = re.sub(r"\.git$", "", repo, flags=re.I)
    if host == "github.com":
        return f"pkg:github/{ns}/{repo}"
    if host == "gitlab.com":
        return f"pkg:gitlab/{ns}/{repo}"
    if host == "bitbucket.org":
        return f"pkg:bitbucket/{ns}/{repo}"
    return None


def alt_purls(rec: dict) -> list[str]:
    out: list[str] = []
    for item in rec.get("alternative_purls") or []:
        if isinstance(item, str) and item:
            out.append(item)
        elif isinstance(item, dict) and item.get("purl"):
            out.append(item["purl"])
    return out


def lookup_assoc(name: str, packages: dict) -> tuple[dict | None, str | None]:
    if name in packages:
        return packages[name], name
    for cand in (name.replace("-", "."), name.replace("-", "_")):
        if cand in packages:
            return packages[cand], cand
    return None, None


def pep503_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", (value or "").strip().lower()).strip("-")


def packaging_name_from_title(title: str) -> str | None:
    m = PACKAGING_TITLE_RE.match((title or "").strip())
    if not m:
        return None
    name = pep503_name(m.group(1))
    return name or None


def gh_bin() -> str | None:
    if DEFAULT_GH.is_file():
        return str(DEFAULT_GH)
    return shutil.which("gh")


def load_local_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip("'").strip('"')
    return out


def resolve_gist_id(cli_value: str | None) -> str | None:
    for candidate in (
        (cli_value or "").strip(),
        os.environ.get(GIST_ID_ENV, "").strip(),
        load_local_env(LOCAL_ENV_PATH).get(GIST_ID_ENV, "").strip(),
    ):
        if candidate:
            return candidate
    return None


def fetch_project_issues(gh: str) -> list[dict]:
    query = """
    query($cursor: String) {
      organization(login: "OpenTeams-WFT-CDO") {
        projectV2(number: 1) {
          items(first: 100, after: $cursor) {
            pageInfo { hasNextPage endCursor }
            nodes {
              content {
                __typename
                ... on Issue {
                  number
                  title
                  url
                  state
                  milestone { title }
                }
              }
            }
          }
        }
      }
    }
    """
    items: list[dict] = []
    cursor = None
    while True:
        args = [gh, "api", "graphql", "-f", f"query={query}"]
        if cursor:
            args += ["-f", f"cursor={cursor}"]
        data = json.loads(subprocess.check_output(args, text=True))
        conn = data["data"]["organization"]["projectV2"]["items"]
        items.extend(conn["nodes"])
        if not conn["pageInfo"]["hasNextPage"]:
            break
        cursor = conn["pageInfo"]["endCursor"]
    return items


def board_packaging_urls(items: list[dict]) -> dict[str, str]:
    """PEP 503 name -> issue URL for OSS Enhancement [Conda-Forge Packaging] titles."""
    out: dict[str, str] = {}
    for node in items:
        content = node.get("content") or {}
        if content.get("__typename") != "Issue":
            continue
        milestone = (content.get("milestone") or {}).get("title") or ""
        if milestone != OSS_MILESTONE:
            continue
        name = packaging_name_from_title(content.get("title") or "")
        url = content.get("url") or ""
        if name and url and name not in out:
            out[name] = url
    return out


def issue_url(inv: dict, board: dict[str, str]) -> str:
    name = pep503_name(inv.get("Core_Python_Package_Name", ""))
    if name in board:
        return board[name]
    raw = inv.get("OpenTeams_Issue_URL", "")
    return "" if na(raw) else raw


def name_keys(row: dict[str, str]) -> list[str]:
    keys: list[str] = []
    for raw in (
        row.get("Core_Python_Package_Name", ""),
        row.get("associator_key", ""),
    ):
        if not raw:
            continue
        for cand in (raw, raw.lower(), pep503_name(raw), raw.replace("-", "_")):
            if cand and cand not in keys:
                keys.append(cand)
    return keys


def first_map(mapping: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        if key in mapping and mapping[key]:
            return mapping[key]
    return ""


def feedstock_repo_name(repo: str) -> str:
    return repo if repo == "cdt-builds" else f"{repo}-feedstock"


def metadata_url(pkg: str) -> str:
    return METADATA_URL.format(pkg=pkg)


def download_json(url: str, dest: Path) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} ...", flush=True)
    with urllib.request.urlopen(url, timeout=120) as resp:
        dest.write_bytes(resp.read())
    return json.loads(dest.read_text())


def load_feedstock_outputs(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Return (feedstock_url_by_key, metadata_url_by_key) from feedstock-outputs.json."""
    if path.is_file():
        data = json.loads(path.read_text())
    else:
        data = download_json(FEEDSTOCK_OUTPUTS_URL, path)
    fs_map: dict[str, str] = {}
    meta_map: dict[str, str] = {}
    for pkg, repos in data.items():
        if not isinstance(repos, list) or not repos:
            continue
        urls = join_list(
            f"https://github.com/conda-forge/{feedstock_repo_name(str(r))}"
            for r in repos
            if r
        )
        meta = metadata_url(pkg)
        for key in (pkg, pkg.lower(), pep503_name(pkg), pkg.replace("-", "_")):
            if key and key not in fs_map:
                fs_map[key] = urls
                meta_map[key] = meta
    return fs_map, meta_map


def names_from_pr_title(title: str) -> list[str]:
    t = (title or "").strip().strip("`\"'")
    t = TITLE_PREFIX_RE.sub("", t).strip(" :.-")
    t = TITLE_JUNK_RE.sub("", t).strip()
    t = TITLE_VERSION_RE.sub("", t).strip()
    if not t:
        return []
    parts = re.split(r"\s+(?:and|&)\s+|,\s*|;\s+|\s+/\s+", t)
    names: list[str] = []
    for part in parts:
        part = part.strip().strip("`\"'").strip(" .")
        part = re.sub(r"\s+recipe\.ya?ml$", "", part, flags=re.I)
        if not part or len(part.split()) > 3:
            continue
        token = pep503_name(part.replace(" ", "-"))
        if not token or len(token) < 2 or token in TITLE_STOP:
            continue
        if token not in names:
            names.append(token)
    return names


def load_staged_prs(
    tsv_path: Path,
    open_json: Path,
    gh: str | None,
    refresh: bool,
) -> dict[str, str]:
    """PEP 503 name -> best staged-recipes PR URL."""
    if refresh or not tsv_path.is_file():
        if not gh:
            raise SystemExit("gh not found; pass --staged-prs")
        tsv_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Fetching staged-recipes PR titles via {gh} ...", flush=True)
        text = subprocess.check_output(
            [
                gh,
                "api",
                "--paginate",
                "-q",
                '.[] | [.number, .state, (.merged_at // ""), .html_url, .title] | @tsv',
                STAGED_PR_API,
            ],
            text=True,
        )
        tsv_path.write_text(text)
    if refresh or not open_json.is_file():
        if not gh:
            raise SystemExit("gh not found; pass --staged-open-prs")
        open_json.parent.mkdir(parents=True, exist_ok=True)
        print(f"Fetching open staged-recipes PR files via {gh} ...", flush=True)
        text = subprocess.check_output(
            [
                gh,
                "pr",
                "list",
                "--repo",
                "conda-forge/staged-recipes",
                "--state",
                "open",
                "--limit",
                "2000",
                "--json",
                "number,title,url,files",
            ],
            text=True,
        )
        open_json.write_text(text)

    best: dict[str, tuple[int, int, str]] = {}

    def consider(name: str, rank: int, number: int, url: str) -> None:
        if not name or not url:
            return
        prev = best.get(name)
        if prev is None or (rank, -number) < (prev[0], -prev[1]):
            best[name] = (rank, number, url)

    for pr in json.loads(open_json.read_text()):
        number = int(pr.get("number") or 0)
        url = pr.get("url") or ""
        for fileinfo in pr.get("files") or []:
            m = RECIPE_FILE_RE.match(fileinfo.get("path") or "")
            if not m:
                continue
            dirname = m.group(1)
            if dirname in SKIP_RECIPE_DIRS:
                continue
            consider(pep503_name(dirname), 0, number, url)
        for name in names_from_pr_title(pr.get("title") or ""):
            consider(name, 1, number, url)

    with tsv_path.open(encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t", 4)
            if len(parts) != 5:
                continue
            number_s, state, merged_at, url, title = parts
            try:
                number = int(number_s)
            except ValueError:
                continue
            if state == "open":
                rank = 1
            elif merged_at:
                rank = 2
            else:
                rank = 3
            for name in names_from_pr_title(title):
                consider(name, rank, number, url)
    return {name: url for name, (_rank, _n, url) in best.items()}


def load_local_recipes(recipes_dir: Path) -> dict[str, str]:
    """PEP 503 package/dir name -> GitHub tree URL for this repo's recipes/."""
    out: dict[str, str] = {}
    if not recipes_dir.is_dir():
        return out
    for d in sorted(p for p in recipes_dir.iterdir() if p.is_dir() and not p.name.startswith(".")):
        url = LOCAL_RECIPES_URL.format(dir=d.name)
        names = {pep503_name(d.name)}
        for fname in ("recipe.yaml", "meta.yaml"):
            fpath = d / fname
            if not fpath.is_file():
                continue
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for m in RECIPE_NAME_RE.finditer(text):
                token = pep503_name(m.group(1))
                if token and token not in TITLE_STOP:
                    names.add(token)
        for name in names:
            if name and name not in out:
                out[name] = url
            elif name and out.get(name) and out[name] != url:
                if url not in out[name].split("; "):
                    out[name] = join_list([out[name], url])
    return out


def inventory_feedstock_fallback(inv: dict[str, str] | None) -> str:
    if not inv:
        return ""
    raw = inv.get("Conda-Forge_FeedStock_URL", "")
    return "" if na(raw) else raw


def attach_packaging_urls(
    row: dict[str, str],
    fs_map: dict[str, str],
    meta_map: dict[str, str],
    staged_map: dict[str, str],
    local_map: dict[str, str],
    inv: dict[str, str] | None,
) -> dict[str, str]:
    keys = name_keys(row)
    fs_url = first_map(fs_map, keys) or inventory_feedstock_fallback(inv)
    meta_url = first_map(meta_map, keys)
    if fs_url and not meta_url:
        pkg = row.get("associator_key") or row.get("Core_Python_Package_Name") or ""
        meta_url = metadata_url(pkg) if pkg else ""
    if not fs_url:
        meta_url = ""
    row["Conda-Forge_FeedStock_URL"] = fs_url
    row["Conda-Forge_Metadata_URL"] = meta_url
    row["Staged_Recipes_PR_URL"] = first_map(staged_map, keys)
    row["Local_Recipes_URL"] = first_map(local_map, keys)
    return row


def from_assoc(
    inv: dict, rec: dict, matched_as: str, timestamp: str, board: dict[str, str]
) -> dict[str, str]:
    conda = "" if na(inv.get("Conda-forge_PURL")) else inv["Conda-forge_PURL"]
    src = "" if na(inv.get("Source_Repository_URL")) else inv["Source_Repository_URL"]
    return {
        "Core_Python_Package_Name": inv["Core_Python_Package_Name"],
        "OpenTeams_Title": inv["OpenTeams_Title"],
        "identity_source": "purl-associator",
        "associator_key": matched_as,
        "associator_status": rec.get("status") or "",
        "primary_purl": rec.get("purl") or "",
        "primary_type": rec.get("type") or "",
        "alternative_purls": join_list(alt_purls(rec)),
        "cpes": join_list(list(rec.get("cpes") or [])),
        "conda_purl": conda,
        "source_repository_url": src,
        "OpenTeams_Issue_URL": issue_url(inv, board),
        "Verification_Timestamp_UTC": timestamp,
    }


def from_inventory(inv: dict, timestamp: str, board: dict[str, str]) -> dict[str, str]:
    pypi = "" if na(inv.get("PyPI_PURL")) else inv["PyPI_PURL"]
    src = "" if na(inv.get("Source_Repository_URL")) else inv["Source_Repository_URL"]
    gp = git_purl(src)
    primary = pypi
    ptype = "pypi" if pypi else ""
    alts: list[str] = []
    if pypi and gp:
        alts.append(gp)
    elif not pypi and gp:
        primary = gp
        ptype = "github" if gp.startswith("pkg:github/") else "git"
    if primary:
        source, status = "inventory", "inventory-derived"
    else:
        source, status = "none", "unmapped"
    return {
        "Core_Python_Package_Name": inv["Core_Python_Package_Name"],
        "OpenTeams_Title": inv["OpenTeams_Title"],
        "identity_source": source,
        "associator_key": "",
        "associator_status": status,
        "primary_purl": primary,
        "primary_type": ptype,
        "alternative_purls": join_list(alts),
        "cpes": "",
        "conda_purl": "" if na(inv.get("Conda-forge_PURL")) else inv["Conda-forge_PURL"],
        "source_repository_url": src,
        "OpenTeams_Issue_URL": issue_url(inv, board),
        "Verification_Timestamp_UTC": timestamp,
    }


def from_board_only(name: str, url: str, packages: dict, timestamp: str) -> dict[str, str]:
    rec, key = lookup_assoc(name, packages)
    if rec and key:
        row = from_assoc(
            {
                "Core_Python_Package_Name": name,
                "OpenTeams_Title": f"[Conda-Forge Packaging] {name}",
                "Conda-forge_PURL": "",
                "Source_Repository_URL": "",
                "OpenTeams_Issue_URL": url,
            },
            rec,
            key,
            timestamp,
            board={name: url},
        )
        row["identity_source"] = "openteams-board"
        return row
    return {
        "Core_Python_Package_Name": name,
        "OpenTeams_Title": f"[Conda-Forge Packaging] {name}",
        "identity_source": "openteams-board",
        "associator_key": "",
        "associator_status": "unmapped",
        "primary_purl": "",
        "primary_type": "",
        "alternative_purls": "",
        "cpes": "",
        "conda_purl": "",
        "source_repository_url": "",
        "OpenTeams_Issue_URL": url,
        "Verification_Timestamp_UTC": timestamp,
    }


def read_inventory_tab(xlsx: Path) -> list[dict[str, str]]:
    wb = load_workbook(xlsx, read_only=True, data_only=True)
    ws = wb[TAB_IN]
    rows_iter = ws.iter_rows(values_only=True)
    header = [str(h) if h is not None else "" for h in next(rows_iter)]
    rows = []
    for raw in rows_iter:
        rows.append({h: ("" if v is None else str(v).strip()) for h, v in zip(header, raw)})
    wb.close()
    return rows


def write_csv(path: Path, records: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for rec in records:
            w.writerow(rec)


def write_xlsx_tab(xlsx: Path, records: list[dict[str, str]]) -> None:
    wb = load_workbook(xlsx)
    if TAB_OUT in wb.sheetnames:
        del wb[TAB_OUT]
    ws = wb.create_sheet(TAB_OUT)
    ws.append(COLUMNS)
    for rec in records:
        ws.append([rec[c] for c in COLUMNS])
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(xlsx)
    wb.close()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def md_cell(value: str) -> str:
    return (
        (value or "")
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
        .replace("<", "\\<")
    )


def write_gist_markdown(
    path: Path,
    records: list[dict[str, str]],
    xlsx: Path,
    gist_id: str,
) -> None:
    rows = sorted(
        records, key=lambda r: (r.get("Core_Python_Package_Name") or "").lower()
    )
    src_counts = Counter(r.get("identity_source", "") for r in rows)
    fills = {h: sum(1 for r in rows if r.get(h)) for h in COLUMNS}
    ts = rows[0].get("Verification_Timestamp_UTC", "") if rows else ""
    sha = file_sha256(xlsx) if xlsx.is_file() else ""
    lines: list[str] = [
        "---",
        "id: mgmt-wf-python-modernization-identity",
        "title: OpenTeams CDO Python modernization identity snapshot",
        "format: gfm-table",
        "primary_key: Core_Python_Package_Name",
        f"rows: {len(rows)}",
        f"columns: {len(COLUMNS)}",
        f"generated: {ts}",
        "source_workbook: docs/Analysis_Dataset-2026-08-12.xlsx",
        "source_tab: identity-2026-08-12",
        f"workbook_sha256: {sha}",
        "generator: scripts/conda-forge-packaging-inventory-operations_openteams_identity.py",
        "blank_means: missing",
        'multi_value_separator: "; "',
        f"gist_id: {gist_id}",
        "parse:",
        '  - GFM pipe table below heading "## Identity rows"',
        "  - Header row is the canonical column names; do not rename",
        "  - One package per row; Core_Python_Package_Name is unique",
        "  - Empty cell = missing / not applicable (never N/A in this snapshot)",
        "  - URLs are raw (not markdown links) so they copy as-is",
        "identity_source:",
    ]
    for key, count in sorted(src_counts.items()):
        lines.append(f"  {key}: {count}")
    lines.append("filled:")
    for col in COLUMNS:
        lines.append(f"  {col}: {fills[col]}")
    lines.extend(
        [
            "---",
            "",
            "# mgmt-wf-python-modernization identity",
            "",
            "Snapshot of workbook tab `identity-2026-08-12`: one row per OpenTeams",
            "universe name (`CDO-ENT-JFROG` ∪ `CDO-ENT-CONDA`) plus board-only",
            "`[Conda-Forge Packaging]` extras from org project 1 view 6",
            "(OSS Enhancements).",
            "",
            f"- Rows: **{len(rows):,}**",
            "- Primary key: `Core_Python_Package_Name` (unique)",
            f"- Generated: `{ts}`",
            "- Source: `docs/Analysis_Dataset-2026-08-12.xlsx` tab `identity-2026-08-12`",
            f"- Workbook sha256: `{sha}`",
            f"- Gist id (edit in place on every rerun; id is not stored in git): `{gist_id}`",
            "",
            "## Parse contract",
            "",
            "1. Skip YAML frontmatter (`---` … `---`).",
            "2. The data table starts at `## Identity rows`.",
            "3. Split rows on `|`; trim cell whitespace; unescape `\\|` and `\\\\`.",
            "4. Multi-value cells (`alternative_purls`, `cpes`, `Conda-Forge_FeedStock_URL`, `Local_Recipes_URL`) split on `'; '`.",
            "5. Blank cell means missing. Do not invent URLs or PURLs.",
            "",
            "## Column schema",
            "",
            "| column | type | required | meaning |",
            "| --- | --- | --- | --- |",
        ]
    )
    for name, typ, req, meaning in GIST_SCHEMA:
        lines.append(f"| `{name}` | {typ} | {req} | {meaning} |")
    lines.extend(
        [
            "",
            "## Identity rows",
            "",
            "| " + " | ".join(md_cell(h) for h in COLUMNS) + " |",
            "| " + " | ".join("---" for _ in COLUMNS) + " |",
        ]
    )
    for rec in rows:
        lines.append("| " + " | ".join(md_cell(rec.get(c, "")) for c in COLUMNS) + " |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def publish_identity_gist(gh: str, gist_id: str, filename: str, md_path: Path) -> None:
    subprocess.check_call(
        [gh, "gist", "edit", gist_id, "--filename", filename, str(md_path)]
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--xlsx",
        type=Path,
        default=Path("docs/Analysis_Dataset-2026-08-12.xlsx"),
    )
    p.add_argument(
        "--associator",
        type=Path,
        default=Path("/tmp/purl-associator-mappings-index.json"),
    )
    p.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Optional CSV path. Default: skip CSV (workbook tab only).",
    )
    p.add_argument(
        "--project-items",
        type=Path,
        default=None,
        help="Cached GitHub project items JSON. Default: fetch live project 1.",
    )
    p.add_argument(
        "--cache-dir",
        type=Path,
        default=CACHE_DIR,
        help="Cache dir for feedstock-outputs and staged-recipes PR lists.",
    )
    p.add_argument(
        "--feedstock-outputs",
        type=Path,
        default=None,
        help="feedstock-outputs.json (conda-forge.org/packages data).",
    )
    p.add_argument(
        "--staged-prs",
        type=Path,
        default=None,
        help="TSV of all staged-recipes PRs (number,state,merged_at,url,title).",
    )
    p.add_argument(
        "--staged-open-prs",
        type=Path,
        default=None,
        help="JSON from gh pr list --state open --json number,title,url,files.",
    )
    p.add_argument(
        "--recipes-dir",
        type=Path,
        default=REPO_ROOT / "recipes",
        help="Local recipes/ directory.",
    )
    p.add_argument(
        "--refresh-staged-prs",
        action="store_true",
        help="Re-fetch staged-recipes PR lists even if cache exists.",
    )
    p.add_argument(
        "--skip-gist",
        action="store_true",
        help="Do not edit the pinned identity gist (offline tests only).",
    )
    p.add_argument(
        "--gist-id",
        default=None,
        help=(
            "Secret gist to edit in place. Default: "
            f"{GIST_ID_ENV} or {LOCAL_ENV_PATH.name}. Never commit the id."
        ),
    )
    args = p.parse_args()
    cache = args.cache_dir
    cache.mkdir(parents=True, exist_ok=True)
    feedstock_path = args.feedstock_outputs or cache / "feedstock-outputs.json"
    staged_tsv = args.staged_prs or cache / "staged-recipes-prs.tsv"
    staged_open = args.staged_open_prs or cache / "staged-recipes-open-prs.json"

    packages = json.loads(args.associator.read_text())["packages"]
    inventory = read_inventory_tab(args.xlsx)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if args.project_items:
        items = json.loads(args.project_items.read_text())
    else:
        gh = gh_bin()
        if not gh:
            print("gh not found; pass --project-items", file=sys.stderr)
            return 1
        print(f"Fetching OpenTeams project 1 via {gh} ...", flush=True)
        items = fetch_project_issues(gh)
    board = board_packaging_urls(items)

    fs_map, meta_map = load_feedstock_outputs(feedstock_path)
    staged_map = load_staged_prs(
        staged_tsv, staged_open, gh_bin(), args.refresh_staged_prs
    )
    local_map = load_local_recipes(args.recipes_dir)
    inv_by_name = {
        pep503_name(row["Core_Python_Package_Name"]): row for row in inventory
    }

    records = []
    seen: set[str] = set()
    for inv in inventory:
        name = pep503_name(inv["Core_Python_Package_Name"])
        seen.add(name)
        rec, key = lookup_assoc(inv["Core_Python_Package_Name"], packages)
        row = (
            from_assoc(inv, rec, key, timestamp, board)
            if rec and key
            else from_inventory(inv, timestamp, board)
        )
        records.append(
            attach_packaging_urls(row, fs_map, meta_map, staged_map, local_map, inv)
        )
    extra = 0
    for name, url in sorted(board.items()):
        if name in seen:
            continue
        row = from_board_only(name, url, packages, timestamp)
        records.append(
            attach_packaging_urls(
                row, fs_map, meta_map, staged_map, local_map, inv_by_name.get(name)
            )
        )
        extra += 1

    write_xlsx_tab(args.xlsx, records)
    if args.output_csv:
        write_csv(args.output_csv, records)

    counts = Counter(r["identity_source"] for r in records)
    print(f"Wrote {len(records):,} rows to {args.xlsx} tab {TAB_OUT}")
    if args.output_csv:
        print(f"Wrote CSV {args.output_csv}")
    print("identity_source:", dict(counts))
    print("board packaging issues:", len(board))
    print("board-only extra rows:", extra)
    print("has primary_purl:", sum(1 for r in records if r["primary_purl"]))
    print("has conda_purl:", sum(1 for r in records if r["conda_purl"]))
    print("has OpenTeams_Issue_URL:", sum(1 for r in records if r["OpenTeams_Issue_URL"]))
    print(
        "has Conda-Forge_FeedStock_URL:",
        sum(1 for r in records if r["Conda-Forge_FeedStock_URL"]),
    )
    print(
        "has Conda-Forge_Metadata_URL:",
        sum(1 for r in records if r["Conda-Forge_Metadata_URL"]),
    )
    print(
        "has Staged_Recipes_PR_URL:",
        sum(1 for r in records if r["Staged_Recipes_PR_URL"]),
    )
    print("has Local_Recipes_URL:", sum(1 for r in records if r["Local_Recipes_URL"]))
    print("Verification_Timestamp_UTC:", timestamp)

    if args.skip_gist:
        print("Skipped gist publish (--skip-gist)")
        return 0
    gist_id = resolve_gist_id(args.gist_id)
    if not gist_id:
        print(
            "Skipped gist publish (set "
            f"{GIST_ID_ENV}, {LOCAL_ENV_PATH}, or --gist-id)",
            flush=True,
        )
        return 0
    gh = gh_bin()
    if not gh:
        print("gh not found; pass --skip-gist to skip identity gist publish", file=sys.stderr)
        return 1
    md_path = cache / GIST_FILENAME
    write_gist_markdown(md_path, records, args.xlsx, gist_id)
    print(f"Publishing {md_path} to gist {gist_id} ...", flush=True)
    publish_identity_gist(gh, gist_id, GIST_FILENAME, md_path)
    print(f"Updated gist {gist_id} (gh gist view {gist_id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
