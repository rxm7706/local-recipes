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
review_loop_iteration: 0
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
   Codeberg never sends a credential. A no-op auth keeps `~/.netrc` out.
3. **Registries.** Maven asks for the group and the artifact; NuGet takes the last stable version; crates the newest
   stable version.
4. **Rate.** crates and rubygems run at one request a second (catalog `rps: 1.0`).

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
- **AC4 — Rate.** crates and rubygems at 1.0 request a second.
- **AC5 — Live.** See Verification. Tolerance against legacy's stored versions: every legacy GitLab, Codeberg and
  registry package asked; the same version for at least 80% of the packages both hold (legacy's values are from its
  last run, not today's).
- **AC6 — Gates.** `pyforge-atlas-test`, `kedro-catalog-check`, the coverage gate, `lint-types` (and mypy in
  `pyforge-foundry-full`), `flag-gate-check`; governing Specs reconciled and stamped scoped.

## Verification

- Unit, from the repo root: `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_hosts_and_registries.py`.
- **Live, recorded 2026-10-18** — PENDING (a public run, no credential).

## Boundaries & Constraints

**Never:** a credential to a public registry or to Codeberg; GitLab's token without the switch.

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
