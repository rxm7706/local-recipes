---
spec: enterprise-airgap
status: shipped
owner-dream: docs/dreams/enterprise-airgap.md
program: regenerable-factory (Wave 3)
surface:
  - .claude/skills/conda-forge-expert/scripts/_http.py
  - docs/reference/pixi-config-jfrog.example.toml
companions:
  - ../../../../../docs/reference/enterprise-deployment.md   # adopted: deployment guide
open_questions:
  - "JFROG_API_KEY injects unconditionally on every outbound request
    regardless of host — cross-resolver credential leak (Doctor finding,
    Steward remediation): host-gate the header in _http.make_request."
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
- **CAP-2 — offline-safe read side.** Intent: all atlas read-side CLIs
  answer from local state (cf_atlas.db, caches) with no network dependency.
  Success: read commands succeed with networking disabled.
- **CAP-3 — mirror-friendly data paths.** Intent: bulk data acquisition uses
  artifacts a mirror can serve verbatim (e.g. `current_repodata.json` over
  the sharded protocol). Success: pipeline phases run against a JFrog
  remote-repo mirror unchanged.

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
