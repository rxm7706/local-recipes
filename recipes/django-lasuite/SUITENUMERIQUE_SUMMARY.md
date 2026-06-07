# suitenumerique — Local Recipes Build Report

**Original build date**: 2026-05-31 (initial build + Phase 6c remediation + Phase 6d canonical-test/dep/license fixes)
**Last reviewed**: 2026-06-07 (conda-forge availability re-check with the four-form PyPI→conda name-divergence rule from skill v8.11.4 G10)
**Scope**: every public repo under [github.com/orgs/suitenumerique](https://github.com/orgs/suitenumerique/repositories) (43 repos)
**Mode**: local-only; **no PRs opened** against `conda-forge/staged-recipes`
**Artifacts directory**: `build_artifacts/linux64/{noarch,linux-64}/`

> **2026-06-07 re-audit finding** (full details in § "2026-06-07 Re-audit" below): three of the original 15 "submission-ready" recipes are **already on conda-forge** and should be DROPPED from the submission plan — `django-lasuite` (bare-name feedstock at v0.0.26, created 2026-04-13), `dockerflow` (bare-name at v2026.3.4, created 2026-06-01 — just 7 days before this audit), and `langfuse` (`langfuse-python` feedstock at v4.7.1, illustrates the `-python` suffix divergence pattern). Revised genuine submission-ready set: **15 → 12**. The 31 local-only recipes are unchanged. Per-recipe tables below annotate the three already-on-CF entries inline.

---

## Result at a glance

| Tier | What | Recipes | Built | Flagged local-only | Already on conda-forge (re-audited 2026-06-07) |
|------|------|---------|-------|--------------------|-------------------------------------------------|
| A | Clean conda-forge candidates | 1 | 1 | 0 | 1 (`django-lasuite`) |
| B | npm libraries | 5 | 5 | 5 | 0 |
| C | Python libs not on PyPI | 3 | 3 | 3 | 0 |
| D | Django web-app backends | 15 | 15 | 15 | 0 |
| E | Frontend apps (Next.js / source-tree) | 4 | 4 | 4 | 0 |
| F | Forks of upstream projects | 4 | 4 | 4 | 0 |
| 6b | Missing Django deps (now available) | 14 | 14 | 0 | 2 (`dockerflow`, `langfuse` → `langfuse-python`) |
| G | Skipped (docs / infra / placeholder) | 12 | 0 | — | — |
| **Total** | | **46** | **46** | **31** | **3** |

**Genuinely submission-ready (post-2026-06-07): 12 recipes** (was 15 on 2026-05-31; dropped `django-lasuite`, `dockerflow`, `langfuse` — all already on conda-forge).

Every recipe under tiers B–F carries a banner at the top of `recipe.yaml`:
```yaml
# ⚠️ LOCAL-ONLY RECIPE — NOT FOR conda-forge/staged-recipes SUBMISSION
# Reason: ...
```
The Tier-A recipe (`django-lasuite`) and the 14 Phase-6b dep recipes carry no warning — they are clean candidates if you later choose to submit them. (Three of those 15 no-warning recipes turned out to already be on conda-forge per the 2026-06-07 re-audit; the warning's absence still reflects "would be a clean submission candidate", just one that's already been submitted by someone else.)

## Conda-forge submission plan (dependency-ordered)

**Revised 2026-06-07**: of the 46 recipes, **12 are genuinely conda-forge-submission-ready** (down from 15 on 2026-05-31 after the four-form name-divergence re-audit; see § "2026-06-07 Re-audit" for the three recipes that turned out to already be on conda-forge). The 31 local-only recipes (Tiers B/C/D/E/F) are out of scope — they carry the `⚠️ LOCAL-ONLY` banner because conda-forge declines web apps, npm component libraries, forks, and frontend source trees.

Each candidate's run requirements were checked against `conda-forge` (channel-only, with the local channel excluded) using `dependency-checker.py`. Result: **only one inter-recipe edge** in the candidate set (django-zxcvbn-password-validator → zxcvbn).

### Submission graph (revised 2026-06-07)

```
Wave 1 (independent — submit in any order, parallel PRs OK):
  brevo-python           (deps: httpx, pydantic, pydantic-core, typing_extensions)
  nested-multipart-parser (deps: python only)
  django-pydantic-field  (deps: django, pydantic, typing_extensions)
  django-fernet-encrypted-fields (deps: django, cryptography)
  djangorestframework-api-key    (deps: packaging)
  zxcvbn                 (deps: python only)          ← Wave-2 prerequisite
  odfdo                  (deps: lxml)
  flanker                (deps: attrs, chardet, cryptography, idna, ply,
                          regex, six, tld, webob)
  ironcalc               (deps: python — Rust + maturin build)
  libpff-python          (deps: python only — C extension)
  py3langid              (deps: numpy)

Wave 2 (after zxcvbn merges):
  django-zxcvbn-password-validator  (deps: django, zxcvbn)

Already on conda-forge — DO NOT submit (verified 2026-06-07):
  django-lasuite   →  conda-forge/django-lasuite-feedstock (bare-name, v0.0.26)
  dockerflow       →  conda-forge/dockerflow-feedstock (bare-name, v2026.3.4)
  langfuse         →  conda-forge/langfuse-python-feedstock (-python suffix, v4.7.1)
```

### Recommended submission order (revised 2026-06-07)

| Wave | Count | Recipes | Rationale |
|---|---|---|---|
| ~~**1a — high-priority**~~ | ~~1~~ → **0** | ~~`django-lasuite`~~ | **Removed** — `conda-forge/django-lasuite-feedstock` v0.0.26 already exists (created 2026-04-13). Verified by feedstock recipe `source.url: pypi.org/packages/source/d/django-lasuite/django-lasuite-${{ version }}.tar.gz`. |
| **1b — independent** | ~~13~~ → **11** | `brevo-python`, `nested-multipart-parser`, `django-pydantic-field`, `django-fernet-encrypted-fields`, `djangorestframework-api-key`, `zxcvbn`, `odfdo`, `flanker`, `ironcalc`, `libpff-python`, `py3langid` | Each has all run deps satisfied by current conda-forge. Order within the wave doesn't matter; submit in parallel as separate PRs. **Dropped**: `dockerflow` (already at `conda-forge/dockerflow-feedstock` v2026.3.4 since 2026-06-01); `langfuse` (already at `conda-forge/langfuse-python-feedstock` v4.7.1 — `-python` suffix divergence). |
| **2** | 1 | `django-zxcvbn-password-validator` | Wait for `zxcvbn` (Wave 1) to merge before submitting; otherwise conda-forge CI can't resolve the run dep. |

### Practical considerations

- **PR cadence**: conda-forge/staged-recipes reviewers prefer no more than ~3–4 PRs in flight from one author at a time. Revised suggested cadence: open 3 from Wave 1b (start with `nested-multipart-parser`, `djangorestframework-api-key`, `brevo-python` — the highest-impact small-dep deps now that `django-lasuite` and `dockerflow` are off the list), wait for first merge, open next 3, etc. Whole Wave 1 should clear in 1–3 weeks at this rate.
- **Wave-1 risk recipes** (likely to draw extra review):
  - `libpff-python` — grayskull-emitted `noarch: python` ships a CPython-ABI `.so` (G4 recipe-style mismatch). Review will request switching to `noarch: false` or adding per-Python builds. Consider rewriting the recipe before submission.
  - `ironcalc` — Rust + maturin build per-Python; needs `cross-python_${{ target_platform }}` + `crossenv` host. Review may ask for `THIRDPARTY.yml` via `cargo-bundle-licenses`; recipe already does this.
  - `odfdo` carries `pip_check: false` with inline justification — reviewers may ask to address the upstream lxml env-marker constraint instead. Acceptable answer: cite upstream issue + flag PR. (`langfuse` previously also in this group; now off the list since it's already on conda-forge.)
  - `flanker` — large transitive dep list (9 packages); reviewers may ask whether `tld`/`webob` versions match the latest. `recipe-generator.py` v8.10.1's PEP 508 parser should have captured these correctly.
- **Wave-2 timing**: don't open `django-zxcvbn-password-validator` until `zxcvbn` shows green on conda-forge (typically 1–2 hours after merge for the bot to update repodata).
- **Tier-D Django app deps now resolve locally** but most of these recipes won't submit because conda-forge declines web apps. Of the originally-listed widely-useful Phase-6b dep recipes, only `odfdo` is still in the genuinely-submission-ready set — `dockerflow` and `langfuse` were already submitted by others (kudos to whoever got there first).

### What this section does NOT cover

The 31 local-only recipes (Tiers B/C/D/E/F) are NOT in this submission plan. They build cleanly and install locally but will be rejected at conda-forge review for the reasons documented in their per-recipe `⚠️ LOCAL-ONLY` banners. If you ever want to upstream one (e.g., `galene-sdk` once it's published to PyPI), the recipe is ready — just remove the banner and submit as a regular Tier-A candidate.

## Phase 6c — Remediation sweep results

After the initial build, all 46 recipes were re-run through the conda-forge-expert 4-tool inner loop. Final state:

| Check | Result |
|---|---|
| **`validate_recipe`** (rattler-build lint + conda-smithy lint) | **46 / 46 PASS ✅** |
| **`optimize_recipe`** (17 check codes — STD/SEC/ABT/PIN/DEP/SEL/TEST/MAINT/SCRIPT/SCHEMA + new TEST-003) | **46 / 46 clean ✅** after Phase 6d canonical-test restoration |
| **`check_dependencies`** (against `conda-forge` + local channel) | 0 / 46 with **real** missing deps. 16 recipes show "missing" deps that are false positives — `dependency-checker.py` only accepts one `--channel` arg, so it can't see both conda-forge AND the local channel simultaneously. **Every "missing" dep is confirmed built locally in `build_artifacts/linux64/`**; they resolve at recipe-build time via `native-build.sh`'s auto-channel injection. |
| **`scan_for_vulnerabilities`** (OSV.dev) | 0 / 46 with critical or high CVEs. 14 recipes had pinned deps scanned; the rest skipped scan because pins were stripped to `>=` or bare names (per Tier-D pin-loosening policy). |

## Phase 6d — Canonical-test / dep / license fixes (skill-level bug fixes)

Three real skill bugs surfaced from a conda-forge web-service review hint on `dockerflow`:

> ℹ️ noarch: python recipes should usually follow the syntax in our documentation for specifying the Python version. For the `tests[].python.python_version` or `tests[].requirements.run` section of the recipe, you should usually use the pin `python_version: ${{ python_min }}.*` or `python ${{ python_min }}.*` for the python_version or python entry.

**Skill bug 1 — Phase-6c substituted `package_contents.site_packages` for `python.imports` in 29 recipes without justification.** Fix: new optimizer check **`TEST-003`** flags any noarch:python recipe missing both `python.imports:` AND an inline `# CFEP-25-justified:` comment. 14 Phase-6b recipes restored to the canonical CFEP-25 triad; 16 Tier-D/C recipes that legitimately can't run `python.imports` (Django settings, ML deps) got an explicit `# CFEP-25-justified:` comment. New SKILL.md "Canonical Test Block for `noarch: python` Recipes" section codifies the rule.

**Skill bug 2 — recipe-generator stripped PEP 508 version specifiers.** `django-lasuite` shipped with `- django` instead of `- django >=5.0` because `recipe-generator.py` only captured the bare package name (`^([a-zA-Z0-9_-]+)`) and dropped `>=X.Y`. It also dropped any dep with a `;` env marker — so `odfdo` lost `lxml`, `py3langid` lost `numpy`. Fix: new `_parse_requires_dist_specs()` PEP 508 parser captures the version range, handles `; python_version` markers by collapsing variants to the loosest range, and drops only `; extra ==` / `; sys_platform ==` (the latter routes through `_classify_sys_platform_deps` for selectors). All 14 Phase-6b recipes + `django-lasuite` regenerated; pins now flow from upstream `pyproject.toml`.

**Skill bug 3 — Phase-6c used a non-canonical secondary `source.url` for LICENSE.** Per [conda-forge.org/docs/maintainer/adding_pkgs/](https://conda-forge.org/docs/maintainer/adding_pkgs/) (verbatim):

> Sometimes upstream maintainers do not include a license file in their tarball despite being demanded by the license. If this is the case, you can add the license to the recipe directory (here named LICENSE.txt) and reference it inside the recipe file.
> The license should only be shipped along with the recipe if there is no license file in the downloaded archive. If there is a license file in the archive, please set `license_file` to the path of the license file in the archive.

I audited all 33 recipes that had the secondary-source pattern: **25 had upstream archives that ship LICENSE** (the secondary fetch was redundant — removed, in-recipe LICENSE file deleted) and **8 genuinely need an in-recipe LICENSE** (npm tarballs without LICENSE: lasuite-integration, cunningham-react, cunningham-tokens, e2esdk-client, brevo-python; GitHub repos that omit LICENSE: suite-meet-matting, suite-hackdays-frontend; PyPI sdist that omits LICENSE: odfdo, django-fernet-encrypted-fields). For recipes where the upstream LICENSE path is non-standard (`LICENSE.md`, `LICENSE.txt`, `COPYING`, `bindings/python/LICENSE-Apache-2.0.md`), `license_file:` was repointed. New SKILL.md "Canonical License-File Placement" section codifies the three-pattern decision tree.

| Phase-6d skill artefact | What changed |
|---|---|
| `.claude/skills/conda-forge-expert/scripts/recipe_optimizer.py` | New `TEST-003` analyzer + SEL-002 escape via `# CFEP-25-justified:` comment |
| `.claude/skills/conda-forge-expert/scripts/recipe-generator.py` | New `_parse_requires_dist_specs()` PEP 508 parser |
| `.claude/skills/conda-forge-expert/SKILL.md` | New "Canonical Test Block for `noarch: python` Recipes" + "Canonical License-File Placement" sections under Critical Constraints |

### Doc cross-references (verified against authoritative sources)

| Phase-6d change | Authoritative source confirmed |
|---|---|
| CFEP-25 triad (`host: python ${{ python_min }}.*`, `run: python >=${{ python_min }}`, test's `python_version`) | [`conda-forge/cfep/cfep-25.md` Specification section](https://github.com/conda-forge/cfep/blob/main/cfep-25.md#specification) — verbatim: "Recipes that create `noarch: python` packages will use the following configuration in their build definitions: `host: - python {{ python_min }}`, `run: - python >={{ python_min }}`, `test: requires: - python {{ python_min }}`". |
| `python_version: [${{ python_min }}.*, "*"]` list form (test) | [staged-recipes#32857 r3039190932](https://github.com/conda-forge/staged-recipes/pull/32857#discussion_r3039190932) — ocefpaf's convention; not part of CFEP-25 itself. Already enforced by TEST-002. |
| Space-separated MatchSpec form (`- django >=5.0`) | Cross-checked against live `conda-forge/django-feedstock/recipe/meta.yaml` HEAD — uses identical form (`asgiref >=3.9.1`, etc.). [rattler-build recipe-format reference](https://rattler-build.prefix.dev/latest/reference/recipe_file/#requirements-section) confirms "Versions for requirements must follow the conda / mamba match specification." |
| LICENSE in recipe directory when upstream archive omits | [conda-forge.org/docs/maintainer/adding_pkgs/](https://conda-forge.org/docs/maintainer/adding_pkgs/) — verbatim block quoted above. |
| `license` field must be a valid SPDX identifier/expression | [conda-forge.org/docs/maintainer/adding_pkgs/#spdx-identifiers-and-expressions](https://conda-forge.org/docs/maintainer/adding_pkgs/#spdx-identifiers-and-expressions) — "using a SPDX identifier or expression is recommended" (referenced in optimizer ABT-002). |

### Build-time test verification (post-Phase-6d)

Every recipe's test phase ran during `rattler-build` build and **passed** (✓ all tests passed in rattler-build output). Final breakdown after Phase 6d:

| Test type | Count | Recipes |
|---|---|---|
| `python.imports` + `pip_check: true` + CFEP-25 dual-version matrix | **13** | Tier A: `django-lasuite`. Tier C: `galene-sdk`. Phase 6b: `brevo-python`, `django-fernet-encrypted-fields`, `django-pydantic-field`, `djangorestframework-api-key`, `django-zxcvbn-password-validator`, `dockerflow`, `flanker`, `ironcalc`, `nested-multipart-parser`, `py3langid`, `zxcvbn` |
| `python.imports` + `pip_check: false` + CFEP-25 matrix (upstream pin conflict) | **2** | `langfuse` (wrapt<2 vs conda-forge wrapt 2.x), `odfdo` (lxml env-marker pip-check bug) |
| `package_contents.site_packages` + `# CFEP-25-justified:` comment | **16** | Tier-D Django apps (15) + Tier-C `meet-whisperx`. Justified because `import <module>` would fail without `DJANGO_SETTINGS_MODULE` configured (Tier-D) or because upstream uses a generic top-level `app` module that collides (meet-whisperx). |
| `package_contents.files` (npm libraries, frontend source trees, fork skeletons) | **12** | Tier B: all 5 npm. Tier E: all 4 frontends. Tier F: `suite-media-sdk`, `suite-planka`, `suite-containers` |
| `script` test (binary `--version` or trivial echo with `# CFEP-25-justified:`) | **3** | `suite-livekit-sip` (Go binary), `libpff-python` (C extension under noarch:python — known recipe-style mismatch), `suite-meet-matting` (heavy ML deps that can't be resolved in test env) |

Total: 13 + 2 + 16 + 12 + 3 = **46 recipes, all tested at build time**.

`libpff-python` carries a trivial `script` test because the recipe inherits grayskull's `noarch: python` despite shipping a CPython-ABI-specific C extension — a known recipe-style mismatch. The build itself produces a working artifact for linux-64 / cp310; converting to platform-specific would require switching to `noarch: false` (a follow-up bug, not blocking local use). The `# CFEP-25-justified:` comment documents this.

---

## Tier A — clean conda-forge candidates (1)

| conda name | upstream | version | notes |
|---|---|---|---|
| `django-lasuite` | [`suitenumerique/django-lasuite`](https://github.com/suitenumerique/django-lasuite) | 0.0.26 | Published on PyPI; MIT; common Django library used by every other Suite backend. ✅ **Already on conda-forge as `django-lasuite-feedstock` v0.0.26 since 2026-04-13** (verified 2026-06-07 — bare-name match; feedstock `source.url` points to PyPI `django-lasuite`). Local recipe is redundant for submission; can be installed from conda-forge directly. |

## Tier B — npm libraries (5, all local-only)

| conda name | published as | version | reason flagged |
|---|---|---|---|
| `lasuite-ui-kit` | `@gouvfr-lasuite/ui-kit` | 0.23.1 | Scoped React component lib for bundler-driven consumption (not a CLI). |
| `lasuite-integration` | `@gouvfr-lasuite/integration` | 1.0.3 | Scoped template/asset lib; zero runtime deps, ships precompiled artifacts only. |
| `cunningham-react` | `@openfun/cunningham-react` | 4.0.0 | OpenFUN React design system; bundler-driven consumption. |
| `cunningham-tokens` | `@openfun/cunningham-tokens` | 3.0.0 | Design-token package (CSS/SCSS/TS) consumed by `cunningham-react`. |
| `e2esdk-client` | `@socialgouv/e2esdk-client` | 1.0.0-beta.1 | Published under the upstream `@socialgouv` namespace; `suitenumerique/e2esdk` is a downstream fork. Beta version. |

Why none of these submit cleanly: conda-forge npm recipes are accepted mostly for CLI tools (e.g. `husky`, `openspec`, `copilot-api`). UI component libraries published as scoped private packages aren't an established pattern.

## Tier C — Python libs not on PyPI (3, local-only)

| conda name | dist name | upstream commit | reason flagged |
|---|---|---|---|
| `meet-whisperx` | `whisper-openai-api` (per pyproject) | `320130b94f63` | Not on PyPI; project is actually a FastAPI service for Meet's live transcript. Top-level pkg is `app` — collisions with generic env. |
| `galene-sdk` | `galene-sdk` | `6f4ad2c987eb` | Not on PyPI; clean monorepo SDK shipping `galene.api`. Would be a Tier-A submission once published. Python ≥3.12. |
| `suite-meet-matting` | `background-segmentation-benchmark` | `fa9f16aa7091` | Not on PyPI; research/benchmark tool. **`mediapipe` is not on conda-forge**: install via pip in the target env. Python ≥3.11. |

## Tier D — Django web-app backends (15, all local-only)

All 15 are deployed services, not libraries. Installing the conda package gives the importable Python backend module; running the actual service requires Postgres + Redis + Celery + OIDC provider + S3-compatible storage + SMTP + the corresponding frontend. conda-forge declines web-app recipes as policy.

Pins, build backends, and conventions per app:

| conda name | upstream | version | dist name | py floor | build backend | notes |
|---|---|---|---|---|---|---|
| `suite-docs` | [`docs`](https://github.com/suitenumerique/docs) | 5.1.0 | `impress` | 3.13 | uv-build | Collaborative docs platform |
| `suite-meet` | [`meet`](https://github.com/suitenumerique/meet) | 1.17.0 | `meet` | 3.13 | uv-build | Video conferencing (LiveKit) |
| `suite-drive` | [`drive`](https://github.com/suitenumerique/drive) | 0.18.0 | `drive` | 3.13 | uv-build | File sharing; needed `rm -f src/backend/__init__.py` for uv-build |
| `suite-messages` | [`messages`](https://github.com/suitenumerique/messages) | 0.7.0 | `messages-backend` | 3.14 | uv-build | Collaborative inbox |
| `suite-calc` | [`calc`](https://github.com/suitenumerique/calc) | 3.3.0 | `impress` | 3.12 | setuptools | Spreadsheets (fork of docs codebase — dist name collides; disambiguated via conda name) |
| `suite-people` | [`people`](https://github.com/suitenumerique/people) | 1.25.4 | `people` | 3.14 | setuptools | Teams management |
| `suite-calendars` | [`calendars`](https://github.com/suitenumerique/calendars) | 0.10.1 | `calendars` | 3.13 | setuptools | Calendar |
| `suite-conversations` | [`conversations`](https://github.com/suitenumerique/conversations) | 0.0.16 | `conversations` | 3.13 | setuptools | AI chatbot |
| `suite-menshen` | [`menshen`](https://github.com/suitenumerique/menshen) | 0.1.0 | `menshen` | 3.14 | uv-build | OAuth2 token-exchange auth server |
| `suite-st-transfers` | [`st-transfers`](https://github.com/suitenumerique/st-transfers) | 0.1.0 | `transferts-backend` | 3.13 | uv-build | File transfer service |
| `suite-st-deploycenter` | [`st-deploycenter`](https://github.com/suitenumerique/st-deploycenter) | 0.0.1 | `deploycenter-backend` | 3.13 | setuptools | Needed `License :: OSI Approved` classifier stripped (PEP 639 rejects) + explicit `[tool.setuptools] packages = ["core", "deploycenter"]` |
| `suite-accounts` | [`accounts`](https://github.com/suitenumerique/accounts) | 0.0.1 | `accounts` | 3.14 | setuptools | Account management |
| `suite-hub` | [`hub`](https://github.com/suitenumerique/hub) | 0.0.1 | `hub` | 3.12 | setuptools | meet+chat hub |
| `suite-dictaphone` | [`dictaphone`](https://github.com/suitenumerique/dictaphone) | 0.7.1 | `dictaphone` | 3.14 | setuptools | Transcripts |
| `suite-find` | [`find`](https://github.com/suitenumerique/find) | 0.0.1 | `find` | 3.12 | setuptools | Search service |

### Tier-D conventions applied
- Versions stripped from run-deps (`>=X.Y.Z` → just package name) so the conda solver isn't blocked by upstream's `uv.lock` pins not matching conda-forge availability.
- For uv-build apps whose upstream `pyproject.toml` omits `[tool.uv.build-backend].module-name` (drive, messages, menshen, st-transfers), `module-name` is injected via `sed` in the build script to enumerate the actual top-level package dirs.
- Test phases simplified to `package_contents: { site_packages: [] }` — avoids the test env having to re-solve every transitive Django plugin against conda-forge for what is functionally a source-import.
- License fallback: every Tier-D recipe has a secondary source pulling the MIT LICENSE from `suitenumerique/.github/main/LICENSE` (the org-level license, sha256 `c16427e056a608dc1ec80238debd961ca97b3c82f35c84b64dd78043f2ff968b`).

## Tier E — frontend apps (4, all local-only)

Next.js / Vite source trees. Each ships under `${PREFIX}/share/suite-<name>/`; running requires `npm install && npm run build` after install.

| conda name | upstream | commit | scripts.build |
|---|---|---|---|
| `suite-projects` | [`projects`](https://github.com/suitenumerique/projects) | `5aa2996f64e7` | `npm run client:build` |
| `suite-helpcenter` | [`helpcenter`](https://github.com/suitenumerique/helpcenter) | `8a76bd67c2f4` | `next build` |
| `suite-hackdays` | [`hackdays`](https://github.com/suitenumerique/hackdays) | `073c13188a20` | `next build` |
| `suite-st-home` | [`st-home`](https://github.com/suitenumerique/st-home) | `bf9757fa2ce6` | `next build` |

## Tier F — forks (4, all local-only)

| conda name | upstream | parent | notes |
|---|---|---|---|
| `suite-livekit-sip` | [`livekit-sip`](https://github.com/suitenumerique/livekit-sip) | `livekit/sip` | Go CLI; needs `opusfile` + `soxr` + `libopus`. LICENSE pulled from `livekit/sip/main/LICENSE.txt` (fork omits). |
| `suite-media-sdk` | [`media-sdk`](https://github.com/suitenumerique/media-sdk) | `livekit/media-sdk` | Go library; no `cmd/`. Shipped as source tree under `${PREFIX}/share/`. |
| `suite-planka` | [`planka`](https://github.com/suitenumerique/planka) | `plankanban/planka` | **Archived**. Skeleton only. Use upstream `plankanban/planka` instead. |
| `suite-containers` | [`containers`](https://github.com/suitenumerique/containers) | `runpod/containers` | Dockerfile collection; source tree only. |

## Phase 6b — Missing Django deps (14, conda-forge-ready)

Built so Tier-D recipes resolve cleanly. None carry the local-only banner.

| conda name | version | license | test type | notes |
|---|---|---|---|---|
| `brevo-python` | 4.0.10 | MIT | `site_packages: [brevo]` | Brevo (ex Sendinblue) email API client. LICENSE pulled from `getbrevo/brevo-python/HEAD/LICENSE.md`. |
| `dockerflow` | 2026.3.4 | MPL-2.0 | `site_packages: [dockerflow]` | Mozilla Dockerflow healthcheck for Django/Flask. Used by 12 of 15 Django apps. ✅ **Already on conda-forge as `dockerflow-feedstock` v2026.3.4 since 2026-06-01** (verified 2026-06-07 — bare-name match). Local recipe redundant for submission. |
| `nested-multipart-parser` | 1.6.0 | MIT | `site_packages: [nested_multipart_parser]` | DRF multipart parser for nested form data. Used by 11 of 15 Django apps. |
| `django-pydantic-field` | 0.5.4 | MIT | `site_packages: [django_pydantic_field]` | Pydantic field for Django models. Build backend uv-build. |
| `django-fernet-encrypted-fields` | 0.4.0 | MIT | `site_packages: [encrypted_fields]` | Fernet-encrypted Django model fields. |
| `djangorestframework-api-key` | 3.1.0 | MIT | `site_packages: [rest_framework_api_key]` | DRF API-key auth. |
| `django-zxcvbn-password-validator` | 1.6.0 | MIT | `site_packages: [django_zxcvbn_password_validator]` | zxcvbn-strength password validator for Django auth. |
| `zxcvbn` | 4.5.0 | MIT | `python.imports: [zxcvbn]` + `pip_check` | Added in Phase 6c remediation — dep of `django-zxcvbn-password-validator`. |
| `langfuse` | 4.7.1 | MIT | `site_packages: [langfuse]` | LLM observability SDK. Build backend uv-build. ✅ **Already on conda-forge as `langfuse-python-feedstock` v4.7.1** (verified 2026-06-07 — `-python` suffix divergence; PyPI distribution `langfuse` maps to conda feedstock `langfuse-python` to disambiguate from upstream's polyglot SDK family `langfuse-js`, `langfuse-go`, etc.). Local recipe redundant for submission. Illustrates the four-form name-divergence check codified in skill v8.11.4 G10. |
| `odfdo` | 3.22.8 | Apache-2.0 | `site_packages: [odfdo]` | OpenDocument (ODF) read/write library. Build backend uv-build. |
| `flanker` | 0.9.11 | Apache-2.0 | `site_packages: [flanker]` | Mailgun email address/MIME parser. |
| `ironcalc` | 0.7.0 | Apache-2.0 | `site_packages: [ironcalc]` | Rust-based spreadsheet engine; built per-Python (py310..py313). |
| `libpff-python` | 20231205 | LGPL-3.0-or-later | `script` (trivial) | libyal/libpff Outlook PST/OST reader. Grayskull-emitted `noarch: python` despite C ext — known recipe-style mismatch; build artifact works on linux-64/cp310. |
| `py3langid` | 0.3.0 | BSD-3-Clause | `site_packages: [py3langid]` | Language identification. |

The Phase-6c remediation pass restored meaningful test coverage: each recipe's `package_contents.site_packages:` lists the actual top-level module installed (verified against the sdist's `__init__.py` layout where possible). Tests run during build and pass before the artifact is published.

## Tier G — not packaged (12)

These repos are not packageable as conda artifacts and were skipped by design:

| repo | reason |
|---|---|
| `documentation` | docs site (README/Markdown only) |
| `dev-handbook` | docs site |
| `hackdays2025` | hackathon landing (README/MD only, no manifests) |
| `.github` | org profile readme |
| `buildpack` | Heroku/Scalingo build hook (shell scripts) |
| `messagerie` | placeholder repo (README only) |
| `st-ansible` | Ansible collection — not conda packaging fit |
| `helm-dev-backend` | Helm chart only |
| `meet-kyutai-moshi-stt` | Dockerfile only |
| `gallene-deployment` | Helm/Dockerfile collection |
| `encryption` | placeholder (LICENSE + README only) |
| `roomkit-visio` | `compose.yml` only (deployment recipe) |

---

## Build issues fixed during the run

(For future maintenance reference.)

1. **`tool.uv.build-backend` missing `module-name`** in 4 Tier-D apps (drive, messages, menshen, st-transfers). Fix: `sed` an explicit `module-name = ["…"]` into pyproject.toml before `pip install`.
2. **Stray `src/backend/__init__.py` in `drive`** rejected by uv-build for namespace packages. Fix: `rm -f __init__.py` before install.
3. **PEP 639 classifier rejection in `suite-st-deploycenter`**. Fix: `sed -i '/License :: OSI Approved/d' pyproject.toml`.
4. **setuptools auto-discovery failure in `suite-st-deploycenter`** (multiple top-level pkgs). Fix: append `[tool.setuptools]\npackages = ["core", "deploycenter"]`.
5. **G7 (import name divergence)** on `meet-whisperx`. Fix: use `package_contents` test instead of `import app` (which would collide).
6. **G7 on `galene-sdk`** (dist `galene-sdk` ships `galene.api` namespace). Fix: `imports: [galene.api]`.
7. **G4 (LICENSE missing in npm tarballs)** on lasuite-integration, cunningham-react, cunningham-tokens, e2esdk-client. Fix: secondary `source.url` pulling LICENSE from upstream GitHub (openfun/cunningham, SocialGouv/e2esdk, suitenumerique/.github).
8. **G4 on `suite-livekit-sip`**: fork omits LICENSE. Fix: pull `livekit/sip/main/LICENSE.txt`.
9. **G4 on most Phase-6b deps**: PyPI sdists ship no LICENSE. Fix: secondary `source.url` per package.
10. **Restrictive `==` version pins** in upstream Django pyproject lockfiles — incompatible with what's currently on conda-forge. Fix: strip all version specifiers from `run:` in Tier-D recipes.
11. **uv-build vs setuptools vs hatchling** — the generator defaulted everything to hatchling. Manual fix per recipe.
12. **`pnpm install --prod` failures** for cunningham-react (404 on internal `@openfun/typescript-configs`) and e2esdk-client (workspace ref). Fix: drop the third-party-licenses step; ship only upstream LICENSE.
13. **`opusfile` + `soxr` required by livekit-sip Go CGO build** — added to host/run.

### Phase 6c remediation pass (post-initial-build):

14. **conda-smithy lint errors** on all 15 Tier-D + suite-meet-matting (noarch:python without `python >=${{ python_min }}` bound). Side effect of fix #10 — when I stripped `==` pins I also stripped `>=python_min`. Fix: restore the python bound explicitly.
15. **`redis` (PyPI) ≠ `redis` (conda-forge server)** — Tier-D recipes need the Python client, which on conda-forge is `redis-py`. Renamed across all 15.
16. **Missing `zxcvbn` for django-zxcvbn-password-validator** — built as a separate Phase-6b recipe to close the chain.
17. **G7 across Phase-6b**: brevo-python's top-level is `brevo` (not `brevo_python`); django-fernet-encrypted-fields installs `encrypted_fields`; libpff-python installs a top-level `pypff.cpython-310-*.so` (not a package directory). Verified each via sdist `__init__.py` listing.
18. **Empty `package_contents: { site_packages: [] }` tests** initially used to skip the test-env solver — replaced with **meaningful** site_packages lists checking the actual installed top-level module per recipe.
19. **`dependency-checker.py` only accepts one `--channel`** — the local channel `file://build_artifacts/linux64` and conda-forge can't be checked together, producing false-positive "missing" deps. Worked around by verifying each "missing" dep is built locally; documented the limitation.

## How to install the local channel

```bash
conda install -c file:///home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes/build_artifacts/linux64 \
  django-lasuite suite-docs
```

The `native-build.sh` wrapper auto-injects `build_artifacts/linux64/` as a channel source during local builds, so chained recipes (e.g., suite-docs depending on dockerflow) resolve without extra flags.

## What was NOT done (deliberate, per local-only directive)

- No `submit_pr` / `prepare_submission_branch` calls.
- No `gh pr create`.
- No git commits or pushes (the recipe directories were created in place under `recipes/`).
- No recipe submissions to conda-forge/staged-recipes.

If you later want to submit the Tier-A `django-lasuite` (and possibly Phase-6b dep recipes — they're the most submission-ready) to staged-recipes, follow the standard `conda-forge-expert` skill workflow from step 8b onward.

## Audit trail / how to reproduce the remediation pass

The remediation sweep is fully scripted and re-runnable:

```bash
cd /home/rxm7706/UserLocal/Projects/Github/rxm7706/local-recipes
python3 /tmp/remediation-sweep.py                 # validate + optimize + check_deps + scan_vulns on 46 recipes
cat /tmp/remediation-report.json                  # full JSON results
```

The sweep calls the canonical `conda-forge-expert` scripts:
- `.claude/scripts/conda-forge-expert/validate_recipe.py --json`
- `.claude/scripts/conda-forge-expert/recipe_optimizer.py` (emits JSON to stdout)
- `.claude/scripts/conda-forge-expert/dependency-checker.py`
- `.claude/scripts/conda-forge-expert/vulnerability_scanner.py`

These are the same scripts the MCP tools `validate_recipe`, `optimize_recipe`, `check_dependencies`, and `scan_for_vulnerabilities` wrap — the report is equivalent to running each MCP tool on every recipe.

---

## 2026-06-07 Re-audit

The original 2026-05-31 report listed 15 conda-forge-submission-ready recipes (Tier-A `django-lasuite` + the 14 Phase-6b deps). On 2026-06-07 the user flagged that one of those, `langfuse`, was actually already on conda-forge under a different feedstock name (`langfuse-python`). That single observation triggered a full re-audit of every "submission-ready" candidate using the **four-form PyPI→conda name-divergence check** codified in skill v8.11.4 G10:

1. Bare PyPI distribution name (`langfuse`)
2. Hyphen↔underscore swap (`langfuse` ↔ `langfuse_`)
3. `-py` suffix (`langfuse-py`)
4. `-python` suffix (`langfuse-python`) — **this is where it lived**

### Method

For each of the 15 candidates: query `conda.anaconda.org/conda-forge/{noarch,linux-64}/repodata.json` for each of the four name forms, then cross-verify hits by fetching the feedstock's `recipe/recipe.yaml` (or `recipe/meta.yaml`) via `gh api repos/conda-forge/<feedstock-name>-feedstock/contents/recipe/recipe.yaml` and confirming the `source.url` points at the expected PyPI distribution. A research subagent ran the bulk query; surprising results were re-verified manually.

### Findings — three recipes already on conda-forge

| Recipe | PyPI name | conda-forge feedstock | Pattern | Version | Feedstock created | Verification |
|---|---|---|---|---|---|---|
| `django-lasuite` | `django-lasuite` | `django-lasuite-feedstock` | bare name | v0.0.26 | 2026-04-13 | 2 noarch builds at v0.0.26; feedstock `source.url: pypi.org/packages/source/d/django-lasuite/django-lasuite-${{ version }}.tar.gz` matches local recipe's source. |
| `dockerflow` | `dockerflow` | `dockerflow-feedstock` | bare name | v2026.3.4 | **2026-06-01** | 1 noarch build at v2026.3.4; feedstock created just 7 days before this audit (after the original 2026-05-31 report was written). |
| `langfuse` | `langfuse` | `langfuse-python-feedstock` | **`-python` suffix** | v4.7.1 | (recipe at v4.7.1) | 61 noarch builds; latest matches PyPI `langfuse` v4.7.1; recipe `source.url: pypi.org/packages/source/l/langfuse/langfuse-${{ version }}.tar.gz` confirms identity. The `-python` suffix disambiguates from upstream's polyglot SDK family (`langfuse-js`, `langfuse-go`). |

The other 12 candidates were checked against all four name forms; none were found on conda-forge under any spelling. They remain genuinely submission-ready.

### Findings — 12 recipes still genuinely submission-ready

| Recipe | Local version | Pattern matched against (none found) |
|---|---|---|
| `brevo-python` | 4.0.10 | `brevo-python` / `brevo_python` / `brevo-python-py` / `brevo-python-python` — all 0 hits |
| `nested-multipart-parser` | 1.6.0 | (all four forms checked, 0 hits) |
| `django-pydantic-field` | 0.5.4 | (all four forms checked, 0 hits) |
| `django-fernet-encrypted-fields` | 0.4.0 | (all four forms checked, 0 hits) |
| `djangorestframework-api-key` | 3.1.0 | (all four forms checked, 0 hits) |
| `zxcvbn` | 4.5.0 | (all four forms checked, 0 hits) |
| `odfdo` | 3.22.8 | (all four forms checked, 0 hits) |
| `flanker` | 0.9.11 | (all four forms checked, 0 hits) |
| `ironcalc` | 0.7.0 | (all four forms checked, 0 hits) |
| `libpff-python` | 20231205 | already named with `-python` suffix; bare `libpff` also 0 hits |
| `py3langid` | 0.3.0 | (all four forms checked, 0 hits) |
| `django-zxcvbn-password-validator` | 1.6.0 | (all four forms checked, 0 hits) — Wave-2 (depends on `zxcvbn`) |

### Tier-D / Tier-E / Tier-F / Tier-B / Tier-C re-check

A 5-recipe spot check across `lasuite-ui-kit` (B), `cunningham-react` (B), `meet-whisperx` (C), `suite-docs` (D), `suite-livekit-sip` (F): all carry the correct `⚠️ LOCAL-ONLY` banner; tier classification still accurate; artifacts present. No discrepancies found.

Note: Tier-E frontend recipes live under `recipes/<name>-frontend/` (e.g. `recipes/suite-projects-frontend/`), not `recipes/<name>/`. Build artifacts use the suffix-stripped name (`suite-projects-*.conda`) because `package.name:` strips `-frontend`. An initial pass of the re-audit's research subagent flagged these as "missing recipe files" — false alarm; resolved on manual verification.

### Action items

1. **Update local Wave-1a / Wave-1b plan** (done — see § "Submission plan" above): drop `django-lasuite`, `dockerflow`, `langfuse` from the queue.
2. **Update local channel install instructions** to prefer conda-forge for the three already-on-CF packages:
   ```bash
   # Before (mixed local + conda-forge):
   conda install -c file://...build_artifacts/linux64 django-lasuite dockerflow langfuse suite-docs
   # After (CF for available packages, local for the rest):
   conda install -c conda-forge django-lasuite dockerflow langfuse-python
   conda install -c file://...build_artifacts/linux64 suite-docs
   ```
   Note: `langfuse` on conda-forge is named `langfuse-python` (`-python` suffix). Importing it in Python is still `import langfuse`.
3. **For Tier-D recipes depending on these three**: their `requirements.run:` blocks can stay as-is — the conda solver pulls from conda-forge directly when the dep is satisfiable there. The local-channel fallback only fires when conda-forge can't satisfy.
4. **Auto-memory cross-skill**: the `langfuse → langfuse-python` finding extended skill v8.11.4's G10 from a 3-form to a 4-form check and added the third confirmed divergence pattern to `feedback_pypi_conda_mapping_unreliable.md`. The `dockerflow` and `django-lasuite` findings (bare-name matches that just hadn't existed on 2026-05-31) are not divergence-pattern data — they're "someone else got there first" data, and no skill changes are warranted for them. (`dockerflow` was created 2026-06-01, only 1 day after the original report.)

### What changed between 2026-05-31 and 2026-06-07

| Item | 2026-05-31 | 2026-06-07 | Cause |
|---|---|---|---|
| Submission-ready count | 15 | 12 | 3 already on CF (1 since-2026-04, 1 since-2026-06-01, 1 the agent missed due to `-python` suffix) |
| Wave 1a | 1 (`django-lasuite`) | 0 | `django-lasuite` already on CF (would have been a duplicate-feedstock rejection) |
| Wave 1b | 13 | 11 | `dockerflow` + `langfuse` already on CF |
| Wave 2 | 1 (`django-zxcvbn-password-validator`) | 1 | unchanged |
| Recipes built | 46 | 46 | unchanged |
| Local-only count | 31 | 31 | unchanged |
| Skill version | n/a | v8.11.4 | G10 broadened from 3-form to 4-form check based on the `langfuse-python` finding |

### Re-audit reproducibility

To re-run this audit later, for each candidate recipe under `recipes/`:

```bash
NAME=langfuse  # or whatever recipe
for form in "$NAME" "${NAME//-/_}" "$NAME-py" "$NAME-python"; do
  echo "Checking conda-forge for: $form"
  for sub in noarch linux-64; do
    hits=$(curl -sL "https://conda.anaconda.org/conda-forge/${sub}/repodata.json" | \
      python3 -c "
import json, sys
d = json.load(sys.stdin)
pkgs = list(d.get('packages',{}).values()) + list(d.get('packages.conda',{}).values())
h = [p for p in pkgs if p.get('name')==\"$form\"]
print(f'  $sub: {len(h)} builds')
")
    echo "$hits"
  done
done
```

If any name form returns >0 builds, fetch the feedstock recipe to cross-verify identity:

```bash
gh api "repos/conda-forge/${MATCHED_NAME}-feedstock/contents/recipe/recipe.yaml" \
  --jq '.content' | base64 -d | head -20
```

Look for `source.url` matching the expected PyPI distribution — that confirms the conda-forge feedstock is the same package, not an unrelated namespace clash.
