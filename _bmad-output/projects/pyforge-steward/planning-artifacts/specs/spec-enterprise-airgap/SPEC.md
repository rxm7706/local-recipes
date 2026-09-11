---
spec: enterprise-airgap
status: shipped
updated: "2026-09-09"
owner-dream: docs/dreams/enterprise-airgap.md
program: regenerable-factory (Wave 3)
surface:
  - .claude/skills/conda-forge-expert/scripts/_http.py
  - docs/reference/pixi-config-jfrog.example.toml
companions:
  - ../../../../../../docs/reference/enterprise-deployment.md   # adopted: deployment guide
open_questions: []
---

# SPEC — the factory behind the firewall

## Why

The factory must run identically on the open internet and inside an
air-gapped enterprise (JFrog Artifactory, internal mirrors) without forked
code or committed configuration. Owner: Steward (the estate).

## Capabilities

- **CAP-1 — runtime-driven routing.** Intent: every outbound HTTP call goes
  through one chokepoint (`_http.py`) that resolves trust (truststore) and
  auth (JFrog / GitHub / `.netrc` chain) from environment variables at call
  time; zero enterprise endpoints in tracked files. Success: the same
  checkout works behind Artifactory by setting env vars only; grep finds no
  committed enterprise URL/credential.
  - **verified:** 2026-09-11 — `test_http_jfrog_host_gate.py` + `test_http_resolvers.py` +
    `test_http_skip_auth.py` (135/135) cover the env-var-derived host gate; a repo grep for
    real enterprise hostnames finds only illustrative placeholders in docstrings/help text
    (`artifactory.corp`, `your-jfrog`), no committed live endpoint or credential.
- **CAP-2 — offline-safe read side.** Intent: all atlas read-side CLIs
  answer from local state (cf_atlas.db, caches) with no network dependency.
  Success: read commands succeed with networking disabled.
  - **verified:** 2026-09-11 — live: `staleness-report --json` run with `http_proxy`/
    `https_proxy` pointed at an unreachable address (forcing any real network call to fail)
    still returned complete, real JSON output against the local `cf_atlas.db`, exit 0.
- **CAP-3 — mirror-friendly data paths.** Intent: bulk data acquisition uses
  artifacts a mirror can serve verbatim (e.g. `current_repodata.json` over
  the sharded protocol). Success: pipeline phases run against a JFrog
  remote-repo mirror unchanged.
  - **verified:** 2026-09-11 — code-level: `conda_forge_atlas.py::_fetch_current_repodata`
    (Phase B) resolves base URLs through the same `_resolve_conda_forge_urls()` chokepoint as
    CAP-1 (JFrog env var/pixi config first, then prefix.dev, then anaconda.org) and fetches a
    single-file `{base_url}/{subdir}/current_repodata.json` — "avoids the sharded msgpack
    protocol" per its own docstring — mirror-servable verbatim. `dependency-checker.py` carries
    the same `_REPODATA_CANDIDATES` preference (current_repodata.json[.bz2] before full
    repodata.json[.bz2]) and a documented `--channel https://artifactory.corp/...` / `file://`
    mirror flag. No live JFrog mirror run performed — per this Spec's own reciprocal-chain
    note the mirror exercise stays unexercised and foundry-side; this verifies the data-path
    shape, not a live mirror round-trip.

## Constraints

- Env-var configuration only; example config ships as
  `docs/reference/pixi-config-jfrog.example.toml`, never as live config.
- The open credential-leak issue above is a NAMED deviation, not accepted
  behavior — the fix is Steward-owned work under this spec's surface.

## Non-goals

- Bundling mirrors or credentials; provisioning the JFrog side itself.

## Success signal

Same-checkout dual-posture operation (open + behind Artifactory via env
vars); offline read-side; the open question closed by a host-gated header
with a regression test.

## Reciprocal chain pointer to mason — 2026-09-09

Mason's `spec-miniforge-installer` names **its own trigger as steward-owned and un-watched**:
*"steward's enterprise-airgap / Story 12.3 work surfaces a private-channel-locking need for a
Python distributable."* The socket already exists and is empty by design —
`src/shared/packages/pyforge-mason/src/pyforge/mason/airgap_contract.py:54`,
`SUPPORTED_DISTRIBUTABLES: dict[str, DistributableBackend] = {}` ("Empty by design (Story 9.2).
External installers register later.").

**So whoever runs the CAP-3 mirror exercise, or Story 12.3's air-gap parity check, must ALSO decide
whether a Python distributable needs private-channel locking — and, if so, tell mason.** The
trigger fires here and nothing watches it from the mason side. This is the reciprocal half of the
Kinship line added to `docs/dreams/enterprise-airgap.md` the same day (batch § 2.3 C7 / Class D
D11).

No capability change: this Spec stays `shipped`, and CAP-3's mirror run remains unexercised and
foundry-side.
