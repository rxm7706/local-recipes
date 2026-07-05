#!/usr/bin/env python3
"""
SBOM emitters — shared by scan_project.py and inventory_channel.py.

Always includes the vulnerabilities[] section per project's design choice
(option A: complete-but-larger SBOMs over portable-but-incomplete ones).

Two formats:
  - CycloneDX 1.6 JSON (vulnerability-centric, OWASP-aligned)
  - SPDX 2.3 JSON (license-centric, Linux Foundation standard)

Public API:
  emit_cyclonedx(deps, vulns_by_dep, project_name, atlas_records=None) -> dict
  emit_spdx(deps, vulns_by_dep, project_name, atlas_records=None) -> dict

Where:
  deps: list of objects with .name, .version, .ecosystem, .manifest, .extras
        (matches scan_project.Dep dataclass; inventory_channel uses a parallel
        Package class with the same shape)
  vulns_by_dep: dict mapping "<eco>:<name>@<version>" to list of vuln dicts
                with keys id, severity, cvss_score, cvss_version, cvss_vector,
                description, cwe, kev, matching_vers
  atlas_records: optional dict mapping "<eco>:<name>" to atlas row dict;
                 when present, fills license + supplier info in components
"""
from __future__ import annotations

import datetime as dt
import json
import re
import uuid
from pathlib import Path
from typing import Any

TOOL_NAME = "conda-forge-expert"
TOOL_VERSION = "5.11.0"
TOOL_VENDOR = "rxm7706"


def _bom_ref(eco: str, name: str, version: str | None) -> str:
    return f"{eco}-{name}-{version or 'unknown'}"


def _spdx_id(eco: str, name: str, version: str | None) -> str:
    raw = f"{eco}-{name}-{version or 'unknown'}"
    # SPDX IDs allow [a-zA-Z0-9.-]; underscores+@ get replaced
    safe = "".join(c if c.isalnum() or c in ".-" else "-" for c in raw)
    return f"SPDXRef-{safe}"


def _purl(
    eco: str,
    name: str,
    version: str | None,
    qualifiers: dict[str, str] | None = None,
) -> str:
    """Build a purl; qualifiers are appended sorted-by-key (purl spec).

    conda purls must carry `?channel=conda-forge` (G98) — callers pass
    `qualifiers={"channel": "conda-forge"}` for the conda ecosystem.
    """
    base = f"pkg:{eco}/{name}"
    if version:
        base = f"{base}@{version}"
    if qualifiers:
        pairs = "&".join(f"{k}={v}" for k, v in sorted(qualifiers.items()))
        base = f"{base}?{pairs}"
    return base


# --- SPDX license normalization (cyclonedx-universe-inventory Wave B / S3) --

# SPDX idstring: letters, digits, '.', '-', with an optional trailing '+'.
_SPDX_ID_RE = re.compile(r"^[A-Za-z0-9.\-]+\+?$")
_SPDX_OPERATORS = {"AND", "OR", "WITH"}

# CycloneDX 1.6 enum-constrains `license.id` to the canonical SPDX license
# list ($ref spdx.schema.json). A shape-only check would emit schema-invalid
# ids for live conda junk (`PSF`, `GPLv2`, `LicenseRef-*`) — the enum ships
# as tracked skill data and is the id-branch gate.
_SPDX_ENUM_PATH = Path(__file__).resolve().parent.parent / "data" / "spdx.schema.json"
_SPDX_ENUM_CACHE: frozenset[str] | None = None


def _spdx_id_enum() -> frozenset[str]:
    global _SPDX_ENUM_CACHE
    if _SPDX_ENUM_CACHE is None:
        try:
            data = json.loads(_SPDX_ENUM_PATH.read_text(encoding="utf-8"))
            _SPDX_ENUM_CACHE = frozenset(data.get("enum", ()))
        except (OSError, json.JSONDecodeError, AttributeError):
            # Enum unavailable → no string can prove itself a canonical id;
            # everything falls through to expression/name (schema-safe).
            _SPDX_ENUM_CACHE = frozenset()
    return _SPDX_ENUM_CACHE


def _is_spdx_expression(text: str) -> bool:
    """Grammar-level check for a compound SPDX license expression.

    Validates STRUCTURE only (operands, case-sensitive uppercase AND/OR/WITH,
    balanced parens) — not license-list membership, which needs the SPDX list
    and is the conda-forge linter's job. Lowercase operators (`x and y`) are
    NOT valid SPDX and correctly fail this check.
    """
    tokens = re.findall(r"\(|\)|[^\s()]+", text)
    if len(tokens) < 3:
        return False
    depth = 0
    expect_operand = True
    # SPDX allows exactly ONE `WITH exception` per simple expression, and
    # only directly after a plain license id (not after `)` or another WITH).
    last_operand_plain = False
    prev_with = False
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "(":
            if not expect_operand:
                return False
            depth += 1
        elif tok == ")":
            if expect_operand or depth == 0:
                return False
            depth -= 1
            last_operand_plain = False
        elif tok in ("AND", "OR"):
            if expect_operand:
                return False
            expect_operand = True
            prev_with = False
        elif tok == "WITH":
            if (expect_operand or prev_with or not last_operand_plain
                    or i + 1 >= len(tokens)):
                return False
            i += 1
            if not _SPDX_ID_RE.match(tokens[i]):
                return False
            prev_with = True
        else:
            if not expect_operand or not _SPDX_ID_RE.match(tok):
                return False
            expect_operand = False
            last_operand_plain = True
        i += 1
    return depth == 0 and not expect_operand


def normalize_license(license_str: str | None) -> dict[str, Any] | None:
    """Map a raw conda license string to a schema-valid CycloneDX entry.

    - single CANONICAL SPDX id (enum-checked) → {"license": {"id": ...}}
    - valid SPDX *expression* (grammar)       → {"expression": ...}
    - anything else (incl. idstring-shaped
      junk like `PSF`/`GPLv2`, `LicenseRef-*`) → {"license": {"name": ...}}

    The pre-Wave-B emitter always used {"license": {"id": ...}}, which is
    schema-INVALID for expressions (live data: `0BSD AND LGPL-2.1-or-later`),
    for junk, AND for shape-plausible non-enum ids — CycloneDX 1.6
    enum-constrains `license.id` to the canonical SPDX list.
    """
    if not license_str:
        return None
    s = str(license_str).strip()
    if not s:
        return None
    if _SPDX_ID_RE.match(s):
        if s in _spdx_id_enum():
            return {"license": {"id": s}}
        return {"license": {"name": s}}
    if _is_spdx_expression(s):
        return {"expression": s}
    return {"license": {"name": s}}


def emit_cyclonedx(
    deps: list[Any],
    vulns_by_dep: dict[str, list[dict[str, Any]]],
    project_name: str = "scan",
    atlas_records: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Emit a CycloneDX 1.6 BOM as a dict (caller does json.dumps).

    Always includes vulnerabilities[] populated from vulns_by_dep.
    """
    atlas_records = atlas_records or {}
    serial = f"urn:uuid:{uuid.uuid4()}"
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    components: list[dict[str, Any]] = []
    component_refs: dict[str, str] = {}  # "<eco>:<name>@<version>" -> bom-ref
    for dep in deps:
        qualifiers = {"channel": "conda-forge"} if dep.ecosystem == "conda" else None
        purl = _purl(dep.ecosystem, dep.name, dep.version, qualifiers)
        ref = _bom_ref(dep.ecosystem, dep.name, dep.version)
        dep_key = f"{dep.ecosystem}:{dep.name}@{dep.version}"
        component_refs[dep_key] = ref
        comp: dict[str, Any] = {
            "type": "library",
            "bom-ref": ref,
            "name": dep.name,
            "version": dep.version or "",
            "purl": purl,
        }
        # License from atlas if available (conda/pypi packages)
        atlas_key = f"{dep.ecosystem}:{dep.name}"
        if atlas_key in atlas_records:
            entry = normalize_license(atlas_records[atlas_key].get("conda_license"))
            if entry:
                comp["licenses"] = [entry]
        # Manifest property
        manifest = getattr(dep, "manifest", None)
        if manifest:
            comp.setdefault("properties", []).append(
                {"name": "manifest", "value": str(manifest)}
            )
        components.append(comp)

    # Dependencies graph (Cargo dep-tree if present)
    dependencies: list[dict[str, Any]] = []
    for dep in deps:
        ref = _bom_ref(dep.ecosystem, dep.name, dep.version)
        depends_on_raw = (getattr(dep, "extras", {}) or {}).get("depends_on", [])
        ref_list: list[str] = []
        for d in depends_on_raw:
            if "@" in d:
                n, v = d.split("@", 1)
                ref_list.append(_bom_ref(dep.ecosystem, n.lower(), v))
        if ref_list:
            dependencies.append({"ref": ref, "dependsOn": sorted(set(ref_list))})

    # Vulnerabilities — always included (option A)
    vulnerabilities: list[dict[str, Any]] = []
    cvss_method_map = {
        "v4": "CVSSv4", "v3.1": "CVSSv31", "v3.0": "CVSSv3",
        "v3": "CVSSv3", "v2": "CVSSv2",
    }
    for dep_key, vlist in vulns_by_dep.items():
        ref = component_refs.get(dep_key)
        if not ref:
            continue
        for v in vlist:
            vid = v.get("id", "?")
            entry: dict[str, Any] = {
                "bom-ref": f"vuln-{vid}-{ref}",
                "id": vid,
                "affects": [{"ref": ref}],
            }
            # CVSS rating
            if v.get("cvss_score"):
                rating: dict[str, Any] = {
                    "score": float(v["cvss_score"]),
                    "method": cvss_method_map.get(v.get("cvss_version", ""), "Other"),
                }
                if v.get("severity") and v["severity"] != "Unknown":
                    rating["severity"] = v["severity"].lower()
                if v.get("cvss_vector"):
                    rating["vector"] = v["cvss_vector"]
                entry["ratings"] = [rating]
            if v.get("description"):
                entry["description"] = v["description"]
            if v.get("cwe"):
                cwe_num = str(v["cwe"]).replace("CWE-", "").strip()
                if cwe_num.isdigit():
                    entry["cwes"] = [int(cwe_num)]
            if v.get("kev"):
                entry["analysis"] = {"state": "exploitable", "detail": "Listed in CISA KEV catalog"}
            vulnerabilities.append(entry)

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": serial,
        "version": 1,
        "metadata": {
            "timestamp": timestamp,
            "tools": {
                "components": [{
                    "type": "application",
                    "name": TOOL_NAME,
                    "version": TOOL_VERSION,
                    "publisher": TOOL_VENDOR,
                }],
            },
            "component": {
                "type": "application",
                "name": project_name,
                "bom-ref": project_name,
            },
        },
        "components": components,
        "dependencies": dependencies,
        "vulnerabilities": vulnerabilities,
    }


def emit_spdx(
    deps: list[Any],
    vulns_by_dep: dict[str, list[dict[str, Any]]],
    project_name: str = "scan",
    atlas_records: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Emit an SPDX 2.3 document as a dict.

    SPDX doesn't have a native vulnerabilities[] section; we attach them as
    annotations on the affected packages (per SPDX 2.3 spec).
    """
    atlas_records = atlas_records or {}
    doc_id = "SPDXRef-DOCUMENT"
    doc_ns = f"https://github.com/rxm7706/local-recipes/sbom/{project_name}-{uuid.uuid4()}"
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    packages: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    pkg_refs: dict[str, str] = {}

    for dep in deps:
        spdx_id = _spdx_id(dep.ecosystem, dep.name, dep.version)
        dep_key = f"{dep.ecosystem}:{dep.name}@{dep.version}"
        pkg_refs[dep_key] = spdx_id
        purl = _purl(dep.ecosystem, dep.name, dep.version)
        pkg: dict[str, Any] = {
            "SPDXID": spdx_id,
            "name": dep.name,
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": False,
            "licenseConcluded": "NOASSERTION",
            "licenseDeclared": "NOASSERTION",
            "copyrightText": "NOASSERTION",
        }
        if dep.version:
            pkg["versionInfo"] = dep.version
        if purl:
            pkg["externalRefs"] = [{
                "referenceCategory": "PACKAGE-MANAGER",
                "referenceType": "purl",
                "referenceLocator": purl,
            }]
        # License from atlas
        atlas_key = f"{dep.ecosystem}:{dep.name}"
        if atlas_key in atlas_records:
            license_str = atlas_records[atlas_key].get("conda_license")
            if license_str:
                pkg["licenseConcluded"] = license_str
                pkg["licenseDeclared"] = license_str
        # Vulnerability annotations
        vlist = vulns_by_dep.get(dep_key, [])
        if vlist:
            annotations = []
            for v in vlist:
                vid = v.get("id", "?")
                sev = v.get("severity", "Unknown")
                score = v.get("cvss_score")
                desc = v.get("description", "")[:100]
                comment = f"VULN: {vid} severity={sev}"
                if score:
                    comment += f" cvss={score}"
                if desc:
                    comment += f" — {desc}"
                annotations.append({
                    "annotationDate": timestamp,
                    "annotationType": "REVIEW",
                    "annotator": f"Tool: {TOOL_NAME}-{TOOL_VERSION}",
                    "comment": comment,
                })
            pkg["annotations"] = annotations
        packages.append(pkg)
        relationships.append({
            "spdxElementId": doc_id,
            "relationshipType": "DESCRIBES",
            "relatedSpdxElement": spdx_id,
        })

    # Dependency relationships (Cargo dep-tree)
    for dep in deps:
        spdx_id = _spdx_id(dep.ecosystem, dep.name, dep.version)
        depends_on_raw = (getattr(dep, "extras", {}) or {}).get("depends_on", [])
        for d in depends_on_raw:
            if "@" in d:
                n, v = d.split("@", 1)
                target_id = _spdx_id(dep.ecosystem, n.lower(), v)
                relationships.append({
                    "spdxElementId": spdx_id,
                    "relationshipType": "DEPENDS_ON",
                    "relatedSpdxElement": target_id,
                })

    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": doc_id,
        "name": project_name,
        "documentNamespace": doc_ns,
        "creationInfo": {
            "created": timestamp,
            "creators": [f"Tool: {TOOL_NAME}-{TOOL_VERSION}"],
        },
        "packages": packages,
        "relationships": relationships,
    }
