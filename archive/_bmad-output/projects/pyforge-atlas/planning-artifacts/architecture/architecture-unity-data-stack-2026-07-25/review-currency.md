---
title: 'Architecture Spine Review — Technology Currency / Reality Check'
reviewer: currency
date: 2026-07-25
verdict: PASS (with notes)
---

# Currency Review — Unity Data Stack Architecture Spine

Scope: every version in the **Stack** table, every technology named in an AD, and the two AQ
items touching version/existence facts (AQ-1 OpenShift/K8s, AQ-8 Dagster-on-3.14). Verified via
WebFetch against PyPI JSON API, `mamba search -c conda-forge` (live channel query, more reliable
than fetching multi-MB anaconda.org JSON through a summarizing fetch), GitHub Releases/API, and
each project's own spec site. WebSearch was not used (budget exhausted for this session, per
instruction).

## Stack table — item by item

| Item | Claimed | Verified (source) | Status |
|---|---|---|---|
| Python (primary) | 3.13, 3.14 | Both stable/released; latest patches 3.13.14, 3.14.6 (python.org/downloads) | VERIFIED |
| Python (legacy) | 3.12 | Confirmed in "security" maintenance phase, EOL Oct 2028 (python.org/downloads) | VERIFIED |
| pixi | 0.73.0 | GitHub `prefix-dev/pixi` latest release = v0.73.0, published 2026-07-15; conda-forge `latest_version` = 0.73.0 | VERIFIED |
| uv | 0.11.32 | PyPI `info.version` = 0.11.32 (exact match). **conda-forge latest available = 0.11.31** — one patch behind PyPI at check time | VERIFIED (PyPI); channel-lag caveat — see below |
| pip | 26.1.2 | PyPI `info.version` = 26.1.2; conda-forge also carries 26.1.2 | VERIFIED |
| PEP 751 `pylock.toml` | lock-version 1.0 | peps.python.org/pep-0751: Status **Final**, Resolution 2025-03-31; spec text: `"the initial version – and only valid value until future updates... — as '1.0'"` | VERIFIED |
| Dagster | 1.13.15 | PyPI `info.version` = 1.13.15; conda-forge `dagster=1.13.15` has 5 build variants spanning `python >=3.10` through `python >=3.14` | VERIFIED |
| Kedro | 1.5.0 | PyPI `info.version` = 1.5.0; conda-forge latest = 1.5.0, noarch build `python >=3.10,<4.0` (no upper cap excluding 3.13/3.14) | VERIFIED |
| DuckDB | 1.5.5 | PyPI `duckdb` `info.version` = 1.5.5; conda-forge `python-duckdb` latest = 1.5.5 | VERIFIED |
| Ruff | 0.16.0 | PyPI `info.version` = 0.16.0; conda-forge latest = 0.16.0 (platform-native, no python dep, as expected for a Rust binary) | VERIFIED |
| pytest | 9.1.1 | PyPI `info.version` = 9.1.1; conda-forge latest = 9.1.1, `python >=3.10` (no ceiling) | VERIFIED |
| deptry | 0.25.1 | PyPI `info.version` = 0.25.1; conda-forge `deptry=0.25.1` has explicit build variants for `python >=3.10` through `python >=3.14` | VERIFIED |
| CycloneDX | 1.7 (ECMA-424) | cyclonedx.org/specification/overview: current version **1.7** (2025-10-21), Ecma International published as **ECMA-424** on 2025-12-10, no newer major spec version. (A `1.7.1` errata/patch tag exists on `CycloneDX/specification` but the published spec version is still stated as "1.7" — doesn't change the pin) | VERIFIED |
| SLSA | v1.2 | slsa.dev/spec/v1.2/ and /spec/: v1.2 is explicitly "Approved" and the current version (v1.1 and a Working Draft also exist but are not newer) | VERIFIED |

**14/14 Stack items verified against a live source.** 13 are exact byte-for-byte matches to the
"current 2026-07-25" claim. One (uv) carries a caveat, not a failure — see below.

### uv: PyPI-vs-conda-forge channel lag (the one item worth flagging)

The pin (0.11.32) is exactly PyPI's latest — correctly verified there. But `mamba search -c
conda-forge uv` tops out at **0.11.31**; conda-forge's build of 0.11.32 had not landed at
check time. This is ordinary bot-lag (hours-to-days), not a stale/invented claim — the spine's
"Verified current 2026-07-25" statement is defensible since it's true on the source the authors
most plausibly checked (PyPI, where `uv` is published). Flagging because AD-2/AA-1 make conda-forge
the authoritative channel for this platform: if the Workspace Lock resolves `uv` from conda-forge
specifically, the effective floor on day one is 0.11.31, not 0.11.32. Not a defect in the spine;
worth a one-line footnote in *Stack* the next time it's touched.

## AD-level technology claims (not in the Stack table but asserted as fact)

| Claim | Where | Verified | Status |
|---|---|---|---|
| PEP 751 `environments` markers describe *intent*, not a coverage guarantee (the premise for AD-3's whole rule) | AD-3 prose | Confirmed against PEP 751 text: `environments` is "a list of Environment Markers for which the lock file is considered compatible with" — a compatibility filter, not an install-success guarantee. Matches the spine's characterization exactly | VERIFIED |
| Dagster (orchestrator) + Kedro (data-science toolbox) is a real, current, supported pairing, not a training-data-vintage assumption | Stack / Capability Map | `stateful-y/kedro-dagster` (23 stars, last pushed 2026-07-25 — today) plus a live `conda-forge/kedro-dagster-feedstock` (pushed 2026-06-22) confirm an actively maintained integration exists on the mandated channel | VERIFIED |
| SLSA Build L1→L2 progression is a real, current track structure (AD-12) | AD-12 | slsa.dev/spec/v1.2/ confirms the Build Track/level structure is live under the current approved spec | VERIFIED |

No AD-level assertion was found that reads as an unchecked training-data claim once the Stack
table and the above three were verified — every quantitative or existence claim I could locate
traces to one of the sources above.

## AQ-1 (OpenShift/Kubernetes baseline) — the declared open question

Independently re-attempted: `docs.redhat.com/en/documentation/openshift_container_platform` →
**HTTP 403**, reproducing the spine's own finding exactly (not an oversight — genuinely gated).
Tried two alternates:
- `access.redhat.com/support/policy/updates/openshift` — accessible, but describes only the *EUS
  policy mechanism* (even-numbered minors get Extended Update Support), not a specific pinned
  version/date; doesn't resolve AQ-1.
- `kubernetes.io/releases/` — accessible, gives **upstream** Kubernetes 1.36.2 (EOL 2027-06-28) as
  current — but OpenShift bundles its own (typically older, offset) Kubernetes minor and versions
  independently, so this doesn't substitute for the OpenShift-specific baseline AQ-1 actually asks
  for.

**Conclusion: AQ-1 is correctly stated as an open question.** I could not resolve it from an
accessible source either, which confirms the spine did not silently invent a value — it did the
right thing by leaving it open.

## AQ-8 (is Dagster built for Python 3.14 on the mandated channel?) — resolvable now, favorably

This is currently listed as open ("Verify before pinning"). Live channel query answers it: yes —
conda-forge's `dagster=1.13.15` ships a `python >=3.14` build today. Not a defect (the spine
correctly declined to assert this without checking), just a note that this particular open
question can likely close on next pass, with a positive answer.

## "Not pinned here, and deliberately" — is the reasoning sound?

PostgreSQL, MongoDB, Redis, MinIO, Django, Wagtail, FastAPI, Node are left unpinned with the
stated reason "Package-level choices governed by AD-14, not spine invariants." That reasoning
holds architecturally — none of these are spine-load-bearing paradigm choices, and AD-14 already
requires a single declared version with a floor+ceiling wherever they do get pinned, so deferring
the number itself to Package authoring time is consistent, not a gap. One forward-looking note,
not a spine defect: Redis (RSALv2/SSPLv1 → back to AGPLv3 under Redis 8, 2024–2025) and MinIO
(Community-edition web UI moved behind AGPL, 2025) both had real licensing-posture changes in the
last two years. Given how much this architecture leans on license compliance (AD-8 Mandate
classification, the Warden compliance chain), whoever pins these at Package level should
re-verify license, not just version, at that time — the spine's deferral is fine, this is just
where that check needs to land.

## Summary verdict

**PASS (with notes).** All 14 Stack-table versions verify against a live source for 2026-07-25;
13 are exact matches, 1 (uv) has a real but minor PyPI-vs-conda-forge one-patch lag worth a
footnote. Every external technology claim embedded in an AD (PEP 751 semantics, SLSA track
structure, the Dagster+Kedro pairing) checks out against its own source rather than reading as an
asserted-from-memory claim. AQ-1 was independently re-attempted and confirmed genuinely blocked,
not an authoring shortcut. AQ-8 is answerable now (favorably) but was correctly left open rather
than asserted. No stale or unverifiable Stack items found.
