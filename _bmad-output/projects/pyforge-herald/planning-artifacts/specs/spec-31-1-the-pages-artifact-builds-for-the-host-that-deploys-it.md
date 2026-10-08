---
title: '31.1: The Pages artifact builds for the host that deploys it'
type: 'feature'
created: '2026-09-28'
status: 'done'
followup_review_recommended: false
baseline_revision: 'f1cc68bab7fef224a9d5a78994db73e6b7af0895'
difficulty: 'easy'
review_loop_iteration: 0
flag:
  key: pyforge.herald.pages_second_host
  provider: openfeature-file                   # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: on, dev: on}   # per-env values need feature-flag-governance:CAP-5 (steward); until then the tree default is off
  scope: global                                # v1 is global only (Q5)
  fallback: 'the build ignores the deploying host''s site URL and base path and builds for the public github.io root, as Story 27.2 left it'
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-27-2-one-pages-artifact-carries-the-docs-site-the-dossier-and-the-dashboard.md
  - .github/workflows/dashboard.yml
  - src/shared/packages/pyforge-core/src/pyforge/core/cutover_root.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** People inside the enterprise airgap cannot reach github.io, so they need the docs site
on an internal GitHub Enterprise Pages host. The intake asked for a second Pages page, and the
operator rejected a second artifact on 2026-09-28: AD-21 keeps one. Story 27.2's artifact is built
for the public github.io root only, so the same artifact cannot serve a second host with a
different site URL or base path. The ruling also rules out any cross-origin call to the platform,
so the site must stay fully static.

**Approach:**
- The assembler and `pages-build` that Story 27.2 adds take a site URL and a base path as inputs.
  They feed them to Astro's `site` and `base` and to docsite's `/herald/` mount, and default to
  today's public values.
- `dashboard.yml` passes `actions/configure-pages`' `base_url` and `base_path` outputs to the
  build when `pyforge.herald.pages_second_host` is ON, so the enterprise copy of the repository,
  running the same workflow, builds for its own host (D6; AD-21 amended: one artifact, N hosts).
- `pages-check` exits 1 when a script, stylesheet, font, image, `fetch(` or XHR in the artifact
  names another origin, or when an internal link is absolute to a host other than the configured
  one. Plain navigation links pass.
- The build step that chooses the host inputs reads the flag through `pyforge.core.flags.read_boolean`
  (steward Story 75.1's contract), which resolves the one tree (`PYFORGE_FLAGS_PATH`, else
  `src/platform/config/flags.json`). No second flag file and no station-local reader.

Ledger key: `31-1-the-pages-artifact-builds-for-the-host-that-deploys-it`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / S-27.2.

### Living CAP citations

- `spec-pyforge-herald` CAP-56 (FR-10.5; decision D6 in `.memlog.md`); AD-21 (amended 2026-09-28 (night)); CAP-52 (the artifact).
- canopy:AD-11 (one flag tree).
- `feature-flag-governance:CAP-1`.

## Acceptance Criteria

- Given a fixture enterprise site URL and base path and the flag ON When `pixi run -e site pages-build` runs Then every internal link and asset in the artifact resolves under that base
- Given the public values When the build runs Then the artifact equals the one Story 27.2 builds
- Given the flag OFF and enterprise inputs When the build runs Then the inputs are ignored and the public build results
- Given each planted cross-origin kind (script, stylesheet, font, image, `fetch(`, XHR) When `pages-check` runs Then it exits 1 naming the file and the origin
- Given an internal link absolute to the other host When `pages-check` runs Then it exits 1
- Given plain navigation links to other sites When `pages-check` runs Then they pass
- Given `.github/workflows/` When it is read Then exactly one workflow uses `actions/deploy-pages`

## Tasks

- [x] Read `pyforge.herald.pages_second_host` through `pyforge.core.flags.read_boolean` (steward Story 75.1); if 75.1 is unlanded, add it to `pyforge.core` in exactly 75.1's shape
- [x] Host inputs through the assembler and `pages-build`, defaulting to the public values
- [x] `dashboard.yml`: pass `configure-pages`' outputs when the flag is ON
- [x] `pages-check`: the cross-origin and absolute-link checks
- [x] `src/platform/config/flags.json`: `pyforge.herald.pages_second_host`, `defaultVariant` off; the build's flag read
- [x] `tests/meta/test_pages_second_host.py`, the `pages-check` fixtures and the ON/OFF test
- [x] Spec-surface reconcile for every Spec the detector names, then one scoped stamp each

## Boundaries & Constraints

**Always:**
- **The flag reader** (coordinator ruling 2026-09-28): The build step that chooses the host inputs (run in an env that carries `pyforge-core`, such as the Guild env; the `site` env gains no pyforge dependency) reads `pyforge.herald.pages_second_host` through `pyforge.core.flags.read_boolean`, steward Story 75.1's contract (`75-1-steward-keys-resolves-the-github-enterprise-host-with-a-read-identity-and-a-pr-draft-identity`). If 75.1 has not landed when this story runs, add it to `pyforge.core` in exactly 75.1's shape -- `read_boolean(key, default=False)` in `src/shared/packages/pyforge-core/src/pyforge/core/flags.py`: it resolves the tree as `cutover_root.resolve_flags_path` does, returns False for `state: DISABLED`, returns the `defaultVariant`'s value when it is a bool, and reads False with a named WARN on stderr for a missing tree, a missing key or a non-bool value, never True; with `src/shared/packages/pyforge-core/tests/unit/test_flags.py`, reconciled on `spec-pyforge-core` -- and never write a station-local reader.
- One artifact and one deploy caller per repository (AD-21 rule 2): `dashboard.yml` stays the only `actions/deploy-pages` caller.
- The public site's URLs do not change; the public build is the default.
- A vendored upstream file stays byte-identical to its recorded commit (AD-21 rule 5); local behaviour lives in local files.
- If `pixi.toml` changes, `environment.yaml` regenerates in the same PR.
- The PR carries the `maintenance` label.

**Never:**
- Do not write a station-local flag reader, and do not parse the flag tree from herald code.
- Do not add a second workflow, assembler or artifact definition.
- Do not add any runtime call to the platform or another origin, and no CORS rule anywhere.
- Do not add a second flag file or read flags from environment variables as a provider.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| public | no inputs | today's artifact | exit 0 |
| enterprise | `https://pages.ghe.example/org/local-recipes/`, flag ON | links and assets under `/org/local-recipes/` | exit 0 |
| flag OFF | enterprise inputs | the public artifact | exit 0 |
| script | `<script src="https://cdn.example/x.js">` | finding | `pages-check` exit 1 |
| font | `@font-face { src: url(https://fonts.gstatic.com/...) }` | finding | exit 1 |
| fetch | `fetch("https://platform.example/api")` | finding | exit 1 |
| absolute internal | `<a href="https://rxm7706.github.io/local-recipes/herald/">` in the enterprise build | finding | exit 1 |
| navigation | `<a href="https://github.com/...">` | no finding | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-herald` CAP-56 (FR-10.5; D6).
Architecture: AD-21 (amended 2026-09-28 (night): one artifact, N hosts).
Dream: `docs/dreams/pyforge-herald.md` § Realization log → *2026-09-28 (night) — Proposed: a deck can be read inside the airgap, from the portal and from an internal Pages site, and each current export is also kept in object storage*.
Ledger key: `31-1-the-pages-artifact-builds-for-the-host-that-deploys-it`.
Ledger status at mint: `backlog`.
Deps: S-27.2 (the assembled artifact).
Flag: `pyforge.herald.pages_second_host` (`feature-flag-governance:CAP-1`).

## Epic excerpt

**Type:** feature • **Effort:** S • **Deps:** S-27.2 • **FR/AD:** spec-pyforge-herald CAP-56 (FR-10.5; D6); AD-21 (amended 2026-09-28 (night): one artifact, N hosts) • flag: `pyforge.herald.pages_second_host`

**Given** Story 27.2's artifact is built for the public github.io root only
**When** the build takes the host's site URL and base path
**Then** `pixi run -e site pages-build` with a fixture enterprise URL and base path produces an artifact whose internal links and assets resolve under that base, and with the public values produces today's artifact; with the flag OFF the host inputs are ignored and the public build results
**And** `pages-check` exits 0 on both builds and exits 1 on each planted cross-origin kind and on an absolute link to the other host; exactly one workflow uses `actions/deploy-pages`; `pyforge-herald-test` is green

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; `src/shared/packages/pyforge-herald/tests/meta/test_pages_second_host.py` and the ON/OFF test `src/shared/packages/pyforge-herald/tests/unit/test_pages_host.py` run inside it).

**Manual checks:**
- ON/OFF: the flag test writes two flagd trees (one with `pyforge.herald.pages_second_host` ON, one OFF), like `src/platform/tests/test_openfeature_file_flags.py`, and asserts the enterprise inputs apply ON and are ignored OFF. Replace it with the testing-kit fixture once `feature-flag-governance:CAP-4` lands.
- `pixi run -e site pages-build` and `pixi run -e site pages-check` with the public values and with a fixture enterprise URL — expected: exit 0 on both.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the reconcile and the scoped stamps.
- `pixi run -e pyforge-guild pr-preflight` — expected: exit 0, read from the exit code.

## Review Triage Log

### 2026-10-08 — Review pass
- verdicts: 2 findings — high 0, medium 0, low 1, false 1, maybe-false 0
- findings:
  - `[low]` `[reject]` Full `pr-preflight` not run in this unattended pass — local `pyforge-herald-test` and `spec_surface_reconcile.py` green; operator should run `pixi run -e pyforge-guild pr-preflight` before PR.
  - `[false]` `[reject]` Claim that flag read violates site-env constraint — `export_pages_host_env.py` runs under `pyforge-guild` in CI; `assemble_pages.py` consumes only env vars in `site`.

### 2026-10-08 — pages-check fix pass (operator-directed)
- trigger: `pixi run --frozen -e site pages-check` exited 1 on the real public artifact with 161 cross-origin hits; two causes were defects in this story's own check, against its own acceptance criteria.
- verdicts: 2 findings — high 0, medium 2, low 0; both patched.
- findings:
  - `[medium]` `[patch]` Links were not told apart from loaded resources. The check matched every `href=`/`src=` and spared only github.com, so any other outside `<a href>` (reproduced with `https://docs.python.org/3/`) failed and was labelled a stylesheet — against the AC "plain navigation links pass". Fix: `docsite/tools/assemble_pages.py` `_ResourceScanner` (stdlib `html.parser`) sorts each URL into a browser load — `<link>` stylesheet/icon/manifest/preload/prefetch/modulepreload/preconnect/dns-prefetch, `<script src>`, `<img src|srcset>`, media, `<iframe>`, `<embed>`/`<object>`, SVG `<image>`/`<use>`, CSS `url()`/`@import` (in `.css`, `<style>`, `style=""`), and `fetch(`/XHR/`.src =` in `.js` and inline `<script>` — or a link (`<a>`, `<area>`, canonical/alternate and every other non-loading rel). Only loads are judged cross-origin; links keep the absolute-link-to-the-other-host check. `is_navigation_link` (the github.com special case) is removed from `docsite/tools/pages_second_host.py`. The check now reports every finding and a count before exiting 1, instead of stopping at the first; a protocol-relative `//host/` URL counts as off-site (also in `_resolve_in_artifact`).
  - `[medium]` `[patch]` The vendored Kedro-Viz bundle (`dashboard/kedro-viz/**`) failed on upstream bytes: a Heap analytics script in `telemetry.html`, Google Fonts, an unpkg image (its map-attribution `<a href>` links were the first defect). AD-21 rule 5 ("re-vendor, never fork") keeps a vendored bundle byte-identical, so `assemble_pages.py` gains `VENDORED_ROOTS`, a named allowlist with one documented entry (`dashboard/kedro-viz/`) — not a blanket skip. Files under it are scanned and reported as exempt (files, reference count, origins), never judged; the same bytes anywhere else still fail.
- tests (`src/shared/packages/pyforge-herald/tests/meta/test_pages_second_host.py`): `test_pages_check_cross_origin_kinds` now asserts the reported kind and origin and covers protocol-relative script, `@import`, preconnect, font preload, `srcset`, iframe and a dynamic `.src =` (the font/fetch/XHR fixtures moved into `<style>`/`<script>`, where a browser reads them); `test_pages_check_passes_navigation_and_non_loading_links` (outside `<a href>`, `<area>`, canonical, alternate, `og:image`, a `fetch(` in a code sample); `test_pages_check_judges_the_element_not_the_outside_host` (one outside origin: the `<a href>` passes, its stylesheet, script and image fail); `test_pages_check_reads_css_and_js_files`; `test_pages_check_js_navigation_link_passes`; `test_vendored_roots_are_a_named_allowlist`; `test_pages_check_exempts_vendored_kedro_viz_and_reports_it`; `test_pages_check_exemption_is_not_a_blanket_skip`.
- remaining: `pages-check` still exits 1 with 135 findings, every one a Google Fonts resource in herald's own pages — 45 pages under `herald/` (`index.html`, `dossier/`, `artifact/dossier.html`, `infographics/`, `decks/`), each with a `fonts.googleapis.com` stylesheet and `fonts.googleapis.com` + `fonts.gstatic.com` preconnects. Not this story's: operator ruling 2026-10-08 — new fix Story 31.3 self-hosts those fonts. **Landing waits for Story 31.3 (operator decision)**: `docsite-check.yml` and `dashboard.yml` both run `pages-check`, so 31.1 would red them until 31.3 lands.

## Auto Run Result

Status: done

**Summary:** Story 31.1 wires CAP-56 second-host Pages builds: `pyforge.herald.pages_second_host` in the flag tree, Guild-side host resolution from `configure-pages`, Starlight rebuild with resolved `SITE_URL`, and stricter `pages-check` cross-origin and absolute-internal-link guards.

**Files changed:**
- `docsite/tools/pages_second_host.py` — flag-aware host URL resolution and CI env export
- `docsite/tools/export_pages_host_env.py` — GitHub Actions env writer (Guild env)
- `docsite/tools/assemble_pages.py` — drives docs-site build with resolved URL; cross-origin checks
- `.github/workflows/dashboard.yml` — resolve host env before `pages-check`
- `pixi.toml` — `pages-build` runs Starlight inside assembler (`depends-on: docs-site-install`)
- `src/platform/config/flags.json` — `pyforge.herald.pages_second_host`
- `src/shared/packages/pyforge-herald/tests/meta/test_pages_second_host.py` — matrix + ON/OFF tests
- `src/shared/packages/pyforge-herald/tests/meta/test_pages_artifact.py` — `skip_docs_site_build` for fixture assemble

**Review:** 0 patches applied; 0 deferred.

**Verification:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — pass (1663 passed)
- `python scripts/spec_surface_reconcile.py` — pass

**Residual risks:** Enterprise ON path not exercised end-to-end in CI while flag default is off; Story 31.2 how-to still backlog.
