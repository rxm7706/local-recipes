---
title: 'Air-gap parity is a failing check'
type: 'test'
created: '2026-08-22'
status: 'done'
baseline_revision: '585d1799199bb7e29c9a3134bc373f13ce5632db'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/ARCHITECTURE-SPINE.md']
warnings: ['oversized']
deferred:
  - summary: >-
      build-pixi-mirror.py has no retry/backoff for a transient network
      failure during the mirror build; one flaky response anywhere in the
      ~428-package fan-out fails the whole job (a rerun is the workaround).
    evidence: |-
      Raised by Blind Hunter in this story's first review pass. Not fixed in
      this pass: standard `requests` retry via a Session+HTTPAdapter is
      straightforward but adds real complexity for a purely operational
      (not correctness) concern -- reruns are cheap and the mirror-build
      phase runs with normal network access, no adversarial condition.
    severity: low
  - summary: >-
      build-pixi-mirror.py's channel/subdir/filename derivation assumes a
      plain 3-segment conda URL and would silently mis-derive the mirror
      path for a labeled-channel package (e.g. .../conda-forge/label/
      broken/linux-64/pkg.conda).
    evidence: |-
      Raised by Blind Hunter and Edge Case Hunter (corroborated). Verified
      live against the real pixi.lock: all 428 platform-dev/linux-64
      packages conform to the plain 3-segment shape today, so this is a
      latent risk, not a live bug -- would surface as a loud mirror-fetch
      failure if it ever occurred, not a silent one.
    severity: low
  - summary: >-
      The .pixi/config.toml `[mirrors]` append in the CI job is a raw
      heredoc string append, not a TOML-aware merge -- would produce a
      duplicate `[mirrors]` table (invalid TOML) if one is ever added to
      the committed file later.
    evidence: |-
      Raised by Blind Hunter. Verified live: the committed .pixi/config.toml
      currently carries only `run-post-link-scripts = "insecure"`, no
      `[mirrors]` table, so the append is safe today. A proper fix needs a
      TOML-aware merge (tomllib/tomli_w), real complexity for a scenario
      that does not exist yet.
    severity: low
  - summary: >-
      The CDN-reference-scan step's allow-pattern only recognizes
      `127.0.0.1`, not `localhost`/`::1` -- a future rendering path that
      happened to emit a localhost-based absolute URL would be flagged as
      external and fail the job even though it is still local.
    evidence: |-
      Raised by Blind Hunter. Fails in the safe direction (false failure,
      not a missed real external reference) and nothing in the current
      codebase emits a `localhost`-based absolute URL, so this is a
      future-proofing note, not a live gap.
    severity: low
---

<intent-contract>

## Intent

**Problem:** Nothing in platform CI proves the python-agent-platform stack can build and deploy
without internet access, even though AD-13/CAP-6 require it as a shipped constraint, not an
aspiration.

**Approach:** Add a new paths-filtered CI job, `air-gap-parity`, that (a) builds a local
file-based mirror of the `platform-dev` env's conda-forge + SelfExplainML packages, (b) blocks
all non-private-network egress on the runner, (c) proves `pixi install --frozen -e platform-dev`
resolves from a FRESH cache using only that mirror, (d) kind-loads the already-built image (no
registry push) and helm-installs the unmodified 12.1 chart, and (e) scans the served home page
for any absolute external URL. Every check is a hard failure (`exit 1`/`::error::`), never a
warning.

## Boundaries & Constraints

**Always:** Reuse `gke-portability-smoke`'s established patterns verbatim where they apply:
disk-reclaim step, `prefix-dev/setup-pixi@v0.10.0` with `environments: platform-dev`, pinned
`kind` install, `docker build -f src/platform/Containerfile -t platform:air-gap-smoke .` (repo
root context, unchanged Containerfile), `kind load docker-image` (no push), the
`platform-secrets` K8s Secret pattern (AD-12: chart never renders a Secret), `--set
image.tag=air-gap-smoke --set django.secureSslRedirect=False` with NO `--wait` (the documented
migrate-Job deadlock fix -- see that job's own comment), and `if: always()` teardown. New job is
`paths: [src/platform/**]`-filtered with `working-directory: src/platform` where applicable
(AD-15); this PR takes the `maintenance` label. Build the local mirror
(`scripts/build-pixi-mirror.py`, new) by reading `pixi.lock` directly (package name/url/sha256
per platform) for the `platform-dev` environment's `linux-64` subset, downloading each artifact
into `<dest>/<channel-name>/<subdir>/<filename>` (channel-name = last path segment of the
package's host channel, i.e. `conda-forge` or `SelfExplainML`) and verifying sha256. Append a
`[mirrors]` table to the (already git-tracked, but here only ephemerally CI-modified --
never commit the change) `.pixi/config.toml` mapping both
`https://conda.anaconda.org/conda-forge` and `https://conda.anaconda.org/SelfExplainML` to the
matching `file://<dest>/<channel-name>` path -- this is picked up automatically for BOTH the
bare-runner pixi step and, via the existing `.dockerignore` `!.pixi/config.toml` exemption, would
also flow into any future docker rebuild step (not exercised by this job -- the image is built
BEFORE egress is blocked, see Never). Block egress with `sudo iptables -A OUTPUT -j DROP` scoped
by first inserting ACCEPT rules for `lo`, `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, and
`192.168.0.0/16` (covers loopback + the Docker/kind bridge networks so kubectl/helm/kind-internal
traffic keeps working) -- insert ACCEPT rules before the DROP so ordering is correct. Immediately
before the mirror-only proof, evict the pixi package cache (fresh `PIXI_CACHE_DIR` env var
pointed at an empty dir, or `rm -rf ~/.cache/rattler`) so `pixi install --frozen -e platform-dev`
cannot silently succeed from a warm cache -- it must genuinely re-fetch through the mirror. The
CDN-reference check extends the `container` job's existing `/static/` asset-fetch pattern: after
a 200 from the deployed app's `/` (via `kubectl port-forward`, not Ingress -- this job does not
re-prove the Ingress path, already covered by 12.2), grep the response body for any
`https?://[^"'\''<> ]+` reference whose host is not the port-forwarded localhost address; any
match fails the job.

**Block If:** iptables is unavailable or `sudo` is refused on the runner (would make the whole
egress-block premise impossible) -- HALT `blocked`. `pixi.lock` has no resolvable entries for the
`platform-dev` environment's `linux-64` platform (schema drift) -- HALT `blocked`.

**Never:** Do not touch `src/platform/Containerfile`, the chart, or any app code -- this story is
CI + a new standalone mirror-builder script only. Do not attempt to air-gap the Containerfile's
own pip-install layer or its build-time `pyforge-steward` env (both fetch live from PyPI during
`docker build`, which stays network-ON in this job, run BEFORE the egress block) -- AD-8 names
"the lockfile" (the `python-agent-platform`/`platform-dev` conda solve specifically), and this
story proves exactly that, decisively, with a real network block and a cache-eviction guard
against a false-green warm-cache pass; the pip layer is a stated, deliberate non-goal here, not a
silent gap. Do not stand up a real JFrog/Artifactory instance -- the mirror is a plain local
directory. Do not re-prove the Ingress path (12.2 already does) or add OCP-specific checks
(12.7's job, needs a live cluster, not available here). Do not touch `sprint-status-ledger.yaml`
or promote this spec -- that is the coordinating session's job after PR review.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | Mirror built, egress blocked, fresh cache | `pixi install --frozen -e platform-dev` exits 0; deploy succeeds; `/` has no external URL | No error |
| Warm-cache false green | Cache NOT evicted before the blocked-egress install | Would pass even with a broken mirror | Cache eviction step is mandatory, not optional |
| CDN reference present | `/` response contains `https://some-cdn.example/x.js` | Job fails | `::error::` naming the offending URL(s), `exit 1` |
| Mirror missing a package | `pixi.lock` references a package the mirror builder failed to download | `pixi install --frozen` fails to resolve it | Job fails loudly (this IS the check working correctly, not a bug to suppress) |
| Egress genuinely blocked but kubectl/helm can't reach kind | iptables rule ordering wrong (DROP before ACCEPT) | kind cluster unreachable, job hangs/fails | Verify ACCEPT rules are inserted, not appended, before the DROP rule |

</intent-contract>

## Code Map

- `.github/workflows/platform-ci.yml` -- add new `air-gap-parity` job after `gke-portability-smoke` (~line 930); model directly on that job's structure (lines 692-930): checkout, "Verify src/platform exists", disk-reclaim, `setup-pixi` (`environments: platform-dev`), pinned `kind` v0.32.0 install, kind cluster create (no ingress-nginx needed -- this job uses `kubectl port-forward`, not the Ingress path), docker build (network ON, unchanged), `docker builder prune`, `kind load docker-image`, namespace+secret creation (AD-12 pattern), helm install (`--set image.tag=... --set django.secureSslRedirect=False`, no `--wait`), migrate-Job wait, teardown `if: always()`.
- `.github/workflows/platform-ci.yml` lines 330-390 (`container` job) -- the `/static/` asset-fetch pattern the new CDN-reference-scan step extends (same "derive URLs from the rendered body, never hardcode" discipline).
- NEW `scripts/build-pixi-mirror.py` -- reads `pixi.lock` (YAML), extracts `platform-dev`/`linux-64` package records (name, url, sha256), downloads each into `<dest>/<channel>/<subdir>/<filename>`, verifies sha256, skips already-valid files (idempotent).
- `pixi.lock` -- source of package URLs/hashes for the mirror builder; confirmed live that `SelfExplainML`-hosted packages (e.g. `slowapi`) appear alongside `conda-forge` ones for this environment (`pixi.toml` lines 150-156 comment).
- `.pixi/config.toml` (repo root, git-tracked, currently just `run-post-link-scripts = "insecure"`) -- the new job APPENDS a `[mirrors]` table to its own checkout's copy only; never commit this change.
- `docs/reference/pixi-config-jfrog.example.toml` -- the authoritative `[mirrors]` table schema/format reference (`{"<original-channel-url>" = ["<mirror-url>", ...]}`).
- `.dockerignore` -- confirmed no catch-all pattern would exclude a new top-level mirror directory (only named entries like `.env`/`.secrets`/`.pixi/*` are excluded); no change needed if the mirror dir is created at CI-runtime only (not committed) with a non-colliding name, e.g. `ci-airgap-mirror/`.
- `src/platform/platformapp/static/{css,js}/vendor/` -- already-vendored assets (Story 10.1 established zero-CDN-by-construction; the Containerfile's own comment documents stripping CDN `sourceMappingURL` references). This story adds the CI proof; it does not change these assets.
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-12-1-the-vanilla-chart-with-an-ocp-overlay.md` and `spec-12-2-gke-as-a-portability-profile.md` -- prior-story Dev Notes; both explicitly flagged air-gap as out of scope for themselves ("no air-gap check (12.3)").

## Tasks & Acceptance

**Execution:**
- `scripts/build-pixi-mirror.py` -- new script -- parses `pixi.lock`, downloads + hash-verifies the `platform-dev`/`linux-64` package set into a local channel-shaped mirror directory; CLI args for lockfile path, environment, platform, dest.
- `.github/workflows/platform-ci.yml` -- add `air-gap-parity` job -- proves AD-13/CAP-6 end-to-end per the Boundaries above.
- Unit-test coverage for `build-pixi-mirror.py`'s URL-to-mirror-path derivation and sha256 verification logic (a small fixture lockfile, no real network needed for the test itself).

**Acceptance Criteria:**
- Given a `platform-dev` pixi cache evicted to empty and all non-private-network egress blocked, when `pixi install --frozen -e platform-dev` runs against the mirror-populated `.pixi/config.toml`, then it exits 0 with zero requests to any public host.
- Given the deployed chart's home page (`/`, via port-forward), when its response body is scanned for absolute external URLs, then none are found; a planted CDN reference in a test fixture fails the same scan.
- Given the image was `kind load`-ed with no registry push, when the pod starts, then it pulls nothing over the network (`imagePullPolicy` resolves against the kind-node-local image).
- Given any of the above checks fails, then the job exits non-zero with an `::error::` annotation naming the specific failure -- never a soft warning.

## Spec Change Log

## Review Triage Log

### 2026-08-22 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 12 (high 2, medium 4, low 6)
- defer: 4 (low 4)
- reject: 6
- addressed_findings:
  - `[high]` `[patch]` postgres:17/redis:7 (chart defaults) were never kind-loaded before the egress block goes up -- only the platform image was. Since the block only touches the `OUTPUT` chain (host-originated traffic), not `FORWARD` (container-routed traffic), pods retain their own outbound internet access, so these two images would silently pull from the real Docker Hub during deploy, leaving the "image from an internal/local registry" claim unproven for 2 of 3 chart images. Fixed by docker-pulling and kind-loading both alongside the platform image, before the block.
  - `[high]` `[patch]` The egress block added only `iptables` (IPv4) rules; a runner with IPv6 connectivity could let `pixi install`/`requests` resolve `conda.anaconda.org` over AAAA and bypass the block entirely, producing a false-green "mirror-only" proof for this story's core Acceptance Criterion. Fixed by mirroring the same ACCEPT-then-DROP ordering with `ip6tables`.
  - `[medium]` `[patch]` PyPI-kind `pixi.lock` entries were silently dropped by `parse_mirror_targets` with no warning (zero exist for `platform-dev`/`linux-64` today, verified live against the real lockfile, so no live impact, but a future addition would silently produce an incomplete mirror). Fixed by raising `MirrorBuildError` naming any non-conda entries found.
  - `[medium]` `[patch]` The mirror-download step produces no output between "Mirroring N packages..." and the final summary; on a slow connection this risks tripping a CI no-output step timeout mid-build. Fixed by printing progress as each download completes.
  - `[medium]` `[patch]` `sudo iptables -A OUTPUT -j DROP` silently drops rather than rejects, so a genuine blocked-network attempt hangs for the full TCP retry window instead of failing fast, risking the job's 40-minute budget. Fixed by wrapping the mirror-only install step with a bounded `timeout`.
  - `[medium]` `[patch]` The CDN-reference-scan regex requires an explicit `https?://` scheme and is case-sensitive, so a protocol-relative (`//cdn.example.com/...`) or uppercase-scheme reference would silently pass undetected -- directly undermining this story's own "any external reference is a FAILING check" AC. Fixed with case-insensitivity and an optional-scheme alternative.
  - `[low]` `[patch]` `main()`'s `yaml.safe_load(pixi.lock)` was unguarded, raising a raw traceback instead of the script's own `::error::` convention on malformed YAML. Wrapped in try/except.
  - `[low]` `[patch]` `parse_mirror_targets` had no guard against `lockfile["packages"]` being YAML-null. Changed to `lockfile.get("packages") or []`.
  - `[low]` `[patch]` `_download_one`'s already-valid check could raise an uncaught `OSError` (e.g. a stale directory at the destination) instead of treating it as needing a fresh download. Wrapped in try/except, falls through to redownload.
  - `[low]` `[patch]` No dedup of `MirrorTarget`s before submission to the thread pool -- a duplicate URL would race two threads on the same destination file. Deduplicated by `dest_relpath` before building the executor's futures.
  - `[low]` `[patch]` `--workers` accepted 0 or negative values, raising an unguarded `ValueError` from `ThreadPoolExecutor`. Added argparse-level validation.
  - `[low]` `[patch]` The script's own docstring documents a local `--dest ci-airgap-mirror` usage example with no corresponding `.gitignore` entry, risking an accidental `git add` of a multi-hundred-MB directory. Added `ci-airgap-mirror/` to `.gitignore`.

## Design Notes

**Scope boundary, stated explicitly (not a silent gap):** AD-8 says "the lockfile must solve
reproducibly from a mirror-only channel config," naming the `python-agent-platform` env's own
lockfile. This story proves exactly that -- the dominant, 395-package conda/pixi layer -- with a
real, decisive egress block and a cache-eviction guard against a false green. The Containerfile's
separate PyPI pip-install layer (9 exact-pinned packages) and its build-time-only
`pyforge-steward` secrets-scan env are NOT re-solved under blocked egress in this job; the image
is built while egress is still on, before the block. Mirroring those two layers too is real,
addressable follow-up work (would need Containerfile ARG/ENV hooks for `PIP_INDEX_URL`, which
this story deliberately does not add), not silently pretended to be covered here.

**iptables ordering example:**
```
sudo iptables -I OUTPUT -o lo -j ACCEPT
sudo iptables -I OUTPUT -d 10.0.0.0/8 -j ACCEPT
sudo iptables -I OUTPUT -d 172.16.0.0/12 -j ACCEPT
sudo iptables -I OUTPUT -d 192.168.0.0/16 -j ACCEPT
sudo iptables -A OUTPUT -j DROP
```
`-I` (insert at head) for the ACCEPTs, `-A` (append) for the final DROP, so ACCEPTs are always
evaluated first regardless of the order these lines run in.

## Verification

**Commands:**
- `python -m pytest -v src/platform/tests/... ` (or wherever the mirror-builder's unit test
  lands) -- expected: passes against a fixture lockfile, no network.
- This job cannot be fully exercised locally (no GH Actions runner, no guaranteed `sudo`
  iptables access in this sandboxed environment) -- state that honestly in the PR rather than
  claiming a local green run, matching Story 12.1/12.2's own "no live-cluster deploy claim"
  precedent. Verify the new job's YAML is syntactically valid and the mirror-builder script runs
  correctly against the real `pixi.lock` in a network-available (non-egress-blocked) dry run.

**Manual checks (if no CLI):**
- Read the rendered `air-gap-parity` job YAML and confirm every check step ends in `exit 1` on
  failure, never a bare warning/continue.

## Auto Run Result

**Summary:** Added a new `air-gap-parity` CI job (`.github/workflows/platform-ci.yml`) proving
AD-13/CAP-6: a `platform-dev`/`linux-64` pixi mirror is built from `pixi.lock` while egress is
still on, then a fresh pixi cache + env prefix is proven to resolve the entire environment from
that mirror alone with all non-private-network egress blocked (IPv4 AND IPv6), the platform
image plus the chart's own postgres/redis default images are all kind-loaded with no registry
push, and the deployed home page is scanned for any absolute or protocol-relative external URL
reference. Every check is a hard failure, never a soft warning.

**Files changed:**
- `.github/workflows/platform-ci.yml` -- new `air-gap-parity` job (~25 steps); two path-filter
  lists updated to include `scripts/build-pixi-mirror.py`.
- `scripts/build-pixi-mirror.py` (new) -- builds a local file-based conda mirror straight from
  `pixi.lock`, with hash verification, idempotent skip, progress reporting, and hard failure on
  any non-conda lock entry, malformed YAML, or download/verification error.
- `tests/scripts/test_build_pixi_mirror.py` (new) -- 22 unit tests covering URL-to-mirror-path
  derivation, sha256 verification, dedup, progress, and CLI-level error handling.
- `.gitignore` -- `/ci-airgap-mirror/` entry for the script's own documented local-usage path.

**Review findings breakdown:** 22 distinct findings after dedup across Blind Hunter (15 raw) and
Edge Case Hunter (10 raw, 3 overlapping with Blind Hunter's). 12 patched (2 high, 4 medium, 6
low; see Review Triage Log above for the full per-finding list). 4 deferred (all low severity;
recorded in frontmatter `deferred`). 6 rejected (channel-drift detection already fails loud by
design; iptables cleanup is inconsequential on an ephemeral GitHub-hosted runner; the double-I/O
sha256-verification pattern is a measured non-issue at this job's real package count/time
budget; `build_mirror`/`main()` orchestration coverage matches this story's own stated test
scope; stale-figure comments match this file's own pre-existing convention; the `maintenance`
label is a PR-metadata step, not a code finding). Verification Gap Reviewer found zero gaps
(ran the mirror builder live against the real `pixi.lock`, confirmed the `.pixi/config.toml`
schema, confirmed no CI ruff gate reaches these files). Intent Alignment Auditor confirmed the
diff implements the natural "new, teeth-having CI gate" reading of the story title, correctly
scoped narrower than a maximalist "air-gap literally everything" reading, with that scope
decision stated explicitly in Design Notes rather than silently assumed.

**Follow-up review recommendation:** `true` -- 2 of the 12 patched findings were `high`
severity (postgres/redis images not kind-loaded before the block; IPv6 egress unblocked), both
now fixed and independently re-verified, but the scoring rule (`true` if any patched finding was
high) triggers regardless of the medium/low tally (4×medium + 6×low would itself also clear the
"5 or more" threshold at 3×4+1×6=18).

**Verification performed (all independently re-run by the orchestrating session, not merely
trusted from the implementation subagent's self-report):**
- `pytest tests/scripts/test_build_pixi_mirror.py -v` -- 22/22 passed.
- `pytest tests/scripts/ -q` (full suite) -- 172 passed, 8 skipped, 2 failed; the 2 failures
  confirmed via `git stash` to be pre-existing and unrelated (an unrelated CFE-retro-mirroring
  fidelity check, `test_cfe_rebuild_guard_check.py`), present identically on the unmodified
  baseline.
- `yaml.safe_load` on the full workflow file -- valid; all 5 jobs present including
  `air-gap-parity`.
- `bash -n` on all 21 `run:` blocks in the new job (YAML-block-scalar-stripped) -- 0 failures.
- `ruff check scripts/build-pixi-mirror.py tests/scripts/test_build_pixi_mirror.py` -- 4
  findings (1 `EXE001`, 3 `PLW1510`), both rule classes confirmed pre-existing/ungated elsewhere
  in this repo (26 `EXE001` across `scripts/`, 28 `PLW1510` across `tests/scripts/`) and outside
  the `test` job's actual `ruff check .` scope (that job's default `working-directory:
  src/platform` never reaches these repo-root-level paths) -- not a regression.
- Live functional test of the CDN-scan regex against 4 fixture pages (clean, standard CDN
  reference, protocol-relative reference, uppercase-scheme reference) -- correctly passes the
  clean page and correctly flags all 3 external-reference shapes.
- Verified the postgres/redis image refs added to the new kind-load step
  (`postgres:17`/`redis:7`) against the chart's actual `values.yaml` -- exact match.
- Live run of `scripts/build-pixi-mirror.py` against the real `pixi.lock` -- 428/428 packages
  downloaded and hash-verified, progress lines printed as designed, in well under a minute.
- Confirmed the `implementation-artifacts` Tier-3 backlink symlink was never disturbed by any
  subagent during this pass (an earlier, separate compile-epic-context subagent run in this same
  session had broken it; recovered before any spec work began -- unrelated to this
  implementation/review pass, noted here only for completeness).

**Residual risks:**
- The `air-gap-parity` job itself has never run in real GitHub Actions (no sandboxed
  `sudo`/iptables/kind access in this environment) -- stated honestly per Story 12.1/12.2's own
  "no live-cluster deploy claim" precedent, not glossed over. The first live PR run is the real
  test of the iptables ordering, the kind-cluster networking assumptions, and the 40-minute
  timeout budget.
- Scope is deliberately narrower than a maximalist reading of AD-13: the Containerfile's own
  PyPI pip-install layer and its build-time-only `pyforge-steward` secrets-scan env are not
  air-gapped by this job (stated explicitly in Design Notes, not silently omitted).
- `ip6tables`/`unique-local-address` blocking assumes the standard GitHub-hosted `ubuntu-latest`
  runner network stack; a runner image change could in principle alter this, though the job's
  own precondition step would fail loudly (not silently) if `ip6tables` were ever unavailable.
