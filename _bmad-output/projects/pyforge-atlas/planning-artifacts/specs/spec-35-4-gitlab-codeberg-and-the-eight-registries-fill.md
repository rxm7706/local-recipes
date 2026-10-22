---
title: "35.4: GitLab, Codeberg and the eight registries fill"
type: 'feature'
created: '2026-10-18'
status: 'in-review'
baseline_revision: '24581b35b8'
flag:
  key: pyforge.atlas.live_vcs_universe            # minted by Story 35.1, shared by Epic 35's feature stories
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through src/platform/config/flag-overlays.json
  scope: global                                   # v1 is global only
  fallback: 'the hosts read their latest tag only and the registries keep the version choices they had before this story'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 3
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-35-1-one-opt-in-switch-and-github-authenticates.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-35-2-the-vcs-batches-come-from-the-whole-universe.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - docs/reference/story-spec-flag-block.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/vcs_sources.py
  - .claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** with Story 35.2's universe batches the GitLab, Codeberg and registry stores have work, but each fetch
differs from legacy:
- GitLab and Codeberg read only the latest tag, with no release and no tag normalization.
- Maven asks `a:<group:artifact>`, which never matches a coordinate.
- NuGet takes the last version listed, a pre-release included; crates takes `newest_version`, a pre-release included.
- Every registry runs at 3 requests a second; legacy runs crates and rubygems one at a time.

Legacy reads:
- **Phase K's REST path** (`_phase_k_fetch_one`, `_fetch_release_or_tag`, CFA:4922-5036): the latest release, else the
  tags; GitLab with a `PRIVATE-TOKEN` when one is set, Codeberg anonymously; tags normalized (CFA:4608).
- **Phase L's resolvers:** `_resolve_maven` (`g:"<group>" AND a:"<artifact>"`), `_resolve_nuget` (the last version
  with no `-`), `_resolve_crates` (`max_stable_version`, else `max_version`), npm's `latest` dist-tag, rubygems'
  `version`.

**Approach** (each behind `pyforge.atlas.live_vcs_universe`; off, nothing changes):
1. **Hosts.** `VcsHostSeedDataset` asks for the latest release, then the tags (`_live_host_paths`): GitLab
   `releases?per_page=1` then `repository/tags?per_page=1` (the project path whole), Codeberg `releases/latest` then
   `tags?limit=10`. The tag is normalized (Story 35.3's `normalize_release_tag`). A release that fails (often a 404)
   falls to the tags; a project with neither reads "no tags".
2. **GitLab's token.** `PRIVATE-TOKEN` from `gitlab_token`, only under `PYFORGE_ATLAS_CREDENTIALED=1`, only over https
   to `gitlab.com` (`credentials.HeaderAuth`, `gitlab_auth`). Unset, GitLab is asked unauthenticated, as it answers.
   Codeberg never sends a credential. A no-op auth keeps `~/.netrc` out. A request that carries the token never
   follows a redirect: requests strips only `Authorization` on a host change, so a custom header would follow it.
   **Operator note:** `gitlab_token` in `conf/local/credentials.yml` is the token as a bare string (`gitlab_token:
   glpat-...`) or `{token: glpat-...}`. A `[PRIVATE-TOKEN, glpat-...]` pair, the shape of the catalog test stub, is no
   token: nothing is sent and GitLab is asked unauthenticated.
   - The token is `{token: ...}` or a bare string; a `[user, password]` pair is no token and sends nothing.
3a. **Retries and errors as legacy.** A 429 or 5xx is retried (its `Retry-After` waited); a 404 release goes to the
   tags at once. A row's error is the status (`HTTP 404`), never the exception's text. A GitLab release without a
   `tag_name` reads its `name`, and a Maven hit without `latestVersion` its `v`, as legacy does. Host requests name
   atlas in their `User-Agent` too.
3. **Registries.** Maven asks for the group and the artifact; NuGet takes the last stable version; crates the newest
   stable version.
4. **Rate.** crates and rubygems run at one request a second (catalog `rps: 1.0`).
5. **Agent.** Every registry request names atlas in its `User-Agent`, as legacy Phase L does (`cf-atlas/phase-l`):
   crates.io answers requests' default agent with a 403.

Ledger key: `35-4-gitlab-codeberg-and-the-eight-registries-fill`.
Type / Effort / Deps: feature / M / Story 35.2 (the batches), Story 35.3 (`normalize_release_tag`).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-65** (FR-73): VCS and registry fetches cover the full universe; public registries send no
  credential.
- **AD-2** (a credential to its own host), **AD-13** (last-good under a marker).

## Acceptance Criteria

- **AC1 — Hosts.** The latest release, else the first tag, normalized; "no tags" when neither; a failed release falls
  to the tags; GitLab subgroups kept whole; a malformed Codeberg identifier is its row's error.
- **AC2 — GitLab's token.** Sent only with the switch, a usable token and an https `gitlab.com` URL; never to Codeberg;
  never in `repr`.
- **AC3 — Registries.** Maven `g:"…" AND a:"…"`; NuGet's last stable; crates' newest stable; flag off unchanged.
- **AC4 — Rate and agent.** crates and rubygems at 1.0 request a second; every registry request carries atlas's
  `User-Agent`.
- **AC5 — Live.** See Verification. Tolerance against legacy's stored versions: every legacy GitLab, Codeberg and
  registry package asked; the same version for at least 80% of the packages both hold (legacy's values are from its
  last run, not today's).
- **AC6 — Gates.** `pyforge-atlas-test`, `kedro-catalog-check`, the coverage gate, `lint-types` (and mypy in
  `pyforge-foundry-full`), `flag-gate-check`; governing Specs reconciled and stamped scoped.

## Verification

- Unit, from the repo root: `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_hosts_and_registries.py`.
- **Live, recorded 2026-10-18,** on a scratch data root (dev, flag on, no switch, no credential):
  - `--pipelines vcs_health --nodes refresh_vcs_host_stores,refresh_vcs_registry_stores,track_upstream_versions,track_registry_versions`
    exit 0 in 22 min. crates.io answered every request 403; the registry node was re-run with the `User-Agent`
    fix (39 s, exit 0).
  - Against legacy `cf_atlas.db` (`upstream_versions`, fetched the same day): every one of legacy's 725 packages with
    a version was asked.

    | Source | Atlas asked / with a version | Legacy with a version | Same version where both hold |
    |---|---|---|---|
    | GitLab | 411 / 372 | 331 | 330 of 330 |
    | Codeberg | 31 / 23 | 19 | 19 of 19 |
    | npm | 211 / 211 | 198 | 195 of 198 |
    | rubygems | 165 / 165 | 165 | 164 of 165 |
    | crates | 10 / 10 | 10 | 10 of 10 |
    | maven | 3 / 3 | 2 | 2 of 2 |
    | nuget | 0 | 0 | — |

    720 of 724 (99.45%), above the 80% tolerance. The four that differ are newer in atlas (ava 8.1.0, commitlint
    21.2.4, knip 6.42.0, rb-pkg-config 1.6.6): releases after legacy's fetch.
  - GitLab rows without a version: 25 "no tags", 14 a fetch error.

## Boundaries & Constraints

**Never:** a credential to a public registry or to Codeberg; GitLab's token without the switch.

**Deviation:** crates and rubygems run at one request a second with the flag off too (the catalog's `rps`); a stricter
rate never sends more, and it is those registries' documented limit.

**Retries.** A 429, a 5xx or a network failure with no HTTP status (a dropped connection, a timeout: an `OSError`
underneath) is retried, a `Retry-After` waited (capped at 60 s); a programming error is not. Each GitLab and Codeberg
request waits 20 s at most, legacy's timeout. Legacy (CFA:5009-5014) differs in three ways: it retries a 403, returns a
5xx at once without the tags, and never retries the tags request; atlas never resends a 403 and asks the tags after
either failure. A row's error is `HTTP <status>`, else the type of the failure underneath (`ConnectionError`), never
its text.

**Residual risk:**
- **GitLab unauthenticated** is rate-limited per IP; a large batch may meet 429s until the operator adds a token.
- **cran, cpan and luarocks** stay empty: legacy never writes their names (Story 35.2).

## I/O & Edge-Case Matrix

| Situation | Before | After (flag on) |
|---|---|---|
| A GitLab project with a release `v2.1` | its latest tag, as written | `2.1` |
| A Codeberg repo with tags only | its latest tag | the first tag, normalized |
| A Maven coordinate `org.acme:thing` | `a:org.acme%3Athing` (no match) | `g:"org.acme" AND a:"thing"` |
| NuGet `1.0, 2.0, 3.0-beta` | `3.0-beta` | `2.0` |
| GitLab with a token and the switch | the catalog pair as Basic auth | `PRIVATE-TOKEN` to gitlab.com |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-65 (FR-73), a feature.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-18 (atlas fills its own data).
- Epic 35 / Story 35.4 in `planning-artifacts/epics.md`.

## Spec Change Log

- 2026-10-18: written with the implementation (branch `atlas-35-4-hosts-and-registries`, stacked on Story 35.3).
- 2026-10-21, review round 3 (PASS), nits applied: a cause chain that loops stops where it repeats; only a network
  failure with no status is retried (a `TypeError` is not); the host stores ask with legacy's 20 s timeout (the 900 s
  default times four attempts held a node for an hour); a test pins one rate token per attempt; the Retries paragraph
  says how legacy differs.
- 2026-10-21, review round 2 (PASS), should-fix applied:
  - Maven's `v` fallback read with the flag off too, which AC3 ("flag off unchanged") does not allow; it is now read
    with the flag on only, and a test pins the flag-off result.
  - Tests for the retry loop: a 429 waits its `Retry-After`, a 5xx is retried after a backoff, a 404 is never retried.
  - A failure with no status is retried, as legacy and the flag-off path do, and its row error names the cause's type
    (`_why` walks `__cause__`).
  - Nits: redirect tests for 301, 307 and 308 and for a redirect on the tags alone; a tag's `tag_name` read when it
    has no `name`; the operator note on `gitlab_token`'s shape.
- 2026-10-19, review round 1 (FAIL), fixed:
  - B1: GitLab's `PRIVATE-TOKEN` followed a redirect to another host or to http; a request carrying it never follows
    one now (Approach 2), tested with a redirecting transport.
  - Should-fix: the flag-off rate recorded as a deviation; tests for a malformed Codeberg identifier through
    `load_many`, `~/.netrc` kept out of a host request, the first tag taken; a row's error is its HTTP status.
  - Nits: a 404 release no longer retried before the tags; a 429 or 5xx waits its `Retry-After`; legacy's `name` and
    `v` fallbacks; host requests' `User-Agent`; the token shapes the store accepts. Not changed: Codeberg's tags use
    `limit=10` (Gitea's parameter; legacy's `per_page` is ignored by Gitea, so the first tag is the same).
- 2026-10-18: the live run found crates.io refusing requests' default `User-Agent` (403); registry requests now send
  `vcs_sources.USER_AGENT`.
